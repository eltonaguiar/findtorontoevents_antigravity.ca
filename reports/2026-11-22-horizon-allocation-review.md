# Horizon and asset-class review — first backtest tranche

**Date:** 2026-11-22 · **Status:** C1–C5, C7–C9 tested on real prices; C6/C10 deferred
**Engine:** `tools/horizon_backtest.py` · **Tests:** `tests/test_horizon_backtest.py` (10 passing)
**Plan:** `reports/2026-11-22-horizon-allocation-review-plan.md`
**Raw output:** `reports/horizon_backtest_2026-11-22.json`

## 0. One-paragraph answer

Over 33 years of real prices, holding a broad US equity index for **one year
loses to cash in ~21 % of windows** and finishes negative in 18 %; over **ten
years it still loses to cash in ~12 %** of windows. Longer horizons are better,
not safe. Cash/T-bills delivered a **17.5 % total return over ten years** with
almost no drawdown, so "long horizon" is a probability statement, not a
guarantee. The doctrine's claim that **volatility scaling adds +0.3 Sharpe is
false on this data** (−0.016, and −0.072 with leverage allowed): it cut drawdown
from 21 % to 11.4 % but also cut CAGR from 8.4 % to 6.6 %. Faber's 10-month
allocation **reduces drawdown by half and slightly improves Sharpe** on SPY
(+0.05), not to the 1.74 the audit quotes, and it **costs 2.1 pp/yr of CAGR**. A
1.5 % MER fund ends with **33.6 % less money** than a 0.05 % fund after 30 years.
And **BTC buy-and-hold beat SPY on Sharpe over 2014–2026 (0.91 vs 0.66)** — so
the ledger's `CRYPTO KILL` verdict is a verdict on *our picks*, not on the asset
class.

## 1. Method and honesty controls

| item | value |
|---|---|
| prices | yfinance, auto-adjusted (dividends included), `period=max` |
| SPY | 8,512 bars, 1993-01-29 → 2026-11-20 |
| QQQ | 6,970 bars, 1999-03-10 → |
| AGG | 5,825 bars, 2003-09-29 → |
| BIL (cash) | 4,903 bars, 2007-05-30 → |
| ^IRX (13-week T-bill yield) | 16,708 bars, 1960 → (used to build a cash index for the long window) |
| BTC-USD | 4,450 bars, 2014-09-17 → |
| cost | 5 bps per switch, every strategy also run at 10 bps |
| signal timing | signal from data through day *t−1* sets the weight held over day *t* (`_shift`), enforced by a unit test |
| Sharpe | excess over cash, annualised from daily returns |
| windows | rolling, **overlapping** — effective independent count printed with every row |

Two windows are used deliberately: **1993–2026** (SPY vs a T-bill accrual index,
33 independent 1-year windows) for the horizon question, and **2007–2026** (BIL
is investable from 2007) for the strategy tests. No look-ahead, no survivorship
issue for the core ETFs (all existed for the full test window), no tax or FX
modelling.

## 2. C1/C2 — the horizon question, answered with distributions

Rolling SPY total returns, 1993-01-29 → 2026-11-20 (8,491 sessions):

| horizon | SPY median | SPY p10 | SPY p90 | SPY negative | cash median | SPY **loses to cash** | indep. windows |
|---|---|---|---|---|---|---|---|
| 1 year | +14.5 % | −12.0 % | +30.6 % | 18.1 % | +2.1 % | **20.6 %** | 33 |
| 3 years | +41.3 % | −16.3 % | +88.7 % | 16.3 % | +5.4 % | **19.6 %** | 11 |
| 5 years | +72.3 % | −5.0 % | +146.8 % | 14.9 % | +11.3 % | **24.1 %** | 6 |
| 10 years | +134.3 % | +17.9 % | +286.6 % | 7.9 % | +17.5 % | **11.6 %** | 3 |

Findings:

- **C1 passes.** One-year equity money is genuinely at risk: a fifth of all
  windows underperformed T-bills, and the 10th percentile is −12 %. Short money
  belongs in cash/GICs.
- **C2 passes but weaker than the folklore.** Ten-year windows were positive in
  92 % of cases, but **11.6 % still lost to cash** — and the sample contains only
  ~3 independent 10-year windows, so this is a statement about a handful of
  regimes, not 5,971 independent observations.
- **The share that loses to cash does not fall monotonically**: 5-year is worse
  than 3-year (24.1 % vs 19.6 %) because the dot-com and GFC windows sit in that
  bucket. Any claim of the form "over N years stocks always win" is refuted by
  the data at every N tested except none.

The 2007+ window (which peers would call "modern") is much kinder — SPY loses to
BIL in 16.8 % / 4.8 % / 1.2 % / 0.0 % of 1/3/5/10-year windows — but it has **one
independent 10-year window** and starts after the two worst drawdowns. Using it
alone would be the classic window-selection error.

60/40 (daily-rebalanced SPY/AGG), 2007+: median 3-year +30.8 % vs SPY +45.2 %,
5-year +57.6 % vs +90.5 %, 10-year +147.8 % vs +248.8 %, with a 5-year
worst-case of +37.9 % vs SPY +50.4 %. Less upside, less dispersion — the
expected shape, now with numbers.

