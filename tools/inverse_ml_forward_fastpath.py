#!/usr/bin/env python3
"""Fast-path status + backfill for inverse_ml CRYPTO sleeves (n→100).

Surfaces decisive forward n from trading_picks, NULL-pnl backlog, and
closes remaining to target. Does not enable production capital.

Usage:
  python3 tools/inverse_ml_forward_fastpath.py
  python3 tools/inverse_ml_forward_fastpath.py --strategy inverse_ml_enhanced_BTCUSDT_15m_D
  python3 tools/inverse_ml_forward_fastpath.py --backfill-dry-run
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TARGET_N = 100
DEFAULT_STRATEGY = "inverse_ml_enhanced_BTCUSDT_15m_D"
SLEEVE_STRATEGIES = (
    "inverse_ml_enhanced_BTCUSDT_15m_D",
    "inverse_ml_enhanced_ADAUSDT_15m_D",
)

DECISIVE_STATUSES = ("TP_HIT", "SL_HIT", "LOST", "TIME_EXIT", "EXPIRED", "WON", "WIN", "LOSS")


def _connect():
    import pymysql
    from tools.db_env import get_stocks_creds

    return pymysql.connect(**get_stocks_creds(), cursorclass=pymysql.cursors.DictCursor)


def _stats(strategy: str) -> dict:
    status_in = ",".join(f"'{s}'" for s in DECISIVE_STATUSES)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                  COUNT(*) AS resolved_total,
                  SUM(pnl_pct IS NOT NULL AND ABS(COALESCE(pnl_pct, 0)) >= 0.0001) AS decisive_n,
                  SUM(pnl_pct IS NULL OR ABS(COALESCE(pnl_pct, 0)) < 0.0001) AS null_or_zero_pnl,
                  SUM(status IN ('OPEN','ACTIVE')) AS open_n
                FROM trading_picks
                WHERE strategy = %s AND closed_at IS NOT NULL
                  AND status IN ({status_in})
                """,
                (strategy,),
            )
            row = cur.fetchone() or {}
            cur.execute(
                f"""
                SELECT
                  COUNT(*) AS n,
                  SUM(pnl_pct > 0) AS wins,
                  SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END) AS gross_w,
                  SUM(CASE WHEN pnl_pct <= 0 THEN pnl_pct ELSE 0 END) AS gross_l,
                  AVG(pnl_pct) AS avg
                FROM trading_picks
                WHERE strategy = %s
                  AND pnl_pct IS NOT NULL AND ABS(pnl_pct) >= 0.0001
                  AND status IN ('TP_HIT','SL_HIT','LOST','TIME_EXIT')
                """,
                (strategy,),
            )
            fwd = cur.fetchone() or {}
    finally:
        conn.close()

    n = int(fwd.get("n") or 0)
    gw = float(fwd.get("gross_w") or 0)
    gl = float(fwd.get("gross_l") or 0)
    wins = float(fwd.get("wins") or 0)
    return {
        "strategy": strategy,
        "resolved_total": int(row.get("resolved_total") or 0),
        "decisive_n": int(row.get("decisive_n") or 0),
        "null_or_zero_pnl": int(row.get("null_or_zero_pnl") or 0),
        "open_n": int(row.get("open_n") or 0),
        "forward_n": n,
        "wr": round(wins / n, 4) if n else 0.0,
        "pf": round(gw / abs(gl), 4) if gl else 0.0,
        "mean_pnl_pct": round(float(fwd.get("avg") or 0), 4),
        "n_remaining": max(0, TARGET_N - n),
        "at_target": n >= TARGET_N,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strategy", default=DEFAULT_STRATEGY)
    ap.add_argument("--all-sleeves", action="store_true")
    ap.add_argument("--backfill-dry-run", action="store_true")
    args = ap.parse_args()

    strategies = list(SLEEVE_STRATEGIES) if args.all_sleeves else [args.strategy]
    rows = []
    for strat in strategies:
        try:
            rows.append(_stats(strat))
        except Exception as exc:
            print(f"[fastpath] WARN: could not query {strat}: {exc}", file=sys.stderr)

    if not rows:
        print("[fastpath] No DB stats (check pymysql + DB creds)")
        return 1

    for r in rows:
        print(
            f"{r['strategy']}: forward_n={r['forward_n']}/{TARGET_N} "
            f"(need {r['n_remaining']}) | resolved={r['resolved_total']} "
            f"null_pnl={r['null_or_zero_pnl']} open={r['open_n']} "
            f"pf={r['pf']} wr={r['wr']}"
        )

    primary = rows[0]
    if primary["null_or_zero_pnl"]:
        print(
            f"\n[fastpath] Backfill {primary['null_or_zero_pnl']} NULL/zero-pnl rows first:"
        )
        print(
            f"  python3 tools/backfill_resolved_pnl.py --dry-run "
            f"--strategy {primary['strategy']}"
        )
        print(
            f"  python3 tools/backfill_resolved_pnl.py --apply "
            f"--strategy {primary['strategy']}"
        )

    if args.backfill_dry_run:
        cmd = [
            sys.executable,
            str(ROOT / "tools/backfill_resolved_pnl.py"),
            "--dry-run",
            "--strategy",
            primary["strategy"],
        ]
        print("\n[fastpath] running:", " ".join(cmd))
        subprocess.run(cmd, check=False)

    print("\n[fastpath] Enable sleeve-only CRYPTO mode:")
    print("  export INVERSE_ML_BTC_15M_ENABLED=1")
    print("  python3 alpha_engine/mysql_trading_sync.py --dry-run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())