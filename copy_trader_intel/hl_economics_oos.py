#!/usr/bin/env python3
"""
hl_economics_oos.py — rank-IC is not profit. Three tests on the H-260 persistence result.

(1) ECONOMIC GATE. Copy the top decile by PRIOR rank into the future week and ask what it pays
    NET of the 9 bp round-trip gate. Reports n, median turnover, net bp per round trip, and the
    per-wallet distribution — because a mean carried by three wallets is not a strategy.
    If top-decile copy does not clear 9 bp net, rho +0.44 is a fact about wallet behaviour and
    NOT a tradable edge. That sentence is the output if the number says so.

(2) OUT-OF-SAMPLE. Bucket realised PnL into NON-OVERLAPPING weeks over ~90 days and compute the
    identical rank-IC for every adjacent week pair. Reports the DISTRIBUTION of rho, not one value.
    +0.44 +0.41 +0.47 +0.43 is structural; +0.44 -0.05 +0.12 -0.20 was a draw.

(3) LOW-TERCILE CARRIED-OVER AUDIT. At low leverage a "persistent" wallet may simply be holding a
    position opened BEFORE the future window — a frozen number, not a new decision. Using
    startPosition on every fill, attribution is exact: a position begins when startPosition == 0.
    Reports the share of future-window realised PnL from positions opened INSIDE the window.

Realised PnL comes from fills (`closedPnl`), not from the leaderboard's mark-to-market window, so
the economic numbers are what a copier could actually have booked.
"""
from __future__ import annotations

import glob
import json
import random
import statistics as st
import sys
import time
import urllib.request

import numpy as np

API = "https://api.hyperliquid.xyz/info"
DAY = 86_400_000
WEEK = 7 * DAY
LOOKBACK_DAYS = 98
MIN_ACCT = 10_000.0
COST_BP = 9.0
RNG = np.random.default_rng(20261125)


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


def pcor(a, b):
    a = a - a.mean(); b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d > 0 else float("nan")


def spearman(x, y):
    if len(x) < 3:
        return float("nan")
    return pcor(rankdata(x), rankdata(y))


def at_or_before(series, ts):
    best = None
    for t, v in series:
        if t <= ts:
            best = float(v)
        else:
            break
    return best


def load_wallet(addr, now):
    """Returns per-wallet record or None."""
    t7, t30 = now - WEEK, now - 30 * DAY
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
    eq7 = at_or_before(ah, t7)
    if None in (p_now, p7, p30) or not eq7 or eq7 < MIN_ACCT:
        return None

    fills = post({"type": "userFillsByTime", "user": addr,
                  "startTime": now - LOOKBACK_DAYS * DAY, "endTime": now})
    if not isinstance(fills, list) or not fills:
        return None

    # ---- realised PnL bucketed into non-overlapping weeks (index 0 = oldest)
    nb = LOOKBACK_DAYS // 7
    base = now - nb * WEEK
    weekly = [0.0] * (nb + 1)
    fut_pnl = 0.0
    fut_notional = 0.0
    fut_fills = 0
    # ---- carried-over attribution, per coin
    open_at = {}
    new_pnl = 0.0
    carried_pnl = 0.0

    for f in sorted(fills, key=lambda x: int(x.get("time", 0))):
        try:
            t = int(f["time"])
            coin = f["coin"]
            sz, px = float(f["sz"]), float(f["px"])
            side = f.get("side")
            start = float(f.get("startPosition", 0.0))
            closed = float(f.get("closedPnl") or 0.0)
            notional = abs(sz * px)
        except (KeyError, TypeError, ValueError):
            continue

        b = (t - base) // WEEK
        if 0 <= b < len(weekly):
            weekly[int(b)] += closed

        in_future = t >= t7
        if in_future:
            fut_pnl += closed
            fut_notional += notional
            fut_fills += 1

        # position lifecycle: startPosition == 0 means this fill OPENS the position
        if abs(start) < 1e-12:
            open_at[coin] = t
        if closed != 0.0:
            opened = open_at.get(coin)
            if opened is not None and opened >= t7:
                new_pnl += closed
            else:
                carried_pnl += closed
        after = start + (sz if side == "B" else -sz)
        if abs(after) < 1e-12:
            open_at.pop(coin, None)

    return dict(addr=addr, eq7=eq7, prior=p7 - p30, future=p_now - p7,
                weekly=weekly, base=base,
                fut_realised=fut_pnl, fut_notional=fut_notional, fut_fills=fut_fills,
                new_pnl=new_pnl, carried_pnl=carried_pnl)


