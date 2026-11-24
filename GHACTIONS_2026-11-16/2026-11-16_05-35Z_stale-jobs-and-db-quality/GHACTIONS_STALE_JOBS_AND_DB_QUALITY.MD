# GHACTIONS — stale jobs, failures without a later success, and DB data quality

**Stamp:** 2026-11-16 ~05:35Z · **Branch audited:** `main` (`d9800a192a4b` at sweep time)
**Method:** `python3 tools/gha_latest_run_check.py --fresh --workers 8` (360 workflows, 696 API
calls, annotations on) + `reports/gha_latest_run_check.json` + read-only MySQL patterns
(`ejaguiar1_stocks`, `ejaguiar1_backtests`).

---

## 1. Stale-job / failure census (fresh, all 360 workflows)

| Bucket | Count | Meaning |
|---|---|---|
| latest = success | 325 | healthy |
| never run at all | 19 | created but zero runs — archive candidates |
| unknown (no conclusion yet) | 12 | disabled/never-finished entries |
| latest = cancelled | 1 | no later success |
| latest = failure | 3 | 1 on `main`, 2 on dead branches |
| startup failures (0 jobs created) | 0 | the two 0-job workflows seen earlier now exist only as `.yml.disabled` |
| masked failures | 0 | — |

**The only genuine `main` failure: Feed Health Check** (run 43806313904, 04:48:47Z, attempt 2).
Cause and fix are in `updates/2026-11-16-feed-health-optional-shadow-sources.md`:
`pm_kalshi_re_signals` / `pm_polymarket_re_signals` were registered in `JSON_PICK_SOURCES`
while their producers run best-effort, so an empty shadow feed failed the hourly gate.
Now reported as an OPTIONAL warning; required sources still fail the gate.

**The other two failures are not on `main` and need no code change:**

| Workflow | Branch / event | Disposition |
|---|---|---|
| Mermaid Test Deploy | `wiring`, push, 2026-11-15 18:23 | dead test branch (`git failed with exit code 128`); archive the branch, don't fix |
| DB Secret Scan | `fix/md-action-items-2026-06-05`, PR, 2026-06-05 | flags `stocks1234560`; `git grep` on `main` = **0 files** — stale June PR, close it |

### 19 never-run workflows (archive → observe → delete)

Dynamic Runner Template · Battleground Mass Backtest · Clear Channel Command · Closed Picks
Command · DB Credentials Test · Deploy fc/api/.env to GoDaddy (torontoevent.net) · Deploy FC API
Hotfix (3 domains) · Deploy MOVIESHOWS3 Hotfix · Deploy Strategy Bundle · Fast Stocks Competition
High Frequency Scanner · Fix Ghost Cards & Thumbnails All Sites · MySQL Dedup Fix · REAL 2-HOUR
CHALLENGE - Live Market Data · Resolver Step 5-6 — at_raw_picks Backfill · Resolver Step 7 —
active_picks_sync APPLY · RL Agent (PPO) Train & Predict · Test Fast Variants · Won PNL
Contradiction Backfill · WSL Runner Manager

These are manual/hotfix workflows that have **never executed once**. They cost nothing at rest,
but they inflate the UI and hide real signal. `Resolver Step 5-6/7` matter: if the backfill were
supposed to run, its never-run state explains part of the open-row bloat below.

### 8 skipped job groups (conditional, mostly legitimate)

`Analyst Tracker` (scrape-analysts) · `AsterDEX Paper Trading` (daily-summary) · `Claude Code
Gainer ML Tracker` (weekly-retrain) · `ALPHA Dynamic Runner` (wsl-direct) · `Live Trading Monitor`
(hour-learning) · `Scrape events` (scrape). **One is not legitimate:** `Master Automation
Scheduler` skips **all three** of its groups (`weekly-tasks`, `four-hourly-tasks`,
`daily-tasks`) — the scheduler is not scheduling anything; it is a zombie window that looks
healthy because its run concludes "success".

---

## 2. Read-only SQL data-quality patterns

**Connection:** `mysql.50webs.com` (MySQL 8.4.7), users `ejaguiar1_stocks` /
`ejaguiar1_backtests`, passwords from `DB_PASS_STOCKS` / `DB_PASS_BACKTESTS` env.
**Note:** `~/dbpasses.txt` holds **API keys only** (AIHUBMIX/LING/…); it contains no MySQL
credentials. The repo convention (`tools/db_env.py`, `tools/cleanup_ghost_rows.py`) reads the DB
password from the environment, which is what was used here.

