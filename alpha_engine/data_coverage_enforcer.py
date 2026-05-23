#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Data Coverage Enforcer
========================================
Runs after feature_populator in production_scanner to:
1. Backfill "inline" features that _signal_to_features computes on-the-fly
   but never persists to the pick dict (strategy_encoded, hour_utc, hour_sin,
   hour_x_vol, rr_asymmetry, strategy_win_rate, etc.)
2. Count how many of the 42 ML features are populated (non-default) per pick
3. Penalize low-coverage picks: <50% -> -5 elite_score, <25% -> -10
4. Save system-wide coverage metrics to data/coverage_metrics.json

Stdlib only (math, json, os) -- NO numpy/pandas.
Windows UTF-8 safe.
Backwards-compatible: if anything fails, picks pass through unchanged.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Windows UTF-8 fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DATA_DIR = Path(__file__).resolve().parent / "data"

# ---------------------------------------------------------------------------
# ML Feature list (mirrors MLSignalRanker.FEATURES from ml_ranker.py)
# These are the 42 features the model actually uses.
# ---------------------------------------------------------------------------
ML_FEATURES = [
    "strategy_encoded",
    "confidence",
    "volume_ratio",
    "risk_reward",
    "direction_market_alignment",
    "strategy_win_rate",
    "strategy_sharpe",
    "strategy_closed_picks",
    "hour_utc",
    "hour_sin",
    "hour_x_vol",
    "sl_distance_pct",
    "tp_distance_pct",
    "rr_asymmetry",
    "funding_rate_raw",
    "funding_z_30d",
    "funding_persistence",
    "orderbook_imbalance",
    "vpin_toxicity",
    "funding_rate_norm",
    "obi_delta_5",
    "obi_delta_15",
    "obi_acceleration",
    "fear_greed_norm",
    "cs_momentum_rank",
    "cs_relative_strength",
    "cs_dispersion",
    "cs_leader_lag",
    "close_to_vwap",
    "garman_klass_vol",
    "fng_gradient",
    "risk_reward_raw",
    "mom30",
    "rsi30",
    "macd_hist_norm",
    "stoch_k30",
    "stoch_d30",
    "cci20_norm",
    "williams_r",
]

# Default values for each feature (matching ml_ranker defaults).
# A feature is "populated" (non-default) if its value differs from this.
FEATURE_DEFAULTS = {
    "strategy_encoded": 0.0,
    "confidence": 0.5,
    "volume_ratio": 1.0,
    "risk_reward": 1.5,
    "direction_market_alignment": None,  # always computed during backfill (±1 without BTC data, dir*btc_trend with data)
    "strategy_win_rate": 0.5,
    "strategy_sharpe": 0.0,
    "strategy_closed_picks": 0,
    "hour_utc": None,  # always computed from timestamp -> always populated
    "hour_sin": None,
    "hour_x_vol": 0.0,
    "sl_distance_pct": 0.0,
    "tp_distance_pct": 0.0,
    "rr_asymmetry": 0.0,
    "funding_rate_raw": 0.0,
    "funding_z_30d": 0.0,
    "funding_persistence": 0.0,
    "orderbook_imbalance": 0.0,
    "vpin_toxicity": 0.5,
    "funding_rate_norm": 0.0,
    "obi_delta_5": 0.0,
    "obi_delta_15": 0.0,
    "obi_acceleration": 0.0,
    "fear_greed_norm": 0.5,
    "cs_momentum_rank": 0.5,
    "cs_relative_strength": 0.0,
    "cs_dispersion": 0.5,
    "cs_leader_lag": 0.0,
    "close_to_vwap": 0.0,
    "garman_klass_vol": 0.0,
    "fng_gradient": 0.0,
    "risk_reward_raw": 0.15,  # 1.5 / 10.0
    "mom30": 0.0,
    "rsi30": 0.5,
    "macd_hist_norm": 0.0,
    "stoch_k30": 0.5,
    "stoch_d30": 0.5,
    "cci20_norm": 0.0,
    "williams_r": -0.5,
}

# ---------------------------------------------------------------------------
# System stats cache (for strategy_win_rate / strategy_sharpe backfill)
# ---------------------------------------------------------------------------
_SYSTEM_STATS: dict[str, dict] = {}


