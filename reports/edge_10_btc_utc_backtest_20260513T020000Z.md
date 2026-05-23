# Edge #10 BTC UTC-Hour Filter — Backtest Validation — 2026-05-13T02:00Z

**Spec:** Validate memory `project_clean_data_symbol_wr` claim that:
- 22 UTC = 61.2% WR (peak)
- 08-09 UTC = sub-30% (death zone)
- NS-C filter (skip 8-9) → +14pp class-WR lift on CRYPTO

**Tool:** `tools/backtest_btc_utc_hour_filter.py` — reads
`alpha_engine/data/closed_picks.json` and bins CRYPTO terminal picks
by entry-hour UTC.

**Sample:** 792 CRYPTO picks with valid timestamps; 600 with valid pnl_pct.
Min-n=10 per hour (small but largest available locally without DB access).

## Memory claim — **FALSIFIED**

| Hour UTC | Memory claim | Actual (this backtest) | Verdict |
|---|---|---|---|
| 22 UTC | 61.2% WR (peak) | **42.9%** WR (n=14) | **WRONG direction** |
| 8 UTC | sub-30% | 38.5% WR (n=13) | partial — below 50% but above 30% |
| 9 UTC | sub-30% | **33.3%** WR (n=21) | confirmed |

NS-C filter (skip 8-9 UTC) live lift: **+1.11pp** (53.83% → 54.95%) NOT
the +14pp claimed. Filter is still net-positive but the marketing claim
was inflated by an order of magnitude.

## Actual hot/cold hours from live data (n>=10)

### TOP 5 HOTTEST (sample-thin caveat — most n<25)

| Hour | n | WR % | PF | Classification |
|---|---|---|---|---|
| 2 UTC | 10 | **90.0** | 2.87 | GOLDEN_HOUR (very thin) |
| 23 UTC | 15 | 80.0 | 0.32 | GOLDEN_HOUR (PF concerning) |
| 14 UTC | 17 | 76.5 | 0.62 | GOLDEN_HOUR (PF<1 = avg-loss wins) |
| 21 UTC | 17 | 70.6 | 1.63 | GOLDEN_HOUR (cleanest) |
| 16 UTC | 45 | 62.2 | 1.17 | GOLDEN_HOUR (largest n) |

### BOTTOM 5 COLDEST

| Hour | n | WR % | PF | Classification |
|---|---|---|---|---|
| **6 UTC** | 13 | **23.1** | 0.06 | **REAL DEATH ZONE** |
| 9 UTC | 21 | 33.3 | 0.12 | DEATH_ZONE |
| 8 UTC | 13 | 38.5 | 1.29 | BELOW_COIN_FLIP |
| 22 UTC | 14 | 42.9 | 1.01 | BELOW (memory wrongly called peak) |
| 3 UTC | 23 | 43.5 | 0.19 | BELOW (large drag) |

## Recommended NS-C v2

Current NS-C filter skips hours (8, 9). Based on actual data:

| Skip set | n_skipped | Lift estimate |
|---|---|---|
| (8, 9) — current | 34 | +1.11pp |
| **(6, 8, 9)** — extend per real death zone | 47 | est +1.8-2.5pp |
| (3, 6, 8, 9) — aggressive | 70 | est +2.5-3pp BUT 3 UTC sample may be regime-specific |

**Recommendation:** Keep current (8, 9) until n>=100 per hour available
(DB query needed). Promote (6, 8, 9) skip-set only after:
1. DB-level backtest validates 6 UTC sub-30% holds across 6+ months
2. Sample n>=100 at hour 6 (currently 13)

## Why memory claim drifted

Possibilities:
1. **Memory was from a different dataset** (DB `ejaguiar1_stocks.trading_picks` vs
   local `closed_picks.json` post-resolver-v2 filter)
2. **Memory was from pre-noise-filter era** when status enum + pnl filtering
   was different (the "61.2% at 22 UTC" pre-cleanup)
3. **Memory drift** — claim was approximate and degraded over multiple cycles

## Action items added

- **AA-8** Run same backtest against `ejaguiar1_stocks.trading_picks` DB
  via `gh workflow run ab_analysis.yml` to get authoritative sample
  (likely 5-10x larger than the 600 local-resolved subset)
- **AA-9** Update memory `project_clean_data_symbol_wr` after AA-8 confirms
  real per-hour pattern
- **AA-10** Once DB-validated, consider promoting NS-C to (6, 8, 9) skip-set

## Honest takeaway

Edge #10 IS real but smaller than memory claimed:
- Free statistical filter → +1.11pp live measured (not +14pp)
- Real death zone is 6 UTC (PF 0.06) not 8-9 UTC
- Current NS-C filter still helps but should be expanded post-validation

This is exactly the kind of "memory drift" the corrigendum pattern
catches. Updating `MEMORY.md` is the next step once DB-level data
confirms the real hot/cold map.

## NFA

Backtest output cached at `audit_dashboard/data/btc_utc_hour_backtest.json`.
Hindsight only — no real-money sizing. Replace with DB-sourced data when
A1 cron unblocks.
