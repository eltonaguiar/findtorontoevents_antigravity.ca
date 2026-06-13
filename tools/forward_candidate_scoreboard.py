#!/usr/bin/env python3
"""forward_candidate_scoreboard.py — standing CI-LB referee over the honest ledger.

Operationalizes the 2026-06-13 manual analysis (reports/FORWARD_CANDIDATE_SCOREBOARD)
into a reusable generator: for every strategy with enough honest intrabar-resolved
outcomes, compute point PF, cluster-bootstrap PF 95% CI lower bound (symbol-day
clusters), effective-n, and the promotion verdict vs the master-loop bar
(CI-LB > 1.15 AND n_eff >= 80). Point-estimate PF is NEVER the promotion signal —
this tool exists because point PF passed the futures_momentum mirage (PF 1.53 /
CI-LB 0.43) while macd_rsi_confluence (PF 1.09 at n_eff 112) is a real-n no-edge.

Honest source ONLY: at_signal_outcomes intrabar TP/SL (first-touch, SL-wins-ties).
Read-only. Writes audit_dashboard/data/forward_candidate_scoreboard.json.

Usage:
    python3 tools/forward_candidate_scoreboard.py [--min-n 20] [--stdout]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from tools.pf_ci_lower import pf_ci_lower, effective_n  # noqa: E402

OUT = REPO / "audit_dashboard" / "data" / "forward_candidate_scoreboard.json"
MIN_N_DEFAULT = 20
CI_LB_BAR = 1.15
N_EFF_BAR = 80


def verdict(ci_lb, n_eff) -> str:
    if ci_lb is None:
        return "uncomputable"
    if ci_lb > CI_LB_BAR and n_eff >= N_EFF_BAR:
        return "SIZABLE"            # clears the promotion bar
    if ci_lb > 1.0:
        return "real-edge(sub-bar)"  # genuine positive edge, not yet promotable
    return "no-edge/mirage"          # point PF may look good; CI-LB says no


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-n", type=int, default=MIN_N_DEFAULT)
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()

    from tools.db_env import get_stocks_creds
    import pymysql
    keep = ("host", "user", "password", "database", "port", "connect_timeout")
    conn = pymysql.connect(**{k: v for k, v in get_stocks_creds().items() if k in keep})
    cur = conn.cursor()
    # candidate strategies with >= min-n honest intrabar TP/SL outcomes, split by direction
    cur.execute(
        "SELECT strategy, UPPER(COALESCE(direction,'')) , COUNT(*) FROM at_signal_outcomes "
        "WHERE intrabar_status IN ('TP_HIT','SL_HIT') AND strategy IS NOT NULL "
        "GROUP BY strategy, UPPER(COALESCE(direction,'')) HAVING COUNT(*) >= %s",
        (args.min_n,))
    keys = [(r[0], r[1]) for r in cur.fetchall()]

    board = []
    for strat, dirn in keys:
        q = ("SELECT symbol, opened_at, intrabar_pnl_pct FROM at_signal_outcomes "
             "WHERE strategy=%s AND UPPER(COALESCE(direction,''))=%s "
             "AND intrabar_status IN ('TP_HIT','SL_HIT') AND intrabar_pnl_pct IS NOT NULL "
             "ORDER BY opened_at")
        cur.execute(q, (strat, dirn))
        rows = cur.fetchall()
        if len(rows) < args.min_n:
            continue
        pnls = [float(r[2]) for r in rows]
        clusters = [f"{r[0]}|{str(r[1])[:10]}" for r in rows]
        ci = pf_ci_lower(pnls, clusters=clusters)
        neff = effective_n(pnls, clusters)
        wins = sum(1 for p in pnls if p > 0)
        pf = ci["pf"]
        board.append({
            "strategy": strat, "direction": dirn or "(any)", "n": len(pnls),
            "wr_pct": round(100 * wins / len(pnls), 1),
            "pf_point": (round(pf, 3) if pf not in (None, float("inf")) else pf),
            "pf_ci_lower": ci["pf_ci_lower"], "n_eff": neff["n_eff"],
            "rho": neff["rho"],
            "verdict": verdict(ci["pf_ci_lower"], neff["n_eff"]),
        })
    conn.close()

    # rank by CI-LB desc (None last)
    board.sort(key=lambda r: (r["pf_ci_lower"] is not None, r["pf_ci_lower"] or -9),
               reverse=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "at_signal_outcomes intrabar TP/SL (first-touch, SL-wins-ties)",
        "promotion_bar": f"CI-LB > {CI_LB_BAR} AND n_eff >= {N_EFF_BAR}",
        "rule": "point-estimate PF is NOT a promotion signal; only the CI lower bound is",
        "n_candidates": len(board),
        "sizable": [b["strategy"] + "/" + b["direction"] for b in board if b["verdict"] == "SIZABLE"],
        "real_sub_bar": [b["strategy"] + "/" + b["direction"] for b in board if b["verdict"] == "real-edge(sub-bar)"],
        "candidates": board,
    }
    if args.stdout:
        print(json.dumps(payload, indent=2, default=str))
    else:
        OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n")
        top = board[:8]
        print(f"# wrote {OUT.relative_to(REPO)} ({len(board)} candidates)")
        print(f"{'candidate':40s} {'n':>4} {'wr%':>5} {'pf':>6} {'CI-LB':>6} {'n_eff':>6}  verdict")
        for b in top:
            print(f"{b['strategy'][:32]+'/'+b['direction']:40s} {b['n']:>4} {b['wr_pct']:>5} "
                  f"{str(b['pf_point']):>6} {str(b['pf_ci_lower']):>6} {str(b['n_eff']):>6}  {b['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
