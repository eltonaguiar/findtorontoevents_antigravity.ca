# Benchmarks, professional metrics and admission QA

## One account, several success questions

Use synchronized total-return NAV curves in the same currency, with identical start/end dates, contributions, executable decision times and financing assumptions.

| Question | Required output | What does not establish it |
|---|---|---|
| Absolute profit | Positive realized/unrealized account return after costs; TWR and cashflow-aware MWR/XIRR | Winning picks with losing/open exposure omitted |
| Positive real return | Inflation-adjusted account return for the stated currency/horizon | Nominal gain or a long holding period |
| Beat cash | Net excess return over an investable, funded cash alternative | Comparing leveraged gross profits with unfunded cash |
| Beat passive | Same-underlying/universe total-return buy-and-hold comparison | Beating a different asset or omitting dividends |
| Beat S&P 500 | Matched SPY total-return excess, tracking error and Information Ratio | Price-only S&P, shorter dates or high WR |
| Risk-adjusted improvement | Matched exposure/volatility baseline, excess Sharpe/Sortino/Calmar, regression exposures and stress | Merely reducing equity weight or drawdown |
| Repeatability | Frozen, sequential independent forward periods with uncertainty and full losses | Retuned walk-forwards, overlapping picks, account resets |

Example: strategy +15%, SPY +18%, strategy drawdown10%, SPY25%. The strategy made money and **failed raw SPY outperformance**. It might improve a risk objective, but needs a SPY/cash risk-matched control. Lower drawdown alone does not prove factor-adjusted alpha.

## Calculation contract

- Daily account equity = cash + marked holdings - liabilities, with external flows treated explicitly.
- Return intervals come from that account, not from multiplying every overlapping trade as if it used100%capital.
- CAGR uses calendar time; annualized Sharpe uses correctly sampled excess returns, same-date cash and disclosed annualization. Use dependence-aware uncertainty, including autocorrelation/overlapping holds.
- PF/expectancy use fully costed economic outcomes; report undefined PF rather than infinity-as-certification when no losses occurred.
- Information Ratio uses benchmark-relative returns and tracking error. IC requires a defined predictor/target universe and horizon; it is not interchangeable with WR.
- Sortino states minimum acceptable return/downside denominator; Calmar states return/drawdown window. VaR/ES state confidence, horizon, estimator, sample/tail support and loss sign.
- Aggregate NAV and risk by look-through holdings, not symbol count. Stress correlations, gaps and liquidity jointly.

## Proposed evaluation bars, not replacement production policy

Existing charter/class-specific gates remain in force. Their sample/PF/WR requirements differ from previous plans; an approved versioned policy migration is needed before changing them.

For research prioritization, use **net positive expectancy and PF>=1.15** as a weak screening floor, not capital proof. Existing Tier2 goals (PF>1.5, WR>50%, MDD<20%) are more demanding and still do not establish benchmark-relative alpha. Some economically valid trend systems have WR<50%; this is a reason to review the mandate explicitly, not bypass it.

Potential forward-review targets: net excess Sharpe>=0.8, benchmark IR>=0.3, risk-budget compliance and a positive dependence-aware benchmark-excess confidence bound after cumulative trial adjustment. These are proposed design bars, not universally accepted industry standards, observed results, or automatically sufficient conditions. Freeze the appropriate objective and bar before testing; do not switch objectives after seeing results.

- Raw n>=100/500 alone is insufficient; justify effective sample and power for the minimum useful effect.200 correlated daily observations are not200 independent trades.
- Monthly fund allocations need calendar time/regime coverage, not manufactured trade counts.6-12months establishes observation, not necessarily adequate power.
- Assess clustered/bootstrap uncertainty, DSR/multiple trials and robustness against the complete attempted family. Confidence bounds measure estimator uncertainty; they are not a future success guarantee.
- Stress prespecified high costs and latency, historically credible gaps/correlations and liquidity constraints. A failure under a realistic stress invalidates the candidate's stated capacity/risk mandate.
- Missing evidence, unresolved critical anomalies and an unreconciled NAV are **admission blockers**. Unknown is neither a zero return nor a harmless successful test.

## Different professional perspectives

