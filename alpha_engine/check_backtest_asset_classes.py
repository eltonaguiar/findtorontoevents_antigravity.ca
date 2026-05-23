#!/usr/bin/env python3
"""
Check asset classes in bt_backtest_trades table.
"""
import sys
import os
import pandas as pd
import pymysql

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.db_env import get_stocks_creds

def check_backtest_asset_classes():
    """Check asset classes in bt_backtest_trades table."""
    query = """
    SELECT 
        asset_class,
        COUNT(*) as trade_count,
        MIN(exit_time) as first_trade,
        MAX(exit_time) as latest_trade
    FROM bt_backtest_trades 
    WHERE status = 'CLOSED'
    GROUP BY asset_class
    ORDER BY trade_count DESC
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
    result = check_backtest_asset_classes()
    if result is not None:
        print("\nAsset Classes in bt_backtest_trades:")
        print("=" * 40)
        print(result.to_string(index=False))
    else:
        print("Failed to retrieve asset class data.")
        sys.exit(1)
