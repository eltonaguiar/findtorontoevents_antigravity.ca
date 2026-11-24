"""H-147, portfolio form: regress the EQUAL-WEIGHT BOOK on SPY.

Per-trade beta was not reliably estimable (mean beta -64.5 before clipping,
because one symbol's covariance dominated). The portfolio series is estimable:
each open pick is one unit, the book's daily return is the equal-weight mean of
the picks open that day, and the regression is on the SERIES, which uses every
pick that has entry and exit timestamps instead of only the price-covered ones.

Convention: each pick's total return is accrued evenly across its business-day
holding period. That preserves totals and avoids needing intraday paths, but it
SMOOTHS the series, which understates beta and overstates t-stats. Results are
therefore reported next to the per-trade estimate, not instead of it.

Usage: python3 tools/portfolio_beta_regression.py --out reports/portfolio_beta_2026-11-20.json
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from alpha_engine.pick_contract import derive_entry_time  # noqa: E402

PICKS = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"


def _dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def spy_calendar(start: str, end: str, use_network: bool = True):
    """Business-day closes for SPY; falls back to a synthetic calendar offline."""
    if use_network:
        try:
            import yfinance as yf
            df = yf.download("SPY", start=start, end=end, auto_adjust=True, progress=False)
            closes = df["Close"].dropna()
            return [d.date() for d in closes.index], np.asarray(closes, dtype=float).ravel()
        except Exception:                                   # noqa: BLE001
            pass
    d0 = datetime.fromisoformat(start).date()
    d1 = datetime.fromisoformat(end).date()
    days, cur = [], d0
    while cur <= d1:
        if cur.weekday() < 5:
            days.append(cur)
        cur = cur.fromordinal(cur.toordinal() + 1)
    return days, np.full(len(days), np.nan)


def ols(y: np.ndarray, x: np.ndarray) -> dict:
    n = len(y)
    X = np.column_stack([np.ones(n), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = n - 2
    if dof <= 0:
        return {"alpha_daily": float(beta[0]), "beta": float(beta[1]),
                "t_alpha": None, "t_beta": None}
    sigma2 = float(resid @ resid) / dof
    xtx_inv = np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(sigma2 * xtx_inv))
    return {"alpha_daily": float(beta[0]), "beta": float(beta[1]),
            "t_alpha": float(beta[0] / se[0]) if se[0] else None,
            "t_beta": float(beta[1] / se[1]) if se[1] else None}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports/portfolio_beta_2026-11-20.json")
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    rows = json.loads(PICKS.read_text())["picks"]["recent_closed"]
    picks = []
    for r in rows:
        ts, _ = derive_entry_time(r)
        entry, exit_ = _dt(ts), _dt(r.get("closed_at"))
        try:
            pnl = float(r.get("pnl_pct")) / 100.0
        except (TypeError, ValueError):
            continue
        if entry and exit_ and exit_ > entry:
            picks.append({"entry": entry, "exit": exit_, "pnl": pnl,
                          "cls": (r.get("asset_class") or "?").upper()})
    if not picks:
        raise SystemExit("no picks with both timestamps")

    start = min(p["entry"] for p in picks).date().isoformat()
    last = max(p["exit"] for p in picks).date()
    end = last.fromordinal(last.toordinal() + 1).isoformat()
    days, spy = spy_calendar(start, end, use_network=not args.offline)
    idx = {d: i for i, d in enumerate(days)}

    sums = np.zeros(len(days))
    counts = np.zeros(len(days), dtype=int)
    skipped = 0
    for p in picks:
        i, j = idx.get(p["entry"].date()), idx.get(p["exit"].date())
        if i is None or j is None or j <= i:
            skipped += 1
            continue
        per_day = p["pnl"] / (j - i)
        sums[i:j] += per_day
        counts[i:j] += 1
    active = counts > 0
    port = np.where(active, sums / np.maximum(counts, 1), np.nan)
    spy_r = np.concatenate([[np.nan], spy[1:] / spy[:-1] - 1])

    mask = active & np.isfinite(spy_r) & np.isfinite(port)
    if mask.sum() < 30:
        raise SystemExit(f"only {int(mask.sum())} usable days")
    res = ols(port[mask], spy_r[mask])
    res.update({
        "n_days": int(mask.sum()),
        "n_picks_used": len(picks) - skipped,
        "picks_skipped_no_day": skipped,
        "mean_daily_book_return_pct": round(float(np.nanmean(port[mask])) * 100, 5),
        "alpha_annualised_pct": round(res["alpha_daily"] * 252 * 100, 3),
        "mean_daily_spy_pct": round(float(np.nanmean(spy_r[mask])) * 100, 5),
        "corr": round(float(np.corrcoef(port[mask], spy_r[mask])[0, 1]), 4),
        "cum_book_pct": round(float(np.nansum(port[mask])) * 100, 2),
        "cum_spy_pct": round(float(np.nansum(spy_r[mask])) * 100, 2),
        "convention": "even accrual of each pick's total return across its business-day hold",
        "caveat": "accrual smooths the series: understates beta and overstates t-stats",
    })
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    print(f"  written -> {args.out}")


if __name__ == "__main__":
    main()
