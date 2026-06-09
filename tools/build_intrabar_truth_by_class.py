#!/usr/bin/env python3
"""build_intrabar_truth_by_class.py — emit honest intrabar-true per-class WR/PF.

WHY: the headline money_ready_verdict per-class numbers come from closed_picks.json
(canonical-resolver pnl), which mislabels ~58% of first-touch CRYPTO outcomes and is
outlier-contaminated (the at_pick_outcomes+partial-intrabar join still shows CRYPTO
PF≈172 from one outlier). The CLEAN truth is `at_signal_outcomes.intrabar_*` — the
self-contained, fully first-touch-replayed, bad-geometry-excluded ledger built by the
w0fkolehf swarm (SL-wins-ties). This tool reads ONLY that ledger and writes an ADDITIVE
reference file the dashboard can surface alongside the headline.

READ-ONLY against the DB. Writes a NEW JSON file (not a live-HTML generator). Idempotent.

Usage: python3 tools/build_intrabar_truth_by_class.py [--out PATH] [--stdout]
Tiering (policy-clean): T1 PF>2/WR>55/MDD<10 ; T2 PF>1.5/WR>50 ; T3 PF>1.2/WR>48. n>=100 to qualify.
"""
from __future__ import annotations
import argparse, datetime as dt, json, os, sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import pymysql  # noqa: E402
from tools.db_env import get_stocks_creds  # noqa: E402

OUT_DEFAULT = os.path.join(REPO_ROOT, "audit_dashboard", "data", "intrabar_truth_by_class.json")
_KEEP = ("host", "user", "password", "database", "port", "connect_timeout")


def _verdict(n: int, wr: float, pf: float) -> str:
    if n < 100:
        return "INSUFFICIENT_N"
    if wr >= 55 and pf >= 2.0:
        return "T1_CANDIDATE"
    if wr >= 50 and pf >= 1.5:
        return "T2_CANDIDATE"
    if wr >= 48 and pf >= 1.2:
        return "T3_CANDIDATE"
    return "FAIL"


def build() -> dict:
    creds = {k: v for k, v in get_stocks_creds().items() if k in _KEEP}
    conn = pymysql.connect(**creds, cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()
    # Per-class, intrabar-true (TP_HIT/SL_HIT only — the resolved binary outcomes).
    cur.execute(
        """
        SELECT asset_class AS ac,
               COUNT(*) AS n,
               SUM(intrabar_status = 'TP_HIT') AS wins,
               ROUND(SUM(CASE WHEN intrabar_pnl_pct > 0 THEN intrabar_pnl_pct ELSE 0 END)
                     / NULLIF(SUM(CASE WHEN intrabar_pnl_pct < 0 THEN -intrabar_pnl_pct ELSE 0 END), 0), 3) AS pf,
               ROUND(AVG(intrabar_pnl_pct), 4) AS avg_pnl
        FROM at_signal_outcomes
        WHERE intrabar_resolved_at IS NOT NULL
          AND intrabar_status IN ('TP_HIT', 'SL_HIT')
        GROUP BY asset_class
        ORDER BY n DESC
        """
    )
    classes = {}
    for r in cur.fetchall():
        ac = (r["ac"] or "UNKNOWN").upper().strip() or "UNKNOWN"
        if not ac or ac in ("", "NONE"):
            continue
        n = int(r["n"] or 0)
        wins = int(r["wins"] or 0)
        wr = round(100.0 * wins / n, 1) if n else 0.0
        pf = float(r["pf"]) if r["pf"] is not None else 0.0
        classes[ac] = {
            "n": n, "wr_pct": wr, "pf": pf, "avg_pnl_pct": float(r["avg_pnl"] or 0.0),
            "verdict": _verdict(n, wr, pf),
        }
    # Cleanest single strategy per class (n>=10) — forward-track candidates, NOT sized.
    cur.execute(
        """
        SELECT asset_class AS ac, strategy,
               COUNT(*) AS n, SUM(intrabar_status='TP_HIT') AS wins,
               ROUND(SUM(CASE WHEN intrabar_pnl_pct>0 THEN intrabar_pnl_pct ELSE 0 END)
                     / NULLIF(SUM(CASE WHEN intrabar_pnl_pct<0 THEN -intrabar_pnl_pct ELSE 0 END),0),3) AS pf
        FROM at_signal_outcomes
        WHERE intrabar_resolved_at IS NOT NULL AND intrabar_status IN ('TP_HIT','SL_HIT')
        GROUP BY asset_class, strategy
        HAVING n >= 10
        ORDER BY pf DESC, n DESC
        """
    )
    leads = []
    for r in cur.fetchall():
        n = int(r["n"] or 0)
        wins = int(r["wins"] or 0)
        wr = round(100.0 * wins / n, 1) if n else 0.0
        pf = float(r["pf"]) if r["pf"] is not None else 0.0
        if wr >= 55 and pf >= 1.5:  # T2-shaped strategy leads only
            leads.append({"asset_class": (r["ac"] or "").upper(), "strategy": r["strategy"],
                          "n": n, "wr_pct": wr, "pf": pf})
    conn.close()
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "at_signal_outcomes.intrabar_* (first-touch, SL-wins-ties, bad-geometry-excluded)",
        "note": "HONEST intrabar-true per-class. Use for the /audit reality check. n<100 = INSUFFICIENT_N. Do NOT size on sub-100-n leads.",
        "by_class": classes,
        "t2_shaped_strategy_leads": leads[:12],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()
    payload = build()
    if args.stdout:
        print(json.dumps(payload, indent=2))
    else:
        with open(args.out, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"wrote {args.out}: {len(payload['by_class'])} classes, {len(payload['t2_shaped_strategy_leads'])} T2-shaped leads")
    return 0


if __name__ == "__main__":
    sys.exit(main())
