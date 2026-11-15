# Executed backtests and risk simulations: results, not a promised edge

**Preregistered before execution:** [main commit199ddeb3ea6dcb726ee268378c8d0446e6276e58](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/commit/199ddeb3ea6dcb726ee268378c8d0446e6276e58), H-142/H-143. Exact rules/hash: [frozen plan](./08_SIMULATION_PLAN.md), [registry capture](./SIMULATION_PREREGISTRATION.json).

**Conclusion:** the broad fund/ETF passive path produced **positive historical modeled returns**. The fixed tactical challenger also made money, but **failed both SPY outperformance and the exposure-matched risk diagnostic**. Eliminate that exact challenger from the alpha forward queue now; do not wait months or retune it until it passes.

This does **not** prove a repeatably profitable predictor. All capital/admissibility permissions remain false/UNTESTED. Historical summaries had already been viewed; no virgin OOS claim.

## Executed implementation plan

> For agentic workers: use the existing executing-plans workflow. All source and evidence are opt-in research in this folder, not production integration.

**Goal:** reproduce funded net historical portfolios and reject false claims of alpha.
**Architecture:** immutable seven-instrument price CSV -> funded account runner -> full NAV and benchmark curves -> fixed block-risk diagnostics. No external service in the runner.
**Tech stack:** Python standard library, CSV/JSON and unittest.

- [x] Inspect current registry and rejected families; no H-141 survivor selection retune.
- [x] Commit H-142/H-143 to main before building/running the runner.
- [x] Write focused tests and observe11expected failures because the new runner was absent.
- [x] Implement [simulation_runner.py](./simulation_runner.py) and run [test_simulation_runner.py](./test_simulation_runner.py):13passed after the independent-review cost correction.
- [x] Freeze/validate all1,255source sessions, seven adjusted/raw-price instruments; no fill-forward or exclusions.
- [x] Execute two prespecified cost cases,24account curves and joint block/horizon scenarios.
- [x] Independently verify all28,120NAV rows and14closed-form passive terminal values.
- [x] Append actual negative and positive results, limitations and [forward protocol](./10_FORWARD_TRACKING_PROTOCOL.md).

## Full-history passive fund/ETF backtests

**2021-11-15 through2026-11-13; USD100,000initial account.**5bps per dollar traded each side, including entry and final liquidation; ongoing fund expenses embedded in adjusted NAV. No leverage; fractional total-return modeling units. Taxes/platform/FX and independent action/fill verification are excluded.

| Fixed holding | Net total return | Net calendar CAGR | Max drawdown | Excess Sharpe vs SGOV |
|---|---:|---:|---:|---:|
| FXAIX | +73.05% | 11.61% | 24.50% | 0.506 |
| FZROX | +66.00% | 10.68% | 25.12% | 0.449 |
| VTSAX | +64.35% | 10.46% | 25.36% | 0.438 |
| SPY | +72.38% | 11.52% | 24.50% | 0.498 |
| VTI | +64.39% | 10.47% | 25.36% | 0.438 |
| BND | **-1.51%** | **-0.30%** | 17.31% | -0.648 |
| SGOV | +20.86% | 3.87% | 0.06% | Not applicable |

The five-year broad US fund holdings were profitable **in this historical model**; bonds did not guarantee profit/ballast. FXAIX's roughly0.09percentage-point CAGR advantage over SPY is small and consistent with wrapper/expense/tracking differences, **not active prediction alpha**.

Equity-fund drawdowns around25%fail a hypothetical20%capital-loss mandate despite profitable ending wealth. Some scenarios/horizons can lose. Fund structure and longer holding time do not guarantee winnings.

At20bps/side, FXAIX CAGR11.54%, SPY11.45%, BND-0.36%: low-turnover baseline results were robust to this specific transaction-cost stress, not every practical cost/access constraint.

## Exact-window tactical test and controls

**2022-09-01 through2026-11-13**, after10month-end observations and next-close execution. First9.5months of source history supply warmup and are **not** included in these comparisons.

| Book,5bps/side | Net total return | Net CAGR | MDD | Excess Sharpe |
|---|---:|---:|---:|---:|
| Same-window SPY buy/hold | +101.05% | 18.09% | 18.76% | 0.845 |
| Same-window FXAIX buy/hold | +101.75% | 18.19% | 18.76% | 0.858 |
| SGOV proxy | +20.27% | 4.49% | 0.05% | N/A |
| **Fixed10-month SPY trend/SGOV** | **+45.50%** | **9.34%** | **11.86%** | **0.438** |
| Ex-post exposure-matched monthly mix | +86.22% | 15.96% | 15.87% | 0.843 |

