#!/usr/bin/env python3
"""
Antigravity Mutations V2 — Creative Edge Exploiters
====================================================

Created: 2026-03-14 by Antigravity AI
Context: V1 mutations failed (4/5) because of over-complex multi-condition
         filters. V2 takes the OPPOSITE approach: maximum 2-3 conditions,
         genuinely novel angles, and intentional simplicity.

Lessons from V1 failure analysis:
  - Multi-condition filters (4-5 conditions) kill all trades
  - Regime detection via ATR percentile is lagging
  - Requiring dual-anchor agreement is too restrictive
  - ag_mtf_aligned worked BECAUSE it was simpler than the others
  - genesis_momentum_blend worked because of momentum scoring, not complexity

V2 Design Philosophy:
  - Each mutation has MAX 3 entry conditions
  - Each exploits a DIFFERENT edge (cross-asset lag, compression energy, momentum persistence)
  - No oscillator thresholds (RSI guards removed — they killed V1 edge)
  - Wider symbol universe — don't restrict to hardcoded lists

Mutations:
  AG6: tidal_force       — BTC leads, alts lag. Trade the lag.
  AG7: gravity_well      — Bollinger compression extreme + volume ignition
  AG8: momentum_cascade  — 3-speed momentum alignment (3/8/21 bar returns)

Interface: same as V1 — Input: dict[symbol -> DataFrame], Output: list[dict]
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Optional


# ── Inline indicators ──────────────────────────────────────────────────

def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def _bb_width(close: pd.Series, period: int = 20) -> pd.Series:
    """Bollinger Band width as percentage of SMA."""
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    return (2 * std / sma) * 100  # width as % of price


# ── Helpers ─────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _smart_round(value: float) -> float:
    if value is None or not np.isfinite(value):
        return 0.0
    if abs(value) >= 1000:
        return round(value, 2)
    if abs(value) >= 1:
        return round(value, 4)
    if abs(value) >= 0.01:
        return round(value, 6)
    return round(value, 8)

def _base_signal(strategy: str, symbol: str, signal_type: str, entry: float,
                 tp: float, sl: float, confidence: float, reason: str,
                 **extra) -> dict:
    """Create standardized signal dict."""
    rr = 0.0
    if signal_type == "BUY" and entry > sl:
        rr = (tp - entry) / (entry - sl)
    elif signal_type == "SELL" and sl > entry:
        rr = (entry - tp) / (sl - entry)

    sig = {
        "strategy": strategy,
        "symbol": symbol,
        "signal_type": signal_type,
        "entry_price": _smart_round(entry),
        "take_profit": _smart_round(tp),
        "stop_loss": _smart_round(sl),
        "confidence": round(min(0.85, confidence), 4),
        "risk_reward": round(max(0, rr), 2),
        "reason": reason,
        "timestamp": _now_iso(),
        "category": "crypto",
        "trust_tier": "SANDBOX",
        "trust_weight": 0.3,
        "mutation_source": "antigravity_v2_creative",
    }
    sig.update(extra)
    return sig


# ═══════════════════════════════════════════════════════════════════════════
# AG6: TIDAL FORCE — BTC-Leading Altcoin Lag Exploit
# ═══════════════════════════════════════════════════════════════════════════
#
# Edge: BTC moves first, altcoins follow with a 1-4 bar lag.
# When BTC surges (>1% in 3 bars), we look for altcoins that
# HAVEN'T moved yet and trade them BEFORE they catch up.
#
# Only 2 conditions:
#   1. BTC 3-bar momentum > threshold (BTC is moving)
#   2. Altcoin 3-bar momentum < half of BTC's (alt hasn't caught up)
#
# This is a cross-asset information edge — uses BTC as a leading
# indicator for the entire market. Ultra-simple, data-driven.
#
# Why this might work:
#   - Market structure: BTC is the bellwether, alts lag by hours
#   - Institutional money hits BTC first (most liquid), then rotates
#   - Retail follows BTC but is slower to buy alts
# ═══════════════════════════════════════════════════════════════════════════

TIDAL_TRADE_SYMBOLS = [
    "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
    "NEARUSDT", "APTUSDT", "SUIUSDT", "INJUSDT",
    "FETUSDT", "SEIUSDT", "JUPUSDT", "TAOUSDT",
    "ARBUSDT", "OPUSDT", "ATOMUSDT",
]

# Momentum thresholds (% change over 3 bars)
BTC_MOMENTUM_THRESHOLD = 0.012     # BTC must move > 1.2% in 3 bars
ALT_LAG_RATIO = 0.40               # Alt must have moved < 40% of BTC's move


def tidal_force(data: dict) -> list[dict]:
    """
    AG6: BTC leads, alts lag. Trade the lag.

    Entry:
      1. BTC 3-bar return > 1.2% (BTC is surging)
      2. Alt 3-bar return < 40% of BTC's return (alt hasn't caught up)

    Direction: Same as BTC's move (if BTC is going up, buy the alt)
    TP: 2x ATR (expect alt to catch up to BTC's move)
    SL: 1.2x ATR (tight stop — if alt doesn't follow, exit fast)

    Expected: Medium frequency, should work well on mid-caps
    """
    signals = []

    # Step 1: Check BTC momentum
    btc_df = data.get("BTCUSDT")
    if btc_df is None or len(btc_df) < 20:
        return signals

    btc_close = btc_df["Close"]
    btc_3bar_return = (float(btc_close.iloc[-1]) - float(btc_close.iloc[-4])) / float(btc_close.iloc[-4])

    # BTC must be moving significantly
    if abs(btc_3bar_return) < BTC_MOMENTUM_THRESHOLD:
        return signals

    btc_direction = "BUY" if btc_3bar_return > 0 else "SELL"

    # Step 2: Find lagging altcoins
    for symbol in TIDAL_TRADE_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 20:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # Alt 3-bar return
        alt_3bar_return = (current - float(close.iloc[-4])) / float(close.iloc[-4])

        # Check if alt is lagging: moved less than ALT_LAG_RATIO of BTC
        if btc_direction == "BUY":
            if alt_3bar_return > btc_3bar_return * ALT_LAG_RATIO:
                continue  # Alt already caught up
            if alt_3bar_return < -0.01:
                continue  # Alt is going OPPOSITE direction — skip (decoupled)
        else:  # BTC bearish
            if alt_3bar_return < btc_3bar_return * ALT_LAG_RATIO:
                continue  # Alt already caught up
            if alt_3bar_return > 0.01:
                continue  # Alt going opposite

        atr_val = float(_atr(high, low, close, 14).iloc[-1])
        if pd.isna(atr_val) or atr_val <= 0:
            continue

        # Lag magnitude: how far behind is the alt?
        lag_magnitude = abs(btc_3bar_return) - abs(alt_3bar_return)

        if btc_direction == "BUY":
            tp = current + 2.0 * atr_val
            sl = current - 1.2 * atr_val
        else:
            tp = current - 2.0 * atr_val
            sl = current + 1.2 * atr_val

        # Confidence: bigger BTC move + bigger alt lag = higher confidence
        conf = min(0.82, 0.55 + abs(btc_3bar_return) * 5 + lag_magnitude * 8)

        signals.append(_base_signal(
            "ag_tidal_force_mut", symbol, btc_direction, current, tp, sl, conf,
            f"AG6 Tidal Force: BTC {btc_3bar_return:+.2%} (3-bar), "
            f"{symbol} only {alt_3bar_return:+.2%} — lag={lag_magnitude:.2%}, "
            f"expecting alt to catch up to BTC direction",
            parent_system="battleground",
            mutation_type="cross_asset_lag",
            btc_momentum=round(btc_3bar_return * 100, 3),
            alt_momentum=round(alt_3bar_return * 100, 3),
            lag_pct=round(lag_magnitude * 100, 3),
            timeframe="1h",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# AG7: GRAVITY WELL — Compression Breakout with Volume Ignition
# ═══════════════════════════════════════════════════════════════════════════
#
# Edge: When Bollinger Band width hits a 20-bar minimum (extreme
# compression), the price is coiled like a spring. When volume
# then spikes above 1.3x average, the spring releases.
#
# Only 3 conditions:
#   1. BB width at or near 20-bar minimum (compression)
#   2. Current volume > 1.3x 20-bar average (ignition)
#   3. Direction from close vs BB mid (above mid = BUY, below = SELL)
#
# Key difference from V1 Keltner approach:
#   - V1 required Keltner expansion ALREADY happening (lagging)
#   - V2 catches the compression-to-breakout TRANSITION (leading)
#   - Volume ignition confirms the breakout is real, not a fake-out
#
# Why this might work:
#   - Compression precedes expansion (Bollinger's own research)
#   - Volume validates: fake breakouts happen on low volume
#   - Works on any asset — not symbol-specific
# ═══════════════════════════════════════════════════════════════════════════

GRAVITY_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
    "NEARUSDT", "APTUSDT", "SUIUSDT", "INJUSDT",
    "FETUSDT", "SEIUSDT", "JUPUSDT", "TAOUSDT",
    "ARBUSDT", "OPUSDT", "ATOMUSDT", "ICPUSDT",
    "DOGEUSDT", "FILUSDT", "UNIUSDT", "AAVEUSDT",
]

BB_COMPRESSION_LOOKBACK = 20   # bars to check for BB width minimum
VOLUME_IGNITION_MULT = 1.3    # volume must be > 1.3x 20-bar avg


def gravity_well(data: dict) -> list[dict]:
    """
    AG7: Bollinger compression extreme + volume ignition = explosive breakout.

    Entry:
      1. BB width at 20-bar minimum (or within 5% of minimum)
      2. Current volume > 1.3x of 20-bar average volume
      3. Close > BB mid → BUY; Close < BB mid → SELL

    TP: 2.5x ATR (expecting explosive move after compression)
    SL: 1.0x ATR (tight — if it doesn't explode, it's a fake-out)

    Expected: Low-medium frequency, high win rate when signal fires
    """
    signals = []

    for symbol in GRAVITY_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 40:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # 1. Bollinger Band compression
        bb_w = _bb_width(close, 20)
        if bb_w.isna().iloc[-1]:
            continue

        current_bw = float(bb_w.iloc[-1])
        recent_bw = bb_w.iloc[-BB_COMPRESSION_LOOKBACK:]
        min_bw = float(recent_bw.min())

        if min_bw <= 0:
            continue

        # Is current width at or near the minimum? (within 10%)
        if current_bw > min_bw * 1.10:
            continue  # Not compressed enough

        # 2. Volume ignition
        vol_avg = float(volume.rolling(20).mean().iloc[-1])
        if vol_avg <= 0:
            continue
        vol_ratio = float(volume.iloc[-1]) / vol_avg

        if vol_ratio < VOLUME_IGNITION_MULT:
            continue  # No volume ignition

        # 3. Direction from BB midline
        sma_20 = float(close.rolling(20).mean().iloc[-1])
        if pd.isna(sma_20) or sma_20 <= 0:
            continue

        if current > sma_20:
            direction = "BUY"
        elif current < sma_20:
            direction = "SELL"
        else:
            continue  # Too close to midline

        atr_val = float(_atr(high, low, close, 14).iloc[-1])
        if pd.isna(atr_val) or atr_val <= 0:
            continue

        # Compression ratio: how tight is the squeeze?
        compression_ratio = min_bw / float(bb_w.rolling(50).mean().iloc[-1]) if not pd.isna(bb_w.rolling(50).mean().iloc[-1]) and float(bb_w.rolling(50).mean().iloc[-1]) > 0 else 1.0

        if direction == "BUY":
            tp = current + 2.5 * atr_val
            sl = current - 1.0 * atr_val
        else:
            tp = current - 2.5 * atr_val
            sl = current + 1.0 * atr_val

        # Confidence: tighter compression + bigger volume = higher confidence
        conf = min(0.83, 0.55 + (vol_ratio - 1.0) * 0.08 +
                   max(0, (1.0 - compression_ratio) * 0.3))

        signals.append(_base_signal(
            "ag_gravity_well_mut", symbol, direction, current, tp, sl, conf,
            f"AG7 Gravity Well: BB width at {current_bw:.3f}% "
            f"(20-bar min={min_bw:.3f}%), vol={vol_ratio:.1f}x avg, "
            f"compression releasing {direction}",
            parent_system="battleground",
            mutation_type="compression_breakout",
            bb_width_pct=round(current_bw, 4),
            bb_width_min=round(min_bw, 4),
            vol_ratio=round(vol_ratio, 2),
            compression_ratio=round(compression_ratio, 3),
            timeframe="1h",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# AG8: MOMENTUM CASCADE — Triple-Speed Momentum Alignment
# ═══════════════════════════════════════════════════════════════════════════
#
# Edge: When momentum at 3 different speeds (fast/medium/slow)
# ALL agree, the trend is strong and persistent. This is the
# purest possible momentum signal — no oscillators, no bands,
# no volume requirements. Just: "is it going up at every speed?"
#
# Only 3 conditions:
#   1. 3-bar return > 0 (fast momentum)
#   2. 8-bar return > 0 (medium momentum)
#   3. 21-bar return > 0 (slow momentum / trend)
#
# Why is this creative?
#   - IGNORES everything the industry obsesses over (RSI, volume, bands)
#   - Pure price action — the ultimate Occam's Razor strategy
#   - Based on academic research: momentum is the most persistent anomaly
#     in financial markets (Jegadeesh & Titman 1993, still works 30+ years later)
#   - Counterintuitive: "buy things that are already going up" feels wrong
#     but is statistically right
#
# The cascade effect: when fast, medium, and slow momentum align,
# it means the trend has built gradually and is self-reinforcing.
# This filters out mean-reversion traps (where fast momentum disagrees
# with slow trend) and also filters out fading momentum (where slow
# is up but fast is down = trend weakening).
# ═══════════════════════════════════════════════════════════════════════════

CASCADE_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT", "LTCUSDT",
    "NEARUSDT", "APTUSDT", "SUIUSDT", "INJUSDT",
    "FETUSDT", "SEIUSDT", "JUPUSDT", "TAOUSDT",
    "ARBUSDT", "OPUSDT", "ATOMUSDT", "ICPUSDT",
    "DOGEUSDT", "FILUSDT", "UNIUSDT", "AAVEUSDT",
    "BCHUSDT", "HBARUSDT", "ALGOUSDT", "WLDUSDT",
]

# Momentum lookback periods
FAST_BARS = 3
MEDIUM_BARS = 8
SLOW_BARS = 21

# Minimum momentum (filter out noise — require at least 0.3% move at each speed)
MIN_MOMENTUM_PCT = 0.003


def momentum_cascade(data: dict) -> list[dict]:
    """
    AG8: Triple-speed momentum alignment = strong persistent trend.

    Entry (BUY):
      1. 3-bar return > +0.3% (fast momentum up)
      2. 8-bar return > +0.3% (medium momentum up)
      3. 21-bar return > +0.3% (slow trend up)

    Entry (SELL): all three returns < -0.3%

    TP: 2.0x ATR (riding the trend)
    SL: 1.5x ATR (give room for pullbacks in strong trends)

    Expected: Medium-high frequency, moderate WR (~50-55%)
    """
    signals = []

    for symbol in CASCADE_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < SLOW_BARS + 5:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # Calculate returns at 3 speeds
        ret_fast = (current - float(close.iloc[-FAST_BARS - 1])) / float(close.iloc[-FAST_BARS - 1])
        ret_medium = (current - float(close.iloc[-MEDIUM_BARS - 1])) / float(close.iloc[-MEDIUM_BARS - 1])
        ret_slow = (current - float(close.iloc[-SLOW_BARS - 1])) / float(close.iloc[-SLOW_BARS - 1])

        # Check cascade alignment
        all_bullish = (ret_fast > MIN_MOMENTUM_PCT and
                       ret_medium > MIN_MOMENTUM_PCT and
                       ret_slow > MIN_MOMENTUM_PCT)

        all_bearish = (ret_fast < -MIN_MOMENTUM_PCT and
                       ret_medium < -MIN_MOMENTUM_PCT and
                       ret_slow < -MIN_MOMENTUM_PCT)

        if not all_bullish and not all_bearish:
            continue

        direction = "BUY" if all_bullish else "SELL"

        atr_val = float(_atr(high, low, close, 14).iloc[-1])
        if pd.isna(atr_val) or atr_val <= 0:
            continue

        # Momentum strength: sum of all 3 speeds (stronger = more conviction)
        total_momentum = abs(ret_fast) + abs(ret_medium) + abs(ret_slow)

        # Cascade quality: are faster speeds accelerating?
        # If fast > medium > slow (accelerating), VERY strong signal
        if direction == "BUY":
            is_accelerating = ret_fast > ret_medium > ret_slow
        else:
            is_accelerating = ret_fast < ret_medium < ret_slow

        if direction == "BUY":
            tp = current + 2.0 * atr_val
            sl = current - 1.5 * atr_val
        else:
            tp = current - 2.0 * atr_val
            sl = current + 1.5 * atr_val

        # Confidence
        conf = min(0.82, 0.50 + total_momentum * 3 +
                   (0.08 if is_accelerating else 0))

        accel_tag = "ACCELERATING" if is_accelerating else "aligned"

        signals.append(_base_signal(
            "ag_momentum_cascade_mut", symbol, direction, current, tp, sl, conf,
            f"AG8 Momentum Cascade: fast={ret_fast:+.2%} med={ret_medium:+.2%} "
            f"slow={ret_slow:+.2%} — {accel_tag} triple-speed {direction}",
            parent_system="battleground",
            mutation_type="momentum_cascade",
            ret_fast_pct=round(ret_fast * 100, 3),
            ret_medium_pct=round(ret_medium * 100, 3),
            ret_slow_pct=round(ret_slow * 100, 3),
            total_momentum_pct=round(total_momentum * 100, 3),
            is_accelerating=is_accelerating,
            timeframe="1h",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# Registry
# ═══════════════════════════════════════════════════════════════════════════

ALL_V2_MUTATIONS = {
    "ag_tidal_force": tidal_force,
    "ag_gravity_well": gravity_well,
    "ag_momentum_cascade": momentum_cascade,
}

ALL_V2_SYMBOLS = list(set(
    TIDAL_TRADE_SYMBOLS + GRAVITY_SYMBOLS + CASCADE_SYMBOLS + ["BTCUSDT"]
))


def run_all_v2(data: dict = None) -> list[dict]:
    """Run all 3 V2 mutations and return combined signals."""
    all_signals = []
    for name, func in ALL_V2_MUTATIONS.items():
        try:
            signals = func(data or {})
            all_signals.extend(signals)
            print(f"  {name}: {len(signals)} signals")
        except Exception as e:
            print(f"  {name}: ERROR -- {e}")
    return all_signals


if __name__ == "__main__":
    print("=" * 60)
    print("ANTIGRAVITY V2 MUTATIONS -- Creative Edge Exploiters")
    print("=" * 60)
    print()
    signals = run_all_v2()
    print(f"\nTotal signals: {len(signals)}")
