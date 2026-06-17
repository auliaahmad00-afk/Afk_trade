import numpy as np
import pandas as pd

from afk_trade.config import BotConfig
from afk_trade.scenarios.generator import generate_scenarios
from afk_trade.strategies import (
    MACDStrategy,
    MomentumStrategy,
    SupertrendStrategy,
    build_strategy,
)


def _trending_df(n=300, up=True):
    """Harga tren naik/turun + sedikit noise -> menguji strategi trend-following."""
    rng = np.random.default_rng(0)
    drift = 1.0 if up else -1.0
    close = 2000 + np.cumsum(drift + rng.normal(0, 0.3, n))
    s = pd.Series(close)
    return pd.DataFrame(
        {"open": s, "high": s + 0.5, "low": s - 0.5, "close": s, "volume": 1.0}
    )


def test_supertrend_follows_uptrend():
    df = _trending_df(up=True)
    sig = SupertrendStrategy(period=10, multiplier=3.0).generate_signals(df)
    # Mayoritas bar di tren naik harus long.
    assert sig.iloc[50:].mean() > 0.5


def test_supertrend_follows_downtrend():
    df = _trending_df(up=False)
    sig = SupertrendStrategy(period=10, multiplier=3.0).generate_signals(df)
    assert sig.iloc[50:].mean() < -0.5


def test_macd_produces_valid_signals():
    # Crossover MACD/sinyal berosilasi (wajar), jadi cukup pastikan sinyal valid
    # dan ada posisi long yang dihasilkan saat tren naik.
    df = _trending_df(up=True)
    sig = MACDStrategy(fast=12, slow=26, signal=9).generate_signals(df)
    assert set(sig.unique()).issubset({-1, 0, 1})
    assert (sig == 1).sum() > 0


def test_momentum_signals_valid_range():
    df = _trending_df(up=True)
    sig = MomentumStrategy(lookback=20, ema=50, threshold=0.0).generate_signals(df)
    assert set(sig.unique()).issubset({-1, 0, 1})
    assert sig.iloc[60:].mean() > 0


def test_build_trend_strategies_registered():
    for name in ("macd", "supertrend", "momentum"):
        s = build_strategy(name, _default_params(name))
        assert s.name == name


def test_generate_scenarios_includes_trend():
    scenarios = generate_scenarios(["supertrend", "macd", "momentum"])
    names = {s.strategy_name for s in scenarios}
    assert names == {"supertrend", "macd", "momentum"}
    assert len(scenarios) > 0


def test_xauusd_preset():
    cfg = BotConfig.preset("xauusd", starting_balance=100)
    assert cfg.symbol == "XAUUSD"
    assert cfg.starting_balance == 100
    assert "supertrend" in cfg.strategies


def _default_params(name):
    return {
        "macd": {"fast": 12, "slow": 26, "signal": 9},
        "supertrend": {"period": 10, "multiplier": 3.0},
        "momentum": {"lookback": 20, "ema": 50, "threshold": 0.0},
    }[name]
