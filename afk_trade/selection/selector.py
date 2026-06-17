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


def select_scenarios(
    results: List[BacktestResult],
    *,
    mode: str = "profit_factor",
    min_trades: int = 20,
    win_threshold: float = 0.80,
    pf_threshold: float = 1.3,
    min_expectancy: float = 0.0,
) -> List[BacktestResult]:
    """Pilih skenario sesuai `mode`. Semua mode tetap wajib `min_trades`.

    - winrate       : winrate >= win_threshold
    - profit_factor : profit_factor >= pf_threshold
    - expectancy    : avg_trade_return >= min_expectancy
    """
    eligible = [r for r in results if r.n_trades >= min_trades]

    if mode == "winrate":
        chosen = [r for r in eligible if r.winrate >= win_threshold]
    elif mode == "profit_factor":
        chosen = [r for r in eligible if r.profit_factor >= pf_threshold]
    elif mode == "expectancy":
        chosen = [r for r in eligible if r.avg_trade_return >= min_expectancy]
    else:
        raise ValueError(f"mode seleksi tidak dikenal: {mode}")

    return rank_results(chosen, mode=mode)
