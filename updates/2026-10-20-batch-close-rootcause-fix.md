# Batch-close root cause + fix (2026-10-20)

Owner: Freebuff/Buffy. Branch `buffy/batch-close-rootcause` (worktree
`wt-freebuff-batchclose`, off `origin/main`). **PR opened, not merged.**

## What was broken

Two defects in how closed picks get their exit price/time, confirmed against the
live payload (`findtorontoevents.ca/audit/data/dashboard_data.json`,
`generated_at=2026-10-20T00:41:39Z`, `picks.recent_closed` n=3500):

1. **Batch-close timestamps.** Every resolution path in
   `audit_trail/universal_pick_resolver.py` stamped `resolved_at = now`
   (line 1113 `now = datetime.now(timezone.utc)`), i.e. the **resolver run
   time**, not the true exit time. All picks resolved in one run therefore shared
   one identical close minute. Live example at `2026-10-20T00:02:50Z`:
   - MomentumEMA **73** rows (39 TP_HIT + 30 SL_HIT + 4 TIME_EXIT) — the TP/SL
     hits occurred on *different* intrabar bars but all carried the run-time stamp.
   - MeanReversionBB **29** rows (all TIME_EXIT), plus stocksunify2/clone rows.

2. **Fabricated flat-0% closes.** 38 rows in the payload carry
   `exit_price=0.0, pnl_pct=0.0` (MeanReversionBB FOREX, stocksunify2 EQUITY) —
   a failed price fetch written as a literal `0.0`. A zero exit price is a fetch
   failure, not a flat trade.

Validator `tools/check_batch_closes.py` on the live payload: **137 defects**
(many `luxalgo_confluence` same-minute clusters across Sept–Oct + the 00:02 batch
+ 38 zero-price rows). Pre-fix baseline recorded.

## Where the 0.0 actually comes from (the "second resolver")

- `tools/mysql_resolve_at_pick_outcomes.py` (the DB-side `at_pick_outcomes`
  writer) is **clean** — it returns `None` when `get_close_on_or_after` finds no
  price (lines 233-236) and never writes `0.0`.
- The `0.0` rows come from the **JSON-side** `universal_pick_resolver.py` TIME_EXIT
  path. Current `main` already guards this with `_priceless_close()` (line 264,
  added 2026-10-18, whose own docstring cites the same 38-row defect) → writes
  `None`. The live payload still shows `0.0`, so **production is running a
  pre-2026-10-18 resolver copy**. The code fix exists on main; it is a deployment
  gap, not a code gap. Tracked as an issue.

## What I changed (this PR)

`audit_trail/universal_pick_resolver.py`:
- Added `_exit_ts_str(pick, now)` helper.
- `_check_tp_sl_intrabar` now records the first-touch bar's timestamp on the pick
  (`pick["_intrabar_exit_ms"]`, same side-channel convention as
  `_intrabar_ambiguous`). The TP/SL path stamps `resolved_at` with that **true
  bar time** (falls back to run-time for close_approx / unstamped bars). The
  strict 3-tuple return contract is **unchanged**.
- TIME_EXIT (both the no-live-price branch and the `_priceless_close` branch):
  when there is no trustworthy price, status is now **`UNRESOLVED_NO_PRICE`**
  (never a `0.0` flat). TIME_EXIT keeps **run-time for both** the price and the
  timestamp (consistent — never mixes deadline-time with run-time price) and sets
  **`exit_time_estimated=true`** so consumers keep these out of PF/WR until a
  historical-bar exit price at `pick_dt+max_hold` is wired in (contingency).

New tools:
- `tools/export_closed_picks_full.py` — nightly **uncapped** read-only export of
  resolved `at_pick_outcomes` → `audit_dashboard/data/closed_picks_full.json`;
  logs `db_count` and `exported_count` and exits 1 on mismatch (removes the
  dashboard's `MAX_CLOSED_PICKS=3500` blind spot).
- `tools/check_batch_closes.py` — operational gate: reports any strategy with
  >3 same-minute closes and any `exit_price=0.0` rows; exit 1 if present.

New test: `tests/test_batch_close_exit_time.py` — **4 passed**. Locks that 20
picks resolved in one run on different bars yield **20 distinct** `resolved_at`
(≥15 required), that same-bar hits still legitimately cluster, close_approx falls
back to run-time, and priceless closes are detected.

## Verification

- `py_compile` clean on all touched files.
- `pytest tests/test_batch_close_exit_time.py` → 4 passed.
- Functional: a TP first touched on bar `2026-10-19T14:30Z` now resolves with
  `resolved_at=2026-10-19T14:30:00Z`, **not** the run-time `2026-10-20T00:02:50Z`.

## Validation (post-deploy, needs a re-resolve against historical bars)

Run `python tools/check_batch_closes.py --payload <live payload>` after the fixed
resolver re-resolves. Expect: the TP/SL same-minute clusters (MomentumEMA et al.)
disperse to their true bar times; `exit_price=0.0` count → **0** (rows become
`UNRESOLVED_NO_PRICE`); residual TIME_EXIT same-minute clusters reflect genuine
shared deadlines (batch issuance) and are `exit_time_estimated=true`.

## Contingency / open items

- **TIME_EXIT historical-bar exit price** not wired (needs bar lookup at
  `pick_dt+max_hold`); rows are `exit_time_estimated=true` and excluded from
  PF/WR. Follow-up.
- **Production resolver is stale** (pre-2026-10-18 `_priceless_close`). The code
  is on main; redeploy + re-resolve is what clears the live `0.0` rows. Issue filed.
- Historical batch rows already persisted with run-time stamps are **left as-is**
  (recorded decision, mirrors the 2026-06-10 entry-anchored precedent) — only new
  resolutions get true timestamps.

## Files changed

- `audit_trail/universal_pick_resolver.py` (true-exit-time + UNRESOLVED_NO_PRICE)
- `tools/export_closed_picks_full.py` (new, uncapped nightly export)
- `tools/check_batch_closes.py` (new, operational gate)
- `tests/test_batch_close_exit_time.py` (new, 4 tests)
- `updates/2026-10-20-batch-close-rootcause-fix.md` (this doc)
