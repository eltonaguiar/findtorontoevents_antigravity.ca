#!/usr/bin/env python3
"""Reject pod manifests that list strategies no system emits.

Why: on 2026-11-20, 15 of 23 registered pod strategies had zero rows in both
`trading_picks` and `at_signal_outcomes` — including all four of
POD-EQUITY-BREAKOUT. The forward clock could never accrue, and every "0 forward
rows" investigation was chasing an emitter that never existed. A five-line audit
would have caught it on day one.

Contract:
  * a strategy is EMITTED if it has >=1 row in trading_picks or at_signal_outcomes;
  * a manifest entry may opt out with `status: unemitted_approved` (research only);
  * `--strict` exits 1 if any strategy is phantom without that opt-out.

Dry-run by default; reads the DB only for counts (no writes).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:          # direct-script invocation: make `tools.*` importable
    sys.path.insert(0, str(REPO))
DEFAULT_MANIFEST = REPO / "reports" / "audit3_confirmatory.json"
DEFAULT_OUT = REPO / "reports" / "pod_emission_audit.json"


def audit(manifest: dict, counts: dict[str, dict]) -> dict:
    """Pure: manifest + {strategy: {picks, intrabar}} -> per-strategy verdicts."""
    rows, phantom = [], []
    for pod in (manifest or {}).get("pods") or []:
        approved = str(pod.get("status") or "").lower() == "unemitted_approved"
        for strat in pod.get("strategies") or []:
            c = counts.get(strat) or {}
            picks = int(c.get("picks") or 0)
            intr = int(c.get("intrabar") or 0)
            emitted = (picks + intr) > 0
            ok = emitted or approved
            row = {"pod": pod.get("id"), "strategy": strat,
                   "picks": picks, "intrabar": intr,
                   "emitted": emitted, "approved_unemitted": approved, "ok": ok}
            rows.append(row)
            if not ok:
                phantom.append(row)
    return {"ok": not phantom, "n_strategies": len(rows),
            "n_phantom": len(phantom), "strategies": rows, "phantom": phantom}


def counts_from_db(strategies: list[str]) -> dict[str, dict]:
    import pymysql
    from tools.db_env import get_stocks_creds
    keep = ("host", "user", "password", "database", "port", "connect_timeout")
    conn = pymysql.connect(cursorclass=pymysql.cursors.DictCursor,
                           **{k: v for k, v in get_stocks_creds().items() if k in keep})
    cur = conn.cursor()
    out = {}
    try:
        for s in strategies:
            cur.execute("SELECT COUNT(*) n FROM trading_picks WHERE strategy=%s", (s,))
            p = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) n FROM at_signal_outcomes WHERE strategy=%s", (s,))
            i = cur.fetchone()["n"]
            out[s] = {"picks": int(p), "intrabar": int(i)}
    finally:
        conn.close()
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="pod manifest emission audit")
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    ap.add_argument("--counts-json", help="offline {strategy: {picks,intrabar}} override")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--strict", action="store_true", help="exit 1 on phantom strategies")
    args = ap.parse_args(argv)

    man = json.loads(Path(args.manifest).read_text())
    strategies = sorted({s for p in man.get("pods") or [] for s in (p.get("strategies") or [])})
    if args.counts_json:
        counts = json.loads(Path(args.counts_json).read_text())
    else:
        counts = counts_from_db(strategies)

    rep = audit(man, counts)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"pod emission audit: {rep['n_strategies']} strategies, "
          f"{rep['n_phantom']} phantom")
    for r in rep["phantom"]:
        print(f"  PHANTOM {r['pod']}: {r['strategy']} (0 picks, 0 intrabar)")
    return 0 if (rep["ok"] or not args.strict) else 1


if __name__ == "__main__":
    sys.exit(main())
