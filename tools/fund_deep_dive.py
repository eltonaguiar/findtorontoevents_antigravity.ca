#!/usr/bin/env python3
"""fund_deep_dive.py — real-data comparison of index funds / ETFs / mutual funds.

Source: 2026-11-15_AM_profitability-plan/copilot-financial-review/market_prices.csv
(adjusted close, 2021-11-15..2026-11-13, ~1,254 daily returns). Computes per-fund:
CAGR, vol, true Sharpe, true Sortino, max drawdown, and NET-of-MER CAGR. Also builds
simple portfolios (100% equity, 60/40, 80/20, T-bill), net of the fund's own MER.
This is a BUYING analysis (beta), not an edge claim.

2026-11-23 corrections (see docs/edge_research/FUND_DEEP_DIVE_TODO_2026-11-23.md):
  A1/A2  Sharpe and Sortino are now (R - R_f)/risk with SGOV net CAGR as R_f.
         The old column survives as `ret_vol` because it is a fee-adjusted
         return/vol ratio, NOT Sharpe. Calling it Sharpe did not make it Sharpe.
  A4     SGOV's ratio is reported as cash (n/a), not 15.886.
  A5     Sortino used a downside-only denominator (dividing by the count of
         negative days), which inflates sigma_down. The correct target downside
         deviation divides by ALL n. Both are emitted so the delta is visible;
         `sortino` is the correct one.
  A6     net_cagr was additive (cagr - mer); now compounded (1+cagr)(1-mer)-1.
  A7     vol used the population stdev; now the sample stdev.
Paper only. Zero capital. Not investment advice.
"""
import csv, json, math, random, statistics as st
from datetime import datetime, timezone
from pathlib import Path

SRC = "2026-11-15_AM_profitability-plan/copilot-financial-review/market_prices.csv"
ANN = 252
CASH_KEY = "SGOV_adj"
# expense ratios (MER), decimal per year
MER = {"FZROX_adj": 0.0000, "FXAIX_adj": 0.00015, "VTSAX_adj": 0.0004,
       "SPY_adj": 0.000945, "VTI_adj": 0.0003, "BND_adj": 0.0003, "SGOV_adj": 0.0009}
LABEL = {"FZROX_adj": "Fidelity ZERO Total Market (index MF, 0.00%)",
         "FXAIX_adj": "Fidelity 500 Index (index MF, 0.015%)",
         "VTSAX_adj": "Vanguard Total Stock (index MF, 0.04%)",
         "SPY_adj": "SPDR S&P 500 ETF (0.0945%)",
         "VTI_adj": "Vanguard Total Market ETF (0.03%)",
         "BND_adj": "Vanguard Total Bond ETF (0.03%)",
         "SGOV_adj": "iShares 0-3mo T-bill ETF (0.09%)"}


def load():
    rows = list(csv.DictReader(open(SRC)))
    cols = [c for c in rows[0] if c.endswith("_adj")]
    ser = {c: [] for c in cols}
    dates = []
    for r in rows:
        ok = True
        vals = {}
        for c in cols:
            try:
                vals[c] = float(r[c])
            except Exception:
                ok = False
                break
        if ok:
            dates.append(r["date"])
            for c in cols:
                ser[c].append(vals[c])
    ret = {c: [ser[c][i] / ser[c][i - 1] - 1 for i in range(1, len(ser[c]))] for c in cols}
    return dates, ser, ret


def metrics(r, mer=0.0, ann=ANN):
    """Raw fee-adjusted statistics. Ratios are finalised by add_ratios()."""
    n = len(r)
    mu = st.mean(r)
    sd = st.stdev(r) if n > 1 else 0.0          # A7: sample, not population
    cagr = (math.prod(1 + x for x in r)) ** (ann / n) - 1 if n else 0
    net_cagr = (1 + cagr) * (1 - mer) - 1        # A6: compounded, not cagr-mer
    eq = 1.0
    peak = 1.0
    mdd = 0.0
    for x in r:
        eq *= (1 + x)
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
    return {
        "cagr_pct": round(cagr * 100, 2),
        "net_cagr_pct": round(net_cagr * 100, 2),
        "vol_pct": round(sd * math.sqrt(ann) * 100, 2),
        "max_dd_pct": round(mdd * 100, 2),
        "n": n,
        "_net_cagr": net_cagr, "_vol": sd * math.sqrt(ann),
        "_mu_ann": mu * ann, "_mer": mer, "_r": r, "_ann": ann,
    }


