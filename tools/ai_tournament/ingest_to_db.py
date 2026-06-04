"""
AI Tournament — MySQL Ingestion Engine.

Writes to the existing `tournament_picks` table (34 columns, 2.8k existing rows).
The table has dedup_key = model_id|symbol|submitted_at for upsert logic.

Usage:
    python tools/ai_tournament/ingest_to_db.py          # normal run
    python tools/ai_tournament/ingest_to_db.py --dry-run # log only, no writes

Environment:
    DB_PASS_STOCKS    MySQL password (default: stocks1234560)
    DB_HOST_STOCKS    MySQL host     (default: mysql.50webs.com)
    DB_NAME_STOCKS    Database name  (default: ejaguiar1_stocks)
    DB_USER_STOCKS    Username       (default: ejaguiar1_stocks)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from normalize import normalize_pick

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PICKS_DIR = REPO_ROOT / "data" / "ai_tournament"
LATEST_PICKS = REPO_ROOT / "audit_dashboard" / "data" / "ai_tournament_picks_latest.json"
DRY_RUN = "--dry-run" in sys.argv


def get_env_or_default(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def load_latest_picks() -> list[dict]:
    """Load the most recent picks file."""
    if PICKS_DIR.exists():
        files = sorted(PICKS_DIR.glob("picks_*.json"), reverse=True)
        if files:
            data = json.loads(files[0].read_text())
            if isinstance(data, list):
                print(f"[ingest] Loaded {len(data)} picks from {files[0].name}")
                return data
    if LATEST_PICKS.exists():
        data = json.loads(LATEST_PICKS.read_text())
        if isinstance(data, list):
            print(f"[ingest] Loaded {len(data)} picks from latest snapshot")
            return data
    print("[ingest] No picks files found")
    return []


def safe_str(v: Any, max_len: int = 500) -> str:
    s = str(v) if v is not None else ""
    return s[:max_len].replace("'", "''")


def safe_float(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def fmt_confidence(v: Any) -> str:
    """Convert confidence to string (HIGH/MEDIUM/LOW) for DB."""
    if isinstance(v, str):
        if v.upper() in ("HIGH", "MEDIUM", "LOW"):
            return v.upper()
        return "MEDIUM"
    try:
        f = float(v)
        if f >= 0.7: return "HIGH"
        if f >= 0.4: return "MEDIUM"
        return "LOW"
    except (TypeError, ValueError):
        return "MEDIUM"


def enrich_confidence_with_persona_wr(picks: list[dict]) -> None:
    """If a pick's confidence is 0/None, fallback to persona_WR as proxy.
    Clamps between 0.25 (floor) and 0.75 (ceiling) for safety."""
    try:
        import pymysql
        conn = pymysql.connect(
            host=os.environ.get("DB_HOST_STOCKS", "mysql.50webs.com"),
            user=os.environ.get("DB_USER_STOCKS", "ejaguiar1_stocks"),
            password=os.environ.get("DB_PASS_STOCKS", "") or os.environ.get("MYSQL_PASSWORD", ""),
            database=os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks"),
            port=3306, connect_timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT persona_id, ROUND(AVG(CASE WHEN status='WIN' THEN 1.0 ELSE 0.0 END), 4) FROM tournament_picks WHERE status IN ('WIN','LOSS') AND persona_id != '' GROUP BY persona_id")
        persona_wr = {r[0]: max(0.25, min(0.75, float(r[1]))) for r in cur.fetchall()}
        conn.close()
        
        enriched = 0
        for p in picks:
            if float(p.get("confidence", 0)) <= 0.01 and p.get("persona_id", "") in persona_wr:
                p["confidence"] = persona_wr[p["persona_id"]]
                enriched += 1
        if enriched:
            print(f"[ingest] Enriched {enriched} picks with persona_WR confidence proxy")
    except Exception as e:
        print(f"[ingest] Persona_WR enrichment skipped (non-fatal): {e}")


def build_upsert_sql(picks: list[dict]) -> tuple[list[tuple], str, str]:
    """Build rows + insert_sql for tournament_picks upsert."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    source = os.path.basename(str(PICKS_DIR / "picks_*.json").replace("*", datetime.now(timezone.utc).strftime("%Y%m%d")))

    rows = []
    for p in picks:
        normalize_pick(p)
        model_id = safe_str(p.get("model_id", "unknown"), 100)
        persona_id = safe_str(p.get("persona_id", ""), 100)
        symbol = safe_str(p.get("symbol", ""), 50)
        asset_class = safe_str(p.get("asset_class", "EQUITY"), 20)
        direction = safe_str(p.get("direction", "LONG"), 10)
        submitted = safe_str(p.get("submitted_at", now), 50)
        dedup_key = f"{model_id}|{symbol}|{submitted.split('+')[0]}"[:500]

        # Determine status: map OPEN/CLOSED/LOSS/WIN
        status_raw = p.get("status", "OPEN")
        pnl = safe_float(p.get("pnl_pct", 0))
        if status_raw == "OPEN":
            status = "OPEN"
        elif pnl > 0:
            status = "WIN"
        else:
            status = "LOSS"

        # Integrity flag
        flag = p.get("data_source", "persona_analysis").upper()[:32]

        # Entry/catalyst/exit from persona or pick data
        entry_criteria = safe_str(p.get("entry_criteria", p.get("thesis", "")), 1000)
        catalyst = safe_str(p.get("catalyst", p.get("thesis", "")[:200]), 500)
        exit_criteria = safe_str(p.get("exit_criteria", ""), 1000)
        risk_factors = safe_str(p.get("risk_factors", ""), 1000)
        rationale = safe_str(p.get("reason", p.get("thesis", "")), 2000)

        rows.append((
            safe_str(model_id, 100),
            safe_str(persona_id, 100),
            safe_str(asset_class, 20),
            safe_str(symbol, 50),
            safe_str(direction, 10),
            safe_float(p.get("entry_price", 0)),
            safe_float(p.get("take_profit", 0)),
            safe_float(p.get("stop_loss", 0)),
            safe_str(p.get("thesis", ""), 2000),
            rationale,
            safe_str(p.get("strategy_name", persona_id), 255),
            entry_criteria,
            catalyst,
            exit_criteria,
            risk_factors,
            fmt_confidence(p.get("confidence", 0.5)),
            safe_str(p.get("timeframe", "14d"), 50),
            "",
            status,
            safe_float(p.get("exit_price", 0)),
            pnl,
            safe_str(p.get("exit_reason", ""), 20),
            submitted,
            safe_str(p.get("resolved_at", ""), 50),
            now,
            safe_str(p.get("data_integrity_flag", flag), 32),
            dedup_key,
        ))

    insert_sql = """
        INSERT INTO tournament_picks
            (model_id, persona_id, asset_class, symbol, direction,
             entry_price, take_profit, stop_loss, thesis, rationale,
             strategy_name, entry_criteria, catalyst, exit_criteria,
             risk_factors, confidence, timeframe, expected_hold,
             status, exit_price, pnl_pct, exit_reason,
             submitted_at, resolved_at, created_at, data_integrity_flag, dedup_key)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            entry_price      = VALUES(entry_price),
            take_profit      = VALUES(take_profit),
            stop_loss        = VALUES(stop_loss),
            thesis           = VALUES(thesis),
            rationale        = VALUES(rationale),
            confidence       = VALUES(confidence),
            status           = VALUES(status),
            pnl_pct          = VALUES(pnl_pct),
            exit_price       = VALUES(exit_price),
            exit_reason      = VALUES(exit_reason),
            resolved_at      = VALUES(resolved_at)
    """

    return rows, insert_sql, source


