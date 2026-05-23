# garch_vol.py - GARCH volatility forecasting for sizing
# Requirements: pip install arch pandas yfinance requests

import os
import sys
import pandas as pd
import yfinance as yf
from arch import arch_model

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import call_api, post_to_api

def fetch_returns(ticker, period='1y'):
    data = yf.download(ticker, period=period)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data = data['Adj Close'] if 'Adj Close' in data.columns else data['Close']
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
    data = call_api('get_position_sizing')
    if not data or not data.get('ok'):
        print('get_position_sizing API failed or returned no data')
        return

    # Expect list of {algorithm_name, half_kelly or kelly_fraction, ...}
    rows = data.get('sizing', data.get('rows', data.get('data', [])))
    if isinstance(rows, dict):
        rows = [rows]
    if not rows:
        return

    returns = fetch_returns('SPY')
    vol = forecast_vol(returns)

    for row in rows:
        algo = row.get('algorithm_name', row.get('algo_name', ''))
        if not algo:
            continue
        kelly = float(row.get('half_kelly') or row.get('kelly_fraction') or row.get('full_kelly') or 0.1)
        adjusted = adjust_kelly(kelly, vol)
        post_to_api('update_position_sizing', {
            'algorithm_name': algo,
            'vol_adjusted_kelly': round(adjusted, 4),
            'vol_forecast': round(vol, 4),
        })

if __name__ == '__main__':
    run_vol_forecast()
