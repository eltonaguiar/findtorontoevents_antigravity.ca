# api_integrations.py - Free API integrations with failovers
# Requirements: pip install yfinance requests pandas mysql-connector-python

import os
import yfinance as yf
import requests
import pandas as pd
import mysql.connector

# DB config
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

# Alpha Vantage key from env
AV_KEY = os.getenv('ALPHA_VANTAGE_KEY')

def connect_db():
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
    )

def fetch_alpha_vantage(function, symbol):
    base = 'https://www.alphavantage.co/query'
    params = {'function': function, 'symbol': symbol, 'apikey': AV_KEY}
    try:
        resp = requests.get(base, params=params)
        resp.raise_for_status()
        return resp.json()
    except:
        return None

def fetch_data(ticker, source='yfinance'):
    if source == 'yfinance':
        data = yf.download(ticker, period='1y')
        if not data.empty:
            return data
            
    if source == 'alphavantage' and AV_KEY:
        data = fetch_alpha_vantage('TIME_SERIES_DAILY', ticker)
        if data:
            return data
            
    # Failover to scrapers
    from yahoo_scraper import scrape_yahoo
    scraped = scrape_yahoo(ticker)
    if scraped is not None and not scraped.empty:
        return scraped
        
    from investing_scraper import scrape_investing
    scraped = scrape_investing(ticker)
    if scraped is not None and not scraped.empty:
        return scraped
        
    return None
    if source == 'yfinance':
        return yf.download(ticker, period='1y')
    elif source == 'alphavantage':
        data = fetch_alpha_vantage('TIME_SERIES_DAILY', ticker)
        if data and 'Time Series (Daily)' in data:
            df = pd.DataFrame(data['Time Series (Daily)']).T
            df = df.astype(float)
            df.index = pd.to_datetime(df.index)
            return df[['1. open', '2. high', '3. low', '4. close', '5. volume']]
    return None

def store_data(df, ticker):
    conn = connect_db()
    cursor = conn.cursor()
    
    for date, row in df.iterrows():
        cursor.execute("""
        INSERT INTO daily_prices 
        (ticker, trade_date, open_price, high_price, low_price, close_price, volume)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
        open_price=VALUES(open_price), high_price=VALUES(high_price),
        low_price=VALUES(low_price), close_price=VALUES(close_price),
        volume=VALUES(volume)
        """, (ticker, date.date(), row['Open'], row['High'], row['Low'], row['Close'], int(row['Volume'])))
    
    conn.commit()
    conn.close()

def run_integrations(tickers):
    for t in tickers:
        data = fetch_data(t, 'yfinance')
        if data is None or data.empty:
            print(f"yfinance failed for {t}, trying Alpha Vantage")
            data = fetch_data(t, 'alphavantage')
        if data is not None and not data.empty:
            store_data(data, t)
            print(f"Stored data for {t}")

if __name__ == '__main__':
    tickers = ['AAPL', 'MSFT', 'GOOGL']  # Example
    run_integrations(tickers)