def _load_system_stats():
    """Load system stats from audit dashboard payload (same as ml_ranker)."""
    global _SYSTEM_STATS
    if _SYSTEM_STATS:
        return
    try:
        candidates = [
            DATA_DIR / "audit_dashboard_payload.json",
            DATA_DIR.parent.parent / "audit_dashboard" / "payload.json",
        ]
        for path in candidates:
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    payload = json.load(f)
                systems = payload.get("systems") or payload.get("strategies") or []
                for s in systems:
                    name = s.get("name") or s.get("strategy")
                    if name:
                        _SYSTEM_STATS[name] = {
                            "win_rate": float(s.get("win_rate", 0) or 0),
                            "sharpe": float(s.get("sharpe", 0) or 0),
                            "closed_picks": int(s.get("closed_picks", 0) or 0),
                        }
                break
    except Exception:
        pass


def _ts_hour(pick: dict) -> int:
    """Extract UTC hour from pick timestamp."""
    for key in ("timestamp", "entry_date", "created_at", "signal_time"):
        ts = pick.get(key)
        if ts:
            try:
                if isinstance(ts, (int, float)):
                    return int(datetime.fromtimestamp(ts, tz=timezone.utc).hour)
                dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                return dt.hour
            except Exception:
                continue
    return datetime.now(timezone.utc).hour


# ---------------------------------------------------------------------------
# Backfill inline features
# ---------------------------------------------------------------------------

def backfill_inline_features(pick: dict) -> dict:
    """Compute and store features that _signal_to_features computes inline
    but never persists. This closes the gap between what the ML model sees
    and what the health report can observe on the pick dict.

    Does NOT overwrite existing values.
    """
    strat = pick.get("strategy", "")
    entry = float(pick.get("entry_price", 0) or 0)
    tp = float(pick.get("take_profit", 0) or 0)
    sl = float(pick.get("stop_loss", 0) or 0)
    direction = (pick.get("direction") or pick.get("signal_type") or "").upper()
    hour = _ts_hour(pick)

    # strategy_encoded: deterministic hash
    if "strategy_encoded" not in pick or pick["strategy_encoded"] == 0:
        pick["strategy_encoded"] = round(sum(ord(c) for c in str(strat)) % 100 / 100.0, 4)

    # direction_market_alignment: direction * btc_24h_trend, falls back to raw direction when no BTC data
    # Aligned with ml_ranker.py _signal_to_features graceful fallback (Phase 20).
    # When btc trend data is absent, returns dir_val (±1) so the feature retains
    # directional information instead of collapsing to 0.0 for all picks.
    dir_map = {
        "BUY": 1, "LONG": 1, "CALL": 1,
        "SELL": -1, "SHORT": -1, "PUT": -1,
    }
    if "direction_market_alignment" not in pick:
        dir_val = dir_map.get(direction, 0)
        mf = pick.get("ml_features_at_entry") or {}
        btc_raw = mf.get("btc_24h_change") or pick.get("btc_24h_change")
        if btc_raw is not None and btc_raw != 0:
            btc_trend = max(-1.0, min(1.0, float(btc_raw) / 10.0))
            pick["direction_market_alignment"] = dir_val * btc_trend
        else:
            # No BTC trend data — graceful fallback to raw direction value
            pick["direction_market_alignment"] = dir_val

    # hour_utc (normalized 0-1)
    if "hour_utc" not in pick:
        pick["hour_utc"] = round(hour / 23.0, 4)

    # hour_sin
    if "hour_sin" not in pick:
        pick["hour_sin"] = round(math.sin(2 * math.pi * hour / 24.0), 6)

    # hour_x_vol (hour_sin * atr_pct)
    atr_pct = float(pick.get("atr_at_entry", 0) or 0)
    if "hour_x_vol" not in pick:
        pick["hour_x_vol"] = round(math.sin(2 * math.pi * hour / 24.0) * atr_pct, 8)

    # SL/TP distances as % of entry
    if entry > 0:
        if "sl_distance_pct" not in pick and sl > 0:
            pick["sl_distance_pct"] = round(abs(entry - sl) / entry, 6)
        if "tp_distance_pct" not in pick and tp > 0:
            pick["tp_distance_pct"] = round(abs(tp - entry) / entry, 6)

    # rr_asymmetry
    sl_dist = float(pick.get("sl_distance_pct", 0) or 0)
    tp_dist = float(pick.get("tp_distance_pct", 0) or 0)
    if "rr_asymmetry" not in pick and (tp_dist + sl_dist) > 0:
        pick["rr_asymmetry"] = round((tp_dist - sl_dist) / (tp_dist + sl_dist), 6)

    # risk_reward_raw (capped at 10, normalized)
    if "risk_reward_raw" not in pick:
        rr = float(pick.get("risk_reward", 1.5) or 1.5)
        pick["risk_reward_raw"] = round(min(rr, 10.0) / 10.0, 4)

    # Strategy performance from system stats
    _load_system_stats()
    if strat in _SYSTEM_STATS:
        ss = _SYSTEM_STATS[strat]
        if "strategy_win_rate" not in pick or pick.get("strategy_win_rate") in (0, 0.0, None):
            pick["strategy_win_rate"] = ss.get("win_rate", 0.5)
        if "strategy_sharpe" not in pick or pick.get("strategy_sharpe") in (0, 0.0, None):
            pick["strategy_sharpe"] = ss.get("sharpe", 0.0)
        if "strategy_closed_picks" not in pick or pick.get("strategy_closed_picks") in (0, None):
            pick["strategy_closed_picks"] = ss.get("closed_picks", 0)

    # funding_rate_norm from funding_rate
    fr = float(pick.get("funding_rate", 0) or 0)
    if "funding_rate_norm" not in pick and fr != 0:
        pick["funding_rate_norm"] = round(max(-3.0, min(3.0, fr / 0.01)), 4)

    # fear_greed_norm from fear_greed (0-100 -> 0-1)
    fg = pick.get("fear_greed")
    if fg is not None and "fear_greed_norm" not in pick:
        try:
            pick["fear_greed_norm"] = round(max(0.0, min(1.0, float(fg) / 100.0)), 4)
        except (TypeError, ValueError):
            pass

    return pick


