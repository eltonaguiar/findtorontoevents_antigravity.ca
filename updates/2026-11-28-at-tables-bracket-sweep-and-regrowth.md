# 2026-11-28 — Bracket sweep on `at_raw_picks` / `at_signal_outcomes`, `meme` relabel, and the regrowth mechanism

Status: data repaired and verified. **Not durable until PR #1240 merges** — see §5.

## 1. What was broken

Three separate defects, all found by querying the live DB rather than by
trusting the earlier sweep's "0 remaining":

| # | Defect | Evidence |
|---|--------|----------|
| A | `label_drift` was red on a single lowercase `meme` row | `trading_picks` id `hoffman_keltner_expansion::PEPE-USD::2026-09-26`, `alpha_engine_fast`, written 2026-09-26T14:08Z |
| B | `at_raw_picks` carried 2,849 wrong-side stops, 2,969 wrong-side take-profits and 891 brackets >100× from entry | 114,288-row table, `bad_side_stops`-shaped query |
| C | The 04:03Z sweep did not hold: 48 cleaned rows came back within the hour | see §5 |

Defect B was **not** random corruption. It had one dominant author:

```
source_system      rows with a SHORT stop below entry
incubator_gainer                 2,481   (2,323 CRYPTO, 104 MEMECOIN, 54 FOREX)
Predictions                         32
alpha_engine_unified                6
AlphaEngine                         6
audit_trail_local                   5
(8 further sources)                15
```

`incubator_gainer` writes a **LONG-shaped bracket for both directions**:

| direction | rows | long-shaped bracket | short-shaped |
|-----------|------|---------------------|--------------|
| LONG  | 2,614 | 2,600 | 0 |
| SHORT | 2,489 | 2,469 | 1 |

Example: `VANRYUSDT` SHORT, entry 0.00639, stop 0.00598273 (−6.4 %), target
0.00759469 (+18.8 %) — a long bracket wearing a SHORT label. The producer is
frozen (last row 2026-05-12) and is already banned in `quality_gates`,
`picks_now_professional`, `build_clean_ledger_v2` and `risk_policy.json`, so
this is a historical repair, not a live signal to chase.

The 891 off-scale take-profits are a second pattern: 874 of them are the
`Predictions` (4chan) sentinel `take_profit = 9999999999.99999999` — a "no
target" marker stored as a price.

## 2. What changed in the code

`tools/quarantine_bad_rows.py`

* Registered `at_raw_picks` in `TABLES` with `"row_rules": False`.
  It has no `created_at` column (it uses `recorded_at`), and every R1–R7 rule
  plus the R7 OHLCV cross-check selects `created_at`. Without the flag the
  post-state verification would raise `Unknown column 'created_at'` after the
  writes had already committed — the worst possible failure order.
* Added `supports_row_rules()` and used it at the two call sites
  (`row_hits` construction, post-state), so a table can be bracket-repaired
  without being enrolled in the row-quarantine queue.
* `--table at_raw_picks` without `--brackets-only` now prints
  `quarantine candidates: 0` rather than crashing.

Rule text is unchanged: B1/B2 NULL a field that is `<= 0` or on the wrong side
of entry, B3 NULLs one more than 100× from entry. The rule mirrors the ingest
guard `alpha_engine.mysql_trading_sync::_validate_bracket_geometry`.

## 3. What was applied

`meme` relabel (1 row), through the same snapshot + ledger path:

```
backup: ejaguiar1_backups.trading_picks_label_fix_meme_20261128T052055Z (1 row)
ledger: data_quarantine action=relabel_category rule=L1_lowercase_meme
```

Bracket sweep, `python3 tools/quarantine_bad_rows.py --table at_signal_outcomes
--table at_raw_picks --brackets-only --apply` (2026-11-28T05:20:57Z):

| table | rows | B1 stop_loss | B2 take_profit | B3 off-scale | fields |
|-------|------|--------------|----------------|--------------|--------|
| `at_signal_outcomes` | 51,468 | 31 | 30 | 0 | 61 |
| `at_raw_picks` | 114,288 | 3,095 | 3,000 | 873 (872 TP + 1 SL) | 6,968 |
| **total** | 165,756 | 3,126 | 3,030 | 873 | **7,029** |

