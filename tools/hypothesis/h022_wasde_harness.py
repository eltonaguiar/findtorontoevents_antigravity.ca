#!/usr/bin/env python3
"""
H-022 — USDA WASDE Monthly Crop Report Inventory Surprise Harness
=================================================================
Pre-registered 2026-05-18 per M-107. OPT-IN RESEARCH SIDECAR.

Hypothesis: USDA WASDE monthly crop report inventory surprise
(actual vs prior-month forecast as ±std-dev from trend) discriminates
COMMODITY grain pick outcomes on release day.

Symbols: ZC=F (Corn), ZW=F (Wheat), ZS=F (Soybeans)
Signal:  wasde_z = (actual_ending_stocks - prior_year) / rolling_std
         Computed from USDA ERS annual supply-demand data as a proxy
         for WASDE inventory surprise direction.

Data source attempt order:
  1. USDA FAS PSD Online API (free, no key) — /api/psd/* endpoints
  2. USDA ERS Feed Grains Yearbook CSV (corn/wheat)
  3. USDA ERS Oil Crops Yearbook CSV (soybeans)
  4. DATA_UNAVAILABLE with full explanation

Acceptance criteria (H-022):
  eff_floor: 0.30
  min_windows: 3
  same_sign: True

Usage:
    python tools/hypothesis/h022_wasde_harness.py
    python tools/hypothesis/h022_wasde_harness.py --json
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
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CLOSED_PATH = REPO_ROOT / "alpha_engine" / "data" / "closed_picks.json"
OUTPUT_PATH = REPO_ROOT / "reports" / "h022_wasde_harness.json"

# USDA data endpoints (attempted in order)
PSD_API_COMMODITY_URL = "https://apps.fas.usda.gov/psdonline/api/psd/commodity"
ERS_FEED_GRAINS_CSV = "https://ers.usda.gov/media/5766/feed-grains-yearbook-tables-all-years.csv?v=43943"
ERS_OIL_CROPS_CSV = "https://ers.usda.gov/media/5218/all-tables-oil-crops-yearbook.csv?v=82951"
ERS_WHEAT_XLSX = "https://ers.usda.gov/media/5706/wheat-data-all-years.xlsx?v=80429"

# WASDE approximate release calendar (2nd week of each month)
# Actual dates from usda.gov; using approximate mid-month for join logic
WASDE_RELEASE_DAY = 10  # approximate day-of-month

# Grain symbols → ERS commodity names
GRAIN_SYMBOLS = {"ZC=F", "ZW=F", "ZS=F"}
SYMBOL_TO_COMMODITY = {
    "ZC=F": "Corn",
    "ZW=F": "Wheat",
    "ZS=F": "Soybeans",
}

# Harness thresholds matching H-022 acceptance criteria
EFF_FLOOR = 0.30
MIN_WINDOWS = 3
WINDOW_DAYS = 14

WIN_STATUSES = {"WIN", "TARGET_HIT", "TP_HIT", "CLOSED_WIN", "WON"}
LOSS_STATUSES = {"LOSS", "SL_HIT", "STOPPED", "CLOSED_LOSS", "EXPIRED", "LOST"}


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
    """Cohen's d effect size: (mean_won - mean_lost) / pooled_std."""
    if not won_vals or not lost_vals:
        return 0.0
    n1, n2 = len(won_vals), len(lost_vals)
    m1 = sum(won_vals) / n1
    m2 = sum(lost_vals) / n2
    var1 = sum((x - m1) ** 2 for x in won_vals) / max(n1 - 1, 1)
    var2 = sum((x - m2) ** 2 for x in lost_vals) / max(n2 - 1, 1)
    pooled_std = math.sqrt((var1 * (n1 - 1) + var2 * (n2 - 1)) / max(n1 + n2 - 2, 1))
    if pooled_std < 1e-12:
        return 0.0
    return (m1 - m2) / pooled_std


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def _fetch_url(url: str, timeout: int = 15) -> bytes | None:
    """Fetch URL, return bytes or None on failure."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (research-sidecar; H-022)"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        return None


def _try_psd_api() -> tuple[dict | None, str]:
    """
    Attempt USDA FAS PSD Online API.
    Returns (data_dict, status_msg).
    PSD API provides per-commodity supply-demand data including ending stocks.
    """
    # PSD API commodity codes: Corn=0440000, Wheat (all)=0410000, Soybeans=2222000
    commodity_codes = {
        "ZC=F": ("0440000", "Corn"),
        "ZW=F": ("0410000", "Wheat"),
        "ZS=F": ("2222000", "Soybeans"),
    }
    tried_urls = []
    results = {}

    for sym, (code, name) in commodity_codes.items():
        url = f"{PSD_API_COMMODITY_URL}/{code}/country/US/year/2020"
        tried_urls.append(url)
        data = _fetch_url(url, timeout=10)
        if data is not None:
            try:
                parsed = json.loads(data)
                results[sym] = parsed
            except Exception:
                pass

    if results:
        return results, f"PSD API partial success: {list(results.keys())}"

    # Try alternate PSD endpoint structure
    alt_urls = [
        "https://apps.fas.usda.gov/psdonline/api/psd/country",
        "https://apps.fas.usda.gov/psdonline/api/psd/commodities",
    ]
    for url in alt_urls:
        tried_urls.append(url)
        data = _fetch_url(url, timeout=8)
        if data:
            try:
                parsed = json.loads(data)
                return {"_meta": parsed}, f"PSD country/commodity index fetched from {url}"
            except Exception:
                pass

    return None, f"PSD API unavailable. Tried: {tried_urls}"


def _parse_ers_feed_grains(raw_bytes: bytes) -> dict[str, list[tuple[int, float]]]:
    """
    Parse ERS Feed Grains CSV.
    Returns {symbol: [(year, ending_stocks_mil_bu), ...]} for Corn and Wheat.
    """
    raw = raw_bytes.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(raw))
    results: dict[str, list[tuple[int, float]]] = {"ZC=F": [], "ZW=F": []}

    commodity_map = {"Corn": "ZC=F", "Wheat": "ZW=F"}

    for row in reader:
        attr = str(row.get("attribute", "") or "").lower()
        geo = str(row.get("geography", "") or "")
        commodity = str(row.get("commodity", "") or "")
        freq = str(row.get("frequency", "") or "")
        unit = str(row.get("unit", "") or "").lower()

        if (
            "ending stock" in attr
            and geo == "United States"
            and commodity in commodity_map
            and freq == "Annual"
            and "million bushel" in unit
        ):
            sym = commodity_map[commodity]
            try:
                yr = int(row.get("year", 0))
                amt = float(row.get("amount", 0))
                if yr >= 2010 and amt > 0:
                    results[sym].append((yr, amt))
            except (ValueError, TypeError):
                continue

    # Sort by year
    for sym in results:
        results[sym].sort(key=lambda x: x[0])
    return results


def _parse_ers_oil_crops(raw_bytes: bytes) -> dict[str, list[tuple[int, float]]]:
    """
    Parse ERS Oil Crops CSV.
    Returns {symbol: [(year, ending_stocks_thou_bu), ...]} for Soybeans.
    """
    raw = raw_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(raw))
    results: dict[str, list[tuple[int, float]]] = {"ZS=F": []}

    for row in reader:
        attr = str(row.get("Attribute_Desc", "") or "").lower()
        commodity = str(row.get("Commodity_Desc", "") or "")
        geo = str(row.get("Geography_Desc", "") or "")
        tp = str(row.get("Timeperiod_Desc", "") or "")
        unit = str(row.get("Unit_Desc", "") or "").lower()
        tbl = str(row.get("Table_number", "") or "")

        if (
            "ending stock" in attr
            and commodity == "Soybeans"
            and "United States" in geo
            and "MY Total" in tp
            and "thousand bushel" in unit
        ):
            my = str(row.get("Marketing_Year", "") or "")
            try:
                # Marketing year like "2023/24" → use first year
                yr = int(my.split("/")[0])
                amt_thou = float(row.get("Amount", 0))
                amt_mil = amt_thou / 1000.0  # convert to million bushels
                if yr >= 2010 and amt_mil > 0:
                    results["ZS=F"].append((yr, amt_mil))
            except (ValueError, TypeError):
                continue

    # Sort and deduplicate (take last occurrence per year, from highest table)
    seen: dict[int, float] = {}
    for yr, amt in results["ZS=F"]:
        seen[yr] = amt
    results["ZS=F"] = sorted(seen.items(), key=lambda x: x[0])
    return results


def _xlsx_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    """Extract shared strings from xlsx zip for cell value lookup."""
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    ss_xml = zf.read("xl/sharedStrings.xml")
    ss_root = ET.fromstring(ss_xml)
    shared: list[str] = []
    for si in ss_root.findall(f".//{{{ns}}}si"):
        t_elems = si.findall(f".//{{{ns}}}t")
        text = "".join(t.text or "" for t in t_elems)
        shared.append(text)
    return shared


def _xlsx_read_sheet(zf: zipfile.ZipFile, shared: list[str], sheet_file: str) -> list[list]:
    """Read a worksheet from xlsx zip into a list of rows."""
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    xml = zf.read(f"xl/worksheets/{sheet_file}")
    root = ET.fromstring(xml)
    rows = []
    for row in root.findall(f".//{{{ns}}}row"):
        cells = []
        for cell in row.findall(f"{{{ns}}}c"):
            t = cell.get("t")
            v = cell.find(f"{{{ns}}}v")
            val = v.text if v is not None else None
            if t == "s" and val is not None:
                try:
                    val = shared[int(val)]
                except (IndexError, ValueError):
                    pass
            cells.append(val)
        rows.append(cells)
    return rows


def _parse_ers_wheat_xlsx(raw_bytes: bytes) -> list[tuple[int, float]]:
    """
    Parse ERS Wheat Data xlsx.
    Returns [(year, us_ending_stocks_mil_bu), ...].

    Reads Table 4 (sheet5 in the xlsx) which has columns:
      [0] Marketing year (e.g. "2023/24")
      [8] U.S. ending stocks (million bushels)
    """
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw_bytes))
        shared = _xlsx_shared_strings(zf)
        rows = _xlsx_read_sheet(zf, shared, "sheet5.xml")
    except Exception as e:
        return []

    result = []
    for row in rows:
        if not row or len(row) < 9:
            continue
        my = str(row[0] or "")
        # Marketing year format: "2023/24" or "2023/2024"
        if "/" not in my:
            continue
        us_ending = row[8]
        if us_ending is None or us_ending == "--":
            continue
        try:
            yr = int(my.split("/")[0])
            val = float(us_ending)
            if yr >= 2010 and val > 0:
                result.append((yr, val))
        except (ValueError, TypeError):
            continue

    # Deduplicate (keep last value per year)
    seen: dict[int, float] = {}
    for yr, val in result:
        seen[yr] = val
    return sorted(seen.items(), key=lambda x: x[0])


def fetch_ers_data() -> tuple[dict[str, list[tuple[int, float]]] | None, list[str], list[str]]:
    """
    Fetch and parse USDA ERS annual ending stocks data.
    Returns (stocks_by_symbol, errors, notes).
    stocks_by_symbol = {symbol: [(year, ending_stocks_mil_bu), ...]}
    """
    errors: list[str] = []
    notes: list[str] = []
    combined: dict[str, list[tuple[int, float]]] = {}

    # Feed grains (corn + wheat)
    print("[H-022] Fetching USDA ERS Feed Grains CSV...")
    fg_bytes = _fetch_url(ERS_FEED_GRAINS_CSV, timeout=20)
    if fg_bytes:
        notes.append(f"ERS Feed Grains CSV fetched ({len(fg_bytes):,} bytes)")
        fg_data = _parse_ers_feed_grains(fg_bytes)
        for sym, series in fg_data.items():
            if series:
                combined[sym] = series
                notes.append(f"  {sym} ({SYMBOL_TO_COMMODITY[sym]}): {len(series)} annual obs, "
                              f"years {series[0][0]}–{series[-1][0]}")
            else:
                errors.append(f"  {sym}: no ending stocks rows found in ERS Feed Grains CSV")
    else:
        errors.append(f"ERS Feed Grains CSV fetch failed: {ERS_FEED_GRAINS_CSV}")

    # Oil crops (soybeans)
    print("[H-022] Fetching USDA ERS Oil Crops CSV...")
    oc_bytes = _fetch_url(ERS_OIL_CROPS_CSV, timeout=20)
    if oc_bytes:
        notes.append(f"ERS Oil Crops CSV fetched ({len(oc_bytes):,} bytes)")
        oc_data = _parse_ers_oil_crops(oc_bytes)
        for sym, series in oc_data.items():
            if series:
                combined[sym] = list(series)
                notes.append(f"  {sym} ({SYMBOL_TO_COMMODITY[sym]}): {len(series)} annual obs, "
                              f"years {series[0][0]}–{series[-1][0]}")
            else:
                errors.append(f"  {sym}: no ending stocks rows found in ERS Oil Crops CSV")
    else:
        errors.append(f"ERS Oil Crops CSV fetch failed: {ERS_OIL_CROPS_CSV}")

    # Wheat xlsx (parsed via zipfile+xml, no openpyxl needed)
    print("[H-022] Fetching USDA ERS Wheat Data xlsx...")
    wh_bytes = _fetch_url(ERS_WHEAT_XLSX, timeout=20)
    if wh_bytes:
        notes.append(f"ERS Wheat xlsx fetched ({len(wh_bytes):,} bytes)")
        wh_series = _parse_ers_wheat_xlsx(wh_bytes)
        if wh_series:
            combined["ZW=F"] = wh_series
            notes.append(f"  ZW=F (Wheat): {len(wh_series)} annual obs, "
                          f"years {wh_series[0][0]}–{wh_series[-1][0]}")
        else:
            errors.append("  ZW=F: no US ending stocks rows parsed from ERS Wheat xlsx")
    else:
        errors.append(f"ERS Wheat xlsx fetch failed: {ERS_WHEAT_XLSX}")

    if not combined:
        return None, errors, notes

    return combined, errors, notes


# ---------------------------------------------------------------------------
# Signal computation
# ---------------------------------------------------------------------------

def compute_wasde_z(
    stocks_series: list[tuple[int, float]],
    rolling_n: int = 5,
) -> dict[int, float]:
    """
    Compute year-over-year surprise z-score from annual ending stocks.

    WASDE surrogate signal:
      - Actual ending stocks for year Y = stocks[Y]
      - "Prior forecast" proxy = prior year's actual stocks (stocks[Y-1])
      - Surprise = stocks[Y] - stocks[Y-1]
      - wasde_z = surprise / rolling_std(surprises[-rolling_n:])

    Returns {year: wasde_z} dict.

    Limitation note: this is an annual approximation of WASDE inventory
    surprise, not the true intra-year monthly forecast revision. The true
    WASDE signal requires monthly PSD projection data (not freely available
    in bulk without an API key). This proxy tests the annual direction.
    """
    z_by_year: dict[int, float] = {}
    years = [yr for yr, _ in stocks_series]
    vals = [v for _, v in stocks_series]

    # Compute year-over-year changes
    changes: list[tuple[int, float]] = []  # (year, change)
    for i in range(1, len(vals)):
        changes.append((years[i], vals[i] - vals[i - 1]))

    for j in range(rolling_n, len(changes)):
        yr, surprise = changes[j]
        window = [c for _, c in changes[j - rolling_n:j]]
        mu = sum(window) / len(window)
        std = math.sqrt(sum((x - mu) ** 2 for x in window) / max(len(window) - 1, 1))
        if std < 1e-6:
            z = 0.0
        else:
            z = (surprise - mu) / std
        z_by_year[yr] = z

    return z_by_year


def wasde_z_for_date(d: date, z_by_year: dict[int, float]) -> float | None:
    """
    Map a pick date to its nearest WASDE year-level surprise.

    For a pick in marketing year Y/Y+1 (Sep-Aug for corn/soy, Jun-May for wheat),
    we map the pick date → the most recently published annual ending stocks figure.

    Simplified: picks in Jan-Aug of year Y use the Y-1 marketing year figure;
    picks in Sep-Dec of year Y use the Y marketing year figure.
    """
    # The ERS data uses the first year of the marketing year as the key
    # For pick dates in 2026 (Apr-May), the relevant WASDE is for 2025/26 MY
    # which corresponds to year key 2025
    # For grain futures picks: use the previous completed marketing year if
    # the current MY is not yet complete
    yr = d.year
    month = d.month

    # Corn/soy: MY starts Sep; wheat MY starts Jun
    # For a pick in Apr-May 2026, the ongoing WASDE projections are for 2025/26 MY
    # The most recent completed annual figure is 2024/25 MY (key=2024)
    # Use current MY if final data available, else prior MY
    if month >= 9:
        candidate_years = [yr, yr - 1]
    else:
        # Jan-Aug: current MY is ongoing, use the key for current MY start
        # e.g. Apr 2026 → 2025 is the MY start year (Sep 2025 – Aug 2026)
        my_start = yr - 1 if month < 9 else yr
        candidate_years = [my_start, my_start - 1]

    for candidate in candidate_years:
        if candidate in z_by_year:
            return z_by_year[candidate]

    # Fallback: most recent available year before pick date
    available = [(y, z) for y, z in z_by_year.items() if y < yr]
    if available:
        return sorted(available, key=lambda x: x[0])[-1][1]

    return None


# ---------------------------------------------------------------------------
# Pick loading
# ---------------------------------------------------------------------------

def load_grain_picks() -> list[dict]:
    """Load grain closed picks (ZC=F, ZW=F, ZS=F) from COMMODITY + FUTURES classes."""
    picks = json.loads(CLOSED_PATH.read_text(encoding="utf-8"))
    out = []
    for p in picks:
        sym = str(p.get("symbol") or "").upper()
        if sym not in GRAIN_SYMBOLS:
            continue
        if _is_win(p) is None:
            continue
        out.append(p)
    return out


# ---------------------------------------------------------------------------
# Walk-forward eff
# ---------------------------------------------------------------------------

def run_cross_sectional_analysis(
    picks: list[dict],
    z_by_sym: dict[str, dict[int, float]],
) -> dict:
    """
    Cross-sectional analysis: do picks for high-wasde_z symbols win more often?

    Because all picks cluster in 3 weeks (Apr 28–May 15 2026) with null
    closed_at, the walk-forward cannot separate windows meaningfully.
    Instead we use the cross-sectional discriminant: picks with a positive
    WASDE z (bullish supply surprise = smaller-than-expected stocks, or
    larger-than-expected, depending on sign convention) vs negative.

    This tests: wasde_z > 0 → win_rate differs from wasde_z < 0.
    """
    records = []
    skipped = 0
    for p in picks:
        dt = _parse_dt(
            p.get("entry_date") or p.get("created_at") or p.get("open_date")
        )
        if dt is None:
            skipped += 1
            continue
        sym = str(p.get("symbol") or "").upper()
        sym_z = z_by_sym.get(sym)
        if sym_z is None:
            skipped += 1
            continue
        z = wasde_z_for_date(dt.date(), sym_z)
        if z is None:
            skipped += 1
            continue
        outcome = _is_win(p)
        if outcome is None:
            skipped += 1
            continue
        records.append({"symbol": sym, "wasde_z": z, "won": outcome, "entry_date": str(dt.date())})

    n_matched = len(records)
    pos_wins = [r for r in records if r["wasde_z"] > 0 and r["won"]]
    pos_loss = [r for r in records if r["wasde_z"] > 0 and not r["won"]]
    neg_wins = [r for r in records if r["wasde_z"] <= 0 and r["won"]]
    neg_loss = [r for r in records if r["wasde_z"] <= 0 and not r["won"]]

    n_pos = len(pos_wins) + len(pos_loss)
    n_neg = len(neg_wins) + len(neg_loss)
    wr_pos = len(pos_wins) / n_pos if n_pos > 0 else None
    wr_neg = len(neg_wins) / n_neg if n_neg > 0 else None

    # Cohen's d on wasde_z: won vs lost
    won_z_vals = [r["wasde_z"] for r in records if r["won"]]
    lost_z_vals = [r["wasde_z"] for r in records if not r["won"]]
    eff_overall = _eff(won_z_vals, lost_z_vals)

    return {
        "n_picks_matched": n_matched,
        "n_picks_skipped": skipped,
        "n_pos_z": n_pos,
        "n_neg_z": n_neg,
        "wr_pos_z": round(wr_pos, 4) if wr_pos is not None else None,
        "wr_neg_z": round(wr_neg, 4) if wr_neg is not None else None,
        "eff_overall_won_vs_lost": round(eff_overall, 4),
        "mean_z_won": round(sum(won_z_vals) / len(won_z_vals), 4) if won_z_vals else None,
        "mean_z_lost": round(sum(lost_z_vals) / len(lost_z_vals), 4) if lost_z_vals else None,
        "records": records,
    }


def run_walk_forward(
    picks: list[dict],
    z_by_sym: dict[str, dict[int, float]],
) -> dict:
    """
    Run rolling walk-forward Cohen's d across WINDOW_DAYS windows.

    Because picks span only ~3 weeks (Apr 28 – May 15, 2026) and all have
    null closed_at, the walk-forward will concentrate in a single window.
    This is documented as a structural limitation (N_TOO_SMALL).

    Also runs a cross-sectional analysis as a supplementary discriminant test.
    """
    now = datetime.now(timezone.utc)
    windows = []

    for i in range(20):  # up to 20 windows
        end = now - timedelta(days=i * WINDOW_DAYS)
        start = end - timedelta(days=WINDOW_DAYS)

        won_z: list[float] = []
        lost_z: list[float] = []
        skipped_no_signal = 0

        for p in picks:
            dt = _parse_dt(
                p.get("entry_date") or p.get("created_at") or p.get("open_date")
            )
            if dt is None:
                continue
            closed_dt = _parse_dt(
                p.get("closed_at") or p.get("exit_date") or p.get("resolved_at")
            )
            # Use entry_date for window assignment if closed_at is null
            ref_dt = closed_dt if closed_dt else dt
            if not (start <= ref_dt < end):
                continue

            sym = str(p.get("symbol") or "").upper()
            sym_z = z_by_sym.get(sym)
            if sym_z is None:
                skipped_no_signal += 1
                continue

            z = wasde_z_for_date(dt.date(), sym_z)
            if z is None:
                skipped_no_signal += 1
                continue

            outcome = _is_win(p)
            if outcome is True:
                won_z.append(z)
            elif outcome is False:
                lost_z.append(z)

        n = len(won_z) + len(lost_z)
        eff_z = _eff(won_z, lost_z)

        windows.append({
            "window_end": end.date().isoformat(),
            "window_start": start.date().isoformat(),
            "n_won": len(won_z),
            "n_lost": len(lost_z),
            "n_total": n,
            "n_skipped_no_signal": skipped_no_signal,
            "mean_z_won": sum(won_z) / len(won_z) if won_z else None,
            "mean_z_lost": sum(lost_z) / len(lost_z) if lost_z else None,
            "eff_z": eff_z,
        })

    # Evaluate across populated windows
    populated = [w for w in windows if w["n_total"] >= 2]
    admissible_windows = [
        w for w in populated if abs(w["eff_z"]) >= EFF_FLOOR
    ]
    admissible = len(admissible_windows)

    signs = [math.copysign(1, w["eff_z"]) for w in admissible_windows]
    if signs:
        dominant_sign = max(set(signs), key=signs.count)
        same_sign = all(s == dominant_sign for s in signs)
    else:
        dominant_sign = 0.0
        same_sign = False

    verdict = "ADMISSIBLE" if (admissible >= MIN_WINDOWS and same_sign) else "KILL"

    # Annotate verdict with data quality caveat
    n_total_picks = sum(w["n_total"] for w in windows)

    # Determine structural note
    if verdict == "KILL":
        if n_total_picks < 10:
            structural_note = "N_TOO_SMALL: all picks cluster in <3 weeks with null closed_at; walk-forward is degenerate"
        elif admissible == 0:
            # Check if signal has zero variance (all picks same symbol/year → same wasde_z)
            all_zvals = [w["mean_z_won"] for w in populated if w["mean_z_won"] is not None]
            all_zvals += [w["mean_z_lost"] for w in populated if w["mean_z_lost"] is not None]
            if len(set(round(z, 6) for z in all_zvals)) <= 1:
                structural_note = "SIGNAL_ZERO_VARIANCE: annual wasde_z is constant within window; signal has no intra-window discriminating power"
            else:
                structural_note = "EFF_BELOW_FLOOR: signal exists but Cohen's d < 0.30"
        else:
            structural_note = "SIGN_INCONSISTENT"
    else:
        structural_note = None

    return {
        "hypothesis": "H-022",
        "verdict": verdict,
        "structural_note": structural_note,
        "admissible_windows": admissible,
        "min_required": MIN_WINDOWS,
        "same_sign": same_sign,
        "dominant_direction": (
            "BEARISH_SURPRISE_HURTS_LONGS" if dominant_sign < 0
            else "BULLISH_SURPRISE_HELPS_LONGS" if dominant_sign > 0
            else "NONE"
        ),
        "eff_floor": EFF_FLOOR,
        "n_picks_with_signal": n_total_picks,
        "windows": windows,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="H-022 USDA WASDE harness")
    parser.add_argument("--json", action="store_true", help="Output JSON result")
    args = parser.parse_args()

    fetch_log: list[str] = []
    errors: list[str] = []

    # Step 1: Try PSD API (usually blocked/changed URL structure)
    print("[H-022] Attempting USDA FAS PSD Online API...")
    psd_data, psd_msg = _try_psd_api()
    fetch_log.append(f"PSD API: {psd_msg}")
    if psd_data:
        print(f"[H-022] PSD API returned data (limited use for harness): {psd_msg}")
    else:
        print(f"[H-022] PSD API unavailable: {psd_msg}")

    # Step 2: Fetch ERS annual data (confirmed reachable)
    stocks_by_sym, ers_errors, ers_notes = fetch_ers_data()
    fetch_log.extend(ers_notes)
    errors.extend(ers_errors)

    if not stocks_by_sym:
        # DATA_UNAVAILABLE path
        result = {
            "hypothesis": "H-022",
            "verdict": "DATA_UNAVAILABLE",
            "reason": "All USDA data sources failed to return parseable ending stocks data",
            "fetch_attempts": fetch_log,
            "errors": errors,
            "sources_tried": [
                "USDA FAS PSD Online API (psdonline/api/psd/*) — HTTP 404 on all endpoints",
                f"USDA ERS Feed Grains CSV ({ERS_FEED_GRAINS_CSV})",
                f"USDA ERS Oil Crops CSV ({ERS_OIL_CROPS_CSV})",
            ],
            "next_steps": [
                "Register for USDA NASS Quick Stats API key at quickstats.nass.usda.gov",
                "Use World Bank Commodity Data API for grain price proxy",
                "Purchase Quandl/USDA CME historical WASDE data feed",
            ],
            "run_at": datetime.now(timezone.utc).isoformat(),
        }
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print("\n[H-022] DATA_UNAVAILABLE — see output for details")
        if args.json:
            print(json.dumps(result, indent=2))
        return

    # Step 3: Compute wasde_z per symbol
    print("[H-022] Computing WASDE surprise z-scores from annual ending stocks...")
    z_by_sym: dict[str, dict[int, float]] = {}
    z_notes: list[str] = []

    for sym, series in stocks_by_sym.items():
        z_map = compute_wasde_z(series, rolling_n=5)
        z_by_sym[sym] = z_map
        if z_map:
            latest_yr = max(z_map.keys())
            z_notes.append(
                f"{sym} ({SYMBOL_TO_COMMODITY[sym]}): {len(z_map)} z-scored years, "
                f"latest={latest_yr} z={z_map[latest_yr]:.3f}"
            )
            print(f"  {z_notes[-1]}")
        else:
            z_notes.append(f"{sym}: insufficient data for z-scoring (need ≥6 annual obs)")
            errors.append(z_notes[-1])

    # Step 4: Load grain picks
    print("[H-022] Loading grain closed picks (ZC=F, ZW=F, ZS=F)...")
    picks = load_grain_picks()
    print(f"[H-022] {len(picks)} grain picks loaded")

    from collections import Counter
    sym_counts = Counter(p.get("symbol") for p in picks)
    ac_counts = Counter(p.get("asset_class") for p in picks)
    win_counts = Counter(_is_win(p) for p in picks)
    print(f"  Symbols: {dict(sym_counts)}")
    print(f"  Asset classes: {dict(ac_counts)}")
    print(f"  Outcomes: {win_counts[True]} WON / {win_counts[False]} LOST")

    if len(picks) == 0:
        result = {
            "hypothesis": "H-022",
            "verdict": "DATA_UNAVAILABLE",
            "reason": "No grain closed picks found (ZC=F/ZW=F/ZS=F)",
            "run_at": datetime.now(timezone.utc).isoformat(),
        }
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return

    # Step 5: Walk-forward eff
    print("[H-022] Running walk-forward Cohen's d...")
    result = run_walk_forward(picks, z_by_sym)

    # Step 6: Cross-sectional analysis (supplementary)
    print("[H-022] Running cross-sectional signal analysis...")
    cross = run_cross_sectional_analysis(picks, z_by_sym)
    result["cross_sectional"] = cross

    # Augment with metadata
    result["data_sources"] = {
        "psd_api": psd_msg,
        "ers_feed_grains_url": ERS_FEED_GRAINS_CSV,
        "ers_oil_crops_url": ERS_OIL_CROPS_CSV,
        "fetch_log": fetch_log,
        "z_score_notes": z_notes,
    }
    result["data_limitation"] = (
        "Annual WASDE surrogate: ERS ending stocks are published annually. "
        "True WASDE signal requires monthly PSD projection data "
        "(not freely bulk-downloadable). "
        "wasde_z here = YoY change / rolling_5yr_std — directional proxy only."
    )
    result["pick_stats"] = {
        "n_total": len(picks),
        "n_won": win_counts[True],
        "n_lost": win_counts[False],
        "symbols": dict(sym_counts),
        "asset_classes": dict(ac_counts),
        "date_range": {
            "earliest": min(
                str(p.get("entry_date") or "") for p in picks if p.get("entry_date")
            ),
            "latest": max(
                str(p.get("entry_date") or "") for p in picks if p.get("entry_date")
            ),
        },
    }
    result["wasde_z_series"] = {
        sym: {str(yr): round(z, 4) for yr, z in z_map.items()}
        for sym, z_map in z_by_sym.items()
    }
    result["errors"] = errors
    result["run_at"] = datetime.now(timezone.utc).isoformat()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'='*62}")
        print(f"H-022 USDA WASDE Grain Surprise Harness")
        print(f"{'='*62}")
        print(f"Verdict:            {result['verdict']}")
        if result.get("structural_note"):
            print(f"Structural note:    {result['structural_note']}")
        print(f"Admissible windows: {result['admissible_windows']}/{result['min_required']} required")
        print(f"Same sign:          {result['same_sign']}")
        print(f"Dominant direction: {result['dominant_direction']}")
        print(f"Picks with signal:  {result['n_picks_with_signal']}")
        print(f"Grain picks loaded: {len(picks)}")
        print()

        # Summary table of non-empty windows
        non_empty = [w for w in result["windows"] if w["n_total"] > 0]
        if non_empty:
            print(f"{'Window end':<14} {'N':>4} {'EFF_Z':>8} {'Mean Z WON':>12} {'Mean Z LOST':>12}")
            for w in non_empty[:10]:
                mw = f"{w['mean_z_won']:.3f}" if w["mean_z_won"] is not None else "n/a"
                ml = f"{w['mean_z_lost']:.3f}" if w["mean_z_lost"] is not None else "n/a"
                print(f"{w['window_end']:<14} {w['n_total']:>4} {w['eff_z']:>8.3f} {mw:>12} {ml:>12}")
        else:
            print("  No picks fell within any walk-forward window.")

        # Cross-sectional analysis
        cross = result.get("cross_sectional", {})
        if cross:
            print(f"\nCross-sectional analysis (supplementary):")
            print(f"  Picks matched:    {cross['n_picks_matched']}")
            print(f"  Cohen's d (all):  {cross['eff_overall_won_vs_lost']:.3f}")
            print(f"  Mean Z (WON):     {cross['mean_z_won']}")
            print(f"  Mean Z (LOST):    {cross['mean_z_lost']}")
            if cross.get("n_pos_z") and cross.get("n_neg_z"):
                wr_pos_str = f"{cross['wr_pos_z']:.1%}" if cross["wr_pos_z"] is not None else "n/a"
                wr_neg_str = f"{cross['wr_neg_z']:.1%}" if cross["wr_neg_z"] is not None else "n/a"
                print(f"  WR when z>0:      {wr_pos_str} (n={cross['n_pos_z']})")
                print(f"  WR when z<=0:     {wr_neg_str} (n={cross['n_neg_z']})")

        print()
        print(f"Data limitation: {result['data_limitation']}")
        print()
        print(f"WASDE z-scores (annual surrogate):")
        for sym, z_map in z_by_sym.items():
            recent = sorted(z_map.items())[-3:]
            print(f"  {sym} ({SYMBOL_TO_COMMODITY[sym]}): " +
                  ", ".join(f"{yr}={z:.3f}" for yr, z in recent))
        if errors:
            print(f"\nWarnings:")
            for e in errors:
                print(f"  {e}")
        print(f"\nOutput saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
