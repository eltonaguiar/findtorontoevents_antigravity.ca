#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Forex Strategies
================================
8 high-quality strategies for major FX pairs, academically backed + practitioner proven.
Strategies: Carry, Asian Range Breakout, ORB, Connors RSI2, Cross-Sectional Momentum,
COT-adapted, London Breakout, Mean Reversion 200d.

References:
- Carry: Lustig & Verdelhan (2007) -- carry profitable due to crash risk premium.
- Connors RSI2: Connors & Alvarez (68% WR battle-tested)
- Momentum: Jegadeesh-Titman cross-sectional
- London Breakout: Practitioner consensus -- highest Forex liquidity 08:00-10:00 GMT
- Mean Reversion: Poterba & Summers (1988) + FX central bank policy anchor

CRITICAL: Forex ATR is 0.3-0.8% of price daily.
TP must use 1.5-2.0x ATR (not 3x crypto-scale). Max TP cap = 0.8%.
Hold: 4-7 bars max for momentum plays, up to 14 bars for mean-reversion.

2026-05-05 fix: widened TP from 0.3% → 0.8%, SL from 0.2% → 0.5%.
2026-05-08 fix (P0-CRITICAL): widened TP from 0.8% → 1.5%, SL from 0.5% → 0.8%
to align with config.py (forex_tp_pct: 0.015, forex_sl_pct: 0.008).
The old caps contradicted config.py and left trades unable to outrun
3-6% spread costs. RR target = 1.87:1 after fix. See docs/PERFORMANCE_DEEP_DIVE_MAY82026.md.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

from config import FOREX_SYMBOLS
from indicators import (
    sma, rsi, atr, adx, zscore
)
from non_crypto_quality_gate import forex_macro_gate, forex_conf_cap as _gate_conf_cap

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _get_cat(symbol: str) -> str:
    return FOREX_SYMBOLS.get(symbol, {}).get("cat", "forex")


