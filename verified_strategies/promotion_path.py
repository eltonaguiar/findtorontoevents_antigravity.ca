#!/usr/bin/env python3
"""Unified promotion path (ENHANCEMENT_OVERALL #66).

Problem: the project keeps two scoreboards. The AI-tournament leaderboard
(ai-tournament.html) scores picks under generous labels/costs; the production
money_ready_verdict scores the policy-clean ledger. The same model/strategy
shows PF ~3 on one and PF <1 on the other (EAGLE2 synthesis 2026-06-02). Edge
that looks real on the tournament board dies in production.

This module makes the harness the SINGLE promotion path:

  1. `canonical_promotion()` — the one entrypoint anything must call before a
     sleeve can affect capital. It delegates to the existing
     AdmissibilityPipeline (purged-embargoed walk-forward + per-class cost model
     + DSR/PBO + concentration) and attaches the #67 shadow-size plan. There is
     no second path.
  2. `reconcile_scoreboards()` — the two-scoreboard DRIFT DETECTOR. Given a
     sleeve's tournament PF and its production policy-clean PF, it flags when
     the two disagree beyond tolerance. Advisory/shadow-first: it surfaces the
     split so nobody promotes on the rosier board; it changes no live sizing.

Shadow-first: importing/calling this never sizes capital by itself — it returns
verdict + plan + drift dicts that the sizing/promotion layer reads.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from admissibility_pipeline import (
    AdmissibilityPipeline,
    CostModel,
    shadow_size_plan,
)
from return_attribution import attribution_gate

# Tournament PF and production policy-clean PF for the SAME sleeve should not
# diverge by more than this fraction once both use purged-embargoed labels +
# the same cost model. Beyond it, the tournament number is not promotable.
SCOREBOARD_PF_TOLERANCE = 0.25   # 25% relative divergence


def canonical_cost_model(asset_class: str) -> CostModel:
    """Single source of cost truth — both scoreboards must use this."""
    return CostModel.for_class(asset_class.upper())


def reconcile_scoreboards(sleeve: str, tournament_pf: Optional[float],
                          production_pf: Optional[float],
                          tolerance: float = SCOREBOARD_PF_TOLERANCE) -> Dict[str, Any]:
    """Two-scoreboard drift detector.

    ok=True  — boards agree within tolerance (or one side missing -> can't drift)
    ok=False — boards diverge beyond tolerance (do NOT promote on the rosier one)
    """
    if tournament_pf is None or production_pf is None:
        return {"sleeve": sleeve, "ok": None, "divergence": None,
                "tournament_pf": tournament_pf, "production_pf": production_pf,
                "note": "one scoreboard missing — cannot reconcile"}
    base = max(abs(production_pf), 1e-9)
    divergence = abs(tournament_pf - production_pf) / base
    ok = divergence <= tolerance
    return {
        "sleeve": sleeve,
        "ok": ok,
        "divergence": round(divergence, 4),
        "tolerance": tolerance,
        "tournament_pf": round(tournament_pf, 4),
        "production_pf": round(production_pf, 4),
        "promotable_on_tournament": ok,
        "note": "" if ok else (
            f"tournament PF {tournament_pf:.2f} diverges {divergence*100:.0f}% from "
            f"production {production_pf:.2f} — promote on production board only"),
    }


def canonical_promotion(strategy_name: str, asset_class: str,
                        equity_curve, trades: List[Dict],
                        output_dir: str = "reports/admissibility",
                        sleeve_returns: Optional[List[float]] = None,
                        market_returns: Optional[List[float]] = None,
                        style_returns: Optional[List[float]] = None) -> Dict[str, Any]:
    """The ONE promotion path: run the admissibility harness, attach the
    shadow-size plan + (if a benchmark is supplied) the #111 return-attribution
    leg, and return a single canonical verdict dict. Anything that would size
    capital must route through here — no second path."""
    pipeline = AdmissibilityPipeline(output_dir=output_dir)
    result = pipeline.run_pipeline(strategy_name, asset_class, equity_curve, trades)
    out = result.to_dict()
    # to_dict already carries shadow_size_plan from Step 10; ensure present.
    if out.get("shadow_size_plan") is None:
        out["shadow_size_plan"] = shadow_size_plan(
            out.get("overall_verdict") == "PASS")
    # ENHANCEMENT #111: attribution leg — is the edge alpha, or just beta/style?
    # Advisory (shadow): attached when a market benchmark is provided; it does
    # not change overall_verdict on its own.
    if market_returns is not None and sleeve_returns is not None:
        out["attribution"] = attribution_gate(sleeve_returns, market_returns, style_returns)
    out["promotion_path"] = "canonical"
    return out


def batch_reconcile(pairs: List[Dict[str, Any]],
                    tolerance: float = SCOREBOARD_PF_TOLERANCE) -> Dict[str, Any]:
    """Reconcile many sleeves; summarize how many drift. Each pair:
    {sleeve, tournament_pf, production_pf}."""
    rows = [reconcile_scoreboards(p.get("sleeve", "?"),
                                  p.get("tournament_pf"), p.get("production_pf"),
                                  tolerance) for p in pairs]
    drifting = [r for r in rows if r["ok"] is False]
    return {"n": len(rows), "n_drift": len(drifting),
            "drifting_sleeves": [r["sleeve"] for r in drifting], "rows": rows}
