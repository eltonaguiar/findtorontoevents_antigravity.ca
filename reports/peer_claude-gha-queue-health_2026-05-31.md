# GHA Queue Health — 2026-05-31 ~08:11Z

**Agent:** claude-gha-queue-health
**Trigger:** Run-Backtests run `26706712727` queued 45+ min (created 2026-05-31T07:37:51Z, still `status=queued` at probe time).

## TL;DR

`GHA_QUEUE:queued=163:in_progress=40:starved_hourlies=3:systemic=true`

Run-Backtests is **not isolated** — the GitHub Actions runner pool is system-saturated. 163 runs queued, 40 concurrently running, and at least 3 critical hourlies have not completed in >2h. Operator action recommended: do not retrigger more runs; let the queue drain or audit the runner pool config.

## Raw probe data (verbatim)

### Queue depth
- `gh run list --status queued --limit 100` → **100 rows** (page-cap hit)
- `gh run list --status queued --limit 200` → **163 rows**
- `gh run list --status in_progress --limit 100` → **40 rows**

### GitHub API health
- `gh api meta` → responded OK (SSH/web/api/hooks IP blocks returned)
- `gh api rate_limit` → `{"limit":5000,"remaining":4855,"used":145}` — API is healthy. **Not a GitHub-side outage.** Saturation is on the actions runner pool, not the REST API.

### Target run
```
gh run view 26706712727
{"status":"queued","conclusion":"","createdAt":"2026-05-31T07:37:51Z","workflowName":"Run Backtests & Deploy Dashboards"}
```
Queued ~33 min at first probe (08:11Z).

### Critical hourly last-success gap (probe time 08:11Z)

| Workflow | Last success | Gap | Verdict |
|---|---|---|---|
| Audit Hourly Update | 2026-05-31T05:47:21Z | 2h24m | **STARVED** |
| Live Picks Tracker | 2026-05-31T05:53:14Z | 2h18m | **STARVED** |
| Unified Audit Dashboard | 2026-05-31T06:06:07Z (then 2× `cancelled` at 06:15, 06:31) | 2h05m | **STARVED** |
| Smart Picks Tracker | 2026-05-31T07:09:14Z | 1h02m | OK |
| Hourly Master Picks to Discord | 2026-05-31T07:32:42Z | 39m | OK |
| Audit Impact Tracker | 2026-05-31T07:20:35Z | 51m | OK |
| Consensus Outcome Tracker | 2026-05-31T06:49:12Z | 1h22m | OK |
| AI Tournament Price Tracker | 2026-05-31T04:54:09Z | 3h17m (workflow is ~5h cadence; not necessarily starved) | NEUTRAL |

### Queue composition (notable)
The `--status queued` list is dominated by:
- Per-PR validation gates (`Secret Scan (M-043)`, `Conflict Marker Check`, `No stale DB passwords`, `Branch Large File Duplicate Guard`) firing across many active feature/docs branches (`docs/pr239-cross-verify-*`, `docs/peer-poll-stuck-workflow-*`, `docs/operator-diagnostic-packets-*`, `docs/agent-diff-fabrication-pattern-*`, etc.).
- Cron-fired scanners on `main` piling up at `:00–:10` of the hour (Crypto Signal Engine, Gainer Predictor, Swarm State Sync, Regime Terminal HMM, Multi-Asset Copytrader Scanner v2, QUAN ENGINE Live Autonomous Scanner, Consensus Outcome Tracker, Goldmine Tracker, Benchmark Comparison Daily, Deploy Rise of the Claw, Deploy FindCryptoPairs).
- `Branch Large File Duplicate Guard` appears repeatedly in `in_progress` (≥16 of the 40 concurrent runs) — likely the single largest concurrency consumer.

## Diagnosis

1. **Not isolated to Run-Backtests.** Same probe shows 163 queued and 3 cron-hourlies that should have a run in the last 60 min have not completed in >2h.
2. **Not a GitHub outage.** REST API healthy; rate-limit untouched.
3. **Root cause class = local runner-pool saturation / concurrency limit.** The hourly cron edge (top-of-hour) plus a burst of branch-validation gates from multiple agent-pushed docs branches overflows the available runner concurrency. Branch Large File Duplicate Guard is the most-duplicated job in flight and a likely throttle point.

## Acceptance criteria for operator

Operator should look at this if any of these hold past 09:00Z:
- queued count remains > 80 for 30 min
- any of {Audit Hourly Update, Live Picks Tracker, Unified Audit Dashboard} last-success gap exceeds 3h
- repeated `cancelled` conclusions on hourlies (already seen on Unified Audit Dashboard at 06:15Z + 06:31Z)

Possible knobs:
- Raise runner-pool size / self-hosted runner count.
- Add `concurrency:` group on `Branch Large File Duplicate Guard` to cap parallel guard runs per branch.
- Stagger top-of-hour crons (offset by N minutes) to flatten the burst.
- Pause docs-branch validation gates while saturated (not recommended — they are correctness gates).

**Action right now:** leave Run-Backtests `26706712727` queued. Do not cancel-and-retrigger — that only re-enters the back of the queue. Wait for organic drain.

## Methodology / sources

- `gh run list --status queued --limit 200`
- `gh run list --status in_progress --limit 100`
- `gh run view 26706712727`
- `gh run list --workflow="<name>" --status completed --limit 3` per hourly
- `gh api meta`, `gh api rate_limit`

All counts as of probe ~2026-05-31T08:11Z. No mutations performed; read-only diagnostic.
