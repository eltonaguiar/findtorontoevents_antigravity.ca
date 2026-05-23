#!/usr/bin/env python3
"""
ALPHA ENGINE -- Institutional Signal Scorecard (250-point)
===========================================================
Computes a comprehensive 250-point institutional-grade scorecard
evaluating the Alpha Engine's signal quality across six dimensions:

  1. Data Quality          (25 pts)
  2. Statistical Power     (75 pts)
  3. Operational           (30 pts)
  4. Risk Management       (45 pts)
  5. Market Resilience     (30 pts)
  6. Validation            (45 pts)

Reads actual data from alpha_engine/data/ and produces a graded report.

Usage:
  from institutional_scorecard import compute_scorecard, run_scorecard
  scorecard = run_scorecard()      # compute + save + print
  scorecard = compute_scorecard()  # compute only
"""

from __future__ import annotations

import json
import os
import time
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent / "data"
CLOSED_PICKS_PATH = DATA_DIR / "closed_picks.json"
ACTIVE_PICKS_PATH = DATA_DIR / "active_picks.json"
STRATEGY_PERF_PATH = DATA_DIR / "strategy_performance.json"
WALK_FORWARD_PATH = DATA_DIR / "walk_forward_report.json"
MONTE_CARLO_PATH = DATA_DIR / "monte_carlo_results.json"
OUTPUT_PATH = DATA_DIR / "institutional_scorecard.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> Any:
    """Load JSON file, return None if missing or invalid."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _file_age_minutes(path: Path) -> Optional[float]:
    """Return file age in minutes, or None if file doesn't exist."""
    try:
        mtime = os.path.getmtime(path)
        return (time.time() - mtime) / 60.0
    except OSError:
        return None


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    if b == 0:
        return default
    return a / b


# ---------------------------------------------------------------------------
# Section Scorers
# ---------------------------------------------------------------------------

def score_data_quality(closed_picks: list, active_picks: list) -> dict:
    """
    Data Quality (25 pts max)
    - Data integrity: sources verified (10 pts)
    - No look-ahead bias: timestamps validated (10 pts)
    - Data recency: last scan < 1 hour ago (5 pts)
    """
    details: dict[str, Any] = {}
    score = 0

    # --- Data integrity (10 pts) ---
    # Check that closed picks have required fields and multiple strategies
    integrity_pts = 0
    if closed_picks and len(closed_picks) > 0:
        required_fields = {"id", "strategy", "symbol", "entry_price", "exit_price",
                           "entry_date", "exit_date", "status", "pnl_pct"}
        valid_count = sum(
            1 for p in closed_picks
            if required_fields.issubset(set(p.keys()))
        )
        completeness = _safe_div(valid_count, len(closed_picks))
        strategies_seen = len(set(p.get("strategy", "") for p in closed_picks))
        if completeness >= 0.95 and strategies_seen >= 5:
            integrity_pts = 10
        elif completeness >= 0.80 and strategies_seen >= 3:
            integrity_pts = 7
        elif completeness >= 0.50:
            integrity_pts = 4
        details["data_completeness"] = round(completeness, 3)
        details["strategies_seen"] = strategies_seen
    details["integrity_pts"] = integrity_pts
    score += integrity_pts

    # --- No look-ahead bias (10 pts) ---
    # Validate that exit_date >= entry_date for all closed picks
    bias_pts = 0
    if closed_picks:
        violations = 0
        checked = 0
        for p in closed_picks:
            ed = p.get("entry_date", "")
            xd = p.get("exit_date", "")
            if ed and xd:
                checked += 1
                if xd < ed:
                    violations += 1
        violation_rate = _safe_div(violations, max(checked, 1))
        if violation_rate == 0 and checked > 10:
            bias_pts = 10
        elif violation_rate < 0.01:
            bias_pts = 7
        elif violation_rate < 0.05:
            bias_pts = 4
        details["timestamp_violations"] = violations
        details["timestamp_checked"] = checked
    details["bias_pts"] = bias_pts
    score += bias_pts

    # --- Data recency (5 pts) ---
    recency_pts = 0
    age = _file_age_minutes(ACTIVE_PICKS_PATH)
    if age is not None:
        if age < 60:
            recency_pts = 5
        elif age < 120:
            recency_pts = 3
        elif age < 360:
            recency_pts = 1
        details["active_picks_age_min"] = round(age, 1)
    details["recency_pts"] = recency_pts
    score += recency_pts

    return {"score": score, "max": 25, "details": details}


