"""
Real-time Price Fetcher with Scrapling Fallback

Fetches current cryptocurrency prices from multiple sources:
1. CoinGecko API (primary)
2. CoinMarketCap API (secondary)
3. Scrapling web scraper (fallback)
"""

import json
import logging
import os
import time
from typing import Optional, Dict
from datetime import datetime, timedelta
from pathlib import Path
import requests

logger = logging.getLogger(__name__)

# Cache for prices
_price_cache: Dict[str, tuple] = {}
CACHE_DURATION = 60  # Cache prices for 60 seconds


def get_cached_price(symbol: str) -> Optional[float]:
    """Get price from cache if not expired"""
    global _price_cache
    if symbol in _price_cache:
        price, timestamp = _price_cache[symbol]
        if datetime.now() - timestamp < timedelta(seconds=CACHE_DURATION):
            return price
    return None


def set_cached_price(symbol: str, price: float):
    """Cache a price"""
    global _price_cache
    _price_cache[symbol] = (price, datetime.now())


def normalize_symbol(symbol: str) -> str:
    """Normalize symbol for API calls"""
    # Remove -USD, -USDT, -USD-PERP, etc.
    symbol = symbol.upper()
    for suffix in ['-USD-PERP', '-USDT-PERP', '-PERP', '-USD', '-USDT', 'USDT', 'USD']:
        if symbol.endswith(suffix):
            symbol = symbol[:-len(suffix)]
            break
    return symbol.lower()


def fetch_coingecko_price(symbol: str) -> Optional[float]:
    """Fetch price from CoinGecko API"""
    try:
        coin_id = normalize_symbol(symbol)
        
        # Map common symbols to CoinGecko IDs
        coin_map = {
            'btc': 'bitcoin',
            'eth': 'ethereum',
            'sol': 'solana',
            'bnb': 'binancecoin',
            'xrp': 'ripple',
            'ada': 'cardano',
            'doge': 'dogecoin',
            'dot': 'polkadot',
            'link': 'chainlink',
            'avax': 'avalanche-2',
            'near': 'near',
            'inj': 'injective-protocol',
            'render': 'render-token',
            'bonk': 'bonk',
            'wif': 'dogwifcoin',
            'pepe': 'pepe',
            'shib': 'shiba-inu',
            'spy': None,  # Stocks not on CoinGecko
            'qqq': None,
        }
        
        coin_id = coin_map.get(coin_id, coin_id)
        if not coin_id:
            return None
        
        url = f"https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': coin_id,
            'vs_currencies': 'usd',
            'include_24hr_change': 'false'
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if coin_id in data and 'usd' in data[coin_id]:
                price = float(data[coin_id]['usd'])
                logger.info(f"CoinGecko price for {symbol}: ${price}")
                return price
                
    except Exception as e:
        logger.debug(f"CoinGecko fetch failed for {symbol}: {e}")
    
    return None


