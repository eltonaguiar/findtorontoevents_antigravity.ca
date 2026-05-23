# alpha_engine/high_conviction_enhancements.py
"""
High-Conviction Pick Enhancements
==================================
Enhancements to improve high-conviction pick identification and filtering.
Based on analysis in CODE_REVIEW_CONVICTION_PICKS_2026-04-09.md
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from alpha_engine.utils import _smart_round, _now_iso


def calculate_dynamic_score_thresholds(picks: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calculate adaptive score thresholds based on recent performance quartiles."""
    if not picks:
        return {"min_score": 60, "min_trust": 6, "min_fwd_wr": 0.45}

    # Use last 100 closed picks for threshold calibration
    recent_picks = sorted(picks, key=lambda p: p.get("closed_at", ""), reverse=True)[:100]
    if len(recent_picks) < 20:
        return {"min_score": 60, "min_trust": 6, "min_fwd_wr": 0.45}

    scores = [p.get("score", 0) for p in recent_picks if p.get("pnl_pct", 0) > 0]
    if scores:
        # Set threshold at 75th percentile of winning picks
        min_score = sorted(scores)[int(len(scores) * 0.75)]
    else:
        min_score = 60

    return {
        "min_score": max(50, min(80, min_score)),  # Clamp between 50-80
        "min_trust": 6,  # Keep static for now
        "min_fwd_wr": 0.45  # Keep static for now
    }


