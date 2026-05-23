#!/usr/bin/env python3
"""
H-023 — XL* Sector ETF Cross-Sectional Momentum + Market Breadth Regime Harness
=================================================================================
Pre-registered 2026-05-18 per M-107. OPT-IN RESEARCH SIDECAR.

Hypothesis: XL* sector ETF cross-sectional momentum vs SPY (5-10d) combined
with market breadth regime gate discriminates ETF pick outcomes.
Allow ETF picks only when breadth momentum > 0 (risk-on).

Signal definition:
  - sector_momentum_z: cross-sectional z-score of 5-day return relative to SPY
    for each XL* sector ETF
  - breadth_regime: 1 if >5/11 XL* sectors above their 20-day SMA, 0 otherwise
  - Test if ETF picks entered during breadth_regime=1 outperform breadth_regime=0

Method:
  1. Fetch daily OHLCV for SPY + 11 XL* sector ETFs from Yahoo Finance CSV URL
     (no yfinance or API key required — uses direct CSV endpoint)
  2. Compute 5-day relative returns vs SPY for each XL* ETF
  3. Compute breadth_regime per trading day (how many sectors above 20d SMA)
  4. For each ETF closed pick, join breadth_regime score at pick's entry_date
  5. Run walk-forward Cohen's d (eff) on breadth_regime as discriminator

Data source:
  Yahoo Finance Chart API v8 (free, no key):
  https://query1.finance.yahoo.com/v8/finance/chart/{TICKER}?interval=1d&range=2y

Acceptance criteria (H-023):
  eff_floor: 0.30
  min_windows_admissible: 3
  same_sign: True

Usage:
    python tools/hypothesis/h023_etf_breadth_harness.py
    python tools/hypothesis/h023_etf_breadth_harness.py --json
"""

from __future__ import annotations

import argparse
import json
import math
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CLOSED_PATH = REPO_ROOT / "alpha_engine" / "data" / "closed_picks.json"
CACHE_PATH = REPO_ROOT / "alpha_engine" / "data" / "h023_breadth_cache.json"
OUTPUT_PATH = REPO_ROOT / "reports" / "h023_etf_breadth_harness.json"

# Sector ETF universe (11 SPDR sector ETFs)
SECTOR_ETFS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLB", "XLRE", "XLU", "XLC"]
BENCHMARK = "SPY"
ALL_TICKERS = [BENCHMARK] + SECTOR_ETFS

# Signal parameters
SMA_WINDOW = 20            # 20-day SMA for breadth regime
MOM_WINDOW = 5             # 5-day return for relative momentum
BREADTH_THRESHOLD = 5      # sectors above SMA to be "risk-on"

# Harness thresholds matching H-023 acceptance criteria
EFF_FLOOR = 0.30
MIN_WINDOWS = 3
WALK_FORWARD_WINDOW_DAYS = 14
MIN_PICKS_TOTAL = 30       # below this → INSUFFICIENT_DATA verdict
MIN_PICKS_PER_WINDOW = 3   # minimum picks per window to count

# Price cache TTL
CACHE_TTL_HOURS = 12

WIN_STATUSES = {"WIN", "TARGET_HIT", "TP_HIT", "CLOSED_WIN"}
LOSS_STATUSES = {"LOSS", "SL_HIT", "STOPPED", "CLOSED_LOSS", "EXPIRED"}


# ---------------------------------------------------------------------------
# Yahoo Finance v8 chart API fetching
# ---------------------------------------------------------------------------

# Two hosts for fallback
YF_HOSTS = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]
YF_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://finance.yahoo.com/",
}


