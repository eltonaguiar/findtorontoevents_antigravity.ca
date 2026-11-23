#!/usr/bin/env python3
"""Point-in-time fundamentals from SEC EDGAR `filed` dates (register item PIT-2a).

THE GAP THIS CLOSES
    The HML test used `period_end + 90 days` as a PROXY for "publicly filed". That is
    an assumption, not data. EDGAR `companyfacts` carries the ACTUAL `filed` date on
    every fact, and the repo's existing adapter parses `end` while discarding `filed`.

WHAT THIS DOES
    1. Fetches `data.sec.gov/api/xbrl/companyfacts/CIK##########.json`.
    2. For each fiscal `end`, keeps the value from the EARLIEST `filed` fact.
    3. Persists a per-ticker PIT history to data/fundamentals_pit/<TICKER>.json.
    4. Reports the MEASURED filing-lag distribution, so the 90-day proxy can be
       replaced by a number instead of a guess.

WHY EARLIEST `filed` AND NOT LATEST -- the trap that matters
    companyfacts can carry several values for the same `end`, stamped with the filing
    they appeared in, including later RESTATEMENTS. Verified on AAPL: the FY2024 and
    FY2025 10-K facts BOTH show filed=2026-11-03, the filing they last appeared in.
    Taking the latest-filed value back-fills a restated number into a period before the
    restatement was public -- look-ahead of the subtlest kind. Earliest-filed is what a
    real-time investor could actually have seen.

COMPLIANCE
    SEC requires a descriptive User-Agent with contact details and asks for <=10 req/s.
    This tool identifies itself, paces at ~6 req/s, and backs off on 429. It is read-only
    against a public API.

Read-only with respect to trading. Not investment advice.

Usage:
    python3 tools/edgar_pit_fundamentals.py --limit 25
    python3 tools/edgar_pit_fundamentals.py --tickers AAPL,MSFT
    python3 tools/edgar_pit_fundamentals.py --report      # lag stats only, no fetch
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "data" / "fundamentals_pit"
EARNINGS = ROOT / "data" / "earnings"
OUT = ROOT / "reports" / "pit_filing_lag.json"

UA = "findtorontoevents-research contact@findtorontoevents.ca"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
TAGS = ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]
PACE_SECONDS = 0.16          # ~6 req/s, under SEC's 10 req/s ceiling
# Lags beyond this are not late filings: they are XBRL-adoption artefacts (a 2006-
# 2007 fiscal year first appears in machine-readable form in a 2009-2010 filing) or
# pre-IPO retrospective disclosures. Measured: the 8 largest lags in a 12-ticker
# sample were ALL 2006-2007 period_ends filed 2009-2010, plus ABNB's 2018 period_end
# filed 2022 (its IPO-year 10-K). Treating those as "late filings" overstates
# look-ahead exposure by ~18x, so they are flagged and excluded from the PIT series.
ARTIFACT_LAG_DAYS = 180
# A NEGATIVE lag (filed before the period end) is an EDGAR mis-tag: the filing
# claims to report a period that had not ended yet. Measured on the 480-name run:
# exactly 1 record in 30,333 (0.003%) -- ROP, period_end 2009-12-31 filed
# 2009-11-02 as a 10-Q. It is a LOOK-AHEAD LEAK (as_of would return future data),
# so the usable window is [0, ARTIFACT_LAG_DAYS] inclusive. The smallest genuine
# lag observed is 16d, so nothing legitimate is lost by requiring >= 0.


def _get(url: str, retries: int = 4) -> dict | None:
    last = ""
    for k in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept": "application/json"})
            return json.loads(urllib.request.urlopen(req, timeout=45).read())
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code == 429:
                time.sleep(2.0 * (k + 1))
                continue
            return None
        except Exception as e:                                # noqa: BLE001
            last = f"{type(e).__name__}"
            time.sleep(0.5)
    print(f"    fetch failed: {last}")
    return None


def cik_map(limit: int | None = None, tickers: list[str] | None = None,
            sample: int | None = None, seed: int = 20261123) -> dict[str, int]:
    d = _get(TICKERS_URL)
    if not d:
        return {}
    out = {}
    for row in d.values():
        t = str(row.get("ticker", "")).upper()
        if not t:
            continue
        out[t] = int(row["cik_str"])
    if tickers:
        return {t: out[t] for t in tickers if t in out}
    syms = sorted(p.name for p in EARNINGS.iterdir()
                  if p.is_dir() and p.name.isupper() and 1 <= len(p.name) <= 5)
    picked = {k: v for k, v in ((t, out.get(t)) for t in syms) if v is not None}
    if sample:
        # `--limit` takes the alphabetically-first N, which is a BIASED subset (A-C
        # names only). Rank by sha256(ticker+seed) instead: deterministic, replayable,
        # and spread across the alphabet. Same seed -> same sample forever.
        ranked = sorted(picked, key=lambda t: hashlib.sha256(
            f"{t}:{seed}".encode()).hexdigest())
        return {t: picked[t] for t in ranked[:sample]}
    if limit:
        picked = dict(sorted(picked.items())[:limit])
    return picked


def is_usable(lag_days: int | None) -> bool:
    """The PIT usability rule, in ONE place.

    Recompute from `lag_days` rather than trusting a stored `usable_for_pit` flag.
    Measured failure: after tightening the rule to exclude negative lags, a report
    run over the cached store still printed the stale `range -59..176d`, because
    the flag had been written under the old rule. A cached derived field silently
    outlives the rule that produced it -- the same class of defect as a hard-coded
    promotion list in a dashboard.
    """
    return lag_days is not None and 0 <= lag_days <= ARTIFACT_LAG_DAYS


def pit_history(companyfacts: dict) -> list[dict]:
    """Per fiscal period: value as FIRST filed, plus the true filing lag."""
    gaap = companyfacts.get("facts", {}).get("us-gaap", {})
    best: dict[str, dict] = {}
    for tag in TAGS:
        node = gaap.get(tag)
        if not node:
            continue
        for unit, facts in node.get("units", {}).items():
            if unit != "USD":
                continue
            for f in facts:
                end, filed, val = f.get("end"), f.get("filed"), f.get("val")
                if not end or not filed or val is None:
                    continue
                cur = best.get(end)
                # EARLIEST filed wins -> value as it first became public
                if cur is None or filed < cur["filed"]:
                    best[end] = {"period_end": end, "filed": filed,
                                 "value": float(val), "form": f.get("form"),
                                 "tag": tag}
    rows = sorted(best.values(), key=lambda r: r["period_end"])
    for r in rows:
        try:
            r["lag_days"] = (date.fromisoformat(r["filed"])
                             - date.fromisoformat(r["period_end"])).days
        except ValueError:
            r["lag_days"] = None
        r["usable_for_pit"] = (r["lag_days"] is not None
                               and 0 <= r["lag_days"] <= ARTIFACT_LAG_DAYS)
    return rows


def as_of(ticker: str, asof: str) -> dict | None:
    """Latest fact PUBLICLY FILED on or before `asof`. The only PIT-safe accessor.

    Uses `filed`, never `period_end`. A fact with filed > asof did not exist for a
    real-time investor on `asof` and must not be returned.
    """
    p = STORE / f"{ticker}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    usable = [r for r in d["history"]
              if is_usable(r.get("lag_days")) and r["filed"] <= asof]
    return usable[-1] if usable else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--sample", type=int, default=None,
                    help="deterministic random sample of N tickers (preferred over "
                         "--limit, which is an alphabetical prefix and therefore biased)")
    ap.add_argument("--seed", type=int, default=20261123)
    ap.add_argument("--tickers", default=None)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()

    if a.report:
        return report()

    tickers = [t.strip().upper() for t in a.tickers.split(",")] if a.tickers else None
    cmap = cik_map(a.limit, tickers, sample=a.sample, seed=a.seed)
    if not cmap:
        print("::error:: could not resolve any CIK")
        return 2
    print(f"resolved {len(cmap)} tickers -> CIK")

    STORE.mkdir(parents=True, exist_ok=True)
    ok, failed = 0, []
    for i, (t, cik) in enumerate(sorted(cmap.items()), 1):
        d = _get(FACTS_URL.format(cik=cik))
        time.sleep(PACE_SECONDS)
        if not d:
            failed.append(t)
            continue
        rows = pit_history(d)
        if not rows:
            failed.append(t)
            continue
        (STORE / f"{t}.json").write_text(json.dumps(
            {"ticker": t, "cik": cik, "retrieved_utc":
             datetime.now(timezone.utc).isoformat(), "history": rows}))
        ok += 1
        if i % 10 == 0:
            print(f"  ...{i}/{len(cmap)}")
    print(f"stored {ok} tickers to {STORE.relative_to(ROOT)}/  (failed: {len(failed)})")
    if failed:
        print(f"  failed sample: {failed[:8]}")
    return report()


def report() -> int:
    files = sorted(STORE.glob("*.json")) if STORE.is_dir() else []
    if not files:
        print("no PIT store yet -- run without --report")
        return 1
    lags, per_ticker, latest_filed_drift = [], [], 0
    artifacts = 0
    genuine_late = 0
    total = 0
    for f in files:
        d = json.loads(f.read_text())
        h = [r for r in d["history"] if r.get("lag_days") is not None]
        if not h:
            continue
        total += len(h)
        artifacts += sum(1 for r in h if not is_usable(r.get("lag_days")))
        # genuine late filers: public LATER than the 90d proxy but not an artefact
        genuine_late += sum(1 for r in h
                            if is_usable(r.get("lag_days")) and r["lag_days"] > 90)
        ls = [r["lag_days"] for r in h if is_usable(r.get("lag_days"))]
        if not ls:
            continue
        lags.extend(ls)
        per_ticker.append({"ticker": d["ticker"], "n_periods": len(ls),
                           "median_lag_days": statistics.median(ls),
                           "max_lag_days": max(ls), "min_lag_days": min(ls)})
    if not lags:
        print("no lag data")
        return 1
    lags.sort()
    n = len(lags)
    pct = lambda q: lags[min(n - 1, int(q * n))]
    la90 = genuine_late

    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source": "SEC EDGAR companyfacts, earliest `filed` per period_end",
        "n_tickers": len(per_ticker),
        "n_periods_total": total,
        "n_periods_usable_for_pit": n,
        "n_artifacts_excluded": artifacts,
        "artifact_rule": f"lag > {ARTIFACT_LAG_DAYS}d treated as XBRL-adoption / "
                         f"pre-IPO artefact, not a late filing; lag < 0 treated as "
                         f"an EDGAR mis-tag and excluded as a look-ahead leak",
        "lag_days": {"median": statistics.median(lags), "p10": pct(0.10),
                     "p25": pct(0.25), "p75": pct(0.75), "p90": pct(0.90),
                     "min": min(lags), "max": max(lags),
                     "mean": round(statistics.mean(lags), 2)},
        "proxy_90d": {
            "periods_filed_after_90d": la90,
            "pct_after_90d": round(la90 / n * 100, 2),
            "note": "GENUINE look-ahead exposure only: periods where the fact was "
                    "not public at period_end+90 and the lag is not an artefact",
            "wasted_days_on_median": round(90 - statistics.median(lags), 1),
            "second_note": "a 90d proxy is CONSERVATIVE for the median period -- it "
                           "waits longer than needed, discarding public information",
        },
        "per_ticker": sorted(per_ticker, key=lambda r: r["ticker"]),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))

    print()
    print(f"MEASURED filing lags: {n} PIT-usable periods across {len(per_ticker)} tickers")
    print(f"  excluded {artifacts} of {total} as XBRL-adoption / pre-IPO artefacts "
          f"(lag > {ARTIFACT_LAG_DAYS}d)")
    print(f"  median {out['lag_days']['median']:.0f}d   p10 {out['lag_days']['p10']}d   "
          f"p90 {out['lag_days']['p90']}d   range {min(lags)}..{max(lags)}d")
    print(f"  GENUINE look-ahead on a 90d proxy: {la90} ({out['proxy_90d']['pct_after_90d']}%)")
    print(f"  a 90d proxy WASTES {out['proxy_90d']['wasted_days_on_median']}d of public "
          f"information on the median period")
    print(f"written: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
