# Empty category cleared, and sports betting removed from the stocks DB

2026-11-28 · `ejaguiar1_stocks` @ `mysql.50webs.com`

Two requests, two different kinds of repair:

1. Clear the `empty_category` gate (67 `trading_picks` rows with no class).
2. Remove the sports-betting half of the stocks database — that product is
   scrapped for now.

The first needed a **root-cause** fix as well as a data fix: the labels had
already been repaired once today and the hourly sync put them back. The second
needed an **irreversibility** decision, so every dropped table is snapshotted
first and every writer is switched off.

Numbers below are measured, not estimated; provenance is in §6.

---

## 1. `empty_category`: 67 → 0, and why it kept coming back

| step | rows | backup |
|---|---|---|
| rows with an empty `category` at start | 67 | — |
| resolvable by the existing rules (ISO pair / source / classifier) | 65 | `trading_picks_label_fill_20261128T080640Z` (67 rows) |
| resolved by the two new evidence rules | 2 | same snapshot |
| alias drift found in the same run (`meme`, `prediction_market`) | 14 | `trading_picks_label_fill_20261128T080758Z` (14 rows) |
| **after** | **0** | — |

Class split of the 67: FOREX 29, ETF 26, EQUITY 8, BOND 3, CRYPTO 1.

### The regrowth, proven

`updates/2026-11-28-historical-wrong-side-stop-sweep.md` records 65 of these
rows being relabelled at 04:06Z. They were back by 05:20Z. Grouping the current
empty rows by `updated_at` names the writer precisely:

| `updated_at` (UTC) | rows |
|---|---|
| 2026-11-28 04:59 | 48 |
| 2026-11-28 05:59 | 3 |
| 2026-11-28 06:59 | 14 |

One hour apart, 48 of them identical to the bracket-regrowth batch in
`updates/2026-11-28-at-tables-bracket-sweep-and-regrowth.md`. The hourly
`alpha_engine/mysql_trading_sync.py` run rewrote each repaired label from its
source JSON, which still carries an empty category:

```sql
category = VALUES(category)     -- '' overwrote a repaired label
```

The same statement's `stop_loss = VALUES(stop_loss)` is what restored the
brackets. **One upsert, two regrowing defects.**

Also confirmed on the deployed writer (`origin/main`):

```
126: _CATEGORY_KNOWN_PASSTHROUGH = {"meme", "index", "unknown"}
```

`meme` passes straight through on main, which is why the
`hoffman_keltner_expansion::PEPE-USD::2026-09-26` row was written back as
`meme` at 07:59:52Z after being relabelled this morning. PR #1240's branch has
`"meme": "MEMECOIN"` in the alias map instead.

### Fixes

