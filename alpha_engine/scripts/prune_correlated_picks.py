#!/usr/bin/env python3
"""
GROK_XAI Correlation Pruner for Top Picks
Queries active lm_signals, fetches 90d returns for symbols,
prunes to keep low-correlation (<0.75) subset maximizing total score.
Updates lm_signals with corr_filtered flag.
"""
import yfinance as yf
import pandas as pd
import numpy as np
import mysql.connector
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    config = {
        'host': 'localhost',
        'user': 'root',
        'password': '',
        'database': 'antigravity'
    }
    
    cnx = None
    try:
        cnx = mysql.connector.connect(**config)
        cursor = cnx.cursor()
        
        # Get active signals sorted by strength
        query = """
        SELECT id, symbol, signal_strength, asset_class
        FROM lm_signals 
        WHERE status = 'active' AND expires_at > NOW()
        ORDER BY signal_strength DESC
        """
        cursor.execute(query)
        signals = [{'id': row[0], 'symbol': row[1], 'strength': row[2], 'asset': row[3]} for row in cursor.fetchall()]
        
        if not signals:
            logging.info("No active signals to prune.")
            return
        
        logging.info(f"Pruning {len(signals)} active signals")
        
        # Fetch 90d daily data for unique symbols (handle -USD for crypto)
        symbols = list(set(s['symbol'] for s in signals))
        data = yf.download(symbols, period='3mo', interval='1d', progress=False)['Adj Close']
        data = data.dropna(axis=1, how='all')
        
        if data.empty:
            logging.warning("No price data available")
            return
        
        rets = data.pct_change().dropna()
        
        # Reset corr_filtered to 0
        cursor.execute("UPDATE lm_signals SET corr_filtered = 0 WHERE status = 'active'")
        
        # Greedy selection: highest score first, skip if corr >= 0.75 to any selected
        selected = []
        corr_matrix = rets.corr()
        
        for sig in signals:
            sym = sig['symbol']
            if sym not in corr_matrix.columns:
                continue
            
            if all(corr_matrix.loc[sym, s['symbol']] < 0.75 for s in selected):
                selected.append(sig)
                logging.info(f"Selected {sym} (strength {sig['strength']:.0f})")
                if len(selected) >= 10:  # max 10 uncorrelated
                    break
        
        # Flag selected
        for sig in selected:
            cursor.execute("UPDATE lm_signals SET corr_filtered = 1 WHERE id = %s", (sig['id'],))
        
        cnx.commit()
        logging.info(f"Pruned to {len(selected)} uncorrelated picks")
        
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        if cnx:
            cnx.rollback()
    finally:
        if cnx:
            cursor.close()
            cnx.close()

if __name__ == '__main__':
    main()
