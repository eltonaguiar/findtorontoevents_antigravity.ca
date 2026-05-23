# Strategy Health Monitor — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Auto-detect and ban money-losing strategies, promote proven ones, and report health daily to Discord.

**Architecture:** A GitHub Actions cron job (every 4h) queries MySQL `at_signal_outcomes` + `cw_winners`, computes per-strategy expectancy/PF/WR, writes to a new `strategy_health` table, and outputs `banned_strategies.json` consumed by the aggregator. A separate daily job posts a Discord health card.

**Tech Stack:** Python 3.11, pymysql, requests (Discord webhook), MySQL (ejaguiar1_stocks on mysql.50webs.com)

**Design Doc:** `docs/plans/2026-03-04-strategy-health-monitor-design.md`

---

### Task 1: Schema + Config Module

**Files:**
- Create: `strategy_health/__init__.py`
- Create: `strategy_health/schema.sql`
- Create: `strategy_health/config.py`

**Step 1: Create package init**

```python
# strategy_health/__init__.py
"""Strategy Health Monitor — auto-ban/promote strategies based on live performance."""
```

**Step 2: Create schema.sql**

```sql
-- strategy_health/schema.sql
-- Version: 2026-03-04-v1

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS strategy_health (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    source_system     VARCHAR(100) NOT NULL,
    strategy          VARCHAR(200) NOT NULL,
    asset_class       VARCHAR(20),
    total_trades      INT DEFAULT 0,
    wins              INT DEFAULT 0,
    losses            INT DEFAULT 0,
    win_rate          DECIMAL(5,4) DEFAULT 0,
    avg_win_pct       DECIMAL(10,4) DEFAULT 0,
    avg_loss_pct      DECIMAL(10,4) DEFAULT 0,
    expectancy        DECIMAL(10,4) DEFAULT 0,
    fees_adj_expect   DECIMAL(10,4) DEFAULT 0,
    profit_factor     DECIMAL(10,4),
    rolling_30d_wr    DECIMAL(5,4),
    tier              ENUM('CORE','INCUBATOR','BANNED') DEFAULT 'INCUBATOR',
    tier_changed_at   DATETIME,
    tier_reason       TEXT,
    wf_passed         BOOLEAN DEFAULT NULL,
    wf_last_checked   DATETIME,
    last_evaluated    DATETIME,
    UNIQUE KEY uk_health (source_system, strategy),
    INDEX idx_sh_tier (tier)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS strategy_health_audit (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    source_system   VARCHAR(100),
    strategy        VARCHAR(200),
    old_tier        ENUM('CORE','INCUBATOR','BANNED'),
    new_tier        ENUM('CORE','INCUBATOR','BANNED'),
    reason          TEXT,
    metrics_snapshot JSON,
    created_at      DATETIME DEFAULT NOW(),
    INDEX idx_sha_strat (strategy),
    INDEX idx_sha_ts    (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Step 3: Create config.py**

```python
# strategy_health/config.py
"""Configurable thresholds for strategy health evaluation.
All values loadable from environment variables with sensible defaults."""

import os

# --- Database ---
MYSQL_HOST = os.environ.get("MYSQL_HOST", "mysql.50webs.com")
MYSQL_USER = os.environ.get("MYSQL_USER", "ejaguiar1_stocks")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "stocks")
MYSQL_DB = os.environ.get("MYSQL_DB", "ejaguiar1_stocks")

# --- Fee adjustment ---
FEE_RATE = float(os.environ.get("STRATEGY_FEE_RATE", "0.0015"))  # 0.15% per trade

# --- Ban thresholds ---
BAN_MIN_TRADES = int(os.environ.get("BAN_MIN_TRADES", "15"))
BAN_EXPECT_THRESHOLD = float(os.environ.get("BAN_EXPECT_THRESHOLD", "-0.02"))  # -2%
CATASTROPHIC_WR = float(os.environ.get("CATASTROPHIC_WR", "0.10"))  # 10%
CATASTROPHIC_MIN_TRADES = int(os.environ.get("CATASTROPHIC_MIN_TRADES", "10"))

# --- Incubator thresholds ---
INCUBATOR_MIN_TRADES = int(os.environ.get("INCUBATOR_MIN_TRADES", "10"))

