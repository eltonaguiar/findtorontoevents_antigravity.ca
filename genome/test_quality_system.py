"""
Unit Tests for Signal Quality Scoring System

Run with: python -m pytest genome/test_quality_system.py -v
Or: python genome/test_quality_system.py
"""

import unittest
import json
import os
from datetime import datetime

from quality_engine import SignalQualityEngine, QualityScore, SignalGrade, SignalVerdict
from tp_sl_calculator import TPSLCalculator, RiskProfile
from signal_validator import SignalValidator, ValidationStatus
from picks_generator import PicksGenerator, TradingPick


class TestSignalQualityEngine(unittest.TestCase):
    """Test cases for SignalQualityEngine"""
    
    def setUp(self):
        self.engine = SignalQualityEngine()
        self.base_signal = {
            'symbol': 'BTCUSDT',
            'direction': 'LONG',
            'backtest_metrics': {
                'sharpe_ratio': 1.5,
                'sortino_ratio': 1.8,
                'calmar_ratio': 2.0,
                'max_drawdown': 0.12,
                'total_trades': 100,
                'win_rate': 0.60,
                'profit_factor': 1.8
            },
            'current_regime': 'trending_bull',
            'optimal_regimes': ['trending_bull'],
            'regime_performance': {
                'trending_bull': {'sharpe': 1.7}
            },
            'agreeing_systems': ['alpha_engine', 'mercury2', 'kimi'],
            'market_structure': {
                'daily_volume_usd': 35_000_000_000,
                'spread_pct': 0.0005,
                'volatility_24h': 0.045,
                'trading_enabled': True,
                'bid_depth_usd': 5_000_000_000,
                'ask_depth_usd': 5_000_000_000
            }
        }
    
    def test_basic_scoring(self):
        """Test basic quality score calculation"""
        result = self.engine.calculate_quality_score(self.base_signal)
        
        self.assertIsInstance(result, QualityScore)
        self.assertGreater(result.total_score, 0)
        self.assertLessEqual(result.total_score, 100)
        self.assertIn(result.grade, [g.value for g in SignalGrade])
        self.assertIn(result.verdict, [v.value for v in SignalVerdict])
    
    def test_backtest_validity_scoring(self):
        """Test backtest validity component scoring"""
        # Test Sharpe > 2.0
        signal = self.base_signal.copy()
        signal['backtest_metrics'] = {'sharpe_ratio': 2.5}
        score = self.engine._score_backtest_metrics(signal)
        self.assertEqual(score, 25.0)
        
        # Test Sharpe 1.5-2.0
        signal['backtest_metrics'] = {'sharpe_ratio': 1.7}
        score = self.engine._score_backtest_metrics(signal)
        self.assertEqual(score, 22.0)
        
        # Test Sharpe < 0.5
        signal['backtest_metrics'] = {'sharpe_ratio': 0.3}
        score = self.engine._score_backtest_metrics(signal)
        self.assertEqual(score, 0.0)
    
    def test_statistical_significance(self):
        """Test sample size scoring"""
        # Test > 500 trades
        signal = {'backtest_metrics': {'total_trades': 600}}
        score = self.engine._score_sample_size(signal)
        self.assertEqual(score, 20.0)
        
        # Test < 20 trades
        signal['backtest_metrics'] = {'total_trades': 10}
        score = self.engine._score_sample_size(signal)
        self.assertEqual(score, 3.0)
    
    def test_regime_alignment(self):
        """Test regime alignment scoring"""
        # Optimal regime
        score = self.engine._score_regime_fit(self.base_signal)
        self.assertGreaterEqual(score, 11.0)
        
        # Non-optimal regime
        signal = self.base_signal.copy()
        signal['current_regime'] = 'ranging'
        score = self.engine._score_regime_fit(signal)
        self.assertLess(score, 11.0)
    
    def test_consensus_strength(self):
        """Test multi-system consensus scoring"""
        # 5 systems
        signal = {'agreeing_systems': ['a', 'b', 'c', 'd', 'e']}
        score = self.engine._score_consensus(signal)
        self.assertEqual(score, 10.0)
        
        # 0 systems
        signal['agreeing_systems'] = []
        score = self.engine._score_consensus(signal)
        self.assertEqual(score, 0.0)
    
    def test_grade_conversion(self):
        """Test score to grade conversion"""
        self.assertEqual(self.engine._score_to_grade(95), 'A+')
        self.assertEqual(self.engine._score_to_grade(90), 'A')
        self.assertEqual(self.engine._score_to_grade(85), 'A-')
        self.assertEqual(self.engine._score_to_grade(80), 'B+')
        self.assertEqual(self.engine._score_to_grade(75), 'B')
        self.assertEqual(self.engine._score_to_grade(70), 'B-')
        self.assertEqual(self.engine._score_to_grade(65), 'C+')
        self.assertEqual(self.engine._score_to_grade(50), 'D')
        self.assertEqual(self.engine._score_to_grade(30), 'F')
    
    def test_verdict_conversion(self):
        """Test score to verdict conversion"""
        signal = {'direction': 'LONG'}
        
        self.assertEqual(self.engine._score_to_verdict(95, signal), 'STRONG_BUY')
        self.assertEqual(self.engine._score_to_verdict(85, signal), 'BUY')
        self.assertEqual(self.engine._score_to_verdict(75, signal), 'MODERATE_BUY')
        
        signal['direction'] = 'SHORT'
        self.assertEqual(self.engine._score_to_verdict(95, signal), 'STRONG_SELL')
        self.assertEqual(self.engine._score_to_verdict(85, signal), 'SELL')
    
    def test_tradeability(self):
        """Test tradeability checks"""
        high_score = QualityScore(
            total_score=85, components={}, grade='A-', verdict='BUY',
            confidence=0.8, timestamp=''
        )
        low_score = QualityScore(
            total_score=60, components={}, grade='C', verdict='HOLD',
            confidence=0.5, timestamp=''
        )
        
        self.assertTrue(self.engine.is_tradeable(high_score))
        self.assertFalse(self.engine.is_tradeable(low_score))


