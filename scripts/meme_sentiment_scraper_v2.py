# meme_sentiment_scraper_v2.py - Enhanced Meme Coin Sentiment Analyzer
# Fixed and expanded version with proper imports and multi-source sentiment
# Requirements: pip install beautifulsoup4 requests pandas mysql-connector-python fake-useragent vaderSentiment numpy

import os
import sys
import json
import time
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Try to import MySQL, fallback to JSON storage if not available
try:
    import mysql.connector
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False
    print("Warning: mysql-connector not available, using JSON storage fallback")

# Configuration
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

# Expanded meme coin list (top 50 by market cap + trending)
MEME_COINS = [
    # Tier 1: Established
    'DOGE', 'SHIB', 'PEPE', 'FLOKI', 'BONK', 'WIF', 'MEME', 'TURBO',
    # Tier 2: Emerging/Popular
    'POPCAT', 'PENGU', 'MOG', 'BOME', 'SLERF', 'MYRO', 'WEN', 'SNAP',
    'SC', 'SMOG', 'HONK', 'BODEN', 'TREMP', 'MAGA', 'TRUMP', 'PEOPLE',
    # Solana ecosystem
    'SAMO', 'GUAC', 'CHONKY', 'GIGA', 'POPDOG', 'NOS', 'PONKE',
    # Base ecosystem
    'DEGEN', 'TOSHI', 'BRETT', 'NORMIE', 'AERO', 'BSWAP',
    # ETH ecosystem
    'DOBO', 'SAFEMOON', 'ELON', 'AKITA', 'KISHU', 'LEASH', 'BONE',
    # Recently trending (will be updated dynamically)
    'PUNCH', 'BULLA', 'NEET', 'JELLYBEAN', 'BIRB', 'TIBBIR', 'A47'
]

# Reddit communities to monitor
REDDIT_SUBS = ['cryptocurrency', 'memecoin', 'SatoshiStreetBets', 'CryptoMoonShots', 'altcoin']

# Initialize
ua = UserAgent()
analyzer = SentimentIntensityAnalyzer()

def connect_db():
    """Connect to MySQL database"""
    if not HAS_MYSQL:
        return None
    try:
        return mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
        )
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None

def store_sentiment_json(coin, score, mentions, sources):
    """Fallback JSON storage if MySQL unavailable"""
    data_file = 'meme_sentiment_data.json'
    
    # Load existing data
    if os.path.exists(data_file):
        with open(data_file, 'r') as f:
            data = json.load(f)
    else:
        data = {}
    
    # Add new entry
    if coin not in data:
        data[coin] = []
    
    data[coin].append({
        'timestamp': datetime.utcnow().isoformat(),
        'score': float(score),
        'mentions': mentions,
        'sources': sources
    })
    
    # Keep only last 7 days
    cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
    for c in data:
        data[c] = [x for x in data[c] if x['timestamp'] > cutoff]
    
    # Save
    with open(data_file, 'w') as f:
        json.dump(data, f, indent=2)

def scrape_reddit(subreddit, query, limit=20):
    """Scrape Reddit for mentions of a coin"""
    url = f'https://www.reddit.com/r/{subreddit}/search?q={query}&restrict_sr=1&sort=new&t=day'
    headers = {'User-Agent': ua.random}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        posts = soup.find_all('div', class_='search-result')
        sentiments = []
        mentions = 0
        
        for post in posts[:limit]:
            try:
                title_elem = post.find('a', class_='search-title')
                snippet_elem = post.find('p', class_='search-snippet')
                
                if title_elem and snippet_elem:
                    text = title_elem.text + ' ' + snippet_elem.text
                    score = analyzer.polarity_scores(text)['compound']
                    sentiments.append(score)
                    mentions += 1
            except:
                continue
        
        return {
            'avg_sentiment': np.mean(sentiments) if sentiments else 0,
            'mentions': mentions,
            'sentiments': sentiments
        }
    except Exception as e:
        print(f"Reddit scrape error for {query} in {subreddit}: {e}")
        return {'avg_sentiment': 0, 'mentions': 0, 'sentiments': []}

def get_coin_trends():
    """Get trending coins from CoinGecko"""
    try:
        url = 'https://api.coingecko.com/api/v3/search/trending'
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        trending = []
        for coin in data.get('coins', []):
            symbol = coin['item']['symbol'].upper()
            trending.append(symbol)
        
        return trending
    except Exception as e:
        print(f"CoinGecko trending error: {e}")
        return []

def analyze_coin(coin):
    """Analyze sentiment for a single coin across all sources"""
    print(f"Analyzing {coin}...")
    
    # Reddit analysis
    reddit_scores = []
    total_mentions = 0
    
    for subreddit in REDDIT_SUBS:
        result = scrape_reddit(subreddit, coin, limit=10)
        if result['mentions'] > 0:
            reddit_scores.append(result['avg_sentiment'])
            total_mentions += result['mentions']
        time.sleep(0.5)  # Rate limiting
    
    # Calculate composite score
    if reddit_scores:
        avg_sentiment = np.mean(reddit_scores)
        sentiment_std = np.std(reddit_scores)
        
        # Weight by mention volume (more mentions = more reliable)
        volume_weight = min(total_mentions / 10, 2.0)  # Cap at 2x
        weighted_score = avg_sentiment * volume_weight
    else:
        avg_sentiment = 0
        sentiment_std = 0
        weighted_score = 0
        total_mentions = 0
    
    return {
        'coin': coin,
        'sentiment': float(avg_sentiment),
        'sentiment_std': float(sentiment_std),
        'mentions': total_mentions,
        'weighted_score': float(weighted_score),
        'timestamp': datetime.utcnow().isoformat()
    }

