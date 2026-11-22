#!/usr/bin/env python3
"""residual_mean_reversion.py — market-neutral residual mean reversion.

H-2026-11-20-01 / H-2026-11-20-02 (factor choice: PCA eigenportfolios vs sector
ETFs).

The idea: a stock's return is mostly its market/sector exposure plus a
idiosyncratic piece. The idiosyncratic piece is what mean-reverts. So regress the
return on factor returns, treat the residual as an Ornstein-Uhlenbeck process, and
trade its standardized distance from equilibrium (the s-score).

Why the residual and not the price: a long-only dip-buyer is really buying beta
during a bull market — that is exactly what the RSI(2) replication showed (positive
absolute return, negative selection alpha). Trading the residual removes that by
construction: the position is the stock *hedged* by its factor loadings, so a
rising market moves both legs.

Deliberate choices:
  * every fit uses ONLY data up to and including the decision bar
  * the hedge is beta-weighted by the fitted loadings, not notional-equal
  * a half-life longer than the holding period is reported as unmeasurable
    rather than silently traded
  * entry/exit are on |s|, with the exit threshold below entry so a round trip
    does not require a full return to equilibrium
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

MIN_FIT_N = 60
DEFAULT_WINDOW = 60
ENTRY_S = 1.25
EXIT_S = 0.5
STOP_S = 4.0
# H-2026-11-20-01 pre-registers 5 bps/leg base and 10 bps stress.
COST_BPS = 5.0


def returns(prices: list[float]) -> list[float]:
    """Simple returns; a zero or missing price yields 0.0 rather than inf."""
    out = []
    for prev, cur in zip(prices, prices[1:]):
        if not prev or not cur:
            out.append(0.0)
        else:
            out.append(cur / prev - 1.0)
    return out


def ols(y: list[float], xs: list[list[float]]) -> tuple[float, list[float]] | None:
    """Least squares via normal equations. Returns (intercept, betas).

    No numpy dependency on purpose: this runs in the same constrained CI as the
    rest of the tools, and k is small (1-10 factors).
    """
    n = len(y)
    if n < MIN_FIT_N or not xs or len(xs[0]) != n:
        return None
    k = len(xs)
    # Design matrix with intercept as the first column.
    cols = [[1.0] * n] + [list(x) for x in xs]
    m = k + 1
    ata = [[sum(cols[i][t] * cols[j][t] for t in range(n)) for j in range(m)]
           for i in range(m)]
    atb = [sum(cols[i][t] * y[t] for t in range(n)) for i in range(m)]
    # Gaussian elimination with partial pivoting.
    for i in range(m):
        piv = max(range(i, m), key=lambda r: abs(ata[r][i]))
        if abs(ata[piv][i]) < 1e-12:
            return None  # singular: collinear factors, not a number to invent
        if piv != i:
            ata[i], ata[piv] = ata[piv], ata[i]
            atb[i], atb[piv] = atb[piv], atb[i]
        for r in range(i + 1, m):
            f = ata[r][i] / ata[i][i]
            for c in range(i, m):
                ata[r][c] -= f * ata[i][c]
            atb[r] -= f * atb[i]
    sol = [0.0] * m
    for i in reversed(range(m)):
        sol[i] = (atb[i] - sum(ata[i][j] * sol[j] for j in range(i + 1, m))) / ata[i][i]
    return sol[0], sol[1:]


def residuals(y: list[float], xs: list[list[float]]) -> list[float] | None:
    fit = ols(y, xs)
    if fit is None:
        return None
    a, betas = fit
    return [yt - a - sum(b * x for b, x in zip(betas, [x[t] for x in xs]))
            for t, yt in enumerate(y)]


def ou_fit(resid: list[float]) -> dict | None:
    """AR(1) on the residual: r_t = kappa*(mu - r_{t-1}) + noise.

    Regressing r_t on r_{t-1} gives rho; kappa = 1 - rho, mu = a / kappa, and the
    half-life is ln(2)/kappa. kappa <= 0 means no mean reversion at all — an
    honest None, not a tiny positive number from noise.

    Caveat that must not be dropped: on a pure random walk, AR(1) with a finite
    sample is biased DOWNWARD in rho (the Dickey-Fuller bias), so kappa > 0 and a
    short-looking half-life appear even when nothing mean-reverts. A half-life is
    therefore a filter, never a verdict — it can only exclude, and a survivor
    still needs out-of-sample confirmation.
    """
    if len(resid) < MIN_FIT_N:
        return None
    prev, cur = resid[:-1], resid[1:]
    mp, mc = statistics.fmean(prev), statistics.fmean(cur)
    cov = sum((p - mp) * (c - mc) for p, c in zip(prev, cur))
    var = sum((p - mp) ** 2 for p in prev)
    if var <= 0:
        return None
    rho = cov / var
    kappa = 1.0 - rho
    if kappa <= 0:
        return None
    a = mc - rho * mp
    mu = a / kappa
    errs = [c - (a + rho * p) for p, c in zip(prev, cur)]
    sigma = math.sqrt(sum(e * e for e in errs) / max(1, len(errs) - 1))
    sigma_eq = sigma / math.sqrt(1.0 - rho * rho) if 0 < rho < 1 else None
    if sigma_eq is None:
        return None
    return {
        "kappa": round(kappa, 6),
        "mu": round(mu, 6),
        "half_life": round(math.log(2) / kappa, 2),
        "sigma_eq": round(sigma_eq, 6),
        "rho": round(rho, 4),
    }


def s_score(resid: float, fit: dict) -> float | None:
    """Standardized distance from equilibrium."""
    if not fit.get("sigma_eq"):
        return None
    return (resid - fit["mu"]) / fit["sigma_eq"]


def round_trip_cost_pct(legs: int = 2, bps_per_leg: float = COST_BPS) -> float:
    """Cost of one round trip, in percent.

    Each leg pays bps on the way in and again on the way out, so a two-leg
    residual trade (the name plus its hedge) costs 4 x bps, not 2 x bps. The
    hedge is not free just because it is not the thing being predicted.
    """
    return legs * 2 * bps_per_leg / 100.0


def simulate(symbol: list[float], factors: dict[str, list[float]],
             window: int = DEFAULT_WINDOW, entry: float = ENTRY_S,
             exit_s: float = EXIT_S, stop: float = STOP_S,
             legs: int = 2, bps_per_leg: float = COST_BPS,
             gate: bool = False, stats: dict | None = None) -> list[dict]:
    """Walk-forward residual book on one symbol against factor price series.

    Every bar t uses factors[t-window:t] and symbol[t-window:t] to fit, then
    decides on bar t. Nothing from the future enters any fit.

    Each trade carries ``gross_pct``, ``cost_pct`` and ``pnl_pct`` (= gross -
    cost). Keeping gross visible is deliberate: it is what a naive backtest
    would report, and the gap between the two is the whole point.
    """
    cost_pct = round_trip_cost_pct(legs, bps_per_leg)
    r = returns(symbol)
    fr = {k: returns(v) for k, v in factors.items()}
    names = [k for k in fr if len(fr[k]) == len(r)]
    if not names or len(r) < window + MIN_FIT_N:
        return []
    ys = [fr[k] for k in names]
    trades: list[dict] = []
    open_pos: dict | None = None
    gated_out = 0
    for t in range(window, len(r)):
        y_win = r[t - window:t]
        x_win = [[x[t - window:t] for x in ys][j] for j in range(len(names))]
        resid_win = residuals(y_win, x_win)
        if resid_win is None:
            continue
        ols_fit = ols(y_win, x_win)
        if ols_fit is None:
            continue
        _, betas = ols_fit
        fit = ou_fit(resid_win)
        if fit is None:
            continue
        if fit["half_life"] > window / 2:
            # Too slow for this horizon: trading it would be a slow long-only
            # position, not mean reversion.
            continue
        s = s_score(resid_win[-1], fit)
        if s is None:
            continue
        # CAPTURED reversion, not the full distance. The exit is at |s| <=
        # EXIT_S, so only (|s| - EXIT_S) * sigma_eq is actually collectable;
        # using the full |s| * sigma_eq overstates the tradeable edge by 67%
        # at |s| = 1.25. sigma_eq is in return space, so the result is a
        # percent directly comparable to the round-trip cost.
        expected_pct = max(0.0, abs(s) - exit_s) * fit["sigma_eq"] * 100.0
        if open_pos is None:
            if abs(s) >= entry:
                if gate and expected_pct <= cost_pct:
                    # The forecast is smaller than the cost it must pay:
                    # negative expectancy regardless of forecast skill.
                    gated_out += 1
                    continue
                side = -1 if s > 0 else 1  # short when above equilibrium
                open_pos = {"t": t, "s": s, "side": side, "entry": symbol[t],
                            "half_life": fit["half_life"],
                            "expected_pct": expected_pct,
                            "betas": betas,
                            "fac_entry": {k: factors[k][t] for k in names}}
        else:
            held = t - open_pos["t"]
            if (abs(s) <= exit_s or abs(s) >= stop
                    or held >= max(2, int(open_pos["half_life"] * 3))):
                sym_ret = symbol[t] / open_pos["entry"] - 1.0
                # Book the hedge. The position is the name plus a short of its
                # factor loadings, so P&L is the symbol move MINUS the loaded
                # factor moves. Charging cost for two legs while booking one
                # made the book unhedged where it earns and hedged where it pays.
                hedge_ret = sum(
                    b * (factors[k][t] / open_pos["fac_entry"][k] - 1.0)
                    for k, b in zip(names, open_pos["betas"]))
                gross = (sym_ret - hedge_ret) * 100.0 * open_pos["side"]
                trades.append({
                    "symbol": names and "RESID",
                    "asset_class": "ETF",
                    "direction": "LONG" if open_pos["side"] > 0 else "SHORT",
                    "strategy": f"RESID_MR_w{window}",
                    "entry_price": round(open_pos["entry"], 6),
                    "gross_pct": round(gross, 6),
                    "cost_pct": round(cost_pct, 6),
                    "pnl_pct": round(gross - cost_pct, 6),
                    "hold_days": held,
                    "entry_s": round(open_pos["s"], 4),
                    "expected_pct": round(open_pos["expected_pct"], 6),
                    "exit_s": round(s, 4),
                    "half_life_at_entry": open_pos["half_life"],
                    "exit_kind": ("stop" if abs(s) >= stop
                                  else "time" if held >= max(2, int(open_pos["half_life"] * 3))
                                  else "revert"),
                    "factors": names,
                })
                open_pos = None
    if stats is not None:
        stats["gated_out"] = gated_out
        stats["entries"] = len(trades) + (1 if open_pos else 0)
    return trades


def paired_gate_compare(symbol: list[float], factors: dict[str, list[float]],
                        window: int = DEFAULT_WINDOW, b: int = 2000,
                        seed: int = 0) -> dict:
    """H-2026-11-20-03: gated minus ungated, on identical signals.

    The comparison must be paired — the same bars, the same fits, differing
    only in whether a trade whose forecast does not clear cost is taken. An
    unpaired comparison would confound the gate with a different trade set.

    Reported together, never substituted for each other:
      * the paired Sharpe difference and its bootstrap CI (the statistic)
      * turnover reduction (did it actually trade less?)
      * gross-alpha retention (did it keep the good trades?)
    """
    import random

    base_stats: dict = {}
    gated_stats: dict = {}
    base = simulate(symbol, factors, window, stats=base_stats)
    gated = simulate(symbol, factors, window, gate=True, stats=gated_stats)
    if not base or not gated:
        return {"verdict": "INCONCLUSIVE — one arm produced no round trips"}

    def sharpe(ts: list[dict]) -> float:
        v = [t["pnl_pct"] for t in ts]
        if len(v) < 2:
            return 0.0
        sd = statistics.stdev(v)
        if sd == 0:
            return 0.0
        hold = statistics.fmean([t["hold_days"] for t in ts]) or 1.0
        return statistics.fmean(v) / sd * math.sqrt(252.0 / hold)

    sh_base, sh_gated = sharpe(base), sharpe(gated)
    gross_base = sum(t["gross_pct"] for t in base)
    gross_gated = sum(t["gross_pct"] for t in gated)
    retention = gross_gated / gross_base if gross_base else None
    turnover_red = 1.0 - len(gated) / len(base)

    # Paired bootstrap: resample trade indices once, apply to both arms where
    # both have a trade; the delta distribution is what we test.
    rng = random.Random(seed)
    deltas = []
    for _ in range(b):
        # ONE draw of indices applied to both arms — that is what makes the
        # comparison paired. Two independent draws (as this did) confound the
        # gate with a different trade set, exactly what the docstring forbids.
        n = min(len(base), len(gated))
        idx = [rng.randrange(n) for _ in range(n)]
        vb = [base[i]["pnl_pct"] for i in idx]
        vg = [gated[i]["pnl_pct"] for i in idx]
        if len(vb) < 2 or len(vg) < 2:
            continue
        sdb, sdg = statistics.stdev(vb), statistics.stdev(vg)
        if sdb == 0 or sdg == 0:
            continue
        deltas.append(statistics.fmean(vg) / sdg - statistics.fmean(vb) / sdb)
    deltas.sort()
    lo = deltas[int(0.025 * len(deltas))] if deltas else None
    hi = deltas[int(0.975 * len(deltas)) - 1] if deltas else None
    return {
        "n_ungated": len(base),
        "n_gated": len(gated),
        "gated_out": gated_stats.get("gated_out", 0),
        "sharpe_ungated": round(sh_base, 4),
        "sharpe_gated": round(sh_gated, 4),
        "sharpe_delta": round(sh_gated - sh_base, 4),
        "delta_ci95": [round(lo, 4) if lo is not None else None,
                       round(hi, 4) if hi is not None else None],
        "ci_excludes_zero": bool(lo is not None and hi is not None
                                 and (lo > 0 or hi < 0)),
        "turnover_reduction": round(turnover_red, 4),
        "gross_alpha_retention": round(retention, 4) if retention is not None else None,
        "verdict": ("SUPPORTED" if lo is not None and hi is not None and lo > 0
                    else "NOT SUPPORTED"),
    }


def summarize(trades: list[dict]) -> dict:
    if not trades:
        return {"n": 0, "verdict": "INCONCLUSIVE — no round trips"}
    nets = [t["pnl_pct"] for t in trades]
    win = sum(1 for n in nets if n > 0)
    gross_win = sum(n for n in nets if n > 0)
    gross_loss = -sum(n for n in nets if n < 0)
    return {
        "n": len(trades),
        "mean_net_pct": round(statistics.fmean(nets), 4),
        # Rows built by hand (or by an older caller) may carry only pnl_pct;
        # fall back to it rather than raising, so summarize stays total.
        "mean_gross_pct": round(statistics.fmean(
            [t.get("gross_pct", t["pnl_pct"]) for t in trades]), 4),
        "cost_per_trade_pct": round(statistics.fmean(
            [t.get("cost_pct", 0.0) for t in trades]), 4),
        "win_rate": round(win / len(nets), 4),
        "profit_factor": round(gross_win / gross_loss, 3) if gross_loss else None,
        "mean_hold": round(statistics.fmean([t["hold_days"] for t in trades]), 2),
        "by_exit": {k: sum(1 for t in trades if t["exit_kind"] == k)
                    for k in ("revert", "stop", "time")},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="residual mean reversion (s-score)")
    ap.add_argument("--symbol", default="SPY")
    ap.add_argument("--factors", nargs="*", default=["QQQ", "IWM", "TLT"])
    ap.add_argument("--window", type=int, default=DEFAULT_WINDOW)
    ap.add_argument("--period", default="10y")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    if not args.fetch:
        print("dry run: pass --fetch to download bars")
        return 0

    import yfinance as yf

    def series(sym: str) -> list[float]:
        df = yf.Ticker(sym).history(period=args.period, interval="1d", auto_adjust=True)
        return [float(v) for v in df["Close"].tolist() if v == v]

    px = series(args.symbol)
    fac = {f: series(f) for f in args.factors}
    n = min([len(px)] + [len(v) for v in fac.values()])
    px = px[-n:]
    fac = {k: v[-n:] for k, v in fac.items()}
    if n < args.window + MIN_FIT_N:
        print(f"BLOCKED_DATA — only {n} aligned bars, need "
              f"{args.window + MIN_FIT_N}")
        return 2
    trades = simulate(px, fac, args.window)
    rep = {"hypothesis": "H-2026-11-20-01/-02", "symbol": args.symbol,
           "factors": args.factors, "window": args.window,
           "bars": n, "summary": summarize(trades)}
    text = json.dumps(rep, indent=1)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
