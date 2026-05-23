# Action Plan Delta — Peer-Audit Reconciliation 2026-05-08

Inputs:
- `reports/db_action_plan_2026-05-08.md` (24-todo plan)
- Peer audit summary (322 tables, claimed ~2.26M rows / 1.31M for bt_backtest_trades)
- `reports/peer_audit_factcheck_2026-05-08.md` (5 findings verified)
- `reports/peer_audit_factcheck_part2_2026-05-08.md` (5 more findings verified)

---

## Reconciliation: peer audit got 2 things wrong

| peer claim | actual | gap |
|---|---|---|
| `bt_backtest_trades` = 1.31M rows | **29,845,129 (29.85M)** | peer used `information_schema.TABLES.TABLE_ROWS` — InnoDB approximation, **22.7× under-counted** |
| Engine: MariaDB | **MySQL 8.4.7** | mislabeled |
| DB total ~2.26M rows | actual ≈30M+ | sum of TABLE_ROWS is also wrong; do not cite |
| 322 tables | **322 confirmed** | match |

Use `COUNT(*)` per-table, never `information_schema.TABLES.TABLE_ROWS`, when sizing the DB. Add this to `tools/audit_open_population.py` Wave 0 step 0a as a guard.

---

## NEW critical findings (verified) — promote to P0/P1

### NEW-P0-7: `at_consensus_picks` time-travel resolver bug

**5,268 of 9,188 rows (57.3%)** have `closed_at < generated_at`. Average 35.66h ahead, max 149h. Pattern: resolver retro-stamps `closed_at` to the historical price-bar that triggered TP/SL, while `generated_at` is the cron-write time. **Same class as `feedback_noncrypto_resolver_live_close_bug.md` but on the supposedly-clean crypto path.** Breaks every daily/weekly WR aggregation.

Mitigation:
```sql
ALTER TABLE at_consensus_picks ADD COLUMN time_travel_flag BOOL GENERATED ALWAYS AS (closed_at < generated_at) STORED, ADD INDEX idx_acp_time_travel (time_travel_flag);
```
Then `dashboard_generator.py` filter: `WHERE time_travel_flag = FALSE` until resolver fixed.

**Explains the `at_consensus_picks EQUITY 2.2% WR (n=403)` finding from P0-4.** EQUITY consensus picks are likely 100% time-travel-corrupted.

### NEW-P0-8: `lm_signals` expire-without-resolve cron broken

**32,019 of 33,289 expired rows (96.2%) have exit_price=0** + pnl_pct=0. Time-expire cron stamps status without invoking the resolver. Live monitor's WR on this table is meaningless.

Same pattern in `trading_picks`:
- TIME_EXIT exits: 100% have exit_price NULL
- SL_HIT exits: 96.5% have exit_price NULL
- TP_HIT exits: 96.0% have exit_price NULL

Resolver computes pnl from SL/TP target but never writes back the actual exit price. Bigger than the original P0-3 phantom-row drop — that was 9,600 rows; this is 64K+.

### NEW-P0-9: 35-day freeze companion — `algorithm_rolling_perf` cron dead 11 days

Last write 2026-04-27 (11 days stale). Companion to the P0-5 forward-validator freeze (35 days stale on WON/LOST writes). Two cron jobs broken in the same window — likely the 2026-04-02 deploy that broke the resolver chain also took out rolling-perf writer.

Real resolver gap: 85 rows where `total_picks>0 AND resolved_picks=0`. Not the 3,536 peer claimed (that was just empty-algo rows).

### NEW-P0-10: `at_discord_notifications.signal_tier` 99.99% NULL

40,174 of 40,179 rows NULL on `signal_tier`. Only 3 STRONG + 2 MODERATE survive across 40K notifications. Direction empty on 21,326. source_systems NULL on 21,587. strategy NULL/empty on 24,769.

Two bugs:
- A: `signal_tier` writer never populated even on PICK_POSTED rows (writer-side bug)
- B: Heartbeat events (FORWARD_TEST_UPDATE, COMBO_FINDINGS) pollute pick analytics — should be filtered by `event_type` before tier rollup

