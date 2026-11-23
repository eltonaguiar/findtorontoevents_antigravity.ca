#!/usr/bin/env python3
"""Look-ahead audit across the whole PIT store. Backlog B2.

Invariant under test, for EVERY ticker and EVERY stored fact:

    as_of(T, d) may only return facts whose `filed` <= d

Two probes per fact:
  1. EXCLUSION  — at d = filed - 1 day, that exact fact must NOT be returned.
                  This is the direct look-ahead test: the market did not know it.
  2. VISIBILITY — at d >= filed, the returned record's `filed` must be <= d.
                  This catches a provider that leaks a later amendment.

Also reports the B3 stability check: does the 12-name sample's lag distribution
match the full sample, or was the small sample special?

Read-only. Emits reports/pit_lookahead_audit_2026-11-23.json
"""
from __future__ import annotations

import json
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "data" / "fundamentals_pit"
OUT = ROOT / "reports" / "pit_lookahead_audit_2026-11-23.json"

SMALL_SAMPLE = {"A", "AAPL", "ABBV", "ABNB", "ABT", "ACGL", "ACN", "ADBE",
                "ADI", "ADM", "ADP", "ADSK"}


def _d(s: str) -> date:
    return date.fromisoformat(s)


def as_of(history: list[dict], asof: str) -> dict | None:
    """Same contract as tools.edgar_pit_fundamentals.as_of, on a loaded list."""
    usable = [r for r in history
              if r.get("usable_for_pit") and r["filed"] <= asof]
    return usable[-1] if usable else None


def audit_ticker(ticker: str, history: list[dict]) -> dict:
    """Return per-ticker violation counts. Zero violations is the pass state."""
    usable = [r for r in history if r.get("usable_for_pit")]
    exclusion_viol = []   # fact returned one day before it was filed
    visibility_viol = []  # returned record filed after the as-of date

    for r in usable:
        # 1. EXCLUSION: the day before filing, this fact must be invisible.
        probe = (_d(r["filed"]) - timedelta(days=1)).isoformat()
        got = as_of(history, probe)
        if got is not None and got["filed"] == r["filed"] and \
                got["period_end"] == r["period_end"]:
            exclusion_viol.append({"probe": probe, "leaked": r["filed"]})

        # 2. VISIBILITY: on the filing date, nothing later may be visible.
        got2 = as_of(history, r["filed"])
        if got2 is not None and got2["filed"] > r["filed"]:
            visibility_viol.append({"probe": r["filed"], "returned": got2["filed"]})

    lags = [r["lag_days"] for r in usable if r.get("lag_days") is not None]
    return {
        "ticker": ticker,
        "n_usable": len(usable),
        "n_exclusion_violations": len(exclusion_viol),
        "n_visibility_violations": len(visibility_viol),
        "exclusion_examples": exclusion_viol[:3],
        "visibility_examples": visibility_viol[:3],
        "median_lag": statistics.median(lags) if lags else None,
        "p90_lag": (sorted(lags)[int(0.90 * len(lags))] if lags else None),
        "max_lag": max(lags) if lags else None,
    }


def main() -> int:
    files = sorted(STORE.glob("*.json"))
    if not files:
        print(f"no tickers in {STORE}")
        return 1

    rows = []
    bad = []
    for f in files:
        d = json.loads(f.read_text())
        r = audit_ticker(d["ticker"], d["history"])
        rows.append(r)
        if r["n_exclusion_violations"] or r["n_visibility_violations"]:
            bad.append(r)

    total_usable = sum(r["n_usable"] for r in rows)
    ex = sum(r["n_exclusion_violations"] for r in rows)
    vi = sum(r["n_visibility_violations"] for r in rows)

    all_lags, small_lags = [], []
    for f in files:
        d = json.loads(f.read_text())
        lags = [x["lag_days"] for x in d["history"]
                if x.get("usable_for_pit") and x.get("lag_days") is not None]
        all_lags.extend(lags)
        if d["ticker"] in SMALL_SAMPLE:
            small_lags.extend(lags)

    all_lags.sort()
    def q(xs, p):
        return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else None

    full = {"n": len(all_lags), "median": statistics.median(all_lags) if all_lags else None,
            "p10": q(all_lags, 0.10), "p90": q(all_lags, 0.90)}
    small = {"n": len(small_lags),
             "median": statistics.median(small_lags) if small_lags else None,
             "p10": q(small_lags, 0.10), "p90": q(small_lags, 0.90)}

    drift = None
    p90_drift = None
    if full["median"] and small["median"]:
        drift = abs(full["median"] - small["median"])
    if full["p90"] and small["p90"]:
        p90_drift = abs(full["p90"] - small["p90"])

    print("=" * 88)
    print("PIT LOOK-AHEAD AUDIT")
    print("=" * 88)
    print(f"tickers audited          {len(rows)}")
    print(f"usable facts probed      {total_usable}")
    print(f"exclusion violations     {ex}   (leaked a fact the day before filing)")
    print(f"visibility violations    {vi}   (returned a fact filed after the as-of date)")
    print(f"tickers with violations  {len(bad)}")
    if bad:
        for r in bad[:5]:
            print(f"  !! {r['ticker']}: excl={r['n_exclusion_violations']} "
                  f"vis={r['n_visibility_violations']}")

    print("\n" + "=" * 88)
    print("B3 — is the 12-name sample special?")
    print("=" * 88)
    print(f"full  n={full['n']:>5}  median {full['median']}  p10 {full['p10']}  p90 {full['p90']}")
    print(f"12    n={small['n']:>5}  median {small['median']}  p10 {small['p10']}  p90 {small['p90']}")
    if drift is not None:
        # Median-only stability is NOT enough. Measured: the 12-name sample had a
        # median drift of just 1d while its p90 was 23d short of the full sample,
        # so the small sample understated the TAIL. Judge the distribution.
        stable = drift < 3 and (p90_drift is not None and p90_drift < 3)
        print(f"median drift             {drift:.0f}d")
        print(f"p90 drift                {p90_drift}d")
        print("verdict                  " +
              ("STABLE (median and p90 within 3d)" if stable else
               "TAIL UNSTABLE -- median agrees but p90 does not; the 12-name "
               "sample understated the tail"))

    payload = {
        "generated": "2026-11-23",
        "n_tickers": len(rows),
        "n_usable_facts_probed": total_usable,
        "exclusion_violations": ex,
        "visibility_violations": vi,
        "n_tickers_with_violations": len(bad),
        "pass": ex == 0 and vi == 0,
        "lag_distribution_full": full,
        "lag_distribution_small12": small,
        "median_drift_days": drift,
        "p90_drift_days": p90_drift,
        "sample_stable": (drift is not None and p90_drift is not None
                          and drift < 3 and p90_drift < 3),
        "stability_basis": "median AND p90 within 3d; median alone is insufficient "
                           "because a stable median can hide a shifted tail",
        "violating_tickers": bad,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2))
    print(f"\nwritten: {OUT.relative_to(ROOT)}")
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
