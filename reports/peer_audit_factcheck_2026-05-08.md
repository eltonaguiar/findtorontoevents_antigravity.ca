# Peer Audit Fact-Check — 2026-05-08

**Target DB:** `ejaguiar1_stocks` @ `mysql.50webs.com` (MySQL 8.4.7), read-only SELECTs.
**Verifier:** Claude Opus 4.7 (1M ctx).
**Reproducer:** `python tools/peer_audit_factcheck_2026_05_08.py` + `tools/peer_audit_factcheck_supplement.py` (PYTHONPATH=.).

## TL;DR Verdict Table

| # | Finding                                       | Verdict            | Severity | Real Numbers                                    |
| - | --------------------------------------------- | ------------------ | -------- | ----------------------------------------------- |
| 1 | `at_consensus_picks` time-travel              | **CONFIRMED**      | CRITICAL | 5,268 / 9,188 (57.3%) closed_at < generated_at  |
| 2 | `consensus_tracked` 100% synthetic            | **DISPUTED**       | LOW      | 318 rows, 0 future-dated, only 6 round-entry    |
| 3 | `asset_class=''` empty enum across 3 tables   | **CONFIRMED**      | MEDIUM   | 2,490 + 490 + 279 = 3,259 empty (+ 44,925 UNKNOWN) |
| 4 | `simulation_grid` 100% LONG                   | **CONFIRMED**      | HIGH     | 6,000 / 6,000 LONG, 0 SHORT                     |
| 5 | `rapid_signals` exact 50/50 win/loss          | **PARTIALLY_TRUE** | MEDIUM   | 17,710 W / 17,618 L (50.13%); also 100% LONG, 5,237 zero-pnl-marked-win/loss |

---

## Finding 1 — `at_consensus_picks` time-travel (closed_at < generated_at)

### Verdict: CONFIRMED — **CRITICAL**

| Metric                                          | Value                       |
| ----------------------------------------------- | --------------------------- |
| Total rows                                      | 11,437                      |
| Rows with both timestamps                       | 9,188                       |
| Rows where `closed_at < generated_at`           | **5,268** (57.3% of dated)  |
| Min hours `closed_at` precedes `generated_at`   | 0                           |
| Max hours                                       | 149 (≈6.2 days)             |
| Average hours                                   | 35.66 (≈1.5 days)           |

### Sample (10 worst-case ids)

| id (truncated)                          | symbol     | direction | generated_at         | closed_at            |
| --------------------------------------- | ---------- | --------- | -------------------- | -------------------- |
| 84f84ad4-...-de6810bf98e3               | SOLUSDT    | LONG      | 2026-05-08 14:49:52  | 2026-05-07 00:41:54  |
| 8f3d431b-...-acd1c29942b3               | SOLUSDT    | LONG      | 2026-05-08 13:49:06  | 2026-05-07 15:27:09  |
| 333ada26-...-a5f3b1a86679               | SOLUSDT    | LONG      | 2026-05-08 12:48:39  | 2026-05-07 14:33:08  |
| c71b7e84-...-418657742061               | SOLUSDT    | LONG      | 2026-05-08 11:44:31  | 2026-05-07 14:33:08  |
| cb678cdc-...-994734542f12               | SOLUSDT    | LONG      | 2026-05-08 10:46:54  | 2026-05-07 14:33:08  |
| 03b10c83-...-816de963177a               | AVAXUSDT   | LONG      | 2026-05-08 10:46:54  | 2026-05-07 03:23:50  |
| 65628437-...-1e593ffd23c6               | SOLUSDT    | LONG      | 2026-05-08 09:47:24  | 2026-05-07 14:33:08  |
| 3ac81c65-...-6f5d49a30ce0               | ICPUSDT    | LONG      | 2026-05-08 06:51:41  | 2026-05-06 18:02:49  |
| 7def6622-...-1b478720817e               | ONDOUSDT   | LONG      | 2026-05-08 06:51:41  | 2026-05-07 13:09:00  |
| 25281756-...-8ebadf0ce6fa               | BTCUSDT    | LONG      | 2026-05-08 06:51:41  | 2026-05-08 03:08:58  |

### Breakdown by asset class / status

| asset_class | time_travel_rows | status | n     |
| ----------- | ---------------- | ------ | ----- |
| CRYPTO      | 4,810            | LOST   | 3,296 |
| MEMECOIN    | 305              | WON    | 1,891 |
| ''          | 153              | EXPIRED| 81    |

### Interpretation

