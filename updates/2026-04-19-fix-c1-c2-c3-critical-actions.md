# Critical Fixes: C1 (Corrupted Payload), C2 (pymysql), C3 (ETF DataFrame)

**Date:** 2026-04-19  
**Source:** GitHub Actions audit of last 50 runs

---

## C1: Corrupted `dashboard_payload.json`

### What was broken
`audit_trail/data/dashboard_payload.json` (~25 MB, ~918K lines) had corrupted
`agreeing_systems` arrays where entries were truncated mid-object, leaving the
array unclosed. This caused `json.loads()` to fail with "Expecting ','
delimiter" at line 742,843.

**Impact:** Feed Health Check ❌, Low-Score Winner Tracker ❌,
Dashboard Pick Trader running on stale data.

### What was changed
1. **`tools/repair_dashboard_payload.py`** (new) — Line-based repair script
   that detects unclosed `agreeing_systems` arrays (via indentation analysis)
   and replaces corrupted entries with `[]`. Creates a timestamped `.bak`
   backup before modifying. Run with:
   ```
   python tools/repair_dashboard_payload.py
   ```
2. **`audit_trail/dashboard_payload_health.py`** — Wrapped `json.loads()` in
   `try/except JSONDecodeError` so the health check reports corruption instead
   of crashing.
3. **`audit_trail/dashboard_generator.py`** — Added post-write integrity check:
   reads back the written file and validates it parses as JSON. Logs
   `CRITICAL` if the file is corrupted after write (concurrent write / disk
   issue detection).

### Verification
- Run `python tools/repair_dashboard_payload.py` and confirm "SUCCESS".
- Run `python -c "import json; json.load(open('audit_trail/data/dashboard_payload.json'))"` — should succeed.
- Feed Health Check and Low-Score Winner Tracker workflows should pass on next run.

---

## C2: Missing `pymysql` in ML Battleground CI

### What was broken
`ml_battleground/audit_push.py` imports from `audit_trail` which eventually
calls into MySQL audit sync code requiring `pymysql`. The package was not
installed in the CI environment, causing MySQL audit writes to fail after 3
retries every run.

**Impact:** ML Battleground System F audit trail broken (picks still pushed,
but MySQL audit records missing).

### What was changed
1. **`ml_battleground/requirements.txt`** — Added `pymysql>=1.1.0`.
2. **`.github/workflows/ml-battleground-f.yml`** — Added `pip install -q pymysql`
   before the `audit_push.py` step.

### Verification
- Trigger ML Battleground System F workflow and confirm the audit push step
  completes without pymysql import errors.

---

## C3: ETF Agent DataFrame Bug

### What was broken
`alpha_engine/etf_strategies.py` line 282:
```python
spy_df = data.get("SPY") or data.get("QQQ")
```
Python's `or` operator evaluates the truthiness of the left operand. When
`data.get("SPY")` returns a pandas DataFrame, calling `bool()` on it raises:
> ValueError: The truth value of a DataFrame is ambiguous.

**Impact:** `etf_risk_parity_rotation` strategy produced 0 quality picks.

### What was changed
**`alpha_engine/etf_strategies.py`** — Replaced `or` with explicit `None` check:
```python
spy_df = data.get("SPY")
if spy_df is None:
    spy_df = data.get("QQQ")
```

### Verification
- `python -c "import py_compile; py_compile.compile('alpha_engine/etf_strategies.py', doraise=True)"`
- ETF Agent workflow should produce picks on next run.