Dashboard's "STRONG TAKE" / "MODERATE TAKE" tiers are essentially empty. The 13-PR autonomous round results from `CLAUDE.md` ("NBA STRONG TAKE +164% / NHL STRONG TAKE −100%") were computed off the 5 surviving rows.

### NEW-P1-13: `trading_picks` direction vocab dual-writer

Direction values: LONG 28,239 + SHORT 30,592 + **BUY 3,290 + SELL 1,364** + 449 empty. Two writer paths into one table. 2,668 rows have empty/null `strategy`.

Migration:
```sql
UPDATE trading_picks SET direction='LONG' WHERE direction='BUY';
UPDATE trading_picks SET direction='SHORT' WHERE direction='SELL';
```
Then add CHECK constraint `direction IN ('LONG','SHORT')` on writer side. Find both writers via `grep -r "INSERT INTO.*trading_picks"` and unify.

### NEW-P1-14: `asset_class=''` empty enum (sql_mode non-strict)

`at_raw_picks` 2,490 rows; `at_audit_events` 490; `at_consensus_picks` 279. Both `''` and `UNKNOWN` coexist (at_audit_events is 68.6% UNKNOWN). Root cause: non-strict sql_mode + writers passing unmapped values. Python `None` casting to `""` instead of `UNKNOWN`.

```sql
SET GLOBAL sql_mode='STRICT_ALL_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE';
UPDATE at_raw_picks SET asset_class='UNKNOWN' WHERE asset_class='';
UPDATE at_audit_events SET asset_class='UNKNOWN' WHERE asset_class='';
UPDATE at_consensus_picks SET asset_class='UNKNOWN' WHERE asset_class='';
```
Add CHECK constraint or strict-mode at session level on writer.

### NEW-P1-15: `simulation_grid` 100% LONG (6,000/6,000 rows, 0 SHORT)

Parameter grid for backtests has no SHORT coverage. Every conclusion drawn from this grid is LONG-only-conditional. Re-run grid w/ direction=SHORT for full coverage. Note: confirms `feedback_long_source_bias.md` at the simulation level.

### NEW-P2-19: `rapid_signals` constant-pnl ghost (5,237 rows)

Peer's "50/50 statistically improbable" is WRONG (95% CI for n=35,328 fits). Real bug: 5,237 rows (14.8%) are **labeled win/loss with pnl_pct=0** — same class as the EXPIRED phantom rows. Plus 100% `long` signal_type.

Fix: drop pnl=0 rows from win/loss aggregations or re-resolve them.

### NEW-P3-25: 102 empty tables, 73 abandoned

Confirmed exact count + 10/10 spot-checks empty. Categories:
- 73 abandoned: `KIMI_GOLDMINE_*`, `lm_bridge_*`, `goldmine_cursor_*`, `cp_*`, `cr_*`, `fxp_*`, `mf_*`, `portfolio_*`, `sp_*`, `strategy_lifecycle_*`
- 9 rotation-targets: `crypto_*`, `stock_*` (intended to be rotated, but empty now)
- 3 lazy-init: `at_discord_gate_state`, etc.

`DROP TABLE` script in `tools/cleanup_empty_tables.py` after manual review.

---

## DISPUTED peer claims

### `consensus_tracked` 100% synthetic — DISPUTED

Peer claimed all 318 rows are future-dated, round-priced, 0% returns. Actual:
- 0/318 future-dated
- Only 6 with round entry_price (1.9%)
- 83 zero-return rows are explicable: 44 `closed_neutral` + 39 still open

Looks like real equity backtest data. **Do NOT purge `consensus_tracked`** as peer recommended. Existing `audit_synthetic_patterns.py` baseline run reported "HIGHLY SYNTHETIC" but that was driven by 50/95 flags = whole-dollar prices on equity tickers, which is normal for stock backtests at SLB/NVDA/MSFT levels.

### `rapid_signals` 50/50 split improbable — DISPUTED

