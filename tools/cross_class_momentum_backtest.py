#!/usr/bin/env python3
"""Cross-class backtest under IDENTICAL entry criteria (ranked-pick objective, block 2).

THE POINT OF "IDENTICAL"
    Comparing a value book to a carry trade to a trend rule and calling one "better"
    is meaningless unless the entry rule, the rebalance clock, and the cost treatment
    are the same. So every class here runs the SAME rule family:

        time-series momentum: hold the instrument when its trailing L-day return
        is > 0, otherwise hold cash. Rebalance every H trading days.

    Only the instrument and the measured round-trip cost differ per class, because
    those are properties of the class, not of the rule.

GRID (identical for every class) -> 15 configs
    L in {21, 63, 126, 189, 252}, H in {5, 10, 21}

PROTOCOL
    * In-sample = first 70% of observations, out-of-sample = last 30%.
    * The "top pick" per class is the config with the best IN-SAMPLE Sharpe.
    * Reported OOS figures are for that config, chosen without looking at OOS.
    * Returns matrices are saved per class so the DSR/PBO pass (block 3) works on
      exactly the same numbers.

NO LOOK-AHEAD
    The signal at bar i uses only closes up to i, and the position only earns the
    return from i to i+1. A test asserts this.

COST
    Per-class round trip, using MEASURED values where they exist:
      EQUITY/ETF 4.97bp (measured today, n=191)   CRYPTO 12.60bp (measured)
      FOREX 7.53bp (measured upper bound)
      COMMODITY/BOND: 4.97bp PROXY, flagged -- futures/bond execution is UNMEASURED
    Charged on position changes only.

Read-only. Not investment advice.

Usage:
    python3 tools/cross_class_momentum_backtest.py
"""
from __future__ import annotations

import csv
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache" / "asset_class_review"
OUT = ROOT / "reports" / "cross_class_backtest.json"
RETDIR = ROOT / "reports" / "cross_class_returns"

# representative instrument per class. ONE per class, fixed before running.
INSTRUMENTS = {
    "EQUITY": "AAPL",
    "ETF": "SPY",
    "CRYPTO": "BTC-USD",
    "FOREX": "EURUSD_X",
    "COMMODITY": "GC_F",
    "BOND": "TLT",
}
# Cost where we have it; PROXY flagged where we do not.
# PROVENANCE CORRECTED 2026-11-23 (backlog A5-A7). Each label now says whether the
# number can be RE-RUN from a committed artifact or is only an import:
#   * FOREX 7.53 was labelled "MEASURED" but is in NO fx artifact -- grep for
#     7.533 across reports/fx_meanrev_cost_sweep/* returns nothing. It is imported
#     from the subq COMS note (Tiingo top-of-book, 48 polls, thin Sunday reopen).
#     What IS committed is the break-even, 4.3038 bp (sweep.json).
#   * CRYPTO 12.60 was labelled "MEASURED" but the committed measurement is a BAND:
#     reports/cost_measurement_20261122.json gives taker 10 bp/side (binance,
#     binanceus, kucoin) and 26 bp/side (kraken) => round trip 20-52 bp. 12.60 is a
#     mid-band choice, not a measurement.
COST_BP = {
    "EQUITY": (4.97, "MEASURED reports/equity_cost_hml.json n=191 (spread only, LOWER bound)"),
    "ETF": (4.97, "MEASURED 6.7122bp house band; 4.97 used as conservative floor"),
    "CRYPTO": (12.60, "BAND 20-52bp MEASURED (reports/cost_measurement_20261122.json); "
                       "12.60 is a mid-band choice, NOT a measurement"),
    "FOREX": (7.53, "IMPORT from subq COMS note (Tiingo, 48 polls, thin Sunday reopen); "
                     "NOT reproducible from a repo artifact. Committed break-even is 4.3038bp"),
    "COMMODITY": (4.97, "PROXY UNMEASURED - futures execution not measured"),
    "BOND": (4.97, "PROXY UNMEASURED - bond execution not measured. NOTE: the 42.64bp "
                   "figure sometimes quoted for BOND is claim C-013, which is a CRYPTO "
                   "delta-neutral funding-carry round trip, NOT a bond cost"),
}
LOOKBACKS = [21, 63, 126, 189, 252]
HOLDS = [5, 10, 21]
IS_FRACTION = 0.70
HURDLE = 0.0432


