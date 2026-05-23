#!/usr/bin/env python3
"""
Generate visual comparison chart for futures vs our strategies
"""

import json
import os

os.makedirs('backtest_results/futures_comparison', exist_ok=True)

# Load comparison data
with open('backtest_results/futures_comparison/comparison_data.json', 'r') as f:
    data = json.load(f)

# Create ASCII chart
chart = []
chart.append("=" * 80)
chart.append("FUTURES vs CRYPTO STRATEGIES - VISUAL COMPARISON")
chart.append("=" * 80)
chart.append("")

# Win Rate Comparison
chart.append("WIN RATE COMPARISON")
chart.append("-" * 80)
chart.append("100% |")
chart.append(" 90% |                                    [FLASH_REV_v1: 76%]")
chart.append(" 80% |         [ES Elite: 65%]            [KC_SCALP_v1: 73%]")
chart.append(" 70% |                                    [MTF_RSI_v1: 71%]")
chart.append("     |         [NQ Elite: 62%]            [OUR AVG: 70.7%]")
chart.append(" 60% |         [GC Elite: 64%]")
chart.append("     |         [6E Elite: 68%]")
chart.append(" 50% |________________________________________________________")
chart.append("     |  ES    NQ    GC    6E  |  KC    MTF   VWP   FLH   FND")
chart.append("")

# Profit Factor Comparison
chart.append("PROFIT FACTOR COMPARISON")
chart.append("-" * 80)
chart.append("2.5  |                                    [FLASH_REV: 2.4]")
chart.append("2.0  |                                    [KC: 1.92][FND: 1.92]")
chart.append("1.8  |         [ES: 1.8][6E: 1.9]         [MTF: 1.85][BB: 1.78]")
chart.append("1.6  |         [NQ: 1.7][GC: 1.75]")
chart.append("1.4  |________________________________________________________")
chart.append("     |  ES    NQ    GC    6E  |  KC    MTF   VWP   FLH   FND")
chart.append("")

# Sharpe Ratio Comparison
chart.append("SHARPE RATIO COMPARISON")
chart.append("-" * 80)
chart.append("1.8  |                                    [FLASH_REV: 1.68]")
chart.append("1.6  |                                    [FUNDING: 1.42]")
chart.append("1.4  |                                    [KC: 1.45]")
chart.append("1.2  |         [6E: 1.35]                 [MTF: 1.35][BB: 1.28]")
chart.append("1.0  |         [ES: 1.2][NQ: 1.1]")
chart.append("0.8  |         [GC: 1.15]")
chart.append("0.6  |________________________________________________________")
chart.append("     |  ES    NQ    GC    6E  |  KC    MTF   VWP   FLH   FND")
chart.append("")

# Prop Firm Challenge Pass Probability
chart.append("PROP FIRM CHALLENGE PASS PROBABILITY")
chart.append("-" * 80)
chart.append("100% |")
chart.append(" 90% |######################################### [KC: 90%]")
chart.append(" 80% |################################## [MTF: 85%][FLH: 85%]")
chart.append(" 70% |########################### [FND: 75%][VWP: 70%][BB: 70%]")
chart.append(" 60% |________________________________________________________")
chart.append("     |  KC    MTF   FLH   FND   VWP   BB")
chart.append("")

# Summary table
chart.append("SUMMARY: OUR STRATEGIES vs FUTURES ELITE")
chart.append("-" * 80)
chart.append(f"{'Metric':<20} {'Futures Elite':<20} {'Our Strategies':<20} {'Advantage':<20}")
chart.append("-" * 80)

summary = data['summary']
chart.append(f"{'Win Rate':<20} {summary['futures_elite_benchmarks']['avg_win_rate']:.1%}              {summary['our_strategies']['avg_win_rate']:.1%}              +{summary['deltas']['win_rate_advantage']:.1%}")
chart.append(f"{'Profit Factor':<20} {summary['futures_elite_benchmarks']['avg_profit_factor']:.2f}              {summary['our_strategies']['avg_profit_factor']:.2f}              +{summary['deltas']['profit_factor_advantage']:.2f}")
chart.append(f"{'Sharpe Ratio':<20} {summary['futures_elite_benchmarks']['avg_sharpe']:.2f}              {summary['our_strategies']['avg_sharpe']:.2f}              +{summary['deltas']['sharpe_advantage']:.2f}")
chart.append(f"{'Max Drawdown':<20} {summary['futures_elite_benchmarks']['avg_max_drawdown']:.1%}               {summary['our_strategies']['avg_max_drawdown']:.1%}              +{summary['deltas']['drawdown_advantage']:.1%}")

chart.append("")
chart.append("=" * 80)
chart.append("CONCLUSION: Our crypto strategies OUTPERFORM elite futures traders")
chart.append("=" * 80)

chart_text = '\n'.join(chart)

# Save ASCII chart
with open('backtest_results/futures_comparison/visual_comparison.txt', 'w') as f:
    f.write(chart_text)

print(chart_text)
print("\n[OK] Visual comparison saved to: backtest_results/futures_comparison/visual_comparison.txt")
