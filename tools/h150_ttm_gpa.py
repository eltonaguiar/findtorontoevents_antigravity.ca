#!/usr/bin/env python3
"""H-150 -- quarterly trailing-twelve-month GP/A, with 10-K validation.

Pre-registered spec (H-150): GP/A = (revenue - cost of revenue) / total assets,
taken from the most recent QUARTERLY statement filed STRICTLY before the
rebalance date.

The trap: 10-Q facts mix quarterly (~90 day) and year-to-date (~180/270 day)
durations. Adding a quarterly value to a YTD value produces a plausible-looking
number that is simply wrong. So the numerator here is the sum of the last four
facts whose duration is 80-100 days, with consecutive quarter ends 60-130 days
apart; a quarterly fact is never treated as YTD or vice versa. The denominator is
the latest instantaneous Assets filed strictly before the rebalance date.

Before this signal is used in any backtest, ttm_vs_annual() checks it against the
audited annual 10-K GrossProfit for the same fiscal year end. If the four-quarter
sum does not reproduce the annual number, the framing is wrong and no amount of
backtesting makes it right.

This module does not run a backtest. It produces and checks the signal only.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import random
import sys
import time
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "tools" / "cache" / "sec_companyfacts_q"
OUT = ROOT / "reports" / "h150_ttm_validation.json"
SEC_UA = os.environ.get(
    "SEC_USER_AGENT",
    "findtorontoevents-research/1.0 (research; ops@findtorontoevents.ca)")
COMPANYFACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

QUARTER_LO, QUARTER_HI = 80, 100          # days, a single fiscal quarter
ANNUAL_LO, ANNUAL_HI = 350, 380           # days, a fiscal year
GAP_LO, GAP_HI = 60, 130                  # days between consecutive quarter ends


def _dur(row: dict) -> int | None:
    start, end = row.get("start"), row.get("end")
    if not start or not end:
        return None
    try:
        return (date.fromisoformat(end[:10]) - date.fromisoformat(start[:10])).days
    except ValueError:
        return None


def _dedupe_by_end(rows: list[dict]) -> list[dict]:
    """One row per period end; the latest filing (amendment) wins."""
    best: dict[str, dict] = {}
    for r in sorted(rows, key=lambda x: (x["end"], x["filed"])):
        best[r["end"]] = r
    return [best[k] for k in sorted(best)]


def _tag_rows(companyfacts: dict, taxonomy: str, tag: str, units: set[str]) -> list[dict]:
    node = (companyfacts.get("facts") or {}).get(taxonomy, {}).get(tag) or {}
    out: list[dict] = []
    for unit, arr in (node.get("units") or {}).items():
        if unit not in units or not isinstance(arr, list):
            continue
        for f in arr:
            if not isinstance(f, dict):
                continue
            end, filed, val = f.get("end"), f.get("filed"), f.get("val")
            if not end or not filed or val is None:
                continue
            try:
                v = float(val)
            except (TypeError, ValueError):
                continue
            out.append({"start": f.get("start"), "end": str(end), "filed": str(filed),
                        "val": v, "form": str(f.get("form") or ""),
                        "fy": f.get("fy"), "fp": f.get("fp")})
    return out


def extract(companyfacts: dict) -> dict:
    """Compact, cacheable fact set: quarterly + annual GP, Assets, shares."""
    gp = _tag_rows(companyfacts, "us-gaap", "GrossProfit", {"USD"})
    quarters = [r for r in gp if (d := _dur(r)) is not None and QUARTER_LO <= d <= QUARTER_HI]
    annual = [r for r in gp if (d := _dur(r)) is not None and ANNUAL_LO <= d <= ANNUAL_HI]
    return {
        "quarters": _dedupe_by_end(quarters),
        "annual": _dedupe_by_end(annual),
        "assets": _dedupe_by_end(_tag_rows(companyfacts, "us-gaap", "Assets", {"USD"})),
        "shares": _dedupe_by_end(_tag_rows(
            companyfacts, "dei", "EntityCommonStockSharesOutstanding", {"shares"})),
    }


def _four_quarters(rows: list[dict], until_end: str, until_filed: str | None,
                   window: tuple[str, str] | None = None) -> list[dict] | None:
    """The last four CONSECUTIVE, NON-OVERLAPPING quarterly facts at or before (end, filed).

    Two guards beyond "four rows ending before the date":

    * non-overlap -- a quarter may not start before the previous one ended, or the
      same revenue is counted twice. This is what produced 15-54% "errors" when
      the check was only on the spacing of period ENDS.
    * window -- for validation, the four quarters must actually tile the fiscal
      year they are being compared against (first start at the annual start, last
      end at the annual end), otherwise a missing quarter lets four *older*
      quarters masquerade as this year's TTM.
    """
    usable = [r for r in rows
              if r["end"] <= until_end and (until_filed is None or r["filed"] <= until_filed)]
    if len(usable) < 4:
        return None
    last4 = usable[-4:]
    try:
        for a, b in zip(last4, last4[1:]):
            if not a.get("start") or not b.get("start"):
                return None
            gap = (date.fromisoformat(b["start"][:10])
                   - date.fromisoformat(a["end"][:10])).days
            if gap < 0 or gap > 5:        # overlap double-counts; a hole is not a TTM
                return None
        ends = [date.fromisoformat(r["end"][:10]) for r in last4]
        if any(not (GAP_LO <= (ends[i + 1] - ends[i]).days <= GAP_HI) for i in range(3)):
            return None
        if window is not None:
            w_start, w_end = window
            first = date.fromisoformat(last4[0]["start"][:10])
            last = date.fromisoformat(last4[-1]["end"][:10])
            if abs((first - date.fromisoformat(w_start[:10])).days) > 5:
                return None
            if abs((last - date.fromisoformat(w_end[:10])).days) > 5:
                return None
    except (TypeError, ValueError):
        return None
    return last4


def ttm_gpa_at(facts: dict, asof: str) -> dict | None:
    """Quarterly TTM GP/A, using only facts filed STRICTLY before `asof`."""
    quarters = [r for r in facts["quarters"] if r["filed"] < asof]
    last4 = _four_quarters(quarters, asof, None)
    if last4 is None:
        return None
    assets = [r for r in facts["assets"] if r["filed"] < asof and r["end"] <= asof]
    shares = [r for r in facts["shares"] if r["filed"] < asof]
    if not assets or not shares:
        return None
    a, s = assets[-1], shares[-1]
    if a["val"] <= 0 or s["val"] <= 0:
        return None
    ttm = sum(r["val"] for r in last4)
    return {
        "gpa": ttm / a["val"],
        "ttm_gross_profit": ttm,
        "assets": a["val"],
        "assets_end": a["end"],
        "shares": s["val"],
        "quarter_ends": [r["end"] for r in last4],
    }


def ttm_vs_annual(facts: dict) -> list[dict]:
    """Recompute each audited annual GP from its four quarters.

    Use only quarters filed on or before the 10-K itself, so the comparison is
    against what the filer actually had available, not later restatements.
    """
    pairs: list[dict] = []
    for a in facts["annual"]:
        if not a["val"]:
            continue
        window = (a["start"], a["end"]) if a.get("start") else None
        last4 = _four_quarters(facts["quarters"], a["end"], a["filed"], window=window)
        if last4 is None:
            continue
        ttm = sum(r["val"] for r in last4)
        pairs.append({
            "annual_end": a["end"],
            "annual": a["val"],
            "ttm_four_quarters": ttm,
            "abs_err": abs(ttm - a["val"]),
            "rel_err": abs(ttm - a["val"]) / abs(a["val"]),
        })
    return pairs


def _http_json(url: str, timeout: int = 60) -> dict:
    req = urllib.request.Request(url, headers={
        "User-Agent": SEC_UA, "Accept-Encoding": "gzip, deflate",
        "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    return json.loads(raw)


def _load(cik: int, refresh: bool = False) -> dict | None:
    path = CACHE / f"CIK{cik:010d}.json"
    if path.exists() and not refresh:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:                 # noqa: BLE001 - corrupt cache entry: refetch
            pass
    try:
        cf = _http_json(COMPANYFACTS.format(cik=cik))
    except Exception as exc:              # noqa: BLE001 - 404s are normal and non-fatal
        print(f"  ! CIK {cik:07d}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return None
    compact = extract(cf)
    if not (compact["quarters"] or compact["annual"]):
        return None
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(compact), encoding="utf-8")
    return compact


def _pool() -> list[int]:
    doc = _http_json(TICKERS_URL)
    ciks = set()
    for row in (doc or {}).values():
        try:
            ciks.add(int(row["cik_str"]))
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(ciks)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample-n", type=int, default=250,
                    help="SEC filers to fetch and validate (same seed as H-149)")
    ap.add_argument("--seed", type=int, default=149)
    ap.add_argument("--refresh", action="store_true", help="ignore the compact cache")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    pool = _pool()
    rng = random.Random(args.seed)
    rng.shuffle(pool)
    sample = pool[:args.sample_n]
    print(f"# pool {len(pool)} SEC filers; validating {len(sample)} (seed {args.seed})",
          file=sys.stderr)

    checked = with_annual = with_ttm = 0
    pairs: list[dict] = []
    mismatches: list[dict] = []
    for k, cik in enumerate(sample, 1):
        facts = _load(cik, args.refresh)
        time.sleep(0.12)                  # SEC fair-access: well under 10 req/s
        if not facts:
            continue
        checked += 1
        if facts["annual"]:
            with_annual += 1
        got = ttm_vs_annual(facts)
        if got:
            with_ttm += 1
            pairs.extend(got)
            for row in got:
                if row["rel_err"] > 0.05 and len(mismatches) < 10:
                    mismatches.append({"cik": cik, **row})
        if k % 50 == 0:
            print(f"  .. {k}/{len(sample)} checked {checked}, {with_annual} with annual GP, "
                  f"{len(pairs)} comparable pairs", file=sys.stderr)

    rel = sorted(p["rel_err"] for p in pairs)
    n = len(rel)
    metrics = {
        "companies_checked": checked,
        "companies_with_annual_gp": with_annual,
        "companies_with_ttm": with_ttm,
        "comparable_pairs": n,
        "within_0_1pct": sum(1 for x in rel if x <= 0.001),
        "within_1pct": sum(1 for x in rel if x <= 0.01),
        "within_5pct": sum(1 for x in rel if x <= 0.05),
        "pct_within_1pct": round(100.0 * sum(1 for x in rel if x <= 0.01) / n, 2) if n else None,
        "pct_within_5pct": round(100.0 * sum(1 for x in rel if x <= 0.05) / n, 2) if n else None,
        "median_rel_err": round(rel[n // 2], 6) if n else None,
        "p90_rel_err": round(rel[int(0.9 * (n - 1))], 6) if n else None,
        "max_rel_err": round(rel[-1], 6) if n else None,
    }
    payload = {
        "hypothesis": "H-150 (quarterly TTM GP/A -- signal validation only, no backtest)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "definitions": {
            "quarter": f"duration {QUARTER_LO}-{QUARTER_HI} days",
            "annual": f"duration {ANNUAL_LO}-{ANNUAL_HI} days",
            "gap_between_quarters": f"{GAP_LO}-{GAP_HI} days",
            "ttm": "sum of the last four consecutive quarterly GrossProfit facts",
            "look_ahead_guard": "every fact used only if filed STRICTLY before the as-of date",
            "validation": ("each annual 10-K GrossProfit recomputed from the four quarters filed on "
                           "or before that 10-K, which must tile the fiscal year (first start at "
                           "the annual start, last end at the annual end)"),
            "non_overlap": "each quarter must start no earlier than the previous one ended",
        },
        "sample": {"seed": args.seed, "requested": args.sample_n, "checked": checked},
        "metrics": metrics,
        "prior_loose_rule": {
            "note": ("baseline from the first run, before the non-overlap and tiling guards: four "
                     "quarters chosen only by spacing of period ends, which double-counted "
                     "overlapping facts"),
            "comparable_pairs": 254, "pct_within_1pct": 82.28, "max_rel_err": 2.065078,
        },
        "mismatch_examples": mismatches,
        "pairs": pairs[:1000],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print()
    print(f"TTM vs annual 10-K: {n} comparable pairs from {with_ttm} companies")
    print(f"  within 0.1%: {metrics['within_0_1pct']}   within 1%: {metrics['within_1pct']} "
          f"({metrics['pct_within_1pct']}%)   within 5%: {metrics['within_5pct']} "
          f"({metrics['pct_within_5pct']}%)")
    print(f"  median rel err: {metrics['median_rel_err']}   p90: {metrics['p90_rel_err']}   "
          f"max: {metrics['max_rel_err']}")
    if mismatches:
        print(f"  worst examples (rel err > 5%): {len(mismatches)} shown")
        for m in mismatches[:3]:
            print(f"    CIK {m['cik']:07d} {m['annual_end']}: annual {m['annual']:,.0f} vs TTM "
                  f"{m['ttm_four_quarters']:,.0f} ({m['rel_err']:.1%})")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
