"""
Hoffman Trading Family v1 — 7 Distinct Variations
====================================================

Created by: Claude Code (claude_code_01)
Date: 2026-03-06

The original IRB Hoffman strategy went 0/5 in paper trading.
Root cause analysis:
  - EMA angle >= 30 degrees filter is too strict for crypto sideways chop
  - IRB + ribbon + angle = triple filter leaves almost no setups
  - 45% wick threshold misses many institutional bars
  - No volume confirmation = many false breakouts
  - Entry at current price after breakout = chasing

This module implements 7 DISTINCT Hoffman-inspired strategies, each
focusing on a different aspect of the Rob Hoffman methodology:

1. HoffmanIRBClassicStrategy    — Pure IRB with breakout confirmation
2. HoffmanIRBRelaxedStrategy    — Lower wick threshold + volume filter
3. HoffmanStripTrendStrategy    — EMA 5/18/20 strip pullback
4. HoffmanRoundNumberStrategy   — Round number S/R + RSI
5. HoffmanIRBMomentumStrategy   — IRB + ADX trending + RSI recovery
6. HoffmanMultiConfirmStrategy  — IRB + EMA strip + volume (triple confirm)
7. HoffmanIRBVolProfileStrategy — IRB at VWAP / high-volume price zones

Each returns List[Signal] from generate_signals(data, symbol).
"""

from dataclasses import dataclass
from typing import List
import math
import numpy as np
import pandas as pd


# ── Signal dataclass (compatible with existing baby_strategies pattern) ──

@dataclass
class Signal:
    symbol: str
    direction: str        # "BUY" or "SELL"
    confidence: float     # 0.0 - 1.0
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


# ══════════════════════════════════════════════════════════════════════════
# Shared indicator helpers
# ══════════════════════════════════════════════════════════════════════════

def _ema(arr: np.ndarray, period: int) -> np.ndarray:
    """Exponential Moving Average."""
    n = len(arr)
    if n < period:
        return np.full(n, np.nan)
    k = 2.0 / (period + 1)
    out = np.empty(n)
    out[:period - 1] = np.nan
    out[period - 1] = np.mean(arr[:period])
    for i in range(period, n):
        out[i] = arr[i] * k + out[i - 1] * (1 - k)
    return out


def _sma(arr: np.ndarray, period: int) -> np.ndarray:
    """Simple Moving Average."""
    n = len(arr)
    out = np.full(n, np.nan)
    for i in range(period - 1, n):
        out[i] = np.mean(arr[i - period + 1:i + 1])
    return out


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
         period: int = 14) -> np.ndarray:
    """Average True Range (Wilder smoothing)."""
    n = len(close)
    tr = np.empty(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i],
                     abs(high[i] - close[i - 1]),
                     abs(low[i] - close[i - 1]))
    out = np.full(n, np.nan)
    if n >= period:
        out[period - 1] = np.mean(tr[:period])
        for i in range(period, n):
            out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def _rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    """Relative Strength Index."""
    n = len(close)
    out = np.full(n, np.nan)
    if n < period + 1:
        return out
    delta = np.diff(close)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = np.mean(gain[:period])
    avg_loss = np.mean(loss[:period])
    if avg_loss == 0:
        out[period] = 100.0
    else:
        out[period] = 100.0 - 100.0 / (1 + avg_gain / avg_loss)
    for i in range(period, n - 1):
        avg_gain = (avg_gain * (period - 1) + gain[i]) / period
        avg_loss = (avg_loss * (period - 1) + loss[i]) / period
        if avg_loss == 0:
            out[i + 1] = 100.0
        else:
            out[i + 1] = 100.0 - 100.0 / (1 + avg_gain / avg_loss)
    return out


def _adx(high: np.ndarray, low: np.ndarray, close: np.ndarray,
         period: int = 14) -> np.ndarray:
    """Average Directional Index."""
    n = len(close)
    out = np.full(n, np.nan)
    if n < period * 2 + 1:
        return out

    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]

    for i in range(1, n):
        up = high[i] - high[i - 1]
        down = low[i - 1] - low[i]
        plus_dm[i] = up if (up > down and up > 0) else 0.0
        minus_dm[i] = down if (down > up and down > 0) else 0.0
        tr[i] = max(high[i] - low[i],
                     abs(high[i] - close[i - 1]),
                     abs(low[i] - close[i - 1]))

    # Wilder smoothing
    atr_s = np.full(n, np.nan)
    pdm_s = np.full(n, np.nan)
    mdm_s = np.full(n, np.nan)
    atr_s[period] = np.sum(tr[1:period + 1])
    pdm_s[period] = np.sum(plus_dm[1:period + 1])
    mdm_s[period] = np.sum(minus_dm[1:period + 1])

    for i in range(period + 1, n):
        atr_s[i] = atr_s[i - 1] - atr_s[i - 1] / period + tr[i]
        pdm_s[i] = pdm_s[i - 1] - pdm_s[i - 1] / period + plus_dm[i]
        mdm_s[i] = mdm_s[i - 1] - mdm_s[i - 1] / period + minus_dm[i]

    # DI+ and DI-
    pdi = np.full(n, np.nan)
    mdi = np.full(n, np.nan)
    dx = np.full(n, np.nan)

    for i in range(period, n):
        if not np.isnan(atr_s[i]) and atr_s[i] > 0:
            pdi[i] = 100.0 * pdm_s[i] / atr_s[i]
            mdi[i] = 100.0 * mdm_s[i] / atr_s[i]
            denom = pdi[i] + mdi[i]
            if denom > 0:
                dx[i] = 100.0 * abs(pdi[i] - mdi[i]) / denom

    # ADX = smoothed DX
    start = period * 2
    if start < n and not np.isnan(dx[start]):
        out[start] = np.nanmean(dx[period:start + 1])
        for i in range(start + 1, n):
            if not np.isnan(dx[i]) and not np.isnan(out[i - 1]):
                out[i] = (out[i - 1] * (period - 1) + dx[i]) / period

    return out


