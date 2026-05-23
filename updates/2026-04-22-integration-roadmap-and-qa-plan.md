# 8 Integration Modules — Roadmap & QA Plan

**Date:** 2026-04-22
**Status:** PLAN
**Author:** Buffy (Codebuff AI)
**Branch Target:** main

---

## 1. Executive Summary

Seven new production modules (~4,060 lines) implementing 8 trading system integrations have been created and smoke-tested. This document outlines the **full roadmap** for production readiness and the **QA strategy** to validate each module before live deployment.

---

## 2. Module Inventory

| # | Module | File | Lines | Category | Optional Deps | Smoke Test |
|---|--------|------|-------|----------|---------------|------------|
| 1 | Dynamic Universe Selection | `alpha_engine/dynamic_universe.py` | 573 | Data / Universe | yfinance | ✅ Pass |
| 2 | OpenBB/FRED Macro Pipeline | `data_providers/macro_data_pipeline.py` | 413 | Data / Macro | openbb, yfinance | ✅ Pass |
| 3 | FinGPT Sentiment | `alpha_engine/fingpt_sentiment.py` | 437 | NLP / Sentiment | transformers, finnhub-client | ✅ Pass |
| 4 | Market Making (AS/Grid/XEMM) | `alpha_engine/market_making.py` | 549 | Strategies / MM | None (pure math) | ✅ Pass |
| 5 | HiFi Backtesting | `alpha_engine/hifi_backtest.py` | 671 | Backtest / Sim | None (pure numpy) | ✅ Pass |
| 6 | Multi-Exchange Executor | `alpha_engine/multi_exchange_executor.py` | 677 | Execution / CCXT | ccxt | ✅ Pass |
| 7 | FinRL RL Agent | `alpha_engine/finrl_agent.py` | 739 | ML / RL | stable-baselines3, gymnasium | ✅ Pass |

**Total: 4,059 lines of new production code across 7 files.**

---

## 3. Phased Rollout Roadmap

### Phase 1 — Foundation (Current: 2026-04-22)

- [x] Create all 7 modules with fallback patterns
- [x] Backward-compatible API for `scanner.py` (`load_dynamic_symbols`, etc.)
- [x] Smoke tests passing for all modules
- [x] Code reviewer fixes applied (8 bugs/quality issues)
- [x] `py_compile` passes for all modules

### Phase 2 — QA & Hardening (2026-04-22 → 2026-04-25)

- [ ] Unit test suite for each module (see QA Plan §4)
- [ ] Integration test: dynamic_universe → scanner.py pipeline
- [ ] Integration test: pick_to_order → executor → risk manager chain
- [ ] Integration test: macro_signal → confluence_engine wiring
- [ ] Edge case / adversarial testing (see QA Plan §5)
- [ ] Performance benchmarks for hot paths (see QA Plan §6)

### Phase 3 — Production Wiring (2026-04-25 → 2026-04-28)

- [ ] Wire `MacroDataPipeline.get_macro_signal()` into `confluence_engine.py` as new vote
- [ ] Wire `fingpt_sentiment()` into `scanner.py` for EQUITY/FOREX picks
- [ ] Wire `DynamicUniverseSelector.select()` into scanner's startup symbol load
- [ ] Wire `HiFiBacktestEngine` into `production_scanner.py` validation path
- [ ] Add `market_making` strategies as new `STRATEGY_FAMILY` in `config.py`
- [ ] Add `RLAgent` as optional scoring booster in `score_booster.py`

### Phase 4 — Live Deployment (2026-04-28+)

- [ ] Enable dynamic universe selection in CI scans (replace static list)
- [ ] Enable macro signal in confluence scoring (weight: 0.05 initially)
- [ ] Enable sentiment scoring for non-crypto picks (weight: 0.03)
- [ ] Enable executor dry-run in CI for paper-trade verification
- [ ] Monitor for 7 days before enabling live execution
- [ ] Enable RL agent scoring only after 14-day paper validation

---

## 4. QA Plan — Unit Tests

Each module needs a dedicated test file under `tests/`. All tests must pass both **with** and **without** optional dependencies installed (fallback path coverage).

### 4.1 `tests/test_dynamic_universe.py`

