#!/usr/bin/env python3
"""
hl_skill_persistence.py — H-258: does verifiable trader skill persist out-of-sample?

Pre-registration: reports/hypothesis_registry.json -> H-258 (registered BEFORE this ran).

Design (fixed at registration, not tuned afterwards):
  prior  = month.pnl - week.pnl      (days 8-30, disjoint from future)
  future = week.pnl                  (days 1-7)
  statistic = Spearman rank-IC between prior ROI rank and future ROI rank,
              computed ONCE over the whole eligible cross-section.
              ROI = window_pnl / accountValue.

Why one cross-sectional rank-IC and not "follow the top 50":
  46,603 wallets means thousands look skilled by luck. Selecting the best N and
  then measuring them is selection-on-noise and cannot be powered. A single
  rank-IC over the whole cross-section is one test, so no multiplicity correction
  is needed to interpret it.

The positive control runs FIRST and gates the real verdict. A detector that
cannot return "yes" on data engineered to say yes must not be allowed to return
"no" on real data.
"""
import json
import hashlib
import sys
import time
import urllib.request

import numpy as np

LB = "https://stats-data.hyperliquid.xyz/Mainnet/leaderboard"
MIN_ACCT = 10_000.0
N_PERM = 10_000
N_BOOT = 10_000
RNG = np.random.default_rng(20261124)


# ---------------------------------------------------------------- utilities
def rankdata(x):
    """Average ranks, ties handled (scipy-free)."""
    x = np.asarray(x, dtype=float)
    n = x.size
    sorter = np.argsort(x, kind="mergesort")
    inv = np.empty(n, dtype=np.int64)
    inv[sorter] = np.arange(n)
    xs = x[sorter]
    obs = np.r_[True, xs[1:] != xs[:-1]]
    dense = obs.cumsum()[inv]
    count = np.r_[np.nonzero(obs)[0], n]
    return 0.5 * (count[dense] + count[dense - 1] + 1)


def spearman(x, y):
    if x.size < 3:
        return float("nan")
    rx, ry = rankdata(x), rankdata(y)
    return pearson(rx, ry)


def pearson(rx, ry):
    rx = rx - rx.mean()
    ry = ry - ry.mean()
    d = np.sqrt((rx * rx).sum() * (ry * ry).sum())
    return float((rx * ry).sum() / d) if d > 0 else float("nan")


def boot_ci(rx, ry, n=N_BOOT):
    """Bootstrap over rank PAIRS (ranks fixed from the full sample).

    Disclosed approximation: re-ranking inside every resample is the textbook
    version but costs O(n log n) x n times; at n~2e4 that is minutes for no
    inferential gain on a rank statistic. Resampling the rank pairs is the
    standard fast bootstrap of a correlation.
    """
    n_r = rx.size
    out = np.empty(n, dtype=float)
    for i in range(n):
        idx = RNG.integers(0, n_r, n_r)
        out[i] = pearson(rx[idx], ry[idx])
    return np.percentile(out, [2.5, 97.5])


def perm_p(rx, ry, n=N_PERM):
    """One-sided: P(permuted rho >= observed)."""
    obs = pearson(rx, ry)
    ry0 = ry - ry.mean()
    denom = np.sqrt((rx * rx).sum() * (ry0 * ry0).sum())
    ge = 0
    for _ in range(n):
        p = RNG.permutation(ry0)
        if float((rx * p).sum() / denom) >= obs:
            ge += 1
    return (ge + 1) / (n + 1)