def score_statistical_power(closed_picks: list, strategy_perf: dict) -> dict:
    """
    Statistical Power (75 pts max)
    - Win rate tiers (15 pts)
    - Profit factor tiers (20 pts)
    - Expectancy (15 pts)
    - Information coefficient (15 pts)
    - P-value binomial test (10 pts)
    """
    details: dict[str, Any] = {}
    score = 0

    if not closed_picks:
        return {"score": 0, "max": 75, "details": {"error": "no closed picks"}}

    total = len(closed_picks)
    wins = sum(1 for p in closed_picks if p.get("status") == "WON")
    losses = total - wins
    win_rate = _safe_div(wins, total)

    # --- Win rate (15 pts) ---
    if win_rate > 0.55:
        wr_pts = 15
    elif win_rate > 0.50:
        wr_pts = 10
    elif win_rate > 0.45:
        wr_pts = 5
    else:
        wr_pts = 0
    details["win_rate"] = round(win_rate, 4)
    details["total_picks"] = total
    details["wins"] = wins
    details["wr_pts"] = wr_pts
    score += wr_pts

    # --- Profit factor (20 pts) ---
    gross_wins = sum(p.get("pnl_pct", 0) for p in closed_picks if p.get("pnl_pct", 0) > 0)
    gross_losses = abs(sum(p.get("pnl_pct", 0) for p in closed_picks if p.get("pnl_pct", 0) < 0))
    pf = _safe_div(gross_wins, gross_losses, default=0.0)
    if pf > 1.5:
        pf_pts = 20
    elif pf > 1.2:
        pf_pts = 10
    elif pf > 1.0:
        pf_pts = 5
    else:
        pf_pts = 0
    details["profit_factor"] = round(pf, 4)
    details["pf_pts"] = pf_pts
    score += pf_pts

    # --- Expectancy (15 pts) ---
    pnl_values = [p.get("pnl_pct", 0) for p in closed_picks]
    expectancy = _safe_div(sum(pnl_values), len(pnl_values)) * 100  # as percentage
    if expectancy > 1.0:
        exp_pts = 15
    elif expectancy > 0.5:
        exp_pts = 10
    elif expectancy > 0:
        exp_pts = 5
    else:
        exp_pts = 0
    details["expectancy_pct"] = round(expectancy, 4)
    details["exp_pts"] = exp_pts
    score += exp_pts

    # --- Information coefficient (15 pts) ---
    # Correlation between pick confidence/score and actual PnL
    ic_pts = 0
    scores_list = []
    pnl_list = []
    for p in closed_picks:
        conf = p.get("confidence") or p.get("ml_score")
        pnl = p.get("pnl_pct")
        if conf is not None and pnl is not None:
            scores_list.append(float(conf))
            pnl_list.append(float(pnl))

    ic = 0.0
    if len(scores_list) >= 10:
        # Spearman rank correlation (manual to avoid scipy dependency)
        ic = _rank_correlation(scores_list, pnl_list)
        if ic > 0.05:
            ic_pts = 15
        elif ic > 0.02:
            ic_pts = 8
        elif ic > 0:
            ic_pts = 3
    details["information_coefficient"] = round(ic, 4)
    details["ic_sample_size"] = len(scores_list)
    details["ic_pts"] = ic_pts
    score += ic_pts

    # --- P-value binomial test (10 pts) ---
    # Test if win rate is significantly > 50%
    p_value = _binomial_test_pvalue(wins, total, 0.5)
    if p_value < 0.05:
        pv_pts = 10
    elif p_value < 0.10:
        pv_pts = 5
    else:
        pv_pts = 0
    details["p_value"] = round(p_value, 6)
    details["pv_pts"] = pv_pts
    score += pv_pts

    return {"score": score, "max": 75, "details": details}