| Test Case | Description | Pass Criteria |
|-----------|-------------|---------------|
| `test_selector_instantiation` | `DynamicUniverseSelector()` creates without error | No exception |
| `test_get_regime` | `get_regime()` returns one of: bull, bear, neutral, crisis | String in allowed set |
| `test_backward_compat_load_dynamic_symbols` | `load_dynamic_symbols()` returns list | `isinstance(result, list)` |
| `test_backward_compat_load_dynamic_symbol_meta` | `load_dynamic_symbol_meta()` returns dict | `isinstance(result, dict)` |
| `test_backward_compat_generate_dynamic_universe` | `generate_dynamic_universe()` returns dict with expected keys | Has `dynamic_yf_map`, `rankings` |
| `test_select_returns_symbols` | `select(asset_class="crypto")` returns non-empty dict | `len(result) > 0` |
| `test_select_invalid_asset_class` | `select(asset_class="nonexistent")` returns empty or fallback | No exception |
| `test_missing_yfinance_fallback` | Mock yfinance import failure → returns config symbols | Graceful fallback |
| `test_stale_cache_rejected` | Cache file >2h old → `load_dynamic_symbols()` returns `[]` | Empty list |

### 4.2 `tests/test_macro_data_pipeline.py`

| Test Case | Description | Pass Criteria |
|-----------|-------------|---------------|
| `test_pipeline_instantiation` | `MacroDataPipeline()` creates without error | No exception |
| `test_get_yield_curve_structure` | Returns dict with 2y, 10y, 30y keys and numeric values | All values are float |
| `test_get_macro_signal_structure` | Returns dict with regime, composite_score, signals | regime in allowed set, score in [-1, 1] |
| `test_recession_probability_range` | Returns float between 0 and 1 | `0.0 <= p <= 1.0` |
| `test_fred_unavailable_fallback` | Mock FRED API failure → falls back to yfinance ETF proxies | Returns non-empty dict |
| `test_all_fallbacks_fail` | Mock all external calls failing → returns cached/baseline | Returns dict (not empty) |
| `test_cache_ttl_enforced` | Cache >24h → refetch triggered | Fresh data fetched |
| `test_duration_based_yield_estimate` | Verify ETF price → yield conversion with known duration | Yield within ±1% of expected |

### 4.3 `tests/test_fingpt_sentiment.py`

| Test Case | Description | Pass Criteria |
|-----------|-------------|---------------|
| `test_equity_headline_bullish` | "Apple beats earnings" → score > 0 | `score > 0` |
| `test_equity_headline_bearish` | "Tesla misses targets, layoffs" → score < 0 | `score < 0` |
| `test_equity_headline_neutral` | "Microsoft announces dividend" → score near 0 | `abs(score) < 0.2` |
| `test_crypto_returns_none` | BTC/ETH symbols → `None` (handled by other modules) | `result is None` |
| `test_forex_headline` | "EUR/USD rises on ECB hawkish tone" → non-None | `score is not None` |
| `test_empty_text_returns_none` | No text provided and no Finnhub → `None` | `result is None` |
| `test_batch_analysis` | `analyze_news()` with 5 items → list of 5 scores | `len(results) == 5` |
| `test_finnhub_fallback` | Mock FinBERT/FinGPT unavailable → keyword scoring works | Score still computed |

### 4.4 `tests/test_market_making.py`

| Test Case | Description | Pass Criteria |
|-----------|-------------|---------------|
| `test_as_quotes_symmetric_zero_inventory` | Zero inventory → symmetric bid/ask around mid | `abs(bid_offset) ≈ abs(ask_offset)` |
| `test_as_quotes_shift_with_inventory` | Positive inventory → reservation price below mid | `reservation_price < mid` |
| `test_as_spread_widens_with_volatility` | Higher vol → wider spread | `spread_2 > spread_1` when `vol_2 > vol_1` |
| `test_grid_trader_layout` | `compute_grid()` returns orders centered on price | Center within grid range |
| `test_grid_total_orders` | Grid with 10 levels → 20 orders (10 buy + 10 sell) | `total_orders == 20` |
| `test_xemm_profitable_spread` | Bid_A < Ask_B → actionable, positive profit | `actionable == True, net_profit_bps > 0` |
| `test_xemm_unprofitable_spread` | Bid_A > Ask_B → not actionable | `actionable == False` |
| `test_as_edge_cases` | vol=0, inventory=0 → no crash | Returns valid quotes |

### 4.5 `tests/test_hifi_backtest.py`

| Test Case | Description | Pass Criteria |
|-----------|-------------|---------------|
| `test_slippage_fixed` | Fixed slippage 5bps → fill price shifted by exactly 5bps | Expected offset |
| `test_slippage_percent` | Percentage slippage applied correctly | Within tolerance |
| `test_slippage_volume_based` | Larger order → more slippage | `slippage_big > slippage_small` |
| `test_latency_delays_fill` | Order submitted at T=0, latency=100ms → fill at T+100ms | Correct timestamp |
| `test_partial_fill` | Order for 10 units, only 5 available → partial fill | `filled_qty == 5, status == partially_filled` |
| `test_market_impact` | Large market buy → price moves up | `fill_price > mid_price` |
| `test_engine_run_basic` | Run engine on simple signal series → produces results | Has `total_pnl`, `trades`, `sharpe` |
| `test_zero_slippage_matches_naive` | Slippage=0, latency=0 → matches naive bar backtest | PnL within 0.1% |

