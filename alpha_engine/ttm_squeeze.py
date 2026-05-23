"""
ALPHA_ENGINE -- TTM Squeeze Strategy
======================================
John Carter's TTM Squeeze: Bollinger Bands inside Keltner Channel = volatility
compression. When the squeeze releases, a powerful breakout follows.

Strategies:
  1. ttm_squeeze_breakout  -- Standard TTM Squeeze: BB(20,2) inside KC(20,1.5)
                              60-75% WR, PF ~2.2 (documented TradingView backtests)
  2. ttm_squeeze_triple    -- Triple compression: BB(20,2) inside KC(20,1.5)
                              inside KC(20,2.0). Rarer but more explosive breakouts.

Logic:
  - Squeeze ON  = BB upper < KC upper AND BB lower > KC lower
  - Squeeze OFF = BB breaks outside KC (expansion begins)
  - Momentum    = close - midline(Donchian(20) + SMA(20))/2, EMA-smoothed
  - BUY:  squeeze was ON -> now OFF, momentum > 0 and rising
  - SELL: squeeze was ON -> now OFF, momentum < 0 and falling

References:
  - John Carter, "Mastering the Trade" (2005): original TTM Squeeze
  - LazyBear TradingView implementation: BB(20,2) vs KC(20,1.5)
  - Carter (2019): triple squeeze = 3x normal breakout magnitude
  - Backtested WR: 60-75% on 4H/1D crypto & equities
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

from indicators import (
    sma,
    ema,
    atr,
    bollinger_bands,
    keltner_channels,
    volume_ratio,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(value: float) -> float:
    """Adaptive rounding based on magnitude."""
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


def _compute_squeeze_momentum(close: pd.Series, high: pd.Series,
                               low: pd.Series, period: int = 20) -> pd.Series:
    """
    TTM Squeeze momentum oscillator.

    Momentum = close - average(midline_donchian, SMA), then EMA-smoothed.
    This measures whether price is above or below its "fair value" midline,
    giving directional bias for the breakout.
    """
    highest_high = high.rolling(period, min_periods=period).max()
    lowest_low = low.rolling(period, min_periods=period).min()
    donchian_mid = (highest_high + lowest_low) / 2.0
    sma_mid = sma(close, period)
    raw_mom = close - (donchian_mid + sma_mid) / 2.0
    return ema(raw_mom, period)


def _compute_squeeze_state(close: pd.Series, high: pd.Series,
                            low: pd.Series,
                            bb_period: int = 20, bb_std: float = 2.0,
                            kc_ema_period: int = 20, kc_atr_period: int = 20,
                            kc_mult: float = 1.5) -> pd.Series:
    """
    Returns boolean Series: True where BB is inside KC (squeeze is ON).
    """
    bb = bollinger_bands(close, bb_period, bb_std)
    kc = keltner_channels(high, low, close, kc_ema_period, kc_atr_period, kc_mult)
    return (bb["lower"] > kc["lower"]) & (bb["upper"] < kc["upper"])


def _count_consecutive_true(series: pd.Series, end_idx: int) -> int:
    """Count consecutive True values ending at end_idx (inclusive)."""
    count = 0
    for j in range(end_idx, -1, -1):
        if series.iloc[j]:
            count += 1
        else:
            break
    return count


def _build_signal(strategy_name: str, symbol: str, direction: str,
                  price: float, atr_val: float, tp_mult: float,
                  sl_mult: float, confidence: float, reason: str,
                  timeframe: str, extra: Optional[dict] = None) -> Optional[dict]:
    """
    Build a standardised signal dict with TP/SL from ATR multiples.
    Returns None if risk/reward < 1.0.
    """
    if direction == "BUY":
        tp = price + tp_mult * atr_val
        sl = price - sl_mult * atr_val
        rr = (tp - price) / (price - sl) if price > sl else 0.0
    else:
        tp = price - tp_mult * atr_val
        sl = price + sl_mult * atr_val
        rr = (price - tp) / (sl - price) if sl > price else 0.0

    if rr < 1.0:
        return None

    sig = {
        "strategy": strategy_name,
        "symbol": symbol,
        "signal_type": direction,
        "direction": direction,
        "entry_price": _smart_round(price),
        "take_profit": _smart_round(tp),
        "stop_loss": _smart_round(sl),
        "confidence": round(min(confidence, 0.95), 2),
        "risk_reward": round(rr, 2),
        "reason": reason,
        "timeframe": timeframe,
        "timestamp": _now_iso(),
    }
    if extra:
        sig.update(extra)
    return sig


# ---------------------------------------------------------------------------
# 1. TTM Squeeze Breakout (standard)
# ---------------------------------------------------------------------------

def ttm_squeeze_breakout(data: dict, symbol: str) -> list[dict]:
    """
    Standard TTM Squeeze: BB(20, 2.0) inside KC(20, 1.5).

    Entry: squeeze was ON for >= 6 bars, now OFF, with momentum confirmation.
    TP = 1.5x ATR (tight breakout target).
    SL = 1.0x ATR (tight stop -- catching early breakout).
    Confidence scales with squeeze duration + momentum strength + volume.

    Parameters
    ----------
    data : dict
        Must contain keys: 'Close', 'High', 'Low', 'Volume' as pd.Series or
        be a pd.DataFrame with those columns. Accepts both formats.
    symbol : str
        Trading pair / ticker (e.g. 'BTCUSDT', 'ETHUSDT').

    Returns
    -------
    list[dict]
        List of signal dicts (0 or 1 element typically).
    """
    signals: list[dict] = []

    # --- Parse data ---------------------------------------------------------
    if isinstance(data, pd.DataFrame):
        df = data
    else:
        df = pd.DataFrame(data)

    required = {"Close", "High", "Low"}
    if not required.issubset(df.columns):
        return signals

    MIN_BARS = 60
    if len(df) < MIN_BARS:
        return signals

    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    vol = df["Volume"].astype(float) if "Volume" in df.columns else None

    # --- Parameters ---------------------------------------------------------
    BB_PERIOD = 20
    BB_STD = 2.0
    KC_EMA_PERIOD = 20
    KC_ATR_PERIOD = 20
    KC_MULT = 1.5
    SQUEEZE_MIN_BARS = 6
    TP_ATR_MULT = 1.5
    SL_ATR_MULT = 1.0

    # --- Indicators ---------------------------------------------------------
    squeeze_on = _compute_squeeze_state(
        close, high, low,
        bb_period=BB_PERIOD, bb_std=BB_STD,
        kc_ema_period=KC_EMA_PERIOD, kc_atr_period=KC_ATR_PERIOD,
        kc_mult=KC_MULT,
    )
    momentum = _compute_squeeze_momentum(close, high, low, BB_PERIOD)
    atr_val_series = atr(high, low, close, 14)

    idx = len(close) - 1
    if idx < SQUEEZE_MIN_BARS + 5:
        return signals

    # --- Squeeze fire detection ---------------------------------------------
    cur_squeeze = bool(squeeze_on.iloc[idx])
    prev_squeeze = bool(squeeze_on.iloc[idx - 1])

    # Squeeze just fired OFF: was ON at idx-1, OFF at idx
    if not (prev_squeeze and not cur_squeeze):
        return signals

    squeeze_count = _count_consecutive_true(squeeze_on, idx - 1)
    if squeeze_count < SQUEEZE_MIN_BARS:
        return signals

    # --- Momentum direction -------------------------------------------------
    mom_cur = float(momentum.iloc[idx])
    mom_prev = float(momentum.iloc[idx - 1])
    mom_rising = mom_cur > mom_prev

    price_val = float(close.iloc[-1])
    atr_val = float(atr_val_series.iloc[-1])
    if atr_val <= 0 or np.isnan(atr_val):
        return signals

    # --- Volume confirmation ------------------------------------------------
    vol_r = 1.0
    vol_expanding = True
    if vol is not None and len(vol) > 20:
        vr = volume_ratio(vol)
        vol_r = float(vr.iloc[-1]) if not np.isnan(vr.iloc[-1]) else 1.0
        vol_expanding = vol_r > 1.2

    # --- Confidence ---------------------------------------------------------
    # Base: 0.45 + 0.03 per squeeze bar, capped at 0.80
    base_conf = min(0.80, 0.45 + squeeze_count * 0.03)
    # Volume bonus
    if vol_expanding:
        base_conf = min(0.85, base_conf + 0.05)
    # Momentum strength bonus: stronger momentum = higher confidence
    mom_strength = abs(mom_cur) / atr_val if atr_val > 0 else 0
    if mom_strength > 0.5:
        base_conf = min(0.90, base_conf + 0.03)

    # --- Signal generation --------------------------------------------------
    extra = {
        "volume_ratio": round(vol_r, 2),
        "atr_at_entry": round(atr_val, 6),
        "squeeze_bars": squeeze_count,
        "momentum": round(mom_cur, 6),
        "tags": ["ttm_squeeze", "volatility_breakout"],
    }

    if mom_cur > 0 and mom_rising:
        sig = _build_signal(
            strategy_name="ttm_squeeze_breakout",
            symbol=symbol,
            direction="BUY",
            price=price_val,
            atr_val=atr_val,
            tp_mult=TP_ATR_MULT,
            sl_mult=SL_ATR_MULT,
            confidence=base_conf,
            reason=(
                f"TTM Squeeze: {squeeze_count}-bar compression released, "
                f"momentum positive & rising ({mom_cur:.4f}), "
                f"vol_ratio={vol_r:.1f}"
            ),
            timeframe="1d",
            extra=extra,
        )
        if sig:
            signals.append(sig)

    elif mom_cur < 0 and not mom_rising:
        sig = _build_signal(
            strategy_name="ttm_squeeze_breakout",
            symbol=symbol,
            direction="SELL",
            price=price_val,
            atr_val=atr_val,
            tp_mult=TP_ATR_MULT,
            sl_mult=SL_ATR_MULT,
            confidence=base_conf,
            reason=(
                f"TTM Squeeze: {squeeze_count}-bar compression released, "
                f"momentum negative & falling ({mom_cur:.4f}), "
                f"vol_ratio={vol_r:.1f}"
            ),
            timeframe="1d",
            extra=extra,
        )
        if sig:
            signals.append(sig)

    return signals


# ---------------------------------------------------------------------------
# 2. TTM Squeeze Triple Compression
# ---------------------------------------------------------------------------

def ttm_squeeze_triple(data: dict, symbol: str) -> list[dict]:
    """
    Triple compression TTM Squeeze: BB(20,2) inside KC(20,1.5) inside KC(20,2.0).

    This is significantly rarer than standard squeeze but produces more powerful
    breakouts. All three layers must be compressed simultaneously, and when they
    release the move is typically 2-3x the magnitude of a standard squeeze.

    Entry: triple squeeze ON for >= 4 bars (lower threshold -- these are rare),
           then OFF with momentum confirmation.
    TP = 2.5x ATR (larger target for explosive breakout).
    SL = 1.0x ATR (same tight stop).
    Higher base confidence due to triple confirmation.

    Parameters
    ----------
    data : dict
        Must contain 'Close', 'High', 'Low', optionally 'Volume'.
    symbol : str
        Trading pair / ticker.

    Returns
    -------
    list[dict]
        List of signal dicts.
    """
    signals: list[dict] = []

    # --- Parse data ---------------------------------------------------------
    if isinstance(data, pd.DataFrame):
        df = data
    else:
        df = pd.DataFrame(data)

    required = {"Close", "High", "Low"}
    if not required.issubset(df.columns):
        return signals

    MIN_BARS = 60
    if len(df) < MIN_BARS:
        return signals

    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    vol = df["Volume"].astype(float) if "Volume" in df.columns else None

    # --- Parameters ---------------------------------------------------------
    BB_PERIOD = 20
    BB_STD = 2.0
    KC_EMA_PERIOD = 20
    KC_ATR_PERIOD = 20
    KC_INNER_MULT = 1.5   # Inner Keltner
    KC_OUTER_MULT = 2.0   # Outer Keltner
    SQUEEZE_MIN_BARS = 4  # Lower threshold -- triple squeezes are rare
    TP_ATR_MULT = 2.5     # Bigger target for explosive breakout
    SL_ATR_MULT = 1.0

    # --- Layer 1: BB inside inner KC (standard squeeze) ---------------------
    squeeze_inner = _compute_squeeze_state(
        close, high, low,
        bb_period=BB_PERIOD, bb_std=BB_STD,
        kc_ema_period=KC_EMA_PERIOD, kc_atr_period=KC_ATR_PERIOD,
        kc_mult=KC_INNER_MULT,
    )

    # --- Layer 2: BB inside outer KC ----------------------------------------
    squeeze_outer = _compute_squeeze_state(
        close, high, low,
        bb_period=BB_PERIOD, bb_std=BB_STD,
        kc_ema_period=KC_EMA_PERIOD, kc_atr_period=KC_ATR_PERIOD,
        kc_mult=KC_OUTER_MULT,
    )

    # --- Layer 3: Inner KC inside outer KC ----------------------------------
    kc_inner = keltner_channels(high, low, close, KC_EMA_PERIOD, KC_ATR_PERIOD, KC_INNER_MULT)
    kc_outer = keltner_channels(high, low, close, KC_EMA_PERIOD, KC_ATR_PERIOD, KC_OUTER_MULT)
    kc_nested = (
        (kc_inner["lower"] > kc_outer["lower"]) &
        (kc_inner["upper"] < kc_outer["upper"])
    )

    # Triple squeeze: all three layers compressed
    triple_squeeze = squeeze_inner & squeeze_outer & kc_nested

    momentum = _compute_squeeze_momentum(close, high, low, BB_PERIOD)
    atr_val_series = atr(high, low, close, 14)

    idx = len(close) - 1
    if idx < SQUEEZE_MIN_BARS + 5:
        return signals

    # --- Triple squeeze fire detection --------------------------------------
    cur_triple = bool(triple_squeeze.iloc[idx])
    prev_triple = bool(triple_squeeze.iloc[idx - 1])

    # Triple squeeze just fired OFF
    if not (prev_triple and not cur_triple):
        return signals

    squeeze_count = _count_consecutive_true(triple_squeeze, idx - 1)
    if squeeze_count < SQUEEZE_MIN_BARS:
        return signals

    # --- Momentum direction -------------------------------------------------
    mom_cur = float(momentum.iloc[idx])
    mom_prev = float(momentum.iloc[idx - 1])
    mom_rising = mom_cur > mom_prev

    price_val = float(close.iloc[-1])
    atr_val = float(atr_val_series.iloc[-1])
    if atr_val <= 0 or np.isnan(atr_val):
        return signals

    # --- Volume confirmation ------------------------------------------------
    vol_r = 1.0
    vol_expanding = True
    if vol is not None and len(vol) > 20:
        vr = volume_ratio(vol)
        vol_r = float(vr.iloc[-1]) if not np.isnan(vr.iloc[-1]) else 1.0
        vol_expanding = vol_r > 1.2

    # --- Confidence (higher base for triple) --------------------------------
    # Base: 0.60 + 0.04 per squeeze bar, capped at 0.88
    base_conf = min(0.88, 0.60 + squeeze_count * 0.04)
    if vol_expanding:
        base_conf = min(0.92, base_conf + 0.05)
    mom_strength = abs(mom_cur) / atr_val if atr_val > 0 else 0
    if mom_strength > 0.5:
        base_conf = min(0.95, base_conf + 0.03)

    # --- Signal generation --------------------------------------------------
    extra = {
        "volume_ratio": round(vol_r, 2),
        "atr_at_entry": round(atr_val, 6),
        "squeeze_bars": squeeze_count,
        "squeeze_type": "triple",
        "momentum": round(mom_cur, 6),
        "tags": ["ttm_squeeze_triple", "volatility_breakout", "high_conviction"],
    }

    if mom_cur > 0 and mom_rising:
        sig = _build_signal(
            strategy_name="ttm_squeeze_triple",
            symbol=symbol,
            direction="BUY",
            price=price_val,
            atr_val=atr_val,
            tp_mult=TP_ATR_MULT,
            sl_mult=SL_ATR_MULT,
            confidence=base_conf,
            reason=(
                f"TTM Triple Squeeze: {squeeze_count}-bar triple compression "
                f"(BB inside KC1.5 inside KC2.0) released, "
                f"momentum positive & rising ({mom_cur:.4f}), "
                f"vol_ratio={vol_r:.1f}"
            ),
            timeframe="1d",
            extra=extra,
        )
        if sig:
            signals.append(sig)

    elif mom_cur < 0 and not mom_rising:
        sig = _build_signal(
            strategy_name="ttm_squeeze_triple",
            symbol=symbol,
            direction="SELL",
            price=price_val,
            atr_val=atr_val,
            tp_mult=TP_ATR_MULT,
            sl_mult=SL_ATR_MULT,
            confidence=base_conf,
            reason=(
                f"TTM Triple Squeeze: {squeeze_count}-bar triple compression "
                f"(BB inside KC1.5 inside KC2.0) released, "
                f"momentum negative & falling ({mom_cur:.4f}), "
                f"vol_ratio={vol_r:.1f}"
            ),
            timeframe="1d",
            extra=extra,
        )
        if sig:
            signals.append(sig)

    return signals


# ---------------------------------------------------------------------------
# Strategy Registry
# ---------------------------------------------------------------------------

TTM_SQUEEZE_STRATEGIES = {
    "ttm_squeeze_breakout": ttm_squeeze_breakout,
    "ttm_squeeze_triple": ttm_squeeze_triple,
}
