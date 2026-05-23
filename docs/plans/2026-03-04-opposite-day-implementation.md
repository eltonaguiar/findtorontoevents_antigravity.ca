# Opposite Day Paper-Trade System — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deploy a multi-engine "Opposite Day" paper-trade system that flips picks from 5 signal engines, tracks time-decay performance (1h/4h/12h/24h), and posts results to Discord #paper-trade channel.

**Architecture:** Modular `sandbox/` package with engine adapters that normalize picks from 5 sources into a common format, SQLite for persistent tracking with timeline snapshots, and Discord webhook embeds for reporting. GitHub Actions runs every 30 min.

**Tech Stack:** Python 3.11, SQLite3 (stdlib), requests, Binance public API (prices), Discord webhooks

---

### Task 1: Config Module

**Files:**
- Create: `sandbox/__init__.py`
- Create: `sandbox/config.py`
- Create: `sandbox/data/.gitkeep`

**Step 1: Create directory structure**

```bash
mkdir -p sandbox/data
```

**Step 2: Write `sandbox/__init__.py`**

```python
"""Opposite Day Paper-Trade System.

Flips picks from 5 signal engines and tracks time-decay performance.
"""
```

**Step 3: Write `sandbox/config.py`**

```python
"""Configuration for the Opposite Day sandbox."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # repo root
SANDBOX_DIR = Path(__file__).resolve().parent
DB_PATH = SANDBOX_DIR / "data" / "opposite_day.db"

# Engine source files (relative to ROOT)
ENGINE_SOURCES = {
    "predictions": ROOT / "predictions" / "data" / "active_predictions.json",
    "kimi": ROOT / "KIMI_RISEOFTHECLAW" / "data" / "live_signals_now.json",
    "alpha": ROOT / "alpha_engine" / "data" / "active_picks.json",
    "signal_engine": ROOT / "crypto_signal_engine" / "data" / "active_picks.json",
    "cross_aggregator": ROOT / "cross_aggregation" / "data" / "super_signals.json",
}

# Timeline checkpoints in seconds
CHECKPOINTS = {"1h": 3600, "4h": 14400, "12h": 43200, "24h": 86400}

# Pick expiration
EXPIRATION_SECONDS = 86400  # 24 hours

# Default TP/SL for engines that don't provide them (percentage from entry)
DEFAULT_TP_PCT = 5.0
DEFAULT_SL_PCT = 3.0

# Excluded symbols
EXCLUDED_SYMBOLS = {"SUIUSDT"}

# Discord
WEBHOOK_ENV_VAR = "DISCORD_PAPER_TRADE_WEBHOOK"
EMBED_CHAR_LIMIT = 6000
MAX_PICKS_PER_EMBED = 8  # truncate after this many

# Price fetch
BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/price"
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
```

**Step 4: Create .gitkeep**

```bash
touch sandbox/data/.gitkeep
```

**Step 5: Commit**

```bash
git add sandbox/__init__.py sandbox/config.py sandbox/data/.gitkeep
git commit -m "feat(sandbox): add config module and directory structure"
```

---

### Task 2: Core Module — Flip Logic & Types

**Files:**
- Create: `sandbox/core.py`

**Step 1: Write `sandbox/core.py`**

```python
"""Core flip logic, types, and symbol normalization."""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

from sandbox.config import DEFAULT_TP_PCT, DEFAULT_SL_PCT, EXPIRATION_SECONDS


@dataclass
class NormalizedPick:
    symbol: str
    original_direction: str
    opposite_direction: str
    entry_price: float
    original_tp: float
    original_sl: float
    opposite_tp: float
    opposite_sl: float
    source_engine: str
    source_pick_id: str
    picked_at: str
    expiration_at: str
    confidence: float = 0.0


# ── Symbol normalization ────────────────────────────────────────────

# Common suffixes to strip before adding USDT
_STRIP_SUFFIXES = ["-USD", "USD", "-USDT", "/USDT", "/USD"]

def normalize_symbol(raw: str) -> str:
    """Normalize any symbol variant to XXXUSDT format.

    Examples:
        BTC-USD   → BTCUSDT
        BTCUSD    → BTCUSDT
        BTC       → BTCUSDT
        ETHUSDT   → ETHUSDT
        ETH/USD   → ETHUSDT
    """
    s = raw.upper().strip()
    if s.endswith("USDT"):
        return s
    for suffix in _STRIP_SUFFIXES:
        if s.endswith(suffix):
            s = s[: -len(suffix)]
            break
    return s + "USDT"


# ── Direction flip ──────────────────────────────────────────────────

def flip_direction(direction: str) -> str:
    """LONG → SHORT, SHORT → LONG.  Also handles BUY/SELL."""
    d = direction.upper().strip()
    if d in ("LONG", "BUY"):
        return "SHORT"
    return "LONG"


# ── Distance-based TP/SL inversion ─────────────────────────────────

def flip_tp_sl(
    entry: float,
    tp: float,
    sl: float,
    original_direction: str,
) -> tuple:
    """Compute opposite TP/SL using distance from entry.

    For LONG→SHORT:  new_tp = entry - |tp - entry|,  new_sl = entry + |entry - sl|
    For SHORT→LONG:  new_tp = entry + |entry - tp|,  new_sl = entry - |sl - entry|
    """
    dist_tp = abs(tp - entry)
    dist_sl = abs(sl - entry)

    if original_direction.upper() in ("LONG", "BUY"):
        # Flipping to SHORT
        return round(entry - dist_tp, 8), round(entry + dist_sl, 8)
    else:
        # Flipping to LONG
        return round(entry + dist_tp, 8), round(entry - dist_sl, 8)


def default_tp_sl(entry: float, direction: str) -> tuple:
    """Generate default TP/SL when source doesn't provide them."""
    tp_dist = entry * DEFAULT_TP_PCT / 100
    sl_dist = entry * DEFAULT_SL_PCT / 100
    if direction.upper() in ("LONG", "BUY"):
        return round(entry + tp_dist, 8), round(entry - sl_dist, 8)
    return round(entry - tp_dist, 8), round(entry + sl_dist, 8)


def make_pick_id(source_engine: str, symbol: str, direction: str, timestamp: str) -> str:
    """Generate a unique pick ID."""
    return f"opp::{source_engine}::{symbol}::{direction}::{timestamp[:19]}"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def expiration_from(picked_at: str) -> str:
    dt = datetime.fromisoformat(picked_at.replace("Z", "+00:00"))
    exp = dt + timedelta(seconds=EXPIRATION_SECONDS)
    return exp.strftime("%Y-%m-%dT%H:%M:%SZ")
```

