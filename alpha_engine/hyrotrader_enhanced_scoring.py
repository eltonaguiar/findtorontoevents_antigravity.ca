"""
Hyrotrader Enhanced Scoring with Technical Indicators + Backtest
=================================================================
- Fetches live Binance data for hyrotrader picks
- Computes RSI, MACD, Bollinger Bands, ATR, Volume indicators
- Enhanced conviction scoring with technical validation
- Simple backtest on historical data

Usage: python alpha_engine/hyrotrader_enhanced_scoring.py
"""

from __future__ import annotations
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# Project paths
_REPO = Path(__file__).resolve().parents[1]
_PICKS_PATH = _REPO / "audit_dashboard" / "data" / "hyrotrader_picks.json"
_OUTPUT_PATH = _REPO / "audit_dashboard" / "data" / "hyrotrader_enhanced_picks.json"
_ML_RANKINGS_PATH = _REPO / "audit_dashboard" / "data" / "hyro_ml_pick_rankings.json"

# Use centralized API failover (Binance → Bybit → KuCoin → CoinGecko → CryptoCompare)
try:
    from alpha_engine.api_failover import fetch_klines as _failover_fetch_klines
    _HAS_FAILOVER = True
except ImportError:
    _HAS_FAILOVER = False

try:
    from alpha_engine.asset_class import normalize_asset_class as _norm_asset_class
except ImportError:
    def _norm_asset_class(pick: dict) -> str:
        return str(
            pick.get("category") or pick.get("asset_class") or "crypto"
        ).lower()

# Technical indicator parameters
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BB_PERIOD = 20
BB_STD = 2
ATR_PERIOD = 14
VOLUME_MA_PERIOD = 20


def fetch_klines(symbol: str, interval: str = "1h", limit: int = 100) -> Optional[list]:
    """Fetch klines with full API failover chain.

    Uses api_failover (Binance → Bybit → KuCoin → CoinGecko → CryptoCompare)
    and converts to the dict format expected by compute_all_indicators().
    """
    if _HAS_FAILOVER:
        raw = _failover_fetch_klines(symbol, interval, limit)
    else:
        # Inline fallback if api_failover unavailable (shouldn't happen)
        import requests
        raw = None
        for base in ["https://api.binance.us", "https://api.binance.com",
                      "https://api1.binance.com", "https://api2.binance.com"]:
            try:
                resp = requests.get(
                    f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}",
                    timeout=5,
                )
                if resp.status_code == 200:
                    raw = resp.json()
                    break
            except Exception:
                continue

    if not raw:
        return None

    # Convert Binance-format lists to dicts for DataFrame consumption
    return [
        {
            "timestamp": k[0] if isinstance(k, list) else k.get("timestamp", 0),
            "open": float(k[1]) if isinstance(k, list) else float(k.get("open", 0)),
            "high": float(k[2]) if isinstance(k, list) else float(k.get("high", 0)),
            "low": float(k[3]) if isinstance(k, list) else float(k.get("low", 0)),
            "close": float(k[4]) if isinstance(k, list) else float(k.get("close", 0)),
            "volume": float(k[5]) if isinstance(k, list) else float(k.get("volume", 0)),
        }
        for k in raw
    ]


def compute_rsi(closes: pd.Series, period: int = RSI_PERIOD) -> float:
    """Compute current RSI value."""
    if len(closes) < period + 1:
        return 50.0
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return round(float(rsi.iloc[-1]), 2)


def compute_macd(closes: pd.Series) -> dict:
    """Compute current MACD values."""
    if len(closes) < MACD_SLOW + MACD_SIGNAL:
        return {"macd": 0, "signal": 0, "histogram": 0, "direction": "neutral"}
    
    ema_fast = closes.ewm(span=MACD_FAST, adjust=False).mean()
    ema_slow = closes.ewm(span=MACD_SLOW, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=MACD_SIGNAL, adjust=False).mean()
    histogram = macd_line - signal_line
    
    macd_val = float(macd_line.iloc[-1])
    signal_val = float(signal_line.iloc[-1])
    hist_val = float(histogram.iloc[-1])
    
    # Determine direction
    if macd_val > signal_val and hist_val > 0:
        direction = "bullish"
    elif macd_val < signal_val and hist_val < 0:
        direction = "bearish"
    else:
        direction = "neutral"
    
    return {
        "macd": round(macd_val, 4),
        "signal": round(signal_val, 4),
        "histogram": round(hist_val, 4),
        "direction": direction
    }


