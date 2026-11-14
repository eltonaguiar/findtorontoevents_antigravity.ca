#!/usr/bin/env python3
"""Is the EQUITY class alpha, or is it the market? Per-pick excess vs SPY.

The per-class cost gate (tools/per_class_cost_gate.py) allowed EQUITY at 3.23x
round-trip cost, but its t-statistic against ZERO was 1.52 — not significant even
before asking whether the picks beat simply holding the index. EQUITY is the one
class the whole focus decision rests on, so the honest test is not "is mean PnL
> 0" but "is mean PnL > what SPY did over the same calendar window, per pick".

PRE-REGISTERED GATE — fixed before this file was run, not tuned after:

    PASS (alpha) requires ALL of:
      G1  n >= 100 picks with a usable entry and exit timestamp
      G2  mean excess return > 0
      G3  two-sided t-statistic of the excess >= 2.0
      G4  mean excess > the class round-trip cost (a gross edge the cost eats
          is not an edge)

    Anything else is reported as NO_ALPHA / BETA, including a high t-stat whose
    mean is smaller than costs (G2/G3 can pass while G4 fails — that is a
    break-even result and must not be presented as an edge).

Benchmark construction:
  Each pick is paired with SPY's return over that pick's OWN holding window
  (entry timestamp -> exit timestamp), not a single buy-and-hold figure. A short
  pick is benchmarked against -SPY, because shorting the index is its
  opportunity cost. Using adjusted closes means dividends are included, which is
  the harder benchmark — deliberately.

Usage:
    python3 tools/equity_vs_spy.py --payload /tmp/peercheck/dashboard_payload.json
    python3 tools/equity_vs_spy.py --payload X --json out.json --class EQUITY
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

DEFAULT_COST_PCT = 0.10  # round-trip, % of notional, when the gate config is unreadable
MIN_N = 100
MIN_T = 2.0
BENCHMARK = "SPY"


def _f(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        out = float(v)
    except (TypeError, ValueError):
        return None
    return out if out == out else None


def _parse_dt(v: Any) -> Optional[datetime]:
    if not v:
        return None
    s = str(v).strip()
    if not s:
        return None
    iso = (s[:-1] + "+00:00") if s.endswith("Z") else s
    try:
        dt = datetime.fromisoformat(iso)
    except (ValueError, TypeError):
        # Date-only entries ("2026-11-13") are common in the ledger.
        try:
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_rows(path: str) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        picks = data.get("picks")
        if isinstance(picks, dict) and isinstance(picks.get("recent_closed"), list):
            return [r for r in picks["recent_closed"] if isinstance(r, dict)]
        for k in ("recent_closed", "closed_picks"):
            if isinstance(data.get(k), list):
                return [r for r in data[k] if isinstance(r, dict)]
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []


def round_trip_cost_pct() -> float:
    """Class round-trip cost from the cost-gate config, else a stated default."""
    try:
        with open("config/per_class_cost_gate.json", encoding="utf-8") as fh:
            cfg = json.load(fh)
        for key in ("round_trip_cost_pct", "cost_pct", "cost_pct_by_class"):
            node = cfg.get(key)
            if isinstance(node, dict) and _f(node.get("EQUITY")) is not None:
                return float(node["EQUITY"])
            if _f(node) is not None:
                return float(node)
        cls = cfg.get("classes") or {}
        eq = cls.get("EQUITY") or {}
        for key in ("round_trip_cost_pct", "cost_pct"):
            if _f(eq.get(key)) is not None:
                return float(eq[key])
    except Exception:
        pass
    return DEFAULT_COST_PCT


def fetch_spy_closes(start: datetime, end: datetime) -> List[tuple]:
    """[(date, adjusted_close)] covering [start, end] with a day of slack."""
    try:
        import yfinance as yf
    except ImportError:
        return []
    hist = yf.Ticker(BENCHMARK).history(
        start=(start - timedelta(days=5)).date(),
        end=(end + timedelta(days=5)).date(),
        interval="1d",
        auto_adjust=True,
    )
    if hist is None or hist.empty:
        return []
    out = []
    for idx, row in hist.iterrows():
        try:
            dt = idx.to_pydatetime()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            out.append((dt.astimezone(timezone.utc).date(), float(row["Close"])))
        except (TypeError, ValueError, KeyError):
            continue
    out.sort(key=lambda t: t[0])
    return out


def benchmark_return(closes: Sequence[tuple], entry: datetime, exit_: datetime) -> Optional[float]:
    """SPY % return from the last close on/before ``entry`` to the same for ``exit``.

    Using the last close at/before each timestamp keeps the pairing causal: no
    look-ahead into a close that had not printed when the pick was entered.
    """
    if not closes:
        return None
    ed, xd = entry.date(), exit_.date()
    start = None
    for d, c in closes:
        if d <= ed:
            start = c
        else:
            break
    end = None
    for d, c in closes:
        if d <= xd:
            end = c
        else:
            break
    if not start or not end:
        return None
    return (end - start) / start * 100.0


def t_stat(vals: Sequence[float]) -> Optional[float]:
    n = len(vals)
    if n < 2:
        return None
    sd = statistics.stdev(vals)
    if sd == 0:
        return None
    return statistics.mean(vals) / (sd / math.sqrt(n))


def evaluate(rows: List[Dict[str, Any]], cls: str, cost_pct: float) -> Dict[str, Any]:
    picks = [r for r in rows if str(r.get("asset_class", "")).upper() == cls.upper()]
    usable: List[Dict[str, Any]] = []
    skipped = {"no_time": 0, "no_pnl": 0, "no_bench": 0}

    dates = [d for d in (_parse_dt(r.get("timestamp") or r.get("entry_time")) for r in picks) if d]
    if not dates:
        return {"error": "no parsable entry timestamps", "n_class_rows": len(picks)}
    closes = fetch_spy_closes(min(dates), max(dates))

    for r in picks:
        pnl = _f(r.get("pnl_pct"))
        entry = _parse_dt(r.get("timestamp") or r.get("entry_time"))
        exit_ = _parse_dt(r.get("closed_at") or r.get("exit_time"))
        if not entry or not exit_:
            skipped["no_time"] += 1
            continue
        if pnl is None:
            skipped["no_pnl"] += 1
            continue
        bench = benchmark_return(closes, entry, exit_)
        if bench is None:
            skipped["no_bench"] += 1
            continue
        short = str(r.get("direction") or "LONG").upper() in ("SHORT", "SELL")
        bench = -bench if short else bench
        usable.append({
            "symbol": r.get("symbol"),
            "pnl_pct": pnl,
            "bench_pct": round(bench, 4),
            "excess_pct": round(pnl - bench, 4),
            "hold_days": round((exit_ - entry).total_seconds() / 86400.0, 2),
            "source_system": r.get("source_system"),
        })

    excess = [u["excess_pct"] for u in usable]
    mean_exc = round(statistics.mean(excess), 4) if excess else None
    tval = t_stat(excess)
    checks = {
        "G1_n_ge_100": len(usable) >= MIN_N,
        "G2_mean_excess_gt_0": mean_exc is not None and mean_exc > 0,
        "G3_t_ge_2": tval is not None and tval >= MIN_T,
        "G4_excess_gt_cost": mean_exc is not None and mean_exc > cost_pct,
    }
    return {
        "class": cls.upper(),
        "benchmark": BENCHMARK,
        "n_class_rows": len(picks),
        "n_usable": len(usable),
        "skipped": skipped,
        "cost_pct_used": cost_pct,
        "mean_pnl_pct": round(statistics.mean([u["pnl_pct"] for u in usable]), 4) if usable else None,
        "mean_bench_pct": round(statistics.mean([u["bench_pct"] for u in usable]), 4) if usable else None,
        "mean_excess_pct": mean_exc,
        "median_excess_pct": round(statistics.median(excess), 4) if excess else None,
        "t_stat": round(tval, 4) if tval is not None else None,
        "win_rate_vs_bench_pct": round(100 * sum(1 for e in excess if e > 0) / len(excess), 2) if excess else None,
        "mean_hold_days": round(statistics.mean([u["hold_days"] for u in usable]), 2) if usable else None,
        "checks": checks,
        "verdict": "PASS_ALPHA" if all(checks.values()) else "NO_ALPHA_BETA",
        "spy_closes_loaded": len(closes),
        "sample": usable[:8],
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--payload", required=True)
    ap.add_argument("--class", dest="cls", default="EQUITY")
    ap.add_argument("--json", help="write the full result here")
    args = ap.parse_args(argv)

    rows = load_rows(args.payload)
    if not rows:
        print(f"no closed rows in {args.payload}", file=sys.stderr)
        return 2
    cost = round_trip_cost_pct()
    res = evaluate(rows, args.cls, cost)
    if res.get("error"):
        print(res["error"], file=sys.stderr)
        return 2

    print(f"{res['class']} vs {BENCHMARK} — per-pick excess over the pick's own holding window")
    print(f"class rows {res['n_class_rows']}   usable pairs {res['n_usable']}   skipped {res['skipped']}")
    print(f"SPY closes loaded: {res['spy_closes_loaded']}   cost hurdle {res['cost_pct_used']:.2f}%   "
          f"mean hold {res['mean_hold_days']}d")
    print()
    print(f"{'':<22}{'mean':>10}{'median':>10}{'t':>8}")
    print(f"{'strategy pnl %':<22}{res['mean_pnl_pct']:>10.4f}{'':>10}{'':>8}")
    print(f"{'SPY same window %':<22}{res['mean_bench_pct']:>10.4f}{'':>10}{'':>8}")
    print(f"{'excess %':<22}{res['mean_excess_pct']:>10.4f}{res['median_excess_pct']:>10.4f}"
          f"{(res['t_stat'] or 0):>8.2f}")
    print(f"\nbeat-SPY rate: {res['win_rate_vs_bench_pct']}%")
    print("\ngate (pre-registered):")
    for k, v in res["checks"].items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    print(f"\nVERDICT: {res['verdict']}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=2, sort_keys=True, default=str)
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
