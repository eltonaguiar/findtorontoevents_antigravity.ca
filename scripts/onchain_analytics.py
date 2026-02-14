#!/usr/bin/env python3
"""
On-chain analytics for crypto — whale transaction detection and metrics.

Features:
  - Percentile-based whale threshold (top N% of transactions by value)
  - Configurable max transactions to sample
  - Proper exception handling with logging
  - Rate limiting for API requests
  - Stores results to MySQL for dashboard consumption

Requirements: pip install requests pandas mysql-connector-python web3

Usage:
  python onchain_analytics.py                          # Run with defaults
  python onchain_analytics.py --whale-pct 95           # Top 5% are whales
  python onchain_analytics.py --max-tx 200             # Sample more transactions
"""
import os
import sys
import time
import logging
import argparse
import requests
import mysql.connector
from utils import post_to_api, post_to_bridge

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('onchain_analytics')

# --- DB config ---
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

# --- API config ---
ETHERSCAN_KEY = os.getenv('ETHERSCAN_KEY', '')
INFURA_URL = os.getenv('INFURA_URL', '')

# --- Defaults ---
DEFAULT_WHALE_PERCENTILE = 95   # Top 5% of transactions by value = whale
DEFAULT_MAX_TX = 100            # Sample up to 100 transactions
API_RATE_LIMIT_SECONDS = 0.25   # 250ms between API calls (Etherscan free tier: 5/sec)

# Tracked coins/tokens — add contract addresses as needed
DEFAULT_COINS = [
    # (name, contract_address or 'native' for ETH itself)
    ('ETH', 'native'),
]


def connect_db():
    """Connect to MySQL with proper error handling."""
    try:
        conn = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
        )
        return conn
    except mysql.connector.Error as err:
        logger.error("Database connection failed: %s", err)
        return None


def fetch_onchain_metrics(contract_address, max_tx=DEFAULT_MAX_TX,
                          whale_percentile=DEFAULT_WHALE_PERCENTILE):
    """
    Fetch on-chain transfer metrics from Etherscan API.

    Uses percentile-based whale detection instead of fixed threshold:
      - Fetch up to max_tx recent transfers
      - Compute the Nth percentile of transfer values
      - Count transactions above that percentile as "whale" transactions

    Returns dict with whale_count, total_sampled, whale_threshold_wei, etc.
    """
    if not ETHERSCAN_KEY:
        logger.warning("ETHERSCAN_KEY not set — skipping on-chain fetch")
        return {'whale_count': 0, 'total_sampled': 0, 'error': 'no_api_key'}

    try:
        # Determine API endpoint based on contract type
        if contract_address == 'native':
            # For native ETH, use internal transactions for the latest block
            # Etherscan doesn't have a simple "recent ETH transfers" endpoint,
            # so we use token transfers for a major token as a proxy
            logger.info("Native ETH — using recent block transactions")
            url = (
                f'https://api.etherscan.io/api?module=proxy&action=eth_blockNumber'
                f'&apikey={ETHERSCAN_KEY}'
            )
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            # Just return basic block info for native ETH
            data = resp.json()
            block_hex = data.get('result', '0x0')
            block_num = int(block_hex, 16) if block_hex.startswith('0x') else 0
            return {
                'whale_count': 0,
                'total_sampled': 0,
                'latest_block': block_num,
                'note': 'Native ETH — block number only (use token address for whale detection)',
            }
        else:
            url = (
                f'https://api.etherscan.io/api?module=account&action=tokentx'
                f'&contractaddress={contract_address}&sort=desc'
                f'&apikey={ETHERSCAN_KEY}'
            )

        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get('status') != '1' or not data.get('result'):
            msg = data.get('message', 'Unknown API error')
            logger.warning("Etherscan API returned non-success: %s", msg)
            return {'whale_count': 0, 'total_sampled': 0, 'error': msg}

        # Sample up to max_tx transactions
        transactions = data['result'][:max_tx]
        total_sampled = len(transactions)

        if total_sampled == 0:
            return {'whale_count': 0, 'total_sampled': 0}

        # Extract values (in wei)
        values = []
        for tx in transactions:
            try:
                val = int(tx.get('value', 0))
                values.append(val)
            except (ValueError, TypeError):
                continue

        if not values:
            return {'whale_count': 0, 'total_sampled': total_sampled}

        # --- Percentile-based whale threshold ---
        values_sorted = sorted(values)
        pct_idx = int(len(values_sorted) * whale_percentile / 100.0)
        pct_idx = min(pct_idx, len(values_sorted) - 1)
        whale_threshold = values_sorted[pct_idx]

        # Count whales (transactions above the percentile threshold)
        whale_txs = [v for v in values if v >= whale_threshold and v > 0]
        whale_count = len(whale_txs)

        # Summary stats
        avg_value = sum(values) / len(values) if values else 0
        max_value = max(values) if values else 0

        logger.info(
            "Fetched %d txs, whale threshold (p%d) = %s wei, whales = %d",
            total_sampled, whale_percentile, whale_threshold, whale_count
        )

        return {
            'whale_count': whale_count,
            'total_sampled': total_sampled,
            'whale_percentile': whale_percentile,
            'whale_threshold_wei': whale_threshold,
            'whale_threshold_eth': round(whale_threshold / 1e18, 4),
            'avg_value_wei': int(avg_value),
            'max_value_wei': max_value,
            'max_value_eth': round(max_value / 1e18, 4),
        }

    except requests.exceptions.Timeout:
        logger.error("Etherscan API timed out for %s", contract_address)
        return {'whale_count': 0, 'total_sampled': 0, 'error': 'timeout'}

    except requests.exceptions.RequestException as err:
        logger.error("Etherscan API request failed: %s", err)
        return {'whale_count': 0, 'total_sampled': 0, 'error': str(err)}

    except (KeyError, ValueError) as err:
        logger.error("Error parsing Etherscan response: %s", err)
        return {'whale_count': 0, 'total_sampled': 0, 'error': str(err)}


