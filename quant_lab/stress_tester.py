"""
Stress Tester — Scenario Analysis, Ruin Probability, and Risk Controls.

Implements Phase 3-5 deliverables from the turnaround research roadmap:
- Scenario-based stress tests (crypto crash, regulatory ban, liquidity freeze)
- Monte Carlo ruin probability estimation
- Calmar, Information Ratio, Omega, Ulcer Index computation
- Automated risk alerts (Sharpe < 0.8, DD > 25%)
- Walk-forward validation framework

Usage:
    python quant_lab/stress_tester.py               # Full stress test report
    python quant_lab/stress_tester.py --scenarios    # Scenario analysis only
    python quant_lab/stress_tester.py --ruin         # Ruin probability only
    python quant_lab/stress_tester.py --alerts       # Risk alerts only
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
    load_closed_picks, compute_all_kpis, compute_edge_verdict,
    win_rate, expectancy, sharpe_ratio, max_drawdown, kelly_fraction
)


# ─────────────────────────────────────────────────────────────────
# Extended Metrics (Mutual Fund Ratios)
# ─────────────────────────────────────────────────────────────────

def calmar_ratio(pnls):
    """CAGR / max_drawdown. Higher = better drawdown-adjusted return."""
    if not pnls or len(pnls) < 2:
        return 0.0
    # Approximate CAGR from cumulative return
    equity = 1.0
    for p in pnls:
        equity *= (1 + p)
    total_return = equity - 1
    mdd = max_drawdown(pnls)
    if mdd < 0.001:
        return 99.99 if total_return > 0 else 0.0
    # Annualize assuming ~1 trade/day average
    n_years = max(len(pnls) / 365, 0.01)
    cagr = (equity ** (1 / n_years)) - 1
    return round(cagr / mdd, 4)


def ulcer_index(pnls):
    """Measures depth and duration of drawdowns. Lower = better."""
    if not pnls:
        return 0.0
    equity = 1.0
    peak = 1.0
    dd_squared_sum = 0
    for p in pnls:
        equity *= (1 + p)
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak if peak > 0 else 0
        dd_squared_sum += dd ** 2
    return round(math.sqrt(dd_squared_sum / len(pnls)), 6)


def omega_ratio(pnls, threshold=0.0):
    """Omega ratio: probability-weighted gains / probability-weighted losses.

    Captures full return distribution, not just mean/variance.
    """
    if not pnls:
        return 0.0
    gains = sum(max(p - threshold, 0) for p in pnls)
    losses = sum(max(threshold - p, 0) for p in pnls)
    if losses < 0.0001:
        return 99.99 if gains > 0 else 1.0
    return round(gains / losses, 4)


def information_ratio(pnls, benchmark_return=0.0):
    """(Strategy return - benchmark return) / tracking error."""
    if len(pnls) < 2:
        return 0.0
    active = [p - benchmark_return for p in pnls]
    mean_active = sum(active) / len(active)
    var_active = sum((a - mean_active) ** 2 for a in active) / len(active)
    te = math.sqrt(var_active) if var_active > 0 else 0.0001
    return round(mean_active / te, 4)


# ─────────────────────────────────────────────────────────────────
# Scenario Stress Tests
# ─────────────────────────────────────────────────────────────────

SCENARIOS = {
    "crypto_crash_70pct": {
        "name": "70% Crypto Crash",
        "description": "BTC drops 70% (2022-style bear market)",
        "pnl_multiplier": -0.70,     # All long positions lose 70%
        "long_impact": -0.70,
        "short_impact": 0.70,        # Shorts profit
        "probability": 0.05,         # 5% annual probability
    },
    "regulatory_ban_30pct": {
        "name": "30% Regulatory Ban",
        "description": "Major jurisdiction bans crypto trading",
        "pnl_multiplier": -0.30,
        "long_impact": -0.30,
        "short_impact": -0.10,       # Even shorts impacted by chaos
        "probability": 0.10,
    },
    "liquidity_freeze": {
        "name": "Liquidity Freeze",
        "description": "Exchange halt / liquidity crisis (FTX-style)",
        "pnl_multiplier": -0.50,
        "long_impact": -0.50,
        "short_impact": -0.30,
        "probability": 0.03,
    },
    "flash_crash_20pct": {
        "name": "20% Flash Crash",
        "description": "Sudden 20% drop, recovery within 24h",
        "pnl_multiplier": -0.20,
        "long_impact": -0.20,
        "short_impact": 0.15,
        "probability": 0.15,
    },
    "bull_run_100pct": {
        "name": "100% Bull Run",
        "description": "BTC doubles in 30 days (halving cycle)",
        "pnl_multiplier": 1.00,
        "long_impact": 1.00,
        "short_impact": -0.50,
        "probability": 0.08,
    },
    "stablecoin_depeg": {
        "name": "Stablecoin De-peg",
        "description": "USDT/USDC loses peg (UST-style event)",
        "pnl_multiplier": -0.40,
        "long_impact": -0.40,
        "short_impact": -0.20,
        "probability": 0.02,
    },
}


def run_scenario_analysis(budget):
    """Run all stress scenarios against current portfolio."""
    kpis = compute_all_kpis(min_trades=2)
    edge_strategies = [k for k in kpis if k["expectancy_pct"] > 0]

    if not edge_strategies:
        return {"error": "No edge strategies to stress test"}

    # Assume equal allocation across edge strategies
    n = len(edge_strategies)
    alloc_per = budget / n if n > 0 else 0

    results = {}
    for scenario_id, scenario in SCENARIOS.items():
        total_impact = 0
        strategy_impacts = []

        for kpi in edge_strategies:
            # Estimate direction bias from win pattern
            wr = kpi["win_rate"]
            # Assume mostly long if WR > 0.5 on positive-expectancy
            long_bias = 0.7  # most crypto strategies are long-biased

            impact = (long_bias * scenario["long_impact"] +
                      (1 - long_bias) * scenario["short_impact"]) * alloc_per

            strategy_impacts.append({
                "strategy": kpi["entity_id"],
                "allocation": round(alloc_per, 2),
                "impact_usd": round(impact, 2),
                "impact_pct": round(impact / alloc_per * 100, 2) if alloc_per > 0 else 0,
            })
            total_impact += impact

        results[scenario_id] = {
            "scenario": scenario["name"],
            "description": scenario["description"],
            "probability": scenario["probability"],
            "total_portfolio_impact_usd": round(total_impact, 2),
            "total_portfolio_impact_pct": round(total_impact / budget * 100, 2),
            "recovery_capital_needed": round(abs(total_impact), 2) if total_impact < 0 else 0,
            "worst_hit_strategies": sorted(strategy_impacts,
                                            key=lambda x: x["impact_usd"])[:3],
            "expected_loss": round(total_impact * scenario["probability"], 2),
        }

    return results


# ─────────────────────────────────────────────────────────────────
# Monte Carlo Ruin Probability
# ─────────────────────────────────────────────────────────────────

def monte_carlo_ruin_probability(budget, n_simulations=5000, n_trades=100, ruin_threshold=0.5):
    """Estimate probability of losing > ruin_threshold of capital.

    Samples from actual trade PnL distribution.
    """
    closed = load_closed_picks()
    if not closed:
        return {"error": "No closed picks for simulation"}

    pnls = [t.get("pnl_pct", 0) for t in closed]
    if not pnls:
        return {"error": "No PnL data"}

    random.seed(42)
    ruin_count = 0
    final_equities = []
    max_dds = []

    for _ in range(n_simulations):
        equity = budget
        peak = budget
        max_dd = 0

        for _ in range(n_trades):
            pnl = random.choice(pnls)
            equity *= (1 + pnl)
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

            # Check ruin
            if equity <= budget * (1 - ruin_threshold):
                ruin_count += 1
                break

        final_equities.append(equity)
        max_dds.append(max_dd)

    final_equities.sort()
    ruin_prob = ruin_count / n_simulations

    return {
        "budget": budget,
        "n_simulations": n_simulations,
        "n_trades_per_sim": n_trades,
        "ruin_threshold": ruin_threshold,
        "ruin_probability": round(ruin_prob, 4),
        "ruin_probability_pct": round(ruin_prob * 100, 2),
        "median_final_equity": round(final_equities[n_simulations // 2], 2),
        "mean_final_equity": round(sum(final_equities) / n_simulations, 2),
        "p5_equity": round(final_equities[int(n_simulations * 0.05)], 2),
        "p25_equity": round(final_equities[int(n_simulations * 0.25)], 2),
        "p75_equity": round(final_equities[int(n_simulations * 0.75)], 2),
        "p95_equity": round(final_equities[int(n_simulations * 0.95)], 2),
        "avg_max_drawdown": round(sum(max_dds) / n_simulations, 4),
        "verdict": "SAFE" if ruin_prob < 0.05 else
                   "CAUTION" if ruin_prob < 0.15 else "DANGER",
    }


# ─────────────────────────────────────────────────────────────────
# Risk Alerts
# ─────────────────────────────────────────────────────────────────

ALERT_THRESHOLDS = {
    "sharpe_min": 0.8,
    "max_dd_max": 0.25,
    "kelly_min": 0.0,
    "profit_factor_min": 1.0,
    "expectancy_min": 0.0,
    "ruin_prob_max": 0.05,
}


def check_risk_alerts():
    """Run automated risk alert checks across all strategies."""
    kpis = compute_all_kpis(min_trades=3)
    if not kpis:
        return []

    alerts = []
    for kpi in kpis:
        strat = kpi["entity_id"]
        strat_alerts = []

        if kpi["sharpe"] < ALERT_THRESHOLDS["sharpe_min"] and kpi["expectancy_pct"] > 0:
            strat_alerts.append({
                "level": "WARNING",
                "metric": "sharpe",
                "value": kpi["sharpe"],
                "threshold": ALERT_THRESHOLDS["sharpe_min"],
                "message": f"Sharpe {kpi['sharpe']:.2f} < {ALERT_THRESHOLDS['sharpe_min']} — edge may not be risk-adjusted",
            })

        if kpi["max_drawdown"] > ALERT_THRESHOLDS["max_dd_max"]:
            strat_alerts.append({
                "level": "CRITICAL",
                "metric": "max_drawdown",
                "value": kpi["max_drawdown"],
                "threshold": ALERT_THRESHOLDS["max_dd_max"],
                "message": f"Max DD {kpi['max_drawdown']:.1%} > {ALERT_THRESHOLDS['max_dd_max']:.0%} — capital at risk",
            })

        if kpi["kelly_fraction"] <= ALERT_THRESHOLDS["kelly_min"] and kpi["trade_count"] >= 5:
            strat_alerts.append({
                "level": "CRITICAL",
                "metric": "kelly",
                "value": kpi["kelly_fraction"],
                "threshold": ALERT_THRESHOLDS["kelly_min"],
                "message": f"Kelly {kpi['kelly_fraction']:+.3f} ≤ 0 — no mathematical edge for bet sizing",
            })

        if kpi["expectancy_pct"] < ALERT_THRESHOLDS["expectancy_min"] and kpi["trade_count"] >= 5:
            strat_alerts.append({
                "level": "CRITICAL",
                "metric": "expectancy",
                "value": kpi["expectancy_pct"],
                "threshold": ALERT_THRESHOLDS["expectancy_min"],
                "message": f"Negative expectancy {kpi['expectancy_pct']:+.4f} — stop trading immediately",
            })

        if strat_alerts:
            alerts.append({
                "strategy": strat,
                "trade_count": kpi["trade_count"],
                "verdict": compute_edge_verdict(kpi),
                "alerts": strat_alerts,
            })

    return sorted(alerts, key=lambda x: max(1 if a["level"] == "CRITICAL" else 0 for a in x["alerts"]), reverse=True)


# ─────────────────────────────────────────────────────────────────
# Walk-Forward Validation Framework
# ─────────────────────────────────────────────────────────────────

def walk_forward_analysis(n_folds=3):
    """Simple walk-forward analysis: split trades chronologically,
    check if edge persists across time periods."""
    closed = load_closed_picks()
    if not closed:
        return []

    # Sort by date
    dated = [t for t in closed if t.get("entry_date")]
    dated.sort(key=lambda t: t["entry_date"])

    if len(dated) < n_folds * 5:
        return [{"error": f"Not enough dated trades ({len(dated)}) for {n_folds}-fold validation"}]

    fold_size = len(dated) // n_folds
    folds = []

    for i in range(n_folds):
        start = i * fold_size
        end = start + fold_size if i < n_folds - 1 else len(dated)
        fold_trades = dated[start:end]

        # Group by strategy
        by_strat = defaultdict(list)
        for t in fold_trades:
            by_strat[t.get("strategy", "")].append(t.get("pnl_pct", 0))

        fold_results = {
            "fold": i + 1,
            "period": f"{fold_trades[0]['entry_date'][:10]} → {fold_trades[-1].get('exit_date', fold_trades[-1]['entry_date'])[:10]}",
            "n_trades": len(fold_trades),
            "strategies": {},
        }

        for strat, pnls in by_strat.items():
            if len(pnls) >= 2:
                fold_results["strategies"][strat] = {
                    "trades": len(pnls),
                    "win_rate": round(win_rate(pnls), 4),
                    "expectancy": round(expectancy(pnls), 6),
                    "sharpe": round(sharpe_ratio(pnls), 4),
                    "kelly": round(kelly_fraction(pnls), 4),
                }

        folds.append(fold_results)

    # Check consistency: strategies that are positive in ALL folds
    all_strats = set()
    for f in folds:
        all_strats.update(f["strategies"].keys())

    consistency = {}
    for strat in all_strats:
        fold_exp = []
        for f in folds:
            if strat in f["strategies"]:
                fold_exp.append(f["strategies"][strat]["expectancy"])
        if fold_exp:
            consistency[strat] = {
                "folds_present": len(fold_exp),
                "folds_positive": sum(1 for e in fold_exp if e > 0),
                "all_positive": all(e > 0 for e in fold_exp),
                "avg_expectancy": round(sum(fold_exp) / len(fold_exp), 6),
                "consistency_score": round(sum(1 for e in fold_exp if e > 0) / len(fold_exp), 4),
            }

    return {
        "n_folds": n_folds,
        "folds": folds,
        "consistency": consistency,
        "consistently_profitable": [s for s, c in consistency.items() if c["all_positive"]],
        "inconsistent": [s for s, c in consistency.items() if not c["all_positive"] and c["folds_positive"] > 0],
    }


# ─────────────────────────────────────────────────────────────────
# Main Report
# ─────────────────────────────────────────────────────────────────

def print_full_report():
    """Generate complete stress test report."""
    print("\n" + "=" * 100)
    print("STRESS TESTING & RISK ANALYSIS REPORT")
    print(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 100)

    # Extended metrics for all strategies
    print(f"\n{'─'*80}")
    print("EXTENDED METRICS (Mutual Fund Ratios)")
    print(f"{'─'*80}")
    kpis = compute_all_kpis(min_trades=3)
    closed = load_closed_picks()
    by_strat = defaultdict(list)
    for t in closed:
        by_strat[t.get("strategy", "")].append(t.get("pnl_pct", 0))

    print(f"\n{'Strategy':<30} {'Calmar':>7} {'Omega':>7} {'Ulcer':>7} {'InfoR':>7} {'Verdict':<12}")
    print("-" * 80)
    for kpi in sorted(kpis, key=lambda x: x["expectancy_pct"], reverse=True)[:15]:
        strat = kpi["entity_id"]
        pnls = by_strat.get(strat, [])
        if len(pnls) < 3:
            continue
        cal = calmar_ratio(pnls)
        om = omega_ratio(pnls)
        ul = ulcer_index(pnls)
        ir = information_ratio(pnls)
        verdict = compute_edge_verdict(kpi)
        print(f"{strat:<30} {cal:>7.2f} {om:>7.2f} {ul:>7.4f} {ir:>7.2f} {verdict:<12}")

    # Scenario analysis
    for budget in [500, 1000, 5000]:
        print(f"\n{'─'*80}")
        print(f"SCENARIO STRESS TEST — ${budget:,} Portfolio")
        print(f"{'─'*80}")
        scenarios = run_scenario_analysis(budget)
        if "error" in scenarios:
            print(f"  {scenarios['error']}")
            continue
        for sid, s in scenarios.items():
            emoji = "🔴" if s["total_portfolio_impact_pct"] < -30 else \
                    "🟡" if s["total_portfolio_impact_pct"] < -10 else "🟢"
            print(f"  {emoji} {s['scenario']:<30} Impact: {s['total_portfolio_impact_pct']:>+6.1f}% "
                  f"(${s['total_portfolio_impact_usd']:>+8.2f}) | "
                  f"Prob: {s['probability']:.0%} | E[Loss]: ${s['expected_loss']:>+.2f}")

    # Ruin probability
    print(f"\n{'─'*80}")
    print("MONTE CARLO RUIN PROBABILITY")
    print(f"{'─'*80}")
    for budget in [200, 500, 1000, 2000, 5000]:
        ruin = monte_carlo_ruin_probability(budget, n_simulations=3000)
        if "error" in ruin:
            print(f"  ${budget}: {ruin['error']}")
            continue
        print(f"  ${budget:>5,}: Ruin prob = {ruin['ruin_probability_pct']:>5.1f}% | "
              f"Median equity: ${ruin['median_final_equity']:>8,.2f} | "
              f"P5: ${ruin['p5_equity']:>8,.2f} | P95: ${ruin['p95_equity']:>8,.2f} | "
              f"[{ruin['verdict']}]")

    # Risk alerts
    print(f"\n{'─'*80}")
    print("AUTOMATED RISK ALERTS")
    print(f"{'─'*80}")
    alerts = check_risk_alerts()
    if alerts:
        for a in alerts:
            print(f"\n  {a['strategy']} ({a['trade_count']} trades) [{a['verdict']}]")
            for alert in a["alerts"]:
                icon = "🚨" if alert["level"] == "CRITICAL" else "⚠️"
                print(f"    {icon} {alert['message']}")
    else:
        print("  No risk alerts triggered.")

    # Walk-forward validation
    print(f"\n{'─'*80}")
    print("WALK-FORWARD VALIDATION (3-fold)")
    print(f"{'─'*80}")
    wf = walk_forward_analysis(n_folds=3)
    if isinstance(wf, list):
        for item in wf:
            print(f"  {item}")
    else:
        cp = wf.get("consistently_profitable", [])
        ic = wf.get("inconsistent", [])
        print(f"  Consistently profitable across all folds: {len(cp)}")
        for s in cp[:10]:
            c = wf["consistency"].get(s, {})
            print(f"    ✓ {s:<35} avg E={c.get('avg_expectancy', 0):+.4f}")
        if ic:
            print(f"\n  Inconsistent (positive in some folds): {len(ic)}")
            for s in ic[:5]:
                c = wf["consistency"].get(s, {})
                print(f"    ~ {s:<35} {c.get('folds_positive', 0)}/{c.get('folds_present', 0)} folds positive")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Stress Tester")
    parser.add_argument("--scenarios", action="store_true")
    parser.add_argument("--ruin", action="store_true")
    parser.add_argument("--alerts", action="store_true")
    parser.add_argument("--walkforward", action="store_true")
    parser.add_argument("--budget", type=float, default=1000)
    args = parser.parse_args()

    if args.scenarios:
        results = run_scenario_analysis(args.budget)
        print(json.dumps(results, indent=2))
    elif args.ruin:
        ruin = monte_carlo_ruin_probability(args.budget)
        print(json.dumps(ruin, indent=2))
    elif args.alerts:
        alerts = check_risk_alerts()
        print(json.dumps(alerts, indent=2))
    elif args.walkforward:
        wf = walk_forward_analysis()
        print(json.dumps(wf, indent=2, default=str))
    else:
        print_full_report()
