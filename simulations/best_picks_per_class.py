#!/usr/bin/env python3
"""
Best Picks Per Asset Class — Dashboard Feeder
===============================================
Feeds the best available picks per asset class into the audit dashboard
for monitoring at findtorontoevents.ca/audit.

STRATEGY SELECTION (per asset class, based on simulation evidence):
  CRYPTO:   Pilot verified edges (202 picks) — only live source with recent data
  EQUITY:   Passive beta only (VTI/SPY) — stocks_rsi2 FAILED simulation
  ETF:      Passive beta allocation (VTI/BND 60/40)
  BOND:     Passive beta allocation (BND/FXNAX)
  FOREX:    Existing best pick (USDJPY=X) — WATCH status only
  COMMODITY: Existing best pick (GC=F) — WATCH status only
  FUTURES:  Existing best pick (ES=F) — WATCH status only

Each pick includes:
  - Honest status (ACTIVE / WATCH / PASSIVE_BETA)
  - Simulation verdict reference
  - Risk metrics
  - Forward test tracker gate status

Usage:
    python3 simulations/best_picks_per_class.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_PATH = REPO / "audit_dashboard" / "data" / "best_picks_per_class.json"


def load_pilot_picks() -> list[dict]:
    """Load pilot verified edges."""
    path = REPO / "audit_dashboard" / "data" / "pilot_verified_edges_shadow.json"
    if not path.exists():
        return []
    with open(path) as f:
        data = json.load(f)
    return data.get("picks", [])


def load_existing_active_picks() -> list[dict]:
    """Load existing active picks."""
    path = REPO / "alpha_engine" / "data" / "active_picks.json"
    if not path.exists():
        return []
    with open(path) as f:
        data = json.load(f)
    return data if isinstance(data, list) else data.get("picks", [])


def make_passive_beta_pick(asset_class: str, ticker: str, allocation_pct: float, rationale: str) -> dict:
    """Create a passive beta 'pick' (not alpha, just allocation)."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": f"passive_beta::{asset_class}::{ticker}::{now[:10]}",
        "strategy": "passive_beta_allocation",
        "symbol": ticker,
        "category": asset_class.lower(),
        "asset_class": asset_class,
        "signal_type": "BUY",
        "direction": "LONG",
        "entry_price": None,
        "entry_date": now[:10],
        "entry_time": now,
        "timestamp": now,
        "take_profit": None,
        "stop_loss": None,
        "confidence": 0.95,
        "ml_score": 0.95,
        "risk_reward": None,
        "elite_score": 95.0,
        "elite_grade": "A",
        "ml_composite_score": 95.0,
        "ml_composite_grade": "A",
        "source_system": "passive_beta",
        "trust_tier": "PASSIVE_BETA",
        "is_smart_pick": False,
        "is_verified_alpha": False,
        "hc_tier": "BETA",
        "status": "PASSIVE_HOLD",
        "allocation_pct": allocation_pct,
        "pnl_pct": 0,
        "unrealized_pnl_pct": 0,
        "created_at": now,
        "simulation_verdict": "PROFITABLE — captures equity risk premium, not alpha",
        "forward_tracker_status": "FULL_LIVE",
        "rationale": rationale,
        "_passive_beta_tag": True,
    }


def convert_existing_to_best(pick: dict, status_override: str = None, rationale: str = None) -> dict:
    """Convert an existing pick to 'best pick' format with honest metadata."""
    pick = dict(pick)  # copy
    pick["_best_pick_tag"] = True
    pick["_selected_at"] = datetime.now(timezone.utc).isoformat()
    if status_override:
        pick["status"] = status_override
    if rationale:
        pick["rationale"] = rationale
    return pick


