#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Dynamic Stop-Loss Calibrator
=============================================
Learns optimal SL/TP distances from historical trade outcomes using
MAE (Maximum Adverse Excursion) and MFE (Maximum Favorable Excursion)
analysis on closed picks.

Key ideas:
  - Winning trades have a characteristic "max drawdown before recovery" (MAE).
  - Set SL just outside the 90th percentile of winner MAE so 90% of
    future winners survive.
  - Set TP at the 75th percentile of winner MFE.
  - Segment by symbol family, strategy family, volatility regime, and
    hour-of-day for granular calibration.

Persistence:
  Calibration state saved to data/sl_calibration.json so it carries
  across GH Actions runs (committed to git).

Usage:
  from sl_calibrator import get_calibrated_sl, get_calibrated_tp, recalibrate
  sl_pct = get_calibrated_sl("BTCUSDT", "keltner_breakout", atr_pct=0.025)
  tp_pct = get_calibrated_tp("BTCUSDT", "keltner_breakout", atr_pct=0.025)
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
CALIBRATION_PATH = DATA_DIR / "sl_calibration.json"
CLOSED_PICKS_PATH = DATA_DIR / "closed_picks.json"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_STOP_DISTANCE_PCT = 0.12       # 12% hard cap (allows ATR-based stops to work)
MIN_TRADES_FOR_CALIBRATION = 30    # Need >= 30 closed trades for <15% CI width (KIMI review)
MIN_TRADES_PARENT_FALLBACK = 10    # Absolute minimum for parent-bucket fallback
MAE_PERCENTILE = 90                # Set SL at 90th percentile of winner MAE
MFE_PERCENTILE = 75                # Set TP at 75th percentile of winner MFE
MAE_BUFFER = 1.1                   # 10% buffer beyond the percentile
MIN_RR_RATIO = 1.5                 # Minimum reward:risk ratio enforced

# Time-decay for weighting recent trades more heavily in MAE/MFE analysis
# weight = exp(-TIME_DECAY_LAMBDA * age_days), so a 30-day-old trade has weight ~0.41
TIME_DECAY_LAMBDA = 0.03

# ---------------------------------------------------------------------------
# Symbol family classification
# ---------------------------------------------------------------------------
_BTC_FAMILY = {"BTC-USD", "BTCUSDT", "BTC"}
_MAJOR_ALTS = {"ETH-USD", "ETHUSDT", "ETH", "SOL-USD", "SOLUSDT", "SOL",
               "BNB-USD", "BNBUSDT", "BNB"}
_MEME_FAMILY = {"DOGE-USD", "DOGEUSDT", "PEPE-USD", "PEPEUSDT",
                "TRUMP-USD", "TRUMPUSDT", "WIF-USD", "WIFUSDT",
                "BONK-USD", "BONKUSDT", "FLOKI-USD", "FLOKIUSDT"}
_FOREX_FAMILY = {"EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X",
                 "USDCAD=X", "NZDUSD=X", "USDCHF=X", "EURJPY=X",
                 "GBPJPY=X", "AUDJPY=X"}


def _symbol_family(symbol: str) -> str:
    """Map a symbol to a broad family for grouping."""
    s = symbol.upper()
    if s in _BTC_FAMILY or s.startswith("BTC"):
        return "btc"
    if s in _MAJOR_ALTS:
        return "major_alt"
    if s in _MEME_FAMILY:
        return "meme"
    if s in _FOREX_FAMILY or s.endswith("=X"):
        return "forex"
    if any(s.startswith(p) for p in ("AAPL", "MSFT", "NVDA", "TSLA", "AMZN",
                                      "GOOGL", "META", "AMD")):
        return "equity"
    # Default: crypto altcoin
    return "alt_crypto"


def _strategy_family(strategy: str) -> str:
    """Map a strategy name to a broad family."""
    s = strategy.lower()
    momentum_kw = ("momentum", "breakout", "ema_stack", "keltner", "acceleration",
                   "trend", "bos", "choch", "sfp")
    reversion_kw = ("mean_rev", "rsi_bounce", "bollinger", "reversion", "oversold",
                    "overbought", "squeeze")
    onchain_kw = ("mvrv", "hash_ribbon", "whale", "netflow", "exchange_flow",
                  "on_chain", "onchain")

    for kw in momentum_kw:
        if kw in s:
            return "momentum"
    for kw in reversion_kw:
        if kw in s:
            return "mean_reversion"
    for kw in onchain_kw:
        if kw in s:
            return "onchain"
    return "other"


