# Central Audit Trail Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a centralized SQLite audit trail that captures every raw pick, consensus decision, filtering reason, and outcome from the cross-system aggregator pipeline.

**Architecture:** A self-contained `audit_trail/` Python package imported by `cross_aggregation/aggregator.py` and `cross_aggregation/discord_notify.py`. The package manages a single SQLite DB at `data/audit_trail.db` with UUID primary keys, dedup hashing, JSON-Schema validation, and a MySQL-forward schema design. ~10 lines of instrumentation per consumer file.

**Tech Stack:** Python 3.11+, sqlite3 (stdlib), hashlib, uuid, json, jsonschema (optional, fallback to manual validation)

**Design doc:** `docs/plans/2026-03-04-central-audit-trail-design.md`

---

## Task 1: Create the Schema SQL and DB Module

**Files:**
- Create: `audit_trail/__init__.py`
- Create: `audit_trail/schema.sql`
- Create: `audit_trail/db.py`

**Step 1: Create the directory**

```bash
mkdir -p audit_trail
```

**Step 2: Write the schema DDL**

Create `audit_trail/schema.sql`:

```sql
-- Central Audit Trail Schema
-- version: 1.0
-- Engine: SQLite (designed for MySQL migration)

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', '1.0');

CREATE TABLE IF NOT EXISTS aggregation_runs (
    run_id              TEXT PRIMARY KEY,  -- UUID
    started_at          TEXT NOT NULL,     -- ISO 8601 UTC
    finished_at         TEXT,
    status              TEXT NOT NULL DEFAULT 'RUNNING',  -- RUNNING/COMPLETED/FAILED
    systems_loaded      INTEGER DEFAULT 0,
    raw_picks_count     INTEGER DEFAULT 0,
    consensus_count     INTEGER DEFAULT 0,
    regime_data         TEXT,              -- JSON
    portfolio_drawdown  REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS raw_picks (
    id                  TEXT PRIMARY KEY,  -- UUID
    aggregation_run_id  TEXT NOT NULL REFERENCES aggregation_runs(run_id),
    source_system       TEXT NOT NULL,
    symbol              TEXT NOT NULL,
    asset_class         TEXT NOT NULL,     -- CRYPTO/FOREX/EQUITY
    direction           TEXT NOT NULL,     -- LONG/SHORT
    entry_price         REAL,
    take_profit         REAL,
    stop_loss           REAL,
    risk_reward         REAL,
    confidence          REAL,
    strategy            TEXT,
    raw_payload         TEXT,              -- JSON
    signal_timestamp    TEXT,
    recorded_at         TEXT NOT NULL,
    dedup_hash          TEXT UNIQUE,       -- SHA-256
    was_stale           INTEGER DEFAULT 0,
    was_banned          INTEGER DEFAULT 0,
    was_demoted         INTEGER DEFAULT 0,
    was_wr_suppressed   INTEGER DEFAULT 0,
    created_by          TEXT DEFAULT 'aggregator'
);

CREATE INDEX IF NOT EXISTS idx_raw_run    ON raw_picks(aggregation_run_id);
CREATE INDEX IF NOT EXISTS idx_raw_sys    ON raw_picks(source_system);
CREATE INDEX IF NOT EXISTS idx_raw_sym    ON raw_picks(symbol);
CREATE INDEX IF NOT EXISTS idx_raw_ts     ON raw_picks(signal_timestamp);

CREATE TABLE IF NOT EXISTS consensus_picks (
    id                  TEXT PRIMARY KEY,  -- UUID
    aggregation_run_id  TEXT NOT NULL REFERENCES aggregation_runs(run_id),
    symbol              TEXT NOT NULL,
    asset_class         TEXT NOT NULL,
    direction           TEXT NOT NULL,
    entry_price         REAL,
    take_profit         REAL,
    stop_loss           REAL,
    risk_reward         REAL,
    confidence          REAL,
    agreement_count     INTEGER,
    source_systems      TEXT,              -- JSON array
    source_strategies   TEXT,              -- JSON map
    system_confidences  TEXT,              -- JSON map
    consensus_tier      TEXT,              -- STRONG/MODERATE
    classification      TEXT,              -- ELITE/PROVEN/EXPERIMENTAL
    regime_data         TEXT,              -- JSON
    discord_channel     TEXT,
    discord_message_id  TEXT,
    status              TEXT DEFAULT 'OPEN',  -- OPEN/WON/LOST/EXPIRED/MANUAL_CLOSE
    exit_price          REAL,
    exit_reason         TEXT,              -- TP/SL/TIMEOUT/MANUAL/KILL
    pnl_pct             REAL,
    slippage_estimate   REAL,
    generated_at        TEXT NOT NULL,
    closed_at           TEXT,
    UNIQUE(symbol, direction, entry_price, generated_at)
);

CREATE INDEX IF NOT EXISTS idx_cons_run    ON consensus_picks(aggregation_run_id);
CREATE INDEX IF NOT EXISTS idx_cons_sym    ON consensus_picks(symbol);
CREATE INDEX IF NOT EXISTS idx_cons_status ON consensus_picks(status);

CREATE TABLE IF NOT EXISTS audit_events (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type          TEXT NOT NULL,
    pick_id             TEXT,              -- FK to consensus_picks (nullable)
    aggregation_run_id  TEXT,
    symbol              TEXT,
    payload             TEXT,              -- JSON
    origin              TEXT DEFAULT 'aggregator',
    timestamp           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_evt_run   ON audit_events(aggregation_run_id);
CREATE INDEX IF NOT EXISTS idx_evt_pick  ON audit_events(pick_id);
CREATE INDEX IF NOT EXISTS idx_evt_type  ON audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_evt_sym   ON audit_events(symbol);

CREATE TABLE IF NOT EXISTS filter_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    aggregation_run_id  TEXT,
    raw_pick_id         TEXT,
    symbol              TEXT,
    direction           TEXT,
    source_system       TEXT,
    filter_reason       TEXT NOT NULL,
    details             TEXT,
    timestamp           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_filt_run    ON filter_log(aggregation_run_id);
CREATE INDEX IF NOT EXISTS idx_filt_reason ON filter_log(filter_reason);
CREATE INDEX IF NOT EXISTS idx_filt_sym    ON filter_log(symbol);

CREATE TABLE IF NOT EXISTS strategy_stats (
    strategy        TEXT NOT NULL,
    source_system   TEXT NOT NULL,
    asset_class     TEXT,
    total_picks     INTEGER DEFAULT 0,
    consensus_picks INTEGER DEFAULT 0,
    wins            INTEGER DEFAULT 0,
    losses          INTEGER DEFAULT 0,
    win_rate        REAL DEFAULT 0.0,
    avg_pnl_pct     REAL DEFAULT 0.0,
    best_pnl        REAL DEFAULT 0.0,
    worst_pnl       REAL DEFAULT 0.0,
    avg_risk_reward REAL DEFAULT 0.0,
    last_updated    TEXT,
    PRIMARY KEY (strategy, source_system)
);

CREATE INDEX IF NOT EXISTS idx_stats_sys ON strategy_stats(source_system);
CREATE INDEX IF NOT EXISTS idx_stats_ac  ON strategy_stats(asset_class);
```

