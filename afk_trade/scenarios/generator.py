"""Pembuat skenario.

Sebuah "skenario" = satu strategi dengan satu set parameter konkret. Generator
membuat banyak kombinasi (grid) untuk tiap strategi, sehingga bot bisa
mengevaluasi ratusan skenario dan memilih yang winrate-nya > ambang.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List

from ..strategies import Strategy, build_strategy

# Grid parameter default untuk tiap strategi. Bisa diperluas sesuka hati.
DEFAULT_PARAM_GRID: Dict[str, Dict[str, List[Any]]] = {
    "ma_cross": {
        "fast": [5, 10, 20, 30],
        "slow": [50, 100, 150, 200],
    },
    "rsi_reversion": {
        "period": [7, 14, 21],
        "oversold": [20, 25, 30],
        "overbought": [70, 75, 80],
    },
    "breakout": {
        "lookback": [10, 20, 40, 55, 80],
    },
    # --- strategi trend-following ---
    "macd": {
        "fast": [8, 12, 16],
        "slow": [21, 26, 34],
        "signal": [9],
    },
    "supertrend": {
        "period": [7, 10, 14],
        "multiplier": [2.0, 3.0, 4.0],
    },
    "momentum": {
        "lookback": [10, 20, 40],
        "ema": [50, 100, 200],
        "threshold": [0.0, 0.005],
    },
}


@dataclass(frozen=True)
class Scenario:
    """Satu skenario: nama strategi + parameter."""

    strategy_name: str
    params: Dict[str, Any]

    def build(self) -> Strategy:
        return build_strategy(self.strategy_name, dict(self.params))

    def label(self) -> str:
        return self.build().label()


def _grid_combinations(grid: Dict[str, List[Any]]) -> Iterable[Dict[str, Any]]:
    keys = list(grid.keys())
    for combo in itertools.product(*(grid[k] for k in keys)):
        yield dict(zip(keys, combo))


def generate_scenarios(
    strategy_names: Iterable[str],
    param_grid: Dict[str, Dict[str, List[Any]]] | None = None,
) -> List[Scenario]:
    """Bangun daftar skenario dari grid parameter untuk strategi yang dipilih."""
    grid = param_grid or DEFAULT_PARAM_GRID
    scenarios: List[Scenario] = []
    for name in strategy_names:
        if name not in grid:
            continue
        for params in _grid_combinations(grid[name]):
            # Lewati kombinasi MA yang tidak valid (fast >= slow).
            if name == "ma_cross" and params["fast"] >= params["slow"]:
                continue
            scenarios.append(Scenario(strategy_name=name, params=params))
    return scenarios