def compute_bollinger(closes: pd.Series) -> dict:
    """Compute Bollinger Bands values."""
    if len(closes) < BB_PERIOD:
        return {"upper": 0, "middle": 0, "lower": 0, "pct_b": 0.5, "squeeze": False}
    
    middle = closes.rolling(BB_PERIOD).mean()
    std = closes.rolling(BB_PERIOD).std()
    upper = middle + BB_STD * std
    lower = middle - BB_STD * std
    pct_b = (closes - lower) / (upper - lower).replace(0, np.nan)
    
    current = closes.iloc[-1]
    upper_val = float(upper.iloc[-1])
    lower_val = float(lower.iloc[-1])
    middle_val = float(middle.iloc[-1])
    pct_b_val = float(pct_b.iloc[-1])
    
    # Squeeze detection (narrow bands)
    bandwidth = (upper_val - lower_val) / middle_val if middle_val != 0 else 0
    avg_bandwidth = ((upper - lower) / middle).iloc[-20:].mean() if len(closes) >= 20 else 0.1
    squeeze = bandwidth < (avg_bandwidth * 0.7) if avg_bandwidth > 0 else False
    
    return {
        "upper": round(upper_val, 2),
        "middle": round(middle_val, 2),
        "lower": round(lower_val, 2),
        "pct_b": round(pct_b_val, 3),
        "squeeze": squeeze
    }


def compute_atr(highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = ATR_PERIOD) -> float:
    """Compute current ATR value."""
    if len(closes) < period + 1:
        return 0.0
    
    tr1 = highs - lows
    tr2 = (highs - closes.shift(1)).abs()
    tr3 = (lows - closes.shift(1)).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    
    # Return as percentage of price
    current_price = closes.iloc[-1]
    atr_pct = (float(atr.iloc[-1]) / current_price) * 100 if current_price > 0 else 0
    return round(atr_pct, 3)


def compute_volume_ratio(volumes: pd.Series, closes: pd.Series, period: int = VOLUME_MA_PERIOD) -> dict:
    """Compute volume analysis."""
    if len(volumes) < period:
        return {"ratio": 1.0, "expansion": False, "direction": "neutral"}
    
    avg_vol = volumes.rolling(period).mean()
    current_vol = volumes.iloc[-1]
    ratio = current_vol / avg_vol.iloc[-1] if avg_vol.iloc[-1] > 0 else 1.0
    
    # Expansion threshold
    expansion = ratio > 1.5
    
    # Volume vs price direction
    price_change = (closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2] if len(closes) >= 2 else 0
    if ratio > 1.2 and price_change > 0:
        direction = "accumulation"
    elif ratio > 1.2 and price_change < 0:
        direction = "distribution"
    else:
        direction = "neutral"
    
    return {
        "ratio": round(ratio, 2),
        "expansion": expansion,
        "direction": direction
    }


def compute_all_indicators(klines: list) -> dict:
    """Compute all technical indicators for a symbol."""
    if not klines or len(klines) < 30:
        return {}
    
    df = pd.DataFrame(klines)
    closes = df["close"]
    highs = df["high"]
    lows = df["low"]
    volumes = df["volume"]
    
    rsi_val = compute_rsi(closes)
    macd_data = compute_macd(closes)
    bb_data = compute_bollinger(closes)
    atr_pct = compute_atr(highs, lows, closes)
    vol_data = compute_volume_ratio(volumes, closes)
    
    # Simple trend detection
    sma_20 = closes.rolling(20).mean().iloc[-1]
    sma_50 = closes.rolling(50).mean().iloc[-1] if len(closes) >= 50 else sma_20
    current_price = closes.iloc[-1]
    
    if current_price > sma_20 > sma_50:
        trend = "strong_uptrend"
    elif current_price > sma_20:
        trend = "uptrend"
    elif current_price < sma_20 < sma_50:
        trend = "strong_downtrend"
    elif current_price < sma_20:
        trend = "downtrend"
    else:
        trend = "sideways"
    
    return {
        "rsi": rsi_val,
        "macd": macd_data,
        "bollinger": bb_data,
        "atr_pct": atr_pct,
        "volume": vol_data,
        "trend": trend,
        "sma_20": round(sma_20, 2),
        "sma_50": round(sma_50, 2) if len(closes) >= 50 else None,
        "current_price": round(current_price, 4)
    }


