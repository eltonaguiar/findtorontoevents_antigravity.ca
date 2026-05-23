# Coinglass DNA Bundle — Implementation Plan

> **Strategy Registry:** See [ALL_STRATEGIES.md](../ALL_STRATEGIES.md) for the full crypto strategy inventory across all systems.

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an 8-strategy trading system using Coinglass/Binance long-short ratio data with paper portfolio, Discord alerts to #paper-trade, and cross-aggregation integration.

**Architecture:** Multi-source data fetcher (Binance → Coinglass → OKX) stores 4 ratio types per symbol in SQLite. 8 strategy modules consume historical ratios and emit picks. A paper portfolio tracks $10K virtual equity. GitHub Actions runs every 15 min.

**Tech Stack:** Python 3.11, requests, sqlite3, Discord webhooks, GitHub Actions

---

## Task 1: Package Init & Config

**Files:**
- Create: `coinglass_strategies/__init__.py`
- Create: `coinglass_strategies/config.py`

**Step 1: Create `__init__.py`**

```python
"""Coinglass DNA Bundle — 8-strategy long/short ratio trading system."""
```

**Step 2: Create `config.py`**

```python
"""Centralized configuration for the Coinglass DNA Bundle."""
from pathlib import Path

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = str(DATA_DIR / "coinglass.db")

# Symbols to track (Binance USDT perpetual format)
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT"]

# Map for CoinGecko price lookups
SYMBOL_TO_COINGECKO = {
    "BTCUSDT": "bitcoin",
    "ETHUSDT": "ethereum",
    "SOLUSDT": "solana",
    "BNBUSDT": "binancecoin",
    "DOGEUSDT": "dogecoin",
}

# Data fetcher
FETCH_TIMEOUT = 10
RETRY_MAX = 3
RETRY_BASE_DELAY = 1.0
MIN_INTERVAL_BETWEEN_CALLS = 1.0  # seconds per source

# Strategy thresholds
EXTREME_REVERSION_Z_THRESHOLD = 2.0
WHALE_DIVERGENCE_MIN_DIFF = 0.15
MOMENTUM_SMA_WINDOW = 3
MOMENTUM_CONSECUTIVE_MIN = 3
CROSS_EXCHANGE_SPREAD_MIN = 0.20
FUNDING_RATIO_THRESHOLD = 1.15
SENTIMENT_LONG_THRESHOLD = 0.70
SENTIMENT_SHORT_THRESHOLD = 0.30
SPIKE_THRESHOLD_PCT = 30.0

# Paper portfolio
STARTING_CAPITAL = 10_000.0
RISK_PER_TRADE_PCT = 2.0
MAX_CONCURRENT_POSITIONS = 5
TP_ATR_MULT = 1.5
SL_ATR_MULT = 1.0
MAX_HOLD_HOURS = 48

# Discord
DISCORD_WEBHOOK_PAPERTRADE = ""  # Set via env var at runtime
PORTFOLIO_SUMMARY_INTERVAL_HOURS = 2

# Rolling windows (minutes)
ZSCORE_WINDOW_MINUTES = 1440     # 24 hours
MOMENTUM_WINDOW_MINUTES = 60     # 1 hour
SENTIMENT_NORM_WINDOW_DAYS = 30
```

**Step 3: Commit**

```bash
git add coinglass_strategies/__init__.py coinglass_strategies/config.py
git commit -m "feat(coinglass): add package init and centralized config"
```

---

## Task 2: Rewrite Data Fetcher with All 4 Binance Ratio Endpoints

**Files:**
- Modify: `coinglass_strategies/data_fetcher.py` (full rewrite)

