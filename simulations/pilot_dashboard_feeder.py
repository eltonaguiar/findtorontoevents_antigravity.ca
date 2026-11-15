#!/usr/bin/env python3
"""
Pilot Picks Dashboard Feeder
============================
Reads the pilot verified edges shadow log and converts picks into the
standard dashboard active_picks format for monitoring at
findtorontoevents.ca/audit.

Usage:
    python3 simulations/pilot_dashboard_feeder.py
    
This appends pilot picks to alpha_engine/data/active_picks.json so they
appear in the audit dashboard alongside other active picks.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PILOT_PATH = REPO / "audit_dashboard" / "data" / "pilot_verified_edges_shadow.json"
ACTIVE_PICKS_PATH = REPO / "alpha_engine" / "data" / "active_picks.json"
OUTPUT_PATH = REPO / "alpha_engine" / "data" / "active_picks_pilot.json"


def load_pilot_picks() -> list[dict]:
    """Load pilot verified edge picks."""
    if not PILOT_PATH.exists():
        print(f"[ERROR] Pilot file not found: {PILOT_PATH}")
        return []
    with open(PILOT_PATH) as f:
        data = json.load(f)
    picks = data.get("picks", [])
    print(f"[FEEDER] Loaded {len(picks)} pilot picks from {PILOT_PATH}")
    return picks


def convert_to_dashboard_format(pilot_pick: dict) -> dict:
    """Convert a pilot pick to the standard dashboard active_picks format."""
    now = datetime.now(timezone.utc).isoformat()
    
    # Determine category/asset class
    asset_class = pilot_pick.get("asset_class", pilot_pick.get("category", "CRYPTO")).upper()
    if asset_class in ("CRYPTO", "CRYPTOCURRENCY"):
        category = "crypto"
    elif asset_class in ("EQUITY", "STOCK", "STOCKS"):
        category = "equity"
    elif asset_class == "FOREX":
        category = "forex"
    elif asset_class == "ETF":
        category = "etf"
    elif asset_class == "COMMODITY":
        category = "commodity"
    elif asset_class == "BOND":
        category = "bond"
    else:
        category = "crypto"

    direction = pilot_pick.get("direction", "LONG").upper()
    signal_type = "BUY" if direction in ("LONG", "BUY") else "SELL"

    # Map score to confidence
    score = float(pilot_pick.get("score", pilot_pick.get("elite_score", 50)) or 50)
    confidence = min(1.0, score / 100)

    # Build dashboard pick
    dashboard_pick = {
        "id": pilot_pick.get("id", f"pilot::{pilot_pick.get('symbol','UNKNOWN')}::{now[:10]}"),
        "strategy": pilot_pick.get("strategy", "pilot_verified_edge"),
        "symbol": pilot_pick.get("symbol", "UNKNOWN"),
        "category": category,
        "signal_type": signal_type,
        "direction": direction,
        "entry_price": float(pilot_pick.get("entry_price", 0) or 0),
        "entry_date": pilot_pick.get("entry_date", now[:10]),
        "entry_time": pilot_pick.get("entry_time", now),
        "timestamp": pilot_pick.get("timestamp", now),
        "take_profit": float(pilot_pick.get("take_profit", 0) or 0),
        "stop_loss": float(pilot_pick.get("stop_loss", 0) or 0),
        "confidence": round(confidence, 4),
        "ml_score": round(confidence, 4),
        "risk_reward": float(pilot_pick.get("risk_reward", pilot_pick.get("rr", 1.5)) or 1.5),
        "elite_score": round(score, 2),
        "elite_grade": "B" if score >= 50 else "C" if score >= 40 else "F",
        "ml_composite_score": round(score, 2),
        "ml_composite_grade": "B" if score >= 50 else "C" if score >= 40 else "F",
        "asset_class": asset_class,
        "source_system": pilot_pick.get("source_system", "pilot_verified_edges"),
        "trust_tier": "PILOT",
        "is_smart_pick": False,
        "is_verified_alpha": False,
        "hc_tier": None,
        "pnl_pct": float(pilot_pick.get("pnl_pct", 0) or 0),
        "status": pilot_pick.get("status", "ACTIVE"),
        "unrealized_pnl_pct": float(pilot_pick.get("pnl_pct", 0) or 0),
        "created_at": pilot_pick.get("created_at", now),
        "_pilot_tag": True,
        "_pilot_generated_at": now,
    }

    return dashboard_pick


def main() -> int:
    pilot_picks = load_pilot_picks()
    if not pilot_picks:
        print("[FEEDER] No pilot picks to feed.")
        return 0

    # Convert all pilot picks to dashboard format
    dashboard_picks = [convert_to_dashboard_format(p) for p in pilot_picks]

    # Load existing active picks if present
    existing = []
    if ACTIVE_PICKS_PATH.exists():
        try:
            with open(ACTIVE_PICKS_PATH) as f:
                data = json.load(f)
            if isinstance(data, list):
                existing = data
            else:
                existing = data.get("picks", data.get("active_picks", []))
            print(f"[FEEDER] Loaded {len(existing)} existing active picks.")
        except Exception as exc:
            print(f"[WARNING] Could not load existing picks: {exc}")

    # Deduplicate by id
    existing_ids = {p.get("id") for p in existing}
    new_picks = [p for p in dashboard_picks if p.get("id") not in existing_ids]
    print(f"[FEEDER] {len(new_picks)} new pilot picks to add (after dedup).")

    # Combine
    combined = existing + new_picks
    print(f"[FEEDER] Total active picks after merge: {len(combined)}")

    # Write combined output
    with open(OUTPUT_PATH, "w") as f:
        json.dump(combined, f, indent=2, default=str)
    print(f"[FEEDER] Wrote combined picks to {OUTPUT_PATH}")

    # Also write just the pilot picks for monitoring
    pilot_only_path = REPO / "audit_dashboard" / "data" / "pilot_active_picks.json"
    with open(pilot_only_path, "w") as f:
        json.dump(dashboard_picks, f, indent=2, default=str)
    print(f"[FEEDER] Wrote pilot-only picks to {pilot_only_path}")

    # Summary by asset class
    from collections import Counter
    classes = Counter(p.get("asset_class", "UNKNOWN") for p in dashboard_picks)
    print(f"\n[FEEDER] Pilot picks by asset class:")
    for cls, count in classes.most_common():
        print(f"  {cls}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
