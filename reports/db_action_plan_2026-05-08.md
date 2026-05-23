# DB Action Plan + QA + Future-Watch — 2026-05-08

Synthesized from:
- `reports/db_action_todos_2026-05-07.md` (24 todos)
- `reports/db_master_synthesis_2026-05-07.md` (live forensic findings)
- `swarm_runs/db_action_3phase_20260508T140003Z/` (5-engine swarm: claude/deepseek/kilo healthy; gemini partial; xai empty)
- Existing audit infra: `audit_trail/mysql_client.py`, `audit_synthetic_patterns.py`, `audit_outliers.py`, `audit_suspicious.py`, `audit_comprehensive_report.py`, `AUDIT_BLUEPRINT.md`

Swarm consensus on 2 critical design questions:

| question | verdict (3/3) | reasoning |
|---|---|---|
| **Quarantine vs DELETE** for P0 #1+#2 ghosts | **Quarantine** at `dashboard_generator.py` ingest filter | DELETE on 30M rows = index fragmentation, binlog bloat, no rollback path. Quarantine = easy rollback + forensic. Add `is_quarantined` flag on `bt_backtest_trades` for permanent marker. |
| **STORED vs VIRTUAL** generated `terminal_outcome` col | **STORED** | VIRTUAL recomputes per-SELECT (~3ms × 30M = 90s/scan, no index). STORED = 240MB disk + indexable. WHERE clauses 99% of queries hit this column. |

---

## Highest risk + biggest blind spots (Claude consensus)

### Highest risk (act first)
> **The 35-day forward-validator freeze (P0-5) is the single most dangerous open issue.** For 35 days, all non-CRYPTO positions have been entering OPEN status and never resolving. The dashboard is making capital allocation decisions on 2026-04-02 performance snapshots; an unknown number of OPEN rows represent real closed positions whose actual PnL is invisible.

### Biggest blind spot
> **The OPEN population is completely uncharacterized.** Table has 29.4M rows; terminal rows are a minority. No query in the 24-item plan counts OPEN rows by asset class × strategy × age. If 10-20M OPEN rows represent 35 days of unresolved positions, "cleaned" post-quarantine metrics are still on a frozen snapshot. EQUITY/COMMODITY/BOND have NOT been swept for constant-pnl cohorts — `challenge_200_trades` 57.1% WR could itself be contaminated by an undiscovered ghost cohort.

### Already-known gemini hallucinations (verified WRONG)

| gemini claim | actual |
|---|---|
| 4,420 total picks | **136,050** |
| 97.6% PnL recompute mismatch | 67.7-79.9% on **computable rows only** (12.3% of total) |
| 86% missing strategy | 5.7% |
| Mixed BUY/SELL/LONG/SHORT vocab | LONG/SHORT only |
| 891 rebranded MATIC rows | unverified, likely conflated |

Gemini did surface the **PnL recompute integrity issue** correctly in direction, but its scope numbers are useless. Verify before citing.

---

## Execution sequence (consensus order)

### Wave 0 — Pre-work (no DB writes, run today)

