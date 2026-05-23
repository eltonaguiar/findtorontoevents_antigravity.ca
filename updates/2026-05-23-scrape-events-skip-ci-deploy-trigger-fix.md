# Fix: Scrape Events Commit No Longer Suppresses Deploy Workflows

## What Was Broken

The scraper workflow committed fresh event artifacts with `[skip ci]`:

- `.github/workflows/scrape-events.yml`
- Commit message previously: `chore: update events from scraper (GitHub Actions) [skip ci]`

This suppressed downstream push-triggered workflows, including the events/metadata deploy path used to publish freshness files to production FTP. Result: `last_update.json` could be fresh while live `metadata.json` remained stale.

## What Changed

Updated scraper commit message to remove the CI-suppression token:

- New message: `chore: update events from scraper (GitHub Actions)`

## Why This Fix Is Safe

`deploy-fte-events-json.yml` already has path filters for events/metadata files. Removing `[skip ci]` allows the correct deploy workflow to run without triggering unrelated workflows broadly.

## Verification Notes

- Confirmed stale symptom before fix: live `/metadata.json` lagged while `/last_update.json` was current.
- Confirmed scraper writes events/metadata and pushes to `main`.
- This fix restores downstream workflow eligibility on those push commits.
