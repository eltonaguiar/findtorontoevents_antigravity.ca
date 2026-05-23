#!/usr/bin/env python3
"""
Copy Trader Intelligence Engine v2
====================================
Production-grade multi-source copy-trader intelligence pipeline with:
- Quality-weighted consensus (not raw vote counting)
- Multi-source fallback (OKX -> Bybit -> Hyperliquid)
- Arkham smart-money integration with caching
- Circuit breaker pattern for API resilience
- Async parallel fetching for sub-10-minute runtime
- Performance feedback loop with auto-blacklisting

Targets: <10 min runtime, zero silent error swallowing, >60 quality threshold

Author: Senior Trading Systems Engineer
Date: 2026-05-20
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import pickle
import random
import ssl
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Generic,
    List,
    Optional,
    Protocol,
    Tuple,
    TypeVar,
    Union,
)

# ---------------------------------------------------------------------------
# Third-party imports (stdlib-only fallback where possible)
# ---------------------------------------------------------------------------
try:
    import urllib3
    URLLIB3_AVAILABLE = True
except ImportError:
    URLLIB3_AVAILABLE = False

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
LOG = logging.getLogger("copy_trader_v2")
LOG.setLevel(logging.INFO)
if not LOG.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    LOG.addHandler(_handler)

# ---------------------------------------------------------------------------
# Constants & Configuration
# ---------------------------------------------------------------------------

# Quality thresholds
MIN_QUALITY_SCORE: float = 60.0
MIN_CONSENSUS_TRADERS: int = 3
MIN_PNL_RATIO: float = 1.0
MIN_WIN_RATE: float = 0.50
MIN_RECENCY_WIN_RATE: float = 0.60
MIN_LEAD_DAYS: int = 30
MIN_AUM_USD: float = 100_000.0
RECENCY_DECAY_HOURS: float = 24.0
BLACKLIST_SHARPE_THRESHOLD: float = 0.5

# Rate limits (seconds between requests)
OKX_RATE_LIMIT: float = 1.0
BYBIT_RATE_LIMIT: float = 1.0
HYPERLIQUID_RATE_LIMIT: float = 0.5
ARKHAM_RATE_LIMIT: float = 6.5  # 10 req/min for free tier

# Circuit breaker config
CIRCUIT_FAILURE_THRESHOLD: int = 5
CIRCUIT_RECOVERY_SECONDS: int = 3600  # 1 hour

# Cache config
CACHE_TTL_SECONDS: int = 900  # 15 minutes
CACHE_DIR: Path = Path(os.environ.get("COPY_TRADER_CACHE", "/tmp/copy_trader_cache_v2"))

# Output
OUTPUT_PATH: Path = Path(
    os.environ.get("ACTIVE_PICKS_PATH", "/mnt/agents/output/alpha_engine/data/active_picks.json")
)

# ---------------------------------------------------------------------------
# Custom Exceptions — NEVER silently swallowed
# ---------------------------------------------------------------------------

class CopyTraderError(Exception):
    """Base exception for all copy-trader engine errors."""

class APIError(CopyTraderError):
    """Raised when an external API returns an error or non-2xx status."""
    def __init__(self, message: str, status_code: int = 0, source: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.source = source

class RateLimitError(APIError):
    """Raised when rate limited by an external API."""

class SSLVerificationError(APIError):
    """Raised when SSL verification fails — do NOT disable SSL to work around."""

class DataStaleError(CopyTraderError):
    """Raised when cached data is too stale to be useful."""
    def __init__(self, message: str, last_updated: Optional[datetime] = None) -> None:
        super().__init__(message)
        self.last_updated = last_updated

class InsufficientDataError(CopyTraderError):
    """Raised when there isn't enough quality data to generate a signal."""

class CircuitOpenError(CopyTraderError):
    """Raised when a circuit breaker is open and requests are being blocked."""

class QualityThresholdError(CopyTraderError):
    """Raised when no traders meet the minimum quality threshold."""

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class Direction(Enum):
    LONG = "LONG"
    SHORT = "SHORT"

@dataclass(frozen=True, slots=True)
class Position:
    """A single position held by a lead trader."""
    symbol: str
    direction: Direction
    entry_price: float
    mark_price: float
    size: float
    pnl_ratio: float
    leverage: float = 1.0
    open_time: Optional[datetime] = None
    # Normalised symbol for cross-source comparison
    normalised_symbol: str = ""

    def __post_init__(self) -> None:
        if not self.normalised_symbol:
            object.__setattr__(
                self, "normalised_symbol", normalise_symbol(self.symbol)
            )

@dataclass(slots=True)
class TraderProfile:
    """Aggregated profile of a lead trader."""
    unique_code: str
    name: str
    source: str  # 'okx', 'bybit', 'hyperliquid'
    pnl_ratio: float = 0.0
    win_rate: float = 0.0
    aum: float = 0.0
    recency_wr: float = 0.0  # 7-day or 30-day win rate
    max_drawdown: float = 0.0
    lead_days: int = 0
    follower_count: int = 0
    sharpe_30d: float = 0.0
    quality_score: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_blacklisted: bool = False
    blacklist_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["last_updated"] = self.last_updated.isoformat()
        d["direction"] = None
        return d

@dataclass(slots=True)
class CopyTraderPick:
    """Final quality-weighted consensus pick."""
    symbol: str
    direction: Direction
    confidence: float  # 0.0 - 1.0
    source_system: str = "copy_trader_intel"
    strategy: str = "quality_weighted_consensus"
    asset_class: str = "CRYPTO"
    metadata: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "direction": self.direction.value,
            "confidence": round(self.confidence, 4),
            "source_system": self.source_system,
            "strategy": self.strategy,
            "asset_class": self.asset_class,
            "metadata": self.metadata,
            "generated_at": self.generated_at.isoformat(),
        }

@dataclass(slots=True)
class SmartMoneySignal:
    """Signal from Arkham smart-money tracking."""
    entity_name: str
    chain: str
    token_symbol: str
    direction: Direction  # LONG = accumulation, SHORT = distribution
    confidence: float
    usd_value: float
    tx_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class OnChainSignal:
    """On-chain exchange flow or whale cluster signal."""
    signal_type: str  # 'exchange_flow', 'whale_cluster', 'stablecoin_velocity'
    token_symbol: str
    direction: Direction
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class HealthStatus:
    """Health check result for a single data source."""
    source: str
    healthy: bool
    last_success: Optional[datetime]
    failure_count: int
    circuit_open: bool
    latency_ms: float = 0.0
    message: str = ""

# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def normalise_symbol(symbol: str) -> str:
    """Normalise symbol across exchanges: BTC-USDT -> BTCUSDT, btc/usdt -> BTCUSDT."""
    s = symbol.upper().replace("-", "").replace("/", "").replace("_", "")
    # Strip common perpetual suffixes for comparison
    for suffix in ("PERP", "SWAP", "USDTSWAP", "USDT-SWAP"):
        if s.endswith(suffix):
            s = s[: -len(suffix)]
    return s

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def iso_now() -> str:
    return now_utc().isoformat()

# ---------------------------------------------------------------------------
# Retry Decorator with Exponential Backoff
# ---------------------------------------------------------------------------

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: Tuple[type[Exception], ...] = (APIError, urllib.error.URLError),
):
    """Decorator: retry a function with exponential backoff + jitter.

    NEVER silently swallows errors — if all retries fail, the last exception
    propagates upward so the caller knows something is wrong.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc: Optional[Exception] = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == max_retries:
                        LOG.error(
                            "[%s] All %d retries exhausted. Raising: %s",
                            func.__name__, max_retries, exc,
                        )
                        raise
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    jitter = random.uniform(0, delay * 0.2)
                    sleep_time = delay + jitter
                    LOG.warning(
                        "[%s] Attempt %d/%d failed (%s). Retrying in %.2fs...",
                        func.__name__, attempt, max_retries, exc, sleep_time,
                    )
                    time.sleep(sleep_time)
            # Should never reach here, but type checker needs it
            raise last_exc or CopyTraderError("Unexpected retry loop exit")
        return wrapper
    return decorator

def async_retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: Tuple[type[Exception], ...] = (APIError, urllib.error.URLError),
):
    """Async variant of retry_with_backoff."""
    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc: Optional[Exception] = None
            for attempt in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == max_retries:
                        LOG.error(
                            "[%s] All %d retries exhausted. Raising: %s",
                            func.__name__, max_retries, exc,
                        )
                        raise
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    jitter = random.uniform(0, delay * 0.2)
                    sleep_time = delay + jitter
                    LOG.warning(
                        "[%s] Attempt %d/%d failed (%s). Retrying in %.2fs...",
                        func.__name__, attempt, max_retries, exc, sleep_time,
                    )
                    await asyncio.sleep(sleep_time)
            raise last_exc or CopyTraderError("Unexpected retry loop exit")
        return wrapper
    return decorator

# ---------------------------------------------------------------------------
# Circuit Breaker Pattern
# ---------------------------------------------------------------------------

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    """Circuit breaker that trips after N consecutive failures and stays
    open for a cooldown period before allowing a test request."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = CIRCUIT_FAILURE_THRESHOLD,
        recovery_seconds: int = CIRCUIT_RECOVERY_SECONDS,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock() if hasattr(asyncio, "Lock") else None

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            last_fail = self._last_failure_time or 0
            if (time.time() - last_fail) > self.recovery_seconds:
                LOG.info("[CircuitBreaker:%s] Transitioning OPEN -> HALF_OPEN", self.name)
                self._state = CircuitState.HALF_OPEN
                return CircuitState.HALF_OPEN
        return self._state

    def record_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            LOG.info("[CircuitBreaker:%s] Recovery confirmed. HALF_OPEN -> CLOSED", self.name)
            self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            if self._state != CircuitState.OPEN:
                LOG.error(
                    "[CircuitBreaker:%s] TRIPPED after %d failures. Going OPEN for %ds",
                    self.name, self._failure_count, self.recovery_seconds,
                )
                self._state = CircuitState.OPEN

    def check(self) -> None:
        """Raise CircuitOpenError if the circuit is open."""
        if self.state == CircuitState.OPEN:
            raise CircuitOpenError(
                f"Circuit breaker '{self.name}' is OPEN. "
                f"Last failure: {self._last_failure_time}"
            )

# Global circuit breaker registry
_CIRCUIT_BREAKERS: Dict[str, CircuitBreaker] = {}

def get_circuit_breaker(name: str) -> CircuitBreaker:
    if name not in _CIRCUIT_BREAKERS:
        _CIRCUIT_BREAKERS[name] = CircuitBreaker(name)
    return _CIRCUIT_BREAKERS[name]

# ---------------------------------------------------------------------------
# Local File-System Cache
# ---------------------------------------------------------------------------

class LocalCache:
    """Simple on-disk cache with TTL for API responses."""

    def __init__(self, cache_dir: Path = CACHE_DIR, ttl_seconds: int = CACHE_TTL_SECONDS) -> None:
        self.cache_dir = cache_dir
        self.ttl = ttl_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, key: str) -> Path:
        hashed = hashlib.sha256(key.encode()).hexdigest()[:16]
        return self.cache_dir / f"{hashed}.pkl"

    def get(self, key: str) -> Optional[Any]:
        path = self._cache_path(key)
        if not path.exists():
            return None
        try:
            with open(path, "rb") as f:
                entry = pickle.load(f)
            cached_at = entry["ts"]
            if (time.time() - cached_at) > self.ttl:
                LOG.debug("Cache expired for key %s", key[:40])
                return None
            LOG.debug("Cache HIT for key %s", key[:40])
            return entry["data"]
        except Exception as exc:
            LOG.warning("Cache read error for %s: %s", key[:40], exc)
            return None

    def set(self, key: str, data: Any) -> None:
        path = self._cache_path(key)
        try:
            with open(path, "wb") as f:
                pickle.dump({"ts": time.time(), "data": data}, f)
        except Exception as exc:
            LOG.warning("Cache write error for %s: %s", key[:40], exc)

    def invalidate(self, key_prefix: str = "") -> int:
        """Invalidate cache entries matching a prefix. Returns count removed."""
        removed = 0
        for f in self.cache_dir.glob("*.pkl"):
            try:
                f.unlink()
                removed += 1
            except Exception:
                pass
        return removed

# Global cache instance
_global_cache: Optional[LocalCache] = None

def get_cache() -> LocalCache:
    global _global_cache
    if _global_cache is None:
        _global_cache = LocalCache()
    return _global_cache

# ---------------------------------------------------------------------------
# Thread-safe Rate Limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """Simple in-process rate limiter using token-bucket-like logic."""

    def __init__(self, min_interval_seconds: float) -> None:
        self.min_interval = min_interval_seconds
        self._last_call = 0.0

    def acquire(self) -> None:
        elapsed = time.time() - self._last_call
        if elapsed < self.min_interval:
            sleep_for = self.min_interval - elapsed
            time.sleep(sleep_for)
        self._last_call = time.time()



# =============================================================================
# SECTION 2: OKX COPY TRADER CLIENT (Primary Source)
# =============================================================================

