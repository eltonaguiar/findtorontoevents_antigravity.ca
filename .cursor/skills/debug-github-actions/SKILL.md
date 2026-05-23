---
name: debug-github-actions
description: Debug, test, and fix errors in remote GitHub Actions workflows. Use when a workflow fails, the user reports a GitHub Actions error, wants to inspect run logs, re-run a workflow, fix YAML syntax, secrets issues, or diagnose scheduling/permission/checkout problems.
---

# Debug GitHub Actions

Use this skill when the user asks to **debug a GitHub Action**, **fix a failing workflow**, **check why a workflow failed**, **inspect run logs**, **re-run a workflow**, or **troubleshoot CI/CD issues**.

## Prerequisites

- **`gh` CLI**: Preferred tool for interacting with GitHub Actions. If not installed, install it first (see [reference.md](reference.md) section "Installing gh CLI"). If installation is not possible, use the GitHub REST API via `curl` with a `GITHUB_TOKEN`.
- **Repository**: Must be a git repo with a GitHub remote. Detect the owner/repo from `git remote -v`.

## 1. Identify the problem

Determine what to debug. Ask the user (or infer from context):

1. **Which workflow?** — Get the workflow file name or let the user pick from the list.
2. **What's the symptom?** — Failed run, never triggers, wrong schedule, secrets not available, permission denied, etc.

If unclear, list all workflows and their recent status:

```bash
gh workflow list --all
gh run list --limit 10
```

Or without `gh`:

```bash
OWNER_REPO=$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/')
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER_REPO/actions/runs?per_page=10" | \
  python3 -c "import sys,json; runs=json.load(sys.stdin)['workflow_runs']; [print(f'{r[\"status\"]:12} {r[\"conclusion\"]:12} {r[\"name\"]:40} {r[\"created_at\"]}') for r in runs]"
```

## 2. Read the workflow YAML

Read the workflow file from `.github/workflows/`:

```
.github/workflows/<workflow-name>.yml
```

Check for common YAML issues:
- [ ] Valid YAML syntax (indentation, colons, quotes)
- [ ] `on:` trigger is correct (schedule cron, push branches, workflow_dispatch)
- [ ] `runs-on:` is a valid runner (e.g. `ubuntu-latest`)
- [ ] `uses:` actions reference valid versions (e.g. `actions/checkout@v4`)
- [ ] `env:` / `secrets:` references match what's configured in repo settings
- [ ] `permissions:` block grants needed access (contents, pages, id-token, etc.)
- [ ] No deprecated actions or Node 12/16 warnings

## 3. Fetch and inspect run logs

Get the logs for the most recent (or specific) failed run:

```bash
# List recent runs for a specific workflow
gh run list --workflow <workflow-file.yml> --limit 5

# View details of a specific run (shows each step + status)
gh run view <run-id>

# Download full logs
gh run view <run-id> --log
gh run view <run-id> --log-failed   # only failed steps
```

Without `gh`:

```bash
# Get run ID from the runs list
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER_REPO/actions/runs?per_page=5" | \
  python3 -c "import sys,json; [print(f'{r[\"id\"]} {r[\"conclusion\"]:12} {r[\"name\"]}') for r in json.load(sys.stdin)['workflow_runs']]"

# Get jobs for a run
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER_REPO/actions/runs/<run-id>/jobs" | \
  python3 -m json.tool

# Download logs (zip)
curl -sL -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER_REPO/actions/runs/<run-id>/logs" -o logs.zip
```

## 4. Diagnose common failures

### 4.1 YAML syntax errors
- Validate locally: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/<file>.yml'))"`
- Or use: `npx action-validator .github/workflows/<file>.yml`
- Fix indentation, missing quotes around expressions like `${{ }}`, and bad anchors.

### 4.2 Secret / environment variable issues
- **Symptom:** `Unauthorized`, empty env var, `secret not found`
- **Check:** Repo Settings > Secrets and variables > Actions — verify the secret name matches `${{ secrets.SECRET_NAME }}` exactly (case-sensitive).
- **Fix:** If a secret is missing, tell the user to add it in GitHub repo settings. The agent cannot create secrets remotely.

### 4.3 Permission errors
- **Symptom:** `Resource not accessible by integration`, `403`, `refusing to allow`
- **Check:** The `permissions:` block in the workflow YAML. Common needed permissions:
  - `contents: write` — for git push
  - `pages: write` + `id-token: write` — for GitHub Pages deploy
  - `actions: read` — for reusable workflows
- **Fix:** Add or expand the `permissions:` block. If the repo has restricted default permissions (Settings > Actions > General > Workflow permissions), suggest switching to "Read and write" or adding explicit permissions.

### 4.4 Checkout / submodule failures
- **Symptom:** `fatal: No url found for submodule`, exit code 128 on post-checkout
- **Pattern in this project:** The STOCKSUNIFY submodule entry is broken. Fix:
  ```yaml
  - name: Fix broken submodule entry
    run: |
      if [ -f .gitmodules ]; then
        git config -f .gitmodules --remove-section submodule.STOCKSUNIFY 2>/dev/null || true
      fi
  ```
