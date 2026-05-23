"""
Regime Analyzer — Correlation, Regime Sensitivity, and Diversification Scoring.

Implements Phase 2 deliverables from the turnaround research roadmap:
- Pearson correlation matrix across strategies
- Regime classification (trending/ranging, high-vol/low-vol)
- Diversification score (penalize correlated bundles)
- Strategy pair anti-correlation detection

Usage:
    python quant_lab/regime_analyzer.py               # Full analysis
    python quant_lab/regime_analyzer.py --correlation  # Correlation matrix only
    python quant_lab/regime_analyzer.py --regimes      # Regime breakdown only
"""
import json
import math
import sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "quant_lab"))
from kpi_engine import load_closed_picks, compute_all_kpis, compute_edge_verdict


# ─────────────────────────────────────────────────────────────────
# Regime Classification
# ─────────────────────────────────────────────────────────────────

REGIME_THRESHOLDS = {
    "volatility": {
        "high": 0.05,   # daily return stdev > 5%
        "low": 0.02,    # daily return stdev < 2%
    },
    "trend": {
        "strong": 0.6,  # abs(mean/stdev) > 0.6 → trending
        "weak": 0.2,    # abs(mean/stdev) < 0.2 → ranging
    }
}


def classify_regime(pnls):
    """Classify a set of returns as trending/ranging and high/low volatility."""
    if len(pnls) < 3:
        return {"volatility": "unknown", "trend": "unknown"}

    mean_ret = sum(pnls) / len(pnls)
    var = sum((p - mean_ret) ** 2 for p in pnls) / len(pnls)
    stdev = math.sqrt(var) if var > 0 else 0.0001

    # Volatility regime
    if stdev > REGIME_THRESHOLDS["volatility"]["high"]:
        vol_regime = "high_vol"
    elif stdev < REGIME_THRESHOLDS["volatility"]["low"]:
        vol_regime = "low_vol"
    else:
        vol_regime = "normal_vol"

    # Trend regime (signal-to-noise)
    snr = abs(mean_ret) / stdev if stdev > 0 else 0
    if snr > REGIME_THRESHOLDS["trend"]["strong"]:
        trend_regime = "trending"
    elif snr < REGIME_THRESHOLDS["trend"]["weak"]:
        trend_regime = "ranging"
    else:
        trend_regime = "mixed"

    return {
        "volatility": vol_regime,
        "trend": trend_regime,
        "stdev": round(stdev, 6),
        "mean_return": round(mean_ret, 6),
        "signal_noise_ratio": round(snr, 4),
    }


def analyze_regime_sensitivity(min_trades=3):
    """Analyze each strategy's performance across different market regimes.

    Splits each strategy's trades into volatility and trend buckets
    and computes expectancy per regime.
    """
    closed = load_closed_picks()
    if not closed:
        return []

    by_strategy = defaultdict(list)
    for trade in closed:
        by_strategy[trade.get("strategy", "")].append(trade)

    results = []
    for strat, trades in sorted(by_strategy.items()):
        if len(trades) < min_trades:
            continue

        pnls = [t.get("pnl_pct", 0) for t in trades]
        overall_regime = classify_regime(pnls)

        # Split trades into halves by absolute PnL (proxy for vol regimes)
        sorted_by_abs = sorted(trades, key=lambda t: abs(t.get("pnl_pct", 0)))
        mid = len(sorted_by_abs) // 2
        low_vol_trades = sorted_by_abs[:mid]
        high_vol_trades = sorted_by_abs[mid:]

        low_pnls = [t.get("pnl_pct", 0) for t in low_vol_trades]
        high_pnls = [t.get("pnl_pct", 0) for t in high_vol_trades]

        # Winning vs losing streaks (trend proxy)
        winning_streak_pnls = []
        losing_streak_pnls = []
        streak_type = None
        for t in trades:
            p = t.get("pnl_pct", 0)
            if p > 0:
                if streak_type == "win":
                    winning_streak_pnls.append(p)
                else:
                    streak_type = "win"
                    winning_streak_pnls.append(p)
            else:
                if streak_type == "loss":
                    losing_streak_pnls.append(p)
                else:
                    streak_type = "loss"
                    losing_streak_pnls.append(p)

        # Compute expectancy per regime
        def exp(pnl_list):
            if not pnl_list:
                return 0.0
            wins = [p for p in pnl_list if p > 0]
            losses = [p for p in pnl_list if p <= 0]
            wr = len(wins) / len(pnl_list)
            aw = sum(wins) / len(wins) if wins else 0
            al = abs(sum(losses) / len(losses)) if losses else 0
            return wr * aw - (1 - wr) * al

        results.append({
            "strategy": strat,
            "total_trades": len(trades),
            "overall_regime": overall_regime,
            "low_vol_expectancy": round(exp(low_pnls), 6),
            "high_vol_expectancy": round(exp(high_pnls), 6),
            "low_vol_trades": len(low_vol_trades),
            "high_vol_trades": len(high_vol_trades),
            "winning_streak_avg": round(sum(winning_streak_pnls) / len(winning_streak_pnls), 6) if winning_streak_pnls else 0,
            "losing_streak_avg": round(sum(losing_streak_pnls) / len(losing_streak_pnls), 6) if losing_streak_pnls else 0,
            "regime_preference": "high_vol" if exp(high_pnls) > exp(low_pnls) * 1.5 else
                                 "low_vol" if exp(low_pnls) > exp(high_pnls) * 1.5 else "neutral",
        })

    return results


