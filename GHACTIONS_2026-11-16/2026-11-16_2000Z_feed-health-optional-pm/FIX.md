# Fix — Feed Health hourly RED: pm_momentum_signals required but dead-by-design

- Date: 2026-11-16T20:00Z · File: `audit_trail/dashboard_payload_health.py`
- Symptom: `Feed Health Check` failing every hour since 17:39Z:
  `MISSING system rows (1): ['pm_momentum_signals'] — missing_from_payload` → exit 1.

## Root cause
`_OPTIONAL_SYSTEMS` listed only `pm_kalshi_re_signals` / `pm_polymarket_re_signals`. But
`pm_momentum_signals` is in `dashboard_generator._GHOST_SYSTEMS` (dead-by-design) and
`pm_whale_signals` / `pm_kalshi_signals` are ephemeral (produced only inside the audit-dashboard
job, gitignored via `**/data/*_signals.json`, never committed). They therefore cannot emit a
payload row on most runs — requiring them fails the gate hourly on a source that will never appear.

## Change
Added `pm_momentum_signals`, `pm_whale_signals`, `pm_kalshi_signals` to `_OPTIONAL_SYSTEMS`
(absence = warning, not failure). Required/healthy sources still fail the gate as before.

## Downstream
Feed Health gate (hourly) stops red-flagging a permanently-absent dead source; real wiring
regressions still surface. `tests/test_dashboard_payload_health_optional.py` 4/4 pass.

## Revert
`git checkout origin/main -- audit_trail/dashboard_payload_health.py` (or remove the 3 lines).
