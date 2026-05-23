#!/usr/bin/env python3
"""
H-021 — CFTC COT Small-Speculator Contrarian Signal Harness
==============================================================
Pre-registered per hypothesis_registry. OPT-IN RESEARCH SIDECAR.

Hypothesis: CFTC COT non-reportable (small-speculator) z-score discriminates
COMMODITY pick outcomes. When small specs are extremely long (z>+1.8),
commercials fade them — contrarian SHORT. When small specs extremely short
(z<-1.8), contrarian LONG.

Method:
  1. Fetch CFTC disaggregated futures data for years 2022-2025
  2. Parse CSV, filter to our commodity contracts, compute nr_net_pct
  3. Build rolling 52-week z-score -> nr_z per (symbol, report_date)
  4. Load closed COMMODITY picks, join each pick to nearest COT report date
     within 7 days
  5. Run walk-forward Cohen's d (eff) across 14-day rolling windows
  6. Verdict: ADMISSIBLE if eff >= 0.30, same sign, >= 3 windows

Acceptance criteria (H-021):
  eff_floor: 0.30
  min_windows: 3
  same_sign: True

Usage:
    python tools/hypothesis/h021_cot_smallspec_harness.py
    python tools/hypothesis/h021_cot_smallspec_harness.py --json
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
import urllib.request
import urllib.error
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CLOSED_PATH = REPO_ROOT / "alpha_engine" / "data" / "closed_picks.json"
COT_CACHE_PATH = REPO_ROOT / "alpha_engine" / "data" / "cot_smallspec_cache.json"
OUTPUT_PATH = REPO_ROOT / "reports" / "h021_cot_smallspec_harness.json"

# CFTC disaggregated futures URL pattern
COT_URL_PATTERN = "https://www.cftc.gov/files/dea/history/fut_disagg_txt_{year}.zip"
COT_YEARS = [2022, 2023, 2024, 2025, 2026]

# Key CSV column names (from CFTC disaggregated format)
COL_MARKET = "Market_and_Exchange_Names"
COL_DATE = "Report_Date_as_YYYY-MM-DD"
COL_OI = "Open_Interest_All"
COL_NR_LONG = "NonRept_Positions_Long_All"
COL_NR_SHORT = "NonRept_Positions_Short_All"

# Symbol -> CFTC contract name mapping
SYMBOL_TO_CFTC = {
    "CT=F": "COTTON NO. 2",
    "CL=F": "CRUDE OIL, LIGHT SWEET",
    "NG=F": "NATURAL GAS",
    "ZS=F": "SOYBEANS",
    "ZW=F": "WHEAT-SRW",
    "ZC=F": "CORN",
    "KC=F": "COFFEE C",
    "SI=F": "SILVER",
}

# Build reverse mapping: lowercase partial CFTC name -> symbol
# We use substring matching (case-insensitive)
CFTC_SUBSTRINGS = {sym: name.upper() for sym, name in SYMBOL_TO_CFTC.items()}

# Harness thresholds
EFF_FLOOR = 0.30
MIN_WINDOWS = 3
WINDOW_DAYS = 14
ZSCORE_LOOKBACK_WEEKS = 52  # rolling 52-week z-score

WIN_STATUSES = {"WIN", "TARGET_HIT", "TP_HIT", "CLOSED_WIN"}
LOSS_STATUSES = {"LOSS", "SL_HIT", "STOPPED", "CLOSED_LOSS", "EXPIRED"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_dt(s: Any) -> datetime | None:
    if not s:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
    ):
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


def _eff(won_vals: list[float], lost_vals: list[float]) -> float:
    """Cohen's d: (mean_won - mean_lost) / pooled_std."""
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
# CFTC data fetch & parse
# ---------------------------------------------------------------------------

def _match_symbol(market_name: str) -> str | None:
    """Return our symbol if market_name matches any CFTC contract substring."""
    mn = market_name.upper()
    for sym, cftc_substr in CFTC_SUBSTRINGS.items():
        if cftc_substr in mn:
            return sym
    return None


