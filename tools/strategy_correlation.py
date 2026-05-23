#!/usr/bin/env python3
"""Cross-strategy correlation matrix & risk-parity portfolio optimizer.

Reads closed picks from dashboard_data.json, builds daily PnL time-series
per strategy, computes pairwise Pearson correlations, and outputs:
  - Correlation matrix (top strategies)
  - Redundant pairs (r > 0.7)
  - Natural hedges (r < -0.3)
  - Risk-parity optimal weights

Results -> tools/correlation_results.json
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from math import sqrt

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MIN_PICKS = 15          # minimum closed picks to include a strategy
REDUNDANT_THRESHOLD = 0.70
HEDGE_THRESHOLD = -0.30
TOP_N = 20              # matrix size cap
DATA_PATH = os.path.join(os.path.dirname(__file__), "..",
                         "audit_dashboard", "data", "dashboard_data.json")
OUT_PATH = os.path.join(os.path.dirname(__file__), "correlation_results.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_date(raw):
    """Return date string YYYY-MM-DD from various timestamp formats."""
    if not raw:
        return None
    s = str(raw)[:10]
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except ValueError:
        return None


def _pearson(xs, ys):
    """Pearson correlation for two equal-length lists. Returns 0 on degenerate."""
    n = len(xs)
    if n < 5:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = sqrt(max(sum((x - mx) ** 2 for x in xs), 1e-15))
    sy = sqrt(max(sum((y - my) ** 2 for y in ys), 1e-15))
    return cov / (sx * sy)


def _stdev(xs):
    if len(xs) < 2:
        return 1e-9
    m = sum(xs) / len(xs)
    return sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) or 1e-9


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    # 1. Load data
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data["picks"]["recent_closed"]
    print(f"Loaded {len(picks)} closed picks.")

    # 2. Build daily PnL per strategy
    #    Key = (strategy, date) -> list of pnl_pct values
    strat_daily = defaultdict(lambda: defaultdict(list))
    strat_count = defaultdict(int)
    for p in picks:
        strat = p.get("strategy") or "unknown"
        pnl = p.get("pnl_pct")
        if pnl is None:
            continue
        # Use closed_at first, fall back to timestamp
        dt = _parse_date(p.get("closed_at")) or _parse_date(p.get("timestamp"))
        if not dt:
            continue
        strat_daily[strat][dt].append(float(pnl))
        strat_count[strat] += 1

    # Filter strategies with enough picks
    eligible = sorted(
        [s for s, c in strat_count.items() if c >= MIN_PICKS],
        key=lambda s: -strat_count[s],
    )
    print(f"Strategies with >= {MIN_PICKS} picks: {len(eligible)}")

    # Take top N by count for matrix
    top = eligible[:TOP_N]
    print(f"Using top {len(top)} strategies for correlation matrix.")

    # 3. Build aligned daily series
    #    Collect all dates, then for each strategy compute mean daily PnL
    all_dates = sorted(set(d for s in top for d in strat_daily[s]))
    print(f"Date range: {all_dates[0]} -> {all_dates[-1]} ({len(all_dates)} days)")

    # Per-strategy: daily mean PnL (0 if no trades that day)
    series = {}
    for s in top:
        series[s] = [
            (sum(strat_daily[s][d]) / len(strat_daily[s][d]))
            if d in strat_daily[s] else 0.0
            for d in all_dates
        ]

    # 4. Pairwise correlation matrix
    n = len(top)
    corr_matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        corr_matrix[i][i] = 1.0
        for j in range(i + 1, n):
            r = _pearson(series[top[i]], series[top[j]])
            corr_matrix[i][j] = round(r, 4)
            corr_matrix[j][i] = round(r, 4)

    # 5. Flag redundant pairs and natural hedges
    redundant = []
    hedges = []
    for i in range(n):
        for j in range(i + 1, n):
            r = corr_matrix[i][j]
            if r > REDUNDANT_THRESHOLD:
                redundant.append({
                    "strategy_a": top[i],
                    "strategy_b": top[j],
                    "correlation": r,
                    "picks_a": strat_count[top[i]],
                    "picks_b": strat_count[top[j]],
                })
            if r < HEDGE_THRESHOLD:
                hedges.append({
                    "strategy_a": top[i],
                    "strategy_b": top[j],
                    "correlation": r,
                })

    redundant.sort(key=lambda x: -x["correlation"])
    hedges.sort(key=lambda x: x["correlation"])

    # 6. Diversification score per strategy (lower = better)
    div_scores = {}
    for i, s in enumerate(top):
        others = [abs(corr_matrix[i][j]) for j in range(n) if j != i]
        div_scores[s] = round(sum(others) / len(others), 4) if others else 0.0

    # 7. Risk-parity weights
    #    Step A: inverse-vol weights
    vols = {s: _stdev(series[s]) for s in top}
    inv_vol = {s: 1.0 / vols[s] for s in top}

    #    Step B: cluster penalty — if a strategy is in a redundant pair,
    #    keep only the one with the best diversification score, halve others
    cluster_penalty = {s: 1.0 for s in top}
    seen_clusters = set()
    for pair in redundant:
        a, b = pair["strategy_a"], pair["strategy_b"]
        key = tuple(sorted([a, b]))
        if key in seen_clusters:
            continue
        seen_clusters.add(key)
        # Penalize the more correlated (worse div score) member
        if div_scores.get(a, 1) > div_scores.get(b, 1):
            cluster_penalty[a] *= 0.3   # demote the redundant one
        else:
            cluster_penalty[b] *= 0.3

    raw_w = {s: inv_vol[s] * cluster_penalty[s] for s in top}
    total_w = sum(raw_w.values()) or 1.0
    weights = {s: round(raw_w[s] / total_w * 100, 2) for s in top}
    weights = dict(sorted(weights.items(), key=lambda x: -x[1]))

    # 8. Estimate vol reduction from removing redundancies
    #    Simple estimate: if we zero out redundant-penalized strategies,
    #    how much portfolio vol drops.
    full_port = [
        sum(series[s][d] * (weights[s] / 100) for s in top)
        for d in range(len(all_dates))
    ]
    full_vol = _stdev(full_port)

    # Reduced portfolio: zero-weight strategies with penalty < 1
    reduced_strats = [s for s in top if cluster_penalty[s] >= 1.0]
    if reduced_strats:
        red_w = {s: 1.0 / vols[s] for s in reduced_strats}
        red_total = sum(red_w.values()) or 1.0
        red_w = {s: red_w[s] / red_total for s in reduced_strats}
        reduced_port = [
            sum(series[s][d] * red_w[s] for s in reduced_strats)
            for d in range(len(all_dates))
        ]
        reduced_vol = _stdev(reduced_port)
        vol_reduction_pct = round((1 - reduced_vol / full_vol) * 100, 1) if full_vol > 0 else 0.0
    else:
        vol_reduction_pct = 0.0

    # 9. Write results
    result = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "strategies_analyzed": len(top),
        "date_range": {"start": all_dates[0], "end": all_dates[-1], "days": len(all_dates)},
        "correlation_matrix": {
            "strategies": top,
            "matrix": corr_matrix,
        },
        "redundant_pairs": redundant,
        "natural_hedges": hedges,
        "diversification_scores": div_scores,
        "recommended_weights_pct": weights,
        "volatilities": {s: round(vols[s], 4) for s in top},
        "vol_reduction_estimate_pct": vol_reduction_pct,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\nResults written to {OUT_PATH}")

    # 10. Print summary
    print("\n" + "=" * 60)
    print("CROSS-STRATEGY CORRELATION ANALYSIS")
    print("=" * 60)
    print(f"Strategies analyzed: {len(top)}")
    print(f"Date range: {all_dates[0]} -> {all_dates[-1]} ({len(all_dates)} days)")

    print(f"\n--- Redundant pairs (r > {REDUNDANT_THRESHOLD}): {len(redundant)} ---")
    for p in redundant[:10]:
        print(f"  {p['strategy_a']:40s} <-> {p['strategy_b']:40s}  r={p['correlation']:.3f}")

    print(f"\n--- Natural hedges (r < {HEDGE_THRESHOLD}): {len(hedges)} ---")
    for h in hedges[:10]:
        print(f"  {h['strategy_a']:40s} <-> {h['strategy_b']:40s}  r={h['correlation']:.3f}")

    print(f"\n--- Risk-parity weights (top 10) ---")
    for i, (s, w) in enumerate(weights.items()):
        if i >= 10:
            break
        print(f"  {w:5.1f}%  {s}  (div={div_scores[s]:.3f}, vol={vols[s]:.4f})")

    print(f"\n{len(redundant)} redundant pairs found. "
          f"Removing redundancies would reduce portfolio vol by ~{vol_reduction_pct}%.")


if __name__ == "__main__":
    main()
