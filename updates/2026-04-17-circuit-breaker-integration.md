# Circuit Breaker & Macro Overlay Integration Summary

**Date:** 2026-04-17  
**Author:** Kimi Code CLI  
**Scope:** Integrate macro data and circuit breakers into the production pick-generation pipeline.

---

## Files Modified / Created

| File | Action | Purpose |
|------|--------|---------|
| `alpha_engine/circuit_breaker_aggregator.py` | **Created** | Reads all three breaker state files and returns a single unified decision (`GREEN|YELLOW|RED|HALT`). |
| `alpha_engine/production_scanner.py` | **Modified** | Wires the aggregator, macro overlay, and macro risk-off gate into the scanner pipeline. |
| `updates/2026-04-17-circuit-breaker-integration.md` | **Created** | This document. |

---

## 1. New Module: `circuit_breaker_aggregator.py`

### What it does
- **Reads** three state files:
  * `alpha_engine/data/drawdown_circuit_breaker.json` (real-money drawdown monitor)
  * `alpha_engine/data/circuit_breaker_state.json` (portfolio-level risk)
  * `alpha_engine/data/macro_circuit_breaker.json` (macro data engine)
- **Maps** each file’s native level to a common vocabulary:
  * Drawdown `CIRCUIT_BREAKER_CRITICAL` → `HALT`
  * Drawdown `CIRCUIT_BREAKER_ACTIVE` → `RED`
  * Portfolio `GREEN/YELLOW/RED/HALT` → same
  * Macro `active=true` + catastrophic reason → `HALT`; otherwise maps `YELLOW/RED/HALT` directly; defaults active-but-unclassified to `RED`.
- **Ignores stale states** (>2 hours old) so a broken upstream feeder does not permanently lock the pipeline.
- **Returns** a single dict:
  ```python
  {
      "level": "GREEN|YELLOW|RED|HALT",
      "max_picks": int,
      "min_confidence": float,
      "reasons": [str],
      "details": {drawdown_level, portfolio_level, macro_level, ...},
  }
  ```
- Applies the **most restrictive** `max_picks` and `min_confidence` across all active breakers.

---

## 2. Modifications to `production_scanner.py`

### A. Imports (top of file)
Added two optional imports following the existing fail-safe pattern:

```python
# Macro overlay scoring
try:
    from macro_overlay_score import attach_macro_overlay
    _HAS_MACRO_OVERLAY = True
except ImportError:
    _HAS_MACRO_OVERLAY = False

# Unified circuit breaker aggregator
try:
    from circuit_breaker_aggregator import get_unified_breaker_state
    _HAS_CB_AGGREGATOR = True
except ImportError:
    _HAS_CB_AGGREGATOR = False
```

### B. `global` declaration moved to top of `main()`
Because `MAX_ACTIVE_PICKS` and `QUALITY_GATE_MIN_CONFIDENCE` are now mutated in two places inside `main()`, the `global` statement was moved to the function head (right after `start = time.time()`) to satisfy Python’s lexical rules.

### C. Insertion Point 1 — Pre-generation unified breaker check (line ~2705)
**Location:** Immediately after model calibration (`-0.`) and before the existing `risk_controls` pre-generation block (`-1.`).

**Behavior:**
1. Calls `get_unified_breaker_state()`.
2. Logs the unified level, `max_picks`, `min_confidence`, and every trigger reason.
3. If level is **`HALT`**:
   - Prints a clear abort message.
   - Writes an empty `premium_signals.json` so the dashboard still refreshes.
   - Exits `main()` early.
4. If level is **`RED`** or **`YELLOW`**:
   - Adjusts `MAX_ACTIVE_PICKS = min(current, aggregator_max_picks)`
   - Adjusts `QUALITY_GATE_MIN_CONFIDENCE = max(current, aggregator_min_confidence)`
   - `RED` additionally forces confidence floor to **≥ 0.85**.
   - `YELLOW` additionally forces confidence floor to **≥ 0.70**.

