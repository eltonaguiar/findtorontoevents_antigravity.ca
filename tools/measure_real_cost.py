#!/usr/bin/env python3
"""Measure real all-in transaction cost from LIVE order books (no hardcoded spread).

Every cost number used by this research programme so far has been an assumption
(5bp/side equity, 8bp breakout, 10bp FX, 25bp/side pod slippage). This tool
replaces the assumption with a measurement, wherever a live book is reachable.

What it measures, per symbol and per order size:
  * top book: best bid / best ask / mid
  * half-spread in bp at the top of book: (ask - bid) / 2 / mid * 1e4
  * size-aware execution: walk the ask side to BUY and the bid side to SELL the
    target notional, VWAP each side, then
        round_trip_spread_bp = (vwap_buy - vwap_sell) / mid * 1e4
    This is the honest number for anything above trivial size.
  * book depth within 10bp and 50bp of mid, in notional, for capacity work.

Exchange fees are reported SEPARATELY and then summed with the spread:
  * Binance spot taker 0.10% = 10bp/side (base tier)  -> 20bp round trip
  * KuCoin spot taker  0.10% = 10bp/side (base tier)  -> 20bp round trip
  * Kraken spot taker  0.26% = 26bp/side (base tier)  -> 52bp round trip
  * maker fees are noted per venue; the default assumption is a TAKER, because a
    strategy that needs to get filled pays the spread.
All-in round trip = spread round trip + 2 * taker fee.

Nothing here is a literature value presented as a measurement: if a venue is
unreachable the error is recorded verbatim and the venue is marked BLOCKED.

Usage:
    python3 tools/measure_real_cost.py                       # item 4 (2 symbols)
    python3 tools/measure_real_cost.py --full                # item 5 (10+ symbols)
    python3 tools/measure_real_cost.py --full --samples 5 --out reports/cost_measurement_20261122.json
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SIZES_USD = [1_000, 10_000, 100_000, 1_000_000]

# (exchange id, symbol) -- the primary set is Binance, the rest is venue comparison
ITEM4 = [("binance", "BTC/USDT"), ("binance", "ETH/USDT")]
ITEM5_EXTRA = [("binance", "SOL/USDT"), ("binance", "BNB/USDT"),
               ("binance", "XRP/USDT"), ("binance", "ADA/USDT"),
               ("binance", "DOGE/USDT"), ("binance", "AVAX/USDT"),
               ("kucoin", "BTC/USDT"), ("kucoin", "ETH/USDT"),
               ("kraken", "BTC/USD"), ("kraken", "ETH/USD")]

# Base-tier spot TAKER fees, per side, in bp. Maker fees are informational only.
TAKER_BP = {"binance": 10.0, "binanceus": 10.0, "kucoin": 10.0, "kraken": 26.0}
MAKER_BP = {"binance": 10.0, "binanceus": 10.0, "kucoin": 10.0, "kraken": 16.0}

BOOK_LIMIT = 1000          # levels requested; capped by the venue
# Some venues accept only specific depth values. KuCoin: 20 or 100.
BOOK_LIMIT_BY_VENUE = {"kucoin": 100}


# ---------------------------------------------------------------------------
# Book math
# ---------------------------------------------------------------------------
def walk(levels: list[list[float]], notional_usd: float) -> tuple[float | None, float, int]:
    """Consume `levels` ([price, qty], best first) until notional is filled.

    Returns (vwap, filled_notional, levels_consumed). vwap is None when the book
    cannot fill the order -- the caller must report that as INSUFFICIENT_DEPTH,
    never silently clamp to what was available.
    """
    remaining = notional_usd
    cost = 0.0
    qty_sum = 0.0
    used = 0
    for price, qty in levels:
        if price <= 0 or qty <= 0:
            continue
        level_notional = price * qty
        take = min(remaining, level_notional)
        cost += take
        qty_sum += take / price
        remaining -= take
        used += 1
        if remaining <= 0:
            break
    if remaining > 1e-9 or qty_sum <= 0:
        return None, notional_usd - remaining, used
    return cost / qty_sum, notional_usd, used


def depth_within(levels: list[list[float]], mid: float, band_bp: float) -> float:
    """Notional resting within `band_bp` basis points of mid on one side."""
    if mid <= 0:
        return 0.0
    lo, hi = mid * (1 - band_bp / 1e4), mid * (1 + band_bp / 1e4)
    total = 0.0
    for price, qty in levels:
        if lo <= price <= hi:
            total += price * qty
    return total


def _levels(raw) -> list[list[float]]:
    """Normalise a book side. Kraken returns [price, qty, timestamp]."""
    out = []
    for lv in raw or []:
        try:
            p, q = float(lv[0]), float(lv[1])
        except (TypeError, ValueError, IndexError):
            continue
        if p > 0 and q > 0:
            out.append([p, q])
    return out


def measure_book(book: dict) -> dict:
    bids = _levels(book.get("bids"))
    asks = _levels(book.get("asks"))
    if not bids or not asks:
        raise ValueError("empty order book")
    best_bid, best_ask = bids[0][0], asks[0][0]
    mid = (best_bid + best_ask) / 2
    half_spread_bp = (best_ask - best_bid) / 2 / mid * 1e4

    sizes = {}
    for size in SIZES_USD:
        vwap_buy, filled_buy, lv_buy = walk(asks, size)
        vwap_sell, filled_sell, lv_sell = walk(bids, size)
        if vwap_buy is None or vwap_sell is None:
            sizes[str(size)] = {"status": "INSUFFICIENT_DEPTH",
                                "filled_buy_usd": filled_buy,
                                "filled_sell_usd": filled_sell}
            continue
        eff_half_bp = (vwap_buy - mid) / mid * 1e4          # buy side is the
        # sell side is symmetric by construction of the walk; report both
        eff_half_sell_bp = (mid - vwap_sell) / mid * 1e4
        sizes[str(size)] = {
            "status": "OK",
            "vwap_buy": vwap_buy, "vwap_sell": vwap_sell,
            "effective_half_spread_bp_buy": eff_half_bp,
            "effective_half_spread_bp_sell": eff_half_sell_bp,
            "round_trip_spread_bp": (vwap_buy - vwap_sell) / mid * 1e4,
            "levels_consumed_buy": lv_buy, "levels_consumed_sell": lv_sell,
        }

    return {
        "best_bid": best_bid, "best_ask": best_ask, "mid": mid,
        "top_half_spread_bp": half_spread_bp,
        "top_round_trip_spread_bp": 2 * half_spread_bp,
        "depth_bid_usd_within_10bp": depth_within(bids, mid, 10.0),
        "depth_ask_usd_within_10bp": depth_within(asks, mid, 10.0),
        "depth_bid_usd_within_50bp": depth_within(bids, mid, 50.0),
        "depth_ask_usd_within_50bp": depth_within(asks, mid, 50.0),
        "sizes": sizes,
    }


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------
def make_exchange(ex_id: str):
    import ccxt
    cls = getattr(ccxt, ex_id)
    return cls({"enableRateLimit": True, "timeout": 20000})


def sample_venue(ex_id: str, symbols: list[str], n_samples: int,
                 spacing_s: float, raw_dir: Path) -> dict:
    """Take n_samples snapshots per symbol. Records errors verbatim."""
    out: dict = {"exchange": ex_id, "symbols": {}, "errors": []}
    try:
        ex = make_exchange(ex_id)
        ex.load_markets()
    except Exception as e:                                    # noqa: BLE001
        out["status"] = "BLOCKED"
        out["errors"].append(f"{ex_id}: {type(e).__name__}: {e}")
        return out
    limit = BOOK_LIMIT_BY_VENUE.get(ex_id, BOOK_LIMIT)
    for sym in symbols:
        recs = []
        for k in range(n_samples):
            ts = datetime.now(timezone.utc)
            try:
                book = ex.fetch_order_book(sym, limit=limit)
                (raw_dir / f"{ex_id}_{sym.replace('/', '')}_{ts.strftime('%H%M%S_%f')}.json").write_text(
                    json.dumps({"ts_utc": ts.isoformat(), "exchange": ex_id, "symbol": sym,
                                "bids": (book.get("bids") or [])[:limit],
                                "asks": (book.get("asks") or [])[:limit]}))
                m = measure_book(book)
                m["ts_utc"] = ts.isoformat()
                recs.append(m)
            except Exception as e:                            # noqa: BLE001
                msg = f"{ex_id} {sym}: {type(e).__name__}: {e}"
                out["errors"].append(msg)
                recs.append({"ts_utc": ts.isoformat(), "status": "ERROR", "error": msg})
            if k < n_samples - 1:
                time.sleep(spacing_s)
        ok = [r for r in recs if r.get("status") != "ERROR" and "mid" in r]
        summary = {"n_samples": len(recs), "n_ok": len(ok),
                   "status": "OK" if ok else "BLOCKED"}
        if ok:
            def spread_stats(key):
                v = sorted(r[key] for r in ok)
                return {"min": v[0], "median": v[len(v) // 2], "max": v[-1]}
            summary["top_half_spread_bp"] = spread_stats("top_half_spread_bp")
            summary["top_round_trip_spread_bp"] = spread_stats("top_round_trip_spread_bp")
            summary["mid_last"] = ok[-1]["mid"]
            per_size = {}
            for size in SIZES_USD:
                k = str(size)
                vals = sorted(r["sizes"][k]["round_trip_spread_bp"]
                              for r in ok if r["sizes"].get(k, {}).get("status") == "OK")
                if vals:
                    per_size[k] = {"n": len(vals), "min": vals[0],
                                   "median": vals[len(vals) // 2], "max": vals[-1]}
                else:
                    per_size[k] = {"n": 0, "status": "INSUFFICIENT_DEPTH"}
            summary["round_trip_spread_bp_by_size"] = per_size
            summary["depth_usd_within_10bp"] = {
                "bid_median": sorted(r["depth_bid_usd_within_10bp"] for r in ok)[len(ok) // 2],
                "ask_median": sorted(r["depth_ask_usd_within_10bp"] for r in ok)[len(ok) // 2]}
            summary["depth_usd_within_50bp"] = {
                "bid_median": sorted(r["depth_bid_usd_within_50bp"] for r in ok)[len(ok) // 2],
                "ask_median": sorted(r["depth_ask_usd_within_50bp"] for r in ok)[len(ok) // 2]}
        out["symbols"][sym] = {"summary": summary, "samples": recs}
    return out


def fee_addendum(venue: dict) -> None:
    """Attach spread / fees / all-in per symbol and size (fees are separate)."""
    ex_id = venue["exchange"]
    taker = TAKER_BP.get(ex_id)
    for sym, b in venue["symbols"].items():
        s = b["summary"]
        if s.get("status") != "OK":
            continue
        s["fees_bp_per_side_taker"] = taker
        s["maker_bp_per_side"] = MAKER_BP.get(ex_id)
        s["fees_bp_round_trip_taker"] = 2 * taker if taker is not None else None
        s["all_in_round_trip_bp_top"] = (
            s["top_round_trip_spread_bp"]["median"] + 2 * taker
            if taker is not None else None)
        for size, v in s["round_trip_spread_bp_by_size"].items():
            if v.get("n"):
                v["fees_bp_round_trip"] = 2 * taker if taker is not None else None
                v["all_in_round_trip_bp"] = (v["median"] + 2 * taker
                                            if taker is not None else None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="item 5: 12 symbols, 3 venues")
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--spacing", type=float, default=3.0)
    ap.add_argument("--out", type=str, default="reports/cost_measurement_20261122.json")
    a = ap.parse_args()

    started = datetime.now(timezone.utc)
    pairs = ITEM4 + (ITEM5_EXTRA if a.full else [])
    by_venue: dict[str, list[str]] = {}
    for ex_id, sym in pairs:
        by_venue.setdefault(ex_id, []).append(sym)

    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    raw_dir = ROOT / "reports" / "cost_measurement" / stamp
    raw_dir.mkdir(parents=True, exist_ok=True)

    venues = []
    for ex_id, syms in by_venue.items():
        v = sample_venue(ex_id, syms, a.samples, a.spacing, raw_dir)
        fee_addendum(v)
        venues.append(v)

    report = {
        "generated_utc": started.isoformat(),
        "method": "ccxt fetch_order_book (limit=%d), VWAP walk to target notional; "
                  "fees added separately from the measured spread" % BOOK_LIMIT,
        "ccxt_calls": ["exchange = ccxt.<venue>({'enableRateLimit': True, 'timeout': 20000})",
                       "exchange.load_markets()",
                       "exchange.fetch_order_book('<SYMBOL>/<QUOTE>', limit=%d)" % BOOK_LIMIT],
        "sizes_usd": SIZES_USD,
        "n_samples_per_symbol": a.samples,
        "sample_spacing_s": a.spacing,
        "snapshot_note": "SNAPSHOT observations spaced %.0fs apart, not time-averaged; "
                         "min/median/max are reported rather than a single point." % a.spacing,
        "taker_fee_bp_per_side": TAKER_BP,
        "maker_fee_bp_per_side": MAKER_BP,
        "raw_snapshot_dir": str(raw_dir.relative_to(ROOT)),
        "venues": venues,
        "item": "item5_full_12_symbols" if a.full else "item4_btc_eth",
    }
    # terminal table
    print(f"\n{'venue':<9}{'symbol':<11}{'top half-spread bp (min/med/max)':<36}"
          f"{'all-in RT bp @ top (spread+fees)':<32}")
    print("-" * 88)
    for v in venues:
        for sym, b in v["symbols"].items():
            s = b["summary"]
            if s.get("status") != "OK":
                print(f"{v['exchange']:<9}{sym:<11}BLOCKED")
                continue
            sp = s["top_half_spread_bp"]
            ai = s.get("all_in_round_trip_bp_top")
            print(f"{v['exchange']:<9}{sym:<11}"
                  f"{sp['min']:.3f} / {sp['median']:.3f} / {sp['max']:<12.3f}"
                  f"{(f'{ai:.2f}' if ai is not None else 'n/a'):<32}")
    for v in venues:
        if v.get("errors"):
            print(f"\nERRORS ({v['exchange']}):")
            for e in v["errors"][:6]:
                print("  " + e)

    out = ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1))
    print(f"\nwrote {out}")
    print(f"raw snapshots: {raw_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
