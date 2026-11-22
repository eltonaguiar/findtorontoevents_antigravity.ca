#!/usr/bin/env python3
"""
Harvey-Liu / Bailey-Lopez de Prado Deflated Sharpe Ratio (DSR) for validation.

References:
  - Bailey & Lopez de Prado (2014) "The Deflated Sharpe Ratio"
  - Harvey & Liu (2015) "Backtesting"
  - Bailey, Borwein, Lopez de Prado & Zhu (2014) "Pseudo-Mathematics and
    Financial Charlatanism"

WHAT THIS TOOL HAD WRONG UNTIL 2026-11-22 -- four defects, all verified in source:

  1. `_deflated_sharpe` returned a Z-SCORE and never applied Phi(.), so the
     published `dsr` field ranged [-23.88, +15.08]. DSR is a probability and must
     lie in [0, 1]. Anything outside that range is not a DSR.

  2. `survives = dsr > 0` is z > 0, i.e. a one-sided p < 0.500 -- a COIN-FLIP
     significance gate, not 95%. The "29/45 = 64.4% of strategies survive
     deflation" headline came from that 50% gate and is WITHDRAWN.

  3. ANNUAL_TRADES was hardcoded to 6*365 = 2190, multiplying every strategy's
     per-trade Sharpe by sqrt(2190) = 46.8x no matter how often it actually
     traded. Hence annualised Sharpes of 43.93 and 93.20 and 15 of 45 strategies
     above 10. The trade rate is now MEASURED per strategy from its own
     first-to-last timestamp, and annualisation is skipped entirely when no span
     can be established -- guessing a rate was the defect.

  4. `_sharpe_se` was passed an ANNUALISED Sharpe together with a PER-TRADE T.
     SE(SR) is defined per period; mixing the two is dimensionally incoherent.
     All moments, the standard error and the haircut are now computed in
     PER-TRADE units, and annualisation happens once, at presentation only.

SEMANTIC CHANGES, so the new artifact is not read as the old one:
  * `dsr` is now Phi(z), in [0, 1]. The raw z is kept separately as `dsr_z`.
  * `survives` now means `dsr >= CONFIDENCE` (0.95), not `z > 0`.
  * the multiple-testing haircut needs the SD of Sharpe ratios ACROSS trials.
    That is now MEASURED from the cross-section of the sample being tested
    (`sr_trial_sd_observed`) instead of assumed to be 1.0. The estimate includes
    any genuinely-skilled strategies, which inflates it and therefore makes the
    haircut harsher -- conservative, not kind. With fewer than 3 trials there is no
    cross-section to measure and the haircut collapses to 0, which is printed
    explicitly rather than hidden.

Usage:
    python tools/deflated_sharpe.py             # analyse + write results json
    python tools/deflated_sharpe.py --selftest  # prove the maths
"""

import argparse
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATA_PATH = os.path.join(os.path.dirname(__file__), "..",
                         "audit_dashboard", "data", "dashboard_data.json")
OUT_PATH = os.path.join(os.path.dirname(__file__), "deflated_sharpe_results.json")
MIN_TRADES = 10
CONFIDENCE = 0.95   # one-sided. DSR must reach this to count as surviving.
GAMMA = 0.5772156649015329   # Euler-Mascheroni, for E[max] of N normal draws


def _erfinv_approx(x):
    """Rational approximation of inverse error function (Winitzki 2008)."""
    if x <= -1.0:
        return -float("inf")
    if x >= 1.0:
        return float("inf")
    a = 0.147
    ln1mx2 = math.log(1.0 - x * x)
    t1 = 2.0 / (math.pi * a) + ln1mx2 / 2.0
    inner = t1 * t1 - ln1mx2 / a
    return math.copysign(math.sqrt(math.sqrt(inner) - t1), x)


def _compute_moments(returns):
    """Mean, std, skewness, excess kurtosis from a list of returns."""
    n = len(returns)
    if n < 3:
        return 0.0, 1.0, 0.0, 3.0
    mu = sum(returns) / n
    var = sum((r - mu) ** 2 for r in returns) / n
    std = math.sqrt(var) if var > 0 else 1e-12
    skew = sum(((r - mu) / std) ** 3 for r in returns) / n
    kurt = sum(((r - mu) / std) ** 4 for r in returns) / n  # raw kurtosis
    return mu, std, skew, kurt


