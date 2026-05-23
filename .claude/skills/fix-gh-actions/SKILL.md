---
name: fix-gh-actions
description: Use when checking for failed GitHub Actions jobs that have no subsequent successful run, or when user wants to find and rerun stale failures. Aliases - fixGHACTIONS, FIXGH, fixjobs
---

# Fix GitHub Actions — Failed Job Double-Check

Scan all recent GitHub Actions workflow runs, find failures whose workflow has NOT had a subsequent successful run, and offer to rerun them.

## How It Works

1. Use `gh` CLI to list recent workflow runs on `main`
2. Group by workflow name — keep only the LATEST run per workflow
3. Flag any whose latest run is `failure`, `timed_out`, `startup_failure`, or `stale`
4. Show the user a table of unresolved failures
5. Offer to rerun failed jobs via `gh run rerun --failed <run_id>`

## Hardening Rules (Lessons Learned)

- Duplicate workflow display names can hide unresolved failures. If a user cites a specific run URL/ID, always verify that run directly via `gh run view <id>` and then inspect that exact workflow ID via GitHub API.
- In PowerShell, prefer single-quoted `--jq` strings or PowerShell-native JSON grouping to avoid escaping issues with `\(...)` interpolation.
- If a run is long-lived or repeatedly failing, escalate with `tools/swarm_v2` (`swarm actions` and/or `swarm research`) and include concrete log evidence before proposing fixes.

### Verify a User-Flagged Run by Workflow ID

```bash
gh run view <run_id> --json workflowName,status,conclusion,createdAt,url
gh api --method GET repos/<owner>/<repo>/actions/runs/<run_id> --jq '.workflow_id'
gh api --method GET repos/<owner>/<repo>/actions/workflows/<workflow_id>/runs -f branch=main -f per_page=20
```

Use this when run-name grouping says "all good" but a known run appears unresolved.

### PowerShell-Safe Alternative (No jq Escaping)

```powershell
$runs = gh run list --branch main --limit 200 --json workflowName,status,conclusion,databaseId,createdAt,url | ConvertFrom-Json
$latest = $runs | Group-Object workflowName | ForEach-Object { $_.Group | Sort-Object createdAt | Select-Object -Last 1 }
$latest | Where-Object { $_.status -eq 'completed' -and @('failure','timed_out','startup_failure','stale') -contains $_.conclusion }
```

### Stuck / Repeated-Failure Escalation

If a run is still `queued`/`pending`/`in_progress` for unusually long or a workflow keeps failing:

1. Pull run details + failed logs:

```bash
gh run view <run_id> --json jobs,createdAt,updatedAt,status,conclusion,url
gh run view <run_id> --log-failed
```

2. Run swarm analysis:

```bash
PYTHONPATH=tools/swarm_v2 python -m swarms.cli.main actions <owner>/<repo> --since 7d
PYTHONPATH=tools/swarm_v2 python -m swarms.cli.main research "<run_id> failure summary and logs" --depth 3 --route A
```

3. Apply a fix that addresses root cause (workflow config, permissions, trigger duplication, flaky step), then re-run or dispatch the workflow.

## Execution

Run this bash command to get all failed latest-runs:

```bash
gh run list --branch main --limit 200 --json workflowName,status,conclusion,databaseId,createdAt,url \
  --jq '
    [group_by(.workflowName)[] |
     sort_by(.createdAt) | last |
     select(.status == "completed" and (.conclusion == "failure" or .conclusion == "timed_out" or .conclusion == "startup_failure" or .conclusion == "stale"))] |
    sort_by(.createdAt) | reverse |
    .[] | "\(.workflowName)\t\(.conclusion)\t\(.createdAt)\t\(.databaseId)\t\(.url)"
  '
```

### Presenting Results

Show results as a markdown table:

| Workflow | Status | When | Run ID | Link |
|----------|--------|------|--------|------|

If no failures found, say: "All workflows have a successful latest run — no stale failures."

### Rerunning

Ask the user which (or all) to rerun. For each:

```bash
gh run rerun --failed <run_id>
```

Report success/failure for each rerun attempt.

### Chronically Cancelled Workflows

**Automated (recommended):** the hourly guardian (`scripts/actions_failure_guardian.py`) and local/CI helper (`.github/scripts/workflow_health_check.py`) flag workflows where the **latest completed run on `main` is `cancelled`**, there are **≥4 cancellations** in the last **15** runs, **0 successes** in that window, and there has been **no successful run within 48 hours** in the scanned history (or no success at all in range). Tune with:

- `FAILURE_GUARD_CHRONIC_WINDOW` (default `15`)
- `FAILURE_GUARD_CHRONIC_MIN_CANCELLED` (default `4`)
- `FAILURE_GUARD_CHRONIC_MIN_RUNS` (default `5`)
- `FAILURE_GUARD_CHRONIC_MIN_HOURS_NO_SUCCESS` (default `48`)

For CLI-only ad-hoc scans, workflows whose latest run is `cancelled` with 0 recent successes:

```bash
gh run list --branch main --limit 200 --json workflowName,status,conclusion,createdAt \
  --jq '
    [group_by(.workflowName)[] |
     {name: .[0].workflowName,
      latest: (sort_by(.createdAt) | last | .conclusion),
      success: [.[] | select(.conclusion == "success")] | length,
      cancelled: [.[] | select(.conclusion == "cancelled")] | length,
      total: length} |
     select(.latest == "cancelled" and .success == 0)] |
    sort_by(.cancelled) | reverse |
    .[] | "\(.name)\tcancelled=\(.cancelled)/\(.total)\tsuccess=\(.success)"
  '
```

If found, retrigger them with `gh workflow run "<name>" --ref main`.

### Notes

- The existing `actions-failure-guardian.yml` workflow does this automatically every hour via the GitHub API and posts to Discord. This command is for **manual double-checks** from the CLI.
- Guardian script: `scripts/actions_failure_guardian.py`
- Guardian max age: 72 hours (older failures are skipped)
- If `gh` auth fails, remind user to run `gh auth login` or check `GIT_PAT_CLASSIC` env var.
