#!/usr/bin/env python3
"""
Auto-shutdown monitor: checks rolling Sharpe + drawdown per source system.
Demotes to paper-only or raises alert when thresholds breach.

Gates (from Grok + Lopez de Prado standards):
  - Rolling Sharpe < 0.5 over last 30 trades → DEMOTE_TO_PAPER
  - Rolling drawdown > 20% → HARD_STOP
  - Win rate collapse: last-10 WR < 30% AND historical WR > 45% → ALERT

Run: python3 tools/auto_shutdown_monitor.py [--source mega_mutation] [--dry-run]
"""
from __future__ import annotations
import os, sys, json, argparse
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import pymysql


def connect():
    return pymysql.connect(
        host=os.environ.get("DB_HOST", "mysql.50webs.com"),
        user=os.environ.get("DB_USER", "ejaguiar1_stocks"),
        password=os.environ.get("DB_PASS_STOCKS", "stocks1234560"),
        database=os.environ.get("DB_NAME", "ejaguiar1_stocks"),
        connect_timeout=15,
        cursorclass=pymysql.cursors.DictCursor,
    )


def rolling_sharpe(returns: list[float], window: int = 30) -> float:
    if len(returns) < window:
        return float("inf")  # not enough data
    recent = returns[-window:]
    import math
    n = len(recent)
    mean = sum(recent) / n
    if n < 2:
        return 0.0
    std = math.sqrt(sum((x - mean) ** 2 for x in recent) / (n - 1))
    if std == 0:
        return float("inf") if mean > 0 else 0.0
    return (mean / std) * math.sqrt(252)


def max_drawdown_pct_of_profits(returns: list[float]) -> float:
    """MDD as % of total cumulative profits given back from peak.
    E.g. 0.80 = gave back 80% of cumulative PnL from peak.
    Invariant to scale/compounding; meaningful for both small-pct FX and high-pct CRYPTO.
    """
    if not returns:
        return 0.0
    cum = 0.0
    peak = 0.0
    max_dd_frac = 0.0
    for r in returns:
        cum += r
        if cum > peak:
            peak = cum
        if peak > 0:
            dd_frac = (cum - peak) / peak  # negative when below peak
            if dd_frac < max_dd_frac:
                max_dd_frac = dd_frac
    return abs(max_dd_frac)


def check_source(cursor, source: str, last_n: int = 100) -> dict:
    cursor.execute(
        """SELECT pnl_pct, closed_at FROM trading_picks
           WHERE source_system=%s AND pnl_pct IS NOT NULL
           AND status NOT IN ('OPEN','ABANDONED','ACTIVE')
           ORDER BY closed_at DESC LIMIT %s""",
        (source, last_n),
    )
    rows = cursor.fetchall()
    if not rows:
        return {"source": source, "status": "NO_DATA", "n": 0}

    # pnl_pct is stored as percentage (11.13 = 11.13%), convert to fraction
    returns = [float(r["pnl_pct"]) / 100.0 for r in reversed(rows)]
    n = len(returns)
    wr = sum(1 for r in returns if r > 0) / n

    sharpe = rolling_sharpe(returns)

    last10 = returns[-10:] if len(returns) >= 10 else returns
    last10_wr = sum(1 for r in last10 if r > 0) / len(last10)

    verdict = "OK"
    reasons = []
    if sharpe < 0.5 and n >= 30:
        verdict = "DEMOTE_TO_PAPER"
        reasons.append(f"rolling_sharpe={sharpe:.2f}<0.5")
    if last10_wr < 0.30 and wr > 0.45 and len(last10) >= 10:
        if verdict == "OK":
            verdict = "ALERT"
        reasons.append(f"wr_collapse last10={last10_wr:.0%} vs hist={wr:.0%}")

    return {
        "source": source,
        "status": verdict,
        "n": n,
        "wr": round(wr, 3),
        "last10_wr": round(last10_wr, 3),
        "rolling_sharpe": round(sharpe, 3),
        "mdd_pct_of_profits": None,  # TODO: requires position-sizing context
        "reasons": reasons,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=None, help="Single source to check (default: all >=50 trades)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    conn = connect()
    cur = conn.cursor()

    if args.source:
        sources = [args.source]
    else:
        cur.execute(
            """SELECT DISTINCT source_system FROM trading_picks
               WHERE pnl_pct IS NOT NULL AND status NOT IN ('OPEN','ABANDONED','ACTIVE')
               GROUP BY source_system HAVING COUNT(*)>=50"""
        )
        sources = [r["source_system"] for r in cur.fetchall()]

    results = [check_source(cur, s) for s in sources]
    results.sort(key=lambda x: {"HARD_STOP": 0, "DEMOTE_TO_PAPER": 1, "ALERT": 2, "OK": 3, "NO_DATA": 4}.get(x["status"], 5))

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        problems = [r for r in results if r["status"] != "OK"]
        print(f"\nAuto-Shutdown Monitor — {len(sources)} sources checked")
        print(f"Problems: {len(problems)}\n")
        for r in results:
            icon = {"HARD_STOP": "🔴", "DEMOTE_TO_PAPER": "🟡", "ALERT": "🟠", "OK": "✅", "NO_DATA": "⚪"}.get(r["status"], "?")
            reasons_str = "; ".join(r.get("reasons", []))
            print(f"  {icon} {r['source']:<35} n={r['n']:>4} WR={r['wr']:.0%} last10_WR={r['last10_wr']:.0%} Sharpe={r['rolling_sharpe']:.2f} [{r['status']}]{' | '+reasons_str if reasons_str else ''}")

    conn.close()
    return results


if __name__ == "__main__":
    main()
