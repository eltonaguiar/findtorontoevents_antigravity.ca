#!/usr/bin/env python3
"""
================================================================================
Outcome Resolver V2 — Batch Resolution Engine
================================================================================
Resolves closed trading picks with PnL by efficiently fetching market data
and computing outcomes.  Replaces the V1 resolver (0.09% effectiveness) with
a robust, parallelised, caching, and retry-aware pipeline.

Target:  >= 95 % resolution rate
Current:    0.09 %  (V1)

Pipeline
--------
1.  LOAD    — fetch batches of unresolved / stale picks from DB
2.  CACHE   — in-memory + on-disk SQLite price cache (TTL = 15 min L1, 4 h L2)
3.  BATCH   — chunk symbol requests (default 50 / batch)
4.  FETCH   — parallel HTTP requests with exponential back-off
5.  CALC    — PnL, hit/miss, slippage, market-impact
6.  WRITE   — UPDATE picks table + INSERT resolution_audit log
7.  REPORT  — emit resolution_rate, latency histogram, error breakdown

Author: Alpha Engine Team
Date: 2026-05-20
================================================================================
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import lru_cache, wraps
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import numpy as np
import pandas as pd
import requests
from scipy import stats

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("outcome_resolver_v2")


def _setup_logging(level: int = logging.INFO) -> None:
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        fmt = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.setLevel(level)


_setup_logging()

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------
__version__ = "2.0.0"
__date__ = "2026-05-20"

# Asset-class PnL thresholds (basis points)
PNL_WIN_THRESHOLD_BY_CLASS: Dict[str, float] = {
    "CRYPTO": 0.00001,     # 0.1  bp  — ultra-tight for scalping
    "EQUITY": 0.0005,      # 5    bp
    "ETF": 0.0005,         # 5    bp
    "FOREX": 0.0005,       # 5    bp
    "COMMODITY": 0.0005,   # 5    bp
    "BOND": 0.0005,        # 5    bp
    "FUTURES": 0.0005,     # 5    bp
    "STOCK": 0.0005,       # alias
    "INDEX": 0.0005,       # alias
}

# Batch / concurrency knobs
DEFAULT_BATCH_SIZE: int = 50
DEFAULT_MAX_WORKERS: int = 8
DEFAULT_BACKOFF_BASE: float = 1.0
DEFAULT_BACKOFF_MAX: float = 60.0
DEFAULT_MAX_RETRIES: int = 5
CACHE_TTL_SECONDS: int = 900          # L1 in-memory 15 min
PERSISTENT_CACHE_TTL_SECONDS: int = 14400  # L2 on-disk 4 h
PRICE_CACHE_TABLE: str = "price_cache_v2"

# API end-points (overridable via env)
PRICE_API_URL: str = os.getenv(
    "ALPHA_PRICE_API_URL",
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
)
API_TIMEOUT: int = int(os.getenv("ALPHA_API_TIMEOUT", "15"))

# DB path (env override)
DB_PATH: str = os.getenv("ALPHA_DB_PATH", "./alpha_engine.db")
CACHE_DB_PATH: str = os.getenv("ALPHA_CACHE_DB_PATH", "./price_cache.db")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class ResolutionStatus(Enum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    ERROR = "error"
    STALE = "stale"
    MANUAL_OVERRIDE = "manual_override"


class Outcome(Enum):
    WIN = "win"
    LOSS = "loss"
    BREAKEVEN = "breakeven"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class PickRecord:
    """Row from the picks table awaiting resolution."""
    pick_id: int
    symbol: str
    asset_class: str
    direction: str          # "LONG" | "SHORT"
    entry_price: Optional[float]
    exit_price: Optional[float]
    entry_time: datetime
    exit_time: Optional[datetime]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    confidence: float
    status: str
    metadata: str = "{}"

    @property
    def meta_dict(self) -> Dict[str, Any]:
        try:
            return json.loads(self.metadata)
        except Exception:
            return {}


@dataclass
class PriceSnapshot:
    """A single cached price observation."""
    symbol: str
    price: float
    timestamp: datetime
    source: str = "api"
    expiry: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(seconds=CACHE_TTL_SECONDS))


@dataclass
class ResolutionResult:
    """Outcome of resolving one pick."""
    pick_id: int
    status: ResolutionStatus
    outcome: Outcome
    pnl_pct: float
    pnl_abs: float
    exit_price_used: float
    resolution_time_ms: float
    error_message: str = ""
    slippage_estimate: float = 0.0
    market_impact_estimate: float = 0.0


@dataclass
class ResolutionMetrics:
    """Aggregated run-time metrics."""
    run_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    total_picks: int = 0
    resolved_count: int = 0
    error_count: int = 0
    unresolved_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    api_calls: int = 0
    api_errors: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    resolution_rate_pct: float = 0.0
    error_breakdown: Dict[str, int] = field(default_factory=dict)
    outcome_distribution: Dict[str, int] = field(default_factory=dict)

    @property
    def effective_rate(self) -> float:
        if self.total_picks == 0:
            return 0.0
        return (self.resolved_count / self.total_picks) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "total_picks": self.total_picks,
            "resolved_count": self.resolved_count,
            "error_count": self.error_count,
            "unresolved_count": self.unresolved_count,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "api_calls": self.api_calls,
            "api_errors": self.api_errors,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "resolution_rate_pct": round(self.resolution_rate_pct, 4),
            "effective_rate_pct": round(self.effective_rate, 4),
            "error_breakdown": self.error_breakdown,
            "outcome_distribution": self.outcome_distribution,
        }


# ---------------------------------------------------------------------------
# Exponential back-off decorator
# ---------------------------------------------------------------------------
def exponential_backoff(
    max_retries: int = DEFAULT_MAX_RETRIES,
    base: float = DEFAULT_BACKOFF_BASE,
    cap: float = DEFAULT_BACKOFF_MAX,
    exceptions: Tuple[type, ...] = (requests.RequestException,),
):
    """Decorator that retries *func* with exponential back-off + jitter."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == max_retries:
                        logger.error("Max retries (%d) exceeded for %s: %s", max_retries, func.__name__, exc)
                        raise
                    jitter = np.random.uniform(0, 0.5)
                    sleep_time = min(base * (2 ** (attempt - 1)) + jitter, cap)
                    logger.warning(
                        "Attempt %d/%d failed for %s: %s — sleeping %.2fs",
                        attempt, max_retries, func.__name__, exc, sleep_time,
                    )
                    time.sleep(sleep_time)
            return None  # unreachable
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Price Cache (L1 in-memory + L2 persistent SQLite)
# ---------------------------------------------------------------------------
class PriceCache:
    """Two-tier price cache: in-memory LRU + persistent SQLite."""

    def __init__(
        self,
        l1_ttl: int = CACHE_TTL_SECONDS,
        l2_ttl: int = PERSISTENT_CACHE_TTL_SECONDS,
        db_path: str = CACHE_DB_PATH,
    ) -> None:
        self.l1_ttl = l1_ttl
        self.l2_ttl = l2_ttl
        self.db_path = db_path
        self._l1: Dict[str, Tuple[float, datetime]] = {}
        self._lock = threading.RLock()
        self._ensure_table()

    def _ensure_table(self) -> None:
        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            conn.execute(
                f"""CREATE TABLE IF NOT EXISTS {PRICE_CACHE_TABLE} (
                    symbol TEXT PRIMARY KEY,
                    price REAL NOT NULL,
                    fetched_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )"""
            )
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_expires ON {PRICE_CACHE_TABLE}(expires_at)"
            )
            conn.commit()

    def _now(self) -> datetime:
        return datetime.utcnow()

    def _l1_key(self, symbol: str, ts: Optional[datetime] = None) -> str:
        # granularity: minute-level
        minute = (ts or self._now()).strftime("%Y%m%d%H%M")
        return f"{symbol}::{minute}"

    def get(self, symbol: str, ts: Optional[datetime] = None) -> Optional[PriceSnapshot]:
        key = self._l1_key(symbol, ts)
        now = self._now()

        # --- L1 ---
        with self._lock:
            if key in self._l1:
                price, expiry = self._l1[key]
                if expiry > now:
                    return PriceSnapshot(symbol, price, now, source="l1_cache", expiry=expiry)
                else:
                    del self._l1[key]

        # --- L2 ---
        try:
            with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
                row = conn.execute(
                    f"SELECT price, fetched_at, expires_at FROM {PRICE_CACHE_TABLE} WHERE symbol = ?",
                    (key,),
                ).fetchone()
                if row:
                    price, fetched_at, expires_at = row
                    expiry = datetime.fromisoformat(expires_at)
                    if expiry > now:
                        # promote to L1
                        with self._lock:
                            self._l1[key] = (price, expiry)
                        return PriceSnapshot(symbol, price, datetime.fromisoformat(fetched_at), source="l2_cache", expiry=expiry)
                    else:
                        conn.execute(f"DELETE FROM {PRICE_CACHE_TABLE} WHERE symbol = ?", (key,))
                        conn.commit()
        except Exception as exc:
            logger.warning("L2 cache read error: %s", exc)

        return None

    def put(self, symbol: str, price: float, ts: Optional[datetime] = None) -> None:
        key = self._l1_key(symbol, ts)
        now = self._now()
        expiry = now + timedelta(seconds=self.l1_ttl)

        with self._lock:
            self._l1[key] = (price, expiry)

        try:
            l2_expiry = now + timedelta(seconds=self.l2_ttl)
            with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
                conn.execute(
                    f"""INSERT OR REPLACE INTO {PRICE_CACHE_TABLE}
                        (symbol, price, fetched_at, expires_at)
                        VALUES (?, ?, ?, ?)""",
                    (key, price, now.isoformat(), l2_expiry.isoformat()),
                )
                conn.commit()
        except Exception as exc:
            logger.warning("L2 cache write error: %s", exc)

    def purge_stale(self) -> int:
        """Remove expired L2 entries.  Returns count deleted."""
        now = self._now().isoformat()
        try:
            with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
                cur = conn.execute(f"DELETE FROM {PRICE_CACHE_TABLE} WHERE expires_at < ?", (now,))
                conn.commit()
                return cur.rowcount
        except Exception as exc:
            logger.warning("Cache purge error: %s", exc)
            return 0

    def l1_size(self) -> int:
        with self._lock:
            return len(self._l1)

    def l2_size(self) -> int:
        try:
            with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
                row = conn.execute(f"SELECT COUNT(*) FROM {PRICE_CACHE_TABLE}").fetchone()
                return row[0] if row else 0
        except Exception:
            return 0


