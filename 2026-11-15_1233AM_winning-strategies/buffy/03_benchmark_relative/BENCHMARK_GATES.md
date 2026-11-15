# Benchmark-Relative Gates — "Beat the S&P 500" and "Beat Buy-and-Hold"

**Date:** 2026-11-15 · **Author:** Buffy

You were right that the previous metrics work missed this. Profit factor and Sharpe answer *"is this
positive?"* They do not answer *"is this better than just buying the index?"* — and for a long-only
system, buying the index is always available, free, and takes one click. So **benchmark-relative
performance is not a nice-to-have; it is the actual test.**

---

## 1. Why absolute metrics are insufficient

A strategy with PF 1.15 and Sharpe 0.8 that is long-only equity during a bull market may simply be
**beta with extra steps**. The dashboard shows a profit; the investor would have done better in SPY with
less risk and no work.

Every claim in this repo must therefore answer: **versus what?**

---

## 2. The benchmark per class (mandatory)

| Class | Benchmark | Why this one |
|---|---|---|
| EQUITY | **SPY total return** | The default alternative for any US equity exposure |
| ETF | **SPY TR** (or the specific ETF's buy-and-hold) | Otherwise you are timing, not picking |
| CRYPTO | **BTC buy-and-hold** | The dominant, liquid alternative |
| FOREX | **T-bill cash** (risk-free) | FX has no natural long-only premium |
| BOND | **AGG total return** | Duration benchmark |
| COMMODITY | **Equal-weight basket buy-and-hold** (e.g. GSG) | Avoids single-contract artefacts |
| FUTURES | **Underlying cash index** | Otherwise you are paying roll for beta |
| PREDICTION | **No-trade** (settle at price) | Fee arithmetic makes "do nothing" the benchmark |
| MUTUAL FUND | **Its own index** (e.g. S&P 500 for large-cap) | SPIVA's methodology |

**Critical rule: match exposure.** If the strategy holds 50% cash, compare against a 50/50 SPY/cash
blend, not 100% SPY. Otherwise you are measuring cash drag, not skill. Compute the strategy's average
net exposure and build the benchmark at that same exposure.

---

## 3. The metrics, with formulas

Let `Rp` = strategy return series, `Rb` = benchmark return series, `Rf` = risk-free.

| Metric | Formula | Gate |
|---|---|---|
| **Excess return (annualised)** | `Rp − Rb` | **> 0** net of costs |
| **Beta** | `cov(Rp,Rb) / var(Rb)` | report always |
| **Jensen's alpha** | `Rp − [Rf + β(Rb − Rf)]` | **> 0**, t-stat **> 2** |
| **Information ratio (IR)** | `mean(Rp − Rb) / sd(Rp − Rb)` | **≥ 0.5** |
| **Tracking error** | `sd(Rp − Rb)` | report |
| **Up-capture** | `mean(Rp \| Rb>0) / mean(Rb \| Rb>0)` | ≥ 100 if seeking alpha |
| **Down-capture** | `mean(Rp \| Rb<0) / mean(Rb \| Rb<0)` | **< 100** (must lose less) |
| **Capture ratio** | up-capture / down-capture | **> 1.0** |
| **Batting average** | share of periods `Rp > Rb` | ≥ 55% |
| **M² (Modigliani)** | `Rf + Sharpe_p × σ_b` | > `Rb` annualised |
| **Treynor** | `(Rp − Rf) / β` | report |
| **Alpha t-stat** | from regression | **> 3.0** with multiple-testing correction |

### The single number to publish

```
EDGE = annualised(Rp) − annualised(Rb at matched exposure) − costs
```

If `EDGE ≤ 0`, **the strategy is not a strategy — it is an expensive way to own the benchmark.** No
amount of PF or Sharpe rescues it.

---

## 4. Worked example (illustrative arithmetic, not a measured result)

Strategy: long-only US equity, avg exposure 60%, `Rp` = 11.0%/yr, `Rb(SPY)` = 10.0%/yr, costs 1.5%/yr.

- Matched benchmark = 0.60 × 10.0% + 0.40 × 4.0% (cash) = **7.6%**
- Excess = 11.0 − 7.6 − 1.5 = **+1.9%** → passes the excess gate
- But beta ≈ 0.6, so much of the 11% is just participation; Jensen's alpha must be positive **and** t > 2
  before this counts as skill.

Note what happened: against 100% SPY the strategy "beat" by only +1.0% before costs and **lost by 0.5%
after costs**. Against matched exposure it won by +1.9%. **Both framings are used in marketing; only the
matched one is honest.**

---

## 5. Where this repo stands today

| Class | Measured | vs benchmark | Verdict |
|---|---|---|---|
| EQUITY | PF 1.15, 738 verified marks | **never computed** | unknown |
| ETF | PF 1.04, 566 verified marks | SPY buy-and-hold = 8.71% CAGR / Sharpe 0.64 | almost certainly losing to buy-and-hold |
| CRYPTO | PF 1.02 | BTC hold | never computed |
| FOREX | PF 1.16 | T-bill cash | never computed |
| BOND | PF 0.59 | AGG | losing |

**Zero of five classes has ever been measured against its benchmark.** That is the gap you identified,
and it is larger than the ledger-contamination gap in one respect: contamination makes a number wrong,
but a missing benchmark makes the *question* unasked.

---

## 6. The gate to add (copy into the promotion check)

```
PROMOTE only if ALL of:
  verified_n            >= 100
  months_covered        >= 3
  intrabar_validated    == true
  costs_subtracted      == true
  excess_return_ann     >  0        # vs matched-exposure benchmark
  information_ratio     >= 0.5
  jensen_alpha_tstat    >  2.0
  down_capture          <  100
  capture_ratio         >  1.0
  deflated_sharpe       >= 0.95     # at true trial count
  forward_paper         >= 30 round trips or 90 days
```

## 7. The uncomfortable implication for mutual funds

If the gate is "beat SPY net of costs", then **most funds fail it by construction**: SPIVA reports
**92.89% of large-cap active funds trailed the S&P 500 over 20 years** (and 95.01% of all domestic funds
trailed the S&P Composite 1500). So "mutual funds win given enough time" is true for the *wrapper* and
false for the *average active manager*. See `04_mutual_funds/MF_CAN_WIN.md` for how to act on that
distinction without giving up the intuition that funds are the right vehicle.

---

## 8. What to report on every dashboard card

Add these four to any pick or strategy card, next to PF:

```
benchmark: SPY TR          excess: −1.9%/yr        IR: −0.4        down-capture: 118
```

A card that cannot fill those four fields is not ready to be shown, let alone funded.
