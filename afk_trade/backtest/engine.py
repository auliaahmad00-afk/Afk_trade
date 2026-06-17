"""Mesin backtest sederhana yang menghitung winrate (probabilitas menang).

Model:
- Sinyal posisi digeser 1 bar ke depan (act-next-bar) untuk mencegah lookahead.
- Return per-bar = posisi * persentase perubahan close.
- Satu "trade" = rangkaian bar berturut-turut dengan arah posisi yang sama.
- Winrate = jumlah trade untung / total trade. Inilah "probabilitas" yang dipakai
  bot untuk menyaring skenario.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd

from ..scenarios.generator import Scenario


@dataclass
class BacktestResult:
    """Ringkasan hasil backtest sebuah skenario."""

    label: str
    n_trades: int
    wins: int
    losses: int
    winrate: float
    total_return: float
    avg_trade_return: float
    profit_factor: float
    max_drawdown: float
    last_signal: int  # sinyal pada bar terakhir (untuk eksekusi)

    def is_selectable(self, win_threshold: float, min_trades: int) -> bool:
        """True jika winrate >= ambang DAN jumlah trade cukup untuk dipercaya."""
        return self.n_trades >= min_trades and self.winrate >= win_threshold

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "n_trades": self.n_trades,
            "winrate": round(self.winrate, 4),
            "total_return": round(self.total_return, 4),
            "avg_trade_return": round(self.avg_trade_return, 5),
            "profit_factor": round(self.profit_factor, 3),
            "max_drawdown": round(self.max_drawdown, 4),
            "last_signal": self.last_signal,
        }


def _max_drawdown(equity: np.ndarray) -> float:
    """Drawdown maksimum dari kurva ekuitas (nilai positif, mis. 0.12 = 12%)."""
    if len(equity) == 0:
        return 0.0
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    return float(-dd.min())


def backtest_signals(
    df: pd.DataFrame,
    signals: pd.Series,
    cost_per_trade: float = 0.0001,
) -> BacktestResult:
    """Backtest dari sinyal mentah. Mengembalikan BacktestResult."""
    close = df["close"].astype(float)
    bar_ret = close.pct_change().fillna(0.0).to_numpy()

    # Posisi efektif: sinyal digeser 1 bar (kita masuk pada bar berikutnya).
    pos = signals.shift(1).fillna(0).to_numpy().astype(int)
    n = len(pos)

    trade_returns: List[float] = []
    i = 0
    while i < n:
        direction = pos[i]
        if direction == 0:
            i += 1
            continue
        start = i
        while i < n and pos[i] == direction:
            i += 1
        # Trade berlangsung dari bar `start` sampai `i-1`.
        gross = float(np.sum(bar_ret[start:i])) * direction
        net = gross - cost_per_trade  # potong biaya/spread sekali per trade
        trade_returns.append(net)

    n_trades = len(trade_returns)
    if n_trades == 0:
        return BacktestResult(
            label="", n_trades=0, wins=0, losses=0, winrate=0.0,
            total_return=0.0, avg_trade_return=0.0, profit_factor=0.0,
            max_drawdown=0.0, last_signal=int(signals.iloc[-1]) if len(signals) else 0,
        )

    arr = np.array(trade_returns)
    wins = int((arr > 0).sum())
    losses = int((arr <= 0).sum())
    winrate = wins / n_trades
    gross_profit = float(arr[arr > 0].sum())
    gross_loss = float(-arr[arr <= 0].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    equity = np.cumprod(1.0 + arr)
    total_return = float(equity[-1] - 1.0)

    return BacktestResult(
        label="",
        n_trades=n_trades,
        wins=wins,
        losses=losses,
        winrate=winrate,
        total_return=total_return,
        avg_trade_return=float(arr.mean()),
        profit_factor=profit_factor,
        max_drawdown=_max_drawdown(equity),
        last_signal=int(signals.iloc[-1]),
    )


def backtest_scenario(
    scenario: Scenario,
    df: pd.DataFrame,
    cost_per_trade: float = 0.0001,
) -> BacktestResult:
    """Bangun strategi dari skenario, hasilkan sinyal, lalu backtest."""
    strategy = scenario.build()
    signals = strategy.generate_signals(df)
    result = backtest_signals(df, signals, cost_per_trade)
    result.label = scenario.label()
    return result