**Step 3: Write the DB connection module**

Create `audit_trail/db.py`:

```python
"""
SQLite connection manager for the audit trail.

Designed for easy swap to MySQL/PostgreSQL later:
- All DB-specific logic lives in this file
- Callers use get_connection() and never import sqlite3 directly
"""

import pathlib
import sqlite3
import threading

DB_PATH = pathlib.Path(__file__).resolve().parent.parent / "data" / "audit_trail.db"
SCHEMA_PATH = pathlib.Path(__file__).resolve().parent / "schema.sql"

_local = threading.local()


def get_connection() -> sqlite3.Connection:
    """Get a thread-local SQLite connection. Creates DB + schema on first call."""
    if not hasattr(_local, "conn") or _local.conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")

        # Initialize schema if needed
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema_sql)

        _local.conn = conn
    return _local.conn


def close():
    """Close the thread-local connection."""
    if hasattr(_local, "conn") and _local.conn is not None:
        _local.conn.close()
        _local.conn = None
```

**Step 4: Write the `__init__.py` stub**

Create `audit_trail/__init__.py`:

```python
"""Central Audit Trail for crypto prediction picks."""
```

**Step 5: Verify DB creation works**

Run:
```bash
cd e:/findtorontoevents_antigravity.ca && py -c "from audit_trail.db import get_connection; c = get_connection(); print('Tables:', [r[0] for r in c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()])"
```

Expected output: `Tables: ['meta', 'aggregation_runs', 'raw_picks', 'consensus_picks', 'audit_events', 'filter_log', 'strategy_stats']`

**Step 6: Commit**

```bash
git add audit_trail/__init__.py audit_trail/schema.sql audit_trail/db.py
git commit -m "feat(audit): add central audit trail schema and DB module"
```

---

## Task 2: Build the Recorder Module (Validation + Dedup + Recording)

**Files:**
- Create: `audit_trail/recorder.py`
- Modify: `audit_trail/__init__.py` (add public API exports)

**Step 1: Write `audit_trail/recorder.py`**