def calculate_enhanced_score(pick: dict, indicators: dict) -> dict:
    """
    Calculate enhanced conviction score with technical validation.
    Returns (total_score, breakdown, validation_notes)
    """
    base_confidence = pick.get("confidence_pct", 50)
    direction = pick.get("direction", "LONG").upper()
    ac = _norm_asset_class(pick)
    is_forex = ac == "forex"
    is_crypto = ac in ("crypto", "meme")

    score = base_confidence
    breakdown = {"base": base_confidence}
    validation_notes = []
    warnings = []
    
    if not indicators:
        return {
            "enhanced_score": base_confidence,
            "breakdown": breakdown,
            "validation": "no_data",
            "notes": ["Insufficient data for technical analysis"],
            "warnings": ["Technical indicators unavailable"]
        }
    
    # RSI validation — FX has smaller typical swings; crypto chop punishes late longs harder.
    rsi = indicators.get("rsi", 50)
    os_long, ob_long = (28, 72) if is_forex else ((30, 68) if is_crypto else (30, 70))
    # SHORT favors overbought; thresholds mirror asset-class tuning above.
    if is_forex:
        ob_for_short, os_for_short = 72, 28
    elif is_crypto:
        ob_for_short, os_for_short = 70, 32
    else:
        ob_for_short, os_for_short = 70, 30
    if direction == "LONG":
        if rsi < os_long:
            score += 10
            breakdown["rsi_oversold"] = 10
            validation_notes.append("RSI oversold (bullish momentum)")
        elif rsi > ob_long:
            pen = 7 if is_crypto else 5
            score -= pen
            breakdown["rsi_overbought"] = -pen
            warnings.append("RSI overbought - possible pullback")
        else:
            breakdown["rsi_neutral"] = 0
    else:  # SHORT
        if rsi > ob_for_short:
            score += 10
            breakdown["rsi_overbought"] = 10
            validation_notes.append("RSI overbought (bearish momentum)")
        elif rsi < os_for_short:
            pen = 7 if is_crypto else 5
            score -= pen
            breakdown["rsi_oversold"] = -pen
            warnings.append("RSI oversold - possible bounce")
    
    # MACD validation
    macd = indicators.get("macd", {})
    macd_direction = macd.get("direction", "neutral")
    if direction == "LONG" and macd_direction == "bullish":
        score += 8
        breakdown["macd_bullish"] = 8
        validation_notes.append("MACD bullish crossover")
    elif direction == "SHORT" and macd_direction == "bearish":
        score += 8
        breakdown["macd_bearish"] = 8
        validation_notes.append("MACD bearish crossover")
    elif macd_direction == "neutral":
        score -= 2
        breakdown["macd_neutral"] = -2
    
    # Bollinger validation
    bb = indicators.get("bollinger", {})
    pct_b = bb.get("pct_b", 0.5)
    if direction == "LONG":
        if pct_b < 0.2:
            score += 5
            breakdown["bb_oversold"] = 5
            validation_notes.append("Price at lower Bollinger Band")
        elif pct_b > 0.8:
            score -= 3
            breakdown["bb_overbought"] = -3
            warnings.append("Price at upper Bollinger Band")
    else:  # SHORT
        if pct_b > 0.8:
            score += 5
            breakdown["bb_overbought"] = 5
            validation_notes.append("Price at upper Bollinger Band")
        elif pct_b < 0.2:
            score -= 3
            breakdown["bb_oversold"] = -3
            warnings.append("Price at lower Bollinger Band")
    
    # Squeeze bonus (low volatility = potential breakout)
    if bb.get("squeeze", False):
        score += 3
        breakdown["bb_squeeze"] = 3
        validation_notes.append("Bollinger squeeze - volatility compression")
    
    # Volume validation
    vol = indicators.get("volume", {})
    if vol.get("expansion", False):
        direction_match = (direction == "LONG" and vol.get("direction") in ["accumulation", "neutral"]) or \
                         (direction == "SHORT" and vol.get("direction") in ["distribution", "neutral"])
        if direction_match:
            score += 5
            breakdown["volume_expansion"] = 5
            validation_notes.append("Volume expansion confirms direction")
    
    # Trend alignment
    trend = indicators.get("trend", "sideways")
    if direction == "LONG" and "uptrend" in trend:
        score += 5
        breakdown["trend_aligned"] = 5
        validation_notes.append("Trend aligned with direction")
    elif direction == "SHORT" and "downtrend" in trend:
        score += 5
        breakdown["trend_aligned"] = 5
        validation_notes.append("Trend aligned with direction")
    elif "sideways" in trend:
        score -= 2
        breakdown["trend_sideways"] = -2
    
    # ATR-based volatility warning
    atr = indicators.get("atr_pct", 0)
    if atr > 5:
        warnings.append(f"High volatility: {atr}% ATR - consider reduced position size")
    elif atr < 1:
        warnings.append(f"Low volatility: {atr}% ATR - limited move potential")
    
    # Cap score at 100
    final_score = min(max(score, 0), 100)
    
    # Determine validation status
    if final_score >= 80 and len(warnings) == 0:
        validation_status = "high_conviction"
    elif final_score >= 65:
        validation_status = "moderate"
    else:
        validation_status = "low_confidence"
    
    return {
        "enhanced_score": final_score,
        "breakdown": breakdown,
        "validation": validation_status,
        "notes": validation_notes,
        "warnings": warnings
    }


