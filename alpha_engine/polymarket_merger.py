#!/usr/bin/env python3
"""
Polymarket Signal Merger — merges polymarket prediction signals into active_picks.json.

Reads polymarket_signals.json (produced by polymarket_signals.py workflow),
converts SIGNAL-status picks to ACTIVE, and merges into the main active_picks
pipeline. Deduplicates by symbol+direction so we don't stack identical signals.

Entry prices and TP/SL are filled downstream by universal_price_enricher.py
and tp_sl_filler.py.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
ACTIVE_PICKS_PATH = DATA_DIR / "active_picks.json"
POLYMARKET_PATH = DATA_DIR / "polymarket_signals.json"

# Only merge signals with confidence >= this threshold
MIN_CONFIDENCE = 0.60

# Max age in hours — don't merge stale signals
MAX_AGE_HOURS = 24


def load_json(path):
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def merge():
    poly_data = load_json(POLYMARKET_PATH)
    if not poly_data:
        print("[POLYMARKET MERGER] No polymarket_signals.json found — skipping")
        return

    poly_picks = poly_data.get("picks", [])
    if not poly_picks:
        print("[POLYMARKET MERGER] No polymarket picks to merge")
        return

    # Load active picks
    active_data = load_json(ACTIVE_PICKS_PATH)
    if active_data is None:
        active_picks = []
    elif isinstance(active_data, list):
        active_picks = active_data
    else:
        active_picks = active_data.get("picks", [])

    # Build set of existing symbol+direction combos to avoid duplicates
    existing_keys = set()
    for p in active_picks:
        sym = (p.get("symbol") or "").upper()
        dir_ = (p.get("signal_type") or p.get("direction") or "").upper()
        src = (p.get("source_system") or "").lower()
        if sym and dir_:
            existing_keys.add(f"{sym}_{dir_}_{src}")

    now = datetime.now(timezone.utc)
    merged = 0
    skipped_conf = 0
    skipped_dup = 0
    skipped_stale = 0

    for pick in poly_picks:
        # Filter by confidence
        conf = float(pick.get("confidence", 0) or 0)
        if conf < MIN_CONFIDENCE:
            skipped_conf += 1
            continue

        # Check staleness
        created = pick.get("created_at", "")
        if created:
            try:
                pick_time = datetime.fromisoformat(created.replace("Z", "+00:00"))
                age_hours = (now - pick_time).total_seconds() / 3600
                if age_hours > MAX_AGE_HOURS:
                    skipped_stale += 1
                    continue
            except (ValueError, TypeError):
                pass

        sym = (pick.get("symbol") or "").upper()
        dir_ = (pick.get("signal_type") or "").upper()
        key = f"{sym}_{dir_}_polymarket"

        if key in existing_keys:
            skipped_dup += 1
            continue

        # Convert to ACTIVE pick format
        pick["status"] = "ACTIVE"
        pick["category"] = pick.get("category", "crypto")
        pick["direction"] = dir_
        # Ensure it has fields the pipeline expects
        if not pick.get("entry_price"):
            pick["entry_price"] = 0  # Will be filled by universal_price_enricher
        if not pick.get("take_profit"):
            pick["take_profit"] = 0  # Will be filled by tp_sl_filler
        if not pick.get("stop_loss"):
            pick["stop_loss"] = 0

        active_picks.append(pick)
        existing_keys.add(key)
        merged += 1

    print(f"[POLYMARKET MERGER] Merged {merged} picks "
          f"(skipped: {skipped_conf} low-conf, {skipped_dup} dupes, {skipped_stale} stale)")

    # Save back
    if merged > 0:
        if isinstance(active_data, dict):
            active_data["picks"] = active_picks
            out = active_data
        else:
            out = active_picks
        with open(ACTIVE_PICKS_PATH, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, default=str)
        print(f"[POLYMARKET MERGER] Saved {len(active_picks)} total active picks")


if __name__ == "__main__":
    merge()
