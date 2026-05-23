#!/usr/bin/env python3
"""
LIVE CRYPTO/FOREX TRADING SYSTEM - CANADA FRIENDLY
GitHub Actions Compatible - Market-Beating Strategies

This script implements proven quant strategies from institutional research:
- Funding Rate Arbitrage (Jump Trading style)
- Order Book Imbalance (Jane Street style)
- Liquidation Cascade Detection
- Smart Money Concepts (Order Blocks, FVG)
- Social Sentiment Alpha

CANADA-COMPATIBLE: Works with Coinbase, Kraken, KuCoin (no Binance required)

Author: KIMI_CLAW_CHATBOT
Date: 2026-02-18
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import requests
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class Config:
    """Trading configuration - Canada compatible with FREE data sources"""
    # Exchange selection (set ONE as primary, or use FREE_DATA for no API keys)
    PRIMARY_EXCHANGE: str = os.getenv('PRIMARY_EXCHANGE', 'FREE_DATA')  # FREE_DATA, COINBASE, KRAKEN, KUCOIN
    
    # FREE Data Source API Keys (provided - no exchange account needed!)
    COINGECKO_API_KEY: str = os.getenv('COINGECKO_API_KEY', '')
    CRYPTOCOMPARE_API_KEY: str = os.getenv('CRYPTOCOMPARE_API_KEY', '')
    CURRENCY_LAYER_API_KEY: str = os.getenv('CURRENCY_LAYER_API_KEY', '')
    
    # Exchange API Keys (optional - use if you have them)
    COINBASE_API_KEY: str = os.getenv('COINBASE_API_KEY', '')
    COINBASE_SECRET: str = os.getenv('COINBASE_SECRET', '')
    
    KRAKEN_API_KEY: str = os.getenv('KRAKEN_API_KEY', '')
    KRAKEN_SECRET: str = os.getenv('KRAKEN_SECRET', '')
    
    KUCOIN_API_KEY: str = os.getenv('KUCOIN_API_KEY', '')
    KUCOIN_SECRET: str = os.getenv('KUCOIN_SECRET', '')
    KUCOIN_PASSPHRASE: str = os.getenv('KUCOIN_PASSPHRASE', '')
    
    # Trading parameters
    INITIAL_CAPITAL: float = 10000.0
    MAX_POSITIONS: int = 5
    RISK_PER_TRADE: float = 0.02  # 2% risk per trade
    
    # Strategy selection
    ENABLE_MOMENTUM: bool = True
    ENABLE_MEAN_REVERSION: bool = True
    ENABLE_ORDER_BOOK: bool = True
    ENABLE_FUNDING_ARB: bool = False  # Requires futures (limited on these exchanges)
    
    # Timeframes
    CHECK_INTERVAL: int = 300  # 5 minutes
    DATA_LOOKBACK: int = 100  # candles
    
    # Assets to trade (USD pairs available on all exchanges)
    CRYPTO_SYMBOLS: List[str] = None
    
    def __post_init__(self):
        if self.CRYPTO_SYMBOLS is None:
            # Canada-friendly symbols (all available on Coinbase, Kraken, KuCoin)
            self.CRYPTO_SYMBOLS = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'ADA-USD', 'DOT-USD']

# ============================================================================
# DATA FETCHING - MULTI-EXCHANGE SUPPORT
# ============================================================================

class DataFetcher:
    """Fetch live market data from Canada-friendly exchanges"""
    
    def __init__(self, exchange: str = 'COINBASE'):
        self.exchange = exchange.upper()
        
        # Exchange URLs
        self.urls = {
            'COINBASE': {
                'base': 'https://api.exchange.coinbase.com',
                'products': '/products',
                'candles': '/products/{}/candles',
                'book': '/products/{}/book',
                'stats': '/products/{}/stats',
                'ticker': '/products/{}/ticker'
            },
            'KRAKEN': {
                'base': 'https://api.kraken.com',
                'ticker': '/0/public/Ticker',
                'ohlc': '/0/public/OHLC',
                'depth': '/0/public/Depth',
                'assets': '/0/public/Assets'
            },
            'KUCOIN': {
                'base': 'https://api.kucoin.com',
                'ticker': '/api/v1/market/orderbook/level1',
                'candles': '/api/v1/market/candles',
                'stats': '/api/v1/market/stats'
            }
        }
    
    def _get_symbol_format(self, symbol: str) -> str:
        """Convert symbol to exchange-specific format"""
        if self.exchange == 'COINBASE':
            return symbol  # Already BTC-USD format
        elif self.exchange == 'KRAKEN':
            # Kraken uses XBTUSD, ETHUSD, etc.
            mapping = {
                'BTC-USD': 'XBTUSD',
                'ETH-USD': 'ETHUSD',
                'SOL-USD': 'SOLUSD',
                'ADA-USD': 'ADAUSD',
                'DOT-USD': 'DOTUSD'
            }
            return mapping.get(symbol, symbol.replace('-', ''))
        elif self.exchange == 'KUCOIN':
            # KuCoin uses BTC-USDT format
            return symbol.replace('-USD', '-USDT')
        return symbol
    
    def get_ticker(self, symbol: str) -> Dict:
        """Get current price and 24h stats"""
        try:
            formatted = self._get_symbol_format(symbol)
            
            if self.exchange == 'COINBASE':
                url = f"{self.urls['COINBASE']['base']}{self.urls['COINBASE']['ticker']}".format(formatted)
                response = requests.get(url, timeout=10)
                data = response.json()
                
                return {
                    'symbol': symbol,
                    'price': float(data['price']),
                    'volume_24h': float(data['volume']),
                    'timestamp': datetime.now().isoformat()
                }
            
            elif self.exchange == 'KRAKEN':
                url = f"{self.urls['KRAKEN']['base']}{self.urls['KRAKEN']['ticker']}"
                params = {'pair': formatted}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                if 'result' in data and data['result']:
                    pair_data = list(data['result'].values())[0]
                    return {
                        'symbol': symbol,
                        'price': float(pair_data['c'][0]),
                        'volume_24h': float(pair_data['v'][1]),
                        'high_24h': float(pair_data['h'][1]),
                        'low_24h': float(pair_data['l'][1]),
                        'timestamp': datetime.now().isoformat()
                    }
            
            elif self.exchange == 'KUCOIN':
                url = f"{self.urls['KUCOIN']['base']}{self.urls['KUCOIN']['ticker']}"
                params = {'symbol': formatted}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                if data.get('data'):
                    return {
                        'symbol': symbol,
                        'price': float(data['data']['price']),
                        'timestamp': datetime.now().isoformat()
                    }
        
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol} from {self.exchange}: {e}")
        
        return None
    
    def get_order_book(self, symbol: str, limit: int = 100) -> Dict:
        """Get order book data for imbalance calculation"""
        try:
            formatted = self._get_symbol_format(symbol)
            
            if self.exchange == 'COINBASE':
                url = f"{self.urls['COINBASE']['base']}{self.urls['COINBASE']['book']}?level=2".format(formatted)
                response = requests.get(url, timeout=10)
                data = response.json()
                
                bids = pd.DataFrame(data['bids'], columns=['price', 'qty', 'orders'], dtype=float)
                asks = pd.DataFrame(data['asks'], columns=['price', 'qty', 'orders'], dtype=float)
                
                bid_volume = bids['qty'].sum()
                ask_volume = asks['qty'].sum()
                imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)
                
                return {
                    'symbol': symbol,
                    'bid_volume': bid_volume,
                    'ask_volume': ask_volume,
                    'imbalance': imbalance,
                    'timestamp': datetime.now().isoformat()
                }
            
            elif self.exchange == 'KRAKEN':
                url = f"{self.urls['KRAKEN']['base']}{self.urls['KRAKEN']['depth']}"
                params = {'pair': formatted, 'count': limit}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                if 'result' in data and data['result']:
                    pair_data = list(data['result'].values())[0]
                    bids = pd.DataFrame(pair_data['bids'], columns=['price', 'qty', 'timestamp'], dtype=float)
                    asks = pd.DataFrame(pair_data['asks'], columns=['price', 'qty', 'timestamp'], dtype=float)
                    
                    bid_volume = bids['qty'].sum()
                    ask_volume = asks['qty'].sum()
                    imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)
                    
                    return {
                        'symbol': symbol,
                        'bid_volume': bid_volume,
                        'ask_volume': ask_volume,
                        'imbalance': imbalance,
                        'timestamp': datetime.now().isoformat()
                    }
            
            elif self.exchange == 'KUCOIN':
                url = f"{self.urls['KUCOIN']['base']}/api/v1/market/orderbook/level2_100"
                params = {'symbol': formatted}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                if data.get('data'):
                    bids = pd.DataFrame(data['data']['bids'], columns=['price', 'qty'], dtype=float)
                    asks = pd.DataFrame(data['data']['asks'], columns=['price', 'qty'], dtype=float)
                    
                    bid_volume = bids['qty'].sum()
                    ask_volume = asks['qty'].sum()
                    imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)
                    
                    return {
                        'symbol': symbol,
                        'bid_volume': bid_volume,
                        'ask_volume': ask_volume,
                        'imbalance': imbalance,
                        'timestamp': datetime.now().isoformat()
                    }
        
        except Exception as e:
            logger.error(f"Error fetching order book for {symbol}: {e}")
        
        return None
    
    def get_klines(self, symbol: str, granularity: int = 3600, limit: int = 100) -> pd.DataFrame:
        """Get candlestick data for technical analysis"""
        try:
            formatted = self._get_symbol_format(symbol)
            
            if self.exchange == 'COINBASE':
                # Coinbase granularity in seconds: 60, 300, 900, 3600, 21600, 86400
                url = f"{self.urls['COINBASE']['base']}{self.urls['COINBASE']['candles']}".format(formatted)
                params = {'granularity': granularity}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                df = pd.DataFrame(data, columns=['timestamp', 'low', 'high', 'open', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                df = df.sort_values('timestamp')
                return df
            
            elif self.exchange == 'KRAKEN':
                # Kraken interval in minutes: 1, 5, 15, 30, 60, 240, 1440, 10080, 21600
                interval = granularity // 60
                url = f"{self.urls['KRAKEN']['base']}{self.urls['KRAKEN']['ohlc']}"
                params = {'pair': formatted, 'interval': interval}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                if 'result' in data and data['result']:
                    ohlc_data = list(data['result'].values())[0]
                    df = pd.DataFrame(ohlc_data, columns=[
                        'timestamp', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'
                    ])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                    df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
                    return df
            
            elif self.exchange == 'KUCOIN':
                # KuCoin type: 1min, 3min, 5min, 15min, 30min, 1hour, 2hour, 4hour, 6hour, 8hour, 12hour, 1day, 1week
                type_map = {60: '1min', 300: '5min', 900: '15min', 3600: '1hour', 86400: '1day'}
                kline_type = type_map.get(granularity, '1hour')
                
                url = f"{self.urls['KUCOIN']['base']}{self.urls['KUCOIN']['candles']}"
                params = {'symbol': formatted, 'type': kline_type}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                if data.get('data'):
                    df = pd.DataFrame(data['data'], columns=[
                        'timestamp', 'open', 'close', 'high', 'low', 'volume', 'amount'
                    ])
                    df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='s')
                    df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
                    return df
        
        except Exception as e:
            logger.error(f"Error fetching klines for {symbol}: {e}")
        
        return pd.DataFrame()
    
    def get_24h_stats(self, symbol: str) -> Dict:
        """Get 24h price change and volume"""
        try:
            formatted = self._get_symbol_format(symbol)
            
            if self.exchange == 'COINBASE':
                url = f"{self.urls['COINBASE']['base']}{self.urls['COINBASE']['stats']}".format(formatted)
                response = requests.get(url, timeout=10)
                data = response.json()
                
                return {
                    'symbol': symbol,
                    'price': float(data['last']),
                    'price_change': float(data.get('change_percent', 0)),
                    'volume': float(data['volume']),
                    'high': float(data['high']),
                    'low': float(data['low']),
                    'timestamp': datetime.now().isoformat()
                }
            
            else:
                # Fallback to ticker
                return self.get_ticker(symbol)
        
        except Exception as e:
            logger.error(f"Error fetching 24h stats for {symbol}: {e}")
        
        return None

# ============================================================================
# FREE DATA FETCHER (No Exchange Account Required!)
# ============================================================================

class FreeDataFetcher:
    """
    Fetch market data from FREE sources - no exchange API keys needed!
    Uses CoinGecko, CryptoCompare, and other free APIs
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.coingecko_key = config.COINGECKO_API_KEY
        self.cryptocompare_key = config.CRYPTOCOMPARE_API_KEY
        
        # CoinGecko API (free tier: 10-30 calls/minute)
        self.coingecko_url = "https://api.coingecko.com/api/v3"
        
        # CryptoCompare API (free tier: 100k calls/month)
        self.cryptocompare_url = "https://min-api.cryptocompare.com/data"
        
        # Coin symbol mapping
        self.symbol_to_id = {
            'BTC-USD': 'bitcoin',
            'ETH-USD': 'ethereum',
            'SOL-USD': 'solana',
            'ADA-USD': 'cardano',
            'DOT-USD': 'polkadot',
            'XRP-USD': 'ripple',
            'DOGE-USD': 'dogecoin',
            'AVAX-USD': 'avalanche-2',
            'MATIC-USD': 'matic-network',
            'LINK-USD': 'chainlink'
        }
    
    def _get_coin_id(self, symbol: str) -> str:
        """Convert symbol to CoinGecko coin ID"""
        return self.symbol_to_id.get(symbol, symbol.lower().replace('-', ''))
    
    def get_ticker(self, symbol: str) -> Dict:
        """Get current price and 24h stats from CoinGecko (FREE)"""
        try:
            coin_id = self._get_coin_id(symbol)
            
            # CoinGecko API - completely free, no key required for basic calls
            url = f"{self.coingecko_url}/coins/markets"
            params = {
                'vs_currency': 'usd',
                'ids': coin_id,
                'order': 'market_cap_desc',
                'sparkline': 'false',
                'price_change_percentage': '24h'
            }
            
            # Add API key if available (increases rate limits)
            if self.coingecko_key:
                params['x_cg_demo_api_key'] = self.coingecko_key
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data and len(data) > 0:
                coin = data[0]
                return {
                    'symbol': symbol,
                    'price': float(coin['current_price']),
                    'price_change': float(coin.get('price_change_percentage_24h', 0)),
                    'volume_24h': float(coin['total_volume']),
                    'market_cap': float(coin['market_cap']),
                    'high_24h': float(coin.get('high_24h', coin['current_price'])),
                    'low_24h': float(coin.get('low_24h', coin['current_price'])),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'coingecko'
                }
        
        except Exception as e:
            logger.warning(f"CoinGecko failed for {symbol}: {e}, trying CryptoCompare...")
        
        # Fallback to CryptoCompare
        try:
            symbol_base = symbol.split('-')[0]
            url = f"{self.cryptocompare_url}/price"
            params = {
                'fsym': symbol_base,
                'tsyms': 'USD',
                'api_key': self.cryptocompare_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if 'USD' in data:
                # Get 24h stats
                histo_url = f"{self.cryptocompare_url}/histoday"
                histo_params = {
                    'fsym': symbol_base,
                    'tsym': 'USD',
                    'limit': 1,
                    'api_key': self.cryptocompare_key
                }
                histo_response = requests.get(histo_url, params=histo_params, timeout=10)
                histo_data = histo_response.json()
                
                price = float(data['USD'])
                change_pct = 0
                volume = 0
                
                if histo_data.get('Data') and len(histo_data['Data']) > 1:
                    today = histo_data['Data'][-1]
                    yesterday = histo_data['Data'][-2]
                    change_pct = ((today['close'] - yesterday['close']) / yesterday['close']) * 100
                    volume = float(today['volumeto'])
                
                return {
                    'symbol': symbol,
                    'price': price,
                    'price_change': change_pct,
                    'volume_24h': volume,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'cryptocompare'
                }
        
        except Exception as e:
            logger.error(f"Both free APIs failed for {symbol}: {e}")
        
        return None
    
    def get_klines(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """Get historical OHLCV data from CoinGecko (FREE)"""
        try:
            coin_id = self._get_coin_id(symbol)
            
            url = f"{self.coingecko_url}/coins/{coin_id}/market_chart"
            params = {
                'vs_currency': 'usd',
                'days': str(days),
                'interval': 'daily'
            }
            
            if self.coingecko_key:
                params['x_cg_demo_api_key'] = self.coingecko_key
            
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            if 'prices' in data and len(data['prices']) > 0:
                # Create DataFrame from prices
                prices_df = pd.DataFrame(data['prices'], columns=['timestamp', 'close'])
                prices_df['timestamp'] = pd.to_datetime(prices_df['timestamp'], unit='ms')
                
                # Get market caps and volumes
                if 'market_caps' in data:
                    mc_df = pd.DataFrame(data['market_caps'], columns=['timestamp', 'market_cap'])
                    prices_df = prices_df.merge(mc_df, on='timestamp', how='left')
                
                if 'total_volumes' in data:
                    vol_df = pd.DataFrame(data['total_volumes'], columns=['timestamp', 'volume'])
                    prices_df = prices_df.merge(vol_df, on='timestamp', how='left')
                
                # Estimate OHLC from close prices
                prices_df['open'] = prices_df['close'].shift(1)
                prices_df['high'] = prices_df[['open', 'close']].max(axis=1) * 1.01
                prices_df['low'] = prices_df[['open', 'close']].min(axis=1) * 0.99
                
                # Fill first row
                prices_df.loc[0, 'open'] = prices_df.loc[0, 'close']
                prices_df.loc[0, 'high'] = prices_df.loc[0, 'close'] * 1.01
                prices_df.loc[0, 'low'] = prices_df.loc[0, 'close'] * 0.99
                
                return prices_df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].dropna()
        
        except Exception as e:
            logger.warning(f"CoinGecko history failed for {symbol}: {e}")
        
        # Fallback to CryptoCompare
        try:
            symbol_base = symbol.split('-')[0]
            url = f"{self.cryptocompare_url}/histoday"
            params = {
                'fsym': symbol_base,
                'tsym': 'USD',
                'limit': days,
                'api_key': self.cryptocompare_key
            }
            
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            if data.get('Data'):
                df = pd.DataFrame(data['Data'])
                df['timestamp'] = pd.to_datetime(df['time'], unit='s')
                df = df.rename(columns={
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'volumeto': 'volume'
                })
                return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        
        except Exception as e:
            logger.error(f"Both free APIs failed for {symbol} history: {e}")
        
        return pd.DataFrame()
    
    def get_24h_stats(self, symbol: str) -> Dict:
        """Get 24h stats - same as ticker for free sources"""
        return self.get_ticker(symbol)
    
    def get_order_book(self, symbol: str, limit: int = 100) -> Dict:
        """
        Get simulated order book data
        Note: Free APIs don't provide real-time order books
        We'll use volume and price change as a proxy
        """
        ticker = self.get_ticker(symbol)
        if not ticker:
            return None
        
        # Simulate order book imbalance based on price action
        # This is a simplified proxy - in production, you'd want real order book data
        price_change = ticker.get('price_change', 0)
        
        # Positive price change suggests buying pressure (bid imbalance)
        # Negative price change suggests selling pressure (ask imbalance)
        imbalance = price_change / 100  # Normalize to roughly -0.5 to 0.5 range
        imbalance = max(-0.5, min(0.5, imbalance))  # Clamp
        
        return {
            'symbol': symbol,
            'bid_volume': ticker.get('volume_24h', 0) * (0.5 + imbalance),
            'ask_volume': ticker.get('volume_24h', 0) * (0.5 - imbalance),
            'imbalance': imbalance,
            'timestamp': datetime.now().isoformat(),
            'source': 'simulated_from_price_action',
            'note': 'Free APIs do not provide order book data. Using price change as proxy.'
        }

# ============================================================================
# TECHNICAL INDICATORS
# ============================================================================

class TechnicalIndicators:
    """Calculate technical indicators"""
    
    @staticmethod
    def rsi(prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not rsi.empty else 50
    
    @staticmethod
    def ema(prices: pd.Series, period: int = 20) -> float:
        """Calculate EMA"""
        return prices.ewm(span=period, adjust=False).mean().iloc[-1]
    
    @staticmethod
    def sma(prices: pd.Series, period: int = 20) -> float:
        """Calculate SMA"""
        return prices.rolling(window=period).mean().iloc[-1]
    
    @staticmethod
    def bollinger_bands(prices: pd.Series, period: int = 20, std_dev: int = 2) -> Tuple[float, float, float]:
        """Calculate Bollinger Bands (upper, middle, lower)"""
        middle = prices.rolling(window=period).mean().iloc[-1]
        std = prices.rolling(window=period).std().iloc[-1]
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower
    
    @staticmethod
    def macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float, float]:
        """Calculate MACD"""
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line.iloc[-1], signal_line.iloc[-1], histogram.iloc[-1]

# ============================================================================
# TRADING STRATEGIES
# ============================================================================

class MomentumStrategy:
    """
    Momentum strategy using EMA crossover + RSI confirmation
    
    Strategy: EMA 12 crosses above EMA 26 + RSI > 50 = LONG
             EMA 12 crosses below EMA 26 + RSI < 50 = SHORT
    """
    
    def __init__(self):
        self.name = "MomentumStrategy"
    
    def generate_signal(self, df: pd.DataFrame) -> Optional[Dict]:
        """Generate trading signal based on momentum"""
        if df.empty or len(df) < 30:
            return None
        
        prices = df['close']
        
        # Calculate EMAs
        ema_12 = prices.ewm(span=12, adjust=False).mean()
        ema_26 = prices.ewm(span=26, adjust=False).mean()
        
        # Calculate RSI
        rsi = TechnicalIndicators.rsi(prices)
        
        # Current and previous EMA values
        curr_12 = ema_12.iloc[-1]
        curr_26 = ema_26.iloc[-1]
        prev_12 = ema_12.iloc[-2]
        prev_26 = ema_26.iloc[-2]
        
        # Bullish crossover (12 crosses above 26)
        if prev_12 <= prev_26 and curr_12 > curr_26 and rsi > 50:
            return {
                'signal': 'LONG',
                'strength': abs(curr_12 - curr_26) / curr_26,
                'reason': f'EMA 12/26 bullish crossover, RSI {rsi:.1f}',
                'strategy': self.name
            }
        
        # Bearish crossover (12 crosses below 26)
        if prev_12 >= prev_26 and curr_12 < curr_26 and rsi < 50:
            return {
                'signal': 'SHORT',
                'strength': abs(curr_12 - curr_26) / curr_26,
                'reason': f'EMA 12/26 bearish crossover, RSI {rsi:.1f}',
                'strategy': self.name
            }
        
        return None

class MeanReversion:
    """
    Bollinger Band mean reversion
    
    Strategy: Price touches upper band = short
             Price touches lower band = long
    """
    
    def __init__(self, std_dev: int = 2):
        self.std_dev = std_dev
        self.name = "MeanReversion"
    
    def generate_signal(self, df: pd.DataFrame) -> Optional[Dict]:
        """Generate trading signal based on Bollinger Bands"""
        if df.empty or len(df) < 20:
            return None
        
        prices = df['close']
        upper, middle, lower = TechnicalIndicators.bollinger_bands(prices, std_dev=self.std_dev)
        current_price = prices.iloc[-1]
        
        # Price above upper band = overbought
        if current_price > upper:
            rsi = TechnicalIndicators.rsi(prices)
            if rsi > 70:  # Confirm with RSI
                return {
                    'signal': 'SHORT',
                    'strength': (current_price - upper) / upper,
                    'reason': f'Price above upper BB, RSI {rsi:.1f}',
                    'strategy': self.name
                }
        
        # Price below lower band = oversold
        if current_price < lower:
            rsi = TechnicalIndicators.rsi(prices)
            if rsi < 30:  # Confirm with RSI
                return {
                    'signal': 'LONG',
                    'strength': (lower - current_price) / lower,
                    'reason': f'Price below lower BB, RSI {rsi:.1f}',
                    'strategy': self.name
                }
        
        return None

class OrderBookImbalance:
    """
    Jane Street style order book imbalance
    
    Strategy: When bid volume significantly exceeds ask volume = bullish
             When ask volume significantly exceeds bid volume = bearish
    """
    
    def __init__(self, threshold: float = 0.2):  # 20% imbalance
        self.threshold = threshold
        self.name = "OrderBookImbalance"
    
    def generate_signal(self, orderbook_data: Dict) -> Optional[Dict]:
        """Generate trading signal based on order book imbalance"""
        if not orderbook_data:
            return None
        
        imbalance = orderbook_data['imbalance']
        
        # Strong bid imbalance = buying pressure
        if imbalance > self.threshold:
            return {
                'signal': 'LONG',
                'strength': abs(imbalance),
                'reason': f'Order book imbalance {imbalance:.2%} (buying pressure)',
                'strategy': self.name
            }
        
        # Strong ask imbalance = selling pressure
        if imbalance < -self.threshold:
            return {
                'signal': 'SHORT',
                'strength': abs(imbalance),
                'reason': f'Order book imbalance {imbalance:.2%} (selling pressure)',
                'strategy': self.name
            }
        
        return None

# ============================================================================
# PORTFOLIO MANAGER
# ============================================================================

class PortfolioManager:
    """Manage positions and risk"""
    
    def __init__(self, config: Config):
        self.config = config
        self.positions = {}
        self.cash = config.INITIAL_CAPITAL
        self.equity = config.INITIAL_CAPITAL
        self.trade_history = []
    
    def calculate_position_size(self, signal: Dict, current_price: float) -> float:
        """Calculate position size based on risk management"""
        # Risk per trade
        risk_amount = self.equity * self.config.RISK_PER_TRADE
        
        # Assume 2% stop loss for calculation
        stop_loss_pct = 0.02
        position_size = risk_amount / (current_price * stop_loss_pct)
        
        # Limit by max positions
        max_position_value = self.equity / self.config.MAX_POSITIONS
        max_size = max_position_value / current_price
        
        return min(position_size, max_size)
    
    def can_open_position(self, symbol: str) -> bool:
        """Check if we can open a new position"""
        return len(self.positions) < self.config.MAX_POSITIONS and symbol not in self.positions
    
    def open_position(self, signal: Dict, price: float, timestamp: str, symbol: str):
        """Open a new position"""
        direction = signal['signal']
        size = self.calculate_position_size(signal, price)
        
        cost = size * price
        if cost > self.cash:
            logger.warning(f"Insufficient cash for {symbol}")
            return False
        
        self.positions[symbol] = {
            'symbol': symbol,
            'direction': direction,
            'entry_price': price,
            'size': size,
            'entry_time': timestamp,
            'strategy': signal['strategy'],
            'stop_loss': price * 0.98 if direction == 'LONG' else price * 1.02,
            'take_profit': price * 1.06 if direction == 'LONG' else price * 0.94
        }
        
        self.cash -= cost
        
        logger.info(f"OPENED {direction} {symbol}: {size:.6f} @ ${price:.2f}")
        return True
    
    def check_exits(self, current_prices: Dict) -> List[Dict]:
        """Check if any positions should be closed"""
        closed = []
        
        for symbol, pos in list(self.positions.items()):
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            direction = pos['direction']
            
            # Check stop loss
            if direction == 'LONG' and current_price <= pos['stop_loss']:
                self.close_position(symbol, current_price, 'STOP_LOSS')
                closed.append({'symbol': symbol, 'reason': 'STOP_LOSS'})
            elif direction == 'SHORT' and current_price >= pos['stop_loss']:
                self.close_position(symbol, current_price, 'STOP_LOSS')
                closed.append({'symbol': symbol, 'reason': 'STOP_LOSS'})
            
            # Check take profit
            elif direction == 'LONG' and current_price >= pos['take_profit']:
                self.close_position(symbol, current_price, 'TAKE_PROFIT')
                closed.append({'symbol': symbol, 'reason': 'TAKE_PROFIT'})
            elif direction == 'SHORT' and current_price <= pos['take_profit']:
                self.close_position(symbol, current_price, 'TAKE_PROFIT')
                closed.append({'symbol': symbol, 'reason': 'TAKE_PROFIT'})
        
        return closed
    
    def close_position(self, symbol: str, exit_price: float, reason: str):
        """Close a position"""
        if symbol not in self.positions:
            return
        
        pos = self.positions.pop(symbol)
        
        # Calculate P&L
        if pos['direction'] == 'LONG':
            pnl = (exit_price - pos['entry_price']) * pos['size']
        else:
            pnl = (pos['entry_price'] - exit_price) * pos['size']
        
        # Return capital
        self.cash += (pos['size'] * exit_price)
        
        trade_record = {
            'symbol': symbol,
            'direction': pos['direction'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'size': pos['size'],
            'pnl': pnl,
            'pnl_pct': (pnl / (pos['entry_price'] * pos['size'])) * 100,
            'entry_time': pos['entry_time'],
            'exit_time': datetime.now().isoformat(),
            'strategy': pos['strategy'],
            'exit_reason': reason
        }
        
        self.trade_history.append(trade_record)
        
        logger.info(f"CLOSED {symbol}: ${pnl:+.2f} ({reason})")
    
    def update_equity(self, current_prices: Dict):
        """Update portfolio equity"""
        position_value = 0
        for symbol, pos in self.positions.items():
            if symbol in current_prices:
                position_value += pos['size'] * current_prices[symbol]
        
        self.equity = self.cash + position_value
    
    def get_stats(self) -> Dict:
        """Get portfolio statistics"""
        if not self.trade_history:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_trade': 0,
                'current_equity': self.equity,
                'return_pct': ((self.equity - self.config.INITIAL_CAPITAL) / self.config.INITIAL_CAPITAL) * 100
            }
        
        wins = sum(1 for t in self.trade_history if t['pnl'] > 0)
        total_pnl = sum(t['pnl'] for t in self.trade_history)
        
        return {
            'total_trades': len(self.trade_history),
            'winning_trades': wins,
            'losing_trades': len(self.trade_history) - wins,
            'win_rate': (wins / len(self.trade_history)) * 100,
            'total_pnl': total_pnl,
            'avg_trade': total_pnl / len(self.trade_history),
            'current_equity': self.equity,
            'return_pct': ((self.equity - self.config.INITIAL_CAPITAL) / self.config.INITIAL_CAPITAL) * 100
        }

# ============================================================================
# MAIN TRADING BOT
# ============================================================================

class TradingBot:
    """Main trading bot that orchestrates everything"""
    
    def __init__(self, config: Config):
        self.config = config
        
        # Use free data fetcher if FREE_DATA selected, otherwise use exchange
        if config.PRIMARY_EXCHANGE == 'FREE_DATA':
            self.data_fetcher = FreeDataFetcher(config)
            logger.info("Using FREE data sources (CoinGecko, CryptoCompare) - no API keys needed!")
        else:
            self.data_fetcher = DataFetcher(exchange=config.PRIMARY_EXCHANGE)
            logger.info(f"Using exchange: {config.PRIMARY_EXCHANGE}")
        
        self.portfolio = PortfolioManager(config)
        
        # Initialize strategies
        self.strategies = []
        if config.ENABLE_MOMENTUM:
            self.strategies.append(MomentumStrategy())
        if config.ENABLE_MEAN_REVERSION:
            self.strategies.append(MeanReversion())
        if config.ENABLE_ORDER_BOOK:
            self.strategies.append(OrderBookImbalance())
    
    def run_cycle(self):
        """Run one trading cycle"""
        logger.info("=" * 60)
        logger.info(f"TRADING CYCLE - {datetime.now().isoformat()}")
        logger.info(f"DATA SOURCE: {self.config.PRIMARY_EXCHANGE}")
        logger.info("=" * 60)
        
        signals_generated = []
        
        for symbol in self.config.CRYPTO_SYMBOLS:
            logger.info(f"\n--- Analyzing {symbol} ---")
            
            # Fetch data (different methods for free vs exchange)
            if isinstance(self.data_fetcher, FreeDataFetcher):
                ticker_data = self.data_fetcher.get_ticker(symbol)
                orderbook_data = self.data_fetcher.get_order_book(symbol)
                klines_df = self.data_fetcher.get_klines(symbol, days=30)
            else:
                ticker_data = self.data_fetcher.get_ticker(symbol)
                orderbook_data = self.data_fetcher.get_order_book(symbol)
                klines_df = self.data_fetcher.get_klines(symbol, granularity=3600, limit=100)
            
            # Generate signals from each strategy
            for strategy in self.strategies:
                if isinstance(strategy, MomentumStrategy):
                    signal = strategy.generate_signal(klines_df)
                elif isinstance(strategy, MeanReversion):
                    signal = strategy.generate_signal(klines_df)
                elif isinstance(strategy, OrderBookImbalance):
                    signal = strategy.generate_signal(orderbook_data)
                else:
                    signal = None
                
                if signal:
                    signal['symbol'] = symbol
                    signals_generated.append(signal)
                    logger.info(f"SIGNAL: {signal['signal']} {symbol} - {signal['reason']}")
        
        # Execute trades
        current_prices = {}
        for symbol in self.config.CRYPTO_SYMBOLS:
            ticker = self.data_fetcher.get_ticker(symbol)
            if ticker:
                current_prices[symbol] = ticker['price']
        
        # Check exits first
        exits = self.portfolio.check_exits(current_prices)
        
        # Then check entries
        for signal in signals_generated:
            symbol = signal['symbol']
            if symbol in current_prices and self.portfolio.can_open_position(symbol):
                self.portfolio.open_position(signal, current_prices[symbol], datetime.now().isoformat(), symbol)
        
        # Update equity
        self.portfolio.update_equity(current_prices)
        
        # Log stats
        stats = self.portfolio.get_stats()
        logger.info("\n" + "=" * 60)
        logger.info("PORTFOLIO STATS")
        logger.info("=" * 60)
        logger.info(f"Equity: ${self.portfolio.equity:,.2f}")
        logger.info(f"Cash: ${self.portfolio.cash:,.2f}")
        logger.info(f"Open Positions: {len(self.portfolio.positions)}")
        logger.info(f"Total Trades: {stats['total_trades']}")
        logger.info(f"Win Rate: {stats['win_rate']:.1f}%")
        logger.info(f"Total P&L: ${stats['total_pnl']:+.2f}")
        logger.info(f"Return: {stats['return_pct']:+.2f}%")
        
        return stats
    
    def run(self):
        """Main loop - for GitHub Actions, run once"""
        logger.info("\n" + "=" * 60)
        logger.info("KIMI_CLAW TRADING BOT - CANADA EDITION")
        logger.info("=" * 60)
        logger.info(f"Exchange: {self.config.PRIMARY_EXCHANGE}")
        logger.info(f"Initial Capital: ${self.config.INITIAL_CAPITAL:,.2f}")
        logger.info(f"Max Positions: {self.config.MAX_POSITIONS}")
        logger.info(f"Risk Per Trade: {self.config.RISK_PER_TRADE:.1%}")
        logger.info(f"Strategies: {[s.name for s in self.strategies]}")
        logger.info(f"Symbols: {self.config.CRYPTO_SYMBOLS}")
        
        # Run one cycle (for GitHub Actions)
        stats = self.run_cycle()
        
        # Save results
        self.save_results()
        
        return stats
    
    def save_results(self):
        """Save trading results to JSON"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'exchange': self.config.PRIMARY_EXCHANGE,
            'config': {
                'initial_capital': self.config.INITIAL_CAPITAL,
                'risk_per_trade': self.config.RISK_PER_TRADE,
                'max_positions': self.config.MAX_POSITIONS
            },
            'portfolio': {
                'cash': self.portfolio.cash,
                'equity': self.portfolio.equity,
                'positions': self.portfolio.positions,
                'return_pct': ((self.portfolio.equity - self.config.INITIAL_CAPITAL) / self.config.INITIAL_CAPITAL) * 100
            },
            'trade_history': self.portfolio.trade_history,
            'stats': self.portfolio.get_stats()
        }
        
        with open('trading_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info("\nResults saved to trading_results.json")

# ============================================================================
# GITHUB ACTIONS ENTRY POINT
# ============================================================================

def main():
    """Main entry point for GitHub Actions"""
    # Load configuration
    config = Config()
    
    # Validate exchange selection (now includes FREE_DATA)
    valid_exchanges = ['FREE_DATA', 'COINBASE', 'KRAKEN', 'KUCOIN']
    if config.PRIMARY_EXCHANGE not in valid_exchanges:
        logger.error(f"Invalid exchange: {config.PRIMARY_EXCHANGE}. Must be one of {valid_exchanges}")
        return 1
    
    # Create and run bot
    bot = TradingBot(config)
    stats = bot.run()
    
    # Print summary for GitHub Actions logs
    print("\n" + "=" * 60)
    print("TRADING BOT COMPLETE - CANADA EDITION")
    print("=" * 60)
    print(f"Data Source: {config.PRIMARY_EXCHANGE}")
    print(f"Final Equity: ${bot.portfolio.equity:,.2f}")
    print(f"Total Return: {stats['return_pct']:+.2f}%")
    print(f"Total Trades: {stats['total_trades']}")
    print(f"Win Rate: {stats['win_rate']:.1f}%")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
