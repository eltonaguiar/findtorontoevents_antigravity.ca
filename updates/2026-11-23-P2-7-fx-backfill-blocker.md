# P2-7: FX backfill blocker (2026-11-23)

## Summary
FX price backfill for 15 pairs × 203 days is blocked on DB credentials.

## Missing input
- `dbpasses.txt` (must **not** be read by agents)
- `DB_PASS_STOCKS` / `DB_PASSWORDS_JSON` secrets (GitHub Actions)

## Current state
- `fx_prices` span ends **2026-02-09** (stale ~287 days as of 2026-11-23).
- Selection-alpha gate (`alpha_engine/audit3_selection_alpha.py`) reports FX scope empty or fallback.
- POD-FOREX-USDJPY-MOMENTUM (H-2026-11-19-04) is gated on this data.

## Planned commands (run only after creds supplied)
```bash
python3 tools/fx_backfill.py --dry-run --since 2026-02-10 --pairs "EURUSD,GBPUSD,..."
python3 tools/fx_backfill.py --apply   --since 2026-02-10 --pairs "EURUSD,GBPUSD,..."
```

## Acceptance
- `selection_alpha` gate reports non-empty FX scope (`n >= 100` forward rows for at least one FX pod).
- `fx_prices` last bar is within the 5-day TOLERANCE_MS of the run date.

## Notes
- The backfill is intentionally **not** attempted in CI when secrets are absent (see `audit3-ledger.yml:129`).
- Operator must supply the DB creds; agents are forbidden from reading or exposing `dbpasses.txt`.

**Status:** BLOCKED ON HUMAN (DB credentials). No code change required.
