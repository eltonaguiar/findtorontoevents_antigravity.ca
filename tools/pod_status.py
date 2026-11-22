"""Pod status report + journal — programme items G43 and G44.

Deliberately does NOT emit signals or invent forward observations. It reads every pod spec
under reports/pods/, evaluates each one's own gate against whatever rows actually exist in
its journal, and appends ONE status row per pod per day. A pod with zero forward rows reports
`n=0 GATED`, which is the honest state and the one most of this programme is in.

Why a journal file rather than a database: the gate state is the deliverable, it must be
diffable, and a JSONL append cannot silently rewrite history the way a table update can.

Usage
  python3 tools/pod_status.py               # print the table, append today's rows
  python3 tools/pod_status.py --dry-run     # print only
  python3 tools/pod_status.py --json        # machine-readable report
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POD_DIR = ROOT / "reports" / "pods"
JOURNAL = POD_DIR / "pod_journal.jsonl"
FWD_DIR = POD_DIR / "forward"


def load_specs() -> list[dict]:
    if not POD_DIR.exists():
        return []
    out = []
    for p in sorted(POD_DIR.glob("pod_*.json")):
        try:
            out.append(json.loads(p.read_text()))
        except json.JSONDecodeError as e:
            out.append({"pod_id": p.stem, "status": "SPEC_UNREADABLE", "error": str(e)})
    return out


def _ingest(path: Path, rows: dict[str, list[dict]]) -> None:
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        rows.setdefault(r.get("pod_id", "?"), []).append(r)


def load_rows() -> dict[str, list[dict]]:
    """Forward observations PLUS gate-state rows.

    The journal on its own only ever records gate STATE, so reading it alone pins
    `n_days` at 0 forever -- a pod could run daily and never become eligible. The
    actual forward sessions are written by `pod_forward.py` under forward/, and
    they are what the gate must count. (Found on the first real run: 15 sessions
    on disk, status still reading 0/20.)
    """
    rows: dict[str, list[dict]] = {}
    if FWD_DIR.exists():
        for p in sorted(FWD_DIR.glob("*.jsonl")):
            _ingest(p, rows)
    if JOURNAL.exists():
        _ingest(JOURNAL, rows)
    return rows


def evaluate(spec: dict, rows: list[dict]) -> dict:
    """Gate the pod on ITS OWN declared thresholds, never on a global one."""
    pid = spec.get("pod_id", "?")
    status = spec.get("status", "unknown")
    gate = spec.get("size_gate", {}) or {}
    min_days = gate.get("no_verdict_before_n_days")
    min_trades = gate.get("no_verdict_before_n_trades", gate.get("no_verdict_before_n_trades"))
    n_days = max((r.get("n_days", 0) for r in rows), default=0)
    n_trades = max((r.get("n_trades", 0) for r in rows), default=0)

    blockers = []
    if status != "pre_registered":
        blockers.append(f"status={status} (tribunal bars anything else)")
    if min_days and n_days < min_days:
        blockers.append(f"n_days {n_days}/{min_days}")
    if min_trades and n_trades < min_trades:
        blockers.append(f"n_trades {n_trades}/{min_trades}")
    eligible = not blockers
    return {"pod_id": pid, "status": status, "n_days": n_days, "n_trades": n_trades,
            "eligible_for_verdict": eligible,
            "blocked_by": blockers or ["none"],
            "verdict": "PENDING" if eligible else "GATED"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    specs = load_specs()
    rows = load_rows()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report = [evaluate(s, rows.get(s.get("pod_id", "?"), [])) for s in specs]

    if not a.dry_run:
        POD_DIR.mkdir(parents=True, exist_ok=True)
        with JOURNAL.open("a") as fh:
            for r in report:
                fh.write(json.dumps({"ts": today, **r}) + "\n")

    if a.json:
        print(json.dumps({"generated": today, "pods": report}, indent=2))
        return

    print(f"pod status @ {today}   ({len(report)} pods, journal {JOURNAL.name})")
    print(f"{'pod':40s} {'status':15s} {'n_days':>7s} {'n_trades':>9s} {'verdict':8s} blocked_by")
    for r in report:
        print(f"{r['pod_id']:40s} {r['status']:15s} {r['n_days']:7d} {r['n_trades']:9d} "
              f"{r['verdict']:8s} {', '.join(r['blocked_by'])}")
    n_elig = sum(1 for r in report if r["eligible_for_verdict"])
    print(f"\n{n_elig}/{len(report)} pods eligible for a verdict. "
          f"{len(report) - n_elig} correctly gated — that is the gate working, not a failure.")


if __name__ == "__main__":
    main()
