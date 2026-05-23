"""Rolling Sharpe + max-drawdown tracker — fills the tail-risk gap.

Why this exists
---------------
The supplement suite already covers mean edge (`wr_posterior`),
multi-testing-corrected risk-adjusted return (`dsr_audit`), and
factor-orthogonal alpha (`factor_attribution`). What it's missing is
**tail-risk** — a strategy can have positive mean PnL and a
respectable Sharpe over the full sample yet be unhold-able because of
unbearable drawdowns.

This module computes a rolling 30-trade Sharpe and rolling 30-trade
max-drawdown for every strategy with at least 30 closed picks. The
output surfaces:

  - `current_sharpe_30`       Sharpe over the most recent 30 trades.
  - `max_drawdown_30`         Worst peak-to-trough loss over any
                              30-trade window in the strategy's history.
  - `worst_window_start_pick_idx`  Where that worst window begins.
  - `sharpe_pct90 / pct10`    Range of historical 30-trade Sharpe.
  - `drawdown_pct90`          90th-percentile worst-window drawdown.

This catches the dispositive "mean edge is fine but I'd never sleep at
night holding this" pattern.

Math
----
- Sharpe = (mean(window) / std(window)) * sqrt(252) (per-trade not
  per-day; this is the conventional Sharpe for trade-frequency PnL).
- Max-drawdown = max over the window of (running_peak_cumulative_pnl
  - cumulative_pnl_t) / (1 + running_peak_cumulative_pnl). Reported as
  a positive percent (5% = 5pp drawdown).

Wiring status: OPT-IN SIDECAR. No production caller. Future PR adds
`Sharpe (rolling)` and `MDD (worst 30)` columns to
`audit_dashboard/template.html` strategy table, sourcing
`tools/data/rolling_sharpe_drawdown_results.json`.

Caveats
-------
1. Like every supplement, fits on closed-pick labels from
   `outcome_resolver.py` — Theme B contamination on FOREX/COMMODITY
   pending the cloud agent's resolver fix.
2. Assumes equal-weight picks. Real PnL would weight by position size,
   which the dashboard payload doesn't carry. The drawdown number is
   therefore the drawdown a UNIFORM-SIZED bettor would experience.
3. Rolling window is fixed at 30 trades. Smaller windows are noisier;
   larger windows hide regime-localised drawdowns. 30 is a defensible
   institutional default.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
PICKS_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO_ROOT / "tools" / "data" / "rolling_sharpe_drawdown_results.json"

DEFAULT_WINDOW = 30
DEFAULT_MIN_N = DEFAULT_WINDOW
TRADING_DAYS = 252.0


def _safe_pnl(pick: dict) -> float | None:
    pnl = pick.get("pnl_pct")
    if pnl is None:
        return None
    try:
        v = float(pnl)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return v


def _parse_iso(s: Any) -> datetime | None:
    if not isinstance(s, str):
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _window_sharpe(window: np.ndarray) -> float:
    """Per-trade Sharpe annualised by sqrt(252). Returns 0 if degenerate."""
    if len(window) < 2:
        return 0.0
    mu = float(np.mean(window))
    sd = float(np.std(window, ddof=1))
    if sd <= 1e-12:
        return 0.0
    return (mu / sd) * math.sqrt(TRADING_DAYS)


def _window_max_drawdown(window: np.ndarray) -> float:
    """Max drawdown in the window as a positive fraction.

    Returns the worst peak-to-trough loss on the cumulative-equity curve
    `(1 + r_1)(1 + r_2)...` — i.e., compounded drawdown.
    """
    if len(window) == 0:
        return 0.0
    # pnl_pct is a percent; convert to fractional return
    rets = window / 100.0
    equity = np.cumprod(1.0 + rets)
    peak = np.maximum.accumulate(equity)
    dd = (peak - equity) / peak
    return float(np.max(dd) * 100.0)  # back to percent


def analyze_strategy(picks: list[dict],
                      window: int = DEFAULT_WINDOW,
                      min_n: int = DEFAULT_MIN_N) -> dict | None:
    """Per-strategy rolling Sharpe + max-drawdown summary.

    Picks are sorted by closed_at when available; otherwise the input
    order is treated as chronological.
    """
    cleaned: list[tuple[datetime | None, float, int]] = []
    for idx, p in enumerate(picks):
        pnl = _safe_pnl(p)
        if pnl is None:
            continue
        ts = _parse_iso(p.get("closed_at") or p.get("opened_at"))
        cleaned.append((ts, pnl, idx))

    if len(cleaned) < min_n:
        return None

    # Sort chronologically — tz-aware now thanks to _parse_iso
    # Tuples without timestamps sort to the front using a min datetime.
    cleaned.sort(key=lambda x: (x[0] is None, x[0] or datetime.min.replace(tzinfo=timezone.utc)))
    pnls = np.array([c[1] for c in cleaned], dtype=float)
    n = len(pnls)

    rolling_sharpe: list[float] = []
    rolling_drawdown: list[float] = []
    for i in range(window - 1, n):
        win = pnls[i - window + 1:i + 1]
        rolling_sharpe.append(_window_sharpe(win))
        rolling_drawdown.append(_window_max_drawdown(win))

    if not rolling_sharpe:
        return None

    rs = np.array(rolling_sharpe)
    rd = np.array(rolling_drawdown)
    worst_idx = int(np.argmax(rd))
    return {
        "n": int(n),
        "window": int(window),
        "n_rolling_windows": int(len(rs)),
        "current_sharpe_30": round(float(rs[-1]), 4),
        "current_drawdown_30": round(float(rd[-1]), 4),
        "max_drawdown_30": round(float(rd[worst_idx]), 4),
        "worst_window_start_pick_idx": int(worst_idx),
        "sharpe_pct10": round(float(np.percentile(rs, 10)), 4),
        "sharpe_median": round(float(np.median(rs)), 4),
        "sharpe_pct90": round(float(np.percentile(rs, 90)), 4),
        "drawdown_pct90": round(float(np.percentile(rd, 90)), 4),
        "drawdown_median": round(float(np.median(rd)), 4),
    }


def analyze_all(picks: list[dict],
                window: int = DEFAULT_WINDOW,
                min_n: int = DEFAULT_MIN_N) -> dict:
    by_strategy: dict[str, list[dict]] = defaultdict(list)
    for p in picks:
        by_strategy[p.get("strategy") or "unknown"].append(p)

    out: list[dict] = []
    for strat, sub in by_strategy.items():
        r = analyze_strategy(sub, window, min_n)
        if r is None:
            continue
        r["strategy"] = strat
        out.append(r)
    out.sort(key=lambda r: -r["max_drawdown_30"])
    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "config": {"window": window, "min_n": min_n,
                   "trading_days_per_year": TRADING_DAYS},
        "n_strategies": len(out),
        "strategies": out,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--window", type=int, default=DEFAULT_WINDOW)
    ap.add_argument("--min-n", type=int, default=DEFAULT_MIN_N)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    with PICKS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data.get("picks", {}).get("recent_closed", [])

    summary = analyze_all(picks, args.window, args.min_n)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    if not args.quiet:
        print(f"strategies analysed: {summary['n_strategies']}")
        print(f"window: {args.window} trades")
        print(f"top 10 by max-drawdown:")
        for r in summary["strategies"][:10]:
            print(f"  {r['strategy'][:35]:<35} "
                  f"max_DD={r['max_drawdown_30']:>6.2f}% "
                  f"sharpe(now)={r['current_sharpe_30']:>6.2f} "
                  f"sharpe_pct10/90={r['sharpe_pct10']:>5.2f}/{r['sharpe_pct90']:<5.2f} "
                  f"n={r['n']}")
        print(f"JSON: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
