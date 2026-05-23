"""Predictor IC (Information Coefficient) reproducer.

Verifies the Spearman / Pearson IC values claimed by third-party agents
(mimo PR proposal 2026-05-13) before any per-asset-class scoring reweight
PR is merged. Resolves blocker A1 from
``reports/audit_enhancements_2026-05-13/action_items.md``.

Data sources (auto-detected):
  - ``alpha_engine/data/closed_picks.json`` (8235 picks, includes
    quan_engine MATIC ghost: 1057 rows).  Has: ``elite_score``,
    ``confidence``, ``net_edge_bps``, ``pnl_pct``.
  - ``audit_dashboard/data/dashboard_data.json::picks.recent_closed``
    (3500 picks, post-resolver-v2 cleaned). Has: ``elite_score``,
    ``confidence``, ``trust_score``, ``trust_tier``, ``pnl_pct``.

Ghost-cleanup filter: drops ``(source_system=quan_engine, symbol like
MATIC*)`` rows. Memory ref: ``project_quan_engine_matic_positive_artifact``
+ ``project_confidence_rho_matic_artifact``.

Usage:
  python tools/predictor_ic_reproducer.py
  python tools/predictor_ic_reproducer.py --no-ghost-filter
  python tools/predictor_ic_reproducer.py --dataset recent_closed

NFA. Read-only. Writes report to
``reports/predictor_ic_reproducer_<UTC>.json`` and prints summary table.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent

CLOSED_PICKS_PATH = ROOT / "alpha_engine" / "data" / "closed_picks.json"
DASHBOARD_PATH = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"

FEATURES_CLOSED_PICKS = ["elite_score", "confidence", "net_edge_bps"]
FEATURES_RECENT_CLOSED = ["elite_score", "confidence", "trust_score"]


def _load_closed_picks() -> list[dict]:
    if not CLOSED_PICKS_PATH.exists():
        return []
    d = json.loads(CLOSED_PICKS_PATH.read_text(encoding="utf-8"))
    return d if isinstance(d, list) else (d.get("picks") or [])


def _load_recent_closed() -> list[dict]:
    if not DASHBOARD_PATH.exists():
        return []
    d = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))
    return (d.get("picks") or {}).get("recent_closed") or []


def _is_matic_ghost(p: dict) -> bool:
    src = (p.get("source_system") or "").lower()
    sym = (p.get("symbol") or "").upper()
    return src == "quan_engine" and sym.startswith("MATIC")


def _rank(xs: list[float]) -> list[float]:
    """Average-rank for ties; identical to scipy's 'average' method."""
    n = len(xs)
    idx = sorted(range(n), key=lambda i: xs[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and xs[idx[j + 1]] == xs[idx[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[idx[k]] = avg
        i = j + 1
    return ranks


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 3:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(xs, ys))
    vx = sum((xi - mx) ** 2 for xi in xs)
    vy = sum((yi - my) ** 2 for yi in ys)
    if vx == 0 or vy == 0:
        return 0.0
    return num / math.sqrt(vx * vy)


def _spearman(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 3:
        return 0.0
    return _pearson(_rank(xs), _rank(ys))


def _safe_float(v) -> float | None:
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _ic_for_feature(picks: list[dict], feature: str, target: str = "pnl_pct") -> dict:
    pairs = []
    for p in picks:
        x = _safe_float(p.get(feature))
        y = _safe_float(p.get(target))
        if x is None or y is None:
            continue
        pairs.append((x, y))
    if len(pairs) < 30:
        return {
            "feature": feature,
            "n": len(pairs),
            "spearman_rho": None,
            "pearson_r": None,
            "verdict": "INSUFFICIENT_N",
        }
    xs = [a for a, _ in pairs]
    ys = [b for _, b in pairs]
    rho = _spearman(xs, ys)
    r = _pearson(xs, ys)
    return {
        "feature": feature,
        "n": len(pairs),
        "spearman_rho": round(rho, 4),
        "pearson_r": round(r, 4),
        "verdict": _verdict(rho),
    }


def _verdict(rho: float) -> str:
    if rho is None:
        return "UNKNOWN"
    a = abs(rho)
    if a < 0.03:
        return "NOISE"
    if rho < -0.10:
        return "ANTI_PREDICTIVE"
    if rho < 0:
        return "WEAK_INVERSE"
    if rho < 0.10:
        return "WEAK_POSITIVE"
    if rho < 0.20:
        return "MODEST_POSITIVE"
    return "STRONG_POSITIVE"


def _summary_row(rec: dict) -> str:
    rho = rec.get("spearman_rho")
    rho_s = f"{rho:+.4f}" if rho is not None else "    -- "
    return (
        f"  {rec['feature']:<22} n={rec['n']:>5}  "
        f"rho={rho_s}  verdict={rec['verdict']}"
    )


def run(dataset: str, ghost_filter: bool, out_path: Path | None) -> dict:
    if dataset == "closed_picks":
        picks_all = _load_closed_picks()
        features = FEATURES_CLOSED_PICKS
        path_used = str(CLOSED_PICKS_PATH.relative_to(ROOT))
    elif dataset == "recent_closed":
        picks_all = _load_recent_closed()
        features = FEATURES_RECENT_CLOSED
        path_used = str(DASHBOARD_PATH.relative_to(ROOT)) + "::picks.recent_closed"
    else:
        raise ValueError(f"unknown dataset {dataset}")

    n_total = len(picks_all)
    if ghost_filter:
        picks = [p for p in picks_all if not _is_matic_ghost(p)]
    else:
        picks = list(picks_all)
    n_after = len(picks)
    n_ghost = n_total - n_after

    print(f"# Predictor IC reproducer")
    print(f"# dataset={dataset} path={path_used}", file=sys.stderr)
    print(f"# n_total={n_total} ghost_filter={ghost_filter} "
          f"n_dropped={n_ghost} n_kept={n_after}", file=sys.stderr)

    results = [_ic_for_feature(picks, f) for f in features]
    print("\n  feature                 n       rho      verdict")
    print("  " + "-" * 60)
    for rec in results:
        print(_summary_row(rec))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": dataset,
        "path_used": path_used,
        "ghost_filter_applied": ghost_filter,
        "n_total": n_total,
        "n_ghost_dropped": n_ghost,
        "n_kept": n_after,
        "results": results,
        "target": "pnl_pct",
        "notes": [
            "Spearman rho computed against pnl_pct, no time-decay weighting.",
            "Ghost filter drops (source_system=quan_engine, symbol startswith MATIC) — "
            "see memory project_quan_engine_matic_positive_artifact.",
            "NFA. Hindsight IC. Out-of-sample IC may differ.",
        ],
    }
    if out_path is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = ROOT / "reports" / f"predictor_ic_reproducer_{ts}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\n# wrote {out_path.relative_to(ROOT)}", file=sys.stderr)
    return payload


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", choices=["closed_picks", "recent_closed"],
                    default="closed_picks")
    ap.add_argument("--no-ghost-filter", action="store_true",
                    help="Skip MATIC ghost filter (reproduce pre-cleanup numbers)")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    run(args.dataset, ghost_filter=(not args.no_ghost_filter), out_path=args.out)


if __name__ == "__main__":
    main()
