#!/usr/bin/env python3
"""
FORWARD-TEST TRACKER — fast elimination vs hold-longer decisions
=================================================================
Implements FORWARD_TEST_PROTOCOL.md as a drop-in tool. For each closed paper
pick it computes the EXCESS vs the class benchmark over the pick's own holding
window, then applies the decision rule at n=30/60.

Decision rule (from the protocol):
  At n=30:
    - % closed trades with excess > 0 < 45%  -> ELIMINATE
    - median excess < 0                        -> ELIMINATE
    - else keep monitoring
  At n=60:
    - Sharpe (weekly) < 0.4                    -> ELIMINATE
    - max drawdown of equity curve > 20%       -> ELIMINATE
    - else HOLD / extend

Benchmarks (per class):
    EQUITY  -> SPY (adjusted closes)
    ETF     -> SPY
    CRYPTO  -> BTC-USD (buy-and-hold)
    BOND    -> 60/40 equity/bond index
    default  -> class index (or SPY fallback)

Usage:
    python3 tools/forward_test_tracker.py --picks paper_ledger.json [--json out.json]
Input pick schema (one per closed trade):
    {symbol, asset_class, entry_date, exit_date, entry_price, exit_price,
     pnl_pct (net of costs), direction}
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

REPO = Path(__file__).resolve().parents[1]

MIN_N_ELIM = 30
PCT_EXCESS_ELIM = 0.45
SHARPE_ELIM = 0.4
DD_ELIM = 0.20
MIN_N_HOLD = 60

# asset_class -> benchmark ticker (buy-and-hold reference)
BENCH = {
    "EQUITY": "SPY",
    "ETF": "SPY",
    "MUTUAL_FUNDS": "SPY",
    "CRYPTO": "BTC-USD",
    "BOND": "BND",
    "COMMODITY": "GLD",
    "FUTURES": "GLD",
    "FOREX": "^DXY",
    "": "SPY",
}


def _f(v):
    try:
        out = float(v)
    except (TypeError, ValueError):
        return None
    return out if out == out else None


def _dt(v):
    try:
        return pd.Timestamp(v).tz_localize(None) if v else None
    except Exception:  # noqa: BLE001
        return None


def load_benchmark(ticker: str, start, end) -> pd.Series:
    px = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    if px.empty:
        return pd.Series(dtype=float)
    close = px["Close"].squeeze()
    return close.dropna()


def bench_return(bench: pd.Series, entry_dt, exit_dt):
    """Return of benchmark over [entry, exit] window (fraction)."""
    a, b = bench.index.searchsorted([entry_dt, exit_dt])
    if b <= a:
        return None
    seg = bench.iloc[a:b]
    if len(seg) < 2:
        return None
    return seg.iloc[-1] / seg.iloc[0] - 1.0


def run(picks, bench_cache):
    # pre-compute the global window so each benchmark is downloaded once, broadly
    entry_dts = [_dt(p.get("entry_date") or p.get("generated_at")) for p in picks]
    exit_dts = [_dt(p.get("exit_date") or p.get("closed_at")) for p in picks]
    entry_dts = [d for d in entry_dts if d is not None]
    exit_dts = [d for d in exit_dts if d is not None]
    if not entry_dts or not exit_dts:
        return {"verdict": "NO_DATA", "n": 0}
    global_start = min(entry_dts) - pd.Timedelta(days=40)
    global_end = max(exit_dts) + pd.Timedelta(days=10)

    rows = []
    for p in picks:
        aclass = (p.get("asset_class") or "").upper()
        bench_ticker = BENCH.get(aclass, BENCH[""])
        sym = p.get("symbol", "")
        entry_dt = _dt(p.get("entry_date") or p.get("generated_at"))
        exit_dt = _dt(p.get("exit_date") or p.get("closed_at"))
        if entry_dt is None or exit_dt is None:
            continue
        pnl = _f(p.get("pnl_pct"))
        if pnl is None:
            continue
        bench = bench_cache.setdefault(bench_ticker, {})
        if "s" not in bench:
            bench["s"] = load_benchmark(bench_ticker, global_start, global_end)
        br = bench_return(bench["s"], entry_dt, exit_dt)
        if br is None:
            continue
        direction = str(p.get("direction", "")).upper()
        bench_pnl = -br * 100.0 if direction in ("SHORT", "SELL", "STRONG_SELL") else br * 100.0
        excess = pnl - bench_pnl
        rows.append({"symbol": sym, "asset_class": aclass, "pnl_pct": pnl,
                     "bench_pnl_pct": round(bench_pnl, 4), "excess_pct": round(excess, 4),
                     "hold_days": int((exit_dt - entry_dt).days)})

    if not rows:
        return {"verdict": "NO_DATA", "n": 0}

    n = len(rows)
    pct_pos = sum(1 for r in rows if r["excess_pct"] > 0) / n
    med_excess = statistics.median(r["excess_pct"] for r in rows)
    # weekly equity curve from excess
    ex = pd.Series([r["excess_pct"] for r in rows])
    sharpe = (ex.mean() / ex.std() * np.sqrt(52)) if ex.std() > 0 else 0.0
    eq = (1 + ex / 100).cumprod()
    dd = float((eq / eq.cummax() - 1).min()) if len(eq) else 0.0

    # decision
    if n >= MIN_N_ELIM and (pct_pos < PCT_EXCESS_ELIM or med_excess < 0):
        verdict = "ELIMINATE_FAST"
        reason = (f"{pct_pos:.0%} excess>0 (<45%)" if pct_pos < PCT_EXCESS_ELIM
                  else f"median excess {med_excess:.2f}% < 0")
    elif n >= MIN_N_HOLD and (sharpe < SHARPE_ELIM or dd < -DD_ELIM):
        verdict = "ELIMINATE_FAST"
        reason = (f"sharpe {sharpe:.2f} < 0.4" if sharpe < SHARPE_ELIM
                  else f"maxDD {dd:.1%} < -20%")
    else:
        verdict = "HOLD_EXTEND" if n >= MIN_N_HOLD else "MONITOR"
        reason = f"need {MIN_N_ELIM} trades for elimination gate (have {n})" if n < MIN_N_ELIM else "consistent excess"

    return {
        "verdict": verdict,
        "reason": reason,
        "n": n,
        "pct_excess_gt_0": round(pct_pos, 4),
        "median_excess_pct": round(med_excess, 4),
        "sharpe_weekly": round(float(sharpe), 3),
        "max_drawdown_pct": round(dd * 100, 2),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--picks", required=True, help="paper ledger JSON (list of closed picks)")
    ap.add_argument("--json", default=str(REPO / "reports/forward_test_tracker.json"))
    a = ap.parse_args()

    picks = json.loads(Path(a.picks).read_text())
    if isinstance(picks, dict):
        picks = picks.get("picks", picks.get("closed", []))
    result = run(picks, {})
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(result, indent=2))
    print(f"FORWARD-TEST verdict: {result['verdict']}  ({result['reason']})")
    print(f"  n={result['n']}  pct_excess>0={result['pct_excess_gt_0']:.0%}  "
          f"median_excess={result['median_excess_pct']:.2f}%  "
          f"sharpe={result['sharpe_weekly']}  maxDD={result['max_drawdown_pct']}%")
    print(f"wrote {a.json}")


if __name__ == "__main__":
    main()
