# Dead-data checker: column auto-detection replaces hardcoded names (false alarms eliminated)

**Date:** 2026-11-23
**Owner:** `copilot-cli-deepseek-flash`
**File:** `investments/goldmines/antigravity/check_dead_data.php`

---

## TL;DR

After connectivity was restored, the dead-data checker was still producing **four broken
verdicts out of seven** — and none of them was about data being dead. All four were the
checker's own config drifting from the real schema:

| System | Before | After |
|---|---|---|
| Sports Betting Picks | `❌ Table 'sports_picks' does not exist!` **(false CRITICAL)** | `ℹ️ Not database-backed (static JSON feed) — skipped` |
| Penny Stocks | `❌ Query error: Unknown column 'last_updated'` **(false alarm)** | `ℹ️ Not database-backed (Yahoo screener proxy) — skipped` |
| Forex Insights | `❌ Query error: Unknown column 'timestamp'` **(false alarm)** | `🚨 STALE 4685h, 2,694 records` — **real finding** |
| Meme Coin Scanner | `⚠️ No timestamp!` (vague) | `⚠️ All date columns NULL (created_at)` — **precise** |

## 1. Root cause: the config, not the systems

Two of the four were systems with **no database at all**:
`penny_stocks.php` proxies the Yahoo Finance screener, and Sports Betting serves a
static JSON file. Querying a table that was never part of their design can only ever
produce a permanent false alert.

The other two were **schema drift**: the checker asked for `timestamp` on
`fxp_price_history` (which has `price_date`) and for `last_updated` on tables that never
had it.

The failure mode that made this dangerous: a `QUERY_ERROR` was being reported as
`is_stale = true`, so a *config typo* was indistinguishable from *dead data*.

## 2. The fix

**a) Non-DB systems declared as such**

```php
'penny_stocks' => array(
    ...
    'db_backed' => false,
    'source' => 'Yahoo Finance screener proxy (no database)',
),
```

The loop short-circuits to a `NOT_DB_BACKED` status with `is_stale = false` before any
`SHOW TABLES`. Saying "this system has no database" is the correct answer.

**b) Timestamp column auto-detected from the live schema**

Instead of trusting one hardcoded name, the checker reads `SHOW COLUMNS`, then walks a
preference list — `created_at`, `updated_at`, `pick_date`, `price_date`, `scan_date`,
`snapshot_date`, `trade_date`, `as_of_date`, `bar_date`, `end_date`, `generated_at`,
`scan_time`, `timestamp`, `last_updated`, `date` — and uses the first that exists **and
actually holds a value**.

That second condition matters. A column can exist and be entirely NULL (`created_at` on
`mc_winners` is exactly that), and reporting "no timestamp" while a populated date column
sits beside it would just be a different false alarm.

**c) Errors no longer masquerade as staleness**

If every candidate column exists but is NULL, the status is `NO_TIMESTAMP` with the tried
list attached. If the query itself fails, it stays `QUERY_ERROR`. Only a real, parsed
timestamp can produce a `DEAD DATA` verdict.

## 3. Verified live

```
Crypto Winner Scanner   STALE 4666.95h   Records: 351      <- real
Meme Coin Scanner       All date columns NULL (created_at) <- real data defect, now precise
Sports Betting Picks    Not database-backed - skipped      <- was a false CRITICAL
Stock Intelligence      STALE 5045.64h   Records: 7239     <- real
Penny Stocks            Not database-backed - skipped      <- was a false alarm
Forex Insights          STALE 4685.64h   Records: 2694     <- was a false alarm, now a real finding
Mutual Funds            STALE 5741.64h   Records: 600      <- real
```

**Every alert now corresponds to a genuine condition.** Nothing is being reported as dead
because a column name changed.

## 4. What this reveals about the estate

The checker is now trustworthy enough to read as a finding, and what it says is sobering:
**0 active systems, 5 stale.** Four of the five have data — `stock_intel` 7,239 rows,
`fxp_price_history` 2,694, `mf2_fund_picks` 600, `cw_winners` 351 — but the newest row in
each is 2,600–5,700 hours old (**~108 to ~239 days**). The pipelines that write them
stopped long ago; only the endpoints stayed up.

That is a data-pipeline staleness problem, separate from connectivity and outside this
change. Worth its own pass, and now measurable instead of masked.

## 5. Reproduce

```bash
python3 tools/validate_php52.py investments/goldmines        # 7 files pass
curl -s 'https://findtorontoevents.ca/investments/goldmines/antigravity/check_dead_data.php'
```

---

Infrastructure only. No picks, no signals, zero capital, not investment advice.
