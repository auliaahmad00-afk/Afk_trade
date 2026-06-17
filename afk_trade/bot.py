"""Orkestrator utama: jalankan skenario, hitung probabilitas, eksekusi pemenang."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import pandas as pd

from .aggregation.voting import AggregatedSignal, aggregate_signals
from .backtest.engine import BacktestResult, backtest_scenario
from .config import BotConfig
from .data.feed import get_data
from .execution.broker import Broker, Order
from .execution.paper import PaperBroker
from .scenarios.generator import generate_scenarios
from .selection.selector import rank_results, select_scenarios
from .validation.splitter import split_data
from .validation.validator import ValidationResult, validate_scenarios


@dataclass
class RunReport:
    """Hasil satu putaran penuh bot."""

    all_results: List[BacktestResult]
    winners: List[BacktestResult]
    aggregated: AggregatedSignal
    executed: List[Order]
    broker_summary: dict
    # Diisi saat validasi train/test aktif:
    validation: List[ValidationResult] = field(default_factory=list)
    robust_winners: List[BacktestResult] = field(default_factory=list)
    validated: bool = False


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

    def _select(self, results: List[BacktestResult]) -> List[BacktestResult]:
        return select_scenarios(
            results,
            mode=self.config.selection_mode,
            min_trades=self.config.min_trades,
            win_threshold=self.config.win_threshold,
            pf_threshold=self.config.pf_threshold,
            min_expectancy=self.config.min_expectancy,
        )

    def _validate(
        self, df: pd.DataFrame
    ) -> Tuple[List[BacktestResult], List[BacktestResult], List[BacktestResult], List[ValidationResult]]:
        """Jalur dengan validasi out-of-sample.

        Returns: (all_results_train, winners_train, robust_winners_test, validation).
        """
        train_df, test_df = split_data(df, self.config.test_ratio)
        all_results = self.evaluate(train_df)
        winners = self._select(all_results)

        scenarios = generate_scenarios(self.config.strategies)
        validation = validate_scenarios(
            scenarios,
            train_df,
            test_df,
            cost_per_trade=self.config.cost_per_trade,
            mode=self.config.selection_mode,
            min_trades=self.config.min_trades,
            win_threshold=self.config.win_threshold,
            pf_threshold=self.config.pf_threshold,
            min_expectancy=self.config.min_expectancy,
        )
        # Skenario robust: lolos di train DAN test. Pakai hasil test (out-of-sample)
        # untuk sinyal & bobot voting agar lebih jujur.
        robust = [v.test for v in validation if v.robust]
        robust = rank_results(robust, mode=self.config.selection_mode)
        return all_results, winners, robust, validation

    def run(self, df: Optional[pd.DataFrame] = None) -> RunReport:
        """Jalankan pipeline penuh sekali jalan."""
        if df is None:
            df = get_data(
                self.config.symbol, self.config.timeframe, self.config.bars
            )

        validation: List[ValidationResult] = []
        if self.config.validate:
            all_results, winners, vote_pool, validation = self._validate(df)
        else:
            all_results = self.evaluate(df)
            winners = self._select(all_results)
            vote_pool = winners  # tanpa validasi, semua pemenang ikut voting

        aggregated = aggregate_signals(
            vote_pool,
            weight_scheme=self.config.vote_weight,
            min_agreement=self.config.min_agreement,
        )

        last_price = float(df["close"].iloc[-1])
        executed = self.execute_aggregated(aggregated, last_price)

        return RunReport(
            all_results=all_results,
            winners=winners,
            aggregated=aggregated,
            executed=executed,
            broker_summary=(
                self.broker.summary({self.config.symbol: last_price})
                if hasattr(self.broker, "summary")
                else {}
            ),
            validation=validation,
            robust_winners=vote_pool if self.config.validate else [],
            validated=self.config.validate,
        )
