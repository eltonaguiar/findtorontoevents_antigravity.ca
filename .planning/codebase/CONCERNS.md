# Codebase Concerns

**Analysis Date:** 2026-02-23

## Tech Debt

**Broad Exception Handling (Silent Failures):**
- Issue: Widespread use of bare `except Exception:` clauses that suppress errors without logging or recovery
- Files: `claude_gainer_ml/train_model.py` (lines 217-219, 235, 243), `alpha_engine/advanced_strategies.py` (100+, 217, 265, 503, 628, 798, 918, 1012, 1123), `backtest_framework.py` (997, 1188)
- Impact: Bugs in data fetching, API calls, and strategy computation get silently swallowed. Makes debugging extremely difficult when signals suddenly stop working
- Fix approach: Replace bare `except:` with specific exception types. Log all errors to file/console. Add metric tracking for exception frequencies

**Missing Fallback Chain Recovery:**
- Issue: Live scanner has multiple data source layers (Binance → CoinGecko → Bybit/OKX) but failures in middle layers silently degrade to broken fallbacks
- Files: `KIMI_RISEOFTHECLAW/live_scanner.py` (lines 42-133), `claude_gainer_ml/live_scanner.py` (44-50), `claude_gainer_ml/train_model.py` (64-70)
- Impact: If primary source (Binance) fails, fallback to CoinGecko returns incomplete/different data. Signals computed on bad data. No visibility into which data source was used for which symbol
- Fix approach: Add explicit data source validation. Log which source was used per symbol. Reject signals if data quality < threshold. Add circuit breaker to disable signals when fallback active for >N consecutive runs

**Bare `except ImportError` with Global State:**
- Issue: 10+ conditional imports (crypto_acceleration_engine, proven_crypto_forex_strategies, ml_signal_ranker, sqlite_store, etc.) set global flags but don't validate dependent code paths
- Files: `KIMI_RISEOFTHECLAW/live_scanner.py` (54-156 — 102 lines of conditional imports)
- Impact: If a module fails to import, code silently continues but downstream code that assumes that module is loaded will crash. Example: if `ml_signal_ranker` fails to import, `_HAS_ML = False` but code path that uses ML weights might still execute
- Fix approach: At startup, validate all required modules are present. If critical module (ML ranker, signal tracker, elimination engine) missing, fail fast with clear error. Make module presence explicit in function signatures

**Type Hints and Runtime Type Validation:**
- Issue: Minimal type hints. No runtime validation. Functions accept dicts/floats that may be None/invalid
- Files: Nearly all strategy files pass unvalidated data between functions
- Impact: Subtle bugs when API returns unexpected format (e.g., `null` instead of number). Type errors only manifest at runtime during signal generation
- Fix approach: Add return type hints to all strategy functions. Use Pydantic models for signal outputs. Validate before computation

## Known Bugs

**Gap-Chase Entry Blocker Not Enforced Globally:**
- Symptoms: Some algorithms still enter after large intraday moves. Documented case: RIVN entered at +26.6% gap-up, immediately faded -5%
- Files: `KIMI_RISEOFTHECLAW/live_scanner.py` (lines 334-344 — GAP_REJECT_THRESH defined but enforcement logic not found in entry code)
- Trigger: Run `live_scanner.py` during stock market opens with high-gap symbols
- Workaround: Manual filtering in Discord before taking signals
- Fix: Verify `GAP_REJECT_THRESH` is actually checked in algo signal generation. Add explicit gap-check gate before pick creation

**Symbol Concentration Not Hard-Capped:**
- Symptoms: Same ticker (e.g., RIVN) stacking across 4+ different algorithms simultaneously, creating extreme concentration risk
- Files: `KIMI_RISEOFTHECLAW/live_scanner.py` (line 349 — `MAX_SAME_SYMBOL_GLOBAL = 2` defined but not enforced)
- Trigger: When multiple independent algorithms trigger the same symbol
- Workaround: Manual deduplication in pick aggregation
- Fix: Add pre-generation deduplication loop that collapses duplicate symbols to single highest-confidence signal

**Model Health Agent False Positives:**
- Symptoms: Model health agent reports "Win rate 0.0%" and "Sharpe ratio -15.38" as critical alerts for test data
- Files: `test_model_health_agent.py`, `model_health_agent.log` (lines 5-6, 28, 49-50)
- Trigger: Training on small synthetic datasets with low variance
- Workaround: Ignore alerts for models with <20 closed picks
- Fix: Add minimum sample size check (n_samples >= 30) before computing performance metrics. Don't alert on edge cases

