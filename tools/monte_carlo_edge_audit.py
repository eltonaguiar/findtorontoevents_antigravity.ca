#!/usr/bin/env python3
"""
Monte Carlo Edge Audit — Bootstrap significance testing for trading strategies.

Queries ejaguiar1_stocks.trading_picks for ALL closed trades, groups by
(category, strategy, direction), and runs 10,000 bootstrap resamples on each
group's PnL series to compute a Profit Factor 95% confidence interval lower
bound.  Classifies each combo into a tier:

  TIER-1      PF_CI_low >= 1.50  — institutional-grade edge
  TIER-2      PF_CI_low >= 1.50, n<30  — promising but small sample
  EDGE        PF_CI_low >= 1.00  — statistically profitable
  PROFITABLE  PF > 1.00  but  PF_CI_low < 1.00  — not yet significant
  DESTROYER   PF < 1.00  — money-losing

Also runs a per-asset-class aggregate summary (policy-clean).

Usage:
  python tools/monte_carlo_edge_audit.py                # full audit
  python tools/monte_carlo_edge_audit.py --category crypto  # single class
  python tools/monte_carlo_edge_audit.py --min-n 30     # stricter threshold
  python tools/monte_carlo_edge_audit.py --json         # JSON output
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Database connection ──────────────────────────────────────────────────────

try:
    from tools.db_env import get_stocks_creds
    _USE_DB_ENV = True
except ImportError:
    _USE_DB_ENV = False


def _connect():
    """Connect to ejaguiar1_stocks using db_env or environment fallback."""
    try:
        import mysql.connector
    except ImportError:
        raise RuntimeError("mysql-connector-python not installed — run: pip install mysql-connector-python")

    if _USE_DB_ENV:
        creds = get_stocks_creds()
        conn_kwargs: Dict[str, Any] = {}
        for k in ("host", "user", "password", "database", "port"):
            if k in creds:
                conn_kwargs[k] = creds[k]
        conn_kwargs.setdefault("connect_timeout", 30)
        return mysql.connector.connect(**conn_kwargs)

    # Fallback
    password = (
        os.environ.get("DB_PASS_STOCKS")
        or os.environ.get("MYSQL_PASSWORD")
        or os.environ.get("DB_STOCKS_PASSWORD")
    )
    if not password:
        raise RuntimeError("No DB password — set DB_PASS_STOCKS or MYSQL_PASSWORD")
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST_STOCKS", "mysql.50webs.com"),
        user=os.environ.get("DB_USER_STOCKS", "ejaguiar1_stocks"),
        password=password,
        database=os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks"),
        port=int(os.environ.get("DB_PORT_STOCKS", "3306")),
        connect_timeout=30,
    )


# ── Bootstrap functions ──────────────────────────────────────────────────────

N_BOOTSTRAP = 10_000
RANDOM_SEED = 42
CI_ALPHA = 0.05  # 95% CI


def profit_factor(pnls: np.ndarray) -> float:
    """Profit factor: sum of positive PnLs / abs(sum of negative PnLs)."""
    pos = pnls[pnls > 0].sum()
    neg = abs(pnls[pnls < 0].sum())
    if neg == 0:
        return float("inf") if pos > 0 else 0.0
    return float(pos / neg)


def bootstrap_pf_ci(pnls: np.ndarray, n_iter: int = N_BOOTSTRAP) -> Dict[str, float]:
    """Bootstrap Profit Factor 95% confidence interval.

    Resamples with replacement and computes PF for each resample.
    Returns {pf_low, pf_high, pf_median, pf_mean}.
    """
    rng = np.random.RandomState(RANDOM_SEED)
    n = len(pnls)
    pf_samples = np.empty(n_iter)

    for i in range(n_iter):
        sample = pnls[rng.randint(0, n, size=n)]
        pf_samples[i] = profit_factor(sample)

    return {
        "pf_low": float(np.percentile(pf_samples, 100 * CI_ALPHA / 2)),
        "pf_high": float(np.percentile(pf_samples, 100 * (1 - CI_ALPHA / 2))),
        "pf_median": float(np.median(pf_samples)),
        "pf_mean": float(np.mean(pf_samples)),
    }


def classify(pf: float, pf_ci_low: float, n: int) -> str:
    """Classify a strategy+direction combo into a tier."""
    if pf < 1.0:
        return "DESTROYER"
    if pf_ci_low >= 1.5:
        return "TIER-1" if n >= 30 else "TIER-2"
    if pf_ci_low >= 1.0:
        return "EDGE"
    return "PROFITABLE"


# ── Queries ──────────────────────────────────────────────────────────────────

def fetch_all_trades(conn) -> List[Dict[str, Any]]:
    """Fetch ALL closed trades with PnL data from trading_picks."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT category, strategy, direction, pnl_pct, status, symbol
        FROM trading_picks
        WHERE status IN ('WON', 'LOST', 'SL_HIT', 'TP_HIT', 'EXPIRED', 'TIME_EXIT')
          AND pnl_pct IS NOT NULL
          AND strategy IS NOT NULL
          AND category IS NOT NULL
        ORDER BY category, strategy, direction
    """)
    rows = cursor.fetchall()
    cursor.close()
    return rows


def fetch_per_class_aggregate(conn) -> List[Dict[str, Any]]:
    """Per-asset-class aggregate stats (policy-clean: excluding known bad strats)."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            COALESCE(category, 'UNKNOWN') AS category,
            COUNT(*) AS n,
            ROUND(100.0 * SUM(CASE WHEN status IN ('WON','TP_HIT') THEN 1 ELSE 0 END)
                  / NULLIF(COUNT(*), 0), 1) AS wr,
            ROUND(SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END)
                  / NULLIF(ABS(SUM(CASE WHEN pnl_pct < 0 THEN pnl_pct ELSE 0 END)), 0), 3) AS pf,
            ROUND(SUM(pnl_pct), 1) AS total_pnl_pct,
            ROUND(AVG(pnl_pct), 3) AS avg_pnl,
            ROUND(STDDEV(pnl_pct), 3) AS std_pnl,
            COUNT(DISTINCT strategy) AS unique_strategies,
            COUNT(DISTINCT symbol) AS unique_symbols
        FROM trading_picks
        WHERE status IN ('WON', 'LOST', 'SL_HIT', 'TP_HIT', 'EXPIRED', 'TIME_EXIT')
          AND pnl_pct IS NOT NULL
          AND category IS NOT NULL
        GROUP BY category
        ORDER BY pf DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    return rows


