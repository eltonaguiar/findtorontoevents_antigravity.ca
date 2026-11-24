#!/usr/bin/env python3
"""D6/D7: glide-path table and the risk/return frontier for SPY/BND mixes.

Reuses the tested machinery in tools/fund_deep_dive.py rather than
re-deriving anything: `portfolio()` for a genuine NAV-based rebalancer and
`metrics()`/`add_ratios()` for the ratios.

Deliberately reports GROSS and NET CAGR as separate labelled columns. The
fund report once confused those two fields and produced a false
"non-deterministic CAGRs" bug report, so they are never collapsed here.

Paper only. Not investment advice.

    python3 tools/fund_glide_path.py
    python3 tools/fund_glide_path.py --json /tmp/glide.json
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.fund_deep_dive as fd  # noqa: E402

EQUITY_MIXES = [100, 90, 80, 70, 60, 50, 40]
MER = {"SPY_adj": 0.000945, "BND_adj": 0.0003}
SPREAD_BP = 5.0
REBAL = {"buy & hold": None, "quarterly (63d)": 63}


def build(rebal):
    """One glide path down the equity allocation for a given rebalancing rule."""
    rf = None
    rows = []
    for eq in EQUITY_MIXES:
        w = {"SPY_adj": eq / 100.0, "BND_adj": 1.0 - eq / 100.0}
        mer = w["SPY_adj"] * MER["SPY_adj"] + w["BND_adj"] * MER["BND_adj"]
        path, stats = fd.portfolio(fd.RET, w, rebal=rebal, spread_bp=SPREAD_BP)
        m = fd.metrics(path, mer)          # MER is charged HERE, once
        if rf is None:
            rf = fd.RF
        m = fd.add_ratios(m, rf)
        m.update(stats)
        m["equity_pct"] = eq
        rows.append(m)
    return rows, rf


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", default=None, help="write the result as JSON here")
    args = ap.parse_args(argv)

    dates, ser, ret = fd.load()
    fd.RET = ret
    fd.RF = fd.metrics(ret[fd.CASH_KEY], fd.MER[fd.CASH_KEY])["net_cagr_pct"] / 100.0

    print(f"period {dates[0]} .. {dates[-1]}   n={len(ret[fd.CASH_KEY])} daily returns")
    print(f"cash hurdle R_f = {fd.RF * 100:.2f}%/yr (SGOV net CAGR)")
    print(f"rebalance cost {SPREAD_BP:.0f}bp on the traded fraction\n")

    payload = {"period": [dates[0], dates[-1]], "rf_pct": round(fd.RF * 100, 3),
               "spread_bp": SPREAD_BP, "paths": {}}

    for label, rebal in REBAL.items():
        rows, rf = build(rebal)
        payload["paths"][label] = rows
        print(f"=== {label} (=6)")
        print(f"  {'equity':>7s}{'bond':>6s}{'CAGR':>9s}{'NET':>9s}{'vol':>8s}"
              f"{'Sharpe':>8s}{'MaxDD':>9s}{'turnover':>10s}")
        for m in rows:
            print(f"  {m['equity_pct']:6d}%{100 - m['equity_pct']:5d}%"
                  f"{m['cagr_pct']:9.2f}{m['net_cagr_pct']:9.2f}"
                  f"{m['vol_pct']:8.2f}{m['sharpe']:8.3f}"
                  f"{m['max_dd_pct']:9.2f}{m['turnover']:10.2f}")

        # D7: the two questions people actually ask of a frontier.
        best_sharpe = max(rows, key=lambda m: m["sharpe"] if m["sharpe"] is not None else -9)
        safest = min(rows, key=lambda m: m["vol_pct"])
        print(f"  -> highest Sharpe: {best_sharpe['equity_pct']}/{100 - best_sharpe['equity_pct']}"
              f"  (Sharpe {best_sharpe['sharpe']:.3f}, net {best_sharpe['net_cagr_pct']:.2f}%)")
        print(f"  -> lowest vol:     {safest['equity_pct']}/{100 - safest['equity_pct']}"
              f"  (vol {safest['vol_pct']:.2f}%, net {safest['net_cagr_pct']:.2f}%)\n")

        payload["paths"][label] = {
            "rows": rows,
            "max_sharpe_equity_pct": best_sharpe["equity_pct"],
            "min_vol_equity_pct": safest["equity_pct"],
        }

    # D7 caveat, stated in the output rather than buried: this "frontier" is the
    # SPY/BND line only. It is not the efficient frontier over all assets, and a
    # single 5-year bull-heavy window says nothing about the next one.
    print("Note: this is the SPY/BND line, not the efficient frontier over all")
    print("assets, and it is one 5-year window. A point further left may exist.")

    if args.json:
        Path(args.json).write_text(json.dumps(payload, indent=2))
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
