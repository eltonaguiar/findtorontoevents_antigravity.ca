#!/usr/bin/env python3
"""
================================================================================
LIVE PERFORMANCE DASHBOARD - Real-Time War Room Display
================================================================================

Run this in a separate terminal while war_room.py is running to see live stats.

Usage:
    python live_dashboard.py --watch war_room_report_*.json
================================================================================
"""

import argparse
import json
import time
import os
from datetime import datetime
from pathlib import Path


def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def format_currency(value: float) -> str:
    """Format as currency"""
    if value >= 0:
        return f"${value:,.2f}"
    else:
        return f"-${abs(value):,.2f}"


def get_color(value: float) -> str:
    """Get ANSI color code"""
    if value > 0:
        return "\033[92m"  # Green
    elif value < 0:
        return "\033[91m"  # Red
    else:
        return "\033[93m"  # Yellow


def reset_color():
    """Reset ANSI color"""
    return "\033[0m"


def render_dashboard(report_path: str):
    """Render the live dashboard"""
    try:
        with open(report_path) as f:
            data = json.load(f)
    except:
        return "Waiting for battle report..."
    
    # Extract data
    initial = data.get('initial_capital', 0)
    current = data.get('current_equity', 0)
    return_pct = data.get('total_return_pct', 0)
    battles = data.get('battles_fought', 0)
    won = data.get('battles_won', 0)
    lost = data.get('battles_lost', 0)
    win_rate = (won / battles * 100) if battles > 0 else 0
    
    open_pos = data.get('open_positions', {})
    closed_pos = data.get('closed_positions', [])
    
    # Build dashboard
    lines = []
    lines.append("=" * 80)
    lines.append("🚨 CRYPTOALPHA PRO - LIVE WAR ROOM DASHBOARD 🚨".center(80))
    lines.append("=" * 80)
    lines.append("")
    
    # Portfolio Overview
    lines.append("📊 PORTFORTFOLIO OVERVIEW")
    lines.append("-" * 80)
    
    color = get_color(return_pct)
    reset = reset_color()
    
    lines.append(f"  Initial Capital:    {format_currency(initial)}")
    lines.append(f"  Current Equity:     {format_currency(current)}")
    lines.append(f"  Total Return:       {color}{return_pct:+.2f}%{reset}")
    lines.append(f"  P&L:                {color}{format_currency(current - initial)}{reset}")
    lines.append("")
    
    # Battle Stats
    lines.append("⚔️  BATTLE STATISTICS")
    lines.append("-" * 80)
    lines.append(f"  Battles Fought:     {battles}")
    
    win_color = get_color(1 if win_rate > 50 else -1)
    lines.append(f"  Victories:          {won} {win_color}({win_rate:.1f}%){reset}")
    lines.append(f"  Defeats:            {lost}")
    lines.append(f"  Open Positions:     {len(open_pos)}")
    lines.append("")
    
    # Open Positions
    if open_pos:
        lines.append("🎯 OPEN POSITIONS (LIVE)")
        lines.append("-" * 80)
        lines.append(f"  {'Asset':<8} {'Entry':<12} {'Current':<12} {'P&L %':<10} {'Status':<15}")
        lines.append(f"  {'-'*7:<8} {'-'*11:<12} {'-'*11:<12} {'-'*9:<10} {'-'*14:<15}")
        
        for asset, pos in open_pos.items():
            entry = pos.get('entry_price', 0)
            current_price = pos.get('current_price', 0)
            pnl_pct = pos.get('unrealized_pct', 0) * 100
            status = pos.get('status', 'OPEN')
            
            pnl_color = get_color(pnl_pct)
            lines.append(f"  {asset:<8} ${entry:<11,.2f} ${current_price:<11,.2f} {pnl_color}{pnl_pct:+>8.2f}%{reset} {status:<15}")
        
        # Show targets
        lines.append("")
        lines.append("  TARGETS:")
        for asset, pos in open_pos.items():
            tp1 = pos.get('tp1', 0)
            tp2 = pos.get('tp2', 0)
            tp3 = pos.get('tp3', 0)
            stop = pos.get('stop_loss', 0)
            lines.append(f"    {asset}: Stop ${stop:,.0f} | TP1 ${tp1:,.0f} | TP2 ${tp2:,.0f} | TP3 ${tp3:,.0f} 🌙")
        lines.append("")
    
    # Recent Closed Positions
    if closed_pos:
        lines.append("📈 RECENT BATTLES (Last 5)")
        lines.append("-" * 80)
        lines.append(f"  {'Asset':<8} {'Result':<10} {'P&L %':<10} {'Exit Reason':<20}")
        lines.append(f"  {'-'*7:<8} {'-'*9:<10} {'-'*9:<10} {'-'*19:<20}")
        
        for pos in closed_pos[-5:]:
            asset = pos.get('asset', 'N/A')
            status = pos.get('status', 'UNKNOWN')
            
            # Calculate final P&L
            entry = pos.get('entry_price', 0)
            
            if status == 'STOP_LOSS':
                exit_p = pos.get('stop_loss', 0)
            elif status == 'TP1_HIT':
                exit_p = pos.get('tp1', 0)
            elif status == 'TP2_HIT':
                exit_p = pos.get('tp2', 0)
            elif status == 'TP3_HIT':
                exit_p = pos.get('tp3', 0)
            else:
                exit_p = entry
            
            pnl_pct = (exit_p - entry) / entry * 100 if entry > 0 else 0
            
            result_emoji = "✅" if pnl_pct > 0 else "❌"
            pnl_color = get_color(pnl_pct)
            
            lines.append(f"  {asset:<8} {result_emoji:<10} {pnl_color}{pnl_pct:+>8.2f}%{reset} {status:<20}")
        lines.append("")
    
    # Signals Generated
    signals = data.get('signals_generated', [])
    if signals:
        lines.append("🚨 EXTREME SIGNALS GENERATED (Last 3)")
        lines.append("-" * 80)
        
        for sig in signals[-3:]:
            asset = sig.get('asset', 'N/A')
            score = sig.get('composite_score', 0)
            conviction = sig.get('conviction', 'NONE')
            timestamp = sig.get('timestamp', '')[:19].replace('T', ' ')
            
            lines.append(f"  [{timestamp}] {asset} - {conviction} ({score:.1f}/100)")
        lines.append("")
    
    # Footer
    timestamp = data.get('timestamp', datetime.now().isoformat())
    lines.append("-" * 80)
    lines.append(f"Last Update: {timestamp}")
    lines.append("Press Ctrl+C to exit dashboard")
    lines.append("=" * 80)
    
    return "\n".join(lines)


def watch_file(pattern: str, interval: int = 5):
    """Watch for newest file matching pattern"""
    print("👁️  Watching for battle reports...")
    print(f"   Pattern: {pattern}")
    print(f"   Refresh: {interval}s")
    print("\nStarting dashboard in 3 seconds...\n")
    time.sleep(3)
    
    try:
        while True:
            # Find newest matching file
            files = list(Path('.').glob(pattern))
            if files:
                newest = max(files, key=lambda p: p.stat().st_mtime)
                
                # Render dashboard
                clear_screen()
                dashboard = render_dashboard(str(newest))
                print(dashboard)
            else:
                clear_screen()
                print("Waiting for war room to generate battle reports...")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n👋 Dashboard closed.")


def main():
    parser = argparse.ArgumentParser(description='Live War Room Dashboard')
    parser.add_argument('--watch', default='war_room_report_*.json',
                       help='File pattern to watch')
    parser.add_argument('--interval', type=int, default=5,
                       help='Refresh interval in seconds')
    
    args = parser.parse_args()
    
    watch_file(args.watch, args.interval)


if __name__ == '__main__':
    main()