def enhanced_correlation_filter(pick: Dict[str, Any], active_picks: List[Dict[str, Any]]) -> bool:
    """Prevent correlated picks from dominating the high-conviction set."""
    symbol = pick.get("symbol", "").upper()
    direction = pick.get("direction", "")

    # Define correlation groups
    correlation_groups = {
        "BTC": ["BTCUSDT", "BTC-USD", "BTCBUSD"],
        "ETH": ["ETHUSDT", "ETH-USD", "ETHBUSD"],
        "CRYPTO_LARGE": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT"],
        "CRYPTO_SMALL": ["DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "FLOKIUSDT"],
        "TECH": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA"],
        "FINANCIAL": ["JPM", "BAC", "WFC", "GS", "MS"],
        "COMMODITIES": ["GC=F", "SI=F", "CL=F", "NG=F"]
    }

    # Check against already-passed picks
    correlated_count = 0
    for existing in active_picks:
        existing_symbol = existing.get("symbol", "").upper()

        # Check if symbols are in same correlation group
        for group, symbols in correlation_groups.items():
            if symbol in symbols and existing_symbol in symbols:
                if existing.get("direction") == direction:
                    correlated_count += 1
                break

    # Limit to 2 correlated picks maximum per group
    return correlated_count < 2


def optimize_stop_loss_placement(pick: Dict[str, Any]) -> Dict[str, Any]:
    """Dynamic SL placement based on volatility and historical optimal distances."""
    entry = pick.get("entry_price", 0)
    if entry <= 0:
        return {"sl_price": None, "reason": "no_entry"}

    # Base on ATR and historical optimal SL distances
    atr = pick.get("atr_14", 0)
    symbol = pick.get("symbol", "").upper()

    # Historical optimal SL distances (from backtest analysis)
    optimal_sl_distances = {
        "BTCUSDT": 0.02,  # 2% for major crypto pairs
        "ETHUSDT": 0.025,
        "SPY": 0.015,     # 1.5% for equities
        "QQQ": 0.015,
    }

    # Default based on asset class
    if symbol.endswith(('USDT', 'USD', 'BUSD')):
        default_distance = 0.03  # Crypto default
    else:
        default_distance = 0.02  # Equity default

    sl_distance = optimal_sl_distances.get(symbol, default_distance)

    # Adjust for volatility
    if atr > 0:
        vol_adjusted_distance = min(0.08, max(0.01, atr * 2))  # 2x ATR, capped
        sl_distance = (sl_distance + vol_adjusted_distance) / 2  # Average

    direction = pick.get("direction", "LONG")
    if direction.upper() == "LONG":
        sl_price = entry * (1 - sl_distance)
    else:
        sl_price = entry * (1 + sl_distance)

    return {
        "sl_price": round(sl_price, 6),
        "sl_distance_pct": sl_distance,
        "reason": "volatility_adjusted_atr_based"
    }


def calculate_kelly_position_size(pick: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate Kelly-based position sizing for high-conviction picks."""
    fwd_wr = pick.get("strat_fwd_wr", 0.5)
    if fwd_wr <= 0.5:
        return {"size_pct": 0.01, "reason": "insufficient_edge"}

    # Kelly formula: f = (bp - q) / b
    # where b = odds ratio, p = win prob, q = loss prob
    rr_ratio = pick.get("rr_ratio", 1.0)
    kelly_fraction = (fwd_wr - (1 - fwd_wr)) / rr_ratio

    # Conservative Kelly (half-size)
    position_size = max(0.005, min(0.05, kelly_fraction * 0.5))  # 0.5% to 5%

    return {
        "size_pct": position_size,
        "kelly_fraction": kelly_fraction,
        "reason": "kelly_based_conservative"
    }


def enhanced_volatility_filter(pick: Dict[str, Any]) -> int:
    """Advanced volatility-based filtering for high-conviction picks."""
    vol_20d = pick.get("volatility_20d", 0)
    vol_60d = pick.get("volatility_60d", 0)
    atr_current = pick.get("atr_14", 0)

    score_adjustment = 0

    # Volatility spike detection (existing)
    if vol_60d > 0 and vol_20d > 2.0 * vol_60d:
        score_adjustment -= 8

    # New: ATR-based entry quality
    if atr_current > 0:
        atr_90d_p75 = pick.get("atr_90d_p75", 0)
        atr_90d_p25 = pick.get("atr_90d_p25", 0)

        # High ATR = high predictability (trend moves with conviction)
        if atr_current > atr_90d_p75:
            score_adjustment += 5
        elif atr_current < atr_90d_p25:
            score_adjustment -= 5

    # Volatility regime classification
    if vol_20d > 0:
        if vol_20d < 0.02:
            score_adjustment += 3  # Low vol = better R:R
        elif vol_20d > 0.08:
            score_adjustment -= 5  # High vol = increased risk

    return score_adjustment


def compute_ml_ensemble_score(pick: Dict[str, Any]) -> float:
    """Combine multiple ML model predictions for enhanced scoring."""
    scores = []

    # Existing ml_score
    if pick.get("ml_score") is not None:
        scores.append(pick["ml_score"])

    # Add new ML components
    if pick.get("ml_crypto_pred_score") is not None:
        scores.append(pick["ml_crypto_pred_score"])

    if pick.get("neural_net_prediction") is not None:
        scores.append(pick["neural_net_prediction"])

    if pick.get("xgboost_prediction") is not None:
        scores.append(pick["xgboost_prediction"])

    if not scores:
        return 0.5  # Neutral

    # Weighted ensemble (can be calibrated based on validation)
    weights = [0.3, 0.25, 0.25, 0.2]  # Adjust based on historical performance
    ensemble = sum(s * w for s, w in zip(scores, weights[:len(scores)]))

    return min(1.0, max(0.0, ensemble))


def apply_direction_bias_adjustment(pick: Dict[str, Any]) -> Dict[str, Any]:
    """Apply direction bias adjustments based on asset class performance."""
    direction = pick.get("direction", "").upper()
    score = pick.get("score", 50)

    # SHORT bias adjustments (from analysis: SHORT outperforms LONG by 16pp in crypto)
    if direction == "SHORT":
        score += 8  # +8 points for SHORT direction
    elif direction == "LONG":
        score -= 8  # -8 points penalty for LONG

    # Asset class specific adjustments
    symbol = pick.get("symbol", "").upper()
    if symbol in ["BTCUSDT", "ETHUSDT", "BNBUSDT"]:  # Large cap crypto
        if direction == "SHORT":
            score += 5  # Extra boost for shorting large caps
    elif symbol in ["SPY", "QQQ", "IWM"]:  # Major equity indices
        if direction == "LONG":
            score += 3  # Slight boost for long equity indices

    pick["adjusted_score"] = score
    return pick


class PerformanceMonitor:
    """Monitor high-conviction pick performance in real-time."""

    def __init__(self):
        self.performance_window = []  # Last 50 closed HC picks
        self.drift_threshold = 0.15  # 15% WR drop triggers alert

    def update_performance(self, closed_pick: Dict[str, Any]) -> None:
        """Update rolling performance metrics."""
        if not closed_pick.get("high_conviction_gate_passed"):
            return

        self.performance_window.append(closed_pick)
        if len(self.performance_window) > 50:
            self.performance_window.pop(0)

        if len(self.performance_window) >= 10:
            self._check_for_drift()

    def _check_for_drift(self) -> None:
        """Check if recent performance has drifted from expectations."""
        recent_wr = sum(1 for p in self.performance_window[-20:] if p.get("pnl_pct", 0) > 0) / 20
        baseline_wr = 0.75  # Expected HC pick WR

        if recent_wr < baseline_wr - self.drift_threshold:
            # Trigger alert and potentially tighten gates
            self._trigger_performance_alert(recent_wr, baseline_wr)

    def _trigger_performance_alert(self, recent_wr: float, baseline_wr: float) -> None:
        """Log performance degradation and adjust gates if needed."""
        print(f"⚠️ High-conviction performance drift detected: "
              f"Recent WR {recent_wr:.1%} vs baseline {baseline_wr:.1%}")
        # Could automatically increase score thresholds or add new filters


def generate_performance_alerts(active_picks: List[Dict[str, Any]],
                              closed_picks: List[Dict[str, Any]]) -> List[str]:
    """Generate alerts for dashboard display."""
    alerts = []

    # Check HC pick count
    hc_picks = [p for p in active_picks if p.get("high_conviction_gate_passed")]
    if len(hc_picks) < 5:
        alerts.append("⚠️ Low high-conviction pick count - only {len(hc_picks)} qualify")

    # Check recent performance
    recent_closed = sorted(closed_picks, key=lambda p: p.get("closed_at", ""), reverse=True)[:20]
    recent_hc = [p for p in recent_closed if p.get("high_conviction_gate_passed")]
    if recent_hc:
        recent_wr = sum(1 for p in recent_hc if p.get("pnl_pct", 0) > 0) / len(recent_hc)
        if recent_wr < 0.65:
            alerts.append(f"⚠️ High-conviction WR degraded to {recent_wr:.1%}")

    return alerts</content>
<parameter name="filePath">C:\findtorontoevents_antigravity.ca\alpha_engine\high_conviction_enhancements.py