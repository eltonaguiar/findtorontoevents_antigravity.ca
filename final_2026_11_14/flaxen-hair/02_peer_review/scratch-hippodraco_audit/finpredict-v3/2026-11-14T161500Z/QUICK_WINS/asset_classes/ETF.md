# ETF — Per-Asset-Class Quick-Win Fix Proposal

- **Asset class:** ETF
- **Audit date:** 2026-11-14 (live payload `dashboard_data.json` generated 14:30Z)
- **Evidence source:** verified live payload (10 active ETF picks pinned at Friday close = legit snapshot)

## Class Verdict

**ALIVE** — 10 active ETF picks are pinned at Friday close (legitimate weekend-park snapshot), not stale. The closed sample is thin: n=8 (37.5% WR, PF 0.76). Problem = weekend park + thin sample + re-quote handling, not price fidelity.

## Quick-Win Fixes

### 1. Label parked ETF state explicitly
- **Problem:** Active ETF picks pinned at Friday close look like frozen/stale data to a reviewer.
- **Fix:** Render a "parked @ Fri close (weekend)" badge when the active quote equals the previous close; keep the value visible without a stale-warning.
- **Impact:** Medium — removes false stale flags.
- **Effort:** Low.
- **Risk:** Low.
- **Target file(s):** `audit_trail/universal_pick_resolver.py` (price resolution; verified exists). Verify the stale-detection branch.

### 2. Add n + CI to closed-sample stats
- **Problem:** Closed ETF n=8 (37.5% WR, PF 0.76) can be read as a firm signal.
- **Fix:** Render `n=8` with a 95% CI and a "thin sample" note; suppress strong PF/WR wording until n ≥ 30.
- **Impact:** High — prevents over-inference from n=8.
- **Effort:** Low.
- **Risk:** Low.
- **Target file(s):** `audit_trail/dashboard_generator.py` (headline rendering; verified exists).

### 3. Ensure re-quote resumes on next market open
- **Problem:** Pinned-at-Friday-close values must refresh when the market opens, or they become truly stale.
- **Fix:** Add a re-quote hook that, on the next trading session open, re-fetches ETF quotes and updates `current_price`/PnL before the panel is served.
- **Impact:** Medium — keeps the parked→live transition automatic.
- **Effort:** Medium.
- **Risk:** Low.
- **Target file(s):** `audit_trail/universal_pick_resolver.py` or `alpha_engine/production_scanner.py` (verified exist). Verify where quote refresh is triggered.

### 4. Expose sample-size as a first-class metric
- **Problem:** Sample sizes are buried; class-level verdicts can hide n<30.
- **Fix:** Render an `n=` badge + CI bar on class stats, consistent with EQUITY.
- **Impact:** Medium.
- **Effort:** Low.
- **Risk:** Low.
- **Target file(s):** `audit_trail/dashboard_generator.py`.

## Unverified / Notes
- No code surgery required — fixes are disclosure/sampling + re-quote timing.
- Weekend-park snapshot is intentional; do not "fix" it by mutating prices.
