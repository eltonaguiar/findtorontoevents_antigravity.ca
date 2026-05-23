"""
ALPHA_ENGINE -- Sweep Breakout Scaler Strategy
================================================
Reverse-engineered from top Binance Futures copy trader patterns:
  - ETHUSDT Perp only, 50x leverage, 87% WR, 18.45 P/L ratio
  - Liquidity sweep → breakout confirmation → aggressive scaling
  - Sub-minute entry clusters, minutes-to-hours hold time
  - 0.6% price moves → 25-80% PnL (via leverage)

Strategy logic (adapted for paper trading without leverage):
  1. Detect consolidation range (48-bar lookback on 15m candles = 12 hours)
  2. Detect liquidity sweep: wick beyond range, close back inside
  3. Confirm breakout: next candle closes strongly beyond range with volume > 1.5x avg
  4. Generate BUY/SELL with TP +3%, SL -1.5% (2:1 R:R, conservative for no-leverage)

Confidence scoring based on:
  - Volume spike magnitude (higher = stronger institutional participation)
  - Sweep depth (deeper sweep = more stops triggered = stronger reversal fuel)
  - Candle body strength (ratio of body to full range)
  - Range width (tighter ranges = more explosive breakouts)

Applied to 12 most liquid futures symbols.

References:
  - ICT Smart Money Concepts -- liquidity sweep & break of structure
  - TradingView: "Liquidity Sweeps: Complete Guide to Smart Money Manipulation"
  - Binance Futures Leaderboard analysis (top scalper patterns, 2025-2026)
  - Altrady: "What Is a Liquidity Sweep in Trading and How to Trade It"
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from datetime import datetime, timezone

from config import CRYPTO_SYMBOLS
from indicators import rsi, atr, sma, volume_ratio


# -- Configuration -----------------------------------------------------

# Symbols to scan (most liquid perpetual futures)
SWEEP_SYMBOLS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "DOGE-USD",
    "AVAX-USD", "LINK-USD", "ADA-USD", "DOT-USD", "NEAR-USD", "SUI-USD",
]

# Range detection parameters
RANGE_LOOKBACK = 48       # bars for range detection (48 x 15m = 12 hours)
MIN_RANGE_BARS = 20       # minimum bars to form a valid range

# Sweep detection
SWEEP_DEPTH_MIN = 0.001   # minimum 0.1% beyond range for a valid sweep
SWEEP_DEPTH_MAX = 0.03    # max 3% beyond range (larger = likely real breakout)

# Breakout confirmation
VOLUME_SPIKE_MIN = 1.5    # volume must be 1.5x 20-bar average
BODY_STRENGTH_MIN = 0.55  # candle body must be > 55% of full candle range

# Risk/reward (no-leverage paper trading)
TP_PCT = 0.03             # +3% take profit
SL_PCT = 0.015            # -1.5% stop loss (2:1 R:R)


# -- Helpers -----------------------------------------------------------

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
        return round(value, 8)


def _get_category(symbol: str) -> str:
    info = CRYPTO_SYMBOLS.get(symbol, {})
    return info.get("cat", "crypto")


def _detect_range(high: pd.Series, low: pd.Series,
                  lookback: int = RANGE_LOOKBACK) -> tuple[float, float] | None:
    """Find N-bar high/low consolidation range.

    Returns (range_high, range_low) or None if insufficient data.
    """
    if len(high) < lookback + 2:
        return None

    # Use bars from -lookback-2 to -2 (exclude last 2 bars for sweep+confirm)
    window_high = high.iloc[-(lookback + 2):-2]
    window_low = low.iloc[-(lookback + 2):-2]

    range_high = float(window_high.max())
    range_low = float(window_low.min())

    if range_high <= range_low or range_low <= 0:
        return None

    return range_high, range_low


def _detect_sweep_and_breakout(
    open_: pd.Series, high: pd.Series, low: pd.Series,
    close: pd.Series, volume: pd.Series,
    range_high: float, range_low: float,
) -> dict | None:
    """Check if the last 2 bars show a liquidity sweep followed by breakout.

    Bar -2 (sweep bar): wick beyond range, close back inside
    Bar -1 (confirmation bar): close strongly beyond range with volume spike

    Returns signal dict with direction and metrics, or None.
    """
    # Sweep bar (second-to-last)
    sweep_open = float(open_.iloc[-2])
    sweep_high = float(high.iloc[-2])
    sweep_low = float(low.iloc[-2])
    sweep_close = float(close.iloc[-2])

    # Confirmation bar (last)
    conf_open = float(open_.iloc[-1])
    conf_high = float(high.iloc[-1])
    conf_low = float(low.iloc[-1])
    conf_close = float(close.iloc[-1])
    conf_volume = float(volume.iloc[-1])

    range_width = range_high - range_low
    if range_width <= 0:
        return None

    range_width_pct = range_width / ((range_high + range_low) / 2)

    # Volume spike check
    vol_avg = float(volume.iloc[-22:-2].mean()) if len(volume) >= 22 else float(volume.iloc[:-2].mean())
    if vol_avg <= 0:
        return None
    vol_spike = conf_volume / vol_avg

    if vol_spike < VOLUME_SPIKE_MIN:
        return None

    # -- BULLISH PATTERN: sweep below range_low, then breakout above range_high --
    # Sweep: wick below range_low but close inside range
    sweep_below = sweep_low < range_low
    sweep_recovered = sweep_close >= range_low and sweep_close <= range_high

    if sweep_below and sweep_recovered:
        sweep_depth = (range_low - sweep_low) / range_low
        if sweep_depth < SWEEP_DEPTH_MIN or sweep_depth > SWEEP_DEPTH_MAX:
            return None

        # Confirmation: close above range_high (breakout)
        if conf_close <= range_high:
            return None

        # Body strength: bullish candle with strong body
        conf_range = conf_high - conf_low
        if conf_range <= 0:
            return None
        conf_body = conf_close - conf_open
        if conf_body <= 0:
            return None  # Must be bullish candle
        body_strength = conf_body / conf_range
        if body_strength < BODY_STRENGTH_MIN:
            return None

        return {
            "direction": "BUY",
            "sweep_depth": round(sweep_depth * 100, 3),
            "volume_spike": round(vol_spike, 2),
            "range_width_pct": round(range_width_pct * 100, 3),
            "candle_strength": round(body_strength, 3),
            "entry_price": conf_close,
            "range_high": range_high,
            "range_low": range_low,
            "sweep_low": sweep_low,
        }

    # -- BEARISH PATTERN: sweep above range_high, then breakout below range_low --
    sweep_above = sweep_high > range_high
    sweep_recovered_bear = sweep_close <= range_high and sweep_close >= range_low

    if sweep_above and sweep_recovered_bear:
        sweep_depth = (sweep_high - range_high) / range_high
        if sweep_depth < SWEEP_DEPTH_MIN or sweep_depth > SWEEP_DEPTH_MAX:
            return None

        # Confirmation: close below range_low (breakout down)
        if conf_close >= range_low:
            return None

        # Body strength: bearish candle with strong body
        conf_range = conf_high - conf_low
        if conf_range <= 0:
            return None
        conf_body = conf_open - conf_close
        if conf_body <= 0:
            return None  # Must be bearish candle
        body_strength = conf_body / conf_range
        if body_strength < BODY_STRENGTH_MIN:
            return None

        return {
            "direction": "SELL",
            "sweep_depth": round(sweep_depth * 100, 3),
            "volume_spike": round(vol_spike, 2),
            "range_width_pct": round(range_width_pct * 100, 3),
            "candle_strength": round(body_strength, 3),
            "entry_price": conf_close,
            "range_high": range_high,
            "range_low": range_low,
            "sweep_high": sweep_high,
        }

    return None


# -- Main Scanner ------------------------------------------------------

def sweep_breakout_scan(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Scan for sweep-breakout-scaler signals across liquid crypto pairs.

    Logic:
      1. Detect 48-bar consolidation range (12h on 15m candles)
      2. Detect liquidity sweep: wick beyond range, close back inside
      3. Confirm breakout: next candle closes strongly beyond range + volume spike
      4. Generate signal with ATR-aware TP/SL or fixed 3%/1.5%

    Args:
        data: dict of symbol -> DataFrame with OHLCV columns

    Returns:
        List of signal dicts
    """
    signals: list[dict] = []

    for symbol in SWEEP_SYMBOLS:
        if symbol not in CRYPTO_SYMBOLS:
            continue
        df = data.get(symbol)
        if df is None or len(df) < RANGE_LOOKBACK + 5:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            open_ = df["Open"]
            volume = df["Volume"]

            # Step 1: Detect consolidation range
            range_result = _detect_range(high, low, RANGE_LOOKBACK)
            if range_result is None:
                continue
            range_high, range_low = range_result

            # Step 2 & 3: Detect sweep + confirm breakout
            pattern = _detect_sweep_and_breakout(
                open_, high, low, close, volume,
                range_high, range_low,
            )
            if pattern is None:
                continue

            entry = pattern["entry_price"]
            direction = pattern["direction"]

            # Step 4: Calculate TP/SL
            # Try ATR-based first, fall back to fixed percentages
            try:
                atr_val = float(atr(high, low, close, 14).iloc[-1])
                if atr_val > 0 and direction == "BUY":
                    tp = entry + max(atr_val * 3.0, entry * TP_PCT)
                    sl = entry - max(atr_val * 1.5, entry * SL_PCT)
                elif atr_val > 0 and direction == "SELL":
                    tp = entry - max(atr_val * 3.0, entry * TP_PCT)
                    sl = entry + max(atr_val * 1.5, entry * SL_PCT)
                else:
                    raise ValueError("fallback")
            except Exception:
                if direction == "BUY":
                    tp = entry * (1 + TP_PCT)
                    sl = entry * (1 - SL_PCT)
                else:
                    tp = entry * (1 - TP_PCT)
                    sl = entry * (1 + SL_PCT)

            # Risk:reward ratio
            if direction == "BUY":
                risk = entry - sl
                reward = tp - entry
            else:
                risk = sl - entry
                reward = entry - tp

            rr = reward / risk if risk > 0 else 0
            if rr < 1.5:
                continue

            # RSI filter: avoid overbought buys / oversold sells
            rsi_val = float(rsi(close, 14).iloc[-1])
            if direction == "BUY" and rsi_val > 75:
                continue
            if direction == "SELL" and rsi_val < 25:
                continue

            # Confidence scoring
            # Base 0.55, boost for: deeper sweep, higher volume, stronger candle, tighter range
            confidence = 0.55
            confidence += min(pattern["sweep_depth"] * 5, 0.10)       # up to +0.10
            confidence += min((pattern["volume_spike"] - 1.5) * 0.05, 0.10)  # up to +0.10
            confidence += min((pattern["candle_strength"] - 0.55) * 0.5, 0.10)  # up to +0.10
            # Tighter ranges produce more explosive breakouts
            if pattern["range_width_pct"] < 3.0:
                confidence += 0.05
            confidence = round(min(confidence, 0.85), 2)

            signal = {
                "strategy": "sweep_breakout_scaler",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": direction,
                "entry_price": _smart_round(entry),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Liquidity sweep {'below' if direction == 'BUY' else 'above'} "
                    f"{'${:.2f}'.format(range_low) if direction == 'BUY' else '${:.2f}'.format(range_high)} "
                    f"range → breakout confirmed. "
                    f"Sweep depth {pattern['sweep_depth']:.2f}%, "
                    f"vol spike {pattern['volume_spike']:.1f}x, "
                    f"body strength {pattern['candle_strength']:.0%}. "
                    f"Modeled after top Binance Futures scalper (87% WR, 18.45 P/L). "
                    f"Paper: TP +3%, SL -1.5% (2:1 R:R)."
                ),
                "timeframe": "15m",
                "rsi_at_entry": round(rsi_val, 1),
                "volume_ratio": pattern["volume_spike"],
                "extra": {
                    "sweep_depth": pattern["sweep_depth"],
                    "volume_spike": pattern["volume_spike"],
                    "range_width": pattern["range_width_pct"],
                    "candle_strength": pattern["candle_strength"],
                    "range_high": _smart_round(range_high),
                    "range_low": _smart_round(range_low),
                    "source": (
                        "Reverse-engineered from top Binance Futures copy trader: "
                        "ETHUSDT Perp, 50x leverage, 87% WR, 18.45 P/L ratio. "
                        "ICT Smart Money Concepts -- liquidity sweep + breakout."
                    ),
                },
                "timestamp": _now_iso(),
            }

            signals.append(signal)

        except Exception:
            continue

    return signals
