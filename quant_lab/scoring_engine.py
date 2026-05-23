"""
Bundle Scoring & Hidden Gem Detection Engine.

Scores strategies using expectancy-first weighted formula.
Detects hidden gems: low WR + high payoff ratio + positive expectancy.
Clusters strategies by behavior to find regime specialists.

Adapted from Mercury/Inception Labs framework.

Usage:
    python quant_lab/scoring_engine.py                # Full scoring report
    python quant_lab/scoring_engine.py --hidden-gems  # Hidden gem discovery only
    python quant_lab/scoring_engine.py --clusters 4   # Cluster analysis
"""
import json
import math
import sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "quant_lab"))
from kpi_engine import compute_all_kpis, compute_edge_verdict, load_closed_picks


# ─────────────────────────────────────────────────────────────────
# Scoring Formula (expectancy-first, Mercury framework)
# ─────────────────────────────────────────────────────────────────

# Tunable weights — adjust based on research priorities
SCORE_WEIGHTS = {
    "expectancy": 0.35,
    "sharpe": 0.20,
    "low_drawdown": 0.15,
    "kelly": 0.10,
    "profit_factor": 0.10,
    "trade_count_bonus": 0.05,
    "tp_efficiency": 0.05,
}


def compute_strategy_score(kpi):
    """
    Composite score combining multiple metrics.
    Higher = better candidate for capital allocation.
    """
    # Normalize each component to roughly [0, 1] range
    exp_norm = min(max(kpi["expectancy_pct"] * 10, -1), 1)  # scale: 0.1 = 1.0
    sharpe_norm = min(max(kpi["sharpe"] / 50, -1), 1)  # scale: 50 = 1.0
    dd_norm = 1 - min(kpi["max_drawdown"], 1)  # lower DD = higher score
    kelly_norm = min(max(kpi["kelly_fraction"], -1), 1)
    pf_norm = min(kpi["profit_factor"] / 10, 1)  # scale: 10 = 1.0
    trade_bonus = min(kpi["trade_count"] / 20, 1)  # bonus for more trades
    tp_eff = min(max(kpi["tp_efficiency"], 0), 1)

    score = (
        SCORE_WEIGHTS["expectancy"] * exp_norm +
        SCORE_WEIGHTS["sharpe"] * sharpe_norm +
        SCORE_WEIGHTS["low_drawdown"] * dd_norm +
        SCORE_WEIGHTS["kelly"] * kelly_norm +
        SCORE_WEIGHTS["profit_factor"] * pf_norm +
        SCORE_WEIGHTS["trade_count_bonus"] * trade_bonus +
        SCORE_WEIGHTS["tp_efficiency"] * tp_eff
    )
    return round(score, 6)


# ─────────────────────────────────────────────────────────────────
# Hidden Gem Detection
# ─────────────────────────────────────────────────────────────────

def detect_hidden_gems(kpis):
    """
    Find strategies that look bad by win rate but are actually profitable.

    Hidden gem criteria:
    1. Low win rate (< 50%) BUT positive expectancy
    2. High payoff ratio (> 2.0) — wins are much bigger than losses
    3. High profit factor (> 1.5) despite low win rate
    4. Positive Kelly fraction
    """
    gems = []
    for kpi in kpis:
        wr = kpi["win_rate"]
        exp = kpi["expectancy_pct"]
        pr = kpi["payoff_ratio"]
        pf = kpi["profit_factor"]
        kf = kpi["kelly_fraction"]
        trades = kpi["trade_count"]

        # Must have enough trades to be meaningful
        if trades < 3:
            continue

        reasons = []

        # Classic hidden gem: low WR + high payoff
        if wr < 0.5 and exp > 0 and pr > 2.0:
            reasons.append(f"Low WR ({wr:.0%}) but payoff ratio {pr:.1f}x")

        # Asymmetric alpha: very low WR but massive profit factor
        if wr < 0.35 and pf > 5.0:
            reasons.append(f"Asymmetric: {wr:.0%} WR but PF={pf:.1f}")

        # Sortino outlier: high downside-adjusted return
        if kpi["sortino"] > 20 and wr < 0.5:
            reasons.append(f"Sortino outlier: {kpi['sortino']:.1f}")

        # MFE much larger than captured PnL (leaving money on table)
        if kpi["avg_mfe"] > 0 and kpi["tp_efficiency"] < 0.5 and exp > 0:
            reasons.append(f"Only capturing {kpi['tp_efficiency']:.0%} of MFE — exit optimization candidate")

        if reasons:
            gems.append({
                "strategy": kpi["entity_id"],
                "win_rate": wr,
                "expectancy": exp,
                "payoff_ratio": pr,
                "profit_factor": pf,
                "kelly": kf,
                "trades": trades,
                "score": compute_strategy_score(kpi),
                "reasons": reasons,
                "verdict": compute_edge_verdict(kpi),
            })

    return sorted(gems, key=lambda x: x["score"], reverse=True)


# ─────────────────────────────────────────────────────────────────
# Strategy Clustering (pure Python, no sklearn dependency)
# ─────────────────────────────────────────────────────────────────