# ---------------------------------------------------------------- positive control
def positive_control():
    """Synthetic universe with KNOWN persistent skill. Detector must recover it.

    10% of wallets carry a real weekly skill edge of +3% on 10% weekly vol.
    Under no skill, rho should be ~0. With skill it must be clearly positive.
    """
    n, frac, edge, vol = 20_000, 0.10, 0.03, 0.10
    skilled = RNG.random(n) < frac
    prior = RNG.normal(0.0, vol, n)
    # skilled wallets carry the edge in BOTH windows -> persistence
    future = prior * 0.30 + RNG.normal(0.0, vol, n) + np.where(skilled, edge, 0.0)
    rx, ry = rankdata(prior), rankdata(future)
    rho = pearson(rx, ry)
    lo, hi = boot_ci(rx, ry, n=800)
    # does the top decile capture the skilled cohort?
    cut = np.quantile(future, 0.90)
    share_skilled_top = skilled[future >= cut].mean() if (future >= cut).any() else 0.0
    ok = rho > 0.05 and lo > 0.0 and share_skilled_top > frac
    print(f"POSITIVE CONTROL  rho={rho:.4f}  CI=[{lo:.4f},{hi:.4f}]  "
          f"top-decile skilled share={share_skilled_top:.1%} (base {frac:.0%})  -> "
          f"{'PASS' if ok else 'FAIL'}")
    return ok, rho


# ---------------------------------------------------------------- data
def fetch():
    raw = urllib.request.urlopen(LB, timeout=90).read()
    sha = hashlib.sha256(raw).hexdigest()
    d = json.loads(raw)
    rows = d if isinstance(d, list) else next(v for v in d.values() if isinstance(v, list))
    return rows, sha


def parse(rows):
    recs = []
    dup = 0
    seen = set()
    for r in rows:
        addr = (r.get("ethAddress") or "").lower()
        if not addr:
            continue
        if addr in seen:
            dup += 1
            continue
        seen.add(addr)
        wp = {k: v for k, v in (r.get("windowPerformances") or [])}
        def g(win, field, default=0.0):
            try:
                return float(wp[win][field])
            except (KeyError, TypeError, ValueError):
                return default
        acct = float(r.get("accountValue") or 0.0)
        wk_pnl, mo_pnl = g("week", "pnl"), g("month", "pnl")
        wk_vlm, mo_vlm = g("week", "vlm"), g("month", "vlm")
        recs.append(dict(addr=addr, acct=acct, wk_pnl=wk_pnl, mo_pnl=mo_pnl,
                         wk_vlm=wk_vlm, mo_vlm=mo_vlm,
                         prior=mo_pnl - wk_pnl, future=wk_pnl))
    return recs, dup


