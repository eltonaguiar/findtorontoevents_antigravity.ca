# CI Tests + Audit Drift Telemetry Fix — 2026-05-23

## What Was Broken

### 1. CI Tests — pytest.skip Collection Error (3 consecutive failures)
- **Workflow:** CI Tests
- **Run IDs:** 26330204486, 26330228256, 26330280855
- **Error:** `Using pytest.skip outside of a test will skip the entire module.`
- **Root Cause:** Two test files called `pytest.skip()` at module level (inside `_load_payload()`) without `allow_module_level=True`. When `dashboard_data.json` is absent (expected on CI for certain workflow triggers), the skip call crashes the test collection phase instead of gracefully skipping the module.

**Affected files:**
- `tests/test_audit_metric_invariants.py` — `_load_payload()` lines 48-59
- `tests/test_dashboard_payload_contract.py` — `_load_payload()` lines 77-90

### 2. Audit Drift Telemetry — FileNotFoundError
- **Workflow:** Audit Drift Telemetry
- **Run ID:** 26330204496
- **Error:** `FileNotFoundError: [Errno 2] No such file or directory: 'audit_dashboard/data/dashboard_data.json'`
- **Root Cause:** The drift telemetry workflow runs on a 6-hour schedule and on push to `audit_dashboard/**`. However, `dashboard_data.json` is a generated artifact produced by the `audit-dashboard.yml` pipeline. When the drift job runs before the dashboard pipeline completes (or on a fresh checkout), the input file doesn't exist and the script crashes.

## What Was Changed

### Fix 1: Add `allow_module_level=True` to module-level pytest.skip calls
- **File:** `tests/test_audit_metric_invariants.py`
  - Added `allow_module_level=True` to both `pytest.skip()` calls in `_load_payload()`
- **File:** `tests/test_dashboard_payload_contract.py`
  - Added `allow_module_level=True` to both `pytest.skip()` calls in `_load_payload()`

This allows pytest to gracefully skip the entire test module when the payload file is missing, instead of raising a collection error.

### Fix 2: Graceful skip when dashboard_data.json is missing
- **File:** `tools/drift/build_backtest_forward_drift.py`
  - Added existence check in `main()` before calling `build_report()`: if input file is missing, prints a skip message and returns 0 (success) instead of crashing
  - Added defensive `FileNotFoundError` with clear message in `build_report()` for direct callers

This makes the drift telemetry workflow idempotent — it will succeed (with a skip message) when the dashboard pipeline hasn't yet produced data, and run normally once the data is available.

## How It Was Verified
- All three modified files pass `py_compile.compile(doraise=True)` syntax check
- No production logic changed — only error handling paths modified

## Impact
- CI Tests: Should now pass collection phase (either run tests normally or skip gracefully)
- Audit Drift Telemetry: Should no longer fail when `dashboard_data.json` is absent; will produce output once the audit-dashboard pipeline generates the input file
