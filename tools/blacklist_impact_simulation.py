#!/usr/bin/env python3
"""
Blacklist Impact Simulation
============================
Measures portfolio-level WR/PF/PnL improvement after removing the 19
strategies killed by honest_kill_switch.py.

Queries at_signal_outcomes (honest ledger) directly from MySQL and computes:
  1. BASELINE: all strategies included
  2. POST-BLACKLIST: killed strategies excluded
  3. Delta: WR lift, PF lift, PnL lift, trade count reduction

Usage:
    source ~/.config/findtorontoevents/windows_ported_env.sh
    python3 tools/blacklist_impact_simulation.py
"""

from __future__ import annotations
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KILL_SWITCH_PATH = REPO / "alpha_engine" / "data" / "honest_kill_switch.json"


def get_connection():
    import pymysql
    pw = os.environ.get("DB_PASS_STOCKS", "")
    if not pw:
        print("ERROR: DB_PASS_STOCKS not set. Source windows_ported_env.sh first.")
        sys.exit(1)
    return pymysql.connect(
        host="mysql.50webs.com",
        user="ejaguiar1_stocks",
        password=pw,
        database="ejaguiar1_stocks",
        connect_timeout=15,
        cursorclass=pymysql.cursors.DictCursor,
    )


def load_killed_strategies() -> set[str]:
    """Load the set of killed strategy names from honest_kill_switch.json."""
    if not KILL_SWITCH_PATH.exists():
        print(f"ERROR: {KILL_SWITCH_PATH} not found. Run honest_kill_switch.py first.")
        sys.exit(1)
    data = json.loads(KILL_SWITCH_PATH.read_text())
    return {e["strategy"].lower() for e in data.get("killed", [])}


def fetch_all_outcomes(conn):
    """Fetch all closed trades from at_signal_outcomes."""
    cur = conn.cursor()
    cur.execute("""
        SELECT
            strategy,
            source_system,
            asset_class,
            outcome,
            pnl_pct,
            closed_at
        FROM at_signal_outcomes
        WHERE outcome IN ('WON', 'TP_HIT', 'LOST', 'SL_HIT', 'EXPIRED')
          AND pnl_pct IS NOT NULL
          AND strategy IS NOT NULL
          AND strategy != ''
    """)
    rows = cur.fetchall()
    cur.close()
    # Convert Decimal types to float for JSON serialization
    for r in rows:
        if r.get("pnl_pct") is not None:
            r["pnl_pct"] = float(r["pnl_pct"])
    return rows


def compute_portfolio_metrics(trades: list[dict], label: str) -> dict:
    """Compute portfolio-level metrics from a list of trade dicts."""
    n = len(trades)
    if n == 0:
        return {"label": label, "n": 0, "wins": 0, "losses": 0, "expired": 0,
                "closed": 0, "wr": 0, "pf": 0, "total_pnl": 0, "avg_pnl": 0,
                "expectancy": 0, "gross_wins": 0, "gross_losses": 0}

    wins = sum(1 for t in trades if t["outcome"] in ("WON", "TP_HIT"))
    losses = sum(1 for t in trades if t["outcome"] in ("LOST", "SL_HIT"))
    expired = sum(1 for t in trades if t["outcome"] == "EXPIRED")
    closed = wins + losses  # exclude expired from WR denominator

    gross_wins = sum(abs(t["pnl_pct"]) for t in trades
                     if t["outcome"] in ("WON", "TP_HIT") and t["pnl_pct"] is not None)
    gross_losses = sum(abs(t["pnl_pct"]) for t in trades
                       if t["outcome"] in ("LOST", "SL_HIT") and t["pnl_pct"] is not None)
    total_pnl = sum(t["pnl_pct"] for t in trades if t["pnl_pct"] is not None)

    wr = wins / closed if closed > 0 else 0
    pf = gross_wins / gross_losses if gross_losses > 0 else (99.0 if gross_wins > 0 else 0)
    avg_pnl = total_pnl / n if n > 0 else 0
    expectancy = total_pnl / closed if closed > 0 else 0

    return {
        "label": label,
        "n": n,
        "wins": wins,
        "losses": losses,
        "expired": expired,
        "closed": closed,
        "wr": round(wr, 4),
        "pf": round(pf, 4),
        "total_pnl": round(total_pnl, 2),
        "avg_pnl": round(avg_pnl, 4),
        "expectancy": round(expectancy, 4),
        "gross_wins": round(gross_wins, 2),
        "gross_losses": round(gross_losses, 2),
    }


def compute_per_strategy_breakdown(trades: list[dict], killed_set: set[str]) -> dict:
    """Break down by strategy, split into killed vs surviving."""
    by_strat = defaultdict(list)
    for t in trades:
        by_strat[t["strategy"].lower()].append(t)

    killed_detail = []
    surviving_detail = []

    for strat_lc, strat_trades in sorted(by_strat.items(), key=lambda x: -len(x[1])):
        m = compute_portfolio_metrics(strat_trades, strat_lc)
        entry = {
            "strategy": strat_trades[0]["strategy"],  # original case
            **m,
        }
        if strat_lc in killed_set:
            entry["status"] = "KILLED"
            killed_detail.append(entry)
        else:
            entry["status"] = "SURVIVING"
            surviving_detail.append(entry)

    return {
        "killed_strategies": killed_detail,
        "surviving_strategies": surviving_detail,
    }


