#!/usr/bin/env python3
"""One-shot migration: zero pipeline-validated fields on existing clone picks.

Addresses action item B4 from reports/ACTION_ITEMS_REMAINING_2026_04_22.md.

Rationale
---------
copy_trader_intel/strategy_clone_generator.py historically wrote the OKX
whale's self-reported WR into five pipeline-validated fields:
  - forward_trades, forward_wr, forward_validated, elite_score, elite_grade
The seed-time fix (commit 0945e18d52 on fix/reject-exempt-safety-gate)
stops NEW clone picks from doing this, but EXISTING ledger rows still
display elite_grade="A" from marketing WR. This script retroactively
zeros those five fields on clone rows where strat_fwd_trades is null/0
(i.e. the pipeline has not earned real forward stats yet).

The trader's marketing stats are preserved in clone_expected_wr /
clone_expected_pf (already present on each clone row) so the UI can
display them separately as unvalidated expectations.

Safety
------
- Dry-run by default. Pass --apply to modify.
- Creates a timestamped backup before every write.
- Atomic write: temp file + rename.
- Skips rows with strat_fwd_trades > 0 (those have earned real stats).

Usage
-----
    py -3.14 tools/migrate_clone_placeholder_stats.py            # dry-run
    py -3.14 tools/migrate_clone_placeholder_stats.py --apply    # modify
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent

TARGETS = [
    REPO / "alpha_engine" / "data" / "active_picks.json",
    # closed_picks.json intentionally excluded — it has zero clone rows
    # (HC gate correctly rejects clones before they close).
]

FIELDS_TO_ZERO = {
    "forward_trades": 0,
    "forward_wr": 0.0,
    "forward_validated": False,
    "elite_score": 0,
    "elite_grade": "UNGRADED",
}


def is_clone_placeholder(row: dict[str, Any]) -> bool:
    """Row is a clone with no pipeline-validated forward stats."""
    is_clone = (
        row.get("source_system") == "copy_trader_intel"
        or (isinstance(row.get("strategy"), str) and row["strategy"].startswith("clone_hl_"))
    )
    if not is_clone:
        return False
    sft = row.get("strat_fwd_trades")
    # Skip rows that have earned real forward stats.
    if sft is not None and sft > 0:
        return False
    # Only migrate rows that currently carry a non-zero elite_score or
    # a forward_wr value (evidence of marketing-WR seeding).
    has_placeholder = (row.get("elite_score") or 0) > 0 or (row.get("forward_wr") or 0) > 0
    return has_placeholder


def migrate_rows(rows: list[dict]) -> tuple[list[dict], int]:
    changed = 0
    out: list[dict] = []
    for row in rows:
        if not is_clone_placeholder(row):
            out.append(row)
            continue
        new_row = dict(row)
        for field, default in FIELDS_TO_ZERO.items():
            if field in new_row:
                new_row[field] = default
        # Mark the migration so the UI can explain the zero grade.
        new_row["clone_stats_migrated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        out.append(new_row)
        changed += 1
    return out, changed


def atomic_write_json(path: Path, data: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(path)


def backup(path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bk = path.with_name(f"{path.stem}.backup-{stamp}{path.suffix}")
    shutil.copyfile(path, bk)
    return bk


def sample_diff(before_rows: list[dict], after_rows: list[dict], limit: int = 3) -> list[dict]:
    samples: list[dict] = []
    for b, a in zip(before_rows, after_rows):
        if b is a or b == a:
            continue
        diff = {"id": b.get("id"), "symbol": b.get("symbol"), "strategy": b.get("strategy")}
        for f in FIELDS_TO_ZERO:
            if b.get(f) != a.get(f):
                diff[f] = {"before": b.get(f), "after": a.get(f)}
        samples.append(diff)
        if len(samples) >= limit:
            break
    return samples


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="modify files (default: dry-run)")
    args = ap.parse_args()

    total_changed = 0
    for path in TARGETS:
        if not path.exists():
            print(f"[skip] {path} does not exist")
            continue
        data = json.loads(path.read_text())
        rows = data if isinstance(data, list) else data.get("picks", [])
        if not isinstance(rows, list):
            print(f"[skip] {path}: unexpected schema")
            continue

        new_rows, changed = migrate_rows(rows)
        total_changed += changed

        diff = sample_diff(rows, new_rows)
        print(f"\n{path.relative_to(REPO)}")
        print(f"  total_rows: {len(rows)}")
        print(f"  clone_placeholder_rows_flagged: {changed}")
        if diff:
            print("  sample_diff:")
            for d in diff:
                print(f"    {json.dumps(d)}")

        if not args.apply:
            continue

        if changed == 0:
            print("  [no-op] nothing to change")
            continue

        bk = backup(path)
        print(f"  backup -> {bk.relative_to(REPO)}")

        if isinstance(data, list):
            atomic_write_json(path, new_rows)
        else:
            data["picks"] = new_rows
            atomic_write_json(path, data)
        print(f"  wrote {path.relative_to(REPO)} (atomic)")

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"\n[{mode}] total rows that would change: {total_changed}")
    if not args.apply:
        print("Re-run with --apply to modify files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
