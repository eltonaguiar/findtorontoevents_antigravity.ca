# Opposite Day Paper-Trade System — Design Document

**Date:** 2026-03-04
**Status:** Approved (with review feedback incorporated)

## 1. Overview

Deploy an "Opposite Day" paper-trading system that flips picks from **5 signal engines** and tracks performance across **4 time windows** (1h, 4h, 12h, 24h). Each engine gets its own paper-trade portfolio. Results are posted to the Discord `#paper-trade` channel with running scorecards and timeline heatmaps.

### Motivation

Empirical observation: predictions dashboard picks started red but turned green ~1 hour later when inverted. This suggests a **time-decay contrarian edge** that needs systematic measurement across all engines.

## 2. Architecture

```
sandbox/
├── __init__.py          # Expose public API: run, engine_adapters, tracker
├── config.py            # DB path, webhook URL, checkpoint intervals, constants
├── core.py              # Flip logic (direction + distance-based TP/SL inversion)
├── pnl.py               # PnL math, funding-rate adjustment (optional flag)
├── engine_adapters.py   # Normalize picks from 5 engines → NormalizedPick dataclass
├── tracker.py           # SQLite: open picks, timeline snapshots, closed history
├── discord_notify.py    # Embeds to #paper-trade channel (with rate-limit retry)
├── run.py               # CLI orchestrator with sub-commands (--scan --snapshot --close --notify)
└── data/
    └── opposite_day.db  # SQLite database
```

### Key changes from initial design (per review):
- Split PnL utilities into `pnl.py` to keep `core.py` focused on flip operations
- Added `config.py` for all tunable parameters (no magic numbers in code)
- `__init__.py` exposes `run`, `engine_adapters`, `tracker` for clean `python -m sandbox.run`

## 3. Configuration (`config.py`)

```python
from pathlib import Path

ROOT = Path(__file__).parent.parent
SANDBOX_DIR = Path(__file__).parent
DB_PATH = SANDBOX_DIR / "data" / "opposite_day.db"

# Timeline checkpoints (seconds)
CHECKPOINTS = {"1h": 3600, "4h": 14400, "12h": 43200, "24h": 86400}

# Pick expiration
EXPIRATION_HOURS = 24

# Discord
WEBHOOK_ENV_VAR = "DISCORD_PAPER_TRADE_WEBHOOK"
DISCORD_EMBED_CHAR_LIMIT = 6000
DISCORD_RATE_LIMIT_RETRY = 3
DISCORD_RETRY_DELAY = 2  # seconds

# TP/SL defaults (for engines that don't provide them)
DEFAULT_TP_DISTANCE_PCT = 5.0  # 5% from entry
DEFAULT_SL_DISTANCE_PCT = 3.0  # 3% from entry

# Exclusions
EXCLUDED_SYMBOLS = {"SUIUSDT"}  # SUI excluded (only 3 predictions)
```

## 4. Engine Adapters

Each adapter reads one source and returns `List[NormalizedPick]`:

| Adapter | Source File | Direction Field | Entry Field | TP/SL Notes |
|---------|-----------|-----------------|-------------|-------------|
| `predictions` | `predictions/data/active_predictions.json` | `direction` (LONG/SHORT) | `entry_price` | Has `take_profit`, `stop_loss` |
| `kimi` | `KIMI_RISEOFTHECLAW/data/live_signals_now.json` | `signal` (BUY→LONG, SELL→SHORT) | `entryPrice` | Has `targetPrice`, `stopPrice` |
| `alpha` | `alpha_engine/data/active_picks.json` | `direction` (LONG/SHORT) | `entry_price` | Has `take_profit`, `stop_loss` |
| `signal_engine` | `crypto_signal_engine/data/active_picks.json` | `signal` (LONG/SHORT) | `entry` | Has `tp`, `sl` |
| `cross_aggregator` | `cross_aggregation/data/super_signals.json` `.super_signals[]` | `direction` (LONG/SHORT) | `entry_price` | Has `take_profit`, `stop_loss` |

