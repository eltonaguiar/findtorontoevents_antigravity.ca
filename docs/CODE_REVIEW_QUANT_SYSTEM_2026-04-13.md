# Quantitative trading stack — code review (2026-04-13)

**Scope:** Repository-wide assessment of trading/signal/backtest/risk components (`alpha_engine/`, `baby_strategies/`, `audit_trail/`, `copy_trader_intel/`, `tools/`, configs, tests). This is **not** a line-by-line audit of every file; it reflects architecture, repeated patterns, and documented protocol gaps.

---

## 1. Overall architecture & design

### Strengths
- **Clear conceptual layers** exist in places: `alpha_engine/` (signals, forward test, scoring), `baby_strategies/` (indicator logic), `audit_trail/` (recording/dashboard payloads), `copy_trader_intel/` (external trader research), `cross_aggregation/` (conviction picks).
- **`TESTING_PROTOCOL.MD`** explicitly defines a layered stack (data integrity → IS/OOS → walk-forward → stats → Monte Carlo → forward portfolios) and records **known gaps** (e.g. forward test pipeline health, promotion gate vs live dashboard).
- **Portfolio simulation** in `alpha_engine/forward_test_portfolios.py` separates candidate picks, gates (MTF/ensemble), sizing, and TP/SL/max-hold exits.

### Risks / gaps
- The repo is a **monorepo** with **many parallel systems** (KIMI, battleground, genome, VR, site tooling). The pipeline is **not** a single linear DAG; duplicate strategy definitions and overlapping scanners increase maintenance cost.
- **Recommendation:** Maintain a single **system map** (`docs/ARCHITECTURE_OVERVIEW.md`) and enforce “one canonical path” per asset class for promotion (align with `strategy_registry.json` / `TESTING_PROTOCOL.MD`).

---

## 2. Data handling & pre-processing

### Strengths
- **Multi-source failover** is a stated rule (e.g. Binance mirrors → CoinGecko → KuCoin) in several tools.
- **SQLite / JSON stores** in `alpha_engine/` and `audit_trail/` provide reproducible local artifacts.
- **Quality gates** (e.g. `audit_trail/quality_gates.py`, HF strict JSON) reduce bad rows at publish time.

### Risks / gaps
- **Consistency** across systems for timezone (UTC), corporate actions (equities), and **stale price** handling is uneven—some paths use `STALE_DATA_NO_PRICE` exclusions in stats (`forward_validator.py`).
- **Missing-value / outlier** treatment is **strategy-specific**; there is no universal validation module applied to every ingest.
- **Recommendation:** Centralize a small `data_validation` module: monotonic timestamps, dtype checks, and explicit NA policies per asset class; call from ingest jobs before picks hit the dashboard.

---

## 3. Feature engineering

### Strengths
- Baby strategies typically compute indicators on **historical bars only** inside `generate_signals(df, symbol)` (no future rows in the same bar if implemented correctly).
- **Survivor / tiered** backtests (`incubator/backtest_results/`, `survivor_backtest` docs) show awareness of **multi-symbol** validation.

### Risks / gaps
- **Look-ahead risk** appears if any code uses **full-series** stats (e.g. global mean/std including future bars). Review any “batch” features on full DataFrames without rolling windows.
- **Recommendation:** Add explicit tests that **last bar** features use only `iloc[-1]` from rolling objects with sufficient `min_periods`; forbid `center=True` rolling without careful alignment for live simulation.

---

## 4. Model implementation

### Strengths
- Multiple ML / ensemble components (`ml_crypto_predictor`, battleground, calibration tests in `tests/test_ensemble_calibration.py`).
- **Hyper-parameters** often live in JSON (`config/`, strategy `params` dicts) or scanner registry (`forward_signal_scanner.py`).

### Risks / gaps
- **Reproducibility** varies: not all pipelines document **seeds** or fixed `numpy`/`random` seeds in one place.
- **Recommendation:** Standardize `RANDOM_SEED` in a single config; log seed + git SHA + data snapshot id per training run.

---

## 5. Signal generation (long/short)

### Strengths
- Direction is usually explicit (`LONG`/`SHORT`/`BUY`/`SELL`); dashboard normalizes in places.
- **Conviction stack** and **hc_filter.js** apply multi-gate filtering with confidence and trust floors.

### Risks / gaps
- **Naming inconsistency** (`BUY` vs `LONG`) can break filters if not normalized at boundaries.
- **Recommendation:** One normalization function (Python + JS shared contract) used at pick publish time; unit tests for direction mapping.

---

## 6. Take-profit / stop-loss logic

### Strengths
- ATR-based TP/SL is common in baby strategies; forward portfolios enforce exits with **TP/SL/MAX_HOLD** (`forward_test_portfolios.py`).
- **Inverse / slippage** modeling exists (`inverse_edge_system.py` with `SLIPPAGE_PER_TRADE`).