def compute_short_term_entry_profile(pick: dict, indicators: dict, backtest: dict) -> dict:
    """
    Compute a short-term entry profile for actionable buys/sells.
    Produces a 0-100 entry_quality score and a go/no-go flag for immediate entries.
    """
    if not indicators:
        return {
            "entry_quality": 0,
            "actionable": False,
            "horizon": "4-24h",
            "reasons": ["no_indicator_data"],
        }

    direction = str(pick.get("direction", "LONG")).upper()
    score = 50
    reasons = []

    rsi = float(indicators.get("rsi", 50))
    atr = float(indicators.get("atr_pct", 0))
    trend = str(indicators.get("trend", "sideways"))
    macd_dir = str((indicators.get("macd") or {}).get("direction", "neutral"))
    vol = indicators.get("volume") or {}
    vol_ratio = float(vol.get("ratio", 1.0))

    if direction == "LONG":
        if rsi <= 35:
            score += 8
            reasons.append("rsi_pullback_long")
        if "uptrend" in trend:
            score += 8
            reasons.append("trend_aligned")
        if macd_dir == "bullish":
            score += 6
            reasons.append("macd_support")
    else:
        if rsi >= 65:
            score += 8
            reasons.append("rsi_rally_short")
        if "downtrend" in trend:
            score += 8
            reasons.append("trend_aligned")
        if macd_dir == "bearish":
            score += 6
            reasons.append("macd_support")

    if 1.0 <= atr <= 4.5:
        score += 5
        reasons.append("atr_in_tradeable_band")
    elif atr > 6.0:
        score -= 8
        reasons.append("atr_too_high")

    if vol_ratio >= 1.2:
        score += 5
        reasons.append("volume_confirmation")

    bt_wr = float(backtest.get("win_rate", 0) or 0)
    if bt_wr >= 55:
        score += 8
        reasons.append("backtest_wr_support")
    elif bt_wr < 45 and backtest.get("status") == "completed":
        score -= 8
        reasons.append("backtest_wr_weak")

    entry_quality = int(max(0, min(100, round(score))))
    actionable = entry_quality >= 68 and backtest.get("status") == "completed"

    return {
        "entry_quality": entry_quality,
        "actionable": actionable,
        "horizon": "4-24h",
        "reasons": reasons,
    }