### 2.1 Freshness — the lanes that write are fine, two lanes are frozen

| Table | Rows | Newest activity | Verdict |
|---|---|---|---|
| `trading_picks` | 144,567 | created 04:54Z, updated 05:00Z | GREEN |
| `at_raw_picks` | 112,690 | recorded 05:10Z | GREEN |
| `at_signal_outcomes` | 50,804 | created 03:51Z, closed 03:50Z | GREEN |
| `at_signal_outcomes.intrabar_resolved_at` | — | 2026-11-15 13:21Z | ~16h = YELLOW |
| `trading_picks.intrabar_resolved_at` | 15,027 resolved | **2026-06-09** | RED — frozen 5 months |
| `lm_signals.resolved_at` | 111,384 | **2026-02-16** | RED — frozen 9 months |

`lm_signals` keeps receiving signals (04:53Z today) and marks them `expired` (110,985 rows)
without ever resolving again — the resolution lane silently died in February, the same class of
failure the intrabar threshold comments in `tools/db_freshness_check.py` were written for.

### 2.2 Open-row bloat

`trading_picks`: **91,855 OPEN** vs **21 ACTIVE** (63.5% of the table).

| Age of OPEN rows | Count |
|---|---|
| > 30 days | 74,394 |
| 7–30 days | 13,146 |
| 1–7 days | 3,374 |
| < 1 day | 941 |

Worst offenders (open rows older than 30 days): `multi_asset_copytrader` 25,231 (oldest
2026-06-01) · `non_crypto_consensus` 14,408 · `regime_terminal` 5,405 · `short_dominant_engine`
4,140 · `alpha_engine_fast` 4,107 · `combined_confidence_strategy` 3,985 · `forex_copy_trader`
2,917 · `copy_trader_polymarket` 2,742.

Separately, `at_local_picks` holds **108,598,675 rows with status `ACTIVE`** (13.8 GB table,
information_schema estimates 76M). That is the single largest storage/false-truth surface in the
DB — local-run picks that never resolve or expire.

### 2.3 Duplicates

- `trading_picks`, grouped by `(symbol, direction, strategy, DATE(created_at))`:
  **14,568 duplicate groups → 105,669 excess rows**.
  Worst: `OJ=F SHORT commodity_carry_momo_double_sort` ×55 · `CL=F LONG` ×50 ·
  `JUPUSDT` (blank direction/strategy) ×54 · `WIFUSDT` ×50 · `AVAXUSDT` ×48.
- Exact-content duplicates (same prices and timestamp): 267 groups — small, likely re-ingest.
- `at_raw_picks.dedup_hash`: **0** duplicate hashes — the raw layer is clean; duplication is
  introduced downstream.

### 2.4 Degenerate fields

| Defect | `trading_picks` | `at_raw_picks` |
|---|---|---|
| LONG with `take_profit < entry_price` | 54 | 459 |
| LONG with `stop_loss > entry_price` | 85 | 306 |
| SHORT with `take_profit > entry_price` | 1,271 | 2,508 |
| SHORT with `stop_loss < entry_price` | 1,278 | 2,535 |
| **total impossible geometry** | **2,688** | **5,808** |
| blank `direction` | 387 | — |
| blank `strategy` | 1,194 | — |
| blank `category` | 2,559 | — |
| non-positive `entry_price` / `take_profit` / `stop_loss` | 136 / 313 / 498 | — |
| `closed_at < created_at` | 1,810 | — |

The 1,810 inverted timestamps are all `ml_enhanced_*` rows where `closed_at` was truncated to
`00:00` of the same day while `created_at` kept the 13:38 timestamp — a date-only write, not a
time-travel bug, but it corrupts any holding-time metric built on those rows.
`at_raw_picks` also has **17,875 rows** where `|signal_timestamp − recorded_at| > 24h`.

### 2.5 PnL integrity — two rows poison a whole asset class

Only two closed rows exceed |100%|, but they dominate the aggregate:

| id | symbol | class | outcome | pnl_pct | entry | exit |
|---|---|---|---|---|---|---|
| 687,611 | SHIBUSDT | COMMODITY | SL_HIT | **1,000,000.00** | 0.000 | 4,016.416 |
| 1,426,460 | ARBUSDT | CRYPTO | TP_HIT | **18,611.39** | 0.001 | 0.118 |

