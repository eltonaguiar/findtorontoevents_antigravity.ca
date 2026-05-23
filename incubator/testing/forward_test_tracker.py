"""
Forward Testing Tracker for Baby Strat Incubator

Tracks strategies from paper trading through live deployment.
Ensures comprehensive forward-test validation before graduation.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import sqlite3


@dataclass
class ForwardTestRecord:
    """Single forward test measurement"""
    timestamp: str
    strategy_name: str
    agent_id: str
    
    # Performance metrics
    pnl_pct: float
    trades_count: int
    win_rate: Optional[float]
    sharpe: Optional[float]
    max_drawdown: Optional[float]
    
    # Forward test status
    status: str  # 'paper_trading', 'forward_testing', 'graduated', 'failed'
    days_in_test: int
    
    # Metadata
    data_source: str
    notes: str = ""


@dataclass
class StrategyGraduationCriteria:
    """Criteria for graduating a strategy from paper to live"""
    min_forward_days: int = 45
    min_trades: int = 50
    min_win_rate: float = 0.50
    min_sharpe: float = 1.0
    max_drawdown: float = 0.20
    min_pnl_positive: bool = True
    min_pnl_pct: float = 5.0
    # Walk-forward stability (added 2026-05-18). A single 45-day snapshot lets a
    # strategy that was merely *lucky* for one window graduate, then die live —
    # how the live book filled with no-edge strategies (reports/
    # EDGE_VERDICT_2026-05-18.md: method_a_score eff 1.14 -> 0.42 the next
    # window; COT year-unstable). Require the forward period, split into
    # n_stability_windows equal chunks, to be net-positive in >=
    # min_window_consistency of them. Skipped (backward-compatible) when the
    # caller does not supply a `window_pnls` list.
    min_window_consistency: float = 0.60
    n_stability_windows: int = 4

    def check(self, metrics: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Check if metrics meet graduation criteria. Returns (passed, reasons)"""
        passed = True
        reasons = []

        if metrics.get('days_in_test', 0) < self.min_forward_days:
            passed = False
            reasons.append(f"Insufficient days: {metrics.get('days_in_test', 0)}/{self.min_forward_days}")

        if metrics.get('trades_count', 0) < self.min_trades:
            passed = False
            reasons.append(f"Insufficient trades: {metrics.get('trades_count', 0)}/{self.min_trades}")

        if metrics.get('win_rate', 0) < self.min_win_rate:
            passed = False
            reasons.append(f"Win rate too low: {metrics.get('win_rate', 0):.2%}/{self.min_win_rate:.2%}")

        if metrics.get('sharpe', 0) < self.min_sharpe:
            passed = False
            reasons.append(f"Sharpe too low: {metrics.get('sharpe', 0):.2f}/{self.min_sharpe}")

        if metrics.get('max_drawdown', 1) > self.max_drawdown:
            passed = False
            reasons.append(f"Drawdown too high: {metrics.get('max_drawdown', 0):.2%}/{self.max_drawdown:.2%}")

        if self.min_pnl_positive and metrics.get('pnl_pct', 0) <= 0:
            passed = False
            reasons.append(f"P&L not positive: {metrics.get('pnl_pct', 0):.4f}%")

        if metrics.get('pnl_pct', 0) < self.min_pnl_pct:
            passed = False
            reasons.append(f"P&L too low: {metrics.get('pnl_pct', 0):.2f}%/{self.min_pnl_pct:.1f}%")

        # Walk-forward stability gate. `window_pnls` = forward-test pnl split
        # into chronological chunks (the caller computes it from forward_trades).
        # A strategy must be net-positive in a majority of chunks, not just
        # net-positive overall — a lucky single window must not graduate.
        window_pnls = metrics.get('window_pnls')
        if window_pnls and len(window_pnls) >= self.n_stability_windows:
            positive = sum(1 for w in window_pnls if w > 0)
            frac = positive / len(window_pnls)
            if frac < self.min_window_consistency:
                passed = False
                reasons.append(
                    f"Walk-forward unstable: net-positive in only "
                    f"{positive}/{len(window_pnls)} windows "
                    f"({frac:.0%} < {self.min_window_consistency:.0%}) — "
                    f"single-window luck, not a durable edge")

        return passed, reasons


