# Historical wrong-side stop sweep — `trading_picks`

**Date:** 2026-11-28 · **Agent:** `freebuff-deepseek-v4-1-flash-fast`
**Tables touched:** `ejaguiar1_stocks.trading_picks` (bracket fields only)
**Tool:** `tools/quarantine_bad_rows.py --table trading_picks --brackets-only --apply`

---

## 1. What was broken

The class audit's `bad_side_stops` gate counts rows whose `stop_loss` sits on the
wrong side of `entry_price` for the row's own direction. At the start of this
sweep it counted **76 rows**:

| class | rows |
|---|---|
| CRYPTO | 37 |
| EQUITY | 18 |
| FOREX | 8 |
| COMMODITY | 5 |
| ETF | 3 |
| FUTURES | 1 |
| MEMECOIN | 1 |
| *(empty category)* | 3 |

The four classes named in the audit brief (CRYPTO 37, EQUITY 18, FOREX 8,
ETF 3 = **66**) are a subset of that 76.

Two further defect shapes were invisible to the old rule, because it required
`entry_price > 0 AND stop_loss > 0` before it would look at a row:

- **191 rows with `stop_loss = 0`** (CRYPTO 187, MEMECOIN 4) — a non-positive
  level is not a price and the ingest guard rejects it, but the sweep skipped it.
- **28 rows with `stop_loss <= 0` and `entry_price <= 0`** — the same zero stop,
  on a row whose entry is also unusable. These were the 28 the audit gate still
  counted *after* the first pass, which is how the gap surfaced.

A stop of `0` is recorded-missing data, not information; the row's entry, exit,
PnL and label are untouched by removing it.

## 2. The written rule

`B1_bad_stop` / `B2_bad_take_profit` now mirror
`alpha_engine/mysql_trading_sync.py::_validate_bracket_geometry` — the guard that
rejects such brackets at INSERT since 2026-11-28. A bracket field is **NULLed**
(the row is kept) when any of these hold:

1. `field <= 0` — not a price level, whatever the entry or direction says.
2. `field` is on the wrong side of a positive entry for the row's direction:
   LONG `stop_loss >= entry` or `take_profit <= entry`;
   SHORT `stop_loss <= entry` or `take_profit >= entry`.
3. `B3_bracket_scale`: the level is more than **100x** from entry
   (`BRACKET_MAX_RATIO`, the same multiple the ingest guard uses).

Nothing is recomputed or invented: an invalid level is removed, never replaced.
Entry, exit, PnL and the terminal label are left exactly as written, so class
win rates and the PnL ledger are unaffected by this sweep.

## 3. What was done

| field | rule | values NULLed | full-row backup |
|---|---|---|---|
| `stop_loss` | B1 (wrong side + `<= 0`) | 268 | `ejaguiar1_backups.trading_picks_bracket_repair_B1_stop_loss_20261128T040424Z` (28 rows, last pass) and `..._bracket_repair_stop_loss_20261128T040355Z` (240 rows, first pass) |
| `take_profit` | B2 | 81 | `..._bracket_repair_B2_take_profit_20261128T040424Z` (28 rows, last pass) + `data_quarantine.row_json` for the 53 rows of the first pass (see §6) |
| `take_profit` | B3 (>100x) | 91 | `..._bracket_repair_take_profit_20261128T040355Z` (91 rows) |
| `stop_loss` | B3 (>100x) | 8 | `..._bracket_repair_stop_loss_20261128T040355Z` (8 rows) |

Every change is also recorded in `ejaguiar1_stocks.data_quarantine` with
`action = 'nulled_bracket'`, the rule name, the previous values and the backup
table name — 268 B1, 81 B2 and 99 B3 ledger rows for this sweep.

## 4. Verification

`python3 tools/asset_class_audit_checks.py --skip-backtests` — gate
`bad_side_stops`, measured after the sweep:

| class | before | after |
|---|---|---|
| CRYPTO | 37 | **0** |
| EQUITY | 18 | **0** |
| FOREX | 8 | **0** |
| COMMODITY | 5 | **0** |
| ETF | 3 | **0** |
| FUTURES | 1 | **0** |
| MEMECOIN | 1 | **0** |
| *(empty category)* | 3 | **0** |

