# 2026-05-01 — B8: Kill-Switch Leak Verification + Fix

**PR:** feat/b8-kill-switch-leak-verify-2026-05-01  
**Item:** B8 from `reports/REMAINING_ACTION_ITEMS_2026_04_30.md` (Order 18)  
**Risk:** LOW (single-line hardening fix; kill list coverage improves, never weakens)

## What shipped

**Verification:**

Gemma4 claimed "2 post-kill picks leaked through `isolated_signal_integrator.py`".
Empirical investigation (see `reports/B8_KILL_SWITCH_VERIFICATION_2026_05_01.md`):

- 77 active picks have strategy names in the kill list — **but** they all come
  from `ml_crypto_predictor` / `ml_strategy_reviver`, which route through
  `dashboard_generator.py`, NOT through `isolated_signal_integrator.py`.
- The integrator's SOURCES list (26 entries) does NOT include those systems.
- **Gemma4's specific claim = FALSE ALARM** for the integrator file.

**Real bypass found and fixed:**

`strategy = normalized.get("strategy", "")` followed by `isinstance(strategy, str)`
has a bypass: if a normalizer explicitly stores `"strategy": null` (JSON null),
`get()` returns `None` (not the default `""`), and `isinstance(None, str)` → False
→ kill check skipped.

Fix (1 line change): `str(normalized.get("strategy") or "").strip()` — coerces
None/int/list strategy values to string before the kill check. Combined with
`""` already being in the kill list, this catches all edge cases.

**Files changed:**

| File | Change |
|------|--------|
| `alpha_engine/isolated_signal_integrator.py` | Kill check line 654 hardened (str coercion) |
| `tests/test_kill_switch_leak.py` | **New** — 13 tests (all pass) |
| `reports/B8_KILL_SWITCH_VERIFICATION_2026_05_01.md` | Full verification report |

## Wire-Up Rule

N/A — one-line bug fix in an existing production call site. Not a new module.

## Test plan

- [x] `pytest tests/test_kill_switch_leak.py -v` → 13/13 pass
- [x] `python3 -m py_compile alpha_engine/isolated_signal_integrator.py` → OK
- [x] Real-data CI gate: no integrator-sourced picks appear in kill-list leaks
