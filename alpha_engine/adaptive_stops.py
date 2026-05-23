#!/usr/bin/env python3
"""
ALPHA ENGINE -- Adaptive Stop-Loss / Take-Profit Calibration
=============================================================
Per-strategy MFE/MAE analysis for optimal SL/TP sizing.

Complements sl_calibrator.py (which groups by symbol_family x strategy_family)
by providing granular per-strategy calibration when enough closed trades exist.

Key metrics:
  - MFE (Maximum Favorable Excursion): how far price moved in our favor
  - MAE (Maximum Adverse Excursion): how far price moved against us
  - Edge Ratio = median_mfe / median_mae (>1.0 = profitable edge)
  - optimal_sl = p75_mae * 1.1 (let 75% of adverse moves play out)
  - optimal_tp = p50_mfe * 0.8 (capture 80% of median favorable move)

Data sources (in priority order):
  1. Explicit mae/mfe fields from forward_validator.py tracking
  2. Derived from entry_price vs stop_loss/take_profit vs exit_price
  3. pnl_pct as last-resort proxy (only captures realized, not max excursion)

Stdlib only -- no numpy/pandas.
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
DATA_DIR = _THIS_DIR / "data"
CLOSED_PICKS_PATH = DATA_DIR / "closed_picks.json"
CALIBRATION_OUTPUT_PATH = DATA_DIR / "adaptive_stops_calibration.json"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_MIN_TRADES = 10          # Minimum closed trades per strategy
MAX_SL_PCT = 0.15               # 15% hard cap on stop-loss distance
MIN_SL_PCT = 0.005              # 0.5% floor -- never set SL tighter than this
MAX_TP_PCT = 0.30               # 30% hard cap on take-profit distance
MIN_TP_PCT = 0.005              # 0.5% floor
MIN_EDGE_RATIO = 0.5            # Warn if edge ratio below this
MAE_BUFFER = 1.1                # 10% buffer on p75 MAE for optimal SL
MFE_CAPTURE = 0.8               # Capture 80% of median MFE for optimal TP


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_closed_picks() -> list:
    """Load closed picks, handling merge-conflict markers."""
    if not CLOSED_PICKS_PATH.exists():
        return []
    try:
        with open(CLOSED_PICKS_PATH, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()
        # Strip git merge conflict markers
        clean_lines = []
        in_theirs = False
        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.startswith("<<<<<<"):
                continue
            if stripped.startswith("======"):
                in_theirs = True
                continue
            if stripped.startswith(">>>>>>"):
                in_theirs = False
                continue
            if in_theirs:
                continue
            clean_lines.append(line)
        cleaned = "\n".join(clean_lines)
        data = json.loads(cleaned)
        if isinstance(data, list):
            return [p for p in data if isinstance(p, dict)]
        return []
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [ADAPTIVE] Warning: could not load closed_picks.json: {e}")
        return []


def _percentile(values: list, pct: float) -> float:
    """Compute pct-th percentile (0-100 scale) with linear interpolation."""
    if not values:
        return 0.0
    s = sorted(values)
    k = (pct / 100.0) * (len(s) - 1)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] * (c - k) + s[c] * (k - f)


def _median(values: list) -> float:
    """Compute median of a list."""
    return _percentile(values, 50.0)


def _extract_mfe_mae(pick: dict) -> tuple:
    """
    Extract MFE and MAE as positive percentages from a pick.

    Returns (mfe_pct, mae_pct) where both are >= 0.
    Returns (None, None) if no usable data.

    Priority:
      1. Explicit mae/mfe fields (from forward_validator tracking)
      2. Derived from entry vs TP/SL hit and exit price
      3. pnl_pct as proxy (last resort)
    """
    entry = pick.get("entry_price", 0)
    if not entry or entry <= 0:
        return (None, None)

    # --- Priority 1: Explicit mfe/mae fields ---
    raw_mfe = pick.get("mfe")
    raw_mae = pick.get("mae")
    if raw_mfe is not None and raw_mae is not None:
        mfe_val = abs(float(raw_mfe)) if raw_mfe else 0.0
        mae_val = abs(float(raw_mae)) if raw_mae else 0.0
        if mfe_val > 0 or mae_val > 0:
            return (mfe_val, mae_val)

    # --- Priority 2: Derive from exit_reason + prices ---
    exit_price = pick.get("exit_price", 0)
    tp = pick.get("take_profit", 0)
    sl = pick.get("stop_loss", 0)
    status = str(pick.get("status", "")).upper()
    exit_reason = str(pick.get("exit_reason", "")).upper()

    if exit_price and exit_price > 0 and entry > 0:
        # For WON trades: MFE >= realized gain, MAE is unknown but bounded
        # For LOST trades: MAE >= realized loss, MFE is the high_water_mark
        realized_pct = abs(exit_price - entry) / entry

        if status == "WON" or "TP" in exit_reason:
            # MFE is at least the TP distance (may have exceeded)
            mfe_pct = abs(tp - entry) / entry if tp and tp > 0 else realized_pct
            mfe_pct = max(mfe_pct, realized_pct)
            # MAE: use high_water_mark if available, else estimate small
            hwm = pick.get("high_water_mark")
            if hwm and hwm > 0 and hwm != entry:
                # high_water_mark is best price reached -- for winners,
                # MAE is how far it dipped before recovering
                mae_pct = realized_pct * 0.3  # conservative estimate
            else:
                mae_pct = realized_pct * 0.25  # winners typically have small MAE
            return (mfe_pct, mae_pct)

        elif status == "LOST" or "SL" in exit_reason:
            # MAE is at least the SL distance
            mae_pct = abs(sl - entry) / entry if sl and sl > 0 else realized_pct
            mae_pct = max(mae_pct, realized_pct)
            # MFE: use high_water_mark if available
            hwm = pick.get("high_water_mark")
            if hwm and hwm > 0 and hwm != entry:
                mfe_pct = abs(hwm - entry) / entry
            else:
                mfe_pct = realized_pct * 0.2  # losers had some favorable move
            return (mfe_pct, mae_pct)

    # --- Priority 3: pnl_pct as proxy ---
    pnl = pick.get("pnl_pct")
    if pnl is not None:
        pnl_f = float(pnl)
        if pnl_f > 0:
            return (abs(pnl_f), abs(pnl_f) * 0.3)
        elif pnl_f < 0:
            return (abs(pnl_f) * 0.2, abs(pnl_f))

    return (None, None)


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def compute_mfe_mae_stats(closed_picks: list, strategy: str) -> dict:
    """
    Compute MFE/MAE statistics for a single strategy.

    Args:
        closed_picks: List of closed pick dicts.
        strategy: Strategy name to filter on.

    Returns:
        Dict with median/p25/p75 for MFE and MAE, plus optimal_sl,
        optimal_tp, edge_ratio, and sample_size.
        Returns empty dict if insufficient data.
    """
    # Filter picks for this strategy with terminal status
    terminal = {"WON", "LOST", "CLOSED", "EXPIRED"}
    strat_picks = [
        p for p in closed_picks
        if p.get("strategy") == strategy
        and str(p.get("status", "")).upper() in terminal
    ]

    mfe_values = []
    mae_values = []

    for pick in strat_picks:
        mfe, mae = _extract_mfe_mae(pick)
        if mfe is not None and mae is not None:
            mfe_values.append(mfe)
            mae_values.append(mae)

    sample_size = len(mfe_values)
    if sample_size == 0:
        return {}

    # Compute percentiles
    median_mfe = _median(mfe_values)
    p25_mfe = _percentile(mfe_values, 25.0)
    p75_mfe = _percentile(mfe_values, 75.0)

    median_mae = _median(mae_values)
    p25_mae = _percentile(mae_values, 25.0)
    p75_mae = _percentile(mae_values, 75.0)

    # Optimal stops
    optimal_sl = p75_mae * MAE_BUFFER
    optimal_sl = max(MIN_SL_PCT, min(optimal_sl, MAX_SL_PCT))

    optimal_tp = median_mfe * MFE_CAPTURE
    optimal_tp = max(MIN_TP_PCT, min(optimal_tp, MAX_TP_PCT))

    # Edge ratio
    edge_ratio = (median_mfe / median_mae) if median_mae > 0 else 999.0

    # Win rate for this strategy
    wins = sum(1 for p in strat_picks if str(p.get("status", "")).upper() == "WON")
    total = len(strat_picks)
    win_rate = wins / total if total > 0 else 0.0

    return {
        "strategy": strategy,
        "sample_size": sample_size,
        "total_trades": total,
        "wins": wins,
        "win_rate": round(win_rate, 4),
        "median_mfe": round(median_mfe, 6),
        "p25_mfe": round(p25_mfe, 6),
        "p75_mfe": round(p75_mfe, 6),
        "median_mae": round(median_mae, 6),
        "p25_mae": round(p25_mae, 6),
        "p75_mae": round(p75_mae, 6),
        "optimal_sl": round(optimal_sl, 6),
        "optimal_tp": round(optimal_tp, 6),
        "edge_ratio": round(edge_ratio, 4),
    }


def calibrate_all_strategies(closed_picks: list, min_trades: int = DEFAULT_MIN_TRADES) -> dict:
    """
    Run MFE/MAE calibration for every strategy with enough trades.

    Args:
        closed_picks: List of all closed pick dicts.
        min_trades: Minimum trades required per strategy (default 10).

    Returns:
        Dict of {strategy_name: {optimal_sl, optimal_tp, edge_ratio, sample_size, ...}}
    """
    # Collect unique strategies
    from collections import Counter
    strat_counts = Counter(
        p.get("strategy", "")
        for p in closed_picks
        if p.get("strategy")
        and str(p.get("status", "")).upper() in {"WON", "LOST", "CLOSED", "EXPIRED"}
    )

    calibration = {}
    skipped = 0

    for strategy, count in strat_counts.items():
        if count < min_trades:
            skipped += 1
            continue

        stats = compute_mfe_mae_stats(closed_picks, strategy)
        if not stats or stats.get("sample_size", 0) < min_trades:
            skipped += 1
            continue

        calibration[strategy] = stats

    # Sort by edge ratio descending
    calibration = dict(
        sorted(calibration.items(),
               key=lambda x: x[1].get("edge_ratio", 0),
               reverse=True)
    )

    return calibration


def apply_adaptive_stops(pick: dict, calibration: dict) -> dict:
    """
    Apply adaptive SL/TP to a pick based on calibration data.

    Only overrides if the calibrated values are TIGHTER (closer to entry)
    than current values. Tags the pick with adaptive_stops_applied = True.

    Args:
        pick: A pick dict with entry_price, stop_loss, take_profit, strategy.
        calibration: Output from calibrate_all_strategies().

    Returns:
        The pick dict (modified in-place) with adaptive stops applied.
    """
    strategy = pick.get("strategy", "")
    entry = pick.get("entry_price", 0)
    current_sl = pick.get("stop_loss", 0)
    current_tp = pick.get("take_profit", 0)

    if not strategy or not entry or entry <= 0:
        return pick
    if not current_sl or not current_tp:
        return pick

    cal = calibration.get(strategy)
    if not cal:
        return pick

    optimal_sl_pct = cal.get("optimal_sl", 0)
    optimal_tp_pct = cal.get("optimal_tp", 0)

    if optimal_sl_pct <= 0 or optimal_tp_pct <= 0:
        return pick

    # Determine direction from SL position relative to entry
    is_long = current_sl < entry

    # Compute calibrated price levels
    if is_long:
        cal_sl_price = entry * (1.0 - optimal_sl_pct)
        cal_tp_price = entry * (1.0 + optimal_tp_pct)
    else:
        cal_sl_price = entry * (1.0 + optimal_sl_pct)
        cal_tp_price = entry * (1.0 - optimal_tp_pct)

    adjusted = False

    # Only tighten SL (move closer to entry)
    current_sl_dist = abs(current_sl - entry)
    cal_sl_dist = abs(cal_sl_price - entry)
    if 0 < cal_sl_dist < current_sl_dist:
        pick["stop_loss_pre_adaptive"] = current_sl
        pick["stop_loss"] = round(cal_sl_price, 8)
        adjusted = True

    # Only tighten TP (move closer to entry)
    current_tp_dist = abs(current_tp - entry)
    cal_tp_dist = abs(cal_tp_price - entry)
    if 0 < cal_tp_dist < current_tp_dist:
        pick["take_profit_pre_adaptive"] = current_tp
        pick["take_profit"] = round(cal_tp_price, 8)
        adjusted = True

    if adjusted:
        pick["adaptive_stops_applied"] = True
        pick["adaptive_calibration_source"] = strategy
        pick["adaptive_edge_ratio"] = cal.get("edge_ratio", 0)
        pick["adaptive_sample_size"] = cal.get("sample_size", 0)
        # Recalculate R:R
        new_sl = pick.get("stop_loss", 0)
        new_tp = pick.get("take_profit", 0)
        sl_dist = abs(new_sl - entry)
        tp_dist = abs(new_tp - entry)
        if sl_dist > 0:
            pick["risk_reward"] = round(tp_dist / sl_dist, 2)

    return pick


def generate_calibration_report() -> dict:
    """
    Load closed picks, run full calibration, and save results.

    Saves to alpha_engine/data/adaptive_stops_calibration.json.

    Returns:
        Full report dict with per-strategy stats and system-level summary.
    """
    closed = _load_closed_picks()
    if not closed:
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_closed_picks": 0,
            "strategies_calibrated": 0,
            "calibration": {},
            "system_summary": {},
        }
        _save_report(report)
        return report

    calibration = calibrate_all_strategies(closed, min_trades=DEFAULT_MIN_TRADES)

    # System-level aggregation
    all_edge_ratios = [v["edge_ratio"] for v in calibration.values() if v.get("edge_ratio")]
    all_optimal_sl = [v["optimal_sl"] for v in calibration.values() if v.get("optimal_sl")]
    all_optimal_tp = [v["optimal_tp"] for v in calibration.values() if v.get("optimal_tp")]
    all_win_rates = [v["win_rate"] for v in calibration.values() if v.get("win_rate") is not None]
    total_samples = sum(v.get("sample_size", 0) for v in calibration.values())

    system_summary = {
        "total_closed_picks": len(closed),
        "strategies_calibrated": len(calibration),
        "total_samples_used": total_samples,
        "median_edge_ratio": round(_median(all_edge_ratios), 4) if all_edge_ratios else 0,
        "mean_edge_ratio": round(sum(all_edge_ratios) / len(all_edge_ratios), 4) if all_edge_ratios else 0,
        "median_optimal_sl": round(_median(all_optimal_sl), 6) if all_optimal_sl else 0,
        "median_optimal_tp": round(_median(all_optimal_tp), 6) if all_optimal_tp else 0,
        "median_win_rate": round(_median(all_win_rates), 4) if all_win_rates else 0,
        "strategies_with_positive_edge": sum(1 for e in all_edge_ratios if e > 1.0),
        "strategies_with_weak_edge": sum(1 for e in all_edge_ratios if e <= MIN_EDGE_RATIO),
    }

    # Classify strategies by edge quality
    edge_tiers = {"strong": [], "moderate": [], "weak": [], "negative": []}
    for strat, stats in calibration.items():
        er = stats.get("edge_ratio", 0)
        if er >= 2.0:
            edge_tiers["strong"].append(strat)
        elif er >= 1.0:
            edge_tiers["moderate"].append(strat)
        elif er >= MIN_EDGE_RATIO:
            edge_tiers["weak"].append(strat)
        else:
            edge_tiers["negative"].append(strat)

    system_summary["edge_tiers"] = {
        k: {"count": len(v), "strategies": v}
        for k, v in edge_tiers.items()
    }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_closed_picks": len(closed),
        "strategies_calibrated": len(calibration),
        "min_trades_threshold": DEFAULT_MIN_TRADES,
        "calibration": calibration,
        "system_summary": system_summary,
    }

    _save_report(report)
    return report


def _save_report(report: dict) -> None:
    """Save calibration report to JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CALIBRATION_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"  [ADAPTIVE] Saved calibration to {CALIBRATION_OUTPUT_PATH}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 65)
    print("  Adaptive Stops -- MFE/MAE Calibration")
    print("=" * 65)

    report = generate_calibration_report()

    summary = report.get("system_summary", {})
    print(f"\n  Closed picks analyzed: {report.get('total_closed_picks', 0)}")
    print(f"  Strategies calibrated: {report.get('strategies_calibrated', 0)}")
    print(f"  Total samples used:    {summary.get('total_samples_used', 0)}")
    print(f"  Median edge ratio:     {summary.get('median_edge_ratio', 0):.4f}")
    print(f"  Median optimal SL:     {summary.get('median_optimal_sl', 0):.4%}")
    print(f"  Median optimal TP:     {summary.get('median_optimal_tp', 0):.4%}")
    print(f"  Positive edge strats:  {summary.get('strategies_with_positive_edge', 0)}")
    print(f"  Weak edge strats:      {summary.get('strategies_with_weak_edge', 0)}")

    tiers = summary.get("edge_tiers", {})
    for tier_name in ("strong", "moderate", "weak", "negative"):
        tier = tiers.get(tier_name, {})
        count = tier.get("count", 0)
        strats = tier.get("strategies", [])
        if count > 0:
            print(f"\n  [{tier_name.upper()} EDGE] ({count} strategies):")
            for s in strats:
                cal = report["calibration"].get(s, {})
                print(f"    {s}: edge={cal.get('edge_ratio', 0):.2f} "
                      f"SL={cal.get('optimal_sl', 0):.4%} "
                      f"TP={cal.get('optimal_tp', 0):.4%} "
                      f"WR={cal.get('win_rate', 0):.1%} "
                      f"(n={cal.get('sample_size', 0)})")

    print(f"\n  Report saved to: {CALIBRATION_OUTPUT_PATH}")
    print("  Done.")
