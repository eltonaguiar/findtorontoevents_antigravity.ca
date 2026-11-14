# Backtest and simulation plan

Every proposed strategy or algorithm fix needs an explicit test. Do not use these simulations to rewrite historical outcomes or to select a strategy on the final holdout.

## 1. Measurement and PnL normalization

- Build fixtures for fraction/percent units, long/short direction, missing price, invalid geometry, and expired status.
- Recompute PnL only when entry and exit are validated and unit/source are known; preserve raw values and record the calculation version.
- **Pass:** no 100x scale jumps, no `None -> 0`, and every excluded row appears in a reconciliation count.

## 2. Stop-fill and exit replay

- Replay bars from entry only through the recorded exit timestamp. Use OHLC rules that handle gaps and both TP/SL touched in the same bar; mark ambiguous paths as unknown rather than choosing the favorable fill.
- Compare recorded, stop-level, and gap-aware fills with venue fee, spread, slippage, and funding assumptions. The at-stop result is an upper bound, not a live result.
- Publish row IDs, bar source/coverage, missed bars, and per-source results; use an untouched holdout after implementation.
- **Pass:** unit tests cover gaps, missing opens, late polls, both-levels-touched, short positions, and actual-exit truncation; forward fills—not retrospective counterfactuals—confirm the improvement.

## 3. Cost gate

- Evaluate the cost rule on rolling windows where the threshold is estimated only from past data and tested on the next period. Include cost uncertainty and low-sample intervals.
- Compare the current 3x-cost selection with no gate and a cost-only baseline; do not score on the same rows used to choose the class.
- **Pass:** unknown/stale costs block promotion, and the gate improves net OOS performance without unacceptable coverage loss.

## 4. EQUITY factor portfolio

- Use point-in-time constituents/fundamentals, adjusted total returns, delisted names, monthly rebalance, turnover and market impact.
- Compare to a risk-matched broad index and factor-neutral benchmark over train, validation, and a single untouched test; include a bear market and multiple regimes.
- Pre-register factors, ranks, rebalance, costs, and sizing. Report turnover, sector/factor exposure, drawdown, bootstrap interval, and trial count.
- **Pass:** positive net benchmark excess with a predeclared confidence/stability criterion in both test subperiods; no post-hoc factor substitution.

## 5. CRYPTO trend and funding carry

- Keep trend and carry as distinct hypotheses and ledgers. Use timestamped spot/perpetual prices, funding cash flows, realistic venue/fee tiers, spread, slippage, leverage/margin, and liquidation rules.
- Compare to BTC and equal-weight buy-and-hold plus cash; test a bear-inclusive period and a locked holdout. Use block bootstrap for serial dependence.
- **Pass:** net excess and risk criteria hold across the declared universe and period; capital-adjusted carry beats a cash hurdle after margin and tail-risk assumptions.

## 6. COT and commodity direction

- Verify parameter selection uses only the first 60% before trusting the reported final-40% OOS result. Log the selected parameter, selection data hash, and exact cutoff.
- Do not choose the z>=2.0 cell because it had enough trades in the observed OOS set; register it as a new hypothesis with a future untouched period.
- Compare contrarian and momentum variants to an equal-risk commodity benchmark with roll-adjusted contracts and trading costs.
- **Pass:** OOS sample size and net benchmark-relative criteria pass without peeking or multiple-test leakage.

## 7. Mutual-fund trait selection and allocation

- Use the existing NAV caches only with a manifest: file hash, source, date span, fund/share class, distributions, expense ratio, minimum, load, and whether the fund later closed/merged.
- Use a point-in-time universe including unavailable/delisted funds; execute at next NAV, not same-day close. Compare against category and passive total-return benchmarks.
- Model actual account sizes, fractional availability, minimum initial purchase, contribution minimum, broker transaction fee, loads, 12b-1, and ER separately. Do not apply a flat $9.95 fee or whole-share rule to every fund.
- **Pass:** monthly walk-forward net of fees, no survivor-only peer median, and sufficient history; report capital, fee, and drawdown sensitivity.

## 8. Tactical rotation and generic strategy evaluation

- Use only information available at the rebalance decision time; execute at the next tradable NAV/close and test gaps, spreads, slippage, dividends, and turnover.
- Raise winner-hunt evidence beyond the current default `--min-n 10`; report confidence intervals, effective sample size, multiple testing, and benchmark-relative results.
- **Pass:** all model/feature selection is nested in training; the OOS set is evaluated once and is not reused to select a replacement.

## 9. Fix-level simulations before strategy mining

- COT selection boundary: verify train-only parameter choice.
- Mutual-fund feature calendar alignment: join by actual dates, not list position; test missing dates and holiday calendars.
- Fund peer comparison: keep funds with missing terminal NAV in the universe and classify why data is missing.
- Crypto verifier: cost sensitivity by venue/position size; zero-total PnL should return an explicit undefined concentration metric, not divide by zero.
- Cost-gate errors: simulate missing/stale index, exception, low sample, and unknown class at the real caller.
- **Stop condition:** do not expand the strategy search until measurement, freshness, and promotion gates pass.

