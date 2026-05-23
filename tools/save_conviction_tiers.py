#!/usr/bin/env python3
"""
HF Conviction Tier Persistence Fix
Saves conviction tiers to JSON so "High Conviction" button has data.
"""

from pathlib import Path
import json
from datetime import datetime, timezone

_REPO = Path(__file__).parent.parent
_TIER_PATH = _REPO / "config" / "hf_conviction_tiers.json"


def save_conviction_tiers(tiers_data: dict) -> bool:
    """Save conviction tiers to config file."""
    ts = datetime.now(timezone.utc).isoformat()
    tiers_data["_saved_at"] = ts
    try:
        _TIER_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_TIER_PATH, "w") as f:
            json.dump(tiers_data, f, indent=2)
        return True
    except Exception:
        return False


def load_conviction_tiers() -> dict:
    """Load conviction tiers from config file."""
    if _TIER_PATH.exists():
        try:
            with open(_TIER_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def get_high_conviction_picks() -> list:
    """Return picks with conviction tier = S or A."""
    from audit_trail.dashboard_generator import generate_dashboard_data

    data = generate_dashboard_data()
    active = data.get("active", [])
    return [p for p in active if p.get("conviction_tier") in ("S", "A")]


if __name__ == "__main__":
    # Load current tiers and save for persistence
    current = load_conviction_tiers()
    if current:
        save_conviction_tiers(current)
        print(f"Saved conviction tiers to {_TIER_PATH}")
    else:
        # Try to get from dashboard
        picks = get_high_conviction_picks()
        tiers = {"picks": picks, "count": len(picks)}
        save_conviction_tiers(tiers)
        print(f"Saved {len(picks)} high conviction picks")
