# 2026-04-28 Integration Batch Execution Log

## Scope

This log tracks the "integrated + tested fully" pass for the active Goal #1 queue around PRs `#462-#472`.

## What Landed

- Confirmed merged on GitHub: `#462`, `#463`, `#464`, `#465`, `#467`, `#468`, `#469`, `#470`, `#471`.
- Merged during this pass: `#472` (orphan emitter wiring).
- Fixed and merged during this pass: `#466` (QuantStats/PyPortfolioOpt sidecar integration).

## PR #466 CI Failure Root Cause + Fix

### Root cause

- CI failed in `tests/test_quantstats_tearsheets.py::test_write_tearsheet_empty_returns_writes_placeholder`.
- `tools/quantstats_tearsheets.py::write_tearsheet()` imported `quantstats` before checking `returns.empty`.
- In CI environments without `quantstats`, this raised `ImportError` even for empty-return placeholder flow.

### Fix applied

- Moved `qs = _load_quantstats()` to execute only after the `returns.empty` early-return branch.
- This preserves offline/optional behavior while keeping real render paths unchanged.

### Verification evidence

- In PR worktree (`feat/hedge-fund-integrations-2026-04-28`):
  - `python -m pytest tests/test_quantstats_tearsheets.py tests/test_pypfopt_allocator.py -q`
  - Result: `27 passed, 1 skipped`.
- GitHub checks on `#466` rerun and passed:
  - `scan` PASS
  - `test (3.11)` PASS
  - `test (3.12)` PASS

## Consolidated Verification Pass (fresh `origin/main`)

Created clean verification worktree from latest `origin/main` and ran:

- `python -m pytest tests/test_outcome_resolver_v2.py tests/test_hf_quality_gate_wire.py tests/test_quantstats_tearsheets.py tests/test_pypfopt_allocator.py -q`
  - Result: `62 passed, 1 skipped`
- `py_compile` check across integrated modules:
  - `alpha_engine/outcome_resolver.py`
  - `audit_trail/quality_gates.py`
  - `audit_trail/dashboard_generator.py`
  - `alpha_engine/catalyst_filter.py`
  - `alpha_engine/drift_aware_scoring.py`
  - `alpha_engine/anti_overfit_validator.py`
  - `alpha_engine/hedge_fund_quality_gate.py`
  - `tools/quantstats_tearsheets.py`
  - `tools/pypfopt_allocator.py`
  - Result: all compiled successfully.

## Per-Asset Snapshot (current dashboard ledger)

Computed from `audit_dashboard/data/dashboard_data.json` (`picks.recent_closed`) at execution time:

- `BOND`: n=17, WR=47.06%, PF=1.601
- `COMMODITY`: n=624, WR=42.47%, PF=0.896
- `CRYPTO`: n=1588, WR=42.25%, PF=1.131
- `EQUITY`: n=391, WR=51.41%, PF=1.359
- `ETF`: n=83, WR=54.22%, PF=1.220
- `FOREX`: n=792, WR=50.76%, PF=1.556
- `FUTURES`: n=2, WR=100.00%, PF=999.000 (sample too small)
- `UNKNOWN`: n=3, WR=100.00%, PF=999.000 (sample too small)

## Remaining Execution Backlog

1. PEAD wire-up PR.
2. Bond credit-spread strategy PR (LQD-HYG).
3. DSR>=0 trust-tier promotion gate PR.
4. Bond/ETF/Futures elite-score floor relaxation PR.
5. Vol-targeting 30d DD hard-halt PR.
6. Orphan wiring PRs: `hurst_regime`, `hyrotrader_risk_sizer`.
7. N/PF/WR freshness automation in updates pipeline.