def _fetch_cot_year(year: int) -> list[dict]:
    """Fetch and parse CFTC disaggregated futures CSV for a given year."""
    url = COT_URL_PATTERN.format(year=year)
    print(f"[H-021] Fetching COT {year} from {url} ...")
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (research-sidecar; H-021)"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw_bytes = resp.read()
    except urllib.error.HTTPError as e:
        print(f"[H-021] HTTP {e.code} for year {year} — skipping")
        return []
    except Exception as e:
        print(f"[H-021] Error fetching year {year}: {e} — skipping")
        return []

    # Unzip
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
            # Find the txt/csv file inside
            names = zf.namelist()
            txt_files = [n for n in names if n.lower().endswith(".txt") or n.lower().endswith(".csv")]
            if not txt_files:
                print(f"[H-021] No .txt in ZIP for year {year}: {names}")
                return []
            fname = txt_files[0]
            content = zf.read(fname).decode("latin-1", errors="replace")
    except Exception as e:
        print(f"[H-021] ZIP parse error for year {year}: {e}")
        return []

    # Parse CSV
    rows = []
    reader = csv.DictReader(io.StringIO(content))
    # Strip whitespace from field names
    reader.fieldnames = [f.strip() if f else f for f in (reader.fieldnames or [])]

    required_cols = {COL_MARKET, COL_DATE, COL_OI, COL_NR_LONG, COL_NR_SHORT}
    # Check if columns exist (handle case variations)
    if reader.fieldnames:
        available = set(reader.fieldnames)
        missing = required_cols - available
        if missing:
            # Try to find closest matches (some years use slightly different names)
            print(f"[H-021] Year {year} — columns available: {list(available)[:10]}...")
            print(f"[H-021] Year {year} — missing cols: {missing}")
            return []

    for row in reader:
        try:
            # Strip whitespace from keys and values
            row = {k.strip(): v.strip() for k, v in row.items() if k}
            market = row.get(COL_MARKET, "")
            sym = _match_symbol(market)
            if sym is None:
                continue
            report_date_str = row.get(COL_DATE, "")
            if not report_date_str:
                continue
            try:
                report_date = date.fromisoformat(report_date_str.strip())
            except ValueError:
                continue

            oi = float(row.get(COL_OI, 0) or 0)
            nr_long = float(row.get(COL_NR_LONG, 0) or 0)
            nr_short = float(row.get(COL_NR_SHORT, 0) or 0)

            if oi <= 0:
                continue

            nr_net = nr_long - nr_short
            nr_net_pct = nr_net / oi

            rows.append({
                "symbol": sym,
                "market": market,
                "report_date": report_date.isoformat(),
                "oi": oi,
                "nr_long": nr_long,
                "nr_short": nr_short,
                "nr_net": nr_net,
                "nr_net_pct": nr_net_pct,
            })
        except (ValueError, TypeError, KeyError):
            continue

    print(f"[H-021] Year {year}: {len(rows)} matching rows parsed")
    return rows


