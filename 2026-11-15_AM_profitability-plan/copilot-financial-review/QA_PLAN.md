# Financial QA and release acceptance plan

Companion to [the reviewed proposal](./PROFITABILITY_FRAMEWORK.md).
These are proposed acceptance tests, not assertions that the current system passes.

## 1. Coverage before correctness

- Freeze snapshot cutoff, source commit, input hashes, validator-run time and market-data-as-of separately.
- Export uncapped open lifecycles and every terminal event in the fixed 24h interval from authoritative stores. Paginate on a stable watermark; reconcile emitter/outcome counts.
- Validate every row, including null and nonzero PnL. De-duplicate economically but retain every excluded record and reason.
- Report both total and independently measurable rows. Never achieve "100% priced" by dropping unsupported symbols.
- Require 100% validation-state coverage; unknown rows can remain unknown but cannot size/promote.
- Separate OPEN, terminal lifecycle and verified realized cohorts. Mixed `active_raw` is not an open denominator.

## 2. Zero and blank-field matrix

| Fixture | Expected result |
|---|---|
| Fresh, independently timestamped equal entry/exit | Verified gross flat; net result still reflects actual costs |
| Small actual movement rounds to 0.00% | Preserve precise numeric value and quote times; precision-aware display |
| Open, equal stored prices but no quote timestamp | UNVERIFIED/UNPRICED, not automatically verified because recent |
| Missing/stale/nonfinite/negative price | Null measured return plus explicit invalid/stale reason; sizing denied |
| Terminal TIME_EXIT without an event price | Terminal lifecycle with unmeasured financial outcome; never entry-price fallback |
| Blank execution time, otherwise plausible prices | Timestamp/provenance error; no exact-event verification |
| Closed row missing close time | Remains anomalous terminal row, not silently reclassified OPEN |
| Blank, zero and explicit false values | Preserve semantic distinction through backend, JSON, frontend and aggregate math |
| Backfill with valid current price different from entry | Must not write zero PnL or fabricate `closed_at=NOW()` |
| PnL fraction / percentage points / currency amount | Source-declared conversion only; reject undeclared units and global magnitude heuristics |
| Internally consistent prices outside independent history | DISPUTED provenance, even if arithmetic matches perfectly |

Open exit fields can be NOT_APPLICABLE; they are not required to contain a fake price. Closed execution provenance cannot be NOT_APPLICABLE without a declared unmeasured financial outcome.

## 3. Market-time reconciliation

### Common rules

- Identify tradable venue, contract/share class, currency, multiplier, direction and quantity.
- Actual activation/fill time is not interchangeable with signal, scrape, publication or resolution time.
- Compute open marks at the frozen as-of; compute terminal comparisons at the actual exit event.
- No candle/data published after the test's allowed decision time may influence entries.
- Use decimal/tick precision and executable spread/order type, not one universal 0.05pp tolerance.
- Missing historical coverage means UNVERIFIABLE, not a price fallback.
- Two providers should be operationally independent where possible. An identical mirrored feed is not independent corroboration.

### Crypto and intraday assets

- Prefer trade/quote events; bounded fine candles provide reasonability, not proof of fills.
- Test gaps, latency, stale cached marks, timezones, partial candles and data-provider disagreements.
- Test LONG/SHORT/BOTH-touch cases, trailing versus original stop, and opening target reached before later stop.
- No-bars/never-touched stops must be MODELED/AMBIGUOUS, not observed fills.

### ETF/equity/futures/FX

- Trading sessions, weekends, holidays and daylight-saving transitions are explicit.
- Saturday fund/ETF zeros can be reasonable last-session marks; staleness must be measured against the expected publication calendar.
- Handle split/distribution dates, adjusted versus executable raw prices, futures expiry/roll/multiplier and FX base/quote inversion.
- Futures continuous history is not itself an executable contract. Intraday equities need intraday histories, not a later daily close.

### Mutual funds

- Confirm share-class and intermediary cutoffs and next-computed NAV policy.
- Signal based on today's published NAV generally executes at a subsequent eligible NAV.
- Test after-cutoff, holiday, missing NAV, delayed publication, minimum investment, redemption restriction and settlement.
- NAV returns versus total returns must handle distributions and reinvestment without double-counting operating expenses.
- Daily closes may be valid daily NAV inputs; they cannot prove intraday trades.

## 4. Cohort, cost and financial-admission tests

