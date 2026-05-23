#!/usr/bin/env python3
"""
Market Data Fetcher for KIMI Rise of the Claw.

Fetches real-time market prices from multiple sources:
- Yahoo Finance (stocks, ETFs, forex)
- Kraken API (crypto)
- CCXT Binance (meme coins fallback)

Features:
- 15-minute caching to avoid rate limits
- Parallel batch fetching
- Graceful fallbacks on API failures
- Market status detection

Author: Claude Sonnet 4.5
Date: 2026-02-16
"""

import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logger = logging.getLogger(__name__)


class MarketDataFetcher:
    """Unified API for fetching real-time market prices."""

    def __init__(self, cache_duration_minutes: int = 15):
        """
        Initialize market data fetcher.

        Args:
            cache_duration_minutes: How long to cache prices (default 15 min)
        """
        self.cache = {}  # symbol -> {'price': float, 'timestamp': datetime}
        self.cache_duration = timedelta(minutes=cache_duration_minutes)

    def get_current_price(self, symbol: str, asset_type: str) -> Optional[float]:
        """
        Fetch current price for symbol.

        Args:
            symbol: Ticker (e.g., 'AAPL', 'BTC-USD', 'EURUSD=X')
            asset_type: 'stock', 'crypto', 'forex', 'meme', 'penny'

        Returns:
            Current price or None if unavailable
        """
        # Check cache first
        if self._is_cached(symbol):
            logger.debug(f"Using cached price for {symbol}")
            return self.cache[symbol]['price']

        # Route to appropriate fetcher
        price = None
        try:
            if asset_type in ['stock', 'penny', 'forex']:
                price = self._fetch_yahoo(symbol)
            elif asset_type in ['crypto', 'meme']:
                price = self._fetch_crypto(symbol)
            else:
                logger.warning(f"Unknown asset type: {asset_type}, defaulting to Yahoo")
                price = self._fetch_yahoo(symbol)
        except Exception as e:
            logger.error(f"Failed to fetch price for {symbol}: {e}")

        # Cache result if successful
        if price and price > 0:
            self._cache_price(symbol, price)
            return price

        # Try to use stale cache as fallback
        if symbol in self.cache:
            logger.warning(f"Using stale cache for {symbol}")
            return self.cache[symbol]['price']

        return None

    def get_batch_prices(self, symbols: List[Tuple[str, str]]) -> Dict[str, float]:
        """
        Fetch prices for multiple symbols in parallel.

        Args:
            symbols: List of (symbol, asset_type) tuples

        Returns:
            Dict mapping symbol to price
        """
        results = {}

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_symbol = {
                executor.submit(self.get_current_price, symbol, asset_type): symbol
                for symbol, asset_type in symbols
            }

            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    price = future.result(timeout=10)
                    if price:
                        results[symbol] = price
                except Exception as e:
                    logger.error(f"Batch fetch error for {symbol}: {e}")

        logger.info(f"Fetched {len(results)} of {len(symbols)} prices")
        return results

    def get_market_status(self) -> Dict[str, str]:
        """
        Check if markets are open.

        Returns:
            Dict with market status for each asset class
        """
        now = datetime.utcnow()
        hour = now.hour
        weekday = now.weekday()  # 0 = Monday, 6 = Sunday

        # US market hours: 9:30 AM - 4:00 PM EST (14:30 - 21:00 UTC)
        us_open = (14 <= hour < 21) and (weekday < 5)  # Mon-Fri only

        # Forex: 24/5 (closed Saturday evening - Sunday evening)
        forex_open = not (weekday == 5 or (weekday == 6 and hour < 21))

        return {
            'usMarkets': 'OPEN' if us_open else 'CLOSED',
            'cryptoMarkets': '24/7',
            'forexMarkets': 'OPEN' if forex_open else 'CLOSED',
            'lastMarketCheck': now.isoformat() + 'Z'
        }

    def _fetch_yahoo(self, symbol: str) -> Optional[float]:
        """
        Fetch from Yahoo Finance using yfinance.

        Args:
            symbol: Ticker symbol

        Returns:
            Current price or None
        """
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)

            # Try fast_info first (fastest method)
            try:
                price = ticker.fast_info.get('lastPrice')
                if price and price > 0:
                    logger.debug(f"Yahoo (fast_info): {symbol} = ${price:.2f}")
                    return float(price)
            except:
                pass

            # Fallback to history (last closing price)
            hist = ticker.history(period='1d', interval='1m')
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                if price and price > 0:
                    logger.debug(f"Yahoo (history): {symbol} = ${price:.2f}")
                    return float(price)

            logger.warning(f"Yahoo: No data for {symbol}")
            return None

        except Exception as e:
            logger.error(f"Yahoo fetch failed for {symbol}: {e}")
            return None

    def _fetch_crypto(self, symbol: str) -> Optional[float]:
        """
        Fetch from Kraken or CCXT (Binance fallback).

        Args:
            symbol: Crypto ticker (e.g., 'BTC-USD', 'ETH-USD')

        Returns:
            Current price or None
        """
        # Try Kraken first
        price = self._fetch_kraken(symbol)
        if price:
            return price

        # Fallback to CCXT Binance
        price = self._fetch_ccxt_binance(symbol)
        if price:
            return price

        # Last resort: try Yahoo Finance for major crypto
        return self._fetch_yahoo(symbol)

    def _fetch_kraken(self, symbol: str) -> Optional[float]:
        """
        Fetch from Kraken public API.

        Args:
            symbol: Crypto symbol (e.g., 'BTC-USD')

        Returns:
            Current price or None
        """
        try:
            import requests

            # Convert symbol format: BTC-USD -> XBTUSD (Kraken notation)
            kraken_pair = symbol.replace('-USD', 'USD').replace('BTC', 'XBT').replace('ETH', 'XETH')

            url = f"https://api.kraken.com/0/public/Ticker"
            params = {'pair': kraken_pair}

            response = requests.get(url, params=params, timeout=5)
            data = response.json()

            if data.get('error') and len(data['error']) > 0:
                logger.warning(f"Kraken error for {symbol}: {data['error']}")
                return None

            result = data.get('result', {})
            if result:
                # Get the first pair result (there should only be one)
                pair_data = next(iter(result.values()))
                price = float(pair_data['c'][0])  # 'c' = last trade closed
                logger.debug(f"Kraken: {symbol} = ${price:.2f}")
                return price

            return None

        except Exception as e:
            logger.error(f"Kraken fetch failed for {symbol}: {e}")
            return None

    def _fetch_ccxt_binance(self, symbol: str) -> Optional[float]:
        """
        Fetch from Binance using CCXT.

        Args:
            symbol: Crypto symbol (e.g., 'DOGE-USD', 'SHIB-USD')

        Returns:
            Current price or None
        """
        try:
            import ccxt

            exchange = ccxt.binance()

            # Convert symbol format: DOGE-USD -> DOGE/USDT (Binance uses USDT)
            binance_symbol = symbol.replace('-USD', '/USDT')

            ticker = exchange.fetch_ticker(binance_symbol)
            price = ticker['last']

            if price and price > 0:
                logger.debug(f"Binance: {symbol} = ${price:.6f}")
                return float(price)

            return None

        except Exception as e:
            logger.error(f"Binance (CCXT) fetch failed for {symbol}: {e}")
            return None

    def _is_cached(self, symbol: str) -> bool:
        """
        Check if symbol has valid cached price.

        Args:
            symbol: Ticker symbol

        Returns:
            True if cache is valid
        """
        if symbol not in self.cache:
            return False

        cache_age = datetime.now() - self.cache[symbol]['timestamp']
        return cache_age < self.cache_duration

    def _cache_price(self, symbol: str, price: float):
        """
        Store price in cache.

        Args:
            symbol: Ticker symbol
            price: Current price
        """
        self.cache[symbol] = {
            'price': price,
            'timestamp': datetime.now()
        }

    def clear_cache(self):
        """Clear all cached prices."""
        self.cache.clear()
        logger.info("Price cache cleared")