# ── Main audit ───────────────────────────────────────────────────────────────

def run_audit(
    conn,
    min_n: int = 20,
    category_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the full Monte Carlo edge audit.

    Args:
        conn: MySQL connection
        min_n: minimum trade count for a combo to be evaluated
        category_filter: optional single category to filter to

    Returns:
        Full audit dict with per-class summary, per-combo results, and overall tiers.
    """
    rows = fetch_all_trades(conn)

    # ── Group by (category, strategy, direction) ─────────────────────────
    groups: Dict[Tuple[str, str, str], List[float]] = defaultdict(list)
    for row in rows:
        cat = row["category"]
        if category_filter and cat != category_filter:
            continue
        strat = row["strategy"] or "NULL"
        direction = row["direction"] or "BOTH"
        groups[(cat, strat, direction)].append(float(row["pnl_pct"]))

    # ── Bootstrap each group ─────────────────────────────────────────────
    results: List[Dict[str, Any]] = []
    for (cat, strat, direction), pnls in sorted(groups.items()):
        n = len(pnls)
        if n < min_n:
            continue

        pnls_arr = np.array(pnls, dtype=float)
        pf = profit_factor(pnls_arr)
        wr = float(np.mean(pnls_arr > 0))

        # Bootstrap CI
        ci = bootstrap_pf_ci(pnls_arr)
        tier = classify(pf, ci["pf_low"], n)

        results.append({
            "category": cat,
            "strategy": strat,
            "direction": direction,
            "n": n,
            "wr": round(wr * 100, 1),
            "pf": round(pf, 3),
            "pf_ci_low": round(ci["pf_low"], 3),
            "pf_ci_high": round(ci["pf_high"], 3),
            "pf_median": round(ci["pf_median"], 3),
            "avg_pnl": round(float(pnls_arr.mean()), 3),
            "total_pnl": round(float(pnls_arr.sum()), 1),
            "tier": tier,
        })

    # Sort: TIER-1 first, then by PF descending
    tier_order = {"TIER-1": 0, "TIER-2": 1, "EDGE": 2, "PROFITABLE": 3, "DESTROYER": 4}
    results.sort(key=lambda r: (tier_order.get(r["tier"], 99), -r["pf"]))

    # ── Per-class aggregate ──────────────────────────────────────────────
    per_class = fetch_per_class_aggregate(conn)
    if category_filter:
        per_class = [c for c in per_class if c["category"] == category_filter]

    # Class-level PF bootstrap
    class_pnls: Dict[str, List[float]] = defaultdict(list)
    for row in rows:
        cat = row["category"]
        if category_filter and cat != category_filter:
            continue
        class_pnls[cat].append(float(row["pnl_pct"]))

    for cls_entry in per_class:
        cat = cls_entry["category"]
        pnls_arr = np.array(class_pnls.get(cat, []), dtype=float)
        if len(pnls_arr) >= 10:
            ci = bootstrap_pf_ci(pnls_arr)
            cls_entry["pf_ci_low"] = round(ci["pf_low"], 3)
            cls_entry["pf_ci_high"] = round(ci["pf_high"], 3)

    # ── Summary counts ───────────────────────────────────────────────────
    tier_counts = defaultdict(int)
    winners: List[str] = []
    destroyers: List[str] = []
    for r in results:
        tier_counts[r["tier"]] += 1
        if r["tier"] in ("TIER-1", "TIER-2", "EDGE"):
            winners.append(f"{r['strategy']} {r['direction']} ({r['category']}, n={r['n']}, PF={r['pf']})")
        elif r["tier"] == "DESTROYER":
            destroyers.append(f"{r['strategy']} {r['direction']} ({r['category']}, n={r['n']}, PF={r['pf']})")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "n_bootstrap": N_BOOTSTRAP,
            "random_seed": RANDOM_SEED,
            "ci_alpha": CI_ALPHA,
            "min_n": min_n,
            "category_filter": category_filter,
        },
        "per_class": per_class,
        "per_combo": results,
        "summary": {
            "total_combos_evaluated": len(results),
            "tier_counts": dict(tier_counts),
            "winners": winners,
            "destroyers": destroyers,
        },
    }


# ── Output formatting ────────────────────────────────────────────────────────

def print_table(results: List[Dict[str, Any]], max_rows: int = 80):
    """Pretty-print the results table."""
    if not results:
        print("(no results)")
        return

    # Column widths
    header = f"{'Cat':<10} {'Strategy':<38} {'Dir':<7} {'n':>5} {'WR':>7} {'PF':>8} {'PF_CI_low':>10} {'Tier':<12}"
    sep = "-" * len(header)

    last_cat = ""
    for i, r in enumerate(results[:max_rows]):
        if r["category"] != last_cat:
            if last_cat:
                print()
            print(f"\n{'=' * len(header)}")
            last_cat = r["category"]
        if i == 0 or results[i - 1]["category"] != r["category"]:
            print(header)
            print(sep)

        tier_marker = {"TIER-1": "✅", "TIER-2": "🟡", "EDGE": "🔵", "PROFITABLE": "⚪", "DESTROYER": "💀"}.get(
            r["tier"], "?"
        )
        print(
            f"{r['category']:<10} {r['strategy']:<38} {r['direction']:<7} "
            f"{r['n']:>5} {r['wr']:>6.1f}% {r['pf']:>8.3f} {r['pf_ci_low']:>10.3f} "
            f"{tier_marker} {r['tier']:<10}"
        )

    if len(results) > max_rows:
        print(f"\n... ({len(results) - max_rows} more rows omitted)")


def print_per_class(per_class: List[Dict[str, Any]]):
    """Pretty-print per-asset-class summary."""
    print(f"\n{'=' * 90}")
    print("PER-ASSET-CLASS AGGREGATE (policy-clean)")
    print(f"{'=' * 90}")
    print(f"{'Class':<12} {'n':>6} {'WR':>7} {'PF':>8} {'PF_CI_low':>10} {'Total PnL%':>11} {'UniqStrat':>10} {'UniqSym':>8}")
    print("-" * 90)
    for c in per_class:
        pf_ci = f"{c.get('pf_ci_low', '?'):>10}" if "pf_ci_low" in c else f"{'?':>10}"
        print(
            f"{c['category']:<12} {c['n']:>6} {c['wr']:>6.1f}% {c['pf']:>8.3f} {pf_ci} "
            f"{c['total_pnl_pct']:>10.1f}% {c['unique_strategies']:>10} {c['unique_symbols']:>8}"
        )


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Monte Carlo Edge Audit — bootstrap PF significance testing per strategy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--category", type=str, default=None, help="Filter to single asset class")
    parser.add_argument("--min-n", type=int, default=20, help="Minimum trades per combo (default: 20)")
    parser.add_argument("--json", action="store_true", help="Output as JSON instead of table")
    parser.add_argument("--output", type=str, default=None, help="Write JSON report to file")
    args = parser.parse_args()

    log.info("Connecting to ejaguiar1_stocks...")
    conn = _connect()

    try:
        report = run_audit(conn, min_n=args.min_n, category_filter=args.category)

        if args.json:
            print(json.dumps(report, indent=2, default=str))
        else:
            print_per_class(report["per_class"])
            print_table(report["per_combo"])
            print(f"\n{'=' * 90}")
            print("SUMMARY")
            print(f"{'=' * 90}")
            print(f"Combos evaluated: {report['summary']['total_combos_evaluated']}")
            for tier, count in sorted(report["summary"]["tier_counts"].items()):
                print(f"  {tier}: {count}")
            print(f"\nWinners ({len(report['summary']['winners'])}):")
            for w in report["summary"]["winners"]:
                print(f"  • {w}")
            if report["summary"]["destroyers"]:
                print(f"\nDESTROYERS ({len(report['summary']['destroyers'])}):")
                for d in report["summary"]["destroyers"][:15]:
                    print(f"  💀 {d}")
                if len(report["summary"]["destroyers"]) > 15:
                    print(f"  ... and {len(report['summary']['destroyers']) - 15} more")

        if args.output:
            os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
            with open(args.output, "w") as f:
                json.dump(report, f, indent=2, default=str)
            log.info("Report written to %s", args.output)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
