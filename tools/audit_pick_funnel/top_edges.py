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
from itertools import combinations, product
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


# Cell-key dimensions to enumerate (all C(7,3) + C(7,4) combos = 70 total)
DIMS = ["trust", "conf", "rr", "fam", "dir", "score_dec", "source"]
DIM_COMBOS: List[Tuple[str, ...]] = (
    [tuple(c) for c in combinations(DIMS, 3)] +
    [tuple(c) for c in combinations(DIMS, 4)]
)

# Caps to keep the per-class memory bounded
TOP_CELLS_PER_CLASS = 200  # rank by n desc, then score only the top N
MIN_N = 20
HOLDOUT_PF_FLOOR = 1.2     # both halves must clear this PF for holdout_pass


def _score_cell(wins: int, n: int, pnls: List[float]) -> Dict[str, Any]:
    wr = wins / n if n else 0.0
    wr_shrunk = bayes_wr(wins, n) if n else 0.0
    pf = profit_factor(pnls)
    avg = sum(pnls) / n if n else 0.0
    return {
        "n": n,
        "wins": wins,
        "wr_pct": round(100 * wr, 2),
        "wr_shrunk_pct": round(100 * wr_shrunk, 2),
        "pf": round(pf, 3) if pf != float("inf") else 99.0,
        "avg_pnl_pct": round(avg, 4),
    }


