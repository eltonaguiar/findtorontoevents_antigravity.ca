# GHA Deep Scan Audit — 2026-04-16 (Last 4 Hours)

**Scan window:** ~17:15 UTC – 18:55 UTC on 2026-04-16  
**Runs scanned:** ~100 workflow runs across 279 defined workflows  
**Method:** `gh run list` + `gh run view --log` for each relevant run; grep for error/warning/failure patterns in full logs

---

## Executive Summary

| Severity | Count | Description |
|----------|-------|-------------|
| 🔴 **FAILED** | 1 | Unified Audit Dashboard — ML optimizer crash + git push lock-out |
| 🟠 **CANCELLED** | 4 | Git lock races / ref conflicts killed 4 runs |
| 🟡 **SUCCESS w/ hidden errors** | 11 | Runs that reported green but logged significant data loss, price fetch failures, or model errors |
| 🔵 **Systemic infra** | 2 | Git submodule error + Node.js 20 deprecation affect nearly ALL runs |

---

## 🔴 FAILED Runs

### 1. Unified Audit Dashboard (Run 24524216893) — CREATED 17:23:22Z

**Failed job:** `generate-and-deploy`  
**Failed step:** `Commit updated data`

| Issue | Detail |
|-------|--------|
| **ML Optimizer ValueError** | `ValueError: y contains 1 class after sample_weight trimmed classes with zero weights, while a minimum of 2 classes are required.` in `tools/hyro_ml_pick_optimizer.py` — sklearn `FitFailedWarning` triggered |
| **Git push lock-out** | `ERROR: All push attempts failed — another workflow likely has the lock`. Prior logs show `error: unknown switch 'm'` and `fatal: There is no merge to abort (MERGE_HEAD missing)` |
| **Binance HTTP 451** | Persistent 451 errors across all 4 Binance API endpoints during resolve/prediction steps |
| **Hyro pipeline exit 1** | Final step detected sub-process non-success: `Hyro sub-step(s) non-success: ml_optimizer — /audit Hyro JSON or ML rankings may be stale` |
| **Verify URLs** | GitHub Pages URL returned 404 (other URLs 200) |

