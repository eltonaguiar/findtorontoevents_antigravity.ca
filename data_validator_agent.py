#!/usr/bin/env python3
"""
Data Validator Agent
====================
Comprehensive data quality assurance system for market data feeds.

Features:
- Multi-source data validation (Binance, CoinGecko, CryptoCompare, etc.)
- Real-time outlier detection with statistical methods
- Automated failover to backup data sources
- Data quality scoring with confidence metrics
- Intelligent gap filling algorithms
- Staleness detection with configurable thresholds
- Real-time monitoring dashboard
- API endpoints for external monitoring
- Database integration for quality tracking
- Comprehensive alerting system

Author: AI Assistant
Date: 2026
"""

import asyncio
import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import statistics
import requests

# Optional imports with fallbacks
try:
    import numpy as np  # type: ignore
    import pandas as pd  # type: ignore
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    class MockPool:
        async def close(self): pass
        async def fetchrow(self, query, *args): return None
        async def fetch(self, query, *args): return []
        async def execute(self, query, *args): pass

try:
    import aioredis
    AIREDIS_AVAILABLE = True
except ImportError:
    AIREDIS_AVAILABLE = False
    class MockRedis:
        async def from_url(self, url): return self
        async def close(self): pass
        async def publish(self, channel, message): pass
        async def set(self, key, value): pass

try:
    from fastapi import FastAPI, HTTPException  # type: ignore
    from fastapi.responses import HTMLResponse  # type: ignore
    import uvicorn  # type: ignore
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    # Mock classes for when FastAPI is not available
    class FastAPI:  # type: ignore
        def __init__(self, **kwargs): self.routes = []
        def get(self, path, **kwargs): return lambda func: None
        def post(self, path, **kwargs): return lambda func: None
    class HTMLResponse: pass  # type: ignore
    def uvicorn_run(app, **kwargs): logger.info("Mock uvicorn - web server not started")

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    class MockSession:
        async def get(self, *args, **kwargs): return None
        async def close(self): pass

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_validator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION & DATA MODELS
# ============================================================================

class DataSource(Enum):
    BINANCE = "binance"
    COINGECKO = "coingecko"
    CRYPTOCOMPARE = "cryptocompare"
    COINBASE = "coinbase"
    KRAKEN = "kraken"

class QualityLevel(Enum):
    EXCELLENT = "EXCELLENT"  # >95%
    GOOD = "GOOD"           # 85-95%
    FAIR = "FAIR"           # 70-85%
    POOR = "POOR"           # 50-70%
    CRITICAL = "CRITICAL"   # <50%

class AlertType(Enum):
    STALE_DATA = "STALE_DATA"
    OUTLIER_DETECTED = "OUTLIER_DETECTED"
    SOURCE_FAILURE = "SOURCE_FAILURE"
    GAP_DETECTED = "GAP_DETECTED"
    QUALITY_DROP = "QUALITY_DROP"
    FAILOVER_ACTIVATED = "FAILOVER_ACTIVATED"

@dataclass
class DataValidatorConfig:
    """Data validation configuration"""
    # Data sources
    primary_sources: Dict[str, List[DataSource]] = field(default_factory=lambda: {
        'BTC': [DataSource.BINANCE, DataSource.COINGECKO, DataSource.CRYPTOCOMPARE],
        'ETH': [DataSource.BINANCE, DataSource.COINGECKO, DataSource.CRYPTOCOMPARE],
        'SOL': [DataSource.BINANCE, DataSource.COINGECKO, DataSource.CRYPTOCOMPARE],
        'ADA': [DataSource.BINANCE, DataSource.COINGECKO, DataSource.CRYPTOCOMPARE],
        'DOT': [DataSource.BINANCE, DataSource.COINGECKO, DataSource.CRYPTOCOMPARE],
    })

    # Quality thresholds
    max_staleness_seconds: int = 300  # 5 minutes
    outlier_threshold_std: float = 3.0  # 3 standard deviations
    min_quality_score: float = 0.7  # 70%
    gap_fill_max_hours: int = 24  # Max gap to fill

    # Monitoring
    monitoring_interval_seconds: float = 30.0  # 30 seconds
    dashboard_update_interval: int = 60  # 1 minute
    quality_check_window_hours: int = 24  # 24 hours for quality analysis

    # API Keys
    coingecko_api_key: str = os.getenv('COINGECKO_API_KEY', '')
    cryptocompare_api_key: str = os.getenv('CRYPTOCOMPARE_API_KEY', '')

    # Alerting
    alert_cooldown_minutes: int = 5  # Prevent alert spam