def run_backtest(symbol: str, direction: str, entry_price: float, 
                 stop_loss_pct: float = 0.02, take_profit_pct: float = 0.04,
                 klines: list = None) -> dict:
    """
    Improved backtest on historical data.
    Simulates entries at each bar, holds until SL/TP hit or max duration (20 bars).
    """
    if not klines or len(klines) < 50:
        return {"status": "insufficient_data"}
    
    df = pd.DataFrame(klines)
    closes = df["close"].values
    highs = df["high"].values
    lows = df["low"].values
    
    trades = []
    max_bars = 20  # Hold positions for up to 20 bars
    
    # Start from bar 20 to have enough history
    for i in range(20, len(closes) - max_bars):
        entry_sim = closes[i]
        
        if direction.upper() == "LONG":
            sl_price = entry_sim * (1 - stop_loss_pct)
            tp_price = entry_sim * (1 + take_profit_pct)
            
            exited = False
            for j in range(1, max_bars + 1):
                if i + j >= len(closes):
                    break
                # Check SL first (was price ever below SL?)
                if lows[i+j] <= sl_price:
                    trades.append({"exit": "stop_loss", "pnl_pct": -stop_loss_pct * 100, "bars_held": j})
                    exited = True
                    break
                # Check TP (was price ever above TP?)
                elif highs[i+j] >= tp_price:
                    trades.append({"exit": "take_profit", "pnl_pct": take_profit_pct * 100, "bars_held": j})
                    exited = True
                    break
            
            if not exited:
                # No SL/TP hit within max_bars - exit at market
                exit_price = closes[i + max_bars]
                pnl = (exit_price - entry_sim) / entry_sim * 100
                trades.append({"exit": "timeout", "pnl_pct": round(pnl, 2), "bars_held": max_bars})
        else:  # SHORT
            sl_price = entry_sim * (1 + stop_loss_pct)
            tp_price = entry_sim * (1 - take_profit_pct)
            
            exited = False
            for j in range(1, max_bars + 1):
                if i + j >= len(closes):
                    break
                # Check SL (was price ever above SL?)
                if highs[i+j] >= sl_price:
                    trades.append({"exit": "stop_loss", "pnl_pct": -stop_loss_pct * 100, "bars_held": j})
                    exited = True
                    break
                # Check TP (was price ever below TP?)
                elif lows[i+j] <= tp_price:
                    trades.append({"exit": "take_profit", "pnl_pct": take_profit_pct * 100, "bars_held": j})
                    exited = True
                    break
            
            if not exited:
                exit_price = closes[i + max_bars]
                pnl = (entry_sim - exit_price) / entry_sim * 100
                trades.append({"exit": "timeout", "pnl_pct": round(pnl, 2), "bars_held": max_bars})
    
    if not trades:
        return {
            "status": "no_signals",
            "win_rate": 0,
            "avg_pnl": 0,
            "total_trades": 0
        }
    
    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] < 0]
    win_rate = len(wins) / len(trades) * 100 if trades else 0
    avg_pnl = sum(t["pnl_pct"] for t in trades) / len(trades)
    avg_bars = sum(t["bars_held"] for t in trades) / len(trades)
    
    return {
        "status": "completed",
        "win_rate": round(win_rate, 1),
        "avg_pnl": round(avg_pnl, 2),
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "avg_bars_held": round(avg_bars, 1)
    }


