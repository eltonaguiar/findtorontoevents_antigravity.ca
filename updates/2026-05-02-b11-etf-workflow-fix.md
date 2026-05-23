# B11 Fix — ETF Emitter Workflow (2026-05-02)

**Queue item:** B11 — ETF source diversification  
**Root cause:** `alpha-engine-etf.yml` was calling the spike script, not production emitters  
**Risk:** LOW — additive workflow steps; graceful fallback on yfinance failure

## Root Cause Investigation

Three ETF sources are registered in `JSON_PICK_SOURCES` but all produce 0 active picks:

| Source | File | Root Cause |
|--------|------|-----------|
| `leveraged_etf_decay` | `leveraged_etf_decay_picks.json` | Stale (28 days); no workflow to regenerate; script writes to `etf_decay_picks.json` instead |
| `etf_sector_rotation` | `etf_sector_picks.json` | Empty — `etf_sector_emitter.py` never called by any workflow |
| `orphan_emitter_etf` | `non_crypto_agent/data/etf_picks.json` | quality=0; separate pipeline issue |

The `alpha-engine-etf.yml` workflow was calling `tools/etf_emitter_spike.py` which:
- Writes to `active_picks_etf.json` (explicitly marked `ingested_by_dashboard: False`)
- Is documented as a proof-of-concept, not a production emitter

## Fix

### 1. Workflow updated (`alpha-engine-etf.yml`)
Added two new production emitter steps:
- `tools/etf_sector_emitter.py` with `ETF_SECTOR_EMITTER_ENABLED=1` → writes `etf_sector_picks.json`
- `alpha_engine/strategies/etf_decay_shorts.py` → writes `etf_decay_picks.json`

Both steps use `|| echo "... (graceful fallback)"` so yfinance failures don't abort the workflow.

The commit step now includes both new output files.

### 2. JSON_PICK_SOURCES path corrected (`audit_trail/dashboard_generator.py`)
Changed `leveraged_etf_decay` entry from `leveraged_etf_decay_picks.json` (stale manually-crafted stub) to `etf_decay_picks.json` (actual script output).

## Expected Impact

On next `alpha-engine-etf.yml` run in GitHub Actions (where yfinance has network access):
- `etf_sector_picks.json` will contain Faber TAA sector ETF signals (SPDR XLK/XLE/XLV/QQQ)
- `etf_decay_picks.json` will contain leveraged ETF decay SHORTs (LABD/JDST/SOXS/DRIP)
- Both will flow to `/audit` on next dashboard rebuild

If yfinance fails in the workflow, both files get 0 picks — same behavior as today.

## Tests

- 9 new tests in `tests/test_b11_etf_workflow_fix.py` — all pass
- 7 existing `tests/test_etf_sector_emitter.py` tests — all pass
- 18 existing `tests/test_etf_iwm_gld_kill.py` tests — all pass

## Wire-Up Rule

`etf_sector_rotation` and `leveraged_etf_decay` are already registered in `JSON_PICK_SOURCES`. This PR fixes the operational gap (wrong script being called) — no new module, no new Wire-Up Rule obligation.
