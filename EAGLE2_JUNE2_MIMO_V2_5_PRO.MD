# EAGLE2_JUNE2_MIMO_V2_5_PRO — Enhancement Plan: Research-to-Production Translation

**Date:** 2026-06-02  
**Author:** Mimo v2.5 Pro  
**Scope:** Enhancement plan to fix the research-to-production translation problem  
**Based on:** Quant assessment identifying 5 root causes + proper backtesting methodology  

---

## Executive Summary

The system does NOT have a "wait longer" problem. It has a **research-to-production translation problem** plus **data/resolver contamination**. The edge currently lives in:

1. **AI tournament portfolios** (deepseek_v4, gpt4o, grok3) — paper edge, not deployed
2. **Lab/filtered sub-sleeves** (ETF dual momentum, crypto VWAP/Bollinger) — best future candidates
3. **Pick funnel cells** — good for discovery, bad for sizing

The main /audit production book has NO deployable edge right now. CRYPTO, EQUITY, FOREX are below acceptable PF/WR.

---

## Part 1: Immediate Depromotions (Week 1)

### 1.1 — Depromote Weak Live Classes

| Class | Current Status | Action | Rationale |
|-------|---------------|--------|-----------|
| CRYPTO aggregate | PF 0.98, 49.5% WR | **DEPROMOTE** | Drag systems (ml_crypto_predictor, luxalgo_filters) poison the aggregate |
| EQUITY | PF 1.19, 53.9% WR | **DEPROMOTE** | Honest failure — bad deployed strategies, failed holdout |
| FOREX | PF 0.56, 31.1% WR | **DEPROMOTE** | High WR + terrible PF = red flag; mislabels/TIME_EXIT contamination |
| COMMODITY | PF 0.23, 18.8% WR | **DEPROMOTE** | Too little clean sample (n=16) |
| FUTURES | n=2 | **DEPROMOTE** | Concentration/artifact risk |
| BOND | PF 0.67, n=11 | **DEPROMOTE** | No meaningful live sample |
| ETF | PF 1.18, 54% WR | **MONITOR** | Best candidate edge, but sample too small |

**Implementation:** Set per-class sizing multipliers to 0.0 for depromoted classes. Keep scanning but block capital deployment.

### 1.2 — Stop Treating Aggregate Green Stats as Proof

The `/audit` aggregate shows:
- Smart Picks CRYPTO: **DISPUTED** (claimed 78.9% WR, DB ground truth 41.9%)
- Verified Alpha: shares same contaminated cohort
- High Conviction: shares same contaminated cohort

**Rule:** No class gets capital until it passes the admissibility pipeline (Part 3).

---

## Part 2: Edge Location — Where to Focus (Week 1-2)

### 2.1 — AI Tournament Portfolios (BEST CURRENT EDGE)

| Model | Evidence | Status |
|-------|----------|--------|
| deepseek_v4 | Best tournament performance, decent forward proof | **Primary candidate** |
| gpt4o | Good tournament performance | **Secondary candidate** |
| grok3 | Decent tournament performance | **Tertiary candidate** |

**Action:** Wire tournament model picks through the admissibility pipeline. If they pass, size them through the portfolio engine.

### 2.2 — Lab/Filtered Sub-Sleeves (BEST FUTURE CANDIDATES)

| Sleeve | Asset Class | Evidence | Status |
|--------|-------------|----------|--------|
| ETF dual momentum | ETF | Walk-forward validated, small n | **Top promotion candidate** |
| Crypto VWAP/Bollinger | CRYPTO | Walk-forward looks better than production mix | **Needs forward sample** |
| mega_mutation | CRYPTO | PF 1.93, WR 65.9%, n=265 | **Walk-forward validate** |
| rapid_fire | CRYPTO | PF 2.17, WR 61.9%, n=457 | **Walk-forward validate** |

### 2.3 — Pick Funnel Cells (DISCOVERY ONLY)