This ensures the **most restrictive** settings across all breakers are in effect before any pick generation happens.

### D. Insertion Point 2 — Macro overlay attachment (after `apply_quality_gates`, line ~3847)
**Location:** Right after the `[QUALITY GATES] Passed: X, Rejected: Y` log and before the Strategy Priority Tier System (`6f2.`).

**Behavior:**
```python
for pick in active:
    attach_macro_overlay(pick)
```
Each surviving pick is enriched with:
- `macro_score` (float, if snapshot data exists)
- `macro_overlay_source`
- `macro_overlay_as_of`

### E. Insertion Point 3 — Macro risk-off gate (immediately after overlay attachment)
**New function:** `apply_macro_risk_off_gate(picks) -> (kept, rejected)`

**Logic:**
- If `macro_score` is missing → pass through.
- If `macro_score >= -0.5` → pass through.
- If `macro_score < -0.5` (strong risk-off for the asset class):
  * `confidence >= 0.90` → **survive with 0.5× sizing reduction** (`sizing_multiplier *= 0.5`)
  * `confidence < 0.90` → **filtered out** and added to the audit rejection list.

This implements the requested gate without silently killing high-conviction picks.

### F. Rejection audit trail
The existing `all_rejections` collector near the end of `main()` was extended:

```python
if "macro_rejected" in locals(): all_rejections.extend(macro_rejected)
```

This guarantees macro risk-off rejections appear in `premium_signals.json` under `rejected_signals` for dashboard transparency.

---

## 3. Interaction with Existing Macro Gating

There is already a **macro pipeline gating** block (`3.0. MACRO GATING`) around line 2936 that adjusts `MAX_ACTIVE_PICKS` and `QUALITY_GATE_MIN_CONFIDENCE` based on the live `_macro_snapshot` (yield curve, Fed policy, macro risk score).

The new aggregator works **complementarily**:
- The aggregator reads the **discrete** `macro_circuit_breaker.json` (produced by the upcoming `macro_data_engine.py`).
- The existing macro gating reads the **continuous** `_macro_snapshot` directly from the macro pipeline.
- Both use `min()` for pick caps and `max()` for confidence floors, so whichever is more restrictive wins. No conflicts are introduced.

---

## 4. Testing Recommendations

1. **Unit test the aggregator**
   - Create temporary `drawdown_circuit_breaker.json`, `circuit_breaker_state.json`, and `macro_circuit_breaker.json` fixtures.
   - Assert that `get_unified_breaker_state()` returns the worst level.
   - Assert that stale files (>2h) are ignored.
   - Assert that catastrophic macro reasons map to `HALT` while non-catastrophic active macro maps to `RED`.

2. **Integration test in `production_scanner.py`**
   - Mock `get_unified_breaker_state()` to return `HALT` and verify `main()` exits early with empty `premium_signals.json`.
   - Mock `RED` and verify that `QUALITY_GATE_MIN_CONFIDENCE` is raised to ≥ 0.85.
   - Mock `YELLOW` and verify `MAX_ACTIVE_PICKS` is halved and confidence floor raised to ≥ 0.70.

3. **Macro overlay + risk-off gate test**
   - Create a pick with `macro_score = -0.6` and `confidence = 0.95` → assert it survives with `sizing_multiplier == 0.5`.
   - Create a pick with `macro_score = -0.6` and `confidence = 0.80` → assert it is rejected.
   - Create a pick with no `macro_score` → assert it passes through unchanged.

4. **End-to-end syntax / import smoke test**
   - `python -c "import py_compile; py_compile.compile('alpha_engine/production_scanner.py', doraise=True)"`
   - `python -c "from alpha_engine.circuit_breaker_aggregator import get_unified_breaker_state; print('import ok')"`

---

## 5. No Push to Main

Per instructions, these changes have **not** been pushed to `main`. They are ready for review and local testing before merging.
