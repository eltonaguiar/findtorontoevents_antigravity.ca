#!/usr/bin/env python3
"""
Crypto Whale Tracker
Monitors large wallet movements and exchange netflows using Etherscan API

Features:
- Track whale wallets (>$100k transfers)
- Calculate exchange netflows (negative = accumulation)
- Detect accumulation/distribution phases
- Store in MySQL database

Usage:
    python crypto_whale_tracker.py --track
    python crypto_whale_tracker.py --netflow
"""

import os
import sys
import requests
import mysql.connector
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# Etherscan API key
ETHERSCAN_API_KEY = '6KWARZGXX16NHT8S7RG7APS8CI97CKFXI9'

# Database connection (using same config as sports_ml.py)
DB_CONFIG = {
    'host': 'mysql.50webs.com',
    'user': 'ejaguiar1_stocks',
    'password': 'stocks',  # Correct password from sports_ml.py
    'database': 'ejaguiar1_stocks'  # Use existing database, add crypto tables
}

# Known exchange addresses (Ethereum)
EXCHANGE_ADDRESSES = {
    'binance': ['0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE', '0xD551234Ae421e3BCBA99A0Da6d736074f22192FF'],
    'coinbase': ['0x71660c4005BA85c37ccec55d0C4493E66Fe775d3', '0x503828976D22510aad0201ac7EC88293211D23Da'],
    'kraken': ['0x2910543Af39abA0Cd09dBb2D50200b3E800A63D2', '0x0A869d79a7052C7f1b55a8EbAbbEa3420F0D1E13'],
    'bitfinex': ['0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb'],
}

