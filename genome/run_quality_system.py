#!/usr/bin/env python3
"""
Signal Quality System Runner

Run the complete signal quality system:
    python genome/run_quality_system.py [command]

Commands:
    demo      - Run demonstration
    test      - Run unit tests
    generate  - Generate daily picks
    validate  - Validate a specific signal file
"""

import sys
import json
import os
from datetime import datetime

# Ensure genome module is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from genome.quality_engine import SignalQualityEngine
from genome.tp_sl_calculator import TPSLCalculator
from genome.signal_validator import SignalValidator
from genome.picks_generator import PicksGenerator, generate_daily_picks


def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_subheader(title):
    """Print formatted subheader"""
    print(f"\n{'-' * 70}")
    print(f"  {title}")
    print("-" * 70)


def run_demo():
    """Run comprehensive demonstration"""
    print_header("SIGNAL QUALITY SCORING SYSTEM v1.0")
    print("  Hedge Fund Quality Signal Validation for Crypto Trading")
    
    # Sample high-quality signal
    signal = {
        'symbol': 'BTCUSDT',
        'direction': 'LONG',
        'entry_price': 85000.0,
        'strategy_dna': 'combo_ema_rsi_funding_btc',
        'backtest_metrics': {
            'sharpe_ratio': 1.85,
            'sortino_ratio': 2.1,
            'calmar_ratio': 2.5,
            'max_drawdown': 0.12,
            'total_trades': 156,
            'win_rate': 0.68,
            'profit_factor': 2.3
        },
        'current_regime': 'trending_bull',
        'optimal_regimes': ['trending_bull', 'volatile_bull'],
        'regime_performance': {
            'trending_bull': {'sharpe': 2.1, 'win_rate': 0.72},
            'volatile_bull': {'sharpe': 1.5, 'win_rate': 0.65}
        },
        'agreeing_systems': ['alpha_engine', 'mercury2', 'dna_genome', 'kimi'],
        'market_structure': {
            'daily_volume_usd': 35_000_000_000,
            'spread_pct': 0.0005,
            'volatility_24h': 0.045,
            'trading_enabled': True,
            'bid_depth_usd': 5_000_000_000,
            'ask_depth_usd': 5_000_000_000
        }
    }
    
    # 1. Quality Scoring
    print_subheader("STEP 1: MULTI-DIMENSIONAL QUALITY SCORING")
    
    engine = SignalQualityEngine()
    quality = engine.calculate_quality_score(signal)
    quality_dict = engine.to_dict(quality)
    
    print(f"\n  [SIGNAL] {signal['symbol']} {signal['direction']}")
    print(f"  [STRATEGY] {signal['strategy_dna']}")
    print(f"\n  {'-' * 50}")
    print(f"  TOTAL QUALITY SCORE: {quality_dict['total_score']}/100")
    print(f"  GRADE: {quality_dict['grade']}")
    print(f"  VERDICT: {quality_dict['verdict']}")
    print(f"  CONFIDENCE: {quality_dict['confidence']}")
    print(f"  {'-' * 50}")
    
    print(f"\n  Component Scores:")
    print(f"  {'-' * 50}")
    for component, score in quality_dict['components'].items():
        weight = SignalQualityEngine.WEIGHTS[component] * 100
        weighted = score * SignalQualityEngine.WEIGHTS[component]
        bar = '#' * int(score / 5) + '-' * (20 - int(score / 5))
        print(f"  {component:22s}: [{bar}] {score:5.1f} pts -> {weighted:5.2f}")
    
    # 2. Validation
    print_subheader("STEP 2: PRE-TRADE VALIDATION")
    
    validator = SignalValidator()
    validation = validator.validate(signal)
    
    print(f"\n  Status: {'[OK] APPROVED' if validation.approved else '[FAIL] REJECTED'}")
    print(f"\n  Validation Checks:")
    for check, passed in validation.checks.items():
        status = "[OK]" if passed else "[FAIL]"
        print(f"    {status} {check}")
    
    if validation.warnings:
        print(f"\n  [WARN] Warnings: {', '.join(validation.warnings)}")
    
    # 3. TP/SL Calculation
    print_subheader("STEP 3: OPTIMAL TP/SL CALCULATION")
    
    calculator = TPSLCalculator()
    strategy_dna = {
        'risk_profile': 'medium',
        'win_rate': 0.68,
        'avg_win_pct': 8.5,
        'avg_loss_pct': 3.2
    }
    
    levels = calculator.calculate_levels(
        signal['symbol'],
        signal['entry_price'],
        signal['direction'],
        strategy_dna
    )
    
    entry = signal['entry_price']
    risk_amount = abs(entry - levels['stop_loss'])
    reward_amount = abs(levels['take_profit'] - entry)
    
    print(f"\n  [ENTRY]   Entry Price:    ${entry:>12,.2f}")
    print(f"  [TP]      Take Profit:    ${levels['take_profit']:>12,.2f}  (+{(reward_amount/entry*100):.2f}%)")
    print(f"  [SL]      Stop Loss:      ${levels['stop_loss']:>12,.2f}  (-{(risk_amount/entry*100):.2f}%)")
    print(f"  [R:R]     Risk:Reward:    1:{levels['risk_reward']}")
    print(f"  [SIZE]    Position Size:  {levels['position_size_pct']}%")
    print(f"  [KELLY]   Kelly Fraction: {levels['kelly_fraction']:.2%}")
    
    # 4. Trading Summary
    print_subheader("STEP 4: TRADING SUMMARY")
    
    print(f"\n  Signal ID:       BTC_LONG_20260302_001")
    print(f"  Quality:         {quality_dict['grade']} ({quality_dict['total_score']:.1f}/100)")
    print(f"  Verdict:         {quality_dict['verdict']}")
    print(f"  Risk per Unit:   ${risk_amount:,.2f}")
    print(f"  Reward per Unit: ${reward_amount:,.2f}")
    print(f"  Expected Value:  +{((reward_amount/risk_amount)*0.68 - 0.32)*100:.1f}% per trade")
    
    # 5. Grade Reference
    print_subheader("GRADE REFERENCE")
    print("""
    Grade    Score      Status              Action
    -----------------------------------------------------
    A+       95-100     [EXCEPTIONAL]       Full size
    A        90-94      [EXCELLENT]         Full size
    A-       85-89      [VERY GOOD]         Standard size
    B+       80-84      [GOOD]              Standard size
    B        75-79      [ABOVE AVG]         Standard size
    B-       70-74      [ACCEPTABLE]        Reduced size
    C+       65-69      [MARGINAL]          Paper only
    C        60-64      [WEAK]              Paper only
    D-F      < 60       [POOR]              Reject
    """)
    
    print_header("DEMONSTRATION COMPLETE")
    print("\n  Files created:")
    print("    - genome/quality_engine.py       - Core quality scoring")
    print("    - genome/tp_sl_calculator.py     - TP/SL calculations")
    print("    - genome/signal_validator.py     - Pre-trade validation")
    print("    - genome/picks_generator.py      - Picks orchestrator")
    print("    - genome/active_picks.json       - Sample output")
    print("    - genome/grades_explained.md     - Documentation")
    print("\n  Run 'python genome/run_quality_system.py generate' to create picks")
    print("=" * 70 + "\n")


