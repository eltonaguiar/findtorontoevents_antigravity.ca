# Deep Audit Performance Analysis

**Date:** 2026-04-22
**Scope:** All asset classes under findtorontoevents.ca/audit
**Data Source:** `audit_dashboard/data/dashboard_data.json`
**Total Systems:** 120
**Total Closed Picks:** 24,972 (valid: 10,755)
**Total Resolved:** 11,529

---

## Executive Summary

The audit dashboard shows **catastrophic performance** across most asset classes. Only **EQUITY** is genuinely healthy. **FOREX** is in critical condition with a profit factor of 0.27 and -973% PnL. **CRYPTO**, despite the highest trade volume (22,128 trades), is stressed with a profit factor of 0.99 and -122% PnL.

### Top-Level Headlines
- **Overall PnL:** -1,031.68% raw / -274.31% capped / -100% compounded EW
- **Overall Win Rate:** 39.4%
- **Profit Factor:** 0.91 (losing system)
- **Sharpe:** -0.10 (net) / -1.59 (annualized)
- **Max Drawdown:** 1,597.88%
- **Calmar Ratio:** -0.65
- **Sortino:** -6.36 annualized

### Critical Finding: Concentration Risk
**42.5% of total PnL comes from a single symbol: USDCHF=X** (-438.72%). Removing this symbol improves overall PnL from -1,031.7% to -593.0%.

---

## Asset Class Performance Ranking

| Asset Class | Status | Win Rate | Profit Factor | PnL % | Closed Trades | Grade |
|-------------|--------|----------|---------------|-------|---------------|-------|
| **EQUITY** | stable | 53.3% | 1.39 | **+217.38%** | 781 | A |
| **COMMODITY** | watch | 43.6% | 1.07 | +5.56% | 579 | C |
| **BOND** | thin_sample | 50.0% | 1.60 | +2.84% | 17 | B |
| **ETF** | stable | 52.1% | 1.01 | +0.60% | 88 | C |
| **UNKNOWN** | insufficient_data | 60.0% | 4.59 | +0.18% | 7 | N/A |
| **CRYPTO** | stressed | 41.8% | 0.99 | -122.25% | 22,128 | F |
| **FOREX** | stressed | 47.1% | 0.27 | -973.36% | 1,413 | F |
| **FUTURES** | insufficient_data | 0.0% | N/A | 0.00% | 21 | N/A |
| **SPORTS** | insufficient_data | 0.0% | N/A | 0.00% | 0 | N/A |

**Only 2 of 9 asset classes are profitable** (Equity and Bond). Bond has insufficient sample size (n=17).

---

## Deep Dive: Critical Asset Classes

### 1. FOREX (CRITICAL)

**Status:** STRESSED | **Grade:** F

**Key Metrics:**
- Closed Trades: 1,413
- Win Rate: 47.1%
- Profit Factor: **0.27** (extremely poor)
- PnL: **-973.36%**
- Avg Win: 0.78% | Avg Loss: 2.59%
- Expectancy: -1.0% per trade

**Root Cause Analysis:**

The forex division is the single largest drag on portfolio performance, contributing **-973%** to total PnL. The profit factor of 0.27 means for every $1 won, $3.70 is lost.

**Top Losing Symbols:**
1. **USDCHF=X**: -444.26% (42.5% of total portfolio PnL)
2. **AUDJPY=X**: -208.13%
3. **NZDJPY=X**: -205.67%
4. **AUDUSD=X**: -171.95%

These 4 symbols alone account for **-1,030%** in losses -- essentially the entire portfolio loss.

**Worst Performing Systems in FOREX:**
1. `kimi_signal_tracking`: WR 31.1%, PF 0.28, PnL -1,001.41%, n=206
2. `alpha_engine_fast`: WR 39.3%, PF 0.60, PnL -133.81%, n=262
3. `cta_replicator`: WR 8.3%, PF 0.64, PnL -3.26%, n=132
4. `forex_copy_trader`: WR 2.2%, PF 0.31, PnL -0.46%, n=45