# --- Core promotion thresholds ---
CORE_MIN_TRADES = int(os.environ.get("CORE_MIN_TRADES", "30"))
CORE_MIN_30D_WR = float(os.environ.get("CORE_MIN_30D_WR", "0.35"))
CORE_MIN_PF = float(os.environ.get("CORE_MIN_PF", "1.2"))
CORE_MIN_INCUBATOR_DAYS = int(os.environ.get("CORE_MIN_INCUBATOR_DAYS", "7"))

# --- Walk-forward validation ---
WF_SHARPE_DECAY_MAX = float(os.environ.get("WF_SHARPE_DECAY_MAX", "0.5"))
WF_CONSISTENCY_MIN = float(os.environ.get("WF_CONSISTENCY_MIN", "0.5"))
WF_RECHECK_DAYS = int(os.environ.get("WF_RECHECK_DAYS", "7"))

# --- Discord ---
DISCORD_HEALTH_WEBHOOK = os.environ.get("DISCORD_HEALTH_WEBHOOK", "")
```

**Step 4: Run schema against MySQL**

Run: `mysql -h mysql.50webs.com -u ejaguiar1_stocks -p ejaguiar1_stocks < strategy_health/schema.sql`

Or from Python:
```python
import pymysql
from strategy_health.config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB

conn = pymysql.connect(host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASSWORD, database=MYSQL_DB)
with open("strategy_health/schema.sql") as f:
    sql = f.read()
for stmt in sql.split(";"):
    stmt = stmt.strip()
    if stmt and not stmt.startswith("--") and not stmt.startswith("SET"):
        conn.cursor().execute(stmt)
conn.commit()
conn.close()
```

**Step 5: Commit**

```bash
git add strategy_health/__init__.py strategy_health/schema.sql strategy_health/config.py
git commit -m "feat(strategy-health): add schema and config module"
```

---

### Task 2: Core Monitor — Metric Computation

**Files:**
- Create: `strategy_health/monitor.py`
- Create: `strategy_health/data/` (directory)

**Step 1: Create data directory**

```bash
mkdir -p strategy_health/data
echo '{"banned_strategies":[],"incubator_strategies":[],"last_updated":""}' > strategy_health/data/banned_strategies.json
```

**Step 2: Write monitor.py — DB connection + metric queries**

```python
#!/usr/bin/env python3
"""
Strategy Health Monitor
========================
Queries MySQL audit trail for closed trade outcomes, computes per-strategy
expectancy/PF/WR, and manages CORE/INCUBATOR/BANNED tiers.

Run:  python -m strategy_health.monitor [--dry-run]
"""

import argparse
import datetime as dt
import json
import os
import pathlib
import sys
from typing import Dict, List, Optional, Tuple

import pymysql

