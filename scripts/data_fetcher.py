#!/usr/bin/env python3
"""
Data Fetcher — yfinance failover wrapper with Finnhub + Yahoo web scrape fallback.

Provides a single function get_price_data(ticker, period) that other scripts can import.
Tries data sources in order:
  1. yfinance (primary, free, reliable)
  2. Finnhub API (free tier, 60 calls/min, env var FINNHUB_API_KEY)
  3. Direct Yahoo Finance chart API (web scrape fallback)

Usage:
    from data_fetcher import get_price_data
    df = get_price_data('AAPL', period='1mo')
    # Returns DataFrame with columns: Date, Open, High, Low, Close, Volume
"""

import os
import sys
import logging
import time
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger('data_fetcher')

# Finnhub API key from environment
FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY', os.environ.get('FINNHUB', ''))

# Custom User-Agent to bypass ModSecurity blocks
HEADERS = {"User-Agent": "WorldClassIntelligence/1.0"}

# Period to days mapping
PERIOD_DAYS = {
    '1d': 1, '5d': 5, '1mo': 30, '3mo': 90, '6mo': 180,
    '1y': 365, '2y': 730, '5y': 1825, 'ytd': None, 'max': 3650
}

# Period to yfinance interval mapping
PERIOD_INTERVAL = {
    '1d': '5m', '5d': '15m', '1mo': '1d', '3mo': '1d',
    '6mo': '1d', '1y': '1d', '2y': '1wk', '5y': '1wk'
}


def _period_to_timestamps(period):
    """Convert period string to (start_timestamp, end_timestamp) for API calls."""
    now = int(time.time())
    days = PERIOD_DAYS.get(period)

    if days is None:
        # ytd
        start_of_year = datetime(datetime.now().year, 1, 1)
        start_ts = int(start_of_year.timestamp())
        return start_ts, now

    start_ts = now - (days * 86400)
    return start_ts, now


def _try_yfinance(ticker, period='1mo'):
    """Primary source: yfinance library."""
    try:
        import yfinance as yf
        data = yf.download(ticker, period=period, progress=False, timeout=15)
        if data is None or data.empty:
            return None

        # Handle MultiIndex columns (newer yfinance returns ('Close', 'TICKER'))
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # Ensure standard column names
        df = data[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df = df.dropna(subset=['Close'])
        df.index.name = 'Date'
        df = df.reset_index()

        if len(df) < 1:
            return None

        logger.debug("yfinance returned %d rows for %s", len(df), ticker)
        return df

    except ImportError:
        logger.warning("yfinance not installed")
        return None
    except Exception as e:
        logger.warning("yfinance failed for %s: %s", ticker, e)
        return None


def _try_finnhub(ticker, period='1mo'):
    """Fallback source: Finnhub API (free tier)."""
    if not FINNHUB_API_KEY:
        logger.debug("Finnhub API key not set, skipping")
        return None

    try:
        import requests

        # Finnhub uses resolution: 1, 5, 15, 30, 60, D, W, M
        resolution = 'D'
        start_ts, end_ts = _period_to_timestamps(period)

        url = 'https://finnhub.io/api/v1/stock/candle'
        params = {
            'symbol': ticker.upper(),
            'resolution': resolution,
            'from': start_ts,
            'to': end_ts,
            'token': FINNHUB_API_KEY
        }

        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get('s') != 'ok' or not data.get('c'):
            logger.debug("Finnhub returned no data for %s", ticker)
            return None

        df = pd.DataFrame({
            'Date': pd.to_datetime(data['t'], unit='s'),
            'Open': data['o'],
            'High': data['h'],
            'Low': data['l'],
            'Close': data['c'],
            'Volume': data['v']
        })

        df = df.dropna(subset=['Close'])
        if len(df) < 1:
            return None

        logger.debug("Finnhub returned %d rows for %s", len(df), ticker)
        return df

    except ImportError:
        logger.warning("requests not installed")
        return None
    except Exception as e:
        logger.warning("Finnhub failed for %s: %s", ticker, e)
        return None


def _try_yahoo_direct(ticker, period='1mo'):
    """Last resort: Direct Yahoo Finance chart API (no yfinance dependency)."""
    try:
        import requests

        # Yahoo Finance v8 chart API
        interval = PERIOD_INTERVAL.get(period, '1d')
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}'
        params = {
            'range': period,
            'interval': interval,
            'includePrePost': 'false'
        }

        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        chart = data.get('chart', {}).get('result', [])
        if not chart:
            logger.debug("Yahoo direct returned no data for %s", ticker)
            return None

        result = chart[0]
        timestamps = result.get('timestamp', [])
        quote = result.get('indicators', {}).get('quote', [{}])[0]

        if not timestamps or not quote.get('close'):
            return None

        df = pd.DataFrame({
            'Date': pd.to_datetime(timestamps, unit='s'),
            'Open': quote.get('open', [None] * len(timestamps)),
            'High': quote.get('high', [None] * len(timestamps)),
            'Low': quote.get('low', [None] * len(timestamps)),
            'Close': quote.get('close', [None] * len(timestamps)),
            'Volume': quote.get('volume', [0] * len(timestamps))
        })

        df = df.dropna(subset=['Close'])
        if len(df) < 1:
            return None

        logger.debug("Yahoo direct returned %d rows for %s", len(df), ticker)
        return df

    except ImportError:
        logger.warning("requests not installed")
        return None
    except Exception as e:
        logger.warning("Yahoo direct failed for %s: %s", ticker, e)
        return None


