"""
ALPHA_ENGINE -- Community-Sourced Strategies
=============================================
10+ strategies from Reddit r/algotrading, r/daytrading, YouTube, Twitter,
QuantConnect, TradingView, and academic papers. Each returns list[dict] of
signals with BUY/SELL, TP, SL, confidence, reason, etc.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

from config import (
    CRYPTO_SYMBOLS, FOREX_SYMBOLS, EQUITY_SYMBOLS,
    CATEGORY_RISK,
)
from indicators import (
    sma, ema, rsi, atr, adx, bollinger_bands, bollinger_squeeze,
    volume_ratio, zscore, fair_value_gap, vwap_session,
)


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
    return round(value, 10)


def _atr_tp_sl(close: pd.Series, high: pd.Series, low: pd.Series,
               tp_mult: float = 2.0, sl_mult: float = 1.0,
               atr_period: int = 14) -> tuple[float, float, float]:
    atr_val = atr(high, low, close, atr_period)
    current_atr = float(atr_val.iloc[-1])
    price = float(close.iloc[-1])
    tp = price + tp_mult * current_atr
    sl = price - sl_mult * current_atr
    return _smart_round(price), _smart_round(tp), _smart_round(sl)


def _get_category(symbol: str, asset_class: str) -> str:
    if asset_class == "crypto":
        return CRYPTO_SYMBOLS.get(symbol, {}).get("cat", "crypto")
    if asset_class == "forex":
        return "forex"
    return EQUITY_SYMBOLS.get(symbol, {}).get("cat", "stock")


# =========================================================================
# CRYPTO 1: EMA 9/21 Crossover + RSI Filter (Reddit r/daytrading, TradingView)
# =========================================================================

def community_ema_9_21_rsi_crypto(data: dict[str, pd.DataFrame],
                                  context: Optional[dict] = None) -> list[dict]:
    """BUY: EMA(9) cross above EMA(21), RSI 40-65, price above SMA(200). TP 1.5x ATR, SL 1x ATR."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 220:
            continue
        close = df["Close"]
        high, low = df["High"], df["Low"]
        ema9 = ema(close, 9)
        ema21 = ema(close, 21)
        sma200 = sma(close, 200)
        rsi_vals = rsi(close, 14)
        price = float(close.iloc[-1])
        e9_cur, e9_prev = float(ema9.iloc[-1]), float(ema9.iloc[-2])
        e21_cur, e21_prev = float(ema21.iloc[-1]), float(ema21.iloc[-2])
        sma200_val = float(sma200.iloc[-1])
        rsi_val = float(rsi_vals.iloc[-1])
        atr_val = float(atr(high, low, close, 14).iloc[-1])
        vol_r = float(volume_ratio(df["Volume"]).iloc[-1]) if "Volume" in df.columns else 1.0

        # BUY: EMA9 crosses above EMA21, RSI 40-65, price above SMA200
        if e9_prev <= e21_prev and e9_cur > e21_cur and 40 <= rsi_val <= 65 and price > sma200_val:
            tp = price + 1.5 * atr_val
            sl = price - 1.0 * atr_val
            rr = (tp - price) / (price - sl) if price > sl else 0
            if rr < 1.0:
                continue
            signals.append({
                "strategy": "community_ema_9_21_rsi_crypto",
                "symbol": symbol, "category": _get_category(symbol, "crypto"),
                "signal_type": "BUY",
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(tp), "stop_loss": _smart_round(sl),
                "confidence": round(min(0.80, 0.50 + (rsi_val - 40) / 50), 2),
                "risk_reward": round(rr, 2),
                "reason": f"EMA9/21 bullish cross, RSI={rsi_val:.0f}, above SMA200",
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1), "volume_ratio": round(vol_r, 2),
                "atr_at_entry": round(atr_val, 6), "timestamp": _now_iso(),
            })
        # SELL: EMA9 crosses below EMA21, RSI 35-60, price below SMA200
        elif e9_prev >= e21_prev and e9_cur < e21_cur and 35 <= rsi_val <= 60 and price < sma200_val:
            tp = price - 1.5 * atr_val
            sl = price + 1.0 * atr_val
            rr = (price - tp) / (sl - price) if sl > price else 0
            if rr < 1.0:
                continue
            signals.append({
                "strategy": "community_ema_9_21_rsi_crypto",
                "symbol": symbol, "category": _get_category(symbol, "crypto"),
                "signal_type": "SELL",
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(tp), "stop_loss": _smart_round(sl),
                "confidence": round(min(0.80, 0.50 + (60 - rsi_val) / 50), 2),
                "risk_reward": round(rr, 2),
                "reason": f"EMA9/21 bearish cross, RSI={rsi_val:.0f}, below SMA200",
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1), "volume_ratio": round(vol_r, 2),
                "atr_at_entry": round(atr_val, 6), "timestamp": _now_iso(),
            })
    return signals


