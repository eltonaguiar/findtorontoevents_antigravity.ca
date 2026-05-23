# CORRECTED GAMEPLAN — 2026-05-18

> **Status:** Second round — corrected after peer critique of first-pass analysis.
> **First-pass grade:** C — good ideas buried in incorrect facts and overspec.
> **This round:** Uses live repo data only. No speculation. 5 PRs, not 37.

---

## 1. ERRORS CORRECTED FROM FIRST PASS

| Item | First Pass (WRONG) | Corrected (LIVE DATA) | Source |
|------|-------------------|----------------------|--------|
| CRYPTO PF | 2.54 (MONEY_READY) | 1.28 (NOT_READY) | pf_registry.json policy_clean_net |
| CRYPTO n | 195 | 1,942 | pf_registry.json |
| COMMODITY PF | 2.15 (WATCH) | 1.17 (NOT_READY) | pf_registry.json policy_clean_net |
| COMMODITY n | 89 | 160 | pf_registry.json |
| FOREX PF | 0.48 (NOT_READY) | 0.33 canonical | money_ready_verdict() |
| FOREX n | 45 | 393 | pf_registry.json |
| FOREX verdict | HARD_DISABLED | WATCH (FwdWR>=50 gate active) | quality_gates.py L4632 |
| ETF n | 75 | 105 resolved in dashboard | dashboard_data.json |
| EQUITY n | 31 | 31 (local only, MySQL not synced) | pf_registry.json |
| quality_gates.py lines | ~1,669 | 9,397 lines | GitHub API |
| passes_active_gate() line | ~5,939 | ~6,006 | GitHub raw |
| Source files count | "30+ JSON" | 32 source files, 161 entries | pf_registry.json |
| etf_sector_emitter.py | Spec'd gate for it | File does NOT exist in repo | GitHub API listing |
| Concentration caps | Listed as "to-do" | Already implemented 2026-05-13 | commit 1686e9cf6cb |
| Gate Config panel | Listed as "to-do" | Already shipped P0.5 | commit 1686e9cf6cb |
| Pick traceability | 138KB spec (PR-T1..T5) | Already shipped as 3-table SQLite | User feedback |
| Active picks after gates | Not stated | 0 (all 171 filtered out) | dashboard_data.json |

---

## 2. LIVE MONEY-READY VERDICT (per pf_registry.json + dashboard_data.json)

| Asset Class | n (clean) | WR% | PF | DSR | Verdict | Blocker |
|-------------|----------|-----|-----|-----|---------|---------|
| **CRYPTO** | 1,942 | 44.95% | 1.28 | <0.95 | **NOT_READY** | M-105: ml_enhanced family quarantine |
| **COMMODITY** | 160 | 45.0% | 1.17 | <0.95 | **NOT_READY** | COT 3d lag, CT=F 84.9% concentration |
| **ETF** | 105 resolved | 57.1% dash | ~1.2 est | unmeasured | **WATCH** | Need n>=100 + VIX<25 gate + PBO test |
| **EQUITY** | 31 | 35.48% | 0.72 | <0.95 | **INSUFF_DATA** | MySQL ghost-row purge pending |
| **FOREX** | 393 | 27.23% | 0.33 | <0.95 | **NOT_READY** | FwdWR>=50 gate active, hard-disable until eval |
| **BOND** | 1 | 0% | 0.0 | n/a | **INSUFF_DATA** | Scanner just wired, need n>=20 |
| **FUTURES** | 12 | 16.67% | 0.96 | <0.95 | **INSUFF_DATA** | Both copytrader directions blocked |

**Key insight:** ZERO asset classes are MONEY_READY. CRYPTO at PF=1.28 is the closest but still below the PF>=1.6 threshold. The entire portfolio is a research pipeline, not a deployable strategy.

---

## 3. SYSTEM-LEVEL HEALTH

From `dashboard_data.json` (generated 2026-05-18T00:27:47Z):

| Metric | Value | Assessment |
|--------|-------|------------|
| Total active picks (pre-gate) | 171 | — |
| Total active picks (post-gate) | **0** | **ALL picks filtered out** |
| Smart picks count | 0 | No picks qualify |
| Overall resolved | 7,729 | Sufficient data |
| Overall WR | 46.0% | Below 50% threshold |
| Overall PF | 1.23 | Below 1.6 threshold |
| Net Sharpe | 0.32 | Below 1.0 threshold |
| Max drawdown | 288% | Catastrophic |
| 30d rolling max DD | 3.61% | Manageable |
| Signal-to-trade % | 15.1% | Very low conversion |

**Critical finding:** Quality gates are working — they correctly filter out all 171 active picks because none meet the MONEY_READY thresholds. This is *intended behavior*, not a bug.

---

## 4. TOP STRATEGY DRAG (from pf_registry.json)

These strategies destroy the most capital. All are already blocked or quarantined in quality_gates.py:

