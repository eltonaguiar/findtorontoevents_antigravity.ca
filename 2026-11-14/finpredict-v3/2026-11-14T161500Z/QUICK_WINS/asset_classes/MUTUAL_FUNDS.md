# MUTUAL_FUNDS — Per-Asset-Class Quick-Win Fix Proposal

- **Asset class:** MUTUAL_FUNDS
- **Audit date:** 2026-11-14 (live payload `dashboard_data.json` generated 14:30Z)
- **Evidence source:** verified on-disk (ranker/site absent) + DB family presence confirmed

## Class Verdict

**PLANNED (not implemented)** — DB families `mutual_fund_v1` / `mutual_fund_v2` exist (verified: `tools/recon_uncharted_tables.py:29-30`, prefixes `mf_` / `mf2_`), but the planned tooling is **missing**: `alpha_engine/mutual_fund_ranker.py` does not exist, and `/audit/mutual-funds.html` does not exist (note: `audit_dashboard/funds.html` does exist — verify whether that is the intended page). This is an institutional-plan track (F2), not a live-data class.

## Quick-Win Fixes

### 1. Stop implying live data for an unbuilt class
- **Problem:** The dashboard may surface the class or its DB families in a way that implies live ranked performance that does not exist.
- **Fix:** Render an explicit **"PLANNED — not implemented"** badge for MUTUAL_FUNDS; do not emit live-looking stats until the ranker ships.
- **Impact:** High — removes a false-live impression, avoids misleading users.
- **Effort:** Low.
- **Risk:** Low.
- **Target file(s):** `audit_trail/dashboard_generator.py` (verified exists) — verify how the class is currently rendered.

### 2. Either build the minimal ranker or keep the class suppressed
- **Problem:** `alpha_engine/mutual_fund_ranker.py` is referenced by the plan but does not exist.
- **Fix (option A — build minimal):** Create `alpha_engine/mutual_fund_ranker.py` that reads `mutual_fund_v1/v2` families (DB) and emits a simple ranked list (score + source). Reuse existing scoring helpers; keep it read-only.
- **Fix (option B — suppress):** If not building now, hide the class from the active/ranked surfaces entirely.
- **Impact:** Medium-High.
- **Effort:** A = Medium; B = Low.
- **Risk:** A = Low-Medium; B = Low.
- **Target file(s):** New file (A), or config/dashboard config (B). Verify DB access layer path before coding.

### 3. Map the intended presentation page
- **Problem:** `/audit/mutual-funds.html` (plan) does not exist; `audit_dashboard/funds.html` exists but its role is unconfirmed.
- **Fix:** Decide whether `funds.html` is the intended destination; if so, wire the ranker output to it (or create the page). If not, leave it out of the live set.
- **Impact:** Medium.
- **Effort:** Low-Medium.
- **Risk:** Low.
- **Target file(s):** `audit_dashboard/funds.html` (exists — verify it is the mutual-fund page) + deploy list in `audit-dashboard.yml`.

### 4. Track the F2 plan explicitly
- **Problem:** Planned-but-unbuilt state is easy to lose track of.
- **Fix:** Add a one-line status note in the audit/doc layer: "MUTUAL_FUNDS = planned (families present, ranker unbuilt)" so future agents don't assume implementation.
- **Impact:** Low-Medium (process).
- **Effort:** Low.
- **Risk:** None.
- **Target file(s):** docs/audit note (verify path).

## Unverified / Notes
- `audit_dashboard/funds.html` exists but was **not** verified as the mutual-fund page — verify before wiring.
- DB family presence verified via `tools/recon_uncharted_tables.py:29-30` (`mf_`, `mf2_` prefixes).
