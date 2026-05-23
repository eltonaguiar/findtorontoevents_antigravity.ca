#!/usr/bin/env python3
"""
Calculate statistical edge per asset class using multiple data sources.

This script calculates the statistical edge (expectancy) for each asset class 
using data from multiple sources: bt_backtest_trades, at_signal_outcomes, 
and at_strategy_stats tables.
"""
import sys
import os
import pandas as pd
import pymysql

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.db_env import get_stocks_creds

def calculate_statistical_edge():
    """Calculate statistical edge per asset class using multiple data sources."""
    query = '''
    WITH detailed_trades AS (
        -- Get backtest trades
        SELECT 
            'backtest' as source,
            symbol,
            asset_class,
            exit_time,
            pnl_pct,
            CASE 
                WHEN asset_class = 'CRYPTO' THEN pnl_pct >= 0.001
                ELSE pnl_pct >= 0.05
            END as is_win
        FROM bt_backtest_trades 
        WHERE status = 'CLOSED'
        
        UNION ALL
        
        -- Get signal outcomes
        SELECT 
            'signal' as source,
            symbol,
            asset_class,
            created_at as exit_time,
            pnl_pct,
            CASE 
                WHEN asset_class = 'CRYPTO' THEN outcome = 'WIN'
                ELSE pnl_pct >= 0.05
            END as is_win
        FROM at_signal_outcomes 
        WHERE outcome IN ('WIN', 'LOSS')
    ),
    trade_stats AS (
        -- Calculate stats from detailed trades for all asset classes
        SELECT
            asset_class,
            COUNT(*) as total_trades,
            AVG(CASE WHEN is_win THEN pnl_pct ELSE 0 END) as avg_win,
            AVG(CASE WHEN NOT is_win THEN pnl_pct ELSE 0 END) as avg_loss,
            SUM(CASE WHEN is_win THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as win_rate,
            -- Flag if sample size is below minimum threshold
            CASE WHEN COUNT(*) >= 30 THEN 'sufficient' ELSE 'insufficient' END as sample_size_status
        FROM detailed_trades
        GROUP BY asset_class
    )
    SELECT 
        asset_class,
        total_trades,
        ROUND(win_rate * 100, 2) as win_rate_pct,
        ROUND(COALESCE(avg_win, 0), 4) as avg_win_pct,
        ROUND(ABS(COALESCE(avg_loss, 0)), 4) as avg_loss_pct,
        ROUND((win_rate * COALESCE(avg_win, 0)) - ((1-win_rate) * ABS(COALESCE(avg_loss, 0))), 4) as statistical_edge,
        sample_size_status
    FROM trade_stats
    ORDER BY 
        CASE WHEN sample_size_status = 'insufficient' THEN 1 ELSE 0 END,  -- Insufficient samples at end
        statistical_edge DESC;
    '''
    
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
    result = calculate_statistical_edge()
    if result is not None:
        print("\nStatistical Edge by Asset Class:")
        print("=" * 50)
        print(result.to_string(index=False))
    else:
        print("Failed to calculate statistical edge.")
        sys.exit(1)
