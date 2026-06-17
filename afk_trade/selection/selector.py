"""Penyaring & pemeringkat skenario.

Mendukung beberapa kriteria seleksi karena tiap jenis strategi punya profil
berbeda:
- "winrate"       : pilih yang sering menang (cocok untuk mean-reversion).
- "profit_factor" : pilih yang paling profitable (cocok untuk trend-following,
                    yang winrate-nya rendah tapi profitnya besar).
- "expectancy"    : pilih yang ekspektasi profit per trade-nya tertinggi.
"""

from __future__ import annotations

from typing import Callable, List

from ..backtest.engine import BacktestResult

# Kunci pengurutan (skor lebih tinggi = lebih baik) per mode.
_RANK_KEYS: dict[str, Callable[[BacktestResult], tuple]] = {
    "winrate": lambda r: (r.winrate, r.profit_factor, r.total_return),
    "profit_factor": lambda r: (r.profit_factor, r.total_return, r.winrate),
    "expectancy": lambda r: (r.avg_trade_return, r.profit_factor, r.n_trades),
}


def rank_results(
    results: List[BacktestResult], mode: str = "winrate"
) -> List[BacktestResult]:
    """Urutkan hasil dari yang terbaik menurut `mode`."""
    key = _RANK_KEYS.get(mode, _RANK_KEYS["winrate"])
    return sorted(results, key=key, reverse=True)


def select_winners(
    results: List[BacktestResult],
    win_threshold: float = 0.80,
    min_trades: int = 20,
) -> List[BacktestResult]:
    """(Mode winrate) Ambil skenario winrate >= ambang & jumlah trade cukup."""
    winners = [r for r in results if r.is_selectable(win_threshold, min_trades)]
    return rank_results(winners, mode="winrate")


def meets_criteria(
    result: BacktestResult,
    *,
    mode: str = "profit_factor",
    min_trades: int = 20,
    win_threshold: float = 0.80,
    pf_threshold: float = 1.3,
    min_expectancy: float = 0.0,
) -> bool:
    """Apakah SATU hasil backtest memenuhi kriteria seleksi `mode`?

    - winrate       : winrate >= win_threshold
    - profit_factor : profit_factor >= pf_threshold
    - expectancy    : avg_trade_return >= min_expectancy
    Semua mode mensyaratkan jumlah trade >= min_trades.
    """
    if result.n_trades < min_trades:
        return False
    if mode == "winrate":
        return result.winrate >= win_threshold
    if mode == "profit_factor":
        return result.profit_factor >= pf_threshold
    if mode == "expectancy":
        return result.avg_trade_return >= min_expectancy
    raise ValueError(f"mode seleksi tidak dikenal: {mode}")


def select_scenarios(
    results: List[BacktestResult],
    *,
    mode: str = "profit_factor",
    min_trades: int = 20,
    win_threshold: float = 0.80,
    pf_threshold: float = 1.3,
    min_expectancy: float = 0.0,
) -> List[BacktestResult]:
    """Pilih skenario yang memenuhi kriteria `mode`, terurut dari terbaik."""
    chosen = [
        r
        for r in results
        if meets_criteria(
            r,
            mode=mode,
            min_trades=min_trades,
            win_threshold=win_threshold,
            pf_threshold=pf_threshold,
            min_expectancy=min_expectancy,
        )
    ]
    return rank_results(chosen, mode=mode)
