"""
Hierarchical Risk Parity (HRP) Portfolio Allocation for Battleground.

Uses closed trade data to compute correlation-based strategy clustering,
then assigns inverse-variance weights within each cluster.

Reference: Lopez de Prado (2016) "Building Diversified Portfolios that Outperform Out-of-Sample"

Falls back to equal-weight if insufficient data (<20 trades per strategy).
"""
import json
import os
import numpy as np
from collections import defaultdict
from datetime import datetime

try:
    from scipy.cluster.hierarchy import linkage, leaves_list
    from scipy.spatial.distance import squareform
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

BASE = os.path.dirname(os.path.abspath(__file__))
CLOSED_PICKS_FILE = os.path.join(BASE, "data", "closed_picks.json")
MIN_TRADES_PER_STRATEGY = 15


def load_closed_trades():
    """Load closed picks from Battleground data."""
    if not os.path.exists(CLOSED_PICKS_FILE):
        return []
    with open(CLOSED_PICKS_FILE, "r") as f:
        return json.load(f)


def build_return_series(trades, strategies):
    """
    Build daily PnL return series per strategy.
    Returns a dict {strategy: [daily_returns]} aligned to common dates.
    """
    # Group trades by strategy and date
    daily_pnl = defaultdict(lambda: defaultdict(float))

    for t in trades:
        strat = t.get("strategy", "")
        if strat not in strategies:
            continue
        # Use exit_time as the date the return is realized
        exit_time = t.get("exit_time", "")
        if not exit_time:
            continue
        date_str = exit_time[:10]  # YYYY-MM-DD
        daily_pnl[strat][date_str] += float(t.get("pnl_pct", 0) or 0)

    # Get union of all dates
    all_dates = sorted(set(d for strat_dates in daily_pnl.values() for d in strat_dates))
    if len(all_dates) < 5:
        return None, None

    # Build matrix: rows=dates, cols=strategies
    strat_list = sorted(strategies)
    matrix = np.zeros((len(all_dates), len(strat_list)))
    for j, strat in enumerate(strat_list):
        for i, date in enumerate(all_dates):
            matrix[i, j] = daily_pnl[strat].get(date, 0.0)

    return matrix, strat_list


def compute_correlation_matrix(returns_matrix):
    """Compute correlation matrix from returns, handling zero-variance columns."""
    n_cols = returns_matrix.shape[1]
    corr = np.corrcoef(returns_matrix.T)

    # Handle NaN from zero-variance strategies
    corr = np.nan_to_num(corr, nan=0.0)
    np.fill_diagonal(corr, 1.0)

    return corr


def _cluster_manual(corr_matrix):
    """
    Manual single-linkage clustering fallback when scipy is unavailable.
    Returns ordered leaf indices.
    """
    n = corr_matrix.shape[0]
    dist = np.sqrt(0.5 * (1 - corr_matrix))  # correlation distance
    np.fill_diagonal(dist, 0.0)

    # Simple greedy nearest-neighbor ordering
    remaining = list(range(n))
    ordered = [remaining.pop(0)]
    while remaining:
        last = ordered[-1]
        dists = [(dist[last, r], r) for r in remaining]
        dists.sort()
        nearest = dists[0][1]
        ordered.append(nearest)
        remaining.remove(nearest)
    return ordered


def _get_quasi_diag(link, n):
    """Extract quasi-diagonal ordering from linkage matrix."""
    return list(leaves_list(link))


def _get_cluster_var(cov, cluster_items):
    """Compute cluster variance using inverse-variance weights."""
    cov_slice = cov[np.ix_(cluster_items, cluster_items)]
    # Inverse variance portfolio within cluster
    diag = np.diag(cov_slice)
    diag = np.where(diag < 1e-10, 1e-10, diag)  # avoid division by zero
    ivp = 1.0 / diag
    ivp /= ivp.sum()
    cluster_var = float(ivp @ cov_slice @ ivp)
    return cluster_var


def _recursive_bisection(cov, sorted_indices):
    """
    HRP recursive bisection — allocates weights by splitting sorted indices
    and assigning inversely proportional to cluster variance.
    """
    n = len(sorted_indices)
    weights = np.ones(n)

    # Stack-based iterative bisection
    clusters = [(sorted_indices, 1.0)]
    result_weights = {}

    while clusters:
        items, alloc = clusters.pop()
        if len(items) == 1:
            result_weights[items[0]] = alloc
            continue

        mid = len(items) // 2
        left = items[:mid]
        right = items[mid:]

        left_var = _get_cluster_var(cov, left)
        right_var = _get_cluster_var(cov, right)

        total_var = left_var + right_var
        if total_var < 1e-10:
            alpha = 0.5
        else:
            alpha = 1.0 - left_var / total_var  # less variance => more weight

        clusters.append((left, alloc * alpha))
        clusters.append((right, alloc * (1 - alpha)))

    return result_weights


