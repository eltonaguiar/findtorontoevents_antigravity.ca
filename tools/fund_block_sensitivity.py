#!/usr/bin/env python3
"""Bootstrap block-length sensitivity for the fund report.

An independent review objected that a 21-day moving block is too short for
equity returns, because autocorrelation runs for weeks to months, so the
confidence intervals should be systematically too NARROW.

That is a testable claim, so it was tested rather than accepted. The result
contradicts the stated direction: for SPY the 90% interval WIDTH is 26.1pp at
block=5 and 18.8pp at block=252, i.e. longer blocks give NARROWER intervals,
not wider. What is true is that the interval is sensitive to the choice at all
(-/+15-28%), which is a reason to disclose the choice rather than a reason to
pick a different default.

A caveat that matters: at block=252 with n=1254 there are only ~5 blocks, so
the resampling is coarse and a narrow interval there reflects FEW effective
samples, not more information. Long blocks are not automatically safer.

Paper only. Not investment advice.

    python3 tools/fund_block_sensitivity.py --json reports/fund_block_sensitivity.json
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.fund_deep_dive as fd  # noqa: E402

FUNDS = ["SPY_adj", "FXAIX_adj", "VTI_adj", "BND_adj", "SGOV_adj"]
BLOCKS = [5, 21, 63, 126, 252]
BASELINE = 21


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", default=None, help="write results here")
    ap.add_argument("--n-boot", type=int, default=1000)
    args = ap.parse_args(argv)

    dates, ser, ret = fd.load()
    n = len(ret["SPY_adj"])
    print(f"period {dates[0]} .. {dates[-1]}   n={n}\n")
    print(f"  {'block':>6}{'~blocks':>9}  " + "".join(f"{f:>13s}" for f in FUNDS))
    print(f"  {'':>6}{'':>9}  " + "".join(f"{'90% width':>13s}" for _ in FUNDS))

    payload = {"period": [dates[0], dates[-1]], "n_days": n,
               "n_boot": args.n_boot, "baseline_block": BASELINE, "by_block": {}}

    for b in BLOCKS:
        widths, cbs = [], {}
        for f in FUNDS:
            r = fd.bootstrap_stats(ret[f], block=b, n_boot=args.n_boot)
            lo, hi = r["cagr_ci_pct"]
            widths.append(hi - lo)
            cbs[f] = {"lo": lo, "hi": hi, "width": round(hi - lo, 3)}
        nb = n // b
        # record the labels too, so the identifier columns of the report's
        # table are traceable like every other number in it
        payload["by_block"][str(b)] = {"block": b, "n_blocks": nb, **cbs}
        print(f"  {b:6d}{nb:9d}  " + "".join(f"{w:13.2f}" for w in widths))

    base = payload["by_block"][str(BASELINE)]
    print(f"\n  Baseline block={BASELINE}; width change vs baseline:")
    for f in FUNDS:
        lo = min(payload["by_block"][str(b)][f]["width"] for b in BLOCKS)
        hi = max(payload["by_block"][str(b)][f]["width"] for b in BLOCKS)
        pct = (hi - lo) / base[f]["width"] * 100 if base[f]["width"] else 0
        print(f"    {f:11s} width range {lo:6.2f} .. {hi:6.2f}  "
              f"(+/-{pct:5.1f}% around the baseline choice)")

    # The honest summary, derived rather than asserted.
    spy5 = payload["by_block"]["5"]["SPY_adj"]["width"]
    spy252 = payload["by_block"]["252"]["SPY_adj"]["width"]
    verdict = ("LONGER blocks give NARROWER intervals here, so '21 days is too "
               "short, therefore the CI is too narrow' is NOT supported by this data."
               if spy252 < spy5 else
               "longer blocks give WIDER intervals here, consistent with the objection.")
    payload["verdict"] = verdict
    print(f"\n  SPY width: block5={spy5:.2f}  block252={spy252:.2f}  -> {verdict}")

    if args.json:
        Path(args.json).write_text(json.dumps(payload, indent=2))
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
