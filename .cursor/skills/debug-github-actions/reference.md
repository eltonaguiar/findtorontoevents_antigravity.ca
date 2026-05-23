# Debug GitHub Actions — Reference

Detailed troubleshooting patterns, API recipes, and advanced diagnostics.

## Installing gh CLI

### Windows (winget)
```powershell
winget install --id GitHub.cli
```

### Windows (scoop)
```powershell
scoop install gh
```

### macOS
```bash
brew install gh
```

### Linux (Debian/Ubuntu)
```bash
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli-stable.list > /dev/null
sudo apt update && sudo apt install gh
```

After install: `gh auth login` and follow the prompts.

## GitHub REST API recipes (without gh)

All examples assume `GITHUB_TOKEN` is set and `OWNER_REPO` is `owner/repo`.

### Detect owner/repo from git remote

```bash
OWNER_REPO=$(git remote get-url origin | sed -E 's#.*github\.com[:/](.+?)(\.git)?$#\1#')
```

### List workflows

```bash
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER_REPO/actions/workflows" | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
for w in data['workflows']:
    print(f\"{w['id']:>10}  {w['state']:10}  {w['name']}\")
"
```

### List recent runs

```bash
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER_REPO/actions/runs?per_page=15" | \
  python3 -c "
import sys, json
for r in json.load(sys.stdin)['workflow_runs']:
    print(f\"{r['id']}  {r['status']:12}  {r['conclusion'] or 'n/a':12}  {r['name']:40}  {r['created_at']}\")
"
```

### Get failed jobs for a run

```bash
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER_REPO/actions/runs/<RUN_ID>/jobs" | \
  python3 -c "
import sys, json
jobs = json.load(sys.stdin)['jobs']
for j in jobs:
    if j['conclusion'] == 'failure':
        print(f\"FAILED JOB: {j['name']} (id={j['id']})\")
        for s in j['steps']:
            status = '  FAIL' if s['conclusion'] == 'failure' else '    ok'
            print(f\"  {status}  Step {s['number']}: {s['name']}\")
"
```

### Download and inspect logs

```bash
# Download as zip
curl -sL -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER_REPO/actions/runs/<RUN_ID>/logs" \
  -o /tmp/gh_actions_logs.zip

# Extract and search for errors
cd /tmp && unzip -o gh_actions_logs.zip -d gh_actions_logs/
grep -rn -i "error\|fail\|fatal\|exception" gh_actions_logs/ | head -50
```

### Re-run a failed run

```bash
curl -X POST -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER_REPO/actions/runs/<RUN_ID>/rerun-failed-jobs"
```

### Trigger workflow_dispatch

```bash
curl -X POST -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -d '{"ref":"main"}' \
  "https://api.github.com/repos/$OWNER_REPO/actions/workflows/<WORKFLOW_ID>/dispatches"
```

To include inputs:
```bash
curl -X POST -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -d '{"ref":"main","inputs":{"type":"both","pages":"3"}}' \
  "https://api.github.com/repos/$OWNER_REPO/actions/workflows/<WORKFLOW_ID>/dispatches"
```

### Cancel a running workflow

```bash
curl -X POST -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER_REPO/actions/runs/<RUN_ID>/cancel"
```

### Check repo secrets (names only — values are never exposed)

```bash
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER_REPO/actions/secrets" | \
  python3 -c "import sys,json; [print(s['name']) for s in json.load(sys.stdin)['secrets']]"
```

## Advanced diagnostic patterns

### Pattern: Flaky tests / intermittent failures

1. List the last 10 runs and check conclusion:
   ```bash
   gh run list --workflow <file>.yml --limit 10
   ```
2. If a mix of success/failure, the issue is likely:
   - Network timeout (API call, curl, FTP)
   - Race condition in cron schedule
   - Rate limiting from external API
3. **Fix**: Add retry logic, increase `--max-time` on curl, or add `continue-on-error: true` for non-critical steps.

### Pattern: Workflow never triggers (schedule)

