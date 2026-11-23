# stock_picks had 11 readers and zero writers — writer restored

**Date:** 2026-11-23
**Branch:** `copilot/hub-audit-2026-11-23`
**Todo:** #28 — "Restore writers for stock_picks / mf2_fund_picks"

## What was broken

The dead-data checker reported two systems stale:

| System | Table | Rows | Last write |
|---|---|---|---|
| Stock Intelligence | `stock_picks` | 7,239 | **5,047h** ago (~210 days) |
| Mutual Funds | `mf2_fund_picks` | 600 | **5,743h** ago (~239 days) |

`stock_picks` is read by 11 PHP files, several of them served live:
`live-monitor/api/spike_scanner.php`, `live-monitor/api/pair_fingerprint.php`,
`investments/goldmines/antigravity/api/unified_predictions.php`,
`findstocks/portfolio2/api/stock_intel.php`, plus the KIMI goldmine collector
(`kimi_goldmine_collector.php` reads `stock_picks` and derives
`KIMI_GOLDMINE_PICKS` from it, so the starvation cascades).

## The forensics

The obvious hypothesis — "recover the missing writer from the Windows source tree",
the technique that recovered `stock_intel.php` and `penny_stocks.php` — **failed**:

```
findstr /s /i /m /c:"INSERT INTO stock_picks"    E:\...\*.php   -> no matches
findstr /s /i /m /c:"INSERT INTO mf2_fund_picks" E:\...\*.php   -> no matches
```

Searched the Linux tree too, across `.php`/`.py`/`.js`/`.sql`, including
`INSERT IGNORE`, `REPLACE INTO` and `DataFrame.to_sql`. Zero writers. The only
`CREATE TABLE stock_picks` occurrences are a setup script
(`tools/setup_torontoevent_databases.py`) and the schema baseline — neither inserts.

**The pipeline did not break; it moved.** Equity picks are now produced by the
sibling repo `eltonaguiar/STOCKSUNIFY2`, pulled daily by
`tools/sync_stocksunify2.py` (workflow `stocksunify2-pull.yml`, 13:05 UTC, last
three runs all `success`) into
`audit_dashboard/data/stocksunify2_active_picks.json`, which feeds /audit. That
canonical file already carries a `pick_hash`, and `stock_picks` already indexes
`pick_hash` via `idx_hash` — the two shapes were designed to meet. The legacy
table was simply left behind.

## What changed

### 1. `tools/stock_picks_writer.py` (new)

Maps canonical picks → `stock_picks` rows:

| canonical | stock_picks |
|---|---|
| `symbol` | `ticker` |
| `strategy` | `algorithm_name` |
| `generated_at` | `pick_date` + `pick_time` (naive UTC) |
| `entry_price` / `simulated_entry_price` | same (sim falls back to entry when 0) |
| `score` (float) | `score` (int) |
| `risk` | `risk_level` |
| `stop_loss` | `stop_loss_price` |
| `pick_hash` | `pick_hash` |
| `indicators` | `indicators_json` |

- **Dry-run is the default**; nothing is written without `--commit`.
- **Idempotent on `pick_hash`.** The column is indexed but NOT unique, so
  `INSERT ... ON DUPLICATE KEY UPDATE` is unusable — the writer SELECTs the hashes
  already present for the batch and skips them, making re-runs a no-op.
- Rows with no symbol or no parsable timestamp are skipped and reported, not
  invented. A missing or malformed `pick_hash` is replaced by a deterministic
  `sha256(symbol|strategy|generated_at)` so idempotency survives a bad source field.

### 2. `tests/test_stock_picks_writer.py` (new, 20 tests)

Pins the mapping, the timestamp/UTC handling, score coercion, hash derivation,
in-batch de-duplication, the full INSERT column list, and — via an injected fake
cursor — that `--commit` inserts new rows and inserts **nothing** when the hash
already exists. Dry-run is asserted to never open a connection.

### 3. `.github/workflows/stock-picks-writer.yml` (new)

Runs daily at 13:30 UTC (after the source refresh). Always runs the unit tests and
a dry run; the write step is gated on repo variable
`STOCK_PICKS_WRITER_ENABLED == 'true'` or an explicit manual dispatch. Installs
`pytest` and `pymysql` explicitly — the same missing-dependency gap that made the
`php52` gate red on PR #1096.

### 4. `check_dead_data.php` — Mutual Funds reports `DECOMMISSIONED`

`mf2_fund_picks` **cannot** get an honest writer: its universe table `mf2_funds`
also has no writer in either source tree, so there is no fund universe to generate
picks from. Any "fix" would have to invent symbols — fabrication. The table holds
600 historical rows and the app was superseded by the /audit equity surface.

Reporting it `STALE` raised a 🚨 alert that no action could ever clear. It now
reports its own status, contributes no alert, and is counted separately so the
summary still reconciles.

## How it was verified

- `pytest tests/test_stock_picks_writer.py` → **20 passed**.
- Real dry run against the live canonical file → **6 rows mapped correctly**
  (PG, GME, COST, LLY, AAPL, COST), all with valid source hashes.
- `python3 tools/validate_php52.py investments` → **passed, 7 files**.
- `php -n -l check_dead_data.php` → **no syntax errors**.
- Checker deployed and executed live; output:
  ```
  Active Systems: 2
  Stale/Dead Systems: 2
  Skipped (no database): 2
  Decommissioned (no upstream source): 1
  Total Systems Checked: 7 (2 active + 2 stale + 2 skipped + 1 decommissioned)
  ```
  The Mutual Funds 🚨 alert is gone; Stock Intelligence still correctly shows
  5,047.31h, which is what the new writer addresses.

## Deliberately not done

The write is **not** enabled. Enabling a schedule that writes to production MySQL
is a decision for the operator, made after this PR is reviewed and merged — hence
the `STOCK_PICKS_WRITER_ENABLED` switch rather than an unconditional `--commit`.
Once enabled, the first run should be watched to confirm `stock_picks` leaves the
stale list.

Paper only. Zero capital. Not investment advice.