**Diagnosis:**
- **Massive asymmetry in wins vs losses:** avg win is only 0.78% while avg loss is 2.59% (3.3x larger)
- **Extreme concentration risk:** USDCHF=X dominates losses
- `kimi_signal_tracking` is the single worst system across ALL asset classes, destroying -1,001% alone
- Most forex systems show win rates below 40%, meaning they lose more than they win
- The `cta_replicator` has an 8.3% win rate -- effectively random guessing with transaction costs

**Immediate Actions Required:**
1. **HALT all FOREX trading** until the profit factor exceeds 1.0 on a 50-trade rolling window
2. **Investigate `kimi_signal_tracking`** -- it may have a data feed error or logic bug
3. **Cap position size on USDCHF=X, AUDJPY=X, NZDJPY=X** to max 2% of book each
4. **Review stop-loss logic** -- avg loss 2.59% on a 0.78% avg win suggests stops are too wide
5. **Check for overfitting** in forex strategies -- many have backtest WR >> forward WR

---

### 2. CRYPTO (CRITICAL)

**Status:** STRESSED | **Grade:** F

**Key Metrics:**
- Closed Trades: 22,128 (86% of all trades)
- Win Rate: 41.8%
- Profit Factor: **0.99** (breakeven)
- PnL: **-122.25%**
- Avg Win: 2.45% | Avg Loss: 1.78%
- Expectancy: -0.01% per trade

**Root Cause Analysis:**

Crypto represents **86% of all trades** but is essentially a breakeven asset class (PF 0.99). This massive volume of neutral trades consumes capital, margin, and attention without generating returns.

**Top Losing Symbols:**
1. **OPUSDT**: -115.09%
2. **ARBUSDT**: -93.64%
3. **APEUSDT**: -82.97%
4. **HBARUSDT**: -53.39%
5. **ALGOUSDT**: -47.24%

**Worst Performing Systems in CRYPTO:**
1. `kimi_signal_tracking`: WR 31.1%, PF 0.28, PnL -1,001.41%, n=206
2. `copy_trader_intel`: WR 34.5%, PF 0.61, PnL -753.29%, n=333
3. `claude_gainer_st`: WR 37.0%, PF 0.83, PnL -159.30%, n=1,274
4. `mercury2_fast`: WR 42.9%, PF 0.07, PnL -139.53%, n=7
5. `alpha_engine_fast`: WR 39.3%, PF 0.60, PnL -133.81%, n=262

**Critical Findings:**

1. **Backtest vs Forward Degradation (EXTREME):**
   - 78 strategies show >10pp forward degradation
   - Top offenders:
     - `crypto_soc_intraday_time_slices_a07_v1`: BT 56.0% -> FWD 0.0% (56.0pp drop)
     - `crypto_soc_intraday_time_slices_a01_v1`: BT 50.0% -> FWD 0.0% (50.0pp drop)
     - `crypto_soc_trend_filtered_meanrev_a09_v1`: BT 36.0% -> FWD 0.0% (36.0pp drop)
     - `crypto_soc_proxy_decoupling_a03_v1`: BT 66.0% -> FWD 32.7% (33.3pp drop)
   - Many strategies with 0% forward win rate are still active

2. **Strategy Bleeders:**
   - `copy_trader_intel` has -753% PnL on 333 trades -- this is a capital incinerator
   - `claude_gainer_st` has -159% on 1,274 trades -- high volume, consistent losses
   - `mercury2_fast` has PF 0.07 -- for every $1 won, $14.30 is lost