def load_closes(sym: str) -> list[float]:
    p = CACHE / f"{sym}_5y.csv"
    if not p.exists():
        return []
    out = []
    with open(p, newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                c = float(r["Close"])
            except (KeyError, TypeError, ValueError):
                continue
            if c > 0:
                out.append(c)
    return out


def run_config(closes: list[float], lookback: int, hold: int,
               cost_bp: float) -> tuple[list[float], list[float], float]:
    """Return (gross daily returns, net daily returns, annual turnover).

    Convention: position decided at bar i from data <= i, earns return i -> i+1.
    """
    pos = 0
    prev_pos = 0
    gross, net = [], []
    turns = 0.0
    cost = cost_bp / 1e4
    for i in range(len(closes) - 1):
        if i >= lookback and (i - lookback) % hold == 0:
            mom = closes[i] / closes[i - lookback] - 1.0
            pos = 1 if mom > 0 else 0
        r = closes[i + 1] / closes[i] - 1.0
        g = pos * r
        t = abs(pos - prev_pos)
        turns += t
        gross.append(g)
        net.append(g - t * cost)
        prev_pos = pos
    years = max(len(closes) / 252.0, 1e-9)
    return gross, net, turns / years


def metrics(rets: list[float]) -> dict:
    if len(rets) < 30:
        return {"n": len(rets)}
    m = statistics.mean(rets)
    sd = statistics.stdev(rets)
    eq, peak, mdd = 1.0, 1.0, 0.0
    for r in rets:
        eq *= (1 + r)
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
    gains = sum(r for r in rets if r > 0)
    losses = -sum(r for r in rets if r < 0)
    return {
        "n": len(rets),
        "ann_return": round((eq ** (252.0 / len(rets))) - 1, 6),
        "sharpe": round(m / sd * math.sqrt(252), 4) if sd > 0 else None,
        "max_dd": round(mdd, 6),
        "profit_factor": round(gains / losses, 4) if losses > 0 else None,
        "sd_daily": round(sd, 6),
    }


def main() -> int:
    RETDIR.mkdir(parents=True, exist_ok=True)
    results = {}
    for cls, sym in INSTRUMENTS.items():
        closes = load_closes(sym)
        if len(closes) < 300:
            results[cls] = {"instrument": sym, "status": "INSUFFICIENT_DATA",
                            "n_bars": len(closes)}
            continue
        split = int(len(closes) * IS_FRACTION)
        cost_bp, cost_src = COST_BP[cls]

        grid = []
        best = None
        for L in LOOKBACKS:
            for H in HOLDS:
                gross, net, tpy = run_config(closes, L, H, cost_bp)
                is_net = net[:split - 1]
                oos_net = net[split - 1:]
                mi = metrics(is_net)
                cfg = {"lookback": L, "hold": H, "turnover_per_year": round(tpy, 2),
                       "is": mi}
                grid.append(cfg)
                if mi.get("sharpe") is not None:
                    if best is None or mi["sharpe"] > best["cfg"]["is"]["sharpe"]:
                        best = {"cfg": cfg, "oos": metrics(oos_net),
                                "gross_ann_full": metrics(gross)["ann_return"],
                                "net_ann_full": metrics(net)["ann_return"],
                                "_net": net, "_gross": gross}

        if best is None:
            results[cls] = {"instrument": sym, "status": "NO_VALID_CONFIG"}
            continue

        # persist the per-config net return series for the DSR/PBO pass
        series = {}
        for L in LOOKBACKS:
            for H in HOLDS:
                _, net, _ = run_config(closes, L, H, cost_bp)
                series[f"L{L}_H{H}"] = [round(x, 8) for x in net]
        (RETDIR / f"{cls}.json").write_text(json.dumps(
            {"instrument": sym, "cost_bp": cost_bp, "results": series}))

        results[cls] = {
            "instrument": sym,
            "n_bars": len(closes),
            "n_configs": len(grid),
            "cost_bp": cost_bp, "cost_provenance": cost_src,
            "top_pick": {"lookback": best["cfg"]["lookback"],
                         "hold": best["cfg"]["hold"]},
            "is": best["cfg"]["is"],
            "oos": best["oos"],
            "turnover_per_year": best["cfg"]["turnover_per_year"],
            "gross_ann_full": best["gross_ann_full"],
            "net_ann_full": best["net_ann_full"],
            "clears_hurdle_oos": (best["oos"].get("ann_return") or -1) > HURDLE,
            "grid": grid,
        }

    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "rule": "time-series momentum: long if trailing L-day return > 0 else cash",
        "grid": {"lookbacks": LOOKBACKS, "holds": HOLDS,
                 "n_configs_per_class": len(LOOKBACKS) * len(HOLDS)},
        "is_fraction": IS_FRACTION,
        "selection": "top pick = best IN-SAMPLE Sharpe per class",
        "hurdle": HURDLE,
        "classes": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))

    print(f"{'CLASS':10} {'INSTR':9} {'pick':>9} {'IS SR':>7} {'OOS SR':>7} "
          f"{'OOS net':>9} {'OOS DD':>8} {'turn/yr':>8} {'>hurdle':>8}")
    for cls, r in results.items():
        if "top_pick" not in r:
            print(f"{cls:10} {r.get('instrument',''):9} {r.get('status',''):>9}")
            continue
        tp = f"L{r['top_pick']['lookback']}/H{r['top_pick']['hold']}"
        print(f"{cls:10} {r['instrument']:9} {tp:>9} "
              f"{(r['is'].get('sharpe') or 0):>7.2f} "
              f"{(r['oos'].get('sharpe') or 0):>7.2f} "
              f"{(r['oos'].get('ann_return') or 0):>9.2%} "
              f"{(r['oos'].get('max_dd') or 0):>8.2%} "
              f"{r['turnover_per_year']:>8.1f} {str(r['clears_hurdle_oos']):>8}")
    print(f"\nwritten: {OUT.relative_to(ROOT)}  + {len(results)} return matrices in "
          f"{RETDIR.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
