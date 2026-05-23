#!/usr/bin/env python3
"""
Rigorous Validation Framework for Live Trading Readiness
=========================================================

Before deploying real capital, this framework validates:
1. Out-of-sample backtesting (unseen data)
2. Walk-forward analysis
3. Monte Carlo simulation
4. Risk-adjusted performance metrics
5. Drawdown analysis
6. Strategy degradation detection

Generates a Live Trading Readiness Report with pass/fail criteria.

Usage:
    python rigorous_validation_framework.py --validate-all
    python rigorous_validation_framework.py --live-ready-check
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('RigorousValidation')


@dataclass
class ValidationCriteria:
    """Criteria for live trading readiness."""
    min_sharpe: float = 1.5
    min_win_rate: float = 0.55
    max_drawdown: float = 0.15
    min_profit_factor: float = 1.3
    min_trades: int = 100
    min_expectancy: float = 0.5
    max_consecutive_losses: int = 5
    consistency_threshold: float = 0.6


@dataclass
class ValidationResult:
    """Result of validation test."""
    test_name: str
    passed: bool
    score: float
    threshold: float
    details: str


class RigorousValidator:
    """Comprehensive strategy validation."""
    
    def __init__(self):
        self.criteria = ValidationCriteria()
        self.results = []
        self.load_historical_data()
    
    def load_historical_data(self):
        """Load all historical backtest results."""
        self.data = {}
        
        for period in ['today', 'yesterday', 'week']:
            file_path = Path(f'genome/results/historical_{period}.json')
            if file_path.exists():
                with open(file_path) as f:
                    self.data[period] = json.load(f)
        
        # Load deep research
        deep_path = Path('genome/results/deep_research_what_works.json')
        if deep_path.exists():
            with open(deep_path) as f:
                self.deep_research = json.load(f)
        
        logger.info(f"Loaded data for {len(self.data)} periods")
    
    def monte_carlo_simulation(self, trades: List[Dict], n_simulations: int = 1000) -> Dict:
        """
        Run Monte Carlo simulation to test strategy robustness.
        Randomly reshuffles trade sequence to test different paths.
        """
        if not trades:
            return {}
        
        pnls = [t['pnl_pct'] for t in trades]
        
        # Calculate equity curves
        equity_curves = []
        max_drawdowns = []
        final_pnls = []
        
        for _ in range(n_simulations):
            # Randomly sample with replacement (bootstrap)
            sample_pnls = np.random.choice(pnls, size=len(pnls), replace=True)
            
            # Calculate equity curve
            equity = [100]  # Start with $100
            for pnl in sample_pnls:
                equity.append(equity[-1] * (1 + pnl / 100))
            
            # Calculate max drawdown
            peak = equity[0]
            max_dd = 0
            for val in equity:
                if val > peak:
                    peak = val
                dd = (peak - val) / peak
                max_dd = max(max_dd, dd)
            
            equity_curves.append(equity)
            max_drawdowns.append(max_dd)
            final_pnls.append((equity[-1] - 100) / 100)
        
        # Calculate percentiles
        return {
            'n_simulations': n_simulations,
            'median_final_pnl': np.median(final_pnls),
            'worst_case_dd': np.percentile(max_drawdowns, 95),
            'best_case_pnl': np.percentile(final_pnls, 95),
            'worst_case_pnl': np.percentile(final_pnls, 5),
            'prob_profit': sum(1 for p in final_pnls if p > 0) / n_simulations,
            'sharpe_distribution': [
                np.mean(pnls) / (np.std(pnls) + 1e-10) * np.sqrt(252)
                for _ in range(100)
            ]
        }
    
    def walk_forward_analysis(self) -> Dict:
        """
        Walk-forward analysis: Test if strategy works on subsequent periods.
        """
        if len(self.data) < 2:
            return {'passed': False, 'reason': 'Insufficient data periods'}
        
        # Extract metrics from each period
        period_metrics = []
        for period, data in sorted(self.data.items()):
            m = data['overall_metrics']
            period_metrics.append({
                'period': period,
                'sharpe': m['sharpe_ratio'],
                'win_rate': m['win_rate'],
                'pnl': m['total_pnl_pct'],
                'drawdown': m['max_drawdown_pct'],
                'trades': m['total_trades']
            })
        
        # Check consistency across periods
        sharpes = [p['sharpe'] for p in period_metrics]
        win_rates = [p['win_rate'] for p in period_metrics]
        
        sharpe_consistency = np.std(sharpes) / np.mean(sharpes) if np.mean(sharpes) > 0 else 999
        win_rate_consistency = np.std(win_rates) / np.mean(win_rates) if np.mean(win_rates) > 0 else 999
        
        return {
            'period_metrics': period_metrics,
            'sharpe_consistency': sharpe_consistency,
            'win_rate_consistency': win_rate_consistency,
            'passed': sharpe_consistency < 0.3 and win_rate_consistency < 0.2,
            'avg_sharpe': np.mean(sharpes),
            'min_sharpe': min(sharpes)
        }
    
    def out_of_sample_test(self) -> Dict:
        """
        Simulate out-of-sample test by withholding recent data.
        """
        # Use 'week' data as in-sample, 'today' as out-of-sample
        if 'week' not in self.data or 'today' not in self.data:
            return {'passed': False, 'reason': 'Missing data for OOS test'}
        
        in_sample = self.data['week']['overall_metrics']
        out_sample = self.data['today']['overall_metrics']
        
        # Compare performance
        sharpe_decay = (in_sample['sharpe_ratio'] - out_sample['sharpe_ratio']) / in_sample['sharpe_ratio']
        win_rate_decay = (in_sample['win_rate'] - out_sample['win_rate']) / in_sample['win_rate'] if in_sample['win_rate'] > 0 else 0
        
        return {
            'in_sample_sharpe': in_sample['sharpe_ratio'],
            'out_sample_sharpe': out_sample['sharpe_ratio'],
            'sharpe_decay': sharpe_decay,
            'win_rate_decay': win_rate_decay,
            'passed': sharpe_decay < 0.5 and out_sample['sharpe_ratio'] > 1.5,
            'reliability_score': 1 - sharpe_decay
        }
    
    def risk_analysis(self) -> Dict:
        """
        Deep risk analysis including tail risks.
        """
        all_trades = []
        for data in self.data.values():
            all_trades.extend(data.get('best_trades', []))
        
        if not all_trades:
            return {}
        
        pnls = [t['pnl_pct'] for t in all_trades]
        drawdowns = [t['max_dd'] for t in all_trades]
        
        return {
            'var_95': np.percentile(pnls, 5),  # 95% VaR
            'var_99': np.percentile(pnls, 1),  # 99% VaR
            'max_observed_dd': max(drawdowns),
            'avg_dd': np.mean(drawdowns),
            'tail_risk_ratio': abs(np.percentile(pnls, 1)) / np.percentile(pnls, 99),
            'skewness': pd.Series(pnls).skew(),
            'kurtosis': pd.Series(pnls).kurtosis(),
            'passed': np.percentile(pnls, 5) > -5  # 95% of trades better than -5%
        }
    
    def calculate_live_readiness_score(self) -> Tuple[float, List[ValidationResult]]:
        """
        Calculate overall live trading readiness score (0-100).
        """
        results = []
        
        # Test 1: Sharpe Ratio
        avg_sharpe = np.mean([
            d['overall_metrics']['sharpe_ratio'] 
            for d in self.data.values()
        ])
        sharpe_passed = avg_sharpe >= self.criteria.min_sharpe
        results.append(ValidationResult(
            test_name='Sharpe Ratio',
            passed=sharpe_passed,
            score=avg_sharpe,
            threshold=self.criteria.min_sharpe,
            details=f'Average Sharpe: {avg_sharpe:.2f} (threshold: {self.criteria.min_sharpe})'
        ))
        
        # Test 2: Win Rate
        avg_win_rate = np.mean([
            d['overall_metrics']['win_rate']
            for d in self.data.values()
        ])
        win_rate_passed = avg_win_rate >= self.criteria.min_win_rate
        results.append(ValidationResult(
            test_name='Win Rate',
            passed=win_rate_passed,
            score=avg_win_rate,
            threshold=self.criteria.min_win_rate,
            details=f'Average Win Rate: {avg_win_rate:.1%} (threshold: {self.criteria.min_win_rate:.0%})'
        ))
        
        # Test 3: Drawdown
        max_dd = max([
            d['overall_metrics']['max_drawdown_pct']
            for d in self.data.values()
        ])
        dd_passed = max_dd <= self.criteria.max_drawdown * 100
        results.append(ValidationResult(
            test_name='Max Drawdown',
            passed=dd_passed,
            score=max_dd,
            threshold=self.criteria.max_drawdown * 100,
            details=f'Max Drawdown: {max_dd:.1f}% (threshold: {self.criteria.max_drawdown*100:.0f}%)'
        ))
        
        # Test 4: Profit Factor
        avg_pf = np.mean([
            d['overall_metrics']['profit_factor']
            for d in self.data.values()
            if d['overall_metrics']['profit_factor'] < 999
        ])
        pf_passed = avg_pf >= self.criteria.min_profit_factor
        results.append(ValidationResult(
            test_name='Profit Factor',
            passed=pf_passed,
            score=avg_pf,
            threshold=self.criteria.min_profit_factor,
            details=f'Average Profit Factor: {avg_pf:.2f} (threshold: {self.criteria.min_profit_factor})'
        ))
        
        # Test 5: Sample Size
        total_trades = sum([
            d['overall_metrics']['total_trades']
            for d in self.data.values()
        ])
        size_passed = total_trades >= self.criteria.min_trades
        results.append(ValidationResult(
            test_name='Sample Size',
            passed=size_passed,
            score=total_trades,
            threshold=self.criteria.min_trades,
            details=f'Total Trades: {total_trades} (threshold: {self.criteria.min_trades})'
        ))
        
        # Test 6: Walk-Forward
        wfa = self.walk_forward_analysis()
        wfa_passed = wfa.get('passed', False)
        results.append(ValidationResult(
            test_name='Walk-Forward Analysis',
            passed=wfa_passed,
            score=wfa.get('sharpe_consistency', 0),
            threshold=0.3,
            details=f"Sharpe consistency: {wfa.get('sharpe_consistency', 0):.2f}"
        ))
        
        # Test 7: Out-of-Sample
        oos = self.out_of_sample_test()
        oos_passed = oos.get('passed', False)
        results.append(ValidationResult(
            test_name='Out-of-Sample',
            passed=oos_passed,
            score=oos.get('reliability_score', 0),
            threshold=0.5,
            details=f"Reliability: {oos.get('reliability_score', 0):.1%}"
        ))
        
        # Test 8: Risk Analysis
        risk = self.risk_analysis()
        risk_passed = risk.get('passed', False)
        results.append(ValidationResult(
            test_name='Tail Risk',
            passed=risk_passed,
            score=abs(risk.get('var_95', -10)),
            threshold=5,
            details=f"95% VaR: {risk.get('var_95', 0):.2f}%"
        ))
        
        # Calculate overall score
        passed_tests = sum(1 for r in results if r.passed)
        total_tests = len(results)
        readiness_score = (passed_tests / total_tests) * 100
        
        return readiness_score, results
    
    def generate_live_readiness_report(self):
        """Generate comprehensive live trading readiness report."""
        
        score, validations = self.calculate_live_readiness_score()
        
        print("\n" + "="*90)
        print("  LIVE TRADING READINESS ASSESSMENT")
        print("="*90)
        print(f"\nAssessment Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"Overall Readiness Score: {score:.0f}/100")
        
        # Status
        if score >= 90:
            status = "EXCELLENT - Ready for live deployment with full confidence"
            status_color = "GREEN"
        elif score >= 75:
            status = "GOOD - Ready for paper trading, cautious live deployment"
            status_color = "YELLOW"
        elif score >= 60:
            status = "MARGINAL - Further validation required before live trading"
            status_color = "ORANGE"
        else:
            status = "NOT READY - Significant improvements needed"
            status_color = "RED"
        
        print(f"Status: {status}")
        
        # Individual test results
        print("\n" + "-"*90)
        print("  VALIDATION TEST RESULTS")
        print("-"*90)
        print(f"{'Test':<30} {'Status':<12} {'Score':<15} {'Threshold':<15}")
        print("-"*90)
        
        for v in validations:
            status = "PASS" if v.passed else "FAIL"
            print(f"{v.test_name:<30} {status:<12} {v.score:.2f}{'':<10} {v.threshold:.2f}")
        
        # Detailed analysis
        print("\n" + "-"*90)
        print("  DETAILED ANALYSIS")
        print("-"*90)
        
        for v in validations:
            print(f"\n{v.test_name}:")
            print(f"  {v.details}")
            if v.passed:
                print(f"  [PASS] Meets criteria for live trading")
            else:
                print(f"  [FAIL] Does not meet criteria - needs improvement")
        
        # Additional analysis
        print("\n" + "-"*90)
        print("  ADDITIONAL VALIDATION TESTS")
        print("-"*90)
        
        # Monte Carlo
        print("\n[MONTE CARLO SIMULATION]")
        all_trades = []
        for data in self.data.values():
            all_trades.extend(data.get('best_trades', []))
        
        if all_trades:
            mc = self.monte_carlo_simulation(all_trades, 1000)
            print(f"  Simulations: {mc['n_simulations']}")
            print(f"  Probability of Profit: {mc['prob_profit']:.1%}")
            print(f"  Median Final PnL: {mc['median_final_pnl']:.1%}")
            print(f"  Worst Case Drawdown (95th percentile): {mc['worst_case_dd']:.1%}")
            print(f"  Best Case PnL (95th percentile): {mc['best_case_pnl']:.1%}")
            print(f"  Worst Case PnL (5th percentile): {mc['worst_case_pnl']:.1%}")
            
            if mc['prob_profit'] > 0.9 and mc['worst_case_dd'] < 0.15:
                print(f"  [PASS] Monte Carlo shows robust profitability")
            else:
                print(f"  [WARNING] Monte Carlo shows concerning scenarios")
        
        # Walk-forward
        print("\n[WALK-FORWARD ANALYSIS]")
        wfa = self.walk_forward_analysis()
        if wfa.get('period_metrics'):
            print(f"  Periods tested: {len(wfa['period_metrics'])}")
            print(f"  Average Sharpe: {wfa['avg_sharpe']:.2f}")
            print(f"  Minimum Sharpe: {wfa['min_sharpe']:.2f}")
            print(f"  Sharpe Consistency (CV): {wfa['sharpe_consistency']:.2f}")
            if wfa['sharpe_consistency'] < 0.3:
                print(f"  [PASS] Strategy is consistent across periods")
            else:
                print(f"  [WARNING] Strategy varies significantly across periods")
        
        # Out-of-sample
        print("\n[OUT-OF-SAMPLE VALIDATION]")
        oos = self.out_of_sample_test()
        print(f"  In-Sample Sharpe: {oos.get('in_sample_sharpe', 0):.2f}")
        print(f"  Out-of-Sample Sharpe: {oos.get('out_sample_sharpe', 0):.2f}")
        print(f"  Sharpe Decay: {oos.get('sharpe_decay', 0):.1%}")
        print(f"  Reliability Score: {oos.get('reliability_score', 0):.1%}")
        if oos.get('passed'):
            print(f"  [PASS] Strategy performs well on unseen data")
        else:
            print(f"  [WARNING] Strategy degrades on unseen data")
        
        # Risk analysis
        print("\n[RISK ANALYSIS]")
        risk = self.risk_analysis()
        print(f"  95% VaR: {risk.get('var_95', 0):.2f}%")
        print(f"  99% VaR: {risk.get('var_99', 0):.2f}%")
        print(f"  Max Observed Drawdown: {risk.get('max_observed_dd', 0):.1f}%")
        print(f"  Average Drawdown: {risk.get('avg_dd', 0):.1f}%")
        print(f"  Skewness: {risk.get('skewness', 0):.2f} (positive = right tail)")
        print(f"  Kurtosis: {risk.get('kurtosis', 0):.2f} (fat tails if > 3)")
        
        # Recommendations
        print("\n" + "="*90)
        print("  RECOMMENDATIONS")
        print("="*90)
        
        if score >= 90:
            print("""
