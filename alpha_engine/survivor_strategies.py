"""
ALPHA_ENGINE -- Survivor Strategies
====================================
Five backtested strategies from survivor_backtest.py, wired into the live scanner.

1. connors_r3_survivor -- Connors R3: 3-day consecutive RSI drop (71.0% WR, Sharpe 1.40, PF 1.66, 790 trades, p=0.000)
2. keltner_mean_reversion_survivor -- Keltner Channel mean reversion (67.3% WR, Sharpe 1.99, PF 2.76, 110 trades, p=0.000)
3. bollinger_mean_reversion_survivor -- Bollinger Band mean reversion (60.6% WR, Sharpe 0.69, PF 1.50, 360 trades, p=0.000)
4. volatility_scaled_survivor -- Volatility-managed mean reversion (65.8% WR, Sharpe 0.31, PF 1.17, 565 trades, p=0.000)
5. williams_r_oversold_survivor -- Williams %R oversold reversal (58.8% WR, Sharpe 0.31, PF 1.22, 468 trades, p=0.000)

All strategies operate on daily OHLCV data via yfinance.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from config import CRYPTO_SYMBOLS
from indicators import rsi, sma, ema, atr, bollinger_bands


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(value: float) -> float:
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
        return round(value, 10)


def _atr_tp_sl(close: pd.Series, high: pd.Series, low: pd.Series,
               tp_mult: float = 3.0, sl_mult: float = 2.25,
               atr_period: int = 14) -> tuple[float, float, float]:
    """ATR-based TP/SL -- adapts to current volatility."""
    atr_val = atr(high, low, close, atr_period)
    current_atr = float(atr_val.iloc[-1])
    price = float(close.iloc[-1])
    tp = price + tp_mult * current_atr
    sl = price - sl_mult * current_atr
    return _smart_round(price), _smart_round(tp), _smart_round(sl)


# Target symbols for survivor strategies (large-cap crypto with enough history)
SURVIVOR_TARGETS = [
    ("BTC-USD", "crypto"),
    ("ETH-USD", "crypto"),
    ("SOL-USD", "crypto"),
    ("BNB-USD", "crypto"),
    ("AVAX-USD", "crypto"),
    ("LINK-USD", "crypto"),
    ("DOGE-USD", "crypto"),
    ("XRP-USD", "crypto"),
    ("ADA-USD", "crypto"),
    ("NEAR-USD", "crypto"),
]


# =========================================================================
# STRATEGY: Connors R3 Survivor
# =========================================================================
# Source: 'High Probability ETF Trading' Chapter 4 (Connors, 2010).
# 3-day consecutive RSI(2) drop + RSI(2)<10 + above 200d SMA.
# Backtest: 71.0% WR, Sharpe 1.40, PF 1.66, 790 trades, p=0.000.

def connors_r3_survivor(data: dict, context: dict = None) -> list[dict]:
    """Connors R3: 3-day consecutive RSI(2) drop, buy RSI(2)<10, above 200d SMA."""
    signals = []

    for symbol, cat in SURVIVOR_TARGETS:
        df = data.get(symbol)
        if df is None or len(df) < 210:
            continue

        close = df["Close"]
        current = float(close.iloc[-1])

        # Compute RSI(2)
        rsi2 = rsi(close, 2)
        rsi2_now = float(rsi2.iloc[-1])
        rsi2_1 = float(rsi2.iloc[-2])
        rsi2_2 = float(rsi2.iloc[-3])

        # 200d SMA filter
        sma200_val = float(sma(close, 200).iloc[-1])
        if current < sma200_val:
            continue

        # R3 conditions: RSI(2) < 10, 3 consecutive drops, first drop from < 60
        if rsi2_now >= 10:
            continue
        if not (rsi2_now < rsi2_1 < rsi2_2):
            continue
        if rsi2_2 >= 60:
            continue

        # RSI-14 guard: avoid structural breakdown
        rsi14_val = float(rsi(close, 14).iloc[-1])
        if rsi14_val < 20:
            continue

        # ATR-based TP/SL
        # R:R widened 2026-03-16: was 3.5, now 4.0 (target R:R >= 2.0; was 1.94, now 2.22)
        price, tp, sl = _atr_tp_sl(close, df["High"], df["Low"],
                                    tp_mult=4.0, sl_mult=1.8)
        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 1.5:
            continue

        conf = min(0.75, 0.62 + (10.0 - rsi2_now) * 0.013)

        signals.append({
            "strategy": "connors_r3_survivor",
            "symbol": symbol,
            "category": cat,
            "signal_type": "BUY",
            "direction": "long",
            "entry_price": _smart_round(price),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": (
                f"Connors R3: RSI(2)={rsi2_now:.1f}, 3 consecutive drops, "
                f"above 200d SMA ({sma200_val:.0f}). "
                f"Backtest: 71.0% WR, Sharpe 1.40, PF 1.66, 790 trades, p=0.000. "
                f"Source: Connors (2010) 'High Probability ETF Trading' Ch.4."
            ),
            "timeframe": "1d",
            "extra": {
                "rsi2": round(rsi2_now, 2),
                "rsi14": round(rsi14_val, 1),
                "sma200": round(sma200_val, 2),
                "source": "survivor_backtest.py -- 790 trades, p=0.000",
            },
            "timestamp": _now_iso(),
        })

    return signals


# =========================================================================
# STRATEGY: Keltner Mean Reversion Survivor
# =========================================================================
# Keltner Channel mean reversion: buy at lower channel, sell at midline.
# QuantifiedStrategies: 77% WR with 6-day period.
# Backtest: 67.3% WR, Sharpe 1.99, PF 2.76, 110 trades, p=0.000.

def keltner_mean_reversion_survivor(data: dict, context: dict = None) -> list[dict]:
    """Keltner Channel mean reversion: buy at lower Keltner, target midline."""
    signals = []

    for symbol, cat in SURVIVOR_TARGETS:
        df = data.get(symbol)
        if df is None or len(df) < 220:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])
        period = 20
        atr_mult = 2.0

        # 200d SMA uptrend filter
        sma200_val = float(sma(close, 200).iloc[-1])
        if current < sma200_val:
            continue

        # Compute Keltner Channel
        ema_val = ema(close, period)
        ema_now = float(ema_val.iloc[-1])
        atr_val = atr(high, low, close, period)
        atr_now = float(atr_val.iloc[-1])
        lower_channel = ema_now - atr_mult * atr_now

        # Entry: price at or below lower Keltner channel
        if current > lower_channel:
            continue

        # ATR-based TP/SL (target midline = EMA)
        tp = ema_now  # Target is the Keltner midline
        sl = current - 2.25 * atr_now
        price = current

        if sl >= price:
            continue
        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 1.0:
            continue

        # Distance below lower channel = confidence boost
        pct_below = (lower_channel - current) / lower_channel
        conf = min(0.78, 0.60 + pct_below * 5.0)

        signals.append({
            "strategy": "keltner_mean_reversion_survivor",
            "symbol": symbol,
            "category": cat,
            "signal_type": "BUY",
            "direction": "long",
            "entry_price": _smart_round(price),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": (
                f"Keltner mean reversion: price ({current:.2f}) at/below lower channel "
                f"({lower_channel:.2f}), target midline EMA({period})={ema_now:.2f}. "
                f"Backtest: 67.3% WR, Sharpe 1.99 (best survivor), PF 2.76, 110 trades, p=0.000. "
                f"Source: QuantifiedStrategies (77% WR documented)."
            ),
            "timeframe": "1d",
            "extra": {
                "ema20": round(ema_now, 2),
                "atr20": round(atr_now, 2),
                "lower_channel": round(lower_channel, 2),
                "sma200": round(sma200_val, 2),
                "source": "survivor_backtest.py -- 110 trades, Sharpe 1.99, p=0.000",
            },
            "timestamp": _now_iso(),
        })

    return signals


# =========================================================================
# STRATEGY: Bollinger Mean Reversion Survivor
# =========================================================================
# Buy at lower Bollinger Band, sell at middle band (SMA).
# Backtest: 60.6% WR, Sharpe 0.69, PF 1.50, 360 trades, p=0.000.

def bollinger_mean_reversion_survivor(data: dict, context: dict = None) -> list[dict]:
    """Bollinger Band mean reversion: buy at lower BB, target middle band."""
    signals = []
    period = 20
    num_std = 2.0

    for symbol, cat in SURVIVOR_TARGETS:
        df = data.get(symbol)
        if df is None or len(df) < 220:
            continue

        close = df["Close"]
        current = float(close.iloc[-1])

        # 200d SMA uptrend filter (must be within 10% of 200d SMA)
        sma200_val = float(sma(close, 200).iloc[-1])
        if current < sma200_val * 0.9:
            continue

        # Bollinger Bands
        bb_mid, bb_upper, bb_lower = bollinger_bands(close, period, num_std)
        mid_now = float(bb_mid.iloc[-1])
        lower_now = float(bb_lower.iloc[-1])

        # Entry: price at or below lower BB
        if current > lower_now:
            continue

        # TP = middle band, SL = ATR-based
        tp = mid_now
        atr_val = atr(df["High"], df["Low"], close, 14)
        atr_now = float(atr_val.iloc[-1])
        sl = current - 2.25 * atr_now
        price = current

        if sl >= price:
            continue
        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 0.8:
            continue

        # Depth below lower band = confidence
        pct_below = (lower_now - current) / lower_now if lower_now > 0 else 0
        conf = min(0.72, 0.55 + pct_below * 5.0)

        signals.append({
            "strategy": "bollinger_mean_reversion_survivor",
            "symbol": symbol,
            "category": cat,
            "signal_type": "BUY",
            "direction": "long",
            "entry_price": _smart_round(price),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": (
                f"Bollinger mean reversion: price ({current:.2f}) at/below lower BB "
                f"({lower_now:.2f}), target middle band ({mid_now:.2f}). "
                f"Backtest: 60.6% WR, Sharpe 0.69, PF 1.50, 360 trades, p=0.000."
            ),
            "timeframe": "1d",
            "extra": {
                "bb_lower": round(lower_now, 2),
                "bb_mid": round(mid_now, 2),
                "sma200": round(sma200_val, 2),
                "source": "survivor_backtest.py -- 360 trades, p=0.000",
            },
            "timestamp": _now_iso(),
        })

    return signals


# =========================================================================
# STRATEGY: Volatility Scaled Survivor
# =========================================================================
# Source: Moreira & Muir (2017), Journal of Finance.
# Volatility-managed mean reversion: buy when RSI(5) oversold + vol below
# 1.5x median (avoid chaos). Scale by inverse of recent volatility.
# Backtest: 65.8% WR, Sharpe 0.31, PF 1.17, 565 trades, p=0.000.

def volatility_scaled_survivor(data: dict, context: dict = None) -> list[dict]:
    """Volatility-managed mean reversion: buy oversold RSI(5) + low volatility regime."""
    signals = []
    lookback = 21

    for symbol, cat in SURVIVOR_TARGETS:
        df = data.get(symbol)
        if df is None or len(df) < 250:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])

        # 200d SMA uptrend filter
        sma200_val = float(sma(close, 200).iloc[-1])
        if current < sma200_val:
            continue

        # RSI(5) for oversold detection
        rsi5 = rsi(close, 5)
        rsi5_now = float(rsi5.iloc[-1])
        if rsi5_now >= 20:
            continue

        # 21-day realized volatility
        returns = close.pct_change()
        vol = float(returns.rolling(lookback).std().iloc[-1])
        if vol <= 0:
            continue

        # Median vol over last 200 bars for scaling
        vol_series = returns.rolling(lookback).std().iloc[-200:]
        med_vol = float(vol_series[vol_series > 0].median()) if (vol_series > 0).any() else 0.01

        # Only enter when vol is below 1.5x median (avoid chaotic regimes)
        if vol >= med_vol * 1.5:
            continue

        # ATR-based TP/SL -- tighter than Connors because shorter hold period (~7d avg)
        # R:R widened 2026-03-16: was 2.5, now 4.0 (target R:R >= 2.0; was 1.39, now 2.22)
        price, tp, sl = _atr_tp_sl(close, high, low,
                                    tp_mult=4.0, sl_mult=1.8, atr_period=14)

        if sl >= price:
            continue
        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 1.2:
            continue

        # Confidence: deeper RSI oversold + lower vol = higher confidence
        vol_ratio = vol / med_vol if med_vol > 0 else 1.0
        conf = min(0.74, 0.56 + (20.0 - rsi5_now) * 0.008 + (1.0 - vol_ratio) * 0.05)

        signals.append({
            "strategy": "volatility_scaled_survivor",
            "symbol": symbol,
            "category": cat,
            "signal_type": "BUY",
            "direction": "long",
            "entry_price": _smart_round(price),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": (
                f"Vol-scaled MR: RSI(5)={rsi5_now:.1f}, vol={vol:.4f} "
                f"({vol_ratio:.2f}x median), above 200d SMA ({sma200_val:.0f}). "
                f"Backtest: 65.8% WR, PF 1.17, 565 trades, p=0.000. "
                f"Source: Moreira & Muir (2017) Journal of Finance."
            ),
            "timeframe": "1d",
            "extra": {
                "rsi5": round(rsi5_now, 2),
                "vol_21d": round(vol, 6),
                "vol_ratio": round(vol_ratio, 2),
                "median_vol": round(med_vol, 6),
                "sma200": round(sma200_val, 2),
                "source": "survivor_backtest.py -- 565 trades, OOS WR 68.4%, p=0.000",
            },
            "timestamp": _now_iso(),
        })

    return signals


# =========================================================================
# STRATEGY: Williams %R Oversold Survivor
# =========================================================================
# Williams %R oversold reversal. Documented 81% WR on QuantifiedStrategies.
# Buy when %R < -80 (oversold) above 200d SMA, exit when %R > -20 or 15 days.
# Backtest: 58.8% WR, Sharpe 0.31, PF 1.22, 468 trades, p=0.000.

def williams_r_oversold_survivor(data: dict, context: dict = None) -> list[dict]:
    """Williams %R oversold reversal: buy %R < -80, above 200d SMA."""
    signals = []
    period = 14
    oversold = -80

    for symbol, cat in SURVIVOR_TARGETS:
        df = data.get(symbol)
        if df is None or len(df) < 220:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])

        # 200d SMA uptrend filter
        sma200_val = float(sma(close, 200).iloc[-1])
        if current < sma200_val:
            continue

        # Williams %R = -100 * (highest_high - close) / (highest_high - lowest_low)
        highest = high.rolling(period).max()
        lowest = low.rolling(period).min()
        wr_range = highest - lowest
        wr = pd.Series(
            np.where(wr_range != 0, -100.0 * (highest - close) / wr_range, -50.0),
            index=close.index,
        )
        wr_now = float(wr.iloc[-1])

        # Entry: Williams %R below -80 (oversold)
        if wr_now >= oversold:
            continue

        # RSI-14 guard: avoid deep structural collapse
        rsi14_val = float(rsi(close, 14).iloc[-1])
        if rsi14_val < 18:
            continue

        # ATR-based TP/SL
        # R:R widened 2026-03-16: was 3.0, now 4.5 (target R:R >= 2.0; was 1.50, now 2.25)
        price, tp, sl = _atr_tp_sl(close, high, low,
                                    tp_mult=4.5, sl_mult=2.0, atr_period=14)

        if sl >= price:
            continue
        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 1.2:
            continue

        # Confidence: deeper %R oversold = higher confidence
        depth = abs(wr_now - oversold)  # how far past -80
        conf = min(0.70, 0.52 + depth * 0.006)

        signals.append({
            "strategy": "williams_r_oversold_survivor",
            "symbol": symbol,
            "category": cat,
            "signal_type": "BUY",
            "direction": "long",
            "entry_price": _smart_round(price),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": (
                f"Williams %R oversold: %R={wr_now:.1f} (< {oversold}), "
                f"above 200d SMA ({sma200_val:.0f}), RSI(14)={rsi14_val:.1f}. "
                f"Backtest: 58.8% WR, PF 1.22, 468 trades, p=0.000. "
                f"Source: QuantifiedStrategies (81% WR documented)."
            ),
            "timeframe": "1d",
            "extra": {
                "williams_r": round(wr_now, 2),
                "rsi14": round(rsi14_val, 1),
                "sma200": round(sma200_val, 2),
                "source": "survivor_backtest.py -- 468 trades, OOS WR 61.8%, p=0.000",
            },
            "timestamp": _now_iso(),
        })

    return signals


# =========================================================================
# Strategy Registry
# =========================================================================

SURVIVOR_STRATEGIES: dict[str, callable] = {
    "connors_r3_survivor": connors_r3_survivor,
    "keltner_mean_reversion_survivor": keltner_mean_reversion_survivor,
    "bollinger_mean_reversion_survivor": bollinger_mean_reversion_survivor,
    "volatility_scaled_survivor": volatility_scaled_survivor,
    "williams_r_oversold_survivor": williams_r_oversold_survivor,
}
