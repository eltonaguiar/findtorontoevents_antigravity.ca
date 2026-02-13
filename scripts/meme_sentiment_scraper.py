#!/usr/bin/env python3
"""
Meme Coin Sentiment Scraper -- v2.0

Fetches sentiment signals from CoinGecko trending API and Reddit
(via old.reddit.com for reliability). Stores results in ejaguiar1_memecoin
database for consumption by meme_scanner.php.

v2.0 FIXES (Feb 2026):
  - Fixed: numpy import was missing (crashed on line 41)
  - Fixed: database was ejaguiar1_stocks, now ejaguiar1_memecoin
  - Fixed: Reddit scraping uses old.reddit.com JSON endpoint
  - Fixed: coin list expanded from 4 to match unified scanner list
  - Added: CoinGecko trending coins as additional signal
  - Added: proper error handling

Requirements:
  pip install requests mysql-connector-python vaderSentiment
"""
import os
import sys
import json
import time
import requests
from datetime import datetime

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    analyzer = SentimentIntensityAnalyzer()
except ImportError:
    print("WARNING: vaderSentiment not installed. Run: pip install vaderSentiment")
    analyzer = None

# DB config -- FIXED: was ejaguiar1_stocks, now correct memecoin DB
DB_HOST = os.getenv('MEME_DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('MEME_DB_USER', 'ejaguiar1_memecoin')
DB_PASS = os.getenv('MEME_DB_PASS', 'testing123')
DB_NAME = os.getenv('MEME_DB_NAME', 'ejaguiar1_memecoin')

# UNIFIED coin list -- matches kraken_meme_scanner.php _kraken_get_meme_pairs()
MEME_COINS = [
    'PEPE', 'FLOKI', 'BONK', 'SHIB', 'DOGE', 'WIF',
    'MOG', 'POPCAT', 'NEIRO', 'GIGA', 'SPX', 'PONKE',
    'TURBO',  # Also in main scanner tier 1
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


def connect_db():
    """Connect to the meme coin MySQL database."""
    import mysql.connector
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME,
        connect_timeout=15,
    )


def ensure_table(conn):
    """Ensure sentiment table exists."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mc_sentiment (
            id INT AUTO_INCREMENT PRIMARY KEY,
            coin VARCHAR(20) NOT NULL,
            reddit_score DECIMAL(5,3) DEFAULT 0,
            trending_score DECIMAL(5,3) DEFAULT 0,
            combined_score DECIMAL(5,3) DEFAULT 0,
            post_count INT DEFAULT 0,
            source VARCHAR(50),
            created_at DATETIME NOT NULL,
            INDEX idx_coin (coin),
            INDEX idx_created (created_at)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8
    """)
    conn.commit()
    cursor.close()


def scrape_reddit_sentiment(coin, subreddits=None):
    """
    Scrape Reddit sentiment using old.reddit.com JSON endpoint.
    Returns (sentiment_score, post_count).
    """
    if analyzer is None:
        return 0.0, 0

    if subreddits is None:
        subreddits = ['cryptocurrency', 'memecoin', 'CryptoMoonShots']

    all_sentiments = []

    for sub in subreddits:
        try:
            url = f'https://old.reddit.com/r/{sub}/search.json'
            params = {
                'q': coin,
                'restrict_sr': 1,
                'sort': 'new',
                't': 'day',  # Last 24 hours only
                'limit': 25,
            }
            resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
            if resp.status_code != 200:
                continue

            data = resp.json()
            posts = data.get('data', {}).get('children', [])

            for post in posts:
                post_data = post.get('data', {})
                title = post_data.get('title', '')
                selftext = post_data.get('selftext', '')[:500]  # Limit text length
                text = f"{title} {selftext}"

                score = analyzer.polarity_scores(text)['compound']
                all_sentiments.append(score)

            # Rate limit between subreddit requests
            time.sleep(1)

        except Exception as e:
            print(f"  Reddit scrape error for {coin} in r/{sub}: {e}")
            continue

    if not all_sentiments:
        return 0.0, 0

    avg = sum(all_sentiments) / len(all_sentiments)
    return round(avg, 3), len(all_sentiments)


def check_coingecko_trending():
    """
    Check CoinGecko trending coins to see if any meme coins are trending.
    Returns dict of {coin_symbol: trending_score}.
    """
    trending_scores = {}

    try:
        url = 'https://api.coingecko.com/api/v3/search/trending'
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            print(f"  CoinGecko trending API returned {resp.status_code}")
            return trending_scores

        data = resp.json()
        coins = data.get('coins', [])

        for i, entry in enumerate(coins):
            item = entry.get('item', {})
            symbol = item.get('symbol', '').upper()

            if symbol in MEME_COINS:
                # Higher score for higher-ranked trending coins
                score = round(1.0 - (i * 0.1), 2)  # 1.0 for #1, 0.9 for #2, etc.
                trending_scores[symbol] = max(0.1, score)

    except Exception as e:
        print(f"  CoinGecko trending error: {e}")

    return trending_scores


def store_sentiment(conn, coin, reddit_score, trending_score, post_count, source):
    """Store sentiment result in database."""
    combined = round(reddit_score * 0.6 + trending_score * 0.4, 3)

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO mc_sentiment (coin, reddit_score, trending_score, combined_score, post_count, source, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
    """, (coin, reddit_score, trending_score, combined, post_count, source))
    conn.commit()
    cursor.close()

    return combined


def run_scraper():
    """Main scraper execution."""
    print("=" * 60)
    print("  MEME COIN SENTIMENT SCRAPER v2.0")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    # Connect to database
    conn = None
    try:
        conn = connect_db()
        ensure_table(conn)
        print(f"\n  Connected to {DB_NAME}")
    except Exception as e:
        print(f"\n  FATAL: Cannot connect to database: {e}")
        sys.exit(1)

    # Get CoinGecko trending data (one call for all coins)
    print("\n  Checking CoinGecko trending...")
    trending_scores = check_coingecko_trending()
    if trending_scores:
        print(f"  Trending meme coins: {trending_scores}")
    else:
        print("  No meme coins currently trending on CoinGecko")

    # Scrape Reddit sentiment for each coin
    print(f"\n  Scraping sentiment for {len(MEME_COINS)} coins...")
    results = []

    for coin in MEME_COINS:
        reddit_score, post_count = scrape_reddit_sentiment(coin)
        trending_score = trending_scores.get(coin, 0.0)

        combined = store_sentiment(conn, coin, reddit_score, trending_score, post_count, 'reddit+coingecko')
        results.append({
            'coin': coin,
            'reddit': reddit_score,
            'trending': trending_score,
            'combined': combined,
            'posts': post_count,
        })

        symbol = '+' if combined > 0.1 else ('-' if combined < -0.1 else '~')
        print(f"  [{symbol}] {coin:8s}  reddit={reddit_score:+.3f}  trending={trending_score:.2f}  combined={combined:+.3f}  ({post_count} posts)")

        # Rate limit
        time.sleep(2)

    # Summary
    print("\n" + "=" * 60)
    positive = sum(1 for r in results if r['combined'] > 0.1)
    negative = sum(1 for r in results if r['combined'] < -0.1)
    neutral = len(results) - positive - negative
    print(f"  DONE: {positive} bullish, {neutral} neutral, {negative} bearish")
    print("=" * 60)

    if conn:
        conn.close()


if __name__ == '__main__':
    run_scraper()