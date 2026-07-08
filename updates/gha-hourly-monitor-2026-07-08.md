# GHA Hourly Health Monitor — 2026-07-08

## 13:00 UTC

**Verdict:** GREEN

**Main CI Tests (last 5):** N/A — `ci-tests.yml` is PR-only (`event: pull_request`); does not trigger on main pushes. Main branch overall: 23 success / 0 failure / 7 in_progress across 30 most recent workflow runs (sampled at 2026-07-08T13:03Z).

**Chronic workflows:** none
- `sports-smoke-and-e2e.yml` — 30/30 success (last: 2026-07-08T12:49Z) — NOT CHRONIC
- `actions-failure-guardian.yml` — 30/30 success (last: 2026-07-08T13:02Z) — NOT CHRONIC
- `Unified Audit Dashboard` (audit-dashboard.yml) — 27/30 success, 1 isolated cancel (2026-07-07T22:35Z), 2 in_progress — NOT CHRONIC

**Open PRs RED (CI Tests failures):**
- **#667** `feat(b5): forward-track cell selector` — `test (3.11)` FAIL + `test (3.12)` FAIL on run [28109985534](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/28109985534) — **AUTHOR_FIX** — new `tests/test_select_forward_track_candidates.py` suite (29 invariants) failing on both Python versions; PR stale since 2026-06-24, no re-run since open
- **#666** `fix(resolver): B1 backfill price guard` — `test (3.11)` FAIL + `test (3.12)` FAIL on run [28108849365](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/28108849365) — **AUTHOR_FIX** — new `tests/test_universal_pick_resolver.py` B1 invariants failing on both Python versions; PR stale since 2026-06-24

**Action required:** authors of #667 and #666 should investigate and fix failing pytest suites before merge. Main is unaffected (ci-tests.yml only runs on PRs). No operator action needed for main health.
