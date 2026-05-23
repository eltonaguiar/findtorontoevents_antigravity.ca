#!/usr/bin/env python3
"""Sector dual-momentum (Antonacci GEM 12-1) sidecar (Agent C #2, EQUITY EDGE).

Sister sidecar to `tools/research/commodity_carry_momo.py` (shipped 2026-05-12).
Same opt-in pattern, same free-data path (yfinance), different asset class.

Implements Antonacci 2014 "Dual Momentum Investing" Global Equities Momentum
(GEM) extended to US sector ETFs per Zarattini & Antonacci 2024 "Sector
Dual Momentum" (SSRN 4857230) — paper reports Sharpe 0.8-1.1 with MDD < 15%
on the 9-SPDR universe with monthly rebalance.

Rule (12-1 month dual momentum):
  1. Rank universe by 12-1 month return (12-month return EXCLUDING the most
     recent month — skips short-term reversal).
  2. Absolute-momentum filter: if SPY 12-1 mom > 0 → RISK_ON, hold top-3
     sectors equal-weight.
  3. Else RISK_OFF → rotate entire allocation to AGG (US aggregate bond).

This is an OPT-IN SIDECAR per CLAUDE.md Wire-Up Rule. No production picks gated.

## Wiring Plan

Phase 1 (this PR): sidecar emits `audit_dashboard/data/sector_dual_momentum.json`
with per-ETF 12-1 momentum + current rank + regime decision. Read-only on DB.

Phase 2 (follow-up): consumed by `audit_trail/dashboard_generator.py` to surface
EQUITY Tier-1 candidates alongside existing equity edge sources.

Phase 3 (post-SHADOW): wired into `alpha_engine/strategies/` as
`sector_dual_momentum_strategy.py` emitting monthly-rebalance picks tagged for
paper-trading (TV `MONTHLY_GEM` paper account).

## Data sources

- Free path: yfinance daily closes for 9 SPDR sector ETFs (XLE, XLF, XLK, XLV,
  XLI, XLP, XLY, XLU, XLB) + XLRE if available + SPY, VEU, AGG, TLT benchmarks.
- Premium path: not required — Zarattini/Antonacci 2024 result is reproducible
  from free daily-close data alone (monthly rebalance, no intraday needed).

## References

- Antonacci 2014 — "Dual Momentum Investing" (McGraw-Hill, ISBN 978-0071849449)
- Zarattini & Antonacci 2024 — SSRN 4857230 ("Sector Dual Momentum")
- Agent C external-research synthesis 2026-05-12
- Anti-overfit DSR sidecar: audit_dashboard/data/anti_overfit_audit.json
- Master plan: updates/2026-05-11-money-maker-master-plan.html
- Sister sidecar: tools/research/commodity_carry_momo.py

Usage:
    python tools/research/sector_dual_momentum.py            # default 9-SPDR + benchmarks
    python tools/research/sector_dual_momentum.py --dry-run  # no JSON write
    python tools/research/sector_dual_momentum.py --universe XLE XLF XLK  # override basket
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# 9 SPDR sector ETFs (Zarattini/Antonacci 2024 universe) + XLRE (real estate, post-2015)
DEFAULT_SECTORS = [
    "XLE",   # Energy
    "XLF",   # Financials
    "XLK",   # Technology
    "XLV",   # Health care
    "XLI",   # Industrials
    "XLP",   # Consumer staples
    "XLY",   # Consumer discretionary
    "XLU",   # Utilities
    "XLB",   # Materials
    "XLRE",  # Real estate (post-2015; include if history available)
]

# Benchmarks for absolute-momentum filter + risk-off rotation
BENCHMARKS = [
    "SPY",   # US equity benchmark (gate for risk_on/risk_off)
    "VEU",   # International ex-US (optional GEM expansion)
    "AGG",   # US aggregate bond (risk_off destination)
    "TLT",   # 20+ year Treasury (alternative risk_off)
]

DEFAULT_UNIVERSE = DEFAULT_SECTORS + BENCHMARKS


def fetch_momentum_12_1(symbols, lookback_months=12, skip_months=1):
    """For each symbol fetch 12-1 month return (12mo ret excluding last month).

    Returns list of dicts: {ticker, last_close, mom_12_1_pct, history_len_days}.
    """
    try:
        import yfinance as yf
    except ImportError:
        print("ERROR: yfinance not installed. pip install yfinance", file=sys.stderr)
        return []

    rows = []
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=int(30.4 * (lookback_months + 2)))

    for sym in symbols:
        try:
            t = yf.Ticker(sym)
            hist = t.history(start=start, end=end, auto_adjust=False, prepost=False)
            if hist is None or len(hist) < 200:
                rows.append({"ticker": sym, "error": f"insufficient history len={len(hist) if hist is not None else 0}"})
                continue

            closes = hist["Close"].dropna()
            if len(closes) < 200:
                rows.append({"ticker": sym, "error": f"insufficient closes len={len(closes)}"})
                continue

            # 12-1 momentum: return from t-12mo to t-1mo (skip last month to
            # avoid short-term reversal noise per Antonacci 2014)
            n = len(closes)
            t_12mo = closes.iloc[max(0, n - 252)]  # ~252 trading days = 12mo
            t_1mo = closes.iloc[max(0, n - 21)]    # ~21 trading days = 1mo
            mom_12_1 = float((t_1mo / t_12mo - 1.0) * 100.0) if t_12mo > 0 else 0.0

            rows.append({
                "ticker": sym,
                "last_close": float(closes.iloc[-1]),
                "mom_12_1_pct": round(mom_12_1, 3),
                "history_len_days": int(n),
            })
        except Exception as e:
            rows.append({"ticker": sym, "error": str(e)[:100]})
    return rows


def build_decision(rows, sectors, top_n=3, risk_off_ticker="AGG"):
    """Antonacci dual-momentum decision.

    1. SPY 12-1 mom > 0 → RISK_ON, hold top-`top_n` sectors equal-weight.
    2. Else RISK_OFF → rotate entire allocation to `risk_off_ticker`.

    Returns dict with `regime`, `basket`, `current_rank` per row, etc.
    """
    valid = [r for r in rows if "error" not in r]
    by_ticker = {r["ticker"]: r for r in valid}

    spy = by_ticker.get("SPY")
    if spy is None:
        return {"error": "SPY missing from valid rows — cannot determine regime"}

    spy_mom = spy["mom_12_1_pct"]
    risk_on = spy_mom > 0.0

    # Rank sectors (only those present + valid)
    sector_rows = [r for r in valid if r["ticker"] in sectors]
    sector_sorted = sorted(sector_rows, key=lambda r: r["mom_12_1_pct"], reverse=True)

    # Annotate current_rank on every sector row (1 = best 12-1 momentum)
    rank_map = {r["ticker"]: i + 1 for i, r in enumerate(sector_sorted)}
    for r in valid:
        if r["ticker"] in rank_map:
            r["current_rank"] = rank_map[r["ticker"]]

    if risk_on:
        basket = [r["ticker"] for r in sector_sorted[:top_n] if r["mom_12_1_pct"] > 0]
        if len(basket) < top_n:
            # Antonacci: only hold sectors with own positive momentum AND positive SPY
            # If fewer than top_n sectors have positive momentum, partially de-risk
            note = f"only {len(basket)} sectors have positive 12-1 momentum; partial allocation"
        else:
            note = f"top-{top_n} sector basket on positive SPY 12-1 momentum"
        signal_strength = "STRONG" if (len(basket) == top_n and spy_mom > 5.0) else "MODERATE"
    else:
        basket = [risk_off_ticker]
        note = f"SPY 12-1 momentum ({spy_mom:.2f}%) <= 0 → rotate to {risk_off_ticker}"
        signal_strength = "STRONG" if spy_mom < -5.0 else "MODERATE"

    return {
        "regime": "risk_on" if risk_on else "risk_off",
        "spy_mom_12_1_pct": spy_mom,
        "basket": basket,
        "top_n": top_n,
        "risk_off_ticker": risk_off_ticker,
        "sector_ranking": [
            {"ticker": r["ticker"], "mom_12_1_pct": r["mom_12_1_pct"], "rank": rank_map[r["ticker"]]}
            for r in sector_sorted
        ],
        "note": note,
        "expected_signal_strength": signal_strength,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--universe", nargs="*", default=DEFAULT_UNIVERSE,
                   help="ETF tickers (default: 9 SPDR sectors + XLRE + SPY/VEU/AGG/TLT)")
    p.add_argument("--top-n", type=int, default=3,
                   help="Number of top-momentum sectors to hold in risk_on regime (default 3)")
    p.add_argument("--risk-off-ticker", default="AGG",
                   help="Ticker to rotate to in risk_off regime (default AGG)")
    p.add_argument("--dry-run", action="store_true", help="Print results, don't write JSON")
    p.add_argument("--out", default="audit_dashboard/data/sector_dual_momentum.json",
                   help="Output JSON path (relative to repo root)")
    args = p.parse_args()

    print(f"# sector_dual_momentum sidecar (Antonacci GEM 12-1)", file=sys.stderr)
    print(f"# universe: {len(args.universe)} tickers  top_n: {args.top_n}  risk_off: {args.risk_off_ticker}", file=sys.stderr)

    rows = fetch_momentum_12_1(args.universe)

    # Sectors = universe minus benchmarks (anything in BENCHMARKS list is excluded
    # from the rankable sector basket but kept in rows for reporting)
    sectors_in_universe = [s for s in args.universe if s not in BENCHMARKS]
    decision = build_decision(rows, sectors_in_universe, top_n=args.top_n,
                              risk_off_ticker=args.risk_off_ticker)

    err_count = sum(1 for r in rows if "error" in r)
    print(f"# fetched: {len(rows) - err_count} valid, {err_count} errors", file=sys.stderr)
    if "error" not in decision:
        print(f"# regime:  {decision['regime']}  (SPY 12-1 = {decision['spy_mom_12_1_pct']:.2f}%)", file=sys.stderr)
        print(f"# basket:  {decision['basket']}", file=sys.stderr)
        print(f"# signal:  {decision['expected_signal_strength']}", file=sys.stderr)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy_name": "sector_dual_momentum_12_1",
        "reference": "Antonacci 2014 GEM (ISBN 978-0071849449); Zarattini & Antonacci 2024 — SSRN 4857230",
        "expected_sharpe_range": [0.8, 1.1],
        "expected_max_drawdown_pct": 15.0,
        "rebalance_frequency": "monthly",
        "method_caveat": "12-1 momentum skips most-recent month to avoid short-term reversal. Absolute-momentum filter on SPY gates risk_on vs risk_off. Free yfinance daily closes are sufficient — no premium data required.",
        "wiring_status": "OPT_IN_SIDECAR — not yet consumed by production pick path. See follow-up wire-up in audit_trail/dashboard_generator.py.",
        "universe": args.universe,
        "sector_universe": sectors_in_universe,
        "benchmark_universe": [s for s in args.universe if s in BENCHMARKS],
        "lookback_months": 12,
        "skip_months": 1,
        "top_n": args.top_n,
        "risk_off_ticker": args.risk_off_ticker,
        "per_etf": rows,
        "decision": decision,
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