**Step 2: Commit**

```bash
git add sandbox/core.py
git commit -m "feat(sandbox): add core flip logic, types, symbol normalization"
```

---

### Task 3: PnL Module

**Files:**
- Create: `sandbox/pnl.py`

**Step 1: Write `sandbox/pnl.py`**

```python
"""PnL computation utilities."""


def compute_pnl_pct(entry: float, current: float, direction: str) -> float:
    """Compute unrealized PnL percentage.

    For SHORT: profit when price drops → (entry - current) / entry * 100
    For LONG:  profit when price rises → (current - entry) / entry * 100
    """
    if entry <= 0:
        return 0.0
    if direction.upper() == "SHORT":
        return round((entry - current) / entry * 100, 4)
    return round((current - entry) / entry * 100, 4)


def check_tp_sl(
    entry: float,
    current: float,
    tp: float,
    sl: float,
    direction: str,
) -> str:
    """Check if TP or SL was hit.

    Returns: 'TP_HIT', 'SL_HIT', or 'ACTIVE'.
    Rule: if both crossed in same check, TP wins.
    """
    d = direction.upper()
    tp_hit = False
    sl_hit = False

    if d == "SHORT":
        tp_hit = current <= tp
        sl_hit = current >= sl
    else:  # LONG
        tp_hit = current >= tp
        sl_hit = current <= sl

    if tp_hit:
        return "TP_HIT"
    if sl_hit:
        return "SL_HIT"
    return "ACTIVE"
```

**Step 2: Commit**

```bash
git add sandbox/pnl.py
git commit -m "feat(sandbox): add PnL computation and TP/SL check"
```

---

### Task 4: Engine Adapters

**Files:**
- Create: `sandbox/engine_adapters.py`

**Step 1: Write `sandbox/engine_adapters.py`**

Each adapter reads its source JSON and returns `List[NormalizedPick]`. Each is wrapped in try/except so one broken engine never kills the run.