The pick funnel has interesting cells, especially in CRYPTO, but:
- Many surface wins are rejected by concentration, holdout, or dispute flags
- Good for finding candidate filters, not for trusting raw green cells

**Rule:** Funnel cells are candidates for the admissibility pipeline, NOT direct sizing signals.

---

## Part 3: Admissibility Pipeline (Week 2-4)

Every strategy must pass this pipeline before it can affect capital. No exceptions.

### 3.1 — 10-Step Admissibility Requirements

| Step | Requirement | Tool/Method |
|------|-------------|-------------|
| 1 | **Pre-register hypothesis** before backtesting | hypothesis_registry.json |
| 2 | **Real data only** with explicit source/fallback provenance | data_fetcher.py + audit log |
| 3 | **Purged + embargoed walk-forward** (not simple split) | walk_forward_validator.py |
| 4 | **Costs/slippage by asset class** in every engine | transaction_cost_model.py |
| 5 | **DSR/PBO/SPA correction** for multiple testing | deflated_sharpe.py |
| 6 | **Block bootstrap** (not i.i.d. shuffle) | block_bootstrap.py |
| 7 | **Regime robustness** across trend/volatility states | regime_detector.py |
| 8 | **Forward paper evidence** before promotion | shadow_paper_tracker |
| 9 | **Forward PF/WR close to OOS lab PF/WR** | walk_forward_validator.py |
| 10 | **Gradual capital scaling** (shadow → tiny → increase) | position_sizer.py |

### 3.2 — Pipeline Implementation

```
Strategy → Pre-register → Backtest (real data, costs, purged WF) → 
DSR/PBO check → Regime robustness → Shadow paper (30 picks) → 
Forward validation → Promotion decision → Gradual sizing
```

### 3.3 — Promotion Criteria

| Gate | Requirement |
|------|-------------|
| Lab PF | ≥ 1.5 (walk-forward, purged, with costs) |
| Lab WR | ≥ 50% |
| Lab DSR | ≥ 0.95 |
| Lab PBO | ≤ 0.50 (not overfit) |
| Forward PF | ≥ 1.2 (30+ shadow picks) |
| Forward WR | within ±5pp of lab WR |
| Regime | Profitable in ≥ 3 of 4 HMM states |
| Concentration | No single source > 40% of picks |

---

## Part 4: Resolver/Label/Concentration Fixes (Week 1-2)

### 4.1 — Resolver Issues

| Issue | Impact | Fix |
|-------|--------|-----|
| EXPIRED→WON mislabeling | Inflates WR | Fix exit_reason logic in outcome_resolver.py |
| TIME_EXIT contamination | FOREX high WR + bad PF | Separate TIME_EXIT stats from TP/SL stats |
| Disputed CRYPTO cohort | 78.9% WR claim unreliable | Remove from Smart Picks until verified |

### 4.2 — Concentration Issues

| Issue | Impact | Fix |
|-------|--------|-----|
| claude_gainer_st = 91.7% of CRYPTO Smart Picks | Fragile single-source | Cap any single source at 40% of a cell |
| ml_crypto_predictor = 492 raw picks, 0 surviving | Noise generator | Depromote or kill |
| strong consensus = 38 picks, 23.7% WR, +31.6% PnL | Paradox: low WR, positive PnL | Investigate: are wins big and losses small? |

### 4.3 — Label Issues

| Issue | Impact | Fix |
|-------|--------|-----|
| `unknown` strategy = 70 picks, 37.1% WR | Unlabeled noise | Trace source system, label properly |
| `hs_lb_None` = 97 raw picks | Missing strategy name | Fix strategy attribution |

---

## Part 5: Mutation Protocol (Week 3-4)

### 5.1 — Selective Mutation (Not Blanket Inversion)

**Rule:** Inversion only after explicit OOS proof. Mutation is the default.

