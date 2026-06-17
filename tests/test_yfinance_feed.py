"""Test parsing data yfinance tanpa akses jaringan (memakai DataFrame palsu)."""

import pandas as pd

from afk_trade.data.feed import _normalize_yf, get_data


def _fake_yf_daily():
    """Tiru output yf.download untuk data harian (index 'Date', kolom datar)."""
    idx = pd.date_range("2024-01-01", periods=5, freq="D", name="Date")
    return pd.DataFrame(
        {
            "Open": [2000, 2010, 2020, 2030, 2040],
            "High": [2005, 2015, 2025, 2035, 2045],
            "Low": [1995, 2005, 2015, 2025, 2035],
            "Close": [2002, 2012, 2022, 2032, 2042],
            "Adj Close": [2002, 2012, 2022, 2032, 2042],
            "Volume": [100, 110, 120, 130, 140],
        },
        index=idx,
    )


def _fake_yf_multiindex():
    """Tiru yfinance versi baru: kolom MultiIndex (field, ticker), index 'Datetime'."""
    idx = pd.date_range("2024-01-01", periods=3, freq="h", name="Datetime")
    cols = pd.MultiIndex.from_product(
        [["Open", "High", "Low", "Close", "Volume"], ["GC=F"]]
    )
    data = [
        [2000, 2005, 1995, 2002, 100],
        [2002, 2008, 1998, 2006, 110],
        [2006, 2010, 2001, 2009, 120],
    ]
    return pd.DataFrame(data, index=idx, columns=cols)


def test_normalize_daily():
    out = _normalize_yf(_fake_yf_daily(), bars=1000)
    assert list(out.columns) == ["time", "open", "high", "low", "close", "volume"]
    assert len(out) == 5
    assert out["close"].iloc[-1] == 2042
    assert pd.api.types.is_datetime64_any_dtype(out["time"])


def test_normalize_multiindex_columns():
    out = _normalize_yf(_fake_yf_multiindex(), bars=1000)
    assert len(out) == 3
    assert out["open"].iloc[0] == 2000
    assert out["volume"].iloc[-1] == 120


def test_normalize_respects_bars_limit():
    out = _normalize_yf(_fake_yf_daily(), bars=2)
    assert len(out) == 2
    # Mengambil bar TERAKHIR (paling baru).
    assert out["close"].tolist() == [2032, 2042]


def test_normalize_empty_returns_none():
    assert _normalize_yf(pd.DataFrame(), bars=10) is None
    assert _normalize_yf(None, bars=10) is None


def test_get_data_falls_back_to_synthetic_without_network():
    # yfinance tidak terpasang / dimatikan -> tetap dapat data sintetis.
    df = get_data("XAUUSD", "H1", bars=300, allow_yfinance=False)
    assert len(df) == 300
    assert {"open", "high", "low", "close"}.issubset(df.columns)
