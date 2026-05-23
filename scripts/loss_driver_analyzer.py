#!/usr/bin/env python3
"""
Loss Driver Analyzer
====================
Identifies why specific asset classes or strategies are bleeding PnL.

Usage:
    python scripts/loss_driver_analyzer.py --asset-class FOREX
    python scripts/loss_driver_analyzer.py --asset-class COMMODITY
    python scripts/loss_driver_analyzer.py --strategy quan_engine_scalp
    python scripts/loss_driver_analyzer.py --top-n-worst 20

Outputs:
    Console report + JSON to scripts/loss_driver_reports/YYYYMMDD_HHMMSS.json
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "scripts" / "loss_driver_reports"


def classify_strategy(name: str) -> str:
    """Infer asset class from strategy name."""
    n = name.upper()
    if "FOREX" in n or "FX_" in n or "CARRY" in n or "CURRENCY" in n:
        return "FOREX"
    if "FUTURES" in n or "COMMODITY" in n or "COT" in n or "GC" in n or "CL=" in n:
        return "COMMODITY"
    if "STOCK" in n or "EQUITY" in n or "SPY" in n or "QQQ" in n:
        return "EQUITY"
    if "BOND" in n or "TLT" in n or "IEF" in n or "YIELD" in n:
        return "BOND"
    if "ETF" in n or "SECTOR" in n:
        return "ETF"
    # Default: check for crypto suffixes
    if any(x in n for x in ["USDT", "USD", "BTC", "ETH", "SOL", "BNB", "XRP"]):
        return "CRYPTO"
    return "UNKNOWN"


def load_strategy_performance():
    path = ROOT / "alpha_engine" / "data" / "strategy_performance.json"
    if not path.exists():
        print(f"ERROR: {path} not found")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def analyze_strategy(name, perf):
    """Deep-dive on a single strategy's losses from performance data."""
    analysis = {
        "strategy": name,
        "asset_class": classify_strategy(name),
        "total_trades": perf.get("closed_picks", 0),
        "wins": perf.get("wins", 0),
        "losses": perf.get("losses", 0),
        "win_rate": perf.get("win_rate", 0),
        "total_pnl_pct": perf.get("total_pnl_pct", 0),
        "avg_pnl_pct": perf.get("avg_pnl_pct", 0),
        "avg_win_pct": perf.get("avg_win_pct", 0),
        "avg_loss_pct": perf.get("avg_loss_pct", 0),
        "profit_factor": perf.get("profit_factor", 0),
        "sharpe": perf.get("sharpe", 0),
        "max_drawdown": perf.get("max_drawdown", 0),
        "avg_hold_days": perf.get("avg_hold_days", 0),
        "statistically_significant": perf.get("statistically_significant", False),
    }

    # Loss magnitude analysis
    if analysis["losses"] > 0 and analysis["avg_loss_pct"]:
        analysis["loss_to_win_ratio"] = abs(analysis["avg_loss_pct"]) / max(analysis["avg_win_pct"], 1e-10)
        analysis["expected_value_per_trade"] = (
            analysis["win_rate"] * analysis["avg_win_pct"] -
            (1 - analysis["win_rate"]) * abs(analysis["avg_loss_pct"])
        )

    # Exit reason breakdown
    exit_reasons = perf.get("exit_reasons", {})
    if exit_reasons:
        analysis["exit_reasons"] = exit_reasons
        total_exits = sum(exit_reasons.values())
        if total_exits > 0:
            analysis["sl_exit_share"] = exit_reasons.get("SL_HIT", 0) / total_exits
            analysis["tp_exit_share"] = exit_reasons.get("TP_HIT", 0) / total_exits
            analysis["time_exit_share"] = exit_reasons.get("TIME_EXIT", 0) / total_exits

    # Symbol concentration
    by_symbol = perf.get("by_symbol", {})
    if by_symbol:
        sym_pnl = sorted(
            [{"symbol": k, **v} for k, v in by_symbol.items()],
            key=lambda x: x.get("total_pnl_pct", 0),
        )
        analysis["worst_symbols"] = sym_pnl[:5]
        analysis["best_symbols"] = sym_pnl[-5:]

    return analysis


