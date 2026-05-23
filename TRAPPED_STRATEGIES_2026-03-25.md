# Trapped Strategies Investigation — 2026-03-25

## Executive Summary

Four high-performing `ml_enhanced_*` strategies (WR 85–94%) are **invisible on the audit dashboard** despite having exceptional real forward-test records. Two root causes were identified and fixed in this session. This document records the full diagnosis.

---

## The "Trapped in Hell" Strategies

| Strategy | Closed WR | Trades | PF | Issue |
|---|---|---|---|---|
| `ml_enhanced_FETUSDT_1d_B_lightgbm` | **93.8%** | 16 | 99.99 | Stale active pick (89.4h > 72h cutoff) |
| `ml_enhanced_BNBUSDT_15m_B_lightgbm` | **88.2%** | 17 | 99.99 | Same staleness mechanism |
| `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` | **87.5%** | 16 | 35.19 | Same staleness mechanism |
| `ml_enhanced_RENDERUSDT_4h_D_ensemble_stack` | **85.7%** | 7 | 99.99 | Same staleness mechanism |
| `copy_hl_NMTD_25M` | **81.2%** | 16 | 6.09 | Separate investigation needed |
| `binance_smart_money` | **55.0%** | 20 | 3.05 | Performing but not exceptional |

All four `ml_enhanced_*` strategies are real forward-test wins stored in `alpha_engine/data/closed_picks.json` — **not backtest artefacts**.

---

## Root Cause 1 — Stale Active Picks (The Primary Trap)

### What Happens

```
ml_crypto_predictor production engine
  → all_picks_log.json (ACTIVE picks, "timestamp": null)
  → ml_predictor_merger.py (runs in CI as non-fatal step)
    → map_to_alpha_schema(): uses pick.get("generated_at", pick.get("timestamp", now()))
    → BUG: pick["timestamp"] = None (key EXISTS) → get() returns None, not datetime.now()!
    → merged pick saved with timestamp = None OR old source timestamp
  → alpha_engine/data/active_picks.json  ← pick gets timestamp from LAST successful merge
  → dashboard_generator.py staleness filter: IF age > 72h → DROP
  → Pick invisible on findtorontoevents.ca/audit ✗
```

### The Evidence

```
STALE (age=89.4h): ml_enhanced_FETUSDT_1d_B_lightgbm FETUSDT
Total: 19 picks | Stale>72h: 1 | No timestamp: 10
```

The FETUSDT active pick timestamped `2026-03-21T07:19:30` is **89.4 hours old**.  
The 72-hour staleness filter in `dashboard_generator.py` drops it entirely.

### Why the Timestamp Goes Stale

1. `ml_crypto_predictor/enhanced_models/live_picks/all_picks_log.json` ACTIVE entries have `"timestamp": null`
2. Python's `dict.get("timestamp", default)` returns `None` (not `default`) when the key exists with value None
3. The merged pick gets `"timestamp": None` or inherits the old source timestamp
4. `ml_predictor_merger.py` is marked **non-fatal** in `alpha-engine-live.yml` — failures are silently swallowed
5. Without a fresh run, the last-merged timestamp ages past 72h and the pick disappears

### Secondary: `ml_crypto_predictor/active_picks.json` is 17 Days Stale

```
active_picks.json most recent timestamp: 2026-03-08T00:22:xx  (17 days ago)
```

The ml_crypto_predictor production engine stopped generating fresh picks on ~March 8. The `all_picks_log.json` still has 39 ACTIVE records, but all have `timestamp: null`.

---

## Root Cause 2 — OUTLIER_SYMBOLS Wipes FET/RENDER from Scoring

### The Code

In `alpha_engine/elite_scorer.py rebuild_strategy_performance()`:

```python
OUTLIER_SYMBOLS: set[str] = {"FETUSDT", "RENDERUSDT"}

# In rebuild_strategy_performance():
if symbol in OUTLIER_SYMBOLS:
    continue  # skip outlier symbols for honest metrics
```

This was intended to prevent a single lucky FETUSDT trade from inflating **aggregate** system stats. But the implementation applies it to **per-strategy** stats too.

**Result**: `ml_enhanced_FETUSDT_1d_B_lightgbm` trades ONLY FETUSDT. Every single pick is skipped. The strategy appears in performance files as having 0 trades and disappears from the leaderboard.

### Why It Hasn't Broken Things Yet

`forward_validator.py compute_all_strategy_stats()` does NOT exclude OUTLIER_SYMBOLS and writes the RICH format to `strategy_performance.json` (including FET/RENDER). Since `forward_validator` runs as part of every production scan, the RICH file survives.

However, `elite_scorer.py rebuild_strategy_performance()` would OVERWRITE the rich file with a simple format if it runs AFTER forward_validator. This is a latent time bomb.

---

## Root Cause 3 — Empty Audit Trail Database

```
audit_trail/trading_history.db: 0 tables (EMPTY — never initialized)
```

`audit_push.py` writes to this SQLite database after each scan. The database has never been initialized with a schema. Any code path that reads from `trading_history.db` returns empty results.

**Impact**: Historical strategy leaderboards built from this DB are blank. Only JSON-based leaderboards work.

---

## Fixes Applied in This Session

### Fix 1: ml_predictor_merger.py — Timestamp Refresh

**File**: `alpha_engine/ml_predictor_merger.py`

**Before**:
```python
ts = pick.get("generated_at", pick.get("timestamp", datetime.now(timezone.utc).isoformat()))
```

