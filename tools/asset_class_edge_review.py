#!/usr/bin/env python3
"""Per-asset-class edge review with a purged train/test protocol.

For each asset class it:

  1. downloads daily bars for a universe of liquid symbols,
  2. computes features from PAST data only (no same-bar outcome leakage),
  3. defines the event up front (forward H-day return >= T, class-specific),
  4. searches features on the TRAIN slice (first 70% of dates), BH-adjusted,
  5. freezes the top-decile cut from train and evaluates it on the TEST slice
     (last 30%, with an H-day purge gap so overlapping windows cannot leak),
  6. reports train lift vs OOS lift, the OOS Wilson CI, and a binomial p that
     the OOS top-decile rate exceeds the OOS base rate,
  7. lists this week's top movers per class with their feature fingerprint.

Nothing here is a verdict. A pattern that clears OOS still has to clear the
audit3 forward gate on live data before it is treated as an edge.

Usage
    python3 tools/asset_class_edge_review.py
    python3 tools/asset_class_edge_review.py --period 5y --json-out reports/acr.json
    python3 tools/asset_class_edge_review.py --classes CRYPTO FOREX
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.skyrocket_reverse_eng import bh_adjust, permutation_p, spearman, wilson  # noqa: E402

CACHE = ROOT / "data" / "cache" / "asset_class_review"

UNIVERSES: dict[str, list[str]] = {
    "CRYPTO": ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD", "DOGE-USD",
               "AVAX-USD", "LINK-USD", "DOT-USD", "LTC-USD", "BNB-USD", "XLM-USD",
               "ATOM-USD", "NEAR-USD", "UNI-USD", "ETC-USD"],
    "STOCK": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD",
              "JPM", "XOM", "WMT", "COST", "NFLX", "DIS", "BA", "PFE",
              "INTC", "CRM", "ORCL", "KO"],
    "ETF": ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV",
            "GLD", "SLV", "EEM", "EFA", "ARKK", "SOXX"],
    "FOREX": ["EURUSD=X", "GBPUSD=X", "JPY=X", "AUDUSD=X", "USDCAD=X",
              "USDCHF=X", "NZDUSD=X", "EURJPY=X", "GBPJPY=X", "EURGBP=X"],
    "FUTURES": ["ES=F", "NQ=F", "YM=F", "GC=F", "SI=F", "CL=F",
                "NG=F", "HG=F", "ZC=F", "ZS=F"],
    "BOND": ["TLT", "IEF", "SHY", "LQD", "HYG", "AGG", "JNK", "TIP", "BND", "TLH"],
}

# Forward window (days) and event threshold (fractional return) per class.
EVENT: dict[str, tuple[int, float]] = {
    "CRYPTO": (5, 0.15),
    "STOCK": (10, 0.10),
    "ETF": (10, 0.05),
    "FOREX": (5, 0.03),
    "FUTURES": (10, 0.08),
    "BOND": (10, 0.02),
}

FEATURES = [
    "ret_1", "ret_5", "ret_20", "mom_20", "rsi_14", "vol_20", "atr_pct",
    "dist_high_20", "vol_ratio", "range_pct", "gap", "close_pos", "dd_60",
    "up_days_5",
]


def load_bars(symbol: str, period: str) -> pd.DataFrame | None:
    """Daily OHLCV for one symbol, cached on disk so reruns are cheap."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{symbol.replace('=', '_').replace('^', '_')}_{period}.csv"
    if f.exists():
        try:
            df = pd.read_csv(f, index_col=0, parse_dates=True)
            return df if len(df) > 300 else None
        except Exception:
            f.unlink(missing_ok=True)
    try:
        import yfinance as yf
        df = yf.download(symbol, period=period, interval="1d",
                         progress=False, auto_adjust=True, threads=False)
    except Exception:
        return None
    if df is None or len(df) < 300:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    keep = [c for c in ("Open", "High", "Low", "Close", "Volume") if c in df.columns]
    df = df[keep].dropna(how="all")
    df.to_csv(f)
    return df


def features(df: pd.DataFrame) -> pd.DataFrame:
    """All features are functions of bars at or before the current close."""
    c, h, l, v, o = df["Close"], df["High"], df["Low"], df["Volume"], df["Open"]
    r1 = c.pct_change()
    vol20 = r1.rolling(20).std()
    delta = c.diff()
    up = delta.clip(lower=0).rolling(14).mean()
    dn = (-delta.clip(upper=0)).rolling(14).mean()
    rsi = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    out = pd.DataFrame({
        "ret_1": r1,
        "ret_5": c.pct_change(5),
        "ret_20": c.pct_change(20),
        "mom_20": c.pct_change(20) / (vol20 * math.sqrt(20)),
        "rsi_14": rsi,
        "vol_20": vol20,
        "atr_pct": (h - l).rolling(14).mean() / c,
        "dist_high_20": c / h.rolling(20).max() - 1,
        "vol_ratio": v / v.rolling(20).mean(),
        "range_pct": (h - l) / c,
        "gap": o / c.shift(1) - 1,
        "close_pos": (c - l) / (h - l).replace(0, np.nan),
        "dd_60": c / c.rolling(60).max() - 1,
        "up_days_5": (r1 > 0).rolling(5).sum(),
    }, index=df.index)
    return out


