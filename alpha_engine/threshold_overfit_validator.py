#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Threshold Overfit Validator
============================
Walk-forward validation that tests whether the Strong Signal 5-Filter
scoring thresholds (R:R sweet spot, confidence band, stop distance) are
overfit to historical data.

Complements walk_forward_validator.py (ML model OOS) by focusing on the
static threshold parameters in strong_signal_filter.py.

Methodology:
  1. Train/test split: all except last 30 days vs last 30 days
  2. Per-threshold win-rate comparison (train vs test)
  3. Rolling 30-day window walk-forward across all data
  4. Overfit risk score 0-100

Output: alpha_engine/data/walk_forward_report.json

Usage:
    python -m alpha_engine.threshold_overfit_validator
    python alpha_engine/threshold_overfit_validator.py
"""

from __future__ import annotations

import json
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Locate data dir
# ---------------------------------------------------------------------------

_THIS_DIR = Path(__file__).resolve().parent
_DATA_DIR = _THIS_DIR / "data"
_CLOSED_PICKS_PATH = _DATA_DIR / "closed_picks.json"
_REPORT_PATH = _DATA_DIR / "walk_forward_report.json"

# ---------------------------------------------------------------------------
# Import thresholds from strong_signal_filter (graceful fallback)
# ---------------------------------------------------------------------------

if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

try:
    from strong_signal_filter import (
        RR_SWEET_LOW, RR_SWEET_HIGH,
        CONF_BEST_LOW, CONF_BEST_HIGH,
        STOP_OPTIMAL_LOW, STOP_OPTIMAL_HIGH,
        STRONG_SIGNAL_THRESHOLD,
        _compute_strategy_stats,
        compute_strong_signal_score,
    )
    _SSF_AVAILABLE = True
except ImportError:
    # Fallback constants matching strong_signal_filter.py
    RR_SWEET_LOW = 2.0
    RR_SWEET_HIGH = 2.5
    CONF_BEST_LOW = 0.60
    CONF_BEST_HIGH = 0.70
    STOP_OPTIMAL_LOW = 0.015
    STOP_OPTIMAL_HIGH = 0.03
    STRONG_SIGNAL_THRESHOLD = 25
    _SSF_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(date_str: str | None) -> datetime | None:
    """Parse ISO date string to datetime (UTC)."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def _pick_exit_date(pick: dict) -> datetime | None:
    """Best available date: exit_date > entry_date."""
    dt = _parse_date(pick.get("exit_date"))
    if dt:
        return dt
    return _parse_date(pick.get("entry_date"))


def _pick_rr(pick: dict) -> float:
    """Extract or compute risk:reward ratio."""
    rr = pick.get("risk_reward")
    if rr is not None:
        try:
            return float(rr)
        except (TypeError, ValueError):
            pass
    entry = pick.get("entry_price") or 0
    tp = pick.get("take_profit") or 0
    sl = pick.get("stop_loss") or 0
    if entry <= 0 or tp <= 0 or sl <= 0:
        return 0.0
    direction = (pick.get("signal_type") or pick.get("direction") or "BUY").upper()
    if direction in ("SELL", "SHORT"):
        reward = entry - tp
        risk = sl - entry
    else:
        reward = tp - entry
        risk = entry - sl
    return reward / risk if risk > 0 else 0.0


def _pick_stop_distance(pick: dict) -> float:
    """Stop distance as fraction of entry price."""
    entry = pick.get("entry_price") or 0
    sl = pick.get("stop_loss") or 0
    if entry <= 0 or sl <= 0:
        return 0.0
    return abs(entry - sl) / entry


def _pick_confidence(pick: dict) -> float:
    return float(pick.get("confidence") or 0)


def _is_won(pick: dict) -> bool:
    return (pick.get("status") or "").upper() == "WON"


def _is_resolved(pick: dict) -> bool:
    return (pick.get("status") or "").upper() in ("WON", "LOST")


def _win_rate(picks: list[dict]) -> float:
    """Win rate of resolved picks. Returns 0.0 if empty."""
    resolved = [p for p in picks if _is_resolved(p)]
    if not resolved:
        return 0.0
    return sum(1 for p in resolved if _is_won(p)) / len(resolved)