def analyze_asset_class(asset_class, perf_data):
    """Aggregate analysis across all strategies in an asset class."""
    class_strategies = {
        name: perf for name, perf in perf_data.items()
        if classify_strategy(name) == asset_class
    }

    total_trades = sum(p.get("closed_picks", 0) for p in class_strategies.values())
    total_pnl = sum(p.get("total_pnl_pct", 0) for p in class_strategies.values())

    strategy_summaries = []
    for name, perf in class_strategies.items():
        summary = analyze_strategy(name, perf)
        strategy_summaries.append(summary)

    # Sort by PnL
    strategy_summaries.sort(key=lambda x: x["total_pnl_pct"])

    # Loss concentration
    pnls = [s["total_pnl_pct"] for s in strategy_summaries if s["total_pnl_pct"] < 0]
    total_loss = sum(abs(p) for p in pnls)
    loss_concentration = {}
    if total_loss > 0:
        loss_concentration["top_1_loss_share"] = abs(pnls[0]) / total_loss if pnls else 0
        loss_concentration["top_3_loss_share"] = sum(abs(p) for p in pnls[:3]) / total_loss if len(pnls) >= 3 else 0

    report = {
        "asset_class": asset_class,
        "strategies_count": len(class_strategies),
        "total_trades": total_trades,
        "total_pnl_pct": round(total_pnl, 2),
        "top_bleeders": strategy_summaries[:10],
        "top_performers": sorted(strategy_summaries, key=lambda x: x["total_pnl_pct"], reverse=True)[:5],
        **loss_concentration,
    }
    return report


def print_report(report):
    """Pretty-print the report to console."""
    print("=" * 70)
    print(f"LOSS DRIVER REPORT — {report['asset_class']}")
    print("=" * 70)
    print(f"Strategies analyzed: {report['strategies_count']}")
    print(f"Total trades:        {report['total_trades']}")
    print(f"Total PnL:           {report['total_pnl_pct']}%")
    if "top_1_loss_share" in report:
        print(f"Top-1 strategy loss share: {report['top_1_loss_share']:.0%}")
        print(f"Top-3 strategy loss share: {report['top_3_loss_share']:.0%}")
    print("-" * 70)
    print("TOP BLEEDERS (worst first):")
    for i, s in enumerate(report["top_bleeders"][:5], 1):
        print(f"  {i}. {s['strategy'][:50]:50s}  n={s['total_trades']:4d}  WR={s['win_rate']:.1%}  "
              f"PnL={s['total_pnl_pct']:+.1f}%  PF={s.get('profit_factor', 0):.2f}")
        if "loss_to_win_ratio" in s:
            print(f"      loss/win={s['loss_to_win_ratio']:.2f}x  EV={s.get('expected_value_per_trade', 0):+.3f}%")
    print("-" * 70)
    print("TOP PERFORMERS:")
    for i, s in enumerate(report["top_performers"][:3], 1):
        print(f"  {i}. {s['strategy'][:50]:50s}  n={s['total_trades']:4d}  WR={s['win_rate']:.1%}  "
              f"PnL={s['total_pnl_pct']:+.1f}%")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Loss Driver Analyzer")
    parser.add_argument("--asset-class", choices=["CRYPTO", "EQUITY", "ETF", "FOREX", "COMMODITY", "BOND"])
    parser.add_argument("--strategy")
    parser.add_argument("--top-n-worst", type=int, default=0)
    parser.add_argument("--output-json", action="store_true")
    args = parser.parse_args()

    perf_data = load_strategy_performance()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    if args.strategy:
        perf = perf_data.get(args.strategy, {})
        if not perf:
            print(f"ERROR: Strategy '{args.strategy}' not found")
            sys.exit(1)
        analysis = analyze_strategy(args.strategy, perf)
        print(json.dumps(analysis, indent=2))
        if args.output_json:
            out = REPORTS_DIR / f"{timestamp}_{args.strategy}_report.json"
            out.write_text(json.dumps(analysis, indent=2))
            print(f"\nSaved to {out}")

    elif args.asset_class:
        report = analyze_asset_class(args.asset_class, perf_data)
        print_report(report)
        if args.output_json:
            out = REPORTS_DIR / f"{timestamp}_{args.asset_class}_report.json"
            out.write_text(json.dumps(report, indent=2))
            print(f"\nSaved to {out}")

    elif args.top_n_worst:
        results = []
        for name, perf in perf_data.items():
            if perf.get("total_pnl_pct", 0) < -1:  # Only significant bleeders
                analysis = analyze_strategy(name, perf)
                results.append(analysis)
        results.sort(key=lambda x: x.get("total_pnl_pct", 0))
        for r in results[:args.top_n_worst]:
            print(f"{r['strategy']:50s}  n={r['total_trades']:5d}  WR={r['win_rate']:.1%}  "
                  f"PnL={r['total_pnl_pct']:+.1f}%  PF={r.get('profit_factor', 0):.2f}  "
                  f"Sharpe={r.get('sharpe', 0):.2f}  Class={r['asset_class']}")
        if args.output_json:
            out = REPORTS_DIR / f"{timestamp}_top{args.top_n_worst}_worst.json"
            out.write_text(json.dumps(results[:args.top_n_worst], indent=2))
            print(f"\nSaved to {out}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
