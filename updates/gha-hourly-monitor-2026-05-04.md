# GHA Hourly Health Monitor — 2026-05-04

## 02:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** UNKNOWN — all recent main-branch commits carry `[skip ci]` (automated bot
data-push commits and docs-only commits). `gh` CLI is unavailable in this environment; the GitHub MCP
toolset does not expose a workflow-run list API, so the last 5 "CI Tests" runs on `main` cannot be
directly enumerated. No main-branch code-push commits were detected in the last 5 commits that would
have triggered `CI Tests`. Absent evidence of failure, main itself is treated as **not-RED**, but
the state cannot be confirmed GREEN either.

> **Tooling note:** `gh` CLI is not installed in this agent environment. All checks in this report
> use GitHub MCP tools (`mcp__github__*`). Per-workflow chronic-cancellation scan (Step 2) and the
> `gh run list` CI Tests history (Step 1) require the `gh` CLI and are therefore **unverifiable**
> this hour. MCP tooling provides PR-level check-run data only.

**Chronic workflows:** UNKNOWN — per-workflow run history unavailable without `gh` CLI. No evidence
collected this hour. (See `fix-gh-actions` skill for manual remediation when `gh` is available.)

**Open PRs RED:**

- **#759** — `fix(sports): admin-auth fallback for sports_picks.php + sports_bets.php`
  - `test (3.11)` ❌ FAILURE (completed 02:03:40Z), `test (3.12)` cancelled (cascade fail-fast)
  - `smoke` ✅ success, `scan` ✅ success, `deploy-guard` ⊘ skipped
  - Run URLs: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/25297385406
  - Classification: **AUTHOR_FIX** — real test failure on Python 3.11, not an infra flake (smoke
    passed cleanly on same run). Author should inspect `test (3.11)` log, fix the failing assertion,
    and push a new commit.
  - Context: PR fixes 50webs shared-hosting `getenv()` auth bug in `sports_picks.php` /
    `sports_bets.php`. The code changes themselves are FTP-verified live; the CI failure is a
    test-suite issue on this branch, not a production regression.

**Positive delta vs 2026-05-03 last entry:**

Previously-failing PRs #597, #608, #615, #661, #723, #733 are **no longer open** (closed or
merged). Open PR count dropped from ≥5 to **1**. This is a significant improvement in overall PR
health.

**Action required:**
- Author of PR #759 should inspect `test (3.11)` failure log and push a fix before requesting merge.
- Operator: if `gh` CLI becomes available in this environment, re-run the monitor to fill in Steps 1
  and 2 (main CI history + per-workflow chronic-cancel scan).

---

## 03:00 UTC

**Verdict:** GREEN

**Main CI Tests (last 5):** Unable to enumerate directly (no `gh` CLI; MCP toolset has no workflow-run-list API). Best available proxy: most recent code PR with CI Tests = **#759**, which passed `test (3.11)` ✅ and `test (3.12)` ✅ (completed ~02:56Z). All recent main commits since then are `[skip ci]` bot/docs pushes. No CI Tests failure evidence on main.

> **Tooling note:** `gh` CLI is not installed in this environment. All checks use GitHub MCP tools (`mcp__github__*`). Per-workflow chronic-cancellation scan (Step 2) and direct `gh run list` CI history (Step 1) are unverifiable. PR-level check-run data is the best available signal.

**Delta vs 02:00 UTC:**
- PR #759 `test (3.11)` failure (logged at 02:00) is **resolved** — both `test (3.11)` ✅ and `test (3.12)` ✅ now show `success` (completed ~02:56Z). PR is CI-green and ready for review/merge.
- 3 new open PRs: #763 (hourly audit doc, scan ✅), #764 (concept scorer, CI in_progress), #769 (personas batch B, scan ✅ drift ✅).
- 5 PRs merged since last report: #765 (BallDontLie adapter), #766 (This Month leak doc), #767 (Highlightly adapter), #768 (TheSportsDB schedule gate), #770 (homepage multi-day filter fix).

**Chronic workflows:** UNKNOWN — per-workflow run history unavailable without `gh` CLI. One `scan` cancellation observed on PR #759 (job id 74161569924); this is a normal superseded-run pattern (new commit pushed to branch), not a chronic signal.

