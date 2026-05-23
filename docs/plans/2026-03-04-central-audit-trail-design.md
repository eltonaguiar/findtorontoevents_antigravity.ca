# Central Audit Trail — Design Document

**Date:** 2026-03-04
**Status:** Approved
**Scope:** Phase 1 — Core Audit DB + Instrumentation

---

## 1. Goal

Create a centralized audit trail for **every crypto/forex/equity prediction pick** across all 25+ signal generators. Capture raw picks, consensus decisions, filtering reasons, and outcomes in a single SQLite database (`data/audit_trail.db`) designed for future MySQL migration.

## 2. Architecture

```
audit_trail/
  __init__.py          # Public API with type hints
  db.py                # SQLite connection + schema management (swap driver for MySQL later)
  recorder.py          # Core recording logic, JSON-Schema validation, dedup
  schema.sql           # DDL with version header (-- version: 1.0)
```

**Instrumentation approach:** ~10 lines added to `cross_aggregation/aggregator.py` and `cross_aggregation/discord_notify.py`. All other systems untouched in Phase 1 (they're captured via the aggregator's load step).

## 3. Database Schema

### Design Principles
- **UUID primary keys** (`CHAR(36)`) for global uniqueness and MySQL compatibility
- **REAL** for prices/percentages in SQLite (maps to `DECIMAL(18,8)` in MySQL)
- **TEXT** for JSON columns in SQLite (maps to native `JSON` in MySQL)
- **TEXT** for enums in SQLite (maps to `ENUM(...)` in MySQL)
- **Dedup hash** with UNIQUE index to prevent duplicate picks
- **Foreign keys** enabled (`PRAGMA foreign_keys = ON`)
- **Schema version** tracked in `meta` table

### 3.1 `meta` — Schema versioning

| Column | Type | Notes |
|--------|------|-------|
| key | TEXT PK | e.g. "schema_version" |
| value | TEXT | e.g. "1.0" |

### 3.2 `aggregation_runs` — One row per aggregator execution

| Column | Type | Notes |
|--------|------|-------|
| run_id | CHAR(36) PK | UUID |
| started_at | TEXT | ISO 8601 UTC |
| finished_at | TEXT | ISO 8601 UTC |
| status | TEXT | RUNNING / COMPLETED / FAILED |
| systems_loaded | INTEGER | Count of systems that had picks |
| raw_picks_count | INTEGER | Total raw picks ingested |
| consensus_count | INTEGER | Picks that passed all gates |
| regime_data | TEXT | JSON snapshot of regime at run time |
| portfolio_drawdown_pct | REAL | Portfolio DD at time of run |

### 3.3 `raw_picks` — Every pick from every source system

| Column | Type | Notes |
|--------|------|-------|
| id | CHAR(36) PK | UUID |
| aggregation_run_id | CHAR(36) | FK → aggregation_runs, INDEXED |
| source_system | TEXT | e.g. "alpha_engine", "kimi", "genome" |
| symbol | TEXT | Normalized (BTCUSDT) |
| asset_class | TEXT | CRYPTO / FOREX / EQUITY / MEMECOIN (derived from symbol) |
| direction | TEXT | LONG / SHORT |
| entry_price | REAL | |
| take_profit | REAL | |
| stop_loss | REAL | |
| risk_reward | REAL | Computed: (TP-entry)/(entry-SL) for LONG |
| confidence | REAL | 0.00-1.00 |
| strategy | TEXT | Strategy name from source |
| raw_payload | TEXT | Full original JSON for forensics |
| signal_timestamp | TEXT | ISO 8601 UTC — when source generated it |
| recorded_at | TEXT | ISO 8601 UTC — when we logged it |
| dedup_hash | CHAR(64) UNIQUE | SHA-256 of (symbol+direction+entry_price+ts_rounded_5min) |
| was_stale | INTEGER | 0/1 — filtered by staleness guard |
| was_banned | INTEGER | 0/1 — filtered by banned strategy |
| was_demoted | INTEGER | 0/1 — source system was demoted |
| was_wr_suppressed | INTEGER | 0/1 — filtered by rolling WR guard |
| created_by | TEXT | Bot/process name that recorded this |

**Indexes:** `(aggregation_run_id)`, `(source_system)`, `(symbol)`, `(signal_timestamp)`, `(dedup_hash) UNIQUE`

### 3.4 `consensus_picks` — Picks that survived all gates

