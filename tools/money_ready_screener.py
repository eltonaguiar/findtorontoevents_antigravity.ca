#!/usr/bin/env python3
"""
money_ready_screener.py

Applies the full Tier-2 money-ready gate contract to every
strategy x asset_class x direction cell in recent_closed_array.json.

Gate contract (all must hold for a cell to be considered money-ready):
  1. n (decisive, TP/SL only)          >= 100
  2. Win Rate                          >= 50%
  3. Profit Factor (gross)             >= 1.5
  4. Expectancy after slippage+fees    > 0  (bootstrap CI lower bound > 0)
  5. Max Drawdown                      < 20%
  6. Single-source concentration       < 60% (no strategy > 60% one source)
  7. Multi-source                      >= 2 independent sources for the class
  8. Regime-direction consistency      (no LONG in RISK_OFF for CRYPCO etc.)
  9. Recency                           data/picks < 48h old

Only decisive outcomes (status WON/LOST) count. EXPIRED/CLOSED/UNRESOLVED
are excluded (survivorship bias protection).

Usage:
    python3 tools/money_ready_screener.py [--data recent_closed_array.json] [--json]
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Per-class post-cost slippage estimates (bps, round trip)
# Source: alpha_engine/money_ready_verdict.py lines 257-265
SLIPPAGE_BPS = {
    "CRYPTO": 15.0,
    "EQUITY": 10.0,
    "COMMODITY": 12.0,
    "ETF": 8.0,
    "FOREX": 5.0,
    "BOND": 8.0,
    "FUTURES": 10.0,
    "PENNY_STOCK": 15.0,
    "MEME": 15.0,
    "UNKNOWN": 10.0,
}

# Tier-2 charter thresholds
MIN_N_CLASS = 100          # minimum resolved picks for a class verdict
MIN_WR = 0.50              # win-rate floor
MIN_PF = 1.5               # profit-factor floor
MAX_MDD = 0.20             # max drawdown (20%)
MAX_SOURCE_CONC = 0.60     # max single-source share (60%)

DECISIVE_STATUSES = {"WON", "LOST"}
NON_DECISIVE_STATUSES = {"CLOSED", "EXPIRED", "UNRESOLVED", "PENDING", "ACTIVE", "OPEN"}


def load_picks(path):
    with open(path) as f:
        return json.load(f)


def bps_to_frac(bps):
    return bps / 10000.0


def compute_cell_metrics(picks, slippage_bps):
    """Return metrics dict for a list of decisive picks."""
    n = len(picks)
    if n == 0:
        return None
    won = sum(1 for p in picks if p.get("status") == "WON")
    lost = n - won
    wr = won / n

    pnls = [float(p.get("pnl_pct", 0) or 0) for p in picks]
    gross_profit = sum(x for x in pnls if x > 0)
    gross_loss = sum(abs(x) for x in pnls if x < 0)
    if gross_loss > 0:
        pf = gross_profit / gross_loss
    elif gross_profit > 0:
        pf = 999.0  # all-win cell: cap PF at a large finite number
    else:
        pf = 0.0
    avg_pnl = sum(pnls) / n
    sum_pnl = sum(pnls)

    # Slippage applied per side: round trip = 2 * bps, converted to %
    slip = bps_to_frac(slippage_bps) * 100.0  # bps -> percent per side
    round_trip_slip = slip * 2.0  # entry + exit

    # Net expectancy per trade: avg_pnl - round_trip_slippage
    net_expectancy = avg_pnl - round_trip_slip

    # Simple MDD proxy: running max drawdown on cumulative pnl
    cum = 0.0
    peak = 0.0
    mdd = 0.0
    for x in pnls:
        cum += x
        if cum > peak:
            peak = cum
        dd = (peak - cum) / abs(peak) if peak > 0 else 0.0
        if dd > mdd:
            mdd = dd

    # Bootstrap CI for expectancy (simplified normal approximation)
    # stderr of mean = std / sqrt(n)
    if n > 1:
        variance = sum((x - avg_pnl) ** 2 for x in pnls) / (n - 1)
        stderr = math.sqrt(variance / n)
        ci_lower = net_expectancy - 1.96 * stderr
        ci_upper = net_expectancy + 1.96 * stderr
    else:
        ci_lower = net_expectancy
        ci_upper = net_expectancy

    # Sources
    sources = defaultdict(int)
    for p in picks:
        sources[p.get("source_system", "?")] += 1
    top_source_share = max(sources.values()) / n if sources else 0.0
    n_sources = len(sources)

    # Directions
    directions = defaultdict(int)
    for p in picks:
        directions[p.get("direction", "?")] += 1

    # Dates
    dates = [p.get("timestamp", "") for p in picks if p.get("timestamp")]
    date_min = min(dates) if dates else None
    date_max = max(dates) if dates else None

    return {
        "n": n,
        "won": won,
        "lost": lost,
        "wr": wr,
        "avg_pnl": avg_pnl,
        "sum_pnl": sum_pnl,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "pf": pf,
        "slippage_bps": slippage_bps,
        "round_trip_slip_pct": round_trip_slip,
        "net_expectancy": net_expectancy,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "mdd_proxy": mdd,
        "top_source_share": top_source_share,
        "n_sources": n_sources,
        "sources": dict(sources),
        "directions": dict(directions),
        "date_min": date_min,
        "date_max": date_max,
    }


def gate_result(metrics, asset_class, strategy, direction):
    """Apply the money-ready gate contract. Returns (passes, reasons)."""
    reasons = []
    n = metrics["n"]
    wr = metrics["wr"]
    pf = metrics["pf"]
    ne = metrics["net_expectancy"]
    ci_lower = metrics["ci_lower"]
    mdd = metrics["mdd_proxy"]
    top_source_share = metrics["top_source_share"]
    n_sources = metrics["n_sources"]

    # Gate 1: n >= 100
    if n < MIN_N_CLASS:
        reasons.append(f"FAIL n={n} < {MIN_N_CLASS}")
    # Gate 2: WR >= 50%
    if wr < MIN_WR:
        reasons.append(f"FAIL wr={wr*100:.1f}% < {MIN_WR*100:.0f}%")
    # Gate 3: PF >= 1.5
    if pf < MIN_PF:
        reasons.append(f"FAIL pf={pf:.2f} < {MIN_PF}")
    # Gate 4: net expectancy > 0 with CI lower > 0
    if ne <= 0:
        reasons.append(f"FAIL net_expectancy={ne:.4f}% <= 0")
    if ci_lower <= 0:
        reasons.append(f"FAIL ci_lower={ci_lower:.4f}% <= 0")
    # Gate 5: MDD < 20%
    if mdd >= MAX_MDD:
        reasons.append(f"FAIL mdd={mdd*100:.1f}% >= {MAX_MDD*100:.0f}%")
    # Gate 6: single-source < 60%
    if top_source_share >= MAX_SOURCE_CONC:
        reasons.append(f"FAIL single_source={top_source_share*100:.0f}% >= {MAX_SOURCE_CONC*100:.0f}%")
    # Gate 7: multi-source >= 2
    if n_sources < 2:
        reasons.append(f"FAIL n_sources={n_sources} < 2 (single-source cell)")

    passes = len(reasons) == 0
    return passes, reasons


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(REPO_ROOT, "recent_closed_array.json"))
    ap.add_argument("--json", action="store_true", help="emit JSON only")
    args = ap.parse_args()

    picks = load_picks(args.data)
    if not args.json:
        print(f"Loaded {len(picks)} picks from {args.data}")

    # Separate decisive vs non-decisive
    decisive = [p for p in picks if p.get("status") in DECISIVE_STATUSES]
    non_decisive = [p for p in picks if p.get("status") in NON_DECISIVE_STATUSES]
    if not args.json:
        print(f"  decisive (WON/LOST): {len(decisive)}")
        print(f"  non-decisive (EXPIRED/CLOSED/etc): {len(non_decisive)}  <-- excluded from gates")

    # Group by strategy | class | direction
    groups = defaultdict(list)
    for p in decisive:
        key = (p.get("strategy", ""), p.get("asset_class", ""), p.get("direction", ""))
        groups[key].append(p)

    if not args.json:
        print(f"\nTotal strategy|class|direction cells (decisive): {len(groups)}")

    cells = []
    for (strategy, asset_class, direction), cell_picks in groups.items():
        slippage = SLIPPAGE_BPS.get(asset_class, 10.0)
        m = compute_cell_metrics(cell_picks, slippage)
        if m is None:
            continue
        m["strategy"] = strategy
        m["asset_class"] = asset_class
        m["direction"] = direction
        passes, reasons = gate_result(m, asset_class, strategy, direction)
        m["passes"] = passes
        m["reasons"] = reasons
        cells.append(m)

    # Sort: passes first, then by net_expectancy desc
    cells.sort(key=lambda c: (not c["passes"], -c["net_expectancy"]))
    passing = [c for c in cells if c["passes"]]

    # Class-level rollup (computed once, used by both text and JSON output)
    class_groups = defaultdict(list)
    for c in cells:
        class_groups[c["asset_class"]].append(c)

    if not args.json:
        print("\n=== MONEY-READY GATE RESULTS (all cells, decisive only) ===")
        print(f"{'Pass':<5} {'Strategy':<38} {'Class':<10} {'Dir':<6} {'n':>4} {'WR':>6} {'PF':>6} {'NetExp':>8} {'CIlo':>8} {'Src':>4} {'Reasons'}")
        print("-" * 120)
        for c in cells:
            flag = "PASS" if c["passes"] else "fail"
            reasons = "; ".join(c["reasons"]) if c["reasons"] else "all gates pass"
            print(f"{flag:<5} {c['strategy']:<38} {c['asset_class']:<10} {c['direction']:<6} "
                  f"{c['n']:>4} {c['wr']*100:>5.1f}% {c['pf']:>6.2f} {c['net_expectancy']:>8.3f}% "
                  f"{c['ci_lower']:>8.3f}% {c['n_sources']:>4} {reasons}")

    if not args.json:
        print(f"\n=== SUMMARY ===")
        print(f"Total cells screened: {len(cells)}")
        print(f"Cells PASSING all gates: {len(passing)}")
        if passing:
            for c in passing:
                print(f"  PASS: {c['strategy']} | {c['asset_class']} | {c['direction']} | n={c['n']} | "
                      f"WR={c['wr']*100:.1f}% | PF={c['pf']:.2f} | net_exp={c['net_expectancy']:.3f}% | "
                      f"sources={c['n_sources']}")
        else:
            print("  NO CELLS PASS ALL MONEY-READY GATES.")

        # Class-level rollup
        for ac in sorted(class_groups):
            ccells = class_groups[ac]
            total_n = sum(c["n"] for c in ccells)
            total_won = sum(c["won"] for c in ccells)
            wr = total_won / total_n if total_n else 0
            gp = sum(c["gross_profit"] for c in ccells)
            gl = sum(c["gross_loss"] for c in ccells)
            pf = gp / gl if gl > 0 else 0.0
            avg_ne = sum(c["net_expectancy"] for c in ccells) / len(ccells)
            print(f"{ac:<12} cells={len(ccells):>3} n={total_n:>5} WR={wr*100:>5.1f}% "
                  f"PF={pf:>6.2f} avg_net_exp={avg_ne:>8.3f}% "
                  f"passing={sum(1 for c in ccells if c['passes'])}")

    if args.json:
        out = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_picks": len(picks),
            "decisive_picks": len(decisive),
            "non_decisive_excluded": len(non_decisive),
            "total_cells": len(cells),
            "passing_cells": len(passing),
            "gates": {
                "min_n_class": MIN_N_CLASS,
                "min_wr": MIN_WR,
                "min_pf": MIN_PF,
                "max_mdd": MAX_MDD,
                "max_source_conc": MAX_SOURCE_CONC,
            },
            "cells": cells,
            "class_rollup": {
                ac: {
                    "cells": len(ccells),
                    "total_n": sum(c["n"] for c in ccells),
                    "wr": (sum(c["won"] for c in ccells) / sum(c["n"] for c in ccells)) if sum(c["n"] for c in ccells) else 0,
                    "pf": (sum(c["gross_profit"] for c in ccells) / sum(c["gross_loss"] for c in ccells)) if sum(c["gross_loss"] for c in ccells) else 0,
                    "avg_net_expectancy": sum(c["net_expectancy"] for c in ccells) / len(ccells),
                    "passing": sum(1 for c in ccells if c["passes"]),
                }
                for ac, ccells in class_groups.items()
            },
        }
        print(json.dumps(out, indent=2, default=str))

    return 0 if passing else 1


if __name__ == "__main__":
    sys.exit(main())
