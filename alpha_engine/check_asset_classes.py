#!/usr/bin/env python3
"""
Check what asset classes are available in the database.
"""
import sys
import os
import pandas as pd
import pymysql

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.db_env import get_stocks_creds

def check_asset_classes():
    """Check distinct asset classes in the database."""
    query = """
    SELECT 
        'bt_backtest_trades' as source,
        asset_class,
        COUNT(*) as count
    FROM bt_backtest_trades 
    WHERE status = 'CLOSED'
    GROUP BY asset_class
    
    UNION ALL
    
    SELECT 
        'at_signal_outcomes' as source,
        asset_class,
        COUNT(*) as count
    FROM at_signal_outcomes 
    WHERE outcome IN ('WIN', 'LOSS')
    GROUP BY asset_class
    
    ORDER BY source, count DESC
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
    result = check_asset_classes()
    if result is not None:
        print("\nAsset Classes in Database:")
        print("=" * 30)
        print(result.to_string(index=False))
    else:
        print("Failed to retrieve asset classes.")
        sys.exit(1)
