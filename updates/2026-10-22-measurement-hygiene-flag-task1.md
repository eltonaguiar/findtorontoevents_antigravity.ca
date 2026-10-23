# Task 1 — MEASUREMENT_HYGIENE_V1 rollout flag (default OFF)

**Date:** 2026-10-22
**Plan:** Measurement Fix (Sub-project 1) — Task 1 of 12
**Plan doc:** `docs/superpowers/plans/2026-10-22-measurement-fix.md`
**Design spec:** `docs/superpowers/specs/2026-10-22-measurement-fix-design.md`

## What was broken/missing

The Measurement Fix plan needs a single opt-in rollout gate for several
measurement corrections (net-of-cost, overlap-aware compounding, benchmark
columns, and 4 quick-fix gates). No such flag existed, so there was no safe
way to enable/disable the corrections without mixing them into the default
dashboard output.

## What changed

- **`audit_trail/dashboard_generator.py`** — added module-level constant
  ```python
  MEASUREMENT_HYGIENE_V1 = os.environ.get("MEASUREMENT_HYGIENE_V1", "0") == "1"
  ```
  Default-OFF. Only the literal string `"1"` enables it. When OFF (absent,
  `"0"`, empty, or any other value) output is byte-identical to the prior
  un-flagged build.
- **`tests/test_dashboard_generator_measurement_hygiene.py`** — new TDD test
  file (5 tests): constant exists, defaults OFF when unset `"0"`/empty/garbage,
  and turns ON only for literal `"1"`.

## Verification

- RED: all 5 new tests failed with `AttributeError: ... has no attribute
  'MEASUREMENT_HYGIENE_V1'` before the constant was added.
- GREEN: `python3 -m pytest tests/test_dashboard_generator_measurement_hygiene.py -v`
  → **5 passed**.
- Task step 1.3 command: `MEASUREMENT_HYGIENE_V1 = False` → `PASS`.
- `py_compile` on `dashboard_generator.py` → OK.
- No regression: `tests/test_dashboard_generator_net_pf_wireup.py` → **9 passed**.

## Safety

- Byte-identical output when OFF (the whole point of the default-OFF flag).
- The flag only *defines* the gate; later plan tasks (2–12) wire behavior
  into it.

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