```python
"""Engine adapters — normalize picks from 5 sources into NormalizedPick."""

import json
import logging
from pathlib import Path
from typing import List

from sandbox.config import ENGINE_SOURCES, EXCLUDED_SYMBOLS
from sandbox.core import (
    NormalizedPick,
    normalize_symbol,
    flip_direction,
    flip_tp_sl,
    default_tp_sl,
    make_pick_id,
    utc_now,
    expiration_from,
)

log = logging.getLogger(__name__)


def _read_json(path: Path):
    """Safely read a JSON file, return empty list/dict on error."""
    if not path.is_file():
        log.warning("Source file not found: %s", path)
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.error("Failed to read %s: %s", path, exc)
        return []


# ── Predictions Dashboard ───────────────────────────────────────────

def _adapt_predictions() -> List[NormalizedPick]:
    """Flip picks from predictions/data/active_predictions.json.

    Fields: symbol, direction (LONG/SHORT), entry_price, take_profit, stop_loss,
            id, scraped_at, predictor_id
    """
    data = _read_json(ENGINE_SOURCES["predictions"])
    if not isinstance(data, list):
        return []

    # Deduplicate by symbol+direction (many predictors may have same symbol)
    seen = set()
    picks = []
    for p in data:
        try:
            sym = normalize_symbol(p.get("symbol", ""))
            if sym in EXCLUDED_SYMBOLS:
                continue
            orig_dir = p.get("direction", "").upper()
            if not orig_dir or orig_dir not in ("LONG", "SHORT"):
                continue

            dedup_key = f"{sym}_{orig_dir}"
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            entry = float(p["entry_price"])
            tp = float(p.get("take_profit") or 0)
            sl = float(p.get("stop_loss") or 0)
            if tp == 0 or sl == 0:
                tp, sl = default_tp_sl(entry, orig_dir)

            opp_dir = flip_direction(orig_dir)
            opp_tp, opp_sl = flip_tp_sl(entry, tp, sl, orig_dir)
            ts = p.get("scraped_at", utc_now())
            pick_id = make_pick_id("predictions", sym, opp_dir, ts)

            picks.append(NormalizedPick(
                symbol=sym,
                original_direction=orig_dir,
                opposite_direction=opp_dir,
                entry_price=entry,
                original_tp=tp,
                original_sl=sl,
                opposite_tp=opp_tp,
                opposite_sl=opp_sl,
                source_engine="predictions",
                source_pick_id=pick_id,
                picked_at=ts,
                expiration_at=expiration_from(ts),
                confidence=float(p.get("sentiment_score", 0)),
            ))
        except Exception as exc:
            log.warning("Predictions adapter skip: %s", exc)
    return picks


# ── KIMI Rise of the Claw ──────────────────────────────────────────

def _adapt_kimi() -> List[NormalizedPick]:
    """Flip picks from KIMI_RISEOFTHECLAW/data/live_signals_now.json.

    Top-level: {crypto_signals: [{symbol, signal (BUY/SELL), entryPrice,
                targetPrice, stopPrice, confidence, algorithm, timestamp}]}
    """
    raw = _read_json(ENGINE_SOURCES["kimi"])
    if isinstance(raw, dict):
        data = raw.get("crypto_signals", [])
    else:
        data = raw

    seen = set()
    picks = []
    for p in data:
        try:
            sym = normalize_symbol(p.get("symbol", ""))
            if sym in EXCLUDED_SYMBOLS:
                continue
            signal = p.get("signal", "").upper()
            orig_dir = "LONG" if signal == "BUY" else "SHORT"

            dedup_key = f"{sym}_{orig_dir}"
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            entry = float(p.get("entryPrice") or p.get("price", 0))
            if entry <= 0:
                continue
            tp = float(p.get("targetPrice") or p.get("take_profit") or 0)
            sl = float(p.get("stopPrice") or p.get("stop_loss") or 0)
            if tp == 0 or sl == 0:
                tp, sl = default_tp_sl(entry, orig_dir)

            opp_dir = flip_direction(orig_dir)
            opp_tp, opp_sl = flip_tp_sl(entry, tp, sl, orig_dir)
            ts = p.get("timestamp", utc_now())
            pick_id = make_pick_id("kimi", sym, opp_dir, ts)

            picks.append(NormalizedPick(
                symbol=sym,
                original_direction=orig_dir,
                opposite_direction=opp_dir,
                entry_price=entry,
                original_tp=tp,
                original_sl=sl,
                opposite_tp=opp_tp,
                opposite_sl=opp_sl,
                source_engine="kimi",
                source_pick_id=pick_id,
                picked_at=ts,
                expiration_at=expiration_from(ts),
                confidence=float(p.get("confidence", 0)) / 100 if float(p.get("confidence", 0)) > 1 else float(p.get("confidence", 0)),
            ))
        except Exception as exc:
            log.warning("KIMI adapter skip: %s", exc)
    return picks


# ── Alpha Engine ────────────────────────────────────────────────────

def _adapt_alpha() -> List[NormalizedPick]:
    """Flip picks from alpha_engine/data/active_picks.json.

    Fields: id, symbol (BTC-USD), direction (LONG/SHORT), entry_price,
            take_profit, stop_loss, confidence, timestamp, strategy
    """
    data = _read_json(ENGINE_SOURCES["alpha"])
    if not isinstance(data, list):
        return []

    picks = []
    for p in data:
        try:
            sym = normalize_symbol(p.get("symbol", ""))
            if sym in EXCLUDED_SYMBOLS:
                continue
            orig_dir = p.get("direction", "").upper()
            if not orig_dir or orig_dir not in ("LONG", "SHORT"):
                continue

            entry = float(p["entry_price"])
            tp = float(p.get("take_profit") or 0)
            sl = float(p.get("stop_loss") or 0)
            if tp == 0 or sl == 0:
                tp, sl = default_tp_sl(entry, orig_dir)

            opp_dir = flip_direction(orig_dir)
            opp_tp, opp_sl = flip_tp_sl(entry, tp, sl, orig_dir)
            ts = p.get("timestamp", utc_now())
            # Use the source ID if available, else generate
            source_id = p.get("id", make_pick_id("alpha", sym, opp_dir, ts))
            pick_id = f"opp::alpha::{source_id}"

            picks.append(NormalizedPick(
                symbol=sym,
                original_direction=orig_dir,
                opposite_direction=opp_dir,
                entry_price=entry,
                original_tp=tp,
                original_sl=sl,
                opposite_tp=opp_tp,
                opposite_sl=opp_sl,
                source_engine="alpha",
                source_pick_id=pick_id,
                picked_at=ts,
                expiration_at=expiration_from(ts),
                confidence=float(p.get("confidence", 0)),
            ))
        except Exception as exc:
            log.warning("Alpha adapter skip: %s", exc)
    return picks


# ── Signal Engine ───────────────────────────────────────────────────

def _adapt_signal_engine() -> List[NormalizedPick]:
    """Flip picks from crypto_signal_engine/data/active_picks.json.

    Fields: symbol (BTCUSDT), signal (LONG/SHORT), entry, tp, sl,
            confidence, timestamp
    """
    data = _read_json(ENGINE_SOURCES["signal_engine"])
    if not isinstance(data, list):
        return []

    picks = []
    for p in data:
        try:
            sym = normalize_symbol(p.get("symbol", ""))
            if sym in EXCLUDED_SYMBOLS:
                continue
            orig_dir = p.get("signal", "").upper()
            if orig_dir == "BUY":
                orig_dir = "LONG"
            elif orig_dir == "SELL":
                orig_dir = "SHORT"
            if orig_dir not in ("LONG", "SHORT"):
                continue

            entry = float(p.get("entry", 0))
            if entry <= 0:
                continue
            tp = float(p.get("tp") or 0)
            sl = float(p.get("sl") or 0)
            if tp == 0 or sl == 0:
                tp, sl = default_tp_sl(entry, orig_dir)

            opp_dir = flip_direction(orig_dir)
            opp_tp, opp_sl = flip_tp_sl(entry, tp, sl, orig_dir)
            ts = p.get("timestamp", utc_now())
            pick_id = make_pick_id("signal_engine", sym, opp_dir, ts)

            picks.append(NormalizedPick(
                symbol=sym,
                original_direction=orig_dir,
                opposite_direction=opp_dir,
                entry_price=entry,
                original_tp=tp,
                original_sl=sl,
                opposite_tp=opp_tp,
                opposite_sl=opp_sl,
                source_engine="signal_engine",
                source_pick_id=pick_id,
                picked_at=ts,
                expiration_at=expiration_from(ts),
                confidence=float(p.get("confidence", 0)),
            ))
        except Exception as exc:
            log.warning("Signal Engine adapter skip: %s", exc)
    return picks


# ── Cross-Aggregator ────────────────────────────────────────────────

def _adapt_cross_aggregator() -> List[NormalizedPick]:
    """Flip picks from cross_aggregation/data/super_signals.json.

    Top-level: {super_signals: [{symbol (BTCUSDT), direction (LONG/SHORT),
                entry_price, take_profit, stop_loss, confidence,
                agreeing_systems, agreement_count, signal_tier}]}
    """
    raw = _read_json(ENGINE_SOURCES["cross_aggregator"])
    if isinstance(raw, dict):
        data = raw.get("super_signals", [])
    else:
        data = raw

    picks = []
    for p in data:
        try:
            sym = normalize_symbol(p.get("symbol", ""))
            if sym in EXCLUDED_SYMBOLS:
                continue
            orig_dir = p.get("direction", "").upper()
            if orig_dir not in ("LONG", "SHORT"):
                continue

            entry = float(p["entry_price"])
            tp = float(p.get("take_profit") or 0)
            sl = float(p.get("stop_loss") or 0)
            if tp == 0 or sl == 0:
                tp, sl = default_tp_sl(entry, orig_dir)

            opp_dir = flip_direction(orig_dir)
            opp_tp, opp_sl = flip_tp_sl(entry, tp, sl, orig_dir)
            ts = utc_now()  # super_signals don't have per-pick timestamps
            pick_id = make_pick_id("cross_aggregator", sym, opp_dir, ts)

            picks.append(NormalizedPick(
                symbol=sym,
                original_direction=orig_dir,
                opposite_direction=opp_dir,
                entry_price=entry,
                original_tp=tp,
                original_sl=sl,
                opposite_tp=opp_tp,
                opposite_sl=opp_sl,
                source_engine="cross_aggregator",
                source_pick_id=pick_id,
                picked_at=ts,
                expiration_at=expiration_from(ts),
                confidence=float(p.get("confidence", 0)),
            ))
        except Exception as exc:
            log.warning("Cross-Aggregator adapter skip: %s", exc)
    return picks


# ── Public API ──────────────────────────────────────────────────────

ADAPTERS = {
    "predictions": _adapt_predictions,
    "kimi": _adapt_kimi,
    "alpha": _adapt_alpha,
    "signal_engine": _adapt_signal_engine,
    "cross_aggregator": _adapt_cross_aggregator,
}


def fetch_all_opposite_picks() -> List[NormalizedPick]:
    """Run all adapters and return combined opposite picks."""
    all_picks = []
    for name, adapter_fn in ADAPTERS.items():
        try:
            picks = adapter_fn()
            log.info("  %s: %d opposite picks", name, len(picks))
            all_picks.extend(picks)
        except Exception as exc:
            log.error("Adapter %s failed entirely: %s", name, exc)
    return all_picks
```