Direct SQL cross-check (the audit's own predicate, all classes):
`bad stops remaining: ()` · `trading_picks` rows with `stop_loss <= 0 OR
take_profit <= 0`: **0**.

Tests — `python3 -m pytest tests/test_quarantine_bracket_rules.py
tests/test_backfill_unknown_category.py tests/test_sync_bracket_and_scale_guards.py
tests/test_mysql_sync_category_inference.py -q` → **54 passed**.

Two bugs in the new SQL were found this way and fixed before the values were
written, both now covered by `tests/test_quarantine_bracket_rules.py`:

- an unbalanced parenthesis made every B1/B2 statement a MySQL 1064 syntax
  error (`sql.count("(") == sql.count(")")` is now asserted);
- the zero clause was gated on `entry_price > 0`, leaving the 28 rows in §1.

## 5. Guard against regrowth

New rows cannot reintroduce this: `_validate_bracket_geometry` rejects
`field <= 0`, wrong-side and >100x brackets before the INSERT, and its
"suppressed" count is printed by every sync run (132 brackets suppressed on the
2026-11-28 post-rebase dry run — see
`updates/2026-11-28-ingest-bracket-and-scale-guards.md`). This sweep is the
historical half of the same contract.

## 6. Limitations (read these)

- **The first pass's B2 backup was overwritten.** `snapshot()` named tables
  `bracket_repair_<column>_<stamp>`, which is not unique per rule, so the B3
  snapshot for `take_profit` `DROP`ped and recreated the B2 table with its own
  91 rows. The 53 affected rows' `take_profit`/`entry_price` values are intact
  in `data_quarantine.row_json` (53 `B2_bad_take_profit` rows), which is enough
  to restore the one field that was NULLed — but the full-row snapshot for that
  batch is gone. Naming is now `bracket_repair_<rule>_<column>_<stamp>`.
- **28 row-quarantine candidates remain** (`R7_scale_vs_ohlcv`, |PnL| > 50% with
  a price >2x off the OHLCV close of its own date). They are a separate,
  unreviewed queue and were deliberately **not** touched by this bracket sweep —
  `--brackets-only` exists so a bracket request cannot silently neutralise a PnL
  as a side effect.
- `at_signal_outcomes`/`at_raw_picks` were not swept in this pass; the same
  `--brackets-only --table` invocation covers them when asked.
- The sweep is data-only. Any resolver that still writes a stop from a
  different price series than its entry will produce wrong-side stops that the
  ingest guard now catches and logs, but the upstream resolver itself is
  unchanged.

## 7. Provenance

- Rule source: `alpha_engine/mysql_trading_sync.py::_validate_bracket_geometry`
  (lines ~930-985), `BRACKET_MAX_MULTIPLE = 100.0`.
- Sweep rule source: `tools/quarantine_bad_rows.py::_bracket_sql`,
  `BRACKET_RULES`.
- Gate source: `tools/asset_class_audit_checks.py::_class_gates` →
  `gate("bad_side_stops", bad_stops == 0, ...)`.
- Counts above are from the live DB (`ejaguiar1_stocks.trading_picks`,
  154,379 rows at 2026-11-28T04:03Z), the ledger
  `ejaguiar1_stocks.data_quarantine`, and the backup tables named in §3.
- Run reports: `reports/quarantine_bad_rows_20261128T040355Z.json`,
  `reports/quarantine_bad_rows_20261128T040424Z.json`.

## 8. Same-day follow-up — ISO pairs are no longer "unclassifiable"

`tools/backfill_unknown_category.py` was taught the sync's ISO-pair rule, so a
`USD-JPY` / `USD-CHF` row resolves to FOREX instead of being reported as
unclassifiable on every run (the sync already labelled it FOREX at ingest; the
backfill tool disagreed because `detect_asset_class` cannot tell a bare X-Y
shape from anything else).

Applied to `trading_picks` at 2026-11-28T04:06:38Z — backup
`ejaguiar1_backups.trading_picks_label_fill_20261128T040638Z` (65 rows) —
**65** empty labels filled: FOREX **29** (the ISO pairs), ETF 26, EQUITY 7,
BOND 3. Global gate `empty_category` went **67 → 2**.

The remaining two are genuinely ambiguous and were deliberately left alone:
`JTO-USD2` (a crypto pair with a stray `2` suffix) and `BRK-B` (Berkshire class
B, whose `-B` looks like a currency pair). Neither is guessed at.
Tests: `tests/test_backfill_unknown_category.py` asserts the pair rule, that
`BTC-USD` is **not** treated as FX, that an unambiguous emitter still outranks
the symbol, and that the tool's `_FX_ISO` set is byte-for-byte the sync's.
