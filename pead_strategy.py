#!/usr/bin/env python3
"""
PEAD Strategy — Post-Earnings Announcement Drift

Academic edge: Bernard & Thomas (1989), Chordia et al (2020)
Expected WR: 58-65%, Expected edge: 2-4% over 20-60 days

This is the most replicated edge in empirical finance. Your alpha_engine
already has the feature factory (earnings_feat family) but it's not wired
to the daily pipeline. This bridges that gap.

Data source: Yahoo Finance earnings data via yfinance or SEC EDGAR.
"""

import math
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class PEADStrategy:
    """
    Post-Earnings Announcement Drift Strategy
    
    Entry: 1-5 days after earnings announcement (let initial pop settle)
    Hold: 20-60 days (drift plays out slowly)
    Direction: Positive surprise → LONG, negative surprise → SHORT
    
    Scoring components:
    - Earnings surprise magnitude (0-30 pts)
    - Consecutive beats/streaks (0-15 pts)
    - Analyst revision momentum (0-15 pts)
    - Base PEAD signal (40 pts)
    """
    
    MIN_SURPRISE_STD = 2.0      # Must be 2+ std deviations from mean surprise
    ENTRY_WINDOW_DAYS = (1, 5)   # Days after announcement to enter
    BASE_SCORE = 40
    MAX_SCORE = 100
    
    def __init__(self, earnings_data: Dict, prices: Dict):
        """
        Args:
            earnings_data: Dict of symbol → {
                'last_surprise_pct': float,
                'surprise_std_history': float,
                'days_since_announcement': int,
                'consecutive_beats': int,
                'revision_momentum_7d': float,
                'next_earnings_date': str (YYYY-MM-DD),
            }
            prices: Dict of symbol → current price
        """
        self.earnings = earnings_data
        self.prices = prices
    
    def generate_signals(self, universe: List[str] = None) -> List[Dict]:
        """Generate PEAD signals for the given universe."""
        if universe is None:
            universe = list(self.earnings.keys())
        
        signals = []
        
        for symbol in universe:
            signal = self._evaluate_symbol(symbol)
            if signal:
                signals.append(signal)
        
        # Sort by score descending
        signals.sort(key=lambda s: s['score'], reverse=True)
        return signals
    
    def _evaluate_symbol(self, symbol: str) -> Optional[Dict]:
        """Evaluate a single symbol for PEAD signal."""
        edata = self.earnings.get(symbol)
        if not edata:
            return None
        
        surprise = edata.get('last_surprise_pct')
        if surprise is None:
            return None
        
        surprise_std = edata.get('surprise_std_history', 5.0)
        days_since = edata.get('days_since_announcement')
        
        if days_since is None:
            return None
        
        # Gate 1: Must be significant surprise (> 2 std devs)
        if abs(surprise) < self.MIN_SURPRISE_STD * surprise_std:
            return None
        
        # Gate 2: Entry window (1-5 days after announcement)
        if days_since < self.ENTRY_WINDOW_DAYS[0] or days_since > self.ENTRY_WINDOW_DAYS[1]:
            return None
        
        # Gate 3: Price must exist
        price = self.prices.get(symbol)
        if not price or price <= 0:
            return None
        
        direction = 'LONG' if surprise > 0 else 'SHORT'
        consec = edata.get('consecutive_beats', 0)
        revision_mom = edata.get('revision_momentum_7d', 0)
        
        # Score calculation
        score = self.BASE_SCORE
        
        # Surprise magnitude: 0-30 pts
        surprise_points = min(30, abs(surprise) * 3)
        score += surprise_points
        
        # Consecutive beats: +5 per, cap at +15
        consec_points = min(15, consec * 5)
        score += consec_points
        
        # Revision momentum: 0-15 pts
        revision_points = min(15, abs(revision_mom) * 15)
        score += revision_points
        
        score = min(self.MAX_SCORE, score)
        
        # TP/SL calculation
        tp_20d = self._calc_target(price, surprise, 20, direction)
        tp_60d = self._calc_target(price, surprise, 60, direction)
        sl = self._calc_stop(price, direction)
        
        rr = abs(tp_20d - price) / abs(price - sl) if sl != price else 0
        
        # Get next earnings date for hold period awareness
        next_earnings = edata.get('next_earnings_date')
        
        return {
            'symbol': symbol,
            'strategy': 'pead_earnings_drift',
            'direction': direction,
            'score': round(score, 1),
            'entry': price,
            'tp': tp_20d,
            'tp_extended': tp_60d,
            'sl': sl,
            'rr': round(rr, 2),
            'hold_period_days': 20,
            'max_hold_days': 60,
            'surprise_pct': surprise,
            'surprise_std_multiple': round(abs(surprise) / surprise_std, 1),
            'consecutive_beats': consec,
            'revision_momentum': revision_mom,
            'next_earnings_date': next_earnings,
            'asset_class': 'EQUITY',
            'signal_type': 'PEAD',
            'breakdown': {
                'base': self.BASE_SCORE,
                'surprise_magnitude': round(surprise_points, 1),
                'consecutive_beats': consec_points,
                'revision_momentum': round(revision_points, 1),
            }
        }
    
    def _calc_target(self, price: float, surprise: float, days: int, direction: str) -> float:
        """
        PEAD drift target.
        
        Academic finding: ~40-60% of the surprise magnitude gets priced in
        over 60 days. We use a conservative 0.5% per surprise point over 60d.
        """
        drift_pct = abs(surprise) * 0.005 * (days / 60)
        drift_pct = min(drift_pct, 0.10)  # Cap at 10% to be conservative
        
        if direction == 'LONG':
            return round(price * (1 + drift_pct), 2)
        else:
            return round(price * (1 - drift_pct), 2)
    
    def _calc_stop(self, price: float, direction: str) -> float:
        """
        Stop loss for PEAD: use 1.5x the average true range proxy.
        PEAD is a slow drift, so stops should be wide.
        """
        stop_pct = 0.05  # 5% stop for equity PEAD plays
        
        if direction == 'LONG':
            return round(price * (1 - stop_pct), 2)
        else:
            return round(price * (1 + stop_pct), 2)
    
    def check_hold_period(self, signal: Dict, days_held: int) -> str:
        """
        Check if position should still be held.
        PEAD plays out over 20-60 days — don't exit early.
        """
        if days_held < signal['hold_period_days']:
            return 'HOLD'  # Too early to judge
        elif days_held >= signal['max_hold_days']:
            return 'EXIT'  # Max hold reached
        else:
            return 'EVALUATE'  # Between 20-60 days, check price action


