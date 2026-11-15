# Audit report template

> Template only. Replace bracketed fields with cited evidence; use `unknown`
> or `not tested` rather than guessing. A discovered path is not a reviewed
> file. Do not treat this template as an audit or investment recommendation.

## Executive decision

- As-of timestamp and repository commit/worktree state: [value]
- Scope and definitions of asset class, timeframe and performance: [value]
- Data integrity blockers and affected conclusions: [value]
- Most promising hypotheses and passive comparison: [value / none]
- Findings that are inconclusive or contradicted: [value]
- Next independent experiment and decision date: [value]

## Coverage and provenance

| Corpus/source | Discovery method and snapshot | Discovered | Read/assessed | Exclusions / missing | Evidence |
|---|---|---:|---:|---|---|
| [path, glob, live URL or DB table] | [command / timestamp] | [n] | [n] | [reason] | [path:line / artifact] |

Data: [source, version/hash, extraction date, timezone, price type, range,
coverage, survivorship and point-in-time limitations]. Describe secret-safe
access and any permissions barriers. Cite per-class denominators and cohorts.

## Strategy inventory

| Strategy / version | Asset class / instruments | Frequency / holding | Entry and exit / TP-SL | Sizing / costs | Status: proposed, implemented, tested, live | Observed result / sample / dates | Source / evidence |
|---|---|---|---|---|---|---|---|
| [name] | [value] | [value] | [value] | [value] | [status] | [value or unknown] | [path:line] |

## Method inventory

| Method / model / risk control | Where | Actual role / status | Evidence of test and outcome | Gap or uncertainty |
|---|---|---|---|---|
| [method] | [path:line] | [proposal / code / live / tested] | [artifact or unknown] | [value] |

Include statistical tests, validation, cost and sizing functions, mathematical
models and ML. Group equivalent variants but preserve traceable identifiers.

## Pick and ledger reconciliation

- Path from signal through filters, ledger, resolver and dashboard: [citations]
- Observation timestamps and cohorts; active/closed/unresolved counts: [value]
- Duplicates, missing outcomes, timestamp/price discrepancies and effect: [value]
- Corporate actions, execution timing, same-bar TP/SL and costs: [value]
- Backtest/live differences; reproducible examples and limits: [value]

## Failure taxonomy

| Strategy / cohort | Failure mode | Verified / plausible / unknown | Evidence and contradictory evidence | Severity / impact | Follow-up |
|---|---|---|---|---|---|
| [name] | [leakage / data snooping / survivorship / costs / regime / implementation / power / sizing / other] | [status] | [path:line, artifact] | [value] | [value] |

## Experiment and selection ledger

| Trial family | Variants / parameters | Known trial count | Date and data observed | Registry / artifact | Missing search history / adjustment limits |
|---|---|---:|---|---|---|
| [family] | [range] | [n or unknown] | [value] | [path] | [value] |

## Evidence quality and next actions

| Action | Rationale / exact affected data | Priority | Reproducer or prerequisite | Success/failure criteria |
|---|---|---|---|---|
| [action] | [citation] | [value] | [command / blocker] | [value] |

List unreviewed files, unvalidated claims, blocked tests and what would change
the decision. Link the separately completed strategy shortlist and forward
protocol. Do not use absolute certainty as a promotion criterion or claim.
