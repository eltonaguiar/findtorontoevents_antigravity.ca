#!/usr/bin/env python3
"""Power analysis for the R4b ETF forward clock.

Pre-registration: docs/preregistration/ETF_TREND_FORWARD_2026-11-23.md
Proposed amendment: docs/preregistration/ETF_TREND_FORWARD_2026-11-23_AMENDMENT-1_PROPOSED.md

WHAT THIS DOES
    Answers one question the pre-registration never asked: given the volatility of the
    frozen 20-ETF universe and the monthly sampling the clock uses, what size of edge
    can 60 monthly records actually detect -- and can the frozen CONFIRM rule ever fire?

WHAT THIS DELIBERATELY DOES NOT DO
    It does not run the momentum rule over history. Running it would consume a trial and
    the pre-registration forbids re-testing this family (its whole value is trial count 1).
    Only the universe's monthly VOLATILITY is read from the cache -- a market-data
    statistic, not a return series of the rule.

Method
    sigma_book = sigma_avg * sqrt((1 + (k-1)*rho) / k)      equal-weight top-k, pairwise rho
    SE(n)      = sigma_book / sqrt(n)                        n monthly observations
    MDE(n)     = (z_{1-a/2} + z_{1-beta}) * SE(n)             80% power, two-sided 5%
    CONFIRM    = point estimate with one-sided 95% lower bound > hurdle
               => requires point >= hurdle + 1.645 * SE(n)

rho is assumed, not measured, because measuring the pairwise correlation of the rule's own
book would mean running the rule. Three values are reported so the conclusion can be checked
for sensitivity to that assumption.

Usage
    python3 tools/r4b_power.py
    python3 tools/r4b_power.py --json
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics as st
import sys
from pathlib import Path
from statistics import NormalDist

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import etf_trend_forward_clock as clock  # noqa: E402  (frozen universe, CACHE, hurdle, k)

N = NormalDist()
ALPHA = 0.05
POWER = 0.80
RHOS = (0.3, 0.5, 0.7)
BASE_RHO = 0.5
CHECKPOINTS = (12, 36, 60, 120)
Z_95 = N.inv_cdf(1 - ALPHA / 2)
Z_80 = N.inv_cdf(POWER)
Z_ONE_SIDED_95 = N.inv_cdf(0.95)


def monthly_closes(sym: str) -> dict[str, float]:
    p = clock.CACHE / f"{sym}_5y.csv"
    out: dict[str, float] = {}
    for row in csv.DictReader(p.open()):
        if row.get("Close"):
            out[row["Date"][:7]] = float(row["Close"])
    return out


def monthly_returns(sym: str) -> list[float]:
    mc = monthly_closes(sym)
    ks = sorted(mc)
    return [mc[ks[i]] / mc[ks[i - 1]] - 1.0 for i in range(1, len(ks))]


def universe_sigma(symbols=None) -> tuple[float, dict[str, float]]:
    """Mean single-instrument monthly sigma across the frozen universe."""
    per: dict[str, float] = {}
    for s in (symbols or clock.UNIVERSE):
        r = monthly_returns(s)
        if len(r) >= 36:
            per[s] = st.stdev(r)
    if not per:
        raise RuntimeError("no series with >= 36 monthly observations")
    return sum(per.values()) / len(per), per


def book_sigma(sig_avg: float, rho: float, k: int | None = None) -> float:
    """Equal-weight top-k book sigma. rho=1 -> no diversification; rho=0 -> 1/sqrt(k)."""
    k = k or clock.TOP_K
    return sig_avg * math.sqrt((1 + (k - 1) * rho) / k)


def standard_error(sig_book: float, n: int) -> float:
    return sig_book / math.sqrt(n)


def mde(sig_book: float, n: int, alpha: float = ALPHA, power: float = POWER) -> float:
    """Minimum detectable effect per month at the given power."""
    z = N.inv_cdf(1 - alpha / 2) + N.inv_cdf(power)
    return z * standard_error(sig_book, n)


def months_needed(sig_book: float, edge: float, alpha: float = ALPHA,
                  power: float = POWER) -> float:
    """Monthly observations needed to detect `edge` per month."""
    z = N.inv_cdf(1 - alpha / 2) + N.inv_cdf(power)
    return (z * sig_book / edge) ** 2


def confirm_threshold(sig_book: float, n: int, hurdle: float | None = None,
                      z: float = Z_ONE_SIDED_95) -> float:
    """Point estimate needed for a one-sided 95% lower bound to clear the hurdle."""
    h = clock.HURDLE if hurdle is None else hurdle
    return h + z * standard_error(sig_book, n)


def refute_threshold(sig_book: float, n: int, hurdle: float | None = None,
                     z: float = Z_ONE_SIDED_95) -> float:
    """Point estimate below which a one-sided 95% upper bound falls under the hurdle."""
    h = clock.HURDLE if hurdle is None else hurdle
    return h - z * standard_error(sig_book, n)


def power_confirm(sig_book: float, n: int, mu: float, hurdle: float | None = None) -> float:
    """P(point >= hurdle + 1.645*SE) when the true monthly edge is `mu`."""
    h = clock.HURDLE if hurdle is None else hurdle
    z = (mu - h) / standard_error(sig_book, n) - Z_ONE_SIDED_95
    return N.cdf(z)


def power_refute(sig_book: float, n: int, mu: float, hurdle: float | None = None) -> float:
    """P(point <= hurdle - 1.645*SE) when the true monthly edge is `mu`."""
    h = clock.HURDLE if hurdle is None else hurdle
    z = -Z_ONE_SIDED_95 - (mu - h) / standard_error(sig_book, n)
    return N.cdf(z)


def analyse() -> dict:
    sig_avg, per = universe_sigma()
    sb = {rho: book_sigma(sig_avg, rho) for rho in RHOS}
    s = sb[BASE_RHO]
    hurdle_m = clock.HURDLE / 12.0
    out = {
        "universe": len(per),
        "monthly_obs_per_series": len(monthly_returns(clock.UNIVERSE[0])),
        "sigma_avg_monthly": sig_avg,
        "sigma_avg_annualised": sig_avg * math.sqrt(12),
        "top_k": clock.TOP_K,
        "hurdle_annual": clock.HURDLE,
        "hurdle_monthly": hurdle_m,
        "base_rho": BASE_RHO,
        "sigma_book_monthly": s,
        "sigma_book_annualised": s * math.sqrt(12),
        "book_sigma_by_rho": {str(k): v for k, v in sb.items()},
        "se_by_n": {str(n): standard_error(s, n) for n in CHECKPOINTS},
        "mde_by_n": {str(n): mde(s, n) for n in CHECKPOINTS},
        "mde_by_rho_and_n": {str(rho): {str(n): mde(v, n) for n in CHECKPOINTS}
                             for rho, v in sb.items()},
        "months_needed": {str(bp): months_needed(s, bp / 10000.0)
                          for bp in (36, 50, 100, 150)},
        "confirm_threshold_monthly": confirm_threshold(s, 60),
        "refute_threshold_monthly": refute_threshold(s, 60),
        "power_confirm_n60": {str(bp): power_confirm(s, 60, bp / 10000.0)
                              for bp in (36, 50, 100, 150)},
        "power_refute_n60": {str(bp): power_refute(s, 60, bp / 10000.0)
                             for bp in (-36, -50, -100)},
        "per_symbol_sigma": per,
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    d = analyse()
    if a.json:
        print(json.dumps(d, indent=2))
        return 0

    print(f"R4b power analysis | {d['universe']} ETFs, {d['monthly_obs_per_series']} monthly obs each")
    print(f"mean single-ETF monthly sigma {d['sigma_avg_monthly']*100:.2f}% "
          f"({d['sigma_avg_annualised']*100:.1f}%/yr)")
    print(f"top-{d['top_k']} equal weight, rho={d['base_rho']}: book sigma "
          f"{d['sigma_book_monthly']*100:.2f}%/mo ({d['sigma_book_annualised']*100:.1f}%/yr)")
    print(f"monthly hurdle {d['hurdle_monthly']*10000:.1f} bp "
          f"({d['hurdle_annual']*100:.2f}%/yr)\n")

    print("MDE per month (80% power, two-sided 5%):")
    hdr = "  rho  sigma_book " + " ".join(f"{'n='+str(n):>9}" for n in CHECKPOINTS)
    print(hdr)
    for rho in RHOS:
        row = " ".join(f"{d['mde_by_rho_and_n'][str(rho)][str(n)]*100:>8.2f}%" for n in CHECKPOINTS)
        print(f"  {rho:>3}  {d['book_sigma_by_rho'][str(rho)]*100:>9.2f}% {row}")

    print("\nmonths needed to detect an edge (rho=0.5):")
    for bp, n in d["months_needed"].items():
        print(f"  {bp:>3} bp/mo : {n:8.1f} months  ({n/12:5.1f} years)")

    print(f"\nAt n=60: SE {standard_error(d['sigma_book_monthly'],60)*10000:.1f} bp/mo")
    print(f"  CONFIRM needs point >= {d['confirm_threshold_monthly']*10000:.1f} bp/mo "
          f"= {d['confirm_threshold_monthly']*12*100:.1f}%/yr")
    print(f"  REFUTE  needs point <= {d['refute_threshold_monthly']*10000:.1f} bp/mo "
          f"= {d['refute_threshold_monthly']*12*100:.1f}%/yr")
    print("  power to CONFIRM: " + ", ".join(
        f"{bp}bp {p*100:.1f}%" for bp, p in d["power_confirm_n60"].items()))
    print("  power to REFUTE : " + ", ".join(
        f"{bp}bp {p*100:.1f}%" for bp, p in d["power_refute_n60"].items()))
    print("\n(no rule was run; only universe volatility was read)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
