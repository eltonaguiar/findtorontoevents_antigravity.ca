# AI Tournament Model Fleet Coverage Fix

Date: 2026-05-28

## What Was Broken

- `config/model_persona_mapping.json` declares 23 tournament models and 146 model/persona/asset-class assignments.
- The latest generated tournament artifacts only exposed 3 models (`grok3`, `deepseek_v4`, `cerebras_llama4`) in `audit_dashboard/data/ai_tournament_picks_latest.json`, `ai_tournament_model_summary.json`, and `ai_tournament_leaderboard.json`.
- `tools/populate_picks.py` skipped every assignment with a missing key, failed API call, or empty model response. If any provider succeeded, the historical fallback did not fill the rest of the configured fleet, so most models disappeared from the dashboard.
- The scheduled AI tournament workflow run `26513551034` was canceled in the `Generate picks fleet` step after the job hit its 15-minute timeout.

## What Changed

- Added explicit per-assignment coverage fallback rows in `tools/populate_picks.py`. These rows keep all configured models and assignments visible even when an API key is missing or a provider fails.
- Marked coverage fallback rows with provenance fields:
  - `generation_source: coverage_fallback`
  - `api_status`
  - `rank_eligible: false`
  - `rank_exclusion_reason`
  - `data_integrity_flag: COVERAGE_FALLBACK_NOT_MODEL_API`
- Added `data/ai_tournament/model_attempt_log.json` generation so workflow runs report which models had API success, missing keys, or coverage fallback.
- Added a stale snapshot guard so an existing same-day picks file with partial model coverage is regenerated instead of skipped.
- Updated leaderboard and model summary builders to exclude coverage fallback rows from win rate, profit factor, resolved-pick counts, and ranking.
- Updated the browser-side tournament stats to count fallback rows as coverage only, not scored performance.
- Increased `.github/workflows/ai-tournament-pipeline.yml` timeout from 15 to 45 minutes and added bounded API timeout/sleep settings for the picks fleet step.

## GitHub Actions Findings

Reviewed recent Actions history on 2026-05-28.

- Recent run mix: 77 successful, 12 failed, 9 in progress, and 2 skipped across the sampled 100 runs.
- Long-running active jobs included `ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds` around 14 minutes, multiple `Branch Large File Duplicate Guard` runs between 5 and 14 minutes, and `Cross-System Signal Aggregator` around 7 minutes.
- The AI tournament scheduled run `26513551034` canceled during `Generate picks fleet`; the prior manual run `26479021538` succeeded in under 3 minutes but still produced only 3 model submissions.
- Repeated failures in the latest sample were concentrated in `CI Tests` (8), `Branch Large File Duplicate Guard` (2), `Mercury 2 Signal Scanner` (1), and `Claude Gainer ML Live Scanner` (1). Earlier same-session diagnostics also found failures in `Deploy Competition to Live Site`, `Audit Hourly Update`, `Sports endpoint smoke + Playwright`, and `Claude's Test - Portfolio Manager`.
- Queue or runner delays were visible on `Mercury 2 Signal Scanner` around 20 minutes and `ALPHA ENGINE - Dynamic Runner` around 17 minutes.
- Stale queued workflow runs from 2026-05-27 around 12:08 UTC had no jobs attached for `Claude's Test - Portfolio Manager`, `Gate Config Emit`, `Market Beating System`, and `Deploy findtorontoevents.ca core site`.
- Failure log themes:
  - Missing `audit_dashboard/data/claudes_test_state.json` blocked audit/deploy jobs.
  - Sports smoke tests hit `Sports DB connection failed`.
  - Gainer ML scanner failed because trained model files were missing.
  - CI failures included geomean annualized clamp, HF conviction tier, ETF VIX gate, noncrypto resolver time-exit, missing tracked `strategy_performance.json`, missing Toronto audit docx, and VIX/yield-curve ordering checks.

## Why This Fix

The dashboard needs to show the full configured model fleet, but the leaderboard must only rank real model output. The new coverage fallback makes missing models obvious without pretending those rows are model predictions. This bridges the visibility gap now and leaves an audit trail for the next step: adding or repairing API secrets/providers so fallback rows are replaced by real model responses.

## Verification

- `python3 -m py_compile tools/populate_picks.py tools/ai_tournament/update_leaderboard.py tools/ai_tournament/build_model_summary.py`
- Verified coverage fallback generation creates 146 unranked rows across all 23 configured models.
- Verified leaderboard and model summary exclude `coverage_fallback` rows from resolved/scored metrics.
- Verified the workflow YAML parses and the AI tournament job timeout is 45 minutes.
