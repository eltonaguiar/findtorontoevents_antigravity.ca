#!/usr/bin/env python3
"""
Non-Crypto Smart Score — replaces crypto-specific scoring components for equities/forex/ETFs.

Key changes from crypto Smart Score:
- VIX regime replaces crypto regime
- Earnings calendar gate replaces MTF gate
- Sector momentum replaces ensemble gate
- Exponential freshness decay (crypto used linear)
- Time-of-day: equity open/close edges replace crypto hour patterns

From SCORE_PNL_EDGE_REVIEW: elite_score has Spearman 0.39 on non-crypto
vs 0.13 on crypto. Non-crypto scores BETTER — don't dilute it with crypto gates.
"""

import math
from typing import Dict, Optional


def calculate_non_crypto_smart_score(
    pick: Dict,
    vix_regime: str = 'UNKNOWN',
    vix: Optional[float] = None,
    days_to_earnings: Optional[int] = None,
    sector_momentum_20d: Optional[float] = None,
    daily_aligned: Optional[bool] = None,
    weekly_aligned: Optional[bool] = None,
) -> Dict:
    """
    Non-crypto adapted Smart Score (0-100).
    
    Components:
    1. Direction × VIX Regime (25 pts)
    2. Elite Score Quality (35 pts)
    3. Freshness — exponential decay (15 pts)
    4. TP Upside Remaining (15 pts)
    5. Weekly/Daily TF Alignment (10 pts)
    6. Earnings Calendar Gate (+10/-15)
    7. Sector Momentum Gate (+5/-10)
    """
    score = 0
    breakdown = {}
    
    # 1. Direction × VIX Regime (25 pts)
    direction = pick.get('direction', 'LONG')
    if vix_regime in ('CLEAR_BULL', 'PARTLY_CLOUDY'):
        if direction == 'LONG':
            score += 25
            breakdown['regime'] = 25
        else:
            score += 5  # SHORT in bull gets penalized
            breakdown['regime'] = 5
    elif vix_regime == 'OVERCAST':
        score += 12
        breakdown['regime'] = 12
    elif vix_regime in ('STORM', 'HURRICANE'):
        if direction == 'SHORT':
            score += 25
            breakdown['regime'] = 25
        else:
            score += 5
            breakdown['regime'] = 5
    else:  # UNKNOWN
        score += 12
        breakdown['regime'] = 12
    
    # 2. Elite Score Quality (35 pts)
    elite = pick.get('elite_score', 50)
    elite_pts = min(35, max(0, elite * 0.35))
    score += elite_pts
    breakdown['elite'] = round(elite_pts, 1)
    
    # 3. Freshness — exponential decay with 18h half-life (15 pts)
    # Equities trade 6.5h/day, so 18h captures ~3 trading sessions
    age_h = pick.get('age_hours', 0)
    freshness_pts = 15 * math.exp(-age_h / 18)
    score += freshness_pts
    breakdown['freshness'] = round(freshness_pts, 1)
    
    # 4. TP Upside Remaining (15 pts)
    tp = pick.get('tp', 0)
    entry = pick.get('entry', 0)
    current = pick.get('current_price', entry)
    
    if tp and entry and tp != entry:
        if direction == 'LONG':
            tp_remaining = (tp - current) / (tp - entry) if (tp - entry) > 0 else 0
        else:
            tp_remaining = (current - tp) / (entry - tp) if (entry - tp) > 0 else 0
        tp_remaining = max(0, min(1, tp_remaining))
        
        if tp_remaining > 0.7:
            tp_pts = 15
        elif tp_remaining > 0.5:
            tp_pts = 10
        elif tp_remaining > 0.3:
            tp_pts = 5
        else:
            tp_pts = 0
    else:
        tp_pts = 7  # Unknown, give neutral
    score += tp_pts
    breakdown['tp_remaining'] = tp_pts
    
    # 5. Weekly/Daily TF Alignment (10 pts)
    if daily_aligned is True and weekly_aligned is True:
        tf_pts = 10
    elif daily_aligned is True or weekly_aligned is True:
        tf_pts = 5
    elif daily_aligned is False and weekly_aligned is False:
        tf_pts = 0  # Both contradict
    else:
        tf_pts = 5  # Unknown/neutral
    score += tf_pts
    breakdown['tf_alignment'] = tf_pts
    
    # 6. Earnings Calendar Gate (+10/-15) — replaces crypto MTF gate
    if days_to_earnings is not None:
        if days_to_earnings > 10:
            earnings_pts = 10  # Safe zone
        elif days_to_earnings > 5:
            earnings_pts = 5
        elif days_to_earnings > 2:
            earnings_pts = 0  # Approaching earnings, neutral
        elif days_to_earnings >= 0 and direction == 'LONG':
            earnings_pts = -15  # Pre-earnings IV crush penalty
        elif days_to_earnings < -1 and days_to_earnings > -5 and direction == 'SHORT':
            earnings_pts = -15  # Post-earnings gap risk
        else:
            earnings_pts = 0
    else:
        earnings_pts = 0  # Unknown earnings date = neutral
    score += earnings_pts
    breakdown['earnings_gate'] = earnings_pts
    
    # 7. Sector Momentum Gate (+5/-10) — replaces crypto ensemble gate
    if sector_momentum_20d is not None:
        if direction == 'LONG':
            if sector_momentum_20d > 3:
                sector_pts = 5  # Strong sector tailwind
            elif sector_momentum_20d > 0:
                sector_pts = 3
            elif sector_momentum_20d > -3:
                sector_pts = 0
            else:
                sector_pts = -10  # Fighting sector headwind
        else:  # SHORT
            if sector_momentum_20d < -3:
                sector_pts = 5
            elif sector_momentum_20d < 0:
                sector_pts = 3
            else:
                sector_pts = -5
    else:
        sector_pts = 0
    score += sector_pts
    breakdown['sector_momentum'] = sector_pts
    
    final_score = min(100, max(0, score))
    
    return {
        'smart_score': round(final_score, 1),
        'breakdown': breakdown,
        'vix_regime': vix_regime,
        'earnings_gate': earnings_pts,
        'sector_gate': sector_pts,
    }