def load_cot_data() -> list[dict]:
    """Load COT data from cache or CFTC, returning list of row dicts."""
    if COT_CACHE_PATH.exists():
        try:
            cached = json.loads(COT_CACHE_PATH.read_text(encoding="utf-8"))
            fetched_at = datetime.fromisoformat(cached.get("fetched_at", "2000-01-01"))
            if fetched_at.tzinfo is None:
                fetched_at = fetched_at.replace(tzinfo=timezone.utc)
            age_h = (datetime.now(timezone.utc) - fetched_at).total_seconds() / 3600
            if age_h < 24:
                rows = cached["data"]
                print(f"[H-021] Using cached COT data ({len(rows)} rows, {age_h:.1f}h old)")
                return rows
        except Exception:
            pass

    all_rows = []
    for year in COT_YEARS:
        rows = _fetch_cot_year(year)
        all_rows.extend(rows)

    print(f"[H-021] Total COT rows across all years: {len(all_rows)}")

    try:
        COT_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        COT_CACHE_PATH.write_text(json.dumps({
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "data": all_rows,
        }, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[H-021] Warning: cache write failed: {e}")

    return all_rows


# ---------------------------------------------------------------------------
# Z-score computation per symbol
# ---------------------------------------------------------------------------

def compute_nr_zseries(cot_rows: list[dict]) -> dict[tuple[str, date], float]:
    """
    Build rolling 52-week z-score of nr_net_pct per symbol.
    Returns {(symbol, report_date): nr_z} dict.
    """
    # Group by symbol
    by_symbol: dict[str, list[tuple[date, float]]] = defaultdict(list)
    for row in cot_rows:
        sym = row["symbol"]
        d = date.fromisoformat(row["report_date"])
        pct = row["nr_net_pct"]
        by_symbol[sym].append((d, pct))

    lookback_days = ZSCORE_LOOKBACK_WEEKS * 7
    z_dict: dict[tuple[str, date], float] = {}

    for sym, series in by_symbol.items():
        series.sort(key=lambda x: x[0])
        dates = [s[0] for s in series]
        vals = [s[1] for s in series]

        for i, (d, v) in enumerate(series):
            window_start = d - timedelta(days=lookback_days)
            window_vals = [vals[j] for j in range(i + 1) if dates[j] >= window_start]
            if len(window_vals) < 5:
                continue
            mu = sum(window_vals) / len(window_vals)
            var = sum((x - mu) ** 2 for x in window_vals) / max(len(window_vals) - 1, 1)
            sigma = math.sqrt(var)
            if sigma < 1e-9:
                z_dict[(sym, d)] = 0.0
            else:
                z_dict[(sym, d)] = (v - mu) / sigma

    return z_dict


# ---------------------------------------------------------------------------
# Pick loading & COT join
# ---------------------------------------------------------------------------

def load_commodity_picks() -> list[dict]:
    """Load closed COMMODITY picks with resolved outcomes."""
    picks = json.loads(CLOSED_PATH.read_text(encoding="utf-8"))
    out = []
    for p in picks:
        ac = str(p.get("asset_class") or "").upper()
        if ac != "COMMODITY":
            continue
        if _is_win(p) is None:
            continue
        out.append(p)
    return out


def _nearest_cot_date(
    pick_date: date,
    sym: str,
    z_dict: dict[tuple[str, date], float],
    max_days: int = 7,
) -> float | None:
    """
    Find the nearest COT report date for the given symbol within max_days of pick_date.
    Returns the nr_z value or None.
    """
    best_z = None
    best_gap = max_days + 1
    for (s, d), z in z_dict.items():
        if s != sym:
            continue
        gap = abs((d - pick_date).days)
        if gap <= max_days and gap < best_gap:
            best_gap = gap
            best_z = z
    return best_z


def enrich_picks_with_cot(
    picks: list[dict],
    z_dict: dict[tuple[str, date], float],
) -> list[dict]:
    """Add nr_z field to each pick by joining to nearest COT report."""
    enriched = []
    matched = 0
    for p in picks:
        sym = p.get("symbol", "")
        if sym not in SYMBOL_TO_CFTC:
            continue  # Only process symbols we have COT data for
        dt = _parse_dt(p.get("entry_date") or p.get("created_at") or p.get("timestamp"))
        if dt is None:
            continue
        pick_date = dt.date()
        nr_z = _nearest_cot_date(pick_date, sym, z_dict)
        if nr_z is None:
            continue
        enriched_p = dict(p)
        enriched_p["nr_z"] = nr_z
        enriched.append(enriched_p)
        matched += 1

    print(f"[H-021] Picks enriched with COT: {matched}/{len(picks)}")
    return enriched


# ---------------------------------------------------------------------------
# Walk-forward eff
# ---------------------------------------------------------------------------

def run_walk_forward(enriched_picks: list[dict]) -> dict:
    """Run rolling 14-day walk-forward Cohen's d on nr_z."""
    now = datetime.now(timezone.utc)
    windows = []

    for i in range(20):  # up to 20 windows = 280 days
        end = now - timedelta(days=i * WINDOW_DAYS)
        start = end - timedelta(days=WINDOW_DAYS)
        won_z, lost_z = [], []

        for p in enriched_picks:
            # Use closed_at or resolved_at as the window membership date
            closed_dt = _parse_dt(
                p.get("closed_at") or p.get("exit_date") or p.get("resolved_at")
            )
            if closed_dt is None:
                # Fall back to entry_date if no exit date
                closed_dt = _parse_dt(p.get("entry_date") or p.get("created_at"))
            if closed_dt is None or not (start <= closed_dt < end):
                continue

            nr_z = p.get("nr_z")
            if nr_z is None:
                continue

            outcome = _is_win(p)
            if outcome is True:
                won_z.append(nr_z)
            elif outcome is False:
                lost_z.append(nr_z)

        n_won = len(won_z)
        n_lost = len(lost_z)
        n_total = n_won + n_lost
        eff_z = _eff(won_z, lost_z)

        window_rec: dict = {
            "window_end": end.date().isoformat(),
            "window_start": start.date().isoformat(),
            "n_won": n_won,
            "n_lost": n_lost,
            "n_total": n_total,
            "mean_nrz_won": sum(won_z) / n_won if won_z else None,
            "mean_nrz_lost": sum(lost_z) / n_lost if lost_z else None,
            "eff_z": eff_z,
        }
        windows.append(window_rec)

    # Admissibility check
    populated = [w for w in windows if w["n_total"] >= 5]
    admissible_windows = [w for w in populated if abs(w["eff_z"]) >= EFF_FLOOR]
    admissible = len(admissible_windows)

    if admissible_windows:
        signs = [math.copysign(1, w["eff_z"]) for w in admissible_windows]
        dominant_sign = max(set(signs), key=signs.count)
        same_sign = all(s == dominant_sign for s in signs)
    else:
        dominant_sign = 0.0
        same_sign = False

    # Determine direction meaning:
    # nr_z > 0 means small specs very long (contrarian = SHORT)
    # If won_z > lost_z (positive eff_z), wins happen when small specs are long
    # → signal is that SHORT picks win when nr_z is high → contrarian SHORT confirmed
    if dominant_sign > 0:
        direction = "CONTRARIAN_SHORT_WHEN_SMALLSPEC_LONG"
    elif dominant_sign < 0:
        direction = "CONTRARIAN_LONG_WHEN_SMALLSPEC_SHORT"
    else:
        direction = "NONE"

    verdict = "ADMISSIBLE" if (admissible >= MIN_WINDOWS and same_sign) else "KILL"

    return {
        "hypothesis": "H-021",
        "verdict": verdict,
        "admissible_windows": admissible,
        "min_required": MIN_WINDOWS,
        "same_sign": same_sign,
        "dominant_direction": direction,
        "eff_floor": EFF_FLOOR,
        "n_picks_with_cot": sum(w["n_total"] for w in windows),
        "windows": windows,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="H-021 COT Small-Speculator harness")
    parser.add_argument("--json", action="store_true", help="Output JSON result")
    args = parser.parse_args()

    # Step 1: Load COT data
    cot_rows = load_cot_data()
    if not cot_rows:
        print("[H-021] ERROR: No COT data loaded. Cannot run harness.")
        sys.exit(1)

    # Step 2: Build z-score series
    print("[H-021] Computing rolling 52-week z-score per symbol...")
    z_dict = compute_nr_zseries(cot_rows)
    symbols_with_z = {sym for (sym, _) in z_dict.keys()}
    print(f"[H-021] Z-score entries: {len(z_dict)} across symbols: {sorted(symbols_with_z)}")

    # Step 3: Load COMMODITY picks
    print("[H-021] Loading COMMODITY closed picks...")
    picks = load_commodity_picks()
    print(f"[H-021] {len(picks)} resolved COMMODITY picks loaded")

    # Step 4: Join picks to COT
    enriched = enrich_picks_with_cot(picks, z_dict)
    if not enriched:
        print("[H-021] ERROR: No picks could be joined to COT data. Cannot run harness.")
        # Still write a result
        result = {
            "hypothesis": "H-021",
            "verdict": "KILL",
            "admissible_windows": 0,
            "min_required": MIN_WINDOWS,
            "same_sign": False,
            "dominant_direction": "NONE",
            "eff_floor": EFF_FLOOR,
            "n_picks_with_cot": 0,
            "windows": [],
            "error": "No picks joined to COT — check symbol mapping or date range",
            "run_at": datetime.now(timezone.utc).isoformat(),
        }
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nVerdict: KILL\nOutput saved to: {OUTPUT_PATH}")
        return

    # Step 5: Walk-forward eff
    print("[H-021] Running walk-forward Cohen's d...")
    result = run_walk_forward(enriched)
    result["total_picks_loaded"] = len(picks)
    result["picks_with_cot_join"] = len(enriched)
    result["cot_rows_fetched"] = len(cot_rows)
    result["cot_z_entries"] = len(z_dict)
    result["run_at"] = datetime.now(timezone.utc).isoformat()

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'='*65}")
        print(f"H-021 COT Small-Speculator Contrarian Harness — COMMODITY")
        print(f"{'='*65}")
        print(f"Verdict:            {result['verdict']}")
        print(f"Admissible windows: {result['admissible_windows']}/{result['min_required']} required")
        print(f"Same sign:          {result['same_sign']}")
        print(f"Dominant direction: {result['dominant_direction']}")
        print(f"Picks with COT:     {result['picks_with_cot_join']}/{result['total_picks_loaded']}")
        print(f"COT rows fetched:   {result['cot_rows_fetched']}")
        print(f"Output saved to:    {OUTPUT_PATH}")

        populated = [w for w in result["windows"] if w["n_total"] >= 1]
        if populated:
            print(f"\n{'Window end':<14} {'N':>5} {'N_W':>5} {'N_L':>5} {'EFF_Z':>8} "
                  f"{'Mean NRZ Won':>13} {'Mean NRZ Lost':>14}")
            print("-" * 70)
            for w in populated[:10]:
                mw = f"{w['mean_nrz_won']:.3f}" if w["mean_nrz_won"] is not None else "n/a"
                ml = f"{w['mean_nrz_lost']:.3f}" if w["mean_nrz_lost"] is not None else "n/a"
                print(
                    f"{w['window_end']:<14} {w['n_total']:>5} {w['n_won']:>5} {w['n_lost']:>5} "
                    f"{w['eff_z']:>8.3f} {mw:>13} {ml:>14}"
                )
        else:
            print("\n[H-021] No windows with data — all picks may be outside COT date range")


if __name__ == "__main__":
    main()
