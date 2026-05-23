"""
ANTIGRAVITY Live Picks Tracker — Forward-Looking Predictions
=============================================================
Generates REAL predictions (not backtested), logs them with timestamps,
and tracks outcomes for honest forward vs backtest comparison.

Every pick is:
  1. Generated from trained models at prediction time
  2. Logged with exact entry price, TP, SL, confidence
  3. Tracked until TP hit, SL hit, or time expired
  4. Outcome recorded for forward Sharpe calculation

This produces the ONLY honest metric: forward-looking, non-projected results.
"""

import json
import time
import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional

try:
    import requests
    import numpy as np
    import pandas as pd
    import joblib
except ImportError as e:
    print(f"[live_picks] Missing dependency: {e}")
    sys.exit(1)

BASE = Path(__file__).resolve().parent
MODELS_DIR = BASE / "models"
RESULTS_DIR = BASE / "results"
DATA_DIR = BASE / "data"
PICKS_DIR = BASE / "live_picks"
PICKS_DIR.mkdir(parents=True, exist_ok=True)

# Files
ACTIVE_PICKS_FILE = PICKS_DIR / "active_picks.json"
CLOSED_PICKS_FILE = PICKS_DIR / "closed_picks.json"
PICKS_LOG_FILE = PICKS_DIR / "all_picks_log.json"
FORWARD_STATS_FILE = PICKS_DIR / "forward_stats.json"

from .config import CRYPTO_PAIRS, TIMEFRAMES, TPSL_CONFIG, BINANCE_SPOT_BASE
from .data_fetcher import fetch_klines
from .feature_engine import build_features
from .meta_labeler import apply_meta_filter
import math

# Feedback model integration (learns from closed trade outcomes)
try:
    from .feedback_trainer import predict_outcome as feedback_predict
    HAS_FEEDBACK_MODEL = True
except ImportError:
    HAS_FEEDBACK_MODEL = False


def _sanitize_features(features_row) -> dict:
    """Convert a feature row (Series/array/dict) to JSON-safe dict (Design 3E)."""
    result = {}
    if hasattr(features_row, 'items'):
        # pandas Series or dict
        for k, v in features_row.items():
            try:
                val = float(v)
            except (TypeError, ValueError):
                val = 0.0
            if math.isnan(val) or math.isinf(val):
                val = 0.0
            result[str(k)] = val
    elif hasattr(features_row, '__len__'):
        # numpy array
        for i, v in enumerate(features_row):
            try:
                val = float(v)
            except (TypeError, ValueError):
                val = 0.0
            if math.isnan(val) or math.isinf(val):
                val = 0.0
            result[f"feature_{i}"] = val
    return result


def get_current_price(symbol: str) -> Optional[float]:
    """Get current price from Binance."""
    try:
        url = f"{BINANCE_SPOT_BASE}/api/v3/ticker/price"
        resp = requests.get(url, params={"symbol": symbol}, timeout=5)
        resp.raise_for_status()
        return float(resp.json()["price"])
    except Exception:
        return None


def load_json(path: Path) -> list:
    """Load JSON file, return empty list if not found."""
    if path.exists():
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return []


def save_json(path: Path, data) -> None:
    """Save JSON atomically."""
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, default=str)
    tmp.replace(path)


