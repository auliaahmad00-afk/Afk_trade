from afk_trade.aggregation.voting import aggregate_signals
from afk_trade.backtest.engine import BacktestResult


def _res(label, last_signal, pf=1.5, winrate=0.5, expectancy=0.001):
    return BacktestResult(
        label=label, n_trades=100, wins=50, losses=50, winrate=winrate,
        total_return=0.1, avg_trade_return=expectancy, profit_factor=pf,
        max_drawdown=0.1, last_signal=last_signal,
    )


def test_majority_long_wins():
    winners = [_res("a", 1), _res("b", 1), _res("c", -1)]
    agg = aggregate_signals(winners, weight_scheme="equal")
    assert agg.direction == 1
    assert agg.n_long == 2 and agg.n_short == 1
    # 2 vs 1 -> confidence (2-1)/3
    assert abs(agg.confidence - 1 / 3) < 1e-9


def test_profit_factor_weight_can_outweigh_count():
    # Satu skenario short dengan PF besar mengalahkan dua long PF kecil.
    winners = [_res("a", 1, pf=1.1), _res("b", 1, pf=1.1), _res("c", -1, pf=10.0)]
    agg = aggregate_signals(winners, weight_scheme="profit_factor")
    assert agg.direction == -1


def test_tie_results_in_flat():
    winners = [_res("a", 1, pf=2.0), _res("b", -1, pf=2.0)]
    agg = aggregate_signals(winners, weight_scheme="profit_factor")
    assert agg.direction == 0
    assert agg.confidence == 0.0


def test_min_agreement_holds_when_consensus_weak():
    # 2 long vs 1 short -> konsensus 33%, di bawah ambang 0.5 -> FLAT.
    winners = [_res("a", 1), _res("b", 1), _res("c", -1)]
    agg = aggregate_signals(winners, weight_scheme="equal", min_agreement=0.5)
    assert agg.direction == 0


def test_all_flat_gives_flat():
    winners = [_res("a", 0), _res("b", 0)]
    agg = aggregate_signals(winners)
    assert agg.direction == 0
    assert agg.total_weight == 0.0


def test_empty_winners_flat():
    agg = aggregate_signals([])
    assert agg.direction == 0
    assert agg.confidence == 0.0
