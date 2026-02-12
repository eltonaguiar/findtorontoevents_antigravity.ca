# Conflict Check Report — OPUS46 Phase 0-3 Changes

**Date**: 2026-02-11
**Checked by**: Conflict Checker Agent

---

## SUMMARY

**Overall Status: CLEAN** — No critical blocking issues found. A few minor notes below.

### Files Checked: 16
### Critical Issues: 0
### Warnings: 2
### Notes: 5

---

## 1. scripts/run_all.py — 9 New Steps

**Status: PASS**

All 9 imported scripts have the correct entry points:

| Step | Import | Function | Exists? |
|------|--------|----------|---------|
| 20 | `commission_eliminator` | `main()` | YES (line 135) |
| 21 | `algorithm_pauser` | `main()` | YES (line 173) |
| 22 | `corr_pruner` | `main()` | YES (line 74) |
| 23 | `ensemble_stacker` | `main()` | YES (line 282) |
| 24 | `feature_selector` | `main()` | YES (line 245) |
| 25 | `stop_loss_analyzer` | `main()` | YES (line 137) |
| 26 | `dynamic_position_sizer` | `main()` | YES (line 171) |
| 27 | `momentum_crash_protector` | `MomentumCrashProtector` class + `protect_portfolio()` method | YES (line 13, 110) |
| 28 | `alpha_engine_deployer` | `main()` | YES (line 347) |
| 29 | `fred_macro` | `main()` | YES (line 405) |

**Note**: Step 27 (momentum_crash_protector) uses a different pattern — it imports the class and wraps it in a lambda. This is correct and consistent with the class-based design of that script.

**Note**: Step numbering skips from 27 to 29 (Step 28 is `alpha_engine_deployer` but labeled "Step 28" in the code while `fred_macro` is labeled "Step 29"). The step 28/29 labels in comments are swapped vs their order in code (fred_macro runs BEFORE alpha_engine_deployer). This is cosmetic only and does not affect execution.

The `--fred` flag is also properly included in the exclusion list for the consensus-only check (lines 108-109).

---

## 2. live-monitor/api/live_trade.php — PHP 5.2 Compatibility

**Status: PASS**

Checked all 1650 lines for PHP 5.2 incompatibilities:

- **No short array syntax `[]`**: All arrays use `array()` syntax. PASS
- **No `http_response_code()`**: All status codes use `header('HTTP/1.0 ...')`. PASS
- **No `$stmt->get_result()`**: No prepared statements used; all queries use `$conn->query()` + `real_escape_string()`. PASS
- **No spread operator `...$args`**: Not used. PASS
- **No `[]` array shorthand**: Not used. PASS

New functions added (Python position sizing bridge, drawdown scaling, signal cooldown, slippage estimation, Kelly auto-compute) all follow the same PHP 5.2 patterns as existing code.

---

## 3. Sports PHP Files — Include Paths & Schema Consistency

**Status: PASS**

### Include chain:
- `sports_odds.php` -> `require_once sports_db_connect.php` + `require_once sports_schema.php` + calls `_sb_ensure_schema($conn)` -> CORRECT
- `sports_picks.php` -> `require_once sports_db_connect.php` + `require_once sports_scores.php` + `require_once sports_schema.php` + calls `_sb_ensure_schema($conn)` -> CORRECT
- `sports_bets.php` -> `require_once sports_db_connect.php` + `require_once sports_scores.php` + `require_once sports_schema.php` + calls `_sb_ensure_schema($conn)` -> CORRECT

### `$THE_ODDS_API_KEY` availability:
- Defined in `db_config.php` (line 28)
- Included via `sports_db_connect.php` -> `require_once db_config.php`
- Available as global `$THE_ODDS_API_KEY` in all 3 sports files. PASS

### Schema centralization:
- All 7 CREATE TABLE statements are now ONLY in `sports_schema.php`. CONFIRMED.
- `sports_odds.php`: 0 CREATE TABLE statements. CLEAN.
- `sports_picks.php`: 0 CREATE TABLE statements. CLEAN.
- `sports_bets.php`: 0 CREATE TABLE statements. CLEAN.

### No duplicate table creation:
- `lm_sports_odds`: Only in `sports_schema.php`. PASS
- `lm_sports_bets`: Only in `sports_schema.php`. PASS
- `lm_sports_credit_usage`: Only in `sports_schema.php`. PASS
- `lm_sports_clv`: Only in `sports_schema.php`. PASS
- `lm_sports_value_bets`: Only in `sports_schema.php`. PASS
- `lm_sports_daily_picks`: Only in `sports_schema.php`. PASS
- `lm_sports_bankroll`: Only in `sports_schema.php`. PASS
- `lm_trades`: Only in `live_trade.php`. PASS
- `lm_snapshots`: Only in `live_trade.php`. PASS

---

## 4. sports_schema.php — New File Validation

**Status: PASS**

- PHP 5.2 compatible: uses `array()` syntax only. PASS
- Uses `function _sb_ensure_schema($conn)` pattern. PASS
- All 7 tables use `ENGINE=MyISAM DEFAULT CHARSET=utf8`. PASS
- All column types are MySQL 5.x compatible. PASS
- All tables have appropriate indexes. PASS

---

## 5. GitHub Actions Workflows

### worldclass-intelligence.yml

**Status: PASS**

