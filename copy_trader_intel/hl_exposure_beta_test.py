#!/usr/bin/env python3
"""
hl_exposure_beta_test.py — H-261: is the H-260 persistence SKILL or MARKET BETA?

Method
------
For each sampled wallet, measure net directional exposure AT THE PRIOR BOUNDARY (t-7d), not now.
Reconstruction uses `startPosition` on each fill, which makes it self-contained: for each coin, take
the last fill at or before t-7d and derive the position after it. That avoids needing full history and
therefore survives the 2,000-fill API cap.

    position_at_t7(coin) = startPosition + (+sz if side == 'B' else -sz)
    net_notional   = | sum_coin pos(coin) * price(coin) |
    gross_notional =   sum_coin | pos(coin) * price(coin) |
    exposure_ratio = net_notional / equity(t-7d)
    prior  = pnl(t-7d)  - pnl(t-30d)
    future = pnl(t)     - pnl(t-7d)

Then the rank-IC is computed WITHIN net-exposure terciles.

    SKILL  => low-exposure tercile keeps rho > 0
    BETA   => rho rises with exposure, or low-exposure rho ~ 0

A positive control with exposure-INDEPENDENT skill must be recovered in EVERY tercile first,
otherwise the harness is BROKEN and no verdict is issued.

Known limitation (must be stated with any result): a position opened before t-30d and untouched since
produces no fills in the window, so it is invisible here and that wallet's exposure is understated.
"""
from __future__ import annotations

import glob
import json
import random
import sys
import time
import urllib.request

import numpy as np

API = "https://api.hyperliquid.xyz/info"
DAY = 86_400_000
RNG = np.random.default_rng(20261124)

# --- H-261 v2 fixes, all pre-registered in the registry kill_reason before this run ---
MIN_EQ = 1_000.0        # fix 1: floor equity at the prior boundary so the ratio is bounded
RATIO_CAP = 50.0        # fix 2: >50x equity is not a perp position (HL max leverage ~50x)
MAX_UNMEASURED = 0.10   # fix 4: fail the run if >10% of wallets have unknown exposure


