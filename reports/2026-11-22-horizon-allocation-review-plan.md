# Deep review plan — horizon, asset class, and the "best possible investment"

**Date:** 2026-11-22 · **Status:** plan + first backtest tranche executed
**Companion:** `reports/2026-11-22-horizon-allocation-review.md` (results),
`tools/horizon_backtest.py` (engine), `reports/horizon_backtest_2026-11-22.json` (machine output)

## 1. What is being reviewed

Four peer answers to "what is the best possible investment for short, medium and
long horizons" plus our own audit2/audit3 doctrine. The peer answers agree on
the shape — cash/GIC for short money, diversified low-cost ETFs for long money,
a capped research sleeve for trading — and disagree mostly on emphasis and on
how much of the ledger's "KILL" language applies to *asset classes* rather than
to *our own strategy cells*. That distinction is the single most important thing
this review has to get right, so it is claim C9 below.

## 2. Claims inventory

Each claim gets a test, a data source, and a pass/fail rule fixed **before** the
run (M-107 applies to this review exactly as it does to a trading hypothesis).

| # | claim | source | test | pass/fail rule |
|---|---|---|---|---|
| C1 | Short-horizon money (≤3y) should not be in equities | all four peers | rolling 1y/3y SPY vs cash return distributions, 1993–2026 | equity underperforms cash in a material share of windows |
| C2 | Long-horizon diversified equity beats cash with high probability | all four peers | rolling 10y SPY vs cash | ≥90 % of 10y windows positive excess |
| C3 | "Volatility scaling is free alpha... improves Sharpe by 0.3+ for any momentum strategy" | audit2 doctrine | same TSMOM signal, scaled vs unscaled | measured ΔSharpe ≥ +0.30 |
| C4 | Faber 10-month TAA is B-tier (Sharpe 1.74/1.65) | POD-FABER-TAA | reproduce monthly 10-month SMA on SPY/QQQ, net of 5 bps/switch, and at 2× | Sharpe reproduces within ±0.25 and survives 2× cost |
| C5 | ETF dual momentum OOS PF 2.746 | POD-ETF-DUAL-MOMENTUM | 12-1 sector rotation top-1 vs SPY, monthly | PF ≥ 1.5 net at 2× cost with n ≥ 100 switches |
| C6 | Intraday ETF trading is uninvestable (slippage ≈234 % of per-trade PnL) | audit3 | cost drag as % of gross PnL by cadence | drag ≥ 50 % at daily cadence |
| C7 | Mutual-fund MER is a permanent negative alpha | GLM/Claude | 30-year terminal wealth at 0.05/0.5/1.0/1.5/2.0 % MER | terminal gap vs cheapest ≥ 15 % |
| C8 | ETF `required_n` = 1,730,370 is a real requirement | audit3 | power calculation from the observed effect size and its dispersion | required_n recomputes to the same order of magnitude |
| C9 | "CRYPTO KILL" means crypto is a bad investment | peer conflation | separate *pick alpha* (our rows) from *asset-class risk premium* (BTC buy-and-hold, same windows) | state both numbers; the two are different questions |
| C10 | The research sleeve should be ≤5 % and funded only by forward-gated pods | peers + our gates | accounting: what a 5 % sleeve can contribute vs its drag | sleeve cannot move the portfolio total by more than ±0.5 %/yr at realistic edge |

## 3. Workstreams (review rounds)

**R1 — horizon floor (C1, C2).** Rolling-window outcome distributions for SPY,
60/40, and a T-bill proxy. Report medians, 10th/90th percentiles, and the share
of windows where equity loses to cash. Explicitly flag that overlapping windows
are correlated and state the effective independent window count.

**R2 — doctrine claims (C3, C4, C5).** Same-signal A/B tests. The point is not
to find a better strategy but to check whether the *stated* improvements
reproduce. A claim of "+0.3 Sharpe for any momentum strategy" is testable and
either reproduces or does not.

**R3 — cost realism (C6).** Cost drag per cadence, at 1× and 2× measured
slippage, for daily, weekly, monthly and quarterly rebalancing of the same
signal. This decides whether a horizon is even reachable for retail.

**R4 — vehicle comparison (C7, C8).** MER drag over 30 years; the power
calculation behind `required_n`; what gross alpha a 1.5 % MER fund must earn to
match a 0.05 % ETF.

**R5 — class vs pick (C9).** Hold BTC, gold, SPY and cash over identical windows
and compare with our pick-level results. The ledger's KILL verdicts are about
*our picks*, and a review that lets a KILL verdict on picks become a verdict on
the asset class would be committing the same error it is auditing.

**R6 — sleeve accounting (C10).** With a 5 % sleeve and a realistic post-cost
edge, how much can it add or subtract per year, and what is the sequence risk of
funding it before the forward gates pass.

**R7 — data-integrity prerequisites.** Before any of the above is called proven:
fix the audit2 population 404, wire POD-EQUITY-BREAKOUT's emitter (it has zero
forward rows while orphan H-119 has 430), fix the winner-stays bug on
POD-ETF-DUAL-MOMENTUM, and score auto-expired rows as their own class instead of
dropping 9,277 of them.

**R8 — decision framework.** Turn the results into a standing rule with
pre-committed promotion and kill thresholds, and an explicit list of what would
change our mind.

## 4. Evidence rules for this review

- Every backtest states its data source, date range, cost assumption, and
  rebalance cadence, and applies the signal from the *next* bar. No exceptions.
- 2× the measured cost is run for every strategy claim.
- Benchmark-relative: excess over the matched hold, not raw return.
- Overlapping-window statistics are labelled as such and never presented as
  independent samples.
- Survivorship: the core ETFs (SPY/QQQ/AGG/GLD/BIL) have existed for the full
  test window, so the core tests are not survivorship-biased; sector-rotation
  tests are, and are flagged.
- No tax, FX, or account-wrapper modelling in this tranche. Those change the
  net numbers enough that pretending otherwise would be dishonest.

## 5. Out of scope (deliberately)

- Real-money execution. Everything here is paper/backtest.
- Personal financial advice. This is a research programme, not a plan for a
  specific person's money.
- Options, futures term structure, and commodity roll yield: the data layer
  cannot price them yet, and the ledger already says FUTURES has n=4.

## 6. Order of work

1. R1 and R2 first: they answer the user's actual question (which horizon, which
   vehicle) and are runnable today on free daily data.
2. R3 and R4 next: they decide whether any short-horizon idea is even fundable.
3. R5 and R6: class-vs-pick framing and sleeve accounting.
4. R7: the measurement repairs, without which every later number is suspect.
5. R8: the standing rule.
