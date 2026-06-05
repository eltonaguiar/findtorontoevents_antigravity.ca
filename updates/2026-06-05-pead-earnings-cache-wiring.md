# PEAD shadow: wire `data/earnings/` cache into production scanner

## What was broken

`pead_equity` shadow mode only loaded `incubator_picks.json`. Structured earnings snapshots under `data/earnings/<TICKER>/latest.json` were unused, and `REQUIRE_GUIDANCE_RAISE=True` blocked most cache events.

## What changed

- **`alpha_engine/equity_earnings_loader.py`** — maps earnings JSON history (≥5% surprise) to PEAD event dicts.
- **`production_scanner.py`** — merges cache events when `PEAD_EQUITY_ENABLED=1`.
- **`pead_equity.py`** — `PEAD_REQUIRE_GUIDANCE_RAISE` env (default `1`; `0` for shadow probation).

## Verify

```bash
python3 -m pytest tests/test_equity_earnings_loader.py tests/test_m009_pead_equity.py -q
python3 -c "from alpha_engine.equity_earnings_loader import load_pead_events_from_earnings_cache; print(len(load_pead_events_from_earnings_cache()))"
```

## Ops

Shadow collection (does not add to `active` unless probation PR merged):

```bash
PEAD_EQUITY_ENABLED=1 PEAD_REQUIRE_GUIDANCE_RAISE=0
```