# GHA Hourly Health Monitor — 2026-08-12

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 30 sampled):** 0 success, 30 failure, 0 in_progress

All 30 runs returned by the CI Tests workflow API (branch=main) are `failure`. The failure streak spans continuously from at least **2026-08-10T09:32Z** through **2026-08-11T21:16Z** (latest recorded run #2144, run_id 31537099985), covering 30+ consecutive failures across ~36 hours. Each triggering commit is a bot-generated "Merge branch 'main' of …" sync commit — no human fix has landed on main.

**Failing jobs (run #2144, attempt 8, jobs 93975028094 / 93975028204):**
- `test (3.11)` — FAILURE at step 8: "Run all tests (gating — known-drift quarantined)"
- `test (3.12)` — FAILURE at step 8: "Run all tests (gating — known-drift quarantined)"
- All other steps (checkout, install, JS guard, quarantine-list write, known-drift non-blocking run, upload, coverage) — SUCCESS

Log content unavailable (Azure blob URL blocked by egress proxy). Specific failing test names cannot be extracted at this time; see run directly: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/31537099985

The run is on attempt 8 (GitHub has retried 7 times), indicating the failure is persistent, not a transient infra flake.

**Chronic workflows:** none detected — the 30-run snapshot across ~20 minutes of recent activity shows 26 success, 3 in_progress, 1 failure (`robust-edge-miner` run#105, a single schedule-triggered failure; insufficient history available to classify as chronic). No cancellations observed.

**Open PRs CI snapshot (last 5 checked):**

| PR | Title | CI Tests | Recommended action |
|---|---|---|---|
| #667 | feat(b5): forward-track cell selector | `test (3.11)` ❌ `test (3.12)` ❌ (Jun 24 runs, stale) | AUTHOR_FIX — tests fail on both Python versions; likely same root cause as main |
| #666 | fix(resolver): B1 backfill price guard | `test (3.11)` ❌ `test (3.12)` ❌ (Jun 24 runs, stale) | AUTHOR_FIX — same pattern |
| #665 | audit(stalled-producer-detector): v2.0+2 (branch: fix/ci-tests-drift-reconciliation) | `test (3.11)` ❌ `test (3.12)` ❌ (Jun 24 runs, stale) | AUTHOR_FIX — this PR *targets* CI drift; may be blocked by the same root failure on main |
| #657 | feat(contract-test): cold-merge atomic contract-test gate | Not checked (stale Jun 22 branch) | Hold — await main CI fix first |
| #600 | feat(edge): money-ready hunt / intrabar tools | Not checked (stale Jun 13 branch) | Hold — await main CI fix first |

Note: All check run timestamps for open PRs are from 2026-06-24 (~7 weeks ago). No PR has had a fresh CI run since then, consistent with main being continuously broken during that window.

**Open PRs RED:** #667, #666, #665 — all share `test (3.11)` + `test (3.12)` failures. Failure cause: AUTHOR_FIX (or possibly main regression that predates all three branches; cannot distinguish without log content).

**Action required:**
- **OPERATOR must investigate main CI Tests failure** — 30+ consecutive failures on main going back at least to 2026-08-10T09:32Z. Root cause: pytest gating step failing on Python 3.11 and 3.12. Fetch run logs at https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/31537099985 to identify specific failing tests.
- PR #665 (branch `fix/ci-tests-drift-reconciliation`) may already contain the fix — consider fast-tracking its review, but note its own CI is also red.
- `robust-edge-miner` workflow had a single failure (run#105, 2026-08-12T13:03Z) — monitor next run to determine if it's a transient or recurring issue.

**Status change vs previous run (2026-05-22 00:00 UTC):** GREEN → **RED** (verdict changed; gap of ~82 days in monitor coverage). First entry for 2026-08-12 — committing to establish daily baseline and signal the regression.
