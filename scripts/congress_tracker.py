#!/usr/bin/env python3
"""
Congressional Trading Tracker — Follow the politicians' stock trades.

Studies show US Congress members outperform the market by 6-12% annually.
Their trades are disclosed with a 45-day delay, but still profitable to follow.

Data source: House Stock Watcher (public S3 bucket, no API key needed)
  https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json

Pipeline:
  1. Fetch all congressional transactions (public JSON)
  2. Filter to recent purchases >$15K
  3. Identify "cluster buys" — tickers bought by 3+ members
  4. Cross-reference with our tracked tickers
  5. Post signals to world_class_intelligence.php

Requires: pip install requests
Runs via: python run_all.py --congress
"""
import sys
import os
import json
import logging
import warnings
from datetime import datetime, timedelta
from collections import Counter

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import post_to_api, safe_request
from config import API_BASE, ADMIN_KEY, TRACKED_TICKERS, WSB_EXTRA_TICKERS

logger = logging.getLogger('congress_tracker')

HOUSE_DATA_URL = "https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json"
SENATE_DATA_URL = "https://senate-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json"

# All tickers we care about
ALL_TICKERS = set(TRACKED_TICKERS + WSB_EXTRA_TICKERS)


# ---------------------------------------------------------------------------
# Data Fetching
# ---------------------------------------------------------------------------

def fetch_transactions(url, source_name):
    """Fetch congressional transactions from public S3 bucket."""
    logger.info("  Fetching %s transactions...", source_name)
    resp = safe_request(url, timeout=30)
    if resp is None:
        logger.warning("  Failed to fetch %s data", source_name)
        return []

    try:
        data = resp.json()
        logger.info("  Fetched %d %s transactions", len(data), source_name)
        return data
    except Exception as e:
        logger.warning("  Failed to parse %s data: %s", source_name, e)
        return []


def parse_amount(amount_str):
    """
    Parse congressional disclosure amount ranges into estimated dollar value.
    Disclosures use ranges like '$1,001 - $15,000', '$15,001 - $50,000', etc.
    """
    if not amount_str or amount_str == '--':
        return 0

    amount_str = str(amount_str).replace(',', '').replace('$', '').strip()

    # Handle range format
    if '-' in amount_str:
        parts = amount_str.split('-')
        try:
            low = float(parts[0].strip())
            high = float(parts[1].strip())
            return (low + high) / 2  # Midpoint estimate
        except (ValueError, IndexError):
            pass

    # Handle single number
    try:
        return float(amount_str)
    except ValueError:
        return 0


