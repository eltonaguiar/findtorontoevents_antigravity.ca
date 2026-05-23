#!/usr/bin/env python3
"""
Bundle Baby Live Tracker

Actively tracks and records picks from bundle babies in real-time.
- Scans bundle strategies for live signals
- Records trades to audit trail
- Updates forward metrics
- Alerts on new picks
- Tracks TP/SL progress

Usage:
    python bundle_baby_live_tracker.py --scan     # Scan for new picks
    python bundle_baby_live_tracker.py --update   # Update open trades
    python bundle_baby_live_tracker.py --watch    # Continuous monitoring
"""

import json
import sqlite3
import importlib.util
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import sys
import requests

sys.path.insert(0, str(Path(__file__).parent))
from incubator.testing import load_data
from bundle_baby_system import BundleBabySystem, BundleTrade, SymbolScope, TimeframeScope, DirectionBias

# Paths
BUNDLE_DB = Path("battleground/data/bundle_babies.db")
DISCORD_WEBHOOK = None  # Set via env var


@dataclass
class LivePick:
    """Current live pick from a bundle strategy"""
    bundle_id: str
    strategy_name: str
    symbol: str
    side: str  # LONG or SHORT
    entry_price: float
    take_profit: float
    stop_loss: float
    confidence: float
    timestamp: str
    
    def to_dict(self) -> Dict:
        return {
            'bundle_id': self.bundle_id,
            'strategy_name': self.strategy_name,
            'symbol': self.symbol,
            'side': self.side,
            'entry_price': self.entry_price,
            'take_profit': self.take_profit,
            'stop_loss': self.stop_loss,
            'confidence': self.confidence,
            'timestamp': self.timestamp
        }


