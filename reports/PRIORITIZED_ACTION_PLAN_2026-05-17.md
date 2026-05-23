# PRIORITIZED ACTION PLAN — Statistical Edge Per Asset Class
**Generated: 2026-05-17 | Source: Cross-reference of DAILY_IDEAS.MD corpus (14+ AI models) + live dashboard_data.json + full codebase audit**

> **TL;DR:** 1. Fix data plumbing (DB ghost cleanup, paper trading) → 2. COMMODITY live pilot ($500, diversify beyond cotton) → 3. EQUITY amplify (SEC EDGAR, factor models) → 4. Stop spreading effort on failing classes until winners are production-grade.

---

## 0. What's Already Implemented ✅

Before adding new features, know what already works:

| Component | Location | Status |
|-----------|----------|--------|
| PBO/CPCV overfit detection | `anti_overfit_validator.py`, `cpcv_overfit_detector.py`, `pbo_cscv.py` | ✅ DONE |
| PCG-5 portfolio gates (5-gate REJECT stack) | `audit_trail/portfolio_gates.py` + `tests/test_portfolio_gates.py` | ✅ DONE |
| COT dedup guard (72h symbol-level) | `audit_trail/quality_gates.py` | ✅ DONE |
| CT=F concentration cap (-8 score penalty) | `alpha_engine/score_booster.py` | ✅ DONE |
| Drift auto-pause gate | `audit_trail/quality_gates.py::_passes_drift_auto_pause_gate` | ✅ DONE |
| Blacklist system (intake + exec-gate) | `config.py::BLACKLISTED_STRATEGIES` + `quality_gates.py::BLOCKED_SOURCE_SYSTEMS` | ✅ DONE |
| Strategy blocklist (symbol-level) | `audit_trail/strategy_blocklist.py` | ✅ DONE |
| Kill gate with min-n floor | `audit_trail/kill_gate.py` | ✅ DONE |
| Outcome resolver (hourly cron, 3,500 resolved) | `alpha_engine/outcome_resolver.py` | ✅ DONE |
| Swarm pick tracking | `swarm_picks.json` + `weekly_review.py` + `pattern_miner.py` | ✅ DONE |
| Walk-forward validator | `alpha_engine/walkforward_validator.py` | ✅ DONE |
| COT lag correction + friction-adjusted MC | `tools/cot_lag_corrector.py`, `tools/cot_step7_friction_adjusted_mc.py` | ✅ DONE |
| Commodity seasonal + COT contrarian | `alpha_engine/commodity_seasonal.py`, `commodity_cot_contrarian.py` | ✅ DONE |
| Anti-overfit validator with DSR/PSR | `alpha_engine/anti_overfit_validator.py` | ✅ DONE |

---

## 1. Executive Summary

**Verdict: The project has real edge on COMMODITY and EQUITY. The problem is concentration, not absence of edge.**