| Column | Type | Notes |
|--------|------|-------|
| id | CHAR(36) PK | UUID |
| aggregation_run_id | CHAR(36) | FK → aggregation_runs, INDEXED |
| symbol | TEXT | |
| asset_class | TEXT | CRYPTO / FOREX / EQUITY / MEMECOIN |
| direction | TEXT | LONG / SHORT |
| entry_price | REAL | |
| take_profit | REAL | |
| stop_loss | REAL | |
| risk_reward | REAL | |
| confidence | REAL | Final boosted confidence |
| agreement_count | INTEGER | How many systems agreed |
| source_systems | TEXT | JSON array |
| source_strategies | TEXT | JSON map {system: strategy} |
| system_confidences | TEXT | JSON map {system: confidence} |
| consensus_tier | TEXT | STRONG / MODERATE |
| classification | TEXT | ELITE / PROVEN / EXPERIMENTAL |
| regime_data | TEXT | JSON snapshot of regime at pick time |
| discord_channel | TEXT | Where it was routed |
| discord_message_id | TEXT | Discord Snowflake for traceability |
| status | TEXT | OPEN / WON / LOST / EXPIRED / MANUAL_CLOSE |
| exit_price | REAL | Filled on close |
| exit_reason | TEXT | TP / SL / TIMEOUT / MANUAL / KILL |
| pnl_pct | REAL | |
| slippage_estimate | REAL | From cost model |
| generated_at | TEXT | ISO 8601 UTC |
| closed_at | TEXT | ISO 8601 UTC |

**Indexes:** `(aggregation_run_id)`, `(symbol)`, `(status)`, `(source_systems)`
**Unique constraint:** `(symbol, direction, entry_price, generated_at)`

### 3.5 `audit_events` — Chronological event log for forensic replay

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK AUTOINCREMENT | Sequential for ordering |
| event_type | TEXT | AGGREGATION_START, RAW_PICK_LOADED, PICK_FILTERED, CONSENSUS_FORMED, DISCORD_POSTED, TP_HIT, SL_HIT, POSITION_CLOSED |
| pick_id | CHAR(36) | FK → consensus_picks (nullable) |
| aggregation_run_id | CHAR(36) | FK → aggregation_runs |
| symbol | TEXT | For fast filtering |
| payload | TEXT | JSON with event-specific details |
| origin | TEXT | Bot/process that emitted the event |
| timestamp | TEXT | ISO 8601 UTC |

**Indexes:** `(aggregation_run_id)`, `(pick_id)`, `(event_type)`, `(symbol)`

### 3.6 `filter_log` — Why picks were rejected

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK AUTOINCREMENT | |
| aggregation_run_id | CHAR(36) | FK → aggregation_runs, INDEXED |
| raw_pick_id | CHAR(36) | FK → raw_picks (nullable) |
| symbol | TEXT | |
| direction | TEXT | |
| source_system | TEXT | |
| filter_reason | TEXT | staleness, banned_strategy, demoted_system, wr_suppressed, no_consensus, regime_mismatch, concentration_cap, daily_cap |
| details | TEXT | Human-readable explanation |
| timestamp | TEXT | ISO 8601 UTC |

**Indexes:** `(aggregation_run_id)`, `(filter_reason)`, `(symbol)`

### 3.7 `strategy_stats` — Materialized performance view

| Column | Type | Notes |
|--------|------|-------|
| strategy | TEXT | Composite PK part 1 |
| source_system | TEXT | Composite PK part 2 |
| asset_class | TEXT | CRYPTO / FOREX / EQUITY |
| total_picks | INTEGER | Raw picks submitted |
| consensus_picks | INTEGER | How many reached consensus |
| wins | INTEGER | |
| losses | INTEGER | |
| win_rate | REAL | |
| avg_pnl_pct | REAL | |
| best_pnl | REAL | |
| worst_pnl | REAL | |
| avg_risk_reward | REAL | |
| last_updated | TEXT | ISO 8601 UTC |

**Indexes:** `(source_system)`, `(asset_class)`

## 4. Instrumentation Points

### 4.1 `cross_aggregation/aggregator.py`

| Location | Call | Extra data captured |
|----------|------|---------------------|
| Start of `aggregate()` | `audit.start_run()` → returns `run_id` UUID | Portfolio DD, timestamp |
| Each pick loaded (line ~426) | `audit.record_raw_pick(sys_name, pick, run_id)` | Dedup hash computed before call |
| Demoted system skip (line ~430) | `audit.record_filter(symbol, "demoted_system", run_id)` | System name |
| Rolling WR guard (line ~437) | `audit.record_filter(symbol, "wr_suppressed", run_id)` | Actual WR value |
| Banned strategy (line ~455) | `audit.record_filter(symbol, "banned_strategy", run_id)` | Strategy name in details |
| Stale signal (line ~466) | `audit.record_filter(symbol, "staleness", run_id)` | Age in minutes |
| Consensus formed (line ~576) | `audit.record_consensus_pick(unified, run_id)` | All system confidences as JSON |
| No consensus (line ~496) | `audit.record_filter(symbol, "no_consensus", run_id)` | Long/short system counts |
| Correlation gate (lines ~598-625) | `audit.record_filter(symbol, "concentration_cap", run_id)` | Current concentration metrics |
| Regime filter (lines ~658-678) | `audit.record_filter(symbol, "regime_mismatch", run_id)` | Detected vs required regime |
| Daily cap (line ~691) | `audit.record_filter(symbol, "daily_cap", run_id)` | Pick count at cap |
| End of `aggregate()` | `audit.finish_run(run_id, len(aggregated))` | Final stats |

