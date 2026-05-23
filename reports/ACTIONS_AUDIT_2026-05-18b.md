# GitHub Actions Audit — 2026-05-18 (Stage B readiness + broken workflows)

Run-data audit (gh CLI, live). Companion to the resolution-pipeline fix plan.

## Findings

### 1. `Unified Audit Dashboard` — cancellation cascade (THE Stage-B blocker)

Last 12 runs: **1 success, ~10 cancelled.** A concurrency cascade — the
push-storm repo triggers the workflow faster than it completes, so each new run
cancels the prior. **Consequence:** the Stage-A `active_picks_sync` dry-run (just
shipped) almost never runs to completion → the non-crypto dry-run verdict files
are not being produced → **Stage B (writer `--apply` flip) cannot proceed** —
it needs 3-5 clean Stage-A cycles to inspect, and we get ~1 in 12.

**Fix (highest leverage):** the `concurrency:` group on `audit-dashboard.yml`
should `cancel-in-progress: false` (let runs queue + finish) OR the schedule
cadence should be reduced. Until this is fixed, Stage B is gated not on a
decision but on a broken CI cadence.

### 2. `CI Tests` — not a reliable gate, 7+ real test failures

Last 12: ~5 failure, ~6 cancelled, ~1 success. The failures are genuine
test/code drift, not flakes:
- `test_commodity_subclass_kill.py` ×4 (`hg_copper`, `pl_platinum`,
  `blacklisted`, `ct_f_probation`) — COMMODITY_BLACKLIST / CT=F-probation state
  drifted from what the tests assert.
- `test_bond_agent_workflow.py` ×2 (registered-strategy count + advertised
  count) — bond strategy roster changed, tests not updated.
- `test_audit_pick_sanity_gate.py` ×1.

**Fix:** update the 7 drifted tests to the current gate/strategy state (or fix
the code if the tests are right). Recurring pattern — see memory
`feedback_test_fixtures_vs_quarantine_data`. CI is currently not gating merges.

### 3. `penny-stock-picks.yml` — still failing (cause changed)

Latest failure 2026-05-18T13:06 — but the cause is now a
`JSONDecodeError: Expecting value` (a data API returned empty/non-JSON), NOT the
older checkout-token error. Symptom of a **single-API call with no failover** —
matches the peer infra-audit finding. Fix: route the penny-stock data fetch
through a failover chain + guard the empty-response case.

### 4. `dxy-state-update.yml` — RESOLVED

Peer reported "never ran once." **Now healthy** — `success` runs at
2026-05-18T14:40 and 07:34Z. `dxy_state.json` is fresh; M-074 COMMODITY booster
is not degraded. No action.

## Priority

| # | item | impact | fix owner |
|---|------|--------|-----------|
| 1 | audit-dashboard cancellation cascade | **blocks Stage B + dashboard freshness** | concurrency config — focused PR |
| 2 | 7 drifted CI tests | CI not a gate | update tests to current state |
| 3 | penny-stock-picks single-API failure | Goal #1 penny coverage dead | add failover + empty-guard |
| — | dxy-state-update | — | resolved, no action |

## Stage B readiness verdict

**NOT ready** — not because of the writer (code bugs fixed, Stage A shipped) but
because `audit-dashboard.yml` cancels itself ~10/12 runs, so Stage A rarely
produces the dry-run verdict files needed to vet Stage B. **Fix the concurrency
cascade first**, then 3-5 clean cycles, then flip `--apply`.

*Source: live `gh run list` / `gh run view --log-failed`, 2026-05-18T22:00Z.*