# ─── CONFIDENCE & QUALITY GATES ─────────────────────────────────────────────
# v1.3 POST-MORTEM (Feb 22 — 34 picks, 23.5% WR, -28.5% PnL):
#
# ROOT CAUSES:
#   1. 31/34 picks had prob < 0.60 — confidence gate wasn't enforced
#   2. Model selection picked most overconfident model, not best model
#   3. 1h BUY-only bias in falling market (11/12 picks = BUY, 1 won)
#   4. SELL signals actually worked (6/7 on 15m = TP_HIT) but were suppressed
#   5. SL not enforced in real-time → ZROUSDT lost -6.73% vs 2.16% SL
#
# FIXES v1.3/v1.6:
#   - Adjusted confidence to 0.55 (0.75 was mathematically impossible with probability scaling)
#   - Prefer A/B test winner model (C_random_forest) instead of highest prob
#   - Loosen BTC regime filter to catch slow downtrends
#   - Reduce MAX_PER_DIRECTION to 3 (was 5 — too much correlated risk)
#   - Add trend alignment filter (EMA20 vs EMA50 must agree with direction)
#   - Require higher confidence (≥0.60) for 1h picks specifically
MIN_DIRECTIONAL_CONFIDENCE = 0.55  # v1.6: Realistic boundary for calibrated models
MIN_DIRECTIONAL_CONFIDENCE_1H = 0.60  # v1.6: 1h needs higher bar (less noise)
# Fix #2: Minimum SL distance as % of entry price (prevents noise exits)
MIN_SL_DISTANCE_PCT = 0.008  # v1.3: raised 0.5%→0.8% (ZROUSDT gapped through 0.5%)
# Fix #4: Max concurrent picks per direction to avoid correlated risk
MAX_PER_DIRECTION = 3  # v98.1: RE-ENABLED
# Fix #6: Daily loss circuit breaker — stop after N consecutive losses
MAX_CONSECUTIVE_LOSSES = 8  # v1.6: 4 is too strict for normal ML drawdowns, raised to 8
# Fix #7: Pair blacklist — pairs with consistently bad results
PAIR_BLACKLIST_THRESHOLD = -2.0  # v1.3: tightened -3%→-2% (faster blacklist)
# Fix #8: Prefer A/B test winner model
PREFERRED_MODEL_VARIANT = "C_random_forest"  # A/B test winner (81 wins, 0.275 avg)
# Fix #9 (v1.4): Per-symbol dedup — never have same coin in BUY on two timeframes
# v1.2 lesson: BNB lost on 15m+1h+15m (3 picks!), ZRO lost -6.73% on BOTH 15m and 1h
MAX_PER_SYMBOL = 1  # v1.4: max 1 active pick per coin (was unlimited)
# Fix #10 (v1.4): Cross-timeframe conflict detection
# v1.2 lesson: LINK SELL won on 15m (+0.80%) but LINK BUY lost on 1h (-0.80%)
# When 15m says SELL and 1h says BUY, skip the weaker signal
REQUIRE_TF_AGREEMENT = True  # v1.4: block if existing pick has opposite direction


def _check_circuit_breaker() -> bool:
    """Check if we've hit MAX_CONSECUTIVE_LOSSES in recent closed picks."""
    closed = load_json(CLOSED_PICKS_FILE)
    if len(closed) < MAX_CONSECUTIVE_LOSSES:
        return False
    recent = closed[-MAX_CONSECUTIVE_LOSSES:]
    return all(p.get("actual_pnl_pct", 0) <= 0 for p in recent)


def _is_pair_blacklisted(pair: str) -> bool:
    """Check if a pair has been consistently losing in forward picks."""
    closed = load_json(CLOSED_PICKS_FILE)
    pair_picks = [p for p in closed if p.get("symbol") == pair]
    if len(pair_picks) < 2:
        return False
    total_pnl = sum(p.get("actual_pnl_pct", 0) for p in pair_picks)
    return total_pnl < PAIR_BLACKLIST_THRESHOLD