### 4.2 `cross_aggregation/discord_notify.py`

| Location | Call | Extra data |
|----------|------|------------|
| After successful webhook post | `audit.record_event("DISCORD_POSTED", pick_id, message_id)` | Channel name, timestamp |
| `send_tp_hit_alert()` | `audit.record_event("TP_HIT", pick_id, exit_data)` | Exit price, slippage |
| `send_sl_hit_alert()` | `audit.record_event("SL_HIT", pick_id, exit_data)` | Exit price, lesson text |
| `send_position_update()` | `audit.record_event("POSITION_UPDATE", pick_id, pnl_data)` | Current PnL |

## 5. Validation & Dedup

### Hash-based dedup
```python
import hashlib
def compute_dedup_hash(symbol: str, direction: str, entry_price: float, signal_ts: str) -> str:
    epoch = int(parse_iso(signal_ts).timestamp() / 300) * 300  # Round to 5-min
    raw = f"{symbol}|{direction}|{entry_price:.8f}|{epoch}"
    return hashlib.sha256(raw.encode()).hexdigest()
```
- Stored in `dedup_hash` column with UNIQUE index
- INSERT OR IGNORE pattern — silently skip duplicates
- Raises `DuplicatePickError` only when caller needs to know

### Schema validation
- JSON-Schema (draft-07) compiled once at module import
- Required fields: symbol, direction, entry_price
- Price sanity: entry_price > 0; for LONG: TP > entry > SL; for SHORT: SL > entry > TP
- Confidence range: 0.0 ≤ confidence ≤ 1.0
- Timestamp sanity: not more than 5 minutes in the future
- All timestamps normalized to UTC before storage

### Asset class derivation
```python
def derive_asset_class(symbol: str) -> str:
    if symbol.endswith(("USDT", "BTC", "ETH", "BUSD")):
        return "CRYPTO"
    forex_prefixes = ("EUR", "GBP", "USD", "JPY", "AUD", "CAD", "CHF", "NZD")
    if any(symbol.startswith(p) for p in forex_prefixes):
        return "FOREX"
    return "EQUITY"
```

## 6. Public API (`audit_trail/__init__.py`)

```python
def start_run(regime_data: dict = None, portfolio_dd: float = 0.0) -> str: ...
def finish_run(run_id: str, consensus_count: int) -> None: ...
def record_raw_pick(source_system: str, pick: dict, run_id: str) -> str: ...
def record_consensus_pick(pick: dict, run_id: str) -> str: ...
def record_filter(symbol: str, direction: str, source_system: str,
                  filter_reason: str, details: str, run_id: str,
                  raw_pick_id: str = None) -> None: ...
def record_event(event_type: str, pick_id: str = None,
                 run_id: str = None, symbol: str = None,
                 payload: dict = None, origin: str = "aggregator") -> None: ...
def update_pick_outcome(pick_id: str, status: str, exit_price: float,
                        exit_reason: str, pnl_pct: float) -> None: ...
def refresh_strategy_stats() -> None: ...
```

## 7. MySQL Migration Path

| SQLite (Phase 1) | MySQL (later) |
|-------------------|---------------|
| REAL | DECIMAL(18,8) |
| TEXT (enum-like) | ENUM('LONG','SHORT') |
| TEXT (JSON) | JSON (with JSON_EXTRACT indexing) |
| CHAR(36) | CHAR(36) |
| INTEGER 0/1 | TINYINT(1) / BOOLEAN |
| schema.sql with SQLite syntax | Same DDL with type swaps |
| `db.py` uses sqlite3 | Swap to pymysql/psycopg2 |

## 8. What's Deferred (Phase 2+)

- Dashboard UI
- Automated threshold alerts (WR < 45%, Kelly < 5%)
- ML pipeline / feature store
- Regime cache table
- REST API endpoint
- Separate asset-class tables (MySQL optimization)
- Retention/archival policy
