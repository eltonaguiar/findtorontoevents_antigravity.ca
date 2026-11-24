#!/usr/bin/env python3
"""R5 — backtest audit3's only pre_registered pod, outside its validation window.

POD-EQUITY-BREAKOUT cites H-BABY-EQUITY-VT-PATTERN-SWEEP-001, which lives in
baby_strategies/vt_pattern_sweep.py. Its published validation is:

    window 2021-04 .. 2026-04 (5 years), 13 symbols, 245 trades
    PF 1.479, WR 50.2%, Sharpe 0.747, MaxDD -18.1%, CAGR +9.9%

Five years of US mega-cap bull market. The question that matters for funding is
not "does it work in its own window" — it does, by construction — but:

    DOES THE EDGE EXIST BEFORE 2021?

So this runs the REAL strategy code (imported, not re-implemented) over the
longest history free daily data allows, then splits the result at 2021-01-01 and
reports both halves with honest costs.

Deliberately conservative choices
  * Entry at the NEXT bar's OPEN. The runtime path reports entry_price at the
    signal close; using that would be a same-bar fill and is not investable.
  * Stop checked on the entry bar too.
  * If one bar's range covers both stop and target, the STOP is assumed first.
  * Costs charged on both legs at the hypothesis's own stated 25bp equity
    slippage, and also at 4bp for reference.
  * Every window reports its own n. No pooling across windows.

Usage: python3 tools/pod_equity_breakout_backtest.py
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "reports" / "pod_equity_breakout"

SYMBOLS = ["SPY", "QQQ", "XLK", "XLF", "XLE", "XLV", "XLY",
           "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN"]
COST_BP_PRIMARY = 25.0      # the hypothesis's own stated equity slippage
COST_BP_REF = 4.0           # commission-free reference
SPLIT = pd.Timestamp("2021-01-01")
WINDOW = 420                # bars fed to the strategy each step


def fetch_daily(sym: str) -> pd.DataFrame | None:
    import yfinance as yf
    try:
        d = yf.download(sym, period="max", interval="1d", auto_adjust=True,
                        progress=False, threads=False)
        if d is None or len(d) == 0:
            return None
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
        d = d.rename(columns=str.lower)
        need = {"open", "high", "low", "close"}
        if not need.issubset(d.columns):
            return None
        d.index = pd.to_datetime(d.index).tz_localize(None)
        return d[["open", "high", "low", "close"]].dropna()
    except Exception:
        return None


def backtest_symbol(sym: str, strat, df: pd.DataFrame, tie_break: str = "stop") -> list[dict]:
    """Walk forward. One position at a time. Entry at next bar OPEN.

    tie_break='stop'  -> when one bar's range covers BOTH stop and target, assume
                         the STOP filled first (conservative, and the only
                         defensible assumption on daily bars).
    tie_break='target'-> assume the TARGET filled first (optimistic). Provided
                         ONLY to quantify how much of a result is a sequencing
                         assumption rather than a signal. Never use for a verdict.
    """
    trades = []
    n = len(df)
    start = 260                      # SMA200 + buffer
    busy_until = -1
    o, h, l, c = (df[k].values for k in ("open", "high", "low", "close"))
    idx = df.index

    for i in range(start, n - 2):
        if i <= busy_until:
            continue
        win = df.iloc[max(0, i - WINDOW + 1):i + 1]
        try:
            sigs = strat.generate_signals(win, symbol=sym)
        except Exception:
            continue
        if not sigs:
            continue
        s = sigs[0]
        if str(getattr(s, "direction", "")).upper() not in ("LONG", "BUY"):
            continue
        entry = o[i + 1]
        if not np.isfinite(entry) or entry <= 0:
            continue
        tp = float(getattr(s, "take_profit", 0) or 0)
        sl = float(getattr(s, "stop_loss", 0) or 0)
        if not (tp > entry > sl > 0):
            continue
        exitp, exit_bar, reason = None, None, None
        max_hold = 60                # ~3 months cap; avg hold was 6.4 days
        for j in range(i + 1, min(i + 1 + max_hold, n)):
            hit_sl = l[j] <= sl
            hit_tp = h[j] >= tp
            if tie_break == "target":
                if hit_tp:
                    exitp, exit_bar, reason = tp, j, "TP"
                    break
                if hit_sl:
                    exitp, exit_bar, reason = sl, j, "SL"
                    break
            else:
                if hit_sl:           # pessimistic: stop wins ties
                    exitp, exit_bar, reason = sl, j, "SL"
                    break
                if hit_tp:
                    exitp, exit_bar, reason = tp, j, "TP"
                    break
        if exitp is None:
            exit_bar = min(i + max_hold, n - 1)
            exitp, reason = c[exit_bar], "TIMEOUT"
        busy_until = exit_bar
        trades.append({
            "symbol": sym, "entry_date": idx[i + 1].strftime("%Y-%m-%d"),
            "exit_date": idx[exit_bar].strftime("%Y-%m-%d"),
            "gross": (exitp - entry) / entry, "reason": reason,
            "bars": exit_bar - i,
        })
    return trades


def summarize(tr: list[dict], cost_bp: float, label: str) -> dict:
    if not tr:
        return {"label": label, "n": 0}
    g = np.array([t["gross"] for t in tr])
    net = g - 2 * cost_bp / 1e4
    wins, losses = net[net > 0], net[net <= 0]
    pf = (wins.sum() / abs(losses.sum())) if len(losses) and losses.sum() != 0 else float("inf")
    sd = net.std(ddof=1) if len(net) > 1 else 0.0
    t_stat = (net.mean() / (sd / math.sqrt(len(net)))) if sd else float("nan")
    # per-trade Sharpe annualised at ~49 signals/yr universe-wide
    sharpe = (net.mean() / sd * math.sqrt(49)) if sd else float("nan")
    return {"label": label, "n": int(len(net)),
            "gross_pct": float(g.mean() * 100),
            "net_pct": float(net.mean() * 100),
            "total_net_pct": float(net.sum() * 100),
            "wr_pct": float(100 * (net > 0).mean()),
            "pf": float(pf), "t": float(t_stat), "sharpe_ann": float(sharpe),
            "exit_mix": {r: sum(1 for x in tr if x["reason"] == r)
                         for r in ("TP", "SL", "TIMEOUT")}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cost", type=float, default=COST_BP_PRIMARY)
    ap.add_argument("--tie-break", choices=["stop", "target"], default="stop",
                    help="intrabar sequencing assumption; 'target' is optimistic and "
                         "exists only to quantify the effect of the assumption")
    a = ap.parse_args()
    from baby_strategies.vt_pattern_sweep import VTPatternSweepStrategy
    strat = VTPatternSweepStrategy()
    print(f"tie-break assumption: {a.tie_break.upper()}-first"
          + ("   [OPTIMISTIC — diagnostic only]" if a.tie_break == "target" else "   [conservative]"),
          flush=True)

    all_tr = []
    per_sym = {}
    for sym in SYMBOLS:
        df = fetch_daily(sym)
        if df is None or len(df) < 300:
            print(f"  {sym}: no data"); continue
        tr = backtest_symbol(sym, strat, df, tie_break=a.tie_break)
        per_sym[sym] = {"n": len(tr), "window": f"{df.index[0].date()}..{df.index[-1].date()}"}
        all_tr.extend(tr)
        print(f"  {sym:<6} bars={len(df):>5} {df.index[0].date()}..{df.index[-1].date()} "
              f"-> {len(tr):>3} trades")

    if not all_tr:
        print("\nNO TRADES — the strategy did not fire on this data/window combination")
        return 2

    print(f"\n=== R5: POD-EQUITY-BREAKOUT real code, cost {a.cost:.0f}bp/side ===")
    rows = []
    full = summarize(all_tr, a.cost, "ALL history")
    pre = summarize([t for t in all_tr if t["entry_date"] < "2021-01-01"], a.cost, "BEFORE 2021 (out of validation sample)")
    val = summarize([t for t in all_tr if t["entry_date"] >= "2021-01-01"], a.cost, "2021+ (their validation window)")
    for r in (full, pre, val):
        rows.append(r)
        if r["n"] == 0:
            print(f"\n  {r['label']:<45} n=0  — no trades")
            continue
        print(f"\n  {r['label']:<45} n={r['n']:>4}")
        print(f"    gross {r['gross_pct']:>+7.3f}%  net {r['net_pct']:>+7.3f}%  "
              f"total net {r['total_net_pct']:>+8.2f}%  WR {r['wr_pct']:>5.1f}%  "
              f"PF {r['pf']:>5.2f}  t {r['t']:>+6.2f}  Sharpe~{r['sharpe_ann']:>5.2f}")
        print(f"    exits: {r['exit_mix']}")

    print(f"\n=== VERDICT ===")
    if pre["n"] >= 30:
        verdict = ("EDGE SURVIVES OUT OF SAMPLE" if pre["net_pct"] > 0 and pre["t"] > 1.5
                   else "EDGE DOES NOT SURVIVE OUT OF SAMPLE")
        print(f"  pre-2021: n={pre['n']}, net {pre['net_pct']:+.3f}%/trade, t={pre['t']:+.2f} -> {verdict}")
    else:
        print(f"  pre-2021 sample too small (n={pre['n']}) to judge")
    print(f"  in-sample 2021+: n={val['n']}, net {val['net_pct']:+.3f}%/trade, t={val['t']:+.2f}")
    print(f"  published claim: n=245, Sharpe 0.747, PF 1.479, WR 50.2% (2021-04..2026-04)")
    print(f"  this run reproduces: n={val['n']}, Sharpe~{val['sharpe_ann']:.2f}, "
          f"PF {val['pf']:.2f}, WR {val['wr_pct']:.1f}%")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pod_equity_breakout_backtest.json").write_text(json.dumps({
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis": "H-BABY-EQUITY-VT-PATTERN-SWEEP-001",
        "source": "baby_strategies/vt_pattern_sweep.py (imported, not reimplemented)",
        "symbols": SYMBOLS, "cost_bp_per_side": a.cost,
        "fill": "next bar open", "tie_break": a.tie_break,
        "windows": rows, "per_symbol": per_sym,
        "published_claim": {"n": 245, "sharpe": 0.747, "pf": 1.479,
                            "wr": 50.2, "mdd": -18.1, "period": "2021-04..2026-04"},
    }, indent=1))
    print(f"\nwrote {OUT/'pod_equity_breakout_backtest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