# ─────────────────────────────────────────────────────────────────
# Correlation Matrix (Pearson)
# ─────────────────────────────────────────────────────────────────

def pearson_correlation(x, y):
    """Compute Pearson correlation between two lists."""
    n = min(len(x), len(y))
    if n < 3:
        return 0.0
    x, y = x[:n], y[:n]
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / n
    std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x) / n)
    std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y) / n)
    if std_x < 0.0001 or std_y < 0.0001:
        return 0.0
    return cov / (std_x * std_y)


def compute_correlation_matrix(min_trades=5):
    """Build a strategy-vs-strategy correlation matrix using daily PnL returns.

    Uses date-aligned returns: for each date, the PnL from each strategy's
    trade on that date (0 if no trade).
    """
    closed = load_closed_picks()
    if not closed:
        return {}, []

    # Build per-strategy time series keyed by date
    by_strategy = defaultdict(dict)
    all_dates = set()
    for trade in closed:
        strat = trade.get("strategy", "")
        date = trade.get("exit_date", trade.get("entry_date", ""))[:10]
        if date:
            by_strategy[strat][date] = by_strategy[strat].get(date, 0) + trade.get("pnl_pct", 0)
            all_dates.add(date)

    # Filter strategies with enough trades
    strategies = [s for s, dates in by_strategy.items() if len(dates) >= min_trades]
    strategies.sort()
    all_dates = sorted(all_dates)

    if len(strategies) < 2:
        return {}, strategies

    # Build aligned return vectors
    vectors = {}
    for strat in strategies:
        vectors[strat] = [by_strategy[strat].get(d, 0) for d in all_dates]

    # Compute correlation matrix
    matrix = {}
    for i, s1 in enumerate(strategies):
        matrix[s1] = {}
        for j, s2 in enumerate(strategies):
            if i == j:
                matrix[s1][s2] = 1.0
            elif j < i:
                matrix[s1][s2] = matrix[s2][s1]  # symmetric
            else:
                matrix[s1][s2] = round(pearson_correlation(vectors[s1], vectors[s2]), 4)

    return matrix, strategies


def find_correlated_pairs(matrix, strategies, threshold=0.5):
    """Find highly correlated strategy pairs (potential redundancy)."""
    pairs = []
    for i, s1 in enumerate(strategies):
        for j, s2 in enumerate(strategies):
            if j <= i:
                continue
            corr = matrix.get(s1, {}).get(s2, 0)
            if abs(corr) >= threshold:
                pairs.append({
                    "strategy_1": s1,
                    "strategy_2": s2,
                    "correlation": corr,
                    "type": "redundant" if corr > 0 else "hedge",
                })
    return sorted(pairs, key=lambda x: abs(x["correlation"]), reverse=True)


def find_hedge_pairs(matrix, strategies, threshold=-0.3):
    """Find anti-correlated pairs (natural hedges)."""
    pairs = []
    for i, s1 in enumerate(strategies):
        for j, s2 in enumerate(strategies):
            if j <= i:
                continue
            corr = matrix.get(s1, {}).get(s2, 0)
            if corr <= threshold:
                pairs.append({
                    "strategy_1": s1,
                    "strategy_2": s2,
                    "correlation": corr,
                })
    return sorted(pairs, key=lambda x: x["correlation"])


# ─────────────────────────────────────────────────────────────────
# Diversification Score
# ─────────────────────────────────────────────────────────────────

def compute_diversification_score(matrix, strategies):
    """Portfolio diversification score.

    Score = 1 - (avg absolute pairwise correlation).
    Perfect diversification = 1.0 (all uncorrelated).
    Zero diversification = 0.0 (all perfectly correlated).
    """
    if len(strategies) < 2:
        return 1.0

    total_corr = 0
    count = 0
    for i, s1 in enumerate(strategies):
        for j, s2 in enumerate(strategies):
            if j <= i:
                continue
            total_corr += abs(matrix.get(s1, {}).get(s2, 0))
            count += 1

    avg_corr = total_corr / count if count > 0 else 0
    return round(1 - avg_corr, 4)


# ─────────────────────────────────────────────────────────────────
# Symbol Concentration Risk
# ─────────────────────────────────────────────────────────────────

