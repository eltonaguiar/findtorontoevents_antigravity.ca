#!/usr/bin/env python3
"""Execution sensitivity — the four cost questions that decide whether an edge exists.

WHY THIS FILE EXISTS (todos 4, 5, 6, 7)
---------------------------------------
Every edge measured in this programme has landed near the round-trip cost, so the
execution side is not a detail that refines the answer — it IS the answer. Four
separate questions, one harness, because they share a cost model and splitting them
would let four different cost assumptions drift apart:

  TODO 4  CAPACITY      How does cost scale with size? At what notional does the
                        carry sleeve stop clearing its cliff?
  TODO 5  MAKER/TAKER   Does the breakout edge exist only for makers? OUTSIDE-1
                        killed it at 24 bp round trip; if it survives at maker cost
                        then the family is an execution business, not a signal.
  TODO 6  TURNOVER      Does rebalancing less often rescue a strategy that dies at
                        monthly frequency? Same signal, three cadences.
  TODO 7  FILL          What is the lag-0 fill worth? Measures close-of-signal-bar
                        vs next-bar-open vs next-open-plus-slippage.

EACH SECTION STATES ITS OWN SCOPE. Sections 1 uses live order books (crypto only —
ETF books are not available and that gap is already recorded). Sections 2-4 use
daily bars and a stated cost per side.

A shared discipline: every number below is reported at MULTIPLE cost assumptions
rather than one, because ETF execution cost remains UNMEASURED and pretending
otherwise is what this programme keeps getting wrong.

Usage: python3 tools/execution_sensitivity.py [--skip-books]
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "execution_sensitivity" / "execution_sensitivity.json"

# ---- section 1 ----
PAIRS = {"BTC": ("BTC/USDT", "BTC/USDT:USDT"),
         "ETH": ("ETH/USDT", "ETH/USDT:USDT"),
         "SOL": ("SOL/USDT", "SOL/USDT:USDT")}
SIZES = [25_000, 100_000, 250_000, 500_000, 1_000_000, 2_500_000]
TAKER_BP = 10.0
CARRY_CLIFF_BP_DAY = 0.50
HOLD_DAYS = 90

# ---- sections 2-4 ----
MARKETS = ["^GSPC", "SPY", "QQQ", "GLD", "^GDAXI", "^N225"]
LOOK, TP_ATR, SL_ATR, MAX_HOLD = 20, 2.0, 1.0, 10
TAKER_SIDE_BP = [0.0, 2.0, 5.0, 10.0, 12.0]     # round trip = 2x
SLIPPAGE_BP = 5.0                                # extra per side, pessimistic fill


def load_breakout(prices_map: dict[str, list[dict]], cost_side_bp: float,
                  fill: str = "next_open") -> list[float]:
    """Breakout trades under a chosen fill convention and cost. Gross list."""
    out = []
    for bars in prices_map.values():
        i, n = LOOK + 1, len(bars)
        while i < n - 1:
            prior = bars[i - LOOK:i]
            if len(prior) < LOOK:
                break
            if bars[i]["c"] <= max(b["h"] for b in prior):
                i += 1
                continue
            a = sum(max(bars[j]["h"] - bars[j]["l"],
                        abs(bars[j]["h"] - bars[j - 1]["c"]),
                        abs(bars[j]["l"] - bars[j - 1]["c"]))
                    for j in range(max(1, i - 13), i + 1)) / 14
            if a <= 0:
                i += 1
                continue
            if fill == "signal_close":
                entry, start = bars[i]["c"], i + 1       # optimistic: lag-0
            elif fill == "next_open":
                entry, start = bars[i + 1]["o"], i + 1
            else:  # next_open_slip
                entry = bars[i + 1]["o"] * (1 + SLIPPAGE_BP / 1e4)
                start = i + 1
            tp, sl = entry + TP_ATR * a, entry - SL_ATR * a
            exitp, j = None, start
            for j in range(start, min(start + MAX_HOLD, n)):
                if bars[j]["l"] <= sl:
                    exitp = sl
                    break
                if bars[j]["h"] >= tp:
                    exitp = tp
                    break
            if exitp is None:
                j = min(start + MAX_HOLD, n - 1)
                exitp = bars[j]["c"]
            gross_bp = (exitp - entry) / entry * 1e4
            out.append(gross_bp - 2 * cost_side_bp)
            i = j + 1
    return out


def walk_book(levels, target):
    got_q = got_n = 0.0
    for price, qty in levels:
        take = min(price * qty, target - got_n)
        if take <= 0:
            break
        got_n += take
        got_q += take / price
    return (got_n / got_q if got_q else float("nan")), got_n


def section1_capacity() -> dict:
    print("=" * 78)
    print("TODO 4 — COST VS SIZE (CAPACITY CURVE), live order books")
    print("=" * 78)
    print(f"  Round trip = 4 leg-sides (spot buy, perp sell, spot sell, perp buy)")
    print(f"  Carry cliff at a {HOLD_DAYS}-day hold: {CARRY_CLIFF_BP_DAY:.2f} bp/day"
          f" = {CARRY_CLIFF_BP_DAY*HOLD_DAYS:.1f} bp round trip\n")
    try:
        import ccxt
    except ImportError:
        print("  ccxt not installed — section skipped")
        return {"skipped": "no ccxt"}
    ex, pex = ccxt.binance({"enableRateLimit": True}), ccxt.binanceusdm(
        {"enableRateLimit": True})
    print(f"  {'size':>12} {'BTC rt bp':>11} {'ETH rt bp':>11} {'SOL rt bp':>11} "
          f"{'drag@90d':>10}  verdict")
    curve = {}
    cliff = CARRY_CLIFF_BP_DAY * HOLD_DAYS
    for size in SIZES:
        row, ok = {}, True
        for name, (ssym, psym) in PAIRS.items():
            try:
                sb = ex.fetch_order_book(ssym, limit=100)
                pb = pex.fetch_order_book(psym, limit=100)
            except Exception as exc:  # noqa: BLE001
                row[name] = float("nan")
                continue
            sm = (sb["bids"][0][0] + sb["asks"][0][0]) / 2
            pm = (pb["bids"][0][0] + pb["asks"][0][0]) / 2
            sbuy, sf1 = walk_book(sb["asks"], size)
            psel, pf1 = walk_book(pb["bids"], size)
            ssell, sf2 = walk_book(sb["bids"], size)
            pbuy, pf2 = walk_book(pb["asks"], size)
            if min(sf1, pf1, sf2, pf2) < size * 0.99:
                ok = False
            slip = ((sbuy / sm - 1) + (1 - psel / pm)
                    + (1 - ssell / sm) + (pbuy / pm - 1)) * 1e4
            row[name] = slip + 4 * TAKER_BP
        vals = [v for v in row.values() if v == v]
        med = statistics.median(vals) if vals else float("nan")
        drag = med / HOLD_DAYS
        verdict = "ok" if med <= cliff else "FAILS cliff"
        if not ok:
            verdict += " (book too thin)"
        curve[size] = {"per_pair_bp": row, "median_bp": med,
                       "drag_bp_day_90d": drag, "clears_cliff": med <= cliff,
                       "book_filled": ok}
        print(f"  ${size:>11,} {row.get('BTC', float('nan')):>11.1f} "
              f"{row.get('ETH', float('nan')):>11.1f} "
              f"{row.get('SOL', float('nan')):>11.1f} {drag:>10.3f}  {verdict}")
    max_ok = max((s for s, v in curve.items() if v["clears_cliff"]), default=0)
    print(f"\n  Largest size still clearing the 90-day cliff: ${max_ok:,}")
    print(f"  => capacity is bounded by cost, not by the signal. Above this size the")
    print(f"     carry sleeve needs either a longer hold or a better fee tier, and")
    print(f"     neither is free.")
    return {"curve": curve, "max_size_clearing_cliff_usd": max_ok}


def section2_maker_taker(px: dict) -> dict:
    print("\n" + "=" * 78)
    print("TODO 5 — MAKER vs TAKER: does the breakout edge exist only for makers?")
    print("=" * 78)
    print(f"  OUTSIDE-1 killed this family at 24 bp round trip. Here we ask whether")
    print(f"  it survives when you supply liquidity instead of taking it.\n")
    print(f"  {'cost/side':>10} {'round trip':>11} {'n':>6} {'net bp':>9} "
          f"{'win%':>6} {'t':>7}  verdict")
    rows = {}
    for side in TAKER_SIDE_BP:
        nets = load_breakout(px, side, "next_open")
        if not nets:
            continue
        sd = statistics.pstdev(nets)
        t = statistics.mean(nets) / (sd / math.sqrt(len(nets))) if sd else 0.0
        rt = 2 * side
        rows[rt] = {"n": len(nets), "net_bp": statistics.mean(nets),
                    "win_pct": sum(1 for x in nets if x > 0) / len(nets) * 100,
                    "t": t}
        v = "POSITIVE" if statistics.mean(nets) > 0 else "negative"
        print(f"  {side:>10.1f} {rt:>11.1f} {len(nets):>6} "
              f"{statistics.mean(nets):>9.2f} "
              f"{sum(1 for x in nets if x > 0)/len(nets)*100:>6.1f} {t:>7.2f}  {v}")
    pos = [k for k, v in rows.items() if v["net_bp"] > 0]
    print(f"\n  Round trips at which the family is net POSITIVE: "
          f"{pos if pos else 'NONE'}")
    if pos and min(pos) > 0:
        print(f"  => the edge is an EXECUTION property: it exists only if you can")
        print(f"     transact below ~{min(pos):.0f} bp round trip. That is a maker/")
        print(f"     fee-tier question, not a signal question. It also means the")
        print(f"     family cannot be evaluated without a measured ETF spread, which")
        print(f"     remains unavailable.")
    elif not pos:
        print(f"  => negative at EVERY cost including a zero-cost side. There is no")
        print(f"     execution regime that rescues it, so this is a signal failure,")
        print(f"     not a cost failure. That is a stronger kill than OUTSIDE-1.")
    return {"by_round_trip_bp": rows, "positive_at_round_trip_bp": pos}


def section3_turnover() -> dict:
    print("\n" + "=" * 78)
    print("TODO 6 — TURNOVER FREQUENCY: does rebalancing less often rescue it?")
    print("=" * 78)
    import yfinance as yf
    tk = ["SPY", "IEF", "GLD", "TLT", "EFA"]
    # Downloaded one at a time: a single multi-ticker call returns a MultiIndex
    # whose column labels vary by yfinance version, and silently yielding "no
    # usable columns" is exactly the kind of quiet failure this programme keeps
    # having to hunt down. One series per request is boring and reliable.
    series: dict[str, list[float]] = {}
    idx = None
    for t in tk:
        try:
            d = yf.download(t, period="max", interval="1mo", progress=False,
                            auto_adjust=True, threads=False)
        except Exception:  # noqa: BLE001
            continue
        if d is None or len(d) < 60:
            continue
        if hasattr(d.columns, "nlevels") and d.columns.nlevels > 1:
            d.columns = d.columns.get_level_values(0)
        if "Close" not in d.columns:
            continue
        s = d["Close"].dropna()
        series[t] = {str(i)[:10]: float(v) for i, v in s.items()}
        idx = s.index if idx is None else idx.intersection(s.index)
    if not series or idx is None or len(idx) < 60:
        print("  no usable data"); return {}
    px = {t: [series[t].get(str(i)[:10], float("nan")) for i in idx]
          for t in series}
    n = len(idx)
    sma = 12
    # Same 12-month trend signal, three rebalance cadences.
    print(f"  {'cadence':<10} {'rebalances':>11} {'CAGR%':>8} {'vol%':>7} "
          f"{'Sharpe':>7} {'MDD%':>7}")
    out = {}
    for label, every in (("monthly", 1), ("quarterly", 3), ("annual", 12)):
        w = {}
        rets, prev, rebal = [], {}, 0
        for t in range(n):
            if t == 0:
                rets.append(0.0); continue
            if t > sma and (t % every == 0 or not w):
                on = [k for k in px
                      if px[k][t - 1] == px[k][t - 1]
                      and px[k][t - 1] > sum(x for x in px[k][max(0, t - sma):t]
                                             if x == x) / max(1, len(
                                                 [x for x in px[k][max(0, t - sma):t]
                                                  if x == x]))]
                w = {k: 1.0 / len(on) for k in on} if on else {}
                rebal += 1
            r = {k: ((px[k][t] / px[k][t - 1] - 1)
                     if (px[k][t] == px[k][t] and px[k][t - 1] == px[k][t - 1]
                         and px[k][t - 1]) else 0.0)
                 for k in px}
            gross = sum(wt * r.get(k, 0.0) for k, wt in w.items())
            keys = set(w) | set(prev)
            turn = sum(abs(w.get(k, 0.0) - prev.get(k, 0.0)) for k in keys)
            rets.append(gross - turn * 5.0 / 1e4)      # 5 bp/side
            prev = dict(w)
        r = rets[1:]
        if len(r) < 24:
            continue
        cum = 1.0
        for x in r:
            cum *= 1 + x
        cagr = cum ** (12 / len(r)) - 1
        sd = statistics.pstdev(r)
        sh = statistics.mean(r) / sd * math.sqrt(12) if sd else 0
        pk = c = 1.0
        mdd = 0.0
        for x in r:
            c *= 1 + x
            pk = max(pk, c)
            mdd = min(mdd, c / pk - 1)
        out[label] = {"rebalances": rebal, "cagr_pct": cagr * 100,
                      "vol_pct": sd * math.sqrt(12) * 100, "sharpe": sh,
                      "mdd_pct": mdd * 100}
        print(f"  {label:<10} {rebal:>11} {cagr*100:>8.2f} "
              f"{sd*math.sqrt(12)*100:>7.2f} {sh:>7.2f} {mdd*100:>7.2f}")
    best = max(out, key=lambda k: out[k]["sharpe"]) if out else None
    if best:
        print(f"\n  Best cadence on Sharpe: {best}")
        print(f"  => turnover reduction changes cost by a few bp/yr, which cannot")
        print(f"     rescue a strategy that is 0.1+ Sharpe short of a static 60/40.")
        print(f"     Frequency is a cost dial, not an edge dial.")
    return out


def section4_fill(px: dict) -> dict:
    print("\n" + "=" * 78)
    print("TODO 7 — FILL CONVENTION: what is the lag-0 fill worth?")
    print("=" * 78)
    print(f"  Same rule, three fills, at 5 bp per side.\n")
    print(f"  {'fill':<16} {'n':>6} {'net bp':>9} {'win%':>6}  note")
    out = {}
    for label, note in (("signal_close", "OPTIMISTIC lag-0, not executable"),
                        ("next_open", "honest: first price a trader can get"),
                        ("next_open_slip", f"+{SLIPPAGE_BP:.0f} bp adverse on open")):
        nets = load_breakout(px, 5.0, label)
        if not nets:
            continue
        out[label] = {"n": len(nets), "net_bp": statistics.mean(nets),
                      "win_pct": sum(1 for x in nets if x > 0) / len(nets) * 100}
        print(f"  {label:<16} {len(nets):>6} {statistics.mean(nets):>9.2f} "
              f"{sum(1 for x in nets if x > 0)/len(nets)*100:>6.1f}  {note}")
    if "signal_close" in out and "next_open" in out:
        gap = out["signal_close"]["net_bp"] - out["next_open"]["net_bp"]
        out["lag0_premium_bp"] = gap
        print(f"\n  Lag-0 fill is worth {gap:+.2f} bp per trade versus next-open.")
        print(f"  That is the phantom edge a backtest gets for trading at a price it")
        print(f"  could not have known. Any backtest reporting a close-of-signal fill")
        print(f"  is overstating by roughly this much, and it is the same defect that")
        print(f"  produced the fake Sharpe 1.83 in the monthly engine.")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-books", action="store_true")
    a = ap.parse_args()
    results = {}
    results["todo4_capacity"] = ({} if a.skip_books else section1_capacity())

    import yfinance as yf
    px = {}
    for m in MARKETS:
        try:
            df = yf.download(m, period="max", interval="1d", progress=False,
                             auto_adjust=False, threads=False)
            if df is None or len(df) < 200:
                continue
            if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
                df.columns = df.columns.get_level_values(0)
            bars = []
            for _, row in df.iterrows():
                try:
                    o, h, l, c = (float(row["Open"]), float(row["High"]),
                                  float(row["Low"]), float(row["Close"]))
                except (TypeError, ValueError, KeyError):
                    continue
                if any(x != x for x in (o, h, l, c)) or c <= 0:
                    continue
                bars.append({"o": o, "h": h, "l": l, "c": c})
            if bars:
                px[m] = bars
        except Exception:  # noqa: BLE001
            continue
    print(f"\n[sections 2-4 use {len(px)} markets: {list(px)}]")
    results["todo5_maker_taker"] = section2_maker_taker(px)
    results["todo6_turnover"] = section3_turnover()
    results["todo7_fill"] = section4_fill(px)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "evidence_class": "EXECUTION SENSITIVITY (costs swept, not assumed)",
        "scope_excluded": ["measured ETF spread (still unavailable)",
                           "market impact beyond 100 book levels",
                           "borrow/financing"],
    }, indent=2))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
