# GHACTIONS_2026-11-16 — Stabilization Action Plan
**Timestamp (EST):** 2026-11-15 21:03
**Author:** Antigravity Coordinator
**Status:** Ready for Review / Execution

## 1. Current State Verification (Double-Check)
*   **Git HEAD:** `a5e96c0b055` (synced with `origin/main`).
*   **Key Files Verified on `origin/main`:**
    *   `audit-dashboard.yml`: Cron `10 * * * *`, Concurrency `dashboard-publish` (`cancel-in-progress: false`).
    *   `dynamic-alpha-engine.yml`: Cron `18,48 * * * *`, Concurrency `dynamic-alpha-engine-push` (`cancel-in-progress: false`).
*   **Revert Safety:** The exact content of both files at the time of analysis is stored in the git history at `origin/main`. Any change can be reverted with `git checkout origin/main -- .github/workflows/audit-dashboard.yml`.

## 2. Downstream Impact Analysis (`findtorontoevents.ca/audit`)
*   **Primary Consumer:** `audit-dashboard.yml` directly generates the payload for `/audit/data/dashboard_data.json`.
*   **Impact of Change:** Changing the cron from `10 * * * *` (hourly) to `10 */3 * * *` (every 3 hours) means the dashboard data will be **up to 3 hours stale** instead of 1 hour.
*   **Risk Level:** **Low**. The workflow already has `cancel-in-progress: false`, meaning it queues rather than drops. The change simply reduces frequency. The live runtime (105.9 min) already exceeds the hourly interval, so the current state is already "stale" by definition (losing 43% of runs). The fix makes the schedule honest.
*   **Mitigation:** The `workflow_dispatch` input remains available for manual on-demand refreshes if a critical update is needed.

## 3. Proposed Changes (Cron Fixes)
These are the **only two workflows** requiring immediate cron adjustment to stop data loss.

### Fix A: `audit-dashboard.yml`
*   **Current:** `cron: '10 * * * *'` (Runtime: 105.9 min).
*   **Proposed:** `cron: '10 */3 * * *'` (180 min interval).
*   **Rationale:** Runtime > Interval. 43% of runs are silently replaced. 3-hourly gives headroom.

### Fix B: `dynamic-alpha-engine.yml`
*   **Current:** `cron: '18,48 * * * *'` (Runtime: 77-80 min).
*   **Proposed:** `cron: '23 */2 * * *'` (120 min interval).
*   **Rationale:** 62% of runs are killed at ~29 min due to pending slot replacement.

## 4. TODO List (Execution Order)
1.  [ ] Create `GHACTIONS_2026-11-16/2026-11-15_2103_EST_REPORT.md` (Triage Summary).
2.  [ ] Create `GHACTIONS_2026-11-16/REVERT_INSTRUCTIONS.md` (Exact `git show` output of current files).
3.  [ ] Apply Fix A (`audit-dashboard.yml`) — **Review Required**.
4.  [ ] Apply Fix B (`dynamic-alpha-engine.yml`) — **Review Required**.
5.  [ ] Deploy `gha-watchdog.yml` (if not already present).
6.  [ ] Bulk-cancel 51 zombie queued runs (API call required; needs `actions:write` scope).

## 5. Documentation for Reversion
If any change causes issues:
```bash
# Revert both files to the verified state
git checkout origin/main -- .github/workflows/audit-dashboard.yml
git checkout origin/main -- .github/workflows/dynamic-alpha-engine.yml
git commit -m "revert: restore pre-stabilization cron intervals"
git push origin main
```
**Note:** The `audit-dashboard.yml` change impacts data freshness on `findtorontoevents.ca/audit`. Reverting will restore the (broken) hourly schedule.

---
**Next Action:** Awaiting user approval on Fix A and Fix B before editing files. All other swarm workers are on standby.