5 independent senior-quant analyses (Grok, Mercury, Kimi, Inception, ChatGPT) converge on the same 4-step path:
1. **Fix data trustworthiness** (DB ghost cleanup is the #1 trust-breaker, then paper trading, then DB freshness)
2. **Concentrate on COMMODITY** (diversify beyond CT=F cotton while keeping the proven edge, get to real-money pilot)
3. **Amplify EQUITY** (build diversified book with SEC EDGAR earnings/factor strategies)
4. **Stop spreading effort** across failing classes until winners are production-grade

---

## 2. Current State Baseline (dashboard_data.json, 2026-05-17T00:12Z)

| Class | PF | WR | n | Status | OOS_WR | Verdict |
|-------|----|----|---|--------|--------|---------|
| **COMMODITY** | 7.71 | 85.5% | 228 | STABLE | — | **BEST — real-money candidate** |
| **EQUITY** | 1.65 | 53.2% | 393 | STABLE | 66.1% | Meets T2 PF, borderline WR |
| **ETF** | 2.25 | 66.7% | 75 | CANDIDATE | 75.0% | Strong metrics, needs n→200 |
| **CRYPTO** | 1.33 | 46.9% | 7,501 | STABLE | 45.5% | Sub-T2 WR, volume drag |
| **FOREX** | 0.85 | 57.8% | 251 | WATCH | — | Recovering from toxic, sub-T2 PF |
| **BOND** | 0.66 | 54.5% | 11 | THIN_SAMPLE | 56.2% | n sub-floor (charter: 100) |
| **FUTURES** | — | 100% | 2 | INSUFFICIENT_DATA | — | Dead scanner routing |

**Key Insight:** COMMODITY PF 7.71 is extreme but driven by CT=F (cotton) at ~73% concentration. The edge is real (DSR=1.0 verified on 100 closed picks) but single-contract risk. Diversification is the #1 COMMODITY action — add KC=F, ZC=F, GC=F while keeping CT=F pilot active in parallel.

**MySQL DB Reality (the single biggest trust-breaker):** The `at_signal_outcomes` table has 121 outcomes for 145,879 raw picks (0.08% coverage). `paper_trades` and `paper_portfolio_daily` tables are completely empty. Hundreds of thousands of ghost rows. This is why 5/5 independent analyses say "fix data first."

---

## 3. Critical Blockers (MUST fix before real-money deployment)

### 🔴 BLOCKER 1: MySQL Ghost Row Cleanup
- **Symptom:** 655k+ ghost rows; `at_signal_outcomes` at 0.08% coverage; `paper_trades` + `paper_portfolio_daily` EMPTY
- **Impact:** DB queries return wrong aggregates; no trustworthy forward test exists; 5/5 independent analyses flag this as the #1 trust-breaker
- **Action:** (a) Clean `at_raw_picks` ghost rows; (b) Wire paper trading to populate `paper_trades` + `paper_portfolio_daily` daily via `alpha_engine/copytrader_integration.py::generate_paper_trades()`; (c) Run `tools/mysql_prediction_anomaly_scanner.py` monthly
- **Effort:** 6h | **M-Ref:** M-002, M-005, M-011

### 🔴 BLOCKER 2: Paper Trading Gap
- **Symptom:** `paper_trades` and `paper_portfolio_daily` MySQL tables are EMPTY — by design (copytrader_integration.py:82 has no active caller)
- **Impact:** No forward validation. Cannot prove edge survives live conditions. Cannot claim Tier-2 candidacy without shadow record.
- **Action:** Wire `alpha_engine/copytrader_integration.py::generate_paper_trades()` to active cron. Write paper P&L to MySQL daily.
- **Effort:** 4h | **M-Ref:** M-002 (extension)

### 🔴 BLOCKER 3: DB Freshness Guardian Not Enforcing
- **Symptom:** GHA `db-freshness-guardian.yml` may not reliably fail on RED
- **Impact:** Stale data = fake stats = can't trust any performance numbers
- **Action:** Verify guardian fails build on RED; test with intentionally stale data
- **Effort:** 2h | **M-Ref:** M-005

### 🔴 BLOCKER 4: Micro-Deployment at $0
- **Symptom:** Live deployment capital = $0; target was 2026-05-23 per expanded plan
- **Impact:** Still paper-only after months of backtesting
- **Action:** Complete PCG-5 Phase 2 enforcement (promote from shadow log to exec-time REJECT), then deploy $500 on COMMODITY diversified basket
- **Effort:** 8h | **M-Ref:** M-050

---

## 4. Per-Asset-Class Prioritized Actions

### 🥇 COMMODITY — HIGHEST PRIORITY (PF 7.71, WR 85.5%)

| # | Action | Why | Effort | Status |
|---|--------|-----|--------|--------|
| C1 | Diversify beyond CT=F (cotton 73% concentration) | Single-contract risk; add KC=F, ZC=F, ZW=F, GC=F, SI=F, HG=F. CT=F pilot runs in PARALLEL — don't kill the proven edge | 4h | PENDING |
| C2 | Activate COT paper pilot (`cot_paper_pilot.py`) | Track live CT=F edge vs backtest; shadow mode | 2h | PENDING |
| C3 | Fix COMMODITY scanner underutilization (9/25 emitting) | 16 contracts not exercised; COT sensitivity gate may be filtering too hard | 3h | PENDING |
| C4 | Commodity carry+momentum double-sort | Miffre/Fuertes 2010; diversifies away from CT=F PnL | 4h | WIRED — needs activation |
| C5 | CT=F real-money micro-pilot ($500, 1 contract, parallel with diversification) | Only after C1-C3 + Blockers 1-3 cleared | 2h | GATED |

### 🥈 EQUITY — SECOND PRIORITY (PF 1.65, WR 53.2%)

| # | Action | Why | Effort | Status |
|---|--------|-----|--------|--------|
| E1 | SEC EDGAR integration (8-K/10-K/10-Q) | Earnings drift (PEAD) is proven edge; 60-day post-surprise drift | 6h | PENDING |
| E2 | Fama-French 3/5-factor regression | Factor tilts on existing universe; free via yfinance + FRED | 4h | PENDING |
| E3 | Insider Form 4 scanner | Insider buy clusters = leading indicator | 3h | PENDING |
| E4 | Walk-forward verify existing EQUITY systems | OOS_WR=66.1% is strong; confirm on rolling 30/90d | 2h | PENDING |
| E5 | Expand symbol universe (47/50 = 94% utilized) | Good coverage; add small/mid-cap names from SEC filings | 2h | PENDING |

### 🥉 ETF — THIRD PRIORITY (PF 2.25, WR 66.7%)

| # | Action | Why | Effort | Status |
|---|--------|-----|--------|--------|
| T1 | Sector rotation (relative strength, 12-1 momentum) | Cross-sectional momentum on sector ETFs; free via yfinance | 4h | PENDING |
| T2 | Cointegration pairs (XLK/VGT, XLF/KRE) | Stat-arb on ETF pairs; statsmodels cointegration test | 3h | PENDING |
| T3 | Macro overlay (VIX, yield curve, DXY) | Regime-gate sector rotation; FRED data free | 2h | PENDING |
| T4 | Accrue n→200 | Currently n=75; keep scanner active, don't rush | 0h | IN PROGRESS |

### 🔶 CRYPTO — SHRINK & CLEAN (PF 1.33, WR 46.9%)

| # | Action | Why | Effort | Status |
|---|--------|-----|--------|--------|
| X1 | Confidence inversion fix | ML inverted: conf≥0.90 → 14.4% WR. Implement isotonic regression + direction flip | 4h | PENDING (M-014) |
| X2 | Quarantine `quan_engine` (PF 0.66, 21% volume) | Single biggest CRYPTO drag; already in BLOCKED_SOURCE_SYSTEMS — verify enforcement | 1h | PARTIAL |
| X3 | Symbol tier filtering (Tier 1: BTC/ETH/SOL/BNB; Tier 2: XRP/ADA/AVAX; Tier 3: others) | Reduce garbage meme/penny names; focus on liquid pairs | 2h | PENDING |
| X4 | Tuesday-only hard filter (verify vs 22 UTC claim) | Cross-check against `feedback_long_source_bias.md` before implementing | 2h | PENDING |
| X5 | Edge concentrator module | Rolling IC monitor + ATR dynamic TP/SL + regime-routed allocation | 8h | NOT STARTED |

### 🔶 FOREX — MUTATE BEFORE KILL (PF 0.85, WR 57.8%)

| # | Action | Why | Effort | Status |
|---|--------|-----|--------|--------|
| F1 | Full mutation protocol (invert, session filter, COT overlay) | FOREX strategies are the problem, not the universe (22 pairs available) | 6h | PENDING |
| F2 | SHORT-only gate + COT reversal signal | Grok + Kimi converge: FOREX edge is SHORT-biased | 2h | PENDING |
| F3 | `signal_validation` FOREX signal isolation | Only known FOREX entry point (PF 4.31, WR 51%, n=98) | 3h | PENDING |
| F4 | Interest-rate differential carry model | Free via FRED + ECB rates; Eur/USD, Gbp/USD, Aud/USD | 4h | PENDING |

### 🔻 BOND — ACCRUE & EXPAND (PF 0.66, WR 54.5%, n=11)

| # | Action | Why | Effort | Status |
|---|--------|-----|--------|--------|
| B1 | Expand BOND scanner from 2→14 symbols | Currently only TLT/HYG emitting; full roster: IEF, SHY, LQD, etc. | 3h | PENDING |
| B2 | Yield curve signals (2s10s spread, curvature) | FRED data free; steepener/flattener rotation | 3h | PENDING |
| B3 | Keep paper-only until n≥100 | Charter floor; don't rush thin-sample class | 0h | POLICY |

### 🔻 FUTURES — UNBLOCK SCANNER (n=2, dead)

| # | Action | Why | Effort | Status |
|---|--------|-----|--------|--------|
| U1 | Debug `production_scanner.py::passes_active_gate` FUTURES branch | 14 symbols configured, 0 emitting | 3h | PENDING |
| U2 | Donchian breakout system (50/100d) | Turtle Traders proven; free via yfinance | 4h | PENDING |
| U3 | Accumulate 90 days before any verdict | n=2 is stat-meaningless | 0h | POLICY |

---

## 5. System-Wide Improvements

| # | Action | Why | Effort | Status |
|---|--------|-----|--------|--------|
| S1 | Multi-model swarm ensemble | Currently single-model (claude-opus-4-7) with persona prompts; swap personas to Sonnet/Haiku/Grok/DeepSeek | 4h | PENDING (M-051) |
| S2 | **v3b LLM signal-spec translator** | **HIGHEST LEVERAGE** — every NO_EDGE verdict caused by SMA proxy; replace with faithful natural-language signal translation | 6h | PENDING |
| S3 | Daily Supreme Tracker | Track per-class edge metrics daily; surface drift to dashboard | 6h | NOT STARTED |
| S4 | Cross-AI stat validation | 4 AIs compute PF/WR from dashboard_data.json; surface divergence | 2h | PENDING (M-053) |
| S5 | Strategy inversion layer | Auto-detect 35-45% WR strategies, create inverted variants, A/B test | 4h | PENDING |
| S6 | DNA mutation engine | Weekly automated strategy evolution (point mutation, crossover, regime switch) | 8h | PENDING |
| S7 | CI edge monitor for ALL asset classes | Extend `ab_analysis.yml` beyond COMMODITY; alert on >10% edge drop | 3h | PENDING |
| S8 | Data quality scanner (monthly cron) | Ghost rows, duplicate close events, impossible PnL values | 2h | PENDING |
| S9 | Robustness suite (stress tests) | Parameter sensitivity ±10%, scenario replay (2008/2020), Monte Carlo ruin | 8h | NOT STARTED |
| S10 | ai-hedge-fund (virattt) integration spike | Evaluate for strategy ideas; read repo, propose adapter | 4h | PENDING (M-054) |

---

## 6. 90-Day Sprint Plan

### Week 1-2: Foundation (May 17-30)
- [ ] Fix Blockers 1-4 (ghost cleanup, paper trading, DB freshness, PCG-5 Phase 2)
- [ ] C1-C2: COMMODITY diversification + COT paper pilot activation
- [ ] X1-X2: CRYPTO confidence inversion fix + quan_engine quarantine
- [ ] S1: Multi-model swarm ensemble
- [ ] B1: BOND scanner expansion (2→14 symbols)
- [ ] U1: FUTURES scanner routing debug

### Week 3-4: Amplify Winners (May 31 - Jun 13)
- [ ] C3-C4: COMMODITY scanner fix + carry/momentum activation
- [ ] E1-E3: EQUITY SEC EDGAR + Fama-French + insider scanner
- [ ] T1-T2: ETF sector rotation + cointegration pairs
- [ ] **S2: v3b LLM signal-spec translator** (highest leverage — unblocks NO_EDGE verdicts across all classes)
- [ ] S3: Daily Supreme Tracker
- [ ] S4: Cross-AI stat validation

### Week 5-6: Fix Losers (Jun 14-27)
- [ ] F1-F4: FOREX mutation protocol + SHORT-only gate
- [ ] X3-X5: CRYPTO symbol tiers + edge concentrator
- [ ] S5: Strategy inversion layer
- [ ] S8: Data quality scanner

### Week 7-8: Real-Money Pilot (Jun 28 - Jul 11)
- [ ] C5: COMMODITY $500 live pilot (if gates cleared)
- [ ] E4-E5: EQUITY walk-forward verification + universe expansion
- [ ] S9: Robustness suite (stress tests)
- [ ] S7: CI edge monitor all classes

### Week 9-10: Evolve (Jul 12-25)
- [ ] S6: DNA mutation engine
- [ ] S10: ai-hedge-fund integration spike
- [ ] T3-T4: ETF macro overlay + n accrual
- [ ] B2: BOND yield curve signals

### Week 11-12: Consolidate (Jul 26 - Aug 8)
- [ ] U2: FUTURES Donchian breakout
- [ ] Review all per-class metrics; re-rank
- [ ] Scale COMMODITY if pilot successful
- [ ] Begin EQUITY micro-deployment if ready

---

## 7. Convergence Map (Multi-Source Agreement)

These items are recommended by 4+ independent analyses (Grok, Mercury, Kimi, Inception, ChatGPT):

| Item | Sources | Action |
|------|---------|--------|
| COMMODITY is the real-money pilot | 5/5 | C1-C5 sprint |
| Fix outcome tracking / DB ghost cleanup first | 5/5 | Blockers 1-3 |
| Stop spreading effort | 5/5 | Defer FOREX/BOND/FUTURES new features |
| PBO/CPCV needed for overfit detection | 4/5 | ✅ Already implemented — verify |
| Multi-model ensemble needed | 4/5 | S1 |
| Free data per class (EDGAR, COT, FRED) | 5/5 | E1, C4, F4 |
| Mutate-before-kill for failing strategies | 4/5 | F1, S5, S6 |
| Symbol universe audit | 4/5 | B1, U1, C3 |
| v3b signal-spec translator (SMA proxy bottleneck) | — | S2 (highest single leverage per DAILY_IDEAS.MD) |

---

## 8. Success Criteria — When We're "World-Class Ready"

Per asset class:
- **COMMODITY:** PF≥2.0 OOS, n≥200, MDD≤15%, ≥3 diversified contracts, live $500 pilot with PF≥1.3
- **EQUITY:** PF≥1.8, WR≥55%, n≥500, SEC/factor integration live
- **ETF:** PF≥1.8, n≥200, sector rotation active
- **CRYPTO:** PF≥1.5, WR≥50%, confidence calibration fixed, quan_engine quarantined
- **FOREX:** PF≥1.2 (rehab) or formally deprecated
- **BOND:** n≥100, PF≥1.5, full 14-symbol roster
- **FUTURES:** n≥50, PF≥1.5, Donchian active

System-wide:
- Paper trading writes to MySQL daily
- DB Freshness Guardian fails on RED
- Daily Supreme Tracker running
- Multi-model swarm ensemble active
- Drift auto-pause fires at least once and is acted on
- ≥1 asset class at live micro-deployment stage

---

## 9. Anti-Patterns to Avoid

- ❌ Don't kill on raw `by_asset_class` aggregates — use `asset_class_health` (resolver-v2)
- ❌ Don't trust headline WR until ghost-symbol cleanup (MATIC 660-row artifact, quan_engine 755-row twin)
- ❌ Don't trust paper account names as gates (`feedback_gate_at_execution_not_generation.md`)
- ❌ Don't paste DB creds / PATs in chat (`security_pat_exposure_2026_05_15`)
- ❌ Don't add new strategies until existing winners are production-grade
- ❌ Don't spread to new asset classes until 3 are live-profitable 90d
- ❌ Don't trust single-model swarm consensus — use multi-model ensemble
- ❌ Don't re-implement what already exists (see §0) — modify/extend instead

---

**Next immediate action:** Fix Blockers 1-3 (ghost cleanup, paper trading, DB freshness) → then C1-C2 (COMMODITY diversification + COT pilot).

**File lineage:** Synthesizes DAILY_IDEAS.MD corpus (135K+ chars across 14+ AI models including Grok, Kimi, Cerebras, Gemini, Mercury, ChatGPT, Claude), MASTER_ACTION_PLAN_2026-05-15.md, SUPREME_PLAN_90days.md, expanded_enhancement_plan_2026-05-14.md, COT_PAPER_PILOT_TESTING_PLAN_2026-05-12.md, supreme_plan_review_2026-05-13.md, supreme_edge_plan_next_2026-05-12.md, daily_ideas_edge_per_class_20260513T010800Z.md, daily_ideas_synthesis_2026-05-15.md, daily_ideas_synthesis_2026-05-16.md, grok_2026-05-17_daily_ideas_corpus_review_phase2_plan.md, DAILY_IDEAS_PROMPTS.MD, AGENT_PROMPT_LIBRARY.md — cross-referenced against live dashboard_data.json (2026-05-17T00:12Z) and full codebase audit (PBO/CPCV, PCG-5, COT dedup, blacklist, outcome resolver, kill gate, walkforward, concentration cap, drift pause all verified as implemented).
