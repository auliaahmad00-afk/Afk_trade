"""Penyaring & pemeringkat skenario berdasarkan winrate."""

from __future__ import annotations

from typing import List

from ..backtest.engine import BacktestResult


def rank_results(results: List[BacktestResult]) -> List[BacktestResult]:
    """Urutkan dari winrate tertinggi; jika seri, pakai total_return lalu jumlah trade."""
    return sorted(
        results,
        key=lambda r: (r.winrate, r.total_return, r.n_trades),
        reverse=True,
    )


def select_winners(
    results: List[BacktestResult],
    win_threshold: float = 0.80,
    min_trades: int = 20,
) -> List[BacktestResult]:
    """Ambil hanya skenario dengan winrate >= ambang dan jumlah trade cukup.

    Hasil sudah terurut dari yang terbaik.
    """
    winners = [r for r in results if r.is_selectable(win_threshold, min_trades)]
    return rank_results(winners)
