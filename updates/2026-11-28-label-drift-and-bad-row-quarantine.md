# Label drift repaired and provably-bad rows quarantined

**Date:** 2026-11-28
**Databases:** `ejaguiar1_stocks` (mutated) → `ejaguiar1_backups` (12 snapshots, written first)
**Tables:** `trading_picks`, `at_raw_picks`, `at_signal_outcomes`

## 1. What was still broken after the enum normalisation

The `trading_picks.category` enum fix earlier today cleaned 49,570 rows, but two
defects remained:

**Missing labels.** `trading_picks` carried 2,667 rows with `category=''`; 91% of
them are `etf_all_strategies` ETF rows whose emitter never set a class, so the whole
ETF cohort was invisible to every per-class aggregate. `at_raw_picks` held 793
`UNKNOWN`; `at_signal_outcomes` held 216 `''` (the ENUM's *invalid value*, meaning a
writer inserted a class the column cannot store) plus 29 `UNKNOWN`.

**Contradicted labels.** 59 rows filed a `*-USDT/USDC/BUSD` pair under
`EQUITY`/`COMMODITY`/`FOREX`. The symbol alone proves the class is wrong.
(`SHIBUSDT` as `COMMODITY` was the clearest case.)

**Bad rows.** The class audit flagged impossible brackets and clamped PnLs. Inspecting
samples changed the remedy, and that distinction is the most important part of this fix:

| sample row | what is wrong |
|---|---|
| `KAITOUSDT` LONG, entry 0.7858, TP 0.8153 **hit**, pnl **+3.75%**, `stop_loss` 1.3482 | the trade, the TP and the +3.75% are all **correct**. Only the stop is garbage — it sits 72% *above* entry. |
| `SPY` SHORT, entry 749.17, TP 764.15, SL 741.68 | both bracket legs are on the wrong side for a short. |
| `SHIBUSDT` COMMODITY, entry 0.00000475, exit 4016.41, pnl **999999.9999** | unusable row: clamped sentinel, and mislabelled. |
| `ADAUSDT` `TP_HIT` with pnl **−0.0102** | unusable row: a take-profit cannot realise a loss. |

So a single "quarantine everything invalid" pass would have deleted 539 *valid*
outcomes. That is why the fix has two actions instead of one.

## 2. What changed

### `tools/backfill_unknown_category.py` — rewritten

- Now covers all three ledger tables (`trading_picks.category`,
  `at_raw_picks.asset_class`, `at_signal_outcomes.asset_class`).
- Two passes: **missing** (`NULL` / `''` / `'UNKNOWN'`) and **contradicted**
  (`*-USDT` pair under a non-crypto class).
- Resolution is deterministic only: a `SOURCE_FORCE` rule where the emitter is
  unambiguous (`etf_all_strategies → ETF`, `goldmine_meme → MEMECOIN`,
  `polymarket_bts_consensus_v1 → PREDICTION_MARKET`), otherwise
  `alpha_engine.config.detect_asset_class(symbol)`. Anything unresolved is reported and
  left alone — **nothing is guessed**.
- Clamps to the column's real ENUM: `at_raw_picks`/`at_signal_outcomes` have no
  `INDEX` or `PREDICTION_MARKET` member, so those are clamped to `UNKNOWN` rather than
  writing the ENUM's invalid value.
- PK is discovered per table (`at_raw_picks` has no `id` column).
- Snapshots every affected full row to `ejaguiar1_backups` before any UPDATE, then
  writes set-based, PK-keyed chunks.

### `tools/quarantine_bad_rows.py` — new

Two separate actions, each with its own snapshot:

**Quarantine** (row is unusable → copy to backups + ledger + `exit_price`/`pnl_pct`
NULLed, plus the `intrabar_*` mirror on `at_signal_outcomes`):

| rule | definition |
|---|---|
| `R1_pnl_sentinel` | `ABS(pnl_pct) >= 999999` |
| `R3_sign_conflict` | a **WIN** label (`TP_HIT`/`WON`) with `pnl < 0` |
| `R4_nonpositive_exit` | terminal row with `exit_price <= 0` |
| `R5_magnitude` | `ABS(pnl_pct) > 1000` (>10x inside one trade = scale corruption) |
| `R6_stop_out_no_stop` | labelled `SL_HIT` while the stop sat on the wrong side of entry |

**Bracket repair** (field is unusable, row is kept → NULL the field, never recompute):
`B1_bad_stop` (stop on the wrong side of entry), `B2_bad_take_profit` (TP on the wrong
side of entry).

