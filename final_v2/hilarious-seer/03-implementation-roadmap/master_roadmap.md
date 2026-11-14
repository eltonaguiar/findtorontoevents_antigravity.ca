# Master Implementation Roadmap — From FAIL to MONEY-READY

**Date:** 2026-11-14
**Worktree:** hilarious-seer
**Status:** Synthesis of all peer work (finpredict v1-v4, flaxen-hair, scratch-hippodraco, childlike-airport)

---

## Current State Summary

| Asset Class | Status | Best Strategy | Realistic Sharpe | Time to Deploy |
|-------------|--------|---------------|------------------|----------------|
| **CRYPTO** | Best Candidate | Vol-targeted trend (ITERATION-005) | 0.5–2.1 | 2–3 months |
| **EQUITY** | NOT_PROVED | RSI(2) on SPY/QQQ (needs clean forward) | 0.4–0.8 | 6–9 months |
| **ETF** | NOT_PROVED | Multi-asset trend (needs build) | 0.4–0.8 | 6–9 months |
| **FOREX** | Pure Gap | Carry basket (needs feed) | 0.3–0.6 | 6–9 months |
| **BONDS** | INSUFFICIENT_DATA | Duration trend (needs feed) | 0.3–0.6 | 6–9 months |
| **FUTURES** | BLOCKED | CTA trend (needs real feed) | 0.5–1.0 | 12+ months |
| **COMMODITIES** | BLOCKED | Carry + momentum (needs real feed) | 0.3–0.7 | 12+ months |
| **MUTUAL FUNDS** | NOT_BUILT | None (monthly NAV incompatible) | N/A | Do not build |

---

## Phase 0: Stop the Bleed (Weeks 1–2) — ABSOLUTE P0

**Goal:** Make measurement trustworthy. No strategy can be proven on garbage data.

### Week 1: PnL Unit Contract
- [ ] Standardize ALL PnL columns to **decimal ratio** (not percent)
  - `mercury2/scanner.py`: change `* 100` to ratio
  - `copy_trader_intel/outcome_resolver.py`: already ratio — keep
  - `sync_all_picks_to_mysql.py`: remove `pnl *= 100` heuristic
  - `dashboard/generate_dashboard.py`: add `%` sign only when displaying percent
- [ ] Direction-aware recompute: LONG `(cur-entry)/entry`, SHORT `(entry-cur)/entry`
- [ ] Spot-check 50 random rows vs live Binance/Yahoo prices
- [ ] Run `quick_wins/shared/normalize_pnl_units.py` across all stores

### Week 1: Price Freshness Pipeline
- [ ] Wire `alpha_engine/universal_price_enricher.py` into `audit-dashboard.yml` hourly cron
- [ ] Label `UNQUOTED` (never fabricated `0%`) when feed fails
- [ ] Fix `fetch_stock_prices.py` 60s timeout (raise to 300s or make non-fatal)
- [ ] Verify forex cache (`data/forex_rate_cache/`) updates from 161d stale
- [ ] Verify commodity cache (`data/commodity_price_cache/`) updates

### Week 2: Zombie Drain + Dedup
- [ ] Quarantine picks >30 days stale to `zombie_ledger` (do NOT delete)
- [ ] Dedup by composite key: `(symbol, strategy, direction, entry_time, entry_price)`
- [ ] Resolve TIME_EXIT picks via `universal_pick_resolver.py` with live prices
- [ ] Fix resolver output persistence (`audit_trail/data/universal_resolved_picks.json`)
- [ ] Ensure `pick_history` has ≥10% CLOSED/TP/SL events (up from 0%)

### Week 2: Store Reconciliation
- [ ] Make `live_picks.db` the single source of truth for active picks
- [ ] MySQL and dashboard JSON become read-only mirrors
- [ ] Run `tools/cross_db_consistency.py` and resolve all orphaned keys
- [ ] `db_freshness.json` overall = GREEN

**Success Criteria (Phase 0 Gate):**
- All ACTIVE picks have `current_price` within 1% of live market price
- PnL sign matches price move for 100% of spot-checked rows
- `pick_history` has ≥10% CLOSED/TP/SL events
- Zero duplicate pick IDs within same system
- `db_freshness.json` overall = GREEN

---

## Phase 1: Prove CRYPTO (Months 1–3)

**Goal:** Get one asset class to MONEY-READY. CRYPTO is the only candidate with evidence.

### Month 1: Fresh Backtest
- [ ] Run ITERATION-005 (vol-targeted trend) on fresh price data
- [ ] Add survivorship-adjusted universe (include delisted coins)
- [ ] Add taker-cost stress: test 0.1%, 0.15%, 0.2% per side
- [ ] Restate vs buy-and-hold benchmark (paired bootstrap)
- [ ] Report: Sharpe, PF, WR, maxDD, benchmark excess, MC timing percentile

### Month 1: Statistical Gates
- [ ] Run through `StrategyCertifier` (finpredict-v4 6-gate framework)
- [ ] Gate 0: n≥60, no NaN, no zero variance
- [ ] Gate 1: Bootstrap 95% CI PF_lower > 1.0, Sharpe_lower > 0
- [ ] Gate 2: Walk-forward ≥60% profitable folds, mean OOS PF > 1.2
- [ ] Gate 3: Gross PF > 1.5, Sharpe > 1.0, WR > 50%, Sortino > 1.5
- [ ] Gate 4: Net PF > 1.2, Sharpe > 0.5, WR > 45%, DSR > 0.95
- [ ] Gate 5: Direction validation (LONG-only is fine)