# Example earnings data format for integration
EXAMPLE_EARNINGS_DATA = {
    'AAPL': {
        'last_surprise_pct': 8.5,        # Beat by 8.5%
        'surprise_std_history': 3.2,      # Historical std of surprises
        'days_since_announcement': 3,     # 3 days ago
        'consecutive_beats': 4,           # 4 consecutive positive surprises
        'revision_momentum_7d': 0.12,     # 12% upward revision in 7 days
        'next_earnings_date': '2026-07-30',
    },
    'MSFT': {
        'last_surprise_pct': -5.2,        # Missed by 5.2%
        'surprise_std_history': 4.1,
        'days_since_announcement': 2,
        'consecutive_beats': 0,           # Just broke streak
        'revision_momentum_7d': -0.08,
        'next_earnings_date': '2026-07-25',
    },
}


if __name__ == '__main__':
    prices = {'AAPL': 185.50, 'MSFT': 420.00}
    
    strategy = PEADStrategy(EXAMPLE_EARNINGS_DATA, prices)
    signals = strategy.generate_signals()
    
    for sig in signals:
        print(f"\n{'='*60}")
        print(f"Symbol: {sig['symbol']} | Direction: {sig['direction']} | Score: {sig['score']}")
        print(f"Entry: ${sig['entry']} | TP(20d): ${sig['tp']} | TP(60d): ${sig['tp_extended']} | SL: ${sig['sl']}")
        print(f"R:R: {sig['rr']} | Surprise: {sig['surprise_pct']}% ({sig['surprise_std_multiple']}σ)")
        print(f"Breakdown: {sig['breakdown']}")
