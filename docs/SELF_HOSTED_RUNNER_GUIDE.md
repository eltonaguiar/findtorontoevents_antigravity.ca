# Self-Hosted GitHub Actions Runner Guide

Your PC ("elton-pc") is now running a GitHub Actions runner that handles certain workflows locally instead of on GitHub's cloud servers. This guide covers everything you need to know.

---

## Quick Start

- **Installed at:** `E:\actions-runner`
- **Runner name:** `elton-pc`
- **Labels:** `self-hosted`, `Windows`, `X64`
- **Status:** Running and listening for jobs

As long as the runner process is active, it will automatically pick up and execute any workflow configured to use `self-hosted`.

---

## How It Works

1. The runner polls GitHub every ~30 seconds, asking "any jobs for me?"
2. When a workflow file contains `runs-on: self-hosted`, GitHub assigns that job to your PC.
3. The workflow runs locally on your machine, exactly as if you ran the Python scripts yourself.
4. Results (logs, artifacts, dashboard HTML) are reported back to GitHub.

**Why this matters:** Binance and other exchange APIs work reliably because your home IP is not geo-blocked, unlike GitHub's cloud runners which often get rate-limited or blocked.

**Work directory:** Jobs run inside `E:\actions-runner\_work\`. Each repository gets its own subfolder there.

---

## Which Workflows Use Self-Hosted

| Workflow | File | Schedule | Runner |
|----------|------|----------|--------|
| Unified Audit Dashboard | `audit-dashboard.yml` | Every 15 min + on push | **self-hosted** (your PC) |
| Alpha Engine Scanner | `alpha-engine-live.yml` | Every 45 min | **self-hosted** (your PC) |
| Everything else | various | various | `ubuntu-latest` (GitHub cloud) |

Only the two workflows above run on your PC. All other workflows (deploy, scraping, etc.) continue running on GitHub's free cloud runners as before.

---

## Controlling the Runner

### Stop the runner
Close the terminal window where `run.cmd` is running, or press `Ctrl+C` in that terminal.

### Start the runner
Open a terminal and run:
```
cd E:\actions-runner
./run.cmd
```

### Install as a Windows Service (recommended)
This makes the runner start automatically when your PC boots, so you never have to think about it:
```
cd E:\actions-runner
./svc.cmd install
./svc.cmd start
```

### Uninstall the service
If you want to go back to running it manually:
```
cd E:\actions-runner
./svc.cmd stop
./svc.cmd uninstall
```

### Check if the runner is online
```
gh api repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/runners
```
Look for `"status": "online"` next to `elton-pc`.

---

## Performance Impact on Your PC

| State | CPU | RAM | Noticeable? |
|-------|-----|-----|-------------|
| Idle (waiting for jobs) | ~0% | ~30MB | No |
| Running a scan | ~15-20% | ~500MB | Barely — like having an extra browser tab |
| Duration of a scan | — | — | 10-15 minutes |

The runner will not slow down your normal PC usage. You can game, browse, or work while scans run in the background.

**If your PC goes to sleep:** Jobs will queue up on GitHub's side. When your PC wakes up, the runner reconnects and picks up any waiting jobs. Nothing is lost.

---

## When Jobs Run

- **Audit Dashboard:** Every 15 minutes on the clock, plus immediately when you push changes to `template.html`
- **Alpha Engine:** Twice per hour (at :00 and :45)

### Trigger a job manually
You do not have to wait for the schedule. Run either of these anytime:
```
gh workflow run "Unified Audit Dashboard"
gh workflow run "Alpha Engine Live Scanner"
```

### Watch a running job
```
gh run list --limit 5
gh run watch
```

---

## Switching Back to Cloud Runners

If you want to stop using your PC and go back to GitHub's cloud runners:

1. Stop the runner (close the terminal or stop the service).
2. Edit the two workflow files and change `runs-on: self-hosted` back to `runs-on: ubuntu-latest`:
   - `.github/workflows/audit-dashboard.yml`
   - `.github/workflows/alpha-engine-live.yml`
3. Commit and push the change.

That is all. The workflows will start running on GitHub's servers again. Keep in mind that Binance API calls may fail more often on cloud runners due to IP restrictions.

---

## Troubleshooting

### Runner shows as offline on GitHub
- Check that `run.cmd` is actually running (look for the terminal window), or check the Windows service.
- Restart it: `cd E:\actions-runner && ./run.cmd`

### Job is stuck or taking too long
- Check the diagnostic logs at `E:\actions-runner\_diag\`
- Cancel the stuck run: `gh run list` to find the ID, then `gh run cancel <run-id>`

### Permission errors
- Run the terminal as Administrator.
- If using the Windows service, make sure the service account has access to `E:\actions-runner`.

### Job fails on self-hosted but works on ubuntu-latest
- Check that Python is on your system PATH: `python --version`
- Check that required packages are installed: `pip list`
- The cloud runner installs dependencies fresh each time; your PC uses whatever is already installed.

### Runner won't connect after a Windows update
- Restart the runner: stop and start `run.cmd` again.
- If running as a service: `./svc.cmd stop && ./svc.cmd start`

---

## Summary

Your self-hosted runner is a simple, low-impact process that lets your PC handle the two most API-intensive workflows. Everything else stays on GitHub's cloud. If anything goes wrong, you can always switch back by changing two lines in two YAML files.
