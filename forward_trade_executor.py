#!/usr/bin/env python3
"""
Forward Trade Executor - Real P&L Tracking for Tier 1 Strategies

Tracks actual trading performance by:
1. Getting live signals from Tier 1 passing strategies
2. Executing simulated trades with entry/TP/SL
3. Tracking real-time P&L (realized + unrealized)
4. Comparing backtest vs forward performance
5. Alerting when trades hit TP/SL or need attention

Usage:
    python forward_trade_executor.py --scan      # Scan for new signals
    python forward_trade_executor.py --update    # Update open trades
    python forward_trade_executor.py --report    # Generate P&L report
"""

import json
import sqlite3
import importlib.util
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import sys

sys.path.insert(0, str(Path(__file__).parent))

from incubator.testing import load_data

# Paths
DB_PATH = Path("incubator/forward_test.db")
TIERED_RESULTS = Path("battleground/data/tiered_backtest_results_20260227_160805.json")
TRADE_LOG = Path("battleground/data/forward_trades_live.json")


@dataclass
class LiveTrade:
    """Active or completed trade"""
    trade_id: str
    strategy_name: str
    agent_id: str
    symbol: str
    side: str  # LONG or SHORT
    
    # Prices
    entry_price: float
    take_profit: float
    stop_loss: float
    current_price: float
    exit_price: Optional[float] = None
    
    # Times
    entry_time: str
    exit_time: Optional[str] = None
    
    # P&L tracking
    unrealized_pnl_pct: float = 0.0
    realized_pnl_pct: float = 0.0
    max_profit_pct: float = 0.0  # Best price reached (for trailing analysis)
    max_loss_pct: float = 0.0    # Worst price reached
    
    # Status
    status: str = "OPEN"  # OPEN, TP_HIT, SL_HIT, MANUAL_CLOSE
    exit_reason: Optional[str] = None
    
    # Progress metrics
    @property
    def progress_to_tp_pct(self) -> float:
        """How far from entry to TP (0-100+)"""
        if self.side == "LONG":
            total_range = self.take_profit - self.entry_price
            current_move = self.current_price - self.entry_price
        else:
            total_range = self.entry_price - self.take_profit
            current_move = self.entry_price - self.current_price
        
        if total_range == 0:
            return 0
        return (current_move / total_range) * 100
    
    @property
    def distance_to_sl_pct(self) -> float:
        """How far from current price to SL as %"""
        if self.side == "LONG":
            return ((self.current_price - self.stop_loss) / self.entry_price) * 100
        else:
            return ((self.stop_loss - self.current_price) / self.entry_price) * 100
    
    @property
    def risk_reward_at_entry(self) -> float:
        """R:R ratio at entry"""
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.take_profit - self.entry_price)
        return reward / risk if risk > 0 else 0
    
    def update_pnl(self):
        """Update unrealized P&L based on current price"""
        if self.side == "LONG":
            self.unrealized_pnl_pct = ((self.current_price - self.entry_price) / self.entry_price) * 100
        else:
            self.unrealized_pnl_pct = ((self.entry_price - self.current_price) / self.entry_price) * 100
        
        # Track max profit/loss
        if self.unrealized_pnl_pct > self.max_profit_pct:
            self.max_profit_pct = self.unrealized_pnl_pct
        if self.unrealized_pnl_pct < self.max_loss_pct:
            self.max_loss_pct = self.unrealized_pnl_pct
    
    def check_exit(self) -> Optional[str]:
        """Check if TP or SL hit, return exit reason if so"""
        if self.side == "LONG":
            if self.current_price >= self.take_profit:
                return "TP_HIT"
            elif self.current_price <= self.stop_loss:
                return "SL_HIT"
        else:
            if self.current_price <= self.take_profit:
                return "TP_HIT"
            elif self.current_price >= self.stop_loss:
                return "SL_HIT"
        return None
    
    def close(self, exit_price: float, reason: str):
        """Close the trade"""
        self.exit_price = exit_price
        self.exit_time = datetime.now(timezone.utc).isoformat()
        self.status = "CLOSED"
        self.exit_reason = reason
        
        # Calculate realized P&L
        if self.side == "LONG":
            self.realized_pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100
        else:
            self.realized_pnl_pct = ((self.entry_price - exit_price) / self.entry_price) * 100
        
        self.unrealized_pnl_pct = 0