from strategy_health.config import (
    MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB,
    FEE_RATE,
    BAN_MIN_TRADES, BAN_EXPECT_THRESHOLD,
    CATASTROPHIC_WR, CATASTROPHIC_MIN_TRADES,
    INCUBATOR_MIN_TRADES,
    CORE_MIN_TRADES, CORE_MIN_30D_WR, CORE_MIN_PF, CORE_MIN_INCUBATOR_DAYS,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
BANNED_JSON = REPO_ROOT / "strategy_health" / "data" / "banned_strategies.json"


def get_connection():
    return pymysql.connect(
        host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASSWORD,
        database=MYSQL_DB, charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=15, read_timeout=30,
    )


def ensure_tables(conn):
    """Create strategy_health tables if they don't exist."""
    schema_path = pathlib.Path(__file__).parent / "schema.sql"
    if not schema_path.exists():
        return
    sql = schema_path.read_text()
    cur = conn.cursor()
    for stmt in sql.split(";"):
        stmt = stmt.strip()
        if stmt and not stmt.startswith("--") and not stmt.upper().startswith("SET"):
            try:
                cur.execute(stmt)
            except pymysql.err.OperationalError:
                pass  # table already exists
    conn.commit()


def fetch_strategy_metrics(conn) -> List[Dict]:
    """Query at_signal_outcomes + cw_winners for per-strategy metrics."""
    cur = conn.cursor()

    # ── Source 1: at_signal_outcomes (KIMI, signal_tracker, opposite_day, etc.) ──
    cur.execute("""
        SELECT
            source_system,
            COALESCE(strategy, 'unknown') AS strategy,
            asset_class,
            COUNT(*) AS total_trades,
            SUM(CASE WHEN outcome IN ('WIN','TP_HIT') THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN outcome IN ('LOSS','SL_HIT') THEN 1 ELSE 0 END) AS losses,
            AVG(CASE WHEN outcome IN ('WIN','TP_HIT') THEN pnl_pct END) AS avg_win_pct,
            AVG(CASE WHEN outcome IN ('LOSS','SL_HIT') THEN ABS(pnl_pct) END) AS avg_loss_pct
        FROM at_signal_outcomes
        WHERE outcome IN ('WIN','TP_HIT','LOSS','SL_HIT')
        GROUP BY source_system, strategy, asset_class
    """)
    rows = list(cur.fetchall())

    # ── Source 2: cw_winners (crypto winner scanner) ──
    cur.execute("""
        SELECT
            'cw_winners' AS source_system,
            'crypto_winner_scan' AS strategy,
            'CRYPTO' AS asset_class,
            COUNT(*) AS total_trades,
            SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) AS losses,
            AVG(CASE WHEN outcome = 'win' THEN pnl_pct END) AS avg_win_pct,
            AVG(CASE WHEN outcome = 'loss' THEN ABS(pnl_pct) END) AS avg_loss_pct
        FROM cw_winners
        WHERE outcome IN ('win', 'loss')
    """)
    rows.extend(cur.fetchall())

    # ── Source 3: cw_winners by pair (for per-pair tracking) ──
    cur.execute("""
        SELECT
            'cw_winners' AS source_system,
            CONCAT('cw_', pair) AS strategy,
            'CRYPTO' AS asset_class,
            COUNT(*) AS total_trades,
            SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) AS losses,
            AVG(CASE WHEN outcome = 'win' THEN pnl_pct END) AS avg_win_pct,
            AVG(CASE WHEN outcome = 'loss' THEN ABS(pnl_pct) END) AS avg_loss_pct
        FROM cw_winners
        WHERE outcome IN ('win', 'loss')
        GROUP BY pair
        HAVING COUNT(*) >= 3
    """)
    rows.extend(cur.fetchall())

    return rows


def fetch_rolling_30d_wr(conn, source_system: str, strategy: str) -> Optional[float]:
    """Compute win rate over last 30 days for a specific strategy."""
    cur = conn.cursor()

    if source_system == "cw_winners":
        cur.execute("""
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) AS wins
            FROM cw_winners
            WHERE outcome IN ('win','loss')
              AND resolved_at >= NOW() - INTERVAL 30 DAY
        """)
    else:
        cur.execute("""
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN outcome IN ('WIN','TP_HIT') THEN 1 ELSE 0 END) AS wins
            FROM at_signal_outcomes
            WHERE outcome IN ('WIN','TP_HIT','LOSS','SL_HIT')
              AND source_system = %s
              AND (strategy = %s OR (%s = 'unknown' AND strategy IS NULL))
              AND closed_at >= NOW() - INTERVAL 30 DAY
        """, (source_system, strategy, strategy))

    row = cur.fetchone()
    if row and row["total"] and row["total"] > 0:
        return round(row["wins"] / row["total"], 4)
    return None


def compute_metrics(row: Dict) -> Dict:
    """Compute expectancy, profit factor, and fee-adjusted expectancy from raw DB row."""
    total = row["total_trades"] or 0
    wins = row["wins"] or 0
    losses = row["losses"] or 0
    avg_win = float(row["avg_win_pct"] or 0)
    avg_loss = float(row["avg_loss_pct"] or 0)

    if total == 0:
        return {"win_rate": 0, "expectancy": 0, "fees_adj_expect": 0, "profit_factor": None}

    win_rate = round(wins / total, 4)
    loss_rate = 1 - win_rate

    # expectancy = (WR * avg_win) - (LR * avg_loss)
    expectancy = round((win_rate * avg_win) - (loss_rate * avg_loss), 4)

    # Fee-adjusted: subtract fee cost per trade (converted to %)
    fees_adj = round(expectancy - (FEE_RATE * 100), 4)

    # Profit factor = total wins / abs(total losses)
    total_win_pct = wins * avg_win
    total_loss_pct = losses * avg_loss
    profit_factor = None
    if total_loss_pct > 0:
        profit_factor = round(total_win_pct / total_loss_pct, 4)

    return {
        "win_rate": win_rate,
        "avg_win_pct": round(avg_win, 4),
        "avg_loss_pct": round(avg_loss, 4),
        "expectancy": expectancy,
        "fees_adj_expect": fees_adj,
        "profit_factor": profit_factor,
    }


def determine_tier(
    metrics: Dict,
    total_trades: int,
    current_tier: Optional[str],
    tier_changed_at: Optional[dt.datetime],
    rolling_30d_wr: Optional[float],
    wf_passed: Optional[bool],
) -> Tuple[str, str]:
    """Determine the appropriate tier and reason for a strategy.

    Returns (tier, reason).
    """
    fees_adj = metrics["fees_adj_expect"]
    wr = metrics["win_rate"]
    pf = metrics["profit_factor"]

    # ── Catastrophic failure: immediate ban ──
    if total_trades >= CATASTROPHIC_MIN_TRADES and wr < CATASTROPHIC_WR:
        return "BANNED", f"catastrophic WR {wr*100:.1f}% after {total_trades} trades"

    # ── Ban: negative expectancy with enough data ──
    if total_trades >= BAN_MIN_TRADES and fees_adj < BAN_EXPECT_THRESHOLD:
        return "BANNED", (
            f"fees-adj expectancy {fees_adj:.2f}% after {total_trades} trades "
            f"(WR={wr*100:.1f}%, PF={pf})"
        )

    # ── Core promotion: all criteria met ──
    if (
        total_trades >= CORE_MIN_TRADES
        and fees_adj > 0
        and (rolling_30d_wr is not None and rolling_30d_wr > CORE_MIN_30D_WR)
        and (pf is not None and pf >= CORE_MIN_PF)
        and wf_passed is True
    ):
        # Check minimum incubator time
        if current_tier == "INCUBATOR" and tier_changed_at:
            days_in_incubator = (dt.datetime.utcnow() - tier_changed_at).days
            if days_in_incubator < CORE_MIN_INCUBATOR_DAYS:
                return "INCUBATOR", (
                    f"eligible for CORE but only {days_in_incubator}d in incubator "
                    f"(need {CORE_MIN_INCUBATOR_DAYS}d)"
                )
        return "CORE", (
            f"promoted: {total_trades} trades, fees-adj expect {fees_adj:.2f}%, "
            f"WR={wr*100:.1f}%, PF={pf}, 30d WR={rolling_30d_wr*100:.1f}%, WF passed"
        )

    # ── Incubator: not enough data or marginal ──
    if total_trades >= INCUBATOR_MIN_TRADES and fees_adj < 0:
        return "INCUBATOR", (
            f"fees-adj expectancy negative ({fees_adj:.2f}%), monitoring "
            f"({total_trades} trades)"
        )

    # ── Default: stay in current tier or INCUBATOR ──
    if current_tier == "CORE" and fees_adj > 0:
        return "CORE", "maintaining CORE status"
    if current_tier == "BANNED":
        # Can a banned strategy recover? Only if it now has positive expectancy
        # and enough new trades since ban
        if fees_adj > 0 and total_trades >= CORE_MIN_TRADES:
            return "INCUBATOR", f"recovered: fees-adj expect {fees_adj:.2f}%, moved to INCUBATOR for re-evaluation"
        return "BANNED", "still banned — insufficient recovery"

    return current_tier or "INCUBATOR", f"collecting data ({total_trades} trades)"


def upsert_health(conn, record: Dict, dry_run: bool = False):
    """Insert or update strategy_health row. Log tier changes to audit table."""
    cur = conn.cursor()

    # Fetch current state
    cur.execute(
        "SELECT tier, tier_changed_at, wf_passed, wf_last_checked "
        "FROM strategy_health WHERE source_system = %s AND strategy = %s",
        (record["source_system"], record["strategy"]),
    )
    existing = cur.fetchone()
    old_tier = existing["tier"] if existing else None
    new_tier = record["tier"]

    if dry_run:
        changed = "CHANGED" if old_tier and old_tier != new_tier else "same"
        print(
            f"  [DRY-RUN] {record['source_system']:25s} | {record['strategy']:30s} | "
            f"{old_tier or 'NEW'} -> {new_tier} ({changed}) | "
            f"expect={record['fees_adj_expect']:.2f}% | "
            f"trades={record['total_trades']} | WR={record['win_rate']*100:.1f}%"
        )
        return

    # Upsert
    cur.execute("""
        INSERT INTO strategy_health
            (source_system, strategy, asset_class, total_trades, wins, losses,
             win_rate, avg_win_pct, avg_loss_pct, expectancy, fees_adj_expect,
             profit_factor, rolling_30d_wr, tier, tier_changed_at, tier_reason,
             last_evaluated)
        VALUES
            (%(source_system)s, %(strategy)s, %(asset_class)s, %(total_trades)s,
             %(wins)s, %(losses)s, %(win_rate)s, %(avg_win_pct)s, %(avg_loss_pct)s,
             %(expectancy)s, %(fees_adj_expect)s, %(profit_factor)s, %(rolling_30d_wr)s,
             %(tier)s, %(tier_changed_at)s, %(tier_reason)s, NOW())
        ON DUPLICATE KEY UPDATE
            total_trades    = VALUES(total_trades),
            wins            = VALUES(wins),
            losses          = VALUES(losses),
            win_rate        = VALUES(win_rate),
            avg_win_pct     = VALUES(avg_win_pct),
            avg_loss_pct    = VALUES(avg_loss_pct),
            expectancy      = VALUES(expectancy),
            fees_adj_expect = VALUES(fees_adj_expect),
            profit_factor   = VALUES(profit_factor),
            rolling_30d_wr  = VALUES(rolling_30d_wr),
            tier            = VALUES(tier),
            tier_changed_at = IF(tier <> VALUES(tier), NOW(), tier_changed_at),
            tier_reason     = VALUES(tier_reason),
            last_evaluated  = NOW()
    """, record)

    # Log tier change to audit table
    if old_tier and old_tier != new_tier:
        snapshot = {
            "total_trades": record["total_trades"],
            "wins": record["wins"],
            "losses": record["losses"],
            "win_rate": float(record["win_rate"]),
            "expectancy": float(record["expectancy"]),
            "fees_adj_expect": float(record["fees_adj_expect"]),
            "profit_factor": float(record["profit_factor"]) if record["profit_factor"] else None,
        }
        cur.execute("""
            INSERT INTO strategy_health_audit
                (source_system, strategy, old_tier, new_tier, reason, metrics_snapshot)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            record["source_system"], record["strategy"],
            old_tier, new_tier, record["tier_reason"],
            json.dumps(snapshot),
        ))
        print(f"  [TIER CHANGE] {record['strategy']}: {old_tier} -> {new_tier} — {record['tier_reason']}")

    conn.commit()


def write_banned_json(conn):
    """Write banned_strategies.json consumed by aggregator.py."""
    cur = conn.cursor()
    cur.execute("SELECT source_system, strategy FROM strategy_health WHERE tier = 'BANNED'")
    banned = [row["strategy"] for row in cur.fetchall()]

    cur.execute("SELECT source_system, strategy FROM strategy_health WHERE tier = 'INCUBATOR'")
    incubator = [row["strategy"] for row in cur.fetchall()]

    data = {
        "banned_strategies": sorted(set(banned)),
        "incubator_strategies": sorted(set(incubator)),
        "last_updated": dt.datetime.utcnow().isoformat() + "Z",
    }

    BANNED_JSON.parent.mkdir(parents=True, exist_ok=True)
    BANNED_JSON.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Wrote {BANNED_JSON} — {len(banned)} banned, {len(incubator)} incubator")
    return data


def main():
    parser = argparse.ArgumentParser(description="Strategy Health Monitor")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing to DB")
    args = parser.parse_args()

    print(f"Strategy Health Monitor — {dt.datetime.utcnow().isoformat()}Z")
    print(f"Fee rate: {FEE_RATE*100:.2f}% per trade")
    print()

    conn = get_connection()
    ensure_tables(conn)

    # Fetch raw metrics from all sources
    rows = fetch_strategy_metrics(conn)
    print(f"Found {len(rows)} strategy/source combinations with closed trades")
    print()

    for row in rows:
        source = row["source_system"]
        strategy = row["strategy"]
        total = row["total_trades"] or 0
        asset_class = row.get("asset_class", "CRYPTO")

        # Compute metrics
        metrics = compute_metrics(row)

        # Fetch rolling 30d win rate
        rolling_wr = fetch_rolling_30d_wr(conn, source, strategy)

        # Get current tier state
        cur = conn.cursor()
        cur.execute(
            "SELECT tier, tier_changed_at, wf_passed, wf_last_checked "
            "FROM strategy_health WHERE source_system = %s AND strategy = %s",
            (source, strategy),
        )
        existing = cur.fetchone()

        current_tier = existing["tier"] if existing else None
        tier_changed_at = existing["tier_changed_at"] if existing else None
        wf_passed = existing["wf_passed"] if existing else None

        # Determine new tier
        new_tier, reason = determine_tier(
            metrics, total, current_tier, tier_changed_at, rolling_wr, wf_passed,
        )

        record = {
            "source_system": source,
            "strategy": strategy,
            "asset_class": asset_class,
            "total_trades": total,
            "wins": row["wins"] or 0,
            "losses": row["losses"] or 0,
            "win_rate": metrics["win_rate"],
            "avg_win_pct": metrics["avg_win_pct"],
            "avg_loss_pct": metrics["avg_loss_pct"],
            "expectancy": metrics["expectancy"],
            "fees_adj_expect": metrics["fees_adj_expect"],
            "profit_factor": metrics["profit_factor"],
            "rolling_30d_wr": rolling_wr,
            "tier": new_tier,
            "tier_changed_at": dt.datetime.utcnow() if (current_tier and current_tier != new_tier) else tier_changed_at,
            "tier_reason": reason,
        }

        upsert_health(conn, record, dry_run=args.dry_run)

    if not args.dry_run:
        data = write_banned_json(conn)
        print()
        print(f"Summary: {len(data['banned_strategies'])} banned, {len(data['incubator_strategies'])} incubator")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
```

**Step 3: Test locally with dry-run**

Run: `python -m strategy_health.monitor --dry-run`

Expected: prints each strategy with current tier, proposed tier, and metrics. No DB writes.

**Step 4: Run for real**

Run: `python -m strategy_health.monitor`

Expected: populates `strategy_health` table, writes `strategy_health/data/banned_strategies.json`.

**Step 5: Commit**

```bash
git add strategy_health/monitor.py strategy_health/data/banned_strategies.json
git commit -m "feat(strategy-health): core monitor with expectancy computation and tier management"
```

---

### Task 3: Aggregator Integration — Read banned_strategies.json

**Files:**
- Modify: `cross_aggregation/aggregator.py:112-123` (BANNED_STRATEGIES + DEMOTED_SYSTEMS)

**Step 1: Add banned_strategies.json loader to aggregator.py**

At the top of `aggregator.py`, after `BANNED_STRATEGIES = {…}` (around line 123), add:

```python
# ── Data-driven bans from Strategy Health Monitor ──
_HEALTH_BANNED_PATH = REPO_ROOT / "strategy_health" / "data" / "banned_strategies.json"

def _load_health_bans() -> set:
    """Load banned strategies from strategy_health monitor (merges with hardcoded)."""
    try:
        data = json.loads(_HEALTH_BANNED_PATH.read_text())
        extra = set(data.get("banned_strategies", []))
        if extra:
            print(f"  [HEALTH] Loaded {len(extra)} data-driven bans from banned_strategies.json")
        return extra
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return set()

def _load_health_incubator() -> set:
    """Load incubator strategies (tracked but excluded from consensus)."""
    try:
        data = json.loads(_HEALTH_BANNED_PATH.read_text())
        return set(data.get("incubator_strategies", []))
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return set()
```

**Step 2: Modify the main aggregation function to merge bans**

In the `aggregate()` function (or wherever picks are processed), before the pick loop, add:

```python
    # Merge data-driven bans with hardcoded bans
    active_bans = BANNED_STRATEGIES | _load_health_bans()
    incubator_strats = _load_health_incubator()
```

Then replace `if strategy and strategy in BANNED_STRATEGIES:` (line ~491) with:

```python
            if strategy and strategy in active_bans:
```

And add incubator filtering after the banned check:

```python
            if strategy and strategy in incubator_strats:
                if _HAS_AUDIT and _audit_run_id:
                    try:
                        record_filter(raw_symbol, direction, sys_name,
                                      "incubator_strategy",
                                      f"strategy '{strategy}' is in INCUBATOR (excluded from consensus)",
                                      _audit_run_id)
                    except Exception:
                        pass
                continue
```

**Step 3: Test aggregator still works**

Run: `python cross_aggregation/aggregator.py`

Expected: should print `[HEALTH] Loaded N data-driven bans` and still produce consensus picks normally.

**Step 4: Commit**

```bash
git add cross_aggregation/aggregator.py
git commit -m "feat(aggregator): read data-driven bans from strategy_health monitor"
```

---

### Task 4: Discord Health Report

**Files:**
- Create: `strategy_health/discord_report.py`

**Step 1: Write discord_report.py**

```python
#!/usr/bin/env python3
"""
Strategy Health Discord Report
================================
Posts a daily health card showing CORE/INCUBATOR/BANNED tiers.

Run:  python -m strategy_health.discord_report
"""

import datetime as dt
import json
import time

import pymysql
import requests

from strategy_health.config import (
    MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB,
    DISCORD_HEALTH_WEBHOOK,
)


def get_connection():
    return pymysql.connect(
        host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASSWORD,
        database=MYSQL_DB, charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def fetch_health_data(conn) -> dict:
    """Fetch all strategies grouped by tier."""
    cur = conn.cursor()
    cur.execute("""
        SELECT source_system, strategy, tier, total_trades, wins, losses,
               win_rate, fees_adj_expect, profit_factor, tier_reason, tier_changed_at
        FROM strategy_health
        ORDER BY tier, fees_adj_expect DESC
    """)
    rows = cur.fetchall()

    tiers = {"CORE": [], "INCUBATOR": [], "BANNED": []}
    for r in rows:
        tiers.setdefault(r["tier"], []).append(r)
    return tiers


def fetch_tier_changes_today(conn) -> list:
    """Fetch tier changes from the last 24 hours."""
    cur = conn.cursor()
    cur.execute("""
        SELECT strategy, old_tier, new_tier, reason, created_at
        FROM strategy_health_audit
        WHERE created_at >= NOW() - INTERVAL 24 HOUR
        ORDER BY created_at DESC
    """)
    return list(cur.fetchall())


def format_report(tiers: dict, changes: list) -> str:
    """Format the health report as a Discord code block."""
    today = dt.date.today().isoformat()
    lines = [
        f"Strategy Health Report — {today}",
        "=" * 42,
        "",
    ]

    for tier_name, icon in [("CORE", "OK"), ("INCUBATOR", ".."), ("BANNED", "XX")]:
        strategies = tiers.get(tier_name, [])
        lines.append(f"{tier_name} ({len(strategies)})")
        if not strategies:
            lines.append("  (none)")
        for s in strategies[:15]:  # cap display
            pf_str = f"{float(s['profit_factor']):.1f}" if s["profit_factor"] else "inf"
            expect = float(s["fees_adj_expect"] or 0)
            lines.append(
                f"  [{icon}] {s['strategy'][:28]:28s} "
                f"{s['wins'] or 0}W/{s['losses'] or 0}L "
                f"expect:{expect:+.2f}% PF:{pf_str}"
            )
        lines.append("")

    if changes:
        lines.append(f"Tier changes (24h): {len(changes)}")
        for c in changes[:5]:
            lines.append(f"  {c['strategy']}: {c['old_tier']} -> {c['new_tier']}")
    else:
        lines.append("No tier changes in last 24h")

    return "\n".join(lines)


def send_to_discord(report: str):
    """Post report to Discord with retry."""
    if not DISCORD_HEALTH_WEBHOOK:
        print("No DISCORD_HEALTH_WEBHOOK set, skipping Discord send")
        print(report)
        return

    payload = {
        "content": f"```\n{report}\n```",
        "username": "Strategy Health Monitor",
    }

    for attempt in range(3):
        try:
            resp = requests.post(DISCORD_HEALTH_WEBHOOK, json=payload, timeout=10)
            if resp.status_code in (200, 204):
                print(f"Discord report sent successfully (attempt {attempt + 1})")
                return
            if resp.status_code == 429:  # rate limited
                retry_after = resp.json().get("retry_after", 5)
                print(f"Rate limited, waiting {retry_after}s...")
                time.sleep(retry_after)
                continue
            print(f"Discord returned {resp.status_code}: {resp.text[:200]}")
        except requests.RequestException as e:
            print(f"Discord send failed (attempt {attempt + 1}): {e}")

        if attempt < 2:
            time.sleep(2 ** attempt)

    print("WARNING: All Discord send attempts failed")


def main():
    print(f"Strategy Health Report — {dt.datetime.utcnow().isoformat()}Z")

    conn = get_connection()
    tiers = fetch_health_data(conn)
    changes = fetch_tier_changes_today(conn)
    conn.close()

    report = format_report(tiers, changes)
    print(report)
    print()
    send_to_discord(report)


if __name__ == "__main__":
    main()
```

**Step 2: Test locally (no webhook)**

Run: `python -m strategy_health.discord_report`

Expected: prints formatted report to stdout, says "No DISCORD_HEALTH_WEBHOOK set, skipping Discord send".

**Step 3: Commit**

```bash
git add strategy_health/discord_report.py
git commit -m "feat(strategy-health): Discord daily health report"
```

---

### Task 5: GitHub Actions Workflows

**Files:**
- Create: `.github/workflows/strategy-health-monitor.yml`
- Create: `.github/workflows/strategy-health-report.yml`

**Step 1: Create monitor workflow (every 4h)**

```yaml
# .github/workflows/strategy-health-monitor.yml
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
      - name: Checkout
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install pymysql requests

      - name: Run health monitor
        env:
          MYSQL_HOST: mysql.50webs.com
          MYSQL_USER: ejaguiar1_stocks
          MYSQL_PASSWORD: ${{ secrets.MYSQL_PASSWORD }}
          MYSQL_DB: ejaguiar1_stocks
        run: python -m strategy_health.monitor

      - name: Commit if changed
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add strategy_health/data/banned_strategies.json
          git diff --cached --quiet || git commit -m "strategy-health: update banned_strategies.json [$(date -u '+%Y-%m-%d %H:%M UTC')]"
          git pull --rebase origin main || true
          git push
```

**Step 2: Create report workflow (daily 08:00 UTC)**

```yaml
# .github/workflows/strategy-health-report.yml
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
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install pymysql requests

      - name: Post health report
        env:
          MYSQL_HOST: mysql.50webs.com
          MYSQL_USER: ejaguiar1_stocks
          MYSQL_PASSWORD: ${{ secrets.MYSQL_PASSWORD }}
          MYSQL_DB: ejaguiar1_stocks
          DISCORD_HEALTH_WEBHOOK: ${{ secrets.DISCORD_HEALTH_WEBHOOK }}
        run: python -m strategy_health.discord_report
```

**Step 3: Commit**

```bash
git add .github/workflows/strategy-health-monitor.yml .github/workflows/strategy-health-report.yml
git commit -m "feat(strategy-health): add GitHub Actions workflows (4h monitor + daily report)"
```

---

### Task 6: End-to-End Test + First Run

**Step 1: Run the full monitor locally to populate strategy_health table**

Run: `python -m strategy_health.monitor`

Expected output:
- Lists all strategies with computed metrics
- Bans opposite_day and other negative-expectancy strategies
- Writes `strategy_health/data/banned_strategies.json`

**Step 2: Verify strategy_health table in MySQL**

```python
import pymysql
conn = pymysql.connect(host='mysql.50webs.com', user='ejaguiar1_stocks',
                       password='stocks', database='ejaguiar1_stocks',
                       cursorclass=pymysql.cursors.DictCursor)
cur = conn.cursor()
cur.execute("SELECT tier, COUNT(*) FROM strategy_health GROUP BY tier")
for r in cur.fetchall(): print(r)
cur.execute("SELECT strategy, tier, fees_adj_expect, total_trades FROM strategy_health ORDER BY tier, fees_adj_expect DESC")
for r in cur.fetchall(): print(f"  {r['tier']:10s} {r['strategy']:35s} expect:{float(r['fees_adj_expect'] or 0):+.2f}% trades:{r['total_trades']}")
conn.close()
```

**Step 3: Verify banned_strategies.json is correct**

Run: `cat strategy_health/data/banned_strategies.json | python -m json.tool`

Expected: opposite_day and other negative-expectancy strategies listed under `banned_strategies`.

**Step 4: Run aggregator to verify integration**

Run: `python cross_aggregation/aggregator.py`

Expected: should print `[HEALTH] Loaded N data-driven bans` and filter out banned strategies.

**Step 5: Run Discord report locally**

Run: `python -m strategy_health.discord_report`

Expected: prints formatted table of CORE/INCUBATOR/BANNED tiers.

**Step 6: Final commit with all results**

```bash
git add -A strategy_health/
git commit -m "feat(strategy-health): first run — populate tiers, verify integration"
```

**Step 7: Push to trigger workflows**

```bash
git push origin main
```

Verify the `Strategy Health Monitor` workflow runs successfully in GitHub Actions.
