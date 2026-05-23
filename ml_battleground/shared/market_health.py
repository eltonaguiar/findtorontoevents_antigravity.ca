"""
Market Health Gate -- prevents trading during extreme conditions.
Sits in front of ALL 3 scanning systems as a circuit breaker.

Signals checked:
  1. Fear & Greed Index (extreme fear = panic)
  2. BTC trend vs SMA50/SMA200 + 24h momentum + ATR spike
  3. Funding rate extremes across pairs

Health levels:
  SAFE     -> trade freely
  CAUTION  -> reduce position size 50%, min confidence 0.55
  WARNING  -> 25% size, min confidence 0.70
  PANIC    -> Extreme fear: BUY conf>=0.55 at 50% size, SELL conf>=0.65 at 35% size
"""
import numpy as np
from enum import Enum
from typing import Optional


class MarketHealth(Enum):
    SAFE = "safe"           # Normal conditions, trade freely
    CAUTION = "caution"     # Elevated risk, reduce position size 50%
    WARNING = "warning"     # High risk, only take >0.70 confidence signals, 25% size
    PANIC = "panic"         # DO NOT TRADE -- circuit breaker active


def check_market_health(
    fear_greed: int,
    btc_df=None,  # Optional BTC OHLCV DataFrame
    funding_rates: Optional[dict] = None,
) -> tuple:
    """
    Assess market conditions and return health status + details.
    Uses multiple signals to avoid false positives.

    Returns (MarketHealth, details_dict)
    """
    signals = {}
    panic_count = 0
    warning_count = 0

    # --- Signal 1: Fear & Greed Index ---
    signals["fear_greed"] = fear_greed
    if fear_greed <= 15:
        panic_count += 2  # Strong panic signal (double weight)
        signals["fg_status"] = "EXTREME_FEAR"
    elif fear_greed <= 25:
        warning_count += 1
        signals["fg_status"] = "FEAR"
    elif fear_greed <= 35:
        signals["fg_status"] = "CAUTIOUS"
    else:
        signals["fg_status"] = "OK"

    # --- Signal 2: BTC Trend (if data available) ---
    if btc_df is not None and len(btc_df) >= 50:
        close_col = "close" if "close" in btc_df.columns else "Close"
        closes = btc_df[close_col].values
        current = float(closes[-1])

        # SMA checks
        sma50 = float(np.mean(closes[-50:]))
        sma200 = float(np.mean(closes[-200:])) if len(closes) >= 200 else sma50

        signals["btc_price"] = current
        signals["btc_sma50"] = round(sma50, 2)
        signals["btc_vs_sma50"] = round((current / sma50 - 1) * 100, 2)

        if current < sma200 * 0.85:  # 15% below SMA200
            panic_count += 1
            signals["btc_trend"] = "CRASH"
        elif current < sma50:
            warning_count += 1
            signals["btc_trend"] = "BEARISH"
        else:
            signals["btc_trend"] = "OK"

        # Recent momentum: 24-bar (1 day for 1h) change
        if len(closes) >= 24:
            change_24h = (current / float(closes[-24]) - 1) * 100
            signals["btc_24h_change"] = round(change_24h, 2)
            if change_24h < -10:
                panic_count += 2  # Crash in progress
                signals["btc_momentum"] = "CRASH_IN_PROGRESS"
            elif change_24h < -5:
                warning_count += 1
                signals["btc_momentum"] = "SHARP_DROP"
            else:
                signals["btc_momentum"] = "OK"

        # ATR spike detection
        if len(closes) >= 60:
            # Compute ATR-like volatility over recent bars
            high_col = "high" if "high" in btc_df.columns else "High"
            low_col = "low" if "low" in btc_df.columns else "Low"
            highs = btc_df[high_col].values
            lows = btc_df[low_col].values
            ranges = highs[-60:] - lows[-60:]
            current_range = float(ranges[-1])
            median_range = float(np.median(ranges[:-1]))
            if median_range > 0:
                atr_ratio = current_range / median_range
                signals["atr_spike_ratio"] = round(atr_ratio, 2)
                if atr_ratio > 3.0:
                    panic_count += 1
                    signals["volatility"] = "EXTREME_SPIKE"
                elif atr_ratio > 2.0:
                    warning_count += 1
                    signals["volatility"] = "ELEVATED"
                else:
                    signals["volatility"] = "NORMAL"

    # --- Signal 3: Funding Rate Extremes ---
    if funding_rates:
        extreme_funding = sum(1 for r in funding_rates.values() if abs(r) > 0.01)
        signals["extreme_funding_count"] = extreme_funding
        if extreme_funding >= 5:
            warning_count += 1
            signals["funding_status"] = "EXTREME"
        else:
            signals["funding_status"] = "OK"

    # --- Determine final health status ---
    if panic_count >= 2:
        health = MarketHealth.PANIC
    elif panic_count >= 1 or warning_count >= 3:
        health = MarketHealth.WARNING
    elif warning_count >= 1:
        health = MarketHealth.CAUTION
    else:
        health = MarketHealth.SAFE

    signals["health"] = health.value
    signals["panic_signals"] = panic_count
    signals["warning_signals"] = warning_count

    return health, signals


