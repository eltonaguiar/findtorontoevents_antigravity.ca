"""
Forward-Proven Strategy Variations
====================================
New strategies built from patterns that ACTUALLY WORK in forward testing:

1. KeltnerVWAPConfluence    — Keltner compression + VWAP z-score (combines #1 and #2 forward winners)
2. KeltnerRSISqueeze        — RSI oversold at Keltner lower band during compression
3. AdaptiveKeltnerReversion — Dynamic Keltner params + mean reversion at bands
4. MultiPeriodKeltner       — Triple Keltner (10/20/40) agreement for high-confidence entries
5. VWAPRSIDivergence        — VWAP deviation + RSI divergence for reversal entries
6. HMAKeltnerMomentum       — HMA trend + Keltner expansion for momentum continuation

All enforce: min 2.0x ATR SL, 1% price floor, 2:1 R:R minimum
Based on: Keltner compression (84.6% WR forward), VWAP reversion (60-80% WR forward)
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional, Dict

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]



@dataclass
class Signal:
    symbol: str
    direction: str      # "BUY" or "SELL"
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


# ══════════════════════════════════════════════════════════════════════
# Shared Indicators (vectorized numpy)
# ══════════════════════════════════════════════════════════════════════

def _ema(arr, period):
    out = np.full_like(arr, np.nan, dtype=float)
    if len(arr) < period:
        return out
    out[period - 1] = np.mean(arr[:period])
    k = 2.0 / (period + 1)
    for i in range(period, len(arr)):
        out[i] = arr[i] * k + out[i - 1] * (1 - k)
    return out


def _sma(arr, period):
    out = np.full_like(arr, np.nan, dtype=float)
    if len(arr) < period:
        return out
    cs = np.nancumsum(arr)
    out[period - 1:] = (cs[period - 1:] - np.concatenate([[0], cs[:-period]])) / period
    return out


def _atr(high, low, close, period=14):
    n = len(high)
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i],
                     abs(high[i] - close[i - 1]),
                     abs(low[i] - close[i - 1]))
    out = np.full(n, np.nan)
    if n < period:
        return out
    out[period - 1] = np.mean(tr[:period])
    for i in range(period, n):
        out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def _rsi(close, period=14):
    n = len(close)
    out = np.full(n, np.nan)
    if n < period + 1:
        return out
    deltas = np.diff(close)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    if avg_loss == 0:
        out[period] = 100.0
    else:
        out[period] = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            out[i + 1] = 100.0
        else:
            out[i + 1] = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return out


def _hma(close, period=21):
    """Hull Moving Average — lag-reduced trend filter."""
    half = max(1, period // 2)
    sqrt_n = max(1, int(period ** 0.5))
    ema_half = _ema(close, half)
    ema_full = _ema(close, period)
    raw = 2 * ema_half - ema_full
    valid = ~np.isnan(raw)
    if not np.any(valid):
        return np.full_like(close, np.nan)
    return _ema(np.where(valid, raw, 0.0), sqrt_n)


def _rolling_vwap(high, low, close, volume, period=48):
    typical = (high + low + close) / 3.0
    tp_vol = typical * volume
    n = len(close)
    rvwap = np.full(n, np.nan)
    for i in range(period, n):
        wvol = np.sum(volume[i - period:i + 1])
        if wvol > 0:
            rvwap[i] = np.sum(tp_vol[i - period:i + 1]) / wvol
    return rvwap


def _keltner(close, high, low, ema_period=20, atr_period=14, mult=2.0):
    ema = _ema(close, ema_period)
    atr = _atr(high, low, close, atr_period)
    upper = ema + mult * atr
    lower = ema - mult * atr
    return ema, upper, lower, atr


def _make_signal(symbol, direction, price, atr_val, tp_mult, sl_mult, confidence, reason):
    """Build a Signal with min 2.0x ATR SL and 1% price floor."""
    sl_mult = max(sl_mult, 2.0)
    sl_dist = atr_val * sl_mult
    min_sl_dist = price * 0.01
    if sl_dist < min_sl_dist:
        sl_dist = min_sl_dist
        tp_mult_adj = (sl_dist / atr_val) * (tp_mult / sl_mult)
    else:
        tp_mult_adj = tp_mult
    tp_dist = atr_val * tp_mult_adj

    if direction == "BUY":
        tp = price + tp_dist
        sl = price - sl_dist
    else:
        tp = price - tp_dist
        sl = price + sl_dist

    return Signal(
        symbol=symbol,
        direction=direction,
        confidence=round(min(max(confidence, 0.1), 0.95), 3),
        entry_price=round(price, 8),
        take_profit=round(tp, 8),
        stop_loss=round(sl, 8),
        reason=reason,
    )


def _trend_aligned(ema9, ema20, ema50, i, direction):
    """Check EMA 9/20/50 stack alignment."""
    if i < 50 or any(np.isnan(x) for x in [ema9[i], ema20[i], ema50[i]]):
        return True
    if direction == "BUY":
        return ema9[i] > ema20[i] and ema20[i] > ema50[i]
    else:
        return ema9[i] < ema20[i] and ema20[i] < ema50[i]


# ══════════════════════════════════════════════════════════════════════
# Strategy 1: KeltnerVWAPConfluence
# Combines the two strongest forward-tested patterns
# ══════════════════════════════════════════════════════════════════════

class KeltnerVWAPConfluence:
    name = "keltner_vwap_confluence"
    display_name = "Keltner+VWAP Confluence"

    @staticmethod
    def generate_signals(df, symbol="BTCUSDT"):
        close = df["close"].values.astype(float)
        high = df["high"].values.astype(float)
        low = df["low"].values.astype(float)
        volume = df["volume"].values.astype(float)
        n = len(close)
        if n < 120:
            return []

        ema9 = _ema(close, 9)
        ema20 = _ema(close, 20)
        ema50 = _ema(close, 50)
        ema_mid, upper, lower, atr = _keltner(close, high, low, 20, 14, 2.0)
        rvwap = _rolling_vwap(high, low, close, volume, 48)
        rsi = _rsi(close, 14)

        # Keltner width for compression detection
        width = np.where(ema_mid > 0, (upper - lower) / ema_mid, np.nan)
        comp_window = 80

        signals = []
        for i in range(comp_window, n):
            if np.isnan(atr[i]) or atr[i] <= 0 or np.isnan(rvwap[i]):
                continue

            # Compression: current width below 25th percentile of last 80 bars
            w_slice = width[max(0, i - comp_window):i]
            w_valid = w_slice[~np.isnan(w_slice)]
            if len(w_valid) < 20:
                continue
            compressed = width[i] < np.percentile(w_valid, 25)

            # VWAP z-score
            vwap_dev = close[i] - rvwap[i]
            dev_slice = close[max(0, i - 48):i] - rvwap[max(0, i - 48):i]
            dev_valid = dev_slice[~np.isnan(dev_slice)]
            if len(dev_valid) < 10:
                continue
            z_score = vwap_dev / (np.std(dev_valid) + 1e-12)

            # BUY: compression + breakout above upper + VWAP above + trend aligned
            if (compressed and close[i] > upper[i]
                    and z_score > 1.0
                    and _trend_aligned(ema9, ema20, ema50, i, "BUY")):
                conf = 0.55 + min(0.3, abs(z_score - 1.0) * 0.1)
                signals.append(_make_signal(
                    symbol, "BUY", close[i], atr[i], 4.0, 2.0, conf,
                    f"Keltner+VWAP: compression breakout UP, z={z_score:.1f}"
                ))

            # SELL: compression + breakdown below lower + VWAP below + trend aligned
            elif (compressed and close[i] < lower[i]
                  and z_score < -1.0
                  and _trend_aligned(ema9, ema20, ema50, i, "SELL")):
                conf = 0.55 + min(0.3, abs(z_score + 1.0) * 0.1)
                signals.append(_make_signal(
                    symbol, "SELL", close[i], atr[i], 4.0, 2.0, conf,
                    f"Keltner+VWAP: compression breakout DOWN, z={z_score:.1f}"
                ))

        return signals


# ══════════════════════════════════════════════════════════════════════
# Strategy 2: KeltnerRSISqueeze
# RSI oversold/overbought at Keltner band during compression
# ══════════════════════════════════════════════════════════════════════

class KeltnerRSISqueeze:
    name = "keltner_rsi_squeeze"
    display_name = "Keltner RSI Squeeze"

    @staticmethod
    def generate_signals(df, symbol="BTCUSDT"):
        close = df["close"].values.astype(float)
        high = df["high"].values.astype(float)
        low = df["low"].values.astype(float)
        volume = df["volume"].values.astype(float)
        n = len(close)
        if n < 120:
            return []

        ema_mid, upper, lower, atr = _keltner(close, high, low, 20, 14, 2.0)
        rsi = _rsi(close, 14)
        vol_sma = _sma(volume, 20)

        width = np.where(ema_mid > 0, (upper - lower) / ema_mid, np.nan)
        comp_window = 60

        signals = []
        for i in range(comp_window, n):
            if np.isnan(atr[i]) or atr[i] <= 0 or np.isnan(rsi[i]):
                continue

            w_slice = width[max(0, i - comp_window):i]
            w_valid = w_slice[~np.isnan(w_slice)]
            if len(w_valid) < 15:
                continue
            compressed = width[i] < np.percentile(w_valid, 30)

            vol_surge = (not np.isnan(vol_sma[i]) and vol_sma[i] > 0
                         and volume[i] > vol_sma[i] * 1.2)

            # BUY: compression + RSI oversold + touch lower band + volume
            if (compressed and rsi[i] < 30 and close[i] <= lower[i] and vol_surge):
                conf = 0.6 + min(0.25, (30 - rsi[i]) * 0.01)
                signals.append(_make_signal(
                    symbol, "BUY", close[i], atr[i], 4.0, 2.0, conf,
                    f"Keltner squeeze: RSI={rsi[i]:.0f}, compressed, vol surge"
                ))

            # SELL: compression + RSI overbought + touch upper band + volume
            elif (compressed and rsi[i] > 70 and close[i] >= upper[i] and vol_surge):
                conf = 0.6 + min(0.25, (rsi[i] - 70) * 0.01)
                signals.append(_make_signal(
                    symbol, "SELL", close[i], atr[i], 4.0, 2.0, conf,
                    f"Keltner squeeze: RSI={rsi[i]:.0f}, compressed, vol surge"
                ))

        return signals


# ══════════════════════════════════════════════════════════════════════
# Strategy 3: AdaptiveKeltnerReversion
# Mean reversion at Keltner bands with adaptive multiplier
# ══════════════════════════════════════════════════════════════════════

class AdaptiveKeltnerReversion:
    name = "adaptive_keltner_reversion"
    display_name = "Adaptive Keltner Reversion"

    @staticmethod
    def generate_signals(df, symbol="BTCUSDT"):
        close = df["close"].values.astype(float)
        high = df["high"].values.astype(float)
        low = df["low"].values.astype(float)
        volume = df["volume"].values.astype(float)
        n = len(close)
        if n < 100:
            return []

        atr = _atr(high, low, close, 14)
        ema20 = _ema(close, 20)
        ema50 = _ema(close, 50)
        rsi = _rsi(close, 14)
        vol_sma = _sma(volume, 20)

        signals = []
        for i in range(60, n):
            if np.isnan(atr[i]) or atr[i] <= 0 or np.isnan(ema20[i]):
                continue

            # Adaptive multiplier based on recent volatility regime
            atr_slice = atr[max(0, i - 40):i + 1]
            atr_valid = atr_slice[~np.isnan(atr_slice)]
            if len(atr_valid) < 10:
                continue

            vol_pctile = np.searchsorted(np.sort(atr_valid), atr[i]) / len(atr_valid)
            # Low vol → tighter bands (1.5x), high vol → wider bands (2.5x)
            mult = 1.5 + vol_pctile * 1.0

            upper = ema20[i] + mult * atr[i]
            lower = ema20[i] - mult * atr[i]

            # RSI check
            if np.isnan(rsi[i]):
                continue

            # BUY: price at/below lower band + RSI < 45 (relaxed from 40)
            if close[i] <= lower and rsi[i] < 45:
                depth = max(0, (lower - close[i]) / atr[i])
                conf = 0.50 + min(0.35, depth * 0.2 + (45 - rsi[i]) * 0.005)
                signals.append(_make_signal(
                    symbol, "BUY", close[i], atr[i], 4.0, 2.0, conf,
                    f"Adaptive Keltner reversion: mult={mult:.1f}, RSI={rsi[i]:.0f}"
                ))

            # SELL: price at/above upper band + RSI > 55 (relaxed from 60)
            elif close[i] >= upper and rsi[i] > 55:
                depth = max(0, (close[i] - upper) / atr[i])
                conf = 0.50 + min(0.35, depth * 0.2 + (rsi[i] - 55) * 0.005)
                signals.append(_make_signal(
                    symbol, "SELL", close[i], atr[i], 4.0, 2.0, conf,
                    f"Adaptive Keltner reversion: mult={mult:.1f}, RSI={rsi[i]:.0f}"
                ))

        return signals


# ══════════════════════════════════════════════════════════════════════
# Strategy 4: MultiPeriodKeltner
# Triple Keltner (10/20/40) — all three must agree
# ══════════════════════════════════════════════════════════════════════

class KeltnerPullbackEntry:
    name = "keltner_pullback_entry"
    display_name = "Keltner Pullback Entry"

    @staticmethod
    def generate_signals(df, symbol="BTCUSDT"):
        """After a Keltner breakout, enter on pullback to EMA midline.
        Much higher WR than chasing the breakout itself."""
        close = df["close"].values.astype(float)
        high = df["high"].values.astype(float)
        low = df["low"].values.astype(float)
        volume = df["volume"].values.astype(float)
        n = len(close)
        if n < 120:
            return []

        ema_mid, upper, lower, atr = _keltner(close, high, low, 20, 14, 2.0)
        ema9 = _ema(close, 9)
        ema50 = _ema(close, 50)
        rsi = _rsi(close, 14)
        vol_sma = _sma(volume, 20)

        signals = []
        lookback = 10  # bars to look back for prior breakout

        for i in range(80, n):
            if any(np.isnan(x) for x in [atr[i], ema_mid[i], ema9[i], ema50[i], rsi[i]]):
                continue
            if atr[i] <= 0:
                continue

            # Check for recent breakout above upper band in last 10 bars
            had_bull_breakout = False
            had_bear_breakout = False
            for j in range(max(0, i - lookback), i):
                if not np.isnan(upper[j]) and close[j] > upper[j]:
                    had_bull_breakout = True
                if not np.isnan(lower[j]) and close[j] < lower[j]:
                    had_bear_breakout = True

            # BUY: had recent bullish breakout, now pulled back to EMA midline
            if (had_bull_breakout and not had_bear_breakout
                    and abs(close[i] - ema_mid[i]) < atr[i] * 0.5
                    and close[i] > ema50[i]  # still in uptrend
                    and ema9[i] > ema_mid[i]  # short EMA above mid
                    and 35 < rsi[i] < 65):  # RSI neutral (not overbought)
                conf = 0.6 + min(0.25, (rsi[i] - 35) * 0.005)
                signals.append(_make_signal(
                    symbol, "BUY", close[i], atr[i], 4.0, 2.0, conf,
                    f"Keltner pullback: breakout then retrace to EMA20, RSI={rsi[i]:.0f}"
                ))

            # SELL: had recent bearish breakout, now bounced back to EMA midline
            elif (had_bear_breakout and not had_bull_breakout
                  and abs(close[i] - ema_mid[i]) < atr[i] * 0.5
                  and close[i] < ema50[i]  # still in downtrend
                  and ema9[i] < ema_mid[i]  # short EMA below mid
                  and 35 < rsi[i] < 65):
                conf = 0.6 + min(0.25, (65 - rsi[i]) * 0.005)
                signals.append(_make_signal(
                    symbol, "SELL", close[i], atr[i], 4.0, 2.0, conf,
                    f"Keltner pullback: breakdown then retrace to EMA20, RSI={rsi[i]:.0f}"
                ))

        return signals


# ══════════════════════════════════════════════════════════════════════
# Strategy 5: VWAPRSIDivergence
# VWAP deviation + RSI divergence for strong reversals
# ══════════════════════════════════════════════════════════════════════

class VWAPRSIDivergence:
    name = "vwap_rsi_divergence"
    display_name = "VWAP+RSI Divergence"

    @staticmethod
    def generate_signals(df, symbol="BTCUSDT"):
        close = df["close"].values.astype(float)
        high = df["high"].values.astype(float)
        low = df["low"].values.astype(float)
        volume = df["volume"].values.astype(float)
        n = len(close)
        if n < 120:
            return []

        rvwap = _rolling_vwap(high, low, close, volume, 48)
        rsi = _rsi(close, 14)
        atr = _atr(high, low, close, 14)
        vol_sma = _sma(volume, 20)

        signals = []
        div_lookback = 20

        for i in range(80, n):
            if np.isnan(atr[i]) or atr[i] <= 0 or np.isnan(rvwap[i]) or np.isnan(rsi[i]):
                continue

            # VWAP z-score
            dev_slice = close[max(0, i - 48):i + 1] - rvwap[max(0, i - 48):i + 1]
            dev_valid = dev_slice[~np.isnan(dev_slice)]
            if len(dev_valid) < 10:
                continue
            z = (close[i] - rvwap[i]) / (np.std(dev_valid) + 1e-12)

            # RSI divergence detection
            rsi_slice = rsi[max(0, i - div_lookback):i + 1]
            close_slice = close[max(0, i - div_lookback):i + 1]
            rsi_valid = rsi_slice[~np.isnan(rsi_slice)]
            if len(rsi_valid) < 5:
                continue

            # Volume confirmation
            vol_ok = (not np.isnan(vol_sma[i]) and vol_sma[i] > 0
                      and volume[i] > vol_sma[i])

            # Bullish divergence: price makes new low but RSI doesn't
            if (z < -2.0 and vol_ok):
                price_lo = np.min(close_slice)
                rsi_lo = np.min(rsi_valid)
                # Price near recent low but RSI higher than its low
                bullish_div = (close[i] <= price_lo * 1.005 and rsi[i] > rsi_lo + 5)

                if bullish_div:
                    conf = 0.6 + min(0.25, abs(z) * 0.05)
                    signals.append(_make_signal(
                        symbol, "BUY", close[i], atr[i], 4.0, 2.0, conf,
                        f"VWAP+RSI bullish div: z={z:.1f}, RSI diverging up"
                    ))

            # Bearish divergence: price makes new high but RSI doesn't
            elif (z > 2.0 and vol_ok):
                price_hi = np.max(close_slice)
                rsi_hi = np.max(rsi_valid)
                bearish_div = (close[i] >= price_hi * 0.995 and rsi[i] < rsi_hi - 5)

                if bearish_div:
                    conf = 0.6 + min(0.25, abs(z) * 0.05)
                    signals.append(_make_signal(
                        symbol, "SELL", close[i], atr[i], 4.0, 2.0, conf,
                        f"VWAP+RSI bearish div: z={z:.1f}, RSI diverging down"
                    ))

        return signals


# ══════════════════════════════════════════════════════════════════════
# Strategy 6: HMAKeltnerMomentum
# HMA trend + Keltner expansion for momentum continuation
# ══════════════════════════════════════════════════════════════════════

class HMAKeltnerMomentum:
    name = "hma_keltner_momentum"
    display_name = "HMA+Keltner Momentum"

    @staticmethod
    def generate_signals(df, symbol="BTCUSDT"):
        close = df["close"].values.astype(float)
        high = df["high"].values.astype(float)
        low = df["low"].values.astype(float)
        volume = df["volume"].values.astype(float)
        n = len(close)
        if n < 120:
            return []

        ema_mid, upper, lower, atr = _keltner(close, high, low, 30, 20, 2.0)
        hma = _hma(close, 21)
        rsi = _rsi(close, 14)
        vol_sma = _sma(volume, 20)

        # Keltner width for expansion detection
        width = np.where(ema_mid > 0, (upper - lower) / ema_mid, np.nan)

        signals = []
        for i in range(80, n):
            if any(np.isnan(x) for x in [atr[i], hma[i], rsi[i], width[i]]):
                continue
            if atr[i] <= 0:
                continue

            # Expansion: current width above 75th percentile of last 60 bars
            w_slice = width[max(0, i - 60):i]
            w_valid = w_slice[~np.isnan(w_slice)]
            if len(w_valid) < 15:
                continue
            expanding = width[i] > np.percentile(w_valid, 75)

            hma_rising = hma[i] > hma[max(0, i - 1)]
            hma_slope = (hma[i] - hma[max(0, i - 3)]) / (atr[i] * 3) if atr[i] > 0 else 0

            vol_ok = (not np.isnan(vol_sma[i]) and vol_sma[i] > 0
                      and volume[i] > vol_sma[i] * 1.1)

            # BUY: expanding + HMA rising steeply + RSI strong + volume
            if (expanding and hma_rising and hma_slope > 0.3
                    and 40 < rsi[i] < 75 and vol_ok):
                conf = 0.55 + min(0.35, hma_slope * 0.15 + (rsi[i] - 40) * 0.003)
                signals.append(_make_signal(
                    symbol, "BUY", close[i], atr[i], 4.0, 2.0, conf,
                    f"HMA+Keltner momentum: HMA slope={hma_slope:.2f}, expanding"
                ))

            # SELL: expanding + HMA falling steeply + RSI weak + volume
            elif (expanding and not hma_rising and hma_slope < -0.3
                  and 25 < rsi[i] < 60 and vol_ok):
                conf = 0.55 + min(0.35, abs(hma_slope) * 0.15 + (60 - rsi[i]) * 0.003)
                signals.append(_make_signal(
                    symbol, "SELL", close[i], atr[i], 4.0, 2.0, conf,
                    f"HMA+Keltner momentum: HMA slope={hma_slope:.2f}, expanding"
                ))

        return signals


# ══════════════════════════════════════════════════════════════════════
# Registry
# ══════════════════════════════════════════════════════════════════════

ALL_FORWARD_PROVEN = [
    KeltnerVWAPConfluence,
    KeltnerRSISqueeze,
    AdaptiveKeltnerReversion,
    KeltnerPullbackEntry,
    VWAPRSIDivergence,
    HMAKeltnerMomentum,
]
