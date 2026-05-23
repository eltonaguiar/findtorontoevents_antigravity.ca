#!/usr/bin/env python3
"""UST time-series momentum (TSMOM) sidecar with vol-targeting (Agent C #2).

Implements Sihvonen 2024 "Yield Curve Momentum" (SSRN 3965229) — paper reports
Sharpe 0.7-1.0 across UST and broad bond proxies using 12-month time-series
momentum with realized-volatility position sizing:
  (a) 12-month total return per UST/bond proxy
  (b) Long if 12mo return > 0, short (or flat) if < 0
  (c) Size each leg inversely to 90-day realized vol (vol-targeting)
  (d) Monthly rebalance

This is an OPT-IN SIDECAR per CLAUDE.md Wire-Up Rule. No production picks gated.

## Wiring Plan

Phase 1 (this PR): sidecar emits `audit_dashboard/data/ust_tsmom.json` with
per-symbol 12mo momentum + 90d realized vol + vol-targeted position size +
suggested long/short/flat basket. Read-only on DB.

Phase 2 (follow-up): consumed by `audit_trail/dashboard_generator.py` to surface
BOND Tier-1 candidates alongside the existing ETF/BOND health tiles (currently
BOND n=18 below charter floor per CLAUDE.md asset_class_health).

Phase 3 (post-SHADOW): wired into `alpha_engine/strategies/` as
`ust_tsmom_strategy.py` emitting monthly-rebalance picks tagged for paper-trading.

## Data sources

- Free path: yfinance ETF proxies — TLT (20+yr UST), IEF (7-10yr UST),
  SHY (1-3yr UST), GOVT (broad UST), AGG (US bonds composite),
  HYG (high yield corp), LQD (corporate IG)
- Premium path: Bloomberg / FRED direct yield-curve constant-maturity series
  (T10Y, T2Y, T30Y) would give a cleaner replication of Sihvonen's actual
  yield-curve momentum signal. ETF proxies are good enough for an opt-in
  sidecar acceptance test.

## References

- Sihvonen 2024 — SSRN 3965229 "Yield Curve Momentum"
- Moskowitz, Ooi, Pedersen 2012 — "Time Series Momentum" JFE (original TSMOM)
- Agent C external-research synthesis 2026-05-12
- Master plan: updates/2026-05-11-money-maker-master-plan.html

Usage:
    python tools/research/ust_tsmom.py             # default 7-symbol UST/bond basket
    python tools/research/ust_tsmom.py --dry-run   # no JSON write
    python tools/research/ust_tsmom.py --vol-target 10  # 10% annualized vol target
    python tools/research/ust_tsmom.py --lookback 12    # 12-month TSMOM lookback
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# Sihvonen 2024 UST-curve + broad bond proxies (free yfinance path)
DEFAULT_SYMBOLS = [
    "TLT",   # iShares 20+ Year Treasury Bond
    "IEF",   # iShares 7-10 Year Treasury Bond
    "SHY",   # iShares 1-3 Year Treasury Bond
    "GOVT",  # iShares US Treasury Bond (broad)
    "AGG",   # iShares Core US Aggregate Bond
    "HYG",   # iShares iBoxx High Yield Corporate Bond
    "LQD",   # iShares iBoxx Investment Grade Corporate Bond
]


def fetch_tsmom_vol(symbols, lookback_months=12, vol_window_days=90):
    """For each symbol fetch lookback-month return + N-day annualized vol.

    Returns list of dicts: {ticker, last_close, mom_12_pct,
    vol_90d_annualized_pct, signal, history_len_days}.
    """
    try:
        import yfinance as yf
    except ImportError:
        print("ERROR: yfinance not installed. pip install yfinance", file=sys.stderr)
        return []

    rows = []
    end = datetime.now(timezone.utc).date()
    # +2 month padding to handle weekends/holidays + warmup for vol window
    start = end - timedelta(days=int(30.4 * (lookback_months + 2)))

    for sym in symbols:
        try:
            t = yf.Ticker(sym)
            hist = t.history(start=start, end=end, auto_adjust=True, prepost=False)
            if hist is None or len(hist) < 200:
                rows.append({"ticker": sym, "error": f"insufficient history len={len(hist) if hist is not None else 0}"})
                continue

            closes = hist["Close"].dropna()
            if len(closes) < 200:
                rows.append({"ticker": sym, "error": f"insufficient closes len={len(closes)}"})
                continue

            n = len(closes)
            # 12-month total return: t_0 vs t-252 trading days
            t_lookback = closes.iloc[max(0, n - 252)]
            t_now = closes.iloc[-1]
            mom_pct = float((t_now / t_lookback - 1.0) * 100.0) if t_lookback > 0 else 0.0

            # 90-day annualized realized volatility (daily log returns)
            recent = closes.iloc[-(vol_window_days + 1):]
            daily_rets = (recent / recent.shift(1)).dropna().apply(math.log)
            if len(daily_rets) >= 20:
                daily_std = float(daily_rets.std(ddof=1))
                vol_annualized = daily_std * math.sqrt(252) * 100.0
            else:
                vol_annualized = 0.0

            # Signal: long if mom > 0, short if mom < 0, flat if vol degenerate
            if vol_annualized <= 0.0:
                signal = "flat"
            elif mom_pct > 0:
                signal = "long"
            elif mom_pct < 0:
                signal = "short"
            else:
                signal = "flat"

            rows.append({
                "ticker": sym,
                "last_close": float(t_now),
                "mom_12_pct": round(mom_pct, 3),
                "vol_90d_annualized_pct": round(vol_annualized, 3),
                "signal": signal,
                "history_len_days": int(n),
            })
        except Exception as e:
            rows.append({"ticker": sym, "error": str(e)[:100]})
    return rows


def vol_target_basket(rows, vol_target_pct=10.0):
    """Size each non-flat leg inversely to its realized vol.

    position_size_pct = vol_target_pct / realized_vol_pct, capped at 100% per
    leg (no implicit leverage above 1x in this opt-in sidecar). Sum can exceed
    100% across legs — caller decides on portfolio-level leverage cap.
    """
    valid = [r for r in rows if "error" not in r]
    if not valid:
        return {"error": "no valid rows"}

    longs, shorts, cash = [], [], []
    for r in valid:
        vol = r["vol_90d_annualized_pct"]
        if vol > 0 and r["signal"] in ("long", "short"):
            raw_size = vol_target_pct / vol
            size = min(raw_size, 1.0) * 100.0  # cap at 100% (1x notional)
            r["vol_target_position_size_pct"] = round(size, 3)
            if r["signal"] == "long":
                longs.append(r["ticker"])
            else:
                shorts.append(r["ticker"])
        else:
            r["vol_target_position_size_pct"] = 0.0
            cash.append(r["ticker"])

    total_long_notional = sum(r["vol_target_position_size_pct"] for r in valid if r["signal"] == "long")
    total_short_notional = sum(r["vol_target_position_size_pct"] for r in valid if r["signal"] == "short")

    return {
        "vol_target_pct": vol_target_pct,
        "n_valid": len(valid),
        "longs": sorted(longs),
        "shorts": sorted(shorts),
        "cash": sorted(cash),
        "total_long_notional_pct": round(total_long_notional, 3),
        "total_short_notional_pct": round(total_short_notional, 3),
        "expected_signal_strength": (
            "STRONG" if (longs and shorts) else
            "MODERATE" if (longs or shorts) else
            "WEAK_OR_FLAT"
        ),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--symbols", nargs="*", default=DEFAULT_SYMBOLS,
                   help="UST/bond ETF tickers (default 7-sym Sihvonen-style universe)")
    p.add_argument("--lookback", type=int, default=12,
                   help="TSMOM lookback in months (default 12)")
    p.add_argument("--vol-target", type=float, default=10.0,
                   help="Annualized vol target in pct (default 10.0)")
    p.add_argument("--vol-window", type=int, default=90,
                   help="Realized-vol window in calendar days (default 90)")
    p.add_argument("--dry-run", action="store_true", help="Print results, don't write JSON")
    p.add_argument("--out", default="audit_dashboard/data/ust_tsmom.json",
                   help="Output JSON path (relative to repo root)")
    args = p.parse_args()

    print(f"# ust_tsmom sidecar (Sihvonen 2024 yield-curve momentum)", file=sys.stderr)
    print(f"# universe: {len(args.symbols)} symbols  lookback: {args.lookback}mo  vol-target: {args.vol_target}%", file=sys.stderr)

    rows = fetch_tsmom_vol(args.symbols, lookback_months=args.lookback, vol_window_days=args.vol_window)
    basket = vol_target_basket(rows, vol_target_pct=args.vol_target)

    err_count = sum(1 for r in rows if "error" in r)
    print(f"# fetched: {len(rows) - err_count} valid, {err_count} errors", file=sys.stderr)
    if "error" not in basket:
        print(f"# LONGS:  {basket['longs']}", file=sys.stderr)
        print(f"# SHORTS: {basket['shorts']}", file=sys.stderr)
        print(f"# CASH:   {basket['cash']}", file=sys.stderr)
        print(f"# signal: {basket['expected_signal_strength']}", file=sys.stderr)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy_name": "ust_tsmom_level",
        "reference": "Sihvonen 2024 — SSRN 3965229 'Yield Curve Momentum'; Moskowitz/Ooi/Pedersen 2012 JFE TSMOM",
        "expected_sharpe_range": [0.7, 1.0],
        "etf_proxy_caveat": "Free-path uses UST/bond ETF proxies (TLT/IEF/SHY/GOVT/AGG/HYG/LQD). Sihvonen's original uses constant-maturity yield-curve series (premium FRED/Bloomberg). Treat as MODERATE-confidence signal until premium-path replication.",
        "wiring_status": "OPT_IN_SIDECAR — not yet consumed by production pick path. See follow-up wire-up in audit_trail/dashboard_generator.py.",
        "universe": args.symbols,
        "lookback_months": args.lookback,
        "vol_window_days": args.vol_window,
        "vol_target_pct": args.vol_target,
        "rebalance_frequency": "monthly",
        "rows": rows,
        "decision": basket,
    }

    if args.dry_run:
        print(json.dumps(payload, indent=2))
        print("# dry-run: not writing JSON", file=sys.stderr)
        return

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"# wrote {out_path}  ({out_path.stat().st_size:,} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()
