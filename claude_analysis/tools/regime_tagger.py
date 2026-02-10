#!/usr/bin/env python3
"""
GOLDMINE_CURSOR — Market Regime Tagger

Detects the current market regime based on:
  1. VIX level (high_vol if VIX > 25)
  2. SMA50 vs SMA200 (golden cross = bull, death cross = bear)
  3. Price vs SMA50 (above = trending up, below = trending down)
  4. 20-day return direction (sideways if < 2% absolute move)

Regimes:
  - bull: Price above SMA50 AND SMA200, positive momentum
  - bear: Price below SMA50 AND SMA200, negative momentum
  - sideways: Low directional movement (< 2% over 20 days)
  - high_vol: VIX > 25 regardless of direction

Usage:
  python regime_tagger.py --demo
  python regime_tagger.py --ticker SPY --days 252
"""

import argparse
import json
import sys
from datetime import datetime

try:
    import urllib.request
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False


def classify_regime(price_current, sma50, sma200, vix_level=None, return_20d=None):
    """
    Classify the market regime.

    Returns: dict with regime, confidence, and supporting signals
    """
    signals = []
    regime = 'unknown'
    confidence = 0

    # VIX check (overrides if extreme)
    if vix_level is not None and vix_level > 25:
        signals.append('VIX elevated ({:.1f} > 25)'.format(vix_level))
        regime = 'high_vol'
        confidence = min(100, int((vix_level - 25) * 5 + 60))
        return {
            'regime': regime,
            'confidence': confidence,
            'signals': signals,
            'sma50_trend': 'above' if price_current > sma50 else 'below',
            'sma200_trend': 'above' if price_current > sma200 else 'below',
            'vix_level': vix_level
        }

    # Trend analysis
    above_sma50 = price_current > sma50
    above_sma200 = price_current > sma200
    golden_cross = sma50 > sma200

    if above_sma50:
        signals.append('Price above SMA50')
    else:
        signals.append('Price below SMA50')

    if above_sma200:
        signals.append('Price above SMA200')
    else:
        signals.append('Price below SMA200')

    if golden_cross:
        signals.append('Golden Cross (SMA50 > SMA200)')
    else:
        signals.append('Death Cross (SMA50 < SMA200)')

    # Sideways check
    if return_20d is not None and abs(return_20d) < 2.0:
        regime = 'sideways'
        confidence = max(50, int(100 - abs(return_20d) * 25))
        signals.append('Low 20d move ({:.1f}%)'.format(return_20d))
    elif above_sma50 and above_sma200 and golden_cross:
        regime = 'bull'
        confidence = 80
        if return_20d is not None and return_20d > 0:
            confidence = min(95, confidence + int(return_20d * 3))
    elif not above_sma50 and not above_sma200 and not golden_cross:
        regime = 'bear'
        confidence = 80
        if return_20d is not None and return_20d < 0:
            confidence = min(95, confidence + int(abs(return_20d) * 3))
    elif above_sma200 and not above_sma50:
        regime = 'bull'  # Pullback in uptrend
        confidence = 55
        signals.append('Pullback within uptrend')
    elif not above_sma200 and above_sma50:
        regime = 'bear'  # Rally in downtrend
        confidence = 55
        signals.append('Rally within downtrend')
    else:
        regime = 'sideways'
        confidence = 50

    return {
        'regime': regime,
        'confidence': confidence,
        'signals': signals,
        'sma50_trend': 'above' if above_sma50 else 'below',
        'sma200_trend': 'above' if above_sma200 else 'below',
        'vix_level': vix_level
    }


def compute_sma(prices, period):
    """Compute simple moving average from a list of closing prices (most recent first)."""
    if len(prices) < period:
        return None
    return sum(prices[:period]) / period


def demo():
    """Run demo with sample scenarios."""
    print("=== GOLDMINE_CURSOR — Market Regime Tagger Demo ===\n")

    scenarios = [
        {'name': 'Strong Bull Market', 'price': 520, 'sma50': 505, 'sma200': 480, 'vix': 14, 'ret20': 5.2},
        {'name': 'Bear Market', 'price': 380, 'sma50': 410, 'sma200': 440, 'vix': 22, 'ret20': -8.5},
        {'name': 'High Volatility Crisis', 'price': 420, 'sma50': 450, 'sma200': 460, 'vix': 35, 'ret20': -12.0},
        {'name': 'Sideways / Choppy', 'price': 450, 'sma50': 448, 'sma200': 445, 'vix': 18, 'ret20': 0.8},
        {'name': 'Pullback in Uptrend', 'price': 495, 'sma50': 500, 'sma200': 475, 'vix': 19, 'ret20': -3.2},
        {'name': 'Rally in Downtrend', 'price': 420, 'sma50': 415, 'sma200': 440, 'vix': 20, 'ret20': 4.0},
    ]

    for s in scenarios:
        result = classify_regime(s['price'], s['sma50'], s['sma200'], s['vix'], s['ret20'])
        print("  Scenario: {}".format(s['name']))
        print("    Price: {} | SMA50: {} | SMA200: {} | VIX: {} | 20d Return: {}%".format(
            s['price'], s['sma50'], s['sma200'], s['vix'], s['ret20']))
        print("    REGIME: {} ({}% confidence)".format(result['regime'].upper(), result['confidence']))
        print("    Signals: {}".format(', '.join(result['signals'])))
        print()


def main():
    parser = argparse.ArgumentParser(description='GOLDMINE_CURSOR — Market Regime Tagger')
    parser.add_argument('--price', type=float, help='Current price')
    parser.add_argument('--sma50', type=float, help='50-day SMA')
    parser.add_argument('--sma200', type=float, help='200-day SMA')
    parser.add_argument('--vix', type=float, default=None, help='Current VIX level')
    parser.add_argument('--ret20', type=float, default=None, help='20-day return (%)')
    parser.add_argument('--demo', action='store_true', help='Run demo scenarios')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    if args.demo:
        demo()
        return

    if args.price is None or args.sma50 is None or args.sma200 is None:
        parser.print_help()
        print("\nExample: python regime_tagger.py --price 520 --sma50 505 --sma200 480 --vix 14 --ret20 5.2")
        sys.exit(1)

    result = classify_regime(args.price, args.sma50, args.sma200, args.vix, args.ret20)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("=== Market Regime Classification ===")
        print("  Regime: {} ({}% confidence)".format(result['regime'].upper(), result['confidence']))
        print("  Signals: {}".format(', '.join(result['signals'])))
        print("  SMA50 trend: {} | SMA200 trend: {}".format(result['sma50_trend'], result['sma200_trend']))


if __name__ == '__main__':
    main()
