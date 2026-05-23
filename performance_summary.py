#!/usr/bin/env python3
"""
Performance Summary Visualization
=================================

Creates visualizations of the strategy performance.
"""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Set style
plt.style.use('seaborn-v0_8')

# Data from comparison
periods = [
    'Bear Market Recovery',
    'Bitcoin ETF Launch',
    'Post-ETF Consolidation',
    'Spring Rally',
    'Summer Consolidation',
    'Fall Breakout',
    'Full 18-Month Trend'
]

unfiltered_returns = [1.80, 6.35, -5.58, 0.59, -4.42, 5.89, 1.80]
filtered_returns = [0.65, -0.10, -2.16, 1.72, -1.18, 7.43, 0.65]

unfiltered_trades = [19, 8, 17, 14, 13, 17, 19]
filtered_trades = [6, 3, 5, 10, 4, 7, 6]

unfiltered_win_rates = [37.2, 63.3, 24.3, 27.8, 16.7, 46.5, 37.2]
filtered_win_rates = [37.5, 50.0, 16.7, 33.3, 16.7, 80.0, 37.5]

# Create figure
fig = plt.figure(figsize=(15, 12))

# 1. Return Comparison
ax1 = fig.add_subplot(221)
bar_width = 0.35
index = np.arange(len(periods))

ax1.bar(index - bar_width/2, unfiltered_returns, bar_width, 
        label='Unfiltered', alpha=0.7, color='#1f77b4')
ax1.bar(index + bar_width/2, filtered_returns, bar_width, 
        label='Regime-Filtered', alpha=0.7, color='#ff7f0e')

ax1.set_xlabel('Market Period')
ax1.set_ylabel('Return (%)')
ax1.set_title('Monthly Return Comparison')
ax1.set_xticks(index)
ax1.set_xticklabels(periods, rotation=45, ha='right')
ax1.legend()
ax1.grid(True, alpha=0.3)

# 2. Win Rate Comparison
ax2 = fig.add_subplot(222)

ax2.bar(index - bar_width/2, unfiltered_win_rates, bar_width,
        label='Unfiltered', alpha=0.7, color='#1f77b4')
ax2.bar(index + bar_width/2, filtered_win_rates, bar_width,
        label='Regime-Filtered', alpha=0.7, color='#ff7f0e')

ax2.set_xlabel('Market Period')
ax2.set_ylabel('Win Rate (%)')
ax2.set_title('Monthly Win Rate Comparison')
ax2.set_xticks(index)
ax2.set_xticklabels(periods, rotation=45, ha='right')
ax2.legend()
ax2.grid(True, alpha=0.3)

# 3. Trade Count Comparison
ax3 = fig.add_subplot(223)

ax3.plot(index, unfiltered_trades, marker='o', linewidth=2, 
         label='Unfiltered', color='#1f77b4')
ax3.plot(index, filtered_trades, marker='s', linewidth=2, 
         label='Regime-Filtered', color='#ff7f0e')

ax3.set_xlabel('Market Period')
ax3.set_ylabel('Number of Trades')
ax3.set_title('Monthly Trade Count Comparison')
ax3.set_xticks(index)
ax3.set_xticklabels(periods, rotation=45, ha='right')
ax3.legend()
ax3.grid(True, alpha=0.3)

# 4. Overall Performance Metrics
ax4 = fig.add_subplot(224)

metrics = ['Total Return', 'Win Rate', 'Profit Factor', 'Max Drawdown']
unfiltered_values = [0.7, 34.9, 1.23, 10.5]
filtered_values = [1.5, 40.1, 1.19, 4.9]

ax4.bar(np.arange(len(metrics)) - bar_width/2, unfiltered_values, bar_width,
        label='Unfiltered', alpha=0.7, color='#1f77b4')
ax4.bar(np.arange(len(metrics)) + bar_width/2, filtered_values, bar_width,
        label='Regime-Filtered', alpha=0.7, color='#ff7f0e')

ax4.set_ylabel('Value')
ax4.set_title('Overall Performance Metrics')
ax4.set_xticks(np.arange(len(metrics)))
ax4.set_xticklabels(metrics, rotation=45, ha='right')
ax4.legend()
ax4.grid(True, alpha=0.3)

# Adjust layout
plt.tight_layout()
plt.savefig('performance_summary.png', dpi=300, bbox_inches='tight')
plt.show()

print("Performance summary saved as performance_summary.png")
