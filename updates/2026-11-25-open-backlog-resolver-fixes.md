# Open-backlog resolver fixes — exact diffs, ready to apply (2026-11-25)

Source: `reports/supply-bottleneck-analysis-2026-11-25.md` (S4 measurement, ~22 read-only SELECTs).
**Nothing here is applied yet — each item arms production data-writes on the next cron, so all are owner-approved-before-merge.**

## What's broken (measured 2026-11-25)

| Pool | OPEN rows | Past any 48-120h hold window | Scheduled closer? |
|---|---|---|---|
| `trading_picks` | **99,345** (of 153,366) | **94.6%** | **none that ever applies** (both bugs below) |
| `at_local_picks` | 33,515 | n/a (ingest archive, no resolver by design) | none |
| `at_raw_picks` | 180 | healthy (~4d max) | `outcome-resolver.yml` hourly — but it caps 15k/run |

Closed-supply today: 53,415 rows. Closing the backlog grows it to **~147k (+175%)** and pushes the
8 strategies currently sitting just under the n≥100 tier floor (e.g. `etf_rsi2_pullback` n=87)
across it **without lowering any threshold** (that is the recommended supply lever — not the bar).

## Fix 1 (PRIMARY) — give the hourly resolver the right table

`.github/workflows/outcome-resolver.yml`, step `MySQL stale live picks (OPEN+ACTIVE hold window)`
(cron `47 */1 * * *`). Today it runs `resolve_stale_open_picks.py` which defaults
`--table at_raw_picks` (`tools/resolve_stale_open_picks.py:643-648`, `choices=["at_raw_picks","trading_picks"]`) —
i.e. the table with **180** stale rows while the **99,345-row pool nobody points at**.

```diff
         run: |
           echo "::group::stale OPEN+ACTIVE resolver"
           python tools/resolve_stale_open_picks.py --execute --batch-size 500 --max-batches 30
+          # 2026-11-25: trading_picks has no scheduled closer at all (this call defaults
+          # --table at_raw_picks: 180 OPEN, healthy). 99,345 OPEN / 94.6% past window ->
+          # +175% closed supply. Keep the existing at_raw line untouched.
+          python tools/resolve_stale_open_picks.py --table trading_picks --execute --batch-size 500 --max-batches 30
           echo "::endgroup::"
```

- Capacity: 30×500 = **15,000 rows/run, hourly** → backlog drains in ~7h if batches stay full
  (the tool is hold-window aware; it self-limits to rows actually past window).
- Blast radius: closed counts jump; WR/PF recompute more honestly; **active list unaffected**
  (active = recent OPEN within window; the resolver only closes rows past window).
- Reload: no secrets/env change (same `env:` block).

## Fix 2 (SECONDARY) — the dedicated trading_picks closer must not dry-run forever

`.github/workflows/mysql-stale-picks-resolver.yml` (daily `25 4 * * *`), step line ~64:

```diff
-          # Determine mode from input or default to dry-run on schedule
-          DRY_RUN="${{ github.event.inputs.dry_run || 'true' }}"
+          # 2026-11-25: scheduled runs were dry-run by default, so this by-design
+          # trading_picks closer has NEVER applied (empirical: zero WIN/LOSS rows exist).
+          # Manual workflow_dispatch can still override via the dry_run input.
+          DRY_RUN="${{ github.event.inputs.dry_run || 'false' }}"
```

- Also consider `MAX_AGE` default `30` days → lower (e.g. `'3'`) to match the 48-120h hold window,
  and `BATCH` 500 → higher (tool runs once daily; 99k at +500/day would take 198 days — with
  Fix 1 as the workhorse this one is a nightly sweep, batch 2000 is a reasonable default).

## Fix 3 — stop laundering missing PnL into 0.0 (decision: sequence after Fix 1)

`alpha_engine/outcome_resolver.py:2000` coerces missing pnl → `0.0` at close; that plus emitters
closing terminal without exit prices creates the zero/constant cohorts
(`EXPIRED` 80.3% zero; `PENNY_STOCK` 94.5% NULL+0; `smart_money_accumulation` 47.7% zeros).
Backfill tooling exists but is narrow (`backfill_null_pnl.py`, run 08:06) or detect-only
(`zero_pnl_detector.py` prints, never applies, cap 500; `backfill_time_exit_pnl.py` has no workflow).

Recommended order: (1) land Fixes 1-2, (2) one careful commit: write `NULL` (not `0.0`) for
missing-exit closes + give `zero_pnl_detector.py` an `--execute` mode behind the existing
non-fatal step pattern, (3) one bounded backfill run over the constant cohorts (COHORT-LISTED in
the S4 report — never a blanket UPDATE). Risk: medium; display-shifts historical WR/PF once,
then stops moving.

## Fix 4 — stamp `trust_tier` / `smart_score` at the shared chokepoint (Smart Picks structurally 0)

65 of 66 `JSON_PICK_SOURCES` ship **neither** field → everything lands `UNPROVEN` → "Smart Picks"
can never fill. `smart_score` is read-time only (`quality_gates.py:10859`,
`dashboard_generator.py:18357`); `trust_tier` is stamped by `stamp_pick_quality.py:468,478` but
invoked for exactly one file (`alpha-engine-live.yml:268` → `active_picks.json`).

Minimal fix (S/M, no schema change): loop `python -m tools.stamp_pick_quality --file <src>` over
the `JSON_PICK_SOURCES` list in the audit generator, or stamp once at
`parent_process`-style chokepoint `mysql_trading_sync.sync()` after the JSON load loop
(`tools/mysql_trading_sync.py:884-905`) — precedent exists there (elite-score backfill, :911-915).
Then quality gates stop reporting "Smart Picks 0" as a mystery.

## Fix 5 — funnel telemetry is dead, so 1-4 can't stay measurable

`at_filter_log` 7d: 356 rejections with `incubator_strategy` 74.7% top;
`was_demoted`/`was_wr_suppressed` **never written** (0 ever); `at_pick_flow_daily.rejected_total`
= 0 for 7+ days; `pick_funnel_views` stale since 2026-05-29. Repair the ingest flag writes +
refresh the view before trusting any "reject rate" claim afterward.

## Verify after each fix

1. `gh run view <run-id> --log | grep -i "resolved\|closed"` after one cron cycle.
2. DB: `SELECT COUNT(*) FROM trading_picks WHERE status='OPEN'` — expect steady decline after Fix 1.
3. WIN/LOSS rows appear (proof Fix 2 works; today ZERO exist).
4. `/audit/` closed counts move the expected direction; `pick_funnel` rejections stop reading 0.
5. Rollback = revert the one-line change (both fixes are single-line diffs above).

## Decision matrix

| # | Change | Lines | Risk | Owner decision |
|---|---|---|---|---|
| 1 | `--table trading_picks` invocation (hourly) | +4 (1 cmd) + comment | LOW | Y |
| 2 | dry-run default `'true'`→`'false'` (daily) | 2 | MED (arms DB writes) | Y |
| 3 | NULL-not-0 close + detector `--execute` | ~20-40 py | MED | Y |
| 4 | trust_tier/smart_score stamping chokepoint | ~10-30 py | LOW-MED | Y |
| 5 | funnel flags + view repair | ~10-30 | LOW | Y |

Explicitly **not** recommended: lowering n≥100 / WR / PF thresholds; deleting history;
blanket PnL UPDATEs; resurrecting `disabled_manually` workflows.
