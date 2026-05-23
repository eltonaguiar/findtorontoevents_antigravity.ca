# Sports Betting Playwright Swarm Findings

Date: 2026-05-04  
Scope: `https://findtorontoevents.ca/live-monitor/sports-betting.html`

## Objective

Define a deep testing and quality plan focused on:

- stale data detection,
- Today/Tomorrow bucketing correctness,
- runtime JS/console reliability,
- win-rate / profit-factor / settlement integrity.

## Swarm Conclusions

- The sports page needs a layered validation stack:
  - API contract layer,
  - browser runtime layer,
  - UI/API semantic parity layer,
  - metric recomputation layer.
- Midnight EST boundaries and fallback-path transparency are critical risk points.
- Reliability claims (WR/PF/ROI) should always be backed by recomputed checks from settled raw records.

## Test Architecture

### L0: API Contract Tests

- Validate schema and types for:
  - `sports_picks.php`
  - `sports_bets.php`
  - `sports_ml.php`
  - related diagnostics endpoints
- Enforce key invariants:
  - required fields present,
  - numeric fields parse,
  - no impossible values.

### L1: Runtime Error Tests

- Browser-level checks:
  - `page.on('pageerror')`
  - `page.on('console')`
  - network 4xx/5xx on core APIs
- Fail on critical errors (SyntaxError, ReferenceError, TypeError, unhandled crashes).

### L2: Semantic UI/API Parity

- Confirm UI cards match API payload:
  - odds,
  - EV,
  - confidence,
  - status/result,
  - bucket labels.

### L3: Metric Recompute Validation

- Recompute WR, ROI, PF from raw settled picks.
- Verify denominator policies and settlement accounting.
- Enforce sample-size confidence gates before showing strong claims.

## Freshness and Timezone Checks

- Add explicit freshness assertions:
  - generated timestamp age,
  - stale-banner thresholds,
  - fallback marker visibility.
- Midnight EST test matrix:
  - 23:58,
  - 23:59,
  - 00:00,
  - 00:01
- Validate Today/Tomorrow/Yesterday labels and counts across boundary.

## Negative Path Coverage

- Primary API outage with fallback expected.
- Malformed payload fields.
- Partial payload records.
- Duplicate pick injection.
- Delayed settlement/unfinished outcomes.

Each negative case should define strict expected UI behavior and failure policy.

## Observability Recommendations

- Add payload metadata:
  - `trace_id`,
  - `data_generated_at_utc`,
  - `freshness_age_minutes`,
  - `is_fallback_response`,
  - source chain.
- Add lightweight client diagnostics buffer for fetch failures and parsing issues.
- Add synthetic monitors (API + browser) with alert thresholds.

## Two-Week Execution Plan (Summary)

- Days 1-3: contract + helper scaffolding.
- Days 4-7: runtime + freshness + timezone tests.
- Days 8-10: negative tests + fallback validation.
- Days 11-14: metrics reconciliation, CI gating, monitoring rollout.

## Risks and Mitigation

- Hidden stale data risk: make freshness explicit and test-gated.
- Midnight bucket regressions: deterministic EST boundary tests in CI.
- Metric trust drift: recomputed PF/WR checks as blocking gates.

## Outcome

The sports-betting plan is ready for implementation with clear pass/fail criteria and production-grade reliability controls.