### NormalizedPick Dataclass

```python
@dataclass
class NormalizedPick:
    symbol: str                  # Normalized USDT pair (e.g., BTCUSDT)
    original_direction: str      # LONG or SHORT
    opposite_direction: str      # Flipped direction
    entry_price: float
    original_tp: float
    original_sl: float
    opposite_tp: float           # Distance-based inversion (not just swapped)
    opposite_sl: float           # Distance-based inversion
    source_engine: str           # predictions | kimi | alpha | signal_engine | cross_aggregator
    source_pick_id: str          # Unique ID from source (or generated hash)
    picked_at: str               # ISO 8601 UTC timestamp
    expiration_at: str           # picked_at + 24h (pre-computed)
    aggregated_confidence: float # From source (if available), else 0.0
```

### Adapter Implementation Rules
- **Typed return** — `NormalizedPick` dataclass enforced by static analysis
- **Error isolation** — each adapter wrapped in try/except; one broken engine never aborts the run
- **Dedup by `pick_id`** — check DB before insert, skip if already exists
- **Symbol normalization** — `BTC-USD`/`BTCUSD`/`BTC` → `BTCUSDT`
- **Default TP/SL** — if source lacks TP/SL, use `DEFAULT_TP_DISTANCE_PCT`/`DEFAULT_SL_DISTANCE_PCT` from config

## 5. Core Logic (`core.py`)

### Distance-Based TP/SL Inversion

**Critical:** Do NOT simply swap TP and SL numbers. Use distance-based inversion:

```python
def flip_tp_sl(entry: float, tp: float, sl: float) -> Tuple[float, float]:
    """Invert TP/SL using distance from entry, not by swapping values."""
    distance_tp = abs(tp - entry)
    distance_sl = abs(sl - entry)
    # For opposite direction: TP is on the other side at same distance
    # If original was LONG (TP above, SL below) → opposite SHORT (TP below, SL above)
    # new_tp = entry - distance_tp
    # new_sl = entry + distance_sl
    return entry - distance_tp, entry + distance_sl  # for LONG→SHORT
    # Caller handles direction to determine sign
```

### Timezone Handling
- ALL timestamps stored as UTC ISO 8601
- Any incoming local timestamps converted to UTC before insertion

## 6. SQLite Schema

### `opposite_picks`

```sql
CREATE TABLE opposite_picks (
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
    picked_at TIMESTAMP NOT NULL,
    expiration_at TIMESTAMP NOT NULL,
    status TEXT DEFAULT 'ACTIVE',
    closed_at TIMESTAMP,
    close_price REAL,
    pnl_pct REAL,
    original_pnl_pct REAL,
    aggregated_confidence REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_active_picks ON opposite_picks (status, picked_at);
CREATE INDEX idx_engine_status ON opposite_picks (source_engine, status);
```

### `timeline_snapshots`

```sql
CREATE TABLE timeline_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pick_id TEXT NOT NULL REFERENCES opposite_picks(pick_id),
    checkpoint TEXT NOT NULL,
    snapshot_at TIMESTAMP NOT NULL,
    price_at_snapshot REAL NOT NULL,
    pnl_pct_at_snapshot REAL NOT NULL,
    original_pnl_pct REAL NOT NULL,
    original_status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(pick_id, checkpoint)
);

CREATE INDEX idx_snapshot_pick ON timeline_snapshots (pick_id, checkpoint);
```

## 7. PnL Module (`pnl.py`)

```python
def compute_pnl_pct(entry: float, current: float, direction: str) -> float:
    """Compute PnL percentage for a position."""
    if direction == "SHORT":
        return (entry - current) / entry * 100
    return (current - entry) / entry * 100

def apply_funding_adjustment(pnl: float, funding_rate: float, hours_held: float) -> float:
    """Optional: adjust PnL for funding rate exposure (configurable flag)."""
    return pnl - (funding_rate * hours_held)
```

