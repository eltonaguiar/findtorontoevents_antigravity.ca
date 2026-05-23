"""SQLite database for the Social Media Prediction Competition."""
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

from audit_signal_enrichment import enrich_prediction_rows

DB_PATH = Path(__file__).parent / "data" / "predictions.db"


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _create_tables(conn)
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            predictor_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL,
            take_profit REAL,
            stop_loss REAL,
            sentiment_score REAL,
            source_url TEXT,
            source_text TEXT,
            scraped_at TEXT NOT NULL,
            status TEXT DEFAULT 'ACTIVE',
            outcome_pnl_pct REAL,
            resolved_at TEXT,
            resolution_price REAL
        );
        CREATE TABLE IF NOT EXISTS predictors (
            predictor_id TEXT PRIMARY KEY,
            platform TEXT NOT NULL,
            display_name TEXT DEFAULT '',
            profile_url TEXT,
            total_predictions INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            win_rate REAL DEFAULT 0.0,
            avg_pnl_pct REAL DEFAULT 0.0,
            best_pick_pnl REAL,
            worst_pick_pnl REAL,
            sharpe REAL DEFAULT 0.0,
            first_seen TEXT,
            last_active TEXT,
            tier TEXT DEFAULT 'UNRANKED'
        );
        CREATE TABLE IF NOT EXISTS scrape_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT,
            scraped_at TEXT,
            posts_found INTEGER DEFAULT 0,
            predictions_extracted INTEGER DEFAULT 0,
            errors TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_pred_symbol ON predictions(symbol);
        CREATE INDEX IF NOT EXISTS idx_pred_status ON predictions(status);
        CREATE INDEX IF NOT EXISTS idx_pred_predictor ON predictions(predictor_id);
        CREATE INDEX IF NOT EXISTS idx_pred_burst_dedup ON predictions(predictor_id, symbol, direction, scraped_at);
    """)
    # Add analyst tracking columns (safe to re-run — ALTER TABLE ignores if col exists)
    for col, typedef in [
        ("is_known_analyst", "INTEGER DEFAULT 0"),
        ("analyst_category", "TEXT"),
        ("event_id", "TEXT"),  # For prediction market tracking
        ("resolution_date", "TEXT"),  # When prediction resolves
        ("asset_class", "TEXT"),  # crypto | equity | etf | forex | futures
    ]:
        for table in ["predictions", "predictors"]:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typedef}")
            except sqlite3.OperationalError:
                pass  # column already exists
    # KOL performance tracking columns on predictors table
    for col, typedef in [
        ("calibration_score", "REAL"),
        ("dynamic_weight", "REAL DEFAULT 1.0"),
        ("specialty_wr", "REAL"),
        ("last_recalc", "TEXT"),
    ]:
        try:
            conn.execute(f"ALTER TABLE predictors ADD COLUMN {col} {typedef}")
        except sqlite3.OperationalError:
            pass  # column already exists
    conn.commit()


def _sanitize_price_levels(pred: dict) -> dict:
    """Sanitize TP/SL to prevent absurd values from corrupting outcomes.

    Rules:
    - TP/SL must be within 50% of entry_price (if entry_price exists)
    - If no entry_price, TP/SL must be within 10x of each other
    - Nullify values that fail sanity checks rather than rejecting the prediction
    """
    entry = pred.get("entry_price")
    tp = pred.get("take_profit")
    sl = pred.get("stop_loss")

    if entry and entry > 0:
        # TP/SL shouldn't be more than 50% away from entry for crypto/stocks
        max_dist = entry * 0.50
        if tp is not None and abs(tp - entry) > max_dist:
            pred["take_profit"] = None
        if sl is not None and abs(sl - entry) > max_dist:
            pred["stop_loss"] = None
    elif tp and sl and sl > 0:
        # No entry — check TP vs SL ratio isn't absurd
        ratio = tp / sl if sl > 0 else 999
        if ratio > 10 or ratio < 0.1:
            pred["take_profit"] = None
            pred["stop_loss"] = None

    return pred


def insert_prediction(conn: sqlite3.Connection, pred: dict) -> int:
    pred = _sanitize_price_levels(pred)
    if pred.get("source_url"):
        existing = conn.execute(
            "SELECT id FROM predictions WHERE source_url = ?",
            (pred["source_url"],)
        ).fetchone()
        if existing:
            return existing["id"]

    # Burst deduplication: same predictor+symbol+direction within 5 minutes = 1 pick
    # Prevents spam like 31 identical "LONG BNBUSDT" picks from the same user
    existing_burst = conn.execute("""
        SELECT id FROM predictions
        WHERE predictor_id = ? AND symbol = ? AND direction = ?
          AND scraped_at > datetime(?, '-5 minutes')
        LIMIT 1
    """, (
        pred["predictor_id"], pred["symbol"], pred["direction"],
        pred.get("scraped_at", datetime.now(timezone.utc).isoformat()),
    )).fetchone()
    if existing_burst:
        return existing_burst["id"]

    cur = conn.execute("""
        INSERT INTO predictions
            (predictor_id, platform, symbol, direction, entry_price,
             take_profit, stop_loss, sentiment_score, source_url,
             source_text, scraped_at, status, is_known_analyst,
             analyst_category, event_id, resolution_date, asset_class)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?, ?)
    """, (
        pred["predictor_id"], pred["platform"], pred["symbol"],
        pred["direction"], pred.get("entry_price"),
        pred.get("take_profit"), pred.get("stop_loss"),
        pred.get("sentiment_score"), pred.get("source_url"),
        pred.get("source_text"),
        pred.get("scraped_at", datetime.now(timezone.utc).isoformat()),
        pred.get("is_known_analyst", 0),
        pred.get("analyst_category"),
        pred.get("event_id"),
        pred.get("resolution_date"),
        pred.get("asset_class"),
    ))
    conn.commit()
    _upsert_predictor(conn, pred)
    return cur.lastrowid


def _upsert_predictor(conn: sqlite3.Connection, pred: dict) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO predictors (predictor_id, platform, display_name, first_seen, last_active, total_predictions)
        VALUES (?, ?, ?, ?, ?, 1)
        ON CONFLICT(predictor_id) DO UPDATE SET
            last_active = ?, total_predictions = total_predictions + 1
    """, (pred["predictor_id"], pred["platform"],
          pred.get("display_name", pred["predictor_id"]), now, now, now))
    conn.commit()


