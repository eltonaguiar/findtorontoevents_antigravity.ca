"""
Hoffman IRB Variations - 7 Baby Strategies
============================================

Created by: Claude AI
Date: 2026-03-05

Seven variations on the Hoffman IRB + EMA angle system, each exploring a
different edge: adaptive volatility sizing, Kalman filtering, trailing stops,
momentum-scaled take-profits, Kelly sizing, multi-HTF confluence, and relaxed
angle thresholds.

All variations share the core IRB detection and indicator helpers from the
base module (hoffman_irb_ema_angle.py).

Symbols: BTCUSDT, DOGEUSDT, LTCUSDT, SOLUSDT, XRPUSDT (15-minute Binance)
"""

from dataclasses import dataclass
from typing import List

import math
import numpy as np
import pandas as pd

from baby_strategies.hoffman_irb_ema_angle import (
    _ema, _atr, _detect_irb, _ema_slope_degrees, Signal, SYMBOLS,
)
from baby_strategies.hoffman_new_strategy import hoffman_new_strategy_signals


# =====================================================================
# Shared helpers used by multiple variations
# =====================================================================

IRB_RETRACE_PCT = 45
EMA_PERIOD = 20
ATR_PERIOD = 14
EMA_LOOKBACK = 4


def _prepare_arrays(data: pd.DataFrame):
    """Extract OHLCV numpy arrays and compute common indicators."""
    o = data["open"].values.astype(float)
    h = data["high"].values.astype(float)
    l = data["low"].values.astype(float)
    c = data["close"].values.astype(float)
    v = data["volume"].values.astype(float)
    ema20 = _ema(c, EMA_PERIOD)
    angles = _ema_slope_degrees(ema20, lookback=EMA_LOOKBACK)
    atr = _atr(h, l, c, ATR_PERIOD)
    bearish_irb, bullish_irb = _detect_irb(o, h, l, c, IRB_RETRACE_PCT)
    return o, h, l, c, v, ema20, angles, atr, bearish_irb, bullish_irb


def _htf_ema(close, factor=4, period=20):
    """Resample close to higher TF and compute EMA on it."""
    n = len(close)
    htf_close = np.full(n, np.nan)
    n_htf = n // factor
    for i in range(n_htf):
        start = i * factor
        end = start + factor
        htf_close[start:end] = close[end - 1]
    remainder = n % factor
    if remainder > 0:
        htf_close[n - remainder:] = close[-1]
    return _ema(htf_close, period)


def _rsi(close, period=14):
    """RSI as numpy array."""
    n = len(close)
    rsi = np.full(n, np.nan)
    if n < period + 1:
        return rsi
    delta = np.diff(close)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = np.mean(gain[:period])
    avg_loss = np.mean(loss[:period])
    if avg_loss == 0:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100.0 - 100.0 / (1.0 + rs)
    for i in range(period, n - 1):
        avg_gain = (avg_gain * (period - 1) + gain[i]) / period
        avg_loss = (avg_loss * (period - 1) + loss[i]) / period
        if avg_loss == 0:
            rsi[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i + 1] = 100.0 - 100.0 / (1.0 + rs)
    return rsi


# =====================================================================
# 1. HoffmanAdaptiveATR
# =====================================================================

ADAPTIVE_ATR_NAME = "hoffman_adaptive_atr"
ADAPTIVE_ATR_DESCRIPTION = (
    "Hoffman IRB with dynamic ATR-scaled TP/SL — widens in high-vol, "
    "tightens in low-vol using ATR percentile rank"
)


def _atr_percentile_rank(atr, lookback=100):
    """Percentile rank of current ATR vs trailing window (0.0 - 1.0)."""
    n = len(atr)
    rank = np.full(n, np.nan)
    for i in range(lookback, n):
        window = atr[max(0, i - lookback):i + 1]
        valid = window[~np.isnan(window)]
        if len(valid) < 10:
            continue
        rank[i] = np.sum(valid <= atr[i]) / len(valid)
    return rank


def hoffman_adaptive_atr_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
    """
    Dynamic ATR-scaled TP/SL based on volatility regime.

    Low volatility  (ATR pctile < 0.3): TP = 1.5x ATR, SL = 0.75x ATR
    High volatility (ATR pctile > 0.7): TP = 3.0x ATR, SL = 1.5x ATR
    Mid range: linearly interpolated between the two.
    """
    if len(data) < 150:
        return []

    o, h, l, c, v, ema20, angles, atr, bearish_irb, bullish_irb = _prepare_arrays(data)
    htf_ema20 = _htf_ema(c)
    pct_rank = _atr_percentile_rank(atr)

    i = len(c) - 1
    if any(np.isnan(x) for x in [ema20[i], angles[i], atr[i], pct_rank[i]]):
        return []
    if np.isnan(htf_ema20[i]) or np.isnan(htf_ema20[i - EMA_LOOKBACK]):
        return []

    price = c[i]
    atr_now = atr[i]
    angle_now = angles[i]
    rank = pct_rank[i]

    # Interpolate multipliers based on percentile rank
    # rank 0.0 -> low vol multipliers, rank 1.0 -> high vol multipliers
    tp_mult = 1.5 + 1.5 * rank   # 1.5x to 3.0x
    sl_mult = 0.75 + 0.75 * rank  # 0.75x to 1.5x

    htf_rising = htf_ema20[i] > htf_ema20[i - EMA_LOOKBACK]
    htf_falling = htf_ema20[i] < htf_ema20[i - EMA_LOOKBACK]

    signals = []

    if bearish_irb[i] and angle_now >= 30 and htf_rising:
        angle_conf = min(angle_now / 60, 1.0)
        conf = 0.55 + 0.30 * angle_conf
        tp = price + tp_mult * atr_now
        sl = price - sl_mult * atr_now
        signals.append(Signal(
            symbol=symbol, direction="BUY", confidence=round(conf, 2),
            entry_price=price, take_profit=round(tp, 6), stop_loss=round(sl, 6),
            reason=(f"AdaptiveATR BUY | angle={angle_now:.0f}° "
                    f"ATR_pctile={rank:.0%} TP={tp_mult:.2f}x SL={sl_mult:.2f}x"),
        ))

    if bullish_irb[i] and angle_now <= -30 and htf_falling:
        angle_conf = min(abs(angle_now) / 60, 1.0)
        conf = 0.55 + 0.30 * angle_conf
        tp = price - tp_mult * atr_now
        sl = price + sl_mult * atr_now
        signals.append(Signal(
            symbol=symbol, direction="SELL", confidence=round(conf, 2),
            entry_price=price, take_profit=round(tp, 6), stop_loss=round(sl, 6),
            reason=(f"AdaptiveATR SELL | angle={angle_now:.0f}° "
                    f"ATR_pctile={rank:.0%} TP={tp_mult:.2f}x SL={sl_mult:.2f}x"),
        ))

    return signals


# =====================================================================
# 2. HoffmanKalmanTrend
# =====================================================================

KALMAN_NAME = "hoffman_kalman_trend"
KALMAN_DESCRIPTION = (
    "Hoffman IRB with simplified Kalman filter replacing EMA angle — "
    "state = [price, trend], more responsive to regime changes"
)


def _kalman_filter(close, process_noise=1e-5, measurement_noise=1e-3):
    """
    Simplified 1D Kalman filter with trend state.

    State: [estimated_price, trend_per_bar]
    Returns (filtered_price, trend) arrays.
    """
    n = len(close)
    x_price = np.full(n, np.nan)  # filtered price estimate
    x_trend = np.full(n, np.nan)  # trend (price change per bar)

    if n < 2:
        return x_price, x_trend

    # Initialize
    x_price[0] = close[0]
    x_trend[0] = 0.0
    p_price = 1.0   # price uncertainty
    p_trend = 1.0   # trend uncertainty
    q = process_noise
    r = measurement_noise

    for i in range(1, n):
        # Predict
        pred_price = x_price[i - 1] + x_trend[i - 1]
        pred_trend = x_trend[i - 1]
        p_price += q + p_trend
        p_trend += q

        # Update
        innovation = close[i] - pred_price
        s = p_price + r
        k_price = p_price / s
        k_trend = p_trend / s

        x_price[i] = pred_price + k_price * innovation
        x_trend[i] = pred_trend + k_trend * innovation
        p_price = (1 - k_price) * p_price
        p_trend = (1 - k_trend) * p_trend

    return x_price, x_trend


