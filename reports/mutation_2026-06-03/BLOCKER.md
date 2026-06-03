# Mutation Protocol Blocker — 4 MUTATE_CANDIDATEs (2026-06-03)

**Candidates per `quant_monitor.py`** (PF in [0.7, 1.0]):
- `aggregated_picks` — quant_monitor closed=46, PF≈0.70
- `copy_trader_highscore` — closed=140, PF≈0.88
- `multitf_evolver` — closed=10, PF≈0.72
- `paper_trading` — closed=34, PF≈0.92

## Why mutation analysis cannot proceed

`tools/mutation_analysis.py` (per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`) requires row-level closed picks with `Strategy / Direction / PnL% / Timeframe / System / Symbol`. Available row-level sources:

| Source | aggregated_picks | copy_trader_highscore | multitf_evolver | paper_trading |
|---|---:|---:|---:|---:|
| `trading_picks` (live MySQL, status WON/LOST + pnl_pct NOT NULL) | 0 | 0 | 0 | 0 |
| `trading_picks` any-closed status | 5 (TIME_EXIT) | 0 | 5 (EXPIRED) | 35 (1 TIME_EXIT + 21 SL + 13 TP) |
| `dashboard_data.json.picks.recent_closed` | 5 | 0 | 5 | 15 |

**Mismatch**: quant_monitor's `closed_picks` counters (46/140/10/34) come from a cumulative summary field (`systems[].closed_picks` in dashboard JSON), NOT row-level data. The actual row-level closed picks available today are 5/0/5/15 — well below `min_trades=30` threshold required by `mutation_analysis.py`.

## Likely causes
1. Closed-pick rows for these systems were never written to `trading_picks` (legacy source-system writers bypassed it)
2. Or they were pruned/archived between cumulative counter increment and disk-state snapshot
3. `copy_trader_highscore` 140 closed in counter vs 0 in DB = clearest signal of writer-bypass

## Path forward (operator decision)
- **Option A**: Skip mutation for these 4; mark them CULL or MONITOR based on cumulative PF
- **Option B**: Locate the missing closed-pick writer for legacy sources (likely under `copy_trader_intel/` or `paper_trading/`) and backfill into `trading_picks` so row-level analysis is possible
- **Option C**: Use the cumulative summary stats only — but `mutation_analysis.py`'s 3-axis (direction × timeframe × symbol) requires row-level

**Recommendation**: Option A. These 4 are 13% of the closed-pick volume vs kimi_riseoftheclaw (762) + alpha_engine (200) + ml_bg_system_f (179). Effort vs payoff is poor.

Author: claude-opus-4-7 (this session)