# ---------------------------------------------------------------------------
# Price Fetcher (parallel + retry)
# ---------------------------------------------------------------------------
class PriceFetcher:
    """Fetches market prices with caching, retries, and batching."""

    def __init__(
        self,
        cache: Optional[PriceCache] = None,
        max_workers: int = DEFAULT_MAX_WORKERS,
        api_url: str = PRICE_API_URL,
        timeout: int = API_TIMEOUT,
    ) -> None:
        self.cache = cache or PriceCache()
        self.max_workers = max_workers
        self.api_url = api_url
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                )
            }
        )
        self._metrics_lock = threading.Lock()
        self._api_calls = 0
        self._api_errors = 0
        self._cache_hits = 0
        self._cache_misses = 0

    # -- single symbol fetch with retry --
    @exponential_backoff(
        max_retries=DEFAULT_MAX_RETRIES,
        base=DEFAULT_BACKOFF_BASE,
        cap=DEFAULT_BACKOFF_MAX,
    )
    def _fetch_one_raw(self, symbol: str) -> float:
        """HTTP GET for a single symbol; raises on failure."""
        url = self.api_url.format(symbol=symbol)
        resp = self._session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        result = data["chart"]["result"][0]
        # latest close
        closes = result["indicators"]["quote"][0]["close"]
        price = closes[-1]
        if price is None or not np.isfinite(price):
            raise ValueError(f"Invalid price for {symbol}: {price}")
        with self._metrics_lock:
            self._api_calls += 1
        return float(price)

    def fetch_one(self, symbol: str, ts: Optional[datetime] = None) -> Optional[float]:
        """Fetch price for *symbol* with L1/L2 cache lookup."""
        # 1. cache check
        cached = self.cache.get(symbol, ts)
        if cached is not None:
            with self._metrics_lock:
                self._cache_hits += 1
            logger.debug("Cache hit for %s => %.4f", symbol, cached.price)
            return cached.price

        with self._metrics_lock:
            self._cache_misses += 1

        # 2. live fetch
        try:
            price = self._fetch_one_raw(symbol)
            self.cache.put(symbol, price, ts)
            return price
        except Exception as exc:
            with self._metrics_lock:
                self._api_errors += 1
            logger.error("Failed to fetch %s: %s", symbol, exc)
            return None

    def fetch_batch(
        self, symbols: Sequence[str], ts: Optional[datetime] = None
    ) -> Dict[str, Optional[float]]:
        """Parallel fetch for many symbols; returns {symbol: price | None}."""
        if not symbols:
            return {}

        results: Dict[str, Optional[float]] = {}
        to_fetch: List[str] = []

        # cache pass
        for sym in symbols:
            cached = self.cache.get(sym, ts)
            if cached is not None:
                results[sym] = cached.price
                with self._metrics_lock:
                    self._cache_hits += 1
            else:
                to_fetch.append(sym)
                with self._metrics_lock:
                    self._cache_misses += 1

        if not to_fetch:
            return results

        logger.info("Fetching %d symbols in parallel (max_workers=%d)", len(to_fetch), self.max_workers)
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            future_map = {pool.submit(self.fetch_one, sym, ts): sym for sym in to_fetch}
            for future in as_completed(future_map):
                sym = future_map[future]
                try:
                    price = future.result()
                    results[sym] = price
                except Exception as exc:
                    results[sym] = None
                    logger.error("Parallel fetch failed for %s: %s", sym, exc)

        return results

    @property
    def stats(self) -> Dict[str, int]:
        with self._metrics_lock:
            return {
                "api_calls": self._api_calls,
                "api_errors": self._api_errors,
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
            }

    def close(self) -> None:
        self._session.close()


