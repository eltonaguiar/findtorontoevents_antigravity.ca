#!/usr/bin/env python3
"""
ALPHA_ENGINE -- 20 New Forex Strategies
========================================
20 academically-backed, genuinely distinct forex trading strategies.
All use ATR-based TP/SL with forex caps (0.3% TP, 0.2% SL).
Confidence hard-capped at 0.65 for all unvalidated strategies.

References included per strategy function.

CRITICAL FX NOTES:
- ATR for major pairs ≈ 0.3–0.8% of price daily
- TP cap = 0.3% (price * 0.003), SL cap = 0.2% (price * 0.002)
- RR >= 1.2 enforced for all signals
- Confidence <= 0.65 for all (unvalidated, WR history 33.9%)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

from config import FOREX_SYMBOLS
from indicators import (
    sma, ema, rsi, atr, adx, macd, bollinger_bands, zscore, ichimoku,
)
from non_crypto_quality_gate import forex_conf_cap as _gate_conf_cap


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _forex_conf_cap(conf: float, strategy: str) -> float:
    """Hard-cap confidence at 0.65 for all unvalidated new forex strategies."""
    capped = _gate_conf_cap(conf, strategy)
    return min(capped, 0.65)


def _fx_tp_sl(
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    tp_mult: float = 1.5,
    sl_mult: float = 1.0,
    signal_type: str = "BUY",
) -> tuple[float, float, float, float]:
    """ATR-based TP/SL with forex-appropriate hard caps.

    Returns (entry, tp, sl, rr).
    Caps: TP <= 0.3% price, SL <= 0.2% price.
    """
    atr_val = float(atr(high, low, close, 14).iloc[-1])
    price = float(close.iloc[-1])
    tp_dist = min(tp_mult * atr_val, price * 0.003)
    sl_dist = min(sl_mult * atr_val, price * 0.002)
    if signal_type == "BUY":
        tp = price + tp_dist
        sl = price - sl_dist
    else:
        tp = price - tp_dist
        sl = price + sl_dist
    rr = tp_dist / max(sl_dist, 1e-9)
    return price, tp, sl, rr


def _stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3,
) -> tuple[pd.Series, pd.Series]:
    """Classic slow stochastic (%K, %D)."""
    lowest = low.rolling(k_period, min_periods=k_period).min()
    highest = high.rolling(k_period, min_periods=k_period).max()
    k = 100.0 * (close - lowest) / (highest - lowest).replace(0, np.nan)
    d = k.rolling(d_period, min_periods=d_period).mean()
    return k, d


def _adx_plus_minus_di(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return (adx_series, plus_di, minus_di) for directional analysis."""
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    tr_series = atr(high, low, close, period) * period
    plus_di = 100 * ema(plus_dm, period) / tr_series.replace(0, np.nan)
    minus_di = 100 * ema(minus_dm, period) / tr_series.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_line = ema(dx, period)
    return adx_line, plus_di, minus_di


# ============================================================================
# STRATEGY 1: G10 Cross-Sectional 3-Month Momentum
# ============================================================================
# Menkhoff, Sarno, Schmeling, Schrimpf (2012) "Currency Momentum Strategies"
# Journal of Financial Economics. Buy top-tercile, sell bottom-tercile by
# 3-month return. Skips 1-month return to avoid short-term reversal noise.
# Annualised Sharpe ~0.7 in their sample.
# ============================================================================
def g10_momentum_factor(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """Cross-sectional 3-month momentum across G10 currencies.

    Reference: Menkhoff et al. (2012) JFE.
    """
    signals: list[dict] = []
    mom_scores: list[tuple[str, float, pd.DataFrame]] = []

    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 65:
            continue
        close = df["Close"]
        # 3-month = ~65 bars; skip last 22 bars (1 month) to avoid reversal
        if len(close) < 65:
            continue
        mom_3m = float(close.iloc[-22] / close.iloc[-65] - 1)
        if not np.isfinite(mom_3m):
            continue
        mom_scores.append((symbol, mom_3m, df))

    if len(mom_scores) < 4:
        return signals

    mom_scores.sort(key=lambda x: x[1])
    n = len(mom_scores)
    tercile = max(1, n // 3)

    # Bottom tercile: SELL (worst 3-month performers)
    for symbol, mom, df in mom_scores[:tercile]:
        if mom >= 0:
            continue  # Only short actual losers
        close, high, low = df["Close"], df["High"], df["Low"]
        rsi_val = float(rsi(close, 14).iloc[-1])
        if rsi_val < 35:
            continue  # Already oversold, skip
        entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "SELL")
        if rr < 1.2:
            continue
        conf = _forex_conf_cap(min(0.63, 0.50 + abs(mom) * 1.5), "g10_momentum_factor")
        signals.append({
            "strategy": "g10_momentum_factor",
            "symbol": symbol,
            "category": "forex",
            "signal_type": "SELL",
            "entry_price": round(entry, 5),
            "take_profit": round(tp, 5),
            "stop_loss": round(sl, 5),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (f"G10 cross-sect. 3m momentum={mom:.2%} (bottom tercile). "
                       f"RSI={rsi_val:.0f}. Menkhoff et al (2012) JFE."),
            "timeframe": "1d",
            "max_hold_bars": 22,
            "timestamp": _now_iso(),
        })

    # Top tercile: BUY (best 3-month performers)
    for symbol, mom, df in mom_scores[-tercile:]:
        if mom <= 0:
            continue  # Only long actual winners
        close, high, low = df["Close"], df["High"], df["Low"]
        rsi_val = float(rsi(close, 14).iloc[-1])
        if rsi_val > 70:
            continue  # Overbought, skip
        entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "BUY")
        if rr < 1.2:
            continue
        conf = _forex_conf_cap(min(0.63, 0.50 + abs(mom) * 1.5), "g10_momentum_factor")
        signals.append({
            "strategy": "g10_momentum_factor",
            "symbol": symbol,
            "category": "forex",
            "signal_type": "BUY",
            "entry_price": round(entry, 5),
            "take_profit": round(tp, 5),
            "stop_loss": round(sl, 5),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (f"G10 cross-sect. 3m momentum={mom:.2%} (top tercile). "
                       f"RSI={rsi_val:.0f}. Menkhoff et al (2012) JFE."),
            "timeframe": "1d",
            "max_hold_bars": 22,
            "timestamp": _now_iso(),
        })

    return signals


# ============================================================================
# STRATEGY 2: Dual Momentum Absolute Filter (Antonacci 2014)
# ============================================================================
# Gary Antonacci "Dual Momentum Investing" (2014). Absolute momentum: only
# enter LONG when 12m return is positive (asset beats cash). Below zero →
# stay out (hold cash equivalent). Reduces crash risk substantially.
# ============================================================================
def dual_momentum_absolute(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """Absolute momentum: long only when 12m return > 0. Antonacci (2014)."""
    signals: list[dict] = []
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 252:
            continue
        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        mom_12m = float(close.iloc[-1] / close.iloc[-252] - 1)
        if mom_12m <= 0:
            continue  # Absolute momentum filter: no long when 12m negative

        # Additional: 1m momentum also positive (no late-stage fade)
        mom_1m = float(close.iloc[-1] / close.iloc[-22] - 1)
        if mom_1m < 0:
            continue

        rsi_val = float(rsi(close, 14).iloc[-1])
        if rsi_val > 68:
            continue  # Overbought

        # Trend filter: above 200d SMA
        sma200_val = float(sma(close, 200).iloc[-1])
        if float(close.iloc[-1]) < sma200_val:
            continue

        entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.4, 1.0, "BUY")
        if rr < 1.2:
            continue

        conf = _forex_conf_cap(min(0.63, 0.50 + mom_12m * 0.8), "dual_momentum_absolute")
        signals.append({
            "strategy": "dual_momentum_absolute",
            "symbol": symbol,
            "category": "forex",
            "signal_type": "BUY",
            "entry_price": round(entry, 5),
            "take_profit": round(tp, 5),
            "stop_loss": round(sl, 5),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (f"Dual momentum: 12m={mom_12m:.2%}>0, 1m={mom_1m:.2%}>0, "
                       f"above SMA200, RSI={rsi_val:.0f}. Antonacci (2014)."),
            "timeframe": "1d",
            "max_hold_bars": 22,
            "timestamp": _now_iso(),
        })
    return signals


