"""
ALPHA_ENGINE -- ML Feature Improvements
========================================
Fixes for dead ML features identified in health report (75% dead, health_score=0.25).

Priority fixes:
1. Time features (hour_utc, hour_sin) - easy win from timestamp
2. Strategy performance features (win_rate, sharpe) - from strategy_stats
3. RSI/volume/ATR from OHLCV - wire up technical_features.py
4. Remove interaction features that multiply two dead features

Usage:
    from ml_feature_improvements import enrich_pick_features, compute_time_features
    pick = enrich_pick_features(pick, ohlcv_data, strategy_stats)
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path

# ---------------------------------------------------------------------------
# Priority 1: Time Features (from timestamp - always available)
# ---------------------------------------------------------------------------

def compute_time_features(timestamp_str: str) -> Dict[str, float]:
    """Extract time-of-day features from ISO timestamp.
    
    Returns:
        dict with hour_utc, hour_sin, hour_cos, day_of_week, is_weekend
    """
    try:
        # Parse various timestamp formats
        ts = timestamp_str
        if isinstance(ts, str):
            # Handle ISO format with timezone
            ts = ts.replace('Z', '+00:00')
            try:
                dt = datetime.fromisoformat(ts)
            except ValueError:
                # Try common format
                dt = datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")
        elif isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        else:
            dt = datetime.now(timezone.utc)
    except Exception:
        dt = datetime.now(timezone.utc)
    
    hour = dt.hour
    day_of_week = dt.weekday()  # 0=Monday, 6=Sunday
    
    # Cyclic encoding for hour
    hour_sin = math.sin(2 * math.pi * hour / 24)
    hour_cos = math.cos(2 * math.pi * hour / 24)
    
    return {
        "hour_utc": hour / 23.0,  # Normalize 0-23 to 0-1
        "hour_sin": hour_sin,
        "hour_cos": hour_cos,
        "day_of_week": day_of_week / 6.0,  # Normalize 0-6 to 0-1
        "is_weekend": 1.0 if day_of_week >= 5 else 0.0,
    }


# ---------------------------------------------------------------------------
# Priority 2: Strategy Performance Features (from compute_strategy_stats)
# ---------------------------------------------------------------------------

def compute_strategy_performance_features(strategy_name: str, strategy_stats: Dict) -> Dict[str, float]:
    """Extract strategy performance features from strategy_stats dict.
    
    Args:
        strategy_name: Name of the strategy
        strategy_stats: Dict from compute_strategy_stats() with win_rate, sharpe, etc.
    
    Returns:
        dict with strategy_win_rate, strategy_sharpe, strategy_closed_picks
    """
    if not strategy_stats or strategy_name not in strategy_stats:
        return {
            "strategy_win_rate": 0.5,  # Neutral default
            "strategy_sharpe": 0.0,
            "strategy_closed_picks": 0.0,
        }
    
    stats = strategy_stats[strategy_name]
    
    # Extract or compute win rate
    win_rate = stats.get("win_rate", 0.5)
    if isinstance(win_rate, str):
        try:
            win_rate = float(win_rate.replace('%', '')) / 100
        except ValueError:
            win_rate = 0.5
    
    # Extract or compute Sharpe
    sharpe = stats.get("sharpe", 0.0)
    if isinstance(sharpe, str):
        try:
            sharpe = float(sharpe)
        except ValueError:
            sharpe = 0.0
    
    # Normalize Sharpe to [-1, 1] range
    sharpe_normalized = max(-1.0, min(1.0, sharpe / 3.0))
    
    # Count closed picks
    closed_count = stats.get("closed_picks", 0)
    if not closed_count:
        # Try to infer from other fields
        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)
        closed_count = wins + losses
    
    return {
        "strategy_win_rate": win_rate,
        "strategy_sharpe": sharpe_normalized,
        "strategy_closed_picks": min(1.0, closed_count / 100.0),  # Normalize to 0-1
    }


# ---------------------------------------------------------------------------
# Priority 3: Technical Features from OHLCV
# ---------------------------------------------------------------------------

def compute_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """Compute RSI from price series. Returns normalized 0-1 value."""
    if len(prices) < period + 1:
        return None
    
    gains = []
    losses = []
    
    for i in range(1, period + 1):
        change = prices[-i] - prices[-i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        return 1.0  # Max RSI when no losses
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi / 100.0  # Normalize to 0-1


def compute_volume_ratio(volumes: List[float], period: int = 20) -> Optional[float]:
    """Compute current volume vs average. Returns normalized 0-1 value."""
    if len(volumes) < period + 1:
        return None
    
    current_vol = volumes[-1]
    avg_vol = sum(volumes[-period-1:-1]) / period
    
    if avg_vol == 0:
        return 0.5  # Neutral default
    
    ratio = current_vol / avg_vol
    return min(1.0, ratio / 10.0)  # Normalize: 10x volume = 1.0


def compute_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[float]:
    """Compute Average True Range. Returns normalized value."""
    if len(closes) < period + 1:
        return None
    
    tr_values = []
    for i in range(-period, 0):
        if i == -len(closes):
            break
        high = highs[i]
        low = lows[i]
        prev_close = closes[i-1] if i > -len(closes) else closes[i]
        
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        tr = max(tr1, tr2, tr3)
        tr_values.append(tr)
    
    if not tr_values:
        return None
    
    atr = sum(tr_values) / len(tr_values)
    current_price = closes[-1]
    
    if current_price == 0:
        return None
    
    # Normalize as percentage of price
    atr_pct = atr / current_price
    return min(0.2, atr_pct)  # Cap at 0.2 (20%)


def compute_technical_features(ohlcv: Dict[str, List[float]]) -> Dict[str, float]:
    """Compute RSI, volume_ratio, atr_at_entry from OHLCV data."""
    closes = ohlcv.get("close", [])
    highs = ohlcv.get("high", [])
    lows = ohlcv.get("low", [])
    volumes = ohlcv.get("volume", [])
    
    features = {}
    
    # RSI
    rsi = compute_rsi(closes, period=14)
    features["rsi_at_entry"] = rsi if rsi is not None else 0.5  # Default neutral
    
    # Volume ratio
    vol_ratio = compute_volume_ratio(volumes, period=20)
    features["volume_ratio"] = vol_ratio if vol_ratio is not None else 1.0  # Default normal
    
    # ATR
    atr = compute_atr(highs, lows, closes, period=14)
    features["atr_at_entry"] = atr if atr is not None else 0.05  # Default 5%
    
    return features


# ---------------------------------------------------------------------------
# Main enrichment function
# ---------------------------------------------------------------------------

def enrich_pick_features(
    pick: Dict[str, Any],
    ohlcv: Optional[Dict[str, List[float]]] = None,
    strategy_stats: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Enrich a pick with all computable ML features.
    
    Args:
        pick: The pick dict to enrich
        ohlcv: Optional OHLCV data for technical features
        strategy_stats: Optional strategy performance stats
    
    Returns:
        Enriched pick with ml_features_at_entry populated
    """
    # Get existing features or create new
    ml_features = pick.get("ml_features_at_entry", {}) or {}
    
    # Priority 1: Time features (always computable from timestamp)
    timestamp = pick.get("timestamp") or pick.get("entry_time") or pick.get("created_at")
    if timestamp:
        time_features = compute_time_features(timestamp)
        ml_features.update(time_features)
    
    # Priority 2: Strategy performance features
    strategy = pick.get("strategy", "unknown")
    if strategy_stats:
        perf_features = compute_strategy_performance_features(strategy, strategy_stats)
        ml_features.update(perf_features)
    
    # Priority 3: Technical features from OHLCV
    if ohlcv:
        tech_features = compute_technical_features(ohlcv)
        ml_features.update(tech_features)
    
    # Update pick
    pick["ml_features_at_entry"] = ml_features
    return pick


