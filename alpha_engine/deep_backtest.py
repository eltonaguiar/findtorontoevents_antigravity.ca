#!/usr/bin/env python3
"""
Deep Backtest Analysis — Alpha Engine
======================================
Computes advanced strategy profiles, Monte Carlo forward simulations,
and portfolio-level analysis for the top 5 proven strategies.

Uses ONLY stdlib: math, random, json, datetime, statistics, os, collections.
"""

import json
import math
import os
import random
import statistics
from collections import defaultdict
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

CLOSED_PICKS_PATH = os.path.join(DATA_DIR, "closed_picks.json")
STRATEGY_PERF_PATH = os.path.join(DATA_DIR, "strategy_performance.json")
THOMPSON_STATE_PATH = os.path.join(DATA_DIR, "thompson_state.json")
REPORT_PATH = os.path.join(DATA_DIR, "deep_backtest_report.json")

MIN_TRADES = 10
TOP_N = 5
SEED = 42


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)


def _parse_date(s):
    """Parse date string, return datetime or None."""
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            return datetime.fromisoformat(s) if "T" in s else datetime.strptime(s, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _safe_div(a, b, default=0.0):
    return a / b if b else default


def _percentile(data, pct):
    """Simple percentile (linear interpolation)."""
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * pct / 100.0
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] * (c - k) + s[c] * (k - f)


def _rr_bucket(rr):
    """Bucket an R:R value for histogram."""
    if rr <= -2:
        return "<=-2R"
    elif rr <= -1:
        return "-2R to -1R"
    elif rr <= 0:
        return "-1R to 0"
    elif rr <= 1:
        return "0 to 1R"
    elif rr <= 2:
        return "1R to 2R"
    elif rr <= 3:
        return "2R to 3R"
    else:
        return ">3R"


# ---------------------------------------------------------------------------
# 1. Strategy Profile
# ---------------------------------------------------------------------------