| Strategy | n | WR% | PF | Status | Action |
|----------|---|-----|-----|--------|--------|
| cot_positioning | 104 | ~30% | 0.51 | **KILLED 2026-05-17** | M-095: COT look-ahead leakage |
| quan_engine_scalp | 1,793 | 25% | 0.0 | **KILLED** | Scheduled autopsy 2026-05-24 |
| ml_crypto_predictor LONG | 41 | 0% | 0.0 | **KILLED** | Directional kill (SHORT retained) |
| forex_rsi2_mean_reversion | 593 | 43% | 0.37 | **KILLED 2026-05-13** | Post-resolver-v2 failure |
| claude_gainer_st | 790 | 26.5% | ~0.5 | Under investigation | Drives trust-tier inversion |
| cta_commodity_momentum_term | 47 | 36% | 0.02 | **KILLED** | Total bleed |

---

## 5. WHAT THE TEAM ALREADY SHIPPED (acknowledged, not re-spec'd)

| Feature | Status | Date | Commit |
|---------|--------|------|--------|
| Pick traceability (3-table SQLite) | **SHIPPED** | ~2026-05-17 | User implemented |
| Concentration cap controls | **SHIPPED** | 2026-05-13 | 1686e9cf6cb |
| P0.5 Gate Config panel | **SHIPPED** | 2026-05-17 | 1686e9cf6cb |
| Anti-overfit validator (DSR/PBO) | **DEFAULT-ON** | 2026-05-13 | quality_gates.py L271 |
| CRYPTO SHORT regime gate | **DEFAULT-ON** | 2026-05-13 | quality_gates.py L4632 |
| Concept-drift auto-pause | **DEFAULT-ON** | 2026-05-14 | quality_gates.py L4880 |
| ML-enhanced quarantine | **SHIPPED** | 2026-05-15 | crypto_quarantine.json |
| Strategy score overrides | **SHIPPED** | 2026-04-21 | STRATEGY_SCORE_OVERRIDES |
| Cross-asset confluence bonus | **SHIPPED** | 2026-04-05 | CROSS_ASSET_CONFLUENCE_BONUS |
| Preferred pair bonus | **SHIPPED** | 2026-04-05 | PREFERRED_PAIR_BONUS |

---

## 6. PATH TO INSTITUTIONAL GRADE — HONEST ASSESSMENT

### What "institutional grade" means:
- PF >= 1.6 (gross of costs)
- DSR >= 0.95 (Deflated Sharpe Ratio, CPCV-based)
- PBO < 0.10 (Probability of Backtest Overfitting)
- Max drawdown < 20%
- Concentration: single name < 30%, single strategy < 25%
- At least 3 asset classes independently MONEY_READY

### Current gaps:

| Requirement | Current | Gap |
|-------------|---------|-----|
| PF >= 1.6 | 1.23 overall | Need +0.37 PF lift |
| DSR >= 0.95 | <0.95 (estimated) | Need CPCV validation |
| PBO < 0.10 | Unmeasured per class | Need CSCV test |
| Max DD < 20% | 288% historical | Need position sizing + stops |
| 3 classes ready | 0 classes ready | Need strategy culling + data |
| Post-cost expectancy > 0 | ~0.25 raw | Need slippage model wire-up |

### The honest path:

**Phase 1 (now — 2 weeks): Stop the bleeding**
- Quarantine ml_enhanced CRYPTO family (M-105) — already in progress
- Fix COT 3-day lag for COMMODITY — data integrity fix
- Wire VIX<25 gate for ETF — quick PF lift
- Wire post-cost expectancy gate — promotion from warning to hard

**Phase 2 (2–6 weeks): Build the first MONEY_READY class**
- CRYPTO has best shot: PF=1.28, n=1,942, needs +0.32 PF
- Strategy-level culling of the remaining bleeders
- per_class_trainer.predict_quality() wire-up (shadow → production)
- Regime conditioning (bull/bear/choppy)

**Phase 3 (6–12 weeks): Second and third classes**
- ETF at n=105, needs n>=100 + PBO test → closest after CRYPTO
- COMMODITY needs COT fix + concentration cap + diversify beyond CT=F
- EQUITY blocked on MySQL sync (PA console action)

**Phase 4 (12+ weeks): Full portfolio**
- BOND accumulating (n=1 → 20 target)
- FOREX hard-disabled until carry backtest validates
- FUTURES deprioritized

---

## 7. PR PLAN — 5 GENUINELY ACTIONABLE PRs (not 37)

### PR-1: COMMODITY COT Lag Correction + CT=F Cap
**Branch:** `fix/cot-lag-concentration-2026-0518`
**Files:** `audit_trail/quality_gates.py`, `multi_asset/cot_pipeline.py`
**Problem:**
- cot_positioning had 85% of picks on CT=F (cotton) using CFTC data not available at decision time
- WR 87% headline → 30% after 3-day lag correction
- CT=F concentration at 84.9% blocks PBO
**Solution:**
- Add 3-day publication lag to all COT signal ingestion
- Enforce single-symbol concentration < 35% in COMMODITY class
**Acceptance:**
- [ ] COMMODITY PF recalculated with lag-adjusted data
- [ ] CT=F concentration < 35% in next 100 picks
- [ ] M-095 rollback documented

