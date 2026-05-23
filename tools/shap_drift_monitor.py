#!/usr/bin/env python3
"""§4 SHAP / feature-importance drift monitor (stub → production path).

Mercury: alert when importance distribution shifts **> 20%** from baseline.

Until full SHAP is deployed, this tool uses **real** mean ``ml_composite_breakdown``
components from ``audit_dashboard/data/dashboard_data.json`` (active + optional
closed) as a **proxy** for "where the score mass sits."  Same math applies when
you swap in true per-model SHAP JSON (see schema).

Metrics (normalized distributions P, Q over feature keys):
  - ``l1_half`` = 0.5 * Σ|P_i - Q_i|  (total variation distance, in [0,1])
  - ``max_abs_delta`` = max_i |P_i - Q_i|
  - ``cosine_similarity`` on nonnegative weight vectors

Default drift alert: ``l1_half > 0.20`` OR ``max_abs_delta > 0.20``.

Usage:
  python tools/shap_drift_monitor.py --init-baseline
  python tools/shap_drift_monitor.py
  python tools/shap_drift_monitor.py --redis-alert --threshold 0.2
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DASHBOARD = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
DEFAULT_BASELINE = REPO / "tools" / "data" / "ml_composite_baseline.json"
OUT_REPORT = REPO / "tools" / "data" / "shap_drift_report.json"

# Public-facing score keys in ml_composite_breakdown (exclude _internal)
PROXY_KEYS = (
    "confidence",
    "forward_pnl",
    "forward_wr",
    "ml_score",
    "regime_match",
    "sector_rotation",
    "technical_alignment",
    "strategy_concentration_penalty",
)


def _float(x: Any) -> float:
    try:
        if x is None:
            return 0.0
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def extract_breakdown_vector(pick: Dict[str, Any]) -> Dict[str, float]:
    bd = pick.get("ml_composite_breakdown")
    if not isinstance(bd, dict):
        return {}
    out: Dict[str, float] = {}
    for k in PROXY_KEYS:
        if k not in bd:
            continue
        v = _float(bd.get(k))
        if v != v:  # NaN
            continue
        out[k] = max(0.0, v)
    return out


def mean_aggregate(picks: List[Dict[str, Any]]) -> Dict[str, float]:
    if not picks:
        return {}
    sums: Dict[str, float] = {k: 0.0 for k in PROXY_KEYS}
    counts: Dict[str, int] = {k: 0 for k in PROXY_KEYS}
    for p in picks:
        vec = extract_breakdown_vector(p)
        for k, v in vec.items():
            sums[k] += v
            counts[k] += 1
    return {k: sums[k] / counts[k] for k in PROXY_KEYS if counts[k] > 0}


def normalize(weights: Dict[str, float]) -> Dict[str, float]:
    s = sum(max(0.0, v) for v in weights.values())
    if s <= 1e-18:
        return {k: 1.0 / max(len(weights), 1) for k in weights}
    return {k: max(0.0, weights.get(k, 0.0)) / s for k in weights}


def drift_metrics(
    baseline: Dict[str, float], current: Dict[str, float]
) -> Tuple[Dict[str, Any], Dict[str, float], Dict[str, float]]:
    keys = sorted(set(baseline.keys()) | set(current.keys()))
    if not keys:
        return (
            {
                "l1_half": 0.0,
                "max_abs_delta": 0.0,
                "cosine_similarity": 1.0,
                "n_keys": 0,
            },
            {},
            {},
        )

    pb = normalize({k: baseline.get(k, 0.0) for k in keys})
    pc = normalize({k: current.get(k, 0.0) for k in keys})

    l1 = sum(abs(pb[k] - pc[k]) for k in keys)
    l1_half = 0.5 * l1
    max_abs = max(abs(pb[k] - pc[k]) for k in keys) if keys else 0.0

    dot = sum(pb[k] * pc[k] for k in keys)
    nb = sum(pb[k] ** 2 for k in keys) ** 0.5
    nc = sum(pc[k] ** 2 for k in keys) ** 0.5
    cos = dot / (nb * nc) if nb > 1e-18 and nc > 1e-18 else 0.0

    per_feature = {k: round(pc[k] - pb[k], 6) for k in keys}

    return (
        {
            "l1_half": round(l1_half, 6),
            "max_abs_delta": round(max_abs, 6),
            "cosine_similarity": round(cos, 6),
            "n_keys": len(keys),
        },
        pb,
        pc,
    )


def load_snapshot(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_snapshot(
    path: Path,
    source: str,
    features: Dict[str, float],
    n_samples: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": source,
        "features": {k: round(v, 6) for k, v in sorted(features.items())},
        "n_samples": n_samples,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_dashboard_picks(path: Path) -> Tuple[List[Dict], List[Dict]]:
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    picks = doc.get("picks") or {}
    active = picks.get("active") or []
    closed = picks.get("recent_closed") or []
    if not isinstance(active, list):
        active = []
    if not isinstance(closed, list):
        closed = []
    return [p for p in active if isinstance(p, dict)], [
        p for p in closed if isinstance(p, dict)
    ]


def redis_broadcast(msg: str) -> None:
    bus = Path(r"C:\Users\zerou\redis-bus\agent_bus.py")
    if not bus.is_file():
        return
    try:
        subprocess.run(
            [
                sys.executable,
                str(bus),
                "broadcast",
                "cursor-composer",
                msg,
            ],
            check=False,
            timeout=15,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dashboard", type=str, default=str(DEFAULT_DASHBOARD))
    ap.add_argument("--baseline", type=str, default=str(DEFAULT_BASELINE))
    ap.add_argument("--out", type=str, default=str(OUT_REPORT))
    ap.add_argument(
        "--pool",
        choices=("active", "active+closed", "closed"),
        default="active",
        help="which picks to aggregate for current snapshot",
    )
    ap.add_argument(
        "--init-baseline",
        action="store_true",
        help="write current aggregate to baseline file and exit",
    )
    ap.add_argument("--threshold", type=float, default=0.20)
    ap.add_argument(
        "--redis-alert",
        action="store_true",
        help="broadcast to Redis when drift exceeds threshold",
    )
    args = ap.parse_args()

    dash = Path(args.dashboard)
    if not dash.is_file():
        print("ERROR: dashboard not found: %s" % dash, file=sys.stderr)
        return 1

    active, closed = load_dashboard_picks(dash)
    if args.pool == "active":
        pool = active
    elif args.pool == "closed":
        pool = closed
    else:
        pool = active + closed

    current_raw = mean_aggregate(pool)
    if not current_raw:
        print("ERROR: no ml_composite_breakdown data in selected pool", file=sys.stderr)
        return 1

    source = "dashboard_%s_ml_breakdown_mean" % args.pool.replace("+", "_")

    if args.init_baseline:
        save_snapshot(Path(args.baseline), source, current_raw, len(pool))
        print("Wrote baseline:", args.baseline, "n=", len(pool))
        return 0

    bpath = Path(args.baseline)
    if not bpath.is_file():
        print(
            "WARN: no baseline at %s — run with --init-baseline first. "
            "Using uniform prior for this run only." % bpath,
            file=sys.stderr,
        )
        uniform = {k: 1.0 for k in current_raw}
        baseline_feats = uniform
    else:
        snap = load_snapshot(bpath)
        baseline_feats = dict(snap.get("features") or {})

    metrics, pb, pc = drift_metrics(baseline_feats, current_raw)
    drift_flag = (
        metrics["l1_half"] > args.threshold
        or metrics["max_abs_delta"] > args.threshold
    )

    report = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "proxy": "ml_composite_breakdown_mean",
        "pool": args.pool,
        "n_picks": len(pool),
        "threshold": args.threshold,
        "drift_alert": drift_flag,
        "metrics": metrics,
        "baseline_normalized": {k: round(pb[k], 6) for k in sorted(pb)},
        "current_normalized": {k: round(pc[k], 6) for k in sorted(pc)},
        "current_raw_mean": {k: round(v, 6) for k, v in sorted(current_raw.items())},
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print("n_picks=%d l1_half=%s max_abs=%s drift_alert=%s -> %s" % (
        len(pool),
        metrics["l1_half"],
        metrics["max_abs_delta"],
        drift_flag,
        out_path,
    ))

    if args.redis_alert:
        msg = (
            "SHAP-DRIFT-STUB (ml_composite proxy): pool=%s n=%d l1_half=%s max_abs=%s "
            "ALERT=%s threshold=%s | report=%s"
            % (
                args.pool,
                len(pool),
                metrics["l1_half"],
                metrics["max_abs_delta"],
                drift_flag,
                args.threshold,
                str(out_path).replace("\\", "/"),
            )
        )
        redis_broadcast(msg)

    return 0 if not drift_flag else 2


if __name__ == "__main__":
    sys.exit(main())
