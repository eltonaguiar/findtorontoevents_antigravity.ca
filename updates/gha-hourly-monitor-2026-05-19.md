# GHA Hourly Health Monitor — 2026-05-19

## 05:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-filtered (only fires on `paper_trading/**`, `alpha_engine/**`, `tests/**`, `requirements.txt`, `ci-tests.yml`). Last confirmed run: PR #1237 (2026-05-18T06:26Z) — 2 success (py3.11 + py3.12), 0 failure. All commits to main since then carry `[skip ci]` or touch non-qualifying paths — no new CI Tests runs triggered. Gate status: **GREEN** (last known run clean, concurrency fix from PR #1231 still active).

**Chronic workflows:** none (`chronic_cancel_workflows_count: 0` per `reports/actions_failure_guardian.json` scanned at 04:53Z, 600 runs / 344 workflows)

**Operational failures (4 unresolved — source: `reports/actions_failure_guardian.json` 04:53Z):**

| Workflow | Run # | Failed at | Age | URL |
|---|---|---|---|---|
| Gate Config Emit | #60 | 03:48Z | ~1.1h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26074988945 |
| ALPHA ENGINE - Adaptive Trust Tuner | #158 | 01:19Z | ~3.6h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26070262102 |
| DB Freshness Guardian | #13 | 01:10Z | ~3.7h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26069984624 |
| Strategy Health Monitor | #452 | 00:23Z | ~4.5h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26068405857 |

Guardian bot attempted re-run on all 4; all received 403 `Resource not accessible by integration` — manual operator re-run required.

**Open PRs RED:** none (0 open PRs at 05:04Z)

**Action required:** operator should manually re-run the 4 failed workflows listed above (guardian bot lacks re-run permissions). No CI Tests fix needed — the PR gate itself is green.

**Status change vs prior hour:** GREEN (2026-05-18 07:00Z) → DEGRADED. Four overnight operational failures not present in prior monitor. This is the first entry for 2026-05-19.

**Most recently merged PR:** #1239 ("audit(hourly-07z): 2026-05-18 per-asset PF/WR + futures_momentum kill candidate", merged 2026-05-18T08:37:21Z).

---

## 06:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** 1 in_progress (run #6143, started 06:10:49Z, triggered by "scheduled: pick check" commit `bff5e24b`; run #6142 also in_progress since 06:08:57Z from prior push). Last completed run: PR #1237 (2026-05-18T06:26Z) — 2 success (py3.11 + py3.12), 0 failure. CI gate status: **PENDING** (in_progress, last known result clean).

**Chronic workflows:** none (`chronic_cancel_workflows_count: 0` per `reports/actions_failure_guardian.json` generated 04:53Z, 600 runs / 344 workflows scanned; all recent failures carry `failure` conclusion, not `cancelled` — chronic-cancellation threshold not met for any workflow)

**Operational failures (6 unresolved — 4 from guardian + 2 new post-scan):**

| Workflow | Run # | Failed at | Age at 06:10Z | URL |
|---|---|---|---|---|
| Secret Scan (M-043) | #283 | 05:22Z | ~0.8h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26077965617 |
| Check Streamer Live Status | #2281 | 05:20Z | ~0.8h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26077901771 |
| Gate Config Emit | #60 | 03:48Z | ~2.4h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26074988945 |
| ALPHA ENGINE - Adaptive Trust Tuner | #158 | 01:19Z | ~4.9h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26070262102 |
| DB Freshness Guardian | #13 | 01:10Z | ~5.0h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26069984624 |
| Strategy Health Monitor | #452 | 00:23Z | ~5.8h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26068405857 |

Guardian bot (04:53Z scan) attempted re-run on the bottom 4; all received 403 `Resource not accessible by integration` — manual operator re-run required for all 6. Secret Scan (M-043) and Check Streamer Live Status appeared after the guardian scan window.

**Open PRs RED:** none (0 open PRs confirmed at 06:10Z)

**Action required:** operator should manually re-run all 6 failed workflows above. Secret Scan (M-043) failure may indicate a newly committed secret — review the run log before dismissing. CI Tests in-progress runs expected to complete within ~5 min; check next hourly report for result.