def find_top_edges(picks: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], int]:
    """Returns (per-class results, total cells evaluated across all classes)."""
    # Group by asset_class, attach an ordering timestamp for holdout split
    by_class: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for p in picks:
        st = _classify_status(p.get("status"))
        if st not in ("WIN", "LOSS"):
            continue
        tags = expand_pick_tags(p)
        tags["_won"] = (st == "WIN")
        tags["_pnl"] = float(p["pnl_pct"]) if p.get("pnl_pct") is not None else 0.0
        # Time-ordering key: prefer closed_at, fall back to created_at
        t = p.get("closed_at") or p.get("created_at")
        tags["_ts"] = t if t is not None else ""
        by_class[tags["asset_class"]].append(tags)

    result: Dict[str, Any] = {}
    total_cells = 0

    for ac, rows in by_class.items():
        # Sort chronologically for the holdout split
        rows_sorted = sorted(rows, key=lambda r: str(r["_ts"]))
        split_idx = int(len(rows_sorted) * 0.6)
        train_set_ids = set(id(r) for r in rows_sorted[:split_idx])

        cells: Dict[Tuple[Tuple[str, str], ...], Dict[str, Any]] = defaultdict(
            lambda: {
                "n": 0, "wins": 0, "pnls": [],
                "n_tr": 0, "wins_tr": 0, "pnls_tr": [],
                "n_ho": 0, "wins_ho": 0, "pnls_ho": [],
            }
        )
        for r in rows_sorted:
            in_train = id(r) in train_set_ids
            for combo in DIM_COMBOS:
                key = (combo, tuple(r[d] for d in combo))
                c = cells[key]
                c["n"] += 1
                if r["_won"]:
                    c["wins"] += 1
                c["pnls"].append(r["_pnl"])
                if in_train:
                    c["n_tr"] += 1
                    if r["_won"]:
                        c["wins_tr"] += 1
                    c["pnls_tr"].append(r["_pnl"])
                else:
                    c["n_ho"] += 1
                    if r["_won"]:
                        c["wins_ho"] += 1
                    c["pnls_ho"].append(r["_pnl"])

        # Memory cap: keep top-N cells by n
        sized = [(key, c) for key, c in cells.items() if c["n"] >= MIN_N]
        sized.sort(key=lambda kv: kv[1]["n"], reverse=True)
        sized = sized[:TOP_CELLS_PER_CLASS]
        n_cells_eval = len(sized)
        total_cells += n_cells_eval

        scored = []
        for key, c in sized:
            combo, values = key
            base = _score_cell(c["wins"], c["n"], c["pnls"])
            tr = _score_cell(c["wins_tr"], c["n_tr"], c["pnls_tr"])
            ho = _score_cell(c["wins_ho"], c["n_ho"], c["pnls_ho"])
            holdout_pass = (
                c["n_tr"] >= 10 and c["n_ho"] >= 10
                and tr["pf"] >= HOLDOUT_PF_FLOOR
                and ho["pf"] >= HOLDOUT_PF_FLOOR
            )
            cell_label = " & ".join(f"{k}={v}" for k, v in zip(combo, values))
            scored.append({
                "cell": cell_label,
                "dims": list(combo),
                **base,
                "train_pf": tr["pf"],
                "train_n": tr["n"],
                "holdout_pf": ho["pf"],
                "holdout_n": ho["n"],
                "holdout_pass": holdout_pass,
            })

        result[ac] = {
            "n_closed": len(rows),
            "n_cells_evaluated": n_cells_eval,
            "_scored": scored,  # temp, stripped below after multi-test correction
        }

    # Multiple-testing correction: Bonferroni alpha=0.05 across ALL cells across ALL classes
    bonf_alpha = 0.05 / max(total_cells, 1)
    # Approximate: for WR_shrunk >= 55% & n >= 20, one-sided binomial p-value under H0 (wr=0.5)
    # Use normal approximation: z = (p_hat - 0.5) / sqrt(0.25/n). Cell passes Bonferroni if 1-Phi(z) < bonf_alpha
    # Threshold z* = inverse Normal CDF at (1 - bonf_alpha)
    try:
        from statistics import NormalDist
        z_star = NormalDist().inv_cdf(1.0 - bonf_alpha)
    except Exception:
        z_star = 5.0

    final: Dict[str, Any] = {}
    for ac, b in result.items():
        scored = b.pop("_scored")
        for s in scored:
            n = s["n"]
            p_hat = s["wr_pct"] / 100.0
            z = (p_hat - 0.5) / (0.25 / max(n, 1)) ** 0.5 if n > 0 else 0.0
            s["wr_z"] = round(z, 3)
            s["bonferroni_pass"] = bool(z >= z_star)

        proven = [
            s for s in scored
            if s["wr_shrunk_pct"] >= 55 and s["pf"] >= 1.5
            and s["holdout_pass"] and s["bonferroni_pass"]
        ]
        proven.sort(key=lambda x: (x["pf"], x["wr_shrunk_pct"], x["n"]), reverse=True)

        proven_unadj = [s for s in scored if s["wr_shrunk_pct"] >= 55 and s["pf"] >= 1.5]
        proven_unadj.sort(key=lambda x: (x["pf"], x["wr_shrunk_pct"], x["n"]), reverse=True)

        promising_wr_weak_pf = [
            s for s in scored
            if s["wr_shrunk_pct"] >= 55 and s["pf"] < 1.5
        ]
        promising_wr_weak_pf.sort(key=lambda x: x["wr_shrunk_pct"], reverse=True)
        best_pf = sorted(scored, key=lambda x: x["pf"], reverse=True)[:5]

        final[ac] = {
            "n_closed": b["n_closed"],
            "n_cells_evaluated": b["n_cells_evaluated"],
            "top_edges_proven": proven[:10],
            "top_edges_proven_unadjusted": proven_unadj[:10],
            "rejected_good_wr_bad_pf": promising_wr_weak_pf[:5],
            "best_pf_overall": best_pf,
            "n_holdout_pass": sum(1 for s in scored if s["holdout_pass"]),
            "n_bonferroni_pass": sum(1 for s in scored if s["bonferroni_pass"]),
        }

    # Stash globals so main() can use them in payload header
    find_top_edges._total_cells = total_cells  # type: ignore[attr-defined]
    find_top_edges._bonf_alpha = bonf_alpha    # type: ignore[attr-defined]
    return final, total_cells


