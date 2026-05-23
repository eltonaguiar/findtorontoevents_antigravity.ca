"""
Tournament Engine for Alpha Engine strategy promotion/demotion.

Strategies start as "Challenger" (paper-only) and earn promotion to
Bronze -> Silver -> Gold through consistent forward performance.

Key design decisions (from Google/Gemini review):
- EMA-based demotion instead of consecutive-loss counting
- Time-weighted performance via EMA win-rate (recent trades weighted more)
- Per-regime tier tracking (strategy can be Gold-in-trending + Bronze-in-ranging)
"""

import sqlite3
import datetime
from typing import Optional


# Tier risk allocations
TIER_RISK = {
    "challenger": 0.0,
    "bronze": 0.005,
    "silver": 0.01,
    "gold": 0.02,
}

TIER_ORDER = ["challenger", "bronze", "silver", "gold"]

# Portfolio-specific win-rate thresholds
PORTFOLIO_THRESHOLDS = {
    "conservative": {"wr": 0.60, "pf": 1.3},
    "moderate":     {"wr": 0.50, "pf": 1.2},
    "aggressive":   {"wr": 0.45, "pf": 1.0},
}

# Promotion requirements per tier (beyond portfolio WR/PF thresholds)
PROMOTION_REQS = {
    "bronze": {"min_trades": 10, "pf_min": 1.0},
    "silver": {"min_trades": 25, "pf_min": None, "sharpe_min": 0.5},
    "gold":   {"min_trades": 50, "pf_min": 1.3, "sharpe_min": 1.0},
}

# EMA smoothing factor for win-rate tracking
EMA_ALPHA = 0.1

