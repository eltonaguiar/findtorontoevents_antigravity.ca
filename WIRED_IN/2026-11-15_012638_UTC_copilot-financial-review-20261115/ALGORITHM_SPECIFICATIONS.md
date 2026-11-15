# Algorithm specification per asset class

## Scope, status and common admission rule

This is an informational research specification, not orders or capital sizing. A method is not selected merely because its class has a historical PF/WR badge.

For every class, new simulated entries require instrument identity, information-available time, executable fill/mark/exit clock, quantity/currency, cost scope, complete portfolio NAV and a frozen hypothesis/version. Unknown/NULL is not zero. An open exit is not applicable; a missing required closed exit is unknown.

**Abstention specification:** if any required evidence is missing, disputed or fails the approved class/portfolio gates, output `ABSTAIN` with explicit reasons and `capital_eligible=false`. Preserve existing open positions in the accounting ledger; abstention is not retroactive deletion, invented closure or production strategy retirement.

No algorithm in this package is newly wired into production. The tested runner is an opt-in offline caller. Existing charter/registry/harness gates remain unchanged.

## A. Mutual-fund and ETF baseline: H-142

**Selected use:** paper reference/measurement lane, not predictive alpha.

| Field | Exact tested definition |
|---|---|
| Universe | FZROX, FXAIX, VTSAX, SPY, VTI, BND and SGOV, each in its own USD 100,000 account; no ranking among funds |
| Signal | Unconditional fixed holding; no forecasts, momentum filter, stock selection or parameter fitting |
| Entry | Model one funded purchase at the first common session close, 2021-11-15 |
| Holding | Entire fixed dataset window; reinvested distributions implicit in total-return-adjusted prices, no intermediate rebalancing |
| Exit | Model liquidation at final common close, 2026-11-13; include exit cost |
| Allocation | 100% of that separate account to its one instrument after funded fees; no leverage or pooled double-counting of accounts |
| Costs | 5 bps per actual dollar traded each side; repeat at 20 bps. Ongoing expenses already embedded in NAV; tax/platform/FX excluded |
| Accounting | Fractional adjusted total-return units, explicitly not observed raw fill quantities; raw closes retained as references |
| Benchmarks | Same-window SPY total return, same-underlying/wrapper comparisons and SGOV investable cash proxy |
| Risk | Calendar CAGR, cash-relative Sharpe, volatility, MDD, underwater duration, daily ES and joint block scenarios |
| Status | Historical baseline profit; canonical admission `UNTESTED`, capital false, forward positions zero |

**Why FXAIX/SPY are reference choices:** direct large-cap exposure comparison, low turnover, simple reproducible accounting and small observed tracking/cost differences. FXAIX is not a retrospectively selected active-manager winner. Other tested fund holdings remain comparisons; no population-wide "best fund" selection was tested.

**Prospective execution differs from the retrospective model:** register the future paper start/end and mandate separately; verify purchase eligibility, share class and actual NAV order cutoff. A signal based on a newly published NAV cannot fill at that already-published NAV. ETF execution needs a valid post-decision market price/spread. No forward order is created by this specification.

## B. ETF tactical rule: H-143, rejected for alpha

The exact tested rule is retained so nobody changes its name and calls it a winner:

1. At each complete observed calendar month-end, take SPY's last 10 month-end adjusted closes.
2. If the latest value is **strictly greater** than their arithmetic mean, target 100% SPY; otherwise target 100% SGOV.
3. Execute at the **next common session close**. The old allocation earns returns through that execution close; never fill at the signal close.
4. Hold until the next eligible target, with funded 5 bps/side costs; repeat at 20 bps. No shorts, leverage, TP/SL or parameter optimization.
5. Start after 10 month-end observations; ignore incomplete final-month signals. Include initial/final transactions and daily open exposure.
6. Compare to same-window SPY/FXAIX/SGOV and an explicitly ex-post exposure-matched monthly mix.

**Test interval:** 2022-09-01 to 2026-11-13.
**Decision:** `REJECT_ALPHA_FORWARD_QUEUE`; positive return was insufficient. It is not a rejection of every ETF/TAA family, nor a production blacklist change.

The [actual runner](../../2026-11-15_AM_profitability-plan/copilot-financial-review/simulation_runner.py) implements these baseline/trend rules. Its outputs and source hashes are [retained here](../../2026-11-15_AM_profitability-plan/copilot-financial-review/09_EXECUTED_SIMULATIONS.md).

## C. Equity research specification: SPEC-EQ-PIT-01

**Not selected for capital; not implemented, backtested or canonically preregistered by this extension.** This document identifier is not an H-NNN registry entry.

Purpose: test whether information actually available from corporate filings adds value beyond price-only equity factor families already refuted on the earlier dataset. Operating profitability may persist; that is an economic hypothesis, not established alpha.

Proposed frozen research rule, to preregister before any new data test:

- Universe: point-in-time US exchange-listed common stocks, excluding ETFs, ADRs and financial SIC 6000-6999. Historical membership, delistings and corporate actions required.
- At month-end require contemporaneous market cap >= USD 1 billion, price >= USD 5 and trailing 20-session median dollar volume >= USD 10 million. These are proposed feasibility rules, not empirically optimal thresholds.
- Features must have been publicly filed at least one full US trading session earlier. Use contemporaneous amended/restated values only after their actual publication. Latest eligible filing may not be older than 180 calendar days.
- Score = sum of the latest four eligible quarters' operating income divided by the mean of assets at the beginning/end of that four-quarter interval. Require finite, positive denominator and consistent units. Log all missing inputs/exclusions; no current-only survivor universe.
- Rank descending score, ties by ticker ascending. Select 20 names, maximum five per contemporaneous sector, 5% target each. If fewer than 20 eligible names satisfy the constraints, `ABSTAIN`; do not silently relax them.
- Signal after month-end information cutoff, rebalance at next eligible session close; old holdings earn through that close. No leverage/shorts or intraday stop assumptions.
- Model 10 bps per traded dollar each side and fixed 20 bps stress; replace assumptions with evidenced execution estimates before forward approval.
- Compare SPY total return, point-in-time same-universe equal-weight and sector/exposure-matched controls. Retain daily NAV, full trial family and genuine unseen forward evidence.
- Retain existing production gates; before research, freeze portfolio-specific power, trial-adjusted benchmark-excess and risk criteria with the coordinator. No performance is implied by this specification.

**Blocker now:** authoritative point-in-time filings/universe/dead-name coverage and executable price/cost evidence were not verified here. Do not repeat rejected price-only signals under a "quality" label.

## D. Remaining class decisions and required specifications

For these classes, the currently justified output is **abstention or diagnostic research**, not a chosen profitable trading algorithm. Research-family names below are directions, not frozen, tested or registered strategies.

| Class | Current algorithm/decision | Research direction if blockers clear | Inputs/exits that must be specified before testing |
|---|---|---|---|
| BOND / fixed income | H-142 SGOV/BND as reference exposures only; no bond-prediction algorithm selected | Lagged duration/curve allocation | Tradable price, coupon/distribution, duration/credit/FX and timed fill/exit; FRED yields are features, not fills |
| COMMODITY | `ABSTAIN` from alpha admission | Diversified low-frequency trend/carry | Individual contracts, roll/expiry/multiplier/collateral, costs, lagged COT publication if used; fixed next-event entry and registered horizon |
| FUTURES | `ABSTAIN` until contract-accounting validation | Broad volatility-aware trend across underlying exposures | Actual contract months, minimum sizes, margin/limit moves and funded collateral; continuous =F bars alone are not executable history |
| FOREX | Measurement/abstention; no newly selected algorithm | Lagged carry/trend only after diagnosis | Pair/base currency and inversion, bid/ask, swaps/holidays and exact holding/exit; no pip/PnL clamp or automatic inversion of failed signals |
| CRYPTO | Conditional cohort investigation, no admitted new entries | One existing frozen entry-condition or fully modeled carry/basis family | Spot/perp identity, fees/funding, full legs/liquidations, source dedup and event-time fills; compare BTC plus the same asset/direction/duration |
| MEME | `ABSTAIN` pending liquidity/identity/history | Feasibility before any momentum/reversal idea | Listings/delistings, executable depth, gas/MEV and stable token identity; major-coin evidence cannot certify this subset |
| PENNY_STOCK | `ABSTAIN` pending historical universe/fills | Liquidity-aware event study | PIT float/price, halts/delistings, spread/borrow/capacity; no synthetic squeeze/TP wins |
| Options / volatility / leveraged products | No actual option strategy selected | Contract/payoff-aware study, not underlying-signal relabeling | Premiums/Greeks/expiry/assignment, spread, financing and complete hedged portfolio |
| Kalshi / Polymarket event contracts | Lifecycle diagnosis and `ABSTAIN` from execution | Public forecast-calibration/follower feasibility | Contract/token ID, settlement/void rules, quote/depth/time, fees, full leader/follower histories and access constraints |
| REIT / gold / regional/sector exposures | Look-through components/proxies, not independent new alpha | Exposure-matched allocation research | Matching distributions/currency/rates/sector and actual wrapper/contract execution |

Sports betting remains a separate Goal #2 ledger. It cannot borrow fund NAV or stock benchmark evidence.

## Holding style and exit discipline

Baseline fund/ETF exposure is long-term; equity proposal is monthly/position-style. Other holding horizons must be registered, not improvised from a favorable chart.

Scalping/day trading requires depth/latency/cost evidence unavailable from daily NAVs. Swing/position experiments require actual completed independent lifecycles, but open holdings are marked daily. Ordinary mutual funds do not become intraday tradable because the user wants faster elimination.

Use [the complete style/famous-system matrix](../../2026-11-15_AM_profitability-plan/copilot-financial-review/01_PER_CLASS_PLAN_AND_STYLES.md) and [forward stopping protocol](../../2026-11-15_AM_profitability-plan/copilot-financial-review/10_FORWARD_TRACKING_PROTOCOL.md). Risk stops can act on marked exposure; statistical rejection requires the frozen objective, horizon and adequate effective evidence.
