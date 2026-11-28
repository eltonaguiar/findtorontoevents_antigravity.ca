# trading_picks.category — normalised to one canonical enum

**Date:** 2026-11-28
**Class affected:** all (CRYPTO / EQUITY / FOREX / ETF / BOND / COMMODITY / FUTURES + INDEX / MEMECOIN / PREDICTION_MARKET)
**Table:** `ejaguiar1_stocks.trading_picks`

## What was broken

A live survey of `trading_picks.category` found **20 distinct raw values for 11 canonical
classes**. The column collation is `utf8mb4_unicode_ci`, so the table *read* as if it had one
bucket while every exact string compare — and every JSON payload that carried the raw label —
saw two or more:

| raw label | rows | canonical target |
|---|---:|---|
| `FOREX` | 48,601 | *(already canonical)* |
| `CRYPTO` | 27,818 | *(already canonical)* |
| `crypto` | **16,113** | `CRYPTO` |
| `forex` | **16,070** | `FOREX` |
| `COMMODITY` | 11,810 | *(already canonical)* |
| `EQUITY` | 10,778 | *(already canonical)* |
| `commodity` | **8,608** | `COMMODITY` |
| `index` | **3,744** | `INDEX` |
| `equity` | **3,707** | `EQUITY` |
| `''` (empty) | 2,667 | *not a label — left alone* |
| `BOND` | 1,616 | *(already canonical)* |
| `ETF` | 931 | *(already canonical)* |
| `FUTURES` | 537 | *(already canonical)* |
| `prediction_market` | **469** | `PREDICTION_MARKET` |
| `futures` | **434** | `FUTURES` |
| `bond` | **185** | `BOND` |
| `meme` | **119** | `MEMECOIN` |
| `etf` | **119** | `ETF` |
| `MEMECOIN` | 23 | *(already canonical)* |
| `managed_futures` | **2** | `FUTURES` |

Total 154,351 rows; **49,570 were off-enum**.

The previous version of `tools/backfill_category_aliases.py` skipped casing-only variants on
the stated reasoning that "the collation is case-insensitive and every SQL consumer uses
`LOWER(category)` — rewriting would churn ~23k rows for zero read-side benefit". That
reasoning was wrong for two reasons:

1. Not every consumer is SQL. `alpha_engine/transaction_costs.py:109` compared
   `category == "meme"`, `concept_registry.py` and
   `dashboard_generator._get_concept_family` compared `category == "meme"` — a `MEMECOIN`
   row falls through all three.
2. The dashboard payload, JSON sidecars and `tools/asset_class_audit_checks.py::CANONICAL`
   are case-**sensitive**, so the lowercase fork was counted as label drift by the audit
   gates while being invisible to `LOWER()` SQL.

## What changed

### 1. Snapshot first (operator rule: no mutation without an `ejaguiar1_backups` copy)

Two independent restorable copies, both written **before** any UPDATE:

| backup table (in `ejaguiar1_backups`) | rows | contents |
|---|---:|---|
| `trading_picks_category_enum_20261128T025107Z` | 49,570 | **full-schema** `CREATE TABLE LIKE` snapshot of every affected row (parity confirmed). Logged in `reports/db_archives_log.md` |
| `trading_picks_category_alias_backup_20261128_025118` | 49,570 | narrow rollback ledger: `id, old_category, new_category` |

Rollback is one statement:

```sql
UPDATE trading_picks p
  JOIN trading_picks_category_alias_backup_20261128_025118 b ON p.id = b.id
   SET p.category = b.old_category;
```

### 2. `tools/backfill_category_aliases.py` — rewritten

- `CANONICAL_ENUM` is now declared in the tool (11 members, kept in sync with
  `tools/asset_class_audit_checks.py::CANONICAL`).
- The alias map seeds itself from `{c.lower(): c for c in CANONICAL_ENUM}` so casing forks
  are normalised, then adds true synonyms (`meme → MEMECOIN`, `managed_futures → FUTURES`,
  `prediction_market → PREDICTION_MARKET`, …).
- Plans from a **distinct-value survey** instead of fetching 49,570 rows, then applies one
  **set-based** `UPDATE` per raw label — 11 statements instead of 49,570 round trips.
- The `WHERE` is keyed on `CAST(category AS BINARY) = %s`, i.e. the exact byte value. This
  is what stops the `utf8mb4_unicode_ci` collation from widening a rewrite past the bucket
  being normalised. A concurrent writer shows up as a `rowcount` delta, never a clobber.
- Post-run `verify()` re-surveys and fails loudly if any non-empty label is still off-enum.
- Empty/NULL is explicitly **not** normalised: that is a missing label, owned by
  `tools/backfill_unknown_category.py` (symbol auto-tag). 2,667 rows remain and are reported.

### 3. `tools/safe_db_archive.py` — credentials + constraint collision

