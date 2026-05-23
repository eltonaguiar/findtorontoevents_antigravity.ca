# Signal Investigation Report — March 8, 2026

> **Investigator**: Antigravity AI  
> **Date**: March 8, 2026 @ 7:30 PM EST  
> **Scope**: KIMI signal closure, Mercury2 scanner health, unrealized PNL tracking, database consolidation

---

## Executive Summary

| System | Status | Open Signals | Win Rate | Key Issue |
|--------|--------|-------------|----------|-----------|
| **KIMI RiseOfTheClaw** | 🔴 DEAD | 94 zombie picks | 23.1% | Scanner stopped March 1 |
| **Mercury2** | 🟡 DEGRADED | 2 active | 0.0% (46 losses) | Model validation failed |
| **Alpha Engine** | 🟡 ACTIVE | 30 active | 47.6% (W/L) | 1 pick has no TP/SL |
| **Paper Trading** | 🟢 RUNNING | 44 active | 41.2% | Best performer |

**Total SQLite databases in project: 27** — all should be deprecated in favor of MySQL `ejaguiar1_stocks`.

---

## 1. KIMI Signal Closure — Root Cause Analysis

### The Problem

KIMI RiseOfTheClaw has **94 open picks** stuck in its SQLite database (`KIMI_RISEOFTHECLAW/data/kimi_trading.db`). The scanner **stopped running on March 1, 2026** — 7 days ago — so no TP/SL checks or time-based exits are being processed.

### Database State

```
SQLite: KIMI_RISEOFTHECLAW/data/kimi_trading.db
├── signals:  379,995 total (massive signal generation volume)
├── picks:    133 total
│   ├── OPEN:  94  (70.7%)
│   ├── LOSS:  30  (22.6%)
│   └── WIN:    9  ( 6.8%)
└── Win rate on closed: 23.1% (9 / 39)
```

### Age Analysis — All Picks Are Stale

| Entry Date | Count | Days Stale | Exceeds Max Hold? |
|-----------|-------|-----------|-------------------|
| Feb 19 | 13 | **17 days** | ✅ Crypto 5d, Stock 7d |
| Feb 20 | 5 | 16 days | ✅ |
| Feb 21 | 2 | 15 days | ✅ |
| Feb 23-25 | 12 | 11-13 days | ✅ |
| Feb 26-27 | 30 | 9-10 days | ✅ |
| Feb 28-Mar 1 | 12 | 7-8 days | ✅ |
| **TOTAL** | **94** | All exceed max hold | All should be forced closed |

### Why They Won't Close

1. **Scanner is the only exit mechanism** — `live_scanner.py` checks TP/SL/time at runtime. No scan = no closure.
2. **GitHub Actions workflows** (`deploy-riseoftheclaw.yml`, `backtest-and-deploy.yml`) stopped executing after March 1.
3. **Max hold periods** (crypto: 5d, stock: 7d, forex: 7d) are enforced *only* during scanner execution.
4. **No cron watchdog** — there's no independent process that force-closes stale picks.

### Top Open Picks by Algorithm

```
call-surge-scout:          7 open
options-flow-scout:        5 open
cci-crypto-reversal:       5 open
sector-rotation:           4 open
rs-breakout-scout:         4 open
crypto-bb-squeeze-scout:   4 open
bollinger-squeeze:         4 open
quality-minus-junk:        3 open
momentum-factor:           3 open
```

### Top Symbol Concentration

```
AAPL:     6 open picks (over-concentrated)
QQQ:      4 open
MSFT:     4 open
LINK-USD: 4 open
ADA-USD:  4 open
```

### Signal Volume Concern

- **379,995 total signals** → **133 picks opened** = 0.035% conversion rate
- This indicates extremely loose signal generation with aggressive filtering at the pick stage
- The signal table is bloated and adds no analytical value at this scale

---

## 2. Mercury2 Scanner — Running But Broken

### Current Status

Mercury2 IS running (last scan: `2026-03-08T22:15:05 UTC`, ~1 hour ago at time of investigation) via GitHub Actions on a 30-minute cron schedule. However, it's operating in **degraded mode**.

### Validation Failure

```json
{
  "passed": false,
  "dsr_pvalue": 0.000,
  "psr_pvalue": 0.000,
  "sharpe": -4.4829,
  "model": "mercury2_ensemble",
  "reason": "FAILED: DSR=0.000 (need >=0.6), PSR=0.000 (need >=0.6)"
}
```

