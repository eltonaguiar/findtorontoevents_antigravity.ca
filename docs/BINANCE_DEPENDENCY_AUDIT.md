# Binance API Dependency Audit

**Date:** 2026-03-24
**Auditor:** Claude Code (automated)
**Scope:** All 231 GitHub Actions workflow files in `.github/workflows/`

## Summary

| Category | Count | Description |
|----------|-------|-------------|
| SAFE | ~215 | No Binance dependency, or non-crypto workflows |
| AT_RISK | 12 | Uses Binance with proper fallback chain (mirrors + CoinGecko/KuCoin/CryptoCompare) |
| BROKEN | 4 | Uses single Binance endpoint with NO fallback -- will fail on HTTP 451 |

---

## Shared Infrastructure

### `shared/binance_api.py` -- Failover Helper (GOOD)
- 6 spot endpoints (data-api.binance.vision prioritized in CI)
- 3 futures endpoints with circuit breaker (5min block on 451/429)
- Provides `binance_get()`, `binance_futures_get()`, `get_binance_price()`, `get_binance_klines()`
- **Only 1 file imports this module** (`shared/binance_api.py` itself). Most scripts implement their own fallback chains inline.

### `alpha_engine/config.py` -- Central Config (GOOD)
- Defines `BINANCE_SPOT_ENDPOINTS` with mirrors + data-api + binance.us
- Defines `COINGECKO_BASE`, `CRYPTOCOMPARE_BASE`
- CI-aware: reorders endpoints when `GITHUB_ACTIONS` is set

---

## BROKEN Workflows (Single Binance endpoint, NO fallback)

### 1. `genome-evolution.yml` -- Strategy Genome Evolution
- **Schedule:** Weekly Sunday 6AM UTC
- **Script:** Inline Python in workflow YAML (line 42-64)
- **Issue:** Hardcodes `https://api.binance.com/api/v3/klines` with no mirrors, no CoinGecko, no fallback
- **Impact:** Entire price data fetch fails on 451; genome evolution runs with no data
- **Fix needed:** Replace inline fetch with `shared/binance_api.get_binance_klines()` or add mirror loop

### 2. `live_trading.yml` -- Live Trading Bot
- **Schedule:** Every 4 hours
- **Script:** `live_trading_bot.py`
- **Issue:** `live_trading_bot.py` hardcodes `self.base_url = "https://fapi.binance.com"` and `self.spot_url = "https://api.binance.com"` (lines 81-82) with zero fallback endpoints
- **Impact:** All price fetching and order execution fails on 451
- **Fix needed:** Add endpoint failover list or use `shared/binance_api`

### 3. `real_2hour_challenge.yml` / `2hour_challenge.yml` -- 2-Hour Challenge
- **Schedule:** On-demand / scheduled
- **Script:** `real_2hour_challenge.py`
- **Issue:** `get_binance_data()` hardcodes `https://api.binance.com/api/v3/klines` and `https://fapi.binance.com/fapi/v1/fundingRate` (lines 27-50) with no mirrors
- **Impact:** Challenge data fetch fails entirely on 451
- **Fix needed:** Add mirror list or use `shared/binance_api`

### 4. `live_spike_trading.yml` -- Live Spike Trading
- **Schedule:** On-demand
- **Script:** `live_spike_trader.py`
- **Issue:** `get_binance_price()` and `get_binance_klines()` hardcode `https://api.binance.com` (lines 40, 59, 79) with no mirrors
- **Impact:** All spike detection and trading fails on 451
- **Fix needed:** Add endpoint failover

---

## AT_RISK Workflows (Uses Binance WITH fallback chain)

### 5. `alpha-engine-live.yml` -- Alpha Engine (CORE)
- **Schedule:** Every 30 min
- **Scripts:** `production_scanner.py`, `scanner.py`, `forward_validator.py`, `universal_price_enricher.py`, `pick_monitor.py`, `ml_predictor_merger.py`, etc.
- **Status:** GOOD -- `scanner.py` has full 4-tier fallback: Binance mirrors -> CoinGecko -> KuCoin -> CryptoCompare (lines 1091-1132). `universal_price_enricher.py` has mirror list + yfinance fallback. `pick_monitor.py` has mirror list.
- **Risk:** `forward_validator.py` line 2714 has a single `api.binance.com` call for klines (inside a try/except, non-fatal path), but the main validator doesn't depend on it.

