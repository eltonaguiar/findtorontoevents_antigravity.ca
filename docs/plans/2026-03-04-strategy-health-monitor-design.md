# Strategy Health Monitor — Design Document

**Date:** 2026-03-04
**Status:** Approved
**Approach:** A — "Strategy Health Monitor" (GitHub Actions cron, 4-hourly)

## Problem

Our trading systems generate 100+ strategies across KIMI, Alpha Engine, CW_WINNERS, and others. But there's no automated way to:
1. Know which strategies are actually profitable after fees
2. Kill strategies that are bleeding money (opposite_day ran at 2.2% WR for days)
3. Prevent 5 strategies all saying "BTC LONG" from looking like 5 independent bets
4. Validate strategies before promoting them to production

## Solution

A **Strategy Health Monitor** — a new workflow running every 4 hours that computes expectancy, manages strategy tiers (CORE/INCUBATOR/BANNED), deduplicates consensus picks, and gates promotions with walk-forward validation.

---

## Component 1: Expectancy Dashboard (`strategy_health/monitor.py`)

### Data Sources
- MySQL `at_signal_outcomes` (277 closed trades across kimi_riseoftheclaw, kimi_signal_tracker, opposite_day)
- MySQL `cw_winners` (153 resolved trades)
- Future: any new source that writes to `at_signal_outcomes`

### Per-Strategy Metrics
| Metric | Formula | Notes |
|--------|---------|-------|
| `expectancy` | `(win_rate * avg_win) - (loss_rate * avg_loss)` | Raw edge per trade |
| `fees_adj_expectancy` | `expectancy - (FEE_RATE * 100)` | FEE_RATE = 0.0015 (configurable) |
| `profit_factor` | `sum(wins) / abs(sum(losses))` | Guard div-by-zero: NULL if no losses |
| `rolling_30d_wr` | Win rate over last 30 calendar days | `closed_at >= NOW() - INTERVAL 30 DAY` |
| `trade_count` | Total resolved trades | Minimum 10 to evaluate |

### Implementation Rules
- **Parameterized queries only** — `cursor.execute(sql, params)`, never string interpolation
- **Round to 4dp** before INSERT (matches MySQL `DECIMAL(10,4)`)
- **Idempotent upserts** — `INSERT ... ON DUPLICATE KEY UPDATE` with conditional `tier_changed_at`:
  ```sql
  tier_changed_at = IF(tier <> VALUES(tier), NOW(), tier_changed_at)
  ```
- **FEE_RATE** stored as configurable constant, loaded from env var `STRATEGY_FEE_RATE` with default 0.0015

### MySQL Schema: `strategy_health`