| Metric | Value | Threshold | Status |
|--------|-------|----------|--------|
| **Sharpe Ratio** | -4.48 | > 0 | 🔴 Guaranteed loser |
| **DSR p-value** | 0.000 | ≥ 0.6 | 🔴 No statistical edge |
| **PSR p-value** | 0.000 | ≥ 0.6 | 🔴 No skill above luck |
| **Observations** | 69,987 | — | Sufficient sample |

### Mercury2 Performance

```
Active picks:  2  (NEARUSDT +3.86%, RENDERUSDT +1.98%)
Closed picks:  46 (0 wins, 46 losses → 0% win rate)
Total PNL:     +3.1% (accumulated from partial TP hits before final SL)
Fear & Greed:  12 (extreme fear)
BTC Dominance: 56.29%
```

### GitHub Actions Workflows (Mercury2)

| Workflow | Schedule | Status |
|----------|---------|--------|
| `mercury2-scan.yml` | Every 30 min (:05, :35) | ✅ Running |
| `mercury2-fast-scan.yml` | Every 4 hours | ✅ Running |
| `mercury2-retrain.yml` | Manual trigger | Available |

### Mercury2 Data Files

```
mercury2/data/
├── active_picks.json     (2 picks, 2.9KB)
├── closed_picks.json     (46 picks)
├── scan_summary.json     (last scan metadata)
└── validation_report.json (DSR/PSR failure)
```

---

## 3. Unrealized PNL — Open Position Performance

### Alpha Engine (30 open positions)

| Metric | Value |
|--------|-------|
| Total unrealized PNL | **+1.1386%** |
| Average per position | +0.038% |
| Winners (unrealized) | 18 (60%) |
| Losers (unrealized) | 12 (40%) |
| Best open | +0.1258% (NEAR-USD) |
| Worst open | -0.0797% (ETH-USD) |

**Unrealized vs Realized Performance Gap:**

| Metric | Unrealized (Open) | Realized (Closed) |
|--------|-------------------|-------------------|
| Net PNL | **+1.14%** | **-4.24%** |
| Win rate | 60% | 47.6% (W/L only) |
| Positions | 30 | 186 |

This gap suggests positions tend to deteriorate before exit — the system enters OK but exits badly. Most closed picks (165/186) exit via TIME_EXIT, not TP/SL, meaning:
- TP levels are set too wide (never reached)
- SL levels may be too tight (triggered by noise) 
- Time exits close before moves materialize

### Zombie Pick Alert

**1 position has no TP and no SL set:**
- `put_call_ratio_contrarian` on BTC-USD
- Entry: 2026-02-28 (8 days old)
- Unrealized PNL: -0.80%
- **Will never auto-close via price** — only TIME_EXIT can close it

### Paper Trading (44 active positions)

| Status | Count |
|--------|-------|
| ACTIVE | 44 |
| TP_HIT | 21 |
| SL_HIT | 30 |
| **Win Rate** | **41.2%** |

Paper Trading is the **best-performing system** by win rate. It uses MAX_HOLD_DAYS = 7, TRANSACTION_COST = 0.7%, and runs hourly via GitHub Actions.

---

## 4. Database Consolidation — SQLite → MySQL

### Current State: 27 SQLite Databases

The project currently has **27 separate SQLite databases** scattered across subsystems:

| Database | System | Records | Status |
|----------|--------|---------|--------|
| `KIMI_RISEOFTHECLAW/data/kimi_trading.db` | KIMI Claw | 380K signals, 133 picks | ⚠️ 94 zombie picks |
| `KIMI_FEB172026/data/kimi_trading.db` | KIMI Feb17 | empty | Legacy |
| `KIMI_RISEOFTHECLAW/data/signal_tracker.db` | Signal Tracker | unknown | Legacy |
| `paper_trading/data/paper.db` | Paper Trading | 95 positions | Active |
| `data/audit_trail.db` | Central Audit | varies | Being replaced |
| `audit_trail/data/audit_trail.db` | Audit Trail (local) | varies | Being replaced |
| `forward_testing/forward_signals.db` | Forward Testing | varies | Active |
| `data/dna_master_picks.db` | DNA Master | varies | Active |
| `data/live_picks.db` | Live Picks | varies | Active |
| `coinglass_strategies/data/coinglass.db` | Coinglass | varies | Active |
| `predictions/data/predictions.db` | Predictions | varies | Active |
| `signal_recorder/data/signal_log.db` | Signal Recorder | varies | Active |
| `trading/data/positions.db` | Trading | varies | Active |
| `trading/data/atm_challenge.db` | ATM Challenge | varies | Active |
| `sandbox/data/opposite_day.db` | Sandbox | varies | Experimental |
| `battleground/data/bundle_babies.db` | Battleground | varies | Experimental |
| `battleground/data/dna_factory.db` | DNA Factory | varies | Experimental |
| `incubator/backtest_team/bundle_babies.db` | Incubator | varies | Experimental |
| `incubator/forward_test.db` | Incubator FT | varies | Experimental |
| `meta_strategy/data/meta_strategy.db` | Meta Strategy | varies | Experimental |
| `quan_engine/data/quan_engine.db` | Quan Engine | varies | Experimental |
| `quant_lab/genome_results/genome.db` | Quant Lab | varies | Experimental |
| `quant_lab/permutation_results.db` | Quant Lab Perms | varies | Experimental |
| `genome/strategy_registry.db` | Genome Registry | varies | Active |
| `ab_testing_agent/ab_testing.db` | A/B Testing | varies | Experimental |
| `ab_testing_agent/crypto_data.db` | A/B Crypto Data | varies | Experimental |
| `crypto_data.db` | Root Crypto Data | varies | Legacy |

### Target: MySQL `ejaguiar1_stocks` as Master

The MySQL audit trail is **already partially implemented** and should be the single source of truth:

**Existing MySQL Schema** (in `audit_trail/mysql_schema.sql`):

```
at_aggregation_runs     — Run metadata (start/finish, counts)
at_raw_picks            — All raw signals from every system
at_consensus_picks      — Filtered consensus picks
at_audit_events         — Chronological event log
at_filter_log           — Why picks were filtered out
at_strategy_stats       — Materialized strategy performance
at_discord_sent         — Discord notification tracking
at_discord_gate_state   — Gate decisions for Discord
at_signal_outcomes      — Paper trading sync target
at_sqlite_imports       — Import tracking (dedup)
bt_backtest_runs        — Backtest run metadata
bt_backtest_trades      — Individual backtest trades
```

**What's Already Wired to MySQL:**

| System | MySQL Integration | Method |
|--------|-------------------|--------|
| Paper Trading | ✅ Syncs to `at_signal_outcomes` | `mysql_sync.py` on every run |
| Alpha Engine | ✅ Pushes to audit trail | `audit_push.py` on every run |
| Mercury2 | ✅ Pushes to audit trail | `mercury2/audit_push.py` on every run |
| KIMI RiseOfTheClaw | ❌ **Not connected** | Only local SQLite |
| Forward Testing | ❌ Not connected | Local SQLite only |
| Signal Recorder | ❌ Not connected | Local SQLite only |
| Audit Trail Recorder | ✅ Dual-writes SQLite + MySQL | `recorder.py` + `mysql_client.py` |

**Dual-Write Architecture** (current in `audit_trail/recorder.py`):
```
Every audit trail write → SQLite (local, always works)
                       → MySQL (remote, fire-and-forget with retry)
```

### Migration Plan: Deprecation of SQLite

#### Phase 1: Immediate (This Week)
- [ ] **Force-close KIMI's 94 zombie picks** at current market prices
- [ ] **Wire KIMI RiseOfTheClaw** to push picks to MySQL audit trail
- [ ] **Add `at_signal_outcomes` sync** to KIMI scanner (same pattern as `paper_trading/mysql_sync.py`)
- [ ] **Mark all SQLite `.db` files** as FYI/legacy with a `README.md` in each data directory

#### Phase 2: Short-Term (Next Sprint)
- [ ] **Deprecate `data/audit_trail.db`** — MySQL is master, SQLite is fallback only
- [ ] **Add MySQL sync to remaining active systems**: Forward Testing, Signal Recorder, DNA Master
- [ ] **Build a single query layer** that reads from MySQL only (no more scatter-reading 27 SQLite files)
- [ ] **Add unrealized PNL tracking to MySQL** — new `at_unrealized_snapshots` table with periodic snapshots

