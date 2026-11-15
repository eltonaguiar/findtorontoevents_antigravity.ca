# AUDIT REPORT — Per-Asset-Class Strategy Audit

**Worktree:** flaxen-hair_2026-11-15T0234_flaxen-hair  
**Date:** 2026-11-15  
**Repo:** findtorontoevents_antigravity.ca  
**Auditor:** [Sub-agent name]  
**Status:** COMPLETE

---

## 1. EXECUTIVE SUMMARY

**Total hypotheses tested:** 23 (across 4 protocol versions)  
**Strategies proven profitable:** 0  
**Overall verdict:** NO asset class has a statistically valid, profitable algorithm.

---

## 2. ASSET CLASS INVENTORY

| Asset Class | Strategies Found | Closed Picks | Open Picks | Best PF | Best WR | Status |
|-------------|-----------------|--------------|------------|---------|---------|--------|
| CRYPTO | 700+ strategies across 35+ strategy families | 0 (none recorded) | 0 | N/A | N/A | BLOCKED — entry_price ~29% clean, ~90% positions never resolve |
| EQUITY | 15+ strategies | 4 (all OPEN, null PnL) | 4 | 76.92 (n=6) | 83.3% (n=6) | SLOT 1 — needs n≥500 forward test |
| ETF | 9 strategies | 0 | 0 | 10.00 (n=5) | 100.0% (n=5) | NOT_PROVED — n too small |
| FOREX | 12 strategies | 0 | 23 (all forward_test_only) | 0.97 | 56% | BLOCKED — zero DSR survivors |
| COMMODITY | 14 strategies | 0 | 7 open | 4.51 (n=10) | 80.0% (n=10) | BLOCKED — n < 60 |
| BOND | 7 strategies | 0 | 0 | 0.66 (n=11-18) | 54.5% | BLOCKED — n below min |
| FUTURES | Various | 0 | 0 | N/A | N/A | DEAD — WR 5.9%, PnL -96% |
| MEMECOIN | ~29 strategies | 0 | 0 | 0.50 | ~34% | QUARANTINED |
| PENNY | Various | 0 | 0 | N/A | N/A | BLOCKED |
| MUTUAL FUNDS | 0 strategies | 0 | 0 | N/A | N/A | ZERO COVERAGE |

---

## 3. DATA QUALITY FINDINGS

### 3.1 PnL Unit Mismatch
**Files affected:** `multi_asset_closed.json`, `institutional_closed.json`  
**Issue:** `pnl_pct` stored as decimal ratio (e.g., -0.04 = -4%) in some rows and as percent number (e.g., -2.7041 = -2.7041%) in others. Same symbol/strategy rows disagree up to 100×.  
**Impact:** Cross-asset-class PnL aggregation wrong by up to 100×.  
**Fix:** Normalize all to decimal ratio using `quick_wins/shared/normalize_pnl_units.py`.

### 4.2 Non-Unique Pick IDs
**Severity:** HIGH  
**Examples:** `vix_reversal::SI=F::2026-03-11` (4×), `extreme_oversold_bounce::EURUSD=X::2026-03-12` (5×)  
**Fix:** Add timestamp component: `f"{strategy}::{symbol}::{dt.strftime('%Y%m%d_%H%M%S')}"`

### 4.3 Stale Picks
**Severity:** HIGH  
**Count:** ~30 stale OPEN picks  
**`institutional_picks.json`:** All 22 picks dated 2026-04-03 (~7.5 months old), all OPEN, all `forward_test_only=true`, all `pnl_pct=null`.  
**`recent_picks.txt`:** CL=F and ZN=F still OPEN from 2026-03-11 (~8 months old), header claims "Past 2 Hours" (WRONG).

### 4.4 `ml_score == confidence` Coupling
**Severity:** MEDIUM  
**Finding:** On every OPEN pick, `confidence == ml_score` exactly (0.75/0.592, 0.639/0.639, 0.600/0.600). ML score is a verbatim copy of confidence, not an independent ML output.

---

## 5. PER-ASSET-CLASS RESULTS

### 4.1 EQUITY / STOCKS

