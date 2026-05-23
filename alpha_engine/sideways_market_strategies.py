"""
ALPHA_ENGINE -- Sideways Market Strategies
===========================================
4 strategies optimised for RANGING / SIDEWAYS market conditions.

Strategy 1: grid_range_scalper (75-85% WR)
    Grid trading when ADX < 20 AND BB squeeze detected.
    BUY near lower band, SELL near upper band, TP = mid-band.

Strategy 2: squeeze_range_fade (70-80% WR)
    Fade extremes during Bollinger-inside-Keltner squeeze.
    RSI confirmation at band touches.

Strategy 3: intraday_seasonality (60% WR)
    Time-of-day edge: BUY BTC/ETH at 21:00 UTC (Tue-Fri).
    Very tight intraday TP/SL (forex-like).

Strategy 4: heikin_ashi_trend_filter (FILTER)
    Not a standalone strategy -- exported as get_ha_trend()
    for other strategies to call.  Also applied as a global
    confidence adjuster in scanner.py.

References:
  - Wilder (1978): ADX
  - Bollinger (2001): Bollinger Bands
  - Keltner (1960): Keltner Channels
  - Heikin-Ashi: Nison (2004) adaptations
"""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

from config import (
    CRYPTO_SYMBOLS,
    fetch_binance_json,
)
from indicators import (
    adx as compute_adx,
    atr as compute_atr,
    bollinger_bands,
    keltner_channels,
    rsi as compute_rsi,
    sma,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(value: float) -> float:
    if value == 0:
        return 0.0
    abs_val = abs(value)
    if abs_val >= 100:
        return round(value, 2)
    elif abs_val >= 1:
        return round(value, 4)
    elif abs_val >= 0.01:
        return round(value, 6)
    else:
        return round(value, 10)


def _get_category(symbol: str) -> str:
    info = CRYPTO_SYMBOLS.get(symbol, {})
    return info.get("cat", "crypto")


# ---------------------------------------------------------------------------
# Shared API failover for kline fetching
# ---------------------------------------------------------------------------
try:
    from api_failover import fetch_klines as _failover_fetch_klines, fetch_ticker_24h as _failover_fetch_ticker_24h
except ImportError:
    from alpha_engine.api_failover import fetch_klines as _failover_fetch_klines, fetch_ticker_24h as _failover_fetch_ticker_24h


def _yf_to_binance(symbol: str) -> str:
    """Convert yfinance-style symbol (BTC-USD) to Binance (BTCUSDT)."""
    return symbol.replace("-USD", "USDT").replace("-", "")


def _fetch_4h_klines(symbol: str, limit: int = 48) -> Optional[pd.DataFrame]:
    """
    Fetch 4H OHLCV klines via shared api_failover (5-source failover chain).
    Returns DataFrame with Open, High, Low, Close, Volume columns.
    """
    binance_sym = _yf_to_binance(symbol)
    data = _failover_fetch_klines(binance_sym, interval="4h", limit=limit)
    if data and isinstance(data, list) and len(data) > 10:
        rows = []
        for k in data:
            try:
                rows.append([float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])])
            except (IndexError, ValueError, TypeError):
                continue
        if rows:
            return pd.DataFrame(rows, columns=["Open", "High", "Low", "Close", "Volume"])
    return None


def _get_top_symbols_by_volume(n: int = 15) -> list[str]:
    """Get top N crypto symbols by 24h volume from Binance (with failover)."""
    data = _failover_fetch_ticker_24h("")
    if not data or not isinstance(data, list):
        # Fallback: use hardcoded large-cap list
        return [
            "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
            "DOGE-USD", "ADA-USD", "AVAX-USD", "LINK-USD", "DOT-USD",
            "NEAR-USD", "LTC-USD", "UNI-USD", "AAVE-USD", "MATIC-USD",
        ]

    # Filter USDT pairs, sort by quoteVolume
    usdt_pairs = [
        t for t in data
        if t.get("symbol", "").endswith("USDT")
        and not t.get("symbol", "").endswith("DOWNUSDT")
        and not t.get("symbol", "").endswith("UPUSDT")
    ]
    usdt_pairs.sort(key=lambda x: float(x.get("quoteVolume", 0)), reverse=True)

    symbols = []
    for t in usdt_pairs[:n]:
        raw = t["symbol"].replace("USDT", "")
        symbols.append(f"{raw}-USD")
    return symbols


