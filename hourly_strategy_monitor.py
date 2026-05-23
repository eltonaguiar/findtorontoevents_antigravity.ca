#!/usr/bin/env python3
"""
Hourly Strategy Monitor
=======================
Automated monitoring script that:
1. Checks all active bundle performance
2. Generates new strategies if performance drops
3. Monitors World-Class Ensemble signals
4. Reports to console and logs

Run: python hourly_strategy_monitor.py
Schedule: Run every hour via cron/Task Scheduler
"""

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'baby_strategies'))

DB_PATH = Path("battleground/data/bundle_babies.db")

def check_all_bundles():
    """Check performance of all bundles"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT bundle_id, name, forward_status, forward_trades, forward_realized_pnl,
               backtest_sharpe, backtest_win_rate, quality_score
        FROM bundle_babies
        ORDER BY forward_realized_pnl DESC, quality_score DESC
    ''')
    
    bundles = cursor.fetchall()
    conn.close()
    
    total_realized = sum(b[4] or 0 for b in bundles)
    total_trades = sum(b[3] or 0 for b in bundles)
    
    return bundles, total_realized, total_trades

def assess_strategy_health(bundles, total_realized, total_trades):
    """
    Assess if we need new strategies based on:
    - Total realized PnL < -10%
    - Avg trade PnL negative after 20+ trades
    - Top bundle negative after 20+ trades
    - No bundles with 100+ forward trades
    """
    issues = []
    action_needed = False
    
    # Check 1: Overall loss
    if total_realized < -10:
        issues.append(f"Total realized PnL negative: {total_realized:.2f}%")
        action_needed = True
    
    # Check 2: Per-trade average
    if total_trades > 20 and total_realized / total_trades < -0.5:
        issues.append(f"Per-trade avg negative: {total_realized/total_trades:.2f}%")
        action_needed = True
    
    # Check 3: Top bundle health
    top_bundle = bundles[0] if bundles else None
    if top_bundle:
        top_pnl = top_bundle[4] or 0
        top_trades = top_bundle[3] or 0
        if top_trades >= 20 and top_pnl < 0:
            issues.append(f"Top bundle '{top_bundle[1]}' negative after {top_trades} trades")
            action_needed = True
    
    # Check 4: Statistical significance
    bundles_with_100_trades = sum(1 for b in bundles if (b[3] or 0) >= 100)
    if bundles_with_100_trades == 0:
        issues.append("No bundles with 100+ forward trades yet")
    
    return action_needed, issues

def generate_new_strategy_recommendation(issues):
    """Generate recommendation for new strategy based on issues"""
    
    if any("negative" in i.lower() for i in issues):
        return {
            'urgency': 'HIGH',
            'recommendation': 'Create counter-trend mean reversion strategy',
            'rationale': 'Current strategies bleeding - need reversal edge',
            'template': 'Connors RSI-2 variant with volume filter'
        }
    elif any("100+" in i for i in issues):
        return {
            'urgency': 'MEDIUM',
            'recommendation': 'Create more strategy variants for diversification',
            'rationale': 'Need more statistical significance',
            'template': 'Multi-timeframe confluence strategy'
        }
    else:
        return {
            'urgency': 'LOW',
            'recommendation': 'Monitor and optimize existing',
            'rationale': 'Performance acceptable',
            'template': None
        }

def log_monitoring_report(bundles, total_realized, total_trades, action_needed, issues, recommendation):
    """Generate and save monitoring report"""
    
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    
    report = f"""
{'='*70}
[BABY BUNDLE MONITOR] Hourly Report - {timestamp}
{'='*70}

[OVERALL PERFORMANCE]
  Total Bundles: {len(bundles)}
  Total Forward Trades: {total_trades}
  Total Realized PnL: {total_realized:+.2f}%
  Avg PnL per Trade: {total_realized/max(1,total_trades):.2f}%

[TOP PERFORMING BUNDLES]
"""
    
    for i, b in enumerate(bundles[:5], 1):
        status = 'LIVE' if b[2] == 'live' else 'PAPER'
        trades = b[3] or 0
        pnl = b[4] or 0
        bt_sharpe = b[5] or 0
        bt_wr = b[6] or 0
        
        report += f"  {i}. {b[1][:40]:40} | {status} | {trades:3} trades | PnL: {pnl:+7.2f}% | BT: Sharpe {bt_sharpe:.2f} WR {bt_wr:.1f}%\n"
    
    report += f"\n[STRATEGY HEALTH ASSESSMENT]\n"
    
    if action_needed:
        report += f"  STATUS: ACTION REQUIRED\n"
        report += f"  Issues Found:\n"
        for issue in issues:
            report += f"    - {issue}\n"
        report += f"\n  RECOMMENDATION:\n"
        report += f"    Urgency: {recommendation['urgency']}\n"
        report += f"    Action: {recommendation['recommendation']}\n"
        report += f"    Rationale: {recommendation['rationale']}\n"
        if recommendation['template']:
            report += f"    Suggested Template: {recommendation['template']}\n"
    else:
        report += f"  STATUS: HEALTHY\n"
        report += f"  Performance acceptable. Continue monitoring.\n"
    
    report += f"\n[WORLD-CLASS ENSEMBLE STATUS]\n"
    worldclass = next((b for b in bundles if 'WorldClass' in b[1]), None)
    if worldclass:
        report += f"  Status: ACTIVE\n"
        report += f"  Forward Trades: {worldclass[3] or 0}\n"
        report += f"  Realized PnL: {worldclass[4] or 0:.2f}%\n"
        report += f"  Strategy: WorldClassEnsemble_v1\n"
        report += f"  Components: Connors RSI-2, TTM Squeeze, HMA Trend, Z-Score MR\n"
    else:
        report += f"  Status: NOT FOUND - Run create_worldclass_bundle.py\n"
    
    report += f"\n{'='*70}\n"
    
    print(report)
    
    # Save to log file
    log_file = Path(__file__).parent / 'logs' / 'hourly_monitor.log'
    log_file.parent.mkdir(exist_ok=True)
    
    with open(log_file, 'a') as f:
        f.write(report)
    
    return report

def main():
    """Main monitoring function"""
    print("[MONITOR] Starting hourly strategy check...")
    
    # Check all bundles
    bundles, total_realized, total_trades = check_all_bundles()
    
    # Assess health
    action_needed, issues = assess_strategy_health(bundles, total_realized, total_trades)
    
    # Generate recommendation
    recommendation = generate_new_strategy_recommendation(issues)
    
    # Log report
    log_monitoring_report(bundles, total_realized, total_trades, action_needed, issues, recommendation)
    
    # Return status for automation
    if action_needed and recommendation['urgency'] == 'HIGH':
        print("\n[ALERT] High urgency action required! Consider creating new strategy.")
        return 1  # Non-zero exit for alerting
    else:
        print("\n[OK] Monitoring complete. All systems normal.")
        return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
