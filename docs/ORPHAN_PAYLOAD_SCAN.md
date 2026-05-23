# Orphan Payload Scan Report

**Date:** 2026-03-25
**Scope:** All JSON files with pick/signal/prediction data across the entire repo
**Files analyzed:** 213 pick-like JSON files
**Result:** 43 orphan files (713 items, ~966 KB of unreferenced data)

---

## Summary

| Category | Count | Notes |
|----------|-------|-------|
| Total pick-like JSON files | 213 | Files with symbol + entry_price fields |
| Integrated (referenced) | 170 | In dashboard_generator, resolver, or .py/.yml |
| **TRUE ORPHANS** | **43** | Not referenced by ANY script or workflow |
| Systems NOT in dashboard | 17 | Active pick files the dashboard ignores |
| Duplicate data found | 3 | multi_asset, KIMI, copy_trader_intel |
| Dormant systems (0 picks) | 10 | Registered but empty |

---

## STEP 1: True Orphan Files

These files contain valid pick data but are NOT read by any Python script, workflow YAML, or dashboard generator.

### HIGH PRIORITY (active/recent data being lost)

| File | Items | Latest Timestamp | Size | Verdict |
|------|-------|-------------------|------|---------|
| `alpha_engine/data/momentum_tracker_picks.json` | 9 | 2026-03-25T15:00 | 9.2 KB | **INTEGRATE** - actively generated, fresh data |
| `alpha_engine/data/paper_portfolio_cbc.json` | 19 | 2026-03-23T19:03 | 9.2 KB | **INTEGRATE** - recent paper portfolio |
| `alpha_engine/data/paper_portfolio_v2.json` | 8 | 2026-03-23T17:53 | 3.9 KB | **INTEGRATE** - recent paper portfolio |
| `alpha_engine/data/live_scan_now.json` | 25 | N/A | 14.7 KB | **REVIEW** - may be transient scan output |

### MEDIUM PRIORITY (historical/snapshot data)

| File | Items | Latest Timestamp | Size | Verdict |
|------|-------|-------------------|------|---------|
| `updates/data/claude_ml_picks.json` | 196 | N/A | 427.6 KB | DEAD DATA - updates page display artifact |
| `updates/data/claude_ml_history.json` | 133 | N/A | 265.4 KB | DEAD DATA - updates page display artifact |
| `updates/data/antigravity_ml_pick_history.json` | 133 | N/A | 26.6 KB | DEAD DATA - updates page display artifact |
| `updates/data/antigravity_ml_picks.json` | 10 | N/A | 8.2 KB | DEAD DATA - updates page display artifact |
| `updates/data/cursor_ml_history.json` | 9 | N/A | 13.6 KB | DEAD DATA - updates page display artifact |
| `updates/data/cursor_ml_picks.json` | 1 | N/A | 1.6 KB | DEAD DATA - updates page display artifact |
| `updates/data/antigravity_ml_performance_summary.json` | 4 | N/A | 2.3 KB | DEAD DATA - updates page display artifact |

### LOW PRIORITY (stale/backup/test data)

| File | Items | Latest Timestamp | Size | Verdict |
|------|-------|-------------------|------|---------|
| `STOCKS/competition/forward_picks_backup.json` | 51 | 2026-02-16 | 41.8 KB | CLEANUP - stale backup |
| `ml_battleground/system_a_filter/data/closed_picks_pre_20260225.json` | 15 | 2026-02-25 | 19.6 KB | CLEANUP - archive |
| `ml_battleground/system_b_regime/data/closed_picks_pre_20260225.json` | 13 | 2026-02-25 | 18.8 KB | CLEANUP - archive |
| `ml_battleground/system_c_deeplearn/data/closed_picks_pre_20260225.json` | 5 | 2026-02-23 | 5.9 KB | CLEANUP - archive |
| `genome/results/test_picks.json` | 2 | N/A | 4.0 KB | CLEANUP - test artifact |
| `genome/data/kimi_top_3_live_picks.json` | 3 | N/A | 3.1 KB | CLEANUP - duplicate of audit_dashboard version |
| `battleground/incubator/forward_signals/smc_fvg_signals.json` | 3 | N/A | 2.1 KB | CLEANUP - stale incubator experiment |
| `alpha_engine/data/_okx_cache_*.json` (x2) | 1 each | N/A | 0.1 KB each | CLEANUP - API cache artifacts |

### AUDIT DASHBOARD ROUND PICKS (20 files, all orphans)

These are historical "top picks" snapshots from AI challenge rounds. They are not consumed by any script.