| Strategy | n | WR | PF | Action | Mutation Axes |
|----------|---|-----|-----|--------|---------------|
| unknown | 70 | 37.1% | 0.59 | **MUTATE** | Axis 2 (symbol rotation) + Axis 3 (regime gate) |
| macd-hidden-div-scout | 15 | 40.0% | 0.67 | **MUTATE** | Axis 1 (invert) + Axis 2 (symbol rotation) |
| betting-against-beta | 15 | 20.0% | 0.25 | **MUTATE** | Axis 1 (invert) — beta-adjusted residual momentum is a known factor |
| altseason-rotation-scout | 13 | 38.5% | 0.62 | **MUTATE** | Axis 2 (drop bottom-quartile symbols) |
| regime_mild_bear | 11 | 18.2% | 0.22 | **MUTATE** | Axis 3 (regime gate) — bear regime is too narrow |
| stocks_rsi2_pullback | 17 | 29.4% | 0.42 | **MUTATE** | Axis 1 (invert) + Axis 2 (symbol rotation) |
| strong consensus | 38 | 23.7% | 0.31 | **INVERT** | Wins big (+31.6% PnL), loses small — inverse should work |
| extreme_fear | 178 | 46.6% | 0.87 | **MUTATE** | Axis 2 (symbol rotation) + Axis 3 (regime gate) |
| luxalgo_confluence | 132 | 45.5% | 0.83 | **MUTATE** | Axis 2 (drop bottom-quartile) + Axis 3 (regime gate) |
| multi_period_rsi_confluence_eth | 27 | 44.4% | 0.80 | **MUTATE** | Axis 2 (symbol rotation — ETH only is too concentrated) |

### 5.2 — Mutation Protocol

For each candidate:
1. **Axis 1 — Invert**: Flip LONG↔SHORT. Run walk-forward. If inverted PF > 1.3, ship inverted.
2. **Axis 2 — Symbol rotation**: Drop bottom-quartile symbols by WR. Run walk-forward.
3. **Axis 3 — Regime gate**: Only fire in matching HMM state. Run walk-forward.
4. If all 3 fail → kill permanently with autopsy doc.

### 5.3 — Inversion Criteria (STRICT)

Only invert if:
- OOS proof exists (walk-forward, purged, with costs)
- Inverted PF > 1.3 on holdout
- Inverted WR > 55%
- No concentration > 40% from single source
- Regime robust (profitable in ≥ 3 of 4 HMM states)

---

## Part 6: Backtesting Methodology (Week 2-4)

### 6.1 — Proper Walk-Forward Protocol

```
Data: 5 years daily OHLCV (yfinance + Binance failover)
Split: 60% train / 20% validation / 20% test
Method: Purged walk-forward with 5-day embargo
Costs: Per-class slippage model (crypto 0.1%, equity 0.001%, FX 0.0005%)
Bootstrap: Block bootstrap (block size = 5 days), 10,000 iterations
Correction: DSR + PBO for multiple testing
```

### 6.2 — Regime Robustness

Run walk-forward in each HMM state:
- STRONG_BULL
- BULL
- CHOP
- BEAR

Requirement: Profitable in ≥ 3 of 4 states.

### 6.3 — Concentration Check

For each strategy:
- No single source system > 40% of picks
- No single symbol > 20% of picks
- No single asset class > 60% of picks (unless class-specific strategy)

---

## Part 7: Implementation Timeline

| Week | Actions | Deliverables |
|------|---------|--------------|
| **1** | Depromote weak classes, fix resolver labels, cap concentration | Updated quality_gates.py, resolver fixes |
| **2** | Walk-forward validate mega_mutation + rapid_fire, wire tournament picks | Walk-forward reports, tournament integration |
| **3** | Run mutation protocol on 10 candidates | Mutation reports, inverted strategies |
| **4** | Wire admissibility pipeline, shadow paper tracking | pipeline.py, shadow_tracker.py |
| **5** | Promote ETF dual momentum + crypto VWAP/Bollinger if they pass | Promotion decisions |
| **6** | Gradual capital scaling on promoted strategies | Position sizer updates |

