#!/usr/bin/env python3
"""Aggregate bootstrap-approved forward paper pilots (B_flip, inverse_ml BTC)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "reports" / "bootstrap_forward_stats_latest.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PILOT_DIR = ROOT / "verified_strategies" / "paper_pilot"

LAB = {
    "B_flip_PriceRocMeanReversion": {
        "verdict": "BOOTSTRAP_PASS",
        "is_pf": 35.91,
        "is_n": 157,
        "pf_lo_95": 21.21,
        "note": "PR #482 legit — forward virtual only",
    },
    "inverse_ml_enhanced_BTCUSDT_15m_D": {
        "verdict": "BOOTSTRAP_PASS",
        "is_pf": 34.46,
        "is_n": 65,
        "pf_lo_95": 15.97,
        "note": "PR #482 legit — forward virtual only",
    },
}


def _load_state(name: str) -> dict:
    path = PILOT_DIR / name
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _db_forward_stats(strategy_id: str) -> dict | None:
    """Fetch real forward stats from trading_picks (post INCIDENT #94 backfill).
    Returns None if pymysql/credentials unavailable so the workflow
    falls back to the state.json source cleanly.
    """
    try:
        import os
        import pymysql
        conn = pymysql.connect(
            host=os.environ.get("DB_HOST", "mysql.50webs.com"),
            user=os.environ.get("DB_USER_STOCKS", "ejaguiar1_stocks"),
            password=os.environ.get("DB_PASS_STOCKS", "stocks1234560"),
            database=os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks"),
            connect_timeout=10,
        )
        with conn.cursor() as cur:
            cur.execute(
                """SELECT
                     COUNT(*) AS n,
                     SUM(pnl_pct>0) AS wins,
                     SUM(CASE WHEN pnl_pct>0 THEN pnl_pct ELSE 0 END) AS gross_w,
                     SUM(CASE WHEN pnl_pct<=0 THEN pnl_pct ELSE 0 END) AS gross_l,
                     AVG(pnl_pct) AS avg
                   FROM trading_picks
                   WHERE strategy=%s AND pnl_pct IS NOT NULL AND pnl_pct!=0
                     AND status IN ('TP_HIT','SL_HIT','LOST','TIME_EXIT')""",
                (strategy_id,),
            )
            n, wins, gw, gl, avg = cur.fetchone()
        conn.close()
        if not n:
            return None
        # MySQL returns Decimal for SUM/AVG; cast everything to float.
        n_i = int(n)
        wins_f = float(wins or 0)
        gw_f = float(gw or 0.0)
        gl_f = float(gl or 0.0)
        avg_f = float(avg or 0.0)
        wr = wins_f / n_i if n_i else 0.0
        pf = gw_f / abs(gl_f) if gl_f else 0.0
        return {
            "source": "trading_picks_db_post_incident94",
            "strategy_id": strategy_id,
            "n_closed": n_i,
            "wr": round(wr, 4),
            "pf": round(pf, 4),
            "mean_pnl_pct": round(avg_f, 4),
            "promotion_ready": n_i >= 100 and pf >= 1.5 and wr >= 0.5,
        }
    except Exception:
        return None


def build_report() -> dict:
    b_flip = _load_state("b_flip_price_roc_state.json")
    inv = _load_state("inverse_ml_btc_state.json")
    # Prefer DB-sourced forward stats (post INCIDENT #94 backfill); fall back to
    # state.json virtual ticks if DB unreachable. The state.json source was
    # n=2/n=3 frozen because TIME_EXIT pnl=0 bug hid 99.9% of closures
    # (fixed at commit c7cfa69b2d, backfilled at commit 575b5b6153).
    b_flip_db = _db_forward_stats("B_flip_PriceRocMeanReversion")
    inv_db = _db_forward_stats("inverse_ml_enhanced_BTCUSDT_15m_D")
    sleeves = {
        "b_flip_price_roc": {
            "lab_bootstrap": LAB["B_flip_PriceRocMeanReversion"],
            "forward": b_flip_db or b_flip.get("forward") or {"error": "no_tick_yet"},
            "forward_state_json": b_flip.get("forward"),
            "open_position": b_flip.get("open_position"),
            "recommend_enable": False,
            "flag": "B_FLIP_PRICEROC_ENABLED",
        },
        "inverse_ml_btc_15m": {
            "lab_bootstrap": LAB["inverse_ml_enhanced_BTCUSDT_15m_D"],
            "forward": inv_db or inv.get("forward") or {"error": "no_tick_yet"},
            "forward_state_json": inv.get("forward"),
            "open_position": inv.get("open_position"),
            "recommend_enable": False,
            "flag": "INVERSE_ML_BTC_15M_ENABLED",
        },
    }
    any_ready = any(
        (s.get("forward") or {}).get("promotion_ready") for s in sleeves.values()
    )
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "forward_n_target": 100,
        "any_promotion_ready": any_ready,
        "sleeves": sleeves,
        "blocked_from_production": [
            "money_ready_verdict freeze_promotions",
            "no scanner env flags until forward n>=100",
        ],
        "refs": ["updates/2026-06-02-suspicious-pass-investigation.md", "PR #482"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    report = build_report()
    print(json.dumps(report, indent=2))
    if args.write:
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        audit = ROOT / "audit_dashboard" / "data" / "bootstrap_forward_stats.json"
        audit.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote {OUT_PATH}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())