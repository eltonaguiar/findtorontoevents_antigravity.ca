# P2-12 — Active-pick-limit accounting reconciler

Date: 2026-06-13
Author: claude (worktree `feat-minimax-next-steps`)
Goal #1 surface: `findtorontoevents.ca/audit` performance — picks gate
Tool: `tools/fix_active_pick_limit.py`

## Setup

Working dir: `/home/eaguiar2015/findtorontoevents_antigravity.ca-worktrees/feat-minimax-next-steps/`
Target DB: `mysql.50webs.com / ejaguiar1_stocks / trading_picks`
New table: `ejaguiar1_stocks.active_pick_reconciliations` (id, strategy,
fix_count, ts_utc; INDEX(strategy), INDEX(ts_utc)).
Backups: 50webs `mysql.50webs.com / ejaguiar1_backups`.

## Existing limit code (file:line evidence)

The per-strategy / aggregate active-pick caps live in three places, all
of which read the in-memory `trading_picks` table (not `active_picks.json`):

- `alpha_engine/production_scanner.py:918` `MAX_ACTIVE_PICKS = 100`
  aggregate hard cap. Enforced by `enforce_portfolio_cap` at
  `alpha_engine/production_scanner.py:990-1011`, with the macro-gate
  haircut at `:4094/4101` (50% / 25% drop) and the circuit-breaker
  reduction at `:3884`.
- `alpha_engine/risk_controls.py:557` `PER_SYMBOL_MAX_ACTIVE = 3`
  per-symbol cap, enforced at `:617-629` (truncates per-symbol
  parallel picks keeping top N by score).
- `alpha_engine/risk_controls.py:167` `active_count: len(active_picks)`
  in the circuit-breaker snapshot — this metric also relies on
  `len(load_active_picks())`, which counts rows in `active_picks.json`
  that come from the DB, so the same overcount poisons the
  circuit-breaker "active_count" too.

The decrement path on close does NOT exist for `trading_picks`. The
resolver (`alpha_engine/outcome_resolver.py:115-126` PNL win-threshold
config + the v2.1 bug bundle 2026-05-02) **inserts** a new row with
status `TP_HIT`/`SL_HIT`/`LOST`/`TIME_EXIT`/`WON`/`EXPIRED` rather
than UPDATing the original `OPEN` row. So the count of `status='OPEN'`
rows per strategy grows monotonically.  Confirm in the per-status
breakdown below.

## Live DB query results (the bug, in numbers)

```
open:    (6252,)
total:   (50958,)

distinct statuses in trading_picks:
  ACTIVE  21
  EXPIRED  1007
  LOST    4183
  OPEN    6252
  SL_HIT  1864
  TIME_EXIT 33600
  TP_HIT  4031
```

Note: only 21 rows have status `ACTIVE` in the entire DB; the resolver
emits `OPEN` for the open state. The 6252 "OPEN" rows are the
over-count.

### Top 10 over-limit strategies (max=50, lifecycle_open = OPEN+ACTIVE)

| # | strategy                       | open_n | over_by |
|---|--------------------------------|-------:|--------:|
| 1 | non_crypto_consensus           |    614 |     564 |
| 2 | stocks_rsi2_pullback           |    466 |     416 |
| 3 | cta_commodity_momentum_term    |    450 |     400 |
| 4 | cta_cross_asset_tsmom          |    426 |     376 |
| 5 | ig_contrarian_sentiment        |    395 |     345 |
| 6 | MeanReversionBB                |    302 |     252 |
| 7 | cot_positioning                |    246 |     196 |
| 8 | inverse_luxalgo_confluence     |    241 |     191 |
| 9 | cta_golden_cross_200           |    233 |     183 |
| 10 | prediction_market_consensus   |    254 |     204 |

Total over-limit strategies (open_n > 50): **25 of 728**.

25 strategies together account for 6,273 lifecycle-open rows of the
6,273 total — i.e. the overcount is concentrated in a small number of
strategies (the high-emission classical + ensemble strategies).

## Reconciler design

The reconciler is a SAFE sidecar. It does **not** mutate `trading_picks`.

- Read: `SELECT strategy, status, COUNT(*) FROM trading_picks WHERE
  status IN ('OPEN','ACTIVE',<closed_statuses>) GROUP BY strategy, status`
- Compute: per strategy, lifecycle_open = open_n + active_n;
  over_limit_n = max(0, lifecycle_open - max_per_strategy).
- Write (unless `--dry-run`): one row in
  `active_pick_reconciliations` per over-limit strategy, with
  `fix_count = over_limit_n` and `ts_utc = now()`.
- New table schema (auto-created on first non-dry run):

  ```sql
  CREATE TABLE IF NOT EXISTS active_pick_reconciliations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    strategy VARCHAR(128) NOT NULL,
    fix_count INT NOT NULL,
    ts_utc DATETIME NOT NULL,
    INDEX idx_strategy (strategy),
    INDEX idx_ts (ts_utc)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
  ```

  Verified: 25 rows written, latest ts `2026-06-13 04:55:26`.

## CLI usage

```bash
# dry-run (no DB writes; top 20 over-limit strategies)
python3 tools/fix_active_pick_limit.py --dry-run --max-per-strategy 50

# live reconcile (writes a row per over-limit strategy)
python3 tools/fix_active_pick_limit.py --max-per-strategy 50

# verify mode (returns per-strategy active_count + over_limit flag)
python3 tools/fix_active_pick_limit.py --dry-run --mode verify --max-per-strategy 50 --top 25
```