def build_panel(classes: list[str], period: str) -> pd.DataFrame:
    parts = []
    for cls in classes:
        H, T = EVENT[cls]
        for sym in UNIVERSES[cls]:
            bars = load_bars(sym, period)
            if bars is None or "Close" not in bars:
                continue
            feats = features(bars)
            fwd = bars["Close"].shift(-H) / bars["Close"] - 1
            part = feats.copy()
            part["symbol"] = sym
            part["asset_class"] = cls
            part["date"] = bars.index
            part["fwd_ret"] = fwd.values
            part["event"] = (fwd.values >= T).astype(float)
            part.loc[np.isnan(fwd.values), "event"] = np.nan
            part["week_ret"] = (bars["Close"] / bars["Close"].shift(5) - 1).values
            parts.append(part)
    if not parts:
        raise SystemExit("no data downloaded")
    panel = pd.concat(parts, ignore_index=True)
    # Do NOT drop rows for a missing feature: FX has no volume, so vol_ratio is
    # NaN there, and a global dropna would delete every FOREX row. Coverage is
    # enforced per feature inside review_class instead.
    return panel.dropna(subset=["date", "event"])


def review_class(panel: pd.DataFrame, cls: str, min_rows: int = 400,
                 seed: int = 0) -> dict | None:
    """Purged time split; search on train, evaluate the frozen cut on test."""
    H, T = EVENT[cls]
    d = panel[panel["asset_class"] == cls].sort_values("date")
    if len(d) < min_rows:
        return None
    dates = np.sort(d["date"].unique())
    cutoff = dates[int(0.7 * len(dates))]
    train = d[d["date"] <= cutoff]
    # Purge H days so no train label overlaps the test window.
    purge_end = cutoff + pd.Timedelta(days=int(H * 2))
    test = d[d["date"] > purge_end]
    if len(train) < 200 or len(test) < 150:
        return None

    base_tr = float(train["event"].mean())
    base_te = float(test["event"].mean())

    cands = []
    for f in FEATURES:
        sub = train[[f, "event"]].dropna()
        if len(sub) < 200:
            continue
        x_tr = sub[f].tolist()
        y_tr = sub["event"].astype(int).tolist()
        if len(set(x_tr)) < 10:
            continue
        rho = spearman(x_tr, y_tr)
        p = permutation_p(x_tr, y_tr, b=300, seed=seed)
        cands.append({"feature": f, "rho": round(rho, 4), "p": round(p, 4)})
    if not cands:
        return None
    for c, q in zip(cands, bh_adjust([c["p"] for c in cands])):
        c["q"] = round(q, 4)
    cands.sort(key=lambda c: (c["q"], -abs(c["rho"])))
    best = cands[0]

    # Freeze the cut on train, apply it to test — no peeking.
    best_f = best["feature"]
    cut = float(np.quantile(train[best_f].dropna(), 0.9))
    test = test.dropna(subset=[best_f])
    sel_te = test[test[best_f] >= cut]
    n_te, k_te = len(sel_te), int(sel_te["event"].sum())
    if n_te < 30:
        # A train-period cut can select almost nothing in a calmer test period.
        # Report that instead of silently dropping the class.
        return {"asset_class": cls, "event": {"horizon_days": H, "threshold": T},
                "n_train": len(train), "n_test": len(test),
                "base_rate_train": round(base_tr, 4),
                "base_rate_test": round(base_te, 4),
                "best_feature": best_f, "train_rho": best["rho"],
                "train_q": best["q"], "cut": round(cut, 6),
                "oos_n": n_te, "oos_hits": k_te,
                "verdict": (f"inconclusive — train cut selects only {n_te} OOS rows; "
                            f"the feature's level shifted between periods"),
                "week_top_movers": _movers(d)}
    rate_te = k_te / n_te
    lo, hi = wilson(k_te, n_te)
    # Binomial tail: P(X >= k | n, base_te), exact-ish via normal approx with continuity.
    p_oos = _binom_sf(k_te, n_te, base_te)

    sel_tr = train[train[best_f] >= cut]
    rate_tr = float(sel_tr["event"].mean()) if len(sel_tr) else float("nan")

    # Variance vs direction: a volatility-like feature raises P(+T) mechanically
    # without raising expected return. If the UP rate rises but the DOWN rate
    # rises too (or mean forward return does not), there is no directional edge.
    rest_te = test[test[best_f] < cut]
    up_sel, up_rest = rate_te, float(rest_te["event"].mean())
    down_sel = float((sel_te["fwd_ret"] <= -T).mean())
    down_rest = float((rest_te["fwd_ret"] <= -T).mean())
    mean_sel = float(sel_te["fwd_ret"].mean())
    mean_rest = float(rest_te["fwd_ret"].mean())
    directional = (mean_sel > mean_rest) and (up_sel - up_rest) > (down_sel - down_rest)

    if not directional:
        verdict = ("volatility artifact — event rate up but no directional edge "
                   f"(mean fwd {mean_sel:+.4f} vs {mean_rest:+.4f})")
    elif lo > base_te:
        verdict = "candidate — OOS CI excludes base rate AND direction is favourable"
    elif rate_te > base_te:
        verdict = "weak — OOS positive but CI covers base rate"
    else:
        verdict = "no edge — OOS at or below base rate"

    return {
        "asset_class": cls, "event": {"horizon_days": H, "threshold": T},
        "n_train": len(train), "n_test": len(test),
        "base_rate_train": round(base_tr, 4), "base_rate_test": round(base_te, 4),
        "best_feature": best["feature"], "train_rho": best["rho"], "train_q": best["q"],
        "cut": round(cut, 6),
        "train_rate_above_cut": round(rate_tr, 4),
        "oos_n": n_te, "oos_hits": k_te, "oos_rate": round(rate_te, 4),
        "oos_ci": [round(lo, 4), round(hi, 4)],
        "oos_lift": round(rate_te - base_te, 4),
        "shrinkage": round(rate_te - rate_tr, 4),
        "oos_p_vs_base": round(p_oos, 4),
        "direction": {"mean_fwd_selected": round(mean_sel, 5),
                      "mean_fwd_rest": round(mean_rest, 5),
                      "up_rate_selected": round(up_sel, 4),
                      "up_rate_rest": round(up_rest, 4),
                      "down_rate_selected": round(down_sel, 4),
                      "down_rate_rest": round(down_rest, 4),
                      "directional": bool(directional)},
        "verdict": verdict,
        "week_top_movers": _movers(d),
    }


