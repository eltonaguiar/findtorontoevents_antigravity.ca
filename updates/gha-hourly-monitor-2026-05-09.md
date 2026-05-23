# GHA Hourly Health Monitor — 2026-05-09

## 03:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** UNKNOWN — `gh` CLI unavailable in this environment; GitHub MCP tools do not expose the `/actions/runs` endpoint. All recent commits to main carry `[skip ci]` (bot picks/scan commits), so CI Tests has not been triggered by a code merge in the observable window. Inference from PR check-runs: the last 3 merged PRs (#864, #863, #861) were doc-only and only ran the `scan` job (success). No Python-test-matrix failures have landed on main. **No known RED on main**, but cannot confirm last-5 CI Tests SUCCESS chain — hence DEGRADED rather than GREEN.

**Chronic workflows:** UNKNOWN — per-workflow `--limit 15` run history requires `gh run list --workflow`, which is unavailable. From PR check-run sampling: `scan` consistently succeeds across all recent PRs; `drift` passes on #846; `test (3.11)` / `test (3.12)` matrix only appeared on #862 (unmerged, see below). No chronic-cancellation signal detectable from available data.

**Open PRs RED:**
- **#862** `findings/db-query-bank-2026-05-07` — `test (3.11)` = **FAILURE**, `test (3.12)` = **cancelled** (2026-05-08T04:10Z). Classification: **AUTHOR_FIX** — PR #865's triage note confirms this is a real test failure, not infra flake ("HOLD — CI not green"). Author should fix the failing test(s) in `tools/db_query_bank_2026-05-07.py` / `tools/db_query_bank_secondary_2026-05-07.py` before merging. Run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/25536096031

**Open PRs GREEN (scan-only, doc or template PRs):**
- **#865** `audit/hourly-2026-05-08-05z` — scan ✅ (doc-only)
- **#866** `feat/swarmwithprework-skill-2026-05-08` — scan ✅
- **#867** `verify/rapid-fire-pair-block-2026-05-08` — scan ✅
- **#846** `feat/b18-shadow-probation-panel-2026-05-06` — scan ✅ drift ✅ (HOLD: "DO NOT ADMIN-MERGE" flag — awaiting human review, not a CI issue)

**Open PRs SKIPPED:**
- **#849** — draft (Copilot); excluded per checklist

**Most recently merged PR:** #864 — *chore(loop): V1-V7 re-verified 2026-05-08 04:17 UTC* (merged 2026-05-08T05:11Z, scan ✅ only)

**Action required:** Author of #862 should fix `CI Tests` failures before that PR can be considered for merge. No action on main branch itself — no confirmed failures.

---

## 05:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** UNKNOWN — `gh` CLI unavailable; MCP tools do not expose `/actions/runs`. All commits on main since the previous run carry `[skip ci]` (bot picks/scan commits: forward-test resolver, strategy-health, pick-monitor, meme-scanner, Claude Gainer ST/ML, Rapid Fire, Sustained Gainer, prediction-market signals, daily feed). Neither of the two code PRs merged at 03:13 UTC (#866 swarmwithprework, #867 rapid-fire verification) triggered CI Tests — both were scan-only. No Python-test-matrix CI Tests run has touched main in the observable window. **No known RED on main**, but cannot confirm last-5 CI Tests success chain — DEGRADED maintained.

**Chronic workflows:** UNKNOWN — per-workflow `--limit 15` run history requires `gh run list --workflow`, which is unavailable. `scan` check consistently passing on all 7 open PRs sampled. No chronic-cancellation signal detectable from available data.

**Open PRs RED:**
- **#862** `findings/db-query-bank-2026-05-07` — `test (3.11)` = **FAILURE**, `test (3.12)` = **cancelled** (2026-05-08T04:10Z). Classification: **AUTHOR_FIX** — real test logic failure confirmed by multiple audit-PR triage notes. Fix `tools/db_query_bank_2026-05-07.py` / secondary runner before merge. Run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/25536096031 *(persistent — unchanged from 03:00 UTC)*
- **#868** `feat/b13-per-class-regime-filter-2026-05-09` — `test (3.12)` = **FAILURE**, `test (3.11)` = **cancelled** (2026-05-09T03:23Z). Classification: **AUTHOR_FIX** — new code PR opened at 03:19 UTC; PR body notes 56/57 tests passing (`test_smart_gate_uses_strategy_score_overrides_for_proven_non_crypto` was 1 pre-existing failure on main, but `test (3.12)` failure suggests an additional breakage on Python 3.12 not visible in the 3.11 self-test run). PR is flagged "DO NOT ADMIN-MERGE — awaiting human review". Run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/25590267982

**Open PRs GREEN (scan-only, doc or template PRs):**
- **#870** `audit/hourly-2026-05-09-03z` — scan ✅ (doc-only audit report)
- **#869** `docs/loop-2026-05-09` — scan ✅ (docs-only queue update)
- **#865** `audit/hourly-2026-05-08-05z` — scan ✅ (doc-only, behind main)
- **#846** `feat/b18-shadow-probation-panel-2026-05-06` — scan ✅ (HOLD: "DO NOT ADMIN-MERGE")

**Open PRs SKIPPED:**
- **#849** — draft (Copilot); excluded per checklist

**Most recently merged PR:** #867 — *verify: rapid_fire pair-block fix week-1 follow-up — GATE_REGRESSION* (merged 2026-05-09T03:13Z, scan ✅ only); #866 merged same minute.

**Action required:**
- **#862** — author fix required (persistent test failure, no CI improvement since 03:00 UTC)
- **#868** — author should investigate `test (3.12)` failure before requesting merge; the PR description's 56/57 passing claim was against Python 3.11 and may not hold on 3.12

---

> **Tool note:** `gh` CLI is not installed in this environment. Steps 1 and 2 of the checklist (direct `gh run list` queries) were approximated using GitHub MCP `pull_request_read:get_check_runs` against recent PRs. If the hourly monitor is a recurring fixture, install `gh` in the runner for full workflow-run history access.