n=35,328, 17,710W / 17,618L = 50.13% win. 95% CI fits 49.48-50.52%. Statistically NORMAL. The 14.8% pnl=0 mislabel is the actual bug (NEW-P2-19).

---

## Updated execution waves (delta)

### Wave 1 — P0 (UPDATED)

| step | todo | rationale |
|---|---|---|
| 1 | **P0-5** Forward-validator freeze (existing) | 35d freeze on WON/LOST |
| 1b | **NEW-P0-9** algorithm_rolling_perf cron — 11d freeze | likely same root cause; investigate together |
| 2 | **P0-1+P0-2** Quarantine ghost rows (existing) | 217k MATIC + 1.6M meta_strategy |
| 3 | **P0-3** Phantom EXPIRED rows drop (existing) | 9,600 rows |
| 3b | **NEW-P0-8** lm_signals expire-without-resolve fix | **64K rows — bigger than P0-3** |
| 4 | **P0-4** at_consensus_picks EQUITY 2.2% WR investigation | now explained by NEW-P0-7 |
| 4b | **NEW-P0-7** at_consensus_picks time-travel filter | 5,268 rows / 57% of table |
| 5 | **P0-6** quan_engine writer hunt | constant -15% bug |
| 5b | **NEW-P0-10** at_discord_notifications signal_tier writer fix | 99.99% NULL — STRONG TAKE pipeline broken |

### Wave 2 — P1 (UPDATED)

| step | todo |
|---|---|
| 6-11 | existing P1-7 to P1-12 |
| 12 | **NEW-P1-13** trading_picks direction vocab unify (BUY→LONG, SELL→SHORT) |
| 13 | **NEW-P1-14** asset_class='' → UNKNOWN backfill + sql_mode strict |
| 14 | **NEW-P1-15** simulation_grid SHORT coverage rerun |

### Wave 3 — P2 (UPDATED)

| step | todo |
|---|---|
| 15-20 | existing P2-13 to P2-18 |
| 21 | **NEW-P2-19** rapid_signals pnl=0 mislabel scrubber |

### Wave 4 — P3 (UPDATED)

| step | todo |
|---|---|
| 22-26 | existing P3-19 to P3-24 |
| 27 | **NEW-P3-25** drop 73 abandoned tables (after review) |

---

## QA gates — added (Q-V11 to Q-V14)

| # | purpose | SQL | pass threshold |
|---|---|---|---|
| Q-V11 | Time-travel filter active | `SELECT COUNT(*) FROM at_consensus_picks WHERE closed_at < generated_at AND time_travel_flag=FALSE` | **0** rows |
| Q-V12 | lm_signals resolver fix | `SELECT 100*SUM(exit_price=0)/COUNT(*) AS zero_pct FROM lm_signals WHERE status='expired'` | **<5%** (was 96.2%) |
| Q-V13 | signal_tier writer wired | `SELECT 100*SUM(signal_tier IS NULL)/COUNT(*) AS null_pct FROM at_discord_notifications WHERE event_type='PICK_POSTED'` | **<5%** (was 99.99%) |
| Q-V14 | trading_picks direction unified | `SELECT direction, COUNT(*) FROM trading_picks GROUP BY direction` | **only LONG/SHORT, no BUY/SELL/empty** |

---

## CI tests — added (in `tests/test_db_quarantine.py`)

