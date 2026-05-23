#!/usr/bin/env python3
"""
Bundle Baby System
==================

Categorizes strategies into "bundle babies" based on their characteristics:
- Symbol scope: Single vs Multi-symbol
- Timeframe scope: Single vs Multi-timeframe  
- Direction: Long vs Short vs Both

Bundles are:
1. Backtested across all tiers
2. Forward-tested (THE MAIN THING)
3. Ranked by forward performance
4. Displayed at TOP of battleground

Full audit trail:
- Entry/Exit timestamps (EST)
- Entry/Exit prices
- TP/SL levels
- P&L (realized + unrealized)
- Win rate, Sharpe, Drawdown
"""

import json
import sqlite3
import importlib.util
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import sys

sys.path.insert(0, str(Path(__file__).parent))
from incubator.testing import run_tier1_backtest, run_tier2_backtest, run_full_backtest, check_pass_criteria
from forward_metrics_compat import forward_win_rate_percent

# Database paths
DB_PATH = Path("incubator/forward_test.db")
BUNDLE_DB_PATH = Path("battleground/data/bundle_babies.db")
BATTLEGROUND_FILE = Path("battleground/data/baby_strats_dashboard.json")
BUNDLE_RESULTS_FILE = Path("battleground/data/bundle_baby_results.json")


class SymbolScope(Enum):
    SINGLE = "single_symbol"      # Works on only 1 specific symbol
    MULTI = "multi_symbol"        # Works on BTC/ETH/SOL (Tier 1 passers)
    BROAD = "broad"               # Works on 4+ symbols


class TimeframeScope(Enum):
    SINGLE = "single_timeframe"   # Only works on 1h OR 4h OR 1d
    MULTI = "multi_timeframe"     # Passes Tier 2 (works on 1h+4h+1d)
    PARTIAL = "partial_timeframe" # Passes 1-2 timeframes


class DirectionBias(Enum):
    LONG = "long_only"
    SHORT = "short_only"
    BOTH = "both_directions"


@dataclass
class BundleBaby:
    """A bundle of strategies with similar characteristics"""
    bundle_id: str
    name: str
    
    # Classification
    symbol_scope: SymbolScope
    timeframe_scope: TimeframeScope
    direction_bias: DirectionBias
    
    # Member strategies
    strategy_names: List[str]
    
    # Best performing config
    best_symbol: str
    best_timeframe: str
    best_direction: str
    
    # Backtest metrics
    backtest_sharpe: float
    backtest_win_rate: float
    backtest_max_dd: float
    backtest_trades: int
    backtest_total_return: float
    
    # Forward test metrics (THE MAIN THING)
    forward_status: str  # 'paper', 'graduated', 'failed'
    forward_start_date: Optional[str]
    forward_sharpe: float
    forward_win_rate: float
    forward_max_dd: float
    forward_trades: int
    forward_realized_pnl: float
    forward_unrealized_pnl: float
    
    # Quality score
    quality_score: float
    rank: int
    
    # Timestamps
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'bundle_id': self.bundle_id,
            'name': self.name,
            'classification': {
                'symbol_scope': self.symbol_scope.value,
                'timeframe_scope': self.timeframe_scope.value,
                'direction_bias': self.direction_bias.value
            },
            'strategies': self.strategy_names,
            'best_config': {
                'symbol': self.best_symbol,
                'timeframe': self.best_timeframe,
                'direction': self.best_direction
            },
            'backtest': {
                'sharpe': self.backtest_sharpe,
                'win_rate': self.backtest_win_rate,
                'max_dd': self.backtest_max_dd,
                'trades': self.backtest_trades,
                'total_return': self.backtest_total_return
            },
            'forward': {
                'status': self.forward_status,
                'start_date': self.forward_start_date,
                'sharpe': self.forward_sharpe,
                'win_rate': self.forward_win_rate,
                'max_dd': self.forward_max_dd,
                'trades': self.forward_trades,
                'realized_pnl': self.forward_realized_pnl,
                'unrealized_pnl': self.forward_unrealized_pnl
            },
            'quality_score': self.quality_score,
            'rank': self.rank
        }


