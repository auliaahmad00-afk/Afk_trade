"""Orkestrator utama: jalankan skenario, hitung probabilitas, eksekusi pemenang."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

from .backtest.engine import BacktestResult, backtest_scenario
from .config import BotConfig
from .data.feed import get_data
from .execution.broker import Broker, Order
from .execution.paper import PaperBroker
from .scenarios.generator import generate_scenarios
from .selection.selector import rank_results, select_winners


@dataclass
class RunReport:
    """Hasil satu putaran penuh bot."""

    all_results: List[BacktestResult]
    winners: List[BacktestResult]
    executed: List[Order]
    broker_summary: dict


class TradingBot:
    def __init__(self, config: Optional[BotConfig] = None, broker: Optional[Broker] = None):
        self.config = config or BotConfig()
        self.broker: Broker = broker or PaperBroker(self.config.starting_balance)

    def evaluate(self, df: pd.DataFrame) -> List[BacktestResult]:
        """Backtest semua skenario pada data, kembalikan hasil terurut."""
        scenarios = generate_scenarios(self.config.strategies)
        results = [
            backtest_scenario(s, df, self.config.cost_per_trade) for s in scenarios
        ]
        return rank_results(results)

    def _position_volume(self, price: float) -> float:
        """Hitung volume sederhana dari risiko per trade (paper)."""
        risk_cash = self.config.starting_balance * self.config.risk_per_trade
        return round(risk_cash / max(price, 1e-9), 2)

    def execute_winners(
        self, winners: List[BacktestResult], price: float
    ) -> List[Order]:
        """Eksekusi sinyal terakhir dari tiap skenario pemenang lewat broker."""
        executed: List[Order] = []
        for w in winners:
            if w.last_signal == 0:
                continue  # skenario menang tapi saat ini tidak memberi sinyal
            volume = self._position_volume(price)
            order = self.broker.market_order(
                symbol=self.config.symbol,
                side=w.last_signal,
                volume=volume,
                price=price,
                label=w.label,
            )
            executed.append(order)
        return executed

    def run(self, df: Optional[pd.DataFrame] = None) -> RunReport:
        """Jalankan pipeline penuh sekali jalan."""
        if df is None:
            df = get_data(
                self.config.symbol, self.config.timeframe, self.config.bars
            )

        results = self.evaluate(df)
        winners = select_winners(
            results, self.config.win_threshold, self.config.min_trades
        )

        last_price = float(df["close"].iloc[-1])
        executed = self.execute_winners(winners, last_price)

        return RunReport(
            all_results=results,
            winners=winners,
            executed=executed,
            broker_summary=(
                self.broker.summary({self.config.symbol: last_price})
                if hasattr(self.broker, "summary")
                else {}
            ),
        )
