#!/usr/bin/env python3
"""
Missing Field Backfiller — fills the 70-90% missing fields in active/closed picks.

From Copilot analysis:
- 90% missing elite_score
- 87% missing ml_score
- 73% missing risk_reward
- 70% missing strategy name

This module backfills computed values from available fields so the
quality gates and scoring can actually work.

Usage:
    from missing_field_backfiller import backfill_picks
    enriched = backfill_picks(raw_picks)
"""

from typing import Dict, List, Optional
import math


def backfill_risk_reward(pick: Dict) -> Optional[float]:
    """Compute RR from entry/tp/sl if missing."""
    if pick.get('risk_reward') and pick['risk_reward'] > 0:
        return pick['risk_reward']
    
    entry = pick.get('entry_price', pick.get('entry', 0))
    tp = pick.get('take_profit', pick.get('tp', 0))
    sl = pick.get('stop_loss', pick.get('sl', 0))
    
    if not all([entry, tp, sl]) or entry == sl:
        return None
    
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    return round(reward / risk, 2) if risk > 0 else None


def backfill_strategy(pick: Dict) -> str:
    """Infer strategy name from available fields."""
    if pick.get('strategy') and pick['strategy'] != 'unknown':
        return pick['strategy']
    
    # From source_system
    source = pick.get('source_system', '')
    if source:
        return source
    
    # From signal_type (antigravity picks)
    signal = pick.get('signal_type', '')
    if signal:
        return signal.lower()
    
    # From algorithm (stocks)
    algo = pick.get('algorithm', '')
    if algo:
        return algo.lower().replace(' ', '_')
    
    # From mode (quan_engine)
    mode = pick.get('mode', '')
    if mode:
        return f'quan_engine_{mode.lower()}'
    
    return 'unknown'


def backfill_ml_score(pick: Dict) -> float:
    """Compute a proxy ml_score from available fields."""
    if pick.get('ml_score') and pick['ml_score'] > 0:
        return pick['ml_score']
    
    if pick.get('ml_composite_score') and pick['ml_composite_score'] > 0:
        return pick['ml_composite_score']
    
    # Proxy: normalize confidence to 0-1 scale
    conf = pick.get('confidence', 0.5)
    if conf > 1:
        conf = conf / 100
    
    # Adjust by RR if available
    rr = backfill_risk_reward(pick) or 1.0
    rr_factor = min(1.0, rr / 2.0)  # Normalize RR to 0-1
    
    # Simple proxy: 60% confidence + 40% RR quality
    return round(0.6 * conf + 0.4 * rr_factor, 3)


def backfill_elite_score(pick: Dict) -> float:
    """
    Compute proxy elite_score from available fields.
    
    Real elite_score components (from audit dashboard):
    - Forward WR + Track Record (40 pts)
    - Regime Bonus (20 pts)
    - Technical Alignment (5 pts)
    - Various other factors
    
    We approximate with what's available.
    """
    if pick.get('elite_score') and pick['elite_score'] > 0:
        return pick['elite_score']
    
    score = 40  # Base (average)
    
    # Forward WR proxy (0-30 pts)
    conf = pick.get('confidence', 0.5)
    if conf > 1:
        conf = conf / 100
    score += conf * 30
    
    # RR quality (0-15 pts)
    rr = backfill_risk_reward(pick) or 1.0
    score += min(15, rr * 10)
    
    # Direction × regime (0-15 pts)
    direction = pick.get('direction', 'LONG')
    regime = pick.get('market_regime', pick.get('regime', 'UNKNOWN'))
    if regime in ('BULL', 'NEUTRAL', 'CLEAR_BULL', 'PARTLY_CLOUDY') and direction == 'LONG':
        score += 15
    elif regime in ('BEAR', 'STORM') and direction == 'SHORT':
        score += 15
    elif regime in ('UNKNOWN', 'OVERCAST'):
        score += 7
    
    return round(min(100, max(0, score)), 1)


def backfill_direction(pick: Dict) -> str:
    """Ensure direction field exists."""
    if pick.get('direction'):
        return pick['direction'].upper()
    
    side = pick.get('side', pick.get('type', ''))
    if side:
        return side.upper()
    
    return 'LONG'  # Default


