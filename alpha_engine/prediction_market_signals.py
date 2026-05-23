#!/usr/bin/env python3
"""
Prediction Market Signal Engine — Multi-Source Alpha Generation
===============================================================
Extracts directional trading signals from Polymarket and Kalshi prediction
markets.  Converts crowd-implied probabilities into actionable LONG/SHORT
picks with calibrated confidence scores.

Architecture
------------
+ Polymarket Gamma API  ──▶  Event metadata + market definitions
+ Polymarket CLOB API   ──▶  Price history + live order book
+ Kalshi API            ──▶  CFTC-regulated crypto series
                │
                ▼
    ┌───────────────────────┐
    │  Signal Extractors    │
    │  • Implied Prob Curve │
    │  • Prob Momentum      │
    │  • Dip Skew           │
    └───────────┬───────────┘
                │
                ▼
    ┌───────────────────────┐
    │  Consensus Scorer     │
    │  (weighted ensemble)  │
    └───────────┬───────────┘
                │
                ▼
    ┌───────────────────────┐
    │  Signal Quality Track │
    │  • Accuracy monitor   │
    │  • Calibration score  │
    └───────────┬───────────┘
                │
                ▼
    ┌───────────────────────┐
    │  Trading Signal Output│
    │  (premium_signals.json)│
    └───────────────────────┘

Signal Strategies
-----------------
1. Implied Probability Curve  (wt 25%)
   Build cumulative distribution from "reach $X" / "dip $Y" markets.
   Compare distribution median to spot price for directional bias.

2. Probability Momentum       (wt 40%)  ◀── LEADING INDICATOR
   4-hour rate-of-change in probabilities.
   |Δprob| > 5%  ⇒  sharp crowd re-positioning precedes spot moves.

3. Dip Probability Skew       (wt 35%)
   Sum(dip_probs) / (sum(dip_probs) + sum(reach_probs)).
   Skew > 0.6  ⇒  fear dominant (bearish).
   Skew < 0.4  ⇒  greed dominant (bullish).

Consensus Score → Signal Mapping
--------------------------------
  > 70   → STRONG_BULLISH
  55-70  → BULLISH
  45-55  → NEUTRAL
  30-45  → BEARISH
  < 30   → STRONG_BEARISH

Integration
-----------
- Read-only API access (no key required for Polymarket public data)
- Kalshi requires optional API key for production limits
- Caches price history to SQLite to respect rate limits
- Outputs signals compatible with alpha_engine/data/premium_signals.json
- Designed for GitHub Actions: hourly (momentum) + daily (curve) schedules

Author: Alpha Engine Team
Date: 2026-05-20
"""

from __future__ import annotations

import json
import logging
import math
import os
import sqlite3
import time
import warnings
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)
from urllib.parse import urlencode

import numpy as np
import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("prediction_market_signals")
warnings.filterwarnings("ignore", category=RuntimeWarning)

# ---------------------------------------------------------------------------
# Constants & Configuration
# ---------------------------------------------------------------------------

DATE_FMT = "%Y-%m-%d"
DT_FMT = "%Y-%m-%dT%H:%M:%SZ"

# ── Polymarket Endpoints ──────────────────────────────────────────────────
GAMMA_API_BASE = "https://gamma-api.polymarket.com"
CLOB_API_BASE = "https://clob.polymarket.com"

# ── Kalshi Endpoints ──────────────────────────────────────────────────────
KALSHI_API_BASE = "https://api.elections.kalshi.com/trade-api/v2"
KALSHI_API_BASE_V1 = "https://trading-api.kalshi.com/trade-api/v1"

# ── Cache ─────────────────────────────────────────────────────────────────
DEFAULT_CACHE_DIR = Path(__file__).parent / "alpha_engine" / "data"
DEFAULT_CACHE_DB = DEFAULT_CACHE_DIR / "pm_cache.db"

# ── Signal Weights ────────────────────────────────────────────────────────
WT_MOMENTUM = 0.40
WT_DIP_SKEW = 0.35
WT_IMPLIED_CURVE = 0.25

# ── Thresholds ────────────────────────────────────────────────────────────
MOMENTUM_THRESHOLD = 0.05  # 5% probability change in 4h window
MOMENTUM_WINDOW_HOURS = 4
DIP_SKEW_BEARISH = 0.60
DIP_SKEW_BULLISH = 0.40
SCORE_STRONG_BULL = 70
SCORE_BULL = 55
SCORE_NEUTRAL_LOW = 45
SCORE_BEAR = 30

# ── Polymarket Crypto Market Filters ──────────────────────────────────────
CRYPTO_TAGS = {"crypto", "bitcoin", "ethereum", "solana", "btc", "eth", "sol"}
CRYPTO_KEYWORDS = {
    "bitcoin", "btc", "ethereum", "eth", "solana", "sol",
    "crypto", "cryptocurrency", "blockchain",
}

# Key Polymarket crypto event slugs (known high-volume markets)
PM_CRYPTO_SLUGS = {
    "btc": [
        "bitcoin-price-2026",
        "bitcoin-all-time-high-2026",
        "bitcoin-above-100k",
        "bitcoin-monthly-target",
        "btc-price-june-2026",
        "bitcoin-dip-2026",
    ],
    "eth": [
        "ethereum-price-2026",
        "eth-above-5000",
        "ethereum-monthly-target",
        "eth-dip-2026",
    ],
    "sol": [
        "solana-price-2026",
        "sol-above-250",
        "solana-monthly-target",
        "sol-dip-2026",
    ],
}

# ── Kalshi Crypto Series ──────────────────────────────────────────────────
KALSHI_CRYPTO_SERIES: Tuple[str, ...] = (
    "KXBTC", "KXETH", "KXSOL", "KXDOGE", "KXXRP",
    "KXAVAX", "KXLINK", "KXDOT", "KXLTC",
)

# ── Supported output symbols ──────────────────────────────────────────────
PM_TO_SYMBOL: Dict[str, str] = {
    "bitcoin": "BTCUSDT",
    "btc": "BTCUSDT",
    "ethereum": "ETHUSDT",
    "eth": "ETHUSDT",
    "solana": "SOLUSDT",
    "sol": "SOLUSDT",
}


# ===========================================================================
# SECTION 1: ENUMS & DATA CLASSES
# ===========================================================================


class SignalDirection(Enum):
    """Trading signal directions derived from prediction market consensus."""

    STRONG_BULLISH = "STRONG_BULLISH"
    BULLISH = "BULLISH"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"
    STRONG_BEARISH = "STRONG_BEARISH"


class SignalSource(Enum):
    """Origin system for the trading signal."""

    POLYMARKET = "polymarket"
    KALSHI = "kalshi"
    ENSEMBLE = "ensemble"


class SignalStrategy(Enum):
    """Strategy taxonomy for prediction market derived signals."""

    PM_IMPLIED_CURVE = "pm_implied_curve"
    PM_PROB_MOMENTUM = "pm_probability_momentum"
    PM_DIP_SKEW = "pm_dip_skew"
    PM_CONSENSUS = "pm_consensus"
    KALSHI_CRYPTO = "kalshi_crypto"


@dataclass
class PMPricePoint:
    """Single price history point from Polymarket CLOB."""

    timestamp: str
    price: float  # 0.0 - 1.0 implied probability
    volume: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PMMarket:
    """Polymarket market definition (from Gamma API)."""

    market_id: str
    event_id: str
    question: str
    slug: str
    condition_id: str
    token_ids: List[str]
    yes_token_id: Optional[str] = None
    no_token_id: Optional[str] = None
    volume: float = 0.0
    liquidity: float = 0.0
    outcomes: List[str] = field(default_factory=list)
    outcome_prices: List[float] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    end_date: Optional[str] = None
    active: bool = True
    asset: Optional[str] = None  # btc, eth, sol, etc.
    market_type: Optional[str] = None  # 'reach', 'dip', 'narrative'
    target_price: Optional[float] = None  # price target if applicable

    def best_yes_price(self) -> float:
        """Return best (highest) YES price from outcome_prices."""
        if not self.outcome_prices:
            return 0.0
        return max(self.outcome_prices)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PMEvent:
    """Polymarket event (contains multiple markets)."""

    event_id: str
    title: str
    slug: str
    description: Optional[str] = None
    markets: List[PMMarket] = field(default_factory=list)
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    volume: float = 0.0
    liquidity: float = 0.0
    end_date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["markets"] = [m.to_dict() for m in self.markets]
        return d


