"""Pairwise Spearman correlation between strategies' daily PnL series.

Why this exists
---------------
The supplement suite covers per-strategy edge / risk / overfit. What's
missing is the portfolio-level question: are these N "different"
strategies actually diversified, or are they all riding the same
underlying signal under slightly different names?

Two strategies that show high pairwise Spearman correlation on their
daily PnL — even if their NAMES differ — are effectively a single
strategy with a sample-size bonus. Allocating to both is double-counting
the same edge. The audit page should surface this directly.

This module computes pairwise Spearman rho on daily-aggregated PnL series
between every pair of strategies with >= 30 overlapping days, and groups
strategies into clusters where the average pairwise rho exceeds 0.7.

Output
------
- `strategies`: list of strategy names that had enough data to enter the
  matrix.
- `matrix[A][B] = {rho, n_overlap_days}` for every (A, B) pair.
- `top_pairs_by_abs_rho`: top-K pairs by |rho|.
- `threshold_clusters`: greedy clusters where every pair has rho >= 0.7.
  Each cluster reports {strategies, avg_rho, min_rho}.

Pure stdlib (math.fsum + rank + pearson-on-ranks). No scipy/pandas.

Wiring status: OPT-IN SIDECAR. Future PR adds a "concentration cluster"
column on `audit_dashboard/template.html` strategy table, surfacing the
cluster-id alongside each strategy.

Caveats
-------
1. Spearman rho on aggregated daily PnL ignores intra-day timing —
   two strategies that fire at different times on the same day will
   still correlate via daily aggregation.
2. Like every closed-pick supplement, fits on labels from
   outcome_resolver.py. Theme B contamination on FOREX/COMMODITY
   pending the cloud agent's resolver fix.
3. Greedy clustering is order-dependent. We sort by descending degree
   (number of >=0.7 neighbours) for determinism. For full hierarchical
   clustering use scipy.cluster — overkill for a sidecar.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PICKS_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO_ROOT / "tools" / "data" / "strategy_correlation_matrix.json"

DEFAULT_MIN_OVERLAP = 30
DEFAULT_CLUSTER_RHO = 0.70
DEFAULT_TOP_PAIRS = 20


def _safe_pnl(pick: dict) -> float | None:
    pnl = pick.get("pnl_pct")
    if pnl is None:
        return None
    try:
        v = float(pnl)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return v


def _parse_iso_date(s: Any) -> str | None:
    """Return YYYY-MM-DD UTC or None."""
    if not isinstance(s, str):
        return None
    try:
        ts = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%d")


def _aggregate_daily_by_strategy(picks: list[dict]) -> dict[str, dict[str, float]]:
    """Group picks by (strategy, UTC date), compute daily-mean PnL."""
    accum: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for p in picks:
        pnl = _safe_pnl(p)
        if pnl is None:
            continue
        ts_raw = p.get("closed_at") or p.get("opened_at")
        date = _parse_iso_date(ts_raw)
        if date is None:
            continue
        strat = p.get("strategy") or "unknown"
        accum[strat][date].append(pnl)
    return {
        strat: {d: sum(vals) / len(vals) for d, vals in dates.items()}
        for strat, dates in accum.items()
    }


def _ranks(values: list[float]) -> list[float]:
    """Average-rank tie-breaking (matches scipy.stats.rankdata default)."""
    n = len(values)
    indexed = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[indexed[j + 1]] == values[indexed[i]]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[indexed[k]] = avg_rank
        i = j + 1
    return ranks


def _pearson(x: list[float], y: list[float]) -> float:
    n = len(x)
    if n < 2:
        return 0.0
    mx = math.fsum(x) / n
    my = math.fsum(y) / n
    cov = math.fsum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    sx2 = math.fsum((xi - mx) ** 2 for xi in x)
    sy2 = math.fsum((yi - my) ** 2 for yi in y)
    denom = math.sqrt(sx2 * sy2)
    if denom < 1e-12:
        return 0.0
    return cov / denom


def spearman_rho(a: list[float], b: list[float]) -> float:
    """Spearman rank correlation."""
    if len(a) != len(b):
        raise ValueError("series must have equal length")
    return _pearson(_ranks(a), _ranks(b))


def pairwise_correlations(daily_by_strategy: dict[str, dict[str, float]],
                          min_overlap: int = DEFAULT_MIN_OVERLAP
                          ) -> tuple[dict[str, dict[str, dict]], list[str]]:
    """Compute the symmetric pairwise correlation matrix.

    Returns (matrix, strategies). matrix[A][B] = {rho, n} when the pair
    has >= min_overlap overlapping days; otherwise omitted. Strategies
    are sorted by name.
    """
    strategies = sorted(daily_by_strategy.keys())
    matrix: dict[str, dict[str, dict]] = defaultdict(dict)
    for i, a in enumerate(strategies):
        for b in strategies[i + 1:]:
            common_dates = sorted(set(daily_by_strategy[a].keys())
                                  & set(daily_by_strategy[b].keys()))
            if len(common_dates) < min_overlap:
                continue
            xa = [daily_by_strategy[a][d] for d in common_dates]
            xb = [daily_by_strategy[b][d] for d in common_dates]
            rho = spearman_rho(xa, xb)
            matrix[a][b] = {"rho": round(rho, 4),
                            "n_overlap_days": len(common_dates)}
            matrix[b][a] = {"rho": round(rho, 4),
                            "n_overlap_days": len(common_dates)}
    return dict(matrix), strategies


def top_pairs(matrix: dict[str, dict[str, dict]],
              k: int = DEFAULT_TOP_PAIRS) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    pairs: list[tuple[float, str, str, int]] = []
    for a, neighbours in matrix.items():
        for b, info in neighbours.items():
            key = tuple(sorted([a, b]))
            if key in seen:
                continue
            seen.add(key)
            pairs.append((abs(info["rho"]), a, b, info["n_overlap_days"]))
    pairs.sort(reverse=True)
    return [{"strategy_a": a, "strategy_b": b, "rho": round(rho, 4),
             "abs_rho": round(abs_rho, 4), "n_overlap_days": n}
            for abs_rho, a, b, n in pairs[:k]
            for rho in [next(matrix[a][b]["rho"] for _ in [0])]]  # rho dict lookup


def threshold_clusters(matrix: dict[str, dict[str, dict]],
                       threshold: float = DEFAULT_CLUSTER_RHO) -> list[dict]:
    """Greedy clusters where every pair has rho >= threshold.

    Order-dependent but deterministic: sort vertices by descending degree
    (number of >= threshold neighbours).
    """
    degrees: dict[str, int] = {
        a: sum(1 for n_info in neighbours.values() if n_info["rho"] >= threshold)
        for a, neighbours in matrix.items()
    }
    vertices = sorted(degrees, key=lambda v: (-degrees[v], v))
    used: set[str] = set()
    clusters: list[dict] = []
    for v in vertices:
        if v in used:
            continue
        cluster = {v}
        candidates = sorted(
            (b for b, info in matrix.get(v, {}).items()
             if b not in used and info["rho"] >= threshold),
            key=lambda b: (-degrees.get(b, 0), b)
        )
        for c in candidates:
            # All-pairs check: c connects to every member already in cluster
            if all(c in matrix and m in matrix[c]
                   and matrix[c][m]["rho"] >= threshold
                   for m in cluster):
                cluster.add(c)
        if len(cluster) >= 2:
            members = sorted(cluster)
            rhos = []
            for i, ai in enumerate(members):
                for bj in members[i + 1:]:
                    rhos.append(matrix[ai][bj]["rho"])
            clusters.append({
                "strategies": members,
                "size": len(members),
                "avg_rho": round(sum(rhos) / max(len(rhos), 1), 4),
                "min_rho": round(min(rhos), 4),
            })
            used.update(cluster)
    return clusters


def analyze_all(picks: list[dict],
                min_overlap: int = DEFAULT_MIN_OVERLAP,
                cluster_threshold: float = DEFAULT_CLUSTER_RHO,
                top_k: int = DEFAULT_TOP_PAIRS) -> dict:
    daily = _aggregate_daily_by_strategy(picks)
    matrix, strategies = pairwise_correlations(daily, min_overlap)
    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "config": {"min_overlap_days": min_overlap,
                   "cluster_rho_threshold": cluster_threshold,
                   "top_k_pairs": top_k},
        "strategies": strategies,
        "matrix": matrix,
        "top_pairs_by_abs_rho": top_pairs(matrix, top_k),
        "threshold_clusters": threshold_clusters(matrix, cluster_threshold),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--min-overlap", type=int, default=DEFAULT_MIN_OVERLAP)
    ap.add_argument("--cluster-rho", type=float, default=DEFAULT_CLUSTER_RHO)
    ap.add_argument("--top-k", type=int, default=DEFAULT_TOP_PAIRS)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    with PICKS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data.get("picks", {}).get("recent_closed", [])

    summary = analyze_all(picks, args.min_overlap, args.cluster_rho, args.top_k)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    if not args.quiet:
        print(f"strategies in matrix: {len(summary['strategies'])}")
        print(f"clusters >= {args.cluster_rho}: {len(summary['threshold_clusters'])}")
        print("top 10 pairs by |rho|:")
        for r in summary["top_pairs_by_abs_rho"][:10]:
            print(f"  {r['strategy_a'][:25]:<25} <-> {r['strategy_b'][:25]:<25} "
                  f"rho={r['rho']:>+5.3f} n={r['n_overlap_days']}")
        print(f"JSON: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
