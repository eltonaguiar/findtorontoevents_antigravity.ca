# Next Steps Plan for WSL Agent

This plan mirrors the recent earnings-filter improvements and ensures the artifacts build and remain verifiable from inside WSL. Follow each step while staying in `/mnt/c/Users/zerou/Documents/TORONTOEVENTS_ANTIGRAVITY`.

## 1. Persist earnings metadata in generated picks
- Inspect `scripts/generate-daily-stocks.ts` (and any other script writing `data/daily-stocks.json`, `data/v2/history/*`, or `public/data/*/current.json`).
- Ensure every `StockPick` that is serialized includes `earningsDate` and `daysToEarnings` so downstream files retain the earnings context for UI/QA.
- Run the generator so the files on `data/` and `public/data/` now show those fields.

## 2. Capture earnings-filter diagnostics
- Inside the same generator loop (before `processAndRankPicks` or during), add a short log entry for each symbol that is disqualified or penalized by `assessEarningsRisk`.
- Include the symbol, the reason (`<3 days` vs `<7 days`), and the computed `daysToEarnings`.
- Flush the log to the console so the CI/test output captures which tickers the filter touched.

## 3. Validate the new data and logs
- Re-run `npm run stocks:v2:full` (and/or `npm run stocks:all`) inside WSL. Watch for the diagnostic log entries and note any API failures or warnings.
- After the run, open `data/daily-stocks.json` and one of the V2 ledger files (`data/v2/history/2026/01/28.json` or similar) to confirm the earnings metadata fields exist on the pick objects.
- Capture a list of the `earningsDate`/`daysToEarnings` pairs for the most recently generated picks; this can be in the log or a short Markdown summary.

## 4. Share artifacts
- Append the key results (metadata presence, filtered symbols log, any test/lint output) back to `__WSL_CHATGPT_2026-01-28T151312Z.MD`.
- Note any remaining blockers (missing ticker data, audit failures, etc.) so we can prioritize follow-up.

Following this plan keeps the pipeline auditable from WSL and ensures the earnings filter remains visible where we need it.
