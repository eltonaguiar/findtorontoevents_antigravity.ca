# garch_vol.py - GARCH volatility forecasting for sizing
# Requirements: pip install arch pandas yfinance mysql-connector-python

import os
import mysql.connector
import pandas as pd
import yfinance as yf
from arch import arch_model

# DB config
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

def connect_db():
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
    )

def fetch_returns(ticker, period='1y'):
    data = yf.download(ticker, period=period)['Adj Close']
    returns = 100 * data.pct_change().dropna()  # In percent
    return returns

def forecast_vol(returns, horizon=1):
    model = arch_model(returns, vol='GARCH', p=1, q=1)
    res = model.fit(disp='off')
    forecast = res.forecast(horizon=horizon)
    vol_forecast = forecast.variance.iloc[-1, 0] ** 0.5
    return vol_forecast

def adjust_kelly(kelly, vol_forecast, vol_target=0.02):  # 2% daily vol target
    adjustment = vol_target / max(vol_forecast, 0.001)
    return kelly * adjustment

def run_vol_forecast():
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    
    # Get active algos
    cursor.execute("SELECT DISTINCT algo_name FROM lm_kelly_fractions")
    algos = [row['algo_name'] for row in cursor.fetchall()]
    
    for algo in algos:
        # Assume algo tied to SPY vol for simplicity; customize per algo if needed
        returns = fetch_returns('SPY')
        vol = forecast_vol(returns)
        
        # Get current Kelly
        cursor.execute("SELECT kelly_fraction FROM lm_kelly_fractions WHERE algo_name = %s ORDER BY calculation_date DESC LIMIT 1", (algo,))
        row = cursor.fetchone()
        if row:
            kelly = float(row['kelly_fraction'])
            adjusted = adjust_kelly(kelly, vol)
            
            # Update DB (add vol_adjusted_kelly column first if needed)
            cursor.execute("""
            UPDATE lm_kelly_fractions 
            SET vol_adjusted_kelly = %s 
            WHERE algo_name = %s 
            ORDER BY calculation_date DESC LIMIT 1
            """, (adjusted, algo))
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    run_vol_forecast()