**Write guard** (`alpha_engine/mysql_trading_sync.py`, on PR #1240's branch):

```sql
category = COALESCE(NULLIF(VALUES(category), ''), category),
```

A good label now survives an empty incoming one; a non-empty incoming value —
including a corrected label — still wins, so relabels are never blocked.

**Two evidence rules** in `tools/backfill_unknown_category.py`, both requiring
proof from the database rather than a hardcoded symbol list:

* **peer label** — the same symbol already carries a single, unanimous class in
  the same table (`JTO-USD2` has four CRYPTO rows). A symbol with two different
  classes is omitted, so this can never manufacture a label by majority vote.
* **equity universe** — the symbol has price history in `equity_daily_ohlcv`
  or `stock_ohlcv` (`BRK-B`, whose `-B` suffix defeats both the pair detector
  and `detect_asset_class`).

**Alias drift** is now a candidate class in the same tool (14 rows: 13
`prediction_market`, 1 `meme`), so `label_drift` is repairable by name instead
of by hand-written SQL as it was this morning.

Order of resolution: source system > ISO pair > classifier > peer label >
price universe. Each later rule only runs when every earlier one declined.

### A collation trap worth remembering

The first alias query used `WHERE category <> UPPER(category)`. It matched
**nothing** while a row literally held `'meme'`: `trading_picks.category` is
`utf8mb4_unicode_ci`, so `'meme' <> 'MEME'` is false. The rule needs
`BINARY category <> BINARY UPPER(category)`. This is the third time a
case-insensitive collation has silently changed a query's meaning on this
server (the earlier two are recorded in
`updates/2026-11-28-at-tables-bracket-sweep-and-regrowth.md` §7).

---

## 2. Sports betting removed from `ejaguiar1_stocks`

17 tables, **22,061 rows**, dropped after a verified snapshot:

| table | rows | what it held |
|---|---|---|
| `lm_sports_clv` | 20,607 | closing-line-value ledger |
| `lm_sports_odds` | 502 | bookmaker odds feed |
| `lm_sports_value_bets` | 375 | +EV proposals |
| `lm_sports_daily_picks` | 222 | daily picks |
| `lm_sports_credit_usage` | 132 | The Odds API credit meter |
| `lm_sports_ml_predictions` | 79 | sports ML predictions |
| `lm_sports_bets` | 74 | placed paper bets |
| `lm_nba_team_stats` | 30 | NBA team stats |
| `lm_sports_bankroll` | 15 | paper bankroll curve |
| `lm_nba_games_today` | 14 | NBA schedule cache |
| `lm_injury_intel_cache` | 4 | NBA/MLB/NHL injury intel |
| `lm_schedule_intel_cache` | 3 | NBA/MLB/NHL rest/schedule intel |
| `lm_sports_ml_metrics` | 0 | sports ML metrics |
| `lm_nba_stats_cache` / `lm_nfl_stats_cache` / `lm_mlb_stats_cache` / `lm_nhl_stats_cache` | 1 each | league stats caches |

Table count: **469 → 453**. Six tables were created in the same transaction by
other agents; the net of my 17 drops is `469 − 17 = 452`. Post-state query for
sports-shaped names returns **none**.

### Kept on purpose

`sp_picks` / `sp_batches` / `sp_daily_performance` are **smart picks** and
`ss_baselines` / `ss_spikes` are **smart signals** — crypto/equity scanners
whose names look sport-ish. `lm_scraped_data` is an equity options /
short-interest cache. None of them is sports.

### How the removal was made safe

`tools/scrap_sports_tables.py` (new) is the repeatable form of this action:

* dry-run by default; `--apply` required;
* every table cloned into `ejaguiar1_backups` as
  `stocks_sports_drop_20261128T0806Z__<table>`, using the same `clean_ddl()`
  as the label backfill (FK stripped, constraint names suffixed);
* the `DROP` runs only when the snapshot committed exactly `COUNT(*)` rows —
  every table reported `copied/expected` equal;
* refuses to run at all if a foreign key references a target, so an unrelated
  table cannot be broken as a side effect.

No foreign keys referenced any of the 17, and no view did either (checked in
`information_schema` before the run).

**Why a file backup rather than a rename:** the request was to get rid of the
tables, and `ejaguiar1_backups` is the project's mandated archive. Recovery is
one `CREATE TABLE … AS SELECT` away.

### Writers switched off

Dropping the tables without stopping the producers would repeat this morning's
lesson — a data repair is provisional while the writer still runs. Five
workflows lost their `schedule:` block, keeping `workflow_dispatch` as the
revival path:

| workflow | cron removed |
|---|---|
| `sports-betting-refresh.yml` | 5×/day (the only DB writer) |
| `sports-data-snapshots.yml` | every 15 min |
| `sports-prediction-market-sync.yml` | 2×/day |
| `sports-smoke-and-e2e.yml` | hourly |
| `sports-forensics-weekly.yml` | weekly |

The first is the one that matters for regrowth (it drives the PHP endpoints
that wrote `lm_sports_*`); the other four are read-only consumers that would
simply fail against the now-missing tables.

---

## 3. Gate posture

| gate | before this work | after |
|---|---|---|
| `empty_category` | FAIL — 67 | **PASS — 0** |
| `label_drift` | FAIL — `meme=1` | **PASS — none** |
| `bad_side_stops` (6 classes) | 0 (at 05:2x) | FAIL again — 23/6/8/6/5/1 |

**11/51 passed, 40 failed** against 16/51 at 05:2x. That is not a regression
from this work: 16 − 6 (classes whose stops regrew) + 1 (`empty_category`) = 11.
The bracket guard lives only on PR #1240's branch, so every hour the sync
restores the same wrong-side stops. `label_drift` can regrow the same way until
that alias map is deployed.

---

## 4. Verification

| check | result | how |
|---|---|---|
| `empty_category` | **PASS — 0** | `tools/asset_class_audit_checks.py --skip-backtests` |
| `label_drift` | **PASS — none** | same |
| backfill post-state | `0 still updatable, 0 unclassifiable` | the tool's own post-state pass |
| backups | 67/67 and 14/14 rows | printed by `snapshot()` |
| sports tables present after drop | **none** | `information_schema` query |
| sports snapshot row counts | 17/17 equal to source | `scrap_sports_tables.py --apply` |
| workflow triggers | `workflow_dispatch` only (+`pull_request` for smoke) | `yaml.safe_load` of all five |
| tests | **37 passed** | `pytest tests/test_backfill_unknown_category.py tests/test_mysql_sync_category_inference.py` |

New tests: peer label resolves `JTO-USD2`; equity universe resolves `BRK-B`;
the classifier still outranks both; no evidence means no label; the alias rule
repairs `meme`; the tool's alias map matches the sync's for `meme` / `index` /
`managed_futures` / `prediction_market`; the upsert contains the COALESCE guard
and no longer blanket-copies `VALUES(category)`.

No database is touched by the tests.

---

## 5. Limitations

* **Both fixes regrow until PR #1240 merges.** The guard and the alias map are
  on `fix/ingest-guards-and-labels-20261128`; `origin/main` still has
  `category = VALUES(category)` and the lowercase passthrough. `empty_category`
  was 0 when measured, but the next sync can add rows for any *new* pick whose
  source is empty and unclassifiable. Re-running
  `python3 tools/backfill_unknown_category.py --table trading_picks --apply`
  is the repeatable remedy; it is idempotent.
* **The PHP live-monitor endpoints were not touched.** `live-monitor/api/
  sports_*.php` is deployed on the FTP host, not in this repo's runtime. With
  the tables gone those endpoints will error until they are removed or repointed
  — that is expected for a scrapped product, but it is a deploy-side action,
  not something this commit can do.
* `kimi-goldmine-collector.yml` still calls `sports_picks.php?action=today` as a
  liveness probe; it will now fail that step.
* **Sports picks already inside the ledger are untouched.** The ledgers hold no
  `SPORTS`-labelled rows (0 in `trading_picks`, `at_raw_picks`,
  `at_signal_outcomes`), so there is nothing to purge there.
* Six tables were created by other agents during this run (469 − 17 = 452
  expected, 453 observed). None is sports.

---

## 6. Provenance

* Row counts, table inventory, `updated_at` buckets, collation evidence:
  `ejaguiar1_stocks` at `mysql.50webs.com`, read 2026-11-28 between 07:50Z and
  08:09Z.
* Gate numbers: `python3 tools/asset_class_audit_checks.py --skip-backtests`
  (11/51 passed, 41→40 failed across the two runs in this session).
* Backups: `ejaguiar1_backups.trading_picks_label_fill_20261128T080640Z` (67),
  `…080758Z` (14), and `stocks_sports_drop_20261128T0806Z__*` (17 tables).
* Reports: `reports/label_fill_20261128T080640Z.json`,
  `reports/label_fill_20261128T080758Z.json`,
  `reports/sports_tables_scrapped_20261128T0806Z.json`.
* Deployed-writer evidence: `git show origin/main:alpha_engine/
  mysql_trading_sync.py`.
