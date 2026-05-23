"""
QuanEngine Failover System
============================
Multi-tier fallback system for data sources, APIs, and critical services.
Ensures continuous operation even when primary services fail.

Tiers:
  Tier 1: Primary (yfinance, Binance)
  Tier 2: Crypto Data APIs (CoinGecko, CoinMarketCap, CryptoCompare)
  Tier 3: Cached/Stale Data (with warnings)
  Tier 4: Mock Data (last resort for testing)
"""

import os
import json
import time
import pickle
import logging
import hashlib
import urllib.request
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Callable, Any, Tuple
from dataclasses import dataclass, asdict
from functools import wraps
import threading

import pandas as pd
import numpy as np

logger = logging.getLogger("QuanEngine.Failover")

# ============================================================================
# CONFIGURATION
# ============================================================================

FAILOVER_CONFIG = {
    # Cache settings
    "cache_dir": os.path.join(os.path.dirname(__file__), "data", "failover_cache"),
    "cache_ttl_minutes": 60,  # How long cached data is considered "fresh"
    "stale_data_ttl_hours": 24,  # How long to use stale data as fallback
    
    # Retry settings
    "max_retries": 3,
    "retry_delay_base": 1.0,  # Base delay in seconds
    "retry_delay_max": 10.0,
    
    # API Rate limits
    "coingecko_rate_limit": 1.2,  # Seconds between calls (free tier: 10-30 calls/min)
    "cryptocompare_rate_limit": 0.2,  # Free tier: 100k calls/month
    
    # Feature flags
    "enable_tier2_apis": True,
    "enable_stale_cache": True,
    "enable_mock_fallback": False,  # Only for testing
    "log_all_failures": True,
}

# API Endpoints
COINGECKO_API = "https://api.coingecko.com/api/v3"
CRYPTOCOMPARE_API = "https://min-api.cryptocompare.com/data"

# Symbol mappings
BINANCE_TO_COINGECKO = {
    "BTCUSDT": "bitcoin",
    "ETHUSDT": "ethereum",
    "SOLUSDT": "solana",
    "BNBUSDT": "binancecoin",
    "DOGEUSDT": "dogecoin",
    "XRPUSDT": "ripple",
    "ADAUSDT": "cardano",
    "AVAXUSDT": "avalanche-2",
    "DOTUSDT": "polkadot",
    "MATICUSDT": "matic-network",
    "LTCUSDT": "litecoin",
    "LINKUSDT": "chainlink",
    "UNIUSDT": "uniswap",
    "AAVEUSDT": "aave",
    "ATOMUSDT": "cosmos",
    "NEARUSDT": "near",
    "APTUSDT": "aptos",
    "SUIUSDT": "sui",
    "TONUSDT": "the-open-network",
    "ICPUSDT": "internet-computer",
    "ARBUSDT": "arbitrum",
    "OPUSDT": "optimism",
    "MKRUSDT": "maker",
    "INJUSDT": "injective-protocol",
    "FETUSDT": "fetch-ai",
    "TIAUSDT": "celestia",
    "SEIUSDT": "sei-network",
    "JUPUSDT": "jupiter-exchange-solana",
    "WIFUSDT": "dogwifcoin",
    "PEPEUSDT": "pepe",
    "FILUSDT": "filecoin",
    "TRXUSDT": "tron",
    "KASUSDT": "kaspa",
    "ETCUSDT": "ethereum-classic",
    "ALGOUSDT": "algorand",
    "XLMUSDT": "stellar",
    "VETUSDT": "vechain",
    "HBARUSDT": "hedera-hashgraph",
    "SANDUSDT": "the-sandbox",
    "MANAUSDT": "decentraland",
    "AXSUSDT": "axie-infinity",
    "SNXUSDT": "havven",
    "COMPUSDT": "compound-governance-token",
    "CRVUSDT": "curve-dao-token",
    "LDOUSDT": "lido-dao",
    "RNDRUSDT": "render-token",
}