1. Check if repo has been inactive > 60 days (GitHub disables crons).
2. Go to Actions tab > select the workflow > click "Enable workflow" or push a commit.
3. Verify the cron expression at https://crontab.guru/
4. Confirm the workflow file is on the **default branch** (schedule triggers only run from the default branch).

### Pattern: Workflow runs but produces no output / empty artifacts

1. Check if the `run:` step's working directory is correct.
2. Verify file paths are relative to the repo root (not the workflow file location).
3. Check if `actions/upload-artifact` path matches what was produced.
4. Look for silent failures: a command that exits 0 but produces no output.

### Pattern: FTP deploy fails in CI

Common in this project (fetch-movies, kimi-fetch-movies):

1. **Check secrets**: `FTP_HOST`, `FTP_USER`, `FTP_PASS` must be set in repo settings.
2. **lftp vs Python ftplib**: Some workflows use `lftp` (needs `apt-get install lftp`), others use Python ftplib.
3. **SSL issues**: Try `set ftp:ssl-allow no` in lftp, or use explicit TLS in Python.
4. **Path issues**: FTP path must match the hosting structure (e.g. `/findtorontoevents.ca/movieshows2/`).

### Pattern: Git push fails in workflow

1. Ensure `permissions: contents: write` is set.
2. Use the `GITHUB_TOKEN` secret (automatic) or a PAT.
3. Push URL format: `https://x-access-token:${GH_TOKEN}@github.com/OWNER/REPO.git`
4. Configure git identity:
   ```yaml
   - run: |
       git config user.name "github-actions[bot]"
       git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
   ```
5. Avoid pushing to protected branches without appropriate rules/bypass.

### Pattern: Post-checkout step fails (exit 128)

Seen with broken submodules. Fix:

```yaml
# Before checkout won't help — add AFTER checkout
- name: Fix broken submodule entry
  run: |
    if [ -f .gitmodules ]; then
      git config -f .gitmodules --remove-section submodule.STOCKSUNIFY 2>/dev/null || true
    fi

# At the end of the job, with if: always()
- name: Restore workspace for checkout post
  if: always()
  run: |
    git checkout --detach ${{ github.sha }}
    git reset --hard ${{ github.sha }}
```

## YAML validation

### Quick Python check

```python
import yaml, sys
try:
    with open(sys.argv[1]) as f:
        yaml.safe_load(f)
    print("YAML is valid")
except yaml.YAMLError as e:
    print(f"YAML error: {e}")
    sys.exit(1)
```

### Common YAML gotchas in GitHub Actions

| Issue | Example | Fix |
|-------|---------|-----|
| Unquoted `on:` | `on: push` works but `on:` alone is truthy | Always fine in GH Actions context |
| Expression without quotes | `if: github.event.schedule == 0 13 * * *` | Wrap in quotes: `if: github.event.schedule == '0 13 * * *'` |
| Multiline `run` without `\|` | `run: echo a echo b` | Use `run: \|` for multiline |
| Tab indentation | Tabs anywhere | YAML requires spaces only |
| Env var in wrong scope | `env:` at job level vs step level | Place `env:` at the correct level |

## Cron expression reference

| Expression | Meaning |
|-----------|---------|
| `0 12 * * *` | Daily at 12:00 UTC |
| `0 13 * * *` | Daily at 13:00 UTC (8 AM ET in winter) |
| `0 */2 * * *` | Every 2 hours |
| `*/5 * * * *` | Every 5 minutes |
| `0 6 * * *` | Daily at 6:00 UTC |
| `0 13 * * 1` | Mondays at 13:00 UTC |

**Note**: GitHub Actions cron is always UTC. Eastern Time offset: UTC-5 (EST) or UTC-4 (EDT).

## Action version reference (current as of 2026)

| Action | Recommended version |
|--------|-------------------|
| `actions/checkout` | `@v4` |
| `actions/setup-python` | `@v5` |
| `actions/setup-node` | `@v4` |
| `actions/upload-artifact` | `@v4` |
| `actions/download-artifact` | `@v4` |
| `actions/upload-pages-artifact` | `@v3` |
| `actions/deploy-pages` | `@v4` |
| `actions/cache` | `@v4` |
| `shivammathur/setup-php` | `@v2` |
