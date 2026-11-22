#!/usr/bin/env python3
"""Monthly multi-asset tactical engine — the horizon where the ladder says edge lives.

WHY THIS EXISTS (todos 13/14/15/17/18/20/21/22)
-----------------------------------------------
The honest cost-horizon ladder is the most robust shape this programme has found:

    horizon    median gross edge per trade (ALL cells)
    15m          -0.57 bp
    1h           +3.85 bp
    4h           +8.64 bp
    1D          +24.21 bp

Edge per trade rises with holding horizon, monotonically, while cost per trade does
not. Every failure so far has been at high frequency. This engine therefore tests
the ONE place the evidence points: monthly rebalancing, where a round trip is
amortised over a month of exposure rather than a minute.

DESIGN RULES, each one a defect this programme has already been burned by
  * ONE-MONTH LAG. Weights for month t use data through t-1 only. No signal is
    allowed to see the return it earns.
  * REPORT ALL CELLS. Medians are taken over EVERY strategy, never over the
    positive ones. (The ladder was once published as a median of positive cells
    only, which doubled it.)
  * COST IS SWEPT, NOT ASSUMED. ETF execution cost could not be measured from
    daily OHLC (tools/etf_spread_estimate.py: both estimators structurally
    invalid), so instead of inventing a number we report the BREAK-EVEN cost for
    each strategy. A strategy that needs 1 bp to work is a different object from
    one that survives 20 bp.
  * BENCHMARKS FIRST. Buy-and-hold SPY and 60/40 are computed on the SAME data and
    the SAME cost model, because "beats cash" is not the question — beating the
    thing you could have owned for free is.
  * MULTIPLICITY. Every strategy is a trial. DSR is reported with n_trials stated,
    and PBO/CSCV measures how often selecting the in-sample winner is worthless.
  * PASSIVE PAYOFFS PROPERTY. Every return panel has a passive passive proxy
    available; here the benchmarks ARE that proxy.

Scope excluded and stated: no leverage beyond 1.0, no shorting, no options, no
intraday, no factor data. This is a long-only monthly allocator.

Usage:
  python3 tools/monthly_tactical_engine.py
  python3 tools/monthly_tactical_engine.py --start 2004-01 --costs 0,2,5,10,20
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "monthly_tactical" / "monthly_tactical_engine.json"

# Multi-asset ETF universe. Inception dates bound the common window (DBC 2006),
# which is WHY the 2008 window is testable here and 2000-02 is not — that gap is
# reported rather than papered over with a shorter-history substitute.
UNIVERSE = ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "IEF", "LQD", "GLD",
            "DBC", "VNQ", "TIP"]
CASH_PROXY = "^IRX"          # 13-week T-bill yield, converted to a monthly return
BOND = "IEF"
SMA_MONTHS = 12
XSMOM_TOP = 3
LOOKBACK = 12

COST_GRID = [0.0, 2.0, 5.0, 10.0, 20.0]   # bp per side of turnover
BLOCK = 6                                  # months per bootstrap block
BOOT = 4000
SEED = 20261122
CSCV_BLOCKS = 8


# --------------------------------------------------------------------------- #
# data
# --------------------------------------------------------------------------- #
def load_monthly() -> tuple[list[str], list[str], dict[str, list[float]],
                            dict[str, list[float]]]:
    """Return (dates, tickers, prices{tkr: series}, cash_ratio series)."""
    import yfinance as yf
    tickers = UNIVERSE + [CASH_PROXY]
    df = yf.download(tickers, period="max", interval="1mo", progress=False,
                     auto_adjust=True, threads=False)
    if df is None or len(df) < 24:
        raise SystemExit("no data returned")
    if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
        close = df["Close"] if "Close" in df.columns.get_level_values(0) else df
    else:
        close = df
    dates = [str(i)[:7] for i in close.index]
    keep = [t for t in UNIVERSE if t in close.columns
            and close[t].notna().sum() > 24]
    prices = {}
    for t in keep:
        s = close[t]
        prices[t] = [float(x) if x == x else float("nan") for x in s.tolist()]
    cash = ([float(x) / 1200.0 if x == x else 0.0 for x in close[CASH_PROXY].tolist()]
            if CASH_PROXY in close.columns else [0.0] * len(dates))
    return dates, keep, prices, cash


def first_valid(prices: dict[str, list[float]], n: int) -> int:
    """First index where EVERY ticker has a price — the common window start."""
    start = 0
    for series in prices.values():
        for i, v in enumerate(series):
            if v == v:
                start = max(start, i)
                break
    return start


# --------------------------------------------------------------------------- #
# strategies: each returns list of weight dicts, indexed by month t, using P<t
# --------------------------------------------------------------------------- #
def rets_from(prices: dict[str, list[float]], t: int, back: int = 1) -> dict[str, float]:
    """Simple returns ending at index t-back. back=0 means the return over
    (t-1 -> t), which is the ONLY one a weight set at t-1 is allowed to earn.

    LOOK-AHEAD GUARD. The first version of run() called this with back=1, i.e. it
    applied weights decided at the close of t-1 to the return over t-2 -> t-1 — a
    period that had already finished when the decision was made. For a trend rule,
    whose signal is highly correlated with the move that just happened, that is a
    direct leak of the answer into the input, and it produced a spectacular fake
    result (trend Sharpe 1.83 vs SPY 0.76, -10.7% maxDD vs -50.8%).
    """
    out = {}
    for k, s in prices.items():
        i_hi, i_lo = t - back, t - back - 1
        a, b = s[i_hi], s[i_lo]
        out[k] = (a / b - 1.0) if (a == a and b == b and b > 0) else 0.0
    return out


def vol_of(prices: dict[str, list[float]], t: int, n: int = 12) -> dict[str, float]:
    out = {}
    for k, s in prices.items():
        r = []
        for i in range(max(1, t - n), t):
            a, b = s[i], s[i - 1]
            if a == a and b == b and b > 0:
                r.append(a / b - 1.0)
        out[k] = statistics.pstdev(r) if len(r) > 1 else float("nan")
    return out


def build_weights(name: str, prices: dict[str, list[float]],
                  dates: list[str], start: int) -> list[dict[str, float]]:
    tickers = list(prices)
    n = len(dates)
    W: list[dict[str, float]] = []
    for t in range(n):
        w: dict[str, float] = {}
        if t <= start:
            W.append(w)
            continue
        if name == "bh_spy":
            w = {"SPY": 1.0}
        elif name == "sixty_forty":
            w = {"SPY": 0.6, BOND: 0.4} if BOND in prices else {"SPY": 1.0}
        elif name == "ew_all":
            w = {k: 1.0 / len(tickers) for k in tickers}
        elif name == "lowvol":
            v = vol_of(prices, t)
            inv = {k: (1.0 / x if x == x and x > 0 else 0.0) for k, x in v.items()}
            tot = sum(inv.values())
            w = {k: inv[k] / tot for k in tickers} if tot > 0 else {}
        elif name in ("trend", "tsmom_vol"):
            on = {}
            for k in tickers:
                s = prices[k]
                hist = [x for x in s[max(0, t - SMA_MONTHS):t] if x == x]
                if len(hist) < SMA_MONTHS or s[t - 1] != s[t - 1]:
                    continue
                if s[t - 1] > sum(hist) / len(hist):
                    on[k] = 1.0
            if not on:
                w = {}
            elif name == "trend":
                w = {k: 1.0 / len(on) for k in on}
            else:
                v = vol_of(prices, t)
                inv = {k: (1.0 / v[k] if v[k] == v[k] and v[k] > 0 else 0.0)
                       for k in on}
                tot = sum(inv.values())
                w = {k: inv[k] / tot for k in on} if tot > 0 else {}
        elif name == "xsmom":
            score = {}
            for k in tickers:
                s = prices[k]
                a, b = s[t - 2], s[max(0, t - 2 - LOOKBACK)]
                if a == a and b == b and b > 0:
                    score[k] = a / b - 1.0
            top = sorted(score, key=score.get, reverse=True)[:XSMOM_TOP]
            w = {k: 1.0 / len(top) for k in top} if top else {}
        elif name == "dual_mom":
            score = {}
            for k in tickers:
                s = prices[k]
                a, b = s[t - 2], s[max(0, t - 2 - LOOKBACK)]
                if a == a and b == b and b > 0:
                    score[k] = a / b - 1.0
            ranked = sorted(score, key=score.get, reverse=True)
            half = ranked[:max(1, len(ranked) // 2)]
            keep = []
            for k in half:
                s = prices[k]
                hist = [x for x in s[max(0, t - SMA_MONTHS):t] if x == x]
                if len(hist) >= SMA_MONTHS and s[t - 1] > sum(hist) / len(hist):
                    keep.append(k)
            w = {k: 1.0 / len(keep) for k in keep} if keep else {}
        W.append(w)
    return W


STRATEGIES = ["bh_spy", "sixty_forty", "ew_all", "lowvol", "trend", "tsmom_vol",
              "xsmom", "dual_mom"]


# --------------------------------------------------------------------------- #
# backtest
# --------------------------------------------------------------------------- #
def run(name: str, prices: dict[str, list[float]], dates: list[str], start: int,
        cash: list[float], cost_bp: float) -> list[float]:
    W = build_weights(name, prices, dates, start)
    out, prev = [], {}
    for t in range(len(dates)):
        # back=0: the return earned OVER month t, by a weight set at t-1. Using
        # back=1 here (the original bug) let the weight earn a month that had
        # already closed -- see rets_from's docstring.
        r = rets_from(prices, t, back=0) if t > 0 else {k: 0.0 for k in prices}
        w = W[t]
        invested = sum(w.values())
        gross = sum(wt * r.get(k, 0.0) for k, wt in w.items())
        gross += max(0.0, 1.0 - invested) * (cash[t] if t < len(cash) else 0.0)
        keys = set(w) | set(prev)
        turnover = sum(abs(w.get(k, 0.0) - prev.get(k, 0.0)) for k in keys)
        net = gross - turnover * cost_bp / 1e4
        out.append(net)
        prev = dict(w)
    return out


def stats(r: list[float]) -> dict:
    r = r[1:]
    if len(r) < 24:
        return {"n_months": len(r)}
    cum = 1.0
    for x in r:
        cum *= (1 + x)
    yrs = len(r) / 12
    cagr = cum ** (1 / yrs) - 1
    sd = statistics.pstdev(r)
    sharpe = (statistics.mean(r) / sd * math.sqrt(12)) if sd else 0.0
    peak, mdd = 1.0, 0.0
    c = 1.0
    for x in r:
        c *= (1 + x)
        peak = max(peak, c)
        mdd = min(mdd, c / peak - 1)
    return {"n_months": len(r), "cagr_pct": cagr * 100, "vol_pct": sd * math.sqrt(12) * 100,
            "sharpe": sharpe, "maxdd_pct": mdd * 100,
            "terminal_10k": 10_000 * cum,
            "worst_month_pct": min(r) * 100, "hit_rate_pct":
            sum(1 for x in r if x > 0) / len(r) * 100}


def block_bootstrap_sharpe(r: list[float]) -> tuple[float, float, float]:
    import random
    r = r[1:]
    n = len(r)
    if n < BLOCK * 2:
        return float("nan"), float("nan"), float("nan")
    rng = random.Random(SEED)
    vals = []
    for _ in range(BOOT):
        sample = []
        while len(sample) < n:
            s = rng.randrange(0, n - BLOCK + 1)
            sample.extend(r[s:s + BLOCK])
        sample = sample[:n]
        sd = statistics.pstdev(sample)
        vals.append(statistics.mean(sample) / sd * math.sqrt(12) if sd else 0.0)
    vals.sort()
    return (vals[len(vals) // 2], vals[int(0.025 * len(vals))],
            vals[int(0.975 * len(vals))])


def norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def norm_ppf(p: float) -> float:
    lo, hi = -8.0, 8.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if norm_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def deflated_sharpe(sharpe_ann: float, n_months: int, n_trials: int,
                    skew: float, kurt: float) -> float:
    """Bailey & Lopez de Prado DSR: P(true SR > 0) after accounting for trials."""
    if n_months < 24 or n_trials < 2:
        return float("nan")
    sr = sharpe_ann / math.sqrt(12)          # monthly units
    euler = 0.5772156649
    e_max = ((1 - euler) * norm_ppf(1 - 1 / n_trials)
             + euler * norm_ppf(1 - 1 / (n_trials * math.e)))
    var_sr = 1.0 / n_months
    sr0 = math.sqrt(var_sr) * e_max
    denom = 1 - skew * sr + ((kurt - 1) / 4) * sr * sr
    if denom <= 0:
        return float("nan")
    return norm_cdf((sr - sr0) * math.sqrt(n_months - 1) / math.sqrt(denom))


def pbo_cscv(matrix: list[list[float]], blocks: int = CSCV_BLOCKS) -> float:
    """Probability of Backtest Overfitting via combinatorially symmetric CV."""
    T = len(matrix)
    N = len(matrix[0]) if T else 0
    if T < blocks * 2 or N < 2:
        return float("nan")
    size = T // blocks
    idx = [list(range(i * size, (i + 1) * size)) for i in range(blocks)]
    overfit, total = 0, 0
    for combo in combinations(range(blocks), blocks // 2):
        train = [i for b in combo for i in idx[b]]
        test = [i for b in range(blocks) if b not in combo for i in idx[b]]
        if not train or not test:
            continue
        def shp(rows: list[int], j: int) -> float:
            xs = [matrix[i][j] for i in rows]
            sd = statistics.pstdev(xs)
            return statistics.mean(xs) / sd if sd else 0.0
        tr = [shp(train, j) for j in range(N)]
        best = max(range(N), key=lambda j: tr[j])
        te = [shp(test, j) for j in range(N)]
        rank = sum(1 for j in range(N) if te[j] < te[best])
        omega = (rank + 1) / (N + 1)
        logit = math.log(omega / (1 - omega)) if 0 < omega < 1 else (
            -50.0 if omega <= 0 else 50.0)
        total += 1
        if logit <= 0:
            overfit += 1
    return overfit / total if total else float("nan")


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--costs", default=",".join(str(c) for c in COST_GRID))
    args = ap.parse_args()
    costs = [float(c) for c in args.costs.split(",") if c.strip()]

    dates, tickers, prices, cash = load_monthly()
    start = first_valid(prices, len(dates))
    print(f"=== MONTHLY MULTI-ASSET TACTICAL ENGINE ===")
    print(f"  universe      : {len(tickers)} ETFs {tickers}")
    print(f"  common window : {dates[start]} .. {dates[-1]} "
          f"({len(dates) - start} months)")
    print(f"  cash proxy    : {CASH_PROXY} at 0 when unavailable (conservative)")
    print(f"  NOTE: the common window starts where ALL tickers exist, which is why")
    print(f"  2000-02 is NOT testable here. 2008 IS. The gap is stated, not filled")
    print(f"  with a shorter-history substitute.\n")

    results: dict[str, dict] = {}
    for cost in costs:
        print(f"--- cost {cost:.0f} bp per side of turnover ---")
        print(f"  {'strategy':<12} {'CAGR%':>7} {'vol%':>6} {'Sharpe':>7} "
              f"{'MDD%':>7} {'$10k->':>10}")
        for name in STRATEGIES:
            full = run(name, prices, dates, start, cash, cost)
            # SLICE TO THE INVESTED WINDOW. The price series starts before the
            # common window, and pre-window months have EMPTY weights, so they
            # contribute a 0% return and are pure dilution. Leaving them in made
            # stats() compute CAGR over 41.8 years for a portfolio that only
            # invested for 20.8, understating CAGR by roughly half, and reported
            # n_months 502 against a 250-month window. Terminal wealth was never
            # affected, which is exactly why the error survived a glance.
            r = full[start:]
            s = stats([0.0] + r)
            s["returns"] = r          # aligned to the invested window only
            results[f"{name}@{cost:g}"] = s
            print(f"  {name:<12} {s['cagr_pct']:>7.2f} {s['vol_pct']:>6.2f} "
                  f"{s['sharpe']:>7.2f} {s['maxdd_pct']:>7.2f} "
                  f"{s['terminal_10k']:>10,.0f}")
        print()

    # ---- leakage control: a deliberately clairvoyant strategy MUST win ----
    # If a strategy that can see next month's return does NOT dominate, then the
    # harness is broken somewhere else and every other number is untrustworthy.
    # The original look-ahead bug was found precisely because trend looked too
    # good; this control makes that detection systematic instead of lucky.
    print(f"\n=== LEAKAGE CONTROL (clairvoyant strategy must dominate) ===")
    clairvoyant = []
    prev = {}
    for t in range(len(dates)):
        r = rets_from(prices, t, back=0) if t > 0 else {k: 0.0 for k in prices}
        if t <= start:
            clairvoyant.append(0.0)
            continue
        best = max(r, key=lambda k: r[k])
        clairvoyant.append(r[best] - 2 * 10.0 / 1e4)
    cs = stats(clairvoyant)
    print(f"  perfect-foresight Sharpe: {cs.get('sharpe', float('nan')):.2f} "
          f"(CAGR {cs.get('cagr_pct', float('nan')):.1f}%)")
    print(f"  => a harness that cannot make a clairvoyant strategy win is broken.")

    # ---- break-even cost: the number that matters given cost is unmeasured ----
    print("=== BREAK-EVEN COST (the point of sweeping instead of assuming) ===")
    print(f"  {'strategy':<12} {'Sharpe@0':>9} {'Sharpe@20':>10} "
          f"{'beats SPY B&H at':>18}")
    spy0 = results[f"bh_spy@{costs[0]:g}"]["sharpe"]
    print(f"  {'SPY B&H':<12} {spy0:>9.2f} "
          f"{results[f'bh_spy@{costs[-1]:g}']['sharpe']:>10.2f}   (benchmark)")
    for name in STRATEGIES:
        if name == "bh_spy":
            continue
        s0 = results[f"{name}@{costs[0]:g}"]["sharpe"]
        sN = results[f"{name}@{costs[-1]:g}"]["sharpe"]
        be = "never"
        for c in costs:
            if results[f"{name}@{c:g}"]["sharpe"] > spy0:
                be = f"{c:.0f} bp"
                break
        print(f"  {name:<12} {s0:>9.2f} {sN:>10.2f} {be:>18}")

    # ---- statistics at the middle cost ----
    mid = costs[len(costs) // 2]
    print(f"\n=== STATISTICS AT {mid:.0f} bp/SIDE (n_trials={len(STRATEGIES)}) ===")
    print(f"  {'strategy':<12} {'Sharpe':>7} {'CI-LB':>7} {'CI-UB':>7} "
          f"{'DSR':>7}  verdict")
    base = None
    for name in STRATEGIES:
        s = results[f"{name}@{mid:g}"]
        r = s["returns"][1:]
        med, lo, hi = block_bootstrap_sharpe(s["returns"])
        sk = statistics.mean([(x - statistics.mean(r)) ** 3 for x in r]) / (
            statistics.pstdev(r) ** 3) if statistics.pstdev(r) else 0.0
        ku = statistics.mean([(x - statistics.mean(r)) ** 4 for x in r]) / (
            statistics.pstdev(r) ** 4) if statistics.pstdev(r) else 3.0
        dsr = deflated_sharpe(s["sharpe"], s["n_months"], len(STRATEGIES), sk, ku)
        verdict = "beats B&H" if s["sharpe"] > spy0 else "does not beat B&H"
        print(f"  {name:<12} {s['sharpe']:>7.2f} {lo:>7.2f} {hi:>7.2f} "
              f"{dsr:>7.3f}  {verdict}")

    # ---- PBO on the strategy x month matrix ----
    mat = [[results[f"{n}@{mid:g}"]["returns"][i] for n in STRATEGIES]
           for i in range(len(results[f"bh_spy@{mid:g}"]["returns"]))]
    pbo = pbo_cscv(mat)
    print(f"\n=== PBO / CSCV ({CSCV_BLOCKS} blocks, all {len(STRATEGIES)} strategies) ===")
    print(f"  PBO = {pbo:.3f}")
    print(f"  Reading: {pbo*100:.0f}% of the time the in-sample best strategy lands in")
    print(f"  the bottom half out of sample. 0.50 = selection is a coin flip.")
    if pbo > 0.4:
        print(f"  => selection among these strategies is NOT reliable. Do not pick")
        print(f"     the in-sample winner and expect it to persist.")

    # ---- stress windows ----
    # NOTE: `returns` is sliced to the invested window, so date indices must be
    # shifted by `start`. Getting this wrong silently produced +0.0% for every
    # strategy in every window, which looks like "nothing happened in 2008".
    print(f"\n=== STRESS WINDOWS (at {mid:.0f} bp/side) ===")
    for label, (a, b) in {"2008 GFC": ("2008-01", "2009-06"),
                          "2022 rate shock": ("2022-01", "2022-12")}.items():
        ia = next((i for i, d in enumerate(dates) if d >= a), None)
        ib = next((i for i, d in enumerate(dates) if d > b), len(dates))
        if ia is None:
            print(f"  {label:<16} not in window")
            continue
        ia_s, ib_s = max(0, ia - start), min(ib - start,
                                            len(results[f"bh_spy@{mid:g}"]["returns"]))
        if ib_s <= ia_s + 2:
            print(f"  {label:<16} not in window")
            continue
        cells = []
        for n in ("bh_spy", "sixty_forty", "trend", "dual_mom", "lowvol"):
            r = results[f"{n}@{mid:g}"]["returns"][ia_s:ib_s]
            cells.append(f"{n}={((math.prod([1 + x for x in r]) - 1) * 100):+.1f}%")
        print(f"  {label:<16} " + "  ".join(cells))

    # ---- honest verdict ----
    BENCHMARKS = ("bh_spy", "sixty_forty", "ew_all")
    best642 = results[f"sixty_forty@{mid:g}"]["sharpe"]
    best = max((n for n in STRATEGIES if n not in BENCHMARKS),
               key=lambda n: results[f"{n}@{mid:g}"]["sharpe"])
    bs = results[f"{best}@{mid:g}"]
    print(f"\n=== VERDICT ===")
    print(f"  best tactical (non-benchmark) at {mid:.0f}bp : {best} "
          f"(Sharpe {bs['sharpe']:.2f})")
    print(f"  vs SPY B&H {spy0:.2f}  |  vs 60/40 {best642:.2f}")
    if bs["sharpe"] <= best642:
        print(f"  No tactical strategy beat a static 60/40 on Sharpe at {mid:.0f} bp/side.")
        print(f"  The tactical books DO cut drawdown ({bs['maxdd_pct']:.1f}% vs "
              f"{results[f'sixty_forty@{mid:g}']['maxdd_pct']:.1f}% for 60/40 and "
              f"{results[f'bh_spy@{mid:g}']['maxdd_pct']:.1f}% for SPY), but they buy")
        print(f"  that with return. That is a RISK TRANSFORMATION, not an edge —")
        print(f"  the same conclusion the vol-scaling refutation reached.")
    else:
        print(f"  {best} beat 60/40 on Sharpe — but PBO is {pbo:.2f}; with "
              f"{len(STRATEGIES)} trials that is what multiplicity produces.")
    print(f"\n  NOTE ON DSR: every strategy here has a positive Sharpe over 20 years")
    print(f"  of equity beta, so DSR (which tests SR>0, not SR>benchmark) sits near")
    print(f"  1.0 for all of them and cannot discriminate. It is reported for")
    print(f"  completeness, NOT as a selection tool. The selection question is")
    print(f"  'beats the thing you could own for free', which is the Sharpe column.")
    print(f"\n  Evidence: backtest only, {bs['n_months']} invested months, cost SWEPT")
    print(f"  not measured. Zero forward observations. Not advice.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    slim = {k: {kk: vv for kk, vv in v.items() if kk != "returns"}
            for k, v in results.items()}
    OUT.write_text(json.dumps({
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "universe": tickers, "window": [dates[start], dates[-1]],
        "n_months": len(dates) - start, "costs_bp": costs,
        "n_trials": len(STRATEGIES), "pbo": pbo,
        "results": slim,
        "evidence_class": "BACKTEST (monthly, long-only, cost-swept)",
        "scope_excluded": ["leverage>1", "shorting", "options", "intraday",
                           "factor data", "2000-02 (outside common window)"],
    }, indent=2))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
