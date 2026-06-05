#!/usr/bin/env python3
"""ENH #119 — paper-pilot stubs for bias-survivor tournament picks (no DB writes)."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PILOT_ROOT = ROOT / "verified_strategies/paper_pilot/high_quality_2026-06-05"


def _slug(persona: str, asset_class: str, symbol: str, direction: str) -> str:
    raw = f"{persona}_{asset_class}_{symbol}_{direction}".lower()
    return re.sub(r"[^a-z0-9_]+", "_", raw).strip("_")[:80]


def _fetch_survivors() -> list[dict]:
    import pymysql
    from tools.db_env import get_stocks_creds
    from tools.mlflow_bias_detector import scrutinize_cell

    conn = pymysql.connect(**get_stocks_creds(), cursorclass=pymysql.cursors.DictCursor)
    high_quality: list[dict] = []
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT persona_id, asset_class, COUNT(*) n
                   FROM tournament_picks WHERE status IN ('WIN','LOSS') AND persona_id IS NOT NULL
                   GROUP BY persona_id, asset_class HAVING n>=15"""
            )
            cells = cur.fetchall()
        for cell in cells:
            persona = cell["persona_id"]
            ac = cell["asset_class"]
            res = scrutinize_cell(persona, ac)
            if not res or res["n"] < 15:
                continue
            if not (
                res["wr"] >= 0.55
                and res["sym_hhi"] < 0.5
                and res["fam_hhi"] < 0.5
                and res["replay_share"] < 0.25
                and res["unique_symbols"] >= 3
                and res["unique_model_families"] >= 3
            ):
                continue
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT symbol, direction, COUNT(*) n,
                              SUM(status='WIN')/COUNT(*) wr, AVG(pnl_pct) avg
                       FROM tournament_picks
                       WHERE persona_id=%s AND asset_class=%s AND status IN ('WIN','LOSS')
                       GROUP BY symbol, direction HAVING n>=5 AND wr>=0.6""",
                    (persona, ac),
                )
                for sp in cur.fetchall():
                    high_quality.append(
                        {
                            "persona": persona,
                            "asset_class": ac,
                            "symbol": sp["symbol"],
                            "direction": sp["direction"],
                            "hist_n": int(sp["n"]),
                            "hist_wr": round(float(sp["wr"]), 4),
                            "hist_avg_pnl": round(float(sp["avg"] or 0), 4),
                        }
                    )
    finally:
        conn.close()
    high_quality.sort(key=lambda h: (-h["hist_wr"], -h["hist_n"]))
    return high_quality


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=12)
    args = ap.parse_args()
    survivors = _fetch_survivors()[: args.top]
    PILOT_ROOT.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    written = []
    for pick in survivors:
        slug = _slug(pick["persona"], pick["asset_class"], pick["symbol"], pick["direction"])
        path = PILOT_ROOT / f"{slug}_state.json"
        path.write_text(
            json.dumps(
                {
                    "sleeve_id": slug,
                    "source": "high_quality_bias_survivor_2026-06-05",
                    **pick,
                    "forward_virtual": {"n_closed": 0, "promotion_ready": False, "gates": ["n<100"]},
                    "production_enable": False,
                    "started_at": now,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        written.append(slug)
    (PILOT_ROOT / "index.json").write_text(
        json.dumps({"generated_at": now, "enhancement": 119, "sleeves": written}, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(written)} stubs under {PILOT_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())