def fetch_coinmarketcap_price(symbol: str) -> Optional[float]:
    """Fetch price from CoinMarketCap API"""
    api_key = os.getenv('COINMARKETCAP_API_KEY')
    if not api_key:
        return None
    
    try:
        symbol_clean = normalize_symbol(symbol).upper()
        
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        headers = {
            'X-CMC_PRO_API_KEY': api_key,
            'Accept': 'application/json'
        }
        params = {
            'symbol': symbol_clean,
            'convert': 'USD'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and symbol_clean in data['data']:
                price = float(data['data'][symbol_clean]['quote']['USD']['price'])
                logger.info(f"CMC price for {symbol}: ${price}")
                return price
                
    except Exception as e:
        logger.debug(f"CoinMarketCap fetch failed for {symbol}: {e}")
    
    return None


def fetch_scrapling_price(symbol: str) -> Optional[float]:
    """Fetch price using Scrapling as fallback"""
    try:
        # Try to import scrapling
        from scrapling import Fetcher
        
        symbol_clean = normalize_symbol(symbol).upper()
        
        # Try CoinMarketCap public page
        url = f"https://coinmarketcap.com/currencies/{symbol_clean.lower()}/"
        
        fetcher = Fetcher()
        page = fetcher.get(url, timeout=15)
        
        # Look for price in the page
        # CoinMarketCap has price in various selectors
        selectors = [
            '[data-test="text-cdp-price-display"]',
            '.priceValue',
            '[class*="price"]',
            'h2[class*="price"]',
        ]
        
        for selector in selectors:
            try:
                element = page.select_one(selector)
                if element:
                    price_text = element.text.strip().replace('$', '').replace(',', '')
                    price = float(price_text)
                    if price > 0:
                        logger.info(f"Scrapling price for {symbol}: ${price}")
                        return price
            except:
                continue
                
    except ImportError:
        logger.debug("Scrapling not installed")
    except Exception as e:
        logger.debug(f"Scrapling fetch failed for {symbol}: {e}")
    
    return None


_BINANCE_SPOT_BASES = [
    "https://api.binance.com",
    "https://api.binance.us",
    "https://data-api.binance.vision",
]


def fetch_binance_price(symbol: str) -> Optional[float]:
    """Fetch price from Binance public API with endpoint failover"""
    try:
        symbol_clean = normalize_symbol(symbol).upper()

        # Try USDT pair first, then USD
        for quote in ['USDT', 'USD', 'BUSD']:
            for base in _BINANCE_SPOT_BASES:
                try:
                    url = f"{base}/api/v3/ticker/price"
                    params = {'symbol': f"{symbol_clean}{quote}"}

                    response = requests.get(url, params=params, timeout=10)
                    if response.status_code in (451, 403):
                        continue  # geo-blocked, try next endpoint
                    if response.status_code == 200:
                        data = response.json()
                        price = float(data['price'])
                        logger.info(f"Binance price for {symbol}: ${price}")
                        return price
                except:
                    continue

    except Exception as e:
        logger.debug(f"Binance fetch failed for {symbol}: {e}")

    return None


def get_current_price(symbol: str) -> Optional[float]:
    """
    Get current market price for a symbol using multiple sources.
    
    Order:
    1. Cache
    2. CoinGecko API
    3. CoinMarketCap API
    4. Binance API
    5. Scrapling (web scraping)
    """
    # Check cache first
    cached = get_cached_price(symbol)
    if cached:
        return cached
    
    # Try each source in order
    sources = [
        ("CoinGecko", fetch_coingecko_price),
        ("CoinMarketCap", fetch_coinmarketcap_price),
        ("Binance", fetch_binance_price),
        ("Scrapling", fetch_scrapling_price),
    ]
    
    for source_name, fetch_func in sources:
        try:
            price = fetch_func(symbol)
            if price and price > 0:
                set_cached_price(symbol, price)
                return price
        except Exception as e:
            logger.debug(f"{source_name} failed for {symbol}: {e}")
            continue
    
    logger.warning(f"Could not get current price for {symbol} from any source")
    return None


def validate_entry_price(symbol: str, entry_price: float, max_deviation_pct: float = 30.0) -> tuple:
    """
    Validate if entry price is within acceptable range of current market price.
    
    Returns:
        (is_valid: bool, current_price: Optional[float], deviation_pct: float)
    """
    if not entry_price or entry_price <= 0:
        return False, None, 0.0
    
    current_price = get_current_price(symbol)
    if not current_price:
        # Can't validate, assume valid but log warning
        logger.warning(f"Cannot validate {symbol} - no current price available")
        return True, None, 0.0
    
    deviation_pct = abs(entry_price - current_price) / current_price * 100
    is_valid = deviation_pct <= max_deviation_pct
    
    if not is_valid:
        logger.warning(
            f"Price validation FAILED for {symbol}: "
            f"entry=${entry_price:.2f}, current=${current_price:.2f}, "
            f"deviation={deviation_pct:.1f}% (max {max_deviation_pct}%)"
        )
    else:
        logger.info(
            f"Price validation PASSED for {symbol}: "
            f"entry=${entry_price:.2f}, current=${current_price:.2f}, "
            f"deviation={deviation_pct:.1f}%"
        )
    
    return is_valid, current_price, deviation_pct


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BONK-USD']
    
    print("=== Price Fetcher Test ===")
    for symbol in test_symbols:
        price = get_current_price(symbol)
        if price:
            print(f"{symbol}: ${price:.4f}")
        else:
            print(f"{symbol}: Could not fetch price")
    
    # Test validation
    print("\n=== Validation Test ===")
    test_cases = [
        ('SOLUSDT', 143.46),  # Wrong price
        ('SOLUSDT', 87.0),    # Correct price
        ('BTCUSDT', 83646),   # Recent price
    ]
    
    for symbol, entry in test_cases:
        is_valid, current, deviation = validate_entry_price(symbol, entry)
        status = "PASS" if is_valid else "FAIL"
        print(f"{symbol} @ ${entry}: {status} (current=${current}, deviation={deviation:.1f}%)")