---

## Part 8: Success Criteria

### 8.1 — Per-Class Targets

| Class | Current PF | Target PF | Timeline |
|-------|-----------|-----------|----------|
| CRYPTO | 0.98 | ≥ 1.3 (filtered sub-cohorts) | 4 weeks |
| EQUITY | 1.19 | ≥ 1.5 (after mutation) | 6 weeks |
| ETF | 1.18 | ≥ 1.5 (after forward sample) | 4 weeks |
| FOREX | 0.56 | ≥ 1.0 (after mutation) | 8 weeks |
| COMMODITY | 0.23 | ≥ 1.5 (after scanner expansion) | 6 weeks |
| FUTURES | n=2 | ≥ 1.0 (after new strategies) | 8 weeks |
| BOND | 0.67 | ≥ 1.0 (after scanner expansion) | 6 weeks |

### 8.2 — Portfolio Targets

| Metric | Current | Target |
|--------|---------|--------|
| Active portfolios | 66 | 66+ (maintained) |
| Portfolio PF | Unknown | ≥ 1.3 (policy-clean) |
| Portfolio MDD | Unknown | ≤ 15% |
| Concentration | Unknown | No single source > 40% |

### 8.3 — Admissibility Pipeline

| Gate | Current | Target |
|------|---------|--------|
| Strategies passing pipeline | 0 | ≥ 5 by week 4 |
| Walk-forward validated | 0 | ≥ 10 by week 4 |
| Shadow paper tracked | 0 | ≥ 20 by week 4 |
| Promoted to live | 0 | ≥ 3 by week 6 |

---

## Part 9: Files to Create/Modify

### New Files
- `verified_strategies/admissibility_pipeline.py` — 10-step pipeline
- `verified_strategies/mutation_protocol.py` — 3-axis mutation engine
- `verified_strategies/walk_forward_validator.py` — purged walk-forward
- `verified_strategies/block_bootstrap.py` — block bootstrap for DSR
- `verified_strategies/concentration_checker.py` — source/symbol concentration
- `reports/EAGLE2_admissibility_log.json` — pipeline results log

### Files to Modify
- `audit_trail/quality_gates.py` — depromote weak classes, cap concentration
- `alpha_engine/outcome_resolver.py` — fix EXPIRED→WON labeling
- `verified_strategies/strategy_verification_engine.py` — add walk-forward
- `verified_strategies/verification_runner.py` — add admissibility pipeline

---

## Part 10: Answer to Your Questions

**Do we just need more time?**
No. Only for ETF and some small-sample sleeves. The main production book needs structural fixes, not patience.

**Do our strategies suck?**
The deployed production mix mostly does, yes. The lab has some real sleeves (ETF dual momentum, crypto VWAP/Bollinger), but they are not what dominates live picks.

**What are we doing wrong?**
1. Promoting from the wrong evidence
2. Running too many weak emitters
3. Tolerating concentration/artifacts
4. Using inconsistent validation standards

**Do we need to DNA mutate our strategies?**
Yes, selectively. Not blanket inversion — mutation with explicit OOS proof.

**Are data/resolver issues part of it?**
Yes, especially FOREX / disputed dashboard cohorts / some surface stats. But they are not the whole story.

**Why is our portfolio empty?**
It's NOT empty. 81 portfolios exist, 66 with open positions. The issue was URL/cache behavior, not "no portfolio exists." The portfolio engine IS running.

**Where is our edge?**
1. AI tournament portfolios (deepseek_v4, gpt4o, grok3) — best current paper edge
2. Lab/filtered sub-sleeves (ETF dual momentum, crypto VWAP/Bollinger) — best future candidates
3. Pick funnel cells — good for discovery, bad for sizing

---

*This plan is the concrete implementation of the EAGLE_JUNE2 root-cause analysis. Every action item has a timeline, deliverable, and success criterion.*
