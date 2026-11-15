#!/usr/bin/env python3
"""Hours-scale skyrocket reverse-engineer (candle + catalyst + volatility features).

Question: given only information available *at* an hourly bar, which patterns
precede a >=X% move within the next few hours?

Feature groups:
  * price/volume technicals (hourly bars)
  * volatility regime (^VIX level and 1-bar change) - historical, testable
  * catalyst recency (SEC EDGAR 8-K/10-Q/10-K/S-1/424B5 timestamps) - historical, testable
  * options flow (nearest-expiry put/call volume and OI, ATM IV skew) - LIVE ONLY:
    yfinance exposes the current chain, not its history, so these columns are
    reported for the watchlist and are NEVER used in the backtest label stats.

Honesty rules kept from v1: features use data up to and including bar t; the
label is close[t+4]/close[t]-1 against an ATR-normalised threshold; patterns are
reported on the last 30% of the timeline (test) separately from the first 70%.

Writes reports/skyrocket_patterns_<date>.md.
"""
from __future__ import annotations

import json
import math
import os
import sys
import warnings
from datetime import date

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

UNIVERSE = {
    "EQUITY": ("TSLA NVDA AMD PLTR SOFI HOOD COIN MSTR RIVN NIO SMCI MARA RIOT GME AMC "
               "ABNB U DKNG AFRM UPST CVNA WULF CLSK HUT IONQ AI SNAP SHOP BABA"),
    "ETF": "SPY QQQ IWM XLE SOXL TQQQ SMH GDX ARKK",
    "CRYPTO": "BTC-USD ETH-USD SOL-USD DOGE-USD XRP-USD AVAX-USD LINK-USD ADA-USD",
}
THRESHOLD_ATR = 1.5
HORIZON = 4
MIN_HISTORY = 300

TECH_FEATS = ["r1", "r4", "r24", "vol_surge", "range_exp", "atr_comp", "donch_break",
              "rsi", "sma_dist", "bb_z", "gap", "streak"]
REGIME_FEATS = ["vix_level", "vix_r1", "log_hrs_filing", "filing_24h"]
FEATS = TECH_FEATS + REGIME_FEATS

EDGAR_UA = "findtorontoevents research ops@findtorontoevents.ca"
CATALYST_FORMS = ("8-K", "10-Q", "10-K", "S-1", "424B5", "8-K/A")


# ── data ────────────────────────────────────────────────────────────────────
def fetch(tickers: list[str], chunk: int = 15) -> dict[str, pd.DataFrame]:
    import yfinance as yf
    out: dict[str, pd.DataFrame] = {}
    for i in range(0, len(tickers), chunk):
        part = tickers[i:i + chunk]
        try:
            raw = yf.download(part, period="730d", interval="1h", auto_adjust=True,
                              progress=False, threads=False, group_by="ticker")
        except Exception as exc:
            print(f"  ! chunk failed ({len(part)} tickers): {type(exc).__name__}", file=sys.stderr)
            continue
        for t in part:
            try:
                sub = raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw
            except Exception:
                continue
            sub = sub.dropna(subset=["Close"])
            if len(sub) >= MIN_HISTORY:
                out[t] = sub.copy()
    return out


def fetch_vix() -> pd.DataFrame | None:
    """Hourly ^VIX — a volatility regime the candles alone can't see."""
    import yfinance as yf
    try:
        raw = yf.download("^VIX", period="730d", interval="1h", auto_adjust=True,
                          progress=False, threads=False)
    except Exception:
        return None
    if raw is None or len(raw) < 200:
        return None
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    c = raw["Close"].dropna()
    return pd.DataFrame({"vix_level": c, "vix_r1": c.pct_change()})


