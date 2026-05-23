#!/usr/bin/env python3
"""
Adaptive Stop-Loss Engine — Asset-class-aware SL/TP placement.

Replaces fixed ATR multipliers with regime-aware, volatility-adjusted stops.
Key insight: crypto ATR is 3-8% of price; equities are 0.5-2%; forex 0.3-1%.
Using crypto-calibrated stops on equities produces 78.9% SL hit rate (see PERFORMANCE_ANALYSIS_REPORT.md).
"""

import math
from typing import Optional, Tuple, Dict

ASSET_CLASS_CONFIG = {
    'CRYPTO': {
        'atr_multiplier_sl': 2.0,
        'atr_multiplier_tp': 3.0,
        'min_hold_candles': 4,
        'commission_rt': 0.0030,
        'slippage': 0.0005,
    },
    'EQUITY': {
        'atr_multiplier_sl': 1.5,
        'atr_multiplier_tp': 2.5,
        'min_hold_candles': 2,
        'commission_rt': 0.0070,
        'slippage': 0.0010,
    },
    'FOREX': {
        'atr_multiplier_sl': 1.2,
        'atr_multiplier_tp': 2.0,
        'min_hold_candles': 4,
        'commission_rt': 0.0002,
        'slippage': 0.0001,
    },
    'ETF': {
        'atr_multiplier_sl': 1.3,
        'atr_multiplier_tp': 2.0,
        'min_hold_candles': 2,
        'commission_rt': 0.0005,
        'slippage': 0.0003,
    },
    'FUTURES': {
        'atr_multiplier_sl': 1.4,
        'atr_multiplier_tp': 2.2,
        'min_hold_candles': 3,
        'commission_rt': 0.0020,
        'slippage': 0.0005,
    },
    'COMMODITY': {
        'atr_multiplier_sl': 1.3,
        'atr_multiplier_tp': 2.0,
        'min_hold_candles': 3,
        'commission_rt': 0.0015,
        'slippage': 0.0004,
    },
}


def classify_regime(vix: Optional[float] = None,
                    spx_vs_200dma: Optional[float] = None,
                    breadth_pct: Optional[float] = None) -> str:
    """Classify market regime from VIX + breadth data."""
    if vix is None:
        return 'UNKNOWN'
    if vix > 35:
        return 'HURRICANE'
    elif vix > 25 and (spx_vs_200dma is not None and spx_vs_200dma < 0):
        return 'STORM'
    elif vix > 20:
        return 'OVERCAST'
    elif vix > 15:
        return 'PARTLY_CLOUDY'
    else:
        return 'CLEAR_BULL'


REGIME_ADJUSTMENTS = {
    'CLEAR_BULL':   {'sl_mult': 0.90, 'tp_mult': 1.10},
    'PARTLY_CLOUDY': {'sl_mult': 1.00, 'tp_mult': 1.00},
    'OVERCAST':     {'sl_mult': 1.20, 'tp_mult': 0.85},
    'STORM':        {'sl_mult': 1.50, 'tp_mult': 0.75},
    'HURRICANE':    {'sl_mult': 2.00, 'tp_mult': 0.60},
    'UNKNOWN':      {'sl_mult': 1.10, 'tp_mult': 0.95},
}


