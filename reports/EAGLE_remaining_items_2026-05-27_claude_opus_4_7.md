# EAGLE: Remaining Items — Post Quick-Wins Roadmap
**Date:** 2026-05-27 02:26 EST | **Model:** Claude Opus 4.7 (via CommandCode)
**Branch:** `feat/EAGLE-2026-05-27-end-to-end-review`

These items remain AFTER the 9 quick wins are executed. Organized by workstream (from INSTITUTIONAL_READINESS_PLAN_2026-05-24.md) + per-class.

---

## Workstream A — Honesty Layer (Weeks 1-3)

| # | Item | Status | Effort | Files |
|---|---|---|---|---|
| A1 | Per-pick freshness SLA + auto-suppress beyond class threshold | PENDING | M | dashboard_generator.py, quality_gates.py |
| A2 | Cross-provider price reconciliation (≥2 providers) | PENDING | M | New alpha_engine/price_reconciler.py |
| A3 | Score calibration (Platt/isotonic) per asset class | PENDING | L | score_calibrator.py |
| A4 | Lookahead/leakage CI guard | PENDING | M | test_no_lookahead.py |
| A5 | Honest stat surface (compounded EW return as headline) | PARTIALLY SHIPPED | S | template.html, dashboard_generator.py |
| A6 | Ghost-row footnote refresh + pymysql GHA fix | PENDING | M | db_hygiene.py, audit-dashboard.yml |

---

## Workstream B — Edge Quality (Weeks 2-6)