Backups (one table per rule **and** column, so a later rule cannot `DROP` an
earlier rule's snapshot):

```
ejaguiar1_backups.at_signal_outcomes_bracket_repair_B1_stop_loss_20261128T052057Z
ejaguiar1_backups.at_signal_outcomes_bracket_repair_B2_take_profit_20261128T052057
ejaguiar1_backups.at_raw_picks_bracket_repair_B1_stop_loss_20261128T052057Z
ejaguiar1_backups.at_raw_picks_bracket_repair_B2_take_profit_20261128T052057Z
ejaguiar1_backups.at_raw_picks_bracket_repair_B3_take_profit_20261128T052057Z
ejaguiar1_backups.at_raw_picks_bracket_repair_B3_stop_loss_20261128T052057Z
```

(The `at_signal_outcomes` B2 name lost its trailing `Z` to the 64-character
identifier limit; it is still unique per column, which is why the purpose string
carries both rule and column.)

Re-sweep of `trading_picks` after the regrowth was confirmed (§5), same command
with `--table trading_picks` (2026-11-28T05:23:20Z): 52 `stop_loss`,
44 `take_profit`, 3 off-scale → 99 fields NULLed, backups
`…bracket_repair_B{1,2,3}_*_20261128T052320Z`, ledger action `nulled_bracket`.

## 4. Verification

| check | before | after | how |
|-------|--------|-------|-----|
| `bad_side_stops` CRYPTO / EQUITY / FOREX / ETF / BOND / COMMODITY / FUTURES | 23 / 5 / 8 / 3 / 0 / 5 / 1 | **0 in all seven** | `tools/asset_class_audit_checks.py` |
| `label_drift` (global) | `meme=1` | **PASS — none** | same |
| `at_raw_picks` `stop_loss<=0` / `take_profit<=0` | 276 / 275 | **0 / 0** | direct SQL |
| `at_raw_picks` wrong-side stop / take-profit | 2,849 / 2,969 | **0 / 0** | direct SQL |
| `at_raw_picks` brackets >100× | 891 | **0** | direct SQL |
| `at_signal_outcomes` wrong-side stop / take-profit | 0 / 30 | **0 / 0** | direct SQL |
| gate posture | 15/51 | **16/51** | `--skip-backtests --json` |
| `empty_category` (unchanged) | 67 | 67 | out of scope today |

`at_raw_picks` post-state also reports `0 row(s) matching` for the R-rules
(bracket-only mode), and `trading_picks` reports 28 R7 candidates that were
**deliberately not touched** — those are pnl-scale rows, a different defect
class, and `--brackets-only` exists precisely so a bracket request cannot
neutralise a PnL as a side effect.

## 5. The regrowth mechanism — and why this repair is not durable yet

At 04:03Z the first sweep reported 76 → 0. By 05:20Z, 48 wrong-side stops were
back. Those 48 are **not new rows**: all 48 appear in `data_quarantine` with
`action='nulled_bracket'` (overlap 48/48), i.e. they were cleaned and then
rewritten, with `updated_at` between 04:59:24 and 04:59:27Z.

The writer is the `mysql_trading_sync` upsert:

```sql
ON DUPLICATE KEY UPDATE
    entry_price = VALUES(entry_price),
    take_profit = VALUES(take_profit),
    stop_loss   = VALUES(stop_loss),
```

Every sync re-writes `entry_price`/`take_profit`/`stop_loss` from the source
JSON, and the source JSON still holds the bad values. The guard that would
reject them exists **only on the PR branch**:

```
git show origin/main:alpha_engine/mysql_trading_sync.py | grep -c _validate_bracket_geometry
0
git show origin/fix/ingest-guards-and-labels-20261128:alpha_engine/mysql_trading_sync.py | grep -c ...
2
```

So: the data repair is correct, and it will regrow on the next production sync
until **PR #1240** (https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/1240)
merges and the sync job picks up the guarded version. Do not read a future
`bad_side_stops` failure as a new defect before checking whether the guard is
deployed.

## 6. Limitations

* **`incubator_gainer` brackets were NULLed, not mirrored.** Mirroring
  (`stop' = 2·entry − stop`) would preserve the exact risk distance and is
  arithmetically valid for all 2,469 SHORT rows. It was deliberately not done:
  the ingest guard NULLs rather than invents, and a repair that manufactures
  price levels is indistinguishable from a guess in the ledger. If those rows
  are ever needed for a study, mirroring is recoverable from
  `at_raw_picks_bracket_repair_B{1,2}_*_20261128T052057Z`.
* **The B2 `at_signal_outcomes` snapshot name is truncated** to 63 characters
  (`…20261128T052057`, no `Z`). Row data is intact; only the name is shorter.
* **28 `R7_scale_vs_ohlcv` candidates remain on `trading_picks`**, unexamined by
  design (§4).
* **`empty_category` is still 67**, unchanged by this work.
* Whether a *second* writer rewrote rows after 04:59 could not be ruled out: the
  repo has one other direct `trading_picks` upsert
  (`tools/emit_equity_breakout_pod.py`), but it only writes its own pod's ids.
  The 48 restored ids carry 8 different `source_system` values, which matches a
  bulk JSON sync rather than a pod emitter.

## 7. Provenance

* All row counts: `ejaguiar1_stocks` at `mysql.50webs.com`, read 2026-11-28
  between 05:19Z and 05:24Z; `trading_picks` 154,400 rows, `at_raw_picks`
  114,288, `at_signal_outcomes` 51,468.
* Gate numbers: `python3 tools/asset_class_audit_checks.py --skip-backtests
  --json /tmp/gate_after2.json` at 2026-11-28T05:25Z.
* Restoration evidence: join of the 48 bad ids against
  `data_quarantine.source_id` where `action='nulled_bracket'` and
  `source_table='trading_picks'`; `updated_at` from the same rows.
* Guard deployment check: `git show origin/main:…` vs
  `git show origin/fix/ingest-guards-and-labels-20261128:…`, run 2026-11-28.
* Sweep report: `reports/quarantine_bad_rows_20261128T052057Z.json` and
  `reports/quarantine_bad_rows_20261128T052320Z.json`.
