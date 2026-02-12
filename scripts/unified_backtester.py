# unified_backtester.py - Multi-asset backtester
# Requirements: pip install pandas numpy yfinance backtrader mysql-connector-python

import os
import backtrader as bt
import pandas as pd
import yfinance as yf
import mysql.connector

# DB config
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

class UnifiedStrategy(bt.Strategy):
    def __init__(self):
        self.rsi = bt.indicators.RSI(self.data.close)  # Example

    def next(self):
        if self.rsi < 30:
            self.buy()
        elif self.rsi > 70:
            self.sell()

def run_backtest(ticker, asset_class, start_date, end_date):
    cerebro = bt.Cerebro()
    cerebro.addstrategy(UnifiedStrategy)
    
    data = bt.feeds.PandasData(dataname=yf.download(ticker, start_date, end_date))
    cerebro.adddata(data)
    
    cerebro.broker.setcash(10000.0)
    cerebro.run()
    
    return cerebro.broker.getvalue()  # Final value

def store_backtest_results(ticker, asset_class, final_value):
    conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO backtest_results (ticker, asset_class, final_value, run_date)
    VALUES (%s, %s, %s, NOW())
    """, (ticker, asset_class, final_value))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    result = run_backtest('AAPL', 'stock', '2025-01-01', '2026-01-01')
    store_backtest_results('AAPL', 'stock', result)