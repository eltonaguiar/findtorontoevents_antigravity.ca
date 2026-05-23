# DB Helper Scripts — Guide & Reusability Ranking

12 scripts in `database/db_helper_scripts/` plus 7 audit_*.py at repo root. This file ranks each by reusability and identifies candidates for scheduled Hermes jobs.

## Connection conventions

All scripts SHOULD use `audit_trail.mysql_client._create_connection()` (env-driven) instead of inline pymysql. Most Kimi scripts inline the connection — list-fix tracked below.

Env vars resolved by `_create_connection()`:
- `AUDIT_DB_HOST` (default `mysql.50webs.com`)
- `AUDIT_DB_USER` (default `ejaguiar1_stocks`)
- `AUDIT_DB_PASS` (default `stocks`)
- `AUDIT_DB_NAME` (default `ejaguiar1_stocks`)

For the backtests DB: `AUDIT_DB_USER=ejaguiar1_backtests AUDIT_DB_PASS=backtests AUDIT_DB_NAME=ejaguiar1_backtests`.

---

## Script inventory

### Tier 1 — High reusability + scheduling candidates

| script | source | purpose | runtime | reusability | schedule |
|---|---|---|---|---|---|
| `run_bigtable.py` | kimi | **Chunk-based aggregation on bt_backtest_trades 30M rows** (200K-row chunks, reconnect-per-chunk, status/direction/asset/PnL counters, NULL detectors) | ~25-40 min | **VERY HIGH** — only safe pattern for this table on shared host | **Weekly** (Sun 03:00 UTC) |
| `run_all.py` | kimi | Small-table validation (backtests DB): bt_backtest_runs, at_incubator/at_large, perm_id overlap, indexed-column queries on bt_backtest_trades | ~3-5 min | HIGH — comprehensive baseline | **Daily** (06:00 UTC) |
| `run_info.py` | kimi | DB metadata: tables, sizes, indexes, FK relationships | <1 min | HIGH | **Daily** |
| `audit_synthetic_patterns.py` | freebuff | Synthetic-data detector (round prices, weekend trades, return-calc mismatches, repeated values) | <1 min | HIGH but scoped to `consensus_tracked` only — needs extension to `bt_backtest_trades` | **Daily** |
| `audit_outliers.py` | freebuff | Statistical outlier detection (IQR-based) | <1 min | HIGH — extend to per-class | **Daily** |
| `audit_suspicious.py` | freebuff | Anomaly flagging: extreme returns, repeated entry prices, test tickers, extreme WRs | <1 min | HIGH | **Daily** |

### Tier 2 — Reusable for ad-hoc forensics

| script | source | purpose | reusability |
|---|---|---|---|
| `run_indexed.py` | kimi | Indexed-column queries (status, symbol, strategy, asset_class) on bt_backtest_trades | MEDIUM — fast indexed scans |
| `run_queries.py` | kimi | Generic query runner | MEDIUM |
| `run_small.py` | kimi | Small-table queries | LOW — superseded by `run_all.py` |
| `audit_comprehensive_report.py` | freebuff | Full-spectrum audit | MEDIUM — slow, runs many checks |
| `audit_final_summary.py` | freebuff | Summary aggregation | LOW |
| `audit_detailed.py` | freebuff | Row-level inspection | LOW |
| `audit-daily.py` | freebuff | Daily run, supports 15GB SQL dump input | HIGH for offline replay; LOW for live ops |
| `sql_dump_analyzer.py` | (this session) | Streaming phpMyAdmin dump analyzer | MEDIUM (multi-line state-machine bug) |

### Tier 3 — One-shot / can archive

| script | source | purpose |
|---|---|---|
| `micro_1.py`, `micro_2.py`, `micro_3.py`, `micro_4.py` | kimi | One-off probes used during the 2026-05-08 Kimi review. Keep as historical reference. |

---

## Top-priority reusable queries (ranked by ROI)