```python
"""
Core recording logic for the audit trail.

Handles:
- UUID generation for all entities
- SHA-256 dedup hashing
- Schema validation (required fields, price sanity, confidence range)
- Asset class derivation from symbol
- All INSERT operations
"""

import datetime as dt
import hashlib
import json
import uuid
from typing import Optional

from audit_trail.db import get_connection


# ── Asset class derivation ──

_FOREX_PREFIXES = ("EUR", "GBP", "USD", "JPY", "AUD", "CAD", "CHF", "NZD")
_CRYPTO_SUFFIXES = ("USDT", "BTC", "ETH", "BUSD", "USDC")


def derive_asset_class(symbol: str) -> str:
    """Derive asset class from normalized symbol."""
    s = symbol.upper()
    if any(s.endswith(sfx) for sfx in _CRYPTO_SUFFIXES):
        return "CRYPTO"
    if any(s.startswith(p) for p in _FOREX_PREFIXES):
        return "FOREX"
    return "EQUITY"


# ── Dedup hash ──

def compute_dedup_hash(symbol: str, direction: str, entry_price: float,
                       signal_ts: str) -> str:
    """SHA-256 hash for duplicate detection. Rounds timestamp to 5-min window."""
    try:
        ts = dt.datetime.fromisoformat(str(signal_ts).replace("Z", "+00:00"))
        epoch_rounded = int(ts.timestamp() / 300) * 300
    except (ValueError, TypeError):
        epoch_rounded = 0
    raw = f"{symbol}|{direction}|{entry_price:.8f}|{epoch_rounded}"
    return hashlib.sha256(raw.encode()).hexdigest()


# ── Validation ──

def _validate_pick(pick: dict, source_system: str) -> Optional[str]:
    """Validate a raw pick. Returns error string or None if valid."""
    symbol = pick.get("symbol", pick.get("pair", ""))
    if not symbol:
        return "missing symbol"

    direction = pick.get("direction", pick.get("signal_type",
                         pick.get("signal", "")))
    d = str(direction).upper().strip()
    if d not in ("LONG", "SHORT", "BUY", "SELL"):
        return f"invalid direction: {direction}"

    entry = pick.get("entry_price", pick.get("entryPrice",
                     pick.get("entry", pick.get("price", 0))))
    try:
        entry = float(entry)
    except (ValueError, TypeError):
        return f"invalid entry_price: {entry}"
    if entry <= 0:
        return f"entry_price must be > 0, got {entry}"

    conf = pick.get("confidence", pick.get("ml_score", 0.5))
    try:
        conf = float(conf)
    except (ValueError, TypeError):
        pass
    else:
        if not (0.0 <= conf <= 1.0):
            return f"confidence out of range: {conf}"

    # Timestamp sanity: not more than 5 min in the future
    ts = pick.get("timestamp", pick.get("generated_at", pick.get("time", "")))
    if ts:
        try:
            pick_dt = dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            future_delta = (pick_dt - dt.datetime.now(dt.timezone.utc)).total_seconds()
            if future_delta > 300:
                return f"timestamp {ts} is {future_delta/60:.0f}min in the future"
        except (ValueError, TypeError):
            pass

    return None


# ── Field extractors (handle varying source formats) ──

def _extract_price(pick: dict, *keys: str) -> Optional[float]:
    """Extract a price field from a pick dict, trying multiple key names."""
    for k in keys:
        val = pick.get(k)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                pass
    return None


def _extract_direction(pick: dict) -> Optional[str]:
    """Normalize direction from various source formats."""
    raw = pick.get("direction", pick.get("signal_type", pick.get("signal", "")))
    d = str(raw).upper().strip()
    if d in ("LONG", "BUY"):
        return "LONG"
    if d in ("SHORT", "SELL"):
        return "SHORT"
    return None


def _extract_symbol(pick: dict) -> str:
    """Extract and normalize symbol."""
    raw = str(pick.get("symbol", pick.get("pair", ""))).strip().upper()
    raw = raw.replace("-", "")
    if raw.endswith("USD") and not raw.endswith("USDT"):
        raw = raw + "T"
    return raw


def _extract_strategy(pick: dict) -> str:
    """Extract strategy name from a pick, handling different source formats."""
    strat = pick.get("strategy", pick.get("strategy_name", ""))
    if strat:
        return str(strat)
    algo = pick.get("algorithmName", pick.get("algorithm", ""))
    if algo:
        return str(algo)
    dna = pick.get("strategy_dna")
    if isinstance(dna, dict):
        return dna.get("strategy_id", dna.get("name", ""))
    if isinstance(dna, str) and dna:
        return dna
    return ""


def _now_iso() -> str:
    """Current UTC timestamp in ISO 8601."""
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


# ── Public API ──

def start_run(regime_data: dict = None, portfolio_dd: float = 0.0) -> str:
    """Start a new aggregation run. Returns run_id (UUID)."""
    run_id = str(uuid.uuid4())
    conn = get_connection()
    conn.execute(
        "INSERT INTO aggregation_runs (run_id, started_at, status, regime_data, portfolio_drawdown) "
        "VALUES (?, ?, 'RUNNING', ?, ?)",
        (run_id, _now_iso(), json.dumps(regime_data) if regime_data else None, portfolio_dd),
    )
    conn.commit()

    record_event("AGGREGATION_START", run_id=run_id,
                 payload={"regime": regime_data, "portfolio_dd": portfolio_dd})
    return run_id


def finish_run(run_id: str, consensus_count: int, systems_loaded: int = 0,
               raw_count: int = 0) -> None:
    """Mark an aggregation run as completed."""
    conn = get_connection()
    conn.execute(
        "UPDATE aggregation_runs SET finished_at=?, status='COMPLETED', "
        "consensus_count=?, systems_loaded=?, raw_picks_count=? WHERE run_id=?",
        (_now_iso(), consensus_count, systems_loaded, raw_count, run_id),
    )
    conn.commit()


def record_raw_pick(source_system: str, pick: dict, run_id: str) -> Optional[str]:
    """Record a raw pick from a source system. Returns pick_id or None if invalid/duplicate."""
    # Validate
    err = _validate_pick(pick, source_system)
    if err:
        return None  # Silently skip invalid picks (they're noise)

    symbol = _extract_symbol(pick)
    direction = _extract_direction(pick)
    if not direction:
        return None

    entry = _extract_price(pick, "entry_price", "entryPrice", "entry", "price")
    tp = _extract_price(pick, "take_profit", "targetPrice", "tp_price", "tp", "target_price")
    sl = _extract_price(pick, "stop_loss", "stopPrice", "sl_price", "sl", "stop_price")
    conf = _extract_price(pick, "confidence", "ml_score") or 0.5
    strategy = _extract_strategy(pick)
    signal_ts = pick.get("timestamp", pick.get("generated_at", pick.get("time", "")))

    # Compute risk/reward
    rr = None
    if entry and tp and sl and entry > 0:
        if direction == "LONG" and (entry - sl) > 0:
            rr = round((tp - entry) / (entry - sl), 2)
        elif direction == "SHORT" and (sl - entry) > 0:
            rr = round((entry - tp) / (sl - entry), 2)

    # Dedup hash
    dedup = compute_dedup_hash(symbol, direction, entry or 0, signal_ts or "")

    pick_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO raw_picks "
            "(id, aggregation_run_id, source_system, symbol, asset_class, direction, "
            "entry_price, take_profit, stop_loss, risk_reward, confidence, strategy, "
            "raw_payload, signal_timestamp, recorded_at, dedup_hash) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (pick_id, run_id, source_system, symbol, derive_asset_class(symbol),
             direction, entry, tp, sl, rr, conf, strategy,
             json.dumps(pick, default=str), signal_ts, _now_iso(), dedup),
        )
        conn.commit()
        return pick_id
    except Exception:
        # Duplicate hash — silently skip
        conn.rollback()
        return None


def mark_raw_pick_filtered(pick_id: str, reason: str) -> None:
    """Mark a raw pick as filtered (set the appropriate was_* flag)."""
    flag_map = {
        "staleness": "was_stale",
        "banned_strategy": "was_banned",
        "demoted_system": "was_demoted",
        "wr_suppressed": "was_wr_suppressed",
    }
    col = flag_map.get(reason)
    if col and pick_id:
        conn = get_connection()
        conn.execute(f"UPDATE raw_picks SET {col}=1 WHERE id=?", (pick_id,))
        conn.commit()


def record_consensus_pick(pick: dict, run_id: str) -> str:
    """Record a consensus pick that passed all gates. Returns pick_id."""
    pick_id = str(uuid.uuid4())
    symbol = pick.get("symbol", "")
    direction = pick.get("direction", "")
    entry = pick.get("entry", pick.get("entry_price", 0))
    tp = pick.get("tp", pick.get("take_profit", 0))
    sl = pick.get("sl", pick.get("stop_loss", 0))
    conf = pick.get("confidence", 0.5)
    generated_at = pick.get("generated_at", _now_iso())

    # Compute R:R
    rr = None
    try:
        e, t, s = float(entry), float(tp), float(sl)
        if direction == "LONG" and (e - s) > 0:
            rr = round((t - e) / (e - s), 2)
        elif direction == "SHORT" and (s - e) > 0:
            rr = round((e - t) / (s - e), 2)
    except (ValueError, TypeError, ZeroDivisionError):
        pass

    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO consensus_picks "
            "(id, aggregation_run_id, symbol, asset_class, direction, entry_price, "
            "take_profit, stop_loss, risk_reward, confidence, agreement_count, "
            "source_systems, source_strategies, system_confidences, consensus_tier, "
            "classification, regime_data, generated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (pick_id, run_id, symbol, derive_asset_class(symbol), direction,
             entry, tp, sl, rr, conf,
             pick.get("agreement_count"),
             json.dumps(pick.get("source_systems", [])),
             json.dumps(pick.get("source_strategies", {})),
             json.dumps(pick.get("system_rolling_wrs", {})),
             pick.get("consensus_tier"),
             pick.get("classification"),
             json.dumps(pick.get("regime_data")) if pick.get("regime_data") else None,
             generated_at),
        )
        conn.commit()
    except Exception:
        conn.rollback()
    return pick_id


def record_filter(symbol: str, direction: str, source_system: str,
                  filter_reason: str, details: str, run_id: str,
                  raw_pick_id: str = None) -> None:
    """Log why a pick was filtered out."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO filter_log "
        "(aggregation_run_id, raw_pick_id, symbol, direction, source_system, "
        "filter_reason, details, timestamp) VALUES (?,?,?,?,?,?,?,?)",
        (run_id, raw_pick_id, symbol, direction, source_system,
         filter_reason, details, _now_iso()),
    )
    conn.commit()

    # Also mark the raw pick flag if we have a pick_id
    if raw_pick_id:
        mark_raw_pick_filtered(raw_pick_id, filter_reason)


def record_event(event_type: str, pick_id: str = None, run_id: str = None,
                 symbol: str = None, payload: dict = None,
                 origin: str = "aggregator") -> None:
    """Log a chronological audit event."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO audit_events "
        "(event_type, pick_id, aggregation_run_id, symbol, payload, origin, timestamp) "
        "VALUES (?,?,?,?,?,?,?)",
        (event_type, pick_id, run_id, symbol,
         json.dumps(payload, default=str) if payload else None,
         origin, _now_iso()),
    )
    conn.commit()


def update_pick_outcome(pick_id: str, status: str, exit_price: float,
                        exit_reason: str, pnl_pct: float) -> None:
    """Update a consensus pick with its outcome (TP hit, SL hit, etc.)."""
    conn = get_connection()
    conn.execute(
        "UPDATE consensus_picks SET status=?, exit_price=?, exit_reason=?, "
        "pnl_pct=?, closed_at=? WHERE id=?",
        (status, exit_price, exit_reason, pnl_pct, _now_iso(), pick_id),
    )
    conn.commit()

    record_event(event_type=f"POSITION_CLOSED_{status}",
                 pick_id=pick_id, symbol=None,
                 payload={"exit_price": exit_price, "exit_reason": exit_reason,
                          "pnl_pct": pnl_pct},
                 origin="outcome_tracker")


def refresh_strategy_stats() -> None:
    """Rebuild the strategy_stats materialized view from consensus_picks."""
    conn = get_connection()
    conn.execute("DELETE FROM strategy_stats")

    conn.execute("""
        INSERT INTO strategy_stats
            (strategy, source_system, asset_class, total_picks, consensus_picks,
             wins, losses, win_rate, avg_pnl_pct, best_pnl, worst_pnl, last_updated)
        SELECT
            COALESCE(json_extract(cp.source_strategies, '$.' || key), 'unknown') AS strategy,
            key AS source_system,
            cp.asset_class,
            COUNT(*) AS total_picks,
            COUNT(*) AS consensus_picks,
            SUM(CASE WHEN cp.status = 'WON' THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN cp.status = 'LOST' THEN 1 ELSE 0 END) AS losses,
            CASE WHEN SUM(CASE WHEN cp.status IN ('WON','LOST') THEN 1 ELSE 0 END) > 0
                THEN CAST(SUM(CASE WHEN cp.status='WON' THEN 1 ELSE 0 END) AS REAL)
                     / SUM(CASE WHEN cp.status IN ('WON','LOST') THEN 1 ELSE 0 END)
                ELSE 0.0 END AS win_rate,
            AVG(COALESCE(cp.pnl_pct, 0)) AS avg_pnl_pct,
            MAX(COALESCE(cp.pnl_pct, 0)) AS best_pnl,
            MIN(COALESCE(cp.pnl_pct, 0)) AS worst_pnl,
            datetime('now') AS last_updated
        FROM consensus_picks cp,
             json_each(cp.source_systems) AS je(key)
        WHERE cp.status != 'OPEN'
        GROUP BY strategy, source_system, cp.asset_class
    """)
    conn.commit()
```

