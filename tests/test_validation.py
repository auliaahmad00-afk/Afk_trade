import pandas as pd

from afk_trade.data.feed import synthetic_ohlc
from afk_trade.scenarios.generator import generate_scenarios
from afk_trade.validation.splitter import split_data
from afk_trade.validation.validator import validate_scenarios


def test_split_is_chronological_and_complete():
    df = synthetic_ohlc(bars=1000)
    train, test = split_data(df, test_ratio=0.3)
    assert len(train) == 700
    assert len(test) == 300
    # Train mendahului test secara waktu.
    assert train["time"].iloc[-1] < test["time"].iloc[0]
    # Tidak ada bar yang hilang/tumpang tindih.
    assert len(train) + len(test) == len(df)


def test_split_rejects_bad_ratio():
    df = synthetic_ohlc(bars=100)
    for bad in (0.0, 1.0, -0.1, 1.5):
        try:
            split_data(df, bad)
            assert False, "harus ValueError"
        except ValueError:
            pass


def test_validate_marks_robust_flag():
    df = synthetic_ohlc(bars=2000)
    train, test = split_data(df, 0.3)
    scenarios = generate_scenarios(["supertrend", "macd", "ma_cross", "momentum"])
    results = validate_scenarios(
        scenarios, train, test,
        mode="profit_factor", pf_threshold=1.1, min_trades=10,
    )
    # Hanya skenario yang lolos di train yang dikembalikan.
    for v in results:
        assert v.train.profit_factor >= 1.1
        assert v.train.n_trades >= 10
        # robust hanya True bila test juga lolos.
        if v.robust:
            assert v.test.profit_factor >= 1.1


def test_validate_empty_when_no_candidate():
    df = synthetic_ohlc(bars=1000)
    train, test = split_data(df, 0.3)
    scenarios = generate_scenarios(["ma_cross"])
    # Ambang mustahil -> tak ada kandidat.
    results = validate_scenarios(
        scenarios, train, test,
        mode="profit_factor", pf_threshold=999.0, min_trades=10,
    )
    assert results == []
