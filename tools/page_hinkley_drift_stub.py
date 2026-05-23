#!/usr/bin/env python3
"""§4 Page–Hinkley drift stub (Mercury plan: ADWIN / Page–Hinkley / KS).

Online **Page–Hinkley** test for a shift in the mean of a univariate stream.
This v0 builds a **daily mean ``pnl_pct``** series from ``recent_closed`` (mean of
all closed trades that calendar day, UTC date from ``closed_at``) — an **outcome
proxy** until true model residuals exist.

**Upward drift:** cumulative score ``m_t += x_t - mu - delta`` with reference mean
``mu`` from a **warm-up** prefix; alert when ``m_t - min_{s<=t} m_s > h``.

**Downward drift:** same on ``-x_t`` (detects deterioration of mean PnL).

Defaults: ``delta = 0.05 * pstdev(warmup)``, ``h = 5.0 * pstdev(warmup)`` (tunable).

Output: ``tools/data/page_hinkley_drift_report.json``

Usage:
  python tools/page_hinkley_drift_stub.py
  python tools/page_hinkley_drift_stub.py --warmup-ratio 0.25 --redis-alert
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import pstdev
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DASHBOARD = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO / "tools" / "data" / "page_hinkley_drift_report.json"


def parse_ts(ts_str: Any) -> Optional[datetime]:
    if not ts_str:
        return None
    s = str(ts_str).replace("+00:00", "Z").rstrip("Z")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


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


def daily_mean_pnl_series(
    path: Path, crypto_only: bool
) -> Tuple[List[str], List[float]]:
    """Ordered calendar dates and matching daily mean pnl_pct."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    picks = (data.get("picks") or {}).get("recent_closed") or []
    sums: Dict[Any, float] = defaultdict(float)
    counts: Dict[Any, int] = defaultdict(int)

    for p in picks:
        if not isinstance(p, dict):
            continue
        if crypto_only and str(p.get("asset_class") or "").upper() != "CRYPTO":
            continue
        ts = parse_ts(p.get("closed_at"))
        if ts is None:
            continue
        pnl = _float(p.get("pnl_pct"))
        if pnl is None:
            continue
        d = ts.date()
        sums[d] += pnl
        counts[d] += 1

    dates_sorted = sorted(sums.keys())
    means = [sums[d] / max(1, counts[d]) for d in dates_sorted]
    labels = [str(d) for d in dates_sorted]
    return labels, means


def page_hinkley_one_sided(
    stream: List[float],
    mu: float,
    delta: float,
    threshold: float,
    negate: bool,
) -> Tuple[bool, Optional[int], float, float]:
    """
    Returns (alerted, index_in_stream_or_none, final_m_minus_min, m_min_at_end).
    If negate, monitor (-x) to detect drop in original x.
    """
    m = 0.0
    m_min = 0.0
    alert_at: Optional[int] = None
    for t, val in enumerate(stream):
        x = -val if negate else val
        adj_mu = -mu if negate else mu
        m += x - adj_mu - delta
        if m < m_min:
            m_min = m
        if m - m_min > threshold:
            alert_at = t
            break
    return alert_at is not None, alert_at, m - m_min, m_min


def run_report(
    x: List[str],
    y: List[float],
    warmup_ratio: float,
    delta_scale: float,
    h_scale: float,
) -> Dict[str, Any]:
    n = len(y)
    w = max(5, int(n * warmup_ratio))
    if n < w + 5:
        return {
            "error": "insufficient_days",
            "n_days": n,
            "warmup_days": w,
        }
    warm = y[:w]
    stream = y[w:]
    mu = sum(warm) / len(warm)
    sig = pstdev(warm) if len(warm) > 1 else 0.0
    if sig < 1e-12:
        sig = 1.0
    delta = delta_scale * sig
    h = h_scale * sig

    up_alert, up_i, _, _ = page_hinkley_one_sided(stream, mu, delta, h, negate=False)
    dn_alert, dn_i, _, _ = page_hinkley_one_sided(stream, mu, delta, h, negate=True)

    def global_idx(i: Optional[int]) -> Optional[int]:
        if i is None:
            return None
        return w + i

    return {
        "n_days": n,
        "warmup_days": w,
        "monitor_days": len(stream),
        "warmup_mean_pnl_pct": round(mu, 6),
        "warmup_pstdev_pnl_pct": round(sig, 6),
        "delta_used": round(delta, 8),
        "threshold_h": round(h, 8),
        "upward_drift_alert": up_alert,
        "upward_alert_monitor_index": up_i,
        "upward_alert_day": x[global_idx(up_i)] if up_i is not None else None,
        "downward_drift_alert": dn_alert,
        "downward_alert_monitor_index": dn_i,
        "downward_alert_day": x[global_idx(dn_i)] if dn_i is not None else None,
        "daily_mean_series_tail": [
            {"date": x[i], "mean_pnl_pct": round(y[i], 6)} for i in range(max(0, n - 14), n)
        ],
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
    ap.add_argument("--out", type=str, default=str(OUT_JSON))
    ap.add_argument("--warmup-ratio", type=float, default=0.3)
    ap.add_argument("--delta-scale", type=float, default=0.05, help="delta = scale * pstdev(warmup)")
    ap.add_argument("--h-scale", type=float, default=5.0, help="threshold = scale * pstdev(warmup)")
    ap.add_argument("--crypto-only", action="store_true")
    ap.add_argument("--redis-alert", action="store_true")
    args = ap.parse_args()

    path = Path(args.dashboard)
    if not path.is_file():
        print("ERROR: dashboard not found: %s" % path, file=sys.stderr)
        return 1

    labels, means = daily_mean_pnl_series(path, args.crypto_only)
    body = run_report(labels, means, args.warmup_ratio, args.delta_scale, args.h_scale)

    report: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_dashboard": str(path).replace("\\", "/"),
        "config": {
            "warmup_ratio": args.warmup_ratio,
            "delta_scale": args.delta_scale,
            "h_scale": args.h_scale,
            "crypto_only": args.crypto_only,
        },
        "page_hinkley": body,
        "note": "Daily mean pnl_pct is an outcome proxy, not a model residual. Tune delta/h with labeled drift events.",
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    if body.get("error"):
        print("ERROR: %s (n=%s)" % (body["error"], body.get("n_days")), file=sys.stderr)
        return 1

    ph = body
    print(
        "days=%d up_alert=%s down_alert=%s -> %s"
        % (
            ph["n_days"],
            ph["upward_drift_alert"],
            ph["downward_drift_alert"],
            out_path,
        )
    )

    if args.redis_alert:
        redis_broadcast(
            "HEDGE_PLAN §4 Page-Hinkley stub: days=%d up=%s down=%s | %s"
            % (
                ph["n_days"],
                ph["upward_drift_alert"],
                ph["downward_drift_alert"],
                str(out_path).replace("\\", "/"),
            )
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
