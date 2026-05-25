# COMMODITY cftc Edge Cell — DB Replay Verification

**Date:** 2026-05-25
**Source artifact:** `audit_dashboard/data/top_edges_per_class.json` generated 2026-05-25T03:21:15Z
**Replay tool:** `tools/audit_pick_funnel/replay_cftc_cell.py` (calls `extract_funnel.fetch_picks` + `top_edges.expand_pick_tags` against `mysql.50webs.com / ejaguiar1_stocks`)

## Cell under test

```
asset_class = COMMODITY
cell        = conf=C0.60-0.70 & rr=RR1.0-1.5 & fam=cftc
expected    : n=136, wins=96, PF=3.283, avg_pnl=0.0257%, WR_shrunk=67.95%
```

## SQL / extractor used

The replay reuses the production extractor so the bins are byte-identical to nightly:

```sql
SELECT id, symbol, direction, strategy, entry_price, take_profit, stop_loss,
       confidence, elite_score, trust_score, category, source_system, status,
       pnl_pct, exit_price, created_at, closed_at, exit_reason
FROM trading_picks
WHERE created_at >= NOW() - INTERVAL 90 DAY
ORDER BY created_at DESC
LIMIT 5000 OFFSET <paged>;
```

Then applied client-side filters (`top_edges.expand_pick_tags`):
- `_normalize_class(category) == 'COMMODITY'`
- `_classify_status(status) IN ('WIN','LOSS')` (decisive only — `WON/WIN/TP_HIT/CLOSED_TP` vs `LOST/LOSS/SL_HIT/CLOSED_SL`)
- `conf_band(confidence) == 'C0.60-0.70'` (0.60 ≤ conf < 0.70)
- `rr_band(entry, tp, sl, direction) == 'RR1.0-1.5'`  (1.0 ≤ R:R < 1.5)
- `strategy_family(strategy) == 'cftc'` (matches when "cftc" appears in `strategy` and earlier keyword tests fail)

## Replay result

```
[replay] fetched 45365 rows from trading_picks (90d)
[replay] COMMODITY cftc-family decisive picks: 145
[replay] cftc-family decisive (all classes):    145
[replay] matched cell rows: n=136, wins=96
[replay] PF=3.283  avg_pnl%=0.0257  WR_shrunk%=67.95
[replay] expected:   n=136  wins=96  PF=3.283  avg=0.0257  WR_shrunk=67.95
[replay] strategy samples in cell: ['cftc_cot_commercial_signal']
```

**Verdict: EXACT MATCH on every metric.** n / wins / PF / avg_pnl / WR_shrunk all replicate to the displayed precision.

## Notes / cross-checks

- All 145 decisive cftc-family picks are COMMODITY (no leakage to other classes). The 9-pick gap between 145 and 136 is picks that fail the rr=RR1.0-1.5 OR conf=C0.60-0.70 cells — they sit in adjacent bins.
- Only one strategy string feeds the family: `cftc_cot_commercial_signal`. The `cot` family in the next-best edge (n=125) is a sibling reading the same CFTC COT report under a different naming convention.
- The earlier 0-row replay was almost certainly run against `dashboard_data.json::picks.recent_closed` (capped at ~200 rows, post-sampling) instead of the raw `trading_picks` table. The raw table is the right source — `extract_funnel.fetch_picks` does not sample.
- Small avg_pnl (0.0257%) + high PF (3.28) is **mathematically consistent** with the 70.6% raw WR and the avg_win/avg_loss ratio of ~1.34 implied by `PF = (WR / (1-WR)) * (avg_win / avg_loss)`. This is a high-frequency CFTC positioning scalp — tiny per-trade edge, lots of trades, big PF.

## Conclusion

The COMMODITY `cftc` cell in `top_edges_per_class.json` is faithful to the DB. The edge is real (n=136 is above the n>=20 PROVEN floor) and is driven by a single strategy (`cftc_cot_commercial_signal`) reading Commitments of Traders commercial-hedger positioning. Single-strategy concentration is a risk to flag for the ops review even though the per-trade math is sound.