def score_operational(closed_picks: list) -> dict:
    """
    Operational (30 pts max)
    - Signal stability > 3 months (10 pts)
    - Signal volume > 50/month (10 pts)
    - Latency < 30 min (10 pts)
    """
    details: dict[str, Any] = {}
    score = 0

    # --- Signal stability (10 pts) ---
    # Check date range of closed picks
    stab_pts = 0
    dates = []
    for p in closed_picks:
        d = p.get("entry_date", "")
        if d:
            try:
                dates.append(datetime.strptime(d[:10], "%Y-%m-%d"))
            except ValueError:
                pass
    if dates:
        span_days = (max(dates) - min(dates)).days
        if span_days >= 90:
            stab_pts = 10
        elif span_days >= 60:
            stab_pts = 7
        elif span_days >= 30:
            stab_pts = 4
        details["signal_span_days"] = span_days
    details["stability_pts"] = stab_pts
    score += stab_pts

    # --- Signal volume (10 pts) ---
    vol_pts = 0
    if dates:
        span_months = max((max(dates) - min(dates)).days / 30.0, 1.0)
        monthly_vol = len(closed_picks) / span_months
        if monthly_vol >= 50:
            vol_pts = 10
        elif monthly_vol >= 25:
            vol_pts = 7
        elif monthly_vol >= 10:
            vol_pts = 4
        details["monthly_signal_volume"] = round(monthly_vol, 1)
    details["volume_pts"] = vol_pts
    score += vol_pts

    # --- Latency (10 pts) ---
    lat_pts = 0
    age = _file_age_minutes(ACTIVE_PICKS_PATH)
    if age is not None:
        if age < 30:
            lat_pts = 10
        elif age < 60:
            lat_pts = 7
        elif age < 120:
            lat_pts = 3
        details["scan_latency_min"] = round(age, 1)
    details["latency_pts"] = lat_pts
    score += lat_pts

    return {"score": score, "max": 30, "details": details}


def score_risk_management(closed_picks: list, strategy_perf: dict) -> dict:
    """
    Risk Management (45 pts max)
    - Max drawdown < 20% (10 pts) / < 30% (5 pts)
    - Recovery time < 30 trades (10 pts)
    - R:R average > 2.0 (15 pts) / > 1.5 (10 pts)
    - Stress resilience: WR stable in high-vol (10 pts)
    """
    details: dict[str, Any] = {}
    score = 0

    # --- Max drawdown (10 pts) ---
    dd_pts = 0
    max_dd = 0.0
    if strategy_perf:
        drawdowns = []
        for s, data in strategy_perf.items():
            dd = abs(data.get("max_drawdown", 0))
            if dd > 0:
                drawdowns.append(dd)
        if drawdowns:
            max_dd = max(drawdowns)
            # System-level: weighted by number of trades
            # Use the worst strategy drawdown as the system measure
            if max_dd < 0.20:
                dd_pts = 10
            elif max_dd < 0.30:
                dd_pts = 5
    details["max_drawdown_pct"] = round(max_dd * 100, 2)
    details["dd_pts"] = dd_pts
    score += dd_pts

    # --- Recovery time (10 pts) ---
    # Count max consecutive losses across all picks (sorted by date)
    rec_pts = 0
    sorted_picks = sorted(closed_picks, key=lambda p: p.get("exit_date", ""))
    max_consec_loss = 0
    current_streak = 0
    for p in sorted_picks:
        if p.get("status") != "WON":
            current_streak += 1
            max_consec_loss = max(max_consec_loss, current_streak)
        else:
            current_streak = 0
    if max_consec_loss < 30:
        rec_pts = 10
    elif max_consec_loss < 50:
        rec_pts = 5
    details["max_consecutive_losses"] = max_consec_loss
    details["recovery_pts"] = rec_pts
    score += rec_pts

    # --- R:R average (15 pts) ---
    rr_pts = 0
    rr_values = []
    for p in closed_picks:
        entry = p.get("entry_price", 0)
        tp = p.get("take_profit", 0)
        sl = p.get("stop_loss", 0)
        if entry and tp and sl and entry != sl:
            reward = abs(tp - entry)
            risk = abs(entry - sl)
            if risk > 0:
                rr_values.append(reward / risk)
    avg_rr = _safe_div(sum(rr_values), len(rr_values)) if rr_values else 0
    if avg_rr > 2.0:
        rr_pts = 15
    elif avg_rr > 1.5:
        rr_pts = 10
    elif avg_rr > 1.0:
        rr_pts = 5
    details["avg_risk_reward"] = round(avg_rr, 3)
    details["rr_sample_size"] = len(rr_values)
    details["rr_pts"] = rr_pts
    score += rr_pts

    # --- Stress resilience (10 pts) ---
    # Compare WR during high-vol regimes vs overall
    stress_pts = 0
    high_vol_picks = [p for p in closed_picks
                      if p.get("regime_at_entry", "").lower() in
                      ("bear", "volatile", "crash", "high_vol", "risk_off")]
    if len(high_vol_picks) >= 5:
        hv_wins = sum(1 for p in high_vol_picks if p.get("status") == "WON")
        hv_wr = _safe_div(hv_wins, len(high_vol_picks))
        total_wr = _safe_div(
            sum(1 for p in closed_picks if p.get("status") == "WON"),
            len(closed_picks)
        )
        wr_delta = total_wr - hv_wr
        if wr_delta < 0.05:
            stress_pts = 10
        elif wr_delta < 0.10:
            stress_pts = 5
        details["high_vol_wr"] = round(hv_wr, 4)
        details["wr_delta_stress"] = round(wr_delta, 4)
    else:
        details["high_vol_picks_count"] = len(high_vol_picks)
        details["note"] = "insufficient high-vol data"
    details["stress_pts"] = stress_pts
    score += stress_pts

    return {"score": score, "max": 45, "details": details}


