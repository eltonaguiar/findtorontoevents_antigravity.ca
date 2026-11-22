#!/usr/bin/env python3
"""Funding-rate carry: delta-neutral long-spot / short-perp on real Binance history.

Programme items 9, 10, 30, 47. The pre-declared rule lives in
docs/edge_research/06_FUNDING_CARRY_2026-11-22.md §0 and was written before this
script was first run. This script implements exactly that rule; it does not tune.

Position: equal notional long spot + short USDT-M perp, same asset.
PnL = funding received by the short perp
      + basis convergence  N*(b_entry - b_exit),  b = (Pp-Ps)/Ps
      - four taker fills (open both legs, close both legs).

Data (all real, all saved raw for reproducibility):
  * funding: GET https://fapi.binance.com/fapi/v1/fundingRate  (paginated)
  * perp 4h klines: GET https://fapi.binance.com/fapi/v1/klines
  * spot 4h klines: GET https://api.binance.com/api/v3/klines
  * cost: reports/cost_measurement_20261122.json (measured order books)

Nothing is fabricated: if a pull fails the symbol is marked BLOCKED with the error.

Usage:
  python3 tools/funding_carry_backtest.py                 # fetch (cached) + analyse
  python3 tools/funding_carry_backtest.py --refetch       # force a fresh pull
  python3 tools/funding_carry_backtest.py --cost-size 100000
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "reports" / "funding_carry_raw"
OUT_JSON = ROOT / "reports" / "funding_carry_20261122.json"
COST_REPORT = ROOT / "reports" / "cost_measurement_20261122.json"

FAPI = "https://fapi.binance.com"
SPOT = "https://api.binance.com"

# Pre-declared in the doc §0: the five Binance assets whose spot cost was measured.
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
HOLD_DAYS = [1, 3, 7, 14, 30, 90]
INTERVALS_PER_DAY = 3          # funding every 8h
COST_MULT = [1.0, 2.0]         # item 47: 1x measured, 2x stress
TRAILING_INTERVALS = 3         # 24h trailing funding for entry condition B
UA = {"User-Agent": "curl/8.5"}


# ----------------------------------------------------------------------------- io
def http_json(url: str, params: dict | None = None, retries: int = 3) -> list | dict:
    q = ""
    if params:
        q = "?" + "&".join(f"{k}={v}" for k, v in params.items())
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url + q, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read()[:300].decode(errors="replace")
            last = f"HTTP {e.code}: {body}"
            if e.code in (418, 429):          # rate limited / banned
                time.sleep(2 + attempt * 3)
                continue
            raise RuntimeError(f"{url}{q} -> {last}") from None
        except Exception as e:              # noqa: BLE001 - network of any kind
            last = repr(e)
            time.sleep(1 + attempt)
    raise RuntimeError(f"{url}{q} failed after {retries} tries: {last}")


def cache_path(name: str) -> Path:
    return RAW_DIR / name


def load_or_fetch(name: str, fetch, refetch: bool):
    p = cache_path(name)
    if p.exists() and not refetch:
        return json.loads(p.read_text())
    data = fetch()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data))
    return data


# The API caps a page at 500 rows regardless of the requested limit (observed
# 2026-11-22: limit=1000 and limit=1500 both return 500). Page until a short page.
FUNDING_EPOCH_MS = 1546300800000   # 2019-01-01: before any USDT-M perp existed


def fetch_funding(sym: str) -> list:
    out, start = [], FUNDING_EPOCH_MS
    while True:
        page = http_json(f"{FAPI}/fapi/v1/fundingRate",
                         {"symbol": sym, "startTime": start, "limit": 500})
        if not page:
            break
        out.extend(page)
        if len(page) < 500:
            break
        start = int(page[-1]["fundingTime"]) + 1
        time.sleep(0.15)
    return out


def fetch_klines(base: str, sym: str, interval: str, start_ms: int, end_ms: int) -> list:
    out, start = [], start_ms
    while start < end_ms:
        page = http_json(f"{base}/{'fapi/v1' if base == FAPI else 'api/v3'}/klines",
                         {"symbol": sym, "interval": interval, "startTime": start,
                          "endTime": end_ms, "limit": 500})
        if not page:
            break
        out.extend(page)
        nxt = int(page[-1][0]) + 1
        if nxt <= start or int(page[-1][0]) >= end_ms:   # no progress / reached the end
            break
        start = nxt
        time.sleep(0.15)
    return out


# ----------------------------------------------------------------------- helpers
def klines_to_df(raw: list) -> pd.DataFrame:
    df = pd.DataFrame(raw, columns=["open_time", "open", "high", "low", "close", "volume",
                                    "close_time", "qav", "trades", "tbb", "tbq", "ignore"])
    df["ts"] = pd.to_datetime(df["open_time"].astype("int64"), unit="ms", utc=True)
    for c in ("open", "high", "low", "close"):
        df[c] = df[c].astype(float)
    return df[["ts", "open", "high", "low", "close"]].drop_duplicates("ts").set_index("ts")


def measured_pair_cost_bp(size_usd: int) -> tuple[float, dict]:
    """Pair round-trip cost in bp = 2 x (taker fee RT + spot spread RT) for one leg."""
    rep = json.loads(COST_REPORT.read_text())
    rows, per_leg = {}, []
    for v in rep["venues"]:
        if v["exchange"] != "binance":
            continue
        for sym, sd in v["symbols"].items():
            s = sd["summary"]
            bucket = s["round_trip_spread_bp_by_size"].get(str(size_usd))
            if not bucket:
                continue
            # all_in_round_trip_bp = spread round trip + 2 x taker fee (the fee dominates)
            allin = float(bucket.get("all_in_round_trip_bp", bucket["median"]))
            rows[sym] = allin
            per_leg.append(allin)
    mean_leg = float(np.mean(per_leg)) if per_leg else float("nan")
    return 2.0 * mean_leg, {"per_leg_round_trip_bp": rows,
                            "mean_leg_round_trip_bp": mean_leg,
                            "pair_round_trip_bp": 2.0 * mean_leg,
                            "size_usd": size_usd,
                            "source": str(COST_REPORT.relative_to(ROOT)),
                            "note": "perp spread assumed equal to spot spread (not measured)"}


def max_drawdown(equity: np.ndarray) -> float:
    if len(equity) == 0:
        return 0.0
    peak = np.maximum.accumulate(equity)
    dd = equity - peak
    return float(dd.min())


def ann_sharpe(per_interval: np.ndarray) -> tuple[float, float]:
    x = per_interval[np.isfinite(per_interval)]
    if len(x) < 2 or x.std(ddof=1) == 0:
        return float("nan"), float("nan")
    ann = math.sqrt(INTERVALS_PER_DAY * 365)
    return float(x.std(ddof=1) * ann), float(x.mean() / x.std(ddof=1) * ann)


# ----------------------------------------------------------------------- analysis
def analyse_symbol(sym: str, fdf: pd.DataFrame, pdf: pd.DataFrame, sdf: pd.DataFrame,
                   pair_cost_bp: float) -> dict:
    """fdf: funding (ts, rate, mark). pdf/sdf: perp/spot 4h closes."""
    # perp close at each funding time = last 4h close at or before the funding stamp
    pf = pdf["close"].reindex(fdf["ts"], method="ffill")
    sf = sdf["close"].reindex(fdf["ts"], method="ffill")
    ok = (pf.notna() & sf.notna()).to_numpy()   # positional, aligns with fdf's RangeIndex
    d = fdf.loc[ok].copy()
    d["perp"] = pf.to_numpy()[ok]
    d["spot"] = sf.to_numpy()[ok]
    d["basis_bp"] = (d["perp"] - d["spot"]) / d["spot"] * 1e4

    # 4h basis series over the same window (item 30)
    b4 = (pdf["close"] - sdf["close"]) / sdf["close"] * 1e4
    b4 = b4.dropna()
    basis_stats = {
        "n_4h_bars": int(len(b4)),
        "mean_bp": float(b4.mean()), "median_bp": float(b4.median()),
        "std_bp": float(b4.std(ddof=1)),
        "p1_bp": float(b4.quantile(0.01)), "p99_bp": float(b4.quantile(0.99)),
        "min_bp": float(b4.min()), "max_bp": float(b4.max()),
    }

    f = d["rate"].values.astype(float)
    basis = d["basis_bp"].values.astype(float)
    n = len(f)
    dist = {
        "n_intervals": int(n),
        "mean": float(np.mean(f)), "median": float(np.median(f)),
        "pct_positive": float(100 * np.mean(f > 0)),
        "worst_negative": float(np.min(f)),
        "p1": float(np.quantile(f, 0.01)), "p5": float(np.quantile(f, 0.05)),
        "p95": float(np.quantile(f, 0.95)), "p99": float(np.quantile(f, 0.99)),
        "mean_annualised_apr": float(np.mean(f) * INTERVALS_PER_DAY * 365),
    }

    def run_holds(mask: np.ndarray | None, cost_bp: float) -> dict:
        """Non-overlapping holds of H days for every pre-declared H."""
        res = {}
        for H in HOLD_DAYS:
            k = H * INTERVALS_PER_DAY
            trades = []
            i = 0
            while i + k <= n:
                sl = slice(i, i + k)
                if mask is not None and not mask[sl].all():
                    i += 1
                    continue
                gross = float(f[sl].sum())                      # fraction of notional
                bchg = float(basis[i] - basis[i + k - 1]) / 1e4  # fraction of notional
                net = gross + bchg - cost_bp / 1e4
                trades.append({"start": str(d["ts"].iloc[i].date()),
                               "gross": gross, "basis": bchg, "net": net})
                i += k
            if not trades:
                res[H] = {"n_trades": 0}
                continue
            g = np.array([t["gross"] for t in trades])
            b = np.array([t["basis"] for t in trades])
            net = np.array([t["net"] for t in trades])
            years = H / 365.0
            sd = net.std(ddof=1) if len(net) > 1 else float("nan")
            res[H] = {
                "n_trades": int(len(trades)),
                "gross_mean_pct": float(g.mean() * 100),
                "gross_sd_pct": float(g.std(ddof=1) * 100) if len(g) > 1 else float("nan"),
                "basis_mean_pct": float(b.mean() * 100),
                "basis_sd_pct": float(b.std(ddof=1) * 100) if len(b) > 1 else float("nan"),
                "net_mean_pct": float(net.mean() * 100),
                "gross_apr": float(g.mean() / years),
                "net_apr": float(net.mean() / years),
                "win_rate_pct": float(100 * np.mean(net > 0)),
                "sharpe_ann": float(net.mean() / sd * math.sqrt(365 / H)) if sd and sd > 0 else float("nan"),
                "max_dd_pct": float(max_drawdown(np.cumsum(net)) * 100),
            }
        return res

    # A: always-on
    always = run_holds(None, pair_cost_bp)
    trail = np.convolve(f, np.ones(TRAILING_INTERVALS), "full")  # trail[i-2] = sum up to i
    trail_sum = np.full(n, np.nan)
    trail_sum[TRAILING_INTERVALS - 1:] = trail[: n - TRAILING_INTERVALS + 1]
    # condition known at interval i -> hold during interval i+1
    mask_b = np.zeros(n, dtype=bool)
    mask_b[1:] = trail_sum[:-1] > 0
    positive = run_holds(mask_b, pair_cost_bp)

    # continuous always-on over the whole window (one position).
    # Two curves: funding only (the premium), and marked-to-market
    # (funding + basis change of the pair), which is what the position earns.
    vol_ann, sharpe_ann = ann_sharpe(f)
    cum = np.cumsum(f)
    mtm_i = f[1:] + (basis[:-1] - basis[1:]) / 1e4   # per-interval, n-1 points
    mtm_vol, mtm_sharpe = ann_sharpe(mtm_i)
    mtm_cum = np.cumsum(mtm_i)
    whole = {
        "n_intervals": int(n),
        "gross_total_pct": float(cum[-1] * 100),
        "gross_apr": float(f.mean() * INTERVALS_PER_DAY * 365),
        "funding_vol_ann": vol_ann,
        "sharpe_ann": sharpe_ann,
        "max_dd_pct": float(max_drawdown(cum) * 100),
        "mtm": {   # funding + basis convergence, no entry/exit cost
            "total_pct": float(mtm_cum[-1] * 100),
            "apr": float(mtm_i.mean() * INTERVALS_PER_DAY * 365),
            "vol_ann": mtm_vol, "sharpe_ann": mtm_sharpe,
            "max_dd_pct": float(max_drawdown(mtm_cum) * 100),
        },
    }

    # B episodes: consecutive held intervals, each pays the full pair cost
    episodes, i = [], 0
    while i < n:
        if mask_b[i]:
            j = i
            while j < n and mask_b[j]:
                j += 1
            g = float(f[i:j].sum())
            bchg = float(basis[i] - basis[j - 1]) / 1e4
            days = (j - i) / INTERVALS_PER_DAY
            episodes.append({"start": str(d["ts"].iloc[i].date()), "days": days,
                             "gross": g, "basis": bchg, "net": g + bchg - pair_cost_bp / 1e4})
            i = j
        else:
            i += 1
    ep = pd.DataFrame(episodes)
    ep_summary = {"n_episodes": int(len(ep))}
    if len(ep):
        ep_years = ep["days"] / 365
        ep_summary.update({
            "median_days": float(ep["days"].median()),
            "mean_days": float(ep["days"].mean()),
            "gross_mean_pct": float(ep["gross"].mean() * 100),
            "net_mean_pct": float(ep["net"].mean() * 100),
            "pct_episodes_profitable": float(100 * np.mean(ep["net"] > 0)),
            "pct_days_holding_cost": float(100 * np.mean(ep["gross"] > pair_cost_bp / 1e4)),
            "time_in_market_pct": float(100 * ep["days"].sum() / n * INTERVALS_PER_DAY),
            "total_gross_pct": float(ep["gross"].sum() * 100),
            "total_net_pct": float(ep["net"].sum() * 100),
            "median_breakeven_days": float(pair_cost_bp / 1e4 /
                                          (ep["gross"] / ep["days"]).median() * 1e0)
            if (ep["gross"] / ep["days"]).median() > 0 else float("inf"),
        })

    # break-even holding period: cost / funding earned per day
    mean_day = float(np.mean(f) * INTERVALS_PER_DAY)
    med_day = float(np.median(f) * INTERVALS_PER_DAY)
    breakeven = {
        "cost_pair_bp": pair_cost_bp,
        "funding_per_day_mean_pct": mean_day * 100,
        "funding_per_day_median_pct": med_day * 100,
        "breakeven_days_at_mean": float(pair_cost_bp / 1e4 / mean_day) if mean_day > 0 else float("inf"),
        "breakeven_days_at_median": float(pair_cost_bp / 1e4 / med_day) if med_day > 0 else float("inf"),
        "empirical_first_H_net_positive": next(
            (H for H in HOLD_DAYS if always.get(H, {}).get("net_apr", -1) > 0), None),
    }

    # trailing 12 months (always-on, whole sub-window)
    cut = d["ts"].max() - pd.Timedelta(days=365)
    f12 = d.loc[d["ts"] >= cut, "rate"].values
    last12 = {"n_intervals": int(len(f12)),
              "gross_apr": float(np.mean(f12) * INTERVALS_PER_DAY * 365) if len(f12) else None,
              "pct_positive": float(100 * np.mean(f12 > 0)) if len(f12) else None}

    return {
        "symbol": sym,
        "window": f"{d['ts'].iloc[0].date()}..{d['ts'].iloc[-1].date()}",
        "years": float((d['ts'].iloc[-1] - d['ts'].iloc[0]).days / 365.25),
        "funding_distribution": dist,
        "basis_4h": basis_stats,
        "always_on_whole_window": whole,
        "always_on_holds": always,
        "positive_trailing_holds": positive,
        "positive_trailing_episodes": ep_summary,
        "breakeven": breakeven,
        "last_12_months": last12,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="*", default=SYMBOLS)
    ap.add_argument("--cost-size", type=int, default=10000,
                    help="notional bucket for the measured cost (default $10k, pre-declared)")
    ap.add_argument("--cost-mult", type=float, default=1.0,
                    help="cost multiplier; item 47 re-runs at 2.0")
    ap.add_argument("--refetch", action="store_true")
    ap.add_argument("--out", default=str(OUT_JSON))
    a = ap.parse_args()

    pair_cost_1x, cost_meta = measured_pair_cost_bp(a.cost_size)
    pair_cost = pair_cost_1x * a.cost_mult
    print(f"measured pair round-trip cost: {pair_cost_1x:.3f} bp x {a.cost_mult:g} = {pair_cost:.3f} bp "
          f"(2 x {cost_meta['mean_leg_round_trip_bp']:.3f} bp per leg; "
          f"fee 20bp RT + spot spread, ${a.cost_size} notional)")

    per_symbol, blocked = {}, {}
    for sym in a.symbols:
        try:
            funding_raw = load_or_fetch(f"funding_{sym}.json", lambda s=sym: fetch_funding(s), a.refetch)
            if not funding_raw:
                blocked[sym] = "empty funding history"
                continue
            fdf = pd.DataFrame(funding_raw)
            fdf["ts"] = pd.to_datetime(fdf["fundingTime"].astype("int64"), unit="ms", utc=True)
            # markPrice is blank before 2023-11 in the API's own history and is not used:
            # the perp price comes from klines. Only the funding rate matters here.
            fdf["rate"] = fdf["fundingRate"].astype(float)
            fdf = fdf[["ts", "rate"]].sort_values("ts").drop_duplicates("ts").reset_index(drop=True)

            start_ms = int(fdf["ts"].iloc[0].timestamp() * 1000)
            end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            perp_raw = load_or_fetch(f"klines_4h_{sym}_perp.json",
                                     lambda s=sym, a1=start_ms, b1=end_ms: fetch_klines(FAPI, s, "4h", a1, b1),
                                     a.refetch)
            spot_sym = sym[:-4] + "USDT" if sym.endswith("USDT") else sym
            spot_pair = spot_sym.replace("USDT", "")  # BTCUSDT -> BTC for the spot endpoint
            spot_raw = load_or_fetch(f"klines_4h_{sym}_spot.json",
                                     lambda p=spot_pair, a1=start_ms, b1=end_ms: fetch_klines(SPOT, p + "USDT", "4h", a1, b1),
                                     a.refetch)
            pdf, sdf = klines_to_df(perp_raw), klines_to_df(spot_raw)
            if pdf.empty or sdf.empty:
                blocked[sym] = "empty klines"
                continue
            per_symbol[sym] = analyse_symbol(sym, fdf, pdf, sdf, pair_cost)
            w = per_symbol[sym]
            print(f"  {sym:<8} {w['window']} ({w['years']:.1f}y)  "
                  f"gross APR {w['always_on_whole_window']['gross_apr']*100:+.2f}%  "
                  f"mean 8h {w['funding_distribution']['mean']*1e4:+.3f}bp  "
                  f"%pos {w['funding_distribution']['pct_positive']:.1f}%  "
                  f"breakeven(mean) {w['breakeven']['breakeven_days_at_mean']:.2f}d")
        except Exception as e:  # noqa: BLE001
            blocked[sym] = f"{type(e).__name__}: {e}"
            print(f"  {sym}: BLOCKED {blocked[sym]}")

    # aggregate across symbols (equal weight)
    def agg(fn):
        vals = [fn(w) for w in per_symbol.values()]
        vals = [v for v in vals if v is not None and np.isfinite(v)]
        return float(np.mean(vals)) if vals else float("nan")

    agg_always = {}
    for H in HOLD_DAYS:
        rows = [w["always_on_holds"].get(H, {}) for w in per_symbol.values()]
        rows = [r for r in rows if r.get("n_trades")]
        if rows:
            agg_always[H] = {k: float(np.mean([r[k] for r in rows]))
                             for k in ("gross_apr", "net_apr", "basis_mean_pct", "sharpe_ann", "max_dd_pct")}
            agg_always[H]["n_symbols"] = len(rows)

    summary = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "symbols": list(per_symbol),
        "blocked": blocked,
        "cost": cost_meta,
        "cost_mult": a.cost_mult,
        "pair_cost_bp_1x": pair_cost_1x,
        "pair_cost_bp_used": pair_cost,
        "aggregate_always_on_by_H": {str(k): v for k, v in agg_always.items()},
        "aggregate_mean_gross_apr": agg(lambda w: w["always_on_whole_window"]["gross_apr"]),
        "aggregate_mean_sharpe": agg(lambda w: w["always_on_whole_window"]["sharpe_ann"]),
        "aggregate_mean_breakeven_days_at_mean":
            agg(lambda w: w["breakeven"]["breakeven_days_at_mean"]),
        "aggregate_mean_breakeven_days_at_median":
            agg(lambda w: w["breakeven"]["breakeven_days_at_median"]),
        "aggregate_pct_positive": agg(lambda w: w["funding_distribution"]["pct_positive"]),
        "per_symbol": per_symbol,
        "note": "all costs at 1x here; item 47 re-runs at 2x in the write-up from these columns",
    }
    Path(a.out).write_text(json.dumps(summary, indent=1, default=str))
    print(f"\nwrote {a.out}")
    print(f"aggregate gross funding APR: {summary['aggregate_mean_gross_apr']*100:+.2f}%  "
          f"Sharpe {summary['aggregate_mean_sharpe']:+.2f}  "
          f"breakeven {summary['aggregate_mean_breakeven_days_at_mean']:.2f}d (mean rate) / "
          f"{summary['aggregate_mean_breakeven_days_at_median']:.2f}d (median rate)")
    for H, r in agg_always.items():
        print(f"  H={H:>2}d  gross APR {r['gross_apr']*100:+7.2f}%  net APR {r['net_apr']*100:+7.2f}%  "
              f"basis {r['basis_mean_pct']:+.4f}%  Sharpe {r['sharpe_ann']:+.2f}  maxDD {r['max_dd_pct']:+.2f}%")
    if blocked:
        print(f"\nBLOCKED: {blocked}")
    return 0 if per_symbol else 2


if __name__ == "__main__":
    raise SystemExit(main())