- Add a "Restore workspace" step at the end with `if: always()` to prevent post-checkout failures.

### 4.5 Schedule / cron issues
- **Cron not firing:** GitHub disables scheduled workflows after 60 days of repo inactivity. Re-enable via repo Actions tab or push a commit.
- **Wrong timezone:** Cron in GitHub Actions is always UTC. Convert carefully (e.g. 8 AM ET = 13:00 UTC, or 12:00/13:00 depending on DST).
- **Too frequent:** GitHub may throttle crons that run more often than every 5 minutes. Minimum practical interval is `*/5 * * * *`.

### 4.6 Script / command failures
- **Symptom:** Non-zero exit code in a `run:` step
- Read the error output from the logs (step 3). Common causes:
  - Missing dependencies (`pip install`, `apt-get install`)
  - Wrong working directory (`working-directory:` or `cd` needed)
  - API endpoint returning error (check HTTP status codes in curl output)
  - File not found (path relative to repo root, not workflow file)

### 4.7 Deprecated actions / Node version warnings
- **Symptom:** `Node.js 16 actions are deprecated`, warnings about v3 actions
- **Fix:** Update action versions: `actions/checkout@v4`, `actions/setup-python@v5`, `actions/upload-artifact@v4`, `actions/upload-pages-artifact@v3`, `actions/deploy-pages@v4`

### 4.8 Git push failures in workflows
- **Symptom:** `refusing to allow a GitHub App to create or update workflow files`, `Permission denied`
- **Fix:** Ensure `permissions: contents: write`, use `${{ secrets.GITHUB_TOKEN }}` or a PAT, and avoid pushing changes to `.github/workflows/` with the default token.

## 5. Fix the workflow

1. **Edit** the workflow YAML file to fix the identified issue.
2. **Validate** the YAML locally (see 4.1).
3. **Commit and push** the fix to the branch that triggers the workflow.
4. **Do NOT** add `workflow_dispatch` unless already present — if you need to test, suggest the user trigger manually from the Actions tab, or add `workflow_dispatch` temporarily.

## 6. Re-run and verify

After pushing the fix:

```bash
# Re-run the most recent failed run
gh run rerun <run-id>

# Or trigger a workflow_dispatch run
gh workflow run <workflow-file.yml>

# Watch the run in real-time
gh run watch <run-id>
```

Monitor until completion. If it fails again, loop back to step 3.

Without `gh`, tell the user to navigate to the Actions tab on GitHub and click "Re-run all jobs", or use:

```bash
curl -X POST -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER_REPO/actions/runs/<run-id>/rerun"
```

## 7. Verify fix is permanent

- Check the workflow passes on the next scheduled run (if cron-based).
- Confirm no new warnings or deprecation notices.
- If the workflow pushes commits (like scrape-events), verify the commit appears on the target branch.

## 8. Project-specific patterns

This project has several workflows with known patterns:

| Workflow | Key secrets | Common issues |
|----------|------------|---------------|
| `scrape-events.yml` | `GITHUB_TOKEN` | Submodule fix needed, ModSecurity blocking sync POST |
| `fetch-movies.yml` | `FTP_HOST/USER/PASS`, `MS2_SYNC_KEY` | FTP deploy, curl timeout |
| `kimi-fetch-movies.yml` | `FTP_*`, `TMDB_API_KEY`, `EJAGUIAR1_TVMOVIESTRAILERS` | PHP setup, lftp install |
| `check-streamer-status.yml` | (none) | Python script errors, API rate limits |
| `send-event-notifications.yml` | `EVENT_NOTIFY_API_KEY` | API key missing, endpoint down |
| `update-creator-news.yml` | (none) | Endpoint returning non-JSON |
| `deploy-pages.yml` | (auto) | Pages not enabled, path rewriting |

## 9. Checklist before "done"

- [ ] Root cause identified and explained to user
- [ ] Workflow YAML validated (syntax, secrets, permissions)
- [ ] Fix applied and committed (if code change needed)
- [ ] Workflow re-run and passed (or user instructed to trigger)
- [ ] No new warnings or deprecation notices
- [ ] If secrets-related: user informed which secrets to add/update (agent cannot set secrets)

## Automated deep scan (latest + prior on failure)

For a **repo-wide** log pass (one latest run per workflow, plus the **prior** run when the latest did not succeed), use:

- **Cursor command:** `/gha-deep-scan-run-logs` → [gha-deep-scan-run-logs.md](../../commands/gha-deep-scan-run-logs.md)
- **Skill:** [gha-run-log-deep-scan](../gha-run-log-deep-scan/SKILL.md)
- **Scripts:** `tools/gha_latest_prior_log_scan.py`, `tools/gha_merge_deep_scan_parts.py`
- **Output:** `docs/GHA_DEEP_SCAN_LATEST_PRIOR.md`

## Additional resources

- For detailed troubleshooting patterns and API reference, see [reference.md](reference.md)
- For automated log inspection, run: `python .cursor/skills/debug-github-actions/scripts/gh_actions_debug.py`