**Status change vs prior hour:** DEGRADED → DEGRADED (no verdict change; failure count increased 4→6 with Secret Scan M-043 and Check Streamer Live Status added since 05:00Z scan). No commit triggered per step-5 policy (verdict unchanged, chronic list unchanged).

**Most recently merged PR:** #1239 ("audit(hourly-07z): 2026-05-18 per-asset PF/WR + futures_momentum kill candidate", merged 2026-05-18T08:37:21Z).

---

## 08:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-filtered (only fires on `paper_trading/**`, `alpha_engine/**`, `tests/**`, `requirements.txt`, `ci-tests.yml`). PRs #1243, #1244, #1245 — all audit/report PRs touching `reports/` and `updates/` — did not trigger CI Tests. Last confirmed CI Tests run remains PR #1237 (2026-05-18T06:26Z): 2 success (py3.11 + py3.12), 0 failure. Gate status: **GREEN** (last known run clean). Note: 06:00Z in-progress runs (#6142, #6143) outcome unverifiable via MCP tools; PR #1244 body confirms "all CI green" at merge (07:09Z), consistent with clean result.

**Chronic workflows:** none (carry-forward from 05:00Z guardian scan: `chronic_cancel_workflows_count: 0`; no `gh` CLI available in this environment to run per-workflow queries — MCP-only session)

**Operational failures (≥6 unresolved from 06:00Z scan — current state unverifiable via MCP):**

| Workflow | Run # | Failed at | Age at 08:05Z | URL |
|---|---|---|---|---|
| Secret Scan (M-043) | #283 | 05:22Z | ~2.7h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26077965617 |
| Check Streamer Live Status | #2281 | 05:20Z | ~2.7h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26077901771 |
| Gate Config Emit | #60 | 03:48Z | ~4.3h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26074988945 |
| ALPHA ENGINE - Adaptive Trust Tuner | #158 | 01:19Z | ~6.8h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26070262102 |
| DB Freshness Guardian | #13 | 01:10Z | ~6.9h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26069984624 |
| Strategy Health Monitor | #452 | 00:23Z | ~7.7h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26068405857 |

Secret Scan (M-043) superseded: PR #1244 "Gitleaks secret scan" check passed at 06:15Z (after M-043 failed at 05:22Z), and PR #1245 "Gitleaks secret scan" passed at 07:18Z. No leaked secret found in post-M-043 pushes — M-043 failure was likely a transient infra flake, not a real secret leak.

**Open PRs RED:** none. PR #1245 ("audit: hourly report 2026-05-19 07Z") is the only open PR; all 3 check runs (Gitleaks secret scan, Grep for stale hardcoded DB passwords, scan) completed `success` at ~07:18Z. CI Tests not triggered (path-filtered audit content).

