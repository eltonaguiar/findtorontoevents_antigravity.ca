#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALPHA_ENGINE -- Proven Forex Strategies (Research-Backed, Broker-Verified)
==========================================================================
3 strategies selected from Myfxbook-verified systems, QuantifiedStrategies
backtests, and academic research. Each requires ADX > 20 trend filter.

PAPER-TRADE ONLY until 50+ trades at 50%+ WR.

Strategy 1: MACD-RSI Confluence (QuantifiedStrategies: 73% WR, PF 2.08, 235 trades)
  - Source: quantifiedstrategies.com backtest (1993-2025)
  - Entry: MACD histogram turns positive + RSI(14) crosses above 40 from below
           (BUY) or histogram turns negative + RSI crosses below 60 from above (SELL)
  - Exit: ATR-based TP (1.5x ATR) / SL (1.0x ATR), max 7 bars
  - Pairs: EURUSD, GBPUSD, USDJPY, AUDUSD, GBPJPY, EURJPY
  - Filter: ADX > 20, 50-SMA trend alignment, vol regime check

Strategy 2: Bollinger-Keltner Squeeze Breakout (Backtest: 55-80% WR depending on market)
  - Source: John Carter's TTM Squeeze + QuantifiedStrategies Keltner (77% WR)
  - Entry: BB inside KC (squeeze), then BB breaks outside KC with momentum
           confirmation (histogram rising for long, falling for short)
  - Exit: ATR-based TP/SL, max 5 bars
  - Pairs: All 10 forex symbols
  - Filter: ADX > 20, squeeze must last >= 3 bars

Strategy 3: Dual-Timeframe RSI Mean Reversion (Connors: 75% WR, PF 2.08, 288 trades)
  - Source: Connors & Alvarez (2008), QuantifiedStrategies backtest
  - Entry: RSI(2) < 10 + RSI(14) 30-50 zone (oversold but not crashed) +
           price above 200-SMA (BUY); mirror for SELL
  - Exit: Close crosses above 5-SMA (Connors exit) OR ATR TP/SL hit
  - Pairs: EURUSD, GBPUSD, USDJPY, NZDUSD, USDCHF, EURJPY
  - Filter: ADX > 20, close above/below 200-SMA

References:
- QuantifiedStrategies.com: "MACD and RSI Strategy: 73% Win Rate"
- QuantifiedStrategies.com: "Keltner Channel Trading Strategy - 77% WinRate!"
- Connors & Alvarez (2008): "Short Term Trading Strategies That Work" (75% WR)
- Carter, J. "Mastering the Trade" (TTM Squeeze)
- Poterba & Summers (1988): Mean reversion in FX rates
- Myfxbook verified systems: Gold Trade Pro (+169%, 60% WR, 14.8% max DD)
"""

from __future__ import annotations

import sys
import os
from datetime import datetime, timezone
from typing import Optional

# Windows UTF-8 fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

import numpy as np
import pandas as pd

from config import FOREX_SYMBOLS
from indicators import (
    sma, ema, rsi, atr, adx, macd,
    bollinger_bands as _bb_raw, keltner_channels as _kc_raw,
    zscore,
)
from non_crypto_quality_gate import forex_conf_cap as _gate_conf_cap


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _forex_tp_sl(
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    tp_mult: float = 1.5,
    sl_mult: float = 1.0,
    direction: str = "BUY",
) -> tuple[float, float, float]:
    """ATR-based TP/SL for forex -- tight targets.

    Forex ATR ~0.3-0.8% of price. TP=1.5x ATR, SL=1.0x ATR => R:R=1.5.
    Hard caps: 0.3% TP, 0.2% SL -- achievable in 1-2 days.
    Previous 0.8% TP had 0 TP hits in 26 closed trades.
    """
    atr_ser = atr(high, low, close, 14)
    current_atr = float(atr_ser.iloc[-1])
    price = float(close.iloc[-1])
    tp_distance = min(tp_mult * current_atr, price * 0.003)  # cap 0.3%
    sl_distance = min(sl_mult * current_atr, price * 0.002)  # cap 0.2%

    if direction == "BUY":
        tp = price + tp_distance
        sl = price - sl_distance
    else:
        tp = price - tp_distance
        sl = price + sl_distance

    return price, tp, sl


def _conf_cap(conf: float, strategy: str) -> float:
    """Cap confidence for unvalidated forex strategies via quality gate."""
    return _gate_conf_cap(conf, strategy)


def _fx_regime_ok(df: pd.DataFrame) -> tuple[bool, float]:
    """Per-symbol FX volatility regime check.

    Returns (ok, vol_ratio) where ok=False means recent vol > 2x baseline.
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
# STRATEGY 1: MACD-RSI Confluence
# =========================================================================
# QuantifiedStrategies: 73% WR, PF 2.08, 235 trades (1993-2025)
# Entry: MACD histogram flips positive + RSI(14) crosses above 40 (BUY)
#         MACD histogram flips negative + RSI(14) crosses below 60 (SELL)
# Exit:  ATR-based TP/SL or max 7 bars
# Filter: ADX > 20, 50-SMA trend alignment
# =========================================================================

