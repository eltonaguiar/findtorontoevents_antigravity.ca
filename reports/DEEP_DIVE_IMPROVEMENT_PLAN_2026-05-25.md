# Deep-Dive Improvement Plan — May 25, 2026

**Sources:** Incidents page (36 tracked), .MD sweep (193 files), AI Hedge Fund Simulation (22 picks), Session Summary (Grok 4.3), live tournament data (3,161 picks)

---

## 1. Overlapping Issues (Multiple Systems Affected)

### 1.1 ML Calibration Inversion (CRITICAL — P0)
**Incidents:** ML calibration system-wide inverted · smart_picks_engine weights confidence at 35% inverting ranker
**Our Finding:** Confidence 0.85-0.90 band has 20% WR, confidence field = 0.00 for all resolved picks
**Status:** Partially mitigated by persona_WR proxy (confidence fallback). Not fixed at root.
**Fix:** 
- Invert confidence contribution in score_booster.py (line ~45) — if confidence inverted, 1.0 - confidence
- Replace confidence with trust_score as primary signal for HC gate
- Run Platt calibration on a held-out set to produce calibrated probabilities
**Files:** `alpha_engine/score_booster.py`, `alpha_engine/config.py`, `audit_trail/quality_gates.py`

### 1.2 PnL Integrity (CRITICAL — P0)
**Incidents:** PnL mismatch on 38.97% sampled · WON status rows show avg pnl_pct = -41.1% · 5 FOREX rows < -100% · summary_picks.json fixture suspicion
**Our Finding:** FOREX resolver bug (63% wins are 1bp "flicker"), CL=F duplicated at 2 prices, MP calibration inflated
**Status:** FOREX blocked by kill gate. Old dashboard PnL is sum-of-percentages (fake +692% vs real +50.6%)
**Fix:**
- Run `tools/audit_won_picks.py --correct` after fixing column name bug (`category` not `asset_class`)
- Apply ±10% PnL cap to all resolved picks in dashboard_generator.py
- Fix 5 FOREX pnl_pct < -100% rows
- Replace summary_picks.json fixture with live DB query
**Files:** `tools/audit_won_picks.py`, `audit_trail/dashboard_generator.py`

### 1.3 Data Pipeline: Ghost Rows + Open Bloat (CRITICAL — P0)
**Incidents:** 56,559 ghost rows · 29.2M open positions · signal_outcomes 82 days stale · smart_picks.json 25 days stale
**Our Finding:** tournament_picks has 0 duplicates, 0 status/PnL mismatches (CLEAN). Old `picks` table has 8,435 rows, not maintained.
**Status:** Open bloat RESOLVED (4,081 now, was 29.2M). Ghost rows NOT executed.
**Fix:**
- Run `python tools/cleanup_ghost_rows.py --execute` (was DRY-RUN only)
- Fix `tools/check_resolver_health.py` (missing `import argparse`)
- Wire report_freshness_tracker.py to CI
**Files:** `tools/cleanup_ghost_rows.py`, `tools/check_resolver_health.py`

---

## 2. Audit Dashboard Improvements

### 2.1 US Equity Picks (UEPS) — ZERO TRACK RECORD
**Incidents:** US Equity screener emits zero picks · IPO advertised as tracked but zero coverage
**Our Finding:** UEPS n=0/100 live. ADBE (Score 0.839, F-Score 7/9, ROIC 45%) is theoretically strongest but 0 forward-test data.
**Fix:**
- Wire UEPS composite to weekly scanner (already in queue per incidents)
- Build IPO scraper (SEC EDGAR RSS feed) — estimated 4-6 hours
- Generate first 20 UEPS picks within 48 hours using the existing Magic Formula + Piotroski + Acquirer's Multiple engine
**Files:** `alpha_engine/value_screener.py`, `tools/ipo_scraper.py` (to create)

### 2.2 Smart Picks — UNVERIFIED EDGE
**Incidents:** Smart Picks 'Signal Time' is file age, not pick age · empty `sp_*` tables · lm_smart_consensus stale
**Our Finding:** Smart Picks manifest says it filters against smart_picks_feed but historical closed rows lack at-issue fields.
**Fix:**
- Wire `audit_integration/06_pick_surface_eval_schema.sql` to DB
- Populate signal_time in smart_picks_feed payload
- Add daily cron for smart_picks.json generation
**Files:** `audit_integration/06_pick_surface_eval_schema.sql`, `alpha_engine/smart_picks_engine.py`