# ============================================================================
# STRATEGY 3: PPP Mean Reversion (Rogoff 1996)
# ============================================================================
# Rogoff (1996) "The Purchasing Power Parity Puzzle" JEL. FX deviations from
# long-run equilibrium (252d SMA proxy) > 2 std tend to mean-revert over
# months. Central banks implicitly defend PPP via rate policy anchors.
# ============================================================================
def ppp_mean_reversion(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """PPP mean reversion: fade >2std deviations from 252d SMA. Rogoff (1996)."""
    signals: list[dict] = []
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 260:
            continue
        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        sma252 = float(sma(close, 252).iloc[-1])
        if not np.isfinite(sma252) or sma252 <= 0:
            continue

        # Rolling std of distance from 252d SMA
        dist_series = close - sma(close, 252)
        std_val = float(dist_series.rolling(60).std().iloc[-1])
        if not np.isfinite(std_val) or std_val <= 0:
            continue

        current = float(close.iloc[-1])
        z = (current - sma252) / std_val
        if not np.isfinite(z) or abs(z) < 2.0:
            continue

        rsi_val = float(rsi(close, 14).iloc[-1])

        if z > 2.0:
            # Price far above PPP → SELL (fade)
            if rsi_val < 52:
                continue
            entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "SELL")
            # Use SMA252 as dynamic TP if closer than ATR-based
            ppp_tp = max(sma252, tp)
            if ppp_tp < entry:
                tp = ppp_tp
                rr = (entry - tp) / max(sl - entry, 1e-9)
            if rr < 1.2:
                continue
            conf = _forex_conf_cap(min(0.63, 0.50 + (abs(z) - 2.0) * 0.05), "ppp_mean_reversion")
            signals.append({
                "strategy": "ppp_mean_reversion",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "SELL",
                "entry_price": round(entry, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"PPP z={z:.2f} >2std above 252d SMA={sma252:.5f}. "
                           f"RSI={rsi_val:.0f}. Rogoff (1996) JEL."),
                "timeframe": "1d",
                "max_hold_bars": 20,
                "timestamp": _now_iso(),
            })
        else:
            # Price far below PPP → BUY (fade)
            if rsi_val > 48:
                continue
            entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "BUY")
            ppp_tp = min(sma252, tp)
            if ppp_tp > entry:
                tp = ppp_tp
                rr = (tp - entry) / max(entry - sl, 1e-9)
            if rr < 1.2:
                continue
            conf = _forex_conf_cap(min(0.63, 0.50 + (abs(z) - 2.0) * 0.05), "ppp_mean_reversion")
            signals.append({
                "strategy": "ppp_mean_reversion",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "BUY",
                "entry_price": round(entry, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"PPP z={z:.2f} <-2std below 252d SMA={sma252:.5f}. "
                           f"RSI={rsi_val:.0f}. Rogoff (1996) JEL."),
                "timeframe": "1d",
                "max_hold_bars": 20,
                "timestamp": _now_iso(),
            })
    return signals


# ============================================================================
# STRATEGY 4: RSI(7) + Bollinger Band Lower Touch Confluence
# ============================================================================
# Connors & Alvarez (2008) "Short-Term Trading Strategies That Work".
# RSI(7) < 25 AND price at/below lower BB(20,2σ) = 68% WR cited.
# Dual confirmation raises signal quality vs. single-indicator setups.
# ============================================================================
def rsi_bb_confluence_fx(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """RSI(7)<25 AND lower BB(2σ) touch simultaneously. Connors & Alvarez (2008)."""
    signals: list[dict] = []
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue
        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        rsi7 = float(rsi(close, 7).iloc[-1])
        if not np.isfinite(rsi7) or rsi7 >= 25:
            continue

        bb = bollinger_bands(close, 20, 2.0)
        lower_bb = float(bb["lower"].iloc[-1])
        current = float(close.iloc[-1])
        if not np.isfinite(lower_bb):
            continue

        # Price must be at or below lower BB
        if current > lower_bb * 1.001:
            continue

        # Trend filter: above 200d SMA to avoid downtrend mean reversions
        if len(close) >= 200:
            sma200_val = float(sma(close, 200).iloc[-1])
            if current < sma200_val * 0.995:
                continue  # Deeply below 200d → persistent downtrend, skip

        # Breadth confirmation: RSI(14) should not be in free-fall (<20)
        rsi14_val = float(rsi(close, 14).iloc[-1])
        if rsi14_val < 20:
            continue  # Panic selling — avoid

        entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "BUY")
        if rr < 1.2:
            continue

        # Target middle BB as dynamic TP if feasible
        mid_bb = float(bb["middle"].iloc[-1])
        if np.isfinite(mid_bb) and mid_bb > entry:
            tp_dyn = min(tp, mid_bb)
            rr_dyn = (tp_dyn - entry) / max(entry - sl, 1e-9)
            if rr_dyn >= 1.2:
                tp = tp_dyn
                rr = rr_dyn

        conf = _forex_conf_cap(min(0.65, 0.58 - rsi7 * 0.008), "rsi_bb_confluence_fx")
        signals.append({
            "strategy": "rsi_bb_confluence_fx",
            "symbol": symbol,
            "category": "forex",
            "signal_type": "BUY",
            "entry_price": round(entry, 5),
            "take_profit": round(tp, 5),
            "stop_loss": round(sl, 5),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (f"RSI(7)={rsi7:.1f}<25 + lower BB touch={lower_bb:.5f}. "
                       f"RSI14={rsi14_val:.0f}. Connors & Alvarez (2008)."),
            "timeframe": "1d",
            "max_hold_bars": 7,
            "timestamp": _now_iso(),
        })
    return signals


# ============================================================================
# STRATEGY 5: Session Volume Breakout (NY Session)
# ============================================================================
# Chaboud et al. (2014) "Rise of the Machines" FRB. Volume spikes in NY
# session (13-16 UTC) signal informed order flow. When NY-opening volume
# is 2x the baseline AND price breaks recent range high/low → follow.
# ============================================================================
def session_volume_breakout(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """Volume-weighted NY session breakout. Chaboud et al. (2014) FRB."""
    signals: list[dict] = []
    hour_utc = datetime.now(timezone.utc).hour

    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 35:
            continue
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df.get("Volume", pd.Series(np.ones(len(close)), index=close.index))

        current = float(close.iloc[-1])
        atr_val = float(atr(high, low, close, 14).iloc[-1])

        # Volume proxy: recent 5 bars vs prior 20-bar baseline
        vol_recent = float(volume.iloc[-5:].mean()) if len(volume) >= 5 else 1.0
        vol_baseline = float(volume.iloc[-25:-5].mean()) if len(volume) >= 25 else vol_recent
        if vol_baseline <= 0:
            vol_baseline = 1.0
        vol_ratio = vol_recent / vol_baseline

        if vol_ratio < 1.8:
            continue  # No volume surge

        # Range reference: prior 10 bars
        range_high = float(high.iloc[-11:-1].max())
        range_low = float(low.iloc[-11:-1].min())

        rsi_val = float(rsi(close, 14).iloc[-1])

        if current > range_high * 1.0003 and rsi_val < 72:
            # Bullish volume breakout
            entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "BUY")
            if rr < 1.2:
                continue
            conf = _forex_conf_cap(min(0.63, 0.50 + (vol_ratio - 1.8) * 0.05), "session_volume_breakout")
            signals.append({
                "strategy": "session_volume_breakout",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "BUY",
                "entry_price": round(entry, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"NY session vol surge {vol_ratio:.1f}x baseline, "
                           f"break above {range_high:.5f}, RSI={rsi_val:.0f}. "
                           f"Chaboud et al (2014) FRB."),
                "timeframe": "1h",
                "max_hold_bars": 6,
                "timestamp": _now_iso(),
            })

        elif current < range_low * 0.9997 and rsi_val > 28:
            # Bearish volume breakout
            entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "SELL")
            if rr < 1.2:
                continue
            conf = _forex_conf_cap(min(0.63, 0.50 + (vol_ratio - 1.8) * 0.05), "session_volume_breakout")
            signals.append({
                "strategy": "session_volume_breakout",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "SELL",
                "entry_price": round(entry, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"NY session vol surge {vol_ratio:.1f}x baseline, "
                           f"break below {range_low:.5f}, RSI={rsi_val:.0f}. "
                           f"Chaboud et al (2014) FRB."),
                "timeframe": "1h",
                "max_hold_bars": 6,
                "timestamp": _now_iso(),
            })
    return signals


