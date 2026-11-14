# EQUITY — Per-Asset-Class Quick-Win Fix Proposal

- **Asset class:** EQUITY
- **Audit date:** 2026-11-14 (live payload `dashboard_data.json` generated 14:30Z)
- **Evidence source:** verified live payload + Yahoo-verified quotes

## Class Verdict

**ALIVE** — prices are real/legit (ADBE/SNDL current_price == Friday close exactly, Yahoo-verified → 0% PnL is a legitimate parked state, not stale). The real defect is **statistical disclosure**: the headline "75% WR / PF 8.86" is n=8 (95% CI [0.41, 0.93]); larger samples land at ~43–46% WR, PF ~0.70. This is a reporting problem, not a price problem.

## Quick-Win Fixes

### 1. Add n + CI to headline profitability claims
- **Problem:** "75% WR / PF 8.86" reads as strong evidence but is n=8 (CI [0.41,0.93]) — materially different from the larger-sample reality (~43–46% WR, PF ~0.70).
- **Fix:** Append sample size and CI to any headline stat, e.g. `75% WR (n=8, 95% CI [0.41,0.93])`, and show the larger-sample estimate alongside.
- **Impact:** High — stops over-inference / misleading headline.
- **Effort:** Low — string formatting in display layer.
- **Risk:** Low.
- **Target file(s):** `audit_trail/dashboard_generator.py` (headline rendering; verified exists). Verify exact stat-formatting location.

### 2. Treat "current_price == Fri close" as parked, NOT stale
- **Problem:** 0% PnL on ADBE/SNDL will be auto-flagged as stale by a naive freshness check.
- **Fix:** When `current_price == last close` exactly (Yahoo-verified), render a "last quote = Fri close (parked)" label instead of a stale-warning; do not mutate PnL.
- **Impact:** Medium — removes false alarms, keeps legit state visible.
- **Effort:** Low.
- **Risk:** Low.
- **Target file(s):** `audit_trail/universal_pick_resolver.py` (price/PnL resolution; verified exists). Verify the stale-detection branch.

### 3. Gate "profitability" claims behind n ≥ 30
- **Problem:** Small-n headline claims survive review; z=1.39 (EQUITY edge) already fails the 1.96 bar on larger samples.
- **Fix:** Add a sample-size gate: suppress or downgrade any WR/PF headline when n < 30 (show n only), and surface the z-score test result.
- **Impact:** High — prevents editorializing small samples.
- **Effort:** Low.
- **Risk:** Low.
- **Target file(s):** `alpha_engine/config.py` (thresholds; verified exists) + `audit_trail/dashboard_generator.py`.

### 4. Add a sample-size gauge to the panel
- **Problem:** Readers cannot see how thin the underlying sample is.
- **Fix:** Render an `n=` badge + CI bar next to every class-level stat; color-code when n < 30.
- **Impact:** Medium.
- **Effort:** Low-Medium.
- **Risk:** Low.
- **Target file(s):** `audit_trail/dashboard_generator.py` (verify path).

## Unverified / Notes
- Larger-sample figures (~43–46% WR, PF ~0.70) are from prior audit context; re-confirm exact source before quoting precisely.
- No code surgery required — fixes are disclosure/sampling only.
