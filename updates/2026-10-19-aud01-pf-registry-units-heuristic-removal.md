# AUD-01: at_pick_outcomes return-unit contract — magnitude heuristic removed

**Date:** 2026-10-19
**Package:** AUD-01 (`planv2_Oct19_github.MD`) — eliminate return-unit ambiguity
**Files:** `tools/build_pf_registry.py`, `tests/test_audit_cohort_units.py` (new)

## What was broken

`tools/build_pf_registry.py::_load_outcomes_rows` normalized
`at_pick_outcomes.pnl_pct` with a magnitude heuristic:

```python
r["pnl_pct"] = pnl_f / 100.0 if abs(pnl_f) > 1.0 else pnl_f
```

The source column is stored in **PERCENT** (traced 2026-10-19):

- CADJPY=X WON row = `427.9526` matches the documented "+428%" price-feed
  artifact (a fraction 427.95 would be +42,795% — impossible).
- CRYPTO floor is exactly `-100.0` (a long cannot lose >100%; a fraction −100
  would be −10,000%).
- The loader's SQL sanity cap is commented "Caps in PERCENT".

The heuristic decided the *unit* of a number from its *magnitude*, mixing
units **within one cohort**: `2.0` (percent) scaled to `0.02`, but `0.5`
(percent) stayed `0.5` — read downstream as a 50% fraction, **100× too big**.
Every percent value ≤ 1 silently inflated PF/WR, because all downstream
consumers (`SPOT_FLICKER_THRESHOLD=0.0002`, `DOLLAR_SCALE_ARTIFACT_THRESHOLD=1.0`,
fraction-unit slippage, `_rolling_mdd` compounding `1.0 + r`) expect fractions.

## What changed

- Added `_pnl_percent_to_fraction(pct)` which **always divides by 100 — no
  magnitude inference** — and rewired `_load_outcomes_rows` to use it:

```python
r["pnl_pct"] = _pnl_percent_to_fraction(pnl_f)
```

- The uniform scale factor (0.01) now applies to every magnitude, so the
  cohort is unit-consistent: percent in → fraction out, documented at the
  adapter (the AUD-01 contract), never inferred from the value's size.
- Traced +428% artifact still converts to fraction `4.28` (>1.0), so the
  dollar-scale filter continues to drop it after conversion.

## Verification

- `python3 -m pytest tests/test_audit_cohort_units.py tests/test_money_ready_verdict_strict_json.py -q` → **13 passed**
  - `test_no_magnitude_inference` pins uniform `×0.01` for
    0.05 … 99.67 (the exact regression: values ≤ 1 must ALSO be scaled)
  - `test_plan_fixture_percent_to_fraction` pins the AUD-01 acceptance
    fixtures (0.25/1.0/2.0 → 0.0025/0.01/0.02)
  - pure/offline — no DB, no generator, no network
- Full asset-class importer suite (`tests/test_asset_class*.py`) → **110 passed**
- `python3 -m py_compile tools/build_pf_registry.py` → clean

## Status

Fix + doc staged for commit on `fix/js-reference-accuracy-audit`; only files
created/modified by this work are included.