# Demotion requires this many consecutive evaluations below threshold
DEMOTE_EVAL_THRESHOLD = 5

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tournament_state (
    entity_id TEXT NOT NULL,
    portfolio TEXT NOT NULL,
    regime TEXT NOT NULL DEFAULT 'all',
    entity_type TEXT DEFAULT 'strategy',
    tier TEXT DEFAULT 'challenger',
    total_trades INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    win_rate REAL DEFAULT 0,
    ema_wr REAL DEFAULT 0.5,
    demote_eval_count INTEGER DEFAULT 0,
    total_pnl REAL DEFAULT 0,
    avg_pnl REAL DEFAULT 0,
    profit_factor REAL DEFAULT 0,
    gross_profit REAL DEFAULT 0,
    gross_loss REAL DEFAULT 0,
    last_trade_date TEXT,
    promoted_at TEXT,
    demoted_at TEXT,
    updated_at TEXT,
    PRIMARY KEY (entity_id, portfolio, regime)
)
"""


def _utcnow_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class TournamentEngine:
    """Manages strategy tier progression with EMA-based demotion and per-regime tracking."""

    def __init__(self, db_path: str, portfolio: str = "moderate"):
        if portfolio not in PORTFOLIO_THRESHOLDS:
            raise ValueError(
                f"Unknown portfolio: {portfolio}. "
                f"Must be one of {list(PORTFOLIO_THRESHOLDS.keys())}"
            )
        self.db_path = db_path
        self.portfolio = portfolio
        self.thresholds = PORTFOLIO_THRESHOLDS[portfolio]
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(CREATE_TABLE_SQL)
            conn.commit()
        finally:
            conn.close()

    def _ensure_state(self, conn: sqlite3.Connection, entity_id: str,
                      regime: str = "all", entity_type: str = "strategy"):
        """Create a state row if it doesn't exist."""
        row = conn.execute(
            "SELECT 1 FROM tournament_state WHERE entity_id=? AND portfolio=? AND regime=?",
            (entity_id, self.portfolio, regime)
        ).fetchone()
        if not row:
            now = _utcnow_iso()
            conn.execute(
                """INSERT INTO tournament_state
                   (entity_id, portfolio, regime, entity_type, tier, ema_wr, updated_at)
                   VALUES (?, ?, ?, ?, 'challenger', 0.5, ?)""",
                (entity_id, self.portfolio, regime, entity_type, now)
            )
            conn.commit()

    def get_tier(self, entity_id: str, regime: Optional[str] = None) -> str:
        """Returns the tier string for the given entity and regime."""
        regime = regime or "all"
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            self._ensure_state(conn, entity_id, regime)
            row = conn.execute(
                "SELECT tier FROM tournament_state WHERE entity_id=? AND portfolio=? AND regime=?",
                (entity_id, self.portfolio, regime)
            ).fetchone()
            return row["tier"] if row else "challenger"
        finally:
            conn.close()

    def get_risk_pct(self, tier: str) -> float:
        """Returns position risk percentage for a given tier."""
        return TIER_RISK.get(tier, 0.0)

    def get_state(self, entity_id: str, regime: Optional[str] = None) -> dict:
        """Returns full state dict for the entity."""
        regime = regime or "all"
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            self._ensure_state(conn, entity_id, regime)
            row = conn.execute(
                "SELECT * FROM tournament_state WHERE entity_id=? AND portfolio=? AND regime=?",
                (entity_id, self.portfolio, regime)
            ).fetchone()
            return dict(row) if row else {}
        finally:
            conn.close()

    def record_trade(self, entity_id: str, won: bool, pnl_pct: float,
                     entity_type: str = "strategy", regime: Optional[str] = None):
        """Records a trade outcome and updates EMA win-rate."""
        regime = regime or "all"
        now = _utcnow_iso()

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            self._ensure_state(conn, entity_id, regime, entity_type)

            row = conn.execute(
                "SELECT * FROM tournament_state WHERE entity_id=? AND portfolio=? AND regime=?",
                (entity_id, self.portfolio, regime)
            ).fetchone()

            total_trades = row["total_trades"] + 1
            wins = row["wins"] + (1 if won else 0)
            losses = row["losses"] + (0 if won else 1)
            win_rate = wins / total_trades if total_trades > 0 else 0.0

            # EMA win-rate update (for demotion smoothing / time-weighted recency)
            latest_result = 1.0 if won else 0.0
            ema_wr = EMA_ALPHA * latest_result + (1 - EMA_ALPHA) * row["ema_wr"]

            # PnL tracking
            total_pnl = row["total_pnl"] + pnl_pct
            avg_pnl = total_pnl / total_trades

            # Profit factor components
            gross_profit = row["gross_profit"] + (pnl_pct if pnl_pct > 0 else 0.0)
            gross_loss = row["gross_loss"] + (abs(pnl_pct) if pnl_pct < 0 else 0.0)
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else (
                float("inf") if gross_profit > 0 else 0.0
            )

            conn.execute(
                """UPDATE tournament_state SET
                   total_trades=?, wins=?, losses=?, win_rate=?, ema_wr=?,
                   total_pnl=?, avg_pnl=?, profit_factor=?, gross_profit=?, gross_loss=?,
                   last_trade_date=?, updated_at=?
                   WHERE entity_id=? AND portfolio=? AND regime=?""",
                (total_trades, wins, losses, win_rate, ema_wr,
                 total_pnl, avg_pnl, profit_factor, gross_profit, gross_loss,
                 now, now,
                 entity_id, self.portfolio, regime)
            )
            conn.commit()
        finally:
            conn.close()

    def evaluate(self, entity_id: str, regime: Optional[str] = None) -> str:
        """Evaluates promotion/demotion and returns new tier.

        Promotion uses raw win_rate (actual statistics over all trades).
        Demotion uses ema_wr (EMA-smoothed, prevents knee-jerk demotions from
        short losing streaks -- addresses Google/Gemini review feedback).
        """
        regime = regime or "all"
        now = _utcnow_iso()

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            self._ensure_state(conn, entity_id, regime)

            row = conn.execute(
                "SELECT * FROM tournament_state WHERE entity_id=? AND portfolio=? AND regime=?",
                (entity_id, self.portfolio, regime)
            ).fetchone()

            current_tier = row["tier"]
            current_idx = TIER_ORDER.index(current_tier)
            total_trades = row["total_trades"]
            win_rate = row["win_rate"]
            ema_wr = row["ema_wr"]
            profit_factor = row["profit_factor"]
            avg_pnl = row["avg_pnl"]
            demote_eval_count = row["demote_eval_count"]

            # Simple Sharpe approximation: avg_pnl as proxy
            # For a proper Sharpe we'd need trade-by-trade std; use avg_pnl scaled
            sharpe_proxy = avg_pnl / 2.0 if avg_pnl > 0 else avg_pnl

            wr_threshold = self.thresholds["wr"]
            pf_threshold = self.thresholds["pf"]

            new_tier = current_tier

            # --- Check promotion (uses raw win_rate for stable assessment) ---
            if current_idx < len(TIER_ORDER) - 1:
                next_tier = TIER_ORDER[current_idx + 1]
                reqs = PROMOTION_REQS[next_tier]

                can_promote = True

                # Check minimum trades
                if total_trades < reqs["min_trades"]:
                    can_promote = False

                # Check raw win_rate >= portfolio threshold
                if win_rate < wr_threshold:
                    can_promote = False

                # Check profit factor
                pf_min = reqs.get("pf_min")
                if pf_min is not None:
                    effective_pf = max(pf_min, pf_threshold) if next_tier != "bronze" else pf_min
                    if profit_factor < effective_pf:
                        can_promote = False

                # Check Sharpe for Silver and Gold
                sharpe_min = reqs.get("sharpe_min")
                if sharpe_min is not None and sharpe_proxy < sharpe_min:
                    can_promote = False

                if can_promote:
                    new_tier = next_tier
                    conn.execute(
                        """UPDATE tournament_state SET
                           tier=?, promoted_at=?, demote_eval_count=0, updated_at=?
                           WHERE entity_id=? AND portfolio=? AND regime=?""",
                        (new_tier, now, now, entity_id, self.portfolio, regime)
                    )
                    conn.commit()
                    return new_tier

            # --- Check demotion (EMA-based, per Google/Gemini feedback) ---
            # EMA smoothing prevents knee-jerk demotion from short losing streaks.
            # Even a 65% WR strategy has ~4.3% chance of 3 consecutive losses,
            # so we require sustained poor EMA for 5+ evaluations before demoting.
            if current_idx > 0:
                demote_threshold = wr_threshold - 0.10
                if ema_wr < demote_threshold:
                    demote_eval_count += 1
                else:
                    demote_eval_count = 0

                if demote_eval_count >= DEMOTE_EVAL_THRESHOLD:
                    new_tier = TIER_ORDER[current_idx - 1]
                    conn.execute(
                        """UPDATE tournament_state SET
                           tier=?, demoted_at=?, demote_eval_count=0, updated_at=?
                           WHERE entity_id=? AND portfolio=? AND regime=?""",
                        (new_tier, now, now, entity_id, self.portfolio, regime)
                    )
                    conn.commit()
                    return new_tier

                # Update demote_eval_count even if no demotion yet
                conn.execute(
                    """UPDATE tournament_state SET demote_eval_count=?, updated_at=?
                       WHERE entity_id=? AND portfolio=? AND regime=?""",
                    (demote_eval_count, now, entity_id, self.portfolio, regime)
                )
                conn.commit()

            return new_tier
        finally:
            conn.close()

    def get_combo_id(self, strategies: list) -> str:
        """Returns sorted alphabetical join of strategy names with '+'."""
        return "+".join(sorted(strategies))

    def get_all_states(self) -> list:
        """Returns all states for this portfolio."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT * FROM tournament_state WHERE portfolio=?",
                (self.portfolio,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
