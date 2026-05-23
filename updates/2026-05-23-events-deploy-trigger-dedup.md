# 2026-05-23 - Events deploy trigger dedup optimization

## Why

After fixing the stale-events root cause, the events pipeline had redundant trigger fan-out:
- `Scrape events` commit caused both deploy workflows to trigger via `push`
- and both deploy workflows also had `workflow_run` on `Scrape events`

That produced duplicate deploy runs for the same scrape payload.

## What changed

1. `.github/workflows/deploy-fte-index.yml`
- Removed scrape data files from `on.push.paths`:
  - `events.json`
  - `next/events.json`
  - `last_update.json`
- Kept `workflow_run` on `Scrape events`.
- Kept push trigger for homepage/static deploy edits:
  - `TORONTOEVENTS_ANTIGRAVITY/index.html`
  - `TORONTOEVENTS_ANTIGRAVITY/next_htaccess`
  - workflow file itself

2. `.github/workflows/deploy-fte-events-json.yml`
- Removed `on.push` trigger block.
- Kept `workflow_run` on `Scrape events`.
- Kept `workflow_dispatch` for manual recovery runs.

## Result

Routine scrape cycles now trigger one run per deploy workflow via `workflow_run`, reducing duplicate deploy executions while preserving resiliency and manual fallback.
