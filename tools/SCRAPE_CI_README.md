# Scrape events – local debug and re-run

## Run scraper like GitHub Actions (local)

Simulates the CI job: install deps, verify imports, run scraper. Use this to debug failures locally.

**Windows (PowerShell):**
```powershell
.\tools\run_scraper_like_ci.ps1
```

**Linux/macOS:**
```bash
./tools/run_scraper_like_ci.sh
```

Run from the **repo root**.

## Trigger and watch the GitHub Actions workflow

Requires `GITHUB_TOKEN` (PAT with `repo` + `workflow` scope).

**Trigger and wait for result:**
```bash
python tools/trigger_and_watch_scrape_workflow.py
```

**Trigger only (no wait):**
```bash
python tools/trigger_and_watch_scrape_workflow.py --trigger
```

**Watch latest run only (e.g. after manual trigger):**
```bash
python tools/trigger_and_watch_scrape_workflow.py --watch
```

**PowerShell (trigger only):**
```powershell
$env:GITHUB_TOKEN = 'your_pat'
.\tools\trigger_scrape_workflow.ps1
```

## Workflow file

- `.github/workflows/scrape-events.yml` – installs `requests beautifulsoup4 lxml` explicitly (no file path), verifies scraper imports, then runs `python tools/scrape_and_sync_events.py`. Runs **daily** on schedule (12:00 UTC) and on manual trigger; pushes updated `events.json` and `last_update.json` to `main` so the web app pulls the latest events.

## Submodule exception (STOCKSUNIFY)

- **STOCKSUNIFY** is a [git submodule](https://git-scm.com/book/en/v2/Git-Tools-Submodules) pointing at [github.com/eltonaguiar/stocksunify](https://github.com/eltonaguiar/stocksunify). The scrape workflow does not use it; it only updates events. To avoid the checkout action’s post step failing (git 128), the workflow removes the broken STOCKSUNIFY entry from `.gitmodules` after checkout. The STOCKSUNIFY code lives in the repo at `STOCKSUNIFY/` (and may also be under `TORONTOEVENTS_ANTIGRAVITY/STOCKS`). This is an exception for CI only.
