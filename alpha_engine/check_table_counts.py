#!/usr/bin/env python3
"""
Check row counts for key tables.
"""
import sys
import os
import pandas as pd
import pymysql

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.db_env import get_stocks_creds

def check_table_counts():
    """Check row counts for key tables."""
    query = """
    SELECT 
        'bt_backtest_trades' as table_name,
        COUNT(*) as row_count
    FROM bt_backtest_trades
    
    UNION ALL
    
    SELECT 
        'at_signal_outcomes' as table_name,
        COUNT(*) as row_count
    FROM at_signal_outcomes
    
    UNION ALL
    
    SELECT 
        'at_strategy_stats' as table_name,
        COUNT(*) as row_count
    FROM at_strategy_stats
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
    result = check_table_counts()
    if result is not None:
        print("\nRow Counts for Key Tables:")
        print("=" * 30)
        print(result.to_string(index=False))
    else:
        print("Failed to retrieve table counts.")
        sys.exit(1)
