"""H-141: frozen, survivor-universe fund-selection audit. Research only."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def metrics(daily):
    daily = pd.Series(daily, dtype=float)
    if daily.empty or not np.isfinite(daily).all() or (daily <= -1).any():
        raise ValueError("Invalid daily return path")
    curve = (1 + daily).cumprod()
    if isinstance(daily.index, pd.DatetimeIndex) and len(daily) > 1:
        years = (daily.index[-1] - daily.index[0]).days / 365.25
    else:
        years = len(daily) / 252
    vol = daily.std(ddof=1)
    downside = np.sqrt(np.mean(np.minimum(daily.to_numpy(), 0) ** 2))
    mdd = float((1 - curve / curve.cummax().clip(lower=1)).max())
    tail = daily[daily <= daily.quantile(0.05)]
    return {
        "n_days": len(daily), "years": years,
        "compound_pct": float((curve.iloc[-1] - 1) * 100),
        "cagr_pct": float((curve.iloc[-1] ** (1/years) - 1) * 100) if years > 0 else None,
        "sharpe": float(daily.mean()/vol*np.sqrt(252)) if vol > 0 else None,
        "sortino": float(daily.mean()/downside*np.sqrt(252)) if downside > 0 else None,
        "mdd_pct": mdd*100, "daily_cvar5_pct": float(tail.mean()*100),
        "calmar": float((curve.iloc[-1]**(1/years)-1)/mdd) if years > 0 and mdd > 0 else None,
    }


def rank_at(frame, cutoff, selector, min_obs=700):
    history = frame.loc[(frame.index <= cutoff) & (frame.index >= cutoff-pd.DateOffset(years=3))]
    ranked = []
    for symbol in sorted(frame.columns):
        prices = history[symbol]
        if len(prices) < min_obs or prices.isna().any() or (prices <= 0).any():
            continue
        returns = prices.pct_change().iloc[1:]
        std = returns.std(ddof=1)
        if selector == "trailing_total_return":
            score = prices.iloc[-1]/prices.iloc[0]-1
        elif selector == "trailing_sharpe":
            score = returns.mean()/std*np.sqrt(252) if std > 0 else np.nan
        elif selector == "trailing_low_volatility":
            score = -std*np.sqrt(252)
        else:
            raise ValueError("Unknown frozen selector")
        if np.isfinite(score):
            ranked.append((symbol, float(score)))
    return sorted(ranked, key=lambda item: (-item[1], item[0]))


def basket_path(frame, symbols, cost):
    if not symbols or not 0 <= cost < 1 or frame.empty:
        raise ValueError("Invalid basket or cost")
    prices = frame[symbols]
    if prices.isna().any().any() or not np.isfinite(prices).all().all() or (prices <= 0).any().any():
        raise ValueError("Basket requires complete positive price path")
    relative = prices / prices.iloc[0]
    curve = relative.mean(axis=1) * (1-cost)
    curve.iloc[-1] *= 1-cost
    daily = curve.div(curve.shift(1).fillna(1))-1
    return daily


def paired_block_interval(excess, seed=141, simulations=2000):
    values = np.asarray(excess, dtype=float)
    if not len(values) or not np.isfinite(values).all():
        raise ValueError("Paired bootstrap needs finite matching daily observations")
    rng = np.random.default_rng(seed)
    n = len(values)
    blocks = (n+20)//21
    draws = np.empty(simulations)
    for i in range(simulations):
        starts = rng.integers(0, n, blocks)
        indices = (starts[:, None] + np.arange(21)) % n
        draws[i] = values[indices.ravel()[:n]].mean()*252*100
    return [float(v) for v in np.quantile(draws, [0.025, 0.975])]


def fetch_one(symbol, cache, end):
    first = int(datetime(1995, 1, 1, tzinfo=timezone.utc).timestamp())
    last = int(pd.Timestamp(end, tz="UTC").timestamp())+86400
    errors = []
    for attempt in range(3):
        host = "query1.finance.yahoo.com" if attempt != 1 else "query2.finance.yahoo.com"
        url = f"https://{host}/v8/finance/chart/{quote(symbol)}?period1={first}&period2={last}&interval=1d"
        try:
            with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=40) as response:
                raw = response.read()
            result = json.loads(raw)["chart"]["result"][0]
            adjusted = result["indicators"].get("adjclose", [{}])[0].get("adjclose")
            if adjusted is None:
                raise ValueError("Adjusted total-return series unavailable")
            dates = pd.to_datetime(result["timestamp"], unit="s", utc=True).tz_convert(None).normalize()
            series = pd.Series(adjusted, index=dates, dtype=float)
            series = series.loc[series.index <= pd.Timestamp(end)].dropna()
            if series.empty or series.index.has_duplicates or not series.index.is_monotonic_increasing or (series <= 0).any():
                raise ValueError("Invalid adjusted-price series")
            (cache / (symbol+".json")).write_bytes(raw)
            return symbol, {"status": "OK", "rows": len(series), "first": str(series.index[0].date()),
                            "last": str(series.index[-1].date()), "sha256": hashlib.sha256(raw).hexdigest(),
                            "source": url}
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError) as exc:
            errors.append(type(exc).__name__+": "+str(exc)[:120])
            time.sleep(attempt+1)
    return symbol, {"status": "BROKEN", "errors": errors}


def load_series(cache, manifest):
    series = {}
    for symbol, meta in manifest.items():
        if meta["status"] != "OK":
            continue
        raw = (cache/(symbol+".json")).read_bytes()
        if hashlib.sha256(raw).hexdigest() != meta["sha256"]:
            raise ValueError("Cache hash mismatch for "+symbol)
        result = json.loads(raw)["chart"]["result"][0]
        dates = pd.to_datetime(result["timestamp"], unit="s", utc=True).tz_convert(None).normalize()
        values = result["indicators"]["adjclose"][0]["adjclose"]
        series[symbol] = pd.Series(values, index=dates, dtype=float).dropna()
    return series


def annual_forward(series, benchmark):
    joined = pd.concat([series.rename("asset"), benchmark.rename("benchmark")], axis=1).dropna()
    output = []
    for year in sorted(set(joined.index.year)):
        start = joined.loc[joined.index.year == year].index[0]
        for horizon in (1, 3, 5):
            target = start + pd.DateOffset(years=horizon)
            future = joined.index[joined.index >= target]
            if not len(future):
                continue
            end = future[0]
            asset = joined.loc[end, "asset"]/joined.loc[start, "asset"]-1
            bench = joined.loc[end, "benchmark"]/joined.loc[start, "benchmark"]-1
            output.append({"start": str(start.date()), "end": str(end.date()), "horizon": horizon,
                           "return_pct": float(asset*100), "benchmark_pct": float(bench*100),
                           "excess_pct": float((asset-bench)*100)})
    return output


def compare_funds(series, symbols):
    if len(symbols) < 2 or len(set(symbols)) != len(symbols):
        raise ValueError("Comparison needs at least two distinct symbols")
    if len({s.endswith(".TO") for s in symbols}) != 1:
        raise ValueError("Do not compare USD and CAD return paths directly")
    frame = pd.concat({s: series[s] for s in symbols}, axis=1).dropna()
    if len(frame) < 100 or not np.isfinite(frame).all().all() or (frame <= 0).any().any():
        raise ValueError("Insufficient complete positive matching prices")
    return {
        "scope": "Post-registration descriptive comparison, not an H-141 selection trial",
        "first": str(frame.index[0].date()), "last": str(frame.index[-1].date()),
        "currency": "CAD" if symbols[0].endswith(".TO") else "USD",
        "costs": "Adjusted NAV embeds fund expenses; no additional execution, FX, tax or platform costs",
        "metrics": {s: metrics(frame[s].pct_change(fill_method=None).fillna(0)) for s in symbols},
    }


def describe_symbol(symbol, values, benchmark):
    joined = pd.concat([values.rename("asset"), benchmark.rename("benchmark")], axis=1).dropna()
    if len(joined) < 100:
        return {"symbol": symbol, "label": "FAIL", "reason": "insufficient matching history"}
    returns = joined.pct_change(fill_method=None).fillna(0)
    a, b = metrics(returns.asset), metrics(returns.benchmark)
    rolling = annual_forward(joined.asset, joined.benchmark)
    thirds = []
    for block in np.array_split(np.arange(len(returns)), 2):
        ar, br = metrics(returns.asset.iloc[block]), metrics(returns.benchmark.iloc[block])
        thirds.append(ar["cagr_pct"]-br["cagr_pct"])
    three = [r for r in rolling if r["horizon"] == 3]
    stress = {}
    for year in (2008, 2020, 2022):
        subset = returns.loc[returns.index.year == year]
        if len(subset) >= 200:
            stress[str(year)] = {"asset": metrics(subset.asset), "benchmark": metrics(subset.benchmark)}
    passes = {
        "ten_years": a["years"] >= 10,
        "sharpe_ge_1": a["sharpe"] is not None and a["sharpe"] >= 1,
        "mdd_le_20": a["mdd_pct"] <= 20,
        "excess_both_halves": all(x > 0 for x in thirds),
        "three_year_excess_60pct": bool(three) and np.mean([r["excess_pct"] > 0 for r in three]) >= .6,
    }
    return {"symbol": symbol, "first": str(joined.index[0].date()), "last": str(joined.index[-1].date()),
            "asset": a, "benchmark": b, "half_excess_cagr_pp": thirds,
            "rolling_3y_positive_excess_fraction": float(np.mean([r["excess_pct"] > 0 for r in three])) if three else None,
            "screen": {k: bool(v) for k, v in passes.items()}, "descriptive_screen_pass": all(passes.values()),
            "label": "FAIL", "reason": "Survivor universe; no independent trial-adjusted and forward proof",
            "forward_windows": rolling, "stress": stress}


def build_schedules(frame, benchmark, selector, spec):
    calendar = benchmark.index
    frame = frame.reindex(calendar)
    cuts = [group.index[-1] for _, group in benchmark.groupby(benchmark.index.year)]
    schedules, skipped = [], []
    for cut in cuts:
        candidates = calendar[calendar > cut]
        if cut.year < 2004 or not len(candidates):
            continue
        entry = candidates[0]
        next_year = calendar[calendar.year == entry.year+1]
        exit_ = next_year[0] if len(next_year) else calendar[-1]
        if exit_ <= entry:
            continue
        ranked = rank_at(frame, cut, selector, spec["minimum_trailing_observations"])
        eligible = []
        for symbol, score in ranked:
            holding = frame.loc[entry:exit_, symbol]
            if holding.isna().any():
                skipped.append({"year": entry.year, "symbol": symbol, "reason": "future missing-price exclusion; survivorship limitation"})
            else:
                eligible.append((symbol, score))
        if len(eligible) < 3:
            skipped.append({"year": entry.year, "reason": "fewer than three complete assets"})
            continue
        schedules.append({"signal": cut, "entry": entry, "exit": exit_,
                          "selected": [v[0] for v in eligible[:3]], "eligible": [v[0] for v in eligible],
                          "scores": dict(eligible)})
    return schedules, skipped


def book_returns(frame, schedules, cost, rng=None):
    pieces = []
    for schedule in schedules:
        selected = schedule["selected"] if rng is None else list(rng.choice(schedule["eligible"], 3, replace=False))
        piece = basket_path(frame.loc[schedule["entry"]:schedule["exit"]], selected, cost)
        pieces.append(piece)
    if not pieces:
        raise ValueError("No eligible annual schedules")
    # Shared rebalance date includes old-basket exit and new-basket entry factors.
    daily = pd.concat(pieces).add(1).groupby(level=0).prod().sub(1).sort_index()
    return daily.reindex(frame.loc[daily.index[0]:daily.index[-1]].index, fill_value=0)


def test_selection(name, frame, benchmark, selector, spec):
    schedules, skipped = build_schedules(frame, benchmark, selector, spec)
    if not schedules:
        return {"universe": name, "selector": selector, "label": "FAIL", "reason": "no schedules"}
    cost = spec["per_side_cost_bps"]/10000
    daily = book_returns(frame, schedules, cost)
    stress = book_returns(frame, schedules, 2*cost)
    matching = benchmark.reindex(daily.index).pct_change(fill_method=None).fillna(0)
    # benchmark is bought once at first matching close and liquidated at last close.
    matching.iloc[0] = (1+matching.iloc[0])*(1-cost)-1
    matching.iloc[-1] = (1+matching.iloc[-1])*(1-cost)-1
    holdout = daily.index >= pd.Timestamp(spec["reporting_holdout_start"])
    observed = metrics(daily.loc[holdout])
    benchmark_stats = metrics(matching.loc[holdout])
    ci = paired_block_interval(daily.loc[holdout]-matching.loc[holdout])
    rng = np.random.default_rng(141)
    random_sharpes = []
    for _ in range(500):
        random_path = book_returns(frame, schedules, cost, rng).loc[holdout]
        random_sharpes.append(metrics(random_path)["sharpe"])
    score = observed["sharpe"]
    null = np.array(random_sharpes)
    percentile = float(np.mean(null < score)*100)
    p = float((1+np.sum(null >= score))/(len(null)+1))
    # This legacy gate accepts resolved records via _load, not an input argument.
    # An isolated adapter supplies only annual fund observations; thresholds stay unchanged.
    from tools import edge_stability_harness as harness
    from unittest.mock import patch
    records = []
    for schedule in schedules:
        for symbol in schedule["eligible"]:
            ret = frame.loc[schedule["exit"], symbol]/frame.loc[schedule["entry"], symbol]-1
            records.append({"resolved_at": schedule["exit"].isoformat(), "status": "WON" if ret>0 else "LOST",
                            "pnl_pct": float(ret*100), "selection_score": schedule["scores"][symbol]})
    with patch.object(harness, "_load", return_value=records):
        diagnostic = harness.evaluate("selection_score")
        admissible = harness.is_admissible("selection_score")
    return {"universe": name, "selector": selector, "label": "FAIL",
            "full": metrics(daily), "holdout_2016_plus": observed, "benchmark_2016_plus": benchmark_stats,
            "double_cost_holdout": metrics(stress.loc[holdout]),
            "paired_block_excess_ci_annual_pp": ci,
            "random_selection_sharpe_percentile": percentile, "random_selection_upper_tail_p": p,
            "legacy_score_diagnostic": {"admissible": admissible, "verdict": "UNTESTED" if diagnostic["windows_scored"]<5 else ("ADMISSIBLE" if admissible else "REJECTED"), **diagnostic},
            "calendar_gaps": int(sum(np.diff(pd.DatetimeIndex(daily.index).year)>1)),
            "schedule": [{k: v.isoformat() if isinstance(v, pd.Timestamp) else v for k, v in row.items()} for row in schedules],
            "skipped": skipped,
            "reason": "Current-survivor universe, retrospective selection, unverified DSR/PBO, no sealed forward proof"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["fetch", "run", "compare"])
    parser.add_argument("--protocol", type=Path, default=ROOT/"reports/symbol_durability_protocol_2026-10-23.json")
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--extra-cache", type=Path, help="Optional separately fetched descriptive cache")
    parser.add_argument("--symbols", nargs="+", help="Explicit symbols for descriptive fetch or comparison")
    args = parser.parse_args()
    spec = json.loads(args.protocol.read_text())
    args.cache.mkdir(parents=True, exist_ok=True)
    if args.mode == "fetch":
        symbols = args.symbols or sorted({s for values in spec["universes"].values() if isinstance(values, list) for s in values})
        manifest = {}
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = [pool.submit(fetch_one, symbol, args.cache, spec["last_complete_day"]) for symbol in symbols]
            for future in as_completed(futures):
                symbol, result = future.result()
                manifest[symbol] = result
                print(symbol, result["status"], result.get("rows", 0), flush=True)
        args.output.write_text(json.dumps(dict(sorted(manifest.items())), indent=2)+"\n")
        return
    manifest = json.loads((args.cache/"manifest.json").read_text())
    series = load_series(args.cache, manifest)
    if args.mode == "compare":
        if not args.symbols:
            parser.error("compare requires --symbols")
        extra = {}
        if args.extra_cache:
            extra = json.loads((args.extra_cache/"manifest.json").read_text())
            overlap = set(manifest) & set(extra)
            if overlap:
                raise ValueError("Descriptive cache contains duplicate symbols: "+", ".join(sorted(overlap)))
            series.update(load_series(args.extra_cache, extra))
        series = {s: p.loc[p.index <= pd.Timestamp(spec["last_complete_day"])] for s, p in series.items()}
        comparison = compare_funds(series, args.symbols)
        comparison["input_manifest"] = {s: (manifest if s in manifest else extra)[s] for s in args.symbols}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(comparison, indent=2, allow_nan=False)+"\n")
        return
    if "SPY" not in series or "ZSP.TO" not in series:
        raise ValueError("Required USD/CAD benchmark unavailable")
    end = pd.Timestamp(spec["last_complete_day"])
    series = {s: p.loc[p.index <= end] for s, p in series.items()}
    descriptions = []
    for symbol, prices in series.items():
        benchmark = series["ZSP.TO"] if symbol.endswith(".TO") else series["SPY"]
        descriptions.append(describe_symbol(symbol, prices, benchmark))
    universes = spec["universes"]
    base = {name: [s for s in universes[name] if s in series] for name in ("us_equity_mutual", "us_equity_etf")}
    base["us_equity_combined"] = sorted(set(base["us_equity_mutual"]+base["us_equity_etf"]))
    trials = []
    for name, symbols in base.items():
        frame = pd.DataFrame({s: series[s] for s in symbols}).reindex(series["SPY"].index)
        for selector in spec["selectors"]:
            print("Evaluating", name, selector, flush=True)
            trials.append(test_selection(name, frame, series["SPY"], selector, spec))
    result = {"hypothesis": "H-141", "protocol_sha256": hashlib.sha256(args.protocol.read_bytes()).hexdigest(),
              "survivorship_bias": True, "money_ready": [], "candidate": [], "manifest": manifest,
              "symbols": descriptions, "trials": trials,
              "limitations": ["Historical current-survivor universe; dead/merged funds absent",
                              "Future complete-price requirement introduces selection bias",
                              "No historical expense/eligibility/load database; adjusted NAV embeds expenses",
                              "Shared share classes duplicate underlying funds; not independent strategies",
                              "Random selection is not random-entry proof; bootstrap is not trial-adjusted DSR",
                              "No causal issuer fundamental or calibrated prediction model",
                              "No prospective money-ready or all-asset-class impossibility conclusion"]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")


if __name__ == "__main__":
    main()