def compute_hrp_weights(strategies, total_risk_budget=1.0):
    """
    Compute HRP allocation weights for the given strategies.

    Args:
        strategies: list of strategy names
        total_risk_budget: total allocation (1.0 = 100%)

    Returns:
        dict {strategy_name: weight} where weights sum to total_risk_budget,
        or equal weights if insufficient data.
    """
    n = len(strategies)
    equal_weight = total_risk_budget / n
    equal_weights = {s: equal_weight for s in strategies}

    trades = load_closed_trades()
    if not trades:
        return equal_weights

    # Check minimum trades per strategy
    from collections import Counter
    trade_counts = Counter(t["strategy"] for t in trades if t.get("strategy") in set(strategies))
    for s in strategies:
        if trade_counts.get(s, 0) < MIN_TRADES_PER_STRATEGY:
            # Not enough data, use equal weights
            return equal_weights

    # Build return series
    returns_matrix, strat_list = build_return_series(trades, set(strategies))
    if returns_matrix is None or returns_matrix.shape[0] < 5:
        return equal_weights

    # Compute covariance and correlation
    cov = np.cov(returns_matrix.T)
    if cov.ndim == 0:
        return equal_weights
    corr = compute_correlation_matrix(returns_matrix)

    # Cluster strategies
    if HAS_SCIPY:
        # Correlation distance matrix
        dist = np.sqrt(0.5 * (1 - corr))
        np.fill_diagonal(dist, 0.0)
        # Ensure symmetry and valid condensed form
        dist = (dist + dist.T) / 2
        condensed = squareform(dist, checks=False)
        link = linkage(condensed, method="single")
        sorted_idx = list(leaves_list(link))
    else:
        sorted_idx = _cluster_manual(corr)

    # Recursive bisection to get weights
    raw_weights = _recursive_bisection(cov, sorted_idx)

    # Map back to strategy names
    weights = {}
    for idx, w in raw_weights.items():
        weights[strat_list[idx]] = w * total_risk_budget

    # Ensure all strategies have a weight
    for s in strategies:
        if s not in weights:
            weights[s] = equal_weight

    # Normalize to total_risk_budget
    total = sum(weights.values())
    if total > 0:
        for s in weights:
            weights[s] = weights[s] / total * total_risk_budget

    return weights


def get_position_size(strategy_name, strategies, capital, default_pct=0.05):
    """
    Get the dollar position size for a specific strategy using HRP weights.

    Args:
        strategy_name: the strategy to size
        strategies: full list of portfolio strategies
        capital: current portfolio capital
        default_pct: fallback position size percentage

    Returns:
        float: dollar amount to allocate to this trade
    """
    weights = compute_hrp_weights(strategies, total_risk_budget=default_pct * len(strategies))
    pct = weights.get(strategy_name, default_pct)
    # Cap individual position at 3x the equal-weight to prevent concentration
    max_pct = default_pct * 3
    pct = min(pct, max_pct)
    return capital * pct


if __name__ == "__main__":
    # Demo: compute weights for all 9 Battleground strategies
    all_strategies = [
        "crypto_keltner_compression_expansion_v1",
        "keltner_compression_expansion_eth_v1",
        "keltner_compression_expansion_sol_v1",
        "keltner_compression_expansion_xrp_v1",
        "drawdown_recovery_rsi",
        "drawdown_recovery_rsi_eth",
        "multi_period_rsi_confluence_eth",
        "multi_period_rsi_confluence_xrp",
        "crypto_drawdown_convexity_recovery_v1",
    ]

    weights = compute_hrp_weights(all_strategies, total_risk_budget=0.45)

    print("=" * 60)
    print("  HRP Allocation Weights (Battleground)")
    print("=" * 60)
    print(f"\n  {'Strategy':<50} {'Weight':>8}")
    print(f"  {'-'*50} {'-'*8}")

    for s in sorted(weights, key=weights.get, reverse=True):
        pct = weights[s] * 100
        print(f"  {s:<50} {pct:>7.2f}%")

    total = sum(weights.values()) * 100
    print(f"\n  {'TOTAL':<50} {total:>7.2f}%")
    print(f"\n  Equal-weight would be: {0.45/9*100:.2f}% each")
    print(f"  HRP scipy available: {HAS_SCIPY}")
