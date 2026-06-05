# Final Money-Ready Audit Report
**Date:** 2026-06-05
**Objective:** Identify which asset classes/strategies are trustworthy enough for real-money deployment.

---

## Executive Summary

**CRITICAL FINDING:** 0/9 asset classes are currently "money-ready" for live capital deployment. The system has research-tier edge in several areas, but data integrity issues (resolver bugs, ghost rows, stale data) prevent clean edge measurement.

---

## Tier 1: Institutional/Mutual Fund Ready
**Status:** 0/9 classes meet this threshold.

**Criteria:**
- N > 100 realized trades
- Sharpe Ratio ≥ 1.0 (net)
- Profit Factor ≥ 2.0
- Max Drawdown ≤ 20% monthly
- OOS validation passed

**Current Status:**
- **CRYPTO:** PF 1.25, WR 44.34% (Kelly-negative)
- **EQUITY:** PF 0.25, negative expectancy
- **ETF:** PF 1.60 (lab-only), insufficient forward data
- **FOREX:** PF 1.49 (dragged by poor strategies)
- **COMMODITY:** PF 2.26 (paper-pilot only)
- **FUTURES:** Concentration artifacts
- **BOND:** No sample

---

## Tier 2: High Conviction (Aggressive)
**Status:** 1 lab Tier-2 pass, 4 paper-pilot Tier-2 passes.

### Lab-Only Tier-2 Pass
- **ETF Dual Momentum Sectors:** PF 1.60, WR 53.8%, n=104
  - Walk-forward validated
  - Paper pilot just wired
  - **Verdict:** Requires 30+ more forward trades to promote to Tier 1

### Paper-Pilot Tier-2 Passes
- **deepseek_v4__aggressive:** +0.40% PnL (11 open positions, $100,403)
- **llama4_scout__aggressive:** +0.14% PnL
- **cursor_agent__balanced:** +0.015% PnL
- **together_deepseek_v3__aggressive:** +0.001% PnL

**Verdict:** These are emerging edges, not yet trustworthy for live capital.

---

## Tier 3: Research/Experimental
**Status:** Majority of current strategies.

**Notable Research-Grade Candidates:**
- **CRYPTO ML Sleeves:** 4 strategies with DSR ≥ 0.9995, WR 85–100%
  - Only class meeting real-money thresholds
  - Requires concentration/gating fixes
- **COMMODITY COT Positioning:** DSR=1.0, WR 86.5%
  - Currently paper-pilot only
  - PF inflation from dedup artifact
- **AI Tournament Models:** deepseek_v4 (PF 3.46, n=208), gpt4o (PF 3.14), grok3 (PF 2.29)
  - Research edge only, not production-gated

---

## Root Causes of "Embarrassing" Performance

### 1. Data Integrity Issues (CRITICAL)
- **Resolver bugs:** Ghost rows, stale data, label pollution
- **4,154 MISPRICED_ENTRY rows** excluded from audit
- **33,000 DNA backtests** performed
- **11 hypotheses** killed due to data quality

### 2. Concentration Artifacts
- 85% of FUTURES picks from `multi_asset_scanner`
- 40% of EQUITY picks from `regime_terminal`
- Single-source dominance inflates apparent edge

### 3. Strategy Selection Issues
- FOREX: High WR but terrible PF (dragged by `multi_asset_copytrader`)
- EQUITY: Honest failure (n=52, expectancy -1.77%)
- CRYPTO: Research edge in sub-cohorts, but deployed aggregate loses

### 4. SL/TP Mis-tuning
- Intradar OHLC replay shows whipsaw from aggressive SL tightening
- Win-rate collapsed via over-tightening

---

## Action Plan to Reach Money-Ready

### Immediate (Weeks 1-2)
1. **Fix resolver data integrity:**
   - Intrabar OHLC replay on 9,657 ghost OPEN picks
   - Remove 4,154 MISPRICED_ENTRY rows
   - Clean label pollution

2. **Concentration caps:**
   - Reject emit when `top_source > 0.50 AND n < 50`
   - Isolate high-conviction FOREX sleeves (cta_replicator, signal_validation)

3. **SL/TP audit:**
   - Use intrabar OHLC replay (NOT winsorization)
   - Re-tune based on empirical data

### Short-Term (Weeks 3-4)
4. **ETF paper pilot Day-30:**
   - n≥30 + MDD<15% + PF≥1.20 promotion gate

5. **CRYPTO sub-cohort paper pilot:**
   - 2 best DSR-1.0 sleeves (ml_enhanced INJUSDT 1d + DYDXUSDT 15m)
   - Paper only

### Medium-Term (Weeks 5-8)
6. **Per-class mutation framework:**
   - Apply selective mutations to 6 candidates per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
   - Not blanket mutation

7. **Forward testing:**
   - Minimum 30-50 distinct picks per asset class
   - Duration ≥ 2× longest look-back window
   - Start at ≤ 0.5% capital per strategy

---

## Trustworthy Asset Classes (Current State)

### Currently NOT Trustworthy for Real Money
- ❌ CRYPTO (aggregate book loses)
- ❌ EQUITY (negative expectancy)
- ❌ FOREX (poor strategy selection)
- ❌ FUTURES (concentration artifacts)
- ❌ BOND (no sample)

### Research-Grade (Paper-Pilot Only)
- ⚠️ ETF Dual Momentum (lab PF 1.60, needs forward data)
- ⚠️ COMMODITY COT (DSR=1.0, WR 86.5%, paper-pilot)
- ⚠️ CRYPTO ML Sleeves (DSR ≥ 0.9995, WR 85–100%, needs gating)

### Best Paper Candidates
1. **etf_verified_dual_momentum** (shadow pilot, lab PF 1.60, walk-forward PASS)
2. **deepseek_v4** (tournament PF 3.46, n=208)
3. **macd_rsi_momentum** (walk-forward validated PF 3.33, WR 65.4%)

---

## Conclusion

**The bottleneck is plumbing, not strategy.** The system has research-tier edge in several areas, but resolver bugs, ghost rows, stale data, and label pollution prevent clean edge measurement. Multiple audit rounds (4,154 MISPRICED_ENTRY rows excluded, 33,000 DNA backtests, 11 hypotheses killed) confirm the system needs data integrity fixes before new strategies.

**Recommendation:** Focus on fixing the data integrity pipeline (resolver, gating, concentration monitoring) before attempting to deploy new strategies. The existing research edge (ETF dual momentum, CRYPTO ML sleeves, COMMODITY COT) is promising but requires 4-8 weeks of paper-pilot validation before any live capital deployment.

**Timeline to Tier 1:** 8-12 weeks minimum for any asset class to reach institutional-grade readiness.