def strategy_profile(name, closed_picks):
    """Compute comprehensive profile for a single strategy."""
    picks = [p for p in closed_picks if p["strategy"] == name]
    if not picks:
        return {"error": f"No picks for {name}"}

    n = len(picks)
    pnls = [p.get("pnl_pct", 0.0) or 0.0 for p in picks]
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x <= 0]

    total_pnl = sum(pnls)
    avg_pnl = _safe_div(total_pnl, n)
    median_pnl = statistics.median(pnls) if pnls else 0.0
    max_win = max(pnls) if pnls else 0.0
    max_loss = min(pnls) if pnls else 0.0
    win_rate = _safe_div(len(wins), n)

    # Profit factor
    gross_wins = sum(wins) if wins else 0.0
    gross_losses = abs(sum(losses)) if losses else 0.0
    profit_factor = _safe_div(gross_wins, gross_losses, default=99.99)

    # Sharpe ratio (annualized, assuming 4h bars => 6 bars/day => ~2190/year)
    bars_per_year = 6 * 365
    std_ret = statistics.stdev(pnls) if len(pnls) > 1 else 0.0
    sharpe = _safe_div(avg_pnl, std_ret) * math.sqrt(bars_per_year) if std_ret > 0 else 0.0

    # Sortino (downside deviation only)
    downside = [x for x in pnls if x < 0]
    downside_dev = math.sqrt(sum(x ** 2 for x in downside) / n) if downside else 0.0
    sortino = _safe_div(avg_pnl, downside_dev) * math.sqrt(bars_per_year) if downside_dev > 0 else 0.0

    # Max drawdown (sequential equity curve)
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    equity_curve = [1.0]
    for pnl in pnls:
        equity *= (1 + pnl)
        equity_curve.append(equity)
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    # Streaks
    win_streak = 0
    loss_streak = 0
    cur_win = 0
    cur_loss = 0
    for pnl in pnls:
        if pnl > 0:
            cur_win += 1
            cur_loss = 0
        else:
            cur_loss += 1
            cur_win = 0
        win_streak = max(win_streak, cur_win)
        loss_streak = max(loss_streak, cur_loss)

    # Average holding time
    hold_days = []
    for p in picks:
        entry_d = _parse_date(p.get("entry_date"))
        exit_d = _parse_date(p.get("exit_date") or p.get("closed_at"))
        if entry_d and exit_d:
            # Remove timezone info for comparison if needed
            try:
                delta = abs((exit_d.replace(tzinfo=None) - entry_d.replace(tzinfo=None)).total_seconds()) / 86400.0
            except Exception:
                delta = p.get("hold_days", 0) or 0
            hold_days.append(delta)
        else:
            hold_days.append(p.get("hold_days", 0) or 0)
    avg_hold = _safe_div(sum(hold_days), len(hold_days)) if hold_days else 0.0

    # Symbol performance
    by_symbol = defaultdict(lambda: {"wins": 0, "losses": 0, "total_pnl": 0.0, "trades": 0})
    for p in picks:
        sym = p.get("symbol", "UNKNOWN")
        pnl = p.get("pnl_pct", 0.0) or 0.0
        by_symbol[sym]["trades"] += 1
        by_symbol[sym]["total_pnl"] += pnl
        if pnl > 0:
            by_symbol[sym]["wins"] += 1
        else:
            by_symbol[sym]["losses"] += 1

    best_symbols = sorted(by_symbol.items(), key=lambda x: -x[1]["total_pnl"])[:3]
    worst_symbols = sorted(by_symbol.items(), key=lambda x: x[1]["total_pnl"])[:3]

    # Performance by regime
    by_regime = defaultdict(lambda: {"trades": 0, "wins": 0, "total_pnl": 0.0})
    for p in picks:
        regime = p.get("regime_at_entry", "unknown") or "unknown"
        pnl = p.get("pnl_pct", 0.0) or 0.0
        by_regime[regime]["trades"] += 1
        by_regime[regime]["total_pnl"] += pnl
        if pnl > 0:
            by_regime[regime]["wins"] += 1

    # Performance by hour (if timestamp available)
    by_hour = defaultdict(lambda: {"trades": 0, "wins": 0, "total_pnl": 0.0})
    for p in picks:
        ts = _parse_date(p.get("timestamp") or p.get("created_at"))
        if ts:
            try:
                h = ts.hour
            except Exception:
                h = None
            if h is not None:
                pnl = p.get("pnl_pct", 0.0) or 0.0
                by_hour[h]["trades"] += 1
                by_hour[h]["total_pnl"] += pnl
                if pnl > 0:
                    by_hour[h]["wins"] += 1

    # R:R distribution
    rr_histogram = defaultdict(int)
    rr_values = []
    for p in picks:
        entry = p.get("entry_price", 0)
        sl = p.get("stop_loss", 0)
        exit_px = p.get("exit_price", 0)
        if entry and sl and exit_px and entry != sl:
            risk = abs(entry - sl)
            reward = exit_px - entry  # positive = profit for LONG
            if p.get("signal_type") == "SELL" or p.get("direction") == "SHORT":
                reward = entry - exit_px
            rr = reward / risk if risk > 0 else 0.0
            rr_values.append(round(rr, 2))
            rr_histogram[_rr_bucket(rr)] += 1

    # Exit reason breakdown
    exit_reasons = defaultdict(int)
    for p in picks:
        reason = p.get("exit_reason", "UNKNOWN")
        exit_reasons[reason] += 1

    return {
        "strategy": name,
        "total_trades": n,
        "win_rate": round(win_rate, 4),
        "avg_pnl_pct": round(avg_pnl, 6),
        "median_pnl_pct": round(median_pnl, 6),
        "total_pnl_pct": round(total_pnl, 6),
        "max_win_pct": round(max_win, 6),
        "max_loss_pct": round(max_loss, 6),
        "profit_factor": round(profit_factor, 3),
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "max_drawdown": round(max_dd, 6),
        "longest_win_streak": win_streak,
        "longest_loss_streak": loss_streak,
        "avg_hold_days": round(avg_hold, 2),
        "best_symbols": {s: dict(v) for s, v in best_symbols},
        "worst_symbols": {s: dict(v) for s, v in worst_symbols},
        "by_regime": {k: dict(v) for k, v in by_regime.items()},
        "by_hour_utc": {str(k): dict(v) for k, v in sorted(by_hour.items())},
        "rr_distribution": dict(rr_histogram),
        "rr_values": rr_values,
        "exit_reasons": dict(exit_reasons),
        "equity_curve": [round(e, 6) for e in equity_curve],
        "pnl_series": [round(p, 6) for p in pnls],
    }