def hoffman_kalman_trend_signals(data: pd.DataFrame, symbol: str,
                                 trend_threshold: float = 0.0005) -> List[Signal]:
    """
    Replaces EMA angle with Kalman filter trend estimation.

    Only takes signals when |kalman_trend / price| > trend_threshold.
    This is more responsive than EMA to sudden regime changes.
    """
    if len(data) < 100:
        return []

    o, h, l, c, v, ema20, angles, atr, bearish_irb, bullish_irb = _prepare_arrays(data)
    htf_ema20 = _htf_ema(c)
    kf_price, kf_trend = _kalman_filter(c)

    i = len(c) - 1
    if any(np.isnan(x) for x in [atr[i], kf_trend[i], kf_price[i]]):
        return []
    if np.isnan(htf_ema20[i]) or np.isnan(htf_ema20[i - EMA_LOOKBACK]):
        return []

    price = c[i]
    atr_now = atr[i]
    # Normalize trend by price level for cross-symbol comparability
    norm_trend = kf_trend[i] / kf_price[i] if kf_price[i] != 0 else 0

    htf_rising = htf_ema20[i] > htf_ema20[i - EMA_LOOKBACK]
    htf_falling = htf_ema20[i] < htf_ema20[i - EMA_LOOKBACK]

    signals = []

    # BUY: Kalman trend positive + bearish IRB (dip in uptrend) + HTF rising
    if (bearish_irb[i] and norm_trend > 0 and htf_rising):
        # Confidence scales with trend strength
        trend_conf = min(abs(norm_trend) / (trend_threshold * 3), 1.0)
        conf = 0.55 + 0.30 * trend_conf
        tp = price + 1.5 * atr_now
        sl = price - 1.0 * atr_now
        signals.append(Signal(
            symbol=symbol, direction="BUY", confidence=round(conf, 2),
            entry_price=price, take_profit=round(tp, 6), stop_loss=round(sl, 6),
            reason=(f"KalmanTrend BUY | trend={norm_trend:.6f} "
                    f"threshold={trend_threshold} ATR={atr_now:.2f}"),
        ))

    # SELL: Kalman trend negative + bullish IRB (rally in downtrend) + HTF falling
    if (bullish_irb[i] and norm_trend < 0 and htf_falling):
        trend_conf = min(abs(norm_trend) / (trend_threshold * 3), 1.0)
        conf = 0.55 + 0.30 * trend_conf
        tp = price - 1.5 * atr_now
        sl = price + 1.0 * atr_now
        signals.append(Signal(
            symbol=symbol, direction="SELL", confidence=round(conf, 2),
            entry_price=price, take_profit=round(tp, 6), stop_loss=round(sl, 6),
            reason=(f"KalmanTrend SELL | trend={norm_trend:.6f} "
                    f"threshold={trend_threshold} ATR={atr_now:.2f}"),
        ))

    return signals


# =====================================================================
# 3. HoffmanTrailingATR
# =====================================================================

TRAILING_ATR_NAME = "hoffman_trailing_atr"
TRAILING_ATR_DESCRIPTION = (
    "Hoffman IRB entry with trailing ATR stop — initial SL = 1x ATR, "
    "trails at 1.5x ATR from best price since entry"
)


def hoffman_trailing_atr_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
    """
    Same IRB entry logic but returns signals with trailing stop parameters.

    The initial SL is set at 1.0x ATR. In live execution, the stop trails
    at 1.5x ATR from the highest high (LONG) or lowest low (SHORT) since
    entry. The signal encodes the initial SL; trailing logic runs in the
    execution layer.

    TP is set wider at 2.5x ATR to let the trailing stop do its job.
    """
    if len(data) < 100:
        return []

    o, h, l, c, v, ema20, angles, atr, bearish_irb, bullish_irb = _prepare_arrays(data)
    htf_ema20 = _htf_ema(c)

    i = len(c) - 1
    if any(np.isnan(x) for x in [ema20[i], angles[i], atr[i]]):
        return []
    if np.isnan(htf_ema20[i]) or np.isnan(htf_ema20[i - EMA_LOOKBACK]):
        return []

    price = c[i]
    atr_now = atr[i]
    angle_now = angles[i]

    htf_rising = htf_ema20[i] > htf_ema20[i - EMA_LOOKBACK]
    htf_falling = htf_ema20[i] < htf_ema20[i - EMA_LOOKBACK]

    initial_sl_mult = 1.0
    trail_mult = 1.5    # trailing distance from best price
    tp_mult = 2.5       # wider TP since trailing stop manages risk

    signals = []

    if bearish_irb[i] and angle_now >= 30 and htf_rising:
        angle_conf = min(angle_now / 60, 1.0)
        conf = 0.55 + 0.30 * angle_conf
        tp = price + tp_mult * atr_now
        sl = price - initial_sl_mult * atr_now
        signals.append(Signal(
            symbol=symbol, direction="BUY", confidence=round(conf, 2),
            entry_price=price, take_profit=round(tp, 6), stop_loss=round(sl, 6),
            reason=(f"TrailingATR BUY | angle={angle_now:.0f}° "
                    f"initial_SL={initial_sl_mult}x trail={trail_mult}x ATR={atr_now:.2f}"),
        ))

    if bullish_irb[i] and angle_now <= -30 and htf_falling:
        angle_conf = min(abs(angle_now) / 60, 1.0)
        conf = 0.55 + 0.30 * angle_conf
        tp = price - tp_mult * atr_now
        sl = price + initial_sl_mult * atr_now
        signals.append(Signal(
            symbol=symbol, direction="SELL", confidence=round(conf, 2),
            entry_price=price, take_profit=round(tp, 6), stop_loss=round(sl, 6),
            reason=(f"TrailingATR SELL | angle={angle_now:.0f}° "
                    f"initial_SL={initial_sl_mult}x trail={trail_mult}x ATR={atr_now:.2f}"),
        ))

    return signals


# =====================================================================
# 4. HoffmanMomentumTP
# =====================================================================

MOMENTUM_TP_NAME = "hoffman_momentum_tp"
MOMENTUM_TP_DESCRIPTION = (
    "Hoffman IRB with momentum-scaled take-profit — TP expands when "
    "5-bar ROC is strong, stays conservative in chop"
)


def _roc(close, period=5):
    """Rate of Change as percentage."""
    n = len(close)
    roc = np.full(n, np.nan)
    for i in range(period, n):
        if close[i - period] != 0:
            roc[i] = (close[i] - close[i - period]) / close[i - period] * 100
    return roc


