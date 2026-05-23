#!/usr/bin/env python3
"""
Position Manager — Local SQLite-backed position & risk tracker.

Tracks all open/closed positions, computes PnL, enforces risk limits.
Works identically for paper trading and live execution.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


DB_PATH = Path(__file__).parent / "data" / "positions.db"

# ── Risk Limits ──
MAX_CONCURRENT_POSITIONS = 999    # TESTING SPRINT: was 5, uncapped
MAX_POSITION_SIZE_PCT = 2.0       # Max 2% of portfolio per trade
DAILY_LOSS_LIMIT_PCT = 3.0        # Stop trading if -3% daily
DRAWDOWN_CIRCUIT_PCT = 6.0        # Hard halt if -6% from peak
MAX_CORRELATED_POSITIONS = 999    # TESTING SPRINT: was 2, uncapped


@dataclass
class Position:
    id: int
    symbol: str
    direction: str          # LONG or SHORT
    entry_price: float
    quantity: float
    notional_usd: float
    take_profit: float
    stop_loss: float
    strategy: str
    status: str             # OPEN, CLOSED, STOPPED
    opened_at: str
    closed_at: Optional[str] = None
    exit_price: Optional[float] = None
    pnl_usd: Optional[float] = None
    pnl_pct: Optional[float] = None
    fees_paid: float = 0.0
    close_reason: Optional[str] = None  # TP_HIT, SL_HIT, MANUAL, CIRCUIT_BREAKER, TIME_EXIT


class PositionManager:
    """Manages positions and enforces risk rules."""

    def __init__(self, db_path: Path = DB_PATH, initial_balance: float = 1000.0):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initial_balance = initial_balance
        self._init_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    notional_usd REAL NOT NULL,
                    take_profit REAL,
                    stop_loss REAL,
                    strategy TEXT,
                    status TEXT DEFAULT 'OPEN',
                    opened_at TEXT NOT NULL,
                    closed_at TEXT,
                    exit_price REAL,
                    pnl_usd REAL,
                    pnl_pct REAL,
                    fees_paid REAL DEFAULT 0,
                    close_reason TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    starting_balance REAL,
                    ending_balance REAL,
                    pnl_usd REAL,
                    pnl_pct REAL,
                    trades_opened INTEGER DEFAULT 0,
                    trades_closed INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    peak_balance REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS balance_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    balance REAL NOT NULL,
                    event TEXT
                )
            """)
            # Initialize balance if empty
            row = conn.execute("SELECT COUNT(*) FROM balance_log").fetchone()
            if row[0] == 0:
                now = datetime.now(timezone.utc).isoformat()
                conn.execute(
                    "INSERT INTO balance_log (timestamp, balance, event) VALUES (?, ?, ?)",
                    (now, self.initial_balance, "INITIAL_DEPOSIT"),
                )

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def get_balance(self) -> float:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT balance FROM balance_log ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return row["balance"] if row else self.initial_balance

    def get_peak_balance(self) -> float:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT MAX(balance) as peak FROM balance_log"
            ).fetchone()
            return row["peak"] if row and row["peak"] else self.initial_balance

    def get_open_positions(self) -> List[Position]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM positions WHERE status = 'OPEN' ORDER BY opened_at DESC"
            ).fetchall()
            return [Position(**dict(r)) for r in rows]

    def get_closed_positions(self, limit: int = 100) -> List[Position]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM positions WHERE status != 'OPEN' ORDER BY closed_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [Position(**dict(r)) for r in rows]

    # ── Risk Checks ──

    def can_open_position(self, symbol: str, direction: str, size_usd: float) -> tuple[bool, str]:
        """Check all risk rules before opening a position. Returns (allowed, reason)."""
        balance = self.get_balance()
        peak = self.get_peak_balance()
        open_positions = self.get_open_positions()

        # 1. Max concurrent positions
        if len(open_positions) >= MAX_CONCURRENT_POSITIONS:
            return False, f"Max {MAX_CONCURRENT_POSITIONS} concurrent positions reached"

        # 2. Max position size
        size_pct = (size_usd / balance) * 100 if balance > 0 else 100
        if size_pct > MAX_POSITION_SIZE_PCT:
            return False, f"Position size {size_pct:.1f}% exceeds max {MAX_POSITION_SIZE_PCT}%"

        # 3. Daily loss limit
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily_pnl = self._get_daily_pnl(today)
        daily_pnl_pct = (daily_pnl / balance) * 100 if balance > 0 else 0
        if daily_pnl_pct <= -DAILY_LOSS_LIMIT_PCT:
            return False, f"Daily loss limit hit: {daily_pnl_pct:.1f}% (limit: -{DAILY_LOSS_LIMIT_PCT}%)"

        # 4. Drawdown circuit breaker
        drawdown_pct = ((peak - balance) / peak) * 100 if peak > 0 else 0
        if drawdown_pct >= DRAWDOWN_CIRCUIT_PCT:
            return False, f"Drawdown circuit breaker: {drawdown_pct:.1f}% (limit: {DRAWDOWN_CIRCUIT_PCT}%)"

        # 5. No duplicate symbol+direction
        for pos in open_positions:
            if pos.symbol == symbol and pos.direction == direction:
                return False, f"Already have {direction} position on {symbol}"

        # 6. Correlated positions check (crude: same base asset)
        base = symbol.replace("USDT", "").replace("USD", "")
        same_base = sum(1 for p in open_positions if base in p.symbol)
        if same_base >= MAX_CORRELATED_POSITIONS:
            return False, f"Max {MAX_CORRELATED_POSITIONS} correlated positions for {base}"

        return True, "OK"

    def _get_daily_pnl(self, date: str) -> float:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(pnl_usd), 0) as total FROM positions WHERE closed_at LIKE ? AND status != 'OPEN'",
                (f"{date}%",),
            ).fetchone()
            return row["total"]

    # ── Position Lifecycle ──

    def open_position(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        quantity: float,
        take_profit: float,
        stop_loss: float,
        strategy: str,
        fees: float = 0.0,
    ) -> Optional[Position]:
        """Open a new position after risk checks pass."""
        notional = entry_price * quantity
        allowed, reason = self.can_open_position(symbol, direction, notional)
        if not allowed:
            print(f"  [BLOCKED] {symbol} {direction}: {reason}")
            return None

        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            cursor = conn.execute(
                """INSERT INTO positions
                   (symbol, direction, entry_price, quantity, notional_usd,
                    take_profit, stop_loss, strategy, status, opened_at, fees_paid)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)""",
                (symbol, direction, entry_price, quantity, notional,
                 take_profit, stop_loss, strategy, now, fees),
            )
            pos_id = cursor.lastrowid

            # Deduct fees from balance
            if fees > 0:
                cur_balance = self.get_balance()
                conn.execute(
                    "INSERT INTO balance_log (timestamp, balance, event) VALUES (?, ?, ?)",
                    (now, round(cur_balance - fees, 4), f"FEE_OPEN_{symbol}"),
                )

        print(f"  [OPEN] #{pos_id} {symbol} {direction} @ {entry_price} | qty={quantity} | TP={take_profit} SL={stop_loss}")
        return self._get_position(pos_id)

    def close_position(
        self,
        position_id: int,
        exit_price: float,
        reason: str = "MANUAL",
        fees: float = 0.0,
    ) -> Optional[Position]:
        """Close a position and update balance."""
        pos = self._get_position(position_id)
        if not pos or pos.status != "OPEN":
            return None

        # Calculate PnL
        if pos.direction == "LONG":
            pnl_pct = ((exit_price - pos.entry_price) / pos.entry_price) * 100
        else:
            pnl_pct = ((pos.entry_price - exit_price) / pos.entry_price) * 100

        pnl_usd = pos.notional_usd * (pnl_pct / 100) - fees - pos.fees_paid
        now = datetime.now(timezone.utc).isoformat()

        with self._conn() as conn:
            conn.execute(
                """UPDATE positions SET
                   status='CLOSED', closed_at=?, exit_price=?,
                   pnl_usd=?, pnl_pct=?, fees_paid=fees_paid+?, close_reason=?
                   WHERE id=?""",
                (now, exit_price, round(pnl_usd, 4), round(pnl_pct, 4),
                 fees, reason, position_id),
            )

            # Update balance
            balance = self.get_balance()
            new_balance = balance + pnl_usd
            conn.execute(
                "INSERT INTO balance_log (timestamp, balance, event) VALUES (?, ?, ?)",
                (now, round(new_balance, 4), f"CLOSE_{pos.symbol}_{reason}"),
            )

        result = "WIN" if pnl_usd > 0 else "LOSS"
        print(
            f"  [CLOSE] #{position_id} {pos.symbol} {pos.direction} "
            f"@ {exit_price} | PnL: ${pnl_usd:+.2f} ({pnl_pct:+.2f}%) | {result} | {reason}"
        )
        return self._get_position(position_id)

    def _get_position(self, pos_id: int) -> Optional[Position]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM positions WHERE id = ?", (pos_id,)).fetchone()
            return Position(**dict(row)) if row else None

    # ── Reporting ──

    def get_stats(self) -> Dict:
        """Get overall trading statistics."""
        with self._conn() as conn:
            closed = conn.execute(
                "SELECT * FROM positions WHERE status != 'OPEN'"
            ).fetchall()

        if not closed:
            return {"total_trades": 0, "message": "No closed trades yet"}

        wins = [r for r in closed if (r["pnl_usd"] or 0) > 0]
        losses = [r for r in closed if (r["pnl_usd"] or 0) <= 0]
        total_pnl = sum(r["pnl_usd"] or 0 for r in closed)
        gross_wins = sum(r["pnl_usd"] or 0 for r in wins)
        gross_losses = abs(sum(r["pnl_usd"] or 0 for r in losses))

        balance = self.get_balance()
        peak = self.get_peak_balance()

        return {
            "total_trades": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else 0,
            "total_pnl_usd": round(total_pnl, 2),
            "total_pnl_pct": round((total_pnl / self.initial_balance) * 100, 2),
            "avg_win_usd": round(gross_wins / len(wins), 2) if wins else 0,
            "avg_loss_usd": round(-gross_losses / len(losses), 2) if losses else 0,
            "profit_factor": round(gross_wins / gross_losses, 2) if gross_losses > 0 else 999,
            "current_balance": round(balance, 2),
            "peak_balance": round(peak, 2),
            "drawdown_pct": round(((peak - balance) / peak) * 100, 2) if peak > 0 else 0,
            "open_positions": len(self.get_open_positions()),
        }

    def print_dashboard(self):
        """Print a trading dashboard summary."""
        stats = self.get_stats()
        open_pos = self.get_open_positions()

        print(f"\n{'='*60}")
        print(f"  TRADING DASHBOARD")
        print(f"{'='*60}")
        print(f"  Balance:     ${stats.get('current_balance', 0):,.2f}")
        print(f"  Peak:        ${stats.get('peak_balance', 0):,.2f}")
        print(f"  Drawdown:    {stats.get('drawdown_pct', 0):.1f}%")
        print(f"  Total PnL:   ${stats.get('total_pnl_usd', 0):+,.2f} ({stats.get('total_pnl_pct', 0):+.1f}%)")
        print(f"  Trades:      {stats.get('total_trades', 0)} ({stats.get('wins', 0)}W / {stats.get('losses', 0)}L)")
        print(f"  Win Rate:    {stats.get('win_rate', 0):.1f}%")
        print(f"  Profit Factor: {stats.get('profit_factor', 0):.2f}")

        if open_pos:
            print(f"\n  Open Positions ({len(open_pos)}):")
            for p in open_pos:
                print(f"    #{p.id} {p.symbol} {p.direction} @ {p.entry_price} | TP={p.take_profit} SL={p.stop_loss}")

        print(f"{'='*60}\n")


if __name__ == "__main__":
    pm = PositionManager(initial_balance=1000.0)
    pm.print_dashboard()
