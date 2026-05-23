# Researcher Profile: Dr. Alexey Kozlov

## Persona
- **Title:** Open-Source Crypto ML Researcher
- **Expertise:** Evaluating GitHub projects, code quality, community adoption
- **Years Experience:** 8
- **Background:** PhD Moscow State, former maintainer of popular ML library, now curates best open-source crypto trading projects.

## Research Scope
**Primary Question:** How does this codebase's architecture compare to best-in-class open-source crypto prediction systems (Freqtrade, TensorTrade), and where are the critical gaps?

**Evaluation Date:** 2026-02-24
**Codebase:** `findtorontoevents_antigravity.ca` (multi-system crypto/equity/forex ML trading platform)

---

## 1. PROJECT STRUCTURE & MODULARITY

### Current Architecture (Actual Findings)

The repository contains **6 major trading subsystems** operating semi-independently:

| Subsystem | Directory | Purpose | Module Count |
|-----------|-----------|---------|-------------|
| Alpha Engine | `alpha_engine/` | Multi-strategy quant research (crypto/equity/forex) | 60+ Python files |
| Crypto ML Edge | `crypto_ml_edge/` | LightGBM-based crypto prediction | 15+ Python files |
| ML Battleground | `ml_battleground/` | A/B/C system competition framework | 3 sub-systems |
| KIMI Rise of the Claw | `KIMI_RISEOFTHECLAW/` | 81-algorithm live scanner | 20+ Python files |
| Pine Generator | `pine_generator/` | TradingView Pine Script generation | Variable |
| Scripts (worldclass) | `scripts/worldclass/` | Research pipeline utilities | 15+ Python files |

### Strengths (vs. Freqtrade/TensorTrade patterns)

1. **Alpha Engine has proper layered architecture:**
   - `data/` layer (7 modules: price_loader, fundamentals, macro, sentiment, insider, earnings, universe)
   - `features/` factory (14 feature families: momentum, volatility, regime, etc.)
   - `strategies/` with ABC base class (`strategies/base.py` — `StrategyType`, `Signal`, `StrategyConfig` dataclasses)
   - `validation/` engine (walk-forward, purged CV, Monte Carlo, stress test)
   - `ensemble/` meta-learner (regime allocator, signal combiner)
   - `backtest/` engine with cost models and position sizing
   - `reporting/` layer
   - This mirrors Freqtrade's separation of concerns quite well.

2. **Crypto ML Edge follows research-backed constraints:**
   - Config explicitly limits to 10 liquid pairs, 1h+4h timeframes, 10-20 features
   - Comment in `config.py`: "Everything else is overfitting waiting to happen"
   - Transaction cost model with per-pair slippage calibration (`SLIPPAGE_MAP`)
   - This is more disciplined than most open-source projects.

3. **ML Battleground uses shared components well:**
   - `shared/` directory contains reusable modules: `cost_model.py`, `data_fetcher.py`, `indicators.py`, `risk_manager.py`, `sr_engine.py`, `trade_filters.py`, `validator.py`, `discord_notify.py`
   - Three systems (A: Filter, B: Regime, C: DeepLearn) compete on same data

### Weaknesses

1. **Monorepo sprawl:** 100+ top-level files including scripts, strategies, backtests, and markdown docs mixed together. Freqtrade keeps root clean with `freqtrade/` package, `tests/`, `docs/`, and config files only.

2. **Duplicated subsystems:** KIMI_RISEOFTHECLAW, KIMI_FEB172026, KIMI_CLAW_RESEARCH_FEB162026 appear to be evolutionary snapshots rather than branches. Each has its own `sqlite_store.py`, `elimination_engine.py`, `ml_signal_ranker.py`. In Freqtrade, this would be handled via git tags/releases.

3. **No unified package structure:** Each subsystem has its own `requirements.txt` (12 found total), no `pyproject.toml` or `setup.py`. Cannot `pip install -e .` the project. Freqtrade uses a single `setup.py` with extras.

4. **No `conftest.py` in project root** (only found in `.venv/` dependencies). No shared test fixtures.

**Architecture Score: 6.5/10** (Good layering in Alpha Engine and Crypto ML Edge; weakened by monorepo sprawl and duplicated systems)

---

## 2. TESTING COVERAGE

### Actual Test Inventory

