#!/usr/bin/env python3
"""horizon_backtest.py — real backtests for the horizon / asset-class claims.

Answers the question "what is the best possible investment for short, medium and
long horizons" with distributions computed from actual prices rather than
opinion, and tests the doctrine claims that the audit2 page states as fact.

Experiments
  E1 horizon       rolling 1/3/5/10-year returns for SPY, 60/40, cash (BIL) and
                   BTC; share of windows where equity loses to cash
  E2 vol scaling   identical TSMOM signal, unscaled vs inverse-vol scaled, to
                   test "volatility scaling is free alpha (+0.3 Sharpe)"
  E3 faber         10-month SMA tactical allocation on SPY/QQQ, net of costs
  E4 mer drag      30-year terminal wealth under different expense ratios
  E5 class-vs-pick BTC hold vs SPY hold vs cash over identical windows

Honesty rules baked in:
  * a signal computed from data through day t-1 sets the exposure for day t, so
    there is no look-ahead by construction (`_shift`);
  * every strategy charges a per-switch cost, and each is run at 1x and 2x;
  * Sharpe is excess over the cash proxy (BIL), not over zero;
  * rolling-window statistics are overlapping and the effective independent
    window count is printed next to them;
  * a class KILL verdict is never applied to the asset class itself, only to the
    picks — E5 keeps those two numbers separate.

Usage:
  python3 tools/horizon_backtest.py            # run all experiments, write JSON
  python3 tools/horizon_backtest.py --json out.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CACHE = Path("/tmp/horizon_cache")
CACHE.mkdir(parents=True, exist_ok=True)
PERIODS = 252
CASH = "BIL"          # T-bill ETF: the investable cash proxy, total-return adjusted
EQUITY = "SPY"
BOND = "AGG"
CRYPTO = "BTC-USD"
COST_BPS = 5.0        # one-way ETF cost per switch, charged at 1x and 2x


# ----------------------------------------------------------------------- data
def _close_series(df):
    s = df["Close"]
    if hasattr(s, "columns"):
        s = s.iloc[:, 0]
    return s


def load_close(symbol: str, max_age_days: float = 7.0) -> list[tuple[str, float]]:
    """[[iso_date, adjusted_close], ...] oldest first, cached in /tmp."""
    path = CACHE / f"{symbol.replace('^', '').replace('=', '_')}.json"
    if path.exists() and time.time() - path.stat().st_mtime < max_age_days * 86400:
        return json.loads(path.read_text())
    import warnings
    import yfinance as yf
    warnings.filterwarnings("ignore")
    df = yf.download(symbol, period="max", progress=False, auto_adjust=True, threads=False)
    if df is None or len(df) == 0:
        raise RuntimeError(f"no data for {symbol}")
    s = _close_series(df).dropna()
    out = [[d.strftime("%Y-%m-%d"), float(v)] for d, v in s.items()]
    path.write_text(json.dumps(out))
    return out


def cash_index_from_yield(rows: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """Turn a T-bill yield series (percent) into a total-return cash index.

    The investable cash ETF (BIL) only starts in 2007, but the horizon question
    needs 1990s data to get independent 10-year windows. A T-bill yield series
    gives a defensible accrual proxy: daily return = (1 + y/100) ** (1/252) - 1.
    """
    out, idx = [], 1.0
    for i, (d, y) in enumerate(rows):
        if i:
            idx *= (1.0 + max(float(y), 0.0) / 100.0) ** (1.0 / PERIODS)
        out.append([d, idx])
    return out


def align(named: dict[str, list[tuple[str, float]]]) -> tuple[list[str], dict[str, list[float]]]:
    """Inner-join several series on date, so every column has the same calendar."""
    maps = {k: dict(v) for k, v in named.items()}
    dates = sorted(set.intersection(*(set(m) for m in maps.values())))
    return dates, {k: [m[d] for d in dates] for k, m in maps.items()}


# ---------------------------------------------------------------------- maths
def returns(closes: list[float]) -> list[float]:
    return [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes))]


def ann_return(closes: list[float], periods: int = PERIODS) -> float:
    if len(closes) < 2:
        return 0.0
    years = (len(closes) - 1) / periods
    return (closes[-1] / closes[0]) ** (1.0 / years) - 1.0


def ann_vol(rets: list[float], periods: int = PERIODS) -> float:
    if len(rets) < 2:
        return 0.0
    mu = sum(rets) / len(rets)
    var = sum((r - mu) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var * periods)


def sharpe(rets: list[float], cash_rets: list[float] | None = None,
           periods: int = PERIODS) -> float:
    """Annualised Sharpe on excess-over-cash returns."""
    if len(rets) < 2:
        return 0.0
    ex = [r - (cash_rets[i] if cash_rets else 0.0) for i, r in enumerate(rets)]
    mu = sum(ex) / len(ex)
    var = sum((r - mu) ** 2 for r in ex) / (len(ex) - 1)
    sd = math.sqrt(var)
    return 0.0 if sd == 0 else mu / sd * math.sqrt(periods)


def max_drawdown(closes: list[float]) -> float:
    peak, worst = closes[0], 0.0
    for c in closes:
        peak = max(peak, c)
        worst = min(worst, c / peak - 1.0)
    return worst


def equity_curve(rets: list[float], start: float = 1.0) -> list[float]:
    curve, v = [start], start
    for r in rets:
        v *= 1.0 + r
        curve.append(v)
    return curve


def horizon_returns(closes: list[float], years: float, periods: int = PERIODS) -> list[float]:
    """All overlapping `years`-long returns. Overlapping by construction."""
    n = max(1, int(round(years * periods)))
    return [closes[i + n] / closes[i] - 1.0 for i in range(len(closes) - n)]


def percentiles(vals: list[float], qs=(10, 50, 90)) -> dict:
    if not vals:
        return {}
    s = sorted(vals)
    out = {}
    for q in qs:
        idx = min(len(s) - 1, max(0, int(round(q / 100.0 * (len(s) - 1)))))
        out[f"p{q}"] = round(s[idx], 6)
    return out


def _shift(xs: list[float], n: int = 1, fill: float = 0.0) -> list[float]:
    """Past-only: out[t] = xs[t-n]. This is the no-look-ahead primitive."""
    return [fill] * min(n, len(xs)) + xs[: max(0, len(xs) - n)]


def sma(xs: list[float], n: int) -> list[float]:
    out, run = [], 0.0
    for i, x in enumerate(xs):
        run += x
        if i >= n:
            run -= xs[i - n]
        out.append(run / min(i + 1, n))
    return out


def rolling_vol(rets: list[float], n: int = 20) -> list[float]:
    out = []
    for i in range(len(rets)):
        lo = max(0, i - n + 1)
        w = rets[lo:i + 1]
        mu = sum(w) / len(w)
        out.append(math.sqrt(sum((r - mu) ** 2 for r in w) / max(1, len(w) - 1) * PERIODS))
    return out


# ------------------------------------------------------------------- backtest
def _monthly_compound(dates: list[str], rets: list[float]) -> list[float]:
    """Compound daily returns into calendar-month returns."""
    out: list[float] = []
    cur_month, acc = None, 1.0
    for d, r in zip(dates, rets):
        m = d[:7]
        if cur_month is not None and m != cur_month:
            out.append(acc - 1.0)
            acc = 1.0
        cur_month = m
        acc *= 1.0 + r
    if cur_month is not None:
        out.append(acc - 1.0)
    return out


def run_exposure(closes: list[float], exposure: list[float], cash_closes: list[float],
                 cost_bps: float, dates: list[str] | None = None) -> dict:
    """Compound a daily exposure series against cash. Cost charged on |Δweight|.

    `exposure[i]` is the weight **held over day i** (from close i-1 to close i),
    so it earns `closes[i]/closes[i-1]-1`. Signals are lagged before they reach
    this function, which is what makes the no-look-ahead guarantee hold.
    """
    n = min(len(closes), len(exposure), len(cash_closes))
    strat, cash_rets, cost_drag, switches = [], [], 0.0, 0
    prev = 0.0
    for i in range(1, n):
        w = exposure[i]
        mkt = closes[i] / closes[i - 1] - 1.0
        csh = cash_closes[i] / cash_closes[i - 1] - 1.0
        r = w * mkt + (1.0 - w) * csh
        turn = abs(w - prev)
        if turn > 1e-12:
            switches += 1
            drag = turn * cost_bps / 1e4
            cost_drag += drag
            r -= drag
        strat.append(r)
        cash_rets.append(csh)
        prev = w
    curve = equity_curve(strat)
    out = {
        "cagr": round(ann_return(curve), 6),
        "vol": round(ann_vol(strat), 6),
        "sharpe": round(sharpe(strat, cash_rets), 4),
        "max_dd": round(max_drawdown(curve), 6),
        "time_in_market": round(sum(1 for w in exposure[1:n] if w > 1e-9) / max(1, n - 1), 4),
        "switches": switches,
        "cost_drag_annual": round(cost_drag / max(1e-9, (n - 1) / PERIODS), 6),
        "final_equity": round(curve[-1], 6),
        "n_days": n - 1,
    }
    if dates and len(dates) >= n:
        out["sharpe_monthly"] = round(
            sharpe(_monthly_compound(dates[1:n], strat), _monthly_compound(dates[1:n], cash_rets),
                   periods=12), 4)
    return out


def tsmom_exposure(closes: list[float], lookback: int = 200,
                   target_vol: float | None = None, cap: float = 1.0) -> list[float]:
    """Long when close > SMA(lookback), else cash. Signal is lagged one day."""
    sig = [1.0 if c > s else 0.0 for c, s in zip(closes, sma(closes, lookback))]
    sig = _shift(sig, 1, 0.0)
    if target_vol is None:
        return sig
    vol = rolling_vol(returns(closes), 20)
    vol = _shift(vol, 2, 0.0)  # vol known through t-1 only
    lev = []
    for s, v in zip(sig, vol[: len(sig)]):
        if v <= 0:
            lev.append(0.0)
        else:
            lev.append(min(cap, target_vol / v))
    return [s * l for s, l in zip(sig, lev)]


def faber_exposure(dates: list[str], closes: list[float], months: int = 10) -> list[float]:
    """Monthly 10-month SMA regime, held from the next month's first session."""
    month_last: dict[str, int] = {}
    for i, d in enumerate(dates):
        month_last[d[:7]] = i
    sig = [0.0] * len(closes)
    keys = sorted(month_last)
    for j, m in enumerate(keys):
        if j < months:
            continue
        window = [closes[month_last[k]] for k in keys[j - months:j]]
        on = closes[month_last[m]] > sum(window) / len(window)
        # apply from the first session of the NEXT month
        start = month_last[m] + 1
        end = month_last[keys[j + 1]] + 1 if j + 1 < len(keys) else len(closes)
        for i in range(start, end):
            sig[i] = 1.0 if on else 0.0
    return sig


