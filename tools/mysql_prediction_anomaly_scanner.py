#!/usr/bin/env python3
"""Scan trading_picks table for anomalies that degrade performance.

Anomaly types:
  1. INVERTED_CONFIDENCE: high-conf picks from anti-correlated sources
  2. DIRECTION_CONFLICT: symbol has simultaneous LONG + SHORT picks
  3. SILENT_DEAD_STRATEGY: strategy with 0 picks in last 7 days but still active

Usage:
    python tools/mysql_prediction_anomaly_scanner.py          # print report
    python tools/mysql_prediction_anomaly_scanner.py --json   # JSON output
    python tools/mysql_prediction_anomaly_scanner.py --check  # exit 1 if anomalies found

Env vars (all optional — uses defaults / sample data when absent):
    DB_HOST             MySQL host (default: mysql.50webs.com)
    DB_USER             MySQL user (default: ejaguiar1_stocks)
    DB_PASS_STOCKS      MySQL password  ← required for live DB; if missing, uses sample data
    DB_NAME             MySQL database  (default: ejaguiar1_stocks)
    DB_PORT             MySQL port      (default: 3306)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Anti-correlated sources derived from config.py analysis:
#   - quan_engine: ~18% CRYPTO volume @ PF=0.70 (net drag, CLAUDE.md §Goal#1)
#   - super_signals: historically net-negative on high-confidence CRYPTO
#   - luxalgo_filters: partial mutation (source_system_status 2026-05-16)
# BLACKLISTED_STRATEGIES in config.py: binance_smart_money, hl_funding_fade,
#   quan_engine_scalp, claude_gainer_st, kimi_signal_tracking
# ---------------------------------------------------------------------------
ANTI_CORRELATED_SOURCES = [
    "super_signals",
    "luxalgo_filters",
    "quan_engine",
]

INVERTED_CONFIDENCE_THRESHOLD = 0.85
SILENT_DEAD_DAYS = 7
LOOK_BACK_DAYS = 30
DIRECTION_CONFLICT_HOURS = 24

# Table to query — try trading_picks first, fall back to at_raw_picks
CANDIDATE_TABLES = ["trading_picks", "live_picks", "at_raw_picks"]


# ---------------------------------------------------------------------------
# DB connection
# ---------------------------------------------------------------------------

def _get_password() -> str | None:
    """Return DB password from any known env var, or None."""
    return (
        os.environ.get("DB_PASS_STOCKS")
        or os.environ.get("DB_STOCKS_PASSWORD")
        or os.environ.get("MYSQL_PASSWORD")
    )


def connect():
    """Return a pymysql connection to ejaguiar1_stocks."""
    try:
        import pymysql  # type: ignore
    except ImportError:
        raise RuntimeError("pymysql is not installed — run: pip install pymysql")

    pw = _get_password()
    if not pw:
        raise ValueError("DB_PASS_STOCKS env var is not set")

    return pymysql.connect(
        host=os.environ.get("DB_HOST", os.environ.get("DB_STOCKS_HOST", "mysql.50webs.com")),
        user=os.environ.get("DB_USER", os.environ.get("DB_STOCKS_USER", "ejaguiar1_stocks")),
        password=pw,
        database=os.environ.get("DB_NAME", os.environ.get("DB_STOCKS_NAME", "ejaguiar1_stocks")),
        port=int(os.environ.get("DB_PORT", os.environ.get("DB_STOCKS_PORT", "3306"))),
        connect_timeout=20,
        read_timeout=60,
        cursorclass=_pymysql_dict_cursor(),
    )


def _pymysql_dict_cursor():
    """Return pymysql.cursors.DictCursor if available, else None (fallback)."""
    try:
        import pymysql.cursors  # type: ignore
        return pymysql.cursors.DictCursor
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Table discovery
# ---------------------------------------------------------------------------

def _resolve_table(cur) -> str:
    """Return the first CANDIDATE_TABLE that exists in the DB."""
    for table in CANDIDATE_TABLES:
        try:
            cur.execute(f"SELECT 1 FROM `{table}` LIMIT 1")
            return table
        except Exception:
            continue
    raise RuntimeError(
        f"None of the candidate tables exist: {CANDIDATE_TABLES}"
    )


# ---------------------------------------------------------------------------
# Anomaly detectors
# ---------------------------------------------------------------------------

def scan_inverted_confidence(cur, table: str) -> list[dict[str, Any]]:
    """Return OPEN, high-confidence picks from anti-correlated CRYPTO sources."""
    placeholders = ", ".join(["%s"] * len(ANTI_CORRELATED_SOURCES))
    sql = f"""
        SELECT symbol, source_system, confidence, direction, created_at
        FROM `{table}`
        WHERE status = 'OPEN'
          AND confidence >= %s
          AND source_system IN ({placeholders})
          AND asset_class = 'CRYPTO'
        ORDER BY confidence DESC
        LIMIT 50
    """
    params = [INVERTED_CONFIDENCE_THRESHOLD] + list(ANTI_CORRELATED_SOURCES)
    cur.execute(sql, params)
    rows = cur.fetchall()
    # Normalise datetime to string for JSON serialisation
    result = []
    for row in rows:
        r = dict(row)
        if isinstance(r.get("created_at"), datetime):
            r["created_at"] = r["created_at"].isoformat()
        result.append(r)
    return result


def scan_direction_conflicts(cur, table: str) -> list[dict[str, Any]]:
    """Return symbols that have simultaneous LONG + SHORT OPEN picks in last 24h."""
    sql = f"""
        SELECT symbol,
               GROUP_CONCAT(DISTINCT direction ORDER BY direction) AS directions,
               COUNT(*) AS pick_count,
               GROUP_CONCAT(DISTINCT source_system ORDER BY source_system) AS sources
        FROM `{table}`
        WHERE status = 'OPEN'
          AND created_at > NOW() - INTERVAL {DIRECTION_CONFLICT_HOURS} HOUR
        GROUP BY symbol
        HAVING COUNT(DISTINCT direction) > 1
    """
    cur.execute(sql)
    return [dict(row) for row in cur.fetchall()]


def scan_silent_dead_strategies(cur, table: str) -> list[dict[str, Any]]:
    """Return source_systems with no pick in last 7d but active within last 30d."""
    sql = f"""
        SELECT source_system,
               MAX(created_at) AS last_pick,
               COUNT(*)        AS total_picks
        FROM `{table}`
        WHERE created_at > NOW() - INTERVAL {LOOK_BACK_DAYS} DAY
        GROUP BY source_system
        HAVING MAX(created_at) < NOW() - INTERVAL {SILENT_DEAD_DAYS} DAY
        ORDER BY last_pick ASC
    """
    cur.execute(sql)
    rows = cur.fetchall()
    result = []
    for row in rows:
        r = dict(row)
        if isinstance(r.get("last_pick"), datetime):
            r["last_pick"] = r["last_pick"].isoformat()
        result.append(r)
    return result


# ---------------------------------------------------------------------------
# Sample data (used when DB_PASS_STOCKS is absent)
# ---------------------------------------------------------------------------

SAMPLE_DATA: dict[str, Any] = {
    "inverted_confidence": {
        "count": 2,
        "picks": [
            {
                "symbol": "BTCUSDT",
                "source_system": "quan_engine",
                "confidence": 0.92,
                "direction": "LONG",
                "created_at": "2026-05-16T00:00:00",
                "_note": "SAMPLE DATA — DB_PASS_STOCKS not set",
            },
            {
                "symbol": "ETHUSDT",
                "source_system": "luxalgo_filters",
                "confidence": 0.87,
                "direction": "SHORT",
                "created_at": "2026-05-16T01:00:00",
                "_note": "SAMPLE DATA — DB_PASS_STOCKS not set",
            },
        ],
    },
    "direction_conflicts": {
        "count": 1,
        "symbols": [
            {
                "symbol": "SOLUSDT",
                "directions": "LONG,SHORT",
                "pick_count": 2,
                "sources": "super_signals,quan_engine",
                "_note": "SAMPLE DATA — DB_PASS_STOCKS not set",
            }
        ],
    },
    "silent_dead_strategies": {
        "count": 1,
        "strategies": [
            {
                "source_system": "hl_funding_fade",
                "last_pick": "2026-05-08T12:00:00",
                "total_picks": 11,
                "_note": "SAMPLE DATA — DB_PASS_STOCKS not set",
            }
        ],
    },
}


# ---------------------------------------------------------------------------
# Main scanner
# ---------------------------------------------------------------------------

def run_scan() -> dict[str, Any]:
    """Run all three anomaly detectors and return the result dict."""
    generated_at = datetime.now(timezone.utc).isoformat()
    pw = _get_password()

    if not pw:
        # No DB credentials — return annotated sample data
        result = {
            "generated_at": generated_at,
            "mode": "SAMPLE_DATA",
            "warning": "DB_PASS_STOCKS not set — showing sample data, not live DB",
            "anomalies": SAMPLE_DATA,
            "total_anomalies": (
                SAMPLE_DATA["inverted_confidence"]["count"]
                + SAMPLE_DATA["direction_conflicts"]["count"]
                + SAMPLE_DATA["silent_dead_strategies"]["count"]
            ),
            "verdict": "ANOMALIES_FOUND",
        }
        return result

    # Live DB path
    try:
        conn = connect()
    except Exception as exc:
        return {
            "generated_at": generated_at,
            "mode": "ERROR",
            "error": str(exc),
            "anomalies": {
                "inverted_confidence": {"count": 0, "picks": []},
                "direction_conflicts": {"count": 0, "symbols": []},
                "silent_dead_strategies": {"count": 0, "strategies": []},
            },
            "total_anomalies": 0,
            "verdict": "ERROR",
        }

    try:
        with conn:
            cur = conn.cursor()
            table = _resolve_table(cur)

            inv_picks = scan_inverted_confidence(cur, table)
            dir_conflicts = scan_direction_conflicts(cur, table)
            silent_dead = scan_silent_dead_strategies(cur, table)

            total = len(inv_picks) + len(dir_conflicts) + len(silent_dead)
            return {
                "generated_at": generated_at,
                "mode": "LIVE_DB",
                "table": table,
                "anomalies": {
                    "inverted_confidence": {
                        "count": len(inv_picks),
                        "picks": inv_picks,
                    },
                    "direction_conflicts": {
                        "count": len(dir_conflicts),
                        "symbols": dir_conflicts,
                    },
                    "silent_dead_strategies": {
                        "count": len(silent_dead),
                        "strategies": silent_dead,
                    },
                },
                "total_anomalies": total,
                "verdict": "CLEAN" if total == 0 else "ANOMALIES_FOUND",
            }
    except Exception as exc:
        return {
            "generated_at": generated_at,
            "mode": "ERROR",
            "error": str(exc),
            "anomalies": {
                "inverted_confidence": {"count": 0, "picks": []},
                "direction_conflicts": {"count": 0, "symbols": []},
                "silent_dead_strategies": {"count": 0, "strategies": []},
            },
            "total_anomalies": 0,
            "verdict": "ERROR",
        }


def print_report(data: dict[str, Any]) -> None:
    """Human-readable report to stdout."""
    print("=" * 70)
    print("MySQL Prediction Anomaly Scanner")
    print(f"Generated : {data['generated_at']}")
    print(f"Mode      : {data.get('mode', 'UNKNOWN')}")
    if "warning" in data:
        print(f"WARNING   : {data['warning']}")
    if "error" in data:
        print(f"ERROR     : {data['error']}")
    print(f"Verdict   : {data['verdict']}")
    print(f"Total     : {data['total_anomalies']} anomaly/ies found")
    print("=" * 70)

    anomalies = data.get("anomalies", {})

    # 1. Inverted confidence
    inv = anomalies.get("inverted_confidence", {})
    print(f"\n[1] INVERTED_CONFIDENCE  ({inv.get('count', 0)} picks)")
    print(f"    Sources checked: {ANTI_CORRELATED_SOURCES}")
    print(f"    Threshold: confidence >= {INVERTED_CONFIDENCE_THRESHOLD}, asset_class=CRYPTO, status=OPEN")
    for p in inv.get("picks", []):
        print(
            f"    • {p.get('symbol'):<12} src={p.get('source_system'):<20} "
            f"conf={p.get('confidence'):.3f}  dir={p.get('direction')}  "
            f"created={p.get('created_at')}"
        )

    # 2. Direction conflicts
    dc = anomalies.get("direction_conflicts", {})
    print(f"\n[2] DIRECTION_CONFLICT  ({dc.get('count', 0)} symbols)")
    print(f"    Window: OPEN picks created in last {DIRECTION_CONFLICT_HOURS}h")
    for s in dc.get("symbols", []):
        print(
            f"    • {s.get('symbol'):<12} directions={s.get('directions')}  "
            f"count={s.get('pick_count')}  sources={s.get('sources')}"
        )

    # 3. Silent-dead strategies
    sd = anomalies.get("silent_dead_strategies", {})
    print(f"\n[3] SILENT_DEAD_STRATEGY  ({sd.get('count', 0)} strategies)")
    print(
        f"    Criteria: active within last {LOOK_BACK_DAYS}d "
        f"but no pick in last {SILENT_DEAD_DAYS}d"
    )
    for st in sd.get("strategies", []):
        print(
            f"    • {st.get('source_system'):<30} "
            f"last_pick={st.get('last_pick')}  total={st.get('total_picks')}"
        )

    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan MySQL trading_picks for prediction anomalies"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of a human-readable report",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit with code 1 if any anomalies are found (for CI gates)",
    )
    args = parser.parse_args(argv)

    data = run_scan()

    if args.json:
        print(json.dumps(data, indent=2, default=str))
    else:
        print_report(data)

    if args.check and data.get("verdict") == "ANOMALIES_FOUND":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
