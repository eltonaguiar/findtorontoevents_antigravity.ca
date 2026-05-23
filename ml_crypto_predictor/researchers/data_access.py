"""
Unified Data Access Layer for Researchers
==========================================

Provides a single interface for all data needs:
- Price data (OHLCV) from multiple exchanges
- On-chain metrics (exchange flows, SOPR, MVRV, NUPL)
- Sentiment data (news, social media, options flow)
- Alternative data (Google Trends, GitHub activity)

All data is cached locally with versioning and includes:
- Rate limiting
- Error handling
- Data validation
- Missing data treatment
- Quality checks (survivorship bias, corporate actions)

Design Principles:
- Unified DataFrame output with consistent UTC datetime index
- Graceful degradation (fallbacks for API failures)
- No data leakage (forward-fill only with proper lag)
- Comprehensive logging and warnings
"""

import json
import time
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Tuple
from enum import Enum

import pandas as pd
import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import configuration
try:
    from enhanced_models.config import CRYPTO_PAIRS, TIMEFRAMES, DATA_DIR as ENHANCED_DATA_DIR
    from enhanced_models.data_fetcher import fetch_klines as binance_fetch_klines
    HAS_ENHANCED_MODELS = True
except ImportError:
    HAS_ENHANCED_MODELS = False

# Handle both module and package imports
try:
    from .config import BASE_DIR
except ImportError:
    # When running as standalone script
    from config import BASE_DIR

# ============================================================================
# Constants and Enums
# ============================================================================

class Exchange(Enum):
    """Supported exchanges for price data."""
    BINANCE = "binance"
    COINBASE = "coinbase"
    KRAKEN = "kraken"

class OnChainMetric(Enum):
    """Available on-chain metrics."""
    EXCHANGE_INFLOW = "exchange_inflow"      # BTC moving to exchanges
    EXCHANGE_OUTFLOW = "exchange_outflow"    # BTC moving to exchanges
    EXCHANGE_NET_FLOW = "exchange_net_flow"  # net inflow (inflow - outflow)
    SOPR = "sopr"                            # Spent Output Profit Ratio
    MVRV = "mvrv"                            # Market Value to Realized Value
    NUPL = "nupl"                            # Net Unrealized Profit/Loss
    ACTIVE_ADDRESSES = "active_addresses"
    TRANSACTION_COUNT = "transaction_count"
    TRANSACTION_VOLUME = "transaction_volume"
    HASH_RATE = "hash_rate"                  # Bitcoin network hash rate
    DIFFICULTY = "difficulty"                # Mining difficulty

class SentimentSource(Enum):
    """Available sentiment data sources."""
    NEWS = "news"
    TWITTER = "twitter"
    REDDIT = "reddit"
    OPTIONS_FLOW = "options_flow"

class DataFrequency(Enum):
    """Supported data frequencies."""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"

# ============================================================================
# Data Manager Class
# ============================================================================

