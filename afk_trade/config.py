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
        win_threshold: ambang minimal winrate agar skenario dipilih (0.80 = 80%).
        min_trades: jumlah trade minimal agar winrate dianggap valid secara statistik.
        cost_per_trade: biaya/spread per trade dalam fraksi harga (mis. 0.0001 = 1 pip-ish).
        starting_balance: saldo awal untuk paper trading.
        risk_per_trade: fraksi saldo yang dipertaruhkan tiap trade.
        live: jika True, eksekusi ke broker MT5 sungguhan (default False = paper).
    """

    symbol: str = "EURUSD"
    timeframe: str = "H1"
    bars: int = 2000
    win_threshold: float = 0.80
    min_trades: int = 20
    cost_per_trade: float = 0.0001
    starting_balance: float = 10_000.0
    risk_per_trade: float = 0.02
    live: bool = False
    # Daftar nama strategi yang diikutkan dalam pencarian skenario.
    strategies: List[str] = field(
        default_factory=lambda: ["ma_cross", "rsi_reversion", "breakout"]
    )

    def __post_init__(self) -> None:
        if not (0.0 < self.win_threshold <= 1.0):
            raise ValueError("win_threshold harus di antara 0 dan 1")
        if self.min_trades < 1:
            raise ValueError("min_trades minimal 1")
        if self.risk_per_trade <= 0:
            raise ValueError("risk_per_trade harus > 0")
