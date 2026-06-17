"""Validasi out-of-sample untuk melawan overfitting.

Alur: pilih skenario pada data train, lalu uji kembali skenario itu pada data
test. Skenario disebut **robust** jika tetap memenuhi kriteria seleksi pada
test (data yang tidak dipakai saat memilih). Hanya skenario robust yang layak
dieksekusi.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd

from ..backtest.engine import BacktestResult, backtest_scenario
from ..scenarios.generator import Scenario
from ..selection.selector import meets_criteria


@dataclass
class ValidationResult:
    """Perbandingan performa sebuah skenario di train vs test."""

    label: str
    train: BacktestResult
    test: BacktestResult
    robust: bool  # True jika lolos kriteria di train DAN test

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "robust": self.robust,
            "train": {
                "winrate": round(self.train.winrate, 3),
                "pf": round(self.train.profit_factor, 2),
                "ret": round(self.train.total_return, 3),
                "trades": self.train.n_trades,
            },
            "test": {
                "winrate": round(self.test.winrate, 3),
                "pf": round(self.test.profit_factor, 2),
                "ret": round(self.test.total_return, 3),
                "trades": self.test.n_trades,
            },
        }


def validate_scenarios(
    scenarios: List[Scenario],
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    *,
    cost_per_trade: float = 0.0001,
    mode: str = "profit_factor",
    min_trades: int = 20,
    win_threshold: float = 0.80,
    pf_threshold: float = 1.3,
    min_expectancy: float = 0.0,
    test_min_trades: int | None = None,
) -> List[ValidationResult]:
    """Backtest tiap skenario di train & test, tandai yang robust.

    Sebuah skenario robust bila memenuhi kriteria seleksi di kedua periode.
    Karena periode test lebih pendek, ambang jumlah trade untuk test bisa
    diperlonggar lewat `test_min_trades` (default: setengah dari min_trades).

    Hasil hanya berisi skenario yang **lolos di train** (kandidat), masing-masing
    dengan flag `robust` yang menyatakan apakah ia juga lolos di test.
    """
    if test_min_trades is None:
        test_min_trades = max(1, min_trades // 2)

    criteria = dict(
        mode=mode,
        win_threshold=win_threshold,
        pf_threshold=pf_threshold,
        min_expectancy=min_expectancy,
    )

    out: List[ValidationResult] = []
    for s in scenarios:
        train_res = backtest_scenario(s, train_df, cost_per_trade)
        if not meets_criteria(train_res, min_trades=min_trades, **criteria):
            continue  # bukan kandidat -> abaikan
        test_res = backtest_scenario(s, test_df, cost_per_trade)
        robust = meets_criteria(test_res, min_trades=test_min_trades, **criteria)
        out.append(
            ValidationResult(
                label=s.label(), train=train_res, test=test_res, robust=robust
            )
        )
    return out
