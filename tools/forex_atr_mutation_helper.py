#!/usr/bin/env python3
"""
A4 helper — FOREX-only slice of closed_picks.json for ATR-normalized momentum
mutation analysis (Axis 4, docs/MUTATION_THREE_AXIS_PROTOCOL.md Step 1b).

Research / report-only. Does NOT touch production scanners or emission gates.

Reports, per FOREX subset:
  - total FOREX closed trades, overall WR / PF
  - per-symbol WR / n / avg pnl
  - per-strategy WR / n / avg pnl, with direction split
  - which entry fields exist that could carry a volatility signal (honest
    audit of what an ATR-normalized re-test could and could not use)
  - Step-5 mutation-quality guard: candidate winning subset must be
    >= 10% of total FOREX closed trades AND n >= 100 (charter floor).

Usage (repo root):
  python tools/forex_atr_mutation_helper.py
  python tools/forex_atr_mutation_helper.py --json alpha_engine/data/closed_picks.json
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

# FX pairs are quoted with the Yahoo "=X" suffix in this book; also accept
# bare 6-letter pair tickers as a fallback.
_FX_QUOTES = {
    "USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD",
}


def _is_forex(pick: dict) -> bool:
    ac = str(pick.get("asset_class") or "").strip().upper()
    if ac == "FOREX":
        return True
    if ac in ("CRYPTO", "EQUITY", "COMMODITY", "ETF", "BOND", "SPORTS"):
        return False
    sym = str(pick.get("symbol") or pick.get("ticker") or "").strip().upper()
    base = sym.replace("=X", "")
    if len(base) == 6 and base[:3] in _FX_QUOTES and base[3:] in _FX_QUOTES:
        return True
    return False


def _pnl(pick: dict) -> float:
    v = pick.get("pnl_pct")
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _profit_factor(pnls: list[float]) -> float:
    gains = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return gains / losses


def _wr(pnls: list[float]) -> float:
    if not pnls:
        return 0.0
    return sum(1 for p in pnls if p > 0) / len(pnls) * 100.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path,
                    default=Path("alpha_engine/data/closed_picks.json"))
    args = ap.parse_args()

    data = json.loads(args.json.read_text(encoding="utf-8"))
    picks = data if isinstance(data, list) else (
        data.get("picks") or data.get("closed_picks") or data.get("items") or []
    )
    fx = [p for p in picks if _is_forex(p)]
    total_book = len(picks)
    n_fx = len(fx)

    print("=" * 70)
    print("FOREX SLICE — closed_picks.json")
    print("=" * 70)
    print(f"  total book closed trades : {total_book}")
    print(f"  FOREX closed trades      : {n_fx}")
    if n_fx == 0:
        print("  No FOREX picks found — INSUFFICIENT-DATA.")
        return 0

    fx_pnls = [_pnl(p) for p in fx]
    print(f"  FOREX overall WR         : {_wr(fx_pnls):.1f}%")
    print(f"  FOREX overall PF         : {_profit_factor(fx_pnls):.2f}")
    print(f"  Step-5 10% floor (>=)    : {0.10 * n_fx:.0f} trades")
    print(f"  charter n-floor          : 100 trades")

    # --- per-symbol ---
    by_sym: dict[str, list[float]] = defaultdict(list)
    for p in fx:
        by_sym[str(p.get("symbol") or "?")].append(_pnl(p))
    print("\n" + "-" * 70)
    print("PER-SYMBOL  (sorted by WR)")
    print("-" * 70)
    print(f"  {'symbol':14s} {'n':>5s} {'WR%':>7s} {'PF':>7s} {'avgPnL%':>10s}")
    for sym, pnls in sorted(by_sym.items(), key=lambda kv: -_wr(kv[1])):
        avg = sum(pnls) / len(pnls)
        pf = _profit_factor(pnls)
        print(f"  {sym:14s} {len(pnls):5d} {_wr(pnls):7.1f} "
              f"{pf:7.2f} {avg:+10.4f}")

    # --- per-strategy with direction split ---
    by_strat: dict[str, list[float]] = defaultdict(list)
    by_strat_dir: dict[tuple[str, str], list[float]] = defaultdict(list)
    for p in fx:
        s = str(p.get("strategy") or "?")
        d = str(p.get("signal_type") or p.get("direction") or "?").upper()
        if d in ("BUY",):
            d = "LONG"
        if d in ("SELL",):
            d = "SHORT"
        by_strat[s].append(_pnl(p))
        by_strat_dir[(s, d)].append(_pnl(p))
    print("\n" + "-" * 70)
    print("PER-STRATEGY  (sorted by WR)")
    print("-" * 70)
    print(f"  {'strategy':38s} {'n':>5s} {'WR%':>7s} {'PF':>7s}")
    for s, pnls in sorted(by_strat.items(), key=lambda kv: -_wr(kv[1])):
        print(f"  {s[:38]:38s} {len(pnls):5d} {_wr(pnls):7.1f} "
              f"{_profit_factor(pnls):7.2f}")

    print("\n" + "-" * 70)
    print("PER-STRATEGY x DIRECTION")
    print("-" * 70)
    for (s, d), pnls in sorted(by_strat_dir.items(),
                               key=lambda kv: (kv[0][0], -_wr(kv[1]))):
        print(f"  {s[:30]:30s} {d:6s} {len(pnls):5d} "
              f"WR {_wr(pnls):5.1f}%  PF {_profit_factor(pnls):5.2f}")

    # --- candidate winning subsets passing BOTH Step-5 guards ---
    print("\n" + "=" * 70)
    print("CANDIDATE WINNING SUBSETS  (Step-5 guard: WR>=50%, n>=100,")
    print("                            n>=10% of FOREX book)")
    print("=" * 70)
    floor10 = 0.10 * n_fx
    found = False
    # symbol-level
    for sym, pnls in by_sym.items():
        if _wr(pnls) >= 50.0 and len(pnls) >= 100 and len(pnls) >= floor10:
            found = True
            print(f"  SYMBOL  {sym}: n={len(pnls)} WR={_wr(pnls):.1f}% "
                  f"PF={_profit_factor(pnls):.2f}  -> PASSES")
    # strategy-level
    for s, pnls in by_strat.items():
        if _wr(pnls) >= 50.0 and len(pnls) >= 100 and len(pnls) >= floor10:
            found = True
            print(f"  STRATEGY {s}: n={len(pnls)} WR={_wr(pnls):.1f}% "
                  f"PF={_profit_factor(pnls):.2f}  -> PASSES")
    # strategy x direction
    for (s, d), pnls in by_strat_dir.items():
        if _wr(pnls) >= 50.0 and len(pnls) >= 100 and len(pnls) >= floor10:
            found = True
            print(f"  STRAT+DIR {s}/{d}: n={len(pnls)} WR={_wr(pnls):.1f}% "
                  f"PF={_profit_factor(pnls):.2f}  -> PASSES")
    if not found:
        print("  NONE — no winning subset clears WR>=50% AND n>=100 AND "
              f"n>=10% ({floor10:.0f}).")

    # --- volatility-signal field audit ---
    print("\n" + "=" * 70)
    print("ATR / VOLATILITY FIELD AUDIT  (can an ATR-normalized re-test run?)")
    print("=" * 70)
    vol_fields = ["atr", "atr_14", "realized_vol", "volatility", "natr",
                  "atr_pct", "vol_regime"]
    keys = set()
    for p in fx[:2000]:
        keys.update(p.keys())
    present = [k for k in vol_fields if k in keys]
    print(f"  explicit volatility fields present: "
          f"{present or 'NONE'}")
    has_prices = all(k in keys for k in ("entry_price", "stop_loss"))
    print(f"  entry_price + stop_loss present   : {has_prices}")
    print("  -> ATR(14) is NOT stored per pick. A true ATR-normalized "
          "re-test\n     would need a bar-data backfill (yfinance) keyed on "
          "entry_date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
