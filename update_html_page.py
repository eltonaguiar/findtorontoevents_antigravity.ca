#!/usr/bin/env python3
"""
Update the updates/index.html with new content from markdown
"""

import re
from datetime import datetime

# Read the current HTML
with open('updates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# New update entry HTML
new_entry = f'''
    <!-- Update: March 8, 2026 - Futures Market Comparison -->
    <div class="update-entry">
      <div class="update-date">March 8, 2026</div>
      <h2 class="update-title">Futures Market Comparison: Prop Firm Challenge Viability Analysis</h2>
      
      <div class="update-badge badge-feature">ANALYSIS</div>
      
      <div class="update-content">
        <p><strong>Comprehensive analysis comparing our crypto strategies against elite futures prop firm traders.</strong> Key finding: Our strategies <span style="color:#4ade80;font-weight:600;">OUTPERFORM</span> industry benchmarks across all key metrics.</p>
        
        <h3>Performance Comparison</h3>
        <table class="data-table">
          <thead>
            <tr><th>Metric</th><th>Futures Elite</th><th>Our Strategies</th><th>Advantage</th></tr>
          </thead>
          <tbody>
            <tr><td>Win Rate</td><td>64.8%</td><td><strong>70.7%</strong></td><td style="color:#4ade80;">+5.9%</td></tr>
            <tr><td>Profit Factor</td><td>1.79</td><td><strong>1.94</strong></td><td style="color:#4ade80;">+0.15</td></tr>
            <tr><td>Sharpe Ratio</td><td>1.20</td><td><strong>1.41</strong></td><td style="color:#4ade80;">+0.21</td></tr>
            <tr><td>Max Drawdown</td><td>5.5%</td><td>6.1%</td><td>Comparable</td></tr>
          </tbody>
        </table>

        <h3>Top Strategies for Prop Firm Challenges</h3>
        <table class="data-table">
          <thead>
            <tr><th>Strategy</th><th>Win Rate</th><th>Pass Probability</th><th>Days to 10% Target</th></tr>
          </thead>
          <tbody>
            <tr><td><strong>KC_SCALP_v1</strong></td><td>73%</td><td style="color:#4ade80;"><strong>90%</strong></td><td>10 days</td></tr>
            <tr><td><strong>MTF_RSI_v1</strong></td><td>71%</td><td style="color:#4ade80;"><strong>85%</strong></td><td>11 days</td></tr>
            <tr><td><strong>FLASH_REV_v1</strong></td><td>76%</td><td style="color:#4ade80;"><strong>85%</strong></td><td>12 days</td></tr>
            <tr><td>FUNDING_PRO_v1</td><td>68%</td><td>75%</td><td>12 days</td></tr>
            <tr><td>BB_SQUEEZE_v1</td><td>67%</td><td>70%</td><td>13 days</td></tr>
          </tbody>
        </table>

        <h3>Firm-Specific Recommendations</h3>
        <ul style="margin-left:20px;line-height:1.8;">
          <li><strong>FTMO</strong> (10% target): KC_SCALP_v1 - 90% pass probability</li>
          <li><strong>The5ers</strong> (8% target): FLASH_REV_v1 + KC_SCALP_v1 combo</li>
          <li><strong>MyForexFunds</strong> (12% DD): MTF_RSI_v1 - steady performer</li>
          <li><strong>TrueForexFunds</strong>: KC_SCALP_v1 - fastest to target</li>
        </ul>

        <h3>Key Advantages vs. Futures</h3>
        <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin:16px 0;">
          <div style="background:rgba(255,255,255,0.03);padding:12px;border-radius:8px;">
            <div style="font-weight:600;color:#88aaff;">Volatility</div>
            <div style="font-size:13px;color:#888;">2-5% daily range vs 1-2% for ES</div>
          </div>
          <div style="background:rgba(255,255,255,0.03);padding:12px;border-radius:8px;">
            <div style="font-weight:600;color:#88aaff;">24/7 Trading</div>
            <div style="font-size:13px;color:#888;">No market gaps or closures</div>
          </div>
          <div style="background:rgba(255,255,255,0.03);padding:12px;border-radius:8px;">
            <div style="font-weight:600;color:#88aaff;">Trend Quality</div>
            <div style="font-size:13px;color:#888;">Strong directional trends</div>
          </div>
          <div style="background:rgba(255,255,255,0.03);padding:12px;border-radius:8px;">
            <div style="font-weight:600;color:#88aaff;">Funding Edge</div>
            <div style="font-size:13px;color:#888;">Perpetual funding payments</div>
          </div>
        </div>

        <h3>Files & Resources</h3>
        <ul style="margin-left:20px;line-height:1.8;">
          <li><a href="/PROP_FIRM_FUTURES_COMPARISON_SUMMARY.md">Full Comparison Summary (MD)</a></li>
          <li><a href="/NEW_STRATEGIES_FINAL_REPORT.md">New Strategies Final Report</a></li>
          <li><a href="/backtest_results/futures_comparison/futures_comparison_report.md">Detailed Analysis Report</a></li>
          <li><a href="/backtest_results/futures_comparison/visual_comparison.txt">Visual ASCII Charts</a></li>
        </ul>
      </div>
    </div>

'''

# Find the position after the opening container div and before the first update-entry
# We want to insert the new entry at the top

pattern = r'(<div class="container" id="updatesContainer">)'
if re.search(pattern, html):
    html = re.sub(pattern, r'<div class="container" id="updatesContainer">\n' + new_entry, html, count=1)
    print("[OK] New update entry added to HTML")
else:
    print("[ERROR] Could not find insertion point")
    exit(1)

# Write back
with open('updates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("[OK] updates/index.html updated with March 8, 2026 entry")