**SMOTE Disabled but May Still Be Referenced:**
- Symptoms: v3.0 disabled SMOTE-ENN for balanced training (memory/complexity) but code comments still reference it
- Files: `claude_gainer_ml/train_model.py` (lines 56-61 comments reference SMOTE but feature matrix already balanced by threshold)
- Impact: If someone re-enables SMOTE, may introduce data leakage or OOM on large coin sets
- Fix: Remove SMOTE import block entirely. Add comment explaining why class balance is achieved via lower gain threshold (3% → 8-12% positive rate)

## Security Considerations

**API Keys in .env Files (Not Committed but Discoverable):**
- Risk: `.env` file present in `KIMI_RISEOFTHECLAW/.env` contains CoinGecko API key, CryptoQuant key, etc. If leaked, all external APIs become compromised
- Files: `KIMI_RISEOFTHECLAW/.env` (gitignored but visible if .git directory accessed)
- Current mitigation: `.gitignore` blocks .env from commits. Keys scoped to read-only APIs (CoinGecko, CryptoQuant)
- Recommendations:
  - Use GitHub Secrets for CI/CD instead of .env files
  - Rotate all API keys monthly
  - Add API key validation on startup (test each key with dummy call)
  - Log API key usage (which key, when, by which algo) to detect abuse

**No Authentication on Local Signal Server:**
- Risk: If `alpha_engine` runs HTTP server (port 8000+), no auth required. Anyone on network can read live picks
- Files: `alpha_engine/main.py`, various API endpoints mentioned but implementation not visible
- Current mitigation: None detected
- Recommendations:
  - Require API token on all signal endpoints
  - Rate-limit per IP
  - Log all access attempts
  - Use HTTPS for transmission over network

## Performance Bottlenecks

**Backtest Framework Complexity (41,584 lines across 4 modules):**
- Problem: `KIMI_RISEOFTHECLAW/live_scanner.py` (9,363 lines) + related modules contain redundant feature computation loops. Features recalculated multiple times per run
- Files: `KIMI_RISEOFTHECLAW/live_scanner.py`, `KIMI_RISEOFTHECLAW/multi_source_fetcher.py`, `claude_gainer_ml/live_scanner.py` (40,583 lines)
- Cause: Each algorithm independently fetches data, computes indicators (RSI, ATR, EMA). No shared cache. Running 81 algorithms means 81x redundant computation
- Improvement path:
  - Create central indicator cache keyed by (symbol, timeframe, indicator_name)
  - Compute each indicator once per symbol per run
  - Share cache across all algorithms
  - Estimated speedup: 5-10x for live scanning

**Model Prediction Latency Not Tracked:**
- Problem: ML model loading, preprocessing, prediction happens during live signal generation but no timing data
- Files: `claude_gainer_ml/live_scanner.py` (load models line ~300+), `KIMI_RISEOFTHECLAW/ml_signal_ranker.py` (RandomForest inference)
- Cause: Model files (`.joblib` format, 5-20MB each) loaded from disk synchronously. ScalerTransform applied to 30-feature matrix for each coin
- Improvement path:
  - Add `@timing_decorator` to all model inference calls
  - Log prediction latency per symbol
  - If latency > 500ms, cache predictions or skip model for that run
  - Pre-load models at startup instead of lazy loading

**CoinGecko API Rate Limit Thrashing:**
- Problem: Rate-limited to 10-50 req/min depending on API tier. Live scanner hits limit every 15min run, causes 60s sleeps
- Files: `claude_gainer_ml/train_model.py` (RATE_LIMIT_DELAY = 1.6), `claude_gainer_ml/live_scanner.py` (line 67)
- Cause: No prioritization. Fetches data for ALL coins even if many are unchanged since last run
- Improvement path:
  - Track last-fetch timestamp per symbol
  - Skip coins not updated in last N hours
  - Use Binance for frequently-traded symbols (no rate limit)
  - Pre-fetch top 100 symbols daily, cache for 24h

## Fragile Areas

**Large Single-File Modules (9K+ lines):**
- Files: `KIMI_RISEOFTHECLAW/live_scanner.py` (9,363 lines), `claude_gainer_ml/train_model.py` (not measured but large), `claude_gainer_ml/live_scanner.py` (40,583 lines)
- Why fragile:
  - Impossible to navigate. All utility functions, config, algos mixed together
  - Changing one function requires reading 9K lines for context
  - Test coverage likely minimal (single monolithic test file if any)
  - Refactoring is high-risk (one change breaks multiple algos)
