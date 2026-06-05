# PEAD equity probation — capped live emits

## What changed

When both env flags are set:

- `PEAD_EQUITY_ENABLED=1`
- `PEAD_EQUITY_PROBATION=1`

…the scanner appends up to **`PEAD_EQUITY_PROBATION_MAX`** (default **2**) PEAD signals to `active`, each tagged `_probation=True`.

Shadow log (`pead_shadow_picks.json`) still written. Default remains shadow-only (`PEAD_EQUITY_PROBATION=0`).

## Verify

Dry-run scanner with flags in a dev environment; confirm at most 2 `pead_equity_2day` rows reach active.

## Depends on

PR merging earnings cache loader (`equity_earnings_loader.py`) first.