# ---------------------------------------------------------------------------
# Threshold filters (mirrors strong_signal_filter logic)
# ---------------------------------------------------------------------------

def _in_rr_sweet_spot(pick: dict) -> bool:
    rr = _pick_rr(pick)
    return RR_SWEET_LOW <= rr <= RR_SWEET_HIGH


def _in_confidence_band(pick: dict) -> bool:
    conf = _pick_confidence(pick)
    return CONF_BEST_LOW <= conf <= CONF_BEST_HIGH


def _in_stop_distance(pick: dict) -> bool:
    sd = _pick_stop_distance(pick)
    return STOP_OPTIMAL_LOW <= sd <= STOP_OPTIMAL_HIGH


def _passes_all_strong_filters(pick: dict, regime: str = "neutral",
                                closed_picks: list[dict] | None = None) -> bool:
    """Check if pick passes all 5 strong signal filters.

    Uses the imported compute_strong_signal_score when available,
    otherwise applies the 3 core threshold filters as a proxy.
    """
    if _SSF_AVAILABLE:
        stats = _compute_strategy_stats(closed_picks or [])
        score = compute_strong_signal_score(pick, regime, stats)
        return score >= STRONG_SIGNAL_THRESHOLD
    # Fallback: core threshold filters only
    return (_in_rr_sweet_spot(pick) and _in_confidence_band(pick)
            and _in_stop_distance(pick))


# ---------------------------------------------------------------------------
# Core validation logic
# ---------------------------------------------------------------------------

def load_closed_picks(path: Path | str | None = None) -> list[dict]:
    """Load closed picks with parseable dates, sorted by exit date."""
    p = Path(path) if path else _CLOSED_PICKS_PATH
    if not p.exists():
        return []
    with open(p, "r", encoding="utf-8") as f:
        raw = json.load(f)
    picks = []
    for item in raw:
        if not _is_resolved(item):
            continue
        dt = _pick_exit_date(item)
        if dt is None:
            continue
        item["_exit_dt"] = dt
        picks.append(item)
    picks.sort(key=lambda x: x["_exit_dt"])
    return picks


def train_test_split(picks: list[dict], test_days: int = 30):
    """Split into training (all except last N days) and test (last N days)."""
    if not picks:
        return [], []
    latest = picks[-1]["_exit_dt"]
    cutoff = latest - timedelta(days=test_days)
    train = [p for p in picks if p["_exit_dt"] < cutoff]
    test = [p for p in picks if p["_exit_dt"] >= cutoff]
    return train, test


def compute_threshold_stability(train: list[dict], test: list[dict]) -> dict:
    """Compare per-threshold win rates between train and test sets."""
    results = {}
    for name, filter_fn in [
        ("rr_sweet_spot", _in_rr_sweet_spot),
        ("confidence_band", _in_confidence_band),
        ("stop_distance", _in_stop_distance),
    ]:
        train_filtered = [p for p in train if _is_resolved(p) and filter_fn(p)]
        test_filtered = [p for p in test if _is_resolved(p) and filter_fn(p)]
        train_wr = _win_rate(train_filtered)
        test_wr = _win_rate(test_filtered)
        results[name] = {
            "train_picks": len(train_filtered),
            "train_wr": round(train_wr, 4),
            "test_picks": len(test_filtered),
            "test_wr": round(test_wr, 4),
            "delta": round(test_wr - train_wr, 4),
        }
    return results


