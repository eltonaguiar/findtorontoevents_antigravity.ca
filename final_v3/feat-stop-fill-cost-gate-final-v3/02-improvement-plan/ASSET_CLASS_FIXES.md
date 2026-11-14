# Asset-class-specific fixes and gates

Current performance numbers are not directly comparable across files until `cohort_id`, filters, and time windows are aligned. The focus below is a research order, not a profitability claim.

## EQUITY - first research track

- [ ] Complete total-return and survivorship-safe source data: dividends, splits, delisted names, point-in-time fundamentals, and exact timestamps.
- [ ] Test a diversified cross-sectional momentum/value/quality/low-vol portfolio on a monthly clock; do not substitute a single-name scout or index RSI test.
- [ ] Compare net results to a risk-matched, dividend-adjusted benchmark over identical dates. Report beta, drawdown, turnover, factor exposures, and benchmark excess.
- [ ] Use time-ordered train/validation/test windows; no feature selection or factor tuning on the final holdout.
- [ ] Gate research promotion on the pre-registered criteria in `../03-focus/FOCUS_DECISION.md`, not on an in-sample PF.

**Why:** one peer's closed-pick slice reports a positive cost margin, but official verdict/registry snapshots disagree and peer review raises beta and recency concerns. Equity is the best first experiment because valid benchmark data and low-capital diversified exposures are comparatively accessible, not because current alpha is established.

## CRYPTO - second, conditional research track

- [ ] Reconcile spot, futures, and strategy cohorts; remove replay/synthetic observations from any forward result.
- [ ] Audit `kimi_riseoftheclaw`'s exit writer and resolver version; do not assume the shared resolver fixed rows written elsewhere.
- [ ] Record stop/target price, actual exit timestamp, bar source, gap-through, spread, slippage, funding, and venue costs. Reject unmeasured fills from proof-grade metrics.
- [ ] Evaluate trend and funding carry as separate pre-registered tests. Compare to BTC/equal-weight spot and a cash benchmark, and adjust carry results for margin/collateral and liquidation risk.
- [ ] Require a bear-inclusive holdout and sufficient independent post-fix observations; do not promote the POSITION n=33 or crypto carry n=10 anecdotes.

**Why:** the stop-fill problem is plausible and material, but a fill correction can move loss toward breakeven without creating a predictive edge. Mega-mutation and Variant C claims remain unverified.

## ETF

- [ ] First resolve cohort and total-return inconsistencies.
- [ ] Do not treat ETF picks as distinct from equity exposure if the universe overlaps. Test daily/monthly allocation only when the strategy can overcome measured costs.
- [ ] Record expense ratios, spreads, commissions, distributions, and turnover; reject an intraday claim whose expected move is below realized costs.

## FOREX

- [ ] Enforce spot-FX symbol allowlist; route currency ETFs to ETF and crypto pairs out of FOREX.
- [ ] Reject date-only/unparseable timestamps for intraday evaluation.
- [ ] Use a currency-appropriate benchmark and point-in-time FX data. Do not use SPY as a generic comparator for FX returns.
- [ ] Defer signal optimization until taxonomy, prices, and costs are fixed.

## FUTURES and COMMODITY

- [ ] Quarantine crypto proxies that have been labeled as commodities.
- [ ] Obtain a licensed, roll-adjusted continuous-contract feed with actual contract multipliers, roll dates, margins, and realistic costs.
- [ ] Trace one candidate through emitter, resolver, and ledger before enabling a readiness class.
- [ ] Treat COT contrarian as failed unless the OOS selection boundary is verified; any alternate threshold chosen after seeing OOS is a new registered trial.

## BOND

- [ ] Use total-return bond data and a defined duration/curve benchmark; do not infer price from entry or use a stale quote.
- [ ] Keep class status `INSUFFICIENT_DATA` until the sample and source-quality gates pass.
- [ ] Treat a monthly duration/carry allocation as a portfolio sleeve, not an intraday TP/SL pick.

## MUTUAL FUNDS

- [ ] Keep the prediction-class state as `NOT_BUILT`; current NAV caches do not establish an active validated emitter.
- [ ] If useful, maintain a separate passive monthly benchmark/allocation sleeve with NAV provenance, fees, and next-NAV execution semantics.
- [ ] Use point-in-time survivorship-free universe and category benchmarks before claiming a fund-selection edge.

