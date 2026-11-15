# Copy-paste prompts for parallel worktrees and machines

Use the **common contract plus exactly one bounded role** per agent. Coordinate on hypothesis IDs and files, not model names. Do not have several machines independently tune the same family and then pool only winners.

## Common contract: paste into every task

```text
Goal: find a genuinely executable, repeatably profitable AFTER-COST strategy,
or falsify it honestly. No promises, fabricated trades or live-capital authority.

Work in your own isolated worktree. Pin GitHub SHA, data hashes, dataset/event
cutoff and UTC run time. Read AGENTS.md, the relevant class source, current
money-maker skill and this package. Search prior rejected hypotheses first.
Do not run check_active_picks or smart_picks_engine unless explicitly authorized.
Do not run dashboard generators in shared checkouts. Do not touch peer files.

Before any strategy backtest: pre-register the exact universe, instrument,
holding horizon, rule/version, available-at features, execution/exit clock,
cost model, benchmarks, trial family, stopping rule and failure criteria.
Use the existing hypothesis registry workflow; inspect its CLI before use.
Never overwrite a shared registry file from an old checkout.

No current constituent/winner lookahead, synthetic fills, unknown-to-zero,
invented close times, whole-account compounding of overlapping trades or
exclusion of losing/expired/open exposures. Preserve raw anomalies.
Validate zero, NULL, nonzero and blank-field rows against independent prices
at actual entry/exit or frozen current-as-of. Missing provenance is UNKNOWN,
not a manufactured win or loss. OHLC is a reasonability bound, not fill proof.

Output a complete portfolio-NAV ledger: quantities, cash, outstanding positions,
fees, dividends/distributions, financing, rolls and FX. Report TWR and MWR
where flows exist. Compare the same dates/currency/funding/costs to:
1) investable cash, 2) same-universe buy-and-hold, 3) S&P500 TOTAL RETURN,
where relevant, and 4) an exposure/volatility-matched baseline.
Label ABSOLUTE_PROFIT, RETURN_OUTPERFORMANCE and RISK_ADJUSTED_IMPROVEMENT
separately. SPY outperformance is not automatically factor-adjusted alpha.

Use chronological/nested holdouts and dependence-preserving resampling.
Account for every attempted variant across machines. No resetting trial count.
Resampling existing data creates scenarios, not new independent observations.
Reserve genuine unseen forward data; do not tune against it.

Stress prespecified costs, lag, gaps, liquidity/participation, correlation and
provider outages with sufficient source resolution. State n_raw, n_measured,
n_effective, independent periods, data coverage and uncertainty.
Keep research, prediction confidence and financial admission separate.

Deliver: hypothesis record, exact reproducible commands/results, immutable
input/source hashes, full ledger/curve, benchmark curves, regime results,
negative controls, risk/uncertainty/cost table, source citations, limitations,
owned-file diff and an explicit REJECT / INSUFFICIENT / FORWARD_CANDIDATE.
No "proven" based on leaderboard, contest fame, helper imports or green CI.
Do not push any peer commit. Do not deploy or place orders. Ask for bounded
implementation approval before changing production behavior.
```

## Role A: measurement and event-time reconciliation

```text
Own only an approved validator/contract test scope. Audit uncapped OPEN and
recent terminal events from authoritative read-only sources, paginated at a
stable watermark. Preserve raw rows and all exclusions. Distinguish signal,
activation, fill, quote, close, resolver and publication times.

Prioritize TIME_EXIT with missing prices/times, genuine zero/rounded returns,
terminal statuses in active_raw, wrong units/instrument aliases and incomplete
open-NAV marks. Verify representative boundary cases using independently
timestamped market evidence. Never compare an intraday fill solely with that
day's close. Never run mutating legacy NAV diagnostics.

Produce all-row validation-state coverage and a schema consumed identically
by Python and browser. Tests must fail on missing provenance and demonstrate
a real flat can survive. Stop with evidence/patch proposal if historical data
cannot reconstruct the actual event; do not silently backfill.
```

## Role B: mutual-fund/ETF core and one TAA challenger

```text
First reproduce an after-cost passive total-return baseline. Then independently
implement ONE frozen, preregistered monthly rotation/absolute-momentum rule
using common point-in-time history. Do not start with a blend or tune16cells.

Check the current rotation/blend mismatch: negative momentum filtering,
missing history, weights+cash=1, overlapping component concentration,
6m versus mom_9m output and stale per-symbol dates. Reproduce the three existing
negative fixtures before interpreting any backtest.

Fund NAV signals observed after publication execute at a later eligible NAV;
ETFs require an executable post-signal quote/bar, spread and costs. Verify
share classes, distributions, fund access and redemption restrictions.
Bond ETFs are not cash. Compare SPY total return, same funds buy-and-hold,
risk-matched balanced allocation and cash, on identical dates.

Determine whether lower drawdown survives comparison with merely reducing
SPY exposure and holding cash. Show rolling/regime/forward uncertainty.
Existing July checkpoint success or empty committed report is not a track record.
Deliver FORWARD_CANDIDATE only after independent reproduction; no orders.
```

## Role C: diversified equity challenger