def compute_concentration_risk():
    """Analyze symbol concentration across all strategies.

    High concentration = many strategies trading the same symbol = correlated risk.
    """
    closed = load_closed_picks()
    if not closed:
        return {}

    symbol_strategies = defaultdict(set)
    symbol_trades = defaultdict(int)
    symbol_pnl = defaultdict(float)

    for trade in closed:
        sym = trade.get("symbol", "UNKNOWN")
        strat = trade.get("strategy", "unknown")
        symbol_strategies[sym].add(strat)
        symbol_trades[sym] += 1
        symbol_pnl[sym] += trade.get("pnl_pct", 0)

    concentration = {}
    for sym, strats in sorted(symbol_strategies.items(), key=lambda x: len(x[1]), reverse=True):
        concentration[sym] = {
            "strategies_using": len(strats),
            "strategy_list": sorted(strats),
            "total_trades": symbol_trades[sym],
            "total_pnl": round(symbol_pnl[sym], 6),
            "concentration_risk": "HIGH" if len(strats) > 5 else "MEDIUM" if len(strats) > 3 else "LOW",
        }

    return concentration


# ─────────────────────────────────────────────────────────────────
# Main Report
# ─────────────────────────────────────────────────────────────────

def print_full_report():
    """Generate complete regime and correlation report."""
    print("\n" + "=" * 100)
    print("REGIME ANALYZER & CORRELATION REPORT")
    print(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 100)

    # Regime sensitivity
    print(f"\n{'─'*80}")
    print("REGIME SENSITIVITY ANALYSIS")
    print(f"{'─'*80}")
    regimes = analyze_regime_sensitivity(min_trades=3)
    if regimes:
        print(f"\n{'Strategy':<35} {'Trades':>6} {'LowVol E':>9} {'HiVol E':>9} {'Pref':>10}")
        print("-" * 80)
        for r in sorted(regimes, key=lambda x: x["high_vol_expectancy"], reverse=True):
            print(f"{r['strategy']:<35} {r['total_trades']:>6} "
                  f"{r['low_vol_expectancy']:>+8.4f} {r['high_vol_expectancy']:>+8.4f} "
                  f"{r['regime_preference']:>10}")

    # Correlation matrix
    print(f"\n{'─'*80}")
    print("CORRELATION MATRIX")
    print(f"{'─'*80}")
    matrix, strategies = compute_correlation_matrix(min_trades=5)

    if strategies:
        # Print compact matrix
        header = f"{'':>25}" + "".join(f" {s[:6]:>7}" for s in strategies)
        print(header)
        for s1 in strategies:
            row = f"{s1[:25]:>25}"
            for s2 in strategies:
                c = matrix.get(s1, {}).get(s2, 0)
                row += f" {c:>+6.2f} "
            print(row)

        # Correlated pairs
        print(f"\n{'─'*80}")
        print("HIGHLY CORRELATED PAIRS (potential redundancy, |corr| > 0.5)")
        print(f"{'─'*80}")
        corr_pairs = find_correlated_pairs(matrix, strategies)
        for p in corr_pairs[:10]:
            label = "REDUNDANT" if p["type"] == "redundant" else "HEDGE"
            print(f"  {p['strategy_1']:<30} × {p['strategy_2']:<30} r={p['correlation']:>+.3f} [{label}]")

        # Natural hedges
        print(f"\n{'─'*80}")
        print("NATURAL HEDGES (anti-correlated pairs, corr < -0.3)")
        print(f"{'─'*80}")
        hedges = find_hedge_pairs(matrix, strategies)
        if hedges:
            for h in hedges[:5]:
                print(f"  {h['strategy_1']:<30} × {h['strategy_2']:<30} r={h['correlation']:>+.3f}")
        else:
            print("  No strong anti-correlations found.")

        # Diversification score
        div_score = compute_diversification_score(matrix, strategies)
        print(f"\nPORTFOLIO DIVERSIFICATION SCORE: {div_score:.4f}")
        if div_score > 0.8:
            print("  → Well diversified — strategies are largely uncorrelated")
        elif div_score > 0.5:
            print("  → Moderate diversification — some redundant signals")
        else:
            print("  → Poor diversification — high correlation risk")

    # Concentration risk
    print(f"\n{'─'*80}")
    print("SYMBOL CONCENTRATION RISK")
    print(f"{'─'*80}")
    conc = compute_concentration_risk()
    for sym, data in list(conc.items())[:15]:
        print(f"  {sym:<15} {data['strategies_using']} strategies | "
              f"{data['total_trades']} trades | PnL: {data['total_pnl']:>+.4f} | "
              f"Risk: {data['concentration_risk']}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Regime Analyzer")
    parser.add_argument("--correlation", action="store_true")
    parser.add_argument("--regimes", action="store_true")
    parser.add_argument("--concentration", action="store_true")
    args = parser.parse_args()

    if args.correlation:
        matrix, strategies = compute_correlation_matrix()
        pairs = find_correlated_pairs(matrix, strategies)
        print(json.dumps(pairs, indent=2))
    elif args.regimes:
        regimes = analyze_regime_sensitivity()
        print(json.dumps(regimes, indent=2))
    elif args.concentration:
        conc = compute_concentration_risk()
        print(json.dumps(conc, indent=2, default=list))
    else:
        print_full_report()