#### Phase 3: Long-Term (Cleanup)
- [ ] **Remove SQLite fallback** from audit trail recorder (MySQL-only writes)
- [ ] **Archive experimental databases** (battleground, sandbox, quant_lab, etc.) to a backup
- [ ] **Add `.gitignore` rules** for all `*.db` files (they shouldn't be in git)
- [ ] **Build dashboard views** that query MySQL directly instead of JSON files

### Proposed MySQL Table for Unrealized PNL

```sql
CREATE TABLE IF NOT EXISTS at_unrealized_snapshots (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    snapshot_time   DATETIME NOT NULL,
    system          VARCHAR(50) NOT NULL COMMENT 'alpha_engine | mercury2 | paper_trading | kimi',
    symbol          VARCHAR(50) NOT NULL,
    direction       ENUM('LONG','SHORT') NOT NULL,
    strategy        VARCHAR(200),
    entry_price     DECIMAL(18,8),
    current_price   DECIMAL(18,8),
    unrealized_pnl  DECIMAL(10,4) COMMENT 'percentage',
    hold_days       INT,
    peak_price      DECIMAL(18,8),
    trailing_active TINYINT(1) DEFAULT 0,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_us_time    (snapshot_time),
    INDEX idx_us_system  (system),
    INDEX idx_us_symbol  (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## 5. Action Items — Priority Order

### 🔴 Critical (Do Now)

1. **Force-close KIMI's 94 stale picks** — Write a script to close all OPEN picks at current market prices with reason `EXPIRED_STALE` and push outcomes to MySQL
2. **Fix KIMI scanner workflows** — Check GitHub Actions run history for `deploy-riseoftheclaw.yml` and `backtest-and-deploy.yml` to determine why they stopped
3. **Retrain Mercury2 model** — Trigger `mercury2-retrain.yml` (Sharpe of -4.48 means the model is inverted)

### 🟡 Important (This Week)

4. **Fix Alpha Engine zombie pick** — Add TP/SL to `put_call_ratio_contrarian` on BTC-USD or force-close it
5. **Wire KIMI to MySQL audit trail** — Add `audit_push.py` to KIMI scanner matching the Alpha Engine pattern
6. **Build unrealized PNL tracking** — Snapshot open positions to MySQL every scan cycle for historical tracking
7. **Test Mercury2 inverse signals** — With 0% WR on 46 trades, the counter-signal is statistically likely to be profitable

### 🟢 Maintenance (Next Sprint)

8. **Deprecate SQLite databases** — Add README.md markers to all `data/` directories noting MySQL is master
9. **Build single MySQL query layer** — Replace scatter-reading of 27 SQLite files
10. **Consider promoting Paper Trading strategies** — 41.2% WR is the best-performing system

---

## Appendix: File Reference

| File | Purpose |
|------|---------|
| `KIMI_RISEOFTHECLAW/live_scanner.py` | KIMI scanner entry point (9,405 lines) |
| `KIMI_RISEOFTHECLAW/data/kimi_trading.db` | KIMI SQLite database |
| `mercury2/scanner.py` | Mercury2 scanner entry point |
| `mercury2/data/scan_summary.json` | Mercury2 last scan metadata |
| `mercury2/data/validation_report.json` | Mercury2 DSR/PSR validation |
| `alpha_engine/scanner.py` | Alpha Engine scanner (1,589 lines) |
| `alpha_engine/data/active_picks.json` | Alpha Engine open positions |
| `alpha_engine/data/closed_picks.json` | Alpha Engine closed trades |
| `alpha_engine/audit_push.py` | Alpha → MySQL audit sync |
| `paper_trading/scanner.py` | Paper Trading entry point |
| `paper_trading/portfolio_manager.py` | Portfolio management + TP/SL/expiry |
| `paper_trading/mysql_sync.py` | Paper Trading → MySQL sync |
| `audit_trail/mysql_schema.sql` | Master MySQL schema (12 tables) |
| `audit_trail/mysql_client.py` | MySQL client with connection pooling |
| `audit_trail/recorder.py` | Dual-write recorder (SQLite + MySQL) |
| `.github/workflows/mercury2-scan.yml` | Mercury2 GHA (30 min schedule) |
| `.github/workflows/paper-trading.yml` | Paper Trading GHA (hourly) |
| `.github/workflows/alpha-engine-live.yml` | Alpha Engine GHA (15 min) |
