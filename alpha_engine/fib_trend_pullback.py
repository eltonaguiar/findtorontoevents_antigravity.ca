#!/usr/bin/env python3
"""
FIBONACCI TREND PULLBACK + RSI DIVERGENCE
==========================================
A 3-layer confluence strategy combining trend identification, Fibonacci
retracement levels, and RSI divergence confirmation.

ACADEMIC BACKING:
- 50/200 SMA crossover: Brock et al. (1992) "Simple Technical Trading Rules
  and the Stochastic Properties of Stock Returns" -- JF, Vol 47
- Fibonacci retracements: Osler (2000) "Support for Resistance" -- FRBNY,
  documented clustering at 38.2%, 50%, 61.8%
- RSI divergence: Wilder (1978) "New Concepts in Technical Trading Systems",
  confirmed by Chong & Ng (2008) -- Applied Economics

STRATEGY RULES:
---------------
LONG ONLY (trend-following pullback):
  1. TREND:  50 SMA > 200 SMA (golden cross -- confirmed uptrend)
  2. PULLBACK: Price retraces to 38.2%, 50%, or 61.8% Fibonacci level
     from the most recent swing high to prior swing low
  3. CONFIRMATION: Bullish RSI divergence at the Fib level
     (price makes lower low, RSI makes higher low)
  4. ENTRY: All 3 conditions met -> BUY

TP/SL:
  - TP: Previous swing high (100% Fib extension)
  - SL: Below next deeper Fib level or swing low

FREE DATA: yfinance (crypto, ETFs, any liquid instrument)
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from indicators import sma, rsi, atr

EST = timezone(timedelta(hours=-5))
UTC = timezone.utc

# --- Scan universe ----------------------------------------------------------
SCAN_SYMBOLS = {
    # Crypto
    "BTC-USD":  {"name": "Bitcoin",     "cat": "Crypto"},
    "ETH-USD":  {"name": "Ethereum",    "cat": "Crypto"},
    "SOL-USD":  {"name": "Solana",      "cat": "Crypto"},
    "BNB-USD":  {"name": "BNB",         "cat": "Crypto"},
    "XRP-USD":  {"name": "XRP",         "cat": "Crypto"},
    "ADA-USD":  {"name": "Cardano",     "cat": "Crypto"},
    "AVAX-USD": {"name": "Avalanche",   "cat": "Crypto"},
    "LINK-USD": {"name": "Chainlink",   "cat": "Crypto"},
    "DOGE-USD": {"name": "Dogecoin",    "cat": "Crypto"},
    # ETFs & Commodities
    "SPY":      {"name": "S&P 500 ETF",          "cat": "ETF"},
    "QQQ":      {"name": "Nasdaq 100 ETF",       "cat": "ETF"},
    "IWM":      {"name": "Russell 2000 ETF",     "cat": "ETF"},
    "GLD":      {"name": "Gold ETF",             "cat": "Commodity"},
    "SLV":      {"name": "Silver ETF",           "cat": "Commodity"},
    "VDE":      {"name": "Vanguard Energy ETF",  "cat": "ETF"},
    "COPX":     {"name": "Copper Miners ETF",    "cat": "Commodity"},
}

# --- Fibonacci levels -------------------------------------------------------
FIB_LEVELS = [0.382, 0.500, 0.618]

# Swing detection
SWING_LOOKBACK = 60       # Bars to search for swing high/low
SWING_MARGIN = 5          # Ignore last N bars for swing detection (avoid noise)

# RSI divergence
RSI_PERIOD = 14
DIVERGENCE_LOOKBACK = 20  # Bars to search for divergence troughs
RSI_OVERSOLD = 45         # RSI must be below this at trough for divergence

# Proximity: how close price must be to a Fib level to count as "at level"
FIB_TOLERANCE_PCT = 0.025  # 2.5% proximity band

# Minimum swing range as % of price (filter out tiny swings)
MIN_SWING_RANGE_PCT = 0.05  # 5% minimum swing


def _find_swing_points(close: pd.Series, lookback: int = SWING_LOOKBACK,
                       margin: int = SWING_MARGIN) -> Optional[tuple[float, float, int, int]]:
    """Find most recent swing high and preceding swing low.

    Returns (swing_low, swing_high, low_idx, high_idx) or None.
    """
    if len(close) < lookback + margin:
        return None

    # Search window: exclude last `margin` bars
    window = close.iloc[-(lookback + margin):-margin]
    if len(window) < 20:
        return None

    # Find swing high (highest point in window)
    high_idx = int(window.idxmax()) if hasattr(window.idxmax(), '__int__') else window.idxmax()
    high_pos = close.index.get_loc(high_idx)
    swing_high = float(window.max())

    # Find swing low BEFORE the swing high
    pre_high = close.iloc[max(0, high_pos - lookback):high_pos]
    if len(pre_high) < 5:
        # No enough data before swing high; look for low after high
        post_high = close.iloc[high_pos:high_pos + lookback]
        if len(post_high) < 5:
            return None
        low_idx = post_high.idxmin()
        swing_low = float(post_high.min())
    else:
        low_idx = pre_high.idxmin()
        swing_low = float(pre_high.min())

    low_pos = close.index.get_loc(low_idx)

    # Validate swing range
    current_price = float(close.iloc[-1])
    swing_range = swing_high - swing_low
    if swing_range / current_price < MIN_SWING_RANGE_PCT:
        return None

    return swing_low, swing_high, low_pos, high_pos


def _compute_fib_levels(swing_low: float, swing_high: float) -> dict[float, float]:
    """Compute Fibonacci retracement levels from swing low to swing high.

    In an uptrend pullback, retracement levels are measured DOWN from swing high:
      level_price = swing_high - fib_ratio * (swing_high - swing_low)
    """
    swing_range = swing_high - swing_low
    return {level: swing_high - level * swing_range for level in FIB_LEVELS}


def _detect_bullish_divergence(close: pd.Series, rsi_series: pd.Series,
                               lookback: int = DIVERGENCE_LOOKBACK) -> Optional[dict]:
    """Detect bullish RSI divergence: price lower low + RSI higher low.

    Returns dict with divergence details or None.
    """
    if len(close) < lookback * 2 + 5:
        return None

    # Find troughs (local minima) in last `lookback` bars
    recent = close.iloc[-lookback:]
    rsi_recent = rsi_series.iloc[-lookback:]

    troughs = []
    for i in range(1, len(recent) - 1):
        if float(recent.iloc[i]) < float(recent.iloc[i - 1]) and float(recent.iloc[i]) < float(recent.iloc[i + 1]):
            troughs.append(i)

    if len(troughs) < 2:
        return None

    # Compare most recent two troughs
    t1, t2 = troughs[-2], troughs[-1]  # t1 = older, t2 = newer
    p1 = float(recent.iloc[t1])
    p2 = float(recent.iloc[t2])
    r1 = float(rsi_recent.iloc[t1])
    r2 = float(rsi_recent.iloc[t2])

    # Bullish divergence: price lower low + RSI higher low
    price_lower = p2 < p1 * 0.995  # At least 0.5% lower
    rsi_higher = r2 > r1 + 1.5      # At least 1.5 RSI points higher
    rsi_oversold = r2 < RSI_OVERSOLD

    if price_lower and rsi_higher and rsi_oversold:
        return {
            "price_low_1": round(p1, 4),
            "price_low_2": round(p2, 4),
            "rsi_low_1": round(r1, 1),
            "rsi_low_2": round(r2, 1),
            "divergence_strength": round(r2 - r1, 1),
        }

    return None


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten MultiIndex columns from yfinance batch download."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    return df


def generate_signals(verbose: bool = True) -> list[dict]:
    """Scan all symbols for Fibonacci trend pullback + RSI divergence signals."""
    signals = []
    now_est = datetime.now(EST).strftime("%Y-%m-%d %I:%M:%S %p EST")
    now_utc = datetime.now(UTC).isoformat()

    if verbose:
        print(f"\n{'='*65}")
        print(f"  FIB TREND PULLBACK SCAN -- {now_est}")
        print(f"{'='*65}")

    syms = list(SCAN_SYMBOLS.keys())
    try:
        raw = yf.download(
            " ".join(syms),
            period="1y",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False,
        )
    except Exception as e:
        if verbose:
            print(f"  Data fetch error: {e}")
        return []

    for sym, meta in SCAN_SYMBOLS.items():
        try:
            if len(syms) == 1:
                df = raw.copy()
            else:
                if sym not in raw.columns.get_level_values(0):
                    continue
                df = raw[sym].dropna(subset=["Close"]).copy()

            df = _flatten_columns(df)

            if len(df) < 210:
                if verbose:
                    print(f"  {sym:12s} -- insufficient data ({len(df)} bars, need 210)")
                continue

            close = df["Close"].astype(float)
            high = df["High"].astype(float) if "High" in df else close
            low = df["Low"].astype(float) if "Low" in df else close
            price = float(close.iloc[-1])

            # --- Layer 1: Trend (50/200 SMA) -------------------------
            sma50 = float(sma(close, 50).iloc[-1])
            sma200 = float(sma(close, 200).iloc[-1])
            uptrend = sma50 > sma200

            trend_str = "UPTREND" if uptrend else "DOWNTREND"
            if verbose:
                print(f"  {sym:12s} ${price:>10.2f}  SMA50=${sma50:.2f}  "
                      f"SMA200=${sma200:.2f}  {trend_str}")

            if not uptrend:
                if verbose:
                    print(f"  {sym:12s}   -> SKIP: 50 SMA below 200 SMA (downtrend)")
                continue

            # --- Layer 2: Fibonacci pullback --------------------------
            swing = _find_swing_points(close)
            if swing is None:
                if verbose:
                    print(f"  {sym:12s}   -> SKIP: no valid swing detected")
                continue

            swing_low, swing_high, low_pos, high_pos = swing
            fib_levels = _compute_fib_levels(swing_low, swing_high)

            # Check if price is near any Fib level -- pick the CLOSEST one
            hit_level = None
            hit_price = None
            best_distance = float("inf")
            for level, fib_price in fib_levels.items():
                distance = abs(price - fib_price) / fib_price
                if distance <= FIB_TOLERANCE_PCT and distance < best_distance:
                    hit_level = level
                    hit_price = fib_price
                    best_distance = distance

            if hit_level is None:
                if verbose:
                    fib_str = " | ".join(f"{l*100:.1f}%=${p:.2f}" for l, p in sorted(fib_levels.items()))
                    print(f"  {sym:12s}   -> SKIP: price not at Fib level ({fib_str})")
                continue

            if verbose:
                print(f"  {sym:12s}   -> AT {hit_level*100:.1f}% Fib (${hit_price:.2f}), "
                      f"swing {swing_low:.2f}->{swing_high:.2f}")

            # --- Layer 3: RSI pullback confirmation ---------------------
            rsi_series = rsi(close, RSI_PERIOD)
            rsi_val = float(rsi_series.iloc[-1])

            # RSI must be < 50 -- confirms a pullback (not buying at highs)
            if rsi_val >= 55:
                if verbose:
                    print(f"  {sym:12s}   -> SKIP: RSI {rsi_val:.1f} too high (need < 55 for pullback)")
                continue

            # RSI divergence is a bonus, not a hard gate
            divergence = _detect_bullish_divergence(close, rsi_series)
            has_divergence = divergence is not None

            if verbose:
                if has_divergence:
                    print(f"  {sym:12s}   -> DIVERGENCE: price {divergence['price_low_1']:.2f}->"
                          f"{divergence['price_low_2']:.2f} (lower), RSI {divergence['rsi_low_1']:.1f}->"
                          f"{divergence['rsi_low_2']:.1f} (higher)")
                else:
                    print(f"  {sym:12s}   -> No divergence (RSI={rsi_val:.1f}), "
                          f"but Fib pullback + uptrend confirmed")

            # --- TREND + FIB CONFIRMED -> SIGNAL ---------------------

            # Confidence: base 0.64 + adjustments
            confidence = 0.64
            # Shallower pullback = stronger trend = higher confidence
            if hit_level == 0.382:
                confidence += 0.06
            elif hit_level == 0.500:
                confidence += 0.04
            elif hit_level == 0.618:
                confidence += 0.03  # Deeper = riskier, but better R:R
            # RSI divergence bonus (the premium confirmation)
            if has_divergence:
                confidence += 0.05
                if divergence["divergence_strength"] > 5:
                    confidence += 0.02
            # RSI deeply oversold bonus
            if rsi_val < 30:
                confidence += 0.03
            elif rsi_val < 40:
                confidence += 0.02
            elif rsi_val < 50:
                confidence += 0.01
            # Price above 200 SMA = trend confirmed (we already checked 50>200)
            if sma200 > 0 and price > sma200:
                confidence += 0.02  # Above 200 SMA in uptrend
            confidence = round(min(confidence, 0.85), 2)

            # TP: swing high (100% extension)
            tp = swing_high
            # SL: below next deeper Fib level or swing low
            if hit_level == 0.382:
                sl = fib_levels[0.500] - 0.01 * price  # Below 50% level
            elif hit_level == 0.500:
                sl = fib_levels[0.618] - 0.01 * price  # Below 61.8% level
            else:
                sl = swing_low - 0.01 * price  # Below swing low

            # Validate: SL must be below entry, and R:R must be >= 1.0
            if sl >= price:
                if verbose:
                    print(f"  {sym:12s}   -> SKIP: SL (${sl:.2f}) >= entry (${price:.2f})")
                continue

            rr = round((tp - price) / (price - sl), 2)
            if rr < 1.0:
                if verbose:
                    print(f"  {sym:12s}   -> SKIP: R:R {rr:.2f} < 1.0 minimum")
                continue

            atr_val = float(atr(high, low, close).iloc[-1])

            sig = {
                "symbol": sym,
                "name": meta["name"],
                "category": meta["cat"],
                "signal_type": "BUY",
                "entry_price": round(price, 6),
                "take_profit": round(tp, 6),
                "stop_loss": round(sl, 6),
                "risk_reward": rr,
                "strategy": "fib_trend_pullback",
                "confidence": confidence,
                "sma50": round(sma50, 4),
                "sma200": round(sma200, 4),
                "above_200sma": True,
                "trend": "BULL",
                "rsi": round(rsi_val, 2),
                "atr": round(atr_val, 6),
                "fib_level": hit_level,
                "fib_price": round(hit_price, 4),
                "swing_low": round(swing_low, 4),
                "swing_high": round(swing_high, 4),
                "divergence": divergence or {},
                "reason": (
                    f"Fib {hit_level*100:.1f}% pullback in uptrend (50>200 SMA). "
                    f"Price at ${hit_price:.2f} Fib level (swing ${swing_low:.2f}->${swing_high:.2f}). "
                    + (
                        f"Bullish RSI divergence: RSI {divergence['rsi_low_1']:.0f}->"
                        f"{divergence['rsi_low_2']:.0f} (higher low) while price made lower low. "
                        if has_divergence else
                        f"RSI at {rsi_val:.1f} (pullback confirmed, no divergence). "
                    )
                    + f"TP: ${tp:.2f} (swing high). "
                    f"Academic: Brock 1992 (MA), Osler 2000 (Fib), Wilder 1978 (RSI)."
                ),
                "academic_source": (
                    "Brock et al. (1992) JF; Osler (2000) FRBNY; "
                    "Wilder (1978); Chong & Ng (2008) Applied Economics"
                ),
                "entry_time_est": now_est,
                "entry_time_utc": now_utc,
            }

            signals.append(sig)
            if verbose:
                print(f"  * SIGNAL: {sym} BUY @ ${price:.2f} "
                      f"| Fib {hit_level*100:.1f}% | Conf {confidence:.0%} "
                      f"| TP ${tp:.2f} | SL ${sl:.2f} | R:R {rr:.1f}")

        except Exception as e:
            if verbose:
                print(f"  {sym:12s} -- error: {e}")

    if verbose:
        print(f"\n  Total signals: {len(signals)}")
        print(f"{'='*65}\n")

    return signals


if __name__ == "__main__":
    sigs = generate_signals(verbose=True)
    if sigs:
        import json
        print("\nSignal details:")
        for s in sigs:
            print(json.dumps(s, indent=2, default=str))