### 4.6 `tests/test_multi_exchange_executor.py`

| Test Case | Description | Pass Criteria |
|-----------|-------------|---------------|
| `test_dry_run_market_buy` | Market buy in dry-run → simulated fill | `success == True, filled_price > 0` |
| `test_dry_run_limit_sell` | Limit sell in dry-run → simulated fill | `success == True` |
| `test_dry_run_no_real_orders` | Dry-run never calls CCXT `createOrder` | CCXT mock not called |
| `test_risk_limit_rejects_oversize` | Order > max_position → rejected | `success == False, reason contains "risk"` |
| `test_risk_limit_rejects_concentration` | Too many same-symbol orders → rejected | `success == False` |
| `test_pick_to_order_symbol_normalization` | "BTC-USD" → "BTC/USDT", "ETHUSDT" → "ETH/USDT" | Correct CCXT symbol |
| `test_pick_to_order_pickless` | Invalid pick dict → graceful error | Returns result with `success == False` |
| `test_smart_routing_best_price` | Binance=100, Bybit=99.9 → routes to Bybit for buy | Exchange = "bybit" |
| `test_api_keys_lazy_loaded` | Keys not accessible at import time | `_get_exchange_keys` only called on connect |
| `test_ccxt_type_mapping` | "stop_market" maps to "stop_market" (not "stopmarket") | Correct type string |
| `test_execution_log_persists` | Order logged to `execution_log.json` | File exists with entry |

### 4.7 `tests/test_finrl_agent.py`

| Test Case | Description | Pass Criteria |
|-----------|-------------|---------------|
| `test_trading_env_reset` | `env.reset()` returns observation of correct shape | `obs.shape == (lookback + n_features,)` |
| `test_trading_env_step_buy` | Step with BUY action → position increases | `position > 0` after buy |
| `test_trading_env_step_sell` | Step with SELL action → position decreases | `position < 0` after sell |
| `test_trading_env_done_flag` | Episode ends after all steps | `done == True` eventually |
| `test_feature_engineer_output` | `build_features(prices)` returns 2D array | `ndim == 2, shape[1] == 8` |
| `test_rl_agent_rule_based_fallback` | Without SB3 → uses rule-based agent | `agent._model is None, agent.algorithm == "ppo"` |
| `test_rl_agent_predict_returns_action` | `agent.predict(obs)` returns int 0-4 | `0 <= action <= 4` |
| `test_rl_agent_train_returns_metrics` | `agent.train(100)` returns dict with keys | Has `avg_total_pnl`, `avg_total_trades` |
| `test_numpy_none_check` | `features=None` → creates zeros (not truth-value error) | No ValueError |
| `test_gym_wrapper_obs_space` | Wrapper defines correct observation space | `space.shape matches features` |

---

## 5. QA Plan — Edge Cases & Adversarial Testing

### 5.1 Input Validation

| Module | Edge Case | Expected Behavior |
|--------|-----------|-------------------|
| dynamic_universe | Empty config (`CRYPTO_SYMBOLS = {}`) | Returns empty universe, no crash |
| macro_pipeline | FRED returns HTML error page | JSON parse fails → fallback to yfinance |
| fingpt_sentiment | 10,000-char headline | Truncated to 512 tokens, no OOM |
| market_making | mid_price = 0 | Division guard → returns None/zero quotes |
| hifi_backtest | Empty OHLCV DataFrame | Returns empty results, no crash |
| executor | Symbol not on any exchange | Returns `success=False`, no crash |
| finrl_agent | Prices array of length 1 | Env returns done immediately, no IndexError |

### 5.2 Concurrency & State

| Module | Test | Expected Behavior |
|--------|------|-------------------|
| dynamic_universe | Two selectors writing cache simultaneously | No file corruption (atomic write) |
| executor | Two orders submitted simultaneously | Risk manager checks cumulative position |
| macro_pipeline | Parallel cache reads | No race condition (read-only after write) |

### 5.3 Dependency Absence

| Missing Dep | Module | Test | Expected |
|-------------|--------|------|----------|
| yfinance | dynamic_universe | Mock import error | Falls back to config symbols |
| openbb | macro_pipeline | Mock import error | Falls back to FRED API |
| transformers | fingpt_sentiment | Mock import error | Falls back to keyword scoring |
| ccxt | executor | Mock import error | Dry-run still works, live mode raises clear error |
| stable-baselines3 | finrl_agent | Mock import error | Rule-based agent used, no crash |
| gymnasium | finrl_agent | Mock import error | Custom env still works, SB3 wrapper skipped |

