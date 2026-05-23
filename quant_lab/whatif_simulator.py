"""
What-If Simulation Engine — Monte Carlo simulator using historic P&L distributions.

Answers: "If I invested $X using strategy Y, what would happen?"

Adapted from Mercury/Inception Labs framework for our JSON/SQLite infrastructure.

Usage:
    python quant_lab/whatif_simulator.py                              # Default: low budget, all strategies
    python quant_lab/whatif_simulator.py --budget medium --source top7_edge
    python quant_lab/whatif_simulator.py --budget high --source top3 --alloc kelly
    python quant_lab/whatif_simulator.py --budget extreme --source single --strategy autocorrelation_exploiter
"""
import json
import math
import random
import sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "quant_lab"))
from kpi_engine import (
    load_closed_picks, compute_all_kpis, win_rate, expectancy,
    avg_win, avg_loss, kelly_fraction, sharpe_ratio, max_drawdown,
    payoff_ratio, profit_factor, compute_edge_verdict
)

# ─────────────────────────────────────────────────────────────────
# Budget tiers
# ─────────────────────────────────────────────────────────────────

BUDGET_MAP = {
    "low": 200,        # $200 per pick
    "medium": 500,     # $500 per pick
    "high": 1000,      # $1,000 per pick
    "veryhigh": 2000,  # $2,000 per pick
    "extreme": 5000,   # $5,000 per pick
}

# ─────────────────────────────────────────────────────────────────
# TP/SL multipliers for alternate exit testing
# ─────────────────────────────────────────────────────────────────

TP_SL_TIERS = {
    "actual": 1.0,    # Use actual historic P&L
    "1R": 1.0,
    "1.5R": 1.5,
    "2R": 2.0,
    "3R": 3.0,
}


def load_pnl_distributions():
    """Load all closed trades and group PnL by strategy."""
    closed = load_closed_picks()
    by_strategy = defaultdict(list)
    for trade in closed:
        strat = trade.get("strategy", "unknown")
        pnl = trade.get("pnl_pct", 0)
        by_strategy[strat].append(pnl)
    return by_strategy


def select_strategies(source, kpis, strategy_filter=None):
    """Select strategies based on source type."""
    if source == "all":
        return [k for k in kpis if k["expectancy_pct"] != 0]

    if source == "top3":
        ranked = sorted(kpis, key=lambda x: x["expectancy_pct"], reverse=True)
        return ranked[:3]

    if source == "top7_edge":
        edge = [k for k in kpis if compute_edge_verdict(k) in ("EDGE", "EDGE_UNCONFIRMED")]
        return sorted(edge, key=lambda x: x["expectancy_pct"], reverse=True)[:7]

    if source == "positive_kelly":
        return [k for k in kpis if k["kelly_fraction"] > 0]

    if source == "long_only":
        return [k for k in kpis if (k.get("long_expectancy") or 0) > 0]

    if source == "asymmetric":
        return [k for k in kpis if compute_edge_verdict(k) == "ASYMMETRIC"]

    if source == "single" and strategy_filter:
        return [k for k in kpis if k["entity_id"] == strategy_filter]

    # Default: top 7
    ranked = sorted(kpis, key=lambda x: x["expectancy_pct"], reverse=True)
    return ranked[:7]


def compute_weights(strategies, alloc_rule):
    """Compute allocation weights per strategy."""
    n = len(strategies)
    if n == 0:
        return []

    if alloc_rule == "equal":
        return [1.0 / n] * n

    if alloc_rule == "performance":
        exps = [max(s["expectancy_pct"], 0.0001) for s in strategies]
        total = sum(exps)
        return [e / total for e in exps]

    if alloc_rule == "kelly":
        kellys = [max(s["kelly_fraction"], 0.01) for s in strategies]
        total = sum(kellys)
        return [k / total for k in kellys]

    if alloc_rule == "risk_parity":
        # Inverse of max drawdown
        inv_dd = [1.0 / max(s["max_drawdown"], 0.01) for s in strategies]
        total = sum(inv_dd)
        return [i / total for i in inv_dd]

    # Default: equal
    return [1.0 / n] * n


