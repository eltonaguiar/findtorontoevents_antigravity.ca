#!/usr/bin/env python3
"""
WSB Sentiment Analyzer — Scans Reddit for stock sentiment.

Subreddits scanned:
  - r/wallstreetbets (primary, weight=1.0) — hot 100 + new 50
  - r/stocks (secondary, weight=0.6) — hot 50
  - r/investing (secondary, weight=0.4) — hot 50

For each post:
  1. Extract mentioned tickers using parse_tickers_from_text()
  2. Calculate simple keyword-based sentiment (-1 to +1)
  3. Aggregate per ticker: mentions, avg sentiment, total upvotes, wsb_score

wsb_score formula:
  mentions * 10 + sentiment * 50 + min(upvotes / 100, 50)

Requires REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET environment variables.
If not set, exits gracefully with a warning.
"""
import sys
import os
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT,
    TRACKED_TICKERS, WSB_EXTRA_TICKERS,
)
from utils import post_to_api, parse_tickers_from_text

logger = logging.getLogger('wsb_sentiment')

# Sentiment keyword lists
BULLISH_KEYWORDS = [
    'moon', 'rocket', 'tendies', 'calls', 'long', 'buy', 'undervalued',
    'squeeze', 'gamma', 'bull', 'ath', 'diamond hands', 'ape', 'yolo',
    'breakout', 'rally', 'mooning', 'ripping', 'lambo', 'printing',
    'free money', 'cant go tits up', 'to the moon', 'going up',
    'all in', 'doubled down', 'loaded up', 'cheap', 'dip buy',
]

BEARISH_KEYWORDS = [
    'crash', 'puts', 'short', 'sell', 'overvalued', 'bubble', 'bear',
    'dump', 'correction', 'recession', 'bankrupt', 'bag holder',
    'bagholding', 'rug pull', 'scam', 'ponzi', 'dead cat', 'drilling',
    'tanking', 'red', 'bleeding', 'loss porn', 'margin call', 'guh',
    'worthless', 'bagholder', 'going down', 'rip my portfolio',
]

# Known non-ticker words that look like tickers
TICKER_BLACKLIST = {
    'CEO', 'CFO', 'COO', 'CTO', 'IPO', 'ETF', 'SEC', 'FDA', 'NYSE',
    'NASDAQ', 'WSB', 'DD', 'YOLO', 'ATH', 'FYI', 'FOMO', 'IMO',
    'PSA', 'TLDR', 'TL', 'DR', 'OP', 'EPS', 'PE', 'ATM', 'ITM',
    'OTM', 'IV', 'DTE', 'EOD', 'EOW', 'EOM', 'SPY', 'QQQ', 'RSI',
    'THE', 'FOR', 'AND', 'NOT', 'ALL', 'ARE', 'BUT', 'CAN', 'HAS',
    'HIS', 'HOW', 'ITS', 'MAY', 'NEW', 'NOW', 'OLD', 'OUR', 'OUT',
    'OWN', 'SAY', 'SHE', 'TOO', 'USE', 'HER', 'WAS', 'ONE', 'WAY',
}


def init_reddit():
    """
    Initialize Reddit API client using praw.
    Returns praw.Reddit instance or None if credentials not set.
    """
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        logger.warning(
            "Reddit credentials not set (REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET). "
            "WSB sentiment tracking will be skipped."
        )
        return None

    try:
        import praw
    except ImportError:
        logger.warning(
            "praw library not installed. Install with: pip install praw. "
            "WSB sentiment tracking will be skipped."
        )
        return None

    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
        )
        # Test the connection
        reddit.read_only = True
        logger.info("Reddit API connection established (read-only mode)")
        return reddit
    except Exception as e:
        logger.error(f"Failed to initialize Reddit client: {e}")
        return None


