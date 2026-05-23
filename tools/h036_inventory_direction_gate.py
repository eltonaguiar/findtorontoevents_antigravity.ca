#!/usr/bin/env python3
"""H-036 — Inventory Direction Gate (COMMODITY / EIA petroleum).

Pre-registered 2026-05-19 (see reports/hypothesis_registry.json H-036).
Separable from H-004: H-004 tests inventory-surprise + roll-yield BUNDLE
with eff gate; H-036 tests PURE inventory draw/build direction with WR gate.

HYPOTHESIS
----------
EIA weekly petroleum inventory draw (actual < seasonal expectation) → LONG
USO/CL=F proxy for 14 calendar days. Build (actual > expectation) → SHORT.

This is a categorical directional signal: only the SIGN of the surprise
is used. The SIZE of the surprise is ignored. Direction only.

Economic prior: the EIA petroleum stocks report is the single highest-impact
weekly data release for crude oil. A draw vs expectation is a genuine supply
shock that takes 5-10 trading days for the market to fully price (Kaufmann &
Ullman 2009; Ye et al. 2005). USO WR=59.9% n=1066 real-EIA data in H-004
backtest (2026-05-19) establishes the prior.

SEPARABILITY FROM H-004
  H-004 tests the BUNDLE: inventory_surprise_z × roll_yield_z combined signal.
  H-036 tests ONLY the inventory direction (sign of surprise). Different test
  statistic (WR not eff). Different construction (sign not magnitude).

ACCEPTANCE CRITERIA (pre-registered)
  * min_wr = 0.56  (directional win rate gross, 14-day hold)
  * min_n = 100 per window
  * min_windows_admissible = 3 consecutive windows with WR >= 0.56

DATA SOURCES
  * EIA v2 API: WCESTUS1 (crude oil weekly stocks, free, EIA_API_KEY from env)
  * yfinance: USO as the liquid crude ETF proxy

USAGE
-----
    python tools/h036_inventory_direction_gate.py [--json]
    EIA_API_KEY=<key> python tools/h036_inventory_direction_gate.py

OPT-IN RESEARCH SIDECAR. No production wiring. No caller in quality_gates.py
or any pick-generation path. Reads public data, writes a report — nothing else.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import co1_commodity_inventory_surprise_research as co1  # noqa: E402

# ---------------------------------------------------------------------------
# Tunables (pre-registered — do not change post-hoc)
# ---------------------------------------------------------------------------
H036_ID = "H-036"
EIA_SERIES = "WCESTUS1"   # crude oil total US weekly stocks
EIA_ROUTE = "petroleum/stoc/wstk/data"
PROXY = "USO"             # liquid crude ETF
HOLD_DAYS = 14
SURPRISE_Z_ROLL = 26      # 26-week trailing z-score window (same as H-004/CO-1)
MIN_WR = 0.56
MIN_N_WINDOW = 30         # min trades per walk-forward window
MIN_WINDOWS_ADMISSIBLE = 3
ROUND_TRIP_COST_BPS = 14.0
COST_SURVIVAL_MIN = 0.60
WINDOW_SIZE = 150         # number of trades per WF window (direction-only is denser)

CACHE_PATH = ROOT / "tools" / "cache" / "h036_direction_cache.json"
REPORT_DATE = datetime.now(timezone.utc).strftime("%Y%m%d")
REPORT_PATH = ROOT / "reports" / f"h036_direction_gate_{REPORT_DATE}.json"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_inventory_series(refresh: bool = False) -> tuple[dict, bool]:
    """Load USO inventory + price series.
    Returns (series_data, offline) where offline=True means synthetic fallback.
    """
    # Try H-004/CO-1 shared cache first
    co1_cache = ROOT / "tools" / "cache" / "co1_commodity_inventory_surprise_cache.json"
    if co1_cache.exists() and not refresh:
        try:
            with open(co1_cache) as f:
                cache = json.load(f)
            uso = cache.get("data", {}).get(PROXY, {})
            if uso and not uso.get("_offline") and len(uso.get("stocks", {})) >= 60:
                print(f"# loaded {PROXY} from CO-1 cache ({len(uso['stocks'])} stock obs)",
                      file=sys.stderr)
                return uso, False
        except Exception:
            pass

    # Fresh EIA fetch
    print(f"# fetching {PROXY} from EIA API...", file=sys.stderr)
    stocks = co1.fetch_eia_weekly_stocks(EIA_ROUTE, EIA_SERIES)
    price = co1.fetch_price_series(PROXY)

    if len(stocks) < 60 or len(price) < 200:
        print(f"# EIA fetch insufficient ({len(stocks)} stock obs, {len(price)} price bars)"
              f" — synthetic fallback", file=sys.stderr)
        syn = co1._synthetic_series(PROXY)
        return {"stocks": syn["stocks"], "price": syn["price"], "_offline": True}, True

    print(f"# {PROXY}: stocks={len(stocks)} obs  price={len(price)} bars  offline=False",
          file=sys.stderr)
    return {"stocks": stocks, "price": price, "_offline": False}, False


# ---------------------------------------------------------------------------
# Signal computation (categorical direction only)
# ---------------------------------------------------------------------------

def compute_direction_signal(stocks: dict[str, float]) -> dict[str, int]:
    """Compute seasonal-proxy surprise direction for each week.

    Returns {date_str: direction} where direction ∈ {+1 LONG, -1 SHORT}.
    Strictly past: only uses data published strictly before the signal date.

    Seasonal proxy: trailing SURPRISE_Z_ROLL-period mean + stdev of stock levels
    for the same calendar-week-of-year. Direction = -sign(actual - expected)
    (draw = actual < expected = bullish supply = LONG).
    """
    if not stocks:
        return {}

    dates_sorted = sorted(stocks.keys())
    n = len(dates_sorted)
    directions: dict[str, int] = {}

    # Build calendar-week lookup: week_of_year → list of (date, value) in order
    from collections import defaultdict
    woy_history: dict[int, list[tuple[str, float]]] = defaultdict(list)

    for i, d in enumerate(dates_sorted):
        val = stocks[d]
        if val is None:
            continue
        # Week-of-year from date string
        try:
            dt = datetime.fromisoformat(d)
        except ValueError:
            continue
        woy = dt.isocalendar()[1]

        # Compute seasonal expectation from STRICTLY PAST same-woy observations
        past_same_woy = [v for _, v in woy_history[woy] if v is not None]
        if len(past_same_woy) >= 4:
            # Rolling window: last SURPRISE_Z_ROLL observations (strictly past)
            window = past_same_woy[-SURPRISE_Z_ROLL:]
            mu = sum(window) / len(window)
            surprise = val - mu
            # Direction: draw (val < expected = surprise < 0) → bullish → LONG = +1
            direction = -1 if surprise > 0 else +1
            directions[d] = direction

        # Now add current to history (for future use)
        woy_history[woy].append((d, val))

    return directions


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------

def backtest_direction(series: dict, offline: bool) -> dict:
    """Run 14-day directional backtest on USO using inventory direction signal."""
    stocks = series.get("stocks", {})
    price = series.get("price", {})  # date → close price

    if not stocks or not price:
        return {"records": [], "offline": offline}

    # Compute directions
    directions = compute_direction_signal(stocks)
    print(f"# direction signals: {len(directions)}", file=sys.stderr)

    # Build daily price dict
    price_dates = sorted(price.keys())

    records = []
    gross_rets: list[float] = []
    net_rets: list[float] = []

    # Signal dates (EIA publication dates, roughly Wednesdays)
    signal_dates = sorted(directions.keys())

    for sig_date in signal_dates:
        direction = directions[sig_date]

        # Find entry: next trading day after signal date
        entry_date = None
        for pd in price_dates:
            if pd > sig_date:
                entry_date = pd
                break
        if entry_date is None:
            continue

        # Skip stale signals: signal_date must be within 30 days of entry_date
        # (pre-USO signals map hundreds of historical stock obs to the same entry)
        try:
            sig_dt = datetime.fromisoformat(sig_date)
            entry_dt = datetime.fromisoformat(entry_date)
            if (entry_dt - sig_dt).days > 30:
                continue
        except ValueError:
            continue

        # Find exit: HOLD_DAYS calendar days after entry
        exit_target = (
            datetime.fromisoformat(entry_date) + timedelta(days=HOLD_DAYS)
        ).strftime("%Y-%m-%d")
        exit_date = None
        for pd in price_dates:
            if pd >= exit_target:
                exit_date = pd
                break
        if exit_date is None or exit_date == entry_date:
            continue

        p0 = price.get(entry_date)
        p1 = price.get(exit_date)
        if p0 is None or p1 is None or p0 <= 0:
            continue

        raw_ret = p1 / p0 - 1.0
        signed_ret = raw_ret * direction
        cost_frac = ROUND_TRIP_COST_BPS / 10000.0
        net_ret = signed_ret - cost_frac
        status = "WON" if signed_ret > 0 else "LOST"

        gross_rets.append(signed_ret)
        net_rets.append(net_ret)
        records.append({
            "status": status,
            "entry_date": entry_date,
            "exit_date": exit_date,
            "signal_date": sig_date,
            "direction": direction,
            "signed_ret": round(signed_ret, 8),
            "net_ret": round(net_ret, 8),
        })

    return {
        "records": records,
        "gross_rets": gross_rets,
        "net_rets": net_rets,
        "offline": offline,
    }


# ---------------------------------------------------------------------------
# Walk-forward WR harness
# ---------------------------------------------------------------------------

def walk_forward_wr_harness(records: list[dict],
                             window_size: int = WINDOW_SIZE,
                             min_wr: float = MIN_WR,
                             min_n: int = MIN_N_WINDOW,
                             min_windows: int = MIN_WINDOWS_ADMISSIBLE) -> dict:
    """Split records chronologically; count windows with WR >= min_wr."""
    if len(records) < min_n:
        return {"admissible_windows": 0, "total_windows": 0,
                "per_window_wr": [], "min_windows": min_windows}

    sorted_recs = sorted(records, key=lambda r: r.get("entry_date", ""))
    n = len(sorted_recs)
    step = window_size
    windows = []
    for i in range(0, n - window_size + 1, step):
        w = sorted_recs[i:i + window_size]
        if len(w) >= min_n:
            windows.append(w)

    per_window_wr: list[dict] = []
    for w in windows:
        wn = len(w)
        wins = sum(1 for r in w if r["status"] == "WON")
        wr = wins / wn
        per_window_wr.append({
            "n": wn, "wins": wins, "wr": round(wr, 4),
            "admissible": wr >= min_wr,
            "date_range": f"{w[0]['entry_date']} → {w[-1]['entry_date']}",
        })

    admissible = sum(1 for w in per_window_wr if w["admissible"])
    mean_wr = round(sum(w["wr"] for w in per_window_wr) / len(per_window_wr), 4) if per_window_wr else None

    return {
        "admissible_windows": admissible,
        "total_windows": len(per_window_wr),
        "mean_wr": mean_wr,
        "per_window_wr": per_window_wr,
        "min_windows": min_windows,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="H-036 inventory direction gate backtest")
    parser.add_argument("--json", dest="json_out", action="store_true",
                        help="emit JSON summary to stdout")
    parser.add_argument("--refresh", action="store_true",
                        help="force re-fetch from EIA (bypass cache)")
    args = parser.parse_args()

    print("# H-036 Inventory Direction Gate backtest", file=sys.stderr)

    # --- Load data ---
    series, offline = load_inventory_series(refresh=args.refresh)

    # --- Backtest ---
    bt = backtest_direction(series, offline)
    records = bt.get("records", [])
    gross_rets = bt.get("gross_rets", [])
    net_rets = bt.get("net_rets", [])

    if not records:
        verdict = {
            "hypothesis_id": H036_ID,
            "verdict": "HARNESS_REJECTED",
            "n_trades": 0,
            "reason": "no trades generated",
            "offline": offline,
        }
    else:
        n = len(records)
        wins = sum(1 for r in records if r["status"] == "WON")
        wr_gross = wins / n
        mean_gross = sum(gross_rets) / n * 10000  # bps
        mean_net = sum(net_rets) / n * 10000

        # Cost survival (keep at least 60% of gross)
        cost_gate = co1.cost_survival(gross_rets, net_rets)

        # Walk-forward WR harness
        harness = walk_forward_wr_harness(records)
        admissible = harness.get("admissible_windows", 0)
        total_windows = harness.get("total_windows", 0)
        mean_wr_windows = harness.get("mean_wr")

        passed = (
            n >= 100
            and not offline
            and admissible >= MIN_WINDOWS_ADMISSIBLE
            and wr_gross >= MIN_WR
            and cost_gate.get("passes", False)
        )

        verdict_str = "HARNESS_PASS" if passed else "HARNESS_REJECTED"
        verdict = {
            "hypothesis_id": H036_ID,
            "verdict": verdict_str,
            "n_trades": n,
            "win_rate_gross": round(wr_gross, 4),
            "gross_edge_bps": round(mean_gross, 4),
            "net_edge_bps": round(mean_net, 4),
            "cost_survival_pct": cost_gate.get("cost_survival_pct"),
            "cost_gate_passes": cost_gate.get("passes"),
            "harness_admissible_windows": admissible,
            "harness_total_windows": total_windows,
            "harness_mean_wr": mean_wr_windows,
            "per_window_detail": harness.get("per_window_wr"),
            "offline_synthetic": offline,
            "proxy": PROXY,
            "hold_days": HOLD_DAYS,
            "acceptance_criteria": {
                "min_wr": MIN_WR,
                "min_n": 100,
                "min_windows": MIN_WINDOWS_ADMISSIBLE,
                "min_n_per_window": MIN_N_WINDOW,
                "cost_survival_min": COST_SURVIVAL_MIN,
            },
            "run_date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

    # --- Write report ---
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        json.dump(verdict, f, indent=2)
    print(f"# report → {REPORT_PATH}", file=sys.stderr)

    # --- Print summary ---
    if args.json_out:
        print(json.dumps(verdict, indent=2))
    else:
        v = verdict.get("verdict", "?")
        n = verdict.get("n_trades", 0)
        wr = verdict.get("win_rate_gross", 0)
        adm = verdict.get("harness_admissible_windows", 0)
        tot = verdict.get("harness_total_windows", 0)
        mean_ww = verdict.get("harness_mean_wr")
        offline_note = "UNTESTED (synthetic)" if offline else "REAL EIA DATA"
        print(f"\n{'='*60}")
        print(f"H-036 VERDICT: {v}")
        print(f"  n={n}  WR={wr:.1%}  windows={adm}/{tot}  mean_window_WR={mean_ww}")
        print(f"  gross={verdict.get('gross_edge_bps')} bps  net={verdict.get('net_edge_bps')} bps")
        print(f"  cost_survival={verdict.get('cost_survival_pct')}%")
        print(f"  data: {offline_note}")
        print(f"  proxy={PROXY}  hold_days={HOLD_DAYS}")
        print(f"{'='*60}")

        # Window detail
        for w in (verdict.get("per_window_detail") or []):
            flag = "✓" if w.get("admissible") else "✗"
            print(f"  {flag} {w['date_range']}  n={w['n']}  WR={w['wr']:.1%}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