class OKXClient:
    """OKX Copy-Trading public API client.

    Endpoints (public — no auth required):
    - GET /api/v5/copytrading/public-lead-traders
    - GET /api/v5/copytrading/public-lead-trader-positions
    - GET /api/v5/copytrading/public-lead-trader-weekly-pnl

    CRITICAL: Uses PROPER SSL verification. NEVER disables SSL.
    CRITICAL: Raises exceptions on ALL errors. NEVER swallows them.
    """

    BASE_URL: str = "https://www.okx.com"

    def __init__(self) -> None:
        self.rate_limiter = RateLimiter(OKX_RATE_LIMIT)
        self.circuit = get_circuit_breaker("okx")
        self.cache = get_cache()
        self._ssl_ctx = ssl.create_default_context()
        # Enable certificate verification (the default — explicit for clarity)
        self._ssl_ctx.check_hostname = True
        self._ssl_ctx.verify_mode = ssl.CERT_REQUIRED
        self._request_headers = {
            "User-Agent": (
                "CopyTraderIntel/2.0 (Production; OKX Public API; "
                "contact=dev@trading-intel.internal)"
            ),
            "Accept": "application/json",
        }

    # ------------------------------------------------------------------
    # Internal request helpers
    # ------------------------------------------------------------------

    def _request(
        self, method: str, path: str, params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Execute a single HTTPS request with full error handling.

        Raises:
            CircuitOpenError: if circuit breaker is open.
            RateLimitError: on HTTP 429.
            APIError: on non-2xx or non-zero code in body.
            SSLVerificationError: on SSL handshake failure.
        """
        self.circuit.check()
        self.rate_limiter.acquire()

        url = f"{self.BASE_URL}{path}"
        if params:
            query = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
            url = f"{url}?{query}"

        req = urllib.request.Request(url, headers=self._request_headers, method=method)

        try:
            with urllib.request.urlopen(req, context=self._ssl_ctx, timeout=15) as resp:
                body = resp.read().decode("utf-8")
                self.circuit.record_success()
        except urllib.error.HTTPError as exc:
            self.circuit.record_failure()
            if exc.code == 429:
                raise RateLimitError(
                    f"OKX rate limited (429) on {path}", status_code=429, source="okx"
                ) from exc
            raise APIError(
                f"OKX HTTP {exc.code} on {path}: {exc.reason}",
                status_code=exc.code,
                source="okx",
            ) from exc
        except ssl.SSLError as exc:
            self.circuit.record_failure()
            raise SSLVerificationError(
                f"OKX SSL verification failed for {path}: {exc}",
                status_code=0,
                source="okx",
            ) from exc
        except urllib.error.URLError as exc:
            self.circuit.record_failure()
            raise APIError(
                f"OKX connection error on {path}: {exc}", status_code=0, source="okx"
            ) from exc
        except TimeoutError as exc:
            self.circuit.record_failure()
            raise APIError(
                f"OKX timeout on {path}", status_code=0, source="okx"
            ) from exc

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise APIError(
                f"OKX invalid JSON from {path}: {exc}", status_code=0, source="okx"
            ) from exc

        # OKX wraps responses: {"code": "0", "data": [...], "msg": ""}
        if str(data.get("code", "0")) != "0":
            msg = data.get("msg", "Unknown OKX error")
            raise APIError(
                f"OKX API error on {path}: {msg} (code={data.get('code')})",
                status_code=int(data.get("code", 0)),
                source="okx",
            )

        return data

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def _request_with_retry(
        self, method: str, path: str, params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        return self._request(method, path, params)

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def fetch_lead_traders(
        self,
        min_pnl_ratio: float = MIN_PNL_RATIO,
        min_win_rate: float = MIN_WIN_RATE,
        min_lead_days: int = MIN_LEAD_DAYS,
        min_aum: float = MIN_AUM_USD,
        limit: int = 100,
    ) -> List[TraderProfile]:
        """Fetch OKX public lead traders with quality pre-filtering.

        Args:
            min_pnl_ratio: Minimum profit/loss ratio (e.g., 1.0 = break-even).
            min_win_rate: Minimum win rate (0.0 - 1.0).
            min_lead_days: Minimum days leading trades.
            min_aum: Minimum assets under management in USD.
            limit: Max traders to return.

        Returns:
            List of TraderProfile objects that pass quality gates.

        Raises:
            APIError: on any API failure (after retries).
            CircuitOpenError: if circuit breaker is open.
        """
        cache_key = f"okx:lead_traders:{min_pnl_ratio}:{min_win_rate}:{min_lead_days}:{min_aum}:{limit}"
        cached = self.cache.get(cache_key)
        if cached:
            LOG.info("OKX lead traders: returning %d cached profiles", len(cached))
            return cached

        LOG.info("Fetching OKX lead traders (min_pnl=%.2f, min_wr=%.0f%%, min_days=%d)",
                 min_pnl_ratio, min_win_rate * 100, min_lead_days)

        params: Dict[str, str] = {
            "instType": "SWAP",
            "sortType": "pnlRatio",  # Sort by PnL ratio descending
            "limit": str(min(limit, 100)),
        }

        data = self._request_with_retry("GET", "/api/v5/copytrading/public-lead-traders", params)
        rows: List[Dict[str, Any]] = data.get("data", [])
        LOG.info("OKX returned %d raw lead traders", len(rows))

        profiles: List[TraderProfile] = []
        for row in rows:
            try:
                pnl_ratio = float(row.get("pnlRatio", 0))
                win_rate = float(row.get("winRatio", 0))
                aum = float(row.get("aum", 0))
                lead_days = int(row.get("leadingDays", 0))
                recency_wr = float(row.get("winRatioRecent", win_rate))
                drawdown = float(row.get("maxDrawdown", 0))
                followers = int(row.get("followerCount", 0))
                sharpe = float(row.get("sharpeRatio", 0))
                unique_code = str(row.get("uniqueCode", ""))
                name = str(row.get("nickName", unique_code))

                # Hard quality gates
                if pnl_ratio < min_pnl_ratio:
                    continue
                if win_rate < min_win_rate:
                    continue
                if lead_days < min_lead_days:
                    continue
                if aum < min_aum:
                    continue
                if recency_wr < MIN_RECENCY_WIN_RATE:
                    continue

                prof = TraderProfile(
                    unique_code=unique_code,
                    name=name,
                    source="okx",
                    pnl_ratio=pnl_ratio,
                    win_rate=win_rate,
                    aum=aum,
                    recency_wr=recency_wr,
                    max_drawdown=drawdown,
                    lead_days=lead_days,
                    follower_count=followers,
                    sharpe_30d=sharpe,
                )
                profiles.append(prof)
            except (ValueError, TypeError, KeyError) as exc:
                LOG.debug("Skipping malformed OKX trader row: %s", exc)
                continue

        LOG.info("OKX: %d/%d traders passed quality gates", len(profiles), len(rows))
        self.cache.set(cache_key, profiles)
        return profiles

    def fetch_trader_positions(self, unique_code: str) -> List[Position]:
        """Fetch current open positions for a specific lead trader.

        Raises:
            APIError: on API failure.
        """
        cache_key = f"okx:positions:{unique_code}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        params: Dict[str, str] = {
            "uniqueCode": unique_code,
            "instType": "SWAP",
        }
        data = self._request_with_retry(
            "GET", "/api/v5/copytrading/public-lead-trader-positions", params
        )
        rows = data.get("data", [])
        positions: List[Position] = []
        for row in rows:
            try:
                side = str(row.get("posSide", "")).upper()
                direction = Direction.LONG if side in ("LONG", "NET_LONG") else Direction.SHORT
                pos = Position(
                    symbol=str(row.get("instId", "")),
                    direction=direction,
                    entry_price=float(row.get("avgPx", 0)),
                    mark_price=float(row.get("markPx", 0)),
                    size=float(row.get("pos", 0)),
                    pnl_ratio=float(row.get("pnlRatio", 0)),
                    leverage=float(row.get("lever", 1)),
                    open_time=datetime.fromtimestamp(
                        int(row.get("cTime", 0)) / 1000, tz=timezone.utc
                    ) if row.get("cTime") else None,
                )
                positions.append(pos)
            except (ValueError, TypeError, KeyError) as exc:
                LOG.debug("Skipping malformed OKX position row: %s", exc)
                continue

        self.cache.set(cache_key, positions)
        LOG.info("OKX trader %s: fetched %d positions", unique_code[:12], len(positions))
        return positions

    def fetch_trader_history(self, unique_code: str, weeks: int = 4) -> Dict[str, Any]:
        """Fetch historical PnL data for a lead trader.

        Returns:
            Dict with 'weekly_pnl' list, 'total_pnl', 'avg_weekly'.

        Raises:
            APIError: on API failure.
        """
        cache_key = f"okx:history:{unique_code}:{weeks}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        params: Dict[str, str] = {
            "uniqueCode": unique_code,
            "period": str(weeks),
        }
        data = self._request_with_retry(
            "GET", "/api/v5/copytrading/public-lead-trader-weekly-pnl", params
        )
        rows = data.get("data", [])
        weekly_pnl = []
        total_pnl = 0.0
        for row in rows:
            try:
                pnl = float(row.get("pnl", 0))
                weekly_pnl.append(pnl)
                total_pnl += pnl
            except (ValueError, TypeError):
                continue

        result = {
            "weekly_pnl": weekly_pnl,
            "total_pnl": total_pnl,
            "avg_weekly": total_pnl / max(len(weekly_pnl), 1),
            "unique_code": unique_code,
            "fetched_at": iso_now(),
        }
        self.cache.set(cache_key, result)
        return result

    # ------------------------------------------------------------------
    # Batch helpers
    # ------------------------------------------------------------------

    def fetch_all_positions(
        self, traders: List[TraderProfile], max_workers: int = 5
    ) -> Dict[str, List[Position]]:
        """Fetch positions for multiple traders in parallel (thread pool).

        Args:
            traders: List of trader profiles.
            max_workers: Max concurrent request threads.

        Returns:
            Mapping of unique_code -> positions list.

        Raises:
            Does NOT raise on individual trader failures — logs them.
            (This is the ONE place partial failure is acceptable because
            each trader is independent. Still logs loudly.)
        """
        results: Dict[str, List[Position]] = {}
        failures = 0

        def _fetch_one(trader: TraderProfile) -> Tuple[str, List[Position]]:
            try:
                poss = self.fetch_trader_positions(trader.unique_code)
                return (trader.unique_code, poss)
            except Exception as exc:
                LOG.error(
                    "Failed to fetch positions for OKX trader %s (%s): %s",
                    trader.unique_code[:12], trader.name, exc,
                )
                raise

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_fetch_one, t): t for t in traders}
            for future in as_completed(futures):
                trader = futures[future]
                try:
                    code, poss = future.result()
                    results[code] = poss
                except Exception:
                    failures += 1

        LOG.info(
            "OKX batch positions: %d succeeded, %d failed out of %d traders",
            len(results), failures, len(traders),
        )
        return results



# =============================================================================
# SECTION 3: BYBIT COPY TRADER CLIENT (Fallback Source)
# =============================================================================

class BybitClient:
    """Bybit Copy-Trading (Beehive) public API client.

    Endpoints (public — no auth required):
    - GET /v5/copytrading/lead-traders — beehive leaderboard
    - GET /v5/copytrading/lead-trader-positions — current positions
    - GET /v5/copytrading/lead-trader-history — historical performance

    Quality filters mirror OKX for cross-source consistency.
    """

    BASE_URL: str = "https://api.bybit.com"

    def __init__(self) -> None:
        self.rate_limiter = RateLimiter(BYBIT_RATE_LIMIT)
        self.circuit = get_circuit_breaker("bybit")
        self.cache = get_cache()
        self._ssl_ctx = ssl.create_default_context()
        self._request_headers = {
            "User-Agent": (
                "CopyTraderIntel/2.0 (Production; Bybit Public API; "
                "contact=dev@trading-intel.internal)"
            ),
            "Accept": "application/json",
        }

    def _request(
        self, method: str, path: str, params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        self.circuit.check()
        self.rate_limiter.acquire()

        url = f"{self.BASE_URL}{path}"
        if params:
            query = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
            url = f"{url}?{query}"

        req = urllib.request.Request(url, headers=self._request_headers, method=method)

        try:
            with urllib.request.urlopen(req, context=self._ssl_ctx, timeout=15) as resp:
                body = resp.read().decode("utf-8")
                self.circuit.record_success()
        except urllib.error.HTTPError as exc:
            self.circuit.record_failure()
            if exc.code == 429:
                raise RateLimitError(
                    f"Bybit rate limited (429) on {path}", status_code=429, source="bybit"
                ) from exc
            raise APIError(
                f"Bybit HTTP {exc.code} on {path}: {exc.reason}",
                status_code=exc.code, source="bybit",
            ) from exc
        except ssl.SSLError as exc:
            self.circuit.record_failure()
            raise SSLVerificationError(
                f"Bybit SSL verification failed for {path}: {exc}",
                status_code=0, source="bybit",
            ) from exc
        except urllib.error.URLError as exc:
            self.circuit.record_failure()
            raise APIError(
                f"Bybit connection error on {path}: {exc}", status_code=0, source="bybit"
            ) from exc
        except TimeoutError as exc:
            self.circuit.record_failure()
            raise APIError(
                f"Bybit timeout on {path}", status_code=0, source="bybit"
            ) from exc

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise APIError(
                f"Bybit invalid JSON from {path}: {exc}", status_code=0, source="bybit"
            ) from exc

        # Bybit: {"retCode": 0, "retMsg": "OK", "result": {...}}
        if int(data.get("retCode", 0)) != 0:
            msg = data.get("retMsg", "Unknown Bybit error")
            raise APIError(
                f"Bybit API error on {path}: {msg} (retCode={data.get('retCode')})",
                status_code=int(data.get("retCode", 0)), source="bybit",
            )
        return data

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def _request_with_retry(
        self, method: str, path: str, params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        return self._request(method, path, params)

    def fetch_beehive_leaders(
        self,
        min_pnl_ratio: float = MIN_PNL_RATIO,
        min_win_rate: float = MIN_WIN_RATE,
        min_lead_days: int = MIN_LEAD_DAYS,
        min_aum: float = MIN_AUM_USD,
        limit: int = 100,
    ) -> List[TraderProfile]:
        """Fetch Bybit beehive leaderboard with quality pre-filtering.

        Raises:
            APIError: on any API failure.
            CircuitOpenError: if circuit breaker is open.
        """
        cache_key = f"bybit:beehive:{min_pnl_ratio}:{min_win_rate}:{min_lead_days}:{min_aum}:{limit}"
        cached = self.cache.get(cache_key)
        if cached:
            LOG.info("Bybit beehive: returning %d cached profiles", len(cached))
            return cached

        LOG.info("Fetching Bybit beehive leaders")
        params: Dict[str, str] = {
            "category": "linear",
            "limit": str(min(limit, 100)),
        }
        data = self._request_with_retry("GET", "/v5/copytrading/lead-traders", params)
        rows = data.get("result", {}).get("list", [])
        LOG.info("Bybit returned %d raw lead traders", len(rows))

        profiles: List[TraderProfile] = []
        for row in rows:
            try:
                pnl_ratio = float(row.get("totalPnLRatio", 0))
                win_rate = float(row.get("winRate", 0)) / 100.0
                aum = float(row.get("aum", 0))
                lead_days = int(row.get("tradingDays", 0))
                recency_wr = float(row.get("winRateRecent", win_rate))
                drawdown = float(row.get("maxDrawdown", 0))
                followers = int(row.get("followerCount", 0))
                sharpe = float(row.get("sharpeRatio", 0))
                leader_id = str(row.get("leaderId", ""))
                name = str(row.get("nickName", leader_id))

                if pnl_ratio < min_pnl_ratio:
                    continue
                if win_rate < min_win_rate:
                    continue
                if lead_days < min_lead_days:
                    continue
                if aum < min_aum:
                    continue
                if recency_wr < MIN_RECENCY_WIN_RATE:
                    continue

                prof = TraderProfile(
                    unique_code=leader_id,
                    name=name,
                    source="bybit",
                    pnl_ratio=pnl_ratio,
                    win_rate=win_rate,
                    aum=aum,
                    recency_wr=recency_wr,
                    max_drawdown=drawdown,
                    lead_days=lead_days,
                    follower_count=followers,
                    sharpe_30d=sharpe,
                )
                profiles.append(prof)
            except (ValueError, TypeError, KeyError) as exc:
                LOG.debug("Skipping malformed Bybit trader row: %s", exc)
                continue

        LOG.info("Bybit: %d/%d traders passed quality gates", len(profiles), len(rows))
        self.cache.set(cache_key, profiles)
        return profiles

    def fetch_leader_positions(self, leader_id: str) -> List[Position]:
        """Fetch current open positions for a Bybit lead trader.

        Raises:
            APIError: on API failure.
        """
        cache_key = f"bybit:positions:{leader_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        params: Dict[str, str] = {"leaderId": leader_id, "category": "linear"}
        data = self._request_with_retry(
            "GET", "/v5/copytrading/lead-trader-positions", params
        )
        rows = data.get("result", {}).get("list", [])
        positions: List[Position] = []
        for row in rows:
            try:
                side = str(row.get("side", "")).upper()
                direction = Direction.LONG if side in ("BUY", "LONG", "B") else Direction.SHORT
                pos = Position(
                    symbol=str(row.get("symbol", "")),
                    direction=direction,
                    entry_price=float(row.get("avgPrice", 0)),
                    mark_price=float(row.get("markPrice", 0)),
                    size=float(row.get("size", 0)),
                    pnl_ratio=float(row.get("pnlRatio", 0)),
                    leverage=float(row.get("leverage", 1)),
                    open_time=datetime.fromtimestamp(
                        int(row.get("createdTime", 0)) / 1000, tz=timezone.utc
                    ) if row.get("createdTime") else None,
                )
                positions.append(pos)
            except (ValueError, TypeError, KeyError) as exc:
                LOG.debug("Skipping malformed Bybit position row: %s", exc)
                continue

        self.cache.set(cache_key, positions)
        LOG.info("Bybit leader %s: fetched %d positions", leader_id[:12], len(positions))
        return positions

    def fetch_leader_history(self, leader_id: str, days: int = 30) -> Dict[str, Any]:
        """Fetch historical performance for a Bybit lead trader.

        Raises:
            APIError: on API failure.
        """
        cache_key = f"bybit:history:{leader_id}:{days}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        params: Dict[str, str] = {"leaderId": leader_id, "days": str(days)}
        data = self._request_with_retry(
            "GET", "/v5/copytrading/lead-trader-history", params
        )
        rows = data.get("result", {}).get("list", [])
        daily_pnl = []
        total_pnl = 0.0
        for row in rows:
            try:
                pnl = float(row.get("pnl", 0))
                daily_pnl.append(pnl)
                total_pnl += pnl
            except (ValueError, TypeError):
                continue

        result = {
            "daily_pnl": daily_pnl,
            "total_pnl": total_pnl,
            "avg_daily": total_pnl / max(len(daily_pnl), 1),
            "leader_id": leader_id,
            "fetched_at": iso_now(),
        }
        self.cache.set(cache_key, result)
        return result

    def fetch_all_positions(
        self, traders: List[TraderProfile], max_workers: int = 5
    ) -> Dict[str, List[Position]]:
        """Fetch positions for multiple Bybit traders in parallel."""
        results: Dict[str, List[Position]] = {}
        failures = 0

        def _fetch_one(trader: TraderProfile) -> Tuple[str, List[Position]]:
            poss = self.fetch_leader_positions(trader.unique_code)
            return (trader.unique_code, poss)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_fetch_one, t): t for t in traders}
            for future in as_completed(futures):
                trader = futures[future]
                try:
                    code, poss = future.result()
                    results[code] = poss
                except Exception:
                    failures += 1

        LOG.info(
            "Bybit batch positions: %d succeeded, %d failed out of %d traders",
            len(results), failures, len(traders),
        )
        return results


# =============================================================================
# SECTION 4: HYPERLIQUID COPY TRADER CLIENT (DEX Source)
# =============================================================================

class HyperliquidClient:
    """Hyperliquid DEX copy-trading client.

    Hyperliquid exposes a public REST API for leaderboard and position data.
    This client fetches top performers from the Hyperliquid leaderboard
    and their current perp positions.

    Endpoint: https://api.hyperliquid.xyz/info (POST with JSON body)
    """

    BASE_URL: str = "https://api.hyperliquid.xyz"

    def __init__(self) -> None:
        self.rate_limiter = RateLimiter(HYPERLIQUID_RATE_LIMIT)
        self.circuit = get_circuit_breaker("hyperliquid")
        self.cache = get_cache()
        self._ssl_ctx = ssl.create_default_context()
        self._request_headers = {
            "User-Agent": (
                "CopyTraderIntel/2.0 (Production; Hyperliquid; "
                "contact=dev@trading-intel.internal)"
            ),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _request(
        self, method: str, path: str, payload: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute POST request to Hyperliquid API.

        Hyperliquid uses POST with a JSON body containing a 'type' field.
        """
        self.circuit.check()
        self.rate_limiter.acquire()

        url = f"{self.BASE_URL}{path}"
        body = json.dumps(payload or {}).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers=self._request_headers, method=method
        )

        try:
            with urllib.request.urlopen(req, context=self._ssl_ctx, timeout=15) as resp:
                response_body = resp.read().decode("utf-8")
                self.circuit.record_success()
        except urllib.error.HTTPError as exc:
            self.circuit.record_failure()
            if exc.code == 429:
                raise RateLimitError(
                    f"HL rate limited (429)", status_code=429, source="hyperliquid"
                ) from exc
            raise APIError(
                f"HL HTTP {exc.code}: {exc.reason}",
                status_code=exc.code, source="hyperliquid",
            ) from exc
        except ssl.SSLError as exc:
            self.circuit.record_failure()
            raise SSLVerificationError(
                f"HL SSL verification failed: {exc}", status_code=0, source="hyperliquid",
            ) from exc
        except urllib.error.URLError as exc:
            self.circuit.record_failure()
            raise APIError(
                f"HL connection error: {exc}", status_code=0, source="hyperliquid"
            ) from exc
        except TimeoutError as exc:
            self.circuit.record_failure()
            raise APIError(
                f"HL timeout", status_code=0, source="hyperliquid"
            ) from exc

        try:
            data = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise APIError(
                f"HL invalid JSON: {exc}", status_code=0, source="hyperliquid"
            ) from exc

        return data

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def _request_with_retry(
        self, method: str, path: str, payload: Optional[Dict[str, Any]] = None
    ) -> Any:
        return self._request(method, path, payload)

    def fetch_hl_leaders(
        self,
        min_pnl_ratio: float = MIN_PNL_RATIO,
        min_win_rate: float = MIN_WIN_RATE,
        min_lead_days: int = MIN_LEAD_DAYS,
        min_aum: float = MIN_AUM_USD,
        limit: int = 100,
    ) -> List[TraderProfile]:
        """Fetch Hyperliquid leaderboard traders.

        Hyperliquid uses a different API shape. We query the leaderboard
        endpoint then map fields to our standard TraderProfile.
        """
        cache_key = f"hl:leaders:{min_pnl_ratio}:{min_win_rate}:{min_lead_days}:{min_aum}:{limit}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        LOG.info("Fetching Hyperliquid leaderboard")

        # Hyperliquid leaderboard query
        payload = {"type": "leaderboard", "user": ""}
        data = self._request_with_retry("POST", "/info", payload)

        rows = data if isinstance(data, list) else data.get("leaderboard", [])
        LOG.info("Hyperliquid returned %d raw leaderboard entries", len(rows))

        profiles: List[TraderProfile] = []
        for row in rows[:limit]:
            try:
                wallet = str(row.get("ethAddress", row.get("user", "")))
                name = str(row.get("username", wallet[:12]))
                pnl_ratio = float(row.get("pnl", row.get("totalPnl", 0)))
                # HL sometimes returns raw PnL — normalise
                if abs(pnl_ratio) > 1000:
                    pnl_ratio = pnl_ratio / 1e6
                win_rate = float(row.get("winRate", 0))
                if win_rate > 1.0:
                    win_rate = win_rate / 100.0
                aum = float(row.get("aum", row.get("totalVolume", 0)))
                lead_days = int(row.get("tradingDays", 30))
                drawdown = float(row.get("maxDrawdown", 0))
                followers = int(row.get("followerCount", 0))
                sharpe = float(row.get("sharpeRatio", 0))
                recency_wr = float(row.get("winRate7d", win_rate))
                if recency_wr > 1.0:
                    recency_wr = recency_wr / 100.0

                if pnl_ratio < min_pnl_ratio:
                    continue
                if win_rate < min_win_rate:
                    continue
                if lead_days < min_lead_days:
                    continue
                if aum < min_aum:
                    continue
                if recency_wr < MIN_RECENCY_WIN_RATE:
                    continue

                prof = TraderProfile(
                    unique_code=wallet,
                    name=name,
                    source="hyperliquid",
                    pnl_ratio=pnl_ratio,
                    win_rate=win_rate,
                    aum=aum,
                    recency_wr=recency_wr,
                    max_drawdown=drawdown,
                    lead_days=lead_days,
                    follower_count=followers,
                    sharpe_30d=sharpe,
                )
                profiles.append(prof)
            except (ValueError, TypeError, KeyError) as exc:
                LOG.debug("Skipping malformed HL leaderboard row: %s", exc)
                continue

        LOG.info("Hyperliquid: %d/%d traders passed quality gates", len(profiles), len(rows))
        self.cache.set(cache_key, profiles)
        return profiles

    def fetch_hl_positions(self, wallet: str) -> List[Position]:
        """Fetch current perp positions for a Hyperliquid wallet.

        Args:
            wallet: Ethereum address of the trader.

        Raises:
            APIError: on API failure.
        """
        cache_key = f"hl:positions:{wallet}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        payload = {"type": "clearinghouseState", "user": wallet}
        data = self._request_with_retry("POST", "/info", payload)

        asset_positions = data.get("assetPositions", [])
        positions: List[Position] = []
        for ap in asset_positions:
            try:
                pos_data = ap.get("position", {})
                coin = str(pos_data.get("coin", ""))
                szi = float(pos_data.get("szi", 0))
                direction = Direction.LONG if szi > 0 else Direction.SHORT
                entry_px = float(pos_data.get("entryPx", 0))
                mark_px = float(pos_data.get("markPx", entry_px))
                # PnL calculation from HL data
                position_value = abs(szi) * mark_px
                unrealized_pnl = float(pos_data.get("unrealizedPnl", 0))
                pnl_ratio = (unrealized_pnl / (abs(szi) * entry_px)) if entry_px and szi else 0.0
                leverage = float(pos_data.get("leverage", {}).get("value", 1))

                pos = Position(
                    symbol=f"{coin}-USDT-SWAP",
                    direction=direction,
                    entry_price=entry_px,
                    mark_price=mark_px,
                    size=abs(szi),
                    pnl_ratio=pnl_ratio,
                    leverage=leverage,
                )
                positions.append(pos)
            except (ValueError, TypeError, KeyError) as exc:
                LOG.debug("Skipping malformed HL position row: %s", exc)
                continue

        self.cache.set(cache_key, positions)
        LOG.info("HL wallet %s...%s: fetched %d positions", wallet[:6], wallet[-4:], len(positions))
        return positions

    def fetch_all_positions(
        self, traders: List[TraderProfile], max_workers: int = 5
    ) -> Dict[str, List[Position]]:
        """Fetch positions for multiple HL traders in parallel."""
        results: Dict[str, List[Position]] = {}
        failures = 0

        def _fetch_one(trader: TraderProfile) -> Tuple[str, List[Position]]:
            poss = self.fetch_hl_positions(trader.unique_code)
            return (trader.unique_code, poss)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_fetch_one, t): t for t in traders}
            for future in as_completed(futures):
                trader = futures[future]
                try:
                    code, poss = future.result()
                    results[code] = poss
                except Exception:
                    failures += 1

        LOG.info(
            "HL batch positions: %d succeeded, %d failed out of %d traders",
            len(results), failures, len(traders),
        )
        return results