def generate_predictions() -> list:
    """
    Generate FORWARD-LOOKING predictions from all trained models.
    Returns a list of prediction dicts with entry, TP, SL, confidence.

    IMPROVEMENTS (v1.1 — post 0/5 loss review):
    - Probability threshold raised 0.45 → 0.60
    - Minimum SL distance enforced (0.5% of entry)
    - BTC regime filter: no BUY during confirmed bearish move
    - Max 3 concurrent picks per direction
    - Prefer 1h/4h over 15m (less noise)
    """
    from .data_fetcher import fetch_klines, fetch_fear_greed, fetch_funding_rates

    predictions = []
    now = datetime.now(timezone.utc)

    # Fetch market context
    fear_greed = fetch_fear_greed()
    funding_rates = fetch_funding_rates(CRYPTO_PAIRS[:10])

    # Fix #3: BTC Regime Filter — check if BTC is in a downtrend
    # v1.3: Loosened thresholds to catch slow downtrends (old: -0.5% 4h AND -0.2% 1h)
    # Feb 22 lesson: market drifted down slowly, old filter didn't trigger, 11/12 BUYs lost
    btc_regime_bearish = False
    btc_regime_bullish = False
    try:
        btc_1h = fetch_klines("BTCUSDT", "1h", 24)
        if not btc_1h.empty and len(btc_1h) >= 12:
            btc_close = btc_1h["close"].astype(float)
            btc_return_4h = (btc_close.iloc[-1] - btc_close.iloc[-4]) / btc_close.iloc[-4]
            btc_return_12h = (btc_close.iloc[-1] - btc_close.iloc[-12]) / btc_close.iloc[-12]
            # EMA trend check
            btc_ema20 = btc_close.ewm(span=20).mean().iloc[-1]
            btc_ema50 = btc_close.ewm(span=min(50, len(btc_close))).mean().iloc[-1]
            btc_below_emas = btc_close.iloc[-1] < btc_ema20 and btc_close.iloc[-1] < btc_ema50
            btc_above_emas = btc_close.iloc[-1] > btc_ema20 and btc_close.iloc[-1] > btc_ema50
            # v1.6: Bearish requires a more substantial drop or clear breakdown (1.5% in 4h AND below EMAs)
            if (btc_return_4h < -0.015 or btc_return_12h < -0.025) and btc_below_emas:
                btc_regime_bearish = True
                print(f"  [REGIME] BTC bearish: 4h={btc_return_4h:.3%} 12h={btc_return_12h:.3%} below_EMAs={btc_below_emas} — blocking BUY signals")
            elif btc_return_4h > 0.003 and btc_above_emas:
                btc_regime_bullish = True
                print(f"  [REGIME] BTC bullish: 4h={btc_return_4h:.3%} above EMAs — favoring BUY signals")
    except Exception as e:
        print(f"  [REGIME] BTC check failed: {e}")

    # Fix #5: Prefer 1h/4h over 15m — order by expected signal quality
    priority_tfs = ["1h", "4h", "1d", "15m"]

    for tf_name in priority_tfs:
        if tf_name not in TIMEFRAMES:
            continue
        tf_config = TIMEFRAMES[tf_name]
        tpsl = TPSL_CONFIG[tf_config["style"]]

        # Fetch BTC data for cross-features
        btc_df = fetch_klines("BTCUSDT", tf_config["interval"], min(tf_config["limit"], 1000))

        for pair in CRYPTO_PAIRS:
            # Check if model exists for any variant
            model_files = list(MODELS_DIR.glob(f"{pair}_{tf_name}_*.joblib"))
            if not model_files:
                continue

            # Fetch latest data
            df = fetch_klines(pair, tf_config["interval"], min(tf_config["limit"], 1000))
            if df.empty or len(df) < 300:
                continue

            # Build features for latest candle
            funding = funding_rates.get(pair, 0.0)
            features = build_features(df, btc_df=btc_df,
                                       fear_greed=fear_greed,
                                       funding_rate=funding)
            if features.empty:
                continue

            # Get the latest feature row
            latest_features = features.iloc[[-1]]

            # Load models and predict — PREFER A/B TEST WINNER
            # v1.3 FIX: Old logic picked highest prob_up (most overconfident model)
            # An overfit model predicting 85% always "won" selection → bad picks
            # New logic: prefer the A/B test winner, fall back to consensus
            model_predictions = {}  # variant → prob_up

            for model_path in model_files:
                try:
                    model = joblib.load(model_path)
                    # Handle feature name mismatches
                    if hasattr(model, 'feature_names_in_'):
                        missing = set(model.feature_names_in_) - set(latest_features.columns)
                        if missing:
                            for col in missing:
                                latest_features[col] = 0
                        feat_aligned = latest_features[model.feature_names_in_]
                    else:
                        feat_aligned = latest_features

                    proba = model.predict_proba(feat_aligned)
                    prob_up = proba[0][1] if proba.shape[1] > 1 else proba[0][0]
                    model_predictions[model_path.stem] = prob_up
                except Exception:
                    continue

            if not model_predictions:
                continue

            # v1.3: Prefer A/B test winner (C_random_forest), fall back to consensus
            preferred_key = None
            for key in model_predictions:
                if PREFERRED_MODEL_VARIANT in key:
                    preferred_key = key
                    break

            if preferred_key:
                best_prob = model_predictions[preferred_key]
                best_variant = preferred_key
            else:
                # Fall back to median prediction (consensus, not max — avoids overfit outlier)
                probs = list(model_predictions.values())
                median_prob = sorted(probs)[len(probs) // 2]
                # Find the model closest to median
                best_variant = min(model_predictions, key=lambda k: abs(model_predictions[k] - median_prob))
                best_prob = model_predictions[best_variant]

            if best_variant is None:
                continue

            # ─── DIRECTION + CONFIDENCE (v1.3 — stricter gates) ───
            # v1.3: Use higher threshold for 1h (was 8.3% WR at 0.60)
            conf_threshold = MIN_DIRECTIONAL_CONFIDENCE_1H if tf_name == "1h" else MIN_DIRECTIONAL_CONFIDENCE
            if best_prob >= conf_threshold:
                direction = "BUY"
                directional_confidence = best_prob
            elif best_prob <= (1.0 - conf_threshold):
                direction = "SELL"
                directional_confidence = 1.0 - best_prob  # prob_down
            else:
                # Coin flip zone — no edge, skip
                continue

            # v1.5: Meta-labeling filter (M2 trade/no-trade)
            try:
                should_trade, meta_conf = apply_meta_filter(
                    pair, tf_name, latest_features.values[0] if hasattr(latest_features, 'values') else latest_features.flatten(),
                    best_prob, list(features.columns) if hasattr(features, 'columns') else [],
                    threshold=0.55,
                )
                if not should_trade:
                    print(f"    [META-FILTER] {pair} {tf_name} blocked by M2 (meta_conf={meta_conf:.3f})")
                    continue
            except Exception:
                pass  # If meta model not available, proceed without filter

            # v1.3: Trend alignment filter — direction must agree with short-term EMA trend
            try:
                close_vals = df["close"].astype(float)
                pair_ema20 = close_vals.ewm(span=20).mean().iloc[-1]
                pair_ema50 = close_vals.ewm(span=50).mean().iloc[-1]
                if direction == "BUY" and pair_ema20 < pair_ema50:
                    # BUY signal against bearish EMA trend — require higher confidence
                    if directional_confidence < 0.60:
                        print(f"    [TREND FILTER] {pair} {tf_name} BUY against EMA trend (conf={directional_confidence:.2f}<0.60)")
                        continue
                if direction == "SELL" and pair_ema20 > pair_ema50:
                    # SELL signal against bullish EMA trend — require higher confidence
                    if directional_confidence < 0.60:
                        print(f"    [TREND FILTER] {pair} {tf_name} SELL against EMA trend (conf={directional_confidence:.2f}<0.60)")
                        continue
            except Exception:
                pass  # If EMA calc fails, proceed without filter

            # Fix #3: Block BUY signals during bearish regime
            if btc_regime_bearish and direction == "BUY":
                print(f"    [BLOCKED] {pair} {tf_name} BUY blocked — BTC bearish regime")
                continue
            # v1.3: Block SELL signals during strong bullish regime
            if btc_regime_bullish and direction == "SELL":
                if directional_confidence < 0.60:
                    print(f"    [BLOCKED] {pair} {tf_name} SELL blocked — BTC bullish regime (conf={directional_confidence:.2f}<0.60)")
                    continue

            # Fix #6: Check consecutive loss circuit breaker
            if _check_circuit_breaker():
                print(f"    [CIRCUIT BREAKER] {MAX_CONSECUTIVE_LOSSES} consecutive losses — pausing new picks")
                break  # Stop all new picks this cycle

            # Fix #7: Check pair blacklist
            if _is_pair_blacklisted(pair):
                print(f"    [BLACKLISTED] {pair} — forward PnL below {PAIR_BLACKLIST_THRESHOLD}%")
                continue

            current_price = get_current_price(pair)
            if current_price is None:
                current_price = float(df["close"].iloc[-1])

            # Calculate TP/SL based on ATR
            atr_val = float((df["high"] - df["low"]).rolling(14).mean().iloc[-1])

            # Fix #2: Enforce minimum SL distance
            min_sl_distance = current_price * MIN_SL_DISTANCE_PCT
            atr_sl = atr_val * tpsl["sl_atr_mult"]
            actual_sl_distance = max(atr_sl, min_sl_distance)

            # Scale TP proportionally to maintain R:R ratio
            rr_ratio = tpsl["tp_atr_mult"] / tpsl["sl_atr_mult"]
            actual_tp_distance = actual_sl_distance * rr_ratio

            if direction == "BUY":
                tp_price = current_price + actual_tp_distance
                sl_price = current_price - actual_sl_distance
            else:
                tp_price = current_price - actual_tp_distance
                sl_price = current_price + actual_sl_distance

            # Confidence level based on DIRECTIONAL confidence (works for both BUY & SELL)
            if directional_confidence >= 0.75:
                confidence = "HIGH"
            elif directional_confidence >= 0.65:
                confidence = "MEDIUM"
            else:
                confidence = "LOW"

            # Time horizon for this TF
            horizon_hours = {
                "15m": 2, "1h": 12, "4h": 48, "1d": 120
            }.get(tf_name, 24)

            # ─── Build reasoning: WHY was this pick selected? ───
            reasons = []
            try:
                close_vals = df["close"].astype(float)
                # RSI
                delta = close_vals.diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain.iloc[-1] / max(loss.iloc[-1], 1e-10)
                rsi = 100 - (100 / (1 + rs))
                if rsi < 30:
                    reasons.append(f"RSI oversold ({rsi:.0f})")
                elif rsi > 70:
                    reasons.append(f"RSI overbought ({rsi:.0f})")
                else:
                    reasons.append(f"RSI neutral ({rsi:.0f})")

                # EMA trend
                ema20 = close_vals.ewm(span=20).mean().iloc[-1]
                ema50 = close_vals.ewm(span=50).mean().iloc[-1]
                if ema20 > ema50:
                    reasons.append("EMA20 > EMA50 (bullish trend)")
                else:
                    reasons.append("EMA20 < EMA50 (bearish trend)")

                # Volume
                vol = df["volume"].astype(float)
                vol_ratio = vol.iloc[-1] / max(vol.rolling(20).mean().iloc[-1], 1e-10)
                if vol_ratio > 1.5:
                    reasons.append(f"Volume surge ({vol_ratio:.1f}x avg)")
                elif vol_ratio > 1.0:
                    reasons.append(f"Volume above avg ({vol_ratio:.1f}x)")
                else:
                    reasons.append(f"Volume below avg ({vol_ratio:.1f}x)")

                # ATR volatility context
                atr_pct = (atr_val / current_price) * 100
                reasons.append(f"ATR: {atr_pct:.2f}% of price")

                # Fear & Greed
                if fear_greed:
                    fg_val = fear_greed.get("value", "?")
                    fg_class = fear_greed.get("value_classification", "?")
                    reasons.append(f"Fear/Greed: {fg_val} ({fg_class})")

                # BTC regime
                if btc_regime_bearish:
                    reasons.append("BTC regime: BEARISH (SELL only)")
                else:
                    reasons.append("BTC regime: neutral/bullish")

                # Model info
                reasons.append(f"Model: {best_variant} (prob={best_prob:.3f})")
            except Exception:
                reasons.append(f"Model: {best_variant} (prob={best_prob:.3f})")

            # SL/TP reasoning
            sl_pct = abs(actual_sl_distance / current_price) * 100
            tp_pct = abs(actual_tp_distance / current_price) * 100
            reasons.append(f"R:R = {tp_pct:.2f}% TP / {sl_pct:.2f}% SL = {tp_pct/max(sl_pct,0.01):.1f}:1")

            # EST timestamp
            from zoneinfo import ZoneInfo
            est_now = now.astimezone(ZoneInfo("America/New_York"))

            prediction = {
                "id": f"{pair}_{tf_name}_{now.strftime('%Y%m%d_%H%M')}",
                "symbol": pair,
                "timeframe": tf_name,
                "direction": direction,
                "entry_price": round(current_price, 8),
                "take_profit": round(tp_price, 8),
                "stop_loss": round(sl_price, 8),
                "probability": round(directional_confidence, 4),
                "confidence": confidence,
                "features": _sanitize_features(latest_features.iloc[0]),
                "model_variant": best_variant,
                "generated_at": now.isoformat(),
                "generated_at_est": est_now.strftime("%Y-%m-%d %I:%M %p EST"),
                "expires_at": (now + timedelta(hours=horizon_hours)).isoformat(),
                "status": "ACTIVE",
                "current_price": round(current_price, 8),
                "unrealized_pnl_pct": 0.0,
                "outcome": None,
                "closed_at": None,
                "close_price": None,
                "actual_pnl_pct": None,
                "reasoning": reasons,
                "sl_distance_pct": round(sl_pct, 3),
                "tp_distance_pct": round(tp_pct, 3),
                "fear_greed": fear_greed.get("value", None) if isinstance(fear_greed, dict) else fear_greed,
                "btc_regime": "bearish" if btc_regime_bearish else "neutral",
            }

            # FEEDBACK FILTER: Use outcome model trained on 755+ closed trades
            # to predict whether this type of trade historically wins
            feedback_win_prob = None
            if HAS_FEEDBACK_MODEL:
                try:
                    fb_prob, fb_should_trade = feedback_predict(prediction)
                    feedback_win_prob = round(fb_prob, 4)
                    prediction["feedback_win_prob"] = feedback_win_prob
                    if not fb_should_trade:
                        print(f"    [FEEDBACK FILTER] {pair} {tf_name} {direction} "
                              f"blocked by outcome model (win_prob={fb_prob:.3f})")
                        reasons.append(f"BLOCKED by feedback model (win_prob={fb_prob:.2f})")
                        continue
                    else:
                        reasons.append(f"Feedback model: {fb_prob:.0%} win probability")
                except Exception as e:
                    print(f"    [FEEDBACK] Error: {e}")

            predictions.append(prediction)
            time.sleep(0.05)  # Rate limit

    return predictions


def update_active_picks() -> dict:
    """
    Check all active picks against current prices.
    Close picks that hit TP, SL, or expire.
    Returns summary stats.
    """
    active = load_json(ACTIVE_PICKS_FILE)
    closed = load_json(CLOSED_PICKS_FILE)
    now = datetime.now(timezone.utc)

    still_active = []
    newly_closed = []

    for pick in active:
        symbol = pick.get("symbol")
        # Normalize direction: LONG→BUY, SHORT→SELL (compat with live_predictor picks)
        direction = pick.get("direction", "BUY")
        if direction == "LONG":
            direction = "BUY"
        elif direction == "SHORT":
            direction = "SELL"

        # Skip picks missing required fields (stale schema from other systems)
        if not all(k in pick for k in ("entry_price", "take_profit", "stop_loss")):
            print(f"  [SKIP] {symbol} — missing TP/SL fields, dropping stale pick")
            continue

        # Get current price
        current = get_current_price(symbol)
        if current is None:
            still_active.append(pick)
            continue

        pick["current_price"] = round(current, 8)

        # Calculate unrealized PnL
        if direction == "BUY":
            pnl = (current - pick["entry_price"]) / pick["entry_price"]
        else:
            pnl = (pick["entry_price"] - current) / pick["entry_price"]
        pick["unrealized_pnl_pct"] = round(pnl * 100, 2)

        # Check TP hit
        tp_hit = False
        sl_hit = False
        expired = False

        if direction == "BUY":
            tp_hit = current >= pick["take_profit"]
            sl_hit = current <= pick["stop_loss"]
        else:
            tp_hit = current <= pick["take_profit"]
            sl_hit = current >= pick["stop_loss"]

        # Handle missing or invalid expires_at gracefully
        expires_at = pick.get("expires_at")
        if expires_at:
            try:
                expire_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                expired = now >= expire_time
            except (ValueError, AttributeError):
                # Default: expire after 48h if no valid timestamp
                gen_at = pick.get("generated_at", pick.get("timestamp", ""))
                if gen_at:
                    try:
                        gen_time = datetime.fromisoformat(gen_at.replace("Z", "+00:00"))
                        expired = now >= gen_time + timedelta(hours=48)
                    except (ValueError, AttributeError):
                        expired = True  # Can't parse, expire it
                else:
                    expired = True
        else:
            # No expires_at: expire after 48h from generation time
            gen_at = pick.get("generated_at", pick.get("timestamp", ""))
            if gen_at:
                try:
                    gen_time = datetime.fromisoformat(gen_at.replace("Z", "+00:00"))
                    expired = now >= gen_time + timedelta(hours=48)
                except (ValueError, AttributeError):
                    expired = True
            else:
                expired = True

        if tp_hit or sl_hit or expired:
            pick["status"] = "CLOSED"
            pick["closed_at"] = now.isoformat()
            pick["close_price"] = round(current, 8)
            pick["actual_pnl_pct"] = round(pnl * 100, 2)

            if tp_hit:
                pick["outcome"] = "TP_HIT"
            elif sl_hit:
                pick["outcome"] = "SL_HIT"
            else:
                pick["outcome"] = "EXPIRED"

            newly_closed.append(pick)
        else:
            still_active.append(pick)

        time.sleep(0.02)

    # Save updated state
    closed.extend(newly_closed)
    save_json(ACTIVE_PICKS_FILE, still_active)
    save_json(CLOSED_PICKS_FILE, closed)

    # Status-shard rotation (2026-05-14): roll newly-closed picks into the
    # cold monthly shard so the hot all_picks_log.json doesn't accumulate
    # terminal-status rows. Cold shards are gzipped JSON arrays at
    # ml_crypto_predictor/enhanced_models/live_picks/closed/closed_YYYYMM.json.gz.
    # See tools/migrate_all_picks_log.py for the one-shot migration and
    # the matching reader hook in audit_trail/dashboard_generator.py.
    if newly_closed:
        try:
            import gzip
            from collections import defaultdict
            cold_dir = PICKS_DIR / "closed"
            cold_dir.mkdir(parents=True, exist_ok=True)
            by_month = defaultdict(list)
            for p in newly_closed:
                ts = p.get("closed_at") or p.get("generated_at") or ""
                try:
                    dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    key = dt.strftime("%Y%m")
                except (ValueError, TypeError):
                    key = "unknown"
                by_month[key].append(p)
            for month, picks in by_month.items():
                shard = cold_dir / f"closed_{month}.json.gz"
                existing = []
                if shard.exists():
                    with gzip.open(shard, "rt", encoding="utf-8") as f:
                        existing = json.load(f) or []
                # dedup by id (newer write wins)
                seen = {str(p.get("id") or i): p for i, p in enumerate(existing)}
                for p in picks:
                    seen[str(p.get("id") or f"new_{p.get('symbol')}_{p.get('generated_at')}")] = p
                with gzip.open(shard, "wt", encoding="utf-8") as f:
                    json.dump(list(seen.values()), f, indent=2, default=str)
        except Exception as e:
            print(f"  [WARN] cold-shard rotation failed (non-fatal): {e}")

    # Calculate forward stats
    stats = calculate_forward_stats(closed)
    save_json(FORWARD_STATS_FILE, stats)

    return {
        "active": len(still_active),
        "newly_closed": len(newly_closed),
        "total_closed": len(closed),
        "stats": stats,
    }


def calculate_forward_stats(closed_picks: list) -> dict:
    """Calculate honest forward-looking statistics from closed picks."""
    if not closed_picks:
        return {
            "total_picks": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0,
            "avg_pnl_pct": 0,
            "total_pnl_pct": 0,
            "sharpe_ratio": 0,
            "profit_factor": 0,
            "max_drawdown_pct": 0,
            "tp_hits": 0,
            "sl_hits": 0,
            "expired": 0,
            "by_timeframe": {},
            "by_symbol": {},
            "vs_simpleton": {},
        }

    total = len(closed_picks)
    pnls = [p.get("actual_pnl_pct", 0) for p in closed_picks]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    win_rate = len(wins) / total * 100 if total > 0 else 0
    avg_pnl = sum(pnls) / total if total > 0 else 0
    total_pnl = sum(pnls)

    # Sharpe (annualized from trade frequency)
    if len(pnls) > 1:
        pnl_arr = np.array(pnls)
        if pnl_arr.std() > 0:
            sharpe = (pnl_arr.mean() / pnl_arr.std()) * np.sqrt(min(len(pnls), 252))
        else:
            sharpe = 0
    else:
        sharpe = 0

    # Profit factor
    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    # Max drawdown
    cum_pnl = np.cumsum(pnls)
    running_max = np.maximum.accumulate(cum_pnl)
    drawdowns = running_max - cum_pnl
    max_dd = float(drawdowns.max()) if len(drawdowns) > 0 else 0

    # Outcomes breakdown
    tp_hits = sum(1 for p in closed_picks if p.get("outcome") == "TP_HIT")
    sl_hits = sum(1 for p in closed_picks if p.get("outcome") == "SL_HIT")
    expired = sum(1 for p in closed_picks if p.get("outcome") == "EXPIRED")

    # By timeframe
    by_tf = {}
    for p in closed_picks:
        tf = p.get("timeframe", "unknown")
        if tf not in by_tf:
            by_tf[tf] = {"picks": 0, "wins": 0, "total_pnl": 0, "pnls": []}
        by_tf[tf]["picks"] += 1
        pnl_val = p.get("actual_pnl_pct", 0)
        by_tf[tf]["pnls"].append(pnl_val)
        by_tf[tf]["total_pnl"] += pnl_val
        if pnl_val > 0:
            by_tf[tf]["wins"] += 1

    for tf in by_tf:
        pnl_arr = np.array(by_tf[tf]["pnls"])
        by_tf[tf]["win_rate"] = round(by_tf[tf]["wins"] / by_tf[tf]["picks"] * 100, 1)
        if len(pnl_arr) > 1 and pnl_arr.std() > 0:
            by_tf[tf]["sharpe"] = round(float(pnl_arr.mean() / pnl_arr.std() * np.sqrt(min(len(pnl_arr), 252))), 2)
        else:
            by_tf[tf]["sharpe"] = 0
        del by_tf[tf]["pnls"]

    # Comparison vs Simpleton
    simpleton = {
        "simpleton_sharpe": 0.567,
        "simpleton_win_rate": 51.3,
        "simpleton_profit_factor": 1.09,
        "simpleton_max_dd": -34.1,
        "our_sharpe": round(sharpe, 3),
        "our_win_rate": round(win_rate, 1),
        "our_profit_factor": round(profit_factor, 2),
        "our_max_dd": round(-max_dd, 1),
        "beating_sharpe": True if sharpe > 0.567 else False,
        "beating_win_rate": True if win_rate > 51.3 else False,
        "beating_profit_factor": True if profit_factor > 1.09 else False,
        "beating_max_dd": True if max_dd < 34.1 else False,
    }

    return {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_picks": total,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 1),
        "avg_pnl_pct": round(avg_pnl, 2),
        "total_pnl_pct": round(total_pnl, 2),
        "sharpe_ratio": round(sharpe, 3),
        "profit_factor": round(profit_factor, 2),
        "max_drawdown_pct": round(-max_dd, 1),
        "tp_hits": tp_hits,
        "sl_hits": sl_hits,
        "expired": expired,
        "by_timeframe": by_tf,
        "vs_simpleton": simpleton,
    }


TRACKER_VERSION = "v1.5"  # v1.5: Triple Barrier, meta-labeling, calibration, purged CV, feature pruning

def run_prediction_cycle():
    """Full cycle: generate predictions + update existing picks."""
    print("=" * 70)
    print(f"ANTIGRAVITY LIVE PICKS {TRACKER_VERSION} — Prediction Cycle")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    # 1. Update existing active picks
    print("\n[1/3] Updating active picks...")
    update_result = update_active_picks()
    print(f"  Active: {update_result['active']}")
    print(f"  Newly closed: {update_result['newly_closed']}")
    print(f"  Total closed: {update_result['total_closed']}")

    if update_result["stats"].get("total_picks", 0) > 0:
        s = update_result["stats"]
        print(f"  Forward stats: WR={s['win_rate']}% Sharpe={s['sharpe_ratio']} PF={s['profit_factor']}")

    # 2. Generate new predictions
    print("\n[2/3] Generating new forward predictions...")
    new_predictions = generate_predictions()
    print(f"  Generated: {len(new_predictions)} predictions")

    # 3. Add to active picks (avoid duplicate pair/TF combos)
    # Fix #4: Enforce max concurrent picks per direction
    # Fix #9 (v1.4): Per-symbol dedup — max 1 pick per coin across all timeframes
    # Fix #10 (v1.4): Cross-TF conflict detection — block opposite-direction signals
    active = load_json(ACTIVE_PICKS_FILE)
    existing_keys = {(p["symbol"], p["timeframe"]) for p in active}
    buy_count = sum(1 for p in active if p["direction"] == "BUY")
    sell_count = sum(1 for p in active if p["direction"] == "SELL")

    # v1.4: Track active symbols and their directions
    active_symbols = {}  # symbol → direction
    for p in active:
        sym = p["symbol"]
        if sym not in active_symbols:
            active_symbols[sym] = p["direction"]

    added = 0
    blocked_direction = 0
    blocked_symbol = 0
    blocked_conflict = 0
    for pred in new_predictions:
        key = (pred["symbol"], pred["timeframe"])
        if key in existing_keys:
            continue

        sym = pred["symbol"]

        # v1.4 Fix #9: Per-symbol dedup — max MAX_PER_SYMBOL active picks per coin
        symbol_count = sum(1 for p in active if p["symbol"] == sym)
        if symbol_count >= MAX_PER_SYMBOL:
            blocked_symbol += 1
            print(f"    [SYMBOL DEDUP] {sym} {pred['timeframe']} blocked — already have {symbol_count} active pick(s)")
            continue

        # v1.4 Fix #10: Cross-TF conflict detection
        if REQUIRE_TF_AGREEMENT and sym in active_symbols:
            if active_symbols[sym] != pred["direction"]:
                blocked_conflict += 1
                print(f"    [TF CONFLICT] {sym} {pred['timeframe']} {pred['direction']} conflicts with active {active_symbols[sym]}")
                continue

        # Enforce direction limits
        if pred["direction"] == "BUY" and buy_count >= MAX_PER_DIRECTION:
            blocked_direction += 1
            continue
        if pred["direction"] == "SELL" and sell_count >= MAX_PER_DIRECTION:
            blocked_direction += 1
            continue

        active.append(pred)
        existing_keys.add(key)
        active_symbols[sym] = pred["direction"]
        if pred["direction"] == "BUY":
            buy_count += 1
        else:
            sell_count += 1
        added += 1

    save_json(ACTIVE_PICKS_FILE, active)

    # Log all predictions. PICKS_LOG_FILE is the HOT shard — OPEN/ACTIVE
    # only — per the 2026-05-14 status-shard rotation (see
    # tools/migrate_all_picks_log.py). Terminal picks roll to
    # closed/closed_YYYYMM.json.gz at close time elsewhere in this module.
    # New predictions are always non-terminal at insert time so they go
    # straight into the hot shard.
    all_log = load_json(PICKS_LOG_FILE)
    all_log.extend(new_predictions)

    # Defensive: filter out any terminal-status picks that may have leaked
    # into the hot shard (e.g. from legacy state). Closed picks belong in
    # the monthly cold shards, not in the hot file.
    _TERMINAL = {"WIN","WON","LOSS","LOST","CLOSED","EXPIRED","TP_HIT","SL_HIT"}
    all_log = [
        p for p in all_log
        if not (
            isinstance(p, dict)
            and (
                str(p.get("status") or "").upper() in _TERMINAL
                or str(p.get("outcome") or "").upper() in _TERMINAL
            )
        )
    ]
    save_json(PICKS_LOG_FILE, all_log)

    skipped = len(new_predictions) - added
    print(f"  Added to active: {added} (skipped {skipped}: {blocked_direction} direction, {blocked_symbol} symbol-dedup, {blocked_conflict} TF-conflict)")
    print(f"  Total active now: {len(active)}")

    # 4. Show top picks by confidence
    print("\n[3/3] Top picks by confidence:")
    top = sorted(new_predictions, key=lambda p: -p["probability"])
    for i, p in enumerate(top[:10]):
        direction_emoji = "🟢" if p["direction"] == "BUY" else "🔴"
        print(f"  {direction_emoji} {p['symbol']:12s} {p['timeframe']:4s} "
              f"{p['direction']:4s} {p['confidence']:6s} "
              f"prob={p['probability']:.2f} entry=${p['entry_price']:.4f} "
              f"TP=${p['take_profit']:.4f} SL=${p['stop_loss']:.4f}")

    return {
        "new_predictions": len(new_predictions),
        "active_picks": len(active),
        "closed_picks": update_result["total_closed"],
        "forward_stats": update_result["stats"],
    }


if __name__ == "__main__":
    result = run_prediction_cycle()
    print(f"\n{'='*70}")
    print("CYCLE COMPLETE")
    print(f"{'='*70}")