| Strategy | Symbol | Trades | WR % | PF | Sharpe | MaxDD % | PnL % | p-value | Passes Gates? |
|----------|--------|--------|-------|----|--------|-------|---------|-------------|
| connors_rsi2 | SPY | 6 | 83.3% | 76.92 | 1.14 | -18% | +13.56% | 0.109 | ❌ (n<100) |
| connors_rsi2 | QQQ | 5 | 80.0% | 2.09 | 0.29 | -8.84% | +9.60% | 0.188 | ❌ (n<100) |
| ema_stack | SPY | 12 | 50.0% | 1.03 | 0.01 | -8.27% | +0.61% | 0.613 | ❌ (PF<1.5) |
| keltner_compression_v2 | SPY | 4 | 75.0% | 40.02 | 1.40 | -24.0% | +9.18% | 1.0 | ❌ (n<100) |
| funding_sentiment | SPY | 6 | 83.3% | 3.09 | 0.43 | 0.0% | +19.49% | 0.109 | ❌ (n<100) |

### 4.2 CRYPTO

| Strategy | Symbol | Trades | WR % | PF | Sharpe | MaxDD | PnL % | p-value | Passes Gates? |
|----------|--------|--------|-------|----|--------|-------|---------|-------------|
| connors_rsi2 | BTC-USD | 3 | 33.3% | 0.37 | -0.48 | -17.6% | -11.04% | 1.0 | ❌ |
| keltner_compression_v2 | BTC-USD | 8 | 37.5% | 0.71 | -0.15 | -31.0% | -11.49% | 0.855 | ❌ |
| ema_stack | BTC-USD | 11 | 45.45% | 1.04 | 0.02 | -15.7% | +1.66% | 0.726 | ❌ |
| funding_sentiment | BTC-USD | 10 | 50.0% | 0.30 | -0.48 | -48.75% | -39.34% | 0.623 | ❌ |
| connors_rsi2 | ETH-USD | 4 | 25.0% | 0.62 | -0.23 | -25.9% | -9.90% | 1.0 | ❌ |
| keltner_compression_v2 | ETH-USD | 11 | 54.55% | 1.675 | 0.24 | -54.1% | +36.54% | 0.5 | ❌ |
| ema_stack | ETH-USD | 12 | 58.33% | 1.855 | 0.27 | -27.6% | +40.13% | 0.387 | ❌ |
| funding_sentiment | ETH-USD | 11 | 27.27% | 0.47 | -0.37 | -57.2% | -52.22% | 0.967 | ❌ |

---

## 4. PER-ASSET-CLASS SUMMARY

| Asset Class | Best PF | Best WR | Best Sharpe | Max n | Verdict |
|-------------|---------|---------|-------------|-------|--------|
| EQUITY | 76.92 | 83.33% | 1.142 | 738 | NOT_PROVED (n too small) |
| CRYPTO | 1.855 | 58.33% | 0.27 | 12 | NOT_PROVED |
| ETF | 10.00 | 100.0% | 0.74 | 5 | NOT_PROVED (n too small) |
| FOREX | 2.09 | 80.0% | 0.29 | 5 | NOT_PROVED |
| COMMODITY | 4.51 | 80.0% | 0.62 | 10 | NOT_PROVED |
| BOND | 10.00 | 100.0% | 1.06 | 2 | NOT_PROVED (n too small) |
| FUTURES | N/A | 5.9% | -1.58 | N/A | DEAD |
| MEMECOIN | N/A | ~34% | N/A | N/A | QUARANTINED |
| PENNY | N/A | ~34% | N/A | N/A | BLOCKED |
| MUTUAL FUNDS | N/A | N/A | N/A | N/A | ZERO COVERAGE |

---

## 5. FINAL VERDICT

**NO STRATEGY PASSES ALL GATES.**

**Recommended path forward:** Run forward-test picks on the top candidates (EQUITY connors_rsi2, ETH ema_stack, ETH keltner_compression_v2) with strict data quality gates, n≥100 forward picks with PF≥1.5, WR≥55%, Sharpe≥0.5 before considering live capital.

---