# ---------------------------------------------------------------------------
# PnL Calculator
# ---------------------------------------------------------------------------
class PnLCalculator:
    """Computes PnL, outcome classification, and slippage estimates."""

    SLIPPAGE_BPS: Dict[str, float] = {
        "CRYPTO": 1.0,
        "EQUITY": 2.0,
        "ETF": 2.0,
        "FOREX": 0.5,
        "COMMODITY": 3.0,
        "BOND": 1.0,
        "FUTURES": 1.5,
        "STOCK": 2.0,
        "INDEX": 2.0,
    }

    @classmethod
    def compute(
        cls,
        pick: PickRecord,
        exit_price: float,
    ) -> ResolutionResult:
        t0 = time.perf_counter()
        asset_class = (pick.asset_class or "EQUITY").upper()
        threshold = PNL_WIN_THRESHOLD_BY_CLASS.get(asset_class, 0.0005)

        direction_mult = 1.0 if pick.direction.upper() == "LONG" else -1.0
        entry = pick.entry_price
        if entry is None or entry <= 0:
            return ResolutionResult(
                pick_id=pick.pick_id,
                status=ResolutionStatus.ERROR,
                outcome=Outcome.UNKNOWN,
                pnl_pct=0.0,
                pnl_abs=0.0,
                exit_price_used=exit_price,
                resolution_time_ms=(time.perf_counter() - t0) * 1000,
                error_message="Missing or invalid entry_price",
            )

        raw_pnl_pct = ((exit_price - entry) / entry) * direction_mult
        slippage_bps = cls.SLIPPAGE_BPS.get(asset_class, 2.0)
        slippage_pct = slippage_bps / 10000.0
        # conservative: subtract slippage from winner, add to loser
        pnl_pct = raw_pnl_pct - (slippage_pct * np.sign(raw_pnl_pct))
        pnl_abs = pnl_pct * entry

        if pnl_pct >= threshold:
            outcome = Outcome.WIN
        elif pnl_pct <= -threshold:
            outcome = Outcome.LOSS
        else:
            outcome = Outcome.BREAKEVEN

        elapsed = (time.perf_counter() - t0) * 1000

        return ResolutionResult(
            pick_id=pick.pick_id,
            status=ResolutionStatus.RESOLVED,
            outcome=outcome,
            pnl_pct=pnl_pct,
            pnl_abs=pnl_abs,
            exit_price_used=exit_price,
            resolution_time_ms=elapsed,
            slippage_estimate=slippage_pct,
            market_impact_estimate=slippage_pct * 0.5,
        )