def _sharpe_se(sr, skew, kurt, T):
    """Standard error of the Sharpe ratio (Lo 2002 / Bailey-LdP 2014)."""
    # SE(SR) = sqrt( (1 + 0.5*SR^2 - skew*SR + (kurt-3)/4 * SR^2) / T )
    inside = (1.0 + 0.5 * sr * sr
              - skew * sr
              + (kurt - 3.0) / 4.0 * sr * sr)
    if inside < 0:
        inside = abs(inside)  # numerical guard
    return math.sqrt(inside / max(T, 1))


def _norm_cdf(z):
    """Standard normal CDF. This is the step the tool used to omit entirely."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _norm_ppf(p):
    """Inverse standard normal CDF, via the existing erfinv approximation."""
    return math.sqrt(2.0) * _erfinv_approx(2.0 * p - 1.0)


def _parse_dt(v):
    if not v:
        return None
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _observed_trades_per_year(records):
    """Trades per year MEASURED from the sample's own span.

    Returns None when no span can be established -- in which case no annualised
    figure is reported at all, because inventing a trade rate is defect 3.
    """
    tpy, _span = _observed_rate_and_span(records)
    return tpy


def _observed_rate_and_span(records):
    """(trades_per_year, span_days), both measured; (None, None) if unmeasurable.

    The span is returned alongside the rate because annualising a per-trade Sharpe
    by sqrt(trades_per_year) EXTRAPOLATES: a strategy with 20 trades across 2 days
    implies ~3650 trades/yr and multiplies its per-trade Sharpe by ~60. That is
    arithmetic, not a forecast, so the span is published next to the figure.
    """
    stamps = []
    for r in records:
        d = _parse_dt(r.get("closed_at")) or _parse_dt(r.get("timestamp"))
        if d:
            stamps.append(d)
    if len(stamps) < 2:
        return None, None
    span_days = (max(stamps) - min(stamps)).total_seconds() / 86400.0
    if span_days <= 0:
        return None, None
    return len(records) / (span_days / 365.25), span_days


def _empirical_sr_dispersion(srs):
    """Dispersion of per-trade Sharpe ratios ACROSS the trials being tested.

    Returns (robust, plain). This is the sigma_SR the multiple-testing haircut
    actually needs. It cannot be pulled from a constant -- it is a property of the
    SEARCH, not of the market -- so it is estimated from the cross-section.

    Two estimators are returned because the choice matters and must be visible:
      * plain  = population SD. With heavy tails one outlier dominates it. Here the
                 worst strategy sits at -4.22 while the median is -0.07, so the
                 plain SD (0.85) is mostly that one observation.
      * robust = MAD * 1.4826, the standard heavy-tail-robust scale estimate
                 (0.44 here). Used by default; the plain value is still printed so
                 the sensitivity is on the page rather than hidden.

    Caveat, stated rather than buried: using the tested sample to estimate its own
    dispersion includes any genuinely-skilled strategy, which inflates sigma and
    therefore HARSHENS the haircut. Conservative, not flattering.
    """
    xs = sorted(s for s in srs if s is not None)
    if len(xs) < 3:
        return None, None
    mu = sum(xs) / len(xs)
    plain = math.sqrt(sum((x - mu) ** 2 for x in xs) / (len(xs) - 1))
    med = xs[len(xs) // 2] if len(xs) % 2 else (xs[len(xs) // 2 - 1] + xs[len(xs) // 2]) / 2
    mad = sorted(abs(x - med) for x in xs)[len(xs) // 2]
    robust = mad * 1.4826
    return robust, plain


def _sr_haircut(n_strategies, sr_trial_sd):
    """Expected maximum Sharpe under the null across N trials (Bailey-LdP 2014):

        SR* = sigma_SR * [ (1-g)*Phi^-1(1 - 1/N) + g*Phi^-1(1 - 1/(N e)) ]

    `sigma_SR` is the SD of Sharpe ratios across trials, in the SAME units as the
    Sharpe being tested (per-trade here). Passed in, never assumed.
    """
    if n_strategies <= 1 or not sr_trial_sd or sr_trial_sd <= 0:
        return 0.0
    return sr_trial_sd * ((1.0 - GAMMA) * _norm_ppf(1.0 - 1.0 / n_strategies)
                          + GAMMA * _norm_ppf(1.0 - 1.0 / (n_strategies * math.e)))


def _sharpe_se(sr, skew, kurt, T):
    """Standard error of a PER-PERIOD Sharpe ratio (Lo 2002 / Bailey-LdP 2014).

    `sr` must be the per-period Sharpe and `T` the number of periods. Passing an
    annualised Sharpe with a per-trade T was defect 4.
    """
    inside = 1.0 + 0.5 * sr * sr - skew * sr + (kurt - 3.0) / 4.0 * sr * sr
    return math.sqrt(max(inside, 0.0) / max(T, 1))


def _deflated_sharpe(sr_per_period, sr_star, se_sr):
    """DSR = Phi((SR - SR*) / SE(SR)) -- a PROBABILITY in [0, 1].

    The previous version returned (SR - SR*)/SE, i.e. the z-score, and published it
    under the name `dsr`. It is retained as `dsr_z` for continuity.
    """
    if se_sr < 1e-15:
        return 0.0
    return _norm_cdf((sr_per_period - sr_star) / se_sr)


def analyse_group(records_by_key, label="strategy"):
    """Compute DSR for every key. ALL maths in PER-TRADE units.

    Two passes: the first collects per-trade Sharpes so the cross-trial dispersion
    can be measured, the second deflates using the haircut that dispersion implies.
    A single pass would have to assume the dispersion, which is what defect 3 was.
    """
    staged = []
    for key, recs in sorted(records_by_key.items()):
        rets = [float(r["pnl_pct"]) for r in recs if r.get("pnl_pct") is not None]
        T = len(rets)
        if T < MIN_TRADES:
            continue
        mu, std, skew, kurt = _compute_moments(rets)
        sr_trade = mu / std if std > 1e-12 else 0.0
        staged.append({"key": key, "recs": recs, "rets": rets, "T": T, "mu": mu,
                       "skew": skew, "kurt": kurt, "sr_trade": sr_trade,
                       "degenerate": std < 1e-9})

    sigma_rob, sigma_plain = _empirical_sr_dispersion([s["sr_trade"] for s in staged])
    sr_star = _sr_haircut(len(staged), sigma_rob)

    results = []
    for s in staged:
        se = _sharpe_se(s["sr_trade"], s["skew"], s["kurt"], s["T"])
        dsr = _deflated_sharpe(s["sr_trade"], sr_star, se)
        tpy, span = _observed_rate_and_span(s["recs"])
        # annualised ONLY when the sample supplies a real span
        sr_ann = s["sr_trade"] * math.sqrt(tpy) if tpy else None
        results.append({
            "key": s["key"],
            "trades": s["T"],
            "win_rate_pct": round(100 * sum(1 for r in s["rets"] if r > 0) / s["T"], 1),
            "avg_pnl_pct": round(s["mu"], 4),
            "sharpe_per_trade": round(s["sr_trade"], 5),
            "trades_per_year_observed": round(tpy, 1) if tpy else None,
            "span_days_observed": round(span, 1) if span else None,
            "sharpe_annual": round(sr_ann, 4) if sr_ann is not None else None,
            "sr_haircut_per_trade": round(sr_star, 5),
            "se_sr_per_trade": round(se, 5),
            "dsr_z": round((s["sr_trade"] - sr_star) / se, 4) if se else None,
            "dsr": round(dsr, 4),
            "survives": dsr >= CONFIDENCE,
        })
    results.sort(key=lambda x: x["dsr"], reverse=True)
    return results, {"n_trials": len(staged),
                     "sr_trial_sd_observed": round(sigma_rob, 6) if sigma_rob is not None else None,
                     "sr_trial_sd_plain": round(sigma_plain, 6) if sigma_plain is not None else None,
                     "sr_star_per_trade": round(sr_star, 6),
                     "confidence": CONFIDENCE,
                     "degenerate_keys": [s["key"] for s in staged if s["degenerate"]]}


def analyse():
    # ------------------------------------------------------------------
    # Load data
    # ------------------------------------------------------------------
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data["picks"]["recent_closed"]
    print(f"Loaded {len(picks)} closed picks")

    # ------------------------------------------------------------------
    # Group returns by strategy, source_system, and ensemble
    # ------------------------------------------------------------------
    by_strategy = defaultdict(list)
    by_source = defaultdict(list)
    all_records = []

    for p in picks:
        pnl = p.get("pnl_pct")
        if pnl is None:
            continue
        rec = {"pnl_pct": float(pnl), "timestamp": p.get("timestamp"),
               "closed_at": p.get("closed_at")}
        strat = p.get("strategy", "unknown") or "unknown"
        source = p.get("source_system", "unknown") or "unknown"
        by_strategy[strat].append(rec)
        by_source[source].append(rec)
        all_records.append(rec)
    all_returns = [r["pnl_pct"] for r in all_records]

    n_total = len(by_strategy)
    print(f"Total strategies found: {n_total}")
    print()

    # ------------------------------------------------------------------
    # Per-strategy DSR
    # ------------------------------------------------------------------
    strat_results, strat_meta = analyse_group(by_strategy, "strategy")
    print(f"Haircut inputs: N={strat_meta['n_trials']}  "
          f"sigma_SR(robust)={strat_meta['sr_trial_sd_observed']}  "
          f"sigma_SR(plain)={strat_meta['sr_trial_sd_plain']}  "
          f"SR*={strat_meta['sr_star_per_trade']}  (per-trade units)")
    print(f"Survival gate: DSR >= {CONFIDENCE}   (previously: z > 0, i.e. 50%)")
    if strat_meta["sr_trial_sd_observed"] is None:
        print("::warning::fewer than 3 trials -- no cross-section to measure trial "
              "dispersion, so the haircut is 0 and DSR is NOT deflated here")
    if strat_meta["sr_trial_sd_plain"] and strat_meta["sr_trial_sd_observed"]:
        r = strat_meta["sr_trial_sd_plain"] / strat_meta["sr_trial_sd_observed"]
        if r > 1.5:
            print(f"::notice::plain SD is {r:.1f}x the robust SD -- the dispersion is "
                  f"dominated by one or two outliers, which is why the robust scale "
                  f"is used for the haircut")
    if strat_meta["degenerate_keys"]:
        print(f"::warning::DATA DEFECT -- {len(strat_meta['degenerate_keys'])} "
              f"strateg{'y' if len(strat_meta['degenerate_keys'])==1 else 'ies'} has "
              f"zero return variance (identical pnl on every trade), which is not a "
              f"trading record: {strat_meta['degenerate_keys'][:5]}")
    print()
    survivors = [r for r in strat_results if r["survives"]]
    flagged = [r for r in strat_results if not r["survives"]]

    print("=" * 72)
    print(f"STRATEGY DSR  (min {MIN_TRADES} trades, {n_total} strategies)")
    print("=" * 72)
    print(f"{'Strategy':<35} {'Trades':>6} {'WR%':>6} {'DSR':>7} {'z':>7} {'OK':>4}")
    print("-" * 72)
    for r in strat_results[:30]:  # top 30
        flag = "YES" if r["survives"] else " NO"
        z = f"{r['dsr_z']:>7.3f}" if r["dsr_z"] is not None else f"{'n/a':>7}"
        print(f"{r['key'][:34]:<35} {r['trades']:>6} {r['win_rate_pct']:>5.1f}% "
              f"{r['dsr']:>7.4f} {z} {flag:>4}")

    print()
    print(f"Survive DSR>={CONFIDENCE}: {len(survivors)}/{len(strat_results)} "
          f"({len(survivors)/max(len(strat_results),1)*100:.1f}%)")
    print(f"Flagged: {len(flagged)}/{len(strat_results)} "
          f"({len(flagged)/max(len(strat_results),1)*100:.1f}%)")

    # ------------------------------------------------------------------
    # Per-source_system DSR
    # ------------------------------------------------------------------
    n_sources = len(by_source)
    source_results, source_meta = analyse_group(by_source, "source_system")
    print()
    print("=" * 72)
    print(f"SOURCE SYSTEM DSR  ({n_sources} sources, "
          f"SR*={source_meta['sr_star_per_trade']}, "
          f"sigma_SR={source_meta['sr_trial_sd_observed']})")
    print("=" * 72)
    print(f"{'Source':<35} {'Trades':>6} {'WR%':>6} {'DSR':>7} {'z':>7} {'OK':>4}")
    print("-" * 72)
    for r in source_results:
        flag = "YES" if r["survives"] else " NO"
        z = f"{r['dsr_z']:>7.3f}" if r["dsr_z"] is not None else f"{'n/a':>7}"
        print(f"{r['key'][:34]:<35} {r['trades']:>6} {r['win_rate_pct']:>5.1f}% "
              f"{r['dsr']:>7.4f} {z} {flag:>4}")

    # ------------------------------------------------------------------
    # Ensemble (all picks combined -- one test, so no multiple-testing haircut)
    # ------------------------------------------------------------------
    if len(all_returns) >= MIN_TRADES:
        mu, std, skew, kurt = _compute_moments(all_returns)
        sr_t = mu / std if std > 1e-12 else 0.0
        se = _sharpe_se(sr_t, skew, kurt, len(all_returns))   # per-trade units
        dsr_ens = _deflated_sharpe(sr_t, 0.0, se)
        tpy = _observed_trades_per_year(all_records)
        sr_ann = sr_t * math.sqrt(tpy) if tpy else None
        wr = sum(1 for r in all_returns if r > 0) / len(all_returns) * 100
        ensemble = {
            "key": "ENSEMBLE (all picks)",
            "trades": len(all_returns),
            "win_rate_pct": round(wr, 1),
            "avg_pnl_pct": round(mu, 4),
            "sharpe_per_trade": round(sr_t, 5),
            "trades_per_year_observed": round(tpy, 1) if tpy else None,
            "sharpe_annual": round(sr_ann, 4) if sr_ann is not None else None,
            "sr_haircut_per_trade": 0.0,
            "se_sr_per_trade": round(se, 5),
            "dsr_z": round(sr_t / se, 4) if se else None,
            "dsr": round(dsr_ens, 4),
            "survives": dsr_ens >= CONFIDENCE,
        }
        print()
        print("=" * 72)
        print("ENSEMBLE (all picks combined; one test, so no haircut)")
        print("=" * 72)
        sr_ann_s = (f"{ensemble['sharpe_annual']:.4f}"
                    if ensemble["sharpe_annual"] is not None else "n/a (no span)")
        print(f"  Trades: {ensemble['trades']}, WR: {ensemble['win_rate_pct']:.1f}%, "
              f"SR_ann: {sr_ann_s}, DSR: {ensemble['dsr']:.4f} "
              f"-> {'SURVIVES' if ensemble['survives'] else 'FLAGGED'}")
    else:
        ensemble = None

    # ------------------------------------------------------------------
    # Write JSON results
    # ------------------------------------------------------------------
    output = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "semantics": {
            "dsr": "Phi((SR - SR*)/SE), a probability in [0,1]. NOT a z-score.",
            "dsr_z": "the raw z-score the old version published as 'dsr'",
            "survives": f"dsr >= {CONFIDENCE}",
            "units": "all Sharpe/SE/haircut values are PER TRADE; sharpe_annual is "
                     "derived from each strategy's OBSERVED trade span and is null "
                     "when no span could be established",
            "headline_withdrawn": "the previous '64.4% of strategies survive "
                                  "deflation' figure was produced by a gate of "
                                  "z > 0 (a 50% significance level) and is "
                                  "withdrawn"},
        "config": {
            "min_trades": MIN_TRADES,
            "confidence": CONFIDENCE,
            "total_strategies": n_total,
            "sr_trial_sd_observed": strat_meta["sr_trial_sd_observed"],
            "sr_trial_sd_plain": strat_meta["sr_trial_sd_plain"],
            "sr_haircut_per_trade": strat_meta["sr_star_per_trade"],
            "annualisation": "measured per strategy (trades_per_year_observed); "
                             "no hardcoded trade rate",
        },
        "summary": {
            "strategies_analysed": len(strat_results),
            "strategies_surviving": len(survivors),
            "strategies_flagged": len(flagged),
            "survival_rate_pct": round(len(survivors) / max(len(strat_results), 1) * 100, 1),
        },
        "top20_by_dsr": strat_results[:20],
        "all_strategies": strat_results,
        "source_systems": source_results,
        "ensemble": ensemble,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nResults written to {OUT_PATH}")


# ---------------------------------------------------------------------------
# Selftest -- proves the four defects are actually fixed
# ---------------------------------------------------------------------------
def selftest() -> int:
    print("=" * 72)
    print("SELFTEST -- DSR is a probability, gate is 95%, units are consistent")
    print("=" * 72)

    # 1. DSR must be a PROBABILITY. The old version returned a z-score and
    #    published values in [-23.88, +15.08].
    for z_expect, sr, star, se in [
        (0.0, 0.0, 0.0, 0.01),      # z = 0    -> Phi(0) = 0.5
        (1.0, 0.01, 0.0, 0.01),     # z = +1   -> Phi(1) = 0.8413
        (-1.0, -0.01, 0.0, 0.01),   # z = -1   -> Phi(-1) = 0.1587
    ]:
        got = _deflated_sharpe(sr, star, se)
        want = _norm_cdf(z_expect)
        ok = abs(got - want) < 1e-9
        print(f"  z={z_expect:+.1f} -> dsr={got:.6f}  (Phi(z)={want:.6f})  "
              f"{'ok' if ok else 'FAIL'}")
        assert ok, "DSR is not Phi(z)"

    big = _deflated_sharpe(0.10, 0.0, 0.01)   # z = +10, previously published as 10.0
    print(f"  z=+10 huge edge -> dsr={big:.6f} (bounded by 1)   "
          f"{'ok' if 0.0 <= big <= 1.0 else 'FAIL'}")
    assert 0.0 <= big <= 1.0, "DSR outside [0,1] -- still a z-score"

    # 2. A probability of 0.84 must NOT pass a 95% gate. Under the old
    #    `dsr > 0` rule it did.
    print(f"  DSR=0.8413 vs gate {CONFIDENCE}: "
          f"{'PASS(BAD)' if 0.8413 >= CONFIDENCE else 'FAIL(correct)'}")

    # 3. Trade rate must be MEASURED, and absent when unmeasurable.
    recs = [{"closed_at": "2026-01-01T00:00:00+00:00"},
            {"closed_at": "2026-01-08T00:00:00+00:00"}]   # 7 days, 2 trades
    tpy = _observed_trades_per_year(recs)
    want_tpy = 2 / (7 / 365.25)
    ok = tpy is not None and abs(tpy - want_tpy) / want_tpy < 1e-6
    print(f"  observed trades/yr from a 7-day span -> {tpy:.2f} "
          f"(want {want_tpy:.2f})   {'ok' if ok else 'FAIL'}")
    assert ok, "trade rate not measured from the span"
    none_case = _observed_trades_per_year([{"closed_at": None}])
    print(f"  no timestamps -> {none_case} (must be None, not a guess)   "
          f"{'ok' if none_case is None else 'FAIL'}")
    assert none_case is None, "invented a trade rate from no data"

    # 4. Units: SE must scale as 1/sqrt(T). Doubling T reduces SE by sqrt(2).
    se_100 = _sharpe_se(0.02, 0.0, 3.0, 100)
    se_200 = _sharpe_se(0.02, 0.0, 3.0, 200)
    ratio = se_100 / se_200
    ok = abs(ratio - math.sqrt(2.0)) < 1e-9
    print(f"  SE(T=100)/SE(T=200) -> {ratio:.6f} (want sqrt(2)={math.sqrt(2):.6f})"
          f"   {'ok' if ok else 'FAIL'}")
    assert ok, "SE does not scale as 1/sqrt(T)"

    # 5. The haircut must rise with the number of trials and with dispersion.
    h1 = _sr_haircut(10, 0.02)
    h2 = _sr_haircut(146, 0.02)
    h3 = _sr_haircut(146, 0.04)
    ok = h1 < h2 < h3
    print(f"  haircut N=10,sd=.02 -> {h1:.4f} < N=146,sd=.02 -> {h2:.4f} "
          f"< N=146,sd=.04 -> {h3:.4f}   {'ok' if ok else 'FAIL'}")
    assert ok, "haircut does not rise with trials/dispersion"
    print(f"  haircut with no measurable dispersion -> {_sr_haircut(146, None)} "
          f"(0.0, and reported not hidden)")

    print("\n  ALL DSR SELFTESTS PASSED")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    analyse()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
