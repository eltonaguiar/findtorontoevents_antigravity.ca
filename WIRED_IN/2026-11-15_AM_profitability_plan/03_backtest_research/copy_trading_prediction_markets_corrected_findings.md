# Copy Trading & Prediction Markets — Corrected Findings

**Date:** 2026-11-15 (AM)
**Status:** CORRECTS earlier claim that "copy trading and prediction markets have not produced winners"
**Source:** Actual repo backtest data, paper pilot results, per-class audits

---

## Executive Summary

**My earlier claim was wrong.** Copy trading and prediction markets DO have proven winners, but they are **class-specific**, not universal. The aggregate numbers mask per-class failures. The correct conclusion:

| Source | Best Class | WR | n | Status |
|--------|-----------|-----|---|--------|
| **multi_asset_copytrader** | COMMODITY | 93.8% | 96 | **REAL EDGE** (Tier-1 candidate) |
| **multi_asset_copytrader** | FOREX | 14.8% | 662 | Massive drain — BLOCK |
| **multi_asset_copytrader** | FUTURES | 2.5% | 157 | Critical drain — BLOCK |
| **multi_asset_copytrader** | EQUITY | 42.9% | 28 | Thin — insufficient sample |
| **prediction_market_consensus** | CRYPTO | 89.89% (backtest) / 79.09% (forward) | 89 / 110 | Strong but PBO=0.603 (overfitting risk) |
| **prediction_market_consensus** | CRYPTO (paper pilot) | 64.76% | 837 resolved | Promising forward results |

**Key insight:** Multi-class systems are aggregate-misleading. Class-level decomposition is the only honest read.

---

## 1. CopyTrader — Per-Class Breakdown

**Source:** `reports/multi_asset_copytrader_per_class_audit_20260513T014000Z.md`
**Data:** `alpha_engine/data/closed_picks.json` — 943 closed picks decomposed by asset_class

### Per-Class Results

| Class | n | WR % | Volume Share | Status | Action |
|-------|---|------|-------------|--------|--------|
| **COMMODITY** | 96 | **93.8%** | 6.4% | ✅ Real edge — pristine WR | **PRESERVE + AUDIT** |
| EQUITY | 28 | 42.9% | 1.9% | ⚠️ Thin (n<100) | Monitor |
| **FOREX** | 662 | **14.8%** | 44.0% | ❌ Massive drag | **MUTATE-BEFORE-KILL** |
| **FUTURES** | 157 | **2.5%** | 10.4% | ❌ Critical drain | **SURGICAL BLOCK** |

### Aggregate Masking Problem

Dashboard reports `multi_asset_copytrader` PF=4.28 / WR=47.3% / n=1505 / MDD=16.67%.

This aggregate is **misleading**. The COMMODITY 93.8% WR tail wins mask the FOREX/FUTURES drain. The system's true edge is COMMODITY-only.

### Peer Claim FALSIFIED

Peer Big Pickle claimed: "multi_asset_copytrader is your most robust system — PF 4.09, n=812, MDD 16.67%, spans 5 classes. Best candidate for go-live TODAY."

**Falsified on multiple counts:**
1. Spans 3-4 classes, not 5
2. NOT go-live ready — 44% of resolved volume is FOREX at 14.8% WR
3. True edge is COMMODITY-only, same as `multi_asset_cot` finding

### Recommended Actions

| ID | Action | Priority |
|----|--------|----------|
| Block `(FUTURES, multi_asset_copytrader)` | P0 — n=157, WR=2.5% is empirically dead |
| Mutate-before-kill `(FOREX, multi_asset_copytrader)` | P1 — 662 picks at 14.8% WR needs axis analysis |
| Preserve `(COMMODITY, multi_asset_copytrader)` | P0 — 96 picks at 93.8% WR is the legitimate edge |

---

## 2. Prediction Market Consensus — Performance Data

**Source:** `backtest_results/rigorous_backtest_CRYPTO_20260602_124831.json`, `verified_strategies/paper_pilot/`

### Backtest Results (CRYPTO)

| Metric | Value |
|--------|-------|
| Strategy | prediction_market_consensus |
| n | 89 |
| Raw Sharpe | 5.26 |
| Raw WR | 89.89% |
| Raw PF | 24.51 |
| Raw MDD | 0.60 (60%) |
| Costed Sharpe | 5.26 |
| Costed WR | 89.89% |
| Costed PF | 24.47 |
| Costed MDD | 0.60 (60%) |
| **DSR** | **9.36** |
| **PBO** | **0.603** ⚠️ |
| n_trials | 500 |

### Walk-Forward Results (7 folds)

| Fold | n_train | n_test | IS Sharpe | OS Sharpe | WFE | OS Total PnL |
|------|---------|--------|-----------|-----------|-----|--------------|
| 1 | 11 | 11 | 0.57 | 0.96 | 1.0 | +26.69 |
| 2 | 22 | 11 | 0.77 | 1.70 | 1.0 | +43.04 |
| 3 | 33 | 11 | 1.00 | 1.66 | 1.0 | +9.97 |
| 4 | 44 | 11 | 0.92 | 1.98 | 1.0 | +26.41 |
| 5 | 55 | 11 | 1.02 | 1.46 | 1.0 | +31.07 |

All folds: WFE=1.0, OS Sharpe > 0.95 — very consistent out-of-sample.

### Paper Pilot (Forward Testing)

| Metric | Value |
|--------|-------|
| Total picks | 1,016 |
| Resolved | 837 |
| Wins | 542 |
| Losses | 251 |
| Flats | 44 |
| **WR** | **64.76%** |
| **PF** | **2.02** |
| **Avg PnL** | **+2.36%** |
| **Max Drawdown** | **-69.17%** |
| Promotion ready | true |

