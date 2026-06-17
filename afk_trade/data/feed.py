"""Sumber data OHLC.

Menyediakan satu fungsi `get_data` yang mencoba beberapa sumber secara berurutan:
1. MetaTrader5 (jika paket terinstal dan terkoneksi) -> data forex sungguhan.
2. File CSV (jika `csv_path` diberikan).
3. Data sintetis (selalu tersedia) -> agar bot bisa diuji tanpa MT5/internet.

Semua sumber mengembalikan pandas.DataFrame dengan kolom:
    time, open, high, low, close, volume
dan index integer berurutan.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

# Profil data sintetis per simbol (harga awal, volatilitas, drift) agar
# bentuk harga menyerupai pasar aslinya. XAUUSD (emas) ~ $2350 & lebih volatil.
_SYNTHETIC_PROFILES = {
    "XAUUSD": dict(start_price=2350.0, volatility=0.006, drift=0.00010),
    "EURUSD": dict(start_price=1.10, volatility=0.0015, drift=0.00002),
}

# Pemetaan string timeframe -> konstanta MT5 (diisi saat MT5 tersedia).
_MT5_TIMEFRAMES = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 16385,
    "H4": 16388,
    "D1": 16408,
}


def synthetic_ohlc(
    bars: int = 2000,
    *,
    seed: Optional[int] = 42,
    start_price: float = 1.10,
    volatility: float = 0.0015,
    drift: float = 0.00002,
) -> pd.DataFrame:
    """Hasilkan data OHLC sintetis ala random-walk (untuk uji coba tanpa MT5).

    Cocok meniru perilaku pair forex seperti EURUSD di sekitar harga ~1.10.
    """
    rng = np.random.default_rng(seed)
    rets = rng.normal(loc=drift, scale=volatility, size=bars)
    close = start_price * np.exp(np.cumsum(rets))

    # Bangun open/high/low yang konsisten dari close.
    open_ = np.empty_like(close)
    open_[0] = start_price
    open_[1:] = close[:-1]
    noise = np.abs(rng.normal(0, volatility / 2, size=bars))
    high = np.maximum(open_, close) + noise
    low = np.minimum(open_, close) - noise
    volume = rng.integers(50, 500, size=bars).astype(float)

    times = pd.date_range("2020-01-01", periods=bars, freq="h")
    return pd.DataFrame(
        {
            "time": times,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
    )


def _load_csv(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df.columns = [c.lower() for c in df.columns]
    required = {"open", "high", "low", "close"}
    if not required.issubset(df.columns):
        raise ValueError(f"CSV harus punya kolom {required}, dapat {set(df.columns)}")
    if "time" not in df.columns:
        df["time"] = pd.RangeIndex(len(df))
    if "volume" not in df.columns:
        df["volume"] = 0.0
    return df.reset_index(drop=True)


def _load_mt5(symbol: str, timeframe: str, bars: int) -> Optional[pd.DataFrame]:
    """Coba ambil data dari MetaTrader5. Kembalikan None jika tidak tersedia."""
    try:
        import MetaTrader5 as mt5  # type: ignore
    except ImportError:
        return None

    if not mt5.initialize():
        return None
    try:
        tf = _MT5_TIMEFRAMES.get(timeframe.upper(), _MT5_TIMEFRAMES["H1"])
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
        if rates is None or len(rates) == 0:
            return None
        df = pd.DataFrame(rates)
        df = df.rename(columns={"tick_volume": "volume", "real_volume": "real_volume"})
        df["time"] = pd.to_datetime(df["time"], unit="s")
        cols = ["time", "open", "high", "low", "close"]
        df["volume"] = df.get("volume", 0.0)
        return df[cols + ["volume"]].reset_index(drop=True)
    finally:
        mt5.shutdown()


def get_data(
    symbol: str = "EURUSD",
    timeframe: str = "H1",
    bars: int = 2000,
    *,
    csv_path: Optional[str] = None,
    allow_synthetic: bool = True,
) -> pd.DataFrame:
    """Ambil data OHLC dengan fallback otomatis: MT5 -> CSV -> sintetis."""
    df = _load_mt5(symbol, timeframe, bars)
    if df is not None and len(df) > 0:
        return df

    if csv_path:
        return _load_csv(csv_path)

    if allow_synthetic:
        profile = _SYNTHETIC_PROFILES.get(symbol.upper(), {})
        return synthetic_ohlc(bars, **profile)

    raise RuntimeError(
        "Tidak ada sumber data tersedia (MT5 tidak aktif, CSV tidak diberikan, "
        "dan sintetis dimatikan)."
    )
