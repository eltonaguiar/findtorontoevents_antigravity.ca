#!/usr/bin/env python3
"""Idempotent patcher for scripts/actions_failure_guardian.py.

Adds (1) an exclude list and (2) a run_attempt retry cap so the guardian stops
re-running permanently-failing / verification workflows (the backup-verify
issue-flood loop).

Run from repo root. Default is a DRY RUN; pass --apply to write.

    python3 .../apply_guardian_fix.py            # dry run, prints diff plan
    python3 .../apply_guardian_fix.py --apply    # writes the file
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

TARGET = Path("scripts/actions_failure_guardian.py")

ANCHOR_ROW = '            "created_at": latest.get("created_at"),\n'
INSERT_ROW = '            "run_attempt": latest.get("run_attempt", 1),\n'

ANCHOR_CFG = '    max_age_hours = float(os.getenv("FAILURE_GUARD_MAX_AGE_HOURS", "72"))\n'
INSERT_CFG = (
    '    excluded = {\n'
    '        s.strip().lower()\n'
    '        for s in os.getenv("FAILURE_GUARD_EXCLUDE", "").split(",")\n'
    '        if s.strip()\n'
    '    }\n'
    '    max_attempt = int(os.getenv("FAILURE_GUARD_MAX_ATTEMPT", "3"))\n'
)

ANCHOR_LOOP = '        run_id = int(row["run_id"])\n'
INSERT_LOOP = (
    '        _name = (row.get("workflow_name") or "").strip().lower()\n'
    '        if _name in excluded:\n'
    '            row["rerun_message"] = "skipped (workflow in FAILURE_GUARD_EXCLUDE)"\n'
    '            continue\n'
    '        if int(row.get("run_attempt") or 1) >= max_attempt:\n'
    '            row["rerun_message"] = (\n'
    '                f"skipped (run_attempt {row.get(\'run_attempt\')} >= cap {max_attempt})"\n'
    '            )\n'
    '            continue\n'
)


def patch_once(text: str, anchor: str, insert: str) -> tuple[str, bool]:
    if insert.strip().splitlines()[0].strip() in text:
        return text, False  # already applied
    if anchor not in text:
        print(f"!! anchor not found: {anchor!r}", file=sys.stderr)
        return text, False
    return text.replace(anchor, anchor + insert, 1), True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not TARGET.exists():
        print(f"not found: {TARGET}", file=sys.stderr)
        return 1
    original = TARGET.read_text(encoding="utf-8")
    text = original
    changed = False
    for anchor, insert in (
        (ANCHOR_ROW, INSERT_ROW),
        (ANCHOR_CFG, INSERT_CFG),
        (ANCHOR_LOOP, INSERT_LOOP),
    ):
        text, did = patch_once(text, anchor, insert)
        changed = changed or did
        print(("patched" if did else "already/noop") + f": {anchor.strip()[:50]}")

    if not changed:
        print("nothing to do.")
        return 0
    if args.apply:
        TARGET.write_text(text, encoding="utf-8")
        print(f"WROTE {TARGET}")
    else:
        print("DRY RUN — re-run with --apply to write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
