from afk_trade.backtest.engine import BacktestResult
from afk_trade.scenarios.generator import generate_scenarios
from afk_trade.selection.selector import rank_results, select_winners


def _result(label, winrate, n_trades, total_return=0.0):
    return BacktestResult(
        label=label, n_trades=n_trades, wins=int(winrate * n_trades),
        losses=n_trades - int(winrate * n_trades), winrate=winrate,
        total_return=total_return, avg_trade_return=0.0, profit_factor=1.0,
        max_drawdown=0.0, last_signal=1,
    )


def test_generate_scenarios_skips_invalid_ma():
    scenarios = generate_scenarios(["ma_cross"])
    for s in scenarios:
        assert s.params["fast"] < s.params["slow"]
    assert len(scenarios) > 0


def test_generate_scenarios_multiple_strategies():
    scenarios = generate_scenarios(["ma_cross", "rsi_reversion", "breakout"])
    names = {s.strategy_name for s in scenarios}
    assert names == {"ma_cross", "rsi_reversion", "breakout"}


def test_select_winners_respects_threshold_and_min_trades():
    results = [
        _result("A", 0.90, 50),   # lolos
        _result("B", 0.85, 5),    # winrate ok tapi trade kurang -> ditolak
        _result("C", 0.70, 100),  # winrate kurang -> ditolak
        _result("D", 0.80, 30),   # tepat di ambang -> lolos
    ]
    winners = select_winners(results, win_threshold=0.80, min_trades=20)
    labels = [w.label for w in winners]
    assert labels == ["A", "D"]  # terurut dari winrate tertinggi


def test_rank_results_orders_by_winrate():
    results = [_result("low", 0.5, 30), _result("high", 0.95, 30)]
    ranked = rank_results(results)
    assert ranked[0].label == "high"
