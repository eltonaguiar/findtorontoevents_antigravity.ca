# GHA QA Market Validation: missing 5 API secrets

## Problem

The QA Market Validation workflow (`qa-market-validation.yml`) fails every hour. Five API keys required by the price adapters are not set as GitHub Secrets. Without them, adapters 2-6 return `None`, leaving only Stooq (blocked from GitHub runner IPs) and yfinance (flaky in GHA). Result: "ALL 7 sources failed" for every equity ticker.

## Fix

Add the following five secrets via GitHub UI at:

https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/settings/secrets/actions

- `FINNHUB_API_KEY`
- `TIINGO_API_KEY`
- `TWELVE_DATA_API_KEY`
- `ALPHA_VANTAGE_API_KEY`
- `FMP_API_KEY`

## Related PR

PR #786 "fix(ci): restore QA price validation, snapshot pushes, and sports smoke" on branch `wired-in/buffy-gh-actions-fix-2026-11-15`. This PR bundles the secret restoration with the sports smoke pin.

## Why this cannot be fixed via git commit

GitHub Actions secrets are repository-level settings stored in the GitHub UI, not in the repository code. They cannot be added, updated, or committed through git. They must be entered manually through the repository settings page (or via the GitHub API with appropriate permissions).

## Verification

1. Add all five secrets via the GitHub UI above.
2. Trigger the QA Market Validation workflow manually (Actions tab → QA Market Validation → Run workflow).
3. Verify the run completes successfully and no longer reports "ALL 7 sources failed" for equity tickers.