| step | todo | command | deliverable |
|---|---|---|---|
| 0a | OPEN-population census | `audit_open_population.py` (NEW) | row count by (asset_class, strategy, age_bucket) for status=OPEN |
| 0b | Run existing `audit_synthetic_patterns.py` | already exists | baseline. Found 95 flags / "HIGHLY SYNTHETIC" verdict on `consensus_tracked` |
| 0c | Run existing `audit_suspicious.py` | already exists | found 14 strategies w/ extreme expectancy, 54 w/ WR>90% or <10% |
| 0d | Sweep EQUITY/COMMODITY/BOND for constant-pnl cohorts | `audit_bt_synthetic.py` (NEW, generalizes #0b to bt_backtest_trades 30M rows by asset_class) | ghost-row counts per class |
| 0e | PnL recompute mismatch on `bt_backtest_trades` | NEW SQL | actual mismatch %; cap-confirmed |

### Wave 1 — Quarantine + freeze investigation (P0; reversible; deploy in this order)

| step | todo | implementation | rollback | verify |
|---|---|---|---|---|
| 1 | **P0-5 Forward-validator freeze diagnosis** | runbook below | n/a (read-only) | identify root cause |
| 2 | **P0-1+P0-2** Quarantine ingest filter | edit `audit_trail/dashboard_generator.py:_filter_picks` to add `_is_quarantined()` checks | revert single-file commit | re-run Q1; CRYPTO PF >0.42 (was 0.30) |
| 3 | **P0-3** Phantom-row drop | same file, `(status='EXPIRED' AND pnl_pct=0 AND exit_price=entry_price)` drop | same revert | EQUITY terminal count > 0 in dashboard payload |
| 4 | **P0-4** Investigate `at_consensus_picks` EQUITY 2.2% WR (n=403) | read-only — `git blame` on consensus filter for EQUITY path | n/a | root cause documented in `reports/at_consensus_equity_postmortem.md` |
| 5 | **P0-6** Investigate quan_engine constant-pnl writer | grep `outcome_resolver.py` + `quan_engine`-named modules; trace where `pnl_pct=-15.0` is set | n/a | bug location + minimal repro |

### P0-5 forward-validator freeze diagnosis runbook (deepseek + claude consensus)

```
Step 1: git log --since="2026-04-02" -- alpha_engine/forward_validator.py outcome_resolver.py audit_trail/audit_sync.py audit_dashboard/database_consolidation.py
        — pinpoint commits in the freeze window. Suspect any deploy on 2026-04-02 ± 1 day.

Step 2: gh run list --branch main --workflow alpha-engine-live.yml --created ">=2026-04-02" --limit 50
        + gh run view <id> for any RED runs. The freeze likely traces to a workflow that started failing then.

Step 3: SHOW PROCESSLIST on mysql.50webs.com (verify no resolver connection is hung).
        SELECT MAX(imported_at) FROM bt_backtest_trades WHERE status='WON';  — last terminal write timestamp.

Step 4: SELECT COUNT(*), MAX(imported_at) FROM bt_backtest_trades WHERE imported_at > NOW() - INTERVAL 1 HOUR;
        — confirm any recent writes at all.

Step 5: If no recent writes: revert the 2026-04-02 commit on a feature branch, redeploy, watch one cycle of `alpha-engine-live.yml`, confirm WON/LOST/expired statuses resume writing.
```

### Wave 2 — Schema + importer (P1)

| step | todo | implementation | order constraint |
|---|---|---|---|
| 6 | **P1-7** Add `terminal_outcome` STORED column + index | `ALTER TABLE bt_backtest_trades ADD COLUMN terminal_outcome ENUM(...) GENERATED ALWAYS AS (...) STORED, ADD INDEX idx_bt_terminal_outcome (terminal_outcome)` | requires Wave 1 done so migration sees clean cohort |
| 7 | **P1-8** Add `paper_trade BOOL DEFAULT FALSE` + heuristic backfill | `ALTER` + `UPDATE ... SET paper_trade=TRUE WHERE confidence IS NULL AND raw_data IS NULL AND pnl_pct=0` | independent |
| 8 | **P1-9** Add `exit_reason ENUM(...)` | `ALTER` + populate from existing status mapping | needs P1-7 |
| 9 | **P1-10** Importer fix: populate `confidence` + `raw_data` | edit upstream importer (`alpha_engine/audit_sync.py` + JSON loaders) | independent |
| 10 | **P1-11** `source_system` virtual column (kilo's regex) | `ALTER TABLE ... ADD COLUMN source_system VARCHAR(80) GENERATED ALWAYS AS (REGEXP_REPLACE(source_db,'^.*/([^/]+)/data/.*$','$1')) VIRTUAL` | independent; VIRTUAL is fine since dashboard joins it once per render |
| 11 | **P1-12** Status enum normalize | bulk UPDATE rewriting WIN/WON/TP_HIT/CLOSED_TP→WIN; LOST/LOSS/SL_HIT/CLOSED_SL→LOSS; importer enforces canonical going forward | runs after P1-7 |

### Wave 3 — Re-route + dedupe + retrain (P2)

| step | todo | notes |
|---|---|---|
| 12 | **P2-13** /audit EQUITY feed re-route to `challenge_200_trades` + `consensus_tracked` + `at_raw_picks` (NOT `at_consensus_picks`) | first sweep with #0d for cohort-pollution |
| 13 | **P2-14** FUTURES + ETF flagged "INSUFFICIENT DATA" | template change in `audit_dashboard/template.html` |
| 14 | **P2-15** FOREX dedupe by (strategy, symbol, entry_time, direction) | one-shot UPDATE; importer dedup-hash going forward |
| 15 | **P2-16** Retrain `meme_ml_models` on production cohort | use `bt_backtest_trades.MEMECOIN` n=123,648 closed; not the 50-row leakage fixture |
| 16 | **P2-17** Restart `lm_sports_ml_predictions` writer (cold since 2026-02-16) | depends on P0-5 finding (likely same root cause) |
| 17 | **P2-18** 3 composite indexes | `(asset_class,status)`, `(strategy,asset_class)`, `(source_db,source_table)` |

### Wave 4 — Backlog (P3)

P3-19 Parquet move, P3-20 partition, P3-21 archive, P3-22 dump-analyzer fix, P3-23 sportsbet ghost tables, P3-24 nightly snapshot table.

---

## QA gates (verification queries — pass/fail thresholds)

10 verification queries from claude+kilo consensus. Each gates a wave.

| # | purpose | SQL | pass threshold |
|---|---|---|---|
| Q-V1 | Wave-1 quarantine effect on CRYPTO WR | `SELECT 100*SUM(pnl_pct>0)/COUNT(*) AS wr_pct, ROUND(SUM(GREATEST(pnl_pct,0))/NULLIF(-SUM(LEAST(pnl_pct,0)),0),3) AS pf FROM bt_backtest_trades WHERE asset_class='CRYPTO' AND terminal_outcome IN ('WIN','LOSS') AND NOT (symbol='MATICUSDT' AND strategy IN ('quan_engine','quan_engine_scalp','quan_engine_swing','meta_strategy'))` | **CRYPTO PF > 0.7** (raw was 0.46). If still <0.42, more ghost cohorts exist beyond the 5 known. |
| Q-V2 | Forward-validator unfrozen | `SELECT MAX(imported_at) AS last_term_write, TIMESTAMPDIFF(HOUR, MAX(imported_at), NOW()) AS hours_ago FROM bt_backtest_trades WHERE terminal_outcome IN ('WIN','LOSS') AND status IN ('WON','LOST')` | **hours_ago < 26**. Pre-fix ~840h. |
| Q-V3 | FOREX dedupe success | `SELECT COUNT(*)-COUNT(DISTINCT CONCAT(strategy,'|',symbol,'|',entry_time,'|',direction)) AS dupes FROM bt_backtest_trades WHERE asset_class='FOREX' AND terminal_outcome IN ('WIN','LOSS')` | **dupes < 30**. Pre-fix ~228 (18.3% of 1,244). |
| Q-V4 | terminal_outcome integrity | `SELECT COUNT(*) AS mismatch FROM bt_backtest_trades WHERE (pnl_pct>0.0005 AND terminal_outcome!='WIN') OR (pnl_pct<-0.0005 AND terminal_outcome!='LOSS') OR (pnl_pct BETWEEN -0.0005 AND 0.0005 AND terminal_outcome NOT IN ('FLAT','OPEN'))` | **mismatch = 0** |
| Q-V5 | terminal_outcome index used | `EXPLAIN SELECT asset_class, AVG(CASE WHEN terminal_outcome='WIN' THEN 1.0 ELSE 0 END) AS wr FROM bt_backtest_trades WHERE asset_class='CRYPTO' AND terminal_outcome IN ('WIN','LOSS') GROUP BY asset_class` | EXPLAIN.key = `idx_bt_terminal_outcome` (NOT NULL); type = `ref` or `range` (NOT `ALL`); rows < 5M. |
| Q-V6 | Importer fix — confidence NULL drop | `SELECT AVG(CASE WHEN confidence IS NULL THEN 1.0 ELSE 0 END) AS null_ratio, COUNT(*) FROM bt_backtest_trades WHERE imported_at > DATE_SUB(NOW(), INTERVAL 7 DAY)` | **null_ratio < 0.05** (post-fix; pre-fix ~1.0). |
| Q-V7 | challenge_200_trades cohort still positive | `SELECT 100*SUM(pnl_pct>0)/COUNT(*), ROUND(SUM(GREATEST(pnl_pct,0))/NULLIF(-SUM(LEAST(pnl_pct,0)),0),3) FROM challenge_200_trades WHERE strategy_mode='ML'` | **WR > 0.50 AND PF > 1.2 AND n >= 600**. If WR drops <50%, phantom rows infiltrated this table too. |
| Q-V8 | Phantom-row count for EQUITY/FUTURES/ETF | `SELECT asset_class, SUM(status='EXPIRED' AND pnl_pct=0 AND exit_price=entry_price) AS phantom, COUNT(*) AS total FROM bt_backtest_trades WHERE asset_class IN ('EQUITY','FUTURES','ETF') GROUP BY asset_class` | phantom/total per class trends down week-over-week post deploy of P0-3. |
| Q-V9 | OPEN-population age sanity | `SELECT asset_class, COUNT(*) AS n_open, AVG(TIMESTAMPDIFF(DAY, entry_time, NOW())) AS avg_age_days FROM bt_backtest_trades WHERE status='OPEN' GROUP BY asset_class` | **avg_age_days < 7** (was 35 mid-freeze). |
| Q-V10 | meta_strategy template drop | `SELECT COUNT(*) AS meta_const_pnl FROM bt_backtest_trades WHERE strategy='meta_strategy' AND ROUND(pnl_pct,4) IN (5.0000,-3.0000)` | unchanged in DB (quarantine ≠ DELETE). Dashboard CRYPTO WR computed without these rows should rise from 0.32 → >0.40. |

---

## CI regression tests (5 — add to `tests/test_db_quarantine.py`)

```python
# tests/test_db_quarantine.py
import pytest
from audit_trail.mysql_client import _create_connection

def test_no_quan_engine_matic_constant_pnl_in_payload():
    """P0-1 quarantine — 215k constant-pnl rows must NOT appear in dashboard CRYPTO aggregate."""
    from audit_trail.dashboard_generator import _filter_picks
    rows = [{'symbol':'MATICUSDT','strategy':'quan_engine','direction':'LONG','pnl_pct':-15.0,'asset_class':'CRYPTO','status':'closed'}]
    assert _filter_picks(rows) == [], "quan_engine MATICUSDT LONG ghost not filtered"

def test_no_phantom_expired_in_payload():
    """P0-3 phantom-row drop — status=EXPIRED + pnl_pct=0 + exit_price=entry_price must drop."""
    from audit_trail.dashboard_generator import _filter_picks
    rows = [{'symbol':'AAPL','asset_class':'EQUITY','strategy':'foo','direction':'LONG','status':'EXPIRED','pnl_pct':0.0,'entry_price':100.0,'exit_price':100.0}]
    assert _filter_picks(rows) == []

def test_terminal_outcome_column_exists_and_populated():
    """P1-7 — generated column wired."""
    c = _create_connection(); cur = c.cursor()
    cur.execute("SELECT COUNT(*) FROM bt_backtest_trades WHERE pnl_pct IS NOT NULL AND terminal_outcome IS NULL")
    assert cur.fetchone()[0] == 0
    c.close()

def test_forex_dedupe_active():
    """P2-15 — duplicate (strategy,symbol,entry_time,direction) FOREX rows below threshold."""
    c = _create_connection(); cur = c.cursor()
    cur.execute("SELECT COUNT(*)-COUNT(DISTINCT CONCAT(strategy,'|',symbol,'|',entry_time,'|',direction)) FROM bt_backtest_trades WHERE asset_class='FOREX' AND terminal_outcome IN ('WIN','LOSS')")
    assert cur.fetchone()[0] < 30
    c.close()

def test_forward_validator_not_frozen():
    """P0-5 — last terminal-status write must be < 26h old."""
    c = _create_connection(); cur = c.cursor()
    cur.execute("SELECT TIMESTAMPDIFF(HOUR, MAX(imported_at), NOW()) FROM bt_backtest_trades WHERE status IN ('WON','LOST')")
    assert cur.fetchone()[0] < 26
    c.close()
```

---

## Monitoring alerts (8)

| frequency | metric | threshold | remediation |
|---|---|---|---|
| **Daily** | Ghost-row growth: `COUNT(*) WHERE strategy='quan_engine' AND symbol='MATICUSDT' AND pnl_pct=-15` | growth > 100/day → page | filter not active OR new ghost source spawned |
| **Daily** | Forward-validator freshness: `MAX(imported_at) WHERE status IN ('WON','LOST')` | hours_ago > 26 → page | re-run freeze runbook |
| **Daily** | New (strategy, symbol, direction, ROUND(pnl_pct,4)) cohort | any cohort n>1000 → warn | new ghost pattern detected |
| **Weekly** | NULL ratio for `confidence`, `raw_data`, `exit_reason` per asset_class | drift > 5pp WoW → warn | importer regression |
| **Weekly** | Cohort drift: 7d WR vs 28d WR per (strategy, asset_class) | abs(7d - 28d) > 10pp AND n_7d > 50 → warn | strategy decay |
| **Weekly** | Status enum drift: COUNT per status value | new value appears OR old value drops to 0 → warn | importer schema drift |
| **Monthly** | Dangling FK: `COUNT(*) FROM bt_backtest_trades t LEFT JOIN bt_backtest_runs r ON r.id=t.backtest_run_id WHERE t.backtest_run_id IS NOT NULL AND r.id IS NULL` | dangling > 1% → page | run import broken |
| **Monthly** | Total row growth: 28-day delta in `COUNT(*)` | growth > 200% (anomalous spike) → page | runaway importer or pollution |

Wire via `tools/sql_health_check.py` cron + `tools/swarm/comment_poster.ps1`-style alerting.

---

## 30/60/90-day revisits

| day | task | trigger condition |
|---|---|---|
| **30d** | Re-run Q14 cohort drift across all strategies | post-freeze fix; n_post ≥ 50 across 20+ strategies |
| **30d** | Validate `challenge_200_trades` ML-mode 57.1% WR holds on 30 fresh trades | post-routing change |
| **60d** | Re-train `meme_ml_models` on cleaned MEMECOIN cohort + run held-out test | post P2-16 |
| **60d** | Sports CLV trend check on NCAAB + NBA | post P2-17 |
| **90d** | Audit EQUITY/COMMODITY/BOND for new ghost cohorts (Wave 0 #0d generalized) | new asset classes start writing or strategy lineup changes |

---

## Blind-spot mitigations (added during this review)

1. **OPEN-population census** (`tools/audit_open_population.py`) — wave 0 step 0a. Without it, post-quarantine "clean" metrics are false positives.
2. **EQUITY/COMMODITY/BOND ghost sweep** (`tools/audit_bt_synthetic.py`) — wave 0 step 0d. Generalizes existing `audit_synthetic_patterns.py` to bt_backtest_trades 30M rows.
3. **PnL recompute integrity check** (Q-V11): `SUM(ABS(pnl_pct - (exit_price-entry_price)/entry_price*100) > 1) WHERE entry_price>0 AND exit_price>0` per asset_class. Threshold: <5% mismatch on computable rows. Currently 67-79% on `at_raw_picks` — verify same broken on `bt_backtest_trades`.

---

## Existing audit infra to leverage (per freebuff)

Use these instead of writing from scratch:
- `audit_trail/mysql_client.py::_create_connection()` — connection helper. Replace direct pymysql calls.
- `audit_synthetic_patterns.py` — synthetic-pattern detector. Currently targets `consensus_tracked` (318 rows). Extend to `bt_backtest_trades` 30M rows in step 0d.
- `audit_outliers.py`, `audit_suspicious.py`, `audit_comprehensive_report.py` — ready-made audit scripts.
- `audit-daily.py` — supports the 15GB SQL dump file (the original input to this analysis).
- `alpha_engine/audit_sync.py` — full MySQL sync pipeline. P1-10 importer fix lives here.
- `audit_dashboard/database_consolidation.py` — unified dashboard view.
- `.ruflo/agents/audit-quant.yaml` + `audit-researcher.yaml` — swarm review agents (NOTE: free-tier OpenRouter endpoints currently 404; need paid keys or model swap).

`AUDIT_BLUEPRINT.md` documents the existing pipeline. New work goes through it.

---

## Outstanding artifacts for this session

- `reports/db_action_todos_2026-05-07.md` (24 todos input)
- `reports/db_master_synthesis_2026-05-07.md` (live forensics input)
- `swarm_runs/db_action_3phase_20260508T140003Z/{deepseek,kilo,claude,gemini,xai}.{json,raw.txt}` (5-engine swarm)
- `swarm_runs/db_action_3phase_prompt.md` (3-phase prompt sent to swarm)
- `swarm_runs/ruflo-insights/` (failed; free-tier OpenRouter endpoints 404)
- `reports/db_action_plan_2026-05-08.md` (THIS FILE)

## Known issues with this run

- xai engine returned 0 bytes (358s elapsed; transport_status=ok but output empty). Not retried.
- gemini hallucinated scope numbers; trust direction of finding only.
- claude/deepseek/kilo all hit JSON output truncation (~14-37KB raw); structural data extracted via regex, not full JSON parse.
- ruflo (free tier) failed: `deepseek/deepseek-chat:free` and `google/gemini-2.0-flash-exp:free` return 404 from OpenRouter. Need paid keys.
- New `/swarmwithprework` skill (4-phase: prework → brainstorm → action plan → QA critic) is the right tool for next iteration; this run pre-dated its discovery.
