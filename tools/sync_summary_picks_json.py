#!/usr/bin/env python3
"""Build audit_dashboard/data/summary_picks.json from real pick timestamps."""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "audit_dashboard" / "data" / "summary_picks.json"
RESOLVED = frozenset({"WON", "LOST", "CLOSED", "EXPIRED", "TP_HIT", "SL_HIT", "STOPPED", "TARGET_HIT"})


def _norm_class(raw: str) -> str:
    ac = (raw or "").strip().upper()
    if ac in ("MEMECOIN", "PENNY", "PENNYSTOCK"):
        return "PENNY_STOCK"
    return ac or "UNKNOWN"


def _pick_ts(pick: dict) -> str:
    for k in ("created_at", "timestamp", "closed_at", "entry_time", "signal_time", "opened_at"):
        v = pick.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def _from_mysql() -> dict | None:
    try:
        import pymysql
    except ImportError:
        return None
    password = os.environ.get("DB_STOCKS_PASSWORD") or os.environ.get("DB_PASS_STOCKS") or ""
    if not password:
        return None
    try:
        conn = pymysql.connect(
            host=os.environ.get("DB_STOCKS_HOST", "mysql.50webs.com"),
            port=int(os.environ.get("DB_STOCKS_PORT", "3306")),
            user=os.environ.get("DB_STOCKS_USER", "ejaguiar1_stocks"),
            password=password,
            database=os.environ.get("DB_STOCKS_NAME", "ejaguiar1_stocks"),
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
    except Exception:
        return None
    stats: dict[str, dict] = defaultdict(lambda: {
        "total_picks": 0, "resolved": 0, "wins": 0, "losses": 0,
        "pnl_sum": 0.0, "pnl_n": 0, "last_pick": "",
    })
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT category,
                   COUNT(*) AS total_picks,
                   SUM(CASE WHEN status IN ('WON','LOST','CLOSED','EXPIRED','TP_HIT','SL_HIT') THEN 1 ELSE 0 END) AS resolved,
                   SUM(CASE WHEN status = 'WON' OR (pnl_pct IS NOT NULL AND pnl_pct > 0 AND status NOT IN ('LOST','ACTIVE','OPEN')) THEN 1 ELSE 0 END) AS wins,
                   SUM(CASE WHEN status = 'LOST' OR (pnl_pct IS NOT NULL AND pnl_pct < 0) THEN 1 ELSE 0 END) AS losses,
                   AVG(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct ELSE NULL END) AS avg_pnl_pct,
                   MAX(COALESCE(created_at, updated_at)) AS last_pick
            FROM trading_picks
            WHERE category IS NOT NULL AND category != ''
            GROUP BY category
            """
        )
        for row in cur.fetchall():
            ac = _norm_class(row["category"])
            s = stats[ac]
            s["total_picks"] = int(row["total_picks"] or 0)
            s["resolved"] = int(row["resolved"] or 0)
            s["wins"] = int(row["wins"] or 0)
            s["losses"] = int(row["losses"] or 0)
            if row["avg_pnl_pct"] is not None:
                s["pnl_sum"] = float(row["avg_pnl_pct"])
                s["pnl_n"] = 1
            lp = row.get("last_pick")
            if lp is not None:
                s["last_pick"] = lp.isoformat() if hasattr(lp, "isoformat") else str(lp)
    finally:
        conn.close()
    return _format_payload(stats, source="mysql.trading_picks")


def _load_json_picks(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, list):
        return [p for p in data if isinstance(p, dict)]
    if isinstance(data, dict):
        for key in ("picks", "active_picks", "closed_picks", "signals"):
            if isinstance(data.get(key), list):
                return [p for p in data[key] if isinstance(p, dict)]
    return []


def _from_local_json() -> dict:
    stats: dict[str, dict] = defaultdict(lambda: {
        "total_picks": 0, "resolved": 0, "wins": 0, "losses": 0,
        "pnl_sum": 0.0, "pnl_n": 0, "last_pick": "",
    })
    paths = [
        ROOT / "alpha_engine" / "data" / "closed_picks.json",
        ROOT / "alpha_engine" / "data" / "active_picks.json",
    ]
    seen: set[str] = set()
    for path in paths:
        for pick in _load_json_picks(path):
            dedupe = str(pick.get("id") or pick.get("dedup_key") or f"{pick.get('symbol')}|{_pick_ts(pick)}")
            if dedupe in seen:
                continue
            seen.add(dedupe)
            ac = _norm_class(str(pick.get("asset_class") or pick.get("category") or ""))
            if ac == "UNKNOWN":
                continue
            s = stats[ac]
            s["total_picks"] += 1
            st = str(pick.get("status") or "").upper()
            pnl = pick.get("pnl_pct")
            if st in RESOLVED or pnl is not None:
                s["resolved"] += 1
                if pnl is not None:
                    try:
                        pnl_f = float(pnl)
                        s["pnl_sum"] += pnl_f
                        s["pnl_n"] += 1
                        if pnl_f > 0 or st == "WON":
                            s["wins"] += 1
                        elif pnl_f < 0 or st == "LOST":
                            s["losses"] += 1
                    except (TypeError, ValueError):
                        pass
            ts = _pick_ts(pick)
            if ts and (not s["last_pick"] or ts > s["last_pick"]):
                s["last_pick"] = ts
    return _format_payload(stats, source="local_json")


def _format_payload(stats: dict, source: str) -> dict:
    classes = []
    for ac in sorted(stats.keys()):
        s = stats[ac]
        resolved = s["resolved"]
        wins = s["wins"]
        classes.append({
            "asset_class": ac,
            "total_picks": s["total_picks"],
            "resolved": resolved,
            "wins": wins,
            "losses": s["losses"],
            "win_rate_pct": round(100.0 * wins / resolved, 1) if resolved else None,
            "avg_pnl_pct": round(s["pnl_sum"] / s["pnl_n"], 2) if s["pnl_n"] else None,
            "last_pick": s["last_pick"] or None,
        })
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "n_picks_total": sum(c["total_picks"] for c in classes),
        "n_resolved": sum(c["resolved"] for c in classes),
        "n_asset_classes": len(classes),
        "asset_classes": classes,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    payload = _from_mysql() or _from_local_json()
    text = json.dumps(payload, indent=2)
    if args.dry_run:
        print(text)
        return 0
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    print(f"Wrote {out} ({payload['n_asset_classes']} classes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
