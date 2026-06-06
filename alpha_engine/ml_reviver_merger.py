#!/usr/bin/env python3
"""
Merge ML Reviver picks into alpha_engine/data/active_picks.json.

Standalone script that can be called from the workflow or CLI.
Reads ml_reviver_picks.json, merges into active_picks.json with dedup.
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path(__file__).resolve().parent / "data"
REVIVER_PATH = DATA_DIR / "ml_reviver_picks.json"
ACTIVE_PATH = DATA_DIR / "active_picks.json"


def merge_reviver_picks() -> int:
    if not REVIVER_PATH.exists():
        print("No reviver picks to merge.")
        return 0

    with open(REVIVER_PATH) as f:
        reviver_picks = json.load(f)

    if not reviver_picks:
        print("Reviver returned empty picks.")
        return 0

    # Load existing active picks
    existing = []
    if ACTIVE_PATH.exists():
        with open(ACTIVE_PATH) as f:
            existing = json.load(f)

    # Build keys for dedup
    existing_keys = set()
    for p in existing:
        k = (p.get("strategy", ""), p.get("symbol", ""))
        existing_keys.add(k)

    added = 0
    for p in reviver_picks:
        p["category"] = "CRYPTO"
        p["asset_class"] = "CRYPTO"
        k = (p.get("strategy", ""), p.get("symbol", ""))
        if k not in existing_keys:
            existing.append(p)
            existing_keys.add(k)
            added += 1
            print(f"  MERGED: {p.get('strategy', '?')} {p.get('symbol', '?')} "
                  f"{p.get('direction', '?')} conf={p.get('confidence', 0):.2f}")

    if added:
        with open(ACTIVE_PATH, "w") as f:
            json.dump(existing, f, indent=2, default=str)
        print(f"Merged {added} reviver picks into active_picks.json (total: {len(existing)})")
    else:
        print("All reviver picks already in active_picks.json")

    return added


if __name__ == "__main__":
    merge_reviver_picks()