Found while taking the snapshot: the tool defaulted to hardcoded `--source-pass stocks` /
`--backup-pass backups`, which no longer authenticate. It now resolves through
`tools/db_env` (`get_stocks_creds` / `get_backtests_creds` / `get_backups_creds`) unless an
override flag is passed. It also renames named `CONSTRAINT`s with the timestamp suffix —
MySQL 8 requires constraint names to be unique per schema, so the second archive of the same
table collided on `chk_pnl_sign_coherence`-style names.

### 4. `alpha_engine/mysql_trading_sync.py` — stop the regrowth

This is the single production INSERT path into `trading_picks`, so a data-only fix would have
re-drifted by morning. `_CATEGORY_CANONICAL_MAP` gained
`index → INDEX`, `meme/memecoin/meme_coin → MEMECOIN`,
`managed_futures → FUTURES`, `prediction_market(s) → PREDICTION_MARKET`; `meme` and `index`
were removed from `_CATEGORY_KNOWN_PASSTHROUGH` (only `unknown` remains).

The old passthrough comment justified itself by saying rewriting would "destroy the original
tag the flag exists to preserve". That does not hold: the read side lowercases, so
`INDEX → FUTURES` and `MEMECOIN → CRYPTO` resolve identically (proved below).

### 5. Read-side consumers of the exact string `"meme"`

- `alpha_engine/transaction_costs.py` — `category_lc in ("meme","memecoin","meme_coin")`,
  plus `memecoin`/`penny_stock` keys in `_CATEGORY_TO_COST_MODEL` and a lowercase lookup.
  Without this, a `MEMECOIN` row silently got the 0.70 % altcoin cost model instead of the
  1.00 % meme model.
- `alpha_engine/concept_registry.py` and `audit_trail/dashboard_generator._get_concept_family`
  — `category == "meme"` → `"meme" in category`.
- `audit_trail/dashboard_generator._ASSET_CLASS_HINTS` — `memecoin`/`meme_coin` added under
  the same `ASSET_CLASS_MAP_MEME_TO_CRYPTO` flag, plus an early `return None` for those keys
  when the flag is `0` so the generic `"coin"` substring needle cannot re-catch them and
  silently defeat the flag.

## Verification (all re-run after the edits)

| check | command | result |
|---|---|---|
| Compile | `py_compile` on all 6 touched modules | 6/6 OK |
| CLI smoke | `--help` on both tools | OK |
| Tests | `pytest tests/test_mysql_sync_category_inference.py tests/test_dashboard_asset_class_hints.py tests/test_transaction_cost_model.py tests/test_stocks_7_classifier_override.py tests/test_penny_meme_class_gate.py` | **60 passed** |
| Dry-run plan | `tools/backfill_category_aliases.py` | 11 labels / 49,570 rows / **0 unmapped** |
| Apply | `--apply` | `49,570 rows updated`; post-state "OK: every non-empty label is now a member of the canonical enum" |
| Live post-state | `GROUP BY CAST(category AS BINARY)` | **10 distinct non-empty labels, all canonical**; total still 154,351 |
| Snapshot parity | `COUNT(*)` on both backups tables | 49,570 / 49,570 |
| Collation proof | `COUNT(*) WHERE category='equity' AND category='EQUITY'` | 14,485 (ci, so the two forks now unify) |

Post-state distribution (reconciles row-for-row with the survey):

`FOREX` 64,671 · `CRYPTO` 43,931 · `COMMODITY` 20,418 · `EQUITY` 14,485 · `INDEX` 3,744 ·
`''` 2,667 · `BOND` 1,801 · `ETF` 1,050 · `FUTURES` 973 · `PREDICTION_MARKET` 469 ·
`MEMECOIN` 142 = 154,351.

Read-path behaviour, before vs after normalisation (synthetic ticker so only the category
hint can decide):

| input | `ASSET_CLASS_MAP_MEME_TO_CRYPTO` | result |
|---|---|---|
| `category="meme"` | unset/`1` | `CRYPTO` (unchanged) |
| `category="MEMECOIN"` | unset/`1` | `CRYPTO` (same as `meme`) |
| `category="meme"` / `"MEMECOIN"` | `0` | `EQUITY` — flag still unmaps, memes still fall through |
| `category="INDEX"` | either | `FUTURES` (unchanged) |
| `get_round_trip_cost("DOGE-USD", "MEMECOIN")` | — | `0.01` (meme model; was 0.007 altcoin) |
| `get_concept_family({"category": "MEMECOIN"})` | — | `meme_coin` (was `standard`) |

## Known remaining work (not done here)

- **2,667 rows with an empty `category`.** A missing label is not a mislabelled one;
  classifying it requires symbol-pattern inference and belongs to
  `tools/backfill_unknown_category.py`. Tracked, not silently skipped.
- **`penny` / `pennystock` map to `EQUITY`**, not `PENNY_STOCK`, matching the existing
  writer-side map. The DB currently holds **0** such rows, so this is a policy choice to
  review — not a data repair.
- `PREDICTION_MARKET` still derives to `EQUITY` in `_ASSET_CLASS_HINTS` (no hint key), the
  same as `prediction_market` did before this change. Pre-existing, unchanged by this fix.
