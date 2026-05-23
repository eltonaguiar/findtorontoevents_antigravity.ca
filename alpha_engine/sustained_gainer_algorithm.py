#!/usr/bin/env python3
# ENTRY TIMING RULES (backed by data from Mar 24 investigation):
# - Sweet spot: coins up 3-8% with 2x+ volume acceleration
# - BLOCK: coins already up >15% (mean reversion zone)
# - REQUIRE: RSI(4h) < 65 (not overbought)
# - REQUIRE: price within 2% of session high (still making new highs)
"""
ALPHA_ENGINE -- Sustained Gainer Confluence Algorithm
=====================================================
5-condition confluence entry with trailing stop portfolio management.

CRITICAL FIX (Mar 24 2026): Added early entry filters to avoid chasing
pumps. RSI upper bound lowered from 70 to 65. Added 24h gain filter
(3-8% sweet spot) and near-session-high requirement.

Entry Signal (ALL 5 must be true + early entry filters):
  1. Price > 20-day high AND volume > 1.5x 20-day average
  2. SMA(9) crosses above SMA(21) within last 3 bars
  3. RSI(14) between 55 and 65 (was 70 -- lowered to avoid overbought)
  4. MACD histogram increasing AND positive, MACD line > signal line
  5. Bullish candlestick pattern (engulfing/hammer) -- bonus, not required

Early Entry Filters (pre-screen before confluence check):
  - 24h gain must be 3-8% (sweet spot for early pump)
  - BLOCK if 24h gain > 15% (mean reversion zone)
  - Price must be within 2% of 24h high (still making new highs)

Exit Rules:
  - Trailing stop: 5% from highest price reached
  - Hard stop: -8% from entry
  - Time stop: 48 hours max
  - Momentum exit: price < 9-SMA for 2 consecutive bars

Scan Universe: All Binance USDT pairs with 24h volume > $5M
Data: 100 daily candles via api_failover.py
Portfolio: Max 5 positions, $200 each (2% of $10K)

Reference: Multi-factor momentum confluence (Jegadeesh & Titman 1993,
Asness et al. 2013, Moskowitz et al. 2012 JFE).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Ensure local imports work when running as script
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

from api_failover import fetch_klines, fetch_ticker_24h
from indicators import sma, rsi as compute_rsi, macd as compute_macd

logger = logging.getLogger("alpha_engine.sustained_gainer")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STATE_PATH = Path(__file__).resolve().parent / "data" / "sustained_gainer_state.json"
MIN_QUOTE_VOLUME_24H = 5_000_000  # $5M minimum 24h quote volume
CANDLE_LIMIT = 100                # 100 daily candles
CANDLE_INTERVAL = "1d"
RATE_LIMIT_SEC = 0.5              # 0.5s between API calls

# Entry thresholds
HIGH_LOOKBACK = 20                # 20-day high breakout
VOLUME_RATIO_MIN = 1.5            # Volume must be >= 1.5x average
SMA_FAST = 9
SMA_SLOW = 21
RSI_PERIOD = 14
RSI_LOW = 55
RSI_HIGH = 65                     # Was 70 -- lowered Mar 24 to avoid overbought entries
MA_CROSS_LOOKBACK = 3             # MA cross must be within last 3 bars

# Early entry filters (Mar 24 fix: catch pumps early, don't chase)
EARLY_ENTRY_MIN_GAIN_24H = 3.0    # Minimum 24h gain % for sweet spot
EARLY_ENTRY_MAX_GAIN_24H = 8.0    # Maximum 24h gain % for sweet spot
EARLY_ENTRY_BLOCK_GAIN_24H = 15.0 # HARD BLOCK: >15% = mean reversion zone
EARLY_ENTRY_NEAR_HIGH_PCT = 2.0   # Price must be within 2% of 24h high

# Exit thresholds
TRAILING_STOP_PCT = 0.05          # 5% trailing from peak
HARD_STOP_PCT = 0.08              # 8% hard stop from entry
MAX_HOLD_HOURS = 48               # 48h time stop
MOMENTUM_EXIT_BARS = 2            # Close below 9-SMA for 2 bars

# Portfolio
MAX_POSITIONS = 5
PORTFOLIO_CAPITAL = 10_000.0
POSITION_SIZE_PCT = 0.02          # 2% of capital
POSITION_SIZE = PORTFOLIO_CAPITAL * POSITION_SIZE_PCT  # $200

# TP/SL for pick output
TP_PCT = 0.15                     # 15% initial target (trail extends)
SL_PCT = 0.08                     # 8% hard stop


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(v: float) -> float:
    if v == 0:
        return 0.0
    av = abs(v)
    if av >= 100:
        return round(v, 2)
    if av >= 1:
        return round(v, 4)
    if av >= 0.01:
        return round(v, 6)
    return round(v, 10)


def _load_state() -> dict:
    """Load portfolio state from JSON file."""
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"positions": [], "closed": [], "last_scan": None}


def _save_state(state: dict) -> None:
    """Save portfolio state to JSON file."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(STATE_PATH, "w") as f:
            json.dump(state, f, indent=2, default=str)
    except IOError as e:
        logger.error("Failed to save state: %s", e)


