#!/usr/bin/env python3
"""
Baby Picks Presentation View - For Investor Meetings

Shows winning Baby Buckets with:
- Entry/Exit prices
- Realized PnL per trade
- Unrealized PnL for open picks (with live price tracking)
- Progress to TP/SL
- Win rate and performance metrics

Usage:
    python baby_picks_presentation.py           # Show current state
    python baby_picks_presentation.py --live    # With live price updates
"""

import sqlite3
import json
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

DB_PATH = Path("battleground/data/bundle_babies.db")
BINANCE_PRICE_URL = "https://api.binance.com/api/v3/ticker/price"


@dataclass
class PickDisplay:
    """Enhanced pick display for presentation"""
    trade_id: str
    symbol: str
    side: str
    entry_price: float
    current_price: float
    take_profit: float
    stop_loss: float
    entry_time: str
    status: str
    realized_pnl_pct: float
    unrealized_pnl_pct: float
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    
    @property
    def display_pnl(self) -> float:
        """Return appropriate PnL based on status"""
        if self.status == 'CLOSED':
            return self.realized_pnl_pct
        return self.unrealized_pnl_pct
    
    @property
    def pnl_emoji(self) -> str:
        """Emoji based on PnL"""
        pnl = self.display_pnl
        if pnl > 5:
            return "🚀"
        elif pnl > 0:
            return "✅"
        elif pnl > -5:
            return "⚠️"
        else:
            return "🔴"
    
    @property
    def progress_to_tp_pct(self) -> float:
        """Calculate progress % toward take profit"""
        if self.status == 'CLOSED':
            return 100.0 if self.exit_reason == 'TP_HIT' else 0.0
        
        entry = self.entry_price
        tp = self.take_profit
        current = self.current_price
        
        if self.side == 'LONG':
            total_move = tp - entry
            current_move = current - entry
        else:
            total_move = entry - tp
            current_move = entry - current
        
        if total_move == 0:
            return 0
        return min(100, max(0, (current_move / total_move) * 100))
    
    def format_progress_bar(self, width: int = 20) -> str:
        """Create ASCII progress bar"""
        pct = self.progress_to_tp_pct
        filled = int(pct / 100 * width)
        empty = width - filled
        return f"[{'#' * filled}{'-' * empty}] {pct:.1f}%"


def fetch_live_prices(symbols: List[str]) -> Dict[str, float]:
    """Fetch current prices from Binance"""
    prices = {}
    for sym in symbols:
        try:
            sym_clean = sym.replace('/', '')
            resp = requests.get(f"{BINANCE_PRICE_URL}?symbol={sym_clean}", timeout=5)
            if resp.status_code == 200:
                prices[sym] = float(resp.json()["price"])
        except Exception as e:
            print(f"Error fetching {sym}: {e}")
    return prices