### Month 2: Add Missing Gates
- [ ] Port `benchmark_closed_ledger.py::random_entry_mc` as Gate 2b (MC timing ≥0.90)
- [ ] Port `benchmark_closed_ledger.py::paired_bootstrap` as Gate 1b (pass_95 = true)
- [ ] Add purged k-fold CV (from `admissibility_pipeline.py`)
- [ ] Add regime stratification (bull/bear/chop labels from `regime_flip_detector.py`)

### Months 2–3: Paper Trading
- [ ] Deploy with 2% risk per trade
- [ ] Daily PnL log
- [ ] Weekly StrategyCertifier run on rolling 90-day window
- [ ] If any gate fails for 7 consecutive days, auto-demote to paper

**Success Criteria (Phase 1 Gate):**
- 90-day paper PF > 1.5 post-costs
- DSR > 0.95
- MC timing percentile ≥ 0.90
- Paired bootstrap pass_95 = true
- Max drawdown < 25%

---

## Phase 2: Build Diversifiers (Months 3–9)

**Goal:** Add ETF and EQUITY sleeves to reduce portfolio volatility.

### Months 3–5: ETF Multi-Asset Trend
- [ ] Build 10+ year ETF price database (50 ETFs)
- [ ] Implement risk-parity trend backtest
- [ ] Add cost model + regime filter
- [ ] Walk-forward analysis (10-fold)
- [ ] Paper trading (if backtest passes)

### Months 5–7: EQUITY RSI(2) or Fundamental Factor
- [ ] If H10 clean forward OOS passes: deploy RSI(2) on SPY/QQQ
- [ ] Else: build fundamental factor backtest (Piotroski + value + quality)
- [ ] Market-neutral long/short construction
- [ ] Paper trading

### Months 7–9: Blend Portfolio
- [ ] CRYPTO trend (60%) + ETF trend (20%) + EQUITY (15%) + Cash (5%)
- [ ] Risk-parity weighting across sleeves
- [ ] Portfolio-level Sharpe, PF, maxDD
- [ ] Stress test: 2008, 2020, 2022 bear markets

---

## Phase 3: Expand to Other Classes (Months 9–18)

**Goal:** Add FOREX, BONDS as low-return diversifiers.

### Months 9–12: FOREX Carry Basket
- [ ] Wire real forex feed (Frankfurter/OANDA)
- [ ] Build carry feed (FRED/ECB rates)
- [ ] Backtest carry + trend overlay
- [ ] Paper trading

### Months 12–15: BONDS Duration Trend
- [ ] Wire FRED for Treasury yields
- [ ] Backtest duration rotation (TLT/IEF/SHY)
- [ ] Paper trading

### Months 15–18: FUTURES (If Prerequisites Met)
- [ ] Procure real futures data feed
- [ ] Build roll handling + continuous contracts
- [ ] Backtest CTA trend
- [ ] Remove from BLOCKED_ASSET_CLASSES
- [ ] Paper trading

---

## Continuous Monitoring (All Phases)

| Check | Frequency | Action on Failure |
|-------|-----------|-------------------|
| Price freshness | Hourly | Alert if any class >24h stale |
| PnL unit sanity | Daily | CI gate fails if mixed units detected |
| StrategyCertifier | Weekly | Demote to paper if any gate fails 7 days |
| Benchmark re-run | Monthly | Regenerate `benchmark_ledger_proof.json` |
| Cross-DB consistency | Daily | Alert on orphaned keys |
| Zombie scan | Daily | Quarantine >30d stale picks |

---

## Resource Allocation

| Phase | Dev Effort | Data/Infra | Statistical | Total |
|-------|-----------|------------|-------------|-------|
| Phase 0 (Stop Bleed) | 2 weeks | 1 week | 0 | **3 weeks** |
| Phase 1 (Prove CRYPTO) | 4 weeks | 2 weeks | 4 weeks | **10 weeks** |
| Phase 2 (Diversifiers) | 12 weeks | 8 weeks | 4 weeks | **24 weeks** |
| Phase 3 (Expand) | 16 weeks | 12 weeks | 4 weeks | **32 weeks** |

**Total to first MONEY-READY class (CRYPTO): ~3 months**
**Total to diversified portfolio: ~9 months**
**Total to full 8-class coverage: ~18 months**

---

## Risk Factors

1. **Phase 0 fails** — if price feed cannot be fixed (APIs down, rate limits), no strategy can be proven
2. **CRYPTO trend fails fresh backtest** — if ITERATION-005 does not pass gates on clean data, restart with new strategy search
3. **Bear market** — if CRYPTO enters prolonged bear during paper trading, PF may drop below 1.5; extend paper period
4. **API costs** — real-time price feeds (Binance, yfinance, FRED) may have rate limits or costs
5. **Team bandwidth** — 18-month roadmap requires sustained focus; prioritize Phase 0 + Phase 1

---

## Decision Gates

| Gate | Criteria | Go / No-Go |
|------|----------|------------|
| Phase 0 Complete | All success criteria met | Required before any strategy work |
| Phase 1 Complete | CRYPTO paper PF > 1.5 for 90 days | Required before real capital |
| Phase 2 Start | CRYPTO live PF > 1.2 for 30 days | Required before adding diversifiers |
| Phase 3 Start | Portfolio Sharpe > 0.8 | Required before expanding to other classes |

---

## Bottom Line

**The path is clear but long.** Fix data first (3 weeks). Prove CRYPTO (3 months). Build diversifiers (6 months). Expand to other classes (9 months). **Do not skip Phase 0.** Every peer audit concluded the same thing: edge collapses to coin-flip on dirty data. Phase 0 is the foundation. Everything else is decoration.