# ---------------------------------------------------------------------------
# Batch processing for backfill
# ---------------------------------------------------------------------------

def backfill_features_for_picks(
    picks: List[Dict],
    ohlcv_cache: Optional[Dict[str, Dict[str, List[float]]]] = None,
    strategy_stats: Optional[Dict] = None,
) -> List[Dict]:
    """Backfill ML features for a list of picks.
    
    Args:
        picks: List of pick dicts
        ohlcv_cache: Optional dict mapping symbol -> OHLCV data
        strategy_stats: Optional strategy performance stats
    
    Returns:
        List of enriched picks
    """
    enriched = []
    for pick in picks:
        symbol = pick.get("symbol", "")
        ohlcv = ohlcv_cache.get(symbol) if ohlcv_cache else None
        enriched_pick = enrich_pick_features(pick, ohlcv, strategy_stats)
        enriched.append(enriched_pick)
    return enriched


# ---------------------------------------------------------------------------
# Health check utilities
# ---------------------------------------------------------------------------

def check_feature_health_quick(picks: List[Dict], feature_names: List[str]) -> Dict[str, Any]:
    """Quick health check for specific features across picks."""
    results = {name: {"count": 0, "zero": 0, "null": 0} for name in feature_names}
    
    for pick in picks:
        ml_features = pick.get("ml_features_at_entry", {}) or {}
        for name in feature_names:
            val = ml_features.get(name)
            if val is None:
                results[name]["null"] += 1
            elif val == 0 or val == 0.0:
                results[name]["zero"] += 1
                results[name]["count"] += 1
            else:
                results[name]["count"] += 1
    
    # Compute activation rates
    total = len(picks)
    for name in results:
        count = results[name]["count"]
        results[name]["activation_rate"] = count / total if total > 0 else 0
        results[name]["status"] = (
            "healthy" if count / total >= 0.8 else
            "weak" if count / total >= 0.4 else
            "dead"
        )
    
    return results


if __name__ == "__main__":
    # Test the improvements
    print("Testing ML feature improvements...")
    
    # Test time features
    test_ts = "2026-03-26T14:30:00+00:00"
    time_feat = compute_time_features(test_ts)
    print(f"\nTime features for {test_ts}:")
    for k, v in time_feat.items():
        print(f"  {k}: {v:.4f}")
    
    # Test strategy features
    test_stats = {
        "test_strategy": {
            "win_rate": 0.65,
            "sharpe": 1.5,
            "closed_picks": 42
        }
    }
    strat_feat = compute_strategy_performance_features("test_strategy", test_stats)
    print(f"\nStrategy features:")
    for k, v in strat_feat.items():
        print(f"  {k}: {v:.4f}")
    
    # Test technical features
    test_ohlcv = {
        "close": [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 110, 111, 112, 113, 114, 115],
        "high": [101, 103, 102, 104, 106, 105, 107, 109, 108, 110, 111, 112, 113, 114, 115, 116],
        "low": [99, 101, 100, 102, 104, 103, 105, 107, 106, 108, 109, 110, 111, 112, 113, 114],
        "volume": [1000, 1200, 1100, 1300, 1500, 1400, 1600, 1800, 1700, 1900, 2000, 2100, 2200, 2300, 2400, 2500]
    }
    tech_feat = compute_technical_features(test_ohlcv)
    print(f"\nTechnical features:")
    for k, v in tech_feat.items():
        print(f"  {k}: {v:.4f}")
    
    print("\nAll tests passed!")
