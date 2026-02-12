#!/usr/bin/env python3
"""
GROK_XAI Kelly Sizing Engine
Computes Kelly fractions from lm_trades data for each algorithm.
Updates lm_kelly_fractions table with half_kelly values.
Run daily after trade updates.
"""
import mysql.connector
import pandas as pd
import numpy as np
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    config = {
        'host': 'localhost',
        'user': 'root',
        'password': '',
        'database': 'antigravity'
    }
    
    try:
        cnx = mysql.connector.connect(**config)
        query = """
        SELECT 
            algorithm_name,
            COUNT(*) as total_trades,
            SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
            AVG(CASE WHEN realized_pnl_usd > 0 THEN realized_pnl_usd END) as avg_win,
            AVG(CASE WHEN realized_pnl_usd < 0 THEN ABS(realized_pnl_usd) END) as avg_loss_abs
        FROM lm_trades 
        WHERE status = 'closed' 
        GROUP BY algorithm_name 
        HAVING total_trades >= 10
        """
        
        df = pd.read_sql(query, cnx)
        logging.info(f"Found {len(df)} algorithms with >=10 closed trades")
        
        cursor = cnx.cursor()
        
        for _, row in df.iterrows():
            total = row['total_trades']
            wins = row['wins']
            p = wins / total if total > 0 else 0
            
            avg_win = row['avg_win'] or 0
            avg_loss_abs = row['avg_loss_abs'] or 1  # avoid div0
            
            b = avg_win / avg_loss_abs if avg_loss_abs > 0 else 1
            kelly = (p * b - (1 - p)) / b if b > 0 else 0
            half_kelly = max(0, min(0.25, kelly / 2))
            
            logging.info(f"{row['algorithm_name']}: p={p:.3f}, b={b:.3f}, kelly={kelly:.4f}, half={half_kelly:.4f}")
            
            update_sql = "REPLACE INTO lm_kelly_fractions (algorithm_name, half_kelly) VALUES (%s, %s)"
            cursor.execute(update_sql, (row['algorithm_name'], half_kelly))
        
        cnx.commit()
        cursor.close()
        cnx.close()
        logging.info("Kelly fractions updated successfully.")
        
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        if 'cnx' in locals():
            cnx.rollback()

if __name__ == '__main__':
    main()
