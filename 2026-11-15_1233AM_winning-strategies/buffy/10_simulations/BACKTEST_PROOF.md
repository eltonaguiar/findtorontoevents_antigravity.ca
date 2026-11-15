# Does the path forward actually backtest as profitable?

**Run:** `tools/sim_path_forward.py` · **Data:** Yahoo adjusted close (dividends + splits) ·
**Window:** 2004-12 → 2026-11 monthly; 2001-01 → 2026-11 daily; BTC 2014-09 → 2026-11 ·
**Costs:** 6 bps/side equity, 15 bps/side crypto, cash earns real T-bill (^IRX) ·
**Trials:** 8 pre-registered, no parameter search · **Reproduce:** `python3 tools/sim_path_forward.py`

---

## The short answer

**"Profitable" yes. "Beats the benchmark" no.** After costs, the beta core compounds at 10.76%/yr with
DSR 0.99 — but it earns exactly what its own exposure earns, so excess is −0.00%. **None of the six active
rules beat a matched-exposure benchmark.** The trend overlay delivered something real but different:
**the same risk-adjusted return with less than half the drawdown.**

Anyone reading this as "we found alpha" is misreading it. The honest result is:

| Claim | Backtest verdict |
|---|---|
| Low-cost beta is profitable after costs | **SUPPORTED** (10.76% CAGR, DSR 0.99) |
| A trend overlay beats matched-exposure buy-and-hold | **NOT SUPPORTED** (−0.09%/yr, i.e. a wash) |
| A trend overlay cuts drawdown at no return cost | **SUPPORTED** (−21.8% vs −50.8% MDD, SR 0.66 vs 0.65) |
| Dual momentum beats the benchmark | **REJECTED** (−2.57%/yr; failed OOS by −6.34%) |
| 60/40 beats 60% SPY + 40% cash | **REJECTED** (−3.03%/yr; −5.90% OOS) |
| An RSI(2) swing rule works after costs | **REJECTED** (0.21% CAGR, SR −0.64, DSR 0.00) |
| BTC 200-day trend beats BTC hold | **PROMISING, UNPROVEN** (SR 1.10 vs 0.93, but DSR 0.84 < 0.95) |

---

## Full results (baseline costs)

| Strategy | CAGR | Excess vs matched | Sharpe | MaxDD | DSR | Exposure | Trades |
|---|---:|---:|---:|---:|---:|---:|---:|
| BH_SPY (beta core) | 10.76% | −0.00% | 0.65 | −50.8% | 0.99 | 1.00 | 1 |
| SIXTY_FORTY | 8.11% | −3.03% | 0.65 | −28.5% | 0.99 | 1.00 | 1 |
| **FABER10_SPY** | 8.33% | **−0.09%** | **0.66** | **−21.8%** | 0.99 | 0.78 | 33 |
| DUALMOM_2 | 7.59% | −2.57% | 0.50 | −27.6% | 0.96 | 0.91 | 28 |
| DUALMOM_3 | 8.13% | −1.88% | 0.45 | −30.0% | 0.94 | 0.92 | 55 |
| RSI2_SPY | 0.21% | −2.30% | −0.64 | −14.5% | 0.00 | 0.02 | 117 |
| BTC_BH | 51.04% | +48.67%† | 0.93 | −83.0% | 0.65 | 1.00 | 1 |
| BTC_TREND200 | 58.62% | +47.69%† | 1.10 | −63.6% | 0.84 | 0.64 | 30 |

† **Do not read BTC's "+48%" as edge.** Its benchmark is matched-exposure SPY; a 2014–2026 crypto position
beating SPY is *beta*, not skill. BTC's own benchmark is BTC, and against that BTC_TREND200 adds
+7.6pp CAGR and 19pp less drawdown — the only active result that is positive on both axes, and still only
DSR 0.84.

### In-sample vs out-of-sample

| Strategy | IS excess (2004–2015) | OOS excess (2016–2026) | Reading |
|---|---:|---:|---|
| BH_SPY | −0.01% | 0.00% | identity check ✓ |
| SIXTY_FORTY | −0.18% | −5.90% | bonds dragged OOS |
| FABER10_SPY | −0.06% | −0.12% | **stable wash** — the DD benefit is not a fluke |
| DUALMOM_2 | −0.91% | −4.25% | worse OOS |
| DUALMOM_3 | **+2.55%** | **−6.34%** | **classic regime overfit** |
| RSI2_SPY | −1.79% | −2.87% | negative in both halves |
| BTC_TREND200 | +80.13% | +13.32% | decays with regime, still positive |