# Mapping for sector ETF lookups
SECTOR_ETF_MAP = {
    # Technology
    'AAPL': 'XLK', 'MSFT': 'XLK', 'GOOGL': 'XLK', 'META': 'XLK', 'NVDA': 'XLK',
    'AMZN': 'XLY', 'TSLA': 'XLY',
    # Healthcare
    'PFE': 'XLV', 'UNH': 'XLV', 'ABBV': 'XLV', 'JNJ': 'XLV',
    # Financials
    'JPM': 'XLF', 'BAC': 'XLF', 'GS': 'XLF',
    # Energy
    'XOM': 'XLE', 'CVX': 'XLE',
    # Consumer
    'WMT': 'XLP', 'SBUX': 'XLY', 'KO': 'XLP',
    # Industrial
    'GM': 'XLI', 'F': 'XLI', 'CAT': 'XLI',
    # Meme/speculative — use broad market
    'GME': 'SPY', 'AMC': 'SPY',
}

def get_sector_etf(symbol: str) -> str:
    """Map equity symbol to its sector ETF."""
    return SECTOR_ETF_MAP.get(symbol.upper(), 'SPY')


if __name__ == '__main__':
    test_picks = [
        {
            'symbol': 'AAPL', 'direction': 'LONG', 'entry': 185.0,
            'tp': 192.0, 'current_price': 186.5, 'elite_score': 72,
            'age_hours': 4,
        },
        {
            'symbol': 'PFE', 'direction': 'LONG', 'entry': 25.0,
            'tp': 27.0, 'current_price': 25.2, 'elite_score': 65,
            'age_hours': 12,
        },
    ]
    
    for pick in test_picks:
        result = calculate_non_crypto_smart_score(
            pick,
            vix_regime='PARTLY_CLOUDY',
            vix=17.5,
            days_to_earnings=25,
            sector_momentum_20d=2.1,
            daily_aligned=True,
            weekly_aligned=True,
        )
        print(f"{pick['symbol']:6} Smart Score: {result['smart_score']:.0f} | Breakdown: {result['breakdown']}")
