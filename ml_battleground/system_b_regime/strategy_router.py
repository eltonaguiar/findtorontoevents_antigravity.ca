"""
System B: Strategy Router for "The Regime".
Maps each detected market regime to appropriate strategies with
regime-specific ATR-based TP/SL multipliers.

Reuses strategies from System A (system_a_filter/strategies.py) --
no duplication. Each regime activates a subset of strategies and
tunes TP/SL aggressiveness accordingly.
"""
import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import indicators as ind
from system_a_filter.strategies import (
    supertrend_follow,
    connors_rsi2,
    bollinger_keltner_squeeze,
    rsi_macd_confluence,
    ema_stack,
    volume_climax_reversal,
    swing_failure_pattern,
    ornstein_uhlenbeck,
    rsi_bb_macd_confluence,
    supertrend_volume_confirmed,
    fibonacci_retracement,
    ema_crossover_short,
    sell_the_rally,
    bear_trend_short,
)


# --- Regime-to-Strategy mapping ---
REGIME_STRATEGIES = {
    "trending_up": {
        "strategies": ["supertrend_follow", "ema_stack", "rsi_macd_confluence", "fibonacci_retracement"],
        "tp_atr_mult": 3.5,
        "sl_atr_mult": 1.5,
        "position_scale": 1.0,
        "prefer_sell": False,
        "description": "Trend-following with wide TP targets",
    },
    "trending_down": {
        "strategies": ["ema_crossover_short", "sell_the_rally", "bear_trend_short", "swing_failure_pattern", "supertrend_follow"],
        "tp_atr_mult": 3.0,
        "sl_atr_mult": 1.5,
        "position_scale": 1.0,
        "prefer_sell": True,
        "description": "Bear market shorts: EMA cross, rally rejection, trend continuation",
    },
    "range_bound": {
        "strategies": ["ornstein_uhlenbeck", "connors_rsi2", "bollinger_keltner_squeeze", "rsi_macd_confluence", "swing_failure_pattern", "fibonacci_retracement"],
        "tp_atr_mult": 3.0,   # raised from 2.0 — enforce minimum 2:1 TP:SL ratio
        "sl_atr_mult": 1.5,   # was 1.0 — too tight, instant stops in volatile ranges
        "position_scale": 1.0,
        "description": "Mean-reversion + confluence strategies",
    },
    "high_volatility": {
        "strategies": ["bollinger_keltner_squeeze", "swing_failure_pattern", "ema_crossover_short", "sell_the_rally"],
        "tp_atr_mult": 4.0,   # raised from 2.5 — enforce minimum 2:1 TP:SL ratio
        "sl_atr_mult": 2.0,
        "position_scale": 0.5,  # half size in volatile markets
        "description": "Squeeze + reversal + bear shorts with wide stops, reduced size",
    },
}

# Map strategy names to functions
STRATEGY_FUNCTIONS = {
    "supertrend_follow": supertrend_follow,
    "connors_rsi2": connors_rsi2,
    "bollinger_keltner_squeeze": bollinger_keltner_squeeze,
    "rsi_macd_confluence": rsi_macd_confluence,
    "ema_stack": ema_stack,
    "volume_climax_reversal": volume_climax_reversal,
    "swing_failure_pattern": swing_failure_pattern,
    "ornstein_uhlenbeck": ornstein_uhlenbeck,
    "rsi_bb_macd_confluence": rsi_bb_macd_confluence,
    "supertrend_volume_confirmed": supertrend_volume_confirmed,
    "fibonacci_retracement": fibonacci_retracement,
    "ema_crossover_short": ema_crossover_short,
    "sell_the_rally": sell_the_rally,
    "bear_trend_short": bear_trend_short,
}


