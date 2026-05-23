# onchain_analytics.py - On-chain analytics for crypto
# Requirements: pip install requests pandas mysql-connector-python web3

import os
import requests
import pandas as pd
import mysql.connector
from web3 import Web3

# DB config
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

# ETH node (use free Infura/Alchemy key from env)
INFURA_URL = os.getenv('INFURA_URL')

def connect_db():
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
    )

w3 = Web3(Web3.HTTPProvider(INFURA_URL))

def fetch_onchain_metrics(contract_address):
    # Example: whale transactions (large transfers)
    try:
        latest_block = w3.eth.block_number
        transfers = []  # Fetch via Etherscan API for simplicity
        url = f'https://api.etherscan.io/api?module=account&action=tokentx&contractaddress={contract_address}&sort=desc&apikey={os.getenv("ETHERSCAN_KEY")}'
        resp = requests.get(url)
        data = resp.json()
        if data['status'] == '1':
            for tx in data['result'][:50]:
                if int(tx['value']) > 1e18:  # Large tx
                    transfers.append(tx)
        whale_count = len(transfers)
        return {'whale_count': whale_count}
    except:
        return {'whale_count': 0}

def store_onchain(coin, metrics):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO onchain_metrics (coin, whale_count, fetch_date)
    VALUES (%s, %s, NOW())
    """, (coin, metrics['whale_count']))
    conn.commit()
    conn.close()

def run_onchain():
    coins = [('ETH', '0x...')]  # Add contract addresses
    for coin, addr in coins:
        metrics = fetch_onchain_metrics(addr)
        store_onchain(coin, metrics)
        print(f"{coin}: {metrics}")

if __name__ == '__main__':
    run_onchain()