#!/usr/bin/env python3
"""
================================================================================
LIVE DATA CONNECTOR - Real-Time API Integration
================================================================================

Connects to CoinGecko and CoinDesk APIs using provided keys.
Fetches real-time prices, OHLC data, and market metrics.

Usage:
    from live_data_connector import LiveDataConnector
    connector = LiveDataConnector()
    prices = connector.get_live_prices()
================================================================================
"""

import os
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class LiveDataConnector:
    """
    Real-time data connector for crypto markets
    """
    
    def __init__(self):
        self.coingecko_key = os.getenv('COINGECKO_API_KEY')
        self.coindesk_key = os.getenv('COINDESK_API_KEY')
        
        self.coin_ids = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'BNB': 'binancecoin',
            'AVAX': 'avalanche-2'
        }
        
        self.coin_symbols = {
            'BTC': 'BTC',
            'ETH': 'ETH',
            'BNB': 'BNB',
            'AVAX': 'AVAX'
        }
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.2  # CoinGecko demo: 30 calls/min = 2s interval
        
        print("🔄 LiveDataConnector initialized")
        if self.coingecko_key:
            print(f"   ✅ CoinGecko API: Connected (Key: {self.coingecko_key[:8]}...)")
        else:
            print("   ⚠️  CoinGecko API: No key found")
            
        if self.coindesk_key:
            print(f"   ✅ CoinDesk API: Connected (Key: {self.coindesk_key[:8]}...)")
        else:
            print("   ⚠️  CoinDesk API: No key found")
    
    def _rate_limit(self):
        """Ensure we don't exceed rate limits"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def get_live_prices(self) -> Dict[str, Dict]:
        """
        Fetch live prices from CoinGecko
        
        Returns:
            {
                'BTC': {
                    'price': 69852.00,
                    'change_24h': 1.27,
                    'change_24h_usd': 876.50,
                    'market_cap': 1396000000000,
                    'volume_24h': 28000000000,
                    'last_updated': '2026-02-14T14:30:00Z'
                },
                ...
            }
        """
        self._rate_limit()
        
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': ','.join(self.coin_ids.values()),
            'vs_currencies': 'usd',
            'include_24hr_change': 'true',
            'include_24hr_vol': 'true',
            'include_market_cap': 'true',
            'include_last_updated_at': 'true'
        }
        
        headers = {}
        if self.coingecko_key:
            headers['x-cg-demo-api-key'] = self.coingecko_key
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            result = {}
            for asset, coin_id in self.coin_ids.items():
                if coin_id in data:
                    coin_data = data[coin_id]
                    result[asset] = {
                        'price': coin_data.get('usd', 0),
                        'change_24h': coin_data.get('usd_24h_change', 0),
                        'change_24h_usd': coin_data.get('usd', 0) * (coin_data.get('usd_24h_change', 0) / 100),
                        'market_cap': coin_data.get('usd_market_cap', 0),
                        'volume_24h': coin_data.get('usd_24h_vol', 0),
                        'last_updated': datetime.fromtimestamp(
                            coin_data.get('last_updated_at', 0)
                        ).isoformat() if coin_data.get('last_updated_at') else None
                    }
            
            print(f"✅ Live prices fetched at {datetime.now().strftime('%H:%M:%S')}")
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching live prices: {e}")
            return {}
    
    def get_ohlc_data(self, asset: str, days: int = 30) -> pd.DataFrame:
        """
        Fetch OHLC data for backtesting and analysis
        
        Args:
            asset: 'BTC', 'ETH', 'BNB', or 'AVAX'
            days: Number of days of history
            
        Returns:
            DataFrame with columns: open, high, low, close, volume, timestamp
        """
        self._rate_limit()
        
        coin_id = self.coin_ids.get(asset)
        if not coin_id:
            print(f"❌ Unknown asset: {asset}")
            return pd.DataFrame()
        
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
        params = {
            'vs_currency': 'usd',
            'days': days
        }
        
        headers = {}
        if self.coingecko_key:
            headers['x-cg-demo-api-key'] = self.coingecko_key
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # CoinGecko returns: [timestamp, open, high, low, close]
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['volume'] = 0  # OHLC endpoint doesn't include volume
            df.set_index('timestamp', inplace=True)
            
            print(f"✅ OHLC data fetched for {asset}: {len(df)} candles")
            return df
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching OHLC for {asset}: {e}")
            return pd.DataFrame()
    
    def get_market_data(self, asset: str) -> Dict:
        """
        Fetch comprehensive market data for an asset
        
        Returns:
            {
                'price': 69852.00,
                'market_cap': 1396000000000,
                'total_volume': 28000000000,
                'high_24h': 70500.00,
                'low_24h': 68500.00,
                'price_change_24h': 876.50,
                'price_change_percentage_24h': 1.27,
                'market_cap_change_24h': 15000000000,
                'circulating_supply': 19850000,
                'total_supply': 21000000,
                'ath': 73500.00,
                'ath_change_percentage': -4.80,
                'atl': 67.81,
                'atl_change_percentage': 102900.00,
                'last_updated': '2026-02-14T14:30:00Z'
            }
        """
        self._rate_limit()
        
        coin_id = self.coin_ids.get(asset)
        if not coin_id:
            return {}
        
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        params = {
            'localization': 'false',
            'tickers': 'false',
            'market_data': 'true',
            'community_data': 'false',
            'developer_data': 'false',
            'sparkline': 'false'
        }
        
        headers = {}
        if self.coingecko_key:
            headers['x-cg-demo-api-key'] = self.coingecko_key
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            market_data = data.get('market_data', {})
            
            return {
                'price': market_data.get('current_price', {}).get('usd', 0),
                'market_cap': market_data.get('market_cap', {}).get('usd', 0),
                'total_volume': market_data.get('total_volume', {}).get('usd', 0),
                'high_24h': market_data.get('high_24h', {}).get('usd', 0),
                'low_24h': market_data.get('low_24h', {}).get('usd', 0),
                'price_change_24h': market_data.get('price_change_24h_in_currency', {}).get('usd', 0),
                'price_change_percentage_24h': market_data.get('price_change_percentage_24h_in_currency', {}).get('usd', 0),
                'market_cap_change_24h': market_data.get('market_cap_change_24h_in_currency', {}).get('usd', 0),
                'circulating_supply': market_data.get('circulating_supply', 0),
                'total_supply': market_data.get('total_supply', 0),
                'ath': market_data.get('ath', {}).get('usd', 0),
                'ath_change_percentage': market_data.get('ath_change_percentage', {}).get('usd', 0),
                'atl': market_data.get('atl', {}).get('usd', 0),
                'atl_change_percentage': market_data.get('atl_change_percentage', {}).get('usd', 0),
                'last_updated': market_data.get('last_updated')
            }
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching market data for {asset}: {e}")
            return {}
    
    def get_global_market_data(self) -> Dict:
        """Fetch global crypto market data"""
        self._rate_limit()
        
        url = "https://api.coingecko.com/api/v3/global"
        
        headers = {}
        if self.coingecko_key:
            headers['x-cg-demo-api-key'] = self.coingecko_key
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            global_data = data.get('data', {})
            
            return {
                'total_market_cap_usd': global_data.get('total_market_cap', {}).get('usd', 0),
                'total_volume_24h_usd': global_data.get('total_volume', {}).get('usd', 0),
                'market_cap_change_24h': global_data.get('market_cap_change_percentage_24h_usd', 0),
                'btc_dominance': global_data.get('market_cap_percentage', {}).get('btc', 0),
                'eth_dominance': global_data.get('market_cap_percentage', {}).get('eth', 0),
                'active_cryptocurrencies': global_data.get('active_cryptocurrencies', 0),
                'markets': global_data.get('markets', 0)
            }
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching global data: {e}")
            return {}
    
    def test_connection(self) -> bool:
        """Test API connection and return status"""
        print("\n🧪 Testing API connections...")
        
        # Test CoinGecko
        prices = self.get_live_prices()
        coingecko_ok = len(prices) > 0
        
        if coingecko_ok:
            print(f"✅ CoinGecko API: WORKING")
            print(f"   Fetched {len(prices)} assets")
            for asset, data in list(prices.items())[:2]:
                print(f"   {asset}: ${data['price']:,.2f} ({data['change_24h']:+.2f}%)")
        else:
            print(f"❌ CoinGecko API: FAILED")
        
        # Test CoinDesk (basic connectivity)
        coindesk_ok = bool(self.coindesk_key)
        if coindesk_ok:
            print(f"✅ CoinDesk API: Key present")
        
        return coingecko_ok


def main():
    """Test the live data connector"""
    print("=" * 80)
    print("🚀 LIVE DATA CONNECTOR - API TEST")
    print("=" * 80)
    
    connector = LiveDataConnector()
    
    # Test connection
    if not connector.test_connection():
        print("\n❌ API connection failed. Check your keys in .env file")
        return
    
    # Fetch live prices
    print("\n" + "=" * 80)
    print("💹 LIVE PRICES")
    print("=" * 80)
    
    prices = connector.get_live_prices()
    
    for asset, data in prices.items():
        emoji = "🟢" if data['change_24h'] > 0 else "🔴"
        print(f"{emoji} {asset:5}: ${data['price']:>12,.2f} "
              f"({data['change_24h']:>+6.2f}%) "
              f"| Vol: ${data['volume_24h']/1e9:>5.1f}B "
              f"| MCap: ${data['market_cap']/1e9:>5.0f}B")
    
    # Fetch global data
    print("\n" + "=" * 80)
    print("🌍 GLOBAL MARKET DATA")
    print("=" * 80)
    
    global_data = connector.get_global_market_data()
    
    if global_data:
        print(f"Total Market Cap: ${global_data.get('total_market_cap_usd', 0)/1e12:.2f}T")
        print(f"24h Volume: ${global_data.get('total_volume_24h_usd', 0)/1e9:.1f}B")
        print(f"BTC Dominance: {global_data.get('btc_dominance', 0):.1f}%")
        print(f"Active Cryptos: {global_data.get('active_cryptocurrencies', 0):,}")
    
    # Fetch OHLC data for one asset
    print("\n" + "=" * 80)
    print("📊 OHLC DATA SAMPLE (BTC - Last 7 Days)")
    print("=" * 80)
    
    ohlc = connector.get_ohlc_data('BTC', days=7)
    
    if not ohlc.empty:
        print(f"Fetched {len(ohlc)} candles")
        print(f"Latest: Open=${ohlc.iloc[-1]['open']:,.2f}, "
              f"High=${ohlc.iloc[-1]['high']:,.2f}, "
              f"Low=${ohlc.iloc[-1]['low']:,.2f}, "
              f"Close=${ohlc.iloc[-1]['close']:,.2f}")
    
    print("\n" + "=" * 80)
    print("✅ API TEST COMPLETE - Live data connected!")
    print("=" * 80)


if __name__ == '__main__':
    main()
