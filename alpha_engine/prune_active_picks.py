#!/usr/bin/env python3
"""prune_active_picks — remove expired entries from alpha_engine/data/active_picks.json.

Picks expire when:
  1. expires_at field is past, OR
  2. timestamp/created_at + MAX_HOLD_HOURS_BY_CLASS is past (no expires_at)

Expired picks are archived to alpha_engine/data/expired_picks_archive.json
before removal so the data is not lost.

Usage:
    python alpha_engine/prune_active_picks.py            # live prune
    python alpha_engine/prune_active_picks.py --dry-run  # preview only
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "alpha_engine" / "data"
ACTIVE_PICKS_FILE = DATA_DIR / "active_picks.json"
ARCHIVE_FILE = DATA_DIR / "expired_picks_archive.json"

# Max hold hours by asset class — mirrors outcome_resolver.py defaults.
MAX_HOLD_HOURS: dict[str, int] = {
    "CRYPTO":    48,
    "EQUITY":    120,
    "STOCKS":    120,
    "FOREX":     120,
    "COMMODITY": 336,   # 14 days
    "ETF":       120,
    "BOND":      240,
    "FUTURES":   120,
}
DEFAULT_MAX_HOLD_HOURS = 168  # 7 days fallback


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def is_expired(pick: dict, now: datetime) -> bool:
    exp = _parse_dt(pick.get("expires_at"))
    if exp is not None:
        return exp < now
    ts = _parse_dt(pick.get("timestamp") or pick.get("created_at") or pick.get("entry_time"))
    if ts is None:
        return False
    asset_class = (pick.get("asset_class") or "").upper()
    max_hours = MAX_HOLD_HOURS.get(asset_class, DEFAULT_MAX_HOLD_HOURS)
    from datetime import timedelta
    return ts + timedelta(hours=max_hours) < now


def main() -> int:
    ap = argparse.ArgumentParser(description="Prune expired picks from active_picks.json")
    ap.add_argument("--dry-run", action="store_true", help="Preview only, no writes")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)

    if not ACTIVE_PICKS_FILE.exists():
        print("active_picks.json not found — nothing to prune")
        return 0

    with open(ACTIVE_PICKS_FILE, encoding="utf-8") as f:
        all_picks: list[dict] = json.load(f)

    fresh = [p for p in all_picks if not is_expired(p, now)]
    expired = [p for p in all_picks if is_expired(p, now)]

    print(f"active_picks.json: {len(all_picks)} total, {len(expired)} expired, {len(fresh)} fresh")

    if not expired:
        print("Nothing to prune.")
        return 0

    from collections import Counter
    sources = Counter(p.get("source_system", "?") for p in expired)
    print("Expired by source:")
    for src, n in sources.most_common():
        print(f"  {n:3d}  {src}")

    if args.dry_run:
        print("[DRY-RUN] No changes written.")
        return 0

    # Archive expired picks (append to existing archive).
    archive: list[dict] = []
    if ARCHIVE_FILE.exists():
        try:
            with open(ARCHIVE_FILE, encoding="utf-8") as f:
                archive = json.load(f)
        except (json.JSONDecodeError, OSError):
            archive = []

    pruned_at = now.isoformat()
    for p in expired:
        p["_pruned_at"] = pruned_at
        archive.append(p)

    with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
        json.dump(archive, f, indent=2)

    with open(ACTIVE_PICKS_FILE, "w", encoding="utf-8") as f:
        json.dump(fresh, f, indent=2)

    print(f"Pruned {len(expired)} expired picks → archived to expired_picks_archive.json")
    print(f"active_picks.json now has {len(fresh)} picks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