**Step 2: Commit**

```bash
git add sandbox/engine_adapters.py
git commit -m "feat(sandbox): add engine adapters for 5 signal sources"
```

---

### Task 5: SQLite Tracker

**Files:**
- Create: `sandbox/tracker.py`

**Step 1: Write `sandbox/tracker.py`**

```python
"""SQLite-backed tracker for opposite picks and timeline snapshots."""

import sqlite3
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple

from sandbox.config import DB_PATH, CHECKPOINTS
from sandbox.core import NormalizedPick, utc_now
from sandbox.pnl import compute_pnl_pct, check_tp_sl

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS opposite_picks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    source_engine TEXT NOT NULL,
    pick_id TEXT UNIQUE NOT NULL,
    original_direction TEXT NOT NULL,
    opposite_direction TEXT NOT NULL,
    entry_price REAL NOT NULL,
    original_tp REAL,
    original_sl REAL,
    opposite_tp REAL,
    opposite_sl REAL,
    picked_at TEXT NOT NULL,
    expiration_at TEXT NOT NULL,
    status TEXT DEFAULT 'ACTIVE',
    closed_at TEXT,
    close_price REAL,
    pnl_pct REAL,
    original_pnl_pct REAL,
    confidence REAL DEFAULT 0.0,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_active_picks ON opposite_picks (status, picked_at);
CREATE INDEX IF NOT EXISTS idx_engine_status ON opposite_picks (source_engine, status);

CREATE TABLE IF NOT EXISTS timeline_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pick_id TEXT NOT NULL,
    checkpoint TEXT NOT NULL,
    snapshot_at TEXT NOT NULL,
    price_at_snapshot REAL NOT NULL,
    pnl_pct_at_snapshot REAL NOT NULL,
    original_pnl_pct REAL NOT NULL,
    original_status TEXT DEFAULT 'ACTIVE',
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE(pick_id, checkpoint)
);

CREATE INDEX IF NOT EXISTS idx_snapshot_pick ON timeline_snapshots (pick_id, checkpoint);
"""


class Tracker:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self):
        self.conn.close()

    # ── Insert new picks ────────────────────────────────────────────

    def insert_picks(self, picks: List[NormalizedPick]) -> int:
        """Insert new opposite picks, skipping duplicates. Returns count inserted."""
        inserted = 0
        for p in picks:
            try:
                self.conn.execute(
                    """INSERT OR IGNORE INTO opposite_picks
                       (symbol, source_engine, pick_id, original_direction,
                        opposite_direction, entry_price, original_tp, original_sl,
                        opposite_tp, opposite_sl, picked_at, expiration_at, confidence)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (p.symbol, p.source_engine, p.source_pick_id,
                     p.original_direction, p.opposite_direction,
                     p.entry_price, p.original_tp, p.original_sl,
                     p.opposite_tp, p.opposite_sl,
                     p.picked_at, p.expiration_at, p.confidence),
                )
                if self.conn.total_changes:
                    inserted += 1
            except sqlite3.IntegrityError:
                pass  # Duplicate pick_id — skip
        self.conn.commit()
        return inserted

    # ── Get active picks ────────────────────────────────────────────

    def get_active_picks(self) -> List[dict]:
        rows = self.conn.execute(
            "SELECT * FROM opposite_picks WHERE status = 'ACTIVE'"
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Timeline snapshots ──────────────────────────────────────────

    def get_due_snapshots(self, now: datetime) -> List[Tuple[dict, str]]:
        """Return (pick, checkpoint_name) pairs that are due but not yet recorded."""
        active = self.get_active_picks()
        due = []
        for pick in active:
            picked_dt = datetime.fromisoformat(pick["picked_at"].replace("Z", "+00:00"))
            age_seconds = (now - picked_dt).total_seconds()
            for cp_name, cp_seconds in CHECKPOINTS.items():
                if age_seconds >= cp_seconds:
                    # Check if already recorded
                    exists = self.conn.execute(
                        "SELECT 1 FROM timeline_snapshots WHERE pick_id=? AND checkpoint=?",
                        (pick["pick_id"], cp_name),
                    ).fetchone()
                    if not exists:
                        due.append((pick, cp_name))
        return due

    def insert_snapshot(self, pick_id: str, checkpoint: str,
                        price: float, pnl_pct: float,
                        orig_pnl_pct: float, orig_status: str = "ACTIVE"):
        try:
            self.conn.execute(
                """INSERT OR IGNORE INTO timeline_snapshots
                   (pick_id, checkpoint, snapshot_at, price_at_snapshot,
                    pnl_pct_at_snapshot, original_pnl_pct, original_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (pick_id, checkpoint, utc_now(), price, pnl_pct, orig_pnl_pct, orig_status),
            )
            self.conn.commit()
        except Exception as exc:
            log.error("Snapshot insert failed for %s/%s: %s", pick_id, checkpoint, exc)

    # ── Close picks ─────────────────────────────────────────────────

    def close_pick(self, pick_id: str, status: str, close_price: float,
                   pnl_pct: float, original_pnl_pct: float):
        self.conn.execute(
            """UPDATE opposite_picks
               SET status=?, closed_at=?, close_price=?, pnl_pct=?, original_pnl_pct=?
               WHERE pick_id=?""",
            (status, utc_now(), close_price, pnl_pct, original_pnl_pct, pick_id),
        )
        self.conn.commit()

    def get_expired_picks(self, now: datetime) -> List[dict]:
        """Picks past expiration that are still ACTIVE."""
        now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        rows = self.conn.execute(
            "SELECT * FROM opposite_picks WHERE status='ACTIVE' AND expiration_at <= ?",
            (now_str,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Stats queries ───────────────────────────────────────────────

    def get_engine_stats(self, engine: str = None) -> dict:
        """Compute win/loss/WR/PF for an engine (or all if None)."""
        where = "WHERE status IN ('TP_HIT', 'SL_HIT', 'EXPIRED')"
        params = ()
        if engine:
            where += " AND source_engine = ?"
            params = (engine,)

        rows = self.conn.execute(
            f"SELECT status, pnl_pct FROM opposite_picks {where}", params
        ).fetchall()

        wins = sum(1 for r in rows if r["status"] == "TP_HIT")
        losses = sum(1 for r in rows if r["status"] == "SL_HIT")
        expired_win = sum(1 for r in rows if r["status"] == "EXPIRED" and (r["pnl_pct"] or 0) > 0)
        expired_loss = sum(1 for r in rows if r["status"] == "EXPIRED" and (r["pnl_pct"] or 0) <= 0)
        total_w = wins + expired_win
        total_l = losses + expired_loss
        total = total_w + total_l
        wr = (total_w / total * 100) if total else 0
        win_pnl = sum(r["pnl_pct"] for r in rows if (r["pnl_pct"] or 0) > 0)
        loss_pnl = sum(abs(r["pnl_pct"]) for r in rows if (r["pnl_pct"] or 0) < 0)
        pf = (win_pnl / loss_pnl) if loss_pnl else float("inf")

        return {
            "wins": total_w, "losses": total_l, "total": total,
            "win_rate": round(wr, 1),
            "profit_factor": round(pf, 2) if pf != float("inf") else "∞",
        }

    def get_timeline_avg(self, engine: str = None) -> Dict[str, Dict[str, float]]:
        """Average PnL at each checkpoint, comparing opposite vs original."""
        where = ""
        params = ()
        if engine:
            where = """JOIN opposite_picks p ON t.pick_id = p.pick_id
                       WHERE p.source_engine = ?"""
            params = (engine,)

        rows = self.conn.execute(
            f"""SELECT t.checkpoint,
                       AVG(t.pnl_pct_at_snapshot) as avg_opp,
                       AVG(t.original_pnl_pct) as avg_orig,
                       COUNT(*) as n
                FROM timeline_snapshots t {where}
                GROUP BY t.checkpoint""",
            params,
        ).fetchall()

        result = {}
        for r in rows:
            result[r["checkpoint"]] = {
                "avg_opposite_pnl": round(r["avg_opp"], 4),
                "avg_original_pnl": round(r["avg_orig"], 4),
                "count": r["n"],
            }
        return result

    def get_best_window(self, engine: str = None) -> str:
        """Return the checkpoint with the highest avg opposite PnL."""
        avgs = self.get_timeline_avg(engine)
        if not avgs:
            return "N/A"
        best = max(avgs.items(), key=lambda x: x[1]["avg_opposite_pnl"])
        return best[0]

    def get_recently_opened(self, since_minutes: int = 35) -> List[dict]:
        """Picks opened in the last N minutes (for Discord new-pick alerts)."""
        cutoff = datetime.now(timezone.utc)
        from datetime import timedelta
        cutoff = (cutoff - timedelta(minutes=since_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows = self.conn.execute(
            "SELECT * FROM opposite_picks WHERE created_at >= ?", (cutoff,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_recently_closed(self, since_minutes: int = 35) -> List[dict]:
        """Picks closed in the last N minutes."""
        cutoff = datetime.now(timezone.utc)
        from datetime import timedelta
        cutoff = (cutoff - timedelta(minutes=since_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows = self.conn.execute(
            "SELECT * FROM opposite_picks WHERE closed_at >= ? AND status != 'ACTIVE'",
            (cutoff,),
        ).fetchall()
        return [dict(r) for r in rows]
```