# ---------------------------------------------------------------------------
# 2. Monte Carlo Forward Simulation
# ---------------------------------------------------------------------------

def monte_carlo_forward(profile, n_simulations=1000, n_trades=50):
    """
    Simulate n_trades future trades using the strategy's empirical
    win rate and PnL distribution.
    """
    rng = random.Random(SEED)
    pnl_series = profile.get("pnl_series", [])
    if not pnl_series:
        return {"error": "No PnL data"}

    wr = profile["win_rate"]
    wins_pool = [x for x in pnl_series if x > 0]
    losses_pool = [x for x in pnl_series if x <= 0]

    # Fallback if one pool is empty
    if not wins_pool:
        wins_pool = [profile.get("avg_pnl_pct", 0.01)]
    if not losses_pool:
        losses_pool = [profile.get("max_loss_pct", -0.01)]

    final_equities = []
    all_paths = []
    max_dds = []

    for _ in range(n_simulations):
        equity = 1.0
        peak = 1.0
        max_dd = 0.0
        path = [1.0]

        for _ in range(n_trades):
            if rng.random() < wr:
                pnl = rng.choice(wins_pool)
            else:
                pnl = rng.choice(losses_pool)
            equity *= (1 + pnl)
            path.append(equity)
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        final_equities.append(equity)
        max_dds.append(max_dd)
        all_paths.append(path)

    final_equities.sort()
    prob_profit = sum(1 for e in final_equities if e > 1.0) / n_simulations

    # Compute path percentiles at each step
    median_path = []
    p5_path = []
    p95_path = []
    for step in range(n_trades + 1):
        step_values = [all_paths[i][step] for i in range(n_simulations)]
        median_path.append(round(_percentile(step_values, 50), 6))
        p5_path.append(round(_percentile(step_values, 5), 6))
        p95_path.append(round(_percentile(step_values, 95), 6))

    return {
        "strategy": profile["strategy"],
        "n_simulations": n_simulations,
        "n_forward_trades": n_trades,
        "median_final_equity": round(_percentile(final_equities, 50), 6),
        "p5_final_equity": round(_percentile(final_equities, 5), 6),
        "p25_final_equity": round(_percentile(final_equities, 25), 6),
        "p75_final_equity": round(_percentile(final_equities, 75), 6),
        "p95_final_equity": round(_percentile(final_equities, 95), 6),
        "mean_final_equity": round(statistics.mean(final_equities), 6),
        "probability_of_profit": round(prob_profit, 4),
        "median_max_drawdown": round(_percentile(max_dds, 50), 6),
        "p95_max_drawdown": round(_percentile(max_dds, 95), 6),
        "best_case": round(max(final_equities), 6),
        "worst_case": round(min(final_equities), 6),
        "median_path": median_path,
        "p5_path": p5_path,
        "p95_path": p95_path,
    }


# ---------------------------------------------------------------------------
# 3. Portfolio Simulation
# ---------------------------------------------------------------------------