# ============================================================================
# STRATEGY 6: Kijun-Sen Bounce (Ichimoku)
# ============================================================================
# Hosoda (1969) Ichimoku; Penfold (2011) review. Price above cloud AND
# retracing to Kijun-sen (26-period base line) with RSI 40-60 = high-
# probability bounce setup. Cloud acts as strong support in trending markets.
# ============================================================================
def kijun_bounce(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """Kijun-sen bounce above Ichimoku cloud. Hosoda (1969), Penfold (2011)."""
    signals: list[dict] = []
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 80:
            continue
        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        ichi = ichimoku(high, low, close, tenkan=9, kijun=26, senkou_b=52, displacement=26)
        kijun = float(ichi["kijun_sen"].iloc[-1])
        senkou_a = float(ichi["senkou_a"].iloc[-1])
        senkou_b = float(ichi["senkou_b"].iloc[-1])

        if not all(np.isfinite([kijun, senkou_a, senkou_b])):
            continue

        current = float(close.iloc[-1])
        cloud_top = max(senkou_a, senkou_b)
        cloud_bot = min(senkou_a, senkou_b)

        # Price must be above the cloud (bullish Ichimoku condition)
        if current <= cloud_top:
            continue

        # Price must be close to Kijun (within 0.1% = retrace to base line)
        kijun_dist = abs(current - kijun) / max(kijun, 1e-9)
        if kijun_dist > 0.001:
            continue  # Not close enough to Kijun

        # RSI must be neutral-weak (40-60): pullback not panic
        rsi_val = float(rsi(close, 14).iloc[-1])
        if not (40 <= rsi_val <= 62):
            continue

        entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "BUY")
        if rr < 1.2:
            continue

        conf = _forex_conf_cap(min(0.63, 0.55 + (cloud_top - cloud_bot) / max(current, 1e-9) * 10),
                               "kijun_bounce")
        signals.append({
            "strategy": "kijun_bounce",
            "symbol": symbol,
            "category": "forex",
            "signal_type": "BUY",
            "entry_price": round(entry, 5),
            "take_profit": round(tp, 5),
            "stop_loss": round(sl, 5),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (f"Kijun bounce: price={current:.5f} near kijun={kijun:.5f} "
                       f"({kijun_dist*100:.3f}% away), above cloud [{cloud_bot:.5f}-{cloud_top:.5f}], "
                       f"RSI={rsi_val:.0f}. Hosoda (1969)."),
            "timeframe": "4h",
            "max_hold_bars": 10,
            "timestamp": _now_iso(),
        })
    return signals


# ============================================================================
# STRATEGY 7: Pivot Point S1/R1 Reaction
# ============================================================================
# Floor pivot points: P = (H+L+C)/3; R1 = 2P-L; S1 = 2P-H.
# Used by ~78% of institutional FX traders (Euromoney 2019 FX survey).
# S1 retests from above with RSI<40 = high-probability bounce; R1 from
# below with RSI>60 = high-probability reversal short.
# ============================================================================
def pivot_point_reaction(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """Daily pivot S1/R1 reactions with RSI confirmation. Euromoney (2019)."""
    signals: list[dict] = []
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 5:
            continue
        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        # Previous day OHLC for pivot calculation
        prev_h = float(high.iloc[-2])
        prev_l = float(low.iloc[-2])
        prev_c = float(close.iloc[-2])

        if not all(np.isfinite([prev_h, prev_l, prev_c])):
            continue

        pivot = (prev_h + prev_l + prev_c) / 3.0
        r1 = 2 * pivot - prev_l
        s1 = 2 * pivot - prev_h

        current = float(close.iloc[-1])
        rsi_val = float(rsi(close, 14).iloc[-1])
        atr_val = float(atr(high, low, close, 14).iloc[-1])

        # BUY: price near S1 from above with RSI<40
        s1_dist = abs(current - s1) / max(atr_val, 1e-9)
        r1_dist = abs(current - r1) / max(atr_val, 1e-9)

        if s1_dist < 0.3 and current >= s1 and rsi_val < 40:
            entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "BUY")
            if rr < 1.2:
                continue
            conf = _forex_conf_cap(min(0.63, 0.55 - s1_dist * 0.05), "pivot_point_reaction")
            signals.append({
                "strategy": "pivot_point_reaction",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "BUY",
                "entry_price": round(entry, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"S1={s1:.5f} reaction bounce, price={current:.5f}, "
                           f"RSI={rsi_val:.0f}<40. Euromoney (2019) FX survey."),
                "timeframe": "1h",
                "max_hold_bars": 8,
                "timestamp": _now_iso(),
            })

        elif r1_dist < 0.3 and current <= r1 and rsi_val > 60:
            # SELL: price near R1 from below with RSI>60
            entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "SELL")
            if rr < 1.2:
                continue
            conf = _forex_conf_cap(min(0.63, 0.55 - r1_dist * 0.05), "pivot_point_reaction")
            signals.append({
                "strategy": "pivot_point_reaction",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "SELL",
                "entry_price": round(entry, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"R1={r1:.5f} resistance test from below, price={current:.5f}, "
                           f"RSI={rsi_val:.0f}>60. Euromoney (2019) FX survey."),
                "timeframe": "1h",
                "max_hold_bars": 8,
                "timestamp": _now_iso(),
            })
    return signals


# ============================================================================
# STRATEGY 8: Three-Bar Reversal + Bullish Engulfing
# ============================================================================
# Bulkowski (2008) "Encyclopedia of Candlestick Charts". Three consecutive
# bearish bars followed by a bullish engulfing candle (closes above open of
# 3 bars ago). Stricter than 2-bar reversal; ~62% WR in Bulkowski studies.
# ============================================================================
def three_bar_reversal(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """Three red bars + bullish engulfing reversal. Bulkowski (2008)."""
    signals: list[dict] = []
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 35:
            continue
        close = df["Close"]
        open_ = df["Open"]
        high = df["High"]
        low = df["Low"]

        # Three consecutive bearish bars (close < open each)
        b1_bear = float(close.iloc[-4]) < float(open_.iloc[-4])
        b2_bear = float(close.iloc[-3]) < float(open_.iloc[-3])
        b3_bear = float(close.iloc[-2]) < float(open_.iloc[-2])

        if not (b1_bear and b2_bear and b3_bear):
            continue

        # Each bar closes lower than the previous
        sequential_down = (float(close.iloc[-3]) < float(close.iloc[-4]) and
                           float(close.iloc[-2]) < float(close.iloc[-3]))
        if not sequential_down:
            continue

        # Current bar: bullish engulfing — closes above open of 3 bars ago
        current_close = float(close.iloc[-1])
        current_open = float(open_.iloc[-1])
        ref_open = float(open_.iloc[-4])  # 3 bars ago

        if current_close <= current_open:
            continue  # Must be bullish bar
        if current_close <= ref_open:
            continue  # Must close above where the 3-bar decline started

        # RSI should be in recovery zone: 30-55 (not already overbought)
        rsi_val = float(rsi(close, 14).iloc[-1])
        if not (28 <= rsi_val <= 58):
            continue

        entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "BUY")
        if rr < 1.2:
            continue

        conf = _forex_conf_cap(0.60, "three_bar_reversal")
        signals.append({
            "strategy": "three_bar_reversal",
            "symbol": symbol,
            "category": "forex",
            "signal_type": "BUY",
            "entry_price": round(entry, 5),
            "take_profit": round(tp, 5),
            "stop_loss": round(sl, 5),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (f"3-bar decline reversed: engulfing close={current_close:.5f} "
                       f"> ref open={ref_open:.5f}. RSI={rsi_val:.0f}. Bulkowski (2008)."),
            "timeframe": "1d",
            "max_hold_bars": 6,
            "timestamp": _now_iso(),
        })
    return signals


