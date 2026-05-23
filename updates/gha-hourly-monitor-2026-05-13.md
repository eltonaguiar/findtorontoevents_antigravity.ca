# GHA Hourly Health Monitor — 2026-05-13

## 04:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress
_(Inferred from merged-PR check_runs — gh CLI unavailable; MCP check_runs queried for all code PRs merged today.)_
- PR #940 (merged 01:34): test(3.11) ❌ FAILURE, test(3.12) ⛔ cancelled, gate ❌ FAILURE
- PR #941 (merged 02:31): test(3.11) ❌ FAILURE, test(3.12) ⛔ cancelled, gate ❌ FAILURE
- PR #945 (merged 02:51): test(3.11) ❌ FAILURE, test(3.12) ⛔ cancelled, gate ❌ FAILURE
- PR #947 (merged 03:27): test(3.11) ❌ FAILURE, test(3.12) ⛔ cancelled, gate ❌ FAILURE
- PR #944 (merged 04:03, docs-only): scan ✅ only — no test job triggered
- **All 4 code PRs merged today carried failing CI Tests at time of merge. Transition from DEGRADED → RED.**

**Suspected root cause (from PR #946 body):** Pre-existing failing test `test_all_values_in_indicator_families` — `commodity_seasonal_planting_harvest` strategy uses an invalid family value in `alpha_engine/config.py`. Introduced by an earlier merge; all branches that run the full test suite inherit it.

**Chronic workflows:** none meeting the cancellation threshold (latest run cancelled + ≥4 cancels in last 15 + 0 successes + no success in 48h). Pattern seen:
- `gate`: persistent FAILURE on every code PR (5/5 today, consistent with 5/5 on 2026-05-12). This is a chronic FAILURE (not cancellation). Still non-blocking (PRs merge regardless). Warrants operator investigation — appears to have been broken for ≥2 days with 0 successes. See 2026-05-12 06:00 UTC note.
- `test (3.12)`: consistently CANCELLED as a downstream effect of `test (3.11)` failing first (matrix cancel-on-failure). Not an independent failure.

**Open PRs RED (test(3.11) FAILURE on all 5):**

| PR | Title | Failure type | Recommended action |
|----|-------|-------------|-------------------|
| #942 | feat(audit): anti-overfit validator default-ON | AUTHOR_FIX — test.3.11 fails, likely inheriting pre-existing `test_all_values_in_indicator_families` breakage from main | Fix pre-existing failing test in main first, then rebase |
| #943 | feat(audit): system staleness detection in tier-2 hero cards | AUTHOR_FIX — same pattern; audit ✅ drift ✅ but test.3.11 ❌ | Fix root cause on main, rebase |
| #946 | Add confluence-based forex & futures pick strategies | AUTHOR_FIX — PR body explicitly calls out pre-existing `test_all_values_in_indicator_families` + gate ❌; 12/13 tests pass locally | Fix `commodity_seasonal_planting_harvest` invalid family on main; gate failure needs investigation |
| #948 | feat(forex): Donchian Channel Breakout (Turtle Trading) | AUTHOR_FIX — test.3.11 ❌, gate ❌; consistent with systemic pre-existing failure | Same root-cause fix on main required |
| #949 | feat(futures): Donchian breakout + term structure strategies | AUTHOR_FIX — test.3.11 ❌, gate ❌; same pattern | Same root-cause fix on main required |

**Action required:**
1. **P0 — Fix `commodity_seasonal_planting_harvest` invalid family value** in `alpha_engine/config.py` on main. This is the likely root cause of `test_all_values_in_indicator_families` failing on every PR. All 5 open PRs unblock once this is fixed.
2. **P1 — Investigate `gate` workflow**: chronic FAILURE on every PR for ≥2 days (0 successes visible). This check is non-blocking but if it's meant to enforce the Wire-Up Rule it may be silently rubber-stamping every PR.
3. **P2 — Enforce branch protection**: At least 4 code PRs were merged today with failing CI Tests. Recommend requiring `test (3.11)` to pass before merge is allowed.

---

## 05:00 UTC

**Verdict:** RED _(no change from 04:00 UTC)_

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress
_(Inferred from open-PR check_runs — gh CLI unavailable, no workflow-run MCP API. No fix merged to main since 04:03 UTC.)_
- All 5 open code PRs (#942 #943 #946 #948 #949) confirmed still showing test(3.11) ❌ FAILURE.
- 2 new PRs opened since 04:00 UTC: #950 (docs/audit tracking — no test jobs) and #951 (chore/loop-escalation — no test jobs). Neither introduces code changes.
- Root cause unresolved: `commodity_seasonal_planting_harvest` invalid family value in `alpha_engine/config.py` (reported at 04:00 UTC).

**Chronic workflows:** no change from 04:00 UTC. `gate` remains chronic FAILURE (non-blocking); `test(3.12)` remains downstream-cancel of `test(3.11)`.

**Open PRs RED (7 open; 5 with CI failures, 2 docs-only):**

| PR | Title | CI status | Recommended action |
|----|-------|-----------|-------------------|
| #942 | feat(audit): anti-overfit validator default-ON | test(3.11) ❌, test(3.12) ⛔, scan ✅, audit ✅ | AUTHOR_FIX — awaiting P0 root-cause fix on main |
| #943 | feat(audit): system staleness detection | test(3.11) ❌, test(3.12) ⛔, scan ✅, audit ✅, drift ✅ | AUTHOR_FIX — same root cause |
| #946 | Add confluence forex & futures strategies | test(3.11) ❌, test(3.12) ⛔, scan ✅, audit ✅, gate ❌ | AUTHOR_FIX — root cause + gate failure |
| #948 | feat(forex): Donchian Turtle Trading | test(3.11) ❌, test(3.12) ⛔, scan ✅, gate ❌ | AUTHOR_FIX — root cause + gate failure |
| #949 | feat(futures): Donchian + term structure | test(3.11) ❌, test(3.12) ⛔, scan ✅, gate ❌ | AUTHOR_FIX — root cause + gate failure |
| #950 | audit(hourly): 2026-05-13 04Z tracking | docs-only | no action |
| #951 | chore(loop): escalation 2026-05-13 | docs-only | no action |

**Action required:** same as 04:00 UTC — P0 fix for `commodity_seasonal_planting_harvest` family value in `alpha_engine/config.py` on main is the unblocking action for all 5 code PRs.

---

## 06:00 UTC

**Verdict:** RED _(no change from 05:00 UTC — third consecutive RED hour)_

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress
_(Inferred from merged-PR and open-PR check_runs — gh CLI unavailable, no workflow-run MCP API.)_
- PR #956 (merged 06:09): test(3.11) ❌ FAILURE, test(3.12) ⛔ cancelled, scan ✅, audit ✅ — merged with failing CI
- PR #955 (merged 06:02): test(3.11) ❌ FAILURE, test(3.12) ⛔ cancelled, scan ✅, audit ✅, drift ✅ — merged with failing CI
- PR #953 (merged 05:35): test(3.11) ❌ FAILURE, test(3.12) ⛔ cancelled, scan ✅, audit ✅ — merged with failing CI
- PR #952 (merged 05:33): test(3.11) ❌ FAILURE, test(3.12) ⛔ cancelled — merged with failing CI
- Root cause persists: `commodity_seasonal_planting_harvest` invalid family in `alpha_engine/config.py` reported at 04:00 UTC — **still unresolved** after 4 more merged PRs and 2+ hours

**Chronic workflows:** no change from 05:00 UTC.
- `gate`: chronic FAILURE on strategy PRs (#946 #948 #949) — non-blocking, 0 successes seen today across all code PRs.
- `test (3.12)`: consistently CANCELLED as downstream fail-fast effect of `test (3.11)` failure — not an independent issue.
- No workflow meets the strict chronic-cancellation threshold (latest=cancelled + ≥4 cancels + 0 successes + no success in 48h).

**Open PRs RED (8 open; 5 with CI failures, 1 no CI yet, 2 docs-only):**

| PR | Title | CI status | Recommended action |
|----|-------|-----------|-------------------|
| #942 | feat(audit): anti-overfit validator default-ON | test(3.11) ❌, test(3.12) ⛔, scan ✅, audit ✅ | AUTHOR_FIX — awaiting P0 root-cause fix on main |
| #943 | feat(audit): system staleness detection | test(3.11) ❌, test(3.12) ⛔, scan ✅, audit ✅, drift ✅ | AUTHOR_FIX — same root cause |
| #946 | Add confluence forex & futures strategies | test(3.11) ❌, test(3.12) ⛔, gate ❌, scan ✅, audit ✅ | AUTHOR_FIX — root cause + gate failure |
| #948 | feat(forex): Donchian Turtle Trading | test(3.11) ❌, test(3.12) ⛔, gate ❌, scan ✅ | AUTHOR_FIX — root cause + gate failure |
| #949 | feat(futures): Donchian + term structure | test(3.11) ❌, test(3.12) ⛔, gate ❌, scan ✅ | AUTHOR_FIX — root cause + gate failure |
| #950 | audit(hourly): 2026-05-13 04Z tracking | docs-only | no action |
| #951 | chore(loop): escalation 2026-05-13 | docs-only | no action |
| #954 | feat(b9): adversarial debate shadow wirein | no CI yet (opened 05:36) | WAIT — CI pending |

**New since 05:00 UTC:**
- 4 PRs merged (#952 #953 #955 #956), all with failing `test (3.11)` at merge time — pattern of operator overriding failing CI continues.
- 1 new code PR opened: #954 (feat/b9 adversarial debate shadow wirein). No CI check runs yet.

**Action required:** same as 04:00 UTC.
1. **P0 — Fix `commodity_seasonal_planting_harvest` invalid family value** in `alpha_engine/config.py` on main. Three hours and 8 merged PRs have not addressed this. All 5 code PRs unblock once fixed.
2. **P1 — Investigate `gate` workflow**: 0 successes on any code PR for ≥3 days. Non-blocking at present but silently failing its gating purpose.
3. **P2 — Consider branch protection**: 8+ code PRs merged today with failing `test (3.11)`. No merge gate is enforcing CI health.