def fetch_filings(tickers: list[str]) -> dict[str, np.ndarray]:
    """Filing timestamps per ticker from SEC EDGAR (free, no key).

    Fail-soft: an unreachable or rate-limited EDGAR just means the catalyst
    features are absent, never that the run fails.
    """
    import urllib.request

    def _get(url: str, timeout: int = 30):
        # EDGAR serves gzip even when not asked; decode it explicitly instead of
        # requesting an encoding we cannot read (first run returned 0 tickers
        # with UnicodeDecodeError because of exactly that).
        req = urllib.request.Request(url, headers={"User-Agent": EDGAR_UA})
        raw = urllib.request.urlopen(req, timeout=timeout).read()
        if raw[:2] == b"\x1f\x8b":
            import gzip
            raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8", "replace"))

    try:
        mapping = _get("https://www.sec.gov/files/company_tickers.json")
    except Exception as exc:
        print(f"  ! EDGAR ticker map unavailable ({type(exc).__name__}) — catalyst features off",
              file=sys.stderr)
        return {}
    tic2cik = {str(v.get("ticker", "")).upper(): int(v["cik_str"]) for v in mapping.values() if v.get("cik_str")}
    out: dict[str, np.ndarray] = {}
    for t in tickers:
        cik = tic2cik.get(t.upper())
        if cik is None:
            continue
        try:
            sub = _get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
        except Exception:
            continue
        recent = (sub.get("filings") or {}).get("recent") or {}
        dates = recent.get("filingDate") or []
        forms = recent.get("form") or []
        stamps = []
        for dt, form in zip(dates, forms):
            if form in CATALYST_FORMS:
                try:
                    stamps.append(pd.Timestamp(dt, tz="UTC").tz_localize(None) + pd.Timedelta(hours=16))
                except Exception:
                    continue
        if stamps:
            out[t.upper()] = np.array(sorted(stamps), dtype="datetime64[ns]")
    return out


def options_snapshot(tickers: list[str]) -> dict[str, dict]:
    """Nearest-expiry flow, CURRENT SNAPSHOT ONLY (no history exists in yfinance)."""
    import yfinance as yf
    out: dict[str, dict] = {}
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            exps = list(tk.options or [])[:1]
            if not exps:
                continue
            chain = tk.option_chain(exps[0])
            calls, puts = chain.calls, chain.puts
            cv = float(calls.get("volume", pd.Series(dtype=float)).fillna(0).sum())
            pv = float(puts.get("volume", pd.Series(dtype=float)).fillna(0).sum())
            coi = float(calls.get("openInterest", pd.Series(dtype=float)).fillna(0).sum())
            poi = float(puts.get("openInterest", pd.Series(dtype=float)).fillna(0).sum())
            iv_c = iv_p = float("nan")
            if len(calls) and len(puts):
                spot = float(np.nanmedian(pd.concat([calls["strike"], puts["strike"]])))
                iv_c = float(calls.iloc[(calls["strike"] - spot).abs().argsort()[:1]]["impliedVolatility"].iloc[0])
                iv_p = float(puts.iloc[(puts["strike"] - spot).abs().argsort()[:1]]["impliedVolatility"].iloc[0])
            out[t.upper()] = {
                "expiry": exps[0],
                "pc_vol": round(pv / cv, 2) if cv > 0 else None,
                "pc_oi": round(poi / coi, 2) if coi > 0 else None,
                "iv_skew": round(iv_p - iv_c, 4) if np.isfinite(iv_c) and np.isfinite(iv_p) else None,
                "call_vol": int(cv), "put_vol": int(pv),
            }
        except Exception:
            continue
    return out


# ── features ────────────────────────────────────────────────────────────────
def features(df: pd.DataFrame) -> pd.DataFrame:
    c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"].fillna(0)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(20).mean() / c
    f = pd.DataFrame(index=df.index)
    f["r1"] = c.pct_change(1)
    f["r4"] = c.pct_change(4)
    f["r24"] = c.pct_change(24)
    f["vol_surge"] = v / v.rolling(20).mean().replace(0, np.nan)
    f["range_exp"] = (h - l) / c / atr.replace(0, np.nan)
    f["atr_comp"] = atr / atr.rolling(120).mean().replace(0, np.nan)
    f["donch_break"] = c / h.rolling(20).max() - 1
    f["dist52"] = c / c.rolling(252, min_periods=60).max() - 1  # 252-bar high
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    f["rsi"] = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    f["sma_dist"] = c / c.rolling(20).mean() - 1
    bw = (c.rolling(20).std() * 2) / c.rolling(20).mean()
    f["bb_z"] = (bw - bw.rolling(120).mean()) / bw.rolling(120).std().replace(0, np.nan)
    f["gap"] = df["Open"] / c.shift() - 1
    f["streak"] = (np.sign(d).groupby((np.sign(d) != np.sign(d).shift()).cumsum()).cumcount() + 1) * np.sign(d)
    f["hour"] = df.index.hour
    f["dow"] = df.index.dayofweek
    f["atr_pct"] = atr
    f["close"] = c
    return f


