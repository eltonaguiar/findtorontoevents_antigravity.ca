# COMMODITY — Per-Asset-Class Quick-Win Fix Proposal

- **Asset class:** COMMODITY
- **Audit date:** 2026-11-14 (live payload `dashboard_data.json` generated 14:30Z)
- **Evidence source:** verified live payload (PA=F / SB=F entries match Friday close exactly; feed alive)

## Class Verdict

**ALIVE but unproven** — feed is alive (PA=F / SB=F entries match Friday close exactly), but **0 closed trades** exist, so the class has no validated track record; avgScore 19 sits below the 30 threshold.

## Quick-Win Fixes

### 1. Mark class "unproven" (no closed sample)
- **Problem:** 0 closed trades mean any positive signal is unvalidated; presenting it as proven overstates confidence.
- **Fix:** Render an explicit "unproven — 0 closed trades" status badge on the commodity panel; suppress WR/PF claims until n ≥ 1 (ideally ≥ 30).
- **Impact:** Medium — honest disclosure.
- **Effort:** Low.
- **Risk:** Low.
- **Target file(s):** `audit_trail/dashboard_generator.py` (headline/verdict rendering; verified exists).

### 2. Surface / act on avgScore 19 < 30
- **Problem:** avgScore 19 is below the 30 threshold — either the threshold is misapplied or commodity signals are genuinely weak.
- **Fix:** (a) Confirm the score threshold applies to commodities; (b) if so, either raise the entry bar or log why commodity candidates fall short before they are promoted to active.
- **Impact:** Medium — prevents weak candidates from polluting active picks.
- **Effort:** Low-Medium.
- **Risk:** Low.
- **Target file(s):** `alpha_engine/config.py` (score thresholds; verified exists) — verify where commodity scores are compared.

### 3. Add forward-validation tracking for commodity picks
- **Problem:** No closed trades → no feedback loop to validate commodity signal quality.
- **Fix:** Route commodity picks through the existing forward-validator so they accumulate a closed sample over time (reuse `alpha_engine/forward_validator.py`).
- **Impact:** Medium — builds an evidence base.
- **Effort:** Medium.
- **Risk:** Low.
- **Target file(s):** `alpha_engine/forward_validator.py` (verified exists). Verify commodity feed hooks in.

### 4. Add a feed-freshness label for PA=F/SB=F
- **Problem:** Entries matching Friday close exactly could be read as stale rather than a live quoted snapshot.
- **Fix:** Show last-quote age per commodity symbol (e.g. "quote = Fri close") so the alive-but-flat state is explicit.
- **Impact:** Low-Medium.
- **Effort:** Low.
- **Risk:** Low.
- **Target file(s):** `audit_trail/universal_pick_resolver.py` (verified exists).

## Unverified / Notes
- Whether avgScore 19 reflects threshold misapplication vs genuinely weak signals: **UNVERIFIED** — confirm scoring inputs before changing the threshold.
- Feed "alive" evidence from audit is solid (PA=F/SB=F match); closed-trade count of 0 confirmed.
