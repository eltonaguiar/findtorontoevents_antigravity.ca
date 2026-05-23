"""
Multi-Market Data Loader — Fetches OHLCV data across crypto, forex, stocks,
penny stocks, and meme coins using yfinance with error handling and fallbacks.
"""

import sys
import time
import warnings
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf

from . import config

warnings.filterwarnings("ignore", category=FutureWarning)


class MarketDataLoader:
    """
    Fetches and validates OHLCV data for all configured markets.
    Handles missing data, stale tickers, and rate limiting.
    """

    def __init__(self, lookback_days=None, interval=None):
        self.lookback_days = lookback_days or config.LOOKBACK_DAYS
        self.interval = interval or config.DATA_INTERVAL
        self._cache = {}

    def fetch_ticker(self, ticker, force_refresh=False):
        """
        Fetch OHLCV data for a single ticker.

        Returns:
            DataFrame with [Open, High, Low, Close, Volume] or None on failure.
        """
        if ticker in self._cache and not force_refresh:
            return self._cache[ticker]

        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.lookback_days)

        try:
            tk = yf.Ticker(ticker)
            df = tk.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval=self.interval,
            )

            if df is None or df.empty or len(df) < 50:
                print(f"  [WARN] {ticker}: insufficient data ({len(df) if df is not None else 0} rows)")
                return None

            # Validate required columns
            required = ["Open", "High", "Low", "Close", "Volume"]
            for col in required:
                if col not in df.columns:
                    print(f"  [WARN] {ticker}: missing column '{col}'")
                    return None

            # Drop rows with NaN close
            df = df.dropna(subset=["Close"])

            # Fill volume NaN with 0 (some forex pairs have no volume)
            df["Volume"] = df["Volume"].fillna(0)

            if len(df) < 50:
                print(f"  [WARN] {ticker}: only {len(df)} clean rows after filtering")
                return None

            self._cache[ticker] = df
            return df

        except Exception as e:
            print(f"  [ERROR] {ticker}: {e}")
            return None

    def fetch_category(self, category):
        """
        Fetch data for all tickers in a market category.

        Args:
            category: One of "crypto", "meme", "forex", "stocks", "penny"

        Returns:
            Dict of {ticker: DataFrame}
        """
        if category not in config.MARKETS:
            raise ValueError(f"Unknown category: {category}. Choose from {list(config.MARKETS.keys())}")

        tickers = config.MARKETS[category]["tickers"]
        results = {}

        print(f"\n  Fetching {config.MARKETS[category]['label']} ({len(tickers)} tickers)...")

        for ticker in tickers:
            df = self.fetch_ticker(ticker)
            if df is not None:
                results[ticker] = df
                print(f"    {ticker}: {len(df)} bars")
            time.sleep(0.3)  # Rate limit courtesy

        print(f"  → {len(results)}/{len(tickers)} tickers loaded")
        return results

    def fetch_all(self):
        """
        Fetch data for ALL configured markets.

        Returns:
            Dict of {category: {ticker: DataFrame}}
        """
        all_data = {}
        total_loaded = 0
        total_tickers = len(config.ALL_TICKERS)

        print(f"\n{'='*60}")
        print(f"  REGIME TERMINAL DATA LOADER")
        print(f"  Fetching {total_tickers} tickers across {len(config.MARKETS)} markets")
        print(f"  Lookback: {self.lookback_days} days | Interval: {self.interval}")
        print(f"{'='*60}")

        for category in config.MARKETS:
            data = self.fetch_category(category)
            all_data[category] = data
            total_loaded += len(data)

        print(f"\n{'='*60}")
        print(f"  TOTAL: {total_loaded}/{total_tickers} tickers loaded successfully")
        print(f"{'='*60}\n")

        return all_data

    def get_market_summary(self, df):
        """
        Quick summary statistics for a single ticker's data.
        """
        if df is None or df.empty:
            return {}

        close = df["Close"].astype(float)
        return {
            "bars": len(df),
            "start_date": str(df.index[0].date()) if hasattr(df.index[0], "date") else str(df.index[0]),
            "end_date": str(df.index[-1].date()) if hasattr(df.index[-1], "date") else str(df.index[-1]),
            "current_price": round(float(close.iloc[-1]), 4),
            "return_1d": round(float(close.pct_change().iloc[-1] * 100), 2),
            "return_7d": round(float(close.pct_change(7).iloc[-1] * 100), 2) if len(close) > 7 else None,
            "return_30d": round(float(close.pct_change(30).iloc[-1] * 100), 2) if len(close) > 30 else None,
            "return_90d": round(float(close.pct_change(90).iloc[-1] * 100), 2) if len(close) > 90 else None,
            "volatility_30d": round(float(close.pct_change().rolling(30).std().iloc[-1] * 100), 2) if len(close) > 30 else None,
        }
