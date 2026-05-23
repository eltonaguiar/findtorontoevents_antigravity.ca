# Session Review — 2026-05-17 (Session R)

Senior quant review of session R deliverables.

## Deliverables this session

### 1. White's Reality Check / Hansen's SPA Test (M-065) — commit 915782926d
**New file:** `tools/whites_reality_check.py` (pure numpy, no arch/mlfinlab deps)
**Report:** `reports/whites_reality_check_2026-05-17.md`

**Results (n=24 strategies, min_n=20 resolved picks, n_boot=500):**
- Family-wide edge SURVIVES correction: RC p=0.000, SPA p=0.000
- 9/24 strategies pass SPA:
  - `ml_enhanced_FETUSDT_1d_B_lightgbm`: mean +33.66%/pick ← high variance outlier
  - `ml_enhanced_INJUSDT_1d_B_lightgbm`: mean +15.60%/pick
  - `cot_positioning`: mean +3.28%/pick, n=134 ← confirmed genuine COMMODITY edge
  - `cftc_cot_commercial_signal`: mean +2.97%/pick, n=131 ← confirmed genuine COMMODITY edge
  - `ml_enhanced_RENDERUSDT_*`, `ml_enhanced_DYDXUSDT_*`, `ml_enhanced_STRKUSDT_*`, `ml_enhanced_FETUSDT_15m_*`
- Confirmed losers: `forex_carry_momentum` (-0.41%), `myfxbook_retail_contrarian` (-0.44%), `cta_cross_asset_tsmom` (-0.50%), `futures_momentum` (-2.76%)
- Extreme outliers (data quality concern): `ml_enhanced_APEUSDT_1d_D_ensemble_stack` (-34.23%), `ml_enhanced_TRXUSDT_1d_B_lightgbm` (-67.72%)

### 2. M-062 COT publication gate — confirmed ALREADY DONE
Investigation confirmed `COT_PUBLICATION_LAG_DAYS = 3` already in `alpha_engine/cot_positioning.py` + PR #1140 dedup fix. No new code needed.

### 3. Tests: 4848 passed, 37 skipped, 1 xfailed.

## Session Q review (multi_asset_copytrader FOREX LONG block) — swarm responses

From session Q swarm:
- Q1: Re-evaluate SHORT at n=150 with EURGBP/GBPUSD conditional unlock at n=20/PF≥2.0
- Q2: M-062 already done (verified)
- Q3: M-065 is P1 — implemented this session
- Q4: Direction-block EQUITY scouts at n=10 (0% WR) — current n=2, below threshold

## Swarm Questions

**Q1:** The White's Reality Check shows `ml_enhanced_FETUSDT_1d_B_lightgbm` with mean +33.66%/pick (n=25) and `ml_enhanced_TRXUSDT_1d_B_lightgbm` with mean -67.72%/pick (n=24). These extreme outliers dominate the SPA test statistics and could produce spurious results. Should we:
(A) Run the SPA test excluding outliers (|mean| > 10%/pick)?
(B) Winsorize returns at ±5σ before testing?
(C) Trust the raw results (the test is robust to outliers via bootstrap)?

**Q2:** 9/24 strategies pass SPA but only 24 of 159 strategies have n≥20 resolved picks. The 135 strategies with n<20 cannot be tested. Should we add a "pending_spa" flag to strategies with 5≤n<20 to flag them as untested rather than letting them accumulate unexamined?

**Q3:** The M-061 money_ready_verdict() function (wire DSR+PBO+SPA into one per-class verdict) remains un-built. Given that the individual components exist, what is the minimum viable implementation — just a Python function returning {class: {dsr_ok, pbo_ok, spa_ok, n_ok, verdict}} or does it need to be wired into dashboard_generator.py to be production-useful?

**Q4:** The new `tools/reconcile_pf_registry.py` was just merged (not our work — another agent). Should we audit this new file before it runs in CI? It modifies `audit_dashboard/data/pf_registry.json` which is a critical dashboard input.