def monte_carlo_simulation(
    pnl_distributions,
    strategies,
    weights,
    per_pick_capital,
    n_simulations=5000,
    tp_multiplier=1.0,
    trades_per_sim=10
):
    """
    Run Monte Carlo simulation.

    For each simulation:
    1. For each strategy, sample `trades_per_sim` trades from its historic P&L distribution
    2. Apply position sizing based on weights
    3. Compute cumulative P&L
    """
    results = []

    for sim_idx in range(n_simulations):
        total_pnl = 0.0
        equity_curve = [0.0]

        for i, strat in enumerate(strategies):
            strat_name = strat["entity_id"]
            dist = pnl_distributions.get(strat_name, [])

            if not dist:
                continue

            # Position size for this strategy
            position = per_pick_capital * weights[i] * len(strategies)

            # Sample trades
            for _ in range(trades_per_sim):
                sampled_pnl = random.choice(dist) * tp_multiplier
                dollar_pnl = position * sampled_pnl
                total_pnl += dollar_pnl
                equity_curve.append(total_pnl)

        # Compute sim-level metrics
        peak = 0.0
        max_dd = 0.0
        for val in equity_curve:
            if val > peak:
                peak = val
            dd = (peak - val) if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        results.append({
            "total_pnl": total_pnl,
            "max_drawdown": max_dd,
            "final_equity": equity_curve[-1],
            "peak_equity": max(equity_curve),
            "trough_equity": min(equity_curve),
        })

    return results