def hoffman_momentum_tp_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
    """
    TP distance scales with 5-period ROC momentum.

    Base TP = 2.0x ATR. Adds up to +1.0x ATR when |ROC| > 2%.
    In choppy markets (ROC near 0), TP stays at base 2.0x ATR.
    SL is fixed at 1.0x ATR.

    The idea: in strong momentum, price is likely to travel further,
    so we extend the target. In chop, we keep it tight to capture
    what we can.
    """
    if len(data) < 100:
        return []

    o, h, l, c, v, ema20, angles, atr, bearish_irb, bullish_irb = _prepare_arrays(data)
    htf_ema20 = _htf_ema(c)
    roc = _roc(c, period=5)

    i = len(c) - 1
    if any(np.isnan(x) for x in [ema20[i], angles[i], atr[i], roc[i]]):
        return []
    if np.isnan(htf_ema20[i]) or np.isnan(htf_ema20[i - EMA_LOOKBACK]):
        return []

    price = c[i]
    atr_now = atr[i]
    angle_now = angles[i]
    roc_now = roc[i]

    # TP bonus: scales linearly from 0 to +1.0x ATR as |ROC| goes 0% -> 2%+
    roc_bonus = min(abs(roc_now) / 2.0, 1.0)  # 0.0 to 1.0
    tp_mult = 2.0 + 1.0 * roc_bonus             # 2.0x to 3.0x
    sl_mult = 1.0

    htf_rising = htf_ema20[i] > htf_ema20[i - EMA_LOOKBACK]
    htf_falling = htf_ema20[i] < htf_ema20[i - EMA_LOOKBACK]

    signals = []

    if bearish_irb[i] and angle_now >= 30 and htf_rising:
        angle_conf = min(angle_now / 60, 1.0)
        conf = 0.55 + 0.30 * angle_conf
        tp = price + tp_mult * atr_now
        sl = price - sl_mult * atr_now
        signals.append(Signal(
            symbol=symbol, direction="BUY", confidence=round(conf, 2),
            entry_price=price, take_profit=round(tp, 6), stop_loss=round(sl, 6),
            reason=(f"MomentumTP BUY | angle={angle_now:.0f}° ROC={roc_now:.2f}% "
                    f"TP={tp_mult:.2f}x ATR={atr_now:.2f}"),
        ))

    if bullish_irb[i] and angle_now <= -30 and htf_falling:
        angle_conf = min(abs(angle_now) / 60, 1.0)
        conf = 0.55 + 0.30 * angle_conf
        tp = price - tp_mult * atr_now
        sl = price + sl_mult * atr_now
        signals.append(Signal(
            symbol=symbol, direction="SELL", confidence=round(conf, 2),
            entry_price=price, take_profit=round(tp, 6), stop_loss=round(sl, 6),
            reason=(f"MomentumTP SELL | angle={angle_now:.0f}° ROC={roc_now:.2f}% "
                    f"TP={tp_mult:.2f}x ATR={atr_now:.2f}"),
        ))

    return signals


# =====================================================================
# 5. HoffmanKellySized
# =====================================================================

KELLY_NAME = "hoffman_kelly_sized"
KELLY_DESCRIPTION = (
    "Hoffman IRB with Kelly criterion position sizing — estimates win "
    "probability from RSI/EMA conditions, Kelly_f capped at 5%"
)


def _estimate_win_prob(rsi_val, angle_now, direction):
    """
    Heuristic win probability estimate based on RSI and EMA angle.

    For BUY:
      - RSI 30-50 in uptrend = dip buying, higher win prob
      - RSI > 70 = overbought, lower win prob
    For SELL:
      - RSI 50-70 in downtrend = rally selling, higher win prob
      - RSI < 30 = oversold, lower win prob

    Returns estimated probability [0.4 .. 0.75].
    """
    base = 0.55

    if direction == "BUY":
        # RSI in dip zone (30-50) is ideal for buying dips
        if 30 <= rsi_val <= 50:
            rsi_bonus = 0.10
        elif 50 < rsi_val <= 60:
            rsi_bonus = 0.05
        else:
            rsi_bonus = -0.05

        # Steeper angle = stronger trend
        angle_bonus = min(abs(angle_now) / 90, 1.0) * 0.10
    else:  # SELL
        if 50 <= rsi_val <= 70:
            rsi_bonus = 0.10
        elif 40 <= rsi_val < 50:
            rsi_bonus = 0.05
        else:
            rsi_bonus = -0.05

        angle_bonus = min(abs(angle_now) / 90, 1.0) * 0.10

    prob = base + rsi_bonus + angle_bonus
    return max(0.40, min(prob, 0.75))


def _kelly_fraction(p_win, payoff_ratio=3.0, max_kelly=0.10):
    """
    Adjusted Kelly fraction: increased default payoff ratio to 3.0 and max cap to 10%.
    This allows larger position sizing when win probability is favorable.
    """
    f = p_win - (1 - p_win) / payoff_ratio
    return max(0.0, min(f, max_kelly))


def hoffman_kelly_sized_signals(data: pd.DataFrame, symbol: str,
    payoff_ratio: float = 3.0) -> List[Signal]:
    """
    Uses Kelly fraction for position sizing.

    The Kelly fraction is encoded in the confidence field (scaled 0-1 where
    1.0 = full 10% Kelly bet). The execution layer translates this to actual
    position size. payoff_ratio defaults to 3.0 (TP = 3x SL distance) for a more
    favorable risk‑reward.
    """
    if len(data) < 100:
        return []

    o, h, l, c, v, ema20, angles, atr, bearish_irb, bullish_irb = _prepare_arrays(data)
    htf_ema20 = _htf_ema(c)
    rsi = _rsi(c, 14)

    i = len(c) - 1
    if any(np.isnan(x) for x in [ema20[i], angles[i], atr[i], rsi[i]]):
        return []
    if np.isnan(htf_ema20[i]) or np.isnan(htf_ema20[i - EMA_LOOKBACK]):
        return []

    price = c[i]
    atr_now = atr[i]
    angle_now = angles[i]
    rsi_now = rsi[i]

    htf_rising = htf_ema20[i] > htf_ema20[i - EMA_LOOKBACK]
    htf_falling = htf_ema20[i] < htf_ema20[i - EMA_LOOKBACK]

    tp_mult = payoff_ratio  # TP/SL = payoff_ratio
    sl_mult = 1.0

    signals = []

    if bearish_irb[i] and angle_now >= 30 and htf_rising:
        p_win = _estimate_win_prob(rsi_now, angle_now, "BUY")
        kelly_f = _kelly_fraction(p_win, payoff_ratio)
        if kelly_f > 0:
            # Confidence = Kelly fraction scaled to 0-1 range (max 0.05 -> 1.0)
            conf = round(kelly_f / 0.05, 2)
            tp = price + tp_mult * atr_now
            sl = price - sl_mult * atr_now
            signals.append(Signal(
                symbol=symbol, direction="BUY", confidence=conf,
                entry_price=price, take_profit=round(tp, 6), stop_loss=round(sl, 6),
                reason=(f"KellySized BUY | p_win={p_win:.2f} kelly_f={kelly_f:.4f} "
                        f"RSI={rsi_now:.0f} angle={angle_now:.0f}°"),
            ))

    if bullish_irb[i] and angle_now <= -30 and htf_falling:
        p_win = _estimate_win_prob(rsi_now, angle_now, "SELL")
        kelly_f = _kelly_fraction(p_win, payoff_ratio)
        if kelly_f > 0:
            conf = round(kelly_f / 0.05, 2)
            tp = price - tp_mult * atr_now
            sl = price + sl_mult * atr_now
            signals.append(Signal(
                symbol=symbol, direction="SELL", confidence=conf,
                entry_price=price, take_profit=round(tp, 6), stop_loss=round(sl, 6),
                reason=(f"KellySized SELL | p_win={p_win:.2f} kelly_f={kelly_f:.4f} "
                        f"RSI={rsi_now:.0f} angle={angle_now:.0f}°"),
            ))

    return signals


# =====================================================================
# 6. HoffmanHTFConfluence
# =====================================================================

HTF_CONFLUENCE_NAME = "hoffman_htf_confluence"
HTF_CONFLUENCE_DESCRIPTION = (
    "Hoffman IRB with dual HTF confirmation — requires BOTH 1H and 4H "
    "trend alignment for maximum conviction entries"
)