def add_regime(f: pd.DataFrame, vix: pd.DataFrame | None, filings: np.ndarray | None) -> pd.DataFrame:
    if vix is not None and len(vix):
        try:
            f = f.join(vix.reindex(f.index, method="nearest", tolerance=pd.Timedelta("3h")))
        except Exception:
            f["vix_level"] = np.nan
            f["vix_r1"] = np.nan
    else:
        f["vix_level"] = np.nan
        f["vix_r1"] = np.nan
    if filings is not None and len(filings):
        idx = f.index.tz_convert("UTC").tz_localize(None) if f.index.tz is not None else f.index
        pos = np.searchsorted(filings, idx.values, side="right") - 1
        hrs = np.full(len(idx), np.nan)
        ok = pos >= 0
        if ok.any():
            hrs[ok] = (idx.values[ok] - filings[pos[ok]]) / np.timedelta64(1, "h")
        f["hrs_since_filing"] = hrs
        f["log_hrs_filing"] = np.log1p(np.clip(hrs, 0, None))
        f["filing_24h"] = (hrs <= 24).astype(float)
    else:
        f["hrs_since_filing"] = np.nan
        f["log_hrs_filing"] = np.nan
        f["filing_24h"] = 0.0
    return f


def build(tickers: list[str], cls: str, vix, filings_all) -> pd.DataFrame:
    data = fetch(tickers)
    frames = []
    for t, df in data.items():
        f = add_regime(features(df), vix, filings_all.get(t.upper()))
        f["fwd"] = df["Close"].shift(-HORIZON) / df["Close"] - 1
        f["spike"] = (f["fwd"] >= THRESHOLD_ATR * f["atr_pct"]).astype(float)
        f = f.dropna(subset=["r1", "r4", "r24", "vol_surge", "atr_comp", "rsi", "fwd", "atr_pct"])
        f = f[np.isfinite(f["fwd"])]
        f = f[f["dist52"].isna() | (f["dist52"] > -0.98)]
        f = f[f["close"].fillna(0) > 0]
        f["ticker"] = t
        f["asset_class"] = cls
        frames.append(f)
    print(f"  {cls}: {len(data)} tickers -> {sum(len(x) for x in frames)} hourly bars", file=sys.stderr)
    return pd.concat(frames) if frames else pd.DataFrame()


RULES = {
    "vol surge >2x": lambda d: d["vol_surge"] > 2,
    "range expansion >2x ATR": lambda d: d["range_exp"] > 2,
    "volatility squeeze (atr_comp<0.8)": lambda d: d["atr_comp"] < 0.8,
    "squeeze + volume surge": lambda d: (d["atr_comp"] < 0.8) & (d["vol_surge"] > 1.5),
    "20-bar breakout": lambda d: d["donch_break"] >= -0.001,
    "breakout + vol >1.5x": lambda d: (d["donch_break"] >= -0.001) & (d["vol_surge"] > 1.5),
    "breakout + squeeze": lambda d: (d["donch_break"] >= -0.001) & (d["atr_comp"] < 0.9),
    "pullback in uptrend (r24>0, r1<-1%)": lambda d: (d["r24"] > 0) & (d["r1"] < -0.01),
    "oversold snap (RSI<30)": lambda d: d["rsi"] < 30,
    "RSI 50-70 trend": lambda d: d["rsi"].between(50, 70),
    "3+ up bars in a row": lambda d: d["streak"] >= 3,
    "gap up >1%": lambda d: d["gap"] > 0.01,
    "squeeze + breakout + RSI<70": lambda d: (d["atr_comp"] < 0.9) & (d["donch_break"] >= -0.002) & (d["rsi"] < 70),
    # catalyst / regime (new 2026-11-15)
    "filing in last 24h": lambda d: d["filing_24h"] > 0,
    "filing in last 24h + breakout": lambda d: (d["filing_24h"] > 0) & (d["donch_break"] >= -0.002),
    "VIX > 25 (stressed regime)": lambda d: d["vix_level"] > 25,
    "VIX falling (r1<0) + squeeze": lambda d: (d["vix_r1"] < 0) & (d["atr_comp"] < 0.9),
}