# =========================================================================
# CRYPTO 2: Bollinger Band Squeeze Breakout (PyQuantLab, Medium)
# =========================================================================

def community_bb_squeeze_breakout_crypto(data: dict[str, pd.DataFrame],
                                         context: Optional[dict] = None) -> list[dict]:
    """Squeeze: bandwidth < 20d avg bandwidth * 0.75. BUY break above upper BB + vol > 1.5x. TP 2x ATR, SL middle band."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 25:
            continue
        close = df["Close"]
        high, low = df["High"], df["Low"]
        vol = df["Volume"] if "Volume" in df.columns else pd.Series(1.0, index=close.index)
        bb = bollinger_bands(close, 20, 2.0)
        bandwidth = bb["bandwidth"]
        avg_bw_20 = bandwidth.rolling(20).mean()
        price = float(close.iloc[-1])
        upper = float(bb["upper"].iloc[-1])
        lower = float(bb["lower"].iloc[-1])
        middle = float(bb["middle"].iloc[-1])
        atr_val = float(atr(high, low, close, 14).iloc[-1])
        vol_r = float(volume_ratio(vol).iloc[-1]) if vol is not None and len(vol) else 1.0

        # Squeeze = bandwidth < 20d avg * 0.75 (on a recent bar); then breakout this bar
        squeeze_recent = (bandwidth.iloc[-5:-1] < avg_bw_20.iloc[-5:-1] * 0.75).any()
        if not squeeze_recent:
            continue
        # BUY: price breaks above upper BB with volume
        if price > upper and vol_r >= 1.5:
            sl = middle
            tp = price + 2.0 * atr_val
            rr = (tp - price) / (price - sl) if price > sl else 0
            if rr < 1.0:
                continue
            signals.append({
                "strategy": "community_bb_squeeze_breakout_crypto",
                "symbol": symbol, "category": _get_category(symbol, "crypto"),
                "signal_type": "BUY",
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(tp), "stop_loss": _smart_round(sl),
                "confidence": round(min(0.78, 0.45 + vol_r * 0.08), 2),
                "risk_reward": round(rr, 2),
                "reason": f"BB squeeze breakout above upper BB, vol={vol_r:.1f}x",
                "timeframe": "1d",
                "rsi_at_entry": round(float(rsi(close, 14).iloc[-1]), 1),
                "volume_ratio": round(vol_r, 2), "atr_at_entry": round(atr_val, 6),
                "timestamp": _now_iso(),
            })
        # SELL: price breaks below lower BB after squeeze
        elif price < lower:
            sl = middle
            tp = price - 2.0 * atr_val
            rr = (price - tp) / (sl - price) if sl > price else 0
            if rr < 1.0:
                continue
            signals.append({
                "strategy": "community_bb_squeeze_breakout_crypto",
                "symbol": symbol, "category": _get_category(symbol, "crypto"),
                "signal_type": "SELL",
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(tp), "stop_loss": _smart_round(sl),
                "confidence": round(0.65, 2),
                "risk_reward": round(rr, 2),
                "reason": "BB squeeze breakout below lower BB",
                "timeframe": "1d",
                "rsi_at_entry": round(float(rsi(close, 14).iloc[-1]), 1),
                "volume_ratio": round(vol_r, 2), "atr_at_entry": round(atr_val, 6),
                "timestamp": _now_iso(),
            })
    return signals


# =========================================================================
# CRYPTO 3: RSI Extreme Reversal (CryptoQuant backtests)
# =========================================================================

def community_rsi_extreme_reversal_crypto(data: dict[str, pd.DataFrame],
                                          context: Optional[dict] = None) -> list[dict]:
    """BUY: RSI drops below 25 then crosses back above 30. SELL: RSI above 75 then back below 70. TP 2x ATR, SL 1.5x ATR."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 20:
            continue
        close = df["Close"]
        high, low = df["High"], df["Low"]
        rsi_vals = rsi(close, 14)
        r_cur, r_prev = float(rsi_vals.iloc[-1]), float(rsi_vals.iloc[-2])
        price = float(close.iloc[-1])
        atr_val = float(atr(high, low, close, 14).iloc[-1])
        vol_r = float(volume_ratio(df["Volume"]).iloc[-1]) if "Volume" in df.columns else 1.0

        # BUY: RSI was < 25 and now crossed above 30
        if r_prev < 25 and r_cur >= 30:
            tp = price + 2.0 * atr_val
            sl = price - 1.5 * atr_val
            rr = (tp - price) / (price - sl) if price > sl else 0
            if rr < 1.0:
                continue
            signals.append({
                "strategy": "community_rsi_extreme_reversal_crypto",
                "symbol": symbol, "category": _get_category(symbol, "crypto"),
                "signal_type": "BUY",
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(tp), "stop_loss": _smart_round(sl),
                "confidence": round(min(0.75, 0.50 + (30 - r_prev) / 30), 2),
                "risk_reward": round(rr, 2),
                "reason": f"RSI extreme oversold reversal (was {r_prev:.0f}, now {r_cur:.0f})",
                "timeframe": "1d",
                "rsi_at_entry": round(r_cur, 1), "volume_ratio": round(vol_r, 2),
                "atr_at_entry": round(atr_val, 6), "timestamp": _now_iso(),
            })
        # SELL: RSI was > 75 and now crossed below 70
        elif r_prev > 75 and r_cur <= 70:
            tp = price - 2.0 * atr_val
            sl = price + 1.5 * atr_val
            rr = (price - tp) / (sl - price) if sl > price else 0
            if rr < 1.0:
                continue
            signals.append({
                "strategy": "community_rsi_extreme_reversal_crypto",
                "symbol": symbol, "category": _get_category(symbol, "crypto"),
                "signal_type": "SELL",
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(tp), "stop_loss": _smart_round(sl),
                "confidence": round(min(0.75, 0.50 + (r_prev - 70) / 30), 2),
                "risk_reward": round(rr, 2),
                "reason": f"RSI extreme overbought reversal (was {r_prev:.0f}, now {r_cur:.0f})",
                "timeframe": "1d",
                "rsi_at_entry": round(r_cur, 1), "volume_ratio": round(vol_r, 2),
                "atr_at_entry": round(atr_val, 6), "timestamp": _now_iso(),
            })
    return signals


