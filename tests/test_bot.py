from afk_trade.bot import TradingBot
from afk_trade.config import BotConfig
from afk_trade.data.feed import synthetic_ohlc


def test_bot_runs_end_to_end_winrate_mode():
    config = BotConfig(bars=1500, selection_mode="winrate",
                       win_threshold=0.60, min_trades=10)
    bot = TradingBot(config)
    df = synthetic_ohlc(bars=1500)
    report = bot.run(df)

    assert len(report.all_results) > 0
    # Mode winrate -> hasil terurut dari winrate tertinggi.
    winrates = [r.winrate for r in report.all_results]
    assert winrates == sorted(winrates, reverse=True)
    for w in report.winners:
        assert w.winrate >= config.win_threshold
        assert w.n_trades >= config.min_trades


def test_bot_profit_factor_mode_default():
    config = BotConfig(bars=1500, pf_threshold=1.2, min_trades=10)
    assert config.selection_mode == "profit_factor"
    bot = TradingBot(config)
    df = synthetic_ohlc(bars=1500)
    report = bot.run(df)

    # Mode default profit_factor -> hasil terurut dari profit factor tertinggi.
    pfs = [r.profit_factor for r in report.all_results]
    assert pfs == sorted(pfs, reverse=True)
    for w in report.winners:
        assert w.profit_factor >= config.pf_threshold
        assert w.n_trades >= config.min_trades


def test_high_threshold_may_select_nothing_but_not_crash():
    config = BotConfig(bars=1500, win_threshold=0.999, min_trades=50)
    bot = TradingBot(config)
    df = synthetic_ohlc(bars=1500)
    report = bot.run(df)
    # Tidak ada eksekusi jika tidak ada pemenang.
    assert len(report.executed) == len(
        [w for w in report.winners if w.last_signal != 0]
    )