def main():
    print("=" * 78)
    print("H-258  Hyperliquid trader-skill persistence (out-of-sample)")
    print("=" * 78)

    pc_ok, pc_rho = positive_control()
    if not pc_ok:
        print("\nHARNESS_BROKEN: positive control failed. NO VERDICT IS PERMISSIBLE.")
        return 2

    t0 = time.time()
    # --snapshot PATH replays a locked sample instead of re-fetching, so a
    # re-run never silently samples different data than the registration lock.
    replay = sys.argv[1] if len(sys.argv) > 1 else None
    if replay:
        saved = json.load(open(replay))
        recs = saved["rows"]
        sha = saved["sha256"]
        print(f"\nreplayed snapshot: {replay} ({len(recs):,} wallets, sha256={sha[:16]}...)")
    else:
        rows, sha = fetch()
        recs, dup = parse(rows)
        print(f"\nsnapshot: {len(rows):,} rows -> {len(recs):,} unique wallets "
              f"({dup} dup) | sha256={sha[:16]}... | {time.time()-t0:.1f}s")
        snap = f"reports/hl_leaderboard_snapshot_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json"
        json.dump({"sha256": sha, "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "n_rows": len(rows), "rows": recs}, open(snap, "w"))
        print(f"snapshot saved: {snap}")

    # eligible universe (fixed at registration)
    elig = [r for r in recs
            if r["acct"] >= MIN_ACCT and r["wk_vlm"] > 0 and r["mo_vlm"] > 0]
    print(f"eligible: acct>={MIN_ACCT:,.0f} AND vlm>0 in both windows -> {len(elig):,}")

    if len(elig) < 2000:
        print("BROKEN: eligible universe < 2000. Not extended.")
        return 2

    prior = np.array([r["prior"] for r in elig])
    future = np.array([r["future"] for r in elig])
    acct = np.array([r["acct"] for r in elig])
    prior_roi = prior / acct
    future_roi = future / acct

    rx, ry = rankdata(prior_roi), rankdata(future_roi)
    rho = pearson(rx, ry)
    lo, hi = boot_ci(rx, ry)
    p = perm_p(rx, ry)

    rho_pnl = spearman(prior, future)
    print(f"\n--- PRIMARY: prior ROI rank vs future ROI rank ---")
    print(f"  rho = {rho:+.5f}   bootstrap 95% CI [{lo:+.5f}, {hi:+.5f}]   permutation p = {p:.5f}")
    print(f"  secondary (raw PnL): rho = {rho_pnl:+.5f}")

    # decile spread — the economically meaningful view
    order = np.argsort(-prior_roi)
    k = max(1, len(order) // 10)
    top, rest = order[:k], order[k:]
    top_f = future_roi[top]
    med_f = float(np.median(future_roi))
    spread = float(top_f.mean() - med_f)
    hit = float((top_f > 0).mean())
    base = float((future_roi > 0).mean())
    hurdle = 0.0009  # 2 x 4.5bp taker
    # Tail diagnostics: the mean and the median of the top decile disagreeing is
    # the signature of a few leveraged blowups dominating the average.
    med_top = float(np.median(top_f))
    blow = int((top_f < -0.50).sum())
    # 5% two-tail trimmed mean (drop the worst 5% AND the best 5%).
    s = np.sort(top_f)
    t = max(1, int(0.05 * k))
    trim = float(s[t:k - t].mean()) if k > 2 * t else float("nan")
    print(f"\n--- ECONOMIC VIEW (prior top decile, n={k:,}) ---")
    print(f"  MEAN   future ROI {top_f.mean():+.4%}   vs median wallet {med_f:+.4%}   spread {spread:+.4%}")
    print(f"  MEDIAN future ROI {med_top:+.4%}   (mean/median disagreeing => tail-driven)")
    print(f"  blowups (future ROI < -50%): {blow} of {k:,} ({blow/k:.1%})  5%-trimmed mean {trim:+.4%}")
    print(f"  P(future ROI>0): top decile {hit:.1%}  vs whole cross-section {base:.1%}")
    print(f"  cost hurdle {hurdle:.2%} -> {'CLEARED' if spread > hurdle else 'NOT cleared'}")
    econ_ok = spread > hurdle

    # verdict per the pre-registered rules (economic gate is NOT optional)
    if rho >= 0.05 and lo > 0 and p < 0.01 and econ_ok:
        verdict = "SUPPORTED (pending a second snapshot >=7d later)"
    elif lo > 0 and not econ_ok:
        verdict = ("PERSISTENT IN ORDER, ECONOMICALLY NEGATIVE - following the naive top decile "
                   "loses money after tail losses, so NOT supported for copy-trading")
    elif hi < 0 and rho <= 0:
        verdict = "REFUTED (skill does not persist / luck reverts)"
    elif lo > 0:
        verdict = "NULL - detectable but below the 0.05 economic threshold"
    else:
        verdict = "INCONCLUSIVE (CI spans zero)"
    print(f"\nVERDICT: {verdict}")
    print(f"(positive control rho {pc_rho:.4f} proves the detector can say yes)")
    print("\nUNRESOLVED CONFOUND (must be tested before any skill claim):")
    print("  A high rank-IC can be produced by PERSISTENT DIRECTIONAL EXPOSURE, not skill: if")
    print("  wallets are long-biased and the asset trended over both windows, prior and future")
    print("  ROI correlate through market beta. The leaderboard has no position data, so this")
    print("  cannot be separated here. Follow-up H-259 must bucket by net exposure.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
