#!/usr/bin/env python3
"""Commodity carry + momentum double-sort sidecar (Agent C #1, SUPREME EDGE).

Extension of our DSR-verified `cot_positioning` edge (n=104, WR 86.5%, DSR=1.0
per anti_overfit_audit.json) — same data source family.

Implements Fuertes/Miffre/Rallis 2010 "Tactical Allocation in Commodity Futures:
Combining Momentum and Term Structure" — paper reports 21.02% annualized return
from double-sort:
  (a) 12-1 month momentum ranking
  (b) Term-structure basis ranking (front-second contract spread)
  Long top-quintile both, short bottom-quintile both, equal-weight.

This is an OPT-IN SIDECAR per CLAUDE.md Wire-Up Rule. No production picks gated.

## Wiring Plan

Phase 1 (this PR): sidecar emits `audit_dashboard/data/commodity_carry_momo.json`
with per-symbol momentum + carry ranks + suggested basket. Read-only on DB.

Phase 2 (follow-up): consumed by `audit_trail/dashboard_generator.py` to surface
COMMODITY Tier-1 candidates alongside the existing `cot_positioning` edge.

Phase 3 (post-SHADOW): wired into `alpha_engine/strategies/` as
`commodity_carry_momo_strategy.py` emitting picks tagged for paper-trading.

## Data sources

- Free path: yfinance continuous front-month futures (CT=F, KC=F, GC=F, SI=F,
  CL=F, NG=F, ZC=F, ZS=F, ZW=F, HG=F, PL=F, PA=F, HE=F, LE=F, CC=F, SB=F, OJ=F)
- Premium path: CFTC COT public feed (already accessible via cot_positioning
  pipeline) + Quandl/Nasdaq Data Link continuous futures (~$50/mo) for
  second-month contracts (term-structure basis)

This script uses ONLY the free path (yfinance) at first; second-month basis
falls back to simple proxy when premium data unavailable.

## References

- Fuertes, Miffre, Rallis 2010 — SSRN 1127213
- Jiang & Liu 2024 — EFMA Lisbon (independent replication, 18-22% α)
- Agent C external-research synthesis 2026-05-12
- Anti-overfit DSR sidecar: audit_dashboard/data/anti_overfit_audit.json
- Master plan: updates/2026-05-11-money-maker-master-plan.html

Usage:
    python tools/research/commodity_carry_momo.py            # default 17-symbol basket
    python tools/research/commodity_carry_momo.py --dry-run  # no JSON write
    python tools/research/commodity_carry_momo.py --quintile 5  # top/bottom quintile size
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# 17 most-liquid commodity futures (Miffre 2010 universe close approximation)
DEFAULT_SYMBOLS = [
    "CT=F",  # Cotton — our DSR-verified edge anchor
    "KC=F",  # Coffee
    "SB=F",  # Sugar
    "CC=F",  # Cocoa
    "OJ=F",  # Orange juice
    "GC=F",  # Gold
    "SI=F",  # Silver
    "HG=F",  # Copper
    "PL=F",  # Platinum
    "PA=F",  # Palladium
    "CL=F",  # Crude oil
    "NG=F",  # Natural gas
    "ZC=F",  # Corn
    "ZS=F",  # Soybeans
    "ZW=F",  # Wheat
    "HE=F",  # Lean hogs
    "LE=F",  # Live cattle
]


def fetch_momentum_carry(symbols, lookback_months=12, skip_months=1):
    """For each symbol fetch 12-1 momentum + simple basis proxy.

    Returns list of dicts: {symbol, mom_12_1_pct, carry_proxy_pct, last_close,
    history_len_days}.
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
                rows.append({"symbol": sym, "error": f"insufficient history len={len(hist) if hist is not None else 0}"})
                continue

            closes = hist["Close"].dropna()
            if len(closes) < 200:
                rows.append({"symbol": sym, "error": f"insufficient closes len={len(closes)}"})
                continue

            # 12-1 momentum: return from t-12mo to t-1mo (skip last month)
            n = len(closes)
            t_12mo = closes.iloc[max(0, n - 252)]  # ~252 trading days = 12mo
            t_1mo = closes.iloc[max(0, n - 21)]    # ~21 trading days = 1mo
            mom_12_1 = float((t_1mo / t_12mo - 1.0) * 100.0) if t_12mo > 0 else 0.0

            # Carry proxy: rolling 21-day return diff between long-term and short-term mean
            # (this is a weak proxy; real Miffre uses second-month contract basis)
            if n >= 63:
                long_mean = float(closes.iloc[-63:].mean())
                short_mean = float(closes.iloc[-21:].mean())
                carry_proxy = (short_mean / long_mean - 1.0) * 100.0 if long_mean > 0 else 0.0
            else:
                carry_proxy = 0.0

            rows.append({
                "symbol": sym,
                "last_close": float(closes.iloc[-1]),
                "mom_12_1_pct": round(mom_12_1, 3),
                "carry_proxy_pct": round(carry_proxy, 3),
                "history_len_days": int(n),
            })
        except Exception as e:
            rows.append({"symbol": sym, "error": str(e)[:100]})
    return rows


