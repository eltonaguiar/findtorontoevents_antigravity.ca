# GitHub Actions Cloud + WSL Runner Strategy

Date: 2026-03-27
Branch: iron-nutria

## What was changed

1. Dynamic runner selection was applied to workflow jobs that previously used hardcoded `ubuntu-latest`.
2. Cloud remains default through this expression:

```yaml
runs-on: ${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-latest' }}
```

3. Empty `runs-on:` values introduced during the previous migration were repaired across workflows.
4. Local WSL runner support files were added:
- `scripts/start-wsl-runner.ps1`
- `scripts/start-wsl-runner.bat`
- `.github/workflows/wsl-runner-manager.yml`
- `.github/workflows/_dynamic-runner-template.yml`
- `.github/workflows/dynamic-alpha-engine.yml`
- `scripts/check-stale-workflows.ps1`

## Default behavior

- If `ACTIONS_RUNNER_LABEL` is unset: jobs run on GitHub cloud (`ubuntu-latest`).
- If `ACTIONS_RUNNER_LABEL` is set (example: `self-hosted`, `wsl-ubuntu`): jobs run on the self-hosted runner with that label.

## Configure cloud default + optional local override

1. Go to GitHub repository settings.
2. Open `Settings -> Secrets and variables -> Actions -> Variables`.
3. Keep `ACTIONS_RUNNER_LABEL` unset for cloud default.
4. Set `ACTIONS_RUNNER_LABEL=wsl-ubuntu` when you want to route jobs to local WSL.

## Smart skip policy (cloud queue protection)

Target behavior:
- Cloud scheduled runs should skip when a recent local run already completed successfully.

Recommended implementation:
1. Add a lightweight `check_recent_local` job per critical workflow.
2. Query recent runs for the same workflow on `main` and detect a successful run on self-hosted labels within a freshness window (example: 20-30 minutes).
3. Gate cloud jobs with `if` so scheduled cloud runs skip when local is fresh.
4. Keep manual dispatch always runnable.

Pseudo-pattern:

```yaml
jobs:
  check_recent_local:
    runs-on: ubuntu-latest
    outputs:
      skip_cloud: ${{ steps.check.outputs.skip_cloud }}
    steps:
      - id: check
        uses: actions/github-script@v7
        with:
          script: |
            // Find latest successful run of this workflow on self-hosted labels.
            // Set skip_cloud=true if completed within freshness window.

  main_job:
    runs-on: ${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-latest' }}
    if: ${{ github.event_name == 'workflow_dispatch' || needs.check_recent_local.outputs.skip_cloud != 'true' }}
```

## Notes

- Current failing workflow observed during investigation was not runner-capacity related; it failed due to git push/rebase conflicts in job logic.
- VS Code may still show `Context access might be invalid: ACTIONS_RUNNER_LABEL`; this is a linter warning when the variable is not yet defined, not a runtime blocker.

---

## 2026-03-27 Update: Dynamic Runner Routing (Cloud Default + Local Override)

All workflows were updated to use this runner selector:

```yaml
runs-on: ${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-latest' }}
```

### Routing behavior

| ACTIONS_RUNNER_LABEL | Result |
|----------------------|--------|
| **Unset / empty** | Cloud runner (`ubuntu-latest`) |
| `wsl` | Local WSL runner (`wsl-ubuntu`, label `wsl`) |
| `self-hosted` | Any matching self-hosted runner |

### Recommended operating mode

1. Keep cloud as default by leaving `ACTIONS_RUNNER_LABEL` unset.
2. Set `ACTIONS_RUNNER_LABEL=wsl` only when you want jobs routed locally.
3. Use workflow dispatch for priority local runs, especially when cloud queue is busy.

### Set/unset runner variable

```powershell
# Set local routing to WSL
gh variable set ACTIONS_RUNNER_LABEL --body "wsl" --repo eltonaguiar/findtorontoevents_antigravity.ca

# View current variables
gh variable list --repo eltonaguiar/findtorontoevents_antigravity.ca

# Remove override to return to cloud default
gh variable delete ACTIONS_RUNNER_LABEL --repo eltonaguiar/findtorontoevents_antigravity.ca
```

### Start a local run quickly

```powershell
gh workflow run actions-failure-guardian.yml --ref main --repo eltonaguiar/findtorontoevents_antigravity.ca
```

### Monitor jobs (CLI)

```powershell
# Latest runs
gh run list --limit 10 --repo eltonaguiar/findtorontoevents_antigravity.ca

# Latest run for one workflow
gh run list --workflow actions-failure-guardian.yml --limit 1 --repo eltonaguiar/findtorontoevents_antigravity.ca

# Poll one run status
gh api repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/<RUN_ID> --jq '"status=\(.status) conclusion=\(.conclusion)"'

# Confirm which runner executed a job
gh api repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/<RUN_ID>/jobs --jq '.jobs[] | "job=\(.name) runner=\(.runner_name) labels=\(.labels|join(",")) status=\(.status)"'
```

### Monitor jobs (GitHub UI)

1. Open `https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions`
2. Click a run, then open the job.
3. Check the job header for runner name (example: `wsl-ubuntu`) and labels.

### Optional smart skip pattern (queue protection)

Add a pre-check job in critical workflows that:
1. checks if a recent successful self-hosted run already completed,
2. skips scheduled cloud run when that local run is fresh,
3. still allows manual dispatch at all times.

---

*Updated 2026-03-27 by GitHub Copilot (GPT-5.3-Codex) — mirrored runner routing and monitoring instructions from SELF_HOSTED_RUNNER_USAGE.md.*
