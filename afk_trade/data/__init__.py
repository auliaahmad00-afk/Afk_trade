from .feed import get_data, synthetic_ohlc

__all__ = ["get_data", "synthetic_ohlc"]

# Catatan: untuk menarik data nyata via Yahoo Finance, pasang `pip install yfinance`.
# get_data() akan otomatis memakainya (urutan: MT5 -> CSV -> yfinance -> sintetis).