```text
Freeze one point-in-time value/quality OR momentum family, diversified by
sector/issuer, with filing-publication lags and delisted/historical-universe
coverage. No retrospective selection of NVDA/mega-cap winners.
Do not rerun the already rejected SPY test under a new name unless a documented
data/execution premise changed.

Compare SPY total return, the same universe equal-weight, sector/factor and
volatility-matched controls. Include dividends, actions, borrow if short,
turnover/capacity and realistic costs. Report benchmark-relative excess,
tracking error, Information Ratio and factor exposures, not only PF/WR.
If survivorship/PIT coverage is unavailable, label the experiment exploratory;
do not claim verified alpha. Separate long-term, position and swing families.
```

## Role D: bond, commodity and futures accounting/low-frequency research

```text
Choose ONE underlying family and exact contract/ETF universe. Model rates,
credit/duration, contract months, tick/multiplier, expiry/roll, collateral,
margin, financing and limit moves. Yield data are features, never fill prices.

Test one frozen diversified trend/term-structure or curve-allocation hypothesis,
not cotton/natural-gas concentrated episodes. Compare proper funded passive
exposure and managed-futures/risk-matched alternatives; show cash/SPY
opportunity cost separately. Respect COT publication timing.
If only continuous futures bars exist, do not manufacture executable returns.
Deliver accounting/data blockers before another indicator variant.
```

## Role E: crypto/forex conditional candidate

```text
Choose crypto OR forex, not both. First prove entry/fill/mark identity, units,
direction, fees/funding and dedup for the exact candidate cohort.
For crypto, investigate recent raw improvement without pretending12duplicate
groups or98.6%source share are independent corroboration. Do not promote a
corrected-stop counterfactual as entry alpha.

For forex, reconcile pair inversion, base currency, swaps, spread and sessions;
do not clamp corrupt PnL into plausibility.
Register one entry-condition family only after measurement clears. Compare
same-asset buy-hold, direction/duration-matched random entries, collateral cash
and risk-normalized opportunity cost. Include all open/expired exposure.
Carry/basis requires actual simultaneous legs and funding cashflows.
```

## Role F: Polymarket/Kalshi and copytrader diagnosis

```text
READ-ONLY public data and synthetic paper ledgers only; no venue authentication,
account access, geography bypass or order authority.
Determine whether output is an EVENT CONTRACT/token, an underlying BTC/stock
signal, a wallet-position snapshot or a reverse-engineered academic rule.

Trace ten eligible candidate lifecycles end-to-end: source observed-at,
leader fill if actually available, full leader hedge/exposure, follower's
first executable bid/ask, exit/resolution, fees, funding and settlement.
Missing leader trades or exits make follower profitability unestablished.

Event contracts need event/contract/token IDs, rules, executable price/depth,
void/cancellation/push semantics and payout ledger. Measure calibration,
Brier/log loss and information improvement versus a naive/public forecast.
CLV is informative, not sufficient profit proof. Copying displayed winners
without latency/full-book costs is forbidden evidence.

Run a latency/spread stress and a no-trade/naive-probability control. For an
underlying price strategy use BTC/asset benchmarks, not event payout math.
Return the specific first broken lifecycle edge and safest diagnostic fix.
Prediction-market signals are informational inputs, not investment advice.
```

## Role G: paper-account operator after approval

```text
Operate only the approved frozen PAPER strategy with fixed starting equity.
Persist immutable orders/fills/rejections/cancellations, quantities/cash,
all open positions, fees/distributions/financing and daily NAV. No reset of
the account after losses and no replacing losing picks.

Use the same market-data clock and allocation constraints as validation.
Paper fills must include realistic slippage/depth and be labeled modeled.
Record live decision availability before fetching future prices.
Compare cash, buy-hold, SPY total return and risk-matched controls concurrently.
Report consecutive nonoverlapping evaluation periods, losing periods,
drawdown/recovery, costs, NAV reconciliation and effective sample.
Weeks establish liveness; monthly strategies need calendar/regime exposure
and often6-12months or longer for adequate power. Never promise repeated wins.
```

## Role H: independent falsification / merge gate

```text
Do not tune the implementer's strategy. Reproduce it from the frozen spec with
independent code and, where feasible, independent price/adjustment checks.
Attack timing, corporate actions, denominator selection, open exposure,
funding, capacity, overlap, trial counts and null-test validity.

A strategy that makes15% while SPY makes18% has absolute profit but fails
raw SPY outperformance. A smaller drawdown alone is not alpha. A Sharpe-
invariant shuffle of return values is not a valid random-entry timing test.

Quote actual pre-change lines and check exact production caller/command if a
code PR is proposed. Approve only owned-file changes, a common evidence
contract, passing negative tests and a genuinely reproducible candidate.
Write evidence-backed ACCEPT_FOR_FORWARD / REJECT / INSUFFICIENT, not a
majority-model vote. Missing data or an API failure must remain visible.
```

## Cross-machine handoff contract

Each role sends a small manifest: `hypothesis_id`, parent/family ID, owner, role, SHA, input hashes, UTC cutoff, frozen spec hash, owned paths, exact commands/results, artifact URLs and verdict. Use the approved local peer-coordination mechanism; do not send credentials, user portfolios or confidential code to public AI providers.

One coordinator owns the registry and trial ledger. One independent reviewer owns falsification. Implementers do not mark their own candidates capital-eligible. Mutating DB/deployment work requires its own approved plan, backup and rollback; this prompt package does not grant that authority.
