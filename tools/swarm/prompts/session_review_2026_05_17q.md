# Session Review — 2026-05-17 (Session Q)

Senior quant review of session Q deliverables.

## Deliverables this session

### 1. FOREX multi_asset_copytrader LONG block (commit 99a92d8d38)
**Action:** Added `("FOREX", "multi_asset_copytrader", "LONG")` to BLOCKED_DIRECTION_TRIPLES.  
**Data:**
- LONG: n=603, WR=10.9%, PF=0.140 — dominated by JPY-cross exposure
  - EURJPY=X: n=154, WR=1.9%, PF=0.025
  - USDJPY=X: n=133, WR=3.0%, PF=0.036
  - GBPJPY=X: n=87, WR=10.3%, PF=0.163
- SHORT: n=93, WR=52.7%, PF=1.351 — positive edge, kept
- Non-JPY LONG winning subset (EURGBP PF=3.437, GBPUSD PF=2.449, AUDUSD PF=1.600) — too small for unlock, watch
**Tests:** 463 passed, 6 skipped.
**Investigation doc:** `reports/multi_asset_copytrader_forex_investigation_2026-05-17.md`

### 2. ml_enhanced_* investigation confirms ACTIVE (not retired)
**Finding:** 36 active picks as of 2026-05-17 — naming migration artifact, NOT dormancy.
**Investigation doc:** `reports/ml_enhanced_retirement_investigation_2026-05-17.md`

### 3. COMMODITY confidence floor corrected to 0.55 (commit e26a0fcad5)
**Correction:** Initial 0.60 floor would have blocked 17.2% of cot_positioning picks (WR=80%/PF=4.94, min conf=0.55). Floor lowered to 0.55.

### 4. PR #1149 merged — /swarm-transcript-scan skill added.

## Key remaining open items (all externally blocked or time-gated)

**Externally blocked:**
- MySQL 655k ghost-row purge — PA console required
- `UEPS_ENABLE_PEAD=1` prod .env — PA console required
- FRED_API_KEY — manual GitHub secret
- DB password rotation — 50webs operator

**Time-gated:**
- quan_engine full autopsy — 2026-05-24 (after MySQL purge)
- CVX/DYDXUSDT/TRXUSDT/XOM probation — 2026-05-30
- CT=F probation review — 2026-06-06
- META_LABEL_GATE_ENFORCE=1 — ~2026-06-16
- B10 (UEPS KPI panel) — ~2026-05-22 (awaiting ≥10 UEPS closed picks)

**Research/future (M-060..M-065):**
- M-062: COT publication-time gate (look-ahead fix for cot_positioning)
- M-061: Unified money_ready_verdict() wiring DSR/PBO/CSCV
- M-060: Confidence calibrator monthly auto-refit + per-class allowlist
- M-064: EQUITY DB↔repo ledger sync (44 repo vs 393 MySQL picks)
- M-065: White's Reality Check / SPA test (family-wise multiple-comparison)

## Swarm Questions

**Q1:** The multi_asset_copytrader SHORT (n=93, WR=52.7%, PF=1.351) is below T2 PF=1.5 floor but positive. Should we set a re-evaluation trigger at n=150 or n=100, and should we proactively watch specific symbols (EURGBP, GBPUSD showing T1 edge on LONG)?

**Q2:** M-062 (COT publication-time gate) patches cot_positioning.py to use COT data only after Fri 15:30 ET. This is a look-ahead bias fix. Given that cot_positioning WR=80%/PF=4.94 is our best COMMODITY edge, should we treat the look-ahead patch as P0 (fix immediately — results could be artificially inflated) or P2 (research quality fix — results are directionally correct even with the timing)?

**Q3:** M-065 (White's Reality Check / SPA test) is the only genuinely new item from the multi-AI roadmap validation. Is this a P1 (implement before considering any asset class money-ready) or P3 (nice-to-have once performance is stable)?

**Q4:** The EQUITY 7d PF=0.62 continues despite blocking price-accel-scout and macd-hidden-div-scout not yet meeting n≥20 kill threshold. At what n should we apply the direction-block-first (not kill) protocol for EQUITY scouts showing 0% WR?