- Safe modification:
  - Never refactor entire file in one commit
  - Extract ONE clear module at a time (e.g., extract ATR calculation into `indicators.py`)
  - Add tests for extracted module BEFORE removing from monolith
  - Keep live scanner stable during extraction (no behavior changes)
- Test coverage: Gaps. No unit tests found for individual algos. Only integration tests

**Conditional Algorithm Registration (Subtle Logic Bugs):**
- Files: `KIMI_RISEOFTHECLAW/live_scanner.py` (lines 350-500+, algorithm dispatch logic)
- Why fragile: Algorithm list (ACCELERATION_SIGNAL_FUNCS, PROVEN_SIGNAL_FUNCS, etc.) built at runtime based on import success. If 1 import fails, algos silently disappear from output
- Safe modification:
  - Add validation loop that counts registered algos vs. expected algos
  - Warn if count mismatch (e.g., expected 81 algos but only 75 registered)
  - Document expected algo count in file header
  - Add unit test that asserts minimum algo count

**Model Training Data Quality Undocumented:**
- Files: `claude_gainer_ml/train_model.py` (data collection section), `ml_crypto_predictor/enhanced_models/` (no README about training data)
- Why fragile: Models retrain monthly on fresh data but no validation that data is clean. No check for:
  - Duplicate rows in training set
  - Data leakage (future data in features)
  - Missing values handled incorrectly
  - Synthetic data mixed with real (line 280 generates synthetic fallback)
- Safe modification:
  - Add data validation phase before training
  - Check for duplicates, NaNs, outliers
  - Log sample of first/last rows
  - Add assertion: `assert n_rows > 1000`, fail if training set too small

## Scaling Limits

**Model Joblib Storage (300+ GB Growing):**
- Current capacity: ~500 joblib files × 5-20MB each = ~5-100GB total. Git status shows many modified `.joblib` files
- Limit: Git LFS not configured. Pushing joblib files to GitHub exceeds repo size limits (>100GB → account restricted)
- Scaling path:
  - Move all `.joblib` to cloud storage (S3, GCS) or local git-ignored directory
  - Load models from cloud at runtime
  - Version models by date/hash, not by checking into git
  - Archive old model versions monthly

**Live Scanner Complexity (81 Algorithms):**
- Current capacity: 81 algorithms × 2000+ symbols × 5-15 runs/day = ~30K signal evaluations/day. Estimated 2-5 sec per run on modern machine
- Limit: If adding more algorithms, each adds ~30sec to run. By 150 algos, runtime becomes >30min, breaks 15min GitHub Actions schedule
- Scaling path:
  - Parallelize algo evaluation (currently sequential)
  - Use async/ThreadPoolExecutor for data fetching
  - Shard algorithms across multiple runners
  - Remove low-performing algos to make room for new research

**Random Forest Model Training on Large Feature Matrices:**
- Current capacity: 200+ coins × 30 features × ~250 training days = 1.5M rows × 30 cols. RandomForest trains in minutes but memory usage spikes
- Limit: 500+ coins would require >5GB RAM for training
- Scaling path:
  - Use LightGBM or XGBoost for faster training (100x speedup documented)
  - Train separate models per coin category (crypto/stock/forex)
  - Use online learning or incremental training

## Dependencies at Risk

**CoinGecko API Dependency (Single Point of Failure):**
- Risk: Live scanner depends on CoinGecko for market data, trending coins, fear/greed index. If CoinGecko down, signals cannot generate
- Impact:
  - Live scanner crashes with timeout
  - No trades executed
  - Dashboard shows "last updated: >2h ago"
- Current mitigation: Fallback to Binance for price data, but trending/F&G indices have no fallback
- Migration plan:
  - Add CoinCap (free, no rate limits) as second source for trending
  - Use local on-chain data (blockchain.info, Glassnode) for F&G proxy
  - Cache previous F&G value for 24h, use if current fetch fails

**scikit-learn / XGBoost Versions (Compatibility Risk):**
- Risk: `requirements.txt` specifies `scikit-learn>=1.0.0` and `xgboost>=1.7.0`. Major version bumps break serialized models
- Impact: If local sklearn updates to 2.0, saved `.joblib` models from v1.3 won't load (breaking change in tree serialization)
- Current mitigation: None detected. Requirements are loose (>=)
- Migration plan:
  - Pin exact versions: `sklearn==1.3.2`, `xgboost==1.7.6`
  - Add CI test that loads all `.joblib` files to detect compatibility breaks
  - Document retraining procedure when major versions upgrade

