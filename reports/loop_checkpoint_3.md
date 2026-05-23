# Loop Checkpoint 3 — T+~80m (2026-05-08 19:35 UTC)

## New finding: Penny Skyrocket workflow NOT REGISTERED

Investigating EQUITY pipeline canonical writer turned up:

| workflow | state | last run |
|---|---|---|
| `Penny Stock Daily Picks` (`penny-stock-picks.yml`) | **disabled_manually** since 2026-02-21 | 2026-02-20 |
| `Penny Skyrocket Detector` (`penny-skyrocket-runner.yml`) | **NOT REGISTERED** with GH Actions | never triggered |

`penny-skyrocket-runner.yml` is on `main` since commit `2c61d1fdb92` (PR #546) and contains both `cron: '48 14 * * 1-5'` + `workflow_dispatch:`. Yet `gh api repos/.../actions/workflows --paginate` does not return it. Means GitHub Actions has never registered/picked up this workflow — explains why no runs since the PR merged.

Hypothesis (1 of 3):
1. YAML lint error blocks registration (most likely)
2. File never touched after PR merge → registration deferred
3. Default-branch detection lag

Verification: trigger manually via UI or `gh workflow run penny-skyrocket-runner.yml` (will register-on-trigger if file is valid).

## EQUITY pipeline status

- Original (disabled): `Penny Stock Daily Picks` — last successful 2026-02-20
- Canonical replacement: `Penny Skyrocket Detector` — never registered = never ran
- Result: **EQUITY pipeline IS broken**, but the cause is workflow registration / activation, not data quality

This is the highest-leverage Goal #1 win per uncharted recon. Recommended action:
```bash
# 1. Validate workflow YAML
gh workflow view penny-skyrocket-runner.yml -R eltonaguiar/findtorontoevents.ca || python -c "import yaml; yaml.safe_load(open('.github/workflows/penny-skyrocket-runner.yml'))"

# 2. Manually trigger to force registration
gh workflow run penny-skyrocket-runner.yml -R eltonaguiar/findtorontoevents.ca

# 3. After 1 successful run, GitHub will auto-register and the cron will start firing
```

## Done since checkpoint 2

- ✅ Cascade hypothesis investigated via grep across resolver chain → REJECTED
- ✅ db_health_check.py Decimal*float bug fixed
- ✅ pnl_integrity 43.22% mismatch confirmed live
- ✅ phantom_expired query rewritten for shared-host /tmp budget
- ✅ Commit T+60m batch landed (db_health_check fixes + 5 reports + 7 reusable forensic scripts)
- ✅ penny_picks cron disabled_manually 2026-02-21 (mass-decommission of 14+ workflows)
- ✅ Canonical penny EQUITY writer found = penny-skyrocket-runner.yml but NOT registered

## Up next

- 2nd full bg health-check still running (pid 3257)
- Investigate outcome_coverage 12.27% reconciliation vs Kimi 0.09% claim
- Find writer that maps SL_HIT to WON status (won_pnl_contradiction root cause)
- Schedule next wakeup at T+20m

## Scheduled wakeup

T+100m at 15:54 UTC (1200s interval).
