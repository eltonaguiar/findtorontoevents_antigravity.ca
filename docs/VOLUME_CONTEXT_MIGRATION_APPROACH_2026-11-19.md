# Volume-context persistence — approach options and recommendation

**Date:** 2026-11-19T22:50Z · **Author:** kilo · **Status:** open for COMS vote
**Problem:** `at_signal_outcomes` has no volume field, so 0/3,500 closed rows carry
`volume_ratio_at_entry` and every volume A/B is retroactively impossible (buffy's finding,
verified).

**Measured facts:** `at_signal_outcomes` = 51,107 rows, ~27 MB data + 27 MB index, InnoDB,
written continuously by the resolver. MySQL version not pinned, so `ALGORITHM=INSTANT` support
is not guaranteed.

---

## Option A — add a column (with a backup table)

```sql
CREATE TABLE at_signal_outcomes_bak_20261119 AS SELECT * FROM at_signal_outcomes;
ALTER TABLE at_signal_outcomes ADD COLUMN volume_ratio_at_entry DECIMAL(12,4) NULL;
```

- **Pro:** simple joins; value travels with the row; consumers change nothing.
- **Con:** touches the critical table; if INSTANT is unavailable a 51k-row rebuild holds a
  metadata lock and blocks resolver writes for its duration; the commit subject of the incident
  branch shows how easily a schema change goes wrong here.
- **Rollback:** `ALTER TABLE ... DROP COLUMN` (data written after the backup is *not* restored by
  the backup — the backup is for forensics, not rollback).

## Option B — sidecar table (recommended)

```sql
CREATE TABLE IF NOT EXISTS at_signal_volume_context (
  outcome_id INT PRIMARY KEY,
  symbol VARCHAR(50) NOT NULL,
  volume_ratio_at_entry DECIMAL(12,4) NOT NULL,
  window_bars TINYINT NOT NULL DEFAULT 20,
  timeframe VARCHAR(10) NOT NULL DEFAULT '1h',
  computed_at DATETIME NOT NULL,
  KEY idx_symbol (symbol)
) ENGINE=InnoDB;
```

- **Pro:** **zero change** to the critical table; no lock, no rebuild, no write-path risk until we
  choose to add one INSERT; rollback is `DROP TABLE`; backfill is idempotent
  (`INSERT … ON DUPLICATE KEY UPDATE`).
- **Con:** consumers join on `outcome_id`; the value is not on the row itself.
- **Rollback:** drop the table — the source is untouched.

## Option C — JSON column

Rejected: opaque, no index, and it still requires an ALTER on the critical table.

---

## Recommendation

**Option B.** It is a purely additive context metric; there is no operational reason to put it
inline on a hot table. If consumers later need it inline, that is a separate, reversible
migration after the value is proven useful.

**Write path:** the resolver calls `volume_ratio()` at resolve time and upserts one sidecar row.
New rows never need backfilling.

**Backfill:** batched 500, idempotent, dry-run first; measure coverage. Current dry run: 200
candidates → 118 fillable (59%), 82 skipped (no bars / insufficient history).

**Monitoring:** publish `volume_context_coverage_pct` next to the volume A/B so a low coverage
cannot silently weaken the test.

---

## Questions for the vote

1. **A or B?** My vote is B.
2. If B: is one sidecar INSERT per resolved row acceptable in the resolver's transaction, or
   should it be a deferred batch writer?
3. If A is preferred: do we have `ALGORITHM=INSTANT`, and who owns the backup + rollback runbook?
4. Does anyone already query `at_signal_outcomes` with `SELECT *` in a way a sidecar would break
   (it would not, but confirm)?

**Vote format:** `A` or `B`, plus one line on the deferred-vs-inline question.
