#!/usr/bin/env python3
"""H-239 (CRYPTO) + H-240 (EQUITY): monthly top-gainer persistence.

Pre-registered 2026-11-23 in plans/2026-11-23-prereg-H-239-H-240-monthly-top-gainer.md BEFORE this
file was first run. The bar that document fixed:

    >= 48 scored monthly periods  AND  >= 15 symbols of breadth in every period.

Below either, the only permitted answer is UNTESTED / DATA_GAP - never "no edge found", never a pass.

Signal (FROZEN by the pre-registration, not chosen here):
    CRYPTO:  z(dollar_vol) + -z(vol1m)      dollar_vol = 63d median dollar volume, vol1m = 21d vol
    EQUITY:  z(dollar_vol) +  z(volratio)   volratio  = 5d mean volume / 63d mean volume
Signal at month-end t uses data STRICTLY BEFORE t (features shifted one session).
Entry at t's close, exit at the next month-end close, equal weight, top decile.
Benchmark = the UNIVERSE MEAN, never SPY (the H-237/H-238 lesson: a rule that cannot beat its own
average pick is buying the market with extra steps).

Cost: CRYPTO 20bp RT (stress 42.64bp), EQUITY 0.98bp RT (stress 12.0749bp).

Survivorship: both universes are names liquid TODAY. A PASS is therefore WEAK_PASS_SURVIVORSHIP_FLAGGED;
a FAIL needs no such caveat because survivorship inflates long-only results.

Read-only. Paper only. Not investment advice.

Usage:
    python3 tools/monthly_top_gainer.py               # both classes
    python3 tools/monthly_top_gainer.py --class EQUITY
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

warnings.filterwarnings("ignore")

OUT = ROOT / "reports" / "h239_h240_monthly_top_gainer_2026-11-23.json"
CACHE = ROOT / "data" / "cache" / "monthly_panel"

CRYPTO_UNIVERSE = (
    "BTC-USD ETH-USD SOL-USD BNB-USD XRP-USD DOGE-USD ADA-USD AVAX-USD LINK-USD DOT-USD LTC-USD "
    "BCH-USD TRX-USD TON-USD SHIB-USD UNI-USD ATOM-USD XLM-USD NEAR-USD APT-USD ARB-USD OP-USD "
    "INJ-USD SUI-USD SEI-USD TIA-USD FIL-USD ICP-USD HBAR-USD AAVE-USD ETC-USD PEPE-USD JUP-USD "
    "FET-USD ALGO-USD VET-USD MANA-USD SAND-USD GALA-USD EOS-USD MKR-USD CRV-USD GRT-USD"
).split()

EQUITY_UNIVERSE = """
AAPL MSFT NVDA AMZN GOOGL META TSLA AVGO BRK-B JPM V MA UNH XOM JNJ PG HD COST
ABBV MRK CVX PEP KO ADBE WMT CSCO CRM ACN LIN MCD TMO ABT DHR NKE TXN PM NEE
WFC DIS AMD QCOM BA INTC CAT GS AMGN IBM SPGI HON UPS RTX BKNG SBUX BLK AXP
DE ISRG GILD MDT SYK PLD ADI TJX VRTX C MMC LRCX KLAC PANW MU ADSK REGN
BSX ETN NOC FDX EMR APSL SLB AON PGR T FCX GM F DAL UAL AAL CCL NCLH MGM WYNN
LVS RCL MAR HLT YUM CMG DPZ LULU ROST TGT DG DLTR BBY ORCL SAP SHOP SQ PYPL
COIN MSTR HOOD SOFI PLTR SNOW NET CRWD DDOG ZS OKTA
""".split()

SPEC = {
    "CRYPTO": {"hypothesis": "H-239", "universe": CRYPTO_UNIVERSE,
               "features": ["dollar_vol", "vol1m"], "signs": [1, -1],
               "cost_bp": 20.0, "cost_stress_bp": 42.64},
    "EQUITY": {"hypothesis": "H-240", "universe": EQUITY_UNIVERSE,
               "features": ["dollar_vol", "volratio"], "signs": [1, 1],
               "cost_bp": 0.98, "cost_stress_bp": 12.0749},
}

MIN_PERIODS, MIN_BREADTH = 48, 15
TOP_FRAC = 0.10


def panel(tickers: list[str], label: str) -> pd.DataFrame:
    """Daily close+volume panel, cached. Volume matters: dollar_vol and volratio need it."""
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"{label}.parquet"
    if p.exists():
        return pd.read_parquet(p)
    import yfinance as yf
    df = yf.download(tickers, period="6y", interval="1d", progress=False, threads=True,
                     auto_adjust=True, group_by="column")
    if df is None or len(df) == 0:
        raise SystemExit(f"NO panel for {label} - refusing to invent one")
    if isinstance(df.columns, pd.MultiIndex):
        close = df["Close"]
        vol = df["Volume"]
    else:
        raise SystemExit(f"unexpected single-level columns for {label}")
    close = close.dropna(axis=1, how="all")
    vol = vol.reindex(columns=close.columns)
    long = pd.concat({"close": close, "volume": vol}, axis=1)
    long.to_parquet(p)
    return long


def features_for(close: pd.Series, vol: pd.Series) -> pd.DataFrame:
    f = pd.DataFrame(index=close.index)
    dv = close * vol.fillna(0)
    f["dollar_vol"] = dv.rolling(63).median()
    f["vol1m"] = close.pct_change().rolling(21).std()
    f["volratio"] = vol.rolling(5).mean() / vol.rolling(63).mean().replace(0, np.nan)
    return f


def month_ends(idx: pd.DatetimeIndex) -> list[pd.Timestamp]:
    s = pd.Series(idx, index=idx)
    return list(s.groupby([idx.year, idx.month]).last())


def block_bootstrap_ci(x: np.ndarray, block: int = 3, n: int = 4000, seed: int = 7) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    T = len(x)
    if T < block * 4:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    k = max(1, T // block)
    means = np.empty(n)
    for j in range(n):
        st = rng.integers(0, T - block, size=k)
        means[j] = np.concatenate([x[s:s + block] for s in st])[:T].mean()
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def run_class(label: str) -> dict:
    spec = SPEC[label]
    data = panel(spec["universe"], label.lower())
    close, vol = data["close"], data["volume"]
    print(f"\n[{label}] panel {close.shape[0]} bars x {close.shape[1]} names "
          f"{close.index[0].date()} .. {close.index[-1].date()}", flush=True)

    # features computed on the whole panel, then SHIFTED one session: signal at t excludes t's bar
    feats = {s: features_for(close[s].dropna(), vol[s]) for s in close.columns}
    me = [t for t in month_ends(close.index) if t in close.index]
    me = me[:-1]                                  # last month has no forward return

    periods, ics, breadth = [], [], []
    n_rejected_extreme = 0
    for a, b in zip(me[:-1], me[1:]):
        rows = {}
        for s, f in feats.items():
            pos = f.index.get_indexer([a])[0]
            if pos < 1:
                continue
            r = f.iloc[pos - 1]                    # strictly before the signal bar
            c0, c1 = close[s].get(a), close[s].get(b)
            if r.isna().any() or not (c0 and c1) or c0 <= 0:
                continue
            ret = float(c1 / c0 - 1.0)
            # DATA-INTEGRITY GUARD: a monthly crypto return outside (-95%, +500%) is a bad price
            # print (split-like jump, stale quote, unit change), not a market move. Reject the name
            # for that period and COUNT it - silently winsorising would manufacture a result.
            if not np.isfinite(ret) or ret < -0.95 or ret > 5.0:
                n_rejected_extreme += 1
                continue
            rows[s] = (r.to_dict(), ret)
        if len(rows) < MIN_BREADTH:
            continue
        breadth.append(len(rows))
        score = {}
        for fname, sign in zip(spec["features"], spec["signs"]):
            v = pd.Series({s: v[0][fname] for s, v in rows.items()}, dtype=float)
            sd = v.std(ddof=0)
            score[fname] = sign * (v - v.mean()) / (sd if sd and sd > 0 else 1.0)
        total = sum(score.values())
        rets = pd.Series({s: v[1] for s, v in rows.items()}, dtype=float)
        k = max(1, int(round(TOP_FRAC * len(total))))
        top = total.nlargest(k).index
        book = float(rets[top].mean())
        univ = float(rets.mean())
        periods.append({"month_end": str(a)[:10], "exit": str(b)[:10],
                        "n_names": len(rows), "k": k,
                        "book": book, "universe": univ, "excess": book - univ,
                        "hit": bool(book > univ),
                        "selected": list(top)})
        if total.notna().all() and len(total) >= 8:
            rho, _ = spearmanr(total.to_numpy(dtype=float), rets.to_numpy(dtype=float))
            if np.isfinite(rho):
                ics.append(float(rho))

    if not periods:
        return {"hypothesis": spec["hypothesis"], "asset_class": label,
                "status": "UNTESTED", "reason": "NO_PERIODS_BUILT"}

    ex = np.array([p["excess"] for p in periods], dtype=float)
    gross = np.array([p["book"] for p in periods], dtype=float)
    cost = spec["cost_bp"] / 1e4
    net = gross - cost
    lo, hi = block_bootstrap_ci(net - np.array([p["universe"] for p in periods], dtype=float))
    n_periods = len(periods)
    gross_ann = float(np.prod(1 + gross) ** (12 / n_periods) - 1)
    net_ann = float(np.prod(1 + net) ** (12 / n_periods) - 1)
    stress_net = gross - spec["cost_stress_bp"] / 1e4
    stress_ann = float(np.prod(1 + stress_net) ** (12 / n_periods) - 1)
    cost_survival = (net_ann / gross_ann) if gross_ann else None

    admissible = (n_periods >= MIN_PERIODS) and (min(breadth) >= MIN_BREADTH)
    if not admissible:
        verdict = "UNTESTED"
        reason = (f"DATA_GAP: {n_periods} scored periods (need {MIN_PERIODS}), "
                  f"min breadth {min(breadth)} (need {MIN_BREADTH})")
    elif lo > 0 and cost_survival is not None and cost_survival >= 0.60:
        verdict = "ACCEPTED_WEAK_PASS_SURVIVORSHIP_FLAGGED"
        reason = "CI lower bound > 0 and cost survival >= 0.60 on a survivor-conditioned universe"
    else:
        verdict = "REFUTED"
        reason = ("CI includes zero" if lo <= 0 else "cost survival < 0.60")

    return {
        "hypothesis": spec["hypothesis"], "asset_class": label,
        "prereg": "plans/2026-11-23-prereg-H-239-H-240-monthly-top-gainer.md",
        "features": spec["features"], "signs": spec["signs"], "top_frac": TOP_FRAC,
        "universe_n_requested": len(spec["universe"]),
        "panel": {"start": str(close.index[0].date()), "end": str(close.index[-1].date()),
                  "bars": int(close.shape[0]), "names": int(close.shape[1])},
        "n_periods": n_periods, "n_periods_required": MIN_PERIODS,
        "name_periods_rejected_as_extreme": n_rejected_extreme,
        "breadth_min": int(min(breadth)), "breadth_max": int(max(breadth)),
        "breadth_required": MIN_BREADTH,
        "mean_excess_bp": round(1e4 * float(ex.mean()), 2),
        "median_excess_bp": round(1e4 * float(np.median(ex)), 2),
        "excess_ci95_bp": [round(1e4 * lo, 2), round(1e4 * hi, 2)],
        "hit_rate": round(float(np.mean([p["hit"] for p in periods])), 3),
        "mean_rank_ic": round(float(np.mean(ics)), 4) if ics else None,
        "ic_t": (round(float(np.mean(ics) / (np.std(ics, ddof=1) / math.sqrt(len(ics)))), 2)
                 if ics and len(ics) > 2 and np.std(ics, ddof=1) > 0 else None),
        "gross_ann_pct": round(100 * gross_ann, 2),
        "net_ann_pct": round(100 * net_ann, 2),
        "net_at_stress_cost_ann_pct": round(100 * stress_ann, 2),
        "cost_survival": round(cost_survival, 3) if cost_survival is not None else None,
        "cost_bp_rt": spec["cost_bp"], "cost_stress_bp_rt": spec["cost_stress_bp"],
        "status": verdict, "reason": reason,
        "periods": periods,
    }


import math  # noqa: E402  (used in run_class)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--class", dest="cls", choices=["CRYPTO", "EQUITY", "BOTH"], default="BOTH")
    a = ap.parse_args()
    classes = ["CRYPTO", "EQUITY"] if a.cls == "BOTH" else [a.cls]
    out = {"generated_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
           "hypotheses": ["H-239", "H-240"],
           "prereg": "plans/2026-11-23-prereg-H-239-H-240-monthly-top-gainer.md",
           "observation_bar": {"n_periods_min": MIN_PERIODS, "breadth_min": MIN_BREADTH},
           "results": {}}
    for c in classes:
        r = run_class(c)
        out["results"][c] = r
        print(f"  {c}: {r['status']} | n_periods={r.get('n_periods')} "
              f"breadth_min={r.get('breadth_min')} | excess {r.get('mean_excess_bp')}bp "
              f"CI {r.get('excess_ci95_bp')} | {r['reason']}", flush=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
