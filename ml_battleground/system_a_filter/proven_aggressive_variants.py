"""
Proven Aggressive Variants — Higher-frequency mutations of battleground winners.
=================================================================================

These are RELAXED versions of the 4 proven strategies that generated the most P&L
in the battleground forward test. Each variant preserves the core edge logic but
widens the entry zone to trigger more frequently.

Original strategies and their track records:
  1. crypto_vwap_deviation_reversion  → +332% total P&L (best performer)
  2. drawdown_recovery_rsi_eth        → ETH 72.7% WR, +291%
  3. multi_period_rsi_confluence_eth   → ETH 64.3% WR, +200%
  4. multi_period_rsi_confluence_xrp   → XRP 83.3% WR, +157%

Mutations applied:
  - Relaxed thresholds (RSI, VWAP deviation, regime gates)
  - Added more symbols (proven strategies were symbol-limited)
  - Tighter TP targets (capture more frequent smaller wins)
  - Shorter hold periods
  - Added "fast" variants on 15m/1h alongside original 4h timeframe

IMPORTANT: These are SANDBOX tier by default. They must earn PROVEN status
through forward testing (50+ trades, WR > 50%).
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Optional

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import indicators as ind


def _base_signal(strategy: str, pair: str, signal_type: str, entry: float,
                 confidence: float, reason: str, **extra) -> dict:
    """Create a standardized signal dict."""
    sig = {
        "strategy": strategy,
        "symbol": pair,
        "signal_type": signal_type,
        "entry_price": round(entry, 8),
        "confidence": round(min(0.90, confidence), 4),
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "category": "crypto",
    }
    sig.update(extra)
    return sig


# =============================================================================
# VARIANT 1: VWAP Deviation Reversion — Aggressive
# Original: 2σ VWAP dev + HVN + Hurst < 0.60, +332% P&L
# Mutation: 1.5σ VWAP dev, lower HVN threshold, Hurst < 0.65, tighter TP
# =============================================================================

def vwap_deviation_reversion_aggressive(df: pd.DataFrame, pair: str) -> list[dict]:
    """
    Relaxed VWAP mean reversion: 1.5σ deviation (was 2.0σ).
    Uses rolling VWAP with volume profile proxy and Hurst regime gate.

    Key relaxations from original crypto_vwap_deviation_reversion:
      - VWAP std multiplier: 2.0 -> 1.5 (triggers ~2x more often)
      - HVN threshold: 1.2x -> 1.0x avg volume (more price levels qualify)
      - Hurst gate: 0.60 -> 0.65 (allows slightly trending regimes)
      - TP target: revert to VWAP or 1.5x ATR (was 2.0x ATR)
      - Min deviation: 0.8% -> 0.5% (smaller moves qualify)
    """
    if len(df) < 120:
        return []

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    # --- VWAP Calculation (48-bar rolling) ---
    lookback = 48
    typical_price = (high + low + close) / 3
    cum_tp_vol = (typical_price * volume).rolling(lookback).sum()
    cum_vol = volume.rolling(lookback).sum()
    vwap = cum_tp_vol / cum_vol

    if pd.isna(vwap.iloc[-1]) or vwap.iloc[-1] == 0:
        return []

    # Deviation bands (1.5σ instead of 2.0σ)
    deviation = typical_price - vwap
    std_dev = deviation.rolling(lookback).std()
    upper_band = vwap + 1.5 * std_dev
    lower_band = vwap - 1.5 * std_dev

    if pd.isna(upper_band.iloc[-1]) or pd.isna(lower_band.iloc[-1]):
        return []

    current_price = float(close.iloc[-1])
    current_vwap = float(vwap.iloc[-1])
    vwap_dev = (current_price - current_vwap) / current_vwap

    # Min deviation gate (0.5% instead of 0.8%)
    if abs(vwap_dev) < 0.005:
        return []

    # --- Hurst Exponent (regime gate, relaxed to 0.65) ---
    hurst = _compute_hurst_fast(close.values[-100:])
    if hurst >= 0.65:
        return []  # trending regime — skip

    # --- Volume Profile Proxy (simplified HVN check) ---
    # Check if current price zone has above-average volume concentration
    recent_vol = volume.tail(lookback)
    recent_close = close.tail(lookback)
    price_range = float(high.tail(lookback).max() - low.tail(lookback).min())
    if price_range <= 0:
        return []

    # Simple volume density at current price level
    price_proximity = (recent_close - current_price).abs() / price_range
    nearby_mask = price_proximity < 0.05  # within 5% of price range
    nearby_vol = float(recent_vol[nearby_mask].sum()) if nearby_mask.any() else 0
    total_vol = float(recent_vol.sum())
    vol_density = nearby_vol / (total_vol + 1e-10) * lookback / max(1, nearby_mask.sum())

    # Relaxed HVN: vol_density >= 1.0x average (was 1.2x)
    is_hvn = vol_density >= 1.0

    # --- ATR for risk management ---
    atr_val = ind.atr(high, low, close, 14)
    current_atr = float(atr_val.iloc[-1])
    if current_atr <= 0:
        return []

    signals = []

    # BUY: Price below lower band + at volume node + mean-reverting regime
    if (current_price < float(lower_band.iloc[-1])
            and vwap_dev < 0
            and is_hvn):
        dev_score = min(abs(vwap_dev) / 0.03, 1.0)
        hurst_score = (0.65 - hurst) / 0.65
        confidence = min(0.85, 0.55 + 0.15 * dev_score + 0.10 * hurst_score)

        # Tighter TP: revert to VWAP or 1.5x ATR (whichever is closer)
        tp_vwap = current_vwap
        tp_atr = current_price + 1.5 * current_atr
        tp = min(tp_vwap, tp_atr) if tp_vwap > current_price else tp_atr
        sl = current_price - 1.5 * current_atr

        # Ensure min R:R of 1.0
        if tp - current_price < current_price - sl:
            tp = current_price + (current_price - sl) * 1.0

        signals.append(_base_signal(
            "vwap_reversion_aggressive", pair, "BUY", current_price, confidence,
            f"VWAP reversion (aggressive): {vwap_dev:+.2%} from VWAP, "
            f"Hurst={hurst:.3f}, vol_density={vol_density:.2f}",
            atr_value=current_atr,
            vwap_deviation=round(vwap_dev, 4),
            hurst=round(hurst, 3),
            parent_strategy="crypto_vwap_deviation_reversion",
        ))

    # SELL: Price above upper band + at volume node + mean-reverting regime
    elif (current_price > float(upper_band.iloc[-1])
            and vwap_dev > 0
            and is_hvn):
        dev_score = min(abs(vwap_dev) / 0.03, 1.0)
        hurst_score = (0.65 - hurst) / 0.65
        confidence = min(0.85, 0.55 + 0.15 * dev_score + 0.10 * hurst_score)

        tp_vwap = current_vwap
        tp_atr = current_price - 1.5 * current_atr
        tp = max(tp_vwap, tp_atr) if tp_vwap < current_price else tp_atr
        sl = current_price + 1.5 * current_atr

        if current_price - tp < sl - current_price:
            tp = current_price - (sl - current_price) * 1.0

        signals.append(_base_signal(
            "vwap_reversion_aggressive", pair, "SELL", current_price, confidence,
            f"VWAP reversion (aggressive): {vwap_dev:+.2%} from VWAP, "
            f"Hurst={hurst:.3f}, vol_density={vol_density:.2f}",
            atr_value=current_atr,
            vwap_deviation=round(vwap_dev, 4),
            hurst=round(hurst, 3),
            parent_strategy="crypto_vwap_deviation_reversion",
        ))

    return signals


# =============================================================================
# VARIANT 2: Drawdown Recovery RSI — Multi-Symbol
# Original: ETH only, 72.7% WR, +291% P&L
# Mutation: Add BNB/SOL/AVAX/LINK, relaxed RSI threshold, add short timeframe
# =============================================================================

# Symbols where drawdown recovery RSI is allowed (ETH proven, others sandbox)
DRAWDOWN_RSI_SYMBOLS = ["ETHUSDT", "BNBUSDT", "SOLUSDT", "AVAXUSDT", "LINKUSDT",
                         "ADAUSDT", "NEARUSDT", "SUIUSDT", "APTUSDT"]

def drawdown_recovery_rsi_multi(df: pd.DataFrame, pair: str) -> list[dict]:
    """
    RSI oversold after significant drawdown — expanded to multiple symbols.

    Core logic (preserved from drawdown_recovery_rsi_eth):
      - Price has drawn down significantly from recent high (>10%)
      - RSI(14) enters oversold territory
      - Volume picks up (accumulation signal)

    Relaxations:
      - RSI threshold: 30 -> 35 (more entries)
      - Drawdown requirement: 15% -> 10% (catches smaller dips)
      - Volume requirement: 2.0x -> 1.5x average
      - Added recovery confirmation: price above lowest low of last 3 bars
      - Symbols: ETH only -> ETH + 8 alt L1s
    """
    if pair not in DRAWDOWN_RSI_SYMBOLS:
        return []

    if len(df) < 100:
        return []

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    current_price = float(close.iloc[-1])
    rsi14 = ind.rsi(close, 14)
    curr_rsi = float(rsi14.iloc[-1])

    if pd.isna(curr_rsi):
        return []

    # Relaxed RSI threshold: 35 instead of 30
    if curr_rsi >= 35:
        return []

    # Check drawdown from recent high (50-bar lookback)
    recent_high = float(high.tail(50).max())
    drawdown_pct = (recent_high - current_price) / recent_high * 100

    # Relaxed drawdown requirement: 10% instead of 15%
    if drawdown_pct < 10:
        return []

    # Volume confirmation: 1.5x average (relaxed from 2.0x)
    vol_avg = float(volume.rolling(20).mean().iloc[-1])
    curr_vol = float(volume.iloc[-1])
    vol_ratio = curr_vol / vol_avg if vol_avg > 0 else 1.0

    if vol_ratio < 1.5:
        return []

    # Recovery confirmation: price is above the lowest low of last 3 bars
    # (shows the bottom might be in)
    recent_low = float(low.tail(3).min())
    if current_price <= recent_low:
        return []

    atr_val = ind.atr(high, low, close, 14)
    current_atr = float(atr_val.iloc[-1])
    if current_atr <= 0:
        return []

    # Confidence scales with drawdown depth and RSI extremity
    dd_score = min((drawdown_pct - 10) / 20, 1.0)  # 30% dd = max
    rsi_score = (35 - curr_rsi) / 35
    vol_score = min((vol_ratio - 1.5) / 2.0, 0.3)
    confidence = min(0.85, 0.58 + 0.12 * dd_score + 0.10 * rsi_score + vol_score)

    # ETH-specific confidence boost (proven winner)
    if pair == "ETHUSDT":
        confidence = min(0.90, confidence + 0.05)

    # TP/SL: tighter TP for faster wins
    tp = current_price + 1.5 * current_atr
    sl = current_price - 1.5 * current_atr

    # Strategy name includes symbol for trust-tier tracking
    symbol_suffix = pair.replace("USDT", "").lower()
    strategy_name = f"drawdown_recovery_rsi_{symbol_suffix}_agg"

    return [_base_signal(
        strategy_name, pair, "BUY", current_price, confidence,
        f"Drawdown recovery (aggressive): {drawdown_pct:.1f}% DD from high, "
        f"RSI={curr_rsi:.1f}, vol={vol_ratio:.1f}x",
        atr_value=current_atr,
        rsi_value=round(curr_rsi, 2),
        drawdown_pct=round(drawdown_pct, 2),
        volume_ratio=round(vol_ratio, 2),
        parent_strategy="drawdown_recovery_rsi",
    )]


# =============================================================================
# VARIANT 3: Multi-Period RSI Confluence — Aggressive
# Original: RSI(14)<35 AND RSI(50)<40, ETH 64.3% WR, XRP 83.3% WR
# Mutation: RSI(14)<40, RSI(50)<45, more symbols, add RSI(7) for fast variant
# =============================================================================

# Symbols allowed for multi-period RSI (ETH/XRP proven, others sandbox)
MULTI_RSI_SYMBOLS = ["ETHUSDT", "XRPUSDT", "BTCUSDT", "BNBUSDT", "SOLUSDT",
                      "ADAUSDT", "AVAXUSDT", "LINKUSDT", "LTCUSDT", "DOTUSDT",
                      "NEARUSDT", "SUIUSDT", "APTUSDT"]

def multi_period_rsi_confluence_aggressive(df: pd.DataFrame, pair: str) -> list[dict]:
    """
    Dual RSI alignment for oversold entries — relaxed thresholds.

    Original: RSI(14) < 35 AND RSI(50) < 40 -> BUY
    Aggressive: RSI(14) < 40 AND RSI(50) < 45 -> BUY (wider entry zone)

    Additional filter: RSI(14) must be rising (not still falling into abyss)
    This compensates for the relaxed threshold by requiring momentum reversal.
    """
    if pair not in MULTI_RSI_SYMBOLS:
        return []

    if len(df) < 65:
        return []

    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    rsi14 = ind.rsi(close, 14)
    rsi50 = ind.rsi(close, 50)

    if len(rsi14) < 3 or pd.isna(rsi14.iloc[-1]) or pd.isna(rsi50.iloc[-1]):
        return []

    curr_rsi14 = float(rsi14.iloc[-1])
    prev_rsi14 = float(rsi14.iloc[-2])
    curr_rsi50 = float(rsi50.iloc[-1])

    # Relaxed thresholds
    if curr_rsi14 >= 40 or curr_rsi50 >= 45:
        return []

    # Momentum reversal confirmation: RSI(14) must be rising
    # (prevents catching falling knives with relaxed thresholds)
    if curr_rsi14 <= prev_rsi14:
        return []

    atr_val = ind.atr(high, low, close, 14)
    current_atr = float(atr_val.iloc[-1])
    current_price = float(close.iloc[-1])

    if current_atr <= 0:
        return []

    # Confidence scales with how deep the RSI readings are
    rsi14_depth = (40 - curr_rsi14) / 40
    rsi50_depth = (45 - curr_rsi50) / 45
    momentum_bonus = min((curr_rsi14 - prev_rsi14) / 5.0, 0.1)
    confidence = min(0.85, 0.58 + 0.12 * rsi14_depth + 0.10 * rsi50_depth + momentum_bonus)

    # Proven symbol boost
    if pair in ("ETHUSDT", "XRPUSDT"):
        confidence = min(0.90, confidence + 0.05)

    tp = current_price + 1.5 * current_atr
    sl = current_price - 1.5 * current_atr

    symbol_suffix = pair.replace("USDT", "").lower()
    strategy_name = f"multi_rsi_confluence_{symbol_suffix}_agg"

    return [_base_signal(
        strategy_name, pair, "BUY", current_price, confidence,
        f"Multi-RSI confluence (aggressive): RSI14={curr_rsi14:.1f} (rising), "
        f"RSI50={curr_rsi50:.1f}",
        atr_value=current_atr,
        rsi14_value=round(curr_rsi14, 2),
        rsi50_value=round(curr_rsi50, 2),
        parent_strategy="multi_period_rsi_confluence",
    )]


# =============================================================================
# VARIANT 4: Triple RSI Fast — 3-period RSI alignment on faster timeframes
# New strategy inspired by multi_period_rsi_confluence success
# Uses RSI(7), RSI(14), RSI(21) — faster periods for more frequent signals
# =============================================================================

def triple_rsi_fast(df: pd.DataFrame, pair: str) -> list[dict]:
    """
    Fast RSI triple confluence: RSI(7) < 30, RSI(14) < 40, RSI(21) < 45.
    All three must be oversold AND RSI(7) must be rising.

    Inspired by multi_period_rsi_confluence but uses faster periods
    to catch shorter-duration oversold conditions that the original misses.

    Designed for 1h timeframe (original was mainly 4h).
    """
    if len(df) < 50:
        return []

    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    rsi7 = ind.rsi(close, 7)
    rsi14 = ind.rsi(close, 14)
    rsi21 = ind.rsi(close, 21)

    if len(rsi7) < 3 or pd.isna(rsi7.iloc[-1]):
        return []

    curr_rsi7 = float(rsi7.iloc[-1])
    prev_rsi7 = float(rsi7.iloc[-2])
    curr_rsi14 = float(rsi14.iloc[-1])
    curr_rsi21 = float(rsi21.iloc[-1])

    # All three RSI periods must be oversold
    if curr_rsi7 >= 30 or curr_rsi14 >= 40 or curr_rsi21 >= 45:
        return []

    # RSI(7) must be turning up (momentum reversal)
    if curr_rsi7 <= prev_rsi7:
        return []

    atr_val = ind.atr(high, low, close, 14)
    current_atr = float(atr_val.iloc[-1])
    current_price = float(close.iloc[-1])

    if current_atr <= 0:
        return []

    # Volume confirmation (light: 1.2x average)
    volume = df["Volume"]
    vol_avg = float(volume.rolling(20).mean().iloc[-1])
    vol_ratio = float(volume.iloc[-1]) / vol_avg if vol_avg > 0 else 1.0

    rsi7_depth = (30 - curr_rsi7) / 30
    rsi14_depth = (40 - curr_rsi14) / 40
    reversal_strength = min((curr_rsi7 - prev_rsi7) / 3.0, 0.15)
    vol_bonus = min((vol_ratio - 1.0) / 3.0, 0.1) if vol_ratio > 1.0 else 0
    confidence = min(0.85, 0.55 + 0.12 * rsi7_depth + 0.08 * rsi14_depth
                     + reversal_strength + vol_bonus)

    # Tighter TP for fast variant
    tp = current_price + 1.2 * current_atr
    sl = current_price - 1.2 * current_atr

    return [_base_signal(
        "triple_rsi_fast", pair, "BUY", current_price, confidence,
        f"Triple RSI fast: R7={curr_rsi7:.1f} (rising +{curr_rsi7-prev_rsi7:.1f}), "
        f"R14={curr_rsi14:.1f}, R21={curr_rsi21:.1f}, vol={vol_ratio:.1f}x",
        atr_value=current_atr,
        rsi7_value=round(curr_rsi7, 2),
        rsi14_value=round(curr_rsi14, 2),
        rsi21_value=round(curr_rsi21, 2),
        volume_ratio=round(vol_ratio, 2),
        parent_strategy="multi_period_rsi_confluence",
    )]


# =============================================================================
# VARIANT 5: VWAP + RSI Combo — Combines the two best strategies
# Merges VWAP deviation with RSI oversold for higher-probability entries
# =============================================================================

def vwap_rsi_combo(df: pd.DataFrame, pair: str) -> list[dict]:
    """
    Combo of VWAP deviation + RSI oversold. Both conditions must be met,
    but each is individually relaxed since the combination provides confluence.

    Entry: Price below VWAP - 1.0σ (very relaxed) AND RSI(14) < 40
    This catches mean-reversion setups that either strategy alone would miss
    because each threshold is too strict on its own.
    """
    if len(df) < 100:
        return []

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    # RSI check first (cheapest computation)
    rsi14 = ind.rsi(close, 14)
    if pd.isna(rsi14.iloc[-1]):
        return []
    curr_rsi = float(rsi14.iloc[-1])
    if curr_rsi >= 40:
        return []

    # VWAP deviation check
    lookback = 48
    typical_price = (high + low + close) / 3
    cum_tp_vol = (typical_price * volume).rolling(lookback).sum()
    cum_vol = volume.rolling(lookback).sum()
    vwap = cum_tp_vol / cum_vol

    if pd.isna(vwap.iloc[-1]) or vwap.iloc[-1] == 0:
        return []

    current_price = float(close.iloc[-1])
    current_vwap = float(vwap.iloc[-1])
    vwap_dev = (current_price - current_vwap) / current_vwap

    # Very relaxed VWAP deviation: just 1.0σ below
    deviation = typical_price - vwap
    std_dev = deviation.rolling(lookback).std()
    lower_band = vwap - 1.0 * std_dev

    if pd.isna(lower_band.iloc[-1]):
        return []

    # Must be below 1σ VWAP band
    if current_price >= float(lower_band.iloc[-1]):
        return []

    atr_val = ind.atr(high, low, close, 14)
    current_atr = float(atr_val.iloc[-1])
    if current_atr <= 0:
        return []

    # Confidence from both signals agreeing
    rsi_depth = (40 - curr_rsi) / 40
    vwap_depth = min(abs(vwap_dev) / 0.02, 1.0)
    confidence = min(0.87, 0.60 + 0.12 * rsi_depth + 0.12 * vwap_depth)

    # TP: revert toward VWAP (realistic target)
    tp_vwap = current_vwap * 0.998  # slightly below VWAP (conservative)
    tp_atr = current_price + 1.5 * current_atr
    tp = min(tp_vwap, tp_atr) if tp_vwap > current_price else tp_atr
    sl = current_price - 1.2 * current_atr

    return [_base_signal(
        "vwap_rsi_combo", pair, "BUY", current_price, confidence,
        f"VWAP+RSI combo: VWAP dev={vwap_dev:+.2%}, RSI={curr_rsi:.1f}",
        atr_value=current_atr,
        vwap_deviation=round(vwap_dev, 4),
        rsi_value=round(curr_rsi, 2),
        parent_strategy="vwap_rsi_confluence",
    )]


# =============================================================================
# VARIANT 6: Drawdown Recovery RSI — Fast (shorter lookback)
# Same logic but looks at 20-bar drawdown instead of 50-bar
# Catches V-shaped recoveries on faster timeframes
# =============================================================================

def drawdown_recovery_rsi_fast(df: pd.DataFrame, pair: str) -> list[dict]:
    """
    Fast drawdown recovery: 20-bar lookback (instead of 50).
    Lower drawdown threshold: 5% (instead of 10%).

    Catches quick V-reversal setups that the standard variant misses
    because they don't develop a deep enough drawdown over 50 bars.
    """
    if len(df) < 50:
        return []

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    current_price = float(close.iloc[-1])
    rsi14 = ind.rsi(close, 14)
    curr_rsi = float(rsi14.iloc[-1])

    if pd.isna(curr_rsi) or curr_rsi >= 38:
        return []

    # Short-term drawdown from 20-bar high
    recent_high = float(high.tail(20).max())
    drawdown_pct = (recent_high - current_price) / recent_high * 100

    if drawdown_pct < 5:
        return []

    # Volume pickup
    vol_avg = float(volume.rolling(20).mean().iloc[-1])
    vol_ratio = float(volume.iloc[-1]) / vol_avg if vol_avg > 0 else 1.0
    if vol_ratio < 1.3:
        return []

    # Price must show initial recovery (above 3-bar low)
    recent_low = float(low.tail(3).min())
    if current_price <= recent_low:
        return []

    # RSI must be turning (not freefalling)
    prev_rsi = float(rsi14.iloc[-2])
    if curr_rsi < prev_rsi - 2:  # still falling hard
        return []

    atr_val = ind.atr(high, low, close, 14)
    current_atr = float(atr_val.iloc[-1])
    if current_atr <= 0:
        return []

    dd_score = min((drawdown_pct - 5) / 15, 1.0)
    rsi_score = (38 - curr_rsi) / 38
    confidence = min(0.82, 0.55 + 0.12 * dd_score + 0.10 * rsi_score)

    tp = current_price + 1.2 * current_atr
    sl = current_price - 1.3 * current_atr

    return [_base_signal(
        "drawdown_recovery_rsi_fast", pair, "BUY", current_price, confidence,
        f"Fast DD recovery: {drawdown_pct:.1f}% DD (20-bar), "
        f"RSI={curr_rsi:.1f}, vol={vol_ratio:.1f}x",
        atr_value=current_atr,
        rsi_value=round(curr_rsi, 2),
        drawdown_pct=round(drawdown_pct, 2),
        volume_ratio=round(vol_ratio, 2),
        parent_strategy="drawdown_recovery_rsi",
    )]


# =============================================================================
# Helper: Fast Hurst Exponent
# =============================================================================

def _compute_hurst_fast(prices: np.ndarray) -> float:
    """
    Fast Hurst exponent via R/S analysis.
    H < 0.5 → Mean-reverting (target regime)
    H = 0.5 → Random walk
    H > 0.5 → Trending
    """
    if len(prices) < 20:
        return 0.5

    try:
        returns = np.diff(np.log(prices))
        n = len(returns)
        if n < 10:
            return 0.5

        sizes = []
        rs_values = []

        for k in range(2, min(8, n // 4)):
            size = n // k
            if size < 4:
                continue

            n_sub = n // size
            if n_sub < 1:
                continue

            rs_list = []
            for i in range(n_sub):
                sub = returns[i * size:(i + 1) * size]
                mean_sub = np.mean(sub)
                deviate = np.cumsum(sub - mean_sub)
                r = np.max(deviate) - np.min(deviate)
                s = np.std(sub, ddof=1)
                if s > 0:
                    rs_list.append(r / s)

            if rs_list:
                sizes.append(size)
                rs_values.append(np.mean(rs_list))

        if len(sizes) < 3:
            return 0.5

        log_sizes = np.log(sizes)
        log_rs = np.log(rs_values)
        x_mean = np.mean(log_sizes)
        y_mean = np.mean(log_rs)
        num = np.sum((log_sizes - x_mean) * (log_rs - y_mean))
        den = np.sum((log_sizes - x_mean) ** 2)
        if den == 0:
            return 0.5

        hurst = num / den
        return float(np.clip(hurst, 0.0, 1.0))
    except Exception:
        return 0.5


# =============================================================================
# Aggregator — Run all aggressive variants
# =============================================================================

ALL_AGGRESSIVE_VARIANTS = [
    vwap_deviation_reversion_aggressive,
    drawdown_recovery_rsi_multi,
    multi_period_rsi_confluence_aggressive,
    triple_rsi_fast,
    vwap_rsi_combo,
    drawdown_recovery_rsi_fast,
]


def run_all_aggressive_variants(df: pd.DataFrame, pair: str, interval: str = "1h") -> list[dict]:
    """Run all 6 aggressive variant strategies on a single pair's OHLCV DataFrame."""
    if len(df) < 50:
        return []

    signals = []
    for strategy_fn in ALL_AGGRESSIVE_VARIANTS:
        try:
            sigs = strategy_fn(df, pair)
            if sigs:
                for s in sigs:
                    s["timeframe"] = interval
                    s["variant_type"] = "aggressive"
                signals.extend(sigs)
        except Exception as e:
            print(f"    [!] {pair} {strategy_fn.__name__} error: {e}")

    return signals
