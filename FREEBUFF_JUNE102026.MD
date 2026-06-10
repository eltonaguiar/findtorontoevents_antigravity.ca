# FREEBUFF Handoff — June 10, 2026

## Session Summary

### 1. Tournament Portfolio Bloodbath Fix (PR #560 — MERGED to main)

**Root Cause:** 843 losing positions vs 7 winning (0.82% WR) across 123 paper portfolios. Total realized PnL: **-$352,378**. The aggressive risk appetite used **trail-only TP** — positions had no fixed take-profit target, only a stop-loss. 824 exits via stop-loss, 7 via take-profit.

**Fixes committed + merged to main (bc05899):**
- `tools/portfolios/run_daily.py` — `model_picks()`: reject picks with `MISPRICED_ENTRY`, `SYNTHETIC_SEED_ENRICHED`, `BACKTEST_DISPUTED`, `HALLUCINATION` flags
- `tools/portfolios/run_daily.py` — `seed_portfolios()`: raised edge bar to pf_ci_lo > 1.10 (was > 1.0), requires n_resolved >= 30 AND n_wins > 0, removed dead `edge_eligible_models()`
- `tools/portfolios/run_daily.py` — `edge_signal_for()`: recalibrated to 1.10 bar, 50% haircut on WR-only fallback
- `config/portfolio_risk_profiles.json` — aggressive: added fixed 30% TP (was trail-only), max positions cut (12→6, 20→10, 30→15), drawdown breakers tightened
- PR: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/560

### 2. Portfolio Pipeline Re-Run

Ran `tools/portfolios/run_daily.py --apply` from worktree with new gates:
- 35 entries opened
- 1,722 picks rejected by new data-quality gates
- `export_json.py --write` exported updated pf_portfolios.json

### 3. Picks-Now Live PnL Tracking System

**New file: `tools/live_pnl_tracker.py`**
- Fetches current prices via yfinance (equities/ETFs/commodities/forex) and Binance (crypto)
- Computes mark-to-market PnL: `(current - entry) / entry * 100`, flips sign for SHORT
- Writes to picks_now_tracker DB columns (`current_price`, `current_pnl_pct`)
- Exports `audit_dashboard/data/picks_now_live_pnl.json`
- Rate-limits yfinance (sleep 0.3s every 20 calls)
- Idempotent ALTER TABLE for column addition
- Current state: **479 open picks, avg +0.41%, 279/180 positive/negative split**

### 4. Live PnL Dashboard Section

Added to `audit_dashboard/picks-now.html`:
- "LIVE MARK-TO-MARKET PNL" section between Forward-Tested Performance and Multi-Model Review panels
- Summary stats: open picks count, avg unrealized PnL, positive/negative split, priced count
- Per-class breakdown table (EQUITY 446 picks +0.38%, ETF 26 picks +0.52%, etc.)
- Top 10 gainers + top 10 losers side-by-side tables
- Fetches from `picks_now_live_pnl.json`
- Deployed to production: https://findtorontoevents.ca/audit/picks-now.html

### 5. Hourly Cron Workflow

**New file: `.github/workflows/picks-now-live-pnl.yml`**
- Cron: `48 * * * *` (hourly at :48 UTC — free slot, avoids mega-cluster)
- Steps:
  1. `live_pnl_tracker.py --apply` (refresh current prices → DB + JSON)
  2. `resolve_picks_now.py --apply` (resolve matured picks, non-fatal)
  3. `build_picks_now_track_record.py --apply` (rebuild track record, non-fatal)
  4. Commit + push `picks_now_live_pnl.json` + `picks_now_track_record.json`
  5. FTP deploy all 3 JSONs to production
- Concurrency group prevents overlapping runs
- `continue-on-error` on push (standard repo pattern)

### 6. FTP Deploy Updates

**Modified `tools/ftp_deploy_picks_now.py`:**
- Added `picks_now_live_pnl.json` and `picks_now_track_record.json` to upload list

**Modified `tools/deploy_to_ftp.py`:**
- Added `picks-now.html`, `pf.html`, `model.html`, `pick_funnel.html`, `trading_blueprint.html`, `strategy_audit_summary.html`, `claudes_test.html` to audit dashboard HTML deploy list
- Added `picks_now.json`, `picks_now_live_pnl.json`, `picks_now_track_record.json` to data files deploy list

### 7. Git State

All changes on branch: **`intrabar-resolve-signal-outcomes-2026-06-09`**
Pushed to origin, ready for PR to main.

Commits on this branch (newest first):
1. `feat(ci): hourly picks-now live PnL tracker workflow`
2. `feat(deploy): add picks-now.html and picks_now_* JSONs to audit deploy list`
3. `feat(picks-now): live mark-to-market PnL tracking + dashboard panel`

### Files Created
- `tools/live_pnl_tracker.py` — mark-to-market PnL for picks_now_tracker
- `audit_dashboard/data/picks_now_live_pnl.json` — output JSON (157KB)
- `.github/workflows/picks-now-live-pnl.yml` — hourly cron workflow

### Files Modified
- `audit_dashboard/picks-now.html` — added Live PnL section
- `tools/deploy_to_ftp.py` — added new files to deploy lists
- `tools/ftp_deploy_picks_now.py` — added new JSONs to upload list
- `tools/portfolios/run_daily.py` — data-quality gates, raised edge bar (PR #560)
- `config/portfolio_risk_profiles.json` — fixed 30% TP for aggressive (PR #560)

### Remaining Action Items

| Item | Status |
|------|--------|
| Create PR from intrabar-resolve-signal-outcomes-2026-06-09 to main | **PENDING** — operator-gated |
| Add resolve pre-check to hourly workflow (skip if no picks > 10d old) | **PENDING** — nice-to-have optimization |
| Verify hourly cron runs successfully on first scheduled trigger | **TIME-GATED** — wait for :48 UTC |
| Wire live_pnl_tracker.py into GitHub Actions masking_manifest.yaml | **PENDING** — low priority |