**Step 2: Commit**

```bash
git add sandbox/tracker.py
git commit -m "feat(sandbox): add SQLite tracker with timeline snapshots"
```

---

### Task 6: Price Fetcher

**Files:**
- Create: `sandbox/prices.py`

**Step 1: Write `sandbox/prices.py`**

```python
"""Fetch current prices from Binance (primary) and CoinGecko (fallback)."""

import logging
from typing import Dict, List

import requests

from sandbox.config import BINANCE_TICKER_URL, COINGECKO_URL

log = logging.getLogger(__name__)

# CoinGecko ID mapping for non-Binance symbols
_CG_MAP = {
    "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "BNBUSDT": "binancecoin",
    "SOLUSDT": "solana", "XRPUSDT": "ripple", "DOGEUSDT": "dogecoin",
    "ADAUSDT": "cardano", "AVAXUSDT": "avalanche-2", "DOTUSDT": "polkadot",
    "LINKUSDT": "chainlink", "NEARUSDT": "near", "SHIBUSDT": "shiba-inu",
    "TRXUSDT": "tron", "MATICUSDT": "matic-network",
}


def fetch_prices_binance(symbols: List[str]) -> Dict[str, float]:
    """Fetch all Binance USDT ticker prices in one request."""
    try:
        resp = requests.get(BINANCE_TICKER_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        price_map = {item["symbol"]: float(item["price"]) for item in data}
        return {s: price_map[s] for s in symbols if s in price_map}
    except Exception as exc:
        log.error("Binance price fetch failed: %s", exc)
        return {}


def fetch_prices_coingecko(symbols: List[str]) -> Dict[str, float]:
    """Fallback: CoinGecko for symbols missing from Binance."""
    ids_to_sym = {}
    for s in symbols:
        cg_id = _CG_MAP.get(s)
        if cg_id:
            ids_to_sym[cg_id] = s
    if not ids_to_sym:
        return {}
    try:
        resp = requests.get(COINGECKO_URL, params={
            "ids": ",".join(ids_to_sym.keys()),
            "vs_currencies": "usd",
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        result = {}
        for cg_id, sym in ids_to_sym.items():
            if cg_id in data and "usd" in data[cg_id]:
                result[sym] = float(data[cg_id]["usd"])
        return result
    except Exception as exc:
        log.error("CoinGecko price fetch failed: %s", exc)
        return {}


def fetch_prices(symbols: List[str]) -> Dict[str, float]:
    """Fetch prices using Binance first, CoinGecko fallback for missing."""
    prices = fetch_prices_binance(symbols)
    missing = [s for s in symbols if s not in prices]
    if missing:
        prices.update(fetch_prices_coingecko(missing))
    return prices
```