| Pattern | Files | Items Each | Verdict |
|---------|-------|------------|---------|
| `audit_dashboard/data/*_top_picks_round3.json` | 6 | 3 | ARCHIVE or CLEANUP |
| `audit_dashboard/data/*_top_picks_round4.json` | 6 | 3 | ARCHIVE or CLEANUP |
| `audit_dashboard/data/*_top_picks_round5.json` | 6 | 3 | ARCHIVE or CLEANUP |
| `audit_dashboard/data/*_top_picks_phase2.json` | 2 | 3 | ARCHIVE or CLEANUP |

---

## STEP 2: Systems NOT in dashboard_generator.py JSON_PICK_SOURCES

These systems actively write pick data, but the dashboard does NOT read it. Picks are invisible to the audit trail.

### CRITICAL GAPS (should be added to JSON_PICK_SOURCES)

| System | File | Active Items | Last Updated | Impact |
|--------|------|-------------|--------------|--------|
| **copy_trader_intel** | `copy_trader_intel/data/active_picks.json` | 39 | 2026-03-24 | Large system, actively scanning, completely invisible |
| **copy_trader_intel consensus** | `copy_trader_intel/data/consensus_active_picks.json` | 17 | N/A | Cross-exchange consensus picks ignored |
| **copy_trader_intel clones** | `copy_trader_intel/data/clone_active_picks.json` | 40 | 2026-03-19 | Clone trader signals ignored |
| **copy_trader_intel highscore** | `copy_trader_intel/data/highscore_active_picks.json` | 19 | 2026-03-19 | Top-rated trader picks ignored |
| **smart_money** | `smart_money/data/active_picks.json` | 4 | 2026-03-25 | Active and recent |
| **prediction_market_agents** | `prediction_market_agents/data/whale_signals.json` | 5 | 2026-03-25 | ZERO external references |
| **prediction_market_agents** | `prediction_market_agents/data/consensus_signals.json` | 2 | 2026-03-25 | ZERO external references |

### MODERATE GAPS (genome revival systems partially missing)

| System | File | Items | Notes |
|--------|------|-------|-------|
| revival_breakout_spike | `genome/data/revival_breakout_spike_picks.json` | 12 | In resolver but NOT in dashboard |
| revival_crypto_gainer_ml | `genome/data/revival_crypto_gainer_ml_picks.json` | 18 | In resolver but NOT in dashboard |
| revival_ml_system_b_regime | `genome/data/revival_ml_system_b_regime_picks.json` | 17 | In resolver but NOT in dashboard |
| revival_ml_system_c_deeplearn | `genome/data/revival_ml_system_c_deeplearn_picks.json` | 20 | In resolver but NOT in dashboard |
| trusted_genome | `genome/data/trusted_genome_picks_live.json` | 25 | Referenced by scripts but not dashboard |

### CLOSED PICK FILES NOT IN DASHBOARD (losing win/loss history)

| File | Closed Items | Impact |
|------|-------------|--------|
| `battleground/data/luxalgo_closed_picks.json` | 312 | **BIG** - LuxAlgo is active, 312 closed results invisible |
| `multi_asset/data/multi_asset_closed.json` | 105 | 105 closed multi-asset results invisible |
| `rapid_fire_data/closed_picks.json` | 10 | Minor |

---

## STEP 3: Cross-System Bridge Gaps

### prediction_market_agents --> alpha_engine: COMPLETELY DISCONNECTED
- `prediction_market_agents/` writes to its own `data/` directory
- **ZERO external scripts reference** `prediction_market_agents`
- Has active whale signals, consensus signals, momentum signals
- **Action:** Add bridge to dashboard_generator.py or have alpha_engine consume these

### copy_trader_intel --> dashboard: PARTIALLY BRIDGED
- The alpha_engine has `copy_trader_bridge.py` and `cta_bridge.py`
- But the **dashboard_generator.py** does NOT list copy_trader_intel in JSON_PICK_SOURCES
- 39 active picks + 455 sub-file picks are tracked internally but invisible to audit trail
- **Action:** Add `copy_trader_intel` to JSON_PICK_SOURCES

### ml_crypto_predictor --> alpha_engine: RECENTLY FIXED
- The reviver bridge was just implemented
- `ml_crypto_predictor/enhanced_models/live_picks/active_picks.json` IS in both dashboard_generator and resolver
- **Status:** Bridge is working

### smart_money --> dashboard: MISSING FROM DASHBOARD
- Referenced by 75 scripts (heavily used for analysis)
- But `smart_money/data/active_picks.json` is NOT in JSON_PICK_SOURCES
- **Action:** Add to JSON_PICK_SOURCES

