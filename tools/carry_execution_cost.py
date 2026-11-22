#!/usr/bin/env python3
"""Measure the ACTUAL round-trip execution cost of a delta-neutral spot+perp pair.

WHY THIS FILE EXISTS
--------------------
H-228 (delta-neutral crypto funding carry) has one number standing between it
and a verdict: the round-trip cost of putting the pair on and taking it off.
Every previous statement of that number in this programme was a GUESS:

  - "2 legs x 2 sides x ~10bp taker = ~40bp round trip"   (peer estimate)
  - CARRY_DRAG_BP_DAY = 0.44 bp/day                        (mine, at a 90-day hold)
  - the drag sweep tested 0 / 0.25 / 0.5 / 1.0 / 1.5 / 2.0 (assumed points)

The published verdict cliff sits between 0.5 and 1.0 bp/day. My chosen 0.44 is
0.0006 bp/day inside the passing region. That is not a result, that is a coin
standing on its edge, and I picked which side it fell on. This script replaces
the guess with a measurement:

  round_trip_bp = sum over the 4 leg-sides of (walked slippage + taker fee)

where walked slippage is computed by actually consuming the live order book to
a target notional, not by assuming half the top-of-book spread. Half-spread is
an OPTIMISTIC floor: it is only correct if you trade smaller than the best bid
or offer. For any real size you cross multiple levels.

WHAT IT DOES NOT MEASURE (stated up front, because this programme keeps being
burned by unstated scope)
  - Funding-rate risk. Measured elsewhere (tools/funding_carry_measure.py).
  - Margin-transfer cost. On a single exchange, spot<->futures internal transfer
    is FREE, which is why the flat-daily-drag model was wrong. Not measurable
    as a market cost because it is zero.
  - Liquidation / tail risk on the perp leg.
  - Borrow availability on the spot leg (there is none: you BUY spot, you do not
    borrow it).
  - Fee tiers above the public taker rate. If you have a VIP tier, substitute
    --taker-fee-bp.
  - Time variation. This is a snapshot of this minute's book. Spreads widen in
    stress, and stress is when you least want to enter. The snapshot is a FLOOR
    on the average cost, not an estimate of it.

Law: publish gross/fees/net together; disclose n; label the evidence class
(EXECUTION here); never present a cost-derived verdict as a signal.

Usage:
  python3 tools/carry_execution_cost.py
  python3 tools/carry_execution_cost.py --notional 50000 --maker-fee-bp 2
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "carry_execution" / "carry_execution_cost.json"

# symbol -> (spot symbol on binance, perp symbol on binanceusdm)
PAIRS = {
    "BTC": ("BTC/USDT", "BTC/USDT:USDT"),
    "ETH": ("ETH/USDT", "ETH/USDT:USDT"),
    "BNB": ("BNB/USDT", "BNB/USDT:USDT"),
    "SOL": ("SOL/USDT", "SOL/USDT:USDT"),
    "XRP": ("XRP/USDT", "XRP/USDT:USDT"),
}

DEPTH_LIMIT = 100  # order-book levels to request per side


def walk_book(levels: list[list[float]], target_notional: float) -> tuple[float, float]:
    """Consume `levels` ([[price, qty], ...]) until `target_notional` is filled.

    Returns (vwap, filled_notional). If the book is too thin to fill the whole
    order we return the VWAP of what we could fill AND the shortfall is visible
    to the caller through filled_notional < target_notional -- we do not
    extrapolate past the last level, because that is exactly the kind of silent
    assumption that produced the 1.479 PF.
    """
    got_qty = 0.0
    got_notional = 0.0
    for price, qty in levels:
        level_notional = price * qty
        take = min(level_notional, target_notional - got_notional)
        if take <= 0:
            break
        got_notional += take
        got_qty += take / price
    if got_qty <= 0:
        return float("nan"), 0.0
    return got_notional / got_qty, got_notional


def mid_of(book: dict) -> float:
    return (book["bids"][0][0] + book["asks"][0][0]) / 2.0


def measure_one(ex, perp_ex, spot_sym: str, perp_sym: str,
                notional: float, taker_bp: float) -> dict:
    """Round trip = open (buy spot, sell perp) then close (sell spot, buy perp)."""
    sb = ex.fetch_order_book(spot_sym, limit=DEPTH_LIMIT)
    pb = perp_ex.fetch_order_book(perp_sym, limit=DEPTH_LIMIT)
    s_mid, p_mid = mid_of(sb), mid_of(pb)

    # --- OPEN: buy spot at the ASK side, sell perp at the BID side
    spot_buy_vwap, spot_buy_filled = walk_book(sb["asks"], notional)
    perp_sell_vwap, perp_sell_filled = walk_book(pb["bids"], notional)
    # --- CLOSE: sell spot at the BID side, buy perp at the ASK side
    spot_sell_vwap, spot_sell_filled = walk_book(sb["bids"], notional)
    perp_buy_vwap, perp_buy_filled = walk_book(pb["asks"], notional)

    min_filled = min(spot_buy_filled, perp_sell_filled,
                     spot_sell_filled, perp_buy_filled)

    # Slippage in bp relative to each venue's own mid, per leg-side.
    slip_spot_buy = (spot_buy_vwap / s_mid - 1) * 1e4
    slip_perp_sell = (1 - perp_sell_vwap / p_mid) * 1e4
    slip_spot_sell = (1 - spot_sell_vwap / s_mid) * 1e4
    slip_perp_buy = (perp_buy_vwap / p_mid - 1) * 1e4
    slippage_total = slip_spot_buy + slip_perp_sell + slip_spot_sell + slip_perp_buy

    fee_total = 4 * taker_bp  # 4 leg-sides, each charged once
    round_trip = slippage_total + fee_total

    return {
        "spot_mid": s_mid, "perp_mid": p_mid,
        "basis_bp": (p_mid / s_mid - 1) * 1e4,
        "notional_requested": notional,
        "notional_filled_min_leg": min_filled,
        "thin_book": bool(min_filled < notional * 0.999),
        "slip_bp": {
            "spot_buy": slip_spot_buy, "perp_sell": slip_perp_sell,
            "spot_sell": slip_spot_sell, "perp_buy": slip_perp_buy,
            "total": slippage_total,
        },
        "fees_bp": fee_total,
        "round_trip_bp": round_trip,
        "spot_spread_bp": (sb["asks"][0][0] / sb["bids"][0][0] - 1) * 1e4,
        "perp_spread_bp": (pb["asks"][0][0] / pb["bids"][0][0] - 1) * 1e4,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--notional", type=float, default=25_000.0,
                    help="USD notional per leg (default 25000)")
    ap.add_argument("--taker-fee-bp", type=float, default=10.0,
                    help="spot+perp taker fee in bp per side (Binance public is "
                         "10bp spot / 5bp futures at base VIP0; the FUTURES leg is "
                         "cheaper, so 10bp for all four is conservative)")
    ap.add_argument("--maker-fee-bp", type=float, default=2.0,
                    help="if you can rest passive on all 4 leg-sides")
    ap.add_argument("--hold-days", type=int, nargs="+",
                    default=[30, 60, 90, 180, 365])
    args = ap.parse_args()

    try:
        import ccxt
    except ImportError:
        print("ccxt not installed: pip install ccxt", file=sys.stderr)
        return 2

    ex = ccxt.binance({"enableRateLimit": True})
    perp_ex = ccxt.binanceusdm({"enableRateLimit": True})

    print(f"=== CARRY EXECUTION COST — live order books, ${args.notional:,.0f}/leg ===")
    print(f"    measured {datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}")
    print(f"    taker fee assumed {args.taker_fee_bp:.0f}bp per leg-side "
          f"-> {4*args.taker_fee_bp:.0f}bp of pure fees per round trip\n")
    hdr = (f"{'pair':<5} {'basis':>7} {'sprdS':>6} {'sprdP':>6} "
           f"{'slip':>7} {'fees':>6} {'ROUND':>7}   filling?")
    print(hdr)
    print("-" * len(hdr))

    rows, failed = [], []
    for name, (s_sym, p_sym) in PAIRS.items():
        try:
            r = measure_one(ex, perp_ex, s_sym, p_sym, args.notional,
                            args.taker_fee_bp)
        except Exception as exc:  # noqa: BLE001 - report, never silently drop a symbol
            failed.append({"pair": name, "error": f"{type(exc).__name__}: {exc}"})
            print(f"{name:<5}  FAILED  {type(exc).__name__}: {exc}")
            continue
        r["pair"] = name
        rows.append(r)
        thin = "THIN" if r["thin_book"] else "ok"
        print(f"{name:<5} {r['basis_bp']:>7.1f} {r['spot_spread_bp']:>6.1f} "
              f"{r['perp_spread_bp']:>6.1f} {r['slip_bp']['total']:>7.1f} "
              f"{r['fees_bp']:>6.0f} {r['round_trip_bp']:>7.1f}   {thin}")
        time.sleep(1.0)

    if not rows:
        print("\nNo pairs measured. Nothing to report. Not a zero result.")
        return 1

    rt = [r["round_trip_bp"] for r in rows]
    med = sorted(rt)[len(rt) // 2]
    worst = max(rt)
    fees = 4 * args.taker_fee_bp
    slip_med = med - fees
    maker_rt = 4 * args.maker_fee_bp

    print(f"\n=== MEASURED ROUND TRIP (n={len(rows)} pairs, this minute) ===")
    print(f"  median                 : {med:7.2f} bp")
    print(f"  worst                  : {worst:7.2f} bp")
    print(f"  of which pure fees     : {fees:7.2f} bp  ({fees/med*100:.0f}% of median)")
    print(f"  of which walked slippage: {slip_med:7.2f} bp")
    print(f"  if fully passive (maker): {maker_rt:7.2f} bp  <- the number that "
          f"would matter, and the one I cannot assume")

    print(f"\n=== CONVERTED TO A HOLDING-PERIOD DRAG (median {med:.2f}bp round trip) ===")
    print(f"  {'hold':>8} {'bp/day':>8} {'drag on 1.9252bp/day gross':>28}  verdict")
    curve = []
    for d in args.hold_days:
        bpday = med / d
        net = 1.9252 - bpday
        # The published cliff: CI-LB turns negative between 0.5 and 1.0 bp/day.
        verdict = "PASS" if bpday < 0.50 else ("BORDERLINE" if bpday < 1.0 else "FAIL")
        curve.append({"hold_days": d, "drag_bp_day": bpday,
                      "net_bp_day": net, "verdict_vs_cliff": verdict})
        print(f"  {d:>6}d {bpday:>8.3f} {net:>26.3f}  {verdict}")

    print(f"\n=== WHAT THIS SETTLES ===")
    ok = [c for c in curve if c["verdict_vs_cliff"] == "PASS"]
    print(f"  holding periods that pass the published cliff: "
          f"{', '.join(str(c['hold_days']) + 'd' for c in ok) if ok else 'NONE'}")
    print(f"  my tracker used 0.44 bp/day == a {med/0.44:.0f}-day hold at the "
          f"measured cost.")
    print(f"  so the 90-day assumption is {'CONSISTENT with' if 80 <= med/0.44 <= 100 else 'NOT consistent with'} "
          f"the measurement.")
    print(f"\n  CAVEAT, and it is the important line: this is ONE snapshot. "
          f"Spreads widen in\n  stress and stress is when you enter. Treat {med:.1f}bp as a "
          f"FLOOR, not a mean.")
    print(f"  A 2x-worse fill ({med*2:.1f}bp) is "
          f"{'still a PASS at 90d' if med*2/90 < 0.5 else 'a FAIL at 90d and every shorter hold'}.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "measured_utc": datetime.now(timezone.utc).isoformat(),
        "notional_per_leg": args.notional,
        "taker_fee_bp_per_leg_side": args.taker_fee_bp,
        "n_pairs": len(rows), "n_failed": len(failed),
        "median_round_trip_bp": med, "worst_round_trip_bp": worst,
        "fee_component_bp": fees, "slippage_component_bp": slip_med,
        "passive_round_trip_bp": maker_rt,
        "drag_curve": curve,
        "pairs": rows, "failed": failed,
        "evidence_class": "EXECUTION (measured cost, not a signal)",
        "scope_excluded": ["funding risk (measured separately)",
                           "margin transfer (zero on one exchange)",
                           "liquidation tail", "fee tiers above public rate",
                           "time variation -- one snapshot"],
    }, indent=2))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
