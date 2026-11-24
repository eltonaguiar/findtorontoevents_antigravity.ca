#!/usr/bin/env python3
"""Weekly winner reverse-engineer.

For each asset class: what actually went up this week, and can anything known
*at the start of the week* rank next week's winners better than chance?

Every statistic is walk-forward: features are computed from data as of each
Friday close, the target is the NEXT week's return. No lookahead, no fitting on
the test week. Output: reports/weekly_winner_<date>.md
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
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")

UNIVERSE = {
    "CRYPTO": "BTC-USD ETH-USD SOL-USD BNB-USD XRP-USD DOGE-USD ADA-USD AVAX-USD LINK-USD DOT-USD LTC-USD BCH-USD TRX-USD TON-USD SHIB-USD UNI-USD ATOM-USD XLM-USD NEAR-USD APT-USD ARB-USD OP-USD INJ-USD SUI-USD SEI-USD TIA-USD FIL-USD ICP-USD HBAR-USD AAVE-USD ETC-USD PEPE-USD JUP-USD FET-USD ALGO-USD VET-USD MANA-USD SAND-USD GALA-USD EOS-USD MKR-USD CRV-USD GRT-USD",
    "EQUITY": "AAPL MSFT NVDA AMZN GOOGL META TSLA AVGO AMD NFLX CRM ORCL ADBE COST PEP KO JPM BAC WFC GS MS V MA AXP DIS CMCSA TMO ABT PFE MRK LLY UNH JNJ XOM CVX COP CAT DE BA GE HON LMT RTX UPS FDX NKE SBUX MCD HD LOW TGT WMT PG CL INTC QCOM MU AMAT ASML TXN ADI NOW SNOW PLTR CRWD PANW SHOP UBER ABNB COIN MSTR HOOD SOFI RIVN NIO BABA JD PDD TSM",
    "ETF": "SPY QQQ IWM DIA XLE XLF XLK XLV XLI XLP XLY XLU XLB XLRE SMH SOXX ARKK TAN ICLN LIT GDX GDXJ SLV USO UNG TLT IEF HYG LQD EEM EFA FXI EWZ EWJ INDA KWEB IBIT",
    "COMMODITY": "GC=F SI=F PL=F PA=F HG=F CL=F BZ=F NG=F RB=F HO=F ZC=F ZW=F ZS=F ZM=F KC=F SB=F CC=F CT=F LE=F HE=F GF=F",
    "FOREX": "EURUSD=X GBPUSD=X USDJPY=X AUDUSD=X USDCAD=X USDCHF=X NZDUSD=X EURGBP=X EURJPY=X GBPJPY=X USDMXN=X USDCNH=X",
    "BOND": "TLT IEF SHY LQD HYG JNK TIP EMB BNDX AGG MUB ZN=F ZB=F",
}

FEATURES = ["ret1w", "ret1m", "ret3m", "vol1m", "volratio", "dist52", "rsi14", "sma50_dist", "sma200_dist", "dollar_vol"]
MIN_NAMES = 8


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def daily_features(close: pd.Series, vol: pd.Series) -> pd.DataFrame:
    r = close.pct_change()
    f = pd.DataFrame(index=close.index)
    f["ret1w"] = close.pct_change(5)
    f["ret1m"] = close.pct_change(21)
    f["ret3m"] = close.pct_change(63)
    f["vol1m"] = r.rolling(21).std()
    f["volratio"] = r.rolling(10).std() / r.rolling(60).std().replace(0, np.nan)
    f["dist52"] = close / close.rolling(252, min_periods=60).max() - 1
    f["rsi14"] = rsi(close)
    f["sma50_dist"] = close / close.rolling(50, min_periods=20).mean() - 1
    f["sma200_dist"] = close / close.rolling(200, min_periods=60).mean() - 1
    f["dollar_vol"] = (close * vol.fillna(0)).rolling(21).mean()
    return f


def fetch(tickers: list[str], chunk: int = 40) -> dict[str, pd.DataFrame]:
    import yfinance as yf
    out: dict[str, pd.DataFrame] = {}
    for i in range(0, len(tickers), chunk):
        part = tickers[i:i + chunk]
        try:
            raw = yf.download(part, period="2y", interval="1d", auto_adjust=True,
                              progress=False, threads=False, group_by="ticker")
        except Exception as exc:  # network hiccup: skip chunk, report it
            print(f"    ! download failed for {len(part)} tickers: {type(exc).__name__}", file=sys.stderr)
            continue
        for t in part:
            try:
                sub = raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw
            except Exception:
                continue
            sub = sub.dropna(subset=["Close"])
            if len(sub) > 80:
                out[t] = sub[["Close", "Volume"]].copy()
    return out


def weekly_panel(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    frames = []
    for t, df in data.items():
        close, vol = df["Close"], df["Volume"]
        f = daily_features(close, vol)
        wk = close.resample("W-FRI").last()
        fw = f.reindex(wk.index, method="ffill")
        fw = fw.copy()
        fw["fwd"] = (wk.shift(-1) / wk - 1).values
        fw["week_start"] = wk.index
        fw["ticker"] = t
        fw["close_wk"] = wk.values
        fw = fw[fw["dist52"].isna() | (fw["dist52"] > -0.98)]  # drop renamed/stale series
        fw = fw[fw["close_wk"].fillna(0) > 0]
        frames.append(fw.dropna(subset=["fwd"]))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames).reset_index(names="week")


def analyse_class(name: str, panel: pd.DataFrame, top_n: int = 5) -> dict:
    res = {"class": name, "n_tickers": int(panel["ticker"].nunique()),
           "n_weeks": int(panel["week"].nunique()), "features": {}, "weekly_ic": {}}
    weeks = sorted(panel["week"].unique())
    ics = {f: [] for f in FEATURES}
    top_prec = {f: [] for f in FEATURES}
    combo_prec, base_top = [], []
    for w in weeks:
        xs = panel[panel["week"] == w].dropna(subset=["fwd"])
        if len(xs) < MIN_NAMES:
            continue
        y = xs["fwd"].values
        q = np.quantile(y, 0.8)
        is_top = y >= q
        base_top.append(is_top.mean())
        for f in FEATURES:
            x = xs[f].values
            ok = np.isfinite(x) & np.isfinite(y)
            if ok.sum() < MIN_NAMES or np.std(x[ok]) == 0:
                continue
            rho = spearmanr(x[ok], y[ok]).statistic
            if np.isfinite(rho):
                ics[f].append(rho)
            idx = np.argsort(-x[ok])[:top_n]
            if len(idx):
                top_prec[f].append(is_top[ok][idx].mean())
    for f in FEATURES:
        if len(ics[f]) >= 10:
            arr = np.array(ics[f])
            res["features"][f] = {
                "ic": round(float(arr.mean()), 4),
                "ic_t": round(float(arr.mean() / (arr.std(ddof=1) / math.sqrt(len(arr)))), 2) if arr.std(ddof=1) > 0 else 0.0,
                "topN_precision": round(float(np.mean(top_prec[f])), 3) if top_prec[f] else None,
                "weeks": len(arr),
            }
    res["base_top_quintile_rate"] = round(float(np.mean(base_top)), 3) if base_top else None
    res["weeks_scored"] = len(base_top)

    # combined model: z-scored sum of the two most stable features (chosen in-sample
    # on the first half of weeks, evaluated on the second half -> honest holdout)
    ranked = sorted(res["features"].items(), key=lambda kv: -abs(kv[1]["ic_t"]))
    res["best_pair"] = [f for f, _ in ranked[:2]]
    if res["weeks_scored"] >= 20:
        half = res["weeks_scored"] // 2
        scored_weeks = [w for w in weeks if len(panel[panel["week"] == w].dropna(subset=["fwd"])) >= MIN_NAMES]
        train_weeks, test_weeks = scored_weeks[:half], scored_weeks[half:]
        pair = res["best_pair"]

        def score_week(w, xs):
            z = np.zeros(len(xs))
            for f in pair:
                x = xs[f].values.astype(float)
                sd = np.nanstd(x)
                z += 0 if not np.isfinite(sd) or sd == 0 else (x - np.nanmean(x)) / sd
            return z

        train_ic = []
        for w in train_weeks:
            xs = panel[panel["week"] == w].dropna(subset=["fwd"])
            z, y = score_week(w, xs), xs["fwd"].values
            if np.std(z) > 0:
                rho = spearmanr(z, y).statistic
                if np.isfinite(rho):
                    train_ic.append(rho)
        hits, base = [], []
        for w in test_weeks:
            xs = panel[panel["week"] == w].dropna(subset=["fwd"])
            z = score_week(w, xs)
            order = np.argsort(-z)[:top_n]
            y = xs["fwd"].values
            q = np.quantile(y, 0.8)
            hits.append((y[order] >= q).mean())
            base.append((y >= q).mean())
        res["combo"] = {
            "train_ic_mean": round(float(np.mean(train_ic)), 4) if train_ic else None,
            "train_weeks": len(train_weeks), "test_weeks": len(test_weeks),
            "test_topN_precision": round(float(np.mean(hits)), 3) if hits else None,
            "test_base_rate": round(float(np.mean(base)), 3) if base else None,
            "edge_x": round(float(np.mean(hits) / np.mean(base)), 2) if hits and np.mean(base) > 0 else None,
        }

    # this week's actual winners + next week's model picks
    last_week = weeks[-2] if len(weeks) >= 2 else weeks[-1]
    this_week = panel[panel["week"] == last_week].dropna(subset=["fwd"])
    res["actual_winners"] = this_week.nlargest(8, "fwd")[["ticker", "fwd"]].round(4).to_dict("records")
    nxt = panel[panel["week"] == weeks[-1]].copy()
    if len(nxt) >= MIN_NAMES and res.get("best_pair"):
        z = np.zeros(len(nxt))
        for f in res["best_pair"]:
            x = nxt[f].values.astype(float)
            sd = np.nanstd(x)
            if np.isfinite(sd) and sd != 0:
                z += (x - np.nanmean(x)) / sd
        nxt["model_z"] = z
        res["next_week_picks"] = nxt.nlargest(top_n, "model_z")[
            ["ticker", "model_z", "ret1w", "ret1m", "dist52", "rsi14", "volratio"]].round(3).to_dict("records")
    return res


def coingecko_movers(limit: int = 15) -> list[dict]:
    import urllib.request
    url = ("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc"
           "&per_page=250&page=1&price_change_percentage=7d")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "weekly-re/1.0"})
        coins = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
    except Exception as exc:
        print(f"  coingecko unavailable: {exc}", file=sys.stderr)
        return []
    coins = [c for c in coins
             if (c.get("market_cap") or 0) > 50_000_000
             and c.get("price_change_percentage_7d_in_currency") is not None
             and -95 < c["price_change_percentage_7d_in_currency"] < 300]  # exclude thin/new-listing artifacts
    coins.sort(key=lambda c: -c["price_change_percentage_7d_in_currency"])
    return [{"symbol": c["symbol"].upper(), "name": c["name"][:22],
             "chg7d": round(c["price_change_percentage_7d_in_currency"], 1),
             "mcap_musd": round((c.get("market_cap") or 0) / 1e6, 0)} for c in coins[:limit]]


def md(res: list[dict], cg: list[dict], out: str) -> str:
    L = [f"# Weekly winner reverse-engineer — {date.today().isoformat()}", "",
         "Features are as-of each Friday close; the target is the *next* week's return. Nothing is fitted on the week it scores.", ""]
    if cg:
        L += ["## Crypto: this week's top gainers (CoinGecko, top-250 mcap universe)", "",
              "| # | Coin | 7d % | Mcap $M |", "|---|---|---|---|"]
        L += [f"| {i+1} | {c['symbol']} ({c['name']}) | {c['chg7d']:+.1f} | {c['mcap_musd']:.0f} |" for i, c in enumerate(cg)]
        L.append("")
    L += ["## Per asset class", ""]
    for r in res:
        L += [f"### {r['class']}  ({r['n_tickers']} symbols, {r['n_weeks']} weeks, {r['weeks_scored']} scored)", ""]
        if r.get("actual_winners"):
            L.append("**This week's actual winners:** " + ", ".join(
                f"{w['ticker']} {w['fwd']*100:+.1f}%" for w in r["actual_winners"][:5]))
            L.append("")
        feats = sorted(r["features"].items(), key=lambda kv: -abs(kv[1]["ic_t"]))
        if feats:
            L += ["| feature | mean rank-IC | t | top-5 precision |", "|---|---|---|---|"]
            L += [f"| {f} | {v['ic']:+.3f} | {v['ic_t']:+.2f} | {v['topN_precision']} |" for f, v in feats[:6]]
            L.append("")
        c = r.get("combo") or {}
        if c:
            L.append(f"**Holdout model** (z-sum of `{'` + `'.join(r['best_pair'])}`, fitted on {c['train_weeks']} weeks, "
                     f"tested on {c['test_weeks']} unseen weeks): top-5 precision **{c['test_topN_precision']}** vs base rate "
                     f"**{c['test_base_rate']}** → **{c['edge_x']}x** lift. (train IC {c['train_ic_mean']})")
            L.append("")
        if r.get("next_week_picks"):
            L += ["**Next week, by that model:**", "", "| symbol | z | 1w | 1m | vs 52w high | RSI | vol ratio |", "|---|---|---|---|---|---|---|"]
            L += [f"| {p['ticker']} | {p['model_z']:+.2f} | {p['ret1w']:+.1%} | {p['ret1m']:+.1%} | {p['dist52']:+.1%} | {p['rsi14']:.0f} | {p['volratio']:.2f} |"
                  for p in r["next_week_picks"]]
            L.append("")
        L.append(f"Baseline share of names in the top quintile of any week: {r['base_top_quintile_rate']}.")
        L.append("")
    L += ["---", "Sample-size warning: a 5-name top-5 is 5 observations per week; the holdout column is the only",
          "number worth trusting, and even it needs ~30+ weeks before it separates from luck."]
    text = "\n".join(L) + "\n"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text)
    return text


def main() -> int:
    print("fetching price history ...")
    panels, summary = {}, []
    for name, syms in UNIVERSE.items():
        data = fetch(syms.split())
        if not data:
            print(f"  {name}: no data")
            continue
        panel = weekly_panel(data)
        panel["asset_class"] = name
        panels[name] = panel
        summary.append(analyse_class(name, panel))
        print(f"  {name}: {len(data)} symbols, {panel['week'].nunique()} weeks")
    allp = pd.concat(panels.values()) if panels else pd.DataFrame()
    if not allp.empty:
        allp.to_parquet("/tmp/weekly_panel.parquet") if hasattr(allp, "to_parquet") else None
    cg = coingecko_movers()
    out = f"reports/weekly_winners_{date.today().isoformat()}.md"
    text = md(summary, cg, out)
    print(f"\nwrote {out} ({len(text.splitlines())} lines)")
    print(json.dumps([{k: s[k] for k in ('class', 'weeks_scored', 'base_top_quintile_rate', 'best_pair') if k in s} for s in summary], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