@dataclass
class ProbabilityMomentumReading:
    """Snapshot of probability momentum for a single market."""

    market_id: str
    market_question: str
    current_prob: float
    prob_4h_ago: float
    delta: float
    pct_change: float
    direction: str  # 'UP' | 'DOWN' | 'FLAT'
    signal_time: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DipSkewReading:
    """Dip vs reach probability skew for a crypto asset."""

    asset: str  # btc, eth, sol
    dip_prob_sum: float
    reach_prob_sum: float
    skew_ratio: float  # dip / (dip + reach)
    num_dip_markets: int
    num_reach_markets: int
    signal_time: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImpliedCurveReading:
    """Implied probability curve analysis for a crypto asset."""

    asset: str
    median_implied_price: float
    spot_price: float
    price_premium: float  # (median - spot) / spot
    above_prob: float  # probability above spot
    below_prob: float  # probability below spot
    num_markets: int
    signal_time: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConsensusScore:
    """Combined prediction market consensus."""

    asset: str
    score: float  # 0-100
    direction: SignalDirection
    momentum_component: float
    dip_skew_component: float
    implied_curve_component: float
    momentum_detail: Optional[ProbabilityMomentumReading] = None
    dip_skew_detail: Optional[DipSkewReading] = None
    implied_curve_detail: Optional[ImpliedCurveReading] = None
    sources: List[str] = field(default_factory=list)
    signal_time: str = field(default_factory=lambda: datetime.utcnow().strftime(DT_FMT))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset": self.asset,
            "score": round(self.score, 2),
            "direction": self.direction.value,
            "momentum_component": round(self.momentum_component, 4),
            "dip_skew_component": round(self.dip_skew_component, 4),
            "implied_curve_component": round(self.implied_curve_component, 4),
            "sources": self.sources,
            "signal_time": self.signal_time,
        }


@dataclass
class TradingSignal:
    """Final trading signal compatible with premium_signals.json."""

    symbol: str
    direction: str  # LONG | SHORT
    confidence: float  # 0.0 - 1.0
    source_system: str = "prediction_market"
    strategy: str = "pm_consensus"
    asset_class: str = "CRYPTO"
    signal_time: str = field(default_factory=lambda: datetime.utcnow().strftime(DT_FMT))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AccuracyRecord:
    """Single resolved market accuracy record."""

    market_id: str
    source: str  # polymarket | kalshi
    market_type: str  # reach | dip | narrative
    asset: str
    predicted_prob: float
    actual_outcome: int  # 0 or 1
    resolved_correct: bool
    resolve_date: str
    days_to_resolve: int
    signal_time: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ===========================================================================
# SECTION 2: CACHE MANAGER
# ===========================================================================


class PMCacheManager:
    """SQLite-backed cache for Polymarket / Kalshi API responses.

    Minimises redundant API calls and respects rate limits.
    TTL defaults: price history = 15 min, event metadata = 60 min.
    """

    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        price_ttl_seconds: int = 900,
        meta_ttl_seconds: int = 3600,
    ) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_CACHE_DB
        self.price_ttl = price_ttl_seconds
        self.meta_ttl = meta_ttl_seconds
        self._ensure_db()

    def _ensure_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.db_path), timeout=30) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS price_cache (
                    token_id   TEXT PRIMARY KEY,
                    data_json  TEXT NOT NULL,
                    fetched_at INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS meta_cache (
                    cache_key  TEXT PRIMARY KEY,
                    data_json  TEXT NOT NULL,
                    fetched_at INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS accuracy_log (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    market_id  TEXT NOT NULL,
                    source     TEXT NOT NULL,
                    market_type TEXT,
                    asset      TEXT,
                    predicted_prob REAL,
                    actual_outcome INTEGER,
                    resolved_correct INTEGER,
                    resolve_date TEXT,
                    days_to_resolve INTEGER,
                    signal_time TEXT,
                    created_at INTEGER DEFAULT (unixepoch())
                )
                """
            )
            conn.commit()

    # ── Price history cache ─────────────────────────────────────────────────

    def get_price_history(self, token_id: str) -> Optional[List[Dict[str, Any]]]:
        cutoff = int(time.time()) - self.price_ttl
        with sqlite3.connect(str(self.db_path), timeout=30) as conn:
            row = conn.execute(
                "SELECT data_json FROM price_cache WHERE token_id = ? AND fetched_at > ?",
                (token_id, cutoff),
            ).fetchone()
        if row:
            logger.debug("Cache hit: price_history %s", token_id)
            return json.loads(row[0])
        return None

    def set_price_history(self, token_id: str, data: List[Dict[str, Any]]) -> None:
        with sqlite3.connect(str(self.db_path), timeout=30) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO price_cache (token_id, data_json, fetched_at)
                   VALUES (?, ?, ?)""",
                (token_id, json.dumps(data), int(time.time())),
            )
            conn.commit()

    # ── Generic metadata cache ──────────────────────────────────────────────

    def get_meta(self, cache_key: str) -> Optional[Any]:
        cutoff = int(time.time()) - self.meta_ttl
        with sqlite3.connect(str(self.db_path), timeout=30) as conn:
            row = conn.execute(
                "SELECT data_json FROM meta_cache WHERE cache_key = ? AND fetched_at > ?",
                (cache_key, cutoff),
            ).fetchone()
        if row:
            logger.debug("Cache hit: meta %s", cache_key)
            return json.loads(row[0])
        return None

    def set_meta(self, cache_key: str, data: Any) -> None:
        with sqlite3.connect(str(self.db_path), timeout=30) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO meta_cache (cache_key, data_json, fetched_at)
                   VALUES (?, ?, ?)""",
                (cache_key, json.dumps(data), int(time.time())),
            )
            conn.commit()

    # ── Accuracy log ────────────────────────────────────────────────────────

    def log_accuracy(self, record: AccuracyRecord) -> None:
        with sqlite3.connect(str(self.db_path), timeout=30) as conn:
            conn.execute(
                """INSERT INTO accuracy_log
                   (market_id, source, market_type, asset, predicted_prob,
                    actual_outcome, resolved_correct, resolve_date,
                    days_to_resolve, signal_time)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.market_id, record.source, record.market_type,
                    record.asset, record.predicted_prob, record.actual_outcome,
                    int(record.resolved_correct), record.resolve_date,
                    record.days_to_resolve, record.signal_time,
                ),
            )
            conn.commit()

    def get_accuracy_history(
        self,
        asset: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 1000,
    ) -> List[AccuracyRecord]:
        query = "SELECT * FROM accuracy_log WHERE 1=1"
        params: List[Any] = []
        if asset:
            query += " AND asset = ?"
            params.append(asset)
        if source:
            query += " AND source = ?"
            params.append(source)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(str(self.db_path), timeout=30) as conn:
            rows = conn.execute(query, params).fetchall()

        records: List[AccuracyRecord] = []
        cols = [desc[0] for desc in conn.execute(
            "SELECT * FROM accuracy_log LIMIT 0"
        ).description]

        for row in rows:
            d = dict(zip(cols, row))
            records.append(AccuracyRecord(
                market_id=d["market_id"],
                source=d["source"],
                market_type=d.get("market_type", ""),
                asset=d.get("asset", ""),
                predicted_prob=d.get("predicted_prob", 0.0),
                actual_outcome=d.get("actual_outcome", 0),
                resolved_correct=bool(d.get("resolved_correct", 0)),
                resolve_date=d.get("resolve_date", ""),
                days_to_resolve=d.get("days_to_resolve", 0),
                signal_time=d.get("signal_time", ""),
            ))
        return records

    # ── Calibration helpers ─────────────────────────────────────────────────

    def calibration_by_bins(
        self,
        asset: Optional[str] = None,
        num_bins: int = 10,
    ) -> pd.DataFrame:
        """Return calibration data: predicted probability bins vs actual frequency."""
        records = self.get_accuracy_history(asset=asset, limit=5000)
        if not records:
            return pd.DataFrame(columns=["bin_min", "bin_max", "predicted_avg",
                                         "actual_freq", "count"])

        df = pd.DataFrame([r.to_dict() for r in records])
        df["bin"] = pd.cut(df["predicted_prob"], bins=np.linspace(0.0, 1.0, num_bins + 1), include_lowest=True)
        grouped = df.groupby("bin", observed=False).agg(
            predicted_avg=("predicted_prob", "mean"),
            actual_freq=("actual_outcome", "mean"),
            count=("actual_outcome", "size"),
        ).reset_index()
        grouped["bin_min"] = grouped["bin"].apply(lambda x: x.left if pd.notna(x) else None)
        grouped["bin_max"] = grouped["bin"].apply(lambda x: x.right if pd.notna(x) else None)
        return grouped[["bin_min", "bin_max", "predicted_avg", "actual_freq", "count"]]


# ===========================================================================
# SECTION 3: POLYMARKET GAMMA API CLIENT
# ===========================================================================


