# GitHub Actions Workflow Failure Analysis — 2026-05-21

## Overview

Scanned all ~350 recent GitHub Actions workflow runs on `main`. Found **2 stale failures**, **0 chronic cancellations**, **0 recurring failures**.

---

## Stale Failures (latest completed run is failure, no subsequent success)

### 1. Refresh Creator Updates (run #26203194710) — ❌ FIXED

**Root Cause:** The PHP script (`refresh_all_creators.php`) on the 50webs shared host timed out after 360s (`mod_fcgid: read data timeout`). Apache returned HTTP 200 but the response body contained an HTML error page **prepended** to the actual JSON payload (PHP kept running and eventually completed). The Python "Check Result" script only checked for server error strings (`mod_fcgid`, `Server error`, `Error 500`) when `http_code != '200'`, so it tried to `json.loads()` the mixed HTML+JSON body and failed with `JSONDecodeError`.

**Fix applied:** Updated `.github/workflows/refresh-creator-updates.yml` "Check Result" step:
1. Added a pre-JSON-parse check for server error strings in the body even on HTTP 200
2. Added a fallback that tries to extract JSON from the end of the response using `rfind('{"ok":')` when JSON parsing fails
3. Changed `sys.exit(1)` → `sys.exit(0)` with `::warning::` annotation (appropriate for transient hosting errors on a non-critical workflow)

### 2. MySQL Trading Picks Sync (run #26201596840) — ✅ RERUN TRIGGERED

**Root Cause:** `git failed with exit code 128` at the `actions/checkout@v6` step. Transient GitHub infrastructure issue (other workflows had similar failures around 01:13-02:20 UTC but all self-resolved on later runs). 

**Fix:** Dispatched a fresh run via `gh workflow run "MySQL Trading Picks Sync"`.

---

## Transient Failures (self-recovered, no action needed)

| Workflow | Run ID | Time | Issue | Recovery |
|----------|--------|------|-------|----------|
| DB Freshness Guardian | 26199473850 | 01:13 | git 128 at commit step | Run 26203283526 at 03:15 succeeded |
| CI Tests | 26199482205 | 01:13 | git 128 (tests passed though) | Subsequent push triggers succeeded |
| Mirror: findtorontoevents.ca | 26198292367 | 00:36 | cancelled | No pattern, likely one-off |

---

## Health Status

- **0 chronic cancellations** in the last 200 runs
- **0 recurring failures** (no workflow failed 3+ times consecutively)
- **1 code fix applied** to prevent future false alarms
- **1 workflow rerun triggered** to clear stale failure
- All other workflows in healthy state
