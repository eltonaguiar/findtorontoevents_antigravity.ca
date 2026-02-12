# meme_sentiment_scraper.py - Scraper for meme coin sentiment
# Requirements: pip install beautifulsoup4 requests pandas mysql-connector-python fake-useragent vaderSentiment

import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import mysql.connector
from fake_useragent import UserAgent
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# DB config
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

ua = UserAgent()
analyzer = SentimentIntensityAnalyzer()

def connect_db():
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
    )

def scrape_reddit(subreddit, query):
    url = f'https://www.reddit.com/r/{subreddit}/search?q={query}&restrict_sr=1&sort=new'
    headers = {'User-Agent': ua.random}
    
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        posts = soup.find_all('div', class_='search-result')
        sentiments = []
        for post in posts[:20]:
            text = post.find('a', class_='search-title').text + ' ' + post.find('p', class_='search-snippet').text
            score = analyzer.polarity_scores(text)['compound']
            sentiments.append(score)
        return np.mean(sentiments) if sentiments else 0
    except:
        return 0

def store_sentiment(coin, score):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO meme_sentiment (coin, score, fetch_date)
    VALUES (%s, %s, NOW())
    """, (coin, score))
    conn.commit()
    conn.close()

def run_scraper():
    memes = ['DOGE', 'SHIB', 'PEPE', 'FLOKI']
    for m in memes:
        score = scrape_reddit('cryptocurrency', m) * 0.5 + scrape_reddit('memecoin', m) * 0.5
        store_sentiment(m, score)
        print(f"{m} sentiment: {score:.2f}")

if __name__ == '__main__':
    run_scraper()