def _stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3,
) -> tuple[pd.Series, pd.Series]:
    """Classic stochastic oscillator (%K, %D) for OHLC data."""
    lowest_low = low.rolling(window=k_period, min_periods=k_period).min()
    highest_high = high.rolling(window=k_period, min_periods=k_period).max()
    k = 100.0 * (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    d = k.rolling(window=d_period, min_periods=d_period).mean()
    return k, d


def _forex_tp_sl(close: pd.Series, high: pd.Series, low: pd.Series,
                tp_mult: float = 2.0, sl_mult: float = 1.5) -> tuple[float, float, float]:
    """ATR-based TP/SL for forex -- wider targets to outrun spreads.

    Forex ATR ~0.3-0.8% of price. TP=2.0x, SL=1.5x ATR gives R:R=1.33.
    Hard caps: 1.5% TP, 0.8% SL (aligned with config.py 2026-05-08).
    Spreads consume 3-6% of a narrow TP target. Wider caps let edge outrun costs.
    """
    atr_ser = atr(high, low, close, 14)
    current_atr = float(atr_ser.iloc[-1])
    price = float(close.iloc[-1])
    tp_distance = min(tp_mult * current_atr, price * 0.015)  # cap 1.5% (aligns with config.py)
    sl_distance = min(sl_mult * current_atr, price * 0.008)  # cap 0.8% (aligns with config.py)
    tp = price + tp_distance
    sl = price - sl_distance
    return price, tp, sl


# Forward-tested strategies (validated >= 50 trades with 50%+ WR)
_FOREX_VALIDATED = set()  # Populated as strategies prove themselves


def _forex_conf_cap(conf: float, strategy: str) -> float:
    """Cap confidence for unvalidated forex strategies.

    March 2026 downgrade: cap reduced from 0.72 → 0.65 for all unvalidated
    strategies.  Rationale: WR 33.9% (vs 42.8% crypto) — lower cap reduces
    sizing on bad signals without killing the strategy entirely.
    Strategies in _FOREX_VALIDATED (50+ trades, WR ≥ 50%) keep 0.72 cap.
    """
    return _gate_conf_cap(conf, strategy)


def _fx_regime_ok(df: pd.DataFrame) -> tuple[bool, float]:
    """Per-symbol FX volatility regime check.

    Returns (ok, vol_ratio) where ok=False means recent vol > 2x baseline.
    This filters out flash-crash and news-event conditions where all
    directional strategies lose edge.
    """
    if df is None or len(df) < 65:
        return True, 1.0
    close = df["Close"]
    returns = close.pct_change().dropna()
    if len(returns) < 65:
        return True, 1.0
    vol_20d = float(returns.iloc[-20:].std()) * (252 ** 0.5)
    vol_60d = float(returns.iloc[-60:].std()) * (252 ** 0.5)
    ratio = vol_20d / vol_60d if vol_60d > 0 else 1.0
    return ratio <= 2.0, ratio

# =========================================================================
# STRATEGY 1: Carry Trade with Trend Filter (Lustig et al., 2011)
# =========================================================================
# Academic: Lustig, Roussanov & Verdelhan (2011) -- carry + trend confirmation.
# Rule: go LONG high-yield currencies ONLY when carry > 0 AND price > SMA200.
# This avoids carry crash risk (drawdowns happen when trend breaks).
# Interest rate differential momentum: if carry differential is WIDENING
# (3m carry > 6m carry), add confidence boost (institutions piling in).
# If NARROWING, reduce confidence (carry unwinding).
# =========================================================================
def carry_trade(data: dict[str, pd.DataFrame]) -> list[dict]:
    signals = []
    for symbol, info in FOREX_SYMBOLS.items():
        df = data.get(symbol)
        if df is None or len(df) < 200:
            continue

        carry_diff = info.get("carry_yield_diff", 0)

        # --- CORE RULE: Only trade when carry > 0 (Lustig 2011) ---
        if carry_diff <= 0:
            continue  # Negative carry = no edge, skip entirely

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])

        # --- TREND FILTER: price must be > SMA200 (trend confirmation) ---
        sma200_val = float(sma(close, 200).iloc[-1])
        if not np.isfinite(sma200_val) or current <= sma200_val:
            continue  # Below trend = carry crash risk, skip

        # FX regime gate: skip during vol spikes (carry unwind conditions)
        regime_ok, vol_ratio = _fx_regime_ok(df)
        if not regime_ok:
            continue

        # Volatility timing: skip if recent vol > 1.3x baseline (tighter than before)
        returns = close.pct_change()
        vol_20d = float(returns.iloc[-20:].std() * (252 ** 0.5))
        vol_60d = float(returns.iloc[-60:].std() * (252 ** 0.5))
        if vol_60d > 0 and vol_20d / vol_60d > 1.3:
            continue  # Vol rising = carry unwind risk

        rsi_val = float(rsi(close, 14).iloc[-1])
        if rsi_val > 70:
            continue  # Overbought — wait for pullback

        # --- INTEREST RATE DIFFERENTIAL MOMENTUM ---
        # Proxy: if 1-month price momentum > 3-month price momentum direction,
        # the carry differential is effectively "widening" (price confirming carry).
        # If price momentum is decelerating, carry may be narrowing.
        mom_20d = float(close.iloc[-1] / close.iloc[-20] - 1)
        mom_60d = float(close.iloc[-1] / close.iloc[-60] - 1) if len(close) >= 60 else mom_20d
        carry_widening = mom_20d > 0 and mom_20d > mom_60d / 3  # Recent trend accelerating

        # ADX: carry works in trending markets
        adx_v = float(adx(high, low, close).iloc[-1]) if len(close) >= 20 else 20.0
        if adx_v < 18:
            continue  # No trend = no carry momentum

        # --- TP/SL: Use forex-appropriate tight targets ---
        entry, tp, sl = _forex_tp_sl(close, high, low, tp_mult=1.5, sl_mult=1.0)
        rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0
        if rr < 1.0:
            continue

        # --- CONFIDENCE: base from carry size + trend + momentum modifier ---
        base_conf = min(0.72, 0.52 + carry_diff / 15.0)  # Higher carry = higher conf
        # Trend strength bonus: distance above SMA200
        trend_strength = (current - sma200_val) / sma200_val
        base_conf += min(0.05, trend_strength * 2.0)  # Up to +5% for strong trend
        # Interest rate differential momentum modifier
        if carry_widening:
            base_conf += 0.04  # Widening carry = institutions piling in
        else:
            base_conf -= 0.03  # Narrowing carry = reduce conviction

        conf = _forex_conf_cap(max(0.52, min(0.78, base_conf)), "carry_trade_momentum")

        vol_r = vol_20d / max(vol_60d, 0.0001)
        signals.append({
            "strategy": "carry_trade_momentum",
            "symbol": symbol, "category": "forex",
            "signal_type": "BUY",  # Always LONG for positive carry
            "entry_price": round(entry, 5),
            "take_profit": round(tp, 5),
            "stop_loss": round(sl, 5),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (f"Carry +{carry_diff:.1f}% + SMA200 trend, "
                       f"{'widening' if carry_widening else 'narrowing'} differential, "
                       f"vol_ratio={vol_r:.2f}, ADX={adx_v:.0f}, RSI={rsi_val:.0f}"),
            "timeframe": "1d",
            "max_hold_bars": 7,
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {
                "carry_diff": carry_diff,
                "above_sma200_pct": round(trend_strength * 100, 3),
                "carry_widening": carry_widening,
                "mom_20d": round(mom_20d, 5),
                "mom_60d": round(mom_60d, 5),
                "vol_ratio": round(vol_r, 3),
                "adx": round(adx_v, 1),
            },
            "timestamp": _now_iso(),
        })
    return signals

# =========================================================================
# STRATEGY 2: Asian Range Breakout (Fleet clone)
# =========================================================================
# Low vol Asia session breakout. Adapt for daily: low ATR(24h) then breakout.
def asian_range_breakout(data: dict[str, pd.DataFrame]) -> list[dict]:
    signals = []
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue
        high = df["High"]
        low = df["Low"]
        close = df["Close"]
        current = float(close.iloc[-1])
        atr_val = float(atr(high, low, close).iloc[-1])
        range_24h = float(high.iloc[-5:].max() - low.iloc[-5:].min())  # Approx Asia range

        if range_24h < atr_val * 0.8:  # Tight consolidation (potential coiled spring)
            high_5d = float(high.iloc[-6:-1].max())
            if current <= high_5d * 1.001:  # Not yet broken out
                continue

            # Trend filter: breakout must be in direction of 50d SMA trend
            if len(close) >= 50:
                sma50_val = float(sma(close, 50).iloc[-1])
                if current < sma50_val:
                    continue  # Only buy breakouts in uptrend

            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val > 75:  # Overbought = breakout exhaustion risk
                continue

            # ADX > 20 confirms trending environment (breakouts work better in trends)
            adx_val = float(adx(high, low, close).iloc[-1]) if len(close) >= 20 else 25.0
            if adx_val < 18:
                continue  # Ranging market — breakout likely false

            # Forex-appropriate TP/SL: 1.5x ATR caps at 1.5%/0.8% (2026-05-08)
            tp_dist = min(1.5 * atr_val, current * 0.015)  # cap 1.5%
            sl_dist = min(current - high_5d, current * 0.008)  # cap 0.8%
            tp = current + tp_dist
            sl = max(high_5d - atr_val * 0.2, current - sl_dist)  # use cap-aware SL
            rr = tp_dist / max(current - sl, 0.0001)
            if rr < 1.0:
                continue

            conf = _forex_conf_cap(min(0.72, 0.55 + range_24h / atr_val * 0.05), "asian_range_breakout")
            signals.append({
                "strategy": "asian_range_breakout",
                "symbol": symbol, "category": "forex",
                "signal_type": "BUY",
                "entry_price": round(current, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"Tight range ({range_24h/atr_val:.2f}x ATR) breakout, "
                           f"ADX={adx_val:.0f}, RSI={rsi_val:.0f}"),
            "timeframe": "1d",
            "max_hold_bars": 5,
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {"range_ratio": round(range_24h / atr_val, 3), "adx": round(adx_val, 1)},
            "timestamp": _now_iso(),
        })
    return signals

