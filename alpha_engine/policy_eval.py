"""
policy_eval.py — 7-day A/B evaluation pipeline for policy changes.

Loads dashboard_payload.json, slices closed picks into pre/post windows
around last_policy_change_at, computes trading metrics per asset class,
runs significance tests, and outputs policy_eval_result.json.
"""

import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

# Ensure parent is on path for stat_tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from alpha_engine.stat_tests import (
    welch_t_test,
    two_proportion_z_test,
    bonferroni_correction,
    var_cvar,
    profit_factor,
    sharpe_ratio,
    wilson_score_interval,
    bootstrap_ci,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
EVAL_WINDOW_DAYS = 7
SIGNIFICANCE_ALPHA = 0.05


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_iso(ts: str) -> datetime:
    """Parse ISO-8601 timestamp, handling Z suffix."""
    ts = ts.replace("Z", "+00:00")
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    # Fallback: dateutil-like manual parse
    raise ValueError(f"Cannot parse timestamp: {ts}")


def _safe_mean(vals: List[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _safe_median(vals: List[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    if n % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2.0
    return s[mid]


def _safe_std(vals: List[float]) -> float:
    if len(vals) < 2:
        return 0.0
    m = _safe_mean(vals)
    return math.sqrt(sum((x - m) ** 2 for x in vals) / (len(vals) - 1))


# ---------------------------------------------------------------------------
# Core evaluation
# ---------------------------------------------------------------------------

def load_payload(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)


def slice_picks(
    picks: List[Dict[str, Any]],
    change_at: datetime,
    window_days: int = EVAL_WINDOW_DAYS,
) -> Tuple[List[Dict], List[Dict]]:
    """Split picks into pre and post windows around policy change."""
    pre_start = change_at - timedelta(days=window_days)
    pre_end = change_at
    post_start = change_at
    post_end = change_at + timedelta(days=window_days)

    pre, post = [], []
    for p in picks:
        closed_at = p.get("closed_at") or p.get("exit_time") or p.get("timestamp")
        if not closed_at:
            continue
        try:
            t = _parse_iso(closed_at)
        except (ValueError, TypeError):
            continue

        if pre_start <= t < pre_end:
            pre.append(p)
        elif post_start <= t < post_end:
            post.append(p)

    return pre, post


def extract_pnl(pick: Dict[str, Any]) -> Optional[float]:
    """Extract PnL from a pick dict, trying common field names."""
    for key in ("pnl", "pnl_pct", "return_pct", "return", "pnl_percent"):
        val = pick.get(key)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                continue
    # Try computing from entry/exit prices
    entry = pick.get("entry_price") or pick.get("entry")
    exit_ = pick.get("exit_price") or pick.get("exit")
    side = pick.get("side", "long")
    if entry is not None and exit_ is not None:
        try:
            entry, exit_ = float(entry), float(exit_)
            if side == "short":
                return (entry - exit_) / entry
            return (exit_ - entry) / entry
        except (ValueError, TypeError, ZeroDivisionError):
            pass
    return None


def group_by_asset_class(
    picks: List[Dict[str, Any]]
) -> Dict[str, List[float]]:
    """Group picks by asset_class, returning dict of {asset_class: [pnl]}."""
    groups: Dict[str, List[float]] = {}
    for p in picks:
        ac = p.get("asset_class") or p.get("asset") or p.get("symbol") or "UNKNOWN"
        pnl = extract_pnl(p)
        if pnl is not None:
            groups.setdefault(ac, []).append(pnl)
    return groups


def compute_metrics(pnls: List[float]) -> Dict[str, Any]:
    """Compute standard trading metrics for a list of PnL values."""
    if not pnls:
        return {
            "n": 0,
            "win_rate": 0.0,
            "median_pnl": 0.0,
            "mean_pnl": 0.0,
            "profit_factor": 0.0,
            "sharpe": 0.0,
            "var_95": 0.0,
            "cvar_95": 0.0,
        }

    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = len(wins) / len(pnls) if pnls else 0.0

    gains_sum = sum(wins) if wins else 0.0
    losses_sum = abs(sum(losses)) if losses else 0.0
    pf = gains_sum / losses_sum if losses_sum > 0 else (float('inf') if gains_sum > 0 else 0.0)

    v, cv = var_cvar(pnls, confidence=0.95)

    return {
        "n": len(pnls),
        "win_rate": win_rate,
        "median_pnl": _safe_median(pnls),
        "mean_pnl": _safe_mean(pnls),
        "profit_factor": pf if pf != float('inf') else 999.99,
        "sharpe": sharpe_ratio(pnls),
        "var_95": v,
        "cvar_95": cv,
    }


def evaluate_significance(
    pre_pnls: List[float],
    post_pnls: List[float],
    num_comparisons: int = 1,
) -> Dict[str, Any]:
    """Run significance tests comparing pre vs post PnL distributions."""
    adj_alpha = bonferroni_correction(SIGNIFICANCE_ALPHA, num_comparisons)

    pre_wins = sum(1 for p in pre_pnls if p > 0)
    post_wins = sum(1 for p in post_pnls if p > 0)

    results = {}

    # Two-proportion z-test on win rates
    z_stat, p_val, sig = two_proportion_z_test(
        len(pre_pnls), pre_wins, len(post_pnls), post_wins
    )
    results["win_rate_z_test"] = {
        "z_stat": z_stat,
        "p_value": p_val,
        "significant": p_val < adj_alpha,
    }

    # Welch's t-test on PnL means
    pre_mean = _safe_mean(pre_pnls)
    post_mean = _safe_mean(post_pnls)
    pre_std = _safe_std(pre_pnls)
    post_std = _safe_std(post_pnls)

    t_stat, p_val_t, df, sig_t = welch_t_test(
        pre_mean, pre_std, len(pre_pnls) if len(pre_pnls) >= 2 else 2,
        post_mean, post_std, len(post_pnls) if len(post_pnls) >= 2 else 2,
    )
    results["pnl_t_test"] = {
        "t_stat": t_stat,
        "p_value": p_val_t,
        "df": df,
        "significant": p_val_t < adj_alpha,
    }

    results["adjusted_alpha"] = adj_alpha

    return results


def compute_overall_verdict(
    asset_results: Dict[str, Dict[str, Any]]
) -> str:
    """Determine overall verdict from per-asset-class results.

    IMPROVED: majority of asset classes show significant improvement (higher WR/PF, lower VaR)
    DEGRADED: majority show significant degradation
    NEUTRAL: otherwise
    """
    if not asset_results:
        return "NEUTRAL"

    improved = 0
    degraded = 0
    total = 0

    for ac, res in asset_results.items():
        pre = res.get("pre_metrics", {})
        post = res.get("post_metrics", {})
        sig = res.get("significance", {})

        if pre.get("n", 0) == 0 or post.get("n", 0) == 0:
            continue

        total += 1

        wr_improved = post.get("win_rate", 0) > pre.get("win_rate", 0)
        pf_improved = post.get("profit_factor", 0) > pre.get("profit_factor", 0)
        var_improved = post.get("var_95", 0) <= pre.get("var_95", 0)

        wr_sig = sig.get("win_rate_z_test", {}).get("significant", False)
        pnl_sig = sig.get("pnl_t_test", {}).get("significant", False)
        any_sig = wr_sig or pnl_sig

        score = (1 if wr_improved else -1) + (1 if pf_improved else -1) + (1 if var_improved else -1)

        if score >= 1 and any_sig:
            improved += 1
        elif score <= -1 and any_sig:
            degraded += 1

    if total == 0:
        return "NEUTRAL"
    if improved > total / 2:
        return "IMPROVED"
    if degraded > total / 2:
        return "DEGRADED"
    return "NEUTRAL"


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_evaluation(
    payload_path: str = "dashboard_payload.json",
    output_path: str = "policy_eval_result.json",
) -> Dict[str, Any]:
    """Run the full 7-day A/B policy evaluation pipeline."""
    payload = load_payload(payload_path)

    change_at_str = payload.get("last_policy_change_at")
    if not change_at_str:
        raise ValueError("payload missing 'last_policy_change_at'")

    change_at = _parse_iso(change_at_str)
    picks = payload.get("closed_picks") or payload.get("picks") or []

    pre_picks, post_picks = slice_picks(picks, change_at)

    pre_groups = group_by_asset_class(pre_picks)
    post_groups = group_by_asset_class(post_picks)

    all_classes = sorted(set(list(pre_groups.keys()) + list(post_groups.keys())))

    # Count total comparisons for Bonferroni
    num_comparisons = max(1, len(all_classes) * 2)  # WR z-test + t-test per class

    asset_results = {}
    for ac in all_classes:
        pre_pnls = pre_groups.get(ac, [])
        post_pnls = post_groups.get(ac, [])

        pre_metrics = compute_metrics(pre_pnls)
        post_metrics = compute_metrics(post_pnls)
        sig = evaluate_significance(pre_pnls, post_pnls, num_comparisons)

        asset_results[ac] = {
            "pre_metrics": pre_metrics,
            "post_metrics": post_metrics,
            "significance": sig,
        }

    verdict = compute_overall_verdict(asset_results)

    result = {
        "policy_change_at": change_at_str,
        "eval_window_days": EVAL_WINDOW_DAYS,
        "pre_picks_count": len(pre_picks),
        "post_picks_count": len(post_picks),
        "asset_classes": asset_results,
        "verdict": verdict,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, default=str)

    print(f"Policy evaluation complete. Verdict: {verdict}")
    print(f"  Pre-window picks: {len(pre_picks)}")
    print(f"  Post-window picks: {len(post_picks)}")
    print(f"  Asset classes: {', '.join(all_classes)}")
    print(f"  Results written to: {output_path}")

    return result


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="7-day A/B policy evaluation")
    parser.add_argument("--input", default="dashboard_payload.json",
                        help="Path to dashboard payload JSON")
    parser.add_argument("--output", default="policy_eval_result.json",
                        help="Path to write evaluation results")
    args = parser.parse_args()

    run_evaluation(args.input, args.output)
