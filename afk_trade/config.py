"""Konfigurasi bot."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class BotConfig:
    """Pengaturan utama bot.

    Attributes:
        symbol: simbol/pair yang diperdagangkan, mis. "EURUSD".
        timeframe: kerangka waktu, mis. "M15", "H1" (dipakai oleh feed MT5).
        bars: jumlah bar historis yang diambil untuk backtest.
        selection_mode: kriteria pemilihan skenario:
            "profit_factor" (default) | "winrate" | "expectancy".
        win_threshold: ambang minimal winrate (dipakai saat mode "winrate").
        pf_threshold: ambang minimal profit factor (dipakai saat mode "profit_factor").
        min_expectancy: ambang minimal ekspektasi per trade (mode "expectancy").
        min_trades: jumlah trade minimal agar statistik skenario dianggap valid.
        cost_per_trade: biaya/spread per trade dalam fraksi harga (mis. 0.0001 = 1 pip-ish).
        starting_balance: saldo awal untuk paper trading.
        risk_per_trade: fraksi saldo yang dipertaruhkan tiap trade.
        live: jika True, eksekusi ke broker MT5 sungguhan (default False = paper).
    """

    symbol: str = "EURUSD"
    timeframe: str = "H1"
    bars: int = 2000
    selection_mode: str = "profit_factor"
    win_threshold: float = 0.80
    pf_threshold: float = 1.3
    min_expectancy: float = 0.0
    min_trades: int = 20
    cost_per_trade: float = 0.0001
    starting_balance: float = 10_000.0
    risk_per_trade: float = 0.02
    leverage: float = 1.0  # daya ungkit broker (mis. emas/forex CFD ~1:100)
    # Validasi out-of-sample (train/test split) untuk melawan overfitting.
    validate: bool = True   # pilih skenario di train, konfirmasi di test
    test_ratio: float = 0.3  # fraksi bar terakhir untuk test
    # Agregasi sinyal antar skenario terpilih (voting berbobot).
    vote_weight: str = "profit_factor"  # equal | profit_factor | winrate | expectancy
    min_agreement: float = 0.0          # ambang konsensus 0..1; di bawahnya -> FLAT
    scale_by_confidence: bool = False   # skala ukuran posisi dengan derajat konsensus
    live: bool = False
    # Daftar nama strategi yang diikutkan dalam pencarian skenario.
    strategies: List[str] = field(
        default_factory=lambda: [
            "ma_cross", "rsi_reversion", "breakout",
            "macd", "supertrend", "momentum",
        ]
    )

    def __post_init__(self) -> None:
        if not (0.0 < self.win_threshold <= 1.0):
            raise ValueError("win_threshold harus di antara 0 dan 1")
        if self.min_trades < 1:
            raise ValueError("min_trades minimal 1")
        if self.risk_per_trade <= 0:
            raise ValueError("risk_per_trade harus > 0")
        if self.selection_mode not in ("profit_factor", "winrate", "expectancy"):
            raise ValueError(
                "selection_mode harus 'profit_factor', 'winrate', atau 'expectancy'"
            )
        if self.vote_weight not in ("equal", "profit_factor", "winrate", "expectancy"):
            raise ValueError(
                "vote_weight harus 'equal', 'profit_factor', 'winrate', atau 'expectancy'"
            )
        if not (0.0 <= self.min_agreement <= 1.0):
            raise ValueError("min_agreement harus di antara 0 dan 1")
        if not (0.0 < self.test_ratio < 1.0):
            raise ValueError("test_ratio harus di antara 0 dan 1")

    @classmethod
    def preset(cls, name: str, **overrides) -> "BotConfig":
        """Ambil konfigurasi siap-pakai untuk sebuah pair. Override sesuka hati.

        Contoh: BotConfig.preset("xauusd", starting_balance=100)
        """
        key = name.lower()
        if key not in PRESETS:
            raise KeyError(f"Preset '{name}' tidak ada. Pilihan: {list(PRESETS)}")
        params = {**PRESETS[key], **overrides}
        return cls(**params)


# Preset khusus per pair. XAUUSD (emas) lebih volatil & spread lebih lebar,
# serta lebih cocok dengan strategi trend-following.
PRESETS = {
    "xauusd": dict(
        symbol="XAUUSD",
        timeframe="H1",
        # Emas trending kuat -> utamakan strategi trend-following.
        strategies=["supertrend", "macd", "momentum", "breakout", "ma_cross"],
        cost_per_trade=0.00015,  # ~spread emas relatif terhadap harga
        leverage=100.0,          # tipikal gold CFD; tanpa ini $100 tak cukup beli emas
        selection_mode="profit_factor",
        pf_threshold=1.3,
        min_trades=20,
    ),
    "eurusd": dict(
        symbol="EURUSD",
        timeframe="H1",
        strategies=["ma_cross", "rsi_reversion", "breakout", "macd", "momentum"],
        cost_per_trade=0.0001,
    ),
}
