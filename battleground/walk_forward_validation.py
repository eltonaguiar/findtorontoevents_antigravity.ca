#!/usr/bin/env python3
"""
Walk-Forward Validation of Battleground Trading Strategies
==========================================================
Splits closed trades into TRAIN (Feb 24 - Mar 5) and TEST (Mar 6 - Mar 13)
periods, then compares in-sample vs out-of-sample performance.

Key question: Do top strategies maintain their edge out-of-sample?
"""

import json
import os
from datetime import datetime, timezone
from math import comb
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLOSED_PICKS = os.path.join(SCRIPT_DIR, "data", "closed_picks.json")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "data", "walk_forward_results.json")

# Walk-forward split point
SPLIT_DATE = datetime(2026, 3, 6, 0, 0, 0, tzinfo=timezone.utc)

# Strategies to analyze
TARGET_STRATEGIES = [
    "crypto_keltner_compression_expansion_v1",
    "keltner_compression_expansion_eth_v1",
    "keltner_compression_expansion_sol_v1",
    "keltner_compression_expansion_xrp_v1",
    "drawdown_recovery_rsi",
    "multi_period_rsi_confluence_eth",
    "multi_period_rsi_confluence_xrp",
]


def parse_time(ts: str) -> datetime:
    """Parse ISO timestamp to datetime."""
    return datetime.fromisoformat(ts)


def binomial_pvalue(wins: int, n: int, p0: float = 0.5) -> float:
    """One-sided binomial test: P(X >= wins | n, p0).
    Tests whether the observed win rate is significantly better than p0."""
    if n == 0:
        return 1.0
    pval = 0.0
    for k in range(wins, n + 1):
        pval += comb(n, k) * (p0 ** k) * ((1 - p0) ** (n - k))
    return pval


def max_consecutive_losses(trades: list) -> int:
    """Calculate maximum consecutive losses."""
    max_streak = 0
    current = 0
    for t in sorted(trades, key=lambda x: x["entry_time"]):
        if t["status"] == "LOSS":
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


def analyze_period(trades: list) -> dict:
    """Calculate performance metrics for a set of trades."""
    if not trades:
        return {
            "num_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate_pct": 0.0,
            "avg_pnl_pct": 0.0,
            "profit_factor": 0.0,
            "max_consec_losses": 0,
            "gross_wins_pct": 0.0,
            "gross_losses_pct": 0.0,
            "total_pnl_pct": 0.0,
            "p_value": 1.0,
            "date_range": "",
        }

    wins = [t for t in trades if t["status"] == "WIN"]
    losses = [t for t in trades if t["status"] == "LOSS"]
    n_wins = len(wins)
    n_losses = len(losses)
    n = len(trades)

    gross_wins = sum(t["pnl_pct"] for t in wins) if wins else 0.0
    gross_losses = abs(sum(t["pnl_pct"] for t in losses)) if losses else 0.0
    profit_factor = (gross_wins / gross_losses) if gross_losses > 0 else float("inf")

    total_pnl = sum(t["pnl_pct"] for t in trades)
    avg_pnl = total_pnl / n

    dates = sorted(parse_time(t["entry_time"]) for t in trades)
    date_range = f"{dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}"

    return {
        "num_trades": n,
        "wins": n_wins,
        "losses": n_losses,
        "win_rate_pct": round(n_wins / n * 100, 1),
        "avg_pnl_pct": round(avg_pnl, 4),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else "inf",
        "max_consec_losses": max_consecutive_losses(trades),
        "gross_wins_pct": round(gross_wins, 4),
        "gross_losses_pct": round(gross_losses, 4),
        "total_pnl_pct": round(total_pnl, 4),
        "p_value": round(binomial_pvalue(n_wins, n, 0.5), 6),
        "date_range": date_range,
    }


def print_header(title: str):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")


def print_period_stats(label: str, stats: dict):
    if stats["num_trades"] == 0:
        print(f"  {label}: No trades")
        return
    pf = stats["profit_factor"]
    pf_str = f"{pf:.2f}" if isinstance(pf, float) else str(pf)
    sig = "***" if stats["p_value"] < 0.01 else "**" if stats["p_value"] < 0.05 else "*" if stats["p_value"] < 0.10 else ""
    print(f"  {label}:")
    print(f"    Trades: {stats['num_trades']}  |  W/L: {stats['wins']}/{stats['losses']}  |  WR: {stats['win_rate_pct']:.1f}% {sig}")
    print(f"    Avg PnL: {stats['avg_pnl_pct']:+.4f}%  |  Total PnL: {stats['total_pnl_pct']:+.4f}%")
    print(f"    PF: {pf_str}  |  Max Consec Losses: {stats['max_consec_losses']}  |  p-value: {stats['p_value']:.6f}")
    print(f"    Period: {stats['date_range']}")


