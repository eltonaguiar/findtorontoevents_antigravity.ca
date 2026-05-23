"""One-time backfill of asset_class on historical alpha_engine/data/closed_picks.json.

Patch 2 from reports/asset_class_tagger_investigation_2026_05_04.md (companion
to the resolver-side fix in commit 93de0d60e14). Patch 1 only helps picks
resolved AFTER it lands; this script retroactively tags the 6,886 null
picks that already sit in the historical ledger.

Method: apply alpha_engine.outcome_resolver._resolve_asset_class to every
closed pick whose asset_class is null/empty/'UNKNOWN'/'NONE'. Atomic write
(.tmp + replace) so a partial run can't corrupt the ledger. Refuses to
shrink the file (sanity check).

Usage:
    python tools/backfill_asset_class_in_closed_picks.py [--dry-run]

    --dry-run: print what would change but don't write.

Per CLAUDE.md: this DOES mutate a data file. Run on a feature branch and
review the diff before committing. The script does NOT run any dashboard
generators (which the CLAUDE.md mandate forbids locally).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))  # make alpha_engine importable when run from anywhere
LEDGER = REPO / "alpha_engine" / "data" / "closed_picks.json"

SENTINELS = {"", "UNKNOWN", "NONE"}


def needs_backfill(value) -> bool:
    if value is None:
        return True
    return str(value).strip().upper() in SENTINELS


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="Show counts but do not write the file.")
    args = ap.parse_args()

    if not LEDGER.exists():
        print(f"FATAL: {LEDGER} does not exist.", file=sys.stderr)
        return 2

    # Import here so a missing dependency doesn't break --help.
    from alpha_engine.outcome_resolver import _resolve_asset_class

    raw = LEDGER.read_text(encoding="utf-8")
    data = json.loads(raw)
    picks = data.get("picks", data) if isinstance(data, dict) else data
    if not isinstance(picks, list):
        print(f"FATAL: unexpected ledger shape ({type(picks).__name__}).", file=sys.stderr)
        return 2

    before = Counter()
    after = Counter()
    changed = 0
    skipped_no_resolution = 0

    for p in picks:
        before_val = p.get("asset_class")
        before_key = "null" if before_val is None else str(before_val)
        before[before_key] += 1

        if not needs_backfill(before_val):
            after[before_key] += 1
            continue

        # Force re-derivation if the existing value is a sentinel literal.
        scrubbed = dict(p)
        scrubbed["asset_class"] = None
        resolved = _resolve_asset_class(scrubbed)

        if not resolved:
            after[before_key] += 1
            skipped_no_resolution += 1
            continue

        p["asset_class"] = resolved
        after[resolved] += 1
        changed += 1

    print(f"Total picks: {len(picks):,}")
    print(f"\nBefore distribution:")
    for k, n in sorted(before.items(), key=lambda x: -x[1]):
        print(f"  {k:<15} {n:,}")
    print(f"\nAfter distribution:")
    for k, n in sorted(after.items(), key=lambda x: -x[1]):
        print(f"  {k:<15} {n:,}")
    print(f"\nChanged: {changed:,}")
    print(f"Skipped (no resolution): {skipped_no_resolution:,}")

    if args.dry_run:
        print("\n--dry-run: NOT writing ledger.")
        return 0

    if changed == 0:
        print("\nNo changes needed. Ledger left untouched.")
        return 0

    # Atomic write — sanity check that we're not shrinking by >1% (paranoia).
    new_raw = json.dumps(data, indent=2)
    if len(new_raw) < len(raw) * 0.99:
        print(
            f"REFUSED to write: new size ({len(new_raw):,}) shrinks more than "
            f"1% from old ({len(raw):,}). Bailing.",
            file=sys.stderr,
        )
        return 3

    tmp = LEDGER.with_suffix(LEDGER.suffix + ".tmp")
    tmp.write_text(new_raw, encoding="utf-8")
    tmp.replace(LEDGER)
    print(f"\nWrote {LEDGER} ({len(new_raw):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
