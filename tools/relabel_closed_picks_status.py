#!/usr/bin/env python3
"""Relabel closed_picks_enriched.json (and source closed_picks.json) rows where
status == 'CLOSED' to 'WON' or 'LOST' based on pnl_pct sign.

Safe to re-run: idempotent (only touches status='CLOSED' rows).
Dry-run by default. Pass --apply to actually mutate the file.

See: reports/2026-05-26_phase1_2_pnl_integrity_audit.md
"""
import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="alpha_engine/data/closed_picks_enriched.json")
    ap.add_argument("--apply", action="store_true", help="Mutate the file. Default is dry-run.")
    args = ap.parse_args()

    src = Path(args.source)
    if not src.exists():
        raise SystemExit(f"Source not found: {src}")

    data = json.loads(src.read_text())
    picks = data["picks"] if isinstance(data, dict) else data

    changed = []
    skipped_null_pnl = 0
    skipped_zero_pnl = 0

    for p in picks:
        if (p.get("status") or "").upper() != "CLOSED":
            continue
        pp_raw = p.get("pnl_pct")
        if pp_raw is None:
            skipped_null_pnl += 1
            continue
        try:
            pp = float(pp_raw)
        except (TypeError, ValueError):
            skipped_null_pnl += 1
            continue
        if pp == 0:
            skipped_zero_pnl += 1
            continue
        new = "WON" if pp > 0 else "LOST"
        changed.append({
            "id": p.get("id"),
            "asset_class": p.get("asset_class"),
            "exit_reason": p.get("exit_reason"),
            "pnl_pct": pp,
            "old_status": "CLOSED",
            "new_status": new,
        })
        if args.apply:
            p["status"] = new
            p["_relabeled_at"] = datetime.now(timezone.utc).isoformat()
            p["_relabeled_from"] = "CLOSED"

    print(f"Total picks: {len(picks)}")
    print(f"Would relabel: {len(changed)} rows")
    print(f"  -> WON:  {sum(1 for c in changed if c['new_status'] == 'WON')}")
    print(f"  -> LOST: {sum(1 for c in changed if c['new_status'] == 'LOST')}")
    print(f"Skipped (NULL pnl):  {skipped_null_pnl}")
    print(f"Skipped (zero pnl):  {skipped_zero_pnl}")

    out_dir = Path("reports")
    out_dir.mkdir(exist_ok=True)
    diff_name = "2026-05-26_closed_status_relabel_diff" + ("" if args.apply else "_dryrun") + ".json"
    diff_path = out_dir / diff_name
    diff_path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(src),
        "applied": args.apply,
        "total_picks": len(picks),
        "relabeled": len(changed),
        "won_n": sum(1 for c in changed if c['new_status'] == 'WON'),
        "lost_n": sum(1 for c in changed if c['new_status'] == 'LOST'),
        "skipped_null_pnl": skipped_null_pnl,
        "skipped_zero_pnl": skipped_zero_pnl,
        "rows": changed[:500],  # cap to keep file size sane
        "rows_truncated": len(changed) > 500,
    }, indent=2))
    print(f"Diff written: {diff_path}")

    if args.apply:
        bak = src.with_suffix(".json.bak.relabel")
        shutil.copy2(src, bak)
        src.write_text(json.dumps(data, indent=2))
        print(f"Applied. Backup at {bak}")
    else:
        print("Dry-run only. Re-run with --apply to mutate.")


if __name__ == "__main__":
    main()
