
import sqlite3
import pandas as pd
import json
from pathlib import Path

DB_PATH = Path("e:/findtorontoevents_antigravity.ca/alpha_engine/data/alpha.db")

def analyze():
    if not DB_PATH.exists():
        print(f"DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    
    # 1. Asset Class Breakdown
    print("\n=== ASSET CLASS BREAKDOWN ===")
    query = """
    SELECT 
        category,
        COUNT(*) as total_trades,
        SUM(CASE WHEN status='WON' THEN 1 ELSE 0 END) as wins,
        AVG(pnl_pct) * 100 as avg_pct,
        SUM(pnl_dollar) as total_pnl_usd
    FROM picks
    WHERE status IN ('WON', 'LOST', 'BREAKEVEN', 'EXPIRED')
    GROUP BY category
    ORDER BY total_pnl_usd DESC
    """
    df_assets = pd.read_sql_query(query, conn)
    print(df_assets)

    # 2. Top Winners & Losers (Symbols)
    print("\n=== TOP 5 WINNING SYMBOLS ===")
    query_winners = """
    SELECT symbol, category, COUNT(*) as trades, SUM(pnl_dollar) as pnl
    FROM picks
    WHERE status != 'OPEN'
    GROUP BY symbol
    ORDER BY pnl DESC
    LIMIT 5
    """
    print(pd.read_sql_query(query_winners, conn))

    print("\n=== TOP 5 LOSING SYMBOLS ===")
    query_losers = """
    SELECT symbol, category, COUNT(*) as trades, SUM(pnl_dollar) as pnl
    FROM picks
    WHERE status != 'OPEN'
    GROUP BY symbol
    ORDER BY pnl ASC
    LIMIT 5
    """
    print(pd.read_sql_query(query_losers, conn))

    # 3. Strategy Audit
    print("\n=== STRATEGY PERFORMANCE (TOP 10) ===")
    query_strats = """
    SELECT 
        strategy,
        COUNT(*) as trades,
        SUM(CASE WHEN status='WON' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as win_rate,
        AVG(pnl_pct) * 100 as avg_pct,
        SUM(pnl_dollar) as total_pnl
    FROM picks
    WHERE status != 'OPEN'
    GROUP BY strategy
    HAVING trades > 2
    ORDER BY total_pnl DESC
    LIMIT 10
    """
    print(pd.read_sql_query(query_strats, conn))

    # 4. Scarcity Check (High WR, Low Pick Count)
    print("\n=== HIGH QUALITY / LOW FREQUENCY STRATEGIES ===")
    query_scarcity = """
    SELECT strategy, COUNT(*) as trades, AVG(pnl_pct) as win_rate
    FROM picks
    WHERE status != 'OPEN'
    GROUP BY strategy
    HAVING trades BETWEEN 1 AND 5
    ORDER BY win_rate DESC
    LIMIT 5
    """
    print(pd.read_sql_query(query_scarcity, conn))

    # 5. TP/SL Analysis
    print("\n=== TP/SL MISS ANALYSIS (WON but small vs LOST but deep) ===")
    query_tpsl = """
    SELECT 
        exit_reason,
        COUNT(*) as count,
        AVG(pnl_pct) * 100 as avg_pnl_pct,
        AVG(hold_days) as avg_hold
    FROM picks
    WHERE status != 'OPEN'
    GROUP BY exit_reason
    """
    print(pd.read_sql_query(query_tpsl, conn))

    conn.close()

if __name__ == "__main__":
    analyze()
