#!/usr/bin/env python3
"""
Deduplicate ai_tournament_picks_latest.json by (symbol, data_source, thesis, entry_price).

The file accumulates duplicate entries over time — the same picks repeated 3+ times
from multiple submission runs. This script keeps only the latest entry for each unique
(symbol, data_source, thesis, entry_price) tuple.

Usage:
    python tools/dedup_tournament_picks.py          # dry-run (show counts)
    python tools/dedup_tournament_picks.py --write   # actually deduplicate and save
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LATEST_PICKS = REPO_ROOT / "audit_dashboard" / "data" / "ai_tournament_picks_latest.json"

WRITE = "--write" in sys.argv


def dedup_key(pick: dict) -> tuple:
    """Return dedup key: (symbol, data_source, thesis, entry_price)."""
    return (
        pick.get("symbol", ""),
        pick.get("data_source", ""),
        pick.get("thesis", ""),
        pick.get("entry_price", 0),
    )


def main() -> None:
    if not LATEST_PICKS.exists():
        print(f"[dedup] File not found: {LATEST_PICKS}")
        return

    picks = json.loads(LATEST_PICKS.read_text())
    if not isinstance(picks, list):
        print(f"[dedup] Expected list, got {type(picks).__name__}")
        return

    print(f"[dedup] Loaded {len(picks)} picks from {LATEST_PICKS.name}")

    # Group by dedup key, keep latest by submitted_at
    best: dict[tuple, dict] = {}
    for p in picks:
        key = dedup_key(p)
        existing = best.get(key)
        if existing is None:
            best[key] = p
        else:
            # Keep the one with the latest submitted_at
            existing_ts = existing.get("submitted_at", "")
            current_ts = p.get("submitted_at", "")
            if current_ts > existing_ts:
                best[key] = p

    deduped = list(best.values())
    removed = len(picks) - len(deduped)

    print(f"[dedup] {len(picks)} -> {len(deduped)} picks ({removed} duplicates removed)")

    if removed > 0:
        # Show some examples of what was removed
        seen_keys = set(dedup_key(p) for p in deduped)
        dup_samples = set()
        for p in picks:
            key = dedup_key(p)
            if p not in deduped and len(dup_samples) < 5:
                dup_samples.add(f"{p.get('symbol', '?')}/{p.get('data_source', '?')}/{p.get('thesis', '?')}")
        if dup_samples:
            print(f"[dedup] Sample deduped keys: {', '.join(sorted(dup_samples))}")

    if WRITE:
        backup = LATEST_PICKS.with_suffix(f".{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json.bak")
        LATEST_PICKS.rename(backup)
        LATEST_PICKS.write_text(json.dumps(deduped, indent=2))
        print(f"[dedup] Written {len(deduped)} picks (backup: {backup.name})")
    else:
        print("[dedup] Dry-run. Pass --write to actually deduplicate.")


if __name__ == "__main__":
    main()
