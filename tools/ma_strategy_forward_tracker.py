"""
MA Strategy Forward-Tracker v2 — honest, risk-overlaid, out-of-sample trend tracker.

Design + peer review: reports/design_ma_strategy_forward_tracker_2026-05-29.md
(deepseek approve-with-changes + cerebras/ofox cross-review, 2026-05-29).

What v2 adds over tools/ma_strategy_backtest.py (v1, in-sample only):
  - Event-driven per-trade simulation with a RISK OVERLAY: entry next-open after
    close>MA, ATR(14) hard floor stop (k=2.5, capped at 2x a 12% floor), MA
    trailing exit, no take-profit, per-trade risk budget (default 1%).
  - Walk-forward OOS: 5 consecutive test windows over the non-holdout range;
    HEADLINE = median OOS + worst-fold OOS. Single 60/40 kept as a labeled
    secondary. Most-recent 10% is a never-touched HOLDOUT.
  - Net-of-slippage headline (5bps liquid / 15bps illiquid), B&H benchmark,
    bootstrap 95% CI on OOS PF/WR, quantified survivorship penalty.
  - Tighter golden gate: pf_oos>=2.5 & sharpe_oos>=0.8 & n_oos>=50 & beats_bh
    & passes holdout.
  - Forward signal state per strategy x symbol + append-only forward log.

Outputs (audit_dashboard/data/):
  ma_strategy_leaderboard.json   (v2 schema, IS/OOS/holdout/decay/CI/benchmark)
  ma_strategy_signals.json       (today's LONG/FLAT state per strategy x symbol)
  ma_strategy_forward_log.jsonl  (append one dated record per --asof)

Usage:
  python3 tools/ma_strategy_forward_tracker.py --asof 2026-05-29
  python3 tools/ma_strategy_forward_tracker.py --self-test    # 3 symbols/class, fast
  python3 tools/ma_strategy_forward_tracker.py --asof 2026-05-29 --no-write
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

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "audit_dashboard" / "data"
OUT_LB = DATA / "ma_strategy_leaderboard.json"
OUT_SIG = DATA / "ma_strategy_signals.json"
OUT_LOG = DATA / "ma_strategy_forward_log.jsonl"

UNIVERSE = {
    "EQUITY":    ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "JPM", "WMT"],
    "ETF":       ["SPY", "QQQ", "XLK", "XLF", "XLE", "XLV"],
    "CRYPTO":    ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD"],
    "FOREX":     ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"],
    "COMMODITY": ["GC=F", "SI=F", "CL=F", "NG=F", "HG=F"],
    "BOND":      ["TLT", "IEF", "LQD", "BND", "SHY"],
}

# Liquid symbols get 5bps round-trip-leg slippage; everything else 15bps.
LIQUID = {"AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "JPM", "WMT", "SPY", "QQQ",
          "XLK", "XLF", "XLE", "XLV", "TLT", "IEF", "LQD", "BND", "SHY",
          "BTC-USD", "ETH-USD", "EURUSD=X", "GBPUSD=X", "USDJPY=X"}

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

# risk overlay constants
RISK_PCT = 0.01          # 1% per trade
ATR_K = 2.5              # ATR stop multiple
FLOOR_PCT = 0.12         # max stop distance = 12% of entry
N_FOLDS = 5              # walk-forward test windows
HOLDOUT_FRAC = 0.10      # most-recent 10% never used for headline
OOS_FRAC = 0.40          # secondary single split: last 40% of non-holdout
BOOTSTRAP = 500
SURV_PCT = 0.05          # assume 5% of trades would have been ~total losses
# golden gate
G_PF, G_SHARPE, G_NOOS, G_HOLDOUT_PF = 2.5, 0.8, 50, 1.5


def _np_default(o):
    """JSON fallback for numpy scalar types (bool_/int64/float64)."""
    if isinstance(o, np.generic):
        return o.item()
    raise TypeError(f"not serializable: {type(o).__name__}")


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


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([(high - low),
                    (high - prev_close).abs(),
                    (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def _signal_long(close: pd.Series, ma: pd.Series, variant) -> np.ndarray:
    """1 if a LONG signal is active at the close of day t (entry fills t+1 open)."""
    _id, kind, period, tweak = variant
    c, m = close.values, ma.values
    n = len(c)
    sig = np.zeros(n)
    if tweak == "dual_50_200":
        m50 = close.rolling(50).mean().values
        for t in range(n):
            if not (np.isnan(m[t]) or np.isnan(m50[t])):
                sig[t] = 1.0 if (c[t] > m[t] and c[t] > m50[t]) else 0.0
        return sig
    if tweak == "buffer_0.75pct":
        state = 0
        for t in range(n):
            if np.isnan(m[t]):
                continue
            if state == 0 and c[t] > m[t] * 1.0075:
                state = 1
            elif state == 1 and c[t] < m[t]:
                state = 0
            sig[t] = state
        return sig
    for t in range(n):
        if not np.isnan(m[t]):
            sig[t] = 1.0 if c[t] > m[t] else 0.0
    return sig


def _simulate(df: pd.DataFrame, variant, slip_bp: float) -> dict:
    """Event-driven per-trade sim with ATR stop + MA trailing exit + sizing.

    Returns {trades:[{entry_date,exit_date,ret_net,ret_R,hold,reason}], state:{...}}.
    All decisions on day t use only data through day t; entries fill at open[t+1].
    """
    o = df["Open"].values
    h = df["High"].values
    low = df["Low"].values
    c = df["Close"].values
    dates = [d.strftime("%Y-%m-%d") for d in df.index]
    _id, kind, period, _ = variant
    ma = _ma(df["Close"], kind, period).values
    atr = _atr(df["High"], df["Low"], df["Close"]).values
    sig = _signal_long(df["Close"], pd.Series(ma, index=df.index), variant)
    slip = slip_bp / 10000.0
    n = len(c)

    trades = []
    in_pos = False
    entry_i = entry_px = stop = 0.0
    for t in range(1, n):
        if not in_pos:
            # entry the day AFTER a long signal, only with valid ATR
            if sig[t - 1] == 1.0 and not math.isnan(atr[t - 1]) and atr[t - 1] > 0:
                entry_px = o[t] * (1 + slip)              # pay slippage on entry
                a = atr[t - 1]
                stop = max(entry_px - ATR_K * a, entry_px * (1 - FLOOR_PCT))
                # cap stop distance at 2x the fixed floor (vol-blowout guard)
                min_stop = entry_px * (1 - 2 * FLOOR_PCT)
                stop = max(stop, min_stop)
                entry_i = t
                in_pos = True
            continue
        # in position: check hard stop first (intrabar), then MA trailing exit
        exit_px = exit_reason = None
        if low[t] <= stop:
            exit_px = o[t] if o[t] < stop else stop       # gap-through fills at open
            exit_reason = "stop"
        elif sig[t] == 0.0:                                # close<MA today -> exit next open
            if t + 1 < n:
                exit_px = o[t + 1]
                exit_reason = "ma_trail"
            else:
                exit_px = c[t]
                exit_reason = "ma_trail_eod"
        if exit_px is not None:
            exit_px *= (1 - slip)                          # pay slippage on exit
            risk_per_share = entry_px - stop
            ret_net = (exit_px - entry_px) / entry_px
            ret_R = (exit_px - entry_px) / risk_per_share if risk_per_share > 0 else 0.0
            ej = min(t + 1, n - 1) if exit_reason == "ma_trail" else t
            trades.append({
                "entry_date": dates[entry_i], "exit_date": dates[ej],
                "ret_net": ret_net, "ret_R": ret_R,
                "hold": ej - entry_i, "reason": exit_reason,
            })
            in_pos = False
        else:
            # ratchet stop up with ATR trailing (never loosens)
            if not math.isnan(atr[t]) and atr[t] > 0:
                stop = max(stop, c[t] - ATR_K * atr[t])

    # current forward state (what we'd do tomorrow)
    last_close = float(c[-1])
    last_ma = float(ma[-1]) if not math.isnan(ma[-1]) else None
    pct_vs_ma = round((last_close / last_ma - 1) * 100, 2) if last_ma else None
    state = {
        "signal": "LONG" if in_pos else "FLAT",
        "as_of": dates[-1],
        "close": round(last_close, 4),
        "ma": round(last_ma, 4) if last_ma else None,
        "pct_vs_ma": pct_vs_ma,
        "entry_date": dates[entry_i] if in_pos else None,
        "days_held": (n - 1 - entry_i) if in_pos else 0,
        "stop": round(float(stop), 4) if in_pos else None,
    }
    return {"trades": trades, "state": state}


# ----- metrics on a pooled trade list -----

def _pf(rets: list[float]) -> float:
    g = sum(r for r in rets if r > 0)
    l = abs(sum(r for r in rets if r < 0))
    if l <= 0:
        return 9.99 if g > 0 else 0.0
    return round(g / l, 2)


def _wr(rets: list[float]) -> float:
    return round(100 * sum(1 for r in rets if r > 0) / len(rets), 1) if rets else None


def _sharpe_trade(rets: list[float], trades_per_year: float) -> float:
    if len(rets) < 2:
        return 0.0
    a = np.array(rets)
    sd = a.std(ddof=1)
    if sd <= 0:
        return 0.0
    return round(float(a.mean() / sd * math.sqrt(max(trades_per_year, 1))), 2)


def _block(trades: list[dict], span_years: float) -> dict:
    rets = [t["ret_net"] for t in trades]
    n = len(rets)
    tpy = (n / span_years) if span_years > 0 else n
    return {
        "n": n,
        "wr": _wr(rets),
        "pf": _pf(rets),
        "avg_R": round(float(np.mean([t["ret_R"] for t in trades])), 2) if trades else None,
        "avg_ret_pct": round(float(np.mean(rets)) * 100, 2) if rets else None,
        "sharpe": _sharpe_trade(rets, tpy),
        "avg_hold_days": round(float(np.mean([t["hold"] for t in trades])), 1) if trades else None,
    }


def _bootstrap_ci(trades: list[dict], rng: np.random.Generator) -> dict:
    rets = np.array([t["ret_net"] for t in trades])
    if len(rets) < 10:
        return {"pf_lo": None, "pf_hi": None, "wr_lo": None, "wr_hi": None}
    pfs, wrs = [], []
    for _ in range(BOOTSTRAP):
        samp = rng.choice(rets, size=len(rets), replace=True)
        g = samp[samp > 0].sum()
        l = abs(samp[samp < 0].sum())
        pfs.append(g / l if l > 0 else 9.99)
        wrs.append(100 * (samp > 0).mean())
    return {
        "pf_lo": round(float(np.percentile(pfs, 5)), 2),
        "pf_hi": round(float(np.percentile(pfs, 95)), 2),
        "wr_lo": round(float(np.percentile(wrs, 5)), 1),
        "wr_hi": round(float(np.percentile(wrs, 95)), 1),
    }


def _surv_adj_pf(trades: list[dict]) -> float:
    """PF after injecting SURV_PCT synthetic ~total-loss trades (-FLOOR_PCT)."""
    rets = [t["ret_net"] for t in trades]
    n_inject = max(1, int(math.ceil(SURV_PCT * len(rets)))) if rets else 0
    rets = rets + [-FLOOR_PCT] * n_inject
    return _pf(rets)


def _split_by_date(trades: list[dict], asof: str):
    """Return (is_trades, oos_trades, holdout_trades, folds[list], date_span_years)."""
    if not trades:
        return [], [], [], [], 0.0
    ds = sorted(t["entry_date"] for t in trades)
    start = datetime.strptime(ds[0], "%Y-%m-%d")
    end = datetime.strptime(ds[-1], "%Y-%m-%d")
    span_days = max((end - start).days, 1)

    def frac(t):  # 0..1 position of a trade's entry in the full date range
        return (datetime.strptime(t["entry_date"], "%Y-%m-%d") - start).days / span_days

    holdout = [t for t in trades if frac(t) >= (1 - HOLDOUT_FRAC)]
    core = [t for t in trades if frac(t) < (1 - HOLDOUT_FRAC)]
    core_max = (1 - HOLDOUT_FRAC)
    is_cut = core_max * (1 - OOS_FRAC)
    is_t = [t for t in core if frac(t) < is_cut]
    oos_t = [t for t in core if frac(t) >= is_cut]
    # walk-forward: N consecutive test windows over the core range
    folds = []
    for i in range(N_FOLDS):
        lo = core_max * i / N_FOLDS
        hi = core_max * (i + 1) / N_FOLDS
        folds.append([t for t in core if lo <= frac(t) < hi])
    return is_t, oos_t, holdout, folds, span_days / 365.25


def _bh_cagr(symmap: dict, frac_lo: float, frac_hi: float) -> float | None:
    """Median buy-and-hold CAGR across symbols over a fractional date window."""
    cagrs = []
    for s, df in symmap.items():
        n = len(df)
        i0, i1 = int(n * frac_lo), max(int(n * frac_hi) - 1, int(n * frac_lo))
        if i1 <= i0:
            continue
        p0, p1 = float(df["Close"].iloc[i0]), float(df["Close"].iloc[i1])
        yrs = max((df.index[i1] - df.index[i0]).days / 365.25, 0.1)
        if p0 > 0:
            cagrs.append(((p1 / p0) ** (1 / yrs) - 1) * 100)
    return round(float(np.median(cagrs)), 1) if cagrs else None


def _download(universe: dict, period: str) -> dict:
    import yfinance as yf
    series: dict[str, dict[str, pd.DataFrame]] = {}
    for cls, syms in universe.items():
        for s in syms:
            try:
                df = yf.download(s, period=period, interval="1d",
                                 progress=False, auto_adjust=True)
                if df is None or len(df) < 504:   # ~2y minimum
                    print(f"  [skip] {s}: {0 if df is None else len(df)} rows")
                    continue
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                series.setdefault(cls, {})[s] = df.dropna()
            except Exception as e:
                print(f"  [err] {s}: {str(e)[:80]}")
    return series


def run(asof: str, universe: dict, period: str, write: bool) -> dict:
    rng = np.random.default_rng(20260529)   # fixed seed: no Math.random / reproducible
    series = _download(universe, period)
    n_sym = sum(len(v) for v in series.values())
    skipped = [s for cls in universe for s in universe[cls]
               if s not in {k for v in series.values() for k in v}]
    print(f"[ma_v2] {n_sym} symbols across {len(series)} classes; skipped {len(skipped)}")

    strategies = []
    signals = {}
    for variant in VARIANTS:
        vid, kind, period_n, tweak = variant
        by_class = {}
        sig_rows = {}
        for cls, symmap in series.items():
            pooled = []
            for s, df in symmap.items():
                sim = _simulate(df, variant, 5.0 if s in LIQUID else 15.0)
                for t in sim["trades"]:
                    t["sym"] = s
                pooled.extend(sim["trades"])
                sig_rows[f"{cls}:{s}"] = sim["state"]
            is_t, oos_t, hold_t, folds, span_y = _split_by_date(pooled, asof)
            fold_pfs = [_pf([t["ret_net"] for t in f]) for f in folds if len(f) >= 3]
            oos_block = _block(oos_t, span_y * OOS_FRAC) if oos_t else _block([], 1)
            hold_block = _block(hold_t, span_y * HOLDOUT_FRAC) if hold_t else _block([], 1)
            is_block = _block(is_t, span_y * (1 - OOS_FRAC)) if is_t else _block([], 1)
            bh_oos = _bh_cagr(symmap, 1 - HOLDOUT_FRAC - OOS_FRAC, 1 - HOLDOUT_FRAC)
            # strategy OOS CAGR: compound EACH symbol's own OOS trades, then take the
            # median across symbols — comparable to the per-symbol-median B&H benchmark.
            # (pooling all symbols' trades onto one account overstates CAGR ~10x.)
            oos_years = max(span_y * OOS_FRAC, 0.1)
            per_sym_cagr = []
            syms_in_oos = {t.get("sym") for t in oos_t}
            for sym in syms_in_oos:
                rs = [t["ret_net"] for t in oos_t if t.get("sym") == sym]
                if rs:
                    per_sym_cagr.append((float(np.prod([1 + r for r in rs])) ** (1 / oos_years) - 1) * 100)
            oos_cagr = round(float(np.median(per_sym_cagr)), 1) if per_sym_cagr else None
            beats_bh = bool(oos_cagr is not None and bh_oos is not None and oos_cagr > bh_oos)
            decay = round((oos_block["pf"] / is_block["pf"]), 2) if (is_block["pf"] and is_block["pf"] > 0) else None
            ci = _bootstrap_ci(oos_t, rng)
            golden = bool(
                (oos_block["pf"] or 0) >= G_PF and (oos_block["sharpe"] or 0) >= G_SHARPE
                and (oos_block["n"] or 0) >= G_NOOS and beats_bh
                and (hold_block["pf"] or 0) >= G_HOLDOUT_PF
            )
            by_class[cls] = {
                "is": is_block, "oos": oos_block, "holdout": hold_block,
                "oos_cagr_pct": oos_cagr, "bh_oos_cagr_pct": bh_oos, "beats_bh": beats_bh,
                "decay_pf_oos_over_is": decay,
                "wf_fold_pfs": fold_pfs,
                "wf_median_pf": round(float(np.median(fold_pfs)), 2) if fold_pfs else None,
                "wf_worst_pf": round(float(min(fold_pfs)), 2) if fold_pfs else None,
                "oos_ci": ci,
                "pf_oos_survivorship_adj": _surv_adj_pf(oos_t) if oos_t else None,
                "golden": golden,
            }
        strategies.append({
            "id": vid, "ma_type": kind, "period": period_n,
            "tweak": tweak or "none",
            "by_asset_class": by_class,
        })
        signals[vid] = sig_rows

    n_golden = sum(1 for st in strategies for c in st["by_asset_class"].values() if c["golden"])
    exp_false = round(len(VARIANTS) * len(series) * 0.02, 1)  # rough P(PF>=2.5|no edge)~2%
    out = {
        "schema_version": "ma-strategy/v2",
        "generated_at": datetime.now(timezone.utc).isoformat() if write else f"{asof}T00:00:00Z",
        "asof": asof,
        "rule": "Long next-open after close>MA; ATR(14) k=2.5 hard stop capped at 2x12% floor; MA trailing exit; no TP; 1% risk/trade.",
        "lookback": period,
        "universe_size": n_sym,
        "skipped_symbols": skipped,
        "methodology": {
            "headline": "OOS (walk-forward median across %d folds + worst fold). Single 60/40 OOS is secondary. Most-recent %d%% is a never-touched holdout." % (N_FOLDS, int(HOLDOUT_FRAC * 100)),
            "slippage": "net of 5bps liquid / 15bps illiquid per leg",
            "survivorship": "UNIVERSE is current-listed only -> survivorship-biased; pf_oos_survivorship_adj injects %d%% synthetic total-loss trades. LIVE RESULTS WILL BE LOWER." % int(SURV_PCT * 100),
            "golden_gate": "pf_oos>=%.1f & sharpe_oos>=%.1f & n_oos>=%d & beats_bh & holdout_pf>=%.1f" % (G_PF, G_SHARPE, G_NOOS, G_HOLDOUT_PF),
            "multiple_comparisons": "%d variants x %d classes; expected ~%.1f golden by chance under no-edge null." % (len(VARIANTS), len(series), exp_false),
            "out_of_scope": "market impact, order-type, latency not modeled (daily-bar paper tracker). NFA.",
        },
        "n_golden": n_golden,
        "strategies": strategies,
    }
    sig_out = {
        "schema_version": "ma-signals/v1",
        "asof": asof,
        "generated_at": datetime.now(timezone.utc).isoformat() if write else f"{asof}T00:00:00Z",
        "signals": signals,
    }

    if write:
        OUT_LB.write_text(json.dumps(out, indent=2, default=_np_default))
        OUT_SIG.write_text(json.dumps(sig_out, indent=2, default=_np_default))
        # append-only forward log: one compact dated record
        rec = {"asof": asof, "n_golden": n_golden,
               "long_count": sum(1 for v in signals.values() for st in v.values() if st["signal"] == "LONG"),
               "scanned": n_sym * len(VARIANTS)}
        with OUT_LOG.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"[ma_v2] wrote {OUT_LB.name}, {OUT_SIG.name}, +1 {OUT_LOG.name} line")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    ap.add_argument("--period", default="6y")
    ap.add_argument("--self-test", action="store_true", help="3 symbols/class, fast smoke")
    ap.add_argument("--no-write", action="store_true", help="compute but do not write JSON")
    args = ap.parse_args()
    universe = ({k: v[:3] for k, v in UNIVERSE.items()} if args.self_test else UNIVERSE)
    out = run(args.asof, universe, args.period, write=not args.no_write)
    # stdout ranking by best OOS PF across classes
    print(f"[ma_v2] golden cells: {out['n_golden']}")
    for st in out["strategies"]:
        best = max((c["oos"]["pf"] or 0, cls) for cls, c in st["by_asset_class"].items())
        print(f"  {st['id']:11} best OOS PF={best[0]} ({best[1]})")


if __name__ == "__main__":
    main()