def main() -> None:
    print(f"[ingest] AI Tournament DB Ingestion — {datetime.now(timezone.utc).isoformat()}")
    if DRY_RUN:
        print("[ingest] DRY RUN — no writes will be performed")

    picks = load_latest_picks()
    if not picks:
        print("[ingest] No picks to ingest — exiting")
        return

    enrich_confidence_with_persona_wr(picks)
    rows, insert_sql, source = build_upsert_sql(picks)
    print(f"[ingest] {len(rows)} rows to upsert into tournament_picks")

    db_pass = get_env_or_default("DB_PASS_STOCKS", "stocks1234560")
    db_host = get_env_or_default("DB_HOST_STOCKS", "mysql.50webs.com")
    db_name = get_env_or_default("DB_NAME_STOCKS", "ejaguiar1_stocks")
    db_user = get_env_or_default("DB_USER_STOCKS", "ejaguiar1_stocks")

    if DRY_RUN:
        print(f"[ingest] Would connect to {db_host}/{db_name} as {db_user}")
        print(f"[ingest] Would upsert {len(rows)} rows")
        print("[ingest] DRY RUN complete")
        return

    try:
        import pymysql
        conn = pymysql.connect(host=db_host, user=db_user, password=db_pass, database=db_name, port=3306, connect_timeout=10, autocommit=False)

        with conn.cursor() as cur:
            batch_size = 50
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                cur.executemany(insert_sql, batch)
                print(f"[ingest] Upserted batch {i // batch_size + 1}/{(len(rows) - 1) // batch_size + 1}")

        conn.commit()
        conn.close()
        print(f"[ingest] Successfully ingested {len(rows)} picks into tournament_picks")

    except ImportError:
        print("[ingest] WARNING: pymysql not installed — skipping")
    except Exception as e:
        print(f"[ingest] ERROR: {e}")
        # Don't crash — JSON files are source of truth


if __name__ == "__main__":
    main()
