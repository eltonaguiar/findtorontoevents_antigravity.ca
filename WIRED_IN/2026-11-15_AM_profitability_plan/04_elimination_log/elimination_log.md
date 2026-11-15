# Elimination Log — Strategies and Asset Classes Eliminated

**Date:** 2026-11-15 AM
**Purpose:** Document how and why each strategy and asset class was eliminated from consideration.

---

## Elimination Framework

A strategy/asset class is eliminated when it fails any of the following:

| Elimination Criterion | Threshold |
|----------------------|-----------|
| Negative expectancy after costs | Net PnL < 0 |
| Win rate too low | WR < 35% (forward test) / < 50% (money-ready gate) |
| Profit factor too low | PF < 1.15 (money-ready gate) |
| Sharpe insufficient | Sharpe < 1.0 (money-ready gate) |
| DSR insufficient | DSR < 0.95 (money-ready gate) |
| PBO too high | PBO > 0.10 (money-ready gate) |
| Max drawdown excessive | DD > 15% (money-ready gate) |
| Insufficient sample | Trades < 50 (money-ready gate) |
| Structural incompatibility | No viable execution path (e.g., mutual funds daily NAV) |
| Insufficient data | n < 100 (statistical inference floor) |
| Data quality failure | Cohort mismatch, missing resolution_method, stale prices |
| Cost dominance | Costs > 200% of gross profit |
| Protocol block | Mutation-before-kill, keep blocked, not built |

---

## Asset-Class Elimination Log

### EQUITY — RESEARCH SLOT 1 (NOT ELIMINATED, NOT DEPLOYED)

| Strategy | Elimination Reason | Gates Passed | Status |
|----------|-------------------|--------------|--------|
| RSI(2) Mean Reversion | Negative expectancy (-118% to -186%), WR 0-17%, Sharpe -8 to -18, DSR=0 | 2/7 | ELIMINATED |
| Dual MA Crossover | 2-5 trades over 5 years, PF=999 is statistical artifact, DSR=0, PBO=0.999 | 4/7* | ELIMINATED (artifact) |
| Bollinger Mean Reversion | Negative expectancy (-17% to -33%), Sharpe -1.2 to -2.0 | 2-3/7 | ELIMINATED |

\* QQQ/EFA DualMA show 4/7 but are statistical artifacts (2-3 trades, PF=999, DSR=0, PBO=0.999).

**Asset class status:** Not eliminated — kept as research slot 1. But zero strategies are deployable.

---

### CRYPTO — RESEARCH SLOT 2 CONDITIONAL (NOT ELIMINATED, NOT DEPLOYED)

| Strategy | Elimination Reason | Gates Passed | Status |
|----------|-------------------|--------------|--------|
| EMA Trend Crossover | Negative expectancy (-18% to -130%), Max DD up to 153%, Sharpe negative on 4/5 symbols, DSR < 0.4, PBO > 0.97 | 1-4/7 | ELIMINATED |
| Donchian Breakout | Zero trades on all 5 symbols — strategy never fired | 0/7 | ELIMINATED |

**Asset class status:** Not eliminated — kept as conditional research slot 2. Re-open only after fill fixes + SubQ coverage ≥7/10 + clean forward test.

---

### ETF — BLOCKED

| Strategy | Elimination Reason | Status |
|----------|-------------------|--------|
| All ETF active strategies | Cohort mismatch (official PF 0.022 vs registry 1.788), zero live picks, 267% cost ratio | BLOCKED |

**Asset class status:** Blocked until cohort resolved and data pipeline fixed.

---

### MUTUAL FUNDS — NOT BUILT (PASSIVE ONLY)

| Strategy | Elimination Reason | Status |
|----------|-------------------|--------|
| Mutual funds as active picks | Structurally incompatible: daily NAV only, no intraday TP/SL, next-NAV execution, load/12b-1 costs, frequent-trading limits | ELIMINATED (as active picks) |
| Mutual funds as passive allocation | NOT eliminated — recommended as capital deployment vehicle | RECOMMENDED (passive core) |

**Asset class status:** Zero production infrastructure. Not registered as asset class (class id = -1).

---

### FOREX — MUTATION-BEFORE-KILL

| Strategy | Elimination Reason | Status |
|----------|-------------------|--------|
| All Forex strategies | Historical PF 0.27 (sub-floor), recent PF 0.85 (below break-even), WR 32-40%, high n but negative expectancy | ON MUTATION PROTOCOL |

**Asset class status:** Blocked on mutation-before-kill. Not deployable.

---

### COMMODITY / FUTURES — WATCH (LOW FREQUENCY)

| Strategy | Elimination Reason | Status |
|----------|-------------------|--------|
| COT Contrarian | Gate failed 4/4 (OOS n=30, PF 0.861, mean net -0.45%/trade) | ELIMINATED |
| CTA Trend | Low n (7-229), 422% cost ratio, no contract identity pipeline | BLOCKED |
| Multi-asset | Same data quality issues | BLOCKED |

**Asset class status:** Blocked until data quality clears (real feed, contract identity, n ≥ 100).

---

### BOND — INSUFFICIENT DATA

| Strategy | Elimination Reason | Status |
|----------|-------------------|--------|
| Bond duration rotation | n=1 official, n=35 registry (below n≥100 floor) | BLOCKED |
| Bond credit spread | Same data insufficiency | BLOCKED |
| Yield curve rotation | No yield/duration data pipeline | BLOCKED |