def calculate_adaptive_stop(
    entry: float,
    atr: float,
    asset_class: str,
    direction: str = 'LONG',
    regime: str = 'UNKNOWN',
    vix: Optional[float] = None,
    is_earnings_week: bool = False,
) -> Dict:
    """
    Calculate asset-class-aware stop loss and take profit.
    
    Returns dict with sl, tp, rr, and config details.
    Returns None sl/tp if R:R < 1.2 (trade rejected).
    """
    if asset_class not in ASSET_CLASS_CONFIG:
        asset_class = 'CRYPTO'  # Default fallback
    
    config = ASSET_CLASS_CONFIG[asset_class].copy()
    regime_adj = REGIME_ADJUSTMENTS.get(regime, REGIME_ADJUSTMENTS['UNKNOWN'])
    
    # Apply regime adjustments
    sl_mult = config['atr_multiplier_sl'] * regime_adj['sl_mult']
    tp_mult = config['atr_multiplier_tp'] * regime_adj['tp_mult']
    
    # VIX-specific adjustments for equities
    if asset_class == 'EQUITY' and vix is not None:
        if vix > 30:
            sl_mult *= 1.3
        elif vix < 12:
            sl_mult *= 0.85
    
    # Earnings week: widen stops significantly
    if is_earnings_week:
        sl_mult *= 1.5
        tp_mult *= 0.8
    
    # Calculate SL/TP
    if direction == 'LONG':
        sl = entry - (atr * sl_mult)
        tp = entry + (atr * tp_mult)
    else:  # SHORT
        sl = entry + (atr * sl_mult)
        tp = entry - (atr * tp_mult)
    
    # R:R calculation
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    rr = reward / risk if risk > 0 else 0
    
    # Net edge after commission
    net_risk = risk + (entry * config['commission_rt'])
    net_reward = reward - (entry * config['commission_rt'])
    net_rr = net_reward / net_risk if net_risk > 0 else 0
    
    # Hard reject if net R:R < 1.2
    if net_rr < 1.2:
        return {
            'sl': None,
            'tp': None,
            'rr': rr,
            'net_rr': net_rr,
            'rejected': True,
            'reason': f'net_rr_too_low: {net_rr:.2f} (need >= 1.2)',
            'config_used': config,
            'sl_multiplier_used': sl_mult,
            'tp_multiplier_used': tp_mult,
        }
    
    return {
        'sl': round(sl, 6),
        'tp': round(tp, 6),
        'rr': round(rr, 2),
        'net_rr': round(net_rr, 2),
        'rejected': False,
        'reason': 'passed',
        'config_used': config,
        'sl_multiplier_used': round(sl_mult, 2),
        'tp_multiplier_used': round(tp_mult, 2),
        'regime': regime,
    }


def batch_calculate_stops(picks: list, market_state: dict = None) -> list:
    """
    Process a batch of picks through adaptive stop calculation.
    
    Args:
        picks: List of pick dicts with entry, atr, asset_class, direction, etc.
        market_state: Optional dict with vix, spx_vs_200dma, breadth_pct
    
    Returns:
        List of picks enriched with adaptive stop data.
    """
    if market_state is None:
        market_state = {}
    
    regime = classify_regime(
        vix=market_state.get('vix'),
        spx_vs_200dma=market_state.get('spx_vs_200dma'),
        breadth_pct=market_state.get('breadth_pct'),
    )
    
    enriched = []
    for pick in picks:
        result = calculate_adaptive_stop(
            entry=pick['entry'],
            atr=pick.get('atr', pick['entry'] * 0.02),  # Default 2% if no ATR
            asset_class=pick.get('asset_class', 'CRYPTO'),
            direction=pick.get('direction', 'LONG'),
            regime=regime,
            vix=market_state.get('vix'),
            is_earnings_week=pick.get('is_earnings_week', False),
        )
        
        pick_enriched = {**pick, 'adaptive_stop': result}
        if not result['rejected']:
            pick_enriched['sl'] = result['sl']
            pick_enriched['tp'] = result['tp']
            pick_enriched['rr'] = result['rr']
        
        enriched.append(pick_enriched)
    
    return enriched


if __name__ == '__main__':
    # Quick validation
    test_picks = [
        {'symbol': 'AAPL', 'entry': 185.0, 'atr': 3.2, 'asset_class': 'EQUITY', 'direction': 'LONG'},
        {'symbol': 'EURUSD', 'entry': 1.0850, 'atr': 0.0045, 'asset_class': 'FOREX', 'direction': 'LONG'},
        {'symbol': 'BTCUSDT', 'entry': 68000, 'atr': 1800, 'asset_class': 'CRYPTO', 'direction': 'LONG'},
        {'symbol': 'SPY', 'entry': 520.0, 'atr': 5.5, 'asset_class': 'ETF', 'direction': 'LONG'},
    ]
    
    market = {'vix': 18.5, 'spx_vs_200dma': 5.2, 'breadth_pct': 62}
    
    results = batch_calculate_stops(test_picks, market)
    for r in results:
        s = r['adaptive_stop']
        print(f"{r['symbol']:10} ({r['asset_class']:8}) | "
              f"SL: {s['sl']} | TP: {s['tp']} | R:R: {s['rr']} | "
              f"Net R:R: {s['net_rr']} | Rejected: {s['rejected']}")
