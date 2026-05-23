#!/usr/bin/env python3
"""Cross-check a system's PF/WR/n on /audit against ejaguiar1_stocks DB.

Per master-plan P0-#1 + 4-engine swarm consensus (BOTH DB and JSON
cross-check). Q2 verdict: groq=BOTH / cerebras=BOTH / xai=BOTH /
deepseek=JSON-only (overridden by 3-of-4 majority).

Use case: multi_asset_cot reports PF=19.93 / WR=87.4% / n=135 in
`dashboard_data.json::systems`. This is implausibly high; need DB
ground-truth to confirm whether the dashboard aggregator is honest
or has a payload bug.

Output:
  audit_dashboard/data/system_pf_verification.json

Usage:
  python tools/verify_system_pf.py --system multi_asset_cot
  python tools/verify_system_pf.py --all-winners
  python tools/verify_system_pf.py --pf-min 1.5 --wr-min 50

Requires DB_STOCKS_PASSWORD env var (matches audit_trail/mysql_client.py
convention). Read-only diagnostic — no writes to DB.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import pymysql
except ImportError:
    print("ERROR: pymysql not installed", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
REPORT_PATH = ROOT / "audit_dashboard" / "data" / "system_pf_verification.json"

TERMINAL_STATUSES = ("WON", "LOST", "WIN", "LOSS", "TP_HIT", "SL_HIT",
                     "EXPIRED", "closed_win", "closed_loss")

# Tolerances for verdict bucketing
PF_DELTA_OK = 0.5       # absolute PF difference
WR_DELTA_PP_OK = 3.0    # WR percentage-point difference
N_RATIO_OK = 0.15       # +/- 15% on n is acceptable (timing race)


def connect():
    pw = os.environ.get("DB_STOCKS_PASSWORD") or os.environ.get("DB_PASSWORD")
    if not pw:
        raise RuntimeError("DB_STOCKS_PASSWORD env var required")
    return pymysql.connect(
        host=os.environ.get("DB_STOCKS_HOST", "mysql.50webs.com"),
        user=os.environ.get("DB_STOCKS_USER", "ejaguiar1_stocks"),
        password=pw,
        database=os.environ.get("DB_STOCKS_NAME", "ejaguiar1_stocks"),
        port=int(os.environ.get("DB_STOCKS_PORT", "3306")),
        connect_timeout=30,
        read_timeout=60,
    )


def fetch_db_aggregates(system_name: str) -> dict | None:
    """Pull per-system PF/WR/n from trading_picks for given source_system."""
    placeholders = ",".join(["%s"] * len(TERMINAL_STATUSES))
    sql = f"""
        SELECT COUNT(*) AS n_total,
               SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) AS wins,
               SUM(CASE WHEN pnl_pct < 0 THEN 1 ELSE 0 END) AS losses,
               COALESCE(SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END), 0) AS gross_win,
               COALESCE(SUM(CASE WHEN pnl_pct < 0 THEN -pnl_pct ELSE 0 END), 0) AS gross_loss,
               COALESCE(SUM(pnl_pct), 0) AS total_pnl_pct,
               MIN(created_at) AS first_ts,
               MAX(COALESCE(closed_at, created_at)) AS last_ts
          FROM trading_picks
         WHERE source_system = %s
           AND status IN ({placeholders})
           AND pnl_pct IS NOT NULL
    """
    c = connect()
    try:
        cur = c.cursor(pymysql.cursors.DictCursor)
        cur.execute(sql, (system_name,) + TERMINAL_STATUSES)
        row = cur.fetchone() or {}
        cur.close()
    finally:
        c.close()

    if not row or not row.get("n_total"):
        return None

    n = int(row["n_total"])
    wins = int(row["wins"] or 0)
    losses = int(row["losses"] or 0)
    gross_win = float(row["gross_win"] or 0)
    gross_loss = float(row["gross_loss"] or 0)
    wr = (wins / n * 100) if n > 0 else 0.0
    pf = (gross_win / gross_loss) if gross_loss > 0 else (
        float("inf") if gross_win > 0 else 0.0
    )

    return {
        "n": n,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(wr, 2),
        "profit_factor": round(pf, 4) if pf != float("inf") else None,
        "gross_win": round(gross_win, 2),
        "gross_loss": round(gross_loss, 2),
        "total_pnl_pct": round(float(row["total_pnl_pct"] or 0), 2),
        "first_ts": str(row.get("first_ts") or ""),
        "last_ts": str(row.get("last_ts") or ""),
    }


def fetch_dashboard_aggregates(system_name: str) -> dict | None:
    """Pull per-system aggregate from dashboard_data.json::systems."""
    if not DASHBOARD.exists():
        return None
    d = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    for s in d.get("systems", []):
        if s.get("name") == system_name:
            return {
                "n": int(s.get("closed_picks") or s.get("resolved_picks") or 0),
                "wins": int(s.get("wins") or 0),
                "losses": int(s.get("losses") or 0),
                "win_rate_pct": float(s.get("win_rate") or 0),
                "profit_factor": (
                    float(s.get("profit_factor")) if s.get("profit_factor") is not None else None
                ),
                "total_pnl_pct": float(s.get("total_pnl_pct") or 0),
                "max_drawdown": float(s.get("max_drawdown") or 0),
                "last_signal_at": s.get("last_signal_at"),
                "asset_classes": s.get("asset_classes") or [],
                "toxic_concentration": s.get("toxic_concentration"),
                "toxic_symbol": s.get("toxic_symbol"),
            }
    return None


def verdict(db: dict, dash: dict) -> dict:
    """Compute verdict from DB vs dashboard aggregates."""
    pf_db = db.get("profit_factor")
    pf_dash = dash.get("profit_factor")
    wr_db = db.get("win_rate_pct")
    wr_dash = dash.get("win_rate_pct")
    n_db = db.get("n", 0)
    n_dash = dash.get("n", 0)

    pf_delta = (pf_db - pf_dash) if (pf_db is not None and pf_dash is not None) else None
    wr_delta_pp = (wr_db - wr_dash) if (wr_db is not None and wr_dash is not None) else None
    n_ratio = abs(n_db - n_dash) / max(n_db, n_dash, 1) if max(n_db, n_dash, 1) > 0 else 0

    flags = []
    if pf_delta is not None and abs(pf_delta) > PF_DELTA_OK:
        flags.append(f"PF_DIVERGENT_{pf_delta:+.2f}")
    if wr_delta_pp is not None and abs(wr_delta_pp) > WR_DELTA_PP_OK:
        flags.append(f"WR_DIVERGENT_{wr_delta_pp:+.1f}pp")
    if n_ratio > N_RATIO_OK:
        flags.append(f"N_DIVERGENT_{n_ratio*100:.1f}pct")

    if not flags:
        v = "MATCH"
    elif pf_db is not None and pf_dash is not None and pf_dash > 5.0 and pf_db < pf_dash * 0.5:
        v = "DASHBOARD_INFLATED"
    elif pf_db is not None and pf_dash is not None and pf_db > pf_dash * 2.0:
        v = "DB_INFLATED"
    else:
        v = "DIVERGENT"

    return {
        "verdict": v,
        "flags": flags,
        "pf_delta": round(pf_delta, 4) if pf_delta is not None else None,
        "wr_delta_pp": round(wr_delta_pp, 2) if wr_delta_pp is not None else None,
        "n_ratio_pct": round(n_ratio * 100, 2),
    }


def audit_system(name: str) -> dict:
    out: dict = {"system": name}
    try:
        out["db"] = fetch_db_aggregates(name)
    except Exception as exc:
        out["db_error"] = str(exc)[:200]
        out["db"] = None
    out["dashboard"] = fetch_dashboard_aggregates(name)
    if out.get("db") and out.get("dashboard"):
        out.update(verdict(out["db"], out["dashboard"]))
    elif out.get("db") is None and out.get("dashboard") is None:
        out["verdict"] = "NEITHER_FOUND"
    elif out.get("db") is None:
        out["verdict"] = "DB_MISSING"
    else:
        out["verdict"] = "DASHBOARD_MISSING"
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--system", help="Single source_system to verify")
    p.add_argument("--all-winners", action="store_true",
                   help="Verify all systems meeting PF>=pf-min + WR>=wr-min + n>=100 + MDD<=20")
    p.add_argument("--pf-min", type=float, default=1.5)
    p.add_argument("--wr-min", type=float, default=50.0)
    p.add_argument("--mdd-max", type=float, default=20.0)
    p.add_argument("--n-min", type=int, default=100)
    p.add_argument("--out", default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    out_path = Path(args.out) if args.out else REPORT_PATH

    targets: list[str] = []
    if args.system:
        targets = [args.system]
    elif args.all_winners:
        if not DASHBOARD.exists():
            print(f"ERROR: {DASHBOARD} missing", file=sys.stderr)
            sys.exit(1)
        d = json.loads(DASHBOARD.read_text(encoding="utf-8"))
        for s in d.get("systems", []):
            pf = s.get("profit_factor") or 0
            wr = s.get("win_rate") or 0
            n = s.get("closed_picks") or s.get("resolved_picks") or 0
            mdd = s.get("max_drawdown") or 999
            try:
                if (float(pf) >= args.pf_min and float(wr) >= args.wr_min
                        and int(n) >= args.n_min and float(mdd) <= args.mdd_max):
                    targets.append(s.get("name"))
            except (TypeError, ValueError):
                pass
    else:
        print("ERROR: provide --system NAME or --all-winners", file=sys.stderr)
        sys.exit(2)

    print(f"# verify_system_pf: targets={len(targets)}", file=sys.stderr)

    rows: list[dict] = []
    for name in targets:
        if not name:
            continue
        print(f"#   auditing {name} ...", file=sys.stderr)
        try:
            row = audit_system(name)
        except Exception as exc:
            row = {"system": name, "verdict": "AUDIT_ERROR", "error": str(exc)[:200]}
        rows.append(row)
        v = row.get("verdict", "?")
        db_pf = (row.get("db") or {}).get("profit_factor")
        dash_pf = (row.get("dashboard") or {}).get("profit_factor")
        print(f"    {v:24}  db_pf={db_pf}  dash_pf={dash_pf}", file=sys.stderr)

    by_verdict: dict[str, int] = {}
    for r in rows:
        v = r.get("verdict", "?")
        by_verdict[v] = by_verdict.get(v, 0) + 1

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "master-plan P0-#1 + 4-engine swarm Q2 BOTH consensus",
        "thresholds": {
            "pf_delta_ok": PF_DELTA_OK,
            "wr_delta_pp_ok": WR_DELTA_PP_OK,
            "n_ratio_ok": N_RATIO_OK,
        },
        "verdict_counts": by_verdict,
        "n_audited": len(rows),
        "rows": rows,
        "nfa": "Read-only diagnostic. Does not modify DB or production gates.",
    }

    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"# wrote {out_path} ({out_path.stat().st_size:,} bytes)", file=sys.stderr)
    print(f"# verdict counts: {by_verdict}", file=sys.stderr)


if __name__ == "__main__":
    main()