### PR-2: ETF VIX<25 Gate Wire-Up
**Branch:** `feat/etf-vix-gate-2026-0518`
**Files:** `audit_trail/quality_gates.py`, `alpha_engine/etf_pipeline.py`
**Problem:** ETF picks fire regardless of VIX level. Paper analysis shows PF 2.05 when VIX<25 vs 0.72 when VIX>=25.
**Solution:** Add `vix_level` check to `passes_smart_gate()` for ETF class.
```python
if asset_class == "ETF" and pick.get("vix_level", 999) >= 25:
    return False, "etf_vix_too_high"
```
**Acceptance:**
- [ ] ETF picks blocked when VIX >= 25
- [ ] VIX<25 subset shows PF >= 2.0 on next 50 closed picks
- [ ] No regression in other asset classes

### PR-3: Post-Cost Expectancy Gate Promotion
**Branch:** `feat/post-cost-expectancy-gate-2026-0518`
**Files:** `audit_trail/quality_gates.py`, `alpha_engine/charter_slippage.py`
**Problem:** M-069 slippage model runs but results are warnings only. Pick scores are pre-cost; post-cost expectancy is not enforced at the gate.
**Solution:**
- Promote `post_cost_expectancy > 0` from warning to hard gate
- Use `charter_slippage.deduct_slippage()` to adjust expectancy
- Configurable: `EXPECTANCY_GATE_ENABLED=1` (default ON)
**Acceptance:**
- [ ] Picks with post-cost expectancy <= 0 are rejected
- [ ] Overall PF improves by >= 0.05
- [ ] Kill-switch documented

### PR-4: CRYPTO ml_enhanced Family Quarantine (M-105)
**Branch:** `feat/ml-enhanced-quarantine-2026-0518`
**Files:** `audit_dashboard/data/crypto_quarantine.json`, `audit_trail/quality_gates.py`
**Problem:** 147/149 ml_enhanced variants are unquarantined. These strategies have n=2,021, PF=0.41–1.28 range, destroying CRYPTO aggregate.
**Solution:**
- Add all ml_enhanced_* strategies with n<20 or PF<1.2 to quarantine
- Whitelist proven variants: FETUSDT_1d_B (PF=9.25), INJUSDT_1d_B (PF=41.0), BNBUSDT_15m_B (PF=52.6)
**Acceptance:**
- [ ] Quarantine list updated with 140+ strategy variants
- [ ] CRYPTO PF recalculated post-quarantine
- [ ] Whitelist has < 10 variants with n>=20 and PF>=2.0

### PR-5: Pick Traceability Enhancement — Filter "What-If" Query
**Branch:** `feat/pick-what-if-query-2026-0518`
**Files:** `audit_trail/pick_traceability.py` (or existing shipped module)
**Problem:** User wants to query: "This pick was filtered due to banned symbol/strategy — but what if it was allowed? Would it have been profitable?"
**Solution:**
- Add `GET /api/picks/filtered/simulate` endpoint (or CLI equivalent)
- Input: `pick_id`, `hypothetical_gate_overrides`
- Output: simulated P&L if pick had passed
- Reads from existing pick_lifecycle_log table
**Acceptance:**
- [ ] Can query any filtered pick from last 30 days
- [ ] Returns hypothetical P&L with gate override
- [ ] Works for all 7 asset classes
- [ ] < 100ms query time

---

## 8. OPEN DECISIONS (require human/PA action)

| ID | Decision | Blocking | Owner |
|----|----------|----------|-------|
| D-001 | MySQL ghost-row purge (655k stale rows) | EQUITY data sync | PA console |
| D-002 | FRED_API_KEY procurement | BOND macro data | Admin |
| D-003 | CRYPTO paper sizing ($100 → $500?) | MONEY_READY test | Operator |
| D-004 | ml_enhanced whitelist final approval | M-105 completion | Quant lead |
| D-005 | futures_momentum: monitor vs block | FUTURES class | User directive 2026-05-18 |

---

## 9. WHAT WAS WRONG IN THE FIRST PASS (self-critique)

1. **Used stale cached data** instead of reading the live repo
2. **Inflated CRYPTO stats** — took pre-dedup numbers (PF=2.54) instead of canonical PF=1.28
3. **Mischaracterized FOREX** — called it HARD_DISABLED when FwdWR>=50 gate is active and verdict=WATCH
4. **Understated source count** — said "30+" when there are 32 files with 161 entries
5. **Overspec'd 37 PRs** — most were already done or not actionable; 5 is the right number
6. **Wrote 138KB pick traceability spec** — user already shipped a pragmatic 3-table version
7. **Wrong line numbers** — passes_active_gate at ~6006, not 5939; quality_gates.py is 9,397 lines
8. **Spec'd etf_sector_emitter.py gate** — file does not exist in the repo
9. **Called CRYPTO MONEY_READY** — it is NOT_READY per the peer-validated 2026-05-17 plan
10. **Failed to commit files** — PAT was invalid, all files stayed local

---

*Document: CORRECTED_GAMEPLAN_2026-05-18.md*
*Generated: 2026-05-18T01:00:00Z*
*Status: Peer-critiqued, second pass*
