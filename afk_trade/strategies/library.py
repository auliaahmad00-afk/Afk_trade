"""Kumpulan strategi konkret.

Tiap strategi sederhana dan punya beberapa parameter, sehingga "scenario
generator" bisa membuat banyak kombinasi untuk dicari yang winrate-nya tinggi.
"""

from __future__ import annotations

from typing import Any, Dict, Type

import numpy as np
import pandas as pd

from .base import Strategy


def _rsi(close: pd.Series, period: int) -> pd.Series:
    """Hitung Relative Strength Index (Wilder)."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential moving average."""
    return series.ewm(span=period, adjust=False).mean()


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    """Average True Range (Wilder) - ukuran volatilitas, dipakai Supertrend."""
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


class MACrossStrategy(Strategy):
    """Moving-average crossover: long saat MA cepat > MA lambat, short sebaliknya."""

    name = "ma_cross"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        fast = int(self.params["fast"])
        slow = int(self.params["slow"])
        if fast >= slow:
            return pd.Series(0, index=df.index, dtype=int)
        ma_fast = df["close"].rolling(fast).mean()
        ma_slow = df["close"].rolling(slow).mean()
        sig = pd.Series(0, index=df.index, dtype=int)
        sig[ma_fast > ma_slow] = 1
        sig[ma_fast < ma_slow] = -1
        return sig.fillna(0).astype(int)


class RSIReversionStrategy(Strategy):
    """Mean reversion: long saat oversold, short saat overbought."""

    name = "rsi_reversion"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        period = int(self.params["period"])
        oversold = float(self.params["oversold"])
        overbought = float(self.params["overbought"])
        rsi = _rsi(df["close"], period)
        sig = pd.Series(0, index=df.index, dtype=int)
        sig[rsi < oversold] = 1
        sig[rsi > overbought] = -1
        return sig.astype(int)


class BreakoutStrategy(Strategy):
    """Donchian breakout: long saat tembus tertinggi N bar, short saat tembus terendah."""

    name = "breakout"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        lookback = int(self.params["lookback"])
        # Gunakan nilai sampai bar sebelumnya agar tidak melihat masa depan.
        upper = df["high"].rolling(lookback).max().shift(1)
        lower = df["low"].rolling(lookback).min().shift(1)
        sig = pd.Series(0, index=df.index, dtype=int)
        sig[df["close"] > upper] = 1
        sig[df["close"] < lower] = -1
        return sig.fillna(0).astype(int)


class MACDStrategy(Strategy):
    """Trend-following: long saat garis MACD di atas garis sinyal, short sebaliknya.

    MACD = EMA(fast) - EMA(slow); sinyal = EMA(MACD, signal).
    """

    name = "macd"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        fast = int(self.params["fast"])
        slow = int(self.params["slow"])
        signal = int(self.params["signal"])
        if fast >= slow:
            return pd.Series(0, index=df.index, dtype=int)
        macd = _ema(df["close"], fast) - _ema(df["close"], slow)
        macd_signal = _ema(macd, signal)
        sig = pd.Series(0, index=df.index, dtype=int)
        sig[macd > macd_signal] = 1
        sig[macd < macd_signal] = -1
        return sig.astype(int)


class SupertrendStrategy(Strategy):
    """Trend-following berbasis ATR. Mengikuti arah tren selama belum berbalik.

    Saat harga menembus band ATR ke atas -> tren naik (long); ke bawah -> short.
    Sangat cocok untuk aset yang trending kuat seperti XAUUSD (emas).
    """

    name = "supertrend"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        period = int(self.params["period"])
        mult = float(self.params["multiplier"])

        atr = _atr(df, period)
        hl2 = (df["high"] + df["low"]) / 2.0
        upper = (hl2 + mult * atr).to_numpy()
        lower = (hl2 - mult * atr).to_numpy()
        close = df["close"].to_numpy()
        n = len(df)

        direction = np.ones(n, dtype=int)  # 1 = uptrend, -1 = downtrend
        final_upper = np.copy(upper)
        final_lower = np.copy(lower)

        for i in range(1, n):
            # Band mengetat searah tren agar tidak mudah ter-flip oleh noise.
            final_upper[i] = (
                min(upper[i], final_upper[i - 1])
                if close[i - 1] <= final_upper[i - 1]
                else upper[i]
            )
            final_lower[i] = (
                max(lower[i], final_lower[i - 1])
                if close[i - 1] >= final_lower[i - 1]
                else lower[i]
            )
            if close[i] > final_upper[i - 1]:
                direction[i] = 1
            elif close[i] < final_lower[i - 1]:
                direction[i] = -1
            else:
                direction[i] = direction[i - 1]

        sig = pd.Series(direction, index=df.index, dtype=int)
        # Nol-kan periode awal saat ATR belum terbentuk.
        sig[atr.isna().to_numpy()] = 0
        return sig.astype(int)


class MomentumStrategy(Strategy):
    """Trend-following sederhana: ikut arah momentum harga.

    Long jika harga > EMA dan naik (rate-of-change positif) di atas ambang,
    short jika sebaliknya. Filter EMA mencegah masuk melawan tren utama.
    """

    name = "momentum"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        lookback = int(self.params["lookback"])
        ema_period = int(self.params["ema"])
        threshold = float(self.params.get("threshold", 0.0))

        close = df["close"]
        roc = close.pct_change(lookback)
        ema = _ema(close, ema_period)
        sig = pd.Series(0, index=df.index, dtype=int)
        sig[(roc > threshold) & (close > ema)] = 1
        sig[(roc < -threshold) & (close < ema)] = -1
        return sig.fillna(0).astype(int)


STRATEGY_REGISTRY: Dict[str, Type[Strategy]] = {
    MACrossStrategy.name: MACrossStrategy,
    RSIReversionStrategy.name: RSIReversionStrategy,
    BreakoutStrategy.name: BreakoutStrategy,
    MACDStrategy.name: MACDStrategy,
    SupertrendStrategy.name: SupertrendStrategy,
    MomentumStrategy.name: MomentumStrategy,
}


def build_strategy(name: str, params: Dict[str, Any]) -> Strategy:
    """Buat instance strategi berdasarkan nama terdaftar."""
    if name not in STRATEGY_REGISTRY:
        raise KeyError(f"Strategi '{name}' tidak dikenal. Pilihan: {list(STRATEGY_REGISTRY)}")
    return STRATEGY_REGISTRY[name](**params)
