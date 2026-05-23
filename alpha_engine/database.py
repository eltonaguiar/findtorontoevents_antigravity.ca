"""
ALPHA_ENGINE -- SQLite Persistence Layer
========================================
Tracks every signal, pick, and strategy performance metric.
Designed for ML feature extraction and forward-looking validation.

Tables:
  signals  -- every raw signal generated (BUY/SELL with TP/SL)
  picks    -- open and closed positions with outcomes
  strategy_stats -- rolling performance per strategy
  regime   -- market regime snapshots
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from config import DATA_DIR, DB_PATH

# Import standardized win rate calculation
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shared import calculate_win_rate


class SQLiteStore:
    """Thread-safe SQLite store for ALPHA_ENGINE."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    def _create_tables(self):
        c = self._conn
        c.executescript("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            strategy TEXT NOT NULL,
            symbol TEXT NOT NULL,
            category TEXT,
            signal_type TEXT NOT NULL,       -- BUY or SELL
            entry_price REAL NOT NULL,
            take_profit REAL,
            stop_loss REAL,
            confidence REAL,                 -- 0.0-1.0
            ml_score REAL,                   -- ML-assigned probability
            risk_reward REAL,
            reason TEXT,
            timeframe TEXT,
            regime TEXT,
            regime_confidence REAL,
            atr_at_entry REAL,
            rsi_at_entry REAL,
            volume_ratio REAL,
            extra_json TEXT                  -- flexible JSON for strategy-specific data
        );

        CREATE TABLE IF NOT EXISTS picks (
            id TEXT PRIMARY KEY,             -- strategy::symbol::date
            strategy TEXT NOT NULL,
            symbol TEXT NOT NULL,
            category TEXT,
            signal_type TEXT NOT NULL,
            entry_price REAL NOT NULL,
            entry_date TEXT NOT NULL,
            take_profit REAL,
            stop_loss REAL,
            confidence REAL,
            ml_score REAL,
            exit_price REAL,
            exit_date TEXT,
            exit_reason TEXT,               -- TP_HIT | SL_HIT | TRAILING | TIME_EXIT | MANUAL
            pnl_pct REAL,
            pnl_dollar REAL,
            high_water_mark REAL,           -- highest price during hold
            status TEXT DEFAULT 'OPEN',     -- OPEN | WON | LOST | BREAKEVEN | EXPIRED
            regime_at_entry TEXT,
            atr_at_entry REAL,
            rsi_at_entry REAL,
            volume_ratio REAL,
            hold_days INTEGER,
            extra_json TEXT
        );

        CREATE TABLE IF NOT EXISTS strategy_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date TEXT NOT NULL,
            strategy TEXT NOT NULL,
            total_signals INTEGER DEFAULT 0,
            total_picks INTEGER DEFAULT 0,
            closed_picks INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            win_rate REAL,
            avg_pnl_pct REAL,
            total_pnl_pct REAL,
            sharpe REAL,
            sortino REAL,
            max_drawdown REAL,
            profit_factor REAL,
            avg_hold_days REAL,
            kelly_fraction REAL,
            UNIQUE(snapshot_date, strategy)
        );

        CREATE TABLE IF NOT EXISTS regime (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            spy_regime TEXT,               -- bull | bear | sideways
            crypto_regime TEXT,            -- risk_on | risk_off | neutral
            vix_level REAL,
            dxy_trend TEXT,                -- up | down | flat
            fear_greed_crypto INTEGER,
            btc_dominance REAL,
            vol_20d REAL,
            extra_json TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_signals_strategy ON signals(strategy);
        CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol);
        CREATE INDEX IF NOT EXISTS idx_signals_ts ON signals(timestamp);
        CREATE INDEX IF NOT EXISTS idx_picks_status ON picks(status);
        CREATE INDEX IF NOT EXISTS idx_picks_strategy ON picks(strategy);
        CREATE INDEX IF NOT EXISTS idx_regime_ts ON regime(timestamp);
        """)
        c.commit()

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def record_signal(self, signal: dict) -> int:
        """Record a raw signal. Returns signal ID."""
        extra = signal.get("extra", {})
        cur = self._conn.execute("""
            INSERT INTO signals (
                timestamp, strategy, symbol, category, signal_type,
                entry_price, take_profit, stop_loss, confidence, ml_score,
                risk_reward, reason, timeframe, regime, regime_confidence,
                atr_at_entry, rsi_at_entry, volume_ratio, extra_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signal.get("timestamp", datetime.now(timezone.utc).isoformat()),
            signal["strategy"], signal["symbol"],
            signal.get("category", ""), signal.get("signal_type", "BUY"),
            signal["entry_price"],
            signal.get("take_profit"), signal.get("stop_loss"),
            signal.get("confidence"), signal.get("ml_score"),
            signal.get("risk_reward"), signal.get("reason", ""),
            signal.get("timeframe", "1d"),
            signal.get("regime"), signal.get("regime_confidence"),
            signal.get("atr_at_entry"), signal.get("rsi_at_entry"),
            signal.get("volume_ratio"),
            json.dumps(extra) if extra else None,
        ))
        self._conn.commit()
        return cur.lastrowid

    # ------------------------------------------------------------------
    # Picks (open/closed positions)
    # ------------------------------------------------------------------

    def open_pick(self, pick: dict) -> str:
        """Open a new pick from a signal. Returns pick ID."""
        pick_id = f"{pick['strategy']}::{pick['symbol']}::{pick.get('entry_date', datetime.now(timezone.utc).strftime('%Y-%m-%d'))}"
        extra = pick.get("extra", {})
        self._conn.execute("""
            INSERT OR REPLACE INTO picks (
                id, strategy, symbol, category, signal_type,
                entry_price, entry_date, take_profit, stop_loss,
                confidence, ml_score, status, regime_at_entry,
                atr_at_entry, rsi_at_entry, volume_ratio, extra_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?, ?, ?)
        """, (
            pick_id, pick["strategy"], pick["symbol"],
            pick.get("category", ""), pick.get("signal_type", "BUY"),
            pick["entry_price"],
            pick.get("entry_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
            pick.get("take_profit"), pick.get("stop_loss"),
            pick.get("confidence"), pick.get("ml_score"),
            pick.get("regime"), pick.get("atr_at_entry"),
            pick.get("rsi_at_entry"), pick.get("volume_ratio"),
            json.dumps(extra) if extra else None,
        ))
        self._conn.commit()
        return pick_id

    def close_pick(self, pick_id: str, exit_price: float, exit_reason: str,
                   high_water_mark: Optional[float] = None,
                   transaction_cost_pct: float = 0.0,
                   cost_model: str = "") -> dict:
        """Close an open pick with transaction cost deduction. Returns summary."""
        row = self._conn.execute(
            "SELECT * FROM picks WHERE id = ?", (pick_id,)
        ).fetchone()
        if not row:
            return {"error": f"Pick {pick_id} not found"}

        entry_price = row["entry_price"]

        # Gross P&L (before costs) -- direction-aware for SHORT trades
        try:
            signal_type = str(row["signal_type"]).upper()
        except (KeyError, IndexError):
            signal_type = "BUY"
        if signal_type in ("SELL", "SHORT"):
            gross_pnl_pct = (entry_price - exit_price) / entry_price if entry_price > 0 else 0.0
        else:
            gross_pnl_pct = (exit_price - entry_price) / entry_price if entry_price > 0 else 0.0

        # Net P&L (after transaction costs)
        net_pnl_pct = gross_pnl_pct - transaction_cost_pct

        # Use allocation from extra_json if available, else fallback
        extra = json.loads(row["extra_json"]) if row["extra_json"] else {}
        allocation = float(extra.get("allocation", 2000))
        pnl_dollar = net_pnl_pct * allocation

        # WR standard: wins(pnl>0) / resolved(pnl!=0), excludes zero-PnL and open trades
        # Zero PnL = BREAKEVEN (excluded from win rate calculation)
        if net_pnl_pct > 0:
            status = "WON"
        elif net_pnl_pct < 0:
            status = "LOST"
        else:
            status = "BREAKEVEN"
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        entry_dt = row["entry_date"]
        hold_days = 1
        try:
            hold_days = (datetime.strptime(now, "%Y-%m-%d") -
                         datetime.strptime(entry_dt, "%Y-%m-%d")).days
        except (ValueError, TypeError):
            pass

        # Store net P&L in the main columns; gross P&L and costs in extra_json
        extra["gross_pnl_pct"] = round(gross_pnl_pct, 6)
        extra["net_pnl_pct"] = round(net_pnl_pct, 6)
        extra["transaction_cost_pct"] = round(transaction_cost_pct, 6)
        extra["cost_model"] = cost_model
        extra["closed_at"] = datetime.now(timezone.utc).isoformat()

        self._conn.execute("""
            UPDATE picks SET
                exit_price = ?, exit_date = ?, exit_reason = ?,
                pnl_pct = ?, pnl_dollar = ?, status = ?,
                high_water_mark = ?, hold_days = ?, extra_json = ?
            WHERE id = ?
        """, (exit_price, now, exit_reason, round(net_pnl_pct, 6),
              round(pnl_dollar, 2), status, high_water_mark, hold_days,
              json.dumps(extra), pick_id))
        self._conn.commit()

        return {
            "pick_id": pick_id, "symbol": row["symbol"],
            "strategy": row["strategy"],
            "gross_pnl_pct": round(gross_pnl_pct * 100, 2),
            "net_pnl_pct": round(net_pnl_pct * 100, 2),
            "pnl_pct": round(net_pnl_pct * 100, 2),
            "pnl_dollar": round(pnl_dollar, 2), "status": status,
            "exit_reason": exit_reason, "hold_days": hold_days,
            "transaction_cost_pct": round(transaction_cost_pct * 100, 4),
        }

    def get_open_picks(self, strategy: Optional[str] = None) -> list[dict]:
        """Get all open picks, optionally filtered by strategy."""
        query = "SELECT * FROM picks WHERE status = 'OPEN'"
        params = []
        if strategy:
            query += " AND strategy = ?"
            params.append(strategy)
        rows = self._conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_closed_picks(self, strategy: Optional[str] = None,
                         limit: int = 500) -> list[dict]:
        """Get closed picks for ML training."""
        query = "SELECT * FROM picks WHERE status IN ('WON','LOST','BREAKEVEN','EXPIRED')"
        params: list = []
        if strategy:
            query += " AND strategy = ?"
            params.append(strategy)
        query += " ORDER BY exit_date DESC LIMIT ?"
        params.append(limit)
        rows = self._conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def count_open_picks(self, strategy: Optional[str] = None) -> int:
        query = "SELECT COUNT(*) FROM picks WHERE status = 'OPEN'"
        params = []
        if strategy:
            query += " AND strategy = ?"
            params.append(strategy)
        return self._conn.execute(query, params).fetchone()[0]

    # ------------------------------------------------------------------
    # Strategy stats
    # ------------------------------------------------------------------

    def compute_strategy_stats(self, strategy: str, cutoff_time: Optional[datetime] = None) -> dict:
        """Compute live performance metrics for a strategy up to cutoff_time (for ML training)."""
        query = "SELECT * FROM picks WHERE strategy = ? AND status IN ('WON','LOST','BREAKEVEN','EXPIRED')"
        params = [strategy]
        if cutoff_time:
            query += " AND entry_date < ?"
            params.append(cutoff_time.isoformat())
        rows = self._conn.execute(query, params).fetchall()
        if not rows:
            return {"strategy": strategy, "closed_picks": 0}

        pnls = [r["pnl_pct"] for r in rows if r["pnl_pct"] is not None]
        if not pnls:
            return {"strategy": strategy, "closed_picks": len(rows)}

        # WR standard: wins(pnl>0) / resolved(pnl!=0), excludes zero-PnL and open trades
        wins = sum(1 for p in pnls if p > 0)
        losses = sum(1 for p in pnls if p < 0)
        resolved = wins + losses
        # Use standardized win rate calculation
        win_rate = calculate_win_rate(wins, resolved)
        avg_pnl = sum(pnls) / len(pnls)
        total_pnl = sum(pnls)

        # Sharpe (annualized, assuming daily resolution)
        import numpy as np
        pnl_arr = np.array(pnls)
        sharpe = (pnl_arr.mean() / pnl_arr.std() * np.sqrt(252)
                  if pnl_arr.std() > 0 else 0.0)

        # Sortino (downside deviation only)
        downside = pnl_arr[pnl_arr < 0]
        sortino = (pnl_arr.mean() / downside.std() * np.sqrt(252)
                   if len(downside) > 0 and downside.std() > 0 else sharpe)

        # Max drawdown
        cum = np.cumsum(pnl_arr)
        peak = np.maximum.accumulate(cum)
        dd = cum - peak
        max_dd = float(dd.min()) if len(dd) > 0 else 0.0

        # Profit factor
        gross_profit = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Kelly fraction
        if win_rate > 0 and win_rate < 1:
            avg_win = np.mean([p for p in pnls if p > 0]) if wins > 0 else 0
            avg_loss_val = abs(np.mean([p for p in pnls if p < 0])) if losses > 0 else 1
            kelly = win_rate - (1 - win_rate) / (avg_win / avg_loss_val) if avg_loss_val > 0 else 0
        else:
            kelly = 0.0

        # Rolling Sharpe (last 20 trades) -- used by auto-tuner to catch
        # strategies that were once good but are now degrading
        rolling_window = 20
        if len(pnl_arr) >= rolling_window:
            recent = pnl_arr[-rolling_window:]
            rolling_sharpe = (recent.mean() / recent.std() * np.sqrt(252)
                              if recent.std() > 0 else 0.0)
        else:
            rolling_sharpe = sharpe  # not enough data, use overall

        hold_days = [r["hold_days"] for r in rows if r["hold_days"] is not None]
        avg_hold = sum(hold_days) / len(hold_days) if hold_days else 0

        # Direction-aware stats (Feb 26 2026) -- used by auto-tuner to avoid
        # killing strategies that are strong in one direction
        direction_stats = {}
        for direction in ("BUY", "SELL"):
            d_rows = [r for r in rows if (dict(r) if not isinstance(r, dict) else r).get("signal_type") == direction]
            d_pnls = [r["pnl_pct"] for r in d_rows if r["pnl_pct"] is not None]
            if d_pnls:
                # WR standard: wins(pnl>0) / resolved(pnl!=0), excludes zero-PnL
                d_wins = sum(1 for p in d_pnls if p > 0)
                d_losses = sum(1 for p in d_pnls if p < 0)
                d_resolved = d_wins + d_losses
                direction_stats[direction] = {
                    "closed": len(d_pnls),
                    "wins": d_wins,
                    "losses": d_losses,
                    "win_rate": round(calculate_win_rate(d_wins, d_resolved), 4),
                    "avg_pnl": round(sum(d_pnls) / len(d_pnls), 6),
                }

        stats = {
            "strategy": strategy,
            "closed_picks": len(pnls),
            "wins": wins, "losses": losses,
            "win_rate": round(win_rate, 4),
            "avg_pnl_pct": round(avg_pnl, 6),
            "total_pnl_pct": round(total_pnl, 6),
            "sharpe": round(float(sharpe), 3),
            "sortino": round(float(sortino), 3),
            "rolling_sharpe": round(float(rolling_sharpe), 3),
            "max_drawdown": round(float(max_dd), 6),
            "profit_factor": round(float(profit_factor), 3),
            "kelly_fraction": round(float(kelly), 4),
            "avg_hold_days": round(avg_hold, 1),
            "direction_stats": direction_stats,
        }

        # Persist snapshot
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._conn.execute("""
            INSERT OR REPLACE INTO strategy_stats (
                snapshot_date, strategy, total_signals, total_picks, closed_picks,
                wins, losses, win_rate, avg_pnl_pct, total_pnl_pct,
                sharpe, sortino, max_drawdown, profit_factor, avg_hold_days, kelly_fraction
            ) VALUES (?, ?, 0, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (today, strategy, len(pnls), wins, losses,
              stats["win_rate"], stats["avg_pnl_pct"], stats["total_pnl_pct"],
              stats["sharpe"], stats["sortino"], stats["max_drawdown"],
              stats["profit_factor"], stats["avg_hold_days"], stats["kelly_fraction"]))
        self._conn.commit()
        return stats

    # ------------------------------------------------------------------
    # Regime
    # ------------------------------------------------------------------

    def record_regime(self, regime_data: dict):
        """Record a market regime snapshot."""
        self._conn.execute("""
            INSERT INTO regime (
                timestamp, spy_regime, crypto_regime, vix_level,
                dxy_trend, fear_greed_crypto, btc_dominance, vol_20d, extra_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            regime_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            regime_data.get("spy_regime"),
            regime_data.get("crypto_regime"),
            regime_data.get("vix_level"),
            regime_data.get("dxy_trend"),
            regime_data.get("fear_greed_crypto"),
            regime_data.get("btc_dominance"),
            regime_data.get("vol_20d"),
            json.dumps(regime_data.get("extra", {})) or None,
        ))
        self._conn.commit()

    # ------------------------------------------------------------------
    # ML feature export
    # ------------------------------------------------------------------

    def get_ml_training_data(self) -> pd.DataFrame:
        """Export closed picks as DataFrame for ML training.

        Includes computed risk_reward and extra_json so the ML ranker
        can reconstruct feature-rich training rows (funding_rate,
        orderbook_imbalance, regime details, etc.).
        """
        query = """
            SELECT
                p.strategy, p.symbol, p.category, p.signal_type,
                p.entry_price, p.take_profit, p.stop_loss,
                p.confidence, p.ml_score,
                p.pnl_pct, p.status,
                p.regime_at_entry, p.atr_at_entry, p.rsi_at_entry,
                p.volume_ratio, p.hold_days, p.entry_date, p.exit_date,
                p.extra_json,
                CASE
                    WHEN p.stop_loss IS NOT NULL AND p.stop_loss != 0
                         AND p.entry_price IS NOT NULL AND p.entry_price != 0
                         AND p.take_profit IS NOT NULL
                         AND p.signal_type IN ('BUY', 'LONG')
                    THEN ABS(p.take_profit - p.entry_price) / NULLIF(ABS(p.entry_price - p.stop_loss), 0)
                    WHEN p.stop_loss IS NOT NULL AND p.stop_loss != 0
                         AND p.entry_price IS NOT NULL AND p.entry_price != 0
                         AND p.take_profit IS NOT NULL
                         AND p.signal_type = 'SHORT'
                    THEN ABS(p.entry_price - p.take_profit) / NULLIF(ABS(p.stop_loss - p.entry_price), 0)
                    ELSE NULL
                END AS risk_reward
            FROM picks p
            WHERE p.status IN ('WON', 'LOST', 'EXPIRED')
            ORDER BY p.exit_date DESC
        """
        return pd.read_sql_query(query, self._conn)

    def import_closed_picks_json(self, json_path: Optional[Path] = None) -> int:
        """Import closed picks from JSON file into the picks table.

        Used on CI where the SQLite DB is ephemeral but closed_picks.json
        is committed to the repo. Skips picks that already exist (by id).
        Returns count of newly imported picks.

        Also imports from closed_picks_fast.json (properly labeled alpha engine
        picks with WON/LOST/EXPIRED status) and maps CLOSED status picks to
        WON/LOST based on pnl_pct when available.
        """
        all_picks = []

        # Load from primary file
        primary_path = json_path or (DATA_DIR / "closed_picks.json")
        if primary_path.exists():
            try:
                with open(primary_path, encoding="utf-8") as f:
                    all_picks.extend(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass

        # Also load from closed_picks_fast.json (313+ properly labeled picks)
        fast_path = DATA_DIR / "closed_picks_fast.json"
        if fast_path.exists() and str(fast_path) != str(primary_path):
            try:
                with open(fast_path, encoding="utf-8") as f:
                    fast_picks = json.load(f)
                    # Mark source so we can track provenance
                    for p in fast_picks:
                        if not p.get("source"):
                            p["source"] = "alpha_engine_fast"
                    all_picks.extend(fast_picks)
            except (json.JSONDecodeError, OSError):
                pass

        if not all_picks:
            return 0

        imported = 0
        for p in all_picks:
            status = p.get("status", "")
            # Map CLOSED status to WON/LOST based on pnl_pct
            if status == "CLOSED":
                pnl = float(p.get("pnl_pct", 0) or 0)
                if pnl > 0:
                    status = "WON"
                elif pnl < 0:
                    status = "LOST"
                else:
                    status = "EXPIRED"
                p["status"] = status
            if status not in ("WON", "LOST", "BREAKEVEN", "EXPIRED"):
                continue
            pick_id = p.get("id", f"{p.get('strategy', '')}::{p.get('symbol', '')}::{p.get('entry_date', '')}")

            # Check if already exists
            exists = self._conn.execute(
                "SELECT 1 FROM picks WHERE id = ?", (pick_id,)
            ).fetchone()
            if exists:
                continue

            # Build extra_json from all non-core fields
            core_keys = {
                "id", "strategy", "symbol", "category", "signal_type",
                "entry_price", "entry_date", "take_profit", "stop_loss",
                "confidence", "ml_score", "exit_price", "exit_date",
                "exit_reason", "pnl_pct", "pnl_dollar", "high_water_mark",
                "status", "regime_at_entry", "atr_at_entry", "rsi_at_entry",
                "volume_ratio", "hold_days", "extra_json",
            }
            extra = {k: v for k, v in p.items() if k not in core_keys and v is not None}
            # Merge with any existing extra_json string
            if p.get("extra_json"):
                try:
                    existing_extra = json.loads(p["extra_json"]) if isinstance(p["extra_json"], str) else p["extra_json"]
                    existing_extra.update(extra)
                    extra = existing_extra
                except (json.JSONDecodeError, TypeError):
                    pass

            try:
                self._conn.execute("""
                    INSERT OR IGNORE INTO picks (
                        id, strategy, symbol, category, signal_type,
                        entry_price, entry_date, take_profit, stop_loss,
                        confidence, ml_score, exit_price, exit_date,
                        exit_reason, pnl_pct, pnl_dollar, high_water_mark,
                        status, regime_at_entry, atr_at_entry, rsi_at_entry,
                        volume_ratio, hold_days, extra_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pick_id, p.get("strategy"), p.get("symbol"),
                    p.get("category"), p.get("signal_type"),
                    p.get("entry_price"), p.get("entry_date"),
                    p.get("take_profit"), p.get("stop_loss"),
                    p.get("confidence"), p.get("ml_score"),
                    p.get("exit_price"), p.get("exit_date"),
                    p.get("exit_reason"), p.get("pnl_pct"),
                    p.get("pnl_dollar"), p.get("high_water_mark"),
                    status, p.get("regime_at_entry"),
                    p.get("atr_at_entry"), p.get("rsi_at_entry"),
                    p.get("volume_ratio"), p.get("hold_days"),
                    json.dumps(extra) if extra else None,
                ))
                imported += 1
            except Exception:
                continue

        if imported > 0:
            self._conn.commit()
        return imported

    def get_all_strategy_stats(self) -> list[dict]:
        """Get latest stats for all strategies."""
        rows = self._conn.execute("""
            SELECT * FROM strategy_stats
            WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM strategy_stats)
            ORDER BY sharpe DESC
        """).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def get_summary(self) -> dict:
        """Quick summary of database state."""
        total_signals = self._conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
        open_picks = self._conn.execute("SELECT COUNT(*) FROM picks WHERE status='OPEN'").fetchone()[0]
        closed_picks = self._conn.execute("SELECT COUNT(*) FROM picks WHERE status IN ('WON','LOST','BREAKEVEN','EXPIRED')").fetchone()[0]
        won = self._conn.execute("SELECT COUNT(*) FROM picks WHERE status='WON'").fetchone()[0]
        lost = self._conn.execute("SELECT COUNT(*) FROM picks WHERE status='LOST'").fetchone()[0]
        return {
            "total_signals": total_signals,
            "open_picks": open_picks,
            "closed_picks": closed_picks,
            "won": won, "lost": lost,
            "win_rate": round(calculate_win_rate(won, closed_picks), 4),
        }

    def close(self):
        self._conn.close()


# ---------------------------------------------------------------------------
# Module self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    store = SQLiteStore()
    print(f"Database created at: {store.db_path}")
    print(f"Summary: {store.get_summary()}")
    store.close()
