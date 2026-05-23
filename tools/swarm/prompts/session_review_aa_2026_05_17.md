# Session AA Review — 2026-05-17

## Context
Autonomous trading-edge improvement session on findtorontoevents.ca/audit.
Review the following deliverables for correctness, gaps, and follow-up actions needed.

## Deliverables This Session

### 1. M-073 — btc_hour_filter wiring (score_booster.py)
`score_booster._apply_crypto_hour_filter` previously had inline CRYPTO-wide penalties (-20 for hours 08-09, +8 for hour 22).
It now delegates BTC symbols (BTCUSDT, BTCUSD) to `alpha_engine.btc_hour_filter.btc_hour_score_adjustment` (-12 for hours 08-09, +5 for hour 22).
Non-BTC CRYPTO picks continue using the inline -20/+8 penalties.
Fail-open via try/except ImportError.
+2 regression tests, 15/15 pass.

Review questions:
- Is delegating BTC to a lighter penalty (-12 vs -20) correct? The module penalties are based on more granular BTC-specific analysis.
- Is the fail-open pattern safe, or should ImportError be logged?
- Any double-counting risk between module result and inline for BTC symbols?

### 2. charter_drift_circuit_breaker realized_n fix
`compute_realized_wr_30d()` was reading entry `timestamp` (time of signal emission) instead of `closed_at/resolved_at` (close time). Since the 30d lookback uses close time, all classes returned n=0 and stayed in cold_start permanently.
Fixed to read: `closed_at` -> `resolved_at` -> `close_time` -> `timestamp`.
Post-fix: CRYPTO n=133, EQUITY n=44, COMMODITY n=354 (within 30d window).

Review questions:
- Is the fallback chain correct? Any fields missing?
- COMMODITY n=354 within 30d -- does this mean the circuit breaker could now trip for COMMODITY?
- DEFAULT_MIN_REALIZED_N=20 -- is this threshold still appropriate with the fix?

### 3. Dashboard banner corrections (audit_dashboard/template.html)
- CRYPTO: Updated from stale PF=1.30 to MONEY_READY (PF=2.66, WR=69.0%, n=475 filtered)
- COMMODITY: Corrected from inflated raw PF=2.48 to policy-clean PF=1.25, n=160/WR=45.0% per pf_registry.json
- MONEY READY tooltip: Updated to reflect per-class verdicts

Review questions:
- Is the CRYPTO PF=2.66 figure reliable? It uses the 3-layer filter (blocked strats/symbols). Is the filter documented and tested?
- COMMODITY policy-clean n=160 WR=45% is below T2 WR floor (>=50%). Should the banner say COMMODITY is NOT_READY rather than WATCH?
- Any banners that need updating that were missed?

### 4. Slippage test assertions (test_outcome_resolver_slippage_wire.py) -- M-069 units fix
Previously tests expected COMMODITY round-trip slippage = 0.12 (120bp) -- was 100x inflated bug.
Correct value: 12bp = 12/10000 = 0.0012.
Test 2: expected 0.38 -> corrected to 0.4988 (0.5 - 0.0012).
Test 3: expected net < 0 on 7.18bp gross -> corrected to net > 0 (0.0718 - 0.0012 = 0.0706).

Review questions:
- Are any other tests relying on the old inflated slippage values that may still be failing?
- Should there be a test that verifies slippage deduction across all 7 asset classes?

## Current State Summary
- CRYPTO: MONEY_READY (PF=2.66, n=475 filtered, WR=69.0%)
- COMMODITY: WATCH (PF=1.25 policy-clean, n=160, needs n>=100 at T2 WR floor)
- EQUITY: WATCH (only 1 testable strategy; connors_rsi2 shadow accumulating)
- FOREX/ETF/BOND: NOT_READY

## Known Blockers (do not attempt to fix in this review)
- MySQL ghost-row purge: 655k stale rows -- needs PA console (target 2026-05-24)
- UEPS_ENABLE_PEAD=1: needs PA console
- ETF/BOND: accumulation-only (time-gated)

## Output Format Required
Provide a JSON assessment with:
- verdict: APPROVE, REQUEST_CHANGES, or NEEDS_DISCUSSION
- concerns: list of {severity, area, issue, recommendation}
- action_items: list of {priority, description, file, rationale}
- summary: one paragraph overall assessment