@dataclass
class DataPoint:
    """Individual data point with quality metadata"""
    symbol: str
    price: Decimal
    volume: Optional[Decimal] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: DataSource = DataSource.BINANCE
    quality_score: float = 1.0
    is_outlier: bool = False
    is_gap_filled: bool = False
    confidence: float = 1.0

@dataclass
class DataFeed:
    """Data feed status and metrics"""
    symbol: str
    source: DataSource
    last_update: datetime
    status: str = "UNKNOWN"
    latency_ms: float = 0.0
    error_count: int = 0
    success_count: int = 0
    quality_score: float = 1.0
    is_active: bool = True

@dataclass
class QualityMetrics:
    """Overall data quality metrics"""
    total_feeds: int = 0
    active_feeds: int = 0
    failed_feeds: int = 0
    average_quality_score: float = 1.0
    outlier_count_24h: int = 0
    gap_count_24h: int = 0
    failover_events_24h: int = 0
    staleness_alerts_24h: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)

@dataclass
class ValidationAlert:
    """Data validation alert"""
    alert_id: str
    alert_type: AlertType
    severity: str
    message: str
    symbol: Optional[str] = None
    source: Optional[DataSource] = None
    value: float = 0.0
    threshold: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False

# ============================================================================
# DATA VALIDATOR AGENT
# ============================================================================

