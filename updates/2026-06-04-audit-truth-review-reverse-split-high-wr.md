# 2026-06-04 Audit Truth Review — Reverse Splits, Staleness, High-WR Skepticism

## Goal
Goal #1: verify `findtorontoevents.ca/audit` surfaces (main audit, AI leaderboard, AI tournament, curated picks, pick funnel) for stale data, reverse-split price corruption, and inflated win-rate claims.

## What Was Broken

1. **Reverse-split picks** could pollute aggregate strategy/symbol stats when pre-split entries were compared to post-split prices (WKHS/LODE/KULR/etc.).
2. **High WR strategies** (e.g. `luxalgo_confluence` 80.6% on n=31) displayed without DSR/small-n warnings despite `dsr_verdict: OVERFIT_LIKELY`.
3. **pick_funnel.html** local click log showed raw UTC timestamps in one table while the rest of the page used EST.
4. **curated_picks_20260524.html** listed **KULR** in penny stocks without reverse-split context; snapshot date was UTC-only.
5. **ai_leaderboard.html** had no staleness banner when `ai_leaderboard_index.json` is >24h old.

## What Changed

| File | Change |
|------|--------|
| `audit_trail/reverse_split_symbols.py` | Canonical registry (LODE, FFIE, WKHS, KULR, HOLO, GSAT) |
| `audit_trail/dashboard_generator.py` | `_annotate_reverse_split_pick()`; exclude unadjusted RS rows from sym-track stats; stamp active + recent_closed |
| `audit_dashboard/template.html` | RSPLIT badge on pick rows; SMALL-n + OVERFIT badges on strategy drill-down |
| `audit_dashboard/pick_funnel.html` | Click log uses `toEST()`; column header "When (EST)" |
| `audit_dashboard/curated_picks_20260524.html` | EST snapshot label + KULR reverse-split footnote |
| `audit_dashboard/ai_leaderboard.html` | EST "Last updated" + stale-data warning if index >24h |
| `tools/audit_truth_scan.py` | Reproducible read-only audit (`--live` or local JSON) |

## Live Audit Results (2026-06-04 ~12:00 EST)

- **Dashboard freshness:** `generated_at` ~0.9h old — **fresh** (hourly cron healthy).
- **Reverse-split in recent_closed/active:** none currently flagged in live payload (registry ready for next hit).
- **PnL tiers:** no pick ≥80% PnL; one at 51% (HYPEUSDT) — entry/exit prices consistent.
- **WR ≥80%:** all flagged as small-n or OVERFIT except none are money-ready; `luxalgo_confluence` = OVERFIT_LIKELY at n=31.
- **TQQQ/SQQQ:** not in reverse-split registry (leveraged ETF decay, not corporate splits) — correctly excluded.

## Verification

```bash
python3 -c "import py_compile; py_compile.compile('audit_trail/dashboard_generator.py', doraise=True)"
python3 tools/audit_truth_scan.py --live
```

## Reproducer

```bash
python3 tools/audit_truth_scan.py --live
# or local:
python3 tools/audit_truth_scan.py --json audit_dashboard/data/dashboard_data.json
```