def main():
    n_target = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    print("=" * 80)
    print(f"H-260 economics / OOS / carried-over   (sample={n_target})")
    print("=" * 80)

    snap = json.load(open(sorted(glob.glob("reports/hl_leaderboard_snapshot_*.json"))[-1]))
    elig = [r for r in snap["rows"] if r["acct"] >= MIN_ACCT and r["wk_vlm"] > 0]
    random.seed(1234)
    samp = random.sample(elig, min(n_target, len(elig)))
    now = int(time.time() * 1000)

    recs, fail = [], 0
    t0 = time.time()
    for i, r in enumerate(samp, 1):
        w = load_wallet(r["addr"], now)
        if w is None:
            fail += 1
        else:
            recs.append(w)
        if i % 50 == 0:
            print(f"  ..{i}/{len(samp)} ok={len(recs)} fail={fail} {time.time()-t0:.0f}s")
        time.sleep(0.05)
    print(f"\nusable {len(recs):,} / {len(samp):,} (failed {fail}) in {time.time()-t0:.0f}s")
    if len(recs) < 100:
        print("BROKEN: n<100. NO VERDICT.")
        return 2

    out = {"n": len(recs), "run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    # ================= (1) ECONOMIC GATE =================
    prior = np.array([w["prior"] / w["eq7"] for w in recs])
    order = np.argsort(-prior)
    k = max(1, len(order) // 10)
    top = [recs[i] for i in order[:k]]

    rows = []
    for w in top:
        if w["fut_notional"] <= 0:
            continue
        # round trips: notional turns over twice per round trip
        rt = w["fut_notional"] / (2.0 * w["eq7"])
        if rt <= 0:
            continue
        cost = COST_BP / 10000.0 * (2.0 * rt)          # 9bp per round trip on notional
        net_roi = w["fut_realised"] / w["eq7"] - cost
        net_bp_per_rt = (net_roi / rt) * 10000.0
        rows.append(dict(addr=w["addr"], rt=rt, net_roi=net_roi,
                         net_bp=net_bp_per_rt, realised=w["fut_realised"]))

    print(f"\n--- (1) ECONOMIC GATE: top decile by prior rank, copied for one week ---")
    print(f"  top-decile wallets          : {k}")
    with_activity = len(rows)
    print(f"  of which traded in the week : {with_activity}")
    if with_activity >= 5:
        net_bps = np.array([r["net_bp"] for r in rows])
        rts = np.array([r["rt"] for r in rows])
        rois = np.array([r["net_roi"] for r in rows])
        pos = net_bps > 0
        top3 = np.sort(rois)[::-1][:3].sum() / rois.sum() if rois.sum() != 0 else float("nan")
        print(f"  median turnover (round trips/wk): {np.median(rts):.2f}")
        print(f"  median net bp per round trip : {np.median(net_bps):+.2f}   (gate = {COST_BP:.0f} bp)")
        print(f"  mean   net bp per round trip : {net_bps.mean():+.2f}")
        print(f"  trimmed(10%) mean net bp     : {st.mean(sorted(net_bps)[max(1,int(.1*len(net_bps))):len(net_bps)-max(1,int(.1*len(net_bps)))]) if len(net_bps)>5 else float('nan'):+.2f}")
        print(f"  share of wallets net-positive: {pos.mean():.1%}")
        print(f"  top-3 wallets' share of total net ROI: {top3:.1%}  "
              f"({'CARRIED BY A FEW - not a strategy' if top3 > 0.5 else 'not concentrated'})")
        clears = np.median(net_bps) > 0 and pos.mean() > 0.5
        print(f"  GATE: {'CLEARS' if clears else 'DOES NOT CLEAR'} 9bp net")
        if not clears:
            print("  => rho +0.44 is a real fact about wallet behaviour and NOT a tradable edge.")
        out["economic"] = {"n_top": k, "n_traded": with_activity,
                           "median_turnover_rt": float(np.median(rts)),
                           "median_net_bp": float(np.median(net_bps)),
                           "mean_net_bp": float(net_bps.mean()),
                           "share_positive": float(pos.mean()),
                           "top3_share_of_net_roi": float(top3),
                           "clears_9bp": bool(clears),
                           "distribution_net_bp": [round(float(v), 1) for v in net_bps]}
    else:
        print("  too few top-decile wallets traded - GATE UNDETERMINED")

    # ================= (2) OUT-OF-SAMPLE WEEK PAIRS =================
    nb = len(recs[0]["weekly"]) - 1
    print(f"\n--- (2) OUT-OF-SAMPLE: rank-IC across non-overlapping week pairs ({nb} weeks) ---")
    rhos, pair_n = [], []
    for w in range(nb - 1):
        a = np.array([r["weekly"][w] for r in recs])
        b = np.array([r["weekly"][w + 1] for r in recs])
        m = (a != 0) | (b != 0)
        if m.sum() < 60:
            continue
        r_ = spearman(a[m], b[m])
        rhos.append(r_); pair_n.append(int(m.sum()))
        print(f"  week {w+1:>2} -> {w+2:<2}  n={m.sum():>4}  rho={r_:+.4f}")
    if rhos:
        arr = np.array(rhos)
        print(f"\n  DISTRIBUTION over {len(rhos)} pairs: median={np.median(arr):+.4f} "
              f"mean={arr.mean():+.4f} min={arr.min():+.4f} max={arr.max():+.4f} "
              f"positive in {int((arr>0).sum())}/{len(arr)}")
        out["oos"] = {"n_pairs": len(rhos), "rho_median": float(np.median(arr)),
                      "rho_mean": float(arr.mean()), "rho_min": float(arr.min()),
                      "rho_max": float(arr.max()), "n_positive": int((arr > 0).sum()),
                      "rhos": [round(float(v), 4) for v in rhos]}

    # ================= (3) CARRIED-OVER AUDIT =================
    print(f"\n--- (3) CARRIED-OVER AUDIT on future-window realised PnL ---")
    tot_new = sum(r["new_pnl"] for r in recs)
    tot_car = sum(r["carried_pnl"] for r in recs)
    denom = abs(tot_new) + abs(tot_car)
    share_new = abs(tot_new) / denom if denom > 0 else float("nan")
    print(f"  from positions OPENED inside the future window : {share_new:.1%} of |realised|")
    print(f"  from positions opened BEFORE it (carried over) : {1-share_new:.1%}")
    print(f"  totals: new={tot_new:,.0f}  carried={tot_car:,.0f}")

    # restrict to low-turnover wallets (the LOW-leverage tercile claim)
    lev = np.array([w["fut_notional"] / (2 * w["eq7"]) if w["eq7"] else 0.0 for w in recs])
    q1 = np.quantile(lev, 1/3)
    low = [r for r, l in zip(recs, lev) if l <= q1]
    ln = sum(r["new_pnl"] for r in low); lc = sum(r["carried_pnl"] for r in low)
    ld = abs(ln) + abs(lc)
    share_low = abs(ln) / ld if ld > 0 else float("nan")
    print(f"  LOW-turnover tercile only (n={len(low)}): {share_low:.1%} from positions opened inside")
    if share_low < 0.5:
        print("  => the LOW-tercile persistence is substantially a FROZEN position, not a new decision.")
    out["carried_over"] = {"share_new_all": float(share_new), "share_new_low_tercile": float(share_low),
                           "new_pnl": float(tot_new), "carried_pnl": float(tot_car),
                           "low_tercile_n": len(low)}

    json.dump(out, open("reports/hl_economics_oos.json", "w"), indent=1)
    print("\nwrote reports/hl_economics_oos.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
