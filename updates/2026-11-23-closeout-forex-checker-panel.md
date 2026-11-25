# Close-out pass: forex pipeline un-stuck, checker made honest, panel deployed

**Date:** 2026-11-23
**Owner:** `copilot-cli-deepseek-flash`
**Trigger:** re-read of the transcript surfaced items my own "21/21 done" ledger had not captured
**Branch:** `copilot/hub-audit-2026-11-23` (nothing pushed to `main`)

---

## Checklist outcome

| # | Item | Outcome |
|---|---|---|
| 1 | `fetch_prices.php` reports "no pairs need price data" while table is 195d stale | **FIXED** — row-count guard → freshness guard; 8 pairs backfilled |
| 2 | `mc_winners` MAX(created_at) NULL but INSERT sets NOW() | **FIXED** — was an empty table; revealed a strict-comparison bug |
| 3 | Checker claims "Report saved to …" but URL returned 200/0B or 404 | **FIXED** — stable filename, truthful result, PHP 5.2-safe encode |
| 4 | Summary arithmetic: 2 skipped systems in Total but in neither bucket | **FIXED** — counts now reconcile |
| 5 | Pump-watch panel committed but never deployed | **FIXED** — live at `/audit/pumpwatch_consensus.html`, HTTP 200 |
| 6 | Cost rule `breakeven_cost_bp > cost_high_bp` never implemented | **DEFERRED** — see §6 |
| 7 | `stock_picks`, `mf2_fund_picks` have no writer | **DEFERRED** — see §7 |

---

## 1. The forex pipeline was permanently frozen (the important one)

`fxp_price_history` held 2,694 rows whose newest was ~195 days old, yet the writer
returned:

```json
{"ok":true,"fetched":0,"message":"No pairs need price data. All pairs already have sufficient data."}
```

Both statements were "correct" under the code and mutually contradictory. The cause:

```php
$sql .= " WHERE ph.cnt IS NULL OR ph.cnt < 20";
```

The guard counts **rows, not freshness**. Once a pair had 20 bars of history — however
old — it counted as complete and was never selected again. After initial seeding the
query matched nothing forever, so the table froze at its seed date while the endpoint
kept reporting success.

Fix — also refresh anything whose newest bar is older than two days:

```sql
LEFT JOIN (SELECT symbol, COUNT(*) as cnt, MAX(price_date) as max_date
           FROM fxp_price_history GROUP BY symbol) ph ON p.symbol = ph.symbol
WHERE ph.cnt IS NULL OR ph.cnt < 20
   OR ph.max_date IS NULL
   OR ph.max_date < DATE_SUB(CURDATE(), INTERVAL 2 DAY)
```

Verified live, immediately after deploy:

```
before: {"ok":true,"fetched":0,"message":"No pairs need price data"}
after:  {"ok":true,"fetched":8, ... 259 price_records per pair ...}
```

and the checker flipped that system from **STALE 4,685h** to **✅ Active — 5.93h ago,
3,798 records**.

## 2. Empty tables were never detected — a strict-comparison bug

The null diagnostic asked for row counts and returned `[rows=0, non_null_created_at=0]`,
so `mc_winners` was simply **empty** — which should have been reported as `EMPTY_TABLE`.
Why wasn't it?

```php
$result['record_count'] = $count_row['total'];   // MySQL returns a STRING
...
if ($result['record_count'] === 0) {             // "0" === 0  is FALSE
```

`"0" === 0` is `false` in PHP, so **the empty-table branch was dead code for every
system**. An empty table fell through to the timestamp check and was misreported as
"no timestamp". Fixed by casting once at the assignment:

```php
$result['record_count'] = (int)$count_row['total'];
```

`Meme Coin Scanner` now correctly reads `⚠️ Table is empty!`.

## 3. The "saved report" claim was not checkable

```php
$json_file = ... . 'dead_data_report_' . date('Ymd_His') . '.json';
file_put_contents($json_file, json_encode($report, JSON_PRETTY_PRINT));
echo "Report saved to: $json_file\n";
```

Three problems: the return value was never checked; `JSON_PRETTY_PRINT` is **PHP 5.4+**
on a 5.2 host; and a new dated file accumulated in a web-served directory per run while
fetching them back gave **200 with 0 bytes** (or 404).

Now: one stable `dead_data_report.json`, plain `json_encode`, and the outcome is
reported truthfully. Verified:

```
Report saved: .../dead_data_report.json (1463 bytes)
GET .../dead_data_report.json  -> HTTP 200, 1463 bytes
{"total_systems":7,"active":2,"stale":3,"skipped":2}
```

## 4. Summary arithmetic now reconciles

Skipped systems were counted in `Total` but in neither `Active` nor `Stale/Dead`, so
"5 stale of 7" concealed two systems that were never assessed. Added an explicit bucket:

```
Active Systems: 2
Stale/Dead Systems: 3
Skipped (no database): 2
Total Systems Checked: 7 (2 active + 3 stale + 2 skipped)
```

## 5. Pump-watch consensus panel deployed

Committed earlier but never served. Now live with its data sidecar:

```
/audit/pumpwatch_consensus.html          HTTP 200   9,101 B
/audit/data/pumpwatch_consensus.json     HTTP 200   2,707 B   verdict: REFUTED
```

The panel fetches `data/pumpwatch_consensus.json` relatively, which resolves correctly
from `/audit/`.

## 6. DEFERRED — cost rule `breakeven_cost_bp > cost_high_bp`

**Reason:** this would change a *promotion criterion* across the whole estate. The number
is already computed and available (`tools/cost_sensitivity.py` emits `breakeven_cost_bp`),
so making it a **hard gate** would silently reclassify strategies without an owner
decision, and could flip verdicts recorded under the previous rule. That is a policy call
on the money path, not a refactor. It needs an explicit decision before it can gate
anything; until then the tool reports and does not enforce.

## 7. DEFERRED — no writer exists for two stale tables

Measured, not assumed:

| Table | Files mentioning | Files that WRITE |
|---|---|---|
| `stock_picks` | 27 | **0** |
| `mf2_fund_picks` | 4 | **0** |

Neither table has a writer anywhere in this repo (the GHA hit is a JSON file named
`stock_picks.json`, unrelated). Their pipelines are external or decommissioned — likely on
the Windows host or a retired 50webs cron. Nothing here can be fixed without first
locating the writer. By contrast `cw_winners` went **Active** during this pass, so it does
have a working writer and was correctly excluded from this list.

## Final checker state

```
Crypto Winner Scanner   ✅ Active - 0.13h ago        Records: 352
Meme Coin Scanner       ⚠️ Table is empty
Sports Betting Picks    ℹ️ Not database-backed - skipped
Stock Intelligence      🚨 STALE 5045.93h            Records: 7239   (deferred, §7)
Penny Stocks            ℹ️ Not database-backed - skipped
Forex Insights          ✅ Active - 5.93h ago        Records: 3798   (fixed, §1)
Mutual Funds            🚨 STALE 5741.93h            Records: 600    (deferred, §7)

2 active + 3 stale + 2 skipped = 7
```

Every remaining alert now names a condition that was verified to be true.

---

Infrastructure only. No picks, no signals, zero capital, not investment advice.
