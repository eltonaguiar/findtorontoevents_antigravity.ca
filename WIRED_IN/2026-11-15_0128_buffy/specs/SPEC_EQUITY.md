# Algorithm Specification — EQUITY

**Agent:** buffy (Codebuff) · **Date:** 2026-11-15
**Status:** `MEASURED (index proxy) — REJECTED` · and an explicit statement of what was **not** measured

---

## 0. Read this before the spec

The repo's `EQUITY` class means **single-stock picks** (933 ledger rows) with entry/TP/SL. What I
measured is an **index swing rule on SPY**, which is a proxy, not the same thing. So:

| Question | Answer |
|---|---|
| Did I measure the repo's actual equity picks? | **No.** No verified per-pick excess-return series exists to measure — that is the gap documented in `03_benchmark_relative/BENCHMARK_GATES.md`. |
| Did I measure an equity *rule*? | **Yes** — RSI(2) on SPY, 25.76 years, 6,492 daily periods, costs included. It fails. |
| Does that prove the repo's equity picks fail? | **No.** It proves one widely-cited equity rule fails after costs on the index. The picks are a separate, still-unmeasured question. |

A single-stock test additionally needs: point-in-time universe (survivorship-free), 10–20 bps/side (not
6), borrow/short constraints, earnings-gap handling, and delisting returns. None of that exists here, so
I did not pretend to run it.

---

## 1. Rule measured — RSI(2) mean reversion on SPY

| Field | Value |
|---|---|
| Instrument | `SPY` daily adjusted close |
| Sample | 2001-01-03 → 2026-11-13 · 6,492 daily periods · 25.76 years |
| Cost | 6 bps per side, charged on every position change |
| Cash leg | T-bill (`^IRX`) ÷ 252 per day |
| Benchmark | Matched exposure: `exposure × SPY + (1 − exposure) × T-bill` |

```text
RSI2  = Wilder RSI, period 2        (smoothed, seeded at 0)
SMA200, SMA5 = simple moving averages of close

Position state machine, evaluated on each close t:

  if flat:
      if RSI2[t] < 5 and close[t] > SMA200[t]:     enter, weight = 1.0
  if long:
      held += 1
      if close[t] > SMA5[t] or RSI2[t] > 65 or held >= 10:
                                                   exit,  weight = 0.0

Position decided on close t earns close t → t+1.
```

Parameters are Connors' textbook defaults: oversold 5, exit 65, 5-day exit MA, 10-day time stop,
200-day regime filter. **None were tuned.**

---

## 2. Measured result

| Metric | Full | In-sample 2003-01→2015-12 | Out-of-sample 2016-01→2026-11 |
|---|---:|---:|---:|
| CAGR | **0.21%** | 0.56% | −0.17% |
| Excess vs matched benchmark | **−2.30%/yr** | −1.79% | −2.87% |
| Sharpe | **−0.64** | — | — |
| Max drawdown | −14.5% | — | — |
| Deflated Sharpe (N=3 daily trials) | **0.00** | — | — |
| Round trips | 117 | — | — |
| Average exposure | **0.02** | — | — |
| Information ratio | −11.399 | — | — |

At **2× costs**: CAGR **−0.34%**, Sharpe **−0.86**, max drawdown −20.4% — the drawdown gets *worse*
when costs double, because more of the equity curve is spent paying spread.

### The one number that settles it

**Average exposure 0.02.** The rule is in the market 2% of the time. It spends 25.76 years and 117
round trips to earn 0.21%/yr — less than the T-bill leg of its own benchmark (2.54% CAGR). The
strategy's cost of carry alone exceeds its gross return. This is not a marginal call; there is no
plausible cost assumption under which it clears.

---

## 3. Why it looked attractive and why that was wrong

RSI(2) has a well-known high hit rate — most trades are small winners, which is what makes it popular
in screeners and backtest screenshots. What the hit rate hides:

- Winning 1% and losing 3% at a 63% hit rate is a losing system, and the loss is concentrated in the
  trades that gap through the exit.
- Signal frequency (117 round trips in 25.76 years ≈ 4.5/yr) × 6 bps × 2 sides is trivial — but the
  *gross* edge is also trivial, so the ratio is what kills it.
- The 200-day filter removes most of the sample, leaving a small number of effective independent bets.

---

## 4. Elimination

**Eliminated in the backtest** (Stage 0 of the forward protocol). To be re-admitted it would need a
gross-edge estimate that survives 3× the assumed cost, an intrabar fill check, and a point-in-time
single-stock universe — i.e. it is a different, larger study, not a parameter tweak.

Recorded in `ELIMINATION_LOG.md` §2. Not sent to forward testing; it would burn a year to confirm a
negative the arithmetic already shows.

---

## 5. What an EQUITY spec should look like (not run)

If this class is to be measured properly, the minimum viable spec is:

| Requirement | Value |
|---|---|
| Universe | Point-in-time S&P 500 or Russell 1000 constituents, survivorship-free |
| Costs | 10–20 bps/side + borrow where short |
| Benchmark | SPY total return **and** sector-neutral version |
| Data | Split/dividend adjusted, delisting returns included |
| Gate | Excess > 0 after costs, IR ≥ 0.5, alpha t > 2, DSR ≥ 0.95 at disclosed trial count |

Until then, the honest statement about the repo's 933 equity picks is: **their excess return has never
been computed, so their edge is unknown, not positive.**
