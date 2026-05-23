# alpha_engine/forex_carry_ppp.py
"""
Forex Carry Trade with PPP Equilibrium Overlay Strategy
=======================================================
Based on Kwas et al. (2024) ECB research on enhanced carry trades.
Combines traditional interest rate differentials with PPP-based equilibrium estimates.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any
from alpha_engine.indicators import sma, volume_ratio


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _get_category(symbol: str) -> str:
    return "forex"


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


def forex_carry_ppp(data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
    """Enhanced carry trade with PPP equilibrium overlay for major forex pairs."""
    signals = []

    # Test on single pair EURUSD (rehabilitated version)
    pairs = ["EURUSD"]

    for symbol in pairs:
        df = data.get(symbol)
        if df is None or len(df) < 252:  # Need at least 1 year for PPP estimation
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        # Get current exchange rate
        current_rate = float(close.iloc[-1])

        # Estimate PPP-based fair value (simplified model)
        ppp_fair_value = _estimate_ppp_fair_value(close, symbol)

        if ppp_fair_value is None:
            continue

        # Calculate deviation from PPP
        ppp_deviation = (current_rate - ppp_fair_value) / ppp_fair_value

        # Get interest rate differentials
        interest_diff = _get_interest_rate_diff(symbol)

        # Simplified pure carry signal: positive carry only (removed PPP overlay)
        if interest_diff > 0.001:  # 0.1% carry (relaxed for signal generation)
            # Additional filters
            sma_50 = sma(close, 50)
            if len(sma_50) > 0:
                sma50_val = float(sma_50.iloc[-1])
                if symbol.endswith("USD"):
                    if current_rate > sma50_val:
                        continue

            volatility = close.pct_change().rolling(20).std() * np.sqrt(252)
            current_vol = float(volatility.iloc[-1])
            if current_vol > 0.15:
                continue

            position_size_pct = min(0.05, interest_diff * 100)

            entry_price = current_rate

            target_deviation = 0.005  # Reduced from 1% to 0.5%
            if symbol.endswith("USD"):
                tp = ppp_fair_value * (1 - target_deviation)
            else:
                tp = ppp_fair_value * (1 + target_deviation)

            sl_deviation = 0.03  # Reduced from 5% to 3%
            if symbol.endswith("USD"):
                sl = ppp_fair_value * (1 - sl_deviation)
            else:
                sl = ppp_fair_value * (1 + sl_deviation)

            if symbol.endswith("USD"):
                rr = (tp - entry_price) / (entry_price - sl) if entry_price > sl else 0
            else:
                rr = (entry_price - tp) / (sl - entry_price) if sl > entry_price else 0

            if rr < 1.5:
                continue

            signals.append(
                {
                    "strategy": "forex_carry_ppp",
                    "symbol": symbol,
                    "category": "forex",
                    "signal_type": "BUY" if symbol.endswith("USD") else "SELL",
                    "entry_price": _smart_round(entry_price),
                    "take_profit": _smart_round(tp),
                    "stop_loss": _smart_round(sl),
                    "confidence": round(
                        min(
                            0.75,
                            0.50
                            + abs(ppp_deviation) * 10
                            + (interest_diff * 50)
                            + (0.1 if current_vol < 0.10 else 0),
                        ),
                        2,
                    ),
                    "risk_reward": round(rr, 2),
                    "reason": f"PPP deviation {ppp_deviation:.1%} + carry {interest_diff:.2%}, targeting {ppp_fair_value:.4f}",
                    "timeframe": "1d",
                    "ppp_deviation": round(ppp_deviation, 4),
                    "interest_diff": round(interest_diff, 4),
                    "position_size_pct": round(position_size_pct, 3),
                    "hold_months": 6,
                    "timestamp": _now_iso(),
                }
            )

        # Opposite signal: negative carry only
        elif interest_diff < -0.001:
            sma_50 = sma(close, 50)
            if len(sma_50) > 0:
                sma50_val = float(sma_50.iloc[-1])
                if symbol.endswith("USD"):
                    if current_rate < sma50_val:
                        continue

            volatility = close.pct_change().rolling(20).std() * np.sqrt(252)
            current_vol = float(volatility.iloc[-1])
            if current_vol > 0.15:
                continue

            position_size_pct = min(0.05, abs(interest_diff) * 100)

            entry_price = current_rate

            if symbol.endswith("USD"):
                tp = ppp_fair_value * (1 + 0.01)
                sl = ppp_fair_value * (1 + 0.05)
                rr = (entry_price - tp) / (sl - entry_price) if sl > entry_price else 0
            else:
                tp = ppp_fair_value * (1 - 0.01)
                sl = ppp_fair_value * (1 - 0.05)
                rr = (tp - entry_price) / (entry_price - sl) if entry_price > sl else 0

            if rr < 1.5:
                continue

            signals.append(
                {
                    "strategy": "forex_carry_ppp",
                    "symbol": symbol,
                    "category": "forex",
                    "signal_type": "SELL" if symbol.endswith("USD") else "BUY",
                    "entry_price": _smart_round(entry_price),
                    "take_profit": _smart_round(tp),
                    "stop_loss": _smart_round(sl),
                    "confidence": round(
                        min(
                            0.75,
                            0.50
                            + ppp_deviation * 10
                            + (abs(interest_diff) * 50)
                            + (0.1 if current_vol < 0.10 else 0),
                        ),
                        2,
                    ),
                    "risk_reward": round(rr, 2),
                    "reason": f"PPP deviation {ppp_deviation:.1%} + carry {interest_diff:.2%}, targeting {ppp_fair_value:.4f}",
                    "timeframe": "1d",
                    "ppp_deviation": round(ppp_deviation, 4),
                    "interest_diff": round(interest_diff, 4),
                    "position_size_pct": round(position_size_pct, 3),
                    "hold_months": 6,
                    "timestamp": _now_iso(),
                }
            )

    return signals


def _estimate_ppp_fair_value(close: pd.Series, symbol: str) -> float | None:
    """Simplified PPP estimation using long-term moving averages as proxy."""
    if len(close) < 200:
        return None

    ppp_proxy = close.rolling(200).mean()
    current_ppp = float(ppp_proxy.iloc[-1])

    if symbol in ["USDJPY", "USDCHF"]:
        current_ppp *= 0.995

    return current_ppp


def _get_interest_rate_diff(symbol: str) -> float:
    """Simplified interest rate differential estimation."""
    base_rates = {
        "EURUSD": 0.03,
        "GBPUSD": 0.04,
        "AUDUSD": 0.025,
        "USDCAD": -0.015,
        "USDCHF": -0.02,
        "USDJPY": -0.03,
    }

    return base_rates.get(symbol, 0.0)
