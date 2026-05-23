"""
ALPHA_ENGINE -- Justin Trader Strategies
=============================================
Strategies based on winning trader Justin's advice:
- EMA9 candle close crossovers (5m/15m primary, daily proxy here)
- HTF RSI confirmation (1h/4h, approximated with filters)
- Volume confirmation
- Patterns (double top, tweezer) for future variants
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

from alpha_engine.config import CRYPTO_SYMBOLS, CATEGORY_RISK
from alpha_engine.indicators import ema, rsi, atr, volume_ratio


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
               tp_mult: float = 2.5, sl_mult: float = 1.5,
               atr_period: int = 14) -> tuple[float, float, float]:
    atr_val = atr(high, low, close, atr_period)
    current_atr = float(atr_val.iloc[-1])
    price = float(close.iloc[-1])
    tp_long = price + tp_mult * current_atr
    sl_long = price - sl_mult * current_atr
    return _smart_round(price), _smart_round(tp_long), _smart_round(sl_long)


def _get_category(symbol: str) -> str:
    return CRYPTO_SYMBOLS.get(symbol, {}).get("cat", "crypto")


def justin_ema9_level_crypto(data: dict[str, pd.DataFrame],
                            context: Optional[dict] = None) -> list[dict]:
    """
    Justin EMA9 Close Level Cross Strategy (daily proxy for 5m/15m):
    - LONG entry: close crosses above EMA9, RSI > 45, vol_ratio > 1.2
    - SHORT entry: close crosses below EMA9, RSI < 55, vol_ratio > 1.2
    - TP/SL: ATR-scaled 2.5:1.5 R:R (1.67:1)
    """
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 20:
            continue
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        vol = df.get("Volume", pd.Series(1.0, index=close.index))

        ema9 = ema(close, 9)
        rsi_vals = rsi(close, 14)
        vol_r = volume_ratio(vol).iloc[-1] if len(vol) > 0 else 1.0

        c_cur = float(close.iloc[-1])
        c_prev = float(close.iloc[-2])
        e_cur = float(ema9.iloc[-1])
        e_prev = float(ema9.iloc[-2])
        rsi_val = float(rsi_vals.iloc[-1])
        vol_ratio_val = float(vol_r)

        entry, tp_long, sl_long = _atr_tp_sl(close, high, low)

        # LONG: close crosses above EMA9 + RSI filter + volume
        if (c_prev <= e_prev and c_cur > e_cur and
            rsi_val > 45 and vol_ratio_val > 1.2):
            tp = tp_long
            sl = sl_long
            rr = (tp - entry) / (entry - sl)
            if rr < 1.2:
                continue
            conf = min(0.85, 0.60 + min((rsi_val - 45)/30, 0.2) + min((vol_ratio_val - 1.2)/1.0, 0.05))
            signals.append({
                "strategy": "justin_ema9_level_crypto",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": entry,
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": f"Justin EMA9 bullish close cross, RSI={rsi_val:.1f}, vol={vol_ratio_val:.2f}x",
                "timeframe": "1d (5m proxy)",
                "rsi_at_entry": round(rsi_val, 1),
                "volume_ratio": round(vol_ratio_val, 2),
                "atr_at_entry": round(float(atr(high, low, close, 14).iloc[-1]), 6),
                "timestamp": _now_iso(),
            })

        # SHORT: close crosses below EMA9 + RSI filter + volume
        elif (c_prev >= e_prev and c_cur < e_cur and
              rsi_val < 55 and vol_ratio_val > 1.2):
            tp = entry - (tp_long - entry)  # symmetric
            sl = entry + (entry - sl_long)
            rr = (entry - tp) / (sl - entry)
            if rr < 1.2:
                continue
            conf = min(0.85, 0.60 + min((55 - rsi_val)/30, 0.2) + min((vol_ratio_val - 1.2)/1.0, 0.05))
            signals.append({
                "strategy": "justin_ema9_level_crypto",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "SELL",
                "entry_price": entry,
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": f"Justin EMA9 bearish close cross, RSI={rsi_val:.1f}, vol={vol_ratio_val:.2f}x",
                "timeframe": "1d (5m proxy)",
                "rsi_at_entry": round(rsi_val, 1),
                "volume_ratio": round(vol_ratio_val, 2),
                "atr_at_entry": round(float(atr(high, low, close, 14).iloc[-1]), 6),
                "timestamp": _now_iso(),
            })
    return signals


def justin_ema9_rsi_htf_variant(data: dict[str, pd.DataFrame],
                               context: Optional[dict] = None) -> list[dict]:
    """
    Variant with stricter HTF RSI filter (RSI(14*4) approx 4h RSI >50 for long)
    """
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 60:
            continue
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        vol = df.get("Volume", pd.Series(1.0, index=close.index))

        ema9 = ema(close, 9)
        rsi_short = rsi(close, 14)
        rsi_long = rsi(close, 56)  # approx 4h on daily (14*4)
        vol_r = volume_ratio(vol).iloc[-1] if len(vol) > 0 else 1.0

        c_cur = float(close.iloc[-1])
        c_prev = float(close.iloc[-2])
        e_cur = float(ema9.iloc[-1])
        e_prev = float(ema9.iloc[-2])
        rsi_s = float(rsi_short.iloc[-1])
        rsi_l = float(rsi_long.iloc[-1])
        vol_ratio_val = float(vol_r)

        entry, tp_long, sl_long = _atr_tp_sl(close, high, low)

        # LONG: EMA9 cross + short RSI>45 + long RSI>50 + vol
        if (c_prev <= e_prev and c_cur > e_cur and
            rsi_s > 45 and rsi_l > 50 and vol_ratio_val > 1.2):
            tp = tp_long
            sl = sl_long
            rr = (tp - entry) / (entry - sl)
            if rr < 1.2:
                continue
            conf = min(0.90, 0.65 + min((rsi_l - 50)/20, 0.15) + min((vol_ratio_val - 1.2)/1.0, 0.1))
            signals.append({
                "strategy": "justin_ema9_rsi_htf_variant",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": entry,
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": f"Justin EMA9 cross + RSI short={rsi_s:.1f} long={rsi_l:.1f}, vol={vol_ratio_val:.2f}x",
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_s, 1),
                "volume_ratio": round(vol_ratio_val, 2),
                "atr_at_entry": round(float(atr(high, low, close, 14).iloc[-1]), 6),
                "timestamp": _now_iso(),
            })

        # SHORT similar...
        elif (c_prev >= e_prev and c_cur < e_cur and
              rsi_s < 55 and rsi_l < 50 and vol_ratio_val > 1.2):
            tp = entry - (tp_long - entry)
            sl = entry + (entry - sl_long)
            rr = (entry - tp) / (sl - entry)
            if rr < 1.2:
                continue
            conf = min(0.90, 0.65 + min((50 - rsi_l)/20, 0.15) + min((vol_ratio_val - 1.2)/1.0, 0.1))
            signals.append({
                "strategy": "justin_ema9_rsi_htf_variant",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "SELL",
                "entry_price": entry,
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": f"Justin EMA9 cross + RSI short={rsi_s:.1f} long={rsi_l:.1f}, vol={vol_ratio_val:.2f}x",
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_s, 1),
                "volume_ratio": round(vol_ratio_val, 2),
                "atr_at_entry": round(float(atr(high, low, close, 14).iloc[-1]), 6),
                "timestamp": _now_iso(),
            })
    return signals