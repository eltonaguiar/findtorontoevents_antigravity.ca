#!/usr/bin/env python3
"""recommended_portfolio_tracker.py — track the recommendation, and score me on it.

This exists because a recommendation without a dated, falsifiable scorecard is an
opinion. It records MY pick, with weights fixed on the inception date, and then
accrues a forward record that anyone can audit.

THE PICK (fixed 2026-11-22, weights below are the published allocation):

  40%  CASH FLOOR   — 3-month T-bill / laddered GIC. Not a cop-out: peer buffy
                      measured SPY losing to cash in 20.6% of rolling 1y windows
                      (p10 -12.0%), 24.1% of 5y, 11.6% of 10y.
  50%  EQUITY CORE  — broad index buy-and-hold, no timing. Beats every overlay I
                      measured on terminal wealth ($286,771 vs $41,072 over
                      2006-2026). Timing bought drawdown, not return.
  10%  CARRY SATELLITE — delta-neutral perp/spot funding carry. The only stream I
                      measured with positive expectancy that is NOT beta: +7.28%/yr,
                      Sharpe 3.423, reproduced independently. Sized small because
                      its verdict sits inside a 0.5-1.0 bp/day drag assumption, it
                      is negative 26.8% of days, and its carry stream drew down
                      -10.5%.

Deliberately excluded, with reasons in the decision doc: intraday anything,
directional crypto, commodity trend (conflict), FX (three desks negative),
futures (unmeasurable), volatility scaling (refuted), the daily-breakout pod
(unreproducible).

WHAT THIS CAN AND CANNOT TELL YOU
  * The historical column is an IN-SAMPLE reconstruction using measured series.
    It is not evidence of future return.
  * The FORWARD column starts at inception and is the actual scorecard.
  * Until there are >=12 forward months, the honest statement is "author's
    allocation, unproven".

Usage:
  python3 tools/recommended_portfolio_tracker.py --init      # set inception
  python3 tools/recommended_portfolio_tracker.py --mark      # append a mark
  python3 tools/recommended_portfolio_tracker.py --report    # scorecard
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "recommended_portfolio"
STATE = OUT / "state.json"
PRICES = ROOT / "portfolios" / "price_cache.json"
FUNDING = ROOT / "reports" / "funding_carry" / "funding_carry_measure.json"

# ---- THE PICK: fixed at inception, never edited after seeing forward data ----
INCEPTION = "2026-11-22"
WEIGHTS = {"cash": 0.40, "equity": 0.50, "carry": 0.10}
CASH_RATE = 0.035          # annual, laddered GIC / T-bill assumption
EQUITY_TICKER = "SPY"
CARRY_ANNUAL = 0.0728      # measured mean funding, gross of drag
CARRY_DRAG_BP_DAY = 0.44   # round-trip/holding-days at a 90-day hold
BENCHMARKS = {"all_cash": {"cash": 1.0, "equity": 0.0, "carry": 0.0},
              "all_equity": {"cash": 0.0, "equity": 1.0, "carry": 0.0}}


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {}


def save_state(s: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s, indent=1))


FUNDING_CACHE = ROOT / "reports" / "funding_carry" / "funding_cache.json"


def real_carry_monthly() -> pd.Series | None:
    """Monthly carry return from the ACTUAL measured funding settlements.

    Modelling carry as a constant (mean minus drag) gives it ZERO variance, which
    mechanically inflates any blended Sharpe. That was the first version of this
    file and it was wrong in precisely the direction this programme keeps
    catching: over-stating. The sleeve is reconstructed from real funding data
    instead, so its measured 26.8% negative-funding days and -10.5% carry-stream
    drawdown are actually in the series.
    """
    if not FUNDING_CACHE.exists():
        return None
    raw = json.loads(FUNDING_CACHE.read_text())
    if not raw:
        return None
    daily = {}
    for sym, d in raw.items():
        for day, rate in d.items():
            daily.setdefault(day, []).append(rate)
    if not daily:
        return None
    s = pd.Series({d: float(np.mean(v)) for d, v in daily.items()})
    s.index = pd.to_datetime(s.index)
    monthly = (1 + s.sort_index()).resample("ME").prod() - 1
    monthly = monthly - CARRY_DRAG_BP_DAY / 1e4 * 30.44   # drag per month
    return monthly.dropna()


def monthly_returns() -> pd.DataFrame:
    """Monthly returns for the sleeves. Carry uses REAL funding data, so the
    common window is limited to the period where funding history exists."""
    px = json.loads(PRICES.read_text())
    spy = pd.Series(px[EQUITY_TICKER]); spy.index = pd.to_datetime(spy.index)
    spy = spy.sort_index().resample("ME").last().dropna()
    eq = spy.pct_change().dropna()
    df = pd.DataFrame({"equity": eq})
    df["cash"] = (1 + CASH_RATE) ** (1 / 12) - 1
    carry = real_carry_monthly()
    if carry is None:
        df["carry"] = (CARRY_ANNUAL / 12) - (CARRY_DRAG_BP_DAY / 1e4 * 30.44)
        df.attrs["carry_mode"] = "approximated_constant"
    else:
        df["carry"] = carry
        df.attrs["carry_mode"] = "real_funding_series"
    return df.dropna()


def metrics(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 3:
        return {"n": len(r)}
    cum = (1 + r).cumprod()
    n = len(r)
    yrs = n / 12
    cagr = cum.iloc[-1] ** (1 / yrs) - 1
    sd = r.std(ddof=1)
    sharpe = (r.mean() / sd * math.sqrt(12)) if sd else 0.0
    mdd = float((cum / cum.cummax() - 1).min())
    return {"n": n, "cagr_pct": cagr * 100, "sharpe": sharpe,
            "mdd_pct": mdd * 100, "terminal_10k": float(10_000 * cum.iloc[-1]),
            "start": r.index[0].strftime("%Y-%m"), "end": r.index[-1].strftime("%Y-%m")}


def blend(df: pd.DataFrame, w: dict) -> pd.Series:
    return sum(df[k] * wt for k, wt in w.items())


def cmd_init() -> int:
    st = {"inception": INCEPTION,
          "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "weights": WEIGHTS, "cash_rate": CASH_RATE,
          "carry_annual_gross": CARRY_ANNUAL, "carry_drag_bp_day": CARRY_DRAG_BP_DAY,
          "excluded": ["intraday", "directional_crypto", "commodity_trend_UNRESOLVED",
                       "forex", "futures_UNMEASURABLE", "vol_scaling_REFUTED",
                       "pod_equity_breakout_UNREPRODUCED"],
          "forward_marks": []}
    save_state(st)
    print(f"inception set: {INCEPTION}")
    print(f"weights: {WEIGHTS}")
    return cmd_report()


def cmd_mark() -> int:
    st = load_state()
    if not st:
        print("run --init first"); return 2
    df = monthly_returns()
    last = df.index[-1]
    if st["forward_marks"] and st["forward_marks"][-1]["month"] == last.strftime("%Y-%m"):
        print(f"{last.strftime('%Y-%m')} already marked — idempotent, nothing to do")
        return 0
    st["forward_marks"].append({
        "month": last.strftime("%Y-%m"),
        "equity_ret_pct": round(float(df["equity"].iloc[-1]) * 100, 4),
        "marked_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    save_state(st)
    print(f"appended forward mark {last.strftime('%Y-%m')} "
          f"({len(st['forward_marks'])} total)")
    return 0


def cmd_report() -> int:
    st = load_state()
    df = monthly_returns()
    mode = df.attrs.get("carry_mode", "unknown")
    pick = blend(df, WEIGHTS)
    print("=== TRACKED PICK — 40% cash / 50% equity / 10% carry ===")
    print(f"  inception {st.get('inception','?')}   weights {st.get('weights', WEIGHTS)}")
    print(f"  carry sleeve source: {mode}")
    if mode != "real_funding_series":
        print("  !! carry is a CONSTANT here => zero variance => blended Sharpe is inflated.")
        print("     Do not quote the Sharpe until the real funding series is present.")
    print()
    print(f"{'portfolio':<26} {'CAGR%':>8} {'Sharpe':>7} {'MDD%':>8} {'$10k->':>12}  window")
    print("-" * 78)
    rows = [("MY PICK", pick)]
    for name, w in BENCHMARKS.items():
        rows.append((name, blend(df, w)))
    for name, r in rows:
        m = metrics(r)
        print(f"{name:<26} {m['cagr_pct']:>8.2f} {m['sharpe']:>7.2f} {m['mdd_pct']:>8.2f} "
              f"{m['terminal_10k']:>12,.0f}  {m['start']}..{m['end']}")
    # sleeve-level disclosure: the carry sleeve is the one that can flatter the blend
    cm = metrics(df["carry"])
    em = metrics(df["equity"])
    print()
    print("  sleeve detail (carry is the one that can flatter a blend):")
    print(f"    carry   CAGR {cm['cagr_pct']:>7.2f}%  Sharpe {cm['sharpe']:>5.2f}  MDD {cm['mdd_pct']:>7.2f}%")
    print(f"    equity  CAGR {em['cagr_pct']:>7.2f}%  Sharpe {em['sharpe']:>5.2f}  MDD {em['mdd_pct']:>7.2f}%")
    print(f"    cash    {CASH_RATE*100:.2f}% flat, zero variance")
    print()
    fm = st.get("forward_marks", [])
    print(f"=== FORWARD SCORECARD (the only part that counts) ===")
    print(f"  forward months recorded : {len(fm)}")
    if fm:
        for x in fm[-6:]:
            print(f"    {x['month']}  equity sleeve {x['equity_ret_pct']:+.2f}%")
    print("  STATUS: UNPROVEN. A backtest is not a record. With "
          f"{len(fm)} forward month(s), this is the author's allocation, nothing more.")
    print()
    print("  Honest caveats on the reconstruction:")
    print(f"   * cash is a flat {CASH_RATE*100:.1f}% assumption, not realised T-bill history")
    print("   * carry uses REAL funding settlements, so its 26.8% negative-funding days")
    print("     and -10.5% carry-stream drawdown ARE in the series — but the window is")
    print("     limited to where funding history exists, so it is shorter than the equity one")
    print("   * the equity sleeve is buy-and-hold SPY, which carries a -50.8% max drawdown")
    print("   * all three sleeves are reconstructed, not traded. The FORWARD scorecard is the record.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--mark", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.init:
        return cmd_init()
    if a.mark:
        return cmd_mark()
    return cmd_report()


if __name__ == "__main__":
    raise SystemExit(main())