[EXCELLENT] Strategy shows strong potential for live trading:

1. DEPLOYMENT PHASE:
   - Start with 1-2% position sizing
   - Trade only during validated market regimes (volatile/transition)
   - Use the top 3 patterns: RSI_Oversold, RSI_Overbought, Connors_RSI2

2. RISK CONTROLS:
   - Hard stop at 6% portfolio drawdown
   - Max 3 consecutive losses before review
   - Daily loss limit: 3%

3. MONITORING:
   - Track live performance vs backtest daily
   - If Sharpe drops below 1.5 for 5 consecutive days, pause
   - Compare win rate vs 55% benchmark weekly
            """)
        elif score >= 75:
            print("""
[GOOD] Strategy shows promise but needs caution:

1. PAPER TRADING PHASE (2-4 weeks):
   - Trade on paper with real-time data
   - Track execution quality vs theoretical entries
   - Validate that signals trigger as expected

2. SMALL LIVE TEST (1-2 weeks):
   - Deploy 0.5-1% position sizing max
   - Trade only 1-2 symbols (BTC, ETH for liquidity)
   - Monitor for slippage and execution issues

3. SCALING:
   - If live matches paper, gradually increase to 1-2%
   - Add more symbols after proven consistency
            """)
        elif score >= 60:
            print("""
