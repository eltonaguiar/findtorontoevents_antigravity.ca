"""Net-of-cost adjustment helpers (EAGLE2 §3.3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence


@dataclass
class CostModel:
    fee_bps: float = 5.0
    slippage_bps: float = 10.0

    @property
    def total_bps(self) -> float:
        return self.fee_bps + self.slippage_bps


# Per-class defaults aligned with alpha_engine/admissibility_pipeline.py
COST_BY_ASSET_CLASS = {
    "CRYPTO": CostModel(fee_bps=10.0, slippage_bps=10.0),
    "EQUITY": CostModel(fee_bps=1.0, slippage_bps=2.0),
    "ETF": CostModel(fee_bps=1.0, slippage_bps=2.0),
    "FOREX": CostModel(fee_bps=0.5, slippage_bps=1.0),
    "COMMODITY": CostModel(fee_bps=2.0, slippage_bps=5.0),
    "FUTURES": CostModel(fee_bps=2.0, slippage_bps=5.0),
    "BOND": CostModel(fee_bps=1.0, slippage_bps=2.0),
}


def apply_costs_to_pnls(
    pnls: Sequence[float],
    cost_model: CostModel | None = None,
    asset_class: str = "EQUITY",
) -> List[float]:
    """Subtract round-trip cost drag from each PnL observation (percent-based)."""
    model = cost_model or COST_BY_ASSET_CLASS.get(asset_class.upper(), CostModel())
    drag = model.total_bps / 10000.0
    return [float(p) - abs(float(p)) * drag for p in pnls]


def apply_costs(trades: Iterable[dict], cost_model: CostModel | None = None) -> List[dict]:
    """Mutate trade dicts in-place style — returns new list with pnl_net."""
    model = cost_model or CostModel()
    drag = model.total_bps / 10000.0
    out: List[dict] = []
    for t in trades:
        row = dict(t)
        gross = float(row.get("pnl_gross", row.get("pnl", row.get("pnl_pct", 0.0))) or 0.0)
        row["pnl_net"] = gross - abs(gross) * drag
        out.append(row)
    return out
