#!/usr/bin/env python3
"""
Decile Separation Test - Validates that our scoring system actually
separates good picks from bad.

If scoring works, top-decile picks should have significantly higher WR
and PnL than bottom-decile picks. This test quantifies that separation.

Usage:
    python decile_separation_test.py [path_to_closed_picks.json]

Stdlib only - no external dependencies.
"""

import json
import math
import os
import sys
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_scored_picks(path):
    """Load closed picks that have a usable score field."""
    with open(path, "r", encoding="utf-8") as f:
        picks = json.load(f)

    scored = []
    for p in picks:
        # Prefer elite_score, fall back to ml_score, then confidence
        score = p.get("elite_score")
        if score is None:
            score = p.get("ml_score")
        if score is None:
            score = p.get("confidence")
        if score is None:
            continue

        # Need a definitive outcome
        status = p.get("status", "").upper()
        if status not in ("WON", "LOST"):
            continue

        scored.append({
            "score": float(score),
            "won": status == "WON",
            "pnl_pct": float(p.get("pnl_pct", 0.0)),
            "confidence": float(p.get("confidence", 0.0)),
            "regime": _normalize_regime(p.get("regime_at_entry")),
            "category": _normalize_category(p.get("category", "unknown")),
        })

    return scored


def _normalize_regime(raw):
    """Map raw regime strings to BULL / BEAR / NEUTRAL."""
    if raw is None:
        return "NEUTRAL"
    r = str(raw).upper().strip()
    if r in ("BULL", "BULLISH", "TRENDING", "MOMENTUM"):
        return "BULL"
    if r in ("BEAR", "BEARISH"):
        return "BEAR"
    # backfill, ranging, transitional, unknown, NONE, etc.
    return "NEUTRAL"


def _normalize_category(raw):
    """Map category strings to crypto / forex / equity."""
    c = str(raw).lower().strip()
    if c in ("crypto", "on-chain", "futures"):
        return "crypto"
    if c in ("forex",):
        return "forex"
    if c in ("equity", "stock", "etf", "bond", "commodity"):
        return "equity"
    return c


