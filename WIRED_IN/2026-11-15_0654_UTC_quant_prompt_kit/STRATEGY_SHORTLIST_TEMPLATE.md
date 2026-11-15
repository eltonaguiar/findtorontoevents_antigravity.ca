# Strategy shortlist template

> Template only: no numbers or profitability verdicts are implied.
> Repeat the candidate section for each strategy and compare to no-trade/cash
> and relevant implementable passive alternatives. Past performance and even
> a successful forward test do not guarantee future results.

## Summary

| Rank | Candidate / class | Verdict | Data / independent test | Net result vs benchmark / uncertainty | Main blocker / next step |
|---:|---|---|---|---|---|
| [n] | [name] | [REJECT / INCONCLUSIVE / RESEARCH CANDIDATE / FORWARD-SUPPORTED] | [value] | [value or N/A] | [value] |

Use FORWARD-SUPPORTED only after a genuinely prospective, frozen protocol
passes its prespecified economic and statistical criteria. A backtest-only
result cannot qualify. If no candidate qualifies, say so explicitly.

## Candidate: [name and version]

### Hypothesis and implementation

- Economic rationale and source / prior attempts: [value, citations]
- Instruments, point-in-time universe, location/venue and benchmark: [value]
- Signal information cutoff, entry trigger and first executable fill: [value]
- Holding horizon and exit rules, TP/SL or rationale for none: [value]
- Parameter values, permitted ranges and selection procedure: [value]
- Sizing, exposure, leverage, liquidity and concentration limits: [value]
- Portfolio accounting, overlapping positions and cash treatment: [value]
- Frictions, FX, fund expenses, tax/account assumptions and stress: [value]
- Data range, source/version/hash, timestamps, missingness and limitations: [value]
- Registration timestamp, hypothesis ID, frozen plan and seed: [value / none]

### Experiment and validity

| Test | Design / period / sample | Statistic and threshold fixed before testing | Result and uncertainty | Pass / fail / inconclusive | Evidence |
|---|---|---|---|---|---|
| Training / selection | [value] | [value] | [value] | [status] | [path] |
| Nested walk-forward folds | [value] | [value] | [value] | [status] | [path] |
| Untouched holdout | [value] | [value] | [value] | [status] | [path] |
| Benchmark and dependence-aware interval | [value] | [value] | [value] | [status] | [path] |
| Multiple trials / selection correction | [known and unknown trials] | [method and assumptions] | [value] | [status] | [path] |
| Negative/null and implementation controls | [value] | [value] | [value] | [status] | [path] |
| Costs, parameter and regime stress | [value] | [value] | [value] | [status] | [path] |
| Frozen prospective paper test | [dates and n] | [economic/statistical gate] | [value] | [status] | [path] |

### Metrics

| Metric | Gross | Net | Benchmark / difference | Interval, definition, caveat |
|---|---:|---:|---:|---|
| Annualized return / CAGR | [value] | [value] | [value] | [value] |
| Volatility / Sharpe / Sortino / Calmar | [value] | [value] | [value] | [risk-free, frequency] |
| Maximum drawdown / duration | [value] | [value] | [value] | [value] |
| Turnover / exposure / capacity | [value] | [value] | [value] | [value] |
| Trades / win rate / CI | [value] | [value] | [value] | [value] |
| Expectancy / payoff / profit factor | [value] | [value] | [value] | [value] |
| Breakeven cost / margin | [value] | [value] | [value] | [value] |

Report additional distribution and benchmark-dependent metrics if meaningful;
mark N/A when mathematically undefined or data is missing. Cite outputs.

### Verdict and next decision

- Verdict and precise evidence supporting it: [value]
- Confounders, contradictions, known unknowns and risk of ruin: [value]
- Live-parity and paper-forward requirements: [value]
- Reproduction command, inputs, output artifact, exit status: [value / blocker]
- Responsible reviewer and next checkpoint: [value]
