# Holding-Period × Trading-Style Analysis — finpredict-v4

**Date:** 2026-11-15 (AM)
**Question:** For each asset class, which holding period and trading style has the highest grounded probability of profitability?

---

## 1. The Style Spectrum (and what the evidence says)

| Style | Holding | Costs | Failure mode | Verdict |
|-------|---------|-------|--------------|---------|
| **Long-term / buy-and-hold** | 1-10y | Minimal | Market beta (drawdowns) | **Grounded — captures risk premium** |
| **Swing / tactical** | 1-12 weeks | Low | Regime timing | **Grounded when trend-filtered (Faber 200d, dual momentum)** |
| **Day trading** | minutes-hours | High | Costs + overfitting + noise | **Fails across all classes** |
| **Scalping** | seconds-minutes | Very high | Spread/slippage dominate | **Fails; structural market-making only** |

**Core finding:** the only academically-supported, code-existing edge family is **long-term trend / momentum persistence** (Faber 200-day MA, Clenow/AQR momentum, institutional CTA). Intraday mean-reversion and scalping are the consistent losers across all classes.

---

## 2. Per-Asset-Class Style Fit

| Class | Best style | Worst style | Reasoning |
|-------|-----------|-------------|-----------|
| **Mu funds / ETF** | Long-term allocation / monthly tactical | Intraday | Equity risk premium + low costs; Faber trend filter |
| **EQUITY** | Long-term trend (200d MA), swing momentum | Day/scalp | Momentum = strongest anomaly; RSI-2 cost-fragile |
| **CRYPTO** | Swing momentum (POSITION horizon) | Scalping | Extreme vol; short-hold = noise + fill bugs |
| **FOREX** | Low-freq carry/trend | Intraday session | Only macro premia defendable |
| **BOND** | Monthly duration/tact | Intraday | Yield income; low vol |
| **COMMODITY/FUTURES** | CTA trend (weeks-months) | Scalp | Winton/AHL audited trend model |

---

## 3. Famous "Proven" Algorithms — Reality Check (from research)

| Strategy | Asset/timeframe | Evidence | Grounded? |
|----------|-----------------|----------|-----------|
| **Turtle Trading** | Futures trend | Anecdotal, dated (1980s), degraded post-2000 | Partial — trend premium, rules period-fit |
| **Connors RSI-2** | SPY, 1-5d | Book backtest, degraded, cost-regime fragile | Weak — mean-reversion plausible but fragile |
| **Faber 200-day MA** | Index ETFs, monthly | Replicated, ~10%+ alpha vs B&H, lower DD | **Strong** — trend + tail-risk |
| **Dual Momentum** (Antonacci) | US+global equity/bonds | Single-author backtest | Strong principle, single-source practice |
| **Clenow / AQR momentum** | Global equities | Academic + institutional; crashes | **Strong** — must vol-manage |
| **Hoffman IRB** | NQ/ES intraday | Contest-claim marketing, no audited record | Weak — pattern-mining |
| **TradingView "Top Strategy"** | Any | Overfit leaderboard, not proof | **None — theater** |
| **AQR factors** (value/mom/low-vol/quality) | Cross-sectional | Peer-reviewed, institutional | **Strong** — cyclical |
| **CTA trend** (Winton/AHL/Systematica) | Futures | Audited decades | **Strong** — crisis alpha; flat 2010s |
| **ETF rotation** (Faber/Cambria) | ETFs | Self-published + short live | Moderate-strong |

**Key correction:** TradingView's "Pine Script Wizards" is a *community contribution* award, not a performance contest. Backtest leaderboards reward overfitting. Treat all contest winners as entertainment unless they carry an audited, net-of-cost, OOS record (none do).

---

## 4. What makes a strategy robust (not just contest-winning)

1. Standing economic mechanism (risk premium, behavioral bias, structural flow)
2. Survives full costs (spread, slippage, commissions)
3. Validated out-of-sample (walk-forward, cross-asset)
4. Small parameterization (few tuned knobs)
5. Survives regime change (trend/momentum rotate but don't collapse)

---

## 5. Conclusion per class

- **Mutual funds / ETFs**: long-term allocation + monthly Faber trend = the only "solid" path.
- **EQUITY**: long-term trend/momentum; NOT intraday.
- **CRYPTO**: swing momentum POSITION; NOT scalp.
- **All others**: blocked until measurement is clean; then low-frequency trend/carry only.