**Open PRs RED:** none

| PR | Title | CI Status |
|----|-------|-----------|
| #759 | fix(sports): admin-auth fallback | test(3.11) ✅ test(3.12) ✅ scan ✅ — GREEN |
| #763 | audit: hourly audit 02Z | scan ✅ (no CI Tests — docs only) |
| #764 | feat(b5): concept-aware scoring shadow mode | test(3.11) ⏳ test(3.12) ⏳ scan ⏳ — IN PROGRESS |
| #769 | feat(personas): ETF/Bond/Futures personas batch B | scan ✅ drift ✅ (no CI Tests — .md only) |

**Action required:** none — monitor PR #764 CI results when jobs complete (~03:15–03:20Z).

---

## 05:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** UNKNOWN — `gh` CLI unavailable; GitHub MCP toolset has no workflow-run-list API. Best proxy: last code PR to run CI Tests on main was **#759** (test(3.11) ✅ test(3.12) ✅, merged 03:20Z). Subsequent merges (#771 audit-03Z at 04:25Z, #773 event-filter-patch at 03:47Z, #774 multiday-cap at 03:55Z, #775 rescue-chip-state at 04:22Z) are docs/HTML-only or carry `[skip ci]` and did not trigger CI Tests. No evidence of a main-branch CI Tests failure.

> **Tooling note:** Same constraint as prior hours — `gh` CLI absent. Steps 1 and 2 use PR check-run data as best available proxy. Verdict is DEGRADED (not GREEN) due to two confirmed RED open PRs, not due to a detected main-branch failure.

**Chronic workflows:** UNKNOWN — per-workflow run history unavailable without `gh` CLI.

**Open PRs RED:**

| PR | Title | CI Status | Classification |
|----|-------|-----------|----------------|
| **#772** | feat(b9): adversarial debate shadow (UEPS emitter) | test(3.11) ❌ FAILURE / test(3.12) cancelled / ueps-pytest cancelled / scan ✅ | **AUTHOR_FIX** |
| **#764** | feat(b5): concept-aware scoring shadow mode | test(3.12) ❌ FAILURE / test(3.11) cancelled / scan ✅ | **AUTHOR_FIX** |

**Other open PRs (not RED):**

| PR | Title | CI Status |
|----|-------|-----------|
| #777 | fix(sports): normalize EST day bucketing after midnight | smoke ⏳ in_progress / scan ⏳ in_progress / deploy-guard ⊘ — PENDING |
| #776 | audit: hourly audit 04Z | scan ✅ (docs-only, no CI Tests) — GREEN |
| #769 | feat(personas): ETF/Bond/Futures personas batch B | scan ✅ drift ✅ (md-only, no CI Tests) — GREEN |

**Failure run links:**
- #772 test(3.11): https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/25299742406/job/74164525488
- #764 test(3.12): https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/25299164868/job/74162949252

**Delta vs 03:00 UTC:**
- PR #772 (adversarial debate shadow) opened at 03:35Z — `test (3.11)` ❌ FAILURE confirmed, cascade-cancelled test(3.12) and ueps-pytest. AUTHOR_FIX required.
- PR #764 (concept scorer) CI resolved: `test (3.12)` ❌ FAILURE (completed 03:16Z), `test (3.11)` cascade-cancelled. Still RED. AUTHOR_FIX required.
- PR #777 (sports EST date bucketing) opened at 04:35Z — smoke + scan in_progress, no CI Tests check present (sports-smoke workflow only).
- PRs merged since 03:00Z: #771 (audit 03Z, 04:25Z) and #775 (rescue chip-state, 04:22Z) — both docs/HTML, no CI Tests triggered.
- Note: PR #772 also carries explicit **DO NOT ADMIN-MERGE** flag in body — awaiting human review regardless of CI status.

**Action required:**
- **#772 author:** inspect `test (3.11)` failure log and push a fix. Also requires explicit human review sign-off before merge.
- **#764 author:** inspect `test (3.12)` failure log and push a fix before merge.
- Monitor PR #777 CI completion (smoke/scan in_progress as of this report run).