BINANCE_TO_CRYPTOCOMPARE = {
    "BTCUSDT": "BTC",
    "ETHUSDT": "ETH",
    "SOLUSDT": "SOL",
    "BNBUSDT": "BNB",
    "DOGEUSDT": "DOGE",
    "XRPUSDT": "XRP",
    "ADAUSDT": "ADA",
    "AVAXUSDT": "AVAX",
    "DOTUSDT": "DOT",
    "MATICUSDT": "MATIC",
    "LTCUSDT": "LTC",
    "LINKUSDT": "LINK",
    "UNIUSDT": "UNI",
    "AAVEUSDT": "AAVE",
    "ATOMUSDT": "ATOM",
    "NEARUSDT": "NEAR",
    "APTUSDT": "APT",
    "SUIUSDT": "SUI",
    "TONUSDT": "TON",
    "ICPUSDT": "ICP",
    "ARBUSDT": "ARB",
    "OPUSDT": "OP",
    "MKRUSDT": "MKR",
    "INJUSDT": "INJ",
    "FETUSDT": "FET",
    "TIAUSDT": "TIA",
    "SEIUSDT": "SEI",
    "JUPUSDT": "JUP",
    "WIFUSDT": "WIF",
    "PEPEUSDT": "PEPE",
    "FILUSDT": "FIL",
    "TRXUSDT": "TRX",
    "KASUSDT": "KAS",
    "ETCUSDT": "ETC",
    "ALGOUSDT": "ALGO",
    "XLMUSDT": "XLM",
    "VETUSDT": "VET",
    "HBARUSDT": "HBAR",
    "SANDUSDT": "SAND",
    "MANAUSDT": "MANA",
    "AXSUSDT": "AXS",
    "SNXUSDT": "SNX",
    "COMPUSDT": "COMP",
    "CRVUSDT": "CRV",
    "LDOUSDT": "LDO",
    "RNDRUSDT": "RNDR",
}

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class FailoverResult:
    """Result of a failover operation."""
    success: bool
    data: Any = None
    source: str = "unknown"
    is_cached: bool = False
    is_stale: bool = False
    error: str = None
    latency_ms: float = 0.0
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SourceHealth:
    """Health status of a data source."""
    name: str
    is_healthy: bool = True
    last_success: datetime = None
    last_failure: datetime = None
    failure_count: int = 0
    success_count: int = 0
    avg_latency_ms: float = 0.0
    
    def record_success(self, latency_ms: float):
        self.is_healthy = True
        self.last_success = datetime.utcnow()
        self.success_count += 1
        # Exponential moving average of latency
        self.avg_latency_ms = 0.9 * self.avg_latency_ms + 0.1 * latency_ms if self.avg_latency_ms > 0 else latency_ms
    
    def record_failure(self):
        self.last_failure = datetime.utcnow()
        self.failure_count += 1
        # Mark unhealthy after 3 consecutive failures
        if self.failure_count >= 3:
            self.is_healthy = False


# ============================================================================
# CACHE MANAGER
# ============================================================================