def main() -> int:
    conn = connect_stocks()
    try:
        print("[top_edges] fetching 90d picks...", flush=True)
        picks = fetch_picks(conn, 90)
        print(f"[top_edges]  -> {len(picks)} rows", flush=True)
    finally:
        conn.close()

    edges, total_cells = find_top_edges(picks)
    bonf_alpha = getattr(find_top_edges, "_bonf_alpha", 0.05)
    criteria = (
        f"PROVEN = WR_shrunk>=55%, PF>=1.5, n>=20, "
        f"holdout_pass (PF>=1.2 on both 60/40 chrono splits), "
        f"Bonferroni-adjusted alpha=0.05/{total_cells}={bonf_alpha:.3e}. "
        f"Enumerates all C(7,3)+C(7,4)=70 tag-dim combos across "
        f"[trust,conf,rr,fam,dir,score_dec,source]; cap top-200 cells per class by n."
    )
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": 90,
        "criteria": criteria,
        "n_total_cells_evaluated": total_cells,
        "bonferroni_alpha": bonf_alpha,
        "n_dim_combos": len(DIM_COMBOS),
        "by_class": edges,
    }
    OUT.write_text(json.dumps(payload, indent=2, default=str))
    print(f"[top_edges] wrote {OUT}")

    # Markdown summary
    try:
        md_path = ROOT / "reports" / "2026-05-25_top_edges_full_combinatorial.md"
        lines = [
            "# Top Edges — Full Combinatorial Audit (2026-05-25)",
            "",
            f"Generated: {payload['generated_at']}",
            f"Window: last {payload['window_days']}d closed picks",
            "",
            "## Criteria",
            "",
            criteria,
            "",
            f"- Total cells evaluated (after n>=20 + top-200/class cap): **{total_cells}**",
            f"- Dim combos enumerated per pick: **{len(DIM_COMBOS)}** (C(7,3)+C(7,4))",
            f"- Bonferroni alpha: **{bonf_alpha:.3e}**",
            "",
            "## Per-class summary",
            "",
            "| Class | n_closed | cells | holdout_pass | bonf_pass | PROVEN (adj) | PROVEN (unadj) | Top edge |",
            "|-------|----------|-------|--------------|-----------|--------------|----------------|----------|",
        ]
        for ac, b in sorted(edges.items()):
            top = b["top_edges_proven"][0] if b["top_edges_proven"] else (
                b["top_edges_proven_unadjusted"][0] if b["top_edges_proven_unadjusted"] else None
            )
            top_str = (
                f"{top['cell']} (PF {top['pf']}, WR_s {top['wr_shrunk_pct']}%, n {top['n']})"
                if top else "—"
            )
            lines.append(
                f"| {ac} | {b['n_closed']} | {b['n_cells_evaluated']} | "
                f"{b['n_holdout_pass']} | {b['n_bonferroni_pass']} | "
                f"{len(b['top_edges_proven'])} | {len(b['top_edges_proven_unadjusted'])} | {top_str} |"
            )
        lines += ["", "## PROVEN (Bonferroni + holdout) — top 5 per class", ""]
        for ac, b in sorted(edges.items()):
            lines.append(f"### {ac}")
            if not b["top_edges_proven"]:
                lines.append("_No cells passed all gates._")
            else:
                lines.append("| Cell | n | WR | WR_shrunk | PF | train_pf | holdout_pf |")
                lines.append("|------|---|----|-----------|----|----------|------------|")
                for s in b["top_edges_proven"][:5]:
                    lines.append(
                        f"| {s['cell']} | {s['n']} | {s['wr_pct']}% | {s['wr_shrunk_pct']}% | "
                        f"{s['pf']} | {s['train_pf']} | {s['holdout_pf']} |"
                    )
            lines.append("")
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text("\n".join(lines))
        print(f"[top_edges] wrote {md_path}")
    except Exception as e:
        print(f"[top_edges] WARN: could not write markdown summary: {e}")

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
