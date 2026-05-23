#!/usr/bin/env python3
"""
Institutional Quant-Level Risk-Adjusted Scoring Engine

Upgrades from weighted "gambler" model to factor-based risk engine:
1. Alpha Decay & Freshness (exponential half-life)
2. Beta Adjustment (residual return vs market)
3. Liquidity Scaling (tradeable capacity)
4. Volatility Clustering (GARCH-lite penalty)
5. Kelly Criterion Position Sizing

From external agent review — integrated into quality_gates scoring pipeline.
"""

from __future__ import annotations
import math
from typing import Any, Dict, Optional


def institutional_scoring_engine(
    base_score: float,
    asset_metadata: Dict[str, Any],
    market_context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Risk-adjusted scoring: base_score × decay × beta_adj × liquidity × vol_penalty.

    Args:
        base_score: Raw score from quality_gates (0-100 scale)
        asset_metadata: {
            'signal_timestamp': float (unix),
            'half_life': float (hours, default 12 for crypto, 48 for equity),
            'beta': float (asset beta vs BTC/SPY),
            'volume_24h': float (USD),
            'market_cap': float (USD),
            'vol_trend': str ('stable', 'increasing', 'decreasing'),
            'historical_win_rate': float (0-1),
        }
        market_context: {
            'current_time': float (unix),
            'market_return': float (BTC/SPY return over signal period),
        }

    Returns:
        {
            'final_score': float,
            'recommended_size_pct': float,
            'is_institutional_grade': bool,
            'breakdown': dict,
        }
    """
    # Normalize base_score to 0-1
    norm_score = min(1.0, max(0.0, base_score / 100.0))

    # 1. ALPHA DECAY & FRESHNESS
    # Penalize signals that haven't been acted on within the 'Information Half-Life'
    current_time = market_context.get('current_time', 0)
    signal_time = asset_metadata.get('signal_timestamp', current_time)
    half_life = asset_metadata.get('half_life', 12)  # hours

    time_delta_hours = max(0, (current_time - signal_time) / 3600)
    if half_life > 0 and time_delta_hours > 0:
        decay_factor = math.exp(-0.693 * time_delta_hours / half_life)
    else:
        decay_factor = 1.0
    decay_factor = max(0.1, decay_factor)  # floor at 10%

    # 2. BETA ADJUSTMENT
    # If BTC/SPY is up 5% and the asset is up 5%, Alpha is 0.
    # Only score the 'Residual Return' (outperformance)
    beta = asset_metadata.get('beta', 1.0)
    market_return = market_context.get('market_return', 0.0)
    beta_adjusted = norm_score - (beta * market_return)
    beta_adjusted = max(0.0, beta_adjusted)  # floor at 0

    # 3. LIQUIDITY SCALING
    # Scale score based on "Tradeable Capacity"
    vol_24h = asset_metadata.get('volume_24h', 1_000_000)
    mcap = asset_metadata.get('market_cap', 10_000_000)

    if vol_24h > 0 and mcap > 0:
        liquidity_score = math.log1p(vol_24h) / math.log1p(mcap)
        liquidity_score = min(1.0, max(0.3, liquidity_score))  # clamp 0.3-1.0
    else:
        liquidity_score = 0.5  # unknown liquidity

    # 4. VOLATILITY CLUSTERING (GARCH-lite)
    # Reduce score if volatility is increasing (even if price is rising)
    vol_trend = asset_metadata.get('vol_trend', 'stable')
    vol_penalties = {
        'stable': 1.0,
        'decreasing': 1.05,  # slight bonus for calming vol
        'increasing': 0.75,
        'extreme': 0.50,
    }
    vol_penalty = vol_penalties.get(vol_trend, 0.85)

    # FINAL HEDGE FUND SCORE
    hf_score = beta_adjusted * decay_factor * liquidity_score * vol_penalty
    # Rescale to 0-100
    hf_score_100 = min(100.0, hf_score * 100)

    # 5. POSITION SIZING (Kelly Criterion)
    # Capped at 5% for institutional safety
    win_rate = asset_metadata.get('historical_win_rate', 0.5)
    edge = max(0.001, hf_score)

    if win_rate > 0 and edge > 0:
        # Kelly: f* = (p*b - q) / b where b = edge proxy
        q = 1.0 - win_rate
        kelly_raw = (win_rate - q / edge) if edge > 0 else 0
        kelly_size = max(0.0, min(0.05, kelly_raw * 0.5))  # half-Kelly, cap 5%
    else:
        kelly_size = 0.0

    return {
        'final_score': round(hf_score_100, 2),
        'recommended_size_pct': round(kelly_size * 100, 2),
        'is_institutional_grade': hf_score_100 > 65,
        'breakdown': {
            'base_normalized': round(norm_score, 4),
            'decay_factor': round(decay_factor, 4),
            'beta_adjusted': round(beta_adjusted, 4),
            'liquidity_score': round(liquidity_score, 4),
            'vol_penalty': round(vol_penalty, 2),
            'hf_score_raw': round(hf_score, 4),
        },
    }


def score_pick_institutional(pick: Dict[str, Any], market_return: float = 0.0) -> Dict[str, Any]:
    """
    Convenience wrapper: score a pick dict from the dashboard pipeline.

    Extracts metadata from pick fields, applies institutional scoring,
    and returns enriched pick with hf_institutional_score.
    """
    import time

    base_score = float(pick.get('score') or pick.get('elite_score') or 50)

    # Build asset_metadata from pick fields
    created = pick.get('created_at') or pick.get('timestamp') or ''
    try:
        from datetime import datetime, timezone
        if isinstance(created, str) and created:
            dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
            signal_ts = dt.timestamp()
        else:
            signal_ts = time.time()
    except Exception:
        signal_ts = time.time()

    ac = (pick.get('asset_class') or 'CRYPTO').upper()
    half_life = 12 if ac == 'CRYPTO' else 48  # crypto decays faster

    vol_24h = float(pick.get('volume_24h') or pick.get('quote_volume_24h') or 1_000_000)
    mcap = float(pick.get('market_cap') or 10_000_000)

    # Estimate beta from asset class
    beta = 1.0 if ac == 'CRYPTO' else 0.8

    # Vol trend from ATR data
    atr_14 = float(pick.get('atr_14') or pick.get('atr') or 0)
    atr_90p75 = float(pick.get('atr_90d_p75') or 0)
    if atr_14 > 0 and atr_90p75 > 0:
        vol_trend = 'increasing' if atr_14 > atr_90p75 else 'stable'
    else:
        vol_trend = 'stable'

    fwd_wr = float(pick.get('strat_fwd_wr') or pick.get('forward_wr') or 0.5)
    if fwd_wr > 1.5:
        fwd_wr = fwd_wr / 100.0

    result = institutional_scoring_engine(
        base_score=base_score,
        asset_metadata={
            'signal_timestamp': signal_ts,
            'half_life': half_life,
            'beta': beta,
            'volume_24h': vol_24h,
            'market_cap': mcap,
            'vol_trend': vol_trend,
            'historical_win_rate': fwd_wr,
        },
        market_context={
            'current_time': time.time(),
            'market_return': market_return,
        },
    )

    pick['hf_institutional_score'] = result['final_score']
    pick['hf_recommended_size_pct'] = result['recommended_size_pct']
    pick['hf_institutional_grade'] = result['is_institutional_grade']

    return result


if __name__ == '__main__':
    # Demo
    result = institutional_scoring_engine(
        base_score=75,
        asset_metadata={
            'signal_timestamp': 1775520000,
            'half_life': 12,
            'beta': 1.0,
            'volume_24h': 50_000_000,
            'market_cap': 500_000_000,
            'vol_trend': 'stable',
            'historical_win_rate': 0.65,
        },
        market_context={
            'current_time': 1775530000,
            'market_return': 0.02,
        },
    )
    print(f"HF Score: {result['final_score']}")
    print(f"Kelly Size: {result['recommended_size_pct']}%")
    print(f"Institutional Grade: {result['is_institutional_grade']}")
    print(f"Breakdown: {result['breakdown']}")
