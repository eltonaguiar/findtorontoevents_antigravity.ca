# Combined Confidence Strategy — Implementation

**Date:** 2026-04-18  
**Branch:** `feature/combined-confidence-strategy`  
**Files changed:** 3

## What Was Broken / Missing

The audit dashboard had prediction market (PM) signals and copy-trader picks flowing separately, but there was no unified scoring system that blended **trader track record** with **prediction market probability** into a single confidence metric. Position sizing was uniform regardless of conviction level.

## What Changed

### 1. New Module: `alpha_engine/combined_confidence_strategy.py`

Implements the Combined Confidence Score (CS) framework:

- **Formula:** `CS = (TE + MP) / 2`
  - `TE = (WinRate - 0.5) * 2` — Trader Edge, maps 50-100% WR to 0.0-1.0
  - `MP` = prediction market probability (already 0-1)
- **Thresholds:**
  - `CS >= 0.70` → **HIGH** confidence: full position size (1.0x)
  - `0.55 <= CS < 0.70` → **MEDIUM**: reduced size (0.6x), SL tightened 7.5%
  - `CS < 0.55` → **LOW**: skip (not tradeable)
- **Inputs:**
  - `alpha_engine/data/prediction_market_picks.json` (PM consensus picks)
  - `copy_trader_intel/data/non_crypto_consensus_picks.json` (copy-trader picks)
  - `alpha_engine/data/active_picks.json` (historical win rates)
- **Outputs:**
  - `alpha_engine/data/combined_confidence_picks.json` (standalone)
  - Merges into `alpha_engine/data/active_picks.json` (audit dashboard pipeline)

### 2. GHA Workflow: `.github/workflows/audit-dashboard.yml`

- Added `combined_confidence_strategy.py` as a step after PM orchestrator
- Added push trigger path for `alpha_engine/combined_confidence_strategy.py`

### 3. Strategy Registration: `alpha_engine/config.py`

- Registered `combined_confidence` in `STRATEGY_FAMILIES` under `"sentiment"` family

## How It Was Verified

- `py_compile` passed on all modified Python files
- Strategy registered in `STRATEGY_FAMILIES` dict
- Workflow step correctly placed after PM pipeline, before pick resolution
- Push trigger path added (narrow, source-only — no data file globs)