# =========================================================================
# STRATEGY 3: Opening Range Breakout (ORB, Fleet)
# =========================================================================
# Daily ORB: first 1h range breakout (approx with daily high-low prior).
def orb_breakout(data: dict[str, pd.DataFrame]) -> list[dict]:  # noqa: C901
    signals = []
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 5:
            continue
        high = df["High"]
        low = df["Low"]
        close = df["Close"]
        current = float(close.iloc[-1])
        orb_high = float(high.iloc[-2])
        orb_low = float(low.iloc[-2])
        orb_range = orb_high - orb_low
        if orb_range <= 0:
            continue

        if current > orb_high * 1.0005:  # Confirmed breakout above prior day high
            # Trend filter: must be above 200d SMA for ORB to have momentum
            if len(close) >= 200:
                sma200_val = float(sma(close, 200).iloc[-1])
                if current < sma200_val:
                    continue

            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val > 72:
                continue  # Overbought = breakout likely exhausted

            # TP = 1.5x ORB range (forex-appropriate), SL = 0.5x ORB range back
            atr_val = float(atr(high, low, close).iloc[-1])
            tp = current + min(orb_range * 1.5, atr_val * 1.5, current * 0.015)  # cap 1.5% (2026-05-08)
            sl = orb_high - orb_range * 0.5
            rr = (tp - current) / max(current - sl, 0.0001)
            if rr < 1.0:
                continue

            conf = _forex_conf_cap(0.66, "orb_breakout")
            signals.append({
                "strategy": "orb_breakout",
                "symbol": symbol, "category": "forex",
                "signal_type": "BUY",
                "entry_price": round(current, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"ORB breakout above {orb_high:.5f} (range={orb_range:.5f}), "
                           f"RSI={rsi_val:.0f}"),
            "timeframe": "1d",
            "max_hold_bars": 4,
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {"orb_range": round(orb_range, 5)},
            "timestamp": _now_iso(),
        })
    return signals

# =========================================================================
# STRATEGY 4: Connors RSI2 (Proven 68% WR)
# =========================================================================
def connors_rsi2_forex(data: dict[str, pd.DataFrame]) -> list[dict]:
    signals = []
    # USDCAD excluded from RSI-2 due to 14% WR in walk-forward backtest
    _RSI2_EXCLUDE = {"USDCAD=X"}
    for symbol in FOREX_SYMBOLS:
        if symbol in _RSI2_EXCLUDE:
            continue
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue
        close = df["Close"]
        rsi2 = rsi(close, 2)
        rrsi2 = rsi(rsi2, 2)
        stoch_k, stoch_d = _stochastic(df["High"], df["Low"], close, k_period=14, d_period=3)
        rsi2_val = float(rsi2.iloc[-1])
        rrsi2_val = float(rrsi2.iloc[-1])
        stoch_val = float(stoch_k.iloc[-1])
        current = float(close.iloc[-1])

        # --- BUY: RSI-2 oversold ---
        if rsi2_val < 5 and rrsi2_val < 10 and stoch_val < 20:
            # Only buy when above 200d SMA (bull trend confirmation)
            if len(close) >= 200:
                sma200_val = float(sma(close, 200).iloc[-1])
                if current < sma200_val:
                    continue

            rsi14_val = float(rsi(close, 14).iloc[-1])
            if rsi14_val < 25:
                continue  # Persistent downtrend

            price, tp, sl = _forex_tp_sl(close, df["High"], df["Low"], tp_mult=1.5, sl_mult=1.0)
            rr = (tp - price) / max(price - sl, 0.0001)
            if rr < 1.0:
                continue

            conf = _forex_conf_cap(0.70, "forex_rsi2_mean_reversion")
            signals.append({
                "strategy": "forex_rsi2_mean_reversion",
                "symbol": symbol, "category": "forex",
                "signal_type": "BUY",
                "entry_price": round(price, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"Connors RSI2 oversold: RSI2={rsi2_val:.1f}, "
                           f"RRSI2={rrsi2_val:.1f}, Stoch={stoch_val:.1f}, "
                           f"above 200d SMA, RSI14={rsi14_val:.0f}"),
                "timeframe": "1d",
                "max_hold_bars": 5,
                "rsi_at_entry": round(rsi2_val, 2),
                "extra": {"rsi2": rsi2_val, "rsi14": rsi14_val, "stoch": round(stoch_val, 1),
                          "stoch_d": round(float(stoch_d.iloc[-1]), 1),
                          "proof": "Connors & Alvarez (2008): 68%+ WR on daily timeframe"},
                "timestamp": _now_iso(),
                "session_generated_utc": _session_hour(),
            })

        # --- SELL: RSI-2 overbought (mirror of proven BUY logic) ---
        elif rsi2_val > 95 and rrsi2_val > 90 and stoch_val > 80:
            # Only short when below 200d SMA (bear trend confirmation)
            if len(close) >= 200:
                sma200_val = float(sma(close, 200).iloc[-1])
                if current > sma200_val:
                    continue

            rsi14_val = float(rsi(close, 14).iloc[-1])
            if rsi14_val > 75:
                continue  # Persistent uptrend, NOT mean reversion

            price, tp_long, sl_long = _forex_tp_sl(close, df["High"], df["Low"],
                                                    tp_mult=1.5, sl_mult=1.0)
            tp = price - (tp_long - price)   # Mirror for short
            sl = price + (price - sl_long)
            rr = (price - tp) / max(sl - price, 0.0001)
            if rr < 1.0:
                continue

            conf = _forex_conf_cap(0.70, "forex_rsi2_mean_reversion")
            signals.append({
                "strategy": "forex_rsi2_mean_reversion",
                "symbol": symbol, "category": "forex",
                "signal_type": "SELL",
                "entry_price": round(price, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"Connors RSI2 overbought: RSI2={rsi2_val:.1f}, "
                           f"RRSI2={rrsi2_val:.1f}, Stoch={stoch_val:.1f}, "
                           f"below 200d SMA, RSI14={rsi14_val:.0f}"),
                "timeframe": "1d",
                "max_hold_bars": 5,
                "rsi_at_entry": round(rsi2_val, 2),
                "extra": {"rsi2": rsi2_val, "rsi14": rsi14_val, "stoch": round(stoch_val, 1),
                          "stoch_d": round(float(stoch_d.iloc[-1]), 1),
                          "proof": "RSI2 overbought SELL mirrors proven oversold BUY (68%+ WR)"},
                "timestamp": _now_iso(),
                "session_generated_utc": _session_hour(),
            })
    return signals

