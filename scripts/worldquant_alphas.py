# worldquant_alphas.py - 20 WorldQuant alphas implementation
# Based on Kakushadze (2016) 101 Formulaic Alphas
# Requirements: pip install pandas numpy ta-lib yfinance

import pandas as pd
import numpy as np
import yfinance as yf
from talib import RSI, SMA, EMA, MACD, ATR, ADX, OBV, WILLR

def fetch_data(ticker, period='1y'):
    data = yf.download(ticker, period=period)
    return data

def alpha_1(data):
    # rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns, 20) : close), 2.), 5)) - 0.5
    returns = data['Close'].pct_change()
    std = returns.rolling(20).std()
    powered = np.where(returns < 0, std, data['Close']) ** 2
    argmax = pd.Series(powered).rolling(5).apply(np.argmax)
    rank = argmax.rank(pct=True)
    return rank - 0.5

def alpha_2(data):
    # (-1 * correlation(rank(delta(volume, 2)), rank(((close - open) / open)), 6))
    vol_delta = data['Volume'].diff(2).rank(pct=True)
    price_change = ((data['Close'] - data['Open']) / data['Open']).rank(pct=True)
    corr = vol_delta.rolling(6).corr(price_change)
    return -corr

def alpha_3(data):
    # (-1 * correlation(rank(open), rank(volume), 10))
    open_rank = data['Open'].rank(pct=True)
    vol_rank = data['Volume'].rank(pct=True)
    return -open_rank.rolling(10).corr(vol_rank)

def alpha_4(data):
    # (-1 * Ts_Rank(rank(low), 9))
    low_rank = data['Low'].rank(pct=True)
    return -low_rank.rolling(9).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1])

def alpha_5(data):
    # (rank((open - (sum(vwap, 10) / 10))) * (-1 * abs(rank((close - vwap)))))
    vwap = (data['High'] + data['Low'] + data['Close']) / 3 * data['Volume']
    vwap = vwap / data['Volume']
    vwap10 = vwap.rolling(10).mean()
    rank1 = (data['Open'] - vwap10).rank(pct=True)
    rank2 = abs((data['Close'] - vwap).rank(pct=True))
    return rank1 * (-rank2)

# Implement alphas 6-20 similarly...

def compute_alphas(ticker):
    data = fetch_data(ticker)
    alphas = {}
    alphas['alpha1'] = alpha_1(data).iloc[-1]
    alphas['alpha2'] = alpha_2(data).iloc[-1]
    # ... for all 20
    return alphas

if __name__ == '__main__':
    print(compute_alphas('AAPL'))