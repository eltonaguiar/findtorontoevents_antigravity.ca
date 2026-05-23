"""
Quantum Fusion Strategy - Core Logic Validation
==============================================

Test the core signal generation logic without external dependencies
"""

import pandas as pd
import numpy as np
from quantum_fusion_strategy import QuantumFusionStrategy

def create_test_data():
    """Create test OHLCV data."""

    # Create 200 periods of test data
    dates = pd.date_range('2023-01-01', periods=200, freq='H')

    # Generate realistic price data with some trends and volatility
    np.random.seed(42)
    base_price = 50000

    # Create price series with trend and noise
    trend = np.linspace(0, 0.1, 200)  # Slight upward trend
    noise = np.random.normal(0, 0.02, 200)
    returns = trend + noise

    prices = base_price * np.exp(np.cumsum(returns))

    # Create OHLCV data
    data = []
    for i, price in enumerate(prices):
        high = price * (1 + np.random.uniform(0, 0.015))
        low = price * (1 - np.random.uniform(0, 0.015))
        open_price = prices[i-1] if i > 0 else price
        volume = np.random.randint(1000000, 5000000)

        data.append({
            'open': open_price,
            'high': high,
            'low': low,
            'close': price,
            'volume': volume
        })

    df = pd.DataFrame(data, index=dates)
    return df

def test_core_logic():
    """Test the core signal generation logic."""

    print("🧬 Quantum Fusion Strategy - Core Logic Validation")
    print("=" * 60)

    # Create test data
    data = create_test_data()
    print(f"✅ Created test data: {len(data)} periods")

    # Initialize strategy
    strategy = QuantumFusionStrategy()
    print("✅ Strategy initialized")

    # Test regime detection
    regime = strategy._detect_market_regime(data)
    print(f"✅ Market regime detected: {regime}")

    # Test indicator calculation
    indicators = strategy._calculate_quantum_indicators(data)
    print(f"✅ Calculated {len(indicators)} indicators")

    # Test ML feature generation
    features = strategy._generate_ml_features(data, indicators, regime, '1h')
    print(f"✅ Generated ML features: {features.shape[1]} features")

    # Test signal generation
    signals = strategy.generate_signals(data, 'BTC', '1h')
    print(f"✅ Generated {len(signals)} signals")

    # Analyze signals
    if signals:
        directions = [s.direction for s in signals]
        buy_count = directions.count('BUY')
        sell_count = directions.count('SELL')

        confidences = [s.confidence for s in signals]
        avg_confidence = np.mean(confidences)

        ml_scores = [s.ml_score for s in signals]
        avg_ml_score = np.mean(ml_scores)

        regimes = [s.regime for s in signals]
        unique_regimes = set(regimes)

        print("
📊 Signal Analysis:"        print(f"   • BUY signals: {buy_count}")
        print(f"   • SELL signals: {sell_count}")
        print(f"   • Average confidence: {avg_confidence:.3f}")
        print(f"   • Average ML score: {avg_ml_score:.3f}")
        print(f"   • Regimes detected: {unique_regimes}")

        # Show sample signal
        sample = signals[0]
        print("
📋 Sample Signal:"        print(f"   • Direction: {sample.direction}")
        print(f"   • Confidence: {sample.confidence}")
        print(f"   • Entry Price: {sample.entry_price}")
        print(f"   • Take Profit: {sample.take_profit}")
        print(f"   • Stop Loss: {sample.stop_loss}")
        print(f"   • Regime: {sample.regime}")
        print(f"   • Reason: {sample.reason}")

        # Validation checks
        print("
✅ VALIDATION CHECKS:"        signals_ok = len(signals) > 0
        confidence_ok = avg_confidence >= 0.7
        ml_score_ok = avg_ml_score >= 0.5
        regime_ok = len(unique_regimes) > 0

        print(f"   • Signals generated: {'✅' if signals_ok else '❌'}")
        print(f"   • Confidence ≥ 0.7: {'✅' if confidence_ok else '❌'} ({avg_confidence:.3f})")
        print(f"   • ML score ≥ 0.5: {'✅' if ml_score_ok else '❌'} ({avg_ml_score:.3f})")
        print(f"   • Regime detection: {'✅' if regime_ok else '❌'} ({len(unique_regimes)} regimes)")

        all_checks_pass = signals_ok and confidence_ok and ml_score_ok and regime_ok

        print(f"\n🏆 CORE LOGIC VALIDATION: {'✅ PASSED' if all_checks_pass else '❌ FAILED'}")

        if all_checks_pass:
            print("   🎉 Quantum Fusion core logic validated successfully!")
            print("   🚀 Strategy is ready for comprehensive backtesting!")
        else:
            print("   ⚠️ Core logic needs improvement.")

    else:
        print("❌ No signals generated - core logic issue detected")

    return signals

if __name__ == "__main__":
    test_core_logic()