def compute_simulation_stats(results, total_capital):
    """Aggregate Monte Carlo results into summary statistics."""
    pnls = [r["total_pnl"] for r in results]
    dds = [r["max_drawdown"] for r in results]

    n = len(pnls)
    avg_pnl = sum(pnls) / n
    std_pnl = math.sqrt(sum((p - avg_pnl) ** 2 for p in pnls) / n) if n > 1 else 0

    sorted_pnls = sorted(pnls)
    median_pnl = sorted_pnls[n // 2]
    p5 = sorted_pnls[int(n * 0.05)]   # 5th percentile (worst case)
    p25 = sorted_pnls[int(n * 0.25)]
    p75 = sorted_pnls[int(n * 0.75)]
    p95 = sorted_pnls[int(n * 0.95)]  # 95th percentile (best case)

    wr = sum(1 for p in pnls if p > 0) / n
    ruin_prob = sum(1 for p in pnls if p < -total_capital * 0.5) / n  # >50% loss

    avg_dd = sum(dds) / n
    max_dd = max(dds)

    # Probability of profit over different horizons (approximation)
    prob_30d_profit = sum(1 for p in pnls if p > 0) / n
    prob_beat_gic = sum(1 for p in pnls if p > total_capital * 0.004) / n  # ~5%/yr = 0.4%/month

    return {
        "simulations": n,
        "total_capital": round(total_capital, 2),
        "avg_return_dollar": round(avg_pnl, 2),
        "avg_return_pct": round(avg_pnl / total_capital * 100, 2) if total_capital > 0 else 0,
        "median_return_dollar": round(median_pnl, 2),
        "std_return_dollar": round(std_pnl, 2),
        "win_rate_pct": round(wr * 100, 2),
        "sharpe_approx": round(avg_pnl / std_pnl, 4) if std_pnl > 0 else 0,
        "worst_case_5pct": round(p5, 2),
        "best_case_95pct": round(p95, 2),
        "percentile_25": round(p25, 2),
        "percentile_75": round(p75, 2),
        "avg_max_drawdown": round(avg_dd, 2),
        "worst_max_drawdown": round(max_dd, 2),
        "ruin_probability_pct": round(ruin_prob * 100, 2),
        "prob_profit_pct": round(prob_30d_profit * 100, 2),
        "prob_beat_gic_pct": round(prob_beat_gic * 100, 2),
    }


def run_health_check(
    budget_level="low",
    source="top7_edge",
    alloc_rule="equal",
    tp_tier="actual",
    n_simulations=5000,
    trades_per_sim=10,
    strategy_filter=None,
):
    """Run a complete what-if health check."""
    print(f"\n{'='*80}")
    print(f"WHAT-IF HEALTH CHECK SIMULATION")
    print(f"Budget: {budget_level} (${BUDGET_MAP[budget_level]}/pick) | "
          f"Source: {source} | Allocation: {alloc_rule} | TP/SL: {tp_tier}")
    print(f"Simulations: {n_simulations:,} | Trades per sim: {trades_per_sim}")
    print(f"{'='*80}")

    # Load data
    kpis = compute_all_kpis(min_trades=1)
    pnl_dists = load_pnl_distributions()

    # Select strategies
    selected = select_strategies(source, kpis, strategy_filter)
    if not selected:
        print("ERROR: No strategies selected for this source.")
        return None

    # Compute weights
    weights = compute_weights(selected, alloc_rule)

    # Capital
    per_pick = BUDGET_MAP[budget_level]
    total_capital = per_pick * len(selected)
    tp_mult = TP_SL_TIERS.get(tp_tier, 1.0)

    # Print strategy allocation
    print(f"\nStrategies selected: {len(selected)}")
    print(f"Total capital deployed: ${total_capital:,.2f}")
    print(f"\n{'Strategy':<35} {'Weight':>7} {'Alloc$':>8} {'Expect':>8} {'Kelly':>7} {'Verdict':<12}")
    print("-" * 80)
    for i, strat in enumerate(selected):
        verdict = compute_edge_verdict(strat)
        alloc = total_capital * weights[i]
        print(f"{strat['entity_id']:<35} {weights[i]:>6.1%} ${alloc:>7.0f} "
              f"{strat['expectancy_pct']:>+7.4f} {strat['kelly_fraction']:>+6.2f} {verdict:<12}")

    # Run Monte Carlo
    print(f"\nRunning {n_simulations:,} Monte Carlo simulations...")
    results = monte_carlo_simulation(
        pnl_dists, selected, weights, per_pick,
        n_simulations, tp_mult, trades_per_sim
    )

    stats = compute_simulation_stats(results, total_capital)

    # Print results
    print(f"\n{'─'*60}")
    print("SIMULATION RESULTS")
    print(f"{'─'*60}")
    print(f"  Win Rate:           {stats['win_rate_pct']:.1f}%")
    print(f"  Avg Return:         ${stats['avg_return_dollar']:>+,.2f} ({stats['avg_return_pct']:>+.2f}%)")
    print(f"  Median Return:      ${stats['median_return_dollar']:>+,.2f}")
    print(f"  Std Dev:            ${stats['std_return_dollar']:>,.2f}")
    print(f"  Sharpe (approx):    {stats['sharpe_approx']:.4f}")
    print(f"  Worst 5%:           ${stats['worst_case_5pct']:>+,.2f}")
    print(f"  Best 95%:           ${stats['best_case_95pct']:>+,.2f}")
    print(f"  Avg Max Drawdown:   ${stats['avg_max_drawdown']:>,.2f}")
    print(f"  Worst Max Drawdown: ${stats['worst_max_drawdown']:>,.2f}")
    print(f"  Ruin Probability:   {stats['ruin_probability_pct']:.2f}%")
    print(f"  Prob of Profit:     {stats['prob_profit_pct']:.1f}%")
    print(f"  Prob Beat GIC (5%): {stats['prob_beat_gic_pct']:.1f}%")

    # Compare scenarios
    print(f"\n{'─'*60}")
    print("SCENARIO COMPARISON")
    print(f"{'─'*60}")
    print(f"  {'Scenario':<40} {'Capital':>10} {'Exp Return':>12} {'Vs GIC':>8}")
    print(f"  {'-'*75}")
    gic_return = total_capital * 0.05 / 12  # monthly GIC
    print(f"  {'GIC (5% annual, 1 month)':<40} ${total_capital:>9,.0f} ${gic_return:>+11,.2f} {'baseline':>8}")
    print(f"  {'This simulation (avg)':<40} ${total_capital:>9,.0f} "
          f"${stats['avg_return_dollar']:>+11,.2f} "
          f"{'BEATS' if stats['avg_return_dollar'] > gic_return else 'LOSES':>8}")
    print(f"  {'This simulation (median)':<40} ${total_capital:>9,.0f} "
          f"${stats['median_return_dollar']:>+11,.2f} "
          f"{'BEATS' if stats['median_return_dollar'] > gic_return else 'LOSES':>8}")

    # Build report dict
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parameters": {
            "budget_level": budget_level,
            "per_pick_capital": per_pick,
            "source": source,
            "allocation_rule": alloc_rule,
            "tp_tier": tp_tier,
            "n_simulations": n_simulations,
            "trades_per_sim": trades_per_sim,
        },
        "strategies_selected": [
            {
                "name": s["entity_id"],
                "weight": round(weights[i], 4),
                "allocation_dollar": round(total_capital * weights[i], 2),
                "expectancy": s["expectancy_pct"],
                "kelly": s["kelly_fraction"],
                "verdict": compute_edge_verdict(s),
            }
            for i, s in enumerate(selected)
        ],
        "simulation_results": stats,
        "gic_comparison": {
            "gic_monthly_return": round(gic_return, 2),
            "beats_gic_avg": stats["avg_return_dollar"] > gic_return,
            "beats_gic_median": stats["median_return_dollar"] > gic_return,
        }
    }

    return report


