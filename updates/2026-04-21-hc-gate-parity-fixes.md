# HC Gate Parity Fixes — 2026-04-21

## Problem
During validation of the `fix/hc-gate-config-parity-2026-04-22` branch, systematic parity audit found three mismatches between `config/hc_gate_params.json` (single source of truth) and the JS/Python mirrors (`audit_dashboard/hc_filter.js`, `tools/dashboard_hc_rules.py`).

## Root Cause
Commit `b2dfe89964` updated JSON thresholds but missed two embedded-default syncs and one fallback value in JS/Python logic.

## Fixes Applied

### 1. `scoreFloorEquity` mismatch
- **JSON**: 45
- **JS embedded + fallback**: 50 → **fixed to 45**
- **PY embedded + fallback**: 50 → **fixed to 45**

### 2. `trustScoreMinCrypto` fallback mismatch
- **JSON**: 4
- **JS fallback**: `params.trustScoreMinCrypto || 6` → **fixed to `|| 4`**
- **PY fallback**: `params.get("trustScoreMinCrypto", 6)` → **fixed to `default=4`**

### 3. `independentGroupsMin` fallback mismatch (SECURITY)
- **JSON**: 3
- **JS fallback**: `Number(params.independentGroupsMin) || 0` → **fixed to `|| 3`**
- **PY fallback**: `params.get("independentGroupsMin", 0)` → **fixed to `default=3`**
- **Impact**: Missing key previously bypassed the independent-consensus gate entirely. Now it correctly defaults to 3.

## Validation
- `python -m py_compile tools/dashboard_hc_rules.py` → PASS
- `node --check audit_dashboard/hc_filter.js` → PASS
- `python tmp_check_parity.py` → no critical mismatches remain

## Full-Dataset HC Performance (post-fix)
Validating against 3,500 closed picks confirms HC filter is institutionally effective:

| Asset    | Baseline WR | HC WR  | HC Mean | HC PF |
|----------|------------|--------|---------|-------|
| CRYPTO   | 32.6%      | 54.6%  | +0.57%  | 1.86  |
| EQUITY   | 52.4%      | 68.2%  | +1.41%  | 2.82  |
| ETF      | 51.4%      | 62.5%  | +0.85%  | 2.72  |
| FOREX    | 47.2%      | 0      | —       | —     |
| COMMODITY| 43.3%      | 0      | —       | —     |
| **ALL**  | **40.1%**  | **61.1%** | **+0.97%** | **2.37** |

Note: A misleading "last 200 crypto" baseline (80.5% WR) was caused by `claude_gainer_st`'s one-day hot streak (86 picks at 98.8% WR). HC correctly excludes this system (23.8% long-term WR, -463% cum PnL). The full dataset is the authoritative benchmark.