| # | Item | Status | Effort | Files |
|---|---|---|---|---|
| B1 | Transaction-cost + slippage layer (per-class bps curve) | PENDING (PR #1026 scaffolds exist) | L | transaction_cost.py |
| B2 | Regime classifier (trending/MR/crisis) + macro-calendar blackout | PENDING | L | regime_filter.py |
| B3 | Vol-adjusted position sizing (0.5-1% portfolio risk per pick) | PENDING | M | position_sizer.py |
| B4 | Exit-logic upgrade (ATR-trailing, decay exits, liquidity-aware) | PENDING | L | exit_manager.py |

---

## Workstream C — Portfolio Construction (Weeks 4-8)

| # | Item | Status | Effort | Files |
|---|---|---|---|---|
| C1 | Portfolio constraints (correlation cap ≤0.6, sector ≤30%, VaR) | PENDING | L | portfolio_constraints.py |
| C2 | Pairs/co-integration sleeve (AAPL/MSFT, BTC/ETH, TLT/IEF) | PENDING | L | pairs_engine.py |
| C3 | Risk-budget enforcement (per-pick ≤5% portfolio VaR) | PENDING | M | portfolio_constraints.py |

---

## Workstream D — Structural Splits (Weeks 5-9)

| # | Item | Status | Effort | Files |
|---|---|---|---|---|
| D1 | Speculative_flag + visual separation on /audit | PENDING | M | passes_active_gate, template.html |
| D2 | Speculative-bucket gates (float, dilution, borrow, halt freq) | PENDING | M | speculative_engine.py |
| D3 | Institutional-bucket gates (factor exposures, options flow, insider) | PENDING | L | institutional path in quality_gates.py |

---

## Workstream E — Swarm-AI Redesign (Weeks 4-10)

| # | Item | Status | Effort |
|---|---|---|---|
| E1 | Factor-orthogonal specialist roster (Macro Hawk, Vol Hunter, etc.) | PENDING | L |
| E2 | Swarm-diversity guardrail (PCA on agent-return matrix) | PENDING | M |
| E3 | Aggregation upgrade (Wilson-lower CI + anti-correlation weighting) | PENDING | M |

---

## Workstream G — Governance/Monitoring (Weeks 3-13)

| # | Item | Status | Effort |
|---|---|---|---|
| G1 | Real-time monitoring + alerting (score drift, freshness misses) | PENDING | M |
| G2 | Rollback/circuit-breaker (auto-quarantine on 3-day floor violation) | PENDING | M |
| G3 | Data lineage + versioning (source_id, feature_set_hash per pick) | PENDING | M |
| G4 | CI/CD regression (golden hold-out backtest on every PR) | PENDING | L |
| G5 | Explainability surface (per-pick "why it fired") | PENDING | L |
| G6 | Stress/scenario tests (2008/2020/2022 replay against gate stack) | PENDING | L |

---

## Workstream F — Coverage Gaps (Weeks 6-13)

| # | Item | Status | Effort |
|---|---|---|---|
| F1 | Wire missing ETF/Bond/Commodity emitters into active JSON pipeline | PARTIALLY (ETF emitter exists, bond partial) | M |
| F2 | Mutual fund ranker (low-fee no-min) | NOT YET INGESTED | L |
| F3 | Per-class metric expansion (funding/OI for crypto, float/short for equity, etc.) | PENDING | L |

---

## Per-Class Remaining (After Quick Wins)

### CRYPTO
- **M-001 fix**: Clean BTC UTC-hour filter duplication (inline -10/+5 + function -20/+8 = -30 net penalty noted in #1083 swarm review)
- **M-038**: MEMECOIN production path block — quarantine_manifest has 0% cap but no active-gate block for all emission paths
- **Funding rate arbitrage sidecar**: Binance/Hyperliquid free carry edge, high system Sharpe 8+ in funding strategies
- **Confidence dead-zone enforce**: Promote 0.65-0.75 confidence dead-zone from shadow to enforce (WR=26.2%)
- **CRYPTO concentration cap**: Enforce ≤15% per-symbol (env already ON)

### EQUITY
- **VIX regime sidecar merge**: Branch `feat/equity-vix-regime-gate-sidecar-2026-05-13` exists but unmerged — merge + wire
- **PEAD strategy** (M-009): Scaffold on top-100 large-cap with yfinance earnings calendar
- **DOW tilt** (M-026): Tue/Wed long bias via score_booster
- **Overnight intraday reversal** (M-025): Module not created
- **FRED macro context**: Yield-curve inversion gate for EQUITY (YC gate already exists, needs FRED data source)
- **Slippage validator wire**: PR #1026 scaffolds exist for equity path

### COMMODITY
- **Wire carry_momo sidecar** (M-022): commodity_carry_momo.json has 18 symbols with 12-1 mom + carry values, wiring_status=OPT_IN_SIDECAR, not consumed by production
- **Diversify beyond CT=F**: Target 5+ symbols with ≥15 resolved picks, CT=F PnL share ≤30% (currently 73%)
- **COT lag re-run** (M-021): Full re-run with 3d publication lag, paper-pilot acceptance ≥75% on n=100
- **Cross-commodity spread** (M-039): Crude/natgas pair research module
- **Micro contracts**: Add MGC=F, MYM=F for realistic sizing

### ETF
- **Debug etf_sector_emitter**: Why 0 picks on 2026-05-15? Add logging for skip reasons (no sectors above 200d SMA + 3m momo)
- **M-023 dual momentum** (Antonacci): Opt-in sidecar with 12-1m absolute+relative
- **M-036 universe expansion**: XLF/XLE/XLK → n→150
- **FRED economic ETF**: Yield-curve rotation signal for VNQ/DBC/TIP
- **Black-Litterman fix**: Ledoit-Wolf + ridge to fix LinAlgError on rolling cov
- **Prune intermarket-flow-scout**: If ETF contrib PF<1.4, reduce weight; promote rotation as primary

### FOREX
- **KEEP DISABLED** until carry PF>1.0 on n>50 clean paper
- **If revived**: DXY EMA confluence gate (USD-strong → LONG USDJPY, USD-weak → SHORT EURUSD)
- **Real CFTC COT for FX futures**: Replace zscore proxy with actual 6E/6B/6J COT positioning
- **Carry from live FRED rates**: Replace static carry_yield_diff snapshot
- **Universes limit to 4 majors**: EURUSD/GBPUSD/AUDUSD/USDJPY for paper phase
- **MQL5 external comparison**: Top verified forex signal providers vs in-house

### BOND
- **Lower BOND_ELITE_FLOOR to 32-35** (currently defaults 40)
- **3 academic pilots** (from bond_deep_dive_round2):
  - Pilot A: TIPS-Treasury breakeven MR (FRED T10YIE + yf TIP/IEF)
  - Pilot B: Cochrane-Piazzesi curve-carry momentum (rank IEF/TLH/TLT 3m return, MOVE<20d MA gate)
  - Pilot C: HYG-LQD credit-spread 2σ MR (SPY regime filter)
- **M-020**: Walker-forward validator output path for BOND
- **M-024**: BOND TSMOM on TLT/IEF/SHY

### FUTURES
- **MERGE tile**: Patch dashboard_generator.py classification to route all =F contracts to unified CTA
- **Micro contracts**: Add MES=F, MNQ=F, MGC=F, MYM=F (lower notional for realistic paper)
- **3 targeted pilots**:
  - mes_overnight_drift: LONG 16:00 ET, exit 09:30 next (Asness 2011)
  - mgc_asia_mean_reversion: RSI(14)<35 18:00 ET LONG
  - m6a_carry_sign: LONG when 3M rate diff >0 + SMA slope
- **VIX gate for financial futures**: ES/NQ LONG blocked VIX>30

### PENNY/MEME
- **No items. STAY QUARANTINED.**
- If research-only: Speculative_flag + visual separation on /audit (Workstream D1)
- Hard gate spec: float>50M shares, ADV>$10M, dilution_prob<20%, halt_freq<2/year, social_velocity<3σ

---

## Infrastructure Remaining

- **PCG-5 full enforce**: Wire REJECT verdict into passes_active_gate (currently shadow-only)
- **per_class_trainer caller**: predict_quality() declared but never called — needs 30d shadow data collection then enforce
- **Kill gate admission**: evaluate_kill() wired but needs integration with passes_active_gate for auto-block
- **DB Freshness Guardian**: M-002 live, but extend to equity/BOND tables
- **Cross-DB consistency**: M-005 daily audit extended to all 9 classes
- **Canonical gate-policy parity test** (M-044): Extend PR #1030 P0.2 to cover all gate-config readers
- **Gitleaks/trufflehog** (M-043): Add to PR-validation workflow
- **DB secrets rotation** (M-043): Enforce env-var-only, secret-scan in GHA
- **roadmap_items table population**: Seed with all M-xxx items + workstream items + EAGLE quick wins (from DB schema in reports/2026-05-27_enhancements_roadmap_db_schema.md)

---

## Roadmap Database Table — Population Plan

The `ejaguiar1_stocks.roadmap_items` table (schema in `reports/2026-05-27_enhancements_roadmap_db_schema.md`) should be seeded with:

1. **All M-xxx items** from `MASTER_ACTION_PLAN_2026-05-15.md` Sections 3, 20, 21, 23, 27 (~50+ items)
2. **All Workstream items** (A1-G6) from `INSTITUTIONAL_READINESS_PLAN_2026-05-24.md` (~30 items)
3. **All Quick Wins** (PR-1 through PR-9) from EAGLE quick wins
4. **All remaining items** from this document
5. **All open incidents** from INCIDENT_* tables → mapped to roadmap_items with item_kind='incident'
6. **All enhancement backlog** from ENHANCEMENT_* tables → mapped with item_kind='enhancement'

**Field mapping:**
- item_id: 'M-001', 'QW-1', 'INC-P0-007', 'A1', 'B2', etc.
- item_kind: master_plan / quick_win / incident / workstream / asset_plan
- severity: P0/P1/P2/P3
- workstream: A/G/D/etc. (institutional readiness letters)
- parent_item_id: QW-1 parent = 'ETF-VIX-GATE' master plan item
- related_pr_numbers: [1083, 1085] etc.
- files_touched: ['alpha_engine/config.py', ...]

---

## Verification Matrix

| Item | Verification Command | Expected |
|---|---|---|
| ETF VIX gate wired | grep "VIX" tools/etf_sector_emitter.py | VIX check present before emission |
| EQUITY universe split | grep "LARGE_CAP_EQUITY" alpha_engine/config.py | New list exists, 20-25 tickers |
| CRYPTO source whitelist | grep "CRYPTO_SOURCE_WHITELIST" alpha_engine/config.py | 5-6 elite sources listed |
| On-chain momentum enabled | echo $CRYPTO_ONCHAIN_MOMENTUM_ENABLED | "1" |
| COMMODITY PF post-dedup | Read dashboard_data.json::COMMODITY.by_asset_class | PF < 2.0, honest numbers |
| ADV gate | grep "is_liquid\|min_adv\|LIQUIDITY" alpha_engine/production_scanner.py | Gate function present |
| MD dedup skill | ls .claude/skills/md-dedup/SKILL.md | File exists, executable |
| FRED key set | curl GHA secrets API | FRED_API_KEY present |
| Stale incidents fixed | SELECT status FROM INCIDENT_* WHERE incident_id IN (3,11,13,18) | RESOLVED |