| Location | Type | Test Count | Quality |
|----------|------|------------|---------|
| `crypto_ml_edge/tests/` | pytest unit tests | 6 files, ~260 test functions/fixtures | HIGH — covers features, validation, labeling, training, data, gainer |
| `tests/` (root) | Playwright E2E specs | 80+ `.spec.ts` files | HIGH for web/dashboard UI testing |
| `KIMI_RISEOFTHECLAW/tests/` | Playwright E2E | 4 spec files (dashboard, e2e, mode-switching) | MODERATE |
| `test_bot.py` (root) | Smoke test | 1 file, manual assertions | LOW — hardcoded API keys, no pytest |
| `test_data_validator.py` (root) | Unknown | 1 file | UNREVIEWED |
| `test_risk_quantification.py` (root) | Unknown | 1 file | UNREVIEWED |
| `test_model_health_agent.py` (root) | Unknown | 1 file | UNREVIEWED |
| `alpha_engine/tests/` | Empty | `__init__.py` only | ZERO coverage |

### Detailed Assessment

**crypto_ml_edge/tests/ — The Gold Standard in This Repo:**
- `test_validation.py` (58 test functions): Walk-forward chronology, purge gap verification, deflated Sharpe ratio, cost adjustment, lookahead detection, regime coverage — this is research-grade validation testing
- `test_features.py` (33 test functions): Feature count bounds (10-20), NaN guarantees post-warmup, stationarity contract (no raw prices), no-lookahead verification
- `test_labeler.py` (39 test functions): Label quality checks
- `test_trainer.py` (65 test functions): Training pipeline tests
- These tests enforce hard guarantees (FEAT-01 through FEAT-07) — a pattern borrowed from TensorTrade's contract testing

**alpha_engine/tests/ — Critical Gap:**
- Despite being the largest subsystem (60+ Python files, 100 strategies), the `tests/` directory contains only `__init__.py`
- No unit tests for any of the 100 strategies
- No tests for the validation engine (`walk_forward.py`, `purged_cv.py`, `monte_carlo.py`)
- No tests for the backtest engine
- This is the single largest quality gap vs. Freqtrade, which has 1,800+ tests

**Root-level test files are ad-hoc:**
- `test_bot.py` contains hardcoded API keys (CoinGecko, CryptoCompare) — a security anti-pattern
- No test runner configuration (`pytest.ini`, `setup.cfg`, `tox.ini`)

**Testing Score: 4/10** (crypto_ml_edge tests are excellent; alpha_engine has zero; no CI test runs detected in workflows; no pytest configuration)

---

## 3. CI/CD PIPELINE QUALITY

### Scale
- **106 GitHub Actions workflow files** totaling 13,845 lines of YAML
- This is extraordinary volume — Freqtrade has ~15 workflows

### Workflow Categories (Actual Findings)

| Category | Count | Examples |
|----------|-------|---------|
| Live scanning/trading | 25+ | `alpha-engine-live.yml` (every 15 min), `crypto-ml-edge.yml` (every 30 min), `ml-battleground-a/b/c.yml` |
| Deployment | 15+ | `deploy-riseoftheclaw.yml`, `deploy-alpha-dashboard.yml`, `deploy-pages.yml` |
| Data refresh | 10+ | `daily-price-refresh.yml`, `daily-stock-refresh.yml`, `daily-picks-snapshot.yml` |
| Backtesting | 5+ | `backtest-and-deploy.yml`, `riseoftheclaw-weekly-backtest.yml` |
| Monitoring | 5+ | `statistical_validation.yml`, `signal_tracking.yml`, `forward-test-daily.yml` |
| Non-trading (web) | 20+ | `scrape-events.yml`, `fetch-movies.yml`, `mirror-site.yml` |

### Strengths

1. **Autonomous operation:** The Alpha Engine runs every 15 minutes unattended — validates open picks, generates new signals, auto-tweaks parameters, and commits results. This is a production-grade pattern.

2. **Concurrency controls:** `ml-battleground-a.yml` uses `concurrency: { group: superpowers-a, cancel-in-progress: false }` — prevents overlapping runs.

3. **Retry logic on push:** Workflows use retry loops with `git pull --rebase` and backoff:
   ```yaml
   for i in 1 2 3; do
     git pull --rebase origin main && git push origin main && break
     sleep ${i}0
   done
   ```

