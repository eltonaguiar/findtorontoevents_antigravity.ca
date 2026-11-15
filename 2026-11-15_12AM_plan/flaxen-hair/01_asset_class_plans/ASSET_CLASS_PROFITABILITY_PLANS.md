# ASSET CLASS PROFITABILITY PLANS — Per-Class Roadmap to Profitability

**Worktree:** flaxen-hair_2026-11-15T0020 | **Date:** 2026-11-15T00:27Z | **Repo:** findtorontoevents_antigravity.ca

---

## Executive Summary

**Zero asset classes are currently proven profitable.** 0/23 hypotheses across 4 protocol versions survived clean out-of-sample, effective-N, capital, and execution gates. All 9 classes return `sizing_allowed: false`. The system is a research infrastructure, not a money-ready engine.

This document lays out the per-asset-class plan to achieve profitability, ranked by realistic probability.

---

## Asset Class Priority Ranking

| Rank | Asset Class | Probability | Primary Path | Blocker | Action Required |
|------|-------------|-------------|--------------|---------|-----------------|
| **1** | **Passive ETF/MF Allocation** | High (as allocation, not prediction) | Low-cost diversified index ETFs/mutual funds, buy-and-hold or simple rebalance | None (market beta works) | Deploy immediately as core portfolio |
| **2** | **EQUITY (US)** | Medium | Pre-registered benchmark test vs SPY total return | n≥500, PF≥1.15, clean OOS, stability both halves | Run benchmark test; if fails, hold index |
| **3** | **CRYPTO** | Low-Conditional | Fix `kimi_riseoftheclaw` fill bug, then forward-test POSITION horizon n≥100 | Entry_price ~29% clean, ~90% positions never resolve | Fix fill bug; forward-test |
| **4** | **COMMODITY / BOND** | Low | Clean COT data + treasury yield curves | Low n, cost/execution issues | Blocked until arithmetic clears |
| **5** | **ETF Tactical** | Low-Medium | Tactical asset allocation (smart-beta, not alpha) | n=88-100 at floor | Expand universe; validate look-ahead-free |
| **6** | **FOREX** | Very Low | Mutation-before-kill protocol | Zero DSR survivors; sub-floor PF | Blocked |
| **7** | **FUTURES** | None | Retire | WR 5.9%, PnL -96% | Formal retirement |
| **8** | **MEMECOIN/PENNY** | None | Quarantined | PF 0.50, deep oversold blocked | Keep blocked |
| **9** | **MUTUAL FUNDS** | N/A | Not a prediction class | Zero infrastructure exists | Build only if testing selection criteria; otherwise hold low-cost index funds |

---

## 1. EQUITY (US) — Slot 1 Research Candidate

**Current State:**
- n=447, WR 53.2%, PF 1.55 (cumulative, likely inflated)
- Recent WR 52.9%, PF 1.44 (degrading)
- connors_rsi2_scanner (SPY/QQQ): WR 75.7% — sole proven sleeve
- vix_spike_reversal_scanner (SPX): WR 72%
- t=1.52, p=0.12 (not statistically significant)
- Second-half PF fell 1.342 → 0.977 (regime risk)

**Pre-Registered Test Protocol:**

| Parameter | Requirement |
|-----------|-------------|
| Sample | 24 months, n ≥ 500 closed equity trades |
| Benchmark | SPY total return, same window (NOT zero) |
| Gate 1 | OOS Sharpe ≥ SPY Sharpe |
| Gate 2 | PF ≥ 1.15 |
| Gate 3 | Stability: first-half PF ≥ 1.05 AND second-half PF ≥ 1.05 |
| Kill condition | Fails any line → EQUITY is beta, stop emitting, hold index |

**Implementation Steps:**
1. Fix PnL normalization (ratio vs percent, 100× bug) across all equity picks
2. Backfill `asset_class`='EQUITY' for UNK equity picks via `alpha_engine/asset_class.py`
3. Refresh `current_price`/`unrealized_pnl` for stale active picks
4. Run Connors RSI2 scanner against SPY benchmark with T-bill cash overlay
5. Validate on clean OOS data only (no data snooping)

**Success Criteria:** PF ≥ 1.15, WR ≥ 55%, Sharpe ≥ SPY Sharpe, stability both halves → promote to paper trading. Otherwise → hold SPY/QQQ index.

---

## 2. CRYPTO — Slot 3 Conditional

**Current State:**
- n=1154 clean, WR 32.4%, PF 0.73 (NOT money-ready)
- 700+ strategies tested, ALL fail clean-cohort screen
- Root cause: entry_price ~29% clean (37% >10% off bar, 7% >50%), systematically +1.3% biased
- ~90% positions never resolve
- `intrabar_pnl_pct` rides the broken entry_price

**Pre-Conditions Before Any Alpha Hunt:**

| Fix | File | Priority |
|-----|------|----------|
| Fix entry_price integrity | alpha_engine/risk_controls.py | P0 |
| Re-resolve from bar-aligned NEXT-bar entries | tools/reresolve_intrabar.py | P0 |
| Deepen OHLCV history (≥180d 1h bars) | crypto_ohlcv ingest | BLOCKED (~30d today) |
| Kill crypto SWING emission | multi_asset/scanner.py | P0 |
| Resolve stale open positions (>72h) | audit_trail/universal_pick_resolver.py | P0 |