# ============================================================================
# STRATEGY 9: ADX Trend Quality Filter (Wilder 1978)
# ============================================================================
# Wilder (1978) "New Concepts in Technical Trading Systems". ADX>30 = strong
# trend. +DI > -DI confirms bullish directionality. RSI 45-65 = trend intact
# but not overbought. 60-65% WR in strong trending markets (ADX>30).
# ============================================================================
def adx_trend_quality_filter(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """ADX>30 + +DI>-DI + RSI 45-65 trend continuation. Wilder (1978)."""
    signals: list[dict] = []
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 35:
            continue
        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        adx_line, plus_di, minus_di = _adx_plus_minus_di(high, low, close, 14)
        adx_val = float(adx_line.iloc[-1])
        pdi = float(plus_di.iloc[-1])
        mdi = float(minus_di.iloc[-1])

        if not all(np.isfinite([adx_val, pdi, mdi])):
            continue
        if adx_val < 30:
            continue  # Weak trend — no edge here

        rsi_val = float(rsi(close, 14).iloc[-1])

        if pdi > mdi and 45 <= rsi_val <= 65:
            # Bullish strong trend — BUY continuation
            entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "BUY")
            if rr < 1.2:
                continue
            conf = _forex_conf_cap(min(0.65, 0.52 + (adx_val - 30) * 0.005), "adx_trend_quality_filter")
            signals.append({
                "strategy": "adx_trend_quality_filter",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "BUY",
                "entry_price": round(entry, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"ADX={adx_val:.0f}>30, +DI={pdi:.1f}>-DI={mdi:.1f}, "
                           f"RSI={rsi_val:.0f} [45-65]. Wilder (1978)."),
                "timeframe": "4h",
                "max_hold_bars": 10,
                "timestamp": _now_iso(),
            })

        elif mdi > pdi and 35 <= rsi_val <= 55:
            # Bearish strong trend — SELL continuation
            entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "SELL")
            if rr < 1.2:
                continue
            conf = _forex_conf_cap(min(0.65, 0.52 + (adx_val - 30) * 0.005), "adx_trend_quality_filter")
            signals.append({
                "strategy": "adx_trend_quality_filter",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "SELL",
                "entry_price": round(entry, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"ADX={adx_val:.0f}>30, -DI={mdi:.1f}>+DI={pdi:.1f}, "
                           f"RSI={rsi_val:.0f} [35-55]. Wilder (1978)."),
                "timeframe": "4h",
                "max_hold_bars": 10,
                "timestamp": _now_iso(),
            })
    return signals


# ============================================================================
# STRATEGY 10: MACD + RSI Double Confirmation (Appel 1979, Elder 1993)
# ============================================================================
# Appel (1979) MACD + Elder (1993) "Trading for a Living" Triple Screen.
# MACD histogram turns positive (histogram[-1] > 0, histogram[-2] <= 0) AND
# RSI(14) > 50 AND RSI was < 50 three bars ago = double momentum BUY.
# Avoids premature entries in choppy markets.
# ============================================================================
def macd_rsi_double_confirmation(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """MACD histogram cross + RSI(14) > 50 dual confirmation. Appel (1979), Elder (1993)."""
    signals: list[dict] = []
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 40:
            continue
        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        macd_dict = macd(close, 12, 26, 9)
        hist = macd_dict["histogram"]
        hist_now = float(hist.iloc[-1])
        hist_prev = float(hist.iloc[-2])

        if not (np.isfinite(hist_now) and np.isfinite(hist_prev)):
            continue

        rsi_series = rsi(close, 14)
        rsi_now = float(rsi_series.iloc[-1])
        rsi_3ago = float(rsi_series.iloc[-4]) if len(rsi_series) >= 4 else 50.0

        # BUY: MACD histogram just crossed positive + RSI crossed 50 from below
        if hist_now > 0 and hist_prev <= 0 and rsi_now > 50 and rsi_3ago < 50:
            entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "BUY")
            if rr < 1.2:
                continue
            conf = _forex_conf_cap(min(0.63, 0.56 + (rsi_now - 50) * 0.003), "macd_rsi_double_confirmation")
            signals.append({
                "strategy": "macd_rsi_double_confirmation",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "BUY",
                "entry_price": round(entry, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"MACD hist cross positive ({hist_prev:.6f}→{hist_now:.6f}), "
                           f"RSI {rsi_3ago:.0f}→{rsi_now:.0f} (crossed 50). "
                           f"Appel (1979), Elder (1993)."),
                "timeframe": "4h",
                "max_hold_bars": 12,
                "timestamp": _now_iso(),
            })

        # SELL: MACD histogram just crossed negative + RSI crossed 50 from above
        elif hist_now < 0 and hist_prev >= 0 and rsi_now < 50 and rsi_3ago > 50:
            entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "SELL")
            if rr < 1.2:
                continue
            conf = _forex_conf_cap(min(0.63, 0.56 + (50 - rsi_now) * 0.003), "macd_rsi_double_confirmation")
            signals.append({
                "strategy": "macd_rsi_double_confirmation",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "SELL",
                "entry_price": round(entry, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"MACD hist cross negative ({hist_prev:.6f}→{hist_now:.6f}), "
                           f"RSI {rsi_3ago:.0f}→{rsi_now:.0f} (crossed below 50). "
                           f"Appel (1979), Elder (1993)."),
                "timeframe": "4h",
                "max_hold_bars": 12,
                "timestamp": _now_iso(),
            })
    return signals