def rolling_walk_forward(picks: list[dict], window_days: int = 30,
                         step_days: int = 7) -> dict:
    """Rolling 30-day walk-forward: WR of strong-signal picks per window.

    For each window, strategy stats are built from picks BEFORE the window
    (simulating live conditions where you only have past data).

    Returns: mean, std, min, max win rates and window count.
    """
    if not picks:
        return {"mean_wr": 0.0, "std_wr": 0.0, "min_wr": 0.0,
                "max_wr": 0.0, "window_count": 0}

    earliest = picks[0]["_exit_dt"]
    latest = picks[-1]["_exit_dt"]
    total_span = (latest - earliest).days

    if total_span < window_days:
        strong = [p for p in picks if _passes_all_strong_filters(p, closed_picks=picks)]
        wr = _win_rate(strong) if strong else 0.0
        return {"mean_wr": round(wr, 4), "std_wr": 0.0,
                "min_wr": round(wr, 4), "max_wr": round(wr, 4),
                "window_count": 1 if strong else 0}

    window_wrs: list[float] = []
    window_start = earliest

    while window_start + timedelta(days=window_days) <= latest + timedelta(days=1):
        window_end = window_start + timedelta(days=window_days)

        window_picks = [
            p for p in picks
            if window_start <= p["_exit_dt"] < window_end and _is_resolved(p)
        ]

        # Use only prior picks as "training" context (no lookahead)
        prior_picks = [p for p in picks if p["_exit_dt"] < window_start]
        strong_in_window = [
            p for p in window_picks
            if _passes_all_strong_filters(p, closed_picks=prior_picks)
        ]

        if strong_in_window:
            window_wrs.append(_win_rate(strong_in_window))

        window_start += timedelta(days=step_days)

    if not window_wrs:
        return {"mean_wr": 0.0, "std_wr": 0.0, "min_wr": 0.0,
                "max_wr": 0.0, "window_count": 0}

    mean_wr = statistics.mean(window_wrs)
    std_wr = statistics.stdev(window_wrs) if len(window_wrs) > 1 else 0.0

    return {
        "mean_wr": round(mean_wr, 4),
        "std_wr": round(std_wr, 4),
        "min_wr": round(min(window_wrs), 4),
        "max_wr": round(max(window_wrs), 4),
        "window_count": len(window_wrs),
    }


