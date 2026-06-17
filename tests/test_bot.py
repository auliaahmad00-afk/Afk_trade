from afk_trade.bot import TradingBot
from afk_trade.config import BotConfig
from afk_trade.data.feed import synthetic_ohlc


def test_bot_runs_end_to_end_on_synthetic_data():
    config = BotConfig(bars=1500, win_threshold=0.60, min_trades=10)
    bot = TradingBot(config)
    df = synthetic_ohlc(bars=1500)
    report = bot.run(df)

    assert len(report.all_results) > 0
    # Hasil terurut dari winrate tertinggi.
    winrates = [r.winrate for r in report.all_results]
    assert winrates == sorted(winrates, reverse=True)
    # Semua pemenang memenuhi syarat.
    for w in report.winners:
        assert w.winrate >= config.win_threshold
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