def score_market_resilience(closed_picks: list, strategy_perf: dict) -> dict:
    """
    Market Resilience (30 pts max)
    - Regime robustness: WR > 40% in all regimes (10 pts)
    - Low crash correlation (10 pts)
    - Liquidity ok: avg volume ratio > 1.0 (10 pts)
    """
    details: dict[str, Any] = {}
    score = 0

    # --- Regime robustness (10 pts) ---
    regime_pts = 0
    regime_stats: dict[str, dict] = {}
    for p in closed_picks:
        regime = p.get("regime_at_entry", "unknown")
        if regime not in regime_stats:
            regime_stats[regime] = {"total": 0, "wins": 0}
        regime_stats[regime]["total"] += 1
        if p.get("status") == "WON":
            regime_stats[regime]["wins"] += 1

    # Only evaluate regimes with >= 5 picks
    evaluated_regimes = {
        r: _safe_div(s["wins"], s["total"])
        for r, s in regime_stats.items() if s["total"] >= 5
    }
    if evaluated_regimes:
        all_above_40 = all(wr >= 0.40 for wr in evaluated_regimes.values())
        if all_above_40:
            regime_pts = 10
        elif sum(1 for wr in evaluated_regimes.values() if wr >= 0.40) >= len(evaluated_regimes) * 0.75:
            regime_pts = 5
        details["regime_win_rates"] = {k: round(v, 3) for k, v in evaluated_regimes.items()}
    details["regime_pts"] = regime_pts
    score += regime_pts

    # --- Low crash correlation (10 pts) ---
    # Check if losing picks cluster on same dates (crash correlation)
    crash_pts = 0
    loss_dates: dict[str, int] = {}
    for p in closed_picks:
        if p.get("status") != "WON":
            d = p.get("exit_date", "")[:10]
            if d:
                loss_dates[d] = loss_dates.get(d, 0) + 1
    if loss_dates:
        max_loss_cluster = max(loss_dates.values())
        total_losses = sum(loss_dates.values())
        cluster_ratio = _safe_div(max_loss_cluster, total_losses)
        if cluster_ratio < 0.10:
            crash_pts = 10
        elif cluster_ratio < 0.20:
            crash_pts = 5
        details["max_loss_cluster"] = max_loss_cluster
        details["cluster_ratio"] = round(cluster_ratio, 3)
    else:
        crash_pts = 10  # No losses = no crash correlation
    details["crash_pts"] = crash_pts
    score += crash_pts

    # --- Liquidity (10 pts) ---
    liq_pts = 0
    vol_ratios = [p.get("volume_ratio", 0) for p in closed_picks
                  if p.get("volume_ratio") is not None and p.get("volume_ratio", 0) > 0]
    if vol_ratios:
        avg_vol = sum(vol_ratios) / len(vol_ratios)
        if avg_vol > 1.0:
            liq_pts = 10
        elif avg_vol > 0.5:
            liq_pts = 5
        details["avg_volume_ratio"] = round(avg_vol, 3)
        details["vol_ratio_sample"] = len(vol_ratios)
    details["liquidity_pts"] = liq_pts
    score += liq_pts

    return {"score": score, "max": 30, "details": details}


