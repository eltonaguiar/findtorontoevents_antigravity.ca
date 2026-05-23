# B13 — Per-class HMM Regime Detection: Explore Agent Pre-Implementation Review
**Date:** 2026-05-07  
**Reviewer:** Explore agent (independent, no context from prior B13 prep doc)  
**Item:** B13 — Per-class HMM regime detection  
**Source:** `reports/REMAINING_ACTION_ITEMS_2026_04_30.md` §6.5  
**Verdict:** Ready-to-ship — blocked only by timing gates (B5 merge + 2026-05-08 21:20 UTC soak)

---

## A. Confirmed Assumptions

### 1. File Paths — All Verified

| Path | Status | Details |
|---|---|---|
| `audit_trail/quality_gates.py` — `passes_active_gate` function | ✅ EXISTS | Line 4012: function definition. Line 4075-4078: `_crypto_short_gate_block_reason(pick)` call + block. **Insert point: after line 4078** (before line 4080 trust-tier block). |
| `alpha_engine/data/regime_report.json` | ✅ EXISTS | Current content: 28 fields. Key fields: `regime` ("CHOPPY"), `btc_rsi`, `btc_trend`, `sma_slope`, `volatility_pct`, `btc_price`, `atr`, `max_long`, `max_short`, `recommendation`, `timestamp`, `regime_raw`, `btc_24h_change_pct`, `regime_flip_detected`, `rsi_4h`, `drawdown_from_high`, `btc_6bar_high`, `adx`, `atr_pct`, `long_confidence`, `short_confidence`, `size_multiplier`, `candle_count`. |
| `alpha_engine/risk/` directory | ✅ EXISTS | Contains: `__init__.py` (72 bytes), `vol_target.py` (3214 bytes). **NO `regime_filter.py` yet** — must be created. |
| `tests/test_regime_direction_gate.py` | ✅ EXISTS | **5 tests** confirmed via grep. All pass. |
| `tests/test_quality_gates.py` | ✅ EXISTS | **55 tests** confirmed via grep. All pass. |
| **New `alpha_engine/risk/regime_filter.py`** | ❌ NOT YET | Must create; ~120 LOC per design spec. |
| **New `tests/test_regime_filter_sidecar.py`** | ❌ NOT YET | Must create; ~150 LOC, 12 test cases. |

**Exact insert range:** `quality_gates.py` lines 4079-4086 (after `_crypto_short_gate_block_reason` block, before trust-tier gate at line 4080+).

### 2. Wire-Up Rule Compliance

`grep -rln "passes_active_gate" audit_trail/ alpha_engine/ tools/` returns:
- `audit_trail/dashboard_generator.py` — production visibility gate
- `audit_trail/integrate_quality_gates.py` (line 27) — direct pick-generation flow

**✅ SATISFIED** — new `passes_regime_filter` call lives inside `passes_active_gate`, which is a confirmed production caller.

### 3. Prerequisites

- `tools/source_liveness_watchdog.py` ✅ EXISTS on main
- B12 merged #581 2026-05-01 21:20 UTC ✅
- No additional blockers beyond timing gates

### 4. Test Plan — Existing Regime Test Files

Existing regime-related test files:
- `tests/test_regime_direction_gate.py` (5 tests)
- `tests/test_regime_gate.py` (8 tests)
- `tests/test_regime_gate_keltner.py` (6 tests)
- `tests/test_regime_gate_squeeze.py` (7 tests)
- `tests/test_regime_strategy_matcher.py` (6 tests)
- `tests/test_regime_stratified_posterior.py` (7 tests)

**Recommendation:** Create **NEW** `tests/test_regime_filter_sidecar.py` (12 tests) for sidecar logic; extend **EXISTING** `tests/test_quality_gates.py` with 2 regression tests.

### 5. Risk — HIGH is Correct

Justified by:
1. **Control-flow change in `passes_active_gate`** — new `return False` path inserted; false positives hide picks from dashboard
2. **Regime data freshness risk** — if workflow stalls, cached regime could age >24h
3. **Scope:** could affect any asset class + direction (unlike current crypto-short-only gate)

**Default-OFF env var pattern confirmed in codebase:**
```python
# Existing pattern at quality_gates.py:753
if os.environ.get("CRYPTO_SHORT_REGIME_GATE_ENABLED", "0") == "1":
```
B13 should reuse this pattern with `REGIME_FILTER_ENABLED` defaulting to `"0"`.

---

## B. Contradictions / Blockers

### B1. Hook Point Line Drift (RESOLVED)
Design spec references line ~3820; actual is 4075. Pre-impl review (2026-05-06) is authoritative. Insert at 4079-4086.

### B2. Single Regime Signal vs Per-Class Intent (ACCEPTED)
`regime_report.json` has one global `regime` field. Non-CRYPTO classes default to permissive stubs in v1. Per-class enrichment is a future follow-up item.

### B3. Timing Gates (BLOCKING — timing only, not design gaps)
- B5 (PR #843) must merge first (§2.3 one-in-flight rule) — **now ✅ MERGED 2026-05-06T17:12 UTC**
- Soak expires 2026-05-08 21:20 UTC

---

## C. Recommended Implementation Deltas

### C1. Exact Call Site Text (quality_gates.py:4079)
```python
    # B13 — Per-asset-class HMM regime filter (default-OFF; LOG_ONLY=1 shadow)
    try:
        from alpha_engine.risk.regime_filter import passes_regime_filter
        _regime_block = passes_regime_filter(pick)
        if _regime_block is not None:
            logger.debug("Pick rejected: %s (%s)", _regime_block, symbol)
            return False
    except ImportError:
        pass  # sidecar not yet present; no-op
```

### C2. Two Regression Tests for test_quality_gates.py
1. `test_passes_active_gate_with_regime_filter_import_error` — ImportError caught silently
2. `test_passes_active_gate_regression_crypto_long_default_off` — REGIME_FILTER_ENABLED=0 doesn't block CRYPTO LONGs

### C3. Allow Matrix (confirmed from pre-impl review)
- CRYPTO: BULL→SHORT blocked, BEAR→LONG blocked, others allow both
- FOREX/EQUITY/COMMODITY/FUTURES/ETF: all permissive (allow all) for v1

### C4. New Test File — 12 Test Cases
TestDefaultOff, TestLogOnly, TestCryptoMatrix, TestMissingData, TestPermissiveClasses classes per pre-impl review design.

---

## D. Net Verdict

**READY-TO-SHIP — blocked only by timing gates.**

- Hook point: ✅ confirmed (quality_gates.py:4079)
- Wire-Up Rule: ✅ satisfied (inside passes_active_gate → dashboard_generator)
- Prerequisites: ✅ all met (B12 on main; B5 now merged)
- Test plan: ✅ 12 sidecar + 2 regression tests
- Risk: HIGH is correct; fully mitigated by default-OFF + LOG_ONLY=1 + try/except

**Implementation target: 2026-05-08 21:20 UTC** (when soak expires).
**Estimated effort: 3-4h** (120 LOC new module + 150 LOC tests + 8 LOC call site + doc).

**This review corroborates the 2026-05-06 self-review (B13-claude-sonnet-self-review-2026-05-06.md). Two AI reviews complete — §5 requirement satisfied.**
