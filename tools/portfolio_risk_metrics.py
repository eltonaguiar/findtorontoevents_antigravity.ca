#!/usr/bin/env python3
"""
CVaR / VaR Portfolio Risk Metrics
=================================
Computes Value-at-Risk and Conditional Value-at-Risk (Expected Shortfall)
at 95% and 99% confidence levels for the active portfolio.

Breakdowns: overall portfolio, per source_system (top 15), per asset_class.

Output: tools/portfolio_risk_results.json + printed summary table.
"""

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
DATA_PATH = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_PATH = REPO / "tools" / "portfolio_risk_results.json"


# ── helpers ─────────────────────────────────────────────────────────────────

def load_closed_picks():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        d = json.load(f)
    picks = d["picks"]["recent_closed"]
    # Filter to picks that have a numeric pnl_pct
    return [p for p in picks if isinstance(p.get("pnl_pct"), (int, float))]


def compute_risk(pnl_array: np.ndarray) -> dict:
    """Return VaR/CVaR/drawdown metrics for an array of per-trade PnL %."""
    if len(pnl_array) == 0:
        return {}
    sorted_pnl = np.sort(pnl_array)
    n = len(sorted_pnl)

    # VaR = loss at percentile (negative = loss)
    var95 = float(np.percentile(sorted_pnl, 5))
    var99 = float(np.percentile(sorted_pnl, 1))

    # CVaR = mean of losses beyond VaR threshold
    cvar95 = float(sorted_pnl[sorted_pnl <= var95].mean()) if np.any(sorted_pnl <= var95) else var95
    cvar99 = float(sorted_pnl[sorted_pnl <= var99].mean()) if np.any(sorted_pnl <= var99) else var99

    # Maximum drawdown on cumulative PnL curve
    cum = np.cumsum(sorted_pnl if len(sorted_pnl) > 0 else [0])
    # Use trade-order cumulative (not sorted) for drawdown
    cum_ordered = np.cumsum(pnl_array)
    peak = np.maximum.accumulate(cum_ordered)
    drawdowns = cum_ordered - peak
    max_dd = float(drawdowns.min())

    return {
        "n_trades": int(n),
        "mean_pnl_pct": round(float(pnl_array.mean()), 4),
        "std_pnl_pct": round(float(pnl_array.std()), 4),
        "VaR_95": round(var95, 4),
        "VaR_99": round(var99, 4),
        "CVaR_95": round(cvar95, 4),
        "CVaR_99": round(cvar99, 4),
        "max_drawdown_pct": round(max_dd, 4),
        "worst_trade_pct": round(float(sorted_pnl[0]), 4),
        "best_trade_pct": round(float(sorted_pnl[-1]), 4),
        "win_rate": round(float(np.mean(pnl_array > 0)) * 100, 2),
    }


# ── main ────────────────────────────────────────────────────────────────────

def main():
    picks = load_closed_picks()
    print(f"Loaded {len(picks)} closed picks with numeric PnL\n")

    all_pnl = np.array([p["pnl_pct"] for p in picks], dtype=float)

    # 1. Overall portfolio
    overall = compute_risk(all_pnl)

    # 2. Per source_system (top 15 by count)
    by_source = defaultdict(list)
    for p in picks:
        by_source[p.get("source_system", "unknown")].append(p["pnl_pct"])

    top_sources = sorted(by_source.keys(), key=lambda s: len(by_source[s]), reverse=True)[:15]
    per_source = {}
    for src in top_sources:
        per_source[src] = compute_risk(np.array(by_source[src], dtype=float))

    # 3. Per asset_class
    by_asset = defaultdict(list)
    for p in picks:
        by_asset[p.get("asset_class", "UNKNOWN")].append(p["pnl_pct"])

    per_asset = {}
    for ac in sorted(by_asset.keys()):
        per_asset[ac] = compute_risk(np.array(by_asset[ac], dtype=float))

    # ── write JSON ──────────────────────────────────────────────────────
    results = {
        "generated": str(np.datetime64("today")),
        "overall": overall,
        "per_source_system": per_source,
        "per_asset_class": per_asset,
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Results written to {OUT_PATH}\n")

    # ── print tables ────────────────────────────────────────────────────
    _print_section("OVERALL PORTFOLIO", overall)

    print("\n" + "=" * 100)
    print("PER SOURCE SYSTEM (top 15 by trade count)")
    print("=" * 100)
    _print_table_header()
    for src in top_sources:
        _print_table_row(src, per_source[src])

    print("\n" + "=" * 100)
    print("PER ASSET CLASS")
    print("=" * 100)
    _print_table_header()
    for ac in sorted(per_asset.keys()):
        _print_table_row(ac, per_asset[ac])


def _print_section(title, m):
    print("=" * 100)
    print(f"  {title}  ({m['n_trades']} trades)")
    print("=" * 100)
    print(f"  Mean PnL:      {m['mean_pnl_pct']:+.2f}%    Std: {m['std_pnl_pct']:.2f}%    WR: {m['win_rate']:.1f}%")
    print(f"  VaR  95%:      {m['VaR_95']:+.2f}%          VaR  99%: {m['VaR_99']:+.2f}%")
    print(f"  CVaR 95%:      {m['CVaR_95']:+.2f}%          CVaR 99%: {m['CVaR_99']:+.2f}%")
    print(f"  Max Drawdown:  {m['max_drawdown_pct']:+.2f}%")
    print(f"  Worst Trade:   {m['worst_trade_pct']:+.2f}%    Best Trade: {m['best_trade_pct']:+.2f}%")


def _print_table_header():
    print(f"{'Source':<28} {'N':>5} {'Mean%':>7} {'WR%':>6} {'VaR95':>8} {'VaR99':>8} {'CVaR95':>8} {'CVaR99':>8} {'MaxDD':>8} {'Worst':>8}")
    print("-" * 100)


def _print_table_row(name, m):
    print(
        f"{name:<28} {m['n_trades']:>5} {m['mean_pnl_pct']:>+7.2f} {m['win_rate']:>6.1f}"
        f" {m['VaR_95']:>+8.2f} {m['VaR_99']:>+8.2f} {m['CVaR_95']:>+8.2f} {m['CVaR_99']:>+8.2f}"
        f" {m['max_drawdown_pct']:>+8.2f} {m['worst_trade_pct']:>+8.2f}"
    )


if __name__ == "__main__":
    main()