def _vwap_rolling(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                  volume: np.ndarray, period: int = 20) -> np.ndarray:
    """Rolling VWAP (typical price * volume / cumulative volume)."""
    n = len(close)
    typical = (high + low + close) / 3.0
    tp_vol = typical * volume
    out = np.full(n, np.nan)
    for i in range(period - 1, n):
        vol_sum = np.sum(volume[i - period + 1:i + 1])
        if vol_sum > 0:
            out[i] = np.sum(tp_vol[i - period + 1:i + 1]) / vol_sum
    return out


def _volume_sma(volume: np.ndarray, period: int = 20) -> np.ndarray:
    """Simple moving average of volume."""
    return _sma(volume, period)


def _detect_irb(open_a: np.ndarray, high: np.ndarray, low: np.ndarray,
                close: np.ndarray, wick_pct: float = 0.45):
    """
    Detect Hoffman Inventory Retracement Bars.

    An IRB has a wick >= wick_pct of the total candle range, with the
    body concentrated in the opposite end of the candle.

    Returns:
        irb_bull: bool array — bullish IRB (long upper wick, body at bottom)
                  Hoffman calls these "bearish IRBs" but they signal institutional
                  selling absorbed = buy opportunity in uptrend
        irb_bear: bool array — bearish IRB (long lower wick, body at top)
                  Signals institutional buying absorbed = sell in downtrend
        wick_ratios: float array — actual wick ratio for each bar
    """
    n = len(close)
    candle_range = high - low
    body = np.abs(close - open_a)
    top_body = np.maximum(close, open_a)
    bot_body = np.minimum(close, open_a)

    # Upper wick ratio
    upper_wick = high - top_body
    lower_wick = bot_body - low

    wick_ratios = np.zeros(n)
    irb_bull = np.zeros(n, dtype=bool)  # Long upper wick (buy signal)
    irb_bear = np.zeros(n, dtype=bool)  # Long lower wick (sell signal)

    for i in range(n):
        if candle_range[i] < 1e-10:
            continue
        upper_r = upper_wick[i] / candle_range[i]
        lower_r = lower_wick[i] / candle_range[i]
        wick_ratios[i] = max(upper_r, lower_r)

        # Body must be small relative to range
        body_ratio = body[i] / candle_range[i]
        if body_ratio >= wick_pct:
            continue

        # Bullish IRB: long upper wick, close & open in lower portion
        # Hoffman "bearish IRB" = buy signal in uptrend
        y_thresh = high[i] - wick_pct * candle_range[i]
        if close[i] < y_thresh and open_a[i] < y_thresh:
            irb_bull[i] = True

        # Bearish IRB: long lower wick, close & open in upper portion
        # Hoffman "bullish IRB" = sell signal in downtrend
        x_thresh = low[i] + wick_pct * candle_range[i]
        if close[i] > x_thresh and open_a[i] > x_thresh:
            irb_bear[i] = True

    return irb_bull, irb_bear, wick_ratios


def _prepare(df: pd.DataFrame):
    """Extract arrays from DataFrame."""
    o = df["open"].values.astype(float)
    h = df["high"].values.astype(float)
    lo = df["low"].values.astype(float)
    c = df["close"].values.astype(float)
    v = df["volume"].values.astype(float)
    return o, h, lo, c, v


# ══════════════════════════════════════════════════════════════════════════
# Strategy 1: HoffmanIRBClassicStrategy
# ══════════════════════════════════════════════════════════════════════════
# Original IRB: wick > 45% of candle range + breakout confirmation on next bar
# Key fix vs paper trading version: entry at IRB extreme, not at current price