def run_all_scenarios():
    """Run multiple scenarios for comparison."""
    scenarios = [
        {"budget_level": "low", "source": "all", "alloc_rule": "equal", "label": "$200/pick × all strategies (equal weight)"},
        {"budget_level": "low", "source": "top7_edge", "alloc_rule": "equal", "label": "$200/pick × top 7 edge (equal weight)"},
        {"budget_level": "low", "source": "top3", "alloc_rule": "equal", "label": "$200/pick × top 3 (equal weight)"},
        {"budget_level": "medium", "source": "top3", "alloc_rule": "kelly", "label": "$500/pick × top 3 (Kelly weighted)"},
        {"budget_level": "high", "source": "top3", "alloc_rule": "performance", "label": "$1000/pick × top 3 (performance weighted)"},
        {"budget_level": "low", "source": "positive_kelly", "alloc_rule": "kelly", "label": "$200/pick × positive Kelly only"},
    ]

    print("\n" + "=" * 100)
    print("MULTI-SCENARIO COMPARISON")
    print("=" * 100)

    results = []
    for sc in scenarios:
        report = run_health_check(
            budget_level=sc["budget_level"],
            source=sc["source"],
            alloc_rule=sc["alloc_rule"],
            n_simulations=2000,  # Fewer sims for speed
            trades_per_sim=10,
        )
        if report:
            results.append({"label": sc["label"], "report": report})

    # Summary table
    print("\n\n" + "=" * 120)
    print("FINAL SCENARIO COMPARISON TABLE")
    print("=" * 120)
    print(f"  {'Scenario':<55} {'Capital':>8} {'AvgRet$':>9} {'AvgRet%':>8} "
          f"{'WR%':>6} {'Sharpe':>7} {'Ruin%':>6} {'BeatGIC':>8}")
    print(f"  {'-'*115}")

    for r in results:
        s = r["report"]["simulation_results"]
        cap = r["report"]["parameters"]["per_pick_capital"] * len(r["report"]["strategies_selected"])
        beat = "YES" if r["report"]["gic_comparison"]["beats_gic_avg"] else "NO"
        print(f"  {r['label']:<55} ${cap:>7,.0f} ${s['avg_return_dollar']:>+8,.2f} "
              f"{s['avg_return_pct']:>+7.2f}% {s['win_rate_pct']:>5.1f}% "
              f"{s['sharpe_approx']:>7.4f} {s['ruin_probability_pct']:>5.2f}% {beat:>8}")


# ─────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="What-If Simulation Engine")
    parser.add_argument("--budget", choices=BUDGET_MAP.keys(), default="low")
    parser.add_argument("--source", default="top7_edge",
                        choices=["all", "top3", "top7_edge", "positive_kelly",
                                 "long_only", "asymmetric", "single"])
    parser.add_argument("--alloc", default="equal",
                        choices=["equal", "performance", "kelly", "risk_parity"])
    parser.add_argument("--tp", default="actual", choices=TP_SL_TIERS.keys())
    parser.add_argument("--sims", type=int, default=5000)
    parser.add_argument("--trades", type=int, default=10)
    parser.add_argument("--strategy", type=str, help="For --source single")
    parser.add_argument("--compare-all", action="store_true", help="Run all scenarios")
    parser.add_argument("--save", type=str, help="Save report to JSON file")
    args = parser.parse_args()

    if args.compare_all:
        run_all_scenarios()
    else:
        report = run_health_check(
            budget_level=args.budget,
            source=args.source,
            alloc_rule=args.alloc,
            tp_tier=args.tp,
            n_simulations=args.sims,
            trades_per_sim=args.trades,
            strategy_filter=args.strategy,
        )
        if report and args.save:
            with open(args.save, "w") as f:
                json.dump(report, f, indent=2)
            print(f"\nReport saved to {args.save}")