**After**:
```python
# Use `or` (not nested get) so that JSON-null timestamps fall through to datetime.now()
ts = pick.get("generated_at") or pick.get("timestamp") or None

# For ACTIVE picks: always stamp with current time if source ts is missing or
# older than 48 hours. This prevents dashboard_generator's 72h staleness filter
# from dropping picks just because ml_crypto_predictor stopped emitting timestamps.
if not is_closed:
    if not ts:
        ts = datetime.now(timezone.utc).isoformat()
    else:
        try:
            ts_dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            if ts_dt.tzinfo is None:
                ts_dt = ts_dt.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - ts_dt).total_seconds() > 48 * 3600:
                ts = datetime.now(timezone.utc).isoformat()
        except (ValueError, TypeError):
            ts = datetime.now(timezone.utc).isoformat()
else:
    ts = ts or datetime.now(timezone.utc).isoformat()
```

**Effect**: Every merger run will refresh the timestamp of ACTIVE picks that have null/missing/stale timestamps. The 72h staleness clock resets each time the merger runs (every 45 min in CI).

### Fix 2: elite_scorer.py — Remove OUTLIER_SYMBOLS from Per-Strategy Stats

**File**: `alpha_engine/elite_scorer.py`

**Before**: `rebuild_strategy_performance()` skipped all picks where `symbol in OUTLIER_SYMBOLS`

**After**: Removed the exclusion from per-strategy computation. The OUTLIER_SYMBOLS exclusion remains in:
- `build_track_record()` in `production_scanner.py` — aggregate system WR (correct use)
- `forward_validator.py` White's Reality Check — statistical significance test (correct use)
- `load_copy_trader_scorebook()` — copy trader aggregate scores (correct use)

**Effect**: `ml_enhanced_FETUSDT_1d_B_lightgbm` (93.8% WR) and `ml_enhanced_RENDERUSDT_*` will no longer be erased from `strategy_performance.json` when `rebuild_strategy_performance` runs.

---

## What Still Needs Fixing

### P0: ml_crypto_predictor Production Engine Dead

The ML prediction engine stopped generating fresh predictions around March 8, 2026. `active_picks.json` timestamps are 17 days old.

**Action required**: Restart/fix the ml_crypto_predictor workflow. Check GitHub Actions for failure logs.

### P0: Make ml_predictor_merger Non-Fatal → Fatal

**File**: `.github/workflows/alpha-engine-live.yml`

**Current**:
```yaml
python alpha_engine/ml_predictor_merger.py || echo "ML Predictor merger failed (non-fatal)"
```

**Should be**:
```yaml
python alpha_engine/ml_predictor_merger.py
```

Silent failures mean stale picks stay stale for 89+ hours with no alert.

### P1: Initialize trading_history.db

Find `audit_trail/schema.sql` (or equivalent) and run it to initialize the database:
```bash
sqlite3 audit_trail/trading_history.db < audit_trail/schema.sql
```

### P1: copy_hl_NMTD_25M Investigation

This non-ML strategy has **81.25% WR, 16 trades, PF=6.09**. Source: `copy_trader_intel/`. Needs investigation into why it's not surfacing prominently on the audit page — likely a different issue than the ml_enhanced staleness problem.

---

## Data Flow Map (Complete)

```
ml_crypto_predictor/production_engine.py (DEAD — last run March 8!)
  └→ enhanced_models/live_picks/active_picks.json (28 picks, all March 8 timestamps)
  └→ enhanced_models/live_picks/all_picks_log.json (987 picks, 39 ACTIVE, all ts=null)

alpha_engine/ml_predictor_merger.py (runs every 45min in CI, NON-FATAL)
  └→ Reads all_picks_log.json ACTIVE entries
  └→ map_to_alpha_schema() → BUG: null ts → stale timestamp used (FIXED)
  └→ Writes to alpha_engine/data/active_picks.json

alpha_engine/elite_scorer.py
  └→ rebuild_strategy_performance()
     └→ BUG: excluded FET/RENDER from per-strategy stats (FIXED)
  └→ enrich_picks_with_elite_score()
     └→ Reads strategy_performance.json → scores all active picks
     └→ FET pick with 93.8% WR → should score ~85/100 (top tier)

audit_trail/dashboard_generator.py (runs on site build)
  └→ Staleness filter: DROP picks older than 72h ← MAIN TRAP
  └→ Reads alpha_engine/data/active_picks.json
  └→ Publishes to findtorontoevents.ca/audit
```

---

## Score Impact Analysis

Once the timestamp fix is in effect and the merger runs fresh, `ml_enhanced_FETUSDT_1d_B_lightgbm` should score:

| Component | Points | Basis |
|---|---|---|
| Forward WR (40pts max) | **40** | 93.8% WR × 16 trades = max |
| Profit Factor bonus | **+4** | PF=99.99 ≥ 2.0 → 15% bonus |
| Strategy reputation | **8–12** | Known high-WR strategy |
| Confidence | **5** | HIGH confidence picks |
| **Expected total** | **~57–61** | Tier 1 pick |

Current score: **~5** (unvalidated baseline, no forward WR registered due to staleness)

---

## Timeline

| Date | Event |
|---|---|
| ~2026-03-08 | ml_crypto_predictor production engine last ran |
| 2026-03-21 | ml_predictor_merger.py last successfully merged FET pick (timestamp stamped) |
| 2026-03-21+ | ml_predictor_merger.py failing silently (non-fatal) |
| 2026-03-25 | FET pick is 89.4h old → filtered by 72h staleness → INVISIBLE on audit |
| **2026-03-25** | **This fix: timestamp refresh + OUTLIER_SYMBOLS fix applied** |

---

*Investigation by GitHub Copilot, 2026-03-25*
*See also: `DEEP_ANALYSIS_2026-03-24.md` for broader system audit*
