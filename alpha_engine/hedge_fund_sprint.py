#!/usr/bin/env python3
"""
ALPHA ENGINE -- Hedge Fund Sprint Orchestrator (2026-03-25)
===========================================================
Master entry point for all Hedge Fund Sprint 2026-03-25 enhancements.

Orchestrates the 8-hour sprint action plan into a single callable pipeline:

  Phase 1 — STOP THE BLEEDING (Immediate):
    ✅ Kill binance_smart_money at generator level
    ✅ Block Bitget traders (0% WR, gamed stats)
    ✅ Restore ml_score as primary weight (+0.337 correlation)
    ✅ Enforce minimum score threshold ≥55

  Phase 2 — CONCENTRATE & CALIBRATE:
    ✅ Widen whale TP/SL to 8%/4%
    ✅ Fix timestamp refresh (FETUSDT was hidden 89h)
    ✅ Separate ML vs Whale execution pipelines
    ✅ Top-N concentration model (80% capital to top-5 proven strategies)

  Phase 3 — REBUILD THE ENGINE:
    ✅ ML health monitor (halt trading when health < 80%)
    ✅ Promotion system for new strategies (20 trades, 60% WR, PF > 1.8)
    ✅ Score-based position sizing (score ≥80 → 2.0x, ≥70 → 1.5x)
    ✅ Decay detection (auto-suspend degrading strategies)

EXPECTED WIN-RATE TRAJECTORY:
  Phase 1 alone:  46% → ~52-55% (+5-9pp from removing garbage)
  Phase 2-3:     52% → ~58-62% (+6-10pp from concentration + ML fix)

PROTECTED ASSETS (do not touch):
  - ml_enhanced_FETUSDT (93.8% WR) 
  - ml_enhanced_RENDERUSDT (87.5% WR)
  - ml_enhanced_BNBUSDT (94.1% WR)
  - copy_hl_NMTD_25M (81% WR)
  - Alpha engine (stable, consecutive successes)
  - Polymarket bearish BTC signal

Usage:
    from hedge_fund_sprint import HedgeFundSprint, run_sprint_pipeline

    # Quick check
    status = run_sprint_pipeline(picks)

    # Full orchestration
    sprint = HedgeFundSprint()
    result = sprint.process(picks, strategy_perf)
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .dual_execution_engine import DualExecutionEngine, GLOBAL_SCORE_GATE
from .concentration_model import ConcentrationModel, get_position_size_multiplier
from .ml_health_monitor import MLHealthMonitor, check_feature_health

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_DATA_DIR = _THIS_DIR / "data"
SPRINT_STATUS_PATH = _DATA_DIR / "hedge_fund_sprint_status.json"

# ---------------------------------------------------------------------------
# Hard-kill list (copied here for standalone use — DRY via copy_trader_bridge)
# ---------------------------------------------------------------------------
HARD_KILLED_STRATEGIES: frozenset = frozenset({
    "binance_smart_money",
    "binance_smart_money_long",
    "binance_smart_money_short",
    "binance_smart_money_crypto",
    "binance_lsr",
    "binance_top_trader_lsr",
})

BLOCKED_EXCHANGE_PREFIXES: tuple = (
    "copy_bitget_",
    "bitget_copy_",
    "bitget_",
)

# Block equity/commodity strategies (0-19% WR = guaranteed losers)
BLOCKED_ASSET_CLASSES: frozenset = frozenset({
    "equity", "stock", "etf", "commodity", "forex"
})


def _normalise(v: object) -> str:
    return str(v or "").strip().lower()


def _is_hard_killed(pick: dict) -> tuple[bool, str]:
    """Return (True, reason) if pick should be hard-killed."""
    strategy = _normalise(pick.get("strategy", ""))
    source = _normalise(pick.get("source_system", ""))
    category = _normalise(pick.get("category", ""))

    # binance_smart_money family
    if strategy in HARD_KILLED_STRATEGIES or "binance_smart_money" in source:
        return True, "binance_smart_money: sentiment aggregate, not copy trading (45.8% WR)"

    # Bitget traders
    if any(strategy.startswith(p) for p in BLOCKED_EXCHANGE_PREFIXES):
        return True, "Bitget: 0% WR on all tracked picks — gamed leaderboard stats"

    # Equity/commodity (0-19% WR)
    if category in BLOCKED_ASSET_CLASSES:
        return True, f"Non-crypto asset class '{category}' blocked (0-19% WR)"

    return False, ""


class HedgeFundSprint:
    """
    Master orchestrator for the Hedge Fund Sprint enhancements.

    Chains together:
      1. Hard-kill filter (generator-level removal of garbage sources)
      2. ML health check (halt ML if engine degraded)
      3. Dual execution engine (ML scalping vs Whale swing pipelines)
      4. Concentration model (capital allocation + position sizing)
      5. Score gate enforcement (≥55 or blocked)
    """

    def __init__(self):
        self._execution_engine = DualExecutionEngine()
        self._concentration = ConcentrationModel()
        self._ml_monitor = MLHealthMonitor()
        self._ml_health: Optional[dict] = None

    def check_ml_health(self) -> dict:
        """Run ML health check and cache the result."""
        self._ml_health = self._ml_monitor.run_health_check()
        return self._ml_health

    def process(
        self,
        picks: list[dict],
        strategy_perf: Optional[dict] = None,
        run_ml_health_check: bool = True,
    ) -> dict:
        """
        Run all sprint filters on a list of picks.

        Args:
            picks: Raw picks from all generators.
            strategy_perf: Optional strategy_performance dict for promotion evaluation.
            run_ml_health_check: Whether to run ML health check (skip in tests).

        Returns:
            {
                'live_picks': list[dict],      -- sends to execution
                'paper_picks': list[dict],     -- paper tracking only
                'blocked_picks': list[dict],   -- hard-killed or score-gated
                'ml_health': dict,             -- ML engine status
                'allocation_report': dict,     -- concentration model report
                'summary': dict,               -- key metrics
                'processed_at': ISO str
            }
        """
        # Phase 0: ML health check
        if run_ml_health_check:
            ml_health = self.check_ml_health()
        else:
            ml_health = self._ml_health or {"ml_trading_enabled": True, "ml_position_multiplier": 1.0}

        ml_enabled = ml_health.get("ml_trading_enabled", True)
        ml_mult = float(ml_health.get("ml_position_multiplier", 1.0))

        # Phase 1: Hard-kill filter
        hard_killed: list[dict] = []
        surviving: list[dict] = []
        for pick in picks:
            killed, reason = _is_hard_killed(pick)
            if killed:
                p = dict(pick)
                p["_blocked_reason"] = reason
                p["_blocked_phase"] = "hard_kill"
                hard_killed.append(p)
            else:
                surviving.append(pick)

        # Phase 2: Dual execution routing (score gate, TP/SL, pipeline assignment)
        routing_result = self._execution_engine.process_picks(surviving)
        routed_live = routing_result["live"]
        routed_paper = routing_result["paper"]
        routed_blocked = routing_result["blocked"]

        # Phase 3: ML health gate — downgrade ML live picks to paper if engine down
        if not ml_enabled:
            # Demote all ML pipeline picks to paper
            ml_demoted = [p for p in routed_live if p.get("pipeline") == "ML"]
            routed_paper.extend([{**p, "_ml_demoted": True, "_ml_reason": ml_health.get("summary")} for p in ml_demoted])
            routed_live = [p for p in routed_live if p.get("pipeline") != "ML"]
        elif ml_mult < 1.0:
            # Reduce ML position sizes
            for p in routed_live:
                if p.get("pipeline") == "ML":
                    p["position_size_mult"] = ml_mult
                    p["_ml_mult_reduced"] = True

        # Phase 4: Concentration model — enrich with allocation and position sizing
        final_live: list[dict] = []
        for pick in routed_live:
            score = float(pick.get("elite_score", pick.get("pipeline_score", pick.get("score", 0))) or 0)
            enriched = self._concentration.apply_to_pick(pick, score)
            # Apply score-based position sizing multiplier
            size_mult = enriched.get("position_size_mult", 1.0)
            ml_size_adj = ml_mult if pick.get("pipeline") == "ML" else 1.0
            enriched["final_position_size_mult"] = round(size_mult * ml_size_adj, 4)
            final_live.append(enriched)

        # Phase 5: Allocation report
        alloc_report = self._concentration.generate_report(strategy_perf)

        now = datetime.now(timezone.utc).isoformat()
        summary = {
            "input_picks": len(picks),
            "hard_killed": len(hard_killed),
            "score_blocked": len(routed_blocked),
            "live_picks": len(final_live),
            "paper_picks": len(routed_paper),
            "ml_trading_enabled": ml_enabled,
            "ml_position_multiplier": ml_mult,
            "pipeline_breakdown": routing_result["summary"],
            "processed_at": now,
        }

        result = {
            "live_picks": final_live,
            "paper_picks": routed_paper,
            "blocked_picks": hard_killed + routed_blocked,
            "ml_health": ml_health,
            "allocation_report": alloc_report,
            "summary": summary,
            "processed_at": now,
        }

        # Persist status for dashboard
        _save_sprint_status(summary, ml_health)
        return result

    def evaluate_strategy_promotions(self, strategy_perf: dict) -> list[dict]:
        """
        Check all paper-tracked strategies for promotion eligibility.
        Returns list of promoted strategies (if any).
        """
        promoted = []
        for strat_name, perf in strategy_perf.items():
            if not isinstance(perf, dict):
                continue
            trades_count = perf.get("closed_picks", 0)
            if trades_count < 5:
                continue
            # Build a minimal trade list for evaluate_promotion
            wr = perf.get("win_rate", 0)
            # Synthesise outcome list from win_rate + closed_picks
            wins = int(wr * trades_count)
            fake_trades = (
                [{"pnl_pct": 1.0}] * wins +
                [{"pnl_pct": -1.0}] * (trades_count - wins)
            )
            result = self._concentration.evaluate_promotion(strat_name, fake_trades)
            if result["promoted"]:
                promoted.append({"strategy": strat_name, **result})
        return promoted


def _save_sprint_status(summary: dict, ml_health: dict) -> None:
    """Persist sprint status for dashboard consumption."""
    try:
        SPRINT_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SPRINT_STATUS_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "summary": summary,
                "ml_health_summary": ml_health.get("summary", ""),
                "ml_trading_enabled": ml_health.get("ml_trading_enabled", True),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, f, indent=2)
    except Exception:
        pass


def run_sprint_pipeline(picks: list[dict], strategy_perf: Optional[dict] = None) -> dict:
    """
    Convenience top-level function — run all hedge fund sprint filters on picks.

    Returns the full result dict from HedgeFundSprint.process().
    """
    sprint = HedgeFundSprint()
    return sprint.process(picks, strategy_perf)


if __name__ == "__main__":
    # Smoke test
    test_picks = [
        # Should go LIVE (ML pipeline)
        {"strategy": "ml_enhanced_FETUSDT_1d_B_lightgbm", "symbol": "FETUSDT",
         "category": "crypto", "direction": "LONG", "entry_price": 1.50,
         "elite_score": 72, "take_profit": 1.56, "stop_loss": 1.47,
         "confidence": 0.82, "status": "OPEN"},
        # Should go LIVE (Whale pipeline)
        {"strategy": "copy_hl_NMTD_25M", "symbol": "ETHUSDT",
         "category": "crypto", "direction": "LONG", "entry_price": 3000,
         "elite_score": 68, "take_profit": 3090, "stop_loss": 2940,
         "confidence": 0.75, "status": "OPEN"},
        # HARD KILLED — binance_smart_money
        {"strategy": "binance_smart_money", "symbol": "DOGEUSDT",
         "category": "crypto", "direction": "LONG", "entry_price": 0.12,
         "elite_score": 42, "take_profit": 0.124, "stop_loss": 0.118,
         "confidence": 0.62, "status": "OPEN"},
        # BLOCKED — score too low
        {"strategy": "some_random_strategy", "symbol": "XYZUSDT",
         "category": "crypto", "direction": "LONG", "entry_price": 10.0,
         "elite_score": 35, "take_profit": 10.4, "stop_loss": 9.8,
         "confidence": 0.55, "status": "OPEN"},
        # BLOCKED — equity/commodity (0-19% WR)
        {"strategy": "momentum_factor_12m", "symbol": "AAPL",
         "category": "equity", "direction": "LONG", "entry_price": 200.0,
         "elite_score": 62, "take_profit": 208, "stop_loss": 196,
         "confidence": 0.70, "status": "OPEN"},
    ]

    result = run_sprint_pipeline(test_picks, run_ml_health_check=False)
    s = result["summary"]
    print("=== Hedge Fund Sprint Results ===")
    print(f"Input: {s['input_picks']} | Hard-killed: {s['hard_killed']} | Score-blocked: {s['score_blocked']}")
    print(f"Live: {s['live_picks']} | Paper: {s['paper_picks']}")
    print(f"ML enabled: {s['ml_trading_enabled']} | ML mult: {s['ml_position_multiplier']}")
    print(f"\nPipeline breakdown: {s['pipeline_breakdown']}")
    print(f"\nLive picks:")
    for p in result["live_picks"]:
        print(f"  [{p.get('pipeline')}] {p.get('symbol')} score={p.get('elite_score')} "
              f"alloc={p.get('concentration_allocation', 0):.0%} "
              f"size_mult={p.get('final_position_size_mult', 1.0):.1f}x "
              f"TP={p.get('take_profit')} SL={p.get('stop_loss')}")
    print(f"\nBlocked picks:")
    for p in result["blocked_picks"]:
        print(f"  [{p.get('strategy')}] {p.get('symbol')} reason={p.get('_blocked_reason', p.get('pipeline_blocked_reason', '?'))}")
