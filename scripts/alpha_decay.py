# alpha_decay.py - Alpha decay modeling and monitoring
# Requirements: pip install pandas numpy statsmodels mysql-connector-python

import os
import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
import mysql.connector

# DB config
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

def connect_db():
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
    )

def fetch_alpha_performance(algo_name):
    conn = connect_db()
    query = """
    SELECT calc_date, win_rate, avg_return_pct 
    FROM lm_algo_performance 
    WHERE algorithm_name = %s 
    ORDER BY calc_date
    """
    df = pd.read_sql(query, conn, params=(algo_name,))
    conn.close()
    return df.set_index('calc_date')

def model_decay(performance_series):
    # Fit ARIMA(1,1,0) for decay trend
    model = ARIMA(performance_series, order=(1,1,0))
    res = model.fit()
    forecast = res.forecast(steps=30)
    
    # Decay rate: negative AR coefficient indicates decay
    decay_rate = -res.params['ar.L1'] if 'ar.L1' in res.params else 0
    
    return decay_rate, forecast

def monitor_decay():
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT DISTINCT algorithm_name FROM lm_algo_performance")
    algos = [row['algorithm_name'] for row in cursor.fetchall()]
    
    alerts = []
    for algo in algos:
        df = fetch_alpha_performance(algo)
        if len(df) < 30 or 'win_rate' not in df.columns:
            continue
            
        decay_wr, forecast_wr = model_decay(df['win_rate'])
        decay_ret, forecast_ret = model_decay(df['avg_return_pct'])
        
        if decay_wr > 0.1 or decay_ret > 0.05:  # Thresholds for alert
            alerts.append({
                'algo': algo,
                'decay_wr': decay_wr,
                'decay_ret': decay_ret,
                'forecast_30d_wr': forecast_wr.iloc[-1]
            })
    
    # Insert alerts to DB table (create lm_alpha_decay_alerts if needed)
    for alert in alerts:
        cursor.execute("""
        INSERT INTO lm_alpha_decay_alerts 
        (algo_name, decay_rate_wr, decay_rate_ret, forecast_wr, created_at)
        VALUES (%s, %s, %s, %s, NOW())
        """, (alert['algo'], alert['decay_wr'], alert['decay_ret'], alert['forecast_30d_wr']))
    
    conn.commit()
    conn.close()
    return len(alerts)

if __name__ == '__main__':
    num_alerts = monitor_decay()
    print(f"Generated {num_alerts} decay alerts")