def auc(y: np.ndarray, s: np.ndarray) -> float | None:
    n1 = int(y.sum())
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return None
    order = np.argsort(s)
    ranks = np.empty(len(s))
    ranks[order] = np.arange(1, len(s) + 1)
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def fit_logit(X: np.ndarray, y: np.ndarray, iters: int = 400, lr: float = 0.6, l2: float = 1e-3) -> np.ndarray:
    w = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-np.clip(X @ w, -30, 30)))
        w -= lr * (X.T @ (p - y) / len(y) + l2 * w)
    return w


def summarise(df: pd.DataFrame, vix_used: bool, filings_used: int) -> dict:
    base = float(df["spike"].mean())
    out = {"n": int(len(df)), "base_rate": round(base, 4),
           "vix_used": vix_used, "filings_used": filings_used,
           "per_class": {}, "features": {}, "rules": {}}
    for cls, sub in df.groupby("asset_class"):
        out["per_class"][cls] = {
            "bars": int(len(sub)), "base_rate": round(float(sub["spike"].mean()), 4),
            "tickers": int(sub["ticker"].nunique()),
            "median_atr_pct": round(float(sub["atr_pct"].median()) * 100, 3),
            "median_spike_move_pct": round(float((THRESHOLD_ATR * sub["atr_pct"]).median()) * 100, 2),
        }
    for f in FEATS:
        x = df[f].values.astype(float)
        y = df["spike"].values.astype(float)
        ok = np.isfinite(x)
        if ok.sum() < 1000 or np.std(x[ok]) == 0:
            continue
        qs = np.quantile(x[ok], np.linspace(0, 1, 11))
        dec = np.digitize(x, qs[1:-1])
        rates = [float(y[ok & (dec == i)].mean()) for i in range(10) if (ok & (dec == i)).sum() > 50]
        out["features"][f] = {
            "auc": round(auc(y[ok], x[ok]) or 0.5, 4),
            "top_decile_rate": round(max(rates), 4) if rates else None,
            "bottom_decile_rate": round(min(rates), 4) if rates else None,
            "lift_top": round(max(rates) / base, 2) if rates and base > 0 else None,
            "coverage": round(float(ok.mean()), 3),
        }
    df = df.sort_index()
    cut = df.index[int(len(df) * 0.7)] if len(df) > 100 else df.index[0]
    for name, fn in RULES.items():
        try:
            mask = fn(df).fillna(False).values.astype(bool)
        except Exception:
            continue
        tr, te = mask & np.asarray(df.index < cut), mask & np.asarray(df.index >= cut)
        row = {"n": int(mask.sum())}
        for tag, m in (("train", tr), ("test", te)):
            n = int(m.sum())
            row[tag] = {"n": n,
                        "precision": round(float(df["spike"].values[m].mean()), 4) if n else None,
                        "avg_fwd_pct": round(float(df["fwd"].values[m].mean()) * 100, 3) if n else None}
        base_te = df["spike"].values[np.asarray(df.index >= cut)].mean()
        row["lift_test"] = round(row["test"]["precision"] / base_te, 2) if row["test"]["precision"] and base_te else None
        out["rules"][name] = row
    X = df[FEATS].replace([np.inf, -np.inf], np.nan).fillna(0).values
    y = df["spike"].values.astype(float)
    tr = np.asarray(df.index < cut)
    te = ~tr
    if tr.sum() > 500 and te.sum() > 500 and len(np.unique(y[tr])) > 1:
        mu, sd = X[tr].mean(0), X[tr].std(0)
        sd[sd == 0] = 1
        Z = (X - mu) / sd
        w = fit_logit(np.c_[np.ones(len(Z)), Z][tr], y[tr])
        p = 1 / (1 + np.exp(-np.clip(np.c_[np.ones(len(Z)), Z] @ w, -30, 30)))
        base_te = y[te].mean()
        k = max(1, int(te.sum() * 0.01))
        top = np.argsort(-p[te])[:k]
        out["model"] = {
            "train_rows": int(tr.sum()), "test_rows": int(te.sum()),
            "train_base": round(float(y[tr].mean()), 4), "test_base": round(float(base_te), 4),
            "auc_test": round(auc(y[te], p[te]) or 0.5, 4),
            "top1pct_precision": round(float(y[te][top].mean()), 4),
            "top1pct_lift": round(float(y[te][top].mean()) / base_te, 2) if base_te else None,
            "weights": {f: round(float(wi), 3) for f, wi in zip(FEATS, w[1:])},
        }
        # tech-only model, to isolate what the new features actually added
        Xt = df[TECH_FEATS].replace([np.inf, -np.inf], np.nan).fillna(0).values
        mut, sdt = Xt[tr].mean(0), Xt[tr].std(0)
        sdt[sdt == 0] = 1
        Zt = (Xt - mut) / sdt
        wt = fit_logit(np.c_[np.ones(len(Zt)), Zt][tr], y[tr])
        pt = 1 / (1 + np.exp(-np.clip(np.c_[np.ones(len(Zt)), Zt] @ wt, -30, 30)))
        out["model_tech_only"] = {"auc_test": round(auc(y[te], pt[te]) or 0.5, 4)}
        latest = df.groupby("ticker").tail(1).copy()
        Zl = (latest[FEATS].replace([np.inf, -np.inf], np.nan).fillna(0).values - mu) / sd
        latest["score"] = 1 / (1 + np.exp(-np.clip(np.c_[np.ones(len(Zl)), Zl] @ w, -30, 30)))
        cols = ["ticker", "asset_class", "score", "r1", "r24", "vol_surge", "atr_comp", "rsi",
                "donch_break", "vix_level", "hrs_since_filing"]
        out["watchlist"] = latest.nlargest(12, "score")[cols].round(3).to_dict("records")
        out["_model_state"] = (mu, sd, w)
    return out


