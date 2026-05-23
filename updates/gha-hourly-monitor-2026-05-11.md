# GHA Hourly Health Monitor — 2026-05-11

## 03:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** N/A — all 10 recent main commits carry `[skip ci]` (bot scanner commits). CI Tests workflow not triggered on main in this monitoring window. Last full test-suite runs visible only on feature PR branches.

**Chronic workflows:** none — `test (3.12)` cancellations seen on feature PRs are matrix fail-fast side-effects of `test (3.11)` failures, not independent chronic cancellations. No workflow meets the 4-cancel / 0-success / no-48h-success threshold per the per-workflow fixed methodology.

**Open PRs RED** (10 sampled of 18 open; remaining expected to match per prior audit reports):

| PR | CI check results | Classification | Recommended action |
|----|-----------------|---------------|--------------------|
| #862 | test(3.11) ❌ FAIL · test(3.12) ❌ CANCEL · scan ✅ | AUTHOR_FIX | Systemic fixture/dep break |
| #876 | test(3.11) ❌ CANCEL · test(3.12) ❌ FAIL · gate ❌ FAIL · scan ✅ | AUTHOR_FIX | Walkforward gate + test |
| #877 | test(3.11) ❌ CANCEL · test(3.12) ❌ FAIL · gate ❌ FAIL · scan ✅ | AUTHOR_FIX | Walkforward gate + test |
| #878 | test(3.11) ❌ CANCEL · test(3.12) ❌ FAIL · gate ❌ FAIL · scan ✅ | AUTHOR_FIX | Walkforward gate + test |
| #883 | test(3.11) ❌ FAIL · test(3.12) ❌ CANCEL · scan ✅ · audit ✅ | AUTHOR_FIX | Systemic fixture/dep break |
| #884 | test(3.11) ❌ FAIL · test(3.12) ❌ CANCEL · gate ❌ FAIL · scan ✅ | AUTHOR_FIX | Walkforward gate + test |
| #885 | test(3.11) ❌ FAIL · test(3.12) ❌ CANCEL · gate ❌ FAIL · scan ✅ | AUTHOR_FIX | Walkforward gate + test |
| #887 | test(3.11) ❌ FAIL · test(3.12) ❌ CANCEL · scan ✅ · audit ✅ | AUTHOR_FIX | Systemic fixture/dep break |
| #891 | test(3.11) ❌ FAIL · test(3.12) ❌ CANCEL · gate ❌ FAIL · scan ✅ | AUTHOR_FIX | Walkforward gate + test |
| #895 | no check runs (0) | NEEDS PUSH | Force-push branch to trigger CI |

**PRs with no failures (scan-only, no full test suite triggered):**
- #896 (audit doc PR): scan ✅ only — no `test (3.11)` triggered by design on audit branches

**PRs not sampled this run** (expect same pattern per prior audit reports PR #894/#888): #873, #879, #881, #890, #892, #893, #846 (dirty), #849 (draft)

**Failure root cause note:** The `test (3.11)` failure is systemic across unrelated PRs from different sessions (first confirmed in PR #862 opened 2026-05-08). The `gate` failures on alpha_engine/** PRs are a separate pre-existing issue (10 strategies with 100% bt_wr but missing walkforward results). Both are AUTHOR_FIX, not infra flake.

**Action required:** Author should open a dedicated root-cause fix PR for the systemic `test (3.11)` break (shared fixture or dependency regression). All 14+ feature PRs in the merge queue are blocked until resolved. The `gate` failures on alpha_engine/** PRs require per-PR walkforward result population before those PRs can merge.

---
*Monitor run: 2026-05-11T03:10 UTC | Tooling: GitHub MCP API (gh CLI unavailable in this environment) | Baseline: first run of the day, no prior section to compare*

## 05:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** N/A — all recent main commits carry `[skip ci]` (bot scanner commits: Claude Gainer ML scan, Sustained Gainer scan, GSD Edge Engine auto-update, Scanner data update). CI Tests workflow not triggered on main in this window. Pattern unchanged from 03:00 UTC.

**Chronic workflows:** none — no workflow meets the chronic threshold (≥4 cancels, 0 successes, no 48h success). `test (3.12)` cancellations on feature PRs remain fail-fast matrix side-effects of `test (3.11)` failures. Unchanged from 03:00 UTC.

**Open PRs RED** (20 open PRs total; new PRs since 03Z checked, existing PRs sampled):

| PR | Opened | CI check results | Classification | Recommended action |
|----|--------|-----------------|---------------|--------------------|
| #900 | 04:37Z (NEW) | test(3.11) ❌ FAIL · test(3.12) ❌ CANCEL · scan ✅ | AUTHOR_FIX | Systemic test(3.11) fixture break |
| #898 | 03:34Z (NEW) | test(3.11) ❌ FAIL · test(3.12) ❌ CANCEL · scan ✅ · audit ✅ | AUTHOR_FIX | Systemic test(3.11) fixture break |
| #891 | 05-10 | test(3.11) ❌ FAIL · test(3.12) ❌ CANCEL · gate ❌ FAIL · scan ✅ | AUTHOR_FIX | Walkforward gate + systemic break |
| #884 | 05-10 | test(3.11) ❌ FAIL · test(3.12) ❌ CANCEL · gate ❌ FAIL · scan ✅ | AUTHOR_FIX | Walkforward gate + systemic break |
| #895 | 05-10 | no check runs (0) | NEEDS PUSH | Re-push branch to trigger CI |
| #876–#887 | 05-09/10 | test(3.11) ❌ FAIL (unchanged from 03Z) | AUTHOR_FIX | Systemic fixture/dep break |
| #862, #873, #879, #881, #892, #893, #846, #849 | 05-08/09 | Unchanged from 03Z | AUTHOR_FIX / DRAFT | See 03Z section |

**PRs with clean CI (no test(3.11) triggered by design):**
- #899 (04Z audit doc, opened 04:25Z): scan ✅ only — docs-only branch, no test matrix triggered
- #897: MERGED at 04:17Z (03Z audit doc — removed from open set)

**Delta since 03Z:**
- 3 new open PRs: #900, #899, #898
- 1 PR merged (closed): #897
- Systemic `test (3.11)` failure confirmed on both new code PRs (#900, #898) — consistent with prior assessment that root cause is a shared fixture/dependency regression, not per-PR code

**Action required:** Systemic `test (3.11)` root-cause fix PR still outstanding — all 18 open feature PRs with code changes remain blocked. No new actions required beyond what was stated at 03:00 UTC. PR #895 branch owner should push a commit to trigger CI.

---
*Monitor run: 2026-05-11T05:09 UTC | Tooling: GitHub MCP API (gh CLI unavailable in this environment) | Verdict unchanged: DEGRADED → DEGRADED, no commit escalation triggered*