**Step 2: Update `audit_trail/__init__.py` with public API**

```python
"""
Central Audit Trail for crypto prediction picks.

Public API:
    from audit_trail import start_run, finish_run, record_raw_pick, ...
"""

from audit_trail.recorder import (
    start_run,
    finish_run,
    record_raw_pick,
    record_consensus_pick,
    record_filter,
    record_event,
    update_pick_outcome,
    refresh_strategy_stats,
    derive_asset_class,
    compute_dedup_hash,
)

__all__ = [
    "start_run",
    "finish_run",
    "record_raw_pick",
    "record_consensus_pick",
    "record_filter",
    "record_event",
    "update_pick_outcome",
    "refresh_strategy_stats",
    "derive_asset_class",
    "compute_dedup_hash",
]
```

**Step 3: Smoke test the recorder**

Run:
```bash
cd e:/findtorontoevents_antigravity.ca && py -c "
from audit_trail import start_run, record_raw_pick, record_consensus_pick, record_filter, finish_run
from audit_trail.db import get_connection

# Start a run
run_id = start_run(regime_data={'fng': 45, 'regime': 'RANGING'}, portfolio_dd=5.2)
print(f'Run started: {run_id}')

# Record a raw pick
pid = record_raw_pick('alpha_engine', {
    'symbol': 'BTCUSDT', 'direction': 'LONG', 'entry_price': 65000,
    'take_profit': 67000, 'stop_loss': 64000, 'confidence': 0.78,
    'strategy': 'connors_rsi2', 'timestamp': '2026-03-04T12:00:00Z'
}, run_id)
print(f'Raw pick recorded: {pid}')

# Record a filter
record_filter('ETHUSDT', 'LONG', 'kimi', 'regime_mismatch',
              'LONG blocked by RANGING regime', run_id)
print('Filter logged')

# Record consensus
cpid = record_consensus_pick({
    'symbol': 'BTCUSDT', 'direction': 'LONG', 'entry': 65000,
    'tp': 67000, 'sl': 64000, 'confidence': 0.85,
    'agreement_count': 3, 'source_systems': ['alpha_engine', 'kimi', 'genome'],
    'source_strategies': {'alpha_engine': 'connors_rsi2'},
    'consensus_tier': 'STRONG', 'generated_at': '2026-03-04T12:00:00Z'
}, run_id)
print(f'Consensus pick recorded: {cpid}')

# Finish run
finish_run(run_id, consensus_count=1, systems_loaded=5, raw_count=12)
print('Run finished')

# Verify
conn = get_connection()
for t in ['aggregation_runs', 'raw_picks', 'consensus_picks', 'filter_log', 'audit_events']:
    count = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
    print(f'  {t}: {count} rows')
"
```