```sql
CREATE TABLE IF NOT EXISTS strategy_health (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    source_system     VARCHAR(100) NOT NULL,
    strategy          VARCHAR(200) NOT NULL,
    asset_class       VARCHAR(20),
    total_trades      INT,
    wins              INT,
    losses            INT,
    win_rate          DECIMAL(5,4),
    avg_win_pct       DECIMAL(10,4),
    avg_loss_pct      DECIMAL(10,4),
    expectancy        DECIMAL(10,4),
    fees_adj_expect   DECIMAL(10,4),
    profit_factor     DECIMAL(10,4),
    rolling_30d_wr    DECIMAL(5,4),
    tier              ENUM('CORE','INCUBATOR','BANNED') DEFAULT 'INCUBATOR',
    tier_changed_at   DATETIME,
    tier_reason       TEXT,
    wf_passed         BOOLEAN DEFAULT NULL COMMENT 'walk-forward validation result',
    wf_last_checked   DATETIME,
    last_evaluated    DATETIME,
    UNIQUE KEY uk_health (source_system, strategy),
    INDEX idx_sh_tier (tier)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### MySQL Schema: `strategy_health_audit`

```sql
CREATE TABLE IF NOT EXISTS strategy_health_audit (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    source_system VARCHAR(100),
    strategy    VARCHAR(200),
    old_tier    ENUM('CORE','INCUBATOR','BANNED'),
    new_tier    ENUM('CORE','INCUBATOR','BANNED'),
    reason      TEXT,
    metrics_snapshot JSON COMMENT 'expectancy, pf, wr, trades at time of change',
    created_at  DATETIME DEFAULT NOW(),
    INDEX idx_sha_strat (strategy),
    INDEX idx_sha_ts (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## Component 2: Tier-Change Logic

### Ban Threshold (strategy -> BANNED)
- `fees_adj_expectancy < -0.02` (negative buffer to avoid single-day flips) AND `total_trades >= 15`
- OR `win_rate < 0.10` AND `total_trades >= 10` (catches catastrophic failures early)
- Sets `tier_reason` = specific explanation (e.g., "2.2% WR after 141 trades, fees-adj expect -5.6%")

### Demote to INCUBATOR
- `fees_adj_expectancy < 0` AND `total_trades >= 10 but < 15`
- Strategy still tracked in audit trail but excluded from consensus
- Sets `tier_reason` = "fees-adjusted expectancy negative, monitoring (N trades)"

### Promote to CORE
All conditions must be met:
- `fees_adj_expectancy > 0`
- `total_trades >= 30`
- `rolling_30d_wr > 0.35`
- `profit_factor >= 1.2` (extra sanity check)
- Been in INCUBATOR for at least 7 days (no instant flip-flop)
- Walk-forward validation passed (`wf_passed = TRUE`)

### Walk-Forward Gate for Promotion
- Triggered **once** per strategy when it first becomes eligible (30+ trades, positive expectancy)
- Uses existing `walk_forward_validator.py` with configurable windows (default: 3-month train, 1-month test)
- Requires: `sharpe_decay < 0.5` AND `consistency > 0.5`
- Result stored in `wf_passed` column + `walk_forward_results` table
- Only re-runs if `wf_last_checked IS NULL OR wf_last_checked < NOW() - INTERVAL 7 DAY`
- If failed: stays INCUBATOR, `tier_reason` = "walk-forward validation failed (decay=X, consistency=Y)"

### Every Tier Change Logged
Insert into `strategy_health_audit` with old_tier, new_tier, reason, and a JSON snapshot of metrics at that moment.

---

## Component 3: Aggregator Dedup Patch (`aggregator.py`)

### Problem
If Alpha Engine, Mercury2, and KIMI all say "BTC LONG", the aggregator currently counts 3 agreement votes and may send 3 Discord alerts. These aren't independent bets.

### Solution
After consensus formation, collapse picks by `(symbol, direction)`:

```python
consensus = {}
for pick in picks:
    key = (pick["symbol"], pick["direction"])
    if key not in consensus:
        consensus[key] = {
            "confluence_count": 0,
            "confidence": 0.0,
            "source_systems": set(),
            "source_strategies": {},
            # keep best entry/tp/sl
        }
    d = consensus[key]
    d["confluence_count"] += 1
    d["confidence"] = max(d["confidence"], pick["confidence"])
    d["source_systems"].add(pick["source_system"])
```

### Output
- ONE Discord message per `(symbol, direction)` per aggregation run
- `confluence_count` replaces `agreement_count` (backward compat: set both)
- `source_systems` list shows which systems contributed

### Backward Compatibility
- `pick["agreement_count"] = pick["confluence_count"]` for downstream code
- Existing `at_consensus_picks` schema already has `agreement_count` and `source_systems` columns

---

## Component 4: Integration with Aggregator

### Current State (hardcoded)
```python
BANNED_STRATEGIES = {"smart_money_fvg", "fourier_cycle_detector", ...}
DEMOTED_SYSTEMS = {"ml_bg_a", "ml_bg_b", ...}
```

### New State (data-driven)
On startup, aggregator reads `strategy_health/data/banned_strategies.json`:
```json
{
  "banned_strategies": ["opposite_day", "smart_money_fvg", ...],
  "incubator_strategies": ["options_25delta_skew", ...],
  "last_updated": "2026-03-04T12:00:00Z"
}
```

Merges with any remaining hardcoded bans (belt-and-suspenders). INCUBATOR strategies are excluded from consensus but still tracked in raw_picks.

---

## Component 5: Discord Health Report

### Schedule
Separate workflow at 08:00 UTC daily (not every 4h).

### Format
```
Strategy Health Report — 2026-03-04
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CORE (3)
  keltner-bounce        3W/0L   expect:+2.19%  PF:inf
  funding-confluence     2W/1L   expect:+1.84%  PF:3.2
  fear-reversal-scout    1W/0L   expect:+9.30%  PF:inf

INCUBATOR (5)
  options_25delta_skew   1W/0L   expect:+12.1%  needs 29 more trades
  hash_ribbon_buy        0W/0L   collecting...

BANNED (2)
  opposite_day           2W/76L  expect:-5.6%   killed 2026-03-04
  signal_engine          0W/2L   expect:-6.1%   killed 2026-03-02

Tier changes today: 1 (opposite_day: INCUBATOR -> BANNED)
```

### Error Handling
- Retry Discord webhook up to 3x with exponential backoff
- On failure, log to `discord_errors` table (or file) for investigation

---

## File Structure

```
strategy_health/
    __init__.py
    monitor.py              # Main: query DB, compute metrics, update tiers
    discord_report.py       # Daily health card formatter + sender
    schema.sql              # strategy_health + strategy_health_audit DDL
    config.py               # Constants: FEE_RATE, thresholds, loaded from env
    data/
        banned_strategies.json  # Output consumed by aggregator.py
.github/workflows/
    strategy-health-monitor.yml   # Every 4h — metric refresh + tier changes
    strategy-health-report.yml    # Daily 08:00 UTC — Discord report
```

---

## Workflow: strategy-health-monitor.yml

```yaml
name: Strategy Health Monitor
on:
  schedule:
    - cron: '0 */4 * * *'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  refresh:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install deps
        run: pip install pymysql requests
      - name: Run monitor
        env:
          MYSQL_HOST: mysql.50webs.com
          MYSQL_USER: ejaguiar1_stocks
          MYSQL_PASSWORD: ${{ secrets.MYSQL_PASSWORD }}
          MYSQL_DB: ejaguiar1_stocks
          STRATEGY_FEE_RATE: '0.0015'
        run: python -m strategy_health.monitor
      - name: Commit if changed
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add strategy_health/data/banned_strategies.json
          git diff --cached --quiet || git commit -m "strategy-health: update banned_strategies.json"
          git pull --rebase origin main || true
          git push
```

## Workflow: strategy-health-report.yml

```yaml
name: Strategy Health Report
on:
  schedule:
    - cron: '0 8 * * *'
  workflow_dispatch:

jobs:
  report:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install deps
        run: pip install pymysql requests
      - name: Post Discord report
        env:
          MYSQL_HOST: mysql.50webs.com
          MYSQL_USER: ejaguiar1_stocks
          MYSQL_PASSWORD: ${{ secrets.MYSQL_PASSWORD }}
          MYSQL_DB: ejaguiar1_stocks
          DISCORD_HEALTH_WEBHOOK: ${{ secrets.DISCORD_HEALTH_WEBHOOK }}
        run: python -m strategy_health.discord_report
```

---

## Testing

1. **Unit tests** (`tests/test_strategy_health.py`)
   - Mock pymysql cursor, feed fixture trades, assert expectancy/PF match formulas
   - Test tier-change logic respects thresholds and 7-day minimum
   - Test dedup produces one entry per (symbol, direction)

2. **Dry-run mode** — `python -m strategy_health.monitor --dry-run`
   - Prints would-be changes without writing to DB
   - Useful for PR validation

3. **Integration test** (optional)
   - Load fixture CSV into test MySQL, run monitor, assert `strategy_health` rows

---

## Config & Secrets

| Parameter | Source | Default |
|-----------|--------|---------|
| `MYSQL_HOST` | env / secret | mysql.50webs.com |
| `MYSQL_USER` | env / secret | ejaguiar1_stocks |
| `MYSQL_PASSWORD` | GitHub secret | (required) |
| `MYSQL_DB` | env | ejaguiar1_stocks |
| `STRATEGY_FEE_RATE` | env | 0.0015 |
| `BAN_MIN_TRADES` | config.py | 15 |
| `BAN_EXPECT_THRESHOLD` | config.py | -0.02 |
| `CATASTROPHIC_WR` | config.py | 0.10 |
| `CATASTROPHIC_MIN_TRADES` | config.py | 10 |
| `CORE_MIN_TRADES` | config.py | 30 |
| `CORE_MIN_30D_WR` | config.py | 0.35 |
| `CORE_MIN_PF` | config.py | 1.2 |
| `CORE_MIN_INCUBATOR_DAYS` | config.py | 7 |
| `WF_SHARPE_DECAY_MAX` | config.py | 0.5 |
| `WF_CONSISTENCY_MIN` | config.py | 0.5 |
| `DISCORD_HEALTH_WEBHOOK` | GitHub secret | (required) |

---

## Summary of Changes

| File | Action |
|------|--------|
| `strategy_health/monitor.py` | NEW — core metrics + tier management |
| `strategy_health/discord_report.py` | NEW — daily health card |
| `strategy_health/config.py` | NEW — thresholds + env loading |
| `strategy_health/schema.sql` | NEW — 2 tables |
| `strategy_health/__init__.py` | NEW — package init |
| `strategy_health/data/banned_strategies.json` | NEW — output for aggregator |
| `.github/workflows/strategy-health-monitor.yml` | NEW — 4h cron |
| `.github/workflows/strategy-health-report.yml` | NEW — daily Discord |
| `cross_aggregation/aggregator.py` | PATCH — same-symbol dedup + read banned_strategies.json |