def post(payload, tries=3):
    for i in range(tries):
        req = urllib.request.Request(API, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            return json.loads(urllib.request.urlopen(req, timeout=25).read())
        except Exception:
            if i == tries - 1:
                return None
            time.sleep(0.5)


def rankdata(x):
    x = np.asarray(x, float)
    n = x.size
    s = np.argsort(x, kind="mergesort")
    inv = np.empty(n, dtype=np.int64)
    inv[s] = np.arange(n)
    xs = x[s]
    obs = np.r_[True, xs[1:] != xs[:-1]]
    dense = obs.cumsum()[inv]
    cnt = np.r_[np.nonzero(obs)[0], n]
    return 0.5 * (cnt[dense] + cnt[dense - 1] + 1)


def spearman(a, b):
    ra, rb = rankdata(a), rankdata(b)
    ra -= ra.mean(); rb -= rb.mean()
    d = np.sqrt((ra * ra).sum() * (rb * rb).sum())
    return float((ra * rb).sum() / d) if d > 0 else float("nan")


def at_or_before(series, ts):
    best = None
    for t, v in series:
        if t <= ts:
            best = float(v)
        else:
            break
    return best


def measure(addr):
    now = int(time.time() * 1000)
    t7, t30 = now - 7 * DAY, now - 30 * DAY

    port = post({"type": "portfolio", "user": addr})
    if not isinstance(port, list):
        return None
    ph = ah = None
    for w, body in port:
        if w == "month":
            ph, ah = body.get("pnlHistory") or [], body.get("accountValueHistory") or []
            break
    if not ph or not ah:
        return None
    p_now, p7, p30 = at_or_before(ph, now), at_or_before(ph, t7), at_or_before(ph, t30)
    eq7 = at_or_before(ah, t7) or at_or_before(ah, p7 and t7 or t7)
    if None in (p_now, p7, p30) or not eq7 or eq7 <= 0:
        return None

    fills = post({"type": "userFillsByTime", "user": addr, "startTime": t30, "endTime": now})
    if not isinstance(fills, list):
        return None

    # position at t7 = position after the last fill at or before t7, per coin.
    # has_pre distinguishes FLAT from UNKNOWN: a wallet with fills at/before t7 has a
    # known position (possibly zero); one with none has an unknown position.
    last = {}
    has_pre = False
    for f in fills:
        try:
            ft = int(f.get("time", 0))
            if ft > t7:
                continue
            has_pre = True
            coin = f.get("coin")
            sz, px, side = float(f["sz"]), float(f["px"]), f.get("side")
            start = float(f.get("startPosition", 0.0))
            pos = start + (sz if side == "B" else -sz)
            if coin not in last or ft >= last[coin][0]:
                last[coin] = (ft, pos, px)
        except (KeyError, TypeError, ValueError):
            continue

    net = 0.0
    gross = 0.0
    for _coin, (_t, pos, px) in last.items():
        notional = pos * px
        net += notional
        gross += abs(notional)

    return dict(addr=addr, equity7=eq7, prior=p7 - p30, future=p_now - p7,
                net_exposure=abs(net) / eq7, gross_exposure=gross / eq7,
                measurable=has_pre, n_coins=len(last), n_fills=len(fills))


def positive_control():
    """Exposure-INDEPENDENT skill must be recovered in every mock tercile."""
    n = 6_000
    exposure = RNG.random(n)
    skilled = RNG.random(n) < 0.10
    prior = RNG.normal(0, 0.10, n)
    future = prior * 0.30 + RNG.normal(0, 0.10, n) + np.where(skilled, 0.03, 0.0)
    rhos = []
    for lo, hi in ((0, 1 / 3), (1 / 3, 2 / 3), (2 / 3, 1.01)):
        m = (exposure >= lo) & (exposure < hi)
        rhos.append(spearman(prior[m], future[m]))
    ok = all(r > 0.05 for r in rhos)
    print(f"POSITIVE CONTROL (exposure-independent skill)  tercile rhos="
          f"{[round(r,4) for r in rhos]} -> {'PASS' if ok else 'FAIL'}")
    return ok


def main():
    n_target = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    print("=" * 76)
    print(f"H-261  skill vs beta: rank-IC within net-exposure terciles  (sample={n_target})")
    print("=" * 76)
    if not positive_control():
        print("HARNESS_BROKEN: positive control not recovered in every tercile. No verdict.")
        return 2

    snap = json.load(open(sorted(glob.glob("reports/hl_leaderboard_snapshot_*.json"))[-1]))
    elig = [r for r in snap["rows"] if r["acct"] >= 10000 and r["wk_vlm"] > 0]
    random.seed(2718)
    samp = random.sample(elig, min(n_target, len(elig)))

    recs, fail = [], 0
    t0 = time.time()
    for i, r in enumerate(samp, 1):
        m = measure(r["addr"])
        if m is None:
            fail += 1
        else:
            recs.append(m)
        if i % 50 == 0:
            print(f"  ..{i}/{len(samp)} ok={len(recs)} fail={fail} {time.time()-t0:.0f}s")
        time.sleep(0.06)

    total = len(recs)
    print(f"\nwallets measured: {total:,} (failed {fail}) in {time.time()-t0:.0f}s")
    if total < 90:
        print("BROKEN: n < 90. No verdict.")
        return 2

    # ---- fix 1: equity floor at the prior boundary, so the ratio is bounded
    floored = [r for r in recs if r["equity7"] >= MIN_EQ]
    # ---- fix 3: UNMEASURED is its own bucket, never pooled into LOW
    meas = [r for r in floored if r["measurable"]]
    unmeas = [r for r in floored if not r["measurable"]]

    # ---- fix 2: refuse physically implausible exposure ratios
    def _plausible(r):
        return r["gross_exposure"] <= RATIO_CAP and r["net_exposure"] <= RATIO_CAP

    plausible = [r for r in meas if _plausible(r)]
    implausible = [r for r in meas if not _plausible(r)]

    print(f"  passed equity floor >= ${MIN_EQ:,.0f}  : {len(floored):,} of {total:,}")
    print(f"  UNMEASURED (no fill at/before t7)   : {len(unmeas):,}")
    print(f"  implausible exposure > {RATIO_CAP:.0f}x equity   : {len(implausible):,}")
    print(f"  usable                              : {len(plausible):,}")

    # ---- fix 4: fail the run if the unmeasured share is too large
    unmeas_share = len(unmeas) / max(len(floored), 1)
    if unmeas_share > MAX_UNMEASURED:
        print(f"\nHARNESS_BROKEN: unmeasured share {unmeas_share:.1%} > {MAX_UNMEASURED:.0%}.")
        print("  A LOW bucket built from UNKNOWN positions would masquerade as flat exposure.")
        print("  NO VERDICT.")
        return 2
    if len(plausible) < 90:
        print("\nBROKEN: too few plausible wallets for terciles. NO VERDICT.")
        return 2

    exp = np.array([r["net_exposure"] for r in plausible])
    eq = np.array([r["equity7"] for r in plausible])
    prior_roi = np.array([r["prior"] for r in plausible]) / eq
    fut_roi = np.array([r["future"] for r in plausible]) / eq

    q = np.percentile(exp, [50, 90, 99])
    print(f"\nnet-exposure ratio (usable): median={q[0]:.4f} p90={q[1]:.4f} "
          f"p99={q[2]:.4f} max={exp.max():.4f}")

    q1, q2 = np.quantile(exp, [1 / 3, 2 / 3])
    print(f"{'tercile':10} {'n':>5} {'rho':>9} {'mean_net_exp':>13}")
    rhos = {}
    for name, m in (("LOW", exp <= q1), ("MID", (exp > q1) & (exp <= q2)), ("HIGH", exp > q2)):
        if m.sum() < 20:
            print(f"{name:10} {m.sum():5}  too few")
            continue
        rhos[name] = spearman(prior_roi[m], fut_roi[m])
        print(f"{name:10} {m.sum():5} {rhos[name]:+9.4f} {exp[m].mean():13.4f}")

    whole = spearman(prior_roi, fut_roi)
    print(f"\nwhole-sample rho (measured, plausible subset) = {whole:+.4f}  n={len(plausible):,}")
    if "LOW" in rhos and "HIGH" in rhos:
        d = rhos["HIGH"] - rhos["LOW"]
        if rhos["LOW"] > 0.03 and abs(d) < 0.10:
            v = "SKILL-consistent: persistence survives in the LOW-exposure tercile"
        elif d >= 0.10 and rhos["LOW"] < 0.03:
            v = "BETA-consistent: persistence concentrates in HIGH exposure"
        else:
            v = "MIXED / INCONCLUSIVE"
        print(f"\nVERDICT: {v}   (rho_HIGH - rho_LOW = {d:+.4f})")

    out = f"reports/hl_beta_test_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json"
    json.dump({"total": total, "floored": len(floored), "unmeasured": len(unmeas),
               "unmeasured_share": round(unmeas_share, 4), "implausible": len(implausible),
               "usable": len(plausible), "whole_rho": whole, "tercile_rhos": rhos,
               "exposure_pct": {"median": float(q[0]), "p90": float(q[1]),
                                "p99": float(q[2]), "max": float(exp.max())},
               "tertile_cuts": [float(q1), float(q2)],
               "run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
              open(out, "w"), indent=1)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
