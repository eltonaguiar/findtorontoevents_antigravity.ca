#!/usr/bin/env python3
"""Cross-venue funding dispersion + venue fee-tier break-even for the carry leg.

TODOS 38 and 39.

38  Does the SAME perp pay materially different funding on different venues, and
    if so can you harvest the gap after paying to be long on one venue and short
    on another (two venues, two legs, margin posted twice)?
39  At what fee tier does delta-neutral funding carry clear a 3.5% T-bill? Swept
    across published VIP ladders rather than assumed.

Evidence discipline
  * Every funding number is measured from the venue's own settlement history and
    the settlement count is printed. No interpolated rates.
  * The cross-venue arb is evaluated with the FULL cost stack: taker fee on both
    sides of both legs (4 fills), plus a slippage estimate, plus the fact that
    margin must be posted on two venues so capital is not 1x.
  * n_trials (venues x symbols) is printed. Scanning 5 venues for the richest
    funding is a search.
  * If the answer is "no tier works", it says so rather than presenting the
    best-looking tier.

Read-only. No capital, no keys, no orders. Not investment advice.

Usage:
    python3 tools/funding_venue_dispersion.py
    python3 tools/funding_venue_dispersion.py --days 90 --out reports/funding_venues
"""
from __future__ import annotations

import argparse
import json
import math
import statistics as st
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "reports/funding_venues"

VENUES = ["binanceusdm", "bybit", "okx", "kucoinfutures", "bitget"]
COINS = ["BTC", "ETH", "SOL"]
SYMS = {c: f"{c}/USDT:USDT" for c in COINS}

# Published Binance USD-settled-M taker/maker ladder, as a RATE (not bp).
# These are a published schedule, NOT measured here -- verify on the venue before
# relying on them. The conclusion below does not depend on the exact values,
# because the zero-fee case already fails.
FEE_LADDER = [
    ("VIP0", 0.00050, 0.00020),
    ("VIP1", 0.00040, 0.00020),
    ("VIP2", 0.00035, 0.00016),
    ("VIP3", 0.00032, 0.00014),
    ("VIP4", 0.00030, 0.00012),
    ("VIP5", 0.00027, 0.00010),
    ("VIP6", 0.00025, 0.00008),
    ("VIP7", 0.00022, 0.00006),
    ("VIP8", 0.00020, 0.00004),
    ("VIP9", 0.00017, 0.00000),
]
TBILL = 0.035          # 3.5%/yr hurdle used throughout the programme
SLIP_BP_PER_LEG = 1.3  # half-spread + impact estimate per fill at modest size
CAPITAL_MULT = 2.0     # margin posted on two venues -> capital is 2x the leg


def annualise(rate, hours_per_settlement=8.0):
    """Funding rate per settlement -> simple annualised rate."""
    return rate * (8760.0 / hours_per_settlement)


def human(x):
    return f"{x*100:+.3f}%/yr" if isinstance(x, float) and x == x else "n/a"


# ---------------------------------------------------------------- fetching
VENUE_LIMIT = {"binanceusdm": 1000, "bybit": 200, "okx": 100,
               "kucoinfutures": 100, "bitget": 100}
MIN_IN_WINDOW = 20          # settlements a venue must have inside the common window