# ---------------------------------------------------------------------------
# Coverage computation
# ---------------------------------------------------------------------------

def compute_pick_coverage(pick: dict) -> dict:
    """Compute feature coverage for a single pick.

    Returns dict with:
      - populated_count: number of features with non-default values
      - total_features: total features checked
      - coverage_pct: populated_count / total_features
      - missing_features: list of feature names still at default
      - coverage_class: HIGH (>=75%), MEDIUM (>=50%), LOW (>=25%), VERY_LOW (<25%)
    """
    populated = 0
    missing = []
    mf = pick.get("ml_features_at_entry") or {}

    for feat_name in ML_FEATURES:
        default = FEATURE_DEFAULTS.get(feat_name)

        # Check pick dict first, then ml_features_at_entry
        val = pick.get(feat_name)
        if val is None:
            val = mf.get(feat_name)

        if val is None:
            missing.append(feat_name)
            continue

        # If default is None, it means "always populated" (like hour_utc)
        if default is None:
            populated += 1
            continue

        # Check if value differs from default (with tolerance for floats)
        try:
            fval = float(val)
            fdef = float(default)
            if abs(fval - fdef) > 1e-6:
                populated += 1
            else:
                missing.append(feat_name)
        except (TypeError, ValueError):
            # Non-numeric value that exists -> count as populated
            populated += 1

    total = len(ML_FEATURES)
    pct = populated / total if total > 0 else 0.0

    if pct >= 0.75:
        cls = "HIGH"
    elif pct >= 0.50:
        cls = "MEDIUM"
    elif pct >= 0.25:
        cls = "LOW"
    else:
        cls = "VERY_LOW"

    return {
        "populated_count": populated,
        "total_features": total,
        "coverage_pct": round(pct, 4),
        "missing_features": missing,
        "coverage_class": cls,
    }


def apply_coverage_penalties(pick: dict, coverage: dict) -> dict:
    """Apply elite_score penalties for low coverage.

    - LOW coverage (<50%): -5 elite_score
    - VERY_LOW coverage (<25%): -10 elite_score
    """
    cls = coverage["coverage_class"]
    penalty = 0

    if cls == "LOW":
        penalty = -5
    elif cls == "VERY_LOW":
        penalty = -10

    if penalty != 0:
        old_score = float(pick.get("elite_score", 0) or 0)
        pick["elite_score"] = round(old_score + penalty, 2)
        pick["coverage_penalty"] = penalty

    pick["feature_coverage_pct"] = coverage["coverage_pct"]
    pick["feature_coverage_class"] = cls
    return pick


# ---------------------------------------------------------------------------
# Batch enforcement (main entry point)
# ---------------------------------------------------------------------------

