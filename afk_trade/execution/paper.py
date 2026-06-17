"""Broker paper-trading: simulasikan order dengan uang virtual.

Tidak menyentuh akun/uang sungguhan. Cocok untuk menguji apakah skenario
terpilih benar-benar menghasilkan sebelum beralih ke live.
"""

from __future__ import annotations

from typing import Dict, List

from .broker import Broker, Order, Position


class PaperBroker(Broker):
    def __init__(self, starting_balance: float = 10_000.0):
        self.starting_balance = float(starting_balance)
        self.balance = float(starting_balance)  # kas terealisasi
        self.positions: Dict[str, Position] = {}
        self.order_history: List[Order] = []

    # --- helper internal ---
    def _realize(self, symbol: str, price: float) -> None:
        """Tutup posisi yang ada dan bukukan PnL ke saldo."""
        pos = self.positions.pop(symbol, None)
        if pos is None:
            return
        pnl = pos.side * (price - pos.entry_price) * pos.volume
        self.balance += pnl

    # --- API broker ---
    def market_order(self, symbol: str, side: int, volume: float, price: float, label: str = "") -> Order:
        if side not in (1, -1):
            raise ValueError("side harus 1 (buy) atau -1 (sell)")
        # Jika sudah ada posisi berlawanan/berbeda, realisasikan dulu lalu balik arah.
        existing = self.positions.get(symbol)
        if existing is not None and existing.side != side:
            self._realize(symbol, price)
            existing = None
        if existing is None:
            self.positions[symbol] = Position(symbol, side, volume, price)
        else:
            # Tambah ke posisi searah: rata-ratakan harga masuk.
            total_vol = existing.volume + volume
            existing.entry_price = (
                existing.entry_price * existing.volume + price * volume
            ) / total_vol
            existing.volume = total_vol

        order = Order(symbol, side, volume, price, label)
        self.order_history.append(order)
        return order

    def close(self, symbol: str, price: float) -> None:
        self._realize(symbol, price)

    def equity(self, mark_prices: Dict[str, float]) -> float:
        eq = self.balance
        for symbol, pos in self.positions.items():
            mark = mark_prices.get(symbol, pos.entry_price)
            eq += pos.side * (mark - pos.entry_price) * pos.volume
        return eq

    def summary(self, mark_prices: Dict[str, float] | None = None) -> dict:
        mark_prices = mark_prices or {}
        return {
            "starting_balance": self.starting_balance,
            "balance": round(self.balance, 2),
            "equity": round(self.equity(mark_prices), 2),
            "open_positions": {
                s: {"side": p.side, "volume": p.volume, "entry": p.entry_price}
                for s, p in self.positions.items()
            },
            "orders_executed": len(self.order_history),
        }