def compute_per_asset_class(trades: list[dict], killed_set: set[str]) -> dict:
    """Per-asset-class metrics: baseline vs post-blacklist."""
    by_ac = defaultdict(list)
    for t in trades:
        ac = (t.get("asset_class") or "UNKNOWN").upper()
        by_ac[ac].append(t)

    results = {}
    for ac, ac_trades in sorted(by_ac.items(), key=lambda x: -len(x[1])):
        baseline = compute_portfolio_metrics(ac_trades, f"{ac}_baseline")
        filtered = [t for t in ac_trades if t["strategy"].lower() not in killed_set]
        post = compute_portfolio_metrics(filtered, f"{ac}_post_blacklist")
        results[ac] = {"baseline": baseline, "post_blacklist": post}
    return results


def main():
    killed_set = load_killed_strategies()
    print(f"Loaded {len(killed_set)} killed strategies from {KILL_SWITCH_PATH.name}")
    print()

    conn = get_connection()
    rows = fetch_all_outcomes(conn)
    conn.close()
    print(f"Fetched {len(rows)} closed trades from at_signal_outcomes")
    print()

    # ---- Portfolio-level comparison ----
    baseline = compute_portfolio_metrics(rows, "ALL STRATEGIES (BASELINE)")
    filtered_trades = [r for r in rows if r["strategy"].lower() not in killed_set]
    post = compute_portfolio_metrics(filtered_trades, "POST-BLACKLIST")

    print("=" * 78)
    print("  PORTFOLIO-LEVEL IMPACT: BEFORE vs AFTER BLACKLIST")
    print("=" * 78)
    print()
    hdr = f"{'Metric':<30s} {'BASELINE':>14s} {'POST-BLACKLIST':>14s} {'DELTA':>14s}"
    print(hdr)
    print("-" * 78)

    def row(name, base_val, post_val, fmt=".4f", pct=False):
        delta = post_val - base_val
        sign = "+" if delta > 0 else ""
        suffix = "%" if pct else ""
        print(f"  {name:<28s} {base_val:>12{fmt}}{suffix} {post_val:>12{fmt}}{suffix} {sign}{delta:>11{fmt}}{suffix}")

    row("Trades", baseline["n"], post["n"], ".0f")
    row("Wins", baseline["wins"], post["wins"], ".0f")
    row("Losses", baseline["losses"], post["losses"], ".0f")
    row("Win Rate", baseline["wr"] * 100, post["wr"] * 100, ".2f", pct=True)
    row("Profit Factor", baseline["pf"], post["pf"], ".4f")
    row("Total PnL (%)", baseline["total_pnl"], post["total_pnl"], ".2f")
    row("Avg PnL / Trade", baseline["avg_pnl"], post["avg_pnl"], ".4f")
    row("Expectancy / Trade", baseline["expectancy"], post["expectancy"], ".4f")
    row("Gross Wins (%)", baseline["gross_wins"], post["gross_wins"], ".2f")
    row("Gross Losses (%)", baseline["gross_losses"], post["gross_losses"], ".2f")

    print()

    # ---- Trade count reduction ----
    removed = baseline["n"] - post["n"]
    pct_removed = removed / baseline["n"] * 100 if baseline["n"] > 0 else 0
    print(f"  Trades removed: {removed} / {baseline['n']} ({pct_removed:.1f}%)")
    print(f"  WR lift:  {baseline['wr']*100:.2f}% → {post['wr']*100:.2f}% "
          f"(+{(post['wr'] - baseline['wr'])*100:.2f} pp)")
    print(f"  PF lift:  {baseline['pf']:.4f} → {post['pf']:.4f} "
          f"(+{post['pf'] - baseline['pf']:.4f})")

    # ---- Per-asset-class breakdown ----
    print()
    print("=" * 78)
    print("  PER-ASSET-CLASS IMPACT")
    print("=" * 78)
    ac_data = compute_per_asset_class(rows, killed_set)
    print()
    print(f"  {'Asset Class':<14s} {'Baseline WR':>12s} {'Post WR':>10s} {'WR Lift':>10s} "
          f"{'Baseline PF':>12s} {'Post PF':>10s} {'PF Lift':>10s} {'Trades Lost':>12s}")
    print("  " + "-" * 92)
    for ac, data in sorted(ac_data.items(), key=lambda x: -x[1]["baseline"]["n"]):
        b = data["baseline"]
        p = data["post_blacklist"]
        wr_lift = (p["wr"] - b["wr"]) * 100
        pf_lift = p["pf"] - b["pf"]
        trades_lost = b["n"] - p["n"]
        wr_s = f"+{wr_lift:.2f}" if wr_lift > 0 else f"{wr_lift:.2f}"
        pf_s = f"+{pf_lift:.4f}" if pf_lift > 0 else f"{pf_lift:.4f}"
        print(f"  {ac:<14s} {b['wr']*100:>10.2f}% {p['wr']*100:>8.2f}% {wr_s:>9s}pp "
              f"{b['pf']:>12.4f} {p['pf']:>10.4f} {pf_s:>10s} {trades_lost:>12d}")

    # ---- Top killed strategies by PnL damage ----
    print()
    print("=" * 78)
    print("  TOP KILLED STRATEGIES BY TOTAL PNL DAMAGE")
    print("=" * 78)
    print()
    breakdown = compute_per_strategy_breakdown(rows, killed_set)
    killed_sorted = sorted(breakdown["killed_strategies"], key=lambda x: x["total_pnl"])
    print(f"  {'Strategy':<45s} {'Trades':>7s} {'WR':>8s} {'PF':>8s} {'Total PnL':>12s}")
    print("  " + "-" * 82)
    for entry in killed_sorted:
        print(f"  {entry['strategy']:<45s} {entry['n']:>7d} "
              f"{entry['wr']*100:>6.1f}% {entry['pf']:>8.4f} {entry['total_pnl']:>+11.2f}%")

    total_killed_pnl = sum(e["total_pnl"] for e in killed_sorted)
    total_killed_trades = sum(e["n"] for e in killed_sorted)
    print()
    print(f"  {'TOTAL DAMAGE FROM KILLED STRATEGIES':<45s} {total_killed_trades:>7d} "
          f"{'':>8s} {'':>8s} {total_killed_pnl:>+11.2f}%")

    # ---- Surviving strategies ----
    print()
    print("=" * 78)
    print("  SURVIVING STRATEGIES (POST-BLACKLIST)")
    print("=" * 78)
    print()
    surviving_sorted = sorted(breakdown["surviving_strategies"],
                              key=lambda x: -x["n"])
    print(f"  {'Strategy':<45s} {'Trades':>7s} {'WR':>8s} {'PF':>8s} {'Total PnL':>12s}")
    print("  " + "-" * 82)
    for entry in surviving_sorted[:20]:  # top 20 by volume
        print(f"  {entry['strategy']:<45s} {entry['n']:>7d} "
              f"{entry['wr']*100:>6.1f}% {entry['pf']:>8.4f} {entry['total_pnl']:>+11.2f}%")
    if len(surviving_sorted) > 20:
        remaining = len(surviving_sorted) - 20
        remaining_pnl = sum(e["total_pnl"] for e in surviving_sorted[20:])
        print(f"  ... +{remaining} more strategies ({remaining_pnl:+.2f}% total PnL)")

    total_surviving_pnl = sum(e["total_pnl"] for e in surviving_sorted)
    total_surviving_trades = sum(e["n"] for e in surviving_sorted)
    print()
    print(f"  {'TOTAL SURVIVING PORTFOLIO':<45s} {total_surviving_trades:>7d} "
          f"{'':>8s} {'':>8s} {total_surviving_pnl:>+11.2f}%")

    # ---- Summary verdict ----
    print()
    print("=" * 78)
    print("  VERDICT")
    print("=" * 78)
    print()
    wr_lift_pp = (post["wr"] - baseline["wr"]) * 100
    pf_lift = post["pf"] - baseline["pf"]
    pnl_saved = baseline["total_pnl"] - post["total_pnl"]

    verdict = "POSITIVE" if wr_lift_pp > 0 else "NEGATIVE"
    print(f"  Blacklisting {len(killed_set)} strategies removes {pct_removed:.1f}% of trades")
    print(f"  but improves WR by {wr_lift_pp:+.2f} pp and PF by {pf_lift:+.4f}")
    print(f"  {pnl_saved:+.2f}% PnL damage removed from portfolio")
    print(f"  Overall impact: {verdict}")
    print()

    if post["pf"] >= 1.0 and baseline["pf"] < 1.0:
        print("  ★ Portfolio crosses PF 1.0 threshold — from negative to positive expectancy!")
    elif post["pf"] > baseline["pf"]:
        print(f"  ★ Portfolio PF improved from {baseline['pf']:.4f} to {post['pf']:.4f}")

    # ---- Save report ----
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "killed_strategies_count": len(killed_set),
        "killed_strategies": sorted(killed_set),
        "baseline": baseline,
        "post_blacklist": post,
        "delta": {
            "trades_removed": removed,
            "trades_removed_pct": round(pct_removed, 1),
            "wr_lift_pp": round(wr_lift_pp, 2),
            "pf_lift": round(pf_lift, 4),
            "pnl_damage_removed": round(pnl_saved, 2),
        },
        "per_asset_class": {
            ac: {
                "baseline_wr": d["baseline"]["wr"],
                "post_wr": d["post_blacklist"]["wr"],
                "baseline_pf": d["baseline"]["pf"],
                "post_pf": d["post_blacklist"]["pf"],
                "trades_lost": d["baseline"]["n"] - d["post_blacklist"]["n"],
            }
            for ac, d in ac_data.items()
        },
        "verdict": verdict,
    }
    out_path = REPO / "reports" / "blacklist_impact_simulation.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, default=float)
    print(f"  Full report saved to: {out_path}")


if __name__ == "__main__":
    main()
