#!/usr/bin/env python3
"""Test the audit2 doctrine: "volatility scaling is free alpha (+0.3 Sharpe)".

Doctrine under test (audit2, asserted as established fact):
    "Volatility scaling is free alpha. Simply scaling positions by inverse
     realized vol improves Sharpe by 0.3+ for any momentum strategy."

Method
------
* Universe: liquid crypto daily closes via ccxt (Binance, USDT pairs) plus the
  ECB daily FX cache in data/forex_rate_cache/. No yfinance (Yahoo 429 this
  session), no Stooq (JS proof-of-work challenge).
* Signal: cross-sectional time-series momentum per asset -- go long an asset
  when its trailing L-day return is positive, else flat. L in {21, 63}.
* Variant A (plain): equal weight across the assets that are long, gross 1.0.
* Variant B (vol-scaled): weight proportional to 1/sigma_20d (inverse realised
  vol), renormalised to the SAME gross exposure as A on every bar.
* Costs: 1x and 2x round-trip per unit turnover.
* Control: rescale B's daily returns by a single constant so its realised vol
  equals A's realised vol, then recompute Sharpe. If the Sharpe gain survives
  that, vol scaling added something beyond "take less risk"; if it collapses,
  the gain was only an exposure change.

Returns are next-bar (signal at t applied to the t+1 return), so there is no
look-ahead. Everything is deterministic given the downloaded bars; the JSON
output records the universe, the bar window, and every number reported.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics as st
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FX_DIR = REPO / "data" / "forex_rate_cache"
CACHE_DIR = REPO / "reports" / "vol_scaling_cache"

CRYPTO_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT",
                 "ADA/USDT", "BNB/USDT", "DOGE/USDT", "LTC/USDT"]
FX_PAIRS = ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD", "USDCHF"]


# ── data loading ─────────────────────────────────────────────────────────────
def load_crypto(symbol: str, limit: int = 1500) -> list[float] | None:
    """Daily closes from Binance via ccxt, cached on disk."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / (symbol.replace("/", "_") + ".json")
    if cache.exists():
        try:
            return json.load(open(cache))["closes"]
        except Exception:
            pass
    try:
        import ccxt
        ex = ccxt.binance({"enableRateLimit": True, "timeout": 20000})
        ohlcv = ex.fetch_ohlcv(symbol, "1d", limit=limit)
        closes = [float(r[4]) for r in ohlcv if r[4]]
        if len(closes) < 120:
            return None
        json.dump({"symbol": symbol, "closes": closes}, open(cache, "w"))
        return closes
    except Exception as e:  # noqa: BLE001
        print(f"  skip {symbol}: {e}", file=sys.stderr)
        return None


def load_fx(pair: str) -> list[float] | None:
    path = FX_DIR / f"{pair}.csv"
    if not path.exists():
        return None
    out = []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                out.append(float(row["close"]))
            except (KeyError, ValueError):
                continue
    return out if len(out) >= 120 else None


# ── strategy ────────────────────────────────────────────────────────────────
def returns_of(closes: list[float]) -> list[float]:
    return [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes))
            if closes[i - 1]]


def backtest(series: dict[str, list[float]], lookback: int, cost_bps: float) -> dict:
    """Cross-sectional TS-momentum, equal-weight vs inverse-vol weight.

    Aligns on the shortest series length so all assets share a bar index.
    """
    n = min(len(v) for v in series.values())
    names = list(series)
    px = {k: v[-n:] for k, v in series.items()}
    rets = {k: returns_of(v) for k, v in px.items()}          # len n-1
    m = n - 1                                                 # return bars

    def realized_vol(r: list[float], end: int, win: int = 20) -> float:
        seg = r[max(0, end - win + 1):end + 1]
        return st.pstdev(seg) if len(seg) >= 5 else 0.0

    eq_a, eq_b = [], []
    prev_w_a: dict[str, float] = {}
    prev_w_b: dict[str, float] = {}
    cost = cost_bps / 1e4
    for t in range(lookback, m):
        longs, inv = [], {}
        for k in names:
            r = rets[k]
            mom = px[k][t] / px[k][t - lookback] - 1.0 if px[k][t - lookback] else 0.0
            if mom > 0:
                v = realized_vol(r, t)
                longs.append(k)
                inv[k] = 1.0 / v if v > 1e-9 else 0.0
        w_a = {k: 1.0 / len(longs) for k in longs} if longs else {}
        s = sum(inv.values())
        w_b = {k: inv[k] / s for k in longs} if longs and s > 0 else (
            {k: 1.0 / len(longs) for k in longs} if longs else {})
        r_a = sum(w_a.get(k, 0.0) * rets[k][t] for k in names)
        r_b = sum(w_b.get(k, 0.0) * rets[k][t] for k in names)
        to_a = sum(abs(w_a.get(k, 0) - prev_w_a.get(k, 0)) for k in names)
        to_b = sum(abs(w_b.get(k, 0) - prev_w_b.get(k, 0)) for k in names)
        eq_a.append(r_a - cost * to_a)
        eq_b.append(r_b - cost * to_b)
        prev_w_a, prev_w_b = w_a, w_b
    return {"plain": eq_a, "volscaled": eq_b}


