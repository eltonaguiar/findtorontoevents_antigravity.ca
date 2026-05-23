#!/usr/bin/env python3
"""
Enhanced Data Fetcher v2
Addresses: yfinance CI failures, forex intraday data, retry logic

Key Improvements:
- Exponential backoff retry for all sources
- Multi-source failover with priority tiers
- Intraday forex data (was: daily only)
- Rate limiting compliance
- Data freshness validation
"""

import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedDataFetcher:
    """
    Enhanced data fetcher with retry logic and failover.
    """
    
    # Source priority tiers
    CRYPTO_SOURCES = [
        ('binance', 'primary'),
        ('okx', 'secondary'),
        ('bybit', 'tertiary'),
        ('kucoin', 'fallback'),
    ]
    
    FOREX_SOURCES = [
        ('oanda', 'primary'),        # Intraday forex (if API key available)
        ('alphavantage', 'secondary'),  # Free tier: 5 calls/min
        ('twelvedata', 'tertiary'),     # Free tier: 8 calls/min
        ('frankfurter', 'fallback'),    # Daily only - last resort
    ]
    
    EQUITY_SOURCES = [
        ('yfinance', 'primary'),
        ('alphavantage', 'secondary'),
    ]
    
    def __init__(self, 
                 alpha_vantage_key: Optional[str] = None,
                 oanda_key: Optional[str] = None,
                 max_retries: int = 5,
                 base_delay: float = 2.0):
        
        self.alpha_vantage_key = alpha_vantage_key
        self.oanda_key = oanda_key
        self.max_retries = max_retries
        self.base_delay = base_delay
        
        # Rate limiting state
        self.last_call_time = {}
        self.rate_limits = {
            'alphavantage': 12.0,  # 5 calls per minute = 12s between calls
            'twelvedata': 7.5,     # 8 calls per minute = 7.5s between calls
            'oanda': 1.0,          # 1s between calls
        }
        
    def _rate_limit(self, source: str):
        """Enforce rate limiting for a source."""
        if source in self.rate_limits:
            min_interval = self.rate_limits[source]
            if source in self.last_call_time:
                elapsed = time.time() - self.last_call_time[source]
                if elapsed < min_interval:
                    sleep_time = min_interval - elapsed
                    logger.debug(f"Rate limiting {source}: sleeping {sleep_time:.2f}s")
                    time.sleep(sleep_time)
            self.last_call_time[source] = time.time()
    
    def _fetch_with_retry(self, 
                         fetch_func, 
                         source_name: str,
                         *args, 
                         **kwargs) -> Optional[pd.DataFrame]:
        """
        Fetch data with exponential backoff retry.
        
        Args:
            fetch_func: Function to call
            source_name: Name of the source (for logging)
            *args, **kwargs: Arguments to pass to fetch_func
            
        Returns:
            DataFrame or None
        """
        for attempt in range(self.max_retries):
            try:
                self._rate_limit(source_name)
                result = fetch_func(*args, **kwargs)
                
                if result is not None and len(result) > 0:
                    logger.info(f"{source_name}: Success on attempt {attempt + 1}")
                    return result
                    
            except Exception as e:
                # Check if it's a rate limit error
                if 'rate' in str(e).lower() or '429' in str(e):
                    delay = self.base_delay * (2 ** attempt) * 2  # Extra delay for rate limits
                    logger.warning(f"{source_name}: Rate limited, waiting {delay:.1f}s")
                else:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"{source_name}: Attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(delay)
                else:
                    logger.error(f"{source_name}: All {self.max_retries} attempts failed")
        
        return None
    
    def fetch_yfinance(self, 
                      symbol: str, 
                      period: str = "60d",
                      interval: str = "1h") -> Optional[pd.DataFrame]:
        """
        Fetch from yfinance with enhanced retry logic.
        
        Fixes CI failures by:
        - Longer retry delays
        - Multiple attempts
        - Proper error handling
        """
        def _fetch():
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                raise ValueError("Empty dataframe returned")
            
            # Standardize column names
            df.columns = [c.lower().replace(' ', '_') for c in df.columns]
            return df
        
        return self._fetch_with_retry(_fetch, 'yfinance')
    
    def fetch_alpha_vantage(self,
                           symbol: str,
                           interval: str = "60min") -> Optional[pd.DataFrame]:
        """
        Fetch from Alpha Vantage (backup for equities/forex).
        """
        if not self.alpha_vantage_key:
            logger.warning("Alpha Vantage API key not provided")
            return None
        
        def _fetch():
            url = "https://www.alphavantage.co/query"
            
            # Determine if forex or equity
            if '/' in symbol:
                # Forex
                from_sym, to_sym = symbol.split('/')
                params = {
                    "function": "FX_INTRADAY",
                    "from_symbol": from_sym,
                    "to_symbol": to_sym,
                    "interval": interval,
                    "apikey": self.alpha_vantage_key,
                    "outputsize": "full"
                }
            else:
                # Equity
                params = {
                    "function": "TIME_SERIES_INTRADAY",
                    "symbol": symbol,
                    "interval": interval,
                    "apikey": self.alpha_vantage_key,
                    "outputsize": "full"
                }
            
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            
            # Find the time series key
            time_series_key = [k for k in data.keys() if 'Time Series' in k]
            if not time_series_key:
                raise ValueError(f"No time series data: {data.get('Note', data.get('Information', 'Unknown error'))}")
            
            time_series = data[time_series_key[0]]
            
            # Convert to DataFrame
            df = pd.DataFrame.from_dict(time_series, orient='index')
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            
            # Rename columns
            df.columns = ['open', 'high', 'low', 'close', 'volume']
            df = df.astype(float)
            
            return df
        
        return self._fetch_with_retry(_fetch, 'alphavantage')
    
    def fetch_frankfurter(self,
                         symbol: str,
                         days: int = 60) -> Optional[pd.DataFrame]:
        """
        Fetch from Frankfurter (ECB daily rates) - LAST RESORT for forex.
        Note: Only daily data available.
        """
        def _fetch():
            if '/' not in symbol:
                raise ValueError("Frankfurter requires forex pair (e.g., EUR/USD)")
            
            base, quote = symbol.split('/')
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            url = f"https://api.frankfurter.app/{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}"
            params = {
                'from': base,
                'to': quote
            }
            
            response = requests.get(url, timeout=30)
            data = response.json()
            
            if 'rates' not in data:
                raise ValueError(f"No rates data: {data}")
            
            rates = data['rates']
            df = pd.DataFrame([
                {'date': date, 'close': rate[quote]}
                for date, rate in rates.items()
            ])
            
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)
            
            # Generate OHLC from close (daily only)
            df['open'] = df['close'].shift(1)
            df['high'] = df['close'] * 1.001  # Synthetic
            df['low'] = df['close'] * 0.999   # Synthetic
            df['volume'] = 0  # Not available
            
            df.dropna(inplace=True)
            
            logger.warning(f"Frankfurter only provides DAILY data for {symbol}")
            return df
        
        return self._fetch_with_retry(_fetch, 'frankfurter')
    
    def fetch_ccxt_crypto(self,
                         symbol: str,
                         exchange_name: str = 'binance',
                         timeframe: str = '1h',
                         limit: int = 500) -> Optional[pd.DataFrame]:
        """
        Fetch crypto data using CCXT.
        """
        import ccxt
        
        def _fetch():
            exchange_class = getattr(ccxt, exchange_name)
            exchange = exchange_class({'enableRateLimit': True})

            # Format symbol for exchange
            formatted_symbol = symbol if '/' in symbol else f"{symbol[:-4]}/{symbol[-4:]}"  # BTCUSDT -> BTC/USDT

            ohlcv = exchange.fetch_ohlcv(formatted_symbol, timeframe, limit=limit)
            
            if not ohlcv:
                raise ValueError("Empty OHLCV data")
            
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
        
        return self._fetch_with_retry(_fetch, exchange_name)
    
    def fetch_crypto(self,
                    symbol: str,
                    timeframe: str = '1h',
                    limit: int = 500) -> Optional[pd.DataFrame]:
        """
        Fetch crypto data with failover across exchanges.
        """
        # Try each exchange in priority order
        for exchange_name, priority in self.CRYPTO_SOURCES:
            logger.info(f"Trying {exchange_name} ({priority}) for {symbol}...")
            
            df = self.fetch_ccxt_crypto(symbol, exchange_name, timeframe, limit)
            
            if df is not None and self.validate_data_freshness(df):
                logger.info(f"✓ Successfully fetched from {exchange_name}")
                return df
        
        logger.error(f"All crypto sources failed for {symbol}")
        return None
    
    def fetch_forex(self,
                   symbol: str,
                   interval: str = "1h") -> Optional[pd.DataFrame]:
        """
        Fetch forex data with intraday sources.
        
        FIX: Was using Frankfurter (daily only), now tries intraday first.
        """
        # Try intraday sources first
        for source_name, priority in self.FOREX_SOURCES:
            if source_name == 'frankfurter':
                continue  # Skip daily-only source for now
            
            logger.info(f"Trying {source_name} ({priority}) for {symbol}...")
            
            if source_name == 'alphavantage':
                df = self.fetch_alpha_vantage(symbol, interval)
            else:
                continue  # Other sources not yet implemented
            
            if df is not None and self.validate_data_freshness(df):
                logger.info(f"✓ Successfully fetched intraday forex from {source_name}")
                return df
        
        # Fallback to Frankfurter (daily only)
        logger.warning(f"No intraday source available for {symbol}, falling back to daily")
        return self.fetch_frankfurter(symbol)
    
    def fetch_equity(self,
                    symbol: str,
                    interval: str = "1h") -> Optional[pd.DataFrame]:
        """
        Fetch equity data with failover.
        """
        # Try yfinance first (primary)
        logger.info(f"Trying yfinance for {symbol}...")
        df = self.fetch_yfinance(symbol, interval=interval)
        
        if df is not None and self.validate_data_freshness(df):
            logger.info("✓ Successfully fetched from yfinance")
            return df
        
        # Fallback to Alpha Vantage
        logger.info("yfinance failed, trying Alpha Vantage...")
        df = self.fetch_alpha_vantage(symbol, interval)
        
        if df is not None and self.validate_data_freshness(df):
            logger.info("✓ Successfully fetched from Alpha Vantage")
            return df
        
        logger.error(f"All equity sources failed for {symbol}")
        return None
    
    def validate_data_freshness(self,
                               df: pd.DataFrame,
                               max_age_minutes: int = 15) -> bool:
        """
        Validate that data is fresh.
        
        Args:
            df: DataFrame with datetime index
            max_age_minutes: Maximum acceptable age
            
        Returns:
            True if data is fresh
        """
        if df.empty:
            logger.warning("Empty dataframe")
            return False
        
        last_timestamp = df.index[-1]
        age = datetime.now() - last_timestamp
        
        if age > timedelta(minutes=max_age_minutes):
            logger.warning(f"Data stale: {age.total_seconds()/60:.1f} minutes old")
            return False
        
        logger.debug(f"Data fresh: {age.total_seconds()/60:.1f} minutes old")
        return True
    
    def fetch(self,
             symbol: str,
             asset_type: str = 'auto',
             interval: str = '1h') -> Optional[pd.DataFrame]:
        """
        Universal fetch method with automatic asset type detection.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT', 'EUR/USD', 'AAPL')
            asset_type: 'crypto', 'forex', 'equity', or 'auto'
            interval: Time interval (e.g., '1h', '1d')
            
        Returns:
            DataFrame with OHLCV data or None
        """
        # Auto-detect asset type
        if asset_type == 'auto':
            if '/' in symbol:
                # Check if crypto or forex
                if any(x in symbol.upper() for x in ['BTC', 'ETH', 'USDT', 'USD']):
                    if symbol.upper().endswith('USDT') or '/USDT' in symbol.upper():
                        asset_type = 'crypto'
                    else:
                        asset_type = 'forex'
                else:
                    asset_type = 'forex'
            else:
                asset_type = 'equity'
        
        logger.info(f"Fetching {symbol} as {asset_type}...")
        
        if asset_type == 'crypto':
            return self.fetch_crypto(symbol, interval)
        elif asset_type == 'forex':
            return self.fetch_forex(symbol, interval)
        elif asset_type == 'equity':
            return self.fetch_equity(symbol, interval)
        else:
            logger.error(f"Unknown asset type: {asset_type}")
            return None


def test_data_fetcher():
    """Test the enhanced data fetcher."""
    print("="*60)
    print("ENHANCED DATA FETCHER - TEST SUITE")
    print("="*60)
    
    fetcher = EnhancedDataFetcher(
        alpha_vantage_key=None,  # Add your key here
        max_retries=3,
        base_delay=2.0
    )
    
    tests = [
        ('BTC/USDT', 'crypto'),
        ('ETH/USDT', 'crypto'),
        ('EUR/USD', 'forex'),
        ('AAPL', 'equity'),
    ]
    
    for symbol, expected_type in tests:
        print(f"\n[TEST] {symbol} ({expected_type})")
        
        df = fetcher.fetch(symbol)
        
        if df is not None:
            print(f"  ✓ Success: {len(df)} rows")
            print(f"  Latest: {df.index[-1]}")
            print(f"  Close: {df['close'].iloc[-1]:.2f}")
        else:
            print(f"  ✗ Failed to fetch")


if __name__ == "__main__":
    test_data_fetcher()