def add_ratios(m, rf):
    """A1/A2/A4/A5: true Sharpe and Sortino, excess of cash.

    rf is the annual cash return as a decimal (SGOV's own net CAGR). mar is the
    same rate expressed per-period, so downside deviation is measured against the
    cash hurdle rather than against zero.
    """
    vol, n, r, mer, ann = m["_vol"], m["n"], m["_r"], m["_mer"], m["_ann"]
    mar = (rf or 0.0) / ann
    dsd_all = math.sqrt(sum(min(0.0, x - mar) ** 2 for x in r) / n) if n else 0.0
    down = [x for x in r if x < 0]
    dsd_legacy = math.sqrt(sum(x * x for x in down) / len(down)) if down else 0.0
    m["ret_vol"] = round((m["_mu_ann"] - mer) / vol, 3) if vol else None
    m["sharpe"] = round((m["_net_cagr"] - rf) / vol, 3) if (vol and rf is not None) else None
    m["sortino"] = (round((m["_net_cagr"] - rf) / (dsd_all * math.sqrt(ann)), 3)
                    if (dsd_all and rf is not None) else None)
    m["sortino_legacy"] = (round((m["_net_cagr"] - rf) / (dsd_legacy * math.sqrt(ann)), 3)
                           if (dsd_legacy and rf is not None) else None)
    m["rf_pct"] = round(rf * 100, 2) if rf is not None else None
    for k in [k for k in list(m) if k.startswith("_")]:
        del m[k]
    return m


def _mdd_of(rs):
    eq = 1.0
    peak = 1.0
    mdd = 0.0
    for x in rs:
        eq *= (1 + x)
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
    return mdd


def _cagr_of(rs, ann=ANN):
    n = len(rs)
    return (math.prod(1 + x for x in rs)) ** (ann / n) - 1 if n else 0.0


def _vol_of(rs, ann=ANN):
    return st.stdev(rs) * math.sqrt(ann) if len(rs) > 1 else 0.0


def _pct(sorted_xs, lo=0.05, hi=0.95):
    k = len(sorted_xs)
    return round(sorted_xs[int(lo * k)] * 100, 3), round(sorted_xs[min(k - 1, int(hi * k))] * 100, 3)


def bootstrap_stats(r, block=21, n_boot=1000, seed=20261123):
    """Moving-block bootstrap (B1/B2). Blocks preserve short-range dependence
    that an i.i.d. bootstrap would destroy."""
    n = len(r)
    if n <= block or block < 1:
        return None
    rng = random.Random(seed)
    nblocks = n // block + 1
    hi = n - block
    cagrs, vols, mdds = [], [], []
    for _ in range(n_boot):
        samp = []
        for _ in range(nblocks):
            j = rng.randrange(0, hi + 1)
            samp.extend(r[j:j + block])
        samp = samp[:n]
        cagrs.append(_cagr_of(samp))
        vols.append(_vol_of(samp))
        mdds.append(_mdd_of(samp))
    return {"cagr_ci_pct": _pct(sorted(cagrs)),
            "vol_ci_pct": _pct(sorted(vols)),
            "mdd_ci_pct": _pct(sorted(mdds)),
            "n_boot": n_boot, "block": block}


