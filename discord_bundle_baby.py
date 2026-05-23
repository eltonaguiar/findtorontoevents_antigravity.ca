#!/usr/bin/env python3
"""
Discord Command: !fc-bundle

Shows TOP PERFORMING Bundle Babies with recent picks
This is THE RECOMMENDED command for tracking strategy performance

Usage:
    !fc-bundle          - Show top bundles with recent picks
    !fc-bundle audit    - Full audit trail
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any
import os
import requests

from forward_metrics_compat import forward_win_rate_percent

REPO_ROOT = Path(__file__).resolve().parent
BUNDLE_DB = REPO_ROOT / "battleground" / "data" / "bundle_babies.db"
BATTLEGROUND = REPO_ROOT / "battleground" / "data" / "baby_strats_dashboard.json"


def get_bundle_babies() -> List[Dict]:
    """Get bundle babies from database, sorted by forward performance"""
    if not BUNDLE_DB.exists():
        return []
    
    conn = sqlite3.connect(BUNDLE_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM bundle_babies
        ORDER BY 
            CASE 
                WHEN forward_trades >= 100 THEN forward_sharpe 
                ELSE backtest_sharpe * 0.5 
            END DESC,
            forward_trades DESC
    ''')
    
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    conn.close()
    
    bundles = []
    for row in rows:
        data = dict(zip(columns, row))
        data['strategy_names'] = json.loads(data['strategy_names'])
        bundles.append(data)
    
    return bundles


def get_bundle_trades(bundle_id: str, limit: int = 5) -> List[Dict]:
    """Get recent trades for bundle"""
    if not BUNDLE_DB.exists():
        return []
    
    conn = sqlite3.connect(BUNDLE_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM bundle_trades
        WHERE bundle_id = ?
        ORDER BY entry_time_est DESC
        LIMIT ?
    ''', (bundle_id, limit))
    
    columns = [desc[0] for desc in cursor.description]
    trades = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    
    return trades


def format_timestamp(ts: str) -> str:
    """Format timestamp for display"""
    if not ts:
        return "N/A"
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return dt.strftime('%m/%d %H:%M')
    except:
        return ts[:16]


def calculate_progress_to_tp(trade: Dict) -> float:
    """Calculate progress % toward take profit"""
    try:
        entry = trade['entry_price']
        tp = trade['take_profit']
        current = trade.get('current_price', entry)
        side = trade['side']
        
        if side == 'LONG':
            total_move = tp - entry
            current_move = current - entry
        else:
            total_move = entry - tp
            current_move = entry - current
        
        if total_move == 0:
            return 0
        return min(100, max(0, (current_move / total_move) * 100))
    except:
        return 0


def generate_discord_message() -> str:
    """Generate Discord message for bundle babies - THE RECOMMENDED VIEW"""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    bundles = get_bundle_babies()
    
    if not bundles:
        return f"""[BUNDLE BABIES - TOP TIER STRATEGIES]
*{now}* | Command: `!fc-bundle`

[ALERT] No active bundles found.
Run: `python bundle_baby_system.py --create`
"""
    
    msg = f"""[BUNDLE BABIES - TOP TIER STRATEGIES]
*{now}* | Command: `!fc-bundle`

[RECOMMENDED] THIS IS THE TOP COMMAND FOR STRATEGY TRACKING
Shows forward-tested bundles with live picks

================================================================================

"""
    
    for i, bundle in enumerate(bundles[:3], 1):
        fw_trades = bundle.get('forward_trades', 0)
        is_early_stage = fw_trades < 100
        
        # Status indicators
        if is_early_stage:
            warning = "[WARNING] EARLY STAGE - Less than 100 forward trades"
            stage_emoji = "[NEW]"
        elif bundle['forward_status'] == 'graduated':
            warning = "[PROVEN] GRADUATED - Proven forward performance"
            stage_emoji = "[PROVEN]"
        else:
            warning = "[TRACKING] Building forward history"
            stage_emoji = "[TRACKING]"
        
        # Calculate win rate decay
        bt_wr = bundle['backtest_win_rate']
        fw_wr = forward_win_rate_percent(bundle)
        decay = fw_wr - bt_wr if fw_trades > 0 else None
        
        msg += f"""**{i}. {stage_emoji} {bundle['name']}**