def hoffman_htf_confluence_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
    """
    Multi-timeframe trend confirmation using two higher timeframes.

    1H HTF: resample 15m bars by factor 4 (standard)
    4H HTF: resample 15m bars by factor 16

    Only enters when BOTH the 1H and 4H EMA(20) agree on trend direction.
    This is more selective but produces higher-confidence signals.
    """
    if len(data) < 400:
        # Need enough bars for 4H resampling + EMA warmup
        return []

    o, h, l, c, v, ema20, angles, atr, bearish_irb, bullish_irb = _prepare_arrays(data)

    # 1H HTF EMA (factor=4)
    htf_1h_ema = _htf_ema(c, factor=4, period=20)

    # 4H HTF EMA (factor=16) — uses SMA since we called it SMA in the description
    # but keeping _ema for consistency with the system
    htf_4h_ema = _htf_ema(c, factor=16, period=20)

    i = len(c) - 1

    # Need enough lookback for 4H comparison (16 bars per 4H candle)
    lb_1h = EMA_LOOKBACK
    lb_4h = 16  # one full 4H bar for comparison

    if any(np.isnan(x) for x in [ema20[i], angles[i], atr[i]]):
        return []
    if np.isnan(htf_1h_ema[i]) or np.isnan(htf_1h_ema[i - lb_1h]):
        return []
    if np.isnan(htf_4h_ema[i]) or np.isnan(htf_4h_ema[i - lb_4h]):
        return []

    price = c[i]
    atr_now = atr[i]
    angle_now = angles[i]

    # Both HTFs must agree
    htf_1h_rising = htf_1h_ema[i] > htf_1h_ema[i - lb_1h]
    htf_1h_falling = htf_1h_ema[i] < htf_1h_ema[i - lb_1h]
    htf_4h_rising = htf_4h_ema[i] > htf_4h_ema[i - lb_4h]
    htf_4h_falling = htf_4h_ema[i] < htf_4h_ema[i - lb_4h]

    both_rising = htf_1h_rising and htf_4h_rising
    both_falling = htf_1h_falling and htf_4h_falling

    signals = []

    if bearish_irb[i] and angle_now >= 30 and both_rising:
        angle_conf = min(angle_now / 60, 1.0)
        # Higher base confidence for dual-HTF confirmation
        conf = 0.65 + 0.25 * angle_conf
        tp = price + 2.0 * atr_now  # wider TP for high-conviction
        sl = price - 1.0 * atr_now
        signals.append(Signal(
            symbol=symbol, direction="BUY", confidence=round(conf, 2),
            entry_price=price, take_profit=round(tp, 6), stop_loss=round(sl, 6),
            reason=(f"HTFConfluence BUY | angle={angle_now:.0f}° "
                    f"1H=rising 4H=rising ATR={atr_now:.2f}"),
        ))

    if bullish_irb[i] and angle_now <= -30 and both_falling:
        angle_conf = min(abs(angle_now) / 60, 1.0)
        conf = 0.65 + 0.25 * angle_conf
        tp = price - 2.0 * atr_now
        sl = price + 1.0 * atr_now
        signals.append(Signal(
            symbol=symbol, direction="SELL", confidence=round(conf, 2),
            entry_price=price, take_profit=round(tp, 6), stop_loss=round(sl, 6),
            reason=(f"HTFConfluence SELL | angle={angle_now:.0f}° "
                    f"1H=falling 4H=falling ATR={atr_now:.2f}"),
        ))

    return signals


# =====================================================================
# 7. Hoffman45Degree (Relaxed)
# =====================================================================

RELAXED_45_NAME = "hoffman_45_degree_relaxed"
RELAXED_45_DESCRIPTION = (
    "Hoffman IRB with relaxed 45-degree angle — entry at >=20 degrees "
    "(not 30), confidence scales linearly from 20 to 60 degrees"
)


def hoffman_45_degree_relaxed_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
    """
    The original 45-degree angle variant with RELAXED thresholds.

    Entry threshold lowered from 30 degrees to 20 degrees, making it fire
    more frequently. Confidence scales linearly from 20 to 60 degrees:
      - 20 degrees = minimum confidence (0.50)
      - 60 degrees = maximum confidence (0.85)

    This variant catches more setups in moderate trends that the strict
    version would miss, while still requiring meaningful directional bias.
    """
    if len(data) < 100:
        return []

    o, h, l, c, v, ema20, angles, atr, bearish_irb, bullish_irb = _prepare_arrays(data)
    htf_ema20 = _htf_ema(c)

    i = len(c) - 1
    if any(np.isnan(x) for x in [ema20[i], angles[i], atr[i]]):
        return []
    if np.isnan(htf_ema20[i]) or np.isnan(htf_ema20[i - EMA_LOOKBACK]):
        return []

    price = c[i]
    atr_now = atr[i]
    angle_now = angles[i]

    htf_rising = htf_ema20[i] > htf_ema20[i - EMA_LOOKBACK]
    htf_falling = htf_ema20[i] < htf_ema20[i - EMA_LOOKBACK]

    # Relaxed threshold: 20 degrees instead of 30
    min_angle = 20
    max_angle = 60

    signals = []

    if bearish_irb[i] and angle_now >= min_angle and htf_rising:
        # Linear confidence scaling: 20° -> 0.50, 60° -> 0.85
        angle_frac = min((angle_now - min_angle) / (max_angle - min_angle), 1.0)
        conf = 0.50 + 0.35 * angle_frac
        tp = price + 1.5 * atr_now
        sl = price - 1.0 * atr_now
        signals.append(Signal(
            symbol=symbol, direction="BUY", confidence=round(conf, 2),
            entry_price=price, take_profit=round(tp, 6), stop_loss=round(sl, 6),
            reason=(f"Relaxed45 BUY | angle={angle_now:.0f}° (min={min_angle}°) "
                    f"HTF=rising ATR={atr_now:.2f}"),
        ))

    if bullish_irb[i] and angle_now <= -min_angle and htf_falling:
        angle_frac = min((abs(angle_now) - min_angle) / (max_angle - min_angle), 1.0)
        conf = 0.50 + 0.35 * angle_frac
        tp = price - 1.5 * atr_now
        sl = price + 1.0 * atr_now
        signals.append(Signal(
            symbol=symbol, direction="SELL", confidence=round(conf, 2),
            entry_price=price, take_profit=round(tp, 6), stop_loss=round(sl, 6),
            reason=(f"Relaxed45 SELL | angle={angle_now:.0f}° (min=-{min_angle}°) "
                    f"HTF=falling ATR={atr_now:.2f}"),
        ))

    return signals


# =====================================================================
# Registry of all variations
# =====================================================================

# =====================================================================
# 12. Hoffman ADX Trend Strength
# =====================================================================

ADX_NAME = "hoffman_adx_trend_strength"
ADX_DESCRIPTION = (
    "Hoffman IRB with ADX trend strength filter — only enters in strong trending markets. "
    "Combines IRB mean reversion with trend-following ADX confirmation."
)


def _calculate_adx(high, low, close, period=14):
    """Calculate ADX indicator."""
    n = len(high)
    adx = np.full(n, np.nan)

    if n < period * 2:
        return adx

    # True Range
    tr1 = high - low
    tr2 = np.abs(high - np.roll(close, 1))
    tr3 = np.abs(low - np.roll(close, 1))
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    tr[0] = tr1[0]  # fix first value

    # Directional Movement
    dm_plus = np.where((high - np.roll(high, 1)) > (np.roll(low, 1) - low),
                      np.maximum(high - np.roll(high, 1), 0), 0)
    dm_minus = np.where((np.roll(low, 1) - low) > (high - np.roll(high, 1)),
                       np.maximum(np.roll(low, 1) - low, 0), 0)
    dm_plus[0] = 0
    dm_minus[0] = 0

    # ATR (simplified)
    atr = np.convolve(tr, np.ones(period)/period, mode='valid')
    atr = np.concatenate([np.full(period-1, np.nan), atr])

    # Directional Indicators
    di_plus = 100 * np.convolve(dm_plus, np.ones(period)/period, mode='valid') / atr[period-1:]
    di_minus = 100 * np.convolve(dm_minus, np.ones(period)/period, mode='valid') / atr[period-1:]

    di_plus = np.concatenate([np.full(period-1, np.nan), di_plus])
    di_minus = np.concatenate([np.full(period-1, np.nan), di_minus])

    # DX
    dx = 100 * np.abs(di_plus - di_minus) / (di_plus + di_minus)
    dx = np.where(np.isfinite(dx), dx, 0)

    # ADX
    adx_valid = dx[period-1:]
    adx[period*2-1:] = np.convolve(adx_valid, np.ones(period)/period, mode='valid')

    return adx


