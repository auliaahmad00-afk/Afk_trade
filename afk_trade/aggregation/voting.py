"""Agregasi sinyal lewat voting berbobot antar skenario terpilih.

Tiap skenario pemenang "memberi suara" sesuai sinyal terakhirnya (LONG/SHORT/FLAT).
Suara dijumlahkan dengan bobot tertentu, lalu menghasilkan SATU keputusan net.
Ini mencegah skenario yang saling berlawanan membuka order yang saling
menetralkan di broker.

Skema bobot:
- "equal"         : tiap skenario bernilai 1 suara.
- "profit_factor" : bobot = profit factor (skenario lebih profit, suara lebih besar).
- "winrate"       : bobot = winrate.
- "expectancy"    : bobot = ekspektasi profit per trade (di-clip ke >= 0).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from ..backtest.engine import BacktestResult

# Bobot bisa tak hingga (profit_factor saat tanpa loss); batasi agar tidak
# mendominasi total secara ekstrem.
_MAX_WEIGHT = 1e6


def _weight_of(result: BacktestResult, scheme: str) -> float:
    if scheme == "equal":
        w = 1.0
    elif scheme == "profit_factor":
        w = result.profit_factor
    elif scheme == "winrate":
        w = result.winrate
    elif scheme == "expectancy":
        w = max(result.avg_trade_return, 0.0)
    else:
        raise ValueError(f"skema bobot tidak dikenal: {scheme}")
    if w != w:  # NaN
        return 0.0
    return float(min(max(w, 0.0), _MAX_WEIGHT))


@dataclass
class AggregatedSignal:
    """Hasil voting: satu keputusan net beserta rinciannya."""

    direction: int          # 1 = LONG, -1 = SHORT, 0 = FLAT/tak ada konsensus
    confidence: float       # 0..1 = derajat kesepakatan (|net| / total bobot suara)
    long_weight: float = 0.0
    short_weight: float = 0.0
    n_long: int = 0
    n_short: int = 0
    n_flat: int = 0
    weight_scheme: str = "profit_factor"
    contributors: List[Tuple[str, int, float]] = field(default_factory=list)

    @property
    def total_weight(self) -> float:
        return self.long_weight + self.short_weight

    def as_dict(self) -> dict:
        side = {1: "LONG", -1: "SHORT", 0: "FLAT"}[self.direction]
        return {
            "direction": side,
            "confidence": round(self.confidence, 3),
            "long_weight": round(self.long_weight, 3),
            "short_weight": round(self.short_weight, 3),
            "votes": f"{self.n_long} long / {self.n_short} short / {self.n_flat} flat",
            "weight_scheme": self.weight_scheme,
        }


def aggregate_signals(
    winners: List[BacktestResult],
    *,
    weight_scheme: str = "profit_factor",
    min_agreement: float = 0.0,
) -> AggregatedSignal:
    """Gabungkan sinyal skenario terpilih menjadi satu keputusan net.

    Args:
        winners: skenario terpilih (punya atribut last_signal & bobot).
        weight_scheme: cara membobot suara.
        min_agreement: ambang konsensus minimal (0..1). Bila derajat kesepakatan
            di bawah ini, hasilnya FLAT (tahan diri karena suara terbelah).

    Returns:
        AggregatedSignal dengan direction, confidence, dan rincian suara.
    """
    long_w = 0.0
    short_w = 0.0
    n_long = n_short = n_flat = 0
    contributors: List[Tuple[str, int, float]] = []

    for r in winners:
        sig = int(r.last_signal)
        w = _weight_of(r, weight_scheme)
        contributors.append((r.label, sig, w))
        if sig == 1:
            long_w += w
            n_long += 1
        elif sig == -1:
            short_w += w
            n_short += 1
        else:
            n_flat += 1

    total = long_w + short_w
    net = long_w - short_w
    confidence = abs(net) / total if total > 0 else 0.0

    if total == 0 or net == 0 or confidence < min_agreement:
        direction = 0  # tak ada suara, seri, atau konsensus terlalu lemah -> tahan
    else:
        direction = 1 if net > 0 else -1

    return AggregatedSignal(
        direction=direction,
        confidence=confidence,
        long_weight=long_w,
        short_weight=short_w,
        n_long=n_long,
        n_short=n_short,
        n_flat=n_flat,
        weight_scheme=weight_scheme,
        contributors=contributors,
    )