### Forward Dashboard (Shadow Mode)

| Metric | Value |
|--------|-------|
| Forward n | 110 |
| Forward WR | 79.09% |
| Forward PF | 13.20 |
| Avg PnL | +2.35% |
| Total PnL | +258.6% |
| Shadow mode | true |
| Promotion ready | false |

### Critical Concern: PBO=0.603

PBO (Probability of Backtest Overfitting) = 0.603 means there's a ~60% probability the backtest results are overfitted. This is **above the 0.10 threshold** required for money-ready deployment.

**Recommendation:** Prediction market consensus is promising but NOT yet money-ready due to PBO > 0.10. Continue shadow mode forward testing. Kill switch: WR floor 55%, n_min 50.

---

## 3. Why Earlier Claim Was Wrong

I previously stated: "Despite access to Kalshi/Polymarket and copy-trading infrastructure, the system has zero proven profitable outputs."

This is **incorrect**. The data shows:

1. **CopyTrader COMMODITY**: WR=93.8%, n=96 — a real, class-specific edge
2. **Prediction Market Consensus**: Backtest WR=89.89%, forward WR=79.09%, paper pilot WR=64.76% — strong results but PBO=0.603
3. **Both are under-utilized**: Prediction markets used only for scoring boosts, not primary pick generation. CopyTrader volume is low compared to other scanners.

### The Real Problem

The system's issues with copy trading and prediction markets are:

1. **Aggregate masking**: Class-level performance hidden by aggregate numbers (FOREX/FUTURES drag masks COMMODITY edge)
2. **Low primary volume**: Both sources used mainly for scoring boosts, not primary pick emission
3. **PBO overfitting risk**: Prediction market consensus has PBO=0.603, above the 0.10 gate
4. **Not wired into active picks**: `prediction_market_picks.json` shows `pick_count: 0` — not currently emitting

---

## 4. Recommended Integration Path

### For CopyTrader (COMMODITY focus)

```
1. Block (FUTURES, multi_asset_copytrader) — P0, immediate
2. Run mutation-axes on (FOREX, multi_asset_copytrader) — P1
3. Preserve and scale (COMMODITY, multi_asset_copytrader) — P0
4. Cross-reference with multi_asset_cot (COMMODITY WR=94.1%, n=102)
5. Build dedicated COMMODITY copy-trader emitter with elite filtering
```

### For Prediction Markets (CRYPTO focus)

```
1. Continue shadow mode forward testing — n=110, WR=79.09%, PF=13.20
2. Address PBO=0.603 — need more independent data or parameter reduction
3. Wire into primary pick emission (currently pick_count=0)
4. Set kill switch: WR < 55% or n < 50
5. Combine with CopyTrader intel for multi-source "smart money" consensus
```

---

## 5. Trusted Copy Traders (Documented)

**Source:** `trusted_copy_traders.md`

Curated proven copy traders across platforms:

| Platform | Top Trader | 90-Day/30-Day ROI | AUM | Win Rate |
|----------|-----------|-------------------|-----|----------|
| OKX | Expert-Ethash-Camel | +1,053.34% | $164K | — |
| OKX | nightraid- | +255.31% | $164K | — |
| Bitget | Bg-ATM | +57.48% | $117K | 90.3% |
| Bitget | ICHIZENCapital | +4,302% (lifetime) | — | — |
| Hyperliquid | 0x393d...2109 | +30.59% | $849M | — |

**Integration path:** Integrate trader IDs into `alpha_engine/copy_trader_analyzer.py`, monitor via APIs, apply risk rules from `alpha_engine/portfolio_tracker_copytrader.py`.

---

## 6. Updated Asset-Class Recommendation

| Asset Class | Best Source | WR | n | Money-Ready? |
|-------------|------------|-----|---|--------------|
| COMMODITY | multi_asset_copytrader / multi_asset_cot | 93.8% / 94.1% | 96 / 102 | **Tier-1 candidate** — DB-verify pending |
| CRYPTO | prediction_market_consensus | 79.09% (forward) | 110 | Shadow mode — PBO too high |
| EQUITY | — | — | — | No proven source |
| FOREX | — | 14.8% (copytrader) | 662 | BLOCK |
| FUTURES | — | 2.5% (copytrader) | 157 | BLOCK |
| MUTUAL FUNDS | — | — | — | Passive allocation only |
| ETF | — | — | — | Cohort mismatch, blocked |

**New primary recommendation:** COMMODITY via copy trader / COT consensus is the strongest single edge across the entire dashboard (WR 93.8-94.1%, n=96-102). This should be the Tier-1 go-live candidate, not EQUITY or CRYPTO as previously stated.

---

## 7. Files Referenced

| File | What It Contains |
|------|-----------------|
| `reports/multi_asset_copytrader_per_class_audit_20260513T014000Z.md` | Per-class copy trader audit |
| `backtest_results/rigorous_backtest_CRYPTO_20260602_124831.json` | Prediction market consensus backtest (n=89) |
| `verified_strategies/paper_pilot/prediction_market_consensus_pilot.json` | Paper pilot results (n=1016) |
| `verified_strategies/paper_pilot/prediction_market_consensus_dashboard.json` | Forward dashboard (n=110) |
| `trusted_copy_traders.md` | Curated proven copy traders |
| `alpha_engine/data/prediction_market_picks.json` | Live picks (currently pick_count=0) |
| `copy_trader_intel/data/copy_trader_patterns.json` | Consensus picks data |
| `alpha_engine/data/copy_trader_patterns.json` | Copy trader pattern analysis |