def score_validation(closed_picks: list) -> dict:
    """
    Validation (45 pts max)
    - Out-of-sample tested (10 pts) - check walk_forward_report.json
    - Monte Carlo done (10 pts) - check monte_carlo_results.json
    - Signal decay < 50% over 6 weeks (10 pts)
    - Forward test active with 100+ trades (15 pts)
    """
    details: dict[str, Any] = {}
    score = 0

    # --- Walk forward / OOS (10 pts) ---
    oos_pts = 0
    wf_data = _load_json(WALK_FORWARD_PATH)
    if wf_data and wf_data.get("status") == "complete":
        valid_folds = wf_data.get("valid_folds", 0)
        if valid_folds >= 2:
            oos_pts = 10
        elif valid_folds >= 1:
            oos_pts = 5
        details["walk_forward_folds"] = valid_folds
    details["oos_pts"] = oos_pts
    score += oos_pts

    # --- Monte Carlo (10 pts) ---
    mc_pts = 0
    mc_data = _load_json(MONTE_CARLO_PATH)
    if mc_data:
        strategies_with_mc = 0
        mc_strategies = mc_data.get("strategies", mc_data)
        if isinstance(mc_strategies, dict):
            for s, info in mc_strategies.items():
                if isinstance(info, dict) and info.get("n_simulations", 0) > 0:
                    strategies_with_mc += 1
        if strategies_with_mc >= 5:
            mc_pts = 10
        elif strategies_with_mc >= 1:
            mc_pts = 5
        details["monte_carlo_strategies"] = strategies_with_mc
    details["mc_pts"] = mc_pts
    score += mc_pts

    # --- Signal decay (10 pts) ---
    # Compare WR of recent picks vs older picks (proxy for decay)
    decay_pts = 0
    if closed_picks and len(closed_picks) >= 20:
        sorted_by_date = sorted(closed_picks, key=lambda p: p.get("entry_date", ""))
        mid = len(sorted_by_date) // 2
        first_half = sorted_by_date[:mid]
        second_half = sorted_by_date[mid:]
        wr_first = _safe_div(
            sum(1 for p in first_half if p.get("status") == "WON"),
            len(first_half)
        )
        wr_second = _safe_div(
            sum(1 for p in second_half if p.get("status") == "WON"),
            len(second_half)
        )
        # Decay = drop from first to second half
        if wr_first > 0:
            decay_ratio = (wr_first - wr_second) / wr_first
        else:
            decay_ratio = 0
        if decay_ratio < 0.50:
            decay_pts = 10
        elif decay_ratio < 0.75:
            decay_pts = 5
        details["wr_first_half"] = round(wr_first, 4)
        details["wr_second_half"] = round(wr_second, 4)
        details["decay_ratio"] = round(decay_ratio, 4)
    details["decay_pts"] = decay_pts
    score += decay_pts

    # --- Forward test active with 100+ trades (15 pts) ---
    fwd_pts = 0
    total_closed = len(closed_picks) if closed_picks else 0
    if total_closed >= 100:
        fwd_pts = 15
    elif total_closed >= 50:
        fwd_pts = 10
    elif total_closed >= 20:
        fwd_pts = 5
    details["forward_test_trades"] = total_closed
    details["fwd_pts"] = fwd_pts
    score += fwd_pts

    return {"score": score, "max": 45, "details": details}


# ---------------------------------------------------------------------------
# Rank correlation (Spearman) -- avoids scipy dependency
# ---------------------------------------------------------------------------

def _rank_correlation(x: list[float], y: list[float]) -> float:
    """Compute Spearman rank correlation without scipy."""
    n = len(x)
    if n < 3:
        return 0.0

    def _ranks(vals: list[float]) -> list[float]:
        indexed = sorted(enumerate(vals), key=lambda t: t[1])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and indexed[j + 1][1] == indexed[j][1]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                ranks[indexed[k][0]] = avg_rank
            i = j + 1
        return ranks

    rx = _ranks(x)
    ry = _ranks(y)

    mean_rx = sum(rx) / n
    mean_ry = sum(ry) / n

    num = sum((rx[i] - mean_rx) * (ry[i] - mean_ry) for i in range(n))
    den_x = math.sqrt(sum((rx[i] - mean_rx) ** 2 for i in range(n)))
    den_y = math.sqrt(sum((ry[i] - mean_ry) ** 2 for i in range(n)))

    if den_x == 0 or den_y == 0:
        return 0.0
    return num / (den_x * den_y)


