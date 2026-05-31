# Strategy Build — Post-IPO Drift (Loughran & Ritter 1995)

**Date:** 2026-05-31
**Agent:** peer_claude (build wave)
**Slug:** `post_ipo_drift`
**Isolation:** `/tmp/strategy_builds_2026-05-31/post_ipo_drift/` (no shared-tree edits)

## Academic basis
Loughran & Ritter (1995), "The New Issues Puzzle," *J. Fin.* 50(1) 23-51. 5yr IPO BHR ~15.7% vs 66.4% matched non-issuers → systematic post-IPO underperformance.

## Implementation summary
- **strategy.py — 285 lines.** Two variants:
  - Classical SHORT at T+180d (lockup expiry), hold 180-365d, equal-weight basket.
  - Modern LONG at T+90d gated by (rev YoY > 20%, OCF positive, mkt-cap > $500M, float > $100M, price > $5, not SPAC by name or flag).
- **paper_pilot_harness.py** — JSON state under `state/` only. Writes NEVER reach `ejaguiar1_stocks.trading_picks`. Tick advances asof-date, opens/closes positions, mark-to-market PnL.
- **tests.py** — 10 unit tests, all passing (filters, signals, Wilson LB, bootstrap PF, gate logic).

## Cursor statistical framework (M-107 compliant)
- n_floor = 500 trades before live promotion.
- α_family = 0.05; N = 7 strategies → α_Bonferroni ≈ 0.00714.
- Admit-live requires: n≥500 AND binomial-one-sided p < α_Bonf AND Wilson95 LB > 0.50 AND bootstrap PF 95% CI lower > 1.0.
- All four implemented in `statistical_gate()`.

## Universe
Seed sample contains 3 IPOs (1 strong-fundamentals long, 1 lockup-expiry short, 1 SPAC rejected). Real universe expected ~150-200 US IPOs/yr; after filters ~40-60/yr admissible.

## AI consult
**DeepSeek (deepseek-chat)** consulted via REST on filter tightening. Verbatim response in `ai_consult_deepseek.json`. Top recs:
1. Tighten rev YoY 20%→40% + sequential QoQ acceleration.
2. Add VC/share-overhang filter (pre-IPO VC>50% + lockup float-increase >25%).
3. Require positive EPS revisions over 30d pre-entry.
4. ≥15% institutional ownership pre-lockup.
5. Volume + 50DMA relative-strength filter.

Logged as v2 candidates; v1 kept pure L&R for clean baseline comparison.

## Wire-up
Sidecar / paper-only. Target caller `alpha_engine/production_scanner.py::scan_equity()` gated behind `ENABLE_POST_IPO_DRIFT=1`. Promotion contingent on paper pilot reaching `admit_live=True`. ETA 18-24 months given universe size.

## Files (absolute paths)
- `/tmp/strategy_builds_2026-05-31/post_ipo_drift/strategy.py`
- `/tmp/strategy_builds_2026-05-31/post_ipo_drift/paper_pilot_harness.py`
- `/tmp/strategy_builds_2026-05-31/post_ipo_drift/tests.py`
- `/tmp/strategy_builds_2026-05-31/post_ipo_drift/README.md`
- `/tmp/strategy_builds_2026-05-31/post_ipo_drift/ai_consult_deepseek.json`
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/reports/peer_claude-strategy-build-post-ipo-drift_2026-05-31.md`

## Test verification
```
Ran 10 tests in 0.286s — OK
```
