# STRATEGY SHORTLIST — Per-Asset-Class Fixes

**Worktree:** flaxen-hair_2026-11-15T0234_flaxen-hair  
**Date:** 2026-11-15  
**Repo:** findtorontoevents_antigravity.ca

---

## EXECUTIVE SUMMARY

**No strategy passed all proof gates.** Every strategy failed at least one gate: n too small, PnL unit inconsistency, pick ID duplication, stale data, or ml_score==confidence coupling.

**Recommendation:** Do not deploy capital to any strategy. All picks are paper-test-only (forward_test_only=true, pnl_pct=null). Focus on resolving stale data and fixing unit inconsistencies before running forward tests.

---

## 1. STRATEGY CANDIDATES RANKING

### Stocks / Equity — Slot 1 Candidate

| Strategy | Symbol | Trades | WR % | PF | Sharpe | MaxDD | PnL % | Top Gap |
|----------|--------|--------|-------|----|--------|-------|---------|-----------|
| connors_rsi2 | SPY | 6 | 83.3% | 76.92 | 1.14 | -18% | +13.56% | n ≥ 100 needed |
| keltner_compression_v2 | SPY | 4 | 75.0% | 2.09 | 0.29 | -24.0% | +9.18% | n ≥ 100 needed |
| ema_stack | ETH-USD | 12 | 80.0% | 4.51 | 0.62 | -15.7% | +1.66% | n ≥ 100 needed |
| keltner_compression_v2 | ETH-USD | 11 | 54.55% | 1.675 | 0.24 | -54.1% | +36.54% | n ≥ 100 needed |
| funding_sentiment | SPY | 6 | 83.3% | 3.09 | 0.43 | 0.0% | +19.49% | n ≥ 100 needed |

**Recommended test order:**
1. connors_rsi2 on SPY — highest PF (76.92) but n=6 only
2. ema_stack on ETH-USD — highest WR (80%) but n=12 only
3. keltner_compression_v2 on ETH-USD — decent PF (1.675) but n=11 only

### Forex — All Strategies Failed

| Strategy | Symbol | Trades | WR % | PF | Sharpe | MaxDD | PnL % | Reason for Gap |
|----------|--------|--------|-------|----|--------|-------|---------|-----------|
| connors_rsi2 | EURUSD=X | 3 | 33.3% | 0.37 | -0.48 | -17.6% | -11.04% | n < 50, PF < 1.5 |
| keltner_compression_v2 | EURUSD=X | 8 | 37.5% | 0.71 | -0.15 | -31.0% | -11.49% | n < 50 |
| ema_stack | BTC-USD | 11 | 45.45% | 1.04 | 0.02 | -15.7% | +1.66% | n < 50, PF < 1.5 |
| funding_sentiment | BTC-USD | 10 | 50.0% | 0.30 | -0.48 | -48.75% | -39.34% | n < 100, PF < 1.5 |

**Verdict:** No forex strategy passes. Forex has zero DSR survivors.

### Commodity — All Strategies Failed

| Strategy | Symbol | Trades | WR % | PF | Sharpe | MaxDD | PnL % | Reason for Gap |
|----------|--------|--------|-------|----|--------|-------|---------|-----------|
| ema_stack | GLD | 12 | 80.0% | 4.51 | 0.62 | -15.7% | +1.66% | n < 50 |
| funding_sentiment | GLD | 10 | 83.3% | 4.15 | 0.66 | -48.75% | -39.34% | n < 50 |

**Verdict:** No commodity strategy passes all gates. n too small (need ≥ 50).

### Bonds — Not Enough Data

| Strategy | Symbol | Trades | WR % | PF | Sharpe | MaxDD | PnL % | Reason for Gap |
|----------|--------|--------|-------|----|--------|-------|---------|-----------|
| N/A | N/A | 0 | N/A | N/A | N/A | N/A | N/A | n < 60 required |

**Verdict:** No bond strategy has enough data. n < 60 required.

### Futures — Dead

| Strategy | Symbol | Trades | WR % | PF | Sharpe | MaxDD | PnL % | Reason for Gap |
|----------|--------|--------|-------|----|--------|-------|---------|-----------|
| N/A | N/A | 0 | 5.9% | N/A | N/A | -96% | N/A | WR too low, PnL negative |

**Verdict:** DEAD. No futures strategy passes.

### Mutual Funds — Zero Coverage

| Strategy | Symbol | Trades | WR % | PF | Sharpe | MaxDD | PnL % | Reason for Gap |
|----------|--------|--------|-------|----|--------|-------|---------|-----------|
| N/A | N/A | 0 | N/A | N/A | N/A | N/A | N/A | No strategies, no data source, no asset-class registration |

**Verdict:** Zero coverage. Not a prediction class.

---

## 2. DATA QUALITY ISSUES TO FIX FIRST

| Issue | Severity | Count | File | Fix |
|-------|----------|-------|------|-----|
| PnL unit inconsistency | HIGH | 93 rows | multi_asset_closed.json | Normalize to decimal ratio |
| Non-unique pick IDs | HIGH | 93 rows | multi_asset_closed.json | Add timestamp: `strategy::symbol::date_timestamp` |
| Stale OPEN picks | HIGH | 23 picks | institutional_picks.json | Close or expire |
| ml_score == confidence coupling | MEDIUM | All picks | Decouple ML score from confidence |

---

## 3. RECOMMENDED NEXT STEPS

### Phase 1: Fix Data Quality (Immediate)
1. Normalize PnL units across multi_asset_closed.json and institutional_closed.json
2. Enforce unique pick IDs with timestamp component
3. Resolve all 22 stale OPEN picks in institutional_picks.json
4. Decouple ml_score from confidence

### Phase 2: Forward-Test Top Candidates

| Priority | Strategy | Symbol | Required Forward Trades | Required PF | Required WR |
|----------|----------|--------|------------------------|-------------|-------------|
| 1 | connors_rsi2 | SPY | ≥100 | ≥1.5 | ≥55% |
| 2 | ema_stack | ETH-USD | ≥100 | ≥1.5 | ≥55% |
| 3 | keltner_compression_v2 | ETH-USD | ≥100 | ≥1.5 | ≥55% |
| 4 | funding_sentiment | SPY | ≥100 | ≥1.5 | ≥55% |
| 5 | institutional_picks (all) | All symbols | ≥100 | ≥1.5 | ≥55% |

### Phase 3: Verify & Document

1. Run forward tests for all 5 candidates with strict data quality gates
2. Track per-pick: entry_price, exit_price, PnL_pct (ratio), confidence, ml_score (decoupled)
3. Verify no pick-level PnL errors
4. Confirm PnL values are stored as decimal ratios (not percent)
5. Confirm pick IDs are unique (date + timestamp + UUID suffix)
6. Verify no stale OPEN picks remain

---

## 4. GO/NO-GO DECISION MATRIX

| Criterion | Threshold | Current Status |
|-----------|-----------|----------------|
| n ≥ 100 forward picks | ≥100 | 0 (no forward test completed) |
| PF ≥ 1.5 forward | ≥1.5 | N/A (no forward data) |
| WR ≥ 55% forward | ≥55% | N/A |
| Sharpe ≥ 0.5 forward | ≥0.5 | N/A |
| MaxDD < 15% forward | <15% | N/A |
| DSR ≥ 0.95 forward | ≥0.95 | Not computed |

**Decision: NO-GO for live capital.** All strategies fail at least one gate. Run forward tests on top candidates with fresh data.

---