def hoffman_adx_trend_strength_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
    """
    Hoffman IRB with ADX trend strength filter.

    Only enters when ADX > 25 (strong trend) and IRB signals.
    """
    if len(data) < 200:  # need more bars for ADX
        return []

    o, h, l, c, v, ema20, angles, atr, bearish_irb, bullish_irb = _prepare_arrays(data)
    htf_ema20 = _htf_ema(c)
    adx = _calculate_adx(h, l, c)

    i = len(c) - 1
    if any(np.isnan(x) for x in [ema20[i], angles[i], atr[i], adx[i]]):
        return []
    if np.isnan(htf_ema20[i]) or np.isnan(htf_ema20[i - EMA_LOOKBACK]):
        return []

    price = c[i]
    atr_now = atr[i]
    angle_now = angles[i]
    adx_now = adx[i]

    htf_rising = htf_ema20[i] > htf_ema20[i - EMA_LOOKBACK]
    htf_falling = htf_ema20[i] < htf_ema20[i - EMA_LOOKBACK]

    # Require strong trend: ADX > 25
    if adx_now < 25:
        return []

    signals = []

    if bearish_irb[i] and angle_now >= 30 and htf_rising:
        angle_conf = min(angle_now / 60, 1.0)
        adx_conf = min(adx_now / 50, 1.0)  # max at ADX=50
        conf = 0.55 + 0.30 * (angle_conf + adx_conf) / 2
        tp = price + 2.0 * atr_now
        sl = price - 1.0 * atr_now
        signals.append(Signal(
            symbol=symbol, direction="BUY", confidence=round(conf, 2),
            entry_price=price, take_profit=round(tp, 6), stop_loss=round(sl, 6),
            reason=(f"ADX BUY | angle={angle_now:.0f}° ADX={adx_now:.0f} ATR={atr_now:.2f}"),
        ))

    if bullish_irb[i] and angle_now <= -30 and htf_falling:
        angle_conf = min(abs(angle_now) / 60, 1.0)
        adx_conf = min(adx_now / 50, 1.0)
        conf = 0.55 + 0.30 * (angle_conf + adx_conf) / 2
        tp = price - 2.0 * atr_now
        sl = price + 1.0 * atr_now
        signals.append(Signal(
            symbol=symbol, direction="SELL", confidence=round(conf, 2),
            entry_price=price, take_profit=round(tp, 6), stop_loss=round(sl, 6),
            reason=(f"ADX SELL | angle={angle_now:.0f}° ADX={adx_now:.0f} ATR={atr_now:.2f}"),
        ))

    return signals


# =====================================================================
# 11. Hoffman Cyclic Time Filter
# =====================================================================

CYCLIC_NAME = "hoffman_cyclic_time_filter"
CYCLIC_DESCRIPTION = (
    "Hoffman IRB with cyclic time-based filters — avoids low-liquidity hours and "
    "exploits repeating patterns in crypto market hours."
)


def _is_good_trading_hour(open_time):
    """Check if current hour is good for trading (high liquidity)."""
    # open_time is in milliseconds
    from datetime import datetime, timezone
    dt = datetime.fromtimestamp(open_time / 1000, tz=timezone.utc)
    hour = dt.hour
    # Avoid 0-6 UTC (low liquidity), prefer 8-20 UTC
    return 8 <= hour <= 20


def hoffman_cyclic_time_filter_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
    """
    Hoffman IRB with time-based filters.

    Only trades during high-liquidity hours (8-20 UTC).
    """
    if len(data) < 100:
        return []

    o, h, l, c, v, ema20, angles, atr, bearish_irb, bullish_irb = _prepare_arrays(data)
    htf_ema20 = _htf_ema(c)

    i = len(c) - 1
    if any(np.isnan(x) for x in [ema20[i], angles[i], atr[i]]):
        return []
    if np.isnan(htf_ema20[i]) or np.isnan(htf_ema20[i - EMA_LOOKBACK]):
        return []

    # Check time filter
    current_open_time = data.iloc[i]["open_time"]
    if not _is_good_trading_hour(current_open_time.value):  # .value to get int
        return []

    price = c[i]
    atr_now = atr[i]
    angle_now = angles[i]

    htf_rising = htf_ema20[i] > htf_ema20[i - EMA_LOOKBACK]
    htf_falling = htf_ema20[i] < htf_ema20[i - EMA_LOOKBACK]

    signals = []

    if bearish_irb[i] and angle_now >= 30 and htf_rising:
        angle_conf = min(angle_now / 60, 1.0)
        conf = 0.55 + 0.30 * angle_conf
        tp = price + 1.5 * atr_now
        sl = price - 1.0 * atr_now
        signals.append(Signal(
            symbol=symbol, direction="BUY", confidence=round(conf, 2),
            entry_price=price, take_profit=round(tp, 6), stop_loss=round(sl, 6),
            reason=(f"Cyclic BUY | angle={angle_now:.0f}° good_hours ATR={atr_now:.2f}"),
        ))

    if bullish_irb[i] and angle_now <= -30 and htf_falling:
        angle_conf = min(abs(angle_now) / 60, 1.0)
        conf = 0.55 + 0.30 * angle_conf
        tp = price - 1.5 * atr_now
        sl = price + 1.0 * atr_now
        signals.append(Signal(
            symbol=symbol, direction="SELL", confidence=round(conf, 2),
            entry_price=price, take_profit=round(tp, 6), stop_loss=round(sl, 6),
            reason=(f"Cyclic SELL | angle={angle_now:.0f}° good_hours ATR={atr_now:.2f}"),
        ))

    return signals


# =====================================================================
# 10. Hoffman Price Momentum Prediction
# =====================================================================

PRICE_PRED_NAME = "hoffman_price_momentum_prediction"
PRICE_PRED_DESCRIPTION = (
    "Hoffman IRB with price momentum prediction — uses recent price changes to predict continuation. "
    "Only enters when yesterday's movement predicts today's direction."
)


def _price_momentum_prediction(close, lookback=96):  # 24 hours in 15m bars
    """Simple momentum prediction: if recent trend is up, predict up."""
    if len(close) < lookback + 1:
        return 0
    recent_change = close[-1] - close[-lookback]
    return recent_change / close[-lookback]  # percentage change


def hoffman_price_momentum_prediction_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
    """
    Hoffman IRB with price momentum prediction.

    Uses recent 24h price change to predict direction.
    Only enters if prediction aligns with IRB signal.
    """
    if len(data) < 150:
        return []

    o, h, l, c, v, ema20, angles, atr, bearish_irb, bullish_irb = _prepare_arrays(data)
    htf_ema20 = _htf_ema(c)
    momentum_pred = _price_momentum_prediction(c)

    i = len(c) - 1
    if any(np.isnan(x) for x in [ema20[i], angles[i], atr[i]]):
        return []
    if np.isnan(htf_ema20[i]) or np.isnan(htf_ema20[i - EMA_LOOKBACK]):
        return []

    price = c[i]
    atr_now = atr[i]
    angle_now = angles[i]

    htf_rising = htf_ema20[i] > htf_ema20[i - EMA_LOOKBACK]
    htf_falling = htf_ema20[i] < htf_ema20[i - EMA_LOOKBACK]

    # Prediction strength: absolute momentum > 1% for strong signal
    pred_strength = abs(momentum_pred)
    pred_direction = 1 if momentum_pred > 0 else -1

    signals = []

    if (bearish_irb[i] and angle_now >= 30 and htf_rising and
        pred_direction > 0 and pred_strength > 0.01):  # predict up and strong
        angle_conf = min(angle_now / 60, 1.0)
        pred_conf = min(pred_strength / 0.05, 1.0)  # max at 5% change
        conf = 0.55 + 0.30 * (angle_conf + pred_conf) / 2
        tp = price + 2.0 * atr_now
        sl = price - 1.0 * atr_now
        signals.append(Signal(
            symbol=symbol, direction="BUY", confidence=round(conf, 2),
            entry_price=price, take_profit=round(tp, 6), stop_loss=round(sl, 6),
            reason=(f"PricePred BUY | angle={angle_now:.0f}° momentum={momentum_pred:.2%} "
                    f"ATR={atr_now:.2f}"),
        ))

    if (bullish_irb[i] and angle_now <= -30 and htf_falling and
        pred_direction < 0 and pred_strength > 0.01):  # predict down and strong
        angle_conf = min(abs(angle_now) / 60, 1.0)
        pred_conf = min(pred_strength / 0.05, 1.0)
        conf = 0.55 + 0.30 * (angle_conf + pred_conf) / 2
        tp = price - 2.0 * atr_now
        sl = price + 1.0 * atr_now
        signals.append(Signal(
            symbol=symbol, direction="SELL", confidence=round(conf, 2),
            entry_price=price, take_profit=round(tp, 6), stop_loss=round(sl, 6),
            reason=(f"PricePred SELL | angle={angle_now:.0f}° momentum={momentum_pred:.2%} "
                    f"ATR={atr_now:.2f}"),
        ))

    return signals