def resolve_prediction(conn: sqlite3.Connection, pred_id: int,
                       status: str, exit_price: float, pnl_pct: float) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        UPDATE predictions SET status = ?, resolution_price = ?,
               outcome_pnl_pct = ?, resolved_at = ?
        WHERE id = ?
    """, (status, exit_price, pnl_pct, now, pred_id))
    conn.commit()


def get_active_predictions(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM predictions WHERE status = 'ACTIVE' ORDER BY scraped_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def get_leaderboard(conn: sqlite3.Connection, min_picks: int = 3) -> list[dict]:
    rows = conn.execute("""
        SELECT * FROM predictors WHERE total_predictions >= ?
        ORDER BY total_predictions DESC, win_rate DESC
    """, (min_picks,)).fetchall()
    return [dict(r) for r in rows]


def get_analyst_leaderboard(conn: sqlite3.Connection, min_picks: int = 1) -> list[dict]:
    """Return leaderboard filtered to known analysts only."""
    rows = conn.execute("""
        SELECT * FROM predictors WHERE is_known_analyst = 1 AND total_predictions >= ?
        ORDER BY win_rate DESC, total_predictions DESC
    """, (min_picks,)).fetchall()
    return [dict(r) for r in rows]


def get_analyst_active_predictions(conn: sqlite3.Connection) -> list[dict]:
    """Return active predictions from known analysts only."""
    rows = conn.execute("""
        SELECT * FROM predictions WHERE status = 'ACTIVE' AND is_known_analyst = 1
        ORDER BY scraped_at DESC
    """).fetchall()
    return [dict(r) for r in rows]


def get_sample_predictor_ids(conn: sqlite3.Connection) -> set[str]:
    """Predictors that only/primarily came from seeded sample URLs."""
    rows = conn.execute("""
        SELECT DISTINCT predictor_id
        FROM predictions
        WHERE source_url IS NOT NULL
          AND LOWER(source_url) LIKE '%sample%'
    """).fetchall()
    return {str(r["predictor_id"]) for r in rows}


def _is_sample_prediction(pred: dict) -> bool:
    url = str(pred.get("source_url") or "").lower()
    return "/sample" in url or "status/sample" in url


def backfill_predictors(conn: sqlite3.Connection) -> int:
    """Sync predictors table from predictions table.

    Many scrapers (StockTwits, Reddit, Polymarket, etc.) bypass insert_prediction()
    and do raw INSERTs, so their predictor_id never gets an entry in the predictors
    table. This backfill fixes that by upserting from the predictions table.
    """
    conn.execute("""
        INSERT OR IGNORE INTO predictors (predictor_id, platform, display_name, first_seen, last_active, total_predictions)
        SELECT predictor_id, platform, predictor_id, MIN(scraped_at), MAX(scraped_at), COUNT(*)
        FROM predictions
        GROUP BY predictor_id
    """)
    # Update counts and stats for ALL predictors from actual prediction data
    conn.execute("""
        UPDATE predictors SET
            total_predictions = (
                SELECT COUNT(*) FROM predictions p WHERE p.predictor_id = predictors.predictor_id
            ),
            wins = (
                SELECT COUNT(*) FROM predictions p
                WHERE p.predictor_id = predictors.predictor_id
                  AND p.status IN ('TP_HIT', 'EXPIRED_WIN')
            ),
            losses = (
                SELECT COUNT(*) FROM predictions p
                WHERE p.predictor_id = predictors.predictor_id
                  AND p.status IN ('SL_HIT', 'EXPIRED_LOSS')
            ),
            last_active = (
                SELECT MAX(scraped_at) FROM predictions p WHERE p.predictor_id = predictors.predictor_id
            ),
            avg_pnl_pct = (
                SELECT AVG(outcome_pnl_pct) FROM predictions p
                WHERE p.predictor_id = predictors.predictor_id
                  AND p.outcome_pnl_pct IS NOT NULL
            ),
            best_pick_pnl = (
                SELECT MAX(outcome_pnl_pct) FROM predictions p
                WHERE p.predictor_id = predictors.predictor_id
                  AND p.outcome_pnl_pct IS NOT NULL
            ),
            worst_pick_pnl = (
                SELECT MIN(outcome_pnl_pct) FROM predictions p
                WHERE p.predictor_id = predictors.predictor_id
                  AND p.outcome_pnl_pct IS NOT NULL
            )
    """)
    # Recompute win_rate from actual wins/total
    conn.execute("""
        UPDATE predictors SET
            win_rate = CASE WHEN total_predictions > 0
                THEN CAST(wins AS REAL) / total_predictions
                ELSE 0.0 END
    """)
    # Recompute tiers
    conn.execute("""
        UPDATE predictors SET tier = CASE
            WHEN total_predictions < 5 THEN 'UNRANKED'
            WHEN total_predictions >= 50 AND win_rate >= 0.65 THEN 'ELITE'
            WHEN total_predictions >= 25 AND win_rate >= 0.55 THEN 'PROVEN'
            WHEN total_predictions >= 5  AND win_rate >= 0.45 THEN 'MIXED'
            WHEN total_predictions >= 5 THEN 'LOSING'
            ELSE 'UNRANKED'
        END
    """)
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM predictors").fetchone()[0]
    return count


def export_analyst_json(conn: sqlite3.Connection, leaderboard_path: Path, active_path: Path) -> None:
    """Export analyst-specific leaderboard and active calls JSON files."""
    sample_predictors = get_sample_predictor_ids(conn)
    leaders = [r for r in get_analyst_leaderboard(conn) if r.get("predictor_id") not in sample_predictors]
    active = [
        p for p in get_analyst_active_predictions(conn)
        if p.get("predictor_id") not in sample_predictors and not _is_sample_prediction(p)
    ]
    active = enrich_prediction_rows(active, conn)
    lb_data = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "leaderboard": leaders,
        "total_analysts": len(leaders),
        "total_predictions": sum(r.get("total_predictions", 0) for r in leaders),
    }
    leaderboard_path.parent.mkdir(parents=True, exist_ok=True)
    leaderboard_path.write_text(json.dumps(lb_data, indent=2, default=str))

    active_data = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "active_calls": active[:100],
        "total_active": len(active),
    }
    active_path.parent.mkdir(parents=True, exist_ok=True)
    active_path.write_text(json.dumps(active_data, indent=2, default=str))


def export_leaderboard_json(conn: sqlite3.Connection, path: Path) -> None:
    # Backfill predictors from scrapers that bypass insert_prediction()
    backfill_predictors(conn)
    sample_predictors = get_sample_predictor_ids(conn)
    # Get all predictors with at least 1 pick (not just 3+)
    leaders = [r for r in get_leaderboard(conn, min_picks=1) if r.get("predictor_id") not in sample_predictors]
    active = [
        p for p in get_active_predictions(conn)
        if p.get("predictor_id") not in sample_predictors and not _is_sample_prediction(p)
    ]
    active = enrich_prediction_rows(active, conn)
    # Count ALL predictions in DB (not just leaderboard sum) for accurate total
    all_pred_count = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
    data = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "leaderboard": leaders,
        "active_predictions": active,  # No limit - show all
        "total_predictions": all_pred_count,
        "total_predictors": len(leaders),
        "prediction_enrichment": {
            "source": "audit_signal_enrichment",
            "note": "enhanced_conviction blends predictor tier with fleet alignment from dashboard_payload picks.active",
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str))
    active_standalone = path.parent / "active_predictions.json"
    active_standalone.write_text(json.dumps(active, indent=2, default=str))


def export_kol_leaderboard_json(conn: sqlite3.Connection, path: Path) -> None:
    """Export KOL-specific leaderboard with performance stats and dynamic weights."""
    from collections import defaultdict
    sample_predictors = get_sample_predictor_ids(conn)
    rows = conn.execute("""
        SELECT * FROM predictors
        WHERE is_known_analyst = 1 AND total_predictions >= 1
        ORDER BY win_rate DESC, total_predictions DESC
    """).fetchall()
    leaders = [dict(r) for r in rows if r["predictor_id"] not in sample_predictors]

    # Category summary
    cat_stats = defaultdict(lambda: {"count": 0, "total_wr": 0.0, "total_preds": 0})
    for r in leaders:
        cat = r.get("analyst_category") or "unknown"
        cat_stats[cat]["count"] += 1
        cat_stats[cat]["total_wr"] += (r.get("win_rate") or 0.0)
        cat_stats[cat]["total_preds"] += (r.get("total_predictions") or 0)

    category_summary = {}
    for cat, stats in cat_stats.items():
        category_summary[cat] = {
            "count": stats["count"],
            "avg_wr": round(stats["total_wr"] / stats["count"], 4) if stats["count"] else 0,
            "total_predictions": stats["total_preds"],
        }

    # Rank leaders by composite score
    for i, r in enumerate(leaders):
        r["rank"] = i + 1
        r["dynamic_weight"] = r.get("dynamic_weight") or 1.0

    data = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_kols": len(leaders),
        "leaderboard": leaders[:100],
        "category_summary": category_summary,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str))
