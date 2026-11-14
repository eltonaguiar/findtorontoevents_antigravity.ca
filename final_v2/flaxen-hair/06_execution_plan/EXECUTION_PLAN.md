# Execution Plan — final_v2

**Date:** 2026-11-14 | **Worktree:** flaxen-hair

## Phase 1: Immediate (This Week)

### 1.1 Paper Trade mega_mutation on Crypto
- **Action:** Run `quick_wins/shared/daily_forward_tracker.py --once` daily
- **Output:** Picks logged to `quick_wins/shared/gated_picks.jsonl`
- **Status:** Scanner ready; currently emits 0 picks (BTC below 200-EMA bear regime — correct behavior)
- **Owner:** System (automated)

### 1.2 Monitor Forward Performance
- **Action:** Track TP/SL hits on emitted picks
- **Target:** Accumulate n=100 forward picks for T2 confirmation (currently n=50)
- **Success criteria:** WR ≥ 55%, PF ≥ 1.5 after n=100
- **Owner:** System (automated)

### 1.3 Fix PnL Unit Bug (Already Done)
- **Action:** Normalized `pnl_pct` across `multi_asset_closed.json` (93 rows) and `institutional_closed.json` (23 rows)
- **Status:** Complete — decimal ratio units enforced
- **Verification:** `quick_wins/shared/normalize_pnl_units.py` — run on any closed-pick JSON file

### 1.4 Fix Pick ID Uniqueness (Already Built)
- **Action:** `quick_wins/shared/validate_pick_ids.py` — CI-enforced unique pick IDs
- **Status:** Complete — ready for CI integration

---

## Phase 2: Next Sprint (2-4 Weeks)

### 2.1 Clean Forward OOS Test of H10 RSI(2) on SPY/QQQ
- **Action:** Run `research/profitability/backtest.py` with frozen H10 parameters
- **Protocol:** Start after 2026-11-13, minimum 90 calendar days or 30 round trips
- **Gates:** DSR ≥0.95 after N≥38, DSR ≥0.95 after removing best day, 2-day-lag Sharpe ≥1.0
- **Risk-matched benchmark:** Compare against ~17% SPY/QQQ + ~83% T-bill mix (rf=0 Sharpe 2.168-2.285)
- **Owner:** Manual execution

### 2.2 Apply finpredict-v4 6-Gate Scoring to All Strategies
- **Action:** Run `alpha_engine/statistical_scoring_framework.py` on all strategies
- **Output:** Certification results (FAIL/DISCOVERY/VALIDATED/MONEY_READY)
- **Owner:** Manual execution

### 2.3 Develop New Hypotheses for Untested Asset Classes
- **Bonds:** Bond ETF TSMOM (TLT, IEF, SHY, TBT)
- **Mutual funds:** Monthly NAV-based dual momentum (add MUTUAL_FUND class)
- **Forex:** Carry trade + trend following on major pairs
- **Commodities:** TSMOM on GC=F, SI=F, CL=F, ZN=F, NG=F
- **Owner:** Strategy development

---

## Phase 3: Medium-Term (1-3 Months)

### 3.1 Promote to Live Capital
- **Criteria:** n≥100 forward picks, WR ≥ 55%, PF ≥ 1.5, pf_drift < 30%, all 6 gates passing
- **Action:** Flip `production_enable = true`, allocate capital
- **Start small:** Minimal capital allocation, scale up after 3+ months clean performance

### 3.2 Address ENA Collinearity Risk
- **Action:** Verify mega_mutation edge isn't just funding-rate arbitrage on ENA
- **Method:** Test edge with and without ENA; check funding rate correlation
- **Owner:** Strategy research

### 3.3 Independent Replication
- **Action:** Have separate agent/team replicate v4 funding carry results
- **Requirement:** Venue-level capital/margin data
- **Owner:** External validation

---

## Phase 4: Long-Term (3-6 Months)

### 4.1 New Data Sources
- **Action:** Acquire intraday/order-book data, options/vol-risk-premium data, venue-level capital data
- **Rationale:** Keyless data hypothesis space is exhausted (23 hypotheses, NONE PROVED)
- **Owner:** Data acquisition

### 4.2 Heterogeneous Stacking
- **Action:** Stack LightGBM + GRU-Attention + Ridge linear model as meta-features
- **Source:** Components exist in `ml_battleground/` but not wired together
- **Owner:** ML engineering

### 4.3 Prediction Tail Clipping
- **Action:** Clip ensemble outputs to [2nd, 98th] percentile of training-set predictions
- **Rationale:** Reduce variance from outlier predictions
- **Owner:** ML engineering

---

## Go/No-Go Criteria

### GO (Promote to Live)
- [ ] n ≥ 100 forward picks
- [ ] WR ≥ 55%
- [ ] PF ≥ 1.5
- [ ] pf_drift < 30%
- [ ] All 6 gates passing (finpredict-v4 framework)
- [ ] 3+ months of clean forward performance

### NO-GO (Stay in Paper/Halt)
- [ ] n < 100 forward picks
- [ ] WR < 55%
- [ ] PF < 1.5
- [ ] Any gate failing
- [ ] DSR < 0.95
- [ ] Regime filter fails (bear market)

---

## Timeline Summary

| Phase | Timeline | Key Milestone |
|-------|----------|---------------|
| Phase 1 | Week 1 | Daily paper trading, n=100 forward target |
| Phase 2 | Weeks 2-4 | H10 clean forward test, 6-gate scoring, new hypotheses |
| Phase 3 | Months 1-3 | Live capital promotion (if criteria met) |
| Phase 4 | Months 3-6 | New data sources, heterogeneous stacking |

---

## Emergency Stop Conditions

| Condition | Action |
|-----------|--------|
| Any gate fails for 2 consecutive weeks | Halt all live trading |
| Drawdown exceeds -20% monthly cap | Halt all trading for month |
| 3 consecutive losing sessions | Halt for session, review regime |
| Data staleness > T-1 day | No new picks until refreshed |
| Exchange counterparty risk | Reduce exposure, diversify venues |
