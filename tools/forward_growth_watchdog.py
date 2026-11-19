#!/usr/bin/env python3
"""Fail when the forward ledger stops growing — per hypothesis, not just globally.

The failure this catches is silent non-accrual: the writer runs, exits 0, and adds
nothing — exactly what the 2026-11-19 audit found (430 rows, all H-119, one manual
fill). A ledger that does not grow cannot mint a forward verdict.

A global age check is not enough: one fresh H-119 row kept the gate green while the
EQUITY pod had zero rows. So the contract is per hypothesis, plus pod coverage:

  * n_admissible == 0                    -> OK (nothing to accrue)
  * hypothesis with rows, newest > max_age -> FAIL (that writer stalled)
  * hypothesis with rows but no timestamp  -> FAIL
  * pre_registered pod with 0 rows past its grace period -> FAIL (never emitted)
  * pre_registered pod with 0 rows inside grace          -> WARN
  * observe pod with 0 rows                             -> WARN

Reads only JSON/JSONL. No DB, so it runs as a cheap CI step and is unit-testable.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = REPO / "reports" / "forward_observations.jsonl"
DEFAULT_MANIFEST = REPO / "reports" / "audit3_confirmatory.json"


def _parse(ts):
    if not ts:
        return None
    try:
        d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def newest_timestamp(rows: list[dict]):
    stamps = [r.get("created_at") or r.get("opened_at") for r in rows]
    parsed = [p for p in (_parse(s) for s in stamps) if p]
    return max(parsed).isoformat() if parsed else None


def newest_for(rows: list[dict], hypothesis_id: str):
    subset = [r for r in rows
              if str(r.get("hypothesis_id") or "").upper() == str(hypothesis_id).upper()]
    return newest_timestamp(subset)


def assess(n_admissible: int, newest_created_at, now: datetime,
           max_age_days: float = 7.0) -> dict:
    """Global decision (kept for callers/tests that only have one timestamp)."""
    if not n_admissible:
        return {"ok": True, "status": "no_eligible_rows", "n_admissible": 0,
                "age_days": None, "detail": "no admissible cohort rows this run"}
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


def per_hypothesis(rows: list[dict], n_by_hypothesis: dict, now: datetime,
                   max_age_days: float = 7.0) -> list[dict]:
    """One verdict per hypothesis that has admissible rows."""
    out = []
    for hid, n in sorted((n_by_hypothesis or {}).items()):
        if not n:
            continue
        ts = newest_for(rows, hid)
        newest = _parse(ts)
        if newest is None:
            out.append({"hypothesis_id": hid, "n": n, "ok": False,
                        "status": "missing_rows",
                        "detail": f"{hid}: {n} eligible rows but no timestamped ledger row"})
            continue
        age = (now - newest).total_seconds() / 86400.0
        ok = age <= max_age_days
        out.append({"hypothesis_id": hid, "n": n, "ok": ok,
                    "status": "growing" if ok else "stalled",
                    "age_days": round(age, 2),
                    "detail": f"{hid}: newest row {age:.2f}d old "
                              f"(limit {max_age_days}d)"})
    return out


def pod_coverage(manifest: dict, rows: list[dict], now: datetime,
                 grace_days: float = 7.0) -> list[dict]:
    """Pods with zero forward rows: WARN inside grace, FAIL for pre_registered past it."""
    out = []
    for pod in (manifest or {}).get("pods") or []:
        hid = pod.get("hypothesis_id")
        if not hid:
            continue
        count = sum(1 for r in rows
                    if str(r.get("hypothesis_id") or "").upper() == str(hid).upper())
        if count:
            continue
        registered = _parse(pod.get("registered_at"))
        age = (now - registered).total_seconds() / 86400.0 if registered else None
        status = str(pod.get("status") or "").lower()
        past_grace = age is not None and age > grace_days
        fail = status == "pre_registered" and past_grace
        out.append({
            "pod": pod.get("id"), "hypothesis_id": hid, "status": status,
            "n_forward": 0, "registered_at": pod.get("registered_at"),
            "age_days": round(age, 2) if age is not None else None,
            "ok": not fail,
            "severity": "FAIL" if fail else "WARN",
            "detail": (f"{pod.get('id')} has 0 forward rows"
                       + (f" {age:.1f}d after pre-registration (grace {grace_days}d)"
                          if age is not None else "")
                       + (" — the emitter never landed" if fail else " — inside grace/observe")),
        })
    return out


def assess_all(n_admissible: int, rows: list[dict], n_by_hypothesis: dict,
               manifest: dict | None, now: datetime,
               max_age_days: float = 7.0, grace_days: float = 7.0) -> dict:
    global_v = assess(n_admissible, newest_timestamp(rows), now, max_age_days)
    hyps = per_hypothesis(rows, n_by_hypothesis, now, max_age_days)
    pods = pod_coverage(manifest or {}, rows, now, grace_days)
    failed = [h for h in hyps if not h["ok"]] + [p for p in pods if not p["ok"]]
    return {
        "ok": bool(global_v["ok"] and not failed),
        "global": global_v,
        "hypotheses": hyps,
        "pods": pods,
        "n_failed": len(failed),
        "detail": (f"{len(failed)} failure(s)" if failed else global_v["detail"]),
    }


def load_ledger(path: str | Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="forward-ledger growth watchdog")
    ap.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    ap.add_argument("--ingest-report", help="JSON from forward_observations_ingest --json")
    ap.add_argument("--n-admissible", type=int, default=None)
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST),
                    help="confirmatory manifest with pods + registered_at")
    ap.add_argument("--max-age-days", type=float, default=7.0)
    ap.add_argument("--grace-days", type=float, default=7.0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    n_by: dict = {}
    if args.n_admissible is not None:
        n = args.n_admissible
    elif args.ingest_report:
        rep = json.loads(Path(args.ingest_report).read_text())
        n = int(rep.get("n_admissible") or 0)
        n_by = rep.get("n_by_hypothesis") or {}
    else:
        print("ERROR: need --ingest-report or --n-admissible", file=sys.stderr)
        return 2

    rows = load_ledger(args.ledger)
    manifest = {}
    mp = Path(args.manifest)
    if mp.exists():
        try:
            manifest = json.loads(mp.read_text())
        except json.JSONDecodeError:
            manifest = {}
    verdict = assess_all(n, rows, n_by, manifest, datetime.now(timezone.utc),
                         args.max_age_days, args.grace_days)
    verdict["ledger_rows"] = len(rows)
    if args.json:
        print(json.dumps(verdict, indent=1))
    else:
        g = verdict["global"]
        print(f"{g['status']}: {g['detail']} (ledger rows={len(rows)})")
        for h in verdict["hypotheses"]:
            print(f"  {'OK ' if h['ok'] else 'FAIL'} {h['detail']}")
        for p in verdict["pods"]:
            print(f"  {p['severity']:4} {p['detail']}")
    return 0 if verdict["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