Effect on `at_signal_outcomes` per class:

| Class | With outliers | Honest (excl. |pnl|>100) |
|---|---|---|
| COMMODITY | avg **+1,968.44**, PF **6,690** | avg **−0.06**, PF **0.79** (n=507) |
| CRYPTO | avg +0.98, PF 3.08 | avg +0.10, PF **1.21** (n=21,158) |

"COMMODITY is the strongest class" is entirely an artifact of one SHIBUSDT row. Honest
`at_signal_outcomes` view: CRYPTO 50.9%/PF 1.21 · FOREX 48.6/2.05 (n=1,984) · EQUITY 53.8/1.35
(n=728) · ETF 40.7/1.16 (n=189) · FUTURES 58.8/6.84 (n=136) · MEMECOIN 42.6/0.51 (n=129) · BOND
21.8/1.02 (n=78) · COMMODITY 28.2/0.79.

`trading_picks` closed rows (`closed_at IS NOT NULL`) tell the same story with different lane
weights: CRYPTO 46.7%/1.04 (n=21,977) · FOREX 48.4/1.38 (n=17,641) · COMMODITY 46.7/1.13 (n=7,444)
· EQUITY 38.5/**0.97** (n=3,466) · FUTURES 48.5/1.57 (n=458) · ETF 43.5/1.22 (n=391) · bond
41.1/0.77 (n=224) · meme 35.2/0.84 (n=88).

**No class with n ≥ 500 clears PF 1.5.** That independently supports the site's own
`money_ready_verdict.json` (4 NOT_READY / 1 WATCH / 5 INSUFFICIENT_DATA).

---

## 3. Reconciliation with `findtorontoevents.ca/audit`

The page's headline per-class figures (`CRYPTO 35.8% / PF 0.916 / n=3,716`, etc.) come from the
**intrabar-resolved subset** of `at_signal_outcomes`, which is a different population from either
table's full closed set — so page-vs-DB differences are lane differences, not necessarily errors.
What the page cannot currently show, and the DB does:

1. one row can move a class's PF from 0.79 to 6,690 (no outlier guard in the page's class view);
2. two intrabar lanes disagree: `at_signal_outcomes` is 16h fresh, `trading_picks` is frozen
   since 2026-06-09 — any page metric derived from the latter is 5 months stale;
3. 91,855 OPEN rows (74,394 older than 30 days) inflate "active picks" and unrealized PnL.

## 4. Recommended actions, in order

1. **Clamp PnL at ingest** (`|pnl_pct| <= 100` for non-leveraged classes) and quarantine the two
   offending rows; until then, exclude `|pnl_pct| > 100` from every class aggregate.
2. **Resolve the open-row backlog**: expire/close OPEN rows older than the horizon, then re-check
   `at_local_picks` (108.6M ACTIVE) for a truncation or dedupe policy.
3. **Re-arm the two frozen lanes**: `lm_signals` resolution (since Feb) and
   `trading_picks.intrabar_resolved_at` (since Jun 9). The never-run `Resolver Step 5-6/7`
   workflows are the likely intended owners.
4. **Reject or repair impossible geometry at write time** (5,808 + 2,688 rows) and fix the
   `ml_enhanced` `closed_at` date-only write.
5. **Archive the 19 never-run workflows** and retire `Master Automation Scheduler`; close the two
   dead branches/PRs behind the non-`main` failures.
6. Keep the Feed Health gate tight — the optional list covers only the two shadow PM feeds.

## 5. Reproduce

```bash
python3 tools/gha_latest_run_check.py --fresh --workers 8     # 360 workflows, annotations
python3 - <<'PY'                                              # DB patterns, read-only
import os, pymysql
c = pymysql.connect(host="mysql.50webs.com", user="ejaguiar1_stocks",
                    password=os.environ["DB_PASS_STOCKS"], database="ejaguiar1_stocks",
                    connect_timeout=15, read_timeout=200)
cur = c.cursor(); cur.execute("SET SESSION MAX_EXECUTION_TIME=60000")
cur.execute("SELECT status, COUNT(*) FROM trading_picks GROUP BY 1 ORDER BY 2 DESC")
print(cur.fetchall())
PY
```
