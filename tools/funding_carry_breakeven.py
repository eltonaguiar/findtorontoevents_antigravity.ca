"""At what ALL-IN round-trip cost does funding carry stop beating a T-bill?

The carry cell is not "good" or "dead" — it is a function of three measured things and one
number that belongs to the reader:

    net bp/day = forward_honest_funding - (round_trip / holding_days) - rehedge_drag

Forward-honest funding is the SECOND-half mean (the halves decay 46%), because extrapolating
the full-sample mean assumes the decay stopped. Round trip is the reader's execution, not a
market constant. Re-hedging is measured in tools/venue_rebalance_cost.py.

So the useful output is not another verdict, it is the THRESHOLD: the largest round-trip cost
at which the sleeve still beats cash, as a function of holding period. A reader with a maker
book and a 90-day hold can then check their own number against it in one line.

Fee schedules are NOT asserted here. Published VIP tiers change, I have no account on this box
to authenticate against, and quoting a tier from memory is exactly the unsupported-claim
pattern this programme exists to catch. The tool takes costs as inputs and reports a grid.

Usage
  python3 tools/funding_carry_breakeven.py \
      --cache reports/funding_carry/funding_cache.json \
      --out reports/funding_carry/funding_breakeven.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# measured in earlier tools, restated so the ledger is self-contained
FULL_SAMPLE_BP = 1.9252      # gross, whole sample
SECOND_HALF_BP = 1.346       # gross, forward-honest (first half 2.504)
REHEDGE_BP_DAY = 0.072       # 5% drift band, live books + hourly bars
HOLDS = (30, 60, 90, 120, 180, 365)
ROUND_TRIPS = (8.0, 12.0, 20.0, 24.0, 30.0, 42.64, 60.0, 85.3)


def net_bp_day(round_trip_bp: float, hold_days: int, gross_bp: float = SECOND_HALF_BP,
               rehedge: float = REHEDGE_BP_DAY) -> float:
    return gross_bp - round_trip_bp / hold_days - rehedge


def ann_pct(bp_day: float) -> float:
    return bp_day * 365 / 100.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="reports/funding_carry/funding_cache.json")
    ap.add_argument("--tbill-pct", type=float, default=3.5)
    ap.add_argument("--out", default="reports/funding_carry/funding_breakeven.json")
    args = ap.parse_args()

    hurdle_bp_day = args.tbill_pct / 365 * 100.0     # cash hurdle in bp/day

    # threshold: largest round trip that still clears the hurdle at each hold
    thresholds = []
    for h in HOLDS:
        budget = SECOND_HALF_BP - REHEDGE_BP_DAY - hurdle_bp_day   # bp/day available for entry/exit
        max_rt = max(0.0, budget * h)
        thresholds.append({
            "holding_days": h,
            "max_roundtrip_bp_to_beat_cash": round(max_rt, 1),
            "max_per_side_bp": round(max_rt / 2, 1),
            "net_at_measured_42_64bp_pct": round(ann_pct(net_bp_day(42.64, h)), 2),
            "beats_cash_at_42_64bp": net_bp_day(42.64, h) > hurdle_bp_day,
        })

    grid = {}
    for rt in ROUND_TRIPS:
        row = {}
        for h in HOLDS:
            n = net_bp_day(rt, h)
            row[str(h)] = {"net_bp_day": round(n, 4), "ann_pct": round(ann_pct(n), 2),
                           "beats_cash": n > hurdle_bp_day}
        grid[f"{rt:.2f}"] = row

    out = {
        "generated_by": "tools/funding_carry_breakeven.py",
        "question": "which execution costs let the carry sleeve beat a T-bill, and which do not?",
        "inputs": {
            "gross_full_sample_bp_day": FULL_SAMPLE_BP,
            "gross_forward_honest_bp_day": SECOND_HALF_BP,
            "rehedge_bp_day": REHEDGE_BP_DAY,
            "tbill_pct": args.tbill_pct,
            "hurdle_bp_day": round(hurdle_bp_day, 4),
            "roundtrip_measured_bp": 42.64,
            "roundtrip_measured_source": "mercury3 tools/carry_execution_cost.py, $25k/leg, live books",
            "fee_tiers_asserted": False,
            "why_no_tiers": "published VIP schedules change and cannot be authenticated from this "
                            "box; asserting one from memory would be an unsupported claim. The "
                            "threshold is reported instead so a reader can test their own tier.",
        },
        "thresholds": thresholds,
        "grid": grid,
        "headline": (
            "at the measured 42.64 bp retail-taker round trip the sleeve beats cash only on holds "
            "longer than the threshold row where beats_cash first turns true"),
    }

    # a crisp single answer: where does 42.64 bp cross the hurdle
    cross = next((t["holding_days"] for t in thresholds if t["beats_cash_at_42_64bp"]), None)
    out["retail_taker_crossing_days"] = cross

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")

    print(f"hurdle = {args.tbill_pct:.2f}% T-bill = {hurdle_bp_day:.4f} bp/day")
    print(f"forward-honest gross {SECOND_HALF_BP:.3f} - rehedge {REHEDGE_BP_DAY:.3f} "
          f"= {SECOND_HALF_BP - REHEDGE_BP_DAY:.3f} bp/day before entry/exit\n")
    print(f"{'hold':>6}{'max RT bp':>11}{'max/side':>10}{'net@42.64':>11}{'beats cash':>12}")
    for t in thresholds:
        print(f"{t['holding_days']:>6}{t['max_roundtrip_bp_to_beat_cash']:>11.1f}"
              f"{t['max_per_side_bp']:>10.1f}{t['net_at_measured_42_64bp_pct']:>10.2f}%"
              f"{str(t['beats_cash_at_42_64bp']):>12}")
    print(f"\nmeasured retail-taker round trip 42.64 bp beats cash from a {cross}-day hold onward"
          if cross else "\nmeasured retail-taker round trip never beats cash at any hold shown")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
