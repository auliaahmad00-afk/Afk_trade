"""Antarmuka dasar strategi."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

import pandas as pd


class Strategy(ABC):
    """Strategi mengubah data OHLC menjadi sinyal posisi per-bar.

    Sinyal bernilai:
         1  -> ingin posisi long (beli)
        -1  -> ingin posisi short (jual)
         0  -> flat (tidak ada posisi)

    Sinyal mewakili posisi yang DIINGINKAN pada bar tersebut. Backtester yang
    menggeser sinyal satu bar ke depan agar tidak terjadi lookahead bias.
    """

    name: str = "base"

    def __init__(self, **params: Any) -> None:
        self.params: Dict[str, Any] = params

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Kembalikan pd.Series berisi {-1, 0, 1} sepanjang df."""

    def label(self) -> str:
        """Label ringkas untuk skenario, mis. 'ma_cross(fast=10,slow=50)'."""
        parts = ",".join(f"{k}={v}" for k, v in sorted(self.params.items()))
        return f"{self.name}({parts})"

    def __repr__(self) -> str:  # pragma: no cover - kosmetik
        return self.label()
