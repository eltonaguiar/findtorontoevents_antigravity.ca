# GHA Hourly Health Monitor — 2026-08-30

## 13:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** N/A — no workflow named "CI Tests" exists in this repository (404). Repo uses production-specific scheduled workflows instead of a unified CI Tests gate.

**Sports data snapshots (intermittent failures — last 30 runs):** 5 failure / 25 success. Latest 2 consecutive failures at 12:40 UTC (run #3453) and 12:48 UTC (run #3454). Root cause: FTP upload timeout to 50webs — `mkdir: Fatal error: max-retries exceeded` + `put: data/pinnacle_snapshots/20260830T1248Z.json: Fatal error: max-retries exceeded` (lftp net:max-retries=3 × net:timeout=30s ≈ 90s hang, then fatal). Classification: **RERUN / infra-flake** (50webs FTP intermittent connectivity; not a code regression). Not chronic — has 25 successes in last 30 runs; last success was at 12:20 UTC (run #3452).

**Chronic workflows:** none — no workflows with ≥4 cancellations + 0 successes in last 15 runs detected across all scanned workflows.

**Open PRs RED:** none — 9 open PRs (#562, #564, #581, #595, #600, #657, #665, #666, #667) are all long-stale (opened June 2026, last activity July 2026). No active CI failures visible on any open PR.

**Action required:** operator should monitor FTP connectivity to 50webs. The `sports-data-snapshots` workflow is hitting ~17% failure rate today due to lftp timeouts against the Pinnacle snapshot upload step. No code fix needed — infra-level: check 50webs FTP server health or increase `net:max-retries` / `net:timeout` in the workflow's lftp commands if transient drops are expected.

**Run notes:**
- Failing run URL: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/33312475416
- Error lines: `mkdir: Fatal error: max-retries exceeded` (12:50:31 UTC) → `put: data/pinnacle_snapshots/20260830T1248Z.json: Fatal error: max-retries exceeded` (12:52:01 UTC)
- All other monitored workflows (30+ unique workflows in the last 100 runs) show normal success/in_progress status.
- No "CI Tests" workflow found — monitoring scope adjusted to per-workflow health scan.