def get_all_trades() -> List[PickDisplay]:
    """Get all trades with current pricing"""
    if not DB_PATH.exists():
        return []
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT trade_id, symbol, side, entry_price, take_profit, stop_loss,
               entry_time_est, status, realized_pnl_pct, unrealized_pnl_pct,
               exit_price, exit_reason
        FROM bundle_trades
        ORDER BY entry_time_utc DESC
    """)
    
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    conn.close()
    
    # Get unique symbols for price fetch
    symbols = list(set([row[1] for row in rows if row[1]]))
    live_prices = fetch_live_prices(symbols)
    
    picks = []
    for row in rows:
        data = dict(zip(columns, row))
        symbol = data['symbol']
        
        # Use live price for open trades, exit price for closed
        if data['status'] == 'OPEN' and symbol in live_prices:
            current_price = live_prices[symbol]
            # Recalculate unrealized PnL
            if data['side'] == 'LONG':
                unrealized = ((current_price - data['entry_price']) / data['entry_price']) * 100
            else:
                unrealized = ((data['entry_price'] - current_price) / data['entry_price']) * 100
        elif data['status'] == 'CLOSED' and data['exit_price']:
            current_price = data['exit_price']
            unrealized = 0.0
        else:
            current_price = data['entry_price']
            unrealized = data.get('unrealized_pnl_pct', 0.0)
        
        picks.append(PickDisplay(
            trade_id=data['trade_id'],
            symbol=symbol,
            side=data['side'],
            entry_price=data['entry_price'],
            current_price=current_price,
            take_profit=data['take_profit'],
            stop_loss=data['stop_loss'],
            entry_time=data['entry_time_est'],
            status=data['status'],
            realized_pnl_pct=data.get('realized_pnl_pct', 0.0) or 0.0,
            unrealized_pnl_pct=unrealized,
            exit_price=data.get('exit_price'),
            exit_reason=data.get('exit_reason')
        ))
    
    return picks


def generate_presentation_view():
    """Generate investor presentation view"""
    picks = get_all_trades()
    
    if not picks:
        print("=" * 80)
        print("BABY BUCKETS - WINNING PICKS")
        print("=" * 80)
        print("No trades yet. Waiting for signals...")
        return
    
    open_picks = [p for p in picks if p.status == 'OPEN']
    closed_picks = [p for p in picks if p.status == 'CLOSED']
    
    # Calculate metrics
    total_closed = len(closed_picks)
    winning_closed = len([p for p in closed_picks if p.realized_pnl_pct > 0])
    total_realized_pnl = sum(p.realized_pnl_pct for p in closed_picks)
    total_unrealized_pnl = sum(p.unrealized_pnl_pct for p in open_picks)
    
    print("=" * 80)
    print("BABY BUCKETS - WINNING PICKS")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()
    
    # Performance Summary
    print("PERFORMANCE SUMMARY")
    print("-" * 80)
    print(f"  Closed Trades:    {total_closed}")
    print(f"  Win Rate:         {(winning_closed/total_closed*100) if total_closed > 0 else 0:.1f}%")
    print(f"  Realized P&L:     {total_realized_pnl:+.2f}%")
    print(f"  Open Trades:      {len(open_picks)}")
    print(f"  Unrealized P&L:   {total_unrealized_pnl:+.2f}%")
    print(f"  Combined P&L:     {total_realized_pnl + total_unrealized_pnl:+.2f}%")
    print()
    
    # Open Picks with Unrealized PnL
    if open_picks:
        print("ACTIVE PICKS (With Live Unrealized P&L)")
        print("-" * 80)
        print(f"{'Symbol':<10} {'Side':<6} {'Entry':<12} {'Current':<12} {'Unreal P&L':<12} {'Progress':<25}")
        print("-" * 80)
        
        for pick in open_picks:
            print(f"{pick.symbol:<10} {pick.side:<6} "
                  f"${pick.entry_price:<11.2f} ${pick.current_price:<11.2f} "
                  f"{pick.unrealized_pnl_pct:+.2f}%    "
                  f"{pick.format_progress_bar(15)}")
            print(f"  TP: ${pick.take_profit:.2f} | SL: ${pick.stop_loss:.2f}")
            print()
    
    # Closed Picks with Realized PnL
    if closed_picks:
        print("CLOSED TRADES (Realized P&L)")
        print("-" * 80)
        print(f"{'Symbol':<10} {'Side':<6} {'Entry':<12} {'Exit':<12} {'Real P&L':<12} {'Result':<10}")
        print("-" * 80)
        
        for pick in closed_picks:
            result_mark = "[TP]" if pick.exit_reason == 'TP_HIT' else "[SL]"
            print(f"{pick.symbol:<10} {pick.side:<6} "
                  f"${pick.entry_price:<11.2f} ${pick.exit_price:<11.2f} "
                  f"{pick.realized_pnl_pct:+.2f}%    "
                  f"{result_mark} {pick.exit_reason}")
        print()
    
    # Key Metrics for Investors
    print("KEY INVESTOR METRICS")
    print("-" * 80)
    print(f"  - Average P&L per Trade: {(total_realized_pnl/total_closed) if total_closed > 0 else 0:+.2f}%")
    print(f"  - Best Trade:            {max([p.realized_pnl_pct for p in closed_picks], default=0):+.2f}%")
    print(f"  - Worst Trade:           {min([p.realized_pnl_pct for p in closed_picks], default=0):+.2f}%")
    
    if open_picks:
        print(f"  - Best Open Position:    {max([p.unrealized_pnl_pct for p in open_picks]):+.2f}%")
    
    print()
    print("=" * 80)
    print("* Not financial advice. Past performance does not guarantee future results.")
    print("=" * 80)


def generate_discord_presentation() -> str:
    """Generate Discord-friendly presentation"""
    picks = get_all_trades()
    
    if not picks:
        return """🎯 **BABY BUCKETS - WINNING PICKS**

No active trades. Waiting for signals...
"""
    
    open_picks = [p for p in picks if p.status == 'OPEN']
    closed_picks = [p for p in picks if p.status == 'CLOSED']
    
    total_closed = len(closed_picks)
    winning_closed = len([p for p in closed_picks if p.realized_pnl_pct > 0])
    total_realized_pnl = sum(p.realized_pnl_pct for p in closed_picks)
    total_unrealized_pnl = sum(p.unrealized_pnl_pct for p in open_picks)
    
    msg = f"""**BABY BUCKETS - WINNING PICKS**
*{datetime.now().strftime('%Y-%m-%d %H:%M UTC')}*

**PERFORMANCE SUMMARY**"
```
Closed Trades:    {total_closed}
Win Rate:         {(winning_closed/total_closed*100) if total_closed > 0 else 0:.1f}%
Realized P&L:     {total_realized_pnl:+.2f}%
Open Trades:      {len(open_picks)}
Unrealized P&L:   {total_unrealized_pnl:+.2f}%
Combined P&L:     {total_realized_pnl + total_unrealized_pnl:+.2f}%
```
"""
    
    if open_picks:
        msg += """
**ACTIVE PICKS (Live Unrealized P&L)**
```
Symbol  Side   Entry       Current     Unreal P&L  Progress
"""
        for pick in open_picks:
            msg += f"{pick.symbol:<8} {pick.side:<6} ${pick.entry_price:<10.2f} ${pick.current_price:<10.2f} {pick.unrealized_pnl_pct:+7.2f}%  {pick.progress_to_tp_pct:5.1f}% to TP\n"
        msg += "```\n"
    
    if closed_picks:
        msg += """
**CLOSED TRADES (Realized P&L)**
```
Symbol  Side   Entry       Exit        Real P&L   Result
"""
        for pick in closed_picks[:5]:  # Show last 5
            msg += f"{pick.symbol:<8} {pick.side:<6} ${pick.entry_price:<10.2f} ${pick.exit_price:<10.2f} {pick.realized_pnl_pct:+7.2f}%  {pick.exit_reason}\n"
        msg += "```\n"
    
    msg += """
*Not financial advice. DYOR.*
"""
    return msg


if __name__ == "__main__":
    import sys
    
    if "--discord" in sys.argv:
        print(generate_discord_presentation())
    else:
        generate_presentation_view()