4. **Multiple run modes:** Alpha Engine workflow supports `full-cycle`, `validate-only`, `generate-only`, `report`, and `train-ml` via `workflow_dispatch` inputs.

5. **Timeout guards:** Most workflows set `timeout-minutes: 10-15`.

### Weaknesses

1. **No test-gate workflows:** None of the 106 workflows run `pytest` as a quality gate before deploying. Freqtrade runs tests on every PR and blocks merge on failure.

2. **No PR-based workflow triggers:** All workflows trigger on `schedule` or `push`. No `pull_request` triggers for code review enforcement.

3. **Inline dependency installation:** `alpha-engine-live.yml` uses `pip install yfinance pandas numpy scikit-learn joblib requests` inline rather than `pip install -r requirements.txt`. This creates version drift between local and CI.

4. **Workflow sprawl:** 106 workflows is unmanageable. Many could be consolidated with reusable workflow templates (`workflow_call`).

5. **No caching strategy:** Only `crypto-ml-edge.yml` uses `cache: 'pip'`. Most workflows reinstall from scratch every run.

**CI/CD Score: 6/10** (Impressive autonomous operation and scale; severely lacking test gates, PR enforcement, and workflow consolidation)

---

## 4. DOCUMENTATION QUALITY

### README/Documentation

| File | Quality | Notes |
|------|---------|-------|
| `alpha_engine/README.md` | **HIGH** | Full architecture diagram, module descriptions, strategy listing, data layer documentation |
| `crypto_ml_edge/AUDIT.md` | **HIGH** | Brutally honest self-audit: "No existing ML model has demonstrated genuine out-of-sample edge." Includes root cause analysis with specific numbers |
| `KIMI_RISEOFTHECLAW/README.md` | MODERATE | Exists but not deeply reviewed |
| Root `README.md` | Not found for trading systems | The root appears to be a web project (findtorontoevents.ca) |
| 50+ root `.md` files | EXCESSIVE | Research reports, plans, summaries — useful knowledge but creates noise |

### Docstrings

**Alpha Engine (connors_rsi2.py) — Exemplary:**
- 42-line module docstring with academic citations (Connors & Alvarez 2008, Davydov et al. 2016, AQR)
- Explains WHY retail can exploit this edge (institutional constraints)
- Full strategy rules with entry/exit conditions
- Function-level type hints: `def rsi(close: pd.Series, period: int = 14) -> pd.Series`

**crypto_ml_edge/config.py — Research-backed comments:**
- Each configuration constant has a research justification
- "Research says: 5-10 liquid pairs, 1h+4h timeframes, 10-20 features"

**model_health_agent.py — Proper typing:**
- Uses `from typing import Dict, List, Optional, Tuple, Any, Callable`
- Dataclasses with type annotations
- Optional imports with graceful fallbacks (`PANDAS_AVAILABLE`, `SCIPY_AVAILABLE`, `SKLEARN_AVAILABLE`)

### Type Hints Coverage

Across the alpha_engine alone, **421 type-annotated function signatures** were found across 69 files. This is significantly above average for open-source trading projects. However, no `mypy` or `pyright` configuration exists to enforce type correctness.

**Documentation Score: 7/10** (Excellent docstrings and research citations in key modules; weakened by root-level document sprawl and no enforced type checking)

---

## 5. ERROR HANDLING PATTERNS

### Findings

- **613 try/except blocks** across 60 files in `alpha_engine/` alone
- `production_scanner.py` wraps every external API call in individual try/except with fallback to `None`
- `model_health_agent.py` uses optional import pattern with boolean flags (`PANDAS_AVAILABLE`, `SCIPY_AVAILABLE`)
- `crypto_ml_edge/` scanner uses `continue-on-error: true` in CI for non-critical steps

### Strengths
- Defensive programming is pervasive — API failures don't crash the scanner
- JSON sanitization: `_sanitize_for_json()` recursively replaces `NaN`/`Infinity` before `json.dump`

### Weaknesses
- Many bare `except Exception` blocks that swallow errors silently
- No custom exception hierarchy (Freqtrade defines `OperationalException`, `DependencyException`, `InvalidOrderException`, etc.)
- No structured error reporting (no Sentry, no error aggregation)

**Error Handling Score: 5.5/10** (Defensive but not structured)

---

