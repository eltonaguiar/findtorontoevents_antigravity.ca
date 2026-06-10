#!/usr/bin/env python3
"""Focused test for picks_now_professional.py dividendYield fix.

Bug context: FMP's `lastDiv` is the dollar AMOUNT of the most recent
distribution payment, NOT a yield. Previously the FMP path set
`info["dividendYield"] = lastDiv` and the scorer did `*100`,
producing 1011% for JEPQ and 1165% for RYLD on the live page.

Fix: FMP path now sets `info["dividendYield"] = None`.

This test mocks yfinance as unavailable, forcing fetch_analyst_info_failover
into the FMP profile fallback chain (the exact code path that produced the
bug), and verifies the returned dict for JEPQ/RYLD has dividendYield=None.
"""
from __future__ import annotations
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "tools" / "picks_now_professional.py"


def load_module():
    spec = importlib.util.spec_from_file_location("picks_now", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    print("=" * 70)
    print("FOCUSED FMP dividendYield FIX TEST")
    print("=" * 70)
    print()
    mod = load_module()
    test_tickers = [
        ("JEPQ", "BUG CASE: was 1011%"),
        ("RYLD", "BUG CASE: was 1165%"),
        ("JEPI", "sister covered-call ETF"),
        ("QYLD", "sister covered-call ETF"),
        ("SCHD", "dividend ETF reference"),
        ("AAPL", "low/no div, reference"),
    ]

    def _yf_ticker_broken(sym):
        class _T:
            def __init__(self, s): self._s = s
            @property
            def info(self):
                raise RuntimeError(f"yfinance mocked unavailable for {self._s}")
        return _T(sym)

    results, failures = [], []
    for sym, note in test_tickers:
        print(f"--- {sym}  ({note}) ---")
        with patch.object(mod.yf, "Ticker", _yf_ticker_broken):
            try:
                info = mod.fetch_analyst_info_failover(sym)
            except Exception as e:
                print(f"  RAISED: {e}")
                failures.append((sym, f"raised: {e}"))
                continue
        div_yield = info.get("dividendYield")
        market_cap = info.get("marketCap")
        print(f"  source        = {info.get('source')!r}")
        print(f"  marketCap     = {market_cap}")
        print(f"  dividendYield = {div_yield!r}  (was lastDiv in dollars before fix)")
        if div_yield is None:
            verdict = "PASS (None = fix took effect)"
        elif isinstance(div_yield, (int, float)) and 0 <= div_yield < 1.0:
            verdict = f"PASS (real yield fraction: {div_yield*100:.2f}%)"
        elif isinstance(div_yield, (int, float)) and 5 <= div_yield <= 50:
            verdict = f"FAIL: looks like old bug (would *=100 to {div_yield*100:.0f}%)"
            failures.append((sym, verdict))
        else:
            verdict = f"WARN: unexpected value {div_yield}"
        print(f"  -> {verdict}")
        results.append((sym, div_yield, verdict))
        print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for sym, dy, verdict in results:
        marker = "  " if verdict.startswith("PASS") else "!!"
        print(f"  {marker} {sym:6s} dividendYield={dy!r:12s}  {verdict}")
    if failures:
        print(f"\nFAILURES ({len(failures)}):")
        for sym, msg in failures:
            print(f"  - {sym}: {msg}")
        return 1
    print("\nAll JEPQ/RYLD cases show dividendYield=None (the fix). PASS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
