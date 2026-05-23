#!/usr/bin/env python3
"""
Forward Testing Database
Centralized tracking for forward test performance.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json


class ForwardTestDatabase:
    """
    Database for tracking forward test signals and performance.
    """
    
    def __init__(self, db_path: str = "forward_testing/forward_signals.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main signals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS forward_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id TEXT UNIQUE NOT NULL,
                system TEXT NOT NULL,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                tp_price REAL NOT NULL,
                sl_price REAL NOT NULL,
                entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                exit_time TIMESTAMP,
                exit_price REAL,
                exit_reason TEXT,
                pnl_absolute REAL,
                pnl_percent REAL,
                regime TEXT,
                volatility_atr REAL,
                max_profit REAL,
                max_drawdown REAL,
                bars_held INTEGER,
                partial_exits TEXT,  -- JSON array
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Performance statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                system TEXT NOT NULL,
                total_signals INTEGER,
                resolved_signals INTEGER,
                win_count INTEGER,
                loss_count INTEGER,
                win_rate REAL,
                avg_profit REAL,
                avg_loss REAL,
                profit_factor REAL,
                total_pnl REAL,
                UNIQUE(date, system)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON forward_signals(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON forward_signals(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_system ON forward_signals(system)')
        
        conn.commit()
        conn.close()
    
    def add_signal(self, signal: Dict) -> bool:
        """Add a new signal to track."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO forward_signals 
                (signal_id, system, symbol, direction, entry_price, tp_price, sl_price,
                 regime, volatility_atr, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal['id'],
                signal['system'],
                signal['symbol'],
                signal['direction'],
                signal['entry_price'],
                signal['tp_price'],
                signal['sl_price'],
                signal.get('regime', 'UNKNOWN'),
                signal.get('atr', 0),
                'open'
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding signal: {e}")
            return False
    
    def close_signal(self, signal_id: str, exit_data: Dict) -> bool:
        """Mark a signal as closed."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE forward_signals 
                SET exit_time = ?,
                    exit_price = ?,
                    exit_reason = ?,
                    pnl_absolute = ?,
                    pnl_percent = ?,
                    max_profit = ?,
                    max_drawdown = ?,
                    bars_held = ?,
                    partial_exits = ?,
                    status = 'closed'
                WHERE signal_id = ?
            ''', (
                datetime.now(),
                exit_data['exit_price'],
                exit_data['exit_reason'],
                exit_data.get('pnl_absolute', 0),
                exit_data.get('pnl_percent', 0),
                exit_data.get('max_profit', 0),
                exit_data.get('max_drawdown', 0),
                exit_data.get('bars_held', 0),
                json.dumps(exit_data.get('partial_exits', [])),
                signal_id
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error closing signal: {e}")
            return False
    
    def get_performance_summary(self, days: int = 30) -> Dict:
        """Get performance summary for recent period."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_date = datetime.now() - timedelta(days=days)
        
        cursor.execute('''
            SELECT 
                COUNT(*),
                SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END),
                SUM(CASE WHEN pnl_percent > 0 THEN 1 ELSE 0 END),
                SUM(CASE WHEN pnl_percent < 0 THEN 1 ELSE 0 END),
                AVG(CASE WHEN pnl_percent > 0 THEN pnl_percent END),
                AVG(CASE WHEN pnl_percent < 0 THEN pnl_percent END),
                SUM(pnl_percent)
            FROM forward_signals
            WHERE entry_time > ?
        ''', (start_date,))
        
        row = cursor.fetchone()
        conn.close()
        
        total, closed, wins, losses, avg_win, avg_loss, total_pnl = row
        
        return {
            'period_days': days,
            'total_signals': total or 0,
            'closed_signals': closed or 0,
            'win_count': wins or 0,
            'loss_count': losses or 0,
            'win_rate': (wins / closed * 100) if closed else 0,
            'avg_win': avg_win or 0,
            'avg_loss': avg_loss or 0,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss else 0,
            'total_pnl': total_pnl or 0
        }


if __name__ == "__main__":
    db = ForwardTestDatabase()
    print("Forward Testing Database initialized")
