#!/usr/bin/env python3
"""Round N1 - low-turnover tests (pre-registered).

Three rules, each with <=4 rebalances per year:

  R1  12-month momentum, annual rebalance.  Rank the whole cache universe by
      trailing 252-day return, hold the top 5 equal-weight.
  R2  Quarterly sector momentum.  Rank only the sector ETFs present in the
      cache (XLK, XLF, XLV, XLE) by trailing 126-day return, hold the top 2.
  R3  200-day trend filter on SPY (Faber).  Long SPY when close > 200d SMA,
      cash otherwise.  Minimum-turnover control.

Conventions
  * Prices are reindexed onto the SPY trading calendar and forward filled.
  * Every decision is taken on the close of day t and executed on the close
    of day t+1 (next-bar execution, no same-day look-ahead).
  * Per-side cost is charged on the traded notional at execution:
    cost = bps/1e4 * sum(|w_new - w_old|).  Base case 5 bp per side for US
    ETFs, stress case 15 bp (3x).
  * All rules and the SPY benchmark are measured on the SAME evaluation
    window, which starts 253 trading days in (after the slowest warm-up).

No network access, no new packages: numpy + pandas only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
CACHE = Path("data/cache/asset_class_review")
OUT_JSON = Path("reports/low_turnover_20261122.json")

COST_BPS = 5.0          # per side, US ETF
COST_BPS_STRESS = 15.0  # 3x stress

N_R1 = 5               # top 5 of the universe
R1_LOOKBACK = 252
N_R2 = 2
R2_LOOKBACK = 126
R3_MA = 200

N_BOOT = 2000
BLOCK = 21
N_SHUFFLES = 500
G5_PERCENTILE = 95.0

SECTORS = ["XLK", "XLF", "XLV", "XLE"]

ASSET_CLASS = {
    # US equity index / broad ETFs
    **{s: "us_equity_index_etf" for s in ["SPY", "QQQ", "DIA", "IWM", "SOXX", "ARKK", "EEM", "EFA"]},
    # US sector ETFs
    **{s: "us_sector_etf" for s in SECTORS},
    # US single names
    **{s: "us_single_stock" for s in [
        "AAPL", "AMD", "AMZN", "BA", "COST", "CRM", "DIS", "GOOGL", "INTC", "JPM",
        "KO", "META", "MSFT", "NFLX", "NVDA", "ORCL", "PFE", "TSLA", "WMT", "XOM"]},
    # bonds
    **{s: "bonds" for s in ["AGG", "BND", "HYG", "IEF", "JNK", "LQD", "SHY", "TIP", "TLH", "TLT"]},
    # commodities / futures / metals
    **{s: "commodities_futures" for s in [
        "CL_F", "ES_F", "GC_F", "HG_F", "NQ_F", "NG_F", "SI_F", "YM_F", "ZC_F", "ZS_F",
        "GLD", "SLV"]},
    # FX
    **{s: "fx" for s in [
        "AUDUSD_X", "EURGBP_X", "EURJPY_X", "EURUSD_X", "GBPJPY_X", "GBPUSD_X",
        "JPY_X", "NZDUSD_X", "USDCAD_X", "USDCHF_X"]},
    # crypto
    **{s: "crypto" for s in [
        "ADA-USD", "ATOM-USD", "AVAX-USD", "BNB-USD", "BTC-USD", "DOGE-USD", "DOT-USD",
        "ETC-USD", "ETH-USD", "LINK-USD", "LTC-USD", "NEAR-USD", "SOL-USD", "XLM-USD",
        "XRP-USD"]},
}


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
def load_prices(cache: Path):
    spy = pd.read_csv(cache / "SPY_5y.csv", parse_dates=["Date"]).set_index("Date")
    cal = pd.DatetimeIndex(spy.index).sort_values()
    series, meta = {}, {}
    for f in sorted(cache.glob("*_5y.csv")):
        sym = f.name[: -len("_5y.csv")]
        df = pd.read_csv(f, parse_dates=["Date"]).set_index("Date")
        df = df[~df.index.duplicated(keep="last")].sort_index()
        close = pd.to_numeric(df["Close"], errors="coerce").dropna()
        close = close[close > 0]
        if close.empty:
            continue
        meta[sym] = {
            "first": str(close.index[0].date()),
            "last": str(close.index[-1].date()),
            "n_bars": int(len(close)),
        }
        series[sym] = close
    prices = pd.DataFrame(series).reindex(cal).ffill()
    return prices, cal, meta


# --------------------------------------------------------------------------
# weight construction / simulation
# --------------------------------------------------------------------------
def build_weights(dates, targets: pd.DataFrame, assets):
    """Targets are decided at close of row i and executed at close of row i+1.

    Returns W where row i = weights held during day i (i.e. established at the
    close of day i-1).
    """
    T = targets.reindex(index=dates, columns=assets)
    E = pd.DataFrame(np.nan, index=dates, columns=assets)
    rows = np.where(~T.isna().all(axis=1).to_numpy())[0]
    for i in rows:
        if i + 1 < len(dates):
            E.iloc[i + 1] = T.iloc[i].to_numpy()
    return E.ffill().fillna(0.0)


def simulate(dates, R: pd.DataFrame, W: pd.DataFrame, cost_bps: float):
    held = W.to_numpy()
    r = R.to_numpy()
    n = len(dates)
    ret = np.zeros(n)
    cost = np.zeros(n)
    ret[1:] = (held[:-1] * r[1:]).sum(axis=1)
    dw = np.abs(held[1:] - held[:-1]).sum(axis=1)
    cost[1:] = dw * cost_bps / 1e4
    legs = (np.abs(held[1:] - held[:-1]) > 1e-9).sum(axis=1)
    turn = np.zeros(n)
    turn[1:] = dw
    net = (1.0 + ret) * (1.0 - cost) - 1.0
    eq = np.cumprod(1.0 + net)
    eq_nocost = np.cumprod(1.0 + ret)
    return {
        "ret": ret, "cost": cost, "net": net, "eq": eq, "eq_nocost": eq_nocost,
        "legs": legs, "turnover": turn, "held": held,
    }


def metrics(dates_w, sim, start_idx, label):
    """Metrics on the evaluation window only (equity re-based at start)."""
    sl = slice(start_idx, None)
    net = sim["net"][sl]
    ret = sim["ret"][sl]
    cost = sim["cost"][sl]
    eq = np.concatenate(([1.0], np.cumprod(1.0 + net)))
    eq_nc = np.concatenate(([1.0], np.cumprod(1.0 + ret)))
    dw = dates_w[sl]
    days = (dw[-1] - dw[0]).days
    years = days / 365.25
    cagr = eq[-1] ** (1.0 / years) - 1.0
    cagr_nocost = eq_nc[-1] ** (1.0 / years) - 1.0
    vol = float(np.std(net, ddof=1) * np.sqrt(252))
    sharpe = float(np.mean(net) / np.std(net, ddof=1) * np.sqrt(252)) if np.std(net, ddof=1) > 0 else float("nan")
    mdd = float(np.min(eq / np.maximum.accumulate(eq) - 1.0))
    legs = int(sim["legs"][sl].sum())
    turnover = float(sim["turnover"][sl].sum())
    return {
        "label": label,
        "years": round(float(years), 4),
        "cagr": float(cagr),
        "cagr_zero_cost": float(cagr_nocost),
        "cost_drag_pp_per_year": float((cagr_nocost - cagr) * 100.0),
        "vol": vol,
        "max_drawdown": mdd,
        "sharpe": sharpe,
        "total_cost_paid": float(np.sum(cost)),
        "trades_total": legs,
        "trades_per_year": float(legs / years),
        "turnover_notional_per_year": float(turnover / years),
        "final_equity": float(eq[-1]),
    }


# --------------------------------------------------------------------------
# rules -> target weight frames
# --------------------------------------------------------------------------
def empty_targets(dates, assets):
    return pd.DataFrame(np.nan, index=dates, columns=assets)


def annual_rebalance_rows(dates):
    years = pd.Series(dates.year, index=dates)
    first = dates[np.r_[True, years.to_numpy()[1:] != years.to_numpy()[:-1]]]
    return [dates.get_loc(d) for d in first]


def quarterly_rebalance_rows(dates):
    key = dates.year * 10 + dates.quarter
    first = dates[np.r_[True, key[1:] != key[:-1]]]
    return [dates.get_loc(d) for d in first]


def rule_r1(prices, dates, assets, lookback=R1_LOOKBACK, n_hold=N_R1):
    mom = prices / prices.shift(lookback) - 1.0
    T = empty_targets(dates, assets)
    rows = annual_rebalance_rows(dates)
    for i in rows:
        d = dates[i]
        ranks = mom.loc[d].dropna()
        ranks = ranks[np.isfinite(ranks)]
        if len(ranks) < n_hold:
            continue
        top = list(ranks.nlargest(n_hold).index)
        w = np.zeros(len(assets))
        for s in top:
            w[assets.index(s)] = 1.0 / len(top)
        T.iloc[i] = w
    return T, rows


def rule_r2(prices, dates, assets, lookback=R2_LOOKBACK, n_hold=N_R2):
    sectors = [s for s in SECTORS if s in prices.columns]
    mom = prices[sectors] / prices[sectors].shift(lookback) - 1.0
    T = empty_targets(dates, assets)
    rows = quarterly_rebalance_rows(dates)
    for i in rows:
        d = dates[i]
        ranks = mom.loc[d].dropna()
        if len(ranks) < n_hold:
            continue
        top = list(ranks.nlargest(n_hold).index)
        w = np.zeros(len(assets))
        for s in top:
            w[assets.index(s)] = 1.0 / len(top)
        T.iloc[i] = w
    return T, rows


def rule_r3(prices, dates, assets, ma=R3_MA):
    spy = prices["SPY"]
    sma = spy.rolling(ma).mean()
    sig = (spy > sma).astype(float)
    sig[sma.isna()] = np.nan
    T = empty_targets(dates, assets)
    j = assets.index("SPY")
    prev = None
    for i, d in enumerate(dates):
        s = sig.iloc[i]
        if not np.isfinite(s):
            continue
        if prev is None or s != prev:
            w = np.zeros(len(assets))
            w[j] = s
            T.iloc[i] = w
            prev = s
    return T, None


def random_targets(dates, assets, reb_rows, n_hold, rng):
    T = empty_targets(dates, assets)
    for i in reb_rows:
        pick = rng.choice(len(assets), size=min(n_hold, len(assets)), replace=False)
        w = np.zeros(len(assets))
        w[pick] = 1.0 / len(pick)
        T.iloc[i] = w
    return T


# --------------------------------------------------------------------------
# statistics
# --------------------------------------------------------------------------
def cagr_from(net, years):
    return float(np.prod(1.0 + net) ** (1.0 / years) - 1.0)


def block_bootstrap_excess(net_rule, net_bench, years, seed=SEED, n_boot=N_BOOT, block=BLOCK):
    rng = np.random.default_rng(seed)
    n = len(net_rule)
    n_blocks = int(np.ceil(n / block))
    starts_max = n - block
    out = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, starts_max + 1, size=n_blocks)
        idx = np.concatenate([np.arange(s, s + block) for s in starts])[:n]
        out[b] = cagr_from(net_rule[idx], years) - cagr_from(net_bench[idx], years)
    lo, hi = np.percentile(out, [2.5, 97.5])
    return {
        "mean": float(out.mean()),
        "ci95_low": float(lo),
        "ci95_high": float(hi),
        "p_value_le_0": float(np.mean(out <= 0.0)),
    }


def per_year_table(dates_w, net_rule, net_bench, start_idx):
    d = dates_w[start_idx:]
    yr = d.year
    rows = {}
    for y in sorted(set(yr)):
        m = yr == y
        if m.sum() < 20:
            continue
        r = float(np.prod(1.0 + net_rule[m]) - 1.0)
        s = float(np.prod(1.0 + net_bench[m]) - 1.0)
        rows[int(y)] = {"rule": r, "spy": s, "excess": r - s, "days": int(m.sum())}
    return rows


def contribution(held, R, assets, start_idx):
    contrib = (held[start_idx:-1] * R.to_numpy()[start_idx + 1:]).sum(axis=0)
    total = contrib.sum()
    order = np.argsort(-np.abs(contrib))
    out = []
    for j in order[:6]:
        if abs(contrib[j]) < 1e-12:
            continue
        out.append({
            "symbol": assets[j],
            "contrib": float(contrib[j]),
            "share_of_total": float(contrib[j] / total) if abs(total) > 1e-12 else None,
        })
    return {"total_gross_contrib": float(total), "top": out}


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main():
    if not CACHE.is_dir():
        sys.exit(f"cache not found: {CACHE}")
    prices, cal, meta = load_prices(CACHE)

    # drop symbols that cannot be aligned onto the SPY calendar from the start
    usable = [c for c in prices.columns if prices[c].notna().all()]
    dropped = [
        {"symbol": c, "reason": "no price on the full SPY calendar (starts after / ends before)"}
        for c in prices.columns if c not in usable
    ]
    prices = prices[usable]
    assets = list(prices.columns)
    R = prices.pct_change().fillna(0.0)
    dates = pd.DatetimeIndex(prices.index)

    warmup = max(R1_LOOKBACK, R3_MA) + 1
    start_idx = warmup + 1  # first day a rule can already be holding

    # ---------------- benchmark: buy and hold SPY, zero cost ----------------
    W_b = pd.DataFrame(0.0, index=dates, columns=assets)
    W_b["SPY"] = 1.0
    sim_b = simulate(dates, R, W_b, 0.0)
    m_bench = metrics(dates, sim_b, start_idx, "SPY buy & hold")

    rules = {}
    cfg = {
        "R1_12m_momentum_annual_top5": (rule_r1, N_R1, "annual"),
        "R2_sector_momentum_quarterly_top2": (rule_r2, N_R2, "quarterly"),
        "R3_spy_200d_trend_filter": (rule_r3, 1, "signal"),
    }

    for name, (fn, n_hold, freq) in cfg.items():
        T, reb_rows = fn(prices, dates, assets)
        W = build_weights(dates, T, assets)
        sim = simulate(dates, R, W, COST_BPS)
        sim3 = simulate(dates, R, W, COST_BPS_STRESS)
        m = metrics(dates, sim, start_idx, name)
        m3 = metrics(dates, sim3, start_idx, name)
        m["excess_cagr_vs_spy"] = m["cagr"] - m_bench["cagr"]
        m["excess_cagr_vs_spy_3x_cost"] = m3["cagr"] - m_bench["cagr"]
        m["cagr_3x_cost"] = m3["cagr"]
        m["cost_drag_pp_per_year_3x"] = m3["cost_drag_pp_per_year"]
        m["stress_cost_bps"] = COST_BPS_STRESS

        years = m["years"]
        net_w = sim["net"][start_idx:]
        net_b = sim_b["net"][start_idx:]
        m["bootstrap_excess_cagr"] = block_bootstrap_excess(net_w, net_b, years)
        m["per_year_excess"] = per_year_table(dates, net_w, net_b, start_idx)
        m["attribution"] = contribution(sim["held"], R, assets, start_idx)

        # holdings log
        hh = {}
        for i in (reb_rows if reb_rows is not None else []):
            held_row = W.iloc[i + 1] if i + 1 < len(W) else W.iloc[i]
            for j, w in enumerate(held_row):
                if w > 1e-9:
                    hh[assets[j]] = hh.get(assets[j], 0) + 1
        m["holdings_count_by_symbol"] = dict(sorted(hh.items(), key=lambda kv: -kv[1]))

        # ---------------- random-selection control ----------------
        if reb_rows is None:
            reb = annual_rebalance_rows(dates)
        else:
            reb = reb_rows
        rng = np.random.default_rng(SEED)
        null = np.empty(N_SHUFFLES)
        for k in range(N_SHUFFLES):
            Tr = random_targets(dates, assets, reb, n_hold, rng)
            Wr = build_weights(dates, Tr, assets)
            sr = simulate(dates, R, Wr, COST_BPS)
            mr = metrics(dates, sr, start_idx, "rand")
            null[k] = mr["cagr"] - m_bench["cagr"]
        pct = float(100.0 * np.mean(null < m["excess_cagr_vs_spy"]))
        m["random_control"] = {
            "n_shuffles": N_SHUFFLES,
            "n_hold": n_hold,
            "rebalance_rows": len(reb),
            "null_mean_excess": float(null.mean()),
            "null_p5": float(np.percentile(null, 5)),
            "null_p50": float(np.percentile(null, 50)),
            "null_p95": float(np.percentile(null, 95)),
            "rule_excess": float(m["excess_cagr_vs_spy"]),
            "percentile_of_rule": pct,
        }

        # ---------------- gates ----------------
        g = {}
        g["G1_excess_cagr_gt_0"] = bool(m["excess_cagr_vs_spy"] > 0)
        g["G2_ci_low_gt_0"] = bool(m["bootstrap_excess_cagr"]["ci95_low"] > 0)
        g["G3_risk_adjusted"] = bool(
            (m["max_drawdown"] > m_bench["max_drawdown"]) or (m["sharpe"] > m_bench["sharpe"])
        )
        g["G4_cost_drag_lt_1pp"] = bool(m["cost_drag_pp_per_year"] < 1.0)
        g["G5_beats_random_p95"] = bool(pct >= G5_PERCENTILE)
        if all(g.values()):
            verdict = "CANDIDATE"
        elif g["G1_excess_cagr_gt_0"] and g["G2_ci_low_gt_0"]:
            verdict = "WEAK"
        else:
            verdict = "KILL"
        m["gates"] = g
        m["verdict"] = verdict
        rules[name] = m

    # asset class composition of the universe actually used
    comp = {}
    for s in assets:
        comp.setdefault(ASSET_CLASS.get(s, "unclassified"), []).append(s)

    survivorship = {
        "symbols_used": len(assets),
        "symbols_dropped": dropped,
        "first_date_min": min(m["first"] for m in meta.values()),
        "first_date_max": max(m["first"] for m in meta.values()),
        "last_date_max": max(m["last"] for m in meta.values()),
        "all_symbols_have_full_history": all(m["first"] <= "2021-11-23" for m in meta.values()),
        "median_bars": int(np.median([m["n_bars"] for m in meta.values()])),
    }

    out = {
        "round": "N1",
        "generated": "2026-11-22",
        "seed": SEED,
        "config": {
            "cost_bps_per_side": COST_BPS,
            "cost_bps_stress": COST_BPS_STRESS,
            "r1": {"universe": "all usable cache symbols", "lookback": R1_LOOKBACK, "n_hold": N_R1, "rebalance": "annual (first trading day of year)"},
            "r2": {"universe": SECTORS, "lookback": R2_LOOKBACK, "n_hold": N_R2, "rebalance": "quarterly"},
            "r3": {"symbol": "SPY", "ma": R3_MA, "rebalance": "signal (daily check, trade on cross)"},
            "bootstrap": {"reps": N_BOOT, "block_days": BLOCK, "seed": SEED},
            "random_control": {"shuffles": N_SHUFFLES, "seed": SEED, "gate_percentile": G5_PERCENTILE},
            "evaluation_window": {"start": str(dates[start_idx].date()), "end": str(dates[-1].date())},
        },
        "universe": {
            "n_symbols": len(assets),
            "symbols": assets,
            "asset_class_composition": {k: v for k, v in comp.items()},
            "survivorship": survivorship,
        },
        "benchmark_spy_buy_and_hold": m_bench,
        "benchmark_spy_full_window": metrics(dates, sim_b, 1, "SPY buy & hold full window"),
        "rules": rules,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
