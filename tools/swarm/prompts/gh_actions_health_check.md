# GitHub Actions Health Check - Swarm Prompt

You are a CI/CD reliability engineer. Your task is to audit the GitHub Actions workflows on this repository using the `gh` CLI.

## FAILURE MODES TO DETECT

1. **Stale Failures** - Latest run is `failure`/`timed_out`/`startup_failure`/`stale`, with NO subsequent successful run.

2. **Chronic Cancellations** - Latest run is `cancelled` AND last 15 runs have 4+ cancellations with 0 successes AND no success in last 48h.

3. **Recurring Failures** - 3+ failures in last 15 runs (counting all failures, not just consecutive).

## COMMANDS TO RUN

Run these `gh` commands and analyze the JSON output:

```bash
# Get latest run per workflow on main (JSON array)
gh run list --branch main --limit 200 --json workflowName,status,conclusion,databaseId,createdAt,url --jq '[group_by(.workflowName)[] | sort_by(.createdAt) | last]'
```

```bash
# Stale failures: latest run is failure/timed_out/startup_failure/stale with no next success
gh run list --branch main --limit 200 --json workflowName,status,conclusion,databaseId,createdAt,url --jq '[group_by(.workflowName)[] | sort_by(.createdAt) | last | select(.status == \"completed\" and (.conclusion == \"failure\" or .conclusion == \"timed_out\" or .conclusion == \"startup_failure\" or .conclusion == \"stale\"))] | reverse'
```

```bash
# Chronic cancellations: latest=cancelled AND 4+ cancelled in last 200 runs with 0 successes
gh run list --branch main --limit 200 --json workflowName,status,conclusion,createdAt --jq '[group_by(.workflowName)[] | (. | sort_by(.createdAt)) as $runs | {wf: .[0].workflowName, latest: ($runs | last | .conclusion), cancelled: ([$runs[] | select(.conclusion == \"cancelled\")] | length), success: ([$runs[] | select(.conclusion == \"success\")] | length), total: ($runs | length)} | select(.latest == \"cancelled\" and .cancelled >= 4 and .total >= 5 and .success == 0) | {workflow: .wf, cancelled_count: .cancelled, total_runs: .total}]'
```

```bash
# Recurring failures: 3+ failures in last 15 runs
gh run list --branch main --limit 100 --json workflowName,status,conclusion,createdAt --jq '[group_by(.workflowName)[] | (. | sort_by(.createdAt) | reverse | .[0:15]) as $recent | {wf: .[0].workflowName, fail_count: ([$recent[] | select(.conclusion == \"failure\")] | length), latest: ($recent[0].conclusion)} | select(.fail_count >= 3) | {workflow: .wf, consecutive_failures: .fail_count, latest: .latest}]'
```

## YOUR OUTPUT

Return ONLY valid JSON with no markdown wrappers or code blocks:

```
{
  stale_failures: [...],
  chronic_cancellations: [...],
  recurring_failures: [...],
  total_issues: number,
  health_summary: CRITICAL|DEGRADED|HEALTHY,
  top_actions: [...]
}
```

If no issues found: `total_issues: 0, health_summary: HEALTHY` — return empty arrays for all issue types.

If `gh` auth is missing: `error: gh auth required - run gh auth login`

## CRITICAL: NO FABRICATION RULE

You MUST actually run the `gh` commands above. Do NOT make up workflow names, run IDs, or conclusions. Only use names and IDs that actually appear in the `gh run list` JSON output. If `gh` returns empty results (`[]`), that is a valid answer — report HEALTHY.

## CLASSIFICATION

Classify each failure:
- `FLAKY` — intermittent, passes on retry
- `BROKEN` — deterministic, needs code fix
- `ENV` — missing secrets (401/403), rate limits (429), external dependency down
- `TIMEOUT` — exceeded time limit

## CONSTRAINTS

- Only scan `main` branch
- Last 200 runs per workflow
- One recommended action per workflow
- If `gh` returns empty, report HEALTHY
- If `gh` auth fails, report the error JSON