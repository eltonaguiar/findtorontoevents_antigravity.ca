# ML Scores & Feature Persistence — Edge Tracking Integration Plan

**Date:** 2026-04-22  
**Branch:** `copilot/ml-feature-edge-tracking-20260422`  
**Status:** PR open — implementation ready for review

---

## Problem Statement

Our audit dashboard (`findtorontoevents.ca/audit`) tracks pick outcomes but has two significant blind spots:

1. **Features are computed but never stored.** `alpha_engine/feature_populator.py` computes 18 technical indicators (RSI, ATR, VWAP deviation, volume ratio, MACD histogram, order-book imbalance, etc.) at scan time. These are fed to `ml_ranker.py` and then discarded. We cannot answer "do picks with RSI < 35 win more often?" because the RSI at entry is not in any closed-pick record.

2. **High-conviction picks are point-in-time.** The existing "high conviction" classification was built around asset-class-level win rate analysis. It does not track the **symbol × strategy combination** — e.g. that `BTCUSDT + btc_breakout_volume` has a 72% win rate while `BTCUSDT + rsi_hidden_divergence` has 41%.

Additionally, several ML score fields (`ml_composite_score`, `darwin_score_v2`, `elite_score`, `smart_score`) are computed but not persisted in the audit trail, making it impossible to validate whether higher scores predict better outcomes.

---

## What Was Built

### 1. `audit_trail/pick_feature_store.py`

Provides persistence of all ML scores and technical features into the audit trail database.

**Key functions:**
- `run_sqlite_migration(conn)` — idempotent v2 schema migration that adds 25 new columns to `raw_picks`
- `store_pick_features(pick, conn)` — upserts ML + feature values for a pick by ID
- `extract_feature_row(pick)` — normalises pick dict to storable column map

**Columns added to `raw_picks` (SQLite) / `at_pick_features` (MySQL side-table):**

| Column | Source | Example |
|--------|--------|---------|
| `ml_score` | `ml_ranker.py` | 0.73 |
| `elite_score` | `quality_gates.py` | 82.4 |
| `smart_score` | `calculate_smart_score()` | 68.0 |
| `trust_score` | `quality_gates.py` | 7.5 |
| `darwin_score_v2` | `darwin_score_v2_calculator.py` | 71.2 |
| `method_a_score` | scoring pipeline | 85.0 |
| `ml_composite_score` | `smart_picks_engine.py` | 0.61 |
| `wf_verdict` | `walkforward_validator.py` | ELITE |
| `strat_fwd_wr` | forward validator | 0.58 |
| `forward_wr` | pick-level validator | 0.62 |
| `agreement_count` | consensus | 4 |
| `high_conviction` | `high_conviction_gate_passed` | 1 |
| `feat_rsi` | `feature_populator.py` | 38.2 |
| `feat_volume_ratio` | `feature_populator.py` | 1.8 |
| `feat_atr_pct` | `feature_populator.py` | 1.2 |
| `feat_vwap_dev` | `feature_populator.py` | -0.8 |
| `feat_macd_hist` | `feature_populator.py` | 0.003 |
| `feat_btc_corr` | `feature_populator.py` | 0.71 |
| `feat_regime` | `feature_populator.py` | 1 |
| `feat_funding_rate` | `feature_populator.py` | 0.0001 |
| `feat_cs_momentum` | `feature_populator.py` | 0.64 |
| `feat_ob_imbalance` | `feature_populator.py` | 0.12 |
| `feat_stoch_k` | `feature_populator.py` | 42.1 |
| `feat_cci` | `feature_populator.py` | -0.18 |
| `feat_williams_r` | `feature_populator.py` | -0.55 |

**MySQL target:** `at_pick_features` side-table (avoids `ALTER TABLE` on production MySQL).

---

### 2. `audit_trail/symbol_strategy_tracker.py`

Maintains the `symbol_strategy_stats` table — win-rate tracking at the *symbol + strategy* granularity.

**Why this matters over the existing `strategy_stats` table:**

| Table | Granularity | Use case |
|-------|-------------|----------|
| `strategy_stats` | strategy + source_system | Is this strategy good overall? |
| `symbol_strategy_stats` | symbol + strategy + direction | Is BTCUSDT + rsi_divergence long a proven edge? |

**Key functions:**
- `update_from_closed_pick(pick, conn)` — called on every pick close, running-average update
- `rebuild_from_closed_picks(conn)` — full recalc from scratch (idempotent)
- `get_edge_picks(conn, min_win_rate=0.55, min_picks=5)` — query combinations with proven edge
- `get_symbol_strategy_summary(conn)` — summary card data for dashboard

**Schema (`symbol_strategy_stats`):**

```sql
PRIMARY KEY (symbol, strategy, source_system, direction)
-- tracks: total_picks, wins, losses, win_rate, avg_pnl_pct,
--         avg_ml_score, avg_elite_score, avg_rsi, avg_volume_ratio
```

---

### 3. `audit_trail/feature_edge_analyzer.py`

Analyzes which feature value ranges correlate with winning picks. Results are written to `feature_edge_snapshots`.

**Example output:**