The existing fetcher only gets the global ratio and uses the wrong Binance endpoint (openInterest doesn't return L/S ratios). Binance provides 4 free dedicated endpoints:

- `GET /futures/data/globalLongShortAccountRatio` → global account L/S
- `GET /futures/data/topLongShortAccountRatio` → top trader account L/S
- `GET /futures/data/topLongShortPositionRatio` → top trader position L/S
- `GET /futures/data/takerlongshortRatio` → taker buy/sell ratio

**Step 1: Rewrite `data_fetcher.py`**

```python
"""Multi-source ratio fetcher: Binance (primary) → Coinglass → OKX.

Fetches all 4 long/short ratio types for each symbol with failover
and per-source rate limiting.
"""
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

BINANCE_FUTURES = "https://fapi.binance.com"
COINGLASS_API = "https://open-api.coinglass.com"
OKX_API = "https://www.okx.com"

# Per-source rate limit tracking
_last_call: Dict[str, float] = {}
_MIN_INTERVAL = 1.0  # seconds between calls to same source


def _rate_limit(source: str):
    """Enforce minimum interval between calls to the same source."""
    now = time.time()
    last = _last_call.get(source, 0)
    wait = _MIN_INTERVAL - (now - last)
    if wait > 0:
        time.sleep(wait)
    _last_call[source] = time.time()


def _http_get(url: str, params: dict = None, timeout: int = 10,
              headers: dict = None) -> Optional[dict]:
    """GET with single retry on failure."""
    for attempt in range(2):
        try:
            resp = requests.get(url, params=params, timeout=timeout,
                                headers=headers or {})
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            if attempt == 0:
                time.sleep(2)
            else:
                logger.warning("GET %s failed: %s", url, exc)
    return None


# ── Binance (primary) ─────────────────────────────────────────────
def _binance_ratio(endpoint: str, symbol: str,
                   period: str = "15m") -> Optional[float]:
    """Fetch a single ratio type from Binance Futures data endpoints."""
    _rate_limit("binance")
    url = f"{BINANCE_FUTURES}/futures/data/{endpoint}"
    data = _http_get(url, params={"symbol": symbol, "period": period, "limit": 1})
    if data and isinstance(data, list) and len(data) > 0:
        row = data[0]
        # Global/top endpoints return longShortRatio
        # Taker endpoint returns buyVol/sellVol
        if "longShortRatio" in row:
            return float(row["longShortRatio"])
        elif "buySellRatio" in row:
            return float(row["buySellRatio"])
    return None


def fetch_binance(symbol: str) -> Dict[str, Optional[float]]:
    """Fetch all 4 ratio types from Binance Futures."""
    return {
        "global": _binance_ratio("globalLongShortAccountRatio", symbol),
        "top_trader_account": _binance_ratio("topLongShortAccountRatio", symbol),
        "top_trader_position": _binance_ratio("topLongShortPositionRatio", symbol),
        "taker": _binance_ratio("takerlongshortRatio", symbol),
    }


# ── Coinglass (fallback 1) ────────────────────────────────────────
def fetch_coinglass(symbol: str) -> Dict[str, Optional[float]]:
    """Fetch from Coinglass public v2 endpoint."""
    _rate_limit("coinglass")
    base_sym = symbol.replace("USDT", "")
    url = f"{COINGLASS_API}/public/v2/long_short"
    data = _http_get(url, params={"symbol": base_sym, "timeType": 2})
    result = {"global": None, "top_trader_account": None,
              "top_trader_position": None, "taker": None}
    if not data or not isinstance(data, dict):
        return result
    items = data.get("data", [])
    if isinstance(items, list):
        for item in items:
            if item.get("symbol", "").upper() == base_sym.upper():
                result["global"] = _safe_float(item.get("longRate"))
                break
    elif isinstance(items, dict):
        result["global"] = _safe_float(items.get("longRate"))
    return result


# ── OKX (fallback 2) ──────────────────────────────────────────────
def fetch_okx(symbol: str) -> Dict[str, Optional[float]]:
    """Fetch from OKX Rubik long/short ratio endpoint."""
    _rate_limit("okx")
    # OKX uses BTC-USDT format
    okx_sym = symbol[:-4] + "-USDT" if symbol.endswith("USDT") else symbol
    url = f"{OKX_API}/api/v5/rubik/stat/contracts-long-short-account-ratio"
    data = _http_get(url, params={"instId": okx_sym, "period": "5m"})
    result = {"global": None, "top_trader_account": None,
              "top_trader_position": None, "taker": None}
    if data and data.get("data"):
        latest = data["data"][0]  # [ts, long_ratio, short_ratio]
        if len(latest) >= 2:
            result["global"] = _safe_float(latest[1])
    return result


def _safe_float(val) -> Optional[float]:
    try:
        return float(val) if val is not None else None
    except (ValueError, TypeError):
        return None


# ── Main entry point ──────────────────────────────────────────────
def fetch_all_ratios(symbol: str) -> Dict[str, Optional[float]]:
    """Fetch all 4 ratio types with 3-source failover.

    Returns dict with keys: global, top_trader_account,
    top_trader_position, taker, source, fetched_at.
    """
    # Try Binance first (has all 4 ratio types)
    ratios = fetch_binance(symbol)
    if ratios.get("global") is not None:
        ratios["source"] = "binance"
        ratios["fetched_at"] = datetime.now(timezone.utc).isoformat()
        return ratios

    # Fallback to Coinglass (may only have global)
    ratios = fetch_coinglass(symbol)
    if ratios.get("global") is not None:
        ratios["source"] = "coinglass"
        ratios["fetched_at"] = datetime.now(timezone.utc).isoformat()
        return ratios

    # Fallback to OKX
    ratios = fetch_okx(symbol)
    if ratios.get("global") is not None:
        ratios["source"] = "okx"
        ratios["fetched_at"] = datetime.now(timezone.utc).isoformat()
        return ratios

    logger.error("All sources failed for %s", symbol)
    return {"global": None, "top_trader_account": None,
            "top_trader_position": None, "taker": None,
            "source": None, "fetched_at": None}


def fetch_funding_rate(symbol: str) -> Optional[float]:
    """Fetch current funding rate from Binance for Strategy S6."""
    _rate_limit("binance")
    url = f"{BINANCE_FUTURES}/fapi/v1/fundingRate"
    data = _http_get(url, params={"symbol": symbol, "limit": 1})
    if data and isinstance(data, list) and len(data) > 0:
        return _safe_float(data[0].get("fundingRate"))
    return None


def fetch_current_price(symbol: str) -> Optional[float]:
    """Fetch latest price from Binance for TP/SL tracking."""
    url = "https://api.binance.com/api/v3/ticker/price"
    data = _http_get(url, params={"symbol": symbol})
    if data:
        return _safe_float(data.get("price"))
    return None


def fetch_atr(symbol: str, period: int = 14) -> Optional[float]:
    """Compute ATR from recent Binance klines for position sizing."""
    url = f"{BINANCE_FUTURES}/fapi/v1/klines"
    data = _http_get(url, params={"symbol": symbol, "interval": "1h",
                                  "limit": period + 1})
    if not data or len(data) < period + 1:
        return None
    trs = []
    for i in range(1, len(data)):
        high = float(data[i][2])
        low = float(data[i][3])
        prev_close = float(data[i - 1][4])
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    return sum(trs) / len(trs) if trs else None
```

**Step 2: Verify the Binance endpoints work**

Run: `cd /e/findtorontoevents_antigravity.ca && py -c "from coinglass_strategies.data_fetcher import fetch_all_ratios; print(fetch_all_ratios('BTCUSDT'))"`

Expected: Dict with all 4 ratios populated from Binance source.

**Step 3: Commit**

```bash
git add coinglass_strategies/data_fetcher.py
git commit -m "feat(coinglass): rewrite data fetcher with all 4 Binance ratio endpoints + failover"
```

---

## Task 3: Upgrade Ratio Store with Portfolio & Signal Tables

**Files:**
- Modify: `coinglass_strategies/ratio_store.py` (extend with new tables)

**Step 1: Rewrite `ratio_store.py` with additional tables**

```python
"""SQLite persistence: ratios, signals, paper portfolio, snapshots."""
import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from . import config

logger = logging.getLogger(__name__)


def _connect():
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create all tables."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS ratios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                symbol TEXT NOT NULL,
                source TEXT NOT NULL,
                global_ratio REAL,
                top_trader_account_ratio REAL,
                top_trader_position_ratio REAL,
                taker_ratio REAL,
                funding_rate REAL,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(ts, symbol)
            );

            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id TEXT UNIQUE,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                strategy TEXT NOT NULL,
                confidence REAL,
                entry_price REAL,
                take_profit REAL,
                stop_loss REAL,
                ratios_snapshot TEXT,
                reason TEXT,
                generated_at TEXT NOT NULL,
                status TEXT DEFAULT 'ACTIVE'
            );

            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id TEXT UNIQUE,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                take_profit REAL NOT NULL,
                stop_loss REAL NOT NULL,
                quantity REAL NOT NULL,
                risk_amount REAL NOT NULL,
                opened_at TEXT NOT NULL,
                closed_at TEXT,
                exit_price REAL,
                exit_reason TEXT,
                pnl_dollar REAL,
                pnl_pct REAL,
                status TEXT DEFAULT 'OPEN'
            );

            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                equity REAL NOT NULL,
                open_positions INTEGER,
                total_trades INTEGER,
                wins INTEGER,
                losses INTEGER,
                win_rate REAL,
                total_pnl REAL,
                max_drawdown REAL
            );

            CREATE INDEX IF NOT EXISTS idx_ratios_symbol_ts
                ON ratios(symbol, ts);
            CREATE INDEX IF NOT EXISTS idx_positions_status
                ON positions(status);
        """)
    logger.info("Initialized coinglass DB at %s", config.DB_PATH)


def store_ratios(symbol: str, data: Dict, funding_rate: float = None):
    """Store fetched ratio data."""
    ts = data.get("fetched_at") or datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO ratios
            (ts, symbol, source, global_ratio, top_trader_account_ratio,
             top_trader_position_ratio, taker_ratio, funding_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (ts, symbol, data.get("source", "unknown"),
              data.get("global"), data.get("top_trader_account"),
              data.get("top_trader_position"), data.get("taker"),
              funding_rate))


def get_recent_ratios(symbol: str, window_minutes: int = 1440) -> List[Dict]:
    """Return ratio rows within window, ordered ascending."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            "SELECT * FROM ratios WHERE symbol = ? AND ts >= ? ORDER BY ts ASC",
            (symbol, cutoff))
        return [dict(row) for row in cur.fetchall()]


def store_signal(signal: Dict):
    """Persist a generated signal."""
    with _connect() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO signals
            (signal_id, symbol, direction, strategy, confidence,
             entry_price, take_profit, stop_loss, ratios_snapshot,
             reason, generated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (signal["signal_id"], signal["symbol"], signal["direction"],
              signal["strategy"], signal["confidence"],
              signal.get("entry_price"), signal.get("take_profit"),
              signal.get("stop_loss"),
              json.dumps(signal.get("ratios", {})),
              signal.get("reason", ""),
              signal.get("generated_at")))


def open_position(signal: Dict, quantity: float, risk_amount: float):
    """Open a paper trading position."""
    with _connect() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO positions
            (signal_id, symbol, direction, entry_price, take_profit,
             stop_loss, quantity, risk_amount, opened_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (signal["signal_id"], signal["symbol"], signal["direction"],
              signal["entry_price"], signal["take_profit"],
              signal["stop_loss"], quantity, risk_amount,
              signal["generated_at"]))


def close_position(signal_id: str, exit_price: float, exit_reason: str):
    """Close a paper position with P&L calculation."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM positions WHERE signal_id = ? AND status = 'OPEN'",
            (signal_id,)).fetchone()
        if not row:
            return
        entry = row["entry_price"]
        direction = row["direction"]
        qty = row["quantity"]
        if direction == "LONG":
            pnl_pct = (exit_price - entry) / entry * 100
        else:
            pnl_pct = (entry - exit_price) / entry * 100
        pnl_dollar = qty * (pnl_pct / 100)
        conn.execute("""
            UPDATE positions SET status='CLOSED', closed_at=?,
            exit_price=?, exit_reason=?, pnl_pct=?, pnl_dollar=?
            WHERE signal_id=? AND status='OPEN'
        """, (datetime.now(timezone.utc).isoformat(), exit_price,
              exit_reason, round(pnl_pct, 4), round(pnl_dollar, 2),
              signal_id))


def get_open_positions() -> List[Dict]:
    """Return all open positions."""
    with _connect() as conn:
        cur = conn.execute("SELECT * FROM positions WHERE status = 'OPEN'")
        return [dict(row) for row in cur.fetchall()]


def get_closed_positions(limit: int = 100) -> List[Dict]:
    """Return recent closed positions."""
    with _connect() as conn:
        cur = conn.execute(
            "SELECT * FROM positions WHERE status='CLOSED' ORDER BY closed_at DESC LIMIT ?",
            (limit,))
        return [dict(row) for row in cur.fetchall()]


def get_portfolio_equity() -> float:
    """Compute current equity = starting capital + sum of closed P&L."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(pnl_dollar), 0) as total FROM positions WHERE status='CLOSED'"
        ).fetchone()
        return config.STARTING_CAPITAL + (row["total"] if row else 0)


def save_snapshot():
    """Save a portfolio snapshot for the equity curve."""
    closed = get_closed_positions(limit=9999)
    wins = sum(1 for p in closed if (p.get("pnl_pct") or 0) > 0)
    losses = sum(1 for p in closed if (p.get("pnl_pct") or 0) <= 0)
    total = wins + losses
    equity = get_portfolio_equity()
    open_pos = len(get_open_positions())
    total_pnl = sum(p.get("pnl_dollar", 0) for p in closed)
    with _connect() as conn:
        conn.execute("""
            INSERT INTO portfolio_snapshots
            (ts, equity, open_positions, total_trades, wins, losses,
             win_rate, total_pnl, max_drawdown)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (datetime.now(timezone.utc).isoformat(), equity, open_pos,
              total, wins, losses,
              round(wins / total * 100, 2) if total else 0,
              round(total_pnl, 2), 0))


def prune_old(days: int = 60):
    """Delete ratio rows older than N days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with _connect() as conn:
        conn.execute("DELETE FROM ratios WHERE ts < ?", (cutoff,))
```

**Step 2: Commit**

```bash
git add coinglass_strategies/ratio_store.py
git commit -m "feat(coinglass): upgrade ratio store with signals, positions, and portfolio tables"
```

---

## Task 4: Create Strategy Base & Signal Registry

**Files:**
- Create: `coinglass_strategies/strategies/__init__.py`
- Create: `coinglass_strategies/strategies/base.py`

**Step 1: Create strategies package**

`coinglass_strategies/strategies/__init__.py`:
```python
"""Coinglass DNA Bundle — 8 trading strategies."""
```

**Step 2: Create base strategy class and Signal dataclass**

`coinglass_strategies/strategies/base.py`:
```python
"""Base strategy interface and Signal container."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class Signal:
    """A trading signal emitted by a strategy."""
    symbol: str
    direction: str          # "LONG" or "SHORT"
    strategy: str           # strategy function name
    confidence: float       # 0.0 to 1.0
    reason: str
    ratios: Dict = field(default_factory=dict)
    entry_price: float = 0.0
    take_profit: float = 0.0
    stop_loss: float = 0.0
    signal_id: str = ""
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()
        if not self.signal_id:
            self.signal_id = f"{self.strategy}::{self.symbol}::{self.generated_at[:19]}"

    def to_dict(self) -> Dict:
        return {
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "strategy": self.strategy,
            "confidence": self.confidence,
            "reason": self.reason,
            "ratios": self.ratios,
            "entry_price": self.entry_price,
            "take_profit": self.take_profit,
            "stop_loss": self.stop_loss,
            "generated_at": self.generated_at,
            "source": "coinglass_strategies",
        }
```

**Step 3: Commit**

```bash
git add coinglass_strategies/strategies/
git commit -m "feat(coinglass): add strategy base class and Signal dataclass"
```

---

## Task 5: Implement Strategies S1-S4

**Files:**
- Create: `coinglass_strategies/strategies/extreme_reversion.py`
- Create: `coinglass_strategies/strategies/top_trader_divergence.py`
- Create: `coinglass_strategies/strategies/ratio_momentum.py`
- Create: `coinglass_strategies/strategies/cross_exchange_spread.py`

**Step 1: S1 — Extreme Ratio Reversion**

`coinglass_strategies/strategies/extreme_reversion.py`:
```python
"""S1: Extreme Ratio Reversion — contrarian Z-score spike reversal.

When the Taker L/S ratio's Z-score exceeds ±2 vs its 24h rolling window,
expect mean reversion. Too many longs → SHORT, too many shorts → LONG.
"""
import math
from typing import Dict, List, Optional

from .base import Signal
from .. import config


def run(symbol: str, recent_rows: List[Dict],
        current_ratios: Dict) -> Optional[Signal]:
    """Check for extreme Z-score in taker ratio."""
    # Use taker ratio; fall back to global if taker unavailable
    values = []
    for row in recent_rows:
        val = row.get("taker_ratio") or row.get("global_ratio")
        if val is not None:
            values.append(float(val))

    if len(values) < 10:
        return None  # Need sufficient history

    current = current_ratios.get("taker") or current_ratios.get("global")
    if current is None:
        return None

    # Compute Z-score
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std = math.sqrt(variance) if variance > 0 else 0
    if std == 0:
        return None

    z_score = (current - mean) / std
    threshold = config.EXTREME_REVERSION_Z_THRESHOLD

    if abs(z_score) < threshold:
        return None

    # Contrarian: high Z (too many longs) → SHORT
    direction = "SHORT" if z_score > 0 else "LONG"
    conf = 0.55 + 0.05 * min(abs(z_score) - threshold, 4.0)
    conf = round(min(conf, 0.75), 3)

    return Signal(
        symbol=symbol,
        direction=direction,
        strategy="coinglass_extreme_reversion",
        confidence=conf,
        reason=f"Taker ratio Z-score={z_score:.2f} (mean={mean:.3f}, std={std:.3f})",
        ratios=current_ratios,
    )
```

**Step 2: S2 — Top-Trader Divergence**

`coinglass_strategies/strategies/top_trader_divergence.py`:
```python
"""S2: Top-Trader Divergence — whale lead signal.

When top-trader ratio diverges from global ratio (opposite sides of 1.0),
follow the whales.
"""
from typing import Dict, List, Optional

from .base import Signal
from .. import config


def run(symbol: str, recent_rows: List[Dict],
        current_ratios: Dict) -> Optional[Signal]:
    """Check for divergence between top-trader and global ratios."""
    top = current_ratios.get("top_trader_account")
    glob = current_ratios.get("global")

    if top is None or glob is None:
        return None

    # Check if they're on opposite sides of 1.0
    top_side = 1 if top > 1 else -1
    glob_side = 1 if glob > 1 else -1
    diff = abs(top - glob)

    if top_side == glob_side or diff < config.WHALE_DIVERGENCE_MIN_DIFF:
        return None

    # Follow top traders
    direction = "LONG" if top > 1 else "SHORT"
    conf = 0.60 + 0.10 * min(diff / 0.3, 2.0)
    conf = round(min(conf, 0.80), 3)

    return Signal(
        symbol=symbol,
        direction=direction,
        strategy="coinglass_whale_divergence",
        confidence=conf,
        reason=f"Top-trader={top:.3f} vs Global={glob:.3f} (diff={diff:.3f}), following whales",
        ratios=current_ratios,
    )
```

**Step 3: S3 — Ratio Momentum**

`coinglass_strategies/strategies/ratio_momentum.py`:
```python
"""S3: Ratio Momentum — SMA-3 flow momentum.

Track the first derivative of the ratio. If SMA-3 of delta is positive
for 3+ consecutive windows, signal bullish flow (and vice versa).
"""
from typing import Dict, List, Optional

from .base import Signal
from .. import config


def run(symbol: str, recent_rows: List[Dict],
        current_ratios: Dict) -> Optional[Signal]:
    """Check for sustained ratio momentum."""
    values = []
    for row in recent_rows:
        val = row.get("global_ratio")
        if val is not None:
            values.append(float(val))

    sma_window = config.MOMENTUM_SMA_WINDOW
    min_consecutive = config.MOMENTUM_CONSECUTIVE_MIN

    if len(values) < sma_window + min_consecutive + 1:
        return None

    # Compute deltas
    deltas = [values[i] - values[i - 1] for i in range(1, len(values))]

    # Compute SMA of deltas
    sma_values = []
    for i in range(sma_window - 1, len(deltas)):
        window = deltas[i - sma_window + 1:i + 1]
        sma_values.append(sum(window) / len(window))

    if len(sma_values) < min_consecutive:
        return None

    # Check consecutive positive or negative
    recent_smas = sma_values[-min_consecutive:]
    all_positive = all(s > 0 for s in recent_smas)
    all_negative = all(s < 0 for s in recent_smas)

    if not all_positive and not all_negative:
        return None

    direction = "LONG" if all_positive else "SHORT"
    consecutive = len(recent_smas)
    conf = 0.50 + 0.05 * min(consecutive, 3)
    conf = round(min(conf, 0.65), 3)

    avg_sma = sum(recent_smas) / len(recent_smas)
    return Signal(
        symbol=symbol,
        direction=direction,
        strategy="coinglass_ratio_momentum",
        confidence=conf,
        reason=f"Ratio SMA-3 {'positive' if all_positive else 'negative'} for {consecutive} periods (avg delta={avg_sma:.4f})",
        ratios=current_ratios,
    )
```

**Step 4: S4 — Cross-Exchange Spread**

`coinglass_strategies/strategies/cross_exchange_spread.py`:
```python
"""S4: Cross-Exchange Spread — divergence between exchanges.

Compares the same ratio across Binance and OKX. A large spread
signals arbitrage pressure or exchange-specific sentiment.
"""
from typing import Dict, Optional

from .base import Signal
from .. import config
from ..data_fetcher import fetch_binance, fetch_okx


def run(symbol: str, **kwargs) -> Optional[Signal]:
    """Check for cross-exchange spread in global ratio."""
    binance_ratios = fetch_binance(symbol)
    okx_ratios = fetch_okx(symbol)

    b_global = binance_ratios.get("global")
    o_global = okx_ratios.get("global")

    if b_global is None or o_global is None:
        return None

    spread = b_global - o_global
    if abs(spread) < config.CROSS_EXCHANGE_SPREAD_MIN:
        return None

    # Follow Binance (typically higher OI / more institutional)
    direction = "LONG" if b_global > 1 else "SHORT"
    conf = 0.50 + 0.05 * min(abs(spread) / 0.2, 2.0)
    conf = round(min(conf, 0.60), 3)

    return Signal(
        symbol=symbol,
        direction=direction,
        strategy="coinglass_exchange_spread",
        confidence=conf,
        reason=f"Binance={b_global:.3f} vs OKX={o_global:.3f} (spread={spread:.3f})",
        ratios={"binance": binance_ratios, "okx": okx_ratios},
    )
```

**Step 5: Commit**

```bash
git add coinglass_strategies/strategies/
git commit -m "feat(coinglass): implement strategies S1-S4 (reversion, whale divergence, momentum, cross-exchange)"
```

---

## Task 6: Implement Strategies S5-S8

**Files:**
- Create: `coinglass_strategies/strategies/leverage_adjusted.py`
- Create: `coinglass_strategies/strategies/funding_confirmation.py`
- Create: `coinglass_strategies/strategies/sentiment_index.py`
- Create: `coinglass_strategies/strategies/spike_detection.py`

**Step 1: S5 — Leverage-Adjusted Ratio**

`coinglass_strategies/strategies/leverage_adjusted.py`:
```python
"""S5: Leverage-Adjusted Ratio — squeeze risk detection.

Uses funding rate as a leverage proxy. When the dominant side is also
paying high funding, a squeeze/liquidation cascade is likely.
"""
from typing import Dict, List, Optional

from .base import Signal
from .. import config


def run(symbol: str, recent_rows: List[Dict],
        current_ratios: Dict) -> Optional[Signal]:
    """Detect over-leveraged positioning via ratio × funding sign."""
    glob = current_ratios.get("global")
    if glob is None:
        return None

    # Get funding rate from most recent row that has it
    funding = None
    for row in reversed(recent_rows):
        if row.get("funding_rate") is not None:
            funding = float(row["funding_rate"])
            break

    if funding is None:
        return None

    # Leverage proxy: ratio deviation from 1.0 amplified by funding direction
    deviation = glob - 1.0
    leverage_signal = deviation * (1 if funding > 0 else -1)

    # High leverage_signal means longs dominate AND are paying funding
    # → squeeze risk for longs → go SHORT (contrarian)
    if abs(leverage_signal) < 0.10:
        return None

    direction = "SHORT" if leverage_signal > 0 else "LONG"
    severity = min(abs(leverage_signal) / 0.15, 3.0)
    conf = 0.55 + 0.05 * severity
    conf = round(min(conf, 0.70), 3)

    return Signal(
        symbol=symbol,
        direction=direction,
        strategy="coinglass_leverage_squeeze",
        confidence=conf,
        reason=f"Leverage squeeze: ratio={glob:.3f}, funding={funding:.6f}, signal={leverage_signal:.4f}",
        ratios=current_ratios,
    )
```

**Step 2: S6 — Funding-Rate Confirmation**

`coinglass_strategies/strategies/funding_confirmation.py`:
```python
"""S6: Funding-Rate Confirmation — ratio + funding confluence.

When ratio shows strong directional bias AND funding rate confirms it,
the signal has higher conviction. Trend-following.
"""
from typing import Dict, List, Optional

from .base import Signal
from .. import config


def run(symbol: str, recent_rows: List[Dict],
        current_ratios: Dict) -> Optional[Signal]:
    """Check for ratio + funding rate confluence."""
    glob = current_ratios.get("global")
    if glob is None:
        return None

    funding = None
    for row in reversed(recent_rows):
        if row.get("funding_rate") is not None:
            funding = float(row["funding_rate"])
            break

    if funding is None:
        return None

    threshold = config.FUNDING_RATIO_THRESHOLD
    bullish = glob > threshold and funding > 0
    bearish = glob < (2 - threshold) and funding < 0  # e.g., < 0.85

    if not bullish and not bearish:
        return None

    direction = "LONG" if bullish else "SHORT"
    # Stronger confluence = higher confidence
    ratio_strength = abs(glob - 1.0)
    funding_strength = abs(funding) * 10000  # Scale funding (typically 0.0001)
    agreement = min(ratio_strength + funding_strength, 1.0)
    conf = 0.60 + 0.05 * min(agreement / 0.2, 3.0)
    conf = round(min(conf, 0.75), 3)

    return Signal(
        symbol=symbol,
        direction=direction,
        strategy="coinglass_funding_confluence",
        confidence=conf,
        reason=f"Funding confirms ratio: ratio={glob:.3f}, funding={funding:.6f} ({'bullish' if bullish else 'bearish'})",
        ratios=current_ratios,
    )
```

**Step 3: S7 — Sentiment Composite Index**

`coinglass_strategies/strategies/sentiment_index.py`:
```python
"""S7: Composite Sentiment Index — weighted 4-ratio score.

Combines all 4 ratios into a single normalized index:
40% top-trader + 30% taker + 20% global + 10% position.
Smoothed with SMA-5 over recent history.
"""
from typing import Dict, List, Optional

from .base import Signal
from .. import config


def _normalize(value: float, values: List[float]) -> float:
    """Normalize a value to [0, 1] based on min/max of historical values."""
    if not values:
        return 0.5
    mn, mx = min(values), max(values)
    if mx == mn:
        return 0.5
    return (value - mn) / (mx - mn)


def run(symbol: str, recent_rows: List[Dict],
        current_ratios: Dict) -> Optional[Signal]:
    """Compute weighted sentiment index from 4 ratio types."""
    # Need at least some history for normalization
    if len(recent_rows) < 5:
        return None

    # Extract historical values for normalization
    hist = {"global": [], "top_trader_account": [], "taker": [], "top_trader_position": []}
    for row in recent_rows:
        for key, col in [("global", "global_ratio"),
                         ("top_trader_account", "top_trader_account_ratio"),
                         ("taker", "taker_ratio"),
                         ("top_trader_position", "top_trader_position_ratio")]:
            val = row.get(col)
            if val is not None:
                hist[key].append(float(val))

    # Current values
    cur = {
        "global": current_ratios.get("global"),
        "top_trader_account": current_ratios.get("top_trader_account"),
        "taker": current_ratios.get("taker"),
        "top_trader_position": current_ratios.get("top_trader_position"),
    }

    # Need at least global ratio
    if cur["global"] is None:
        return None

    # Normalize each to [0, 1] and compute weighted index
    weights = {"top_trader_account": 0.40, "taker": 0.30, "global": 0.20,
               "top_trader_position": 0.10}
    total_weight = 0
    index = 0
    for key, weight in weights.items():
        val = cur.get(key)
        if val is not None and hist.get(key):
            norm = _normalize(val, hist[key])
            index += norm * weight
            total_weight += weight

    if total_weight == 0:
        return None

    index /= total_weight  # Re-normalize for missing components

    long_thresh = config.SENTIMENT_LONG_THRESHOLD
    short_thresh = config.SENTIMENT_SHORT_THRESHOLD

    if short_thresh < index < long_thresh:
        return None

    direction = "LONG" if index >= long_thresh else "SHORT"
    conf = 0.55 + 0.10 * abs(index - 0.5)
    conf = round(min(conf, 0.70), 3)

    return Signal(
        symbol=symbol,
        direction=direction,
        strategy="coinglass_sentiment_composite",
        confidence=conf,
        reason=f"Sentiment index={index:.3f} (threshold: long>{long_thresh}, short<{short_thresh})",
        ratios=current_ratios,
    )
```

**Step 4: S8 — Spike Detection**

`coinglass_strategies/strategies/spike_detection.py`:
```python
"""S8: Spike Detection — event-driven sudden ratio change.

Detects when any ratio changes >30% within a 15-minute window,
suggesting a large event or whale activity.
"""
from typing import Dict, List, Optional

from .base import Signal
from .. import config


def run(symbol: str, recent_rows: List[Dict],
        current_ratios: Dict) -> Optional[Signal]:
    """Detect sudden spikes in any ratio."""
    if len(recent_rows) < 2:
        return None

    prev = recent_rows[-2] if len(recent_rows) >= 2 else recent_rows[-1]
    threshold_pct = config.SPIKE_THRESHOLD_PCT

    # Check each ratio type for spikes
    ratio_keys = [
        ("global_ratio", "global", "Global"),
        ("top_trader_account_ratio", "top_trader_account", "Top-Trader Account"),
        ("taker_ratio", "taker", "Taker"),
        ("top_trader_position_ratio", "top_trader_position", "Top-Trader Position"),
    ]

    best_spike = None
    best_pct = 0

    for db_col, cur_key, label in ratio_keys:
        prev_val = prev.get(db_col)
        cur_val = current_ratios.get(cur_key)
        if prev_val is None or cur_val is None or prev_val == 0:
            continue
        pct_change = abs(cur_val - float(prev_val)) / float(prev_val) * 100
        if pct_change > threshold_pct and pct_change > best_pct:
            best_pct = pct_change
            best_spike = (label, float(prev_val), cur_val, pct_change)

    if best_spike is None:
        return None

    label, prev_val, cur_val, pct = best_spike
    # Follow the spike direction
    direction = "LONG" if cur_val > prev_val else "SHORT"
    conf = 0.50 + 0.05 * min(pct / 30.0, 3.0)
    conf = round(min(conf, 0.65), 3)

    return Signal(
        symbol=symbol,
        direction=direction,
        strategy="coinglass_spike_detector",
        confidence=conf,
        reason=f"{label} spike: {prev_val:.3f}→{cur_val:.3f} ({pct:.1f}% change)",
        ratios=current_ratios,
    )
```

**Step 5: Commit**

```bash
git add coinglass_strategies/strategies/
git commit -m "feat(coinglass): implement strategies S5-S8 (leverage, funding, sentiment, spike)"
```

---

## Task 7: Build Signal Engine with Deduplication

**Files:**
- Create: `coinglass_strategies/signal_engine.py`

**Step 1: Create the signal engine**

```python
"""Signal engine — runs all 8 strategies, deduplicates, emits picks.

Iterates over configured symbols, fetches fresh ratios, runs each
strategy, deduplicates by symbol+direction, and writes active_picks.json.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from . import config
from .data_fetcher import fetch_all_ratios, fetch_funding_rate, fetch_current_price, fetch_atr
from . import ratio_store
from .strategies import (
    extreme_reversion,
    top_trader_divergence,
    ratio_momentum,
    cross_exchange_spread,
    leverage_adjusted,
    funding_confirmation,
    sentiment_index,
    spike_detection,
)
from .strategies.base import Signal

logger = logging.getLogger(__name__)

# Strategy registry — order matters for priority in dedup
STRATEGIES = [
    ("S2-WhaleDivergence", top_trader_divergence),
    ("S1-ExtremeReversion", extreme_reversion),
    ("S6-FundingConfluence", funding_confirmation),
    ("S5-LeverageSqueeze", leverage_adjusted),
    ("S7-SentimentComposite", sentiment_index),
    ("S3-RatioMomentum", ratio_momentum),
    ("S8-SpikeDetector", spike_detection),
    ("S4-ExchangeSpread", cross_exchange_spread),
]

ACTIVE_PICKS_PATH = config.DATA_DIR / "active_picks.json"


def fetch_and_store(symbol: str) -> Dict:
    """Fetch ratios + funding rate, store in DB, return current ratios."""
    ratios = fetch_all_ratios(symbol)
    funding = fetch_funding_rate(symbol)
    ratio_store.store_ratios(symbol, ratios, funding_rate=funding)
    return ratios


def run_strategies(symbol: str, current_ratios: Dict) -> List[Signal]:
    """Run all 8 strategies for a symbol, return list of signals."""
    recent = ratio_store.get_recent_ratios(
        symbol, window_minutes=config.ZSCORE_WINDOW_MINUTES)
    signals = []

    for name, strategy_mod in STRATEGIES:
        try:
            # S4 has a different signature (no recent_rows)
            if strategy_mod == cross_exchange_spread:
                sig = strategy_mod.run(symbol)
            else:
                sig = strategy_mod.run(symbol, recent, current_ratios)
            if sig:
                signals.append(sig)
                logger.info("[%s] %s → %s %s (conf=%.3f)",
                            name, symbol, sig.direction, sig.strategy, sig.confidence)
        except Exception as exc:
            logger.warning("[%s] %s failed: %s", name, symbol, exc)

    return signals


def deduplicate(signals: List[Signal]) -> List[Signal]:
    """Keep only the highest-confidence signal per symbol+direction."""
    best = {}
    for sig in signals:
        key = f"{sig.symbol}_{sig.direction}"
        if key not in best or sig.confidence > best[key].confidence:
            best[key] = sig
    return list(best.values())


def add_price_levels(signals: List[Signal]):
    """Compute entry, TP, SL for each signal using current price + ATR."""
    for sig in signals:
        price = fetch_current_price(sig.symbol)
        atr = fetch_atr(sig.symbol)
        if price is None or atr is None:
            continue
        sig.entry_price = price
        if sig.direction == "LONG":
            sig.take_profit = round(price + atr * config.TP_ATR_MULT, 2)
            sig.stop_loss = round(price - atr * config.SL_ATR_MULT, 2)
        else:
            sig.take_profit = round(price - atr * config.TP_ATR_MULT, 2)
            sig.stop_loss = round(price + atr * config.SL_ATR_MULT, 2)


def scan_all() -> List[Dict]:
    """Full scan: fetch → store → strategize → deduplicate → write picks."""
    ratio_store.init_db()
    all_signals = []

    for symbol in config.SYMBOLS:
        logger.info("Scanning %s ...", symbol)
        current_ratios = fetch_and_store(symbol)
        if current_ratios.get("source") is None:
            logger.warning("No data for %s, skipping", symbol)
            continue
        signals = run_strategies(symbol, current_ratios)
        all_signals.extend(signals)

    # Deduplicate
    deduped = deduplicate(all_signals)

    # Add price levels
    add_price_levels(deduped)

    # Store signals in DB
    for sig in deduped:
        ratio_store.store_signal(sig.to_dict())

    # Write active_picks.json for cross-aggregation
    picks = [sig.to_dict() for sig in deduped if sig.entry_price > 0]
    ACTIVE_PICKS_PATH.write_text(json.dumps(picks, indent=2, default=str))
    logger.info("Wrote %d picks to %s", len(picks), ACTIVE_PICKS_PATH)

    return picks
```

**Step 2: Commit**

```bash
git add coinglass_strategies/signal_engine.py
git commit -m "feat(coinglass): build signal engine with 8-strategy registry and deduplication"
```

---

## Task 8: Build Paper Portfolio Manager

**Files:**
- Create: `coinglass_strategies/paper_portfolio.py`

**Step 1: Create paper portfolio manager**

```python
"""Paper portfolio manager — $10K virtual equity, ATR-based sizing.

Manages position lifecycle: open → monitor → close (TP/SL/timeout).
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List

from . import config
from .data_fetcher import fetch_current_price
from . import ratio_store

logger = logging.getLogger(__name__)


def compute_position_size(equity: float, entry_price: float,
                          stop_loss: float) -> float:
    """Compute position size based on % equity risk."""
    risk_per_unit = abs(entry_price - stop_loss)
    if risk_per_unit == 0:
        return 0
    risk_amount = equity * (config.RISK_PER_TRADE_PCT / 100)
    quantity = risk_amount / risk_per_unit
    return round(quantity * entry_price, 2)  # Dollar value of position


def open_positions_from_picks(picks: List[Dict]):
    """Open new paper positions from fresh signal picks."""
    open_positions = ratio_store.get_open_positions()
    if len(open_positions) >= config.MAX_CONCURRENT_POSITIONS:
        logger.info("Max positions (%d) reached, skipping new entries",
                     config.MAX_CONCURRENT_POSITIONS)
        return

    equity = ratio_store.get_portfolio_equity()
    existing_symbols = {p["symbol"] for p in open_positions}
    slots = config.MAX_CONCURRENT_POSITIONS - len(open_positions)

    for pick in picks[:slots]:
        if pick["symbol"] in existing_symbols:
            continue
        entry = pick.get("entry_price", 0)
        sl = pick.get("stop_loss", 0)
        if entry == 0 or sl == 0:
            continue
        qty = compute_position_size(equity, entry, sl)
        risk_amount = equity * (config.RISK_PER_TRADE_PCT / 100)
        ratio_store.open_position(pick, quantity=qty, risk_amount=risk_amount)
        logger.info("Opened %s %s @ %.2f (qty=$%.2f, TP=%.2f, SL=%.2f)",
                     pick["direction"], pick["symbol"], entry, qty,
                     pick["take_profit"], pick["stop_loss"])


def monitor_positions():
    """Check open positions for TP/SL hits or timeout."""
    positions = ratio_store.get_open_positions()
    if not positions:
        return

    for pos in positions:
        symbol = pos["symbol"]
        price = fetch_current_price(symbol)
        if price is None:
            continue

        entry = pos["entry_price"]
        tp = pos["take_profit"]
        sl = pos["stop_loss"]
        direction = pos["direction"]

        # Check TP/SL
        if direction == "LONG":
            if price >= tp:
                ratio_store.close_position(pos["signal_id"], price, "TP_HIT")
                logger.info("TP HIT: %s LONG @ %.2f → %.2f", symbol, entry, price)
            elif price <= sl:
                ratio_store.close_position(pos["signal_id"], price, "SL_HIT")
                logger.info("SL HIT: %s LONG @ %.2f → %.2f", symbol, entry, price)
        else:
            if price <= tp:
                ratio_store.close_position(pos["signal_id"], price, "TP_HIT")
                logger.info("TP HIT: %s SHORT @ %.2f → %.2f", symbol, entry, price)
            elif price >= sl:
                ratio_store.close_position(pos["signal_id"], price, "SL_HIT")
                logger.info("SL HIT: %s SHORT @ %.2f → %.2f", symbol, entry, price)

        # Check timeout
        opened = datetime.fromisoformat(pos["opened_at"].replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - opened).total_seconds() / 3600
        if age_hours > config.MAX_HOLD_HOURS:
            ratio_store.close_position(pos["signal_id"], price, "TIMEOUT")
            logger.info("TIMEOUT: %s %s after %.1fh", symbol, direction, age_hours)

    # Save portfolio snapshot
    ratio_store.save_snapshot()


def get_portfolio_summary() -> Dict:
    """Get current portfolio state for Discord reporting."""
    equity = ratio_store.get_portfolio_equity()
    open_pos = ratio_store.get_open_positions()
    closed = ratio_store.get_closed_positions(limit=9999)
    wins = sum(1 for p in closed if (p.get("pnl_pct") or 0) > 0)
    losses = sum(1 for p in closed if (p.get("pnl_pct") or 0) <= 0)
    total = wins + losses
    total_pnl = sum(p.get("pnl_dollar", 0) for p in closed)

    return {
        "equity": round(equity, 2),
        "starting_capital": config.STARTING_CAPITAL,
        "pnl_pct": round((equity - config.STARTING_CAPITAL) / config.STARTING_CAPITAL * 100, 2),
        "total_pnl": round(total_pnl, 2),
        "open_positions": len(open_pos),
        "positions": open_pos,
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / total * 100, 2) if total else 0,
    }
```

**Step 2: Commit**

```bash
git add coinglass_strategies/paper_portfolio.py
git commit -m "feat(coinglass): add paper portfolio manager with ATR sizing and TP/SL monitoring"
```

---

## Task 9: Build Discord Notifier for #paper-trade

**Files:**
- Create: `coinglass_strategies/discord_notify.py`

**Step 1: Create Discord notifier**

```python
"""Discord notifier for #paper-trade channel.

Sends signal alerts (immediate) and portfolio summaries (every 2h).
"""
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, List

import requests

logger = logging.getLogger(__name__)

WEBHOOK_URL = os.environ.get(
    "DISCORD_WEBHOOK_PAPERTRADE",
    "https://discord.com/api/webhooks/1478588243459965008/9TZAjAtrgz5dTvWpV3TP7FO8Fo5JRDCz03PkPiTaSlef0EcIEdHEDUmz8Zi13sZrqgA3"
)
USERNAME = "Coinglass DNA Bundle"

COLOR_GREEN = 0x22C55E
COLOR_RED = 0xEF4444
COLOR_BLUE = 0x3B82F6
COLOR_GOLD = 0xFFD700
COLOR_PURPLE = 0x8B5CF6


def _post(embeds: list):
    """Post embeds to Discord webhook."""
    if not WEBHOOK_URL:
        logger.warning("No DISCORD_WEBHOOK_PAPERTRADE set")
        return
    for i in range(0, len(embeds), 10):
        batch = embeds[i:i + 10]
        payload = {"username": USERNAME, "embeds": batch}
        try:
            resp = requests.post(WEBHOOK_URL, json=payload, timeout=15)
            if resp.status_code == 429:
                retry = resp.json().get("retry_after", 5)
                time.sleep(retry)
                requests.post(WEBHOOK_URL, json=payload, timeout=15)
            elif resp.status_code not in (200, 204):
                logger.warning("Discord post failed: %d", resp.status_code)
        except Exception as exc:
            logger.error("Discord error: %s", exc)


def send_signal_alerts(picks: List[Dict]):
    """Send immediate alert for new trading signals."""
    if not picks:
        return
    embeds = []
    for pick in picks:
        direction = pick.get("direction", "?")
        color = COLOR_GREEN if direction == "LONG" else COLOR_RED
        symbol = pick.get("symbol", "?")
        entry = pick.get("entry_price", 0)
        tp = pick.get("take_profit", 0)
        sl = pick.get("stop_loss", 0)
        conf = pick.get("confidence", 0)
        strategy = pick.get("strategy", "?")
        reason = pick.get("reason", "")

        # Confidence bar
        filled = int(conf * 10)
        bar = "█" * filled + "░" * (10 - filled)

        embed = {
            "title": f"{'🟢' if direction == 'LONG' else '🔴'} {direction} {symbol}",
            "color": color,
            "fields": [
                {"name": "Strategy", "value": f"`{strategy}`", "inline": True},
                {"name": "Confidence", "value": f"{bar} {conf:.0%}", "inline": True},
                {"name": "Entry", "value": f"${entry:,.2f}", "inline": True},
                {"name": "Take Profit", "value": f"${tp:,.2f}", "inline": True},
                {"name": "Stop Loss", "value": f"${sl:,.2f}", "inline": True},
                {"name": "R:R", "value": f"{abs(tp - entry) / abs(entry - sl):.1f}x" if abs(entry - sl) > 0 else "—", "inline": True},
                {"name": "Rationale", "value": reason[:200], "inline": False},
            ],
            "footer": {"text": f"Coinglass DNA Bundle • {datetime.now(timezone.utc).strftime('%H:%M UTC')}"},
        }
        embeds.append(embed)

    _post(embeds)
    logger.info("Sent %d signal alerts to Discord", len(embeds))


def send_portfolio_summary(summary: Dict, ratio_snapshot: Dict = None):
    """Send portfolio summary embed (called every 2h)."""
    equity = summary.get("equity", 0)
    pnl_pct = summary.get("pnl_pct", 0)
    color = COLOR_GREEN if pnl_pct >= 0 else COLOR_RED

    # Open positions list
    positions_text = ""
    for pos in summary.get("positions", [])[:5]:
        sym = pos.get("symbol", "?")
        d = pos.get("direction", "?")
        entry = pos.get("entry_price", 0)
        positions_text += f"{'🟢' if d == 'LONG' else '🔴'} {sym} {d} @ ${entry:,.2f}\n"
    if not positions_text:
        positions_text = "No open positions"

    embed = {
        "title": "📊 Coinglass DNA — Portfolio Summary",
        "color": color,
        "fields": [
            {"name": "Equity", "value": f"${equity:,.2f}", "inline": True},
            {"name": "P&L", "value": f"{'+'if pnl_pct >= 0 else ''}{pnl_pct:.2f}%", "inline": True},
            {"name": "Total P&L", "value": f"${summary.get('total_pnl', 0):,.2f}", "inline": True},
            {"name": "Trades", "value": f"{summary.get('total_trades', 0)} ({summary.get('wins', 0)}W / {summary.get('losses', 0)}L)", "inline": True},
            {"name": "Win Rate", "value": f"{summary.get('win_rate', 0):.1f}%", "inline": True},
            {"name": "Open Positions", "value": f"{summary.get('open_positions', 0)}/{5}", "inline": True},
            {"name": "Positions", "value": positions_text, "inline": False},
        ],
        "footer": {"text": f"Starting capital: ${summary.get('starting_capital', 10000):,.0f} • Updated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"},
    }

    # Add ratio snapshot if available
    if ratio_snapshot:
        ratio_text = ""
        for sym, data in ratio_snapshot.items():
            g = data.get("global", "—")
            t = data.get("taker", "—")
            ratio_text += f"**{sym}**: G={g:.3f} T={t:.3f}\n" if isinstance(g, float) else f"**{sym}**: no data\n"
        if ratio_text:
            embed["fields"].append({"name": "Current Ratios", "value": ratio_text[:1024], "inline": False})

    _post([embed])
    logger.info("Sent portfolio summary to Discord")


def send_close_alert(position: Dict, exit_reason: str, exit_price: float):
    """Send alert when a position is closed."""
    direction = position.get("direction", "?")
    symbol = position.get("symbol", "?")
    entry = position.get("entry_price", 0)
    pnl_pct = position.get("pnl_pct", 0)
    is_win = exit_reason == "TP_HIT"
    color = COLOR_GOLD if is_win else COLOR_PURPLE

    embed = {
        "title": f"{'✅' if is_win else '❌'} CLOSED {symbol} {direction}",
        "color": color,
        "fields": [
            {"name": "Entry", "value": f"${entry:,.2f}", "inline": True},
            {"name": "Exit", "value": f"${exit_price:,.2f}", "inline": True},
            {"name": "P&L", "value": f"{'+'if pnl_pct >= 0 else ''}{pnl_pct:.2f}%", "inline": True},
            {"name": "Reason", "value": exit_reason, "inline": True},
        ],
        "footer": {"text": f"Coinglass DNA Bundle • {datetime.now(timezone.utc).strftime('%H:%M UTC')}"},
    }
    _post([embed])
```

**Step 2: Commit**

```bash
git add coinglass_strategies/discord_notify.py
git commit -m "feat(coinglass): add Discord notifier for #paper-trade channel"
```

---

## Task 10: Build CLI Scanner

**Files:**
- Create: `coinglass_strategies/scanner.py`
- Create: `coinglass_strategies/__main__.py`

**Step 1: Create scanner CLI**

`coinglass_strategies/scanner.py`:
```python
"""CLI entry point for the Coinglass DNA Bundle.

Usage:
    python -m coinglass_strategies --scan              # Fetch + generate signals
    python -m coinglass_strategies --portfolio          # Monitor positions + P&L
    python -m coinglass_strategies --summary            # Send Discord portfolio summary
    python -m coinglass_strategies --scan --portfolio   # Full cycle
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone

from . import config
from . import ratio_store
from .signal_engine import scan_all
from .paper_portfolio import open_positions_from_picks, monitor_positions, get_portfolio_summary
from .discord_notify import send_signal_alerts, send_portfolio_summary
from .data_fetcher import fetch_all_ratios

logger = logging.getLogger(__name__)


def cmd_scan():
    """Fetch ratios, run strategies, emit picks, send Discord alerts."""
    logger.info("=== Coinglass DNA Scanner ===")
    picks = scan_all()
    logger.info("Generated %d picks", len(picks))
    if picks:
        send_signal_alerts(picks)
    return picks


def cmd_portfolio(picks=None):
    """Open positions from picks, monitor existing, check TP/SL."""
    logger.info("=== Portfolio Monitor ===")
    if picks:
        open_positions_from_picks(picks)
    monitor_positions()
    summary = get_portfolio_summary()
    logger.info("Equity: $%.2f | Open: %d | Win rate: %.1f%%",
                summary["equity"], summary["open_positions"], summary["win_rate"])
    return summary


def cmd_summary():
    """Send portfolio summary + ratio snapshot to Discord."""
    logger.info("=== Portfolio Summary ===")
    summary = get_portfolio_summary()

    # Collect current ratios for all symbols
    ratio_snapshot = {}
    for symbol in config.SYMBOLS:
        ratios = fetch_all_ratios(symbol)
        ratio_snapshot[symbol] = ratios

    send_portfolio_summary(summary, ratio_snapshot)
    return summary


def main():
    parser = argparse.ArgumentParser(description="Coinglass DNA Bundle Scanner")
    parser.add_argument("--scan", action="store_true", help="Fetch ratios and generate signals")
    parser.add_argument("--portfolio", action="store_true", help="Monitor paper portfolio")
    parser.add_argument("--summary", action="store_true", help="Send Discord portfolio summary")
    parser.add_argument("--init-db", action="store_true", help="Initialize database only")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")

    # Load Discord webhook from env if not hardcoded
    if os.environ.get("DISCORD_WEBHOOK_PAPERTRADE"):
        from . import discord_notify
        discord_notify.WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_PAPERTRADE"]

    ratio_store.init_db()

    if args.init_db:
        logger.info("Database initialized at %s", config.DB_PATH)
        return

    picks = None
    if args.scan:
        picks = cmd_scan()
    if args.portfolio:
        cmd_portfolio(picks)
    if args.summary:
        cmd_summary()

    if not any([args.scan, args.portfolio, args.summary, args.init_db]):
        # Default: full cycle
        picks = cmd_scan()
        cmd_portfolio(picks)

    # Prune old data
    ratio_store.prune_old(days=60)

    logger.info("Done.")


if __name__ == "__main__":
    main()
```

`coinglass_strategies/__main__.py`:
```python
from .scanner import main
main()
```

**Step 2: Test the CLI**

Run: `cd /e/findtorontoevents_antigravity.ca && py -m coinglass_strategies --init-db`
Expected: "Database initialized at coinglass_strategies/data/coinglass.db"

Run: `py -m coinglass_strategies --scan -v`
Expected: Scans 5 symbols, fetches ratios from Binance, writes active_picks.json

**Step 3: Commit**

```bash
git add coinglass_strategies/scanner.py coinglass_strategies/__main__.py
git commit -m "feat(coinglass): add CLI scanner with --scan, --portfolio, --summary modes"
```

---

## Task 11: Create GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/coinglass-scanner.yml`

**Step 1: Create the workflow**

```yaml
name: Coinglass DNA Scanner

on:
  schedule:
    - cron: '3,18,33,48 * * * *'    # Every 15 min (offset to avoid collisions)
  workflow_dispatch:
    inputs:
      mode:
        description: 'Run mode'
        required: false
        default: 'full'
        type: choice
        options:
          - full
          - scan-only
          - portfolio-only
          - summary-only

jobs:
  scan:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install requests

      - name: Run Coinglass DNA Scanner
        env:
          DISCORD_WEBHOOK_PAPERTRADE: ${{ secrets.DISCORD_WEBHOOK_PAPERTRADE }}
        run: |
          MODE="${{ github.event.inputs.mode || 'full' }}"
          echo "Mode: $MODE"

          if [ "$MODE" = "scan-only" ]; then
            python -m coinglass_strategies --scan
          elif [ "$MODE" = "portfolio-only" ]; then
            python -m coinglass_strategies --portfolio
          elif [ "$MODE" = "summary-only" ]; then
            python -m coinglass_strategies --summary
          else
            python -m coinglass_strategies --scan --portfolio
          fi

      # Send portfolio summary every 2 hours (at :03 past even hours)
      - name: Portfolio summary (every 2h)
        if: github.event.schedule == '3,18,33,48 * * * *'
        env:
          DISCORD_WEBHOOK_PAPERTRADE: ${{ secrets.DISCORD_WEBHOOK_PAPERTRADE }}
        run: |
          HOUR=$(date -u +%H)
          MINUTE=$(date -u +%M)
          if [ "$MINUTE" -lt "15" ] && [ $((HOUR % 2)) -eq 0 ]; then
            echo "Sending 2-hour portfolio summary"
            python -m coinglass_strategies --summary
          fi

      - name: Commit data changes
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "Coinglass scan [$(date -u +'%Y-%m-%d %H:%M UTC')]"
          file_pattern: "coinglass_strategies/data/*"
```

**Step 2: Commit**

```bash
git add .github/workflows/coinglass-scanner.yml
git commit -m "ci(coinglass): add GitHub Actions workflow running every 15 min"
```

---

## Task 12: Wire into Cross-Aggregation

**Files:**
- Modify: `cross_aggregation/aggregator.py` (add coinglass_strategies to source list)

**Step 1: Add coinglass_strategies to the SYSTEMS dict**

Find the `SYSTEMS` dictionary in `cross_aggregation/aggregator.py` and add:

```python
"coinglass_strategies": "coinglass_strategies/data/active_picks.json",
```

**Step 2: Commit**

```bash
git add cross_aggregation/aggregator.py
git commit -m "feat(cross-agg): wire coinglass_strategies into consensus aggregator"
```

---

## Task 13: Add Discord Webhook Secret & Initial Data Directory

**Files:**
- Create: `coinglass_strategies/data/.gitkeep`
- Modify: `.github/workflows/coinglass-scanner.yml` (if secret name needs updating)

**Step 1: Create data directory placeholder**

```bash
mkdir -p coinglass_strategies/data
touch coinglass_strategies/data/.gitkeep
```

**Step 2: Add the Discord webhook as a GitHub secret**

```bash
gh secret set DISCORD_WEBHOOK_PAPERTRADE --body "https://discord.com/api/webhooks/1478588243459965008/9TZAjAtrgz5dTvWpV3TP7FO8Fo5JRDCz03PkPiTaSlef0EcIEdHEDUmz8Zi13sZrqgA3"
```

**Step 3: Verify secret was set**

```bash
gh secret list | grep PAPERTRADE
```

**Step 4: Commit**

```bash
git add coinglass_strategies/data/.gitkeep
git commit -m "chore(coinglass): add data directory and Discord webhook secret"
```

---

## Task 14: End-to-End Test & First Run

**Step 1: Initialize the database locally**

```bash
cd /e/findtorontoevents_antigravity.ca
py -m coinglass_strategies --init-db
```

**Step 2: Run a full scan locally**

```bash
py -m coinglass_strategies --scan --portfolio -v
```

Expected output:
- Fetches ratios for 5 symbols from Binance
- Runs 8 strategies per symbol
- Writes `coinglass_strategies/data/active_picks.json`
- Opens paper positions for any signals
- Sends Discord alerts to #paper-trade

**Step 3: Verify active_picks.json**

```bash
cat coinglass_strategies/data/active_picks.json
```

Expected: JSON array of picks with symbol, direction, entry_price, take_profit, stop_loss, confidence, strategy fields.

**Step 4: Verify Discord message arrived in #paper-trade**

Check the Discord channel for signal alert embeds.

**Step 5: Trigger GitHub Actions workflow**

```bash
gh workflow run coinglass-scanner.yml
gh run list --workflow=coinglass-scanner.yml --limit=1
```

**Step 6: Commit any data files**

```bash
git add coinglass_strategies/data/
git commit -m "chore(coinglass): initial scan data from first run"
```

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Package init + config | `__init__.py`, `config.py` |
| 2 | Data fetcher rewrite (Binance 4 endpoints + failover) | `data_fetcher.py` |
| 3 | Ratio store upgrade (signals, positions, snapshots) | `ratio_store.py` |
| 4 | Strategy base + Signal dataclass | `strategies/__init__.py`, `strategies/base.py` |
| 5 | Strategies S1-S4 | 4 strategy files |
| 6 | Strategies S5-S8 | 4 strategy files |
| 7 | Signal engine with dedup | `signal_engine.py` |
| 8 | Paper portfolio manager | `paper_portfolio.py` |
| 9 | Discord notifier | `discord_notify.py` |
| 10 | CLI scanner | `scanner.py`, `__main__.py` |
| 11 | GitHub Actions workflow | `coinglass-scanner.yml` |
| 12 | Cross-aggregation wiring | `aggregator.py` |
| 13 | Data dir + Discord secret | `.gitkeep`, GitHub secret |
| 14 | E2E test + first run | Verify everything works |