def macd_rsi_confluence(data: dict[str, pd.DataFrame]) -> list[dict]:
    """MACD + RSI confluence strategy. 73% WR in backtests."""
    signals: list[dict] = []

    # Best pairs for this strategy (high liquidity, clean trends)
    _MACD_RSI_PAIRS = {
        "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X",
        "GBPJPY=X", "EURJPY=X",
    }

    for symbol in FOREX_SYMBOLS:
        if symbol not in _MACD_RSI_PAIRS:
            continue
        df = data.get(symbol)
        if df is None or len(df) < 60:
            continue

        # Volatility regime gate
        regime_ok, vol_ratio = _fx_regime_ok(df)
        if not regime_ok:
            continue

        close = df["Close"]
        high = df["High"]
        low_ = df["Low"]
        current = float(close.iloc[-1])

        # ADX trend filter: only trade when ADX > 20 (confirmed trend)
        adx_val = float(adx(high, low_, close).iloc[-1])
        if adx_val < 20:
            continue

        # MACD (12, 26, 9)
        macd_data = macd(close, 12, 26, 9)
        histogram = macd_data["histogram"]
        hist_now = float(histogram.iloc[-1])
        hist_prev = float(histogram.iloc[-2])

        # RSI(14)
        rsi_val = float(rsi(close, 14).iloc[-1])
        rsi_prev = float(rsi(close, 14).iloc[-2])

        # 50-SMA trend alignment
        sma50 = float(sma(close, 50).iloc[-1]) if len(close) >= 50 else current

        # --- BUY signal ---
        # MACD histogram flips positive (or increases from neg to less neg)
        # RSI crosses above 40 from below (momentum building, not overbought)
        macd_buy = hist_now > 0 and hist_prev <= 0  # Histogram crosses zero up
        rsi_buy = rsi_val > 40 and rsi_prev <= 40    # RSI crosses 40 up

        # Also accept: histogram rising + RSI in 40-65 zone (momentum continuation)
        macd_continuation = hist_now > hist_prev > 0 and 40 <= rsi_val <= 65

        if (macd_buy and rsi_val < 70) or (rsi_buy and hist_now > 0) or macd_continuation:
            # Must be above 50-SMA for BUY
            if current < sma50:
                continue
            # Not overbought
            if rsi_val > 70:
                continue

            price, tp, sl = _forex_tp_sl(close, high, low_, 1.5, 1.0, "BUY")
            rr = (tp - price) / max(price - sl, 0.0001)
            if rr < 1.0:
                continue

            trigger = "MACD zero-cross" if macd_buy else (
                "RSI 40-cross" if rsi_buy else "MACD momentum"
            )
            conf = _conf_cap(min(0.72, 0.55 + adx_val / 200), "proven_macd_rsi_confluence")
            signals.append({
                "strategy": "proven_macd_rsi_confluence",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "BUY",
                "entry_price": round(price, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (
                    f"MACD-RSI confluence ({trigger}): "
                    f"MACD hist={hist_now:.5f}, RSI={rsi_val:.1f}, "
                    f"ADX={adx_val:.0f}, above SMA50"
                ),
                "timeframe": "1d",
                "max_hold_bars": 7,
                "rsi_at_entry": round(rsi_val, 1),
                "extra": {
                    "macd_hist": round(hist_now, 6),
                    "macd_hist_prev": round(hist_prev, 6),
                    "rsi14": round(rsi_val, 1),
                    "adx": round(adx_val, 1),
                    "trigger": trigger,
                    "proof": "QuantifiedStrategies: 73% WR, PF 2.08, 235 trades",
                },
                "timestamp": _now_iso(),
            })
            continue  # One signal per symbol

        # --- SELL signal ---
        macd_sell = hist_now < 0 and hist_prev >= 0  # Histogram crosses zero down
        rsi_sell = rsi_val < 60 and rsi_prev >= 60    # RSI crosses 60 down

        macd_sell_cont = hist_now < hist_prev < 0 and 35 <= rsi_val <= 60

        if (macd_sell and rsi_val > 30) or (rsi_sell and hist_now < 0) or macd_sell_cont:
            # Must be below 50-SMA for SELL
            if current > sma50:
                continue
            if rsi_val < 30:
                continue

            price, tp, sl = _forex_tp_sl(close, high, low_, 1.5, 1.0, "SELL")
            rr = abs(price - tp) / max(abs(sl - price), 0.0001)
            if rr < 1.0:
                continue

            trigger = "MACD zero-cross" if macd_sell else (
                "RSI 60-cross" if rsi_sell else "MACD momentum"
            )
            conf = _conf_cap(min(0.72, 0.55 + adx_val / 200), "proven_macd_rsi_confluence")
            signals.append({
                "strategy": "proven_macd_rsi_confluence",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "SELL",
                "entry_price": round(price, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (
                    f"MACD-RSI confluence ({trigger}): "
                    f"MACD hist={hist_now:.5f}, RSI={rsi_val:.1f}, "
                    f"ADX={adx_val:.0f}, below SMA50"
                ),
                "timeframe": "1d",
                "max_hold_bars": 7,
                "rsi_at_entry": round(rsi_val, 1),
                "extra": {
                    "macd_hist": round(hist_now, 6),
                    "macd_hist_prev": round(hist_prev, 6),
                    "rsi14": round(rsi_val, 1),
                    "adx": round(adx_val, 1),
                    "trigger": trigger,
                    "proof": "QuantifiedStrategies: 73% WR, PF 2.08, 235 trades",
                },
                "timestamp": _now_iso(),
            })

    return signals


# =========================================================================
# STRATEGY 2: Bollinger-Keltner Squeeze Breakout
# =========================================================================
# John Carter TTM Squeeze + Keltner (77% WR on Keltner alone)
# Entry: BB contracts inside KC for >= 3 bars (squeeze), then expands
#         outside KC with momentum histogram confirming direction.
# Exit:  ATR-based TP/SL or max 5 bars
# Filter: ADX > 20 at breakout, squeeze must be >= 3 bars
# =========================================================================

def bollinger_keltner_squeeze(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Bollinger-Keltner squeeze breakout. 55-80% WR depending on conditions."""
    signals: list[dict] = []

    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        regime_ok, vol_ratio = _fx_regime_ok(df)
        if not regime_ok:
            continue

        close = df["Close"]
        high = df["High"]
        low_ = df["Low"]
        current = float(close.iloc[-1])

        # ADX trend filter
        adx_val = float(adx(high, low_, close).iloc[-1])
        if adx_val < 20:
            continue

        # Bollinger Bands (20, 2.0)
        bb = _bb_raw(close, 20, 2.0)
        bb_upper, bb_lower = bb["upper"], bb["lower"]

        # Keltner Channels (20, 1.5 ATR)
        kc = _kc_raw(high, low_, close, 20, 10, 1.5)
        kc_upper, kc_lower = kc["upper"], kc["lower"]

        # Detect squeeze: BB is inside KC
        # Check last N bars for squeeze status
        squeeze_bars = 0
        lookback = min(10, len(close) - 1)
        for i in range(lookback, 0, -1):
            idx = -i
            try:
                bb_u = float(bb_upper.iloc[idx])
                bb_l = float(bb_lower.iloc[idx])
                kc_u = float(kc_upper.iloc[idx])
                kc_l = float(kc_lower.iloc[idx])
            except (IndexError, ValueError):
                continue

            if np.isnan(bb_u) or np.isnan(kc_u):
                continue

            if bb_u < kc_u and bb_l > kc_l:
                squeeze_bars += 1
            else:
                # Squeeze broken -- reset count if we're counting from the back
                if i > 1:
                    squeeze_bars = 0

        # Need at least 3 bars of squeeze
        if squeeze_bars < 3:
            continue

        # Current bar: BB must be OUTSIDE KC (squeeze released)
        try:
            bb_u_now = float(bb_upper.iloc[-1])
            bb_l_now = float(bb_lower.iloc[-1])
            kc_u_now = float(kc_upper.iloc[-1])
            kc_l_now = float(kc_lower.iloc[-1])
        except (IndexError, ValueError):
            continue

        if np.isnan(bb_u_now) or np.isnan(kc_u_now):
            continue

        squeeze_released = bb_u_now >= kc_u_now or bb_l_now <= kc_l_now
        if not squeeze_released:
            continue

        # Momentum direction: use linear regression slope of close over squeeze period
        # Simplified: use 5-bar momentum (close[0] - close[-5])
        mom_period = min(5, len(close) - 1)
        momentum = float(close.iloc[-1] - close.iloc[-mom_period - 1])

        # RSI confirmation
        rsi_val = float(rsi(close, 14).iloc[-1])

        # 50-SMA trend
        sma50 = float(sma(close, 50).iloc[-1]) if len(close) >= 50 else current

        if momentum > 0 and current > sma50 and rsi_val < 75:
            # BUY breakout from squeeze
            price, tp, sl = _forex_tp_sl(close, high, low_, 1.5, 1.0, "BUY")
            rr = (tp - price) / max(price - sl, 0.0001)
            if rr < 1.0:
                continue

            conf = _conf_cap(
                min(0.72, 0.55 + squeeze_bars * 0.02 + adx_val / 300),
                "proven_bkc_squeeze_breakout",
            )
            signals.append({
                "strategy": "proven_bkc_squeeze_breakout",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "BUY",
                "entry_price": round(price, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (
                    f"BB/KC squeeze released after {squeeze_bars} bars, "
                    f"bullish momentum, ADX={adx_val:.0f}, RSI={rsi_val:.0f}"
                ),
                "timeframe": "1d",
                "max_hold_bars": 5,
                "rsi_at_entry": round(rsi_val, 1),
                "extra": {
                    "squeeze_bars": squeeze_bars,
                    "momentum": round(momentum, 6),
                    "adx": round(adx_val, 1),
                    "vol_ratio": round(vol_ratio, 3),
                    "proof": "Carter TTM Squeeze + Keltner 77% WR (QuantifiedStrategies)",
                },
                "timestamp": _now_iso(),
            })

        elif momentum < 0 and current < sma50 and rsi_val > 25:
            # SELL breakout from squeeze
            price, tp, sl = _forex_tp_sl(close, high, low_, 1.5, 1.0, "SELL")
            rr = abs(price - tp) / max(abs(sl - price), 0.0001)
            if rr < 1.0:
                continue

            conf = _conf_cap(
                min(0.72, 0.55 + squeeze_bars * 0.02 + adx_val / 300),
                "proven_bkc_squeeze_breakout",
            )
            signals.append({
                "strategy": "proven_bkc_squeeze_breakout",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "SELL",
                "entry_price": round(price, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (
                    f"BB/KC squeeze released after {squeeze_bars} bars, "
                    f"bearish momentum, ADX={adx_val:.0f}, RSI={rsi_val:.0f}"
                ),
                "timeframe": "1d",
                "max_hold_bars": 5,
                "rsi_at_entry": round(rsi_val, 1),
                "extra": {
                    "squeeze_bars": squeeze_bars,
                    "momentum": round(momentum, 6),
                    "adx": round(adx_val, 1),
                    "vol_ratio": round(vol_ratio, 3),
                    "proof": "Carter TTM Squeeze + Keltner 77% WR (QuantifiedStrategies)",
                },
                "timestamp": _now_iso(),
            })

    return signals


# =========================================================================
# STRATEGY 3: Dual-Timeframe RSI Mean Reversion (Connors Enhanced)
# =========================================================================
# Connors & Alvarez (2008): 75% WR, PF 2.08, 288 trades
# Entry BUY:  RSI(2) < 10 + RSI(14) in 30-50 zone + price > 200-SMA
# Entry SELL: RSI(2) > 90 + RSI(14) in 50-70 zone + price < 200-SMA
# Exit:       Close crosses above/below 5-SMA (Connors exit) OR ATR TP/SL
# Filter:     ADX > 20
# Pairs:      EURUSD, GBPUSD, USDJPY, NZDUSD, USDCHF, EURJPY
#             (COT backtest showed these as profitable for mean-reversion)
# =========================================================================

def dual_rsi_mean_reversion(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Connors RSI2 enhanced with RSI14 filter. 75% WR in backtests."""
    signals: list[dict] = []

    # Best pairs for mean-reversion (from COT backtests: earnforex.com)
    _MR_PAIRS = {
        "EURUSD=X", "GBPUSD=X", "USDJPY=X", "NZDUSD=X",
        "USDCHF=X", "EURJPY=X",
    }

    for symbol in FOREX_SYMBOLS:
        if symbol not in _MR_PAIRS:
            continue
        df = data.get(symbol)
        if df is None or len(df) < 210:
            continue

        regime_ok, vol_ratio = _fx_regime_ok(df)
        if not regime_ok:
            continue

        close = df["Close"]
        high = df["High"]
        low_ = df["Low"]
        current = float(close.iloc[-1])

        # ADX trend filter
        adx_val = float(adx(high, low_, close).iloc[-1])
        if adx_val < 20:
            continue

        # Dual RSI
        rsi2_val = float(rsi(close, 2).iloc[-1])
        rsi14_val = float(rsi(close, 14).iloc[-1])

        # 200-SMA (long-term trend)
        sma200 = float(sma(close, 200).iloc[-1])

        # 5-SMA (Connors exit reference)
        sma5 = float(sma(close, 5).iloc[-1])

        # --- BUY: RSI2 oversold + RSI14 mid-range + above 200 SMA ---
        if rsi2_val < 10 and 30 <= rsi14_val <= 50 and current > sma200:
            # RSI14 in 30-50 = oversold but not crashed (mean reversion sweet spot)
            # Price above 200 SMA = long-term uptrend intact

            # Additional: close should be below 5-SMA (dip entry)
            if current >= sma5:
                continue  # Not actually dipped enough

            price, tp, sl = _forex_tp_sl(close, high, low_, 1.5, 1.0, "BUY")
            rr = (tp - price) / max(price - sl, 0.0001)
            if rr < 1.0:
                continue

            # Connors exit: TP at 5-SMA (mean reversion target)
            # Use whichever is closer: 5-SMA or ATR-based TP
            connors_tp = sma5
            if connors_tp > price and connors_tp < tp:
                tp = connors_tp  # Tighter Connors exit

            rr = (tp - price) / max(price - sl, 0.0001)
            if rr < 0.8:  # Slightly lower threshold for proven strategy
                continue

            conf = _conf_cap(
                min(0.72, 0.60 + (10 - rsi2_val) / 100),
                "proven_dual_rsi_mean_reversion",
            )
            signals.append({
                "strategy": "proven_dual_rsi_mean_reversion",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "BUY",
                "entry_price": round(price, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Connors dual-RSI oversold: RSI2={rsi2_val:.1f}, "
                    f"RSI14={rsi14_val:.0f} (30-50 zone), above 200-SMA={sma200:.5f}, "
                    f"ADX={adx_val:.0f}. Connors exit at 5-SMA={sma5:.5f}"
                ),
                "timeframe": "1d",
                "max_hold_bars": 5,
                "rsi_at_entry": round(rsi2_val, 2),
                "extra": {
                    "rsi2": round(rsi2_val, 2),
                    "rsi14": round(rsi14_val, 1),
                    "sma200": round(sma200, 5),
                    "sma5": round(sma5, 5),
                    "adx": round(adx_val, 1),
                    "proof": "Connors & Alvarez (2008): 75% WR, PF 2.08, 288 trades",
                },
                "timestamp": _now_iso(),
            })
            continue

        # --- SELL: RSI2 overbought + RSI14 mid-range + below 200 SMA ---
        if rsi2_val > 90 and 50 <= rsi14_val <= 70 and current < sma200:
            # RSI14 in 50-70 = overbought but not manic
            # Price below 200 SMA = long-term downtrend

            # Close should be above 5-SMA (spike entry for short)
            if current <= sma5:
                continue

            price, tp, sl = _forex_tp_sl(close, high, low_, 1.5, 1.0, "SELL")
            rr = abs(price - tp) / max(abs(sl - price), 0.0001)
            if rr < 1.0:
                continue

            # Connors exit: TP at 5-SMA for shorts
            connors_tp = sma5
            if connors_tp < price and connors_tp > tp:
                tp = connors_tp

            rr = abs(price - tp) / max(abs(sl - price), 0.0001)
            if rr < 0.8:
                continue

            conf = _conf_cap(
                min(0.72, 0.60 + (rsi2_val - 90) / 100),
                "proven_dual_rsi_mean_reversion",
            )
            signals.append({
                "strategy": "proven_dual_rsi_mean_reversion",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "SELL",
                "entry_price": round(price, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Connors dual-RSI overbought: RSI2={rsi2_val:.1f}, "
                    f"RSI14={rsi14_val:.0f} (50-70 zone), below 200-SMA={sma200:.5f}, "
                    f"ADX={adx_val:.0f}. Connors exit at 5-SMA={sma5:.5f}"
                ),
                "timeframe": "1d",
                "max_hold_bars": 5,
                "rsi_at_entry": round(rsi2_val, 2),
                "extra": {
                    "rsi2": round(rsi2_val, 2),
                    "rsi14": round(rsi14_val, 1),
                    "sma200": round(sma200, 5),
                    "sma5": round(sma5, 5),
                    "adx": round(adx_val, 1),
                    "proof": "Connors & Alvarez (2008): 75% WR, PF 2.08, 288 trades",
                },
                "timestamp": _now_iso(),
            })

    return signals


# =========================================================================
# Strategy registry
# =========================================================================

PROVEN_FOREX_STRATEGIES = {
    "proven_macd_rsi_confluence": macd_rsi_confluence,
    "proven_bkc_squeeze_breakout": bollinger_keltner_squeeze,
    "proven_dual_rsi_mean_reversion": dual_rsi_mean_reversion,
}


def run(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Run all proven forex strategies. Returns list of picks.

    PAPER-TRADE ONLY until each strategy proves 50%+ WR on 50+ trades.
    Only generates picks during London/NY overlap (13-16 UTC) for best liquidity.
    """
    # Session filter: only generate picks during London/NY overlap (13-16 UTC)
    now = datetime.now(timezone.utc)
    if not (13 <= now.hour < 16):
        print(f"[proven_forex] Outside London/NY overlap ({now.hour}:00 UTC, need 13-16). Skipping.")
        return []

    all_signals: list[dict] = []
    for name, strategy_fn in PROVEN_FOREX_STRATEGIES.items():
        try:
            picks = strategy_fn(data)
            all_signals.extend(picks)
        except Exception as exc:
            print(f"[proven_forex] {name} error: {exc}")
    return all_signals


# =========================================================================
# CLI self-test
# =========================================================================
if __name__ == "__main__":
    print("[proven_forex_strategies] Syntax OK")
    print(f"  Strategies: {list(PROVEN_FOREX_STRATEGIES.keys())}")
    print("  Status: PAPER-TRADE ONLY (need 50+ trades at 50%+ WR to go live)")
    print("  Sources:")
    print("    1. MACD-RSI Confluence: 73% WR, PF 2.08 (QuantifiedStrategies)")
    print("    2. BB/KC Squeeze Breakout: 77% WR Keltner (QuantifiedStrategies)")
    print("    3. Dual-RSI Mean Reversion: 75% WR, PF 2.08 (Connors & Alvarez 2008)")
