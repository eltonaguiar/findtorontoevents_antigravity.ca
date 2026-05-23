#!/usr/bin/env python3
"""§4 Concept drift stub — two-sample KS on closed-trade outcomes + variance shift.

Mercury / HEDGE_FUND_ENHANCEMENT_PLAN.md: **ADWIN + weekly KS** on residuals.
This v0 uses **pnl_pct** from ``picks.recent_closed`` as an outcome proxy (until
model residuals are exported).

1. **Two-sample Kolmogorov–Smirnov** D = sup_t |F_early(t) − F_late(t)| on two
   time-ordered windows (default: first half vs second half by ``closed_at``).
   Reject equal distributions at ~5%% if D > c * sqrt((n+m)/(nm)), c ≈ 1.36.

2. **ADWIN-lite (variance ratio)**: compare variance of pnl in the first vs last
   quartile of the sorted-by-time series; flag if ratio > ``--var-ratio`` (default 2.5)
   or < 1/ratio (explosive shrink).

Usage:
  python tools/concept_drift_ks_stub.py
  python tools/concept_drift_ks_stub.py --redis-alert --min-per-window 200
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DASHBOARD = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_REPORT = REPO / "tools" / "data" / "concept_drift_report.json"


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


def _parse_ts(pick: Dict[str, Any]) -> Optional[float]:
    for key in ("closed_at", "timestamp", "opened_at"):
        raw = pick.get(key)
        if not raw:
            continue
        s = str(raw).strip()
        if not s:
            continue
        try:
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except ValueError:
            continue
    return None


def load_closed(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    picks = (doc.get("picks") or {}).get("recent_closed") or []
    if not isinstance(picks, list):
        return []
    return [p for p in picks if isinstance(p, dict)]


def ordered_pnl_series(closed: List[Dict[str, Any]]) -> List[Tuple[float, float]]:
    """List of (unix_ts, pnl_pct) with valid both."""
    rows: List[Tuple[float, float]] = []
    for p in closed:
        ts = _parse_ts(p)
        pnl = _float(p.get("pnl_pct"))
        if ts is None or pnl is None:
            continue
        rows.append((ts, pnl))
    rows.sort(key=lambda r: r[0])
    return rows


def ks_two_sample(x: List[float], y: List[float]) -> float:
    """D statistic; empirical CDFs, all knot points from x ∪ y."""
    if not x or not y:
        return 0.0
    xs = sorted(x)
    ys = sorted(y)
    n, m = len(xs), len(ys)
    knots = sorted(set(xs + ys))
    best = 0.0
    for t in knots:
        fn = bisect.bisect_right(xs, t) / float(n)
        gm = bisect.bisect_right(ys, t) / float(m)
        d = abs(fn - gm)
        if d > best:
            best = d
    return best


def ks_critical_d05(n: int, m: int) -> float:
    """Asymptotic 5%% two-sample KS critical value (Smirnov)."""
    if n < 1 or m < 1:
        return 1.0
    return 1.36 * math.sqrt((n + m) / float(n * m))


def split_windows(
    series: List[Tuple[float, float]], mode: str
) -> Tuple[List[float], List[float], str]:
    if len(series) < 4:
        return [], [], "insufficient_data"
    pnls = [p for _, p in series]
    if mode == "half":
        mid = len(series) // 2
        early = [series[i][1] for i in range(mid)]
        late = [series[i][1] for i in range(mid, len(series))]
        return early, late, "first_half_vs_second_half"
    if mode == "quartile":
        q = len(series) // 4
        if q < 1:
            return [], [], "insufficient_data"
        early = [series[i][1] for i in range(q)]
        late = [series[i][1] for i in range(len(series) - q, len(series))]
        return early, late, "first_quartile_vs_last_quartile"
    return [], [], "unknown_mode"


def variance_ratio_quarters(series: List[Tuple[float, float]]) -> Dict[str, Any]:
    """ADWIN-lite: var(first 25%%) vs var(last 25%%)."""
    n = len(series)
    if n < 8:
        return {"ok": False, "reason": "n<8"}
    q = max(2, n // 4)
    first = [series[i][1] for i in range(q)]
    last = [series[i][1] for i in range(n - q, n)]

    def var(vals: List[float]) -> float:
        if len(vals) < 2:
            return 0.0
        mu = sum(vals) / len(vals)
        return sum((v - mu) ** 2 for v in vals) / (len(vals) - 1)

    v1, v2 = var(first), var(last)
    eps = 1e-12
    ratio = (v2 + eps) / (v1 + eps)
    inv = (v1 + eps) / (v2 + eps)
    return {
        "ok": True,
        "var_early_quarter": round(v1, 8),
        "var_late_quarter": round(v2, 8),
        "ratio_late_over_early": round(ratio, 6),
        "ratio_early_over_late": round(inv, 6),
    }


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
    ap.add_argument(
        "--split",
        choices=("half", "quartile"),
        default="half",
        help="how to form early vs late windows for KS",
    )
    ap.add_argument(
        "--min-per-window",
        type=int,
        default=50,
        help="minimum trades per window or skip KS",
    )
    ap.add_argument(
        "--var-ratio",
        type=float,
        default=2.5,
        help="ADWIN-lite flag if var_late/var_early > this or inverse",
    )
    ap.add_argument("--redis-alert", action="store_true")
    args = ap.parse_args()

    path = Path(args.dashboard)
    if not path.is_file():
        print("ERROR: dashboard not found: %s" % path, file=sys.stderr)
        return 1

    closed = load_closed(path)
    series = ordered_pnl_series(closed)
    early, late, split_desc = split_windows(series, args.split)

    report: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_dashboard": str(path).replace("\\", "/"),
        "closed_picks_total": len(closed),
        "time_ordered_with_pnl": len(series),
        "split_mode": split_desc,
    }

    ks_d = 0.0
    ks_crit = 0.0
    ks_alert = False
    if len(early) >= args.min_per_window and len(late) >= args.min_per_window:
        ks_d = ks_two_sample(early, late)
        ks_crit = ks_critical_d05(len(early), len(late))
        ks_alert = ks_d > ks_crit
        report["ks_two_sample"] = {
            "D": round(ks_d, 6),
            "critical_D_approx_05": round(ks_crit, 6),
            "n_early": len(early),
            "n_late": len(late),
            "distribution_shift_alert": ks_alert,
        }
    else:
        report["ks_two_sample"] = {
            "skipped": True,
            "reason": "min_per_window not met",
            "n_early": len(early),
            "n_late": len(late),
        }

    vr = variance_ratio_quarters(series)
    report["adwin_lite_variance_quarters"] = vr
    var_alert = False
    if vr.get("ok"):
        r = vr.get("ratio_late_over_early", 1.0)
        ir = vr.get("ratio_early_over_late", 1.0)
        thr = args.var_ratio
        var_alert = r > thr or ir > thr

    report["drift_alert_any"] = bool(ks_alert or var_alert)
    report["thresholds"] = {
        "ks_alpha_05_smirnov": "D > 1.36*sqrt((n+m)/(nm))",
        "var_ratio": args.var_ratio,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(
        "n=%s KS_D=%s crit=%s ks_alert=%s var_alert=%s any=%s -> %s"
        % (
            len(series),
            round(ks_d, 4) if ks_d else "n/a",
            round(ks_crit, 4) if ks_crit else "n/a",
            ks_alert,
            var_alert,
            report["drift_alert_any"],
            out_path,
        )
    )

    if args.redis_alert:
        msg = (
            "CONCEPT-DRIFT-STUB: n=%s split=%s KS_D=%s ks_alert=%s var_alert=%s "
            "ANY=%s | %s"
            % (
                len(series),
                split_desc,
                round(ks_d, 4) if ks_d else None,
                ks_alert,
                var_alert,
                report["drift_alert_any"],
                str(out_path).replace("\\", "/"),
            )
        )
        redis_broadcast(msg)

    return 2 if report["drift_alert_any"] else 0


if __name__ == "__main__":
    sys.exit(main())