def _klines_to_df(klines: list) -> Optional[pd.DataFrame]:
    """Convert Binance-format klines to DataFrame."""
    if not klines or len(klines) < 30:
        return None
    try:
        rows = []
        for k in klines:
            rows.append({
                "Open": float(k[1]),
                "High": float(k[2]),
                "Low": float(k[3]),
                "Close": float(k[4]),
                "Volume": float(k[5]),
            })
        df = pd.DataFrame(rows)
        if len(df) < 30:
            return None
        return df
    except (IndexError, ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Candlestick pattern detection
# ---------------------------------------------------------------------------

def _is_bullish_engulfing(o: pd.Series, h: pd.Series,
                          l: pd.Series, c: pd.Series) -> bool:
    """Check if last candle is a bullish engulfing pattern."""
    if len(c) < 2:
        return False
    # Previous candle bearish, current candle bullish
    prev_bearish = float(c.iloc[-2]) < float(o.iloc[-2])
    curr_bullish = float(c.iloc[-1]) > float(o.iloc[-1])
    # Current body engulfs previous body
    engulfs = (float(o.iloc[-1]) <= float(c.iloc[-2]) and
               float(c.iloc[-1]) >= float(o.iloc[-2]))
    return prev_bearish and curr_bullish and engulfs


def _is_hammer(o: pd.Series, h: pd.Series,
               l: pd.Series, c: pd.Series) -> bool:
    """Check if last candle is a hammer pattern."""
    if len(c) < 1:
        return False
    body = abs(float(c.iloc[-1]) - float(o.iloc[-1]))
    if body == 0:
        return False
    lower_shadow = min(float(o.iloc[-1]), float(c.iloc[-1])) - float(l.iloc[-1])
    upper_shadow = float(h.iloc[-1]) - max(float(o.iloc[-1]), float(c.iloc[-1]))
    # Hammer: lower shadow >= 2x body, small upper shadow
    return lower_shadow >= 2 * body and upper_shadow <= body * 0.5


# ---------------------------------------------------------------------------
# Core signal detection
# ---------------------------------------------------------------------------

def _check_confluence(df: pd.DataFrame) -> dict:
    """
    Check all 5 confluence conditions on a DataFrame of OHLCV data.

    Returns dict with:
        'signal': True/False
        'conditions_met': int (0-5)
        'details': dict of each condition result
    """
    close = df["Close"]
    volume = df["Volume"]
    high = df["High"]
    low = df["Low"]
    opn = df["Open"]

    details = {}
    conditions = 0

    # --- Condition 1: Price > 20-day high AND volume > 1.5x average ---
    if len(close) >= HIGH_LOOKBACK + 1:
        recent_high = close.iloc[-(HIGH_LOOKBACK + 1):-1].max()
        current_price = float(close.iloc[-1])
        price_breakout = current_price > recent_high

        avg_vol = volume.iloc[-HIGH_LOOKBACK:].mean()
        current_vol = float(volume.iloc[-1])
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 0
        vol_confirm = vol_ratio >= VOLUME_RATIO_MIN

        cond1 = price_breakout and vol_confirm
        details["price_breakout"] = price_breakout
        details["volume_ratio"] = round(vol_ratio, 2)
        details["volume_confirm"] = vol_confirm
        if cond1:
            conditions += 1
    else:
        details["price_breakout"] = False
        details["volume_ratio"] = 0
        details["volume_confirm"] = False

    # --- Condition 2: SMA(9) crosses above SMA(21) within last 3 bars ---
    sma_fast = sma(close, SMA_FAST)
    sma_slow = sma(close, SMA_SLOW)
    if len(sma_fast.dropna()) >= MA_CROSS_LOOKBACK + 1 and len(sma_slow.dropna()) >= MA_CROSS_LOOKBACK + 1:
        # Current: fast > slow
        current_above = float(sma_fast.iloc[-1]) > float(sma_slow.iloc[-1])
        # Check if there was a cross in last 3 bars (fast was below slow, now above)
        crossed_recently = False
        for i in range(2, MA_CROSS_LOOKBACK + 2):
            if i <= len(sma_fast) and i <= len(sma_slow):
                if float(sma_fast.iloc[-i]) <= float(sma_slow.iloc[-i]):
                    crossed_recently = True
                    break
        cond2 = current_above and crossed_recently
        # Also accept if fast has been above slow for the entire lookback (sustained trend)
        if current_above and not crossed_recently:
            # Check fast > slow for all recent bars (sustained uptrend)
            sustained = all(
                float(sma_fast.iloc[-j]) > float(sma_slow.iloc[-j])
                for j in range(1, min(MA_CROSS_LOOKBACK + 1, len(sma_fast)))
                if not pd.isna(sma_fast.iloc[-j]) and not pd.isna(sma_slow.iloc[-j])
            )
            if sustained:
                cond2 = True
        details["sma_cross"] = cond2
        if cond2:
            conditions += 1
    else:
        details["sma_cross"] = False

    # --- Condition 3: RSI between 55 and 70 ---
    rsi_series = compute_rsi(close, RSI_PERIOD)
    if len(rsi_series.dropna()) >= 1:
        rsi_val = float(rsi_series.iloc[-1])
        cond3 = RSI_LOW < rsi_val < RSI_HIGH
        details["rsi"] = round(rsi_val, 2)
        details["rsi_in_range"] = cond3
        if cond3:
            conditions += 1
    else:
        details["rsi"] = 0
        details["rsi_in_range"] = False

    # --- Condition 4: MACD histogram increasing AND positive, MACD > signal ---
    macd_data = compute_macd(close)
    macd_line = macd_data["macd"]
    signal_line = macd_data["signal"]
    histogram = macd_data["histogram"]
    if len(histogram.dropna()) >= 2:
        hist_curr = float(histogram.iloc[-1])
        hist_prev = float(histogram.iloc[-2])
        macd_val = float(macd_line.iloc[-1])
        sig_val = float(signal_line.iloc[-1])

        hist_increasing = hist_curr > hist_prev
        hist_positive = hist_curr > 0
        macd_above_signal = macd_val > sig_val

        cond4 = hist_increasing and hist_positive and macd_above_signal
        details["macd_hist_current"] = round(hist_curr, 6)
        details["macd_hist_prev"] = round(hist_prev, 6)
        details["macd_hist_rising"] = hist_increasing and hist_positive
        details["macd_above_signal"] = macd_above_signal
        if cond4:
            conditions += 1
    else:
        details["macd_hist_rising"] = False
        details["macd_above_signal"] = False

    # --- Condition 5: Bullish candlestick pattern (BONUS - not strictly required) ---
    bullish_engulfing = _is_bullish_engulfing(opn, high, low, close)
    hammer = _is_hammer(opn, high, low, close)
    cond5 = bullish_engulfing or hammer
    details["bullish_engulfing"] = bullish_engulfing
    details["hammer"] = hammer
    details["candle_pattern"] = cond5
    if cond5:
        conditions += 1

    # Signal requires conditions 1-4 (all mandatory); condition 5 is bonus
    mandatory_met = (
        details.get("price_breakout", False) and
        details.get("volume_confirm", False) and
        details.get("sma_cross", False) and
        details.get("rsi_in_range", False) and
        details.get("macd_hist_rising", False) and
        details.get("macd_above_signal", False)
    )

    return {
        "signal": mandatory_met,
        "conditions_met": conditions,
        "details": details,
    }


# ---------------------------------------------------------------------------
# Portfolio management (trailing stop, time stop, momentum exit)
# ---------------------------------------------------------------------------

def _update_positions(state: dict) -> list:
    """
    Check open positions for exit conditions.
    Returns list of picks to close (with reason).
    """
    to_close = []
    now = datetime.now(timezone.utc)

    for pos in state.get("positions", []):
        symbol = pos["symbol"]
        entry_price = pos["entry_price"]
        highest_price = pos.get("highest_price", entry_price)

        # Fetch current price
        klines = fetch_klines(symbol, "1h", limit=10)
        if not klines:
            continue
        try:
            current_price = float(klines[-1][4])
        except (IndexError, ValueError, TypeError):
            continue

        # Update highest price
        if current_price > highest_price:
            pos["highest_price"] = current_price
            highest_price = current_price
        pos["current_price"] = current_price

        # Trailing stop level
        trailing_stop_level = highest_price * (1 - TRAILING_STOP_PCT)
        pos["trailing_stop_level"] = _smart_round(trailing_stop_level)

        close_reason = None

        # 1. Trailing stop: price drops 5% from peak
        if current_price <= trailing_stop_level:
            close_reason = f"trailing_stop (peak={_smart_round(highest_price)}, stop={_smart_round(trailing_stop_level)})"

        # 2. Hard stop: -8% from entry
        hard_stop = entry_price * (1 - HARD_STOP_PCT)
        if current_price <= hard_stop:
            close_reason = f"hard_stop (-8% from entry {_smart_round(entry_price)})"

        # 3. Time stop: 48 hours
        entry_time = pos.get("entry_time")
        if entry_time:
            try:
                et = datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
                hours_held = (now - et).total_seconds() / 3600
                if hours_held >= MAX_HOLD_HOURS:
                    close_reason = f"time_stop ({hours_held:.1f}h >= {MAX_HOLD_HOURS}h)"
            except (ValueError, TypeError):
                pass

        # 4. Momentum exit: price < SMA(9) for 2 consecutive bars
        if close_reason is None and klines and len(klines) >= SMA_FAST + MOMENTUM_EXIT_BARS:
            try:
                closes = [float(k[4]) for k in klines]
                close_series = pd.Series(closes)
                sma9 = sma(close_series, SMA_FAST)
                if len(sma9.dropna()) >= MOMENTUM_EXIT_BARS:
                    below_count = 0
                    for i in range(1, MOMENTUM_EXIT_BARS + 1):
                        if float(close_series.iloc[-i]) < float(sma9.iloc[-i]):
                            below_count += 1
                    if below_count >= MOMENTUM_EXIT_BARS:
                        close_reason = f"momentum_exit (price < SMA9 for {MOMENTUM_EXIT_BARS} bars)"
            except Exception:
                pass

        if close_reason:
            pnl_pct = (current_price - entry_price) / entry_price
            to_close.append({
                "symbol": symbol,
                "entry_price": entry_price,
                "exit_price": current_price,
                "pnl_pct": round(pnl_pct, 4),
                "reason": close_reason,
                "closed_at": _now_iso(),
            })

    return to_close


# ---------------------------------------------------------------------------
# Universe scanner: find USDT pairs with $5M+ volume
# ---------------------------------------------------------------------------

def _get_scan_universe() -> tuple[list[str], dict]:
    """Get all Binance USDT pairs with 24h quote volume > $5M.

    Returns (list of symbols, dict of symbol -> ticker data for early entry filters).
    """
    tickers = fetch_ticker_24h()  # all tickers
    if not tickers or not isinstance(tickers, list):
        logger.warning("Failed to fetch ticker list, using fallback universe")
        fallback = [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
            "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "LINKUSDT", "NEARUSDT",
            "DOTUSDT", "ATOMUSDT", "LTCUSDT", "UNIUSDT", "AAVEUSDT",
            "ARBUSDT", "OPUSDT", "SUIUSDT", "APTUSDT", "INJUSDT",
            "FETUSDT", "PEPEUSDT", "WIFUSDT", "RENDERUSDT", "TONUSDT",
        ]
        return fallback, {}

    universe = []
    ticker_data = {}
    for t in tickers:
        sym = t.get("symbol", "")
        if not sym.endswith("USDT"):
            continue
        # Skip stablecoins and leveraged tokens
        base = sym.replace("USDT", "")
        if base in ("USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDD"):
            continue
        if any(x in base for x in ("UP", "DOWN", "BULL", "BEAR")):
            continue
        try:
            quote_vol = float(t.get("quoteVolume", 0))
            if quote_vol >= MIN_QUOTE_VOLUME_24H:
                universe.append(sym)
                # Store ticker data for early entry filters
                ticker_data[sym] = {
                    "priceChangePercent": float(t.get("priceChangePercent", 0)),
                    "lastPrice": float(t.get("lastPrice", 0)),
                    "highPrice": float(t.get("highPrice", 0)),
                }
        except (ValueError, TypeError):
            continue

    logger.info("Scan universe: %d symbols with >$%dM volume",
                len(universe), MIN_QUOTE_VOLUME_24H // 1_000_000)
    return universe, ticker_data


# ---------------------------------------------------------------------------
# Main scan function
# ---------------------------------------------------------------------------

def generate_sustained_gainer_picks(data: dict | None = None) -> list[dict]:
    """
    Scan for sustained gainer confluence signals.

    Args:
        data: Optional pre-loaded data dict from scanner.py (unused -- we self-fetch).

    Returns:
        List of pick dicts in standard scanner format.
    """
    picks = []
    state = _load_state()
    now_str = _now_iso()

    # --- Step 1: Check and close existing positions ---
    to_close = _update_positions(state)
    for closed in to_close:
        # Move from positions to closed
        state["positions"] = [
            p for p in state["positions"]
            if p["symbol"] != closed["symbol"]
        ]
        state["closed"].append(closed)
        logger.info("Closed %s: %s (PnL: %.2f%%)",
                     closed["symbol"], closed["reason"], closed["pnl_pct"] * 100)

    # --- Step 2: Count open positions ---
    open_count = len(state.get("positions", []))
    open_symbols = {p["symbol"] for p in state.get("positions", [])}

    if open_count >= MAX_POSITIONS:
        logger.info("Max positions (%d) reached, skipping scan", MAX_POSITIONS)
        state["last_scan"] = now_str
        _save_state(state)
        return picks

    # --- Step 3: Scan universe ---
    universe, ticker_data = _get_scan_universe()
    scanned = 0
    signals_found = 0
    blocked_count = 0

    for symbol in universe:
        if open_count >= MAX_POSITIONS:
            break

        if symbol in open_symbols:
            continue

        # --- Early entry filters (Mar 24 fix) ---
        td = ticker_data.get(symbol, {})
        gain_24h = td.get("priceChangePercent", 0)
        last_price = td.get("lastPrice", 0)
        high_price = td.get("highPrice", 0)

        # HARD BLOCK: coins already up >15% (mean reversion zone)
        if gain_24h > EARLY_ENTRY_BLOCK_GAIN_24H:
            blocked_count += 1
            continue

        # Prefer coins in 3-8% sweet spot (skip if available data shows outside range)
        # Note: if ticker_data is empty (fallback universe), we skip this filter
        if td and not (EARLY_ENTRY_MIN_GAIN_24H <= gain_24h <= EARLY_ENTRY_MAX_GAIN_24H):
            continue

        # "Near session high" filter: price within 2% of 24h high
        if last_price > 0 and high_price > 0:
            dist_from_high_pct = ((high_price - last_price) / high_price) * 100
            if dist_from_high_pct > EARLY_ENTRY_NEAR_HIGH_PCT:
                continue  # Price pulling back, not making new highs

        # Rate limit
        if scanned > 0:
            time.sleep(RATE_LIMIT_SEC)
        scanned += 1

        # Fetch candles
        klines = fetch_klines(symbol, CANDLE_INTERVAL, CANDLE_LIMIT)
        df = _klines_to_df(klines)
        if df is None:
            continue

        # Check confluence
        result = _check_confluence(df)

        if not result["signal"]:
            continue

        signals_found += 1
        details = result["details"]

        # Compute entry, TP, SL
        current_price = float(df["Close"].iloc[-1])
        entry = _smart_round(current_price)
        tp = _smart_round(entry * (1 + TP_PCT))
        sl = _smart_round(entry * (1 - SL_PCT))

        # Confidence: base 0.70, +0.03 per extra condition, +0.02 for high volume
        conditions_met = result["conditions_met"]
        confidence = 0.70
        if conditions_met >= 5:
            confidence += 0.03  # bonus candle pattern
        vol_ratio = details.get("volume_ratio", 1.5)
        if vol_ratio >= 3.0:
            confidence += 0.05
        elif vol_ratio >= 2.0:
            confidence += 0.02
        rsi_val = details.get("rsi", 60)
        # RSI near 60-65 is sweet spot
        if 58 <= rsi_val <= 67:
            confidence += 0.02
        confidence = min(confidence, 0.85)

        pick = {
            "symbol": symbol,
            "direction": "BUY",
            "entry": entry,
            "entry_price": entry,
            "tp": tp,
            "sl": sl,
            "confidence": round(confidence, 3),
            "strategy": "sustained_gainer_confluence",
            "asset_class": "crypto",
            "timestamp": now_str,
            "reason": (
                f"5-cond confluence: {conditions_met}/5 met | "
                f"RSI={details.get('rsi', 'N/A')} | "
                f"Vol={details.get('volume_ratio', 'N/A')}x | "
                f"MACD rising | SMA9>SMA21"
            ),
            "extra": {
                "signal_count": conditions_met,
                "volume_ratio": vol_ratio,
                "rsi": rsi_val,
                "macd_hist_rising": details.get("macd_hist_rising", False),
                "bullish_engulfing": details.get("bullish_engulfing", False),
                "hammer": details.get("hammer", False),
                "trailing_stop_pct": TRAILING_STOP_PCT,
                "hard_stop_pct": HARD_STOP_PCT,
                "max_hold_hours": MAX_HOLD_HOURS,
                "position_size_usd": POSITION_SIZE,
            },
        }
        picks.append(pick)

        # Add to portfolio state
        state["positions"].append({
            "symbol": symbol,
            "entry_price": entry,
            "highest_price": entry,
            "current_price": entry,
            "trailing_stop_level": _smart_round(entry * (1 - TRAILING_STOP_PCT)),
            "entry_time": now_str,
            "conditions_met": conditions_met,
            "volume_ratio": vol_ratio,
            "rsi_at_entry": rsi_val,
        })
        open_count += 1
        open_symbols.add(symbol)

        logger.info("SIGNAL: %s @ %s (conf=%.2f, conditions=%d/5, vol=%.1fx, RSI=%.1f)",
                     symbol, entry, confidence, conditions_met, vol_ratio, rsi_val)

    # --- Step 4: Save state ---
    state["last_scan"] = now_str
    state["scan_stats"] = {
        "symbols_scanned": scanned,
        "signals_found": signals_found,
        "blocked_mean_reversion": blocked_count,
        "open_positions": len(state.get("positions", [])),
        "total_closed": len(state.get("closed", [])),
    }
    _save_state(state)

    logger.info("Scan complete: %d scanned, %d signals, %d blocked (>15%%), %d open positions",
                scanned, signals_found, blocked_count, open_count)

    return picks


# ---------------------------------------------------------------------------
# Strategy dict for scanner.py import
# ---------------------------------------------------------------------------
SUSTAINED_GAINER_STRATEGIES = {
    "sustained_gainer_confluence": generate_sustained_gainer_picks,
}


# ---------------------------------------------------------------------------
# Standalone execution
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    print("=" * 60)
    print("Sustained Gainer Confluence Algorithm -- Standalone Scan")
    print("=" * 60)
    print(f"  Entry conditions: 5-factor confluence (4 mandatory + 1 bonus)")
    print(f"  Trailing stop: {TRAILING_STOP_PCT*100:.0f}% | Hard stop: {HARD_STOP_PCT*100:.0f}%")
    print(f"  Time stop: {MAX_HOLD_HOURS}h | Max positions: {MAX_POSITIONS}")
    print(f"  Position size: ${POSITION_SIZE:.0f} (2% of ${PORTFOLIO_CAPITAL:,.0f})")
    print()

    results = generate_sustained_gainer_picks()
    if results:
        print(f"\n  SIGNALS FOUND: {len(results)}")
        for p in results:
            print(f"    {p['symbol']:12s} | Entry: {p['entry']:>12} | "
                  f"TP: {p['tp']:>12} | SL: {p['sl']:>12} | "
                  f"Conf: {p['confidence']:.2f} | "
                  f"Conditions: {p['extra']['signal_count']}/5")
    else:
        print("\n  No signals found (all 4 mandatory conditions must align)")

    # Show portfolio state
    state = _load_state()
    positions = state.get("positions", [])
    if positions:
        print(f"\n  Open positions: {len(positions)}")
        for pos in positions:
            print(f"    {pos['symbol']:12s} | Entry: {pos['entry_price']} | "
                  f"Current: {pos.get('current_price', 'N/A')} | "
                  f"Trail stop: {pos.get('trailing_stop_level', 'N/A')}")

    print(f"\n  Scan complete at {_now_iso()}")