def cluster_strategies(kpis, n_clusters=4):
    """
    Simple K-means-like clustering on strategy behavior metrics.
    Pure Python implementation — no sklearn required.

    Clusters on: win_rate, payoff_ratio, sharpe, max_drawdown, kelly_fraction
    """
    # Extract features
    features = []
    names = []
    for kpi in kpis:
        if kpi["trade_count"] < 2:
            continue
        features.append([
            kpi["win_rate"],
            min(kpi["payoff_ratio"], 10),  # cap outliers
            min(kpi["sharpe"] / 50, 1),    # normalize
            kpi["max_drawdown"],
            max(min(kpi["kelly_fraction"], 1), -1),
        ])
        names.append(kpi["entity_id"])

    if len(features) < n_clusters:
        return []

    # Normalize features (z-score)
    n = len(features)
    d = len(features[0])
    means = [sum(features[i][j] for i in range(n)) / n for j in range(d)]
    stds = [math.sqrt(sum((features[i][j] - means[j]) ** 2 for i in range(n)) / n) for j in range(d)]
    stds = [s if s > 0 else 1 for s in stds]

    normalized = [[(features[i][j] - means[j]) / stds[j] for j in range(d)] for i in range(n)]

    # Simple K-means (10 iterations)
    import random
    random.seed(42)
    centroids = random.sample(normalized, n_clusters)

    for _ in range(10):
        # Assign to nearest centroid
        assignments = []
        for point in normalized:
            dists = [sum((point[j] - c[j]) ** 2 for j in range(d)) for c in centroids]
            assignments.append(dists.index(min(dists)))

        # Update centroids
        for k in range(n_clusters):
            members = [normalized[i] for i in range(n) if assignments[i] == k]
            if members:
                centroids[k] = [sum(m[j] for m in members) / len(members) for j in range(d)]

    # Build cluster report
    clusters = defaultdict(list)
    for i, name in enumerate(names):
        kpi = next(k for k in kpis if k["entity_id"] == name)
        clusters[assignments[i]].append({
            "strategy": name,
            "win_rate": kpi["win_rate"],
            "expectancy": kpi["expectancy_pct"],
            "sharpe": kpi["sharpe"],
            "kelly": kpi["kelly_fraction"],
            "verdict": compute_edge_verdict(kpi),
        })

    return dict(clusters)


# ─────────────────────────────────────────────────────────────────
# Tail Event Mining
# ─────────────────────────────────────────────────────────────────

def find_tail_catchers(kpis, closed_picks=None):
    """Find strategies that catch extreme moves (>10% single-trade PnL)."""
    if closed_picks is None:
        closed_picks = load_closed_picks()

    by_strategy = defaultdict(list)
    for trade in closed_picks:
        by_strategy[trade.get("strategy", "")].append(trade)

    tail_catchers = []
    for strat, trades in by_strategy.items():
        big_wins = [t for t in trades if t.get("pnl_pct", 0) > 0.10]  # >10%
        if big_wins:
            kpi = next((k for k in kpis if k["entity_id"] == strat), None)
            tail_catchers.append({
                "strategy": strat,
                "total_trades": len(trades),
                "big_wins": len(big_wins),
                "biggest_win_pct": max(t["pnl_pct"] for t in big_wins),
                "avg_big_win_pct": sum(t["pnl_pct"] for t in big_wins) / len(big_wins),
                "symbols_caught": list(set(t.get("symbol", "") for t in big_wins)),
                "verdict": compute_edge_verdict(kpi) if kpi else "UNKNOWN",
            })

    return sorted(tail_catchers, key=lambda x: x["biggest_win_pct"], reverse=True)


# ─────────────────────────────────────────────────────────────────
# Graveyard Forensics
# ─────────────────────────────────────────────────────────────────

def graveyard_forensics(kpis):
    """Analyze dead strategies for resurrection candidates."""
    candidates = []
    for kpi in kpis:
        verdict = compute_edge_verdict(kpi)
        if verdict not in ("DEAD", "TRAP", "NO_EDGE"):
            continue

        reasons = []

        # Check if direction was correct (MFE > MAE)
        if kpi["avg_mfe"] > abs(kpi["avg_mae"]) * 0.8:
            reasons.append(f"Direction correct (MFE {kpi['avg_mfe']:+.4f} > 80% MAE)")

        # Check if exit is the problem
        if kpi["tp_efficiency"] < 0.3 and kpi["avg_mfe"] > 0.02:
            reasons.append(f"Exit kills edge (only capturing {kpi['tp_efficiency']:.0%} of move)")

        # Check if specific symbols are profitable
        by_sym = kpi.get("by_symbol", {})
        profitable_syms = [s for s, d in by_sym.items() if d.get("pnl", 0) > 0]
        if profitable_syms and len(profitable_syms) < len(by_sym):
            reasons.append(f"Profitable on {profitable_syms} — consider symbol filtering")

        if reasons:
            candidates.append({
                "strategy": kpi["entity_id"],
                "current_pnl": kpi["total_pnl_dollar"],
                "win_rate": kpi["win_rate"],
                "trades": kpi["trade_count"],
                "resurrection_reasons": reasons,
            })

    return candidates


