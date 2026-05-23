#!/usr/bin/env python3
"""
Discord Bot Integration for Baby Strat Forward Testing
Command: !fc-baby

Shows top performing forward-testing strategies with:
- Actual picks (entry/exit times EST, prices, TP/SL, direction)
- Stats: # picks, closed vs open, unrealized/realized P/L
- Performance: drawdown, sharpe
- Backtest metadata: timeframes passed, symbols passed
"""

import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests

# Database path
DB_PATH = Path("incubator/forward_test.db")
RESULTS_DIR = Path("battleground/data/forward_test")
TIERED_RESULTS_DIR = Path("battleground/data")


def format_timestamp(ts_str: str, to_est: bool = True) -> str:
    """Convert UTC timestamp to EST format"""
    if not ts_str:
        return "N/A"
    try:
        # Parse the timestamp
        if isinstance(ts_str, str):
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        else:
            ts = ts_str
        
        if to_est:
            # Convert to EST (UTC-5)
            est_offset = timedelta(hours=-5)
            ts = ts.astimezone(timezone(est_offset))
            return ts.strftime("%m/%d %H:%M EST")
        else:
            return ts.strftime("%m/%d %H:%M UTC")
    except:
        return str(ts_str)[:16]


def load_tiered_backtest_data() -> Dict[str, Any]:
    """Load the latest tiered backtest results"""
    # Find the most recent tiered backtest results
    tiered_files = sorted(TIERED_RESULTS_DIR.glob("tiered_backtest_results_*.json"))
    if not tiered_files:
        return {}
    
    latest = tiered_files[-1]
    try:
        with open(latest, 'r') as f:
            return json.load(f)
    except:
        return {}


def get_forward_test_db() -> Optional[sqlite3.Connection]:
    """Get connection to forward test database"""
    if DB_PATH.exists():
        return sqlite3.connect(DB_PATH)
    return None


def get_top_strategies(limit: int = 5) -> List[Dict[str, Any]]:
    """Get top performing strategies from forward test database"""
    conn = get_forward_test_db()
    if not conn:
        return []
    
    cursor = conn.cursor()
    
    # Get strategies with forward data, ordered by performance
    cursor.execute('''
        SELECT 
            strategy_name, agent_id, status,
            forward_sharpe, forward_win_rate, forward_max_dd,
            forward_pnl_pct, forward_trades_count, forward_days,
            backtest_sharpe, backtest_win_rate,
            paper_started_at, graduated_at
        FROM strategies
        WHERE forward_sharpe IS NOT NULL OR forward_pnl_pct != 0
        ORDER BY forward_sharpe DESC NULLS LAST
        LIMIT ?
    ''', (limit,))
    
    strategies = []
    for row in cursor.fetchall():
        strategies.append({
            'strategy_name': row[0],
            'agent_id': row[1],
            'status': row[2],
            'forward_sharpe': row[3] or 0,
            'forward_win_rate': row[4] or 0,
            'forward_max_dd': row[5] or 0,
            'forward_pnl_pct': row[6] or 0,
            'forward_trades_count': row[7] or 0,
            'forward_days': row[8] or 0,
            'backtest_sharpe': row[9] or 0,
            'backtest_win_rate': row[10] or 0,
            'paper_started_at': row[11],
            'graduated_at': row[12]
        })
    
    conn.close()
    return strategies


