# gha_browser — GitHub Actions inspection via a logged-in Chrome

Promoted from session tooling (2026-11-16) so it survives reboots and is fleet-shareable.
HTML-scrapes the GitHub Actions UI through a persistent logged-in Chrome — zero REST API
quota. See `GHACTIONS_2026-11-16/…/AGENT_PROMPT_job_analysis.md` for the methodology.

## Setup (one-time)
    DISPLAY=:0 google-chrome --remote-debugging-port=9222 --remote-allow-origins=* \
      --user-data-dir=$HOME/.cache/gha-scrape-profile --no-first-run \
      --no-default-browser-check https://github.com/login
(log in once; the profile persists the session. Attach: Playwright `connect_over_cdp(9222)`.)

## Tools
- `scrape.py` — `runs "<query>"`, `wf-history <file>`, `run-detail <id>`, `raw <url>`, login helpers.
- `cleanup_branches.py` — safe remote-branch cleanup executor (4 safety rails, dry-run default).
- `delete_runs.py` — UI deletion of phantom runs (needs an admin session; REST delete is 403).
- `gha_health_audit_main.py` — local variant of `tools/gha_health_audit.py` for ad-hoc sweeps.

## Gotchas (hard-won)
- `created:>YYYY-MM-DD` excludes the named DAY (after its end) — use `>=` to include it.
- `on: push` workflows execute the pushed REF's YAML; `schedule` runs only from the default branch.
- Phantom queued runs are uncancelable (REST 409/403, UI fails) — GitHub Support item.
