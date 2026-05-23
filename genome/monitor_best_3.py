#!/usr/bin/env python3
"""
Best 3 Picks Monitor — Continuous Quality Scanner
=================================================

Runs the Best 3 selector on a schedule and logs changes.
Updates the dashboard and alerts on new high-quality setups.

Usage:
  python genome/monitor_best_3.py --interval 300  # Run every 5 minutes
  python genome/monitor_best_3.py --once          # Run once and exit
  python genome/monitor_best_3.py --watch         # Watch mode with alerts

Author: KIMI | Version: 1.0
"""

import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from genome.kimi_best_3_selector import Best3Selector


def log_message(msg, level="INFO"):
    """Log with timestamp."""
    est_tz = timezone(timedelta(hours=-4))
    ts = datetime.now(est_tz).strftime('%H:%M:%S')
    print(f"[{ts}] {level}: {msg}")


def load_previous_picks():
    """Load previous picks for comparison."""
    path = ROOT / 'genome' / 'data' / 'kimi_best_3_current.json'
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def compare_picks(old, new):
    """Compare old and new picks, return changes."""
    changes = []
    
    old_symbols = {p['symbol']: p for p in old.get('top_3', [])}
    new_symbols = {p['symbol']: p for p in new}
    
    # Check for new entries
    for symbol, pick in new_symbols.items():
        if symbol not in old_symbols:
            changes.append({
                'type': 'NEW',
                'symbol': symbol,
                'grade': pick['entry_grade'],
                'direction': pick['direction']
            })
    
    # Check for removed
    for symbol in old_symbols:
        if symbol not in new_symbols:
            changes.append({
                'type': 'REMOVED',
                'symbol': symbol
            })
    
    # Check for grade changes
    for symbol in set(old_symbols.keys()) & set(new_symbols.keys()):
        old_grade = old_symbols[symbol]['entry_grade']
        new_grade = new_symbols[symbol]['entry_grade']
        if old_grade != new_grade:
            changes.append({
                'type': 'GRADE_CHANGE',
                'symbol': symbol,
                'old_grade': old_grade,
                'new_grade': new_grade
            })
    
    return changes


def run_scan(args):
    """Execute a single scan."""
    log_message("Starting Best 3 scan...")
    
    selector = Best3Selector()
    best_3 = selector.select_best_3()
    
    if not best_3:
        log_message("No valid setups found.", "WARN")
        return
    
    # Save report
    report = selector.generate_report(best_3)
    
    output_path = ROOT / 'genome' / 'data' / 'kimi_best_3_current.json'
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    log_message(f"Saved to {output_path}")
    
    # Check for changes
    if args.watch or args.alert:
        previous = load_previous_picks()
        if previous:
            changes = compare_picks(previous, report['top_3'])
            if changes:
                log_message("CHANGES DETECTED:", "ALERT")
                for change in changes:
                    if change['type'] == 'NEW':
                        log_message(f"  NEW SETUP: {change['symbol']} {change['direction']} (Grade {change['grade']})", "ALERT")
                    elif change['type'] == 'REMOVED':
                        log_message(f"  REMOVED: {change['symbol']}", "WARN")
                    elif change['type'] == 'GRADE_CHANGE':
                        log_message(f"  GRADE CHANGE: {change['symbol']} {change['old_grade']} -> {change['new_grade']}", "ALERT")
    
    # Print summary with Entry/TP/SL
    log_message("="*60)
    log_message("TOP 3 PICKS - ENTRY / TP / SL")
    log_message("="*60)
    for i, pick in enumerate(best_3, 1):
        log_message(f"#{i}: {pick.symbol} [{pick.direction}] Grade:{pick.entry_grade} Conv:{pick.conviction_score:.0f}%")
        log_message(f"    ENTRY:${pick.entry_price} | TP:${pick.take_profit} | SL:${pick.stop_loss} | R:R {pick.risk_reward}:1")
    
    return report


def main():
    parser = argparse.ArgumentParser(description='Monitor Best 3 Picks')
    parser.add_argument('--interval', type=int, default=300,
                       help='Scan interval in seconds (default: 300 = 5 min)')
    parser.add_argument('--once', action='store_true',
                       help='Run once and exit')
    parser.add_argument('--watch', action='store_true',
                       help='Watch mode - show changes')
    parser.add_argument('--alert', action='store_true',
                       help='Alert on significant changes')
    args = parser.parse_args()
    
    if args.once:
        run_scan(args)
        return
    
    # Continuous mode
    log_message("Starting Best 3 Monitor (press Ctrl+C to stop)")
    log_message(f"Scan interval: {args.interval} seconds")
    
    try:
        while True:
            run_scan(args)
            
            if not args.once:
                log_message(f"Sleeping {args.interval}s...")
                time.sleep(args.interval)
                
    except KeyboardInterrupt:
        log_message("Monitor stopped by user")
        sys.exit(0)


if __name__ == '__main__':
    main()
