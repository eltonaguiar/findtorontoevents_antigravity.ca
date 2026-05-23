# alpha_engine/equity_bb_zscore_mr.py
"""
Equity Bollinger Band Z-Score Mean-Reversion Strategy
===================================================
Based on Huang (2016) OU process research and Berkowitz (1988) VWAP studies.
Adapted single-asset mean-reversion using Bollinger Bands and Z-score.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any
from alpha_engine.indicators import bollinger_bands, rsi, sma, volume_ratio


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _get_category(symbol: str) -> str:
    return "equity"


def _smart_round(value: float) -> float:
    """Round to appropriate precision based on magnitude."""
    if abs(value) >= 100:
        return round(value, 2)
    elif abs(value) >= 10:
        return round(value, 3)
    else:
        return round(value, 4)


def _atr_tp_sl(
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    tp_mult: float = 2.0,
    sl_mult: float = 1.0,
):
    """Calculate take profit and stop loss using ATR."""
    # Simplified ATR calculation
    atr_period = 14
    tr = pd.concat(
        [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(atr_period).mean()

    current_atr = atr.iloc[-1]
    current_close = close.iloc[-1]

    tp = current_close + (current_atr * tp_mult)
    sl = current_close - (current_atr * sl_mult)

    return tp, sl


def equity_bb_zscore_mr(data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
    """Bollinger Band Z-score mean-reversion for equity indices."""
    signals = []
    # Focus on available equity symbols from config
    from config import EQUITY_SYMBOLS

    symbols = list(EQUITY_SYMBOLS.keys())

    for symbol in symbols:
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

        # Calculate Bollinger Bands (20-period, 2 SD)
        bb_data = bollinger_bands(close, 20, 2.0)
        bb_upper_20 = bb_data["upper"]
        bb_lower_20 = bb_data["lower"]
        sma_20 = bb_data["middle"]

        # Calculate Z-score: (price - mean) / std
        current_close = float(close.iloc[-1])
        current_sma = float(sma_20.iloc[-1])
        rolling_std = close.rolling(20).std()
        current_std = float(rolling_std.iloc[-1])

        if current_std == 0:
            continue

        z_score = (current_close - current_sma) / current_std

        # Pre-calculate common indicators
        vol_r = float(volume_ratio(volume).iloc[-1])
        sma_50 = sma(close, 50)
        sma_200 = sma(close, 200)
        rsi_14 = rsi(close, 14)

        # Mean-reversion signal: price below lower BB (relaxed Z-score < -1.2)
        if z_score < -1.0:
            # Additional filters
            # 1. Volume confirmation
            if vol_r < 1.1:
                continue

            # 2. Not in strong downtrend (SMA 50 > SMA 200)
            if len(sma_50) > 0 and len(sma_200) > 0:
                sma50_val = float(sma_50.iloc[-1])
                sma200_val = float(sma_200.iloc[-1])
                if sma50_val < sma200_val:
                    continue  # Skip if in strong downtrend

            # 3. RSI filter for longs (<40 for better entry)
            current_rsi = float(rsi_14.iloc[-1])
            if current_rsi >= 40:  # Require RSI < 40 for longs
                continue

            # Calculate entry/exit
            entry_price = current_close
            tp_mult = 1.5  # Target 1.5x the distance to mean
            sl_mult = 1.0  # Stop at 1x the distance beyond lower BB

            # Target profit: move back to mean (Z-score = 0)
            target_price = current_sma
            tp = min(target_price, entry_price * 1.08)  # Cap at 8% gain

            # Stop loss: below lower BB by additional 1 SD
            lower_bb = float(bb_lower_20.iloc[-1])
            sl = lower_bb * 0.98  # 2% below lower BB

            rr = (tp - entry_price) / (entry_price - sl) if entry_price > sl else 0
            if rr < 1.2:
                continue

            signals.append(
                {
                    "strategy": "equity_bb_zscore_mr",
                    "symbol": symbol,
                    "category": "equity",
                    "signal_type": "BUY",
                    "entry_price": _smart_round(entry_price),
                    "take_profit": _smart_round(tp),
                    "stop_loss": _smart_round(sl),
                    "confidence": round(
                        min(
                            0.70,
                            0.40
                            + abs(z_score) * 0.1
                            + (0.1 if vol_r > 1.3 else 0)
                            + (0.1 if current_rsi > 25 else 0),
                        ),
                        2,
                    ),
                    "risk_reward": round(rr, 2),
                    "reason": f"Z-score {z_score:.2f} (< -1.5), targeting mean reversion to {current_sma:.2f}, Vol {vol_r:.1f}x",
                    "timeframe": "1d",
                    "z_score": round(z_score, 2),
                    "bb_position": "below_lower",
                    "hold_days": 10,  # Extended hold time for better exit
                    "timestamp": _now_iso(),
                }
            )

        # Short signals when Z-score > +1.2 (relaxed from +1.5)
        elif z_score > 1.0:
            if vol_r < 1.1:
                continue

            # Not in strong uptrend
            if len(sma_50) > 0 and len(sma_200) > 0:
                sma50_val = float(sma_50.iloc[-1])
                sma200_val = float(sma_200.iloc[-1])
                if sma50_val > sma200_val:
                    continue  # Skip if in strong uptrend

            # RSI filter for shorts (>60 for better entry)
            current_rsi = float(rsi_14.iloc[-1])
            if current_rsi <= 60:  # Require RSI > 60 for shorts
                continue

            entry_price = current_close
            target_price = current_sma
            tp = max(target_price, entry_price * 0.92)  # Cap at 8% loss for shorts

            upper_bb = float(bb_upper_20.iloc[-1])
            sl = upper_bb * 1.02  # 2% above upper BB

            rr = (entry_price - tp) / (sl - entry_price) if sl > entry_price else 0
            if rr < 1.2:
                continue

            signals.append(
                {
                    "strategy": "equity_bb_zscore_mr",
                    "symbol": symbol,
                    "category": "equity",
                    "signal_type": "SELL",
                    "entry_price": _smart_round(entry_price),
                    "take_profit": _smart_round(tp),
                    "stop_loss": _smart_round(sl),
                    "confidence": round(
                        min(
                            0.70,
                            0.40
                            + z_score * 0.1
                            + (0.1 if vol_r > 1.3 else 0)
                            + (0.1 if current_rsi < 75 else 0),
                        ),
                        2,
                    ),
                    "risk_reward": round(rr, 2),
                    "reason": f"Z-score {z_score:.2f} (> +1.5), targeting mean reversion to {current_sma:.2f}, Vol {vol_r:.1f}x",
                    "timeframe": "1d",
                    "z_score": round(z_score, 2),
                    "bb_position": "above_upper",
                    "hold_days": 10,
                    "timestamp": _now_iso(),
                }
            )

    return signals
