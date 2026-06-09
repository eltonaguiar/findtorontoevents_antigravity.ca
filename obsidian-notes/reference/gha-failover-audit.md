---
tags: [reference, ci, failover, gha, api]
created: 2026-06-06
status: active
---

# GitHub Actions Failover Audit — 2026-06-06

## TL;DR

**Gap found:** 10+ production workflows rely on yfinance with **no failover env vars set**. When yfinance 401s on GHA (known pattern), they silently produce zero picks. The failover modules exist (`equity_price_failover.py`, `api_failover.py`) but have no API keys to use.

**Fixed today:** picks-now-refresh.yml, alpha-engine-live.yml, walk-forward-backtest.yml

**Still gap:** dynamic-alpha-engine.yml, alpha-engine-daily-picks.yml, alpha-trend-catcher.yml, crypto-smart-picks.yml, algorithm-competition-refresh.yml, forward-test-new-strategies.yml

---

## Workflow Health Overview

| Workflow | Status | Failover | Notes |
|----------|--------|----------|-------|
| picks-now-refresh.yml | ❌ ALL 5 runs failed | ✅ Fixed | yfinance timeout on GHA; added failover env vars |
| alpha-engine-live.yml | ✅ Passing | ✅ Fixed | Added job-level failover env vars |
| ueps-pick-runner.yml | ✅ Passing | ✅ Already wired | Model example — has failover commentary |
| alpha-engine-etf.yml | ✅ Passing | ⚠️ yfinance only | ETF-only, but no failover for price data |
| walk-forward-backtest.yml | ✅ Passing (weekly) | ✅ Fixed | Forex step was bare yfinance; added failover keys |
| battle_test.yml | ✅ Passing | ⚠️ Partial | Has CRYPTOCOMPARE + COINGECKO keys but no equity |
| audit-dashboard.yml | 🔄 Running | ⚠️ None | Dashboard generator doesn't fetch prices directly |
| Dynamic Alpha Engine | ✅ Passing | ❌ **Gap** | No failover env vars |
| Alpha Engine Daily Picks | ✅ Passing | ❌ **Gap** | No failover env vars |
| Alpha Engine Trend Catcher | ? | ❌ **Gap** | Has backtest mode but no failover vars |
| Crypto Smart Picks | ? | ❌ **Gap** | No failover env vars |
| Forward Test New Strategies | ✅ Passing | ❌ **Gap** | No failover vars |
| Copy Trader Intelligence | ✅ Passing | ✅ Implicit | Uses its own scraper chain |
| Prediction Market Agents | ✅ Passing | ✅ Implicit | Uses own PM data sources |

---

## picks-now-refresh.yml — Root Cause of Failures

**Symptom:** All 5 recent runs failed (runs #1–#5, June 6).

**Root cause:** The workflow only set `DB_PASS_STOCKS` and `FMP_API_KEY` env vars. When yfinance rate-limited on GHA (HTTP 429 / silent 401), the new failover code in `fetch_ohlcv_failover()` and `fetch_analyst_info_failover()` could fall back to FMP for OHLCV history but had no `FINNHUB_API_KEY`, `TIINGO_API_KEY`, etc. to try the proper equity failover chain.

**Fix applied:** Added 6 failover API keys to the `Generate picks` step env.

**Also needed:** Install `scipy` (dependency for pandas rolling operations used by scorer).

---

## Key Module: `alpha_engine/equity_price_failover.py`

This is the reference implementation for equity failover. Its chain:
```
Quote:  Stooq → Finnhub → Tiingo → Twelve Data → Alpha Vantage → FMP → yfinance
Market cap: Finnhub → FMP → Polygon.io → SEC EDGAR → yfinance
```
But it **only works on GHA if the env vars are set**. Adding them at the job level (as done in alpha-engine-live.yml) ensures every step benefits.

## Key Module: `alpha_engine/api_failover.py`

Crypto failover:
```
Spot: Binance 6-mirror → CoinGecko → KuCoin → CryptoCompare
Futures: Binance FAPI → KuCoin futures
```
Needs `CRYPTOCOMPARE_API_KEY` and `COINGECKO_API_KEY` for best reliability.

---

## Verified: Available GitHub Secrets

Only these data-source API keys exist as secrets:
- `FMP_API_KEY` — Financial Modeling Prep (250/day)
- `FRED_API_KEY` — St. Louis Fed (unlimited free)
- `CRYPTOCOMPARE_API_KEY` — CryptoCompare (set only in battle_test.yml)
- `COINGECKO_API_KEY` — CoinGecko (only in battle_test.yml env)

**Missing (not set as GitHub Secrets):** FINNHUB_API_KEY, TIINGO_API_KEY, TWELVE_DATA_API_KEY, ALPHA_VANTAGE_API_KEY, POLYGON_API_KEY, EXCHANGERATE_API_KEY

Without these keys, the failover chain falls through to the anon-accessible sources (Stooq, Binance mirrors, CoinGecko, FRED CSV) and ultimately to yfinance. The failover code handles missing keys gracefully (skips that source), so adding `${{ secrets.X }}` for non-existent secrets is safe — but they resolve to empty string.

**To get the full failover benefit:** Register at finnhub.io, tiingo.com, twelvedata.com (all free tier) and add the API keys as GitHub secrets. The current fix ensures the failover module is at least wired and ready to use the keys the moment they're added.

### Standard env snippet (copy-paste for any new workflow)
```yaml
    env:
      FMP_API_KEY: ${{ secrets.FMP_API_KEY }}
      FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
      CRYPTOCOMPARE_API_KEY: ${{ secrets.CRYPTOCOMPARE_API_KEY }}
```

---

## How to Verify

```bash
# Check picks-now workflow runs
gh run list --workflow "Picks NOW Refresh" --branch main --limit 5

# Check workflow logs for yfinance-related errors
gh run view <run_id> --log | grep -iE "yfinance|401|429|timeout|failover"

# After fix: check if failover module is being hit
gh run view <run_id> --log | grep -i "api_failover\|failover\|equity_price"
```

---

## Related

- [[reference/data-sources]]
- [[reference/data-quality-checklist]]
- [[asset-classes/EQUITY]]
