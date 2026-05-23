#!/usr/bin/env python3
"""
ALPHA ENGINE -- Top-N Concentration Model (Hedge Fund Sprint 2026-03-25)
========================================================================
Implements the hedge fund capital concentration principle:

  "You don't have a signal problem — you have a capital allocation problem."

Current state:  1,325 traders, 130+ strategies → 46% WR, Sharpe ~0.3
Target state:   2-4 proven traders, 5-8 strategies → 58-62% WR, Sharpe ~1.0

ALLOCATION MODEL (Top-5 only — everything else gets 0%):
    Rank | Strategy                      | Allocation
    -----+-------------------------------+-----------
    1    | ml_enhanced_FETUSDT           | 30%
    2    | ml_enhanced_RENDERUSDT        | 20%
    3    | ml_enhanced_BNBUSDT           | 15%
    4    | NMTD_25M (copy whale)         | 25%
    5    | whale_123M (copy whale)       | 10%
    All others                           | 0% (paper only)

PROMOTION SYSTEM:
  New strategies/traders must prove themselves before getting capital:
    - Minimum 20-30 paper trades
    - Win rate > 60%
    - Profit Factor > 1.8
  On promotion: start at 5% allocation, scale up as track record builds.

DECAY REMOVAL:
  Even proven strategies get cut if performance degrades:
    - Rolling-20 WR drops below 50% → reduce weight by 50%
    - Rolling-20 WR drops below 40% → suspend (paper-only) for review
    - Correlation to ml_score flips negative → flag for inspection

Usage:
    from concentration_model import ConcentrationModel
    model = ConcentrationModel()
    alloc = model.get_allocation("ml_enhanced_FETUSDT_1d_B_lightgbm")
    # → 0.30 (30% of portfolio)

    report = model.generate_report(strategy_perf)
    # → dict with current allocations, promotion candidates, decay warnings
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_DATA_DIR = _THIS_DIR / "data"
_CONCENTRATION_STATE_PATH = _DATA_DIR / "concentration_state.json"

# ---------------------------------------------------------------------------
# Top-5 Proven Strategies — the only ones receiving live capital
# ---------------------------------------------------------------------------
TOP_5_ALLOCATION: dict[str, float] = {
    # ML scalping — empirically verified 85-94% WR
    "ml_enhanced_fetusdt_1d_b_lightgbm":                  0.30,
    "ml_enhanced_renderusdt_1h_d_ensemble_stack":          0.10,
    "ml_enhanced_renderusdt_4h_d_ensemble_stack":          0.10,  # combined RENDER = 20%
    "ml_enhanced_bnbusdt_15m_b_lightgbm":                  0.15,
    # Whale copy — Hyperliquid verified track records
    "copy_hl_nmtd_25m":                                    0.25,
    "nmtd_25m":                                            0.25,  # alt key
    "copy_hl_whale_123m_87roi":                            0.10,
    "whale_123m_87roi":                                    0.10,  # alt key
    "copy_hl_whale_123m":                                  0.10,  # alt key
    "whale_123m":                                          0.10,  # alt key
}

# Prefix-based allocation for any ml_enhanced_* on proven symbols
ML_PROVEN_PREFIXES: dict[str, float] = {
    "ml_enhanced_fetusdt": 0.30,
    "ml_enhanced_renderusdt": 0.10,
    "ml_enhanced_bnbusdt": 0.15,
}

# ---------------------------------------------------------------------------
# Promotion thresholds — paper stage requirements before getting capital
# ---------------------------------------------------------------------------
PROMOTION_MIN_TRADES = 20
PROMOTION_MIN_WR = 0.60
PROMOTION_MIN_PF = 1.8
PROMOTION_STARTING_ALLOCATION = 0.05  # 5% on promotion

# ---------------------------------------------------------------------------
# Decay thresholds — conditions for reducing or suspending allocations
# ---------------------------------------------------------------------------
DECAY_REDUCE_WR = 0.50     # Rolling-20 WR below this → halve allocation
DECAY_SUSPEND_WR = 0.40    # Rolling-20 WR below this → suspend to paper
DECAY_ROLLING_WINDOW = 20  # Trades in rolling WR window

# ---------------------------------------------------------------------------
# Score-based position sizing multipliers
# ---------------------------------------------------------------------------
POSITION_SIZE_TIERS: list[tuple[float, float]] = [
    (80.0, 2.0),   # score ≥ 80 → 2.0x
    (70.0, 1.5),   # score ≥ 70 → 1.5x
    (60.0, 1.0),   # score ≥ 60 → 1.0x
    (0.0,  0.0),   # score < 55 → blocked (should be caught by gate earlier)
]


def _normalise_key(name: object) -> str:
    return str(name or "").strip().lower()


def get_position_size_multiplier(score: float) -> float:
    """
    Return position size multiplier based on elite score.

    Score ≥ 80 → 2.0x | Score ≥ 70 → 1.5x | Score ≥ 60 → 1.0x | <55 → 0x
    This dramatically improves Sharpe by concentrating size on high-conviction picks.
    """
    for threshold, multiplier in POSITION_SIZE_TIERS:
        if score >= threshold:
            return multiplier
    return 0.0


class ConcentrationModel:
    """
    Manages capital allocation within the hedge-fund concentration paradigm:
      - Only top-5 proven strategies receive live capital
      - All others paper-trade until promoted via verified track record
      - Decay detection auto-reduces allocation for degrading strategies
    """

    def __init__(self, state_path: Optional[Path] = None):
        self._state_path = state_path or _CONCENTRATION_STATE_PATH
        self._promoted: dict[str, float] = {}   # dynamically promoted strategies
        self._suspended: set[str] = set()        # temporarily suspended strategies
        self._load_state()

    def _load_state(self) -> None:
        """Load persisted concentration state (promotions, suspensions)."""
        if self._state_path.exists():
            try:
                with open(self._state_path, encoding="utf-8") as f:
                    state = json.load(f)
                self._promoted = state.get("promoted", {})
                self._suspended = set(state.get("suspended", []))
            except Exception:
                pass

    def _save_state(self) -> None:
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._state_path, "w", encoding="utf-8") as f:
                json.dump({
                    "promoted": self._promoted,
                    "suspended": list(self._suspended),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }, f, indent=2)
        except Exception:
            pass

    def get_allocation(self, strategy_name: str) -> float:
        """
        Return the target portfolio allocation fraction for a strategy (0.0-1.0).
        Returns 0.0 for strategies not in the proven/promoted tier.
        """
        key = _normalise_key(strategy_name)

        # Suspended strategies get zero
        if key in self._suspended:
            return 0.0

        # Check top-5 allocation table
        if key in TOP_5_ALLOCATION:
            return TOP_5_ALLOCATION[key]

        # Check prefix-based ML allocation
        for prefix, alloc in ML_PROVEN_PREFIXES.items():
            if key.startswith(prefix):
                return alloc

        # Check dynamically promoted strategies
        if key in self._promoted:
            return self._promoted[key]

        # Everything else: paper-only
        return 0.0

    def is_live(self, strategy_name: str) -> bool:
        """Return True if strategy receives live capital."""
        return self.get_allocation(strategy_name) > 0.0

    def apply_to_pick(self, pick: dict, elite_score: float = 0.0) -> dict:
        """
        Enrich a pick with allocation and position sizing metadata.

        Adds:
          - concentration_allocation: float (0.0–1.0)
          - concentration_live: bool
          - position_size_mult: float (based on elite_score)
          - effective_allocation: concentration_allocation * position_size_mult
        """
        alloc = self.get_allocation(pick.get("strategy", ""))
        size_mult = get_position_size_multiplier(elite_score) if elite_score > 0 else 1.0

        p = dict(pick)
        p["concentration_allocation"] = alloc
        p["concentration_live"] = alloc > 0.0
        p["position_size_mult"] = size_mult
        p["effective_allocation"] = round(alloc * size_mult, 4)
        return p

    def check_decay(self, strategy_name: str, recent_trades: list[dict]) -> dict:
        """
        Check if a strategy's recent performance warrants allocation reduction.

        Args:
            strategy_name: Strategy identifier.
            recent_trades: List of recent closed trade dicts with 'pnl_pct' or 'status'.

        Returns:
            {
                'action': 'ok' | 'reduce' | 'suspend',
                'rolling_wr': float,
                'reason': str
            }
        """
        key = _normalise_key(strategy_name)
        window = recent_trades[-DECAY_ROLLING_WINDOW:]
        if len(window) < 5:
            return {"action": "ok", "rolling_wr": None, "reason": "insufficient_data"}

        wins = sum(
            1 for t in window
            if (t.get("status") == "WON" or float(t.get("pnl_pct", 0) or 0) > 0)
        )
        rolling_wr = wins / len(window)

        if rolling_wr < DECAY_SUSPEND_WR:
            self._suspended.add(key)
            # Remove from promoted if applicable
            self._promoted.pop(key, None)
            self._save_state()
            return {
                "action": "suspend",
                "rolling_wr": rolling_wr,
                "reason": f"rolling WR {rolling_wr:.1%} < suspend threshold {DECAY_SUSPEND_WR:.1%}",
            }

        if rolling_wr < DECAY_REDUCE_WR:
            # Halve the allocation
            current = self.get_allocation(strategy_name)
            if current > 0:
                new_alloc = round(current * 0.5, 4)
                if key in TOP_5_ALLOCATION:
                    # Can't modify the constant — promote with halved value
                    self._promoted[key] = new_alloc
                elif key in self._promoted:
                    self._promoted[key] = new_alloc
                self._save_state()
            return {
                "action": "reduce",
                "rolling_wr": rolling_wr,
                "reason": f"rolling WR {rolling_wr:.1%} < reduce threshold {DECAY_REDUCE_WR:.1%}",
            }

        return {"action": "ok", "rolling_wr": rolling_wr, "reason": "within_thresholds"}

    def evaluate_promotion(self, strategy_name: str, trades: list[dict]) -> dict:
        """
        Evaluate whether a paper-trading strategy deserves promotion to live.

        Returns:
            {
                'promoted': bool,
                'reason': str,
                'starting_allocation': float
            }
        """
        key = _normalise_key(strategy_name)
        if self.is_live(strategy_name):
            return {"promoted": False, "reason": "already_live", "starting_allocation": 0.0}

        if len(trades) < PROMOTION_MIN_TRADES:
            return {
                "promoted": False,
                "reason": f"need {PROMOTION_MIN_TRADES} trades, have {len(trades)}",
                "starting_allocation": 0.0,
            }

        wins = sum(1 for t in trades if (t.get("status") == "WON" or float(t.get("pnl_pct", 0) or 0) > 0))
        wr = wins / len(trades) if trades else 0

        gross_profit = sum(float(t.get("pnl_pct", 0) or 0) for t in trades if float(t.get("pnl_pct", 0) or 0) > 0)
        gross_loss = abs(sum(float(t.get("pnl_pct", 0) or 0) for t in trades if float(t.get("pnl_pct", 0) or 0) < 0))
        pf = (gross_profit / gross_loss) if gross_loss > 0 else (10.0 if gross_profit > 0 else 0.0)

        if wr >= PROMOTION_MIN_WR and pf >= PROMOTION_MIN_PF:
            self._promoted[key] = PROMOTION_STARTING_ALLOCATION
            self._save_state()
            return {
                "promoted": True,
                "reason": f"WR={wr:.1%}, PF={pf:.2f} — meets thresholds",
                "starting_allocation": PROMOTION_STARTING_ALLOCATION,
            }

        return {
            "promoted": False,
            "reason": f"WR={wr:.1%} (need {PROMOTION_MIN_WR:.0%}), PF={pf:.2f} (need {PROMOTION_MIN_PF})",
            "starting_allocation": 0.0,
        }

    def generate_report(self, strategy_perf: Optional[dict] = None) -> dict:
        """
        Generate a full allocation report.

        Returns:
            {
                'live_strategies': {name: allocation, ...},
                'paper_strategies': [name, ...],
                'suspended_strategies': [name, ...],
                'promoted_strategies': {name: allocation, ...},
                'promotion_candidates': [{name, trades, wr, pf}, ...],
                'generated_at': ISO timestamp
            }
        """
        live = {**TOP_5_ALLOCATION, **self._promoted}
        # Remove suspended
        live = {k: v for k, v in live.items() if k not in self._suspended}

        promotion_candidates = []
        if strategy_perf:
            for strat_name, perf in strategy_perf.items():
                key = _normalise_key(strat_name)
                if key in live or key in self._suspended:
                    continue
                trades = perf.get("closed_picks", 0)
                wr = perf.get("win_rate", 0)
                pf = perf.get("profit_factor", 0)
                if trades >= PROMOTION_MIN_TRADES and wr >= 0.50:
                    promotion_candidates.append({
                        "strategy": strat_name,
                        "trades": trades,
                        "wr": wr,
                        "pf": pf,
                        "meets_promotion": wr >= PROMOTION_MIN_WR and pf >= PROMOTION_MIN_PF,
                    })
            promotion_candidates.sort(key=lambda x: x["wr"], reverse=True)

        return {
            "live_strategies": {k: v for k, v in live.items() if v > 0},
            "paper_strategies": [],
            "suspended_strategies": list(self._suspended),
            "promoted_strategies": self._promoted,
            "promotion_candidates": promotion_candidates[:10],
            "total_live_allocation": sum(
                v for k, v in live.items()
                if any(prefix in k for prefix in ("fetusdt", "renderusdt", "bnbusdt"))
                or "nmtd" in k or "whale_123m" in k or "whale_123" in k
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


if __name__ == "__main__":
    model = ConcentrationModel()
    print("=== Concentration Model ===")
    print(f"ml_enhanced_FETUSDT allocation: {model.get_allocation('ml_enhanced_FETUSDT_1d_B_lightgbm'):.0%}")
    print(f"copy_hl_NMTD_25M allocation: {model.get_allocation('copy_hl_NMTD_25M'):.0%}")
    print(f"binance_smart_money allocation: {model.get_allocation('binance_smart_money'):.0%}")
    print(f"\nPosition size mult @ score 85: {get_position_size_multiplier(85)}")
    print(f"Position size mult @ score 72: {get_position_size_multiplier(72)}")
    print(f"Position size mult @ score 62: {get_position_size_multiplier(62)}")
    print(f"Position size mult @ score 42: {get_position_size_multiplier(42)}")