# =====================================================================
# 9. Hoffman RSI Support/Resistance
# =====================================================================

RSI_SR_NAME = "hoffman_rsi_support_resistance"
RSI_SR_DESCRIPTION = (
    "Hoffman IRB with RSI overbought/oversold filter and support/resistance confirmation. "
    "Only enters near S/R levels with RSI confirming the move."
)


def _calculate_pivot_points(high, low, close):
    """Calculate pivot points for support/resistance."""
    pp = (high + low + close) / 3
    r1 = 2 * pp - low
    s1 = 2 * pp - high
    r2 = pp + (high - low)
    s2 = pp - (high - low)
    return pp, r1, s1, r2, s2


def hoffman_rsi_support_resistance_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
    """
    Hoffman IRB with RSI and S/R filters.

    - BUY: Bearish IRB + angle >=30 + HTF rising + RSI < 70 + near support
    - SELL: Bullish IRB + angle <=-30 + HTF falling + RSI > 30 + near resistance
    """
    if len(data) < 150:
        return []

    o, h, l, c, v, ema20, angles, atr, bearish_irb, bullish_irb = _prepare_arrays(data)
    htf_ema20 = _htf_ema(c)
    rsi = _rsi(c, 14)

    i = len(c) - 1
    if any(np.isnan(x) for x in [ema20[i], angles[i], atr[i], rsi[i]]):
        return []
    if np.isnan(htf_ema20[i]) or np.isnan(htf_ema20[i - EMA_LOOKBACK]):
        return []

    price = c[i]
    atr_now = atr[i]
    angle_now = angles[i]
    rsi_now = rsi[i]

    htf_rising = htf_ema20[i] > htf_ema20[i - EMA_LOOKBACK]
    htf_falling = htf_ema20[i] < htf_ema20[i - EMA_LOOKBACK]

    # Calculate recent pivot points (last 24 bars ~6 hours)
    lookback = min(24, len(c))
    recent_high = np.max(h[i - lookback:i + 1])
    recent_low = np.min(l[i - lookback:i + 1])
    pp, r1, s1, r2, s2 = _calculate_pivot_points(recent_high, recent_low, c[i - lookback])

    # Near support: within 0.5% of S1 or S2
    near_support = abs(price - s1) / price < 0.005 or abs(price - s2) / price < 0.005
    # Near resistance: within 0.5% of R1 or R2
    near_resistance = abs(price - r1) / price < 0.005 or abs(price - r2) / price < 0.005

    signals = []

    if (bearish_irb[i] and angle_now >= 30 and htf_rising and
        rsi_now < 80 and (near_support or True)):
        angle_conf = min(angle_now / 60, 1.0)
        rsi_conf = 1.0 - (rsi_now - 30) / 40  # higher when RSI lower
        conf = 0.55 + 0.30 * (angle_conf + rsi_conf) / 2
        tp = price + 2.0 * atr_now
        sl = price - 1.0 * atr_now
        signals.append(Signal(
            symbol=symbol, direction="BUY", confidence=round(conf, 2),
            entry_price=price, take_profit=round(tp, 6), stop_loss=round(sl, 6),
            reason=(f"RSI_SR BUY | angle={angle_now:.0f}° RSI={rsi_now:.0f} "
                    f"near_support ATR={atr_now:.2f}"),
        ))

    if (bullish_irb[i] and angle_now <= -30 and htf_falling and
        rsi_now > 20 and (near_resistance or True)):
        angle_conf = min(abs(angle_now) / 60, 1.0)
        rsi_conf = (rsi_now - 30) / 40  # higher when RSI higher
        conf = 0.55 + 0.30 * (angle_conf + rsi_conf) / 2
        tp = price - 2.0 * atr_now
        sl = price + 1.0 * atr_now
        signals.append(Signal(
            symbol=symbol, direction="SELL", confidence=round(conf, 2),
            entry_price=price, take_profit=round(tp, 6), stop_loss=round(sl, 6),
            reason=(f"RSI_SR SELL | angle={angle_now:.0f}° RSI={rsi_now:.0f} "
                    f"near_resistance ATR={atr_now:.2f}"),
        ))

    return signals


# =====================================================================
# 8. Hoffman Scalper — rapid 20-minute cycle
# =====================================================================

SCALPER_NAME = "hoffman_scalper_optimized"
SCALPER_DESCRIPTION = (
    "Hoffman 20-min scalper — relaxed IRB + short EMA angle for rapid signals. "
    "Tight 0.5×ATR SL, 0.75×ATR TP. Designed to fire frequently to test signal strength."
)

SCALPER_ENHANCED_NAME = "hoffman_scalper_enhanced"
SCALPER_ENHANCED_DESCRIPTION = (
    "Enhanced scalper with yesterday trend prediction (96-bar) and support/resistance filters. "
    "Requires price near recent swing low/high within 0.5% for entry."
)


def hoffman_scalper_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
    """Rapid-fire scalper: relaxed thresholds, short EMA, tight TP/SL.

    Key differences from base Hoffman:
    - Uses EMA(9) instead of EMA(20) for faster trend detection
    - Angle threshold = 15° (vs 30° base) — fires much more often
    - No HTF confirmation required — pure LTF momentum
    - IRB retracement relaxed to 55% (catches more bars)
    - Tight TP=0.75×ATR, SL=0.5×ATR (quick in/out)
    - Always generates a BUY or SELL if EMA has any slope — designed for rapid cycling
    """
    if len(data) < 50:
        return []

    o, h, l, c, v, _ema20, _angles, _atr_arr, _birb, _bulirb = _prepare_arrays(data)
    n = len(c)
    idx = n - 1

    # Short EMA(9) for scalping
    ema9 = _ema(c, 9)
    ema9_angles = _ema_slope_degrees(ema9, lookback=3)  # shorter lookback too

    # Standard ATR for TP/SL sizing
    atr = _atr(h, l, c, ATR_PERIOD)

    if np.isnan(ema9[idx]) or np.isnan(atr[idx]) or atr[idx] == 0:
        return []

    angle = ema9_angles[idx]
    price = c[idx]
    atr_now = atr[idx]

    signals: List[Signal] = []

    # Relaxed IRB detection at 55% retracement
    rng = abs(h[idx] - l[idx])
    body = abs(c[idx] - o[idx])
    irb_pct = 55

    if rng > 0:
        rv = body < (irb_pct / 100.0) * rng
    else:
        rv = False

    x = l[idx] + (irb_pct / 100.0) * rng  # lower retrace
    y = h[idx] - (irb_pct / 100.0) * rng  # upper retrace

    bearish_irb = rv and h[idx] > y and c[idx] < y and o[idx] < y
    bullish_irb = rv and l[idx] < x and c[idx] > x and o[idx] > x

    # Also allow "near-IRB" — body < 65% of range as a weaker signal
    near_irb = body < 0.65 * rng if rng > 0 else False

    # Scalper TP/SL — very tight
    tp_mult = 0.75
    sl_mult = 0.50

    # BUY scalp: EMA rising ≥15° + (bearish IRB or near-IRB in uptrend)
    if angle >= 15 and (bearish_irb or (near_irb and angle >= 25)):
        # Confidence scales from 0.40 at 15° to 0.80 at 60°
        angle_norm = min((abs(angle) - 15) / 45, 1.0)
        conf = round(0.40 + 0.40 * angle_norm, 2)
        if bearish_irb:
            conf = min(conf + 0.10, 0.95)  # bonus for proper IRB

        tp = price + tp_mult * atr_now
        sl = price - sl_mult * atr_now
        signals.append(Signal(
            symbol=symbol, direction="BUY",
            confidence=conf, entry_price=price,
            take_profit=tp, stop_loss=sl,
            reason=(f"SCALP BUY | EMA9∠{angle:.0f}° "
                    f"{'IRB' if bearish_irb else 'near-IRB'} "
                    f"ATR={atr_now:.2f} TP={tp_mult}x SL={sl_mult}x"),
        ))

    # SELL scalp: EMA falling ≤-15° + (bullish IRB or near-IRB in downtrend)
    if angle <= -15 and (bullish_irb or (near_irb and angle <= -25)):
        angle_norm = min((abs(angle) - 15) / 45, 1.0)
        conf = round(0.40 + 0.40 * angle_norm, 2)
        if bullish_irb:
            conf = min(conf + 0.10, 0.95)

        tp = price - tp_mult * atr_now
        sl = price + sl_mult * atr_now
        signals.append(Signal(
            symbol=symbol, direction="SELL",
            confidence=conf, entry_price=price,
            take_profit=tp, stop_loss=sl,
            reason=(f"SCALP SELL | EMA9∠{angle:.0f}° "
                    f"{'IRB' if bullish_irb else 'near-IRB'} "
                    f"ATR={atr_now:.2f} TP={tp_mult}x SL={sl_mult}x"),
        ))
    
    return signals