Tactical mean equity exposure84.16%. The control uses that realized exposure **ex post** and is only an exposure diagnostic, not a preselected investable winning allocation.

- Tactical SPY CAGR gap: **-8.75percentage points/year**; IR **-0.778**.
- Smaller drawdown did not deliver higher cash-relative Sharpe than its exposure control.
- Annualized mean SPY excess negative in both pre2025 (-8.18pp) and from2025 (-8.42pp) historical segments.
- Paired95%mean-excess lower bounds: -16.96/-17.09/-15.48pp for21/60/120session blocks after boundary-cost correction. These are historical uncertainty diagnostics, not prospective probabilities.
- At20bps/side: tactical CAGR8.56% vs SPY18.01%, tactical MDD12.65%, modeled cost$4,457.82.
- **ALLOCATION_SCREEN=false in both cases.** It earned beta-related money but did not pass the claimed alpha/risk objective.

Do not infer that every TAA algorithm is disproven. This is one fixed rule/window, not the July multi-asset strategy, and no alternative parameters were searched.

## Holding-horizon simulations actually executed

1,000joint circular block paths per scenario, seed20261115;21/60/120session blocks;21/63/252/756session horizons. Contemporary regular account/SPY/SGOV returns resampled together; initial/terminal fees removed from the sampling pool and applied **once at each path's endpoints**. See [independent review and correction](./11_INDEPENDENT_REVIEW_AND_CORRECTIONS.md).

**Strong warning:** these are conditional scenario frequencies fitted to a favorable, already-observed2022-2026window. They are **not estimates of future success**, real-return probabilities or formal ruin guarantees. Longer synthetic paths recycle the same observations. No additional independent evidence is created.

| Horizon | FXAIX: conditional positive-wealth fraction across blocks | Tactical: conditional positive fraction | Tactical: fraction beating SPY |
|---|---:|---:|---:|
|21sessions |70.4% |68.1% |4.2% |
|63sessions |74.0-80.6% |65.9-69.2% |6.7-11.6% |
|252sessions |88.8-94.8% |78.9-82.0% |8.1-17.9% |
|756sessions |97.9-99.3% |92.3-94.2% |2.7-6.1% |

Even that optimistic fitted model produces losing paths. Maximum across block cases of simulated95th-percentile three-year MDD: FXAIX25.37%, tactical22.65%. Synthetic risk can exceed the one realized path.

The monthly policy is **not recomputed on synthetic prices**: simulations resample its historically realized net-return process. A state-dependent synthetic-policy backtest would be a separately preregistered experiment.

Joint60/30/10shock arithmetic remains-24% and-36%; it is not simulated execution of the100%SPY/SGOV rule or a recommended allocation.

## Reproducibility and exact validation

From this directory:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s . -p test_simulation_runner.py -v
PYTHONDONTWRITEBYTECODE=1 python3 simulation_runner.py run --input market_prices.csv --output simulation_results.json
```

Actual result: **13tests passed; both cost cases ALLOCATION_SCREEN=false, capital_eligible=false.**

Runner rejects wrong/missing/nonpositive/nonfinite prices, duplicate dates, mismatched calendars and overweight targets. Tests cover next-close lag, future-price causality, partial final months, drift, costs funded from account, real concurrent account returns and identical paired-bootstrap controls.

Independent closed-form passive check:

`final_NAV =100000 * adjusted_end/adjusted_start *(1-rate)/(1+rate)`.

All14full-history cost/instrument outcomes matched within1e-12relative tolerance. All28,120rows/24books reconcile cash+positions, cost sums and final liquidation. The boundary-cost correction left the realized NAV file byte-identical. [SIMULATION_QA.json](./SIMULATION_QA.json) records hashes/checks; [market source manifest](./market_prices.sources.json) hashes original feeds.

Outputs: [results JSON](./simulation_results.json), [full daily NAV](./simulation_results_nav.csv), [frozen adjusted/raw prices](./market_prices.csv).

**Limitations:** one vendor and known survivor funds; only five years; no independent distributions/PIT/access/real-fill audit; tax/FX/platform costs excluded; early signal history may not span prior crises; return annualization includes an initial transaction-cost-only observation. Existing trade-level harness/gates were not altered or falsely passed.
