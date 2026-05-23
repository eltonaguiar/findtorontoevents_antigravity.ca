#!/usr/bin/env python3
"""H-037: VIX term-structure carry signal.

Hypothesis (pre-registered 2026-05-19):
  When VIX spot is below VIX3M (contango), volatility risk premium is
  being sold into the market → risk-on signal for diversified ETF basket.
  When VIX > VIX3M (backwardation / fear spike), move to cash.

Test statistic: WR of signal direction accuracy over 5-day forward windows.
Vehicle: equal-weight basket of 11 SPDR sector ETFs.
Data: yfinance (free) — ^VIX, ^VIX3M, ^VIX6M, plus XLK/XLF/XLE/XLV/XLI/
      XLU/XLB/XLRE/XLY/XLP/XLC.

Acceptance criteria (M-107):
  min_wr=0.55, min_n=100, eff_floor=0.3 (walk-forward), min_windows=3.

Usage:
    python tools/h037_vix_carry.py
    python tools/h037_vix_carry.py --json
    python tools/h037_vix_carry.py --years 5 --hold-days 5

Output: human-readable summary to stdout; --json emits JSON to stdout.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Optional

SECTOR_ETFS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLU", "XLB", "XLRE", "XLY", "XLP", "XLC"]
VIX_TICKERS = ["^VIX", "^VIX3M", "^VIX6M"]

ACCEPT_MIN_WR = 0.55
ACCEPT_MIN_N = 100
ACCEPT_EFF_FLOOR = 0.3
ACCEPT_MIN_WINDOWS = 3
CARRY_THRESHOLD = 0.0  # contango if (VIX3M - VIX) / VIX > threshold
HOLD_DAYS_DEFAULT = 5
YEARS_DEFAULT = 5
WF_FOLDS = 5


def _download(tickers: list[str], years: int) -> dict:
    """Download adjusted close prices via yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        print("ERROR: yfinance not installed. Run: pip install yfinance", file=sys.stderr)
        sys.exit(1)

    end = datetime.today()
    start = end - timedelta(days=int(years * 365.25))
    data = yf.download(
        tickers,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        auto_adjust=True,
        progress=False,
    )
    if "Close" in data.columns:
        return data["Close"].to_dict(orient="list"), list(data.index.strftime("%Y-%m-%d"))
    # Single ticker returns flat DataFrame
    return {tickers[0]: data["Close"].tolist()}, list(data.index.strftime("%Y-%m-%d"))


def _align_series(prices: dict, dates: list, tickers: list) -> tuple[list, dict]:
    """Return dates where all requested tickers have valid (non-NaN) data."""
    import math

    valid_dates = []
    aligned: dict[str, list] = {t: [] for t in tickers}

    for i, d in enumerate(dates):
        row = {t: prices.get(t, [None] * len(dates)) for t in tickers}
        vals = [row[t][i] if i < len(row[t]) else None for t in tickers]
        if all(v is not None and not (isinstance(v, float) and math.isnan(v)) and v > 0 for v in vals):
            valid_dates.append(d)
            for j, t in enumerate(tickers):
                aligned[t].append(vals[j])

    return valid_dates, aligned


def _spearman(xs: list[float], ys: list[float]) -> float:
    """Spearman rank correlation (no scipy dependency)."""
    n = len(xs)
    if n < 4:
        return 0.0

    def _rank(lst: list[float]) -> list[float]:
        idx_sorted = sorted(range(n), key=lambda i: lst[i])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n and lst[idx_sorted[j]] == lst[idx_sorted[i]]:
                j += 1
            avg_rank = (i + j - 1) / 2.0 + 1
            for k in range(i, j):
                ranks[idx_sorted[k]] = avg_rank
            i = j
        return ranks

    rx, ry = _rank(xs), _rank(ys)
    mean_rx = sum(rx) / n
    mean_ry = sum(ry) / n
    num = sum((rx[i] - mean_rx) * (ry[i] - mean_ry) for i in range(n))
    den = (sum((r - mean_rx) ** 2 for r in rx) * sum((r - mean_ry) ** 2 for r in ry)) ** 0.5
    return num / den if den > 0 else 0.0


