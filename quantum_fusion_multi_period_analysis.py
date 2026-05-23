"""
Quantum Fusion Strategy - Multi-Period Analysis Report
=====================================================

Analyzes the results of multi-period backtesting to validate strategy consistency.
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
import glob

def load_latest_backtest_results():
    """Load the most recent multi-period backtest results."""

    # Find the latest results file
    pattern = "quantum_fusion_multi_period_backtest_*.json"
    files = glob.glob(pattern)

    if not files:
        print("❌ No backtest result files found")
        return None

    # Get the most recent file
    latest_file = max(files, key=lambda x: x.split('_')[-1].replace('.json', ''))

    try:
        with open(latest_file, 'r') as f:
            data = json.load(f)
        print(f"✅ Loaded results from: {latest_file}")
        return data
    except Exception as e:
        print(f"❌ Error loading results: {e}")
        return None

def analyze_multi_period_performance(data):
    """Analyze performance across different periods."""

    if not data:
        return

    print("🧬 Quantum Fusion Strategy - Multi-Period Performance Analysis")
    print("=" * 80)

    period_summaries = data.get('period_summaries', {})
    detailed_results = data.get('detailed_results', [])

    # Overall summary
    summary = data.get('summary', {})
    print(f"📊 Test Summary:")
    print(f"   • Periods Tested: {summary.get('total_periods_tested', 0)}")
    print(f"   • Total Combinations: {summary.get('total_combinations', 0)}")
    print(f"   • Successful Tests: {summary.get('successful_tests', 0)}")
    print(f"   • Test Timestamp: {summary.get('timestamp', 'Unknown')}")

    # Period-by-period analysis
    print(f"\n📅 Period-by-Period Performance:")
    print("-" * 80)

    periods_data = []
    for period_name, summary in period_summaries.items():
        if summary.get('successful_tests', 0) > 0:
            period_data = {
                'Period': period_name,
                'Description': summary.get('description', ''),
                'Regime': summary.get('regime', ''),
                'Tests': summary.get('successful_tests', 0),
                'Trades': summary.get('total_trades', 0),
                'Win Rate': f"{summary.get('avg_win_rate', 0):.1%}",
                'Return': f"{summary.get('avg_return', 0):.1f}%",
                'Sharpe': f"{summary.get('avg_sharpe', 0):.2f}"
            }
            periods_data.append(period_data)

            print(f"   {period_data['Description']}")
            print(f"      Market Regime: {period_data['Regime']}")
            print(f"      Tests: {period_data['Tests']}, Trades: {period_data['Trades']}")
            print(f"      Win Rate: {period_data['Win Rate']}, Return: {period_data['Return']}, Sharpe: {period_data['Sharpe']}")
            print()

    # Market regime analysis
    print("🎭 Market Regime Performance Analysis:")
    print("-" * 80)

    regime_stats = {}
    for result in detailed_results:
        if result.get('total_trades', 0) > 0:
            period_name = result['period']
            regime = period_summaries.get(period_name, {}).get('regime', 'Unknown')

            if regime not in regime_stats:
                regime_stats[regime] = []

            regime_stats[regime].append({
                'win_rate': result.get('win_rate', 0),
                'return': result.get('total_return_percent', 0),
                'sharpe': result.get('sharpe_ratio', 0)
            })

    for regime, results in regime_stats.items():
        if results:
            avg_win_rate = np.mean([r['win_rate'] for r in results])
            avg_return = np.mean([r['return'] for r in results])
            avg_sharpe = np.mean([r['sharpe'] for r in results])

            print(f"   {regime}:")
            print(f"      Average Win Rate: {avg_win_rate:.1%}")
            print(f"      Average Return: {avg_return:.1f}%")
            print(f"      Average Sharpe: {avg_sharpe:.2f}")
            print(f"      Sample Size: {len(results)} tests")
            print()

    # Statistical consistency analysis
    print("📈 Strategy Consistency Analysis:")
    print("-" * 80)

    valid_results = [r for r in detailed_results if r.get('total_trades', 0) > 0]

    if valid_results:
        win_rates = [r.get('win_rate', 0) for r in valid_results]
        returns = [r.get('total_return_percent', 0) for r in valid_results]
        sharpes = [r.get('sharpe_ratio', 0) for r in valid_results]

        win_rate_mean = np.mean(win_rates)
        win_rate_std = np.std(win_rates)
        return_mean = np.mean(returns)
        return_std = np.std(returns)
        sharpe_mean = np.mean(sharpes)
        sharpe_std = np.std(sharpes)

        print(f"   Win Rate: Mean = {win_rate_mean:.1%}, Std = {win_rate_std:.3f} ({win_rate_std*100:.1f} pts)")
        print(f"   Returns: Mean = {return_mean:.1f}%, Std = {return_std:.1f} pts")
        print(f"   Sharpe: Mean = {sharpe_mean:.2f}, Std = {sharpe_std:.2f}")
        print(f"   Sample Size: {len(valid_results)} test combinations")

        # Best and worst performers
        best_win_rate = max(valid_results, key=lambda x: x.get('win_rate', 0))
        worst_win_rate = min(valid_results, key=lambda x: x.get('win_rate', 0))
        best_return = max(valid_results, key=lambda x: x.get('total_return_percent', 0))
        worst_return = min(valid_results, key=lambda x: x.get('total_return_percent', 0))

        print(f"\n🏆 Best Performers:")
        print(f"   Highest Win Rate: {best_win_rate['symbol']} {best_win_rate['timeframe']} in {best_win_rate['period']} - {best_win_rate['win_rate']:.1%}")
        print(f"   Highest Return: {best_return['symbol']} {best_return['timeframe']} in {best_return['period']} - {best_return['total_return_percent']:.1f}%")

        print(f"\n📉 Most Challenging:")
        print(f"   Lowest Win Rate: {worst_win_rate['symbol']} {worst_win_rate['timeframe']} in {worst_win_rate['period']} - {worst_win_rate['win_rate']:.1%}")
        print(f"   Lowest Return: {worst_return['symbol']} {worst_return['timeframe']} in {worst_return['period']} - {worst_return['total_return_percent']:.1f}%")

    # Validation criteria
    print("\n✅ VALIDATION CRITERIA:")
    print("-" * 80)

    if valid_results:
        # Performance criteria
        avg_win_rate = np.mean(win_rates)
        avg_return = np.mean(returns)
        win_rate_consistency = np.std(win_rates) < 0.15  # < 15% variation

        performance_ok = avg_win_rate >= 0.55
        return_ok = avg_return >= 5.0
        consistency_ok = win_rate_consistency

        print(f"   • Performance (≥55% Win Rate): {'✅' if performance_ok else '❌'} ({avg_win_rate:.1%})")
        print(f"   • Returns (≥5% Average): {'✅' if return_ok else '❌'} ({avg_return:.1f}%)")
        print(f"   • Consistency (Win Rate Std <15%): {'✅' if consistency_ok else '❌'} ({np.std(win_rates):.3f})")

        all_criteria_pass = performance_ok and return_ok and consistency_ok

        print(f"\n🏆 OVERALL VALIDATION: {'✅ PASSED' if all_criteria_pass else '❌ FAILED'}")

        if all_criteria_pass:
            print("   🎉 Quantum Fusion Strategy demonstrates consistent performance across market regimes!")
            print("   📈 Strategy is robust and ready for production deployment!")
        else:
            print("   ⚠️ Strategy shows inconsistent performance across different periods.")
            print("   🔧 Consider regime-specific optimizations.")

    # Create summary table
    if periods_data:
        print(f"\n📋 PERFORMANCE SUMMARY TABLE:")
        print("-" * 80)

        # Print header
        headers = ["Period", "Regime", "Win Rate", "Return", "Sharpe", "Trades"]
        print(f"{'':<12} {'':<20} {'':<8} {'':<8} {'':<6} {'':<6}")
        print("-" * 80)

        # Print data
        for period in periods_data:
            print(f"{period['Period']:<12} {period['Regime']:<20} {period['Win Rate']:<8} {period['Return']:<8} {period['Sharpe']:<6} {period['Trades']:<6}")

def main():
    """Main analysis function."""

    data = load_latest_backtest_results()
    if data:
        analyze_multi_period_performance(data)
    else:
        print("❌ Could not load backtest results for analysis")

if __name__ == "__main__":
    main()