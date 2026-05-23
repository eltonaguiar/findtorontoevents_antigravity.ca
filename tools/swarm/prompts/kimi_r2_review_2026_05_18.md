# Kimi R2 PR Specs Review — 2026-05-18

## Context
Kimi (AI coding agent) produced a corrected second-pass analysis (Round 2) for findtorontoevents_antigravity.ca.
This session reviews 5 actionable PR specs written for the quality_gates pipeline.

## Live System Reality (verified from repo)
- `quality_gates.py`: 9,541 lines — core gate logic in `passes_active_gate()`
- `pick_lifecycle_logger.py`: NEW this session — 3-table SQLite (pick_lifecycle_log, filter_event_log, gate_pass_log)
- `pick_provenance_index.py`: NEW this session — traces pick lineage JSON→emitter→GitHub Action
- **Non-existent files Kimi referenced**: `data_pipeline/cot_ingestor.py`, `charter_slippage.py`, `pick_evaluator.py`, `alembic/`, `config/trading.yaml`, `config/asset_class_limits.yaml`, `crypto_quarantine.json`
- **Already DONE**: PR-02 (ETF VIX gate) shipped as commit 18a2d4ee2d this session

## PR Specs to Review (reports/ in repo)

### PR-01: COMMODITY COT Lag + CT=F 35% Concentration Cap
Key claims:
- COT 3-day publication lag exists (CFTC publishes Friday, data as-of Tuesday)
- CT=F concentration = 84.9% of COMMODITY class
- Headline WR=87% on CT=F collapses to 30% with lag correction
- Proposes: `data_pipeline/cot_ingestor.py` fix + alembic migration + `position_sizer.py` 35% cap

**Validation questions:**
1. Does `data_pipeline/cot_ingestor.py` exist? (Suspected: NO — wrong file)
2. Does `quality_gates.py` have a `get_cot_signal()` function or equivalent?
3. Is CT=F concentration really 84.9%? Check `pf_registry.json` or `audit_trail/data/`
4. Is the 35% cap for `position_sizer.py` where that file exists?

### PR-02: ETF VIX<25 Gate
**SKIP — already implemented this session (commit 18a2d4ee2d)**

### PR-03: Post-Cost Expectancy Hard Gate
Key claims:
- M-069 slippage model is advisory only in `charter_slippage.py`
- Proposes promoting to hard gate via `passes_post_cost_expectancy(pick)` function
- Shadow mode rollout → hard reject after 2 weeks
- Claims ~$1.17M/year in negative-expectancy trades (unverifiable)

**Validation questions:**
1. Does `charter_slippage.py` exist? Does `deduct_slippage()` exist in it?
2. Is there an existing slippage gate in `quality_gates.py`? (Session BM implemented M-041 slippage shadow gate)
3. Where is transaction cost data available? (Source file TBD)

### PR-04: ML-Enhanced Quarantine for CRYPTO
Key claims:
- 147 of 149 `ml_enhanced_*` strategy variants unquarantined
- Bottom 136 variants PF=0.63 aggregate
- Top 3 whitelisted: FETUSDT_1d_B (PF=9.25), INJUSDT_1d_B (PF=41), BNBUSDT_15m_B (PF=52.6)
- Proposes: restructure `crypto_quarantine.json` to allowlist mode

**Validation questions:**
1. Do strategies named `FETUSDT_1d_B`, `INJUSDT_1d_B`, `BNBUSDT_15m_B` actually exist in active_picks.json?
   (Actual format is like `ml_enhanced_LTCUSDT_4h_A_xgboost`)
2. Does `crypto_quarantine.json` exist in the repo?
3. Is there a `BLOCKED_ASSET_STRATEGY_PAIRS` entry for ml_enhanced strategies already?
4. What does per-variant PF analysis on closed_picks.json show for ml_enhanced variants?

### PR-05: Pick What-If Query Endpoint
Key claims:
- Add REST endpoint `/api/picks/what-if` to existing pick lifecycle tables
- Simulate which gate would reject a hypothetical pick
- Build on existing pick_lifecycle_log.py (SQLite)

**Validation questions:**
1. Is there an existing REST API server in the repo? (Where? Flask/FastAPI?)
2. Would a `passes_active_gate()` dry-run function be simpler than a full REST endpoint?
3. Is the pick_lifecycle_log database populated enough to answer what-if queries?

## Expected Output Format
For each PR: IMPLEMENT/DEFER/MODIFY + EVIDENCE + specific implementation path (correct file + function names).
Identify any new action items.
Overall R2 grade: A/B/C/D.