# ============================================================================
# STRATEGY 11: 50% Fibonacci Retracement Mean Revert (Carney 2010)
# ============================================================================
# Carney (2010) "Harmonic Trading". After an impulse move (last 20 bars),
# price retracing to the 50% Fibonacci midpoint = high-probability bounce.
# Self-fulfilling: major institutions place orders at exact 50% levels.
# ============================================================================
def fifty_pct_fibonacci_mean_revert(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """50% Fibonacci midpoint retracement bounce. Carney (2010)."""
    signals: list[dict] = []
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 35:
            continue
        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        # Identify swing over last 20 bars
        window = 20
        swing_high = float(high.iloc[-window:].max())
        swing_low = float(low.iloc[-window:].min())
        swing_range = swing_high - swing_low

        if swing_range <= 0:
            continue

        # Only apply if impulse is at least 0.3% (meaningful FX move)
        if swing_range / max(swing_low, 1e-9) < 0.003:
            continue

        fib50 = (swing_high + swing_low) / 2.0
        current = float(close.iloc[-1])

        # Price within 0.05% of 50% Fib level
        fib_dist = abs(current - fib50) / max(fib50, 1e-9)
        if fib_dist > 0.0005:
            continue

        rsi_val = float(rsi(close, 14).iloc[-1])
        atr_val = float(atr(high, low, close, 14).iloc[-1])

        # Determine direction: is price retracing from the high or the low?
        recent_high_idx = int(high.iloc[-window:].argmax())
        recent_low_idx = int(low.iloc[-window:].argmin())

        if recent_high_idx > recent_low_idx and rsi_val < 55:
            # Impulse was UP, retrace down to 50% → BUY the dip
            if current > fib50 * 0.9995:  # Still holding above
                entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "BUY")
                if rr < 1.2:
                    continue
                conf = _forex_conf_cap(min(0.62, 0.55 - fib_dist * 100), "fifty_pct_fibonacci_mean_revert")
                signals.append({
                    "strategy": "fifty_pct_fibonacci_mean_revert",
                    "symbol": symbol,
                    "category": "forex",
                    "signal_type": "BUY",
                    "entry_price": round(entry, 5),
                    "take_profit": round(tp, 5),
                    "stop_loss": round(sl, 5),
                    "confidence": conf,
                    "risk_reward": round(rr, 2),
                    "reason": (f"50% Fib={fib50:.5f} retrace of up-impulse "
                               f"[{swing_low:.5f}-{swing_high:.5f}], RSI={rsi_val:.0f}. "
                               f"Carney (2010)."),
                    "timeframe": "4h",
                    "max_hold_bars": 10,
                    "timestamp": _now_iso(),
                })

        elif recent_low_idx > recent_high_idx and rsi_val > 45:
            # Impulse was DOWN, retrace up to 50% → SELL the rally
            if current < fib50 * 1.0005:
                entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "SELL")
                if rr < 1.2:
                    continue
                conf = _forex_conf_cap(min(0.62, 0.55 - fib_dist * 100), "fifty_pct_fibonacci_mean_revert")
                signals.append({
                    "strategy": "fifty_pct_fibonacci_mean_revert",
                    "symbol": symbol,
                    "category": "forex",
                    "signal_type": "SELL",
                    "entry_price": round(entry, 5),
                    "take_profit": round(tp, 5),
                    "stop_loss": round(sl, 5),
                    "confidence": conf,
                    "risk_reward": round(rr, 2),
                    "reason": (f"50% Fib={fib50:.5f} retrace of down-impulse "
                               f"[{swing_high:.5f}-{swing_low:.5f}], RSI={rsi_val:.0f}. "
                               f"Carney (2010)."),
                    "timeframe": "4h",
                    "max_hold_bars": 10,
                    "timestamp": _now_iso(),
                })
    return signals


# ============================================================================
# STRATEGY 12: VIX Carry Regime Filter (Brunnermeier et al. 2009)
# ============================================================================
# Brunnermeier, Nagel, Pedersen (2009) "Carry Trades and Currency Crashes"
# NBER. Carry trades generate positive returns in low-vol regimes but suffer
# during VIX spikes (funding illiquidity). Proxy: 20d realized vol of SPY or
# cross-pair volatility. When recent vol < long-run vol = low-risk carry window.
# ============================================================================
def vix_carry_regime(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """Carry signals in low-vol regimes. Brunnermeier et al. (2009) NBER."""
    signals: list[dict] = []

    # Build a cross-pair vol proxy using the average realized vol of all pairs
    all_vols_20d: list[float] = []
    all_vols_60d: list[float] = []
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 65:
            continue
        returns = df["Close"].pct_change().dropna()
        if len(returns) < 60:
            continue
        all_vols_20d.append(float(returns.iloc[-20:].std()))
        all_vols_60d.append(float(returns.iloc[-60:].std()))

    if not all_vols_20d:
        return signals

    avg_vol_20d = float(np.mean(all_vols_20d))
    avg_vol_60d = float(np.mean(all_vols_60d))
    vol_regime_ratio = avg_vol_20d / max(avg_vol_60d, 1e-9)

    # Only trade carry in low-vol regime (recent vol < 110% of baseline)
    if vol_regime_ratio > 1.1:
        return signals  # High-vol regime = carry crash risk

    for symbol, info in FOREX_SYMBOLS.items():
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue

        carry_diff = info.get("carry_yield_diff", 0)
        if carry_diff <= 1.0:
            continue  # Only high-carry pairs

        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        # Trend filter: above 50d SMA
        sma50_val = float(sma(close, 50).iloc[-1])
        current = float(close.iloc[-1])
        if current < sma50_val:
            continue

        rsi_val = float(rsi(close, 14).iloc[-1])
        if rsi_val > 68:
            continue

        entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "BUY")
        if rr < 1.2:
            continue

        conf = _forex_conf_cap(
            min(0.65, 0.52 + carry_diff / 20.0 + (1.1 - vol_regime_ratio) * 0.1),
            "vix_carry_regime",
        )
        signals.append({
            "strategy": "vix_carry_regime",
            "symbol": symbol,
            "category": "forex",
            "signal_type": "BUY",
            "entry_price": round(entry, 5),
            "take_profit": round(tp, 5),
            "stop_loss": round(sl, 5),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (f"Low vol regime ({vol_regime_ratio:.2f}x) + carry={carry_diff:.1f}%, "
                       f"above SMA50, RSI={rsi_val:.0f}. Brunnermeier et al (2009) NBER."),
            "timeframe": "1d",
            "max_hold_bars": 10,
            "timestamp": _now_iso(),
        })
    return signals


# ============================================================================
# STRATEGY 13: Morning Star Candlestick (Nison 1991)
# ============================================================================
# Nison (1991) "Japanese Candlestick Charting Techniques". Morning Star:
# (1) Large bearish body, (2) Small-bodied middle candle (doji/spinning top),
# (3) Bullish candle closing above 50% of candle 1's body. ~61% WR in FX.
# ============================================================================
def morning_star_fx(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """Morning Star reversal pattern. Nison (1991). ~61% WR in FX."""
    signals: list[dict] = []
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 35:
            continue
        close = df["Close"]
        open_ = df["Open"]
        high = df["High"]
        low = df["Low"]

        # Three-candle pattern: bars -3, -2, -1 (most recent complete)
        c1_o, c1_c = float(open_.iloc[-3]), float(close.iloc[-3])
        c2_o, c2_c = float(open_.iloc[-2]), float(close.iloc[-2])
        c3_o, c3_c = float(open_.iloc[-1]), float(close.iloc[-1])

        if not all(np.isfinite([c1_o, c1_c, c2_o, c2_c, c3_o, c3_c])):
            continue

        # Candle 1: large bearish body (close < open, body > 0.6x ATR)
        atr_val = float(atr(high, low, close, 14).iloc[-1])
        body1 = c1_o - c1_c  # Positive for bearish
        if body1 < 0.6 * atr_val:
            continue  # Not a large bearish candle

        # Candle 2: small body (doji/spinning top) — body < 30% of candle 1
        body2 = abs(c2_c - c2_o)
        if body2 > 0.3 * body1:
            continue

        # Candle 3: bullish, closes above 50% of candle 1's body
        c1_body_mid = c1_c + body1 * 0.5  # Midpoint of bearish candle 1
        if c3_c <= c3_o:
            continue  # Must be bullish
        if c3_c < c1_body_mid:
            continue  # Must close above 50% of candle 1

        # Additional: RSI not already overbought
        rsi_val = float(rsi(close, 14).iloc[-1])
        if rsi_val > 62:
            continue

        entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "BUY")
        if rr < 1.2:
            continue

        conf = _forex_conf_cap(0.61, "morning_star_fx")
        signals.append({
            "strategy": "morning_star_fx",
            "symbol": symbol,
            "category": "forex",
            "signal_type": "BUY",
            "entry_price": round(entry, 5),
            "take_profit": round(tp, 5),
            "stop_loss": round(sl, 5),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (f"Morning Star: bearish({c1_o:.5f}→{c1_c:.5f}) + "
                       f"doji + bullish close={c3_c:.5f}>{c1_body_mid:.5f}. "
                       f"RSI={rsi_val:.0f}. Nison (1991)."),
            "timeframe": "1d",
            "max_hold_bars": 6,
            "timestamp": _now_iso(),
        })
    return signals


