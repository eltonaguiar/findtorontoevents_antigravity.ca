# Prediction Market & Copy Trader Audit Findings

**Worktree:** flaxen-hair_2026-11-15T0125  
**Date:** 2026-11-15  
**Scope:** Prediction market signals (Kalshi/Polymarket) and copy trader intel data sources  
**Repo:** findtorontoevents_antigravity.ca

---

## 1. Prediction Market Findings

### Files Found

| File | Path | Status |
|------|------|--------|
| `alpha_engine/kalshi_signals.py` | Strategy module | Exists |
| `alpha_engine/kalshi_signals.py` | Strategy module | Exists |
| `alpha_engine/prediction_market_consensus.py` | Strategy module | Exists |
| `alpha_engine/data/prediction_market_picks.json` | Picks data | Exists - EMPTY |
| `alpha_engine/data/polymarket_signals.json` | Signals data | **MISSING** (referenced but not generated) |
| `prediction_market_agents/data/whale_tracker.json` | Whale data | Empty (0 traders, 0 signals) |
| `tools/kimi_research_2026_05_20/prediction_market_signals.py` | Legacy script | Exists |
| `tools/kimi_research_2026_05_20/PREDICTION_MARKET_REPORT.md` | Report | Exists |
| `tools/prediction_market_consensus_pilot.py` | Pilot script | Exists |
| `tests/test_prediction_market_consensus.py` | Tests | Exists |
| `tests/audit_prediction_markets_crossover.spec.ts` | Test spec | Exists |

### Key Findings

**1. `multi_asset/data/multi_asset_closed.json` - Prediction Market Picks**
- Total picks: 0 (empty array)
- All `forward_test_only=true`, `pnl_pct=null`, `status=OPEN`, `forward_validated=false`, `forward_trades=0`
- Source systems: `multi_asset_copytrader` (30 picks), `coinglass_strategies` (1 pick), `cftc_socrata` (1 pick)

**2. `alpha_engine/kalshi_signals.py`**
- Kalshi signals module exists but all picks have `exit_price=0`, `take_profit=0`, `stop_loss=0`
- Blocked by `adversarial_compat.py` guard: `entry_price <= 0` check rejects all Kalshi picks

**3. `prediction_market_agents/data/whale_tracker.json`**
- 0 traders, 0 signals
- All whale tracker picks have `entry_price=0`

**4. `polymarket_strategy_audit.json`**
- Stale data: generated 2026-03-26 (~8 months old)
- All 5 audited wallets classified as "blocked" (HFT micro, market maker systematic, latency arb)
- Zero copyable strategies

### PnL Inconsistency Issues

| Symbol | Strategy | Entry Price | Exit Price | Stated PnL | Expected PnL | Issue |
|--------|----------|-------------|------------|------------|--------------|
| EURUSD=X | macd_divergence | 1.163602590560913 | 1.163602590560913 | -0.00567 | 0.00% | Stated -0.567% but exit price equals entry price (0.00% expected) |

**Conclusion:** The `pnl_pct` field in `multi_asset_closed.json` is **copied from `unrealized_pnl_pct` vs `current_price`** rather than computed from `entry_price`/`exit_price`. When `exit_price == entry_price`, the correct PnL is 0.0%, but the stored value of -0.567% represents an unrelated unrealized calculation.

---

## 2. Copy Trader Intel Sources

### Files Found

| File | Path | Status |
|------|------|--------|
| `copy_trader_intel/technical_analyzer.py` | Strategy module | Exists |
| `copy_trader_intel/non_crypto_consensus.py` | Strategy module | Exists |
| `copy_trader_intel/non_crypto_quality_enhancer.py` | Strategy module | Exists |
| `copy_trader_intel/gmx_scraper.py` | Strategy module | Exists |
| `copy_trader_intel/asset_class_analysis_forex.py` | Strategy module | Exists |
| `copy_trader_intel/data/clone_closed_picks.json` | Closed picks data | Exists |
| `copy_trader_intel/data/highscore_closed_picks.json` | Closed picks data | Exists |

### Copy Trader Performance Data

**From `multi_asset_closed.json` analysis:**

| Metric | Value |
|--------|-------|
| Total closed picks (institutional_closed.json) | 23 |
| Forward test only | All 23 (100%) |
| Forward validated | 0 (0%) |
| Forward trades > 0 | 0 |
| Status = OPEN | All 23 (100%) |
| Status = CLOSED | 0 |

**Copy Trader Performance Summary:**

| Metric | Value |
|--------|-------|
| Total copy trader picks | 0 (none resolved with actual PnL) |
| Average win rate | 0% |
| Average profit factor | N/A (no closed picks with realized PnL) |
| Best performing copy trader | N/A |

### Source Systems

| Source System | Count | Status |
|---------------|-------|--------|
| `multi_asset_copytrader` | 30 picks | All `forward_test_only=true`, `pnl_pct=null` |
| `cta_replicator` | 6 picks | All `forward_test_only=true`, `pnl_pct=null` |
| `coinglass_strategies` | 1 pick | `forward_test_only=true`, `pnl_pct=null` |
| `cftc_socrata` | 1 pick | `forward_test_only=true`, `pnl_pct=null` |