def _binom_sf(k: int, n: int, p: float) -> float:
    """P(X >= k) for X ~ Bin(n, p), normal approximation with continuity fix."""
    if n == 0:
        return 1.0
    if p <= 0:
        return 0.0 if k > 0 else 1.0
    mu, sd = n * p, math.sqrt(n * p * (1 - p))
    if sd == 0:
        return 1.0
    z = (k - 0.5 - mu) / sd
    return 0.5 * math.erfc(z / math.sqrt(2))


def _movers(d: pd.DataFrame, k: int = 3) -> list[dict]:
    last = d.sort_values("date").groupby("symbol").tail(1)
    last = last.dropna(subset=["week_ret"]).sort_values("week_ret", ascending=False)
    return [{"symbol": r.symbol, "week_ret": round(float(r.week_ret), 4),
             "vol_20": round(float(r.vol_20), 4) if pd.notna(r.vol_20) else None,
             "vol_ratio": round(float(r.vol_ratio), 3) if pd.notna(r.vol_ratio) else None,
             "dist_high_20": round(float(r.dist_high_20), 4) if pd.notna(r.dist_high_20) else None}
            for r in last.head(k).itertuples()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--period", default="5y")
    ap.add_argument("--classes", nargs="*", default=list(UNIVERSES))
    ap.add_argument("--json-out")
    a = ap.parse_args(argv)

    panel = build_panel(a.classes, a.period)
    print(f"panel: {len(panel)} rows, {panel['symbol'].nunique()} symbols\n")
    results = []
    for cls in a.classes:
        r = review_class(panel, cls)
        if r is None:
            print(f"{cls:<8} insufficient data\n")
            continue
        results.append(r)
        if "oos_ci" not in r:
            print(f"{cls:<8} event +{r['event']['threshold']:.0%}/{r['event']['horizon_days']}d  "
                  f"base {r['base_rate_test']:.3f} (test)  best {r['best_feature']} q={r['train_q']}")
            print(f"         {r['verdict']}\n")
            continue
        print(f"{cls:<8} event +{r['event']['threshold']:.0%}/{r['event']['horizon_days']}d  "
              f"base {r['base_rate_test']:.3f} (test)  best {r['best_feature']} q={r['train_q']}")
        dr = r["direction"]
        print(f"         train {r['train_rate_above_cut']:.3f} -> OOS {r['oos_rate']:.3f} "
              f"{r['oos_ci']} lift {r['oos_lift']:+.3f} shrink {r['shrinkage']:+.3f} "
              f"p_vs_base {r['oos_p_vs_base']:.3f}")
        print(f"         up {dr['up_rate_selected']:.3f} vs {dr['up_rate_rest']:.3f} | "
              f"down {dr['down_rate_selected']:.3f} vs {dr['down_rate_rest']:.3f} | "
              f"mean fwd {dr['mean_fwd_selected']:+.4f} vs {dr['mean_fwd_rest']:+.4f}")
        print(f"         {r['verdict']}")
        movers = ", ".join(f"{m['symbol']} {m['week_ret']:+.1%}" for m in r["week_top_movers"])
        print(f"         week: {movers}\n")

    if a.json_out:
        Path(a.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json_out).write_text(json.dumps({"period": a.period, "classes": results},
                                               indent=1), encoding="utf-8")
    print("discovery only — no verdict; survivors must clear the audit3 forward gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