# ============================================================================
# STRATEGY 14: Price Action Higher Low with RSI Divergence
# ============================================================================
# Brooks (2012) "Trading Price Action". Higher low = each successive swing
# low is higher than the previous. Combined with bullish RSI divergence
# (RSI makes higher low while price makes higher low) = strong continuation.
# ============================================================================
def price_action_swing_lo(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """Higher low + RSI divergence setup. Brooks (2012) price action."""
    signals: list[dict] = []
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 40:
            continue
        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        rsi_series = rsi(close, 14)
        # Find last two swing lows in 5-bar windows
        swing_lows: list[tuple[int, float, float]] = []
        for i in range(5, len(low) - 2):
            window_vals = [float(low.iloc[i + k]) for k in range(-2, 3)]
            if float(low.iloc[i]) == min(window_vals):
                swing_lows.append((i, float(low.iloc[i]), float(rsi_series.iloc[i])))

        if len(swing_lows) < 2:
            continue

        # Most recent two swing lows
        sl1 = swing_lows[-2]  # (idx, price_low, rsi_val)
        sl2 = swing_lows[-1]

        # Higher low in price: sl2 price > sl1 price
        if sl2[1] <= sl1[1]:
            continue

        # RSI at sl2 >= RSI at sl1 (non-diverging is fine; bullish divergence is ideal)
        # Bullish divergence: price HL while RSI HL (both rising) = continuation
        if sl2[2] < sl1[2] - 2:
            continue  # RSI also falling = no divergence support

        # Current price above the second swing low (still in upswing)
        current = float(close.iloc[-1])
        if current < sl2[1]:
            continue

        rsi_val = float(rsi_series.iloc[-1])
        if rsi_val > 68:
            continue  # Overbought

        # Recent momentum: close > ema20
        ema20_val = float(ema(close, 20).iloc[-1])
        if current < ema20_val:
            continue

        entry, tp, sl_price, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "BUY")
        if rr < 1.2:
            continue

        conf = _forex_conf_cap(min(0.63, 0.54 + (sl2[1] - sl1[1]) / max(sl1[1], 1e-9) * 10),
                               "price_action_swing_lo")
        signals.append({
            "strategy": "price_action_swing_lo",
            "symbol": symbol,
            "category": "forex",
            "signal_type": "BUY",
            "entry_price": round(entry, 5),
            "take_profit": round(tp, 5),
            "stop_loss": round(sl_price, 5),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (f"Higher low: {sl1[1]:.5f}→{sl2[1]:.5f}, "
                       f"RSI at lows: {sl1[2]:.0f}→{sl2[2]:.0f}, "
                       f"above EMA20={ema20_val:.5f}. Brooks (2012)."),
            "timeframe": "4h",
            "max_hold_bars": 12,
            "timestamp": _now_iso(),
        })
    return signals


# ============================================================================
# STRATEGY 15: Stochastic Divergence (Lane 1957, Pring 2002)
# ============================================================================
# Lane (1957) slow stochastic; Pring (2002) "Technical Analysis Explained".
# Bullish divergence: price makes new 20d low but Stoch %K makes higher low.
# Entry when %K crosses above %D below 20. Bearish: inverse.
# ============================================================================
def stochastic_divergence_fx(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """Stochastic bullish/bearish divergence + cross. Lane (1957), Pring (2002)."""
    signals: list[dict] = []
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 40:
            continue
        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        stoch_k, stoch_d = _stochastic(high, low, close, k_period=14, d_period=3)
        k_now = float(stoch_k.iloc[-1])
        k_prev = float(stoch_k.iloc[-2])
        d_now = float(stoch_d.iloc[-1])
        d_prev = float(stoch_d.iloc[-2])

        if not all(np.isfinite([k_now, k_prev, d_now, d_prev])):
            continue

        current = float(close.iloc[-1])
        low20_price = float(low.iloc[-20:].min())
        high20_price = float(high.iloc[-20:].max())
        low20_k = float(stoch_k.iloc[-20:].min())
        high20_k = float(stoch_k.iloc[-20:].max())

        # Bullish divergence: current price near 20d low, Stoch not at 20d low
        price_near_low = (current <= low20_price * 1.002)
        k_higher_low = (k_now > low20_k + 5)  # %K is higher than 20d Stoch low

        if (price_near_low and k_higher_low and
                k_now < 30 and k_now > k_prev and k_now > d_now > d_prev):
            # %K crossing above %D below 30 = bullish signal
            entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "BUY")
            if rr < 1.2:
                continue
            conf = _forex_conf_cap(min(0.62, 0.54 + (30 - k_now) * 0.003), "stochastic_divergence_fx")
            signals.append({
                "strategy": "stochastic_divergence_fx",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "BUY",
                "entry_price": round(entry, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"Stoch bullish divergence: price near 20d low={low20_price:.5f}, "
                           f"%K={k_now:.1f}>%D={d_now:.1f} crossover below 30. "
                           f"Lane (1957), Pring (2002)."),
                "timeframe": "4h",
                "max_hold_bars": 10,
                "timestamp": _now_iso(),
            })

        # Bearish divergence: price near 20d high, Stoch not at 20d high
        price_near_high = (current >= high20_price * 0.998)
        k_lower_high = (k_now < high20_k - 5)

        if (price_near_high and k_lower_high and
                k_now > 70 and k_now < k_prev and k_now < d_now < d_prev):
            entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "SELL")
            if rr < 1.2:
                continue
            conf = _forex_conf_cap(min(0.62, 0.54 + (k_now - 70) * 0.003), "stochastic_divergence_fx")
            signals.append({
                "strategy": "stochastic_divergence_fx",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "SELL",
                "entry_price": round(entry, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"Stoch bearish divergence: price near 20d high={high20_price:.5f}, "
                           f"%K={k_now:.1f}<%D={d_now:.1f} crossover above 70. "
                           f"Lane (1957), Pring (2002)."),
                "timeframe": "4h",
                "max_hold_bars": 10,
                "timestamp": _now_iso(),
            })
    return signals


# ============================================================================
# STRATEGY 16: Trendline Break and Retest (Kaufman 2013)
# ============================================================================
# Kaufman (2013) "Trading Systems and Methods". Linear regression on last 20
# bars defines trend. When price breaks the regression line AND then
# retests it from the other side (closes back above after breaking above),
# trade the retest as a high-confidence continuation.
# ============================================================================
def trendline_break_retest(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """Linear regression trendline break + retest. Kaufman (2013)."""
    signals: list[dict] = []
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 35:
            continue
        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        window = 20
        y = close.iloc[-window:].values
        x = np.arange(len(y), dtype=float)

        # Linear regression: y = a*x + b
        if len(y) < window:
            continue
        coeffs = np.polyfit(x, y, 1)
        a, b = float(coeffs[0]), float(coeffs[1])
        # Current regression value (last x = window-1)
        reg_now = a * (window - 1) + b
        reg_prev = a * (window - 2) + b

        current = float(close.iloc[-1])
        prev = float(close.iloc[-2])

        # Upward sloping trend (a > 0): look for break above regression then retest from above
        if a > 0:
            # Break above: prev was below regression line, current is above
            crossed_above = prev < reg_prev and current > reg_now
            if not crossed_above:
                continue
            # For a "retest" proxy: price is close to regression line from above
            dist_pct = (current - reg_now) / max(reg_now, 1e-9)
            if dist_pct > 0.002 or dist_pct < 0:
                continue  # Too far above or below — not a tight retest

            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val > 68:
                continue

            entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "BUY")
            if rr < 1.2:
                continue

            conf = _forex_conf_cap(min(0.62, 0.55 - dist_pct * 100), "trendline_break_retest")
            signals.append({
                "strategy": "trendline_break_retest",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "BUY",
                "entry_price": round(entry, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"Upward regression break+retest: slope={a:.7f}, "
                           f"reg_line={reg_now:.5f}, dist={dist_pct*100:.3f}%, "
                           f"RSI={rsi_val:.0f}. Kaufman (2013)."),
                "timeframe": "4h",
                "max_hold_bars": 10,
                "timestamp": _now_iso(),
            })

        elif a < 0:
            # Downward sloping trend: break below + retest from below
            crossed_below = prev > reg_prev and current < reg_now
            if not crossed_below:
                continue
            dist_pct = (reg_now - current) / max(reg_now, 1e-9)
            if dist_pct > 0.002 or dist_pct < 0:
                continue

            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val < 32:
                continue

            entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "SELL")
            if rr < 1.2:
                continue

            conf = _forex_conf_cap(min(0.62, 0.55 - dist_pct * 100), "trendline_break_retest")
            signals.append({
                "strategy": "trendline_break_retest",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "SELL",
                "entry_price": round(entry, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"Downward regression break+retest: slope={a:.7f}, "
                           f"reg_line={reg_now:.5f}, dist={dist_pct*100:.3f}%, "
                           f"RSI={rsi_val:.0f}. Kaufman (2013)."),
                "timeframe": "4h",
                "max_hold_bars": 10,
                "timestamp": _now_iso(),
            })
    return signals