class HoffmanIRBClassicStrategy:
    NAME = "hoffman_irb_classic"
    DESCRIPTION = (
        "Classic Hoffman IRB: wick > 45% of range + EMA 5>20>50 ribbon "
        "+ breakout past IRB extreme within 5 bars (tighter temporal decay)"
    )

    @staticmethod
    def generate_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
        if len(data) < 60:
            return []
        o, h, lo, c, v = _prepare(data)
        n = len(c)

        ema5 = _ema(c, 5)
        ema20 = _ema(c, 20)
        sma50 = _sma(c, 50)
        atr = _atr(h, lo, c, 14)
        irb_bull, irb_bear, wick_ratios = _detect_irb(o, h, lo, c, 0.45)

        signals: List[Signal] = []

        # Scan last 10 bars for IRB setups, check if breakout occurred
        for irb_idx in range(max(50, n - 10), n - 1):
            if np.isnan(sma50[irb_idx]) or np.isnan(atr[irb_idx]):
                continue
            if atr[irb_idx] <= 0:
                continue

            bullish_ribbon = (ema5[irb_idx] > ema20[irb_idx] > sma50[irb_idx])
            bearish_ribbon = (ema5[irb_idx] < ema20[irb_idx] < sma50[irb_idx])

            # LONG: bullish IRB (long upper wick) in uptrend
            if irb_bull[irb_idx] and bullish_ribbon:
                # Check for breakout above IRB high in subsequent bars
                for b in range(irb_idx + 1, min(irb_idx + 6, n)):
                    if h[b] > h[irb_idx]:
                        # Breakout confirmed
                        entry = h[irb_idx]  # Enter at IRB high (breakout level)
                        sl = lo[irb_idx]    # Stop below IRB low
                        risk = entry - sl
                        if risk <= 0 or risk < 0.1 * atr[irb_idx]:
                            break
                        tp = entry + 1.5 * risk
                        conf = min(0.85, 0.55 + wick_ratios[irb_idx] * 0.4)

                        # Check if this is still a valid setup (not already stopped)
                        stopped = False
                        for check_b in range(irb_idx + 1, b):
                            if lo[check_b] < sl:
                                stopped = True
                                break
                        if stopped:
                            break

                        signals.append(Signal(
                            symbol=symbol, direction="BUY",
                            confidence=round(conf, 2),
                            entry_price=round(entry, 8),
                            take_profit=round(tp, 8),
                            stop_loss=round(sl, 8),
                            reason=(f"IRB Classic BUY | wick={wick_ratios[irb_idx]:.0%} "
                                    f"ribbon=5>20>50 breakout_bar={b - irb_idx} "
                                    f"R:R=1:1.5")
                        ))
                        break

            # SHORT: bearish IRB (long lower wick) in downtrend
            if irb_bear[irb_idx] and bearish_ribbon:
                for b in range(irb_idx + 1, min(irb_idx + 6, n)):
                    if lo[b] < lo[irb_idx]:
                        entry = lo[irb_idx]
                        sl = h[irb_idx]
                        risk = sl - entry
                        if risk <= 0 or risk < 0.1 * atr[irb_idx]:
                            break
                        tp = entry - 1.5 * risk
                        conf = min(0.85, 0.55 + wick_ratios[irb_idx] * 0.4)

                        stopped = False
                        for check_b in range(irb_idx + 1, b):
                            if h[check_b] > sl:
                                stopped = True
                                break
                        if stopped:
                            break

                        signals.append(Signal(
                            symbol=symbol, direction="SELL",
                            confidence=round(conf, 2),
                            entry_price=round(entry, 8),
                            take_profit=round(tp, 8),
                            stop_loss=round(sl, 8),
                            reason=(f"IRB Classic SELL | wick={wick_ratios[irb_idx]:.0%} "
                                    f"ribbon=5<20<50 breakout_bar={b - irb_idx} "
                                    f"R:R=1:1.5")
                        ))
                        break

        # Deduplicate: keep highest confidence per direction
        best = {}
        for s in signals:
            key = s.direction
            if key not in best or s.confidence > best[key].confidence:
                best[key] = s
        return list(best.values())


# ══════════════════════════════════════════════════════════════════════════
# Strategy 2: HoffmanIRBRelaxedStrategy
# ══════════════════════════════════════════════════════════════════════════
# Relaxed: wick > 35% + volume above average (lower wick threshold, add volume)