---

## 3. Data Quality Issues Identified

### Issue 1: PnL Unit Mismatch (ratio vs percent, up to 100×)

**Severity:** HIGH  
**Affected Files:** `multi_asset/data/multi_asset_closed.json` (93 rows), `multi_asset/data/institutional_closed.json` (23 rows)  
**Details:** `pnl_pct`/`realized_pnl_pct` stored as decimal ratio (e.g., -0.04 = -4%) in some rows and as percent number (e.g., -2.7041 = -2.7041%) in others. Same symbol/strategy rows disagree up to 100×:

| Symbol | Strategy | Stated pnl_pct | Recomputed Ratio | Issue |
|--------|----------|----------------|------------------|-------|
| `vix_reversal::SI=F` | vix_reversal | -3.6402 | -0.036402 | 100× off |
| `vix_reversal::SI=F` | vix_reversal | -3.4652 | -0.034652 | 100× off |
| `vix_reversal::SI=F` | vix_reversal | -0.04244 | -0.0400 | ≈ match |

Same symbol, same strategy, different rows use different units.

**Impact:** Cross-asset-class PnL aggregation wrong by up to 100×. Normalization required.

### Issue 2: Non-Unique Pick IDs

**Severity:** HIGH  
**Affected Files:** `multi_asset/data/multi_asset_closed.json`, `multi_asset/data/institutional_closed.json`  
**Description:** Pick IDs use date-only format (`<strategy>::<symbol>::<date>`), producing duplicates:

| Duplicate ID | Count |
|--------------|-------|
| `vix_reversal::SI=F::2026-03-11` | 4 |
| `extreme_oversold_bounce::EURUSD=X::2026-03-12` | 5 |
| `ema_stack_momentum::CL=F::2026-03-11` | 2 |
| `bb_mean_reversion_forex::NZDUSD=X::2026-03-13` | 2 |
| `connors_rsi2::SI=F::2026-03-12` | 2 |

### 4. Stale Picks

**Severity:** HIGH  
**Count:** ~30 stale OPEN picks

**`institutional_picks.json`:** All 22 picks dated 2026-04-03 (~7.5 months old), all OPEN, all `forward_test_only=true`, all `pnl_pct=null`.

**`recent_picks.txt`:** CL=F and ZN=F still OPEN from 2026-03-11 (~8 months old), header claims "Past 2 Hours" (WRONG).

### 4.5 `ml_score == confidence` Coupling

**Severity:** MEDIUM  
**Finding:** On every OPEN pick, `confidence == ml_score` exactly (0.75/0.592, 0.639/0.639, 0.600/0.600). ML score is a verbatim copy of confidence, not an independent ML output.

---

## 6. PROPOSED FIXES

### 4.1 Normalize PnL Units (P0)
**File:** `quick_wins/shared/normalize_pnl_units.py`  
**Action:** Recompute `pnl_pct = (exit_price / entry_price - 1) * direction` for all CLOSED picks. Store as decimal ratio (e.g., -0.04 = -4%). OPEN picks keep `pnl_pct=null`.

### 4.2 Make Pick IDs Unique (P0)
**File:** `multi_asset/scanner.py:_pick_id()`  
**Action:** Add timestamp component: `f"{strategy}::{symbol}::{dt.strftime('%Y%m%d_%H%M%S')}"`

### 4.3 Resolve Stale Open Picks (P0)
**File:** `multi_asset/data/institutional_picks.json`  
**Action:** Close or mark EXPIRED all picks dated 2026-04-03. Mark all 2026-11-12 picks as `forward_test_only=true` explicitly.

### 4.4 Decouple ml_score from confidence (P1)
**File:** `alpha_engine/equity_strategies.py` and all strategy modules  
**Action:** Compute `ml_score` independently from `confidence`. Do not copy confidence → ml_score.

---

## 7. GO/NO-GO DECISION

**CURRENT STATUS: NO-GO for live capital deployment.**

| Criterion | Threshold | Current Status | Verdict |
|-----------|-----------|----------------|---------|
| PnL ≥ 1.5 forward | 1.5 | 0.71–76.92 (n=6–12) | ❌ FAIL |
| WR ≥ 55% forward | 55% | 25%–83% (n < 12) | ❌ FAIL |
| Sharpe ≥ 0.5 forward | 0.5 | -0.48 to 1.14 | ❌ FAIL |
| DSR ≥ 0.95 forward | 0.95 | Not computed | ❌ FAIL |
| n ≥ 100 forward picks | 100 | Max n=12 | ❌ FAIL |
| 3+ months clean forward | 3 months | 0 days | ❌ FAIL |

**RECOMMENDATION:** Do not deploy capital to any strategy. All picks are paper-test-only. The highest-probability path to profitability is low-cost ETF/mutual fund passive allocation (beta capture), not active ML prediction.
