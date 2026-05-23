# B11: ETF Sector Emitter Workflow Wire (2026-05-02)

**PR:** fix/b11-etf-sector-workflow-wire-2026-05-02  
**Queue item:** B11 — ETF Source Diversification (`reports/REMAINING_ACTION_ITEMS_2026_04_30.md`, Order 12)

## Problem

`tools/etf_sector_emitter.py` (Faber TAA sector rotation over SPDR ETFs) was added on 2026-05-01 and registered in `JSON_PICK_SOURCES` at `audit_trail/dashboard_generator.py:3848`. However, the ETF workflow (`.github/workflows/alpha-engine-etf.yml`) only calls `tools/etf_emitter_spike.py` (proof-of-concept), which writes to `active_picks_etf_draft.json` — a file that is NOT in `JSON_PICK_SOURCES`. The result: `alpha_engine/data/etf_sector_picks.json` remains at its placeholder `picks: []` and no Faber TAA picks ever reach `/audit`.

## Investigation findings

| Metric | Value |
|---|---|
| ETF recent_closed picks | 86 |
| kimi_riseoftheclaw share | 74/86 = 86.0% |
| kimi ETF WR (by pnl_pct) | 52.7% |
| kimi ETF sum_pnl | +25.78% |
| ETF active picks | 0 (all blocked by quality gates) |
| `etf_sector_picks.json` state | Placeholder — `picks: []` |

The concentration is real (86%) and the goal of B11 is to add an independent source. The underlying kimi performance is positive, but single-source concentration is a risk.

## Fix

**One workflow addition** to `.github/workflows/alpha-engine-etf.yml`:

1. Added `python tools/etf_sector_emitter.py` to the "Run ETF emitter" step after the spike call.
2. Added `git add alpha_engine/data/etf_sector_picks.json` to the commit step.

## Wire-Up Rule

**Already wired.** `JSON_PICK_SOURCES` entry at `dashboard_generator.py:3848` was added by the original B11 PR. This PR completes the last mile — the workflow invocation — so picks flow through on each 6-hour cycle.

## Expected behavior after merge

- On next `alpha-engine-etf.yml` run (every 6h): emitter fetches yfinance 13-month OHLCV for SPDR sector ETFs, applies Faber 10-month SMA filter + 3-month momentum ranking, writes BUY/SHORT picks to `etf_sector_picks.json`.
- Dashboard picks up `etf_sector_picks.json` on next hourly rebuild and surfaces picks tagged `source_system=etf_sector_rotation`.
- Quality gates (score floor, forward_wr floor) apply normally. Initially these picks go to `active_raw`. After ≥20 forward-closed picks at ≥40% WR, they graduate to `active`.
- If yfinance is unavailable: `picks: []` is written — no crash, no dashboard pollution.

## Tests

`tests/test_etf_sector_emitter.py` — 7/7 passing (existing, covers emitter logic).

## Multi-AI feedback

- `reports/feedback/B11-self-review-1-2026-05-02.md` — confirmed ready-to-ship
- `reports/feedback/B11-self-review-2-2026-05-02.md` — confirmed ready-to-ship; noted potential `etf_strategies` import path risk (handled by PYTHONPATH in workflow)