@dataclass
class BundleTrade:
    """Individual trade record for bundle audit trail"""
    trade_id: str
    bundle_id: str
    strategy_name: str
    
    # Entry
    entry_time_utc: str
    entry_time_est: str
    entry_price: float
    side: str  # LONG or SHORT
    symbol: str
    
    # Exit
    exit_time_utc: Optional[str]
    exit_time_est: Optional[str]
    exit_price: Optional[float]
    exit_reason: Optional[str]  # TP_HIT, SL_HIT, MANUAL, TIMEOUT
    
    # TP/SL
    take_profit: float
    stop_loss: float
    tp_distance_remaining_pct: float  # % distance still to TP
    sl_distance_remaining_pct: float  # % distance still to SL
    
    # P&L
    realized_pnl_pct: float
    unrealized_pnl_pct: float
    max_profit_pct: float  # Best price reached
    max_loss_pct: float    # Worst price reached
    
    # Status
    status: str  # OPEN, CLOSED
    
    # Metadata
    bars_held: int
    time_in_trade_minutes: int


class BundleBabySystem:
    """Main system for managing bundle babies"""
    
    def __init__(self):
        self.db_path = BUNDLE_DB_PATH
        self._init_db()
        
    def _init_db(self):
        """Initialize bundle baby database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Bundle definitions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bundle_babies (
                bundle_id TEXT PRIMARY KEY,
                name TEXT,
                symbol_scope TEXT,
                timeframe_scope TEXT,
                direction_bias TEXT,
                strategy_names TEXT,  -- JSON array
                best_symbol TEXT,
                best_timeframe TEXT,
                best_direction TEXT,
                backtest_sharpe REAL,
                backtest_win_rate REAL,
                backtest_max_dd REAL,
                backtest_trades INTEGER,
                backtest_total_return REAL,
                forward_status TEXT DEFAULT 'paper',
                forward_start_date TEXT,
                forward_sharpe REAL DEFAULT 0,
                forward_win_rate REAL DEFAULT 0,
                forward_max_dd REAL DEFAULT 0,
                forward_trades INTEGER DEFAULT 0,
                forward_realized_pnl REAL DEFAULT 0,
                forward_unrealized_pnl REAL DEFAULT 0,
                quality_score REAL DEFAULT 0,
                rank INTEGER,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        # Trade audit trail
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bundle_trades (
                trade_id TEXT PRIMARY KEY,
                bundle_id TEXT,
                strategy_name TEXT,
                entry_time_utc TEXT,
                entry_time_est TEXT,
                entry_price REAL,
                side TEXT,
                symbol TEXT,
                exit_time_utc TEXT,
                exit_time_est TEXT,
                exit_price REAL,
                exit_reason TEXT,
                take_profit REAL,
                stop_loss REAL,
                tp_distance_remaining_pct REAL,
                sl_distance_remaining_pct REAL,
                realized_pnl_pct REAL DEFAULT 0,
                unrealized_pnl_pct REAL DEFAULT 0,
                max_profit_pct REAL DEFAULT 0,
                max_loss_pct REAL DEFAULT 0,
                status TEXT,
                bars_held INTEGER,
                time_in_trade_minutes INTEGER,
                FOREIGN KEY (bundle_id) REFERENCES bundle_babies(bundle_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def categorize_strategy(self, strategy_name: str, tiered_results: Dict) -> Tuple[SymbolScope, TimeframeScope, DirectionBias]:
        """
        Categorize a strategy based on tiered backtest results
        """
        tier1 = tiered_results.get('results', {}).get('tier_1', {}).get(strategy_name, {})
        tier2 = tiered_results.get('results', {}).get('tier_2', {}).get(strategy_name, {})
        
        # Symbol scope
        passed_pairs = tier1.get('passed_pairs', [])
        if len(passed_pairs) >= 4:
            symbol_scope = SymbolScope.BROAD
        elif len(passed_pairs) >= 2:
            symbol_scope = SymbolScope.MULTI
        else:
            symbol_scope = SymbolScope.SINGLE
        
        # Timeframe scope
        if tier2.get('fully_robust'):
            timeframe_scope = TimeframeScope.MULTI
        elif tier2.get('passed_timeframes'):
            timeframe_scope = TimeframeScope.PARTIAL
        else:
            timeframe_scope = TimeframeScope.SINGLE
        
        # Direction bias
        best_result = tier1.get('best_result', {})
        direction = best_result.get('direction', 'LONG')
        if direction == 'LONG':
            direction_bias = DirectionBias.LONG
        elif direction == 'SHORT':
            direction_bias = DirectionBias.SHORT
        else:
            direction_bias = DirectionBias.BOTH
        
        return symbol_scope, timeframe_scope, direction_bias
    
    def create_bundle_babies(self, tiered_results_path: Path):
        """
        Create bundle babies from tiered backtest results
        Group strategies by their classification
        """
        with open(tiered_results_path, 'r') as f:
            tiered = json.load(f)
        
        # Categorize all Tier 1 passing strategies
        categorized = {
            (SymbolScope.SINGLE, TimeframeScope.SINGLE, DirectionBias.LONG): [],
            (SymbolScope.SINGLE, TimeframeScope.SINGLE, DirectionBias.SHORT): [],
            (SymbolScope.SINGLE, TimeframeScope.MULTI, DirectionBias.LONG): [],
            (SymbolScope.MULTI, TimeframeScope.SINGLE, DirectionBias.LONG): [],
            (SymbolScope.MULTI, TimeframeScope.MULTI, DirectionBias.LONG): [],
            (SymbolScope.BROAD, TimeframeScope.MULTI, DirectionBias.BOTH): [],
        }
        
        for name, result in tiered.get('results', {}).get('tier_1', {}).items():
            if not result.get('passed'):
                continue
            
            scope, tf, direction = self.categorize_strategy(name, tiered)
            key = (scope, tf, direction)
            
            if key not in categorized:
                categorized[key] = []
            
            categorized[key].append({
                'name': name,
                'result': result,
                'scope': scope,
                'tf': tf,
                'direction': direction
            })
        
        # Create bundle babies from categories
        bundles = []
        for (scope, tf, direction), strategies in categorized.items():
            if not strategies:
                continue
            
            # Sort by backtest sharpe
            strategies.sort(key=lambda x: x['result'].get('best_result', {}).get('sharpe_ratio', 0), reverse=True)
            
            # Take top 3 for the bundle
            top_strategies = strategies[:3]
            
            best = top_strategies[0]['result']['best_result']
            
            now = datetime.now(timezone.utc).isoformat()
            bundle = BundleBaby(
                bundle_id=f"bundle_{scope.value}_{tf.value}_{direction.value}_{datetime.now().strftime('%Y%m%d')}",
                name=f"{scope.value.title()} {tf.value.title()} {direction.value.title()}",
                symbol_scope=scope,
                timeframe_scope=tf,
                direction_bias=direction,
                strategy_names=[s['name'] for s in top_strategies],
                best_symbol=best.get('pair', 'BTC/USDT'),
                best_timeframe='1h',
                best_direction=best.get('direction', 'LONG'),
                backtest_sharpe=best.get('sharpe_ratio', 0),
                backtest_win_rate=best.get('win_rate', 0),
                backtest_max_dd=best.get('max_drawdown', 0),
                backtest_trades=best.get('trades', 0),
                backtest_total_return=best.get('total_return', 0),
                forward_status='paper',
                forward_start_date=None,
                forward_sharpe=0,
                forward_win_rate=0,
                forward_max_dd=0,
                forward_trades=0,
                forward_realized_pnl=0,
                forward_unrealized_pnl=0,
                quality_score=0,
                rank=0,
                created_at=now,
                updated_at=now
            )
            
            bundles.append(bundle)
        
        # Save to DB
        self._save_bundles(bundles)
        
        return bundles
    
    def _save_bundles(self, bundles: List[BundleBaby]):
        """Save bundles to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now(timezone.utc).isoformat()
        
        for bundle in bundles:
            cursor.execute('''
                INSERT OR REPLACE INTO bundle_babies (
                    bundle_id, name, symbol_scope, timeframe_scope, direction_bias,
                    strategy_names, best_symbol, best_timeframe, best_direction,
                    backtest_sharpe, backtest_win_rate, backtest_max_dd, backtest_trades,
                    backtest_total_return, forward_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                bundle.bundle_id, bundle.name, bundle.symbol_scope.value,
                bundle.timeframe_scope.value, bundle.direction_bias.value,
                json.dumps(bundle.strategy_names), bundle.best_symbol,
                bundle.best_timeframe, bundle.best_direction,
                bundle.backtest_sharpe, bundle.backtest_win_rate,
                bundle.backtest_max_dd, bundle.backtest_trades,
                bundle.backtest_total_return, bundle.forward_status,
                now, now
            ))
        
        conn.commit()
        conn.close()
        print(f"Saved {len(bundles)} bundle babies to database")
    
    def record_trade(self, trade: BundleTrade):
        """Record a trade to the audit trail"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO bundle_trades (
                trade_id, bundle_id, strategy_name, entry_time_utc, entry_time_est,
                entry_price, side, symbol, exit_time_utc, exit_time_est, exit_price,
                exit_reason, take_profit, stop_loss, tp_distance_remaining_pct,
                sl_distance_remaining_pct, realized_pnl_pct, unrealized_pnl_pct,
                max_profit_pct, max_loss_pct, status, bars_held, time_in_trade_minutes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade.trade_id, trade.bundle_id, trade.strategy_name,
            trade.entry_time_utc, trade.entry_time_est, trade.entry_price,
            trade.side, trade.symbol, trade.exit_time_utc, trade.exit_time_est,
            trade.exit_price, trade.exit_reason, trade.take_profit, trade.stop_loss,
            trade.tp_distance_remaining_pct, trade.sl_distance_remaining_pct,
            trade.realized_pnl_pct, trade.unrealized_pnl_pct, trade.max_profit_pct,
            trade.max_loss_pct, trade.status, trade.bars_held, trade.time_in_trade_minutes
        ))
        
        conn.commit()
        conn.close()
    
    def get_bundle_trades(self, bundle_id: str, limit: int = 50) -> List[BundleTrade]:
        """Get audit trail for a bundle"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM bundle_trades
            WHERE bundle_id = ?
            ORDER BY entry_time_utc DESC
            LIMIT ?
        ''', (bundle_id, limit))
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        trades = []
        for row in rows:
            data = dict(zip(columns, row))
            trades.append(BundleTrade(**data))
        
        return trades
    
    def update_forward_metrics(self, bundle_id: str):
        """Update forward metrics from trade history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate metrics
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'CLOSED' THEN 1 ELSE 0 END) as closed,
                SUM(CASE WHEN status = 'CLOSED' AND realized_pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN status = 'CLOSED' THEN realized_pnl_pct ELSE 0 END) as realized,
                SUM(CASE WHEN status = 'OPEN' THEN unrealized_pnl_pct ELSE 0 END) as unrealized
            FROM bundle_trades
            WHERE bundle_id = ?
        ''', (bundle_id,))
        
        row = cursor.fetchone()
        total, closed, wins, realized, unrealized = row
        
        win_rate = (wins / closed * 100) if closed else 0
        
        # Update bundle
        cursor.execute('''
            UPDATE bundle_babies SET
                forward_trades = ?,
                forward_win_rate = ?,
                forward_realized_pnl = ?,
                forward_unrealized_pnl = ?,
                updated_at = ?
            WHERE bundle_id = ?
        ''', (total, win_rate, realized or 0, unrealized or 0,
              datetime.now(timezone.utc).isoformat(), bundle_id))
        
        conn.commit()
        conn.close()
    
    def rank_bundles(self) -> List[BundleBaby]:
        """Rank all bundles by forward performance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM bundle_babies
            ORDER BY forward_sharpe DESC, forward_win_rate DESC
        ''')
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        bundles = []
        for i, row in enumerate(rows):
            data = dict(zip(columns, row))
            data['strategy_names'] = json.loads(data['strategy_names'])
            data['symbol_scope'] = SymbolScope(data['symbol_scope'])
            data['timeframe_scope'] = TimeframeScope(data['timeframe_scope'])
            data['direction_bias'] = DirectionBias(data['direction_bias'])
            data['rank'] = i + 1
            bundles.append(BundleBaby(**data))

        return bundles

    @staticmethod
    def evaluate_gate(stats: dict) -> dict:
        """
        Evaluate an 8-check validation gate for a bundle's forward-test stats.
        Returns: {"status": str, "checks_passed": int, "check_details": dict}

        Statuses: COLLECTING (<10 trades) -> TESTING (1-4 checks) -> MARGINAL (5-6) -> PROVEN (7) -> ELITE (8)
        """
        checks = {}

        trades = stats.get("forward_trades", 0)
        wr = forward_win_rate_percent(stats)
        sharpe = stats.get("forward_sharpe", 0)
        max_dd = stats.get("forward_max_dd", 0)
        pnl = stats.get("forward_realized_pnl", 0)

        # Gate 1: Minimum trades (statistical significance)
        checks["min_trades"] = {"passed": trades >= 10, "value": trades, "threshold": 10}
        # Gate 2: Win rate > 50%
        checks["win_rate"] = {"passed": wr > 50, "value": wr, "threshold": 50}
        # Gate 3: Sharpe > 0.5
        checks["sharpe"] = {"passed": sharpe > 0.5, "value": sharpe, "threshold": 0.5}
        # Gate 4: Max drawdown > -20% (not too deep)
        checks["max_drawdown"] = {"passed": max_dd > -20, "value": max_dd, "threshold": -20}
        # Gate 5: Positive realized PnL
        checks["positive_pnl"] = {"passed": pnl > 0, "value": pnl, "threshold": 0}
        # Gate 6: Win rate > 55% (higher bar)
        checks["strong_wr"] = {"passed": wr > 55, "value": wr, "threshold": 55}
        # Gate 7: Sharpe > 1.0 (strong risk-adjusted)
        checks["strong_sharpe"] = {"passed": sharpe > 1.0, "value": sharpe, "threshold": 1.0}
        # Gate 8: Max DD > -10% (tight risk)
        checks["tight_drawdown"] = {"passed": max_dd > -10, "value": max_dd, "threshold": -10}

        passed = sum(1 for c in checks.values() if c["passed"])

        if trades < 10:
            status = "COLLECTING"
        elif passed <= 4:
            status = "TESTING"
        elif passed <= 6:
            status = "MARGINAL"
        elif passed == 7:
            status = "PROVEN"
        else:
            status = "ELITE"

        return {"status": status, "checks_passed": passed, "check_details": checks}

    def update_battleground(self):
        """Update battleground dashboard with bundles at TOP"""
        bundles = self.rank_bundles()
        
        # Format for battleground
        bundle_data = {
            'section': 'BUNDLE_BABIES_TOP',
            'description': 'Forward-tested strategy bundles - THE MAIN THING',
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'bundles': [b.to_dict() for b in bundles[:10]],  # Top 10
            'audit_trail_note': 'Full trade history in bundle_babies.db table: bundle_trades'
        }
        
        # Load existing battleground
        if BATTLEGROUND_FILE.exists():
            with open(BATTLEGROUND_FILE, 'r') as f:
                battleground = json.load(f)
        else:
            battleground = {}
        
        # Insert bundles at TOP
        sections = battleground.get('sections', [])
        
        # Remove existing bundle section if present
        sections = [s for s in sections if s.get('section') != 'BUNDLE_BABIES_TOP']
        
        # Add at beginning
        sections.insert(0, bundle_data)
        battleground['sections'] = sections
        battleground['total_bundles'] = len(bundles)
        battleground['last_updated'] = datetime.now(timezone.utc).isoformat()
        
        with open(BATTLEGROUND_FILE, 'w') as f:
            json.dump(battleground, f, indent=2)
        
        print(f"Battleground updated with {len(bundles)} bundles at TOP")
    
    def generate_audit_report(self, bundle_id: str) -> str:
        """Generate human-readable audit report for a bundle"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get bundle info
        cursor.execute('SELECT * FROM bundle_babies WHERE bundle_id = ?', (bundle_id,))
        bundle_row = cursor.fetchone()
        
        if not bundle_row:
            return "Bundle not found"
        
        columns = [desc[0] for desc in cursor.description]
        bundle = dict(zip(columns, bundle_row))
        
        # Get trades
        cursor.execute('''
            SELECT * FROM bundle_trades
            WHERE bundle_id = ?
            ORDER BY entry_time_est DESC
        ''', (bundle_id,))
        
        trade_columns = [desc[0] for desc in cursor.description]
        trades = [dict(zip(trade_columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        
        # Generate report
        report = []
        report.append("="*80)
        report.append(f"BUNDLE BABY AUDIT REPORT: {bundle['name']}")
        report.append(f"Bundle ID: {bundle_id}")
        report.append("="*80)
        
        report.append(f"\n[CLASSIFICATION]")
        report.append(f"  Symbol Scope: {bundle['symbol_scope']}")
        report.append(f"  Timeframe Scope: {bundle['timeframe_scope']}")
        report.append(f"  Direction: {bundle['direction_bias']}")
        report.append(f"  Strategies: {json.loads(bundle['strategy_names'])}")
        
        report.append(f"\n[BACKTEST METRICS]")
        report.append(f"  Sharpe: {bundle['backtest_sharpe']:.2f}")
        report.append(f"  Win Rate: {bundle['backtest_win_rate']:.1f}%")
        report.append(f"  Max DD: {bundle['backtest_max_dd']:.1f}%")
        report.append(f"  Trades: {bundle['backtest_trades']}")
        
        report.append(f"\n[FORWARD METRICS - THE MAIN THING]")
        report.append(f"  Status: {bundle['forward_status'].upper()}")
        report.append(f"  Sharpe: {bundle.get('forward_sharpe', 0):.2f}")
        report.append(f"  Win Rate: {forward_win_rate_percent(bundle):.1f}%")
        report.append(f"  Realized P&L: {bundle.get('forward_realized_pnl', 0):+.2f}%")
        report.append(f"  Unrealized P&L: {bundle.get('forward_unrealized_pnl', 0):+.2f}%")
        report.append(f"  Total Trades: {bundle.get('forward_trades', 0)}")
        
        report.append(f"\n[TRADE AUDIT TRAIL] ({len(trades)} trades)")
        report.append("-"*80)
        report.append(f"{'Status':<8} {'Side':<6} {'Entry (EST)':<20} {'Exit (EST)':<20} {'P&L':<10} {'Exit Reason'}")
        report.append("-"*80)
        
        for t in trades[:20]:  # Show last 20
            status = t['status']
            side = t['side'][:5]
            entry = t['entry_time_est'][:19] if t['entry_time_est'] else 'N/A'
            exit_t = t['exit_time_est'][:19] if t['exit_time_est'] else 'OPEN'
            pnl = f"{t['realized_pnl_pct']:+.2f}%" if status == 'CLOSED' else f"{t['unrealized_pnl_pct']:+.2f}%"
            reason = t['exit_reason'] or ''
            
            report.append(f"{status:<8} {side:<6} {entry:<20} {exit_t:<20} {pnl:<10} {reason}")
        
        report.append("\n" + "="*80)
        
        return "\n".join(report)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Bundle Baby System')
    parser.add_argument('--create', action='store_true', help='Create bundles from tiered results')
    parser.add_argument('--tiered-file', default='battleground/data/tiered_backtest_results_20260227_160805.json')
    parser.add_argument('--update-battleground', action='store_true', help='Update battleground with bundles')
    parser.add_argument('--audit', type=str, help='Generate audit report for bundle ID')
    parser.add_argument('--list', action='store_true', help='List all bundles')
    
    args = parser.parse_args()
    
    system = BundleBabySystem()
    
    if args.create:
        bundles = system.create_bundle_babies(Path(args.tiered_file))
        print(f"\nCreated {len(bundles)} bundle babies:")
        for b in bundles:
            print(f"  {b.name}: {b.strategy_names}")
    
    if args.update_battleground:
        system.update_battleground()
    
    if args.audit:
        report = system.generate_audit_report(args.audit)
        print(report)
    
    if args.list:
        bundles = system.rank_bundles()
        print("\n" + "="*80)
        print("BUNDLE BABIES RANKED BY FORWARD PERFORMANCE")
        print("="*80)
        for b in bundles:
            print(f"\n{b.rank}. {b.name}")
            print(f"   ID: {b.bundle_id}")
            print(f"   Classification: {b.symbol_scope.value} | {b.timeframe_scope.value} | {b.direction_bias.value}")
            print(f"   Backtest: Sharpe {b.backtest_sharpe:.2f}, WR {b.backtest_win_rate:.1f}%")
            print(f"   Forward: Status {b.forward_status}, Trades {b.forward_trades}")


if __name__ == "__main__":
    main()