## 6. DEPENDENCY MANAGEMENT

### Findings

- **12 separate `requirements.txt` files** across subsystems
- Root `requirements.txt`: Pinned versions (`pandas==2.1.4`, `numpy==1.26.2`)
- `alpha_engine/requirements.txt`: Minimum version bounds (`numpy>=1.24.0`, `pandas>=2.0.0`)
- `ml_battleground/requirements.txt`: Minimum version bounds with heavy ML deps (`torch>=2.1.0`)
- **Inconsistent pinning strategy:** Root pins exact, sub-packages use minimum bounds
- **No lock file** (`pip freeze > requirements.lock` or `poetry.lock`)
- **No `pyproject.toml`** — the modern Python standard
- **No virtual environment enforcement** (no `.python-version`, no `Pipfile`)

**Dependency Management Score: 3/10** (Fragmented, inconsistent, no lockfile)

---

## 7. MONITORING, LOGGING & ALERTING

### Logging
- **1,955 logging-related statements** across 118 Python files (excluding `.venv/`)
- Uses standard `logging` module with `getLogger(__name__)` pattern
- Dedicated log files: `data_validator.log`, `l2_orderbook.log`, `model_health_agent.log`, `onchain_metrics.log`, `probabilistic_sharpe.log`, `risk_quantification.log`

### Monitoring Agents (Actual)
| Agent | File | Purpose |
|-------|------|---------|
| Model Health Agent | `model_health_agent.py` | Drift detection, retraining triggers, model versioning |
| Data Validator | `data_validator_agent.py` | Data quality monitoring |
| Risk Quantification | `risk_quantification_agent.py` | Risk metric tracking |
| Statistical Validator | `statistical_validator.py` | Statistical significance testing |
| L2 Orderbook Agent | `l2_orderbook_agent.py` | Order book microstructure monitoring |
| Signal Tracker | `signal_tracker.py` | TP/SL validation against real prices |

### Alerting
- Discord webhook integration in multiple workflows (`DISCORD_WEBHOOK_URL` secret)
- `crypto_ml_edge/discord_notify.py` — dedicated notification module
- `ml_battleground/shared/discord_notify.py` — shared notification module

### Persistence
- SQLite databases: `model_health.db`, `crypto_data.db`, KIMI's `kimi_trading.db`, `signal_tracker.db`
- JSON state files for pick tracking, strategy performance, signal history

### Weaknesses
- No centralized observability (no Prometheus/Grafana, no structured log aggregation)
- No health check endpoints
- No uptime monitoring for the autonomous scanners
- Model Health Agent exists but doesn't appear to be wired into CI workflows

**Monitoring Score: 6/10** (Multiple agents exist with Discord alerting; lacks centralized observability)

---

## 8. COMPARISON TO BEST-IN-CLASS OPEN SOURCE

### vs. Freqtrade (25k+ stars)

