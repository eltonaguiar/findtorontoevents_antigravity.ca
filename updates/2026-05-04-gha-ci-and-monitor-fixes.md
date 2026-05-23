# GitHub Actions: CI regressions + monitor workflow (2026-05-04)

## Symptoms

1. **CI Tests** on `origin/main`: `tests/test_jpy_cross_buy_block.py` failed after `USDJPY=X` was added to `JPY_CROSS_PAIRS` in `audit_trail/quality_gates.py` while tests still require **excluding** USDJPY per Phase 2-C panel (`reports/HFPA_PHASE-2-findings-FOREX-2026-04-29.md`).
2. **Continuous Improvement Monitor** (`continuous-improvement-monitor.yml`): `ModuleNotFoundError: No module named 'numpy'` because only `requests` was installed before `python -m alpha_engine.continuous_improvement_monitor` (`alpha_engine/__init__.py` imports `decay_tracker` → `numpy`).
3. **2-hour challenge** workflow: full-history checkout (`fetch-depth: 0`) + bare `git push` caused slow clones and brittle pushes on churny `main` (see `DIAGNOSE.MD`).

## Changes

- **`alpha_engine/__init__.py`**: Lazy-export `DecayTracker` / `StrategyStatus` via `__getattr__` so `python -m alpha_engine.continuous_improvement_monitor` does not transitively require numpy at package import time (belt-and-suspenders with dependency install below).
- **`audit_trail/quality_gates.py`**: Workspace `main` already keeps `JPY_CROSS_PAIRS` **without** `USDJPY=X`, matching gates + tests; **landing that on GitHub `main`** (or resolving merge vs remote) restores green CI Tests.
- **`.github/workflows/continuous-improvement-monitor.yml`**: Install `numpy` + `requests` via `python -m pip`; pass `TOKEN_FOR_PUSH` into `safe_commit_push.sh`.
- **`.github/workflows/2hour_challenge.yml`**: `permissions: contents: write`, shallow checkout (`fetch-depth: 1`), checkout token `GH_PAT || github.token`, `TOKEN_FOR_PUSH` + `bash .github/scripts/safe_push.sh`, align actions to `@v6`, append `[skip ci]` on results commit message.
- **`.github/workflows/real_2hour_challenge.yml`**: `TOKEN_FOR_PUSH` on Save Results step for `safe_push.sh`.

## Verification

- `python -m pytest tests/test_jpy_cross_buy_block.py -q` — 15 passed (local workspace state).
- Re-run failing workflows after push: CI Tests on `push`, Continuous Improvement Monitor on `workflow_dispatch`.
