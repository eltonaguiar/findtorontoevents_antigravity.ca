# AI Tournament Model Fleet Coverage Fix

Date: 2026-05-28

## What Was Broken

The AI tournament config declares 23 models and 146 model/persona/asset-class assignments, but the dashboard artifacts only showed 3 live models: `deepseek_v4`, `cerebras_llama4`, and `grok3`.

The generator skipped assignments when a provider key was missing or a model API failed, and those skipped models had no durable, machine-readable coverage record. The last scheduled AI tournament run also timed out in `Generate picks fleet` after the 15-minute job limit, so the model-summary and leaderboard artifacts stayed stuck on the 3-model snapshot.

## What Changed

- Added explicit per-assignment coverage fallback rows in `tools/populate_picks.py`.
- Marked fallback rows with `generation_source=coverage_fallback`, `rank_eligible=false`, and `data_integrity_flag=COVERAGE_FALLBACK_NOT_MODEL_API` so they cannot be mistaken for direct model API output.
- Added `data/ai_tournament/model_attempt_log.json` generation so each run records which configured models produced API picks, used fallback coverage, or lacked keys.
- Updated leaderboard and model-summary builders to exclude coverage fallback rows from WR/PF/rank calculations while still showing full configured fleet coverage.
- Increased the AI tournament workflow timeout from 15 to 45 minutes and set explicit API timeout/sleep knobs.
- Updated the tournament page client-side stats so rank-excluded coverage rows do not inflate resolved counts.

## GitHub Actions Findings

Live Actions metadata checked at 2026-05-28 02:22 UTC:

- Last 100 runs: 77 success, 12 failure, 9 skipped, 2 in progress.
- Current long runners: `ALPHA ENGINE - Dynamic Runner` (~24m) and `Gainer Predictor Scanner` (~7m).
- Stale queued runs from 2026-05-27 12:08 UTC still showed no jobs for four workflows: `Claude's Test - Portfolio Manager`, `Gate Config Emit`, `Market Beating System`, and `Deploy findtorontoevents.ca core site`.
- Most repeated recent failure: `Deploy Competition to Live Site`, caused by missing `audit_dashboard/data/claudes_test_state.json` during FTP upload.
- `Audit Hourly Update` failed because `claudes_test_state.json` was missing.
- `Sports endpoint smoke + Playwright` failed because production sports endpoints returned `Sports DB connection failed`.
- The AI tournament scheduled run `26513551034` was cancelled in `Generate picks fleet` after the 15-minute timeout; the prior manual success still only committed 3 model submissions.

## Verification

- `python3 -m py_compile tools/populate_picks.py tools/ai_tournament/update_leaderboard.py tools/ai_tournament/build_model_summary.py`
- Local config inspection confirmed 23 configured models and 146 assignments.
- Local artifact inspection before the fix confirmed `ai_tournament_picks_latest.json`, `ai_tournament_model_summary.json`, and `ai_tournament_leaderboard.json` contained only 3 models.
