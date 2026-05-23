# Fix: recent_closed leaked banned sources/tiers

Date: 2026-04-30
Area: audit dashboard closed-history publication path
Files:
- audit_trail/dashboard_generator.py
- tests/test_dashboard_generator.py

## What was broken

`_build_recent_closed_picks()` was publishing rows from banned source systems and rows explicitly labeled with banned trust tiers into `recent_closed`.

Impact:

1. Polluted class-level metrics in the audit dashboard (PF/WR/DD by asset class).
2. Weakened trust in high-conviction diagnostics derived from published closed cohorts.

## What I changed

1. Added an early filter in `_build_recent_closed_picks()` to exclude:
	- picks where `get_tier(source_system) == "BANNED"`
	- picks where `trust_tier` or `at_issue_trust_tier` is in `_HARD_BLOCKED_TRUST_TIERS`
2. Added regression test `test_build_recent_closed_picks_excludes_banned_sources_and_tiers()`.

## How it was verified

1. Runtime behavioral check using Python snippet (same synthetic case as test):
	- Input symbols: `BTCUSDT` (rapid_fire), `AAPL` (trust_tier=BANNED), `MSFT` (valid)
	- Output after fix: `['MSFT']`
2. Syntax validation:
	- `python -m py_compile audit_trail/dashboard_generator.py tests/test_dashboard_generator.py`
3. Editor diagnostics:
	- No errors in both touched files.

## Notes

- `pytest` is not available in the current environment (`No module named pytest`), so executable validation was done via direct runtime snippet and `py_compile`.