# Module-level convenience function
def fetch_price(symbol: str, asset_type: str) -> Optional[float]:
    """
    Convenience function to fetch a single price.

    Args:
        symbol: Ticker symbol
        asset_type: Asset type ('stock', 'crypto', etc.)

    Returns:
        Current price or None
    """
    fetcher = MarketDataFetcher()
    return fetcher.get_current_price(symbol, asset_type)


if __name__ == '__main__':
    # Test the fetcher
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    print("Testing Market Data Fetcher")
    print("=" * 60)

    fetcher = MarketDataFetcher()

    # Test stock
    print("\n[Stock] AAPL:")
    price = fetcher.get_current_price('AAPL', 'stock')
    print(f"  Price: ${price:.2f}" if price else "  Price: UNAVAILABLE")

    # Test ETF
    print("\n[ETF] SPY:")
    price = fetcher.get_current_price('SPY', 'stock')
    print(f"  Price: ${price:.2f}" if price else "  Price: UNAVAILABLE")

    # Test crypto
    print("\n[Crypto] BTC-USD:")
    price = fetcher.get_current_price('BTC-USD', 'crypto')
    print(f"  Price: ${price:.2f}" if price else "  Price: UNAVAILABLE")

    # Test forex
    print("\n[Forex] EURUSD=X:")
    price = fetcher.get_current_price('EURUSD=X', 'forex')
    print(f"  Price: ${price:.4f}" if price else "  Price: UNAVAILABLE")

    # Test market status
    print("\n[Market Status]:")
    status = fetcher.get_market_status()
    for market, state in status.items():
        print(f"  {market}: {state}")

    # Test batch fetching
    print("\n[Batch Fetch] Multiple symbols:")
    symbols = [
        ('SPY', 'stock'),
        ('QQQ', 'stock'),
        ('BTC-USD', 'crypto'),
        ('ETH-USD', 'crypto')
    ]
    prices = fetcher.get_batch_prices(symbols)
    for sym, price in prices.items():
        print(f"  {sym}: ${price:.2f}")

    print("\n" + "=" * 60)
    print("Test complete!")
