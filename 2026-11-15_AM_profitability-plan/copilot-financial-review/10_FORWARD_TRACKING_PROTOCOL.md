# Easy forward tracking and fast elimination protocol

## Start with an honest queue

| Experiment | Current decision | Forward action |
|---|---|---|
| H-142 fixed passive fund/ETF baseline | Positive historical modeled beta, not predictive alpha;25%drawdown risk | Optional paper reference accounts for FXAIX and SPY, separately funded, no timing; no real orders |
| H-143 fixed10-month trend | Failed SPY and exposure-risk screen in both cost cases | **Remove from alpha-forward queue now**; preserve records. Do not wait months hoping it passes or retune into a new "winner" |
| Any new algorithm/class | Unestablished | Preregister its exact lifecycle/benchmarks/holding clock before paper admission |

No forward position has been entered by this deliverable. Earliest new paper decision must precede its eligible future fill; past November13close cannot be retroactively declared a forward entry.

## The four small files

Use one immutable experiment manifest and the three empty CSV templates supplied:

- [forward_decisions.csv](./forward_decisions.csv): timestamped information/decision, frozen version, target and intended expiry.
- [forward_fills.csv](./forward_fills.csv): actual observed reference, modeled fill, quantity, fees, execution status and reason if unfilled.
- [forward_daily_nav.csv](./forward_daily_nav.csv): cash, all marked holdings, flows, NAV, benchmarks, source/as-of and anomalies.

Each experiment has its own paper capital. Do not add two independent100kpaper books as if they were one allocated account. Keep immutable append-only copies/hashes; corrections reference prior row IDs, not overwrites.

### One-time, about20minutes

1. Copy a single strategy's frozen spec, hypothesis/family ID, spec/data hashes and approval status. Record currency, starting paper cash, mandate, risk limits, source and cost assumptions.
2. Freeze independent cash, same-asset buyhold and SPY total-return reference accounts with the same start date/flows. Include risk-matched baseline if claiming risk improvement.
3. Define decision availability, first executable fill, NAV/quote publication/cutoff, registered holding horizon and calendar. No real account/API access.
4. Set evaluation dates before any forward return is read. Fill rejection, outages, zero/unknown treatment and end-of-test rules must be explicit.
5. Register a genuine forward start. Current fund metadata/access and quote/adjustment checks remain required; an empty CSV is not tracking evidence.

### Daily, about5minutes after the correct market/NAV publication

1. Append decision **before** observing any subsequent price used for fill. If none, record no-change; do not invent a new trade daily.
2. Append modeled paper fills only from eligible post-decision market/NAV observations. Capture reference price/time/source; never silently choose a favorable candle.
3. Mark all holdings and cash. Include distributions, fees, financing and external flows exactly once; actual distributions are cashflows, not manually double-counted adjusted prices.
4. Calculate `NAV=cash+sum(quantity*mark)-liabilities`; reconcile prior NAV, trades/flows and changes. Benchmarks use the identical clock/currency/cost scope.
5. Flag blanks,0.00%, missing prices, stale marks and anomalous movement with validation states. Unknown does not become zero or a terminal winner.

An open exit price is not applicable, not a missing-required-field fault. A terminal missing exit/time/quantity is critical. For a weekend/holiday, retain the latest observation **with its real as-of**, not a fabricated fresh timestamp.

### Weekly, about10minutes

Check coverage, unexplained NAV/cost/position differences, quote/cutoff compliance, overlapping exposures, concentration, outages and missing terminal records. Publish loss/open-NAV/cost and benchmark panels together. Only inspect edge at the planned evaluation dates.

## Fast versus slow decisions

| What happened | How fast | Decision |
|---|---|---|
| Lookahead, impossible fill, absent provenance, wrong instrument/payoff, broken NAV or required blank | Immediately | **INTEGRITY_BLOCKED**. Halt new simulated fills; retain and mark existing exposure. Fix measurement, not history |
| Deterministic costs/eligibility/margin make the proposed trade unexecutable | Immediately | Reject that execution design; separate source/data remediation from retiring the entire economic family |
| Frozen backtest/benchmark gate failed, as H-143 did | Before forward entry | **REJECT_BACKTEST** for the stated alpha objective; keep immutable failure and no parameter rescue |
| Predeclared account drawdown/exposure/operational stop breached | Every valid mark, including open trades | Halt paper risk per approved stop; actual gaps/unknown marks remain visible. A risk stop is not an inference of universal no-edge |
| First loss,1bad day or temporary underperformance | Not sufficient | Do not declare strategy death or profit; follow frozen lifecycle |
| Unresolved open trades have not reached registered exit horizon | Keep correct marks daily | **PENDING_HORIZON**; do not score hypothetical terminal wins or force early closes to create sample |
| Adequately powered prespecified independent forward test fails | Planned checkpoints | Demote/reject on the frozen economic/benchmark criteria; no deletion/reset |
| Sufficient evidence appears favorable | Planned checkpoints | **REVIEWABLE**, not automatically money-ready; independent validation and existing gates still required |

## Checkpoints by style

These are observation/review cadences, **not universal sample sufficiency thresholds**:

| Style | Earliest useful operational review | Economic observation | Why not close everything early |
|---|---|---|---|
| Scalp/day |1-3sessions for quote/latency/cost/fill realism | Scheduled20/60/120sessions; many same-day trades are correlated | Costs/data failures can eliminate quickly, but small gross gains do not establish repeatability |
| Swing2-20sessions |First week plus first completed lifecycle | Fixed6/12/24week checkpoints, with actual independent resolved episodes | Must respect held horizons; retain unrealized NAV/risk daily |
| Position/monthly ETF |First decision/fill cycle |3/6/12months and longer if power inadequate | Monthly rebalances/daily marks do not become independent trades |
| Long-term fund allocation |First cutoff/NAV/distribution reconciliation | Quarterly operations,6/12month risk review; multi-year economic horizon | One falling quarter cannot falsify a multi-year beta mandate, but risk budgets still apply daily |
| Event contracts |First executable public quote/rules check | After independently resolved event clusters and frozen cohort window | Contract settlement/void rules determine terminal PnL; BTC movement is not event settlement |

Never wait years to reject a demonstrably flawed **alpha** simulation. Conversely, do not abandon a correctly modeled long-horizon **beta** reference because a few weeks lose money. Match the decision to the objective and horizon.

## Avoid premature statistical elimination

Use one family-wide trial/checkpoint ledger across machines. If statistical early stopping is desired, preregister a validated dependence-aware sequential design and family-wide error budget; do not repeatedly peek at a95%CI or use IID trade tests.

At an approved checkpoint, a reliably negative net-excess upper bound or futility/power result can support early rejection. A negative point estimate or an unpowered interval does not. Missing effectiveN means **INSUFFICIENT**, not a pass. Protocol/market-regime changes require a new version and trial record, not replacement of the old results.

Actual rules in the charter/registry/harness remain enforced; this easy protocol does not override them. Keep raw outcomes, open exposures and failed experiments accessible to an independent reviewer.