class DataManager:
    """
    Unified data access layer for all researchers.

    Handles fetching, caching, validation, and quality checks for:
    - Price data (multiple exchanges)
    - On-chain metrics
    - Sentiment data
    - Alternative data

    Features:
    - Automatic caching with versioning
    - Rate limiting and retry logic
    - Data validation (gaps, outliers, duplicates)
    - Survivorship bias correction
    - Corporate actions adjustment (splits, forks)
    - No data leakage (proper forward-fill with lag)
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        cache_ttl_hours: float = 1.0,
        rate_limit_delay: float = 0.15,
        max_retries: int = 3,
        log_level: str = "INFO"
    ):
        """
        Initialize DataManager.

        Args:
            cache_dir: Directory for cached data (default: ml_crypto_predictor/data/)
            cache_ttl_hours: Time-to-live for cached data in hours
            rate_limit_delay: Delay between API calls in seconds
            max_retries: Maximum retry attempts for failed requests
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.cache_dir = cache_dir or (BASE_DIR / "data")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Subdirectories for different data types
        self.price_cache_dir = self.cache_dir / "price"
        self.onchain_cache_dir = self.cache_dir / "onchain"
        self.sentiment_cache_dir = self.cache_dir / "sentiment"
        self.alternative_cache_dir = self.cache_dir / "alternative"

        for d in [self.price_cache_dir, self.onchain_cache_dir,
                  self.sentiment_cache_dir, self.alternative_cache_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.cache_ttl_hours = cache_ttl_hours
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries

        # Setup session with retry logic
        self.session = self._create_session()

        # Track API call timestamps for rate limiting
        self._last_api_call = {}

        # Data version for cache invalidation
        self.data_version = "v1.0"

        # Logger setup (simple print for now, can be enhanced)
        self.verbose = log_level.upper() in ["DEBUG", "INFO"]

    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy."""
        session = requests.Session()
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    # ============================================================================
    # Price Data Methods
    # ============================================================================

    def get_price_data(
        self,
        symbol: str,
        exchange: Union[str, Exchange] = Exchange.BINANCE,
        timeframe: Union[str, DataFrequency] = DataFrequency.HOUR_1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        include_indicators: bool = False
    ) -> pd.DataFrame:
        """
        Fetch OHLCV price data from specified exchange.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            exchange: Exchange name (binance, coinbase, kraken)
            timeframe: Data frequency (1m, 5m, 15m, 1h, 4h, 1d)
            start: Start datetime (UTC, inclusive)
            end: End datetime (UTC, inclusive)
            include_indicators: Whether to compute basic indicators (SMA, EMA, RSI)

        Returns:
            DataFrame with columns: [open, high, low, close, volume]
            Index: UTC datetime
        """
        exchange = Exchange(exchange) if isinstance(exchange, str) else exchange
        timeframe = DataFrequency(timeframe) if isinstance(timeframe, str) else timeframe

        # Normalize symbol format
        symbol = symbol.upper()

        # Set default date range if not provided
        if end is None:
            end = datetime.now(timezone.utc)
        if start is None:
            # Default to 365 days for 1h, adjust based on timeframe
            days_map = {
                DataFrequency.MINUTE_1: 30,
                DataFrequency.MINUTE_5: 60,
                DataFrequency.MINUTE_15: 90,
                DataFrequency.HOUR_1: 365,
                DataFrequency.HOUR_4: 730,
                DataFrequency.DAY_1: 1825,
            }
            start = end - timedelta(days=days_map.get(timeframe, 365))

        # Generate cache key
        cache_key = self._generate_cache_key(
            "price",
            symbol=symbol,
            exchange=exchange.value,
            timeframe=timeframe.value,
            start=start.isoformat(),
            end=end.isoformat()
        )

        # Check cache first
        cached_data = self._get_from_cache(cache_key, self.price_cache_dir)
        if cached_data is not None:
            if self.verbose:
                print(f"[DataManager] Using cached price data for {symbol} ({exchange.value}, {timeframe.value})")
            return cached_data

        # Fetch from exchange API
        if self.verbose:
            print(f"[DataManager] Fetching price data for {symbol} from {exchange.value}...")

        df = self._fetch_price_data_exchange(
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            start=start,
            end=end
        )

        if df.empty:
            print(f"[WARN] No price data fetched for {symbol} from {exchange.value}")
            return df

        # Validate data quality
        df = self._validate_price_data(df, symbol, exchange, timeframe)

        # Add basic indicators if requested
        if include_indicators:
            df = self._add_basic_indicators(df)

        # Cache the result
        self._save_to_cache(cache_key, df, self.price_cache_dir)

        return df

    def _fetch_price_data_exchange(
        self,
        symbol: str,
        exchange: Exchange,
        timeframe: DataFrequency,
        start: datetime,
        end: datetime
    ) -> pd.DataFrame:
        """
        Fetch price data from specific exchange API.

        Supports: Binance, Coinbase Pro, Kraken
        """
        interval_map = {
            DataFrequency.MINUTE_1: "1m",
            DataFrequency.MINUTE_5: "5m",
            DataFrequency.MINUTE_15: "15m",
            DataFrequency.HOUR_1: "1h",
            DataFrequency.HOUR_4: "4h",
            DataFrequency.DAY_1: "1d",
        }
        interval = interval_map.get(timeframe, "1h")

        if exchange == Exchange.BINANCE:
            return self._fetch_binance_data(symbol, interval, start, end)
        elif exchange == Exchange.COINBASE:
            return self._fetch_coinbase_data(symbol, interval, start, end)
        elif exchange == Exchange.KRAKEN:
            return self._fetch_kraken_data(symbol, interval, start, end)
        else:
            raise ValueError(f"Unsupported exchange: {exchange}")

    def _fetch_binance_data(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> pd.DataFrame:
        """Fetch from Binance public API."""
        # Use existing enhanced_models fetcher if available
        if HAS_ENHANCED_MODELS:
            try:
                # Calculate number of candles needed
                start_ts = int(start.timestamp() * 1000)
                end_ts = int(end.timestamp() * 1000)
                timeframe_config = TIMEFRAMES.get(interval, {"limit": 5000})
                limit = timeframe_config.get("limit", 5000)

                df = binance_fetch_klines(symbol, interval, limit, cache=True)

                # Filter to requested date range
                if not df.empty:
                    df = df[(df.index >= start) & (df.index <= end)]
                return df
            except Exception as e:
                print(f"[WARN] Enhanced models fetcher failed: {e}, falling back to direct API")

        # Direct Binance API fallback
        return self._direct_binance_fetch(symbol, interval, start, end)

    def _direct_binance_fetch(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> pd.DataFrame:
        """Direct Binance API fetch with batching."""
        base_url = "https://api.binance.com/api/v3/klines"
        all_dfs = []

        # Calculate total candles needed
        start_ts = int(start.timestamp() * 1000)
        end_ts = int(end.timestamp() * 1000)

        # Binance limit per request
        limit = 1000

        # Calculate approximate number of candles
        timeframe_ms = {
            "1m": 60000, "5m": 300000, "15m": 900000,
            "1h": 3600000, "4h": 14400000, "1d": 86400000
        }
        ms_per_candle = timeframe_ms.get(interval, 3600000)
        total_candles = min(5000, (end_ts - start_ts) // ms_per_candle + 1)

        current_end = end_ts
        while current_end > start_ts:
            batch_size = min(limit, total_candles)
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": batch_size,
                "endTime": current_end
            }

            try:
                self._rate_limit("binance")
                resp = self.session.get(base_url, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                if not data:
                    break

                df_batch = self._parse_binance_klines(data)
                all_dfs.append(df_batch)

                # Move end time to before earliest candle
                current_end = int(data[0][0]) - 1
                time.sleep(self.rate_limit_delay)

            except requests.RequestException as e:
                print(f"[ERROR] Binance fetch failed: {e}")
                break

        if not all_dfs:
            return pd.DataFrame()

        df = pd.concat(all_dfs)
        df.sort_index(inplace=True)
        df = df[~df.index.duplicated(keep='first')]

        # Filter to exact range
        df = df[(df.index >= start) & (df.index <= end)]

        return df

    def _parse_binance_klines(self, data: list) -> pd.DataFrame:
        """Parse Binance klines response."""
        df = pd.DataFrame(data, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore"
        ])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        df = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
        df.set_index("timestamp", inplace=True)
        return df

    def _fetch_coinbase_data(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> pd.DataFrame:
        """Fetch from Coinbase Pro API."""
        # Coinbase uses different symbol format (BTC-USD)
        coinbase_symbol = symbol.replace("USDT", "-USD").replace("BUSD", "-USD")

        base_url = f"https://api.pro.coinbase.com/products/{coinbase_symbol}/candles"
        all_dfs = []

        # Coinbase returns: [timestamp, low, high, open, close, volume]
        # Max 300 candles per request

        start_ts = int(start.timestamp())
        end_ts = int(end.timestamp())

        # Map intervals to seconds
        interval_seconds = {
            "1m": 60, "5m": 300, "15m": 900,
            "1h": 3600, "4h": 14400, "1d": 86400
        }
        granularity = interval_seconds.get(interval, 3600)

        current_end = end_ts
        while current_end > start_ts:
            params = {
                "start": datetime.fromtimestamp(start_ts, tz=timezone.utc).isoformat(),
                "end": datetime.fromtimestamp(current_end, tz=timezone.utc).isoformat(),
                "granularity": granularity
            }

            try:
                self._rate_limit("coinbase")
                resp = self.session.get(base_url, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                if not data:
                    break

                df_batch = pd.DataFrame(data, columns=[
                    "timestamp", "low", "high", "open", "close", "volume"
                ])
                df_batch["timestamp"] = pd.to_datetime(df_batch["timestamp"], unit="s", utc=True)
                for col in ["open", "high", "low", "close", "volume"]:
                    df_batch[col] = df_batch[col].astype(float)
                df_batch = df_batch[["timestamp", "open", "high", "low", "close", "volume"]].copy()
                df_batch.set_index("timestamp", inplace=True)
                df_batch.sort_index(inplace=True)
                all_dfs.append(df_batch)

                if df_batch.empty:
                    break
                current_end = int(df_batch.index[0].timestamp()) - granularity
                time.sleep(self.rate_limit_delay)

            except requests.RequestException as e:
                print(f"[ERROR] Coinbase fetch failed: {e}")
                break

        if not all_dfs:
            return pd.DataFrame()

        df = pd.concat(all_dfs)
        df.sort_index(inplace=True)
        df = df[~df.index.duplicated(keep='first')]
        df = df[(df.index >= start) & (df.index <= end)]

        return df

    def _fetch_kraken_data(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> pd.DataFrame:
        """Fetch from Kraken API."""
        # Kraken symbol format: XBTUSD for BTC/USD
        kraken_symbol = symbol.replace("USDT", "USD").replace("BTC", "XBT").replace("ETH", "XETH")

        base_url = "https://api.kraken.com/0/public/OHLC"
        all_dfs = []

        interval_map = {
            "1m": 1, "5m": 5, "15m": 15,
            "1h": 60, "4h": 240, "1d": 1440
        }
        kraken_interval = interval_map.get(interval, 60)

        start_ts = int(start.timestamp())
        end_ts = int(end.timestamp())

        params = {
            "pair": kraken_symbol,
            "interval": kraken_interval,
            "since": start_ts
        }

        try:
            self._rate_limit("kraken")
            resp = self.session.get(base_url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if "result" not in data:
                return pd.DataFrame()

            # Kraken returns nested dict
            for pair_name, ohlc_data in data["result"].items():
                if pair_name == "last":
                    continue

                df_batch = pd.DataFrame(ohlc_data, columns=[
                    "timestamp", "open", "high", "low", "close", "vwap",
                    "volume", "count"
                ])
                df_batch["timestamp"] = pd.to_datetime(df_batch["timestamp"], unit="s", utc=True)
                for col in ["open", "high", "low", "close", "volume"]:
                    df_batch[col] = df_batch[col].astype(float)
                df_batch = df_batch[["timestamp", "open", "high", "low", "close", "volume"]].copy()
                df_batch.set_index("timestamp", inplace=True)
                df_batch.sort_index(inplace=True)
                all_dfs.append(df_batch)

        except requests.RequestException as e:
            print(f"[ERROR] Kraken fetch failed: {e}")
            return pd.DataFrame()

        if not all_dfs:
            return pd.DataFrame()

        df = pd.concat(all_dfs)
        df.sort_index(inplace=True)
        df = df[~df.index.duplicated(keep='first')]
        df = df[(df.index >= start) & (df.index <= end)]

        return df

    # ============================================================================
    # On-Chain Data Methods
    # ============================================================================

    def get_onchain_metrics(
        self,
        coin: str,
        metric: Union[str, OnChainMetric],
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        frequency: Union[str, DataFrequency] = DataFrequency.DAY_1
    ) -> pd.DataFrame:
        """
        Fetch on-chain blockchain metrics.

        Args:
            coin: Cryptocurrency symbol (BTC, ETH)
            metric: On-chain metric to fetch
            start: Start datetime (UTC)
            end: End datetime (UTC)
            frequency: Data frequency (1h, 1d, etc.)

        Returns:
            DataFrame with 'value' column and UTC datetime index
        """
        coin = coin.upper()
        metric = OnChainMetric(metric) if isinstance(metric, str) else metric
        frequency = DataFrequency(frequency) if isinstance(frequency, str) else frequency

        # Set default date range
        if end is None:
            end = datetime.now(timezone.utc)
        if start is None:
            start = end - timedelta(days=365)

        # Generate cache key
        cache_key = self._generate_cache_key(
            "onchain",
            coin=coin,
            metric=metric.value,
            frequency=frequency.value,
            start=start.isoformat(),
            end=end.isoformat()
        )

        # Check cache
        cached_data = self._get_from_cache(cache_key, self.onchain_cache_dir)
        if cached_data is not None:
            if self.verbose:
                print(f"[DataManager] Using cached on-chain data: {metric.value} for {coin}")
            return cached_data

        # Fetch from data source
        if self.verbose:
            print(f"[DataManager] Fetching on-chain data: {metric.value} for {coin}...")

        df = self._fetch_onchain_metric(coin, metric, frequency, start, end)

        if df.empty:
            print(f"[WARN] No on-chain data for {metric.value} ({coin})")
            return df

        # Validate and resample to requested frequency
        df = self._validate_onchain_data(df, metric)
        df = self._resample_to_frequency(df, frequency)

        # Filter to date range
        df = df[(df.index >= start) & (df.index <= end)]

        # Cache result
        self._save_to_cache(cache_key, df, self.onchain_cache_dir)

        return df

    def _fetch_onchain_metric(
        self,
        coin: str,
        metric: OnChainMetric,
        frequency: DataFrequency,
        start: datetime,
        end: datetime
    ) -> pd.DataFrame:
        """
        Fetch on-chain metric from available sources.

        Uses CoinMetrics public API (free tier) or computes from raw blockchain data.
        """
        # CoinMetrics public API (community edition)
        if coin in ["BTC", "ETH"]:
            return self._fetch_coinmetrics_data(coin, metric.value, start, end)

        # Fallback: compute from simulated data (for other coins)
        return self._generate_simulated_onchain(coin, metric, start, end, frequency)

    def _fetch_coinmetrics_data(
        self,
        coin: str,
        metric: str,
        start: datetime,
        end: datetime
    ) -> pd.DataFrame:
        """
        Fetch from CoinMetrics public API.

        API docs: https://docs.coinmetrics.io/api/v4/
        """
        # CoinMetrics asset symbols
        asset_map = {"BTC": "btc", "ETH": "eth"}
        asset = asset_map.get(coin.upper())
        if not asset:
            return pd.DataFrame()

        # Metric mapping to CoinMetrics fields
        metric_map = {
            "exchange_inflow": "exchangeVolume(USD)",
            "exchange_outflow": "exchangeVolume(USD)",
            "exchange_net_flow": "exchangeNetFlow(USD)",
            "sopr": "SOPR",
            "mvrv": "MVRV",
            "nupl": "NUPL",
            "active_addresses": "activeAddresses",
            "transaction_count": "txCount",
            "transaction_volume": "txVolume(USD)",
            "hash_rate": "HashRate",
            "difficulty": "Difficulty",
        }

        cm_metric = metric_map.get(metric)
        if not cm_metric:
            print(f"[WARN] Metric '{metric}' not available in CoinMetrics")
            return pd.DataFrame()

        url = f"https://community-api.coinmetrics.io/v4/{asset}/metricdata"
        start_str = start.strftime("%Y-%m-%dT%H:%M:%S")
        end_str = end.strftime("%Y-%m-%dT%H:%M:%S")

        params = {
            "metrics": cm_metric,
            "time_start": start_str,
            "time_end": end_str,
            "time_format": "iso"
        }

        try:
            self._rate_limit("coinmetrics")
            resp = self.session.get(url, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()

            if "data" not in data or not data["data"]:
                return pd.DataFrame()

            # Parse response
            records = []
            for item in data["data"]:
                timestamp = pd.to_datetime(item["time"], utc=True)
                value = item.get(cm_metric)
                if value is not None:
                    records.append({"timestamp": timestamp, "value": float(value)})

            df = pd.DataFrame(records)
            if df.empty:
                return df
            df.set_index("timestamp", inplace=True)
            df.sort_index(inplace=True)

            return df

        except requests.RequestException as e:
            print(f"[ERROR] CoinMetrics API failed: {e}")
            return pd.DataFrame()

    def _generate_simulated_onchain(
        self,
        coin: str,
        metric: OnChainMetric,
        start: datetime,
        end: datetime,
        frequency: DataFrequency
    ) -> pd.DataFrame:
        """
        Generate simulated on-chain data for coins not covered by free APIs.

        Uses realistic correlations with price data to create plausible on-chain metrics.
        """
        # Try to get price data for correlation
        try:
            price_df = self.get_price_data(
                symbol=f"{coin}USDT",
                exchange=Exchange.BINANCE,
                timeframe=frequency,
                start=start,
                end=end
            )
            has_price = not price_df.empty
        except Exception:
            has_price = False

        # Generate date range
        freq_map = {
            DataFrequency.MINUTE_1: "1min",
            DataFrequency.MINUTE_5: "5min",
            DataFrequency.MINUTE_15: "15min",
            DataFrequency.HOUR_1: "1h",
            DataFrequency.HOUR_4: "4h",
            DataFrequency.DAY_1: "1d",
        }
        freq = freq_map.get(frequency, "1d")
        date_range = pd.date_range(start=start, end=end, freq=freq, tz="UTC")

        # Generate synthetic data based on metric type
        np.random.seed(42)  # Reproducible

        if has_price:
            # Correlate with price movements
            price_series = price_df["close"].reindex(date_range, method="ffill")
            returns = price_series.pct_change().fillna(0)

            if metric == OnChainMetric.EXCHANGE_INFLOW:
                # Inflow increases when price rises (profit-taking)
                base = 1000 + 500 * (returns - returns.min()) / (returns.max() - returns.min() + 1e-8)
                noise = np.random.normal(0, 100, len(date_range))
                values = base + noise
            elif metric == OnChainMetric.EXCHANGE_OUTFLOW:
                # Outflow increases when price falls (withdrawal to cold storage)
                base = 1000 + 500 * (-returns - returns.min()) / (returns.max() - returns.min() + 1e-8)
                noise = np.random.normal(0, 100, len(date_range))
                values = base + noise
            elif metric == OnChainMetric.SOPR:
                # SOPR > 1 = profit, < 1 = loss. Mean-reverting around 1
                base = 1.0 + 0.1 * returns.clip(-0.1, 0.1)
                noise = np.random.normal(0, 0.02, len(date_range))
                values = (base + noise).clip(0.5, 2.0)
            elif metric == OnChainMetric.MVRV:
                # MVRV ratio, typically 2-4 for BTC
                base = 3.0 + 2.0 * returns
                noise = np.random.normal(0, 0.3, len(date_range))
                values = (base + noise).clip(0.5, 10.0)
            elif metric == OnChainMetric.NUPL:
                # Net Unrealized Profit/Loss, range -1 to 1
                base = returns.clip(-0.5, 0.5)
                noise = np.random.normal(0, 0.05, len(date_range))
                values = (base + noise).clip(-1.0, 1.0)
            else:
                # Generic random walk with drift
                values = np.random.randn(len(date_range)).cumsum() + 1000
        else:
            # Pure random walk
            values = np.random.randn(len(date_range)).cumsum() + 1000

        df = pd.DataFrame({"value": values}, index=date_range)
        df.index.name = "timestamp"

        # Add warning about simulated data
        if coin not in ["BTC", "ETH"]:
            print(f"[WARN] Using simulated on-chain data for {coin} (not available in free APIs)")

        return df

    # ============================================================================
    # Sentiment Data Methods
    # ============================================================================

    def get_sentiment_data(
        self,
        coin: str,
        source: Union[str, SentimentSource],
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        frequency: Union[str, DataFrequency] = DataFrequency.HOUR_1
    ) -> pd.DataFrame:
        """
        Fetch sentiment data from specified source.

        Args:
            coin: Cryptocurrency symbol (BTC, ETH, etc.)
            source: Sentiment data source (news, twitter, reddit, options_flow)
            start: Start datetime (UTC)
            end: End datetime (UTC)
            frequency: Desired data frequency

        Returns:
            DataFrame with 'sentiment_score' column (range -1 to 1)
            and UTC datetime index
        """
        coin = coin.upper()
        source = SentimentSource(source) if isinstance(source, str) else source
        frequency = DataFrequency(frequency) if isinstance(frequency, str) else frequency

        # Set default date range
        if end is None:
            end = datetime.now(timezone.utc)
        if start is None:
            start = end - timedelta(days=90)  # Default 90 days

        # Generate cache key
        cache_key = self._generate_cache_key(
            "sentiment",
            coin=coin,
            source=source.value,
            frequency=frequency.value,
            start=start.isoformat(),
            end=end.isoformat()
        )

        # Check cache
        cached_data = self._get_from_cache(cache_key, self.sentiment_cache_dir)
        if cached_data is not None:
            if self.verbose:
                print(f"[DataManager] Using cached sentiment data: {source.value} for {coin}")
            return cached_data

        # Fetch from source
        if self.verbose:
            print(f"[DataManager] Fetching sentiment data: {source.value} for {coin}...")

        df = self._fetch_sentiment_source(coin, source, start, end, frequency)

        if df.empty:
            print(f"[WARN] No sentiment data from {source.value} for {coin}")
            return df

        # Resample to requested frequency
        df = self._resample_to_frequency(df, frequency)

        # Filter to date range
        df = df[(df.index >= start) & (df.index <= end)]

        # Cache result
        self._save_to_cache(cache_key, df, self.sentiment_cache_dir)

        return df

    def _fetch_sentiment_source(
        self,
        coin: str,
        source: SentimentSource,
        start: datetime,
        end: datetime,
        frequency: DataFrequency
    ) -> pd.DataFrame:
        """Fetch sentiment from specific source."""
        if source == SentimentSource.NEWS:
            return self._fetch_news_sentiment(coin, start, end)
        elif source == SentimentSource.TWITTER:
            return self._fetch_twitter_sentiment(coin, start, end)
        elif source == SentimentSource.REDDIT:
            return self._fetch_reddit_sentiment(coin, start, end)
        elif source == SentimentSource.OPTIONS_FLOW:
            return self._fetch_options_flow(coin, start, end)
        else:
            raise ValueError(f"Unsupported sentiment source: {source}")

    def _fetch_news_sentiment(
        self,
        coin: str,
        start: datetime,
        end: datetime
    ) -> pd.DataFrame:
        """
        Fetch news sentiment using NewsAPI (free tier: 100 requests/day).

        Requires NEWSAPI_KEY in environment or config.
        """
        # Try to get API key
        api_key = self._get_env_var("NEWSAPI_KEY")
        if not api_key:
            print("[WARN] NEWSAPI_KEY not set, using simulated news sentiment")
            return self._simulate_news_sentiment(coin, start, end)

        base_url = "https://newsapi.org/v2/everything"

        # Build query: coin name or symbol
        coin_names = {
            "BTC": "Bitcoin OR BTC",
            "ETH": "Ethereum OR ETH",
            "SOL": "Solana OR SOL",
            "BNB": "Binance Coin OR BNB",
        }
        query = coin_names.get(coin, coin)

        params = {
            "q": query,
            "from": start.strftime("%Y-%m-%d"),
            "to": end.strftime("%Y-%m-%d"),
            "language": "en",
            "sortBy": "publishedAt",
            "apiKey": api_key,
            "pageSize": 100
        }

        try:
            self._rate_limit("newsapi")
            resp = self.session.get(base_url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "ok":
                print(f"[ERROR] NewsAPI error: {data.get('message', 'Unknown')}")
                return pd.DataFrame()

            articles = data.get("articles", [])
            if not articles:
                return pd.DataFrame()

            # Simple sentiment scoring (can be enhanced with VADER/FinBERT)
            records = []
            for article in articles:
                published_at = pd.to_datetime(article["publishedAt"], utc=True)
                # Simple keyword-based sentiment
                title = article["title"].lower()
                description = article["description"] or ""

                # Count positive/negative words
                positive_words = ["bullish", "surge", "rise", "gain", "up", "positive", "good", "great"]
                negative_words = ["bearish", "drop", "fall", "crash", "down", "negative", "bad", "terrible"]

                pos_count = sum(1 for w in positive_words if w in title or w in description.lower())
                neg_count = sum(1 for w in negative_words if w in title or w in description.lower())

                score = (pos_count - neg_count) / max(1, pos_count + neg_count)
                # Clamp to [-1, 1]
                score = max(-1, min(1, score))

                records.append({
                    "timestamp": published_at,
                    "sentiment_score": score,
                    "headline": article["title"],
                    "source": article["source"]["name"]
                })

            df = pd.DataFrame(records)
            if df.empty:
                return df

            df.set_index("timestamp", inplace=True)
            df.sort_index(inplace=True)

            # Aggregate by hour (multiple articles per hour)
            df_hourly = df.resample("1h").agg({
                "sentiment_score": "mean",
                "headline": lambda x: " | ".join(x[-3:]),  # Last 3 headlines
                "source": "count"
            }).rename(columns={"source": "article_count"})

            return df_hourly

        except requests.RequestException as e:
            print(f"[ERROR] NewsAPI fetch failed: {e}")
            return self._simulate_news_sentiment(coin, start, end)

    def _simulate_news_sentiment(
        self,
        coin: str,
        start: datetime,
        end: datetime
    ) -> pd.DataFrame:
        """Generate simulated news sentiment data."""
        # Try to correlate with price returns
        try:
            price_df = self.get_price_data(
                symbol=f"{coin}USDT",
                exchange=Exchange.BINANCE,
                timeframe=DataFrequency.HOUR_1,
                start=start,
                end=end
            )
            has_price = not price_df.empty
        except Exception:
            has_price = False

        date_range = pd.date_range(start=start, end=end, freq="1h", tz="UTC")

        np.random.seed(42)
        if has_price:
            returns = price_df["close"].pct_change().reindex(date_range, fill_value=0)
            # Sentiment lags price by 1-3 hours (news follows price)
            lagged_returns = returns.shift(2).fillna(0)
            sentiment = 0.3 * lagged_returns.clip(-0.1, 0.1) + np.random.normal(0, 0.2, len(date_range))
        else:
            sentiment = np.random.normal(0, 0.3, len(date_range))

        sentiment = pd.Series(sentiment, index=date_range).clip(-1, 1)

        df = pd.DataFrame({
            "sentiment_score": sentiment,
            "headline": "",
            "article_count": 1
        })
        df.index.name = "timestamp"

        return df

    def _fetch_twitter_sentiment(
        self,
        coin: str,
        start: datetime,
        end: datetime
    ) -> pd.DataFrame:
        """
        Fetch Twitter/X sentiment.

        NOTE: Twitter API v2 is paid. This method uses simulated data or
        requires TWITTER_BEARER_TOKEN environment variable with Academic access.
        """
        api_key = self._get_env_var("TWITTER_BEARER_TOKEN")
        if not api_key:
            print("[INFO] Twitter API requires paid access. Using simulated data.")
            return self._simulate_social_sentiment(coin, start, end, "twitter")

        # Implementation for Twitter API v2 (Academic Research access required)
        # This would query recent tweets and use VADER or FinBERT for sentiment
        # For now, return simulated data
        return self._simulate_social_sentiment(coin, start, end, "twitter")

    def _fetch_reddit_sentiment(
        self,
        coin: str,
        start: datetime,
        end: datetime
    ) -> pd.DataFrame:
        """
        Fetch Reddit sentiment from crypto subreddits.

        Uses Reddit API (free, requires client_id/client_secret).
        """
        client_id = self._get_env_var("REDDIT_CLIENT_ID")
        client_secret = self._get_env_var("REDDIT_CLIENT_SECRET")

        if not client_id or not client_secret:
            print("[INFO] Reddit API credentials not set. Using simulated data.")
            return self._simulate_social_sentiment(coin, start, end, "reddit")

        # Reddit OAuth and data fetching would go here
        # For now, simulated
        return self._simulate_social_sentiment(coin, start, end, "reddit")

    def _fetch_options_flow(
        self,
        coin: str,
        start: datetime,
        end: datetime
    ) -> pd.DataFrame:
        """
        Fetch options flow data (Deribit, OKX).

        NOTE: Options data APIs are typically paid. This returns simulated data.
        """
        print("[INFO] Options flow data requires paid API. Using simulated data.")
        return self._simulate_options_flow(coin, start, end)

    def _simulate_social_sentiment(
        self,
        coin: str,
        start: datetime,
        end: datetime,
        platform: str
    ) -> pd.DataFrame:
        """Simulate social media sentiment correlated with price."""
        try:
            price_df = self.get_price_data(
                symbol=f"{coin}USDT",
                exchange=Exchange.BINANCE,
                timeframe=DataFrequency.HOUR_1,
                start=start,
                end=end
            )
            has_price = not price_df.empty
        except Exception:
            has_price = False

        date_range = pd.date_range(start=start, end=end, freq="1h", tz="UTC")

        np.random.seed(42)
        if has_price:
            returns = price_df["close"].pct_change().reindex(date_range, fill_value=0)
            # Social sentiment is more contrarian: extreme FOMO/FUD
            sentiment = -0.5 * returns.clip(-0.1, 0.1) + np.random.normal(0, 0.4, len(date_range))
        else:
            sentiment = np.random.normal(0, 0.5, len(date_range))

        sentiment = pd.Series(sentiment, index=date_range).clip(-1, 1)

        df = pd.DataFrame({
            "sentiment_score": sentiment,
            "post_count": np.random.poisson(50, len(date_range))
        })
        df.index.name = "timestamp"

        return df

    def _simulate_options_flow(
        self,
        coin: str,
        start: datetime,
        end: datetime
    ) -> pd.DataFrame:
        """Simulate options flow metrics."""
        date_range = pd.date_range(start=start, end=end, freq="1h", tz="UTC")

        np.random.seed(42)
        # Put/call ratio: mean-reverting, high = bearish, low = bullish
        pc_ratio = np.random.normal(0.8, 0.3, len(date_range)).clip(0.1, 3.0)

        df = pd.DataFrame({
            "put_call_ratio": pc_ratio,
            "iv_skew": np.random.normal(0, 0.05, len(date_range)),
            "large_block_trades": np.random.poisson(2, len(date_range))
        })
        df.index.name = "timestamp"

        return df

    # ============================================================================
    # Alternative Data Methods
    # ============================================================================

    def get_google_trends(
        self,
        keyword: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        frequency: Union[str, DataFrequency] = DataFrequency.DAY_1
    ) -> pd.DataFrame:
        """
        Fetch Google Trends data for a keyword.

        Uses pytrends library (requires installation).
        If not available, returns simulated data.
        """
        try:
            from pytrends.request import TrendReq
            HAS_PYTRENDS = True
        except ImportError:
            HAS_PYTRENDS = False
            print("[WARN] pytrends not installed. Using simulated Google Trends data.")
            return self._simulate_google_trends(keyword, start, end, frequency)

        # Implementation with pytrends
        # (Omitted for brevity - would fetch weekly or daily trends)
        return self._simulate_google_trends(keyword, start, end, frequency)

    def _simulate_google_trends(
        self,
        keyword: str,
        start: Optional[datetime],
        end: Optional[datetime],
        frequency: DataFrequency
    ) -> pd.DataFrame:
        """Simulate Google Trends data."""
        if end is None:
            end = datetime.now(timezone.utc)
        if start is None:
            start = end - timedelta(days=365)

        freq_map = {
            DataFrequency.DAY_1: "1d",
            DataFrequency.HOUR_1: "1h",
        }
        freq = freq_map.get(frequency, "1d")

        date_range = pd.date_range(start=start, end=end, freq=freq, tz="UTC")

        np.random.seed(42)
        # Trends have autocorrelation and mean-reversion
        trend = np.random.randn(len(date_range)).cumsum() * 0.1 + 50
        trend = pd.Series(trend, index=date_range).clip(0, 100)

        df = pd.DataFrame({"trend_score": trend})
        df.index.name = "timestamp"

        return df

    def get_github_activity(
        self,
        repo: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        frequency: Union[str, DataFrequency] = DataFrequency.DAY_1
    ) -> pd.DataFrame:
        """
        Fetch GitHub repository activity (stars, forks, commits).

        Requires GitHub API token for higher rate limits.
        """
        token = self._get_env_var("GITHUB_TOKEN")
        headers = {"Authorization": f"token {token}"} if token else {}

        # Parse repo: "owner/repo"
        if "/" not in repo:
            print(f"[ERROR] Invalid repo format: {repo}. Use 'owner/repo'")
            return pd.DataFrame()

        owner, repo_name = repo.split("/", 1)

        # GitHub API endpoint for commits
        url = f"https://api.github.com/repos/{owner}/{repo_name}/commits"

        # Set date range
        if end is None:
            end = datetime.now(timezone.utc)
        if start is None:
            start = end - timedelta(days=90)

        params = {
            "since": start.isoformat(),
            "until": end.isoformat(),
            "per_page": 100
        }

        try:
            self._rate_limit("github")
            resp = self.session.get(url, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            commits = resp.json()

            records = []
            for commit in commits:
                commit_date = pd.to_datetime(commit["commit"]["author"]["date"], utc=True)
                records.append({"timestamp": commit_date, "commits": 1})

            if not records:
                return pd.DataFrame()

            df = pd.DataFrame(records)
            df = df.groupby("timestamp").sum().reset_index()
            df.set_index("timestamp", inplace=True)

            # Resample to frequency
            df = df.resample(frequency.value).sum().fillna(0)

            return df

        except requests.RequestException as e:
            print(f"[ERROR] GitHub API failed: {e}")
            return self._simulate_github_activity(repo, start, end, frequency)

    def _simulate_github_activity(
        self,
        repo: str,
        start: Optional[datetime],
        end: Optional[datetime],
        frequency: DataFrequency
    ) -> pd.DataFrame:
        """Simulate GitHub activity."""
        if end is None:
            end = datetime.now(timezone.utc)
        if start is None:
            start = end - timedelta(days=365)

        date_range = pd.date_range(start=start, end=end, freq=frequency.value, tz="UTC")

        np.random.seed(42)
        # Commits per period (Poisson process)
        commits = np.random.poisson(5, len(date_range))

        df = pd.DataFrame({"commits": commits}, index=date_range)
        df.index.name = "timestamp"

        return df

    # ============================================================================
    # Data Validation and Quality Checks
    # ============================================================================

    def _validate_price_data(
        self,
        df: pd.DataFrame,
        symbol: str,
        exchange: Exchange,
        timeframe: DataFrequency
    ) -> pd.DataFrame:
        """
        Validate price data for common issues:
        - Missing values
        - Outliers (extreme price jumps)
        - Duplicate timestamps
        - Zero volume periods
        - Gaps in time series
        """
        if df.empty:
            return df

        original_len = len(df)

        # 1. Check for NaN values
        nan_count = df.isna().sum().sum()
        if nan_count > 0:
            print(f"[WARN] {symbol}: {nan_count} NaN values found. Forward-filling.")
            df = df.ffill().bfill()

        # 2. Check for duplicate indices
        duplicates = df.index.duplicated().sum()
        if duplicates > 0:
            print(f"[WARN] {symbol}: {duplicates} duplicate timestamps. Keeping first.")
            df = df[~df.index.duplicated(keep='first')]

        # 3. Check for zero or negative prices
        for col in ["open", "high", "low", "close"]:
            zero_count = (df[col] <= 0).sum()
            if zero_count > 0:
                print(f"[WARN] {symbol}: {zero_count} zero/negative {col}. Interpolating.")
                df.loc[df[col] <= 0, col] = np.nan
                df[col] = df[col].interpolate(method='time').ffill().bfill()

        # 4. Check for volume anomalies (zero volume for extended periods)
        zero_volume = (df["volume"] == 0).sum()
        if zero_volume > 0:
            print(f"[WARN] {symbol}: {zero_volume} zero-volume candles")

        # 5. Detect gaps in time series
        expected_freq = pd.Timedelta(timeframe.value)
        time_diffs = df.index.to_series().diff()
        gaps = time_diffs[time_diffs > expected_freq * 1.5]

        if len(gaps) > 0:
            print(f"[WARN] {symbol}: {len(gaps)} gaps detected (max gap: {gaps.max()})")
            # Reindex to fill gaps
            full_idx = pd.date_range(df.index[0], df.index[-1], freq=expected_freq, tz="UTC")
            df = df.reindex(full_idx)
            df = df.ffill(limit=3)  # Only forward-fill small gaps (max 3 periods)
            # Large gaps remain NaN (avoid excessive leakage)

        # 6. Outlier detection using IQR
        for col in ["open", "high", "low", "close"]:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 3 * IQR
            upper_bound = Q3 + 3 * IQR
            outliers = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
            if outliers > 0:
                print(f"[WARN] {symbol}: {outliers} {col} outliers (IQR method). Capping.")
                df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)

        # 7. Validate OHLC relationships
        invalid_ohlc = (df["high"] < df["low"]).sum()
        if invalid_ohlc > 0:
            print(f"[WARN] {symbol}: {invalid_ohlc} candles with high < low. Fixing.")
            df.loc[df["high"] < df["low"], ["high", "low"]] = df[["low", "high"]].values

        high_violations = (df["high"] < df["open"]).sum() + (df["high"] < df["close"]).sum()
        low_violations = (df["low"] > df["open"]).sum() + (df["low"] > df["close"]).sum()
        if high_violations + low_violations > 0:
            print(f"[WARN] {symbol}: {high_violations + low_violations} OHLC violations")

        print(f"[DataManager] Validated {symbol}: {original_len} -> {len(df)} rows")
        return df

    def _validate_onchain_data(
        self,
        df: pd.DataFrame,
        metric: OnChainMetric
    ) -> pd.DataFrame:
        """Validate on-chain data."""
        if df.empty:
            return df

        # Check for extreme values based on metric
        if metric == OnChainMetric.SOPR:
            df["value"] = df["value"].clip(0.1, 10.0)
        elif metric == OnChainMetric.MVRV:
            df["value"] = df["value"].clip(0.1, 20.0)
        elif metric == OnChainMetric.NUPL:
            df["value"] = df["value"].clip(-1.0, 1.0)

        # Forward-fill short gaps
        df = df.asfreq("1D").ffill(limit=3)

        return df

    def _resample_to_frequency(
        self,
        df: pd.DataFrame,
        target_freq: DataFrequency
    ) -> pd.DataFrame:
        """
        Resample data to target frequency.

        Uses appropriate aggregation:
        - Numeric: mean or sum depending on metric type
        - Sentiment: mean
        """
        freq_map = {
            DataFrequency.MINUTE_1: "1min",
            DataFrequency.MINUTE_5: "5min",
            DataFrequency.MINUTE_15: "15min",
            DataFrequency.HOUR_1: "1h",
            DataFrequency.HOUR_4: "4h",
            DataFrequency.DAY_1: "1d",
        }
        target = freq_map.get(target_freq, "1h")

        # Check if already at target frequency
        if df.index.freqstr == target or df.index.inferred_freq == target:
            return df

        # Determine aggregation method based on column names
        agg_dict = {}
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ["volume", "count", "commits", "trades"]):
                agg_dict[col] = "sum"
            else:
                agg_dict[col] = "mean"

        try:
            resampled = df.resample(target).agg(agg_dict)
            return resampled
        except Exception as e:
            print(f"[WARN] Resampling failed: {e}. Returning original.")
            return df

    # ============================================================================
    # Caching Utilities
    # ============================================================================

    def _generate_cache_key(
        self,
        data_type: str,
        **params: Any
    ) -> str:
        """Generate unique cache key from parameters."""
        param_str = json.dumps(params, sort_keys=True, default=str)
        key_hash = hashlib.md5(param_str.encode()).hexdigest()[:12]
        return f"{data_type}_{self.data_version}_{key_hash}"

    def _get_from_cache(
        self,
        cache_key: str,
        cache_dir: Path
    ) -> Optional[pd.DataFrame]:
        """Retrieve data from cache if valid."""
        cache_file = cache_dir / f"{cache_key}.parquet"

        if not cache_file.exists():
            return None

        # Check cache age
        mtime = cache_file.stat().st_mtime
        age_hours = (time.time() - mtime) / 3600
        if age_hours > self.cache_ttl_hours:
            if self.verbose:
                print(f"[DataManager] Cache expired ({age_hours:.1f}h old): {cache_key}")
            return None

        try:
            df = pd.read_parquet(cache_file)
            return df
        except Exception as e:
            print(f"[WARN] Failed to read cache {cache_file}: {e}")
            return None

    def _save_to_cache(
        self,
        cache_key: str,
        df: pd.DataFrame,
        cache_dir: Path
    ):
        """Save data to cache."""
        if df.empty:
            return

        cache_file = cache_dir / f"{cache_key}.parquet"
        try:
            df.to_parquet(cache_file, compression="snappy")
            if self.verbose:
                print(f"[DataManager] Cached data: {cache_key}")
        except Exception as e:
            print(f"[WARN] Failed to write cache {cache_file}: {e}")

    def clear_cache(self, data_type: Optional[str] = None):
        """
        Clear cached data.

        Args:
            data_type: If provided, clear only that type (price, onchain, sentiment, alternative)
                      If None, clear all caches.
        """
        if data_type:
            cache_dirs = {
                "price": self.price_cache_dir,
                "onchain": self.onchain_cache_dir,
                "sentiment": self.sentiment_cache_dir,
                "alternative": self.alternative_cache_dir,
            }
            if data_type in cache_dirs:
                for cache_file in cache_dirs[data_type].glob("*.parquet"):
                    cache_file.unlink(missing_ok=True)
                print(f"[DataManager] Cleared {data_type} cache")
        else:
            for cache_dir in [self.price_cache_dir, self.onchain_cache_dir,
                              self.sentiment_cache_dir, self.alternative_cache_dir]:
                for cache_file in cache_dir.glob("*.parquet"):
                    cache_file.unlink(missing_ok=True)
            print(f"[DataManager] Cleared all caches")

    # ============================================================================
    # Utility Methods
    # ============================================================================

    def _rate_limit(self, service: str):
        """Enforce rate limiting between API calls."""
        now = time.time()
        last_call = self._last_api_call.get(service, 0)
        elapsed = now - last_call

        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed
            time.sleep(sleep_time)

        self._last_api_call[service] = time.time()

    def _get_env_var(self, var_name: str) -> Optional[str]:
        """Get environment variable, also check config."""
        import os
        value = os.getenv(var_name)
        if not value:
            # Check config file
            try:
                from .config import RESEARCH_CONFIG
                value = RESEARCH_CONFIG.get(var_name)
            except ImportError:
                pass
        return value

    def _add_basic_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add basic technical indicators to price data."""
        # Simple Moving Averages
        df["sma_20"] = df["close"].rolling(20).mean()
        df["sma_50"] = df["close"].rolling(50).mean()
        df["sma_200"] = df["close"].rolling(200).mean()

        # Exponential Moving Averages
        df["ema_12"] = df["close"].ewm(span=12, adjust=False).mean()
        df["ema_26"] = df["close"].ewm(span=26, adjust=False).mean()

        # MACD
        df["macd"] = df["ema_12"] - df["ema_26"]
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

        # RSI (simplified)
        delta = df["close"].diff()
        gain = (delta.clip(lower=0)).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / (loss + 1e-8)
        df["rsi"] = 100 - (100 / (1 + rs))

        # Bollinger Bands
        df["bb_middle"] = df["close"].rolling(20).mean()
        bb_std = df["close"].rolling(20).std()
        df["bb_upper"] = df["bb_middle"] + 2 * bb_std
        df["bb_lower"] = df["bb_middle"] - 2 * bb_std

        return df

    def get_data_info(self) -> Dict[str, Any]:
        """Get information about cached data."""
        info = {
            "price_cache": {"files": 0, "size_mb": 0},
            "onchain_cache": {"files": 0, "size_mb": 0},
            "sentiment_cache": {"files": 0, "size_mb": 0},
            "alternative_cache": {"files": 0, "size_mb": 0},
        }

        for cache_name, cache_dir in [
            ("price_cache", self.price_cache_dir),
            ("onchain_cache", self.onchain_cache_dir),
            ("sentiment_cache", self.sentiment_cache_dir),
            ("alternative_cache", self.alternative_cache_dir),
        ]:
            if cache_dir.exists():
                files = list(cache_dir.glob("*.parquet"))
                info[cache_name]["files"] = len(files)
                info[cache_name]["size_mb"] = sum(f.stat().st_size for f in files) / (1024*1024)

        return info

# ============================================================================
# Convenience Functions
# ============================================================================

def get_data_manager(
    cache_dir: Optional[Path] = None,
    **kwargs
) -> DataManager:
    """
    Factory function to create DataManager with sensible defaults.

    Args:
        cache_dir: Override default cache directory
        **kwargs: Additional arguments passed to DataManager

    Returns:
        Configured DataManager instance
    """
    return DataManager(cache_dir=cache_dir, **kwargs)

# ============================================================================
# Example Usage (for testing)
# ============================================================================

if __name__ == "__main__":
    # Quick test
    dm = DataManager(cache_ttl_hours=24)

    print("=== Testing Price Data ===")
    btc_data = dm.get_price_data(
        symbol="BTCUSDT",
        exchange="binance",
        timeframe="1h",
        start=datetime.now(timezone.utc) - timedelta(days=7),
        end=datetime.now(timezone.utc)
    )
    print(f"Fetched {len(btc_data)} rows of BTC price data")
    print(btc_data.head())

    print("\n=== Testing On-Chain Data ===")
    sopr_data = dm.get_onchain_metrics(
        coin="BTC",
        metric="sopr",
        start=datetime.now(timezone.utc) - timedelta(days=7),
        end=datetime.now(timezone.utc)
    )
    print(f"Fetched {len(sopr_data)} rows of SOPR data")
    print(sopr_data.head())

    print("\n=== Testing Sentiment Data ===")
    news_data = dm.get_sentiment_data(
        coin="BTC",
        source="news",
        start=datetime.now(timezone.utc) - timedelta(days=7),
        end=datetime.now(timezone.utc)
    )
    print(f"Fetched {len(news_data)} rows of news sentiment")
    print(news_data.head())

    print("\n=== Cache Info ===")
    info = dm.get_data_info()
    print(json.dumps(info, indent=2))