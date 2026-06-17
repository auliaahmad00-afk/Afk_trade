import numpy as np
import pandas as pd

from afk_trade.backtest.engine import backtest_signals


def _df_from_close(prices):
    s = pd.Series(prices, dtype=float)
    return pd.DataFrame(
        {"open": s, "high": s, "low": s, "close": s, "volume": 1.0}
    )


def test_winning_long_trade_counts_as_win():
    # Harga naik terus; sinyal long sejak awal -> trade untung.
    df = _df_from_close([1.0, 1.1, 1.2, 1.3, 1.4])
    signals = pd.Series([1, 1, 1, 1, 1])
    res = backtest_signals(df, signals, cost_per_trade=0.0)
    assert res.n_trades == 1
    assert res.wins == 1
    assert res.winrate == 1.0
    assert res.total_return > 0


def test_no_signal_means_no_trades():
    df = _df_from_close([1.0, 1.1, 1.2])
    signals = pd.Series([0, 0, 0])
    res = backtest_signals(df, signals)
    assert res.n_trades == 0
    assert res.winrate == 0.0


def test_cost_turns_marginal_trade_into_loss():
    df = _df_from_close([1.0, 1.001])  # naik 0.1%
    signals = pd.Series([1, 1])
    res = backtest_signals(df, signals, cost_per_trade=0.01)  # biaya 1%
    assert res.losses == 1
    assert res.winrate == 0.0


def test_winrate_mix():
    # Dua trade: satu untung (long saat naik), satu rugi (long saat turun).
    df = _df_from_close([1.0, 1.2, 1.2, 1.0])
    # bar0->flat, masuk long bar1 (naik), keluar, lalu long lagi saat turun
    signals = pd.Series([1, 0, 1, 1])
    res = backtest_signals(df, signals, cost_per_trade=0.0)
    assert res.n_trades == 2
    assert 0.0 < res.winrate < 1.0


def test_last_signal_recorded():
    df = _df_from_close([1.0, 1.1, 1.2])
    signals = pd.Series([0, 1, -1])
    res = backtest_signals(df, signals)
    assert res.last_signal == -1
