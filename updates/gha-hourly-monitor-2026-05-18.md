# GHA Hourly Health Monitor — 2026-05-18

## 05:00 UTC

**Verdict:** GREEN ✅

**Main CI Tests (last 5):** Inferred from PR branch check runs (MCP-only environment — no `gh run list` access). Most recent code PRs to trigger CI Tests:

| Check | PR #1232 (merged 05:08Z) | PR #1231 (open, created 05:05Z) |
|---|---|---|
| test (3.11) | in_progress (started 05:07Z) | in_progress (started 05:06Z) |
| test (3.12) | in_progress (started 05:07Z) | in_progress (started 05:06Z) |
| gate | in_progress (started 05:07Z) | — |
| scan | ✅ success (05:10Z) | ✅ success (05:08Z) |
| Gitleaks secret scan | ✅ success (05:10Z) | ✅ success (05:08Z) |
| Grep for stale DB passwords | ✅ success (05:10Z) | ✅ success (05:08Z) |

All other PRs merged since 03:00 UTC (#1229, #1230, #1225, #1228, #1220, #1219, #1218, #1217, #1216, #1215, #1214, #1213, #1212, #1211) only triggered the 3 lightweight security gate checks — all **success**. None triggered CI Tests (docs/data/research/workflow paths only).

No CI Tests `failure` or `cancelled` conclusion observed anywhere in the scan window. Verdict: **GREEN** (0 failures / 0 in last 5 CI Tests completions — 0 completed runs means no RED trigger; currently all in_progress with no failures).

**Chronic workflows:** None confirmed. Per-workflow run history is not queryable via MCP tools (requires `gh run list --workflow`). No cancellation conclusions observed in any check run across all scanned PRs. Threshold not triggered.

**Open PRs CI status:**

| PR | Title | CI Status | Classification |
|---|---|---|---|
| #1231 | fix(actions): concurrency cancel-in-progress on 4 push gates | test(3.11)=in_progress, test(3.12)=in_progress, scan ✅, Gitleaks ✅, DB-grep ✅ | PENDING — no failure yet; CI Tests expected to complete ~05:25Z |

**Open PRs RED:** none. PR #1231 CI Tests still running; no failure observed.

**⚠️ Advisory — fast-merge pattern (continued from 2026-05-17):** PR #1232 ("feat(gates): book-level direction-conflict reconciler") was merged at 05:08:25Z. Its CI Tests jobs (`test (3.11)`, `test (3.12)`, `gate`) started at 05:07:49Z — only 36 seconds before the merge. CI Tests cannot complete in 36 seconds (typical runtime 10–18 min). The PR was merged before its test suite ran. This is the same pattern flagged at 10:00Z yesterday (#1154 etc.). CI Tests is **not functioning as a merge gate** for code PRs.

**Most recently merged PR:** #1232 ("feat(gates): book-level direction-conflict reconciler", merged 05:08:25Z).

**Action required:** none on main CI. Advisory: operator should enable branch protection requiring CI Tests pass before merge to prevent fast-merge bypass of the test gate.

**Run context:** First entry for today — no previous section to diff. New file committed.

---

## 06:00 UTC

**Verdict:** GREEN ✅

**Main CI Tests (last 5):** All completed CI Tests runs are success. Confirmed results since 05:00 UTC scan:

| Check | PR #1231 (merged 05:16Z) | PR #1232 (merged 05:08Z) |
|---|---|---|
| test (3.11) | ✅ success (05:06–05:13Z) | ✅ success (05:07–05:15Z) |
| test (3.12) | ✅ success (05:06–05:16Z) | ✅ success (05:07–05:18Z) |
| gate | — | ✅ success (05:07–05:28Z) |
| scan | ✅ success | ✅ success |
| Gitleaks secret scan | ✅ success | ✅ success |
| Grep for stale DB passwords | ✅ success | ✅ success |

PR #1234 (audit/research, merged 06:16Z) did not trigger CI Tests — only the 3 lightweight security checks fired (all ✅). Consistent with path filters excluding docs/research/tools from `ci-tests.yml`. No CI Tests `failure` or `cancelled` conclusion in any recent run.

**Chronic workflows:** None confirmed. No cancellation conclusions observed in check runs across all scanned PRs. PR #1231 (concurrency fix) is now merged — `cancel-in-progress: true` is active on 4 gate workflows going forward; any future cancellations on superseded pushes are expected behavior, not chronic failure.

**Open PRs CI status:** No open PRs. (0 open PRs at scan time.)

**Open PRs RED:** none.

**Updates since 05:00Z:**
- PR #1231 (concurrency cancel-in-progress fix): merged 05:16Z with CI Tests fully green (tests finished before merge — properly gated ✅).
- PR #1232 CI Tests completed post-merge: test(3.11) ✅ 05:15Z, test(3.12) ✅ 05:18Z, gate ✅ 05:28Z. All passed; no regression on main.
- PR #1234 (audit/research): merged 06:16Z — docs/tools only, no CI Tests triggered.
- Advisory carried forward: fast-merge bypass on code PRs remains unmitigated (PR #1232 was still merged 36s after CI start). PR #1231's concurrency fix reduces wasted minutes on redundant runs but does not enforce a pass-before-merge gate.

**Most recently merged PR:** #1234 ("audit(hourly-05z): 2026-05-18 per-asset PF/WR + P1 FUTURES catastrophic finding", merged 06:16Z).

**Action required:** none. GREEN unchanged from 05:00Z. Ongoing advisory: operator should enable branch protection requiring CI Tests pass before merge.

**Run context:** Verdict unchanged GREEN→GREEN. No commit required (no status change, no chronic-workflow list change).

---

## 07:00 UTC

**Verdict:** GREEN ✅

**Main CI Tests (last 5):** All completed CI Tests runs are success. Confirmed results from 06:00–07:17Z scan:

| Check | PR #1237 (merged 06:37Z) | PR #1232 (merged 05:08Z) | PR #1231 (merged 05:16Z) |
|---|---|---|---|
| test (3.11) | ✅ success (06:33Z) | ✅ success (05:15Z) | ✅ success (05:13Z) |
| test (3.12) | ✅ success (06:36Z) | ✅ success (05:18Z) | ✅ success (05:16Z) |
| gate | — | ✅ success (05:28Z) | — |
| scan | ✅ success | ✅ success | ✅ success |
| Gitleaks secret scan | ✅ success | ✅ success | ✅ success |
| Grep for stale DB passwords | ✅ success | ✅ success | ✅ success |

PR #1238 (audit/hourly-06z, merged 07:11Z) is docs/audit path only — 3 lightweight security checks all ✅ success; CI Tests not triggered (expected per path filter).

No CI Tests `failure` or `cancelled` conclusion observed in any run.

**✅ Positive note — PR #1237 properly gated:** `feat/regime-conditional-harness` merged at 06:37:41Z. test(3.11) completed 06:33:34Z and test(3.12) completed 06:36:50Z — both finished before merge. First properly-gated code PR observed this session; contrast with the fast-merge pattern on #1232 (merged 36s after CI start).

**Chronic workflows:** None confirmed. No cancellation conclusions observed in check runs across all scanned PRs. Concurrency fix (PR #1231) remains active.

**Open PRs CI status:** 0 open PRs. Nothing to classify.

**Open PRs RED:** none.

**Updates since 06:00Z:**
- PR #1237 (feat/regime-conditional-harness): merged 06:37Z — code PR, CI Tests passed before merge ✅ properly gated.
- PR #1238 (audit/hourly-06z): merged 07:11Z — docs only, security checks ✅.

**Most recently merged PR:** #1238 ("audit(hourly-06z): 2026-05-18 per-asset PF/WR + dashboard staleness alert", merged 07:11:56Z).

**Action required:** none. GREEN unchanged from 06:00Z. Ongoing advisory: operator should enable branch protection requiring CI Tests pass before merge.

**Run context:** Verdict unchanged GREEN→GREEN. No commit (no status change, no chronic-workflow list change).

---
