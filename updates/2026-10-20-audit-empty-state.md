# Audit empty-state: gate-validated only smart_picks + curated_feed

Date: 2026-10-20

## Problem
`/audit` Smart Picks tab showed 0 picks. A prior fallback promoted unvalidated `smart_picks_feed` picks into `picks.smart_picks`, which violated the rule that picks failing gates must not appear as "Smart Picks".

## Change
- `audit_trail/dashboard_generator.py`: `smart_picks` remains strictly gate-validated (quality gates). Added:
  - `picks.curated_feed`: curated smart_picks_feed picks labeled "Curated – not gate-validated" (separate field).
  - `picks.smart_picks_gate_failures`: counts of failed gates.
  - `picks.smart_picks_near_miss`: top 3 near-miss picks with their failed gate (contingency for empty state).

## Validation
- Regenerate dashboard; assert `smart_picks` contains only gate-passed picks.
- Added test (see PR) asserting no unvalidated pick appears in `smart_picks`.
"