class TestTPSLCalculator(unittest.TestCase):
    """Test cases for TPSLCalculator"""
    
    def setUp(self):
        self.calculator = TPSLCalculator()
        self.base_dna = {
            'risk_profile': 'medium',
            'win_rate': 0.60,
            'avg_win_pct': 8.0,
            'avg_loss_pct': 4.0
        }
    
    def test_long_calculation(self):
        """Test LONG position TP/SL calculation"""
        result = self.calculator.calculate_levels(
            symbol='BTCUSDT',
            entry_price=85000.0,
            direction='LONG',
            strategy_dna=self.base_dna
        )
        
        self.assertIn('take_profit', result)
        self.assertIn('stop_loss', result)
        self.assertIn('risk_reward', result)
        self.assertIn('position_size_pct', result)
        self.assertIn('confidence', result)
        
        # LONG: TP > Entry > SL
        self.assertGreater(result['take_profit'], 85000.0)
        self.assertLess(result['stop_loss'], 85000.0)
    
    def test_short_calculation(self):
        """Test SHORT position TP/SL calculation"""
        result = self.calculator.calculate_levels(
            symbol='BTCUSDT',
            entry_price=85000.0,
            direction='SHORT',
            strategy_dna=self.base_dna
        )
        
        # SHORT: TP < Entry < SL
        self.assertLess(result['take_profit'], 85000.0)
        self.assertGreater(result['stop_loss'], 85000.0)
    
    def test_kelly_calculation(self):
        """Test Kelly criterion calculation"""
        kelly = self.calculator._calculate_kelly(
            win_rate=0.60,
            avg_win=10.0,
            avg_loss=5.0
        )
        
        # Kelly should be positive and reasonable
        self.assertGreater(kelly, 0)
        self.assertLessEqual(kelly, 0.20)  # Capped at 20%
    
    def test_risk_profile_multipliers(self):
        """Test different risk profiles"""
        conservative = {'risk_profile': 'conservative', 'win_rate': 0.6}
        aggressive = {'risk_profile': 'aggressive', 'win_rate': 0.6}
        
        result_cons = self.calculator.calculate_levels(
            'BTCUSDT', 85000.0, 'LONG', conservative
        )
        result_agg = self.calculator.calculate_levels(
            'BTCUSDT', 85000.0, 'LONG', aggressive
        )
        
        # Conservative should have tighter stops
        cons_risk = 85000.0 - result_cons['stop_loss']
        agg_risk = 85000.0 - result_agg['stop_loss']
        self.assertLess(cons_risk, agg_risk)
    
    def test_trailing_stop(self):
        """Test trailing stop calculation"""
        # LONG position, profit activated
        trailing = self.calculator.calculate_trailing_stop(
            entry_price=85000.0,
            current_price=90000.0,  # ~5.9% profit
            direction='LONG',
            activation_pct=3.0,
            trail_pct=2.0
        )
        self.assertIsNotNone(trailing)
        self.assertLess(trailing, 90000.0)
        
        # Not yet activated
        trailing = self.calculator.calculate_trailing_stop(
            entry_price=85000.0,
            current_price=86000.0,  # ~1.2% profit
            direction='LONG',
            activation_pct=3.0
        )
        self.assertIsNone(trailing)