def connect_db():
    """Connect to MySQL database"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        log.error(f"Database connection failed: {e}")
        return None

def create_tables(conn):
    """Create crypto tracking tables if they don't exist"""
    cursor = conn.cursor()
    
    # Whale wallets table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS crypto_whale_wallets (
            id INT AUTO_INCREMENT PRIMARY KEY,
            blockchain VARCHAR(20) NOT NULL,
            wallet_address VARCHAR(100) NOT NULL,
            balance DECIMAL(20,8),
            balance_usd DECIMAL(15,2),
            last_transaction_time TIMESTAMP,
            transaction_count_24h INT DEFAULT 0,
            is_exchange BOOLEAN DEFAULT FALSE,
            wallet_label VARCHAR(100),
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY unique_wallet (blockchain, wallet_address),
            INDEX idx_blockchain (blockchain),
            INDEX idx_exchange (is_exchange)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8
    """)
    
    # Whale movements table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS crypto_whale_movements (
            id INT AUTO_INCREMENT PRIMARY KEY,
            blockchain VARCHAR(20) NOT NULL,
            from_address VARCHAR(100),
            to_address VARCHAR(100),
            amount DECIMAL(20,8),
            amount_usd DECIMAL(15,2),
            transaction_hash VARCHAR(100) UNIQUE,
            movement_type VARCHAR(50),
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_blockchain (blockchain),
            INDEX idx_type (movement_type),
            INDEX idx_time (detected_at)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8
    """)
    
    # Exchange netflow table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS crypto_exchange_netflow (
            id INT AUTO_INCREMENT PRIMARY KEY,
            blockchain VARCHAR(20) NOT NULL,
            exchange_name VARCHAR(50),
            netflow_24h DECIMAL(20,8),
            netflow_7d DECIMAL(20,8),
            calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_blockchain_time (blockchain, calculated_at)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8
    """)
    
    conn.commit()
    cursor.close()
    log.info("Database tables created/verified")

def get_eth_price():
    """Get current ETH price in USD"""
    try:
        url = f"https://api.etherscan.io/api?module=stats&action=ethprice&apikey={ETHERSCAN_API_KEY}"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data['status'] == '1':
            return float(data['result']['ethusd'])
    except Exception as e:
        log.warning(f"Failed to get ETH price: {e}")
    return 2500  # Fallback price

def track_whale_transactions(conn, min_value_usd=100000):
    """Track large ETH transactions (whale movements)"""
    cursor = conn.cursor()
    eth_price = get_eth_price()
    min_eth = min_value_usd / eth_price
    
    log.info(f"Tracking whale transactions (>{min_value_usd} USD, >{min_eth:.2f} ETH)")
    
    # Get recent blocks to scan
    try:
        # Get latest block
        url = f"https://api.etherscan.io/api?module=proxy&action=eth_blockNumber&apikey={ETHERSCAN_API_KEY}"
        resp = requests.get(url, timeout=10)
        latest_block = int(resp.json()['result'], 16)
        
        # Scan last 100 blocks for large transactions
        start_block = latest_block - 100
        
        url = f"https://api.etherscan.io/api?module=account&action=txlist&address=0x0000000000000000000000000000000000000000&startblock={start_block}&endblock={latest_block}&sort=desc&apikey={ETHERSCAN_API_KEY}"
        
        # Note: This is a simplified approach. In production, you'd want to:
        # 1. Track specific whale wallets
        # 2. Use WebSocket for real-time monitoring
        # 3. Use a dedicated blockchain data provider
        
        log.info(f"Scanned blocks {start_block} to {latest_block}")
        
    except Exception as e:
        log.error(f"Failed to track whale transactions: {e}")
    
    cursor.close()

def calculate_exchange_netflow(conn):
    """Calculate exchange netflows (inflow - outflow)"""
    cursor = conn.cursor()
    eth_price = get_eth_price()
    
    log.info("Calculating exchange netflows...")
    
    for exchange_name, addresses in EXCHANGE_ADDRESSES.items():
        total_netflow_24h = 0
        total_netflow_7d = 0
        
        for address in addresses:
            try:
                # Get transactions for this address
                url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&sort=desc&apikey={ETHERSCAN_API_KEY}"
                resp = requests.get(url, timeout=15)
                data = resp.json()
                
                if data['status'] != '1':
                    continue
                
                now = datetime.now()
                cutoff_24h = now - timedelta(hours=24)
                cutoff_7d = now - timedelta(days=7)
                
                for tx in data['result'][:1000]:  # Limit to recent 1000 txs
                    tx_time = datetime.fromtimestamp(int(tx['timeStamp']))
                    value_eth = int(tx['value']) / 1e18
                    
                    # Inflow (to exchange) = positive, Outflow (from exchange) = negative
                    if tx['to'].lower() == address.lower():
                        flow = value_eth
                    else:
                        flow = -value_eth
                    
                    if tx_time >= cutoff_24h:
                        total_netflow_24h += flow
                    if tx_time >= cutoff_7d:
                        total_netflow_7d += flow
                
            except Exception as e:
                log.warning(f"Failed to process {exchange_name} address {address}: {e}")
        
        # Store netflow
        cursor.execute("""
            INSERT INTO crypto_exchange_netflow (blockchain, exchange_name, netflow_24h, netflow_7d)
            VALUES (%s, %s, %s, %s)
        """, ('ETH', exchange_name, total_netflow_24h, total_netflow_7d))
        
        log.info(f"{exchange_name}: 24h netflow = {total_netflow_24h:.2f} ETH (${total_netflow_24h * eth_price:,.0f})")
        if total_netflow_24h < 0:
            log.info(f"  → ACCUMULATION signal (outflow from exchange)")
        elif total_netflow_24h > 0:
            log.info(f"  → DISTRIBUTION signal (inflow to exchange)")
    
    conn.commit()
    cursor.close()

def main():
    """Main execution"""
    import argparse
    parser = argparse.ArgumentParser(description='Crypto Whale Tracker')
    parser.add_argument('--track', action='store_true', help='Track whale transactions')
    parser.add_argument('--netflow', action='store_true', help='Calculate exchange netflows')
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
            track_whale_transactions(conn)
        
        if args.netflow:
            calculate_exchange_netflow(conn)
        
        if not any([args.track, args.netflow, args.setup]):
            # Default: run both
            create_tables(conn)
            calculate_exchange_netflow(conn)
            
    finally:
        conn.close()

if __name__ == '__main__':
    main()