```python
def test_no_time_travel_in_consensus_picks_filter():
    """NEW-P0-7 — dashboard payload must exclude time-travel rows."""
    from audit_trail.dashboard_generator import _filter_picks
    rows = [{
        'symbol': 'BTCUSDT', 'asset_class':'CRYPTO',
        'generated_at':'2026-05-07 13:18:24',
        'closed_at':'2026-05-06 09:20:20',
        'pnl_pct': 1.2, 'status':'closed_win',
    }]
    assert _filter_picks(rows) == []

def test_lm_signals_resolver_writes_exit_price():
    """NEW-P0-8 — expired lm_signals must have exit_price > 0."""
    from audit_trail.mysql_client import _create_connection
    c = _create_connection(); cur = c.cursor()
    cur.execute("SELECT 100*SUM(exit_price=0)/COUNT(*) FROM lm_signals WHERE status='expired'")
    assert cur.fetchone()[0] < 5
    c.close()

def test_trading_picks_direction_canonical():
    """NEW-P1-13 — only LONG/SHORT allowed."""
    from audit_trail.mysql_client import _create_connection
    c = _create_connection(); cur = c.cursor()
    cur.execute("SELECT COUNT(*) FROM trading_picks WHERE direction NOT IN ('LONG','SHORT')")
    assert cur.fetchone()[0] == 0
    c.close()

def test_signal_tier_populated():
    """NEW-P0-10 — signal_tier must be non-NULL on PICK_POSTED rows."""
    from audit_trail.mysql_client import _create_connection
    c = _create_connection(); cur = c.cursor()
    cur.execute("SELECT 100*SUM(signal_tier IS NULL)/COUNT(*) FROM at_discord_notifications WHERE event_type='PICK_POSTED' AND created_at > NOW() - INTERVAL 7 DAY")
    assert cur.fetchone()[0] < 5
    c.close()
```

---

## Monitoring alerts — added

| frequency | metric | threshold | remediation |
|---|---|---|---|
| Daily | `at_consensus_picks` time-travel growth | new rows > 50/day with closed_at < generated_at → page | resolver still retro-stamping |
| Daily | `lm_signals` expire-without-resolve growth | new expired rows with exit_price=0 > 100/day → page | cron not invoking resolver |
| Daily | `algorithm_rolling_perf` write age | last_updated > 26h → page | cron dead |
| Weekly | `at_discord_notifications` signal_tier NULL ratio | NULL ratio > 10% → warn | writer regressed |
| Weekly | `trading_picks` direction vocab drift | any non-LONG/SHORT value detected → warn | new writer added old vocab |
| Weekly | `at_*` empty-string asset_class growth | new rows w/ asset_class='' > 50/day → warn | sql_mode lapsed |

---

## Updated highest risk + blind spots

### Highest risk (revised)

The 35-day forward-validator freeze (P0-5) is **NOT alone**. Three resolver/cron pipelines are broken simultaneously since 2026-04-02:

1. Forward-validator (35d stale on WON/LOST writes)
2. `algorithm_rolling_perf` writer (11d stale)
3. `at_consensus_picks` resolver (active but writes time-travel timestamps)
4. `lm_signals` time-expire cron (active but skips resolver, writes exit_price=0)
5. `at_discord_notifications` signal_tier writer (99.99% NULL — likely never worked properly, not a freeze)

**Root cause is probably one shared module/deploy** in the resolver chain. Investigate together via `git log --since="2026-04-01" -- alpha_engine/ audit_trail/ outcome_resolver.py` plus `gh run list` for the same window.

### Blind spot (revised)

We have NOT yet swept:
- Memecoin tables (`meme_*`) — 5 tables, 150 rows total, claimed broken
- Mutual-fund tables (`mf_*`, `mf2_*`) — 33 tables, 13.8K rows, schema migration incomplete
- Goldmine (`gm_*`) — 6 tables, 5.5K rows, SEC 13F holdings (not in current /audit scope)
- Penny-stock (`penny_*`) — 1.1K rows, 40+ scoring columns

These are not in the 24-todo plan. Either flag as out-of-scope (sportsbet & fundamentals are Goal #2/#3, not Goal #1) or add Wave-0 reconnaissance for each before promoting any to /audit.

---

## Output to next iteration

1. Run `/swarmwithprework` (the new 4-phase skill) on this delta + the 30-todo combined list. It does pre-work → multi-family brainstorm → action plan → QA critic in one orchestrated chain.
2. Add monitoring alerts (NEW table: `db_health_heartbeat`) — automate the NULL-ratio + freshness checks.
3. Wire `audit_synthetic_patterns.py` extension (`tools/audit_bt_synthetic.py`) to scan `bt_backtest_trades` 30M rows weekly for new ghost cohorts.
