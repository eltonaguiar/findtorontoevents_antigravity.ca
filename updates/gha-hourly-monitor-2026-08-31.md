# GHA Hourly Health Monitor — 2026-08-31

## 13:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** N/A — no workflow named "CI Tests" exists in this repo (404). 362 active workflows found; no standard CI gate detected. The closest referenced gate is `sports-smoke-and-e2e.yml` (see CLAUDE.md §Goal #2).

**Picks-Now Live PnL (hourly) — FAILURE (run #1746):**
- Run ID: 33394090626 | [View run](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/33394090626)
- All code steps succeeded: checkout ✓, python setup ✓, deps ✓, refresh live PnL ✓, resolve matured picks ✓, rebuild track record ✓, commit JSONs ✓, push data commit ✓
- **Failed step:** "FTP deploy to production" (step 10/10) — duration ~30s then failure
- Classification: likely FTP/TLS drop to 50webs (known fragile; see CLAUDE.md critical file rules). Data was committed and pushed to git successfully; only live-site FTP upload failed.

**Chronic workflows:** none detected in 100 sampled recent main-branch runs. All completed runs show `success`; no `cancelled` conclusions observed.

**Open PRs:** 9 open PRs (#562, #564, #581, #595, #600, #657, #665, #666, #667). No "CI Tests" check exists repo-wide, so no CI Tests PR failures to classify. PR heads are all stale against main (base sha `69c8ff54` or older); no active CI failures triggered from these PRs in recent run history.

**Action required:** Operator should verify FTP connectivity to 50webs for `picks-now-live-pnl.yml`. If the FTP drop is recurring, consider adding retry logic or alerting on step 10 specifically. The git data commit succeeded — production data is not lost, just the live-site HTML/JSON refresh failed.

---

_Note: No "CI Tests" workflow found — if this workflow was intentionally removed or renamed, update the monitor prompt to use the current workflow name._
