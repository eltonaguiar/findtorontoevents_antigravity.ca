#!/usr/bin/env python3
"""Measure ETF execution cost from daily OHLC — replace an assumed number.

WHY THIS FILE EXISTS (todo 2/3, highest-priority item)
------------------------------------------------------
Every EQUITY/ETF conclusion in this programme rests on `VENUE_COST_BP = {"SPY":
(4.0, -1.0), ...}` — 4 bp per side, i.e. 8 bp round trip. That number was
ASSUMED, never measured. It is the single most load-bearing assumption left in the
work, because the breakout family's entire verdict turns on it:

    at 4 bp/side : pre-2010 positive in 7/7 markets, 4 individually significant
    at 10 bp/side: positive in 2/7, nothing significant

The family passes or fails depending on a cost we never measured. If true ETF
cost is ~2 bp round trip rather than 8, the family's numbers were computed with 4x
too much cost and the conclusion is wrong in the pessimistic direction.

METHOD — two independent estimators, because one estimator certifying itself is
not evidence
  Corwin & Schultz (2012): from consecutive daily high/low pairs. High-low ranges
      embed the spread because a transaction at the bid or ask sets the extreme.
  Roll (1984): from the first-order autocovariance of close-to-close returns. Bid-
      ask bounce induces negative serial covariance.
They use disjoint information (ranges vs return autocovariance), so agreement in
magnitude is real corroboration and disagreement is a warning.

WHAT THIS MEASURES AND WHAT IT DOES NOT
  It estimates the EFFECTIVE spread, which includes adverse selection. That is the
  correct quantity for a taker crossing the book. It is NOT commission (assume $0
  at a modern retail broker, which is the case the breakout family needs).
  It cannot see: market impact at size (todo 4), maker rebates (todo 5),
  the fill convention (todo 7), or borrow/financing. Those are separate items and
  this file must not be cited as if it covered them.

KNOWN BIASES, STATED UP FRONT RATHER THAN DISCOVERED LATER
  - CS is biased UPWARD when volatility is high or when the estimator's no-gap
    assumption fails; it also produces negatives, which are floored at zero.
  - Both estimators are biased UPWARD for low-volatility instruments (bonds), where
    the price range is dominated by noise rather than by spread.
  - Both are DAILY. Intraday spreads are tighter than this in liquid names and much
    wider at the open/close. A daily estimate is a coarse upper-ish bound.
  So if this file says SPY costs 3 bp round trip, the honest reading is "the assumed
  8 bp was too pessimistic", not "SPY costs exactly 3 bp".

Usage: python3 tools/etf_spread_estimate.py [--years 5]
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "etf_spread" / "etf_spread_estimate.json"

# Tickers actually used in this programme's backtests, with the assumption each
# was previously carrying (bp per side, from VENUE_COST_BP).
TICKERS = {
    "SPY": 4.0, "QQQ": 4.0, "IWM": 4.0, "GLD": 4.0,
    "TLT": 4.0, "AGG": 4.0, "DBC": 6.0,
}

SQRT2 = math.sqrt(2.0)
DEN = 3.0 - 2.0 * SQRT2


def corwin_schultz(h: list[float], l: list[float]) -> tuple[float, int]:
    """Mean/median CS proportional spread (as a fraction). Returns (median, n)."""
    vals = []
    for i in range(len(h) - 1):
        h1, l1, h2, l2 = h[i], l[i], h[i + 1], l[i + 1]
        if min(h1, l1, h2, l2) <= 0:
            continue
        beta = math.log(h1 / l1) ** 2 + math.log(h2 / l2) ** 2
        if beta <= 0:
            continue
        gamma = math.log(max(h1, h2) / min(l1, l2)) ** 2
        alpha = (math.sqrt(2 * beta) - math.sqrt(beta)) / DEN - math.sqrt(
            max(gamma, 0.0) / DEN)
        if alpha <= 0:
            vals.append(0.0)      # CS floor: negative alpha => zero spread
            continue
        vals.append(2 * (math.exp(alpha) - 1) / (1 + math.exp(alpha)))
    if not vals:
        return float("nan"), 0
    vals.sort()
    return vals[len(vals) // 2], len(vals)


def roll_spread(c: list[float]) -> float:
    """Roll (1984) proportional spread from lag-1 autocovariance of log returns."""
    r = [math.log(c[i] / c[i - 1]) for i in range(1, len(c))
         if c[i - 1] > 0 and c[i] > 0]
    if len(r) < 30:
        return float("nan")
    m = sum(r) / len(r)
    d = [x - m for x in r]
    cov = sum(d[i] * d[i - 1] for i in range(1, len(d))) / (len(d) - 1)
    return 2 * math.sqrt(-cov) if cov < 0 else 0.0


def acf1(c: list[float]) -> float:
    """Lag-1 autocorrelation of log returns — the assumption test for Roll.

    Roll (1984) decomposes return autocovariance into bid-ask bounce and assumes
    nothing else creates it. For an index ETF, daily returns carry genuine
    microstructure reversal/momentum, so this is violated. Measuring the
    autocorrelation lets us REFUSE the estimate instead of publishing it.
    """
    r = [math.log(c[i] / c[i - 1]) for i in range(1, len(c))
         if c[i - 1] > 0 and c[i] > 0]
    if len(r) < 30:
        return float("nan")
    m = sum(r) / len(r)
    d = [x - m for x in r]
    var = sum(x * x for x in d) / (len(d) - 1)
    cov = sum(d[i] * d[i - 1] for i in range(1, len(d))) / (len(d) - 1)
    return cov / var if var > 0 else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=5)
    args = ap.parse_args()

    try:
        import yfinance as yf
    except ImportError:
        print("yfinance not installed"); return 2

    print(f"=== ETF EFFECTIVE-SPREAD ESTIMATE — {args.years}y daily OHLC ===")
    print("    CS = Corwin-Schultz (high/low); Roll = return autocovariance")
    print("    Reported as ROUND TRIP bp (a taker crossing pays the full spread once;\n"
          "    entering AND exiting pays it twice, so round trip = 2 x spread).\n")
    hdr = (f"{'tkr':<5} {'n':>5} {'CS1x':>7} {'Roll1x':>7} {'ACF1':>7} | "
           f"{'RT measured':>11}  verdict")
    print(hdr)
    print("-" * len(hdr))

    rows, failures = [], []
    for tkr, assumed_side in TICKERS.items():
        try:
            df = yf.download(tkr, period=f"{args.years}y", interval="1d",
                             progress=False, auto_adjust=False, threads=False)
            if df is None or len(df) < 100:
                failures.append({"ticker": tkr, "why": "insufficient history"})
                print(f"{tkr:<5}  no data")
                continue
            if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
                df.columns = df.columns.get_level_values(0)
            hi = [float(x) for x in df["High"].dropna().tolist()]
            lo = [float(x) for x in df["Low"].dropna().tolist()]
            cl = [float(x) for x in df["Close"].dropna().tolist()]

            cs, n = corwin_schultz(hi, lo)
            rl = roll_spread(cl)
            a1 = acf1(cl)
            # median daily high-low range, as a fraction of price
            rng = sorted(math.log(h / l) for h, l in zip(hi, lo) if h > 0 and l > 0)
            med_range = rng[len(rng) // 2] if rng else float("nan")

            # ---- ASSUMPTION VALIDITY GATES -------------------------------------
            # CS floors every negative alpha to zero. All-zero means the spread is
            # not IDENTIFIABLE from daily ranges, not that it is free.
            cs_valid = (cs == cs) and cs > 0
            # Roll's estimator is spread = 2*sqrt(-autocov), which scales with
            # VOLATILITY, not with spread: any volatile instrument yields a large
            # number whether or not it has a wide market. The structural test is
            # that a genuine spread is a SMALL SHARE of the daily range. A 35 bp
            # implied spread against an 80 bp daily range would mean half of every
            # day's range is bid-ask, which no liquid ETF exhibits.
            roll_valid = ((rl == rl) and rl > 0 and med_range == med_range
                          and med_range > 0 and (rl / med_range) < 0.10)
            usable = [x for x in ([cs] if cs_valid else []) +
                      ([rl] if roll_valid else []) if x == x]
            spread_1x = sum(usable) / len(usable) if usable else float("nan")
            rt_meas = spread_1x * 2 * 1e4 if usable else None
            rt_assum = assumed_side * 2
            ratio = (rt_meas / rt_assum) if (rt_meas and rt_assum) else None

            if not usable:
                verdict = "UNMEASURABLE"
            elif rt_meas < rt_assum * 0.75:
                verdict = "ASSUMPTION TOO PESSIMISTIC"
            elif rt_meas > rt_assum * 1.33:
                verdict = "ASSUMPTION TOO OPTIMISTIC"
            else:
                verdict = "assumption holds"
            rts = f"{rt_meas:>11.2f}" if rt_meas else f"{'n/a':>11}"
            print(f"{tkr:<5} {n:>5} {cs*1e4:>7.2f} {rl*1e4:>7.2f} {a1:>7.3f} | "
                  f"{rts}  {verdict}")
            rows.append({"ticker": tkr, "n_pairs": n,
                         "cs_1x_bp": cs * 1e4, "roll_1x_bp": rl * 1e4,
                         "acf1": a1, "median_daily_range_bp": med_range * 1e4,
                         "roll_share_of_range": (rl / med_range) if med_range else None,
                         "cs_valid": bool(cs_valid), "roll_valid": bool(roll_valid),
                         "rt_measured_bp": rt_meas, "rt_assumed_bp": rt_assum,
                         "ratio": ratio, "verdict": verdict})
        except Exception as exc:  # noqa: BLE001
            failures.append({"ticker": tkr, "why": f"{type(exc).__name__}: {exc}"})
            print(f"{tkr:<5}  FAILED {type(exc).__name__}: {exc}")

    if not rows:
        print("\nNo ticker measured. Not a zero result — a failure.")
        return 1

    print(f"\n=== WHAT THIS SETTLES ===")
    measured = [r for r in rows if r["rt_measured_bp"] is not None]
    cs_ok = [r for r in rows if r["cs_valid"]]
    roll_ok = [r for r in rows if r["roll_valid"]]
    print(f"  tickers attempted                  : {len(rows)}")
    print(f"  Corwin-Schultz identifiable        : {len(cs_ok)}/{len(rows)}")
    print(f"  Roll plausible (<10% of range)     : {len(roll_ok)}/{len(rows)}")
    shares = [r["roll_share_of_range"] for r in rows
              if r["roll_share_of_range"] is not None]
    if shares:
        shares.sort()
        print(f"  Roll implied spread as share of daily range: median "
              f"{shares[len(shares)//2]*100:.0f}%  max {shares[-1]*100:.0f}%")
        print(f"     (a real spread is 1-3% of the daily range; 30%+ means the")
        print(f"      estimator is reading volatility, not spread)")
    if not measured:
        print(f"\n  RESULT: MEASUREMENT FAILED. Neither estimator is valid on daily OHLC.")
        print(f"  This is a failure of the METHOD, not a finding about ETF costs, and it")
        print(f"  must NOT be reported as a cost figure.")
        print(f"  CS floors all-negative alpha to zero, so a tight market reads as")
        print(f"  \"unidentifiable\". Roll is spread = 2*sqrt(-autocov), which scales")
        print(f"  with VOLATILITY: a -0.025 daily ACF on a 1% vol instrument")
        print(f"  mechanically becomes a 32 bp \"spread\". Neither can resolve a sub-2bp")
        print(f"  market from daily bars.")
        print(f"\n  WHAT WOULD MEASURE IT: intraday NBBO quotes (TAQ or a vendor feed) or")
        print(f"  live L2. Until that exists, the 4 bp/side figure stays UNMEASURED and")
        print(f"  must be labelled UNMEASURED wherever it gates a verdict -- including in")
        print(f"  the breakout family's 7/7 pre-2010 result.")
    else:
        m = sorted(r["rt_measured_bp"] for r in measured)
        med = m[len(m) // 2]
        print(f"\n  usable median round trip : {med:.2f} bp (n={len(measured)})")
        print(f"  previously assumed       : 8.00 bp (4 bp/side)")
    print(f"\n  CAVEATS: daily data only; CS biased up in high vol and in low-vol")
    print(f"  bonds (TLT/AGG are the weakest rows here); no market impact at size,")
    print(f"  no maker rebates, no commission. See todos 4/5/7 before quoting this")
    print(f"  as an all-in trading cost.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "measured_utc": datetime.now(timezone.utc).isoformat(),
        "years": args.years, "rows": rows, "failures": failures,
        "evidence_class": "EXECUTION (estimated from daily OHLC, not order books)",
        "method": ["corwin_schultz_2012", "roll_1984"],
        "scope_excluded": ["market impact at size", "maker rebates",
                           "commission", "borrow/financing", "intraday variation"],
    }, indent=2))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
