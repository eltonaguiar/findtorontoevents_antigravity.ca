"""
Import Evolved Strategies to ejaguiar1_stocks Audit Trail
=========================================================

This script imports viable evolved strategies into the central audit trail
database (ejaguiar1_stocks) for forward tracking and performance monitoring.

Usage:
    python genome/import_to_ejaguiar1.py --all-viable
    python genome/import_to_ejaguiar1.py --strategy-id <id>
    python genome/import_to_ejaguiar1.py --create-picks
"""

import json
import sqlite3
import hashlib
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "paper_trading" / "data" / "paper.db"
AUDIT_DB_PATH = PROJECT_ROOT / "data" / "audit_trail.db"
RESULTS_DIR = PROJECT_ROOT / "genome" / "batch_results"


def get_db_connection(db_path: Path):
    """Get SQLite connection with row factory."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def fetch_viable_strategies(min_fitness: float = 0.5) -> List[Dict]:
    """Fetch all viable evolved strategies from the local database."""
    conn = get_db_connection(DB_PATH)
    
    rows = conn.execute(
        """SELECT * FROM evolved_strategies 
           WHERE is_active = 1 AND fitness >= ?
           ORDER BY fitness DESC""",
        (min_fitness,)
    ).fetchall()
    
    strategies = [dict(row) for row in rows]
    conn.close()
    
    return strategies


def create_audit_trail_tables():
    """Ensure audit trail tables exist."""
    conn = get_db_connection(AUDIT_DB_PATH)
    
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS evolved_strategy_picks (
            pick_id TEXT PRIMARY KEY,
            strategy_id TEXT NOT NULL,
            strategy_type TEXT NOT NULL,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL,
            take_profit REAL,
            stop_loss REAL,
            confidence REAL,
            fitness REAL,
            win_rate REAL,
            sharpe_ratio REAL,
            status TEXT DEFAULT 'PENDING',
            created_at TEXT NOT NULL,
            activated_at TEXT,
            closed_at TEXT,
            realized_pnl_pct REAL,
            source_system TEXT DEFAULT 'genome_evolution'
        );
        
        CREATE INDEX IF NOT EXISTS idx_evp_status ON evolved_strategy_picks(status);
        CREATE INDEX IF NOT EXISTS idx_evp_strategy ON evolved_strategy_picks(strategy_id);
        CREATE INDEX IF NOT EXISTS idx_evp_symbol ON evolved_strategy_picks(symbol);
        CREATE INDEX IF NOT EXISTS idx_evp_fitness ON evolved_strategy_picks(fitness);
        
        CREATE TABLE IF NOT EXISTS evolved_strategy_performance (
            strategy_id TEXT PRIMARY KEY,
            strategy_type TEXT,
            total_picks INTEGER DEFAULT 0,
            winning_picks INTEGER DEFAULT 0,
            losing_picks INTEGER DEFAULT 0,
            avg_realized_return REAL,
            max_drawdown REAL,
            current_streak INTEGER DEFAULT 0,
            best_streak INTEGER DEFAULT 0,
            worst_streak INTEGER DEFAULT 0,
            last_updated TEXT
        );
    """)
    
    conn.commit()
    conn.close()


