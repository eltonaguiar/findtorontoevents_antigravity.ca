"""
Incubator — Database Layer
============================
Persists incubator candidates and backtest results to:
  1. Local SQLite (alpha_engine/data/incubator.db) — always available
  2. MySQL (ejaguiar1_stocks) — the audit trail DB that powers
     https://findtorontoevents.ca/audit/

MySQL tables created:
  - at_incubator_strategies — ranked candidates with status
  - at_incubator_backtest_results — per-symbol backtest detail
  - at_large_backtest_results — full-resolution backtests (step 7)
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

INCUBATOR_DIR = Path(__file__).resolve().parent
ENGINE_DIR = INCUBATOR_DIR.parent
DATA_DIR = ENGINE_DIR / "data"
LOCAL_DB = DATA_DIR / "incubator.db"

# MySQL config — same pattern as audit_trail/mysql_client.py
MYSQL_HOST = os.environ.get("AUDIT_DB_HOST") or os.environ.get("MYSQL_HOST") or "mysql.50webs.com"
MYSQL_USER = os.environ.get("AUDIT_DB_USER") or os.environ.get("MYSQL_USER") or "ejaguiar1_stocks"
MYSQL_PASS = os.environ.get("AUDIT_DB_PASS") or os.environ.get("MYSQL_PASSWORD") or "stocks"
MYSQL_DB = os.environ.get("AUDIT_DB_NAME") or os.environ.get("MYSQL_DB") or "ejaguiar1_stocks"


class IncubatorDB:
    """Dual-write database: local SQLite + remote MySQL."""

    def __init__(self, local_path: Path = LOCAL_DB):
        self.local_path = local_path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self._sqlite = sqlite3.connect(str(local_path), check_same_thread=False)
        self._sqlite.row_factory = sqlite3.Row
        self._sqlite.execute("PRAGMA journal_mode=WAL")
        self._create_sqlite_tables()
        self._mysql_conn = None
        self._mysql_warned = False

    def _create_sqlite_tables(self):
        self._sqlite.executescript("""
        CREATE TABLE IF NOT EXISTS incubator_strategies (
            perm_id TEXT PRIMARY KEY,
            archetype TEXT NOT NULL,
            seed_strategy TEXT DEFAULT '',
            params_json TEXT NOT NULL,
            combined_sharpe REAL DEFAULT 0,
            combined_sortino REAL DEFAULT 0,
            combined_max_dd REAL DEFAULT 0,
            combined_pf REAL DEFAULT 0,
            combined_wr REAL DEFAULT 0,
            combined_trades INTEGER DEFAULT 0,
            combined_return REAL DEFAULT 0,
            composite_score REAL DEFAULT 0,
            status TEXT DEFAULT 'INCUBATOR',
            ready_for_paper INTEGER DEFAULT 0,
            rejection_reasons TEXT DEFAULT '',
            per_symbol_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS backtest_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            perm_id TEXT NOT NULL,
            archetype TEXT NOT NULL,
            symbol TEXT NOT NULL,
            params_json TEXT NOT NULL,
            total_trades INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            win_rate REAL DEFAULT 0,
            sharpe REAL DEFAULT 0,
            sortino REAL DEFAULT 0,
            max_drawdown REAL DEFAULT 0,
            profit_factor REAL DEFAULT 0,
            total_return REAL DEFAULT 0,
            avg_trade_pnl REAL DEFAULT 0,
            avg_hold_bars REAL DEFAULT 0,
            slippage_pct REAL DEFAULT 0,
            commission_pct REAL DEFAULT 0,
            backtest_type TEXT DEFAULT 'fast',
            created_at TEXT NOT NULL,
            UNIQUE(perm_id, symbol, backtest_type)
        );

        CREATE INDEX IF NOT EXISTS idx_inc_status ON incubator_strategies(status);
        CREATE INDEX IF NOT EXISTS idx_inc_score ON incubator_strategies(composite_score);
        CREATE INDEX IF NOT EXISTS idx_bt_perm ON backtest_results(perm_id);
        CREATE INDEX IF NOT EXISTS idx_bt_symbol ON backtest_results(symbol);
        """)
        self._sqlite.commit()

    # ------------------------------------------------------------------
    # MySQL connection (lazy, fire-and-forget)
    # ------------------------------------------------------------------

    def _get_mysql(self):
        """Get or create MySQL connection. Returns None if unavailable."""
        if self._mysql_conn is not None:
            try:
                self._mysql_conn.ping(reconnect=True)
                return self._mysql_conn
            except Exception:
                self._mysql_conn = None

        try:
            import pymysql
            self._mysql_conn = pymysql.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASS,
                database=MYSQL_DB,
                charset="utf8mb4",
                autocommit=True,
                connect_timeout=10,
                read_timeout=10,
                write_timeout=10,
            )
            self._ensure_mysql_tables()
            return self._mysql_conn
        except Exception as e:
            if not self._mysql_warned:
                print(f"[incubator_db] MySQL unavailable: {e} (suppressing further warnings)")
                self._mysql_warned = True
            return None

    def _ensure_mysql_tables(self):
        """Create MySQL tables if they don't exist."""
        if not self._mysql_conn:
            return
        cur = self._mysql_conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS at_incubator_strategies (
            perm_id VARCHAR(20) PRIMARY KEY,
            archetype VARCHAR(80) NOT NULL,
            seed_strategy VARCHAR(100) DEFAULT '',
            params_json JSON NOT NULL,
            combined_sharpe DECIMAL(10,4) DEFAULT 0,
            combined_sortino DECIMAL(10,4) DEFAULT 0,
            combined_max_dd DECIMAL(10,6) DEFAULT 0,
            combined_pf DECIMAL(10,4) DEFAULT 0,
            combined_wr DECIMAL(6,4) DEFAULT 0,
            combined_trades INT DEFAULT 0,
            combined_return DECIMAL(10,6) DEFAULT 0,
            composite_score DECIMAL(10,4) DEFAULT 0,
            status ENUM('INCUBATOR','PAPER_READY','PAPER_TESTING',
                        'GRADUATED','REJECTED','ARCHIVED') DEFAULT 'INCUBATOR',
            ready_for_paper TINYINT DEFAULT 0,
            rejection_reasons TEXT DEFAULT '',
            per_symbol_json JSON,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            INDEX idx_ais_status (status),
            INDEX idx_ais_score (composite_score DESC),
            INDEX idx_ais_archetype (archetype)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS at_incubator_backtest_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            perm_id VARCHAR(20) NOT NULL,
            archetype VARCHAR(80) NOT NULL,
            symbol VARCHAR(30) NOT NULL,
            params_json JSON NOT NULL,
            total_trades INT DEFAULT 0,
            wins INT DEFAULT 0,
            losses INT DEFAULT 0,
            win_rate DECIMAL(6,4) DEFAULT 0,
            sharpe DECIMAL(10,4) DEFAULT 0,
            sortino DECIMAL(10,4) DEFAULT 0,
            max_drawdown DECIMAL(10,6) DEFAULT 0,
            profit_factor DECIMAL(10,4) DEFAULT 0,
            total_return DECIMAL(10,6) DEFAULT 0,
            avg_trade_pnl DECIMAL(10,6) DEFAULT 0,
            avg_hold_bars DECIMAL(6,1) DEFAULT 0,
            slippage_pct DECIMAL(6,4) DEFAULT 0,
            commission_pct DECIMAL(6,4) DEFAULT 0,
            backtest_type ENUM('fast','full') DEFAULT 'fast',
            created_at DATETIME NOT NULL,
            UNIQUE KEY uk_perm_sym (perm_id, symbol, backtest_type),
            INDEX idx_aibr_perm (perm_id),
            INDEX idx_aibr_symbol (symbol),
            INDEX idx_aibr_sharpe (sharpe DESC)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS at_large_backtest_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            perm_id VARCHAR(20) NOT NULL,
            archetype VARCHAR(80) NOT NULL,
            symbol VARCHAR(30) NOT NULL,
            params_json JSON NOT NULL,
            total_trades INT DEFAULT 0,
            wins INT DEFAULT 0,
            losses INT DEFAULT 0,
            win_rate DECIMAL(6,4) DEFAULT 0,
            sharpe DECIMAL(10,4) DEFAULT 0,
            sortino DECIMAL(10,4) DEFAULT 0,
            max_drawdown DECIMAL(10,6) DEFAULT 0,
            profit_factor DECIMAL(10,4) DEFAULT 0,
            total_return DECIMAL(10,6) DEFAULT 0,
            avg_trade_pnl DECIMAL(10,6) DEFAULT 0,
            avg_hold_bars DECIMAL(6,1) DEFAULT 0,
            slippage_pct DECIMAL(6,4) DEFAULT 0,
            commission_pct DECIMAL(6,4) DEFAULT 0,
            equity_curve_json JSON,
            trade_log_json JSON,
            created_at DATETIME NOT NULL,
            UNIQUE KEY uk_large_perm_sym (perm_id, symbol),
            INDEX idx_albr_perm (perm_id),
            INDEX idx_albr_sharpe (sharpe DESC)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

    # ------------------------------------------------------------------
    # Write operations (dual-write: SQLite + MySQL)
    # ------------------------------------------------------------------

    def save_candidate(self, candidate: dict) -> None:
        """Save a ranked incubator candidate."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        params_json = json.dumps(candidate["params"], default=str)
        per_sym_json = json.dumps(candidate.get("per_symbol", {}), default=str)
        rejection = ", ".join(candidate.get("rejection_reasons", []))

        # SQLite
        self._sqlite.execute("""
            INSERT OR REPLACE INTO incubator_strategies (
                perm_id, archetype, seed_strategy, params_json,
                combined_sharpe, combined_sortino, combined_max_dd,
                combined_pf, combined_wr, combined_trades, combined_return,
                composite_score, status, ready_for_paper, rejection_reasons,
                per_symbol_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            candidate["perm_id"], candidate["archetype"],
            candidate.get("seed_strategy", ""), params_json,
            candidate.get("combined_sharpe", 0),
            candidate.get("combined_sortino", 0),
            candidate.get("combined_max_dd", 0),
            candidate.get("combined_pf", 0),
            candidate.get("combined_wr", 0),
            candidate.get("combined_trades", 0),
            candidate.get("combined_return", 0),
            candidate.get("composite_score", 0),
            "PAPER_READY" if candidate.get("ready_for_paper") else "INCUBATOR",
            1 if candidate.get("ready_for_paper") else 0,
            rejection, per_sym_json, now, now,
        ))
        self._sqlite.commit()

        # MySQL (fire-and-forget)
        mysql = self._get_mysql()
        if mysql:
            try:
                cur = mysql.cursor()
                cur.execute("""
                    INSERT INTO at_incubator_strategies (
                        perm_id, archetype, seed_strategy, params_json,
                        combined_sharpe, combined_sortino, combined_max_dd,
                        combined_pf, combined_wr, combined_trades, combined_return,
                        composite_score, status, ready_for_paper, rejection_reasons,
                        per_symbol_json, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        combined_sharpe=VALUES(combined_sharpe),
                        combined_sortino=VALUES(combined_sortino),
                        combined_max_dd=VALUES(combined_max_dd),
                        combined_pf=VALUES(combined_pf),
                        combined_wr=VALUES(combined_wr),
                        combined_trades=VALUES(combined_trades),
                        combined_return=VALUES(combined_return),
                        composite_score=VALUES(composite_score),
                        status=VALUES(status),
                        ready_for_paper=VALUES(ready_for_paper),
                        rejection_reasons=VALUES(rejection_reasons),
                        per_symbol_json=VALUES(per_symbol_json),
                        updated_at=VALUES(updated_at)
                """, (
                    candidate["perm_id"], candidate["archetype"],
                    candidate.get("seed_strategy", ""), params_json,
                    candidate.get("combined_sharpe", 0),
                    candidate.get("combined_sortino", 0),
                    candidate.get("combined_max_dd", 0),
                    candidate.get("combined_pf", 0),
                    candidate.get("combined_wr", 0),
                    candidate.get("combined_trades", 0),
                    candidate.get("combined_return", 0),
                    candidate.get("composite_score", 0),
                    "PAPER_READY" if candidate.get("ready_for_paper") else "INCUBATOR",
                    1 if candidate.get("ready_for_paper") else 0,
                    rejection, per_sym_json, now, now,
                ))
            except Exception as e:
                print(f"[incubator_db] MySQL write failed: {e}")

    def save_backtest_result(self, result: dict, backtest_type: str = "fast") -> None:
        """Save a single backtest result."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        params_json = json.dumps(result.get("params", {}), default=str)

        # SQLite
        self._sqlite.execute("""
            INSERT OR REPLACE INTO backtest_results (
                perm_id, archetype, symbol, params_json,
                total_trades, wins, losses, win_rate,
                sharpe, sortino, max_drawdown, profit_factor,
                total_return, avg_trade_pnl, avg_hold_bars,
                slippage_pct, commission_pct, backtest_type, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result["perm_id"], result["archetype"], result["symbol"], params_json,
            result.get("total_trades", 0), result.get("wins", 0),
            result.get("losses", 0), result.get("win_rate", 0),
            result.get("sharpe", 0), result.get("sortino", 0),
            result.get("max_drawdown", 0), result.get("profit_factor", 0),
            result.get("total_return", 0), result.get("avg_trade_pnl", 0),
            result.get("avg_hold_bars", 0), 0, 0, backtest_type, now,
        ))
        self._sqlite.commit()

        # MySQL
        mysql = self._get_mysql()
        if mysql:
            try:
                table = "at_incubator_backtest_results" if backtest_type == "fast" else "at_large_backtest_results"
                cur = mysql.cursor()
                cur.execute(f"""
                    INSERT INTO {table} (
                        perm_id, archetype, symbol, params_json,
                        total_trades, wins, losses, win_rate,
                        sharpe, sortino, max_drawdown, profit_factor,
                        total_return, avg_trade_pnl, avg_hold_bars,
                        slippage_pct, commission_pct,
                        {'backtest_type,' if backtest_type == 'fast' else ''}
                        created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                              {'%s,' if backtest_type == 'fast' else ''} %s)
                    ON DUPLICATE KEY UPDATE
                        sharpe=VALUES(sharpe), win_rate=VALUES(win_rate),
                        total_trades=VALUES(total_trades), max_drawdown=VALUES(max_drawdown),
                        profit_factor=VALUES(profit_factor), total_return=VALUES(total_return)
                """, (
                    result["perm_id"], result["archetype"], result["symbol"], params_json,
                    result.get("total_trades", 0), result.get("wins", 0),
                    result.get("losses", 0), result.get("win_rate", 0),
                    result.get("sharpe", 0), result.get("sortino", 0),
                    result.get("max_drawdown", 0), result.get("profit_factor", 0),
                    result.get("total_return", 0), result.get("avg_trade_pnl", 0),
                    result.get("avg_hold_bars", 0), 0, 0,
                    *([backtest_type] if backtest_type == "fast" else []),
                    now,
                ))
            except Exception as e:
                print(f"[incubator_db] MySQL backtest write failed: {e}")

    def save_batch(self, ranked: dict) -> int:
        """Save all candidates and their backtest results. Returns count saved."""
        count = 0
        for c in ranked.get("combined_ranking", []):
            self.save_candidate(c)
            count += 1
            # Save per-symbol backtest detail
            for sym, detail in c.get("per_symbol", {}).items():
                self.save_backtest_result(detail)

        # Also save paper-ready that aren't in combined ranking
        seen = {c["perm_id"] for c in ranked.get("combined_ranking", [])}
        for c in ranked.get("paper_ready", []):
            if c["perm_id"] not in seen:
                self.save_candidate(c)
                count += 1
                for sym, detail in c.get("per_symbol", {}).items():
                    self.save_backtest_result(detail)

        print(f"[incubator_db] Saved {count} candidates to SQLite"
              f"{' + MySQL' if self._mysql_conn else ''}")
        return count

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_incubator_strategies(self, status: str = None) -> list[dict]:
        """Get incubator strategies, optionally filtered by status."""
        query = "SELECT * FROM incubator_strategies"
        params = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY composite_score DESC"
        rows = self._sqlite.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_paper_ready(self) -> list[dict]:
        """Get strategies ready for paper trading."""
        return self.get_incubator_strategies("PAPER_READY")

    def export_paper_trading_json(self, output_path: Path = None) -> Path:
        """Export paper-ready strategies as JSON for the paper trading engine."""
        if output_path is None:
            output_path = DATA_DIR / "incubator_paper_ready.json"

        candidates = self.get_paper_ready()
        export = []
        for c in candidates:
            params = json.loads(c["params_json"]) if isinstance(c["params_json"], str) else c["params_json"]
            export.append({
                "perm_id": c["perm_id"],
                "archetype": c["archetype"],
                "seed_strategy": c.get("seed_strategy", ""),
                "params": params,
                "combined_sharpe": c["combined_sharpe"],
                "combined_max_dd": c["combined_max_dd"],
                "combined_pf": c["combined_pf"],
                "combined_wr": c["combined_wr"],
                "composite_score": c["composite_score"],
                "status": c["status"],
            })

        output_path.write_text(json.dumps(export, indent=2, default=str))
        print(f"[incubator_db] Exported {len(export)} paper-ready strategies to {output_path}")
        return output_path

    def close(self):
        self._sqlite.close()
        if self._mysql_conn:
            try:
                self._mysql_conn.close()
            except Exception:
                pass
