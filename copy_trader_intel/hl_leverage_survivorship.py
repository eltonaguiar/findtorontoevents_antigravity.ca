#!/usr/bin/env python3
"""
hl_leverage_survivorship.py — does H-260's rank persistence survive leverage and survivorship?

TWO objections this answers:

(A) LEVERAGE. A wallet running 20x posts persistently extreme PnL in BOTH windows because
    variance scales with exposure. A positive rank-IC on RAW PnL is therefore exactly what
    pure exposure persistence looks like. Conditioning is done three ways:
      1. partial Spearman: rho(prior, future | leverage)
      2. rank-IC computed WITHIN leverage terciles
      3. a NEGATIVE CONTROL that manufactures a leverage-only "edge" and must be destroyed
         by the conditioning — if the method cannot kill that, it cannot certify the real one.

    Leverage proxy: month_volume / accountValue (turnover intensity). This is a PROXY, not
    position notional / equity. It is used because it exists for every wallet without a
    per-wallet position pull, and because the direct measure was shown today to be
    unmeasurable at a single instant (24% unknown, 1,133x artefacts). Stated, not hidden.

(B) SURVIVORSHIP. My eligibility required week_volume > 0, which structurally deletes wallets
    that stopped trading between the two windows — disproportionately the blown-up ones. The
    future window is then conditioned on survival by construction, biasing persistence UP.
    Measured: the fraction of prior-window-eligible wallets missing from the future window,
    and rho recomputed with them included (future PnL = 0, the recorded value for a wallet
    that stopped).
"""
from __future__ import annotations

import glob
import json
import sys

import numpy as np

MIN_ACCT = 10_000.0
RNG = np.random.default_rng(20261125)


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
    return pcor(rankdata(x), rankdata(y))


def partial_spearman(x, y, z):
    """rho(x,y) with z held out, computed on ranks."""
    rx, ry, rz = rankdata(x), rankdata(y), rankdata(z)
    rxy, rxz, ryz = pcor(rx, ry), pcor(rx, rz), pcor(ry, rz)
    den = np.sqrt((1 - rxz ** 2) * (1 - ryz ** 2))
    return float((rxy - rxz * ryz) / den) if den > 0 else float("nan")


def report_block(name, prior, future, lev, show_partial=True):
    r_raw = spearman(prior, future)
    out = {"n": int(prior.size), "rho_raw": round(r_raw, 4)}
    if show_partial:
        rp = partial_spearman(prior, future, lev)
        out["rho_partial_given_leverage"] = round(rp, 4)
        out["rho_prior_lev"] = round(spearman(prior, lev), 4)
        out["rho_future_lev"] = round(spearman(future, lev), 4)
    # within-tercile
    q1, q2 = np.quantile(lev, [1 / 3, 2 / 3])
    ter = {}
    for nm, m in (("LOW", lev <= q1), ("MID", (lev > q1) & (lev <= q2)), ("HIGH", lev > q2)):
        if m.sum() >= 20:
            ter[nm] = {"n": int(m.sum()), "rho": round(spearman(prior[m], future[m]), 4),
                       "mean_lev": round(float(lev[m].mean()), 4)}
    out["terciles"] = ter
    print(f"\n{name}")
    print(f"  n={out['n']:,}  rho_raw={r_raw:+.4f}", end="")
    if show_partial:
        print(f"  rho_PARTIAL(given leverage)={out['rho_partial_given_leverage']:+.4f}"
              f"   [rho(prior,lev)={out['rho_prior_lev']:+.3f} "
              f"rho(future,lev)={out['rho_future_lev']:+.3f}]")
    else:
        print()
    for nm in ("LOW", "MID", "HIGH"):
        if nm in ter:
            t = ter[nm]
            print(f"    {nm:5} n={t['n']:>5}  lev={t['mean_lev']:>9.3f}  rho={t['rho']:+.4f}")
    return out