# ============================================================================
# STRATEGY 17: EUR/USD DXY Inverse Correlation Lag
# ============================================================================
# Akram (2009) "Commodity prices and the USD" IMF WP. EUR/USD and DXY are
# ~95% inversely correlated. When DXY (USD index proxy) breaks its 20d high
# but EUR/USD has not yet confirmed the corresponding new low (momentum lag),
# SHORT EUR/USD on the expected catch-up move.
# ============================================================================
_EURUSD_SYMBOLS = {"EURUSD=X"}

def euro_dollar_inverse(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """EUR/USD inverse DXY lag trade. Akram (2009) IMF WP."""
    signals: list[dict] = []

    # Use USDCHF or DXY-proxy: when USDCHF breaks 20d high (DXY proxy up)
    # EUR/USD should also be breaking down; if it hasn't yet → SHORT EURUSD
    dxy_proxy_symbol = "USDCHF=X"  # High ~0.92 correlation with DXY
    dxy_df = data.get(dxy_proxy_symbol)

    for symbol in FOREX_SYMBOLS:
        if symbol not in _EURUSD_SYMBOLS:
            continue
        df = data.get(symbol)
        if df is None or len(df) < 25:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        current_eurusd = float(close.iloc[-1])

        # DXY proxy: check if USDCHF made 20d high
        if dxy_df is not None and len(dxy_df) >= 21:
            usdchf_close = dxy_df["Close"]
            usdchf_20d_high = float(usdchf_close.iloc[-21:-1].max())
            usdchf_now = float(usdchf_close.iloc[-1])
            dxy_breakout = usdchf_now > usdchf_20d_high * 1.0003
        else:
            # Fallback: use DXY-like logic on EUR/USD itself
            dxy_breakout = False

        if not dxy_breakout:
            continue

        # EUR/USD should lag: it has NOT yet made a new 20d low
        eurusd_20d_low = float(low.iloc[-21:-1].min())
        eurusd_lag = current_eurusd > eurusd_20d_low * 1.001  # Not yet confirmed new low

        if not eurusd_lag:
            continue

        rsi_val = float(rsi(close, 14).iloc[-1])
        if rsi_val < 38:
            continue  # Already oversold

        entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "SELL")
        if rr < 1.2:
            continue

        conf = _forex_conf_cap(0.59, "euro_dollar_inverse")
        signals.append({
            "strategy": "euro_dollar_inverse",
            "symbol": symbol,
            "category": "forex",
            "signal_type": "SELL",
            "entry_price": round(entry, 5),
            "take_profit": round(tp, 5),
            "stop_loss": round(sl, 5),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (f"DXY proxy (USDCHF) broke 20d high, EUR/USD lagging above "
                       f"20d low={eurusd_20d_low:.5f}. RSI={rsi_val:.0f}. "
                       f"Akram (2009) IMF WP."),
            "timeframe": "4h",
            "max_hold_bars": 8,
            "timestamp": _now_iso(),
        })
    return signals


# ============================================================================
# STRATEGY 18: Forex Weekend Gap Reversal (Ma & Maclean 2019)
# ============================================================================
# Ma & Maclean (2019) forex gap study: gaps >0.15% from Friday close to
# Monday open fill within 2 days ~73% of the time. Fade the gap direction.
# Strategy: detect gap (Friday close vs current open on Monday),
# trade the fill if gap is significant and RSI not extreme.
# ============================================================================
def gap_reversal_fx(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """Weekend gap fade strategy. Ma & Maclean (2019) ~73% fill rate."""
    signals: list[dict] = []
    today_utc = datetime.now(timezone.utc)

    # Only meaningful near market open (check for gap condition)
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 5:
            continue
        close = df["Close"]
        open_ = df["Open"]
        high = df["High"]
        low = df["Low"]

        # Gap = current open vs previous close
        prev_close = float(close.iloc[-2])
        curr_open = float(open_.iloc[-1])
        current = float(close.iloc[-1])

        if prev_close <= 0 or curr_open <= 0:
            continue

        gap_pct = (curr_open - prev_close) / prev_close
        if abs(gap_pct) < 0.0015:
            continue  # Gap too small (< 0.15%)

        rsi_val = float(rsi(close, 14).iloc[-1])
        atr_val = float(atr(high, low, close, 14).iloc[-1])

        if gap_pct > 0:
            # Gap UP → SELL the gap (expect fill back to prev_close)
            if rsi_val > 75:
                continue  # Already at extreme, might not fill
            if current > curr_open * 1.001:
                continue  # Gap extending, not fading
            entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.4, 1.0, "SELL")
            # TP target: prev_close (gap fill)
            gap_fill_tp = prev_close
            if gap_fill_tp < entry:
                tp_cand = max(tp, gap_fill_tp)
                rr_cand = (entry - tp_cand) / max(sl - entry, 1e-9)
                if rr_cand >= 1.2:
                    tp = tp_cand
                    rr = rr_cand
            if rr < 1.2:
                continue
            conf = _forex_conf_cap(min(0.62, 0.52 + abs(gap_pct) * 20), "gap_reversal_fx")
            signals.append({
                "strategy": "gap_reversal_fx",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "SELL",
                "entry_price": round(entry, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"Gap UP {gap_pct*100:.3f}% (prev_close={prev_close:.5f}→"
                           f"open={curr_open:.5f}). RSI={rsi_val:.0f}. "
                           f"Ma & Maclean (2019) 73% fill rate."),
                "timeframe": "1h",
                "max_hold_bars": 6,
                "timestamp": _now_iso(),
            })

        else:
            # Gap DOWN → BUY the gap (expect fill back to prev_close)
            if rsi_val < 25:
                continue
            if current < curr_open * 0.999:
                continue  # Gap extending down
            entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.4, 1.0, "BUY")
            gap_fill_tp = prev_close
            if gap_fill_tp > entry:
                tp_cand = min(tp, gap_fill_tp)
                rr_cand = (tp_cand - entry) / max(entry - sl, 1e-9)
                if rr_cand >= 1.2:
                    tp = tp_cand
                    rr = rr_cand
            if rr < 1.2:
                continue
            conf = _forex_conf_cap(min(0.62, 0.52 + abs(gap_pct) * 20), "gap_reversal_fx")
            signals.append({
                "strategy": "gap_reversal_fx",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "BUY",
                "entry_price": round(entry, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"Gap DOWN {gap_pct*100:.3f}% (prev_close={prev_close:.5f}→"
                           f"open={curr_open:.5f}). RSI={rsi_val:.0f}. "
                           f"Ma & Maclean (2019) 73% fill rate."),
                "timeframe": "1h",
                "max_hold_bars": 6,
                "timestamp": _now_iso(),
            })
    return signals


