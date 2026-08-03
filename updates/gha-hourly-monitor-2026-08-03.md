# GHA Hourly Health Monitor — 2026-08-03

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

- Run [#1990](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/30812230635) — failure — 2026-08-03T12:07Z
- Run #1989 — failure — 2026-08-03T10:09Z
- Run #1988 — failure — 2026-08-03T08:12Z
- Run #1987 — failure — 2026-08-03T06:09Z
- Run #1986 — failure — 2026-08-03T04:54Z

**Failing step:** `Run all tests (gating — known-drift quarantined)` (step 8)
Both matrix jobs (`test (3.11)` and `test (3.12)`) fail at this step.
Failure is persistent: runs from 2026-07-29 (5+ days ago) are also all failures.
Log URL expired before content could be retrieved — see latest run linked above for details.

**Sports smoke (sports-smoke-and-e2e):** 5/5 success today — GREEN
- Latest: run #1350, success at 2026-08-03T11:24Z

**Chronic workflows:** None detected in 30-run snapshot (17 success, 0 failure, 1 skipped, ~12 in-progress at query time). Per-workflow chronic-cancellation scan skipped — API responses too large to fully enumerate 362 active workflows in one pass.

**Open PRs (9 open):**
- #667 feat(b5): forward-track cell selector
- #666 fix(resolver): B1 backfill price guard
- #665 audit(stalled-producer-detector): v2.0+2 cron wiring
- #657 feat(contract-test): cold-merge atomic contract-test gate
- #600 feat(edge): money-ready hunt
- #595 feat(validate): non-crypto intrabar replay scaffold
- #581 feat(audit): P2-9 model_portfolios.html
- #564 docs: Audit Edge Hunt Action Plan
- #562 feat(audit): edge hunt session docs

Individual PR check rollup not retrieved (size constraints). Given CI Tests has been failing on main for 5+ days, any PR whose CI Tests gate runs against main will also be RED.

**Action required:** AUTHOR_FIX — `CI Tests` / step `Run all tests (gating — known-drift quarantined)` has been failing on `main` since at least 2026-07-29. Investigate failing test names at [run #1990](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/30812230635). This is not an infra flake — consistent 5+ day failure across Python 3.11 + 3.12. An author/maintainer should diagnose and fix the test regression.
