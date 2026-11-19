#!/usr/bin/env python3
"""Fail when the forward ledger stops growing while eligible rows exist.

The failure this catches is silent non-accrual: the writer runs, exits 0, and adds
nothing — exactly what the 2026-11-19 audit found (430 rows, all H-119, one manual
fill). A ledger that does not grow cannot mint a forward verdict.

Contract:
  * n_admissible == 0            -> nothing to accrue; OK (no eligible rows).
  * ledger empty                 -> FAIL (eligible rows exist, nothing written).
  * newest row older than max_age-> FAIL (writer stalled).
  * otherwise                    -> OK.

Reads only JSON/JSONL. No DB, so it can run as a cheap CI step and be unit-tested.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = REPO / "reports" / "forward_observations.jsonl"


def _parse(ts):
    if not ts:
        return None
    try:
        d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def assess(n_admissible: int, newest_created_at, now: datetime,
           max_age_days: float = 7.0) -> dict:
    """Pure decision function: (eligible rows, newest row, now) -> verdict."""
    if not n_admissible:
        return {"ok": True, "status": "no_eligible_rows",
                "n_admissible": 0, "age_days": None,
                "detail": "no admissible cohort rows this run"}
    newest = _parse(newest_created_at)
    if newest is None:
        return {"ok": False, "status": "ledger_empty", "n_admissible": n_admissible,
                "age_days": None,
                "detail": "eligible rows exist but the ledger has no timestamped row"}
    age = (now - newest).total_seconds() / 86400.0
    ok = age <= max_age_days
    return {
        "ok": ok,
        "status": "growing" if ok else "stalled",
        "n_admissible": n_admissible,
        "newest_created_at": newest.isoformat(),
        "age_days": round(age, 2),
        "max_age_days": max_age_days,
        "detail": (f"newest forward row is {age:.2f}d old (limit {max_age_days}d)"
                   if ok else
                   f"STALLED: newest forward row is {age:.2f}d old "
                   f"(limit {max_age_days}d) while {n_admissible} rows were eligible"),
    }


def newest_timestamp(rows: list[dict]):
    stamps = [r.get("created_at") or r.get("opened_at") for r in rows]
    parsed = [p for p in (_parse(s) for s in stamps) if p]
    return max(parsed).isoformat() if parsed else None


def load_ledger(path: str | Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="forward-ledger growth watchdog")
    ap.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    ap.add_argument("--ingest-report", help="JSON from forward_observations_ingest --json")
    ap.add_argument("--n-admissible", type=int, default=None,
                    help="override when no ingest report is available")
    ap.add_argument("--max-age-days", type=float, default=7.0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.n_admissible is not None:
        n = args.n_admissible
    elif args.ingest_report:
        rep = json.loads(Path(args.ingest_report).read_text())
        n = int(rep.get("n_admissible") or 0)
    else:
        print("ERROR: need --ingest-report or --n-admissible", file=sys.stderr)
        return 2

    rows = load_ledger(args.ledger)
    verdict = assess(n, newest_timestamp(rows), datetime.now(timezone.utc),
                     args.max_age_days)
    verdict["ledger_rows"] = len(rows)
    if args.json:
        print(json.dumps(verdict, indent=1))
    else:
        print(f"{verdict['status']}: {verdict['detail']} (ledger rows={len(rows)})")
    return 0 if verdict["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
