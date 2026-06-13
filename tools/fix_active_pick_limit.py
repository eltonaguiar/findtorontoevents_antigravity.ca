#!/usr/bin/env python3
"""P2-12 active-pick-limit accounting reconciler.

The per-strategy cap enforced by production_scanner.py:918
MAX_ACTIVE_PICKS=100 (and risk_controls.py:557 PER_SYMBOL_MAX_ACTIVE=3)
counts `trading_picks` rows with status OPEN/ACTIVE. The resolver
INSERTs new rows (status=TP_HIT/SL_HIT/LOST/TIME_EXIT/WON/EXPIRED) on
close instead of UPDATing the original, so OPEN-count grows without
bound. Confirmed 2026-06-13: non_crypto_consensus 614 OPEN,
stocks_rsi2_pullback 466 OPEN, cta_commodity_momentum_term 450 OPEN.

This tool is a SAFE sidecar: READ trading_picks, WRITE
active_pick_reconciliations. --dry-run does not touch the DB.

Wiring plan: reports/p2-12_active_pick_limit_2026-06-13.md.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from typing import Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import pymysql  # noqa: E402

try:
    from tools.db_env import get_stocks_creds  # type: ignore
except Exception:  # pragma: no cover - fallback if env helper unavailable
    def get_stocks_creds() -> dict:  # type: ignore
        # NOTE: never inline a literal password here. Per
        # docs/DB_CREDENTIALS_MIGRATION_2026-06-02.md, raise if neither
        # DB_PASSWORDS_JSON nor the legacy env vars are set.
        pw = (
            os.environ.get("DB_PASS_STOCKS")
            or os.environ.get("DB_STOCKS_PASSWORD")
            or os.environ.get("MYSQL_PASSWORD")
            or os.environ.get("DB_PASSWORD")
            or os.environ.get("AUDIT_DB_PASS")
        )
        if not pw:
            raise ValueError(
                "no DB password in env — set DB_PASSWORDS_JSON (canonical) or "
                "MYSQL_PASSWORD / DB_STOCKS_PASSWORD / DB_PASS_STOCKS / "
                "DB_PASSWORD / AUDIT_DB_PASS"
            )
        return {
            "host": os.environ.get("DB_HOST", "mysql.50webs.com"),
            "port": int(os.environ.get("DB_PORT", "3306")),
            "user": os.environ.get("DB_USER", "ejaguiar1_stocks"),
            "password": pw,
            "database": os.environ.get("DB_NAME", "ejaguiar1_stocks"),
            "charset": "utf8mb4",
            "connect_timeout": 10,
        }


CLOSED_STATUSES = ("TP_HIT", "SL_HIT", "LOST", "TIME_EXIT", "WON", "EXPIRED")
ACTIVE_STATUSES = ("OPEN", "ACTIVE")
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS active_pick_reconciliations (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  strategy VARCHAR(128) NOT NULL,
  fix_count INT NOT NULL,
  ts_utc DATETIME NOT NULL,
  INDEX idx_strategy (strategy),
  INDEX idx_ts (ts_utc)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
""".strip()