| Dimension | Freqtrade | This Codebase | Gap |
|-----------|-----------|---------------|-----|
| Project structure | Clean package (`freqtrade/`) | Monorepo sprawl with 6 sub-systems | LARGE |
| Strategy abstraction | `IStrategy` base with `populate_indicators`, `populate_entry_trend`, `populate_exit_trend` | `StrategyConfig`/`Signal` dataclasses in `strategies/base.py` | MODERATE (this project's base is solid but unused by most strategies) |
| Testing | 1,800+ tests, 95%+ coverage, CI-gated | ~260 tests in crypto_ml_edge, 0 in alpha_engine, no CI gate | CRITICAL |
| CI/CD | ~15 focused workflows with test gates | 106 workflows, no test gates | LARGE |
| Dependency mgmt | `setup.py` with extras, pinned in CI | 12 scattered `requirements.txt` | LARGE |
| Documentation | Comprehensive docs site (mkdocs) | Good docstrings, no docs site | MODERATE |
| Backtesting | Vectorized + event-driven, integrated | Multiple engines not unified | MODERATE |
| Exchange support | 30+ via CCXT | Binance + yfinance only | N/A (different scope) |

### vs. TensorTrade (4k+ stars)

| Dimension | TensorTrade | This Codebase | Gap |
|-----------|-------------|---------------|-----|
| ML integration | RL environments (gym-like) | LightGBM/XGBoost classifiers + heuristic rankers | DIFFERENT APPROACH |
| Modularity | Strict observer pattern, component composition | Function-based strategies with shared indicators | MODERATE |
| Research rigor | Academic but unproven in production | Brutally honest self-audit, proven RSI-2 edge | THIS PROJECT AHEAD |
| Walk-forward validation | Not built-in | Full purged walk-forward with embargo (`crypto_ml_edge/validation.py`) | THIS PROJECT AHEAD |
| Deflated Sharpe Ratio | Not implemented | Implemented and tested (`deflated_sharpe_ratio()`) | THIS PROJECT AHEAD |

---

## Actionable Recommendations (Priority Order)

### P0 — Critical (Do This Week)
1. **Add pytest to CI:** Create a single workflow that runs `pytest crypto_ml_edge/tests/ -v` on every push. This is the single highest-ROI improvement.
2. **Write alpha_engine tests:** Port the crypto_ml_edge test patterns to alpha_engine. Start with `test_connors_rsi2.py` and `test_forward_validator.py`.
3. **Remove hardcoded API keys** from `test_bot.py` (line 9-10). Use environment variables.

### P1 — High Priority (Do This Month)
4. **Consolidate requirements:** Create a single `pyproject.toml` with optional extras (`[alpha]`, `[ml-edge]`, `[battleground]`).
5. **Create `conftest.py`** with shared fixtures (synthetic OHLCV data, mock API responses).
6. **Consolidate workflows:** Use reusable workflows (`workflow_call`) to reduce from 106 to ~30.
7. **Add PR-trigger workflows** with test gates to prevent regressions.

### P2 — Medium Priority (Do This Quarter)
8. **Add `mypy` or `pyright`** configuration to enforce the existing type hints.
9. **Create a unified backtest CLI:** `python -m alpha_engine backtest --strategy connors_rsi2 --symbol SPY`
10. **Add structured logging** (JSON format) for log aggregation.
11. **Implement custom exception hierarchy** (replace bare `except Exception`).

### P3 — Nice to Have
12. **Add pre-commit hooks** (black, isort, flake8/ruff).
13. **Create docs site** (mkdocs-material) from existing README.md files.
14. **Adopt TensorTrade's observer pattern** for strategy composition.

---

## Overall Assessment

| Category | Score | Weight | Weighted |
|----------|-------|--------|----------|
| Architecture & Modularity | 6.5/10 | 20% | 1.30 |
| Testing Coverage | 4.0/10 | 25% | 1.00 |
| CI/CD Pipeline | 6.0/10 | 15% | 0.90 |
| Documentation | 7.0/10 | 10% | 0.70 |
| Error Handling | 5.5/10 | 10% | 0.55 |
| Dependency Management | 3.0/10 | 10% | 0.30 |
| Monitoring & Alerting | 6.0/10 | 10% | 0.60 |
| **TOTAL** | | **100%** | **5.35/10** |

**Verdict:** This codebase is **above average** for a privately-developed crypto ML project but **below Freqtrade-grade** for production open-source standards. The crypto_ml_edge module demonstrates that the team *knows how to* write rigorous tests and validation — the issue is that this discipline hasn't been applied consistently across all subsystems, especially the alpha_engine which is the largest and most actively used component.

The most impressive aspects are:
- The brutal self-honesty in `AUDIT.md` (acknowledging Sharpe -2.799 failure)
- Research-backed parameter constraints in crypto_ml_edge
- The 421 type-annotated functions across alpha_engine
- Working autonomous scanning pipeline running every 15 minutes

The most concerning gaps are:
- Zero tests for the 100-strategy alpha_engine
- No test gates in any of the 106 CI workflows
- Fragmented dependency management across 12 requirements files
- Security anti-patterns (hardcoded API keys in test files)

## References
- Freqtrade: github.com/freqtrade/freqtrade (architecture comparison baseline)
- TensorTrade: github.com/tensortrade-ai/tensortrade (RL approach comparison)
- Connors & Alvarez (2008): "Short Term Trading Strategies That Work" (cited in codebase)
- Davydov et al. (2016): RSI-2 replication study (cited in codebase)
- Bailey & Lopez de Prado (2014): "The Deflated Sharpe Ratio" (implemented in crypto_ml_edge)

---
*Researcher ID: 022* | *Status: Complete* | *Last Updated: 2026-02-24*
