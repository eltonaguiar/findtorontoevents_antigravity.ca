# WIRED_IN — childlike-airport — 2026-11-15T0150Z

Shadow monitoring cards for findtorontoevents.ca/audit. Not money-ready. `sizing_allowed=false`.

## What is wired

| Asset class | Pick | Strategy | Status |
|---|---|---|---|
| ETF | XLV LONG 188.85 / TP 195.03 / SL 185.15 | `wired_in_trend_momo_4d` | OPEN paper |
| EQUITY | LLY LONG 1443.50 / TP 1528.62 / SL 1392.53 | `wired_in_trend_momo_4d` | OPEN paper |
| BOND | SHY LONG 81.17 / TP 81.39 / SL 81.04 | `wired_in_short_duration_ballast` | OPEN paper |
| CRYPTO, FOREX, COMMODITY, FUTURES, MF, prediction markets | none | eliminated | see ELIMINATION.md |

Active file the audit pipeline reads: `audit_dashboard/data/wired_in_childlike_active_picks.json`.
Closed file starts empty. The hourly audit workflow runs `universal_pick_resolver`, which now lists this source, and writes TP/SL/TIME_EXIT rows into `audit_trail/data/universal_resolved_picks.json`. The dashboard generator drops matching active ids once that file updates. Push does not redeploy the site; the hourly cron does.

System name: `wired_in_childlike`. Flagged `paper_only` so these rows display but do not count as forward-tested wins.

## Files

- `ALGORITHM_SPEC.md` — rule per asset class
- `PICK_JUSTIFICATION.md` — why these three
- `ELIMINATION.md` — what was rejected and why
- `RESEARCH_AND_BACKTEST.md` — prices used and the 5y replay
- `PARTICLE_1_FREE_429.md` — OpenRouter 429 debug
- `picks/active_picks.json` — copy of the wired active file
- `picks/closed_picks.json` — empty until the resolver closes something
