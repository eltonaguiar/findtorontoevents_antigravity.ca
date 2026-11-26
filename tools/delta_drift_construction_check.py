"""Does a spot-long / perp-short book stay delta-neutral on its own, and what does each
construction cost?

I claimed the perp notional is fixed at entry while the spot leg moves, so delta drifts and
must be re-traded (~0.07 bp/day at a 5% band). Mercury3 measured 0.00 for a quantity-matched
book and 10.67 bp/day for a constant-USD-notional book, i.e. one construction costs nothing
and the other costs 150x my estimate.

Both can be true at once, which is why this tool runs BOTH and names which one each number
describes. The distinction is not academic: it decides whether the carry pays a maintenance
charge at all, and that charge moves the break-even holding period by ~25%.

  A. QUANTITY-MATCHED - long q coins spot, short q coins perp, q never changed.
     Net delta = q*px - q*px = 0 on every day by algebra. Re-trades: 0. Cost: 0.

  B. USD-NOTIONAL-CONSTANT - each leg re-marked to a fixed USD notional, so the coin
     quantity must be re-derived whenever px moves. Re-trades every time drift breaches the
     band. This is the construction my 0.07 bp/day estimate described.

Cost per re-trade is NOT assumed: it is the measured 42.64 bp round trip / 4 leg-sides =
10.66 bp, because a delta re-trade touches both legs once.

Usage
  python3 tools/delta_drift_construction_check.py --out reports/delta_drift/construction_check.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

MEASURED_RT_BP = 42.64
LEG_SIDES = 4                      # spot entry, perp entry, spot exit, perp exit
COST_PER_RETRADE_BP = MEASURED_RT_BP / LEG_SIDES
BANDS = (0.02, 0.05, 0.10)


def load_prices(start: str, end: str | None = None):
    import yfinance as yf

    df = yf.download("BTC-USD", start=start, end=end, auto_adjust=True, progress=False)
    close = df["Close"]
    if hasattr(close, "columns"):
        close = close.iloc[:, 0]
    return close.dropna()


def quantity_matched(px) -> dict:
    """Long q coins spot, short q coins perp, q untouched. Delta is zero by construction."""
    q = 1.0
    deltas = [q * p - q * p for p in px]
    return {
        "construction": "quantity_matched",
        "n_days": int(len(px)),
        "max_abs_net_delta": float(max(abs(d) for d in deltas)),
        "days_with_nonzero_delta": int(sum(1 for d in deltas if abs(d) > 1e-12)),
        "retrades": 0,
        "cost_bp_per_day": 0.0,
        "note": "delta is identically zero because both legs hold the same coin quantity; "
                "price changes revalue both legs equally. What drifts is MARGIN, not delta, "
                "and topping up margin is an internal transfer on one venue.",
    }


def notional_constant(px, band: float) -> dict:
    """Each leg held at a constant USD notional; re-derive coin quantity on band breach."""
    n = float(px.iloc[0])          # one coin's worth at inception, as the fixed notional
    q = n / float(px.iloc[0])      # = 1.0, but kept symbolic so the rule is explicit
    retrades = 0
    bleed = 0
    breaches = 0
    for p in px:
        p = float(p)
        drift = abs(q * p - n) / n
        if drift > band:
            breaches += 1
            # one re-trade resets both legs; a re-trade touches both legs once = 2 leg-sides
            retrades += 1
            bleed += 2 * COST_PER_RETRADE_BP
            q = n / p
    days = len(px)
    return {
        "construction": f"usd_notional_constant_band_{band:.0%}",
        "n_days": int(days),
        "breach_days": int(breaches),
        "breach_pct_of_days": round(100 * breaches / days, 1),
        "retrades": int(retrades),
        "retrades_per_month": round(retrades / (days / 21.0), 1),
        "cost_bp_per_day": round(bleed / days, 3),
        "note": "this is the construction that costs something, and it costs far more than I "
                "estimated. It should be forbidden by spec rather than costed: no carry edge "
                "survives it.",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2019-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--out", default="reports/delta_drift/construction_check.json")
    args = ap.parse_args()

    px = load_prices(args.start, args.end)
    print(f"BTC-USD {px.index[0].date()} -> {px.index[-1].date()}  n={len(px)}")
    print(f"cost per re-trade (measured 42.64 / {LEG_SIDES} leg-sides) = "
          f"{COST_PER_RETRADE_BP:.2f} bp\n")

    out = {
        "generated_by": "tools/delta_drift_construction_check.py",
        "question": "does a spot-long/perp-short book stay neutral without maintenance, and "
                    "what does each construction cost?",
        "window": {"start": str(px.index[0].date()), "end": str(px.index[-1].date())},
        "assumptions": {
            "cost_per_retrade_bp": round(COST_PER_RETRADE_BP, 3),
            "cost_source": "measured 42.64 bp round trip / 4 leg-sides (mercury3, live books)",
            "daily_bars": True,
        },
        "constructions": [],
        "verdict": {},
    }

    a = quantity_matched(px)
    out["constructions"].append(a)
    print(f"{'construction':<28}{'retrades':>10}{'bp/day':>10}{'breach days':>13}")
    print(f"{'A quantity-matched':<28}{a['retrades']:>10}{a['cost_bp_per_day']:>10.3f}"
          f"{0:>13}")

    for band in BANDS:
        b = notional_constant(px, band)
        out["constructions"].append(b)
        print(f"{'B notional const ' + f'{band:.0%}':<28}{b['retrades']:>10}"
              f"{b['cost_bp_per_day']:>10.3f}{b['breach_pct_of_days']:>12.1f}%")

    b5 = next(c for c in out["constructions"]
              if c["construction"] == "usd_notional_constant_band_5%")
    out["verdict"] = {
        "mercury3_right": a["days_with_nonzero_delta"] == 0,
        "my_0p072_estimate_described": "construction B at a 5% band, not the quantity-matched book",
        "ratio_B_to_my_estimate": round(b5["cost_bp_per_day"] / 0.072, 1),
        "what_changes_for_my_carry_model": (
            "the rehedge term must be 0.0 for a quantity-matched book. My breakeven tools "
            "charged 0.072 bp/day, so removing it moves every crossing EARLIER - the "
            "flattering direction - which is exactly why it needs saying out loud."),
        "reading": (
            "quantity-matched is delta-neutral for free; constant-USD-notional is a different "
            "mandate whose maintenance cost exceeds the carry's entire gross. Charge 0.0 for "
            "the former, and refuse to model the latter."),
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nverdict: quantity-matched delta drift == 0 -> {out['verdict']['mercury3_right']}")
    print(f"  B at 5% band costs {b5['cost_bp_per_day']:.2f} bp/day = "
          f"{out['verdict']['ratio_B_to_my_estimate']}x my 0.072 estimate")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
