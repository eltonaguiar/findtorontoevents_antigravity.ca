#!/usr/bin/env python3
"""PROVEIT: scenario portfolios + trading-philosophy backtest, with explicit fees.

Answers, with arithmetic rather than opinion:
  * which asset classes would I endorse at $300 / $500 / $2,000 / $10,000?
  * does a trading philosophy (buy-and-hold vs TP/SL vs trend timing) actually beat
    simply holding, after real costs?
  * what breaks first at small account sizes?

Fee model, stated because it drives everything:
  * commission per order ....... $0 (discount broker) — also runnable at $9.99
  * spread / slippage .......... 5bp round-turn on every traded notional
  * fund MER ................... annual drag, charged daily
  * fractional shares .......... NOT available (whole shares), so small accounts
                                 carry unavoidable cash drag

Honesty constraints baked in:
  * One window (2021-11-15..2026-11-15). Bull-heavy, one rate cycle. Not a forecast.
  * The signals used here are the same family the 1000-cell sweep killed; they are
    included precisely to show loss, not to sell them.
  * No result here is investment advice or tradeable.

    python3 tools/proveit_sim.py --out-dir <repo>/PROVEIT/PROVEIT_<stamp>KILOCODE_AGENT
"""
import argparse
import json
import math
import statistics as st
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

ANN = 252
START, END = "2021-11-15", "2026-11-15"
SPREAD_BP = 5.0
MER = {"SPY": 0.000945, "TLT": 0.0015, "GLD": 0.0040, "BIL": 0.00136}
TICKERS = list(MER)
SCENARIOS = [300, 500, 2000, 10000]


def fetch():
    import yfinance as yf
    out = {}
    for t in TICKERS:
        h = yf.Ticker(t).history(start=START, end=END)
        if not len(h):
            raise SystemExit(f"no data for {t}")
        out[t] = {"d": [str(i.date()) for i in h.index],
                  "c": [float(v) for v in h["Close"]]}
    n = min(len(out[t]["c"]) for t in TICKERS)
    return {t: out[t]["c"][-n:] for t in TICKERS}, out["SPY"]["d"][-n:]


def sma(xs, n):
    out = [None] * len(xs)
    run = 0.0
    for i, x in enumerate(xs):
        run += x
        if i >= n:
            run -= xs[i - n]
        if i >= n - 1:
            out[i] = run / n
    return out