| Perspective | Required questions/metrics | Practical control |
|---|---|---|
| Professional allocator | Net excess Sharpe with uncertainty, drawdown/recovery, correlation, capacity, concentration and credible economic rationale | Compare to an investable opportunity set; independent verification and a clear loss budget |
| Mutual-fund manager | Category/mandate total-return benchmark, net alpha/IR, tracking error, fees, turnover/tax and PIT shareholder liquidity | Correct share-class NAV/distributions, custody/accounting, no misrepresented passive beta |
| Bank/prop trader | Intraday/daily PnL, risk sensitivities, liquidity/margin, execution shortfall, VaR/ES and limit breaches | Independent risk desk, transaction/position reconciliation, scenario limits and kill-switch tests |
| Risk manager | ES/tail support, joint stresses, drawdown duration, leverage/counterparty exposure, model/replay divergence | Risk limits can reduce exposure; they cannot create expectancy or guarantee fills |
| Quant/model validator | Availability/label integrity, IC/calibration, family-wide trial count, dependence/effectiveN, instability and negative controls | Independent reproduction, frozen holdout, failure ledger and model retirement criteria |
| User/auditor | What exactly was executed? What is missing? What costs/taxes are excluded? Which benchmark did it beat? | Timestamped source evidence, complete open/closed ledger and explicit permission state |

No responsible universal "good mutual-fund Sharpe=1" or "S&P Sharpe=0.5" can be asserted without specifying currency, sample, cash proxy, costs and annualization.

## Applied risk results already computed

Retained market histories, same window2021-11-15 through2026-11-13, show FXAIX CAGR11.63%, volatility17.17%, drawdown24.50%; SPY11.54%,17.33%,24.50%; BND CAGR-0.28%, drawdown17.31%. These are one-vendor passive descriptive histories, **not all-in net strategies**. Source hashes, annualization and all seven curves are in [the framework](./PROFITABILITY_FRAMEWORK.md) and [risk evidence](./framework-passive-risk-verified.json).

A hypothetical60%stocks/30%bonds/10%cash shock with stocks-35%, bonds-10% produces-24%. A-50%/-20%case produces-36%. Stops, quarter-Kelly and low fees do not cap gap losses; no portfolio weights are recommended.

Prospective profitability probability is **not identifiable here**. SubQ scores, bootstrap-positive fractions, trade hit rates and selected historical rolling frequencies are not calibrated probabilities of future account profit.

## Exact measurement/release QA

Reuse [the detailed QA plan](./QA_PLAN.md). Specifically:

1. Audit **all** OPEN and recent terminal rows at a frozen watermark; paginate, reconcile counts and preserve exclusions. Validate nonzero/NULL/zero equally.
2. Instrument, currency, direction, quantity, entry/available/fill times, current-as-of and terminal exit/cost fields must be typed and explicit. An open exit is not applicable; an absent closed exit is a critical unknown.
3. Recompute long return as `(exit-entry)/entry`, short as `(entry-exit)/entry` only for the appropriate unlevered price instrument; then incorporate quantity/account capital and costs. Futures, options, binary contracts and financing need their own payoff ledger.
4. A0.00%value can be genuinely flat, precision-rounded, unresolved or corrupted. Require timestamped entry/current-or-exit reference data; age<=15min is not market verification.
5. Compare to the **same open-to-close/open-to-current period**. Daily close is not an intraday fill. OHLC bounds cannot identify which stop/target filled first; mark ambiguity instead of fabricating.
6. Flag stale opens relative to their registered horizon, calendars and publication schedule. A legitimate long-term fund hold should not be rejected merely for being>72h old.
7. Two equal-weight simultaneous+10%positions must yield portfolio+10%, not+21%. Include open losses, external flows, fees and missing legs.
8. Test NAV cutoff/late signals, corporate actions/distributions, inverted FX, futures roll/multiplier, options expiry, settlement/void, quote outages and unavailable history.
9. UI/payload and backend must agree on validation states, cohort, time, costs and permission. Show blocked/unknown explicitly; a green build must not manufacture money readiness.
10. Independently reproduce candidate/benchmark outputs, preserve failed tests and assert the exact production invocation/caller before any separately approved code integration.
