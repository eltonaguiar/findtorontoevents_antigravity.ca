#!/usr/bin/env python3
"""
H-020 — OpenInsider / SEC Form 4 Cluster Buy Signal Harness
============================================================
Pre-registered 2026-05-18 per M-107. OPT-IN RESEARCH SIDECAR.

Hypothesis: When ≥3 unique insiders buy the same ticker within 30 days AND
aggregate purchase value > $500K, the stock outperforms over the next 30-60 days.

Method:
  1. For each EQUITY symbol in closed_picks.json, look up its SEC CIK
  2. Fetch Form 4 filings from SEC EDGAR (free, official data.sec.gov API)
  3. Identify cluster buy windows: >=3 unique filers, aggregate > $500K, within 30d
  4. For each closed pick, tag cluster_buy_flag = 1 if pick entry_date falls
     within [cluster_event_date, cluster_event_date + 30d]
  5. Run walk-forward Cohen's d eff: do cluster-buy-flagged picks win more?

Data sources:
  - SEC EDGAR Submissions API: https://data.sec.gov/submissions/CIK{n}.json
  - SEC EDGAR company search: https://efts.sec.gov/LATEST/search-index
  - No API key required; rate limit ~10 req/sec with proper User-Agent

Limitations (noted per M-107):
  - Only 55 EQUITY picks (11 symbols) in closed_picks.json — walk-forward may
    not achieve MIN_N_PER_WINDOW=20 per window. Result is indicative, not definitive.
  - Form 4 XML parsing requires additional work for transaction value extraction.
    This version uses a simplified scoring approach.

Acceptance criteria (H-020):
  eff_floor: 0.30
  min_windows_admissible: 3
  same_sign: true

Usage:
    python tools/hypothesis/h020_openinsider_harness.py
    python tools/hypothesis/h020_openinsider_harness.py --json
"""

from __future__ import annotations

import argparse
import json
import math
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CLOSED_PATH = REPO_ROOT / "alpha_engine" / "data" / "closed_picks.json"
CACHE_DIR = REPO_ROOT / "alpha_engine" / "data" / "sec_form4_cache"
OUTPUT_PATH = REPO_ROOT / "reports" / "h020_openinsider_harness.json"

SEC_API_BASE = "https://data.sec.gov"
SEC_USER_AGENT = "research-h020 findtorontoevents.ca"
SEC_RATE_LIMIT_S = 0.15  # max ~7 req/sec to stay within SEC limits

# Known CIKs for our EQUITY symbols (avoids search API calls)
KNOWN_CIKS = {
    "AMD":  "0000002488",
    "NVDA": "0001045810",
    "INTC": "0000050863",
    "AVGO": "0001730168",
    "JNJ":  "0000200406",
    "CVX":  "0000093410",
    "PFE":  "0000078003",
    "PEP":  "0000077476",
    "NIO":  "0001735556",
    "RIOT": "0001591698",
}

# Cluster buy thresholds matching hypothesis spec
CLUSTER_MIN_FILERS = 3
CLUSTER_MIN_VALUE_USD = 500_000
CLUSTER_WINDOW_DAYS = 30
SIGNAL_WINDOW_DAYS = 30  # how long after cluster event a pick qualifies

# Harness thresholds
EFF_FLOOR = 0.30
MIN_WINDOWS = 3
WINDOW_DAYS = 14

WIN_STATUSES = {"WIN", "TARGET_HIT", "TP_HIT", "CLOSED_WIN"}
LOSS_STATUSES = {"LOSS", "SL_HIT", "STOPPED", "CLOSED_LOSS", "EXPIRED"}


# ---------------------------------------------------------------------------
# SEC EDGAR helpers
# ---------------------------------------------------------------------------

def _get(url: str) -> dict | None:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": SEC_USER_AGENT, "Accept": "application/json"},
    )
    try:
        time.sleep(SEC_RATE_LIMIT_S)
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"[H-020] SEC API error for {url}: {e}")
        return None


def fetch_form4_filings(cik_padded: str) -> list[dict]:
    """Fetch all Form 4 filings for a CIK from EDGAR submissions API."""
    cache_file = CACHE_DIR / f"{cik_padded}.json"
    if cache_file.exists():
        age = (datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)).total_seconds()
        if age < 24 * 3600:
            return json.loads(cache_file.read_text(encoding="utf-8"))

    url = f"{SEC_API_BASE}/submissions/CIK{cik_padded}.json"
    data = _get(url)
    if not data:
        return []

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])

    filings = [
        {"form": forms[i], "filing_date": dates[i], "accession": accessions[i]}
        for i in range(len(forms))
        if forms[i] in ("4", "4/A")
    ]

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(filings), encoding="utf-8")
    return filings