def buy(px, cash, notional, comm):
    """Whole shares, spending at most `notional` OUT OF the full `cash` balance.

    BUG FIXED: the first version was called as buy(px, cash*0.6) and its return
    assigned to `cash`, which silently deleted the other 40% of the balance.
    That produced a $300 buy-and-hold ending at $72 - nonsense that looked like a
    finding. Notional is now capped against total cash and the FULL remainder is
    returned.
    """
    if px <= 0 or notional <= 0 or cash <= 0:
        return 0, cash, 0.0
    budget = min(notional, cash)
    qty = int(budget // px)
    while qty > 0:
        n = qty * px
        fee = comm + n * SPREAD_BP / 1e4
        if n + fee <= cash:
            return qty, cash - n - fee, fee
        qty -= 1
    return 0, cash, 0.0


def sell(px, qty, comm):
    if qty <= 0:
        return 0.0, 0.0
    notional = qty * px
    fee = comm + notional * SPREAD_BP / 1e4
    return notional - fee, fee


def run(strategy, start_cash, px, comm=0.0):
    """Daily-marked simulation. Returns dict of results."""
    n = len(px["SPY"])
    cash = float(start_cash)
    pos = {t: 0 for t in ("SPY", "TLT", "GLD")}
    fees = 0.0
    trades = 0
    navs = []
    entry = {}
    s200 = sma(px["SPY"], 200)
    last_rebal_year = None

    def targets():
        return {"SPY": 0.6, "TLT": 0.4, "GLD": 0.0}

    for i in range(n):
        nav = cash
        for t, q in pos.items():
            nav += q * px[t][i]
        # MER drag applied daily to held positions
        for t, q in pos.items():
            if q:
                nav -= q * px[t][i] * MER[t] / ANN
        navs.append(nav)

        if i < 200:
            continue

        if strategy == "buy_hold":
            if i == 200:
                for t, w in targets().items():
                    if w > 0:
                        total = cash + sum(pos[x] * px[x][i] for x in pos)
                        q, cash, f = buy(px[t][i], cash, total * w / sum(targets().values()), comm)
                        pos[t] += q; fees += f; trades += q > 0

        elif strategy == "annual_rebalance":
            yr = 2021 + i // 252
            if last_rebal_year is None or yr != last_rebal_year:
                total = cash + sum(pos[t] * px[t][i] for t in pos)
                for t in pos:
                    cash += sell(px[t][i], pos[t], comm)[0]
                pos = {t: 0 for t in pos}
                for t, w in targets().items():
                    if w > 0:
                        q, cash, f = buy(px[t][i], cash, total * w, comm)
                        pos[t] += q; fees += f; trades += q > 0
                last_rebal_year = yr

        elif strategy == "tp_sl":
            if i == 200:
                for t, w in targets().items():
                    if w > 0:
                        tot = cash + sum(pos[x] * px[x][i] for x in pos)
                        q, cash, f = buy(px[t][i], cash, tot * w, comm)
                        pos[t] += q; fees += f; trades += q > 0
                        if q:
                            entry[t] = px[t][i]
            for t in ("SPY", "TLT"):
                if pos[t] > 0 and t in entry:
                    r = px[t][i] / entry[t] - 1.0
                    if r >= 0.20 or r <= -0.10:       # TP +20% / SL -10%
                        proceeds, f = sell(px[t][i], pos[t], comm)
                        cash += proceeds; fees += f; trades += 1
                        pos[t] = 0
                        entry.pop(t, None)
                elif pos[t] == 0 and cash > px[t][i]:
                    q, cash, f = buy(px[t][i], cash, cash, comm)
                    if q:
                        pos[t] += q; fees += f; trades += 1; entry[t] = px[t][i]

        elif strategy == "trend_200":
            want = px["SPY"][i] > (s200[i] or px["SPY"][i])
            if want and pos["SPY"] == 0:
                q, cash, f = buy(px["SPY"][i], cash, cash, comm)
                pos["SPY"] += q; fees += f; trades += q > 0
            elif not want and pos["SPY"] > 0:
                proceeds, f = sell(px["SPY"][i], pos["SPY"], comm)
                cash += proceeds; fees += f; trades += 1
                pos["SPY"] = 0

    final = navs[-1]
    peak, mdd = 0.0, 0.0
    for v in navs:
        peak = max(peak, v)
        if peak > 0:
            mdd = min(mdd, v / peak - 1)
    yrs = n / ANN
    cagr = (final / start_cash) ** (1 / yrs) - 1 if final > 0 else -1
    return {"start": start_cash, "final": round(final, 2),
            "cagr_pct": round(cagr * 100, 2), "max_dd_pct": round(mdd * 100, 2),
            "trades": trades, "fees_and_spread": round(fees, 2),
            "fee_pct_of_start": round(fees / start_cash * 100, 2),
            "idle_cash_pct": round(cash / final * 100, 1) if final else 0}


STRATS = ["buy_hold", "annual_rebalance", "tp_sl", "trend_200"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--commission", type=float, default=0.0)
    a = ap.parse_args(argv)

    px, dates = fetch()
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%MZ")

    payload = {"generated_at": stamp, "window": [dates[0], dates[-1]], "n_days": len(dates),
               "commission": a.commission, "spread_bp": SPREAD_BP,
               "mer": MER, "fractional_shares": False,
               "scenarios": {}}

    print(f"  window {dates[0]} .. {dates[-1]}  n={len(dates)}  comm=${a.commission}")
    print(f"  {'start':>7} {'strategy':18s}{'final':>10}{'CAGR':>8}{'maxDD':>8}"
          f"{'trades':>8}{'fees$':>8}{'fee%':>7}{'idle%':>7}")
    for s in SCENARIOS:
        payload["scenarios"][str(s)] = {}
        for strat in STRATS:
            r = run(strat, s, px, a.commission)
            payload["scenarios"][str(s)][strat] = r
            print(f"  {s:>7} {strat:18s}{r['final']:>10.2f}{r['cagr_pct']:>8.2f}"
                  f"{r['max_dd_pct']:>8.2f}{r['trades']:>8}{r['fees_and_spread']:>8.2f}"
                  f"{r['fee_pct_of_start']:>7.2f}{r['idle_cash_pct']:>7.1f}")

    (out / f"sim_{stamp}.json").write_text(json.dumps(payload, indent=2))
    print(f"\n  wrote {out}/sim_{stamp}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