**Asset class status:** Blocked until yield/duration data acquired and n ≥ 100.

---

### MEME / PENNY STOCK — KEEP BLOCKED

| Strategy | Elimination Reason | Status |
|----------|-------------------|--------|
| All meme/penny stock | n=10/n=1, toxic, no legitimate edge | KEEP BLOCKED |

**Asset class status:** Permanently blocked.

---

## Strategy-Level Elimination Detail

### RSI(2) Mean Reversion (Equity)

**Eliminated because:**
- Tested on 7 equity ETFs over 2020-2025 (1,508 daily bars each).
- Net PnL: -118% to -186% across all symbols.
- Win rate: 0% to 17% (far below 50% break-even).
- Profit factor: 0.002 to 0.148 (gross losses dwarf gross profits).
- Sharpe: -8.5 to -18.5 (deeply negative risk-adjusted return).
- DSR: 0.000 (no confidence Sharpe > 0).
- PBO: 0.999 (near-certain overfitting).
- Max drawdown: 117% to 180% (catastrophic).

**Previously famous** (Connors, 2008-2020 era) but the edge has completely decayed in the 2020-2025 regime.

---

### Dual MA Crossover (Equity)

**Eliminated because:**
- Tested on 7 equity ETFs over 2020-2025.
- Only 2-5 trades per symbol over 5+ years — insufficient sample.
- QQQ and EFA show PF=999 on 2-3 trades — statistical artifact, not tradable edge.
- DSR: 0.000 for all symbols.
- PBO: 0.999 for all symbols.
- Net PnL: -2.9% to +22.3% (the positives are on 2 trades = noise).

---

### Bollinger Mean Reversion (Equity)

**Eliminated because:**
- Tested on 7 equity ETFs over 2020-2025.
- Net PnL: -17.6% to -33.0%.
- Win rate: 20% to 43% (below 50%).
- Profit factor: 0.05 to 0.15 (gross losses 7-20× gross profits).
- Sharpe: -1.2 to -2.0.
- DSR: 0.000-0.061.
- PBO: 0.999.

---

### EMA Trend Crossover (Crypto)

**Eliminated because:**
- Tested on 5 crypto symbols over 2020-2025 (2,092-2,192 daily bars each).
- Net PnL: -18.2% to -130.7%.
- Win rate: 33.3% to 46.9% (below 50%).
- Profit factor: 0.315 to 0.889 (below 1.15).
- Sharpe: -3.10 to -0.30 (negative on 4/5 symbols).
- DSR: 0.002 to 0.383 (all below 0.95).
- PBO: 0.979 to 0.999 (all above 0.10).
- Max drawdown: 79% to 153% (catastrophic).

**Best case (ADA-USD):** Passes 4/7 gates but fails Sharpe (-0.30), DSR (0.383), PBO (0.979). Max DD 79% — unacceptable for deployment.

---

### Donchian Channel Breakout (Crypto)

**Eliminated because:**
- Zero trades on all 5 crypto symbols (BTC, ETH, SOL, XRP, ADA) over 5+ years.
- Strategy never generated an entry signal.
- Not viable.

---

## Cross-Validated Eliminations (Buffy's Parallel Backtest)

| Strategy | Elimination Reason | Source |
|----------|-------------------|--------|
| RSI2_SPY | 0.21% CAGR, SR -0.64, DSR 0.00, cost-dominated (2× costs → negative) | Buffy BACKTEST_PROOF.md |
| DUALMOM_2 | -2.57%/yr excess vs benchmark | Buffy BACKTEST_PROOF.md |
| DUALMOM_3 | IS +2.55% but OOS -6.34% (classic regime overfit) | Buffy BACKTEST_PROOF.md |
| SIXTY_FORTY | -3.03%/yr excess vs benchmark, OOS -5.90% | Buffy BACKTEST_PROOF.md |
| BH_SPY-as-alpha | −0.00% excess (it IS the benchmark, not alpha) | Buffy BACKTEST_PROOF.md |

Both simulations independently eliminate the same strategies. RSI(2), dual momentum, and 60/40-as-alpha are dead on 25+ years of data.

---

## What Was NOT Eliminated (But Also Not Deployed)

| Asset Class | Why Not Eliminated | Why Not Deployed |
|-------------|-------------------|------------------|
| EQUITY | Research slot 1 — only class with pre-registered SPY benchmark path | 0 strategies pass all gates |
| CRYPTO | Conditional slot 2 — largest n, fill fix may help | 0 strategies pass all gates, DSR < 0.4 |
| Mutual Funds | Not an active pick class | Structurally incompatible as picks; valid as passive allocation |

---

## Final Elimination Count

| Category | Count |
|----------|-------|
| Strategies backtested and eliminated | 5 (RSI2 Equity, DualMA Equity, Bollinger Equity, EMA Trend Crypto, Donchian Crypto) |
| Asset classes blocked | 5 (ETF, Forex, Commodity, Bond, Meme/Penny) |
| Asset classes not built | 1 (Mutual Funds as active picks) |
| Asset classes as research slots | 2 (Equity, Crypto) |
| Strategies passing all money-ready gates | 0 |
| Asset classes money-ready | 0 |