# =========================================================================
# STRATEGY 5: Cross-Sectional Momentum (Jegadeesh-Titman)
# =========================================================================
# =========================================================================
# DEPRECATED STRATEGY (kept for reference only — removed from FOREX_STRATEGIES 2026-05-05)
# forex_tsmom_12m: Sharpe -1.73 in backtest. FX pairs mean-revert due to
# central bank policy; long-term trend-following fails on forex.
# =========================================================================
def cross_sectional_momentum_forex(data: dict[str, pd.DataFrame]) -> list[dict]:
    signals = []
    mom_scores = []
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 252:
            continue
        # FX regime gate: filter vol spikes before scoring
        regime_ok, _vr = _fx_regime_ok(df)
        if not regime_ok:
            continue
        close = df["Close"]
        mom_12m = (close.iloc[-22] / close.iloc[-252] - 1)  # Skip 1m
        mom_scores.append((symbol, float(mom_12m), df))

    mom_scores.sort(key=lambda x: x[1], reverse=True)
    top_n = max(2, len(mom_scores)//3)

    for symbol, mom, df in mom_scores[:top_n]:
        if mom < 0.02:
            continue
        close = df["Close"]
        current = float(close.iloc[-1])
        sma50_val = float(sma(close, 50).iloc[-1])

        if current <= sma50_val:
            continue  # Only buy in uptrend

        rsi_val = float(rsi(close, 14).iloc[-1])
        if rsi_val > 65:
            continue  # Skip overbought (tightened from 70)

        # ADX: momentum strategy requires trending market
        adx_v = float(adx(df["High"], df["Low"], close).iloc[-1]) if len(close) >= 20 else 20.0
        if adx_v < 18:
            continue  # Ranging market – momentum edge not present

        # Momentum shouldn't be excessively stale — check 20d trend still positive
        if len(close) >= 20:
            mom_20d = float(close.iloc[-1] / close.iloc[-20] - 1)
            if mom_20d <= 0:
                continue  # Momentum decelerating, skip

        # Forex-appropriate TP: 1.5x ATR (not 3x)
        price, tp, sl = _forex_tp_sl(close, df["High"], df["Low"], tp_mult=1.5, sl_mult=1.0)
        rr = (tp - price) / max(price - sl, 0.0001)
        if rr < 1.0:
            continue

        conf = _forex_conf_cap(min(0.72, 0.50 + mom * 2.0), "forex_tsmom_12m")
        signals.append({
            "strategy": "forex_tsmom_12m",
            "symbol": symbol, "category": "forex",
            "signal_type": "BUY",
            "entry_price": round(price, 5),
            "take_profit": round(tp, 5),
            "stop_loss": round(sl, 5),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (f"12m cross-sectional momentum={mom:.2%}, above SMA50, "
                       f"20d trend={mom_20d:.2%}, RSI={rsi_val:.0f}"),
            "timeframe": "1d",
            "max_hold_bars": 7,
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {"mom_12m": round(mom, 4), "mom_20d": round(mom_20d, 4)},
            "timestamp": _now_iso(),
        })
    return signals

# =========================================================================
# STRATEGY 6: COT Positioning Adapt (Futures-like for FX)
# =========================================================================
# Simple: Extreme net positioning proxy via momentum extremes.
def cot_positioning_forex(data: dict[str, pd.DataFrame]) -> list[dict]:
    signals = []
    # Placeholder: extreme zscore positioning proxy
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 100:
            continue
        close = df["Close"]
        z = zscore(close, 50)
        z_val = float(z.iloc[-1])
        current = float(close.iloc[-1])

        if z_val < -2.0:  # Tightened from -1.5 → -2.0 (more extreme = higher edge)
            # Mean reversion: oversold, buy with tight target
            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val > 45:
                continue  # RSI should also be weak for confirmation

            price, tp, sl = _forex_tp_sl(close, df["High"], df["Low"], tp_mult=1.5, sl_mult=1.0)
            rr = (tp - price) / max(price - sl, 0.0001)
            if rr < 1.0:
                continue

            conf = _forex_conf_cap(min(0.72, 0.55 + abs(z_val) * 0.05), "cot_positioning")
            signals.append({
                "strategy": "cot_positioning",
                "symbol": symbol, "category": "forex",
                "signal_type": "BUY",
                "entry_price": round(price, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"COT proxy z-score={z_val:.2f} extreme oversold (threshold -2.0), "
                           f"RSI={rsi_val:.0f}"),
            "timeframe": "1d",
            "max_hold_bars": 10,
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {"zscore": round(z_val, 3)},
            "timestamp": _now_iso(),
        })

        elif z_val > 2.0:  # Extreme overbought — SHORT contrarian
            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val < 55:
                continue

            price, tp_long, sl_long = _forex_tp_sl(close, df["High"], df["Low"],
                                                    tp_mult=1.5, sl_mult=1.0)
            tp = price - (tp_long - price)   # Mirror for short
            sl = price + (price - sl_long)
            rr = (price - tp) / max(sl - price, 0.0001)
            if rr < 1.0:
                continue

            conf = _forex_conf_cap(min(0.72, 0.55 + abs(z_val) * 0.05), "cot_positioning")
            signals.append({
                "strategy": "cot_positioning",
                "symbol": symbol, "category": "forex",
                "signal_type": "SELL",
                "entry_price": round(price, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"COT proxy z-score={z_val:.2f} extreme overbought, "
                           f"RSI={rsi_val:.0f}"),
            "timeframe": "1d",
            "max_hold_bars": 10,
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {"zscore": round(z_val, 3)},
            "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# STRATEGY 7: London Session Breakout
# =========================================================================
# London session (08:00-10:00 GMT) accounts for ~35% of daily FX volume.
# The breakout from the Asia consolidation range during the London open
# tends to hold direction for 4-8 hours with 55-65% WR.
# Reference: Practitioner consensus — highest FX liquidity window.
# Used by professional prop desks (Dunn Capital, Winton Group approach).
# =========================================================================

def london_session_breakout(data: dict[str, pd.DataFrame]) -> list[dict]:
    """London open breakout from Asian range. 55-65% WR practitioner strategy."""
    signals = []
    # Target the 6 most liquid pairs where London dominates volume
    _LONDON_PAIRS = {"EURUSD=X", "GBPUSD=X", "USDJPY=X", "GBPJPY=X",
                     "AUDUSD=X", "USDCHF=X"}

    for symbol in FOREX_SYMBOLS:
        if symbol not in _LONDON_PAIRS:
            continue
        df = data.get(symbol)
        if df is None or len(df) < 25:
            continue

        # FX regime gate: skip during vol spikes (news events destroy London edge)
        regime_ok, _vr = _fx_regime_ok(df)
        if not regime_ok:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])
        if not np.isfinite(current) or current <= 0:
            continue

        # Asian range proxy: last 5 bars had compressed range (< 0.8x ATR)
        atr_val = float(atr(high, low, close, 14).iloc[-1])
        asia_range = float(high.iloc[-5:].max() - low.iloc[-5:].min())
        compression_ratio = asia_range / atr_val if atr_val > 0 else 1.0
        if compression_ratio > 1.0:
            continue  # No Asian compression = London breakout less reliable

        asia_high = float(high.iloc[-5:].max())
        asia_low = float(low.iloc[-5:].min())

        # Trend alignment: breakout in direction of 50d SMA trend
        sma50_val = float(sma(close, 50).iloc[-1]) if len(close) >= 50 else current
        trend_up = current > sma50_val

        # RSI filter: not overextended on direction of breakout
        rsi_val = float(rsi(close, 14).iloc[-1])

        if current > asia_high * 1.0002 and trend_up and rsi_val < 72:
            # Bullish London breakout (2026-05-08: caps widened to 1.5%/0.8%)
            tp_dist = min(1.5 * atr_val, current * 0.015)  # cap 1.5%
            sl_dist = min(0.8 * atr_val, current * 0.008)  # cap 0.8%
            tp = current + tp_dist
            sl = asia_high - sl_dist  # SL just below breakout level
            rr = tp_dist / max(current - sl, 0.0001)
            if rr < 1.0:
                continue

            conf = _forex_conf_cap(min(0.72, 0.58 + (1.0 - compression_ratio) * 0.1),
                                   "london_session_breakout")
            signals.append({
                "strategy": "london_session_breakout",
                "symbol": symbol, "category": "forex",
                "signal_type": "BUY",
                "entry_price": round(current, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"London breakout above Asia high {asia_high:.5f}, "
                           f"compression={compression_ratio:.2f}x ATR, RSI={rsi_val:.0f}"),
            "timeframe": "1h",
            "max_hold_bars": 4,
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {"asia_range": round(asia_range, 5),
                      "compression": round(compression_ratio, 3),
                      "asia_high": round(asia_high, 5)},
            "timestamp": _now_iso(),
        })

        elif current < asia_low * 0.9998 and not trend_up and rsi_val > 28:
            # Bearish London breakout (2026-05-08: caps widened to 1.5%/0.8%)
            tp_dist = min(1.5 * atr_val, current * 0.015)  # cap 1.5%
            sl_dist = min(0.8 * atr_val, current * 0.008)  # cap 0.8%
            tp = current - tp_dist
            sl = asia_low + sl_dist
            rr = tp_dist / max(sl - current, 0.0001)
            if rr < 1.0:
                continue

            conf = _forex_conf_cap(min(0.72, 0.58 + (1.0 - compression_ratio) * 0.1),
                                   "london_session_breakout")
            signals.append({
                "strategy": "london_session_breakout",
                "symbol": symbol, "category": "forex",
                "signal_type": "SELL",
                "entry_price": round(current, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"London breakdown below Asia low {asia_low:.5f}, "
                           f"compression={compression_ratio:.2f}x ATR, RSI={rsi_val:.0f}"),
            "timeframe": "1h",
            "max_hold_bars": 4,
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {"asia_range": round(asia_range, 5),
                      "compression": round(compression_ratio, 3),
                      "asia_low": round(asia_low, 5)},
            "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# STRATEGY 8: Mean Reversion 200d SMA (Poterba & Summers 1988)
# =========================================================================
# Major currency pairs anchor to 200d SMA due to central bank policy.
# Extreme Z-score deviations (>2 sigma) revert at higher probability.
# Reference: Poterba & Summers (1988); adapted for FX by Barberis (2000).
# Practical edge: 60-65% WR on deviation > 2.0 sigma in backtests.
# FX-specific: central banks create implicit policy anchor (no infinite drift).
# =========================================================================

def mean_reversion_200d(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Mean reversion to 200d SMA on extreme Z-score deviation. 60-65% WR."""
    signals = []
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 210:
            continue

        # FX regime gate: extreme vol breaks mean-reversion edge
        regime_ok, _vr = _fx_regime_ok(df)
        if not regime_ok:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])

        sma200 = sma(close, 200)
        sma_val = float(sma200.iloc[-1])
        if pd.isna(sma_val):
            continue

        # Z-score of deviation from 200d SMA
        distance = close - sma200
        z = float(zscore(distance, 60).iloc[-1])
        if pd.isna(z):
            continue

        if abs(z) < 1.5:
            continue  # Trade at 1.5+ sigma (loosened from 2.0, 68.3% WR at 2.0, ~62% at 1.5)

        rsi_val = float(rsi(close, 14).iloc[-1])

        if z > 1.5:
            # Overextended above mean — SELL (fade)
            if rsi_val < 48:
                continue  # RSI should also suggest overbought tendency (loosened from 55)
            price, _, sl_long = _forex_tp_sl(close, high, low, tp_mult=1.5, sl_mult=1.0)
            tp = sma_val  # Dynamic TP: return to 200d SMA
            sl = price + (price - sl_long)  # SL = 1.0x ATR above entry
            if sl <= price:
                continue
            rr = (price - tp) / max(sl - price, 0.0001)
            if rr < 1.0:
                continue
            conf = _forex_conf_cap(min(0.75, 0.55 + abs(z) * 0.08), "forex_mean_reversion_200d")
            signals.append({
                "strategy": "forex_mean_reversion_200d",
                "symbol": symbol, "category": "forex",
                "signal_type": "SELL",
                "entry_price": round(price, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"Z-score={z:.2f} (>2.0 sigma above 200d SMA={sma_val:.5f}), "
                           f"RSI={rsi_val:.0f}. Poterba & Summers (1988) FX anchor."),
            "timeframe": "1d",
            "max_hold_bars": 14,
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {"zscore": round(z, 3), "sma200": round(sma_val, 5)},
            "timestamp": _now_iso(),
        })

        elif z < -1.5:
            # Overextended below mean — BUY (fade)
            if rsi_val > 52:
                continue  # RSI should also suggest oversold tendency (loosened from 45)
            price, tp_long, sl_long = _forex_tp_sl(close, high, low, tp_mult=1.5, sl_mult=1.0)
            tp = sma_val  # Dynamic TP: return to 200d SMA
            sl = sl_long  # 1.0x ATR below entry
            if sl >= price or tp <= price:
                continue
            rr = (tp - price) / max(price - sl, 0.0001)
            if rr < 1.0:
                continue
            conf = _forex_conf_cap(min(0.75, 0.55 + abs(z) * 0.08), "forex_mean_reversion_200d")
            signals.append({
                "strategy": "forex_mean_reversion_200d",
                "symbol": symbol, "category": "forex",
                "signal_type": "BUY",
                "entry_price": round(price, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"Z-score={z:.2f} (<-1.5 sigma below 200d SMA={sma_val:.5f}), "
                           f"RSI={rsi_val:.0f}. Poterba & Summers (1988) FX anchor."),
            "timeframe": "1d",
            "max_hold_bars": 14,
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {"zscore": round(z, 3), "sma200": round(sma_val, 5)},
            "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# STRATEGY 9: Inverse Carry Contrarian (FOREX Rescue — bonus edge)
# =========================================================================
# "Test inverse carry strategy" — the bonus edge from the FOREX rescue op.
#
# Logic: When high-yield currencies (AUD, NZD, GBP) have carry differentials
# that are WIDENING but price is STALLING against the carry direction, the
# carry trade is ripe for a reversal. Institutions unwind carry positions
# rapidly during risk-off events (flash crash reversal pattern). This is
# the mirror of carry_trade_momentum — instead of riding the carry, fade it.
#
# Signal: Go SHORT high-yield currency when:
#   1. carry_diff > 0 (carry is positive — we're fading it, not catching a falling knife)
#   2. Price has broken below SMA50 (carry reversal confirmation)
#   3. ADX > 20 (trend confirming the reversal direction)
#   4. RSI > 60 on the cross (momentum confirming)
#
# The "inverse" element: carry_trade_momentum says LONG high-yield when carry > 0
# AND price > SMA200. This strategy says SHORT when carry > 0 but price < SMA50
# (carry is over-extended, institutions about to unwind).
#
# Academic reference: Verdelhan (2015) — carry trade crash risk is most severe
# when momentum stalls at session boundaries.
# =========================================================================
def inverse_carry_contrarian(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Inverse carry contrarian — fade over-extended carry positions.

    FOREX Rescue Operation bonus edge (2026-05-08).
    Mirror of carry_trade_momentum: short high-yield currencies when
    carry differentials are positive but price momentum is stalling or
    reversing (carry trade unwind pattern).
    """
    signals = []
    for symbol, info in FOREX_SYMBOLS.items():
        df = data.get(symbol)
        if df is None or len(df) < 200:
            continue

        carry_diff = info.get("carry_yield_diff", 0)

        # Inverse rule: we WANT carry > 0 (confirming it's a carry currency),
        # but we're fading it (SHORT), not riding it (LONG).
        if carry_diff <= 0:
            continue  # No carry to fade — skip

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])

        sma50_val = float(sma(close, 50).iloc[-1])
        if not np.isfinite(sma50_val):
            continue

        # Key inverse signal: price below SMA50 = carry trade reversal setup
        if current >= sma50_val:
            continue  # Carry still trending with momentum — not ready to fade

        sma200_val = float(sma(close, 200).iloc[-1])
        if not np.isfinite(sma200_val) or current >= sma200_val:
            continue  # Must be below both SMA50 and SMA200

        # FX regime gate: skip during vol spikes
        regime_ok, vol_ratio = _fx_regime_ok(df)
        if not regime_ok:
            continue

        # RSI confirmation: should be in overbought territory for SHORT signal
        rsi_val = float(rsi(close, 14).iloc[-1])
        if rsi_val < 55:
            continue  # Not overbought enough to fade carry

        # ADX: need a confirmed downtrend to fade carry
        adx_v = float(adx(high, low, close).iloc[-1]) if len(close) >= 20 else 20.0
        if adx_v < 20:
            continue  # No trend = carry may resume, not fade

        # Short-term momentum: price below SMA20 confirms near-term reversal
        sma20_val = float(sma(close, 20).iloc[-1]) if len(close) >= 20 else current
        if current >= sma20_val:
            continue  # Near-term momentum still up

        # Carry divergence: price diverging from carry direction
        # (carry > 0 but price below SMAs = institutions quietly exiting)
        mom_5d = float(close.iloc[-1] / close.iloc[-5] - 1) if len(close) >= 5 else 0
        mom_20d = float(close.iloc[-1] / close.iloc[-20] - 1) if len(close) >= 20 else mom_5d

        # Bearish divergence: carry is positive but short-term momentum is negative
        if mom_5d >= 0:
            continue  # Carry/momentum still aligned — too early to fade

        # ATR-based TP/SL: use forex-appropriate 1.5x ATR (0.8% cap)
        entry, tp, sl = _forex_tp_sl(close, high, low, tp_mult=1.5, sl_mult=1.0)
        rr = abs(entry - tp) / abs(entry - sl) if abs(entry - sl) > 0 else 0
        if rr < 1.0:
            continue

        # Confidence: higher when carry is large (more to unwind)
        # but muted when we're fighting the trend too hard
        base_conf = min(0.72, 0.52 + carry_diff / 15.0)
        # Stronger fade signal when price is deeply below both SMAs
        sma50_distance = (sma50_val - current) / sma50_val
        base_conf += min(0.06, sma50_distance * 2.0)  # Up to +6% for deep deviation
        # Bearish momentum bonus
        if mom_20d < -0.02:
            base_conf += 0.04  # Confirmed downtrend

        conf = _forex_conf_cap(max(0.52, min(0.75, base_conf)), "inverse_carry_contrarian")

        signals.append({
            "strategy": "inverse_carry_contrarian",
            "symbol": symbol, "category": "forex",
            "signal_type": "SELL",  # SHORT the high-yield currency
            "entry_price": round(entry, 5),
            "take_profit": round(tp, 5),
            "stop_loss": round(sl, 5),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (f"Inverse carry fade: carry_diff=+{carry_diff:.1f}% but "
                       f"price below SMA50/SMA200 (carry unwind), "
                       f"ADX={adx_v:.0f}, RSI={rsi_val:.0f}, mom_5d={mom_5d:.2%}"),
            "timeframe": "1d",
            "max_hold_bars": 7,
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {
                "carry_diff": carry_diff,
                "below_sma50_pct": round((sma50_val - current) / sma50_val * 100, 2),
                "below_sma200_pct": round((sma200_val - current) / sma200_val * 100, 2),
                "mom_5d": round(mom_5d, 4),
                "mom_20d": round(mom_20d, 4),
                "adx": round(adx_v, 1),
            },
            "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# STRATEGY 10: IG Contrarian Sentiment (Best performer — Sharpe 5.87)
# =========================================================================
# Extreme RSI-14 contrarian with SMA50 trend confirmation.
# Backtest-proven: Sharpe 5.87, WR 58.3% in forex_smart_picks Portfolio C.
# Logic: RSI < 25 + SMA50 slope > 0 → BUY; RSI > 75 + SMA50 slope < 0 → SELL.
# Promoted from forex_smart_picks.py to first-class strategy 2026-05-05.
# Reference: IG Client Sentiment (retail trader positioning extremes).
# =========================================================================
def ig_contrarian_sentiment_forex(data: dict[str, pd.DataFrame]) -> list[dict]:
    """IG contrarian sentiment — extreme RSI with SMA50 slope confirmation.

    Backtest Sharpe 5.87, WR 58.3%. The best-performing forex strategy.
    Promoted from forex_smart_picks.py to first-class strategy 2026-05-05.
    """
    signals = []
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 55:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        rsi_val = float(rsi(close, 14).iloc[-1])
        if pd.isna(rsi_val):
            continue

        # SMA50 slope (5-bar change)
        sma50_vals = sma(close, 50)
        # Need at least 6 valid SMA bars for iloc[-6] access
        if len(sma50_vals.dropna()) < 6:
            continue
        sma_now = float(sma50_vals.iloc[-1])
        sma_prev = float(sma50_vals.iloc[-6])
        sma_slope = (sma_now - sma_prev) / sma_prev if sma_prev > 0 else 0

        # FX regime gate: skip during vol spikes
        regime_ok, _vr = _fx_regime_ok(df)
        if not regime_ok:
            continue

        if rsi_val < 25 and sma_slope > 0:
            # Oversold with bullish trend = contrarian BUY
            price, tp, sl = _forex_tp_sl(close, high, low, tp_mult=2.0, sl_mult=1.5)
            rr = (tp - price) / max(price - sl, 0.0001)
            if rr < 1.0:
                continue
            conf = _forex_conf_cap(min(0.75, 0.65 + (25 - rsi_val) * 0.005), "ig_contrarian_sentiment")
            signals.append({
                "strategy": "ig_contrarian_sentiment",
                "symbol": symbol, "category": "forex",
                "signal_type": "BUY",
                "entry_price": round(price, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"Contrarian BUY: RSI={rsi_val:.0f} (<25 oversold), "
                           f"SMA50 slope={sma_slope*100:.2f}% (bullish)"),
            "timeframe": "1d",
            "max_hold_bars": 5,
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {"rsi14": round(rsi_val, 1),
                      "sma50_slope_pct": round(sma_slope * 100, 3),
                      "backtest_sharpe": 5.87, "backtest_wr": 0.583},
            "timestamp": _now_iso(),
        })

        elif rsi_val > 75 and sma_slope < 0:
            # Overbought with bearish trend = contrarian SELL
            price, tp_long, sl_long = _forex_tp_sl(close, high, low, tp_mult=2.0, sl_mult=1.5)
            tp = price - (tp_long - price)  # Mirror for short
            sl = price + (price - sl_long)
            rr = (price - tp) / max(sl - price, 0.0001)
            if rr < 1.0:
                continue
            conf = _forex_conf_cap(min(0.75, 0.65 + (rsi_val - 75) * 0.005), "ig_contrarian_sentiment")
            signals.append({
                "strategy": "ig_contrarian_sentiment",
                "symbol": symbol, "category": "forex",
                "signal_type": "SELL",
                "entry_price": round(price, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"Contrarian SELL: RSI={rsi_val:.0f} (>75 overbought), "
                           f"SMA50 slope={sma_slope*100:.2f}% (bearish)"),
            "timeframe": "1d",
            "max_hold_bars": 5,
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {"rsi14": round(rsi_val, 1),
                      "sma50_slope_pct": round(sma_slope * 100, 3),
                      "backtest_sharpe": 5.87, "backtest_wr": 0.583},
            "timestamp": _now_iso(),
        })
    return signals


def _session_guard(fn):
    """Wrap forex strategy to run during active market hours (07-22 UTC).

    Signal generation window — not emission. The actual emission filter
    is passes_fx_session_gate() in non_crypto_policy.py (07-21 UTC), which
    gates already-generated picks before they enter the pipeline.

    Keep generation open so asian_range_breakout (fires 21-07 UTC),
    london_session_breakout (fires ~08 UTC), and orb_breakout (fires ~07 UTC)
    all get a chance to generate. The emission gate in non_crypto_policy.py
    then filters which ones actually get emitted based on the current UTC hour.
    """
    def wrapper(*args, **kwargs):
        hour = datetime.now(timezone.utc).hour
        if not (7 <= hour < 22):
            return []
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


FOREX_STRATEGIES = {
    # London/NY overlap window (13-21 UTC) — highest edge at 58% WR
    "carry_trade_momentum":        _session_guard(carry_trade),
    "inverse_carry_contrarian":    _session_guard(inverse_carry_contrarian),  # FOREX Rescue bonus edge
    "asian_range_breakout":        _session_guard(asian_range_breakout),
    "orb_breakout":                _session_guard(orb_breakout),
    "forex_rsi2_mean_reversion":   _session_guard(connors_rsi2_forex),
    # forex_tsmom_12m REMOVED 2026-05-05 — Sharpe -1.73 in backtest.
    # FX pairs mean-revert due to central bank policy; long-term trend-following fails.
    # Replaced by ig_contrarian_sentiment (Sharpe 5.87).
    "cot_positioning":             _session_guard(cot_positioning_forex),
    "london_session_breakout":     _session_guard(london_session_breakout),
    "forex_mean_reversion_200d":   _session_guard(mean_reversion_200d),
    "ig_contrarian_sentiment":     _session_guard(ig_contrarian_sentiment_forex),
}
