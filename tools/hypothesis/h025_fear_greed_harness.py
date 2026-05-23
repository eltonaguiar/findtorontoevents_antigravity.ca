#!/usr/bin/env python3
"""
H-025 — Alternative.me Fear & Greed Contrarian Signal Harness
==============================================================
Pre-registered 2026-05-18 per M-107. OPT-IN RESEARCH SIDECAR.

Hypothesis: Alternative.me Fear & Greed score (0-100) discriminates
CRYPTO pick outcomes. Extreme Fear (score<25) → mean-reversion LONG edge.
Extreme Greed (score>75) → SHORT caution filter.

Method:
  1. Fetch 2yr daily F&G from api.alternative.me/fng/?limit=730 (free, no key)
  2. For each CRYPTO closed pick, join F&G score at pick's entry_date
  3. Normalise to z-score over a 90-day rolling window
  4. Run walk-forward Cohen's d (eff) across 14-day rolling windows
  5. Admissible if eff >= 0.30 in same direction across >= 3 windows

Acceptance criteria (from hypothesis_registry.json H-025):
  eff_floor: 0.30
  min_windows_admissible: 3
  same_sign: true
  cost_survival_min: 0.60

Usage:
    python tools/hypothesis/h025_fear_greed_harness.py
    python tools/hypothesis/h025_fear_greed_harness.py --json
    python tools/hypothesis/h025_fear_greed_harness.py --asset-class CRYPTO
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.request
import urllib.error
from collections import defaultdict
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CLOSED_PATH = REPO_ROOT / "alpha_engine" / "data" / "closed_picks.json"
CACHE_PATH = REPO_ROOT / "alpha_engine" / "data" / "feargreed_cache.json"
OUTPUT_PATH = REPO_ROOT / "reports" / "h025_fear_greed_harness.json"

FG_API_URL = "https://api.alternative.me/fng/?limit=730"
FG_CACHE_TTL_HOURS = 12

# Harness thresholds matching H-025 acceptance criteria
EFF_FLOOR = 0.30
MIN_WINDOWS = 3
WINDOW_DAYS = 14
ZSCORE_LOOKBACK = 90  # days for rolling z-score normalisation

WIN_STATUSES = {"WIN", "TARGET_HIT", "TP_HIT", "CLOSED_WIN"}
LOSS_STATUSES = {"LOSS", "SL_HIT", "STOPPED", "CLOSED_LOSS", "EXPIRED"}


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def _fetch_fg_fresh() -> list[dict]:
    """Fetch Fear & Greed history from Alternative.me. Returns list of dicts."""
    req = urllib.request.Request(
        FG_API_URL,
        headers={"User-Agent": "Mozilla/5.0 (research-sidecar; H-025)"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        payload = json.loads(r.read())
    return payload["data"]


def load_fg_series() -> dict[date, float]:
    """Return {date: fg_score} dict from cache or API."""
    # Check cache freshness
    if CACHE_PATH.exists():
        try:
            cached = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            ts = datetime.fromisoformat(cached.get("fetched_at", "2000-01-01"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
            if age_h < FG_CACHE_TTL_HOURS:
                raw = cached["data"]
                print(f"[H-025] Using cached F&G ({len(raw)} entries, {age_h:.1f}h old)")
                return _parse_fg(raw)
        except Exception:
            pass

    print("[H-025] Fetching F&G from Alternative.me...")
    raw = _fetch_fg_fresh()
    # Save to cache
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps({
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "data": raw,
        }, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[H-025] Warning: cache write failed: {e}")
    return _parse_fg(raw)


def _parse_fg(raw: list[dict]) -> dict[date, float]:
    """Convert API list to {date: score} dict."""
    result = {}
    for entry in raw:
        try:
            ts = int(entry["timestamp"])
            d = datetime.fromtimestamp(ts, tz=timezone.utc).date()
            score = float(entry["value"])
            result[d] = score
        except (KeyError, ValueError, TypeError):
            continue
    return result


# ---------------------------------------------------------------------------
# Z-score normalisation
# ---------------------------------------------------------------------------

def compute_fg_zseries(fg_by_date: dict[date, float]) -> dict[date, float]:
    """Rolling 90-day z-score of FG score for each day in the series."""
    sorted_dates = sorted(fg_by_date.keys())
    z_by_date: dict[date, float] = {}
    for i, d in enumerate(sorted_dates):
        # Use up to ZSCORE_LOOKBACK prior days (inclusive)
        window_start = d - timedelta(days=ZSCORE_LOOKBACK)
        window_vals = [fg_by_date[dd] for dd in sorted_dates[:i+1]
                       if dd >= window_start]
        if len(window_vals) < 10:
            continue  # Not enough history for z-score
        mu = sum(window_vals) / len(window_vals)
        var = sum((v - mu) ** 2 for v in window_vals) / max(len(window_vals) - 1, 1)
        sigma = math.sqrt(var)
        if sigma < 1e-6:
            z_by_date[d] = 0.0
        else:
            z_by_date[d] = (fg_by_date[d] - mu) / sigma
    return z_by_date


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


def load_picks(asset_class: str) -> list[dict]:
    """Load closed picks for the given asset class."""
    picks = json.loads(CLOSED_PATH.read_text(encoding="utf-8"))
    out = []
    for p in picks:
        ac = str(p.get("asset_class") or "").upper()
        if ac != asset_class.upper():
            continue
        if _is_win(p) is None:
            continue
        out.append(p)
    return out


# ---------------------------------------------------------------------------
# Eff computation
# ---------------------------------------------------------------------------

def _eff(won_vals: list[float], lost_vals: list[float]) -> float:
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


def run_walk_forward(
    picks: list[dict],
    fg_by_date: dict[date, float],
    z_by_date: dict[date, float],
) -> dict:
    """Run rolling walk-forward eff across WINDOW_DAYS windows."""
    now = datetime.now(timezone.utc)
    windows = []
    for i in range(20):  # up to 20 windows = 280 days
        end = now - timedelta(days=i * WINDOW_DAYS)
        start = end - timedelta(days=WINDOW_DAYS)
        won_raw, lost_raw = [], []
        won_z, lost_z = [], []
        for p in picks:
            # Join by entry_date (day of pick creation / open)
            dt = _parse_dt(p.get("entry_date") or p.get("created_at") or p.get("open_date"))
            if dt is None:
                continue
            closed_dt = _parse_dt(p.get("closed_at") or p.get("exit_date") or p.get("resolved_at"))
            if closed_dt is None or not (start <= closed_dt < end):
                continue
            d = dt.date()
            fg_score = fg_by_date.get(d)
            fg_z = z_by_date.get(d)
            if fg_score is None or fg_z is None:
                continue
            outcome = _is_win(p)
            if outcome is True:
                won_raw.append(fg_score)
                won_z.append(fg_z)
            elif outcome is False:
                lost_raw.append(fg_score)
                lost_z.append(fg_z)

        n = len(won_raw) + len(lost_raw)
        window_rec: dict = {
            "window_end": end.date().isoformat(),
            "window_start": start.date().isoformat(),
            "n_won": len(won_raw),
            "n_lost": len(lost_raw),
            "n_total": n,
            "mean_fg_won": sum(won_raw) / len(won_raw) if won_raw else None,
            "mean_fg_lost": sum(lost_raw) / len(lost_raw) if lost_raw else None,
            "eff_raw": _eff(won_raw, lost_raw),
            "eff_z": _eff(won_z, lost_z),
        }
        windows.append(window_rec)

    # Count admissible windows (eff_z direction consistent and >= EFF_FLOOR)
    populated = [w for w in windows if w["n_total"] >= 5]
    if populated:
        signs = [math.copysign(1, w["eff_z"]) for w in populated if abs(w["eff_z"]) >= EFF_FLOOR]
        admissible = sum(1 for w in populated if abs(w["eff_z"]) >= EFF_FLOOR)
        dominant_sign = max(set(signs), key=signs.count) if signs else 0
        same_sign = all(s == dominant_sign for s in signs) if signs else False
    else:
        admissible = 0
        dominant_sign = 0
        same_sign = False

    verdict = "ADMISSIBLE" if (
        admissible >= MIN_WINDOWS and same_sign
    ) else "KILL"

    return {
        "hypothesis": "H-025",
        "verdict": verdict,
        "admissible_windows": admissible,
        "min_required": MIN_WINDOWS,
        "same_sign": same_sign,
        "dominant_direction": "CONTRARIAN_LONG_AT_FEAR" if dominant_sign < 0 else "TREND_FOLLOW_AT_GREED" if dominant_sign > 0 else "NONE",
        "eff_floor": EFF_FLOOR,
        "n_picks_with_fg": sum(w["n_total"] for w in windows),
        "windows": windows,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="H-025 Fear & Greed harness")
    parser.add_argument("--asset-class", default="CRYPTO", help="Asset class to test (default: CRYPTO)")
    parser.add_argument("--json", action="store_true", help="Output JSON result")
    args = parser.parse_args()

    print(f"[H-025] Loading F&G series...")
    fg_by_date = load_fg_series()
    z_by_date = compute_fg_zseries(fg_by_date)
    print(f"[H-025] F&G series: {len(fg_by_date)} days, z-scored {len(z_by_date)} days")

    ac = args.asset_class.upper()
    print(f"[H-025] Loading {ac} closed picks...")
    picks = load_picks(ac)
    print(f"[H-025] {len(picks)} resolved {ac} picks loaded")

    result = run_walk_forward(picks, fg_by_date, z_by_date)
    result["asset_class"] = ac
    result["fg_days"] = len(fg_by_date)
    result["total_picks_loaded"] = len(picks)
    result["run_at"] = datetime.now(timezone.utc).isoformat()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"H-025 Fear & Greed Harness — {ac}")
        print(f"{'='*60}")
        print(f"Verdict:           {result['verdict']}")
        print(f"Admissible windows:{result['admissible_windows']}/{result['min_required']} required")
        print(f"Same sign:         {result['same_sign']}")
        print(f"Dominant direction:{result['dominant_direction']}")
        print(f"Picks with F&G:    {result['n_picks_with_fg']}")
        print(f"Output saved to:   {OUTPUT_PATH}")

        if result["windows"]:
            print(f"\n{'Window end':<14} {'N':>5} {'EFF_Z':>8} {'Mean FG WON':>12} {'Mean FG LOST':>13}")
            for w in result["windows"][:10]:
                n = w["n_total"]
                ez = w["eff_z"]
                mw = f"{w['mean_fg_won']:.1f}" if w["mean_fg_won"] is not None else "n/a"
                ml = f"{w['mean_fg_lost']:.1f}" if w["mean_fg_lost"] is not None else "n/a"
                print(f"{w['window_end']:<14} {n:>5} {ez:>8.3f} {mw:>12} {ml:>13}")


if __name__ == "__main__":
    main()