class ActivePickLimitReconciler:
    """Reconciler for the active-pick accounting bug.

    The "active" count for a strategy is the number of `trading_picks` rows
    with status IN ('OPEN','ACTIVE').  When the resolver inserts a new row
    with status 'TP_HIT'/'SL_HIT'/'TIME_EXIT'/'WON'/'EXPIRED' for a pick
    that was previously OPEN, the OPEN row is NOT closed out, so the count
    of OPEN rows per strategy grows monotonically.  This reconciler
    computes the true active count (rows whose row-level lifecycle is
    OPEN) and writes an audit log of how many surplus rows it found per
    strategy.
    """

    def __init__(self, dry_run: bool = False, max_per_strategy: int = 50):
        self.dry_run = dry_run
        self.max_per_strategy = max_per_strategy
        self.creds = get_stocks_creds()
        self.ts_utc = dt.datetime.now(dt.timezone.utc).replace(microsecond=0, tzinfo=None)

    # ------------------------------------------------------------------ I/O
    def _conn(self):  # noqa: D401
        return pymysql.connect(
            host=self.creds["host"],
            port=self.creds.get("port", 3306),
            user=self.creds["user"],
            password=self.creds["password"],
            database=self.creds["database"],
            charset="utf8mb4",
            connect_timeout=10,
            autocommit=False,
        )

    def ensure_table(self) -> None:
        if self.dry_run:
            return
        with self._conn() as c:
            with c.cursor() as cur:
                cur.execute(CREATE_TABLE_SQL)
            c.commit()

    # -------------------------------------------------------------- analysis
    def _per_strategy_counts(self) -> dict[str, dict[str, int]]:
        """Return {strategy: {open_n, closed_n, active_n, total_n, over_limit_n}}."""
        with self._conn() as c:
            with c.cursor() as cur:
                placeholders = ",".join(["%s"] * len(CLOSED_STATUSES))
                sql = (
                    "SELECT strategy, status, COUNT(*) "
                    f"FROM trading_picks "
                    f"WHERE status IN ('OPEN','ACTIVE' {',' + placeholders if CLOSED_STATUSES else ''}) "
                    "GROUP BY strategy, status"
                )
                params: tuple = CLOSED_STATUSES
                cur.execute(sql, params)
                rows = cur.fetchall()
        out: dict[str, dict[str, int]] = {}
        for strat, status, n in rows:
            d = out.setdefault(strat, {"open_n": 0, "active_n": 0, "closed_n": 0, "total_n": 0})
            if status == "OPEN":
                d["open_n"] = int(n)
            elif status == "ACTIVE":
                d["active_n"] = int(n)
            else:
                d["closed_n"] += int(n)
            d["total_n"] += int(n)
        for d in out.values():
            d["lifecycle_open_n"] = d["open_n"] + d["active_n"]
            d["over_limit_n"] = max(0, d["lifecycle_open_n"] - self.max_per_strategy)
        return out

    def reconcile(self) -> dict:
        """Audit-only reconcile. Counts over-limit per strategy, writes a log row."""
        counts = self._per_strategy_counts()
        over = sorted(
            (s, d) for s, d in counts.items() if d["lifecycle_open_n"] > self.max_per_strategy
        )
        summary = {
            "ts_utc": self.ts_utc.isoformat() + "Z",
            "dry_run": self.dry_run,
            "max_per_strategy": self.max_per_strategy,
            "n_strategies": len(counts),
            "n_over_limit": len(over),
            "rows_audited": sum(d["total_n"] for d in counts.values()),
            "rows_in_lifecycle_open": sum(d["lifecycle_open_n"] for d in counts.values()),
            "top_over_limit": [
                {"strategy": s, "open_n": d["lifecycle_open_n"], "over_by": d["over_limit_n"]}
                for s, d in over[:10]
            ],
            "wrote": [],
        }
        if self.dry_run:
            return summary
        self.ensure_table()
        with self._conn() as c:
            with c.cursor() as cur:
                for s, d in over:
                    cur.execute(
                        "INSERT INTO active_pick_reconciliations (strategy, fix_count, ts_utc) "
                        "VALUES (%s, %s, %s)",
                        (s, int(d["over_limit_n"]), self.ts_utc),
                    )
                    summary["wrote"].append(
                        {"strategy": s, "fix_count": int(d["over_limit_n"])}
                    )
            c.commit()
        return summary

    def verify_limit(self, max_active_per_strategy: Optional[int] = None) -> dict:
        """Return {strategy, active_count, over_limit: bool} for each strategy."""
        cap = max_active_per_strategy or self.max_per_strategy
        counts = self._per_strategy_counts()
        return {
            "ts_utc": self.ts_utc.isoformat() + "Z",
            "max_per_strategy": cap,
            "strategies": [
                {
                    "strategy": s,
                    "active_count": d["lifecycle_open_n"],
                    "over_limit": d["lifecycle_open_n"] > cap,
                }
                for s, d in sorted(
                    counts.items(), key=lambda kv: -kv[1]["lifecycle_open_n"]
                )
            ],
        }


# ---------------------------------------------------------------------- CLI
def _emit_json(obj: dict) -> None:
    print(json.dumps(obj, indent=2, default=str))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="Do not write to DB")
    ap.add_argument("--max-per-strategy", type=int, default=50,
                    help="Per-strategy active-pick cap (default: 50)")
    ap.add_argument("--mode", choices=("reconcile", "verify"), default="reconcile",
                    help="reconcile = log fix_count; verify = return per-strategy verdict only")
    ap.add_argument("--top", type=int, default=20, help="Top-N strategies in output")
    args = ap.parse_args(argv)

    r = ActivePickLimitReconciler(dry_run=args.dry_run, max_per_strategy=args.max_per_strategy)
    if args.mode == "verify":
        out = r.verify_limit()
        out["strategies"] = out["strategies"][: args.top]
        _emit_json(out)
        return 0
    out = r.reconcile()
    if not out["top_over_limit"]:
        out["top_over_limit"] = [
            {"strategy": s, "open_n": d["lifecycle_open_n"], "over_by": d["over_limit_n"]}
            for s, d in sorted(
                r._per_strategy_counts().items(),
                key=lambda kv: -kv[1]["lifecycle_open_n"],
            )[: args.top]
        ]
    _emit_json(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
