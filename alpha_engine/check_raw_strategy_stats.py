#!/usr/bin/env python3
"""
Check raw data in at_strategy_stats table.
"""
import sys
import os
import pandas as pd
import pymysql

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.db_env import get_stocks_creds

def check_raw_strategy_stats():
    """Check raw data in at_strategy_stats table."""
    query = """
    SELECT 
        asset_class,
        COUNT(*) as strategy_count,
        SUM(wins) as total_wins,
        SUM(losses) as total_losses,
        SUM(wins + losses) as total_trades,
        AVG(win_rate) as avg_win_rate,
        AVG(avg_pnl_pct) as avg_pnl_pct
    FROM at_strategy_stats 
    GROUP BY asset_class
    ORDER BY total_trades DESC
    """
    
    # Get database credentials
    try:
        creds = get_stocks_creds()
    except ValueError as e:
        print(f"Error getting database credentials: {e}")
        return None
    
    # Execute query
    try:
        connection = pymysql.connect(**creds)
        
        df = pd.read_sql(query, connection)
        
        connection.close()
        
        return df
        
    except Exception as e:
        print(f"Error executing query: {e}")
        if 'connection' in locals():
            connection.close()
        return None

if __name__ == "__main__":
    result = check_raw_strategy_stats()
    if result is not None:
        print("\nRaw Strategy Stats by Asset Class:")
        print("=" * 50)
        print(result.to_string(index=False))
    else:
        print("Failed to retrieve raw strategy stats.")
        sys.exit(1)
