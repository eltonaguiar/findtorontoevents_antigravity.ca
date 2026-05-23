# investing_scraper.py - Scraper for Investing.com data
# Similar structure to yahoo_scraper.py

import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import mysql.connector
from fake_useragent import UserAgent

# DB config same as above

ua = UserAgent()

def scrape_investing(ticker):
    url = f'https://www.investing.com/equities/{ticker.lower()}-historical-data'
    headers = {'User-Agent': ua.random}
    
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        table = soup.find('table', id='curr_table')
        if not table:
            return None
            
        rows = table.find('tbody').find_all('tr')
        data = []
        for row in rows[:252]:
            cols = row.find_all('td')
            if len(cols) < 7: continue
            date = cols[0].text
            close = float(cols[1].text.replace(',', ''))
            open_p = float(cols[2].text.replace(',', ''))
            high = float(cols[3].text.replace(',', ''))
            low = float(cols[4].text.replace(',', ''))
            volume = cols[5].text  # May need parsing (K/M)
            # Parse volume
            if 'K' in volume:
                volume = float(volume.replace('K', '')) * 1000
            elif 'M' in volume:
                volume = float(volume.replace('M', '')) * 1000000
            else:
                volume = float(volume.replace(',', ''))
            data.append({
                'date': date,
                'open': open_p,
                'high': high,
                'low': low,
                'close': close,
                'volume': int(volume)
            })
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        return df
    except:
        return None

# store_scraped_data same as yahoo

if __name__ == '__main__':
    tickers = ['apple-computer-inc']
    for t in tickers:
        df = scrape_investing(t)
        if df is not None:
            store_scraped_data(df, 'AAPL')  # Map symbol
            print(f"Scraped Investing.com for {t}")