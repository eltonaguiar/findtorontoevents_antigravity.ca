# P0 Round-Up: Concept Drift, VIX Gate, Volume Cap, Regime Tagging

**Date:** 2026-05-14  
**Session:** Swarm Master Synthesis + Money-Maker-Ready per-asset-class enhancement plan  
**Branch:** `feat/all-picks-log-status-shard-rotation-2026-05-14`

## Changes Made

### 1. quan_engine CRYPTO Volume Cap: 12% → 5%

**File:** `alpha_engine/per_source_volume_cap.py`  
**Why:** Swarm master synthesis identified `quan_engine` as a performance drag on CRYPTO (84% share with 66% loss rate in ML ranker). All three reviewers (DeepSeek, Grok-3, Cerebras) recommended 5% ceiling.  
**Change:** `"quan_engine": {"CRYPTO": 0.12}` → `"quan_engine": {"CRYPTO": 0.05}`  
**Verified:** Module imports clean, cap constant test updated (`0.12` → `0.05`), `test_quan_engine_volume_cap.py` passes (6/6).

### 2. VIX Regime Gate: Enabled by Default

**File:** `audit_trail/vix_regime_gate.py`  
**Why:** VIX regime gate (`VIX<22` filter for EQUITY) was implemented but OFF by default (env default `"0"`). Per `reports/equity_vix_regime_breakthrough_20260513.md`, VIX<22 delivers PF 4.55 / Sharpe 1.98 for EQUITY momentum. Should be ON by default.  
**Change:** `os.environ.get("VIX_REGIME_GATE_ENABLED", "0")` → `os.environ.get("VIX_REGIME_GATE_ENABLED", "1")`  
**Also updated:** Docstring lines 9 and 21 to reflect new default.  
**Verified:** `test_vix_regime_gate.py` (9/9) and `test_vix_yc_combined_gate.py` (11/11) both pass.

### 3. Regime Tagging Silent Bug Fix

**File:** `alpha_engine/production_scanner.py` (line 5607)  
**Why:** The `regime_alignment` field was guarded by `if not _p.get("regime_alignment"):`, meaning picks that already had a stale `regime_alignment` from a prior scan would never get refreshed. The dashboard reported `active_regime_composition.with_regime_data = 0 out of 236 active picks`.  
**Change:** Removed the `if not _p.get("regime_alignment"):` guard — `regime_alignment` is now unconditionally stamped on every pick each scan cycle, ensuring it reflects the current market regime.  
**Verified:** File compiles cleanly (py_compile OK).

### 4. Concept Drift Auto-Pause: Confirmed Already Active

**File:** `audit_trail/quality_gates.py` (lines 733–767, 4579–4595)  
**Status:** Already implemented and ON by default (`DRIFT_PAUSE_GATE_ENABLED=1`, `DRIFT_PAUSE_RATIO=3.0`). No code change needed.  
**Note:** Current live state KS_D/critical = 6.6× (SEVERE) — gate is actively blocking CRYPTO/FOREX picks.

## Test Results

| Test Suite | Tests | Result |
|-----------|-------|--------|
| `test_vix_regime_gate.py` | 9/9 | ✅ PASS |
| `test_vix_yc_combined_gate.py` | 11/11 | ✅ PASS |
| `test_quan_engine_volume_cap.py` | 6/6 | ✅ PASS |
| **Total** | **26/26** | **✅ ALL PASS** |
