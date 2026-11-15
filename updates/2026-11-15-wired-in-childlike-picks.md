# 2026-11-15 wired_in_childlike monitoring cards

## What was broken

New discretionary picks had nowhere to land that both the audit dashboard and the universal resolver read. Prior retrofits (tradingagents, stocksunify2) showed that a dashboard-only path stays OPEN forever.

## What changed

- Added `audit_dashboard/data/wired_in_childlike_active_picks.json` (XLV, LLY, SHY; paper, no `current_price`).
- Added an empty closed file for the same system.
- Registered `wired_in_childlike` in `audit_trail/dashboard_generator.py` `JSON_PICK_SOURCES` and `_PAPER_ONLY_SYSTEMS`.
- Registered the same active path in `audit_trail/universal_pick_resolver.py` `SYSTEM_SOURCES`.
- Spec and elimination notes: `WIRED_IN/2026-11-15T0150Z_childlike-airport/`.

## Verification

- JSON parses; three OPEN picks; no `current_price` (resolver treats that as already closed).
- `tests/test_wired_in_childlike_wireup.py` checks both registries name the same file.
- Replay numbers are in the spec folder. They do not clear a PF 1.5 gate. Cards are monitoring only.
