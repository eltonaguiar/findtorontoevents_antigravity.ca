# Swarm review: VIX+YC combined gate diff

## Context

Branch `feat/vix-yc-combined-gate-2026-05-13`. Implements 2-of-2 regime filter per backtest result:
- EQUITY VIX<22 AND YC>0: PF 4.98 / Sharpe 2.08 / MDD 16.8% / n=79
- EQUITY VIX<20 AND YC>0: PF 5.87 / Sharpe 2.29 / MDD 7.2% / n=77 (SUPER-BREAKTHROUGH)

Prior swarm consult voted Option C standalone verifier for NS-A (shipped); voted PROCEED + add_new_function for this Item 1.

## Diff summary

### `audit_trail/vix_regime_gate.py` extensions
- Added `_YC_CACHE` module-level state (independent from VIX cache, same 4h TTL)
- Added `_fetch_yc_now()` — yfinance ^TNX - ^FVX, fail-open
- Added `get_cached_yc()` — same TTL pattern as VIX
- Added `is_yc_below_threshold(threshold=None)` — env `YC_REGIME_GATE_MIN_SPREAD` (default 0.0)
- **Added `should_reject_combined(pick)`** — new function (not overload of equity_pick)
- Added `reset_yc_cache()` test helper
- Kept `should_reject_equity_pick()` unchanged (backward-compat for PR #958/#959)

### `audit_trail/quality_gates.py::passes_smart_gate` extension
- Wires `should_reject_combined()` FIRST (precedence over single-VIX)
- Sets `_hf_quality_gate_reason = "vix_yc_regime_combined"` on combined reject
- Existing VIX-only path still active when `YC_REGIME_GATE_ENABLED=0` + `VIX_REGIME_GATE_ENABLED=1`

### `tests/test_vix_yc_combined_gate.py` — 11 new tests
- Default-off behavior
- VIX-high reject path
- YC-inverted reject path
- Both-clean pass path
- EQUITY + ETF coverage
- CRYPTO/FOREX/BOND/COMMODITY/FUTURES unaffected
- Threshold configurability
- Fail-open on YC fetch failure (VIX-only fallback)
- Independent VIX/YC caching
- Integration wire-check (smart-gate has the call)
- Combined fires BEFORE single-VIX in call order

**57/57 total gate-suite tests pass** (11 new + 46 regression on NS-C/D/F + FX1 + prior VIX gate).

## Question to engines

Return strict JSON ONLY:

```json
{
  "verdict": "APPROVE | APPROVE_WITH_CAVEATS | REQUEST_CHANGES | REJECT",
  "merge_decision": "MERGE | HOLD | REJECT",
  "code_quality_score": <1-10>,
  "default_state_correct": "<yes | no>",
  "stacks_with_vix_only_path": "<correctly | conflict | unclear>",
  "concerns": ["<list>"],
  "missing_edge_cases_or_tests": ["<list>"],
  "production_safety": "<safe | risky | needs_shadow_first>"
}
```

## Constraints

- YC_REGIME_GATE_ENABLED defaults to 0 (OFF) — preserves PR #958/#959 behavior
- VIX_REGIME_GATE_ENABLED still works independently for single-VIX use case
- When both flags on, combined gate fires first; if it passes, VIX-only also checks (but won't fire since same VIX condition already evaluated)
- Reversibility: env-flag flip
- Fail-open on yfinance failures (preserves throughput)
- yfinance multi-ticker download (^TNX + ^FVX) is single call, same rate-limit class as VIX-only fetch