# ---------------------------------------------------------------------------
# DB Interface
# ---------------------------------------------------------------------------
class OutcomeDatabase:
    """Thin wrapper around the picks / resolution_audit tables."""

    EXPECTED_TABLES: Tuple[str, ...] = ("picks", "resolution_audit", "strategies")

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def get_unresolved_picks(
        self,
        batch_size: int = DEFAULT_BATCH_SIZE,
        max_age_hours: Optional[int] = 48,
    ) -> List[PickRecord]:
        """Load picks that need resolution."""
        where_clauses = ["(status != 'resolved' OR status IS NULL)"]
        params: List[Any] = []

        if max_age_hours is not None:
            cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
            where_clauses.append("entry_time >= ?")
            params.append(cutoff.isoformat())

        where_sql = " AND ".join(where_clauses)

        sql = f"""
            SELECT
                pick_id, symbol, asset_class, direction,
                entry_price, exit_price, entry_time, exit_time,
                stop_loss, take_profit, confidence, status, metadata
            FROM picks
            WHERE {where_sql}
            ORDER BY entry_time ASC
            LIMIT ?
        """
        params.append(batch_size)

        rows: List[PickRecord] = []
        try:
            with self._conn() as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.execute(sql, params)
                for row in cur.fetchall():
                    rows.append(
                        PickRecord(
                            pick_id=row["pick_id"],
                            symbol=row["symbol"],
                            asset_class=row["asset_class"] or "EQUITY",
                            direction=row["direction"] or "LONG",
                            entry_price=row["entry_price"],
                            exit_price=row["exit_price"],
                            entry_time=datetime.fromisoformat(row["entry_time"]),
                            exit_time=(
                                datetime.fromisoformat(row["exit_time"])
                                if row["exit_time"]
                                else None
                            ),
                            stop_loss=row["stop_loss"],
                            take_profit=row["take_profit"],
                            confidence=row["confidence"] or 0.5,
                            status=row["status"] or "unresolved",
                            metadata=row["metadata"] or "{}",
                        )
                    )
        except Exception as exc:
            logger.error("DB read error: %s", exc)

        logger.info("Loaded %d unresolved picks", len(rows))
        return rows

    def update_pick_resolution(
        self,
        result: ResolutionResult,
        asset_class: str,
    ) -> bool:
        """Atomically update the picks table and insert audit row."""
        try:
            with self._conn() as conn:
                # 1. update picks row
                conn.execute(
                    """UPDATE picks SET
                        status = ?,
                        exit_price = ?,
                        pnl_pct = ?,
                        resolved_at = ?,
                        outcome = ?,
                        resolution_version = ?
                    WHERE pick_id = ?""",
                    (
                        result.status.value,
                        result.exit_price_used,
                        result.pnl_pct,
                        datetime.utcnow().isoformat(),
                        result.outcome.value,
                        __version__,
                        result.pick_id,
                    ),
                )

                # 2. audit trail
                conn.execute(
                    """INSERT INTO resolution_audit (
                        pick_id, status, outcome, pnl_pct, exit_price,
                        resolution_time_ms, slippage_estimate,
                        market_impact_estimate, error_message,
                        resolver_version, resolved_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        result.pick_id,
                        result.status.value,
                        result.outcome.value,
                        result.pnl_pct,
                        result.exit_price_used,
                        result.resolution_time_ms,
                        result.slippage_estimate,
                        result.market_impact_estimate,
                        result.error_message,
                        __version__,
                        datetime.utcnow().isoformat(),
                    ),
                )
                conn.commit()
                return True
        except Exception as exc:
            logger.error("DB write error for pick %d: %s", result.pick_id, exc)
            return False

    def get_resolution_rate(self) -> float:
        """Return current % of picks resolved (0-100)."""
        try:
            with self._conn() as conn:
                total = conn.execute("SELECT COUNT(*) FROM picks").fetchone()[0]
                if total == 0:
                    return 100.0
                resolved = conn.execute(
                    "SELECT COUNT(*) FROM picks WHERE status = 'resolved'"
                ).fetchone()[0]
                return (resolved / total) * 100.0
        except Exception as exc:
            logger.error("Cannot compute resolution rate: %s", exc)
            return 0.0

    def create_audit_table_if_missing(self) -> None:
        """Idempotent schema helper."""
        ddl = """
            CREATE TABLE IF NOT EXISTS resolution_audit (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pick_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                outcome TEXT,
                pnl_pct REAL,
                exit_price REAL,
                resolution_time_ms REAL,
                slippage_estimate REAL,
                market_impact_estimate REAL,
                error_message TEXT,
                resolver_version TEXT,
                resolved_at TEXT NOT NULL
            )
        """
        try:
            with self._conn() as conn:
                conn.execute(ddl)
                conn.commit()
        except Exception as exc:
            logger.warning("Audit table creation: %s", exc)


# ---------------------------------------------------------------------------
# OutcomeResolver (main orchestrator)
# ---------------------------------------------------------------------------
class OutcomeResolver:
    """Batch outcome resolution engine."""

    def __init__(
        self,
        db: Optional[OutcomeDatabase] = None,
        fetcher: Optional[PriceFetcher] = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self.db = db or OutcomeDatabase()
        self.fetcher = fetcher or PriceFetcher()
        self.batch_size = batch_size
        self.db.create_audit_table_if_missing()
        self._metrics = ResolutionMetrics(
            run_id=self._generate_run_id(),
            started_at=datetime.utcnow(),
        )

    @staticmethod
    def _generate_run_id() -> str:
        return datetime.utcnow().strftime("%Y%m%d%H%M%S") + "_" + hashlib.sha256(
            str(time.time()).encode()
        ).hexdigest()[:8]

    def _collect_latencies(self, results: List[ResolutionResult]) -> None:
        if not results:
            return
        latencies = [r.resolution_time_ms for r in results]
        self._metrics.avg_latency_ms = float(np.mean(latencies))
        self._metrics.p95_latency_ms = float(np.percentile(latencies, 95))

    def run_single_batch(self) -> int:
        """Process one batch of unresolved picks.  Returns number resolved."""
        picks = self.db.get_unresolved_picks(batch_size=self.batch_size)
        if not picks:
            logger.info("No unresolved picks to process.")
            return 0

        self._metrics.total_picks += len(picks)

        # extract unique symbols
        symbols = list({p.symbol for p in picks if p.symbol})
        logger.info("Batch: %d picks, %d unique symbols", len(picks), len(symbols))

        # parallel price fetch
        prices = self.fetcher.fetch_batch(symbols)

        # compute PnL per pick
        results: List[ResolutionResult] = []
        for pick in picks:
            price = prices.get(pick.symbol)
            if price is None:
                self._metrics.error_count += 1
                self._metrics.error_breakdown["price_fetch_failure"] = (
                    self._metrics.error_breakdown.get("price_fetch_failure", 0) + 1
                )
                self._metrics.unresolved_count += 1
                results.append(
                    ResolutionResult(
                        pick_id=pick.pick_id,
                        status=ResolutionStatus.ERROR,
                        outcome=Outcome.UNKNOWN,
                        pnl_pct=0.0,
                        pnl_abs=0.0,
                        exit_price_used=0.0,
                        resolution_time_ms=0.0,
                        error_message=f"No price for {pick.symbol}",
                    )
                )
                continue

            result = PnLCalculator.compute(pick, price)
            results.append(result)

            if result.status == ResolutionStatus.RESOLVED:
                self._metrics.resolved_count += 1
                self._metrics.outcome_distribution[result.outcome.value] = (
                    self._metrics.outcome_distribution.get(result.outcome.value, 0) + 1
                )
                # persist
                ok = self.db.update_pick_resolution(result, pick.asset_class)
                if not ok:
                    self._metrics.error_count += 1
            else:
                self._metrics.error_count += 1
                self._metrics.unresolved_count += 1

        self._collect_latencies(results)
        fetch_stats = self.fetcher.stats
        self._metrics.api_calls = fetch_stats["api_calls"]
        self._metrics.api_errors = fetch_stats["api_errors"]
        self._metrics.cache_hits = fetch_stats["cache_hits"]
        self._metrics.cache_misses = fetch_stats["cache_misses"]

        effective_rate = (
            (self._metrics.resolved_count / max(self._metrics.total_picks, 1)) * 100
        )
        logger.info(
            "Batch complete: resolved=%d errors=%d rate=%.2f%%",
            self._metrics.resolved_count,
            self._metrics.error_count,
            effective_rate,
        )
        return len([r for r in results if r.status == ResolutionStatus.RESOLVED])

    def run_continuous(
        self,
        max_batches: int = 1000,
        pause_seconds: float = 5.0,
    ) -> ResolutionMetrics:
        """Run until no more unresolved picks or *max_batches* reached."""
        logger.info("OutcomeResolver V2 starting — run_id=%s", self._metrics.run_id)
        for batch_num in range(1, max_batches + 1):
            resolved = self.run_single_batch()
            if resolved == 0:
                logger.info("No progress in batch %d — stopping.", batch_num)
                break
            logger.info("Batch %d/%d resolved %d picks", batch_num, max_batches, resolved)
            if pause_seconds > 0:
                time.sleep(pause_seconds)
        else:
            logger.info("Reached max_batches=%d", max_batches)

        self._metrics.ended_at = datetime.utcnow()
        self._metrics.resolution_rate_pct = self.db.get_resolution_rate()
        logger.info("Run complete — final metrics: %s", json.dumps(self._metrics.to_dict(), indent=2))
        return self._metrics

    def run_dry_run(self) -> Dict[str, Any]:
        """Preview what would be resolved without writing DB."""
        picks = self.db.get_unresolved_picks(batch_size=self.batch_size)
        symbols = list({p.symbol for p in picks if p.symbol})
        prices = self.fetcher.fetch_batch(symbols)
        preview: List[Dict[str, Any]] = []
        for pick in picks:
            price = prices.get(pick.symbol)
            if price:
                result = PnLCalculator.compute(pick, price)
                preview.append(
                    {
                        "pick_id": pick.pick_id,
                        "symbol": pick.symbol,
                        "asset_class": pick.asset_class,
                        "outcome": result.outcome.value,
                        "pnl_pct": round(result.pnl_pct, 6),
                        "exit_price": result.exit_price_used,
                    }
                )
            else:
                preview.append(
                    {
                        "pick_id": pick.pick_id,
                        "symbol": pick.symbol,
                        "error": "price_unavailable",
                    }
                )
        return {
            "run_id": self._metrics.run_id,
            "preview_count": len(preview),
            "would_resolve": len([p for p in preview if "error" not in p]),
            "sample": preview[:20],
        }

    def close(self) -> None:
        self.fetcher.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Outcome Resolver V2")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--max-batches", type=int, default=1000)
    parser.add_argument("--pause", type=float, default=5.0)
    parser.add_argument("--db-path", default=DB_PATH)
    parser.add_argument("--cache-db", default=CACHE_DB_PATH)
    args = parser.parse_args()

    cache = PriceCache(db_path=args.cache_db)
    fetcher = PriceFetcher(cache=cache)
    db = OutcomeDatabase(db_path=args.db_path)
    resolver = OutcomeResolver(db=db, fetcher=fetcher, batch_size=args.batch_size)

    if args.dry_run:
        preview = resolver.run_dry_run()
        print(json.dumps(preview, indent=2))
    else:
        metrics = resolver.run_continuous(
            max_batches=args.max_batches, pause_seconds=args.pause
        )
        print(json.dumps(metrics.to_dict(), indent=2))


if __name__ == "__main__":
    main()