### 2.3 Money Ready — ORPHANED FEATURE
**Incidents:** (implicit — not in incident list but flagged by our audit)
**Our Finding:** btn-money-ready toggles state but no render path applies filter.
**Fix:** Wire money-ready tab to the 5-gate framework from our edge_significance_gate.py
**Files:** `audit_dashboard/template.html`

---

## 3. Per-Asset-Class Gaps

### 3.1 EQUITY
**Gaps:** UEPS n=0 · PENNY_STOCK PF=0.19 dragging class · VIX regime gate branch unmerged · Weekend-gap handling incomplete
**Our Edge:** deep_value x EQUITY (60 picks, 60% WR, +1.07% PnL) — only proven pair
**Fix:**
- Merge VIX regime gate sidecar (branch `feat/equity-vix-regime-gate-sidecar-2026-05-13`)
- Split penny stocks from equity universe (Flag step per Institutional Readiness Plan)
- DOW tilt (Tue/Wed long bias) + PEAD strategy launch
**Files:** `alpha_engine/equity_strategies.py`, `alpha_engine/quality_gates.py`

### 3.2 CRYPTO
**Gaps:** MEMECOIN not quarantined · ADV filter missing · on-chain momentum disabled · CONFIDENCE INVERTED
**Our Edge:** SOLUSDT LONG (65% WR, n=23) — small sample, vol_arb persona
**Fix:**
- Enable CRYPTO_ONCHAIN_MOMENTUM_ENABLED=1 (Glassnode MVRV-Z)
- Add BTC UTC-hour death-zone filter (08-09Z reject)
- ML confidence inversion fix (see §1.1)
- Wire copy_trader_intel crypto signals to tournament
**Files:** `alpha_engine/score_booster.py`, `config.py`, `alpha_engine/crypto_strategies.py`

### 3.3 FOREX
**Gaps:** PF<1, negative PnL, 93% USDJPY concentration in survivor · SL at 0.5% sits at median daily ATR · forex_carry.py in repo but not allowlisted
**Our Finding:** BLOCKED by kill gate (57.3% WR, -0.39% avg PnL)
**Fix:**
- Widen FOREX SL to ≥1.0% or 1.5x daily ATR
- Block all losing FOREX strategies, diversify survivor
- Add forex_carry to non-crypto policy allowlist
- FOREX_HARD_DISABLE env switch (M-007)
**Files:** `alpha_engine/forex_strategies.py`, `alpha_engine/config.py`

### 3.4 COMMODITY
**Gaps:** Class-level 11.9% WR / PF 0.29 · COT over-emission (65% concentration in CT=F) · Re-derive post-PR #994
**Our Finding:** All picks SHORT — regime bias suspected. CL=F near-zero EV (0.05 risk units)
**Fix:**
- Re-derive COMMODITY PF/WR on post-PR #994 deduped data
- Kill all losing COMMODITY strategies, rebuild from non-COT signals
- Diversify beyond CT=F: GC/SI/HG/CL/NG/ZW/ZC/ZS
**Files:** `alpha_engine/commodities_strategies.py`, `alpha_engine/cftc_positioning.py`

### 3.5 BOND
**Gaps:** Antigravity_bond 0% WR on n=9 · bond_connors_rsi2 in shadow mode · TLT 75% concentration
**Our Finding:** BOND WARNED (-0.14% avg PnL, n=251)
**Fix:**
- Kill BOND emission until viable strategy built (per incidents)
- Run bond_connors_rsi2 in shadow 60 days → gate to probation
- Add more symbols beyond TLT/IEF (BND, AGG, LQD, HYG)
**Files:** `alpha_engine/bond_strategies.py`, `alpha_engine/bond_data_fred.py`

### 3.6 PENNY / FUTURES
**Gaps:** 0 resolved data in our pipeline · penny_deep_oversold BLOCKED · futures strategies BANNED at 0% WR
**Our Finding:** MVST/KULR/QBTS all have n=0. First resolution May 31 for PENNY, Jun 8 for FUTURES.
**Fix:**
- Wait for natural resolution windows to close
- Investigate Gate 0 logic for penny (likely per-class score floor)
- Formally retire banned futures strategies, move to deprecated/
**Files:** `alpha_engine/penny_strategies.py`, `alpha_engine/futures_strategies.py`

---

## 4. Persona / Simulation Improvements

