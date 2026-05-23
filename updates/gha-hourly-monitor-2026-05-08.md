# GHA Hourly Health Monitor — 2026-05-08

## 03:00 UTC

**Verdict:** DEGRADED *(carried over from 2026-05-07 04:00 UTC — same tooling gap)*

**Main CI Tests (last 5):** UNKNOWN — `gh` CLI not available in this environment; MCP server
has no workflow-run listing endpoint. All 10 most-recent main-branch commits carry `[skip ci]`
(bot writers: Pick-monitor, Meme-Scanner, ML-Tracker, Conviction-Scan, Alpha-Engine-FAST,
Signal-Recorder, System-F-Claws-of-Doom, mega-mutation-tracker, prediction-quality-metrics,
Dashboard-pick-trader). Earliest non-skip-ci commits found on main: `bb2e34a` ("Merge branch"
2026-05-08T02:42Z), `32fa822` ("OBI snapshot" 2026-05-08T02:21Z), `481cd40` ("Merge branch"
2026-05-08T01:53Z) — MCP `get_commit` does not return check-run status, so CI Tests verdict
on these commits is unverifiable without `gh run list --workflow "CI Tests"`.

**Chronic workflows:** UNKNOWN — per-workflow cancellation scan requires
`gh run list --workflow "<name>" --limit 15`. Not available. No change from prior hours.
Interim coverage: the `actions-failure-guardian.yml` workflow runs on its own schedule and
should surface chronic failures if they exist.

**Open PRs CI snapshot (3 open, 1 draft skipped):**

| PR | Title | Checks | Status |
|----|-------|--------|--------|
| #859 | audit(05Z 2026-05-07): forex_rsi2 escalated | scan ✅ (2026-05-07T05:22Z) | OK |
| #846 | feat(b18): Shadow Probation panel on /audit | scan ✅ · drift ✅ (2026-05-06T03:38Z) | DO NOT ADMIN-MERGE (explicit hold) |
| #849 | Edge action plan + swarm peer-review harness | 0 check runs (draft) | SKIP |

**PRs closed since 2026-05-07 04:00Z:** #855, #856, #857, #854 no longer in open list;
most recently merged PR is **#860** ("Fix dating 'All Dates' grid hiding today's events",
merged 2026-05-07T23:31:21Z, 0 check runs — does not touch CI-gated paths).

**Open PRs RED:** none — no failing check_runs on any open PR.

**Chronic workflows flagged:** none detected within observable scope.

**Action required:**
1. **Tooling gap persists (carry-over)** — Steps 1–2 of the monitor checklist require
   `gh run list --workflow "CI Tests" --limit 5`. Until `gh` CLI is installed or a
   workflow-run MCP endpoint is added, Main CI Tests health cannot be determined. Check
   `scripts/actions_failure_guardian.py` GHA run results for authoritative data.
2. **PR #846 hold** — explicit "DO NOT ADMIN-MERGE" label; awaiting human review.
   scan + drift passing; no CI action needed from monitor.
3. **PR #859 stale** — opened 2026-05-07T05:20Z, base SHA `c47660713` is 1 day old.
   No action required from monitor; PR author should rebase if needed before merge.

**Last merged PR:** #860 (`Fix dating "All Dates" grid hiding today's events`,
merged 2026-05-07T23:31:21Z). No RED transition detected → Step 6 (PR comment) skipped.

*Verdict vs previous hour (2026-05-07 04:00Z): DEGRADED → DEGRADED (no change).*
*No commit triggered — verdict unchanged and chronic-workflow list unchanged.*

*Data sources: MCP `get_check_runs` (PRs #846, #849, #859), `list_commits` (100 most
recent main parsed locally), `list_pull_requests` (open + merged top-1), `list_commits`
page-1 (10 most recent for bot-commit audit). `gh` CLI absent — Steps 1–2 UNKNOWN.*

---

## 04:00 UTC

**Verdict:** DEGRADED *(unchanged from 03:00 UTC — same tooling gap + new CI Tests failure finding)*

**Main CI Tests (last 5):** UNKNOWN — `gh` CLI unavailable; MCP has no workflow-run endpoint.
All 10 most-recent main commits carry `[skip ci]` (bot writers: System-F-Claws-of-Doom,
mega-mutation-tracker, Signal-Recorder, Crypto-Smart-Picks, prediction-quality-metrics,
Dashboard-pick-trader, Gainer-scan, Copy-trader-portfolio, continuous-improvement-report,
Live-spike-trading). No CI-Tests-eligible commits found in observable main window.

**NEW FINDING vs 03:00Z:** PR #854 (`chore: remove freebuff engine + add DB spec doc`,
merged 2026-05-07T11:30:30Z) — previously logged as "0 checks" while open — shows 4 completed
check runs post-merge:

| Job | Conclusion |
|-----|------------|
| `test (3.11)` | **failure** |
| `test (3.12)` | **cancelled** |
| `scan` | success |
| `audit` | success |

This is the most recent CI Tests run visible via MCP. No subsequent successful CI Tests run
found. PR #854 was merged despite failing tests. Whether CI Tests ran again on main after
merge (and passed) is unverifiable without `gh run list --workflow "CI Tests"`.

**Chronic workflows:** UNKNOWN — per-workflow cancellation scan requires `gh run list --workflow`.
Not available. No change from prior hours.

**Open PRs CI snapshot:**

| PR | Title | Checks | Status |
|----|-------|--------|--------|
| #861 | audit(03Z 2026-05-08): FOREX recovery + EQUITY T1 5th run | scan ✅ (03:28Z) | OK |
| #846 | feat(b18): Shadow Probation panel on /audit | scan ✅ · drift ✅ (2026-05-06T03:38Z) | DO NOT ADMIN-MERGE (explicit hold) |
| #849 | Edge action plan + swarm peer-review harness | 0 checks (draft) | SKIP |

