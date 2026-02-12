#!/usr/bin/env python3
"""
Social Sentiment Tracker for Crypto/Memecoins
Uses Twitter API v2 to track mentions, sentiment, and viral patterns

Features:
- Track crypto/memecoin mentions on Twitter
- Analyze sentiment (positive/negative/neutral)
- Monitor crypto influencers
- Detect viral patterns

Usage:
    python social_sentiment.py --track BTC ETH SOL
    python social_sentiment.py --influencers
"""

import os
import sys
import requests
import mysql.connector
from datetime import datetime, timedelta
import logging
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# Twitter API v2 Bearer Token
TWITTER_BEARER_TOKEN = os.environ.get('X_BEARER', '')

# Database connection
DB_CONFIG = {
    'host': 'mysql.50webs.com',
    'user': 'ejaguiar1_stocks',
    'password': 'stocks',  # Correct password from sports_ml.py
    'database': 'ejaguiar1_stocks'  # Use existing database, add social sentiment tables
}

# Crypto influencers to monitor
CRYPTO_INFLUENCERS = [
    'elonmusk',
    'VitalikButerin',
    'CZ_Binance',
    'cz_binance',
    'SBF_FTX',
    'aantonop',
    'APompliano',
    'naval',
    'balajis',
]

def connect_db():
    """Connect to MySQL database"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        log.error(f"Database connection failed: {e}")
        return None

def create_tables(conn):
    """Create social sentiment tables"""
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS social_sentiment (
            id INT AUTO_INCREMENT PRIMARY KEY,
            asset_class VARCHAR(20) NOT NULL,
            symbol VARCHAR(20) NOT NULL,
            platform VARCHAR(20) NOT NULL,
            mention_count_24h INT DEFAULT 0,
            sentiment_score DECIMAL(3,2),
            engagement_score INT DEFAULT 0,
            influencer_mentions INT DEFAULT 0,
            viral_coefficient DECIMAL(5,2),
            calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_symbol_platform (symbol, platform),
            INDEX idx_time (calculated_at)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS social_influencers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            platform VARCHAR(20) NOT NULL,
            username VARCHAR(100) NOT NULL,
            follower_count INT,
            influence_score DECIMAL(5,2),
            category VARCHAR(50),
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY unique_influencer (platform, username)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8
    """)
    
    conn.commit()
    cursor.close()
    log.info("Social sentiment tables created/verified")

def get_twitter_headers():
    """Get Twitter API headers"""
    if not TWITTER_BEARER_TOKEN:
        log.error("X_BEARER token not found in environment")
        return None
    
    return {
        'Authorization': f'Bearer {TWITTER_BEARER_TOKEN}',
        'User-Agent': 'v2RecentSearchPython'
    }

def track_crypto_mentions(conn, symbols):
    """Track crypto mentions on Twitter"""
    headers = get_twitter_headers()
    if not headers:
        return
    
    cursor = conn.cursor()
    
    for symbol in symbols:
        try:
            # Search for recent tweets mentioning the symbol
            query = f"${symbol} OR #{symbol} OR {symbol} -is:retweet lang:en"
            url = f"https://api.twitter.com/2/tweets/search/recent?query={query}&max_results=100&tweet.fields=created_at,public_metrics"
            
            resp = requests.get(url, headers=headers, timeout=15)
            
            if resp.status_code != 200:
                log.warning(f"Twitter API error for {symbol}: {resp.status_code}")
                continue
            
            data = resp.json()
            
            if 'data' not in data:
                log.info(f"No tweets found for {symbol}")
                continue
            
            tweets = data['data']
            mention_count = len(tweets)
            total_engagement = 0
            influencer_mentions = 0
            
            # Calculate engagement and sentiment
            for tweet in tweets:
                metrics = tweet.get('public_metrics', {})
                engagement = (
                    metrics.get('like_count', 0) +
                    metrics.get('retweet_count', 0) * 2 +  # Retweets worth more
                    metrics.get('reply_count', 0)
                )
                total_engagement += engagement
            
            # Simple sentiment analysis (can be enhanced with NLP)
            sentiment_score = 0.0  # Neutral for now
            
            # Viral coefficient (engagement per mention)
            viral_coefficient = total_engagement / mention_count if mention_count > 0 else 0
            
            # Store sentiment data
            cursor.execute("""
                INSERT INTO social_sentiment 
                (asset_class, symbol, platform, mention_count_24h, sentiment_score, engagement_score, influencer_mentions, viral_coefficient)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, ('crypto', symbol, 'twitter', mention_count, sentiment_score, total_engagement, influencer_mentions, viral_coefficient))
            
            log.info(f"{symbol}: {mention_count} mentions, {total_engagement} engagement, viral_coef={viral_coefficient:.2f}")
            
        except Exception as e:
            log.error(f"Failed to track {symbol}: {e}")
    
    conn.commit()
    cursor.close()

def monitor_influencers(conn):
    """Monitor crypto influencer activity"""
    headers = get_twitter_headers()
    if not headers:
        return
    
    cursor = conn.cursor()
    
    for username in CRYPTO_INFLUENCERS:
        try:
            # Get user info
            url = f"https://api.twitter.com/2/users/by/username/{username}?user.fields=public_metrics"
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code != 200:
                continue
            
            data = resp.json()
            if 'data' not in data:
                continue
            
            user = data['data']
            follower_count = user.get('public_metrics', {}).get('followers_count', 0)
            
            # Calculate influence score (simplified)
            influence_score = min(100, follower_count / 100000)  # 10M followers = 100 score
            
            cursor.execute("""
                INSERT INTO social_influencers (platform, username, follower_count, influence_score, category)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE follower_count=%s, influence_score=%s
            """, ('twitter', username, follower_count, influence_score, 'crypto', follower_count, influence_score))
            
            log.info(f"@{username}: {follower_count:,} followers, influence={influence_score:.1f}")
            
        except Exception as e:
            log.warning(f"Failed to process @{username}: {e}")
    
    conn.commit()
    cursor.close()

def main():
    """Main execution"""
    import argparse
    parser = argparse.ArgumentParser(description='Social Sentiment Tracker')
    parser.add_argument('--track', nargs='+', help='Track crypto symbols (e.g., BTC ETH SOL)')
    parser.add_argument('--influencers', action='store_true', help='Monitor influencers')
    parser.add_argument('--setup', action='store_true', help='Setup database tables')
    args = parser.parse_args()
    
    conn = connect_db()
    if not conn:
        log.error("Failed to connect to database")
        return
    
    try:
        if args.setup:
            create_tables(conn)
        
        if args.track:
            track_crypto_mentions(conn, args.track)
        
        if args.influencers:
            monitor_influencers(conn)
        
        if not any([args.track, args.influencers, args.setup]):
            # Default: track major cryptos
            create_tables(conn)
            track_crypto_mentions(conn, ['BTC', 'ETH', 'SOL', 'DOGE'])
            
    finally:
        conn.close()

if __name__ == '__main__':
    main()
