# 06 — Key Metrics That Must Be Satisfied, by Perspective

**Date:** 2026-11-15 · **Author:** Buffy

The same strategy can be "good" to a prop trader and "uninvestable" to a fund manager. Below, each
audience's actual bar, and the repo's current position against it.

---

## 1. The metric stack (compute in this order)

| Metric | Formula | Why it gates |
|---|---|---|
| **Verified-mark coverage** | verified / closed | Without this, everything below is fiction. Repo: **51.9%** |
| **Profit factor (net)** | Σwins / \|Σlosses\|, costs subtracted | Repo (verified): 0.59–1.16 |
| **Expectancy** | (WR × avgWin) − (LR × avgLoss) − cost | Must be > 0 |
| **Sharpe (annualised)** | (mean/SD) × √(periods per year) | Requires disclosed trades/yr — see §4 |
| **Sortino** | excess / downside deviation | Penalises only bad vol |
| **Calmar** | CAGR / \|maxDD\| | Return per unit of pain |
| **CVaR95** | mean of worst 5% of trades | Repo: −7.96% |
| **Max drawdown (compounded)** | peak-to-trough on equity path | Repo: **−100%** (additive sums gave the impossible −140%) |
| **Kelly** | WR − (1−WR)/payoff | Repo: **−0.0538 → size zero** |
| **Risk of ruin (MC)** | P(equity < ruin) over N trades | Repo: **44.4% / 200 trades** |
| **Deflated Sharpe** | Sharpe adjusted for N trials | Repo: absent; N=361 |
| **PBO** | P(backtest overfit) | absent |

---

## 2. Thresholds by perspective

### 2.1 Bank prop desk / senior trader

| Metric | Bar | Rationale |
|---|---|---|
| Sharpe (net) | **≥ 1.5** | Desk capital has a hard internal cost; below 1.5 you are not covering your seat |
| Sortino | ≥ 2.0 | They care about downside, not upside vol |
| Calmar | ≥ 1.0 | A 30% DD needs 30% return to justify it |
| Max DD | < 10% | Desk-level limit; breach = capital pulled |
| Daily VaR 99% | < 1% of NAV | Hard risk limit |
| Hit rate × payoff | WR 45–55%, payoff > 1.5 | They do not need high WR, they need asymmetry |
| Break-even slippage | > 2× realised slippage | Execution desk must have margin |

**Repo position:** Sharpe/trade 0.005–0.061, maxDD −100%, ruin 44.4%. **Not remotely close.**

### 2.2 Mutual fund manager (long-only, benchmarked)

| Metric | Bar | Rationale |
|---|---|---|
| Sharpe | ≥ 0.5 | Modest absolute bar; benchmark-relative matters more |
| Information ratio | ≥ 0.5 | Beating the benchmark consistently |
| Tracking error | 2–6% | Mandate constraint |
| Max DD | < 15–20% | Investor tolerance |
| Record length | 3–5 years | Marketing rule requires it |
| Turnover | consistent with 30-day trading limits | Structural |
| Fees | net-of-fee disclosure | Regulatory |

**Repo position:** no MUTUAL_FUND class exists; **this is an allocation mandate, not a pick mandate.**
The relevant bar is the ETF/fund product: SPY 10y window positive 90.2% of the time, Sharpe 0.64,
maxDD −52.2% — passes on Sharpe, fails on DD for a typical mandate.

### 2.3 Hedge fund allocator (institutional LP)

| Metric | Bar | Rationale |
|---|---|---|
| Sharpe (net of fees) | ≥ 1.0 | 2-and-20 has to be beaten |
| **DSR** | **≥ 0.95 at true trial count** | Their whole job is detecting data mining |
| PBO | < 0.5 | Probability backtest is overfit |
| Alpha t-stat | **> 3.0** (Harvey–Liu–Zhu) | Multiple-testing-aware significance |
| Capacity | stated | Can they get size in? |
| Drawdown communication | documented | AQR's actual survival mechanism |
| Independent admin | required | Self-reported NAV is disqualifying |

**Repo position:** self-graded resolver, no DSR, no PBO, no independent verification. **Disqualified at
the first item, before any performance discussion.**

### 2.4 Chief risk officer

| Metric | Bar |
|---|---|
| CVaR95 | within stated limit; currently −7.96% |
| Stress loss (worst historical window) | < 20% of NAV |
| HHI concentration | **< 0.25**; repo 0.385 |
| Effective beta | < 1.5 |
| Largest single emitter | < 20% of book; repo **48.2%** (`kimi_riseoftheclaw`) |
| Liquidity | exit < 5 days at 20% ADV |
| Circuit breakers | daily −2%, weekly −5%, monthly −10% |

**Repo position:** three hard breaches (HHI, single-emitter, maxDD).

### 2.5 Retail / prop-challenge (HyroTrader-style)

| Metric | Bar | Note |
|---|---|---|
| Max daily loss | 5% | Breach = account terminated |
| Max total loss | 10% | |
| Profit target | 8–10% | |
| Per-trade risk | 0.5–1% | Sizing discipline, not signal quality |
| Min trading days | 5–10 | Prevents one-shot gambling |

**Implication:** the binding constraint is **survival**, not Sharpe. A 44.4% ruin probability fails this
gate instantly regardless of PF.

### 2.6 Academic / replication standard

| Metric | Bar |
|---|---|
| t-stat | **> 3.0** on the strategy, not the factor |
| OOS | ≥ 2 disjoint periods, both positive |
| Replication | independent implementation reproduces within tolerance |
| Data provenance | point-in-time, survivorship-free |
| Trial disclosure | full count published |

---

## 3. The single table that matters

| Gate | Bar | Repo measured | Pass? |
|---|---|---|---|
| Verified-mark coverage | ≥95% | 51.9% | ❌ |
| Profit factor (net) | ≥1.5 | 0.59–1.16 | ❌ |
| Sharpe (annualised) | ≥1.0 | 0.005–0.061 per trade (≈0.1–0.9 ann.) | ❌ |
| Max drawdown | <15% sleeve | −100% ledger | ❌ |
| Kelly | >0 | −0.0538 | ❌ |
| Risk of ruin | <5% | 44.4% | ❌ |
| HHI | <0.25 | 0.385 | ❌ |
| DSR | ≥0.95 @ N=361 | absent | ❌ |
| Independent verification | required | none | ❌ |

**9 gates, 0 passes.** This is why the Nov-14 plan's "do not deploy" is correct, and it is also why the
answer is not "try harder on strategies."

---

## 4. The Sharpe trap in this repo

Per-trade Sharpe must be annualised before comparison: `Sharpe_ann ≈ Sharpe_trade × √(trades per year)`.
For 250 trades/yr, per-trade 0.054 → ~0.85. **But that arithmetic assumes independent trades and a
stable edge**, and this ledger has 48% forged marks and 59%-contaminated CRYPTO. So:

- Publishing an annualised Sharpe from unvalidated per-trade numbers is **how "Sharpe 3.76" appeared and was falsified**.
- Until L0 passes, report **per-trade Sharpe with the trade count**, never a headline annualised figure.

## 5. What to publish, in what order

1. Verified-mark coverage per class (blocks everything)
2. Net PF + expectancy with cost assumption stated
3. Per-trade Sharpe + n + effective N
4. CVaR95 and compounded max DD
5. Kelly and ruin probability — **including when negative**
6. DSR/PBO once trial count is fixed

Items 1–5 exist today for 3 of 7 classes. Item 6 does not exist at all.
