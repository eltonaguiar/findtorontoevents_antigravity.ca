# ML Scores & Feature Persistence — Edge Tracking Integration

**Date:** 2026-04-22  
**PR:** `copilot/ml-feature-edge-tracking-20260422`

## What Was Broken

1. `alpha_engine/feature_populator.py` computes 18+ technical indicators (RSI, ATR, volume ratio, VWAP dev, MACD, order-book imbalance, etc.) at scan time but **none were persisted** — they existed only as in-memory dict values, making post-hoc edge analysis impossible.

2. ML scores (`elite_score`, `smart_score`, `darwin_score_v2`, `ml_composite_score`) were computed but **not stored in the audit trail DB**, so we could not validate whether higher scores predicted better outcomes. The `SMART_PICKS_MIN_ML_SCORE` gate was disabled at `0.0` because the data to validate it didn't exist.

3. `strategy_stats` tracked win rate per strategy globally but not per **symbol × strategy** combination, hiding cases where a strategy works well on BTC but poorly on altcoins (or vice versa).

## What Changed

### New files
- **`audit_trail/pick_feature_store.py`** — persists 25 ML score + technical feature columns for every pick. Includes MySQL `at_pick_features` side-table DDL and SQLite migration.
- **`audit_trail/symbol_strategy_tracker.py`** — maintains `symbol_strategy_stats` table with running-average win rates per symbol + strategy + direction combination.
- **`audit_trail/feature_edge_analyzer.py`** — CLI tool and library that buckets features and computes win rate per bucket, writing results to `feature_edge_snapshots`. Answers "does RSI 30–40 win more often than RSI 60–70?"

### Schema updated
- **`audit_trail/schema.sql`** — added `symbol_strategy_stats` and `feature_edge_snapshots` table definitions.

## How to Integrate

See `docs/ML_SCORE_FEATURE_PERSISTENCE_EDGE_TRACKING_2026-04-22.md` for the full wiring guide. Minimum wiring:

```python
# dashboard_generator.py — add after calculate_smart_score()
from audit_trail.pick_feature_store import store_pick_features, run_sqlite_migration
run_sqlite_migration(audit_conn)
store_pick_features(pick, audit_conn)

# universal_pick_resolver.py — add after pick closes
from audit_trail.symbol_strategy_tracker import update_from_closed_pick
update_from_closed_pick(closed_pick, audit_conn)
```

## How It Was Verified

- `py_compile` syntax check passes on all three new files
- Schema SQL reviewed for idempotency (all `CREATE TABLE IF NOT EXISTS`, migration uses try/except for duplicate column errors)
- All functions are defensively coded to skip if columns not yet in schema