### 4.1 Extend Simulation
**Our Status:** 22 picks tracked in simulation_picks table, weekly resolver active, 10-round debate complete
**Gaps:** IPO category stale (800+ day data), no live IPO scraper, no mutual fund tracking
**Fix:**
- Build live SEC EDGAR IPO scraper (RSS feed + stockanalysis.com)
- Add mutual fund tracker (Fidelity Zero, Vanguard, Schwab no-fee funds)
- Run IPO lockup backtest with regime filter (only when SPY below 200-DMA)
**Files:** New: `tools/ipo_scraper.py`, `tools/mutual_fund_tracker.py`

### 4.2 Super Secure Picks — OPERATIONALIZE
**Our Status:** 3 personas defined (super_secure_value, super_secure_macro, super_secure_trend), 11 picks generated
**Gaps:** Persona criteria exist but not wired into tournament pipeline scoring
**Fix:**
- Wire persona_WR proxy into all new pick generation
- Add F-Score/Altman Z''/Beneish M gates to EQUITY persona
- Surface kills/warnings on tournament page
**Files:** `tools/ai_tournament/super_secure_personas.py`, `tools/populate_picks.py`

---

## 5. CI / Infrastructure

### 5.1 Failing Tools (from .MD sweep)
| Tool | Issue | Fix |
|------|-------|-----|
| `tools/check_resolver_health.py` | Missing `import argparse` | Add import |
| `tools/audit_won_picks.py` | Column mismatch (`category` vs `asset_class`) | Fix SQL |
| `tools/test_ghost_cleanup.py` | String vs int assertion | Fix fixture |
| `tools/test_resolver_health.py` | 2/40 failing (staleness boundary) | Fix threshold logic |

### 5.2 Deployment Gaps
- Tournament model_summary.json not auto-generated by pipeline → add step
- UEPS score data not persisted → add DB write
- Smart Picks engine runs on stale data → add daily cron

---

## 6. Priority-Ordered Action Plan

### Sprint 1 (This Session — P0 fixes)
| # | Action | Impact | Time |
|---|--------|--------|------|
| 1 | Fix `tools/check_resolver_health.py` (add import) | Resolver health monitoring | 5 min |
| 2 | Fix `tools/audit_won_picks.py` column bug | PnL integrity | 15 min |
| 3 | Generate + deploy tournament model_summary.json | Tournament page shows live data | 10 min |
| 4 | Add gen_tournament_summary.py to pipeline CI | Auto-regenerate on each run | 10 min |
| 5 | Wire UEPS composite to emit first 20 picks | Equity track record | 2 hrs |

### Sprint 2 (This Week)
| # | Action | Impact | Time |
|---|--------|--------|------|
| 6 | ML calibration inversion fix | All confidence-based decisions | 2-4 hrs |
| 7 | Run ghost_row cleanup --execute | DB health | 1 hr |
| 8 | Merge VIX regime gate sidecar | EQUITY edge | 2 hrs |
| 9 | Build IPO scraper (SEC EDGAR) | New asset class coverage | 4-6 hrs |
| 10 | Wire report freshness tracker to CI | Prevent stale reports | 1 hr |

### Sprint 3 (Next Week)
| # | Action | Impact | Time |
|---|--------|--------|------|
| 11 | CRYPTO on-chain momentum enable | Crypto edge | 30 min |
| 12 | FOREX SL widen + carry strategy allowlist | FOREX rehabilitation | 2 hrs |
| 13 | COMMODITY re-derive post-dedup PF/WR | Honest numbers | 2 hrs |
| 14 | Wire smart_picks DB schema | Verify Smart Pick edge | 2 hrs |
| 15 | Mutual fund tracker | New category | 2-3 hrs |

---

## 7. What Our Work Today CLOSED

| Incident | How We Closed It |
|----------|-----------------|
| FOREX negative PnL trap | Kill gate: FOREX asset-class BLOCKED (253 picks, -0.39% avg PnL) |
| No n-threshold gate | Statistical kill gate: 4 KILLED personas, 5 WARN, 33 WATCH |
| Confidence field = 0.00 | persona_WR confidence proxy in ingest_to_db.py |
| PENNY/FUTURES generating blind picks | Flagged as WR=0%, PAPER ONLY, removed from active allocation |
| CL=F duplicated at 2 prices | Flagged, commodity entry kept, futures dropped |
| ML calibration warning undocumented | Added to simulation report + confidence methodology |
| No forward-test simulation | simulation_picks DB table + weekly GHA resolver + 22 picks tracked |
| UEPS has n=0 | Flagged, infrastructure gap documented, IPO scraper plan |
| Smart Picks unverified | Flagged, DB schema exists, needs wiring |

---

*Generated: May 25, 2026 · Sources: 36 incidents, 193 .MD files, tournament_picks (3,161 picks), AI Hedge Fund Simulation*