### 6. `alpha-engine-fast.yml` -- Alpha Engine Fast
- **Script:** `production_scanner.py`
- **Status:** GOOD -- delegates to `scanner.py` which has full fallback chain

### 7. `deploy-riseoftheclaw.yml` -- KIMI Rise of the Claw
- **Schedule:** Every 15 min
- **Scripts:** `KIMI_RISEOFTHECLAW/live_scanner.py`, `signal_tracker.py`
- **Status:** GOOD -- `live_scanner.py` uses `multi_source_fetcher` with Binance mirrors + CoinGecko + CoinCap fallback (line 6459-6460). `signal_tracker.py` has 3-endpoint list (lines 34-36).

### 8. `claude-gainer-tracker.yml` -- Claude Gainer ML
- **Scripts:** `claude_gainer_ml/live_scanner.py`, `tp_sl_tracker.py`
- **Status:** GOOD -- `live_scanner.py` has Binance mirrors + data-api.binance.vision + binance.us (lines 87-89) plus CoinGecko fallback. `tp_sl_tracker.py` uses CoinGecko primary with Binance as fallback.

### 9. `cross-aggregator.yml` -- Cross Aggregator
- **Script:** `cross_aggregation/aggregator.py`
- **Status:** GOOD -- 5-endpoint Binance mirror list (lines 403-405) plus yfinance fallback for equities

### 10. `copy-trader-intelligence.yml` -- Copy Trader Intel
- **Scripts:** `copy_trader_intel/main.py`, `binance_scraper.py`, `technical_analyzer.py`
- **Status:** GOOD -- `binance_scraper.py` uses futures mirror chain (fapi1, fapi2) with documented failover (line 27). `technical_analyzer.py` has data-api.binance.vision + api1 mirrors (lines 12-14).

### 11. `copy-trader-forward-test.yml` / `copytrader-tracker.yml`
- **Script:** `alpha_engine/portfolio_tracker_copytrader.py`
- **Status:** GOOD -- 3-API fallback: Binance -> CoinGecko -> (graceful degrade) (lines 107-136)

### 12. `now-scanner.yml` -- NOW Scanner
- **Script:** `NOW.py`
- **Status:** GOOD -- `BINANCE_ENDPOINTS` list with mirrors + data-api.binance.vision + CoinGecko fallback + CoinCap fallback (lines 52-157)

### 13. `audit-dashboard.yml` -- Audit Dashboard
- **Scripts:** `audit_trail/dashboard_generator.py`, `copy_trader_intel/technical_analyzer.py`, `alpha_engine/audit_sync.py`
- **Status:** MOSTLY GOOD -- `dashboard_generator.py` has 3-endpoint Binance chain + CoinGecko fallback (lines 144, 255). One hardcoded call at line 4487 (`api.binance.com` for BTC chart) lacks fallback but is non-critical.

### 14. `genome-daily-pipeline.yml` -- DNA Genome Pipeline
- **Schedule:** Every 3 hours
- **Status:** GOOD -- Uses ccxt with Bybit as PRIMARY exchange, then binanceus, then binance as fallback (lines 54-63). Proper try/except per exchange.

### 15. `live-position-monitor.yml`
- **Script:** `live_monitor/position_monitor.py`
- **Status:** GOOD -- Uses binance.us as primary, api.binance.com as fallback (lines 29-30)

### 16. `dashboard-pick-trader.yml`
- **Script:** `alpha_engine/dashboard_pick_trader.py`
- **Status:** GOOD -- Full 4-tier fallback: Binance -> Binance mirror1 -> CoinGecko -> KuCoin (lines 57-87)