The time-travel rows are NOT random. The pattern is: **the same `closed_at` repeats for every new pick on the same symbol** (SOLUSDT 2026-05-07 14:33:08 appears 4× in the sample with different generated_at values). This is the signature of the resolver re-stamping `closed_at` with the price-bar timestamp where TP/SL was historically hit — i.e., a row generated NOW gets `closed_at` retro-dated to whenever the bar that resolved it occurred.

Severity is CRITICAL because:
- LOST 3,296 / WON 1,891 / EXPIRED 81 — these picks already have outcomes attached. If `closed_at` is the bar timestamp but `generated_at` is the cron-write timestamp, **every PnL aggregation grouped by week/day will double-count or mis-bucket trades** (a pick "closed" yesterday but only generated today shows up in yesterday's WR ledger as if it were a same-day trade).
- This is the same class of bug as `feedback_noncrypto_resolver_live_close_bug.md`. Crypto path was supposed to be unaffected — this finding suggests it's NOT.

### Proposed mitigation

**Minimal SQL: defensive read-side filter (no DB write):**
```sql
-- Add to every aggregation query reading at_consensus_picks
WHERE (closed_at IS NULL OR closed_at >= generated_at)
```

**Code-side fix (preferred):** in `audit_trail/forward_validator.py` (or wherever `at_consensus_picks.closed_at` is set), clamp `closed_at = GREATEST(generated_at, bar_close_ts)`. The "bar that resolved" must be ≥ the pick's generation — otherwise the pick was generated using future information (look-ahead) and the row should be flagged invalid, not stored.

**Audit table addition:**
```sql
ALTER TABLE at_consensus_picks
  ADD COLUMN time_travel_flag TINYINT(1) GENERATED ALWAYS AS
    (CASE WHEN closed_at < generated_at THEN 1 ELSE 0 END) STORED;
CREATE INDEX idx_acp_timetravel ON at_consensus_picks (time_travel_flag);
```

---

## Finding 2 — `consensus_tracked` 100% synthetic

### Verdict: DISPUTED — peer's specific signals do NOT hold

| Peer claim                          | Reality                                |
| ----------------------------------- | -------------------------------------- |
| 318 rows total                      | 318 — **CONFIRMED**                    |
| All future-dated (`entry_date > NOW`) | **0 / 318** (0.0%) — **REFUTED**     |
| All round-number entry_price        | 6 / 318 (1.9%) round to whole — **REFUTED** |
| All `final_return_pct = 0`          | 83 / 318 (26.1%) — **REFUTED**         |

### Actual stats

| Metric                                      | Value           |
| ------------------------------------------- | --------------- |
| Total rows                                  | 318             |
| `entry_date > NOW()`                        | 0               |
| Round-to-0dp entry_price                    | 6               |
| Round-to-2dp entry_price                    | 298 (expected — DECIMAL stored as cents) |
| `final_return_pct = 0` total                | 83              |
| ↳ status `closed_neutral`                   | 44              |
| ↳ status `open`                             | 39              |
| Distinct entry_date values                  | 49 (2026-02-10 → 2026-04-27) |

### Status distribution

| status          | n   |
| --------------- | --- |
| closed_loss     | 131 |
| closed_win      | 104 |
| closed_neutral  | 44  |
| open            | 39  |

### Interpretation

`consensus_tracked` looks like **real backtest/forward-track data**, not synthetic:
- Entry dates span 76 days (Feb 10 → Apr 27 2026), all in the past.
- Prices are 2-decimal cents (e.g. AAPL 278.12, SBUX 99.45), normal equity quotes.
- Win/loss/neutral split (104/131/44) is plausible.
- The 83 zero-return rows are explicable: 39 are still `open` (no exit), 44 are `closed_neutral` (consensus_dropped before TP/SL hit). Zero-return is the *correct* value for those states, not synthetic noise.

Sample row #1 (AAPL): generated 2026-02-10, hit SL @ 261.73 on 2026-02-12 for −5.89% — fully consistent with a real losing trade.

The peer's claim conflates "neutral exit" (legitimate) with "synthetic" (fabricated). The table appears legitimate. **Severity LOW** — no fix recommended; instead document that `consensus_tracked` is the *equity stock-pick consensus tracker* (different domain from crypto `at_consensus_picks`) and label `closed_neutral` as expected noise in any aggregation.

---

## Finding 3 — `asset_class=''` empty enum across 3 tables

### Verdict: CONFIRMED — **MEDIUM**

| Table                  | Total    | empty_string | NULL | UNKNOWN literal | empty %  |
| ---------------------- | -------- | ------------ | ---- | --------------- | -------- |
| `at_raw_picks`         | 136,084  | **2,490**    | 0    | 4,326           | 1.83%    |
| `at_audit_events`      | 59,184   | **490**      | 0    | 40,596          | 0.83%    |
| `at_consensus_picks`   | 11,437   | **279**      | 0    | 3              | 2.44%    |

### Column definition (all 3 tables)

```
ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN')
```

### Key follow-up answer (the question peer asked)

**BOTH** `''` empty-string AND `UNKNOWN` literal coexist:

| Table                | UNKNOWN  | ''     |
| -------------------- | -------- | ------ |
| at_raw_picks         | 4,326    | 2,490  |
| at_audit_events      | 40,596   | 490    |
| at_consensus_picks   | 3        | 279    |

`at_audit_events` is dominated by `UNKNOWN` (68.6% of rows). `at_consensus_picks` mostly fills in correctly but uses empty-string almost-exclusively for the unfilled cases. This is **two orthogonal write paths** with inconsistent fallback conventions.

### Interpretation

Empty-string in an ENUM column is a MySQL-specific gotcha: when a write tries to insert a value not in the enum, MySQL stores `''` (the implicit zeroth element) instead of erroring (depending on `sql_mode`). This is happening because some writer is passing `None` or an unmapped value, and `STRICT_TRANS_TABLES` is off. Filters like `WHERE asset_class IN ('CRYPTO','EQUITY',...)` will silently drop these rows; `WHERE asset_class != 'UNKNOWN'` won't catch them either.

**Severity MEDIUM:** at_consensus_picks 2.44% empty means dashboard aggregations may exclude ~2.4% of the consensus picks from class-by-class WR/PF stats.

### Proposed mitigation

```sql
-- 1. Read-side: treat both as same bucket
WHERE COALESCE(NULLIF(asset_class,''), 'UNKNOWN') = 'UNKNOWN'

-- 2. Backfill empties to UNKNOWN (one-shot, NEEDS USER APPROVAL — write op):
UPDATE at_raw_picks SET asset_class='UNKNOWN' WHERE asset_class='';
UPDATE at_audit_events SET asset_class='UNKNOWN' WHERE asset_class='';
UPDATE at_consensus_picks SET asset_class='UNKNOWN' WHERE asset_class='';

-- 3. Prevent recurrence: tighten sql_mode on write connections
SET SESSION sql_mode = CONCAT(@@sql_mode, ',STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO');
```

Also: `audit_trail/asset_classification.py::resolve_asset_class()` should be the single source of truth — every writer must call it and it must never return `''`.

---

## Finding 4 — `simulation_grid` 100% LONG

### Verdict: CONFIRMED — **HIGH**

| Direction | Rows  | %      |
| --------- | ----- | ------ |
| LONG      | 6,000 | 100.0% |
| SHORT     | 0     | 0.0%   |

**Total rows:** 6,000. **Direction column present:** `direction` (string).

### Interpretation

The `simulation_grid` table holds parameter-sweep backtest results across `algorithm`, `algo_combo`, `tp`, `sl`, `hold_days`, `commission`, `regime`. **Zero SHORT scenarios** means every conclusion drawn from this grid is conditional on long-only execution. This is consistent with the existing `feedback_long_source_bias.md` finding — multiple writers in this codebase generate LONG-only universes.

**Severity HIGH** because:
- If anyone is using `simulation_grid` to set TP/SL defaults, hold_days, or commission tolerances, those parameters are tuned for long-only and will be **suboptimal for SHORT picks** in production.
- Bear-market regimes are inherently under-represented — the grid cannot tell us how `algo_combo` X performs in DOWN regimes when shorting.

### Proposed mitigation

**Code fix (whoever runs the parameter sweep):**
- In the simulation runner, swap `direction='LONG'` for `direction IN ('LONG','SHORT')` and double the row count to 12,000.
- For SHORT rows, invert the entry/exit logic (`exit = entry * (1 - tp_pct/100)` for TP, `exit = entry * (1 + sl_pct/100)` for SL).

**Read-side guard (until grid is regenerated):**
```sql
-- Annotate any aggregation that reads simulation_grid:
-- "Long-only — N=6000, no short scenarios in the universe"
SELECT '⚠ LONG-ONLY GRID' AS warning, COUNT(*) AS rows FROM simulation_grid;
```

---

## Finding 5 — `rapid_signals` exact 50/50 win/loss

### Verdict: PARTIALLY_TRUE — **MEDIUM**

### Peer claim vs reality

| Claim                              | Reality                                       |
| ---------------------------------- | --------------------------------------------- |
| Mathematically improbable 50/50    | 50.13% / 49.87% — **plausible, NOT impossible** |
| 35K closed signals                 | 35,328 — **CONFIRMED**                        |
| All `status = closed`              | 35,328 / 35,328 — **CONFIRMED** (no other states stored) |

### Outcome distribution

| outcome | n      | %      |
| ------- | ------ | ------ |
| win     | 17,710 | 50.13% |
| loss    | 17,618 | 49.87% |

For n=35,328 a true coin-flip 95% CI is roughly 49.48%–50.52%. **50.13% sits squarely inside** — this is statistically indistinguishable from random. Not "improbable balance," just lack of edge.

### BUT — the more damning signals (Q10-style ghost-row scan)

| pnl    | outcome | n     | flag                                          |
| ------ | ------- | ----- | --------------------------------------------- |
| -0.01  | loss    | 5,290 | constant pnl repeat                           |
| 0.03   | win     | 3,284 | constant pnl repeat                           |
| -0.02  | loss    | 3,185 | constant pnl repeat                           |
| **0.00**  | **win**  | **2,647** | **outcome=win with pnl=0** — invalid label    |
| 0.01   | win     | 2,616 | constant pnl repeat                           |
| **0.00**  | **loss** | **2,590** | **outcome=loss with pnl=0** — invalid label   |
| -0.03  | loss    | 1,933 | constant pnl repeat                           |

**5,237 rows (14.8%) have `pnl = 0` but are labeled win or loss** — that is the actual bug. The 50/50 split looks "too clean" because half of the zero-pnl rows are arbitrarily flipped each way, padding both buckets symmetrically.

| pnl summary stats | value     |
| ----------------- | --------- |
| n_total           | 35,328    |
| n_pos_pnl         | 15,063    |
| n_neg_pnl         | 15,028    |
| n_zero_pnl        | **5,237** |
| n_null_pnl        | 0         |
| avg_pnl           | $0.0106   |
| min_pnl           | -$0.17    |
| max_pnl           | $0.43     |

Bonus finding: **`signal_type` is 100% `long`** — same long-only bias as `simulation_grid`.

### Interpretation

- The "50/50 looks fake" instinct is reasonable but the math doesn't actually rule out edge-zero. What's real:
  - **~15% of rows have invalid outcome labels** (outcome ∈ {win,loss} but pnl = 0).
  - The realized PnL distribution (avg +$0.011, max +$0.43, min −$0.17) is **trivially small** — these are sub-cent-per-share trades. With strength values of 33-34, they look like 1-bar momentum signals on equities (XOM in the sample) where TP is ~3% from entry but actual exit happened at intraday tick precision.
  - 100% `long` again — same systemic bias.

**Severity MEDIUM**: the table can't be trusted for win-rate calculation as-is. Real WR after dropping zero-pnl rows = 15,063 / (15,063 + 15,028) = **50.05%** (still no edge).

### Proposed mitigation

```sql
-- Read-side: real WR (excludes invalid 5,237 zero-pnl rows)
SELECT
  COUNT(*) AS valid_signals,
  SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) / COUNT(*) AS true_wr
FROM rapid_signals
WHERE pnl != 0 AND status = 'closed';
```

```sql
-- Write-side (NEEDS USER APPROVAL): backfill outcome from pnl
UPDATE rapid_signals
SET outcome = CASE WHEN pnl > 0 THEN 'win'
                   WHEN pnl < 0 THEN 'loss'
                   ELSE 'neutral' END
WHERE status = 'closed';
```

Add a `neutral` value to the `outcome` enum (varchar today, so a no-op schema change).

---

## Audit Script Routing — which existing tool should catch each

| Finding | Script to extend                | New check                                                                        |
| ------- | ------------------------------- | -------------------------------------------------------------------------------- |
| 1       | `audit_outliers.py`             | Add `closed_at < generated_at` time-travel scan (per-table per-class breakdown)  |
| 2       | n/a — peer claim was wrong; document `consensus_tracked` semantics in `audit_dashboard/template.html` glossary instead |
| 3       | `audit_synthetic_patterns.py`   | Add empty-string ENUM scan: `WHERE asset_class = ''` across at_raw_picks, at_audit_events, at_consensus_picks |
| 4       | `audit_suspicious.py`           | Add direction-distribution invariant: any table with a `direction`/`signal_type` column where one side is >95% of rows = WARN |
| 5       | `audit_synthetic_patterns.py` + `audit_outliers.py` | (synthetic) constant-pnl repeat threshold + (outlier) outcome-label mismatch where outcome ∈ {win,loss} but pnl = 0 |

---

## Reproducer

```bash
cd e:\findtorontoevents_antigravity.ca
PYTHONPATH=. python tools/peer_audit_factcheck_2026_05_08.py
PYTHONPATH=. python tools/peer_audit_factcheck_supplement.py
```

Both scripts are READ-ONLY (`SELECT`-only, `SET SESSION MAX_EXECUTION_TIME=120000`, no DDL/DML).