def calculate_sentiment(text):
    """
    Calculate simple keyword-based sentiment score from text.
    Returns float in range [-1, 1].
    """
    text_lower = text.lower()
    bull_count = 0
    bear_count = 0

    for kw in BULLISH_KEYWORDS:
        if kw in text_lower:
            bull_count += 1

    for kw in BEARISH_KEYWORDS:
        if kw in text_lower:
            bear_count += 1

    total = bull_count + bear_count
    if total == 0:
        return 0.0

    return (bull_count - bear_count) / total


def extract_tickers_filtered(text):
    """Extract tickers from text, filtering out common non-ticker words."""
    raw = parse_tickers_from_text(text)
    return [t for t in raw if t not in TICKER_BLACKLIST]


def scan_subreddit(reddit, subreddit_name, hot_limit=100, new_limit=50, weight=1.0):
    """
    Scan a subreddit for ticker mentions and sentiment.
    Returns list of (ticker, sentiment, upvotes, title, weight) tuples.
    """
    results = []
    cutoff = datetime.utcnow() - timedelta(hours=24)
    seen_ids = set()

    try:
        subreddit = reddit.subreddit(subreddit_name)
    except Exception as e:
        logger.warning(f"Failed to access r/{subreddit_name}: {e}")
        return results

    # Scan hot posts
    try:
        for post in subreddit.hot(limit=hot_limit):
            if post.id in seen_ids:
                continue
            seen_ids.add(post.id)

            # Check age (only last 24 hours)
            post_time = datetime.utcfromtimestamp(post.created_utc)
            if post_time < cutoff:
                continue

            text = f"{post.title} {post.selftext or ''}"
            tickers = extract_tickers_filtered(text)
            if not tickers:
                continue

            sentiment = calculate_sentiment(text)
            upvotes = post.score

            for ticker in tickers:
                results.append({
                    'ticker': ticker,
                    'sentiment': sentiment,
                    'upvotes': upvotes,
                    'title': post.title[:200],
                    'weight': weight,
                    'source': f'r/{subreddit_name}',
                    'post_id': post.id,
                })
    except Exception as e:
        logger.warning(f"Error scanning r/{subreddit_name} hot: {e}")

    # Scan new posts
    try:
        for post in subreddit.new(limit=new_limit):
            if post.id in seen_ids:
                continue
            seen_ids.add(post.id)

            post_time = datetime.utcfromtimestamp(post.created_utc)
            if post_time < cutoff:
                continue

            text = f"{post.title} {post.selftext or ''}"
            tickers = extract_tickers_filtered(text)
            if not tickers:
                continue

            sentiment = calculate_sentiment(text)
            upvotes = post.score

            for ticker in tickers:
                results.append({
                    'ticker': ticker,
                    'sentiment': sentiment,
                    'upvotes': upvotes,
                    'title': post.title[:200],
                    'weight': weight,
                    'source': f'r/{subreddit_name}',
                    'post_id': post.id,
                })
    except Exception as e:
        logger.warning(f"Error scanning r/{subreddit_name} new: {e}")

    logger.info(f"r/{subreddit_name}: scanned {len(seen_ids)} posts, found {len(results)} ticker mentions")
    return results