**Post-Fix Forward Test:**
- POSITION horizon only (not entry-bar)
- Frozen rules, n ≥ 100
- PF ≥ 1.3, WR ≥ 55%
- Regime filter: BTC > 200-EMA (bull regime only)
- Correlation limit: max 1 position per correlated group

**Kill Condition:** If post-fix forward test does not show PF ≥ 1.3 at n=100, retire crypto direction trading entirely.

---

## 3. ETF Tactical Asset Allocation — Primary Money Track

**Current State (VALIDATED):**
- Top-5 asset-class ETFs by 6-month momentum, monthly, abs-momentum filter → bonds
- Universe: 14 liquid free ETFs (yfinance)
- 2007-2026 (incl 2008 GFC): Sharpe 0.88 vs SPY 0.74, MaxDD −19% vs SPY −51%, Calmar 0.48 vs 0.21
- ALL 16 grid cells (top-N × lookback) cut MaxDD to −12/−17% vs SPY −24%
- 9-month region: Sharpe 1.09-1.21 / Calmar 0.81-1.10 vs SPY 1.00/0.68
- Positive all 3 time-thirds (both-halves stability)

**Implementation:**
- Universe: SPY, QQQ, IWM, EFA, EEM, TLT, IE, SHY, GLD, XLF, XLE, XLV, XLY, XLC
- Monthly rebalance, top-5 by 6-month momentum
- Abs-momentum filter: if all ETFs below cash-equivalent threshold, hold bonds/cash
- Position size: equal weight among top-5, max 20% per ETF

**Success Criteria:** Forward 6-12 months vs SPY with MaxDD < SPY MaxDD. This is smart-beta, NOT alpha — do not over-size.

---

## 4. COMMODITY / BOND — Blocked

**COMMODITY:**
- n≈27 post-filter (HG=F only), below min_trades=60
- Cost/PnL ratio 422%
- COT contrarian failed all 4 pre-registered checks
- **Action:** Enable CFTC_COT_FETCHER_ENABLED=1, populate data/cftc_cot/, add freshness guard

**BOND:**
- n=11-18, WR 54.5%, PF 0.66
- Requires BOND scanner + FRED data unblock
- No bond mutual fund data feed
- **Action:** Flip CFTC_COT_FETCHER_ENABLED=1, get FRED API key, populate data/cftc_cot/

---

## 5. FOREX — Blocked

**Current State:**
- WR 46.2%, PF 0.29 (stressed, sub-floor)
- SHORT-axis 57% WR vs LONG 21% on ig_contrarian_sentiment (36pp spread) but NO strategy passes DSR ≥ 0.5
- Zero DSR survivors
- PROVEN_STRATEGIES whitelist has zero forex strategies

**Action:** Apply mutation-before-kill protocol. If no forex strategy passes DSR ≥ 0.5 after mutation testing, retire forex emission entirely.

---

## 6. MUTUAL FUNDS — Zero Coverage

**Current State:** No algorithms, no data source, no asset class registration, no scanner, no strategies.

**If building (only if testing selection criteria, not as prediction):**

| Criterion | Threshold |
|-----------|-----------|
| Expense ratio | ≤ 0.20% |
| Load fees | None |
| 12b-1 fees | None |
| Min investment | ≤ $1,000 |
| AUM | ≥ $1B |
| Turnover | ≤ 20% |
| Tracking error | ≤ 0.25% |
| Track record | ≥ 10 years |
| NAV freshness | ≤ 24h |

**Implementation:**
1. Add `MUTUAL_FUND_SYMBOLS` frozenset to `alpha_engine/asset_class.py`
2. Register `"MUTUAL_FUND": 7` in `ml_gatekeeper/gatekeeper.py` ASSET_CLASS_MAP
3. Add `"mutual_fund"` to `_CAT_MAP` and `"mutual_fund": "MUTUAL_FUND"` in `_LOWER_TO_UPPER`
4. Add mutual fund handling to `asset_class_from_symbol()` and `normalize_asset_class()`
5. Add `"MUTUAL_FUND"` to dashboard `_PER_ASSET_CLASSES`, `_CANONICAL`, `_AC_TF_GRID_ASSET_CLASSES`
6. Create `alpha_engine/mutual_fund_strategies.py` (NAV-based monthly rebalance)
7. Create `audit_dashboard/data/mf_cache_manifest.json` (SHA-256 provenance)
8. Wire into PnL normalization + freshness gate (NAV-based daily rebalance, T+1 settlement)

**Recommendation:** Do NOT build mutual fund prediction. Instead, hold low-cost index mutual funds as core allocation.

---

## 7. Implementation Priority

| Phase | Timeline | Action | Success Gate |
|-------|----------|--------|--------------|
| Phase 1 | Week 1 | Measurement fixes (PnL normalization, gate fail-closed, QA validator) | Zero CRITICAL QA flags |
| Phase 2 | Weeks 2-4 | Mutual fund + ETF infrastructure | MF/ETF ready for testing |
| Phase 3 | Weeks 4-8 | EQUITY benchmark vs SPY; CRYPTO forward test post-fill-fix | EQUITY PF≥1.15 OR CRYPTO PF≥1.3 |
| Phase 4 | Weeks 9-13 | Go/No-Go decision | Promote to paper OR hold index |

**Success at day 90 is NOT "profitable."** It is one class with a pre-registered, benchmark-relative result and known trial count.

---