**yfinance (Yahoo Finance) Unofficial API:**
- Risk: yfinance scrapes Yahoo Finance (unofficial). Yahoo can block scraping or change HTML structure without notice
- Impact: Equity/forex data fetch fails overnight
- Current mitigation: Fallback to CoinGecko/Binance for crypto only
- Migration plan:
  - Switch to official data source (IEX Cloud for stocks, FRED for macro)
  - Keep yfinance as fallback
  - Add HTTP status code monitoring on yfinance requests

## Missing Critical Features

**No Automated Model Retraining Scheduler:**
- Problem: Models retrain manually or on demand. If model hasn't retrained in 30 days, predictions degrade (data distribution drift)
- Blocks: Cannot confidently declare "models are always fresh" in docs/dashboard
- Solution:
  - Add cron trigger in GitHub Actions: `schedule: 0 2 * * 1` (weekly Monday 2am UTC)
  - Log retraining timestamp to `training_meta.json`
  - Alert if last retrain > 14 days old
  - Store retraining logs for audit

**No A/B Testing Framework for Strategy Changes:**
- Problem: New algorithm or hyperparameter change deployed immediately to live trading. No way to measure if change improves/hurts performance
- Blocks: Cannot safely experiment with new strategies
- Solution (already exists in codebase): `ab_testing_agent/` directory. Need to integrate with live scanner
  - Route 50% of picks to control (old algo), 50% to treatment (new algo)
  - Track performance divergence
  - Auto-rollback if treatment underperforms > 2 std devs
  - Log results to dashboard

**No Live TP/SL Tracking Against Real Prices:**
- Problem: TP/SL levels are calculated but never validated against actual market execution
- Blocks: Cannot know if TP is actually reachable (too tight) or SL too loose
- Files: `claude_gainer_ml/tp_sl_tracker.py` exists but unclear if actively used
- Solution:
  - Query Binance hourly for actual high/low of each open pick
  - Check if TP/SL was hit
  - Compute `% picks hit SL before TP`, `avg time to TP`, etc
  - Log to database for analytics

## Test Coverage Gaps

**No Unit Tests for Strategy Signals:**
- What's not tested: Individual strategy algorithms (80+ algo functions). No test verifies that RSI signal triggers correctly, ATR calculation is accurate, etc
- Files: `alpha_engine/advanced_strategies.py`, `KIMI_RISEOFTHECLAW/proven_crypto_forex_strategies.py`, all signal generators
- Risk: A one-character typo in indicator math goes undetected until trades fail
- Priority: **HIGH** — These are core to all signal generation
- Solution:
  - Create `test_strategies.py` with fixtures for sample OHLCV data
  - For each strategy, verify: (1) signal triggers on known patterns, (2) math checks out (RSI bounds 0-100, etc)
  - Run on every commit via GitHub Actions

**No Integration Tests for Data Pipeline:**
- What's not tested: Full end-to-end flow (fetch data → compute features → generate picks → output JSON). No test verifies output is valid
- Files: `claude_gainer_ml/live_scanner.py`, `KIMI_RISEOFTHECLAW/live_scanner.py`
- Risk: Pipeline produces empty picks or malformed JSON without obvious reason
- Priority: **HIGH** — Breaks dashboards if output format invalid
- Solution:
  - Create `test_live_scanner_e2e.py` that mocks API calls
  - Run scanner with sample data
  - Assert output is valid JSON with correct schema
  - Check pick count is reasonable (>0, <1000)

**No Tests for Error Handling:**
- What's not tested: What happens when API fails, model loading fails, feature computation returns NaN
- Files: Everywhere `except Exception:` blocks exist
- Risk: Edge cases cause silent failures
- Priority: **MEDIUM** — Hard to reproduce but critical when they occur
- Solution:
  - Create `test_error_cases.py` with fixtures that trigger errors
  - Verify graceful degradation (fallback used, error logged, signal quality flagged)

**No Backtests with Real Data on Recent Strategies:**
- What's not tested: Wave 2-6 strategies (SFP, BOS, funding carry, on-chain, event-driven, advanced) — no recent backtest results
- Files: `alpha_engine/pattern_strategies.py`, `alpha_engine/cyclical_strategies.py`, `alpha_engine/onchain_strategies.py`
- Risk: Strategies may be overfitted or simply broken
- Priority: **MEDIUM** — Academic backing exists but no proof they work on live data
- Solution:
  - Run `simpleton_backtester.py` for each strategy pair/timeframe combo
  - Require Sharpe > 0.5 before live deployment
  - Store results in `alpha_engine/backtest_results/`

---

*Concerns audit: 2026-02-23*