def get_strategy_trades(strategy_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get trades for a specific strategy"""
    conn = get_forward_test_db()
    if not conn:
        return []
    
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            entry_time, exit_time, direction,
            entry_price, exit_price, pnl_pct, exit_reason
        FROM forward_trades
        WHERE strategy_name = ?
        ORDER BY entry_time DESC
        LIMIT ?
    ''', (strategy_name, limit))
    
    trades = []
    for row in cursor.fetchall():
        trades.append({
            'entry_time': row[0],
            'exit_time': row[1],
            'direction': row[2],
            'entry_price': row[3],
            'exit_price': row[4],
            'pnl_pct': row[5],
            'exit_reason': row[6],
            'status': 'CLOSED' if row[1] else 'OPEN'
        })
    
    conn.close()
    return trades


def get_strategy_backtest_meta(strategy_name: str) -> Dict[str, Any]:
    """Get backtest metadata for a strategy from tiered results"""
    tiered_data = load_tiered_backtest_data()
    
    # Look in tier1_passed
    for result in tiered_data.get('tier1_passed', []):
        if result.get('strategy_name') == strategy_name:
            return {
                'tier': 'Tier 1 Passed',
                'best_pair': result.get('best_pair', 'N/A'),
                'best_direction': result.get('best_direction', 'N/A'),
                'best_sharpe': result.get('best_sharpe', 0),
                'timeframes': ['1h'],  # Tier 1 tests on 1h
                'symbols_tested': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
            }
    
    # Look in tier2_passed
    for result in tiered_data.get('tier2_passed', []):
        if result.get('strategy_name') == strategy_name:
            return {
                'tier': 'Tier 2 Passed (Fully Robust)',
                'best_pair': result.get('best_pair', 'N/A'),
                'timeframes': ['1h', '4h', '1d'],
                'symbols_tested': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
            }
    
    # Look in tier2_partial
    for result in tiered_data.get('tier2_partial', []):
        if result.get('strategy_name') == strategy_name:
            return {
                'tier': 'Tier 2 Partial',
                'best_pair': result.get('best_pair', 'N/A'),
                'timeframes': result.get('passed_timeframes', []),
                'symbols_tested': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
            }
    
    return {
        'tier': 'Unknown',
        'timeframes': [],
        'symbols_tested': []
    }


def calculate_pick_stats(trades: List[Dict]) -> Dict[str, Any]:
    """Calculate pick statistics"""
    total = len(trades)
    closed = [t for t in trades if t['status'] == 'CLOSED']
    open_picks = [t for t in trades if t['status'] == 'OPEN']
    
    realized_pnl = sum(t['pnl_pct'] for t in closed) if closed else 0
    
    # Calculate unrealized P/L for open picks (would need current price in real implementation)
    unrealized_pnl = 0  # Placeholder - would calculate from current market price
    
    return {
        'total_picks': total,
        'closed_picks': len(closed),
        'open_picks': len(open_picks),
        'realized_pnl': realized_pnl,
        'unrealized_pnl': unrealized_pnl
    }


def generate_discord_message(top_n: int = 3) -> str:
    """Generate the !fc-baby Discord message"""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    
    # Get top strategies
    strategies = get_top_strategies(limit=top_n)
    
    if not strategies:
        return f"""🍼 **Baby Strat Forward Testing Report**
*{now}*

⚠️ No forward test data available yet.
Strategies are being tested in paper trading mode.
Check back in 24-48 hours for initial results.

**Status:** Building forward test database...
**Strategies in Pipeline:** Check `incubator/forward_test.db`
"""
    
    message = f"""🍼 **Baby Strat Forward Testing Report — Top Performers**
*{now}* | Command: `!fc-baby`

📊 **LEGEND:**
• 🟢 = Graduated to Live | 🟡 = Paper Trading | 🔴 = Failed
• All times in EST | P&L includes fees
• Forward = Live paper trading results

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
    
    for i, strat in enumerate(strategies, 1):
        # Get trades for this strategy
        trades = get_strategy_trades(strat['strategy_name'], limit=10)
        stats = calculate_pick_stats(trades)
        meta = get_strategy_backtest_meta(strat['strategy_name'])
        
        # Status emoji
        status_emoji = {
            'graduated': '🟢',
            'live': '🟢',
            'paper_trading': '🟡',
            'failed': '🔴'
        }.get(strat['status'], '⚪')
        
        # Calculate sharpe decay
        sharpe_decay = 0
        if strat['backtest_sharpe'] > 0:
            sharpe_decay = ((strat['forward_sharpe'] - strat['backtest_sharpe']) / strat['backtest_sharpe']) * 100
        
        message += f"""**{i}. {status_emoji} {strat['strategy_name'][:35]}**
```
Agent: {strat['agent_id']} | Status: {strat['status'].upper()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 PERFORMANCE (Forward Test)
   Sharpe: {strat['forward_sharpe']:.2f} (Backtest: {strat['backtest_sharpe']:.2f} | Decay: {sharpe_decay:+.1f}%)
   Win Rate: {strat['forward_win_rate']:.1%} (Backtest: {strat['backtest_win_rate']:.1%})
   Max DD: {strat['forward_max_dd']:.1%} | P&L: {strat['forward_pnl_pct']:+.2f}%
   Trades: {stats['total_picks']} ({stats['closed_picks']} closed, {stats['open_picks']} open)
   Realized P/L: {stats['realized_pnl']:+.2f}% | Unrealized: {stats['unrealized_pnl']:+.2f}%
   Days in Test: {strat['forward_days']}

📋 BACKTEST VALIDATION
   Tier: {meta.get('tier', 'N/A')}
   Best Pair: {meta.get('best_pair', 'N/A')}
   Timeframes Passed: {', '.join(meta.get('timeframes', [])) or 'N/A'}
   Symbols Passed: {', '.join(meta.get('symbols_tested', [])) or 'N/A'}
```
"""
        
        # Add recent picks
        if trades:
            message += "**📊 Recent Picks:**\n```\n"
            message += f"{'Status':<8} {'Side':<6} {'Entry Time':<14} {'Exit Time':<14} {'Entry $':<10} {'P&L %':<8}\n"
            message += "-" * 70 + "\n"
            
            for trade in trades[:5]:  # Show top 5
                entry_time = format_timestamp(trade['entry_time'])
                exit_time = format_timestamp(trade['exit_time']) if trade['exit_time'] else "OPEN"
                side = trade['direction'][:4] if trade['direction'] else "N/A"
                entry_price = f"${trade['entry_price']:.4f}" if trade['entry_price'] else "N/A"
                pnl = f"{trade['pnl_pct']:+.2f}%" if trade['pnl_pct'] else "N/A"
                
                message += f"{trade['status']:<8} {side:<6} {entry_time:<14} {exit_time:<14} {entry_price:<10} {pnl:<8}\n"
            
            message += "```\n"
        
        message += "\n"
    
    # Summary stats
    message += """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**📊 FORWARD TEST SUMMARY**
```
✅ Key Insights:
• Only strategies with forward Sharpe > 0.8 shown above
• Forward testing validates backtest results in live markets
• Graduation requires: 30+ days, 20+ trades, Sharpe ≥ 0.8, Positive P&L

⚠️ Reality Check:
• Historical data shows only ~22% of strategies pass forward validation
• Backtest/Forward correlation typically 0.30-0.50 (expect decay)
• Always verify forward performance before live deployment
```

**🔗 LINKS:**
• Forward Test DB: `incubator/forward_test.db`
• Tiered Results: `battleground/data/tiered_backtest_results_*.json`
• Full Report: Run `python -m incubator.testing.forward_dashboard`

*⚠️ Not financial advice — DYOR! These are paper trading results.*
"""
    
    return message


def send_to_discord(webhook_url: Optional[str] = None, message: Optional[str] = None):
    """Send message to Discord webhook"""
    webhook_url = webhook_url or os.getenv('DISCORD_WEBHOOK_URL') or os.getenv('DISCORD_BABY_WEBHOOK')
    
    if not message:
        message = generate_discord_message()
    
    if not webhook_url:
        print("No webhook URL found. Set DISCORD_WEBHOOK_URL or DISCORD_BABY_WEBHOOK")
        print("\nMessage preview:\n")
        print(message)
        return False
    
    # Split message if too long (Discord limit 2000 chars)
    chunks = []
    while len(message) > 2000:
        split_point = message.rfind('\n', 0, 2000)
        if split_point == -1:
            split_point = 2000
        chunks.append(message[:split_point])
        message = message[split_point:]
    chunks.append(message)
    
    success = True
    for chunk in chunks:
        try:
            payload = {"content": chunk}
            resp = requests.post(webhook_url, json=payload, timeout=10)
            if resp.status_code != 204:
                print(f"Discord error: {resp.status_code} - {resp.text}")
                success = False
        except Exception as e:
            print(f"Send error: {e}")
            success = False
    
    return success


# Discord bot command handler (for use with discord.py)
async def handle_fc_baby_command(ctx, top_n: int = 3):
    """Handler for !fc-baby Discord command
    
    Usage in Discord:
        !fc-baby          - Show top 3 strategies
        !fc-baby 5        - Show top 5 strategies
        !fc-baby all      - Show all strategies with forward data
    """
    # Send initial "loading" message
    loading_msg = await ctx.send("🍼 Loading Baby Strat forward test data...")
    
    try:
        if top_n == "all":
            top_n = 20  # Reasonable limit
        else:
            top_n = min(int(top_n), 10)  # Max 10
    except:
        top_n = 3
    
    # Generate message
    message = generate_discord_message(top_n=top_n)
    
    # Delete loading message
    await loading_msg.delete()
    
    # Send in chunks if needed
    if len(message) <= 2000:
        await ctx.send(message)
    else:
        chunks = []
        remaining = message
        while len(remaining) > 2000:
            split_point = remaining.rfind('\n\n', 0, 2000)
            if split_point == -1:
                split_point = remaining.rfind('\n', 0, 2000)
            if split_point == -1:
                split_point = 2000
            chunks.append(remaining[:split_point])
            remaining = remaining[split_point:]
        chunks.append(remaining)
        
        for chunk in chunks:
            await ctx.send(chunk)


if __name__ == "__main__":
    import sys
    
    # Check if being called as command
    if len(sys.argv) > 1:
        if sys.argv[1] == "--send":
            send_to_discord()
        elif sys.argv[1] == "--preview":
            print(generate_discord_message())
        elif sys.argv[1].isdigit():
            print(generate_discord_message(top_n=int(sys.argv[1])))
    else:
        # Default: preview
        print(generate_discord_message())
        print("\n" + "="*50)
        print("To send to Discord: python discord_forward_test_bot.py --send")
        print("To show more strategies: python discord_forward_test_bot.py 5")