**Step 2: Commit**

```bash
git add sandbox/prices.py
git commit -m "feat(sandbox): add price fetcher (Binance primary, CoinGecko fallback)"
```

---

### Task 7: Discord Notifications

**Files:**
- Create: `sandbox/discord_notify.py`

**Step 1: Write `sandbox/discord_notify.py`**

```python
"""Discord embed builder and webhook sender for Opposite Day."""

import json
import logging
import os
import time
from typing import Dict, List, Optional

import requests

from sandbox.config import (
    WEBHOOK_ENV_VAR, EMBED_CHAR_LIMIT, MAX_PICKS_PER_EMBED,
    DISCORD_RATE_LIMIT_RETRY, DISCORD_RETRY_DELAY,
    CHECKPOINTS,
)

log = logging.getLogger(__name__)

ENGINE_NAMES = {
    "predictions": "Predictions Dashboard",
    "kimi": "KIMI Rise of the Claw",
    "alpha": "Alpha Engine",
    "signal_engine": "Signal Engine",
    "cross_aggregator": "Cross-Aggregator",
}

ENGINE_COLORS = {
    "predictions": 0x3498DB,   # blue
    "kimi": 0xE74C3C,         # red
    "alpha": 0x2ECC71,        # green
    "signal_engine": 0xF39C12, # orange
    "cross_aggregator": 0x9B59B6,  # purple
}


def _post_webhook(embeds: list, webhook_url: str) -> bool:
    """Post embeds to Discord with retry on rate-limit."""
    for attempt in range(DISCORD_RATE_LIMIT_RETRY):
        try:
            resp = requests.post(webhook_url, json={"embeds": embeds[:10]}, timeout=10)
            if resp.status_code == 204:
                return True
            if resp.status_code == 429:
                retry_after = resp.json().get("retry_after", DISCORD_RETRY_DELAY)
                log.warning("Rate limited, retrying in %.1fs", retry_after)
                time.sleep(retry_after)
                continue
            log.error("Discord error %d: %s", resp.status_code, resp.text[:200])
            return False
        except Exception as exc:
            log.error("Discord post failed: %s", exc)
            return False
    return False


def _fmt_price(price: float) -> str:
    if price >= 1000:
        return f"${price:,.2f}"
    if price >= 1:
        return f"${price:.4f}"
    return f"${price:.6f}"


def _pnl_emoji(pnl: float) -> str:
    return "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"


def build_engine_embed(
    engine: str,
    stats: dict,
    timeline_avg: Dict[str, dict],
    new_picks: List[dict],
    closed_picks: List[dict],
) -> dict:
    """Build a Discord embed for one engine portfolio."""
    name = ENGINE_NAMES.get(engine, engine)
    color = ENGINE_COLORS.get(engine, 0x95A5A6)

    fields = []

    # Scorecard
    wr = stats.get("win_rate", 0)
    pf = stats.get("profit_factor", "∞")
    fields.append({
        "name": "📊 Scorecard",
        "value": f"**{stats['wins']}W / {stats['losses']}L** ({wr}% WR) | PF: {pf}",
        "inline": False,
    })

    # New picks
    if new_picks:
        lines = []
        for p in new_picks[:MAX_PICKS_PER_EMBED]:
            lines.append(
                f"**{p['opposite_direction']}** {p['symbol']} @ {_fmt_price(p['entry_price'])} "
                f"(flipped from {p['original_direction']})\n"
                f"TP: {_fmt_price(p['opposite_tp'])} | SL: {_fmt_price(p['opposite_sl'])}"
            )
        if len(new_picks) > MAX_PICKS_PER_EMBED:
            lines.append(f"*+ {len(new_picks) - MAX_PICKS_PER_EMBED} more*")
        fields.append({
            "name": "🆕 New Opposite Picks",
            "value": "\n".join(lines),
            "inline": False,
        })

    # Timeline performance
    if timeline_avg:
        cp_order = ["1h", "4h", "12h", "24h"]
        lines = []
        for cp in cp_order:
            if cp in timeline_avg:
                avg = timeline_avg[cp]
                opp = avg["avg_opposite_pnl"]
                orig = avg["avg_original_pnl"]
                lines.append(
                    f"`{cp:>3}:` {opp:+.2f}% {_pnl_emoji(opp)}  (original: {orig:+.2f}%)"
                )
        if lines:
            fields.append({
                "name": "📈 Timeline Performance (avg PnL)",
                "value": "\n".join(lines),
                "inline": False,
            })

    # Closed picks
    if closed_picks:
        lines = []
        for p in closed_picks[:MAX_PICKS_PER_EMBED]:
            emoji = "✅" if p["status"] == "TP_HIT" else "❌" if p["status"] == "SL_HIT" else "⏰"
            pnl = p.get("pnl_pct", 0) or 0
            lines.append(
                f"{emoji} {p['symbol']} {p['opposite_direction']} → "
                f"{p['status']} {pnl:+.2f}%"
            )
        if len(closed_picks) > MAX_PICKS_PER_EMBED:
            lines.append(f"*+ {len(closed_picks) - MAX_PICKS_PER_EMBED} more*")
        fields.append({
            "name": "📋 Recently Closed",
            "value": "\n".join(lines),
            "inline": False,
        })

    return {
        "title": f"🔄 Opposite Day — {name}",
        "color": color,
        "fields": fields,
        "footer": {"text": "Paper Trading | Not financial advice — DYOR!"},
    }


def build_summary_embed(all_stats: Dict[str, dict], all_timelines: Dict[str, dict]) -> dict:
    """Build the all-portfolios summary embed."""
    lines = ["```"]
    lines.append(f"{'Engine':<17} | {'WR':>5} | {'PF':>5} | Best Window")
    lines.append("-" * 50)
    total_w, total_l = 0, 0
    for eng in ["predictions", "kimi", "alpha", "signal_engine", "cross_aggregator"]:
        s = all_stats.get(eng, {})
        name = ENGINE_NAMES.get(eng, eng)[:15]
        wr = s.get("win_rate", 0)
        pf = s.get("profit_factor", "∞")
        best = "N/A"
        if eng in all_timelines and all_timelines[eng]:
            tl = all_timelines[eng]
            best_cp = max(tl.items(), key=lambda x: x[1].get("avg_opposite_pnl", -999))
            best = best_cp[0]
        lines.append(f"{name:<17} | {wr:>4.1f}% | {str(pf):>5} | {best}")
        total_w += s.get("wins", 0)
        total_l += s.get("losses", 0)
    lines.append("```")

    total = total_w + total_l
    overall_wr = (total_w / total * 100) if total else 0

    return {
        "title": "🏆 Opposite Day — All Portfolios Summary",
        "description": "\n".join(lines),
        "color": 0xF1C40F,
        "fields": [{
            "name": "📊 Totals",
            "value": f"**{total} picks** | {total_w}W / {total_l}L | Overall WR: {overall_wr:.1f}%",
            "inline": False,
        }],
        "footer": {"text": "Paper Trading | Not financial advice — DYOR!"},
    }