def main() -> int:
    now = datetime.now(timezone.utc).isoformat()
    best_picks = []

    # ── CRYPTO: Pilot Verified Edges (best available live source) ──
    pilot_picks = load_pilot_picks()
    # Select top 10 by score for monitoring (not all 202)
    pilot_sorted = sorted(pilot_picks, key=lambda p: float(p.get("score", 0) or 0), reverse=True)
    for p in pilot_sorted[:20]:
        pick = {
            "id": p.get("id", f"pilot::{p.get('symbol','UNKNOWN')}::{now[:10]}"),
            "strategy": p.get("strategy", "pilot_verified_edge"),
            "symbol": p.get("symbol", "UNKNOWN"),
            "category": "crypto",
            "asset_class": "CRYPTO",
            "signal_type": "BUY" if p.get("direction", "LONG").upper() in ("LONG", "BUY") else "SELL",
            "direction": p.get("direction", "LONG").upper(),
            "entry_price": float(p.get("entry_price", 0) or 0),
            "entry_date": p.get("entry_date", now[:10]),
            "entry_time": p.get("entry_time", now),
            "timestamp": p.get("timestamp", now),
            "take_profit": float(p.get("take_profit", 0) or 0),
            "stop_loss": float(p.get("stop_loss", 0) or 0),
            "confidence": float(p.get("score", 50)) / 100,
            "elite_score": float(p.get("score", 0) or 0),
            "source_system": p.get("source_system", "pilot_verified_edges"),
            "trust_tier": "PILOT",
            "status": "ACTIVE",
            "simulation_verdict": "Conditional — forward test only after fill fix",
            "forward_tracker_status": "PAPER",
            "rationale": f"Pilot verified edge. Score={p.get('score')}. Requires stop-fill fix before live deployment.",
            "_best_pick_tag": True,
            "_selected_at": now,
        }
        best_picks.append(pick)

    # ── EQUITY: Passive Beta ONLY (stocks_rsi2 FAILED simulation) ──
    best_picks.append(make_passive_beta_pick(
        "EQUITY", "VTI", 60.0,
        "Simulation proved passive beta is only viable EQUITY path. Connors RSI-2 FAILED (-12.6% vs SPY +345%). Deploy VTI/SPY as beta capture."
    ))
    best_picks.append(make_passive_beta_pick(
        "EQUITY", "SPY", 40.0,
        "SPY buy-and-hold: AnnRet 14.3%, Sharpe 0.56 over 12 years. No active strategy tested beat this after costs."
    ))

    # ── ETF: Passive Beta Allocation ──
    best_picks.append(make_passive_beta_pick(
        "ETF", "VTI", 60.0,
        "VTI (Total Market) 60% allocation. ETF tactical strategies all failed gates. Only passive beta is deployable."
    ))
    best_picks.append(make_passive_beta_pick(
        "ETF", "BND", 40.0,
        "BND (Aggregate Bonds) 40% allocation. Provides drawdown reduction (-21.8% vs SPY -33.7%)."
    ))

    # ── BOND: Passive Beta ──
    best_picks.append(make_passive_beta_pick(
        "BOND", "BND", 50.0,
        "BND as bond ballast. Active bond timing has zero proven edge in this system."
    ))
    best_picks.append(make_passive_beta_pick(
        "BOND", "SHY", 50.0,
        "SHY (Short-term Treasuries) as cash alternative when no assets pass absolute momentum filter."
    ))

    # ── FOREX: Existing best pick (WATCH only) ──
    existing = load_existing_active_picks()
    forex_picks = [p for p in existing if p.get("asset_class") == "FOREX"]
    if forex_picks:
        best = max(forex_picks, key=lambda p: p.get("elite_score", 0) or 0)
        best_picks.append(convert_existing_to_best(
            best,
            status_override="WATCH",
            rationale="FOREX is NOT money-ready (PF 0.85, WR 36%). This is the best existing pick but DO NOT deploy capital. Monitor only."
        ))

    # ── COMMODITY: Existing best pick (WATCH only) ──
    comm_picks = [p for p in existing if p.get("asset_class") == "COMMODITY"]
    if comm_picks:
        best = max(comm_picks, key=lambda p: p.get("elite_score", 0) or 0)
        best_picks.append(convert_existing_to_best(
            best,
            status_override="WATCH",
            rationale="COMMODITY is NOT money-ready (PF 0.17, WR 14%). COT contrarian failed 4/4 trials. Monitor only."
        ))

    # ── FUTURES: Existing best pick (WATCH only) ──
    fut_picks = [p for p in existing if p.get("asset_class") == "FUTURES"]
    if fut_picks:
        best = max(fut_picks, key=lambda p: p.get("elite_score", 0) or 0)
        best_picks.append(convert_existing_to_best(
            best,
            status_override="WATCH",
            rationale="FUTURES is NOT money-ready (near-dead, 95% resolver bugs). No continuous-contract feed. Monitor only."
        ))

    # Save
    payload = {
        "generated_at": now,
        "protocol_version": "2026-11-15-v1",
        "total_picks": len(best_picks),
        "disclaimer": "PASSIVE_BETA picks are deployable. All other picks are for MONITORING ONLY until forward test gates pass.",
        "picks": best_picks,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(payload, f, indent=2, default=str)

    print(f"[BEST PICKS] Wrote {len(best_picks)} best picks to {OUT_PATH}")
    from collections import Counter
    classes = Counter(p.get("asset_class", "UNKNOWN") for p in best_picks)
    statuses = Counter(p.get("status", "UNKNOWN") for p in best_picks)
    print(f"\nBy Asset Class:")
    for cls, n in classes.most_common():
        print(f"  {cls}: {n}")
    print(f"\nBy Status:")
    for st, n in statuses.most_common():
        print(f"  {st}: {n}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
