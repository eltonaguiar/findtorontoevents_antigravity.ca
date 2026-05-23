#!/usr/bin/env python3
"""
Check the schema of a database table.
"""
import sys
import os
import pandas as pd
import pymysql

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.db_env import get_stocks_creds

def check_table_schema(table_name):
    """Check the schema of a database table."""
    query = f"DESCRIBE {table_name}"
    
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
    result = check_table_schema("at_strategy_stats")
    if result is not None:
        print("\nSchema for at_strategy_stats table:")
        print("=" * 40)
        print(result.to_string(index=False))
    else:
        print("Failed to retrieve table schema.")
        sys.exit(1)
