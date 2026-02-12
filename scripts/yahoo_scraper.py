# yahoo_scraper.py - Web scraper for Yahoo Finance data
# Requirements: pip install beautifulsoup4 requests pandas mysql-connector-python fake-useragent

import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import mysql.connector
from fake_useragent import UserAgent

# DB config
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

ua = UserAgent()

def connect_db():
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
    )

def scrape_yahoo(ticker):
    url = f'https://finance.yahoo.com/quote/{ticker}/history?p={ticker}'
    headers = {'User-Agent': ua.random}
    
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        table = soup.find('table', {'data-test': 'historical-prices'})
        if not table:
            return None
            
        rows = table.find('tbody').find_all('tr')
        data = []
        for row in rows[:252]:  # Last year approx
            cols = row.find_all('td')
            if len(cols) < 7: continue
            date = cols[0].text
            open_p = float(cols[1].text.replace(',', ''))
            high = float(cols[2].text.replace(',', ''))
            low = float(cols[3].text.replace(',', ''))
            close = float(cols[4].text.replace(',', ''))
            volume = int(cols[6].text.replace(',', ''))
            data.append({
                'date': date,
                'open': open_p,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        return df
    except:
        return None

def store_scraped_data(df, ticker):
    conn = connect_db()
    cursor = conn.cursor()
    
    for _, row in df.iterrows():
        cursor.execute("""
        INSERT INTO daily_prices 
        (ticker, trade_date, open_price, high_price, low_price, close_price, volume)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
        open_price=VALUES(open_price), high_price=VALUES(high_price),
        low_price=VALUES(low_price), close_price=VALUES(close_price),
        volume=VALUES(volume)
        """, (ticker, row['date'].date(), row['open'], row['high'], row['low'], row['close'], row['volume']))
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    tickers = ['AAPL', 'MSFT']  # Example
    for t in tickers:
        df = scrape_yahoo(t)
        if df is not None:
            store_scraped_data(df, t)
            print(f"Scraped and stored {t}")