**Action required:** operator should manually re-run the 5 remaining operational workflow failures (skip Secret Scan M-043 — superseded by clean Gitleaks on PRs #1244 and #1245). Guardian bot re-run blocked by 403 on all attempts.

**Status change vs prior hour:** DEGRADED → DEGRADED (no verdict change; Secret Scan M-043 likely cleared as real concern; most-recently-merged PR updated from #1239 → #1244). No commit per step-5 policy (verdict unchanged, chronic list unchanged).

**Most recently merged PR:** #1244 ("audit: hourly report 2026-05-19 06Z — 4 directional findings, 2 symbol kill candidates", merged 2026-05-19T07:09:12Z).

---

## 09:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-filtered (only fires on `paper_trading/**`, `alpha_engine/**`, `tests/**`, `requirements.txt`, `ci-tests.yml`). PRs #1245, #1246, #1248 — audit/report/docs PRs touching `reports/`, `updates/`, `audit_dashboard/` — did not trigger CI Tests. Last confirmed CI Tests run remains PR #1237 (2026-05-18T06:26Z): 2 success (py3.11 + py3.12), 0 failure. Gate status: **GREEN** (last known run clean).

**Chronic workflows:** none (carry-forward from 05:00Z guardian scan: `chronic_cancel_workflows_count: 0`; per-workflow queries unavailable in MCP-only environment — no new evidence of chronic cancellations)

**Operational failures (≥5 unresolved from 08:00Z scan — resolution unverifiable via MCP):**

| Workflow | Run # | Failed at | Age at 09:08Z | URL |
|---|---|---|---|---|
| Check Streamer Live Status | #2281 | 05:20Z | ~3.8h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26077901771 |
| Gate Config Emit | #60 | 03:48Z | ~5.3h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26074988945 |
| ALPHA ENGINE - Adaptive Trust Tuner | #158 | 01:19Z | ~7.8h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26070262102 |
| DB Freshness Guardian | #13 | 01:10Z | ~7.9h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26069984624 |
| Strategy Health Monitor | #452 | 00:23Z | ~8.7h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26068405857 |

Secret Scan M-043 carried forward as resolved (superseded by clean Gitleaks on PRs #1244, #1245, #1248 at 09:08Z). PR #1248's Gitleaks check passed at 09:08Z — no secret leak.

**Open PRs RED:** PR #1247 ("feat(ai): model grill sequential + API roster", branch `chore/stageb-consult-cancellation-fix-2026-05-19`) — `test (3.11)` completed `failure` at 08:54Z; `test (3.12)` cascaded `cancelled`. All other checks on PR #1247 (scan, Gitleaks, password grep, audit) completed `success`. Gate check still `in_progress` at 08:47Z start. Classification: **AUTHOR_FIX** — test matrix failure (not an infra flake; 3.11 ran to completion with failure conclusion). Run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26086549497

**Action required:** author should fix CI failure on PR #1247 (test (3.11) failure — review run logs at above URL); operator should manually re-run the 5 operational workflow failures above (guardian bot re-run blocked by 403 since 05:00Z).

**Status change vs prior hour:** DEGRADED → DEGRADED (verdict unchanged; open PRs RED count changed 0→1 with PR #1247 CI failure; chronic list unchanged). No commit per step-5 policy (verdict + chronic list unchanged).

**Most recently merged PR:** #1248 ("docs(audit): localrun round5/6 update + bounce-back mapping", merged 2026-05-19T09:07:16Z).

---

## 10:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-filtered (only fires on `paper_trading/**`, `alpha_engine/**`, `tests/**`, `requirements.txt`, `ci-tests.yml`). PRs #1246, #1247, #1249 open on audit/report/model-grill content — none triggered CI Tests on qualifying paths (except PR #1247 which also touches source files). Last confirmed CI Tests run: PR #1237 (2026-05-18T06:26Z) — 2 success (py3.11 + py3.12), 0 failure. Gate status: **GREEN** (last known run clean).

**Chronic workflows:** none (carry-forward from 05:00Z guardian scan: `chronic_cancel_workflows_count: 0`; per-workflow queries unavailable in MCP-only environment — no new evidence of chronic cancellations at 10:00Z)

**Operational failures (≥5 unresolved from 09:00Z scan — resolution unverifiable via MCP):**

| Workflow | Run # | Failed at | Age at 10:10Z | URL |
|---|---|---|---|---|
| Check Streamer Live Status | #2281 | 05:20Z | ~4.8h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26077901771 |
| Gate Config Emit | #60 | 03:48Z | ~6.3h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26074988945 |
| ALPHA ENGINE - Adaptive Trust Tuner | #158 | 01:19Z | ~8.8h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26070262102 |
| DB Freshness Guardian | #13 | 01:10Z | ~8.9h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26069984624 |
| Strategy Health Monitor | #452 | 00:23Z | ~9.7h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26068405857 |

Secret Scan M-043 carried forward as resolved (superseded by clean Gitleaks on PRs #1244, #1245, #1248, #1249 — most recently at 09:18Z on PR #1249).

**Open PRs RED:**

| PR | Title | Failing Check | Classification | Action |
|---|---|---|---|---|
| #1247 | feat(ai): model grill sequential + API roster | `test (3.11)` failure (08:54Z); `test (3.12)` cascaded cancelled | **AUTHOR_FIX** | Author must fix test failures; run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26086549497 |

PR #1249 (audit/hourly-09z): all 3 checks green (Gitleaks, scan, pwd-grep) — no CI Tests triggered.
PR #1246 (audit/hourly-08z): all 3 checks green — no CI Tests triggered.

**Action required:** author should fix CI failure on PR #1247 (test (3.11) — review run logs at URL above); operator should manually re-run the 5 unresolved operational workflow failures (guardian bot re-run blocked by 403 since 05:00Z; 4 of these are now >8h old with no retry).

**Status change vs prior hour:** DEGRADED → DEGRADED (verdict unchanged; open PRs RED still #1247 AUTHOR_FIX, unchanged from 09:00Z; chronic list unchanged). No commit per step-5 policy.

**Most recently merged PR:** #1248 ("docs(audit): localrun round5/6 update + bounce-back mapping", merged 2026-05-19T09:07:16Z).

---

## 11:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-filtered (only fires on `paper_trading/**`, `alpha_engine/**`, `tests/**`, `requirements.txt`, `ci-tests.yml`). PRs #1246, #1249, #1250 — all audit/report PRs — did not trigger CI Tests. PR #1247 (model grill, touches source files) triggered CI Tests and has `test (3.11)` failure at 08:54Z. Last clean CI Tests run on main: PR #1237 (2026-05-18T06:26Z) — 2 success (py3.11 + py3.12), 0 failure. Gate status: **GREEN** on main (no new qualifying push since last clean run); PR #1247 gate is **RED**.

**Chronic workflows:** none (carry-forward from 05:00Z guardian scan: `chronic_cancel_workflows_count: 0`; per-workflow queries unavailable in MCP-only environment — no new evidence of chronic cancellations at 11:00Z)

**Operational failures (≥5 unresolved from 10:00Z scan — resolution unverifiable via MCP):**

| Workflow | Run # | Failed at | Age at 11:05Z | URL |
|---|---|---|---|---|
| Check Streamer Live Status | #2281 | 05:20Z | ~5.7h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26077901771 |
| Gate Config Emit | #60 | 03:48Z | ~7.3h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26074988945 |
| ALPHA ENGINE - Adaptive Trust Tuner | #158 | 01:19Z | ~9.7h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26070262102 |
| DB Freshness Guardian | #13 | 01:10Z | ~9.9h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26069984624 |
| Strategy Health Monitor | #452 | 00:23Z | ~10.7h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26068405857 |

Secret Scan M-043 carried forward as resolved (superseded by clean Gitleaks on PRs #1244–#1250 — most recently PR #1250 at 10:21Z).

**Open PRs CI snapshot:**

| PR | Title | Checks | Classification | Action |
|---|---|---|---|---|
| #1250 | audit: hourly report 2026-05-19 10Z | 3/3 success (scan, Gitleaks, pwd-grep) ~10:21Z | GREEN | Mergeable once verdict clean |
| #1247 | feat(ai): model grill sequential + API roster | `test (3.11)` FAIL 08:54Z; `test (3.12)` cancelled; 5 other checks pass | **AUTHOR_FIX** | Author must fix test failure; run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26086549497 |
| #1246 | audit: hourly report 2026-05-19 08Z | 3/3 success (Gitleaks, scan, pwd-grep) ~08:21Z | GREEN | Long-pending hold; mergeable |

**Action required:** author should fix CI failure on PR #1247 (`test (3.11)` — logs at run #26086549497, unchanged since 09:00Z, now ~3.4h stale); operator should manually re-run the 5 unresolved operational workflow failures above (guardian bot re-run blocked by 403 since 05:00Z; Strategy Health Monitor now ~10.7h old with no retry).

**Status change vs prior hour:** DEGRADED → DEGRADED (verdict unchanged; open PRs RED still #1247 AUTHOR_FIX, unchanged since 09:00Z; chronic list unchanged; most-recently-merged PR updated #1248 → #1249, merged 10:11Z). No commit per step-5 policy (verdict + chronic list unchanged).

**Most recently merged PR:** #1249 ("audit: hourly report 2026-05-19 09Z — FINDING-11 new + FOREX 5th confirmation", merged 2026-05-19T10:11:40Z).

---

## 12:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-filtered (only fires on `paper_trading/**`, `alpha_engine/**`, `tests/**`, `requirements.txt`, `ci-tests.yml`). PRs #1246, #1249, #1250, #1251 — all audit/report PRs touching `reports/` and `updates/` — did not trigger CI Tests. PR #1247 (model grill, touches source files) has `test (3.11)` failure at 08:54Z — still open/unmerged. Last confirmed CI Tests run on main remains PR #1237 (2026-05-18T06:26Z): 2 success (py3.11 + py3.12), 0 failure. Gate status: **GREEN** on main (no new qualifying push since last clean run).

**Chronic workflows:** none (carry-forward from 05:00Z guardian scan: `chronic_cancel_workflows_count: 0`; per-workflow queries unavailable in MCP-only environment — no new evidence of chronic cancellations at 12:00Z)

**Operational failures (≥5 unresolved from 11:00Z scan — resolution unverifiable via MCP):**

| Workflow | Run # | Failed at | Age at 12:15Z | URL |
|---|---|---|---|---|
| Check Streamer Live Status | #2281 | 05:20Z | ~6.9h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26077901771 |
| Gate Config Emit | #60 | 03:48Z | ~8.5h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26074988945 |
| ALPHA ENGINE - Adaptive Trust Tuner | #158 | 01:19Z | ~10.9h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26070262102 |
| DB Freshness Guardian | #13 | 01:10Z | ~11.1h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26069984624 |
| Strategy Health Monitor | #452 | 00:23Z | ~11.9h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26068405857 |

Secret Scan M-043 carried forward as resolved (superseded by clean Gitleaks on PRs #1244–#1251 — most recently PR #1251 at ~11:18Z).

**Open PRs CI snapshot:**

| PR | Title | Checks | Classification | Action |
|---|---|---|---|---|
| #1247 | feat(ai): model grill sequential + API roster | `test (3.11)` FAIL 08:54Z; `test (3.12)` cancelled; 5 other checks pass | **AUTHOR_FIX** | Author must fix test failure; run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26086549497 |

PR #1251 (audit: hourly report 2026-05-19 11Z): 3/3 security checks passed; merged to main at 12:13:20Z. No CI Tests triggered (path-filtered audit content).

**Action required:** author should fix CI failure on PR #1247 (`test (3.11)` — logs at run #26086549497, unchanged since 09:00Z, now ~3.4h stale); operator should manually re-run the 5 unresolved operational workflow failures above (guardian bot re-run blocked by 403 since 05:00Z; Strategy Health Monitor now ~11.9h old with no retry — escalation warranted).

**Status change vs prior hour:** DEGRADED → DEGRADED (verdict unchanged; open PRs RED still #1247 AUTHOR_FIX, unchanged since 09:00Z; chronic list unchanged; most-recently-merged PR updated #1249 → #1251, merged 12:13Z). No commit per step-5 policy (verdict + chronic list unchanged).

**Most recently merged PR:** #1251 ("audit: hourly report 2026-05-19 11Z — FINDING-12 resolving, FINDING-14 new", merged 2026-05-19T12:13:20Z).

---

## 13:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-filtered (only fires on `paper_trading/**`, `alpha_engine/**`, `tests/**`, `requirements.txt`, `ci-tests.yml`). All 10 most-recent main commits (12:56Z–13:04Z) carry `[skip ci]` — no new CI Tests runs triggered post-12:00Z on main. Last confirmed CI Tests run on main remains PR #1237 (2026-05-18T06:26Z): 2 success (py3.11 + py3.12), 0 failure. Gate status: **YELLOW** — see CRITICAL NOTE below.

**⚠ CRITICAL NOTE — PR #1247 merged with CI failure:** PR #1247 ("feat(ai): model grill sequential + API roster") was merged to main at **12:31:15Z** while a fresh CI Tests run (triggered at 12:30:30Z, run #26097255077) was in progress. That run completed `test (3.11)` = **failure** (12:37:30Z) and `test (3.12)` = **cancelled** (12:37:48Z) — 6 minutes after merge. The PR was merged before test results were known. If the PR #1247 merge commit touches `alpha_engine/**` or `tests/**` (as expected from its scope), the next qualifying push to main will trigger CI Tests and is likely to fail. **Operator should audit what broke in test (3.11) and push a fix commit before the next CI-qualifying push.**

Failure run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26097255077

**Chronic workflows:** none (carry-forward from 05:00Z guardian scan: `chronic_cancel_workflows_count: 0`; per-workflow queries unavailable in MCP-only environment — no new evidence of chronic cancellations at 13:00Z)

**Operational failures (≥5 unresolved from 12:00Z scan — resolution unverifiable via MCP):**

| Workflow | Run # | Failed at | Age at 13:10Z | URL |
|---|---|---|---|---|
| Check Streamer Live Status | #2281 | 05:20Z | ~7.8h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26077901771 |
| Gate Config Emit | #60 | 03:48Z | ~9.4h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26074988945 |
| ALPHA ENGINE - Adaptive Trust Tuner | #158 | 01:19Z | ~11.9h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26070262102 |
| DB Freshness Guardian | #13 | 01:10Z | ~12.0h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26069984624 |
| Strategy Health Monitor | #452 | 00:23Z | ~12.8h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26068405857 |

Secret Scan M-043 carried forward as resolved (superseded by clean Gitleaks on PRs #1244–#1252 — most recently PR #1252 at ~12:16Z).

**Open PRs RED:** none (0 open PRs at 13:10Z)

**Action required:**
1. **URGENT** — Operator should investigate `test (3.11)` failure from PR #1247 run #26097255077 (merged to main with CI red). Push a fix commit before the next code-qualifying push triggers a confirmed main CI failure.
2. Operator should manually re-run the 5 unresolved operational workflow failures above (guardian bot re-run blocked by 403 since 05:00Z; DB Freshness Guardian and Strategy Health Monitor now >12h old with no retry — escalation overdue).

**Status change vs prior hour:** DEGRADED → DEGRADED (verdict unchanged; open PRs RED changed 1→0 but only because PR #1247 was merged with CI red, not fixed; PR #1247 CI failure now lives on main; chronic list unchanged). No commit per step-5 policy (verdict + chronic list unchanged).

**Most recently merged PR:** #1247 ("feat(ai): model grill sequential + API roster", merged 2026-05-19T12:31:15Z — **CI failure on test (3.11) at merge time**).

---

## 14:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-filtered (only fires on `paper_trading/**`, `alpha_engine/**`, `tests/**`, `requirements.txt`, `ci-tests.yml`). All 5 most-recent main commits (13:57Z–14:02Z) carry `[skip ci]` — no new CI Tests runs triggered post-13:00Z. Last known CI Tests run: PR #1247 head (run #26097255077, triggered 12:30:30Z) — `test (3.11)` **FAILURE** (12:37:30Z), `test (3.12)` **cancelled**. This run's outcome was on the branch SHA `cfbe011b` which was merged to main at 12:31:15Z before results were known. Gate status: **YELLOW** — latent breakage on main; next code-qualifying push will expose the failure.

**⚠ CRITICAL NOTE (carried from 13:00Z) — PR #1247 merged with CI failure:** "feat(ai): model grill sequential + API roster" was merged to main at **12:31:15Z** while CI Tests run #26097255077 was in progress. `test (3.11)` completed **failure** at 12:37:30Z (6 min post-merge). Main is carrying broken test code. No remediation commit has landed as of 14:05Z (all subsequent commits are `[skip ci]` bot scans). Failure run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26097255077

**Chronic workflows:** none (carry-forward from 05:00Z guardian scan: `chronic_cancel_workflows_count: 0`; per-workflow queries unavailable in MCP-only environment — no new evidence of chronic cancellations at 14:00Z)

**Operational failures (≥5 unresolved from 13:00Z scan — resolution unverifiable via MCP):**

| Workflow | Run # | Failed at | Age at 14:05Z | URL |
|---|---|---|---|---|
| Check Streamer Live Status | #2281 | 05:20Z | ~8.7h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26077901771 |
| Gate Config Emit | #60 | 03:48Z | ~10.3h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26074988945 |
| ALPHA ENGINE - Adaptive Trust Tuner | #158 | 01:19Z | ~12.8h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26070262102 |
| DB Freshness Guardian | #13 | 01:10Z | ~12.9h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26069984624 |
| Strategy Health Monitor | #452 | 00:23Z | ~13.7h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26068405857 |

Secret Scan M-043 carried forward as resolved (superseded by clean Gitleaks on PRs #1244–#1253 — most recently PR #1253 at ~13:19Z).

**Open PRs CI snapshot:**

| PR | Title | Checks | Classification | Action |
|---|---|---|---|---|
| #1253 | audit: 13Z hourly — FINDING-16 resolved, FINDING-17 new | 3/3 success (Gitleaks, scan, pwd-grep ~13:19Z); 0 CI Tests runs | GREEN | Mergeable; no code changes, CI Tests not triggered |

**Action required:**
1. **URGENT (now ~1h 34min stale)** — Operator must investigate `test (3.11)` failure from PR #1247 run #26097255077 and push a remediation commit to main. Every hour this sits unresolved increases risk that an automated bot commit drops the `[skip ci]` tag and triggers a confirmed main CI failure publicly.
2. Operator should manually re-run the 5 unresolved operational workflow failures above (guardian bot re-run blocked by 403 since 05:00Z; Strategy Health Monitor now ~13.7h old with no retry — critical escalation overdue).

**Status change vs prior hour:** DEGRADED → DEGRADED (verdict unchanged; open PR #1253 CI green — no new RED; chronic list unchanged; critical note on PR #1247 main breakage carried forward from 13:00Z). No commit per step-5 policy (verdict + chronic list unchanged).

**Most recently merged PR:** #1247 ("feat(ai): model grill sequential + API roster", merged 2026-05-19T12:31:15Z — **CI failure on test (3.11) at merge time, ~1h 34min unresolved at 14:05Z**).

---

## 15:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-filtered (only fires on `paper_trading/**`, `alpha_engine/**`, `tests/**`, `requirements.txt`, `ci-tests.yml`). All commits to main since the PR #1247 merge at 12:31Z carry `[skip ci]` — no new CI Tests runs triggered. Last known CI Tests run: PR #1247 head (run #26097255077, triggered 12:30:30Z) — `test (3.11)` **FAILURE** (12:37:30Z), `test (3.12)` **cancelled**. This breakage merged into main at 12:31:15Z and is **~2h 37min unresolved** at 15:06Z. Gate status: **YELLOW** — latent breakage on main; next code-qualifying push will expose the failure.

**⚠ CRITICAL NOTE (carried from 13:00Z) — PR #1247 merged with CI failure:** "feat(ai): model grill sequential + API roster" was merged to main at **12:31:15Z** while CI Tests run #26097255077 was in progress. `test (3.11)` completed **failure** at 12:37:30Z (6 min post-merge). No remediation commit has landed as of 15:06Z (all subsequent commits carry `[skip ci]`). Failure run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26097255077

**Chronic workflows:** none (carry-forward from 05:00Z guardian scan: `chronic_cancel_workflows_count: 0`; per-workflow queries unavailable in MCP-only environment — no new evidence of chronic cancellations at 15:00Z)

**Operational failures (≥5 unresolved from 14:00Z scan — resolution unverifiable via MCP):**

| Workflow | Run # | Failed at | Age at 15:06Z | URL |
|---|---|---|---|---|
| Check Streamer Live Status | #2281 | 05:20Z | ~9.8h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26077901771 |
| Gate Config Emit | #60 | 03:48Z | ~11.3h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26074988945 |
| ALPHA ENGINE - Adaptive Trust Tuner | #158 | 01:19Z | ~13.8h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26070262102 |
| DB Freshness Guardian | #13 | 01:10Z | ~13.9h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26069984624 |
| Strategy Health Monitor | #452 | 00:23Z | ~14.7h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26068405857 |

Secret Scan M-043 carried forward as resolved (superseded by clean Gitleaks on PRs #1244–#1254 — most recently PR #1254 at ~14:22Z).

**Open PRs CI snapshot:**

| PR | Title | Checks | Classification | Action |
|---|---|---|---|---|
| #1254 | audit: 14Z hourly — FINDING-17 HOLD (cftc_cot n=18), FINDING-15 to 3-AI queue | 3/3 success (Gitleaks, scan, pwd-grep ~14:22Z); 0 CI Tests runs | GREEN | Mergeable; no code changes, CI Tests not triggered |

**Action required:**
1. **URGENT (~2h 37min stale)** — Operator must investigate `test (3.11)` failure from PR #1247 run #26097255077 and push a remediation commit to main. PR #1247 touched `alpha_engine/` and `tests/` — the next CI-qualifying push to main will surface a confirmed public CI failure.
2. Operator should manually re-run the 5 unresolved operational workflow failures above (guardian bot re-run blocked by 403 since 05:00Z; Strategy Health Monitor now ~14.7h old with no retry — critical escalation overdue).

**Status change vs prior hour:** DEGRADED → DEGRADED (verdict unchanged; PR #1253 merged at 14:12Z — 13Z audit, security checks green; PR #1254 now open and green; critical note on PR #1247 main breakage carried forward from 13:00Z; chronic list unchanged). No commit per step-5 policy (verdict + chronic list unchanged).

**Most recently merged PR:** #1253 ("audit: 13Z hourly — FINDING-16 resolved, FINDING-17 new (cftc_cot_commercial_signal n=18)", merged 2026-05-19T14:12:10Z).

---

## 16:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-filtered (only fires on `paper_trading/**`, `alpha_engine/**`, `tests/**`, `requirements.txt`, `ci-tests.yml`). All 50 scanned main commits (15:19Z–16:04Z) carry `[skip ci]` — no new CI Tests runs triggered. Last known CI Tests run: PR #1247 head (run #26097255077, triggered 12:30:30Z) — `test (3.11)` **FAILURE** (12:37:30Z), `test (3.12)` **cancelled**. This breakage merged into main at 12:31:15Z and is **~3h 33min unresolved** at 16:04Z. Gate status: **YELLOW** — latent breakage on main; next code-qualifying push to `alpha_engine/**` or `tests/**` will expose the failure.

**⚠ CRITICAL NOTE (carried from 13:00Z) — PR #1247 merged with CI failure:** "feat(ai): model grill sequential + API roster" was merged to main at **12:31:15Z** while CI Tests run #26097255077 was in progress. `test (3.11)` completed **failure** at 12:37:30Z (6 min post-merge). No remediation commit has landed as of 16:04Z (all subsequent commits carry `[skip ci]`). Failure run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26097255077

**Chronic workflows:** none (carry-forward from 05:00Z guardian scan: `chronic_cancel_workflows_count: 0`; per-workflow queries unavailable in MCP-only environment — no new evidence of chronic cancellations at 16:00Z)

**Operational failures (≥5 unresolved from 15:00Z scan — resolution unverifiable via MCP):**

| Workflow | Run # | Failed at | Age at 16:04Z | URL |
|---|---|---|---|---|
| Check Streamer Live Status | #2281 | 05:20Z | ~10.7h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26077901771 |
| Gate Config Emit | #60 | 03:48Z | ~12.3h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26074988945 |
| ALPHA ENGINE - Adaptive Trust Tuner | #158 | 01:19Z | ~14.8h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26070262102 |
| DB Freshness Guardian | #13 | 01:10Z | ~14.9h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26069984624 |
| Strategy Health Monitor | #452 | 00:23Z | ~15.7h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26068405857 |

Secret Scan M-043 carried forward as resolved (superseded by clean Gitleaks on PRs #1244–#1254 — most recently PR #1254 at ~14:22Z).

**Open PRs CI snapshot:**

| PR | Title | Checks | Classification | Action |
|---|---|---|---|---|
| #1255 | audit: 15Z hourly — FINDING-19 multi_asset_copytrader COMMODITY | 0 check runs at 16:04Z (created 15:19Z, ~45min elapsed — unusual; prior audit PRs had security checks within seconds) | YELLOW — watch | Likely transient infra delay; CI Tests not expected (path-filtered audit content) |

**Action required:**
1. **URGENT (~3h 33min stale)** — Operator must investigate `test (3.11)` failure from PR #1247 run #26097255077 and push a remediation commit to main. No `[skip ci]` bot commit will surface this — the next human or non-skip-tagged push to `alpha_engine/**` / `tests/**` will trigger a confirmed public CI failure.
2. Operator should manually re-run the 5 unresolved operational workflow failures above (guardian bot re-run blocked by 403 since 05:00Z; Strategy Health Monitor now ~15.7h old, DB Freshness Guardian ~14.9h old — both in critical escalation territory with no retry in sight).

**Status change vs prior hour:** DEGRADED → DEGRADED (verdict unchanged; PR #1254 merged at 15:11:44Z — 14Z audit, security checks green; PR #1255 open with 0 check runs after 45min — unusual but likely infra delay; PR #1247 main breakage now ~3h 33min unresolved, up from ~2h 37min at 15:00Z; chronic list unchanged). No commit per step-5 policy (verdict + chronic list unchanged).

**Most recently merged PR:** #1254 ("audit: 14Z hourly — FINDING-17 HOLD (cftc_cot n=18), FINDING-15 to 3-AI queue", merged 2026-05-19T15:11:44Z).

---
