---
name: check-gh-actions
description: Use when user asks to check GitHub Actions for failing jobs, chronic cancellations, or jobs without a subsequent successful run. Also for CI/CD health audits, rerunning failed workflows, or monitoring workflow reliability. Aliases - checkGHA, gha_health, github_actions_health, gh_actions, check_actions, fixjob, github_actions, actions_health
---

# Check GitHub Actions Health

Scan all recent GitHub Actions workflow runs on main, detect three classes of problems, and offer to fix them.

## Three Failure Modes

### 1. Stale Failures (no subsequent success)
Workflows whose latest completed run on main is failure/timed_out/startup_failure/stale AND the workflow has NOT had a subsequent successful run since then.

Run this to find them:
```bash
gh run list --branch main --limit 200 --json workflowName,status,conclusion,databaseId,createdAt,url --jq '
  [group_by(.workflowName)[] |
   sort_by(.createdAt) | last |
   select(.status == "completed" and (.conclusion == "failure" or .conclusion == "timed_out" or .conclusion == "startup_failure" or .conclusion == "stale"))] |
  sort_by(.createdAt) | reverse
'
```

Show as a table, then ask to rerun. Use: gh run rerun --failed <run_id>

### 2. Chronic Cancellations
Workflows where the latest run is cancelled AND within the last 15 runs there are at least 4 cancellations with 0 successes and no success in the last 48 hours.

```bash
gh run list --branch main --limit 200 --json workflowName,status,conclusion,createdAt --jq '
  [group_by(.workflowName)[] |
   (. | sort_by(.createdAt)) as $runs |
   {wf: .[0].workflowName,
    latest: ($runs | last | .conclusion),
    cancelled: ([$runs[] | select(.conclusion == "cancelled")] | length),
    success: ([$runs[] | select(.conclusion == "success")] | length),
    total: ($runs | length)} |
   select(.latest == "cancelled" and .cancelled >= 4 and .total >= 5 and .success == 0) |
   {workflow: .wf, cancelled_count: .cancelled, total_runs: .total}
'
```

For each chronically-cancelled workflow, also check if there was any success in the last 48 hours:
```bash
# Replace WORKFLOW_NAME with actual workflow name
gh run list --branch main --limit 200 --json workflowName,status,conclusion,createdAt --jq '
  [group_by(.workflowName)[] |
   select(.[0].workflowName == WORKFLOW_NAME) |
   .[0].runs | [sort_by(.createdAt) | .[] | select(.conclusion == "success")] | last
'
```

If truly chronic (no recent success), retrigger with: gh workflow run NAME --ref main

### 3. Recurring Failures (same workflow failing multiple times in a row)
Check if any workflow has failed 3+ times consecutively without any intervening success:
```bash
gh run list --branch main --limit 100 --json workflowName,status,conclusion,createdAt --jq '
  [group_by(.workflowName)[] |
   (. | sort_by(.createdAt) | reverse | .[0:15]) as $recent |
   {wf: .[0].workflowName,
    fail_count: ([$recent[] | select(.conclusion == "failure")] | length),
    streak_starts: ($recent[0].conclusion)} |
   select(.fail_count >= 3) |
   {workflow: .wf, consecutive_failures: .fail_count, latest: .streak_starts}
'
```

## Presentation

Show results as markdown tables:

STALE FAILURES (no next success):
| Workflow | Conclusion | When | Run ID | Link |

CHRONIC CANCELLATIONS:
| Workflow | Cancelled/Total | Recommended Action |

RECURRING FAILURES:
| Workflow | Consecutive Failures | Latest | Action |

## Fix Actions

- Stale failures: gh run rerun --failed <run_id>
- Chronic cancellations: gh workflow run NAME --ref main
- Recurring failures: gh run rerun --failed <run_id> plus investigate root cause

## Context Gathering

Before rerunning, optionally run: gh run view <run_id> --log

Classify each failure as:
- FLAKY: intermittent, passes on retry
- BROKEN: always fails, needs code fix
- ENV: missing secrets (401/403), rate limits (429), external dependency down
- TIMEOUT: exceeded time limit

## Notes

- The existing actions-failure-guardian.yml workflow does this automatically every hour via the GitHub API and posts to Discord. This skill is for on-demand CLI double-checks.
- Guardian script: scripts/actions_failure_guardian.py
- If gh auth fails, remind user to run gh auth login or check GIT_PAT_CLASSIC / GH_TOKEN env var.
- The --limit 200 covers about 3 days of hourly workflow runs. Adjust upward for longer scan windows.