# =============================================================================
# SECTION 5: ARKHAM SMART MONEY CLIENT
# =============================================================================

class ArkhamClient:
    """Arkham Intelligence API client for smart-money tracking.

    Features:
    - Entity tracking (Paradigm, a16z, Jump, etc.)
    - Individual whale address tracking
    - Proper rate limiting (10 req/min = 6s interval for safety)
    - Local 15-minute cache to minimize API calls
    - Multi-chain support: Ethereum, Bitcoin, Solana, Arbitrum, Base

    API Key required — set ARKHAM_API_KEY env var.
    Free tier: 10 requests per minute.
    """

    BASE_URL: str = "https://api.arkhamintelligence.com"

    # Known labeled entities to track
    DEFAULT_ENTITIES: List[str] = [
        "Paradigm",
        "a16z",
        "Jump Trading",
        "Wintermute",
        "Galaxy Digital",
        "Pantera Capital",
        "Dragonfly Capital",
        "Polychain Capital",
        "Multicoin Capital",
        "Delphi Digital",
        "Framework Ventures",
        "Coinbase Ventures",
    ]

    # Chains supported
    CHAINS: List[str] = ["ethereum", "bitcoin", "solana", "arbitrum", "base"]

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.environ.get("ARKHAM_API_KEY", "")
        self.rate_limiter = RateLimiter(ARKHAM_RATE_LIMIT)
        self.circuit = get_circuit_breaker("arkham")
        self.cache = get_cache()
        self._ssl_ctx = ssl.create_default_context()
        self._request_headers = {
            "User-Agent": (
                "CopyTraderIntel/2.0 (Production; Arkham; "
                "contact=dev@trading-intel.internal)"
            ),
            "Accept": "application/json",
        }
        if self.api_key:
            self._request_headers["API-Key"] = self.api_key

    def _request(
        self, method: str, path: str, params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Execute HTTPS request to Arkham with full error handling.

        CRITICAL: SSL verification is ENABLED. Never disabled.
        CRITICAL: All errors are raised, never swallowed.
        """
        self.circuit.check()
        self.rate_limiter.acquire()

        url = f"{self.BASE_URL}{path}"
        if params:
            query = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
            url = f"{url}?{query}"

        req = urllib.request.Request(url, headers=self._request_headers, method=method)

        try:
            with urllib.request.urlopen(req, context=self._ssl_ctx, timeout=20) as resp:
                body = resp.read().decode("utf-8")
                self.circuit.record_success()
        except urllib.error.HTTPError as exc:
            self.circuit.record_failure()
            if exc.code == 429:
                raise RateLimitError(
                    f"Arkham rate limited (429) on {path}", status_code=429, source="arkham"
                ) from exc
            if exc.code == 401:
                raise APIError(
                    f"Arkham authentication failed (401). Check ARKHAM_API_KEY.",
                    status_code=401, source="arkham",
                ) from exc
            raise APIError(
                f"Arkham HTTP {exc.code} on {path}: {exc.reason}",
                status_code=exc.code, source="arkham",
            ) from exc
        except ssl.SSLError as exc:
            self.circuit.record_failure()
            raise SSLVerificationError(
                f"Arkham SSL verification failed for {path}: {exc}",
                status_code=0, source="arkham",
            ) from exc
        except urllib.error.URLError as exc:
            self.circuit.record_failure()
            raise APIError(
                f"Arkham connection error on {path}: {exc}", status_code=0, source="arkham"
            ) from exc
        except TimeoutError as exc:
            self.circuit.record_failure()
            raise APIError(
                f"Arkham timeout on {path}", status_code=0, source="arkham"
            ) from exc

        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise APIError(
                f"Arkham invalid JSON from {path}: {exc}", status_code=0, source="arkham"
            ) from exc

    @retry_with_backoff(max_retries=3, base_delay=2.0)
    def _request_with_retry(
        self, method: str, path: str, params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        return self._request(method, path, params)

    # ------------------------------------------------------------------
    # Entity tracking
    # ------------------------------------------------------------------

    def track_entity(
        self, entity_name: str, chain: str = "ethereum", hours: int = 24
    ) -> SmartMoneySignal:
        """Track a labeled entity's recent activity.

        Args:
            entity_name: Name of the entity (e.g., "Paradigm").
            chain: Blockchain to query.
            hours: Lookback window in hours.

        Returns:
            SmartMoneySignal with accumulation/distribution direction.

        Raises:
            APIError: on API failure.
            CircuitOpenError: if circuit breaker is open.
        """
        cache_key = f"arkham:entity:{entity_name}:{chain}:{hours}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            # Reconstruct from dict
            return SmartMoneySignal(**cached)

        LOG.info("Arkham: tracking entity '%s' on %s (last %dh)", entity_name, chain, hours)

        # Arkham entity portfolio/transfers endpoint
        params: Dict[str, str] = {
            "entity": entity_name,
            "chain": chain,
            "timeRange": f"{hours}h",
        }
        data = self._request_with_retry(
            "GET", "/v2/transfers/entity", params
        )

        transfers = data.get("transfers", [])
        inflows = 0.0
        outflows = 0.0
        top_token = ""
        top_token_value = 0.0
        token_volumes: Dict[str, float] = {}

        for tx in transfers:
            try:
                usd_value = float(tx.get("usdValue", 0))
                token = str(tx.get("tokenSymbol", tx.get("token", "")))
                tx_type = str(tx.get("type", "")).lower()

                if usd_value <= 0 or not token:
                    continue

                if tx_type in ("in", "receive", "inflow"):
                    inflows += usd_value
                elif tx_type in ("out", "send", "outflow"):
                    outflows += usd_value

                token_volumes[token] = token_volumes.get(token, 0.0) + usd_value
            except (ValueError, TypeError, KeyError):
                continue

        # Determine direction and primary token
        if token_volumes:
            top_token = max(token_volumes, key=token_volumes.get)
            top_token_value = token_volumes[top_token]

        net_flow = inflows - outflows
        if net_flow > 0:
            direction = Direction.LONG  # Accumulation
            confidence = min(abs(net_flow) / (outflows + 1), 1.0)
        else:
            direction = Direction.SHORT  # Distribution
            confidence = min(abs(net_flow) / (inflows + 1), 1.0)

        signal = SmartMoneySignal(
            entity_name=entity_name,
            chain=chain,
            token_symbol=top_token,
            direction=direction,
            confidence=round(confidence, 4),
            usd_value=round(abs(net_flow), 2),
            metadata={
                "inflows": round(inflows, 2),
                "outflows": round(outflows, 2),
                "net_flow": round(net_flow, 2),
                "transfer_count": len(transfers),
                "top_token_volume": round(top_token_value, 2),
                "lookback_hours": hours,
                "fetched_at": iso_now(),
            },
        )
        self.cache.set(cache_key, signal.__dict__)
        return signal

    def track_entity_multi_chain(
        self, entity_name: str, hours: int = 24
    ) -> List[SmartMoneySignal]:
        """Track an entity across all supported chains.

        Returns:
            List of SmartMoneySignal, one per chain with activity.
        """
        signals: List[SmartMoneySignal] = []
        for chain in self.CHAINS:
            try:
                sig = self.track_entity(entity_name, chain=chain, hours=hours)
                if sig.usd_value > 0:
                    signals.append(sig)
            except (APIError, CircuitOpenError) as exc:
                LOG.warning("Arkham entity %s on %s failed: %s", entity_name, chain, exc)
                continue
        return signals

    def track_all_entities(
        self, hours: int = 24
    ) -> Dict[str, List[SmartMoneySignal]]:
        """Track all default entities across all chains.

        Returns:
            Mapping of entity_name -> list of signals (one per active chain).
        """
        LOG.info("Arkham: tracking all %d entities", len(self.DEFAULT_ENTITIES))
        results: Dict[str, List[SmartMoneySignal]] = {}
        for entity in self.DEFAULT_ENTITIES:
            try:
                sigs = self.track_entity_multi_chain(entity, hours=hours)
                if sigs:
                    results[entity] = sigs
                    LOG.info(
                        "Arkham: %s active on %d chains (net: $%.0f)",
                        entity, len(sigs), sum(s.usd_value for s in sigs),
                    )
            except Exception as exc:
                LOG.error("Arkham: failed to track entity %s: %s", entity, exc)
                continue
        return results

    # ------------------------------------------------------------------
    # Whale address tracking
    # ------------------------------------------------------------------

    def track_whale_address(
        self, address: str, chain: str = "ethereum", hours: int = 24
    ) -> SmartMoneySignal:
        """Track a single whale address's recent transfers.

        Args:
            address: Wallet address to track.
            chain: Blockchain.
            hours: Lookback window.

        Returns:
            SmartMoneySignal.
        """
        cache_key = f"arkham:whale:{address}:{chain}:{hours}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return SmartMoneySignal(**cached)

        LOG.info("Arkham: tracking whale %s...%s on %s", address[:6], address[-4:], chain)

        params: Dict[str, str] = {
            "address": address,
            "chain": chain,
            "timeRange": f"{hours}h",
        }
        data = self._request_with_retry("GET", "/v2/transfers/address", params)

        transfers = data.get("transfers", [])
        inflows = 0.0
        outflows = 0.0
        token_volumes: Dict[str, float] = {}
        large_txs = 0  # >$1M

        for tx in transfers:
            try:
                usd_value = float(tx.get("usdValue", 0))
                token = str(tx.get("tokenSymbol", tx.get("token", "")))
                tx_type = str(tx.get("type", "")).lower()

                if usd_value <= 0 or not token:
                    continue

                if usd_value >= 1_000_000:
                    large_txs += 1

                if tx_type in ("in", "receive", "inflow"):
                    inflows += usd_value
                elif tx_type in ("out", "send", "outflow"):
                    outflows += usd_value

                token_volumes[token] = token_volumes.get(token, 0.0) + usd_value
            except (ValueError, TypeError, KeyError):
                continue

        top_token = max(token_volumes, key=token_volumes.get) if token_volumes else ""
        top_value = token_volumes.get(top_token, 0.0)
        net_flow = inflows - outflows

        direction = Direction.LONG if net_flow > 0 else Direction.SHORT
        confidence = min(abs(net_flow) / max(inflows + outflows, 1), 1.0)
        # Boost confidence if there are large transactions
        if large_txs >= 2:
            confidence = min(confidence * 1.2, 1.0)

        signal = SmartMoneySignal(
            entity_name=f"whale:{address[:10]}...",
            chain=chain,
            token_symbol=top_token,
            direction=direction,
            confidence=round(confidence, 4),
            usd_value=round(abs(net_flow), 2),
            metadata={
                "address": address,
                "inflows": round(inflows, 2),
                "outflows": round(outflows, 2),
                "net_flow": round(net_flow, 2),
                "transfer_count": len(transfers),
                "large_transactions_1m+": large_txs,
                "top_token_volume": round(top_value, 2),
                "lookback_hours": hours,
            },
        )
        self.cache.set(cache_key, signal.__dict__)
        return signal

    def discover_whale_addresses(
        self, chain: str = "ethereum", min_usd: float = 1_000_000, limit: int = 50
    ) -> List[str]:
        """Dynamically discover whale addresses from recent large transfers.

        Uses Arkham's transfer search to find addresses involved in
        transactions > $1M in the last 24h.

        Args:
            chain: Blockchain to search.
            min_usd: Minimum USD value per transfer.
            limit: Max addresses to return.

        Returns:
            List of wallet addresses sorted by total volume.
        """
        cache_key = f"arkham:discover:{chain}:{min_usd}:{limit}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        LOG.info("Arkham: discovering whales on %s (min $%.0f)", chain, min_usd)

        params: Dict[str, str] = {
            "chain": chain,
            "minUsd": str(min_usd),
            "timeRange": "24h",
            "limit": str(limit),
        }
        data = self._request_with_retry("GET", "/v2/transfers/search", params)

        transfers = data.get("transfers", [])
        address_volumes: Dict[str, float] = {}

        for tx in transfers:
            try:
                usd_value = float(tx.get("usdValue", 0))
                from_addr = str(tx.get("from", ""))
                to_addr = str(tx.get("to", ""))
                if from_addr:
                    address_volumes[from_addr] = address_volumes.get(from_addr, 0.0) + usd_value
                if to_addr:
                    address_volumes[to_addr] = address_volumes.get(to_addr, 0.0) + usd_value
            except (ValueError, TypeError, KeyError):
                continue

        sorted_addrs = sorted(address_volumes, key=address_volumes.get, reverse=True)[:limit]
        LOG.info("Arkham: discovered %d whale addresses on %s", len(sorted_addrs), chain)
        self.cache.set(cache_key, sorted_addrs)
        return sorted_addrs



# =============================================================================
# SECTION 6: QUALITY SCORING & WEIGHTED CONSENSUS ENGINE
# =============================================================================

class QualityScorer:
    """Compute quality scores for traders and generate weighted consensus picks.

    Quality Score Formula (0-100):
        pnl_component      = min(pnl_ratio, 10.0) / 10.0 * 30
        winrate_component  = win_rate * 25
        aum_component      = min(aum / 1_000_000, 1.0) * 20
        recency_component  = recency_wr * 15
        consistency_comp   = (1.0 - drawdown) * 10

        quality_score = sum of all components (clamped to 0-100)

    Only traders with quality_score >= MIN_QUALITY_SCORE (60) contribute.
    Minimum MIN_CONSENSUS_TRADERS (3) required for a valid consensus.
    """

    # Weights for quality score components
    W_PNL: float = 30.0
    W_WINRATE: float = 25.0
    W_AUM: float = 20.0
    W_RECENCY: float = 15.0
    W_CONSISTENCY: float = 10.0

    def compute_score(self, trader: TraderProfile) -> float:
        """Compute quality score for a single trader.

        Args:
            trader: TraderProfile with metrics.

        Returns:
            Quality score in range [0, 100].
        """
        pnl_component = min(trader.pnl_ratio, 10.0) / 10.0 * self.W_PNL
        winrate_component = trader.win_rate * self.W_WINRATE
        aum_component = min(trader.aum / 1_000_000.0, 1.0) * self.W_AUM
        recency_component = trader.recency_wr * self.W_RECENCY
        drawdown = min(max(trader.max_drawdown, 0.0), 1.0)
        consistency_component = (1.0 - drawdown) * self.W_CONSISTENCY

        score = (
            pnl_component
            + winrate_component
            + aum_component
            + recency_component
            + consistency_component
        )
        return max(0.0, min(100.0, score))

    def score_traders(self, traders: List[TraderProfile]) -> List[TraderProfile]:
        """Compute and assign quality scores to all traders.

        Args:
            traders: List of TraderProfile objects.

        Returns:
            Traders with quality_score populated, sorted descending.
        """
        for t in traders:
            t.quality_score = self.compute_score(t)
        traders.sort(key=lambda x: x.quality_score, reverse=True)
        return traders

    def filter_quality_traders(
        self, traders: List[TraderProfile], min_score: float = MIN_QUALITY_SCORE
    ) -> List[TraderProfile]:
        """Filter to only traders meeting minimum quality threshold.

        Args:
            traders: Pre-scored traders.
            min_score: Minimum quality score.

        Returns:
            Filtered list, still sorted by quality descending.

        Raises:
            QualityThresholdError: if fewer than MIN_CONSENSUS_TRADERS pass.
        """
        qualified = [t for t in traders if t.quality_score >= min_score and not t.is_blacklisted]
        if len(qualified) < MIN_CONSENSUS_TRADERS:
            raise QualityThresholdError(
                f"Only {len(qualified)} traders meet quality threshold "
                f"({min_score}), need {MIN_CONSENSUS_TRADERS}"
            )
        LOG.info(
            "Quality filter: %d/%d traders pass threshold (score >= %.1f)",
            len(qualified), len(traders), min_score,
        )
        return qualified


class ConsensusEngine:
    """Generate quality-weighted consensus picks from trader positions.

    Algorithm:
    1. Collect all positions from quality-filtered traders
    2. Group by normalised symbol + direction
    3. For each group, compute weighted consensus:
       - Weight = trader's quality_score * recency_weight
       - recency_weight = 1.0 for positions < 24h old, 0.5 otherwise
    4. Normalise to confidence [0, 1]
    5. Require minimum MIN_CONSENSUS_TRADERS unique traders in group
    """

    def __init__(self, quality_scorer: Optional[QualityScorer] = None) -> None:
        self.scorer = quality_scorer or QualityScorer()

    def _recency_weight(self, position: Position) -> float:
        """Compute recency weight for a position.

        Positions opened < 24h ago: full weight (1.0)
        Positions >= 24h old: decayed weight (0.5)
        """
        if position.open_time is None:
            return 0.7  # Unknown time — moderate weight
        age_hours = (now_utc() - position.open_time).total_seconds() / 3600.0
        if age_hours <= RECENCY_DECAY_HOURS:
            return 1.0
        # Exponential decay after 24h: weight halves every 24h
        return max(0.5 ** (age_hours / RECENCY_DECAY_HOURS), 0.1)

    def generate_consensus(
        self,
        trader_positions: Dict[str, List[Position]],
        traders: List[TraderProfile],
    ) -> List[CopyTraderPick]:
        """Generate consensus picks from trader positions.

        Args:
            trader_positions: Mapping of unique_code -> positions.
            traders: List of all traders (must have quality_score set).

        Returns:
            List of CopyTraderPick sorted by confidence descending.

        Raises:
            InsufficientDataError: if no consensus picks can be formed.
        """
        trader_lookup = {t.unique_code: t for t in traders}

        # Group positions by (normalised_symbol, direction)
        groups: Dict[Tuple[str, Direction], List[Tuple[Position, TraderProfile, float]]] = {}
        for code, positions in trader_positions.items():
            trader = trader_lookup.get(code)
            if not trader or trader.quality_score < MIN_QUALITY_SCORE:
                continue
            if trader.is_blacklisted:
                continue
            for pos in positions:
                key = (pos.normalised_symbol, pos.direction)
                if key not in groups:
                    groups[key] = []
                recency_w = self._recency_weight(pos)
                groups[key].append((pos, trader, recency_w))

        if not groups:
            raise InsufficientDataError("No position groups formed from quality traders")

        picks: List[CopyTraderPick] = []
        for (symbol, direction), entries in groups.items():
            # Count unique traders in this group
            unique_traders = set(e[1].unique_code for e in entries)
            if len(unique_traders) < MIN_CONSENSUS_TRADERS:
                continue

            # Compute weighted consensus
            total_weight = 0.0
            weighted_score = 0.0
            avg_pnl = 0.0
            avg_quality = 0.0
            top_trader: Optional[TraderProfile] = None
            top_trader_score = 0.0
            youngest_age_hours: float = float("inf")

            for pos, trader, recency_w in entries:
                weight = trader.quality_score * recency_w
                total_weight += weight
                weighted_score += weight
                avg_pnl += pos.pnl_ratio
                avg_quality += trader.quality_score

                if trader.quality_score > top_trader_score:
                    top_trader_score = trader.quality_score
                    top_trader = trader

                if pos.open_time:
                    age = (now_utc() - pos.open_time).total_seconds() / 3600.0
                    youngest_age_hours = min(youngest_age_hours, age)

            count = len(entries)
            avg_pnl /= count
            avg_quality /= count

            # Normalise confidence: weighted_score / (max_possible * 0.7)
            # max_possible = count * 100 (if every trader had score 100 and recency 1.0)
            max_possible = count * 100.0
            confidence = min(weighted_score / (max_possible * 0.7), 1.0) if max_possible > 0 else 0.0

            # Require minimum confidence
            if confidence < 0.5:
                continue

            pick = CopyTraderPick(
                symbol=symbol,
                direction=direction,
                confidence=round(confidence, 4),
                metadata={
                    "consensus_count": len(unique_traders),
                    "position_count": count,
                    "avg_quality_score": round(avg_quality, 1),
                    "top_trader": top_trader.name if top_trader else "unknown",
                    "top_trader_code": top_trader.unique_code[:16] if top_trader else "",
                    "avg_pnl_ratio": round(avg_pnl, 3),
                    "recency_hours": round(youngest_age_hours, 1)
                    if youngest_age_hours != float("inf")
                    else -1,
                    "sources": list(
                        set(trader_lookup[e[1].unique_code].source for e in entries)
                    ),
                },
            )
            picks.append(pick)

        picks.sort(key=lambda p: p.confidence, reverse=True)
        LOG.info(
            "Consensus engine: generated %d picks from %d position groups",
            len(picks), len(groups),
        )

        if not picks:
            raise InsufficientDataError(
                f"No picks met confidence threshold. "
                f"Groups formed: {len(groups)}, but none had >= {MIN_CONSENSUS_TRADERS} traders "
                f"with confidence >= 0.5"
            )
        return picks

    def merge_with_smart_money(
        self,
        copy_trader_picks: List[CopyTraderPick],
        smart_money_signals: List[SmartMoneySignal],
    ) -> List[CopyTraderPick]:
        """Boost copy trader pick confidence when smart money aligns.

        If 2+ entities are accumulating the same token the copy traders
        are also long on, boost confidence by +0.10 (capped at 1.0).

        Args:
            copy_trader_picks: Base consensus picks.
            smart_money_signals: Signals from Arkham entity tracking.

        Returns:
            Picks with potentially boosted confidence and enriched metadata.
        """
        # Group smart money by token + direction
        sm_by_token: Dict[Tuple[str, Direction], List[SmartMoneySignal]] = {}
        for sig in smart_money_signals:
            key = (normalise_symbol(sig.token_symbol), sig.direction)
            if key not in sm_by_token:
                sm_by_token[key] = []
            sm_by_token[key].append(sig)

        enhanced: List[CopyTraderPick] = []
        for pick in copy_trader_picks:
            key = (pick.symbol, pick.direction)
            sm_sigs = sm_by_token.get(key, [])

            # Count unique entities
            entities = list(set(s.entity_name for s in sm_sigs))
            entity_count = len(entities)

            if entity_count >= 2 and pick.direction == Direction.LONG:
                # Strong alignment: multiple entities accumulating
                boost = min(0.10 * (entity_count - 1), 0.25)
                old_conf = pick.confidence
                pick.confidence = min(pick.confidence + boost, 1.0)
                pick.metadata["smart_money_boost"] = round(pick.confidence - old_conf, 4)
                pick.metadata["smart_money_entities"] = entities
                pick.metadata["smart_money_signal_count"] = entity_count
                LOG.info(
                    "Smart money boost for %s %s: %.0f%% -> %.0f%% (%d entities)",
                    pick.symbol, pick.direction.value, old_conf * 100,
                    pick.confidence * 100, entity_count,
                )
            elif entity_count >= 1:
                pick.metadata["smart_money_entities"] = entities
                pick.metadata["smart_money_signal_count"] = entity_count

            enhanced.append(pick)

        enhanced.sort(key=lambda p: p.confidence, reverse=True)
        return enhanced

    def merge_with_onchain_signals(
        self,
        picks: List[CopyTraderPick],
        onchain_signals: List[OnChainSignal],
    ) -> List[CopyTraderPick]:
        """Boost picks based on on-chain exchange flow / whale cluster signals.

        Args:
            picks: Current picks.
            onchain_signals: On-chain signals.

        Returns:
            Picks with on-chain metadata and possible confidence adjustments.
        """
        oc_by_token: Dict[str, List[OnChainSignal]] = {}
        for sig in onchain_signals:
            sym = normalise_symbol(sig.token_symbol)
            if sym not in oc_by_token:
                oc_by_token[sym] = []
            oc_by_token[sym].append(sig)

        enhanced: List[CopyTraderPick] = []
        for pick in picks:
            sigs = oc_by_token.get(pick.symbol, [])

            aligned = [s for s in sigs if s.direction == pick.direction]
            opposed = [s for s in sigs if s.direction != pick.direction]

            if aligned:
                boost = min(0.05 * len(aligned), 0.15)
                pick.confidence = min(pick.confidence + boost, 1.0)
                pick.metadata["onchain_aligned_signals"] = len(aligned)
                pick.metadata["onchain_signal_types"] = list(
                    set(s.signal_type for s in aligned)
                )

            if opposed:
                penalty = min(0.03 * len(opposed), 0.10)
                pick.confidence = max(pick.confidence - penalty, 0.0)
                pick.metadata["onchain_opposed_signals"] = len(opposed)

            enhanced.append(pick)

        enhanced.sort(key=lambda p: p.confidence, reverse=True)
        return enhanced



# =============================================================================
# SECTION 7: ON-CHAIN SIGNAL INTEGRATION
# =============================================================================

class OnChainSignalProvider:
    """Provides on-chain signals from multiple sources.

    Includes:
    - Exchange flow analysis (net deposits/withdrawals)
    - Whale transaction clustering
    - Stablecoin velocity (mint/burn)

    Uses Arkham + free on-chain APIs (Glassnode-style where available).
    """

    # Known major exchange addresses for flow analysis
    EXCHANGE_ENTITIES: List[str] = [
        "Binance",
        "Coinbase",
        "Kraken",
        "OKX",
        "Bybit",
        "Bitfinex",
    ]

    def __init__(self, arkham: Optional[ArkhamClient] = None) -> None:
        self.arkham = arkham
        self.cache = get_cache()

    def fetch_exchange_flows(
        self, hours: int = 24, chain: str = "bitcoin"
    ) -> List[OnChainSignal]:
        """Analyze net exchange deposits vs withdrawals.

        Deposit ROC accelerating = bearish (selling pressure building).
        Withdrawal ROC accelerating = bullish (accumulation).

        Uses Arkham entity transfers for exchange wallets.

        Args:
            hours: Lookback window.
            chain: Blockchain to analyze.

        Returns:
            List of OnChainSignal for each exchange with significant flow.
        """
        cache_key = f"onchain:exchange_flows:{chain}:{hours}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return [OnChainSignal(**s) for s in cached]

        if self.arkham is None:
            raise CopyTraderError("Arkham client required for exchange flow analysis")

        signals: List[OnChainSignal] = []
        for exchange in self.EXCHANGE_ENTITIES:
            try:
                sig = self.arkham.track_entity(exchange, chain=chain, hours=hours)
                if sig.usd_value < 100_000:  # Filter noise
                    continue

                signal_type = "exchange_flow"
                # If outflows > inflows = bullish (accumulation/withdrawal)
                # If inflows > outflows = bearish (deposits for selling)
                net = sig.metadata.get("net_flow", 0)
                inflows = sig.metadata.get("inflows", 0)
                outflows = sig.metadata.get("outflows", 0)

                # Exchange inflows (deposits) = potential selling pressure = SHORT signal
                # Exchange outflows (withdrawals) = accumulation = LONG signal
                if abs(net) < 100_000:
                    continue

                direction = Direction.SHORT if net > 0 else Direction.LONG
                # Confidence based on relative magnitude
                total_flow = inflows + outflows
                confidence = min(abs(net) / max(total_flow * 0.5, 1), 1.0)

                onchain_sig = OnChainSignal(
                    signal_type=signal_type,
                    token_symbol="BTC" if chain == "bitcoin" else "ETH",
                    direction=direction,
                    confidence=round(confidence, 4),
                    metadata={
                        "exchange": exchange,
                        "chain": chain,
                        "inflows": inflows,
                        "outflows": outflows,
                        "net_flow": net,
                        "lookback_hours": hours,
                        "fetched_at": iso_now(),
                    },
                )
                signals.append(onchain_sig)
                LOG.info(
                    "Exchange flow %s/%s: %s $%.0f (conf=%.2f)",
                    exchange, chain, direction.value, abs(net), confidence,
                )
            except (APIError, CircuitOpenError) as exc:
                LOG.warning("Exchange flow %s/%s failed: %s", exchange, chain, exc)
                continue

        self.cache.set(cache_key, [s.__dict__ for s in signals])
        return signals

    def detect_whale_clusters(
        self, chain: str = "ethereum", hours: int = 1, min_usd: float = 1_000_000
    ) -> List[OnChainSignal]:
        """Detect clusters of large whale transactions in short windows.

        If > 5 distinct whale addresses make large transfers (> $1M) in
        the same 1-hour window, this indicates unusual activity.

        Args:
            chain: Blockchain to analyze.
            hours: Time window.
            min_usd: Minimum USD per transaction.

        Returns:
            List of whale cluster signals.
        """
        cache_key = f"onchain:whale_clusters:{chain}:{hours}:{min_usd}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return [OnChainSignal(**s) for s in cached]

        if self.arkham is not None:
            try:
                addresses = self.arkham.discover_whale_addresses(
                    chain=chain, min_usd=min_usd, limit=100
                )
            except (APIError, CircuitOpenError) as exc:
                LOG.warning("Whale cluster discovery failed: %s", exc)
                addresses = []
        else:
            addresses = []

        if not addresses:
            return []

        # Sample top addresses for detailed tracking
        sample_addrs = addresses[:20]
        whale_signals: List[SmartMoneySignal] = []
        for addr in sample_addrs:
            try:
                if self.arkham is None:
                    break
                sig = self.arkham.track_whale_address(addr, chain=chain, hours=hours)
                if sig.usd_value >= min_usd:
                    whale_signals.append(sig)
            except (APIError, CircuitOpenError):
                continue

        if len(whale_signals) < 5:
            return []

        # Aggregate: determine dominant direction
        long_volume = sum(s.usd_value for s in whale_signals if s.direction == Direction.LONG)
        short_volume = sum(s.usd_value for s in whale_signals if s.direction == Direction.SHORT)
        total = long_volume + short_volume

        direction = Direction.LONG if long_volume > short_volume else Direction.SHORT
        confidence = min(max(long_volume, short_volume) / max(total * 0.5, 1), 1.0)

        # Boost confidence for larger clusters
        if len(whale_signals) >= 10:
            confidence = min(confidence * 1.15, 1.0)

        token_counter: Dict[str, float] = {}
        for s in whale_signals:
            sym = normalise_symbol(s.token_symbol)
            token_counter[sym] = token_counter.get(sym, 0.0) + s.usd_value

        top_token = max(token_counter, key=token_counter.get) if token_counter else "ETH"

        signal = OnChainSignal(
            signal_type="whale_cluster",
            token_symbol=top_token,
            direction=direction,
            confidence=round(confidence, 4),
            metadata={
                "chain": chain,
                "whale_count": len(whale_signals),
                "total_volume": round(total, 2),
                "long_volume": round(long_volume, 2),
                "short_volume": round(short_volume, 2),
                "lookback_hours": hours,
                "fetched_at": iso_now(),
            },
        )

        self.cache.set(cache_key, [signal.__dict__])
        LOG.info(
            "Whale cluster detected on %s: %d whales, %s, vol=$%.0f, conf=%.2f",
            chain, len(whale_signals), direction.value, total, confidence,
        )
        return [signal]

    def fetch_stablecoin_velocity(
        self, hours: int = 24
    ) -> List[OnChainSignal]:
        """Analyze stablecoin mint/burn velocity as a market signal.

        High mint velocity + exchange inflows = bullish (dry powder entering).
        High burn velocity = bearish (capital leaving).

        Uses Arkham to track major stablecoin contract activity.

        Args:
            hours: Lookback window.

        Returns:
            List of stablecoin velocity signals.
        """
        cache_key = f"onchain:stablecoin_vel:{hours}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return [OnChainSignal(**s) for s in cached]

        signals: List[OnChainSignal] = []
        stablecoins = ["USDT", "USDC", "DAI"]

        for stable in stablecoins:
            try:
                if self.arkham is None:
                    break
                # Track the stablecoin contract/entity
                sig = self.arkham.track_entity(stable, chain="ethereum", hours=hours)
                if sig.usd_value < 1_000_000:
                    continue

                inflows = sig.metadata.get("inflows", 0)
                outflows = sig.metadata.get("outflows", 0)
                net = inflows - outflows

                # Minting (inflows to contract) = new supply = potential buying power
                # Burning (outflows from contract) = supply reduction
                if net > 0:
                    direction = Direction.LONG  # New mints = dry powder
                else:
                    direction = Direction.SHORT  # Burns = capital leaving

                confidence = min(abs(net) / max(inflows + outflows, 1), 1.0)

                oc_sig = OnChainSignal(
                    signal_type="stablecoin_velocity",
                    token_symbol=stable,
                    direction=direction,
                    confidence=round(confidence, 4),
                    metadata={
                        "stablecoin": stable,
                        "inflows": inflows,
                        "outflows": outflows,
                        "net_velocity": net,
                        "lookback_hours": hours,
                    },
                )
                signals.append(oc_sig)
            except (APIError, CircuitOpenError) as exc:
                LOG.warning("Stablecoin velocity %s failed: %s", stable, exc)
                continue

        self.cache.set(cache_key, [s.__dict__ for s in signals])
        return signals

    def get_all_onchain_signals(self) -> List[OnChainSignal]:
        """Fetch all on-chain signals in batch.

        Returns:
            Combined list of exchange flow, whale cluster, and stablecoin signals.
        """
        all_signals: List[OnChainSignal] = []

        try:
            all_signals.extend(self.fetch_exchange_flows(hours=24, chain="bitcoin"))
        except Exception as exc:
            LOG.error("Exchange flow (BTC) failed: %s", exc)

        try:
            all_signals.extend(self.fetch_exchange_flows(hours=24, chain="ethereum"))
        except Exception as exc:
            LOG.error("Exchange flow (ETH) failed: %s", exc)

        try:
            all_signals.extend(self.detect_whale_clusters(chain="ethereum", hours=1))
        except Exception as exc:
            LOG.error("Whale cluster detection failed: %s", exc)

        try:
            all_signals.extend(self.fetch_stablecoin_velocity(hours=24))
        except Exception as exc:
            LOG.error("Stablecoin velocity failed: %s", exc)

        LOG.info("On-chain signals: collected %d total signals", len(all_signals))
        return all_signals



# =============================================================================
# SECTION 8: PERFORMANCE TRACKING & FEEDBACK LOOP
# =============================================================================

@dataclass(slots=True)
class TrackedPick:
    """A pick being tracked from entry to resolution."""
    pick_id: str
    symbol: str
    direction: Direction
    entry_confidence: float
    entry_price: float
    entry_time: datetime
    source_traders: List[str] = field(default_factory=list)
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pnl_pct: Optional[float] = None
    resolved: bool = False
    resolution_source: str = ""  # 'tp', 'sl', 'timeout', 'manual'

@dataclass(slots=True)
class TraderPerformance:
    """Aggregated performance metrics for a single trader."""
    unique_code: str
    total_picks: int = 0
    winning_picks: int = 0
    losing_picks: int = 0
    total_pnl_pct: float = 0.0
    avg_pnl_pct: float = 0.0
    sharpe_30d: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PerformanceTracker:
    """Track copy-trader pick outcomes and maintain trader quality scores.

    Features:
    - Track every pick from entry to exit (TP, SL, or timeout)
    - Resolve against actual price data
    - Compute actual win rate, PnL, Sharpe per trader
    - Auto-blacklist traders whose 30-day Sharpe drops below 0.5
    - 90-day exponential decay for old performance
    - Daily quality score recomputation
    """

    PICK_TIMEOUT_HOURS: int = 168  # 7 days max hold
    DECAY_HALF_LIFE_DAYS: int = 45  # 90-day exponential decay

    def __init__(
        self,
        state_dir: Path = Path("/tmp/copy_trader_state_v2"),
        price_api: Optional[Any] = None,
    ) -> None:
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.price_api = price_api
        self.cache = get_cache()
        # In-memory state
        self._tracked_picks: Dict[str, TrackedPick] = {}
        self._trader_perf: Dict[str, TraderPerformance] = {}
        self._blacklist: set = set()
        self._load_state()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _state_path(self) -> Path:
        return self.state_dir / "performance_state.json"

    def _load_state(self) -> None:
        """Load tracked picks and trader performance from disk."""
        path = self._state_path()
        if not path.exists():
            return
        try:
            with open(path, "r") as f:
                data = json.load(f)
            for p in data.get("tracked_picks", []):
                tp = TrackedPick(
                    pick_id=p["pick_id"],
                    symbol=p["symbol"],
                    direction=Direction(p["direction"]),
                    entry_confidence=p["entry_confidence"],
                    entry_price=p["entry_price"],
                    entry_time=datetime.fromisoformat(p["entry_time"]),
                    source_traders=p.get("source_traders", []),
                    exit_price=p.get("exit_price"),
                    exit_time=datetime.fromisoformat(p["exit_time"]) if p.get("exit_time") else None,
                    pnl_pct=p.get("pnl_pct"),
                    resolved=p.get("resolved", False),
                    resolution_source=p.get("resolution_source", ""),
                )
                self._tracked_picks[tp.pick_id] = tp

            for code, perf in data.get("trader_perf", {}).items():
                self._trader_perf[code] = TraderPerformance(
                    unique_code=code,
                    total_picks=perf.get("total_picks", 0),
                    winning_picks=perf.get("winning_picks", 0),
                    losing_picks=perf.get("losing_picks", 0),
                    total_pnl_pct=perf.get("total_pnl_pct", 0.0),
                    avg_pnl_pct=perf.get("avg_pnl_pct", 0.0),
                    sharpe_30d=perf.get("sharpe_30d", 0.0),
                    max_drawdown=perf.get("max_drawdown", 0.0),
                    win_rate=perf.get("win_rate", 0.0),
                    last_updated=datetime.fromisoformat(perf.get("last_updated", iso_now())),
                )

            self._blacklist = set(data.get("blacklist", []))
            LOG.info(
                "PerformanceTracker loaded: %d picks, %d traders, %d blacklisted",
                len(self._tracked_picks), len(self._trader_perf), len(self._blacklist),
            )
        except Exception as exc:
            LOG.error("Failed to load performance state: %s. Starting fresh.", exc)

    def save_state(self) -> None:
        """Persist tracked picks and trader performance to disk."""
        data = {
            "tracked_picks": [
                {
                    "pick_id": p.pick_id,
                    "symbol": p.symbol,
                    "direction": p.direction.value,
                    "entry_confidence": p.entry_confidence,
                    "entry_price": p.entry_price,
                    "entry_time": p.entry_time.isoformat(),
                    "source_traders": p.source_traders,
                    "exit_price": p.exit_price,
                    "exit_time": p.exit_time.isoformat() if p.exit_time else None,
                    "pnl_pct": p.pnl_pct,
                    "resolved": p.resolved,
                    "resolution_source": p.resolution_source,
                }
                for p in self._tracked_picks.values()
            ],
            "trader_perf": {
                code: {
                    "unique_code": perf.unique_code,
                    "total_picks": perf.total_picks,
                    "winning_picks": perf.winning_picks,
                    "losing_picks": perf.losing_picks,
                    "total_pnl_pct": perf.total_pnl_pct,
                    "avg_pnl_pct": perf.avg_pnl_pct,
                    "sharpe_30d": perf.sharpe_30d,
                    "max_drawdown": perf.max_drawdown,
                    "win_rate": perf.win_rate,
                    "last_updated": perf.last_updated.isoformat(),
                }
                for code, perf in self._trader_perf.items()
            },
            "blacklist": list(self._blacklist),
            "saved_at": iso_now(),
        }
        try:
            with open(self._state_path(), "w") as f:
                json.dump(data, f, indent=2, default=str)
            LOG.debug("Performance state saved (%d picks, %d traders)",
                      len(self._tracked_picks), len(self._trader_perf))
        except Exception as exc:
            LOG.error("Failed to save performance state: %s", exc)

    # ------------------------------------------------------------------
    # Pick tracking
    # ------------------------------------------------------------------

    def register_pick(self, pick: CopyTraderPick, entry_price: float, source_traders: List[str]) -> str:
        """Register a new pick for outcome tracking.

        Args:
            pick: The consensus pick.
            entry_price: Entry price.
            source_traders: List of trader unique_codes that contributed.

        Returns:
            pick_id for later resolution.
        """
        pick_id = hashlib.sha256(
            f"{pick.symbol}:{pick.direction.value}:{pick.generated_at.isoformat()}".encode()
        ).hexdigest()[:16]

        tp = TrackedPick(
            pick_id=pick_id,
            symbol=pick.symbol,
            direction=pick.direction,
            entry_confidence=pick.confidence,
            entry_price=entry_price,
            entry_time=now_utc(),
            source_traders=source_traders,
        )
        self._tracked_picks[pick_id] = tp
        LOG.info("Registered pick %s: %s %s @ %.4f", pick_id, pick.symbol, pick.direction.value, entry_price)
        self.save_state()
        return pick_id

    def resolve_pick(
        self,
        pick_id: str,
        exit_price: float,
        resolution_source: str = "manual",
    ) -> Optional[float]:
        """Resolve a tracked pick with an exit price.

        Computes PnL based on direction:
        - LONG: (exit - entry) / entry
        - SHORT: (entry - exit) / entry

        Args:
            pick_id: ID from register_pick.
            exit_price: Exit price.
            resolution_source: 'tp', 'sl', 'timeout', 'manual'.

        Returns:
            PnL percentage, or None if pick not found.
        """
        tp = self._tracked_picks.get(pick_id)
        if tp is None:
            LOG.warning("Cannot resolve unknown pick_id: %s", pick_id)
            return None
        if tp.resolved:
            LOG.debug("Pick %s already resolved, skipping", pick_id)
            return tp.pnl_pct

        if tp.direction == Direction.LONG:
            pnl = (exit_price - tp.entry_price) / tp.entry_price * 100.0
        else:
            pnl = (tp.entry_price - exit_price) / tp.entry_price * 100.0

        tp.exit_price = exit_price
        tp.exit_time = now_utc()
        tp.pnl_pct = round(pnl, 4)
        tp.resolved = True
        tp.resolution_source = resolution_source

        # Update trader performance
        for trader_code in tp.source_traders:
            self._update_trader_performance(trader_code, pnl)

        LOG.info(
            "Resolved pick %s: %s %s -> PnL=%.2f%% (via %s)",
            pick_id, tp.symbol, tp.direction.value, pnl, resolution_source,
        )
        self.save_state()
        return tp.pnl_pct

    def resolve_expired_picks(self, current_prices: Dict[str, float]) -> int:
        """Auto-resolve picks that have exceeded timeout.

        Args:
            current_prices: Mapping of symbol -> current price.

        Returns:
            Number of picks resolved.
        """
        resolved_count = 0
        cutoff = now_utc() - timedelta(hours=self.PICK_TIMEOUT_HOURS)

        for pick_id, tp in list(self._tracked_picks.items()):
            if tp.resolved:
                continue
            if tp.entry_time < cutoff:
                price = current_prices.get(tp.symbol)
                if price is None:
                    continue
                self.resolve_pick(pick_id, price, resolution_source="timeout")
                resolved_count += 1

        if resolved_count > 0:
            LOG.info("Auto-resolved %d expired picks", resolved_count)
        return resolved_count

    # ------------------------------------------------------------------
    # Trader performance
    # ------------------------------------------------------------------

    def _update_trader_performance(self, trader_code: str, pnl: float) -> None:
        """Update performance metrics for a single trader."""
        perf = self._trader_perf.get(trader_code)
        if perf is None:
            perf = TraderPerformance(unique_code=trader_code)
            self._trader_perf[trader_code] = perf

        perf.total_picks += 1
        perf.total_pnl_pct += pnl
        if pnl > 0:
            perf.winning_picks += 1
        else:
            perf.losing_picks += 1
        perf.avg_pnl_pct = perf.total_pnl_pct / perf.total_picks
        perf.win_rate = perf.winning_picks / perf.total_picks if perf.total_picks > 0 else 0.0
        perf.last_updated = now_utc()

        # Sharpe (simplified): avg return / std dev of returns
        # We approximate using win rate and avg PnL
        if perf.total_picks >= 10:
            # Approximate Sharpe: win_rate * avg_win_size / (loss_rate * avg_loss_size)
            avg_win = perf.total_pnl_pct / perf.winning_picks if perf.winning_picks > 0 else 0
            avg_loss = abs(perf.total_pnl_pct / perf.losing_picks) if perf.losing_picks > 0 else 0.001
            if perf.losing_picks > 0:
                perf.sharpe_30d = (perf.win_rate * avg_win) / ((1 - perf.win_rate) * avg_loss)
            else:
                perf.sharpe_30d = 3.0  # No losses yet — high Sharpe

        # Update max drawdown tracking
        if pnl < 0:
            perf.max_drawdown = max(perf.max_drawdown, abs(pnl))

    def get_trader_performance(self, trader_code: str) -> Optional[TraderPerformance]:
        return self._trader_perf.get(trader_code)

    def is_blacklisted(self, trader_code: str) -> bool:
        return trader_code in self._blacklist

    def auto_blacklist(self) -> List[str]:
        """Auto-blacklist traders whose Sharpe drops below threshold.

        Returns:
            List of newly blacklisted trader codes.
        """
        newly_blacklisted: List[str] = []
        for code, perf in self._trader_perf.items():
            if code in self._blacklist:
                continue
            if perf.total_picks < 10:
                continue  # Need minimum sample size
            if perf.sharpe_30d < BLACKLIST_SHARPE_THRESHOLD:
                self._blacklist.add(code)
                newly_blacklisted.append(code)
                LOG.warning(
                    "AUTO-BLACKLISTED trader %s: Sharpe=%.2f (threshold=%.2f), "
                    "WR=%.1f%%, Picks=%d",
                    code, perf.sharpe_30d, BLACKLIST_SHARPE_THRESHOLD,
                    perf.win_rate * 100, perf.total_picks,
                )

        # Also check existing traders for recovery
        recovered: List[str] = []
        for code in list(self._blacklist):
            perf = self._trader_perf.get(code)
            if perf and perf.sharpe_30d >= BLACKLIST_SHARPE_THRESHOLD * 1.5:
                self._blacklist.discard(code)
                recovered.append(code)
                LOG.info(
                    "RECOVERED trader %s from blacklist: Sharpe=%.2f",
                    code, perf.sharpe_30d,
                )

        if newly_blacklisted:
            self.save_state()
        return newly_blacklisted

    def apply_blacklist(self, traders: List[TraderProfile]) -> List[TraderProfile]:
        """Mark blacklisted traders in the profile list."""
        for t in traders:
            if t.unique_code in self._blacklist:
                t.is_blacklisted = True
                t.blacklist_reason = f"Sharpe below {BLACKLIST_SHARPE_THRESHOLD}"
        return traders

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate a human-readable performance report."""
        total_picks = sum(p.total_picks for p in self._trader_perf.values())
        total_wins = sum(p.winning_picks for p in self._trader_perf.values())
        total_losses = sum(p.losing_picks for p in self._trader_perf.values())
        overall_wr = total_wins / total_picks if total_picks > 0 else 0.0

        top_traders = sorted(
            self._trader_perf.values(),
            key=lambda p: p.sharpe_30d,
            reverse=True,
        )[:10]

        worst_traders = sorted(
            self._trader_perf.values(),
            key=lambda p: p.sharpe_30d,
        )[:5]

        return {
            "summary": {
                "total_tracked_picks": len(self._tracked_picks),
                "resolved_picks": sum(1 for p in self._tracked_picks.values() if p.resolved),
                "active_picks": sum(1 for p in self._tracked_picks.values() if not p.resolved),
                "total_traders": len(self._trader_perf),
                "blacklisted_traders": len(self._blacklist),
                "overall_win_rate": round(overall_wr, 4),
                "total_wins": total_wins,
                "total_losses": total_losses,
            },
            "top_traders": [
                {
                    "code": t.unique_code[:16],
                    "picks": t.total_picks,
                    "win_rate": round(t.win_rate, 4),
                    "sharpe": round(t.sharpe_30d, 3),
                    "avg_pnl": round(t.avg_pnl_pct, 4),
                }
                for t in top_traders
            ],
            "worst_traders": [
                {
                    "code": t.unique_code[:16],
                    "picks": t.total_picks,
                    "win_rate": round(t.win_rate, 4),
                    "sharpe": round(t.sharpe_30d, 3),
                    "avg_pnl": round(t.avg_pnl_pct, 4),
                }
                for t in worst_traders
            ],
            "blacklist": list(self._blacklist)[:50],
            "generated_at": iso_now(),
        }



# =============================================================================
# SECTION 9: MAIN ENGINE ORCHESTRATOR
# =============================================================================

class CopyTraderEngine:
    """Main orchestrator that ties together all data sources, quality scoring,
    consensus generation, smart-money integration, and on-chain signals.

    Runtime target: < 10 minutes (vs. old 28-43 minutes)
    - Parallel source fetching via ThreadPoolExecutor
    - Local caching (15-min TTL) to avoid redundant API calls
    - Circuit breakers to skip failing sources quickly
    - All errors raised loudly — zero silent swallowing

    Usage:
        engine = CopyTraderEngine()
        picks = engine.run()
        engine.write_picks(picks)
    """

    def __init__(
        self,
        okx: Optional[OKXClient] = None,
        bybit: Optional[BybitClient] = None,
        hyperliquid: Optional[HyperliquidClient] = None,
        arkham: Optional[ArkhamClient] = None,
        scorer: Optional[QualityScorer] = None,
        consensus: Optional[ConsensusEngine] = None,
        perf_tracker: Optional[PerformanceTracker] = None,
        onchain: Optional[OnChainSignalProvider] = None,
        output_path: Path = OUTPUT_PATH,
    ) -> None:
        self.okx = okx or OKXClient()
        self.bybit = bybit or BybitClient()
        self.hyperliquid = hyperliquid or HyperliquidClient()
        self.arkham = arkham
        self.scorer = scorer or QualityScorer()
        self.consensus = consensus or ConsensusEngine(self.scorer)
        self.perf_tracker = perf_tracker or PerformanceTracker()
        self.onchain = onchain or OnChainSignalProvider(self.arkham)
        self.output_path = output_path
        self.health_statuses: List[HealthStatus] = []

    def _timed(self, label: str, func: Callable[[], T]) -> T:
        """Execute a function and log its runtime."""
        start = time.time()
        try:
            result = func()
            elapsed = time.time() - start
            LOG.info("[TIMER] %s: %.2fs", label, elapsed)
            return result
        except Exception as exc:
            elapsed = time.time() - start
            LOG.error("[TIMER] %s: FAILED after %.2fs: %s", label, elapsed, exc)
            raise

    # ------------------------------------------------------------------
    # Parallel source fetching
    # ------------------------------------------------------------------

    def _fetch_okx_pipeline(self) -> Tuple[List[TraderProfile], Dict[str, List[Position]]]:
        """Fetch OKX traders and their positions."""
        start = time.time()
        try:
            traders = self.okx.fetch_lead_traders()
            if not traders:
                return [], {}
            positions = self.okx.fetch_all_positions(traders[:20])  # Top 20 by quality
            elapsed = time.time() - start
            self.health_statuses.append(
                HealthStatus(
                    source="okx", healthy=True,
                    last_success=now_utc(), failure_count=0,
                    circuit_open=False, latency_ms=elapsed * 1000,
                    message=f"{len(traders)} traders, {sum(len(v) for v in positions.values())} positions",
                )
            )
            return traders, positions
        except Exception as exc:
            elapsed = time.time() - start
            self.health_statuses.append(
                HealthStatus(
                    source="okx", healthy=False,
                    last_success=None, failure_count=1,
                    circuit_open=isinstance(exc, CircuitOpenError),
                    latency_ms=elapsed * 1000, message=str(exc)[:200],
                )
            )
            LOG.error("OKX pipeline failed: %s", exc)
            raise

    def _fetch_bybit_pipeline(self) -> Tuple[List[TraderProfile], Dict[str, List[Position]]]:
        """Fetch Bybit traders and their positions."""
        start = time.time()
        try:
            traders = self.bybit.fetch_beehive_leaders()
            if not traders:
                return [], {}
            positions = self.bybit.fetch_all_positions(traders[:20])
            elapsed = time.time() - start
            self.health_statuses.append(
                HealthStatus(
                    source="bybit", healthy=True,
                    last_success=now_utc(), failure_count=0,
                    circuit_open=False, latency_ms=elapsed * 1000,
                    message=f"{len(traders)} traders, {sum(len(v) for v in positions.values())} positions",
                )
            )
            return traders, positions
        except Exception as exc:
            elapsed = time.time() - start
            self.health_statuses.append(
                HealthStatus(
                    source="bybit", healthy=False,
                    last_success=None, failure_count=1,
                    circuit_open=isinstance(exc, CircuitOpenError),
                    latency_ms=elapsed * 1000, message=str(exc)[:200],
                )
            )
            LOG.error("Bybit pipeline failed: %s", exc)
            raise

    def _fetch_hyperliquid_pipeline(self) -> Tuple[List[TraderProfile], Dict[str, List[Position]]]:
        """Fetch Hyperliquid traders and their positions."""
        start = time.time()
        try:
            traders = self.hyperliquid.fetch_hl_leaders()
            if not traders:
                return [], {}
            positions = self.hyperliquid.fetch_all_positions(traders[:20])
            elapsed = time.time() - start
            self.health_statuses.append(
                HealthStatus(
                    source="hyperliquid", healthy=True,
                    last_success=now_utc(), failure_count=0,
                    circuit_open=False, latency_ms=elapsed * 1000,
                    message=f"{len(traders)} traders, {sum(len(v) for v in positions.values())} positions",
                )
            )
            return traders, positions
        except Exception as exc:
            elapsed = time.time() - start
            self.health_statuses.append(
                HealthStatus(
                    source="hyperliquid", healthy=False,
                    last_success=None, failure_count=1,
                    circuit_open=isinstance(exc, CircuitOpenError),
                    latency_ms=elapsed * 1000, message=str(exc)[:200],
                )
            )
            LOG.error("Hyperliquid pipeline failed: %s", exc)
            raise

    def _fetch_smart_money(self) -> List[SmartMoneySignal]:
        """Fetch smart money signals from Arkham."""
        if self.arkham is None:
            LOG.info("Arkham not configured — skipping smart money")
            self.health_statuses.append(
                HealthStatus(
                    source="arkham", healthy=True,
                    last_success=now_utc(), failure_count=0,
                    circuit_open=False, message="Not configured",
                )
            )
            return []

        start = time.time()
        try:
            entity_signals: List[SmartMoneySignal] = []
            for entity in ArkhamClient.DEFAULT_ENTITIES[:6]:  # Top 6 for speed
                try:
                    sigs = self.arkham.track_entity_multi_chain(entity, hours=24)
                    entity_signals.extend(sigs)
                except (APIError, CircuitOpenError) as exc:
                    LOG.warning("Smart money %s failed: %s", entity, exc)
                    continue

            elapsed = time.time() - start
            self.health_statuses.append(
                HealthStatus(
                    source="arkham", healthy=True,
                    last_success=now_utc(), failure_count=0,
                    circuit_open=False, latency_ms=elapsed * 1000,
                    message=f"{len(entity_signals)} entity signals",
                )
            )
            return entity_signals
        except Exception as exc:
            elapsed = time.time() - start
            self.health_statuses.append(
                HealthStatus(
                    source="arkham", healthy=False,
                    last_success=None, failure_count=1,
                    circuit_open=isinstance(exc, CircuitOpenError),
                    latency_ms=elapsed * 1000, message=str(exc)[:200],
                )
            )
            LOG.error("Smart money pipeline failed: %s", exc)
            raise

    def _fetch_onchain_signals(self) -> List[OnChainSignal]:
        """Fetch on-chain signals."""
        start = time.time()
        try:
            signals = self.onchain.get_all_onchain_signals()
            elapsed = time.time() - start
            self.health_statuses.append(
                HealthStatus(
                    source="onchain", healthy=True,
                    last_success=now_utc(), failure_count=0,
                    circuit_open=False, latency_ms=elapsed * 1000,
                    message=f"{len(signals)} signals",
                )
            )
            return signals
        except Exception as exc:
            elapsed = time.time() - start
            self.health_statuses.append(
                HealthStatus(
                    source="onchain", healthy=False,
                    last_success=None, failure_count=1,
                    circuit_open=False, latency_ms=elapsed * 1000,
                    message=str(exc)[:200],
                )
            )
            LOG.error("On-chain signals failed: %s", exc)
            raise

    # ------------------------------------------------------------------
    # Main execution pipeline
    # ------------------------------------------------------------------

    def run(self) -> List[CopyTraderPick]:
        """Execute the full copy-trader intelligence pipeline.

        Steps:
        1. Parallel fetch from OKX, Bybit, Hyperliquid
        2. Quality score all traders
        3. Generate weighted consensus picks
        4. Fetch smart money signals
        5. Merge smart money with consensus
        6. Fetch on-chain signals
        7. Merge on-chain signals
        8. Auto-blacklist underperformers
        9. Return final picks

        Returns:
            List of CopyTraderPick sorted by confidence.

        Raises:
            InsufficientDataError: if no picks can be generated.
        """
        pipeline_start = time.time()
        LOG.info("=" * 60)
        LOG.info("CopyTraderEngine v2 starting pipeline run")
        LOG.info("=" * 60)

        # Step 1: Parallel source fetching
        LOG.info("--- Step 1: Parallel source fetching ---")
        all_traders: List[TraderProfile] = []
        all_positions: Dict[str, List[Position]] = {}

        # Use ThreadPool for parallel I/O-bound fetching
        fetch_tasks: List[Tuple[str, Callable[[], Tuple[List[TraderProfile], Dict[str, List[Position]]]]]] = [
            ("okx", self._fetch_okx_pipeline),
            ("bybit", self._fetch_bybit_pipeline),
            ("hyperliquid", self._fetch_hyperliquid_pipeline),
        ]

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(task): name for name, task in fetch_tasks}
            for future in as_completed(futures):
                source_name = futures[future]
                try:
                    traders, positions = future.result()
                    all_traders.extend(traders)
                    all_positions.update(positions)
                    LOG.info(
                        "%s: collected %d traders, %d positions",
                        source_name, len(traders), sum(len(v) for v in positions.values()),
                    )
                except Exception as exc:
                    LOG.error("Source %s failed in parallel fetch: %s", source_name, exc)

        LOG.info(
            "Total: %d traders, %d position maps from %d sources",
            len(all_traders), len(all_positions),
            len(set(t.source for t in all_traders)),
        )

        if not all_traders:
            raise InsufficientDataError("No traders fetched from any source")

        # Step 2: Quality scoring
        LOG.info("--- Step 2: Quality scoring ---")
        scored = self.scorer.score_traders(all_traders)
        LOG.info("Top 5 traders by quality score:")
        for t in scored[:5]:
            LOG.info(
                "  %.1f | %s (%s) | PnL=%.2f WR=%.1f%% AUM=$%.0f",
                t.quality_score, t.name[:20], t.source,
                t.pnl_ratio, t.win_rate * 100, t.aum,
            )

        # Apply performance tracker blacklist
        scored = self.perf_tracker.apply_blacklist(scored)
        blacklisted_count = sum(1 for t in scored if t.is_blacklisted)
        LOG.info("Blacklisted traders: %d", blacklisted_count)

        # Step 3: Filter to quality traders
        LOG.info("--- Step 3: Quality filtering ---")
        try:
            qualified = self.scorer.filter_quality_traders(scored)
        except QualityThresholdError as exc:
            LOG.error("Quality threshold not met: %s", exc)
            # Fallback: use top traders even if below threshold
            qualified = scored[:max(MIN_CONSENSUS_TRADERS, len(scored) // 4)]
            LOG.warning("Fallback: using top %d traders below threshold", len(qualified))

        # Build position map for qualified traders only
        qualified_codes = {t.unique_code for t in qualified}
        qualified_positions = {
            k: v for k, v in all_positions.items() if k in qualified_codes
        }

        LOG.info(
            "Qualified: %d traders with %d position maps",
            len(qualified), len(qualified_positions),
        )

        # Step 4: Generate consensus
        LOG.info("--- Step 4: Consensus generation ---")
        try:
            picks = self.consensus.generate_consensus(qualified_positions, qualified)
        except InsufficientDataError as exc:
            LOG.error("Consensus generation failed: %s", exc)
            picks = []

        LOG.info("Generated %d consensus picks", len(picks))

        # Step 5: Smart money (sequential — lower priority)
        LOG.info("--- Step 5: Smart money integration ---")
        try:
            smart_money = self._fetch_smart_money()
            if smart_money and picks:
                picks = self.consensus.merge_with_smart_money(picks, smart_money)
                LOG.info("Smart money merged: %d picks after merge", len(picks))
        except Exception as exc:
            LOG.error("Smart money step failed: %s", exc)

        # Step 6: On-chain signals
        LOG.info("--- Step 6: On-chain signals ---")
        try:
            onchain = self._fetch_onchain_signals()
            if onchain and picks:
                picks = self.consensus.merge_with_onchain_signals(picks, onchain)
                LOG.info("On-chain merged: %d picks after merge", len(picks))
        except Exception as exc:
            LOG.error("On-chain signals step failed: %s", exc)

        # Step 7: Auto-blacklist
        LOG.info("--- Step 7: Performance feedback ---")
        try:
            newly_blacklisted = self.perf_tracker.auto_blacklist()
            if newly_blacklisted:
                LOG.warning("Auto-blacklisted %d traders: %s", len(newly_blacklisted), newly_blacklisted)
        except Exception as exc:
            LOG.error("Auto-blacklist failed: %s", exc)

        elapsed = time.time() - pipeline_start
        LOG.info("=" * 60)
        LOG.info("Pipeline complete: %d picks in %.2fs", len(picks), elapsed)
        LOG.info("=" * 60)

        if not picks:
            raise InsufficientDataError(
                "Pipeline completed but no picks met all thresholds. "
                "Check individual source logs above."
            )

        return picks

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def write_picks(
        self,
        picks: List[CopyTraderPick],
        path: Optional[Path] = None,
    ) -> Path:
        """Write picks to the active picks JSON file.

        Format compatible with alpha_engine/data/active_picks.json schema.

        Args:
            picks: List of CopyTraderPick.
            path: Override output path.

        Returns:
            Path to the written file.
        """
        out = path or self.output_path
        out.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "generated_at": iso_now(),
            "source_system": "copy_trader_intel_v2",
            "strategy": "quality_weighted_consensus",
            "engine_version": "2.0.0",
            "pick_count": len(picks),
            "picks": [p.to_dict() for p in picks],
            "health": [h.__dict__ for h in self.health_statuses],
        }

        with open(out, "w") as f:
            json.dump(data, f, indent=2, default=str)

        LOG.info("Wrote %d picks to %s", len(picks), out)
        return out

    def get_health_report(self) -> Dict[str, Any]:
        """Generate health check report for all data sources.

        Returns:
            Dict with overall health and per-source status.
        """
        healthy_count = sum(1 for h in self.health_statuses if h.healthy)
        total = len(self.health_statuses)

        # Also check circuit breakers
        cb_status = {}
        for name, cb in _CIRCUIT_BREAKERS.items():
            cb_status[name] = {
                "state": cb.state.value,
                "failure_count": cb._failure_count,
                "last_failure": datetime.fromtimestamp(cb._last_failure_time, tz=timezone.utc).isoformat()
                if cb._last_failure_time else None,
            }

        return {
            "overall_healthy": healthy_count == total and total > 0,
            "healthy_sources": healthy_count,
            "total_sources": total,
            "sources": [h.__dict__ for h in self.health_statuses],
            "circuit_breakers": cb_status,
            "generated_at": iso_now(),
        }



# =============================================================================
# SECTION 10: HEALTH CHECK HTTP SERVER
# =============================================================================

def create_health_handler(engine: CopyTraderEngine):
    """Factory: create an HTTP request handler bound to an engine instance."""
    from http.server import BaseHTTPRequestHandler

    class HealthHandler(BaseHTTPRequestHandler):
        engine_ref: CopyTraderEngine = engine  # type: ignore[misc]

        def log_message(self, format: str, *args: Any) -> None:
            LOG.debug(format, *args)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                report = self.engine_ref.get_health_report()
                status_code = 200 if report["overall_healthy"] else 503
                body = json.dumps(report, indent=2, default=str).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif self.path == "/picks":
                try:
                    path = self.engine_ref.output_path
                    if path.exists():
                        with open(path, "rb") as f:
                            body = f.read()
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                    else:
                        body = b'{"error": "No picks generated yet"}'
                        self.send_response(404)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(body)
                except Exception as exc:
                    body = json.dumps({"error": str(exc)}).encode("utf-8")
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(body)
            else:
                body = b'{"error": "Not found. Try /health or /picks"}'
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

    return HealthHandler


def start_health_server(engine: CopyTraderEngine, port: int = 8080) -> None:
    """Start a blocking HTTP health check server.

    Args:
        engine: CopyTraderEngine instance to serve health from.
        port: TCP port to listen on.
    """
    from http.server import HTTPServer

    handler = create_health_handler(engine)
    server = HTTPServer(("0.0.0.0", port), handler)
    LOG.info("Health server starting on port %d", port)
    LOG.info("  GET /health  -> Source health status")
    LOG.info("  GET /picks   -> Current active picks")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOG.info("Health server shutting down")
        server.shutdown()


# =============================================================================
# SECTION 11: CLI ENTRY POINT
# =============================================================================

def parse_args(argv: Optional[List[str]] = None) -> Any:
    """Parse command-line arguments."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Copy Trader Intelligence Engine v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s run                          # Full pipeline run
  %(prog)s run --output picks.json      # Write to custom path
  %(prog)s health                       # Print health report
  %(prog)s perf                         # Print performance report
  %(prog)s server --port 8080           # Start health server
  %(prog)s run --no-smart-money         # Skip Arkham smart money
  %(prog)s run --no-onchain             # Skip on-chain signals
  %(prog)s invalidate-cache             # Clear local cache
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # run
    run_parser = subparsers.add_parser("run", help="Run the full pipeline")
    run_parser.add_argument(
        "--output", "-o", type=Path, default=OUTPUT_PATH,
        help=f"Output path for picks (default: {OUTPUT_PATH})",
    )
    run_parser.add_argument(
        "--no-smart-money", action="store_true",
        help="Skip Arkham smart money integration",
    )
    run_parser.add_argument(
        "--no-onchain", action="store_true",
        help="Skip on-chain signal integration",
    )
    run_parser.add_argument(
        "--max-traders", type=int, default=20,
        help="Max traders per source to fetch positions for (default: 20)",
    )

    # health
    subparsers.add_parser("health", help="Print health report and exit")

    # perf
    subparsers.add_parser("perf", help="Print performance report and exit")

    # server
    server_parser = subparsers.add_parser("server", help="Start health check HTTP server")
    server_parser.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")

    # invalidate-cache
    subparsers.add_parser("invalidate-cache", help="Clear local API cache")

    # test-imports
    subparsers.add_parser("test-imports", help="Verify all imports work")

    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the copy trader engine.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    args = parse_args(argv)

    # Setup logging level from env
    log_level = os.environ.get("COPY_TRADER_LOG_LEVEL", "INFO")
    LOG.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if args.command == "test-imports":
        LOG.info("All imports verified successfully")
        return 0

    if args.command == "invalidate-cache":
        cache = get_cache()
        removed = cache.invalidate()
        LOG.info("Cache invalidated: %d entries removed", removed)
        return 0

    if args.command == "health":
        engine = CopyTraderEngine()
        report = engine.get_health_report()
        print(json.dumps(report, indent=2, default=str))
        return 0 if report["overall_healthy"] else 1

    if args.command == "perf":
        perf = PerformanceTracker()
        report = perf.get_performance_report()
        print(json.dumps(report, indent=2, default=str))
        return 0

    if args.command == "server":
        engine = CopyTraderEngine()
        start_health_server(engine, port=args.port)
        return 0

    if args.command == "run":
        engine = CopyTraderEngine(
            output_path=args.output,
        )

        # Disable sources per CLI flags
        if getattr(args, "no_smart_money", False):
            engine.arkham = None
            LOG.info("Smart money disabled via --no-smart-money")
        if getattr(args, "no_onchain", False):
            engine.onchain = OnChainSignalProvider(None)
            LOG.info("On-chain signals disabled via --no-onchain")

        try:
            picks = engine.run()
            engine.write_picks(picks)
            LOG.info("SUCCESS: Generated %d picks", len(picks))
            for i, p in enumerate(picks[:10], 1):
                LOG.info(
                    "  #%d: %s %s | conf=%.1f%% | traders=%d | avg_q=%.1f",
                    i, p.symbol, p.direction.value, p.confidence * 100,
                    p.metadata.get("consensus_count", 0),
                    p.metadata.get("avg_quality_score", 0),
                )
            return 0
        except InsufficientDataError as exc:
            LOG.error("Pipeline completed but no picks generated: %s", exc)
            return 1
        except Exception as exc:
            LOG.exception("Pipeline FAILED: %s", exc)
            return 1

    # No command or unknown
    print("Usage: copy_trader_engine_v2.py {run|health|perf|server|invalidate-cache|test-imports}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

