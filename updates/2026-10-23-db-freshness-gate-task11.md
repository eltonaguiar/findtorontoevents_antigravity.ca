# Task 11: DB Freshness Gate as Measurement Hygiene Input

**Date:** 2026-10-23

## What was broken / missing

The measurement hygiene pipeline emitted its `measurement_hygiene` payload
block without validating the recency of the underlying data sources. A stale
database (e.g. an old `pf_registry.json` or an aged `money_ready_archive/*.json`)
could be presented as if the underlying data were current, undermining the
measurement integrity the block is meant to convey.

## What changed

- Added `audit_trail/dashboard_generator.py::_check_data_freshness()` — a
  fail-soft helper returning `(freshness_ok, warning)`.
  - Reads the latest timestamp from each canonical source:
    `audit_dashboard/data/pf_registry.json` and every
    `audit_dashboard/data/money_ready_archive/*.json`.
  - Timestamp resolution: tries content timestamps (`generated_utc`,
    `generated_at`, `as_of`, `timestamp`, `scan_timestamp`, `last_updated`,
    `updated_at`), then falls back to file mtime.
  - Any source older than 24 h → `(False, warning)`; otherwise `(True, "")`.
  - Missing/unreadable sources are ignored (fail-open); if no source is
    readable the gate passes. Never raises.
- Wired the gate into `_attach_measurement_payload_keys()`:
  - Fresh → `freshness_ok: true`, no warning, `enabled` preserved.
  - Stale → `freshness_ok: false`, `enabled` forced `false`, and a
    `freshness_warning` field added to the `measurement_hygiene` block (both
    the top-level and `summary` blocks; if no block exists, a minimal block is
    created so the warning always surfaces).
- `generate()` now calls `_check_data_freshness()` before emitting the
  `measurement_hygiene` block and passes the result through.
- Added `tests/test_freshness_gate.py` (9 tests covering fresh/stale content
  timestamps, mtime fallback, fail-open missing sources, any-stale wins, and
  the payload attachment behavior including that non-hygiene fields are
  untouched).

## Verification

- `python3 -m pytest tests/test_freshness_gate.py -q` → **9 passed**.
- Related dashboard/measurement suites run clean (210 passed) — the only
  failures in the full run were pre-existing FOREX gate parity tests in
  `tests/test_quality_gates.py` (unrelated to freshness; untouched by this
  change).
- `py_compile` passes on both changed files.
- Global "NOT FINANCIAL ADVICE" disclaimer invariant preserved — no disclaimer
  strings were modified.
