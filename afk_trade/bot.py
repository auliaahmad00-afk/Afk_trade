"""Orkestrator utama: jalankan skenario, hitung probabilitas, eksekusi pemenang."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

from .aggregation.voting import AggregatedSignal, aggregate_signals
from .backtest.engine import BacktestResult, backtest_scenario
from .config import BotConfig
from .data.feed import get_data
from .execution.broker import Broker, Order
from .execution.paper import PaperBroker
from .scenarios.generator import generate_scenarios
from .selection.selector import rank_results, select_scenarios


@dataclass
class RunReport:
    """Hasil satu putaran penuh bot."""

    all_results: List[BacktestResult]
    winners: List[BacktestResult]
    aggregated: AggregatedSignal
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
        return rank_results(results, mode=self.config.selection_mode)

    def _position_volume(self, price: float) -> float:
        """Hitung volume (unit/oz) dari risiko per trade dengan memperhitungkan leverage.

        notional = saldo * risk_per_trade * leverage
        volume   = notional / harga
        Dibulatkan ke 4 desimal agar tidak menjadi 0 untuk aset berharga tinggi
        seperti emas pada akun kecil.
        """
        notional = (
            self.config.starting_balance
            * self.config.risk_per_trade
            * self.config.leverage
        )
        return round(notional / max(price, 1e-9), 4)

    def execute_aggregated(
        self, signal: AggregatedSignal, price: float
    ) -> List[Order]:
        """Eksekusi SATU order net hasil voting skenario terpilih."""
        if signal.direction == 0:
            return []  # tidak ada konsensus -> tahan diri
        volume = self._position_volume(price)
        if self.config.scale_by_confidence:
            volume = round(volume * signal.confidence, 4)
        if volume <= 0:
            return []  # akun terlalu kecil / konsensus terlalu lemah
        label = (
            f"VOTE[{signal.weight_scheme}] {signal.n_long}L/{signal.n_short}S "
            f"conf={signal.confidence:.0%}"
        )
        order = self.broker.market_order(
            symbol=self.config.symbol,
            side=signal.direction,
            volume=volume,
            price=price,
            label=label,
        )
        return [order]

    def run(self, df: Optional[pd.DataFrame] = None) -> RunReport:
        """Jalankan pipeline penuh sekali jalan."""
        if df is None:
            df = get_data(
                self.config.symbol, self.config.timeframe, self.config.bars
            )

        results = self.evaluate(df)
        winners = select_scenarios(
            results,
            mode=self.config.selection_mode,
            min_trades=self.config.min_trades,
            win_threshold=self.config.win_threshold,
            pf_threshold=self.config.pf_threshold,
            min_expectancy=self.config.min_expectancy,
        )

        aggregated = aggregate_signals(
            winners,
            weight_scheme=self.config.vote_weight,
            min_agreement=self.config.min_agreement,
        )

        last_price = float(df["close"].iloc[-1])
        executed = self.execute_aggregated(aggregated, last_price)

        return RunReport(
            all_results=results,
            winners=winners,
            aggregated=aggregated,
            executed=executed,
            broker_summary=(
                self.broker.summary({self.config.symbol: last_price})
                if hasattr(self.broker, "summary")
                else {}
            ),
        )
