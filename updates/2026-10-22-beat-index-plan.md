# Plan: Beat the Index Fund — OPENCODE_BEAM (2026-10-22)

> **⚠️ NOT FINANCIAL ADVICE (NFA).** This document is research and education only. It is not a recommendation to buy or sell any security, fund, or account. Past performance does not guarantee future results. Do your own research (DYOR).

**Agent:** OPENCODE_BEAM (opencode/beam-free)
**Status:** IN PROGRESS — hypothesis tested and REFUTED; scoreboard fixes ongoing
**Branch:** `oc-winning-candidate`

---

## The Goal (ELI5)

We want to build a trading system that makes more money than simply buying an index fund (like the S&P 500) and doing nothing. An index fund is a basket of the biggest companies — when they go up, the basket goes up. Most professional fund managers fail to beat this basket over time. We want to be one of the rare systems that does.

**Technical definition:** Produce a strategy (or portfolio of strategies) whose net-of-cost compound annual growth rate (CAGR — the average yearly profit, accounting for compounding) exceeds the CAGR of the S&P 500 (Standard & Poor's 500 — a stock index of the 500 largest U.S. companies) on a risk-adjusted basis, with maximum drawdown (MDD — the largest peak-to-trough drop in portfolio value) ≤ 20%.

---

## What We Tested (And What Actually Happened)

### BTC 12-Month Momentum — LABEL: FAIL

**Hypothesis:** Hold Bitcoin only if its 12-month return is positive; else cash. Would beat an index fund.

**Result after rigorous audit (2 independent rebuilds):**

| Metric | Strategy | Just holding BTC | SPY index ETF |
|---|---|---|---|
| CAGR | 52.7–58.6% | 53.9–70.2% | 13.7% |
| Daily max drawdown (MDD) | −80.1 to −81.9% | −83.4% | −33.7% |
| Sharpe ratio | 1.04–1.08 | 0.99–1.14 | 0.83 |
| Worst calendar year | −56 to −60% | −73.6% | −18.2% |

**Why it FAILS:**
1. Daily mark-to-market MDD ≈ −80% (gate: ≤20%) — the earlier closed-trade-only figure ignored every drop while holding (it checked the account only when a trade closed)
2. It does NOT beat just holding Bitcoin (lower CAGR, marginally lower MDD)
3. MC (random entry dates, same hold lengths, 2,000 runs): 77th percentile (gate: ≥95th) — FAIL
4. DSR (Bailey–López de Prado, N=65 trials across all agents): ≈0 (gate: >0.95) — FAIL
5. n = 11–13 trades (gate: ≥100); one trade = 75% of profit
6. Only 2 of 9 lookback variants pass — parameter instability = curve-fitting

**Verdict:** FAIL. Research lead only: trend filters make Bitcoin *slightly* calmer (−80% vs −83%) but give up return. **A plain index fund remains the better choice** (−34% worst drop, Sharpe 0.83, no skill required).

## The 9 Validation Gates (GROK Protocol — expanded)

All acronyms expanded. Source: COMMUNITY/GROK_20261022_1855.MD (scorecard).

| # | Gate | Target | Value (corrected) | Result |
|---|---|---|---|---|
| 1 | n ≥ 100 closed trades | 100 | 11–13 | FAIL |
| 2 | Profit Factor net ≥ 1.5 | 1.5 | 43.5–94.9 (1 trade = 75%) | PASS (unstable) |
| 3 | PF bootstrap CI low ≥ 1.2 | 1.2 | 3.79 (CI width 400× at n=13) | PASS (unstable) |
| 4 | Daily mark-to-market MDD ≤ 20% | ≤20% | −80.1% (Grok: −81.9%) | FAIL |
| 5 | Random-entry MC ≥ 95th percentile | ≥95 | 77 (Grok: 2,000 runs, random buy dates) | FAIL |
| 6 | DSR (Bailey–López de Prado) > 0.95 | >0.95 | ≈0 at N=65 trials (all agents) | FAIL |
| 7 | PF ≥ 1.3 at 2× costs | 1.3 | passes (not decisive) | PASS |
| 8 | Top symbol ≤ 30% | 30% | N/A (single asset) | PASS |
| 9 | Both halves profitable | >1.0 | H1/H2 positive but n too thin | PASS (weak) |

**Score: 5/9 PASS but 3 hard gates FAIL (daily MDD, MC, DSR) → LABEL: FAIL.**
Labels allowed: MONEY-READY / CANDIDATE / FAIL only. Daily MDD >20% = FAIL outright.

**Additional failure:** the strategy does not beat simply holding Bitcoin (CAGR 52.7% vs 53.9% in our rebuild; Grok's rebuild 58.6% vs 70.2%).

## Strategies Tested That FAIL (Proposed Kills)

These are proposed for operator approval. Do not kill without approval.

| Strategy | ELI5 reason | Technical gates failed |
|---|---|---|
| BTC 200-day SMA trend | Too much pain (38.8% drop) | MDD 38.8%, CI 1.15, n=38 |
| BTC 300-day (10-month) SMA | Same problem, slightly less pain | MDD 35.9%, n=37 |
| BTC 50/200 golden cross | Too few trades + big drops | MDD 30.8%, n=11 |
| BTC RSI<30 mean reversion | RSI = Relative Strength Index (momentum oscillator); bought dips but crashed anyway | MDD 55.2%, CI 0.63 |
| BTC 12m+6m dual momentum | Dual momentum = both long-term AND medium-term must agree; still crashed | MDD 51.1%, CI 1.03 |
| ETH 12m momentum | Ethereum crashes harder than Bitcoin | MDD 51%, CI 0.13 |
| SOL 12m momentum | Same | MDD 37.7%, CI 0.29 |
| BNB 12m momentum | Same | MDD 72%, CI 0.16 |
| All AlphaEngine regime_* EQUITY | Same trade duplicated 4.3×; win rate drops from 54% to 38% after dedup | Duplicate inflation |

---

## The 3 Ultimate P/L Bugs (Must Fix Before Any Number Is Trusted)

**P/L = Profit and Loss (the money made or lost).**

### Bug 1: Duplicate Trades (inflates n and P/L up to 5.2×)
**ELI5:** The database records the same trade many times under different IDs. Imagine a basketball player who makes 5 shots but the scoreboard counts it as 64 shots — their stats look amazing but it's fake.
**Technical:** Trades are deduplicated by (symbol, entry_price, exit_price) tuple. IONQ: 64 rows, only 7 distinct entry/exit prices. NIO: 21 rows, 1 distinct. AMD: 21 rows, 2 distinct. After dedup, regime_mild_bear SHORT EQUITY drops from WR 54.1% to 38.5%.
**Fix location:** All /audit aggregation code — deduplicate before computing any statistic.

### Bug 2: Batch-Close Contamination (21.2% of all closed picks)
**ELI5:** Thousands of trades all "closed" at the exact same second — which is impossible. It's like a store checkout where 11,381 customers all paid at 03:16:00 on May 10th. They didn't; the receipt printer broke.
**Technical:** 11,381 picks have closed_at = 2026-05-10 03:16:00/01 with pnl_pct = 0.0000 and exit_reason = RESOLUTION_TIMEOUT_NULL_TS or NULL_TIMESTAMP_STALE (the exit-price resolver timed out and stamped them at entry price). 2,301 more on 2026-04-11 08:02:50–08:03:04. Total: 13,682 = 21.2% of 64,616 closed picks.
**Fix location:** `audit_trail/universal_pick_resolver.py` — the scoreboard engine. These should be marked EXPIRED/ABANDONED, not CLOSED.

### Bug 3: Lookahead Contamination (1,239 picks)
**ELI5:** Some trades show they were closed less than 2 minutes after they opened. You can't profit from a trade that finished before you could have possibly seen the result — that's like knowing the answer before the test starts.
**Technical:** 1,239 picks have TIMESTAMPDIFF(SECOND, recorded_at, closed_at) BETWEEN 0 AND 119 with status IN (WON, LOST, CLOSED). These are data artifacts where the resolver stamped a close immediately rather than waiting for TP/SL/time exit.
**Fix location:** Same resolver — add a minimum holding period filter.

---

## The Plan (Sequential Steps)

### Phase 1: Fix the Scoreboard (P0 — blocks everything) [IN PROGRESS]
- [x] Quantify all 3 bugs (done: 3 bugs found and documented)
- [x] Write artifact exclusion tests (done: `tests/test_artifact_exclusion.py`, 10/10 pass)
- [ ] Apply dedup + batch-close + lookahead filters to universal_pick_resolver.py
- [ ] Apply compound return instead of Σ Trade % (sum of trade percentages ≠ compound return)
- [ ] Verify /audit numbers change after fix (before/after table)

### Phase 2: Apply GROK's Protocol to Each Asset Class ("Save the Asset Class") [IN PROGRESS]
- [x] Implement proper Bailey–López de Prado DSR (done: applied with N=65 trials → BTC momentum ≈0)
- [x] Correct daily mark-to-market equity + random-entry-dates MC (done: MDD −80%, MC 77th pct)
- [ ] For each class (crypto, stocks, ETF, forex, commodities): list every strategy's full spec (entry, hold, TP, SL, time stop, size, costs) — mark "undefined" where missing
- [ ] Test published strategies: RSI(2)+200-day filter, IBS (Internal Bar Strength) with 200-day filter, 10-month SMA, dual momentum, carry for FX
- [ ] Next-bar entry, real costs, holds of days-to-months, 10+ years of data
- [ ] Log EVERY trial in trials.csv (required for DSR honesty)
- [ ] Run all 9 gates; labels MONEY-READY / CANDIDATE / FAIL only

### Phase 3: Scoreboard Fixes [PENDING — blocks all trust in /audit numbers]
- [ ] Apply dedup + batch-close + lookahead filters to universal_pick_resolver.py
- [ ] Compound return instead of Σ Trade %
- [ ] Show excluded counts per card + data-coverage line
- [ ] No strategy is paper-traded forward until it passes all 9 gates (BTC momentum is FAIL — not registered)

### Phase 4: Per-Asset-Class Winners [PENDING]
- [ ] FOREX: Test carry trade (earn interest rate differential between currencies) — published strategy
- [ ] EQUITY: Test IBS (Internal Bar Strength — buy on weak open days) with 200-day filter
- [ ] ETF: Test 200-day SMA rotation among sector ETFs
- [ ] COMMODITY: Test 10-month momentum on gold (GLD) and oil (USO)
- [ ] BOND: bond_yield_curve_slope already passes (n=18, PF 9.44) — needs more data
- [ ] Run all 9 gates on each

### Phase 5: Variety-Pack Fund Proposal [PENDING]
- [ ] Combine per-asset-class winners into a diversified portfolio
- [ ] Compute portfolio-level MDD, Sharpe, CAGR
- [ ] Compare vs S&P 500 on same metrics
- [ ] Document in COMMUNITY

---

## Key Concepts (Glossary — all acronyms expanded)

| Acronym | Full Term | ELI5 Meaning |
|---|---|---|
| CAGR | Compound Annual Growth Rate | Average yearly profit if you reinvested everything |
| P/L | Profit and Loss | Money made or lost |
| PF | Profit Factor | Total money won ÷ total money lost |
| WR | Win Rate | % of trades that made money |
| MDD | Maximum Drawdown | Biggest drop from highest point to lowest point |
| CI | Confidence Interval | Range of likely outcomes (e.g., 95% chance true PF is in this range) |
| DSR | Deflated Sharpe Ratio | Adjusts for the fact that you tried many strategies — discounts lucky guesses |
| MC | Monte Carlo | Simulating random outcomes thousands of times to see how lucky you were |
| SMA | Simple Moving Average | Average price over the last N days (smooths out noise) |
| RSI | Relative Strength Index | A 0–100 gauge of how fast price moved (30 = oversold, 70 = overbought) |
| TP | Take Profit | Auto-sell price when you've made enough |
| SL | Stop Loss | Auto-sell price when you've lost too much |
| S&P 500 | Standard & Poor's 500 | Index of the 500 biggest U.S. companies |
| ETF | Exchange-Traded Fund | A basket of stocks you can buy like a single stock |
| OCR | Optical Character Recognition | Reading text from images |
| OHLCV | Open-High-Low-Close-Volume | The 5 numbers for each day's price bar |

---

## Files

- **Tool:** `tools/crypto_published_strategies.py` — 6-strategy backtest with 9 gates
- **Data:** `audit_dashboard/data/btcusd_daily.csv` — 12 years of BTC-USD daily prices
- **Results:** `audit_dashboard/data/published_strategy_gates.json`, `momentum_multi_symbol.json`
- **Tests:** `tests/test_artifact_exclusion.py` — 10/10 pass
- **Page:** https://findtorontoevents.ca/audit/opencode_paper_trading.html
- **COMMUNITY verdict:** `OPENCODE_20261022_2330.MD`
