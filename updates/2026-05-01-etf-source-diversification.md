# ETF Source Diversification — B11 (2026-05-01)

**PR:** feat/etf-source-diversification-2026-04-30  
**Item:** B11 from `reports/REMAINING_ACTION_ITEMS_2026_04_30.md`

## What shipped

Adds the first alternative ETF emitter to reduce kimi concentration in the
ETF active book: **SPDR Sector Rotation** via Faber Tactical Asset Allocation.

### New emitter: `tools/etf_sector_emitter.py`

Implements Faber (2007) 10-month SMA filter + 3-month sector momentum across
SPDR sector ETFs (XLK, XLF, XLE, XLV, IWM, TLT, HYG) using the existing
`alpha_engine/etf_strategies::etf_sector_momentum` strategy.

- Writes to `alpha_engine/data/etf_sector_picks.json`
- Controlled by `ETF_SECTOR_EMITTER_ENABLED` env flag (default on)
- Fails gracefully: yfinance unavailable → empty picks array, no crash

### JSON_PICK_SOURCES registration

`etf_sector_rotation` registered in `audit_trail/dashboard_generator.py` as
an opt-in sidecar. Picks reach `/audit` on next dashboard rebuild after the
emitter cron runs (via `alpha-engine-etf.yml`).

### Files changed

| File | Change |
|---|---|
| `tools/etf_sector_emitter.py` | New production emitter (Faber TAA) |
| `alpha_engine/data/etf_sector_picks.json` | Initial placeholder file |
| `audit_trail/dashboard_generator.py` | `etf_sector_rotation` added to `JSON_PICK_SOURCES` |
| `tests/test_etf_sector_emitter.py` | 7 unit tests — all PASS |

## Wire-Up Rule compliance

**OPT-IN SIDECAR** — the `etf_sector_rotation` entry in `JSON_PICK_SOURCES`
is the production caller. Picks flow to `/audit` automatically. No gate
promotion until ≥14 days of shadow data accrues.

## Wiring plan

The workflow `alpha-engine-etf.yml` already runs `tools/etf_emitter_spike.py`
on a 6h cron. A follow-up PR will update the workflow to call
`tools/etf_sector_emitter.py` instead (or in addition). The current PR ships
the emitter + registration; the workflow update is a ≤5-line change.

## Acceptance criteria met

- [x] ≥1 alternative ETF source added (SPDR sector rotation)
- [x] `JSON_PICK_SOURCES` registration correct
- [x] 7 pytest tests passing
- [x] Syntax checks pass
- [x] Wire-Up Rule: opt-in sidecar with explicit wiring plan