Expected: All tables have 1+ rows, no errors.

**Step 4: Commit**

```bash
git add audit_trail/recorder.py audit_trail/__init__.py
git commit -m "feat(audit): add recorder module with validation, dedup, and public API"
```

---

## Task 3: Instrument the Aggregator

**Files:**
- Modify: `cross_aggregation/aggregator.py:1-20` (add import)
- Modify: `cross_aggregation/aggregator.py:409-820` (add ~15 instrumentation calls)

**Step 1: Add the audit trail import at top of aggregator.py**

After line 21 (the existing imports), add:

```python
# Audit trail integration
try:
    from audit_trail import (
        start_run, finish_run, record_raw_pick,
        record_consensus_pick, record_filter, record_event,
    )
    _HAS_AUDIT = True
except ImportError:
    _HAS_AUDIT = False
```

**Step 2: Instrument `aggregate()` — start of function (line ~409)**

After the portfolio drawdown check (around line 418), insert:

```python
    # ── Audit trail: start run ──
    _audit_run_id = None
    _audit_raw_count = 0
    if _HAS_AUDIT:
        try:
            _audit_run_id = start_run(
                regime_data=None,  # filled later when regime is fetched
                portfolio_dd=dd_pct,
            )
        except Exception as e:
            print(f"  [AUDIT] Failed to start run: {e}")
```