class DataValidatorAgent:
    """
    Comprehensive data validation agent with real-time monitoring,
    quality assurance, and automated failover capabilities.
    """

    def __init__(self, redis_url: str, db_url: str, config: Optional[DataValidatorConfig] = None):
        self.redis_url = redis_url
        self.db_url = db_url
        self.config = config or DataValidatorConfig()

        # Core components (use mocks if dependencies not available)
        self.redis: Optional[Any] = None
        self.db: Optional[Any] = None
        self.session: Optional[Any] = None

        # State
        self.feeds: Dict[str, Dict[DataSource, DataFeed]] = {}
        self.quality_metrics = QualityMetrics()
        self.active_alerts: Dict[str, ValidationAlert] = {}
        self.price_history: Dict[str, List[DataPoint]] = {}
        self.failover_active: Dict[str, DataSource] = {}

        # Monitoring
        self.monitoring_task: Optional[asyncio.Task] = None
        self.quality_task: Optional[asyncio.Task] = None
        self.dashboard_task: Optional[asyncio.Task] = None

        # Web components
        if FASTAPI_AVAILABLE:
            self.app = FastAPI(title="Data Validator Dashboard")
        else:
            self.app = FastAPI(title="Data Validator Dashboard")  # Mock will work
        self.setup_api_routes()

        # Threading for web server
        self.web_thread: Optional[threading.Thread] = None

        logger.info("Data Validator Agent initialized")

    async def start(self):
        """Start the data validator agent"""
        logger.info("Starting Data Validator Agent...")

        # Initialize connections (use mocks if dependencies not available)
        if AIREDIS_AVAILABLE:
            self.redis = await aioredis.from_url(self.redis_url)
        else:
            self.redis = MockRedis()

        if ASYNCPG_AVAILABLE:
            self.db = await asyncpg.create_pool(self.db_url)
        else:
            self.db = MockPool()

        if AIOHTTP_AVAILABLE:
            self.session = aiohttp.ClientSession()
        else:
            self.session = MockSession()

        # Initialize feeds
        await self.initialize_feeds()

        # Load historical data
        await self.load_price_history()

        # Start monitoring tasks
        self.monitoring_task = asyncio.create_task(self.monitor_feeds())
        self.quality_task = asyncio.create_task(self.check_data_quality())
        self.dashboard_task = asyncio.create_task(self.update_dashboard())

        # Start web server in background thread (only if FastAPI available)
        if FASTAPI_AVAILABLE:
            self.web_thread = threading.Thread(target=self.start_web_server, daemon=True)
            self.web_thread.start()
        else:
            logger.warning("FastAPI not available - web dashboard disabled")

        logger.info("Data Validator Agent started successfully")

    async def stop(self):
        """Stop the data validator agent"""
        logger.info("Stopping Data Validator Agent...")

        # Cancel tasks
        if self.monitoring_task:
            self.monitoring_task.cancel()
        if self.quality_task:
            self.quality_task.cancel()
        if self.dashboard_task:
            self.dashboard_task.cancel()

        # Close connections
        if self.redis:
            await self.redis.close()
        if self.db:
            await self.db.close()
        if self.session:
            await self.session.close()

        logger.info("Data Validator Agent stopped")

    async def initialize_feeds(self):
        """Initialize data feeds for all symbols"""
        for symbol, sources in self.config.primary_sources.items():
            self.feeds[symbol] = {}
            for source in sources:
                feed = DataFeed(
                    symbol=symbol,
                    source=source,
                    last_update=datetime.utcnow(),
                    status="INITIALIZING"
                )
                self.feeds[symbol][source] = feed

        logger.info(f"Initialized {len(self.feeds)} symbols with data feeds")

    async def monitor_feeds(self):
        """Main monitoring loop for data feeds"""
        while True:
            try:
                # Monitor all feeds concurrently
                tasks = []
                for symbol in self.feeds:
                    for source in self.feeds[symbol]:
                        tasks.append(self.check_feed_health(symbol, source))

                await asyncio.gather(*tasks, return_exceptions=True)

                # Update quality metrics
                await self.update_quality_metrics()

                # Check for alerts
                await self.check_alerts()

                await asyncio.sleep(self.config.monitoring_interval_seconds)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)

    async def check_feed_health(self, symbol: str, source: DataSource):
        """Check health of a specific data feed"""
        feed = self.feeds[symbol][source]

        try:
            start_time = time.time()

            # Fetch data from source
            data_point = await self.fetch_data_point(symbol, source)

            latency = (time.time() - start_time) * 1000
            feed.latency_ms = latency

            if data_point:
                feed.last_update = datetime.utcnow()
                feed.status = "HEALTHY"
                feed.success_count += 1
                feed.error_count = 0

                # Store data point
                await self.store_data_point(data_point)

                # Check for outliers
                await self.detect_outliers(symbol, data_point)

            else:
                feed.status = "FAILED"
                feed.error_count += 1

                # Trigger failover if needed
                await self.handle_feed_failure(symbol, source)

        except Exception as e:
            logger.error(f"Error checking feed {symbol}:{source}: {e}")
            feed.status = "ERROR"
            feed.error_count += 1

    async def fetch_data_point(self, symbol: str, source: DataSource) -> Optional[DataPoint]:
        """Fetch data point from specific source"""
        try:
            if source == DataSource.COINGECKO:
                return await self.fetch_coingecko(symbol)
            elif source == DataSource.CRYPTOCOMPARE:
                return await self.fetch_cryptocompare(symbol)
            elif source == DataSource.BINANCE:
                return await self.fetch_binance(symbol)
            else:
                logger.warning(f"Unsupported source: {source}")
                return None
        except Exception as e:
            logger.error(f"Error fetching from {source} for {symbol}: {e}")
            return None

    async def fetch_coingecko(self, symbol: str) -> Optional[DataPoint]:
        """Fetch data from CoinGecko"""
        if not self.session:
            return None

        coin_id = symbol.lower()
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': coin_id,
            'vs_currencies': 'usd',
            'include_24hr_vol': 'true'
        }

        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    if coin_id in data:
                        price = Decimal(str(data[coin_id]['usd']))
                        volume = Decimal(str(data[coin_id].get('usd_24h_vol', 0)))
                        return DataPoint(
                            symbol=symbol,
                            price=price,
                            volume=volume,
                            source=DataSource.COINGECKO
                        )
        except Exception as e:
            logger.error(f"Error fetching from CoinGecko: {e}")
        return None

    async def fetch_cryptocompare(self, symbol: str) -> Optional[DataPoint]:
        """Fetch data from CryptoCompare"""
        if not self.session:
            return None

        url = "https://min-api.cryptocompare.com/data/price"
        params = {
            'fsym': symbol,
            'tsyms': 'USD',
            'api_key': self.config.cryptocompare_api_key
        }

        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'USD' in data:
                        price = Decimal(str(data['USD']))
                        return DataPoint(
                            symbol=symbol,
                            price=price,
                            source=DataSource.CRYPTOCOMPARE
                        )
        except Exception as e:
            logger.error(f"Error fetching from CryptoCompare: {e}")
        return None

    async def fetch_binance(self, symbol: str) -> Optional[DataPoint]:
        """Fetch data from Binance"""
        if not self.session:
            return None

        url = f"https://api.binance.com/api/v3/ticker/price"
        params = {'symbol': f'{symbol}USDT'}

        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    price = Decimal(str(data['price']))
                    return DataPoint(
                        symbol=symbol,
                        price=price,
                        source=DataSource.BINANCE
                    )
        except Exception as e:
            logger.error(f"Error fetching from Binance: {e}")
        return None

    async def detect_outliers(self, symbol: str, data_point: DataPoint):
        """Detect price outliers using statistical methods"""
        if symbol not in self.price_history:
            return

        history = self.price_history[symbol]
        if len(history) < 10:  # Need minimum history
            return

        # Get recent prices (last hour)
        recent_prices = [
            float(p.price) for p in history
            if (datetime.utcnow() - p.timestamp).total_seconds() < 3600
        ]

        if len(recent_prices) < 5:
            return

        try:
            mean = statistics.mean(recent_prices)
            stdev = statistics.stdev(recent_prices)

            current_price = float(data_point.price)
            z_score = abs(current_price - mean) / stdev if stdev > 0 else 0

            if z_score > self.config.outlier_threshold_std:
                data_point.is_outlier = True
                await self.create_alert(
                    AlertType.OUTLIER_DETECTED,
                    "HIGH",
                    f"Outlier detected for {symbol}: {current_price} (z-score: {z_score:.2f})",
                    symbol=symbol,
                    value=z_score,
                    threshold=self.config.outlier_threshold_std
                )
                logger.warning(f"Outlier detected: {symbol} price {current_price}, z-score {z_score:.2f}")

        except Exception as e:
            logger.error(f"Error detecting outliers for {symbol}: {e}")

    async def handle_feed_failure(self, symbol: str, failed_source: DataSource):
        """Handle feed failure and trigger failover"""
        sources = self.config.primary_sources.get(symbol, [])
        if failed_source not in sources:
            return

        # Find next available source
        current_index = sources.index(failed_source)
        for i in range(1, len(sources)):
            next_index = (current_index + i) % len(sources)
            next_source = sources[next_index]

            feed = self.feeds[symbol][next_source]
            if feed.status == "HEALTHY":
                if symbol not in self.failover_active or self.failover_active[symbol] != next_source:
                    self.failover_active[symbol] = next_source
                    await self.create_alert(
                        AlertType.FAILOVER_ACTIVATED,
                        "MEDIUM",
                        f"Failover activated for {symbol}: {failed_source} -> {next_source}",
                        symbol=symbol,
                        source=next_source
                    )
                    logger.info(f"Failover: {symbol} switched from {failed_source} to {next_source}")
                break

    async def check_data_quality(self):
        """Periodic data quality assessment"""
        while True:
            try:
                await self.assess_overall_quality()
                await self.detect_data_gaps()
                await self.check_staleness()

                await asyncio.sleep(300)  # 5 minutes

            except Exception as e:
                logger.error(f"Error in quality check: {e}")
                await asyncio.sleep(60)

    async def assess_overall_quality(self):
        """Assess overall data quality across all feeds"""
        total_quality = 0.0
        total_feeds = 0
        active_feeds = 0

        for symbol in self.feeds:
            for source, feed in self.feeds[symbol].items():
                total_feeds += 1
                if feed.status == "HEALTHY":
                    active_feeds += 1
                    total_quality += feed.quality_score

        self.quality_metrics.total_feeds = total_feeds
        self.quality_metrics.active_feeds = active_feeds
        self.quality_metrics.failed_feeds = total_feeds - active_feeds
        self.quality_metrics.average_quality_score = total_quality / active_feeds if active_feeds > 0 else 0.0

        # Alert on quality drops
        if self.quality_metrics.average_quality_score < self.config.min_quality_score:
            await self.create_alert(
                AlertType.QUALITY_DROP,
                "HIGH",
                f"Overall data quality dropped to {self.quality_metrics.average_quality_score:.2%}",
                value=self.quality_metrics.average_quality_score,
                threshold=self.config.min_quality_score
            )

    async def detect_data_gaps(self):
        """Detect and fill data gaps"""
        for symbol in self.price_history:
            history = sorted(self.price_history[symbol], key=lambda x: x.timestamp)

            if len(history) < 2:
                continue

            # Check for gaps larger than expected interval
            expected_interval = timedelta(minutes=5)  # Expected data frequency

            for i in range(1, len(history)):
                gap = history[i].timestamp - history[i-1].timestamp
                if gap > expected_interval * 2:  # 2x expected interval = gap
                    await self.fill_data_gap(symbol, history[i-1], history[i])

                    if gap > timedelta(hours=1):  # Alert on large gaps
                        await self.create_alert(
                            AlertType.GAP_DETECTED,
                            "MEDIUM",
                            f"Data gap detected for {symbol}: {gap.total_seconds()/3600:.1f} hours",
                            symbol=symbol,
                            value=gap.total_seconds()/3600
                        )

    async def fill_data_gap(self, symbol: str, start_point: DataPoint, end_point: DataPoint):
        """Fill data gap using interpolation"""
        gap_duration = end_point.timestamp - start_point.timestamp
        if gap_duration > timedelta(hours=self.config.gap_fill_max_hours):
            return  # Too large to fill

        # Simple linear interpolation
        price_diff = float(end_point.price) - float(start_point.price)
        time_diff = gap_duration.total_seconds()

        # Fill with interpolated points every 5 minutes
        current_time = start_point.timestamp
        interval = timedelta(minutes=5)

        while current_time < end_point.timestamp:
            progress = (current_time - start_point.timestamp).total_seconds() / time_diff
            interpolated_price = float(start_point.price) + price_diff * progress

            filled_point = DataPoint(
                symbol=symbol,
                price=Decimal(str(interpolated_price)),
                timestamp=current_time,
                source=start_point.source,
                is_gap_filled=True,
                quality_score=0.5  # Lower quality for filled data
            )

            await self.store_data_point(filled_point)
            current_time += interval

    async def check_staleness(self):
        """Check for stale data across all feeds"""
        now = datetime.utcnow()
        stale_threshold = timedelta(seconds=self.config.max_staleness_seconds)

        for symbol in self.feeds:
            for source, feed in self.feeds[symbol].items():
                if feed.status == "HEALTHY":
                    age = now - feed.last_update
                    if age > stale_threshold:
                        feed.status = "STALE"
                        await self.create_alert(
                            AlertType.STALE_DATA,
                            "HIGH",
                            f"Stale data for {symbol}:{source} - {age.total_seconds():.0f}s old",
                            symbol=symbol,
                            source=source,
                            value=age.total_seconds(),
                            threshold=self.config.max_staleness_seconds
                        )

    async def create_alert(self, alert_type: AlertType, severity: str, message: str,
                          symbol: Optional[str] = None, source: Optional[DataSource] = None,
                          value: float = 0.0, threshold: float = 0.0):
        """Create a validation alert"""
        alert_id = f"{alert_type.value}_{symbol or 'SYSTEM'}_{int(time.time())}"

        # Check cooldown
        if alert_id in self.active_alerts:
            last_alert = self.active_alerts[alert_id]
            if (datetime.utcnow() - last_alert.timestamp).total_seconds() < self.config.alert_cooldown_minutes * 60:
                return  # Cooldown active

        alert = ValidationAlert(
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            symbol=symbol,
            source=source,
            value=value,
            threshold=threshold
        )

        self.active_alerts[alert_id] = alert

        # Log alert
        logger.warning(f"ALERT [{severity}]: {message}")

        # Store in database
        await self.store_alert(alert)

    async def store_data_point(self, data_point: DataPoint):
        """Store data point in history and database"""
        if data_point.symbol not in self.price_history:
            self.price_history[data_point.symbol] = []

        # Keep last 1000 points per symbol
        history = self.price_history[data_point.symbol]
        history.append(data_point)
        if len(history) > 1000:
            history.pop(0)

        # Store in database
        if self.db:
            try:
                await self.db.execute("""
                    INSERT INTO data_points (symbol, price, volume, timestamp, source, quality_score, is_outlier, is_gap_filled)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, data_point.symbol, float(data_point.price), float(data_point.volume) if data_point.volume else None,
                     data_point.timestamp, data_point.source.value, data_point.quality_score,
                     data_point.is_outlier, data_point.is_gap_filled)
            except Exception as e:
                logger.error(f"Error storing data point: {e}")

    async def store_alert(self, alert: ValidationAlert):
        """Store alert in database"""
        if self.db:
            try:
                await self.db.execute("""
                    INSERT INTO validation_alerts (alert_id, alert_type, severity, message, symbol, source, value, threshold, timestamp)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """, alert.alert_id, alert.alert_type.value, alert.severity, alert.message,
                     alert.symbol, alert.source.value if alert.source else None,
                     alert.value, alert.threshold, alert.timestamp)
            except Exception as e:
                logger.error(f"Error storing alert: {e}")

    async def load_price_history(self):
        """Load recent price history from database"""
        if not self.db:
            return

        try:
            # Load last 24 hours of data
            since = datetime.utcnow() - timedelta(hours=24)
            rows = await self.db.fetch("""
                SELECT symbol, price, volume, timestamp, source, quality_score, is_outlier, is_gap_filled
                FROM data_points
                WHERE timestamp > $1
                ORDER BY timestamp
            """, since)

            for row in rows:
                data_point = DataPoint(
                    symbol=row['symbol'],
                    price=Decimal(str(row['price'])),
                    volume=Decimal(str(row['volume'])) if row['volume'] else None,
                    timestamp=row['timestamp'],
                    source=DataSource(row['source']),
                    quality_score=row['quality_score'],
                    is_outlier=row['is_outlier'],
                    is_gap_filled=row['is_gap_filled']
                )

                if data_point.symbol not in self.price_history:
                    self.price_history[data_point.symbol] = []
                self.price_history[data_point.symbol].append(data_point)

            logger.info(f"Loaded {len(rows)} historical data points")

        except Exception as e:
            logger.error(f"Error loading price history: {e}")

    async def update_quality_metrics(self):
        """Update overall quality metrics"""
        self.quality_metrics.last_updated = datetime.utcnow()

        # Count recent outliers and gaps
        now = datetime.utcnow()
        day_ago = now - timedelta(hours=24)

        outlier_count = 0
        gap_count = 0

        for symbol in self.price_history:
            for point in self.price_history[symbol]:
                if point.timestamp > day_ago:
                    if point.is_outlier:
                        outlier_count += 1
                    if point.is_gap_filled:
                        gap_count += 1

        self.quality_metrics.outlier_count_24h = outlier_count
        self.quality_metrics.gap_count_24h = gap_count

    async def check_alerts(self):
        """Check and clean up old alerts"""
        now = datetime.utcnow()
        max_age = timedelta(hours=24)

        # Remove old alerts
        to_remove = []
        for alert_id, alert in self.active_alerts.items():
            if now - alert.timestamp > max_age:
                to_remove.append(alert_id)

        for alert_id in to_remove:
            del self.active_alerts[alert_id]

    def setup_api_routes(self):
        """Setup FastAPI routes for the dashboard"""

        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard():
            return self.generate_dashboard_html()

        @self.app.get("/api/health")
        async def health_check():
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": {
                    "total_feeds": self.quality_metrics.total_feeds,
                    "active_feeds": self.quality_metrics.active_feeds,
                    "average_quality": f"{self.quality_metrics.average_quality_score:.2%}",
                    "outliers_24h": self.quality_metrics.outlier_count_24h,
                    "alerts_active": len(self.active_alerts)
                }
            }

        @self.app.get("/api/feeds")
        async def get_feeds():
            feeds_data = {}
            for symbol in self.feeds:
                feeds_data[symbol] = {}
                for source, feed in self.feeds[symbol].items():
                    feeds_data[symbol][source.value] = {
                        "status": feed.status,
                        "last_update": feed.last_update.isoformat(),
                        "latency_ms": feed.latency_ms,
                        "quality_score": feed.quality_score,
                        "error_count": feed.error_count
                    }
            return feeds_data

        @self.app.get("/api/alerts")
        async def get_alerts():
            return {
                alert_id: {
                    "type": alert.alert_type.value,
                    "severity": alert.severity,
                    "message": alert.message,
                    "symbol": alert.symbol,
                    "timestamp": alert.timestamp.isoformat(),
                    "acknowledged": alert.acknowledged
                }
                for alert_id, alert in self.active_alerts.items()
            }

        @self.app.get("/api/quality")
        async def get_quality_metrics():
            return {
                "overall_quality": self.quality_metrics.average_quality_score,
                "active_feeds": self.quality_metrics.active_feeds,
                "failed_feeds": self.quality_metrics.failed_feeds,
                "outliers_24h": self.quality_metrics.outlier_count_24h,
                "gaps_24h": self.quality_metrics.gap_count_24h,
                "failovers_24h": self.quality_metrics.failover_events_24h,
                "staleness_alerts_24h": self.quality_metrics.staleness_alerts_24h,
                "last_updated": self.quality_metrics.last_updated.isoformat()
            }

    def generate_dashboard_html(self) -> str:
        """Generate HTML dashboard"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Data Validator Dashboard</title>
            <meta http-equiv="refresh" content="60">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .metric {{ background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 5px; }}
                .alert {{ background: #ffebee; border-left: 5px solid #f44336; padding: 10px; margin: 10px 0; }}
                .warning {{ background: #fff3e0; border-left: 5px solid #ff9800; padding: 10px; margin: 10px 0; }}
                .healthy {{ background: #e8f5e8; border-left: 5px solid #4caf50; padding: 10px; margin: 10px 0; }}
                .status-healthy {{ color: #4caf50; }}
                .status-error {{ color: #f44336; }}
                .status-stale {{ color: #ff9800; }}
            </style>
        </head>
        <body>
            <h1>Data Validator Dashboard</h1>
            <p>Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>

            <h2>Quality Metrics</h2>
            <div class="metric">
                <strong>Overall Quality Score:</strong> {self.quality_metrics.average_quality_score:.2%}<br>
                <strong>Active Feeds:</strong> {self.quality_metrics.active_feeds}/{self.quality_metrics.total_feeds}<br>
                <strong>Outliers (24h):</strong> {self.quality_metrics.outlier_count_24h}<br>
                <strong>Data Gaps (24h):</strong> {self.quality_metrics.gap_count_24h}<br>
                <strong>Active Alerts:</strong> {len(self.active_alerts)}
            </div>

            <h2>Active Alerts</h2>
            {"".join([f'<div class="alert"><strong>{alert.alert_type.value}</strong> [{alert.severity}]: {alert.message}</div>' for alert in self.active_alerts.values()])}

            <h2>Feed Status</h2>
        """

        for symbol in sorted(self.feeds.keys()):
            html += f"<h3>{symbol}</h3>"
            for source, feed in self.feeds[symbol].items():
                status_class = "status-healthy" if feed.status == "HEALTHY" else "status-error" if feed.status in ["FAILED", "ERROR"] else "status-stale"
                html += f"""
                <div class="metric">
                    <strong>{source.value.upper()}:</strong>
                    <span class="{status_class}">{feed.status}</span><br>
                    Last Update: {feed.last_update.strftime('%H:%M:%S')}<br>
                    Latency: {feed.latency_ms:.1f}ms<br>
                    Quality: {feed.quality_score:.2%}<br>
                    Errors: {feed.error_count}
                </div>
                """

        html += """
        </body>
        </html>
        """
        return html

    async def update_dashboard(self):
        """Update dashboard data periodically"""
        while True:
            try:
                # Dashboard auto-updates via HTML refresh
                await asyncio.sleep(self.config.dashboard_update_interval)
            except Exception as e:
                logger.error(f"Error updating dashboard: {e}")
                await asyncio.sleep(10)

    def start_web_server(self):
        """Start the web server in a separate thread"""
        try:
            uvicorn.run(self.app, host="0.0.0.0", port=8001, log_level="warning")  # type: ignore
        except Exception as e:
            logger.error(f"Error starting web server: {e}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    """Main entry point"""
    # Configuration
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    db_url = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/trading")

    # Initialize agent
    agent = DataValidatorAgent(redis_url, db_url)

    # Start agent
    await agent.start()

    try:
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())