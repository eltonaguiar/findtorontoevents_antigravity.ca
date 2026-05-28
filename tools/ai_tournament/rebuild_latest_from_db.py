"""
Rebuild ai_tournament_picks_latest.json from the authoritative DB.

The /audit/ai-tournament.html page (and model.html drill-down, plus
build_model_summary.py and update_leaderboard.py) read
audit_dashboard/data/ai_tournament_picks_latest.json as a flat list of pick
dicts. Historically that file was produced by merge_submissions_to_latest.py,
which globs data/ai_tournament/submissions/*.json. That path is fragile: when
the picks fleet writes data/ai_tournament/picks_YYYYMMDD.json (consumed by
ingest_to_db.py) but the per-model submission files are missing/stale, the
merge silently keeps an old snapshot. On 2026-05-28 this stranded the page on
3 models (May-26) while the DB held 42 models / 12 active that day.

ingest_to_db.py already writes every model's picks into
ejaguiar1_stocks.tournament_picks, so the DB is the complete, fresh source of
truth. This rebuild reads it directly and writes the flat snapshot the page
expects — no dependency on the submissions/ glob.

Usage:  DB_PASS_STOCKS=... python tools/ai_tournament/rebuild_latest_from_db.py
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pymysql

REPO = Path(__file__).resolve().parents[2]
LATEST = REPO / "audit_dashboard" / "data" / "ai_tournament_picks_latest.json"

# Columns the page/builders read; excludes heavy internals like
# _model_api_response and dedup hashes to keep the snapshot lean.
FIELDS = (
    "model_id", "provider", "persona_id", "asset_class", "symbol", "direction",
    "entry_price", "take_profit", "stop_loss", "thesis", "strategy_name",
    "catalyst", "confidence", "timeframe", "expected_hold", "status",
    "exit_price", "pnl_pct", "exit_reason", "submitted_at", "resolved_at",
)


def _connect() -> pymysql.connections.Connection:
    pw = os.environ.get("DB_PASS_STOCKS", "")
    return pymysql.connect(
        host=os.environ.get("DB_HOST_STOCKS", "mysql.50webs.com"),
        user=os.environ.get("DB_USER_STOCKS", "ejaguiar1_stocks"),
        password=pw,
        database=os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks"),
        port=3306,
        connect_timeout=25,
        cursorclass=pymysql.cursors.DictCursor,
    )


def _coerce(p: dict) -> dict:
    for k in ("entry_price", "take_profit", "stop_loss", "exit_price", "pnl_pct"):
        if p.get(k) is not None:
            try:
                p[k] = float(p[k])
            except (TypeError, ValueError):
                p[k] = None
    for k in ("submitted_at", "resolved_at"):
        v = p.get(k)
        if isinstance(v, datetime):
            p[k] = v.astimezone(timezone.utc).isoformat()
    return p


def main() -> None:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            f"SELECT {', '.join(FIELDS)} FROM tournament_picks "
            "ORDER BY submitted_at DESC"
        )
        picks = [_coerce(dict(r)) for r in cur.fetchall()]
    finally:
        conn.close()

    LATEST.write_text(json.dumps(picks, indent=2))
    n_models = len({p.get("model_id") for p in picks})
    n_open = sum(1 for p in picks if p.get("status") == "OPEN")
    print(
        f"[rebuild_latest] wrote {LATEST.relative_to(REPO)} — "
        f"{len(picks)} picks, {n_models} models, {n_open} open"
    )


if __name__ == "__main__":
    main()