## 3. C3 — "volatility scaling is free alpha (+0.3 Sharpe)" — **REFUTED**

Same TSMOM signal (SPY > 200-day SMA), 2007-05-30 → 2026-11-20, 5 bps/switch:

| variant | CAGR | vol | Sharpe | max DD | switches |
|---|---|---|---|---|---|
| unscaled, 0/1 exposure | 8.38 % | 11.69 % | **0.627** | −21.0 % | 114 |
| inverse-vol, target 10 %, cap 1.0 | 6.64 % | 8.87 % | **0.611** | −11.4 % | 2,613 |
| inverse-vol, target 10 %, cap 2.0 | 6.64 % | 9.95 % | **0.555** | −13.9 % | 3,823 |

ΔSharpe = **−0.016** (cap 1) and **−0.072** (cap 2). At 2× cost: 0.602 / 0.573 /
0.499 — still no improvement. The doctrine claim of +0.30 does not reproduce.

What vol scaling *does* buy is real: drawdown roughly halved and volatility cut
by a quarter. That is **risk transformation, not alpha** — the portfolio earns
less because it holds less. Presenting it as "free alpha" would make every
subsequent Sharpe comparison dishonest, because the comparison is between
different risk levels unless the baseline is vol-matched (this is exactly what
gate **G6b** in the per-class harness exists to prevent).

Caveat in the strategy's favour: the cap-2 variant re-levers daily (3,823
switches), which is not practical and is charged for. A weekly-rebalanced vol
target would land between the two rows. The sign of the result is unlikely to
flip; the magnitude would narrow.

## 4. C4 — Faber 10-month TAA vs the quoted Sharpe 1.74/1.65 — **DOES NOT REPRODUCE**

Monthly 10-month SMA regime, held from the next month's first session, 5 bps/switch:

| | CAGR | vol | Sharpe (daily excess) | Sharpe (monthly) | max DD | switches | time in market |
|---|---|---|---|---|---|---|---|
| SPY Faber | 7.88 % | 12.39 % | 0.562 | 0.622 | **−24.7 %** | 29 | 76.0 % |
| SPY buy & hold | 10.03 % | 19.70 % | 0.511 | 0.600 | −55.2 % | 1 | 100 % |
| QQQ Faber | 11.42 % | 16.71 % | 0.647 | 0.751 | **−28.6 %** | 31 | 76.1 % |
| QQQ buy & hold | 14.96 % | 22.43 % | 0.670 | 0.751 | −53.4 % | 1 | 100 % |

- On SPY the regime filter **improves Sharpe by +0.05 and halves drawdown**, at
  the cost of 2.15 pp/yr of CAGR — a defensible risk trade, not an alpha claim.
- On QQQ it **does not improve Sharpe at all** (0.647 vs 0.670) while still
  giving up 3.5 pp/yr of CAGR.
- The audit's quoted 1.74/1.65 is roughly **three times** the reproduced
  number, even on the monthly basis. Either it was computed on a different
  sample, as a raw (not excess-over-cash) Sharpe, or with a different
  rebalance/leverage assumption. As stated, the number is not reproducible from
  the data, so treating Faber as "B-tier" overstates it. The **direction** of
  the claim (lower drawdown) is right.
- Survives 2× cost (Sharpe 0.556 vs 0.562 on SPY), because 29 switches in 19
  years is cheap. Cost is not what breaks it; the return give-up is.

## 5. C7 — MER drag — **CONFIRMED, and larger than most people expect**

$1 compounded at 7 % gross for 30 years, net of expense ratio:

| MER | terminal multiple | vs 0.05 % |
|---|---|---|
| 0.05 % | 7.506 | — |
| 0.50 % | 6.614 | −11.9 % |
| 1.00 % | 5.743 | −23.5 % |
| 1.50 % | 4.984 | **−33.6 %** |
| 2.00 % | 4.322 | **−42.4 %** |

A 1.5 % MER fund needs to out-earn a 0.05 % ETF by **1.45 pp/yr, every year, for
30 years** just to draw. That is the hurdle the peer answer described as
"permanent negative selection alpha", and it is the single largest, most certain
number in this whole review — larger than any edge the pods are chasing.

## 6. C8 — is `required_n = 1,730,370` plausible?

Power arithmetic from the ledger's own numbers (ETF: effect −0.0062 %/trade, CI
half-width 0.433 % on n = 590): implied per-trade σ ≈ 5.4 %, so
n ≈ (z₀.₉₇₅ + z₀.₈)² σ²/μ² ≈ 7.84 × (0.0537/0.000062)² ≈ **5.9 million**.
The ledger's 1.73 M and this 5.9 M are the same order of magnitude; the factor
difference is α/power convention. CRYPTO (effect −0.418 %/trade, σ ≈ 11.4 %)
recomputes to ~5,900 vs the ledger's 917 — again the same story.