## 8. Run Logic (every 30 minutes)

### Phase 1: Scan (`--scan`)
- Read all 5 engine pick files via adapters
- Filter out excluded symbols (SUI)
- For each new pick not yet in DB → compute distance-based opposite TP/SL → insert as ACTIVE
- Bulk insert for efficiency

### Phase 2: Timeline Snapshots (`--snapshot`)
- Query all ACTIVE picks
- For each, check age against checkpoints (1h, 4h, 12h, 24h)
- If checkpoint due and not yet recorded → fetch current price → bulk insert snapshots
- Record both opposite PnL and original PnL at each checkpoint

### Phase 3: Close (`--close`)
- For ACTIVE picks where `expiration_at <= now()` → close as EXPIRED
- For ACTIVE picks: fetch current price, check if TP/SL hit
  - If price crossed both TP and SL in same interval → TP wins (documented rule)
- Record close_price and final pnl_pct

### Phase 4: Discord (`--notify`)
- Post to `#paper-trade` webhook
- One embed per engine that had activity (new picks, closures, or snapshots)
- Summary embed with all 5 portfolios
- Truncate pick lists if embed exceeds 6000 chars ("+ N more")
- Retry on 429 with exponential backoff (max 3 retries)

## 9. Discord Embed Format

### Per-Engine Embed

```
🔄 Opposite Day — Alpha Engine Portfolio
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Scorecard: 12W / 5L (70.6% WR) | PF: 1.83

🆕 New Opposite Picks:
  SHORT BTCUSDT @ $67,544 (flipped from LONG)
  TP: $63,011 | SL: $73,960

📈 Timeline Performance (avg PnL):
  1h:  +0.42% 🟢  (original: -0.38%)
  4h:  +0.81% 🟢  (original: -0.72%)
  12h: +0.23% 🟢  (original: -0.19%)
  24h: -0.15% 🔴  (original: +0.22%)

✅ Closed: ETHUSDT SHORT → TP HIT +2.3%
❌ Closed: SOLUSDT LONG → SL HIT -1.1%
```

### Summary Embed

```
🏆 Opposite Day — All Portfolios Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Engine          | WR    | PF   | Best Window
Predictions     | 68.2% | 1.72 | 4h
KIMI            | 55.0% | 1.21 | 1h
Alpha           | 70.6% | 1.83 | 12h
Signal Engine   | 62.5% | 1.45 | 4h
Cross-Agg       | 48.0% | 0.95 | 1h

Total Picks: 47 | Overall WR: 62.3%
```

## 10. GitHub Actions Workflow

**File:** `.github/workflows/opposite-day.yml`
**Schedule:** Every 30 minutes (`cron: '*/30 * * * *'`)
**Triggers:** schedule + workflow_dispatch (manual)
**Timeout:** 15 minutes

**Steps:**
1. Checkout repo
2. Setup Python 3.11
3. Install deps (requests)
4. Run `python -m sandbox.run --scan --snapshot --close --notify`
5. Commit & push `sandbox/data/opposite_day.db` changes

**Secrets needed:**
- `DISCORD_PAPER_TRADE_WEBHOOK` — #paper-trade channel webhook

## 11. Price Fetching

**Primary:** Binance public ticker (`/api/v3/ticker/price`) — no API key, reliable, supports all USDT pairs.
**Fallback:** CoinGecko public API (for non-Binance symbols).

Batch all symbols into a single request where possible.

## 12. Testing

1. **Unit tests** — mock JSON files per adapter, assert NormalizedPick output matches schema
2. **Integration test** — synthetic picks → in-memory SQLite → verify snapshots and TP/SL logic
3. **Dry-run mode** — `--dry-run` flag that does everything except Discord posting

## 13. Exclusions

- SUI excluded from predictions adapter (only 3 predictions)
- Picks with no entry_price or missing direction are skipped
- Duplicate picks (same pick_id) deduplicated at DB level (UNIQUE constraint)
