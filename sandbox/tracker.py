"""SQLite-backed tracker for opposite picks and timeline snapshots."""

import sqlite3
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple

from sandbox.config import DB_PATH, CHECKPOINTS
from sandbox.core import NormalizedPick, utc_now
from sandbox.pnl import compute_pnl_pct, check_tp_sl

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS opposite_picks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    source_engine TEXT NOT NULL,
    pick_id TEXT UNIQUE NOT NULL,
    original_direction TEXT NOT NULL,
    opposite_direction TEXT NOT NULL,
    entry_price REAL NOT NULL,
    original_tp REAL,
    original_sl REAL,
    opposite_tp REAL,
    opposite_sl REAL,
    picked_at TEXT NOT NULL,
    expiration_at TEXT NOT NULL,
    status TEXT DEFAULT 'ACTIVE',
    closed_at TEXT,
    close_price REAL,
    pnl_pct REAL,
    original_pnl_pct REAL,
    confidence REAL DEFAULT 0.0,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_active_picks ON opposite_picks (status, picked_at);
CREATE INDEX IF NOT EXISTS idx_engine_status ON opposite_picks (source_engine, status);

CREATE TABLE IF NOT EXISTS timeline_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pick_id TEXT NOT NULL,
    checkpoint TEXT NOT NULL,
    snapshot_at TEXT NOT NULL,
    price_at_snapshot REAL NOT NULL,
    pnl_pct_at_snapshot REAL NOT NULL,
    original_pnl_pct REAL NOT NULL,
    original_status TEXT DEFAULT 'ACTIVE',
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE(pick_id, checkpoint)
);