def store_onchain(coin, metrics):
    """Store on-chain metrics to MySQL."""
    conn = connect_db()
    if conn is None:
        logger.error("Cannot store metrics — DB connection failed")
        return False

    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO onchain_metrics (coin, whale_count, fetch_date)
            VALUES (%s, %s, NOW())
        """, (coin, metrics.get('whale_count', 0)))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Stored metrics for %s: whale_count=%d", coin, metrics.get('whale_count', 0))
        return True
    except mysql.connector.Error as err:
        logger.error("Failed to store metrics for %s: %s", coin, err)
        try:
            conn.close()
        except Exception:
            pass
        return False


def run_onchain(coins=None, max_tx=DEFAULT_MAX_TX, whale_percentile=DEFAULT_WHALE_PERCENTILE):
    """Run on-chain analytics for all configured coins."""
    if coins is None:
        coins = DEFAULT_COINS

    logger.info("=== On-Chain Analytics ===")
    logger.info("Coins: %d | Max TX: %d | Whale percentile: %d%%",
                len(coins), max_tx, whale_percentile)

    for i, (coin, addr) in enumerate(coins):
        logger.info("Processing %s (%s)...", coin, addr[:10] + '...' if len(addr) > 10 else addr)

        metrics = fetch_onchain_metrics(addr, max_tx, whale_percentile)

        if 'error' not in metrics:
            store_onchain(coin, metrics)
        else:
            logger.warning("Skipping DB store for %s due to error: %s", coin, metrics['error'])

        payload = {
            'coin': coin,
            'whale_count': metrics.get('whale_count', 0),
            'total_sampled': metrics.get('total_sampled', 0),
            'whale_threshold_wei': metrics.get('whale_threshold_wei', 0),
            'whale_threshold_eth': metrics.get('whale_threshold_eth', 0),
            'avg_value_wei': metrics.get('avg_value_wei', 0),
            'max_value_wei': metrics.get('max_value_wei', 0),
            'max_value_eth': metrics.get('max_value_eth', 0),
        }

        api_result = post_to_api('ingest_regime', payload)
        if api_result.get('ok'):
            logger.info("On-chain data posted to API")
        else:
            logger.warning("API post error: %s", api_result.get('error', 'unknown'))

        post_to_bridge('onchain_analytics', payload,
                       "BTC=$%s, TVL 7d=%+.1f%%" % (
                           "{:,.0f}".format(0),
                           0))

        print(f"{coin}: {metrics}")

        # Rate limiting between API calls
        if i < len(coins) - 1:
            time.sleep(API_RATE_LIMIT_SECONDS)

    logger.info("Done.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='On-Chain Analytics')
    parser.add_argument('--whale-pct', type=int, default=DEFAULT_WHALE_PERCENTILE,
                        help=f'Whale percentile threshold (default {DEFAULT_WHALE_PERCENTILE})')
    parser.add_argument('--max-tx', type=int, default=DEFAULT_MAX_TX,
                        help=f'Max transactions to sample (default {DEFAULT_MAX_TX})')
    args = parser.parse_args()

    run_onchain(whale_percentile=args.whale_pct, max_tx=args.max_tx)