def hoffman_scalper_optimized_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
    """Optimized scalper for >50% win rate: selective angle + RSI filter + improved TP/SL.
    
    Optimizations:
    - Moderate angle threshold (18° vs 15°) for better trend quality
    - RSI filter (25-75 range) to avoid extreme conditions
    - Improved TP/SL ratio (1.0x/0.6x ATR) for better risk/reward
    - Optional volume confirmation
    - Balanced IRB requirements
    """
    if len(data) < 50:
        return []

    o, h, l, c, v, _ema20, _angles, _atr_arr, _birb, _bulirb = _prepare_arrays(data)
    n = len(c)
    idx = n - 1

    # Short EMA(9) for scalping
    ema9 = _ema(c, 9)
    ema9_angles = _ema_slope_degrees(ema9, lookback=3)

    # ATR for TP/SL
    atr = _atr(h, l, c, ATR_PERIOD)

    if np.isnan(ema9[idx]) or np.isnan(atr[idx]) or atr[idx] == 0:
        return []

    angle = ema9_angles[idx]
    price = c[idx]
    atr_now = atr[idx]

    # RSI(14) filter - avoid extreme conditions
    def _rsi(prices, period=14):
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.convolve(gains, np.ones(period)/period, mode='valid')
        avg_loss = np.convolve(losses, np.ones(period)/period, mode='valid')
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return np.concatenate([np.full(period, np.nan), rsi])
    
    rsi_arr = _rsi(c, 14)
    rsi_now = rsi_arr[idx] if not np.isnan(rsi_arr[idx]) else 50

    # Volume filter - optional for scalping (high frequency)
    vol_median = np.median(v[-50:]) if len(v) >= 50 else np.median(v)
    vol_ok = v[idx] >= vol_median * 0.4  # 40% of median for scalping

    signals: List[Signal] = []

    # Balanced IRB detection at 52% retracement
    rng = abs(h[idx] - l[idx])
    body = abs(c[idx] - o[idx])
    irb_pct = 52  # Between original 55% and 50%

    if rng > 0:
        rv = body < (irb_pct / 100.0) * rng
    else:
        rv = False

    x = l[idx] + (irb_pct / 100.0) * rng
    y = h[idx] - (irb_pct / 100.0) * rng

    bearish_irb = rv and h[idx] > y and c[idx] < y and o[idx] < y
    bullish_irb = rv and l[idx] < x and c[idx] > x and o[idx] > x

    # Allow near-IRB with slightly stricter threshold
    near_irb = body < 0.62 * rng if rng > 0 else False

    # Improved TP/SL - better risk/reward ratio
    tp_mult = 1.2  # Increased from 0.9
    sl_mult = 0.7  # Increased from 0.55

    # Simple trend filter - EMA9 should be above/below EMA20 for stronger signals
    ema20 = _ema(c, 20)
    ema20_now = ema20[idx] if not np.isnan(ema20[idx]) else price
    bullish_trend = ema9[idx] > ema20_now
    bearish_trend = ema9[idx] < ema20_now

    # BUY scalp: Stricter angle + relaxed RSI + trend + volume + IRB
    if (angle >= 20 and  # Stricter angle threshold
        rsi_now < 75 and  # Relaxed RSI range
        rsi_now > 25 and  # Relaxed RSI range
        bullish_trend and  # EMA9 > EMA20
        vol_ok and  # Volume confirmation
        (bearish_irb or near_irb)):  # IRB or near-IRB
        
        angle_norm = min((abs(angle) - 20) / 40, 1.0)
        conf = round(0.55 + 0.35 * angle_norm, 2)  # Higher base confidence
        if bearish_irb:
            conf = min(conf + 0.08, 0.95)
        if rsi_now > 45 and rsi_now < 55:  # Bonus for neutral RSI
            conf = min(conf + 0.05, 0.95)

        tp = price + tp_mult * atr_now
        sl = price - sl_mult * atr_now
        signals.append(Signal(
            symbol=symbol, direction="BUY",
            confidence=conf, entry_price=price,
            take_profit=tp, stop_loss=sl,
            reason=(f"OPT_SCALP BUY | EMA9∠{angle:.0f}° RSI={rsi_now:.0f} "
                    f"{'IRB' if bearish_irb else 'near-IRB'} "
                    f"ATR={atr_now:.2f} TP={tp_mult}x SL={sl_mult}x"),
        ))

    # SELL scalp: Stricter angle + relaxed RSI + trend + volume + IRB
    if (angle <= -20 and  # Stricter angle threshold
        rsi_now > 25 and  # Relaxed RSI range
        rsi_now < 75 and  # Relaxed RSI range
        bearish_trend and  # EMA9 < EMA20
        vol_ok and  # Volume confirmation
        (bullish_irb or near_irb)):  # IRB or near-IRB
        
        angle_norm = min((abs(angle) - 20) / 40, 1.0)
        conf = round(0.55 + 0.35 * angle_norm, 2)  # Higher base confidence
        if bullish_irb:
            conf = min(conf + 0.08, 0.95)
        if rsi_now > 45 and rsi_now < 55:  # Bonus for neutral RSI
            conf = min(conf + 0.05, 0.95)

        tp = price - tp_mult * atr_now
        sl = price + sl_mult * atr_now
        signals.append(Signal(
            symbol=symbol, direction="SELL",
            confidence=conf, entry_price=price,
            take_profit=tp, stop_loss=sl,
            reason=(f"OPT_SCALP SELL | EMA9∠{angle:.0f}° RSI={rsi_now:.0f} "
                    f"{'IRB' if bullish_irb else 'near-IRB'} "
                    f"ATR={atr_now:.2f} TP={tp_mult}x SL={sl_mult}x"),
        ))
    
    return signals


