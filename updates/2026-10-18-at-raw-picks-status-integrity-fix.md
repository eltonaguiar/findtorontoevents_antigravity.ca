# 2026-10-18 — at_raw_picks open-status integrity: NULL status, fake 0% TIME_EXITs, and the "zero active picks" paradox

**Fix + verification record.** Three defects found while auditing `/audit` pick
quality per asset class (see `updates/2026-10-18-audit-picks-quality-per-class-review.md`
and the state-of-union card on `findtorontoevents.ca/updates/`).

## What was broken

### 1. `at_raw_picks.status` was never written — every DB-backed "active" counter read 0

`record_raw_pick()` in `audit_trail/mysql_client.py` built its `INSERT IGNORE INTO
at_raw_picks` **without the `status` column**, and the column is `enum(...)` with
`Default: None`. So every row this function ever inserted landed with
`status = NULL`.

Measured against production:

```
== all-time status histogram (at_raw_picks) ==
  WON 30682 · LOST 30601 · CLOSED 22201 · EXPIRED 11228 · ABANDONED 9682
  <NULL> 3126 · rows with status='OPEN': 0   ← never written, ever
== are NULL rows really open? ==
  status_null=True  closed_at_set=False  n=3126   ← 100% of them
  status_null=False closed_at_set=False  n=18277
  status_null=False closed_at_set=True   n=86127
```

NULL therefore means "open" unambiguously: **all 3,126 NULL-status rows have
`closed_at IS NULL`.**

Two consumers already knew this — `alpha_engine/active_picks_sync.py` queries
`(status IN ('OPEN','ACTIVE') OR status IS NULL)` for both its SELECT and its
idempotent UPDATE guard. `tools/audit_pick_funnel/build_recency_summary.py` did
not: it counted `ACTIVE_STATUSES = {"OPEN","ACTIVE"}` only, so the DB-backed
48-hour sidecar (`source = ejaguiar1_stocks.at_raw_picks (DB)`,
`fallback_mode: false`) reported **`n_active = 0` in all 9 classes** while the
dashboard showed 22 curated actives — 21 of them inside that exact window.

`tools/pick_flow_snapshot.py:115` (`WHERE status='OPEN'`) has the same blind spot.

### 2. 38 fabricated "flat" TIME_EXIT closes

`picks.recent_closed` carried 38 rows (29 FOREX + 9 EQUITY) with
`exit_reason=TIME_EXIT`, `exit_price=0.0`, `pnl_pct=0.0` against real non-zero
entries (`V` 383.9 → 0.0, `MA` 598.47 → 0.0, `EURUSD` 1.335 → 0.0), all
`source_system=stocksunify2`, all `closed_at=02:01:53Z`.

A zero exit price means the price fetch failed. `_compute_pnl` on that failure
produces either `-100%` (real entry) or `0.0` (falsy entry) — both are arithmetic
performed on a failed fetch, not a measured trade. The resolver's no-live-price
path had already been fixed on 2026-10-17 (writes `exit_price=None`), but the
generic TIME_EXIT path still wrote `exit_price=current_price` with no validity
check, so a falsy price passed straight through to the published payload.

### 3. A published claim that was wrong

The state-of-union card first said the live `dashboard_enhancements.js` was
"hand-edited" and "never came from the repo". It was byte-identical to `main`
(sha `d635bc11640d`); the comparison had been made against a stale local branch.
The defect was **committed to the repo** — a malformed nested ternary that made
the whole file fail `node --check` from 2026-10-04 until PR #733. Corrected in
the same PR that shipped the syntax fix.

## What changed

| File | Change |
|------|--------|
| `audit_trail/mysql_client.py` | `record_raw_pick()` INSERT now declares `status` and pins `'OPEN'`, so new rows stop arriving as NULL. |
| `tools/audit_pick_funnel/build_recency_summary.py` | Active = `status IN ('OPEN','ACTIVE')` **or** (`status IS NULL` and `closed_at IS NULL`) — matching `active_picks_sync.py`. The `closed_at` guard stops a NULL-status row that was already closed from being resurrected as active. |
| `audit_trail/universal_pick_resolver.py` | New `_priceless_close(exit_price, entry)` helper; the generic TIME_EXIT branch now records `exit_price=None, pnl_pct=None, _mtm="unresolved"` and logs a warning instead of publishing a fabricated 0% flat. |
| `tests/test_at_raw_picks_open_status_2026_10_18.py` | 11 regression tests pinning all three behaviours. |

Downstream effect of the second change: the outcomes writer
(`_write_outcomes_to_mysql`) already skips rows with `pnl_pct is None`, so
priceless closes are now excluded from `at_pick_outcomes` automatically instead
of entering it as `pnl=0` "flat" results.

## Verification

```
python3 -m pytest tests/test_at_raw_picks_open_status_2026_10_18.py -v
  → 11 passed
python3 -m pytest tests/test_universal_pick_resolver.py tests/test_b23_... \
  tests/test_resolver_intrabar_accuracy.py tests/test_dedup.py \
  tests/test_tradingagents_smoke.py -q
  → 31 passed, 5 skipped (pre-existing: live smoke needs TRADINGAGENTS_LIVE_SMOKE=1)
```

End-to-end through the real builder with the DB mocked to the production row
shape (NULL status, `closed_at` NULL):

```
[build_recency_summary] wrote .../pick_summary_stats_48h.json — 2 classes
  CRYPTO  touched=2  active=1  closed=1  ...
  FOREX   touched=1  active=1  closed=0  ...
FOREX n_active : 1 (was 0 before the fix)
CRYPTO n_active: 1 (was 0 before the fix)
END-TO-END: n_active now > 0 for NULL-status actives — PASS
```

Also verified: `python3 -m py_compile` on all three modified modules, and the
generated sidecar was reverted afterwards so the worktree stayed clean.

## Not done — needs a production write decision

The **3,126 legacy NULL-status rows are untouched.** The INSERT fix only stops
new NULLs; until the legacy rows are backfilled, `build_recency_summary` is the
only consumer that reads them as active (the fix that shipped). A one-time,
idempotent backfill would align every other `WHERE status='OPEN'` query too:

```sql
UPDATE at_raw_picks SET status = 'OPEN'
 WHERE status IS NULL AND closed_at IS NULL;
```

Scope: 3,126 rows, no `closed_at` rows affected (verified: every NULL row has
`closed_at IS NULL`). Deliberately **not executed** in this change — it writes to
production MySQL and needs operator sign-off.

Related open items from the same audit, not addressed here: the 38 historical
fabricated rows still sit in `recent_closed`, only AlphaEngine writes to
`at_raw_picks` (GC=F / XLB / USO / TQQQ / PA=F actives have no row at all), and
the `rapid_fire_data/active_picks.json` feed 404s.