**Most recently merged PRs:**
- **#859** (audit 05Z 2026-05-07, merged 2026-05-08T03:15Z) — scan ✅ only (report-only, no Python CI gate)
- **#860** (Fix dating "All Dates" grid, merged 2026-05-07T23:31Z) — 0 checks (HTML/JS path, not Python CI gate)

**Open PRs RED:** none — no failing check runs on any open PR.

**Chronic workflows flagged:** none detected within observable scope.

**Action required:**
1. **Tooling gap persists** — Steps 1–2 of checklist require `gh run list --workflow "CI Tests"`.
   Check `scripts/actions_failure_guardian.py` GHA run results for authoritative CI Tests data.
2. **PR #854 merged with test failure (new)** — `test (3.11)` failed, `test (3.12)` cancelled
   on the freebuff-removal PR before merge (2026-05-07T11:30Z). No successful CI Tests run
   found after this. Human operator should verify whether tests pass on current main via
   the `actions-failure-guardian.yml` report or by re-running CI manually.
3. **PR #846 hold** — explicit "DO NOT ADMIN-MERGE"; scan + drift passing; no monitor action.

*Verdict vs previous section (2026-05-08 03:00Z): DEGRADED → DEGRADED (no change in verdict).*
*No commit triggered — verdict unchanged and chronic-workflow list unchanged.*
*New finding documented: PR #854 CI Tests failure (test 3.11 failure + test 3.12 cancelled).*

*Data sources: MCP `get_check_runs` (PRs #854, #855, #858, #859, #860, #861, #846, #849),
`list_commits` (10 most recent main), `list_pull_requests` (open perPage=30; closed perPage=5
sort=updated desc). `gh` CLI absent — Steps 1–2 UNKNOWN.*

---

## 05:00 UTC

**Verdict:** DEGRADED *(unchanged from 04:00 UTC — same tooling gap + test(3.11) failure now confirmed on two PRs)*

**Main CI Tests (last 5):** UNKNOWN — `gh` CLI unavailable; MCP has no workflow-run listing endpoint.
All 10 most-recent main commits carry `[skip ci]` (bot writers: What-Worked-insights,
Volatile-Alt-scan, KIMI_FEB172026-validate, QuantumFusion-report, pick-check, forward-tracking,
Signal-Engine-scan, Forward-scan, KIMI-scan, Regime-Terminal-scan). No CI-eligible commits
found in the observable main window. CI Tests last seen failing on PR #854 (2026-05-07T11:30Z,
test 3.11 failure pre-merge) and now confirmed again on open PR #862 — both same symptom.

**Chronic workflows:** UNKNOWN — `gh run list --workflow "<name>" --limit 15` not available.
No change from prior hours. `actions-failure-guardian.yml` is the authoritative source.

**Open PRs CI snapshot (5 open, 1 draft skipped):**

| PR | Title snippet | Checks | Classification |
|----|--------------|--------|----------------|
| #864 | chore(loop): V1-V7 re-verified 04:17Z | scan ✅ (04:29Z) | OK |
| #863 | audit(04Z 2026-05-08): CRYPTO alarm cleared | scan ✅ (04:29Z) | OK |
| #862 | DB query bank: forex pnl corruption + 50 untested live pairs | scan ✅ · test(3.11) ❌ · test(3.12) cancelled | **RED — AUTHOR_FIX** |
| #849 | Edge action plan + swarm peer-review harness | 0 checks (draft) | SKIP |
| #846 | feat(b18): Shadow Probation panel on /audit | scan ✅ · drift ✅ (2026-05-06T03:38Z) | DO NOT ADMIN-MERGE (explicit hold) |

**Open PRs RED:** #862 — `test (3.11)` failure (04:10Z) + `test (3.12)` cancelled.
PR adds `tools/db_query_bank_2026-05-07.py`, `tests/playwright/test_pr860_dating_today_visible.spec.ts`,
and 16 CSV report files. Failure is assertion/import error (not infra flake) — **AUTHOR_FIX required**.
Note: test(3.11) now failing on 2 consecutive PRs (#854 merged 2026-05-07, #862 open) — possible
systemic issue with 3.11 compatibility in new test files.

**Action required:**
1. **Tooling gap persists (carry-over)** — Steps 1–2 require `gh run list --workflow "CI Tests"`.
   Check `scripts/actions_failure_guardian.py` GHA results for authoritative CI Tests data.
2. **PR #862 — AUTHOR_FIX** — `test (3.11)` failure on `findings/db-query-bank-2026-05-07`.
   Author should inspect job https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/25536096031/job/74952123684,
   fix failing tests, and push a new commit. Do not merge until CI Tests green.
3. **Systemic 3.11 concern** — test(3.11) failed on both #854 (merged) and #862 (open).
   Investigate whether a recent dependency or import change broke 3.11 compat system-wide.
4. **PR #846 hold** — explicit "DO NOT ADMIN-MERGE"; scan + drift passing; no CI action needed.

*Verdict vs previous section (2026-05-08 04:00Z): DEGRADED → DEGRADED (no change in verdict).*
*No commit triggered — verdict unchanged and chronic-workflow list unchanged.*
*New finding: PR #862 RED (test 3.11 failure); systemic 3.11 pattern now on 2 PRs.*

*Data sources: MCP `get_check_runs` (PRs #858, #859, #861, #862, #863, #864, #846, #849),
`list_commits` (10 most recent main), `list_pull_requests` (open perPage=30; closed perPage=5
sort=updated desc), `get_commit` (main tip 51a8380f). `gh` CLI absent — Steps 1–2 UNKNOWN.*
