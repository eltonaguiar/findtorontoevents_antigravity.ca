# 2026-05-28 AI tournament fleet gap + GitHub Actions audit

## What was broken

`/audit/ai-tournament.html` looked like the tournament only had **3 models**, even though the repo now registers **23** models in `config/model_persona_mapping.json`.

The deeper issue was twofold:

1. **The live tournament artifacts were stale.**
   - Last successful tournament pipeline run: `26479021538` on 2026-05-26.
   - That run used a **10-model / 55-assignment** config.
   - The next tournament run (`26513551034`, 2026-05-27) was **cancelled after ~15 minutes** during `Generate picks fleet`.
   - That left the live page serving old `ai_tournament_model_summary.json`, which still only reflected the pre-expansion fleet.

2. **The page hardcoded model status rows.**
   - The HTML claimed models were ACTIVE/PENDING from a static table.
   - It did not consume any generated diagnostics explaining whether a model had a key, produced picks, or was blocked.

## What I changed

1. **Scaled the tournament generator for a larger fleet**
   - `tools/populate_picks.py` now executes model/persona prompts with a bounded `ThreadPoolExecutor`.
   - Added per-key throttling so one provider/key cannot fan out unbounded requests.
   - Preserved deterministic output order by sorting results back to task sequence before writing picks.
   - Wired the existing `AI_TOURNAMENT_API_TIMEOUT_SECONDS` env setting through the actual API calls.

2. **Added generated fleet diagnostics**
   - New script: `tools/ai_tournament/build_model_diagnostics.py`
   - Output: `audit_dashboard/data/ai_tournament_model_diagnostics.json`
   - It compares:
     - configured models
     - runner key availability
     - today's submission envelopes
     - historical model summary
   - It classifies each model as:
     - `active_today`
     - `configured_no_picks`
     - `configured_no_submission`
     - `blocked_missing_key`
     - `historical_only`

3. **Updated the tournament workflow**
   - Added bounded worker env vars
   - Added diagnostics generation to the workflow
   - Added the diagnostics JSON to the committed artifacts

4. **Updated `/audit/ai-tournament.html`**
   - Replaced the stale hardcoded model-status rows with a live-rendered table driven by `ai_tournament_model_diagnostics.json`
   - Added a diagnostics summary line showing:
     - active today
     - configured with keys
     - blocked by missing key
     - refresh time

5. **Added tests**
   - Deterministic ordering for parallel pick collection
   - Diagnostics classification for active / missing-key / no-picks cases

## GitHub Actions findings

### Tournament-specific root cause

- **AI Tournament Pipeline — Daily Picks + DB Ingest**
  - Last success: `26479021538`
  - Last failed progression: `26513551034`
  - Failure mode: **timeout / cancelled during `Generate picks fleet`**
  - Why it mattered: the expanded fleet never made it through artifact generation, so the live page kept showing stale 3-model data.

### Current stale failures on `main` at audit time

- `Audit Hourly Update` -> failed in `Run generate_hourly_update.py`
- `CI Tests` -> failed in `Run all tests`
- `Claude Code Gainer ML Tracker` -> failed in `Run live predictions`
- `Claude Gainer ML Live Scanner` -> failed in `Run live scanner`
- `Claude's Test - Portfolio Manager` -> failed in `Run portfolio manager`
- `ML Feedback Retrain Learn from Closed Trades` -> failed in `Run feedback trainer`
- `Mercury 2 Signal Scanner` -> failed in `Run Mercury 2 scanner`
- `Sports endpoint smoke + Playwright` -> failed in `Run pytest smoke suite (live production endpoints)`

No chronic cancellation cluster was found from the last-15-run scan, but the tournament pipeline timeout was a real single-workflow delay/failure that directly explained the live fleet gap.

## Why this bridges the gap

This change does **not** invent secrets or provider access that do not exist, but it fixes the two repo-level blockers that were under version control:

1. the tournament pipeline was not scaled for the expanded model fleet
2. the page hid the true configured-vs-active state behind static rows

After this PR, the page can truthfully show the full fleet picture, and the pipeline has a much better chance of actually generating picks for the larger registered model set instead of timing out before publish.