def is_recent(date_str, days=60):
    """Check if a date string is within the last N days."""
    if not date_str:
        return False
    try:
        # Handle multiple date formats
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%dT%H:%M:%S'):
            try:
                dt = datetime.strptime(date_str[:19], fmt)
                return dt > datetime.utcnow() - timedelta(days=days)
            except ValueError:
                continue
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze_transactions(transactions, days_back=60, min_amount=15000):
    """
    Analyze congressional transactions to find actionable signals.

    Returns: {
        'cluster_buys': {ticker: count},  — tickers bought by 3+ members
        'recent_buys': [{ticker, member, amount, date}],
        'recent_sells': [{ticker, member, amount, date}],
        'buy_sell_ratio': {ticker: ratio},
        'top_buyers': [(member, count)],
    }
    """
    recent_buys = []
    recent_sells = []

    for tx in transactions:
        # Filter: recent, significant amount
        tx_date = tx.get('transaction_date', tx.get('date', ''))
        if not is_recent(tx_date, days=days_back):
            continue

        amount = parse_amount(tx.get('amount', '0'))
        if amount < min_amount:
            continue

        ticker = tx.get('ticker', '').upper().strip()
        if not ticker or len(ticker) > 6 or ticker == '--':
            continue

        tx_type = str(tx.get('type', tx.get('transaction_type', ''))).lower()
        member = tx.get('representative', tx.get('senator', tx.get('member', 'Unknown')))

        entry = {
            'ticker': ticker,
            'member': member,
            'amount_est': round(amount),
            'date': tx_date,
            'type': tx_type,
            'disclosure_date': tx.get('disclosure_date', ''),
        }

        if 'purchase' in tx_type or 'buy' in tx_type:
            recent_buys.append(entry)
        elif 'sale' in tx_type or 'sell' in tx_type:
            recent_sells.append(entry)

    # Cluster analysis: tickers bought by multiple members
    buy_counts = Counter(b['ticker'] for b in recent_buys)
    sell_counts = Counter(s['ticker'] for s in recent_sells)

    cluster_buys = {ticker: count for ticker, count in buy_counts.items() if count >= 3}

    # Buy/sell ratio per ticker
    all_tickers = set(list(buy_counts.keys()) + list(sell_counts.keys()))
    buy_sell_ratio = {}
    for ticker in all_tickers:
        buys = buy_counts.get(ticker, 0)
        sells = sell_counts.get(ticker, 0)
        ratio = buys / max(sells, 1)
        if buys > 0:
            buy_sell_ratio[ticker] = round(ratio, 2)

    # Top buyers (most active members)
    member_counts = Counter(b['member'] for b in recent_buys)
    top_buyers = member_counts.most_common(10)

    # Filter to our tracked tickers
    tracked_buys = [b for b in recent_buys if b['ticker'] in ALL_TICKERS]
    tracked_sells = [s for s in recent_sells if s['ticker'] in ALL_TICKERS]

    return {
        'cluster_buys': cluster_buys,
        'recent_buys': recent_buys[:50],  # Cap for API payload
        'recent_sells': recent_sells[:50],
        'tracked_buys': tracked_buys,
        'tracked_sells': tracked_sells,
        'buy_sell_ratio': dict(sorted(buy_sell_ratio.items(),
                                       key=lambda x: x[1], reverse=True)[:20]),
        'top_buyers': [{'member': m, 'trades': c} for m, c in top_buyers],
        'total_buys': len(recent_buys),
        'total_sells': len(recent_sells),
    }


# ---------------------------------------------------------------------------
# Signal Generation
# ---------------------------------------------------------------------------