def portfolio_simulation(profiles, closed_picks, n_simulations=1000, n_trades=50):
    """
    Simulate a portfolio of the top strategies with equal allocation.
    Each simulation step: each strategy independently picks a trade,
    portfolio return = mean of individual returns (equal weight).
    """
    rng = random.Random(SEED + 1)
    n_strats = len(profiles)
    if n_strats == 0:
        return {"error": "No strategies"}

    # Build per-strategy pools
    pools = {}
    for prof in profiles:
        name = prof["strategy"]
        pnl_series = prof.get("pnl_series", [])
        wr = prof["win_rate"]
        wins_pool = [x for x in pnl_series if x > 0] or [0.01]
        losses_pool = [x for x in pnl_series if x <= 0] or [-0.01]
        pools[name] = {"wr": wr, "wins": wins_pool, "losses": losses_pool}

    portfolio_equities = []
    individual_equities = {p["strategy"]: [] for p in profiles}

    for _ in range(n_simulations):
        port_equity = 1.0
        ind_eq = {name: 1.0 for name in pools}

        for _ in range(n_trades):
            port_return = 0.0
            for name, pool in pools.items():
                if rng.random() < pool["wr"]:
                    pnl = rng.choice(pool["wins"])
                else:
                    pnl = rng.choice(pool["losses"])
                ind_eq[name] *= (1 + pnl)
                port_return += pnl / n_strats  # equal weight

            port_equity *= (1 + port_return)

        portfolio_equities.append(port_equity)
        for name in pools:
            individual_equities[name].append(ind_eq[name])

    # Portfolio stats
    port_returns_per_sim = [(e - 1.0) for e in portfolio_equities]
    port_mean = statistics.mean(port_returns_per_sim)
    port_std = statistics.stdev(port_returns_per_sim) if len(port_returns_per_sim) > 1 else 0.001
    portfolio_sharpe = _safe_div(port_mean, port_std) * math.sqrt(6 * 365)  # annualized

    # Best single-strategy Sharpe
    best_single_sharpe = max(p["sharpe_ratio"] for p in profiles)

    # Individual medians
    individual_medians = {}
    for name, eqs in individual_equities.items():
        individual_medians[name] = round(_percentile(sorted(eqs), 50), 6)

    # Correlation matrix (using final equities across simulations)
    strat_names = list(pools.keys())
    correlation_matrix = {}
    for i, s1 in enumerate(strat_names):
        for j, s2 in enumerate(strat_names):
            if i <= j:
                eq1 = individual_equities[s1]
                eq2 = individual_equities[s2]
                mean1 = statistics.mean(eq1)
                mean2 = statistics.mean(eq2)
                std1 = statistics.stdev(eq1) if len(eq1) > 1 else 0.001
                std2 = statistics.stdev(eq2) if len(eq2) > 1 else 0.001
                cov = sum((a - mean1) * (b - mean2) for a, b in zip(eq1, eq2)) / len(eq1)
                corr = _safe_div(cov, std1 * std2)
                key = f"{s1} x {s2}"
                correlation_matrix[key] = round(corr, 4)

    return {
        "n_strategies": n_strats,
        "n_simulations": n_simulations,
        "n_forward_trades": n_trades,
        "portfolio_median_equity": round(_percentile(sorted(portfolio_equities), 50), 6),
        "portfolio_p5_equity": round(_percentile(sorted(portfolio_equities), 5), 6),
        "portfolio_p95_equity": round(_percentile(sorted(portfolio_equities), 95), 6),
        "portfolio_prob_profit": round(sum(1 for e in portfolio_equities if e > 1.0) / n_simulations, 4),
        "portfolio_sharpe_annualized": round(portfolio_sharpe, 2),
        "best_single_strategy_sharpe": round(best_single_sharpe, 2),
        "diversification_benefit": round(portfolio_sharpe - best_single_sharpe, 2),
        "individual_median_equities": individual_medians,
        "correlation_matrix": correlation_matrix,
    }


# ---------------------------------------------------------------------------
# 4. Generate Full Backtest Report
# ---------------------------------------------------------------------------

