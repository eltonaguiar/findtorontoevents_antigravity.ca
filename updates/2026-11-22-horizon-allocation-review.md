# Horizon and asset-class review: first backtest tranche

**Date:** 2026-11-22 · **Branch:** `research/horizon-allocation-review-2026-11-22`
**Files:** `tools/horizon_backtest.py`, `tests/test_horizon_backtest.py`,
`reports/2026-11-22-horizon-allocation-review-plan.md`,
`reports/2026-11-22-horizon-allocation-review.md`,
`reports/horizon_backtest_2026-11-22.json`

## Why

Peer answers to "what should I invest in for short / medium / long horizons" all
agreed on the shape (cash for short money, index ETFs for long money, a capped
sleeve for trading) but rested on assertions — including two from our own audit2
page stated as fact: "volatility scaling is free alpha (+0.3 Sharpe for any
momentum strategy)" and "Faber TAA is B-tier (Sharpe 1.74/1.65)". Those are
testable, so they were tested rather than repeated.

## What was built

`tools/horizon_backtest.py` — a small, dependency-light engine (yfinance +
stdlib) with five experiments:

- **E1 horizon**: rolling 1/3/5/10-year returns for SPY, 60/40 and cash, plus
  the share of windows where equity loses to cash.
- **E2 vol scaling**: identical TSMOM signal, unscaled vs inverse-vol scaled at
  cap 1.0 and cap 2.0, each at 1× and 2× cost.
- **E3 Faber**: monthly 10-month SMA regime vs buy-and-hold on SPY and QQQ.
- **E4 MER drag**: 30-year terminal wealth across expense ratios.
- **E5 class-vs-pick**: BTC vs SPY vs cash buy-and-hold over identical windows.

No-look-ahead is structural: `_shift` lags every signal one day, `run_exposure`
takes the weight held *over* day *t* and earns `close[t]/close[t-1]`. Unit tests
pin that, plus the cost-per-switch accounting, excess-over-cash Sharpe, drawdown,
overlapping-window counts and the MER monotonicity.

## Findings

| claim | result |
|---|---|
| short money belongs in cash | **pass** — SPY lost to T-bills in 20.6 % of 1-year windows; p10 −12.0 % |
| long money in equity is safe | **pass with caveat** — 92 % of 10-year windows positive, but 11.6 % lost to cash on ~3 independent windows |
| vol scaling is +0.3 Sharpe of free alpha | **refuted** — ΔSharpe −0.016 (cap 1), −0.072 (cap 2); drawdown halves, CAGR falls 8.4 %→6.6 % |
| Faber is B-tier Sharpe 1.74/1.65 | **does not reproduce** — 0.56 (SPY) / 0.65 (QQQ) daily-excess, 0.62/0.75 monthly; drawdown benefit is real, CAGR costs 2.2 pp/yr |
| MER is permanent negative alpha | **confirmed** — 1.5 % MER ends 33.6 % behind a 0.05 % fund over 30 years |
| required_n 1,730,370 | **same order of magnitude** — ~5.9 M recomputed from the ledger's own effect and dispersion |
| CRYPTO KILL means crypto is a bad investment | **refuted as stated** — BTC buy-and-hold Sharpe 0.91 vs SPY 0.66 over 2014–2026, with an −83 % drawdown; the KILL verdict is about our picks |

## Verification

```
$ python3 -m pytest tests/test_horizon_backtest.py -q
10 passed

$ python3 tools/horizon_backtest.py
loaded SPY: 8512 bars 1993-01-29..2026-11-20
loaded BIL: 4903 bars 2007-05-30..2026-11-20
loaded BTC-USD: 4450 bars 2014-09-17..2026-11-22
loaded ^IRX: 16708 bars 1960-01-04..2026-11-20
wrote reports/horizon_backtest_2026-11-22.json
```

Every number in the report is reproducible with that one command. Costs are 5 bps
per switch charged at 1× and 2×; cash is BIL (2007+) or a ^IRX accrual index
(1993+); rolling windows are labelled overlapping with the effective independent
count printed alongside.

## Limits

Overlapping windows mean the long-horizon bands rest on a handful of regimes.
Daily-rebalanced 60/40 is an idealisation with no rebalance cost. No taxes, FX or
account-wrapper modelling. C5 (dual momentum), C6 (cost per cadence) and C10
(sleeve accounting) are deliberately not run yet and are listed as NOT RUN rather
than estimated.

## Nothing here is a live signal

This tranche produces no picks, no position sizes, and no promotions. It is the
evidence base for the horizon framework and for correcting two claims on the
audit2 page that are currently stated as fact.
