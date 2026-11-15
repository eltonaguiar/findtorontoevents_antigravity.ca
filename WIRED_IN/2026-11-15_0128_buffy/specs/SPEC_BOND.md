# Algorithm Specification — BOND (duration sleeve)

**Agent:** buffy (Codebuff) · **Date:** 2026-11-15
**Status:** `MEASURED AS A SLEEVE — NO STANDALONE BOND ALPHA RULE SURVIVED`

---

## 1. Role of this class in the design

Bonds are not traded here on their own signal. They serve two mechanical purposes, and both are
measured:

| Role | Where it appears | Rule |
|---|---|---|
| Static duration sleeve | `SIXTY_FORTY` | 60% SPY / 40% TLT, rebalanced monthly |
| Momentum destination | `DUALMOM_2`, `DUALMOM_3` | Hold TLT instead of SPY when 12-month momentum wins |
| Cash proxy | all rules | Actually T-bills (`^IRX`), **not** TLT — cash is not assumed to yield 0 |

| Field | Value |
|---|---|
| Instrument | `TLT` (20+ year Treasury ETF), monthly adjusted close |
| Sample | 2004-12-01 → 2026-11-13 · 265 monthly periods |
| Cost | 6 bps/side |
| Benchmark (per gate doc) | `AGG` total return for a duration strategy; here `SPY` at matched exposure, as for every row |

**Why TLT and not AGG:** TLT has a measurable duration bet and long history; AGG's return is dominated
by a blend that is hard to attribute. This is a measurement choice, disclosed — for a real bond
allocation, AGG or a duration-matched Treasury ladder is the correct vehicle.

---

## 2. Measured results

### 60/40 as a strategy

| Metric | Value |
|---|---:|
| CAGR | 8.11% |
| Excess vs matched exposure | **−3.03%/yr** |
| Sharpe | 0.65 |
| Max drawdown | −28.5% |
| DSR | 0.99 |
| IS 2003–2015 | 7.77% (excess −0.18%) |
| OOS 2016–2026 | 8.45% (excess **−5.90%**) |

60/40 is **profitable and Sharpe-equal to buy-and-hold SPY** (0.65 both) with a much smaller drawdown,
but it is not alpha: it is a lower-beta portfolio being measured against its own exposure. The OOS
excess of −5.90%/yr says the 2016–2026 window was one where the duration sleeve cost real return
relative to equities.

### TLT as a momentum destination

| Rule | CAGR | Excess | Sharpe | MDD | DSR |
|---|---:|---:|---:|---:|---:|
| DUALMOM_2 (SPY vs TLT) | 7.59% | −2.57% | 0.50 | −27.6% | 0.96 |
| DUALMOM_3 (SPY vs TLT vs GLD) | 8.13% | −1.88% | 0.45 | −30.0% | 0.94 |

Both fail. The mechanism is visible in `DUALMOM_3`'s split: **+2.55% excess in-sample, −6.34%
out-of-sample.** The TLT leg helped in 2008-style deflationary crashes and hurt in 2022, when bonds and
equities fell together. A 12-month momentum filter cannot distinguish those two regimes because in both
the prior 12 months looked favourable.

---

## 3. What was NOT measured

- No **credit** strategy (HYG/LQD spread, default premium).
- No **curve** strategy (2s10s, roll-down, carry).
- No **AGG** buy-and-hold baseline as its own row.
- No duration targeting or risk parity.

So the correct statement is: **the duration sleeve is measured; a bond alpha strategy is not.** Anyone
claiming a bond edge from this repo has no measurement behind it — the ledger's BOND PF is 0.59 on 47
rows, which is a small-sample negative, not a strategy result.

---

## 4. Promotion condition

For a bond strategy to be considered, the benchmark must be `AGG` total return **and** a duration-matched
Treasury index, because "beat AGG" is trivially achievable by taking more duration risk. Pre-register the
duration before the test, or the result is a beta statement in disguise.
