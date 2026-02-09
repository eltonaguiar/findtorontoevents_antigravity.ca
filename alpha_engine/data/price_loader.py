"""
Price & Volume Data Loader

Fetches and caches OHLCV data from Yahoo Finance with fallbacks.
Handles corporate actions, splits, and dividend adjustments.
"""
import os
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class PriceLoader:
    """Load and cache OHLCV price data for a universe of tickers."""

    def __init__(self, cache_dir: Optional[Path] = None):
        from .. import config
        self.cache_dir = cache_dir or config.DATA_DIR / "prices"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._price_cache: Dict[str, pd.DataFrame] = {}

    def load(
        self,
        tickers: List[str],
        start: str = "2015-01-01",
        end: Optional[str] = None,
        fields: List[str] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        Load OHLCV data for multiple tickers.

        Returns:
            Dict mapping ticker -> DataFrame with columns:
            [Open, High, Low, Close, Adj Close, Volume]
        """
        import yfinance as yf

        if end is None:
            end = datetime.now().strftime("%Y-%m-%d")
        if fields is None:
            fields = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]

        result = {}
        to_download = []

        # Check cache first
        for ticker in tickers:
            cached = self._load_from_cache(ticker, start, end)
            if cached is not None:
                result[ticker] = cached
            else:
                to_download.append(ticker)

        # Download missing tickers in batch
        if to_download:
            logger.info(f"Downloading {len(to_download)} tickers from Yahoo Finance...")
            try:
                data = yf.download(
                    to_download,
                    start=start,
                    end=end,
                    auto_adjust=False,
                    threads=True,
                    progress=False,
                )

                if len(to_download) == 1:
                    # Single ticker returns different structure
                    ticker = to_download[0]
                    if not data.empty:
                        df = data[fields].copy() if all(f in data.columns for f in fields) else data.copy()
                        df.index = pd.to_datetime(df.index)
                        df = df.dropna(how="all")
                        result[ticker] = df
                        self._save_to_cache(ticker, df)
                else:
                    for ticker in to_download:
                        try:
                            if isinstance(data.columns, pd.MultiIndex):
                                df = data.xs(ticker, level=1, axis=1).copy()
                            else:
                                df = data.copy()
                            df = df.dropna(how="all")
                            if not df.empty:
                                df.index = pd.to_datetime(df.index)
                                result[ticker] = df
                                self._save_to_cache(ticker, df)
                        except (KeyError, Exception) as e:
                            logger.warning(f"Failed to load {ticker}: {e}")

            except Exception as e:
                logger.error(f"Batch download failed: {e}")
                # Fallback: download one by one
                for ticker in to_download:
                    try:
                        df = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False)
                        if not df.empty:
                            df.index = pd.to_datetime(df.index)
                            result[ticker] = df
                            self._save_to_cache(ticker, df)
                    except Exception as e2:
                        logger.warning(f"Individual download failed for {ticker}: {e2}")

        self._price_cache.update(result)
        logger.info(f"Loaded price data for {len(result)}/{len(tickers)} tickers")
        return result

    def load_single(self, ticker: str, start: str = "2015-01-01", end: Optional[str] = None) -> pd.DataFrame:
        """Load OHLCV for a single ticker."""
        result = self.load([ticker], start=start, end=end)
        return result.get(ticker, pd.DataFrame())

    def get_close_prices(self, tickers: List[str], start: str = "2015-01-01", end: Optional[str] = None) -> pd.DataFrame:
        """
        Get adjusted close prices as a wide DataFrame (tickers as columns).
        This is the most common format for factor computations.
        """
        data = self.load(tickers, start=start, end=end)
        closes = {}
        for ticker, df in data.items():
            if "Adj Close" in df.columns:
                closes[ticker] = df["Adj Close"]
            elif "Close" in df.columns:
                closes[ticker] = df["Close"]
        return pd.DataFrame(closes)

    def get_volume(self, tickers: List[str], start: str = "2015-01-01", end: Optional[str] = None) -> pd.DataFrame:
        """Get volume as a wide DataFrame."""
        data = self.load(tickers, start=start, end=end)
        volumes = {t: df["Volume"] for t, df in data.items() if "Volume" in df.columns}
        return pd.DataFrame(volumes)

    def get_ohlcv_panel(self, tickers: List[str], start: str = "2015-01-01", end: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Get full OHLCV as dict of wide DataFrames.
        Returns: {'Open': df, 'High': df, 'Low': df, 'Close': df, 'Volume': df}
        """
        data = self.load(tickers, start=start, end=end)
        fields = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
        panel = {}
        for field in fields:
            series = {}
            for t, df in data.items():
                if field in df.columns:
                    series[t] = df[field]
            panel[field] = pd.DataFrame(series)
        return panel

    def _cache_path(self, ticker: str) -> Path:
        return self.cache_dir / f"{ticker.replace('^', '_').replace('=', '_')}.parquet"

    def _load_from_cache(self, ticker: str, start: str, end: str) -> Optional[pd.DataFrame]:
        """Load from local cache if fresh enough (< 1 day old)."""
        path = self._cache_path(ticker)
        if not path.exists():
            return None

        # Check staleness
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        if (datetime.now() - mtime).total_seconds() > 86400:  # 24 hours
            return None

        try:
            df = pd.read_parquet(path)
            df.index = pd.to_datetime(df.index)
            mask = (df.index >= start) & (df.index <= end)
            return df.loc[mask]
        except Exception:
            return None

    def _save_to_cache(self, ticker: str, df: pd.DataFrame):
        """Save to local parquet cache."""
        try:
            path = self._cache_path(ticker)
            df.to_parquet(path)
        except Exception as e:
            logger.warning(f"Cache save failed for {ticker}: {e}")

    def get_dollar_volume(self, tickers: List[str], start: str = "2015-01-01", end: Optional[str] = None) -> pd.DataFrame:
        """Get dollar volume (Close * Volume) for liquidity analysis."""
        data = self.load(tickers, start=start, end=end)
        dvol = {}
        for t, df in data.items():
            if "Close" in df.columns and "Volume" in df.columns:
                dvol[t] = df["Close"] * df["Volume"]
        return pd.DataFrame(dvol)

    def get_returns(self, tickers: List[str], start: str = "2015-01-01", end: Optional[str] = None, periods: int = 1) -> pd.DataFrame:
        """Get N-period returns."""
        closes = self.get_close_prices(tickers, start=start, end=end)
        return closes.pct_change(periods)

    def data_quality_report(self, tickers: List[str], start: str = "2015-01-01") -> pd.DataFrame:
        """Generate data quality report: missing %, date range, staleness."""
        data = self.load(tickers, start=start)
        rows = []
        for t, df in data.items():
            rows.append({
                "ticker": t,
                "start_date": df.index.min(),
                "end_date": df.index.max(),
                "total_bars": len(df),
                "missing_pct": df.isnull().mean().mean() * 100,
                "zero_volume_pct": (df.get("Volume", pd.Series([1])) == 0).mean() * 100,
            })
        return pd.DataFrame(rows).set_index("ticker")
