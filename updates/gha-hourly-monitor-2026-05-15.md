# GHA Hourly Health Monitor — 2026-05-15

## 05:00 UTC

**Verdict:** RED

**Main CI Tests (last run on main):** 0 success, 1 failure, 0 in_progress
> Note: `gh` CLI unavailable in this environment; assessment based on GitHub MCP check-run queries against recently merged PRs. The last CI Tests run on main came from PR #1036 (merged 04:41Z), which showed `test (3.11)` = **failure**, `test (3.12)` = **cancelled**. PRs merged after that (#1038, #1034, #1031) were docs/skills-only and did not trigger the full test matrix.

**Chronic workflows:** none independently chronic
> `test (3.12)` is consistently cancelled, but this is a matrix fail-fast cascade from `test (3.11)` failing — not a standalone cancellation loop. All other workflow jobs (`scan`, `audit`, `drift`) are passing.

**Open PRs RED:**

| PR | Title | Failing checks | Classification |
|---|---|---|---|
| #1037 | feat(crypto): BTC UTC-hour death-zone filter | test(3.11) failure, gate failure, test(3.12) cancelled | **AUTHOR_FIX** |
| #1027 | feat(crypto): SHORT direction bias multiplier | test(3.11) failure, gate failure, test(3.12) cancelled | **AUTHOR_FIX** |
| #1026 | feat: Phase J ML-calibration banner + Kilo P0 fix | test(3.11) failure, gate failure, test(3.12) cancelled | **AUTHOR_FIX** |

PRs with scan-only (no test suite triggered — docs/archive/config branches):
- #1040, #1039: scan passing (docs-only, no test matrix needed)
- #1029: scan passing (no CI Tests matrix triggered)
- #1030, #1032: no check runs recorded

**Systemic failure pattern:** The `test (3.11)` job has been failing consistently across every code-touching PR opened today, starting at ~03:13Z (PR #1026), through 04:30Z (PR #1037). This is a **pre-existing shared test suite break**, not individual PR authoring errors. The `gate` job also fails on every PR where tests fail. PR #1036 was merged into main with this failure already present.

**Action required:** operator/author should investigate the CI test suite break. The failure predates today's PRs and is systemic — a single fix on main (or the shared test runner config) should unblock all three RED PRs. Likely cause: import error or missing dependency in a shared module, OR a test that asserts against live data that changed. Run `python -m pytest tests/ -x --tb=short` on main to locate the failing test.

**Run URLs for investigation:**
- PR #1037 test(3.11): https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/25900316274/job/76122100208
- PR #1026 test(3.11): https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/25898178319/job/76115634793
- PR #1037 gate: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/25900316224/job/76122100273

---

## 06:00 UTC

**Verdict:** RED (unchanged from 05:00 UTC)

**Main CI Tests (last run on main):** 0 success, 1 failure, 0 in_progress
> No code-touching PR has been merged to main since PR #1036 (04:41Z). All merges since then (#1038 04:42Z, #1034 04:45Z, #1031 04:46Z, #1039 05:12Z, #1040 05:12Z) were docs/skills/config only and do not trigger the test matrix. The systemic `test (3.11)` failure on main is **still unresolved**.

**Chronic workflows:** none independently chronic
> `test (3.12)` cancellations continue as a fail-fast cascade from `test (3.11)` — not standalone. All auxiliary jobs (`scan`, `audit`, `drift`) remain green.

**Open PRs RED:**

| PR | Title | Failing checks | Classification | Status vs 05Z |
|---|---|---|---|---|
| #1037 | feat(crypto): BTC UTC-hour death-zone filter | test(3.11) failure, gate failure, test(3.12) cancelled | **AUTHOR_FIX** (systemic) | UNCHANGED |
| #1027 | feat(crypto): SHORT direction bias multiplier | test(3.11) failure, gate failure, test(3.12) cancelled | **AUTHOR_FIX** (systemic) | UNCHANGED |
| #1026 | feat: Phase J ML-calibration banner + Kilo P0 fix | test(3.11) failure, gate failure, test(3.12) cancelled | **AUTHOR_FIX** (systemic) | UNCHANGED |

**New PRs since 05Z (all scan-only — no test matrix triggered):**
| PR | Title | CI state | Notes |
|---|---|---|---|
| #1043 | docs(audit): hourly audit 05Z | scan ✅ | docs-only |
| #1044 | docs(validation): external eval audit | scan ✅ | docs-only |
| #1045 | feat(M-008/M-021): COT lag correction (Copilot) | no runs | draft PR, CI not yet triggered |
| #1046 | docs(bond): regression deep-dive | scan ✅ | docs-only |

**PRs with no CI runs (persisting from 05Z):**
- #1030 (fix(audit): Mercury2 P0.1+P0.2): 0 check runs — open non-draft PR, test matrix not triggered (branch may be too stale to trigger CI or path filters exempt it)
- #1032 (docs/kimi-archive): 0 check runs — likely path filter exempts the `docs/` subtree

**Action required:** operator/author should investigate the CI test suite break — same action as 05Z. No new regressions or improvements detected this hour. The three code-touching PRs (#1026, #1027, #1037) remain blocked on the shared `test (3.11)` failure. Fix main first, then rebasing any of these PRs will re-run CI against a clean baseline.

**Note on PR #1030:** Non-draft, open, code-touching PR with 0 CI check runs since creation (03:19Z). Worth investigating whether the branch is missing a CI trigger event or if the workflow path filter is silently bypassing it.