The usable conclusion is not the exact integer. It is: **the observed effects are
1–2 orders of magnitude smaller than their own dispersion**, so no realistic
sample will ever settle them. That is a reason to withdraw the question, not to
collect more trades. C8 passes as an order-of-magnitude check and strengthens the
case against funding those cells.

## 7. C9 — "CRYPTO KILL" is about our picks, not about crypto

2014-09-17 → 2026-11-20, identical windows, buy-and-hold, no timing:

| asset | CAGR | vol | Sharpe vs cash | max DD | median 1y | median 3y | median 5y |
|---|---|---|---|---|---|---|---|
| BTC-USD | **+49.1 %** | 65.4 % | **0.911** | **−83.0 %** | +70.7 % | +328.6 % | +1,023.9 % |
| SPY | +12.6 % | 17.5 % | 0.655 | −33.7 % | +15.9 % | +45.6 % | +92.1 % |
| BIL | +1.9 % | 0.26 % | 0.00 | −0.2 % | +1.4 % | +4.1 % | +6.6 % |

Our ledger says CRYPTO is KILL (n = 6,926 picks, −0.42 %/trade, DSR 0.000). Both
statements are true at once, and conflating them would be the exact error this
review exists to catch:

- **Our crypto picks** lost money net of costs, with a CI entirely below zero.
  That is a verdict on the signal and the exit expression.
- **The crypto asset class** delivered a higher Sharpe than US equities over this
  window, with a drawdown that would have tested any real holder at −83 %.

An honest statement is: *"we have no crypto timing edge; holding crypto has been
a high-return, very-high-risk bet over a short, bull-dominated sample."* Twelve
years contains roughly two cycles, so the asset-class number deserves no more
confidence than that — but it is not zero, and it is certainly not −0.42 %.

## 8. Verdict table

| # | claim | verdict |
|---|---|---|
| C1 | short money should not be in equities | **PASS** (21 % of 1y windows lost to cash; p10 −12 %) |
| C2 | long-horizon equity beats cash with high probability | **PASS with caveat** (92 % positive, 11.6 % lost to cash, ~3 independent windows) |
| C3 | vol scaling is free alpha, +0.3 Sharpe | **REFUTED** (−0.016 / −0.072; risk reduction is real, alpha is not) |
| C4 | Faber TAA is B-tier, Sharpe 1.74/1.65 | **DOES NOT REPRODUCE** (0.56/0.65; drawdown benefit is real) |
| C5 | ETF dual momentum OOS PF 2.746 | **NOT RUN** — next tranche |
| C6 | daily ETF trading is uninvestable | **NOT RUN** — next tranche (cost-per-cadence) |
| C7 | MER is permanent negative alpha | **PASS** (−33.6 % terminal wealth at 1.5 % MER) |
| C8 | ETF required_n = 1,730,370 | **PASS as order of magnitude** (~5.9 M recomputed) |
| C9 | CRYPTO KILL means crypto is bad | **REFUTED as stated** (BTC hold Sharpe 0.91 vs SPY 0.66; picks are a different question) |
| C10 | a 5 % sleeve is the right size | **NOT RUN** — sleeve accounting tranche |

## 9. What this changes about "the best possible investment"

1. **The floor is not optional, and it is bigger than it looks.** T-bills
   compounded to +17.5 % over ten years with essentially no drawdown. Any equity
   allocation has to clear that, plus costs, plus the ~12 % chance of losing to
   it over a decade.
2. **Horizon helps, but it is a probability, not a promise.** Long money can
   reasonably be in a broad index; short money cannot. The 1-year p10 of −12 %
   is the number that should decide where 1–3-year money sits.
3. **Do not buy "free alpha" claims.** Vol scaling changed the risk, not the
   return per unit of risk. The audit2 page states it as fact; the data says it
   is false, and the page should be corrected because it is used to justify
   position sizing.
4. **Fees are the one certain edge.** A 1.45 pp/yr hurdle is larger than most of
   the researched effects, and it is guaranteed.
5. **Keep pick-level and class-level verdicts in separate columns.** CRYPTO is
   `KILL` for our picks and was a strong (if brutal) asset-class hold. Both facts
   belong in the record.

## 10. Limitations

- Overlapping windows: the 10-year rows rest on ~3 independent windows. The
  percentile bands are error bars on a handful of regimes.
- Daily-rebalanced 60/40 is an idealisation; no rebalance cost is charged.
- Cash for 1993–2007 is a T-bill accrual index, not an investable fund; BIL is
  used wherever it exists.
- Monthly Faber Sharpe uses calendar-month compounding; the audit's 1.74 was
  computed some other way that is not stated.
- No taxes, no FX, no account-wrapper effects. A Canadian taxable account would
  change the net numbers materially.
- Nothing here is personalised financial advice; it is a research review.

## 11. Next rounds

R3 (cost per cadence), R4 dual momentum reproduction (C5), R6 sleeve accounting
(C10), and the R7 measurement repairs — POD-EQUITY-BREAKOUT's starving emitter
and the 9,277 auto-expired rows — before any of this is used to size capital.
