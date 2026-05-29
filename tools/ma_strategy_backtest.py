"""
200-day (and variants) moving-average TREND strategy backtest, per asset class.

Rule (per user 2026-05-29): long the NEXT trading day after the daily close
crosses ABOVE a moving average; go flat when the daily close is below it. No
fixed TP — the MA is the trailing exit. We report raw strategy stats; the
1-2%/trade risk overlay is a sizing wrapper, not part of the signal.

Variants (peer-reviewed via /PeerReviewSwarmOptions, grok-4.3):
  Classic200  SMA 200            benchmark long-term trend
  EMA200      EMA 200            user-requested EMA@200
  HMA200      HMA 200            user-requested Hull@200 (low lag)
  RespEMA50   EMA 50             faster medium-term
  LagHull16   HMA 16             low-lag short-term
  MedHull50   HMA 50             balanced low-lag
  DualCross   SMA 50 & 200       long only when close > BOTH (confirmation)
  Buff200     SMA 200 +0.75%     0.75% entry buffer to cut whipsaws

Output: audit_dashboard/data/ma_strategy_leaderboard.json
  { generated_at, rule, universe_size, strategies:[ { id, ma_type, period, tweak,
    overall:{n_trades,wr,pf,total_return_pct,cagr_pct,max_dd_pct,sharpe,avg_hold_days},
    by_asset_class:{ CLASS:{...same...}, ... } } ] }

Usage:  python3 tools/ma_strategy_backtest.py            # full run (network: yfinance)
        python3 tools/ma_strategy_backtest.py --quick    # 3 symbols/class for a fast smoke
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "audit_dashboard" / "data" / "ma_strategy_leaderboard.json"

UNIVERSE = {
    "EQUITY":    ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "JPM", "WMT"],
    "ETF":       ["SPY", "QQQ", "XLK", "XLF", "XLE", "XLV"],
    "CRYPTO":    ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD"],
    "FOREX":     ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"],
    "COMMODITY": ["GC=F", "SI=F", "CL=F", "NG=F", "HG=F"],
    "BOND":      ["TLT", "IEF", "LQD", "BND", "SHY"],
}

# variant spec: (id, ma_type, period, tweak)
VARIANTS = [
    ("Classic200", "SMA", 200, None),
    ("EMA200", "EMA", 200, None),
    ("HMA200", "HMA", 200, None),
    ("RespEMA50", "EMA", 50, None),
    ("LagHull16", "HMA", 16, None),
    ("MedHull50", "HMA", 50, None),
    ("DualCross", "SMA", 200, "dual_50_200"),
    ("Buff200", "SMA", 200, "buffer_0.75pct"),
]


def _wma(s: pd.Series, n: int) -> pd.Series:
    w = np.arange(1, n + 1)
    return s.rolling(n).apply(lambda x: np.dot(x, w) / w.sum(), raw=True)


def _ma(close: pd.Series, kind: str, period: int) -> pd.Series:
    if kind == "SMA":
        return close.rolling(period).mean()
    if kind == "EMA":
        return close.ewm(span=period, adjust=False).mean()
    if kind == "HMA":
        half = max(1, period // 2)
        sq = max(1, int(round(math.sqrt(period))))
        return _wma(2 * _wma(close, half) - _wma(close, period), sq)
    raise ValueError(kind)


def _positions(close: pd.Series, variant) -> np.ndarray:
    """Daily position (1 long / 0 flat) for day t, applied to t->t+1 return."""
    _id, kind, period, tweak = variant
    ma = _ma(close, kind, period)
    c = close.values
    m = ma.values
    n = len(c)
    pos = np.zeros(n)
    if tweak == "dual_50_200":
        m50 = close.rolling(50).mean().values
        for t in range(n):
            if not (np.isnan(m[t]) or np.isnan(m50[t])):
                pos[t] = 1.0 if (c[t] > m[t] and c[t] > m50[t]) else 0.0
        return pos
    if tweak == "buffer_0.75pct":
        state = 0
        for t in range(n):
            if np.isnan(m[t]):
                continue
            if state == 0 and c[t] > m[t] * 1.0075:
                state = 1
            elif state == 1 and c[t] < m[t]:
                state = 0
            pos[t] = state
        return pos
    for t in range(n):
        if not np.isnan(m[t]):
            pos[t] = 1.0 if c[t] > m[t] else 0.0
    return pos


def _backtest_symbol(close: pd.Series, variant) -> dict | None:
    pos = _positions(close, variant)
    ret = close.pct_change().fillna(0.0).values
    # enter NEXT day: yesterday's position earns today's return
    held = np.zeros(len(pos))
    held[1:] = pos[:-1]
    strat_ret = held * ret
    if held.sum() < 5:
        return None
    # equity + drawdown
    eq = np.cumprod(1 + strat_ret)
    peak = np.maximum.accumulate(eq)
    max_dd = float(((eq - peak) / peak).min() * 100)
    days = len(strat_ret)
    total_ret = float((eq[-1] - 1) * 100)
    cagr = float(((eq[-1]) ** (252 / max(days, 1)) - 1) * 100)
    vol = strat_ret.std()
    sharpe = float((strat_ret.mean() / vol * math.sqrt(252)) if vol > 0 else 0.0)
    # per-trade episodes (contiguous held runs)
    trades = []
    holds = []
    i = 1
    while i < len(held):
        if held[i] == 1 and held[i - 1] == 0:
            j = i
            while j < len(held) and held[j] == 1:
                j += 1
            seg = strat_ret[i:j]
            tr = float(np.prod(1 + seg) - 1)
            trades.append(tr)
            holds.append(j - i)
            i = j
        else:
            i += 1
    if not trades:
        return None
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t < 0]
    g = sum(wins)
    l = abs(sum(losses))
    pf = (g / l) if l > 0 else (9.99 if g > 0 else 0.0)
    return {
        "n_trades": len(trades),
        "wr": round(100 * len(wins) / len(trades), 1),
        "pf": round(pf, 2),
        "total_return_pct": round(total_ret, 1),
        "cagr_pct": round(cagr, 1),
        "max_dd_pct": round(max_dd, 1),
        "sharpe": round(sharpe, 2),
        "avg_hold_days": round(float(np.mean(holds)), 1),
    }


def _agg(rows: list[dict]) -> dict:
    if not rows:
        return {"n_trades": 0, "wr": None, "pf": None, "total_return_pct": None,
                "cagr_pct": None, "max_dd_pct": None, "sharpe": None, "avg_hold_days": None, "n_symbols": 0}
    nt = sum(r["n_trades"] for r in rows)

    def wmean(key):
        return round(sum(r[key] * r["n_trades"] for r in rows) / nt, 2) if nt else None
    return {
        "n_trades": nt,
        "n_symbols": len(rows),
        "wr": wmean("wr"),
        "pf": round(float(np.median([r["pf"] for r in rows])), 2),
        "total_return_pct": round(float(np.median([r["total_return_pct"] for r in rows])), 1),
        "cagr_pct": round(float(np.median([r["cagr_pct"] for r in rows])), 1),
        "max_dd_pct": round(float(np.median([r["max_dd_pct"] for r in rows])), 1),
        "sharpe": round(float(np.median([r["sharpe"] for r in rows])), 2),
        "avg_hold_days": wmean("avg_hold_days"),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--period", default="6y")
    args = ap.parse_args()

    universe = {k: (v[:3] if args.quick else v) for k, v in UNIVERSE.items()}
    # download once per symbol; run all variants on it
    series: dict[str, dict[str, pd.Series]] = {}
    for cls, syms in universe.items():
        for s in syms:
            try:
                df = yf.download(s, period=args.period, interval="1d", progress=False, auto_adjust=True)
                if df is None or len(df) < 260:
                    print(f"  [skip] {s}: {0 if df is None else len(df)} rows")
                    continue
                close = df["Close"]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                series.setdefault(cls, {})[s] = close.dropna()
            except Exception as e:
                print(f"  [err] {s}: {str(e)[:80]}")
    n_sym = sum(len(v) for v in series.values())
    print(f"[ma_bt] downloaded {n_sym} symbols across {len(series)} classes")

    strategies = []
    for variant in VARIANTS:
        vid, kind, period, tweak = variant
        by_class = {}
        all_rows = []
        for cls, symmap in series.items():
            rows = []
            for s, close in symmap.items():
                r = _backtest_symbol(close, variant)
                if r:
                    rows.append(r)
            by_class[cls] = _agg(rows)
            all_rows.extend(rows)
        strategies.append({
            "id": vid, "ma_type": kind, "period": period,
            "tweak": tweak or "none",
            "overall": _agg(all_rows),
            "by_asset_class": by_class,
        })

    out = {
        "schema_version": "ma-strategy/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rule": "Long next day after daily close > MA; flat when close < MA. No TP (MA = trailing exit). Risk overlay 1-2%/trade.",
        "lookback": args.period,
        "universe_size": n_sym,
        "note": "WR/PF are per-trade (each long episode). Aggregates: WR=trade-weighted mean; PF/return/DD/Sharpe=median across symbols. NFA.",
        "strategies": strategies,
    }
    OUT.write_text(json.dumps(out, indent=2))
    print(f"[ma_bt] wrote {OUT.relative_to(REPO)} — {len(strategies)} strategies, {n_sym} symbols")
    # quick stdout ranking
    ranked = sorted(strategies, key=lambda x: (x["overall"]["pf"] or 0), reverse=True)
    for s in ranked:
        o = s["overall"]
        print(f"  {s['id']:11} {s['ma_type']}{s['period']:<4} n={o['n_trades']:4} WR={o['wr']}% PF={o['pf']} CAGR={o['cagr_pct']}% MDD={o['max_dd_pct']}% Sharpe={o['sharpe']}")


if __name__ == "__main__":
    main()
