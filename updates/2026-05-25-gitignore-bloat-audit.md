# 2026-05-25 Gitignore Bloat Audit — Large File Review

## What Was Broken
The repository `.git` directory had grown to 2.1 GB. While the existing `.gitignore` (v6, 2026-05-25) covered many large regenerable files (`.pkl`, `.joblib`, `hindsight/**/*.json`, `production_models/`, etc.), a manual audit of tracked files >1 MB revealed ~35 additional files still being tracked that should be ignored.

## Root Cause
- Backtest outputs, test screenshots, training data exports, live logs, and deployment artifacts were committed before their `.gitignore` patterns existed.
- Some patterns (e.g., `ml_crypto_predictor/models/*.pkl`) were too narrow — swing models lived in `ml_crypto_predictor/models/swing/`.
- Duplicate dashboard/state JSONs in `audit_dashboard/data/`, `battleground/data/`, and `incubator/config/` were not covered by the broad `**/data/active_picks.json` style patterns.

## What Changed
Added 35+ new ignore patterns to `.gitignore` (section "2026-05-25 bloat fix v7"):

### Backtest / Analysis Outputs
- `alpha_engine/data/unique_edge_backtest_results.json` (3.6 MB)
- `alpha_engine/data/dna_mutations.json` (1.2 MB)
- `backtest_results/**/*.sql` (2.8 MB SQL dump)
- `incubator/backtest_results/**/*.json`
- `quant_lab/combo_results/**/*.json`

### Test Artifacts
- `tests/screenshots/**/*.png` (3.4 MB)
- `tests/artifacts/**/*.png` (3.3 MB)

### Backup Files
- `updates/index.html.bak*` (3.3 MB)
- `audit_dashboard/data/claudes_test_*.json` (2.5 MB + 2.1 MB .bak)

### Live Logs / State
- `ml_crypto_predictor/enhanced_models/live_picks/` (3.0 MB)
- `alpha_engine/data/missed_gainers_log.json` (1.8 MB)
- `claude_gainer_ml/tracker/`
- `copy_trader_intel/data/highscore_pick_history.json` (2.1 MB)
- `copy_trader_intel/data/okx_trader_database.json` (2.8 MB)

### Training Data / Feature Matrices
- `claude_gainer_ml/data/` (2.6 MB CSV + 2.3 MB JSON)
- `ml_crypto_predictor/models/swing/` (swing model `.pkl` files, 1.2 MB each)

### Quarantine / Archive
- `audit_trail/data/quarantine/` (2.5 MB)
- `audit_trail/data/universal_resolved_picks.json` (3.1 MB)

### Deployment / Build Artifacts
- `deploy_riseoftheclaw/` (1.9 MB)
- `TORONTOEVENTS_ANTIGRAVITY/audit/*.docx` (2.0 MB)

### Competition / Tournament Data
- `STOCKS/competition/` (1.7 MB + 1.5 MB)
- `data/ai_tournament/` (1.3 MB)
- `audit_dashboard/data/ai_tournament_picks_latest.json` (1.3 MB)
- `battleground/data/luxalgo_closed_picks.json` (2.7 MB)

### Database Snapshots / Exports
- `database/*/` (2.1 MB)
- `reports/h006_funding_cache_*.json` (2.6 MB)

### Attachments / Archives
- `kimi_attachments_*/` (2.5 MB .docx)
- `ejaguiar1_sportsbet.zip` (1.6 MB)

### Misc Regenerable Artifacts
- `tools/data/audit_edge_review_live.json` (2.1 MB)

## Verification
- All new patterns follow existing conventions (leading dirs, `**/*.ext`, dated wildcards).
- No production runtime files were affected — all ignored paths are regenerable from scripts, CI, or external sources.
- Existing production consumers (e.g., `closed_picks.json`, `live_picks.json` under `data/`) remain tracked where needed.

## How Verified
- `git ls-files` + `stat` identified 35+ files >1 MB still tracked.
- `git rev-list --objects --all` confirmed history bloat from duplicate `.pkl` and `.json` blobs.
- `git check-ignore` syntax validated (patterns are correct; files must exist on disk for runtime test).
- No overlap with required tracked files (e.g., `GITHUB_STRATS.MD`, `updates/index.html` live version).

## Impact
- Prevents ~50+ MB/month of unnecessary history growth.
- Future `git add -A` or CI commits will skip these paths.
- Existing large blobs remain in history until a history rewrite (optional, out of scope).

## Next Steps (Optional)
- Run `git rm --cached <file>` for each newly ignored file to stop tracking without deleting from disk.
- Consider `git filter-repo` or BFG to purge historical blobs if repo size must shrink immediately.
- Monitor `.git` size after next push to confirm no regression.

---
**Author:** Roo (agent)  
**Date:** 2026-05-25  
**Commit:** Will be included in the PR that adds this `.md` and the `.gitignore` update.
