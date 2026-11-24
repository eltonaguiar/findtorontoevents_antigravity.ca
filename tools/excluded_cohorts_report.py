"""Measure the excluded-cohort bias (N6) from a dashboard payload.

The dashboard export drops the rows it excludes from metrics, but it keeps
either the rows (`picks.recent_closed` with `_auto_expired` markers) or aggregate
counts (`resolved_closed_picks_net.counts`). This tool reports what it can and
says plainly when it cannot:

* rows present  -> retained vs excluded mean PnL, the gap, and a per-reason table;
* counts only   -> input/kept/excluded plus the per-reason breakdown, and an
                   explicit note that per-row PnL is not exported.

Usage:
    python3 tools/excluded_cohorts_report.py --payload dashboard_data.json
    python3 tools/excluded_cohorts_report.py --payload dashboard_data.json --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from audit_trail.excluded_cohorts import (  # noqa: E402
    bias_report, split_auto_expired)


def _closed_rows(payload: dict) -> list[dict]:
    picks = payload.get("picks") if isinstance(payload, dict) else None
    if isinstance(picks, dict):
        rows = picks.get("recent_closed") or picks.get("closed") or []
        if rows:
            return [r for r in rows if isinstance(r, dict)]
    for key in ("resolved_closed_picks_net", "closed_picks", "recent_closed"):
        block = payload.get(key)
        if isinstance(block, dict) and isinstance(block.get("rows"), list):
            return [r for r in block["rows"] if isinstance(r, dict)]
        if isinstance(block, list):
            return [r for r in block if isinstance(r, dict)]
    return []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--payload", required=True)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--coverage", action="store_true",
                    help="print the payload's coverage.excluded_summary block")
    args = ap.parse_args(argv)

    payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))

    if args.coverage:
        block = (payload.get("coverage") or {}).get("excluded_summary")
        if not isinstance(block, dict):
            print("payload has no coverage.excluded_summary "
                  "(generator not wired for this artifact)", file=sys.stderr)
            return 3
        print(f"scope  {block.get('scope')}")
        print(f"total  {block.get('total')}")
        print(f"n_with_pnl  {block.get('n_with_pnl')}")
        for _k, _v in (block.get("by_reason") or {}).items():
            print(f"  {_k:<20}{_v.get('n'):>7}")
        return 0
    rows = _closed_rows(payload)
    if not rows:
        # The export drops excluded rows, so only aggregate counts survive.
        counts = ((payload.get("resolved_closed_picks_net") or {}).get("counts")
                  or payload.get("counts") or {})
        if isinstance(counts, dict) and counts.get("excluded_by_reason"):
            out = {
                "measurement": "counts_only",
                "input_rows": counts.get("input_rows"),
                "kept_rows": counts.get("kept_rows"),
                "excluded_rows": counts.get("excluded_rows"),
                "excluded_by_reason": counts.get("excluded_by_reason"),
                "pnl_available": False,
                "note": ("Excluded rows are dropped before export, so their PnL "
                         "cannot be measured from this artifact. Wire "
                         "excluded_cohorts.summarize_excluded() into "
                         "dashboard_generator at the auto-expired split to make "
                         "the bias numeric."),
            }
            if args.json:
                print(json.dumps(out, indent=1))
            else:
                print("counts-only (no per-row PnL exported)")
                print(f"input {out['input_rows']} / kept {out['kept_rows']} / "
                      f"excluded {out['excluded_rows']}")
                for k, v in out["excluded_by_reason"].items():
                    print(f"  {k:<26}{v:>7}")
                print()
                print(out["note"])
            return 0
        print("no closed rows found in payload", file=sys.stderr)
        return 2

    real, auto = split_auto_expired(rows)
    excluded = [dict(r, exclude_reason="auto_expired") for r in auto]
    included = [r for r in real if r.get("pnl_pct") is not None]

    report = bias_report(included, excluded)
    report["payload_rows"] = len(rows)
    report["retained_rows"] = len(included)
    report["excluded_rows"] = len(excluded)
    report["excluded_pnl_share_pct"] = (
        round(100.0 * report["excluded"]["n_with_pnl"] / len(rows), 2)
        if rows else None)

    if args.json:
        print(json.dumps(report, indent=1))
        return 0

    inc = report["included"]
    exc = report["excluded"]
    print(f"payload closed rows      : {len(rows)}")
    print(f"retained (with pnl)      : {len(included)}")
    print(f"excluded (auto-expired)  : {len(excluded)}")
    print(f"retained mean pnl        : {inc['mean_pnl_pct']}%  (n={inc['n_with_pnl']})")
    print(f"excluded mean pnl        : {exc['mean_pnl_pct']}%  (n={exc['n_with_pnl']})")
    print(f"retained - excluded (pp) : {report['retained_minus_excluded_pp']}")
    print()
    print(f"{'reason':<28}{'n':>6}{'wr':>8}{'mean%':>9}{'long':>6}{'short':>6}")
    for reason, b in (exc.get("by_reason") or {}).items():
        wr = b.get("win_rate")
        mean = b.get("mean_pnl_pct")
        print(f"{reason:<28}{b['n']:>6}"
              f"{(f'{wr:.1%}' if wr is not None else '-'):>8}"
              f"{(f'{mean:.3f}' if mean is not None else '-'):>9}"
              f"{b['long']:>6}{b['short']:>6}")
    print()
    print(report["note"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