# =========================================================================
# CRYPTO 4: VWAP Bounce (crypto guides, Discord)
# =========================================================================

def community_vwap_bounce_crypto(data: dict[str, pd.DataFrame],
                                context: Optional[dict] = None) -> list[dict]:
    """BUY: price within 0.5% of VWAP in uptrend (close > SMA50), then bounce (close > open). SL 1x ATR below VWAP, TP 2x ATR."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 55:
            continue
        close = df["Close"]
        high, low = df["High"], df["Low"]
        vol = df["Volume"] if "Volume" in df.columns else pd.Series(1.0, index=close.index)
        vwap_vals = vwap_session(high, low, close, vol)
        sma50 = sma(close, 50)
        price = float(close.iloc[-1])
        vwap_val = float(vwap_vals.iloc[-1])
        if pd.isna(vwap_val) or vwap_val <= 0:
            continue
        dist_pct = abs(price - vwap_val) / vwap_val
        uptrend = price > float(sma50.iloc[-1])
        bullish_candle = close.iloc[-1] > df["Open"].iloc[-1] if "Open" in df.columns else True
        atr_val = float(atr(high, low, close, 14).iloc[-1])
        vol_r = float(volume_ratio(vol).iloc[-1]) if vol is not None else 1.0

        if dist_pct <= 0.005 and uptrend and bullish_candle:
            sl = min(price - 1.0 * atr_val, vwap_val - 1.0 * atr_val)
            tp = price + 2.0 * atr_val
            rr = (tp - price) / (price - sl) if price > sl else 0
            if rr < 1.0:
                continue
            signals.append({
                "strategy": "community_vwap_bounce_crypto",
                "symbol": symbol, "category": _get_category(symbol, "crypto"),
                "signal_type": "BUY",
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(tp), "stop_loss": _smart_round(sl),
                "confidence": round(min(0.72, 0.48 + (0.005 - dist_pct) * 30), 2),
                "risk_reward": round(rr, 2),
                "reason": f"VWAP bounce (within {dist_pct*100:.2f}% of VWAP), uptrend",
                "timeframe": "1d",
                "rsi_at_entry": round(float(rsi(close, 14).iloc[-1]), 1),
                "volume_ratio": round(vol_r, 2), "atr_at_entry": round(atr_val, 6),
                "timestamp": _now_iso(),
            })
    return signals


# =========================================================================
# CRYPTO 5: Momentum Breakout Volume (QuantConnect)
# =========================================================================

def community_momentum_breakout_volume_crypto(data: dict[str, pd.DataFrame],
                                               context: Optional[dict] = None) -> list[dict]:
    """BUY: price breaks 20d high AND volume > 2x 20d avg AND ADX > 25. TP 2x ATR, SL 1x ATR."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 25:
            continue
        close = df["Close"]
        high, low = df["High"], df["Low"]
        vol = df["Volume"] if "Volume" in df.columns else pd.Series(1.0, index=close.index)
        high_20d = float(high.iloc[-21:-1].max())
        price = float(close.iloc[-1])
        vol_r = float(volume_ratio(vol).iloc[-1]) if vol is not None else 0.0
        adx_val = float(adx(high, low, close, 14).iloc[-1])

        if price <= high_20d or vol_r < 2.0 or adx_val < 25:
            continue
        atr_val = float(atr(high, low, close, 14).iloc[-1])
        tp = price + 2.0 * atr_val
        sl = price - 1.0 * atr_val
        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 1.0:
            continue
        rsi_val = float(rsi(close, 14).iloc[-1])
        signals.append({
            "strategy": "community_momentum_breakout_volume_crypto",
            "symbol": symbol, "category": _get_category(symbol, "crypto"),
            "signal_type": "BUY",
            "entry_price": _smart_round(price),
            "take_profit": _smart_round(tp), "stop_loss": _smart_round(sl),
            "confidence": round(min(0.78, 0.45 + vol_r * 0.05 + adx_val * 0.005), 2),
            "risk_reward": round(rr, 2),
            "reason": f"20d breakout, vol={vol_r:.1f}x, ADX={adx_val:.0f}",
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1), "volume_ratio": round(vol_r, 2),
            "atr_at_entry": round(atr_val, 6), "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# FOREX 6: EMA 8/21 Scalp (kenyaforexfirm.com -- 65% WR, PF 1.85)
# =========================================================================

def community_ema_8_21_scalp_forex(data: dict[str, pd.DataFrame],
                                   context: Optional[dict] = None) -> list[dict]:
    """BUY: EMA(8) cross above EMA(21), RSI 40-70. SELL: EMA(8) cross below EMA(21), RSI 30-60. TP 1.5x ATR, SL 1x ATR."""
    signals = []
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 25:
            continue
        close = df["Close"]
        high, low = df["High"], df["Low"]
        ema8 = ema(close, 8)
        ema21 = ema(close, 21)
        rsi_vals = rsi(close, 14)
        e8_cur, e8_prev = float(ema8.iloc[-1]), float(ema8.iloc[-2])
        e21_cur, e21_prev = float(ema21.iloc[-1]), float(ema21.iloc[-2])
        rsi_val = float(rsi_vals.iloc[-1])
        price = float(close.iloc[-1])
        atr_val = float(atr(high, low, close, 14).iloc[-1])
        vol_r = float(volume_ratio(df["Volume"]).iloc[-1]) if "Volume" in df.columns else 1.0

        if e8_prev <= e21_prev and e8_cur > e21_cur and 40 <= rsi_val <= 70:
            # Forex-appropriate: 1.2x ATR TP, 1.0x ATR SL with % caps
            tp_dist = min(1.2 * atr_val, price * 0.003)  # cap 0.3%
            sl_dist = min(1.0 * atr_val, price * 0.002)  # cap 0.2%
            tp = price + tp_dist
            sl = price - sl_dist
            rr = (tp - price) / (price - sl) if price > sl else 0
            if rr < 1.0:
                continue
            conf = round(min(0.72, 0.50 + (rsi_val - 40) / 60), 2)
            signals.append({
                "strategy": "community_ema_8_21_scalp_forex",
                "symbol": symbol, "category": "forex",
                "signal_type": "BUY",
                "entry_price": round(price, 5),
                "take_profit": round(tp, 5), "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": f"EMA8/21 bullish cross, RSI={rsi_val:.0f}",
                "timeframe": "1d",
                "max_hold_bars": 20,
                "rsi_at_entry": round(rsi_val, 1), "volume_ratio": round(vol_r, 2),
                "atr_at_entry": round(atr_val, 6), "timestamp": _now_iso(),
            })
        elif e8_prev >= e21_prev and e8_cur < e21_cur and 30 <= rsi_val <= 60:
            tp_dist = min(1.2 * atr_val, price * 0.008)
            sl_dist = min(1.0 * atr_val, price * 0.005)
            tp = price - tp_dist
            sl = price + sl_dist
            rr = (price - tp) / (sl - price) if sl > price else 0
            if rr < 1.0:
                continue
            conf = round(min(0.72, 0.50 + (60 - rsi_val) / 60), 2)
            signals.append({
                "strategy": "community_ema_8_21_scalp_forex",
                "symbol": symbol, "category": "forex",
                "signal_type": "SELL",
                "entry_price": round(price, 5),
                "take_profit": round(tp, 5), "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": f"EMA8/21 bearish cross, RSI={rsi_val:.0f}",
                "timeframe": "1d",
                "max_hold_bars": 20,
                "rsi_at_entry": round(rsi_val, 1), "volume_ratio": round(vol_r, 2),
                "atr_at_entry": round(atr_val, 6), "timestamp": _now_iso(),
            })
    return signals


# =========================================================================
# FOREX 7: London Session Breakout v2 (5-day range proxy)
# =========================================================================

def community_london_breakout_v2_forex(data: dict[str, pd.DataFrame],
                                       context: Optional[dict] = None) -> list[dict]:
    """DISABLED: needs intraday (1H/4H) data to work properly. On daily data,
    this is just a generic 5-day breakout that doesn't capture the London
    session dynamics it was designed for. 0% WR in production.
    """
    return []  # Disabled -- needs intraday data, can't work on daily bars

    signals = []
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 10:
            continue
        close = df["Close"]
        high, low = df["High"], df["Low"]
        high_5d = float(high.iloc[-6:-1].max())
        low_5d = float(low.iloc[-6:-1].min())
        price = float(close.iloc[-1])
        atr_val = float(atr(high, low, close, 14).iloc[-1])
        vol_r = float(volume_ratio(df["Volume"]).iloc[-1]) if "Volume" in df.columns else 1.0

        if price > high_5d and vol_r >= 1.0:
            tp = price + 2.0 * atr_val
            sl = price - 1.0 * atr_val
            rr = (tp - price) / (price - sl) if price > sl else 0
            if rr < 1.0:
                continue
            signals.append({
                "strategy": "community_london_breakout_v2_forex",
                "symbol": symbol, "category": "forex",
                "signal_type": "BUY",
                "entry_price": round(price, 5),
                "take_profit": round(tp, 5), "stop_loss": round(sl, 5),
                "confidence": round(min(0.70, 0.45 + vol_r * 0.05), 2),
                "risk_reward": round(rr, 2),
                "reason": f"5d range breakout above {high_5d:.5f}, vol={vol_r:.1f}x",
                "timeframe": "1d",
                "rsi_at_entry": round(float(rsi(close, 14).iloc[-1]), 1),
                "volume_ratio": round(vol_r, 2), "atr_at_entry": round(atr_val, 6),
                "timestamp": _now_iso(),
            })
        elif price < low_5d:
            tp = price - 2.0 * atr_val
            sl = price + 1.0 * atr_val
            rr = (price - tp) / (sl - price) if sl > price else 0
            if rr < 1.0:
                continue
            signals.append({
                "strategy": "community_london_breakout_v2_forex",
                "symbol": symbol, "category": "forex",
                "signal_type": "SELL",
                "entry_price": round(price, 5),
                "take_profit": round(tp, 5), "stop_loss": round(sl, 5),
                "confidence": round(0.65, 2),
                "risk_reward": round(rr, 2),
                "reason": f"5d range breakout below {low_5d:.5f}",
                "timeframe": "1d",
                "rsi_at_entry": round(float(rsi(close, 14).iloc[-1]), 1),
                "volume_ratio": round(vol_r, 2), "atr_at_entry": round(atr_val, 6),
                "timestamp": _now_iso(),
            })
    return signals


# =========================================================================
# FOREX 8: Mean Reversion Z-Score (academic)
# =========================================================================

def community_forex_zscore_mean_reversion(data: dict[str, pd.DataFrame],
                                           context: Optional[dict] = None) -> list[dict]:
    """BUY: z-score < -2, RSI < 35. SELL: z-score > 2, RSI > 65. TP: mean (z=0), SL 1.5x ATR."""
    signals = []
    for symbol in FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 25:
            continue
        close = df["Close"]
        high, low = df["High"], df["Low"]
        z_vals = zscore(close, 20)
        z_cur = float(z_vals.iloc[-1])
        if pd.isna(z_cur):
            continue
        rsi_val = float(rsi(close, 14).iloc[-1])
        price = float(close.iloc[-1])
        mean_price = float(close.iloc[-21:].mean())
        atr_val = float(atr(high, low, close, 14).iloc[-1])
        vol_r = float(volume_ratio(df["Volume"]).iloc[-1]) if "Volume" in df.columns else 1.0

        if z_cur < -2.0 and rsi_val < 35:
            tp = mean_price
            sl_dist = min(1.0 * atr_val, price * 0.005)
            sl = price - sl_dist
            # Cap TP distance too
            tp_dist = min(abs(tp - price), price * 0.008)
            tp = price + tp_dist
            rr = (tp - price) / (price - sl) if price > sl else 0
            if rr < 1.0:
                continue
            conf = round(min(0.72, 0.50 + abs(z_cur) * 0.10), 2)
            signals.append({
                "strategy": "community_forex_zscore_mean_reversion",
                "symbol": symbol, "category": "forex",
                "signal_type": "BUY",
                "entry_price": round(price, 5),
                "take_profit": round(tp, 5), "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": f"Z-score={z_cur:.2f} (oversold), RSI={rsi_val:.0f}, target mean",
                "timeframe": "1d",
                "max_hold_bars": 20,
                "rsi_at_entry": round(rsi_val, 1), "volume_ratio": round(vol_r, 2),
                "atr_at_entry": round(atr_val, 6), "timestamp": _now_iso(),
            })
        elif z_cur > 2.0 and rsi_val > 65:
            tp = mean_price
            sl_dist = min(1.0 * atr_val, price * 0.005)
            sl = price + sl_dist
            tp_dist = min(abs(price - tp), price * 0.008)
            tp = price - tp_dist
            rr = (price - tp) / (sl - price) if sl > price else 0
            if rr < 1.0:
                continue
            conf = round(min(0.72, 0.50 + abs(z_cur) * 0.10), 2)
            signals.append({
                "strategy": "community_forex_zscore_mean_reversion",
                "symbol": symbol, "category": "forex",
                "signal_type": "SELL",
                "entry_price": round(price, 5),
                "take_profit": round(tp, 5), "stop_loss": round(sl, 5),
                "confidence": conf,
                "risk_reward": round(rr, 2),
                "reason": f"Z-score={z_cur:.2f} (overbought), RSI={rsi_val:.0f}, target mean",
                "timeframe": "1d",
                "max_hold_bars": 20,
                "rsi_at_entry": round(rsi_val, 1), "volume_ratio": round(vol_r, 2),
                "atr_at_entry": round(atr_val, 6), "timestamp": _now_iso(),
            })
    return signals


# =========================================================================
# EQUITY 9: Opening Range Breakout ORB (Reddit r/stocks, QuantConnect 71.4% WR)
# =========================================================================

def community_orb_equity(data: dict[str, pd.DataFrame],
                         context: Optional[dict] = None) -> list[dict]:
    """BUY: price breaks above 5-day high, RSI < 70, volume > 1.5x avg. TP 2x ATR, SL 1x ATR."""
    signals = []
    for symbol in EQUITY_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 25:
            continue
        close = df["Close"]
        high, low = df["High"], df["Low"]
        vol = df["Volume"] if "Volume" in df.columns else pd.Series(1.0, index=close.index)
        high_5d = float(high.iloc[-6:-1].max())
        price = float(close.iloc[-1])
        vol_r = float(volume_ratio(vol).iloc[-1]) if vol is not None else 0.0
        rsi_val = float(rsi(close, 14).iloc[-1])

        if price <= high_5d or rsi_val >= 70 or vol_r < 1.5:
            continue
        atr_val = float(atr(high, low, close, 14).iloc[-1])
        tp = price + 2.0 * atr_val
        sl = price - 1.0 * atr_val
        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 1.0:
            continue
        cat = _get_category(symbol, "equity")
        signals.append({
            "strategy": "community_orb_equity",
            "symbol": symbol, "category": cat,
            "signal_type": "BUY",
            "entry_price": round(price, 2),
            "take_profit": round(tp, 2), "stop_loss": round(sl, 2),
            "confidence": round(min(0.75, 0.45 + vol_r * 0.06), 2),
            "risk_reward": round(rr, 2),
            "reason": f"ORB 5d high breakout, RSI={rsi_val:.0f}, vol={vol_r:.1f}x",
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1), "volume_ratio": round(vol_r, 2),
            "atr_at_entry": round(atr_val, 4), "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# EQUITY 10: Penny Stock Volume Surge (day trading communities)
# =========================================================================

def community_penny_volume_surge(data: dict[str, pd.DataFrame],
                                context: Optional[dict] = None) -> list[dict]:
    """BUY: volume > 3x 20d avg, price > SMA(10), RSI 40-65, ADX > 20. TP 2.5x ATR, SL 1.5x ATR. Penny/meme only."""
    penny_meme = [s for s, info in EQUITY_SYMBOLS.items() if info.get("cat") in ("penny", "meme")]
    signals = []
    for symbol in penny_meme:
        df = data.get(symbol)
        if df is None or len(df) < 25:
            continue
        close = df["Close"]
        high, low = df["High"], df["Low"]
        vol = df["Volume"] if "Volume" in df.columns else pd.Series(1.0, index=close.index)
        sma10 = sma(close, 10)
        vol_r = float(volume_ratio(vol).iloc[-1]) if vol is not None else 0.0
        price = float(close.iloc[-1])
        sma10_val = float(sma10.iloc[-1])
        rsi_val = float(rsi(close, 14).iloc[-1])
        adx_val = float(adx(high, low, close, 14).iloc[-1])

        if vol_r < 3.0 or price <= sma10_val or not (40 <= rsi_val <= 65) or adx_val < 20:
            continue
        atr_val = float(atr(high, low, close, 14).iloc[-1])
        tp = price + 2.5 * atr_val
        sl = price - 1.5 * atr_val
        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 1.0:
            continue
        cat = _get_category(symbol, "equity")
        signals.append({
            "strategy": "community_penny_volume_surge",
            "symbol": symbol, "category": cat,
            "signal_type": "BUY",
            "entry_price": round(price, 2),
            "take_profit": round(tp, 2), "stop_loss": round(sl, 2),
            "confidence": round(min(0.72, 0.42 + vol_r * 0.05 + adx_val * 0.005), 2),
            "risk_reward": round(rr, 2),
            "reason": f"Penny vol surge {vol_r:.1f}x, above SMA10, RSI={rsi_val:.0f}, ADX={adx_val:.0f}",
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1), "volume_ratio": round(vol_r, 2),
            "atr_at_entry": round(atr_val, 4), "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# CRYPTO + FOREX 11: ICT Order Block + FVG Selective (TradingView SMC Pro 61.9% WR)
# =========================================================================

def community_ict_fvg_selective(data: dict[str, pd.DataFrame],
                               context: Optional[dict] = None) -> list[dict]:
    """FVG entry ONLY if: price in discount (below 50% of recent range), ADX > 20, RSI < 45. TP 2x ATR, SL below FVG low."""
    # REGIME GATE: Disable ICT/SMC in extreme fear (F&G < 20).
    # These strategies assume normal market structure; panic destroys structure.
    # TJR Trades analysis: 70% WR requires normal volatility + structure.
    fng = (context or {}).get("fear_greed", 50)
    if fng < 20:
        return []  # Sit out during extreme fear

    symbols = list(CRYPTO_SYMBOLS) + list(FOREX_SYMBOLS)
    signals = []
    for symbol in symbols:
        df = data.get(symbol)
        if df is None or len(df) < 35:
            continue
        close = df["Close"]
        high, low = df["High"], df["Low"]
        current = float(close.iloc[-1])
        range_20 = close.iloc[-21:-1]
        range_high = float(range_20.max())
        range_low = float(range_20.min())
        mid = (range_high + range_low) / 2
        # Discount zone = below 50% of range
        in_discount = current < mid
        adx_val = float(adx(high, low, close).iloc[-1])
        rsi_val = float(rsi(close, 14).iloc[-1])
        if not in_discount or adx_val < 20 or rsi_val >= 45:
            continue

        fvgs = fair_value_gap(high, low, min_gap_pct=0.005)
        if fvgs.empty:
            continue
        bullish = fvgs[fvgs["type"] == "bullish"]
        if bullish.empty:
            continue
        for _, gap in bullish.tail(3).iterrows():
            gap_high = gap["gap_high"]
            gap_low = gap["gap_low"]
            # FVG Quality Filter (TJR-style): skip young/tiny FVGs
            gap_age = len(df) - int(gap.name) if hasattr(gap, 'name') else 0
            if gap_age < 5:
                continue  # FVG must be at least 5 bars old
            gap_size_pct = (gap_high - gap_low) / current if current > 0 else 0
            if gap_size_pct < 0.005:
                continue  # FVG too small (noise)
            if not (gap_low * 0.98 <= current <= gap_high * 1.02):
                continue
            if close.iloc[-1] <= close.iloc[-2]:
                continue
            atr_val = float(atr(high, low, close, 14).iloc[-1])
            # Scale-out TP (TJR-style: 1:3 R:R instead of ~1:1.4)
            risk = current - gap_low * 0.97
            tp = current + 3.0 * risk if risk > 0 else current + 2.0 * atr_val
            sl = gap_low * 0.97
            rr = (tp - current) / (current - sl) if current > sl else 0
            if rr < 1.0:
                continue
            vol_r = float(volume_ratio(df["Volume"]).iloc[-1]) if "Volume" in df.columns else 1.0
            cat = "crypto" if symbol in CRYPTO_SYMBOLS else "forex"
            entry = round(current, 5) if cat == "forex" else _smart_round(current)
            signals.append({
                "strategy": "community_ict_fvg_selective",
                "symbol": symbol, "category": cat,
                "signal_type": "BUY",
                "entry_price": entry,
                "take_profit": round(tp, 5) if cat == "forex" else _smart_round(tp),
                "stop_loss": round(sl, 5) if cat == "forex" else _smart_round(sl),
                "confidence": round(min(0.78, 0.50 + (45 - rsi_val) / 50 + adx_val * 0.005), 2),
                "risk_reward": round(rr, 2),
                "reason": f"ICT FVG discount zone, ADX={adx_val:.0f}, RSI={rsi_val:.0f}",
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1), "volume_ratio": round(vol_r, 2),
                "atr_at_entry": round(atr_val, 6), "timestamp": _now_iso(),
            })
            break
    return signals


# =========================================================================
# Combined registry for merging into crypto/forex/equity
# =========================================================================

COMMUNITY_CRYPTO_STRATEGIES = {
    "community_ema_9_21_rsi_crypto":       community_ema_9_21_rsi_crypto,
    "community_bb_squeeze_breakout_crypto":  community_bb_squeeze_breakout_crypto,
    "community_rsi_extreme_reversal_crypto": community_rsi_extreme_reversal_crypto,
    "community_vwap_bounce_crypto":         community_vwap_bounce_crypto,
    "community_momentum_breakout_volume_crypto": community_momentum_breakout_volume_crypto,
    "community_ict_fvg_selective":          community_ict_fvg_selective,
}

COMMUNITY_FOREX_STRATEGIES = {
    "community_ema_8_21_scalp_forex":      community_ema_8_21_scalp_forex,
    "community_london_breakout_v2_forex":   community_london_breakout_v2_forex,
    "community_forex_zscore_mean_reversion": community_forex_zscore_mean_reversion,
    "community_ict_fvg_selective":          community_ict_fvg_selective,
}

COMMUNITY_EQUITY_STRATEGIES = {
    "community_orb_equity":                community_orb_equity,
    "community_penny_volume_surge":        community_penny_volume_surge,
}

COMMUNITY_STRATEGIES = {
    **COMMUNITY_CRYPTO_STRATEGIES,
    **COMMUNITY_FOREX_STRATEGIES,
    **COMMUNITY_EQUITY_STRATEGIES,
}