def bootstrap_pair_diff(a, b, block=21, n_boot=1000, seed=20261123):
    """B3: bootstrap the DIFFERENCE series, in the same blocks.

    Resampling each fund separately and comparing intervals is the wrong test --
    the two series are near-perfectly correlated (same index), so the paired
    difference has far less variance than either leg. This returns a CI on the
    annualised arithmetic difference in percentage points.
    """
    d = [x - y for x, y in zip(a, b)]
    n = len(d)
    if n <= block or block < 1:
        return None
    rng = random.Random(seed)
    nblocks = n // block + 1
    hi = n - block
    diffs = []
    for _ in range(n_boot):
        samp = []
        for _ in range(nblocks):
            j = rng.randrange(0, hi + 1)
            samp.extend(d[j:j + block])
        samp = samp[:n]
        diffs.append(st.mean(samp) * ANN)
    lo, hi_ = _pct(sorted(diffs))
    point = round(st.mean(d) * ANN * 100, 3)
    # B4: indistinguishable from zero when the interval straddles it.
    return {"point_pct": point, "ci_pct": (lo, hi_),
            "distinguishable_from_zero": not (lo <= 0.0 <= hi_)}


ANCHOR_TTL_HOURS = 24


def fetch_anchors(ttl_hours=ANCHOR_TTL_HOURS):
    """F1/F2/F7: current forward anchors, dated, failing loudly when stale.

    Trailing 5y CAGR is a poor forecast input. The decision-relevant numbers are
    the CURRENT cash yield and the CURRENT bond yield-to-maturity. They are
    fetched opt-in (--anchors) so the default run stays deterministic and works
    offline; but once fetched they are timestamped and a stale anchor is an
    error, not a silent fallback. (plan items F1, F2, F7)
    """
    out = {"fetched_at": datetime.now(timezone.utc).isoformat(), "ttl_hours": ttl_hours}
    try:
        import yfinance as yf
    except ImportError:
        out["error"] = "yfinance not installed; anchors unavailable"
        return out

    # F1: cash anchor = 13-week T-bill yield (^IRX, quoted in percent)
    try:
        h = yf.Ticker("^IRX").history(period="7d")
        if len(h):
            out["cash_tbill_yield_pct"] = round(float(h["Close"].iloc[-1]), 3)
            asof = str(h.index[-1].date())
            out["cash_asof"] = asof
            age_h = (datetime.now(timezone.utc)
                     - datetime.fromisoformat(asof + "T00:00:00+00:00")).total_seconds() / 3600
            out["cash_age_hours"] = round(age_h, 1)
            out["cash_stale"] = age_h > ttl_hours * 7   # weekend-tolerant
        else:
            out["cash_error"] = "no ^IRX history returned"
    except Exception as e:  # noqa: BLE001
        out["cash_error"] = str(e)[:160]

    # F2: bond anchor = BND yield-to-maturity proxy from the fund's own metadata
    try:
        info = yf.Ticker("BND").info or {}
        for key in ("yield", "yieldToMaturity", "ytm", "dividendYield"):
            v = info.get(key)
            if v:
                pct = float(v) * (100.0 if float(v) < 1.0 else 1.0)
                out["bnd_ytm_pct"] = round(pct, 3)
                out["bnd_ytm_source"] = key
                break
        else:
            out["bnd_error"] = "no yield field in BND metadata"
    except Exception as e:  # noqa: BLE001
        out["bnd_error"] = str(e)[:160]

    return out