class BundleBabyLiveTracker:
    """Live tracking system for bundle baby picks"""
    
    def __init__(self):
        self.bundle_system = BundleBabySystem()
        self.db_path = BUNDLE_DB
        
    def get_active_bundles(self) -> List[Dict]:
        """Get all active bundles from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM bundle_babies
            WHERE forward_status IN ('paper', 'graduated')
            ORDER BY backtest_sharpe DESC
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
    
    def load_strategy_class(self, strategy_name: str, agent_id: str):
        """Load strategy class from file"""
        # Map agent to directory
        dirs = {
            'baby': Path('baby_strategies'),
            'codex': Path('incubator/agents/codex_gpt5'),
            'cursor': Path('incubator/agents/cursor_ai'),
            'opus': Path('incubator/agents/claude_opus_batch'),
            'alpha': Path('incubator/agents/team_alpha'),
            'web': Path('incubator/agents/web_ai'),
        }
        
        dir_path = dirs.get(agent_id)
        if not dir_path:
            return None
        
        # Find file
        strategy_file = None
        for f in dir_path.glob('*.py'):
            if f.stem == strategy_name or strategy_name in f.stem:
                strategy_file = f
                break
        
        if not strategy_file:
            return None
        
        try:
            spec = importlib.util.spec_from_file_location(f"live_{strategy_name}", strategy_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and attr_name.endswith('Strategy'):
                    return attr
            return None
        except Exception as e:
            print(f"Error loading {strategy_name}: {e}")
            return None
    
    def get_strategy_signal(self, strategy_name: str, agent_id: str, symbol: str) -> Optional[LivePick]:
        """Get current signal from a strategy"""
        strategy_class = self.load_strategy_class(strategy_name, agent_id)
        if not strategy_class:
            return None
        
        try:
            # Load data
            data = load_data(symbol, '1h')
            if data is None or len(data) < 100:
                return None
            
            # Get signal
            strategy = strategy_class()
            signals = strategy.generate_signals(data, symbol.replace('/', ''))
            
            if not signals:
                return None
            
            signal = signals[-1] if isinstance(signals, list) else signals
            direction = getattr(signal, 'direction', 'NEUTRAL')
            
            if direction not in ['BUY', 'SELL']:
                return None
            
            side = 'LONG' if direction == 'BUY' else 'SHORT'
            
            # Get prices
            entry = getattr(signal, 'entry_price', data['close'].iloc[-1])
            tp = getattr(signal, 'take_profit', None)
            sl = getattr(signal, 'stop_loss', None)
            
            # Validate TP/SL exist
            if not tp or not sl:
                # Calculate default TP/SL (5%)
                if side == 'LONG':
                    tp = entry * 1.05
                    sl = entry * 0.95
                else:
                    tp = entry * 0.95
                    sl = entry * 1.05
            
            return LivePick(
                bundle_id='',  # Will be set by caller
                strategy_name=strategy_name,
                symbol=symbol,
                side=side,
                entry_price=entry,
                take_profit=tp,
                stop_loss=sl,
                confidence=0.8,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
        except Exception as e:
            print(f"Error getting signal from {strategy_name}: {e}")
            return None
    
    def utc_to_est(self, utc_str: str) -> str:
        """Convert UTC to EST"""
        try:
            utc = datetime.fromisoformat(utc_str.replace('Z', '+00:00'))
            est = utc.astimezone(timezone(timedelta(hours=-5)))
            return est.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return utc_str
    
    def has_open_trade(self, bundle_id: str, strategy_name: str) -> bool:
        """Check if strategy already has an open trade in this bundle"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(*) FROM bundle_trades
            WHERE bundle_id = ? AND strategy_name = ? AND status = 'OPEN'
        ''', (bundle_id, strategy_name))

        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def has_recent_trade(self, bundle_id: str, strategy_name: str, entry_price: float, side: str, cooldown_hours: int = 24) -> bool:
        """Prevent duplicate trades: skip if same signal was recorded within cooldown period"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = (datetime.now(timezone.utc) - timedelta(hours=cooldown_hours)).isoformat()

        cursor.execute('''
            SELECT COUNT(*) FROM bundle_trades
            WHERE bundle_id = ? AND strategy_name = ? AND side = ?
              AND ABS(entry_price - ?) / entry_price < 0.005
              AND entry_time_utc > ?
        ''', (bundle_id, strategy_name, side, entry_price, cutoff))

        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    
    def record_new_pick(self, pick: LivePick) -> bool:
        """Record a new pick to the audit trail"""
        if self.has_open_trade(pick.bundle_id, pick.strategy_name):
            return False

        # Prevent duplicate signals (same price/side within 24h cooldown)
        if self.has_recent_trade(pick.bundle_id, pick.strategy_name, pick.entry_price, pick.side):
            print(f"    [DEDUP] {pick.strategy_name}: Same signal already recorded within 24h")
            return False
        
        trade_id = f"{pick.bundle_id}_{pick.strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Calculate initial distances
        if pick.side == 'LONG':
            tp_distance = ((pick.take_profit - pick.entry_price) / pick.entry_price) * 100
            sl_distance = ((pick.entry_price - pick.stop_loss) / pick.entry_price) * 100
        else:
            tp_distance = ((pick.entry_price - pick.take_profit) / pick.entry_price) * 100
            sl_distance = ((pick.stop_loss - pick.entry_price) / pick.entry_price) * 100
        
        trade = BundleTrade(
            trade_id=trade_id,
            bundle_id=pick.bundle_id,
            strategy_name=pick.strategy_name,
            entry_time_utc=pick.timestamp,
            entry_time_est=self.utc_to_est(pick.timestamp),
            entry_price=pick.entry_price,
            side=pick.side,
            symbol=pick.symbol,
            exit_time_utc=None,
            exit_time_est=None,
            exit_price=None,
            exit_reason=None,
            take_profit=pick.take_profit,
            stop_loss=pick.stop_loss,
            tp_distance_remaining_pct=tp_distance,
            sl_distance_remaining_pct=sl_distance,
            realized_pnl_pct=0.0,
            unrealized_pnl_pct=0.0,
            max_profit_pct=0.0,
            max_loss_pct=0.0,
            status='OPEN',
            bars_held=0,
            time_in_trade_minutes=0
        )
        
        # Save to database
        self.bundle_system.record_trade(trade)
        
        # Update bundle forward metrics
        self.update_bundle_metrics(pick.bundle_id)
        
        print(f"[NEW PICK] {pick.strategy_name}: {pick.side} {pick.symbol} @ {pick.entry_price:.2f}")
        print(f"  TP: {pick.take_profit:.2f} | SL: {pick.stop_loss:.2f}")
        print(f"  Trade ID: {trade_id}")
        
        return True
    
    def update_bundle_metrics(self, bundle_id: str):
        """Update forward metrics for a bundle"""
        self.bundle_system.update_forward_metrics(bundle_id)
    
    def scan_for_new_picks(self) -> List[LivePick]:
        """Scan all bundle strategies for new picks"""
        bundles = self.get_active_bundles()
        new_picks = []
        
        print(f"[SCAN] Checking {len(bundles)} bundles for new picks...")
        print("="*80)
        
        for bundle in bundles:
            bundle_id = bundle['bundle_id']
            print(f"\nBundle: {bundle['name']} ({bundle_id})")
            print(f"  Classification: {bundle['symbol_scope']} | {bundle['timeframe_scope']} | {bundle['direction_bias']}")
            print(f"  Strategies: {bundle['strategy_names']}")
            
            for strategy_name in bundle['strategy_names']:
                # Skip if already has open trade
                if self.has_open_trade(bundle_id, strategy_name):
                    print(f"    [SKIP] {strategy_name}: Already has open trade")
                    continue
                
                # Get signal (try to get agent_id or use default)
                agent_id = bundle.get('agent_id', 'cursor')  # Default to cursor
                pick = self.get_strategy_signal(
                    strategy_name, 
                    agent_id, 
                    bundle['best_symbol']
                )
                
                if pick:
                    pick.bundle_id = bundle_id
                    
                    # Check direction matches bundle bias
                    bundle_direction = bundle['direction_bias']
                    if bundle_direction == 'long_only' and pick.side != 'LONG':
                        print(f"    [FILTER] {strategy_name}: SHORT signal filtered (long-only bundle)")
                        continue
                    if bundle_direction == 'short_only' and pick.side != 'SHORT':
                        print(f"    [FILTER] {strategy_name}: LONG signal filtered (short-only bundle)")
                        continue
                    
                    # Record the pick
                    if self.record_new_pick(pick):
                        new_picks.append(pick)
                else:
                    print(f"    [NO SIGNAL] {strategy_name}: No entry signal")
        
        print("\n" + "="*80)
        print(f"[SCAN COMPLETE] Found {len(new_picks)} new picks")
        
        return new_picks
    
    def update_open_trades(self, current_prices: Dict[str, float]):
        """Update all open trades with current prices"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM bundle_trades WHERE status = 'OPEN'
        ''')
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        closed_trades = []
        
        for row in rows:
            trade_data = dict(zip(columns, row))
            symbol = trade_data['symbol']
            
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            side = trade_data['side']
            entry_price = trade_data['entry_price']
            tp = trade_data['take_profit']
            sl = trade_data['stop_loss']
            
            # Calculate P&L
            if side == 'LONG':
                unrealized = ((current_price - entry_price) / entry_price) * 100
                tp_hit = current_price >= tp
                sl_hit = current_price <= sl
            else:
                unrealized = ((entry_price - current_price) / entry_price) * 100
                tp_hit = current_price <= tp
                sl_hit = current_price >= sl
            
            # Update distances
            if side == 'LONG':
                tp_dist = max(0, ((tp - current_price) / entry_price) * 100)
                sl_dist = max(0, ((current_price - sl) / entry_price) * 100)
            else:
                tp_dist = max(0, ((current_price - tp) / entry_price) * 100)
                sl_dist = max(0, ((sl - current_price) / entry_price) * 100)
            
            # Check for exit
            if tp_hit or sl_hit:
                exit_price = tp if tp_hit else sl
                exit_reason = 'TP_HIT' if tp_hit else 'SL_HIT'
                realized = unrealized
                
                # Close trade
                cursor.execute('''
                    UPDATE bundle_trades SET
                        status = 'CLOSED',
                        exit_time_utc = ?,
                        exit_time_est = ?,
                        exit_price = ?,
                        exit_reason = ?,
                        realized_pnl_pct = ?,
                        unrealized_pnl_pct = 0,
                        tp_distance_remaining_pct = 0,
                        sl_distance_remaining_pct = 0
                    WHERE trade_id = ?
                ''', (
                    datetime.now(timezone.utc).isoformat(),
                    self.utc_to_est(datetime.now(timezone.utc).isoformat()),
                    exit_price,
                    exit_reason,
                    realized,
                    trade_data['trade_id']
                ))
                
                closed_trades.append({
                    'trade_id': trade_data['trade_id'],
                    'strategy': trade_data['strategy_name'],
                    'reason': exit_reason,
                    'pnl': realized
                })
                
                print(f"[CLOSED] {trade_data['strategy_name']}: {exit_reason} @ {exit_price:.2f} (P&L: {realized:+.2f}%)")
            else:
                # Update open trade
                max_profit = max(trade_data.get('max_profit_pct', 0), unrealized)
                max_loss = min(trade_data.get('max_loss_pct', 0), unrealized)
                
                entry_time = datetime.fromisoformat(trade_data['entry_time_utc'].replace('Z', '+00:00'))
                time_in_trade = int((datetime.now(timezone.utc) - entry_time).total_seconds() / 60)
                
                cursor.execute('''
                    UPDATE bundle_trades SET
                        unrealized_pnl_pct = ?,
                        max_profit_pct = ?,
                        max_loss_pct = ?,
                        tp_distance_remaining_pct = ?,
                        sl_distance_remaining_pct = ?,
                        time_in_trade_minutes = ?
                    WHERE trade_id = ?
                ''', (unrealized, max_profit, max_loss, tp_dist, sl_dist, time_in_trade, trade_data['trade_id']))
        
        conn.commit()
        conn.close()
        
        # Update bundle metrics for affected bundles
        for trade in closed_trades:
            bundle_id = trade['trade_id'].split('_')[0] + '_' + trade['trade_id'].split('_')[1]
            self.update_bundle_metrics(bundle_id)
        
        return closed_trades
    
    def watch_mode(self, interval_seconds: int = 300):
        """Continuous monitoring mode"""
        print("[WATCH MODE] Starting continuous monitoring...")
        print(f"Scan interval: {interval_seconds} seconds")
        print("Press Ctrl+C to exit\n")
        
        while True:
            try:
                # Scan for new picks
                new_picks = self.scan_for_new_picks()
                
                if new_picks:
                    print(f"\n[ALERT] {len(new_picks)} new picks detected!")
                    for pick in new_picks:
                        print(f"  → {pick.strategy_name}: {pick.side} {pick.symbol}")
                
                # Update open trades (would use real prices in production)
                # For now, placeholder prices
                current_prices = {
                    'BTC/USDT': 85000,  # Would be live
                    'ETH/USDT': 3200,
                    'SOL/USDT': 180
                }
                closed = self.update_open_trades(current_prices)
                
                if closed:
                    print(f"\n[UPDATE] {len(closed)} trades closed")
                
                # Update battleground
                self.bundle_system.update_battleground()
                
                print(f"\n[OK] Next scan in {interval_seconds}s...")
                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                print("\n[EXIT] Watch mode stopped")
                break
            except Exception as e:
                print(f"\n[ERROR] {e}")
                time.sleep(10)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Bundle Baby Live Tracker')
    parser.add_argument('--scan', action='store_true', help='Scan for new picks')
    parser.add_argument('--update', action='store_true', help='Update open trades')
    parser.add_argument('--watch', action='store_true', help='Continuous monitoring')
    parser.add_argument('--interval', type=int, default=300, help='Scan interval (seconds)')
    
    args = parser.parse_args()
    
    tracker = BundleBabyLiveTracker()
    
    if args.watch:
        tracker.watch_mode(args.interval)
    elif args.scan:
        tracker.scan_for_new_picks()
    elif args.update:
        # Placeholder prices - in production would fetch from exchange
        current_prices = {
            'BTC/USDT': 85000,
            'ETH/USDT': 3200,
            'SOL/USDT': 180
        }
        closed = tracker.update_open_trades(current_prices)
        print(f"Updated {len(closed)} closed trades")
    else:
        print("Usage:")
        print("  python bundle_baby_live_tracker.py --scan     # Scan once")
        print("  python bundle_baby_live_tracker.py --update   # Update open trades")
        print("  python bundle_baby_live_tracker.py --watch    # Continuous monitoring")


if __name__ == "__main__":
    main()
