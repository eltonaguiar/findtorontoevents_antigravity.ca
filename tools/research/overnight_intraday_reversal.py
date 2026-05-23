#!/usr/bin/env python3
"""Overnight-Intraday Reversal sidecar (Liu, Liu, Wang, Zhou, Zhu replication).

Implements the "Overnight-Intraday Reversal Everywhere" anomaly: prior-day
intraday returns ((close-open)/open) negatively predict next-day overnight
returns. Long the worst intraday losers at today's close, hold overnight,
close at tomorrow's open.

Paper reports Sharpe 1.5-2.5 across global equity markets.

This is an OPT-IN SIDECAR per CLAUDE.md Wire-Up Rule. No production picks gated.

## Wiring Plan

Phase 1 (this PR): sidecar emits
`audit_dashboard/data/overnight_intraday_reversal.json` with per-symbol
intraday returns + quintile ranks + suggested basket. Read-only on DB.

Phase 2 (follow-up): consumed by `audit_trail/dashboard_generator.py` to
surface EQUITY Tier-1 candidates alongside the existing Tier-2 EQUITY edge
(PF 1.41 / WR 52.7% / n=421 per asset_class_health 2026-05-03).

Phase 3 (post-SHADOW): wired into `alpha_engine/strategies/` as
`overnight_intraday_reversal_strategy.py` emitting picks tagged for paper-
trading with overnight-only hold horizon (close-to-open).

## Data sources

- Free path: yfinance daily OHLC for ~30 large-cap US equities (top SPY
  components by weight). auto_adjust=False + prepost=False for clean
  regular-hours OHLC.
- No premium data required — strategy is fully reproducible from public OHLC.

## References

- Liu, Liu, Wang, Zhou, Zhu — "Overnight-Intraday Reversal Everywhere"
  SSRN 2730304
- Agent C external-research synthesis 2026-05-12
- Master plan: updates/2026-05-11-money-maker-master-plan.html
- Sister sidecar: tools/research/commodity_carry_momo.py (Miffre 2010)

Usage:
    python tools/research/overnight_intraday_reversal.py            # default 30-symbol basket
    python tools/research/overnight_intraday_reversal.py --dry-run  # no JSON write
    python tools/research/overnight_intraday_reversal.py --quintile 6  # top/bottom 20% of 30
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# Top ~30 SPY components by weight (large-cap US equities)
DEFAULT_SYMBOLS = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "META",
    "AMZN", "BRK-B", "JPM", "V", "MA",
    "JNJ", "WMT", "PG", "XOM", "HD",
    "CVX", "KO", "LLY", "MRK", "ABBV",
    "COST", "PEP", "AVGO", "ADBE", "NFLX",
    "CRM", "AMD", "INTC", "IBM", "DIS",
]


def fetch_intraday_returns(symbols, lookback_days=30):
    """For each symbol fetch prior-day intraday return ((close-open)/open).

    Returns list of dicts: {ticker, last_open, last_close,
    intraday_return_pct, history_len_days}.
    """
    try:
        import yfinance as yf
    except ImportError:
        print("ERROR: yfinance not installed. pip install yfinance", file=sys.stderr)
        return []

    rows = []
    end = datetime.now(timezone.utc).date() + timedelta(days=1)
    start = end - timedelta(days=lookback_days + 10)

    for sym in symbols:
        try:
            t = yf.Ticker(sym)
            hist = t.history(start=start, end=end, auto_adjust=False, prepost=False)
            if hist is None or len(hist) < 2:
                rows.append({"ticker": sym, "error": f"insufficient history len={len(hist) if hist is not None else 0}"})
                continue

            opens = hist["Open"].dropna()
            closes = hist["Close"].dropna()
            if len(opens) < 2 or len(closes) < 2:
                rows.append({"ticker": sym, "error": f"insufficient OHLC len={len(opens)}/{len(closes)}"})
                continue

            last_open = float(opens.iloc[-1])
            last_close = float(closes.iloc[-1])
            intraday_return_pct = ((last_close / last_open) - 1.0) * 100.0 if last_open > 0 else 0.0

            rows.append({
                "ticker": sym,
                "last_open": round(last_open, 4),
                "last_close": round(last_close, 4),
                "intraday_return_pct": round(intraday_return_pct, 4),
                "history_len_days": int(len(closes)),
            })
        except Exception as e:
            rows.append({"ticker": sym, "error": str(e)[:100]})
    return rows


def rank_and_basket(rows, quintile=6):
    """Rank by intraday return (ascending = most-negative first).

    Long bottom-quintile (worst intraday losers) — they have biggest expected
    overnight bounce. Optionally short top-quintile (best intraday winners) —
    they have expected overnight mean-reversion.

    Returns dict with `longs`, `shorts`, ranked rows, signal strength.
    """
    valid = [r for r in rows if "error" not in r]
    if len(valid) < quintile * 2:
        return {"error": f"insufficient valid rows ({len(valid)}) for quintile size {quintile}"}

    # Ascending sort: most-negative intraday return first (bottom = worst losers)
    ranked = sorted(valid, key=lambda r: r["intraday_return_pct"])
    for i, r in enumerate(ranked):
        r["rank"] = i + 1  # 1 = worst intraday (target LONG)

    longs = [r["ticker"] for r in ranked[:quintile]]
    shorts = [r["ticker"] for r in ranked[-quintile:]]

    return {
        "quintile_size": quintile,
        "n_valid": len(valid),
        "longs": longs,
        "shorts": shorts,
        "neutrals": [r["ticker"] for r in ranked[quintile:-quintile]],
        "ranked_rows": ranked,
        "expected_signal_strength": (
            "STRONG" if (longs and shorts and abs(ranked[0]["intraday_return_pct"]) > 1.0) else
            "MODERATE" if (longs or shorts) else
            "WEAK_OR_FLAT"
        ),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--symbols", nargs="*", default=DEFAULT_SYMBOLS,
                   help="Equity tickers (default 30-sym large-cap US universe)")
    p.add_argument("--quintile", type=int, default=6,
                   help="Quintile size for top/bottom (default 6 for 30-sym universe = 20%%)")
    p.add_argument("--dry-run", action="store_true", help="Print results, don't write JSON")
    p.add_argument("--out", default="audit_dashboard/data/overnight_intraday_reversal.json",
                   help="Output JSON path (relative to repo root)")
    args = p.parse_args()

    print(f"# overnight_intraday_reversal sidecar (Liu et al SSRN 2730304)", file=sys.stderr)
    print(f"# universe: {len(args.symbols)} symbols  quintile: {args.quintile}", file=sys.stderr)

    rows = fetch_intraday_returns(args.symbols)
    basket = rank_and_basket(rows, args.quintile)

    err_count = sum(1 for r in rows if "error" in r)
    print(f"# fetched: {len(rows) - err_count} valid, {err_count} errors", file=sys.stderr)
    if "error" not in basket:
        print(f"# LONGS  (bottom-quintile, worst intraday): {basket['longs']}", file=sys.stderr)
        print(f"# SHORTS (top-quintile, best intraday):    {basket['shorts']}", file=sys.stderr)
        print(f"# signal: {basket['expected_signal_strength']}", file=sys.stderr)

    # Trim ranked_rows out of basket for top-level per_symbol view; basket still has them
    per_symbol = []
    if "error" not in basket:
        for r in basket["ranked_rows"]:
            per_symbol.append({
                "ticker": r["ticker"],
                "last_open": r["last_open"],
                "last_close": r["last_close"],
                "intraday_return_pct": r["intraday_return_pct"],
                "rank": r["rank"],
                "history_len_days": r["history_len_days"],
            })
    else:
        # Even on basket error, expose raw rows for debugging
        for r in rows:
            if "error" not in r:
                per_symbol.append({
                    "ticker": r["ticker"],
                    "last_open": r["last_open"],
                    "last_close": r["last_close"],
                    "intraday_return_pct": r["intraday_return_pct"],
                    "rank": None,
                    "history_len_days": r["history_len_days"],
                })

    decision = (
        {
            "longs": basket["longs"],
            "shorts": basket["shorts"],
            "expected_signal_strength": basket["expected_signal_strength"],
        }
        if "error" not in basket
        else {"longs": [], "shorts": [], "expected_signal_strength": "ERROR",
              "error": basket["error"]}
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy_name": "overnight_intraday_reversal",
        "reference": "Liu, Liu, Wang, Zhou, Zhu — 'Overnight-Intraday Reversal Everywhere' SSRN 2730304",
        "expected_sharpe_range": [1.5, 2.5],
        "hold_horizon": "overnight (close-to-next-open, ~16h)",
        "rebalance": "daily",
        "rule": "Rank by prior-day intraday return ((close-open)/open). Long bottom-quintile, short top-quintile if long-short. Close at next open.",
        "wiring_status": "OPT_IN_SIDECAR — not yet consumed by production pick path. See follow-up wire-up in audit_trail/dashboard_generator.py.",
        "universe": args.symbols,
        "quintile_size": args.quintile,
        "errors": [r for r in rows if "error" in r],
        "per_symbol": per_symbol,
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
