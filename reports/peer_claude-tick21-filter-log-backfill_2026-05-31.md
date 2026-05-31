# at_filter_log UNKNOWN backfill — NO-OP verdict

**Date:** 2026-05-31
**Agent:** claude-tick21
**Task:** finish buffy's at_filter_log UNKNOWN backfill (~27,102 remaining).

## Live counts (verbatim)

```
TOTAL_rows: 818190
asset_class='UNKNOWN' rows: 26909
source_system='UNKNOWN' rows: 0
```

Note: task brief said "source_system='UNKNOWN'" but the actual UNKNOWN
column on `at_filter_log` is `asset_class` (enum includes 'UNKNOWN'). The
26,909 figure matches the brief's ~27,102 ballpark (small drift from new
inserts since buffy's pass).

## Breakdown of the 26,909 UNKNOWN rows

```
symbol breakdown:
  '' (empty)        : 26906
  'WALLET_TRACKER'  : 3

filter_reason breakdown:
  demoted_system    : 20421  ("X excluded from consensus")
  wr_suppressed     :  4352  ("rolling WR n% < 45%")
  banned_purge      :  2133
```

Sample rows (all with `raw_pick_id=NULL`, `symbol=''`):

```
(2, agg_run_id, NULL, '', '', 'mercury2',      'wr_suppressed',  'rolling WR 0% < 45%')
(4, agg_run_id, NULL, '', '', 'signal_engine', 'demoted_system', 'signal_engine excluded from consensus')
(5, agg_run_id, NULL, '', '', 'ml_bg_a',       'demoted_system', 'ml_bg_a excluded from consensus')
```

## Verdict: NO BACKFILL POSSIBLE OR CORRECT

These rows are **aggregator-level system-policy events**, not per-symbol
pick filters:
- `raw_pick_id = NULL` → no join to `at_raw_picks` or `at_signal_outcomes`.
- `symbol = ''` → buffy's symbol→`detect_asset_class()` rule from
  `tools/backfill_unknown_category.py` (commit 1688956c7) cannot infer.
- The filter_reasons (`demoted_system`, `wr_suppressed`, `banned_purge`)
  are emitted by the aggregator when blocking an entire source_system or
  WR cohort before any per-symbol pick is considered. They have no asset
  class by construction.

The 3 `WALLET_TRACKER` rows are similarly system-level (a watcher pseudo-
symbol), not a tradeable instrument.

## Action taken

- **No backup created** (no UPDATE planned → no rollback target needed).
- **No UPDATE executed.**
- Buffy's earlier 35.5K backfill almost certainly hit per-symbol rows
  (raw_pick_id NOT NULL). The 26,909 residual is the irreducible system-
  event tail.

## Recommendation

Either:
1. Leave as-is (correct semantically; UNKNOWN means "not a per-symbol event").
2. Add a new enum value `SYSTEM` to `at_filter_log.asset_class` and migrate
   these 26,909 rows to it, so the UNKNOWN bucket truly means "we tried
   and failed to resolve" rather than "wasn't applicable."

Option 2 is a schema change and out of scope for this tick. Leaving as-is.

## Return

`FILTER_LOG:pre=26909:post_unknown=26909:resolved=0:backup=none:status=success_noop`