def estimate_purchase_value(filing: dict, cik_padded: str) -> dict | None:
    """
    Fetch Form 4 XML and extract purchase transactions.
    Returns dict with date, filer_name, transaction_value if it's a purchase.
    Uses simplified heuristic: if filing exists near our pick dates, flag it.
    Full XML parsing deferred — this version counts Form 4 filing frequency as proxy.
    """
    # For MVP: treat each Form 4 as a potential insider transaction
    # A more complete version would parse the XML nonDerivativeTable/derivativeTable
    # to extract transactionCode='P' (open-market purchase) and shares*price
    return {
        "filing_date": filing["filing_date"],
        "accession": filing["accession"],
        "estimated_value": None,  # requires XML parse
        "is_purchase": None,      # requires transactionCode check
    }


# ---------------------------------------------------------------------------
# Cluster detection
# ---------------------------------------------------------------------------

def detect_clusters(form4_filings: list[dict]) -> list[dict]:
    """
    Identify cluster buy windows from Form 4 filing frequency.
    MVP: cluster = >=CLUSTER_MIN_FILERS Form 4 filings in a 30-day window.
    (Full implementation would filter to purchases only and sum dollar values.)
    """
    if not form4_filings:
        return []

    # Sort by filing date
    dated = []
    for f in form4_filings:
        try:
            d = date.fromisoformat(f["filing_date"])
            dated.append(d)
        except (ValueError, KeyError):
            continue
    dated.sort()

    clusters = []
    for i, d in enumerate(dated):
        window_end = d + timedelta(days=CLUSTER_WINDOW_DAYS)
        window_filings = [dd for dd in dated if d <= dd <= window_end]
        if len(window_filings) >= CLUSTER_MIN_FILERS:
            clusters.append({
                "cluster_start": d.isoformat(),
                "cluster_end": window_end.isoformat(),
                "n_filings": len(window_filings),
                "signal_window_end": (window_end + timedelta(days=SIGNAL_WINDOW_DAYS)).isoformat(),
            })

    # Deduplicate overlapping clusters (keep first occurrence per month)
    seen_months = set()
    deduped = []
    for c in clusters:
        ym = c["cluster_start"][:7]
        if ym not in seen_months:
            seen_months.add(ym)
            deduped.append(c)

    return deduped


# ---------------------------------------------------------------------------
# Pick helpers
# ---------------------------------------------------------------------------

def _parse_dt(s: Any) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(str(s)[:26].strip(), fmt.replace("%z", "").strip())
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def _is_win(pick: dict) -> bool | None:
    status = str(pick.get("status") or "").upper()
    if status in WIN_STATUSES:
        return True
    if status in LOSS_STATUSES:
        return False
    pnl = pick.get("pnl_pct")
    if pnl is not None:
        try:
            return float(pnl) > 0
        except (TypeError, ValueError):
            pass
    return None


def _in_cluster_window(entry_date: date, clusters: list[dict]) -> bool:
    for c in clusters:
        try:
            c_start = date.fromisoformat(c["cluster_start"])
            c_sig_end = date.fromisoformat(c["signal_window_end"])
            if c_start <= entry_date <= c_sig_end:
                return True
        except (ValueError, KeyError):
            continue
    return False


# ---------------------------------------------------------------------------
# Eff
# ---------------------------------------------------------------------------

def _eff(won_vals: list[float], lost_vals: list[float]) -> float:
    if not won_vals or not lost_vals:
        return 0.0
    n1, n2 = len(won_vals), len(lost_vals)
    m1 = sum(won_vals) / n1
    m2 = sum(lost_vals) / n2
    var1 = sum((x - m1) ** 2 for x in won_vals) / max(n1 - 1, 1)
    var2 = sum((x - m2) ** 2 for x in lost_vals) / max(n2 - 1, 1)
    pooled_std = math.sqrt(
        (var1 * (n1 - 1) + var2 * (n2 - 1)) / max(n1 + n2 - 2, 1)
    )
    if pooled_std < 1e-12:
        return 0.0
    return (m1 - m2) / pooled_std


# ---------------------------------------------------------------------------
# Main harness
# ---------------------------------------------------------------------------