def generate_backtest_report(closed_picks=None):
    """Run all analyses and write report."""
    if closed_picks is None:
        closed_picks = _load_json(CLOSED_PICKS_PATH)

    strategy_perf = _load_json(STRATEGY_PERF_PATH)
    thompson_state = _load_json(THOMPSON_STATE_PATH)

    # Identify top 5 strategies by WR with >= MIN_TRADES
    qualified = {
        k: v for k, v in strategy_perf.items()
        if v.get("closed_picks", 0) >= MIN_TRADES
    }
    ranked = sorted(qualified.items(), key=lambda x: -x[1]["win_rate"])
    top5_names = [name for name, _ in ranked[:TOP_N]]

    print(f"[Deep Backtest] {len(closed_picks)} total closed picks")
    print(f"[Deep Backtest] {len(qualified)} strategies with >= {MIN_TRADES} trades")
    print(f"[Deep Backtest] Top {TOP_N}: {top5_names}")

    # 1. Strategy profiles
    profiles = []
    for name in top5_names:
        print(f"  Profiling: {name}...")
        prof = strategy_profile(name, closed_picks)
        profiles.append(prof)

    # 2. Monte Carlo forward simulations
    mc_results = []
    for prof in profiles:
        print(f"  Monte Carlo: {prof['strategy']}...")
        mc = monte_carlo_forward(prof, n_simulations=1000, n_trades=50)
        mc_results.append(mc)

    # 3. Portfolio simulation
    print("  Portfolio simulation...")
    port_sim = portfolio_simulation(profiles, closed_picks, n_simulations=1000, n_trades=50)

    # 4. Thompson/Bayesian cross-reference
    bayesian_posteriors = {}
    for name in top5_names:
        ts = thompson_state.get(name, {})
        alpha = ts.get("alpha", 1.0)
        beta = ts.get("beta", 1.0)
        posterior_mean = alpha / (alpha + beta)
        # 95% credible interval approximation (normal approx for Beta)
        var = (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))
        ci_half = 1.96 * math.sqrt(var)
        bayesian_posteriors[name] = {
            "alpha": alpha,
            "beta": beta,
            "posterior_mean": round(posterior_mean, 4),
            "ci_95_lower": round(max(0, posterior_mean - ci_half), 4),
            "ci_95_upper": round(min(1, posterior_mean + ci_half), 4),
        }

    # Rankings
    rankings = {
        "by_win_rate": sorted(
            [(p["strategy"], p["win_rate"]) for p in profiles],
            key=lambda x: -x[1]
        ),
        "by_profit_factor": sorted(
            [(p["strategy"], p["profit_factor"]) for p in profiles],
            key=lambda x: -x[1]
        ),
        "by_sharpe": sorted(
            [(p["strategy"], p["sharpe_ratio"]) for p in profiles],
            key=lambda x: -x[1]
        ),
        "by_sortino": sorted(
            [(p["strategy"], p["sortino_ratio"]) for p in profiles],
            key=lambda x: -x[1]
        ),
        "by_max_drawdown": sorted(
            [(p["strategy"], p["max_drawdown"]) for p in profiles],
            key=lambda x: x[1]  # lower is better
        ),
        "by_mc_prob_profit": sorted(
            [(mc["strategy"], mc["probability_of_profit"]) for mc in mc_results],
            key=lambda x: -x[1]
        ),
    }

    # Allocation suggestions (risk-parity-inspired: inverse of max_drawdown)
    inv_dds = []
    for prof in profiles:
        dd = prof["max_drawdown"]
        inv_dds.append(1.0 / dd if dd > 0 else 100.0)
    total_inv = sum(inv_dds)
    allocations = {}
    for i, prof in enumerate(profiles):
        allocations[prof["strategy"]] = round(inv_dds[i] / total_inv, 4)

    # Recommendations
    recommendations = []
    for i, prof in enumerate(profiles):
        mc = mc_results[i]
        name = prof["strategy"]
        rec = {
            "strategy": name,
            "verdict": "",
            "notes": [],
        }
        # Verdicts
        if mc["probability_of_profit"] >= 0.9 and prof["profit_factor"] >= 2.0:
            rec["verdict"] = "STRONG_DEPLOY"
            rec["notes"].append("High MC profit probability + strong profit factor")
        elif mc["probability_of_profit"] >= 0.7 and prof["profit_factor"] >= 1.5:
            rec["verdict"] = "DEPLOY"
            rec["notes"].append("Good forward outlook")
        elif mc["probability_of_profit"] >= 0.5:
            rec["verdict"] = "MONITOR"
            rec["notes"].append("Marginal edge, needs more data")
        else:
            rec["verdict"] = "AVOID"
            rec["notes"].append("Negative expected value forward")

        # Additional notes
        if prof["max_drawdown"] > 0.1:
            rec["notes"].append(f"WARNING: High max drawdown ({prof['max_drawdown']:.1%})")
        if prof["total_trades"] < 20:
            rec["notes"].append(f"Limited sample size ({prof['total_trades']} trades)")
        if prof["longest_loss_streak"] >= 3:
            rec["notes"].append(f"Loss streak risk: {prof['longest_loss_streak']} consecutive losses observed")

        bp = bayesian_posteriors.get(name, {})
        if bp:
            rec["notes"].append(
                f"Bayesian posterior WR: {bp['posterior_mean']:.1%} "
                f"(95% CI: {bp['ci_95_lower']:.1%} - {bp['ci_95_upper']:.1%})"
            )

        recommendations.append(rec)

    # Build report
    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_closed_picks": len(closed_picks),
        "qualified_strategies": len(qualified),
        "top_5_strategies": top5_names,
        "strategy_profiles": {p["strategy"]: p for p in profiles},
        "monte_carlo_forward": {mc["strategy"]: mc for mc in mc_results},
        "portfolio_simulation": port_sim,
        "bayesian_posteriors": bayesian_posteriors,
        "rankings": rankings,
        "allocation_suggestions": allocations,
        "recommendations": recommendations,
        "summary": {
            "best_overall": recommendations[0]["strategy"] if recommendations else None,
            "best_verdict": recommendations[0]["verdict"] if recommendations else None,
            "portfolio_prob_profit": port_sim.get("portfolio_prob_profit"),
            "portfolio_sharpe": port_sim.get("portfolio_sharpe_annualized"),
            "diversification_benefit": port_sim.get("diversification_benefit"),
        },
    }

    _save_json(REPORT_PATH, report)
    print(f"\n[Deep Backtest] Report saved to {REPORT_PATH}")

    # Print summary
    print("\n" + "=" * 70)
    print("DEEP BACKTEST REPORT SUMMARY")
    print("=" * 70)
    for prof in profiles:
        mc = [m for m in mc_results if m["strategy"] == prof["strategy"]][0]
        bp = bayesian_posteriors.get(prof["strategy"], {})
        rec = [r for r in recommendations if r["strategy"] == prof["strategy"]][0]
        alloc = allocations.get(prof["strategy"], 0)
        print(f"\n--- {prof['strategy']} ---")
        print(f"  Trades: {prof['total_trades']}  |  WR: {prof['win_rate']:.1%}  |  "
              f"Avg PnL: {prof['avg_pnl_pct']:.4%}  |  PF: {prof['profit_factor']:.2f}")
        print(f"  Sharpe: {prof['sharpe_ratio']:.1f}  |  Sortino: {prof['sortino_ratio']:.1f}  |  "
              f"Max DD: {prof['max_drawdown']:.2%}")
        print(f"  Win Streak: {prof['longest_win_streak']}  |  Loss Streak: {prof['longest_loss_streak']}  |  "
              f"Avg Hold: {prof['avg_hold_days']:.1f}d")
        print(f"  MC 50-trade: Median={mc['median_final_equity']:.4f}  "
              f"P5={mc['p5_final_equity']:.4f}  P95={mc['p95_final_equity']:.4f}  "
              f"P(profit)={mc['probability_of_profit']:.1%}")
        print(f"  Bayesian: mean={bp.get('posterior_mean', 'N/A')}  "
              f"CI=({bp.get('ci_95_lower', 'N/A')}, {bp.get('ci_95_upper', 'N/A')})")
        print(f"  Verdict: {rec['verdict']}  |  Suggested Alloc: {alloc:.1%}")

    print(f"\n--- PORTFOLIO (equal weight, 5 strategies) ---")
    print(f"  Median Equity: {port_sim['portfolio_median_equity']:.4f}  |  "
          f"P(profit): {port_sim['portfolio_prob_profit']:.1%}")
    print(f"  Portfolio Sharpe: {port_sim['portfolio_sharpe_annualized']:.1f}  |  "
          f"Best Single Sharpe: {port_sim['best_single_strategy_sharpe']:.1f}")
    print(f"  Diversification Benefit: {port_sim['diversification_benefit']:+.1f} Sharpe points")
    print("=" * 70)

    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    generate_backtest_report()