def import_strategy_to_audit(strategy: Dict, create_pick: bool = True) -> Optional[str]:
    """
    Import a single strategy into the audit trail.
    Returns the pick_id if a pick was created.
    """
    conn = get_db_connection(AUDIT_DB_PATH)
    
    try:
        # Check if strategy already exists
        existing = conn.execute(
            "SELECT 1 FROM evolved_strategy_performance WHERE strategy_id = ?",
            (strategy["strategy_id"],)
        ).fetchone()
        
        if not existing:
            # Register strategy performance tracking
            conn.execute(
                """INSERT INTO evolved_strategy_performance
                   (strategy_id, strategy_type, total_picks, last_updated)
                   VALUES (?, ?, 0, ?)""",
                (strategy["strategy_id"], strategy["strategy_type"],
                 datetime.now(timezone.utc).isoformat())
            )
        
        pick_id = None
        
        if create_pick:
            # Create a forward pick
            pick_id = f"evp_{hashlib.md5(f'{strategy['strategy_id']}_{datetime.now().timestamp()}'.encode()).hexdigest()[:16]}"
            
            conn.execute(
                """INSERT INTO evolved_strategy_picks
                   (pick_id, strategy_id, strategy_type, symbol, direction,
                    entry_price, take_profit, stop_loss, confidence,
                    fitness, win_rate, sharpe_ratio, status, created_at, source_system)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (pick_id, strategy["strategy_id"], strategy["strategy_type"],
                 strategy["symbol"], strategy["direction"],
                 None, None, None,  # Prices to be filled at execution
                 strategy["fitness"], strategy["fitness"],
                 strategy["win_rate"], strategy["sharpe_ratio"],
                 'PENDING', datetime.now(timezone.utc).isoformat(),
                 f"genome_{strategy['strategy_type']}")
            )
            
            print(f"  Created pick {pick_id} for {strategy['name']} ({strategy['symbol']} {strategy['direction']})")
        
        conn.commit()
        return pick_id
        
    except Exception as e:
        print(f"  Error importing strategy {strategy['strategy_id']}: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def import_all_viable(min_fitness: float = 0.5, max_strategies: int = 100):
    """Import all viable strategies to the audit trail."""
    print("=" * 70)
    print("IMPORTING VIABLE STRATEGIES TO AUDIT TRAIL")
    print("=" * 70)
    
    # Ensure tables exist
    create_audit_trail_tables()
    
    # Fetch viable strategies
    strategies = fetch_viable_strategies(min_fitness)
    
    if not strategies:
        print("No viable strategies found. Run batch_evolve_and_integrate.py first.")
        return
    
    print(f"Found {len(strategies)} viable strategies (fitness >= {min_fitness})")
    print(f"Importing top {max_strategies}...\n")
    
    imported = 0
    picks_created = 0
    
    for strategy in strategies[:max_strategies]:
        pick_id = import_strategy_to_audit(strategy, create_pick=True)
        if pick_id:
            imported += 1
            picks_created += 1
    
    print(f"\n{'=' * 70}")
    print(f"IMPORT COMPLETE")
    print(f"{'=' * 70}")
    print(f"Strategies imported: {imported}")
    print(f"Forward picks created: {picks_created}")
    
    # Save summary
    summary = {
        "import_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_strategies": len(strategies),
        "imported": imported,
        "picks_created": picks_created,
        "min_fitness_threshold": min_fitness
    }
    
    summary_file = RESULTS_DIR / "import_summary.json"
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"Summary saved to: {summary_file}")


def activate_pending_picks(symbol: str = None):
    """
    Activate pending picks with current market prices.
    In production, this would fetch real prices and update entry_price.
    """
    conn = get_db_connection(AUDIT_DB_PATH)
    
    query = """SELECT * FROM evolved_strategy_picks 
               WHERE status = 'PENDING'"""
    params = ()
    
    if symbol:
        query += " AND symbol = ?"
        params = (symbol,)
    
    picks = conn.execute(query, params).fetchall()
    
    if not picks:
        print("No pending picks to activate")
        conn.close()
        return
    
    print(f"Found {len(picks)} pending picks")
    print("(In production, these would be activated with current market prices)")
    
    # In a real scenario, we would:
    # 1. Fetch current prices for symbols
    # 2. Calculate TP/SL prices based on strategy parameters
    # 3. Update picks to ACTIVE status
    # 4. Track in portfolio
    
    conn.close()


def generate_daily_picks_report():
    """Generate a report of all active and pending picks."""
    conn = get_db_connection(AUDIT_DB_PATH)
    
    # Get stats
    stats = conn.execute("""
        SELECT 
            status,
            COUNT(*) as count,
            AVG(fitness) as avg_fitness,
            AVG(win_rate) as avg_win_rate
        FROM evolved_strategy_picks
        GROUP BY status
    """).fetchall()
    
    print("\n" + "=" * 70)
    print("EVOLVED STRATEGY PICKS REPORT")
    print("=" * 70)
    
    for row in stats:
        print(f"{row['status']:12s}: {row['count']:3d} picks | "
              f"Avg Fitness: {row['avg_fitness']:.3f} | "
              f"Avg WR: {row['avg_win_rate']:.1%}")
    
    # Get top pending picks
    print("\n--- Top 10 Pending Picks (by fitness) ---")
    pending = conn.execute("""
        SELECT strategy_id, symbol, direction, fitness, win_rate, sharpe_ratio
        FROM evolved_strategy_picks
        WHERE status = 'PENDING'
        ORDER BY fitness DESC
        LIMIT 10
    """).fetchall()
    
    for p in pending:
        print(f"  {p['symbol']:10s} {p['direction']:5s} | "
              f"Fitness: {p['fitness']:.3f} | "
              f"WR: {p['win_rate']:.1%} | "
              f"Sharpe: {p['sharpe_ratio']:.2f}")
    
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Import evolved strategies to audit trail")
    parser.add_argument("--all-viable", action="store_true", 
                       help="Import all viable strategies")
    parser.add_argument("--min-fitness", type=float, default=0.5,
                       help="Minimum fitness threshold")
    parser.add_argument("--max-strategies", type=int, default=100,
                       help="Maximum strategies to import")
    parser.add_argument("--create-picks", action="store_true",
                       help="Create forward picks for strategies")
    parser.add_argument("--activate-pending", action="store_true",
                       help="Activate pending picks with market prices")
    parser.add_argument("--report", action="store_true",
                       help="Generate picks report")
    parser.add_argument("--symbol", type=str,
                       help="Filter by symbol")
    
    args = parser.parse_args()
    
    if args.all_viable:
        import_all_viable(args.min_fitness, args.max_strategies)
    
    if args.activate_pending:
        activate_pending_picks(args.symbol)
    
    if args.report:
        generate_daily_picks_report()
    
    # Default action
    if not any([args.all_viable, args.activate_pending, args.report]):
        print("No action specified. Use --all-viable to import strategies.")
        print("Use --help for more options.")


if __name__ == "__main__":
    main()
