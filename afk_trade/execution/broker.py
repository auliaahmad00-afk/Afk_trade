"""Antarmuka broker bersama untuk paper trading maupun live."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Order:
    symbol: str
    side: int          # 1 = buy/long, -1 = sell/short
    volume: float      # ukuran lot/unit
    price: float       # harga eksekusi
    label: str = ""    # skenario sumber sinyal


@dataclass
class Position:
    symbol: str
    side: int
    volume: float
    entry_price: float


class Broker(ABC):
    """Kontrak minimal yang dipakai bot untuk mengeksekusi sinyal."""

    @abstractmethod
    def market_order(self, symbol: str, side: int, volume: float, price: float, label: str = "") -> Order:
        """Buka/ubah posisi pasar."""

    @abstractmethod
    def close(self, symbol: str, price: float) -> None:
        """Tutup posisi pada simbol."""

    @abstractmethod
    def equity(self, mark_prices: dict[str, float]) -> float:
        """Nilai ekuitas saat ini berdasarkan harga pasar terkini."""