def to_md(res: dict, flow: dict) -> str:
    L = [f"# Hours-scale skyrocket patterns — {date.today().isoformat()}", "",
         f"Label: forward {HORIZON}-hour move >= {THRESHOLD_ATR}x the ATR% at the signal bar. Hourly bars, ~2 years. "
         f"Base rate over all bars: **{res['base_rate']*100:.2f}%**.", "",
         f"Feature sources live this run: VIX regime **{'yes' if res['vix_used'] else 'no'}**, "
         f"SEC filing recency **{res['filings_used']} tickers**. Options flow is live-only (see below).", "",
         "## Base rates by class", "",
         "| class | bars | tickers | base rate | median ATR% | median spike size |", "|---|---|---|---|---|---|"]
    for cls, v in res["per_class"].items():
        L.append(f"| {cls} | {v['bars']} | {v['tickers']} | {v['base_rate']*100:.2f}% | "
                 f"{v['median_atr_pct']}% | {v['median_spike_move_pct']}% |")
    L += ["", "## Which feature orders the spikes", "",
          "| feature | AUC | top-decile rate | bottom-decile | lift | coverage |", "|---|---|---|---|---|---|"]
    for f, v in sorted(res["features"].items(), key=lambda kv: -abs(kv[1]["auc"] - 0.5)):
        L.append(f"| {f} | {v['auc']:.3f} | {v['top_decile_rate']*100:.2f}% | "
                 f"{v['bottom_decile_rate']*100:.2f}% | {v['lift_top']}x | {v['coverage']*100:.0f}% |")
    L += ["", "## Named patterns (train = first 70% of time, test = last 30%)", "",
          "| pattern | signals | train precision | test precision | test lift | avg fwd test |",
          "|---|---|---|---|---|---|"]
    for name, r in sorted(res["rules"].items(), key=lambda kv: -(kv[1].get("lift_test") or 0)):
        te = r["test"]
        L.append(f"| {name} | {r['n']} | {(r['train']['precision'] or 0)*100:.2f}% | "
                 f"{(te['precision'] or 0)*100:.2f}% | {r['lift_test']}x | {te['avg_fwd_pct']}% |")
    m = res.get("model")
    if m:
        t = res.get("model_tech_only") or {}
        L += ["", "## Model ceiling (chronological split)", "",
              f"- all features: test AUC **{m['auc_test']}**, base {m['test_base']*100:.2f}%, "
              f"top-1% precision **{m['top1pct_precision']*100:.2f}%** ({m['top1pct_lift']}x lift)",
              f"- candle-only model: test AUC **{t.get('auc_test')}** → "
              f"catalyst/regime features {'+' if (t.get('auc_test') or 0) and m['auc_test'] > t['auc_test'] else ''}"
              f"{round((m['auc_test'] - (t.get('auc_test') or m['auc_test'])) * 1000) / 1000} AUC",
              f"- rows: {m['train_rows']} train / {m['test_rows']} test", "",
              "weights: " + ", ".join(f"`{k}` {v:+.2f}" for k, v in m["weights"].items())]
    if res.get("watchlist"):
        L += ["", "## Live watchlist (latest bar scored by that model)", "",
              "| ticker | class | score | 1h | 24h | vol surge | ATR comp | RSI | vs 20h high | VIX | hrs since filing |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for w in res["watchlist"]:
            vix = f"{w['vix_level']:.1f}" if isinstance(w.get("vix_level"), (int, float)) and w["vix_level"] == w["vix_level"] else "—"
            hrs = f"{w['hrs_since_filing']:.0f}" if isinstance(w.get("hrs_since_filing"), (int, float)) and w["hrs_since_filing"] == w["hrs_since_filing"] else "—"
            L.append(f"| {w['ticker']} | {w['asset_class']} | {w['score']:.3f} | {w['r1']*100:+.1f}% | "
                     f"{w['r24']*100:+.1f}% | {w['vol_surge']:.2f}x | {w['atr_comp']:.2f} | {w['rsi']:.0f} | "
                     f"{w['donch_break']*100:+.2f}% | {vix} | {hrs} |")
    if flow:
        L += ["", "## Options flow — CURRENT SNAPSHOT ONLY (not backtested)", "",
              "yfinance exposes the live chain, not its history, so these columns cannot enter the label stats above.",
              "", "| ticker | expiry | put/call vol | put/call OI | ATM IV skew (put-call) | call vol | put vol |",
              "|---|---|---|---|---|---|---|"]
        for t, v in sorted(flow.items()):
            L.append(f"| {t} | {v['expiry']} | {v['pc_vol']} | {v['pc_oi']} | {v['iv_skew']} | "
                     f"{v['call_vol']} | {v['put_vol']} |")
    L += ["", "---", "Read the test column only. Catalyst recency is a *filing timestamp*, not the news content:",
          "an 8-K at 16:00 is knowable, its effect is not. Options flow stays snapshot-only until a historical",
          "chain source exists — treating a live ratio as if it were backtested is how false edges get shipped."]
    return "\n".join(L) + "\n"


def main() -> int:
    print("fetching price history + VIX + EDGAR filings ...")
    vix = fetch_vix()
    all_syms = [s for syms in UNIVERSE.values() for s in syms.split()]
    filings = fetch_filings([s for s in all_syms if "=" not in s and "-USD" not in s])
    frames = []
    for cls, syms in UNIVERSE.items():
        df = build(syms.split(), cls, vix, filings)
        if not df.empty:
            frames.append(df)
    if not frames:
        print("no data", file=sys.stderr)
        return 1
    pooled = pd.concat(frames).sort_index()
    res = summarise(pooled, vix_used=vix is not None and len(vix) > 0, filings_used=len(filings))
    top = [w["ticker"] for w in res.get("watchlist", []) if w["asset_class"] in ("EQUITY", "ETF")]
    flow = options_snapshot(top[:10]) if top else {}
    out = f"reports/skyrocket_patterns_{date.today().isoformat()}.md"
    text = to_md(res, flow)
    open(out, "w", encoding="utf-8").write(text)
    print(f"wrote {out} ({len(text.splitlines())} lines) | bars={res['n']} base={res['base_rate']*100:.2f}% "
          f"| filings={res['filings_used']} | flow={len(flow)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
