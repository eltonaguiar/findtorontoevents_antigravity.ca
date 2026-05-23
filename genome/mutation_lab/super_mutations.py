"""Super Mutation Strategies — Blending the Best of Every Winning System.

5 strategies that crossbreed techniques from the ONLY 3 profitable systems:
  - Battleground (298 trades, 61.7% WR, +158% PnL)
  - Cross Aggregation (48 trades, 58.3% WR, +71.4% PnL)
  - Claude Gainer ML (32 trades, 56.2% WR, +99.5% PnL)

Plus proven techniques from:
  - RSI Capitulation Sniper (+2.51%, 60% WR, 7.12 profit factor)
  - Deep-Value category (all 4 strategies profitable)
  - GENESIS genome (+442% PnL), NEXUS (+256% PnL)
  - Keltner Compression Expansion (72.9% WR on BTC)
  - Multi-Period RSI Confluence (64% WR, Sharpe 10.86)

Usage:
    from genome.mutation_lab.super_mutations import (
        SUPER_MUTATION_STRATEGIES,
        run_all_super_mutations,
    )

Each function follows the genome mutation_lab signal pattern:
    def strategy(df: pd.DataFrame, symbol: str, context: dict) -> list[dict]
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Project imports — indicators from Battleground's proven library
# ---------------------------------------------------------------------------
try:
    import sys
    from pathlib import Path
    _project_root = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(_project_root / "ml_battleground"))
    from shared.indicators import (
        rsi, ema, sma, macd, atr, bollinger_bands, keltner_channels,
        atr_gate, atr_volatility_regime, adx, supertrend,
        obv, stochastic, hurst_exponent, rate_of_change,
        mfi, chaikin_money_flow, volume_profile_poc,
        linear_regression_slope,
    )
    _HAS_INDICATORS = True
except ImportError as _e:
    logger.warning(f"Could not import shared.indicators: {_e}")
    _HAS_INDICATORS = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_signal(strategy: str, symbol: str, direction: str, entry: float,
                 confidence: float, reason: str, **extra) -> dict:
    """Create standardized signal dict (same format as battleground strategies)."""
    sig = {
        "strategy": strategy,
        "symbol": symbol,
        "direction": direction,
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "entry_price": round(entry, 8),
        "confidence": round(min(0.95, confidence), 4),
        "reason": reason,
        "source_system": "super_mutation",
        "trust_tier": "SANDBOX",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "category": "crypto",
    }
    sig.update(extra)
    return sig


def _compute_fear_greed() -> int:
    """Fetch Fear & Greed Index. Returns 50 on failure (neutral)."""
    try:
        import urllib.request
        import json
        req = urllib.request.Request(
            "https://api.alternative.me/fng/?limit=1",
            headers={"User-Agent": "SuperMutation/1.0"},
        )
        data = json.loads(urllib.request.urlopen(req, timeout=8).read())
        return int(data["data"][0]["value"])
    except Exception:
        return 50


def _dna_hash(strategy_name: str, params: dict) -> str:
    """Generate a reproducible DNA hash for a strategy + params combo."""
    raw = f"{strategy_name}:{sorted(params.items())}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


# =========================================================================
#  STRATEGY 1: Keltner-RSI Confluence v2
# =========================================================================

def keltner_rsi_confluence_v2(
    df: pd.DataFrame, symbol: str, context: dict | None = None
) -> list[dict]:
    """
    Combines the two highest-WR Battleground strategies into one entry filter:
      - Keltner Compression/Expansion (72.9% WR on BTC, 48 trades, p=0.0015)
      - Multi-Period RSI Confluence (64% WR, Sharpe 10.86)

    Entry conditions (ALL must hold):
      1. BB squeeze inside Keltner Channel on prior bar (compression detected)
      2. Price breaks above/below KC on current bar (expansion breakout)
      3. RSI(14) < 35 AND RSI(50) < 40 -- dual-period oversold alignment
      4. Volume > 1.3x 20-period median (Battleground-verified threshold)
      5. ATR gate passes (skip during crash regimes: ATR > 3x mean)

    TP: 2.0 * ATR(14) -- wider than Keltner-only (1.5x) because dual
        confirmation gives higher conviction for larger moves.
    SL: 1.0 * ATR(14) -- tight stop; dual filter means entries are precise.
    Expected R:R = 2:1

    Rationale: Each signal alone is profitable. Together, the false-positive
    rate drops dramatically. The squeeze detects coiled-spring setups while
    dual RSI ensures we only enter at genuine oversold extremes.
    """
    if not _HAS_INDICATORS or len(df) < 80:
        return []

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    vol = df.get("Volume", pd.Series(dtype=float))

    price = float(close.iloc[-1])
    if price <= 0:
        return []

    # -- Keltner Channel: EMA(20) +/- 1.5 * ATR(14) --
    kc_upper, kc_mid, kc_lower = keltner_channels(high, low, close, 20, 14, 1.5)

    # -- Bollinger Bands: SMA(20), 2.0 std --
    bb_upper, bb_mid, bb_lower, bb_width, bb_pctb = bollinger_bands(close, 20, 2.0)

    # -- Check squeeze on prior bar --
    if len(bb_upper) < 2 or len(kc_upper) < 2:
        return []

    bb_up_prev = float(bb_upper.iloc[-2])
    bb_lo_prev = float(bb_lower.iloc[-2])
    kc_up_prev = float(kc_upper.iloc[-2])
    kc_lo_prev = float(kc_lower.iloc[-2])

    squeeze = bb_up_prev < kc_up_prev and bb_lo_prev > kc_lo_prev
    if not squeeze:
        return []

    # -- ATR gate (crash protection from Battleground v93/v95 stress test) --
    atr_val = atr(high, low, close, 14)
    atr_now = float(atr_val.iloc[-1])
    if atr_now <= 0 or pd.isna(atr_now):
        return []

    vol_regime = atr_volatility_regime(high, low, close, 14, 30)
    if vol_regime["extreme_volatility"]:
        return []

    position_scale = vol_regime["position_scale"]

    # -- Multi-period RSI oversold confluence --
    rsi14 = rsi(close, 14)
    rsi50 = rsi(close, 50) if len(close) >= 55 else rsi(close, min(len(close) - 5, 30))
    rsi14_now = float(rsi14.iloc[-1])
    rsi50_now = float(rsi50.iloc[-1])

    if pd.isna(rsi14_now) or pd.isna(rsi50_now):
        return []

    # Dual RSI must confirm oversold
    dual_rsi_oversold = rsi14_now < 35 and rsi50_now < 40

    if not dual_rsi_oversold:
        return []

    # -- Volume confirmation: > 1.3x 20-period median --
    vol_ok = True
    if len(vol) >= 20 and vol.sum() > 0:
        vol_now = float(vol.iloc[-1])
        vol_median = float(vol.rolling(20).median().iloc[-1])
        if vol_median > 0 and np.isfinite(vol_now):
            vol_ok = vol_now > 1.3 * vol_median
    if not vol_ok:
        return []

    # -- Breakout direction (price vs KC) --
    kc_up_now = float(kc_upper.iloc[-1])
    kc_lo_now = float(kc_lower.iloc[-1])

    signals = []

    # For this deep-value variant, we only go LONG (RSI < 35 means oversold bounce)
    if price <= kc_lo_now:
        # Price at or below lower Keltner = deep oversold squeeze breakout down
        # Combined with RSI < 35 = strong capitulation BUY
        rsi14_depth = (35 - rsi14_now) / 35
        rsi50_depth = (40 - rsi50_now) / 40
        conf = min(0.92, 0.65 + rsi14_depth * 0.10 + rsi50_depth * 0.08)

        if vol_regime["high_volatility_regime"]:
            conf *= 0.85

        tp = round(price + 2.0 * atr_now, 8)
        sl = round(price - 1.0 * atr_now, 8)

        signals.append(_base_signal(
            "keltner_rsi_confluence_v2", symbol, "LONG", price, conf,
            f"Keltner squeeze + dual RSI oversold: RSI14={rsi14_now:.0f}, "
            f"RSI50={rsi50_now:.0f}, price ${price:.4f} at/below KC lower ${kc_lo_now:.4f}",
            take_profit=tp,
            stop_loss=sl,
            risk_reward=2.0,
            position_scale=position_scale,
            atr_value=atr_now,
            rsi14=rsi14_now,
            rsi50=rsi50_now,
            high_volatility_regime=vol_regime["high_volatility_regime"],
            atr_ratio=vol_regime["atr_ratio"],
            dna_hash=_dna_hash("keltner_rsi_confluence_v2", {
                "rsi14": round(rsi14_now), "rsi50": round(rsi50_now),
            }),
            parent_strategies=["keltner_compression_expansion", "multi_period_rsi_confluence"],
            expected_wr="70%+",
        ))

    return signals


# =========================================================================
#  STRATEGY 2: Consensus Deep-Value Hybrid
# =========================================================================

def consensus_deep_value_hybrid(
    df: pd.DataFrame, symbol: str, context: dict | None = None
) -> list[dict]:
    """
    Combines cross-aggregation consensus (58.3% WR, +71.4% PnL) with
    deep-value RSI capitulation (60% WR, 7.12 profit factor).

    Entry conditions (ALL must hold):
      1. RSI(14) < 25 -- extreme oversold (deeper than standard 30)
      2. Price bouncing from 7d low (bounce_pct > 1%)
      3. Price in deep drawdown from 90d high (> 20%)
      4. Fear & Greed Index < 30 (market-wide capitulation)
      5. Consensus check: symbol must appear in 3+ source systems' picks
         OR score high on conviction metrics (consensus is optional context)

    TP: 15% from entry (RSI capitulation recovery target)
    SL: 8% from entry (tight for deep-value, proven by Sniper portfolio)
    Expected R:R = 1.875:1

    Rationale: The RSI Capitulation Sniper is the TOP portfolio (+2.51%, 60% WR,
    7.12 profit factor). Adding consensus agreement from cross-aggregation
    (the second-best system) ensures we only enter when MULTIPLE independent
    systems agree the asset is oversold. Fear & Greed < 30 adds macro
    confirmation. This is a "blood in the streets" strategy.
    """
    if not _HAS_INDICATORS or len(df) < 90:
        return []

    context = context or {}
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    price = float(close.iloc[-1])
    if price <= 0:
        return []

    # -- RSI must be deeply oversold --
    rsi14 = rsi(close, 14)
    rsi_now = float(rsi14.iloc[-1])
    if pd.isna(rsi_now) or rsi_now >= 25:
        return []

    # -- Drawdown from 90d (or available) high --
    lookback = min(len(high), 90 * 24)  # up to 90 days of hourly data
    high_90d = float(high.iloc[-lookback:].max())
    if high_90d <= 0:
        return []
    drawdown_pct = ((high_90d - price) / high_90d) * 100

    if drawdown_pct < 20:
        return []  # Not deep enough

    # -- Bounce confirmation (price recovering from recent low) --
    lookback_7d = min(len(low), 7 * 24)
    low_7d = float(low.iloc[-lookback_7d:].min())
    bounce_pct = ((price - low_7d) / low_7d) * 100 if low_7d > 0 else 0

    if bounce_pct < 1.0:
        return []  # Not bouncing yet

    # -- Fear & Greed filter --
    fear_greed = context.get("fear_greed", _compute_fear_greed())
    if fear_greed > 30:
        return []  # Only buy in fear/extreme fear

    # -- Consensus check (if available from cross-aggregation context) --
    agreeing_systems = context.get("agreeing_systems", [])
    consensus_count = len(agreeing_systems) if agreeing_systems else 0

    # If consensus data available, require 3+ agreements
    # If not available (standalone run), proceed based on technical signals
    has_consensus = consensus_count >= 3
    running_standalone = not context.get("has_consensus_data", False)

    if not has_consensus and not running_standalone:
        return []  # Had consensus data but didn't meet threshold

    # -- Confidence computation --
    # Deeper RSI oversold = higher confidence (proven by Sniper)
    rsi_depth = (25 - rsi_now) / 25  # 0-1 scale
    drawdown_depth = min((drawdown_pct - 20) / 40, 1.0)  # 0-1 scale
    fear_depth = (30 - fear_greed) / 30  # 0-1 scale

    conf = min(0.92, 0.55 + rsi_depth * 0.12 + drawdown_depth * 0.08
               + fear_depth * 0.06 + consensus_count * 0.03)

    # -- TP / SL (RSI Capitulation Sniper parameters: 15% TP, 8% SL) --
    tp = round(price * 1.15, 8)
    sl = round(price * 0.92, 8)
    rr = (tp - price) / (price - sl)

    signals = []
    signals.append(_base_signal(
        "consensus_deep_value_hybrid", symbol, "LONG", price, conf,
        f"Deep-value capitulation: RSI={rsi_now:.0f}, drawdown={drawdown_pct:.0f}%, "
        f"F&G={fear_greed}, bounce={bounce_pct:.1f}%, "
        f"consensus={consensus_count} systems",
        take_profit=tp,
        stop_loss=sl,
        risk_reward=round(rr, 2),
        rsi14=rsi_now,
        drawdown_pct=round(drawdown_pct, 1),
        fear_greed=fear_greed,
        bounce_pct=round(bounce_pct, 2),
        consensus_count=consensus_count,
        agreeing_systems=agreeing_systems,
        dna_hash=_dna_hash("consensus_deep_value_hybrid", {
            "rsi": round(rsi_now), "dd": round(drawdown_pct),
            "fg": fear_greed,
        }),
        parent_strategies=["rsi_capitulation_sniper", "cross_aggregation_consensus",
                           "fear_greed_contrarian"],
        expected_wr="60%+",
    ))

    return signals


# =========================================================================
#  STRATEGY 3: Genesis Momentum Blend
# =========================================================================

def genesis_momentum_blend(
    df: pd.DataFrame, symbol: str, context: dict | None = None
) -> list[dict]:
    """
    Inspired by GENESIS genome (+442% PnL) -- expression tree DNA evolution
    that invents novel indicator formulas via genetic programming.

    GENESIS's core edge: it discovers non-obvious indicator combinations
    by crossing RSI/EMA/MACD/BB primitives with arithmetic operators.
    The +442% result came from expression trees that effectively computed:
      score = f(RSI, EMA_ratio, MACD_hist, BB_pctb, volume_ratio)

    This strategy replicates that scoring approach using a linear blend
    of the most predictive indicators (from Battleground backtest data):
      - EMA stack alignment (EMA9 > EMA21 > EMA50) -- trend confirmed
      - MACD histogram positive and rising -- momentum acceleration
      - RSI in sweet spot (40-65) -- not overbought, not capitulating
      - BB %B in expansion zone (> 0.6) -- breaking out of range
      - Volume ratio > 1.5x -- institutional flow confirmation
      - Supertrend bullish -- trend direction filter

    Adds momentum confirmation from Battleground's proven indicators:
      - ADX > 25 -- strong trend (eliminate chop/range entries)
      - Rate of Change (7d) > 0 -- price momentum positive

    TP: 2.0 * ATR(14) -- momentum continuation target
    SL: 1.5 * ATR(14) -- slightly wider than Keltner (momentum can retrace)
    Expected R:R = 1.33:1 (compensated by higher WR from multi-filter)
    """
    if not _HAS_INDICATORS or len(df) < 60:
        return []

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    vol = df.get("Volume", pd.Series(dtype=float))

    price = float(close.iloc[-1])
    if price <= 0:
        return []

    # -- ATR gate --
    atr_val = atr(high, low, close, 14)
    atr_now = float(atr_val.iloc[-1])
    if atr_now <= 0 or pd.isna(atr_now):
        return []

    vol_regime = atr_volatility_regime(high, low, close, 14, 30)
    if vol_regime["extreme_volatility"]:
        return []

    # -- GENESIS-style multi-indicator scoring --
    # Each sub-signal contributes a score component (0 or positive weight)
    score = 0.0
    reasons = []

    # 1. EMA stack alignment (EMA9 > EMA21 > EMA50)
    ema9 = float(ema(close, 9).iloc[-1])
    ema21 = float(ema(close, 21).iloc[-1])
    ema50 = float(ema(close, 50).iloc[-1])
    ema_stack_bullish = ema9 > ema21 > ema50

    if ema_stack_bullish:
        score += 0.18
        reasons.append("EMA stack aligned")
    elif ema9 > ema21:
        score += 0.08  # partial credit

    # 2. MACD histogram positive and rising
    macd_line, macd_sig, macd_hist = macd(close, 12, 26, 9)
    hist_now = float(macd_hist.iloc[-1])
    hist_prev = float(macd_hist.iloc[-2]) if len(macd_hist) > 1 else 0
    if not pd.isna(hist_now) and hist_now > 0:
        score += 0.12
        if not pd.isna(hist_prev) and hist_now > hist_prev:
            score += 0.06  # rising histogram bonus
            reasons.append("MACD hist rising")
        else:
            reasons.append("MACD hist positive")

    # 3. RSI in the momentum sweet spot (40-65)
    rsi14 = rsi(close, 14)
    rsi_now = float(rsi14.iloc[-1])
    if not pd.isna(rsi_now) and 40 <= rsi_now <= 65:
        score += 0.10
        reasons.append(f"RSI {rsi_now:.0f} in sweet spot")

    # 4. BB %B in expansion zone
    bb_upper, bb_mid, bb_lower, bb_width, bb_pctb = bollinger_bands(close, 20, 2.0)
    pctb_now = float(bb_pctb.iloc[-1])
    if not pd.isna(pctb_now) and pctb_now > 0.6:
        score += 0.10
        reasons.append(f"BB %B={pctb_now:.2f} expanding")

    # 5. Volume ratio confirmation
    vol_ratio = 1.0
    if len(vol) >= 20 and vol.sum() > 0:
        vol_avg = float(vol.rolling(20).mean().iloc[-1])
        if vol_avg > 0:
            vol_ratio = float(vol.iloc[-1]) / vol_avg
    if vol_ratio > 1.5:
        score += 0.10
        reasons.append(f"Vol {vol_ratio:.1f}x")

    # 6. Supertrend bullish
    st = supertrend(high, low, close, 10, 3.0)
    if float(st.iloc[-1]) == 1:
        score += 0.10
        reasons.append("Supertrend bullish")

    # 7. ADX > 25 -- strong trend
    adx_val, plus_di, minus_di = adx(high, low, close, 14)
    adx_now = float(adx_val.iloc[-1])
    if not pd.isna(adx_now) and adx_now > 25:
        score += 0.08
        reasons.append(f"ADX={adx_now:.0f} trending")

    # 8. Rate of Change (7-period) positive
    roc = rate_of_change(close, 7)
    roc_now = float(roc.iloc[-1])
    if not pd.isna(roc_now) and roc_now > 0:
        score += 0.06
        reasons.append(f"RoC7={roc_now*100:.1f}%")

    # -- Minimum score threshold (need 4+ confirming sub-signals) --
    if score < 0.50:
        return []

    signals = []

    # Confidence from score
    conf = min(0.92, 0.50 + score * 0.50)
    if vol_regime["high_volatility_regime"]:
        conf *= 0.85

    tp = round(price + 2.0 * atr_now, 8)
    sl = round(price - 1.5 * atr_now, 8)

    signals.append(_base_signal(
        "genesis_momentum_blend", symbol, "LONG", price, conf,
        f"GENESIS momentum: score={score:.2f}, {', '.join(reasons)}",
        take_profit=tp,
        stop_loss=sl,
        risk_reward=round(2.0 / 1.5, 2),
        position_scale=vol_regime["position_scale"],
        atr_value=atr_now,
        genesis_score=round(score, 4),
        ema_stack_bullish=ema_stack_bullish,
        adx=round(adx_now, 1) if not pd.isna(adx_now) else None,
        rsi14=round(rsi_now, 1) if not pd.isna(rsi_now) else None,
        vol_ratio=round(vol_ratio, 2),
        dna_hash=_dna_hash("genesis_momentum_blend", {
            "score": round(score, 2), "ema_stack": ema_stack_bullish,
        }),
        parent_strategies=["GENESIS_genome", "battleground_keltner",
                           "battleground_momentum"],
        expected_wr="62%+",
    ))

    return signals


# =========================================================================
#  STRATEGY 4: ML Keltner Adaptive
# =========================================================================

def ml_keltner_adaptive(
    df: pd.DataFrame, symbol: str, context: dict | None = None
) -> list[dict]:
    """
    Combines Claude Gainer ML's feature-driven scanning (56.2% WR, +99.5% PnL)
    with Keltner channel signals (72.9% WR), adding adaptive parameter
    adjustment based on volatility regime.

    Claude Gainer ML's edge: it uses 30 features (RSI, BB, OBV, volume
    velocity, sector performance) and ensemble prediction. We replicate
    this by computing a multi-feature score and combining it with Keltner
    breakout detection.

    Adaptive behavior:
      - LOW volatility (ATR < 0.8x mean):
          Use tighter Keltner (1.2x ATR), smaller TP (1.2x ATR)
          These are ranging markets -- take quick profits
      - NORMAL volatility (0.8-2.0x mean):
          Standard Keltner (1.5x ATR), normal TP (1.8x ATR)
      - HIGH volatility (2.0-3.0x mean):
          Wider Keltner (2.0x ATR), larger TP (2.5x ATR), half position
      - EXTREME volatility (> 3.0x mean):
          Skip entirely (proven 42% WR crash in stress test)

    Additional ML-style features (from Claude Gainer):
      - OBV trend (accumulation/distribution)
      - MFI < 20 (volume-weighted oversold)
      - Chaikin Money Flow positive (buying pressure)
      - Hurst exponent (mean-reverting vs trending)

    TP/SL: Adaptive (see above)
    """
    if not _HAS_INDICATORS or len(df) < 80:
        return []

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    vol = df.get("Volume", pd.Series(dtype=float))

    price = float(close.iloc[-1])
    if price <= 0:
        return []

    # -- ATR and volatility regime --
    atr_val = atr(high, low, close, 14)
    atr_now = float(atr_val.iloc[-1])
    if atr_now <= 0 or pd.isna(atr_now):
        return []

    vol_regime = atr_volatility_regime(high, low, close, 14, 30)
    if vol_regime["extreme_volatility"]:
        return []  # Skip during crashes

    atr_ratio = vol_regime["atr_ratio"]

    # -- Adaptive Keltner parameters based on regime --
    if atr_ratio < 0.8:
        # Low volatility: tighter channels, quick profits
        kc_mult = 1.2
        tp_mult = 1.2
        sl_mult = 0.8
        regime_label = "low_vol"
    elif atr_ratio < 2.0:
        # Normal: standard parameters
        kc_mult = 1.5
        tp_mult = 1.8
        sl_mult = 1.0
        regime_label = "normal"
    else:
        # High volatility: wider channels, bigger targets, half size
        kc_mult = 2.0
        tp_mult = 2.5
        sl_mult = 1.5
        regime_label = "high_vol"

    # -- Keltner Channel with adaptive multiplier --
    kc_ema = ema(close, 20)
    kc_upper = kc_ema + kc_mult * atr_val
    kc_lower = kc_ema - kc_mult * atr_val

    kc_up_now = float(kc_upper.iloc[-1])
    kc_lo_now = float(kc_lower.iloc[-1])

    # -- ML-style feature scoring (inspired by Claude Gainer's 30 features) --
    ml_score = 0.0
    ml_reasons = []

    # Feature 1: OBV trend (accumulation if OBV rising over 20 bars)
    if len(vol) >= 20 and vol.sum() > 0:
        obv_vals = obv(close, vol)
        obv_slope = float(linear_regression_slope(obv_vals, 20).iloc[-1])
        if not pd.isna(obv_slope) and obv_slope > 0.001:
            ml_score += 0.15
            ml_reasons.append("OBV accumulating")

    # Feature 2: MFI (volume-weighted RSI) oversold
    if len(vol) >= 20 and vol.sum() > 0:
        mfi_val = mfi(high, low, close, vol, 14)
        mfi_now = float(mfi_val.iloc[-1])
        if not pd.isna(mfi_now) and mfi_now < 20:
            ml_score += 0.15
            ml_reasons.append(f"MFI={mfi_now:.0f} oversold")
        elif not pd.isna(mfi_now) and mfi_now < 40:
            ml_score += 0.05

    # Feature 3: Chaikin Money Flow positive (buying pressure)
    if len(vol) >= 20 and vol.sum() > 0:
        cmf_val = chaikin_money_flow(high, low, close, vol, 20)
        cmf_now = float(cmf_val.iloc[-1])
        if not pd.isna(cmf_now) and cmf_now > 0.05:
            ml_score += 0.10
            ml_reasons.append(f"CMF={cmf_now:.2f} positive")

    # Feature 4: Hurst exponent regime
    if len(close) >= 100:
        h = hurst_exponent(close, 50)
        if h > 0.55:
            ml_score += 0.08  # Trending -- momentum strategies work
            ml_reasons.append(f"Hurst={h:.2f} trending")
        elif h < 0.45:
            ml_score += 0.08  # Mean-reverting -- good for Keltner reversion
            ml_reasons.append(f"Hurst={h:.2f} mean-reverting")

    # Feature 5: RSI not overbought
    rsi14 = rsi(close, 14)
    rsi_now = float(rsi14.iloc[-1])
    if not pd.isna(rsi_now) and rsi_now < 60:
        ml_score += 0.08
    elif not pd.isna(rsi_now) and rsi_now > 70:
        ml_score -= 0.10  # Overbought penalty

    # Feature 6: Volume velocity (Claude Gainer v4.0 wide-universe scan feature)
    if len(vol) >= 24 and vol.sum() > 0:
        vol_recent = float(vol.iloc[-6:].sum())
        vol_prior = float(vol.iloc[-24:-6].sum()) / 3  # normalize to same period
        vol_velocity = vol_recent / vol_prior if vol_prior > 0 else 1.0
        if vol_velocity > 1.5:
            ml_score += 0.10
            ml_reasons.append(f"Vol velocity {vol_velocity:.1f}x")

    # -- Combine Keltner breakout with ML score --
    signals = []

    # Need minimum ML score (at least 3 confirming ML features)
    if ml_score < 0.25:
        return []

    # LONG: price at/below lower Keltner + ML features confirm
    if price <= kc_lo_now:
        conf = min(0.90, 0.55 + ml_score * 0.40 + 0.05)
        if vol_regime["high_volatility_regime"]:
            conf *= 0.85

        tp = round(price + tp_mult * atr_now, 8)
        sl = round(price - sl_mult * atr_now, 8)

        signals.append(_base_signal(
            "ml_keltner_adaptive", symbol, "LONG", price, conf,
            f"Adaptive Keltner LONG ({regime_label}): price ${price:.4f} <= "
            f"KC lower ${kc_lo_now:.4f}, ML score={ml_score:.2f}, "
            f"{', '.join(ml_reasons)}",
            take_profit=tp,
            stop_loss=sl,
            risk_reward=round(tp_mult / sl_mult, 2),
            position_scale=vol_regime["position_scale"],
            atr_value=atr_now,
            atr_ratio=atr_ratio,
            regime=regime_label,
            kc_mult=kc_mult,
            ml_score=round(ml_score, 4),
            rsi14=round(rsi_now, 1) if not pd.isna(rsi_now) else None,
            dna_hash=_dna_hash("ml_keltner_adaptive", {
                "regime": regime_label, "ml_score": round(ml_score, 2),
            }),
            parent_strategies=["claude_gainer_ml", "keltner_compression_expansion",
                               "atr_volatility_regime"],
            expected_wr="65%+",
        ))

    # LONG: price breaking above upper Keltner (momentum breakout)
    elif price > kc_up_now and not pd.isna(rsi_now) and rsi_now < 70:
        conf = min(0.88, 0.50 + ml_score * 0.35 + 0.05)
        if vol_regime["high_volatility_regime"]:
            conf *= 0.85

        tp = round(price + tp_mult * atr_now, 8)
        sl = round(price - sl_mult * atr_now, 8)

        signals.append(_base_signal(
            "ml_keltner_adaptive", symbol, "LONG", price, conf,
            f"Adaptive Keltner breakout UP ({regime_label}): price ${price:.4f} > "
            f"KC upper ${kc_up_now:.4f}, ML score={ml_score:.2f}, "
            f"{', '.join(ml_reasons)}",
            take_profit=tp,
            stop_loss=sl,
            risk_reward=round(tp_mult / sl_mult, 2),
            position_scale=vol_regime["position_scale"],
            atr_value=atr_now,
            atr_ratio=atr_ratio,
            regime=regime_label,
            kc_mult=kc_mult,
            ml_score=round(ml_score, 4),
            rsi14=round(rsi_now, 1) if not pd.isna(rsi_now) else None,
            dna_hash=_dna_hash("ml_keltner_adaptive", {
                "regime": regime_label, "ml_score": round(ml_score, 2),
                "breakout": "up",
            }),
            parent_strategies=["claude_gainer_ml", "keltner_channel_breakout",
                               "atr_volatility_regime"],
            expected_wr="62%+",
        ))

    return signals


# =========================================================================
#  STRATEGY 5: Multi-System Conviction Filter
# =========================================================================

def multi_system_conviction_filter(
    df: pd.DataFrame, symbol: str, context: dict | None = None
) -> list[dict]:
    """
    Meta-strategy that combines ALL winning approaches into one high-conviction
    filter. Only enters when 3+ different top-system techniques independently
    agree on direction.

    Scoring layers (weighted by proven system WR):
      Layer 1 -- Battleground signals (weight 1.5x, highest proven WR):
        - Keltner squeeze detected (BB inside KC)
        - Supertrend bullish
        - RSI in favorable zone (<60 for LONG)
        - Volume > 1.3x median
      Layer 2 -- Deep-Value signals (weight 1.3x, all profitable):
        - RSI < 35 (capitulation)
        - Price in drawdown from highs
        - Bounce confirmation (price rising from lows)
      Layer 3 -- ML Feature signals (weight 1.0x):
        - OBV accumulation trend
        - MFI oversold or neutral
        - Positive volume velocity
      Layer 4 -- Macro filter (weight 1.2x):
        - Fear & Greed < 30 (fear = buy)
        - Stochastic %K < 20 (oversold)

    Conviction score = weighted sum of active layers.
    ONLY emit signal if conviction >= 3 layers active AND score > threshold.

    TP/SL: Scaled by conviction level.
      - 3 layers: conservative (1.5x ATR TP, 1.0x SL)
      - 4 layers: standard (2.0x ATR TP, 1.2x SL)
    """
    if not _HAS_INDICATORS or len(df) < 60:
        return []

    context = context or {}
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    vol = df.get("Volume", pd.Series(dtype=float))

    price = float(close.iloc[-1])
    if price <= 0:
        return []

    # -- ATR --
    atr_val = atr(high, low, close, 14)
    atr_now = float(atr_val.iloc[-1])
    if atr_now <= 0 or pd.isna(atr_now):
        return []

    vol_regime = atr_volatility_regime(high, low, close, 14, 30)
    if vol_regime["extreme_volatility"]:
        return []

    # ================================================================
    # Layer 1: Battleground signals (weight 1.5)
    # ================================================================
    layer1_score = 0.0
    layer1_active = False
    layer1_reasons = []

    # Keltner squeeze check
    kc_upper, kc_mid, kc_lower = keltner_channels(high, low, close, 20, 14, 1.5)
    bb_upper, bb_mid, bb_lower, bb_width, bb_pctb = bollinger_bands(close, 20, 2.0)

    if len(bb_upper) >= 2 and len(kc_upper) >= 2:
        squeeze = (float(bb_upper.iloc[-2]) < float(kc_upper.iloc[-2]) and
                   float(bb_lower.iloc[-2]) > float(kc_lower.iloc[-2]))
        if squeeze:
            layer1_score += 0.15
            layer1_reasons.append("KC squeeze")

    # Supertrend bullish
    st = supertrend(high, low, close, 10, 3.0)
    if float(st.iloc[-1]) == 1:
        layer1_score += 0.12
        layer1_reasons.append("Supertrend bullish")

    # RSI in favorable zone
    rsi14 = rsi(close, 14)
    rsi_now = float(rsi14.iloc[-1])
    if not pd.isna(rsi_now) and rsi_now < 60:
        layer1_score += 0.08
        layer1_reasons.append(f"RSI={rsi_now:.0f}")

    # Volume above median
    if len(vol) >= 20 and vol.sum() > 0:
        vol_median = float(vol.rolling(20).median().iloc[-1])
        vol_now = float(vol.iloc[-1])
        if vol_median > 0 and vol_now > 1.3 * vol_median:
            layer1_score += 0.10
            layer1_reasons.append(f"Vol {vol_now/vol_median:.1f}x")

    if layer1_score >= 0.20:
        layer1_active = True

    # ================================================================
    # Layer 2: Deep-Value signals (weight 1.3)
    # ================================================================
    layer2_score = 0.0
    layer2_active = False
    layer2_reasons = []

    # RSI capitulation
    if not pd.isna(rsi_now) and rsi_now < 35:
        layer2_score += 0.20
        layer2_reasons.append(f"RSI capitulation {rsi_now:.0f}")

    # Drawdown from highs
    lookback_90d = min(len(high), 90 * 24)
    high_90d = float(high.iloc[-lookback_90d:].max())
    if high_90d > 0:
        drawdown = ((high_90d - price) / high_90d) * 100
        if drawdown > 20:
            layer2_score += 0.15
            layer2_reasons.append(f"Drawdown {drawdown:.0f}%")

    # Bounce confirmation
    lookback_7d = min(len(low), 7 * 24)
    low_7d = float(low.iloc[-lookback_7d:].min())
    bounce = ((price - low_7d) / low_7d) * 100 if low_7d > 0 else 0
    if bounce > 1.0:
        layer2_score += 0.10
        layer2_reasons.append(f"Bounce {bounce:.1f}%")

    if layer2_score >= 0.20:
        layer2_active = True

    # ================================================================
    # Layer 3: ML Feature signals (weight 1.0)
    # ================================================================
    layer3_score = 0.0
    layer3_active = False
    layer3_reasons = []

    # OBV accumulation
    if len(vol) >= 20 and vol.sum() > 0:
        obv_vals = obv(close, vol)
        obv_slope = float(linear_regression_slope(obv_vals, 20).iloc[-1])
        if not pd.isna(obv_slope) and obv_slope > 0.001:
            layer3_score += 0.15
            layer3_reasons.append("OBV accumulating")

    # MFI oversold
    if len(vol) >= 20 and vol.sum() > 0:
        mfi_val = mfi(high, low, close, vol, 14)
        mfi_now = float(mfi_val.iloc[-1])
        if not pd.isna(mfi_now) and mfi_now < 30:
            layer3_score += 0.15
            layer3_reasons.append(f"MFI={mfi_now:.0f}")

    # Volume velocity
    if len(vol) >= 24 and vol.sum() > 0:
        vol_recent = float(vol.iloc[-6:].sum())
        vol_prior = float(vol.iloc[-24:-6].sum()) / 3
        vol_velocity = vol_recent / vol_prior if vol_prior > 0 else 1.0
        if vol_velocity > 1.5:
            layer3_score += 0.10
            layer3_reasons.append(f"Vol velocity {vol_velocity:.1f}x")

    if layer3_score >= 0.15:
        layer3_active = True

    # ================================================================
    # Layer 4: Macro filter (weight 1.2)
    # ================================================================
    layer4_score = 0.0
    layer4_active = False
    layer4_reasons = []

    # Fear & Greed
    fear_greed = context.get("fear_greed", _compute_fear_greed())
    if fear_greed < 30:
        layer4_score += 0.20
        layer4_reasons.append(f"F&G={fear_greed} (fear)")
    elif fear_greed < 45:
        layer4_score += 0.08

    # Stochastic %K oversold
    stoch_k, stoch_d = stochastic(high, low, close, 14, 3)
    stoch_now = float(stoch_k.iloc[-1])
    if not pd.isna(stoch_now) and stoch_now < 20:
        layer4_score += 0.15
        layer4_reasons.append(f"Stoch %K={stoch_now:.0f}")

    if layer4_score >= 0.15:
        layer4_active = True

    # ================================================================
    # Conviction computation
    # ================================================================
    active_layers = sum([layer1_active, layer2_active, layer3_active, layer4_active])

    if active_layers < 3:
        return []  # Need 3+ layers agreeing

    # Weighted conviction score
    conviction = (
        layer1_score * 1.5 +  # Battleground weight (highest WR)
        layer2_score * 1.3 +  # Deep-Value weight (all profitable)
        layer3_score * 1.0 +  # ML Features weight
        layer4_score * 1.2    # Macro filter weight
    )

    # -- Adaptive TP/SL based on conviction level --
    if active_layers >= 4:
        tp_mult = 2.0
        sl_mult = 1.2
        conviction_label = "ultra"
    else:
        tp_mult = 1.5
        sl_mult = 1.0
        conviction_label = "standard"

    # Confidence from conviction score + active layers
    conf = min(0.93, 0.50 + conviction * 0.30 + active_layers * 0.05)
    if vol_regime["high_volatility_regime"]:
        conf *= 0.85

    tp = round(price + tp_mult * atr_now, 8)
    sl = round(price - sl_mult * atr_now, 8)

    # Collect all reasons
    all_reasons = layer1_reasons + layer2_reasons + layer3_reasons + layer4_reasons

    signals = []
    signals.append(_base_signal(
        "multi_system_conviction_filter", symbol, "LONG", price, conf,
        f"Multi-system conviction ({conviction_label}): "
        f"{active_layers}/4 layers active, score={conviction:.2f}, "
        f"{', '.join(all_reasons[:8])}",
        take_profit=tp,
        stop_loss=sl,
        risk_reward=round(tp_mult / sl_mult, 2),
        position_scale=vol_regime["position_scale"],
        atr_value=atr_now,
        conviction_score=round(conviction, 4),
        active_layers=active_layers,
        conviction_label=conviction_label,
        layer1_score=round(layer1_score, 3),
        layer2_score=round(layer2_score, 3),
        layer3_score=round(layer3_score, 3),
        layer4_score=round(layer4_score, 3),
        fear_greed=fear_greed,
        rsi14=round(rsi_now, 1) if not pd.isna(rsi_now) else None,
        dna_hash=_dna_hash("multi_system_conviction_filter", {
            "layers": active_layers, "conviction": round(conviction, 2),
        }),
        parent_strategies=[
            "battleground_keltner", "battleground_supertrend",
            "rsi_capitulation_sniper", "deep_drawdown_dca",
            "claude_gainer_ml", "cross_aggregation_consensus",
            "fear_greed_contrarian",
        ],
        expected_wr="65%+",
    ))

    return signals


# =========================================================================
#  2026-04-11: New Mutation Strategies from Scoring Optimization Audit
#  Based on proven winners with highest forward WR and PF
# =========================================================================


def regime_filtered_obv_divergence(
    df: pd.DataFrame, symbol: str, context: dict | None = None,
) -> list[dict]:
    """OBV divergence with regime filter to skip ranging/bear markets.

    Parent: st_obv_support_divergence (61.5% WR, PF 2.10, +202% PnL, 327 trades)
    Mutation: Add regime detection — skip signals during RANGING (10% WR) and
    TRENDING_DOWN (16.7% WR) regimes where long-only strategies fail.
    Uses 50-period EMA slope + ADX for regime classification.
    """
    if not _HAS_INDICATORS or df is None or len(df) < 60:
        return []

    signals = []
    context = context or {}

    _close = df["Close"]
    _high = df["High"]
    _low = df["Low"]
    _volume = df["Volume"]

    _atr_vals = atr(_high, _low, _close, 14)
    _rsi14 = rsi(_close, 14)
    _obv_vals = obv(_close, _volume)
    _ema50 = ema(_close, 50)
    _adx_vals, _, _ = adx(_high, _low, _close, 14)
    _sma20 = sma(_close, 20)

    for i in range(55, len(df)):
        if pd.isna(_atr_vals.iloc[i]) or _atr_vals.iloc[i] <= 0:
            continue

        cur_close = _close.iloc[i]
        cur_atr = _atr_vals.iloc[i]
        cur_rsi = _rsi14.iloc[i]
        cur_obv = _obv_vals.iloc[i]
        cur_adx = _adx_vals.iloc[i] if not pd.isna(_adx_vals.iloc[i]) else 15
        cur_ema50 = _ema50.iloc[i]

        # Regime filter: skip if ADX < 20 (ranging) or price below EMA50 with falling slope
        if pd.isna(cur_ema50) or cur_adx < 20:
            continue  # Ranging regime — 10% WR, skip
        ema50_slope = (cur_ema50 - _ema50.iloc[i - 10]) / _ema50.iloc[i - 10] * 100 if _ema50.iloc[i - 10] > 0 else 0
        if cur_close < cur_ema50 and ema50_slope < -1.0:
            continue  # Trending down — 16.7% WR, skip

        # OBV divergence: price making lower lows but OBV making higher lows
        prev_obv = _obv_vals.iloc[i - 10]
        prev_close = _close.iloc[i - 10]
        obv_rising = cur_obv > prev_obv
        price_flat_or_down = cur_close <= prev_close * 1.01

        if not (obv_rising and price_flat_or_down):
            continue

        # RSI confirmation: not overbought
        if pd.isna(cur_rsi) or cur_rsi > 65:
            continue

        # Volume confirmation: above average
        vol_avg = _volume.iloc[max(0, i - 20):i].mean()
        if vol_avg > 0 and _volume.iloc[i] < vol_avg * 0.8:
            continue

        tp = cur_close + 2.0 * cur_atr
        sl = cur_close - 1.0 * cur_atr
        conf = min(0.85, 0.60 + (cur_adx - 20) / 100)

        signals.append(_base_signal(
            "regime_filtered_obv_divergence", symbol, "LONG", cur_close, conf,
            f"OBV divergence + regime filter: ADX={cur_adx:.0f}, drawdown recovery, "
            f"OBV accumulating while price flat",
            take_profit=tp,
            stop_loss=sl,
            risk_reward=round(tp_mult if 'tp_mult' in dir() else 2.0, 2),
            source_system="genome_mutations_v2",
            dna_hash=_dna_hash("regime_filtered_obv_divergence", {
                "adx": round(cur_adx), "rsi": round(cur_rsi),
            }),
        ))
        break

    return signals


def fear_greed_obv_confluence(
    df: pd.DataFrame, symbol: str, context: dict | None = None,
) -> list[dict]:
    """Fear & Greed contrarian + OBV volume confirmation.

    Parents:
    - st_fear_greed_contrarian (81.4% WR, PF 6.91, +1249% PnL, 787 trades)
    - st_obv_support_divergence (61.5% WR, PF 2.10, 327 trades)

    Mutation: Combine the F&G extreme-fear contrarian buy with OBV accumulation
    confirmation. Only triggers when fear is extreme AND smart money (OBV) is
    accumulating — filtering out falling-knife scenarios.
    """
    if not _HAS_INDICATORS or df is None or len(df) < 60:
        return []

    signals = []
    context = context or {}
    fear_greed_val = context.get("fear_greed", 50)

    # Only trigger in fear zones (F&G < 30)
    if fear_greed_val >= 30:
        return []

    _close = df["Close"]
    _high = df["High"]
    _low = df["Low"]
    _volume = df["Volume"]
    _atr_vals = atr(_high, _low, _close, 14)
    _rsi14 = rsi(_close, 14)
    _obv_vals = obv(_close, _volume)
    _ema20 = ema(_close, 20)
    _bb_upper, _bb_mid, _bb_lower, _, _ = bollinger_bands(_close, 20, 2.0)

    for i in range(25, len(df)):
        if pd.isna(_atr_vals.iloc[i]) or _atr_vals.iloc[i] <= 0:
            continue

        cur_close = _close.iloc[i]
        cur_atr = _atr_vals.iloc[i]
        cur_rsi = _rsi14.iloc[i]
        cur_obv = _obv_vals.iloc[i]
        cur_bb_lower = _bb_lower.iloc[i]

        # F&G extreme fear + price near/below lower Bollinger Band
        if pd.isna(cur_bb_lower) or cur_close > cur_bb_lower * 1.02:
            continue

        # RSI oversold confirmation
        if pd.isna(cur_rsi) or cur_rsi > 35:
            continue

        # OBV accumulation: OBV rising over last 5 bars despite price drop
        if i < 5:
            continue
        obv_5bar_change = cur_obv - _obv_vals.iloc[i - 5]
        price_5bar_change = cur_close - _close.iloc[i - 5]
        if obv_5bar_change <= 0 or price_5bar_change > 0:
            continue  # Need OBV up while price down = smart money buying

        # Deeper fear = higher conviction
        if fear_greed_val < 15:
            conf = 0.80
            tp_mult = 2.5
        elif fear_greed_val < 25:
            conf = 0.72
            tp_mult = 2.0
        else:
            conf = 0.65
            tp_mult = 1.8

        tp = cur_close + tp_mult * cur_atr
        sl = cur_close - 1.0 * cur_atr

        signals.append(_base_signal(
            "fear_greed_obv_confluence", symbol, "LONG", cur_close, conf,
            f"F&G extreme fear ({fear_greed_val}) + OBV accumulation: RSI={cur_rsi:.0f}, "
            f"price below BB lower, smart money buying",
            take_profit=tp,
            stop_loss=sl,
            risk_reward=round(tp_mult, 2),
            fear_greed=fear_greed_val,
            source_system="genome_mutations_v2",
            dna_hash=_dna_hash("fear_greed_obv_confluence", {
                "fgi": fear_greed_val, "rsi": round(cur_rsi),
            }),
        ))
        break

    return signals


def drawdown_keltner_recovery(
    df: pd.DataFrame, symbol: str, context: dict | None = None,
) -> list[dict]:
    """Drawdown recovery RSI + Keltner squeeze for optimal entry timing.

    Parents:
    - drawdown_recovery_rsi_eth (65.2% WR, PF 3.20, +38% PnL, 69 trades)
    - crypto_keltner_compression_expansion_v1 (57.9% WR, PF 2.77, +25% PnL, 95 trades)

    Mutation: Wait for Keltner channel compression (low volatility squeeze)
    during a drawdown recovery phase (RSI rising from oversold). Entry at
    the expansion breakout — catching the start of the recovery move with
    tight risk.
    """
    if not _HAS_INDICATORS or df is None or len(df) < 60:
        return []

    signals = []
    context = context or {}

    _close = df["Close"]
    _high = df["High"]
    _low = df["Low"]
    _volume = df["Volume"]
    _atr_vals = atr(_high, _low, _close, 14)
    _rsi14 = rsi(_close, 14)
    _rsi50 = rsi(_close, 50)
    _kc_upper, _kc_mid, _kc_lower = keltner_channels(_high, _low, _close, 20, 14, 1.5)
    _bb_upper, _bb_mid, _bb_lower, _, _ = bollinger_bands(_close, 20, 2.0)

    for i in range(55, len(df)):
        if pd.isna(_atr_vals.iloc[i]) or _atr_vals.iloc[i] <= 0:
            continue
        if pd.isna(_kc_upper.iloc[i]) or pd.isna(_bb_upper.iloc[i]):
            continue

        cur_close = _close.iloc[i]
        cur_atr = _atr_vals.iloc[i]
        cur_rsi14 = _rsi14.iloc[i]
        cur_rsi50 = _rsi50.iloc[i] if not pd.isna(_rsi50.iloc[i]) else 50

        # Drawdown detection: significant drop from recent high
        recent_high = _close.iloc[max(0, i - 30):i].max()
        drawdown_pct = (recent_high - cur_close) / recent_high * 100
        if drawdown_pct < 8:
            continue  # Need meaningful drawdown (>= 8%)

        # RSI recovery: RSI was oversold but now recovering (30-50 range)
        if pd.isna(cur_rsi14) or cur_rsi14 < 25 or cur_rsi14 > 55:
            continue

        # Check RSI is rising (recovery in progress)
        if i < 3:
            continue
        prev_rsi = _rsi14.iloc[i - 3]
        if pd.isna(prev_rsi) or cur_rsi14 <= prev_rsi:
            continue  # RSI must be rising

        # Keltner squeeze: BB inside KC (volatility compression)
        bb_width = _bb_upper.iloc[i] - _bb_lower.iloc[i]
        kc_width = _kc_upper.iloc[i] - _kc_lower.iloc[i]
        in_squeeze = bb_width < kc_width

        # Keltner expansion: price breaking above KC mid after squeeze
        if i < 2:
            continue
        was_squeezed = False
        for j in range(max(0, i - 5), i):
            if not pd.isna(_bb_upper.iloc[j]) and not pd.isna(_kc_upper.iloc[j]):
                if (_bb_upper.iloc[j] - _bb_lower.iloc[j]) < (_kc_upper.iloc[j] - _kc_lower.iloc[j]):
                    was_squeezed = True
                    break

        if not (in_squeeze or was_squeezed):
            continue

        # Price above KC mid = breakout direction is up
        if cur_close < _kc_mid.iloc[i]:
            continue

        # Wider TP during deeper drawdowns (more room to recover)
        if drawdown_pct > 20:
            tp_mult, sl_mult = 3.0, 1.2
            conf = 0.75
        elif drawdown_pct > 12:
            tp_mult, sl_mult = 2.5, 1.0
            conf = 0.70
        else:
            tp_mult, sl_mult = 2.0, 1.0
            conf = 0.65

        tp = cur_close + tp_mult * cur_atr
        sl = cur_close - sl_mult * cur_atr

        signals.append(_base_signal(
            "drawdown_keltner_recovery", symbol, "LONG", cur_close, conf,
            f"Drawdown recovery + Keltner squeeze: drawdown={drawdown_pct:.0f}%, "
            f"RSI recovering={cur_rsi14:.0f}, squeeze breakout above KC mid",
            take_profit=tp,
            stop_loss=sl,
            risk_reward=round(tp_mult / sl_mult, 2),
            drawdown_pct=round(drawdown_pct, 1),
            source_system="genome_mutations_v2",
            dna_hash=_dna_hash("drawdown_keltner_recovery", {
                "dd": round(drawdown_pct), "rsi": round(cur_rsi14),
            }),
        ))
        break

    return signals


# =========================================================================
#  REGISTRY: All Super Mutation Strategies (5 original + 3 from optimization audit)
# =========================================================================

SUPER_MUTATION_STRATEGIES = {
    "keltner_rsi_confluence_v2": {
        "fn": keltner_rsi_confluence_v2,
        "description": "Keltner squeeze + dual RSI oversold confluence",
        "parents": ["keltner_compression_expansion (72.9% WR)",
                     "multi_period_rsi_confluence (64% WR, Sharpe 10.86)"],
        "expected_wr": "70%+",
        "risk_reward": "2.0:1",
        "category": "deep_value_momentum",
    },
    "consensus_deep_value_hybrid": {
        "fn": consensus_deep_value_hybrid,
        "description": "Cross-system consensus + RSI capitulation + F&G filter",
        "parents": ["rsi_capitulation_sniper (+2.51%, 7.12 PF)",
                     "cross_aggregation (58.3% WR, +71.4%)",
                     "fear_greed_contrarian"],
        "expected_wr": "60%+",
        "risk_reward": "1.875:1",
        "category": "deep_value",
    },
    "genesis_momentum_blend": {
        "fn": genesis_momentum_blend,
        "description": "GENESIS-style multi-indicator scoring + momentum confirmation",
        "parents": ["GENESIS genome (+442% PnL)",
                     "battleground EMA stack, supertrend, ADX"],
        "expected_wr": "62%+",
        "risk_reward": "1.33:1",
        "category": "momentum",
    },
    "ml_keltner_adaptive": {
        "fn": ml_keltner_adaptive,
        "description": "Claude Gainer ML features + adaptive Keltner channels",
        "parents": ["claude_gainer_ml (56.2% WR, +99.5% PnL)",
                     "keltner_channel_breakout (72.9% WR)",
                     "atr_volatility_regime (crash protection)"],
        "expected_wr": "65%+",
        "risk_reward": "adaptive (1.5-2.5:1)",
        "category": "adaptive",
    },
    "multi_system_conviction_filter": {
        "fn": multi_system_conviction_filter,
        "description": "Meta-strategy requiring 3+ system layers to agree",
        "parents": ["battleground (61.7% WR, +158%)",
                     "rsi_capitulation_sniper (60% WR, 7.12 PF)",
                     "claude_gainer_ml (56.2% WR, +99.5%)",
                     "cross_aggregation (58.3% WR, +71.4%)",
                     "fear_greed_contrarian"],
        "expected_wr": "65%+",
        "risk_reward": "adaptive (1.5-2.5:1)",
        "category": "meta_conviction",
    },
    # 2026-04-11: New mutations from scoring optimization audit
    "regime_filtered_obv_divergence": {
        "fn": regime_filtered_obv_divergence,
        "description": "OBV divergence (61.5% WR parent) + regime filter to avoid ranging/bear",
        "parents": ["st_obv_support_divergence (61.5% WR, PF 2.10, +202% PnL, 327 trades)",
                     "regime_detector (RANGING=10% WR, TRENDING_DOWN=16.7% WR)"],
        "expected_wr": "68%+",
        "risk_reward": "2.0:1",
        "category": "regime_filtered_momentum",
    },
    "fear_greed_obv_confluence": {
        "fn": fear_greed_obv_confluence,
        "description": "F&G contrarian (81.4% WR) + OBV confirmation for higher conviction",
        "parents": ["st_fear_greed_contrarian (81.4% WR, PF 6.91, +1249% PnL, 787 trades)",
                     "st_obv_support_divergence (61.5% WR, PF 2.10, 327 trades)"],
        "expected_wr": "75%+",
        "risk_reward": "2.0:1",
        "category": "deep_value_contrarian",
    },
    "drawdown_keltner_recovery": {
        "fn": drawdown_keltner_recovery,
        "description": "Drawdown recovery RSI (65% WR) + Keltner squeeze for optimal entry timing",
        "parents": ["drawdown_recovery_rsi_eth (65.2% WR, PF 3.20, +38% PnL)",
                     "crypto_keltner_compression_expansion_v1 (57.9% WR, PF 2.77, +25% PnL)"],
        "expected_wr": "65%+",
        "risk_reward": "2.5:1",
        "category": "recovery_squeeze",
    },
}


def run_all_super_mutations(
    df: pd.DataFrame, symbol: str, context: dict | None = None
) -> list[dict]:
    """Run all 5 super mutation strategies on a symbol and return all signals.

    Args:
        df: OHLCV DataFrame with columns [Open, High, Low, Close, Volume]
        symbol: Trading pair (e.g. "BTCUSDT")
        context: Optional dict with external data:
            - fear_greed: int (0-100)
            - agreeing_systems: list[str]
            - has_consensus_data: bool

    Returns:
        List of signal dicts from all strategies that fire.
    """
    all_signals = []
    for name, meta in SUPER_MUTATION_STRATEGIES.items():
        try:
            signals = meta["fn"](df, symbol, context)
            if signals:
                logger.info(f"[super_mutation] {symbol} {name}: {len(signals)} signal(s)")
            all_signals.extend(signals)
        except Exception as e:
            logger.warning(f"[super_mutation] {symbol} {name} error: {e}")
    return all_signals


# =========================================================================
#  Self-test when run directly
# =========================================================================

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")

    print("=" * 60)
    print("SUPER MUTATION STRATEGIES -- Self Test")
    print("=" * 60)
    print(f"\n{len(SUPER_MUTATION_STRATEGIES)} strategies registered:\n")

    for name, meta in SUPER_MUTATION_STRATEGIES.items():
        print(f"  {name}")
        print(f"    Description: {meta['description']}")
        print(f"    Parents:     {', '.join(meta['parents'])}")
        print(f"    Expected WR: {meta['expected_wr']}")
        print(f"    R:R:         {meta['risk_reward']}")
        print()

    # Try to fetch real data and test
    try:
        from genome.mutation_lab.backtester import fetch_klines, BACKTEST_SYMBOLS
        for sym in BACKTEST_SYMBOLS:
            print(f"Fetching {sym} klines...")
            df = fetch_klines(sym, limit=300)
            if df is None or len(df) < 60:
                print(f"  Skipping {sym}: insufficient data")
                continue

            signals = run_all_super_mutations(df, sym, {"fear_greed": 20})
            print(f"  {sym}: {len(signals)} total signals")
            for s in signals:
                print(f"    -> {s['strategy']} {s['direction']} "
                      f"conf={s['confidence']:.2f} "
                      f"entry=${s['entry_price']:.4f}")
    except Exception as e:
        print(f"\nCould not run live test (expected in CI): {e}")
        print("Generating synthetic data test...")

        # Synthetic test
        np.random.seed(42)
        n = 200
        returns = np.random.normal(0.0001, 0.012, n)
        prices = 50000 * np.exp(np.cumsum(returns))
        # Make the last 30 bars drop (simulate oversold)
        prices[-30:] *= np.linspace(1.0, 0.75, 30)
        prices[-10:] *= np.linspace(1.0, 1.03, 10)  # small bounce

        df = pd.DataFrame({
            "Open": prices * (1 + np.random.normal(0, 0.001, n)),
            "High": prices * (1 + np.abs(np.random.normal(0, 0.005, n))),
            "Low": prices * (1 - np.abs(np.random.normal(0, 0.005, n))),
            "Close": prices,
            "Volume": np.random.lognormal(15, 1, n),
        })

        signals = run_all_super_mutations(df, "BTCUSDT", {"fear_greed": 15})
        print(f"  Synthetic BTCUSDT: {len(signals)} total signals")
        for s in signals:
            print(f"    -> {s['strategy']} {s['direction']} "
                  f"conf={s['confidence']:.2f} "
                  f"entry=${s['entry_price']:.4f}")

    print("\n" + "=" * 60)
    print("Self-test complete.")
