#!/usr/bin/env python3
"""The Canadian answer: TSX-listed ETFs, priced in CAD, no FX conversion needed.

Follows the jurisdiction decision of 2026-11-24 (Canadian resident). The
US-domiciled funds analysed elsewhere are unusable for that holder on PFIC
grounds, so the recommendation has to be tested on funds a Canadian can
actually buy.

Why this is a separate analysis and not a currency conversion
-------------------------------------------------------------
A TSX-listed fund already prices in CAD, so there is no FX term to add - the
currency exposure is embedded in the fund (VFV is unhedged, so it carries USD
exposure inside a CAD-listed wrapper). That is a different exposure from
"USD fund, converted at the broker", and conflating the two would be wrong.

What it measures
----------------
Per TSX-listed ETF: CAGR, volatility, max drawdown, and Sharpe against CASH.TO
as the CAD cash hurdle. Then the CAD-listed cost against the US-listed
equivalent, so the price of the Canadian wrapper is explicit.

Data provenance: fetched on demand and committed with an as-of stamp and a row
count. Paper only. Not investment advice.

    python3 tools/fund_cad_home.py --json reports/fund_cad_home.json
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

START, END = "2021-11-15", "2026-11-15"
ANN = 252

# ticker -> (label, MER%, role, us_listed_alternative, us_mer%)
FUNDS = {
    "VFV.TO":   ("Vanguard S&P 500 (CAD, unhedged)", 0.09, "us_equity", "SPY", 0.0945),
    "ZSP.TO":   ("BMO S&P 500 (CAD, unhedged)", 0.09, "us_equity", "SPY", 0.0945),
    "VUN.TO":   ("Vanguard US Total Market (CAD)", 0.17, "us_total", "VTI", 0.03),
    "XEQT.TO":  ("iShares All-Equity (CAD)", 0.20, "all_equity", None, None),
    "ZAG.TO":   ("BMO Aggregate Bond (CAD)", 0.09, "bond", "BND", 0.03),
    "CASH.TO":  ("Global X High-Interest Savings (CAD)", 0.11, "cash", "SGOV", 0.09),
}
CASH = "CASH.TO"


def fetch():
    import yfinance as yf  # noqa: PLC0415

    out = {}
    for t in FUNDS:
        h = yf.Ticker(t).history(start=START, end=END)
        if not len(h):
            continue
        out[t] = {"dates": [str(i.date()) for i in h.index],
                  "close": [float(v) for v in h["Close"]]}
    return out


def stats(ret, mer_pct):
    n = len(ret)
    if n < 30:
        return None
    mer = mer_pct / 100.0
    nav = 1.0
    for r in ret:
        nav *= 1 + r
    gross = nav ** (ANN / n) - 1
    net = (1 + gross) * (1 - mer) - 1
    vol = st.stdev(ret) * math.sqrt(ANN)
    peak, mdd = 1.0, 0.0
    nav2 = 1.0
    for r in ret:
        nav2 *= 1 + r
        peak = max(peak, nav2)
        mdd = min(mdd, nav2 / peak - 1)
    return {"gross_cagr_pct": round(gross * 100, 3),
            "net_cagr_pct": round(net * 100, 3),
            "vol_pct": round(vol * 100, 3),
            "max_dd_pct": round(mdd * 100, 3),
            "n": n}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)

    raw = fetch()
    if CASH not in raw:
        print("  cash series unavailable; refusing to compute a hurdle")
        return 1

    # align on the cash calendar
    base = raw[CASH]["dates"]
    idx = {d: i for i, d in enumerate(base)}
    rets, rows = {}, {}
    for t, d in raw.items():
        s = d["close"]
        r = [s[i] / s[i - 1] - 1 for i in range(1, len(s))]
        rets[t] = r
        rows[t] = stats(r, FUNDS[t][1])

    cash_net = rows[CASH]["net_cagr_pct"] / 100.0

    print(f"  period {base[0]} .. {base[-1]}   n={len(rets[CASH])}")
    print(f"  CAD cash hurdle (CASH.TO net) = {cash_net*100:.2f}%/yr\n")
    print(f"  {'ticker':9s}{'MER':>7s}{'gross':>9s}{'net':>9s}{'vol':>8s}"
          f"{'Sharpe':>8s}{'MaxDD':>9s}  label")
    payload = {"fetched_at": datetime.now(timezone.utc).isoformat(),
               "period": [base[0], base[-1]], "cash_hurdle_pct": round(cash_net * 100, 3),
               "source": "yfinance (TSX-listed, CAD)", "funds": {}}

    for t, m in rows.items():
        if m is None:
            continue
        sharpe = (round((m["net_cagr_pct"] / 100.0 - cash_net) / (m["vol_pct"] / 100.0), 3)
                  if m["vol_pct"] > 0 else None)
        if t == CASH:
            sharpe = None
        payload["funds"][t] = {**m, "sharpe_vs_cad_cash": sharpe,
                               "label": FUNDS[t][0], "mer_pct": FUNDS[t][1],
                               "role": FUNDS[t][2]}
        print(f"  {t:9s}{FUNDS[t][1]:7.2f}{m['gross_cagr_pct']:9.2f}"
              f"{m['net_cagr_pct']:9.2f}{m['vol_pct']:8.2f}"
              f"{str(sharpe):>8s}{m['max_dd_pct']:9.2f}  {FUNDS[t][0]}")

    # cost of the Canadian wrapper, stated per sleeve
    print("\n  Price of the CAD-listed wrapper (MER, pp/yr):")
    payload["wrapper_cost"] = {}
    for t, (label, mer, role, us, us_mer) in FUNDS.items():
        if not us or t not in payload["funds"]:
            continue
        delta = mer - us_mer
        payload["wrapper_cost"][t] = {"us_listed": us, "cad_mer_pct": mer,
                                      "us_mer_pct": us_mer, "delta_pp": round(delta, 4)}
        print(f"    {t:9s} vs {us:4s}  {mer:.2f}% - {us_mer:.4f}% = {delta:+.4f} pp/yr")

    print("\n  Note: a CAD-listed unhedged fund embeds USD exposure; it is not the")
    print("  same as holding a USD fund and converting at the broker. Neither is")
    print("  modelled as tax-deductible here - see the withholding artifact.")

    if args.json:
        Path(args.json).write_text(json.dumps(payload, indent=2))
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
