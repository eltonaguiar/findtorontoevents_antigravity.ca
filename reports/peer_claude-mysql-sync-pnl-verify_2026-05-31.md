# MySQL Trading Sync — pnl_pct Verification

**Branch:** `fix/mysql-trading-sync-pnl-verify-2026-05-31`
**File:** `alpha_engine/mysql_trading_sync.py`
**Date:** 2026-05-31
**Author:** Claude Opus 4.7 (peer agent)

## Context

Per `reports/peer_claude-exit-logic-divergence_2026-05-31.md`, the MySQL
writer for `trading_picks` is one of 4 bugs producing the divergence
between `trading_picks` and `at_signal_outcomes`. The writer's payload
builder (`pick_to_row()`, formerly lines ~222-249) accepted the upstream
`pnl_pct` field verbatim with no integrity check — meaning if a producer
emitted a logically impossible value (e.g. `entry=100`, `exit=105`,
`direction=LONG`, `pnl_pct=-3.0`), MySQL would happily overwrite the
existing row with the corrupted value.

## Change

1. Import `compute_pnl(entry, exit, direction)` from
   `alpha_engine.outcome_resolver` (which already encodes the
   asset-class-aware PnL math — `(exit-entry)/entry` for LONG,
   `(entry-exit)/entry` for SHORT, returning a *fraction*).
2. In `pick_to_row()`, when `entry_price`, `exit_price`, and `direction`
   are all present:
   - Compute `expected_pct = compute_pnl(...) * 100` (`compute_pnl`
     returns fractional, `pnl_pct` column is percent).
   - Compare to the upstream `pnl`.
   - If `abs(expected_pct - upstream_pnl) > 1bp (0.01 pp)`, log a
     `WARNING` with full context and **drop the value to `None`** (we
     prefer NULL over corruption — the row will not silently overwrite
     a valid existing pnl_pct with a wrong one).
3. New run-level counter `_PNL_VERIFY_STATS = {checked, ok, mismatch,
   skipped_no_inputs}` surfaced in the sync summary line.

## Tolerance choice

`1bp = 0.01 percentage points`. Same scale as
`PNL_WIN_THRESHOLD_BY_CLASS["CRYPTO"]` in `outcome_resolver.py`. Wide
enough to absorb the upstream's `round(pnl, 4)`, narrow enough to catch
sign errors or 2x/100x misscaling.

## Safety

- Verification failures **never raise** — wrapped in a broad `try/except`
  with a `logger.warning`. The sync continues for other rows.
- If `compute_pnl` cannot be imported (e.g. tooling change in
  `outcome_resolver.py`), `_compute_pnl is None` and the verification
  short-circuits — sync behavior reverts to pre-change semantics.
- No schema change. The `pnl_pct` column stays `DECIMAL(10,4) NULL`.

## Verification

```text
$ python3 -m py_compile alpha_engine/mysql_trading_sync.py  # OK

In-process sanity (pick_to_row):
  LONG  e=100 x=105 upstream=-3.0  → pnl_pct=None  (mismatch dropped)
  LONG  e=100 x=105 upstream= 5.0  → pnl_pct=5.0   (match preserved)
  SHORT e=100 x= 95 upstream= 5.0  → pnl_pct=5.0   (match preserved)
  SHORT e=100 x= 95 upstream=-5.0  → pnl_pct=None  (mismatch dropped)
  LONG  no exit_price upstream=2.5 → pnl_pct=2.5   (verify skipped)
stats: {checked: 4, ok: 2, mismatch: 2, skipped_no_inputs: 1}
```

## Backup

`trading_picks` (45,710 rows) backed up to
`ejaguiar1_backups.trading_picks_bk_20260531_025622_pnlverify` before
the worktree was opened, per repo backup rule.

## Followups (out of scope for this PR)

- Once the workflow has run for a few days, query
  `SELECT id, pnl_pct FROM trading_picks WHERE pnl_pct IS NULL AND
   status NOT IN ('ACTIVE','OPEN')` and grep the workflow logs for the
  "pnl_pct verify mismatch" warnings to identify the upstream sources
  emitting bad pnl_pct — that's the *real* fix.
- The remaining 3 bugs in
  `reports/peer_claude-exit-logic-divergence_2026-05-31.md` still need
  separate PRs.