def main():
    """Main function to enhance hyrotrader picks."""
    print("=" * 60)
    print("HYROTRADER ENHANCED SCORING + BACKTEST")
    print("=" * 60)
    
    # Load ML rankings if available (from hyro_ml_pick_optimizer)
    ml_rankings = {}  # key: (strategy, symbol) -> {score, grade, method}
    ml_meta = {}
    if _ML_RANKINGS_PATH.exists():
        try:
            with open(_ML_RANKINGS_PATH, encoding="utf-8") as f:
                ml_data = json.load(f)
            for r in ml_data.get("all_rankings", []):
                key = (r.get("strategy", ""), r.get("symbol", ""))
                ml_rankings[key] = r
            ml_meta = ml_data.get("model_info", {})
            print(f"\n[ML] Loaded {len(ml_rankings)} ML rankings "
                  f"(method: {ml_data.get('scoring_method', 'unknown')}, "
                  f"drift: {ml_meta.get('drift_detected', False)})")
        except (json.JSONDecodeError, OSError) as e:
            print(f"\n[ML] Could not load ML rankings: {e}")
    else:
        print("\n[ML] No ML rankings found — run hyro_ml_pick_optimizer.py first")
    
    # Load existing picks
    with open(_PICKS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    
    picks = data.get("picks", [])
    print(f"\nLoaded {len(picks)} hyrotrader picks")
    
    enhanced_picks = []
    
    for pick in picks:
        symbol = pick.get("symbol_hint", pick.get("symbol", "")).replace("(match Hyro symbol)", "").strip()
        
        # Normalize symbol for Binance
        if not symbol.endswith("USDT"):
            symbol = symbol.replace("USDT", "") + "USDT"
        if "hedge" in pick.get("label", "").lower():
            # Already handling hedge separately
            pass
        
        print(f"\n--- Processing: {symbol} ({pick.get('direction', 'LONG')}) ---")
        
        # Fetch 4h klines for indicators, 1h for backtest
        klines_4h = fetch_klines(symbol, "4h", 100)
        klines_1h = fetch_klines(symbol, "1h", 200)
        
        if not klines_4h:
            print(f"  WARNING: Could not fetch data for {symbol}")
            enhanced_pick = {
                **pick,
                "technical_indicators": {"error": "data_fetch_failed"},
                "enhanced_scoring": {"enhanced_score": pick.get("confidence_pct", 50)},
                "backtest": {"status": "no_data"}
            }
            enhanced_picks.append(enhanced_pick)
            continue
        
        # Compute indicators
        indicators = compute_all_indicators(klines_4h)
        
        # Calculate enhanced score
        scoring = calculate_enhanced_score(pick, indicators)
        
        # Run backtest (using 1h data)
        current_price = indicators.get("current_price", 0) if indicators else 0
        direction = pick.get("direction", "LONG")
        
        # Use 2% stop loss, 4% take profit (2:1 R:R)
        backtest_result = run_backtest(symbol, direction, current_price, 
                                        stop_loss_pct=0.02, take_profit_pct=0.04,
                                        klines=klines_1h)
        
        # Create enhanced pick
        entry_profile = compute_short_term_entry_profile(pick, indicators, backtest_result)

        # ML edge integration — apply ML optimizer score if available
        ml_edge = {}
        strategy_id = pick.get("strategy", pick.get("label", "")).lower().replace(" ", "_")
        # Try exact match, then partial match
        ml_match = ml_rankings.get((strategy_id, symbol))
        ml_cross_strategy = False
        cross_strategy_name = None
        if not ml_match:
            # Fuzzy match: find any ranking that matches the symbol
            # ⚠️ This applies a score from a potentially different strategy — log warning
            for (s, sym), r in ml_rankings.items():
                if sym == symbol:
                    ml_match = r
                    if s != strategy_id:
                        ml_cross_strategy = True
                        cross_strategy_name = s
                    break
        if ml_match:
            ml_score = ml_match.get("score", 0)
            ml_grade = ml_match.get("grade", "?")
            ml_method = ml_match.get("method", "unknown")
            if ml_cross_strategy and cross_strategy_name:
                scoring["warnings"].append(
                    f"ML cross-strategy match: using {cross_strategy_name} ranking for {strategy_id}/{symbol}"
                )
                print(f"  WARNING: ML cross-strategy match — applying {cross_strategy_name} ranking to {strategy_id}/{symbol}")
            ml_edge = {
                "ml_score": ml_score,
                "ml_grade": ml_grade,
                "ml_method": ml_method,
                "ml_boost_applied": True,
                "ml_cross_strategy_match": ml_cross_strategy,
            }
            # Blend ML into enhanced score; down-weight ML when cross-strategy fuzzy match.
            orig_score = scoring["enhanced_score"]
            w_base, w_ml = (0.85, 0.15) if ml_cross_strategy else (0.70, 0.30)
            blended = round(orig_score * w_base + ml_score * w_ml)
            scoring["enhanced_score"] = min(100, max(0, blended))
            scoring["breakdown"]["ml_edge_blend"] = blended - orig_score
            scoring["breakdown"]["ml_blend_weights"] = f"{w_base:.0%}/{w_ml:.0%}"
            if ml_grade in ("A+", "A"):
                scoring["notes"].append(f"ML optimizer: {ml_grade} edge ({ml_score})")
            elif ml_grade in ("D", "F"):
                scoring["warnings"].append(f"ML optimizer: {ml_grade} — weak edge ({ml_score})")
        else:
            ml_edge = {"ml_score": None, "ml_grade": None, "ml_boost_applied": False}

        enhanced_pick = {
            **pick,
            "technical_indicators": indicators,
            "enhanced_scoring": scoring,
            "backtest": backtest_result,
            "short_term_entry": entry_profile,
            "ml_edge": ml_edge,
            "processed_at": datetime.now(timezone.utc).isoformat()
        }
        
        enhanced_picks.append(enhanced_pick)
        
        # Print summary
        print(f"  RSI: {indicators.get('rsi', 'N/A')}")
        print(f"  MACD: {indicators.get('macd', {}).get('direction', 'N/A')}")
        print(f"  Trend: {indicators.get('trend', 'N/A')}")
        print(f"  ATR: {indicators.get('atr_pct', 'N/A')}%")
        print(f"  Enhanced Score: {scoring['enhanced_score']} ({scoring['validation']})")
        print(
            f"  Entry Quality: {entry_profile['entry_quality']} "
            f"(actionable={entry_profile['actionable']})"
        )
        print(f"  Backtest: {backtest_result.get('status', 'N/A')} - WR: {backtest_result.get('win_rate', 'N/A')}%")
        
        if scoring.get("notes"):
            print(f"  Notes: {', '.join(scoring['notes'][:2])}")
        if scoring.get("warnings"):
            print(f"  Warnings: {', '.join(scoring['warnings'][:2])}")
        
        # Rate limit
        time.sleep(0.3)
    
    # Convert numpy types to Python native types for JSON serialization
    def convert_numpy(obj):
        if isinstance(obj, dict):
            return {k: convert_numpy(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [convert_numpy(v) for v in obj]
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj
    
    # Re-rank picks by ML-blended enhanced score (highest first)
    enhanced_picks.sort(
        key=lambda p: p.get("enhanced_scoring", {}).get("enhanced_score", 0),
        reverse=True,
    )
    for i, p in enumerate(enhanced_picks, 1):
        p["ml_rank"] = i
    
    ml_reranked = any(p.get("ml_edge", {}).get("ml_boost_applied") for p in enhanced_picks)
    if ml_reranked:
        print("\n  [ML] Picks re-ranked by ML-blended enhanced score")

    # Save enhanced picks
    output_data = {
        **data,
        "picks": convert_numpy(enhanced_picks),
        "enhanced_at": datetime.now(timezone.utc).isoformat(),
        "ml_integrated": ml_reranked,
        "enhancement_summary": {
            "total_picks": len(enhanced_picks),
            "high_conviction": sum(1 for p in enhanced_picks if p.get("enhanced_scoring", {}).get("validation") == "high_conviction"),
            "moderate": sum(1 for p in enhanced_picks if p.get("enhanced_scoring", {}).get("validation") == "moderate"),
            "low_confidence": sum(1 for p in enhanced_picks if p.get("enhanced_scoring", {}).get("validation") == "low_confidence"),
            "actionable_short_term": sum(1 for p in enhanced_picks if (p.get("short_term_entry") or {}).get("actionable")),
            "ml_boosted": sum(1 for p in enhanced_picks if p.get("ml_edge", {}).get("ml_boost_applied")),
        }
    }
    
    with open(_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    
    print("\n" + "=" * 60)
    print("ENHANCEMENT COMPLETE")
    print("=" * 60)
    print(f"Output saved to: {_OUTPUT_PATH}")
    print(f"High conviction: {output_data['enhancement_summary']['high_conviction']}")
    print(f"Moderate: {output_data['enhancement_summary']['moderate']}")
    print(f"Low confidence: {output_data['enhancement_summary']['low_confidence']}")
    print(f"Actionable short-term entries: {output_data['enhancement_summary']['actionable_short_term']}")


if __name__ == "__main__":
    main()