DUALMOM_3 is the textbook case the framework exists to catch: it looks like it works in the first half
(+2.55%/yr) and loses badly in the second (−6.34%/yr). Had I reported the full sample only, nobody would
have seen it.

### Cost stress (2× all costs)

| Strategy | CAGR (1×) | CAGR (2×) | Change |
|---|---:|---:|---:|
| BH_SPY | 10.76% | 10.75% | −0.01pp |
| FABER10_SPY | 8.33% | 8.23% | −0.10pp |
| DUALMOM_2 | 7.59% | 7.44% | −0.15pp |
| DUALMOM_3 | 8.13% | 7.85% | −0.28pp |
| **RSI2_SPY** | **0.21%** | **−0.34%** | **−0.55pp → negative** |
| BTC_TREND200 | 58.62% | 57.45% | −1.17pp |

Low-turnover rules are cost-insensitive. The swing rule is *made of* costs — doubling them turns it
negative. That alone is a kill signal.

---

## What this does and does not prove

**Proves (within this data):**
1. A buy-and-hold beta core is profitable after realistic costs with overwhelming statistical support.
2. A 10-month SMA overlay on SPY reduces max drawdown by 29pp at no measurable return cost, in both halves
   of the sample. That is a *risk* result, repeatable and stable.
3. Several popular active rules (dual momentum, 60/40-as-alpha, RSI(2) swing) do **not** beat their own
   exposure benchmark on this data, and the swing rule cannot survive doubled costs.

**Does not prove:**
- That the trend overlay will keep cutting drawdown (it depends on trends existing; 2009–2020 was a
  whipsaw graveyard for SMA rules, and this sample contains one of each regime).
- Anything about forward returns. One 22-year window is **one draw**, not 22 independent tests.
- That these are the best rules — they are 8 pre-registered textbook rules in a **3-asset universe chosen
  in 2026** (SPY/TLT/GLD), so there is hindsight in the universe even though there is none in the rules.
- That costs are complete: **ETF expense ratios (SPY 0.0945%, TLT ~0.15%) and taxes are not deducted.**
  They are small relative to the effects above but they are real, and they favour every row equally.

## Reproducibility and honesty notes

- No parameter was tuned. Faber=10M, momentum=12M, RSI=2/5/65/10d, SMA=200 were fixed before the run.
  `STRATEGIES` in the script is the trial registry; adding a strategy **invalidates the DSR** and the
  script will use the larger N.
- DSR uses per-**period** Sharpe with trial variance from the same frequency (monthly N=5, daily N=3).
  Mixing annualised monthly and daily Sharpes inflates the variance and understates the hurdle — the first
  version of this script did exactly that and reported DSR 0.14 for SPY. Fixed; do not reintroduce.
- Signals are acted on at the close that generates them. A T+1 execution would shave a few bps off the
  daily rules and nothing meaningful off the monthly ones.
- BTC dates are matched to SPY trading days; non-SPY days contribute 0 to the SPY benchmark leg
  (price forward-filled). This slightly *favours* the BTC rows' excess, another reason not to read it as edge.

## What the path forward actually is, per this evidence

| Sleeve | Status after backtest | Size guidance |
|---|---|---|
| **A. Low-cost beta core** | **Proven profitable** (DSR 0.99) | the actual deployment vehicle |
| **B. 10-month trend overlay** | **Proven risk reduction, not alpha** | overlay on A; sells volatility, not return |
| **C. BTC 200-day trend** | **Promising, unproven** (DSR 0.84) | small, forward-tested, capped |
| **D. Dual momentum / 60-40-as-alpha** | **Rejected** (−2.57%, −3.03%/yr) | none |
| **E. RSI(2) swing** | **Rejected, cost-dominated** | killed — no forward test needed |

Sleeves D and E are already dead on 25 years of data. Spending forward-test months on them would be
paying for information we already have. That is the point of the protocol in `FORWARD_PROTOCOL.md`:
**backtest kills what it can kill, so forward testing is spent only on the two survivors (B and C).**