class HoffmanIRBRelaxedStrategy:
    NAME = "hoffman_irb_relaxed"
    DESCRIPTION = (
        "Relaxed IRB: wick > 35% (lower threshold catches more bars) "
        "+ volume > 1.2x 20-bar avg + simple EMA20 trend filter"
    )

    @staticmethod
    def generate_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
        if len(data) < 50:
            return []
        o, h, lo, c, v = _prepare(data)
        n = len(c)

        ema20 = _ema(c, 20)
        atr = _atr(h, lo, c, 14)
        vol_sma = _volume_sma(v, 20)
        irb_bull, irb_bear, wick_ratios = _detect_irb(o, h, lo, c, 0.35)

        signals: List[Signal] = []
        i = n - 1

        if np.isnan(ema20[i]) or np.isnan(atr[i]) or atr[i] <= 0:
            return []
        if np.isnan(vol_sma[i]) or vol_sma[i] <= 0:
            return []

        price = c[i]
        atr_now = atr[i]

        # Check last 3 bars for fresh IRB setups
        for idx in range(max(20, n - 3), n):
            # Volume confirmation: bar volume > 1.2x average
            vol_ratio = v[idx] / vol_sma[idx] if vol_sma[idx] > 0 else 0
            if vol_ratio < 1.2:
                continue

            # Simple trend: price above EMA20 for longs
            uptrend = c[idx] > ema20[idx] and ema20[idx] > ema20[max(0, idx - 5)]
            downtrend = c[idx] < ema20[idx] and ema20[idx] < ema20[max(0, idx - 5)]

            if irb_bull[idx] and uptrend:
                entry = price
                sl = lo[idx] - 0.2 * atr_now
                risk = entry - sl
                if risk <= 0:
                    continue
                tp = entry + 2.0 * risk
                vol_conf = min(vol_ratio / 2.0, 1.0)
                conf = 0.50 + 0.20 * wick_ratios[idx] + 0.15 * vol_conf
                signals.append(Signal(
                    symbol=symbol, direction="BUY",
                    confidence=round(min(conf, 0.90), 2),
                    entry_price=round(entry, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=(f"IRB Relaxed BUY | wick={wick_ratios[idx]:.0%} "
                            f"vol={vol_ratio:.1f}x avg | R:R=1:2.0")
                ))

            if irb_bear[idx] and downtrend:
                entry = price
                sl = h[idx] + 0.2 * atr_now
                risk = sl - entry
                if risk <= 0:
                    continue
                tp = entry - 2.0 * risk
                vol_conf = min(vol_ratio / 2.0, 1.0)
                conf = 0.50 + 0.20 * wick_ratios[idx] + 0.15 * vol_conf
                signals.append(Signal(
                    symbol=symbol, direction="SELL",
                    confidence=round(min(conf, 0.90), 2),
                    entry_price=round(entry, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=(f"IRB Relaxed SELL | wick={wick_ratios[idx]:.0%} "
                            f"vol={vol_ratio:.1f}x avg | R:R=1:2.0")
                ))

        best = {}
        for s in signals:
            if s.direction not in best or s.confidence > best[s.direction].confidence:
                best[s.direction] = s
        return list(best.values())


# ══════════════════════════════════════════════════════════════════════════
# Strategy 3: HoffmanStripTrendStrategy
# ══════════════════════════════════════════════════════════════════════════
# EMA 5/18/20 strip: buy when all 3 EMAs aligned bullish + pullback to EMA20

class HoffmanStripTrendStrategy:
    NAME = "hoffman_strip_trend"
    DESCRIPTION = (
        "Hoffman Strip: EMA 5/18/20 all aligned + price pulls back to "
        "touch EMA 18-20 zone + bounces (candle close back above strip)"
    )

    @staticmethod
    def generate_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
        if len(data) < 30:
            return []
        o, h, lo, c, v = _prepare(data)
        n = len(c)

        ema5 = _ema(c, 5)
        ema18 = _ema(c, 18)
        ema20 = _ema(c, 20)
        atr = _atr(h, lo, c, 14)

        signals: List[Signal] = []
        i = n - 1

        if any(np.isnan(x) for x in [ema5[i], ema18[i], ema20[i], atr[i]]):
            return []
        if atr[i] <= 0:
            return []

        price = c[i]
        atr_now = atr[i]

        # Check if EMAs were aligned in recent bars AND price pulled back to strip
        # Look at last 5 bars for pullback
        for idx in range(max(20, n - 5), n):
            if any(np.isnan(x) for x in [ema5[idx], ema18[idx], ema20[idx]]):
                continue

            # Bullish strip: EMA5 > EMA18 > EMA20
            bull_strip = ema5[idx] > ema18[idx] > ema20[idx]
            bear_strip = ema5[idx] < ema18[idx] < ema20[idx]

            # Strip zone = between EMA18 and EMA20
            strip_top = max(ema18[idx], ema20[idx])
            strip_bot = min(ema18[idx], ema20[idx])

            if bull_strip:
                # Pullback: low touched or dipped into the strip zone
                touched_strip = lo[idx] <= strip_top + 0.3 * atr_now
                # Bounce: close back above the strip
                bounced = c[idx] > strip_top

                # Also check that prior bar was above (confirming pullback, not breakdown)
                if idx > 0:
                    was_above = c[idx - 1] > strip_top or h[idx - 1] > strip_top
                else:
                    was_above = True

                if touched_strip and bounced and was_above:
                    entry = price
                    sl = strip_bot - 0.5 * atr_now
                    risk = entry - sl
                    if risk <= 0:
                        continue
                    tp = entry + 2.0 * risk

                    # Confidence: tighter strip = stronger trend
                    strip_width = strip_top - strip_bot
                    width_norm = strip_width / atr_now if atr_now > 0 else 1.0
                    # Narrow strip (< 0.3 ATR) = strong aligned trend
                    tightness = max(0, 1.0 - width_norm / 0.5)
                    conf = 0.55 + 0.25 * tightness

                    signals.append(Signal(
                        symbol=symbol, direction="BUY",
                        confidence=round(min(conf, 0.85), 2),
                        entry_price=round(entry, 8),
                        take_profit=round(tp, 8),
                        stop_loss=round(sl, 8),
                        reason=(f"Strip Trend BUY | EMA 5>{ema5[idx]:.2f} "
                                f"18>{ema18[idx]:.2f} 20>{ema20[idx]:.2f} "
                                f"pullback+bounce | R:R=1:2.0")
                    ))

            if bear_strip:
                touched_strip = h[idx] >= strip_bot - 0.3 * atr_now
                bounced_down = c[idx] < strip_bot

                if idx > 0:
                    was_below = c[idx - 1] < strip_bot or lo[idx - 1] < strip_bot
                else:
                    was_below = True

                if touched_strip and bounced_down and was_below:
                    entry = price
                    sl = strip_top + 0.5 * atr_now
                    risk = sl - entry
                    if risk <= 0:
                        continue
                    tp = entry - 2.0 * risk

                    strip_width = strip_top - strip_bot
                    width_norm = strip_width / atr_now if atr_now > 0 else 1.0
                    tightness = max(0, 1.0 - width_norm / 0.5)
                    conf = 0.55 + 0.25 * tightness

                    signals.append(Signal(
                        symbol=symbol, direction="SELL",
                        confidence=round(min(conf, 0.85), 2),
                        entry_price=round(entry, 8),
                        take_profit=round(tp, 8),
                        stop_loss=round(sl, 8),
                        reason=(f"Strip Trend SELL | EMA 5<{ema5[idx]:.2f} "
                                f"18<{ema18[idx]:.2f} 20<{ema20[idx]:.2f} "
                                f"rally+rejection | R:R=1:2.0")
                    ))

        best = {}
        for s in signals:
            if s.direction not in best or s.confidence > best[s.direction].confidence:
                best[s.direction] = s
        return list(best.values())


# ══════════════════════════════════════════════════════════════════════════
# Strategy 4: HoffmanRoundNumberStrategy
# ══════════════════════════════════════════════════════════════════════════
# Price within 0.5% of round number support + RSI < 40

class HoffmanRoundNumberStrategy:
    NAME = "hoffman_round_number"
    DESCRIPTION = (
        "Hoffman Price Ladder: buy near round number support "
        "(within 0.5% of round level) + RSI < 40 (oversold) + bounce"
    )

    @staticmethod
    def _find_round_levels(price: float, n_levels: int = 5) -> List[float]:
        """Find nearby round number levels (psychological S/R)."""
        if price <= 0:
            return []
        # Determine the appropriate round number interval
        magnitude = 10 ** int(math.log10(price))
        # For BTC ~90000: interval = 1000
        # For ETH ~3000: interval = 100
        # For SOL ~150: interval = 10
        # For XRP ~0.5: interval = 0.1
        if price > 10000:
            interval = 1000
        elif price > 1000:
            interval = 100
        elif price > 100:
            interval = 10
        elif price > 10:
            interval = 1
        elif price > 1:
            interval = 0.1
        else:
            interval = 0.01

        base = (price // interval) * interval
        levels = []
        for i in range(-n_levels, n_levels + 1):
            levels.append(base + i * interval)
        return [l for l in levels if l > 0]

    @staticmethod
    def generate_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
        if len(data) < 30:
            return []
        o, h, lo, c, v = _prepare(data)
        n = len(c)

        rsi = _rsi(c, 14)
        atr = _atr(h, lo, c, 14)
        ema20 = _ema(c, 20)

        signals: List[Signal] = []
        i = n - 1

        if np.isnan(rsi[i]) or np.isnan(atr[i]) or atr[i] <= 0:
            return []

        price = c[i]
        atr_now = atr[i]
        rsi_now = rsi[i]

        round_levels = HoffmanRoundNumberStrategy._find_round_levels(price)

        # Find nearest round level below price (support)
        support_levels = [l for l in round_levels if l < price]
        resist_levels = [l for l in round_levels if l > price]

        # BUY: price near round support + RSI oversold + bounce
        if support_levels and rsi_now < 40:
            nearest_support = max(support_levels)
            distance_pct = (price - nearest_support) / price

            if distance_pct < 0.005:  # Within 0.5% of round level
                # Confirm bounce: current close > prior low
                if n >= 3 and c[i] > lo[i - 1]:
                    entry = price
                    sl = nearest_support - 0.5 * atr_now
                    risk = entry - sl
                    if risk > 0:
                        tp = entry + 2.5 * risk  # Higher RR for S/R plays

                        # Confidence based on RSI depth + proximity
                        rsi_depth = max(0, (40 - rsi_now) / 30)  # 0 at RSI=40, 1 at RSI=10
                        prox = 1.0 - distance_pct / 0.005  # 1 at level, 0 at 0.5%
                        conf = 0.50 + 0.20 * rsi_depth + 0.15 * prox

                        signals.append(Signal(
                            symbol=symbol, direction="BUY",
                            confidence=round(min(conf, 0.85), 2),
                            entry_price=round(entry, 8),
                            take_profit=round(tp, 8),
                            stop_loss=round(sl, 8),
                            reason=(f"Round# BUY | support={nearest_support} "
                                    f"dist={distance_pct:.3%} RSI={rsi_now:.0f} "
                                    f"| R:R=1:2.5")
                        ))

        # SELL: price near round resistance + RSI overbought + rejection
        if resist_levels and rsi_now > 60:
            nearest_resist = min(resist_levels)
            distance_pct = (nearest_resist - price) / price

            if distance_pct < 0.005:
                # Confirm rejection: current close < prior high
                if n >= 3 and c[i] < h[i - 1]:
                    entry = price
                    sl = nearest_resist + 0.5 * atr_now
                    risk = sl - entry
                    if risk > 0:
                        tp = entry - 2.5 * risk

                        rsi_depth = max(0, (rsi_now - 60) / 30)
                        prox = 1.0 - distance_pct / 0.005
                        conf = 0.50 + 0.20 * rsi_depth + 0.15 * prox

                        signals.append(Signal(
                            symbol=symbol, direction="SELL",
                            confidence=round(min(conf, 0.85), 2),
                            entry_price=round(entry, 8),
                            take_profit=round(tp, 8),
                            stop_loss=round(sl, 8),
                            reason=(f"Round# SELL | resist={nearest_resist} "
                                    f"dist={distance_pct:.3%} RSI={rsi_now:.0f} "
                                    f"| R:R=1:2.5")
                        ))

        return signals


# ══════════════════════════════════════════════════════════════════════════
# Strategy 5: HoffmanIRBMomentumStrategy
# ══════════════════════════════════════════════════════════════════════════
# IRB + ADX > 20 (trending market) + RSI recovery (RSI crosses above 30 from below)

class HoffmanIRBMomentumStrategy:
    NAME = "hoffman_irb_momentum"
    DESCRIPTION = (
        "IRB + ADX > 20 (confirmed trend) + RSI recovery from oversold "
        "(RSI was < 30 within 5 bars, now > 30)"
    )

    @staticmethod
    def generate_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
        if len(data) < 50:
            return []
        o, h, lo, c, v = _prepare(data)
        n = len(c)

        rsi = _rsi(c, 14)
        adx = _adx(h, lo, c, 14)
        atr = _atr(h, lo, c, 14)
        ema20 = _ema(c, 20)
        irb_bull, irb_bear, wick_ratios = _detect_irb(o, h, lo, c, 0.40)

        signals: List[Signal] = []
        i = n - 1

        if any(np.isnan(x) for x in [rsi[i], adx[i], atr[i], ema20[i]]):
            return []
        if atr[i] <= 0:
            return []

        price = c[i]
        atr_now = atr[i]
        adx_now = adx[i]

        # ADX > 20 = trending market (Hoffman requires trend)
        if adx_now < 20:
            return []

        # Check last 5 bars for IRB + RSI recovery combo
        for idx in range(max(30, n - 5), n):
            if np.isnan(rsi[idx]):
                continue

            # RSI recovery: was below 30 in last 5 bars, now above 30
            rsi_was_oversold = any(
                not np.isnan(rsi[j]) and rsi[j] < 30
                for j in range(max(0, idx - 5), idx)
            )
            rsi_recovered = rsi[idx] > 30

            # RSI overbought mirror: was above 70, now below 70
            rsi_was_overbought = any(
                not np.isnan(rsi[j]) and rsi[j] > 70
                for j in range(max(0, idx - 5), idx)
            )
            rsi_fell = rsi[idx] < 70

            uptrend = price > ema20[idx]
            downtrend = price < ema20[idx]

            # BUY: IRB + RSI recovery from oversold + uptrend
            if irb_bull[idx] and rsi_was_oversold and rsi_recovered and uptrend:
                entry = price
                sl = lo[idx] - 0.3 * atr_now
                risk = entry - sl
                if risk <= 0:
                    continue
                tp = entry + 2.0 * risk

                adx_conf = min((adx_now - 20) / 30, 1.0)  # Stronger ADX = more conf
                conf = 0.55 + 0.20 * adx_conf + 0.10 * wick_ratios[idx]

                signals.append(Signal(
                    symbol=symbol, direction="BUY",
                    confidence=round(min(conf, 0.90), 2),
                    entry_price=round(entry, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=(f"IRB Momentum BUY | ADX={adx_now:.0f} "
                            f"RSI recovery>30 wick={wick_ratios[idx]:.0%} "
                            f"| R:R=1:2.0")
                ))

            # SELL: IRB + RSI overbought rejection + downtrend
            if irb_bear[idx] and rsi_was_overbought and rsi_fell and downtrend:
                entry = price
                sl = h[idx] + 0.3 * atr_now
                risk = sl - entry
                if risk <= 0:
                    continue
                tp = entry - 2.0 * risk

                adx_conf = min((adx_now - 20) / 30, 1.0)
                conf = 0.55 + 0.20 * adx_conf + 0.10 * wick_ratios[idx]

                signals.append(Signal(
                    symbol=symbol, direction="SELL",
                    confidence=round(min(conf, 0.90), 2),
                    entry_price=round(entry, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=(f"IRB Momentum SELL | ADX={adx_now:.0f} "
                            f"RSI rejection<70 wick={wick_ratios[idx]:.0%} "
                            f"| R:R=1:2.0")
                ))

        best = {}
        for s in signals:
            if s.direction not in best or s.confidence > best[s.direction].confidence:
                best[s.direction] = s
        return list(best.values())


# ══════════════════════════════════════════════════════════════════════════
# Strategy 6: HoffmanMultiConfirmStrategy
# ══════════════════════════════════════════════════════════════════════════
# IRB + EMA strip aligned + volume above avg (all 3 confirmations required)

class HoffmanMultiConfirmStrategy:
    NAME = "hoffman_multi_confirm"
    DESCRIPTION = (
        "Triple confirmation: IRB (wick > 40%) + EMA 5/18/20 strip aligned "
        "+ volume > 1.5x average. All 3 must fire simultaneously."
    )

    @staticmethod
    def generate_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
        if len(data) < 30:
            return []
        o, h, lo, c, v = _prepare(data)
        n = len(c)

        ema5 = _ema(c, 5)
        ema18 = _ema(c, 18)
        ema20 = _ema(c, 20)
        atr = _atr(h, lo, c, 14)
        vol_sma = _volume_sma(v, 20)
        irb_bull, irb_bear, wick_ratios = _detect_irb(o, h, lo, c, 0.40)

        signals: List[Signal] = []

        # Check last 3 bars
        for idx in range(max(20, n - 3), n):
            if any(np.isnan(x) for x in [ema5[idx], ema18[idx], ema20[idx],
                                           atr[idx], vol_sma[idx]]):
                continue
            if atr[idx] <= 0 or vol_sma[idx] <= 0:
                continue

            # Condition 1: EMA strip aligned
            bull_strip = ema5[idx] > ema18[idx] > ema20[idx]
            bear_strip = ema5[idx] < ema18[idx] < ema20[idx]

            # Condition 2: Volume above 1.5x average
            vol_ratio = v[idx] / vol_sma[idx]
            high_volume = vol_ratio > 1.5

            if not high_volume:
                continue

            price = c[n - 1]
            atr_now = atr[n - 1] if not np.isnan(atr[n - 1]) else atr[idx]

            # BUY: IRB + bull strip + high volume
            if irb_bull[idx] and bull_strip:
                entry = price
                sl = lo[idx] - 0.2 * atr_now
                risk = entry - sl
                if risk <= 0:
                    continue
                tp = entry + 2.5 * risk  # Higher RR for triple-confirm

                # Higher confidence for triple confirmation
                vol_conf = min(vol_ratio / 3.0, 1.0)
                conf = 0.65 + 0.15 * wick_ratios[idx] + 0.10 * vol_conf

                signals.append(Signal(
                    symbol=symbol, direction="BUY",
                    confidence=round(min(conf, 0.92), 2),
                    entry_price=round(entry, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=(f"MultiConfirm BUY | IRB wick={wick_ratios[idx]:.0%} "
                            f"strip=5>18>20 vol={vol_ratio:.1f}x "
                            f"| R:R=1:2.5")
                ))

            # SELL: IRB + bear strip + high volume
            if irb_bear[idx] and bear_strip:
                entry = price
                sl = h[idx] + 0.2 * atr_now
                risk = sl - entry
                if risk <= 0:
                    continue
                tp = entry - 2.5 * risk

                vol_conf = min(vol_ratio / 3.0, 1.0)
                conf = 0.65 + 0.15 * wick_ratios[idx] + 0.10 * vol_conf

                signals.append(Signal(
                    symbol=symbol, direction="SELL",
                    confidence=round(min(conf, 0.92), 2),
                    entry_price=round(entry, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=(f"MultiConfirm SELL | IRB wick={wick_ratios[idx]:.0%} "
                            f"strip=5<18<20 vol={vol_ratio:.1f}x "
                            f"| R:R=1:2.5")
                ))

        best = {}
        for s in signals:
            if s.direction not in best or s.confidence > best[s.direction].confidence:
                best[s.direction] = s
        return list(best.values())


# ══════════════════════════════════════════════════════════════════════════
# Strategy 7: HoffmanIRBVolProfileStrategy
# ══════════════════════════════════════════════════════════════════════════
# IRB at high-volume price zones (close near VWAP or 20-bar avg price)

class HoffmanIRBVolProfileStrategy:
    NAME = "hoffman_irb_vol_profile"
    DESCRIPTION = (
        "IRB at high-volume price zones: IRB bar occurs within 0.5 ATR "
        "of rolling VWAP (institutional activity at value area)"
    )

    @staticmethod
    def generate_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
        if len(data) < 30:
            return []
        o, h, lo, c, v = _prepare(data)
        n = len(c)

        atr = _atr(h, lo, c, 14)
        vwap = _vwap_rolling(h, lo, c, v, 20)
        vol_sma = _volume_sma(v, 20)
        ema20 = _ema(c, 20)
        irb_bull, irb_bear, wick_ratios = _detect_irb(o, h, lo, c, 0.40)

        signals: List[Signal] = []

        # Check last 3 bars
        for idx in range(max(20, n - 3), n):
            if any(np.isnan(x) for x in [atr[idx], vwap[idx], ema20[idx]]):
                continue
            if atr[idx] <= 0:
                continue

            # IRB must occur near VWAP (within 0.5 ATR = value area)
            price_to_vwap = abs(c[idx] - vwap[idx])
            near_vwap = price_to_vwap < 0.5 * atr[idx]

            if not near_vwap:
                continue

            price = c[n - 1]
            atr_now = atr[n - 1] if not np.isnan(atr[n - 1]) else atr[idx]
            vwap_now = vwap[idx]

            # Volume confirmation: at least average volume
            vol_ok = vol_sma[idx] > 0 and v[idx] >= vol_sma[idx]

            # Trend context
            uptrend = c[idx] > ema20[idx]
            downtrend = c[idx] < ema20[idx]

            # BUY: IRB at VWAP + price above VWAP = institutional support
            if irb_bull[idx] and uptrend and vol_ok:
                entry = price
                sl = vwap_now - 1.0 * atr_now
                risk = entry - sl
                if risk <= 0:
                    continue
                tp = entry + 2.0 * risk

                # Closer to VWAP = higher confidence
                prox = 1.0 - (price_to_vwap / (0.5 * atr[idx]))
                conf = 0.55 + 0.20 * prox + 0.10 * wick_ratios[idx]

                signals.append(Signal(
                    symbol=symbol, direction="BUY",
                    confidence=round(min(conf, 0.88), 2),
                    entry_price=round(entry, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=(f"IRB@VWAP BUY | VWAP={vwap_now:.4f} "
                            f"dist={price_to_vwap:.4f} wick={wick_ratios[idx]:.0%} "
                            f"| R:R=1:2.0")
                ))

            # SELL: IRB at VWAP + price below VWAP = institutional resistance
            if irb_bear[idx] and downtrend and vol_ok:
                entry = price
                sl = vwap_now + 1.0 * atr_now
                risk = sl - entry
                if risk <= 0:
                    continue
                tp = entry - 2.0 * risk

                prox = 1.0 - (price_to_vwap / (0.5 * atr[idx]))
                conf = 0.55 + 0.20 * prox + 0.10 * wick_ratios[idx]

                signals.append(Signal(
                    symbol=symbol, direction="SELL",
                    confidence=round(min(conf, 0.88), 2),
                    entry_price=round(entry, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=(f"IRB@VWAP SELL | VWAP={vwap_now:.4f} "
                            f"dist={price_to_vwap:.4f} wick={wick_ratios[idx]:.0%} "
                            f"| R:R=1:2.0")
                ))

        best = {}
        for s in signals:
            if s.direction not in best or s.confidence > best[s.direction].confidence:
                best[s.direction] = s
        return list(best.values())


# ══════════════════════════════════════════════════════════════════════════
# Registry
# ══════════════════════════════════════════════════════════════════════════

ALL_STRATEGIES = [
    HoffmanIRBClassicStrategy,
    HoffmanIRBRelaxedStrategy,
    HoffmanStripTrendStrategy,
    HoffmanRoundNumberStrategy,
    HoffmanIRBMomentumStrategy,
    HoffmanMultiConfirmStrategy,
    HoffmanIRBVolProfileStrategy,
]

STRATEGY_MAP = {s.NAME: s for s in ALL_STRATEGIES}


if __name__ == "__main__":
    print("=" * 70)
    print("Hoffman Trading Family v1 — 7 Strategies")
    print("=" * 70)
    for s in ALL_STRATEGIES:
        print(f"\n  {s.NAME}")
        print(f"    {s.DESCRIPTION}")
    print()
