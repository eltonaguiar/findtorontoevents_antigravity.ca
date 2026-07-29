# GHA Hourly Health Monitor — 2026-07-29

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress
- Run 30454089123 — 2026-07-29T13:00Z — ❌ failure (3.11 + 3.12 both FAIL, step "Run all tests (gating — known-drift quarantined)")
- Run 30449062038 — 2026-07-29T11:49Z — ❌ failure
- Run 30442205053 — 2026-07-29T10:04Z — ❌ failure
- Run 30437341538 — 2026-07-29T08:53Z — ❌ failure
- Run 30433254244 — 2026-07-29T07:52Z — ❌ failure

**Earliest confirmed RED run (this query):** 2026-07-28T00:39Z (run 30-run sample all failure — CI RED since at least 36 hours ago).

**Failing run:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/30454089123

**Failing step:** "Run all tests (gating — known-drift quarantined)" — both `test (3.11)` and `test (3.12)` jobs. The "Known-drift tests (non-blocking visibility run)" step passed, meaning the failure is in tests OUTSIDE the quarantine list, i.e. previously-gating tests that have newly broken.

**Likely cause:** AUTHOR_FIX — assertion failures in non-quarantined gating tests. Production behavior changes since the quarantine list was last updated (June 2026) may have invalidated previously-passing tests. Exact test names unavailable (log blob expired before retrieval). CI was path-gated; the July 29 trigger was a merge commit (`5b332d7c`) including `alpha_engine/data/*.json` changes, which matched `alpha_engine/**` path filter.

**Chronic workflows:** None detected in the 30-run global activity sample (all July 29 runs, 29 distinct workflows — zero `cancelled` conclusions visible in the sample).
Note: Full per-workflow chronic scan of all 362 workflows not performed in this run (volume constraint); zero chronic-cancellation signals in visible sample.

**Open PRs RED:** Unable to retrieve per-PR check rollup via list API. 8 open PRs exist (#562, #564, #581, #595, #600, #657, #665, #666, #667) — all from June 2026, last updated 2026-07-13. None of these PRs appear to touch `alpha_engine/` code paths that would explain the current main CI failure. The failure predates all these PRs' last activity.

**Action required:** AUTHOR_FIX — investigate gating test failures on main. Recommended steps:
1. View the failing run logs at the URL above (job "test (3.11)" → step "Run all tests").
2. Identify tests failing outside the known-drift quarantine list in `.github/workflows/ci-tests.yml:102–174`.
3. Either reconcile failing tests with current production behavior and remove them from quarantine, OR add new failures to the quarantine list with a reconciliation TODO.
4. Do NOT size up or promote any trading picks while CI is RED on main.

**Status change vs last monitor entry:** Last recorded verdict was GREEN (2026-05-22 monitor file, latest section). This is the first GHA monitor entry for 2026-07-29. CI has been red since at least 2026-07-28T00:39Z — this is a confirmed, multi-day RED state, not a new regression this hour. No PR comment posted (condition: previous-hour must be GREEN; no previous hour exists in today's file).

---