class PolymarketGammaClient:
    """Client for Polymarket Gamma API (metadata + event discovery).

    All endpoints are public-read — no API key required.
    """

    BASE = GAMMA_API_BASE
    _TIMEOUT = 30
    _MAX_RETRIES = 3
    _BACKOFF = 1.5

    def __init__(self, cache: Optional[PMCacheManager] = None) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "AlphaEngine-PM-Signals/1.0",
        })
        self.cache = cache or PMCacheManager()

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Cached GET with retry + exponential backoff."""
        cache_key = f"gamma:{endpoint}:{urlencode(params or {})}"
        cached = self.cache.get_meta(cache_key)
        if cached is not None:
            return cached

        url = f"{self.BASE}{endpoint}"
        for attempt in range(self._MAX_RETRIES):
            try:
                resp = self.session.get(url, params=params, timeout=self._TIMEOUT)
                if resp.status_code == 429:
                    sleep_time = self._BACKOFF ** attempt * 2
                    logger.warning("Rate limited on Gamma API, sleeping %.1fs", sleep_time)
                    time.sleep(sleep_time)
                    continue
                resp.raise_for_status()
                data = resp.json()
                self.cache.set_meta(cache_key, data)
                return data
            except requests.exceptions.RequestException as exc:
                logger.warning("Gamma API request failed (attempt %d): %s", attempt + 1, exc)
                time.sleep(self._BACKOFF ** attempt)
        logger.error("Gamma API exhausted retries for %s", url)
        return None

    # ── Event discovery ─────────────────────────────────────────────────────

    def fetch_active_crypto_events(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[PMEvent]:
        """Fetch active events tagged with crypto-related keywords.

        Queries /events endpoint with tag filter then filters client-side
        for crypto relevance.
        """
        params: Dict[str, Any] = {
            "active": "true",
            "closed": "false",
            "limit": limit,
            "offset": offset,
            "order": "volume",
            "ascending": "false",
        }
        data = self._get("/events", params)
        if not data or not isinstance(data, list):
            return []

        events: List[PMEvent] = []
        for ev in data:
            tags = {t.lower() for t in ev.get("tags", [])}
            title_lower = ev.get("title", "").lower()
            desc_lower = (ev.get("description") or "").lower()
            is_crypto = bool(
                CRYPTO_TAGS & tags
                or any(kw in title_lower for kw in CRYPTO_KEYWORDS)
                or any(kw in desc_lower for kw in CRYPTO_KEYWORDS)
            )
            if not is_crypto:
                continue

            event = self._parse_event(ev)
            events.append(event)

        logger.info("Fetched %d active crypto events from Gamma", len(events))
        return events

    def fetch_event_by_slug(self, slug: str) -> Optional[PMEvent]:
        """Fetch a specific event by its slug identifier."""
        cache_key = f"event_slug:{slug}"
        cached = self.cache.get_meta(cache_key)
        if cached and isinstance(cached, dict):
            return self._dict_to_event(cached)

        data = self._get("/events", {"slug": slug})
        if isinstance(data, list) and data:
            event = self._parse_event(data[0])
            self.cache.set_meta(cache_key, event.to_dict())
            return event
        if isinstance(data, dict):
            event = self._parse_event(data)
            self.cache.set_meta(cache_key, event.to_dict())
            return event
        return None

    def fetch_all_crypto_events_deep(
        self,
        max_pages: int = 10,
    ) -> List[PMEvent]:
        """Paginated fetch of all active crypto events (deep scan)."""
        all_events: List[PMEvent] = []
        for page in range(max_pages):
            events = self.fetch_active_crypto_events(
                limit=100, offset=page * 100
            )
            if not events:
                break
            all_events.extend(events)
            if len(events) < 100:
                break
        logger.info("Deep scan: total %d crypto events", len(all_events))
        return all_events

    def search_markets_by_keyword(
        self,
        keyword: str,
        limit: int = 50,
    ) -> List[PMMarket]:
        """Search markets by keyword in question / title."""
        params = {"active": "true", "archived": "false", "limit": limit}
        data = self._get("/markets", params)
        if not data or not isinstance(data, list):
            return []

        results: List[PMMarket] = []
        keyword_lower = keyword.lower()
        for m in data:
            q = m.get("question", "").lower()
            if keyword_lower in q:
                results.append(self._parse_market(m))
        return results

    # ── Internal parsers ────────────────────────────────────────────────────

    @staticmethod
    def _parse_event(ev: Dict[str, Any]) -> PMEvent:
        """Convert raw Gamma API event dict to PMEvent."""
        event = PMEvent(
            event_id=str(ev.get("id", "")),
            title=ev.get("title", ""),
            slug=ev.get("slug", ""),
            description=ev.get("description"),
            category=ev.get("category"),
            tags=ev.get("tags", []),
            volume=float(ev.get("volume", 0) or 0),
            liquidity=float(ev.get("liquidity", 0) or 0),
            end_date=ev.get("endDate") or ev.get("end_date"),
        )
        for m in ev.get("markets", []):
            event.markets.append(PolymarketGammaClient._parse_market(m))
        return event

    @staticmethod
    def _parse_market(m: Dict[str, Any]) -> PMMarket:
        """Convert raw Gamma API market dict to PMMarket."""
        market = PMMarket(
            market_id=str(m.get("id", "")),
            event_id=str(m.get("eventID") or m.get("event_id", "")),
            question=m.get("question", ""),
            slug=m.get("slug", ""),
            condition_id=str(m.get("conditionId") or m.get("condition_id", "")),
            token_ids=[],
            volume=float(m.get("volume", 0) or 0),
            liquidity=float(m.get("liquidity", 0) or 0),
            outcomes=m.get("outcomes", []) or [],
            outcome_prices=[],
            tags=m.get("tags", []),
            end_date=m.get("endDate") or m.get("end_date"),
            active=bool(m.get("active", True)),
        )
        # Token IDs from clobTokenIds field (can be comma-separated)
        token_ids_raw = m.get("clobTokenIds") or m.get("clob_token_ids", "")
        if token_ids_raw:
            market.token_ids = [t.strip() for t in str(token_ids_raw).split(",") if t.strip()]
            if market.token_ids:
                market.yes_token_id = market.token_ids[0]
                if len(market.token_ids) > 1:
                    market.no_token_id = market.token_ids[1]

        # Outcome prices
        market.outcome_prices = []
        for p in m.get("outcomePrices", []) or []:
            try:
                market.outcome_prices.append(float(p))
            except (TypeError, ValueError):
                market.outcome_prices.append(0.0)

        # Derive asset and market type from question text
        market.asset = _extract_asset_from_question(market.question)
        market.market_type = _classify_market_type(market.question)
        market.target_price = _extract_target_price(market.question)

        return market

    @staticmethod
    def _dict_to_event(d: Dict[str, Any]) -> PMEvent:
        """Reconstruct PMEvent from cached dict."""
        event = PMEvent(
            event_id=d["event_id"],
            title=d["title"],
            slug=d["slug"],
            description=d.get("description"),
            category=d.get("category"),
            tags=d.get("tags", []),
            volume=d.get("volume", 0),
            liquidity=d.get("liquidity", 0),
            end_date=d.get("end_date"),
        )
        for md in d.get("markets", []):
            event.markets.append(PolymarketGammaClient._dict_to_market(md))
        return event

    @staticmethod
    def _dict_to_market(d: Dict[str, Any]) -> PMMarket:
        """Reconstruct PMMarket from cached dict."""
        return PMMarket(
            market_id=d["market_id"],
            event_id=d["event_id"],
            question=d["question"],
            slug=d["slug"],
            condition_id=d["condition_id"],
            token_ids=d.get("token_ids", []),
            yes_token_id=d.get("yes_token_id"),
            no_token_id=d.get("no_token_id"),
            volume=d.get("volume", 0),
            liquidity=d.get("liquidity", 0),
            outcomes=d.get("outcomes", []),
            outcome_prices=d.get("outcome_prices", []),
            tags=d.get("tags", []),
            end_date=d.get("end_date"),
            active=d.get("active", True),
            asset=d.get("asset"),
            market_type=d.get("market_type"),
            target_price=d.get("target_price"),
        )


# ===========================================================================
# SECTION 4: POLYMARKET CLOB API CLIENT
# ===========================================================================


class PolymarketClobClient:
    """Client for Polymarket CLOB API (price history + order book).

    All price-history endpoints are public-read.
    """

    BASE = CLOB_API_BASE
    _TIMEOUT = 30
    _MAX_RETRIES = 3
    _BACKOFF = 1.5

    def __init__(self, cache: Optional[PMCacheManager] = None) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "AlphaEngine-PM-Signals/1.0",
        })
        self.cache = cache or PMCacheManager()

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.BASE}{endpoint}"
        for attempt in range(self._MAX_RETRIES):
            try:
                resp = self.session.get(url, params=params, timeout=self._TIMEOUT)
                if resp.status_code == 429:
                    sleep_time = self._BACKOFF ** attempt * 2
                    logger.warning("Rate limited on CLOB API, sleeping %.1fs", sleep_time)
                    time.sleep(sleep_time)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.RequestException as exc:
                logger.warning("CLOB API request failed (attempt %d): %s", attempt + 1, exc)
                time.sleep(self._BACKOFF ** attempt)
        logger.error("CLOB API exhausted retries for %s", url)
        return None

    # ── Price history ───────────────────────────────────────────────────────

    def fetch_price_history(
        self,
        token_id: str,
        fidelity: str = "hour",
        start_ts: Optional[int] = None,
        end_ts: Optional[int] = None,
    ) -> List[PMPricePoint]:
        """Fetch full price time series for a token.

        Parameters
        ----------
        token_id : str
            CLOB token ID (from Gamma API).
        fidelity : str
            "min", "hour", or "day" candle aggregation.
        start_ts : int, optional
            Unix-epoch start (seconds).
        end_ts : int, optional
            Unix-epoch end (seconds).

        Returns
        -------
        list of PMPricePoint
        """
        # Check cache first
        cached = self.cache.get_price_history(token_id)
        if cached is not None:
            return [PMPricePoint(**p) for p in cached]

        params: Dict[str, Any] = {
            "token_id": token_id,
            "fidelity": fidelity,
        }
        if start_ts:
            params["start_ts"] = start_ts
        if end_ts:
            params["end_ts"] = end_ts

        data = self._get("/prices-history", params)
        if not data or not isinstance(data, dict):
            return []

        history_raw = data.get("history", [])
        points: List[PMPricePoint] = []
        for h in history_raw:
            try:
                points.append(PMPricePoint(
                    timestamp=h.get("t") or h.get("timestamp", ""),
                    price=float(h.get("p") or h.get("price", 0)),
                    volume=float(h.get("v") or h.get("volume", 0)),
                ))
            except (TypeError, ValueError):
                continue

        # Cache successful result
        if points:
            self.cache.set_price_history(token_id, [p.to_dict() for p in points])

        logger.info("Fetched %d price points for token %s", len(points), token_id)
        return points

    def fetch_price_history_bulk(
        self,
        token_ids: List[str],
        fidelity: str = "hour",
    ) -> Dict[str, List[PMPricePoint]]:
        """Fetch price histories for multiple tokens (sequential, rate-aware)."""
        results: Dict[str, List[PMPricePoint]] = {}
        for tid in token_ids:
            results[tid] = self.fetch_price_history(tid, fidelity=fidelity)
            time.sleep(0.2)  # gentle rate limit between calls
        return results

    # ── Order book ──────────────────────────────────────────────────────────

    def fetch_order_book(
        self,
        token_id: str,
    ) -> Dict[str, Any]:
        """Fetch current bid/ask order book for a token.

        Returns dict with keys: bids, asks, last_trade_price, timestamp.
        """
        data = self._get("/book", {"token_id": token_id})
        if not data or not isinstance(data, dict):
            return {"bids": [], "asks": [], "last_trade_price": None, "timestamp": None}

        return {
            "bids": data.get("bids", []),
            "asks": data.get("asks", []),
            "last_trade_price": data.get("last_trade_price"),
            "timestamp": data.get("timestamp"),
            "token_id": token_id,
        }

    def fetch_mid_price(self, token_id: str) -> float:
        """Get mid-market implied probability from best bid/ask."""
        ob = self.fetch_order_book(token_id)
        bids = ob.get("bids", [])
        asks = ob.get("asks", [])
        if not bids and not asks:
            return 0.0
        best_bid = float(bids[0].get("price", 0)) if bids else 0.0
        best_ask = float(asks[0].get("price", 0)) if asks else 0.0
        if best_bid > 0 and best_ask > 0:
            return (best_bid + best_ask) / 2
        return max(best_bid, best_ask)

    # ── Market data batch ───────────────────────────────────────────────────

    def fetch_market_data(self, token_id: str) -> Dict[str, Any]:
        """Aggregate market data: price history + order book for a token."""
        history = self.fetch_price_history(token_id)
        ob = self.fetch_order_book(token_id)
        return {
            "token_id": token_id,
            "price_history": [p.to_dict() for p in history],
            "order_book": ob,
            "last_price": history[-1].price if history else None,
            "data_points": len(history),
        }


# ===========================================================================
# SECTION 5: KALSHI API CLIENT
# ===========================================================================


class KalshiClient:
    """Client for Kalshi API (CFTC-regulated prediction markets).

    Public read-only endpoints work without authentication.
    Authenticated endpoints require API key for higher rate limits.
    """

    BASE = KALSHI_API_BASE
    _TIMEOUT = 30
    _MAX_RETRIES = 3
    _BACKOFF = 1.5

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache: Optional[PMCacheManager] = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("KALSHI_API_KEY")
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "AlphaEngine-Kalshi/1.0",
        })
        if self.api_key:
            self.session.headers["Authorization"] = f"Bearer {self.api_key}"
        self.cache = cache or PMCacheManager()

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        cache_key = f"kalshi:{endpoint}:{urlencode(params or {})}"
        cached = self.cache.get_meta(cache_key)
        if cached is not None:
            return cached

        url = f"{self.BASE}{endpoint}"
        for attempt in range(self._MAX_RETRIES):
            try:
                resp = self.session.get(url, params=params, timeout=self._TIMEOUT)
                if resp.status_code == 429:
                    sleep_time = self._BACKOFF ** attempt * 2
                    logger.warning("Rate limited on Kalshi API, sleeping %.1fs", sleep_time)
                    time.sleep(sleep_time)
                    continue
                if resp.status_code == 401:
                    logger.error("Kalshi auth failed — check API key")
                    return None
                resp.raise_for_status()
                data = resp.json()
                self.cache.set_meta(cache_key, data)
                return data
            except requests.exceptions.RequestException as exc:
                logger.warning("Kalshi API request failed (attempt %d): %s", attempt + 1, exc)
                time.sleep(self._BACKOFF ** attempt)
        logger.error("Kalshi API exhausted retries for %s", url)
        return None

    # ── Series / Markets ────────────────────────────────────────────────────

    def fetch_crypto_series(
        self,
        ticker: str,
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Fetch active markets for a crypto series (e.g. KXBTC).

        Returns list of market dicts with yes_bid, yes_ask, last_price, etc.
        """
        if ticker.upper() not in KALSHI_CRYPTO_SERIES:
            logger.warning("Ticker %s not in known Kalshi crypto series", ticker)

        params: Dict[str, Any] = {
            "series_ticker": ticker.upper(),
            "limit": 100,
        }
        if active_only:
            params["status"] = "open"

        data = self._get("/markets", params)
        if not data or not isinstance(data, dict):
            return []

        markets = data.get("markets", [])
        logger.info("Kalshi %s: fetched %d markets", ticker.upper(), len(markets))
        return markets

    def fetch_crypto_series_bulk(
        self,
        tickers: Optional[List[str]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch markets for multiple crypto series."""
        tickers = tickers or list(KALSHI_CRYPTO_SERIES)
        results: Dict[str, List[Dict[str, Any]]] = {}
        for t in tickers:
            results[t.upper()] = self.fetch_crypto_series(t)
            time.sleep(0.3)  # gentle rate limiting
        return results

    def fetch_market_orderbook(self, market_id: str) -> Dict[str, Any]:
        """Fetch order book for a specific Kalshi market."""
        data = self._get(f"/markets/{market_id}/orderbook")
        if not data:
            return {"yes_bids": [], "yes_asks": [], "no_bids": [], "no_asks": []}
        return {
            "yes_bids": data.get("orderbook", {}).get("yes", []),
            "yes_asks": data.get("orderbook", {}).get("yes_asks", []),
            "no_bids": data.get("orderbook", {}).get("no", []),
            "no_asks": data.get("orderbook", {}).get("no_asks", []),
        }

    def extract_yes_probability(self, market: Dict[str, Any]) -> float:
        """Extract YES probability from Kalshi market data."""
        # Try last_price first, then midpoint of yes_bid / yes_ask
        last = market.get("last_price")
        if last is not None:
            try:
                return float(last)
            except (TypeError, ValueError):
                pass

        yes_bid = market.get("yes_bid")
        yes_ask = market.get("yes_ask")
        if yes_bid is not None and yes_ask is not None:
            try:
                return (float(yes_bid) + float(yes_ask)) / 2
            except (TypeError, ValueError):
                pass
        if yes_bid is not None:
            try:
                return float(yes_bid)
            except (TypeError, ValueError):
                pass
        return 0.5  # default neutral

    def fetch_series_trades(
        self,
        series_ticker: str,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Fetch recent trade history for a series."""
        data = self._get(
            "/trades",
            {"series_ticker": series_ticker.upper(), "limit": limit},
        )
        return data.get("trades", []) if data else []


# ===========================================================================
# SECTION 6: TEXT UTILS (asset / type extraction)
# ===========================================================================


def _extract_asset_from_question(question: str) -> Optional[str]:
    """Infer crypto asset from market question text."""
    q = question.lower()
    if "bitcoin" in q or " btc" in q:
        return "btc"
    if "ethereum" in q or " eth" in q:
        return "eth"
    if "solana" in q or " sol" in q:
        return "sol"
    if "dogecoin" in q or " doge" in q:
        return "doge"
    if "xrp" in q or "ripple" in q:
        return "xrp"
    if "cardano" in q or " ada" in q:
        return "ada"
    if "avalanche" in q or " avax" in q:
        return "avax"
    if "chainlink" in q or " link" in q:
        return "link"
    return None


def _classify_market_type(question: str) -> Optional[str]:
    """Classify market as 'reach', 'dip', or 'narrative'."""
    q = question.lower()
    if any(w in q for w in ("dip", "below", "under", "fall to", "drop to")):
        return "dip"
    if any(w in q for w in ("reach", "above", "over", "hit", "cross")):
        return "reach"
    return "narrative"


def _extract_target_price(question: str) -> Optional[float]:
    """Try to extract a numeric price target from question text."""
    import re
    # Match $X,XXX or $XX,XXX or $X or USD X,XXX patterns
    matches = re.findall(r'[\$]\s*([\d,]+(?:\.\d+)?)', question)
    if matches:
        try:
            return float(matches[0].replace(",", ""))
        except ValueError:
            pass
    # Match "USD 100,000" patterns
    matches = re.findall(r'USD\s+([\d,]+(?:\.\d+)?)', question)
    if matches:
        try:
            return float(matches[0].replace(",", ""))
        except ValueError:
            pass
    return None


# ===========================================================================
# SECTION 7: SIGNAL EXTRACTORS
# ===========================================================================


class SignalExtractor:
    """Core signal extraction engine.

    Operates on fetched Polymarket events + price histories to produce
    ImpliedCurveReading, ProbabilityMomentumReading, and DipSkewReading.
    """

    def __init__(
        self,
        gamma: Optional[PolymarketGammaClient] = None,
        clob: Optional[PolymarketClobClient] = None,
        cache: Optional[PMCacheManager] = None,
    ) -> None:
        self.gamma = gamma or PolymarketGammaClient()
        self.clob = clob or PolymarketClobClient()
        self.cache = cache or PMCacheManager()

    # ── 7A. Implied Probability Curve ───────────────────────────────────────

    def implied_probability_curve(
        self,
        asset: str,
        events: Optional[List[PMEvent]] = None,
    ) -> Optional[ImpliedCurveReading]:
        """Build cumulative probability distribution from reach/dip markets.

        Compare distribution median to spot price for directional bias.

        Parameters
        ----------
        asset : str
            "btc", "eth", or "sol"
        events : list of PMEvent, optional
            Pre-fetched events. If None, fetches from Gamma API.

        Returns
        -------
        ImpliedCurveReading or None
        """
        asset = asset.lower()
        if events is None:
            events = self.gamma.fetch_active_crypto_events(limit=100)

        # Collect relevant markets with target prices
        reach_markets: List[Tuple[float, float]] = []  # (target_price, prob)
        dip_markets: List[Tuple[float, float]] = []    # (target_price, prob)

        for ev in events:
            for m in ev.markets:
                if m.asset != asset:
                    continue
                prob = m.best_yes_price()
                if m.target_price is None:
                    continue
                if m.market_type == "reach":
                    reach_markets.append((m.target_price, prob))
                elif m.market_type == "dip":
                    dip_markets.append((m.target_price, prob))

        if not reach_markets and not dip_markets:
            logger.warning("No target-price markets found for %s", asset)
            return None

        # Get spot price (from most liquid reach market probability)
        # Use the median target_price weighted by probability as proxy
        all_targets = reach_markets + dip_markets
        if not all_targets:
            return None

        # Weighted median
        targets = sorted(all_targets, key=lambda x: x[0])
        weights = [p for _, p in targets]
        prices = [t for t, _ in targets]

        median_implied = self._weighted_median(prices, weights)

        # Approximate spot from highest-volume reach market
        spot_price = self._estimate_spot_price(asset, reach_markets)
        if spot_price is None:
            spot_price = median_implied

        # Compute above/below probability from reach markets
        above_prob = sum(p for t, p in reach_markets if t > spot_price) / max(len(reach_markets), 1)
        below_prob = 1.0 - above_prob

        premium = (median_implied - spot_price) / spot_price if spot_price else 0.0

        reading = ImpliedCurveReading(
            asset=asset,
            median_implied_price=median_implied,
            spot_price=spot_price,
            price_premium=premium,
            above_prob=above_prob,
            below_prob=below_prob,
            num_markets=len(all_targets),
            signal_time=datetime.utcnow().strftime(DT_FMT),
        )
        logger.info(
            "ImpliedCurve %s: median=$%.1f spot=$%.1f premium=%.2f%% above_prob=%.2f",
            asset, median_implied, spot_price, premium * 100, above_prob,
        )
        return reading

    @staticmethod
    def _weighted_median(values: List[float], weights: List[float]) -> float:
        """Compute weighted median."""
        if not values:
            return 0.0
        pairs = sorted(zip(values, weights))
        sorted_vals = [v for v, _ in pairs]
        sorted_weights = [w for _, w in pairs]
        total_w = sum(sorted_weights)
        if total_w == 0:
            return sorted_vals[len(sorted_vals) // 2]
        cumsum = 0.0
        for v, w in zip(sorted_vals, sorted_weights):
            cumsum += w
            if cumsum >= total_w / 2:
                return v
        return sorted_vals[-1]

    @staticmethod
    def _estimate_spot_price(
        asset: str,
        reach_markets: List[Tuple[float, float]],
    ) -> Optional[float]:
        """Estimate current spot price from market probabilities.

        Uses the price target where probability is closest to 0.5
        (market is most uncertain = closest to current spot).
        """
        if not reach_markets:
            return None
        # Find target price with probability closest to 0.5
        closest = min(reach_markets, key=lambda x: abs(x[1] - 0.5))
        return closest[0]

    # ── 7B. Probability Momentum ────────────────────────────────────────────

    def probability_momentum(
        self,
        asset: str,
        events: Optional[List[PMEvent]] = None,
        window_hours: int = MOMENTUM_WINDOW_HOURS,
    ) -> List[ProbabilityMomentumReading]:
        """Calculate 4-hour probability momentum for all asset markets.

        Polls price history, computes rate-of-change.
        |Δprob| > MOMENTUM_THRESHOLD → sharp crowd repositioning.

        Parameters
        ----------
        asset : str
            "btc", "eth", or "sol"
        events : list of PMEvent, optional
        window_hours : int
            Lookback window in hours.

        Returns
        -------
        list of ProbabilityMomentumReading
        """
        asset = asset.lower()
        if events is None:
            events = self.gamma.fetch_active_crypto_events(limit=100)

        readings: List[ProbabilityMomentumReading] = []
        for ev in events:
            for m in ev.markets:
                if m.asset != asset:
                    continue
                token_id = m.yes_token_id
                if not token_id:
                    continue

                history = self.clob.fetch_price_history(token_id, fidelity="hour")
                if len(history) < window_hours:
                    continue

                current = history[-1].price
                past = history[-(window_hours + 1)].price if len(history) > window_hours else history[0].price
                delta = current - past
                pct_change = (delta / past) if past != 0 else 0.0

                direction = "UP" if delta > 0 else "DOWN" if delta < 0 else "FLAT"

                readings.append(ProbabilityMomentumReading(
                    market_id=m.market_id,
                    market_question=m.question,
                    current_prob=current,
                    prob_4h_ago=past,
                    delta=delta,
                    pct_change=pct_change,
                    direction=direction,
                    signal_time=datetime.utcnow().strftime(DT_FMT),
                ))

        readings.sort(key=lambda r: abs(r.pct_change), reverse=True)
        logger.info(
            "ProbabilityMomentum %s: computed for %d markets",
            asset, len(readings),
        )
        return readings

    def strongest_momentum_signals(
        self,
        asset: str,
        threshold: float = MOMENTUM_THRESHOLD,
        top_n: int = 5,
    ) -> List[ProbabilityMomentumReading]:
        """Return markets with |probability change| > threshold."""
        all_readings = self.probability_momentum(asset)
        filtered = [r for r in all_readings if abs(r.pct_change) >= threshold]
        return filtered[:top_n]

    # ── 7C. Dip Probability Skew ────────────────────────────────────────────

    def dip_probability_skew(
        self,
        asset: str,
        events: Optional[List[PMEvent]] = None,
    ) -> Optional[DipSkewReading]:
        """Compute dip vs reach probability skew.

        skew = sum(dip_probs) / (sum(dip_probs) + sum(reach_probs))
        skew > 0.6 → fear dominant (bearish)
        skew < 0.4 → greed dominant (bullish)
        0.4-0.6 → neutral

        Parameters
        ----------
        asset : str
        events : list of PMEvent, optional

        Returns
        -------
        DipSkewReading or None
        """
        asset = asset.lower()
        if events is None:
            events = self.gamma.fetch_active_crypto_events(limit=100)

        dip_sum = 0.0
        reach_sum = 0.0
        num_dip = 0
        num_reach = 0

        for ev in events:
            for m in ev.markets:
                if m.asset != asset:
                    continue
                prob = m.best_yes_price()
                if m.market_type == "dip":
                    dip_sum += prob
                    num_dip += 1
                elif m.market_type == "reach":
                    reach_sum += prob
                    num_reach += 1

        total = dip_sum + reach_sum
        if total == 0:
            logger.warning("No dip/reach markets for skew calculation: %s", asset)
            return None

        skew = dip_sum / total

        reading = DipSkewReading(
            asset=asset,
            dip_prob_sum=dip_sum,
            reach_prob_sum=reach_sum,
            skew_ratio=skew,
            num_dip_markets=num_dip,
            num_reach_markets=num_reach,
            signal_time=datetime.utcnow().strftime(DT_FMT),
        )
        logger.info(
            "DipSkew %s: skew=%.3f (dip=%.2f, reach=%.2f, n_dip=%d, n_reach=%d)",
            asset, skew, dip_sum, reach_sum, num_dip, num_reach,
        )
        return reading

    # ── 7D. Kalshi Signal Extractor ─────────────────────────────────────────

    def kalshi_crypto_signals(
        self,
        kalshi: Optional[KalshiClient] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Extract signals from Kalshi crypto series.

        For each crypto series, compute average YES probability across
        all active markets as a sentiment proxy.

        Returns
        -------
        dict: ticker -> list of signal dicts
        """
        kalshi = kalshi or KalshiClient()
        all_markets = kalshi.fetch_crypto_series_bulk()

        results: Dict[str, List[Dict[str, Any]]] = {}
        for ticker, markets in all_markets.items():
            signals: List[Dict[str, Any]] = []
            for m in markets:
                prob = kalshi.extract_yes_probability(m)
                # Probability > 0.6 → bullish (market thinks YES will happen)
                direction = "BULLISH" if prob > 0.6 else "BEARISH" if prob < 0.4 else "NEUTRAL"
                signals.append({
                    "market_id": m.get("id", ""),
                    "ticker": ticker,
                    "question": m.get("title", ""),
                    "yes_probability": prob,
                    "direction": direction,
                    "yes_bid": m.get("yes_bid"),
                    "yes_ask": m.get("yes_ask"),
                    "volume": m.get("volume", 0),
                    "expiration": m.get("expiration_date"),
                    "source": "kalshi",
                })
            # Sort by volume descending
            signals.sort(key=lambda x: x.get("volume", 0), reverse=True)
            results[ticker] = signals

        logger.info("Kalshi signals extracted for %d series", len(results))
        return results


# ===========================================================================
# SECTION 8: CONSENSUS SCORER
# ===========================================================================


class ConsensusScorer:
    """Combine individual signal readings into a unified 0-100 consensus score.

    Weights
    -------
    • Probability Momentum : 40% (leading indicator)
    • Dip Probability Skew : 35%
    • Implied Curve        : 25%
    """

    def __init__(
        self,
        wt_momentum: float = WT_MOMENTUM,
        wt_dip_skew: float = WT_DIP_SKEW,
        wt_implied: float = WT_IMPLIED_CURVE,
    ) -> None:
        self.wt_momentum = wt_momentum
        self.wt_dip_skew = wt_dip_skew
        self.wt_implied = wt_implied
        self._validate_weights()

    def _validate_weights(self) -> None:
        total = self.wt_momentum + self.wt_dip_skew + self.wt_implied
        if not 0.99 <= total <= 1.01:
            raise ValueError(f"Signal weights must sum to 1.0, got {total}")

    @staticmethod
    def momentum_to_component(readings: List[ProbabilityMomentumReading]) -> float:
        """Convert momentum readings to 0-100 component score.

        Average of strongest |pct_change| scaled to 0-100.
        Direction: if more readings are UP → bullish (high score),
                   if more are DOWN → bearish (low score).
        """
        if not readings:
            return 50.0  # neutral default

        # Take top 3 by absolute change
        top = sorted(readings, key=lambda r: abs(r.pct_change), reverse=True)[:3]
        avg_change = np.mean([r.pct_change for r in top])

        # Scale: ±20% change → 0 or 100; 0 change → 50
        score = 50.0 + (avg_change * 250.0)  # 20% → 100, -20% → 0
        return float(np.clip(score, 0, 100))

    @staticmethod
    def dip_skew_to_component(reading: Optional[DipSkewReading]) -> float:
        """Convert dip skew to 0-100 component score.

        skew=0.0 (all reach/greed) → 100 (bullish)
        skew=1.0 (all dip/fear)    → 0   (bearish)
        """
        if reading is None:
            return 50.0
        # Invert: 0 skew (no fear) = 100 bullish
        score = (1.0 - reading.skew_ratio) * 100.0
        return float(np.clip(score, 0, 100))

    @staticmethod
    def implied_curve_to_component(reading: Optional[ImpliedCurveReading]) -> float:
        """Convert implied curve to 0-100 component score.

        Premium > 0 (implied > spot) → bullish (high score)
        Premium < 0 (implied < spot) → bearish (low score)
        """
        if reading is None:
            return 50.0
        # Scale: ±20% premium → 0 or 100
        score = 50.0 + (reading.price_premium * 250.0)
        return float(np.clip(score, 0, 100))

    @staticmethod
    def classify_direction(score: float) -> SignalDirection:
        """Map 0-100 consensus score to SignalDirection."""
        if score >= SCORE_STRONG_BULL:
            return SignalDirection.STRONG_BULLISH
        if score >= SCORE_BULL:
            return SignalDirection.BULLISH
        if score >= SCORE_NEUTRAL_LOW:
            return SignalDirection.NEUTRAL
        if score >= SCORE_BEAR:
            return SignalDirection.BEARISH
        return SignalDirection.STRONG_BEARISH

    def compute(
        self,
        asset: str,
        momentum_readings: List[ProbabilityMomentumReading],
        dip_skew_reading: Optional[DipSkewReading],
        implied_curve_reading: Optional[ImpliedCurveReading],
    ) -> ConsensusScore:
        """Compute weighted consensus score from all signal components."""
        comp_mom = self.momentum_to_component(momentum_readings)
        comp_dip = self.dip_skew_to_component(dip_skew_reading)
        comp_imp = self.implied_curve_to_component(implied_curve_reading)

        score = (
            self.wt_momentum * comp_mom
            + self.wt_dip_skew * comp_dip
            + self.wt_implied * comp_imp
        )

        direction = self.classify_direction(score)

        sources = ["polymarket"]
        strongest_momentum = momentum_readings[0] if momentum_readings else None

        return ConsensusScore(
            asset=asset,
            score=score,
            direction=direction,
            momentum_component=comp_mom,
            dip_skew_component=comp_dip,
            implied_curve_component=comp_imp,
            momentum_detail=strongest_momentum,
            dip_skew_detail=dip_skew_reading,
            implied_curve_detail=implied_curve_reading,
            sources=sources,
        )

    def compute_batch(
        self,
        assets: List[str],
        extractor: SignalExtractor,
    ) -> Dict[str, ConsensusScore]:
        """Run full consensus pipeline for multiple assets."""
        # Fetch events once and reuse
        events = extractor.gamma.fetch_active_crypto_events(limit=100)

        results: Dict[str, ConsensusScore] = {}
        for asset in assets:
            logger.info("Computing consensus for %s ...", asset)
            momentum = extractor.probability_momentum(asset, events=events)
            dip_skew = extractor.dip_probability_skew(asset, events=events)
            implied_curve = extractor.implied_probability_curve(asset, events=events)

            score = self.compute(asset, momentum, dip_skew, implied_curve)
            results[asset] = score

        return results


# ===========================================================================
# SECTION 9: SIGNAL QUALITY TRACKER
# ===========================================================================


class SignalQualityTracker:
    """Monitors prediction market accuracy and calibration over time.

    When markets resolve, compares predicted probability to actual outcome.
    Logs to SQLite and computes calibration scores.
    """

    CALIBRATION_THRESHOLD = 0.10  # alert when |predicted - actual| > 10%

    def __init__(self, cache: Optional[PMCacheManager] = None) -> None:
        self.cache = cache or PMCacheManager()

    def record_resolution(
        self,
        market_id: str,
        source: str,
        predicted_prob: float,
        actual_outcome: int,
        asset: str = "",
        market_type: str = "",
        resolve_date: str = "",
        days_to_resolve: int = 0,
        signal_time: str = "",
    ) -> None:
        """Log a resolved market outcome for accuracy tracking."""
        resolved_correct = (
            (predicted_prob >= 0.5 and actual_outcome == 1)
            or (predicted_prob < 0.5 and actual_outcome == 0)
        )

        record = AccuracyRecord(
            market_id=market_id,
            source=source,
            market_type=market_type,
            asset=asset,
            predicted_prob=predicted_prob,
            actual_outcome=actual_outcome,
            resolved_correct=resolved_correct,
            resolve_date=resolve_date,
            days_to_resolve=days_to_resolve,
            signal_time=signal_time,
        )
        self.cache.log_accuracy(record)
        logger.info(
            "Accuracy recorded: %s | pred=%.3f actual=%d correct=%s",
            market_id, predicted_prob, actual_outcome, resolved_correct,
        )

    def get_accuracy_summary(
        self,
        asset: Optional[str] = None,
        source: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get accuracy summary statistics."""
        records = self.cache.get_accuracy_history(asset=asset, source=source, limit=5000)
        if not records:
            return {"total": 0, "accuracy_rate": None, "by_market_type": {}}

        df = pd.DataFrame([r.to_dict() for r in records])
        total = len(df)
        correct = int(df["resolved_correct"].sum())
        overall_rate = correct / total if total > 0 else 0.0

        by_type = df.groupby("market_type")["resolved_correct"].agg(
            ["sum", "count", "mean"]
        ).to_dict("index") if "market_type" in df.columns else {}

        return {
            "total": total,
            "correct": correct,
            "accuracy_rate": round(overall_rate, 4),
            "by_market_type": {
                k: {"correct": int(v["sum"]), "total": int(v["count"]),
                    "rate": round(v["mean"], 4)}
                for k, v in by_type.items()
            },
        }

    def calibration_score(self, asset: Optional[str] = None) -> Dict[str, Any]:
        """Compute calibration score: how well predicted probs match actual frequencies.

        Well-calibrated → actual frequency ≈ predicted probability in each bin.
        Returns Brier score and per-bin calibration data.
        """
        records = self.cache.get_accuracy_history(asset=asset, limit=5000)
        if not records:
            return {"brier_score": None, "bins": [], "is_calibrated": False}

        df = pd.DataFrame([r.to_dict() for r in records])

        # Brier score
        df["brier"] = (df["predicted_prob"] - df["actual_outcome"]) ** 2
        brier = float(df["brier"].mean())

        # Calibration bins
        bins_df = self.cache.calibration_by_bins(asset=asset, num_bins=10)
        bins_list = bins_df.to_dict("records") if not bins_df.empty else []

        # Check if calibrated (avg |predicted - actual| < threshold)
        is_calibrated = False
        if bins_list:
            avg_error = np.mean([
                abs(b["predicted_avg"] - b["actual_freq"])
                for b in bins_list
                if b["count"] and b["count"] > 0
            ])
            is_calibrated = avg_error < self.CALIBRATION_THRESHOLD

        return {
            "brier_score": round(brier, 4),
            "brier_skill": round(1.0 - (brier / 0.25), 4),  # vs random baseline
            "bins": bins_list,
            "is_calibrated": is_calibrated,
            "calibration_error": round(
                np.mean([
                    abs(b["predicted_avg"] - b["actual_freq"])
                    for b in bins_list
                    if b["count"] and b["count"] > 0
                ]) if bins_list else float("nan"), 4),
        }

    def check_calibration_alert(self, asset: Optional[str] = None) -> Optional[str]:
        """Return alert string if calibration is poor, else None."""
        cal = self.calibration_score(asset=asset)
        if cal["is_calibrated"] is False and cal["brier_score"] is not None:
            return (
                f"CALIBRATION ALERT: Prediction market signals for {asset or 'ALL'} "
                f"are poorly calibrated (Brier={cal['brier_score']:.3f}, "
                f"error={cal.get('calibration_error', 'N/A')}). "
                f"Consider reducing signal weights."
            )
        return None


# ===========================================================================
# SECTION 10: TRADING SIGNAL CONVERTER
# ===========================================================================


class TradingSignalConverter:
    """Convert prediction market ConsensusScore objects into trading signals
    compatible with alpha_engine/data/premium_signals.json.
    """

    DIRECTION_MAP: Dict[SignalDirection, str] = {
        SignalDirection.STRONG_BULLISH: "LONG",
        SignalDirection.BULLISH: "LONG",
        SignalDirection.NEUTRAL: "NEUTRAL",
        SignalDirection.BEARISH: "SHORT",
        SignalDirection.STRONG_BEARISH: "SHORT",
    }

    @staticmethod
    def consensus_to_trading_signal(
        consensus: ConsensusScore,
        kalshi_signals: Optional[List[Dict[str, Any]]] = None,
        calibration_score: Optional[float] = None,
    ) -> Optional[TradingSignal]:
        """Convert a ConsensusScore to a TradingSignal.

        Parameters
        ----------
        consensus : ConsensusScore
        kalshi_signals : list of dict, optional
            Kalshi signals for the same asset (for cross-validation).
        calibration_score : float, optional
            Calibration score (0-1) for confidence adjustment.

        Returns
        -------
        TradingSignal or None (if NEUTRAL and confidence too low)
        """
        # Skip pure neutral
        if consensus.direction == SignalDirection.NEUTRAL and consensus.score < 48:
            return None

        symbol = PM_TO_SYMBOL.get(consensus.asset.upper(),
                                  f"{consensus.asset.upper()}USDT")

        direction_str = TradingSignalConverter.DIRECTION_MAP.get(
            consensus.direction, "NEUTRAL"
        )

        # Base confidence from score: map 0-100 → 0-1
        base_confidence = consensus.score / 100.0
        if consensus.direction in (SignalDirection.BEARISH, SignalDirection.STRONG_BEARISH):
            base_confidence = 1.0 - base_confidence

        # Adjust by calibration
        if calibration_score is not None:
            base_confidence *= (0.5 + 0.5 * calibration_score)

        # Cross-validate with Kalshi if available
        kalshi_direction = None
        if kalshi_signals:
            bullish_count = sum(1 for s in kalshi_signals if s.get("direction") == "BULLISH")
            bearish_count = sum(1 for s in kalshi_signals if s.get("direction") == "BEARISH")
            total = len(kalshi_signals)
            if total > 0:
                kalshi_bull_pct = bullish_count / total
                kalshi_direction = "LONG" if kalshi_bull_pct > 0.6 else "SHORT" if kalshi_bull_pct < 0.4 else None
                # Penalize confidence if directions disagree
                if kalshi_direction and kalshi_direction != direction_str:
                    base_confidence *= 0.7

        confidence = float(np.clip(base_confidence, 0.05, 0.95))

        # Skip weak signals
        if confidence < 0.35:
            return None

        metadata: Dict[str, Any] = {
            "pm_source": "polymarket",
            "signal_type": consensus.direction.value.lower(),
            "pm_consensus_score": round(consensus.score, 2),
            "momentum_component": round(consensus.momentum_component, 4),
            "dip_skew_component": round(consensus.dip_skew_component, 4),
            "implied_curve_component": round(consensus.implied_curve_component, 4),
            "calibration_score": round(calibration_score, 4) if calibration_score else None,
        }

        # Add dip skew detail
        if consensus.dip_skew_detail:
            metadata["dip_skew"] = round(consensus.dip_skew_detail.skew_ratio, 4)
            metadata["num_dip_markets"] = consensus.dip_skew_detail.num_dip_markets
            metadata["num_reach_markets"] = consensus.dip_skew_detail.num_reach_markets

        # Add momentum detail
        if consensus.momentum_detail:
            metadata["momentum_4h"] = round(consensus.momentum_detail.pct_change, 4)
            metadata["strongest_momentum_market"] = consensus.momentum_detail.market_question

        # Add implied curve detail
        if consensus.implied_curve_detail:
            metadata["implied_premium"] = round(consensus.implied_curve_detail.price_premium, 4)
            metadata["spot_estimate"] = round(consensus.implied_curve_detail.spot_price, 2)

        # Add Kalshi cross-validation
        if kalshi_signals:
            metadata["kalshi_signals_count"] = len(kalshi_signals)
            metadata["kalshi_bullish_pct"] = round(
                sum(1 for s in kalshi_signals if s.get("direction") == "BULLISH")
                / len(kalshi_signals), 4
            ) if kalshi_signals else None
            metadata["kalshi_alignment"] = kalshi_direction

        return TradingSignal(
            symbol=symbol,
            direction=direction_str,
            confidence=round(confidence, 4),
            source_system="prediction_market",
            strategy="pm_consensus",
            asset_class="CRYPTO",
            metadata=metadata,
        )

    @classmethod
    def convert_batch(
        cls,
        consensus_scores: Dict[str, ConsensusScore],
        kalshi_data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        quality_tracker: Optional[SignalQualityTracker] = None,
    ) -> List[TradingSignal]:
        """Convert multiple consensus scores to trading signals."""
        signals: List[TradingSignal] = []
        for asset, consensus in consensus_scores.items():
            cal_score = None
            if quality_tracker:
                cal = quality_tracker.calibration_score(asset=asset)
                cal_score = cal.get("brier_skill")

            kalshi_for_asset = kalshi_data.get(asset.upper()) if kalshi_data else None
            sig = cls.consensus_to_trading_signal(
                consensus, kalshi_signals=kalshi_for_asset, calibration_score=cal_score
            )
            if sig:
                signals.append(sig)

        return signals


# ===========================================================================
# SECTION 11: FULL PIPELINE ORCHESTRATOR
# ===========================================================================


class PredictionMarketPipeline:
    """End-to-end pipeline: fetch → extract → score → output.

    Usage
    -----
    pipeline = PredictionMarketPipeline()
    signals = pipeline.run(assets=["btc", "eth", "sol"])
    pipeline.save_signals(signals)
    """

    def __init__(
        self,
        cache_dir: Optional[Union[str, Path]] = None,
        kalshi_api_key: Optional[str] = None,
        enable_kalshi: bool = True,
    ) -> None:
        cache_path = Path(cache_dir) if cache_dir else None
        self.cache = PMCacheManager(db_path=(cache_path / "pm_cache.db") if cache_path else None)
        self.gamma = PolymarketGammaClient(cache=self.cache)
        self.clob = PolymarketClobClient(cache=self.cache)
        self.extractor = SignalExtractor(gamma=self.gamma, clob=self.clob, cache=self.cache)
        self.scorer = ConsensusScorer()
        self.quality = SignalQualityTracker(cache=self.cache)
        self.converter = TradingSignalConverter()
        self.enable_kalshi = enable_kalshi
        self.kalshi = KalshiClient(api_key=kalshi_api_key, cache=self.cache) if enable_kalshi else None

        self.output_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        assets: List[str] = None,
        include_kalshi: bool = True,
    ) -> Dict[str, Any]:
        """Run full signal extraction pipeline.

        Parameters
        ----------
        assets : list of str
            Assets to process (default: btc, eth, sol).
        include_kalshi : bool
            Whether to include Kalshi data in consensus.

        Returns
        -------
        dict with keys: consensus_scores, trading_signals, kalshi_signals,
                        accuracy_summary, calibration, metadata.
        """
        assets = assets or ["btc", "eth", "sol"]
        logger.info("=== Prediction Market Pipeline Start ===")
        logger.info("Assets: %s | Kalshi: %s", assets, include_kalshi)

        # Step 1: Pre-fetch all events (shared across extractors)
        events = self.gamma.fetch_active_crypto_events(limit=100)

        # Step 2: Extract signals per asset
        consensus_scores: Dict[str, ConsensusScore] = {}
        all_momentum: Dict[str, List[ProbabilityMomentumReading]] = {}
        all_dip_skew: Dict[str, Optional[DipSkewReading]] = {}
        all_implied: Dict[str, Optional[ImpliedCurveReading]] = {}

        for asset in assets:
            logger.info("Extracting signals for %s ...", asset)
            all_momentum[asset] = self.extractor.probability_momentum(asset, events=events)
            all_dip_skew[asset] = self.extractor.dip_probability_skew(asset, events=events)
            all_implied[asset] = self.extractor.implied_probability_curve(asset, events=events)

            consensus = self.scorer.compute(
                asset, all_momentum[asset], all_dip_skew[asset], all_implied[asset]
            )
            consensus_scores[asset] = consensus

        # Step 3: Kalshi signals (optional)
        kalshi_data: Dict[str, List[Dict[str, Any]]] = {}
        if include_kalshi and self.kalshi:
            kalshi_raw = self.extractor.kalshi_crypto_signals(self.kalshi)
            # Map Kalshi tickers to asset names
            ticker_map = {"KXBTC": "btc", "KXETH": "eth", "KXSOL": "sol",
                          "KXDOGE": "doge", "KXXRP": "xrp", "KXAVAX": "avax",
                          "KXLINK": "link", "KXDOT": "dot", "KXLTC": "ltc"}
            for ticker, signals in kalshi_raw.items():
                asset_key = ticker_map.get(ticker, ticker.lower())
                kalshi_data[asset_key] = signals

        # Step 4: Convert to trading signals
        trading_signals = self.converter.convert_batch(
            consensus_scores,
            kalshi_data=kalshi_data if include_kalshi else None,
            quality_tracker=self.quality,
        )

        # Step 5: Quality metrics
        accuracy_summary = self.quality.get_accuracy_summary()
        calibration = self.quality.calibration_score()
        cal_alert = self.quality.check_calibration_alert()

        # Step 6: Assemble results
        results = {
            "metadata": {
                "run_time": datetime.utcnow().strftime(DT_FMT),
                "assets": assets,
                "num_events_fetched": len(events),
                "kalshi_enabled": include_kalshi and self.kalshi is not None,
            },
            "consensus_scores": {
                a: c.to_dict() for a, c in consensus_scores.items()
            },
            "trading_signals": [s.to_dict() for s in trading_signals],
            "kalshi_signals": {
                a: s[:5] for a, s in kalshi_data.items()  # top 5 per asset
            } if kalshi_data else {},
            "accuracy_summary": accuracy_summary,
            "calibration": calibration,
            "alerts": [cal_alert] if cal_alert else [],
        }

        logger.info(
            "=== Pipeline Complete === signals=%d assets=%d",
            len(trading_signals), len(assets),
        )
        return results

    def run_momentum_only(
        self,
        assets: List[str] = None,
    ) -> Dict[str, Any]:
        """Fast momentum-only run (for hourly GHA schedule).

        Only computes probability momentum — skips implied curve and dip skew.
        """
        assets = assets or ["btc", "eth", "sol"]
        logger.info("=== Momentum-Only Pipeline ===")

        events = self.gamma.fetch_active_crypto_events(limit=100)
        signals: List[TradingSignal] = []

        for asset in assets:
            momentum = self.extractor.probability_momentum(asset, events=events)
            if not momentum:
                continue

            # Simple momentum-only score
            top = sorted(momentum, key=lambda r: abs(r.pct_change), reverse=True)[:3]
            avg_change = np.mean([r.pct_change for r in top])
            score = 50.0 + (avg_change * 250.0)
            score = float(np.clip(score, 0, 100))

            direction = ConsensusScorer.classify_direction(score)
            if direction == SignalDirection.NEUTRAL:
                continue

            symbol = PM_TO_SYMBOL.get(asset.upper(), f"{asset.upper()}USDT")
            direction_str = "LONG" if direction in (
                SignalDirection.BULLISH, SignalDirection.STRONG_BULLISH
            ) else "SHORT"
            confidence = score / 100.0 if direction_str == "LONG" else 1.0 - (score / 100.0)
            confidence = float(np.clip(confidence, 0.35, 0.95))

            sig = TradingSignal(
                symbol=symbol,
                direction=direction_str,
                confidence=round(confidence, 4),
                source_system="prediction_market",
                strategy="pm_probability_momentum",
                asset_class="CRYPTO",
                metadata={
                    "pm_source": "polymarket",
                    "signal_type": "probability_momentum",
                    "momentum_4h": round(avg_change, 4),
                    "pm_consensus_score": round(score, 2),
                    "top_market": top[0].market_question if top else None,
                },
            )
            signals.append(sig)

        results = {
            "metadata": {
                "run_time": datetime.utcnow().strftime(DT_FMT),
                "mode": "momentum_only",
                "assets": assets,
            },
            "trading_signals": [s.to_dict() for s in signals],
        }
        logger.info("Momentum-only: %d signals generated", len(signals))
        return results

    def save_signals(
        self,
        results: Dict[str, Any],
        filepath: Optional[Path] = None,
    ) -> Path:
        """Save pipeline results to JSON file."""
        filepath = filepath or (self.output_dir / "pm_signals.json")
        with open(filepath, "w") as f:
            json.dump(results, f, indent=2, default=str)
        logger.info("Signals saved to %s", filepath)
        return filepath

    def save_to_premium_format(
        self,
        trading_signals: List[TradingSignal],
        filepath: Optional[Path] = None,
    ) -> Path:
        """Append trading signals to premium_signals.json format."""
        filepath = filepath or (self.output_dir / "premium_signals.json")

        # Read existing if present
        existing: List[Dict[str, Any]] = []
        if filepath.exists():
            try:
                with open(filepath) as f:
                    existing = json.load(f)
                if isinstance(existing, dict) and "signals" in existing:
                    existing = existing["signals"]
            except (json.JSONDecodeError, KeyError):
                existing = []

        # Append new signals
        new_entries = [s.to_dict() for s in trading_signals]
        combined = existing + new_entries

        with open(filepath, "w") as f:
            json.dump(combined, f, indent=2, default=str)

        logger.info("Premium signals: appended %d entries (total %d)",
                    len(new_entries), len(combined))
        return filepath


# ===========================================================================
# SECTION 12: CLI / GHA ENTRY POINTS
# ===========================================================================


def run_full_pipeline(
    assets: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
    kalshi_key: Optional[str] = None,
) -> Dict[str, Any]:
    """CLI entry point for full daily pipeline.

    Example GHA cron (daily):
      - cron: "0 6 * * *"
    """
    out = Path(output_dir) if output_dir else DEFAULT_CACHE_DIR
    pipeline = PredictionMarketPipeline(
        cache_dir=out,
        kalshi_api_key=kalshi_key,
        enable_kalshi=True,
    )
    results = pipeline.run(assets=assets)
    pipeline.save_signals(results, out / "pm_signals.json")
    if results.get("trading_signals"):
        pipeline.save_to_premium_format(
            [TradingSignal(**s) for s in results["trading_signals"]],
            out / "premium_signals.json",
        )
    return results


def run_momentum_pipeline(
    assets: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """CLI entry point for hourly momentum-only pipeline.

    Example GHA cron (hourly):
      - cron: "0 * * * *
    """
    out = Path(output_dir) if output_dir else DEFAULT_CACHE_DIR
    pipeline = PredictionMarketPipeline(cache_dir=out, enable_kalshi=False)
    results = pipeline.run_momentum_only(assets=assets)
    pipeline.save_signals(results, out / "pm_momentum_signals.json")
    if results.get("trading_signals"):
        pipeline.save_to_premium_format(
            [TradingSignal(**s) for s in results["trading_signals"]],
            out / "premium_signals.json",
        )
    return results


def main() -> None:
    """Command-line entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Prediction Market Signal Engine")
    parser.add_argument("mode", choices=["full", "momentum"], default="full",
                        help="Pipeline mode: full (daily) or momentum (hourly)")
    parser.add_argument("--assets", default="btc,eth,sol",
                        help="Comma-separated asset list")
    parser.add_argument("--output", default=None,
                        help="Output directory (default: alpha_engine/data)")
    parser.add_argument("--kalshi-key", default=None,
                        help="Kalshi API key (optional)")
    args = parser.parse_args()

    asset_list = [a.strip().lower() for a in args.assets.split(",")]
    if args.mode == "full":
        results = run_full_pipeline(
            assets=asset_list,
            output_dir=args.output,
            kalshi_key=args.kalshi_key,
        )
    else:
        results = run_momentum_pipeline(
            assets=asset_list,
            output_dir=args.output,
        )

    # Print summary
    signals = results.get("trading_signals", [])
    print(f"\n{'='*60}")
    print(f" Prediction Market Signal Engine — {results['metadata']['run_time']}")
    print(f" Mode: {results['metadata'].get('mode', 'full')}")
    print(f" Assets: {results['metadata']['assets']}")
    print(f" Signals Generated: {len(signals)}")
    print(f" {'='*60}")
    for s in signals:
        print(f"  {s['symbol']:12s} | {s['direction']:6s} | "
              f"confidence={s['confidence']:.2f} | {s['strategy']}")
    print(f" {'='*60}\n")


if __name__ == "__main__":
    main()
