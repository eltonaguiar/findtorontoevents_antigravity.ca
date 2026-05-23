#!/usr/bin/env python3
"""
Comprehensive Historical Analysis Report Generator
===================================================

Generates a complete report analyzing what would've worked across:
- Today (last 24h)
- Yesterday (24-48h ago)
- Last week (7 days)

For each period, shows:
- Win rates and profit factors
- Average holding periods (how long to hold)
- Sharpe ratios (risk-adjusted returns)
- Max drawdowns
- Best performing patterns
- Symbol-by-symbol breakdown

Usage:
    python comprehensive_historical_analysis.py --generate
    python comprehensive_historical_analysis.py --summary
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ComprehensiveAnalysis')


def run_analysis(period: str) -> Dict:
    """Run historical analysis for a period."""
    logger.info(f"Running analysis for {period}...")
    
    try:
        result = subprocess.run(
            [sys.executable, 'genome/historical_reverse_engineer.py', f'--{period}'],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # Load results
        output_file = Path(f'genome/results/historical_{period}.json')
        if output_file.exists():
            with open(output_file) as f:
                return json.load(f)
        
    except Exception as e:
        logger.error(f"Failed to analyze {period}: {e}")
    
    return {}


def load_all_results() -> Dict[str, Dict]:
    """Load results from all periods if they exist."""
    results = {}
    
    for period in ['today', 'yesterday', 'week', 'month']:
        file_path = Path(f'genome/results/historical_{period}.json')
        if file_path.exists():
            with open(file_path) as f:
                results[period] = json.load(f)
    
    return results


def generate_summary_report(results: Dict[str, Dict]):
    """Generate comprehensive summary report."""
    
    print("\n" + "="*90)
    print("  COMPREHENSIVE HISTORICAL REVERSE ENGINEERING REPORT")
    print("="*90)
    print(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Analysis: What trading patterns WOULD have won in recent history")
    
    # Summary table
    print("\n" + "-"*90)
    print("  SUMMARY BY TIME PERIOD")
    print("-"*90)
    print(f"{'Period':<12} {'Trades':>8} {'Win Rate':>10} {'Total PnL':>12} {'Sharpe':>10} {'Max DD':>10} {'Avg Hold':>12}")
    print("-"*90)
    
    for period in ['today', 'yesterday', 'week', 'month']:
        if period in results:
            m = results[period]['overall_metrics']
            avg_hold_hours = m['avg_holding_minutes'] / 60
            print(f"{period.capitalize():<12} {m['total_trades']:>8} {m['win_rate']*100:>9.1f}% "
                  f"{m['total_pnl_pct']:>11.1f}% {m['sharpe_ratio']:>10.2f} {m['max_drawdown_pct']:>9.1f}% "
                  f"{avg_hold_hours:>10.1f}h")
    
    print("-"*90)
    
    # Detailed period analysis
    for period in ['today', 'yesterday', 'week', 'month']:
        if period not in results:
            continue
        
        result = results[period]
        m = result['overall_metrics']
        
        print(f"\n{'='*90}")
        print(f"  {period.upper()} ANALYSIS")
        print("="*90)
        
        # Core metrics
        print(f"\n[PERFORMANCE METRICS]")
        print(f"  Total Trades:     {m['total_trades']}")
        print(f"  Win Rate:         {m['win_rate']*100:.1f}% ({m['winning_trades']} wins / {m['losing_trades']} losses)")
        print(f"  Total PnL:        {m['total_pnl_pct']:.1f}%")
        print(f"  Average Trade:    {m['avg_trade_pct']:.2f}%")
        print(f"  Profit Factor:    {m['profit_factor']:.2f}")
        print(f"  Expectancy:       {m['expectancy']:.2f}% per trade")
        
        # Holding time
        print(f"\n[HOLDING TIME ANALYSIS - HOW LONG TO HOLD?]")
        print(f"  Average:          {m['avg_holding_minutes']:.0f} minutes ({m['avg_holding_minutes']/60:.1f} hours)")
        print(f"  Median:           {m['median_holding_minutes']:.0f} minutes")
        print(f"  Shortest:         {m['shortest_trade_minutes']} minutes")
        print(f"  Longest:          {m['longest_trade_minutes']} minutes ({m['longest_trade_minutes']/60:.1f} hours)")
        print(f"\n  INTERPRETATION:")
        if m['avg_holding_minutes'] < 60:
            print(f"    -> Optimal holding: SCALPING (under 1 hour)")
        elif m['avg_holding_minutes'] < 240:
            print(f"    -> Optimal holding: INTRADAY (1-4 hours)")
        else:
            print(f"    -> Optimal holding: SWING (4+ hours)")
        
        # Risk metrics
        print(f"\n[RISK METRICS]")
        print(f"  Sharpe Ratio:     {m['sharpe_ratio']:.2f}")
        if m['sharpe_ratio'] > 2:
            print(f"    -> EXCELLENT: High risk-adjusted returns")
        elif m['sharpe_ratio'] > 1:
            print(f"    -> GOOD: Acceptable risk-adjusted returns")
        else:
            print(f"    -> POOR: Low risk-adjusted returns")
        
        print(f"  Sortino Ratio:    {m['sortino_ratio']:.2f}")
        print(f"  Calmar Ratio:     {m['calmar_ratio']:.2f}")
        print(f"  Max Drawdown:     {m['max_drawdown_pct']:.1f}%")
        print(f"  Recovery Factor:  {m['recovery_factor']:.2f}")
        print(f"  Max Consecutive:  {m['max_consecutive_losses']} losses")
        print(f"  Consistency:      {m['consistency_score']*100:.1f}%")
        
        # Top patterns
        print(f"\n[TOP PERFORMING PATTERNS]")
        for i, pattern in enumerate(result['pattern_performance'][:5], 1):
            print(f"\n  {i}. {pattern['pattern_name']}")
            print(f"     Trades:        {pattern['total_trades']}")
            print(f"     Win Rate:      {pattern['win_rate']*100:.1f}%")
            print(f"     Total PnL:     {pattern['total_pnl_pct']:.1f}%")
            print(f"     Profit Factor: {pattern['profit_factor']:.2f}")
            print(f"     Sharpe:        {pattern['sharpe_ratio']:.2f}")
            print(f"     Avg Hold:      {pattern['avg_holding_minutes']:.0f}min")
            print(f"     Max DD:        {pattern['max_drawdown_pct']:.1f}%")
        
        # Best trades
        print(f"\n[BEST TRADES]")
        for i, trade in enumerate(result['best_trades'][:5], 1):
            print(f"  {i}. {trade['symbol']} {trade['direction']}")
            print(f"     Entry: ${trade['entry']:.4f} -> Exit: ${trade['exit']:.4f}")
            print(f"     PnL: +{trade['pnl_pct']:.2f}% in {trade['duration_min']} minutes")
            print(f"     Max DD: {trade['max_dd']:.1f}% | Regime: {trade['regime']}")
        
        # Symbol breakdown
        print(f"\n[SYMBOL BREAKDOWN - TOP PERFORMERS]")
        sorted_symbols = sorted(
            result['symbol_breakdown'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        for symbol, count in sorted_symbols:
            print(f"  {symbol}: {count} winning trades")
    
    # Cross-period comparison
    if len(results) > 1:
        print("\n" + "="*90)
        print("  CROSS-PERIOD COMPARISON")
        print("="*90)
        
        print("\n[CONSISTENT PATTERNS ACROSS TIME]")
        print("(Patterns that performed well in multiple periods)")
        
        # Find patterns that appear in multiple periods
        pattern_scores = {}
        for period, result in results.items():
            for pattern in result['pattern_performance'][:5]:
                name = pattern['pattern_name']
                if name not in pattern_scores:
                    pattern_scores[name] = []
                pattern_scores[name].append({
                    'period': period,
                    'sharpe': pattern['sharpe_ratio'],
                    'win_rate': pattern['win_rate'],
                    'pnl': pattern['total_pnl_pct']
                })
        
        # Show patterns appearing in 2+ periods
        consistent = {k: v for k, v in pattern_scores.items() if len(v) >= 2}
        if consistent:
            for name, performances in sorted(consistent.items(), 
                                            key=lambda x: sum(p['sharpe'] for p in x[1]),
                                            reverse=True):
                print(f"\n  {name}")
                print(f"    Appears in {len(performances)} periods")
                for perf in performances:
                    print(f"      {perf['period']}: Sharpe {perf['sharpe']:.2f}, "
                          f"WR {perf['win_rate']*100:.0f}%, PnL {perf['pnl']:.1f}%")
        else:
            print("  No patterns appeared consistently across multiple periods")
            print("  (This suggests market conditions changed significantly)")
    
    # Recommendations
    print("\n" + "="*90)
    print("  KEY INSIGHTS & RECOMMENDATIONS")
    print("="*90)
    
    # Calculate averages across periods
    if results:
        avg_sharpe = sum(r['overall_metrics']['sharpe_ratio'] for r in results.values()) / len(results)
        avg_hold = sum(r['overall_metrics']['avg_holding_minutes'] for r in results.values()) / len(results)
        avg_win_rate = sum(r['overall_metrics']['win_rate'] for r in results.values()) / len(results)
        
        print(f"\n[AVERAGES ACROSS PERIODS]")
        print(f"  Average Sharpe Ratio: {avg_sharpe:.2f}")
        print(f"  Average Win Rate:     {avg_win_rate*100:.1f}%")
        print(f"  Average Hold Time:    {avg_hold:.0f} minutes ({avg_hold/60:.1f} hours)")
        
        print(f"\n[WHAT WORKS?]")
        if avg_sharpe > 2:
            print(f"  -> EXCELLENT: Current patterns show strong risk-adjusted returns")
        elif avg_sharpe > 1:
            print(f"  -> GOOD: Patterns are viable but monitor for degradation")
        else:
            print(f"  -> CAUTION: Risk-adjusted returns are marginal")
        
        if avg_hold < 60:
            print(f"  -> SCALPING is optimal: Hold positions for under 1 hour")
        elif avg_hold < 180:
            print(f"  -> INTRADAY is optimal: Hold for 1-3 hours")
        else:
            print(f"  -> SWING trading: Hold for 3+ hours")
        
        print(f"\n[DEPLOYMENT RECOMMENDATIONS]")
        print(f"  1. Use patterns with Sharpe > 1.5 for live trading")
        print(f"  2. Set holding time limits based on historical averages")
        print(f"  3. Use max drawdown metrics for position sizing")
        print(f"  4. Avoid trading when patterns show low consistency scores")
    
    print("\n" + "="*90)
    print("Report saved to: genome/results/comprehensive_historical_report.json")
    print("="*90 + "\n")


def save_comprehensive_report(results: Dict[str, Dict]):
    """Save comprehensive report to JSON."""
    
    # Calculate summary stats
    summary = {}
    for period, result in results.items():
        m = result['overall_metrics']
        summary[period] = {
            'trades': m['total_trades'],
            'win_rate': m['win_rate'],
            'total_pnl': m['total_pnl_pct'],
            'sharpe': m['sharpe_ratio'],
            'max_dd': m['max_drawdown_pct'],
            'avg_hold_hours': m['avg_holding_minutes'] / 60,
            'profit_factor': m['profit_factor'],
            'expectancy': m['expectancy']
        }
    
    output = {
        'generated_at': datetime.now().isoformat(),
        'periods_analyzed': list(results.keys()),
        'summary': summary,
        'detailed_results': results
    }
    
    output_path = Path('genome/results/comprehensive_historical_report.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    logger.info(f"Saved comprehensive report to {output_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Comprehensive Historical Analysis')
    parser.add_argument('--generate', action='store_true', 
                       help='Generate new analysis for all periods')
    parser.add_argument('--summary', action='store_true',
                       help='Show summary of existing results')
    
    args = parser.parse_args()
    
    if args.generate:
        # Run analysis for each period
        for period in ['today', 'yesterday', 'week']:
            run_analysis(period)
        
        # Load and report
        results = load_all_results()
        generate_summary_report(results)
        save_comprehensive_report(results)
    
    elif args.summary:
        results = load_all_results()
        if results:
            generate_summary_report(results)
        else:
            print("No results found. Run with --generate first.")
    
    else:
        print("Comprehensive Historical Analysis")
        print("\nUsage:")
        print("  --generate    Run full analysis for all periods")
        print("  --summary     Show summary of existing results")
        print("\nExample:")
        print("  python comprehensive_historical_analysis.py --generate")


if __name__ == "__main__":
    main()