@dataclass
class EarlyHatchCriteria:
    """
    Fast-track graduation for exceptional baby strategies.

    A baby strategy can "hatch early" and get promoted to the audit dashboard
    if it demonstrates EXCEPTIONAL performance in a shorter window.
    This prevents proven winners from sitting idle for 45 days.

    Requirements are STRICTER than normal graduation on quality metrics
    but RELAXED on time/trade count to allow early promotion.

    Added 2026-03-16: No baby strategies had graduated despite 150 in paper
    trading and 107 with live picks — the 45-day minimum was blocking all of them.
    """
    # Relaxed time/count requirements
    min_forward_days: int = 7          # 7 days minimum (not 45)
    min_trades: int = 15               # 15 trades minimum (not 50)

    # STRICTER quality requirements (must be exceptional to hatch early)
    min_win_rate: float = 0.55         # 55% WR — realistic threshold (62.7% WR + Sharpe 5.57 should graduate)
    min_sharpe: float = 1.5            # Sharpe 1.5 (not 1.0) — must show strong risk-adjusted returns
    max_drawdown: float = 0.10         # Max 10% DD (not 20%) — must be safe
    min_pnl_pct: float = 3.0           # At least 3% positive PnL
    min_profit_factor: float = 1.5     # PF must be at least 1.5 (not just positive)

    # Bonus criteria (any one of these can further reduce min_trades to 10)
    walk_forward_validated: bool = False  # If walk-forward passed, needs only 10 trades
    consensus_agreement: int = 0         # If 3+ systems agree, needs only 10 trades

    def check(self, metrics: Dict[str, Any]) -> Tuple[bool, List[str], str]:
        """
        Check if metrics meet early hatch criteria.
        Returns (passed, reasons, hatch_type)
        hatch_type: 'EARLY_HATCH_EXCEPTIONAL' | 'EARLY_HATCH_VALIDATED' | ''
        """
        reasons = []

        # Check if we have bonus criteria that reduce trade minimum
        effective_min_trades = self.min_trades
        hatch_type = 'EARLY_HATCH_EXCEPTIONAL'

        if metrics.get('walk_forward_validated', False):
            effective_min_trades = 10
            hatch_type = 'EARLY_HATCH_VALIDATED'
        elif metrics.get('consensus_agreement', 0) >= 3:
            effective_min_trades = 10
            hatch_type = 'EARLY_HATCH_CONSENSUS'

        # Check all criteria
        checks = [
            (metrics.get('days_in_test', 0) >= self.min_forward_days,
             f"Days: {metrics.get('days_in_test', 0)}/{self.min_forward_days}"),
            (metrics.get('trades_count', 0) >= effective_min_trades,
             f"Trades: {metrics.get('trades_count', 0)}/{effective_min_trades}"),
            (metrics.get('win_rate', 0) >= self.min_win_rate,
             f"WR: {metrics.get('win_rate', 0):.1%}/{self.min_win_rate:.1%}"),
            (metrics.get('sharpe', 0) >= self.min_sharpe,
             f"Sharpe: {metrics.get('sharpe', 0):.2f}/{self.min_sharpe}"),
            (metrics.get('max_drawdown', 1) <= self.max_drawdown,
             f"DD: {metrics.get('max_drawdown', 0):.1%}/{self.max_drawdown:.1%}"),
            (metrics.get('pnl_pct', 0) >= self.min_pnl_pct,
             f"PnL: {metrics.get('pnl_pct', 0):.2f}%/{self.min_pnl_pct}%"),
            (metrics.get('profit_factor', 0) >= self.min_profit_factor,
             f"PF: {metrics.get('profit_factor', 0):.2f}/{self.min_profit_factor}"),
        ]

        passed = all(ok for ok, _ in checks)
        reasons = [msg for ok, msg in checks if not ok]

        if passed:
            reasons = [f"EARLY HATCH: {hatch_type} — all quality gates exceeded!"]

        return passed, reasons, hatch_type if passed else ''


# Standard graduation criteria (45 days, 50 trades)
STANDARD_GRADUATION = StrategyGraduationCriteria()

# Early hatch for exceptional performers (7 days, 15 trades, stricter quality)
EARLY_HATCH = EarlyHatchCriteria()