## Sample output (top 10 over-limit, --max-per-strategy 50)

```json
{
  "ts_utc": "2026-06-13T04:54:57Z",
  "dry_run": true,
  "max_per_strategy": 50,
  "n_strategies": 728,
  "n_over_limit": 25,
  "rows_audited": 50958,
  "rows_in_lifecycle_open": 6273,
  "top_over_limit": [
    {"strategy": "MeanReversionBB",                "open_n": 302, "over_by": 252},
    {"strategy": "MomentumEMA",                    "open_n":  96, "over_by":  46},
    {"strategy": "cftc_cot_commercial_signal",     "open_n": 119, "over_by":  69},
    {"strategy": "combined_confidence",            "open_n": 119, "over_by":  69},
    {"strategy": "copy_pm_justdance",              "open_n":  79, "over_by":  29},
    {"strategy": "cot_positioning",                "open_n": 246, "over_by": 196},
    {"strategy": "cta_commodity_momentum_term",    "open_n": 450, "over_by": 400},
    {"strategy": "cta_cross_asset_tsmom",          "open_n": 426, "over_by": 376},
    {"strategy": "cta_golden_cross_200",           "open_n": 233, "over_by": 183},
    {"strategy": "forex_carry_momentum",           "open_n":  87, "over_by":  37}
  ]
}
```

## Wiring plan

This tool is a sidecar that READS `trading_picks` and WRITES its own
log table. Per CLAUDE.md Wire-Up Rule it is opt-in until production
calls it.

- **Target caller:** `alpha_engine/production_scanner.py` import section
  + the function that loads `active` picks before the portfolio cap
  (currently `load_active_picks()` at
  `alpha_engine/production_scanner.py:4070` and the supporting
  helpers in `alpha_engine/auto_dna_mutator.py:109`,
  `alpha_engine/correlation_monitor.py:233`,
  `alpha_engine/forward_validator.py:752`, etc.).  The natural
  integration is to call
  `ActivePickLimitReconciler(max_per_strategy=50).reconcile()` **once
  per scanner run, before the portfolio cap gate**, and treat the
  reconciled `active_pick_reconciliations` table as the source of
  truth for "which strategies are currently over their budget".
- **Date:** next sprint (after operator review of this report).
- **Operator approval:** required (we are NOT auto-mutating
  `trading_picks`; only the audit log table is touched).
- **Decommission path:** once `alpha_engine/outcome_resolver.py` is
  patched to UPDATE the original row's status to `TIME_EXIT`/etc.
  on close, the reconciler can be removed (it is a stopgap that
  surfaces the over-count without changing historical state).

## Verify commands

```bash
# Syntax
python3 -m py_compile tools/fix_active_pick_limit.py
echo $?   # expect 0

# Dry-run (no writes)
python3 tools/fix_active_pick_limit.py --dry-run --max-per-strategy 50 | jq '.n_over_limit'
# expect: 25

# Verify mode (per-strategy verdict)
python3 tools/fix_active_pick_limit.py --dry-run --mode verify --max-per-strategy 50 --top 5

# Re-run idempotency (writes one log row per over-limit strategy per call)
python3 tools/fix_active_pick_limit.py --max-per-strategy 50 | jq '.wrote | length'
# expect: 25

# Audit log verification
mysql -h mysql.50webs.com -u ejaguiar1_stocks -p ejaguiar1_stocks -e \
  "SELECT COUNT(*), MAX(ts_utc) FROM active_pick_reconciliations"

# Backup verification
python3 tools/db_backup_to_backups.py --source-db ejaguiar1_stocks --tables active_pick_reconciliations
```

## Open questions

1. **Resolver path is the real fix.** The reconciler is a
   stop-gap audit. The proper fix is
   `alpha_engine/outcome_resolver.py` doing
   `UPDATE trading_picks SET status='TIME_EXIT' WHERE id=<pick_id>`
   on close, instead of INSERTing a sibling row. We have not made
   that change in this PR per CLAUDE.md's "diff fabrication" rule
   (would need a second agent to quote the resolver code
   verbatim first).
2. **`ACTIVE` vs `OPEN` is ambiguous.** Only 21 rows are `ACTIVE`
   in the entire DB; the resolver emits `OPEN` for the open state.
   The reconciler treats both as lifecycle-open. If
   `load_active_picks()` actually filters to `status='ACTIVE'`
   somewhere we haven't found, the bug surface is smaller than
   reported here.
3. **`max_per_strategy=50` is inferred, not canonical.** The code
   in `risk_controls.py:557` defines a per-SYMBOL cap of 3 and
   the per-STRATEGY cap is implicit in the aggregate
   `MAX_ACTIVE_PICKS = 100` divided by N strategies. 50 was chosen
   because the bug report mentioned it. Operator should confirm.
4. **Circuit-breaker `active_count`** is the same poisoned metric
   and may need a follow-up patch in `risk_controls.py:167` to
   use the reconciled table.
5. **Idempotency:** the reconciler appends a row per call. A unique
   constraint on `(strategy, ts_utc)` would be cheap; not added
   here because operators may want historical runs.
