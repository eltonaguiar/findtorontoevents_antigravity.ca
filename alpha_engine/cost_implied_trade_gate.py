"""Cost-implied trade gate (P2-h / H-146).

Standalone, measurable component: change position only when the absolute
forecast exceeds the round-trip cost. Measure turnover reduction and
gross-alpha retention SEPARATELY so we can see whether the gate kills
turnover (good) or kills alpha (bad).

This is an ORDER-GATEWAY rule, not a model suggestion. Sizing limits that
live inside the model are advisory and fail precisely in the regime where
they matter.

Usage:
    from alpha_engine.cost_implied_trade_gate import CostImpliedTradeGate

    gate = CostImpliedTradeGate(round_trip_cost_bps=20.0)
    decision = gate.decide(forecast_bps=35.0, current_position=0.0)
    # decision.trade == True, decision.new_position = +1 (or sized)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Use the corrected cost gate (captured reversion, not full reversion)
try:
    from alpha_engine import cost_gate as _cg
    _HAS_COST_GATE = True
except ImportError:
    _HAS_COST_GATE = False

log = logging.getLogger(__name__)


@dataclass
class GateDecision:
    trade: bool
    reason: str
    forecast_bps: float
    round_trip_cost_bps: float
    edge_over_cost_bps: float
    current_position: float
    new_position: float
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GateStats:
    n_decisions: int = 0
    n_trades: int = 0
    n_blocked: int = 0
    turnover_before: float = 0.0   # sum of |position changes| without gate
    turnover_after: float = 0.0    # sum of |position changes| with gate
    gross_alpha_before: float = 0.0  # sum of |forecast| acted on without gate
    gross_alpha_after: float = 0.0   # sum of |forecast| acted on with gate

    @property
    def turnover_reduction_pct(self) -> float:
        if self.turnover_before == 0:
            return 0.0
        return 100.0 * (1.0 - self.turnover_after / self.turnover_before)

    @property
    def gross_alpha_retention_pct(self) -> float:
        if self.gross_alpha_before == 0:
            return 0.0
        return 100.0 * (self.gross_alpha_after / self.gross_alpha_before)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["turnover_reduction_pct"] = round(self.turnover_reduction_pct, 4)
        d["gross_alpha_retention_pct"] = round(self.gross_alpha_retention_pct, 4)
        return d


class CostImpliedTradeGate:
    """Hard gate: only change position when |forecast| > round_trip_cost.

    Position sizing is NOT done here — this gate only decides whether to
    act at all. Sizing (vol-targeted, capped) happens downstream and is
    enforced in the order gateway, outside the model.
    """

    def __init__(
        self,
        round_trip_cost_bps: float,
        cost_model_version: str = "v1.0",
        min_edge_over_cost_bps: float = 0.0,
        sigma_eq_median: float | None = None,
    ) -> None:
        if round_trip_cost_bps < 0:
            raise ValueError("round_trip_cost_bps must be >= 0")
        self.round_trip_cost_bps = float(round_trip_cost_bps)
        self.cost_model_version = cost_model_version
        # Extra buffer beyond pure cost; 0 = act the moment forecast clears cost.
        self.min_edge_over_cost_bps = float(min_edge_over_cost_bps)
        # P0.0k redesign: sigma_eq_median for conditioning (not filtering).
        # When set, the gate requires sigma_eq >= median before trading.
        self.sigma_eq_median = sigma_eq_median
        self.stats = GateStats()
        self._history: List[GateDecision] = []

    def threshold(self) -> float:
        return self.round_trip_cost_bps + self.min_edge_over_cost_bps

    def decide(
        self,
        forecast_bps: float,
        current_position: float = 0.0,
        new_position_if_trade: Optional[float] = None,
        s_entry: Optional[float] = None,
        sigma_eq_frac: Optional[float] = None,
        s_exit: float = 0.5,
    ) -> GateDecision:
        """Decide whether to change position.

        forecast_bps: signed expected move in basis points.
        current_position: current signed position (0 = flat).
        new_position_if_trade: desired position if we act (default: sign(forecast)).
        s_entry: (optional) OU s-score at entry. If provided with sigma_eq_frac,
                 uses the CORRECTED cost gate (captured reversion, not full
                 reversion) from alpha_engine.cost_gate. This is the preferred
                 path — the raw forecast comparison overstates the margin by ~67%.
        sigma_eq_frac: (optional) equilibrium sigma as a return fraction (0.02 = 2%).
        s_exit: (optional) exit s-score threshold (default 0.5).
        """
        ts = datetime.now(timezone.utc).isoformat()
        abs_fc = abs(forecast_bps)
        thr = self.threshold()

        # Use corrected cost gate if s_entry and sigma_eq_frac are provided
        if _HAS_COST_GATE and s_entry is not None and sigma_eq_frac is not None:
            result = _cg.should_trade(s_entry, sigma_eq_frac, self.round_trip_cost_bps,
                                     s_exit=s_exit, cost_multiple=1.0 + self.min_edge_over_cost_bps / self.round_trip_cost_bps if self.round_trip_cost_bps > 0 else 1.0,
                                     sigma_eq_median=self.sigma_eq_median)
            trade = result["trade"]
            edge = result["captured_edge_bps"]
            reason_detail = (f"captured_edge {edge:.2f} bps vs cost {self.round_trip_cost_bps:.2f} bps "
                            f"(fraction {result['captured_fraction']:.2f}, margin {result['margin_ratio']}, "
                            f"sigma_cond={result['sigma_condition_ok']}, cost_cond={result['cost_condition_ok']})")
        else:
            # Fallback: raw forecast comparison (legacy, overstates margin by ~67%)
            trade = abs_fc > thr
            edge = abs_fc
            reason_detail = f"|forecast| {abs_fc:.2f} bps vs threshold {thr:.2f} bps"

        # Track gross alpha that would have been acted on without the gate.
        self.stats.gross_alpha_before += abs_fc

        if not trade:
            dec = GateDecision(
                trade=False,
                reason=f"BLOCKED: {reason_detail}",
                forecast_bps=forecast_bps,
                round_trip_cost_bps=self.round_trip_cost_bps,
                edge_over_cost_bps=edge - self.round_trip_cost_bps,
                current_position=current_position,
                new_position=current_position,
                timestamp=ts,
            )
            self.stats.n_blocked += 1
        else:
            if new_position_if_trade is None:
                new_pos = 1.0 if forecast_bps >= 0 else -1.0
            else:
                new_pos = float(new_position_if_trade)
            dec = GateDecision(
                trade=True,
                reason=f"TRADE: {reason_detail}",
                forecast_bps=forecast_bps,
                round_trip_cost_bps=self.round_trip_cost_bps,
                edge_over_cost_bps=edge - self.round_trip_cost_bps,
                current_position=current_position,
                new_position=new_pos,
                timestamp=ts,
            )
            self.stats.n_trades += 1
            self.stats.turnover_after += abs(new_pos - current_position)
            self.stats.gross_alpha_after += abs_fc

        self.stats.n_decisions += 1
        # Without-gate turnover: assume we act on every non-zero forecast.
        if abs_fc > 0:
            npw = 1.0 if forecast_bps >= 0 else -1.0
            self.stats.turnover_before += abs(npw - current_position)
        self._history.append(dec)
        return dec

    def evaluate_series(
        self, forecasts_bps: List[float], positions_before: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """Run the gate over a series and return before/after stats.

        positions_before: optional list of current positions aligned with forecasts;
        defaults to 0 (flat) for all.
        """
        if positions_before is None:
            positions_before = [0.0] * len(forecasts_bps)
        # Reset stats for a clean measurement.
        self.stats = GateStats()
        self._history = []
        decisions = []
        for fc, pos in zip(forecasts_bps, positions_before):
            decisions.append(self.decide(fc, current_position=pos))
        return {
            "n": len(forecasts_bps),
            "stats": self.stats.to_dict(),
            "decisions": [d.to_dict() for d in decisions],
        }

    def to_json(self, path: str) -> None:
        payload = {
            "cost_model_version": self.cost_model_version,
            "round_trip_cost_bps": self.round_trip_cost_bps,
            "min_edge_over_cost_bps": self.min_edge_over_cost_bps,
            "threshold_bps": self.threshold(),
            "stats": self.stats.to_dict(),
            "n_history": len(self._history),
        }
        with open(path, "w") as fh:
            json.dump(payload, fh, indent=2)
        log.info("wrote gate stats to %s", path)


if __name__ == "__main__":
    # Smoke test + demonstration of turnover reduction vs alpha retention.
    import random

    random.seed(42)
    gate = CostImpliedTradeGate(round_trip_cost_bps=20.0)
    # Simulate 1000 forecasts: 60% small (5-15 bps), 40% large (25-60 bps)
    forecasts = []
    for _ in range(1000):
        if random.random() < 0.6:
            forecasts.append(random.uniform(5, 15) * random.choice([-1, 1]))
        else:
            forecasts.append(random.uniform(25, 60) * random.choice([-1, 1]))
    res = gate.evaluate_series(forecasts)
    print(json.dumps(res["stats"], indent=2))
    gate.to_json("/tmp/opencode/cost_gate_smoke.json")
    print("threshold bps:", gate.threshold())