# Update: Measurement Hygiene V1 — Playwright + DB End-to-End Verification (Task 12)

Date: 2026-10-23
Branch: `feat/measurement-hygiene-v1-flag`
Commit: `d0f299c823e224de87ae148c980f93a9863d3c2d`

## What was broken

Task 12 (Playwright + DB End-to-End Verification, final gate) surfaced two issues:

1. **Stale prod artifact in `audit_dashboard/index.html`.** The Playwright spec
   `tests/audit_measurement_hygiene.spec.ts` expects `mountMeasurementBanner()`
   (the `#measurement-hygiene-banner` injector) to exist in the served artifact.
   The canonical source `audit_dashboard/template.html` has it, but the built
   `index.html` artifact was stale and predated the banner code, so the test
   failed with "element not found".

2. **Non-deterministic payload-shape test.** `tests/test_measurement_hygiene_payload.py`
   asserted `mh["enabled"] is True`. Task 11 added the DB freshness gate, which
   correctly forces `enabled=false` when the underlying data sources are stale
   (>24h). Running against live (stale) data made the test fail
   (`assert False is True`).

## What changed

1. **Rebuilt `audit_dashboard/index.html` from `template.html`** via `build_html()`
   so the served artifact contains the banner mount code (+78 lines: `mountMeasurementBanner`
   and the `#measurement-hygiene-banner` target).

2. **Made the payload-shape test freshness-deterministic.** The test now:
   - reloads `audit_trail.dashboard_generator` so the module-level `MEASUREMENT_HYGIENE_V1`
     flag constant is re-evaluated after the env var is set, and
   - monkeypatches `_check_data_freshness` to return `(True, "")`, isolating the
     SHAPE assertions from live data age.

## How it was verified

- `pytest tests/test_freshness_gate.py tests/test_regression_guard.py` → 15 passed.
- `npx playwright test tests/audit_measurement_hygiene.spec.ts --project="Desktop Chrome"`
  → 1 passed (after index.html rebuild).
- `pytest tests/test_measurement_hygiene_payload.py` → 1 passed (after patch).
- Freshness gate end-to-end harness: `stale.json` (48h old) → `enabled=false`,
  `freshness_ok=false`, `freshness_warning` on both top-level and summary blocks.
- Regression guard end-to-end harness: drifted OFF payload → warning + fallback to
  byte-identical previous generation (`used_fallback=True`).
- Disclaimer invariant preserved: "not financial advice" appears 6× in both
  `template.html` and `index.html`.
