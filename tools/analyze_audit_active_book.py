#!/usr/bin/env python3
"""Analyze active picks vs closed history from audit dashboard_data.json.

Reads ``audit_dashboard/data/dashboard_data.json`` (same feed as /audit).
Emits ``tools/data/audit_active_book_analysis.json`` for docs and bus posts.

- Active picks by asset_class: scores, unrealized pnl_pct, VA share
- Spearman(score vs unrealized pnl) on actives only if n>=25 with finite both
- Per strategy (present in active): closed-book n, WR, mean pnl from recent_closed
- Closed picks summarized by asset_class
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DASH = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO / "tools" / "data" / "audit_active_book_analysis.json"
LAST_RUN_JSON = REPO / "tools" / "data" / "last_snapshot_run.json"


def _float(x: Any) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def pearson(x: np.ndarray, y: np.ndarray) -> float:
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 15:
        return float("nan")
    a, b = x[m], y[m]
    if a.std() < 1e-12 or b.std() < 1e-12:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def avg_ranks(arr: np.ndarray) -> np.ndarray:
    n = len(arr)
    order = np.argsort(arr, kind="mergesort")
    ranks = np.empty(n, dtype=np.float64)
    i = 0
    while i < n:
        j = i + 1
        v = arr[order[i]]
        while j < n and arr[order[j]] == v:
            j += 1
        avg = (i + j + 1) / 2.0
        for k in range(i, j):
            ranks[order[k]] = avg
        i = j
    return ranks


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 15:
        return float("nan")
    a, b = x[m], y[m]
    return pearson(avg_ranks(a), avg_ranks(b))


def unrealized_pct(pick: Dict[str, Any]) -> float | None:
    if pick.get("_suspicious_entry") or pick.get("pnl_flagged"):
        return None
    v = pick.get("unrealized_pnl_pct", pick.get("pnl_pct"))
    if v is None:
        return None
    f = _float(v)
    if not math.isfinite(f):
        return None
    return f


def norm_ac(pick: Dict[str, Any]) -> str:
    return str(pick.get("asset_class") or pick.get("category") or "UNKNOWN").upper().strip() or "UNKNOWN"


def _parse_dt(val: Any) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        try:
            return datetime.fromtimestamp(float(val), tz=timezone.utc)
        except (OSError, ValueError, OverflowError):
            return None
    t = str(val).strip()
    if not t:
        return None
    t = t.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(t)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def extract_systems_unrealized_echo(data: Dict[str, Any]) -> Dict[str, Any]:
    """Echo per-system unrealized from payload ``systems`` (generator rollup)."""
    systems = data.get("systems") or []
    if not isinstance(systems, list):
        return {"note": "systems_not_a_list"}
    total = 0.0
    rows: List[Dict[str, Any]] = []
    for s in systems:
        if not isinstance(s, dict):
            continue
        name = str(s.get("name") or s.get("source_system") or "?")
        u = _float(s.get("unrealized_pnl_pct"))
        if not math.isfinite(u):
            continue
        total += u
        rows.append({"name": name, "unrealized_pnl_pct": round(u, 2)})
    rows.sort(key=lambda r: -abs(r["unrealized_pnl_pct"]))
    return {
        "systems_unrealized_sum_pct": round(total, 2),
        "per_system_top_by_abs": rows[:25],
        "per_system_count": len(rows),
    }


def summarize_active_by_ac(active: List[Dict[str, Any]]) -> Dict[str, Any]:
    by: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for p in active:
        by[norm_ac(p)].append(p)

    out: Dict[str, Any] = {}
    for ac, rows in sorted(by.items()):
        scores = [_float(r.get("score")) for r in rows]
        scores_f = [s for s in scores if math.isfinite(s)]
        pnls = []
        for r in rows:
            u = unrealized_pct(r)
            if u is not None:
                pnls.append(u)
        va_n = sum(
            1
            for r in rows
            if str(r.get("research_cohort") or "").lower() == "verified_alpha"
        )
        out[ac] = {
            "n_active": len(rows),
            "verified_alpha_count": va_n,
            "verified_alpha_pct": round(100.0 * va_n / max(len(rows), 1), 1),
            "score_mean": round(float(np.mean(scores_f)), 2) if scores_f else None,
            "score_median": round(float(np.median(scores_f)), 2) if scores_f else None,
            "score_min": round(float(np.min(scores_f)), 2) if scores_f else None,
            "score_max": round(float(np.max(scores_f)), 2) if scores_f else None,
            "unrealized_n_with_value": len(pnls),
            "unrealized_mean_pct": round(float(np.mean(pnls)), 4) if pnls else None,
            "unrealized_median_pct": round(float(np.median(pnls)), 4) if pnls else None,
            "unrealized_sum_pct": round(float(np.sum(pnls)), 4) if pnls else None,
        }
    return out


def active_score_vs_unrealized(active: List[Dict[str, Any]], min_n: int = 25) -> Dict[str, Any]:
    xs: List[float] = []
    ys: List[float] = []
    for p in active:
        sc = _float(p.get("score"))
        u = unrealized_pct(p)
        if math.isfinite(sc) and u is not None and math.isfinite(u):
            xs.append(sc)
            ys.append(u)
    n = len(xs)
    if n < min_n:
        return {
            "n": n,
            "note": "insufficient_n_for_rank_ic_need_%d" % min_n,
            "pearson": None,
            "spearman": None,
        }
    a = np.array(xs, dtype=np.float64)
    b = np.array(ys, dtype=np.float64)
    return {
        "n": n,
        "pearson": round(pearson(a, b), 5),
        "spearman": round(spearman(a, b), 5),
    }


def closed_by_asset_class(closed: List[Dict[str, Any]]) -> Dict[str, Any]:
    by: Dict[str, List[float]] = defaultdict(list)
    for p in closed:
        pnl = _float(p.get("pnl_pct"))
        if not math.isfinite(pnl):
            continue
        by[norm_ac(p)].append(pnl)

    out = {}
    for ac, vals in sorted(by.items(), key=lambda x: -len(x[1])):
        a = np.array(vals, dtype=np.float64)
        wins = int(np.sum(a > 0))
        n = len(a)
        out[ac] = {
            "n_closed": n,
            "win_rate_pct": round(100.0 * wins / n, 2) if n else None,
            "mean_pnl_pct": round(float(np.mean(a)), 4) if n else None,
            "median_pnl_pct": round(float(np.median(a)), 4) if n else None,
        }
    return out


def strategy_closed_lookup(
    active: List[Dict[str, Any]], closed: List[Dict[str, Any]]
) -> Dict[str, Any]:
    strat_set = set()
    for p in active:
        s = str(p.get("strategy") or "").strip()
        if s:
            strat_set.add(s)

    by_strat: Dict[str, List[float]] = defaultdict(list)
    by_strat_dated: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
    now = datetime.now(timezone.utc)
    win_30 = now - timedelta(days=30)
    win_90 = now - timedelta(days=90)

    for p in closed:
        s = str(p.get("strategy") or "").strip()
        if s not in strat_set:
            continue
        pnl = _float(p.get("pnl_pct"))
        if not math.isfinite(pnl):
            continue
        by_strat[s].append(pnl)
        dt = _parse_dt(p.get("closed_at")) or _parse_dt(p.get("timestamp"))
        if dt is not None:
            by_strat_dated[s].append((dt, pnl))

    active_strategies_no_closed: List[str] = []
    rows_out = []
    for s in sorted(strat_set):
        vals = by_strat.get(s) or []
        if not vals:
            active_strategies_no_closed.append(s)
            rows_out.append(
                {
                    "strategy": s,
                    "n_closed": 0,
                    "n_closed_30d": 0,
                    "n_closed_90d": 0,
                    "win_rate_pct": None,
                    "mean_pnl_pct": None,
                    "median_pnl_pct": None,
                }
            )
            continue
        a = np.array(vals, dtype=np.float64)
        wins = int(np.sum(a > 0))
        n = len(a)
        dated = by_strat_dated.get(s) or []
        n30 = sum(1 for dt, _ in dated if dt >= win_30)
        n90 = sum(1 for dt, _ in dated if dt >= win_90)
        rows_out.append(
            {
                "strategy": s,
                "n_closed": n,
                "n_closed_30d": n30,
                "n_closed_90d": n90,
                "win_rate_pct": round(100.0 * wins / n, 2),
                "mean_pnl_pct": round(float(np.mean(a)), 4),
                "median_pnl_pct": round(float(np.median(a)), 4),
            }
        )

    rows_out.sort(key=lambda r: (-r["n_closed"], r["strategy"]))
    return {
        "strategies_on_active_book": sorted(strat_set),
        "strategies_with_zero_closed_matches": active_strategies_no_closed,
        "by_strategy_closed": rows_out,
        "recency_note": "n_closed_30d/90d use closed_at else timestamp; ISO parse only.",
    }


def aggregate_active_unrealized(active: List[Dict[str, Any]]) -> Dict[str, Any]:
    vals = []
    excluded = 0
    for p in active:
        if p.get("_suspicious_entry") or p.get("pnl_flagged"):
            excluded += 1
            continue
        u = unrealized_pct(p)
        if u is not None:
            vals.append(u)
    return {
        "active_count": len(active),
        "excluded_suspicious_or_flagged": excluded,
        "unrealized_count": len(vals),
        "unrealized_sum_pct": round(float(np.sum(vals)), 4) if vals else 0.0,
        "unrealized_mean_pct": round(float(np.mean(vals)), 4) if vals else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dashboard", default=str(DEFAULT_DASH))
    ap.add_argument("--out", default=str(OUT_JSON))
    args = ap.parse_args()

    path = Path(args.dashboard)
    if not path.is_file():
        print("missing %s" % path, file=sys.stderr)
        return 1

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    picks = data.get("picks") or {}
    active = picks.get("active") or []
    closed = picks.get("recent_closed") or []
    va = data.get("verified_alpha") or {}
    summary_top = data.get("summary") or {}

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "analysis_generated_at": ts,
        "dashboard_path": str(path),
        "dashboard_generated_at": summary_top.get("generated_at")
        or data.get("generated_at"),
        "active_count": len(active),
        "recent_closed_count": len(closed),
        "verified_alpha_summary_counts": {
            "active_count": va.get("active_count"),
            "smart_count": va.get("smart_count"),
            "realized": va.get("realized"),
        },
        "smart_picks_count": len(picks.get("smart_picks") or []),
        "active_raw_count": len(picks.get("active_raw") or []),
        "aggregate_active_unrealized": aggregate_active_unrealized(active),
        "active_by_asset_class": summarize_active_by_ac(active),
        "active_score_vs_unrealized_pnl_pct": active_score_vs_unrealized(active),
        "recent_closed_by_asset_class": closed_by_asset_class(closed),
        "active_strategies_vs_closed": strategy_closed_lookup(active, closed),
        "payload_systems_unrealized": extract_systems_unrealized_echo(data),
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print("wrote %s" % out_path)

    run_manifest = {
        "analysis_generated_at": ts,
        "dashboard_path": str(path),
        "dashboard_generated_at": payload.get("dashboard_generated_at"),
        "active_count": payload.get("active_count"),
        "smart_picks_count": payload.get("smart_picks_count"),
        "verified_alpha_active": (payload.get("verified_alpha_summary_counts") or {}).get(
            "active_count"
        ),
        "verified_alpha_smart": (payload.get("verified_alpha_summary_counts") or {}).get(
            "smart_count"
        ),
    }
    last_path = Path(LAST_RUN_JSON)
    last_path.parent.mkdir(parents=True, exist_ok=True)
    last_path.write_text(json.dumps(run_manifest, indent=2, default=str), encoding="utf-8")
    print("wrote %s" % last_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
