"""
Quantum Fusion Strategy - Quick Validation Test
===============================================

Fast validation of core functionality with synthetic data
"""

import pandas as pd
import numpy as np
from quantum_fusion_strategy import QuantumFusionStrategy

def create_synthetic_data(length=500, volatility=0.02, trend_strength=0.001):
    """Create synthetic OHLCV data for testing."""

    np.random.seed(42)

    # Generate price series with trend and volatility
    returns = np.random.normal(trend_strength, volatility, length)
    prices = 50000 * np.exp(np.cumsum(returns))

    # Create OHLCV data
    data = []
    for i in range(length):
        price = prices[i]
        high = price * (1 + np.random.uniform(0, 0.02))
        low = price * (1 - np.random.uniform(0, 0.02))
        open_price = data[-1]['close'] if data else price
        volume = np.random.randint(1000, 10000)

        data.append({
            'open': open_price,
            'high': high,
            'low': low,
            'close': price,
            'volume': volume
        })

    return pd.DataFrame(data)

def test_strategy_core_functionality():
    """Test core strategy functionality."""

    print("🧬 Quantum Fusion Strategy - Core Functionality Test")
    print("=" * 60)

    strategy = QuantumFusionStrategy()

    # Test different market regimes
    regimes = [
        ("trending_bull", 0.002, 0.015),  # Strong uptrend
        ("high_volatility", 0.000, 0.04),  # High volatility
        ("ranging", 0.000, 0.01),         # Sideways
        ("trending_bear", -0.001, 0.02),  # Downtrend
    ]

    results = []

    for regime_name, trend, vol in regimes:
        print(f"\n🧪 Testing {regime_name} market regime...")

        # Create synthetic data
        data = create_synthetic_data(length=300, trend_strength=trend, volatility=vol)

        # Test multiple timeframes
        timeframes = ['1h', '4h', '1d']

        for tf in timeframes:
            try:
                # Generate signals
                signals = strategy.generate_signals(data, 'BTC', tf)

                # Analyze signals
                if signals:
                    directions = [s.direction for s in signals]
                    buy_signals = directions.count('BUY')
                    sell_signals = directions.count('SELL')

                    avg_confidence = np.mean([s.confidence for s in signals])
                    avg_ml_score = np.mean([s.ml_score for s in signals])

                    regimes_found = set(s.regime for s in signals)

                    result = {
                        'regime': regime_name,
                        'timeframe': tf,
                        'total_signals': len(signals),
                        'buy_signals': buy_signals,
                        'sell_signals': sell_signals,
                        'avg_confidence': round(avg_confidence, 3),
                        'avg_ml_score': round(avg_ml_score, 3),
                        'regimes_detected': list(regimes_found),
                        'signal_balance': 'balanced' if abs(buy_signals - sell_signals) <= 2 else ('bullish' if buy_signals > sell_signals else 'bearish')
                    }

                    results.append(result)

                    print(f"   {tf}: {len(signals)} signals ({buy_signals}B/{sell_signals}S), Conf: {avg_confidence:.3f}, ML: {avg_ml_score:.3f}")

                else:
                    print(f"   {tf}: No signals generated")

            except Exception as e:
                print(f"   {tf}: Error - {e}")

    # Summary analysis
    print("\n" + "="*60)
    print("📊 VALIDATION SUMMARY")
    print("="*60)

    if results:
        total_tests = len(results)
        avg_signals = np.mean([r['total_signals'] for r in results])
        avg_confidence = np.mean([r['avg_confidence'] for r in results])
        avg_ml_score = np.mean([r['avg_ml_score'] for r in results])

        print(f"✅ Total Tests: {total_tests}")
        print(f"📈 Average Signals per Test: {avg_signals:.1f}")
        print(f"🎯 Average Confidence: {avg_confidence:.3f}")
        print(f"🧠 Average ML Score: {avg_ml_score:.3f}")

        # Check for balanced signal generation
        balanced_signals = sum(1 for r in results if r['signal_balance'] == 'balanced')
        print(f"⚖️ Balanced Signal Distribution: {balanced_signals}/{total_tests} tests")

        # Check regime detection
        regime_detection = len(set(r['regime'] for r in results if r['regimes_detected']))
        print(f"🎭 Regimes Detected: {regime_detection} different regime types")

        # Validation criteria
        signals_ok = avg_signals >= 3
        confidence_ok = avg_confidence >= 0.7
        ml_score_ok = avg_ml_score >= 0.5
        balance_ok = balanced_signals >= total_tests * 0.6

        print("
✅ VALIDATION CHECKS:"        print(f"   • Signals Generated: {'✅' if signals_ok else '❌'} ({avg_signals:.1f} >= 3)")
        print(f"   • Confidence Level: {'✅' if confidence_ok else '❌'} ({avg_confidence:.3f} >= 0.7)")
        print(f"   • ML Score Quality: {'✅' if ml_score_ok else '❌'} ({avg_ml_score:.3f} >= 0.5)")
        print(f"   • Signal Balance: {'✅' if balance_ok else '❌'} ({balanced_signals}/{total_tests} balanced)")

        all_checks_pass = signals_ok and confidence_ok and ml_score_ok and balance_ok

        print(f"\n🏆 OVERALL VALIDATION: {'✅ PASSED' if all_checks_pass else '❌ FAILED'}")

        if all_checks_pass:
            print("   🎉 Quantum Fusion Strategy core functionality validated!")
            print("   🚀 Ready for comprehensive backtesting!")
        else:
            print("   ⚠️ Core functionality needs improvement.")

    else:
        print("❌ No valid test results generated")

    return results

if __name__ == "__main__":
    test_strategy_core_functionality()