def generate_signals(analysis):
    """
    Generate trading signals from congressional trading patterns.

    Signal types:
    1. CLUSTER_BUY: 3+ members buying same stock → strong bullish
    2. TRACKED_BUY: Congress member buying a stock we track → moderate bullish
    3. HEAVY_SELLING: Buy/sell ratio < 0.5 → bearish warning
    """
    signals = []

    # Cluster buys (strongest signal)
    for ticker, count in analysis['cluster_buys'].items():
        signals.append({
            'ticker': ticker,
            'signal_type': 'CONGRESS_CLUSTER_BUY',
            'strength': min(90, 50 + count * 10),  # 3 members = 80, 4 = 90
            'members_buying': count,
            'description': f"{count} Congress members bought {ticker} recently",
            'edge_estimate': '6-12% annual outperformance (academic studies)',
        })

    # Individual tracked ticker buys
    seen_tickers = set()
    for buy in analysis['tracked_buys']:
        ticker = buy['ticker']
        if ticker in seen_tickers:
            continue
        seen_tickers.add(ticker)

        # Check if it's also a cluster
        if ticker in analysis['cluster_buys']:
            continue  # Already covered above

        signals.append({
            'ticker': ticker,
            'signal_type': 'CONGRESS_BUY',
            'strength': 55,
            'member': buy['member'],
            'amount_est': buy['amount_est'],
            'description': f"{buy['member']} bought {ticker} (~${buy['amount_est']:,})",
        })

    # Heavy selling warnings
    for ticker, ratio in analysis['buy_sell_ratio'].items():
        if ratio < 0.3 and ticker in ALL_TICKERS:
            signals.append({
                'ticker': ticker,
                'signal_type': 'CONGRESS_HEAVY_SELLING',
                'strength': 30,
                'buy_sell_ratio': ratio,
                'description': f"Congress heavily selling {ticker} (buy/sell ratio: {ratio})",
            })

    return signals


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def main():
    """Run congressional trading analysis."""
    logger.info("=" * 60)
    logger.info("CONGRESSIONAL TRADING TRACKER — Starting")
    logger.info("=" * 60)

    # Fetch from both chambers
    house_tx = fetch_transactions(HOUSE_DATA_URL, "House")
    senate_tx = fetch_transactions(SENATE_DATA_URL, "Senate")

    all_transactions = house_tx + senate_tx
    logger.info("Total transactions fetched: %d (House: %d, Senate: %d)",
                 len(all_transactions), len(house_tx), len(senate_tx))

    if not all_transactions:
        logger.warning("No transaction data available")
        return []

    # Analyze
    analysis = analyze_transactions(all_transactions, days_back=60, min_amount=15000)

    logger.info("")
    logger.info("ANALYSIS RESULTS (last 60 days, >$15K):")
    logger.info("  Total buys:  %d", analysis['total_buys'])
    logger.info("  Total sells: %d", analysis['total_sells'])

    # Log cluster buys
    if analysis['cluster_buys']:
        logger.info("")
        logger.info("  CLUSTER BUYS (3+ members buying same stock):")
        for ticker, count in sorted(analysis['cluster_buys'].items(),
                                     key=lambda x: x[1], reverse=True):
            in_our_list = " *** IN OUR WATCHLIST ***" if ticker in ALL_TICKERS else ""
            logger.info("    %s: %d members%s", ticker, count, in_our_list)

    # Log tracked ticker activity
    if analysis['tracked_buys']:
        logger.info("")
        logger.info("  OUR TRACKED TICKERS — Congress Activity:")
        for buy in analysis['tracked_buys'][:10]:
            logger.info("    BUY  %s by %s (~$%s) on %s",
                         buy['ticker'], buy['member'],
                         f"{buy['amount_est']:,}", buy['date'])

    if analysis['tracked_sells']:
        for sell in analysis['tracked_sells'][:10]:
            logger.info("    SELL %s by %s (~$%s) on %s",
                         sell['ticker'], sell['member'],
                         f"{sell['amount_est']:,}", sell['date'])

    # Log top buyers
    if analysis['top_buyers']:
        logger.info("")
        logger.info("  MOST ACTIVE BUYERS:")
        for buyer in analysis['top_buyers'][:5]:
            logger.info("    %s: %d trades", buyer['member'], buyer['trades'])

    # Generate signals
    signals = generate_signals(analysis)

    # Post to API
    if signals or analysis['total_buys'] > 0:
        api_result = post_to_api('ingest_regime', {
            'source': 'congress_tracker',
            'signals': signals,
            'analysis_summary': {
                'total_buys': analysis['total_buys'],
                'total_sells': analysis['total_sells'],
                'cluster_buys': analysis['cluster_buys'],
                'top_buy_sell_ratios': dict(list(analysis['buy_sell_ratio'].items())[:10]),
                'tracked_ticker_buys': len(analysis['tracked_buys']),
                'tracked_ticker_sells': len(analysis['tracked_sells']),
            },
            'computed_at': datetime.utcnow().isoformat(),
            'data_sources': ['house_stock_watcher', 'senate_stock_watcher'],
        })

        if api_result.get('ok'):
            logger.info("Congressional data posted to API")
        else:
            logger.warning("API post error: %s", api_result.get('error', 'unknown'))

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("CONGRESSIONAL TRACKER SUMMARY")
    logger.info("  Signals generated: %d", len(signals))
    for sig in signals:
        logger.info("    [%s] %s (strength=%d) — %s",
                     sig['signal_type'], sig['ticker'],
                     sig['strength'], sig['description'])
    logger.info("=" * 60)

    return signals


if __name__ == '__main__':
    main()