**Step 3: Instrument raw pick loading (inside the system loop, line ~426)**

After each pick is processed (after `picks_by_symbol[symbol].append(...)` on line 472), add:

```python
            # ── Audit: record raw pick ──
            if _HAS_AUDIT and _audit_run_id:
                try:
                    record_raw_pick(sys_name, pick, _audit_run_id)
                    _audit_raw_count += 1
                except Exception:
                    pass
```

**Step 4: Instrument filter points**

At each filter location, add a `record_filter` call. These go INSIDE the existing `if` blocks:

**a) Demoted system (line ~430):**
```python
            # After the print statement for demoted
            if _HAS_AUDIT and _audit_run_id:
                try:
                    record_filter("", "", sys_name, "demoted_system",
                                  f"{sys_name} excluded from consensus", _audit_run_id)
                except Exception:
                    pass
```

**b) Rolling WR guard (line ~437):**
```python
            # After the print statement for WR guard
            if _HAS_AUDIT and _audit_run_id:
                try:
                    record_filter("", "", sys_name, "wr_suppressed",
                                  f"{sys_name} rolling WR {rwr*100:.0f}% < {ROLLING_WR_SUSPEND*100:.0f}%",
                                  _audit_run_id)
                except Exception:
                    pass
```

**c) Banned strategy (line ~455):**
```python
                # Inside the `if strategy and strategy in BANNED_STRATEGIES:` block
                if _HAS_AUDIT and _audit_run_id:
                    try:
                        record_filter(raw_symbol, direction or "", sys_name,
                                      "banned_strategy", f"strategy '{strategy}' is banned",
                                      _audit_run_id)
                    except Exception:
                        pass
```

**d) Stale signal (line ~466):**
```python
                        # Inside the `if age_min > MAX_SIGNAL_AGE_MIN:` block
                        if _HAS_AUDIT and _audit_run_id:
                            try:
                                record_filter(raw_symbol, direction or "", sys_name,
                                              "staleness", f"{age_min:.0f}min old > {MAX_SIGNAL_AGE_MIN}min",
                                              _audit_run_id)
                            except Exception:
                                pass
```

**e) No consensus (inside the else at line ~496):**
```python
            # After the conflicts.append() block
            if _HAS_AUDIT and _audit_run_id:
                try:
                    record_filter(symbol, "", "", "no_consensus",
                                  f"LONG:{long_cnt} SHORT:{short_cnt} < threshold {CONSENSUS_THRESHOLD}",
                                  _audit_run_id)
                except Exception:
                    pass
```

**f) Correlation gate (line ~598):**
```python
        # Inside each corr_filtered.append() call, also add:
        if _HAS_AUDIT and _audit_run_id:
            try:
                record_filter(sym, direction, "", "concentration_cap",
                              cf["reason"], _audit_run_id)
            except Exception:
                pass
```

**g) Regime filter (line ~719):**
```python
                    # When a pick is regime-filtered
                    if _HAS_AUDIT and _audit_run_id:
                        try:
                            record_filter(sym, direction, "", "regime_mismatch",
                                          f"{direction} blocked by regime={reg}, F&G={fng}",
                                          _audit_run_id)
                        except Exception:
                            pass
```

**h) Daily cap (line ~693):**
```python
        # For each dropped pick
        if _HAS_AUDIT and _audit_run_id:
            for d in dropped:
                try:
                    record_filter(d["symbol"], d["direction"], "", "daily_cap",
                                  f"exceeded {MAX_DAILY_PICKS} daily limit", _audit_run_id)
                except Exception:
                    pass
```

**Step 5: Instrument consensus pick recording (line ~576)**

After building the `unified` dict, add:

```python
        # ── Audit: record consensus pick ──
        if _HAS_AUDIT and _audit_run_id:
            try:
                record_consensus_pick(unified, _audit_run_id)
            except Exception:
                pass
```

**Step 6: Instrument end of aggregate() (before the return)**

Before `return aggregated` (line ~807), add:

```python
    # ── Audit trail: finish run ──
    if _HAS_AUDIT and _audit_run_id:
        try:
            finish_run(_audit_run_id, consensus_count=len(aggregated),
                       systems_loaded=sum(1 for v in system_stats.values() if v > 0),
                       raw_count=_audit_raw_count)
        except Exception as e:
            print(f"  [AUDIT] Failed to finish run: {e}")
```

**Step 7: Test the instrumented aggregator locally**

Run:
```bash
cd e:/findtorontoevents_antigravity.ca && py cross_aggregation/aggregator.py
```

Then verify audit data:
```bash
py -c "
from audit_trail.db import get_connection
conn = get_connection()
for t in ['aggregation_runs', 'raw_picks', 'consensus_picks', 'filter_log', 'audit_events']:
    count = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
    print(f'{t}: {count} rows')

# Show latest run
run = conn.execute('SELECT * FROM aggregation_runs ORDER BY started_at DESC LIMIT 1').fetchone()
if run:
    print(f'\nLatest run: {run[\"run_id\"][:8]}... status={run[\"status\"]} consensus={run[\"consensus_count\"]} raw={run[\"raw_picks_count\"]}')
"
```

Expected: Tables populated with real data from the aggregator run.

**Step 8: Commit**

```bash
git add cross_aggregation/aggregator.py
git commit -m "feat(audit): instrument aggregator with audit trail logging"
```

---

## Task 4: Instrument Discord Notify (TP/SL/Post Events)

**Files:**
- Modify: `cross_aggregation/discord_notify.py:24-32` (add import)
- Modify: `cross_aggregation/discord_notify.py:648` (send_consensus_alert)
- Modify: `cross_aggregation/discord_notify.py:969` (send_tp_hit_alert)
- Modify: `cross_aggregation/discord_notify.py:1043` (send_sl_hit_alert)

**Step 1: Add audit import at top of discord_notify.py**

After line 31 (`from typing import Optional`), add:

```python
# Audit trail integration
try:
    from audit_trail import record_event
    _HAS_AUDIT = True
except ImportError:
    _HAS_AUDIT = False
```

**Step 2: Instrument send_consensus_alert (after successful _post call)**

In `send_consensus_alert()`, after each successful `_post(embeds)` call for actual picks (around line 940-960 area where the batch posting happens), add:

```python
            # ── Audit: log Discord post ──
            if _HAS_AUDIT:
                for p in batch_picks:
                    try:
                        record_event("DISCORD_POSTED", symbol=p.get("symbol"),
                                     payload={"channel": channel_name,
                                              "direction": p.get("direction"),
                                              "confidence": p.get("confidence")},
                                     origin="discord_notify")
                    except Exception:
                        pass
```

**Step 3: Instrument send_tp_hit_alert (after _post call, line ~1040)**

After `_post(embeds)` in `send_tp_hit_alert`, add:

```python
    # ── Audit: log TP hit ──
    if _HAS_AUDIT:
        try:
            record_event("TP_HIT", symbol=symbol,
                         payload={"direction": direction, "entry": entry,
                                  "tp": tp, "exit_price": live_price,
                                  "pnl_pct": pnl, "agreement": agreement},
                         origin="discord_notify")
        except Exception:
            pass
```

**Step 4: Instrument send_sl_hit_alert (after _post call, line ~1170 area)**

After `_post(embeds)` in `send_sl_hit_alert`, add:

```python
    # ── Audit: log SL hit ──
    if _HAS_AUDIT:
        try:
            record_event("SL_HIT", symbol=symbol,
                         payload={"direction": direction, "entry": entry,
                                  "sl": sl, "exit_price": live_price,
                                  "pnl_pct": pnl, "agreement": agreement,
                                  "lesson": lesson},
                         origin="discord_notify")
        except Exception:
            pass
```

**Step 5: Verify imports work**

Run:
```bash
cd e:/findtorontoevents_antigravity.ca && py -c "from cross_aggregation.discord_notify import send_consensus_alert; print('Import OK')"
```

**Step 6: Commit**

```bash
git add cross_aggregation/discord_notify.py
git commit -m "feat(audit): instrument discord notifier with TP/SL/post event logging"
```

---

## Task 5: Add audit_trail.db to .gitignore and Workflow

**Files:**
- Modify: `.gitignore` (add audit DB)
- Modify: `.github/workflows/cross-aggregator.yml` (commit audit DB)

**Step 1: Add to .gitignore**

The SQLite DB should NOT be gitignored — it needs to persist across GitHub Actions runs via git commits (same pattern as `data/dna_master_picks.db`).

Verify the existing pattern:
```bash
grep -n "audit_trail" e:/findtorontoevents_antigravity.ca/.gitignore || echo "not in gitignore (good)"
```

**Step 2: Update the workflow to commit audit data**

In `.github/workflows/cross-aggregator.yml`, find the `git add` step and add `data/audit_trail.db`:

The git add line should include: `data/audit_trail.db`