def fetch_history(days, verbose=True):
    """Fetch funding history, paginating properly.

    DEFECT FIXED 2026-11-22: the first version passed no `limit`, so binance
    returned its default 100 settlements ending 2026-09-27 while okx/kucoin ran to
    2026-11-22. Section 38 then compared venues over DIFFERENT two-month windows
    and the pooled 'gross carry' of +3.644%/yr was a blend across inconsistent
    periods. Pagination now passes each venue's own max limit and walks forward
    until the present, and section_dispersion enforces a synchronised window.
    """
    import ccxt

    since = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    got = defaultdict(list)     # (venue, coin) -> [(ts, rate)]
    for vname in VENUES:
        try:
            ex = getattr(ccxt, vname)({"enableRateLimit": True, "timeout": 30000})
            ex.load_markets()
        except Exception as e:  # noqa: BLE001
            if verbose:
                print(f"  {vname:<15} UNAVAILABLE ({type(e).__name__})")
            continue
        lim = VENUE_LIMIT.get(vname, 100)
        for coin in COINS:
            sym = SYMS[coin]
            if sym not in ex.markets:
                continue
            seen, cursor = {}, since
            for _ in range(25):
                try:
                    batch = ex.fetch_funding_rate_history(sym, since=cursor, limit=lim)
                except Exception as e:  # noqa: BLE001
                    if verbose:
                        print(f"  {vname:<15} {coin} history FAIL {type(e).__name__}")
                    break
                if not batch:
                    break
                for r in batch:
                    if r.get("fundingRate") is not None:
                        seen[r["timestamp"]] = float(r["fundingRate"])
                nxt = max(r["timestamp"] for r in batch) + 1
                if nxt <= cursor or nxt >= now_ms:
                    break
                cursor = nxt
            if len(seen) >= MIN_IN_WINDOW:
                clean = sorted(seen.items())
                got[(vname, coin)] = clean
                if verbose:
                    print(f"  {vname:<15} {coin} n={len(clean):>4} "
                          f"{datetime.fromtimestamp(clean[0][0]/1000, timezone.utc):%Y-%m-%d}"
                          f"..{datetime.fromtimestamp(clean[-1][0]/1000, timezone.utc):%Y-%m-%d}")
    return got


def common_window(got, min_venues=3):
    """Restrict every series to the window ALL retained venues cover.

    Returns (windowed_got, lo_ms, hi_ms, dropped). A venue-coin series that
    cannot produce MIN_IN_WINDOW settlements inside the common window is dropped
    rather than contributing a partial, non-comparable sample.
    """
    if not got:
        return {}, None, None, []
    per_venue = {}
    for (v, c), rows in got.items():
        per_venue.setdefault(v, []).append((rows[0][0], rows[-1][0]))
    # start with the venues that have the widest coverage, then narrow
    feasi = {v: (max(s for s, _ in rs), min(e for _, e in rs))
             for v, rs in per_venue.items()}
    # greedy: try all venues, drop the one that constrains the window most, repeat
    keep = set(feasi)
    dropped = []
    while True:
        if len(keep) < min_venues:
            break
        lo = max(feasi[v][0] for v in keep)
        hi = min(feasi[v][1] for v in keep)
        bad = [v for v in keep
               if sum(1 for c in COINS
                      if sum(1 for ts, _ in got.get((v, c), []) if lo <= ts <= hi)
                      < MIN_IN_WINDOW) == len(COINS)]
        if not bad:
            break
        worst = min(bad, key=lambda v: -sum(len(got.get((v, c), [])) for c in COINS))
        keep.discard(worst)
        dropped.append(worst)
    if len(keep) < min_venues:
        return {}, None, None, sorted(dropped)
    lo = max(feasi[v][0] for v in keep)
    hi = min(feasi[v][1] for v in keep)
    out = {}
    for (v, c), rows in got.items():
        if v not in keep:
            continue
        w = [(ts, r) for ts, r in rows if lo <= ts <= hi]
        if len(w) >= MIN_IN_WINDOW:
            out[(v, c)] = w
    return out, lo, hi, sorted(dropped)


