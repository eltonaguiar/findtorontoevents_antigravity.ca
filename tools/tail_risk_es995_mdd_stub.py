#!/usr/bin/env python3
"""§2 Tail risk stub — ES 99.5% + rolling 30-day max drawdown (Mercury plan).

HEDGE_FUND_ENHANCEMENT_PLAN.md §2: **Expected Shortfall at 99.5%** and **MDD over
30-day rolling windows** on closed-trade outcomes.

Uses ``recent_closed`` with ``closed_at`` + ``pnl_pct`` (same date handling spirit
as ``rolling_cvar.py``):

  * **ES 99.5% (trade PnL proxy):** mean of the worst ``max(1, floor(n×0.005))``
    trades in the window (0.5% left tail of the empirical PnL distribution).
  * **MDD (window):** max peak-to-trough drop on the **cumulative sum** of
    window trades in **time order** (units: percentage points, same as ``pnl_pct``).

Calendar windows: **30 days** inclusive, stepped **1 day** (dense series). Minimum
trades per window configurable.

Output: ``tools/data/tail_risk_es995_mdd_report.json``

Usage:
  python tools/tail_risk_es995_mdd_stub.py
  python tools/tail_risk_es995_mdd_stub.py --crypto-only --redis-alert
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DASHBOARD = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO / "tools" / "data" / "tail_risk_es995_mdd_report.json"

WINDOW_DAYS = 30
TAIL_FRAC = 0.005  # 0.5% — ES 99.5% empirical tail mean
MIN_TRADES = 10


def parse_ts(ts_str: Any) -> Optional[datetime]:
    if not ts_str:
        return None
    s = str(ts_str).replace("+00:00", "Z").rstrip("Z")
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def es_tail_mean(pnls: List[float], tail_fraction: float) -> float:
    """Mean of smallest k outcomes, k = max(1, int(n * tail_fraction))."""
    if not pnls:
        return 0.0
    a = sorted(pnls)
    n = len(a)
    k = max(1, int(n * tail_fraction))
    k = min(k, n)
    return sum(a[:k]) / float(k)


def max_drawdown_on_cumsum(pnls_time_ordered: List[float]) -> float:
    """Max (running_max - current_cum) in pct points."""
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pnls_time_ordered:
        cum += p
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd
    return max_dd


def load_dated_picks(
    path: Path, crypto_only: bool
) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    picks = (data.get("picks") or {}).get("recent_closed") or []
    out: List[Dict[str, Any]] = []
    for p in picks:
        if not isinstance(p, dict):
            continue
        if crypto_only:
            ac = str(p.get("asset_class") or "").upper()
            if ac != "CRYPTO":
                continue
        pnl = p.get("pnl_pct")
        if pnl is None:
            continue
        ts = parse_ts(p.get("closed_at"))
        if ts is None:
            continue
        try:
            pf = float(pnl)
        except (TypeError, ValueError):
            continue
        out.append({"ts": ts, "pnl": pf})
    out.sort(key=lambda x: x["ts"])
    return out


def rolling_windows(
    dated: List[Dict[str, Any]],
    window_days: int,
    min_trades: int,
) -> List[Dict[str, Any]]:
    if not dated:
        return []
    by_date: Dict[Any, List[float]] = defaultdict(list)
    for row in dated:
        by_date[row["ts"].date()].append(row["pnl"])

    min_date = dated[0]["ts"].date()
    max_date = dated[-1]["ts"].date()
    series: List[Dict[str, Any]] = []
    current = min_date + timedelta(days=window_days)
    while current <= max_date:
        window_start = current - timedelta(days=window_days)
        window_pnls_flat: List[float] = []
        ordered_for_mdd: List[float] = []
        d = window_start
        while d <= current:
            day_list = by_date.get(d, [])
            window_pnls_flat.extend(day_list)
            for pnl in day_list:
                ordered_for_mdd.append(pnl)
            d += timedelta(days=1)

        if len(window_pnls_flat) >= min_trades:
            es995 = es_tail_mean(window_pnls_flat, TAIL_FRAC)
            mdd = max_drawdown_on_cumsum(ordered_for_mdd)
            series.append(
                {
                    "window_end": str(current),
                    "n_trades": len(window_pnls_flat),
                    "es_99_5_pct": round(es995, 6),
                    "mdd_pct_points": round(mdd, 6),
                }
            )
        current += timedelta(days=1)
    return series


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
    ap.add_argument("--window-days", type=int, default=WINDOW_DAYS)
    ap.add_argument("--min-trades", type=int, default=MIN_TRADES)
    ap.add_argument("--crypto-only", action="store_true")
    ap.add_argument("--redis-alert", action="store_true")
    args = ap.parse_args()

    path = Path(args.dashboard)
    if not path.is_file():
        print("ERROR: dashboard not found: %s" % path, file=sys.stderr)
        return 1

    dated = load_dated_picks(path, args.crypto_only)
    if not dated:
        print("ERROR: no dated picks", file=sys.stderr)
        return 1

    rolling = rolling_windows(dated, args.window_days, args.min_trades)
    all_pnls = [x["pnl"] for x in dated]
    all_es995 = es_tail_mean(all_pnls, TAIL_FRAC)
    all_mdd = max_drawdown_on_cumsum(all_pnls)

    last = rolling[-1] if rolling else None
    report: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_dashboard": str(path).replace("\\", "/"),
        "config": {
            "window_days": args.window_days,
            "min_trades_per_window": args.min_trades,
            "tail_fraction": TAIL_FRAC,
            "crypto_only": args.crypto_only,
        },
        "summary": {
            "dated_picks": len(dated),
            "rolling_windows": len(rolling),
            "all_time_es_99_5_pct": round(all_es995, 6),
            "all_time_mdd_pct_points": round(all_mdd, 6),
            "latest_window_end": last["window_end"] if last else None,
            "latest_es_99_5_pct": last["es_99_5_pct"] if last else None,
            "latest_mdd_pct_points": last["mdd_pct_points"] if last else None,
        },
        "rolling_series": rolling,
        "note": "ES is empirical mean of worst 0.5% of trade pnls in window; MDD on cumulative pnl_pct path — not dollar equity.",
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(
        "picks=%d windows=%d all_ES99.5=%.4f%% all_MDD=%.4fpp -> %s"
        % (len(dated), len(rolling), all_es995, all_mdd, out_path)
    )

    if args.redis_alert:
        redis_broadcast(
            "HEDGE_PLAN §2 tail-risk stub: ES99.5 + 30d rolling MDD — picks=%d windows=%d latest_ES99.5=%s | %s"
            % (
                len(dated),
                len(rolling),
                last["es_99_5_pct"] if last else "n/a",
                str(out_path).replace("\\", "/"),
            )
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