CREATE INDEX IF NOT EXISTS idx_snapshot_pick ON timeline_snapshots (pick_id, checkpoint);
"""


class Tracker:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self):
        self.conn.close()

    # ── Insert new picks ────────────────────────────────────────────

    def insert_picks(self, picks: List[NormalizedPick]) -> int:
        """Insert new opposite picks, skipping duplicates. Returns count inserted."""
        inserted = 0
        for p in picks:
            try:
                self.conn.execute(
                    """INSERT OR IGNORE INTO opposite_picks
                       (symbol, source_engine, pick_id, original_direction,
                        opposite_direction, entry_price, original_tp, original_sl,
                        opposite_tp, opposite_sl, picked_at, expiration_at, confidence)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (p.symbol, p.source_engine, p.source_pick_id,
                     p.original_direction, p.opposite_direction,
                     p.entry_price, p.original_tp, p.original_sl,
                     p.opposite_tp, p.opposite_sl,
                     p.picked_at, p.expiration_at, p.confidence),
                )
                if self.conn.total_changes:
                    inserted += 1
            except sqlite3.IntegrityError:
                pass
        self.conn.commit()
        return inserted

    # ── Get active picks ────────────────────────────────────────────

    def get_active_picks(self) -> List[dict]:
        rows = self.conn.execute(
            "SELECT * FROM opposite_picks WHERE status = 'ACTIVE'"
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Timeline snapshots ──────────────────────────────────────────

    def get_due_snapshots(self, now: datetime) -> List[Tuple[dict, str]]:
        """Return (pick, checkpoint_name) pairs that are due but not yet recorded."""
        active = self.get_active_picks()
        due = []
        for pick in active:
            picked_dt = datetime.fromisoformat(pick["picked_at"].replace("Z", "+00:00"))
            age_seconds = (now - picked_dt).total_seconds()
            for cp_name, cp_seconds in CHECKPOINTS.items():
                if age_seconds >= cp_seconds:
                    exists = self.conn.execute(
                        "SELECT 1 FROM timeline_snapshots WHERE pick_id=? AND checkpoint=?",
                        (pick["pick_id"], cp_name),
                    ).fetchone()
                    if not exists:
                        due.append((pick, cp_name))
        return due

    def insert_snapshot(self, pick_id: str, checkpoint: str,
                        price: float, pnl_pct: float,
                        orig_pnl_pct: float, orig_status: str = "ACTIVE"):
        try:
            self.conn.execute(
                """INSERT OR IGNORE INTO timeline_snapshots
                   (pick_id, checkpoint, snapshot_at, price_at_snapshot,
                    pnl_pct_at_snapshot, original_pnl_pct, original_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (pick_id, checkpoint, utc_now(), price, pnl_pct, orig_pnl_pct, orig_status),
            )
            self.conn.commit()
        except Exception as exc:
            log.error("Snapshot insert failed for %s/%s: %s", pick_id, checkpoint, exc)

    # ── Close picks ─────────────────────────────────────────────────

    def close_pick(self, pick_id: str, status: str, close_price: float,
                   pnl_pct: float, original_pnl_pct: float):
        self.conn.execute(
            """UPDATE opposite_picks
               SET status=?, closed_at=?, close_price=?, pnl_pct=?, original_pnl_pct=?
               WHERE pick_id=?""",
            (status, utc_now(), close_price, pnl_pct, original_pnl_pct, pick_id),
        )
        self.conn.commit()

    def get_expired_picks(self, now: datetime) -> List[dict]:
        """Picks past expiration that are still ACTIVE."""
        now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        rows = self.conn.execute(
            "SELECT * FROM opposite_picks WHERE status='ACTIVE' AND expiration_at <= ?",
            (now_str,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Stats queries ───────────────────────────────────────────────

    def get_engine_stats(self, engine: str = None) -> dict:
        """Compute win/loss/WR/PF for an engine (or all if None)."""
        where = "WHERE status IN ('TP_HIT', 'SL_HIT', 'EXPIRED')"
        params = ()
        if engine:
            where += " AND source_engine = ?"
            params = (engine,)

        rows = self.conn.execute(
            f"SELECT status, pnl_pct FROM opposite_picks {where}", params
        ).fetchall()

        wins = sum(1 for r in rows if r["status"] == "TP_HIT")
        losses = sum(1 for r in rows if r["status"] == "SL_HIT")
        expired_win = sum(1 for r in rows if r["status"] == "EXPIRED" and (r["pnl_pct"] or 0) > 0)
        expired_loss = sum(1 for r in rows if r["status"] == "EXPIRED" and (r["pnl_pct"] or 0) <= 0)
        total_w = wins + expired_win
        total_l = losses + expired_loss
        total = total_w + total_l
        wr = (total_w / total * 100) if total else 0
        win_pnl = sum(r["pnl_pct"] for r in rows if (r["pnl_pct"] or 0) > 0)
        loss_pnl = sum(abs(r["pnl_pct"]) for r in rows if (r["pnl_pct"] or 0) < 0)
        pf = (win_pnl / loss_pnl) if loss_pnl else float("inf")

        return {
            "wins": total_w, "losses": total_l, "total": total,
            "win_rate": round(wr, 1),
            "profit_factor": round(pf, 2) if pf != float("inf") else "∞",
            "win_pnl": round(win_pnl, 2),
            "loss_pnl": round(loss_pnl, 2),
        }

    def get_timeline_avg(self, engine: str = None) -> Dict[str, Dict[str, float]]:
        """Average PnL at each checkpoint, comparing opposite vs original."""
        if engine:
            query = """SELECT t.checkpoint,
                              AVG(t.pnl_pct_at_snapshot) as avg_opp,
                              AVG(t.original_pnl_pct) as avg_orig,
                              COUNT(*) as n
                       FROM timeline_snapshots t
                       JOIN opposite_picks p ON t.pick_id = p.pick_id
                       WHERE p.source_engine = ?
                       GROUP BY t.checkpoint"""
            params = (engine,)
        else:
            query = """SELECT checkpoint,
                              AVG(pnl_pct_at_snapshot) as avg_opp,
                              AVG(original_pnl_pct) as avg_orig,
                              COUNT(*) as n
                       FROM timeline_snapshots
                       GROUP BY checkpoint"""
            params = ()

        rows = self.conn.execute(query, params).fetchall()

        result = {}
        for r in rows:
            result[r["checkpoint"]] = {
                "avg_opposite_pnl": round(r["avg_opp"], 4),
                "avg_original_pnl": round(r["avg_orig"], 4),
                "count": r["n"],
            }
        return result

    def get_best_window(self, engine: str = None) -> str:
        """Return the checkpoint with the highest avg opposite PnL."""
        avgs = self.get_timeline_avg(engine)
        if not avgs:
            return "N/A"
        best = max(avgs.items(), key=lambda x: x[1]["avg_opposite_pnl"])
        return best[0]

    def get_recently_opened(self, since_minutes: int = 35) -> List[dict]:
        """Picks opened in the last N minutes (for Discord new-pick alerts)."""
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=since_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows = self.conn.execute(
            "SELECT * FROM opposite_picks WHERE created_at >= ?", (cutoff,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_recently_closed(self, since_minutes: int = 35) -> List[dict]:
        """Picks closed in the last N minutes."""
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=since_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows = self.conn.execute(
            "SELECT * FROM opposite_picks WHERE closed_at >= ? AND status != 'ACTIVE'",
            (cutoff,),
        ).fetchall()
        return [dict(r) for r in rows]
