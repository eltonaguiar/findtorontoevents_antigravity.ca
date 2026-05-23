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

    # Source 1: at_signal_outcomes
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

    # Source 2: cw_winners overall
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

    # Source 3: cw_winners by pair
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
    """Compute expectancy, profit factor, and fee-adjusted expectancy."""
    total = int(row["total_trades"] or 0)
    wins = int(row["wins"] or 0)
    losses = int(row["losses"] or 0)
    avg_win = float(row["avg_win_pct"] or 0)
    avg_loss = float(row["avg_loss_pct"] or 0)

    if total == 0:
        return {"win_rate": 0, "expectancy": 0, "fees_adj_expect": 0, "profit_factor": None, "avg_win_pct": 0, "avg_loss_pct": 0}

    win_rate = round(float(wins) / float(total), 4)
    loss_rate = 1.0 - win_rate

    expectancy = round((win_rate * avg_win) - (loss_rate * avg_loss), 4)
    fees_adj = round(expectancy - (FEE_RATE * 100), 4)

    total_win_pct = float(wins) * avg_win
    total_loss_pct = float(losses) * avg_loss
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
    """Determine the appropriate tier and reason."""
    fees_adj = metrics["fees_adj_expect"]
    wr = metrics["win_rate"]
    pf = metrics["profit_factor"]

    if total_trades >= CATASTROPHIC_MIN_TRADES and wr < CATASTROPHIC_WR:
        return "BANNED", f"catastrophic WR {wr*100:.1f}% after {total_trades} trades"

    if total_trades >= BAN_MIN_TRADES and fees_adj < BAN_EXPECT_THRESHOLD:
        return "BANNED", (
            f"fees-adj expectancy {fees_adj:.2f}% after {total_trades} trades "
            f"(WR={wr*100:.1f}%, PF={pf})"
        )

    if (
        total_trades >= CORE_MIN_TRADES
        and fees_adj > 0
        and (rolling_30d_wr is not None and rolling_30d_wr > CORE_MIN_30D_WR)
        and (pf is not None and pf >= CORE_MIN_PF)
        and wf_passed is True
    ):
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

    if total_trades >= INCUBATOR_MIN_TRADES and fees_adj < 0:
        return "INCUBATOR", (
            f"fees-adj expectancy negative ({fees_adj:.2f}%), monitoring "
            f"({total_trades} trades)"
        )

    if current_tier == "CORE" and fees_adj > 0:
        return "CORE", "maintaining CORE status"
    if current_tier == "BANNED":
        if fees_adj > 0 and total_trades >= CORE_MIN_TRADES:
            return "INCUBATOR", f"recovered: fees-adj expect {fees_adj:.2f}%, moved to INCUBATOR for re-evaluation"
        return "BANNED", "still banned — insufficient recovery"

    return current_tier or "INCUBATOR", f"collecting data ({total_trades} trades)"


def upsert_health(conn, record: Dict, dry_run: bool = False):
    """Insert or update strategy_health row. Log tier changes to audit table."""
    cur = conn.cursor()

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

    rows = fetch_strategy_metrics(conn)
    print(f"Found {len(rows)} strategy/source combinations with closed trades")
    print()

    for row in rows:
        source = row["source_system"]
        strategy = row["strategy"]
        total = row["total_trades"] or 0
        asset_class = row.get("asset_class", "CRYPTO")

        metrics = compute_metrics(row)
        rolling_wr = fetch_rolling_30d_wr(conn, source, strategy)

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
