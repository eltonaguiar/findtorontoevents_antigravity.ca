"""Particle Swarm Optimization (PSO) for dynamic permutation weight allocation.

Each strategy permutation is a "particle" navigating a 10-dimensional parameter
space.  The swarm collectively converges on optimal parameter combinations with
market-adaptive inertia: high volatility encourages exploration, low volatility
encourages exploitation.

Standalone usage:
    python -m meta_strategy.swarm_consensus
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from meta_strategy.db import get_db

# ---------------------------------------------------------------------------
# Parameter space definition
# ---------------------------------------------------------------------------

PARAM_NAMES: list[str] = [
    "confidence_threshold",       # 0
    "confluence_window_minutes",  # 1
    "min_agreement_ratio",        # 2
    "fee_tolerance",              # 3
    "position_size_pct",          # 4
    "tp_pct",                     # 5
    "sl_pct",                     # 6
    "max_correlated_positions",   # 7
    "regime_sensitivity",         # 8
    "decay_factor",               # 9
]

PARAM_BOUNDS: np.ndarray = np.array([
    [0.3,   0.9  ],  # confidence_threshold
    [60.0,  1440.0],  # confluence_window_minutes
    [0.5,   1.0  ],  # min_agreement_ratio
    [0.005, 0.02 ],  # fee_tolerance
    [0.01,  0.05 ],  # position_size_pct
    [0.02,  0.10 ],  # tp_pct
    [0.01,  0.05 ],  # sl_pct
    [1.0,   5.0  ],  # max_correlated_positions
    [0.0,   1.0  ],  # regime_sensitivity
    [0.8,   1.0  ],  # decay_factor
])

N_DIMS = len(PARAM_NAMES)
DATA_DIR = Path(__file__).parent / "data"

# PSO hyper-parameters
C1 = 1.5   # cognitive (personal best pull)
C2 = 2.0   # social (global best pull)
V_MAX_FRAC = 0.2  # max velocity as fraction of range


# ---------------------------------------------------------------------------
# Swarm Particle
# ---------------------------------------------------------------------------

@dataclass
class SwarmParticle:
    """A single particle representing one permutation combo in the swarm."""

    combo_id: str
    position: np.ndarray
    velocity: np.ndarray
    best_position: np.ndarray = field(default_factory=lambda: np.zeros(0))
    best_score: float = -np.inf

    def __post_init__(self) -> None:
        if self.best_position.size == 0:
            self.best_position = self.position.copy()

    def update(self, global_best: np.ndarray, market_state: dict[str, Any]) -> None:
        """PSO velocity + position update with market-state-dependent inertia.

        Parameters
        ----------
        global_best : array of shape (N_DIMS,)
            Best position found by *any* particle in the swarm.
        market_state : dict
            Must contain ``"inertia"`` (float 0.4-0.9) derived from recent
            volatility.
        """
        inertia: float = market_state.get("inertia", 0.7)
        r1 = np.random.random(N_DIMS)
        r2 = np.random.random(N_DIMS)

        cognitive = C1 * r1 * (self.best_position - self.position)
        social = C2 * r2 * (global_best - self.position)

        self.velocity = inertia * self.velocity + cognitive + social

        # Clamp velocity
        ranges = PARAM_BOUNDS[:, 1] - PARAM_BOUNDS[:, 0]
        v_max = V_MAX_FRAC * ranges
        self.velocity = np.clip(self.velocity, -v_max, v_max)

        # Move
        self.position = self.position + self.velocity

        # Enforce bounds (reflect)
        for d in range(N_DIMS):
            lo, hi = PARAM_BOUNDS[d]
            if self.position[d] < lo:
                self.position[d] = lo
                self.velocity[d] *= -0.5
            elif self.position[d] > hi:
                self.position[d] = hi
                self.velocity[d] *= -0.5


# ---------------------------------------------------------------------------
# Fitness helpers
# ---------------------------------------------------------------------------

def _consistency(pnl_series: list[float], window: int = 5) -> float:
    """Fraction of rolling *window*-trade windows that are net profitable."""
    if len(pnl_series) < window:
        return 0.0
    profitable = 0
    total = len(pnl_series) - window + 1
    for i in range(total):
        if sum(pnl_series[i : i + window]) > 0:
            profitable += 1
    return profitable / total


def compute_fitness(sharpe: float, max_dd: float, trades: int,
                    pnl_series: list[float]) -> float:
    """Multi-objective fitness.

    fitness = sharpe * 0.4 + consistency * 0.3 + (1 - max_dd) * 0.2
              + log(1 + trades) * 0.1
    """
    cons = _consistency(pnl_series)
    return (
        sharpe * 0.4
        + cons * 0.3
        + (1.0 - min(abs(max_dd), 1.0)) * 0.2
        + math.log(1.0 + trades) * 0.1
    )


# ---------------------------------------------------------------------------
# SwarmConsensus engine
# ---------------------------------------------------------------------------

class SwarmConsensus:
    """Particle-Swarm weight optimizer over active permutations."""

    def __init__(self) -> None:
        self.particles: list[SwarmParticle] = []
        self.global_best_position: np.ndarray = np.zeros(N_DIMS)
        self.global_best_score: float = -np.inf

    # -- DB helpers ---------------------------------------------------------

    @staticmethod
    def _load_active_combos() -> list[str]:
        """Return combo_ids with status ACTIVE (or RESURRECTED / PROBATION)."""
        conn = get_db()
        try:
            rows = conn.execute(
                "SELECT combo_id FROM permutations "
                "WHERE status IN ('ACTIVE', 'RESURRECTED', 'PROBATION')"
            ).fetchall()
            return [r["combo_id"] for r in rows]
        finally:
            conn.close()

    @staticmethod
    def _load_results(combo_id: str) -> dict[str, Any]:
        """Load aggregate backtest results for *combo_id*."""
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT sharpe, max_drawdown_pct, total_trades, total_pnl_pct "
                "FROM permutation_results "
                "WHERE combo_id = ? AND symbol IS NULL "
                "ORDER BY id DESC LIMIT 1",
                (combo_id,),
            ).fetchone()
            if row is None:
                return {"sharpe": 0.0, "max_dd": 0.0, "trades": 0, "pnl_series": []}
            # Build a rough pnl_series from individual signal outcomes
            signals = conn.execute(
                "SELECT pnl_pct FROM permutation_signals "
                "WHERE combo_id = ? AND status IN ('TP_HIT', 'SL_HIT', 'CLOSED') "
                "ORDER BY exit_timestamp ASC",
                (combo_id,),
            ).fetchall()
            pnl_series = [s["pnl_pct"] for s in signals if s["pnl_pct"] is not None]
            return {
                "sharpe": float(row["sharpe"]) if row["sharpe"] else 0.0,
                "max_dd": float(row["max_drawdown_pct"]) if row["max_drawdown_pct"] else 0.0,
                "trades": int(row["total_trades"]) if row["total_trades"] else 0,
                "pnl_series": pnl_series,
            }
        finally:
            conn.close()

    @staticmethod
    def _detect_market_state() -> dict[str, Any]:
        """Derive market-adaptive inertia from recent PnL volatility in DB.

        High volatility -> inertia = 0.9 (explore)
        Low volatility  -> inertia = 0.4 (exploit)
        """
        conn = get_db()
        try:
            rows = conn.execute(
                "SELECT pnl_pct FROM permutation_signals "
                "WHERE status IN ('TP_HIT', 'SL_HIT', 'CLOSED') "
                "  AND pnl_pct IS NOT NULL "
                "ORDER BY exit_timestamp DESC LIMIT 100"
            ).fetchall()
        finally:
            conn.close()

        pnls = [r["pnl_pct"] for r in rows]
        if len(pnls) < 5:
            return {"inertia": 0.7, "volatility": "unknown"}

        std = float(np.std(pnls))
        # Map std to inertia: std < 0.01 -> 0.4, std > 0.05 -> 0.9
        inertia = float(np.clip(0.4 + (std - 0.01) * (0.5 / 0.04), 0.4, 0.9))
        vol_label = "high" if inertia > 0.7 else ("medium" if inertia > 0.5 else "low")
        return {"inertia": inertia, "volatility": vol_label}

    # -- Core ---------------------------------------------------------------

    def initialize(self) -> None:
        """Load active combos from DB and create one particle per combo."""
        combo_ids = self._load_active_combos()
        if not combo_ids:
            print("[swarm] No active permutations found in DB.")
            return

        ranges = PARAM_BOUNDS[:, 1] - PARAM_BOUNDS[:, 0]
        lows = PARAM_BOUNDS[:, 0]

        for cid in combo_ids:
            pos = lows + np.random.random(N_DIMS) * ranges
            vel = (np.random.random(N_DIMS) - 0.5) * V_MAX_FRAC * ranges
            self.particles.append(SwarmParticle(
                combo_id=cid,
                position=pos,
                velocity=vel,
            ))

        print(f"[swarm] Initialized {len(self.particles)} particles for "
              f"{len(combo_ids)} active combos.")

    def _evaluate(self, particle: SwarmParticle) -> float:
        """Compute fitness for a particle using DB results + current position."""
        res = self._load_results(particle.combo_id)
        # Use position[0] (confidence_threshold) as a filter — combos whose
        # DB sharpe is below the particle's threshold are penalized.
        threshold = particle.position[0]
        sharpe = res["sharpe"]
        if sharpe < threshold * 2.0:
            sharpe *= 0.5  # penalize low-sharpe under high-threshold particle

        return compute_fitness(
            sharpe=sharpe,
            max_dd=res["max_dd"],
            trades=res["trades"],
            pnl_series=res["pnl_series"],
        )

    def optimize_weights(self, n_iterations: int = 20) -> dict[str, float]:
        """Run *n_iterations* of PSO and return normalized weight dict.

        Returns
        -------
        dict mapping combo_id -> allocation_weight (sums to 1.0).
        Also persists to ``data/swarm_weights.json``.
        """
        if not self.particles:
            print("[swarm] No particles — nothing to optimize.")
            return {}

        market_state = self._detect_market_state()
        print(f"[swarm] Market state: inertia={market_state['inertia']:.2f} "
              f"volatility={market_state['volatility']}")

        for iteration in range(1, n_iterations + 1):
            for p in self.particles:
                score = self._evaluate(p)

                # Update personal best
                if score > p.best_score:
                    p.best_score = score
                    p.best_position = p.position.copy()

                # Update global best
                if score > self.global_best_score:
                    self.global_best_score = score
                    self.global_best_position = p.position.copy()

            # Move all particles
            for p in self.particles:
                p.update(self.global_best_position, market_state)

            if iteration % 5 == 0 or iteration == 1:
                print(f"  iteration {iteration:>3}/{n_iterations}  "
                      f"global_best_score={self.global_best_score:.4f}")

        # Build weight dict from final best scores (softmax-style normalization)
        scores = np.array([p.best_score for p in self.particles])
        # Shift to avoid overflow and handle all-negative
        shifted = scores - scores.max()
        exp_scores = np.exp(shifted)
        total = exp_scores.sum()
        if total == 0:
            weights = np.ones(len(self.particles)) / len(self.particles)
        else:
            weights = exp_scores / total

        result: dict[str, float] = {}
        for p, w in zip(self.particles, weights):
            result[p.combo_id] = round(float(w), 6)

        # Persist
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        out_path = DATA_DIR / "swarm_weights.json"
        payload = {
            "generated_at": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            "n_iterations": n_iterations,
            "n_particles": len(self.particles),
            "global_best_score": round(self.global_best_score, 6),
            "market_inertia": market_state["inertia"],
            "weights": result,
        }
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"[swarm] Saved weights to {out_path}")

        return result


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main() -> None:
    """Load active combos, run 20 PSO iterations, print top 10, save."""
    swarm = SwarmConsensus()
    swarm.initialize()

    if not swarm.particles:
        print("[swarm] Exiting — no active permutations to optimize.")
        sys.exit(0)

    weights = swarm.optimize_weights(n_iterations=20)

    # Top 10 by weight
    ranked = sorted(weights.items(), key=lambda kv: kv[1], reverse=True)[:10]
    print("\n=== Top 10 Combos by Swarm-Optimized Weight ===")
    print(f"{'Rank':<5} {'Combo ID':<50} {'Weight':>10}")
    print("-" * 67)
    for i, (cid, w) in enumerate(ranked, 1):
        print(f"{i:<5} {cid:<50} {w:>10.6f}")


if __name__ == "__main__":
    main()