def mer_drag(gross: float = 0.07, years: int = 30,
             mers=(0.0005, 0.005, 0.01, 0.015, 0.02)) -> dict:
    out = {}
    for m in mers:
        out[f"{m * 100:.2f}%"] = round((1 + gross - m) ** years, 3)
    base = out[f"{mers[0] * 100:.2f}%"]
    return {"terminal_multiple": out,
            "gap_vs_cheapest_pct": {k: round(100 * (1 - v / base), 2) for k, v in out.items()},
            "required_gross_for_1.5pct_to_match_cheapest":
                round(mers[0] + 0.015 - mers[0], 4)}


# ---------------------------------------------------------------- experiments
def e1_horizon(dates, cols, label: str = "") -> dict:
    cash = cols[CASH]
    spy = cols[EQUITY]
    universe = {"SPY": spy, "cash": cash}
    if BOND in cols:
        ratio = 0.6
        universe["60/40"] = [ratio * cols[EQUITY][i] / cols[EQUITY][0] +
                             (1 - ratio) * cols[BOND][i] / cols[BOND][0]
                             for i in range(len(dates))]
    out = {"label": label, "window": {"start": dates[0], "end": dates[-1]},
           "sessions": len(dates), "horizons": {}}
    for years in (1, 3, 5, 10):
        row = {}
        for name, series in universe.items():
            hr = horizon_returns(series, years)
            if not hr:
                continue
            row[name] = {"median": round(percentiles(hr)["p50"], 4),
                         "p10": round(percentiles(hr)["p10"], 4),
                         "p90": round(percentiles(hr)["p90"], 4),
                         "pct_negative": round(100 * sum(1 for r in hr if r < 0) / len(hr), 1),
                         "n_windows": len(hr),
                         "n_independent_windows": len(hr) // max(1, int(years * PERIODS)) + 1}
        spy_hr = horizon_returns(spy, years)
        cash_hr = horizon_returns(cash, years)
        if spy_hr and cash_hr:
            m = min(len(spy_hr), len(cash_hr))
            row["SPY_underperforms_cash_pct"] = round(
                100 * sum(1 for a, b in zip(spy_hr[:m], cash_hr[:m]) if a < b) / m, 1)
        out["horizons"][f"{years}y"] = row
    return out


def e2_vol_scaling(dates, cols) -> dict:
    spy, cash = cols[EQUITY], cols[CASH]
    base = tsmom_exposure(spy, 200)
    results = {}
    for label, exp, costs in (
            ("tsmom_unscaled", base, (COST_BPS, COST_BPS * 2)),
            ("tsmom_volscaled_cap1", tsmom_exposure(spy, 200, 0.10, 1.0), (COST_BPS, COST_BPS * 2)),
            ("tsmom_volscaled_cap2", tsmom_exposure(spy, 200, 0.10, 2.0), (COST_BPS, COST_BPS * 2))):
        results[label] = {
            f"cost_{'1x' if i == 0 else '2x'}": run_exposure(spy, exp, cash, c)
            for i, c in enumerate(costs)}
    d1 = results["tsmom_volscaled_cap1"]["cost_1x"]["sharpe"] - results["tsmom_unscaled"]["cost_1x"]["sharpe"]
    d2 = results["tsmom_volscaled_cap2"]["cost_1x"]["sharpe"] - results["tsmom_unscaled"]["cost_1x"]["sharpe"]
    return {"window": {"start": dates[0], "end": dates[-1]}, "results": results,
            "delta_sharpe_cap1": round(d1, 4), "delta_sharpe_cap2": round(d2, 4),
            "doctrine_claim": "+0.30 Sharpe",
            "claim_reproduces_cap1": d1 >= 0.30, "claim_reproduces_cap2": d2 >= 0.30}


def e3_faber(dates, cols) -> dict:
    out = {}
    for sym in (EQUITY, "QQQ"):
        series = cols.get(sym)
        if not series:
            continue
        exp = faber_exposure(dates, series)
        out[sym] = {
            "faber_1x": run_exposure(series, exp, cols[CASH], COST_BPS, dates),
            "faber_2x": run_exposure(series, exp, cols[CASH], COST_BPS * 2, dates),
            "buy_hold_1x": run_exposure(series, [1.0] * len(series), cols[CASH], COST_BPS, dates),
        }
    return {"window": {"start": dates[0], "end": dates[-1]}, "results": out}


def e4_mer() -> dict:
    return mer_drag()


def e5_class_vs_pick(dates, cols) -> dict:
    out = {}
    for sym in (CRYPTO, EQUITY, CASH):
        series = cols.get(sym)
        if not series:
            continue
        out[sym] = {
            "cagr": round(ann_return(series), 4),
            "vol": round(ann_vol(returns(series)), 4),
            "sharpe_vs_cash": round(sharpe(returns(series), returns(cols[CASH])), 4),
            "max_dd": round(max_drawdown(series), 4),
            "horizons": {f"{y}y": percentiles(horizon_returns(series, y), (50,))
                         for y in (1, 3, 5)},
        }
    return {"window": {"start": dates[0], "end": dates[-1]}, "results": out,
            "note": "asset-class risk premium, NOT our pick alpha; the ledger's KILL "
                    "verdicts describe pick rows, not these numbers"}


# ------------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(ROOT / "reports" / "horizon_backtest_2026-11-22.json"))
    a = ap.parse_args()
    named = {}
    for s in [EQUITY, "QQQ", BOND, CASH, CRYPTO, "^IRX"]:
        try:
            named[s] = load_close(s)
            print(f"loaded {s}: {len(named[s])} bars {named[s][0][0]}..{named[s][-1][0]}")
        except Exception as exc:  # noqa: BLE001
            print(f"skip {s}: {type(exc).__name__}: {exc}")
    out = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "cost_bps_per_switch": COST_BPS,
           "data": {s: {"bars": len(named[s]), "start": named[s][0][0],
                        "end": named[s][-1][0]} for s in named}}

    # Long window (1993+): SPY against a T-bill accrual index, for the horizon
    # question where independent 10-year windows matter most.
    if "^IRX" in named:
        cash_long = cash_index_from_yield(named["^IRX"])
        dates_l, cols_l = align({EQUITY: named[EQUITY], CASH: cash_long})
        print(f"long window {dates_l[0]}..{dates_l[-1]} ({len(dates_l)} sessions)")
        out["e1_horizon_long"] = e1_horizon(dates_l, cols_l,
                                            "SPY vs T-bill accrual (^IRX)")

    # Core window (2007+): investable cash ETF plus bonds, for strategies.
    core_named = {k: named[k] for k in (EQUITY, "QQQ", BOND, CASH) if k in named}
    dates_c, cols_c = align(core_named)
    print(f"core window {dates_c[0]}..{dates_c[-1]} ({len(dates_c)} sessions)")
    out["e1_horizon_core"] = e1_horizon(dates_c, cols_c, "SPY / 60-40 vs BIL")
    out["e2_vol_scaling"] = e2_vol_scaling(dates_c, cols_c)
    out["e3_faber"] = e3_faber(dates_c, cols_c)
    out["e4_mer_drag"] = e4_mer()

    btc_named = {k: named[k] for k in (EQUITY, CASH, CRYPTO) if k in named}
    if len(btc_named) == 3:
        dates_b, cols_b = align(btc_named)
        print(f"crypto window {dates_b[0]}..{dates_b[-1]} ({len(dates_b)} sessions)")
        out["e5_class_vs_pick"] = e5_class_vs_pick(dates_b, cols_b)

    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("e2_vol_scaling", "e3_faber", "e4_mer_drag")}, indent=1)[:3000])
    print(f"wrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
