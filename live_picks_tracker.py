#!/usr/bin/env python3
"""
LIVE PICKS TRACKER
Monitors all active picks across all systems in real-time
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("live_picks_tracker")


@dataclass
class LivePick:
    """Represents a live trading pick"""
    id: str
    symbol: str
    strategy: str
    system: str  # alpha_engine, mercury2, etc.
    side: str  # LONG or SHORT
    entry_price: float
    take_profit: float
    stop_loss: float
    current_price: float
    unrealized_pnl_pct: float
    entry_time: str
    bars_held: int
    status: str  # ACTIVE, TP_HIT, SL_HIT, EXPIRED
    metadata: Dict = None
    
    def to_dict(self):
        return asdict(self)


class LivePicksTracker:
    """Central tracker for all live picks across systems"""
    
    def __init__(self, db_path: str = "data/live_picks.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
    def _init_db(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS live_picks (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                strategy TEXT NOT NULL,
                system TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                take_profit REAL NOT NULL,
                stop_loss REAL NOT NULL,
                current_price REAL,
                unrealized_pnl_pct REAL,
                entry_time TEXT NOT NULL,
                last_updated TEXT,
                bars_held INTEGER DEFAULT 0,
                status TEXT DEFAULT 'ACTIVE',
                metadata TEXT,
                UNIQUE(id, system)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pick_history (
                id TEXT,
                system TEXT,
                timestamp TEXT,
                price REAL,
                unrealized_pnl_pct REAL,
                event TEXT,
                PRIMARY KEY (id, system, timestamp)
            )
        """)
        
        conn.commit()
        conn.close()
        
    def register_pick(self, pick: LivePick):
        """Register a new live pick"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO live_picks 
                (id, symbol, strategy, system, side, entry_price, take_profit, stop_loss,
                 current_price, unrealized_pnl_pct, entry_time, last_updated, bars_held, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pick.id, pick.symbol, pick.strategy, pick.system, pick.side,
                pick.entry_price, pick.take_profit, pick.stop_loss,
                pick.current_price, pick.unrealized_pnl_pct, pick.entry_time,
                datetime.now().isoformat(), pick.bars_held, pick.status,
                json.dumps(pick.metadata) if pick.metadata else None
            ))
            
            # Add to history
            cursor.execute("""
                INSERT INTO pick_history (id, system, timestamp, price, unrealized_pnl_pct, event)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (pick.id, pick.system, datetime.now().isoformat(), 
                  pick.current_price, pick.unrealized_pnl_pct, 'REGISTERED'))
            
            conn.commit()
            logger.info(f"Registered pick: {pick.id} ({pick.symbol} {pick.side})")
            
        except Exception as e:
            logger.error(f"Error registering pick: {e}")
        finally:
            conn.close()
            
    def update_pick(self, pick_id: str, system: str, current_price: float, 
                    unrealized_pnl_pct: float, bars_held: int = None):
        """Update pick with current market data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE live_picks 
                SET current_price = ?, unrealized_pnl_pct = ?, last_updated = ?,
                    bars_held = COALESCE(?, bars_held)
                WHERE id = ? AND system = ?
            """, (current_price, unrealized_pnl_pct, datetime.now().isoformat(),
                  bars_held, pick_id, system))
            
            # Add to history
            cursor.execute("""
                INSERT INTO pick_history (id, system, timestamp, price, unrealized_pnl_pct, event)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (pick_id, system, datetime.now().isoformat(), 
                  current_price, unrealized_pnl_pct, 'UPDATE'))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error updating pick: {e}")
        finally:
            conn.close()
            
    def close_pick(self, pick_id: str, system: str, exit_price: float, 
                   realized_pnl_pct: float, exit_reason: str):
        """Mark pick as closed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE live_picks 
                SET status = 'CLOSED', current_price = ?, unrealized_pnl_pct = ?,
                    last_updated = ?
                WHERE id = ? AND system = ?
            """, (exit_price, realized_pnl_pct, datetime.now().isoformat(), 
                  pick_id, system))
            
            cursor.execute("""
                INSERT INTO pick_history (id, system, timestamp, price, unrealized_pnl_pct, event)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (pick_id, system, datetime.now().isoformat(), 
                  exit_price, realized_pnl_pct, f'CLOSED: {exit_reason}'))
            
            conn.commit()
            logger.info(f"Closed pick: {pick_id} ({exit_reason}, PnL: {realized_pnl_pct:+.2f}%)")
            
        except Exception as e:
            logger.error(f"Error closing pick: {e}")
        finally:
            conn.close()
            
    def get_active_picks(self, system: str = None, strategy: str = None) -> List[LivePick]:
        """Get all active picks, optionally filtered"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM live_picks WHERE status = 'ACTIVE'"
        params = []
        
        if system:
            query += " AND system = ?"
            params.append(system)
        if strategy:
            query += " AND strategy = ?"
            params.append(strategy)
            
        query += " ORDER BY entry_time DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        picks = []
        for row in rows:
            picks.append(LivePick(
                id=row[0], symbol=row[1], strategy=row[2], system=row[3],
                side=row[4], entry_price=row[5], take_profit=row[6],
                stop_loss=row[7], current_price=row[8] or row[5],
                unrealized_pnl_pct=row[9] or 0,
                entry_time=row[10], bars_held=row[12] or 0,
                status=row[13], metadata=json.loads(row[14]) if row[14] else None
            ))
            
        return picks
        
    def get_summary(self) -> Dict:
        """Get summary statistics of all live picks"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Active picks summary
        cursor.execute("""
            SELECT system, strategy, COUNT(*), 
                   SUM(CASE WHEN unrealized_pnl_pct > 0 THEN 1 ELSE 0 END) as winners,
                   SUM(unrealized_pnl_pct) as total_pnl
            FROM live_picks 
            WHERE status = 'ACTIVE'
            GROUP BY system, strategy
        """)
        
        active_summary = cursor.fetchall()
        
        # Closed picks summary (today)
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT system, COUNT(*), 
                   SUM(CASE WHEN unrealized_pnl_pct > 0 THEN 1 ELSE 0 END) as winners,
                   SUM(unrealized_pnl_pct) as total_pnl
            FROM live_picks 
            WHERE status = 'CLOSED' AND date(last_updated) = ?
            GROUP BY system
        """, (today,))
        
        closed_summary = cursor.fetchall()
        conn.close()
        
        return {
            "active": {
                "by_system_strategy": [
                    {
                        "system": row[0],
                        "strategy": row[1],
                        "count": row[2],
                        "winners": row[3],
                        "total_pnl_pct": row[4]
                    }
                    for row in active_summary
                ],
                "total_active": sum(row[2] for row in active_summary),
                "total_unrealized_pnl": sum(row[4] for row in active_summary) if active_summary else 0
            },
            "closed_today": {
                "by_system": [
                    {
                        "system": row[0],
                        "count": row[1],
                        "winners": row[2],
                        "total_pnl_pct": row[3]
                    }
                    for row in closed_summary
                ],
                "total_closed": sum(row[1] for row in closed_summary),
                "total_realized_pnl": sum(row[3] for row in closed_summary) if closed_summary else 0
            },
            "timestamp": datetime.now().isoformat()
        }
        
    def export_to_dashboard(self, output_path: str = "dashboard/live_picks.json"):
        """Export current state to dashboard JSON"""
        summary = self.get_summary()
        active_picks = self.get_active_picks()
        
        dashboard_data = {
            "summary": summary,
            "active_picks": [pick.to_dict() for pick in active_picks],
            "generated_at": datetime.now().isoformat()
        }
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(dashboard_data, f, indent=2)
            
        logger.info(f"Dashboard exported: {output_file}")
        return dashboard_data


def sync_all_systems():
    """Sync picks from all system JSON files to tracker DB"""
    tracker = LivePicksTracker()
    
    systems_to_sync = [
        ("alpha_engine", "alpha_engine/data/active_picks.json"),
        ("mercury2", "mercury2/data/active_picks.json"),
        ("crypto_ml_edge", "crypto_ml_edge/data/active_picks.json"),
    ]
    
    for system, filepath in systems_to_sync:
        path = Path(filepath)
        if not path.exists():
            continue
            
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                
            picks = data if isinstance(data, list) else data.get('picks', [])
            
            for pick_data in picks:
                if not isinstance(pick_data, dict):
                    continue
                    
                # Helper to safely convert to float
                def safe_float(val, default=0.0):
                    if val is None:
                        return default
                    try:
                        return float(val)
                    except (TypeError, ValueError):
                        return default
                
                pick = LivePick(
                    id=pick_data.get('id', f"{pick_data.get('symbol')}_{pick_data.get('timestamp', '')}"),
                    symbol=pick_data.get('symbol', pick_data.get('pair', 'UNKNOWN')),
                    strategy=pick_data.get('strategy', 'unknown'),
                    system=system,
                    side=pick_data.get('side', pick_data.get('direction', 'LONG')),
                    entry_price=safe_float(pick_data.get('entry_price'), 0),
                    take_profit=safe_float(pick_data.get('take_profit'), 0),
                    stop_loss=safe_float(pick_data.get('stop_loss'), 0),
                    current_price=safe_float(pick_data.get('current_price'), safe_float(pick_data.get('entry_price'), 0)),
                    unrealized_pnl_pct=safe_float(pick_data.get('unrealized_pnl_pct'), 0),
                    entry_time=pick_data.get('timestamp', pick_data.get('entry_time', datetime.now().isoformat())),
                    bars_held=int(pick_data.get('bars_held', 0) or 0),
                    status=pick_data.get('status', 'ACTIVE'),
                    metadata=pick_data
                )
                
                tracker.register_pick(pick)
                
        except Exception as e:
            logger.error(f"Error syncing {system}: {e}")
            
    # Export to dashboard
    tracker.export_to_dashboard()
    
    # Print summary
    summary = tracker.get_summary()
    print("\n" + "="*80)
    print("LIVE PICKS SUMMARY")
    print("="*80)
    print(f"Total Active: {summary['active']['total_active']}")
    print(f"Total Unrealized PnL: {summary['active']['total_unrealized_pnl']:+.2f}%")
    print(f"Closed Today: {summary['closed_today']['total_closed']}")
    print(f"Realized Today: {summary['closed_today']['total_realized_pnl']:+.2f}%")
    print("="*80)


if __name__ == "__main__":
    sync_all_systems()