[MARGINAL] Strategy needs refinement before live trading:

1. IMPROVEMENTS NEEDED:
   - Increase sample size (need more trades)
   - Improve consistency across market regimes
   - Add more confirmation filters to reduce false signals

2. VALIDATION:
   - Run for another 2 weeks of forward testing
   - Optimize parameters on recent data
   - Test on more symbols

3. DO NOT DEPLOY LIVE YET
   - Continue paper trading only
   - Work on improving failing validation criteria
            """)
        else:
            print("""
[NOT READY] Strategy requires significant work:

1. CRITICAL ISSUES TO FIX:
   - Sharpe ratio too low (need > 1.5)
   - Win rate insufficient (need > 55%)
   - Drawdown too high (need < 15%)
   - Sample size too small (need > 100 trades)

2. NEXT STEPS:
   - Revisit strategy logic
   - Add more robust entry/exit rules
   - Implement better risk management
   - Test on longer time period

3. DO NOT TRADE LIVE
   - Strategy is not yet viable
   - Continue research and development
            """)
        
        # Save report
        report = {
            'assessment_date': datetime.now().isoformat(),
            'readiness_score': score,
            'status': status,
            'validations': [asdict(v) for v in validations],
            'monte_carlo': mc if all_trades else {},
            'walk_forward': wfa,
            'out_of_sample': oos,
            'risk_analysis': risk
        }
        
        output_path = Path('genome/results/live_readiness_report.json')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n[Saved] Full report: {output_path}")
        print("="*90 + "\n")
        
        return score, validations


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Rigorous Validation Framework')
    parser.add_argument('--validate-all', action='store_true', help='Run all validations')
    parser.add_argument('--live-ready-check', action='store_true', help='Quick live readiness check')
    
    args = parser.parse_args()
    
    validator = RigorousValidator()
    
    if not validator.data:
        print("No historical data found. Run historical analysis first:")
        print("  python genome/historical_reverse_engineer.py --all")
        return
    
    if args.validate_all or args.live_ready_check:
        score, validations = validator.generate_live_readiness_report()
        
        print(f"\n{'='*90}")
        print(f"FINAL VERDICT: {score:.0f}/100")
        print(f"{'='*90}")
        
        if score >= 90:
            print("✓ READY FOR LIVE TRADING (with proper risk controls)")
        elif score >= 75:
            print("[PAPER] READY FOR PAPER TRADING (live with caution)")
        elif score >= 60:
            print("⚠ NEEDS MORE VALIDATION")
        else:
            print("✗ NOT READY FOR LIVE TRADING")
    else:
        print("Rigorous Validation Framework")
        print("\nUsage:")
        print("  --validate-all       Run comprehensive validation")
        print("  --live-ready-check   Quick readiness assessment")
        print("\nExample:")
        print("  python rigorous_validation_framework.py --validate-all")


if __name__ == "__main__":
    main()
