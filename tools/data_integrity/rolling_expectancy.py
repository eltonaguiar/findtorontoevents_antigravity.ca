"""Rolling 30-day expectancy + WR + PF window analysis.

Detects regime decay — when did the system start losing? Feeds into
the staleness framework from PR #149.

Method:
  1. Load closed picks, filter ghosts, extract (closed_at, pnl_pct).
  2. Sort by closed_at.
  3. For each ending day in [min_day, max_day], compute expectancy/WR/PF
     over the prior `window_days` window.
  4. Detect the earliest day where rolling expectancy crosses from
     positive to negative (the "decay point").
  5. Report the slope of rolling expectancy via simple least squares.

Stdlib only. Safe-default when n < 2 * window.

Usage:
    python tools/data_integrity/rolling_expectancy.py
    python tools/data_integrity/rolling_expectancy.py --window 30
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from datetime import timedelta
from typing import Any

try:
    from tools.data_integrity import _common
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from tools.data_integrity import _common  # type: ignore

DEFAULT_WINDOW_DAYS = 30
DEFAULT_STEP_DAYS = 3  # sample every 3 days to keep output manageable


def extract_trades(rows: list[dict]) -> list[tuple[float, float]]:
    """Return list of (epoch_seconds, pnl_pct) sorted ascending."""
    out: list[tuple[float, float]] = []
    for p in rows:
        if _common.is_ghost_row(p):
            continue
        raw = p.get("pnl_pct")
        if raw is None:
            raw = p.get("pnl")
        try:
            pnl = float(raw) if raw is not None else None
        except (TypeError, ValueError):
            pnl = None
        if pnl is None:
            continue
        ts = (
            _common.parse_ts(p.get("closed_at"))
            or _common.parse_ts(p.get("close_time"))
            or _common.parse_ts(p.get("resolved_at"))
            or _common.parse_ts(p.get("exit_time"))
            or _common.parse_ts(p.get("timestamp"))
            or _common.parse_ts(p.get("created_at"))
        )
        if ts is None:
            continue
        out.append((ts.timestamp(), pnl))
    out.sort()
    return out


def window_stats(pnls: list[float]) -> dict[str, Any]:
    """Compute expectancy/WR/PF/n for a flat pnl window."""
    n = len(pnls)
    if n == 0:
        return {"n": 0, "wr": None, "expectancy": None, "profit_factor": None}
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]
    wr = len(wins) / n
    expectancy = statistics.fmean(pnls)
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    pf = (gross_win / gross_loss) if gross_loss > 0 else None
    return {
        "n": n,
        "wr": round(wr, 4),
        "expectancy": round(expectancy, 6),
        "profit_factor": round(pf, 3) if pf is not None else None,
    }


def rolling_analysis(
    trades: list[tuple[float, float]],
    window_days: int,
    step_days: int,
) -> list[dict[str, Any]]:
    """Compute window stats ending every `step_days`."""
    if not trades:
        return []
    start_ts = trades[0][0]
    end_ts = trades[-1][0]
    window_s = window_days * 86400
    step_s = max(1, step_days) * 86400
    from datetime import datetime, timezone

    samples: list[dict[str, Any]] = []
    t = start_ts + window_s
    while t <= end_ts:
        window_pnls = [pnl for (ts, pnl) in trades if (t - window_s) < ts <= t]
        stats = window_stats(window_pnls)
        stats["window_end"] = datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d")
        samples.append(stats)
        t += step_s
    return samples


def detect_decay_point(samples: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Find earliest sample where expectancy first crosses from positive to negative."""
    prev_positive = False
    for s in samples:
        e = s.get("expectancy")
        if e is None:
            continue
        if e > 0:
            prev_positive = True
        elif e < 0 and prev_positive:
            return s
    return None


def linear_slope(xs: list[float], ys: list[float]) -> float | None:
    """Return least-squares slope of y over x. None if undefined."""
    n = len(xs)
    if n < 2:
        return None
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return None
    return num / den