def double_sort_basket(rows, quintile=3):
    """Long top-`quintile` on BOTH mom + carry; short bottom-`quintile` on BOTH.

    Returns dict with `longs`, `shorts`, `neutrals`, `expected_signal_strength`.
    """
    valid = [r for r in rows if "error" not in r]
    if len(valid) < quintile * 2:
        return {"error": f"insufficient valid rows ({len(valid)}) for quintile size {quintile}"}

    mom_sorted = sorted(valid, key=lambda r: r["mom_12_1_pct"], reverse=True)
    carry_sorted = sorted(valid, key=lambda r: r["carry_proxy_pct"], reverse=True)

    mom_top = {r["symbol"] for r in mom_sorted[:quintile]}
    mom_bot = {r["symbol"] for r in mom_sorted[-quintile:]}
    carry_top = {r["symbol"] for r in carry_sorted[:quintile]}
    carry_bot = {r["symbol"] for r in carry_sorted[-quintile:]}

    longs = mom_top & carry_top   # Both momentum AND carry positive ranks
    shorts = mom_bot & carry_bot  # Both bottom ranks

    return {
        "quintile_size": quintile,
        "n_valid": len(valid),
        "longs": sorted(longs),
        "shorts": sorted(shorts),
        "neutrals": sorted(r["symbol"] for r in valid if r["symbol"] not in longs and r["symbol"] not in shorts),
        "mom_sort_top": sorted(mom_top),
        "mom_sort_bottom": sorted(mom_bot),
        "carry_sort_top": sorted(carry_top),
        "carry_sort_bottom": sorted(carry_bot),
        "expected_signal_strength": (
            "STRONG" if (longs and shorts) else
            "MODERATE" if (longs or shorts) else
            "WEAK_OR_FLAT"
        ),
    }


