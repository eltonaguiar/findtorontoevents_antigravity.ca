# /swarm-actions

Monitor GitHub Actions for failed, flaky, cancelled, and stale jobs.

## Usage
```
/swarm-actions <repo> [--since 30d] [--notify]
```

## Detection
- **Failed** — Consecutive failures without subsequent success
- **Flaky** — Intermittent pass/fail patterns
- **Cancelled** — Frequently cancelled jobs
- **Stale** — Jobs not run in > N days

## Pipeline
1. Fetch workflow runs (last 100 or N days)
2. Pattern detection per workflow/job
3. Impact analysis for each flaky job
4. Recommendation generation

## Output
- Lists of failed/flaky/stale/cancelled jobs
- Blast radius assessment per job
- Actionable recommendations