class CacheManager:
    """Manages local cache for failover data."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.cache_dir = FAILOVER_CONFIG["cache_dir"]
        os.makedirs(self.cache_dir, exist_ok=True)
        self._memory_cache: Dict[str, Any] = {}
        self._cache_meta: Dict[str, dict] = {}
        logger.info(f"CacheManager initialized at {self.cache_dir}")
    
    def _get_cache_path(self, key: str) -> str:
        """Get filesystem path for cache key."""
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{safe_key}.pkl")
    
    def _get_meta_path(self, key: str) -> str:
        """Get metadata path for cache key."""
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{safe_key}.json")
    
    def get(self, key: str, max_age_minutes: int = None) -> Optional[Any]:
        """Get cached data if not expired."""
        if max_age_minutes is None:
            max_age_minutes = FAILOVER_CONFIG["cache_ttl_minutes"]
        
        # Check memory cache first
        if key in self._memory_cache:
            meta = self._cache_meta.get(key, {})
            cached_time = datetime.fromisoformat(meta.get("timestamp", "2000-01-01"))
            if datetime.utcnow() - cached_time < timedelta(minutes=max_age_minutes):
                return self._memory_cache[key]
        
        # Check disk cache
        cache_path = self._get_cache_path(key)
        meta_path = self._get_meta_path(key)
        
        if not os.path.exists(cache_path) or not os.path.exists(meta_path):
            return None
        
        try:
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            
            cached_time = datetime.fromisoformat(meta.get("timestamp", "2000-01-01"))
            if datetime.utcnow() - cached_time < timedelta(minutes=max_age_minutes):
                with open(cache_path, 'rb') as f:
                    data = pickle.load(f)
                # Populate memory cache
                self._memory_cache[key] = data
                self._cache_meta[key] = meta
                return data
        except Exception as e:
            logger.warning(f"Cache read error for {key}: {e}")
        
        return None
    
    def get_stale(self, key: str, max_age_hours: int = None) -> Optional[Any]:
        """Get cached data even if stale (for emergency fallback)."""
        if max_age_hours is None:
            max_age_hours = FAILOVER_CONFIG["stale_data_ttl_hours"]
        
        # Try regular get first
        result = self.get(key, max_age_minutes=max_age_hours * 60)
        if result is not None:
            return result
        
        # Try disk cache even if expired
        cache_path = self._get_cache_path(key)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning(f"Stale cache read error for {key}: {e}")
        
        return None
    
    def set(self, key: str, data: Any, metadata: dict = None):
        """Cache data to memory and disk."""
        # Memory cache
        self._memory_cache[key] = data
        self._cache_meta[key] = {
            "timestamp": datetime.utcnow().isoformat(),
            **(metadata or {})
        }
        
        # Disk cache
        try:
            cache_path = self._get_cache_path(key)
            meta_path = self._get_meta_path(key)
            
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            
            with open(meta_path, 'w') as f:
                json.dump(self._cache_meta[key], f)
        except Exception as e:
            logger.warning(f"Cache write error for {key}: {e}")
    
    def clear(self):
        """Clear all caches."""
        self._memory_cache.clear()
        self._cache_meta.clear()
        for f in os.listdir(self.cache_dir):
            try:
                os.remove(os.path.join(self.cache_dir, f))
            except:
                pass


# ============================================================================
# HEALTH MONITOR
# ============================================================================

class HealthMonitor:
    """Monitors health of all data sources."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.sources: Dict[str, SourceHealth] = {}
        self._lock = threading.RLock()
    
    def get_health(self, name: str) -> SourceHealth:
        """Get or create health tracker for a source."""
        with self._lock:
            if name not in self.sources:
                self.sources[name] = SourceHealth(name=name)
            return self.sources[name]
    
    def record_success(self, name: str, latency_ms: float):
        """Record successful operation."""
        health = self.get_health(name)
        health.record_success(latency_ms)
    
    def record_failure(self, name: str):
        """Record failed operation."""
        health = self.get_health(name)
        health.record_failure()
    
    def get_healthy_sources(self) -> List[str]:
        """Get list of currently healthy sources."""
        with self._lock:
            return [name for name, h in self.sources.items() if h.is_healthy]
    
    def get_health_report(self) -> dict:
        """Get full health report."""
        with self._lock:
            return {
                name: {
                    "is_healthy": h.is_healthy,
                    "success_count": h.success_count,
                    "failure_count": h.failure_count,
                    "last_success": h.last_success.isoformat() if h.last_success else None,
                    "last_failure": h.last_failure.isoformat() if h.last_failure else None,
                    "avg_latency_ms": round(h.avg_latency_ms, 2),
                }
                for name, h in self.sources.items()
            }


# ============================================================================
# FAILOVER FETCHERS
# ============================================================================