### 17. `mega-mutation-tracker.yml`
- **Script:** `genome/mega_mutation_live_tracker.py`
- **Status:** PARTIAL -- Has 3 Binance mirrors (line 241: api, api1, api2) but NO non-Binance fallback. A separate call at line 268 is single-endpoint. If all Binance mirrors 451, it fails.

---

## Workflows with NO Binance Dependency (SAFE)

The following workflow categories have no Binance API calls in their scripts:

- **Events/Toronto:** `scrape-events.yml`, `send-event-notifications.yml`, `taste-profile-scan.yml`
- **Movies:** `fetch-movies.yml`, `fetch-movies-v3.yml`, `deploy-movieshows-all.yml`
- **Deploy-only:** `deploy-pages.yml`, `deploy-fc-frontend.yml`, `deploy-battleground-ftp.yml`, `deploy-alpha-dashboard.yml`, `mirror-site.yml`, `torontoevent-deploy-*.yml`
- **Discord/Notifications:** `discord-heartbeat.yml`, `discord-status.yml`, `discord_status.yml`, `discord-bot.yml`
- **Stocks/Equity:** `daily-stock-refresh.yml`, `weekly-stock-simulation.yml`, `refresh-stocks-portfolio.yml` (use yfinance/FMP, not Binance)
- **ML/Battleground dashboards:** `ml-battleground-a/b/c/d/e/f.yml` (audit_push only, no price fetching)
- **Infrastructure:** `actions-failure-guardian.yml`, `db-backup-email.yml`, `db-sync-*.yml`
- **Pine Script:** `pine-generator.yml`
- **Sports/Deals:** `sports-betting-refresh.yml`, `deals-refresh.yml`
- **Content:** `update-creator-news.yml`, `refresh-creator-updates.yml`, `index-creator-content.yml`
- **Non-crypto ML:** `ml-health-monitor.yml`, `ml-discord-status.yml`
- And ~180 more that either don't call Python scripts with Binance imports, or use non-Binance data sources

---

## Risk Matrix: Scripts Needing Fixes

| Script | Used By Workflow | Current State | Fix Needed |
|--------|-----------------|---------------|------------|
| `live_trading_bot.py` | `live_trading.yml` | Single endpoint, no fallback | Add mirror list + CoinGecko |
| `real_2hour_challenge.py` | `real_2hour_challenge.yml`, `2hour_challenge.yml` | Single endpoint, no fallback | Add mirror list |
| `live_spike_trader.py` | `live_spike_trading.yml` | Single endpoint, no fallback | Add mirror list |
| Inline Python in `genome-evolution.yml` | `genome-evolution.yml` | Single endpoint, no fallback | Use `shared/binance_api` or add mirrors |
| `genome/mega_mutation_live_tracker.py` line 268 | `mega-mutation-tracker.yml` | Mirrors but no non-Binance fallback | Add CoinGecko fallback |
| `alpha_engine/forward_validator.py` line 2714 | `alpha-engine-live.yml` | Single endpoint in non-critical path | Add mirrors (low priority) |
| `audit_trail/dashboard_generator.py` line 4487 | `audit-dashboard.yml` | Single endpoint for BTC chart | Add mirrors (low priority) |

---

## Recommendations

1. **Immediate:** Fix the 4 BROKEN workflows listed above. Each needs a Binance mirror list at minimum, ideally CoinGecko/KuCoin as non-Binance fallbacks.

2. **Standardize:** The codebase has `shared/binance_api.py` but almost no scripts import it. Consider refactoring scripts to use this shared module instead of inline endpoint lists.

3. **CI Detection:** `shared/binance_api.py` already detects `GITHUB_ACTIONS` env and reorders endpoints. Scripts that roll their own lists should follow the same pattern (prioritize `data-api.binance.vision` and `api.binance.us` in CI).

4. **Non-Binance Fallback Rule:** Several scripts have Binance mirror chains but no escape hatch to CoinGecko/KuCoin/CryptoCompare. If all Binance endpoints return 451 (which happens on US-based runners), mirrors won't help. Always include at least one non-Binance source.
