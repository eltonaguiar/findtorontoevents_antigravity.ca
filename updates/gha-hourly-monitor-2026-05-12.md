# GHA Hourly Health Monitor — 2026-05-12

## 05:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** Inferred from merged-PR check runs (gh CLI unavailable; direct workflow-run history accessed via MCP check_runs). Last 3 "CI Tests" executions on code PRs all passed — PR #909 (merged 05:00): test(3.11) ✅ test(3.12) ✅; PR #912 (merged 04:58): test(3.11) ✅ test(3.12) ✅; PR #906 (merged 04:58): test(3.11) ✅ test(3.12) ✅. Docs-only merges #915 and #911 triggered scan only (no CI Tests run). **3 success, 0 failure, 0 in_progress — main CI Tests GREEN.**

**Chronic workflows:** none meeting cancellation criteria. Side note: `gate` workflow shows FAILURE on 4/4 recently sampled PRs (#916, #909, #912, #906) with 0 successes visible (run IDs: 25714591174, 25714401989, 25714078856, 25714072817). This is a persistent FAILURE pattern (not cancellation) — PRs are merging regardless, so `gate` appears non-blocking. Warrants operator investigation but does not trip the CHRONIC-cancel threshold.

**Open PRs RED:** #916 "feat(commodity): seasonal supply-demand strategy (PR-I)" — `test (3.12)` FAILURE (run https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/25714591163), `test (3.11)` CANCELLED (matrix cancel-on-failure), `gate` FAILURE (chronic pattern). Action: **AUTHOR_FIX** — 575-line new feature module (USDA seasonal strategy), test failure is likely logic/import in the new module, not infra flake. Author claimed 8/8 tests pass locally; re-check against base-branch drift after today's 9 post-base merges.

**Action required:** Author of PR #916 should rebase onto current main and fix `test (3.12)` failure before merge. Operator should also investigate chronic `gate` failures appearing on every PR.

---

## 06:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5 accessible via MCP check_runs on merged PRs):**
- PR #921 "feat(ml-gatekeeper): A/B router Phase B" (merged 05:39): test(3.11) ✅ test(3.12) ✅ scan ✅ — **3/3 success**
- PR #916 "feat(commodity): seasonal supply-demand strategy" (merged 05:37 **with failing CI**): test(3.11) ❌ FAILURE, test(3.12) cancelled (matrix cancel-on-failure), gate ❌ FAILURE — **merged despite failures**
- PRs #909 / #912 / #906 (from 05:00 report): all test(3.11) ✅ test(3.12) ✅
- **Net: 1 failure in last 5 code PRs (PR #916 test.3.11). PR #921 (post-#916 merge) ran GREEN, suggesting main-branch CI recovered after the bad merge. Conservative verdict: DEGRADED (not RED) because #921 confirms recovery, but regression risk from #916 code remains unverified.**
- 2 direct-to-main pushes at 06:08-06:11 UTC (`feat(anti-overfit)` sha 52dfc50, `feat(quant-rescue)` sha d60a7b2) — CI status not queryable without gh CLI. These bypassed the PR gate entirely.

**Chronic workflows:** none meeting cancellation criteria (0 cancelled runs observed). `gate` workflow continues its persistent FAILURE pattern (seen on PR #916 at 05:34, consistent with 4/4 PRs in 05:00 report). FAILURE ≠ cancellation — does not trip CHRONIC threshold. Non-blocking (PRs merge regardless), but structurally broken.

**Open PRs RED:** none — 0 open PRs as of 06:11 UTC.

**Action required:**
1. Operator should investigate why `gate` fails on every PR — 5+ consecutive failures with 0 successes is a broken workflow, not a flake.
2. Operator should verify that PR #916 (merged with test.3.11 FAILURE) did not introduce a regression on main. PR #921 ran green post-merge but was tested against a different subset of the codebase.
3. Direct-to-main code pushes (anti-overfit, quant-rescue) bypassed CI gates entirely — recommend enforcing branch protection that requires CI Tests to pass before main accepts pushes.