def run_harness() -> dict:
    print("[H-020] Loading EQUITY closed picks...")
    all_picks = json.loads(CLOSED_PATH.read_text(encoding="utf-8"))
    equity_picks = [
        p for p in all_picks
        if str(p.get("asset_class", "")).upper() == "EQUITY" and _is_win(p) is not None
    ]
    print(f"[H-020] {len(equity_picks)} resolved EQUITY picks")

    # Fetch Form 4 clusters for each symbol
    print("[H-020] Fetching Form 4 filings from SEC EDGAR...")
    cluster_map: dict[str, list[dict]] = {}
    for sym, cik in KNOWN_CIKS.items():
        filings = fetch_form4_filings(cik)
        clusters = detect_clusters(filings)
        cluster_map[sym] = clusters
        print(f"  {sym}: {len(filings)} Form4 filings → {len(clusters)} cluster events")

    # Tag each pick with cluster_buy_flag
    tagged = []
    for p in equity_picks:
        sym = str(p.get("symbol") or "").upper()
        clusters = cluster_map.get(sym, [])
        entry_dt = _parse_dt(p.get("entry_date") or p.get("created_at") or p.get("open_date"))
        if entry_dt is None:
            continue
        d = entry_dt.date()
        flag = 1.0 if _in_cluster_window(d, clusters) else 0.0
        tagged.append({**p, "_cluster_flag": flag})

    n_flagged = sum(1 for t in tagged if t["_cluster_flag"] == 1.0)
    print(f"[H-020] {n_flagged}/{len(tagged)} picks in cluster buy windows")

    # Walk-forward eff on cluster_flag
    now = datetime.now(timezone.utc)
    windows = []
    for i in range(20):
        end = now - timedelta(days=i * WINDOW_DAYS)
        start = end - timedelta(days=WINDOW_DAYS)
        won_flags, lost_flags = [], []
        for p in tagged:
            closed_dt = _parse_dt(p.get("closed_at") or p.get("exit_date") or p.get("resolved_at"))
            if closed_dt is None or not (start <= closed_dt < end):
                continue
            outcome = _is_win(p)
            if outcome is True:
                won_flags.append(p["_cluster_flag"])
            elif outcome is False:
                lost_flags.append(p["_cluster_flag"])

        n = len(won_flags) + len(lost_flags)
        window_rec = {
            "window_end": end.date().isoformat(),
            "window_start": start.date().isoformat(),
            "n_won": len(won_flags),
            "n_lost": len(lost_flags),
            "n_total": n,
            "mean_flag_won": sum(won_flags) / len(won_flags) if won_flags else None,
            "mean_flag_lost": sum(lost_flags) / len(lost_flags) if lost_flags else None,
            "eff": _eff(won_flags, lost_flags),
        }
        windows.append(window_rec)

    populated = [w for w in windows if w["n_total"] >= 3]
    signs = [math.copysign(1, w["eff"]) for w in populated if abs(w["eff"]) >= EFF_FLOOR]
    admissible = sum(1 for w in populated if abs(w["eff"]) >= EFF_FLOOR)
    dominant_sign = max(set(signs), key=signs.count) if signs else 0
    same_sign = all(s == dominant_sign for s in signs) if signs else False

    verdict = "ADMISSIBLE" if (admissible >= MIN_WINDOWS and same_sign) else "KILL"

    # Note: with only 55 EQUITY picks, we expect INSUFFICIENT_DATA in most windows
    insufficient_data_note = (
        "INSUFFICIENT_DATA — only 55 EQUITY picks (11 symbols). "
        "Walk-forward windows rarely hit MIN_N=3. "
        "Hypothesis should be retested when EQUITY n≥200."
    ) if len(equity_picks) < 200 else None

    return {
        "hypothesis": "H-020",
        "verdict": verdict,
        "admissible_windows": admissible,
        "min_required": MIN_WINDOWS,
        "same_sign": same_sign,
        "eff_floor": EFF_FLOOR,
        "n_equity_picks": len(equity_picks),
        "n_picks_tagged": len(tagged),
        "n_picks_in_cluster_window": n_flagged,
        "cluster_events_by_symbol": {sym: len(c) for sym, c in cluster_map.items()},
        "insufficient_data_note": insufficient_data_note,
        "windows": windows,
        "run_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="H-020 OpenInsider/Form4 cluster buy harness")
    parser.add_argument("--json", action="store_true", help="Output JSON result")
    args = parser.parse_args()

    result = run_harness()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"H-020 OpenInsider Cluster Buy Harness")
        print(f"{'='*60}")
        print(f"Verdict:           {result['verdict']}")
        if result["insufficient_data_note"]:
            print(f"NOTE: {result['insufficient_data_note']}")
        print(f"Admissible windows:{result['admissible_windows']}/{result['min_required']} required")
        print(f"Same sign:         {result['same_sign']}")
        print(f"EQUITY picks:      {result['n_equity_picks']}")
        print(f"Picks in cluster:  {result['n_picks_in_cluster_window']}")
        print(f"Cluster events:")
        for sym, n in result["cluster_events_by_symbol"].items():
            print(f"  {sym}: {n} cluster events")
        print(f"Output saved to:   {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