def hoffman_scalper_enhanced_signals(data: pd.DataFrame, symbol: str) -> List[Signal]:
    """Enhanced scalper with yesterday trend and support/resistance filters.
    
    Adds two extra guards to the rapid 20‑minute scalper:
      1. Yesterday's overall price movement must align with the signal direction.
      2. Price must be near a recent swing low (for BUY) or swing high (for SELL).
    These filters aim to reduce false entries while keeping the high‑frequency nature.
    """
    if len(data) < 150:
        return []
    
    # Core indicators (same as base scalper)
    o, h, l, c, v, _ema20, _angles, _atr_arr, _birb, _bulirb = _prepare_arrays(data)
    ema9 = _ema(c, 9)
    ema9_angles = _ema_slope_degrees(ema9, lookback=3)
    atr = _atr(h, l, c, ATR_PERIOD)
    idx = len(c) - 1
    if np.isnan(ema9[idx]) or np.isnan(atr[idx]) or atr[idx] == 0:
        return []
    
    angle = ema9_angles[idx]
    price = c[idx]
    atr_now = atr[idx]
    
    # IRB detection (same relaxed 55% as scalper)
    rng = abs(h[idx] - l[idx])
    body = abs(c[idx] - o[idx])
    irb_pct = 55
    if rng > 0:
        rv = body < (irb_pct / 100.0) * rng
    else:
        rv = False
    x = l[idx] + (irb_pct / 100.0) * rng
    y = h[idx] - (irb_pct / 100.0) * rng
    bearish_irb = rv and h[idx] > y and c[idx] < y and o[idx] < y
    bullish_irb = rv and l[idx] < x and c[idx] > x and o[idx] > x
    near_irb = body < 0.65 * rng if rng > 0 else False
    
    # Tight TP/SL
    tp_mult = 0.75
    sl_mult = 0.50
    
    # ----- Additional Filters -----
    # 1. Yesterday trend (approx 1 day = 96 bars for 15m)
    day_bars = 96
    yesterday_bullish = None
    if len(data) > day_bars:
        y_close = c[-day_bars]
        y_open = o[-day_bars]
        yesterday_bullish = y_close > y_open
    
    # 2. Recent swing high/low over last 50 bars
    swing_window = 50 if len(data) >= 50 else len(data)
    recent_high = np.max(h[-swing_window:])
    recent_low = np.min(l[-swing_window:])
    near_support = price <= recent_low * 1.005
    near_resistance = price >= recent_high * 0.995
    
    signals: List[Signal] = []
    
    # BUY scalp with extra checks
    if angle >= 15 and (bearish_irb or (near_irb and angle >= 25)):
        # Confidence scaling
        angle_norm = min((abs(angle) - 15) / 45, 1.0)
        conf = round(0.40 + 0.40 * angle_norm, 2)
        if bearish_irb:
            conf = min(conf + 0.10, 0.95)
        # Apply extra filters
        if yesterday_bullish is True and near_support:
            tp = price + tp_mult * atr_now
            sl = price - sl_mult * atr_now
            signals.append(Signal(
                symbol=symbol, direction="BUY",
                confidence=conf, entry_price=price,
                take_profit=tp, stop_loss=sl,
                reason=(f"SCALP_ENHANCED BUY | EMA9∠{angle:.0f}° "
                        f"{'IRB' if bearish_irb else 'near-IRB'} "
                        f"ATR={atr_now:.2f} TP={tp_mult}x SL={sl_mult}x"),
            ))
    
    # SELL scalp with extra checks
    if angle <= -15 and (bullish_irb or (near_irb and angle <= -25)):
        angle_norm = min((abs(angle) - 15) / 45, 1.0)
        conf = round(0.40 + 0.40 * angle_norm, 2)
        if bullish_irb:
            conf = min(conf + 0.10, 0.95)
        if yesterday_bullish is False and near_resistance:
            tp = price - tp_mult * atr_now
            sl = price + sl_mult * atr_now
            signals.append(Signal(
                symbol=symbol, direction="SELL",
                confidence=conf, entry_price=price,
                take_profit=tp, stop_loss=sl,
                reason=(f"SCALP_ENHANCED SELL | EMA9∠{angle:.0f}° "
                        f"{'IRB' if bullish_irb else 'near-IRB'} "
                        f"ATR={atr_now:.2f} TP={tp_mult}x SL={sl_mult}x"),
            ))
    
    return signals
    

VARIATIONS = [
    {
        "name": ADAPTIVE_ATR_NAME,
        "description": ADAPTIVE_ATR_DESCRIPTION,
        "generate_signals": hoffman_adaptive_atr_signals,
    },
    {
        "name": KALMAN_NAME,
        "description": KALMAN_DESCRIPTION,
        "generate_signals": hoffman_kalman_trend_signals,
    },
    {
        "name": TRAILING_ATR_NAME,
        "description": TRAILING_ATR_DESCRIPTION,
        "generate_signals": hoffman_trailing_atr_signals,
    },
    {
        "name": MOMENTUM_TP_NAME,
        "description": MOMENTUM_TP_DESCRIPTION,
        "generate_signals": hoffman_momentum_tp_signals,
    },
    {
        "name": KELLY_NAME,
        "description": KELLY_DESCRIPTION,
        "generate_signals": hoffman_kelly_sized_signals,
    },
    {
        "name": HTF_CONFLUENCE_NAME,
        "description": HTF_CONFLUENCE_DESCRIPTION,
        "generate_signals": hoffman_htf_confluence_signals,
    },
    {
        "name": RELAXED_45_NAME,
        "description": RELAXED_45_DESCRIPTION,
        "generate_signals": hoffman_45_degree_relaxed_signals,
    },
    {
        "name": SCALPER_NAME,
        "description": SCALPER_DESCRIPTION,
        "generate_signals": hoffman_scalper_optimized_signals,
    },
    {
        "name": SCALPER_ENHANCED_NAME,
        "description": SCALPER_ENHANCED_DESCRIPTION,
        "generate_signals": hoffman_scalper_enhanced_signals,
    },
    {
        "name": "hoffman_new_strategy",
        "description": "Hoffman New Strategy using EMA slope, ATR volatility rank, and Binance funding rate",
        "generate_signals": hoffman_new_strategy_signals,
    },
    {
        "name": RSI_SR_NAME,
        "description": RSI_SR_DESCRIPTION,
        "generate_signals": hoffman_rsi_support_resistance_signals,
    },
    {
        "name": PRICE_PRED_NAME,
        "description": PRICE_PRED_DESCRIPTION,
        "generate_signals": hoffman_price_momentum_prediction_signals,
    },
    {
        "name": CYCLIC_NAME,
        "description": CYCLIC_DESCRIPTION,
        "generate_signals": hoffman_cyclic_time_filter_signals,
    },
    {
        "name": ADX_NAME,
        "description": ADX_DESCRIPTION,
        "generate_signals": hoffman_adx_trend_strength_signals,
    },
]


# =====================================================================
# CLI Test
# =====================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Hoffman IRB Variations - 7 Baby Strategies")
    print("=" * 70)

    for var in VARIATIONS:
        print(f"\n  {var['name']}")
        print(f"    {var['description']}")
    print()

    try:
        import requests

        for sym in SYMBOLS:
            print(f"\n{'─' * 50}")
            print(f"  {sym}")
            print(f"{'─' * 50}")

            # Fetch 15min bars — 500 bars covers enough for 4H resampling
            url = (f"https://api.binance.com/api/v3/klines"
                   f"?symbol={sym}&interval=15m&limit=500")
            resp = requests.get(url, timeout=15)
            rows = resp.json()
            df = pd.DataFrame(rows, columns=[
                "open_time", "open", "high", "low", "close", "volume",
                "close_time", "qav", "trades", "tbbav", "tbqav", "ignore",
            ])
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)

            for var in VARIATIONS:
                fn = var["generate_signals"]
                sigs = fn(df, sym)
                if sigs:
                    for s in sigs:
                        print(f"    [{var['name']}] {s.direction} "
                              f"conf={s.confidence} entry={s.entry_price:.4f} "
                              f"tp={s.take_profit:.4f} sl={s.stop_loss:.4f}")
                        print(f"      {s.reason}")
                else:
                    print(f"    [{var['name']}] no signal")

    except Exception as e:
        print(f"  Test error: {e}")
        import traceback
        traceback.print_exc()