Two rules were **narrowed during the dry run because they were false-positive machines**:

- `R4` originally included `exit_price IS NULL`. That matched **2,184** `trading_picks`
  rows that simply store a realised PnL without an exit price — perfectly normal, not a
  defect. Now only `exit_price <= 0`.
- `R3` originally also flagged `SL_HIT`/`LOST` with `pnl > 0`. That is exactly what a
  **trailing stop** produces, so it would have deleted real wins. Now only the WIN-label
  direction (unambiguous); the mirror case is *reported* (89 + 2 rows) and never mutated.

Deliberately **not** quarantined: rows whose `|pnl|` is merely large (`TONUSDT`
1.238 → 2.47). The local OHLCV cache covers ~331 symbols and comparing a June entry to a
November close is not a valid test, so "implausible versus an external price" never
triggers a mutation here — only internal contradictions do.

## 3. Backups written before any mutation (12 tables in `ejaguiar1_backups`)

| backup table | rows |
|---|---:|
| `trading_picks_category_enum_20261128T025107Z` | 49,570 |
| `trading_picks_category_alias_backup_20261128_025118` | 49,570 |
| `trading_picks_label_fill_20261128T025617Z` | 2,676 |
| `at_raw_picks_label_fill_20261128T025617Z` | 829 |
| `at_signal_outcomes_label_fill_20261128T025617Z` | 260 |
| `at_signal_outcomes_quarantine_20261128T025630Z` | 86 |
| `trading_picks_quarantine_20261128T025630Z` | 26 |
| `at_signal_outcomes_bracket_repair_20261128T025630Z` | 320 |
| `trading_picks_bracket_repair_stop_loss_20261128T025712Z` | 1,554 |
| `trading_picks_bracket_repair_take_profit_20261128T025712Z` | 1,492 |
| `trading_picks_quarantine_20261128T025658Z` / `…025712Z` | 15 / 15 |

The last two are no-op snapshots from the two runs that aborted on an archive bug (see
§6); the rows were already neutralised. Every count was verified against the expected
row count at copy time and reads back equal now.

Rollback for the bracket repair, for example:

```sql
UPDATE trading_picks p
  JOIN ejaguiar1_backups.trading_picks_bracket_repair_stop_loss_20261128T025712Z b
    ON p.id = b.id
   SET p.stop_loss = b.stop_loss;
```

## 4. What was applied

**Labels — 3,765 rows relabelled**, none guessed:

| table | filled | via source rule | via symbol detection | left unclassifiable |
|---|---:|---:|---:|---:|
| `trading_picks` | 2,676 | 2,442 | 234 | 31 |
| `at_raw_picks` | 829 | — | 829 | 8 |
| `at_signal_outcomes` | 260 | — | 260 | 0 |

Post-state label sets (exact, `CAST(... AS BINARY)`):

- `trading_picks`: FOREX 64,664 · CRYPTO 43,971 · COMMODITY 20,408 · EQUITY 14,560 ·
  INDEX 3,744 · **ETF 3,553** · BOND 1,821 · FUTURES 973 · PREDICTION_MARKET 470 ·
  MEMECOIN 156 · `''` **31** (was 2,667)
- `at_raw_picks`: `UNKNOWN` 793 → **8**
- `at_signal_outcomes`: `''` 216 → **0**, `UNKNOWN` 29 → **0**

**Quarantine — 112 rows** (`at_signal_outcomes` 86, `trading_picks` 26). Ledger
(`ejaguiar1_stocks.data_quarantine`):

| table | rules | rows |
|---|---|---:|
| `at_signal_outcomes` | `R3_sign_conflict` | 64 |
| `at_signal_outcomes` | `R6_stop_out_no_stop` | 17 |
| `at_signal_outcomes` | `R4_nonpositive_exit` | 3 |
| `at_signal_outcomes` | `R1+R5+R6` (SHIBUSDT/COMMODITY) | 1 |
| `at_signal_outcomes` | `R5_magnitude` | 1 |
| `trading_picks` | `R6_stop_out_no_stop` | 15 |
| `trading_picks` | `R4_nonpositive_exit` | 11 |

**Bracket repair — 3,905 field values NULLed** across 2,283 distinct rows
(`trading_picks` 1,554 stops + 1,492 TPs over 1,619 rows; `at_signal_outcomes` 539 stops
+ 320 TPs over 664 rows). No value was recomputed or invented.

