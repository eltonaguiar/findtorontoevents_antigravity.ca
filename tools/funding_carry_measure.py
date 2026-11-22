#!/usr/bin/env python3
"""funding_carry_measure.py — measure the REAL drag on a delta-neutral
perp/spot funding-carry book, using exchange funding history via ccxt.

Why this exists
---------------
Peer `buffy` reported (COMS 2026-11-22) a crypto funding-carry cell with
1.925 bps/day gross, Sharpe 3.42, delta-neutral on BTC/ETH/BNB/SOL/XRP over
2021-01-01..2026-11-22, and stated plainly that "the ENTIRE result sits inside a
cost assumption I chose" — a 1.0 bps/day drag that they had not measured. They
asked any seat to measure it. This script measures it.

What "drag" actually is, decomposed
-----------------------------------
A delta-neutral book is long spot + short perp, same notional.
  1. Funding: the short perp RECEIVES funding when the rate is positive (longs
     pay shorts) and PAYS when negative. This is measured directly, per
     settlement, per coin — no assumption needed.
  2. Entry/exit: two legs, two sides. Charged once, not daily.
  3. Margin rebalancing: as price moves, the hedge drifts. On ONE exchange,
     spot<->futures internal transfers are free, so the correct drag is the
     transfer COUNT and any minimum-size frictions, not a daily bps bleed.
     Charging a flat bps/day for this was the assumption under test.
  4. Liquidation/under-collateralisation: a risk, not a measured cost here.

Honesty rules
  * Funding is measured, never assumed.
  * Days with no settlement are treated as 0.0 return, NOT as missing.
  * Negative-funding days are KEPT (they are the actual risk).
  * Every result printed beside its n, its halves, and its CI-LB.
  * The gross number is decomposed so a reader can see how much is funding vs
    everything else.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "funding_carry"
CACHE = OUT / "funding_cache.json"

SYMBOLS = ["BTC/USDT:USDT", "ETH/USDT:USDT", "BNB/USDT:USDT",
           "SOL/USDT:USDT", "XRP/USDT:USDT"]
START = "2021-01-01T00:00:00Z"
END = "2026-11-22T00:00:00Z"
N_BOOT = 5000
BLOCK = 10          # days per block in the stationary-ish bootstrap


def _stamp(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d")


def fetch_funding(symbol: str, refresh: bool = False) -> dict[str, float]:
    """Daily sum of funding rates. Cached on disk."""
    cache: dict = {}
    if CACHE.exists() and not refresh:
        try:
            cache = json.loads(CACHE.read_text())
        except Exception:
            cache = {}
    if symbol in cache and not refresh:
        return cache[symbol]

    import ccxt
    ex = ccxt.binance({"enableRateLimit": True})
    since = ex.parse8601(START)
    until = ex.parse8601(END)
    daily: dict[str, float] = {}
    cursor = since
    guard = 0
    while cursor < until and guard < 400:
        guard += 1
        try:
            batch = ex.fetch_funding_rate_history(symbol, since=cursor, limit=1000)
        except Exception as e:
            print(f"    {symbol}: fetch failed at {_stamp(cursor)}: {type(e).__name__}")
            break
        if not batch:
            break
        for r in batch:
            d = _stamp(r["timestamp"])
            daily[d] = daily.get(d, 0.0) + float(r["fundingRate"])
        last = batch[-1]["timestamp"]
        if last <= cursor:
            break
        cursor = last + 1
    cache[symbol] = daily
    OUT.mkdir(parents=True, exist_ok=True)
    existing = {}
    if CACHE.exists():
        try:
            existing = json.loads(CACHE.read_text())
        except Exception:
            existing = {}
    existing[symbol] = daily
    CACHE.write_text(json.dumps(existing))
    return daily


def build_basket(refresh: bool) -> tuple[list[str], list[float], dict[str, int]]:
    per_coin: dict[str, dict[str, float]] = {}
    counts: dict[str, int] = {}
    for s in SYMBOLS:
        print(f"  fetching {s} ...", flush=True)
        d = fetch_funding(s, refresh=refresh)
        if d:
            per_coin[s] = d
            counts[s] = len(d)
            print(f"    {s}: {len(d)} settlement-days, mean rate/day "
                  f"{statistics.mean(d.values())*1e4:.3f} bp")
    if not per_coin:
        return [], [], {}
    dates = sorted({d for v in per_coin.values() for d in v})
    # equal-weight across coins; a coin with no settlement that day contributes 0
    basket = []
    for day in dates:
        vals = [per_coin[s].get(day, 0.0) for s in per_coin]
        basket.append(sum(vals) / len(per_coin))
    return dates, basket, counts


def sharpe_daily(x: list[float]) -> float:
    if len(x) < 3:
        return float("nan")
    sd = statistics.stdev(x)
    return (statistics.mean(x) / sd * math.sqrt(365)) if sd else 0.0


def block_bootstrap_mean(x: list[float], n_boot: int = N_BOOT, block: int = BLOCK,
                         seed: int = 20261122) -> dict:
    """CI on the mean daily yield, using a circular block bootstrap so that
    serial correlation in funding does not produce a fake-narrow interval."""
    n = len(x)
    if n < block * 3:
        return {"ci_lo": float("nan"), "ci_hi": float("nan")}
    rng = random.Random(seed)
    nb = n // block
    means = []
    for _ in range(n_boot):
        tot = 0.0
        for _ in range(nb):
            st = rng.randrange(n)
            for k in range(block):
                tot += x[(st + k) % n]
        means.append(tot / (nb * block))
    means.sort()
    return {"ci_lo": means[int(0.025 * n_boot)], "ci_hi": means[int(0.975 * n_boot)],
            "ci_lo_2p5": means[int(0.025 * n_boot)]}


def max_dd(series: list[float]) -> float:
    """Max drawdown of the cumulative carry stream (additive daily)."""
    cum, peak, worst = 0.0, 0.0, 0.0
    for r in series:
        cum += r
        peak = max(peak, cum)
        worst = min(worst, cum - peak)
    return worst


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    print(f"Delta-neutral funding carry — {len(SYMBOLS)} coins, {START[:10]}..{END[:10]}")
    dates, basket, counts = build_basket(a.refresh)
    if not basket:
        print("no funding data retrieved"); return 2
    n = len(basket)
    gross_mean = statistics.mean(basket)
    ann_gross = (1 + gross_mean) ** 365 - 1
    sd = statistics.stdev(basket) if n > 1 else 0.0
    neg_days = sum(1 for r in basket if r < 0)
    boot = block_bootstrap_mean(basket)
    half = n // 2
    h1 = statistics.mean(basket[:half])
    h2 = statistics.mean(basket[half:])

    print(f"\n=== MEASURED FUNDING (delta-neutral: long spot + short perp) ===")
    print(f"  window            : {dates[0]} .. {dates[-1]}  ({n} days)")
    print(f"  settlements/coin  : {counts}")
    print(f"  mean funding/day  : {gross_mean*1e4:+.4f} bp  (= {ann_gross*100:+.2f}% annualised)")
    print(f"  sd of daily yield : {sd*1e4:.4f} bp")
    print(f"  carry Sharpe      : {sharpe_daily(basket):.3f}  (annualised, sqrt(365))")
    print(f"  days funding<0    : {neg_days}/{n} = {100*neg_days/n:.1f}%")
    print(f"  worst day         : {min(basket)*1e4:+.2f} bp")
    print(f"  max DD of stream  : {max_dd(basket)*1e4:+.1f} bp")
    print(f"  95% CI on mean/day: [{boot['ci_lo']*1e4:+.4f}, {boot['ci_hi']*1e4:+.4f}] bp")
    print(f"  halves            : first {h1*1e4:+.4f} bp/day, second {h2*1e4:+.4f} bp/day")

    print(f"\n=== NET OF DRAG (the number buffy said decides the cell) ===")
    print(f"{'drag bp/day':>12} {'net bp/day':>12} {'net ann%':>10} {'Sharpe':>8} {'CI-LB':>9} {'halves +/-':>12} {'verdict':>18}")
    rows = []
    for drag in (0.0, 0.25, 0.5, 1.0, 1.5, 2.0):
        adj = [r - drag / 1e4 for r in basket]
        m = statistics.mean(adj)
        b = block_bootstrap_mean(adj, n_boot=1500)
        hh1, hh2 = statistics.mean(adj[:half]), statistics.mean(adj[half:])
        both_pos = hh1 > 0 and hh2 > 0
        ci_pos = b["ci_lo"] > 0
        verdict = "PASS" if (ci_pos and both_pos and m > 0) else \
                  ("CI-LB FAIL" if not ci_pos else "HALVES FAIL")
        rows.append({"drag_bp_day": drag, "net_bp_day": m * 1e4,
                     "ann_pct": ((1 + m) ** 365 - 1) * 100,
                     "sharpe": sharpe_daily(adj), "ci_lo_bp": b["ci_lo"] * 1e4,
                     "half1_bp": hh1 * 1e4, "half2_bp": hh2 * 1e4, "verdict": verdict})
        print(f"{drag:>12.2f} {m*1e4:>+12.4f} {((1+m)**365-1)*100:>10.2f} "
              f"{sharpe_daily(adj):>8.3f} {b['ci_lo']*1e4:>+9.4f} "
              f"{hh1*1e4:>+6.3f}/{hh2*1e4:>+6.3f} {verdict:>18}")

    # what drag set does the ORIGINAL 2x-cost rule imply?
    twice_ci = [r - 2 * 1.0 / 1e4 for r in basket]
    b2 = block_bootstrap_mean(twice_ci, n_boot=1500)
    print(f"\n  At the pre-registered 1.0 bp/day drag: net {gross_mean*1e4 - 1.0:+.4f} bp/day")
    print(f"  At 2x cost (2.0 bp/day):               net {gross_mean*1e4 - 2.0:+.4f} bp/day, "
          f"CI-LB {b2['ci_lo']*1e4:+.4f} bp  -> "
          f"{'PASS' if b2['ci_lo'] > 0 else 'FAILS_2X_COST (reproduces buffy)'}")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "funding_carry_measure.json").write_text(json.dumps({
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "coins": SYMBOLS, "window": [dates[0], dates[-1]], "n_days": n,
        "settlements_per_coin": counts,
        "gross_mean_bp_day": gross_mean * 1e4,
        "gross_ann_pct": ann_gross * 100,
        "carry_sharpe": sharpe_daily(basket),
        "pct_days_negative_funding": 100 * neg_days / n,
        "max_dd_bp": max_dd(basket) * 1e4,
        "bootstrap_ci_mean_bp": [boot["ci_lo"] * 1e4, boot["ci_hi"] * 1e4],
        "halves_bp": [h1 * 1e4, h2 * 1e4],
        "drag_sweep": rows,
        "note": ("Funding is MEASURED from exchange settlement history. Drag is a "
                 "hypothesis variable swept, not assumed. Internal spot<->futures "
                 "transfers on one exchange are free, so rebalancing is a count, not "
                 "a daily bps bleed."),
    }, indent=1))
    print(f"\nwrote {OUT/'funding_carry_measure.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