def apply_health_gate(
    health: MarketHealth,
    signals: list,
    min_confidence_override: Optional[float] = None,
) -> list:
    """
    Filter and adjust signals based on market health.

    PANIC: Extreme fear — BUY conf>=0.55 at 50% size, SELL conf>=0.65 at 35% size
    WARNING: Only signals with confidence >= 0.70, scale size to 25%
    CAUTION: Only signals with confidence >= 0.55, scale size to 50%
    SAFE: Pass through all signals
    """
    if health == MarketHealth.PANIC:
        # CAPITULATION GUARD (Feb 25 2026): When F&G <= 15 AND market is bouncing,
        # forcing shorts is catastrophic (-4.49% avg). Block shorts in extreme fear
        # and only allow HIGH-conviction sells in moderate panic.
        # Reviewed by: Inception Labs, Grok AI, Perplexity, Google/Gemini — all agree.
        fng = 50  # default
        for sig in signals:
            fng = sig.get("fng", sig.get("fear_greed", 50))
            break
        if fng <= 15:
            # Extreme fear — allow BOTH directions with reduced sizing.
            # Use max(ml_score, confidence) — min() was killing signals when
            # ml_score defaults to 0.5 (no model trained yet). The position
            # sizing reduction (50%/35%) is the real safety net, not the gate.
            filtered = []
            for s in signals:
                ml = s.get("ml_score", 0)
                sc = s.get("confidence", 0)
                # Use whichever score is available; if both exist, use max
                conf = max(ml, sc) if (ml > 0 and sc > 0) else (ml or sc or 0)
                sig_type = s.get("signal_type", "BUY")
                if sig_type == "BUY" and conf >= 0.50:
                    s["position_size_pct"] = s.get("position_size_pct", 2.0) * 0.50
                    s["health_adjusted"] = True
                    filtered.append(s)
                elif sig_type == "SELL" and conf >= 0.58:
                    # Moderate bar for shorts — sizing is already 35%
                    s["position_size_pct"] = s.get("position_size_pct", 2.0) * 0.35
                    s["health_adjusted"] = True
                    s["panic_sell"] = True
                    filtered.append(s)
            return filtered

        panic_sells = []
        for sig in signals:
            ml_score = sig.get("ml_score", 0)
            strat_conf = sig.get("confidence", 0)
            conf = max(ml_score, strat_conf) if (ml_score > 0 and strat_conf > 0) else (ml_score or strat_conf or 0)
            if sig.get("signal_type") == "SELL" and conf >= 0.65:
                sig["position_size_pct"] = sig.get("position_size_pct", 2.0) * 0.25
                sig["health_adjusted"] = True
                sig["panic_sell"] = True
                panic_sells.append(sig)
        return panic_sells

    if health == MarketHealth.SAFE:
        return signals

    min_conf = {
        MarketHealth.WARNING: 0.70,
        MarketHealth.CAUTION: 0.55,
    }.get(health, 0.40)

    if min_confidence_override is not None:
        min_conf = min_confidence_override

    size_mult = {
        MarketHealth.WARNING: 0.25,
        MarketHealth.CAUTION: 0.50,
    }.get(health, 1.0)

    filtered = []
    for sig in signals:
        conf = sig.get("confidence", sig.get("ml_score", 0))
        if conf >= min_conf:
            # In WARNING, reduce BUY size further if F&G < 25 (but don't block)
            if health == MarketHealth.WARNING:
                fg = sig.get("fear_greed", 50)
                if fg < 25 and sig.get("signal_type", "BUY") == "BUY":
                    sig["position_size_pct"] = sig.get("position_size_pct", 2.0) * 0.50
            sig["position_size_pct"] = sig.get("position_size_pct", 2.0) * size_mult
            sig["health_adjusted"] = True
            filtered.append(sig)

    return filtered


def dynamic_sl_multiplier(health: MarketHealth, base_mult: float = 1.5) -> float:
    """
    Widen stop losses during dangerous conditions.

    PANIC: N/A (no trading)
    WARNING: 2.5x base SL
    CAUTION: 1.5x base SL
    SAFE: 1.0x (unchanged)
    """
    scale = {
        MarketHealth.PANIC: 3.0,
        MarketHealth.WARNING: 2.5,
        MarketHealth.CAUTION: 1.5,
        MarketHealth.SAFE: 1.0,
    }
    return base_mult * scale.get(health, 1.0)