def generate_summary(results):
    """Generate summary of sentiment analysis"""
    if not results:
        return "No results to summarize"
    
    # Sort by weighted score
    sorted_results = sorted(results, key=lambda x: x['weighted_score'], reverse=True)
    
    print("\n" + "="*60)
    print("MEME COIN SENTIMENT SUMMARY")
    print("="*60)
    print(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("-"*60)
    
    print("\n🔥 MOST BULLISH (High Sentiment + High Mentions):")
    for r in sorted_results[:5]:
        if r['mentions'] > 0:
            print(f"  {r['coin']:12} | Sentiment: {r['sentiment']:+.3f} | Mentions: {r['mentions']:3d} | Score: {r['weighted_score']:+.3f}")
    
    print("\n❄️  MOST BEARISH:")
    for r in sorted_results[-5:]:
        if r['mentions'] > 0:
            print(f"  {r['coin']:12} | Sentiment: {r['sentiment']:+.3f} | Mentions: {r['mentions']:3d} | Score: {r['weighted_score']:+.3f}")
    
    print("\n📊 NO MENTIONS (Potential Early Entry):")
    no_mention_coins = [r for r in sorted_results if r['mentions'] == 0][:5]
    for r in no_mention_coins:
        print(f"  {r['coin']}")
    
    print("\n" + "="*60)
    
    # Save summary
    summary = {
        'timestamp': datetime.utcnow().isoformat(),
        'top_bullish': sorted_results[:5],
        'top_bearish': sorted_results[-5:],
        'no_mentions': no_mention_coins
    }
    
    with open('meme_sentiment_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    return summary

def run_full_analysis():
    """Run complete sentiment analysis on all tracked coins"""
    print(f"Starting Meme Coin Sentiment Analysis v2")
    print(f"Tracking {len(MEME_COINS)} coins across {len(REDDIT_SUBS)} subreddits")
    print("-"*60)
    
    results = []
    
    # Get trending coins first
    trending = get_coin_trends()
    print(f"Trending on CoinGecko: {', '.join(trending[:10])}")
    
    # Add trending coins to tracking if not already there
    for coin in trending:
        if coin not in MEME_COINS:
            MEME_COINS.append(coin)
    
    # Analyze each coin
    for coin in MEME_COINS:
        try:
            result = analyze_coin(coin)
            results.append(result)
            
            # Store to database or JSON
            conn = connect_db()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                    INSERT INTO meme_sentiment (coin, sentiment_score, mentions, weighted_score, fetch_date)
                    VALUES (%s, %s, %s, %s, NOW())
                    """, (coin, result['sentiment'], result['mentions'], result['weighted_score']))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print(f"DB store error: {e}")
                    store_sentiment_json(coin, result['sentiment'], result['mentions'], ['reddit'])
            else:
                store_sentiment_json(coin, result['sentiment'], result['mentions'], ['reddit'])
            
            time.sleep(1)  # Be nice to Reddit
            
        except Exception as e:
            print(f"Error analyzing {coin}: {e}")
            continue
    
    # Generate summary
    generate_summary(results)
    
    return results

def get_sentiment_signal(coin):
    """Get current sentiment signal for a coin (for scanner integration)"""
    data_file = 'meme_sentiment_data.json'
    
    if not os.path.exists(data_file):
        return {'sentiment': 0, 'mentions': 0, 'signal': 'neutral'}
    
    with open(data_file, 'r') as f:
        data = json.load(f)
    
    if coin not in data or not data[coin]:
        return {'sentiment': 0, 'mentions': 0, 'signal': 'neutral'}
    
    # Get latest entry
    latest = sorted(data[coin], key=lambda x: x['timestamp'], reverse=True)[0]
    
    sentiment = latest['score']
    mentions = latest['mentions']
    
    # Generate signal
    if sentiment > 0.3 and mentions > 5:
        signal = 'bullish'
    elif sentiment < -0.3 and mentions > 5:
        signal = 'bearish'
    elif mentions == 0:
        signal = 'undiscovered'
    else:
        signal = 'neutral'
    
    return {
        'sentiment': sentiment,
        'mentions': mentions,
        'signal': signal,
        'timestamp': latest['timestamp']
    }

if __name__ == '__main__':
    # Check for command line args
    if len(sys.argv) > 1:
        if sys.argv[1] == '--single' and len(sys.argv) > 2:
            # Analyze single coin
            coin = sys.argv[2].upper()
            result = analyze_coin(coin)
            print(json.dumps(result, indent=2))
        elif sys.argv[1] == '--signal' and len(sys.argv) > 2:
            # Get signal for coin
            coin = sys.argv[2].upper()
            print(json.dumps(get_sentiment_signal(coin), indent=2))
        else:
            print("Usage: python meme_sentiment_scraper_v2.py [--single COIN|--signal COIN]")
    else:
        # Run full analysis
        run_full_analysis()
