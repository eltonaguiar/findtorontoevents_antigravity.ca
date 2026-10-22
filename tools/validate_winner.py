"""Validate a candidate winning strategy via bootstrap expectancy CI.

Usage:
    python tools/validate_winner.py --strategy high_trust_momentum --source AlphaEngine

Reads resolved (WON/LOST) outcomes from at_raw_picks, computes bootstrap
95% CI for expectancy and win rate, and writes a certificate JSON to
audit_dashboard/data/winner_certificate_<strategy>.json.
"""
import argparse
import json
import os
import random
import statistics
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pymysql

DB_HOST = os.getenv("AUDIT_DB_HOST", "mysql.50webs.com")
DB_PORT = int(os.getenv("AUDIT_DB_PORT", "3306"))
DB_USER = os.getenv("AUDIT_DB_USER", "ejaguiar1_stocks")
DB_PASS = os.getenv("AUDIT_DB_PASS", "stocks1234560")
DB_NAME = os.getenv("AUDIT_DB_NAME", "ejaguiar1_stocks")


def fetch(strategy, source):
    conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS,
                           database=DB_NAME, connect_timeout=15)
    cur = conn.cursor()
    cur.execute(
        "SELECT pnl_pct FROM at_raw_picks "
        "WHERE source_system=%s AND strategy=%s AND status IN ('WON','LOST')",
        (source, strategy),
    )
    pnls = [float(r[0]) for r in cur.fetchall()]
    conn.close()
    return pnls


def bootstrap(pnls, n_iter=10000, seed=42):
    random.seed(seed)
    exps, wrs = [], []
    for _ in range(n_iter):
        sample = [random.choice(pnls) for _ in range(len(pnls))]
        w = sum(1 for p in sample if p > 0) / len(sample)
        aw = statistics.mean([p for p in sample if p > 0]) if any(p > 0 for p in sample) else 0.0
        al = statistics.mean([p for p in sample if p <= 0]) if any(p <= 0 for p in sample) else 0.0
        exps.append(w * aw + (1 - w) * al)
        wrs.append(w)
    exps.sort()
    wrs.sort()
    lo, hi = int(0.025 * n_iter), int(0.975 * n_iter)
    return {
        "expectancy_mean": statistics.mean(exps),
        "expectancy_ci95": [exps[lo], exps[hi]],
        "wr_mean": statistics.mean(wrs),
        "wr_ci95": [wrs[lo], wrs[hi]],
        "p_expectancy_positive": sum(1 for e in exps if e > 0) / n_iter,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", required=True)
    ap.add_argument("--source", default="AlphaEngine")
    args = ap.parse_args()

    pnls = fetch(args.strategy, args.source)
    if len(pnls) < 30:
        print("INSUFFICIENT_DATA", len(pnls))
        sys.exit(1)

    b = bootstrap(pnls)
    w = sum(1 for p in pnls if p > 0) / len(pnls)
    pf = sum(p for p in pnls if p > 0) / abs(sum(p for p in pnls if p < 0))
    cert = {
        "strategy": args.strategy,
        "source_system": args.source,
        "n_hard_resolved": len(pnls),
        "win_rate": w,
        "profit_factor": pf,
        "avg_return_pct": statistics.mean(pnls),
        "bootstrap": b,
        "verdict": "PROVEN" if (b["expectancy_ci95"][0] > 0 and b["p_expectancy_positive"] > 0.95) else "NOT_PROVEN",
        "validated_at": datetime.utcnow().isoformat() + "Z",
        "agent": "OPENCODE_BEAM",
    }
    out = os.path.join("audit_dashboard", "data", f"winner_certificate_{args.strategy}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(cert, f, indent=2)
    print(json.dumps(cert, indent=2))


if __name__ == "__main__":
    main()