class TestSignalValidator(unittest.TestCase):
    """Test cases for SignalValidator"""
    
    def setUp(self):
        self.validator = SignalValidator()
        self.base_signal = {
            'symbol': 'BTCUSDT',
            'direction': 'LONG',
            'strategy_dna': 'test_strategy',
            'backtest_metrics': {
                'total_trades': 100,
                'backtest_days': 365,
                'win_rate': 0.60
            },
            'market_structure': {
                'daily_volume_usd': 35_000_000_000,
                'spread_pct': 0.0005,
                'volatility_24h': 0.045,
                'trading_enabled': True,
                'bid_depth_usd': 5_000_000_000,
                'ask_depth_usd': 5_000_000_000
            }
        }
    
    def test_valid_signal(self):
        """Test validation of valid signal"""
        result = self.validator.validate(self.base_signal)
        
        self.assertTrue(result.approved)
        self.assertEqual(result.status, ValidationStatus.APPROVED.value)
        self.assertEqual(len(result.failures), 0)
    
    def test_insufficient_backtest(self):
        """Test rejection of insufficient backtest data"""
        signal = self.base_signal.copy()
        signal['backtest_metrics'] = {
            'total_trades': 10,  # Too few
            'win_rate': 0.60
        }
        
        result = self.validator.validate(signal)
        self.assertFalse(result.approved)
        self.assertIn('sufficient_backtest_data', result.failures)
    
    def test_low_liquidity(self):
        """Test rejection of low liquidity"""
        signal = self.base_signal.copy()
        signal['market_structure'] = {
            'daily_volume_usd': 100_000,  # Too low
            'spread_pct': 0.0005,
            'trading_enabled': True
        }
        
        result = self.validator.validate(signal)
        self.assertFalse(result.approved)
        self.assertIn('liquidity_sufficient', result.failures)
    
    def test_signal_cooldown(self):
        """Test signal cooldown enforcement"""
        # First signal should be approved
        result1 = self.validator.validate(self.base_signal)
        self.assertTrue(result1.approved)
        
        # Identical signal should be rejected (cooldown)
        result2 = self.validator.validate(self.base_signal)
        self.assertFalse(result2.approved)
        self.assertIn('no_recent_similar_signal', result2.failures)
        self.assertIsNotNone(result2.cooldown_remaining)
    
    def test_blacklist_check(self):
        """Test blacklisted symbols"""
        signal = self.base_signal.copy()
        signal['symbol'] = 'SHIBUSDT'
        
        result = self.validator.validate(signal)
        self.assertFalse(result.approved)
        self.assertIn('not_blacklisted', result.failures)


