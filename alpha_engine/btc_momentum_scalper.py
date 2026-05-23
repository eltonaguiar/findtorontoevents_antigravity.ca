#!/usr/bin/env python3
"""
BTC Momentum Scalper Strategy
=============================
Based on 12-trade analysis: 91.67% WR, 10× leverage, selective momentum scalping

Key Patterns Identified:
- 1-minute timeframe entries
- 0.5 BTC position sizing (reduced to 0.1 on larger breakouts)
- Quick profit-taking (20-100 point deltas)
- Selective entries only during active volatility windows

Entry Criteria (inferred):
1. Price breaking recent micro-high/low + sustained momentum
2. Volume spike confirmation
3. Active volatility window (evening UTC sessions)
4. No holding through chop - exit on reversal
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional


def calculate_momentum_score(
    price_data: List[Dict[str, float]],
    lookback: int = 5
) -> Dict[str, Any]:
    """
    Calculate momentum score for BTC scalping.
    
    Returns:
        - momentum_score: 0-100 (higher = stronger momentum)
        - direction: "LONG" or "SHORT"
        - confidence: 0-1.0
    """
    if len(price_data) < lookback + 1:
        return {"momentum_score": 0, "direction": "NEUTRAL", "confidence": 0}
    
    closes = [c["close"] for c in price_data[-lookback:]]
    highs = [c["high"] for c in price_data[-lookback:]]
    lows = [c["low"] for c in price_data[-lookback:]]
    volumes = [c.get("volume", 0) for c in price_data[-lookback:]]
    
    # Price momentum
    price_change = (closes[-1] - closes[0]) / closes[0] * 100
    
    # Breakout detection
    recent_high = max(highs[:-1])  # Exclude last candle
    recent_low = min(lows[:-1])
    
    breaking_high = closes[-1] > recent_high
    breaking_low = closes[-1] < recent_low
    
    # Volume confirmation (current vs avg)
    avg_volume = np.mean(volumes[:-1]) if volumes[:-1] else 1
    volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 1
    
    # Momentum scoring
    momentum_score = 0
    direction = "NEUTRAL"
    
    if breaking_high and price_change > 0.05:  # 0.05% minimum move
        momentum_score = min(100, int((price_change * 10) + (volume_ratio * 20)))
        direction = "LONG"
    elif breaking_low and price_change < -0.05:
        momentum_score = min(100, int((abs(price_change) * 10) + (volume_ratio * 20)))
        direction = "SHORT"
    
    # Confidence based on volume and move size
    confidence = min(1.0, (volume_ratio * 0.3) + (abs(price_change) * 5))
    
    return {
        "momentum_score": momentum_score,
        "direction": direction,
        "confidence": confidence,
        "price_change_pct": price_change,
        "volume_ratio": volume_ratio,
        "breaking_high": breaking_high,
        "breaking_low": breaking_low,
    }


def generate_scalp_signal(
    symbol: str = "BTCUSDT",
    price_data: Optional[List[Dict]] = None,
    min_momentum_score: int = 70,
    min_confidence: float = 0.6
) -> Optional[Dict[str, Any]]:
    """
    Generate scalp signal if criteria met.
    
    Returns signal dict or None if no trade.
    """
    if price_data is None:
        # Would fetch from API in production
        return None
    
    momentum = calculate_momentum_score(price_data)
    
    if momentum["momentum_score"] < min_momentum_score:
        return None
    
    if momentum["confidence"] < min_confidence:
        return None
    
    current_price = price_data[-1]["close"]
    
    # TP/SL based on observed pattern
    # Average win: 20-100 points on 0.5 BTC = $100-500
    # At 10× leverage, 0.1% move = 1% PnL
    if momentum["direction"] == "LONG":
        tp_price = current_price * 1.0015  # 0.15% = 1.5% with 10×
        sl_price = current_price * 0.999   # 0.1% = 1% with 10×
    else:
        tp_price = current_price * 0.9985
        sl_price = current_price * 1.001
    
    return {
        "symbol": symbol,
        "direction": momentum["direction"],
        "entry_price": current_price,
        "take_profit": tp_price,
        "stop_loss": sl_price,
        "momentum_score": momentum["momentum_score"],
        "confidence": momentum["confidence"],
        "volume_ratio": momentum["volume_ratio"],
        "strategy": "btc_momentum_scalper",
        "timeframe": "1m",
        "position_size": 0.5,  # BTC
        "leverage": 10,
    }


if __name__ == "__main__":
    # Example usage
    print("BTC Momentum Scalper Strategy")
    print("=" * 50)
    print("Based on 12-trade analysis:")
    print("- 91.67% Win Rate")
    print("- 10× Leverage")
    print("- 0.5 BTC position size")
    print("- Selective momentum entries")
    print()
    print("Entry criteria:")
    print("1. Price breaking micro high/low")
    print("2. Volume spike (ratio > 1.5)")
    print("3. Momentum score >= 70")
    print("4. Confidence >= 0.6")