This follows the same pattern already used for `data/dna_master_picks.db` and `data/aggregated_picks.json`.

**Step 3: Commit**

```bash
git add .github/workflows/cross-aggregator.yml
git commit -m "ci: include audit_trail.db in cross-aggregator workflow commits"
```

---

## Task 6: Verification Script

**Files:**
- Create: `audit_trail/verify.py`

**Step 1: Write a verification/query script**

Create `audit_trail/verify.py`:

```python
"""
Audit Trail Verification & Query Script
========================================
Run: python -m audit_trail.verify

Prints summary stats from the audit trail DB.
"""

import json
from audit_trail.db import get_connection


def verify():
    conn = get_connection()

    print("=" * 60)
    print("AUDIT TRAIL VERIFICATION")
    print("=" * 60)

    # Schema version
    ver = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    print(f"\nSchema version: {ver[0] if ver else 'UNKNOWN'}")

    # Table counts
    print("\nTable row counts:")
    for table in ["aggregation_runs", "raw_picks", "consensus_picks",
                  "filter_log", "audit_events", "strategy_stats"]:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:25s} {count:>6d} rows")

    # Latest run
    run = conn.execute(
        "SELECT * FROM aggregation_runs ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    if run:
        print(f"\nLatest run:")
        print(f"  ID:        {run['run_id'][:8]}...")
        print(f"  Started:   {run['started_at']}")
        print(f"  Status:    {run['status']}")
        print(f"  Systems:   {run['systems_loaded']}")
        print(f"  Raw picks: {run['raw_picks_count']}")
        print(f"  Consensus: {run['consensus_count']}")

    # Filter breakdown
    print("\nFilter reasons (all time):")
    rows = conn.execute(
        "SELECT filter_reason, COUNT(*) as cnt FROM filter_log "
        "GROUP BY filter_reason ORDER BY cnt DESC"
    ).fetchall()
    for r in rows:
        print(f"  {r['filter_reason']:25s} {r['cnt']:>6d}")

    # Source system pick counts
    print("\nRaw picks by source system:")
    rows = conn.execute(
        "SELECT source_system, COUNT(*) as cnt FROM raw_picks "
        "GROUP BY source_system ORDER BY cnt DESC LIMIT 10"
    ).fetchall()
    for r in rows:
        print(f"  {r['source_system']:25s} {r['cnt']:>6d}")

    # Consensus picks by status
    print("\nConsensus picks by status:")
    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM consensus_picks "
        "GROUP BY status ORDER BY cnt DESC"
    ).fetchall()
    for r in rows:
        print(f"  {r['status']:25s} {r['cnt']:>6d}")

    # Event types
    print("\nAudit events by type:")
    rows = conn.execute(
        "SELECT event_type, COUNT(*) as cnt FROM audit_events "
        "GROUP BY event_type ORDER BY cnt DESC"
    ).fetchall()
    for r in rows:
        print(f"  {r['event_type']:30s} {r['cnt']:>6d}")

    print(f"\n{'=' * 60}")


if __name__ == "__main__":
    verify()
```

**Step 2: Test it**

Run:
```bash
cd e:/findtorontoevents_antigravity.ca && py -m audit_trail.verify
```

Expected: Summary table with row counts and breakdowns.

**Step 3: Commit**

```bash
git add audit_trail/verify.py
git commit -m "feat(audit): add verification and query script"
```

---

## Task 7: End-to-End Integration Test

**Step 1: Run the full pipeline locally**

```bash
cd e:/findtorontoevents_antigravity.ca
# Run aggregator (this now writes to audit DB)
py cross_aggregation/aggregator.py
# Verify audit data
py -m audit_trail.verify
```

**Step 2: Run sample queries against the DB**

```bash
py -c "
from audit_trail.db import get_connection
conn = get_connection()

# Win rate per system (from raw_picks that made it to consensus)
print('=== Systems contributing to consensus ===')
rows = conn.execute('''
    SELECT source_system, COUNT(*) as picks
    FROM raw_picks
    WHERE was_stale=0 AND was_banned=0 AND was_demoted=0 AND was_wr_suppressed=0
    GROUP BY source_system ORDER BY picks DESC
''').fetchall()
for r in rows:
    print(f'  {r[\"source_system\"]:25s} {r[\"picks\"]:>4d} valid picks')

# Filter funnel
print('\n=== Filter Funnel ===')
total = conn.execute('SELECT COUNT(*) FROM raw_picks').fetchone()[0]
valid = conn.execute('SELECT COUNT(*) FROM raw_picks WHERE was_stale=0 AND was_banned=0 AND was_demoted=0 AND was_wr_suppressed=0').fetchone()[0]
consensus = conn.execute('SELECT COUNT(*) FROM consensus_picks').fetchone()[0]
print(f'  Raw picks loaded:    {total}')
print(f'  After filters:       {valid}')
print(f'  Consensus picks:     {consensus}')
print(f'  Pass rate:           {consensus/max(total,1)*100:.1f}%')
"
```

**Step 3: Commit all remaining changes**

```bash
git add -A audit_trail/ data/audit_trail.db
git commit -m "feat(audit): complete Phase 1 central audit trail with end-to-end verification"
```
