"""What does STAYING delta-neutral actually cost? (the number that decides the carry sleeve)

Mercury3's corrected model prices the carry as round-trip / holding days and charges
nothing for staying hedged. My flat model charged 1.0 bp/day and had no mechanism. Both
are guesses; this measures the missing term with LIVE order books and a drift-band
simulation of the actual hedging trades.

The model, stated explicitly so it can be attacked:
  * The book holds spot long and perp short. The funding income is separate (measured
    elsewhere) and is NOT part of this tool.
  * If you size the two legs to equal USD notional at entry and never touch them, the spot
    leg's USD value drifts away from the perp notional as price moves, so the book stops
    being dollar-neutral. The drift is `spot_value/perp_notional - 1`, which for a fixed
    entry is just `price_t/price_0 - 1`.
  * A drift band b re-hedges whenever |drift| > b. Each re-hedge trades roughly b of
    notional on the perp leg. Cost per re-hedge = b x (taker fee + book walk cost).
  * Drag in bp/day = (total traded notional x cost per unit) / days.

What it does NOT include: funding income, margin top-ups (a capital transfer, not a cost),
borrow, or the spot leg's own entry/exit. Those are the other half of the ledger and are
already measured in tools/funding_carry_sign_autocorr.py.

Usage
  python3 tools/venue_rebalance_cost.py --days 365 --notional 100000 \
      --out reports/venue_rebalance_cost_2026-11-22.json

Costs: published VIP0 taker rates by default (spot 10 bp, USDT-M futures 4 bp) because
fetching account-specific fees needs API keys. Override with --spot-fee-bps/--perp-fee-bps.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

COINS = ("BTC", "ETH", "BNB", "SOL", "XRP")
BANDS = (0.02, 0.05, 0.10)


def make_exchange(name: str = "binance"):
    import ccxt  # local import so --help works without the dep
    return getattr(ccxt, name)({"enableRateLimit": True, "timeout": 25000})


def book_cost_bps(ob: dict, side: str, notional_usd: float) -> float | None:
    """Walk the book for `notional_usd` on one side; return cost vs mid in bps.

    Returns None when the visible book cannot fill the size (reported, never guessed).
    """
    levels = ob["asks"] if side == "buy" else ob["bids"]
    if not levels:
        return None
    mid = (ob["bids"][0][0] + ob["asks"][0][0]) / 2.0
    remaining, spent, filled = notional_usd, 0.0, 0.0
    for price, size in levels:
        avail = price * size
        take = min(remaining, avail)
        spent += take
        filled += take / price
        remaining -= take
        if remaining <= 0:
            break
    if remaining > 0:
        return None
    vwap = spent / filled
    bps = (vwap / mid - 1.0) * 1e4
    return bps if side == "buy" else -bps


def drift_stats(closes: list[float], band: float) -> dict:
    """Count re-hedges of a fixed-notional delta-neutral book at a drift band."""
    p0 = closes[0]
    perp_notional = 1.0                     # normalised; USD notional cancels out
    rehedges = 0
    traded = 0.0                            # in units of initial notional
    max_drift = 0.0
    for p in closes[1:]:
        drift = (p / p0) / perp_notional - 1.0
        max_drift = max(max_drift, abs(drift))
        if abs(drift) > band:
            traded += abs(drift)
            perp_notional *= (1.0 + drift)  # re-match the legs
            rehedges += 1
    return {"rehedges": rehedges, "traded_notional_frac": traded, "max_drift": max_drift,
            "bars": len(closes) - 1}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--timeframe", default="1h")
    ap.add_argument("--notional", type=float, default=100_000.0,
                    help="size walked against the live book, per leg, in USD")
    ap.add_argument("--spot-fee-bps", type=float, default=10.0)
    ap.add_argument("--perp-fee-bps", type=float, default=4.0)
    ap.add_argument("--out", default="reports/venue_rebalance_cost_2026-11-22.json")
    args = ap.parse_args()

    ex = make_exchange()
    ex.load_markets()
    per_bar_days = {"1h": 1 / 24, "15m": 1 / 96, "4h": 1 / 6, "1d": 1.0}[args.timeframe]
    limit = min(1000, 500)  # ccxt caps a single call; we page

    out: dict = {
        "generated_by": "tools/venue_rebalance_cost.py",
        "question": "what is the drag of STAYING delta-neutral, measured rather than assumed?",
        "venue": "binance",
        "assumptions": {
            "model": "equal USD notional at entry; re-hedge on |spot/perp-1| > band",
            "spot_fee_bps": args.spot_fee_bps,
            "perp_fee_bps": args.perp_fee_bps,
            "note": "the re-hedge trades the PERP leg only; internal transfers between "
                    "spot and futures wallets are free on one venue",
        },
        "books": {},
        "coins": {},
    }

    # 1) live book cost for the size we would actually trade
    for c in COINS:
        for venue, sym in (("spot", f"{c}/USDT"), ("perp", f"{c}/USDT:USDT")):
            try:
                ob = ex.fetch_order_book(sym, limit=50)
                buy = book_cost_bps(ob, "buy", args.notional)
                sell = book_cost_bps(ob, "sell", args.notional)
                mid = (ob["bids"][0][0] + ob["asks"][0][0]) / 2.0
                out["books"][f"{c}|{venue}"] = {
                    "symbol": sym, "mid": mid,
                    "spread_bps": round((ob["asks"][0][0] / ob["bids"][0][0] - 1) * 1e4, 3),
                    "buy_cost_bps": None if buy is None else round(buy, 3),
                    "sell_cost_bps": None if sell is None else round(sell, 3),
                    "filled_notional": args.notional if buy is not None else None,
                }
            except Exception as e:  # noqa: BLE001
                out["books"][f"{c}|{venue}"] = {"symbol": sym, "error": f"{type(e).__name__}: {e}"[:200]}

    # 2) drift-band simulation on real bars
    for c in COINS:
        sym = f"{c}/USDT"
        try:
            bars = ex.fetch_ohlcv(sym, args.timeframe, limit=limit)
            need = int(args.days / per_bar_days)
            while len(bars) < need:
                # int(): binance rejects a float timestamp with code -1100
                since = int(bars[0][0] - limit * per_bar_days * 86400 * 1000)
                more = ex.fetch_ohlcv(sym, args.timeframe, since=since, limit=limit)
                if not more:
                    break
                bars = more + bars
            closes = [b[4] for b in bars if b[4]]
            closes = closes[-need:] if len(closes) > need else closes
            days = len(closes) * per_bar_days
            row = {"bars": len(closes), "days": round(days, 1),
                   "first": bars[0][0], "last": bars[-1][0], "bands": {}}
            # realised vol for context
            rets = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
            mu = sum(rets) / len(rets)
            sd = math.sqrt(sum((r - mu) ** 2 for r in rets) / max(1, len(rets) - 1))
            row["daily_vol_pct"] = round(sd * math.sqrt(1 / per_bar_days) * 100, 3)
            for band in BANDS:
                st = drift_stats(closes, band)
                trades_per_month = st["rehedges"] / (days / 30.0) if days else 0.0
                cost_per_unit = (args.perp_fee_bps + 1.0) / 1e4   # fee + ~1bp slippage
                drag_bp_day = st["traded_notional_frac"] * cost_per_unit * 1e4 / days if days else 0.0
                row["bands"][f"{band:.2f}"] = {
                    "rehedges": st["rehedges"],
                    "rehedges_per_month": round(trades_per_month, 2),
                    "traded_notional_frac": round(st["traded_notional_frac"], 4),
                    "max_drift_pct": round(st["max_drift"] * 100, 2),
                    "drag_bp_day": round(drag_bp_day, 4),
                }
            out["coins"][c] = row
        except Exception as e:  # noqa: BLE001
            out["coins"][c] = {"error": f"{type(e).__name__}: {e}"[:200]}

    # 3) equal-weight aggregate at each band
    agg = {}
    for band in BANDS:
        vals = [r["bands"][f"{band:.2f}"]["drag_bp_day"] for r in out["coins"].values()
                if isinstance(r, dict) and "bands" in r]
        rpms = [r["bands"][f"{band:.2f}"]["rehedges_per_month"] for r in out["coins"].values()
                if isinstance(r, dict) and "bands" in r]
        if vals:
            agg[f"{band:.2f}"] = {
                "coins": len(vals),
                "drag_bp_day": round(sum(vals) / len(vals), 4),
                "rehedges_per_month": round(sum(rpms) / len(rpms), 2),
                "verdict_vs_mercury3_condition": (
                    "TRIGGERS raise-to-20pct (<=0.5 bp/day)" if sum(vals) / len(vals) <= 0.5
                    else "does NOT trigger" if sum(vals) / len(vals) <= 1.0
                    else "kills the sleeve (>1.0 bp/day)"),
            }
    out["aggregate"] = agg
    out["headline"] = ("NO DATA: no coin produced a drift-band result" if not agg else
                       "measured rehedging drag is small relative to the 1.0 bp/day flat charge"
                       if all(v["drag_bp_day"] < 1.0 for v in agg.values())
                       else "some bands exceed the 1.0 bp/day charge")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")

    print(f"{'coin':6}{'vol%':>7}" + "".join(f"{b*100:>5.0f}% band  " for b in BANDS))
    for c, r in out["coins"].items():
        if "bands" not in r:
            print(f"{c:6} {r.get('error','')[:60]}")
            continue
        cells = "".join(f"{r['bands'][f'{b:.2f}']['drag_bp_day']:>7.3f} bp/d "
                        f"{r['bands'][f'{b:.2f}']['rehedges_per_month']:>5.1f}/mo " for b in BANDS)
        print(f"{c:6}{r['daily_vol_pct']:>7.2f} " + cells)
    print("\naggregate (equal weight):")
    for k, v in agg.items():
        print(f"  band {float(k)*100:.0f}%: {v['drag_bp_day']:.3f} bp/day, "
              f"{v['rehedges_per_month']:.1f} re-hedges/month/coin -> {v['verdict_vs_mercury3_condition']}")
    print(f"\n{out['headline']}\nwrote {args.out}")


if __name__ == "__main__":
    main()