def backfill_asset_class(pick: Dict) -> str:
    """Infer asset class from symbol."""
    if pick.get('asset_class'):
        return pick['asset_class'].upper()
    
    symbol = pick.get('symbol', pick.get('pair', '')).upper()
    
    if 'USDT' in symbol or 'USDC' in symbol or 'BUSD' in symbol:
        return 'CRYPTO'
    if '=X' in symbol:
        return 'FOREX'
    if symbol.startswith('XAU') or symbol.startswith('XAG'):
        return 'COMMODITY'
    if '=F' in symbol:
        return 'FUTURES'
    if symbol in ('SPY', 'QQQ', 'TLT', 'IWM', 'DIA', 'VTI', 'VOO'):
        return 'ETF'
    if len(symbol) <= 5 and symbol.isalpha():
        return 'EQUITY'
    
    return 'CRYPTO'  # Default


def backfill_symbol(pick: Dict) -> str:
    """Normalize symbol field."""
    return pick.get('symbol', pick.get('pair', pick.get('ticker', 'UNKNOWN')))


def backfill_picks(picks: List[Dict]) -> List[Dict]:
    """
    Backfill all missing fields in a list of picks.
    Returns enriched list with all critical fields populated.
    """
    enriched = []
    
    stats = {
        'total': len(picks),
        'rr_backfilled': 0,
        'strategy_backfilled': 0,
        'ml_score_backfilled': 0,
        'elite_backfilled': 0,
        'direction_backfilled': 0,
        'asset_class_backfilled': 0,
    }
    
    for pick in picks:
        p = {**pick}
        
        # Symbol
        p['symbol'] = backfill_symbol(p)
        
        # Direction
        if not p.get('direction'):
            p['direction'] = backfill_direction(p)
            stats['direction_backfilled'] += 1
        
        # Asset class
        if not p.get('asset_class'):
            p['asset_class'] = backfill_asset_class(p)
            stats['asset_class_backfilled'] += 1
        
        # Risk/Reward
        if not p.get('risk_reward') or p['risk_reward'] <= 0:
            rr = backfill_risk_reward(p)
            if rr:
                p['risk_reward'] = rr
                stats['rr_backfilled'] += 1
        
        # Strategy
        if not p.get('strategy') or p['strategy'] in ('unknown', ''):
            p['strategy'] = backfill_strategy(p)
            stats['strategy_backfilled'] += 1
        
        # ML score
        if not p.get('ml_score') or p['ml_score'] <= 0:
            p['ml_score'] = backfill_ml_score(p)
            stats['ml_score_backfilled'] += 1
        
        # Elite score
        if not p.get('elite_score') or p['elite_score'] <= 0:
            p['elite_score'] = backfill_elite_score(p)
            stats['elite_backfilled'] += 1
        
        # Track what was backfilled
        p['_backfilled'] = True
        
        enriched.append(p)
    
    return enriched, stats


def print_backfill_report(stats: Dict):
    """Print backfill statistics."""
    n = stats['total']
    print(f"\n{'='*50}")
    print(f"BACKFILL REPORT — {n} picks processed")
    print(f"{'='*50}")
    for field, count in stats.items():
        if field == 'total':
            continue
        pct = (count / n * 100) if n > 0 else 0
        print(f"  {field:30s}: {count:5d} / {n} ({pct:.0f}%)")


if __name__ == '__main__':
    # Test with mock data that mimics the broken state
    mock_picks = [
        {'symbol': 'BTCUSDT', 'entry_price': 68000, 'take_profit': 70000, 'stop_loss': 67000, 'confidence': 0.82},
        {'symbol': 'AAPL', 'entry_price': 185, 'take_profit': 192, 'stop_loss': 180, 'confidence': 0.75},
        {'pair': 'EURUSD', 'entry': 1.085, 'tp': 1.092, 'sl': 1.081, 'confidence': 65, 'source_system': 'funding_momentum'},
        {'symbol': 'ETHUSDT', 'confidence': 0.55, 'mode': 'SCALP'},
    ]
    
    enriched, stats = backfill_picks(mock_picks)
    print_backfill_report(stats)
    
    print(f"\nSample enriched pick:")
    for k, v in enriched[0].items():
        print(f"  {k}: {v}")