---

## STEP 4: Duplicate Data

### 1. multi_asset FULL DUPLICATION
- `multi_asset/data/active_picks.json` (76 items) and `multi_asset/data/multi_asset_picks.json` (76 items)
- **69 of 76 picks overlap** (91% duplication)
- Only `active_picks.json` is in the resolver; `multi_asset_picks.json` is referenced by other scripts
- **Risk:** Double-counting if both get added to dashboard

### 2. KIMI FULL DUPLICATION
- `KIMI_RISEOFTHECLAW/data/active_picks.json` (15 items) and `riseoftheclaw/data/active_picks.json` (15 items)
- **100% overlap** - identical data in two locations
- Both are in dashboard_generator (different system names: `kimi_riseoftheclaw` and `riseoftheclaw`)
- **Risk:** All 15 KIMI picks are double-counted in the dashboard

### 3. copy_trader_intel PARTIAL DUPLICATION
- `active_picks.json` (39 items) overlaps with 13 of the 455 sub-file picks
- This is expected (active_picks is a curated subset of sub-files)
- **Risk:** Low, but if multiple sub-files are added to dashboard, dedup needed

---

## STEP 5: Dormant Systems (Registered but Empty)

These are in JSON_PICK_SOURCES but have 0 active picks:

| System | Path | Status |
|--------|------|--------|
| breakout_a_sr | breakout_arena/approach_a_sr_breakout/data/active_picks.json | Empty |
| breakout_c_spike | breakout_arena/approach_c_spike_reverse/data/active_picks.json | Empty |
| crypto_signal_engine | crypto_signal_engine/data/active_picks.json | Empty |
| ml_bg_system_a | ml_battleground/system_a_filter/data/active_picks.json | Empty |
| ml_bg_system_b | ml_battleground/system_b_regime/data/active_picks.json | Empty |
| ml_bg_system_c | ml_battleground/system_c_deeplearn/data/active_picks.json | Empty |
| ml_bg_system_d | ml_battleground/system_d_carry/data/active_picks.json | Empty |
| ml_bg_system_e | ml_battleground/system_e_momentum/data/active_picks.json | Empty |
| ml_bg_ensemble | ml_battleground/ensemble_data/active_picks.json | Empty |
| coinglass | coinglass_strategies/data/active_picks.json | Empty |

---

## Recommended Actions

### Immediate (data being lost right now)
1. **Add to dashboard_generator.py JSON_PICK_SOURCES:**
   - `copy_trader_intel/data/active_picks.json` (39 picks)
   - `smart_money/data/active_picks.json` (4 picks)
   - `prediction_market_agents/data/whale_signals.json` (5 picks)
   - `prediction_market_agents/data/consensus_signals.json` (2 picks)
   - `alpha_engine/data/momentum_tracker_picks.json` (9 picks)
   - `genome/data/revival_breakout_spike_picks.json` (12 picks)
   - `genome/data/revival_crypto_gainer_ml_picks.json` (18 picks)
   - `genome/data/revival_ml_system_b_regime_picks.json` (17 picks)
   - `genome/data/revival_ml_system_c_deeplearn_picks.json` (20 picks)

2. **Add CLOSED pick files to dashboard for win/loss tracking:**
   - `battleground/data/luxalgo_closed_picks.json` (312 results!)
   - `multi_asset/data/multi_asset_closed.json` (105 results)

3. **Fix KIMI double-counting:**
   - `KIMI_RISEOFTHECLAW/data/active_picks.json` and `riseoftheclaw/data/active_picks.json` are 100% identical
   - Remove one from JSON_PICK_SOURCES or deduplicate in the loader

### Cleanup (safe to delete)
- `alpha_engine/data/_okx_cache_*.json` - API cache artifacts
- `genome/results/test_picks.json` - test data
- `STOCKS/competition/forward_picks_backup.json` - stale backup
- `ml_battleground/system_*/data/closed_picks_pre_20260225.json` (3 files) - pre-reset archives
- 20 `audit_dashboard/data/*_top_picks_round*.json` files - historical snapshots no script reads
- 7 `updates/data/*_ml_*.json` files - page display artifacts, never consumed

### Review
- `alpha_engine/data/live_scan_now.json` (25 items) - determine if this is transient or should be integrated
- `alpha_engine/data/paper_portfolio_cbc.json` / `paper_portfolio_v2.json` - paper portfolios may be valuable
- `multi_asset/data/multi_asset_picks.json` duplication with `active_picks.json` - pick one canonical source