def send_notifications(tracker) -> bool:
    """Build and send all Discord embeds for this run."""
    webhook_url = os.getenv(WEBHOOK_ENV_VAR, "")
    if not webhook_url:
        log.warning("No %s env var set — skipping Discord", WEBHOOK_ENV_VAR)
        return False

    engines = ["predictions", "kimi", "alpha", "signal_engine", "cross_aggregator"]
    all_stats = {}
    all_timelines = {}
    embeds = []

    new_picks = tracker.get_recently_opened()
    closed_picks = tracker.get_recently_closed()

    for eng in engines:
        stats = tracker.get_engine_stats(eng)
        timeline = tracker.get_timeline_avg(eng)
        all_stats[eng] = stats
        all_timelines[eng] = timeline

        eng_new = [p for p in new_picks if p["source_engine"] == eng]
        eng_closed = [p for p in closed_picks if p["source_engine"] == eng]

        # Only post if there's activity or stats exist
        if eng_new or eng_closed or stats.get("total", 0) > 0:
            embeds.append(build_engine_embed(eng, stats, timeline, eng_new, eng_closed))

    # Summary embed
    embeds.append(build_summary_embed(all_stats, all_timelines))

    # Discord allows max 10 embeds per message
    success = True
    for i in range(0, len(embeds), 10):
        batch = embeds[i : i + 10]
        if not _post_webhook(batch, webhook_url):
            success = False

    return success
```

**Step 2: Commit**

```bash
git add sandbox/discord_notify.py
git commit -m "feat(sandbox): add Discord notification with per-engine embeds and summary"
```

---

### Task 8: Run Orchestrator

**Files:**
- Create: `sandbox/run.py`

**Step 1: Write `sandbox/run.py`**

```python
"""CLI orchestrator for the Opposite Day sandbox.

Usage:
    python -m sandbox.run --scan --snapshot --close --notify
    python -m sandbox.run --scan --snapshot --close --notify --dry-run
    python -m sandbox.run --scan   # just scan for new picks
"""

import argparse
import logging
import sys
from datetime import datetime, timezone

from sandbox.engine_adapters import fetch_all_opposite_picks
from sandbox.tracker import Tracker
from sandbox.prices import fetch_prices
from sandbox.pnl import compute_pnl_pct, check_tp_sl
from sandbox.discord_notify import send_notifications

log = logging.getLogger("sandbox")


def phase_scan(tracker: Tracker):
    """Phase 1: Read all engines, create opposite picks for new signals."""
    log.info("=== PHASE 1: SCAN ===")
    picks = fetch_all_opposite_picks()
    log.info("Total opposite picks from adapters: %d", len(picks))
    inserted = tracker.insert_picks(picks)
    log.info("New picks inserted: %d", inserted)
    active = tracker.get_active_picks()
    log.info("Total active opposite picks: %d", len(active))


def phase_snapshot(tracker: Tracker):
    """Phase 2: Record timeline snapshots at 1h/4h/12h/24h checkpoints."""
    log.info("=== PHASE 2: SNAPSHOT ===")
    now = datetime.now(timezone.utc)
    due = tracker.get_due_snapshots(now)
    if not due:
        log.info("No snapshots due this run.")
        return

    # Collect all symbols we need prices for
    symbols = list({pick["symbol"] for pick, _ in due})
    prices = fetch_prices(symbols)
    log.info("Fetched prices for %d/%d symbols", len(prices), len(symbols))

    recorded = 0
    for pick, checkpoint in due:
        sym = pick["symbol"]
        price = prices.get(sym)
        if price is None:
            log.warning("No price for %s — skipping snapshot", sym)
            continue

        opp_pnl = compute_pnl_pct(pick["entry_price"], price, pick["opposite_direction"])
        orig_pnl = compute_pnl_pct(pick["entry_price"], price, pick["original_direction"])
        orig_status = check_tp_sl(
            pick["entry_price"], price,
            pick["original_tp"], pick["original_sl"],
            pick["original_direction"],
        )

        tracker.insert_snapshot(
            pick["pick_id"], checkpoint, price,
            opp_pnl, orig_pnl, orig_status,
        )
        recorded += 1

    log.info("Recorded %d timeline snapshots", recorded)