**Prior occurrence:** Run 24523921778 (17:16:28Z) — **cancelled** (no error lines found in logs; likely cancelled by the failed run's retry)

**Impact:** Audit dashboard may have stale ML rankings and missed a deployment cycle.

---

## 🟠 CANCELLED Runs

### 2. Consensus Outcome Tracker (Run 24527045714) — CREATED 18:27:35Z

**Root cause:** Git push/pull infinite loop during `Commit outcome updates` step. The script repeatedly tried `git pull --rebase --no-recurse-submodules -X theirs origin main` then push, but never succeeded. Runner eventually cancelled the job.

**Impact:** Consensus outcome tracking did not commit its results — picks may not have been resolved this cycle.

### 3. Quick Guess ML Agent (Run 24527537305) — CREATED 18:38:41Z

**Root cause:** The `Commit results` step was cancelled. All prior steps (scan, analysis) completed successfully. Appears to be a victim of the same git lock contention.

**Impact:** Quick-guess scan results were not committed; data from this cycle is lost.

### 4. Copy Trader Forward Test (Run 24525271039) — CREATED 17:47:32Z

**Root cause:** 
1. **Widespread price fetch failures** during `Resolve Copy Trader Outcomes` — `Could not fetch price for [SYMBOL]USDT` for BTC, ETH, BNB, ONDO, NEAR, LINK, SUI, AVAX, HYPE, RENDER, ADA, SOL, XRP, DOGE, ENA, PENGU, METIS
2. **Git push cancelled** during `Commit and push changes`

**Impact:** Copy trader outcomes could not be resolved due to price data unavailability. Multiple TIME_EXPIRED exits recorded.

### 5. Low-Score Winner Tracker (Run 24524869258) — CREATED 17:38:20Z

**Root cause:** Git conflict — `error: cannot pull with rebase: You have unstaged changes` / `Please commit or stash them`. Multiple push attempts failed, job was cancelled.

**Impact:** Low-score winner tracking data not committed for this cycle.

---

## 🟡 Successful Runs with Hidden Errors

### 6. QUAN ENGINE Live Autonomous Scanner (Run 24527429546)

| Issue | Detail |
|-------|--------|
| **MATIC-USD delisted** | yfinance: "possibly delisted; no price data found" — repeated across all 3 failover attempts |
| **audit_trail import error** | `No module named 'audit_trail'` — audit push was skipped entirely |
| **Strategy import failure** | `corr_hma_trend` strategy failed to import, defaulted to ABSTAIN |
| **HTTP 451 / 400** | Binance 451 (geo-block); KASUSDT HTTP 400 "insufficient data" |
| **Invalid value in divide** | `RuntimeWarning: invalid value encountered in divide` in `prop_strategies.py` |
| **Audit DB missing** | `fatal: pathspec 'data/audit_trail.db' did not match any files` |

**Impact:** 4 signals generated, 88 picks swept — but audit trail for this run was not recorded due to missing module.

### 7. Enhanced ML Crypto Train & Predict (Run 24527730704)

| Issue | Detail |
|-------|--------|
| **Feature dimension mismatch** | `[ERROR] <Asset>/D_ensemble_stack: X has 65 features, but StandardScaler is expecting 155 features as input.` — affects BTC, ETH, BNB, SOL, XRP, TRX, ADA, AVAX, TAO |
| **Bybit 403 Forbidden** | Open Interest fetch blocked for HOTUSDT, SAHARAUSDT, ANKRUSDT |
| **Binance 451** | Funding rates & long/short ratio blocked for same symbols |
| **yfinance missing** | `[external] SPX/VIX fetch failed: No module named 'yfinance'` |
| **Coinbase premium failure** | `[external] Coinbase premium failed: 'price'` — KeyError on price key |
| **Kraken circuit breaker** | `kraken circuit breaker tripped after 3 failures` |
| **Model not found** | Multiple "Model not found" errors for ANKRUSDT, HOTUSDT, SAHARAUSDT across XGBoost, LightGBM, RF, Ensemble |

**Impact:** 50 picks generated, 31 exported — but ensemble stack models are using wrong feature dimensions (65 vs 155), meaning predictions may be unreliable for top assets.

### 8. Multi-Asset Copytrader Scanner v2 (Run 24527319847 — latest; 24524746296 — prior)

| Issue | Detail |
|-------|--------|
| **FDAX=F delisted** | `Yahoo error = "No data found, symbol may be delisted"` + HTTP 404 (prior run) |
| **Binance Futures disabled** | `BINANCE_FUTURES_DISABLED=True` — intentional but limits coverage |
| **XGBoost / LightGBM missing** | Falls back to RandomForest (both runs) |
| **External data unavailable** | COT Positioning, IG/DailyFX Sentiment, CFTC Socrata API, Myfxbook, TradingView Ideas — ALL unavailable, falling back to RSI/seasonal heuristics |
| **Quality flag: CL=F** | TP distance 19.4% > max 15%; SL distance 14.5% > max 10% (both runs) |
| **Quality flag: CT=F** | Confidence 0.12 < minimum 0.50 (both runs) |
| **Quality flag: NQ=F** | Confidence 0.10 < minimum 0.50 (prior run only) |

**Impact:** Non-crypto data feeds (COT, CFTC, Myfxbook, TradingView) are consistently unavailable. Scanner operates on degraded heuristics. Flagged picks with low confidence or excessive TP/SL distances are still entering the pipeline.

### 9. Market Beating System (Run 24527199994)

| Issue | Detail |
|-------|--------|
| **NumPy runtime warnings** | `Mean of empty slice` + `invalid value encountered in scalar divide` |
| **Forex assets disabled** | DOGE-USD (0% accuracy), GBP-USD (22.2%), EUR-USD (42.9%), USD-CHF (50%) — all auto-disabled for low accuracy |

**Impact:** Forex coverage shrinking — 4 pairs disabled. System only tracking crypto accurately.

### 10. Top Gainers Spike Scanner (Run 24527432809)

| Issue | Detail |
|-------|--------|
| **31 failed symbol downloads** | $DGLY, $MULN, $XSPA, and 28 others — "possibly delisted" / HTTP 404 |
| **yfinance data gaps** | No price data found for multiple stock symbols |

**Impact:** ~31 stock symbols have no price data — any active picks on these symbols cannot be resolved.

### 11. Rapid Fire NOW Scanner (Run 24527655948)

| Issue | Detail |
|-------|--------|
| **UnicodeEncodeError** | `'ascii' codec can't encode characters` for tokens with non-ASCII names (e.g., 币安人生USDT) |
| **CoinGecko 429 rate limiting** | HTTP 429 for AAVE, Polkadot, NEAR, Litecoin, Filecoin, etc. |
| **CoinCap DNS failures** | `[Errno -2] Name or service not known` — service unreachable |
| **ALL SOURCES FAILED** | `WARNING: No prices available from any source` for some assets |

**Impact:** Price discovery is failing across all 3 fallback sources for some assets. Non-ASCII token names crash the encoder.

### 12. Claude Gainer ML Live Scanner (Run 24527626441)

| Issue | Detail |
|-------|--------|
| **data_fetcher.py missing** | `[WARN] data_fetcher.py not found — using legacy CoinGecko mode` |
| **5 circuit breakers tripped** | okx, coingecko, kraken, cryptocompare, yfinance — all tripped after 3 failures each |
| **3 coins failed** | USYCUSDT, EARNETHUSDT, USDAUSDT — no klines, no sparkline, no data from any source |
| **Git rebase failure** | `error: could not apply 216b231... Claude Gainer ML scan 2026-04-16 18:47 UTC [skip ci]` |

**Impact:** All 5 major price sources hit circuit breakers simultaneously — severe data drought. 3 coins have zero data.

### 13. Outcome Resolver (Run 24527582125)

| Issue | Detail |
|-------|--------|
| **BGBUSDT price fetch** | `[WARNING] fetch_price(BGBUSDT): ALL sources failed` |
| **GTUSDT price fetch** | `[WARNING] fetch_price(GTUSDT): ALL sources failed` |

**Impact:** BGB and GT tokens cannot be resolved — active picks on these may never exit.

### 14. Audit Drift Telemetry (Run 24527552041)

| Issue | Detail |
|-------|--------|
| **Integrity check failed** | `WARN integrity check failed for 30/50 rows; looking for fallback snapshot` (60% failure rate) |
| **Probation threshold exceeded** | `asset_class_policy [CRYPTO]` exceeded probation with drift score ~70.43 |
| **Low coverage** | Backtest coverage: 20/200 (10%) |

**Impact:** 60% of backtest rows failed integrity validation. CRYPTO asset class policy is drifting significantly.

### 15. Signal Quality Monitor (Run 24527633915)

| Issue | Detail |
|-------|--------|
| **No quality reports** | `##[warning]No files were found with the provided path: reports/quality/` — artifacts not generated |
| **Forward tracking DB missing** | `No forward tracking database found` |
| **Model AUC below threshold** | `WARNING: Model AUC {auc:.3f} below threshold (0.6)` |

**Impact:** Signal quality monitoring is not producing reports. Forward tracking is not operational.

### 16. Run Backtests & Deploy Dashboards (Run 24526988058)

| Issue | Detail |
|-------|--------|
| **MATIC-USD / NKLA / RNDR-USD / SQ delisted** | yfinance: "No data found, symbol may be delisted" |
| **3 circuit breakers tripped** | kucoin, okx, coincap — all skipped for rest of scan |
| **transaction_costs module missing** | `No module named 'transaction_costs'` — using defaults |
| **Scout function argument mismatches** | `signal_vwap_deviation_scalp() takes 2 positional arguments but 3 were given` — multiple scouts crashing (vwap-deviation-scalp, ema-ribbon-momentum, bb-squeeze-breakout) |
| **External data unavailable** | Reddit WSB, News sentiment — both unavailable |

**Impact:** Scout functions are crashing due to argument mismatches — signals from these scouts are being silently dropped. Transaction cost modeling uses defaults.

---

## 🔵 Systemic Infrastructure Issues

### 17. Git Submodule `.pr41-review` Error (ALL RUNS)

```
fatal: No url found for submodule path '.pr41-review' in .gitmodules
##[warning]The process '/usr/bin/git' failed with exit code 128
```

**Present in:** Nearly every single workflow run during the Post Checkout cleanup phase.  
**Impact:** Non-blocking (cleanup only), but creates noise in logs and may mask real git errors.

### 18. Node.js 20 Actions Deprecation (ALL RUNS)

```
##[warning]Node.js 20 actions are deprecated. Actions will be forced to run on Node.js 24 by June 2nd, 2026.
```

**Affected actions:** `actions/checkout@v4`, `actions/setup-python@v5`, `actions/upload-artifact@v4`  
**Impact:** Will break all workflows on June 2, 2026 if not updated.

---

## Pattern Analysis

### 🔥 Most Critical Pattern: Git Push Lock Contention

4 out of 5 problem runs (1 failed + 4 cancelled) share the same root cause: **concurrent workflows trying to push to `main` at the same time**. The retry-with-rebase pattern works when only 1 workflow is pushing, but with 15+ workflows all committing within a 30-minute window, ref-lock races are inevitable.

**Affected runs:**
- Unified Audit Dashboard (FAILED)
- Consensus Outcome Tracker (CANCELLED)
- Quick Guess ML Agent (CANCELLED)
- Low-Score Winner Tracker (CANCELLED)
- Copy Trader Forward Test (CANCELLED — though also had price issues)

### 🔥 Second Pattern: Binance API Geo-Blocking (HTTP 451)

Affects nearly all crypto-related workflows. The Binance API returns 451 (Unavailable For Legal Reasons) from GitHub Actions runners, likely due to IP geo-restrictions on GitHub-hosted runners.

**Workaround in place:** Most scripts have Binance failover to OKX/CoinGecko, but the failover adds latency and sometimes all fallbacks also fail.

### 🔥 Third Pattern: Delisted / Missing Symbol Data

Symbols that no longer trade but are still in the system:
- **MATIC-USD** (renamed to POL-USD) — appears in QUAN ENGINE and Backtest runs
- **FDAX=F** — appears in Multi-Asset Copytrader
- **NKLA, RNDR-USD, SQ** — appear in Backtests
- **$DGLY, $MULN, $XSPA, + 28 more** — appear in Top Gainers Spike Scanner
- **BGBUSDT, GTUSDT** — Outcome Resolver can't fetch prices

### 🔥 Fourth Pattern: ML Model Feature Dimension Mismatch

Enhanced ML Crypto pipeline: models trained with 155 features are being fed 65 features at inference time. This affects BTC, ETH, BNB, SOL, XRP, TRX, ADA, AVAX, TAO — the top assets.

---

## Recommendations (Not Fixes — For Documentation Only)

1. **Git push contention:** Implement a distributed lock (e.g., Redis mutex or GitHub Actions concurrency groups) to serialize commits to `main`
2. **MATIC-USD → POL-USD:** Add a symbol alias/renaming map in the scanner configs
3. **Feature dimension mismatch:** Retrain models or add feature alignment validation before inference
4. **Binance 451:** Consider routing through a proxy or relying solely on OKX as primary source in CI
5. **Scout function signatures:** Audit and fix argument mismatches in `signal_vwap_deviation_scalp()`, `ema_ribbon_momentum()`, `bb_squeeze_breakout()`
6. **Missing modules:** Add `yfinance`, `transaction_costs`, `audit_trail` to `requirements.txt`
7. **`.pr41-review` submodule:** Remove from `.gitmodules` or add the URL to resolve the fatal error
8. **Node.js 20:** Plan migration to Node.js 24 compatible actions before June 2, 2026

---

## Run Inventory

| Run ID | Workflow Name | Conclusion | Key Issues |
|--------|--------------|------------|------------|
| 24524216893 | Unified Audit Dashboard | 🔴 FAILURE | ML ValueError, git lock-out, Binance 451 |
| 24527045714 | Consensus Outcome Tracker | 🟠 CANCELLED | Git push/pull loop |
| 24527537305 | Quick Guess ML Agent | 🟠 CANCELLED | Git lock contention |
| 24525271039 | Copy Trader Forward Test | 🟠 CANCELLED | Price fetch failures, git cancelled |
| 24524869258 | Low-Score Winner Tracker | 🟠 CANCELLED | Git conflicts (unstaged changes) |
| 24523921778 | Unified Audit Dashboard | 🟠 CANCELLED | Preceded the failed run |
| 24527429546 | QUAN ENGINE Live Scanner | 🟢 (hidden) | MATIC delisted, audit_trail missing, strategy import failure |
| 24527730704 | Enhanced ML Crypto | 🟢 (hidden) | Feature dim mismatch (65 vs 155), Bybit 403, yfinance missing |
| 24527319847 | Multi-Asset Copytrader | 🟢 (hidden) | FDAX=F delisted, external data unavailable, quality flags |
| 24524746296 | Multi-Asset Copytrader (prior) | 🟢 (hidden) | Same as above + NQ=F quality flag |
| 24527199994 | Market Beating System | 🟢 (hidden) | NumPy warnings, 4 forex pairs disabled |
| 24527432809 | Top Gainers Spike Scanner | 🟢 (hidden) | 31 delisted symbols, no price data |
| 24527655948 | Rapid Fire NOW Scanner | 🟢 (hidden) | Unicode error, CoinGecko 429, CoinCap DNS, ALL SOURCES FAILED |
| 24527626441 | Claude Gainer ML Live | 🟢 (hidden) | 5 circuit breakers tripped, 3 coins no data, data_fetcher.py missing |
| 24527582125 | Outcome Resolver | 🟢 (hidden) | BGBUSDT & GTUSDT price fetch ALL sources failed |
| 24527552041 | Audit Drift Telemetry | 🟢 (hidden) | 30/50 integrity check failed, CRYPTO probation exceeded |
| 24527633915 | Signal Quality Monitor | 🟢 (hidden) | No quality reports, forward tracking DB missing |
| 24526988058 | Run Backtests & Deploy | 🟢 (hidden) | Delisted symbols, 3 circuit breakers, scout argument mismatches |
| 24527696055 | Prediction Market Agents | 🟢 | Binance 451 (minor) |
| 24527552041 | Audit Drift Telemetry | 🟢 | Integrity check 30/50 rows failed |
| 24526988058 | Backtests & Deploy | 🟢 | Scout crashes, missing modules |
| 24527852846 | Test Portfolios | 🟢 | Clean |
| 24526742659 | Forex Smart Picks | 🟢 | Clean |
| 24527694815 | Rapid Validation Engine | 🟢 | Deployment curl error (minor) |
| 24527951908 | ALPHA Verify Predictions | 🟢 | Clean |
| 24527905682 | LuxAlgo Signal Generator | 🟢 | Clean |

---

*Report generated by Codebuff deep-scan on 2026-04-16. No fixes applied — findings documented for review.*