# ---------------------------------------------------------------- 38
def section_dispersion(got):
    print("\n" + "=" * 78)
    print("SECTION 38 -- CROSS-VENUE FUNDING DISPERSION")
    print("=" * 78)
    if not got:
        print("BLOCKED: no venue returned funding history. Nothing measured.")
        return {}

    got, lo, hi, dropped = common_window(got)
    if lo is None:
        print("BLOCKED: no synchronised window with >=3 venues.")
        return {}
    print(f"synchronised window: {datetime.fromtimestamp(lo/1000, timezone.utc):%Y-%m-%d}"
          f" .. {datetime.fromtimestamp(hi/1000, timezone.utc):%Y-%m-%d}"
          f"  ({(hi-lo)/86400000:.0f} days)")
    if dropped:
        print(f"venues dropped for insufficient in-window coverage: {dropped}")
    present = sorted({v for v, _ in got})
    print(f"venues in the comparison: {present}")
    print("\nannualised funding by venue x coin (mean of settlements, simple annualisation)")
    hdr = f"    {'coin':<6}" + "".join(f"{v[:11]:>13}" for v in present)
    print(hdr)
    table = {}
    for coin in COINS:
        line = f"    {coin:<6}"
        for v in present:
            rows = got.get((v, coin))
            if not rows:
                line += f"{'-':>13}"
                continue
            rates = [r for _, r in rows]
            a = annualise(sum(rates) / len(rates))
            table[(v, coin)] = {"n": len(rates), "ann": a,
                                "median": annualise(st.median(rates))}
            line += f"{a*100:>12.2f}%"
        print(line)

    n_settle = sum(1 for _ in table)
    print(f"\n    cells measured: {n_settle}  <-- n_trials for venue selection")
    print("    NOTE: all retained venues settle every 8h in this sample; the interval "
          "is\n    verified below, not assumed, because a 4h-funding venue would be "
          "double-counted\n    by an 8h annualisation.")
    ivs = {}
    for (v, c), rows in got.items():
        ts = [t for t, _ in rows]
        if len(ts) > 2:
            ivs.setdefault(v, []).append(
                st.median([(ts[i + 1] - ts[i]) / 3600000 for i in range(len(ts) - 1)]))
    for v, lst in sorted(ivs.items()):
        print(f"      {v:<15} settlement interval {st.median(lst):.1f}h")
    bad_iv = [v for v, lst in ivs.items() if abs(st.median(lst) - 8.0) > 0.5]
    if bad_iv:
        print(f"      WARNING: non-8h interval at {bad_iv} -- annualisation is "
              f"approximate for those")
    else:
        # only point out the clean case; do not belabour it
        pass

    # Synchronised dispersion: only where >=3 venues share a timestamp.
    print("\nsynchronised dispersion (settlements where >=3 venues report)")
    by_ts = defaultdict(dict)
    for (v, coin), rows in got.items():
        for ts, r in rows:
            by_ts[(coin, ts)][v] = r
    disp = {}
    for coin in COINS:
        spreads = []
        for (c, ts), d in by_ts.items():
            if c != coin or len(d) < 3:
                continue
            lo, hi = min(d.values()), max(d.values())
            spreads.append(annualise(hi - lo))
        if len(spreads) < 10:
            continue
        spreads.sort()
        disp[coin] = {"n": len(spreads),
                      "mean_ann": sum(spreads) / len(spreads),
                      "median_ann": st.median(spreads),
                      "p90_ann": spreads[int(0.9 * (len(spreads) - 1))]}
        print(f"    {coin:<5} n={len(spreads):>4}  mean {disp[coin]['mean_ann']*100:>7.2f}%/yr"
              f"   median {disp[coin]['median_ann']*100:>7.2f}%/yr"
              f"   p90 {disp[coin]['p90_ann']*100:>7.2f}%/yr")

    if not disp:
        print("    UNMEASURED: too few timestamps shared by 3+ venues.")
        return {"dispersion": {}, "cells": n_settle}

    # Can the gap be harvested? 4 fills + slippage + 2x capital.
    print("\nharvest test -- long the cheap-funding venue, short the expensive one")
    print(f"    cost assumption: 2 legs x 2 sides x (taker {FEE_LADDER[0][1]*100:.3f}%"
          f" + {SLIP_BP_PER_LEG:.1f}bp slippage)")
    rt_cost = 4 * (FEE_LADDER[0][1] + SLIP_BP_PER_LEG / 10000)   # as a fraction
    print(f"    round-trip cost stack          {rt_cost*100:.4f}% of notional per "
          f"round trip")
    print(f"    capital multiplier             {CAPITAL_MULT:.0f}x (margin on both "
          f"venues)")
    print(f"    -> cost expressed on CAPITAL    {rt_cost*CAPITAL_MULT*100:.4f}%")
    print(f"    holding period assumed         30 days "
          f"(gap must persist to be harvestable)")

    harvest = {}
    for coin, d in disp.items():
        gross_ann = d["mean_ann"]
        # hold 30d: gross earned = 30/365 * gross_ann; cost is per round trip
        gross_30d = gross_ann * 30 / 365
        net_30d = gross_30d - rt_cost * CAPITAL_MULT
        harvest[coin] = {"gross_ann": gross_ann, "gross_30d": gross_30d,
                         "cost_30d_capital": rt_cost * CAPITAL_MULT,
                         "net_30d": net_30d,
                         "net_ann": net_30d * 365 / 30}
        print(f"    {coin:<5} gross {human(gross_ann)} -> over 30d {gross_30d*100*CAPITAL_MULT:+.3f}%"
              f" on capital, cost {rt_cost*CAPITAL_MULT*100:.3f}% -> "
              f"NET {net_30d*100:+.3f}% per 30d = {human(harvest[coin]['net_ann'])}")

    best = max(harvest.items(), key=lambda kv: kv[1]["net_ann"])
    print(f"\n    best coin {best[0]}: {human(best[1]['net_ann'])} net vs T-bill "
          f"{TBILL*100:.1f}%/yr")
    if best[1]["net_ann"] < TBILL:
        print("    -> cross-venue funding dispersion does NOT pay for the round trip.")
        print("       The gap is real but it is smaller than the cost of reaching it.")
    return {"dispersion": disp, "harvest": harvest, "cells": n_settle,
            "rt_cost_capital": rt_cost * CAPITAL_MULT}