def aggregate_results(all_mentions):
    """
    Aggregate per-ticker mentions into summary scores.
    Returns sorted list of ticker summary dicts.
    """
    ticker_data = defaultdict(lambda: {
        'mentions': 0,
        'sentiments': [],
        'total_upvotes': 0,
        'weighted_sentiments': [],
        'top_post_title': '',
        'top_post_upvotes': 0,
        'sources': set(),
    })

    for m in all_mentions:
        ticker = m['ticker']
        td = ticker_data[ticker]
        td['mentions'] += 1
        td['sentiments'].append(m['sentiment'])
        td['weighted_sentiments'].append(m['sentiment'] * m['weight'])
        td['total_upvotes'] += m['upvotes']
        td['sources'].add(m['source'])

        if m['upvotes'] > td['top_post_upvotes']:
            td['top_post_upvotes'] = m['upvotes']
            td['top_post_title'] = m['title']

    results = []
    for ticker, data in ticker_data.items():
        mentions = data['mentions']
        sentiments = data['weighted_sentiments']
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        avg_sentiment = max(-1.0, min(1.0, avg_sentiment))  # Clamp

        # wsb_score = mentions * 10 + sentiment * 50 + min(upvotes / 100, 50)
        upvote_bonus = min(data['total_upvotes'] / 100.0, 50.0)
        wsb_score = mentions * 10 + avg_sentiment * 50 + upvote_bonus

        results.append({
            'ticker': ticker,
            'mentions_24h': mentions,
            'sentiment': round(avg_sentiment, 3),
            'total_upvotes': data['total_upvotes'],
            'wsb_score': round(wsb_score, 2),
            'top_post_title': data['top_post_title'],
            'sources': list(data['sources']),
        })

    # Sort by wsb_score descending
    results.sort(key=lambda x: x['wsb_score'], reverse=True)

    # Return top 20
    return results[:20]


def main():
    """Main entry point for WSB sentiment analysis."""
    logger.info("=" * 60)
    logger.info("WSB Sentiment Analyzer — Starting")
    logger.info("=" * 60)

    reddit = init_reddit()
    if reddit is None:
        logger.info("Reddit client not available — exiting gracefully")
        return {'skipped': True, 'reason': 'no_credentials'}

    all_mentions = []

    # Scan subreddits with different weights
    subreddits = [
        ('wallstreetbets', 100, 50, 1.0),
        ('stocks', 50, 0, 0.6),
        ('investing', 50, 0, 0.4),
    ]

    for sub_name, hot_limit, new_limit, weight in subreddits:
        try:
            mentions = scan_subreddit(reddit, sub_name, hot_limit, new_limit, weight)
            all_mentions.extend(mentions)
        except Exception as e:
            logger.error(f"Error scanning r/{sub_name}: {e}")

    if not all_mentions:
        logger.info("No ticker mentions found in any subreddit")
        return {'mentions': 0, 'tickers': 0}

    # Aggregate
    top_tickers = aggregate_results(all_mentions)

    # POST to API
    today = datetime.utcnow().strftime('%Y-%m-%d')
    payload = {
        'scan_date': today,
        'tickers': top_tickers,
        'total_mentions': len(all_mentions),
        'subreddits_scanned': [s[0] for s in subreddits],
    }

    result = post_to_api('ingest_wsb', payload)
    if not result.get('ok'):
        logger.warning(f"API ingest_wsb failed: {result.get('error', 'unknown')}")
        logger.info("Logging results locally instead:")

    # Summary
    logger.info("=" * 60)
    logger.info("WSB SENTIMENT SUMMARY")
    logger.info(f"  Total mentions found: {len(all_mentions)}")
    logger.info(f"  Unique tickers:       {len(top_tickers)}")
    logger.info("")

    if top_tickers:
        logger.info("  Top tickers by WSB score:")
        logger.info(f"  {'Ticker':6s} | {'Mentions':>8s} | {'Sentiment':>9s} | {'Upvotes':>8s} | {'Score':>8s} | Top Post")
        logger.info(f"  {'-'*6}-+-{'-'*8}-+-{'-'*9}-+-{'-'*8}-+-{'-'*8}-+-{'-'*30}")
        for t in top_tickers[:10]:
            sent_label = 'bullish' if t['sentiment'] > 0.1 else ('bearish' if t['sentiment'] < -0.1 else 'neutral')
            logger.info(
                f"  {t['ticker']:6s} | {t['mentions_24h']:8d} | {t['sentiment']:+8.3f} | "
                f"{t['total_upvotes']:8d} | {t['wsb_score']:8.1f} | {t['top_post_title'][:40]}"
            )

    logger.info("=" * 60)

    return {
        'mentions': len(all_mentions),
        'tickers': len(top_tickers),
        'top': top_tickers[:5],
    }


if __name__ == '__main__':
    main()