### Risks / gaps
- **Gaps / halts** (equities, thin crypto) are not uniformly modeled.
- **Recommendation:** Document assumptions per asset class; optional gap model in forward sim for equities.

---

## 7. Back-testing & evaluation

### Strengths
- Rich backtest tooling (`tools/hyro_backtest.py`, survivor pipelines, Monte Carlo in `alpha_engine/validation/monte_carlo.py`).
- Metrics: Sharpe, Sortino, PF, DD appear in multiple modules.

### Risks / gaps
- **`TESTING_PROTOCOL.MD`** notes **forward test** and **walk-forward staleness** issues—treat metrics as **conditional on pipeline health**.
- **Slippage/commission** not applied uniformly across all backtests (some have it, some idealized).
- **Recommendation:** Tag each backtest output with `cost_model: {slippage, commission, latency_ms}` metadata.

---

## 8. Risk management & position sizing

### Strengths
- **Quarter-Kelly** style sizing and caps in `forward_test_portfolios.py` (`_position_size`, max equity pct).
- **Max positions**, **freshness hours**, and **portfolio-level** stats tracked.

### Risks / gaps
- **Global exposure per asset class** is not always enforced in one central risk service—often duplicated per scanner.
- **Recommendation:** Single `risk_policy.json` loader (see existing `tests/test_risk_policy_loader.py`) wired into all publishers.

---

## 9. Execution & integration

### Strengths
- **Failover chains** for HTTP (Binance mirrors, etc.) in several scripts.
- **TradingView / paper** integration documented in skills; PHP APIs for site.

### Risks / gaps
- **Retry/backoff** is ad hoc; not all callers use shared `tenacity`/wrapper.
- **Order logging** varies by path (some JSONL/SQLite).
- **Recommendation:** Thin `http_client.py` with retries, logging, and rate-limit headers for exchange calls.

---

## 10. Code quality & maintainability

### Strengths
- Extensive **typing** in newer Python; dataclasses for signals in baby strategies.
- Large but **named** modules by domain.

### Risks / gaps
- **Inconsistent** formatter/linter across subprojects; root `package.json` is test-centric; **no root `pyproject.toml`** for Ruff/black (added as optional baseline in this PR via `pytest.ini` + docs).
- **Recommendation:** Introduce Ruff + pre-commit gradually on `alpha_engine/` and `tests/` first.

---

## 11. Testing

### Strengths
- Many **pytest** modules for gates, HF policy, conviction, polymarket scoring, dashboard regressions.
- **Playwright** for audit UI and JS error checks.

### Risks / gaps
- Coverage is **uneven**; not every baby strategy has a unit test.
- **Recommendation:** Minimum tests: direction normalization, one golden-file JSON per critical gate, smoke for `mimo_strategy_validation_smoke.py`-style imports.

---

## 12. Documentation

### Strengths
- `TESTING_PROTOCOL.MD`, `ALL_STRATEGIES.md`, HF docs, `DATA_SOURCES_INTEGRATION.md` (data map).

### Risks / gaps
- Root `README.md` is minimal for onboarding quants.
- **Recommendation:** Link developer setup (`docs/DEVELOPER_SETUP_QUANT.md`) and architecture overview from README.

---

## 13. Security & compliance

### Strengths
- `.gitignore` excludes `.env`, token filename patterns; FTP/env usage documented in rules.
- **No secrets in code** should be policy (PATs must be revoked if leaked).

### Risks / gaps
- **Dependency scanning** (Dependabot/Snyk) not evidenced at repo root for all ecosystems.
- **Recommendation:** Enable GitHub Dependabot; pin `requirements.txt` major versions; periodic `pip audit` / `npm audit`.

---

## 14. Performance & scalability

### Strengths
- Pandas/NumPy usage throughout; vectorized indicators in baby strategies.
- Some **batch** and **scanner** jobs are designed for CI.

### Risks / gaps
- Full historical rescans can be **CPU heavy**; parallelization is inconsistent.
- **Recommendation:** For heavy jobs, standardize on chunked reads + `multiprocessing` pool with deterministic ordering.

---

## Priority actions before production deployment

1. **Verify** forward-test and walk-forward jobs per `TESTING_PROTOCOL.MD` §6–7.  
2. **Normalize** direction and asset class at publish boundary; add tests.  
3. **Unify** cost model metadata on backtest artifacts.  
4. **Centralize** risk limits and ingest validation.  
5. **Expand** pytest smoke for new strategies and critical gates.  
6. **Secrets:** rotate any exposed tokens; use env-only credentials.

---

## References (in-repo)

- `TESTING_PROTOCOL.MD`
- `alpha_engine/forward_test_portfolios.py`
- `alpha_engine/forward_validator.py`
- `docs/DATA_SOURCES_INTEGRATION.md`
- `docs/ARCHITECTURE_OVERVIEW.md` (added with this review)