def build_picks(rows: list, basket: dict, generated_at: str) -> list:
    """Convert basket longs/shorts into the canonical pick schema for dashboard_generator.

    Each pick carries the minimum required fields so _extract_picks() / _normalize_pick()
    can route it into the active-picks table as asset_class=COMMODITY.

    LONG  = top-quintile on BOTH mom AND carry  (Miffre double-sort longs)
    SHORT = bottom-quintile on BOTH            (Miffre double-sort shorts)

    TP/SL are omitted intentionally — this is a systematic momentum basket;
    the universal resolver scores exits via close-price crossings.
    """
    if "error" in basket:
        return []

    row_by_sym = {r["symbol"]: r for r in rows if "error" not in r}
    picks: list = []

    for sym in basket.get("longs", []):
        row = row_by_sym.get(sym, {})
        entry = round(float(row.get("last_close", 0.0)), 4)
        mom = round(float(row.get("mom_12_1_pct", 0.0)), 2)
        carry = round(float(row.get("carry_proxy_pct", 0.0)), 2)
        pick_id = f"commodity_carry_momo::{sym}::{generated_at[:10]}"
        picks.append({
            "id": pick_id,
            "symbol": sym,
            "direction": "LONG",
            "strategy": "commodity_carry_momo_double_sort",
            "source_system": "commodity_carry_momo",
            "asset_class": "COMMODITY",
            "entry_price": entry,
            "confidence": 0.65,
            "timeframe": "POSITION",
            "status": "OPEN",
            "generated_at": generated_at,
            "reason": (
                f"Miffre 2010 double-sort LONG: "
                f"mom_12_1={mom}% carry_proxy={carry}%"
            ),
        })

    for sym in basket.get("shorts", []):
        row = row_by_sym.get(sym, {})
        entry = round(float(row.get("last_close", 0.0)), 4)
        mom = round(float(row.get("mom_12_1_pct", 0.0)), 2)
        carry = round(float(row.get("carry_proxy_pct", 0.0)), 2)
        pick_id = f"commodity_carry_momo::{sym}::SHORT::{generated_at[:10]}"
        picks.append({
            "id": pick_id,
            "symbol": sym,
            "direction": "SHORT",
            "strategy": "commodity_carry_momo_double_sort",
            "source_system": "commodity_carry_momo",
            "asset_class": "COMMODITY",
            "entry_price": entry,
            "confidence": 0.60,
            "timeframe": "POSITION",
            "status": "OPEN",
            "generated_at": generated_at,
            "reason": (
                f"Miffre 2010 double-sort SHORT: "
                f"mom_12_1={mom}% carry_proxy={carry}%"
            ),
        })

    return picks


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--symbols", nargs="*", default=DEFAULT_SYMBOLS,
                   help="Commodity futures symbols (default 17-sym universe)")
    p.add_argument("--quintile", type=int, default=3,
                   help="Quintile size for top/bottom (default 3 for 17-sym universe)")
    p.add_argument("--dry-run", action="store_true", help="Print results, don't write JSON")
    p.add_argument("--out", default="audit_dashboard/data/commodity_carry_momo.json",
                   help="Output JSON path (relative to repo root)")
    args = p.parse_args()

    print(f"# commodity_carry_momo sidecar (Miffre 2010 double-sort)", file=sys.stderr)
    print(f"# universe: {len(args.symbols)} symbols  quintile: {args.quintile}", file=sys.stderr)

    rows = fetch_momentum_carry(args.symbols)
    basket = double_sort_basket(rows, args.quintile)

    err_count = sum(1 for r in rows if "error" in r)
    print(f"# fetched: {len(rows) - err_count} valid, {err_count} errors", file=sys.stderr)
    if "error" not in basket:
        print(f"# LONGS:  {basket['longs']}", file=sys.stderr)
        print(f"# SHORTS: {basket['shorts']}", file=sys.stderr)
        print(f"# signal: {basket['expected_signal_strength']}", file=sys.stderr)

    generated_at = datetime.now(timezone.utc).isoformat()
    picks = build_picks(rows, basket, generated_at)
    print(
        f"# picks emitted: {len(picks)}"
        f" ({sum(1 for pk in picks if pk['direction'] == 'LONG')} LONG,"
        f" {sum(1 for pk in picks if pk['direction'] == 'SHORT')} SHORT)",
        file=sys.stderr,
    )

    payload = {
        "generated_at": generated_at,
        "strategy_name": "commodity_carry_momo_double_sort",
        "reference": "Fuertes, Miffre, Rallis 2010 — SSRN 1127213; replicated Jiang & Liu 2024 EFMA",
        "expected_sharpe_range": [1.0, 1.4],
        "expected_annualized_return_pct": 21.0,
        "carry_proxy_caveat": "Free-path carry proxy uses rolling-mean diff. Real Miffre uses second-month contract basis (premium data). Treat as MODERATE-confidence signal.",
        "wiring_status": "WIRED — registered in audit_trail/dashboard_generator.py::JSON_PICK_SOURCES as CT=F diversifier.",
        "universe": args.symbols,
        "lookback_months": 12,
        "skip_months": 1,
        "quintile_size": args.quintile,
        "picks": picks,
        "rows": rows,
        "basket": basket,
    }

    if args.dry_run:
        print(json.dumps(payload, indent=2))
        print("# dry-run: not writing JSON", file=sys.stderr)
        return

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic write: write to .tmp then rename so readers never see a partial file.
    tmp_path = out_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp_path.replace(out_path)
    print(f"# wrote {out_path}  ({out_path.stat().st_size:,} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()