class TestPicksGenerator(unittest.TestCase):
    """Test cases for PicksGenerator"""
    
    def setUp(self):
        self.generator = PicksGenerator()
    
    def test_diversification(self):
        """Test pick diversification"""
        candidates = [
            {'symbol': 'BTCUSDT', 'direction': 'LONG', 'quality': {'total_score': 85}},
            {'symbol': 'BTCUSDT', 'direction': 'LONG', 'quality': {'total_score': 84}},
            {'symbol': 'BTCUSDT', 'direction': 'LONG', 'quality': {'total_score': 83}},
            {'symbol': 'ETHUSDT', 'direction': 'LONG', 'quality': {'total_score': 82}},
            {'symbol': 'SOLUSDT', 'direction': 'LONG', 'quality': {'total_score': 81}},
        ]
        
        picks = self.generator._diversify_picks(candidates)
        
        # Should limit BTC to 2 picks
        btc_count = sum(1 for p in picks if p['symbol'] == 'BTCUSDT')
        self.assertLessEqual(btc_count, 2)
    
    def test_pick_creation(self):
        """Test TradingPick creation"""
        pick_data = {
            'symbol': 'BTCUSDT',
            'direction': 'LONG',
            'entry_price': 85000.0,
            'strategy_dna': 'test',
            'quality': {'total_score': 85, 'grade': 'A-', 'verdict': 'BUY'},
            'backtest_metrics': {
                'sharpe_ratio': 1.5,
                'win_rate': 0.6,
                'total_trades': 100
            },
            'current_regime': 'trending_bull',
            'agreeing_systems': ['alpha'],
            'validation': {'checks': {}, 'warnings': []},
            'market_structure': {}
        }
        
        pick = self.generator._create_trading_pick(pick_data, 1)
        
        self.assertIsInstance(pick, TradingPick)
        self.assertEqual(pick.symbol, 'BTCUSDT')
        self.assertEqual(pick.quality_score, 85)
        self.assertIsNotNone(pick.take_profit)
        self.assertIsNotNone(pick.stop_loss)
    
    def test_output_format(self):
        """Test output JSON format"""
        pick = TradingPick(
            id='test_001',
            symbol='BTCUSDT',
            direction='LONG',
            entry_price=85000.0,
            take_profit=93500.0,
            stop_loss=80750.0,
            risk_reward=2.0,
            strategy_dna='test',
            quality_score=85.0,
            grade='A-',
            verdict='BUY',
            confidence=0.8,
            position_size_pct=3.0,
            expected_return_pct=10.0,
            max_risk_pct=5.0,
            backtest_metrics={},
            regime='trending',
            consensus_count=2,
            agreeing_systems=['a', 'b'],
            validation_checks={},
            timestamp='2026-03-02T10:00:00Z'
        )
        
        pick_dict = self.generator._pick_to_dict(pick)
        
        required_fields = [
            'id', 'symbol', 'direction', 'entry_price', 'take_profit',
            'stop_loss', 'quality_score', 'grade', 'verdict', 'confidence'
        ]
        for field in required_fields:
            self.assertIn(field, pick_dict)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system"""
    
    def test_full_pipeline(self):
        """Test complete signal processing pipeline"""
        # Create sample signal
        signal = {
            'symbol': 'BTCUSDT',
            'direction': 'LONG',
            'entry_price': 85000.0,
            'strategy_dna': 'combo_test_btc',
            'backtest_metrics': {
                'sharpe_ratio': 1.75,
                'sortino_ratio': 2.0,
                'calmar_ratio': 2.2,
                'max_drawdown': 0.12,
                'total_trades': 156,
                'win_rate': 0.68,
                'profit_factor': 2.1
            },
            'current_regime': 'trending_bull',
            'optimal_regimes': ['trending_bull'],
            'regime_performance': {
                'trending_bull': {'sharpe': 1.9}
            },
            'agreeing_systems': ['alpha_engine', 'mercury2', 'kimi'],
            'market_structure': {
                'daily_volume_usd': 35_000_000_000,
                'spread_pct': 0.0005,
                'volatility_24h': 0.045,
                'trading_enabled': True
            }
        }
        
        # Step 1: Quality scoring
        quality_engine = SignalQualityEngine()
        quality = quality_engine.calculate_quality_score(signal)
        
        self.assertGreaterEqual(quality.total_score, 70)  # Should be tradeable
        self.assertIn(quality.grade, ['A+', 'A', 'A-', 'B+', 'B', 'B-'])
        
        # Step 2: Validation
        validator = SignalValidator()
        validation = validator.validate(signal)
        
        # Step 3: TP/SL calculation
        tpsl_calc = TPSLCalculator()
        strategy_dna = {
            'risk_profile': 'medium',
            'win_rate': 0.68,
            'avg_win_pct': 8.5,
            'avg_loss_pct': 4.0
        }
        levels = tpsl_calc.calculate_levels(
            signal['symbol'],
            signal['entry_price'],
            signal['direction'],
            strategy_dna
        )
        
        # Verify consistency
        self.assertGreater(levels['take_profit'], signal['entry_price'])
        self.assertLess(levels['stop_loss'], signal['entry_price'])
        self.assertGreaterEqual(levels['risk_reward'], 1.5)


def run_demo():
    """Run a demonstration of the quality system"""
    print("\n" + "=" * 70)
    print("SIGNAL QUALITY SCORING SYSTEM - DEMONSTRATION")
    print("=" * 70)
    
    # Test signal
    test_signal = {
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
            'trading_enabled': True
        }
    }
    
    # 1. Quality Scoring
    print("\n📊 STEP 1: Quality Scoring")
    print("-" * 70)
    engine = SignalQualityEngine()
    quality = engine.calculate_quality_score(test_signal)
    quality_dict = engine.to_dict(quality)
    
    print(f"Signal: {test_signal['symbol']} {test_signal['direction']}")
    print(f"Total Score: {quality_dict['total_score']}/100")
    print(f"Grade: {quality_dict['grade']}")
    print(f"Verdict: {quality_dict['verdict']}")
    print(f"Confidence: {quality_dict['confidence']}")
    print(f"Tradeable: {quality_dict['tradeable']}")
    print("\nComponent Breakdown:")
    for component, score in quality_dict['components'].items():
        weight = SignalQualityEngine.WEIGHTS[component] * 100
        weighted = score * SignalQualityEngine.WEIGHTS[component]
        print(f"  • {component:25s}: {score:5.1f} pts × {weight:4.0f}% = {weighted:5.2f}")
    
    # 2. Signal Validation
    print("\n📋 STEP 2: Signal Validation")
    print("-" * 70)
    validator = SignalValidator()
    validation = validator.validate(test_signal)
    
    print(f"Status: {validation.status}")
    print(f"Approved: {validation.approved}")
    print("\nValidation Checks:")
    for check, passed in validation.checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check}")
    
    # 3. TP/SL Calculation
    print("\n🎯 STEP 3: TP/SL Calculation")
    print("-" * 70)
    calculator = TPSLCalculator()
    strategy_dna = {
        'risk_profile': 'medium',
        'win_rate': 0.68,
        'avg_win_pct': 8.5,
        'avg_loss_pct': 3.2
    }
    levels = calculator.calculate_levels(
        test_signal['symbol'],
        test_signal['entry_price'],
        test_signal['direction'],
        strategy_dna
    )
    
    entry = test_signal['entry_price']
    print(f"Entry Price:     ${entry:,.2f}")
    print(f"Take Profit:     ${levels['take_profit']:,.2f} (+{((levels['take_profit']/entry-1)*100):.1f}%)")
    print(f"Stop Loss:       ${levels['stop_loss']:,.2f} ({((levels['stop_loss']/entry-1)*100):.1f}%)")
    print(f"Risk:Reward:     1:{levels['risk_reward']}")
    print(f"Position Size:   {levels['position_size_pct']}%")
    print(f"Kelly Fraction:  {levels['kelly_fraction']}")
    print(f"Confidence:      {levels['confidence']}")
    
    # 4. Summary
    print("\n📈 STEP 4: Final Summary")
    print("-" * 70)
    risk_amount = abs(entry - levels['stop_loss'])
    reward_amount = abs(levels['take_profit'] - entry)
    
    print(f"Signal ID:       BTC_LONG_001")
    print(f"Quality Grade:   {quality_dict['grade']} ({quality_dict['total_score']:.1f}/100)")
    print(f"Verdict:         {quality_dict['verdict']}")
    print(f"Risk Amount:     ${risk_amount:,.2f} per unit")
    print(f"Reward Amount:   ${reward_amount:,.2f} per unit")
    print(f"Expected Value:  +{((reward_amount/risk_amount)*0.68 - 0.32)*100:.1f}% per trade")
    print("=" * 70)
    
    # Save demo result
    demo_result = {
        'signal': test_signal,
        'quality': quality_dict,
        'validation': {
            'approved': validation.approved,
            'checks': validation.checks
        },
        'levels': levels
    }
    
    os.makedirs('genome', exist_ok=True)
    with open('genome/demo_result.json', 'w') as f:
        json.dump(demo_result, f, indent=2)
    
    print("\n✓ Demo result saved to genome/demo_result.json")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        # Run unit tests
        unittest.main(argv=[''], verbosity=2, exit=False)
    else:
        # Run demo
        run_demo()