def run_tests():
    """Run unit tests"""
    print_header("RUNNING UNIT TESTS")
    
    import unittest
    from genome.test_quality_system import (
        TestSignalQualityEngine,
        TestTPSLCalculator,
        TestSignalValidator,
        TestPicksGenerator,
        TestIntegration
    )
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestSignalQualityEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestTPSLCalculator))
    suite.addTests(loader.loadTestsFromTestCase(TestSignalValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestPicksGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n[OK] All tests passed!")
    else:
        print("\n[FAIL] Some tests failed!")
    
    return result.wasSuccessful()


def run_generate():
    """Generate daily picks"""
    result = generate_daily_picks()
    return result


def run_validate(filename):
    """Validate a signal from file"""
    print_header(f"VALIDATING SIGNAL: {filename}")
    
    if not os.path.exists(filename):
        print(f"[ERROR] File not found: {filename}")
        return False
    
    try:
        with open(filename, 'r') as f:
            signal = json.load(f)
        
        # Quality scoring
        engine = SignalQualityEngine()
        quality = engine.calculate_quality_score(signal)
        quality_dict = engine.to_dict(quality)
        
        print(f"\n  Signal: {signal.get('symbol', 'Unknown')} {signal.get('direction', 'Unknown')}")
        print(f"  Quality Score: {quality_dict['total_score']}/100")
        print(f"  Grade: {quality_dict['grade']}")
        print(f"  Verdict: {quality_dict['verdict']}")
        print(f"  Tradeable: {'[YES]' if quality_dict['tradeable'] else '[NO]'}")
        
        # Validation
        validator = SignalValidator()
        validation = validator.validate(signal)
        
        print(f"\n  Validation: {'[OK] APPROVED' if validation.approved else '[FAIL] REJECTED'}")
        if validation.failures:
            print(f"  Failures: {', '.join(validation.failures)}")
        
        return validation.approved and quality_dict['tradeable']
        
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        run_demo()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'demo':
        run_demo()
    elif command == 'test':
        success = run_tests()
        sys.exit(0 if success else 1)
    elif command == 'generate':
        run_generate()
    elif command == 'validate':
        if len(sys.argv) < 3:
            print("Usage: python run_quality_system.py validate <signal_file.json>")
            sys.exit(1)
        run_validate(sys.argv[2])
    else:
        print(f"Unknown command: {command}")
        print("\nUsage: python run_quality_system.py [command]")
        print("\nCommands:")
        print("  demo      - Run demonstration")
        print("  test      - Run unit tests")
        print("  generate  - Generate daily picks")
        print("  validate  - Validate a signal file")
        sys.exit(1)


if __name__ == '__main__':
    main()