```
Bundle ID: {bundle['bundle_id']}
Classification: {bundle['symbol_scope']} | {bundle['timeframe_scope']} | {bundle['direction_bias']}
Strategies: {', '.join(bundle['strategy_names'][:2])}
{warning}

BACKTEST (Historical):
  Sharpe: {bundle['backtest_sharpe']:.2f}
  Win Rate: {bundle['backtest_win_rate']:.1f}%
  Max DD: {bundle['backtest_max_dd']:.1f}%
  Trades: {bundle['backtest_trades']}

FORWARD (Live Paper Trading - THE MAIN THING):
  Status: {bundle['forward_status'].upper()}
  Total Trades: {fw_trades} {"(Need 100+ for reliability)" if is_early_stage else ""}
  Sharpe: {bundle.get('forward_sharpe', 0):.2f}
  Win Rate: {fw_wr:.1f}%{f" (Decay: {decay:+.1f}% vs backtest)" if decay is not None else ""}
  Realized P&L: {bundle.get('forward_realized_pnl', 0):+.2f}%
  Unrealized P&L: {bundle.get('forward_unrealized_pnl', 0):+.2f}%
```
"""
        
        # Get recent picks
        trades = get_bundle_trades(bundle['bundle_id'], 5)
        if trades:
            msg += "**Recent Picks:**\n```\n"
            msg += f"{'Status':<8} {'Side':<6} {'Entry (EST)':<14} {'Progress':<12} {'P&L':<10}\n"
            msg += "-" * 54 + "\n"
            
            for t in trades:
                status = t['status']
                side = t['side'][:5]
                entry = format_timestamp(t['entry_time_est'])
                
                if status == 'CLOSED':
                    pnl = f"{t['realized_pnl_pct']:+.2f}%"
                    progress = t.get('exit_reason', 'N/A')
                else:
                    pnl = f"{t['unrealized_pnl_pct']:+.2f}%"
                    progress_pct = calculate_progress_to_tp(t)
                    progress = f"{progress_pct:.0f}% to TP"
                
                msg += f"{status:<8} {side:<6} {entry:<14} {progress:<12} {pnl:<10}\n"
            
            msg += "```\n"
        else:
            msg += "**Recent Picks:** No trades yet. Waiting for signals...\n\n"
        
        msg += "\n"
    
    msg += """================================================================================
[IMPORTANT NOTES]

[WARNING] EARLY STAGE:
Bundles with <100 forward trades are still proving themselves.
Backtest results often decay 20-50% in forward testing.
Wait for 100+ trades before trusting performance metrics.

[STRATEGY] RECOMMENDED APPROACH:
1. Focus on bundles with 100+ forward trades
2. Look for forward WR > 55% and Sharpe > 1.0
3. Check win rate decay vs backtest (lower is better)
4. Use TP/SL progress to manage open positions

================================================================================
[LINKS & COMMANDS]
- Full Audit: `!fc-bundle audit <bundle_id>`
- Legacy View: `!fc-baby` (shows individual strategies)
- Database: battleground/data/bundle_babies.db
- Tracker: python bundle_baby_live_tracker.py --watch

*[WARNING] Not financial advice - DYOR!*
"""
    
    return msg


def send_to_discord(webhook_url: str = None):
    """Send to Discord webhook"""
    webhook_url = webhook_url or os.getenv('DISCORD_BUNDLE_WEBHOOK') or os.getenv('DISCORD_WEBHOOK_URL')
    
    msg = generate_discord_message()
    
    if not webhook_url:
        print(msg)
        return False
    
    # Split if too long
    chunks = []
    while len(msg) > 2000:
        split = msg.rfind('\n\n', 0, 2000)
        if split == -1:
            split = msg.rfind('\n', 0, 2000)
        if split == -1:
            split = 2000
        chunks.append(msg[:split])
        msg = msg[split:]
    chunks.append(msg)
    
    import time as _time
    for chunk in chunks:
        for _attempt in range(3):
            try:
                r = requests.post(webhook_url, json={"content": chunk}, timeout=10)
                if r.status_code in (200, 204):
                    break
                if r.status_code == 429:
                    _time.sleep(r.json().get("retry_after", 3))
                    continue
                if _attempt < 2:
                    _time.sleep(2 * (_attempt + 1))
                    continue
                break
            except Exception as e:
                if _attempt == 2:
                    print(f"Error sending after 3 attempts: {e}")
                else:
                    _time.sleep(2 * (_attempt + 1))
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--send', action='store_true', help='Send to Discord')
    parser.add_argument('--preview', action='store_true', help='Preview in terminal')
    
    args = parser.parse_args()
    
    if args.send:
        send_to_discord()
    else:
        print(generate_discord_message())
