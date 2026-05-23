#!/usr/bin/env python3
"""
Check the data in at_strategy_stats table by asset class.
"""
import sys
import os
import pandas as pd
import pymysql

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.db_env import get_stocks_creds

def check_strategy_stats_data():
    """Check data in at_strategy_stats table by asset class."""
    query = """
    SELECT 
        asset_class,
        SUM(wins + losses) as total_trades,
        AVG(win_rate) as avg_win_rate,
        AVG(avg_pnl_pct) as avg_pnl_pct,
        MIN(last_updated) as first_record,
        MAX(last_updated) as latest_record
    FROM at_strategy_stats 
    WHERE wins + losses > 0
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
    result = check_strategy_stats_data()
    if result is not None:
        print("\nStrategy Stats Data by Asset Class:")
        print("=" * 50)
        print(result.to_string(index=False))
    else:
        print("Failed to retrieve strategy stats data.")
        sys.exit(1)
