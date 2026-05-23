#!/usr/bin/env python3
"""§7 Alpha decay monitor — rolling 30-day Sharpe per strategy (Mercury plan).

HEDGE_FUND_ENHANCEMENT_PLAN.md §7: **Rolling 30-day Sharpe** per strategy.  If Sharpe
drops **> 2σ below the historical mean** for **3 consecutive** rolling periods →
flag **auto de-risk** candidate (monitoring only in v0; no auto trades).

Uses **closed picks** with valid ``closed_at`` and ``pnl_pct``.  Per window:

  * Sharpe proxy: ``mean(pnl) / std(pnl) * sqrt(n)`` for ``n`` trades in window
    (trade-level i.i.d. approximation — same spirit as other audit stubs).

Windows: **30 calendar days**, stepped **7 days**, when the strategy spans enough
history; otherwise **30 trades** stepped by **7 trades** (``recent_closed`` is often
short-span per strategy).  Baseline mean/σ computed from
all rolling Sharpe points **excluding the last 3**; alert if those last three
are each **strictly below** ``mean - 2*std`` (and ``std > 0``).

Usage:
  python tools/alpha_decay_rolling_sharpe.py
  python tools/alpha_decay_rolling_sharpe.py --window-days 30 --step-days 7 --redis-alert
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DASHBOARD = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO / "tools" / "data" / "alpha_decay_report.json"


def parse_ts(ts_str: Any) -> Optional[datetime]:
    if not ts_str:
        return None
    s = str(ts_str).replace("+00:00", "Z").rstrip("Z")
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=timezone.utc)
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


def window_sharpe(pnls: List[float]) -> float:
    n = len(pnls)
    if n < 2:
        return 0.0
    m = sum(pnls) / n
    var = sum((x - m) ** 2 for x in pnls) / (n - 1)
    sd = math.sqrt(var) if var > 0 else 0.0
    if sd < 1e-12:
        return 0.0
    return (m / sd) * math.sqrt(float(n))


def rolling_series_calendar(
    trades: List[Tuple[datetime, float]],
    window_days: int,
    step_days: int,
    min_trades: int,
) -> List[Dict[str, Any]]:
    """Rolling Sharpe on calendar windows [end-window_days, end] inclusive (see rolling_cvar)."""
    t0d = trades[0][0].date()
    t1d = trades[-1][0].date()
    out: List[Dict[str, Any]] = []
    end_d = t0d + timedelta(days=window_days)
    while end_d <= t1d:
        start_d = end_d - timedelta(days=window_days)
        pnls = []
        for dt, p in trades:
            d = dt.date()
            if start_d <= d <= end_d:
                pnls.append(p)
        if len(pnls) >= min_trades:
            s = window_sharpe(pnls)
            out.append(
                {
                    "window_end": str(end_d),
                    "mode": "calendar",
                    "n_trades": len(pnls),
                    "rolling_sharpe": round(s, 6),
                }
            )
        end_d += timedelta(days=step_days)
    return out


def rolling_series_trade_count(
    trades: List[Tuple[datetime, float]],
    window_trades: int,
    step_trades: int,
    min_trades: int,
) -> List[Dict[str, Any]]:
    """When calendar span < window_days in recent_closed, use trade-index windows (Mercury intent)."""
    trades = sorted(trades, key=lambda x: x[0])
    out: List[Dict[str, Any]] = []
    n = len(trades)
    if n < window_trades:
        return out
    j = window_trades
    while j <= n:
        chunk = trades[j - window_trades : j]
        pnls = [p for _, p in chunk]
        if len(pnls) >= min_trades:
            s = window_sharpe(pnls)
            end_dt = chunk[-1][0]
            out.append(
                {
                    "window_end": str(end_dt.date()),
                    "mode": "trade_count",
                    "n_trades": len(pnls),
                    "rolling_sharpe": round(s, 6),
                }
            )
        j += step_trades
    return out


def rolling_series_for_strategy(
    trades: List[Tuple[datetime, float]],
    window_days: int,
    step_days: int,
    min_trades: int,
    window_trades: int,
    step_trades: int,
) -> List[Dict[str, Any]]:
    trades = sorted(trades, key=lambda x: x[0])
    span_days = (trades[-1][0].date() - trades[0][0].date()).days
    cal = rolling_series_calendar(trades, window_days, step_days, min_trades)
    if cal:
        return cal
    if span_days < window_days and len(trades) >= window_trades:
        return rolling_series_trade_count(trades, window_trades, step_trades, min_trades)
    return []


def decay_alert(series: List[Dict[str, Any]], sigma_mult: float) -> Tuple[bool, Dict[str, Any]]:
    """True if last 3 rolling sharpes are all < mean_hist - sigma_mult * std_hist."""
    if len(series) < 6:
        return False, {"reason": "need_at_least_6_rolling_points"}
    sharpes = [float(x["rolling_sharpe"]) for x in series]
    hist = sharpes[:-3]
    tail = sharpes[-3:]
    mu = sum(hist) / len(hist)
    if len(hist) < 2:
        return False, {"reason": "insufficient_hist_for_std"}
    var = sum((x - mu) ** 2 for x in hist) / (len(hist) - 1)
    sd = math.sqrt(var) if var > 0 else 0.0
    if sd < 1e-12:
        return False, {"reason": "zero_hist_std"}
    thr = mu - sigma_mult * sd
    breached = all(x < thr for x in tail)
    return breached, {
        "hist_mean": round(mu, 6),
        "hist_std": round(sd, 6),
        "threshold": round(thr, 6),
        "last_three": [round(x, 6) for x in tail],
        "sigma_mult": sigma_mult,
    }


def load_closed(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    closed = (doc.get("picks") or {}).get("recent_closed") or []
    if not isinstance(closed, list):
        return []
    return [p for p in closed if isinstance(p, dict)]


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
    ap.add_argument("--window-days", type=int, default=30)
    ap.add_argument("--step-days", type=int, default=7)
    ap.add_argument("--min-trades-window", type=int, default=8)
    ap.add_argument("--min-total-trades", type=int, default=40)
    ap.add_argument(
        "--window-trades",
        type=int,
        default=30,
        help="trade-count window when calendar span < --window-days",
    )
    ap.add_argument("--step-trades", type=int, default=7)
    ap.add_argument("--sigma-mult", type=float, default=2.0)
    ap.add_argument("--crypto-only", action="store_true", help="asset_class == CRYPTO")
    ap.add_argument("--redis-alert", action="store_true")
    args = ap.parse_args()

    path = Path(args.dashboard)
    if not path.is_file():
        print("ERROR: dashboard not found: %s" % path, file=sys.stderr)
        return 1

    by_strat: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
    for p in load_closed(path):
        pnl = _float(p.get("pnl_pct"))
        if pnl is None:
            continue
        if args.crypto_only:
            ac = str(p.get("asset_class") or "").upper()
            if ac != "CRYPTO":
                continue
        ts = parse_ts(p.get("closed_at"))
        if ts is None:
            continue
        strat = str(p.get("strategy") or "unknown").strip() or "unknown"
        by_strat[strat].append((ts, pnl))

    flagged: List[Dict[str, Any]] = []
    all_series: Dict[str, List[Dict[str, Any]]] = {}

    for strat, trades in by_strat.items():
        if len(trades) < args.min_total_trades:
            continue
        rs = rolling_series_for_strategy(
            trades,
            args.window_days,
            args.step_days,
            args.min_trades_window,
            args.window_trades,
            args.step_trades,
        )
        if not rs:
            continue
        all_series[strat] = rs
        alert, detail = decay_alert(rs, args.sigma_mult)
        if alert:
            flagged.append(
                {
                    "strategy": strat,
                    "total_trades": len(trades),
                    "rolling_points": len(rs),
                    **detail,
                }
            )

    report: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_dashboard": str(path).replace("\\", "/"),
        "config": {
            "window_days": args.window_days,
            "step_days": args.step_days,
            "window_trades": args.window_trades,
            "step_trades": args.step_trades,
            "min_trades_window": args.min_trades_window,
            "min_total_trades": args.min_total_trades,
            "sigma_mult": args.sigma_mult,
            "crypto_only": args.crypto_only,
        },
        "summary": {
            "strategies_with_rolling_series": len(all_series),
            "decay_flagged": len(flagged),
        },
        "decay_flagged_strategies": sorted(flagged, key=lambda x: x["strategy"]),
        "rolling_series_by_strategy": {
            k: v for k, v in sorted(all_series.items(), key=lambda kv: -len(kv[1]))[:80]
        },
        "note": "Monitor-only v0; confirm with economic significance before de-risking.",
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(
        "strategies_tracked=%d flagged=%d -> %s"
        % (len(all_series), len(flagged), out_path)
    )

    if args.redis_alert:
        redis_broadcast(
            "HEDGE_PLAN §7 alpha-decay: rolling 30d Sharpe — tracked=%d flagged_3x2sigma=%d | %s"
            % (len(all_series), len(flagged), str(out_path).replace("\\", "/"))
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