def compute_overfit_risk_score(threshold_stability: dict,
                                rolling: dict,
                                train_wr: float,
                                test_wr: float) -> int:
    """Compute overfit risk score 0-100.

    Four components, each 0-25 points:
      1. Overall train-test WR delta (negative = overfitting)
      2. Per-threshold avg negative delta
      3. Rolling WR volatility (high std = unstable)
      4. Rolling worst-window drop from mean

    0 = thresholds stable across time.
    100 = severe overfitting -- thresholds only work on training data.
    """
    score = 0.0

    # Component 1: Overall train-test delta (0-25)
    overall_delta = test_wr - train_wr
    if overall_delta < 0:
        # -0.20 or worse = 25 points
        score += min(25.0, abs(overall_delta) / 0.20 * 25.0)

    # Component 2: Per-threshold deltas (0-25)
    neg_deltas = []
    for info in threshold_stability.values():
        d = info.get("delta", 0)
        if d < 0:
            neg_deltas.append(abs(d))
    if neg_deltas:
        avg_neg = statistics.mean(neg_deltas)
        # -0.15 avg = 25 points
        score += min(25.0, avg_neg / 0.15 * 25.0)

    # Component 3: Rolling WR volatility (0-25)
    std_wr = rolling.get("std_wr", 0)
    # std of 0.25+ = 25 points
    score += min(25.0, std_wr / 0.25 * 25.0)

    # Component 4: Rolling min-WR drop from mean (0-25)
    min_wr = rolling.get("min_wr", 0.5)
    mean_wr = rolling.get("mean_wr", 0.5)
    if mean_wr > 0:
        drop = max(0.0, mean_wr - min_wr)
        # drop of 0.30+ = 25 points
        score += min(25.0, drop / 0.30 * 25.0)

    return max(0, min(100, round(score)))


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_walk_forward_validation(
    picks_path: Path | str | None = None,
    output_path: Path | str | None = None,
    test_days: int = 30,
    window_days: int = 30,
    step_days: int = 7,
) -> dict:
    """Run full walk-forward threshold validation. Returns the report dict."""

    picks = load_closed_picks(picks_path)
    if not picks:
        report = {
            "error": "No closed picks with valid dates found",
            "computed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        _save_report(report, output_path)
        return report

    # 1. Train/test split
    train, test = train_test_split(picks, test_days=test_days)
    train_wr = _win_rate(train)
    test_wr = _win_rate(test)

    training_period = {
        "start": train[0]["_exit_dt"].strftime("%Y-%m-%d") if train else "N/A",
        "end": train[-1]["_exit_dt"].strftime("%Y-%m-%d") if train else "N/A",
        "picks": len(train),
        "wr": round(train_wr, 4),
    }
    test_period = {
        "start": test[0]["_exit_dt"].strftime("%Y-%m-%d") if test else "N/A",
        "end": test[-1]["_exit_dt"].strftime("%Y-%m-%d") if test else "N/A",
        "picks": len(test),
        "wr": round(test_wr, 4),
    }

    # 2. Per-threshold stability
    threshold_stability = compute_threshold_stability(train, test)

    # 3. Rolling walk-forward
    rolling = rolling_walk_forward(
        picks, window_days=window_days, step_days=step_days)

    # 4. Overfit risk score
    overfit_score = compute_overfit_risk_score(
        threshold_stability, rolling, train_wr, test_wr)

    report = {
        "training_period": training_period,
        "test_period": test_period,
        "threshold_stability": threshold_stability,
        "rolling_windows": rolling,
        "overfit_risk_score": overfit_score,
        "config": {
            "test_days": test_days,
            "window_days": window_days,
            "step_days": step_days,
            "thresholds_tested": {
                "rr_sweet_spot": f"{RR_SWEET_LOW}-{RR_SWEET_HIGH}",
                "confidence_band": f"{CONF_BEST_LOW}-{CONF_BEST_HIGH}",
                "stop_distance": f"{STOP_OPTIMAL_LOW}-{STOP_OPTIMAL_HIGH}",
                "strong_signal_score": f">= {STRONG_SIGNAL_THRESHOLD}",
            },
        },
        "computed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    _save_report(report, output_path)
    return report


def _save_report(report: dict, output_path: Path | str | None = None):
    """Write report JSON to disk."""
    out = Path(output_path) if output_path else _REPORT_PATH
    out.parent.mkdir(parents=True, exist_ok=True)

    def _default(o: Any) -> str:
        if isinstance(o, datetime):
            return o.strftime("%Y-%m-%dT%H:%M:%SZ")
        raise TypeError(f"Object of type {type(o)} is not JSON serializable")

    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=_default)
    print(f"[WALK-FORWARD] Threshold overfit report saved to {out}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    report = run_walk_forward_validation()
    score = report.get("overfit_risk_score", "N/A")
    train_info = report.get("training_period", {})
    test_info = report.get("test_period", {})
    rolling = report.get("rolling_windows", {})

    print(f"\n{'='*60}")
    print("Threshold Walk-Forward Overfit Report")
    print(f"{'='*60}")
    print(f"Training: {train_info.get('picks', 0)} picks, "
          f"WR={train_info.get('wr', 0):.1%}")
    print(f"Test:     {test_info.get('picks', 0)} picks, "
          f"WR={test_info.get('wr', 0):.1%}")
    print(f"Rolling:  mean={rolling.get('mean_wr', 0):.1%}, "
          f"std={rolling.get('std_wr', 0):.1%}, "
          f"min={rolling.get('min_wr', 0):.1%}, "
          f"max={rolling.get('max_wr', 0):.1%} "
          f"({rolling.get('window_count', 0)} windows)")

    stab = report.get("threshold_stability", {})
    for name, info in stab.items():
        delta = info.get("delta", 0)
        arrow = "+" if delta >= 0 else ""
        print(f"  {name}: train={info.get('train_wr', 0):.1%} "
              f"test={info.get('test_wr', 0):.1%} "
              f"delta={arrow}{delta:.1%}")

    print(f"\nOverfit Risk Score: {score}/100")
    if isinstance(score, int):
        if score < 20:
            label = "LOW risk -- thresholds appear stable across time"
        elif score < 50:
            label = "MODERATE risk -- some degradation on unseen data"
        elif score < 75:
            label = "HIGH risk -- thresholds may be overfit to training data"
        else:
            label = "SEVERE risk -- strong evidence of overfitting"
        print(f"  -> {label}")
    print(f"{'='*60}")