def phase_close(tracker: Tracker):
    """Phase 3: Close picks that hit TP/SL or expired."""
    log.info("=== PHASE 3: CLOSE ===")
    now = datetime.now(timezone.utc)
    active = tracker.get_active_picks()
    if not active:
        log.info("No active picks to close-check.")
        return

    symbols = list({p["symbol"] for p in active})
    prices = fetch_prices(symbols)

    closed_count = 0
    for pick in active:
        sym = pick["symbol"]
        price = prices.get(sym)
        if price is None:
            continue

        opp_pnl = compute_pnl_pct(pick["entry_price"], price, pick["opposite_direction"])
        orig_pnl = compute_pnl_pct(pick["entry_price"], price, pick["original_direction"])

        status = check_tp_sl(
            pick["entry_price"], price,
            pick["opposite_tp"], pick["opposite_sl"],
            pick["opposite_direction"],
        )

        if status != "ACTIVE":
            tracker.close_pick(pick["pick_id"], status, price, opp_pnl, orig_pnl)
            closed_count += 1
            log.info("  Closed %s %s %s → %s (%.2f%%)",
                     pick["source_engine"], pick["symbol"],
                     pick["opposite_direction"], status, opp_pnl)

    # Expire old picks
    expired = tracker.get_expired_picks(now)
    for pick in expired:
        price = prices.get(pick["symbol"])
        if price:
            opp_pnl = compute_pnl_pct(pick["entry_price"], price, pick["opposite_direction"])
            orig_pnl = compute_pnl_pct(pick["entry_price"], price, pick["original_direction"])
        else:
            opp_pnl = 0.0
            orig_pnl = 0.0
        tracker.close_pick(pick["pick_id"], "EXPIRED", price or 0, opp_pnl, orig_pnl)
        closed_count += 1
        log.info("  Expired %s %s", pick["source_engine"], pick["symbol"])

    log.info("Closed %d picks this run", closed_count)


def phase_notify(tracker: Tracker, dry_run: bool = False):
    """Phase 4: Post Discord embeds."""
    log.info("=== PHASE 4: NOTIFY ===")
    if dry_run:
        log.info("Dry-run mode — skipping Discord post")
        return
    ok = send_notifications(tracker)
    log.info("Discord notification %s", "sent" if ok else "FAILED")


def main():
    parser = argparse.ArgumentParser(description="Opposite Day Paper-Trade System")
    parser.add_argument("--scan", action="store_true", help="Scan engines for new picks")
    parser.add_argument("--snapshot", action="store_true", help="Record timeline snapshots")
    parser.add_argument("--close", action="store_true", help="Close TP/SL/expired picks")
    parser.add_argument("--notify", action="store_true", help="Send Discord notifications")
    parser.add_argument("--dry-run", action="store_true", help="Skip Discord posting")
    parser.add_argument("--all", action="store_true", help="Run all phases")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )

    if args.all:
        args.scan = args.snapshot = args.close = args.notify = True

    if not any([args.scan, args.snapshot, args.close, args.notify]):
        log.error("No phases selected. Use --all or --scan --snapshot --close --notify")
        sys.exit(1)

    tracker = Tracker()
    try:
        if args.scan:
            phase_scan(tracker)
        if args.snapshot:
            phase_snapshot(tracker)
        if args.close:
            phase_close(tracker)
        if args.notify:
            phase_notify(tracker, dry_run=args.dry_run)
    finally:
        tracker.close()

    log.info("=== Opposite Day run complete ===")


if __name__ == "__main__":
    main()
```

**Step 2: Add `sandbox/__main__.py` for `python -m sandbox` support**

```python
"""Allow running as: python -m sandbox --all"""
from sandbox.run import main
main()
```

**Step 3: Commit**

```bash
git add sandbox/run.py sandbox/__main__.py
git commit -m "feat(sandbox): add run orchestrator with 4-phase pipeline"
```

---

### Task 9: GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/opposite-day.yml`

**Step 1: Write workflow**

```yaml
name: Opposite Day Paper-Trade

on:
  schedule:
    - cron: '*/30 * * * *'  # Every 30 minutes
  workflow_dispatch:         # Manual trigger

permissions:
  contents: write

jobs:
  opposite-day:
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install requests

      - name: Run Opposite Day pipeline
        env:
          DISCORD_PAPER_TRADE_WEBHOOK: ${{ secrets.DISCORD_PAPER_TRADE_WEBHOOK }}
        run: python -m sandbox --all

      - name: Commit & push DB changes
        run: |
          git config user.name "Opposite Day Bot"
          git config user.email "bot@opposite-day.local"
          git add sandbox/data/opposite_day.db
          git diff --cached --quiet || git commit -m "📊 Opposite Day run [$(date -u '+%Y-%m-%d %H:%M UTC')]"
          git pull --rebase origin main || true
          git push origin main
```

**Step 2: Commit**

```bash
git add .github/workflows/opposite-day.yml
git commit -m "ci: add Opposite Day GitHub Actions workflow (every 30 min)"
```

---

### Task 10: Local Smoke Test

**Step 1: Run scan phase locally to verify adapters work**

```bash
cd E:/findtorontoevents_antigravity.ca
python -m sandbox --scan --dry-run
```

Expected: Should print adapter counts and insert picks into SQLite.

**Step 2: Run full pipeline in dry-run mode**

```bash
python -m sandbox --all --dry-run
```

Expected: All 4 phases run, snapshots may be empty (picks just created), no Discord post.

**Step 3: Verify DB was created**

```bash
python -c "import sqlite3; c=sqlite3.connect('sandbox/data/opposite_day.db'); print(c.execute('SELECT COUNT(*) FROM opposite_picks').fetchone())"
```

Expected: Non-zero count.

**Step 4: Commit DB**

```bash
git add sandbox/data/opposite_day.db
git commit -m "feat(sandbox): initial opposite day DB with first scan"
```

---

### Task 11: Push and Verify Workflow

**Step 1: Push all changes**

```bash
git push origin main
```

**Step 2: Verify workflow appears in GitHub Actions**

```bash
gh workflow list | grep -i opposite
```

**Step 3: Manually trigger first run**

```bash
gh workflow run opposite-day.yml
gh run watch
```

**Step 4: Verify Discord message appeared in #paper-trade channel**

Check the Discord channel for the embed messages.

---

### Task 12: Add Updates Page Entry

**Step 1: Add entry to `updates/index.html`**

Find the insertion point (after the latest section-year div) and add a new update entry documenting the Opposite Day system launch, including:
- What it does (flips picks from 5 engines)
- Where to see picks (Discord #paper-trade channel)
- Timeline tracking (1h/4h/12h/24h performance)
- Links to the design doc

**Step 2: Commit and push**

```bash
git add updates/index.html
git commit -m "docs: add Opposite Day paper-trade system to updates page"
git push origin main
```