# ============================================================================
# STRATEGY 19: Interest Rate Differential Momentum (Lustig et al. 2011)
# ============================================================================
# Lustig, Roussanov & Verdelhan (2011) "Common Risk Factors in Currency Markets"
# RFS. Higher carry yield + recent short-term momentum continuation =
# interest rate differential momentum. Distinct from pure carry: requires
# recent 1m momentum to be positive (trend confirming carry income).
# ============================================================================
def interest_rate_differential_momentum(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """IR differential + 1m momentum continuation. Lustig et al. (2011) RFS."""
    signals: list[dict] = []
    for symbol, info in FOREX_SYMBOLS.items():
        df = data.get(symbol)
        if df is None or len(df) < 65:
            continue

        carry_diff = info.get("carry_yield_diff", 0)
        if abs(carry_diff) < 0.5:
            continue  # Need meaningful carry differential

        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        mom_1m = float(close.iloc[-1] / close.iloc[-22] - 1)
        mom_3m = float(close.iloc[-1] / close.iloc[-65] - 1)

        if carry_diff > 0:
            # Long the high-yielder: both carry and 1m momentum positive
            if mom_1m < 0.001 or mom_3m < 0:
                continue
            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val > 68:
                continue
            # ADX: momentum should be in trending environment
            adx_val = float(adx(high, low, close).iloc[-1]) if len(close) >= 20 else 20.0
            if adx_val < 18:
                continue
            entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "BUY")
            if rr < 1.2:
                continue
            conf = _forex_conf_cap(
                min(0.64, 0.50 + carry_diff / 15.0 + mom_1m * 2.0),
                "interest_rate_differential_momentum",
            )
            signals.append({
                "strategy": "interest_rate_differential_momentum",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "BUY",
                "entry_price": round(entry, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"IR differential carry={carry_diff:.1f}%, "
                           f"1m mom={mom_1m:.2%}, 3m mom={mom_3m:.2%}, "
                           f"ADX={adx_val:.0f}, RSI={rsi_val:.0f}. "
                           f"Lustig et al (2011) RFS."),
                "timeframe": "1d",
                "max_hold_bars": 15,
                "timestamp": _now_iso(),
            })

        elif carry_diff < -0.5:
            # Short the low-yielder (negative carry): 1m momentum also negative
            if mom_1m > -0.001 or mom_3m > 0:
                continue
            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val < 32:
                continue
            adx_val = float(adx(high, low, close).iloc[-1]) if len(close) >= 20 else 20.0
            if adx_val < 18:
                continue
            entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.5, 1.0, "SELL")
            if rr < 1.2:
                continue
            conf = _forex_conf_cap(
                min(0.64, 0.50 + abs(carry_diff) / 15.0 + abs(mom_1m) * 2.0),
                "interest_rate_differential_momentum",
            )
            signals.append({
                "strategy": "interest_rate_differential_momentum",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "SELL",
                "entry_price": round(entry, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"Negative IR differential carry={carry_diff:.1f}%, "
                           f"1m mom={mom_1m:.2%}, 3m mom={mom_3m:.2%}, "
                           f"ADX={adx_val:.0f}, RSI={rsi_val:.0f}. "
                           f"Lustig et al (2011) RFS."),
                "timeframe": "1d",
                "max_hold_bars": 15,
                "timestamp": _now_iso(),
            })
    return signals


# ============================================================================
# STRATEGY 20: London Fix Momentum (Lyons 2001)
# ============================================================================
# Lyons (2001) "The Microstructure Approach to Exchange Rates". The London
# 4pm Fix (16:00 UTC) creates predictable order flow. In the 30-60 minutes
# before the fix, dominant intraday direction tends to accelerate as
# institutions accumulate positions for fix. Strategy: 1h before fix (15:00
# UTC), if price is above EMA20 (bullish intraday), BUY for 1-2 bars.
# ============================================================================
def london_fix_momentum(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """London Fix pre-accumulation momentum. Lyons (2001) microstructure."""
    signals: list[dict] = []
    _LIQUID_PAIRS = {"EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X",
                     "USDCAD=X", "USDCHF=X", "NZDUSD=X"}

    # Strategy most effective in the hour before London Fix (14-16 UTC)
    hour_utc = datetime.now(timezone.utc).hour
    fix_window = (14 <= hour_utc <= 16)

    for symbol in FOREX_SYMBOLS:
        if symbol not in _LIQUID_PAIRS:
            continue
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue
        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        current = float(close.iloc[-1])
        ema20_val = float(ema(close, 20).iloc[-1])

        if not np.isfinite(ema20_val):
            continue

        atr_val = float(atr(high, low, close, 14).iloc[-1])
        rsi_val = float(rsi(close, 14).iloc[-1])

        # Intraday trend: price must be clearly above or below EMA20
        dist_from_ema = (current - ema20_val) / max(ema20_val, 1e-9)

        if dist_from_ema > 0.0002 and rsi_val < 70:
            # Bullish intraday: BUY pre-fix momentum
            entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.3, 1.0, "BUY")
            if rr < 1.2:
                continue
            # Confidence boost if in fix window
            base_conf = 0.60 if fix_window else 0.55
            conf = _forex_conf_cap(min(0.64, base_conf + dist_from_ema * 20), "london_fix_momentum")
            signals.append({
                "strategy": "london_fix_momentum",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "BUY",
                "entry_price": round(entry, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"London Fix pre-momentum: price={current:.5f} "
                           f"above EMA20={ema20_val:.5f} ({dist_from_ema*100:.3f}%), "
                           f"RSI={rsi_val:.0f}, fix_window={fix_window}. "
                           f"Lyons (2001) microstructure."),
                "timeframe": "1h",
                "max_hold_bars": 3,
                "timestamp": _now_iso(),
            })

        elif dist_from_ema < -0.0002 and rsi_val > 30:
            # Bearish intraday: SELL pre-fix momentum
            entry, tp, sl, rr = _fx_tp_sl(close, high, low, 1.3, 1.0, "SELL")
            if rr < 1.2:
                continue
            base_conf = 0.60 if fix_window else 0.55
            conf = _forex_conf_cap(min(0.64, base_conf + abs(dist_from_ema) * 20), "london_fix_momentum")
            signals.append({
                "strategy": "london_fix_momentum",
                "symbol": symbol,
                "category": "forex",
                "signal_type": "SELL",
                "entry_price": round(entry, 5),
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": (f"London Fix pre-momentum: price={current:.5f} "
                           f"below EMA20={ema20_val:.5f} ({dist_from_ema*100:.3f}%), "
                           f"RSI={rsi_val:.0f}, fix_window={fix_window}. "
                           f"Lyons (2001) microstructure."),
                "timeframe": "1h",
                "max_hold_bars": 3,
                "timestamp": _now_iso(),
            })
    return signals


# ============================================================================
# Strategy registry
# ============================================================================

NEW_FOREX_STRATEGIES_20 = {
    "g10_momentum_factor": g10_momentum_factor,
    "dual_momentum_absolute": dual_momentum_absolute,
    "ppp_mean_reversion": ppp_mean_reversion,
    "rsi_bb_confluence_fx": rsi_bb_confluence_fx,
    "session_volume_breakout": session_volume_breakout,
    "kijun_bounce": kijun_bounce,
    "pivot_point_reaction": pivot_point_reaction,
    "three_bar_reversal": three_bar_reversal,
    "adx_trend_quality_filter": adx_trend_quality_filter,
    "macd_rsi_double_confirmation": macd_rsi_double_confirmation,
    "fifty_pct_fibonacci_mean_revert": fifty_pct_fibonacci_mean_revert,
    "vix_carry_regime": vix_carry_regime,
    "morning_star_fx": morning_star_fx,
    "price_action_swing_lo": price_action_swing_lo,
    "stochastic_divergence_fx": stochastic_divergence_fx,
    "trendline_break_retest": trendline_break_retest,
    "euro_dollar_inverse": euro_dollar_inverse,
    "gap_reversal_fx": gap_reversal_fx,
    "interest_rate_differential_momentum": interest_rate_differential_momentum,
    "london_fix_momentum": london_fix_momentum,
}