class FailoverDataFetcher:
    """Multi-tier data fetcher with automatic failover."""
    
    def __init__(self):
        self.cache = CacheManager()
        self.health = HealthMonitor()
        self._last_coingecko_call = 0
        self._last_cmc_call = 0
        self._lock = threading.Lock()
    
    def _rate_limit(self, source: str):
        """Apply rate limiting for APIs."""
        if source == "coingecko":
            min_interval = FAILOVER_CONFIG["coingecko_rate_limit"]
            last_call = self._last_coingecko_call
            with self._lock:
                elapsed = time.time() - self._last_coingecko_call
                if elapsed < min_interval:
                    time.sleep(min_interval - elapsed)
                self._last_coingecko_call = time.time()
        elif source == "cryptocompare":
            min_interval = FAILOVER_CONFIG["cryptocompare_rate_limit"]
            with self._lock:
                elapsed = time.time() - self._last_cmc_call
                if elapsed < min_interval:
                    time.sleep(min_interval - elapsed)
                self._last_cmc_call = time.time()
    
    def _retry_with_backoff(self, func: Callable, *args, **kwargs) -> Tuple[bool, Any, float]:
        """Execute function with retry and exponential backoff."""
        max_retries = FAILOVER_CONFIG["max_retries"]
        base_delay = FAILOVER_CONFIG["retry_delay_base"]
        max_delay = FAILOVER_CONFIG["retry_delay_max"]
        
        for attempt in range(max_retries):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                latency = (time.time() - start) * 1000
                return True, result, latency
            except Exception as e:
                latency = (time.time() - start) * 1000
                if FAILOVER_CONFIG["log_all_failures"]:
                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                
                if attempt < max_retries - 1:
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    time.sleep(delay)
        
        return False, None, latency
    
    # -------------------------------------------------------------------------
    # TIER 1: Primary Sources (yfinance, Binance)
    # -------------------------------------------------------------------------
    
    def _fetch_yfinance(self, symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
        """Fetch from yfinance."""
        try:
            import yfinance as yf
        except ImportError:
            return None
        
        def _do_fetch():
            yf_ticker = self._binance_to_yf(symbol)
            period_map = {"1h": "25d", "4h": "60d", "1d": "2y", "15m": "7d"}
            period = period_map.get(interval, "25d")
            
            df = yf.download(yf_ticker, period=period, interval=interval, progress=False)
            if df is None or df.empty:
                raise ValueError("Empty dataframe")
            
            # Flatten MultiIndex columns
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            df = df.rename(columns={
                "Open": "open", "High": "high", "Low": "low",
                "Close": "close", "Volume": "volume"
            })
            df = df[["open", "high", "low", "close", "volume"]].dropna()
            
            if len(df) > limit:
                df = df.tail(limit)
            
            return df
        
        success, result, latency = self._retry_with_backoff(_do_fetch)
        if success:
            self.health.record_success("yfinance", latency)
            return result
        else:
            self.health.record_failure("yfinance")
            return None
    
    def _fetch_binance(self, symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
        """Fetch from Binance with fallbacks."""
        from quan_engine import config
        
        bases = [config.BINANCE_BASE] + getattr(config, "BINANCE_FALLBACK_URLS", [])
        
        for base in bases:
            def _do_fetch():
                url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
                req = urllib.request.Request(url, headers={"User-Agent": "QuanEngine/1.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    raw = json.loads(resp.read().decode())
                
                df = pd.DataFrame(raw, columns=[
                    "open_time", "open", "high", "low", "close", "volume",
                    "close_time", "quote_volume", "trades", "taker_buy_base",
                    "taker_buy_quote", "ignore",
                ])
                for col in ["open", "high", "low", "close", "volume"]:
                    df[col] = df[col].astype(float)
                df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
                df = df.set_index("timestamp")
                return df[["open", "high", "low", "close", "volume"]]
            
            success, result, latency = self._retry_with_backoff(_do_fetch)
            if success:
                self.health.record_success(f"binance_{base}", latency)
                return result
            else:
                self.health.record_failure(f"binance_{base}")
        
        return None
    
    # -------------------------------------------------------------------------
    # TIER 2: Crypto Data APIs
    # -------------------------------------------------------------------------
    
    def _fetch_coingecko(self, symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
        """Fetch from CoinGecko."""
        if not FAILOVER_CONFIG["enable_tier2_apis"]:
            return None
        
        coin_id = BINANCE_TO_COINGECKO.get(symbol)
        if not coin_id:
            return None
        
        self._rate_limit("coingecko")
        
        def _do_fetch():
            # Map interval to days
            days_map = {"1h": 30, "4h": 90, "1d": 365, "15m": 7}
            days = days_map.get(interval, 30)
            
            url = f"{COINGECKO_API}/coins/{coin_id}/ohlc?vs_currency=usd&days={days}"
            req = urllib.request.Request(url, headers={"User-Agent": "QuanEngine/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            
            # CoinGecko OHLC format: [timestamp, open, high, low, close]
            df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df = df.set_index("timestamp")
            df["volume"] = 0  # CoinGecko OHLC doesn't include volume
            
            if len(df) > limit:
                df = df.tail(limit)
            
            return df
        
        success, result, latency = self._retry_with_backoff(_do_fetch)
        if success:
            self.health.record_success("coingecko", latency)
            return result
        else:
            self.health.record_failure("coingecko")
            return None
    
    def _fetch_cryptocompare(self, symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
        """Fetch from CryptoCompare."""
        if not FAILOVER_CONFIG["enable_tier2_apis"]:
            return None
        
        cmc_symbol = BINANCE_TO_CRYPTOCOMPARE.get(symbol)
        if not cmc_symbol:
            return None
        
        self._rate_limit("cryptocompare")
        
        def _do_fetch():
            # Map interval to CryptoCompare format
            interval_map = {"1h": "histohour", "4h": "histohour", "1d": "histoday", "15m": "histominute"}
            endpoint = interval_map.get(interval, "histohour")
            aggregate = 4 if interval == "4h" else 1
            
            url = f"{CRYPTOCOMPARE_API}/{endpoint}?fsym={cmc_symbol}&tsym=USD&limit={limit}&aggregate={aggregate}"
            req = urllib.request.Request(url, headers={"User-Agent": "QuanEngine/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            
            if data.get("Response") != "Success":
                raise ValueError(f"CryptoCompare error: {data.get('Message')}")
            
            rows = data["Data"]["Data"]
            df = pd.DataFrame(rows)
            df["timestamp"] = pd.to_datetime(df["time"], unit="s")
            df = df.set_index("timestamp")
            df = df.rename(columns={
                "open": "open", "high": "high", "low": "low",
                "close": "close", "volumefrom": "volume"
            })
            return df[["open", "high", "low", "close", "volume"]]
        
        success, result, latency = self._retry_with_backoff(_do_fetch)
        if success:
            self.health.record_success("cryptocompare", latency)
            return result
        else:
            self.health.record_failure("cryptocompare")
            return None
    
    # -------------------------------------------------------------------------
    # TIER 3: Cached Data
    # -------------------------------------------------------------------------
    
    def _fetch_cached(self, symbol: str, interval: str, allow_stale: bool = True) -> Optional[pd.DataFrame]:
        """Fetch from cache."""
        cache_key = f"klines:{symbol}:{interval}"
        
        # Try fresh cache first
        result = self.cache.get(cache_key)
        if result is not None:
            return result
        
        # Try stale cache if allowed
        if allow_stale and FAILOVER_CONFIG["enable_stale_cache"]:
            result = self.cache.get_stale(cache_key)
            if result is not None:
                logger.warning(f"Using stale cache for {symbol} {interval}")
                return result
        
        return None
    
    def _save_to_cache(self, symbol: str, interval: str, df: pd.DataFrame):
        """Save dataframe to cache."""
        cache_key = f"klines:{symbol}:{interval}"
        self.cache.set(cache_key, df, {
            "symbol": symbol,
            "interval": interval,
            "rows": len(df),
        })
    
    # -------------------------------------------------------------------------
    # TIER 4: Mock Data (Last Resort)
    # -------------------------------------------------------------------------
    
    def _fetch_mock(self, symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
        """Generate mock data for testing."""
        if not FAILOVER_CONFIG["enable_mock_fallback"]:
            return None
        
        logger.warning(f"Using MOCK DATA for {symbol} - THIS IS FOR TESTING ONLY")
        
        # Generate realistic-looking random walk
        np.random.seed(hash(symbol) % 2**32)
        returns = np.random.normal(0, 0.01, limit)
        price = 50000  # Starting price
        
        closes = []
        for r in returns:
            price *= (1 + r)
            closes.append(price)
        
        closes = np.array(closes)
        highs = closes * (1 + np.abs(np.random.normal(0, 0.005, limit)))
        lows = closes * (1 - np.abs(np.random.normal(0, 0.005, limit)))
        opens = closes * (1 + np.random.normal(0, 0.002, limit))
        volumes = np.random.uniform(100, 1000, limit)
        
        # Create datetime index
        end_time = datetime.utcnow()
        if interval == "1h":
            freq = "H"
        elif interval == "4h":
            freq = "4H"
        elif interval == "1d":
            freq = "D"
        else:
            freq = "H"
        
        index = pd.date_range(end=end_time, periods=limit, freq=freq)
        
        df = pd.DataFrame({
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        }, index=index)
        
        return df
    
    # -------------------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------------------
    
    def _binance_to_yf(self, symbol: str) -> str:
        """Convert Binance symbol to yfinance ticker."""
        mapping = {
            "BTCUSDT": "BTC-USD", "ETHUSDT": "ETH-USD", "SOLUSDT": "SOL-USD",
            "BNBUSDT": "BNB-USD", "DOGEUSDT": "DOGE-USD", "XRPUSDT": "XRP-USD",
            "ADAUSDT": "ADA-USD", "AVAXUSDT": "AVAX-USD", "DOTUSDT": "DOT-USD",
            "MATICUSDT": "MATIC-USD", "LTCUSDT": "LTC-USD", "LINKUSDT": "LINK-USD",
            "UNIUSDT": "UNI-USD", "AAVEUSDT": "AAVE-USD", "ATOMUSDT": "ATOM-USD",
            "NEARUSDT": "NEAR-USD", "APTUSDT": "APT-USD", "SUIUSDT": "SUI-USD",
            "TONUSDT": "TON-USD", "ICPUSDT": "ICP-USD", "ARBUSDT": "ARB-USD",
            "OPUSDT": "OP-USD", "MKRUSDT": "MKR-USD", "INJUSDT": "INJ-USD",
            "FETUSDT": "FET-USD", "TIAUSDT": "TIA-USD", "SEIUSDT": "SEI-USD",
            "JUPUSDT": "JUP-USD", "WIFUSDT": "WIF-USD", "PEPEUSDT": "PEPE-USD",
            "FILUSDT": "FIL-USD", "TRXUSDT": "TRX-USD", "ETCUSDT": "ETC-USD",
            "ALGOUSDT": "ALGO-USD", "XLMUSDT": "XLM-USD", "VETUSDT": "VET-USD",
            "HBARUSDT": "HBAR-USD", "SANDUSDT": "SAND-USD", "MANAUSDT": "MANA-USD",
            "AXSUSDT": "AXS-USD", "SNXUSDT": "SNX-USD", "COMPUSDT": "COMP-USD",
            "CRVUSDT": "CRV-USD", "LDOUSDT": "LDO-USD", "RNDRUSDT": "RNDR-USD",
        }
        yf_sym = mapping.get(symbol, symbol.replace("USDT", "-USD"))
        # Apply delisted/rebranded ticker remap
        _remap = {
            "RNDR-USD": "RENDER-USD", "FTM-USD": "S-USD", "COMP-USD": "COMP1-USD",
            "ZK-USD": "ZKSYNC-USD", "THE-USD": "THE1-USD", "TAO-USD": "TAO22974-USD",
            "HIFI-USD": "HIFI1-USD", "IMX-USD": "IMX1-USD", "MEW-USD": "MEW1-USD",
            "ZRO-USD": "ZRO1-USD", "SUI-USD": "SUI20947-USD", "POPCAT-USD": "POPCAT1-USD",
            "ROBO-USD": "ROBO1-USD", "PEPE-USD": "PEPE24478-USD", "HYPE-USD": "HYPE32196-USD",
            "PIXEL-USD": "PORTAL-USD", "TON-USD": "TON11419-USD",
        }
        return _remap.get(yf_sym, yf_sym)
    
    def fetch_klines(self, symbol: str, interval: str = "1h", limit: int = 500) -> FailoverResult:
        """
        Fetch OHLCV klines with full failover chain.
        
        Order:
          1. yfinance (Tier 1 - geo-safe)
          2. Binance + fallbacks (Tier 1)
          3. CoinGecko (Tier 2)
          4. CryptoCompare (Tier 2)
          5. Cached data (Tier 3)
          6. Mock data (Tier 4 - testing only)
        """
        cache_key = f"klines:{symbol}:{interval}"
        start_time = time.time()
        
        # Try Tier 1: yfinance
        df = self._fetch_yfinance(symbol, interval, limit)
        if df is not None and len(df) >= 50:
            self._save_to_cache(symbol, interval, df)
            return FailoverResult(
                success=True,
                data=df,
                source="yfinance",
                is_cached=False,
                latency_ms=(time.time() - start_time) * 1000
            )
        
        # Try Tier 1: Binance
        df = self._fetch_binance(symbol, interval, limit)
        if df is not None and len(df) >= 50:
            self._save_to_cache(symbol, interval, df)
            return FailoverResult(
                success=True,
                data=df,
                source="binance",
                is_cached=False,
                latency_ms=(time.time() - start_time) * 1000
            )
        
        # Try Tier 2: CoinGecko
        df = self._fetch_coingecko(symbol, interval, limit)
        if df is not None and len(df) >= 50:
            self._save_to_cache(symbol, interval, df)
            return FailoverResult(
                success=True,
                data=df,
                source="coingecko",
                is_cached=False,
                latency_ms=(time.time() - start_time) * 1000
            )
        
        # Try Tier 2: CryptoCompare
        df = self._fetch_cryptocompare(symbol, interval, limit)
        if df is not None and len(df) >= 50:
            self._save_to_cache(symbol, interval, df)
            return FailoverResult(
                success=True,
                data=df,
                source="cryptocompare",
                is_cached=False,
                latency_ms=(time.time() - start_time) * 1000
            )
        
        # Try Tier 3: Cached data
        df = self._fetch_cached(symbol, interval, allow_stale=True)
        if df is not None:
            return FailoverResult(
                success=True,
                data=df,
                source="cache",
                is_cached=True,
                is_stale=True,
                latency_ms=(time.time() - start_time) * 1000
            )
        
        # Try Tier 4: Mock data (testing only)
        df = self._fetch_mock(symbol, interval, limit)
        if df is not None:
            return FailoverResult(
                success=True,
                data=df,
                source="mock",
                is_cached=False,
                is_stale=True,
                latency_ms=(time.time() - start_time) * 1000
            )
        
        # All failed
        return FailoverResult(
            success=False,
            error="All data sources failed",
            latency_ms=(time.time() - start_time) * 1000
        )
    
    def fetch_price(self, symbol: str) -> FailoverResult:
        """Fetch current spot price with failover."""
        start_time = time.time()
        
        # Try Binance first (fastest)
        from quan_engine import config
        bases = [config.BINANCE_BASE] + getattr(config, "BINANCE_FALLBACK_URLS", [])
        
        for base in bases:
            try:
                url = f"{base}/api/v3/ticker/price?symbol={symbol}"
                req = urllib.request.Request(url, headers={"User-Agent": "QuanEngine/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                    price = float(data["price"])
                    self.health.record_success(f"binance_{base}", (time.time() - start_time) * 1000)
                    return FailoverResult(
                        success=True,
                        data=price,
                        source=f"binance_{base}",
                        latency_ms=(time.time() - start_time) * 1000
                    )
            except Exception:
                self.health.record_failure(f"binance_{base}")
                continue
        
        # Try CoinGecko
        coin_id = BINANCE_TO_COINGECKO.get(symbol)
        if coin_id:
            self._rate_limit("coingecko")
            try:
                url = f"{COINGECKO_API}/simple/price?ids={coin_id}&vs_currencies=usd"
                req = urllib.request.Request(url, headers={"User-Agent": "QuanEngine/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                    price = float(data[coin_id]["usd"])
                    self.health.record_success("coingecko", (time.time() - start_time) * 1000)
                    return FailoverResult(
                        success=True,
                        data=price,
                        source="coingecko",
                        latency_ms=(time.time() - start_time) * 1000
                    )
            except Exception:
                self.health.record_failure("coingecko")
        
        return FailoverResult(
            success=False,
            error="All price sources failed",
            latency_ms=(time.time() - start_time) * 1000
        )


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_fetcher = None

def get_failover_fetcher() -> FailoverDataFetcher:
    """Get the global failover fetcher instance."""
    global _fetcher
    if _fetcher is None:
        _fetcher = FailoverDataFetcher()
    return _fetcher


# ============================================================================
# CONVENIENCE FUNCTIONS (Drop-in replacements)
# ============================================================================

def fetch_klines_with_failover(symbol: str, interval: str = "1h", limit: int = 500) -> pd.DataFrame:
    """
    Drop-in replacement for scanner.fetch_klines with full failover.
    Returns empty DataFrame on total failure.
    """
    fetcher = get_failover_fetcher()
    result = fetcher.fetch_klines(symbol, interval, limit)
    
    if result.success:
        if result.is_stale:
            logger.warning(f"Using {'stale cached' if result.is_cached else 'mock'} data for {symbol}")
        return result.data
    else:
        logger.error(f"Failed to fetch klines for {symbol}: {result.error}")
        return pd.DataFrame()


def fetch_price_with_failover(symbol: str) -> Optional[float]:
    """
    Drop-in replacement for forward_tracker.get_binance_price with failover.
    Returns None on total failure.
    """
    fetcher = get_failover_fetcher()
    result = fetcher.fetch_price(symbol)
    
    if result.success:
        return result.data
    else:
        logger.warning(f"Failed to fetch price for {symbol}: {result.error}")
        return None


def get_health_report() -> dict:
    """Get health report for all data sources."""
    fetcher = get_failover_fetcher()
    return fetcher.health.get_health_report()


def clear_cache():
    """Clear all cached data."""
    fetcher = get_failover_fetcher()
    fetcher.cache.clear()
    logger.info("Failover cache cleared")


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test the failover system
    print("Testing Failover System...")
    print("=" * 60)
    
    # Test klines
    symbols = ["BTCUSDT", "ETHUSDT"]
    for symbol in symbols:
        print(f"\nFetching {symbol}...")
        result = get_failover_fetcher().fetch_klines(symbol, "1h", 100)
        print(f"  Success: {result.success}")
        print(f"  Source: {result.source}")
        print(f"  Is Cached: {result.is_cached}")
        print(f"  Is Stale: {result.is_stale}")
        print(f"  Rows: {len(result.data) if result.data is not None else 0}")
        print(f"  Latency: {result.latency_ms:.0f}ms")
    
    # Test price
    print("\n" + "=" * 60)
    print("Testing price fetch...")
    for symbol in symbols:
        result = get_failover_fetcher().fetch_price(symbol)
        print(f"{symbol}: {result.data} (from {result.source})" if result.success else f"{symbol}: FAILED")
    
    # Health report
    print("\n" + "=" * 60)
    print("Health Report:")
    print(json.dumps(get_health_report(), indent=2))
