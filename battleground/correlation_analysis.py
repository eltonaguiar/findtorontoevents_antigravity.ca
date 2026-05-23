#!/usr/bin/env python3
"""
Battleground Analysis Suite
Part 1: Keltner Signal Correlation Matrix (BTC/ETH/SOL/XRP)
Part 2: Monte Carlo Stress Test (5000 simulations, 4 portfolios)

Usage: python correlation_analysis.py
"""

import json
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict
import random
import math

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def load_data():
    """Load closed and active picks."""
    with open(os.path.join(DATA_DIR, "closed_picks.json")) as f:
        closed = json.load(f)
    with open(os.path.join(DATA_DIR, "active_picks.json")) as f:
        active = json.load(f)
    return closed, active


def parse_time(ts):
    """Parse ISO timestamp to datetime."""
    # Handle both entry_time (closed) and timestamp (active) formats
    ts = ts.replace("+00:00", "").replace("Z", "")
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f")


def time_to_4h_bucket(dt):
    """Round datetime to 4-hour bucket."""
    return dt.replace(hour=(dt.hour // 4) * 4, minute=0, second=0, microsecond=0)


# =============================================================================
# PART 1: Keltner Signal Correlation Matrix
# =============================================================================

KELTNER_STRATEGIES = {
    "crypto_keltner_compression_expansion_v1": "BTC",
    "keltner_compression_expansion_eth_v1": "ETH",
    "keltner_compression_expansion_sol_v1": "SOL",
    "keltner_compression_expansion_xrp_v1": "XRP",
}


def build_signal_events(closed, active):
    """Extract timestamped signal events for each Keltner strategy."""
    events = defaultdict(list)  # strategy -> [(bucket, direction), ...]

    for trade in closed:
        strat = trade["strategy"]
        if strat in KELTNER_STRATEGIES:
            dt = parse_time(trade["entry_time"])
            bucket = time_to_4h_bucket(dt)
            events[strat].append((bucket, trade["direction"]))

    for trade in active:
        strat = trade["strategy"]
        if strat in KELTNER_STRATEGIES:
            dt = parse_time(trade["timestamp"])
            bucket = time_to_4h_bucket(dt)
            events[strat].append((bucket, trade["direction"]))

    return events


def compute_correlation_matrix(events):
    """
    For each pair of Keltner strategies, compute:
    - % of signals that fire in the same 4h window (temporal correlation)
    - Direction agreement when co-firing
    """
    strats = sorted(KELTNER_STRATEGIES.keys(), key=lambda s: KELTNER_STRATEGIES[s])

    # Build bucket sets: strategy -> {bucket: [directions]}
    bucket_map = {}
    for strat in strats:
        bm = defaultdict(list)
        for bucket, direction in events.get(strat, []):
            bm[bucket].append(direction)
        bucket_map[strat] = bm

    pairs = []
    for i in range(len(strats)):
        for j in range(i + 1, len(strats)):
            s1, s2 = strats[i], strats[j]
            label = f"{KELTNER_STRATEGIES[s1]}/{KELTNER_STRATEGIES[s2]}"

            buckets_1 = set(bucket_map[s1].keys())
            buckets_2 = set(bucket_map[s2].keys())
            union = buckets_1 | buckets_2
            overlap = buckets_1 & buckets_2

            if not union:
                pairs.append({
                    "pair": label,
                    "temporal_correlation_pct": 0,
                    "overlap_count": 0,
                    "union_count": 0,
                    "direction_agreement_pct": 0,
                    "agree_count": 0,
                    "disagree_count": 0,
                })
                continue

            temporal_corr = len(overlap) / len(union) * 100

            # Direction agreement in overlapping buckets
            agree = 0
            disagree = 0
            for bucket in overlap:
                dirs_1 = bucket_map[s1][bucket]
                dirs_2 = bucket_map[s2][bucket]
                # Use majority direction for each
                maj_1 = max(set(dirs_1), key=dirs_1.count)
                maj_2 = max(set(dirs_2), key=dirs_2.count)
                if maj_1 == maj_2:
                    agree += 1
                else:
                    disagree += 1

            dir_agree_pct = agree / len(overlap) * 100 if overlap else 0

            pairs.append({
                "pair": label,
                "temporal_correlation_pct": round(temporal_corr, 1),
                "overlap_count": len(overlap),
                "union_count": len(union),
                "direction_agreement_pct": round(dir_agree_pct, 1),
                "agree_count": agree,
                "disagree_count": disagree,
            })

    return pairs, strats, bucket_map


def print_correlation_report(pairs, strats, bucket_map):
    """Print formatted correlation analysis."""
    print("=" * 80)
    print("PART 1: KELTNER SIGNAL CORRELATION MATRIX")
    print("=" * 80)

    # Strategy summary
    print("\n--- Strategy Signal Counts ---")
    for strat in strats:
        name = KELTNER_STRATEGIES[strat]
        n_buckets = len(bucket_map[strat])
        total_signals = sum(len(v) for v in bucket_map[strat].values())
        print(f"  {name:4s} Keltner: {total_signals:3d} signals across {n_buckets:3d} unique 4h windows")

    # Correlation matrix
    print("\n--- Temporal Correlation (same 4h window) ---")
    print(f"  {'Pair':<12s} {'Overlap':>8s} {'Union':>8s} {'Corr%':>8s} {'Dir Agree%':>11s} {'Agree':>6s} {'Disagree':>9s}")
    print("  " + "-" * 66)
    for p in pairs:
        print(f"  {p['pair']:<12s} {p['overlap_count']:>8d} {p['union_count']:>8d} "
              f"{p['temporal_correlation_pct']:>7.1f}% {p['direction_agreement_pct']:>10.1f}% "
              f"{p['agree_count']:>6d} {p['disagree_count']:>9d}")

    # Visual matrix
    names = [KELTNER_STRATEGIES[s] for s in strats]
    n = len(names)
    matrix = [["-" for _ in range(n)] for _ in range(n)]
    for p in pairs:
        a, b = p["pair"].split("/")
        i, j = names.index(a), names.index(b)
        matrix[i][j] = f"{p['temporal_correlation_pct']:.0f}%"
        matrix[j][i] = f"{p['direction_agreement_pct']:.0f}%"

    print("\n--- Correlation Matrix (upper=temporal%, lower=direction agreement%) ---")
    print(f"  {'':>6s}", end="")
    for name in names:
        print(f" {name:>6s}", end="")
    print()
    for i, name in enumerate(names):
        print(f"  {name:>6s}", end="")
        for j in range(n):
            if i == j:
                print(f" {'---':>6s}", end="")
            else:
                print(f" {matrix[i][j]:>6s}", end="")
        print()

    # Conclusion
    print("\n--- CONCLUSION ---")
    high_corr = [p for p in pairs if p["temporal_correlation_pct"] > 80]
    med_corr = [p for p in pairs if 50 <= p["temporal_correlation_pct"] <= 80]
    low_corr = [p for p in pairs if p["temporal_correlation_pct"] < 50]

    if high_corr:
        print("  HIGH CORRELATION (>80%) - Illusory diversification:")
        for p in high_corr:
            print(f"    {p['pair']}: {p['temporal_correlation_pct']:.1f}% temporal, "
                  f"{p['direction_agreement_pct']:.1f}% direction agreement")
            print(f"      -> These are effectively the SAME trade. Running both adds concentration risk.")

    if med_corr:
        print("  MODERATE CORRELATION (50-80%) - Partial diversification:")
        for p in med_corr:
            print(f"    {p['pair']}: {p['temporal_correlation_pct']:.1f}% temporal, "
                  f"{p['direction_agreement_pct']:.1f}% direction agreement")
            print(f"      -> Some independent signals, but still correlated. Size accordingly.")

    if low_corr:
        print("  LOW CORRELATION (<50%) - Genuine diversification:")
        for p in low_corr:
            print(f"    {p['pair']}: {p['temporal_correlation_pct']:.1f}% temporal, "
                  f"{p['direction_agreement_pct']:.1f}% direction agreement")
            print(f"      -> Independent signals. Good for portfolio construction.")

    avg_corr = sum(p["temporal_correlation_pct"] for p in pairs) / len(pairs) if pairs else 0
    avg_dir = sum(p["direction_agreement_pct"] for p in pairs) / len(pairs) if pairs else 0
    print(f"\n  AVERAGE temporal correlation: {avg_corr:.1f}%")
    print(f"  AVERAGE direction agreement:  {avg_dir:.1f}%")
    if avg_corr > 70:
        print("  VERDICT: Keltner strategies across pairs are HIGHLY correlated.")
        print("           Crypto moves together. Diversification across BTC/ETH/SOL/XRP Keltner")
        print("           provides LESS risk reduction than expected. Consider strategy diversity instead.")
    elif avg_corr > 50:
        print("  VERDICT: Moderate correlation. Some diversification benefit, but crypto pairs")
        print("           still tend to move together. Mix with non-Keltner strategies for best results.")
    else:
        print("  VERDICT: Low correlation. Keltner signals fire independently across pairs.")
        print("           Genuine diversification benefit from running multiple pairs.")

    return pairs


# =============================================================================
# PART 2: Monte Carlo Stress Test (5000 simulations)
# =============================================================================

PORTFOLIOS = {
    "A: Keltner-Only (BTC+ETH+SOL)": [
        "crypto_keltner_compression_expansion_v1",
        "keltner_compression_expansion_eth_v1",
        "keltner_compression_expansion_sol_v1",
    ],
    "B: Keltner+RSI Expanded": [
        "crypto_keltner_compression_expansion_v1",
        "keltner_compression_expansion_eth_v1",
        "keltner_compression_expansion_sol_v1",
        "keltner_compression_expansion_xrp_v1",
        "multi_period_rsi_confluence_eth",
        "multi_period_rsi_confluence_xrp",
    ],
    "C: Full Battleground (all)": [
        "crypto_keltner_compression_expansion_v1",
        "keltner_compression_expansion_eth_v1",
        "keltner_compression_expansion_sol_v1",
        "keltner_compression_expansion_xrp_v1",
        "multi_period_rsi_confluence_eth",
        "multi_period_rsi_confluence_xrp",
        "crypto_drawdown_convexity_recovery_v1",
        "drawdown_recovery_rsi",
        "drawdown_recovery_rsi_eth",
    ],
    "D: Best Per-Trade (DD Recovery + Keltner BTC)": [
        "crypto_drawdown_convexity_recovery_v1",
        "crypto_keltner_compression_expansion_v1",
    ],
}

# Also include whale RSI if present in the full battleground
ALL_STRATEGIES_FULL = None  # Will be set dynamically


def get_portfolio_trades(closed, strategy_list):
    """Filter closed trades for given strategies."""
    return [t for t in closed if t["strategy"] in strategy_list]


def run_monte_carlo(trades, n_sims=5000, start_capital=1000.0, position_pct=0.05, seed=42):
    """
    Run Monte Carlo simulation with bootstrap resampling.

    For each simulation:
    - Resample len(trades) trades WITH replacement
    - Add random slippage: uniform(-0.5%, +0.1%)
    - Add random fee drag: uniform(-0.15%, -0.05%)
    - Track equity curve with 5% position sizing
    """
    random.seed(seed)

    if not trades:
        return {
            "n_trades_source": 0,
            "n_simulations": n_sims,
            "median_final": start_capital,
            "p5_final": start_capital,
            "p95_final": start_capital,
            "p95_max_drawdown_pct": 0,
            "prob_ruin_pct": 0,
            "annual_return_ci_95": [0, 0],
            "median_max_drawdown_pct": 0,
            "mean_final": start_capital,
        }

    pnl_list = [t["pnl_pct"] for t in trades]
    n_trades = len(pnl_list)

    # Estimate trading period for annualization
    times = sorted([parse_time(t["entry_time"]) for t in trades])
    if len(times) >= 2:
        span_days = max((times[-1] - times[0]).total_seconds() / 86400, 1)
        trades_per_year = n_trades / span_days * 365
    else:
        trades_per_year = n_trades  # fallback

    final_capitals = []
    max_drawdowns = []
    annual_returns = []

    for _ in range(n_sims):
        capital = start_capital
        peak = capital
        max_dd = 0.0

        # Resample n_trades with replacement
        for _ in range(n_trades):
            base_pnl = random.choice(pnl_list)

            # Add slippage: uniform(-0.5%, +0.1%)
            slippage = random.uniform(-0.5, 0.1)

            # Add fee drag: uniform(-0.15%, -0.05%)
            fee = random.uniform(-0.15, -0.05)

            effective_pnl = base_pnl + slippage + fee

            # Position sizing: 5% of capital
            position_size = capital * position_pct
            pnl_dollar = position_size * (effective_pnl / 100.0)
            capital += pnl_dollar

            # Track drawdown
            if capital > peak:
                peak = capital
            dd = (peak - capital) / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

            # Bankruptcy check
            if capital <= 0:
                capital = 0
                max_dd = 100
                break

        final_capitals.append(capital)
        max_drawdowns.append(max_dd)

        # Annualized return
        if capital > 0 and start_capital > 0:
            total_return = capital / start_capital
            # Scale to annual: if we simulated n_trades, and trades_per_year gives us the annual scale
            ann_factor = trades_per_year / n_trades if n_trades > 0 else 1
            if ann_factor > 0 and total_return > 0:
                ann_return = (total_return ** ann_factor - 1) * 100
            else:
                ann_return = -100
        else:
            ann_return = -100
        annual_returns.append(ann_return)

    # Sort for percentiles
    final_capitals.sort()
    max_drawdowns.sort()
    annual_returns.sort()

    def percentile(lst, p):
        idx = int(len(lst) * p / 100)
        idx = max(0, min(idx, len(lst) - 1))
        return lst[idx]

    prob_ruin = sum(1 for c in final_capitals if c < 500) / n_sims * 100

    return {
        "n_trades_source": n_trades,
        "n_simulations": n_sims,
        "median_final": round(percentile(final_capitals, 50), 2),
        "p5_final": round(percentile(final_capitals, 5), 2),
        "p95_final": round(percentile(final_capitals, 95), 2),
        "mean_final": round(sum(final_capitals) / len(final_capitals), 2),
        "p95_max_drawdown_pct": round(percentile(max_drawdowns, 95), 2),
        "median_max_drawdown_pct": round(percentile(max_drawdowns, 50), 2),
        "prob_ruin_pct": round(prob_ruin, 2),
        "annual_return_ci_95": [
            round(percentile(annual_returns, 2.5), 2),
            round(percentile(annual_returns, 97.5), 2),
        ],
    }


def print_monte_carlo_report(results):
    """Print formatted Monte Carlo comparison table."""
    print("\n" + "=" * 80)
    print("PART 2: MONTE CARLO STRESS TEST (5000 simulations)")
    print("=" * 80)
    print(f"\nParameters: $1000 start | 5% position sizing | slippage U(-0.5%,+0.1%) | fees U(-0.05%,-0.15%)")
    print(f"Bootstrap: resample trades WITH replacement, {results[list(results.keys())[0]]['n_simulations']} iterations\n")

    # Header
    header = f"{'Portfolio':<42s} {'Trades':>6s} {'Median$':>9s} {'P5$':>9s} {'P95$':>9s} {'P95 DD%':>8s} {'Ruin%':>6s} {'Annual CI 95%':>20s}"
    print(header)
    print("-" * len(header))

    for name, r in results.items():
        ci = r["annual_return_ci_95"]
        ci_str = f"[{ci[0]:+.1f}%, {ci[1]:+.1f}%]"
        print(f"  {name:<40s} {r['n_trades_source']:>6d} {r['median_final']:>9.2f} "
              f"{r['p5_final']:>9.2f} {r['p95_final']:>9.2f} {r['p95_max_drawdown_pct']:>7.2f}% "
              f"{r['prob_ruin_pct']:>5.2f}% {ci_str:>20s}")

    # Analysis
    print("\n--- ANALYSIS ---")

    best_median = max(results.items(), key=lambda x: x[1]["median_final"])
    best_worst = max(results.items(), key=lambda x: x[1]["p5_final"])
    lowest_dd = min(results.items(), key=lambda x: x[1]["p95_max_drawdown_pct"])
    lowest_ruin = min(results.items(), key=lambda x: x[1]["prob_ruin_pct"])

    print(f"  Best median outcome:    {best_median[0]} (${best_median[1]['median_final']:.2f})")
    print(f"  Best worst-case (P5):   {best_worst[0]} (${best_worst[1]['p5_final']:.2f})")
    print(f"  Lowest max drawdown:    {lowest_dd[0]} ({lowest_dd[1]['p95_max_drawdown_pct']:.2f}%)")
    print(f"  Lowest ruin probability: {lowest_ruin[0]} ({lowest_ruin[1]['prob_ruin_pct']:.2f}%)")

    # Risk-adjusted ranking
    print("\n--- RISK-ADJUSTED RANKING (Median / P95-DD) ---")
    rankings = []
    for name, r in results.items():
        dd = r["p95_max_drawdown_pct"]
        if dd > 0:
            risk_adj = (r["median_final"] - 1000) / dd
        else:
            risk_adj = r["median_final"] - 1000
        rankings.append((name, risk_adj, r))

    rankings.sort(key=lambda x: -x[1])
    for rank, (name, score, r) in enumerate(rankings, 1):
        print(f"  #{rank}: {name:<40s} score={score:>7.2f} "
              f"(${r['median_final']:.0f} median, {r['p95_max_drawdown_pct']:.1f}% DD)")


def main():
    print("Loading Battleground data...")
    closed, active = load_data()
    print(f"  Closed trades: {len(closed)}")
    print(f"  Active picks:  {len(active)}")

    # =========================================================================
    # PART 1: Correlation Analysis
    # =========================================================================
    events = build_signal_events(closed, active)
    pairs, strats, bucket_map = compute_correlation_matrix(events)
    print_correlation_report(pairs, strats, bucket_map)

    # =========================================================================
    # PART 2: Monte Carlo Stress Test
    # =========================================================================
    # Check if whale RSI should be in full battleground
    all_strats_in_data = set(t["strategy"] for t in closed)
    full_bg = PORTFOLIOS["C: Full Battleground (all)"]
    # Add whale RSI if present and not already included
    if "crypto_rsi_whaleconfirmed_v1" in all_strats_in_data and "crypto_rsi_whaleconfirmed_v1" not in full_bg:
        full_bg.append("crypto_rsi_whaleconfirmed_v1")

    mc_results = {}
    for name, strat_list in PORTFOLIOS.items():
        trades = get_portfolio_trades(closed, strat_list)
        print(f"\nRunning Monte Carlo for {name} ({len(trades)} trades)...")
        mc_results[name] = run_monte_carlo(trades)

    print_monte_carlo_report(mc_results)

    # Save results
    output = {
        "correlation_analysis": {
            "pairs": pairs,
            "strategy_counts": {
                KELTNER_STRATEGIES[s]: {
                    "windows": len(bucket_map[s]),
                    "signals": sum(len(v) for v in bucket_map[s].values()),
                }
                for s in strats
            },
        },
        "monte_carlo_results": mc_results,
        "parameters": {
            "n_simulations": 5000,
            "start_capital": 1000,
            "position_pct": 0.05,
            "slippage_range": [-0.5, 0.1],
            "fee_range": [-0.15, -0.05],
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    }

    output_path = os.path.join(DATA_DIR, "monte_carlo_results.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