def route(
    regime: str,
    regime_confidence: float,
    df: pd.DataFrame,
    pair: str,
    interval: str = "1h",
    min_rr: float = 1.2,
    fear_greed: int = 50,
) -> list[dict]:
    """
    Route to appropriate strategies based on detected regime.
    Sets regime-specific ATR TP/SL on each signal.

    Args:
        regime: one of REGIMES (trending_up, trending_down, range_bound, high_volatility)
        regime_confidence: 0.0-1.0 confidence in regime classification
        df: OHLCV DataFrame
        pair: trading pair (e.g. "BTCUSDT")
        interval: timeframe string
        min_rr: minimum risk:reward ratio to accept a signal
        fear_greed: Fear & Greed index (0-100)

    Returns:
        list of signal dicts with TP/SL/regime metadata attached
    """
    config = REGIME_STRATEGIES.get(regime, REGIME_STRATEGIES["range_bound"])
    strategy_names = config["strategies"]
    tp_mult = config["tp_atr_mult"]
    sl_mult = config["sl_atr_mult"]
    position_scale = config.get("position_scale", 1.0)
    prefer_sell = config.get("prefer_sell", False)

    if len(df) < 210:
        return []

    # Compute ATR for TP/SL
    atr_val = ind.atr(df["High"], df["Low"], df["Close"], 14)
    if len(atr_val) == 0:
        return []
    atr_now = float(atr_val.iloc[-1])
    if atr_now <= 0:
        return []

    # CRITICAL FIX: Disable mean-reversion strategies during extreme fear
    # Ornstein-Uhlenbeck assumes prices revert to mean, but during panic
    # (F&G < 20) prices are in momentum mode — O-U loses 100% of the time
    if fear_greed < 25:
        # During extreme fear, ALL mean-reversion strategies lose money
        # because prices are in momentum/cascade mode, not reverting to mean
        mean_rev_strats = {"ornstein_uhlenbeck", "connors_rsi2", "bollinger_keltner_squeeze"}
        blocked = [s for s in strategy_names if s in mean_rev_strats]
        strategy_names = [s for s in strategy_names if s not in mean_rev_strats]
        if blocked:
            print(f"  [Router] DISABLED mean-reversion for {pair} (F&G={fear_greed} < 25): {blocked}")

    signals = []

    for strat_name in strategy_names:
        fn = STRATEGY_FUNCTIONS.get(strat_name)
        if fn is None:
            continue

        try:
            raw_signals = fn(df, pair)
        except Exception as e:
            print(f"[Router] Strategy {strat_name} failed on {pair}: {e}")
            continue

        for sig in raw_signals:
            # In trending_down regime, BLOCK BUY signals entirely
            if prefer_sell and sig.get("signal_type") == "BUY":
                continue  # Skip BUY signals in downtrend — only SELL is viable

            # Set ATR-based TP/SL according to regime config
            entry = sig["entry_price"]
            signal_type = sig.get("signal_type", "BUY")

            if signal_type == "BUY":
                tp = entry + tp_mult * atr_now
                sl = entry - sl_mult * atr_now
                risk = entry - sl
                reward = tp - entry
            else:
                tp = entry - tp_mult * atr_now
                sl = entry + sl_mult * atr_now
                risk = sl - entry
                reward = entry - tp

            # --- Dynamic SL widening during volatility spikes ---
            if len(df) >= 60:
                close_col = "close" if "close" in df.columns else "Close"
                high_col = "high" if "high" in df.columns else "High"
                low_col = "low" if "low" in df.columns else "Low"
                ranges = (df[high_col] - df[low_col]).values[-60:]
                current_range = float(ranges[-1])
                median_range = float(np.median(ranges[:-1]))
                if median_range > 0 and current_range / median_range > 2.0:
                    old_sl = sl
                    sl_dist = abs(entry - sl)
                    if signal_type == "BUY":
                        sl = entry - sl_dist * 1.5
                        risk = entry - sl
                    else:
                        sl = entry + sl_dist * 1.5
                        risk = sl - entry
                    # reward stays the same, risk increased
                    print(f"  [volatility] Widening SL for {pair}: {old_sl:.4g} -> {sl:.4g}")

            # R:R gate
            rr = reward / risk if risk > 0 else 0
            if rr < min_rr:
                continue

            # Attach regime metadata
            sig.update({
                "take_profit": round(tp, 8),
                "stop_loss": round(sl, 8),
                "risk_reward": round(rr, 2),
                "tp_atr_mult": tp_mult,
                "sl_atr_mult": sl_mult,
                "tp_sl_method": "regime_atr",
                "regime": regime,
                "regime_confidence": round(regime_confidence, 4),
                "position_scale": position_scale,
                "timeframe": interval,
                "atr_value": round(atr_now, 8),
            })

            # Scale confidence by regime confidence
            raw_conf = sig.get("confidence", 0.5)
            sig["confidence"] = round(min(0.90, raw_conf * (0.7 + 0.3 * regime_confidence)), 4)

            signals.append(sig)

    return signals


def get_regime_config(regime: str) -> dict:
    """Get the full config dict for a regime (for dashboard display)."""
    return REGIME_STRATEGIES.get(regime, REGIME_STRATEGIES["range_bound"])


def get_allowed_strategies(regime: str) -> list[str]:
    """Get list of strategy names allowed for a given regime."""
    config = REGIME_STRATEGIES.get(regime, REGIME_STRATEGIES["range_bound"])
    return config["strategies"]