- Valid YAML structure. PASS
- All Python scripts use `working-directory: scripts` or `scripts/worldclass`. PASS
- All steps have `continue-on-error: true`. PASS
- New FRED Macro step (in worldclass-pipeline.yml, intelligence job) properly sets `FRED_API_KEY: ${{ secrets.FRED_API_KEY }}`. PASS
- Step numbering is consistent (10a through 10h for Sprint 1+2 scripts). PASS

### worldclass-pipeline.yml

**Status: PASS with NOTE**

- Valid YAML structure. PASS
- New `intelligence` job properly declares dependencies: `needs: [regime, bundles]`. PASS
- `summary` job properly includes `intelligence` in its `needs`. PASS
- FRED Macro step has correct env var: `FRED_API_KEY: ${{ secrets.FRED_API_KEY }}`. PASS

**WARNING**: The `FRED_API_KEY` secret must be added to the GitHub repository settings for the FRED macro script to work. Without it, the script will log "FRED_API_KEY not set" and return `None` (graceful degradation, not a crash). This is a setup requirement, not a code bug.

---

## 6. New Python Scripts

### scripts/data_fetcher.py

**Status: PASS**

- Imports: `pandas`, `numpy`, `os`, `sys`, `logging`, `time`, `datetime` — all standard or pip-installable. PASS
- Has `main()` function. PASS
- Handles yfinance MultiIndex columns (line 73-74) — follows the gotcha pattern. PASS
- Uses custom User-Agent header (`WorldClassIntelligence/1.0`) — follows the ModSecurity gotcha. PASS

### scripts/fred_macro.py

**Status: PASS**

- Imports `from utils import post_to_api, API_HEADERS` — `utils.py` exists and has `post_to_api` (line 58). PASS
- Imports `from config import API_BASE, ADMIN_KEY` — `config.py` exists and defines both (lines 8-9). PASS
- Has `main()` function. PASS
- Uses `API_HEADERS` from utils for all requests — follows the ModSecurity User-Agent pattern. PASS
- Requires `FRED_API_KEY` env var — gracefully handles missing key (returns `None`). PASS

---

## 7. investments/goldmines/antigravity/api/create_views.php — PHP 5.2 Compatibility

**Status: PASS**

- Uses `array()` syntax throughout. PASS
- No `http_response_code()` — uses direct `echo json_encode()` + `exit`. PASS
- No short array syntax `[]`. PASS
- MySQL 5.x compatible: No CTEs, no window functions, no `CREATE OR REPLACE VIEW`. Uses `DROP VIEW IF EXISTS` + `CREATE VIEW`. PASS
- Creates its own `$conn` using `new mysqli(...)` — standalone, does not conflict with other DB connections. PASS

---

## 8. live-monitor/api/live_monitor_schema.php — New File Validation

**Status: PASS**

- PHP 5.2 compatible. PASS
- Uses `CREATE TABLE IF NOT EXISTS` — will not overwrite existing `lm_market_regime` table. PASS
- Properly includes `db_connect.php`. PASS
- Self-detection for direct execution works correctly. PASS

---

## 9. predictions/sports.html — API URLs

**Status: PASS**

All 3 API calls use correct relative paths:
- `API_BASE + '/sports_bets.php?action=dashboard'` -> `/live-monitor/api/sports_bets.php?action=dashboard` CORRECT
- `API_BASE + '/sports_picks.php?action=today'` -> `/live-monitor/api/sports_picks.php?action=today` CORRECT
- `API_BASE + '/sports_picks.php?action=performance'` -> `/live-monitor/api/sports_picks.php?action=performance` CORRECT

`API_BASE` is set to `'/live-monitor/api'` (line 175). This is the correct production path.

---

## 10. tools/deploy_opus46_changes.py — Deploy Script

**Status: PASS**

- Uses `FTP_TLS()` + `prot_p()` — follows the FTP gotcha. PASS
- Uses `BASE_REMOTE = '/findtorontoevents.ca'` — correct FTP root path. PASS
- All deployed files are under `live-monitor/` at ROOT, not under `fc/` — follows the FTP deploy path gotcha. PASS
- Optional files section properly checks `os.path.exists()` before adding to deploy list. PASS

**NOTE**: The deploy script does NOT include `sports_schema.php` in the main `FILES` list — it's in `OPTIONAL_FILES` (line 67). This is fine since the file will be deployed if it exists locally.

---

## WARNINGS SUMMARY

### WARNING 1: FRED_API_KEY Secret Required
- **File**: `.github/workflows/worldclass-pipeline.yml` (line 200)
- **Impact**: FRED macro script will skip all FRED data fetching without this secret
- **Fix**: Add `FRED_API_KEY` to GitHub repository secrets
- **Severity**: LOW (graceful degradation)

### WARNING 2: Step Number Label Swap in run_all.py
- **File**: `scripts/run_all.py` (lines 243-253)
- **Impact**: Comment says "Step 29" for FRED but "Step 28" for deployer. FRED runs before deployer in code, but deployer comment says Step 28. Labels are cosmetic.
- **Fix**: Swap step number comments to match execution order
- **Severity**: COSMETIC ONLY

---

## NOTES

1. **All PHP files are PHP 5.2 compatible** — no modern PHP syntax used anywhere.
2. **No duplicate table creation** — schema is properly centralized in sports_schema.php for sports tables, and live_trade.php for trading tables.
3. **All Python script imports resolve** — every script imported by run_all.py exists and exposes the expected function/class.
4. **All API URLs in frontend files are correct** — using production paths.
5. **Deploy script covers all new files** — both required and optional.

---

*Conflict check complete. No blocking issues found.*