class ForwardTradeExecutor:
    """Executes and tracks forward test trades"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self.trade_log = TRADE_LOG
        self._init_db()
        
    def _init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Live trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS live_trades (
                trade_id TEXT PRIMARY KEY,
                strategy_name TEXT,
                agent_id TEXT,
                symbol TEXT,
                side TEXT,
                entry_price REAL,
                take_profit REAL,
                stop_loss REAL,
                current_price REAL,
                exit_price REAL,
                entry_time TEXT,
                exit_time TEXT,
                unrealized_pnl_pct REAL DEFAULT 0,
                realized_pnl_pct REAL DEFAULT 0,
                max_profit_pct REAL DEFAULT 0,
                max_loss_pct REAL DEFAULT 0,
                status TEXT DEFAULT 'OPEN',
                exit_reason TEXT,
                FOREIGN KEY (strategy_name) REFERENCES strategies(strategy_name)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_tier1_strategies(self) -> List[Dict]:
        """Get strategies that passed Tier 1"""
        if not TIERED_RESULTS.exists():
            return []
        
        with open(TIERED_RESULTS, 'r') as f:
            data = json.load(f)
        
        strategies = []
        for name, result in data['results']['tier_1'].items():
            if result.get('passed') and result.get('best_result'):
                strategies.append({
                    'name': name,
                    'agent_id': result.get('source', 'unknown'),
                    'best_pair': result['best_result'].get('pair'),
                    'best_direction': result['best_result'].get('direction', 'LONG'),
                    'backtest_sharpe': result['best_result'].get('sharpe_ratio'),
                    'backtest_wr': result['best_result'].get('win_rate'),
                    'file_path': self._find_strategy_file(name, result.get('source', 'unknown'))
                })
        
        return strategies
    
    def _find_strategy_file(self, name: str, agent_id: str) -> Optional[Path]:
        """Find strategy Python file"""
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
        
        for f in dir_path.glob('*.py'):
            if f.stem == name or name in f.stem:
                return f
        return None
    
    def load_strategy_class(self, file_path: Path):
        """Load strategy class from file"""
        try:
            spec = importlib.util.spec_from_file_location(f"fwd_{file_path.stem}", file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and attr_name.endswith('Strategy'):
                    return attr
            return None
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return None
    
    def get_live_signal(self, strategy_class, symbol: str) -> Optional[Dict]:
        """Get current signal from strategy"""
        try:
            # Load recent data
            data = load_data(symbol, '1h')
            if data is None or len(data) < 100:
                return None
            
            # Get signal
            strategy = strategy_class()
            signals = strategy.generate_signals(data, symbol.replace('/', ''))
            
            if not signals:
                return None
            
            signal = signals[-1] if isinstance(signals, list) else signals
            
            return {
                'direction': getattr(signal, 'direction', 'NEUTRAL'),
                'entry_price': getattr(signal, 'entry_price', data['close'].iloc[-1]),
                'take_profit': getattr(signal, 'take_profit', None),
                'stop_loss': getattr(signal, 'stop_loss', None),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            print(f"Error getting signal: {e}")
            return None
    
    def scan_for_new_trades(self):
        """Scan Tier 1 strategies for new entry signals"""
        strategies = self.get_tier1_strategies()
        new_trades = []
        
        print(f"[SCAN] Checking {len(strategies)} Tier 1 strategies for signals...")
        
        for strat in strategies:
            # Check if we already have an open trade for this strategy
            if self._has_open_trade(strat['name']):
                continue
            
            # Load strategy
            if not strat['file_path']:
                continue
            
            strategy_class = self.load_strategy_class(strat['file_path'])
            if not strategy_class:
                continue
            
            # Get signal
            signal = self.get_live_signal(strategy_class, strat['best_pair'])
            if not signal or signal['direction'] not in ['BUY', 'SELL']:
                continue
            
            # Validate signal has TP/SL
            if not signal['take_profit'] or not signal['stop_loss']:
                continue
            
            # Create trade
            side = "LONG" if signal['direction'] == 'BUY' else "SHORT"
            trade_id = f"{strat['name']}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            
            trade = LiveTrade(
                trade_id=trade_id,
                strategy_name=strat['name'],
                agent_id=strat['agent_id'],
                symbol=strat['best_pair'],
                side=side,
                entry_price=signal['entry_price'],
                take_profit=signal['take_profit'],
                stop_loss=signal['stop_loss'],
                current_price=signal['entry_price'],  # Will update with live price
                entry_time=signal['timestamp']
            )
            
            # Save to DB
            self._save_trade(trade)
            new_trades.append(trade)
            
            print(f"[NEW TRADE] {strat['name']}: {side} {strat['best_pair']} @ {signal['entry_price']:.2f}")
            print(f"  TP: {signal['take_profit']:.2f} | SL: {signal['stop_loss']:.2f}")
            print(f"  R:R = {trade.risk_reward_at_entry:.2f}")
        
        return new_trades
    
    def _has_open_trade(self, strategy_name: str) -> bool:
        """Check if strategy has an open trade"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM live_trades
            WHERE strategy_name = ? AND status = 'OPEN'
        ''', (strategy_name,))
        
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    
    def _save_trade(self, trade: LiveTrade):
        """Save trade to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO live_trades (
                trade_id, strategy_name, agent_id, symbol, side,
                entry_price, take_profit, stop_loss, current_price,
                entry_time, status, unrealized_pnl_pct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade.trade_id, trade.strategy_name, trade.agent_id, trade.symbol, trade.side,
            trade.entry_price, trade.take_profit, trade.stop_loss, trade.current_price,
            trade.entry_time, trade.status, trade.unrealized_pnl_pct
        ))
        
        conn.commit()
        conn.close()
    
    def update_open_trades(self, current_prices: Dict[str, float]):
        """Update all open trades with current market prices"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM live_trades WHERE status = 'OPEN'
        ''')
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        closed_trades = []
        
        for row in rows:
            trade_data = dict(zip(columns, row))
            
            # Get current price
            symbol = trade_data['symbol']
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            
            # Create trade object
            trade = LiveTrade(
                trade_id=trade_data['trade_id'],
                strategy_name=trade_data['strategy_name'],
                agent_id=trade_data['agent_id'],
                symbol=trade_data['symbol'],
                side=trade_data['side'],
                entry_price=trade_data['entry_price'],
                take_profit=trade_data['take_profit'],
                stop_loss=trade_data['stop_loss'],
                current_price=current_price,
                entry_time=trade_data['entry_time'],
                status='OPEN',
                max_profit_pct=trade_data.get('max_profit_pct', 0),
                max_loss_pct=trade_data.get('max_loss_pct', 0)
            )
            
            # Update P&L
            trade.update_pnl()
            
            # Check for exit
            exit_reason = trade.check_exit()
            if exit_reason:
                exit_price = trade.take_profit if exit_reason == "TP_HIT" else trade.stop_loss
                trade.close(exit_price, exit_reason)
                closed_trades.append(trade)
                
                # Update DB
                cursor.execute('''
                    UPDATE live_trades SET
                        exit_price = ?, exit_time = ?, status = ?, exit_reason = ?,
                        realized_pnl_pct = ?, unrealized_pnl_pct = 0
                    WHERE trade_id = ?
                ''', (trade.exit_price, trade.exit_time, trade.status, trade.exit_reason,
                      trade.realized_pnl_pct, trade.trade_id))
                
                print(f"[CLOSED] {trade.strategy_name}: {exit_reason} @ {exit_price:.2f} "
                      f"(P&L: {trade.realized_pnl_pct:+.2f}%)")
            else:
                # Update current price and unrealized P&L
                cursor.execute('''
                    UPDATE live_trades SET
                        current_price = ?, unrealized_pnl_pct = ?,
                        max_profit_pct = ?, max_loss_pct = ?
                    WHERE trade_id = ?
                ''', (trade.current_price, trade.unrealized_pnl_pct,
                      trade.max_profit_pct, trade.max_loss_pct, trade.trade_id))
        
        conn.commit()
        conn.close()
        
        return closed_trades
    
    def generate_pnl_report(self) -> Dict[str, Any]:
        """Generate comprehensive P&L report"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all closed trades
        cursor.execute('''
            SELECT strategy_name, realized_pnl_pct, exit_reason, entry_time
            FROM live_trades WHERE status = 'CLOSED'
            ORDER BY exit_time DESC
        ''')
        closed = cursor.fetchall()
        
        # Get open trades
        cursor.execute('''
            SELECT strategy_name, unrealized_pnl_pct, entry_time, entry_price, current_price
            FROM live_trades WHERE status = 'OPEN'
        ''')
        open_trades = cursor.fetchall()
        
        conn.close()
        
        # Calculate metrics
        realized_pnl = sum(t[1] for t in closed) if closed else 0
        unrealized_pnl = sum(t[1] for t in open_trades) if open_trades else 0
        
        wins = sum(1 for t in closed if t[1] > 0)
        losses = len(closed) - wins
        win_rate = (wins / len(closed) * 100) if closed else 0
        
        # By strategy
        by_strategy = {}
        for t in closed:
            name = t[0]
            if name not in by_strategy:
                by_strategy[name] = {'trades': 0, 'pnl': 0, 'wins': 0}
            by_strategy[name]['trades'] += 1
            by_strategy[name]['pnl'] += t[1]
            if t[1] > 0:
                by_strategy[name]['wins'] += 1
        
        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'summary': {
                'total_closed_trades': len(closed),
                'total_open_trades': len(open_trades),
                'realized_pnl_pct': round(realized_pnl, 2),
                'unrealized_pnl_pct': round(unrealized_pnl, 2),
                'total_pnl_pct': round(realized_pnl + unrealized_pnl, 2),
                'win_rate': round(win_rate, 1),
                'wins': wins,
                'losses': losses
            },
            'closed_trades': [
                {'strategy': t[0], 'pnl': round(t[1], 2), 'reason': t[2], 'time': t[3]}
                for t in closed[:20]
            ],
            'open_trades': [
                {'strategy': t[0], 'unrealized': round(t[1], 2), 'entry': t[3], 'current': t[4]}
                for t in open_trades
            ],
            'by_strategy': {
                name: {
                    'trades': data['trades'],
                    'pnl': round(data['pnl'], 2),
                    'win_rate': round(data['wins'] / data['trades'] * 100, 1) if data['trades'] > 0 else 0
                }
                for name, data in by_strategy.items()
            }
        }
        
        # Save report
        with open(self.trade_log, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report


# CLI
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Forward Trade Executor')
    parser.add_argument('--scan', action='store_true', help='Scan for new trades')
    parser.add_argument('--update', action='store_true', help='Update open trades')
    parser.add_argument('--report', action='store_true', help='Generate P&L report')
    
    args = parser.parse_args()
    
    executor = ForwardTradeExecutor()
    
    if args.scan:
        new_trades = executor.scan_for_new_trades()
        print(f"\n[SCAN COMPLETE] Found {len(new_trades)} new trades")
    
    if args.update:
        # In real implementation, get live prices from exchange/API
        # For now, placeholder
        current_prices = {
            'BTC/USDT': 85000,  # Would be live price
            'ETH/USDT': 3200,
            'SOL/USDT': 180
        }
        closed = executor.update_open_trades(current_prices)
        print(f"\n[UPDATE COMPLETE] Closed {len(closed)} trades")
    
    if args.report:
        report = executor.generate_pnl_report()
        print("\n" + "="*60)
        print("P&L REPORT")
        print("="*60)
        print(f"Realized P&L: {report['summary']['realized_pnl_pct']:+.2f}%")
        print(f"Unrealized P&L: {report['summary']['unrealized_pnl_pct']:+.2f}%")
        print(f"Total P&L: {report['summary']['total_pnl_pct']:+.2f}%")
        print(f"Win Rate: {report['summary']['win_rate']:.1f}% ({report['summary']['wins']}W/{report['summary']['losses']}L)")
        print(f"\nTop Performing Strategies:")
        sorted_strats = sorted(
            report['by_strategy'].items(),
            key=lambda x: x[1]['pnl'],
            reverse=True
        )[:5]
        for name, data in sorted_strats:
            print(f"  {name[:30]:<30} | P&L: {data['pnl']:+.2f}% | WR: {data['win_rate']:.1f}%")