def get_price_data(ticker, period='1mo'):
    """
    Fetch historical price data with automatic failover.

    Args:
        ticker: Stock/crypto/forex symbol (e.g. 'AAPL', 'BTC-USD')
        period: Time period ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'ytd')

    Returns:
        pandas DataFrame with columns: Date, Open, High, Low, Close, Volume
        Returns None if all sources fail.
    """
    # Source 1: yfinance
    df = _try_yfinance(ticker, period)
    if df is not None and len(df) > 0:
        return df

    logger.info("yfinance failed for %s, trying Finnhub...", ticker)

    # Source 2: Finnhub
    df = _try_finnhub(ticker, period)
    if df is not None and len(df) > 0:
        return df

    logger.info("Finnhub failed for %s, trying Yahoo direct...", ticker)

    # Source 3: Yahoo Finance direct API
    df = _try_yahoo_direct(ticker, period)
    if df is not None and len(df) > 0:
        return df

    logger.error("All data sources failed for %s (period=%s)", ticker, period)
    return None


def get_current_price(ticker):
    """
    Get the most recent closing price for a ticker.

    Returns: float price or None if all sources fail.
    """
    df = get_price_data(ticker, period='5d')
    if df is not None and len(df) > 0:
        price = df['Close'].iloc[-1]
        # Handle potential MultiIndex values
        if hasattr(price, 'values'):
            price = price.values.flatten()[0]
        return float(price)
    return None


def main():
    """Test the data fetcher with sample tickers."""
    test_tickers = ['AAPL', 'MSFT', 'BTC-USD']

    for ticker in test_tickers:
        print(f"\n=== Fetching {ticker} (1mo) ===")
        df = get_price_data(ticker, period='1mo')
        if df is not None:
            print(f"  Rows: {len(df)}")
            print(f"  Latest close: ${df['Close'].iloc[-1]:.2f}")
            print(f"  Date range: {df['Date'].iloc[0]} to {df['Date'].iloc[-1]}")
        else:
            print(f"  FAILED: No data available")

    # Test current price
    print("\n=== Current Prices ===")
    for ticker in test_tickers:
        price = get_current_price(ticker)
        if price:
            print(f"  {ticker}: ${price:.2f}")
        else:
            print(f"  {ticker}: UNAVAILABLE")


if __name__ == '__main__':
    main()
