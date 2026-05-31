# Proposal — 100x Unit-Drift Dedup of `at_signal_outcomes`

**Date:** 2026-05-31
**Author:** Claude Opus 4.7 (subagent)
**Branch:** `fix/at-signal-outcomes-100x-dedup-2026-05-31`
**Worktree:** `/tmp/wt_100x_dedup` (off origin/main)
**DB:** `ejaguiar1_stocks.at_signal_outcomes`
**Source incident:** `reports/peer_claude-exit-logic-divergence_2026-05-31.md`

## Status

**DRY-RUN ONLY — no DELETE executed. Awaiting operator approval.**

## Summary

The duplicate-detection grouping `(symbol, direction, entry_price, exit_price)` on rows where `pnl_pct IS NOT NULL AND exit_price IS NOT NULL` returns:

| Metric | Value |
| --- | --- |
| Duplicate groups (cnt > 1) | 1,589 |
| Rows in duplicate groups | 100,257 |
| Groups with 100x drift (max/min abs(pnl) in 99..101) | **438** |
| Pure-duplicate groups (same pnl, no 100x — out of scope) | 1,147 |
| Rows proposed for DELETE (decimal-scale, ~100x smaller magnitude) | **5,498** |
| Rows to KEEP (percent-scale, ~100x larger magnitude) | 14,591 |

The decimal-scale rows are the unit-drift artifact: when the resolver emitted `pnl_pct` as a fraction (0.025 = 2.5%) instead of percent (2.5 = 2.5%), the row was written 100x smaller. These are double-bookings of the same trade.

## Example (matches incident report)

```
symbol=JTOUSDT direction=LONG entry=0.33610 exit=0.32770
  41 rows total. pnl_pct contains both -2.5000 AND -0.0250.
  ratio max/min = 100.0
  -> KEEP the -2.5000 rows (percent-scale, correct)
  -> DELETE the -0.0250 rows (decimal-scale, 100x drift)
```

Other confirmed 100x groups (selected):

| Symbol | Dir | Entry | Exit | cnt | max\|pnl\| | min\|pnl\| | ratio |
| --- | --- | --- | --- | --- | --- | --- | --- |
| COST | LONG | 1028.30005 | 1003.83002 | 61 | 2.3797 | 0.0238 | 99.99 |
| AVGO | LONG | 411.32001 | 419.76501 | 61 | 2.0531 | 0.0205 | 100.15 |
| GOOGL | LONG | 385.42999 | 392.13000 | 61 | 1.7383 | 0.0174 | 99.90 |
| JTOUSDT | LONG | 0.33610 | 0.32770 | 41 | 2.5000 | 0.0250 | 100.00 |
| STGUSDT | LONG | 0.24280 | 0.23673 | 40 | 2.5000 | 0.0250 | 100.00 |
| KATUSDT | LONG | 0.01215 | 0.01185 | 40 | 2.5000 | 0.0250 | 100.00 |

## Backup (DONE)

Full snapshot of all 100,257 rows in the 1,589 duplicate-group set has been written to:

```
ejaguiar1_backups.stocks__at_signal_outcomes_100x_dedup_20260531
```

Backup row count verified: **100,257**.

This is a superset of the proposed DELETE set (5,498) — it preserves the entire affected duplicate cohort (both 100x and pure-dup groups), so a full restore is possible if needed.

## Proposed action (NOT YET EXECUTED)

For each of the 438 groups where `max(abs(pnl_pct)) / min(abs(pnl_pct))` lies in `[99, 101]`:

1. Within the group, mark every row whose `abs(pnl_pct) <= min_abs * 1.01` as a DELETE candidate (the decimal-scale row).
2. Keep every row whose `abs(pnl_pct) >= max_abs * 0.99` (the percent-scale row).
3. Zero-pnl rows are left untouched.

Total candidates: **5,498 row deletions** by `id`.

Proposed SQL:

```sql
-- (Equivalent batched DELETE by id, list materialized in /tmp/100x_delete_ids.txt)
DELETE FROM at_signal_outcomes WHERE id IN (<5498 ids>);
```

Out of scope for this PR: the 1,147 pure-duplicate groups (same `pnl_pct`, no 100x drift) — those need a separate investigation since they may be legitimate re-emissions or a different bug class.

## Operator checklist before approving DELETE

- [ ] Confirm backup table `ejaguiar1_backups.stocks__at_signal_outcomes_100x_dedup_20260531` is intact (100,257 rows).
- [ ] Spot-check 3-5 sample groups in `/tmp/100x_dedup_plan.json` (e.g. JTOUSDT, COST, AVGO).
- [ ] Confirm dashboard / strategy-stats consumers will tolerate the row drop (deletes only over-counted losing rows in the cases sampled; effect: WR up, PF up, sample count down).
- [ ] Sign-off here, then re-run the executor with `--confirm` (operator to provide).

## Reproducer

```bash
# from repo root, in this worktree:
cd /tmp/wt_100x_dedup
cat /tmp/100x_dedup_plan.json   # full plan
wc -l /tmp/100x_delete_ids.txt  # 5498
```

Plan JSON and delete-id list are in `/tmp/` only (not committed) to avoid leaking large id lists into git.
