# Infra Fragility Audit — GitHub Actions, Deps, Failover, Stale Data (2026-05-18)

Two-agent read-only audit. Companion to `reports/MASTER_ENHANCEMENT_PLAN_2026_05_18.md`.

## A. Broken / chronically-dead workflows

| Workflow | State | Diagnosis |
|----------|-------|-----------|
| `penny-stock-picks.yml` | **failing 21 days** | `fatal: could not read Username for github.com` at checkout — missing/expired token. |
| `dxy-state-update.yml` | **never run once** | cron defined, 0 executions — `dxy_state.json` staling, degrades M-074 COMMODITY booster. |
| `ci-tests.yml` | ~18/19 `cancelled` | concurrency cascade in the push-storm repo. Passes when it completes; CI not a reliable gate. |
| `sports-betting-refresh` | `custom-sports-update` leg cancelled 5× at Checkout | Goal #2 sports leg silently not refreshing. |
| `equities/etf/commodities/bond-agent` | green but **0 quality picks** | yfinance empty/"delisted" → scanners fail-open → exit `success`. **Status UI lies.** |

Also: `outcome-resolver` logged a `YM=F` PnL of **+18,926,991%** — futures unit/price-scale bug in the bar-replay resolver.

## B. The #1 systemic fragility — yfinance monoculture

- **~147 of 150** `yf.download`/`yf.Ticker` callers hit Yahoo with **no provider failover**.
- Failover infra **exists** — `alpha_engine/ohlcv_failover.py`, `equity_price_failover.py`, `api_failover.py`, `crypto_data_failover.py` — but **only `etf_scanner.py` + `bond_scanner.py` use it**. Classic "module built, no callers" (Wire-Up Rule gap). Direct CLAUDE.md API-Failover-Rule violation.
- The 2026-05-15 bond/commodities/forex agent failures are the symptom.

**Top-priority fix (documented, not yet applied):** route the two broadest production pick paths through the existing failover, using the `failover_available()`-gated pattern already proven in `etf_scanner.py:194-219`:
- `alpha_engine/scanner.py:1291,1301` (`download_with_retries`) → `ohlcv_failover.fetch_ohlcv_failover`
- `alpha_engine/forex_smart_picks.py:333` (`download_forex_data`) → `ohlcv_failover`
- (then `production_scanner.py:2099,2115`, `forward_validator.py`, ~140 more.)

Needs a focused, tested PR — editing production pick-generation code; not a blind tail-of-session edit.

## C. Other fragile deps

| Package | Risk | Note |
|---------|------|------|
| `fredapi` / `pandas-datareader` | Medium | single-host (FRED / Stooq), no FRED failover module exists — gap. |
| `ccxt` | Low-Med | 4 files, not on a critical scheduled path. |
| `finnhub` | Low | used correctly as a failover leg in `equity_price_failover.py`. |
| `sportsdataverse/nflreadpy/nba_api` | Medium | degrade gracefully (exit 0 on ImportError). |
| alpha_vantage / pycoingecko / web3 / tweepy / praw / newsapi | n/a | **0 importers — unused.** |

## D. Stale data

Core hourly artifacts all fresh (`dashboard_data.json`, `pf_registry.json`, `forex_futures_picks.json` < 1h; `dxy_state.json` 1h). Stale (secondary): `copytrade_pm_*.json` (35 days — copy-trader pipeline not refreshing), `claudes_test_*.json` / `ag_top_picks*.json` / `claude_top_picks_round*.json` (44-51 days — frozen round artifacts, likely intentional).

## Verdict — top 3 fixes

1. **Wire the failover modules** into `scanner.py` + `forex_smart_picks.py` (then the rest). Converts ~147 silent yfinance failures into graceful provider failover.
2. **Fix the fail-open masking** — asset agents must fail/alert on 0 raw picks or high yfinance error-rate, not exit green.
3. **Fix `penny-stock-picks.yml` checkout token** + **`dxy-state-update.yml` cron** (never run) + the `YM=F` 19M% resolver unit bug.