```
Feature                Bucket                          N     WR    AvgPnL    Edge
feat_rsi               rsi_30_40                      47  68.1%      4.2%   0.286
feat_volume_ratio      vol_ratio_2.0_3.0              31  71.0%      3.8%   0.270
wf_verdict             wf_verdict_ELITE               89  66.3%      3.9%   0.259
elite_score            elite_score_80_90             142  63.4%      3.5%   0.222
feat_regime            feat_regime_1.0               198  58.2%      2.9%   0.169
feat_funding_rate      funding_-0.01_0               112  56.3%      2.4%   0.135
```

**Features analyzed (15 numeric, 4 categorical):**

- `feat_rsi` — RSI at entry bucketed into 7 ranges (30-40 is the "oversold but not collapsing" zone)
- `feat_volume_ratio` — volume vs 20-bar SMA (>2x often confirms breakouts)
- `feat_atr_pct` — ATR as % of price (low ATR = tight markets, high = volatile)
- `feat_vwap_dev` — distance from VWAP (negative = below fair value)
- `feat_btc_corr` — BTC correlation (high corr = regime-dependent, not independent alpha)
- `feat_regime` — price vs SMA50 trend direction
- `feat_funding_rate` — negative = shorts paying = bullish skew
- `feat_cs_momentum` — cross-sectional rank (top quartile vs bottom)
- `feat_ob_imbalance` — order book bid/ask imbalance
- `feat_macd_hist` — MACD histogram direction
- `ml_score`, `elite_score`, `smart_score`, `trust_score` — do higher scores win more?
- `strat_fwd_wr`, `darwin_score_v2` — forward validation score buckets
- `wf_verdict` — categorical (ELITE/STRONG/VIABLE/DECAYING/WEAK)
- `direction`, `asset_class` — base segmentation

---

### 4. `audit_trail/schema.sql` — v2 additions

Two new tables added at the end of the schema file:
- `symbol_strategy_stats` (described above)
- `feature_edge_snapshots` (edge analysis results)

---

## Integration Steps (for PR reviewers)

### Step 1 — Wire feature persistence into dashboard generator

In `audit_trail/dashboard_generator.py`, after `calculate_smart_score(pick)` is called for each pick:

```python
from audit_trail.pick_feature_store import store_pick_features, run_sqlite_migration

# Near top of generate():
run_sqlite_migration(audit_conn)

# After quality gate evaluation for each pick:
store_pick_features(pick, audit_conn)
```

### Step 2 — Wire symbol-strategy tracker on pick close

In `audit_trail/universal_pick_resolver.py`, after a pick is marked WIN/LOSS:

```python
from audit_trail.symbol_strategy_tracker import update_from_closed_pick
update_from_closed_pick(closed_pick, audit_conn)
```

### Step 3 — Wire edge analyzer at end of dashboard run

In `audit_trail/dashboard_generator.py`, at the end of the generation pass:

```python
from audit_trail.feature_edge_analyzer import run_full_analysis
run_full_analysis(audit_conn)
```

### Step 4 — Enable ML score gate once data exists

Once `ml_score` is reliably persisted (after ~2 weeks of data collection), revisit in `audit_trail/quality_gates.py`:

```python
SMART_PICKS_MIN_ML_SCORE = 0.40  # currently 0.0 (disabled)
```

Validate first by running `feature_edge_analyzer` and confirming `ml_score_40_50` bucket has higher win rate than `ml_score_20_40`.

### Step 5 — Dashboard display (future PR)

- Add "Edge by Feature" tab to `audit_dashboard/template.html` showing `feature_edge_snapshots`
- Add "Symbol × Strategy Win Rates" table (sortable by win rate) showing `symbol_strategy_stats` where `total_picks >= 5`
- Add "ML Score Distribution" histogram comparing open vs closed picks

---

## Key Gaps Addressed

| Gap | Before | After |
|-----|--------|-------|
| RSI/Volume at entry | Not stored, lost after scan | Persisted in `raw_picks.feat_rsi`, `feat_volume_ratio` |
| ML score persistence | Computed, not in DB | Persisted in `raw_picks.ml_score`, `elite_score`, etc. |
| Symbol-level win rate | Strategy-level only | `symbol_strategy_stats` tracks symbol × strategy × direction |
| Feature → outcome correlation | No analysis | `feature_edge_snapshots` computed per dashboard run |
| ML gate validation | Gate disabled (`= 0.0`) | Framework to re-enable once data validates the signal |

---

## Files Changed

| File | Change |
|------|--------|
| `audit_trail/pick_feature_store.py` | **New** — feature persistence helper |
| `audit_trail/symbol_strategy_tracker.py` | **New** — symbol × strategy win rate tracker |
| `audit_trail/feature_edge_analyzer.py` | **New** — feature → outcome edge analysis |
| `audit_trail/schema.sql` | **Updated** — added `symbol_strategy_stats` + `feature_edge_snapshots` tables |
| `docs/ML_SCORE_FEATURE_PERSISTENCE_EDGE_TRACKING_2026-04-22.md` | **New** — this document |
| `updates/2026-04-22-ml-scores-feature-persistence-edge-tracking.md` | **New** — required update note |