---

## 6. QA Plan — Performance Benchmarks

### 6.1 Critical Path Benchmarks

| Module | Operation | Target | Max Acceptable |
|--------|-----------|--------|----------------|
| dynamic_universe | `select()` with 200 symbols | <500ms | 2s |
| macro_pipeline | `get_macro_signal()` (cached) | <50ms | 200ms |
| macro_pipeline | `get_macro_signal()` (fresh FRED) | <3s | 10s |
| fingpt_sentiment | `analyze_headline()` (keyword) | <1ms | 5ms |
| fingpt_sentiment | `analyze_headline()` (FinBERT) | <200ms | 1s |
| market_making | `compute_quotes()` | <0.1ms | 1ms |
| hifi_backtest | `run()` on 10K bars | <5s | 30s |
| executor | `submit_order()` (dry-run) | <10ms | 50ms |
| finrl_agent | `predict()` (rule-based) | <1ms | 5ms |
| finrl_agent | `predict()` (SB3 PPO) | <10ms | 50ms |

### 6.2 Memory Benchmarks

| Module | Operation | Target Memory | Max Acceptable |
|--------|-----------|---------------|----------------|
| hifi_backtest | 50K bars with order book | <500MB | 1GB |
| finrl_agent | Training 100K steps | <2GB | 4GB |
| macro_pipeline | Full FRED dataset cache | <10MB | 50MB |

---

## 7. QA Plan — Integration Test Matrix

| Source Module | Target Module | Integration Point | Test Description |
|---------------|---------------|-------------------|------------------|
| dynamic_universe | scanner.py | `load_dynamic_symbols()` | Scanner gets non-empty symbol list |
| macro_pipeline | confluence_engine.py | `get_macro_signal()` | Macro vote added to confluence score |
| fingpt_sentiment | scanner.py | `fingpt_sentiment()` | Sentiment score used in EQUITY picks |
| hifi_backtest | production_scanner.py | `HiFiBacktestEngine` | Pick validated with realistic slippage |
| executor | smart_picks_engine.py | `pick_to_order()` | Pick → dry-run execution succeeds |
| market_making | config.py | `STRATEGY_FAMILY` | MM strategies appear in scanner output |
| finrl_agent | score_booster.py | `RLAgent.predict()` | RL score boosts pick confidence |

---

## 8. QA Plan — Regression Guard

All new modules must pass in CI without breaking existing tests:

1. **Existing CI suite:** `validate_quality_gates.py`, `validate_hoffman_combos.py`, `validate_real_data.py`, `validate_team_alpha.py`
2. **New guard:** Add `validate_integration_modules.py` that:
   - Imports all 7 modules
   - Runs smoke tests
   - Checks backward compatibility (`load_dynamic_symbols` still works)
   - Verifies no optional dep is required at import time
3. **GitHub Actions:** Add to `audit-dashboard.yml` paths if these modules feed into dashboard data

---

## 9. Acceptance Criteria

Before any module enters Phase 4 (Live Deployment):

- [ ] **All unit tests pass** (§4 — minimum 9 tests per module = 63 total)
- [ ] **All edge case tests pass** (§5)
- [ ] **All dependency-absence tests pass** (§5.3 — fallback paths work)
- [ ] **Performance within targets** (§6 — no module exceeds max time/memory)
- [ ] **Integration tests pass** (§7 — wired modules interact correctly)
- [ ] **Existing CI unaffected** (§8 — no regressions in existing tests)
- [ ] **7-day paper trading validation** (Phase 4 — for execution modules)
- [ ] **Code review sign-off** (at least 1 human review of each module)

---

## 10. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| yfinance rate limits block dynamic universe | Medium | Low | Cache + fallback to config symbols |
| FRED API key not configured | High | Low | Multi-layer fallback (OpenBB → FRED → yfinance → baseline) |
| CCXT API changes break executor | Low | High | Pin ccxt version; dry-run default; integration tests |
| SB3 model overfits in production | Medium | Medium | Walk-forward validation; rule-based fallback; 14-day paper |
| Market making inventory risk | Medium | High | Inventory limits; kill switch; position cap per symbol |
| Slippage model underestimates live costs | Medium | Medium | Conservative default (5bps); tune from execution logs |
| Macro signals lag real-time (24h cache) | High | Low | Macro is slow-moving; supplement with VIX (more frequent) |

---

## 11. Files Changed (for this commit)

```
updates/2026-04-22-integration-roadmap-and-qa-plan.md   (NEW — this file)
```

---

*End of plan. Next action: commit to main and begin Phase 2 QA execution.*