class ForwardTestTracker:
    """
    Central tracker for all forward-testing strategies.
    
    Tracks:
    - Paper trading performance (45-day minimum)
    - Forward test metrics vs backtest expectations
    - Graduation decisions
    - Live deployment tracking
    """
    
    def __init__(self, db_path: str = "incubator/forward_test.db", 
                 results_dir: str = "battleground/data/forward_test"):
        self.db_path = db_path
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        self._init_db()
        
    def _init_db(self):
        """Initialize SQLite database for forward test tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main strategies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategies (
                strategy_name TEXT PRIMARY KEY,
                agent_id TEXT,
                status TEXT DEFAULT 'paper_trading',
                created_at TEXT,
                paper_started_at TEXT,
                forward_started_at TEXT,
                graduated_at TEXT,
                failed_at TEXT,
                backtest_sharpe REAL,
                backtest_win_rate REAL,
                backtest_max_dd REAL,
                backtest_expectancy REAL,
                forward_sharpe REAL,
                forward_win_rate REAL,
                forward_max_dd REAL,
                forward_expectancy REAL,
                forward_pnl_pct REAL DEFAULT 0.0,
                forward_trades_count INTEGER DEFAULT 0,
                forward_days INTEGER DEFAULT 0,
                graduation_score REAL,
                last_updated TEXT
            )
        ''')
        
        # Daily performance tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT,
                date TEXT,
                pnl_pct REAL,
                trades_count INTEGER,
                cumulative_pnl_pct REAL,
                drawdown_pct REAL,
                FOREIGN KEY (strategy_name) REFERENCES strategies(strategy_name)
            )
        ''')
        
        # Individual trades tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS forward_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT,
                entry_time TEXT,
                exit_time TEXT,
                direction TEXT,
                entry_price REAL,
                exit_price REAL,
                pnl_pct REAL,
                exit_reason TEXT,
                bars_held INTEGER,
                FOREIGN KEY (strategy_name) REFERENCES strategies(strategy_name)
            )
        ''')
        
        # Graduation audit log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS graduation_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT,
                decision TEXT,  -- 'graduated', 'rejected', 'extended'
                decided_at TEXT,
                criteria_met BOOLEAN,
                reasons TEXT,
                recommended_allocation_pct REAL
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def register_strategy(self, strategy_name: str, agent_id: str,
                         backtest_metrics: Dict[str, Any],
                         created_at: Optional[str] = None) -> bool:
        """Register a new strategy for forward testing"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now(timezone.utc).isoformat()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO strategies 
                (strategy_name, agent_id, status, created_at, paper_started_at,
                 backtest_sharpe, backtest_win_rate, backtest_max_dd, backtest_expectancy,
                 last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                strategy_name, agent_id, 'paper_trading',
                created_at or now, now,
                backtest_metrics.get('sharpe'),
                backtest_metrics.get('win_rate'),
                backtest_metrics.get('max_drawdown'),
                backtest_metrics.get('expectancy'),
                now
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"[ForwardTracker] Error registering {strategy_name}: {e}")
            return False
        finally:
            conn.close()
            
    def update_forward_metrics(self, strategy_name: str,
                               metrics: Dict[str, Any],
                               trades: Optional[List[Dict]] = None) -> bool:
        """Update forward test metrics for a strategy"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now(timezone.utc).isoformat()
        
        try:
            cursor.execute('''
                UPDATE strategies SET
                    forward_sharpe = ?,
                    forward_win_rate = ?,
                    forward_max_dd = ?,
                    forward_expectancy = ?,
                    forward_pnl_pct = ?,
                    forward_trades_count = ?,
                    forward_days = ?,
                    last_updated = ?
                WHERE strategy_name = ?
            ''', (
                metrics.get('sharpe'),
                metrics.get('win_rate'),
                metrics.get('max_drawdown'),
                metrics.get('expectancy'),
                metrics.get('pnl_pct', 0),
                metrics.get('trades_count', 0),
                metrics.get('days_in_test', 0),
                now,
                strategy_name
            ))
            
            # Store individual trades if provided
            if trades:
                for trade in trades:
                    cursor.execute('''
                        INSERT OR REPLACE INTO forward_trades
                        (strategy_name, entry_time, exit_time, direction,
                         entry_price, exit_price, pnl_pct, exit_reason, bars_held)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        strategy_name,
                        trade.get('entry_time'),
                        trade.get('exit_time'),
                        trade.get('direction'),
                        trade.get('entry_price'),
                        trade.get('exit_price'),
                        trade.get('pnl_pct'),
                        trade.get('exit_reason'),
                        trade.get('bars_held')
                    ))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"[ForwardTracker] Error updating {strategy_name}: {e}")
            return False
        finally:
            conn.close()
            
    def evaluate_graduation(self, strategy_name: str,
                           criteria: Optional[StrategyGraduationCriteria] = None) -> Dict[str, Any]:
        """Evaluate if a strategy is ready for graduation"""
        if criteria is None:
            criteria = StrategyGraduationCriteria()
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT forward_sharpe, forward_win_rate, forward_max_dd,
                       forward_pnl_pct, forward_trades_count, forward_days,
                       backtest_sharpe, backtest_win_rate, backtest_expectancy
                FROM strategies WHERE strategy_name = ?
            ''', (strategy_name,))
            
            row = cursor.fetchone()
            if not row:
                return {'error': 'Strategy not found'}
                
            metrics = {
                'sharpe': row[0],
                'win_rate': row[1],
                'max_drawdown': row[2],
                'pnl_pct': row[3],
                'trades_count': row[4],
                'days_in_test': row[5],
                'backtest_sharpe': row[6],
                'backtest_win_rate': row[7],
                'backtest_expectancy': row[8]
            }
            
            passed, reasons = criteria.check(metrics)
            
            # Calculate graduation score
            score = self._calculate_graduation_score(metrics)
            
            return {
                'strategy_name': strategy_name,
                'ready_for_graduation': passed,
                'criteria_reasons': reasons,
                'graduation_score': score,
                'metrics': metrics,
                'recommendation': 'graduate' if passed else 'continue_paper'
            }
            
        finally:
            conn.close()
            
    def _calculate_graduation_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate a 0-100 graduation score based on forward performance"""
        score = 0.0
        
        # Days in test (max 20 points at 45 days)
        days = metrics.get('days_in_test', 0)
        score += min(20, days / 45 * 20)

        # Trade count (max 15 points at 50 trades)
        trades = metrics.get('trades_count', 0)
        score += min(15, trades / 50 * 15)
        
        # Win rate (max 20 points at 60%)
        wr = metrics.get('win_rate', 0)
        score += min(20, wr / 0.60 * 20)
        
        # Sharpe (max 25 points at 1.5)
        sharpe = metrics.get('sharpe', 0) or 0
        score += min(25, sharpe / 1.5 * 25)
        
        # Drawdown (max 20 points at <10%)
        dd = metrics.get('max_drawdown', 1)
        score += max(0, 20 - (dd / 0.10 * 5))
        
        return round(score, 2)
        
    def graduate_strategy(self, strategy_name: str,
                         allocation_pct: float,
                         reasons: List[str]) -> bool:
        """Graduate a strategy to live trading"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now(timezone.utc).isoformat()
        
        try:
            # Update strategy status
            cursor.execute('''
                UPDATE strategies SET
                    status = 'graduated',
                    graduated_at = ?,
                    graduation_score = ?,
                    last_updated = ?
                WHERE strategy_name = ?
            ''', (now, self._calculate_graduation_score({}), now, strategy_name))
            
            # Log graduation decision
            cursor.execute('''
                INSERT INTO graduation_decisions
                (strategy_name, decision, decided_at, criteria_met, reasons, recommended_allocation_pct)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (strategy_name, 'graduated', now, True, json.dumps(reasons), allocation_pct))
            
            conn.commit()
            
            # Export graduation certificate
            self._export_graduation_certificate(strategy_name, allocation_pct, reasons)
            
            return True
        except Exception as e:
            print(f"[ForwardTracker] Error graduating {strategy_name}: {e}")
            return False
        finally:
            conn.close()
            
    def _export_graduation_certificate(self, strategy_name: str,
                                      allocation_pct: float,
                                      reasons: List[str]):
        """Export a graduation certificate JSON"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM strategies WHERE strategy_name = ?
        ''', (strategy_name,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            cert = {
                'strategy_name': strategy_name,
                'graduated_at': datetime.now(timezone.utc).isoformat(),
                'allocation_pct': allocation_pct,
                'graduation_reasons': reasons,
                'forward_metrics': {
                    'sharpe': row[12],
                    'win_rate': row[13],
                    'max_drawdown': row[14],
                    'expectancy': row[15],
                    'pnl_pct': row[16],
                    'trades_count': row[17],
                    'days_in_test': row[18]
                },
                'backtest_comparison': {
                    'sharpe': row[8],
                    'win_rate': row[9],
                    'max_dd': row[10],
                    'expectancy': row[11]
                }
            }
            
            cert_path = self.results_dir / f"graduated_{strategy_name}.json"
            with open(cert_path, 'w') as f:
                json.dump(cert, f, indent=2)
                
    def get_all_strategies(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all strategies, optionally filtered by status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status:
            cursor.execute('SELECT * FROM strategies WHERE status = ?', (status,))
        else:
            cursor.execute('SELECT * FROM strategies')
            
        rows = cursor.fetchall()
        conn.close()
        
        strategies = []
        for row in rows:
            strategies.append({
                'strategy_name': row[0],
                'agent_id': row[1],
                'status': row[2],
                'created_at': row[3],
                'forward_sharpe': row[12],
                'forward_win_rate': row[13],
                'forward_max_dd': row[14],
                'forward_pnl_pct': row[16],
                'forward_trades': row[17],
                'forward_days': row[18],
                'graduation_score': row[19]
            })
            
        return strategies
        
    def get_leaderboard(self, min_days: int = 7) -> List[Dict[str, Any]]:
        """Get top performing strategies by forward metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT strategy_name, agent_id, status, forward_sharpe, 
                   forward_win_rate, forward_pnl_pct, forward_trades_count,
                   forward_days, graduation_score
            FROM strategies
            WHERE forward_days >= ? AND forward_sharpe IS NOT NULL
            ORDER BY forward_sharpe DESC
        ''', (min_days,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'rank': i + 1,
                'strategy_name': row[0],
                'agent_id': row[1],
                'status': row[2],
                'sharpe': row[3],
                'win_rate': row[4],
                'pnl_pct': row[5],
                'trades': row[6],
                'days': row[7],
                'score': row[8]
            }
            for i, row in enumerate(rows)
        ]
        
    def export_dashboard_data(self) -> Dict[str, Any]:
        """Export data for dashboard visualization"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Summary stats
        cursor.execute('''
            SELECT status, COUNT(*) FROM strategies GROUP BY status
        ''')
        status_counts = dict(cursor.fetchall())
        
        # Top performers
        cursor.execute('''
            SELECT strategy_name, forward_sharpe, forward_pnl_pct
            FROM strategies
            WHERE status = 'graduated'
            ORDER BY forward_sharpe DESC
            LIMIT 10
        ''')
        top_graduated = cursor.fetchall()
        
        # Paper trading candidates
        cursor.execute('''
            SELECT strategy_name, forward_sharpe, forward_days
            FROM strategies
            WHERE status = 'paper_trading' AND forward_days >= 20
            ORDER BY forward_sharpe DESC
        ''')
        paper_candidates = cursor.fetchall()
        
        conn.close()
        
        return {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'summary': {
                'total': sum(status_counts.values()),
                'paper_trading': status_counts.get('paper_trading', 0),
                'forward_testing': status_counts.get('forward_testing', 0),
                'graduated': status_counts.get('graduated', 0),
                'failed': status_counts.get('failed', 0)
            },
            'top_graduated': [
                {'name': r[0], 'sharpe': r[1], 'pnl': r[2]}
                for r in top_graduated
            ],
            'paper_candidates': [
                {'name': r[0], 'sharpe': r[1], 'days': r[2]}
                for r in paper_candidates
            ]
        }


# Global tracker instance
_tracker: Optional[ForwardTestTracker] = None


def get_tracker(db_path: str = "incubator/forward_test.db") -> ForwardTestTracker:
    """Get or create the global forward test tracker"""
    global _tracker
    if _tracker is None:
        _tracker = ForwardTestTracker(db_path)
    return _tracker


def register_strategy_for_forward_test(strategy_name: str, agent_id: str,
                                       backtest_metrics: Dict[str, Any]) -> bool:
    """Convenience function to register a strategy"""
    tracker = get_tracker()
    return tracker.register_strategy(strategy_name, agent_id, backtest_metrics)


def update_forward_performance(strategy_name: str, metrics: Dict[str, Any],
                               trades: Optional[List[Dict]] = None) -> bool:
    """Convenience function to update forward metrics"""
    tracker = get_tracker()
    return tracker.update_forward_metrics(strategy_name, metrics, trades)


def check_graduation_readiness(strategy_name: str) -> Dict[str, Any]:
    """Convenience function to check if strategy can graduate"""
    tracker = get_tracker()
    return tracker.evaluate_graduation(strategy_name)