def _walk_forward_eff(records: list[dict], window_size: int = 100) -> dict:
    """Walk-forward efficiency harness.

    Slices records into WF_FOLDS equal-size folds, computes WR per fold.
    Returns: {"folds": [...wr...], "eff": fraction of folds >= ACCEPT_MIN_WR,
              "mean_wr": float, "admissible": bool}
    """
    n = len(records)
    fold_size = max(window_size, n // WF_FOLDS)
    fold_wrs = []
    for start in range(0, n - fold_size, fold_size):
        chunk = records[start : start + fold_size]
        if len(chunk) < 20:
            continue
        wins = sum(1 for r in chunk if r.get("win"))
        fold_wrs.append(wins / len(chunk))

    if not fold_wrs:
        return {"folds": [], "eff": 0.0, "mean_wr": 0.0, "admissible": False}

    eff = sum(1 for w in fold_wrs if w >= ACCEPT_MIN_WR) / len(fold_wrs)
    mean_wr = sum(fold_wrs) / len(fold_wrs)
    admissible = (
        eff >= ACCEPT_EFF_FLOOR
        and mean_wr >= ACCEPT_MIN_WR
        and len(fold_wrs) >= ACCEPT_MIN_WINDOWS
    )
    return {"folds": fold_wrs, "eff": eff, "mean_wr": mean_wr, "admissible": admissible}


def backtest(years: int = YEARS_DEFAULT, hold_days: int = HOLD_DAYS_DEFAULT) -> dict:
    """Run the H-037 backtest.

    Returns a result dict with keys: status, n, wr, pf, carry_spearman,
    wf (walk-forward dict), signal_records (list of {date, carry, signal,
    basket_return, win}).
    """
    print("H-037: Downloading VIX term-structure data...", file=sys.stderr)
    all_tickers = VIX_TICKERS + SECTOR_ETFS

    try:
        prices_raw, dates_raw = _download(all_tickers, years)
    except Exception as exc:
        return {
            "status": "DOWNLOAD_ERROR",
            "error": str(exc),
            "n": 0,
            "wr": None,
            "pf": None,
        }

    print(f"H-037: Aligning {len(all_tickers)} series across {len(dates_raw)} dates...", file=sys.stderr)
    dates, prices = _align_series(prices_raw, dates_raw, all_tickers)
    n_dates = len(dates)
    print(f"H-037: {n_dates} aligned dates ({dates[0] if dates else 'N/A'} → {dates[-1] if dates else 'N/A'})", file=sys.stderr)

    if n_dates < ACCEPT_MIN_N + hold_days:
        return {
            "status": "INSUFFICIENT_DATA",
            "error": f"Only {n_dates} aligned dates — need {ACCEPT_MIN_N + hold_days}+",
            "n": 0,
            "wr": None,
            "pf": None,
        }

    # Build signal + forward-return records
    records: list[dict] = []
    carry_values: list[float] = []
    basket_returns: list[float] = []

    for i in range(n_dates - hold_days):
        vix_spot = prices["^VIX"][i]
        vix_3m = prices["^VIX3M"][i]

        # Carry = (VIX3M - VIX) / VIX  (positive = contango = risk-on)
        carry = (vix_3m - vix_spot) / vix_spot if vix_spot > 0 else 0.0

        # Signal: LONG if contango, FLAT/OUT if backwardation
        signal = "LONG" if carry > CARRY_THRESHOLD else "FLAT"

        if signal == "FLAT":
            # Only record LONG signals for WR/PF calculation
            continue

        # Compute equal-weight basket forward return
        basket_fwd_returns = []
        for etf in SECTOR_ETFS:
            p_now = prices[etf][i]
            p_future = prices[etf][i + hold_days]
            if p_now > 0:
                basket_fwd_returns.append((p_future - p_now) / p_now)

        if not basket_fwd_returns:
            continue

        basket_ret = sum(basket_fwd_returns) / len(basket_fwd_returns)
        win = basket_ret > 0.0

        carry_values.append(carry)
        basket_returns.append(basket_ret)

        records.append({
            "date": dates[i],
            "vix_spot": round(vix_spot, 2),
            "vix_3m": round(vix_3m, 2),
            "carry": round(carry, 4),
            "signal": signal,
            "basket_return_pct": round(basket_ret * 100, 3),
            "win": win,
        })

    n = len(records)
    if n < ACCEPT_MIN_N:
        return {
            "status": "INSUFFICIENT_SIGNAL",
            "error": f"Only {n} LONG-signal days — carry threshold may be too tight",
            "n": n,
            "wr": None,
            "pf": None,
            "signal_records": records[:20],
        }

    wins = sum(1 for r in records if r["win"])
    wr = wins / n

    gross_profit = sum(r["basket_return_pct"] for r in records if r["win"])
    gross_loss = abs(sum(r["basket_return_pct"] for r in records if not r["win"]))
    pf = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")

    avg_win = gross_profit / wins if wins > 0 else 0.0
    avg_loss = gross_loss / (n - wins) if (n - wins) > 0 else 0.0

    carry_spearman = _spearman(carry_values, basket_returns) if len(carry_values) >= 10 else None
    wf = _walk_forward_eff(records)

    passes = (
        wr >= ACCEPT_MIN_WR
        and n >= ACCEPT_MIN_N
        and wf["admissible"]
        and pf > 1.0
    )
    status = "PASS" if passes else "WATCH" if (wr >= 0.50 and n >= 50) else "FAIL"

    return {
        "status": status,
        "n": n,
        "wr": round(wr, 4),
        "pf": round(pf, 4),
        "avg_win_pct": round(avg_win, 3),
        "avg_loss_pct": round(avg_loss, 3),
        "carry_spearman": round(carry_spearman, 4) if carry_spearman is not None else None,
        "walk_forward": wf,
        "acceptance_criteria": {
            "min_wr": ACCEPT_MIN_WR,
            "min_n": ACCEPT_MIN_N,
            "eff_floor": ACCEPT_EFF_FLOOR,
            "min_windows": ACCEPT_MIN_WINDOWS,
        },
        "signal_records": records,
        "sample_window": {
            "start": records[0]["date"] if records else None,
            "end": records[-1]["date"] if records else None,
        },
        "parameters": {
            "hold_days": hold_days,
            "carry_threshold": CARRY_THRESHOLD,
            "years": years,
            "etf_basket": SECTOR_ETFS,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="H-037 VIX term-structure carry backtest")
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout")
    parser.add_argument("--years", type=int, default=YEARS_DEFAULT)
    parser.add_argument("--hold-days", type=int, default=HOLD_DAYS_DEFAULT)
    args = parser.parse_args()

    result = backtest(years=args.years, hold_days=args.hold_days)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    # Human-readable summary
    print("\n" + "=" * 64)
    print("H-037: VIX TERM-STRUCTURE CARRY — BACKTEST RESULTS")
    print("=" * 64)
    print(f"Status:           {result['status']}")
    print(f"N (LONG signals): {result['n']}")
    if result.get("wr") is not None:
        print(f"Win Rate:         {result['wr']:.1%}  (min {ACCEPT_MIN_WR:.0%})")
        print(f"Profit Factor:    {result['pf']:.3f}")
        print(f"Avg Win:          {result['avg_win_pct']:+.3f}%")
        print(f"Avg Loss:         {result['avg_loss_pct']:+.3f}%")
    if result.get("carry_spearman") is not None:
        print(f"Carry→Fwd Spearman: {result['carry_spearman']:+.4f}")
    if result.get("walk_forward"):
        wf = result["walk_forward"]
        print(f"\nWalk-Forward ({len(wf['folds'])} folds):")
        for i, wr_f in enumerate(wf["folds"]):
            flag = "✓" if wr_f >= ACCEPT_MIN_WR else "✗"
            print(f"  Fold {i+1}: {wr_f:.1%}  {flag}")
        print(f"  Efficiency: {wf['eff']:.0%}  (floor: {ACCEPT_EFF_FLOOR:.0%})")
        print(f"  Admissible: {wf['admissible']}")
    if result.get("sample_window"):
        sw = result["sample_window"]
        print(f"\nSample:  {sw['start']} → {sw['end']}")
    if result.get("error"):
        print(f"\nError: {result['error']}")
    print("=" * 64)

    # Print first 5 signal records as examples
    if result.get("signal_records"):
        print("\nSample LONG-signal records (first 5):")
        for r in result["signal_records"][:5]:
            win_str = "WIN" if r["win"] else "LOSS"
            print(f"  {r['date']}  VIX={r['vix_spot']:.1f}  VIX3M={r['vix_3m']:.1f}"
                  f"  carry={r['carry']:+.3f}  basket={r['basket_return_pct']:+.3f}%  {win_str}")


if __name__ == "__main__":
    main()