### 1. **Tier verdict per asset_class** (Q1-style, but with full status enum)

```sql
WITH terminal AS (
  SELECT *, CASE WHEN pnl_pct>0 THEN 'WIN'
                 WHEN pnl_pct<0 THEN 'LOSS'
                 ELSE 'FLAT' END AS terminal_outcome
  FROM bt_backtest_trades
  WHERE status IN ('WON','WIN','TP_HIT','CLOSED_TP','LOST','LOSS','SL_HIT','CLOSED_SL','closed','CLOSED','expired')
    AND pnl_pct IS NOT NULL
)
SELECT asset_class,
  COUNT(*) AS n,
  ROUND(100*SUM(terminal_outcome='WIN')/COUNT(*),2) AS wr_pct,
  ROUND(SUM(GREATEST(pnl_pct,0))/NULLIF(-SUM(LEAST(pnl_pct,0)),0),3) AS pf,
  ROUND(SUM(pnl_pct),2) AS sum_pnl
FROM terminal GROUP BY asset_class ORDER BY n DESC;
```

Why first: drives every Tier-1/Tier-2 verdict per `docs/PERFORMANCE_CHARTER.md`. Schedule **daily**.

### 2. **Ghost-row detector** (Q10-style)

```sql
SELECT strategy, symbol, direction, ROUND(pnl_pct,4) AS pnl, COUNT(*) AS n
FROM bt_backtest_trades
WHERE pnl_pct IS NOT NULL
GROUP BY strategy, symbol, direction, ROUND(pnl_pct,4)
HAVING n > GREATEST(20, 0.001 * (SELECT COUNT(*) FROM bt_backtest_trades x WHERE x.symbol=bt_backtest_trades.symbol))
ORDER BY n DESC LIMIT 50;
```

Why second: detects new ghost cohorts (the MATIC/quan_engine pattern). Schedule **daily** with alert if new (strategy, symbol, direction, pnl) tuple appears with n>1000 vs prior day.

### 3. **Forward-validator freshness**

```sql
SELECT
  MAX(imported_at) AS last_term_write,
  TIMESTAMPDIFF(HOUR, MAX(imported_at), NOW()) AS hours_ago,
  COUNT(*) AS terminal_n_24h
FROM bt_backtest_trades
WHERE status IN ('WON','WIN','TP_HIT','CLOSED_TP','LOST','LOSS','SL_HIT','CLOSED_SL')
  AND imported_at > NOW() - INTERVAL 24 HOUR;
```

Why third: detects the smoking-gun freeze pattern. Schedule **hourly**, alert if `hours_ago > 26`.

### 4. **PnL recompute integrity check**

```sql
SELECT asset_class,
  COUNT(*) AS computable,
  SUM(ABS(pnl_pct - (exit_price-entry_price)/entry_price*100) > 1) AS gt1pct,
  ROUND(100*SUM(ABS(pnl_pct - (exit_price-entry_price)/entry_price*100) > 1)/COUNT(*), 2) AS gt1pct_pct
FROM bt_backtest_trades
WHERE entry_price > 0 AND exit_price > 0 AND pnl_pct IS NOT NULL
GROUP BY asset_class ORDER BY gt1pct DESC;
```

Why: 67-79% mismatch found on `at_raw_picks`; verify `bt_backtest_trades`. Schedule **weekly**.

### 5. **at_consensus_picks time-travel detector** (F4)

```sql
SELECT
  COUNT(*) AS total,
  SUM(closed_at < generated_at) AS time_travel_n,
  ROUND(AVG(TIMESTAMPDIFF(HOUR, closed_at, generated_at)) FILTER (WHERE closed_at < generated_at), 2) AS avg_hours_ahead,
  MAX(TIMESTAMPDIFF(HOUR, closed_at, generated_at)) AS max_hours_ahead
FROM at_consensus_picks
WHERE closed_at IS NOT NULL AND generated_at IS NOT NULL;
```

Schedule **daily** (FILTER syntax requires MySQL 8.0+ — drop if needed).

