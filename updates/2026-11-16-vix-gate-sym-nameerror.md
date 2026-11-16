# VIX gates silently failed open; CI Tests red on any high-VIX day

## What was broken

Two independent defects, both proven from CI run 43896182188 and local runs on 2026-11-16 (VIX 23.96).

1. **`_sym` was never bound in `passes_smart_gate`.** `audit_trail/quality_gates.py` uses `_sym` in M-045 (EQUITY VIX), M-046 (COMMODITY source cap) and M-047 (EQUITY shadow floor). Each block wraps itself in `try/except Exception: pass`, so the `NameError` was swallowed and the gate **failed open even when explicitly enabled**. M-045 only worked by accident when the legacy VIX sidecar rejected first.
   - Proven with a `sys.settrace` capture: `NameError("name '_sym' is not defined")` raised at the M-045 log line, caught by the block's own except.
2. **Tests were not hermetic against live VIX.** The per-class hard VIX gates (2026-05-28) call `yfinance ^VIX` and reject EQUITY when VIX > 22 / ETF > 25. `tests/conftest.py` neutralized a dozen other network/live gates but not these. At VIX 23.96 every generic EQUITY fixture was rejected with `_hf_quality_gate_reason=equity_vix_gate_high_vix`, so unrelated gate tests went red on main for 6 consecutive pushes.

## What changed

- edited `audit_trail/quality_gates.py`: bind `_sym` once next to `_ac` in `passes_smart_gate`.
- edited `tests/conftest.py`: default `EQUITY_VIX_GATE_ENABLED=0`, `ETF_VIX_GATE_ENABLED=0`, `VIX_REGIME_GATE_ENABLED=0`, `YC_REGIME_GATE_ENABLED=0` via `setdefault` (same pattern as the existing entries). `VIX_REGIME_ACTIVE_GATE_ENABLED` is deliberately left ON so the M-045 check inside it stays reachable.
- added `updates/2026-11-16-vix-gate-sym-nameerror.md` (this file).

## Impact

- Production defaults unchanged: `EQUITY_VIX_FILTER`, `COMMODITY_SOURCE_CAP`, `EQUITY_SHADOW_FLOOR_50` (set to `1` only in `audit-dashboard.yml` for M-047, logging-only), `COMMODITY_CTF_CAP` are all OFF unless an operator enables them. Binding `_sym` only makes them work when enabled.
- No pick, sizing, database, or emitter change.
- Tests only: the four `setdefault` lines.

## Verification

- Full suite on this branch: **65 failed, 6567 passed**.
- Full suite on clean `origin/main`: **119 failed, 6513 passed**.
- Diff: **54 fixed, 0 new failures**.
- Targeted: `tests/test_wf_verdict_null_block.py tests/test_wf_verdict_failing_gate.py tests/test_phase1_active_gates.py tests/test_m098_etf_vix_gate.py tests/test_vix_regime_gate.py tests/test_vix_yc_combined_gate.py tests/test_quality_gates.py` → **220 passed**.

## Follow-up

`tests/test_quality_gates.py::TestM045EquityVixFilter` is still in the CI known-drift quarantine list although it now passes. Removing that entry is a separate, low-risk cleanup.
