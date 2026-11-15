# Justification, actual evidence and elimination decisions

## What was actually done

This extension documents existing work; it does not claim new simulations, new live quotes or a rerun of all 23 older hypotheses.

- Historical/source review: all 24 mapped money-maker documents, the full 1,695-line strategy catalogue, four money-maker skills and independent focused reviews.
- Two successful SubQ Decisions API calls, eight abstract questions each; primary-source and arithmetic checks were done independently. AI scores are not future investment probabilities.
- Seven retained public market histories; two fixed cost cases, 24 funded account curves, 28,120 NAV rows.
- H-142/H-143 committed to the canonical registry before the simulation. Subsequent independent review corrected one-time fees in resampled paths without changing the strategy or realized NAV.
- 13 focused tests passed; passive terminal wealth also matched an independent closed-form calculation.

Full source/evidence: [executed results](../../2026-11-15_AM_profitability-plan/copilot-financial-review/09_EXECUTED_SIMULATIONS.md), [QA hashes](../../2026-11-15_AM_profitability-plan/copilot-financial-review/SIMULATION_QA.json), [SubQ review](../../2026-11-15_AM_profitability-plan/copilot-financial-review/06_SUBQ_FACT_CHECK.md).

### Reproducibility pins

- Existing evidence package publication: commit `5f1ead568000c214eb886f27d1c2608d2a80f2d7`.
- Registry/source reviewed for this extension: commit `ba39e564090f292c631950afa2da956ab36ea905`; [H-140/H-141 and owned H-142/H-143 records](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/ba39e564090f292c631950afa2da956ab36ea905/reports/hypothesis_registry.json).
- Runner SHA-256: `c4caaf715539cdfc5c70ffd0b9da4c521d74316b01d29d15d2388b1c76b9cba8`.
- Results SHA-256: `15aafe71d12eadfad0d5a6407fcc52f44996c67a13a54e2d803d4db22c60b8ef`.
- Canonical H-142/H-143 remain `UNTESTED`, capital false; research labels distinguish positive baseline from failed tactical alpha.

## Fund/ETF historical comparison

**2021-11-15 through 2026-11-13**, 5 bps per dollar traded each side, reinvested distributions implicit in adjusted NAV, expenses embedded. Values are modeled net of that transaction allowance, not all investor taxes/platform/FX costs.

| Fixed holding | Net total return | Calendar CAGR | MDD loss | Excess Sharpe vs SGOV |
|---|---:|---:|---:|---:|
| FXAIX | 73.05% | 11.61% | 24.50% | 0.506 |
| FZROX | 66.00% | 10.68% | 25.12% | 0.449 |
| VTSAX | 64.35% | 10.46% | 25.36% | 0.438 |
| SPY | 72.38% | 11.52% | 24.50% | 0.498 |
| VTI | 64.39% | 10.47% | 25.36% | 0.438 |
| BND | -1.51% | -0.30% | 17.31% | -0.648 |
| SGOV | 20.86% | 3.87% | 0.06% | N/A |

**Why retain fund/ETF reference accounts:** transparent market exposure, low turnover, comparable clocks and a demonstrated positive historical baseline. These results do not identify the best fund population, prove an active fund selector or guarantee future profitability.

FXAIX's approximately 0.09 percentage-point CAGR advantage over SPY is small and consistent with fee/tracking differences. Do not label it predictive alpha or equate SPY ETF performance with a fee-free index. The broad equity exposures are correlated wrappers, not independent winning asset classes.

A 25% equity-fund drawdown violates a 20% loss mandate despite profitable ending wealth. Short Treasury exposure can have lower short-horizon nominal risk, but carries its own fund/interest/inflation/currency risks. No personal allocation or universal "lowest-risk winner" ranking is made.

## Why the tested tactical algorithm was eliminated

**H-143, 2022-09-01 through 2026-11-13**, after warmup and next-close execution:

| Evidence | Fixed trend | Same-window SPY |
|---|---:|---:|
| Net CAGR, 5 bps/side | 9.34% | 18.09% |
| Net total return | 45.50% | 101.05% |
| MDD | 11.86% | 18.76% |
| Cash-relative Sharpe | 0.438 | 0.845 |
| Net CAGR, 20 bps/side | 8.56% | 18.01% |

It earned money but lost about 8.75 percentage points/year to SPY at the base cost. Its smaller drawdown was insufficient: the ex-post exposure control had Sharpe 0.843 versus 0.438. Both fixed chronological segments had negative SPY mean excess; every paired block lower bound was negative.

**Decision:** remove that exact algorithm from our alpha-forward queue now. Do not force capital risk, wait years hoping for a pass, tune the same data or blacklist all ETF strategies. This is a research rejection, not a production configuration change.

## Why the others are not selected

| Class/family | Evidence supporting the decision | Decision scope |
|---|---|---|
| Annual survivor fund selector H-141 | Existing registry reports all nine frozen variants failed selection/paired-excess screens; survival/eligibility issues remain | Do not retune/rebrand that family; not a fresh rerun here and not proof all active fund selection is impossible |
| Price-only equity factors | Prior registry H-140 beta-neutral low-vol test reported loss; related historical factor failures are not a mandate for more renamed variants | Require a genuinely new PIT information premise; SPEC-EQ-PIT-01 is untested, not a winner |
| Bond prediction | Sparse, cohort-dependent source evidence; BND passive history itself was negative; yields are not fill prices | No prediction admission; SGOV/BND references do not certify dashboard BOND algorithms |
| Commodity/futures | Contract/roll/cost accounting, small effective samples and concentrated historical markets remain unresolved | Deferred, not universally disproved; fixed individual-contract data required |
| Forex | Poor dated published cohort and unresolved unit/quote/funding contracts | Measurement-first/abstain; use mutation-before-retirement, not blind direction flips |
| Crypto | Raw recent improvement was duplicate-flagged and concentrated; fill repairs do not prove entry alpha | Investigate a frozen cleanable cohort; no admission from a 48-hour PF alone |
| Meme/penny subsets | Insufficient liquidity/history/effective samples and instrument-specific risks | Deferred; no claim every strategy was tested or permanently killed |
| Options | Some named paths emit underlying crypto signals, not contracts with premium/expiry/hedge ledgers | No options PnL/admission inferred from an underlying signal |
| Prediction-market copying | Scheduled paths map venue information to underlying USDT signals; token-specific sidecar is separate dry-run; leader/follower fills often unestablished | Diagnose the exact product/lifecycle first; cannot attribute this repo's failure solely to unverified bot statistics |

These are **not interchangeable outcomes**: a failed tested strategy, incomplete measurement, untested implementation and deferred research must remain separate. Current documentation changes no production kill list.

Historical market/class statistics retain their dated cohorts. The November 15 00:05 snapshot had no money-ready classes; this is not a claim to have re-queried every database at the request timestamp. See [the full current-at-review tables and limitations](../../2026-11-15_AM_profitability-plan/copilot-financial-review/PROFITABILITY_FRAMEWORK.md).

## Probability and institutional trust

There is no calibrated future-success percentage here. Historical bootstrap-positive fractions, selected rolling returns, SubQ scores and trade WR do not mean "win again and again." A longer fund hold can still lose money or fail cash/inflation/SPY.

Historical simulated paths remain conditional on one favorable known window. They are not new independent forward evidence. The fixed joint 60/30/10 shocks produced -24% and -36%; they are illustrative, not recommended weights.

The [institutional report](../../2026-11-15_AM_profitability-plan/copilot-financial-review/05_CONTESTS_AND_INSTITUTIONAL_TRUST.md) documents verified AQR research, BlackRock's integrated risk/operations and CFA/GIPS performance principles. It does not invent a verified causal Renaissance/Two Sigma turnaround or equate business revenue, trust and investment alpha.

Contest account success and Hoffman/TradingView fame do not substitute for exact rules, full loss histories, costs and independent forward replication. Unsupported contest/statistical claims stay unverified.
