from afk_trade.backtest.engine import BacktestResult
from afk_trade.selection.selector import select_scenarios


def _res(label, winrate, pf, n_trades, expectancy=0.0, total_return=0.0):
    return BacktestResult(
        label=label, n_trades=n_trades, wins=int(winrate * n_trades),
        losses=n_trades - int(winrate * n_trades), winrate=winrate,
        total_return=total_return, avg_trade_return=expectancy, profit_factor=pf,
        max_drawdown=0.0, last_signal=1,
    )


def test_profit_factor_mode_picks_profitable_low_winrate():
    results = [
        _res("trend", 0.42, 1.5, 200, total_return=0.7),  # winrate rendah tapi profit -> lolos
        _res("flat", 0.90, 1.0, 200),                     # winrate tinggi tapi PF=1 -> ditolak
        _res("fewtrades", 0.50, 2.0, 5),                  # PF tinggi tapi trade kurang -> ditolak
    ]
    chosen = select_scenarios(results, mode="profit_factor", pf_threshold=1.3, min_trades=20)
    assert [c.label for c in chosen] == ["trend"]


def test_profit_factor_mode_orders_by_pf():
    results = [
        _res("a", 0.4, 1.4, 100),
        _res("b", 0.4, 1.9, 100),
    ]
    chosen = select_scenarios(results, mode="profit_factor", pf_threshold=1.3, min_trades=20)
    assert [c.label for c in chosen] == ["b", "a"]


def test_winrate_mode_still_works():
    results = [_res("hi", 0.85, 1.1, 50), _res("lo", 0.60, 3.0, 50)]
    chosen = select_scenarios(results, mode="winrate", win_threshold=0.80, min_trades=20)
    assert [c.label for c in chosen] == ["hi"]


def test_expectancy_mode():
    results = [
        _res("pos", 0.4, 1.5, 100, expectancy=0.002),
        _res("neg", 0.4, 0.9, 100, expectancy=-0.001),
    ]
    chosen = select_scenarios(results, mode="expectancy", min_expectancy=0.0, min_trades=20)
    assert [c.label for c in chosen] == ["pos"]