def _vol_regime_bucket(atr_pct: Optional[float]) -> str:
    """Classify volatility regime from ATR percentage."""
    if atr_pct is None or atr_pct <= 0:
        return "unknown"
    if atr_pct < 0.01:
        return "low"
    if atr_pct < 0.03:
        return "medium"
    if atr_pct < 0.06:
        return "high"
    return "extreme"


def _hour_bucket(hour_utc: Optional[int]) -> str:
    """Classify hour into session buckets."""
    if hour_utc is None:
        return "unknown"
    if 0 <= hour_utc < 8:
        return "asia"
    if 8 <= hour_utc < 14:
        return "europe"
    if 14 <= hour_utc < 21:
        return "us"
    return "late_us"


def _percentile(values: list[float], pct: float) -> float:
    """Compute the pct-th percentile of a sorted list (0-100 scale)."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (pct / 100.0) * (len(sorted_vals) - 1)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


# ---------------------------------------------------------------------------
# Load / save calibration state
# ---------------------------------------------------------------------------
_calibration_cache: Optional[dict] = None


def _load_calibration() -> dict:
    """Load calibration state from JSON, or return empty dict."""
    global _calibration_cache
    if _calibration_cache is not None:
        return _calibration_cache
    if CALIBRATION_PATH.exists():
        try:
            with open(CALIBRATION_PATH, "r", encoding="utf-8", errors="replace") as f:
                _calibration_cache = json.load(f)
                return _calibration_cache
        except (json.JSONDecodeError, OSError):
            pass
    _calibration_cache = {}
    return _calibration_cache


def _save_calibration(cal: dict) -> None:
    """Persist calibration state to JSON."""
    global _calibration_cache
    _calibration_cache = cal
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    cal["_updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(CALIBRATION_PATH, "w", encoding="utf-8") as f:
        json.dump(cal, f, indent=2, default=str)


def _load_closed_picks() -> list[dict]:
    """Load closed picks, handling merge-conflict markers and encoding issues."""
    if not CLOSED_PICKS_PATH.exists():
        return []
    try:
        with open(CLOSED_PICKS_PATH, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()
        # Strip git merge conflict markers and the "theirs" side content
        # Keep "ours" (before =======), discard "theirs" (between ======= and >>>>>>>)
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
        print(f"  [SL_CAL] Warning: could not load closed_picks.json: {e}")
        return []


# ---------------------------------------------------------------------------
# Core calibration engine
# ---------------------------------------------------------------------------

def _compute_age_weight(pick: dict, now: datetime) -> float:
    """Compute time-decay weight for a closed pick.

    weight = exp(-TIME_DECAY_LAMBDA * age_days)
    Recent trades get weight ~1.0, 30-day-old trades ~0.41, 60-day ~0.17.
    """
    ts = pick.get("closed_at") or pick.get("timestamp", "")
    if not ts:
        return 0.5  # unknown age -> moderate weight
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age_days = max((now - dt).total_seconds() / 86400.0, 0.0)
        return math.exp(-TIME_DECAY_LAMBDA * age_days)
    except (ValueError, TypeError):
        return 0.5


def _weighted_percentile(values: list[float], weights: list[float], pct: float) -> float:
    """Compute the pct-th weighted percentile (0-100 scale).

    Uses linear interpolation on cumulative weights, equivalent to
    numpy's 'linear' interpolation but weight-aware.
    """
    if not values or not weights:
        return 0.0
    # Sort by value, carry weights along
    paired = sorted(zip(values, weights), key=lambda x: x[0])
    sorted_vals = [p[0] for p in paired]
    sorted_wts = [p[1] for p in paired]
    cum_wt = []
    running = 0.0
    for w in sorted_wts:
        running += w
        cum_wt.append(running)
    total_wt = cum_wt[-1]
    if total_wt <= 0:
        return _percentile(values, pct)  # fallback to unweighted
    # Normalize cumulative weights to 0-1 range (midpoint convention)
    norm = [(cum_wt[i] - sorted_wts[i] / 2.0) / total_wt for i in range(len(sorted_vals))]
    target = pct / 100.0
    # Find interpolation bounds
    if target <= norm[0]:
        return sorted_vals[0]
    if target >= norm[-1]:
        return sorted_vals[-1]
    for i in range(len(norm) - 1):
        if norm[i] <= target <= norm[i + 1]:
            frac = (target - norm[i]) / (norm[i + 1] - norm[i]) if norm[i + 1] != norm[i] else 0.0
            return sorted_vals[i] + frac * (sorted_vals[i + 1] - sorted_vals[i])
    return sorted_vals[-1]


def recalibrate() -> dict:
    """
    Re-analyze all closed picks and rebuild the calibration table.

    Groups trades by (symbol_family, strategy_family) and optionally
    by (vol_regime, hour_bucket) for finer granularity.

    Uses time-decay weighting so recent trades matter more (KIMI review).
    Two-tier minimum: 30 winners for full calibration, 10 for parent-bucket fallback.

    Returns the full calibration dict (also saved to disk).
    """
    closed = _load_closed_picks()
    if not closed:
        print("  [SL_CAL] No closed picks found -- using defaults")
        _save_calibration({"groups": {}, "total_analyzed": 0})
        return {"groups": {}, "total_analyzed": 0}

    now = datetime.now(timezone.utc)

    # Build groups
    groups: dict[str, dict] = {}

    for pick in closed:
        status = str(pick.get("status", "")).upper()
        if status not in ("WON", "LOST"):
            continue

        symbol = pick.get("symbol", "")
        strategy = pick.get("strategy", "")
        entry = pick.get("entry_price", 0)
        if not symbol or not strategy or not entry or entry <= 0:
            continue

        sym_fam = _symbol_family(symbol)
        strat_fam = _strategy_family(strategy)

        # MAE is stored as negative (max adverse), MFE as positive (max favorable)
        mae_raw = pick.get("mae", 0)
        mfe_raw = pick.get("mfe", 0)

        # Normalize to positive percentages
        mae_pct = abs(float(mae_raw)) if mae_raw else 0.0
        mfe_pct = abs(float(mfe_raw)) if mfe_raw else 0.0

        # Skip picks with no excursion data (never tracked)
        if mae_pct == 0.0 and mfe_pct == 0.0:
            continue

        # Time-decay weight: recent trades matter more
        weight = _compute_age_weight(pick, now)

        # Determine vol regime from ATR at entry
        atr_at_entry = pick.get("atr_at_entry")
        if atr_at_entry and entry > 0:
            atr_pct = float(atr_at_entry) / entry
        else:
            atr_pct = None
        vol_regime = _vol_regime_bucket(atr_pct)

        # Hour bucket from timestamp
        hour_utc = None
        ts = pick.get("timestamp", "")
        if ts:
            try:
                dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                hour_utc = dt.hour
            except (ValueError, TypeError):
                pass
        hour_bkt = _hour_bucket(hour_utc)

        is_winner = (status == "WON")

        # Primary key: symbol_family + strategy_family
        primary_key = f"{sym_fam}::{strat_fam}"
        # Secondary keys for finer granularity
        vol_key = f"{sym_fam}::{strat_fam}::{vol_regime}"
        hour_key = f"{sym_fam}::{strat_fam}::{hour_bkt}"

        for gkey in (primary_key, vol_key, hour_key):
            if gkey not in groups:
                groups[gkey] = {
                    "winner_mae": [],
                    "winner_mfe": [],
                    "winner_weights": [],
                    "loser_mae": [],
                    "loser_mfe": [],
                    "total": 0,
                    "wins": 0,
                }
            g = groups[gkey]
            g["total"] += 1
            if is_winner:
                g["wins"] += 1
                g["winner_mae"].append(mae_pct)
                g["winner_mfe"].append(mfe_pct)
                g["winner_weights"].append(weight)
            else:
                g["loser_mae"].append(mae_pct)
                g["loser_mfe"].append(mfe_pct)

    # Compute optimal SL/TP per group
    # Two-tier calibration: full (>=30 winners), fallback (>=10 winners)
    calibrated: dict[str, dict] = {}
    for gkey, g in groups.items():
        n_winners = len(g["winner_mae"])
        entry = {
            "total_trades": g["total"],
            "wins": g["wins"],
            "win_rate": round(g["wins"] / g["total"], 4) if g["total"] > 0 else 0,
        }

        # Determine calibration tier
        if n_winners >= MIN_TRADES_FOR_CALIBRATION:
            cal_tier = "full"
        elif n_winners >= MIN_TRADES_PARENT_FALLBACK:
            cal_tier = "fallback"
        else:
            cal_tier = None

        if cal_tier is not None:
            weights = g["winner_weights"]

            # MAE analysis: 90th weighted percentile of winner MAE * buffer
            optimal_sl = _weighted_percentile(g["winner_mae"], weights, MAE_PERCENTILE) * MAE_BUFFER
            optimal_sl = min(optimal_sl, MAX_STOP_DISTANCE_PCT)
            entry["optimal_sl_pct"] = round(optimal_sl, 6)
            entry["mae_p50"] = round(_weighted_percentile(g["winner_mae"], weights, 50), 6)
            entry["mae_p90"] = round(_weighted_percentile(g["winner_mae"], weights, 90), 6)

            # MFE analysis: 75th weighted percentile of winner MFE
            optimal_tp = _weighted_percentile(g["winner_mfe"], weights, MFE_PERCENTILE)
            # Enforce minimum R:R
            if optimal_sl > 0 and optimal_tp / optimal_sl < MIN_RR_RATIO:
                optimal_tp = optimal_sl * MIN_RR_RATIO
            entry["optimal_tp_pct"] = round(optimal_tp, 6)
            entry["mfe_p50"] = round(_weighted_percentile(g["winner_mfe"], weights, 50), 6)
            entry["mfe_p75"] = round(_weighted_percentile(g["winner_mfe"], weights, 75), 6)
            entry["calibrated"] = True
            entry["calibration_tier"] = cal_tier
            if cal_tier == "fallback":
                entry["note"] = (f"parent-bucket fallback ({n_winners} winners, "
                                 f"need {MIN_TRADES_FOR_CALIBRATION} for full calibration)")
        else:
            entry["calibrated"] = False
            entry["reason"] = (f"insufficient_data ({n_winners} winners, "
                               f"need {MIN_TRADES_PARENT_FALLBACK} minimum)")

        calibrated[gkey] = entry

    result = {
        "groups": calibrated,
        "total_analyzed": len(closed),
        "total_groups": len(calibrated),
    }
    _save_calibration(result)
    n_full = sum(1 for v in calibrated.values() if v.get("calibration_tier") == "full")
    n_fallback = sum(1 for v in calibrated.values() if v.get("calibration_tier") == "fallback")
    print(f"  [SL_CAL] Calibrated {n_full} full + {n_fallback} fallback / "
          f"{len(calibrated)} groups from {len(closed)} closed picks")
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_calibrated_sl(
    symbol: str,
    strategy: str,
    atr_pct: float,
    hour_utc: Optional[int] = None,
    vol_regime: Optional[str] = None,
    entry_quality: Optional[float] = None,
) -> float:
    """
    Return the recommended stop-loss distance as a percentage (0.0 - 0.02).

    Lookup order (most specific first):
      1. symbol_family::strategy_family::vol_regime
      2. symbol_family::strategy_family::hour_bucket
      3. symbol_family::strategy_family  (primary)
      4. Fallback: min(atr_pct * 1.5, MAX_STOP_DISTANCE_PCT)

    Adjustments applied after lookup:
      - Entry quality: poor entries (<0.3) tighten by 20%, excellent (>0.7) widen by 10%
      - Session-based: Asian tighter (0.9x), US wider (1.1x)
      - ATR safety floor: never less than atr_pct * 0.5

    Args:
        symbol: Trading symbol (e.g. "BTC-USD", "ETHUSDT")
        strategy: Strategy name (e.g. "keltner_breakout")
        atr_pct: Current ATR as percentage of price
        hour_utc: Current hour in UTC (0-23)
        vol_regime: Override vol regime string ("low"/"medium"/"high"/"extreme")
        entry_quality: Entry timing score 0-1 from entry optimizer (None = no adjustment)

    Returns:
        SL distance as a float percentage (e.g. 0.015 = 1.5%)
    """
    cal = _load_calibration()
    groups = cal.get("groups", {})

    sym_fam = _symbol_family(symbol)
    strat_fam = _strategy_family(strategy)

    # Determine vol regime from atr_pct if not provided
    if vol_regime is None:
        vol_regime = _vol_regime_bucket(atr_pct)

    hour_bkt = _hour_bucket(hour_utc)

    # Lookup chain: most specific -> least specific
    lookup_keys = [
        f"{sym_fam}::{strat_fam}::{vol_regime}",
        f"{sym_fam}::{strat_fam}::{hour_bkt}",
        f"{sym_fam}::{strat_fam}",
    ]

    sl_distance = None
    for key in lookup_keys:
        entry = groups.get(key, {})
        if entry.get("calibrated") and "optimal_sl_pct" in entry:
            sl_distance = min(entry["optimal_sl_pct"], MAX_STOP_DISTANCE_PCT)
            break

    # Fallback: ATR-based
    if sl_distance is None:
        sl_distance = min(atr_pct * 1.5, MAX_STOP_DISTANCE_PCT)

    # --- Entry quality adjustment ---
    # Poor entries need quicker exits; excellent entries deserve more room
    if entry_quality is not None:
        if entry_quality < 0.3:
            sl_distance *= 0.8   # tighten 20%
        elif entry_quality > 0.7:
            sl_distance *= 1.1   # widen 10%

    # --- Session-based SL adjustment ---
    if hour_utc is not None:
        if 0 <= hour_utc < 8:
            sl_distance *= 0.9    # Asian session: tighter (lower vol)
        elif 16 <= hour_utc < 24:
            sl_distance *= 1.1    # US session: wider (higher vol)
        # European session (8-16): no adjustment

    # --- ATR safety floor ---
    # Prevent overly tight stops that get hit by normal market noise
    sl_distance = max(sl_distance, atr_pct * 0.5)

    # Final hard cap
    sl_distance = min(sl_distance, MAX_STOP_DISTANCE_PCT)

    return sl_distance


def get_calibrated_tp(
    symbol: str,
    strategy: str,
    atr_pct: float,
) -> float:
    """
    Return the recommended take-profit distance as a percentage.

    Uses MFE analysis on winners. Enforces minimum R:R of 1.5.

    Args:
        symbol: Trading symbol
        strategy: Strategy name
        atr_pct: Current ATR as percentage of price

    Returns:
        TP distance as a float percentage (e.g. 0.03 = 3%)
    """
    cal = _load_calibration()
    groups = cal.get("groups", {})

    sym_fam = _symbol_family(symbol)
    strat_fam = _strategy_family(strategy)

    # Primary key lookup
    primary_key = f"{sym_fam}::{strat_fam}"
    entry = groups.get(primary_key, {})

    if entry.get("calibrated") and "optimal_tp_pct" in entry:
        tp = entry["optimal_tp_pct"]
        # Enforce minimum R:R against the calibrated SL
        sl = get_calibrated_sl(symbol, strategy, atr_pct)
        if sl > 0 and tp / sl < MIN_RR_RATIO:
            tp = sl * MIN_RR_RATIO
        return tp

    # Fallback: ATR * 3 (gives ~2:1 RR with default SL of ATR * 1.5)
    fallback_sl = min(atr_pct * 1.5, MAX_STOP_DISTANCE_PCT)
    return max(atr_pct * 3.0, fallback_sl * MIN_RR_RATIO)


# ---------------------------------------------------------------------------
# Integration helper for forward_validator.py
# ---------------------------------------------------------------------------

def apply_calibrated_sl_tp(pick: dict, entry_quality: Optional[float] = None) -> bool:
    """
    Apply calibrated SL/TP to a pick dict in-place.

    Only overrides if the calibrated value is TIGHTER (more conservative)
    than the current value. Returns True if any adjustment was made.

    Expects pick to have: symbol, strategy, entry_price, stop_loss, take_profit,
    direction, atr_at_entry (optional).

    Args:
        pick: The pick dict to calibrate in-place.
        entry_quality: Entry timing score 0-1 from entry optimizer (None = no adjustment).
    """
    symbol = pick.get("symbol", "")
    strategy = pick.get("strategy", "")
    entry = pick.get("entry_price", 0)
    direction = str(pick.get("direction", "LONG")).upper()

    if not symbol or not strategy or not entry or entry <= 0:
        return False

    current_sl = pick.get("stop_loss")
    current_tp = pick.get("take_profit")
    if not current_sl or not current_tp:
        return False

    # Compute ATR percentage
    atr_at_entry = pick.get("atr_at_entry")
    if atr_at_entry and float(atr_at_entry) > 0:
        atr_pct = float(atr_at_entry) / entry
    else:
        # Estimate from current SL distance
        atr_pct = abs(entry - current_sl) / entry

    # Get hour from timestamp
    hour_utc = None
    ts = pick.get("timestamp", "")
    if ts:
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            hour_utc = dt.hour
        except (ValueError, TypeError):
            pass

    cal_sl_pct = get_calibrated_sl(symbol, strategy, atr_pct, hour_utc=hour_utc,
                                    entry_quality=entry_quality)
    cal_tp_pct = get_calibrated_tp(symbol, strategy, atr_pct)

    # Convert percentages to price levels
    if direction in ("LONG", "BUY"):
        cal_sl_price = entry * (1.0 - cal_sl_pct)
        cal_tp_price = entry * (1.0 + cal_tp_pct)
    else:  # SHORT / SELL
        cal_sl_price = entry * (1.0 + cal_sl_pct)
        cal_tp_price = entry * (1.0 - cal_tp_pct)

    adjusted = False

    # Only tighten SL (closer to entry)
    current_sl_dist = abs(current_sl - entry)
    cal_sl_dist = abs(cal_sl_price - entry)
    if 0 < cal_sl_dist < current_sl_dist:
        old_sl = current_sl
        pick["stop_loss_pre_calibration"] = current_sl
        pick["stop_loss"] = round(cal_sl_price, 8)
        print(f"  [SL_CAL] SL calibrated: {symbol} {strategy} "
              f"ATR-based={old_sl:.4f} calibrated={cal_sl_price:.4f}")
        adjusted = True

    # Only tighten TP (closer to entry)
    current_tp_dist = abs(current_tp - entry)
    cal_tp_dist = abs(cal_tp_price - entry)
    if 0 < cal_tp_dist < current_tp_dist:
        old_tp = current_tp
        pick["take_profit_pre_calibration"] = current_tp
        pick["take_profit"] = round(cal_tp_price, 8)
        print(f"  [SL_CAL] TP calibrated: {symbol} {strategy} "
              f"ATR-based={old_tp:.4f} calibrated={cal_tp_price:.4f}")
        adjusted = True

    if adjusted:
        pick["sl_tp_calibrated"] = True
        # Recalculate R:R after calibration
        new_tp = pick.get("take_profit", 0)
        new_sl = pick.get("stop_loss", 0)
        if new_tp and new_sl and entry:
            tp_dist = abs(new_tp - entry)
            sl_dist = abs(new_sl - entry)
            if sl_dist > 0:
                pick["risk_reward"] = round(tp_dist / sl_dist, 2)

    return adjusted


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  SL Calibrator -- Self-Test")
    print("=" * 60)

    # Test percentile
    assert abs(_percentile([1, 2, 3, 4, 5], 50) - 3.0) < 0.01
    assert abs(_percentile([1, 2, 3, 4, 5], 90) - 4.6) < 0.01
    print("  Percentile: OK")

    # Test weighted percentile (uniform weights = same as unweighted)
    wp = _weighted_percentile([1, 2, 3, 4, 5], [1.0, 1.0, 1.0, 1.0, 1.0], 50)
    assert abs(wp - 3.0) < 0.3, f"Weighted percentile (uniform) expected ~3.0, got {wp}"
    # Test weighted percentile (heavy weight on high values shifts up)
    wp_skew = _weighted_percentile([1, 2, 3, 4, 5], [0.1, 0.1, 0.1, 0.1, 10.0], 50)
    assert wp_skew > 3.0, f"Weighted percentile (skewed) expected >3.0, got {wp_skew}"
    print(f"  Weighted percentile: OK (uniform={wp:.2f}, skewed={wp_skew:.2f})")

    # Test time-decay weight
    now_test = datetime.now(timezone.utc)
    recent_pick = {"timestamp": now_test.isoformat()}
    from datetime import timedelta as _td
    old_pick = {"timestamp": (now_test - _td(days=30)).isoformat()}
    w_recent = _compute_age_weight(recent_pick, now_test)
    w_old = _compute_age_weight(old_pick, now_test)
    assert 0.95 < w_recent <= 1.0, f"Recent weight expected ~1.0, got {w_recent}"
    assert 0.3 < w_old < 0.5, f"30-day weight expected ~0.41, got {w_old}"
    print(f"  Time-decay: recent={w_recent:.4f}, 30d={w_old:.4f}")

    # Verify minimum trades thresholds
    assert MIN_TRADES_FOR_CALIBRATION == 30, f"Full calibration min should be 30, got {MIN_TRADES_FOR_CALIBRATION}"
    assert MIN_TRADES_PARENT_FALLBACK == 10, f"Fallback min should be 10, got {MIN_TRADES_PARENT_FALLBACK}"
    print(f"  Min trades: full={MIN_TRADES_FOR_CALIBRATION}, fallback={MIN_TRADES_PARENT_FALLBACK}")

    # Test symbol family
    assert _symbol_family("BTC-USD") == "btc"
    assert _symbol_family("ETH-USD") == "major_alt"
    assert _symbol_family("DOGEUSDT") == "meme"
    assert _symbol_family("EURUSD=X") == "forex"
    assert _symbol_family("RENDERUSDT") == "alt_crypto"
    print("  Symbol family: OK")

    # Test strategy family
    assert _strategy_family("keltner_breakout") == "momentum"
    assert _strategy_family("rsi_bounce_oversold") == "mean_reversion"
    assert _strategy_family("mvrv_sma_proxy") == "onchain"
    assert _strategy_family("ml_enhanced_xyz") == "other"
    print("  Strategy family: OK")

    # Test fallback (no calibration data)
    # Fallback = min(atr*1.5, 0.02) = min(0.0375, 0.02) = 0.02
    # ATR floor = max(0.02, 0.025*0.5) = max(0.02, 0.0125) = 0.02
    sl = get_calibrated_sl("BTC-USD", "keltner_breakout", 0.025)
    assert sl == min(0.025 * 1.5, 0.02), f"Expected fallback SL, got {sl}"
    print(f"  Fallback SL: {sl:.4f} (ATR*1.5 capped at 2%)")

    # Test entry quality adjustments
    sl_poor = get_calibrated_sl("BTC-USD", "keltner_breakout", 0.01, entry_quality=0.2)
    sl_good = get_calibrated_sl("BTC-USD", "keltner_breakout", 0.01, entry_quality=0.8)
    sl_none = get_calibrated_sl("BTC-USD", "keltner_breakout", 0.01, entry_quality=None)
    assert sl_poor < sl_none, f"Poor entry SL ({sl_poor}) should be < neutral ({sl_none})"
    assert sl_good > sl_none, f"Good entry SL ({sl_good}) should be > neutral ({sl_none})"
    print(f"  Entry quality: poor={sl_poor:.4f} neutral={sl_none:.4f} good={sl_good:.4f}")

    # Test session-based adjustment
    sl_asia = get_calibrated_sl("BTC-USD", "keltner_breakout", 0.01, hour_utc=4)
    sl_euro = get_calibrated_sl("BTC-USD", "keltner_breakout", 0.01, hour_utc=12)
    sl_us = get_calibrated_sl("BTC-USD", "keltner_breakout", 0.01, hour_utc=20)
    assert sl_asia < sl_euro, f"Asian SL ({sl_asia}) should be < European ({sl_euro})"
    assert sl_us > sl_euro, f"US SL ({sl_us}) should be > European ({sl_euro})"
    print(f"  Session: asia={sl_asia:.4f} europe={sl_euro:.4f} us={sl_us:.4f}")

    # Test ATR safety floor
    sl_tiny_atr = get_calibrated_sl("BTC-USD", "keltner_breakout", 0.005, entry_quality=0.1)
    assert sl_tiny_atr >= 0.005 * 0.5, f"SL ({sl_tiny_atr}) must be >= ATR floor ({0.005*0.5})"
    print(f"  ATR floor: SL={sl_tiny_atr:.4f} (floor={0.005*0.5:.4f})")

    tp = get_calibrated_tp("BTC-USD", "keltner_breakout", 0.025)
    assert tp >= sl * 1.5, f"TP {tp} must be >= SL*1.5 ({sl*1.5})"
    print(f"  Fallback TP: {tp:.4f}")

    # Run calibration on actual closed picks
    print("\n  Running recalibration...")
    result = recalibrate()
    print(f"  Analyzed: {result.get('total_analyzed', 0)} picks")
    print(f"  Groups: {result.get('total_groups', 0)}")

    cal_groups = result.get("groups", {})
    for key, val in sorted(cal_groups.items()):
        if val.get("calibrated"):
            print(f"    {key}: SL={val.get('optimal_sl_pct', 0):.4f} "
                  f"TP={val.get('optimal_tp_pct', 0):.4f} "
                  f"WR={val.get('win_rate', 0):.1%} "
                  f"({val.get('total_trades', 0)} trades)")

    print("\n  All tests passed.")