## 5. Measured effect (disclosed, not just claimed)

Per-class PnL over rows that still carry a PnL, before → after this repair:

`at_signal_outcomes`:

| class | n | mean pnl % |
|---|---|---|
| CRYPTO | 21,418 → 21,421 | **0.9747 → 0.1065** |
| FOREX | 2,224 → 2,220 | 0.0278 → 0.0277 |
| EQUITY | 754 → 884 | 0.2088 → 0.1994 |
| COMMODITY | 542 → 537 | **+1844.96 → −0.0579** |
| ETF | 224 → 241 | −0.0138 → −0.0116 |
| FUTURES | 161 → 159 | 0.0357 → 0.0377 |
| BOND | 83 → 102 | −0.0078 → 0.0045 |
| MEMECOIN | 129 → 129 | −0.5074 → −0.5074 |

The two headline numbers are both *corrections*, and both flatter-then-correct in the
uncomfortable direction: COMMODITY's mean was **+1,845% per trade** purely because of one
clamped `SHIBUSDT` row (999,999.9999) sitting in a 542-row cohort; CRYPTO's mean was
~9x inflated by two scale-corrupt rows (ARBUSDT +18,611%, and the same sentinel family).
Neither class was ever as profitable as the raw table said. `EQUITY`/`BOND`/`ETF` n grew
because rows previously filed under `''`/`UNKNOWN` are now in their correct class.

`trading_picks`: CRYPTO 27,962 → 27,992 · FOREX 22,801 → 22,793 · EQUITY 8,230 → 8,278 ·
COMMODITY 7,983 → 7,973 · FUTURES 732 → 732 · ETF 488 → 561 · INDEX 519 → 519 ·
BOND 361 → 380 · MEMECOIN 134 → 133 · `''` 166 → **1**.

## 6. Verification

| check | result |
|---|---|
| `py_compile` both tools | OK |
| Label fill re-run | `0 updatable` in all three tables, 39 unclassifiable reported |
| Quarantine post-state | `0 row(s) matching, 0 bracket(s) invalid` in both tables |
| Quarantined rows still carrying a PnL | **0** (`trading_picks`), **0** (`at_signal_outcomes`) |
| Sanity: nulled-bracket rows holding a stop with no entry/direction | 0 |
| Backup parity | 12/12 tables read back equal to the expected row count |
| Ledger uniqueness | 4,047 → 2,395 rows after removing duplicates left by the aborted runs |

Bugs found and fixed while doing this (each cost a partial run, none lost data — every
abort happened before its UPDATE):

1. `tools/safe_db_archive.py` — hardcoded `stocks`/`backups` passwords no longer
   authenticate; now resolves via `tools/db_env`.
2. Cloned DDL failed with **errno 1824** (`at_raw_picks` → `at_aggregation_runs` FK does
   not exist in the archive schema). Both snapshot helpers now strip FK clauses.
3. Cloned DDL failed with **errno 3822** (duplicate CHECK constraint name): every
   snapshot in a run shared the timestamp suffix, so the quarantine and bracket tables
   collided on `chk_pnl_sign_coherence_<stamp>`. The suffix is now derived from the
   unique destination table name.
4. `fetchall()` returns a tuple under `DictCursor`; `rows.extend(...)` broke the
   post-state re-scan.

## 7. Known remaining work

- **31 `trading_picks` rows and 8 `at_raw_picks` rows still unlabelled.** These are
  genuinely undecidable by symbol: `JTO-USD2`, `DEX:67`, `DEX:IF`, `DEX:CBUCKS`,
  `DEX:USWR`, `DEX:USOH`, `BRK-B`, `USD-JPY`, `USD-CHF`. Needs an emitter fix or a
  manual decision, not a guess.
- **89 + 2 rows with a loss label and a positive PnL** (possible trailing stops) are
  reported only. If they are *not* trailing stops, they are mislabelled and should be
  quarantined — that needs a decision on whether this system uses trailing stops.
- The 18 `SL_HIT` long-side / 13 short-side rows whose stops were invalid are handled,
  but the **writer that produced inverted brackets is still unidentified** — the repair
  is data-level. `mysql_trading_sync` should reject a bracket on the wrong side of entry
  at INSERT time so this stops regrowing.
- `data_quarantine.source_id` uses the server default collation
  (`utf8mb4_0900_ai_ci`) while `trading_picks.id` is `utf8mb4_unicode_ci`, so joins
  between them need an explicit `COLLATE`. Not harmful, but it will bite the next agent.
