#!/usr/bin/env python3
"""§4 Calibration stub — Brier score + binned reliability (ECE-style) from closed picks.

Mercury / HEDGE_FUND_ENHANCEMENT_PLAN.md: **Brier score + reliability diagrams**;
flag rough miscalibration when **expected calibration error (ECE)** exceeds a threshold.

Uses **real** ``recent_closed`` rows: ``confidence`` as predicted win probability,
outcome ``y = 1`` if ``pnl_pct > 0`` else ``0``.  Ignores pushes (``pnl_pct == 0``).

Confidence normalization:
  - If ``1 < conf <= 100``, treat as percent and divide by 100.
  - Clip to ``[1e-6, 1 - 1e-6]`` for numerical stability.

Metrics:
  - **Brier** = mean (p - y)²
  - **ECE** = Σ (n_b / n) · |acc_b − mean(p)_b|  over equal-width probability bins
  - **Brier skill** vs baseline rate p̂ = global win rate (optional)

Usage:
  python tools/brier_reliability_stub.py
  python tools/brier_reliability_stub.py --min-confidence 0.05 --ece-alert 0.05 --redis-alert
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DASHBOARD = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_REPORT = REPO / "tools" / "data" / "brier_calibration_report.json"


def _float(x: Any) -> Optional[float]:
    try:
        if x is None or x == "":
            return None
        v = float(x)
        if v != v:
            return None
        return v
    except (TypeError, ValueError):
        return None


def normalize_prob(conf: float) -> Optional[float]:
    if conf != conf:
        return None
    if conf > 1.0 and conf <= 100.0:
        conf = conf / 100.0
    if conf < 0.0 or conf > 1.0:
        return None
    eps = 1e-6
    if conf < eps:
        return None
    return min(1.0 - eps, max(eps, conf))


def load_pairs(
    path: Path, min_conf: float
) -> Tuple[List[Tuple[float, int]], Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    closed = (doc.get("picks") or {}).get("recent_closed") or []
    if not isinstance(closed, list):
        return [], {"error": "no recent_closed"}

    pairs: List[Tuple[float, int]] = []
    skipped = {"no_pnl": 0, "push": 0, "bad_conf": 0}

    for p in closed:
        if not isinstance(p, dict):
            continue
        pnl = _float(p.get("pnl_pct"))
        if pnl is None:
            skipped["no_pnl"] += 1
            continue
        if pnl == 0.0:
            skipped["push"] += 1
            continue
        y = 1 if pnl > 0 else 0

        c = _float(p.get("confidence"))
        if c is None:
            skipped["bad_conf"] += 1
            continue
        p_hat = normalize_prob(c)
        if p_hat is None or p_hat < min_conf:
            skipped["bad_conf"] += 1
            continue
        pairs.append((p_hat, y))

    return pairs, skipped


def brier_score(pairs: List[Tuple[float, int]]) -> float:
    if not pairs:
        return 0.0
    return sum((p - y) ** 2 for p, y in pairs) / len(pairs)


def brier_skill(pairs: List[Tuple[float, int]], p_base: float) -> float:
    """1 - Brier_model / Brier_naive where naive always predicts p_base."""
    if not pairs:
        return 0.0
    b = brier_score(pairs)
    bn = sum((p_base - y) ** 2 for _, y in pairs) / len(pairs)
    if bn <= 1e-18:
        return 0.0
    return 1.0 - b / bn


def ece_equal_width(pairs: List[Tuple[float, int]], n_bins: int) -> Tuple[float, List[Dict]]:
    """Expected calibration error with equal-width bins on [0,1]."""
    if not pairs or n_bins < 2:
        return 0.0, []

    bins: List[List[Tuple[float, int]]] = [[] for _ in range(n_bins)]
    for p, y in pairs:
        idx = min(n_bins - 1, int(p * n_bins))
        bins[idx].append((p, y))

    n = len(pairs)
    width = 1.0 / n_bins
    ece = 0.0
    rows: List[Dict[str, Any]] = []
    for i, bucket in enumerate(bins):
        if not bucket:
            rows.append(
                {
                    "bin": i,
                    "p_range": [round(i * width, 4), round((i + 1) * width, 4)],
                    "n": 0,
                    "mean_pred": None,
                    "win_rate": None,
                    "gap": None,
                }
            )
            continue
        nb = len(bucket)
        mean_p = sum(x[0] for x in bucket) / nb
        acc = sum(x[1] for x in bucket) / nb
        gap = abs(acc - mean_p)
        ece += (nb / n) * gap
        rows.append(
            {
                "bin": i,
                "p_range": [round(i * width, 4), round((i + 1) * width, 4)],
                "n": nb,
                "mean_pred": round(mean_p, 6),
                "win_rate": round(acc, 6),
                "gap": round(gap, 6),
            }
        )

    return round(ece, 6), rows


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
    ap.add_argument("--out", type=str, default=str(OUT_REPORT))
    ap.add_argument("--min-confidence", type=float, default=0.05)
    ap.add_argument("--bins", type=int, default=10)
    ap.add_argument(
        "--ece-alert",
        type=float,
        default=0.08,
        help="alert if ECE exceeds this (Mercury suggested 0.02 for action; default looser for stub)",
    )
    ap.add_argument(
        "--brier-alert",
        type=float,
        default=0.30,
        help="alert if Brier exceeds this (0.25 = random coin at 0.5)",
    )
    ap.add_argument("--redis-alert", action="store_true")
    args = ap.parse_args()

    path = Path(args.dashboard)
    if not path.is_file():
        print("ERROR: dashboard not found: %s" % path, file=sys.stderr)
        return 1

    pairs, skipped = load_pairs(path, args.min_confidence)
    if len(pairs) < 50:
        print(
            "ERROR: too few rows with confidence>=%s (got %s)"
            % (args.min_confidence, len(pairs)),
            file=sys.stderr,
        )
        return 1

    win_rate = sum(y for _, y in pairs) / len(pairs)
    brier = round(brier_score(pairs), 6)
    skill = round(brier_skill(pairs, win_rate), 6)
    ece, bin_rows = ece_equal_width(pairs, args.bins)

    ece_flag = ece > args.ece_alert
    brier_flag = brier > args.brier_alert
    alert = ece_flag or brier_flag

    report: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_dashboard": str(path).replace("\\", "/"),
        "n_pairs": len(pairs),
        "skipped": skipped,
        "min_confidence": args.min_confidence,
        "empirical_win_rate": round(win_rate, 6),
        "brier_score": brier,
        "brier_skill_vs_baseline_rate": skill,
        "ece_equal_width_bins": args.bins,
        "ece": ece,
        "reliability_bins": bin_rows,
        "thresholds": {"ece_alert": args.ece_alert, "brier_alert": args.brier_alert},
        "calibration_alert": alert,
        "notes": "confidence=p(win); outcome from sign(pnl_pct). Tune thresholds when production probs are well-calibrated.",
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(
        "n=%s win_rate=%.3f Brier=%s ECE=%s alert=%s -> %s"
        % (len(pairs), win_rate, brier, ece, alert, out_path)
    )

    if args.redis_alert and alert:
        redis_broadcast(
            "BRIER/ECE ALERT: n=%s Brier=%s ECE=%s (thresholds brier>%s ece>%s) %s"
            % (
                len(pairs),
                brier,
                ece,
                args.brier_alert,
                args.ece_alert,
                str(out_path).replace("\\", "/"),
            )
        )

    return 2 if alert else 0


if __name__ == "__main__":
    sys.exit(main())
