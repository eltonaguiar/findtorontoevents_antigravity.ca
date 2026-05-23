# findtorontoevents.ca deploy gap fix

## What was broken

On April 17, 2026, the live site at `https://findtorontoevents.ca/next/events.json` was still serving the older 2,928-event payload even though the repository already had the newer 3,351-event `events.json` on `main`.

The root cause was deployment coverage:

- `.github/workflows/deploy-fte-index.yml` only uploaded `TORONTOEVENTS_ANTIGRAVITY/index.html`
- it never uploaded `events.json` or refreshed `/next/events.json`
- `.github/workflows/scrape-events.yml` commits with `[skip ci]`, so a plain `push`-only deploy workflow would still miss the daily scraper refreshes

That left production in a split-brain state:

- live HTML could be newer
- live event data stayed stale

## What changed

Updated `.github/workflows/deploy-fte-index.yml` to deploy the core Toronto Events site, not just the HTML shell:

- trigger on pushes to `TORONTOEVENTS_ANTIGRAVITY/index.html`, `events.json`, `next/events.json`, and `last_update.json`
- trigger on successful completion of the `Scrape events` workflow via `workflow_run`
- validate local payloads before FTP upload
- upload:
  - `TORONTOEVENTS_ANTIGRAVITY/index.html` -> `/findtorontoevents.ca/index.html`
  - `events.json` -> `/findtorontoevents.ca/events.json`
  - `events.json` -> `/findtorontoevents.ca/next/events.json`
  - `last_update.json` -> `/findtorontoevents.ca/last_update.json` when present
- verify deployment by comparing local and remote SHA-256 hashes for both the HTML and `/next/events.json`

Updated `.github/workflows/scrape-events.yml` to harden the producer side:

- validate `events.json`, `next/events.json`, and `last_update.json` before commit
- assert `events.json` and `next/events.json` have the same event count
- run `.github/scripts/assert_no_conflict_markers.sh` before the automated commit

## How it was verified

Local verification completed in the clean PR worktree:

- reproduced the production mismatch:
  - live `https://findtorontoevents.ca/next/events.json` had `2928` events
  - repo `events.json` had `3351` events
- confirmed recent fixes already existed in Git history:
  - `6ca61bb89b` — date-string past-event filter fix
  - `7079b7069e` — April 17 dating/event payload fix
- confirmed the remaining gap was deployment, not missing source data
- validated JSON parity locally:
  - `events.json` count = `3351`
  - `next/events.json` count = `3351`

Recommended follow-up after merge:

- let the updated deploy workflow run once against `main`
- confirm the remote `/next/events.json` hash matches the repo `events.json`
- re-check the Today filter in Toronto timezone on the live site
