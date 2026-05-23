#!/usr/bin/env python3
"""§4 Bayesian Model Averaging (BMA-lite) — ensemble weights from recent performance.

Mercury / HEDGE_FUND_ENHANCEMENT_PLAN.md: **BMA** — weight ∝ posterior probability
given recent performance; update **weekly** (re-run this script after dashboard refresh).

This v0 uses **closed picks** only (real outcomes).  Each bucket (default
``source_system``) gets:

  * ``n``, ``wins``, ``losses`` (``pnl_pct > 0`` / ``< 0``; flat excluded)
  * **Beta(1,1)** posterior mean: ``p_hat = (wins + 1) / (wins + losses + 2)``
  * **Raw BMA weight** (stability-weighted): ``w_k = p_hat * sqrt(n)``
  * Normalized ``weight`` so active buckets sum to 1

Also reports **entropy** of weights (higher ⇒ more diversified ensemble proxy) and
**effective number of sources** ``exp(entropy)``.

Usage:
  python tools/bma_ensemble_weights_stub.py
  python tools/bma_ensemble_weights_stub.py --groupby strategy --min-trades 30 --top 25
  python tools/bma_ensemble_weights_stub.py --redis-alert
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DASHBOARD = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO / "tools" / "data" / "bma_weights_report.json"


def _float(x: Any) -> float | None:
    try:
        if x is None or x == "":
            return None
        v = float(x)
        if v != v:
            return None
        return v
    except (TypeError, ValueError):
        return None


def load_closed(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    closed = (doc.get("picks") or {}).get("recent_closed") or []
    if not isinstance(closed, list):
        return []
    return [p for p in closed if isinstance(p, dict)]


def aggregate(
    closed: List[Dict[str, Any]], groupby: str
) -> Dict[str, Tuple[int, int, int]]:
    """Return key -> (n, wins, losses)."""
    stats: Dict[str, List[int]] = defaultdict(lambda: [0, 0, 0])
    for p in closed:
        key = str(p.get(groupby) or "").strip() or "unknown"
        pnl = _float(p.get("pnl_pct"))
        if pnl is None or pnl == 0.0:
            continue
        row = stats[key]
        row[0] += 1
        if pnl > 0:
            row[1] += 1
        else:
            row[2] += 1
    return {k: (v[0], v[1], v[2]) for k, v in stats.items()}


def compute_weights(
    stats: Dict[str, Tuple[int, int, int]],
    min_trades: int,
    top: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
    rows: List[Dict[str, Any]] = []
    for key, (n, w, l) in stats.items():
        if n < min_trades:
            continue
        p_hat = (w + 1.0) / (w + l + 2.0)
        raw = p_hat * math.sqrt(float(n))
        rows.append(
            {
                "key": key,
                "n": n,
                "wins": w,
                "losses": l,
                "win_rate": round(w / float(n), 6),
                "posterior_mean_p": round(p_hat, 6),
                "raw_weight": round(raw, 8),
            }
        )
    rows.sort(key=lambda r: r["raw_weight"], reverse=True)
    if top > 0:
        rows = rows[:top]

    sraw = sum(r["raw_weight"] for r in rows) or 1.0
    for r in rows:
        r["weight"] = round(r["raw_weight"] / sraw, 8)

    wmap = {r["key"]: r["weight"] for r in rows}
    return rows, wmap


def entropy(weights: List[float]) -> float:
    h = 0.0
    for w in weights:
        if w <= 0:
            continue
        h -= w * math.log(w + 1e-18)
    return h


def redis_broadcast(msg: str) -> None:
    bus = Path(r"C:\Users\zerou\redis-bus\agent_bus.py")
    if not bus.is_file():
        return
    try:
        subprocess.run(
            [sys.executable, str(bus), "broadcast", "cursor-composer", msg],
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
    ap.add_argument("--out", type=str, default=str(OUT_JSON))
    ap.add_argument(
        "--groupby",
        choices=("source_system", "strategy"),
        default="source_system",
    )
    ap.add_argument("--min-trades", type=int, default=15)
    ap.add_argument("--top", type=int, default=40, help="keep top K by raw weight; 0=all")
    ap.add_argument("--redis-alert", action="store_true")
    args = ap.parse_args()

    path = Path(args.dashboard)
    if not path.is_file():
        print("ERROR: dashboard not found: %s" % path, file=sys.stderr)
        return 1

    closed = load_closed(path)
    stats = aggregate(closed, args.groupby)
    rows, wmap = compute_weights(stats, args.min_trades, args.top)

    ws = [r["weight"] for r in rows]
    ent = entropy(ws) if ws else 0.0
    eff = math.exp(ent) if ent > 0 else 0.0

    report: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_dashboard": str(path).replace("\\", "/"),
        "groupby": args.groupby,
        "min_trades": args.min_trades,
        "closed_picks_input": len(closed),
        "buckets_in_output": len(rows),
        "weight_entropy_nat": round(ent, 6),
        "effective_num_sources": round(eff, 4),
        "top_weights": rows,
        "method": "Beta(1,1) on win rate × sqrt(n) for raw weight; then normalize",
        "note": "Proxy for Mercury BMA — replace with marginal likelihood when models export it.",
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    top3 = ", ".join("%s=%.3f" % (r["key"][:20], r["weight"]) for r in rows[:3])
    print("buckets=%d H=%.3f n_eff=%.2f top3: %s -> %s" % (
        len(rows), ent, eff, top3, out_path))

    if args.redis_alert:
        redis_broadcast(
            "BMA-LITE: groupby=%s buckets=%d H=%.3f n_eff=%.2f top=%s | %s"
            % (
                args.groupby,
                len(rows),
                ent,
                eff,
                top3,
                str(out_path).replace("\\", "/"),
            )
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
