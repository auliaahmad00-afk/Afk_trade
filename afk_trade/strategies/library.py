"""Kumpulan strategi konkret.

Tiap strategi sederhana dan punya beberapa parameter, sehingga "scenario
generator" bisa membuat banyak kombinasi untuk dicari yang winrate-nya tinggi.
"""

from __future__ import annotations

from typing import Any, Dict, Type

import numpy as np
import pandas as pd

from .base import Strategy


def _rsi(close: pd.Series, period: int) -> pd.Series:
    """Hitung Relative Strength Index (Wilder)."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


class MACrossStrategy(Strategy):
    """Moving-average crossover: long saat MA cepat > MA lambat, short sebaliknya."""

    name = "ma_cross"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        fast = int(self.params["fast"])
        slow = int(self.params["slow"])
        if fast >= slow:
            return pd.Series(0, index=df.index, dtype=int)
        ma_fast = df["close"].rolling(fast).mean()
        ma_slow = df["close"].rolling(slow).mean()
        sig = pd.Series(0, index=df.index, dtype=int)
        sig[ma_fast > ma_slow] = 1
        sig[ma_fast < ma_slow] = -1
        return sig.fillna(0).astype(int)


class RSIReversionStrategy(Strategy):
    """Mean reversion: long saat oversold, short saat overbought."""

    name = "rsi_reversion"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        period = int(self.params["period"])
        oversold = float(self.params["oversold"])
        overbought = float(self.params["overbought"])
        rsi = _rsi(df["close"], period)
        sig = pd.Series(0, index=df.index, dtype=int)
        sig[rsi < oversold] = 1
        sig[rsi > overbought] = -1
        return sig.astype(int)


class BreakoutStrategy(Strategy):
    """Donchian breakout: long saat tembus tertinggi N bar, short saat tembus terendah."""

    name = "breakout"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        lookback = int(self.params["lookback"])
        # Gunakan nilai sampai bar sebelumnya agar tidak melihat masa depan.
        upper = df["high"].rolling(lookback).max().shift(1)
        lower = df["low"].rolling(lookback).min().shift(1)
        sig = pd.Series(0, index=df.index, dtype=int)
        sig[df["close"] > upper] = 1
        sig[df["close"] < lower] = -1
        return sig.fillna(0).astype(int)


STRATEGY_REGISTRY: Dict[str, Type[Strategy]] = {
    MACrossStrategy.name: MACrossStrategy,
    RSIReversionStrategy.name: RSIReversionStrategy,
    BreakoutStrategy.name: BreakoutStrategy,
}


def build_strategy(name: str, params: Dict[str, Any]) -> Strategy:
    """Buat instance strategi berdasarkan nama terdaftar."""
    if name not in STRATEGY_REGISTRY:
        raise KeyError(f"Strategi '{name}' tidak dikenal. Pilihan: {list(STRATEGY_REGISTRY)}")
    return STRATEGY_REGISTRY[name](**params)