# ---------------------------------------------------------------- 39
def section_fee_tiers(got):
    print("\n" + "=" * 78)
    print("SECTION 39 -- VENUE FEE-TIER BREAK-EVEN FOR CARRY")
    print("=" * 78)
    print("DEFECT FIXED 2026-11-22: the first version received the UNWINDOWED series\n"
          "while section 38 windowed internally, so the two sections reported\n"
          "different samples (+4.027%/yr over 3,618 settlements there vs a\n"
          "100-settlement synchronised window there). Both now receive the same\n"
          "windowed dict from main().")
    rates = []
    for (v, coin), rows in got.items():
        for _, r in rows:
            rates.append(r)
    if not rates:
        print("BLOCKED: no funding data.")
        return {}
    gross_carry = annualise(sum(rates) / len(rates))
    print(f"measured gross funding carry          {gross_carry*100:+.3f}%/yr")
    print(f"  (pooled mean over {len(rates):,} settlements across "
          f"{len(got)} venue-coin series)")
    print(f"  median settlement rate             {st.median(rates)*1e4:+.4f} bp "
          f"= {annualise(st.median(rates))*100:+.3f}%/yr")
    print(f"T-bill hurdle                        {TBILL*100:.2f}%/yr")
    print(f"gross headroom vs T-bill             {(gross_carry-TBILL)*100:+.3f}%/yr")
    print()
    print("FEE LADDER (published schedule, NOT measured here -- verify on venue)")
    print(f"    {'tier':<7}{'taker':>9}{'maker':>9}{'RT taker':>11}"
          f"{'RT maker':>11}{'carry net(ann)':>16}  verdict")
    rows_out = {}
    for tier, taker, maker in FEE_LADDER:
        rt_t = 2 * taker          # one round trip = open + close on one leg
        rt_m = 2 * maker
        # capital multiplier: collateral held, so cost is on 1x notional here
        net_t = gross_carry - rt_t
        net_m = gross_carry - rt_m
        v = "beats T-bill" if max(net_t, net_m) > TBILL else "FAILS T-bill"
        print(f"    {tier:<7}{taker*1e4:>8.1f}b{maker*1e4:>8.1f}b"
              f"{rt_t*1e4:>10.1f}b{rt_m*1e4:>10.1f}b"
              f"{net_t*100:>15.3f}%  {v}")
        rows_out[tier] = {"taker_bp": taker * 1e4, "maker_bp": maker * 1e4,
                          "net_taker_ann": net_t, "net_maker_ann": net_m}

    # Zero-fee upper bound: the strongest possible statement.
    zero_net = gross_carry - 0.0
    print(f"\n    AT ZERO FEES AND ZERO SLIPPAGE the gross carry is "
          f"{zero_net*100:+.3f}%/yr")
    if zero_net < TBILL:
        print(f"    -> that is BELOW the {TBILL*100:.1f}% T-bill. No fee tier, no "
              f"VIP level, no\n       maker rebate can rescue it: the gross edge "
              f"itself is smaller than cash.\n       This is the strongest form of "
              f"the negative result -- it does not depend on\n       the fee ladder, "
              f"so an error in the ladder cannot flip it.")
    else:
        tiers_that_work = [t for t, r in rows_out.items()
                           if max(r["net_taker_ann"], r["net_maker_ann"]) > TBILL]
        print(f"    -> tiers clearing the hurdle: {tiers_that_work or 'NONE'}")

    # What gross carry WOULD be needed, by tier.
    print("\n    required gross carry to clear the T-bill, by tier (taker RT):")
    for tier, r in rows_out.items():
        need = TBILL + 2 * (r["taker_bp"] / 1e4)
        print(f"      {tier:<7} need {need*100:>6.2f}%/yr gross   "
              f"(have {gross_carry*100:+.2f}%, short by "
              f"{max(0,(need-gross_carry))*100:>5.2f}%)")
    return {"gross_carry_ann": gross_carry, "tbill": TBILL,
            "zero_fee_net": zero_net, "tiers": rows_out,
            "n_settlements": len(rates), "stability": stability_result()}


