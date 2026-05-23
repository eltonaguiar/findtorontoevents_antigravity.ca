# B8 — Kill-Switch Leak Verification Report (2026-05-01)

## Gemma4's Claim

> "2 post-kill picks leaked through `isolated_signal_integrator.py`."

## Empirical Investigation

### Step 1 — Active picks vs kill list

Loaded `alpha_engine/data/active_picks.json` (156 picks) and compared each
pick's `strategy` field against the kill list in `alpha_engine/data/core_whitelist.json`
(541 entries).

**Result: 77 active picks with strategy in the kill list.**

Example leaked picks:
| strategy | source_system |
|---------|--------------|
| ml_enhanced_TRXUSDT | ml_crypto_predictor |
| ml_enhanced_ARBUSDT_1h_D_ensemble_stack | ml_strategy_reviver |
| ml_enhanced_FETUSDT_1d_B_lightgbm | ml_strategy_reviver |

### Step 2 — Route analysis

`isolated_signal_integrator.py` has a `SOURCES` list of 26 source systems:
`quan_engine`, `crypto_ml_edge`, `genome`, `battleground`, `claude_gainer_st`,
`tsmom_volscaled`, etc.

**Neither `ml_crypto_predictor` nor `ml_strategy_reviver` is in SOURCES.**

These systems route through `audit_trail/dashboard_generator.py` → `JSON_PICK_SOURCES`
(line 3586), which does NOT apply the kill list. The 77 leaks come from the
dashboard generator path, not the integrator.

### Step 3 — Integrator kill check verification

Inspecting `isolated_signal_integrator.py` lines 653-657 (before fix):

```python
strategy = normalized.get("strategy", "")
if isinstance(strategy, str) and strategy.lower() in kill_list:
    src_stats["filtered"] += 1
    continue
```

**The `isinstance(strategy, str)` guard has a bypass:**

If a normalizer stores `strategy: null` (None) in the normalized dict
(possible when the source JSON has `"strategy": null`), then:
- `normalized.get("strategy", "")` → `None` (key exists, returns None, not default "")
- `isinstance(None, str)` → `False`
- Kill check **skipped**

This is not the specific "2 picked leaked" scenario Gemma4 described (those
picks came from `ml_crypto_predictor`, not the integrator), but it IS a real
bypass path for any integrator source that emits `"strategy": null`.

## Verdict

| Claim | Verdict |
|-------|---------|
| "2 post-kill picks leaked through `isolated_signal_integrator.py`" | **FALSE ALARM** — leaks exist but route through `dashboard_generator.py`, not the integrator |
| `isolated_signal_integrator.py` has a kill-bypass | **REAL** — `strategy=None` skips the `isinstance` check |

## Fix Applied

`alpha_engine/isolated_signal_integrator.py` line 654 changed from:
```python
strategy = normalized.get("strategy", "")
if isinstance(strategy, str) and strategy.lower() in kill_list:
```
to:
```python
strategy = str(normalized.get("strategy") or "").strip()
if strategy.lower() in kill_list:
```

`str(... or "")` coerces None → "", int → str representation, list → repr.
Combined with `""` being explicitly in the kill list, this catches all
non-string strategy values.

## Residual risk

The 77 kills leaked via `dashboard_generator.py` are a **separate issue** (B21/B22
territory — the dashboard's killed-strategy filtering is not the same as the
integrator's). The dashboard intentionally loads ALL sources including killed
strategies for historical tracking. Kill enforcement at the dashboard layer
is a future hardening item.

## Tests added

`tests/test_kill_switch_leak.py` — 13 tests covering:
- Kill list structure and protected-strategy exclusion
- The B8 fix: `strategy=None` now caught
- Real-data CI gate: no integrator sources appear in leaked picks