# ─────────────────────────────────────────────────────────────────
# Main Report
# ─────────────────────────────────────────────────────────────────

def print_full_report():
    """Generate complete scoring report."""
    kpis = compute_all_kpis(min_trades=1)

    # Score all strategies
    for kpi in kpis:
        kpi["composite_score"] = compute_strategy_score(kpi)

    ranked = sorted(kpis, key=lambda x: x["composite_score"], reverse=True)

    print("\n" + "=" * 100)
    print("STRATEGY SCORING & RANKING REPORT")
    print(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 100)

    print(f"\n{'Rank':>4} {'Strategy':<35} {'Score':>7} {'Expect':>8} {'Sharpe':>7} "
          f"{'Kelly':>6} {'WR%':>5} {'PF':>6} {'Verdict':<15}")
    print("-" * 100)
    for i, r in enumerate(ranked, 1):
        verdict = compute_edge_verdict(r)
        print(f"{i:>4} {r['entity_id']:<35} {r['composite_score']:>7.4f} "
              f"{r['expectancy_pct']:>+7.4f} {r['sharpe']:>7.2f} "
              f"{r['kelly_fraction']:>+5.2f} {r['win_rate']*100:>4.0f}% "
              f"{r['profit_factor']:>6.2f} {verdict:<15}")

    # Hidden gems
    print(f"\n{'='*80}")
    print("HIDDEN GEM DISCOVERY")
    print(f"{'='*80}")
    gems = detect_hidden_gems(kpis)
    if gems:
        for gem in gems:
            print(f"\n  {gem['strategy']} (Score: {gem['score']:.4f})")
            print(f"    WR: {gem['win_rate']:.0%} | Expect: {gem['expectancy']:+.4f} | "
                  f"Payoff: {gem['payoff_ratio']:.1f}x | Kelly: {gem['kelly']:+.3f}")
            for reason in gem["reasons"]:
                print(f"    -> {reason}")
    else:
        print("  No hidden gems found.")

    # Tail catchers
    print(f"\n{'='*80}")
    print("TAIL EVENT CATCHERS (strategies that catch 10%+ moves)")
    print(f"{'='*80}")
    tails = find_tail_catchers(kpis)
    for t in tails[:5]:
        print(f"  {t['strategy']}: {t['big_wins']} big wins / {t['total_trades']} trades | "
              f"Best: {t['biggest_win_pct']:+.1%} | Symbols: {', '.join(t['symbols_caught'])}")

    # Clusters
    print(f"\n{'='*80}")
    print("STRATEGY CLUSTERS (behavioral grouping)")
    print(f"{'='*80}")
    clusters = cluster_strategies(kpis, n_clusters=4)
    for cluster_id, members in clusters.items():
        avg_exp = sum(m["expectancy"] for m in members) / len(members) if members else 0
        avg_wr = sum(m["win_rate"] for m in members) / len(members) if members else 0
        print(f"\n  Cluster {cluster_id} ({len(members)} strategies) — "
              f"Avg Expect: {avg_exp:+.4f} | Avg WR: {avg_wr:.0%}")
        for m in members:
            print(f"    {m['strategy']:<35} WR={m['win_rate']:.0%} "
                  f"E={m['expectancy']:+.4f} S={m['sharpe']:.1f} [{m['verdict']}]")

    # Graveyard forensics
    print(f"\n{'='*80}")
    print("GRAVEYARD FORENSICS (resurrection candidates)")
    print(f"{'='*80}")
    resurrections = graveyard_forensics(kpis)
    if resurrections:
        for r in resurrections:
            print(f"\n  {r['strategy']} (PnL: ${r['current_pnl']:+,.2f} | "
                  f"WR: {r['win_rate']:.0%} | Trades: {r['trades']})")
            for reason in r["resurrection_reasons"]:
                print(f"    -> {reason}")
    else:
        print("  No resurrection candidates found.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Strategy Scoring Engine")
    parser.add_argument("--hidden-gems", action="store_true")
    parser.add_argument("--clusters", type=int, default=0)
    parser.add_argument("--tails", action="store_true")
    parser.add_argument("--graveyard", action="store_true")
    args = parser.parse_args()

    if args.hidden_gems:
        kpis = compute_all_kpis(min_trades=2)
        gems = detect_hidden_gems(kpis)
        print(json.dumps(gems, indent=2))
    elif args.clusters > 0:
        kpis = compute_all_kpis(min_trades=2)
        clusters = cluster_strategies(kpis, args.clusters)
        print(json.dumps(clusters, indent=2, default=str))
    elif args.tails:
        kpis = compute_all_kpis(min_trades=1)
        tails = find_tail_catchers(kpis)
        print(json.dumps(tails, indent=2))
    elif args.graveyard:
        kpis = compute_all_kpis(min_trades=1)
        resurrections = graveyard_forensics(kpis)
        print(json.dumps(resurrections, indent=2))
    else:
        print_full_report()