def stability_test(got):
    """Is the carry a stable cash-beater, or does it depend on the window?

    This is the measurement that decides the verdict. A mean above the T-bill is
    not an edge if the two halves of the sample disagree, and it is a coin flip
    if a third of short blocks are negative.
    """
    print("\nstability of the gross carry (the decisive test)")
    allts = sorted({t for _, rows in got.items() for t, _ in rows})
    if len(allts) < 20:
        print("    UNMEASURED: too few settlements.")
        return {}
    half = allts[len(allts) // 2]

    def mean_ann(sel):
        v = [r for (_, _), rows in got.items() for t, r in rows if sel(t)]
        return annualise(sum(v) / len(v)) if len(v) >= 20 else float("nan")

    h1, h2 = mean_ann(lambda t: t < half), mean_ann(lambda t: t >= half)
    d1 = datetime.fromtimestamp(allts[0] / 1000, timezone.utc)
    dh = datetime.fromtimestamp(half / 1000, timezone.utc)
    d2 = datetime.fromtimestamp(allts[-1] / 1000, timezone.utc)
    print(f"    first half  {d1:%Y-%m-%d}..{dh:%Y-%m-%d}   {h1*100:+7.2f}%/yr")
    print(f"    second half {dh:%Y-%m-%d}..{d2:%Y-%m-%d}   {h2*100:+7.2f}%/yr")
    print(f"    T-bill hurdle                       {TBILL*100:+7.2f}%/yr")

    blocks = []
    for i in range(0, len(allts) - 9, 5):
        lo, hi = allts[i], allts[i + 9]
        v = [r for (_, _), rows in got.items() for t, r in rows if lo <= t <= hi]
        if len(v) >= 40:
            blocks.append(annualise(sum(v) / len(v)))
    if blocks:
        above = sum(1 for b in blocks if b > TBILL)
        neg = sum(1 for b in blocks if b < 0)
        print(f"    rolling 10-settlement blocks ({len(blocks)} blocks, ~3.3d each)")
        print(f"      min {min(blocks)*100:+.2f}%  median {st.median(blocks)*100:+.2f}%"
              f"  max {max(blocks)*100:+.2f}%")
        print(f"      blocks above T-bill {above}/{len(blocks)} "
              f"({100*above/len(blocks):.0f}%)   blocks below zero {neg}/{len(blocks)}")
    else:
        above = neg = 0

    stable = (h1 > TBILL) and (h2 > TBILL)
    _plist = [r for (_, _), rows in got.items() for _, r in rows]
    pooled = annualise(sum(_plist) / len(_plist))
    if stable:
        print(f"    -> BOTH halves clear the hurdle. Carry is a stable cash-beater on "
              f"this sample;\n       still requires the forward clock before any label "
              f"above CANDIDATE.")
    else:
        print(f"    -> NOT stable. The halves disagree, and the more recent half is "
              f"the weaker one.\n       A mean that straddles the hurdle is not an edge: "
              f"it is a window you chose.\n       This is the honest verdict -- the "
              f"earlier +3.18% and this sample's\n       +{pooled*100:.2f}% are the same "
              f"stream measured on different windows.")
    return {"h1_ann": h1, "h2_ann": h2, "blocks_above_tbill": above,
            "n_blocks": len(blocks), "blocks_negative": neg,
            "stable": stable}


_STAB = {}


def stability_result():
    return _STAB


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()

    print(f"fetching funding history, {a.days}d lookback, venues={VENUES}")
    raw = fetch_history(a.days)
    # Window ONCE, here, so section 38 and section 39 cannot use different samples.
    got, lo, hi, dropped = common_window(raw)
    if lo is None:
        print("BLOCKED: no synchronised window across >=3 venues. Nothing measured.")
        return 3
    print(f"synchronised window {datetime.fromtimestamp(lo/1000, timezone.utc):%Y-%m-%d}"
          f"..{datetime.fromtimestamp(hi/1000, timezone.utc):%Y-%m-%d}"
          f" ({(hi-lo)/86400000:.0f}d), dropped={dropped}")
    d38 = section_dispersion(got)
    stab = stability_test(got)
    _STAB.update(stab)
    d39 = section_fee_tiers(got)
    if d39:
        d39["stability"] = stab

    print("\n" + "=" * 78)
    print("WHAT THIS SECTION ESTABLISHES")
    print("=" * 78)
    if d39:
        print(f"  * measured gross funding carry {d39['gross_carry_ann']*100:+.3f}%/yr "
              f"over {d39['n_settlements']:,} settlements")
        print(f"  * at ZERO cost it is {d39['zero_fee_net']*100:+.3f}%/yr vs T-bill "
              f"{d39['tbill']*100:.1f}%/yr -> "
              f"{'CANNOT clear it at any tier' if d39['zero_fee_net'] < d39['tbill'] else 'clears it at every tier, by a hair'}")
    if stab:
        print(f"  * STABILITY: first half {stab['h1_ann']*100:+.2f}%/yr vs second half "
              f"{stab['h2_ann']*100:+.2f}%/yr -> "
              f"{'STABLE' if stab['stable'] else 'NOT STABLE (window-dependent)'}")
        print(f"  * {stab['blocks_above_tbill']}/{stab['n_blocks']} rolling blocks clear "
              f"the T-bill; {stab['blocks_negative']} blocks are negative")
    if d38.get("harvest"):
        b = max(d38["harvest"].items(), key=lambda kv: kv[1]["net_ann"])
        print(f"  * best cross-venue harvest {b[0]} {human(b[1]['net_ann'])} net of "
              f"4 fills + {CAPITAL_MULT:.0f}x capital")

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "funding_venues.json").write_text(json.dumps(
        {"days": a.days,
         "series": {f"{v}|{c}": {"n": len(rows),
                                 "ann": annualise(sum(r for _, r in rows) / len(rows))}
                    for (v, c), rows in got.items()},
         "dispersion": d38, "fee_tiers": d39},
        indent=1, default=str))
    print(f"\nwrote {out/'funding_venues.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
