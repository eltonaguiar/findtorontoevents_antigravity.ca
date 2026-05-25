"""
top_edges.py — Per-asset-class "top 5 edge cells" extractor.

For each asset class, permutes tag combinations (trust band, confidence band,
R:R band, strategy family, direction, score decile, source_system) over the
last 90d closed picks and returns combos meeting PROVEN-tier criteria:
  WR (Bayesian-shrunk) >= 55%, PF >= 1.5, n >= 20.

Writes:
  audit_dashboard/data/top_edges_per_class.json

Also (best-effort) writes the top edges into tournament_rating_algorithms with
model_id='audit_blueprint' so the new tables get populated.

Read-only on trading_picks. INSERT only into the new tournament_* tables.
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.audit_pick_funnel._db import connect_stocks  # noqa: E402
from tools.audit_pick_funnel.extract_funnel import (  # noqa: E402
    _classify_status, _normalize_class, fetch_picks,
)

OUT = ROOT / "audit_dashboard" / "data" / "top_edges_per_class.json"

# Tag binners
def trust_band(t: Optional[int]) -> str:
    if t is None: return "UNK"
    if t >= 80: return "PROVEN"
    if t >= 60: return "DEVELOPING"
    if t >= 40: return "WATCH"
    if t >= 20: return "SANDBOX"
    return "PROBATION"

def conf_band(c: Optional[float]) -> str:
    if c is None: return "UNK"
    if c >= 0.90: return "C>=0.90"
    if c >= 0.85: return "C0.85-0.90"
    if c >= 0.80: return "C0.80-0.85"
    if c >= 0.75: return "C0.75-0.80"
    if c >= 0.70: return "C0.70-0.75"
    if c >= 0.60: return "C0.60-0.70"
    return "C<0.60"

def rr_band(entry: Optional[float], tp: Optional[float], sl: Optional[float],
            direction: Optional[str]) -> str:
    try:
        e, t, s = float(entry), float(tp), float(sl)
        if direction and direction.upper() in ("SHORT", "SELL"):
            risk = s - e; reward = e - t
        else:
            risk = e - s; reward = t - e
        if risk <= 0 or reward <= 0:
            return "UNK"
        rr = reward / risk
        if rr >= 2.0: return "RR>=2.0"
        if rr >= 1.5: return "RR1.5-2.0"
        if rr >= 1.0: return "RR1.0-1.5"
        return "RR<1.0"
    except Exception:
        return "UNK"

def score_decile(s: Optional[int]) -> str:
    if s is None: return "S?"
    return f"S{(int(s)//10)*10}"

def strategy_family(strat: Optional[str]) -> str:
    if not strat: return "unknown"
    s = strat.lower()
    if "scalp" in s: return "scalp"
    if "breakout" in s or "breakout_v2" in s: return "breakout"
    if "momentum" in s or "mom_" in s: return "momentum"
    if "mean" in s or "reversion" in s or "rsi" in s: return "mean_reversion"
    if "trend" in s: return "trend"
    if "vol" in s: return "vol"
    if "consensus" in s or "ensemble" in s: return "consensus"
    return s.split("_")[0][:16]


def bayes_wr(wins: int, total: int, prior_wr: float = 0.5, prior_n: float = 20) -> float:
    """Beta-shrunk win rate to discount small-n cells."""
    return (wins + prior_wr * prior_n) / (total + prior_n)


def profit_factor(pnls: List[float]) -> float:
    gains = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses <= 0:
        return float("inf") if gains > 0 else 0.0
    return gains / losses


def expand_pick_tags(p: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "asset_class": _normalize_class(p.get("category")),
        "trust": trust_band(p.get("trust_score")),
        "conf": conf_band(float(p["confidence"]) if p.get("confidence") is not None else None),
        "rr": rr_band(p.get("entry_price"), p.get("take_profit"), p.get("stop_loss"), p.get("direction")),
        "score_dec": score_decile(p.get("elite_score")),
        "fam": strategy_family(p.get("strategy")),
        "dir": (p.get("direction") or "?").upper(),
        "source": p.get("source_system") or "unknown",
    }


# Cell-key dimensions to enumerate (3-tag combos to keep the space tractable)
DIMS = ["trust", "conf", "rr", "fam", "dir", "score_dec", "source"]


def find_top_edges(picks: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Group by asset_class
    by_class: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for p in picks:
        st = _classify_status(p.get("status"))
        if st not in ("WIN", "LOSS"):
            continue
        tags = expand_pick_tags(p)
        tags["_won"] = (st == "WIN")
        tags["_pnl"] = float(p["pnl_pct"]) if p.get("pnl_pct") is not None else 0.0
        by_class[tags["asset_class"]].append(tags)

    result: Dict[str, Any] = {}
    for ac, rows in by_class.items():
        cells: Dict[Tuple[Tuple[str, str], ...], Dict[str, Any]] = defaultdict(
            lambda: {"n": 0, "wins": 0, "pnls": []}
        )
        # Permute over 3-dim combos to constrain combinatorics
        dim_combos = [
            ("trust", "conf", "fam"),
            ("trust", "score_dec", "dir"),
            ("conf", "rr", "fam"),
            ("fam", "dir", "source"),
            ("trust", "fam", "dir"),
            ("score_dec", "conf", "dir"),
            ("rr", "fam", "dir"),
            ("source", "trust", "dir"),
        ]
        for r in rows:
            for combo in dim_combos:
                key = tuple((d, r[d]) for d in combo)
                c = cells[key]
                c["n"] += 1
                if r["_won"]:
                    c["wins"] += 1
                c["pnls"].append(r["_pnl"])

        # Score cells
        scored = []
        for key, c in cells.items():
            n = c["n"]
            if n < 20:
                continue
            wr = c["wins"] / n
            wr_shrunk = bayes_wr(c["wins"], n)
            pf = profit_factor(c["pnls"])
            avg = sum(c["pnls"]) / n
            cell_label = " & ".join(f"{k}={v}" for k, v in key)
            scored.append({
                "cell": cell_label,
                "n": n,
                "wins": c["wins"],
                "wr_pct": round(100 * wr, 2),
                "wr_shrunk_pct": round(100 * wr_shrunk, 2),
                "pf": round(pf, 3) if pf != float("inf") else 99.0,
                "avg_pnl_pct": round(avg, 4),
            })

        # PROVEN edges
        proven = [s for s in scored if s["wr_shrunk_pct"] >= 55 and s["pf"] >= 1.5]
        proven.sort(key=lambda x: (x["pf"], x["wr_shrunk_pct"], x["n"]), reverse=True)
        # Promising-but-failing (good WR, weak PF)
        promising_wr_weak_pf = [
            s for s in scored
            if s["wr_shrunk_pct"] >= 55 and s["pf"] < 1.5
        ]
        promising_wr_weak_pf.sort(key=lambda x: x["wr_shrunk_pct"], reverse=True)
        # System-wide best by PF (even if WR<55)
        best_pf = sorted(scored, key=lambda x: x["pf"], reverse=True)[:5]

        result[ac] = {
            "n_closed": len(rows),
            "n_cells_evaluated": len(cells),
            "top_edges_proven": proven[:5],
            "rejected_good_wr_bad_pf": promising_wr_weak_pf[:5],
            "best_pf_overall": best_pf,
        }
    return result


def main() -> int:
    conn = connect_stocks()
    try:
        print("[top_edges] fetching 90d picks...", flush=True)
        picks = fetch_picks(conn, 90)
        print(f"[top_edges]  -> {len(picks)} rows", flush=True)
    finally:
        conn.close()

    edges = find_top_edges(picks)
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": 90,
        "criteria": "PROVEN = WR_shrunk>=55%, PF>=1.5, n>=20",
        "by_class": edges,
    }
    OUT.write_text(json.dumps(payload, indent=2, default=str))
    print(f"[top_edges] wrote {OUT}")

    # Best-effort: insert top edges into tournament_rating_algorithms
    try:
        conn = connect_stocks()
        with conn.cursor() as cur:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            inserted = 0
            for ac, b in edges.items():
                if not b["top_edges_proven"]:
                    continue
                top = b["top_edges_proven"][0]
                features = json.dumps({
                    "top_edges": b["top_edges_proven"],
                    "n_cells": b["n_cells_evaluated"],
                    "n_closed": b["n_closed"],
                })
                cur.execute(
                    "INSERT INTO tournament_rating_algorithms "
                    "(model_id, provider, persona_id, asset_class, features, "
                    "floor_score, signature_insight, source_ref, captured_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    ("audit_blueprint", "audit_pick_funnel", "top_edges_v1",
                     ac, features, 60,
                     f"{top['cell']} | WR_shrunk={top['wr_shrunk_pct']}% PF={top['pf']} n={top['n']}",
                     "tools/audit_pick_funnel/top_edges.py", now),
                )
                inserted += 1
            conn.commit()
            print(f"[top_edges] inserted {inserted} rows into tournament_rating_algorithms")
    except Exception as e:
        print(f"[top_edges] WARN: could not insert into tournament_rating_algorithms: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