3. **Time-of-Day Edge (from PR #291):**
   - 50 percentage point time-of-day edge found in asset class analysis
   - Current strategies do not exploit this edge
   - Phase-1 TOD block (16-21 UTC) is too narrow

**Immediate Actions Required:**
1. **Kill `copy_trader_intel`, `claude_gainer_st`, `mercury2_fast`** -- these are confirmed bleeders
2. **Deactivate all strategies with BT/FWD degradation >30pp** until rehabilitated
3. **Implement TOD-aware gating** per PR #294 (extend 16-21 UTC block + add conf dead-zone)
4. **Cap altcoin exposure** -- OP, ARB, APE, HBAR, ALGO are all >-40% contributors
5. **Review `kimi_signal_tracking` across ALL asset classes** -- it's destroying -1,001% globally

---

### 3. COMMODITY (WATCH)

**Status:** WATCH | **Grade:** C

**Key Metrics:**
- Closed Trades: 579
- Win Rate: 43.6%
- Profit Factor: 1.07 (barely profitable)
- PnL: +5.56%
- Avg Win: 0.35% | Avg Loss: 0.25%
- Expectancy: +0.01% per trade

**Root Cause Analysis:**

Commodity is technically profitable but the margin is razor-thin (PF 1.07). With 579 trades generating only +5.56%, the expectancy is effectively zero after transaction costs.

**Worst Systems:**
1. `copy_trader_intel`: WR 34.5%, PF 0.61, PnL -753.29% (cross-asset class leech)
2. `alpha_engine_fast`: WR 39.3%, PF 0.60, PnL -133.81%
3. `cta_replicator`: WR 8.3%, PF 0.64, PnL -3.26%

**Immediate Actions Required:**
1. **Raise minimum PF threshold to 1.15** for commodity -- 1.07 is insufficient
2. **Investigate transaction cost assumptions** -- thin margins may turn negative with slippage
3. **Review commodity symbol selection** -- focus on highest-volume, most-liquid contracts

---

### 4. ETF (WATCH)

**Status:** STABLE | **Grade:** C

**Key Metrics:**
- Closed Trades: 88
- Win Rate: 52.1%
- Profit Factor: 1.01 (essentially flat)
- PnL: +0.60%
- Avg Win: 2.43% | Avg Loss: 2.62%

**Root Cause Analysis:**

ETF performance is essentially breakeven. The win rate is above 50%, but avg losses exceed avg wins (2.62% vs 2.43%), indicating poor risk/reward ratio.

**Worst Systems:**
1. `goldmine_stocks`: WR 0.0%, PF 0.00, PnL -39.79%, n=9
2. `institutional_picks_engine`: WR 25.0%, PF 0.32, PnL -6.32%, n=4
3. `alpha_engine_fast`: WR 39.3%, PF 0.60, PnL -133.81%

**Immediate Actions Required:**
1. **Kill `goldmine_stocks`** -- 0% win rate is unacceptable
2. **Review leverage assumptions** in ETF strategies -- losses > wins suggests over-leveraging
3. **Investigate ETF misclassification** (PR #313) -- some may be misclassified as equity

---

### 5. EQUITY (HEALTHY)

**Status:** STABLE | **Grade:** A

**Key Metrics:**
- Closed Trades: 781
- Win Rate: 53.3%
- Profit Factor: 1.39
- PnL: **+217.38%**
- Avg Win: 4.11% | Avg Loss: 3.36%
- Expectancy: +0.62% per trade

**Analysis:**

Equity is the **only genuinely healthy asset class**. It has:
- Positive expectancy (+0.62% per trade)
- Win rate above 50% (53.3%)
- Profit factor above 1.2 (1.39)
- Highest avg win (4.11%) among all asset classes
- Best risk/reward ratio (avg win > avg loss)

**Best Performing Systems:**
- `alpha_engine`: WR 40.5%, PF 1.10, PnL +195.59%, n=3,358
- `multi_asset_copytrader`: WR 27.2%, PF 1.45, PnL +44.59%, n=988

**Recommendation:**
- **Double equity allocation** -- it's the only asset class generating alpha
- **Study equity strategies** and replicate their logic in other asset classes
- Equity's success may be due to longer holding periods and better fundamentals filtering

---

### 6. FUTURES (INSUFFICIENT DATA)

**Status:** INSUFFICIENT_DATA | **Grade:** N/A

**Key Metrics:**
- Closed Trades: 21
- Win Rate: 0.0%
- Profit Factor: N/A
- PnL: 0.00%

**Analysis:**
Only 21 closed trades across 4 systems. Not enough data to draw conclusions.

**Recommendation:**
- **Pause futures trading** until at least 100 closed trades per strategy
- Or **increase futures allocation** to gather data faster if capital allows

---

### 7. SPORTS (INSUFFICIENT DATA)

**Status:** INSUFFICIENT_DATA | **Grade:** N/A

**Key Metrics:**
- Closed Trades: 0
- Active Picks: 1

**Analysis:**
Sports has zero closed trades. The single active pick has no realized PnL yet.

**Recommendation:**
- Either **commit to sports** with dedicated capital and tracking, or **remove it** from the active book

---

## Regime Performance

| Regime | Win Rate | Trades |
|--------|----------|--------|
| RANGING | 0.0% | 9 |
| TRENDING_DOWN | 6.2% | 16 |

**Critical Finding:** Strategies perform catastrophically in ranging and trending-down markets.
- Ranging: 0% win rate (0/9)
- Trending down: 6.2% win rate (1/16)

This suggests the strategy suite is **only effective in uptrends**. There is no hedging or short-selling capability.

**Recommendation:**
1. **Add short-biased strategies** for trending-down regimes
2. **Implement regime detection** and reduce exposure during ranging markets
3. **Study PR #309** (regime x strategy-style matcher)

---

## Timeframe Performance

| Period | Raw PnL | Profit Factor | Max Drawdown |
|--------|---------|---------------|--------------|
| 24h | +7.2% | 1.05 | 54.5% |
| 7d | -994.8% | 0.74 | 1,259.5% |
| 30d | +328.6% | 1.05 | 1,053.3% |
| All | -1,031.7% | 0.91 | 1,597.9% |

**Analysis:**
- Short-term (24h) is slightly positive but with 54.5% drawdown -- extremely volatile
- 7-day window is catastrophic (-994.8%)
- 30-day window is positive (+328.6%), suggesting some strategies recover over longer horizons
- The massive drawdowns indicate **poor risk management** at the portfolio level

**Recommendation:**
- **Implement portfolio-level drawdown circuit breakers** at 20% max DD
- **Reduce position sizing** -- current sizing allows 1,597% drawdown, which is absurd

---

## System Health Overview

### System Status Distribution

| Status | Count | Description |
|--------|-------|-------------|
| active | 37 | Actively trading |
| monitoring | 45 | Being watched |
| empty | 24 | No picks |
| stale | 14 | No recent signals |

**Finding:** 14 systems are stale (no recent signals) and 24 are empty. That's **38/120 (32%)** of systems not contributing.

### Systems by Asset Class

| Asset Class | System Count | % of Total |
|-------------|--------------|------------|
| CRYPTO | 104 | 87% |
| EQUITY | 18 | 15% |
| FOREX | 19 | 16% |
| COMMODITY | 13 | 11% |
| ETF | 9 | 8% |
| FUTURES | 4 | 3% |
| UNKNOWN | 3 | 3% |
| SPORTS | 1 | 1% |
| BOND | 2 | 2% |

**Finding:** 87% of systems trade crypto, but crypto is breakeven. This is a massive misallocation of development effort.

---

## Volatility Alerts

Current extreme pump alerts:
1. **ENJUSDT**: +71.92% (strategy: ensemble)
2. **FETUSDT**: +58.13% (strategy: ml_crypto_pred)

These are **unrealized gains** on active picks. If they reverse, they will add to losses.

---

## Top 15 Worst Symbols (All Asset Classes)

| Symbol | PnL % | Asset Class | Action |
|--------|-------|-------------|--------|
| USDCHF=X | -444.26% | FOREX | HALT |
| AUDJPY=X | -208.13% | FOREX | HALT |
| NZDJPY=X | -205.67% | FOREX | HALT |
| OPUSDT | -115.09% | CRYPTO | CAP |
| ARBUSDT | -93.64% | CRYPTO | CAP |
| APEUSDT | -82.97% | CRYPTO | CAP |
| HBARUSDT | -53.39% | CRYPTO | CAP |
| ALGOUSDT | -47.24% | CRYPTO | CAP |
| ADAUSDT | -42.54% | CRYPTO | CAP |
| SHIB-USD | -40.30% | CRYPTO | CAP |
| WIF-USD | -39.66% | CRYPTO | CAP |
| BONK-USD | -37.01% | CRYPTO | CAP |
| POLUSDT | -33.94% | CRYPTO | CAP |
| DOGE-USD | -28.18% | CRYPTO | CAP |
| DOGEUSDT | -23.38% | CRYPTO | CAP |

---

## Investigation: Why Strategies Fail

### 1. Forward Degradation Epidemic

78 out of 296 strategies (26%) show >10pp forward degradation. Many show **complete degradation** (backtest 35-66% -> forward 0%).

This indicates:
- **Overfitting to backtest data**
- **Regime change not captured in backtests**
- **Look-ahead bias** in backtest construction
- **Data snooping** across parameter space

### 2. The `kimi_signal_tracking` Disaster

This single system is destroying capital across ALL asset classes:
- Total PnL: -1,001.41%
- Win Rate: 31.1%
- Profit Factor: 0.28
- It trades FOREX, CRYPTO, and EQUITY

**This system must be investigated for:**
- Data feed errors
- Logic bugs (e.g., inverted signals)
- Overfitting
- Transaction cost assumptions

### 3. Concentration Risk

Top 5 symbols account for **118.2%** of total PnL:
1. USDCHF=X: 42.5%
2. AUDJPY=X: 20.0%
3. NZDJPY=X: 19.9%
4. DYDXUSDT: 19.6%
5. AUDUSD=X: 16.7%

This violates every principle of diversification.

### 4. Regime Blindness

The system has **zero strategies that work in ranging or downtrending markets**:
- Ranging: 0% WR
- Trending down: 6.2% WR

This is a massive structural flaw. The entire strategy suite is long-biased and trend-dependent.

### 5. Volume Without Edge

Crypto has 22,128 trades with PF 0.99. This is **noise trading** -- high volume with no edge. The system is paying transaction costs to generate random outcomes.

---

## Recommendations

### Immediate (This Week)

1. **HALT `kimi_signal_tracking`** -- investigate for bugs or kill it (-1,001% PnL)
2. **HALT `copy_trader_intel`** -- -753% PnL, no rehabilitation possible
3. **HALT `mercury2_fast`** -- PF 0.07 is beyond recovery
4. **HALT `claude_gainer_st`** -- -159% on 1,274 trades, consistent loser
5. **HALT `cta_replicator`** -- 8.3% WR is worse than random
6. **HALT `goldmine_stocks`** -- 0% WR
7. **HALT all FOREX trading** until PF > 1.0 on rolling 50-trade window
8. **Implement 20% max drawdown circuit breaker** at portfolio level

### Short-Term (Next 2 Weeks)

9. **Cap symbol concentration** -- no single symbol > 5% of book
10. **Deactivate all strategies with BT/FWD degradation >30pp**
11. **Implement regime-aware gating** -- reduce exposure in ranging/downtrending markets
12. **Extend TOD block** per PR #294 (16-21 UTC + conf dead-zone)
13. **Raise minimum profit factor to 1.15** for all asset classes
14. **Add short-biased strategies** for downtrending markets
15. **Kill all empty (24) and stale (14) systems** -- they're dead weight

### Medium-Term (Next Month)

16. **Rebalance system allocation** -- reduce crypto from 87% to 50%, increase equity from 15% to 30%
17. **Implement walk-forward validation** before deploying any new strategy
18. **Add Bonferroni + Deflated Sharpe filters** per PR #293
19. **Study equity strategies** and port their logic to other asset classes
20. **Implement skill-vs-luck filtering** per PR #300 -- ZERO of 174 strategies passed, suggesting most are noise
21. **Create a rolling performance-review process** instead of 35 separate PRs

---

## Conclusion

The audit dashboard reveals a **portfolio in crisis**:
- Only **1 of 9 asset classes** is genuinely profitable (Equity)
- **2 asset classes** are catastrophic (FOREX, CRYPTO)
- **26% of strategies** suffer severe forward degradation
- **A single system** (`kimi_signal_tracking`) is destroying -1,001% across all classes
- **Concentration risk** is extreme -- 42.5% of PnL from one symbol
- **Regime blindness** -- no strategy works in ranging or down markets

**The good news:** Equity proves the system CAN work. The methodology is sound for that asset class. The task is to replicate equity's success in other classes while aggressively pruning the bleeders.

**Bottom line:** Stop trading FOREX and most CRYPTO immediately. Focus capital on EQUITY and a small, vetted set of commodity/ETF strategies. Kill the bleeders. Fix the concentration. Add shorts. Then gradually rebuild.

---

*Generated by Claude Code on 2026-04-22*
*Data Source: audit_dashboard/data/dashboard_data.json*
