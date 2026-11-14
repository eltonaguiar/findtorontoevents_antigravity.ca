# FOREX — Per-Asset-Class Quick-Win Fix Proposal

- **Asset class:** FOREX
- **Audit date:** 2026-11-14 (live payload `dashboard_data.json` generated 14:30Z)
- **Evidence source:** verified live payload (USDCAD=X / NZDUSD=X real live quotes, ~0.04–0.08% move confirmed)

## Class Verdict

**ALIVE (needs cleanup)** — current quotes are real live values (verified ~0.04–0.08% moves); USDCAD=X / NZDUSD=X appear frozen at entry because their PnL is 0 **by construction**, not due to staleness. However, **11 frozen closed phantom rows** (March 2026, exit UNKNOWN, exit==entry) pollute the closed set, and closed_at timestamps are batch-identical.

## Quick-Win Fixes

### 1. Purge / void the 11 phantom closed rows
- **Problem:** 11 closed rows with `exit == entry` and `exit = UNKNOWN` (March 2026) are artifacts, not real trades — they skew the closed set.
- **Fix:** Mark these rows VOID (or hard-delete) and exclude them from all closed-set stats (WR, PF, n). Add a filter: exclude rows where `exit == entry` AND `exit_status == UNKNOWN`.
- **Impact:** High — removes known pollution from metrics.
- **Effort:** Medium — one-off data cleanup + recurring guard.
- **Risk:** Low-Medium (ensure you do not delete real flat trades).
- **Target file(s):** Wherever the closed set is assembled (e.g. universal resolver / dashboard generator) + a one-off DB cleanup script. Verify exact producer path (likely `tools/` or DB script).

### 2. Fix "by-construction zero" labeling for frozen-at-entry pairs
- **Problem:** USDCAD=X / NZDUSD=X show PnL 0 because they sit at entry — a reviewer misreads this as stale.
- **Fix:** Render "frozen at entry (by construction, live quote)" instead of a stale flag when `current_price == entry` for these pairs.
- **Impact:** Medium — removes false staleness alarms.
- **Effort:** Low.
- **Risk:** Low.
- **Target file(s):** `audit_trail/universal_pick_resolver.py` (verified exists). Verify the stale-detection branch.

### 3. Dedupe batch-identical `closed_at` timestamps
- **Problem:** Closed rows share identical `closed_at` timestamps (batch write), so ordering/age stats are unreliable.
- **Fix:** Give each resolved row a unique `closed_at` (per-row resolution time, not one batch stamp); add a uniqueness check on write.
- **Impact:** Medium — restores reliable age/ordering stats.
- **Effort:** Medium.
- **Risk:** Low.
- **Target file(s):** The closure/resolution writer path (verify exact file — likely `audit_trail/universal_pick_resolver.py` or a DB sync script in `alpha_engine/audit_sync.py`).

### 4. Keep live quotes but validate freshness per pair
- **Problem:** Need to distinguish real quoted movement from frozen data generally.
- **Fix:** Emit a freshness flag per pair (e.g. quote age in minutes) so any genuinely stale feed is visible, independent of the by-construction zeros.
- **Impact:** Medium.
- **Effort:** Low-Medium.
- **Risk:** Low.
- **Target file(s):** `audit_trail/universal_pick_resolver.py` (verify path).

## Unverified / Notes
- Exact row provenance for the 11 phantom rows: **UNVERIFIED** — confirm which DB/log produced them before deleting.
- Real live-quote validation (~0.04–0.08% move) was confirmed at audit time.