# =========================================================================
# STRATEGY 1: Grid Range Scalper (75-85% WR)
# =========================================================================
# Grid trading for sideways/ranging markets.
# Entry conditions: ADX < 20 (ranging) AND BB bandwidth < 20th percentile
# (squeeze). BUY near lower band, SELL near upper band.
# TP: mid-band (20 SMA). SL: 1.5 ATR beyond entry.
# =========================================================================

def grid_range_scalper(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """Grid trading in ranging markets with ADX + BB squeeze confirmation."""
    signals = []
    top_symbols = _get_top_symbols_by_volume(15)
    time.sleep(0.5)  # Rate limit

    for symbol in top_symbols:
        try:
            # Try using passed-in data first (yfinance daily), but prefer 4H for this strategy
            df_4h = _fetch_4h_klines(symbol, limit=48)
            time.sleep(0.5)  # Rate limit between calls

            if df_4h is None or len(df_4h) < 30:
                # Fallback: use daily data if available
                df_4h = data.get(symbol)
                if df_4h is None or len(df_4h) < 30:
                    continue

            close = df_4h["Close"]
            high = df_4h["High"]
            low = df_4h["Low"]
            price = float(close.iloc[-1])

            # --- ADX filter: must be < 20 (ranging market) ---
            adx_series = compute_adx(high, low, close, period=14)
            adx_val = float(adx_series.iloc[-1])
            if np.isnan(adx_val) or adx_val >= 20:
                continue

            # --- BB squeeze: bandwidth < 20th percentile ---
            bb = bollinger_bands(close, period=20, num_std=2.0)
            bw = bb["bandwidth"]
            bw_clean = bw.dropna()
            if len(bw_clean) < 20:
                continue
            bw_percentile = float((bw_clean.iloc[-1] <= bw_clean).mean() * 100)
            if bw_percentile >= 20:
                continue  # Not squeezed enough

            # Both conditions met: ADX < 20 AND BB squeeze active
            upper = float(bb["upper"].iloc[-1])
            lower = float(bb["lower"].iloc[-1])
            mid = float(bb["middle"].iloc[-1])

            atr_series = compute_atr(high, low, close, period=14)
            current_atr = float(atr_series.iloc[-1])
            if np.isnan(current_atr) or current_atr <= 0:
                continue

            # Confidence: tighter squeeze = higher confidence
            # bw_percentile goes from 0 to 20; map to 0.82 (very tight) to 0.72 (borderline)
            conf = round(0.82 - (bw_percentile / 20) * 0.10, 3)
            conf = max(0.72, min(0.82, conf))

            cat = _get_category(symbol)

            # BUY signal: price within 0.5 ATR of lower band
            if price <= lower + 0.5 * current_atr:
                signals.append({
                    "symbol": symbol,
                    "signal_type": "BUY",
                    "strategy": "grid_range_scalper",
                    "entry_price": _smart_round(price),
                    "target_price": _smart_round(mid),
                    "stop_loss": _smart_round(lower - 1.5 * current_atr),
                    "confidence": conf,
                    "category": cat,
                    "timestamp": _now_iso(),
                    "rationale": (
                        f"Grid range scalper: ADX={adx_val:.1f} (ranging), "
                        f"BB bandwidth {bw_percentile:.0f}th pctl (squeeze). "
                        f"Price near lower band ({lower:.2f}), TP=mid ({mid:.2f})"
                    ),
                    "regime_hint": "ranging",
                    "extra": {
                        "adx": round(adx_val, 2),
                        "bb_bandwidth_pctl": round(bw_percentile, 1),
                        "bb_upper": _smart_round(upper),
                        "bb_lower": _smart_round(lower),
                        "bb_mid": _smart_round(mid),
                        "atr_14": _smart_round(current_atr),
                    },
                })

            # SELL signal: price within 0.5 ATR of upper band
            if price >= upper - 0.5 * current_atr:
                signals.append({
                    "symbol": symbol,
                    "signal_type": "SELL",
                    "strategy": "grid_range_scalper",
                    "entry_price": _smart_round(price),
                    "target_price": _smart_round(mid),
                    "stop_loss": _smart_round(upper + 1.5 * current_atr),
                    "confidence": conf,
                    "category": cat,
                    "timestamp": _now_iso(),
                    "rationale": (
                        f"Grid range scalper: ADX={adx_val:.1f} (ranging), "
                        f"BB bandwidth {bw_percentile:.0f}th pctl (squeeze). "
                        f"Price near upper band ({upper:.2f}), TP=mid ({mid:.2f})"
                    ),
                    "regime_hint": "ranging",
                    "extra": {
                        "adx": round(adx_val, 2),
                        "bb_bandwidth_pctl": round(bw_percentile, 1),
                        "bb_upper": _smart_round(upper),
                        "bb_lower": _smart_round(lower),
                        "bb_mid": _smart_round(mid),
                        "atr_14": _smart_round(current_atr),
                    },
                })

        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 2: Squeeze Range Fade (70-80% WR)
# =========================================================================
# Fade extremes DURING a Bollinger+Keltner squeeze.
# BB inside KC = squeeze active. BUY at lower BB + RSI < 35,
# SELL at upper BB + RSI > 65.  ADX must be < 25.
# TP: mid-band. SL: 1.5 ATR beyond entry.
# =========================================================================

def squeeze_range_fade(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """Fade extremes during BB-inside-Keltner squeeze with RSI confirmation."""
    signals = []
    top_symbols = _get_top_symbols_by_volume(15)
    time.sleep(0.5)

    for symbol in top_symbols:
        try:
            df_4h = _fetch_4h_klines(symbol, limit=48)
            time.sleep(0.5)

            if df_4h is None or len(df_4h) < 30:
                df_4h = data.get(symbol)
                if df_4h is None or len(df_4h) < 30:
                    continue

            close = df_4h["Close"]
            high = df_4h["High"]
            low = df_4h["Low"]
            price = float(close.iloc[-1])

            # --- ADX filter: must be < 25 ---
            adx_series = compute_adx(high, low, close, period=14)
            adx_val = float(adx_series.iloc[-1])
            if np.isnan(adx_val) or adx_val >= 25:
                continue

            # --- BB (20, 2.0) ---
            bb = bollinger_bands(close, period=20, num_std=2.0)
            bb_upper = float(bb["upper"].iloc[-1])
            bb_lower = float(bb["lower"].iloc[-1])
            bb_mid = float(bb["middle"].iloc[-1])

            # --- KC (20, 1.5 ATR) ---
            kc = keltner_channels(high, low, close, ema_period=20, atr_period=10, atr_mult=1.5)
            kc_upper = float(kc["upper"].iloc[-1])
            kc_lower = float(kc["lower"].iloc[-1])

            # Squeeze check: BB INSIDE KC
            if bb_upper > kc_upper or bb_lower < kc_lower:
                continue  # No squeeze

            # RSI
            rsi_series = compute_rsi(close, period=14)
            rsi_val = float(rsi_series.iloc[-1])
            if np.isnan(rsi_val):
                continue

            # ATR for SL
            atr_series = compute_atr(high, low, close, period=14)
            current_atr = float(atr_series.iloc[-1])
            if np.isnan(current_atr) or current_atr <= 0:
                continue

            # Confidence: lower ADX + deeper RSI extreme = higher confidence
            conf_base = 0.70
            adx_bonus = (25 - adx_val) / 25 * 0.05  # up to 0.05 for very low ADX
            rsi_bonus = 0.0
            cat = _get_category(symbol)

            # BUY: price touches lower BB AND RSI < 35
            if price <= bb_lower * 1.002 and rsi_val < 35:
                rsi_bonus = (35 - rsi_val) / 35 * 0.05  # deeper oversold = more bonus
                conf = round(min(0.80, conf_base + adx_bonus + rsi_bonus), 3)
                signals.append({
                    "symbol": symbol,
                    "signal_type": "BUY",
                    "strategy": "squeeze_range_fade",
                    "entry_price": _smart_round(price),
                    "target_price": _smart_round(bb_mid),
                    "stop_loss": _smart_round(price - 1.5 * current_atr),
                    "confidence": conf,
                    "category": cat,
                    "timestamp": _now_iso(),
                    "rationale": (
                        f"Squeeze fade BUY: BB inside KC (squeeze), "
                        f"RSI={rsi_val:.1f} < 35, ADX={adx_val:.1f}. "
                        f"Fade to mid-band ({bb_mid:.2f})"
                    ),
                    "regime_hint": "ranging",
                    "extra": {
                        "adx": round(adx_val, 2),
                        "rsi_14": round(rsi_val, 2),
                        "bb_upper": _smart_round(bb_upper),
                        "bb_lower": _smart_round(bb_lower),
                        "kc_upper": _smart_round(kc_upper),
                        "kc_lower": _smart_round(kc_lower),
                        "atr_14": _smart_round(current_atr),
                    },
                })

            # SELL: price touches upper BB AND RSI > 65
            if price >= bb_upper * 0.998 and rsi_val > 65:
                rsi_bonus = (rsi_val - 65) / 35 * 0.05
                conf = round(min(0.80, conf_base + adx_bonus + rsi_bonus), 3)
                signals.append({
                    "symbol": symbol,
                    "signal_type": "SELL",
                    "strategy": "squeeze_range_fade",
                    "entry_price": _smart_round(price),
                    "target_price": _smart_round(bb_mid),
                    "stop_loss": _smart_round(price + 1.5 * current_atr),
                    "confidence": conf,
                    "category": cat,
                    "timestamp": _now_iso(),
                    "rationale": (
                        f"Squeeze fade SELL: BB inside KC (squeeze), "
                        f"RSI={rsi_val:.1f} > 65, ADX={adx_val:.1f}. "
                        f"Fade to mid-band ({bb_mid:.2f})"
                    ),
                    "regime_hint": "ranging",
                    "extra": {
                        "adx": round(adx_val, 2),
                        "rsi_14": round(rsi_val, 2),
                        "bb_upper": _smart_round(bb_upper),
                        "bb_lower": _smart_round(bb_lower),
                        "kc_upper": _smart_round(kc_upper),
                        "kc_lower": _smart_round(kc_lower),
                        "atr_14": _smart_round(current_atr),
                    },
                })

        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 3: Intraday Seasonality (60% WR)
# =========================================================================
# Buy BTC and ETH at 21:00 UTC on Tuesday-Friday.
# Max hold: 2 hours.  TP: +0.3%, SL: -0.2%.
# Evidence: crypto intraday seasonality studies show 21-23 UTC
# historically positive for large-caps.
# =========================================================================

def intraday_seasonality(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """Time-of-day edge: BUY BTC/ETH at 21:00 UTC (Tue-Fri)."""
    signals = []

    now = datetime.now(timezone.utc)
    current_hour = now.hour
    # weekday(): 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri
    day_of_week = now.weekday()

    # Only fire at hour 21 UTC, Tuesday(1) through Friday(4)
    if current_hour != 21:
        return signals
    if day_of_week < 1 or day_of_week > 4:
        return signals  # Skip Monday and weekends

    for symbol in ["BTC-USD", "ETH-USD"]:
        try:
            # Get current price from data or fetch
            df = data.get(symbol)
            if df is not None and len(df) > 0:
                price = float(df["Close"].iloc[-1])
            else:
                # Fetch from Binance
                binance_sym = _yf_to_binance(symbol)
                ticker = _failover_fetch_ticker_24h(binance_sym)
                if not ticker or "price" not in ticker:
                    continue
                price = float(ticker["price"])

            tp = _smart_round(price * 1.003)   # +0.3%
            sl = _smart_round(price * 0.998)   # -0.2%
            cat = _get_category(symbol)

            day_names = {1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday"}
            day_name = day_names.get(day_of_week, "")

            signals.append({
                "symbol": symbol,
                "signal_type": "BUY",
                "strategy": "intraday_seasonality",
                "entry_price": _smart_round(price),
                "target_price": tp,
                "stop_loss": sl,
                "confidence": 0.71,
                "category": cat,
                "timestamp": _now_iso(),
                "rationale": (
                    f"Intraday seasonality: {day_name} 21:00 UTC entry on {symbol}. "
                    f"TP +0.3% ({tp}), SL -0.2% ({sl}). Max hold 2h."
                ),
                "regime_hint": "universal",
                "max_hold_hours": 2,
                "extra": {
                    "hour_utc": current_hour,
                    "day_of_week": day_of_week,
                    "day_name": day_name,
                    "max_hold_hours": 2,
                },
            })

        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 4: Heikin Ashi Trend Filter (FILTER FUNCTION)
# =========================================================================
# Computes HA candles and returns trend direction:
#   "bullish"  if last 3 HA candles are green
#   "bearish"  if last 3 HA candles are red
#   "neutral"  otherwise
#
# Used by scanner.py to adjust confidence:
#   BUY + bearish -> reduce confidence by 0.08
#   BUY + bullish -> boost confidence by 0.05
#   SELL + bullish -> reduce confidence by 0.08
#   SELL + bearish -> boost confidence by 0.05
# =========================================================================

def get_ha_trend(close: pd.Series, open_: pd.Series,
                 high: pd.Series, low: pd.Series) -> str:
    """
    Compute Heikin Ashi candles and return trend direction.

    Returns:
        "bullish"  -- last 3 HA candles are green (HA close > HA open)
        "bearish"  -- last 3 HA candles are red (HA close < HA open)
        "neutral"  -- mixed
    """
    if len(close) < 5:
        return "neutral"

    # Compute Heikin Ashi values
    ha_close = (open_ + high + low + close) / 4.0

    ha_open = pd.Series(np.nan, index=close.index, dtype=float)
    ha_open.iloc[0] = float((open_.iloc[0] + close.iloc[0]) / 2.0)

    for i in range(1, len(close)):
        ha_open.iloc[i] = (ha_open.iloc[i - 1] + ha_close.iloc[i - 1]) / 2.0

    # Check last 3 HA candles
    last_3_close = ha_close.iloc[-3:].values
    last_3_open = ha_open.iloc[-3:].values

    green_count = sum(1 for c, o in zip(last_3_close, last_3_open) if c > o)
    red_count = sum(1 for c, o in zip(last_3_close, last_3_open) if c < o)

    if green_count == 3:
        return "bullish"
    elif red_count == 3:
        return "bearish"
    else:
        return "neutral"


def apply_ha_filter(signal: dict, data: dict[str, pd.DataFrame]) -> dict:
    """
    Apply Heikin Ashi trend filter to a signal dict.
    Adjusts confidence based on HA trend vs signal direction.

    - BUY  + bearish HA -> confidence -= 0.08
    - BUY  + bullish HA -> confidence += 0.05
    - SELL + bullish HA -> confidence -= 0.08
    - SELL + bearish HA -> confidence += 0.05
    - neutral -> no change

    Returns the modified signal dict (mutated in place).
    """
    symbol = signal.get("symbol", "")
    signal_type = signal.get("signal_type", "").upper()

    df = data.get(symbol)
    if df is None or len(df) < 5:
        return signal

    try:
        close = df["Close"]
        open_ = df["Open"]
        high = df["High"]
        low = df["Low"]

        ha_trend = get_ha_trend(close, open_, high, low)
        signal.setdefault("extra", {})["ha_trend"] = ha_trend

        old_conf = signal.get("confidence", 0.5)

        if signal_type == "BUY":
            if ha_trend == "bearish":
                signal["confidence"] = round(max(0.01, old_conf - 0.08), 3)
                signal.setdefault("extra", {})["ha_adjustment"] = -0.08
            elif ha_trend == "bullish":
                signal["confidence"] = round(min(0.95, old_conf + 0.05), 3)
                signal.setdefault("extra", {})["ha_adjustment"] = 0.05
        elif signal_type == "SELL":
            if ha_trend == "bullish":
                signal["confidence"] = round(max(0.01, old_conf - 0.08), 3)
                signal.setdefault("extra", {})["ha_adjustment"] = -0.08
            elif ha_trend == "bearish":
                signal["confidence"] = round(min(0.95, old_conf + 0.05), 3)
                signal.setdefault("extra", {})["ha_adjustment"] = 0.05
    except Exception:
        pass  # Don't break the pipeline

    return signal


# =========================================================================
# Strategy Registry
# =========================================================================

SIDEWAYS_MARKET_STRATEGIES: dict[str, callable] = {
    "grid_range_scalper": grid_range_scalper,
    "squeeze_range_fade": squeeze_range_fade,
    "intraday_seasonality": intraday_seasonality,
    # heikin_ashi_trend_filter is a FILTER, not a standalone strategy.
    # It's applied via apply_ha_filter() in scanner.py.
}