def main():
    # Load data
    with open(CLOSED_PICKS, "r") as f:
        all_trades = json.load(f)

    print(f"Loaded {len(all_trades)} total closed trades")
    print(f"Walk-forward split: TRAIN < {SPLIT_DATE.strftime('%Y-%m-%d')} | TEST >= {SPLIT_DATE.strftime('%Y-%m-%d')}")

    results = {}

    for strategy in TARGET_STRATEGIES:
        strat_trades = [t for t in all_trades if t["strategy"] == strategy]
        if not strat_trades:
            continue

        train = [t for t in strat_trades if parse_time(t["entry_time"]) < SPLIT_DATE]
        test = [t for t in strat_trades if parse_time(t["entry_time"]) >= SPLIT_DATE]
        overall = strat_trades

        train_stats = analyze_period(train)
        test_stats = analyze_period(test)
        overall_stats = analyze_period(overall)

        # Determine robustness verdict
        if test_stats["num_trades"] == 0:
            verdict = "INSUFFICIENT DATA"
        elif test_stats["win_rate_pct"] >= 60:
            verdict = "ROBUST - Edge maintained out-of-sample"
        elif test_stats["win_rate_pct"] >= 55:
            verdict = "MARGINAL - Edge weakened but present"
        else:
            verdict = "DEGRADED - Possible curve-fitting"

        # WR degradation
        if train_stats["num_trades"] > 0 and test_stats["num_trades"] > 0:
            wr_change = test_stats["win_rate_pct"] - train_stats["win_rate_pct"]
        else:
            wr_change = 0

        results[strategy] = {
            "overall": overall_stats,
            "train": train_stats,
            "test": test_stats,
            "wr_change": round(wr_change, 1),
            "verdict": verdict,
        }

        print_header(strategy)
        print_period_stats("OVERALL", overall_stats)
        print_period_stats("TRAIN  (Feb 24 - Mar 5)", train_stats)
        print_period_stats("TEST   (Mar 6 - Mar 13)", test_stats)
        print(f"\n  WR Change (TEST - TRAIN): {wr_change:+.1f} pp")
        print(f"  VERDICT: {verdict}")

    # Summary table
    print_header("WALK-FORWARD SUMMARY TABLE")
    print(f"  {'Strategy':<45} {'Train WR':>10} {'Test WR':>10} {'Change':>8} {'Test PF':>8} {'Test p':>10} {'Verdict':<20}")
    print(f"  {'-'*45} {'-'*10} {'-'*10} {'-'*8} {'-'*8} {'-'*10} {'-'*20}")

    for strategy in TARGET_STRATEGIES:
        if strategy not in results:
            continue
        r = results[strategy]
        train_wr = f"{r['train']['win_rate_pct']:.1f}%" if r["train"]["num_trades"] > 0 else "N/A"
        test_wr = f"{r['test']['win_rate_pct']:.1f}%" if r["test"]["num_trades"] > 0 else "N/A"
        change = f"{r['wr_change']:+.1f}pp" if r["test"]["num_trades"] > 0 else "N/A"
        test_pf = r["test"]["profit_factor"]
        test_pf_str = f"{test_pf:.2f}" if isinstance(test_pf, float) else str(test_pf)
        test_p = f"{r['test']['p_value']:.4f}" if r["test"]["num_trades"] > 0 else "N/A"

        # Short name for display
        short = strategy.replace("crypto_", "").replace("keltner_compression_expansion", "keltner")
        short = short.replace("multi_period_rsi_confluence", "rsi_confluence")
        print(f"  {short:<45} {train_wr:>10} {test_wr:>10} {change:>8} {test_pf_str:>8} {test_p:>10} {r['verdict']}")

    # Key findings
    print_header("KEY FINDINGS")
    keltner_btc = results.get("crypto_keltner_compression_expansion_v1", {})
    if keltner_btc:
        test_wr = keltner_btc["test"]["win_rate_pct"]
        test_n = keltner_btc["test"]["num_trades"]
        test_p = keltner_btc["test"]["p_value"]
        print(f"\n  KELTNER BTC (Primary Question):")
        print(f"    Test Period WR: {test_wr:.1f}% over {test_n} trades")
        print(f"    p-value vs 50%: {test_p:.6f}")
        if test_wr >= 60:
            print(f"    CONCLUSION: Edge is ROBUST. WR >= 60% out-of-sample confirms the strategy is NOT curve-fitted.")
        elif test_wr >= 55:
            print(f"    CONCLUSION: Edge is MARGINAL. WR 55-60% suggests some real signal but weaker than in-sample.")
        else:
            print(f"    CONCLUSION: Edge DEGRADED. WR < 55% out-of-sample suggests possible curve-fitting.")

    # Identify best OOS performers
    oos_ranked = sorted(
        [(s, r) for s, r in results.items() if r["test"]["num_trades"] >= 5],
        key=lambda x: x[1]["test"]["win_rate_pct"],
        reverse=True,
    )
    if oos_ranked:
        print(f"\n  Best Out-of-Sample Performers (min 5 trades):")
        for i, (s, r) in enumerate(oos_ranked[:3], 1):
            short = s.replace("crypto_", "").replace("keltner_compression_expansion", "keltner")
            short = short.replace("multi_period_rsi_confluence", "rsi_confluence")
            print(f"    {i}. {short}: {r['test']['win_rate_pct']:.1f}% WR ({r['test']['num_trades']} trades)")

    # Save results
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "split_date": SPLIT_DATE.isoformat(),
        "total_trades_analyzed": len(all_trades),
        "strategies": results,
    }

    # Convert inf to string for JSON serialization
    def sanitize(obj):
        if isinstance(obj, float) and obj == float("inf"):
            return "inf"
        if isinstance(obj, dict):
            return {k: sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [sanitize(v) for v in obj]
        return obj

    with open(OUTPUT_FILE, "w") as f:
        json.dump(sanitize(output), f, indent=2)
    print(f"\n  Results saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