def controls():
    """The method must PASS on leverage-independent skill and KILL leverage-only persistence."""
    n = 20_000
    lev = RNG.lognormal(0, 1.0, n)                       # heavy-tailed leverage
    prior = 0.5 * np.log1p(lev) + RNG.normal(0, 1, n)    # prior partly leverage-driven
    ok = True

    # POSITIVE: genuine skill independent of leverage
    fut_skill = 0.5 * prior + RNG.normal(0, 1, n) + 0.6 * np.log1p(lev)
    r_raw = spearman(prior, fut_skill)
    r_par = partial_spearman(prior, fut_skill, lev)
    pos_ok = r_raw > 0.1 and r_par > 0.1
    print(f"CONTROL +  skill independent of leverage: raw={r_raw:+.3f} partial={r_par:+.3f} "
          f"-> {'PASS' if pos_ok else 'FAIL'} (partial must stay strongly positive)")
    ok &= pos_ok

    # NEGATIVE: persistence is PURELY leverage (future depends only on lev, + noise)
    fut_lev = RNG.normal(0, 1, n) + 1.2 * np.log1p(lev)
    r_raw_n = spearman(prior, fut_lev)
    r_par_n = partial_spearman(prior, fut_lev, lev)
    neg_ok = r_raw_n > 0.1 and abs(r_par_n) < 0.05
    print(f"CONTROL -  persistence is PURE leverage: raw={r_raw_n:+.3f} partial={r_par_n:+.3f} "
          f"-> {'PASS' if neg_ok else 'FAIL'} (partial must collapse to ~0)")
    ok &= neg_ok
    return ok


def load_rows():
    snap = json.load(open(sorted(glob.glob("reports/hl_leaderboard_snapshot_*.json"))[-1]))
    return snap["rows"]


def main():
    print("=" * 78)
    print("H-260 robustness: leverage conditioning + survivorship")
    print("=" * 78)
    if not controls():
        print("\nHARNESS_BROKEN: controls did not behave. NO VERDICT.")
        return 2

    rows = [r for r in load_rows() if r["acct"] >= MIN_ACCT]

    # ---- survivorship accounting
    prior_elig = [r for r in rows if r["mo_vlm"] > 0]
    surv = [r for r in prior_elig if r["wk_vlm"] > 0]
    missing = [r for r in prior_elig if r["wk_vlm"] <= 0]
    frac_missing = len(missing) / max(len(prior_elig), 1)
    print(f"\nSURVIVORSHIP")
    print(f"  prior-window eligible (month vlm>0)      : {len(prior_elig):,}")
    print(f"  present in future window (week vlm>0)    : {len(surv):,}")
    print(f"  MISSING from the future window           : {len(missing):,}  "
          f"({frac_missing:.1%})  <-- deleted by the wk_vlm>0 filter")

    out = {"survivorship": {"prior_eligible": len(prior_elig), "survivors": len(surv),
                            "missing": len(missing), "missing_share": round(frac_missing, 4)}}

    # ---- main conditioning, survivors only (the H-260 definition)
    prior = np.array([r["prior"] for r in surv])
    future = np.array([r["future"] for r in surv])
    acct = np.array([r["acct"] for r in surv])
    lev = np.array([r["mo_vlm"] for r in surv]) / acct        # turnover/equity proxy
    out["survivors_only_raw_pnl"] = report_block(
        "A. SURVIVORS ONLY — raw PnL (this is the 0.449)", prior, future, lev)
    out["survivors_only_roi"] = report_block(
        "B. SURVIVORS ONLY — ROI", prior / acct, future / acct, lev)

    # ---- survivorship-corrected: put the missing wallets back with future = recorded week pnl
    allp = np.array([r["prior"] for r in prior_elig])
    allf = np.array([r["future"] for r in prior_elig])
    allacct = np.array([r["acct"] for r in prior_elig])
    alllev = np.array([r["mo_vlm"] for r in prior_elig]) / allacct
    out["survivorship_corrected_raw_pnl"] = report_block(
        "C. ALL PRIOR-ELIGIBLE (missing wallets re-included, future=week pnl)",
        allp, allf, alllev)
    print(f"  -> bias from the survivorship filter: raw rho "
          f"{out['survivors_only_raw_pnl']['rho_raw']:+.4f} -> "
          f"{out['survivorship_corrected_raw_pnl']['rho_raw']:+.4f}")

    json.dump(out, open("reports/hl_leverage_survivorship.json", "w"), indent=1)
    print("\nwrote reports/hl_leverage_survivorship.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