def analyze(window_days: int, step_days: int) -> dict[str, Any]:
    rows = _common.load_json_list(_common.CLOSED_PICKS)
    trades = extract_trades(rows)
    n = len(trades)
    if n < 2 * window_days:
        return {
            "status": "INSUFFICIENT_DATA",
            "n": n,
            "message": f"Need at least {2 * window_days} dated trades; got {n}",
        }

    samples = rolling_analysis(trades, window_days, step_days)
    if len(samples) < 2:
        return {
            "status": "INSUFFICIENT_WINDOWS",
            "n_trades": n,
            "n_windows": len(samples),
            "message": "Not enough distinct windows to fit a trend",
        }

    # Trend of expectancy
    valid_samples = [s for s in samples if s.get("expectancy") is not None]
    xs = list(range(len(valid_samples)))
    ys = [float(s["expectancy"]) for s in valid_samples]
    slope = linear_slope([float(x) for x in xs], ys)

    first = valid_samples[0]
    last = valid_samples[-1]

    decay = detect_decay_point(valid_samples)

    return {
        "status": "OK",
        "window_days": window_days,
        "step_days": step_days,
        "n_trades": n,
        "n_windows": len(valid_samples),
        "first_window": {
            "end": first["window_end"],
            "n": first["n"],
            "expectancy": first["expectancy"],
            "wr": first["wr"],
            "profit_factor": first["profit_factor"],
        },
        "last_window": {
            "end": last["window_end"],
            "n": last["n"],
            "expectancy": last["expectancy"],
            "wr": last["wr"],
            "profit_factor": last["profit_factor"],
        },
        "expectancy_slope_per_step": round(slope, 6) if slope is not None else None,
        "decay_point": decay,
        "samples": valid_samples,
    }


def format_report(result: dict[str, Any]) -> str:
    lines = ["=== ROLLING EXPECTANCY ==="]
    if result.get("status") != "OK":
        lines.append(f"Status: {result.get('status')}")
        lines.append(f"Message: {result.get('message', '')}")
        return "\n".join(lines)
    lines.append(
        f"Window: {result['window_days']}d  Step: {result['step_days']}d  "
        f"Trades: {result['n_trades']}  Windows: {result['n_windows']}"
    )
    fw, lw = result["first_window"], result["last_window"]
    lines.append("")
    lines.append(
        f"First window ending {fw['end']}: "
        f"n={fw['n']:4d}  WR={fw['wr']}  E={fw['expectancy']:+.4f}%  PF={fw['profit_factor']}"
    )
    lines.append(
        f"Last  window ending {lw['end']}: "
        f"n={lw['n']:4d}  WR={lw['wr']}  E={lw['expectancy']:+.4f}%  PF={lw['profit_factor']}"
    )
    slope = result.get("expectancy_slope_per_step")
    if slope is not None:
        trend = "worsening" if slope < 0 else ("improving" if slope > 0 else "flat")
        lines.append(f"Expectancy slope: {slope:+.6f} per {result['step_days']}d step ({trend})")
    decay = result.get("decay_point")
    if decay:
        lines.append("")
        lines.append(
            f"DECAY POINT detected at window ending {decay['window_end']}: "
            f"expectancy crossed to {decay['expectancy']:+.4f}%"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW_DAYS, dest="window_days")
    parser.add_argument("--step", type=int, default=DEFAULT_STEP_DAYS, dest="step_days")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = analyze(args.window_days, args.step_days)
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(format_report(result))

    out_dir = _common.ensure_out_dir()
    out_path = os.path.join(out_dir, "rolling_expectancy.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)

    if result.get("status") != "OK":
        return 3
    # Flag if the last window is negative expectancy
    last_e = result["last_window"].get("expectancy")
    if last_e is not None and last_e < 0:
        return 2  # decay signal
    return 0


if __name__ == "__main__":
    sys.exit(main())