def enforce_coverage(picks: list[dict]) -> list[dict]:
    """Run coverage enforcement on a batch of picks.

    1. Backfill inline features on each pick
    2. Compute per-pick coverage
    3. Apply elite_score penalties for low coverage
    4. Compute and save system-wide metrics
    5. Return picks (modified in-place)
    """
    if not picks:
        return picks

    t0 = time.time()

    # Phase 1: Backfill inline features
    for pick in picks:
        try:
            backfill_inline_features(pick)
        except Exception:
            pass

    # Phase 2: Compute coverage per pick
    coverages = []
    low_count = 0
    very_low_count = 0
    total_populated = 0

    for pick in picks:
        try:
            cov = compute_pick_coverage(pick)
            coverages.append(cov)
            apply_coverage_penalties(pick, cov)

            if cov["coverage_class"] == "LOW":
                low_count += 1
            elif cov["coverage_class"] == "VERY_LOW":
                very_low_count += 1

            total_populated += cov["populated_count"]
        except Exception:
            coverages.append({"coverage_pct": 0, "coverage_class": "VERY_LOW",
                              "populated_count": 0, "total_features": len(ML_FEATURES),
                              "missing_features": list(ML_FEATURES)})

    # Phase 3: System-wide metrics
    n = len(picks)
    total_features = len(ML_FEATURES)
    system_coverage = total_populated / (n * total_features) if n > 0 else 0.0

    # Per-feature population rate
    feature_rates = {}
    for feat_name in ML_FEATURES:
        count = sum(1 for c in coverages if feat_name not in c.get("missing_features", []))
        feature_rates[feat_name] = round(count / n, 4) if n > 0 else 0.0

    # Find worst features (< 50% population)
    weak_features = {k: v for k, v in feature_rates.items() if v < 0.50}

    metrics = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_picks": n,
        "total_ml_features": total_features,
        "system_coverage_pct": round(system_coverage, 4),
        "picks_high_coverage": sum(1 for c in coverages if c["coverage_class"] == "HIGH"),
        "picks_medium_coverage": sum(1 for c in coverages if c["coverage_class"] == "MEDIUM"),
        "picks_low_coverage": low_count,
        "picks_very_low_coverage": very_low_count,
        "penalties_applied": low_count + very_low_count,
        "per_feature_population_rate": feature_rates,
        "weak_features_below_50pct": weak_features,
        "coverage_target": 0.95,
        "coverage_met": system_coverage >= 0.95,
    }

    # Save metrics
    try:
        metrics_path = DATA_DIR / "coverage_metrics.json"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, default=str)
    except Exception:
        pass

    elapsed = time.time() - t0
    print(f"  [COVERAGE ENFORCER] {n} picks: system coverage {system_coverage*100:.1f}% "
          f"(HIGH={metrics['picks_high_coverage']}, MED={metrics['picks_medium_coverage']}, "
          f"LOW={low_count}, VLOW={very_low_count}) "
          f"| {len(weak_features)} weak features | {elapsed:.1f}s")

    if very_low_count > 0:
        print(f"  [COVERAGE ENFORCER] WARNING: {very_low_count} picks have <25% coverage (-10 elite_score)")

    return picks


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_pick = {
        "symbol": "BTCUSDT",
        "strategy": "cross_sectional_momentum",
        "confidence": 0.75,
        "entry_price": 87000.0,
        "take_profit": 90000.0,
        "stop_loss": 85000.0,
        "direction": "BUY",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rsi_at_entry": 55.3,
        "volume_ratio": 2.1,
        "atr_at_entry": 0.025,
        "fear_greed": 65,
        "funding_rate": 0.0003,
        "orderbook_imbalance": 0.15,
        "mom30": 0.08,
        "rsi30": 0.55,
        "macd_hist_norm": 0.002,
    }

    print("Before backfill:")
    cov_before = compute_pick_coverage(test_pick)
    print(f"  Coverage: {cov_before['coverage_pct']*100:.1f}% ({cov_before['coverage_class']})")
    print(f"  Missing: {cov_before['missing_features']}")

    backfill_inline_features(test_pick)

    print("\nAfter backfill:")
    cov_after = compute_pick_coverage(test_pick)
    print(f"  Coverage: {cov_after['coverage_pct']*100:.1f}% ({cov_after['coverage_class']})")
    print(f"  Missing: {cov_after['missing_features']}")

    print("\nBatch test:")
    enforce_coverage([test_pick])