def stats(rets: list[float]) -> dict:
    if len(rets) < 30:
        return {}
    mu = st.mean(rets)
    sd = st.pstdev(rets)
    ann = math.sqrt(365)
    sharpe = (mu / sd * ann) if sd > 0 else 0.0
    eq, peak, mdd = 1.0, 1.0, 0.0
    for r in rets:
        eq *= (1 + r)
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
    return {"n": len(rets), "sharpe": round(sharpe, 4),
            "ann_vol_pct": round(sd * ann * 100, 3),
            "ann_ret_pct": round((eq ** (ann / len(rets)) - 1) * 100, 3),
            "max_dd_pct": round(mdd * 100, 3)}


def rescaled_control(plain: list[float], volscaled: list[float]) -> dict:
    """Rescale vol-scaled returns to the same realised vol as plain, then Sharpe."""
    sd_a, sd_b = st.pstdev(plain), st.pstdev(volscaled)
    k = sd_a / sd_b if sd_b > 0 else 1.0
    scaled = [k * r for r in volscaled]
    return {"scale_factor": round(k, 4), **stats(scaled)}


def run_universe(label: str, series: dict[str, list[float]]) -> dict:
    out = {"universe": label, "assets": sorted(series), "results": {}}
    for lookback in (21, 63):
        for cost_bps, cost_tag in ((10, "1x"), (20, "2x")):
            bt = backtest(series, lookback, cost_bps)
            a, b = stats(bt["plain"]), stats(bt["volscaled"])
            if not a or not b:
                continue
            ctrl = rescaled_control(bt["plain"], bt["volscaled"])
            out["results"][f"L{lookback}_{cost_tag}"] = {
                "plain": a, "volscaled": b,
                "sharpe_delta_raw": round(b["sharpe"] - a["sharpe"], 4),
                "control_equal_vol": ctrl,
                "sharpe_delta_equal_vol": round(ctrl["sharpe"] - a["sharpe"], 4),
            }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports/vol_scaling_test_20261122.json")
    args = ap.parse_args()

    crypto = {}
    for s in CRYPTO_SYMBOLS:
        c = load_crypto(s)
        if c:
            crypto[s] = c
    fx = {}
    for p in FX_PAIRS:
        c = load_fx(p)
        if c:
            fx[p] = c

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "doctrine": "volatility scaling is free alpha: inverse-vol sizing improves "
                    "Sharpe by 0.3+ for any momentum strategy",
        "method": "TS cross-sectional momentum (long if trailing return>0), "
                  "next-bar returns, equal-weight vs 1/sigma_20d weight at equal gross, "
                  "cost per turnover; control rescales vol-scaled to equal realised vol",
        "n_crypto_assets": len(crypto), "n_fx_assets": len(fx),
        "crypto": run_universe("crypto_binance_daily", crypto) if len(crypto) >= 3 else None,
        "fx": run_universe("ecb_fx_daily", fx) if len(fx) >= 3 else None,
    }
    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(report, open(out, "w"), indent=1)

    for block in ("crypto", "fx"):
        r = report.get(block)
        if not r:
            print(f"\n{block}: UNMEASURABLE (fewer than 3 usable series)")
            continue
        print(f"\n=== {block} ({len(r['assets'])} assets) ===")
        print(f"{'config':10s} {'plain SR':>9s} {'vol SR':>8s} {'raw dSR':>8s} "
              f"{'ctrl SR':>8s} {'eqvol dSR':>9s} {'plain vol%':>10s} {'vol vol%':>9s}")
        for k, v in r["results"].items():
            print(f"{k:10s} {v['plain']['sharpe']:9.3f} {v['volscaled']['sharpe']:8.3f} "
                  f"{v['sharpe_delta_raw']:8.3f} {v['control_equal_vol']['sharpe']:8.3f} "
                  f"{v['sharpe_delta_equal_vol']:9.3f} {v['plain']['ann_vol_pct']:10.2f} "
                  f"{v['volscaled']['ann_vol_pct']:9.2f}")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