- All displayed metrics carry row/cohort ID, filters, n_raw/n_measured/n_effective, time interval, resolver version and cost scope.
- Surface counts reconcile or explicitly explain differences; do not average different cohorts.
- Class expectancy must never fill strategy confidence or realized pick return.
- Cache-aging, missing/invalid/future timestamps, missing hashes, changed inputs and exceptions all deny financial admission.
- Invalid evidence returns a reason visible in UI/logs. Research logging and trade sizing are separate permissions.
- Test actual production normalization/writer/admission callers, not just helper functions.
- Browser/Python consumers share financial permission; intentional Smart/HC policy distinctions remain documented.
- Test OLD versus NEW ML feature values, bundle path, training/scoring schema and environment restoration.
- Reserve exposure after every accepted paper position and load it on the next run; duplicates and correlated instruments cannot bypass caps.

## 5. Statistical and portfolio risk QA

- Compound account NAV with quantities/cash/financing and open marks. Test the first-period loss and initial NAV baseline.
- Do not use additive trade PnL or sequential compounding of overlapping picks as portfolio drawdown.
- Calendar-time excess returns use currency/exposure/risk-matched benchmarks; SGOV is a cash proxy, not a guaranteed risk-free asset.
- Verify Sharpe/Sortino horizons, raw versus excess kurtosis conventions, variance-zero handling and DSR probability versus adjusted score.
- Timing null samples admissible entry times with matched duration/direction/costs; a return permutation preserving Sharpe must fail the test's validity check.
- Bootstrap preserves contemporaneous exposure and serial dependence; report block-length sensitivity and effective sample support.
- Purged chronological/nested tests prohibit training-universe, scaler and feature leakage.
- Register cumulative trials and post-hoc filters; no resetting trial count per report.
- Promotion requires corrected uncertainty on net benchmark-relative economic effect, not merely a 50% win-rate null.
- Tail metrics specify horizon, quantile, sign and sample support; insufficient tails produce INSUFFICIENT, not precise ES99.5.
- Stress equity/rates correlation, spread/funding increases, overnight gaps, redemption/illiquidity, FX, contract margin and provider outage.
- Report probability uncertainty, MDD/recovery duration, look-through concentration and risk contribution. No plug-in Kelly from unverified defaults.

## 6. Focused test placement

Extend existing tests where possible:

- `tests/test_stop_fill.py`, `tests/test_kimi_exit_fill.py`: event-bounded fills and model/observation distinction.
- `tests/test_universal_pick_resolver.py`, placeholder-exit tests: actual missing/stale TIME_EXIT writer branches.
- `tests/test_per_class_cost_gate.py`, `tests/test_hc_after_cost_gate.py`: scope, cache expiry and deny-sizing semantics.
- `tests/test_gatekeeper_leakage_default.py`, A/B tests: explicit OLD/NEW training/scoring parity.
- `tests/test_combined_book_sleeves.py`, `tests/test_benchmark_closed_ledger.py`: executable clocks and nondegenerate nulls.
- Existing Kelly/drawdown/risk tests: invalid-evidence halt, NAV loss and exposure constraints.
- Existing dashboard/browser tests: unknown versus verified zero, field flags, market interval detail and risk disclosure.

New lifecycle tests are justified only where no existing test file exercises persistent pilot positions or exact-event validator coverage.

Current commands run during review: 76 contract tests plus 52 benchmark/Kelly tests, **128 passed**. New negative tests above have not been implemented or run.

## 7. Release and operational QA

1. Re-anchor fixes on current remote main in an isolated own-change branch; preserve peer work.
2. Run the smallest relevant offline suites; then Python/browser contract integration.
3. Verify the production command and actual interpreter, package versions, feature mask and model bundle in critical CI logs.
4. Produce data artifacts in the controlled workflow, not by running dashboard generators in the shared checkout.
5. Compare generated cohort/hash and admission results before deployment.
6. Verify FTP-deployed page and sidecar hashes, all configured mirrors and failed/stale-source behavior. GitHub merge/green CI alone is not deployment.
7. Observe at least three full monthly decision cycles for fund research, longer when power is inadequate. Other strategies need their own predeclared effective-N and calendar exposure.
8. Require explicit approval for financial allocation; otherwise keep read-only/paper-only and zero sizing.

Rollback stops new admission while preserving history, before-images and exception reports. It never deletes anomalies or relabels unknowns as successful flats.