### 6. **Discord signal_tier writer health** (F8)

```sql
SELECT
  COUNT(*) AS total,
  SUM(signal_tier IS NULL) AS null_n,
  ROUND(100*SUM(signal_tier IS NULL)/COUNT(*), 2) AS null_pct,
  signal_tier
FROM at_discord_notifications
WHERE event_type = 'PICK_POSTED' AND created_at > NOW() - INTERVAL 7 DAY
GROUP BY signal_tier;
```

Schedule **daily**, alert if `null_pct > 10%`.

### 7. **lm_signals expire-without-resolve detector** (NEW-P0-8)

```sql
SELECT
  COUNT(*) AS expired_n,
  SUM(exit_price = 0 OR exit_price IS NULL) AS no_resolve_n,
  ROUND(100*SUM(exit_price = 0 OR exit_price IS NULL)/COUNT(*), 2) AS no_resolve_pct
FROM lm_signals
WHERE status = 'expired' AND expired_at > NOW() - INTERVAL 7 DAY;
```

Schedule **daily**, alert if `no_resolve_pct > 20%` (was 96.2% on 2026-05-08).

### 8. **Confidence calibration drift** (F5)

```sql
SELECT asset_class,
  CASE WHEN confidence IS NULL THEN 'NULL'
       WHEN confidence < 0.5 THEN '<0.5'
       WHEN confidence < 0.7 THEN '0.5-0.7'
       WHEN confidence < 0.85 THEN '0.7-0.85'
       ELSE '>=0.85' END AS conf_bucket,
  COUNT(*) AS n,
  ROUND(100*SUM(pnl_pct>0)/COUNT(*), 2) AS wr_pct,
  ROUND(SUM(GREATEST(pnl_pct,0))/NULLIF(-SUM(LEAST(pnl_pct,0)),0), 3) AS pf
FROM bt_backtest_trades
WHERE pnl_pct IS NOT NULL
  AND status NOT IN ('OPEN')
GROUP BY asset_class, conf_bucket
ORDER BY asset_class, conf_bucket;
```

Schedule **weekly**. Alert if `wr_pct(>=0.85)` < `wr_pct(<0.5)` (inversion regression).

### 9. **trading_picks WON/PnL contradiction** (Kimi #1)

```sql
SELECT status,
  COUNT(*) AS n,
  ROUND(AVG(pnl_pct), 4) AS avg_pnl,
  MIN(pnl_pct) AS min_pnl, MAX(pnl_pct) AS max_pnl,
  SUM(pnl_pct < 0) AS negative_pnl
FROM trading_picks
WHERE status IN ('WON','LOST','SL_HIT','TP_HIT','closed_win','closed_loss')
GROUP BY status;
```

Detects the WON-with-negative-PnL anomaly. Schedule **daily**, alert if `WON.avg_pnl < 0` or `LOST.avg_pnl > 0`.

### 10. **Outcome coverage** (Kimi #2)

```sql
SELECT
  (SELECT COUNT(*) FROM at_raw_picks) AS raw_picks_total,
  (SELECT COUNT(*) FROM at_signal_outcomes) AS outcomes_tracked,
  ROUND(100.0 * (SELECT COUNT(*) FROM at_signal_outcomes)/(SELECT COUNT(*) FROM at_raw_picks), 4) AS coverage_pct;
```

Schedule **daily**, alert if coverage drops <0.5% (currently 0.09%).

---

## Recommended Hermes scheduling

Reference: `docs/cross_pc_protocol_v1.md` + Hermes cron capabilities. Suggested cron table:

| job | schedule (UTC) | command | output |
|---|---|---|---|
| `db_freshness_check` | hourly | run query 3 (forward-validator freshness) | alert if hours_ago>26 |
| `db_synthetic_patterns_audit` | daily 05:00 | extended `audit_synthetic_patterns.py` against `bt_backtest_trades` | `database/reports/synthetic_$(date).md` |
| `db_outliers_audit` | daily 05:15 | `audit_outliers.py` | `database/reports/outliers_$(date).md` |
| `db_suspicious_audit` | daily 05:30 | `audit_suspicious.py` | `database/reports/suspicious_$(date).md` |
| `db_tier_verdict` | daily 06:00 | query 1 (tier verdict per asset_class) | `database/reports/tier_$(date).json` + alert on Tier-2 regression |
| `db_ghost_rows` | daily 06:15 | query 2 (ghost-row detector) | alert if new (strategy, symbol, direction, pnl) cohort appears with n>1000 |
| `db_resolver_health` | daily 06:30 | queries 5+6+7 (time-travel + signal_tier + lm_signals expire) | alert thresholds in queries above |
| `db_won_pnl_contradiction` | daily 06:45 | query 9 | alert if WON avg pnl<0 |
| `db_outcome_coverage` | daily 07:00 | query 10 | alert if coverage drops |
| `db_pnl_recompute_integrity` | weekly Sun 04:00 | query 4 | trends in `database/reports/pnl_integrity_weekly.md` |
| `db_confidence_calibration` | weekly Sun 04:30 | query 8 | alert on inversion regression |
| `db_bigtable_chunked_aggregation` | weekly Sun 05:00 | `run_bigtable.py` | `database/reports/bigtable_$(date).json` (full 30M-row scan, ~30 min) |
| `db_full_health_dashboard` | weekly Sun 06:00 | aggregate all above + render to dashboard | `database/reports/health_$(date).html` |

### Hermes job spec template

```yaml
name: db_tier_verdict
schedule: "0 6 * * *"
runtime: python3
working_dir: /e/findtorontoevents_antigravity.ca
env:
  AUDIT_DB_HOST: mysql.50webs.com
  AUDIT_DB_USER: ejaguiar1_stocks
  AUDIT_DB_PASS: stocks
  AUDIT_DB_NAME: ejaguiar1_stocks
  PYTHONUTF8: "1"
command: |
  python -c "
  from audit_trail.mysql_client import _create_connection
  c=_create_connection(); cur=c.cursor()
  cur.execute('SET SESSION MAX_EXECUTION_TIME=120000')
  cur.execute('''<query 1 SQL>''')
  rows=cur.fetchall()
  ..."
output: database/reports/tier_$(date +%Y-%m-%d).json
alert:
  channel: discord
  webhook_env: DISCORD_AUDIT_WEBHOOK
  trigger:
    - any_class.pf < 0.5
    - any_class.wr_pct < 30
on_failure:
  retry_count: 2
  retry_backoff: 5min
```

(See `tools/swarm/comment_poster.ps1` for existing Discord posting infrastructure.)

---

## Refactor todos

To make Tier-1 scripts production-grade:

1. Replace inline `pymysql.connect(host='mysql.50webs.com'...)` with `from audit_trail.mysql_client import _create_connection` everywhere.
2. Replace `/mnt/agents/output/` paths (Kimi scripts) with `os.environ.get('DB_REPORTS_DIR', 'database/reports/')`.
3. Add `--db {stocks,backtests}` CLI flag instead of hardcoded DB.
4. Add structured-logging hooks (write to `logs/db_audit/$(date).jsonl` per run for trend tracking).
5. Wire to `tools/swarm/comment_poster.ps1` for Discord alerts on threshold breach.

These would convert the kimi run_*.py scripts from one-off researcher tools into ops-ready cron jobs.

---

## What NOT to schedule

- `bt_backtest_trades` full `COUNT(*)` queries — timeout-prone on shared host (29M+ rows). Use indexed/PK-bounded scans only.
- Anything that JOINs `bt_backtest_trades` to `bt_backtest_runs` until P1-7 (terminal_outcome) or backtest_run_id backfill is done — 100% NULL FK.
- Heavy window functions over the full table — split per-class via `WHERE asset_class=` (idx_bt_asset).