def _split_into_buckets(picks, n_buckets):
    """
    Sort picks by score ascending and split into *n_buckets* roughly equal
    groups.  Bucket 1 = lowest scores, bucket N = highest scores.
    """
    picks_sorted = sorted(picks, key=lambda p: p["score"])
    bucket_size = max(1, len(picks_sorted) // n_buckets)
    buckets = []
    for i in range(n_buckets):
        start = i * bucket_size
        if i == n_buckets - 1:
            # last bucket gets the remainder
            end = len(picks_sorted)
        else:
            end = start + bucket_size
        buckets.append(picks_sorted[start:end])
    return buckets


def _compute_bucket_stats(bucket):
    """Compute aggregate stats for a single bucket of picks."""
    if not bucket:
        return {
            "count": 0,
            "wr": 0.0,
            "avg_pnl": 0.0,
            "profit_factor": 0.0,
            "avg_confidence": 0.0,
            "avg_score": 0.0,
        }

    wins = sum(1 for p in bucket if p["won"])
    wr = wins / len(bucket) if bucket else 0.0

    pnls = [p["pnl_pct"] for p in bucket]
    avg_pnl = sum(pnls) / len(pnls) if pnls else 0.0

    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (
        float("inf") if gross_profit > 0 else 0.0
    )

    avg_conf = sum(p["confidence"] for p in bucket) / len(bucket)
    avg_score = sum(p["score"] for p in bucket) / len(bucket)

    return {
        "count": len(bucket),
        "wr": round(wr, 4),
        "avg_pnl": round(avg_pnl, 4),
        "profit_factor": round(profit_factor, 4) if profit_factor != float("inf") else 999.0,
        "avg_confidence": round(avg_conf, 4),
        "avg_score": round(avg_score, 4),
    }


def _spearman_correlation(x, y):
    """
    Compute Spearman rank correlation between two equal-length sequences.
    Pure stdlib implementation.
    """
    n = len(x)
    if n < 2:
        return 0.0

    def _rank(seq):
        indexed = sorted(enumerate(seq), key=lambda t: t[1])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and indexed[j + 1][1] == indexed[j][1]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1.0  # 1-based average rank
            for k in range(i, j + 1):
                ranks[indexed[k][0]] = avg_rank
            i = j + 1
        return ranks

    rx = _rank(x)
    ry = _rank(y)

    mean_rx = sum(rx) / n
    mean_ry = sum(ry) / n

    cov = sum((a - mean_rx) * (b - mean_ry) for a, b in zip(rx, ry))
    std_x = math.sqrt(sum((a - mean_rx) ** 2 for a in rx))
    std_y = math.sqrt(sum((b - mean_ry) ** 2 for b in ry))

    if std_x == 0 or std_y == 0:
        return 0.0
    return cov / (std_x * std_y)


def _compute_separation_metrics(bucket_stats):
    """Compute separation metrics from an ordered list of bucket stats."""
    if len(bucket_stats) < 2:
        return {
            "top_bottom_wr_gap": 0.0,
            "monotonicity": 0.0,
            "top_decile_pf": 0.0,
            "bottom_decile_pf": 0.0,
            "information_ratio": 0.0,
        }

    top = bucket_stats[-1]
    bottom = bucket_stats[0]

    wr_gap = top["wr"] - bottom["wr"]

    # Monotonicity: Spearman correlation of bucket rank vs WR
    ranks = list(range(1, len(bucket_stats) + 1))
    wrs = [b["wr"] for b in bucket_stats]
    monotonicity = _spearman_correlation(ranks, wrs)

    top_pf = top["profit_factor"]
    bottom_pf = bottom["profit_factor"]

    # Information ratio: (top avg PnL - bottom avg PnL) / stdev of bucket PnLs
    bucket_avg_pnls = [b["avg_pnl"] for b in bucket_stats]
    if len(bucket_avg_pnls) > 1:
        mean_pnl = sum(bucket_avg_pnls) / len(bucket_avg_pnls)
        variance = sum((x - mean_pnl) ** 2 for x in bucket_avg_pnls) / (len(bucket_avg_pnls) - 1)
        stdev = math.sqrt(variance) if variance > 0 else 0.001
    else:
        stdev = 0.001
    info_ratio = (top["avg_pnl"] - bottom["avg_pnl"]) / stdev

    return {
        "top_bottom_wr_gap": round(wr_gap, 4),
        "monotonicity": round(monotonicity, 4),
        "top_decile_pf": round(top_pf, 4),
        "bottom_decile_pf": round(bottom_pf, 4),
        "information_ratio": round(info_ratio, 4),
    }


def _determine_verdict(metrics):
    """
    STRONG_SEPARATION: gap > 20% AND monotonicity > 0.6
    WEAK_SEPARATION:   gap > 10%
    INVERTED:          D1 WR > D10 WR (negative gap)
    NO_SEPARATION:     otherwise
    """
    gap = metrics["top_bottom_wr_gap"]
    mono = metrics["monotonicity"]

    if gap < 0:
        return "INVERTED"
    if gap > 0.20 and mono > 0.6:
        return "STRONG_SEPARATION"
    if gap > 0.10:
        return "WEAK_SEPARATION"
    return "NO_SEPARATION"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_decile_test(closed_picks_path="alpha_engine/data/closed_picks.json"):
    """
    Split scored picks into 10 deciles and compute stats per decile.
    Returns (decile_results, separation_metrics).
    """
    picks = _load_scored_picks(closed_picks_path)
    if len(picks) < 10:
        return [], {
            "top_bottom_wr_gap": 0.0,
            "monotonicity": 0.0,
            "top_decile_pf": 0.0,
            "bottom_decile_pf": 0.0,
            "information_ratio": 0.0,
        }

    buckets = _split_into_buckets(picks, 10)
    results = []
    for i, bucket in enumerate(buckets, 1):
        stats = _compute_bucket_stats(bucket)
        stats["decile"] = i
        results.append(stats)

    metrics = _compute_separation_metrics(results)
    return results, metrics


def run_quintile_test(closed_picks_path="alpha_engine/data/closed_picks.json"):
    """
    Same as decile test but with 5 buckets (Q1-Q5).
    Better for smaller samples (<100 picks per decile).
    """
    picks = _load_scored_picks(closed_picks_path)
    if len(picks) < 5:
        return [], {
            "top_bottom_wr_gap": 0.0,
            "monotonicity": 0.0,
            "top_decile_pf": 0.0,
            "bottom_decile_pf": 0.0,
            "information_ratio": 0.0,
        }

    buckets = _split_into_buckets(picks, 5)
    results = []
    for i, bucket in enumerate(buckets, 1):
        stats = _compute_bucket_stats(bucket)
        stats["quintile"] = i
        results.append(stats)

    metrics = _compute_separation_metrics(results)
    return results, metrics


def test_by_regime(closed_picks_path="alpha_engine/data/closed_picks.json"):
    """Run decile test separately for BULL, BEAR, NEUTRAL regime picks."""
    picks = _load_scored_picks(closed_picks_path)
    regime_groups = {}
    for p in picks:
        regime_groups.setdefault(p["regime"], []).append(p)

    results = {}
    for regime, group in sorted(regime_groups.items()):
        if len(group) < 5:
            results[regime] = {
                "count": len(group),
                "bucket_results": [],
                "separation_metrics": None,
                "verdict": "INSUFFICIENT_DATA",
            }
            continue

        n_buckets = 10 if len(group) >= 30 else 5
        buckets = _split_into_buckets(group, n_buckets)
        bucket_stats = []
        for i, bucket in enumerate(buckets, 1):
            stats = _compute_bucket_stats(bucket)
            stats["bucket"] = i
            bucket_stats.append(stats)

        metrics = _compute_separation_metrics(bucket_stats)
        verdict = _determine_verdict(metrics)

        results[regime] = {
            "count": len(group),
            "n_buckets": n_buckets,
            "bucket_results": bucket_stats,
            "separation_metrics": metrics,
            "verdict": verdict,
        }

    return results


def test_by_asset_class(closed_picks_path="alpha_engine/data/closed_picks.json"):
    """Run decile test separately for crypto, forex, equity."""
    picks = _load_scored_picks(closed_picks_path)
    class_groups = {}
    for p in picks:
        class_groups.setdefault(p["category"], []).append(p)

    results = {}
    for asset_class, group in sorted(class_groups.items()):
        if len(group) < 5:
            results[asset_class] = {
                "count": len(group),
                "bucket_results": [],
                "separation_metrics": None,
                "verdict": "INSUFFICIENT_DATA",
            }
            continue

        n_buckets = 10 if len(group) >= 30 else 5
        buckets = _split_into_buckets(group, n_buckets)
        bucket_stats = []
        for i, bucket in enumerate(buckets, 1):
            stats = _compute_bucket_stats(bucket)
            stats["bucket"] = i
            bucket_stats.append(stats)

        metrics = _compute_separation_metrics(bucket_stats)
        verdict = _determine_verdict(metrics)

        results[asset_class] = {
            "count": len(group),
            "n_buckets": n_buckets,
            "bucket_results": bucket_stats,
            "separation_metrics": metrics,
            "verdict": verdict,
        }

    return results


def generate_report(closed_picks_path="alpha_engine/data/closed_picks.json"):
    """
    Main entry point: runs all tests, outputs a structured JSON report.
    Saves to data/decile_test.json.
    """
    picks = _load_scored_picks(closed_picks_path)
    total_scored = len(picks)

    decile_results, decile_metrics = run_decile_test(closed_picks_path)
    quintile_results, quintile_metrics = run_quintile_test(closed_picks_path)
    regime_breakdown = test_by_regime(closed_picks_path)
    asset_class_breakdown = test_by_asset_class(closed_picks_path)

    # Use quintile metrics if sample too small for deciles
    primary_metrics = decile_metrics if total_scored >= 100 else quintile_metrics
    verdict = _determine_verdict(primary_metrics)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_scored_picks": total_scored,
        "decile_results": decile_results,
        "quintile_results": quintile_results,
        "separation_metrics": primary_metrics,
        "regime_breakdown": regime_breakdown,
        "asset_class_breakdown": asset_class_breakdown,
        "verdict": verdict,
    }

    # Save report
    data_dir = os.path.join(os.path.dirname(closed_picks_path))
    if not data_dir:
        data_dir = "data"
    output_path = os.path.join(data_dir, "decile_test.json")

    os.makedirs(data_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Decile separation report saved to {output_path}")
    print(f"  Total scored picks: {total_scored}")
    print(f"  Verdict: {verdict}")
    print(f"  Top-Bottom WR gap: {primary_metrics['top_bottom_wr_gap']:.1%}")
    print(f"  Monotonicity: {primary_metrics['monotonicity']:.4f}")
    print(f"  Top decile PF: {primary_metrics['top_decile_pf']:.2f}")
    print(f"  Bottom decile PF: {primary_metrics['bottom_decile_pf']:.2f}")
    print(f"  Information ratio: {primary_metrics['information_ratio']:.2f}")

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "alpha_engine/data/closed_picks.json"
    generate_report(path)