def _fetch_prices_v8(ticker: str, range_str: str = "2y") -> dict[date, float]:
    """
    Fetch daily adj-close prices from Yahoo Finance v8 chart API.
    Returns {date: close}. Falls back to query2 if query1 fails.
    """
    for host in YF_HOSTS:
        url = f"https://{host}/v8/finance/chart/{ticker}?interval=1d&range={range_str}"
        req = urllib.request.Request(url, headers=YF_HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                payload = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            print(f"[H-023] HTTP {e.code} fetching {ticker} from {host}: {e.reason}")
            continue
        except Exception as e:
            print(f"[H-023] Error fetching {ticker} from {host}: {e}")
            continue

        try:
            result = payload["chart"]["result"][0]
            timestamps = result["timestamp"]
            # Prefer adjclose, fall back to close
            indicators = result.get("indicators", {})
            adjclose_list = indicators.get("adjclose", [{}])
            adjclose_vals = (adjclose_list[0] or {}).get("adjclose") if adjclose_list else None
            if not adjclose_vals:
                adjclose_vals = indicators.get("quote", [{}])[0].get("close")
            if not adjclose_vals or len(adjclose_vals) != len(timestamps):
                print(f"[H-023] {ticker}: adjclose/close length mismatch")
                return {}

            prices: dict[date, float] = {}
            for ts, close in zip(timestamps, adjclose_vals):
                if close is None:
                    continue
                d = datetime.fromtimestamp(ts, tz=timezone.utc).date()
                prices[d] = float(close)
            return prices
        except (KeyError, IndexError, TypeError) as e:
            print(f"[H-023] Parse error for {ticker}: {e}")
            return {}

    return {}


def load_price_history() -> dict[str, dict[date, float]]:
    """Load/cache 2yr daily price history for all tickers. Returns {ticker: {date: close}}."""
    now = datetime.now(timezone.utc)

    # Try cache
    if CACHE_PATH.exists():
        try:
            cached = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            ts = datetime.fromisoformat(cached.get("fetched_at", "2000-01-01"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age_h = (now - ts).total_seconds() / 3600
            if age_h < CACHE_TTL_HOURS:
                raw_data = cached["data"]
                result = {}
                for ticker, date_map in raw_data.items():
                    result[ticker] = {
                        datetime.strptime(ds, "%Y-%m-%d").date(): float(v)
                        for ds, v in date_map.items()
                    }
                n_days = sum(len(v) for v in result.values())
                print(f"[H-023] Using cached price history ({len(result)} tickers, "
                      f"{n_days} total data points, {age_h:.1f}h old)")
                return result
        except Exception as e:
            print(f"[H-023] Cache read failed ({e}), fetching fresh data...")

    print(f"[H-023] Fetching {len(ALL_TICKERS)} tickers from Yahoo Finance v8 chart API...")
    result: dict[str, dict[date, float]] = {}
    for i, ticker in enumerate(ALL_TICKERS):
        prices = _fetch_prices_v8(ticker, range_str="2y")
        result[ticker] = prices
        print(f"[H-023]   {ticker}: {len(prices)} trading days")
        if i < len(ALL_TICKERS) - 1:
            time.sleep(0.4)  # polite rate limiting

    # Save to cache
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        cache_data = {
            ticker: {d.isoformat(): v for d, v in date_map.items()}
            for ticker, date_map in result.items()
        }
        CACHE_PATH.write_text(json.dumps({
            "fetched_at": now.isoformat(),
            "data": cache_data,
        }, indent=2), encoding="utf-8")
        print(f"[H-023] Price cache saved to {CACHE_PATH}")
    except Exception as e:
        print(f"[H-023] Warning: cache write failed: {e}")

    return result


# ---------------------------------------------------------------------------
# Signal computation
# ---------------------------------------------------------------------------

def compute_breadth_series(
    prices: dict[str, dict[date, float]]
) -> dict[date, dict]:
    """
    For each trading day, compute:
      - breadth_count: number of XL* sectors above 20d SMA
      - breadth_regime: 1 if breadth_count > BREADTH_THRESHOLD, else 0
      - sector_momentum_z: dict of {ticker: 5d-relative-return z-score}
      - breadth_score: breadth_count / 11 (float, 0-1)

    Returns {date: {...}} for all dates where SPY has prices.
    """
    spy_prices = prices.get(BENCHMARK, {})
    sorted_spy_dates = sorted(spy_prices.keys())

    breadth_series: dict[date, dict] = {}

    for d in sorted_spy_dates:
        # Compute 5d relative returns for each sector ETF
        rel_returns: dict[str, float | None] = {}
        for ticker in SECTOR_ETFS:
            ticker_prices = prices.get(ticker, {})
            # Find price 5 trading days ago
            past_dates = [dd for dd in sorted(ticker_prices.keys()) if dd <= d]
            if len(past_dates) < SMA_WINDOW + MOM_WINDOW:
                rel_returns[ticker] = None
                continue
            price_now = ticker_prices.get(d)
            # 5d ago (by index in sorted dates)
            price_5d_ago = None
            ticker_sorted = sorted(ticker_prices.keys())
            idx = ticker_sorted.index(d) if d in ticker_sorted else -1
            if idx >= MOM_WINDOW:
                price_5d_ago = ticker_prices.get(ticker_sorted[idx - MOM_WINDOW])

            spy_now = spy_prices.get(d)
            spy_5d_dates = [dd for dd in sorted_spy_dates if dd <= d]
            spy_5d_ago = None
            idx_spy = sorted_spy_dates.index(d) if d in sorted_spy_dates else -1
            if idx_spy >= MOM_WINDOW:
                spy_5d_ago = spy_prices.get(sorted_spy_dates[idx_spy - MOM_WINDOW])

            if (price_now and price_5d_ago and price_5d_ago > 0
                    and spy_now and spy_5d_ago and spy_5d_ago > 0):
                etf_ret = (price_now / price_5d_ago) - 1.0
                spy_ret = (spy_now / spy_5d_ago) - 1.0
                rel_returns[ticker] = etf_ret - spy_ret
            else:
                rel_returns[ticker] = None

        # Cross-sectional z-score of relative returns
        valid_rets = [v for v in rel_returns.values() if v is not None]
        if len(valid_rets) >= 5:
            mu = sum(valid_rets) / len(valid_rets)
            var = sum((v - mu) ** 2 for v in valid_rets) / max(len(valid_rets) - 1, 1)
            sigma = math.sqrt(var) if var > 0 else 1e-9
            mom_z = {t: (v - mu) / sigma for t, v in rel_returns.items() if v is not None}
        else:
            mom_z = {}

        # Breadth: count sectors above 20d SMA
        breadth_count = 0
        sector_sma_flags: dict[str, bool] = {}
        for ticker in SECTOR_ETFS:
            ticker_prices = prices.get(ticker, {})
            ticker_sorted = sorted(ticker_prices.keys())
            # Get SMA_WINDOW most recent closing prices up to d
            recent = [ticker_prices[dd] for dd in ticker_sorted
                      if dd <= d][-SMA_WINDOW:]
            if len(recent) >= SMA_WINDOW:
                sma = sum(recent) / len(recent)
                current_price = ticker_prices.get(d)
                if current_price and current_price > sma:
                    breadth_count += 1
                    sector_sma_flags[ticker] = True
                else:
                    sector_sma_flags[ticker] = False

        breadth_regime = 1 if breadth_count > BREADTH_THRESHOLD else 0

        breadth_series[d] = {
            "breadth_count": breadth_count,
            "breadth_regime": breadth_regime,
            "breadth_score": breadth_count / len(SECTOR_ETFS),
            "sector_sma_flags": sector_sma_flags,
            "sector_momentum_z": mom_z,
            "n_sectors_with_data": len(valid_rets),
        }

    return breadth_series


# ---------------------------------------------------------------------------
# Pick helpers
# ---------------------------------------------------------------------------

def _parse_dt(s: Any) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            cleaned = str(s)[:26].strip()
            dt = datetime.strptime(cleaned, fmt.replace("%z", ""))
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
    # Try pnl_pct
    pnl = pick.get("pnl_pct")
    if pnl is not None:
        try:
            return float(pnl) > 0
        except (TypeError, ValueError):
            pass
    # Try exit_reason
    exit_r = str(pick.get("exit_reason") or "").upper()
    if exit_r in {"TP", "TARGET", "TAKE_PROFIT"}:
        return True
    if exit_r in {"SL", "STOP", "STOP_LOSS"}:
        return False
    return None


def load_etf_picks() -> list[dict]:
    """Load all resolved ETF picks from closed_picks.json."""
    raw = json.loads(CLOSED_PATH.read_text(encoding="utf-8"))
    picks = []
    for p in raw:
        ac = str(p.get("asset_class") or "").upper()
        if ac != "ETF":
            continue
        if _is_win(p) is None:
            continue
        picks.append(p)
    return picks


# ---------------------------------------------------------------------------
# Cohen's d eff computation
# ---------------------------------------------------------------------------

def _cohens_d(group_a: list[float], group_b: list[float]) -> float:
    """Cohen's d between two groups (group_a - group_b)."""
    if not group_a or not group_b:
        return 0.0
    n1, n2 = len(group_a), len(group_b)
    m1 = sum(group_a) / n1
    m2 = sum(group_b) / n2
    var1 = sum((x - m1) ** 2 for x in group_a) / max(n1 - 1, 1)
    var2 = sum((x - m2) ** 2 for x in group_b) / max(n2 - 1, 1)
    pooled_std = math.sqrt((var1 * (n1 - 1) + var2 * (n2 - 1)) / max(n1 + n2 - 2, 1))
    if pooled_std < 1e-12:
        return 0.0
    return (m1 - m2) / pooled_std


# ---------------------------------------------------------------------------
# Walk-forward harness
# ---------------------------------------------------------------------------

def run_walk_forward(
    picks: list[dict],
    breadth_series: dict[date, dict],
) -> dict:
    """
    Walk-forward eff on breadth_regime discriminator.

    For each window, split picks into:
      - regime_1: picks entered during breadth_regime=1 (risk-on)
      - regime_0: picks entered during breadth_regime=0 (risk-off)
    Compute Cohen's d on win/loss outcome (1=win, 0=loss).
    Compute mean win_rate for each group.
    """
    n_total_picks = len(picks)
    now = datetime.now(timezone.utc)

    # Enrich picks with breadth_regime at entry
    enriched: list[dict] = []
    no_entry_date = 0
    no_breadth_data = 0
    for p in picks:
        dt = _parse_dt(
            p.get("entry_date") or p.get("entry_time") or
            p.get("created_at") or p.get("open_date")
        )
        if dt is None:
            no_entry_date += 1
            continue
        d = dt.date()
        # Find closest breadth data (same day or nearest previous trading day)
        bd = breadth_series.get(d)
        if bd is None:
            # Look back up to 5 calendar days for nearest trading day
            for delta in range(1, 6):
                bd = breadth_series.get(d - timedelta(days=delta))
                if bd is not None:
                    break
        if bd is None:
            no_breadth_data += 1
            continue
        closed_dt = _parse_dt(
            p.get("closed_at") or p.get("exit_date") or
            p.get("exit_time") or p.get("resolved_at")
        )
        enriched.append({
            **p,
            "_entry_dt": dt,
            "_closed_dt": closed_dt,
            "_entry_date": d,
            "_breadth_regime": bd["breadth_regime"],
            "_breadth_count": bd["breadth_count"],
            "_breadth_score": bd["breadth_score"],
            "_outcome": 1.0 if _is_win(p) else 0.0,
        })

    # Regime split across all data (not windowed — for overall stats)
    regime1 = [p for p in enriched if p["_breadth_regime"] == 1]
    regime0 = [p for p in enriched if p["_breadth_regime"] == 0]

    overall_wr_regime1 = (
        sum(p["_outcome"] for p in regime1) / len(regime1) if regime1 else None
    )
    overall_wr_regime0 = (
        sum(p["_outcome"] for p in regime0) / len(regime0) if regime0 else None
    )

    # Walk-forward windows (rolling, 14-day)
    windows = []
    for i in range(20):
        end = now - timedelta(days=i * WALK_FORWARD_WINDOW_DAYS)
        start = end - timedelta(days=WALK_FORWARD_WINDOW_DAYS)

        window_picks = [
            p for p in enriched
            if (p["_closed_dt"] is not None and start <= p["_closed_dt"] < end)
        ]

        r1 = [p["_outcome"] for p in window_picks if p["_breadth_regime"] == 1]
        r0 = [p["_outcome"] for p in window_picks if p["_breadth_regime"] == 0]

        eff = _cohens_d(r1, r0)  # positive = regime1 outperforms regime0
        wr1 = sum(r1) / len(r1) if r1 else None
        wr0 = sum(r0) / len(r0) if r0 else None

        windows.append({
            "window_end": end.date().isoformat(),
            "window_start": start.date().isoformat(),
            "n_total": len(window_picks),
            "n_regime1": len(r1),
            "n_regime0": len(r0),
            "wr_regime1": round(wr1, 4) if wr1 is not None else None,
            "wr_regime0": round(wr0, 4) if wr0 is not None else None,
            "eff": round(eff, 4),
        })

    # Admissibility check
    populated = [w for w in windows if w["n_total"] >= MIN_PICKS_PER_WINDOW]
    admissible_windows = [w for w in populated if abs(w["eff"]) >= EFF_FLOOR]
    signs = [math.copysign(1, w["eff"]) for w in admissible_windows]
    dominant_sign = max(set(signs), key=signs.count) if signs else 0
    same_sign = all(s == dominant_sign for s in signs) if signs else False

    # Determine overall verdict
    if n_total_picks < MIN_PICKS_TOTAL:
        verdict = "INSUFFICIENT_DATA"
    elif len(admissible_windows) >= MIN_WINDOWS and same_sign:
        verdict = "ADMISSIBLE"
    else:
        verdict = "KILL"

    direction_label = (
        "BREADTH_CONFIRMS_EDGE" if dominant_sign > 0
        else "BREADTH_CONTRADICTS_HYPOTHESIS" if dominant_sign < 0
        else "NO_DIRECTION"
    )

    return {
        "hypothesis": "H-023",
        "verdict": verdict,
        "admissible_windows": len(admissible_windows),
        "min_required": MIN_WINDOWS,
        "same_sign": same_sign,
        "dominant_direction": direction_label,
        "eff_floor": EFF_FLOOR,
        "n_etf_picks_total": n_total_picks,
        "n_etf_picks_enriched": len(enriched),
        "n_picks_no_entry_date": no_entry_date,
        "n_picks_no_breadth_data": no_breadth_data,
        "n_picks_regime1": len(regime1),
        "n_picks_regime0": len(regime0),
        "overall_wr_regime1": round(overall_wr_regime1, 4) if overall_wr_regime1 is not None else None,
        "overall_wr_regime0": round(overall_wr_regime0, 4) if overall_wr_regime0 is not None else None,
        "wr_delta": (
            round(overall_wr_regime1 - overall_wr_regime0, 4)
            if (overall_wr_regime1 is not None and overall_wr_regime0 is not None)
            else None
        ),
        "insufficient_data_note": (
            f"Only {n_total_picks} ETF picks with resolved outcomes in closed_picks.json "
            f"(need >= {MIN_PICKS_TOTAL}). Walk-forward windows will be near-empty. "
            f"Signal construction validated against {len(breadth_series)} trading days of XL* breadth data."
            if n_total_picks < MIN_PICKS_TOTAL else None
        ),
        "windows": windows,
    }


# ---------------------------------------------------------------------------
# Breadth signal summary (for validation even with 0 picks)
# ---------------------------------------------------------------------------

def summarize_breadth_signal(breadth_series: dict[date, dict]) -> dict:
    """Return descriptive stats about the breadth signal for the last 252 days."""
    if not breadth_series:
        return {}

    sorted_dates = sorted(breadth_series.keys())
    recent_dates = sorted_dates[-252:] if len(sorted_dates) > 252 else sorted_dates

    regime1_days = sum(1 for d in recent_dates if breadth_series[d]["breadth_regime"] == 1)
    regime0_days = len(recent_dates) - regime1_days
    scores = [breadth_series[d]["breadth_score"] for d in recent_dates]
    mean_score = sum(scores) / len(scores) if scores else None
    latest_d = recent_dates[-1]
    latest = breadth_series[latest_d]

    # Count regime transitions
    transitions = 0
    for i in range(1, len(recent_dates)):
        prev_regime = breadth_series[recent_dates[i - 1]]["breadth_regime"]
        curr_regime = breadth_series[recent_dates[i]]["breadth_regime"]
        if prev_regime != curr_regime:
            transitions += 1

    return {
        "n_trading_days_analyzed": len(recent_dates),
        "regime1_days": regime1_days,
        "regime0_days": regime0_days,
        "regime1_pct": round(regime1_days / len(recent_dates), 4) if recent_dates else None,
        "mean_breadth_score": round(mean_score, 4) if mean_score is not None else None,
        "regime_transitions_1yr": transitions,
        "latest_date": latest_d.isoformat(),
        "latest_breadth_count": latest["breadth_count"],
        "latest_breadth_regime": latest["breadth_regime"],
        "latest_breadth_score": round(latest["breadth_score"], 4),
        "latest_sector_sma_flags": latest.get("sector_sma_flags", {}),
        "latest_n_sectors_with_momentum_data": latest.get("n_sectors_with_data", 0),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="H-023 ETF Breadth Regime harness")
    parser.add_argument("--json", action="store_true", help="Output JSON result")
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Force fresh price fetch (ignore cache)"
    )
    args = parser.parse_args()

    # Optionally bust cache
    if args.no_cache and CACHE_PATH.exists():
        CACHE_PATH.unlink()
        print("[H-023] Cache cleared (--no-cache)")

    # Step 1: Check ETF pick count
    print("[H-023] Loading ETF closed picks...")
    picks = load_etf_picks()
    print(f"[H-023] ETF resolved picks found: {len(picks)}")
    if len(picks) < MIN_PICKS_TOTAL:
        print(f"[H-023] WARNING: Only {len(picks)} picks (need >= {MIN_PICKS_TOTAL} for statistical power)")
        print("[H-023] Proceeding to validate signal construction against price data...")

    # Step 2: Fetch price history
    prices = load_price_history()
    spy_days = len(prices.get(BENCHMARK, {}))
    print(f"[H-023] SPY: {spy_days} trading days fetched")
    for t in SECTOR_ETFS:
        n = len(prices.get(t, {}))
        if n == 0:
            print(f"[H-023] WARNING: No data for {t}")

    # Step 3: Compute breadth series
    print("[H-023] Computing breadth regime series...")
    breadth_series = compute_breadth_series(prices)
    print(f"[H-023] Breadth series computed: {len(breadth_series)} trading days")

    if not breadth_series:
        print("[H-023] ERROR: No breadth data computed — check network access to Yahoo Finance")
        result = {
            "hypothesis": "H-023",
            "verdict": "ERROR",
            "error": "Failed to compute breadth series — no price data available",
            "run_at": datetime.now(timezone.utc).isoformat(),
        }
    else:
        # Step 4: Run walk-forward
        print("[H-023] Running walk-forward eff harness...")
        result = run_walk_forward(picks, breadth_series)

        # Step 5: Add breadth signal summary
        result["breadth_signal_summary"] = summarize_breadth_signal(breadth_series)
        result["signal_params"] = {
            "sma_window": SMA_WINDOW,
            "momentum_window": MOM_WINDOW,
            "breadth_threshold": BREADTH_THRESHOLD,
            "sector_etfs": SECTOR_ETFS,
            "benchmark": BENCHMARK,
            "min_picks_total": MIN_PICKS_TOTAL,
            "eff_floor": EFF_FLOOR,
            "min_windows": MIN_WINDOWS,
        }

    result["asset_class"] = "ETF"
    result["data_source"] = "Yahoo Finance CSV (free, no key)"
    result["run_at"] = datetime.now(timezone.utc).isoformat()

    # Save output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'='*65}")
        print(f"H-023 ETF Breadth Regime Harness")
        print(f"{'='*65}")
        print(f"Verdict:              {result.get('verdict', 'N/A')}")
        print(f"ETF picks total:      {result.get('n_etf_picks_total', 0)}")
        print(f"Picks enriched:       {result.get('n_etf_picks_enriched', 0)}")
        print(f"Admissible windows:   {result.get('admissible_windows', 0)}/{result.get('min_required', MIN_WINDOWS)} required")
        print(f"Same sign:            {result.get('same_sign', False)}")
        print(f"Dominant direction:   {result.get('dominant_direction', 'N/A')}")

        if result.get("overall_wr_regime1") is not None:
            print(f"WR regime=1 (risk-on): {result['overall_wr_regime1']:.1%}")
        if result.get("overall_wr_regime0") is not None:
            print(f"WR regime=0 (risk-off):{result['overall_wr_regime0']:.1%}")
        if result.get("wr_delta") is not None:
            print(f"WR delta (R1-R0):     {result['wr_delta']:+.1%}")

        bs = result.get("breadth_signal_summary", {})
        if bs:
            print(f"\nBreadth signal (last ~252 trading days):")
            print(f"  Regime-1 days:      {bs.get('regime1_days', 'n/a')} "
                  f"({bs.get('regime1_pct', 0):.1%} of time)")
            print(f"  Mean breadth score: {bs.get('mean_breadth_score', 'n/a')}")
            print(f"  Latest date:        {bs.get('latest_date', 'n/a')}")
            print(f"  Latest regime:      {bs.get('latest_breadth_regime', 'n/a')} "
                  f"({bs.get('latest_breadth_count', 'n/a')}/11 sectors above SMA)")
            flags = bs.get("latest_sector_sma_flags", {})
            above = [t for t, v in flags.items() if v]
            below = [t for t, v in flags.items() if not v]
            if above:
                print(f"  Above 20d SMA:      {', '.join(above)}")
            if below:
                print(f"  Below 20d SMA:      {', '.join(below)}")

        if result.get("insufficient_data_note"):
            print(f"\nNOTE: {result['insufficient_data_note']}")

        windows = result.get("windows", [])
        populated_windows = [w for w in windows if w["n_total"] >= MIN_PICKS_PER_WINDOW]
        if populated_windows:
            print(f"\n{'Window end':<14} {'N':>5} {'R1_n':>6} {'R0_n':>6} "
                  f"{'WR_R1':>8} {'WR_R0':>8} {'EFF':>8}")
            for w in populated_windows[:10]:
                wr1 = f"{w['wr_regime1']:.3f}" if w["wr_regime1"] is not None else " n/a"
                wr0 = f"{w['wr_regime0']:.3f}" if w["wr_regime0"] is not None else " n/a"
                print(f"{w['window_end']:<14} {w['n_total']:>5} {w['n_regime1']:>6} "
                      f"{w['n_regime0']:>6} {wr1:>8} {wr0:>8} {w['eff']:>8.3f}")
        else:
            print("\nNo walk-forward windows had sufficient picks.")

        print(f"\nOutput saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
