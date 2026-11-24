#!/usr/bin/env python3
"""What these funds returned to someone who spends in Canadian dollars.

Plan item that was previously marked "unmodelled: currency". It is modelable
with public data, so it is modelled here rather than flagged.

Why it matters: over the same window the fee debate in the report is worth
0.0795pp/yr, while USD/CAD moved from ~1.25 to ~1.43 (~2.5%/yr). The currency
effect is roughly thirty times the effect the report spends most of its length
measuring. For a CAD-based holder the fee comparison is still correct but far
from the largest term.

Method
------
Daily CAD-basis return = (1 + r_usd) * (1 + r_fx) - 1, where r_fx is the change
in USD/CAD (a rising USD/CAD means CAD weakened, which HELPS a CAD holder of USD
assets). MER is charged in USD terms, as in the main tool.

Hedging is shown as an APPROXIMATION only. A hedged share class removes r_fx
and pays the forward points, approximated as the short-rate differential. That
differential is a parameter (-1.0%/yr by default, i.e. USD cash yielding about a
point more than CAD cash), not a measurement, and the output says so.

Paper only. Not investment advice. No FX forecast is implied.

    python3 tools/fund_cad_view.py --json reports/fund_cad_view.json
    python3 tools/fund_cad_view.py --hedge-carry-pct -0.5
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.fund_deep_dive as fd  # noqa: E402

FUNDS = ["SPY_adj", "FXAIX_adj", "VTI_adj", "BND_adj", "SGOV_adj"]


def fetch_usdcad(dates):
    """USD/CAD close per CSV date, forward-filled onto the price calendar."""
    try:
        import yfinance as yf
    except ImportError:
        return None, "yfinance not installed"
    try:
        h = yf.Ticker("CAD=X").history(start=dates[0], end=dates[-1])
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)[:160]
    if not len(h):
        return None, "no CAD=X history returned"

    by_day = {str(ix.date()): float(v) for ix, v in zip(h.index, h["Close"])}
    out, last = [], None
    for d in dates:
        if d in by_day:
            last = by_day[d]
        out.append(last)
    # back-fill any leading gap with the first available observation
    first = next((v for v in out if v is not None), None)
    if first is None:
        return None, "CAD=X did not cover the price calendar"
    return [v if v is not None else first for v in out], None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", default=None, help="write results here")
    ap.add_argument("--hedge-carry-pct", type=float, default=-1.0,
                    help="approx annual cost of hedging USD to CAD (default -1.0)")
    args = ap.parse_args(argv)

    dates, ser, _ = fd.load()
    fx, err = fetch_usdcad(dates)
    if fx is None:
        print(f"  FX UNAVAILABLE: {err}")
        print("  Refusing to emit a CAD view without currency data.")
        return 1

    n = len(dates)
    fx_rets = [fx[i] / fx[i - 1] - 1.0 for i in range(1, n)]
    usd_rets = {c: [ser[c][i] / ser[c][i - 1] - 1.0 for i in range(1, n)] for c in FUNDS}
    cad_rets = {c: [(1 + u) * (1 + f) - 1.0 for u, f in zip(usd_rets[c], fx_rets)]
                for c in FUNDS}

    yrs = len(fx_rets) / fd.ANN
    fx_cagr = (fx[-1] / fx[0]) ** (1 / yrs) - 1.0

    cash_key = fd.CASH_KEY
    rf_cad = fd.metrics(cad_rets[cash_key], fd.MER[cash_key])["net_cagr_pct"] / 100.0

    print(f"period {dates[0]} .. {dates[-1]}   n={len(fx_rets)} daily returns")
    print(f"USD/CAD {fx[0]:.4f} -> {fx[-1]:.4f}   ({fx_cagr*100:+.2f}%/yr)")
    print(f"CAD cash hurdle (SGOV, CAD basis) R_f = {rf_cad*100:.2f}%/yr\n")

    print(f"  {'fund':11s}{'USD CAGR':>10s}{'CAD CAGR':>10s}{'FX effect':>11s}"
          f"{'CAD Sharpe':>12s}{'CAD vol':>9s}{'CAD MaxDD':>11s}")
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "period": [dates[0], dates[-1]],
        "n_days": len(fx_rets),
        "fx_pair": "CAD=X (USD/CAD)",
        "usdcad_first": round(fx[0], 4),
        "usdcad_last": round(fx[-1], 4),
        "fx_cagr_pct": round(fx_cagr * 100, 3),
        "rf_cad_pct": round(rf_cad * 100, 3),
        "hedge_carry_pct_assumed": args.hedge_carry_pct,
        "funds": {},
    }

    for c in FUNDS:
        usd = fd.metrics(usd_rets[c], fd.MER[c])
        cad = fd.add_ratios(fd.metrics(cad_rets[c], fd.MER[c]), rf_cad)
        if c == cash_key:
            cad["sharpe"] = None
            cad["sortino"] = None
            cad["ratio_note"] = "cash hurdle; ratios undefined"
        fx_effect = cad["net_cagr_pct"] - usd["net_cagr_pct"]
        hedge = args.hedge_carry_pct  # approximation, see module docstring
        payload["funds"][c] = {
            "usd_net_cagr_pct": usd["net_cagr_pct"],
            "cad_net_cagr_pct": cad["net_cagr_pct"],
            "fx_effect_pp": round(fx_effect, 3),
            "cad_vol_pct": cad["vol_pct"],
            "cad_sharpe": cad["sharpe"],
            "cad_max_dd_pct": cad["max_dd_pct"],
            "hedged_approx_net_cagr_pct": round(usd["net_cagr_pct"] + hedge, 3),
        }
        print(f"  {c:11s}{usd['net_cagr_pct']:10.2f}{cad['net_cagr_pct']:10.2f}"
              f"{fx_effect:+11.2f}{str(cad['sharpe']):>12s}{cad['vol_pct']:9.2f}"
              f"{cad['max_dd_pct']:11.2f}")

    # the sentence the report actually needs, computed not asserted
    fee_edge = 0.0795
    payload["fee_edge_pp"] = fee_edge
    payload["currency_vs_fee_ratio"] = round(abs(fx_cagr * 100) / fee_edge, 1)
    print(f"\n  FX effect on a USD asset: {fx_cagr*100:+.2f}%/yr")
    print(f"  FXAIX-vs-SPY fee edge   : {fee_edge:.4f}%/yr")
    print(f"  ratio (currency : fee)  : {abs(fx_cagr*100)/fee_edge:.0f}x")
    print("\n  Hedging is shown with an ASSUMED carry of "
          f"{args.hedge_carry_pct:+.1f}%/yr (not measured). Over this window CAD "
          "weakened, so\n  hedging would have cost roughly that plus the FX gain "
          "it removed.")

    if args.json:
        Path(args.json).write_text(json.dumps(payload, indent=2))
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