def portfolio(ret, weights, rebal=None, merblend=0.0, spread_bp=0.0):
    """Portfolio daily returns with genuine periodic rebalancing.

    rebal=None  -> BUY AND HOLD: sleeves drift, nothing is ever traded.
    rebal=k     -> rebalance back to target weights every k trading days.

    Compounding is done sleeve-by-sleeve on a NAV, so buy-and-hold is a real,
    different path from rebalancing. The previous implementation summed weighted
    daily returns (`sum(w*r_i)`), which is *silently daily rebalancing* -- it
    harvested volatility and overstated the 60/40 versus buy-and-hold, while the
    docstring claimed monthly. (plan item D1)

    `spread_bp` charges a round-trip cost on the traded fraction at each
    rebalance: cost = turnover * spread. Turnover is the one-way weight change,
    sum(|w_drifted - w_target|)/2. (plan item D3)
    """
    cols = list(weights)
    n = min(len(ret[c]) for c in cols)
    target = [float(weights[c]) for c in cols]
    sleeve = list(target)                 # NAV starts at sum(target)
    prev_nav = sum(sleeve)
    out = []
    turnover_total = 0.0
    rebalances = 0

    for i in range(n):
        for j, c in enumerate(cols):
            sleeve[j] *= (1.0 + ret[c][i])
        nav = sum(sleeve)
        day_ret = nav / prev_nav - 1.0

        if rebal and (i + 1) % rebal == 0 and (i + 1) < n:
            drift = [v / nav for v in sleeve]
            turnover = sum(abs(drift[j] - target[j]) for j in range(len(cols))) / 2.0
            if turnover > 0:
                nav *= (1.0 - turnover * (spread_bp / 1e4))
                day_ret = nav / prev_nav - 1.0
                turnover_total += turnover
                rebalances += 1
                sleeve = [nav * t for t in target]

        out.append(day_ret)
        prev_nav = nav

    stats = {"turnover": round(turnover_total, 4), "rebalances": rebalances}
    return out, stats


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Fund deeper dive (paper only, not investment advice).")
    ap.add_argument("--anchors", action="store_true",
                    help="fetch current cash T-bill yield and BND YTM (needs network)")
    ap.add_argument("--out", default="reports/fund_deep_dive.json")
    args = ap.parse_args(argv)

    dates, ser, ret = load()
    out = {"schema_version": 2,
           "generated_at": datetime.now(timezone.utc).isoformat(),
           "source": SRC, "period": [dates[0], dates[-1]],
           "n_days": len(ret[list(ret)[0]]),
           "corrections": ["A1/A2 excess-of-cash Sharpe+Sortino", "A4 SGOV cash-labelled",
                           "A5 Sortino all-N denominator", "A6 compounded net CAGR",
                           "A7 sample stdev"],
           "rebalancing": "monthly (21 trading days) for standard portfolios; "
                          "see rebalance_sensitivity for buy-and-hold vs daily",
           "funds": {}}

    # Pass 1: raw statistics. Pass 2: ratios need the cash hurdle from SGOV.
    base = {c: metrics(ret[c], MER[c]) for c in ret}
    rf = base[CASH_KEY]["net_cagr_pct"] / 100.0

    hdr = (f"{'fund':34s}{'CAGR':>8s}{'netCAGR':>9s}{'vol':>7s}"
           f"{'ret/vol':>9s}{'Sharpe':>14s}{'Sortino':>9s}{'MaxDD':>8s}")
    print(f"cash hurdle R_f = {rf*100:.2f}%/yr (SGOV net CAGR)\n")
    print(hdr)
    for c in ret:
        m = add_ratios(base[c], rf)
        if c == CASH_KEY:
            # A4: SGOV is the hurdle. Its own ratio is 0/0, so store null --
            # a number here (e.g. -0.006) is an artefact of float rounding and
            # would be read as a real Sharpe by any consumer of this JSON.
            m["sharpe"] = None
            m["sortino"] = None
            m["ratio_note"] = "cash hurdle (R_f); Sharpe/Sortino undefined"
        out["funds"][c] = m
        label = "n/a (cash)" if c == CASH_KEY else str(m["sharpe"])
        print(f"{LABEL[c][:33]:34s}{m['cagr_pct']:8.2f}{m['net_cagr_pct']:9.2f}"
              f"{m['vol_pct']:7.2f}{str(m['ret_vol']):>9s}{label:>14s}"
              f"{str(m['sortino']):>9s}{m['max_dd_pct']:8.2f}")

    # B1/B2: every CAGR needs an interval. A 5y point estimate from ~1,254
    # draws is not a precise number.
    print("\nBootstrap 90% intervals (moving block, 21d, 1000 draws):")
    for c in ret:
        bs = bootstrap_stats(ret[c])
        if bs:
            out["funds"][c]["bootstrap"] = bs
            lo, hi = bs["cagr_ci_pct"]
            print(f"  {LABEL[c][:30]:31s} CAGR {out['funds'][c]['cagr_pct']:6.2f}%"
                  f"  [{lo:6.2f}, {hi:6.2f}]")

    # B3/B4: the paired difference is the correct test; separate intervals
    # overlap for same-index vehicles and prove nothing.
    print("\nPaired difference (annualised pp, 90% CI):")
    out["paired_diffs"] = {}
    for label, (a, b) in (("FXAIX - SPY (same index)", ("FXAIX_adj", "SPY_adj")),
                          ("FZROX - VTI (total market)", ("FZROX_adj", "VTI_adj")),
                          ("VTI - VTSAX (same portfolio)", ("VTI_adj", "VTSAX_adj"))):
        pd_ = bootstrap_pair_diff(ret[a], ret[b])
        if pd_:
            # The paired test is on GROSS returns; the fee difference is the only
            # part that is certain in expectation. Report both, because a gross
            # gap can flip sign while the net gap stays positive.
            fee_pp = (MER[b] - MER[a]) * 100.0
            pd_["fee_advantage_pct"] = round(fee_pp, 4)
            pd_["net_point_pct"] = round(pd_["point_pct"] + fee_pp, 4)
            pd_["net_ci_pct"] = (round(pd_["ci_pct"][0] + fee_pp, 4),
                                 round(pd_["ci_pct"][1] + fee_pp, 4))
            out["paired_diffs"][label] = pd_
            lo, hi = pd_["ci_pct"]
            verdict = "distinguishable" if pd_["distinguishable_from_zero"] else "NOT distinguishable"
            print(f"  {label:28s} gross {pd_['point_pct']:+6.3f} [{lo:+.3f},{hi:+.3f}]"
                  f"  fee {fee_pp:+.4f}  NET {pd_['net_point_pct']:+6.3f}  {verdict}")

    # B9: one 5y window can be a single regime. Split it and report both halves,
    # then re-run the paired test inside each half -- if the fee story only holds
    # in one half, it is a regime artefact, not a fee effect.
    split = "2024-11-15"
    cut = next((i for i, d in enumerate(dates) if d >= split), len(dates) // 2)
    cut_ret = max(2, cut - 1)          # ret[c][i] corresponds to dates[i+1]
    print(f"\nSub-periods (split {split}; H1 {dates[0]}..{dates[cut_ret]}, "
          f"H2 {dates[cut_ret+1]}..{dates[-1]}):")
    out["subperiods"] = {"split_date": split, "funds": {}, "paired_diffs": {}}
    print(f"  {'fund':31s}{'H1 CAGR':>10s}{'H2 CAGR':>10s}")
    for c in ret:
        h1, h2 = ret[c][:cut_ret], ret[c][cut_ret:]
        if len(h1) < 30 or len(h2) < 30:
            continue
        c1 = _cagr_of(h1) * 100
        c2 = _cagr_of(h2) * 100
        out["subperiods"]["funds"][c] = {"h1_cagr_pct": round(c1, 2),
                                         "h2_cagr_pct": round(c2, 2),
                                         "h1_n": len(h1), "h2_n": len(h2)}
        print(f"  {LABEL[c][:30]:31s}{c1:10.2f}{c2:10.2f}")

    print("  paired FXAIX - SPY per half:")
    for half, sl in (("H1", slice(0, cut_ret)), ("H2", slice(cut_ret, None))):
        a, b = ret["FXAIX_adj"][sl], ret["SPY_adj"][sl]
        pd_ = bootstrap_pair_diff(a, b, n_boot=500)
        if pd_:
            fee_pp = (MER["SPY_adj"] - MER["FXAIX_adj"]) * 100.0
            pd_["fee_advantage_pct"] = round(fee_pp, 4)
            pd_["net_point_pct"] = round(pd_["point_pct"] + fee_pp, 4)
            out["subperiods"]["paired_diffs"][half] = pd_
            lo, hi = pd_["ci_pct"]
            verdict = ("distinguishable" if pd_["distinguishable_from_zero"]
                       else "NOT distinguishable")
            print(f"    {half}  gross {pd_['point_pct']:+6.3f} [{lo:+.3f},{hi:+.3f}]"
                  f"  fee {fee_pp:+.4f}  NET {pd_['net_point_pct']:+6.3f}  {verdict}")

    print("\nPortfolios (MONTHLY-rebalanced 21d, net of blended MER):")
    ports = {
        "100% SPY (SP500)": ({"SPY_adj": 1.0}, 0.000945),
        "100% VTI (total mkt)": ({"VTI_adj": 1.0}, 0.0003),
        "80/20 SPY/BND": ({"SPY_adj": 0.8, "BND_adj": 0.2}, 0.8 * 0.000945 + 0.2 * 0.0003),
        "60/40 SPY/BND": ({"SPY_adj": 0.6, "BND_adj": 0.4}, 0.6 * 0.000945 + 0.4 * 0.0003),
        "100% SGOV (T-bill)": ({"SGOV_adj": 1.0}, 0.0009),
    }
    out["portfolios"] = {}
    for name, (w, mer) in ports.items():
        # D1: monthly (21 trading day) rebalancing, which is what the original
        # docstring claimed while the code actually rebalanced daily.
        p, _ = portfolio(ret, w, rebal=21, merblend=mer)
        m = add_ratios(metrics(p, mer), rf)
        if set(w) == {CASH_KEY}:
            m["sharpe"] = None
            m["sortino"] = None
            m["ratio_note"] = "cash hurdle (R_f); Sharpe/Sortino undefined"
        out["portfolios"][name] = m
        # A4: the 100%-cash portfolio IS the hurdle; a Sharpe against itself is
        # 0/0 and meaningless, so label it instead of printing -0.006.
        is_cash = set(w) == {CASH_KEY}
        label = "n/a (cash)" if is_cash else str(m["sharpe"])
        print(f"{name:34s}{m['cagr_pct']:8.2f}{m['net_cagr_pct']:9.2f}"
              f"{m['vol_pct']:7.2f}{str(m['ret_vol']):>9s}{label:>14s}"
              f"{str(m['sortino']):>9s}{m['max_dd_pct']:8.2f}")

    # D2/D3: the rebalancing choice is worth real money -- show it rather than
    # assert it. Same 60/40, 5bp round-trip cost on the traded fraction.
    print("\nRebalancing sensitivity (60/40 SPY/BND, 5bp spread):")
    w6040 = {"SPY_adj": 0.6, "BND_adj": 0.4}
    mer6040 = 0.6 * 0.000945 + 0.4 * 0.0003
    out["rebalance_sensitivity"] = {}
    for label, rb in (("buy & hold", None), ("quarterly (63d)", 63),
                      ("monthly (21d)", 21), ("daily (1d)", 1)):
        p, pstats = portfolio(ret, w6040, rebal=rb, spread_bp=5.0)
        m = add_ratios(metrics(p, mer6040), rf)
        out["rebalance_sensitivity"][label] = {**m, **pstats}
        print(f"{label:16s}{m['cagr_pct']:8.2f}{m['vol_pct']:7.2f}"
              f"{str(m['sharpe']):>8s}{m['max_dd_pct']:8.2f}"
              f"{pstats['turnover']:9.2f}{pstats['rebalances']:7d}")

    # F3: forward expectations, opt-in and clearly separated from measurement.
    out["forward_anchors"] = None
    if args.anchors:
        print("\nForward anchors (current, not trailing):")
        a = fetch_anchors()
        out["forward_anchors"] = a
        if a.get("cash_tbill_yield_pct") is not None:
            print(f"  cash (13w T-bill)  {a['cash_tbill_yield_pct']:6.2f}%  asof {a.get('cash_asof')}")
            print(f"    vs trailing SGOV net CAGR {out['funds'][CASH_KEY]['net_cagr_pct']:.2f}%")
        else:
            print(f"  cash anchor UNAVAILABLE: {a.get('cash_error')}")
        if a.get("bnd_ytm_pct") is not None:
            print(f"  BND YTM           {a['bnd_ytm_pct']:6.2f}%  (source: {a.get('bnd_ytm_source')})")
            print(f"    vs trailing BND CAGR     {out['funds']['BND_adj']['cagr_pct']:.2f}%")
        else:
            print(f"  BND YTM UNAVAILABLE: {a.get('bnd_error')}")
        if a.get("cash_stale"):
            print("  WARNING: cash anchor is stale -- do not use it as an expectation")

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nwrote {outp}")


if __name__ == "__main__":
    main()