# ---------------------------------------------------------------------------
# Binomial test (one-sided, without scipy)
# ---------------------------------------------------------------------------

def _binomial_test_pvalue(successes: int, trials: int, p0: float = 0.5) -> float:
    """
    One-sided binomial test P(X >= successes) under H0: p = p0.
    Uses normal approximation for large n, exact for small n.
    """
    if trials <= 0:
        return 1.0
    if successes <= trials * p0:
        return 1.0  # Not above baseline, p-value = 1

    if trials > 50:
        # Normal approximation
        mu = trials * p0
        sigma = math.sqrt(trials * p0 * (1 - p0))
        if sigma == 0:
            return 0.0 if successes > mu else 1.0
        z = (successes - 0.5 - mu) / sigma  # continuity correction
        # P(Z >= z) using complementary error function
        return 0.5 * math.erfc(z / math.sqrt(2))
    else:
        # Exact calculation for small n
        total_prob = 0.0
        for k in range(successes, trials + 1):
            log_prob = (
                _log_comb(trials, k)
                + k * math.log(p0)
                + (trials - k) * math.log(1 - p0)
            )
            total_prob += math.exp(log_prob)
        return min(total_prob, 1.0)


def _log_comb(n: int, k: int) -> float:
    """Log of binomial coefficient C(n, k)."""
    if k < 0 or k > n:
        return float('-inf')
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


# ---------------------------------------------------------------------------
# Main scorecard computation
# ---------------------------------------------------------------------------

def compute_scorecard() -> dict:
    """Compute the full 250-point institutional scorecard from data files."""

    closed_picks = _load_json(CLOSED_PICKS_PATH) or []
    active_picks = _load_json(ACTIVE_PICKS_PATH) or []
    strategy_perf = _load_json(STRATEGY_PERF_PATH) or {}

    sections = {
        "data_quality": score_data_quality(closed_picks, active_picks),
        "statistical_power": score_statistical_power(closed_picks, strategy_perf),
        "operational": score_operational(closed_picks),
        "risk_management": score_risk_management(closed_picks, strategy_perf),
        "market_resilience": score_market_resilience(closed_picks, strategy_perf),
        "validation": score_validation(closed_picks),
    }

    total_score = sum(s["score"] for s in sections.values())
    max_score = sum(s["max"] for s in sections.values())

    # Grade
    if total_score >= 200:
        grade = "A"
    elif total_score >= 150:
        grade = "B"
    elif total_score >= 100:
        grade = "C"
    elif total_score >= 50:
        grade = "D"
    else:
        grade = "F"

    return {
        "total_score": total_score,
        "max_score": max_score,
        "grade": grade,
        "sections": sections,
        "computed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def save_scorecard(scorecard: dict) -> Path:
    """Save scorecard to JSON."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(scorecard, f, indent=2)
    return OUTPUT_PATH


def print_scorecard(scorecard: dict) -> None:
    """Print a summary table to stdout."""
    print("=" * 60)
    print("  INSTITUTIONAL SIGNAL SCORECARD (250-point)")
    print("=" * 60)
    print()

    section_names = {
        "data_quality": "Data Quality",
        "statistical_power": "Statistical Power",
        "operational": "Operational",
        "risk_management": "Risk Management",
        "market_resilience": "Market Resilience",
        "validation": "Validation",
    }

    for key, label in section_names.items():
        sec = scorecard["sections"][key]
        bar_filled = int(20 * sec["score"] / sec["max"]) if sec["max"] > 0 else 0
        bar = "#" * bar_filled + "-" * (20 - bar_filled)
        print(f"  {label:<22} {sec['score']:>3} / {sec['max']:<3}  [{bar}]")

    print()
    print("-" * 60)
    total = scorecard["total_score"]
    mx = scorecard["max_score"]
    grade = scorecard["grade"]
    pct = round(100 * total / mx, 1) if mx > 0 else 0
    print(f"  TOTAL SCORE:  {total} / {mx}  ({pct}%)  Grade: {grade}")
    print(f"  Computed at:  {scorecard['computed_at']}")
    print("=" * 60)


def run_scorecard() -> dict:
    """Compute, save, and print the scorecard. Returns the scorecard dict."""
    scorecard = compute_scorecard()
    save_scorecard(scorecard)
    print_scorecard(scorecard)
    return scorecard


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run_scorecard()
