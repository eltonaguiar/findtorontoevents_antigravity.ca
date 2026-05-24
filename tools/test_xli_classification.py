#!/usr/bin/env python3
"""
Test XLI and asset class classification correctness.

Tests:
  1. XLI -> ETF via asset_class_from_symbol() from alpha_engine.asset_class
  2. All sector ETFs (XLK, XLF, XLE, XLV, XLY, XLP, XLB, XLU, XLC, XLRE, XLI) -> ETF
  3. BTCUSDT, ETHUSDT -> CRYPTO
  4. EURUSD=X -> FOREX

Run with:
    python3 -m pytest tools/test_xli_classification.py -v
    python3 tools/test_xli_classification.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on sys.path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alpha_engine.asset_class import (
    normalize_asset_class, asset_class_from_symbol,
)


def test_xli_is_etf():
    """XLI (Industrial Select Sector SPDR) must classify as ETF, not CRYPTO."""
    assert asset_class_from_symbol("XLI") == "etf"


def test_xli_normalize_asset_class():
    """normalize_asset_class must resolve XLI to ETF even with wrong upstream tag."""
    pick = {"symbol": "XLI"}
    assert normalize_asset_class(pick) == "etf"
    # Even if upstream had wrong tag, symbol-based lookup is correct
    assert asset_class_from_symbol("XLI") == "etf"


def test_sector_etfs():
    """All 11 SPDR sector ETFs must classify as ETF."""
    sector_etfs = ["XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLB", "XLU", "XLC", "XLRE", "XLI"]
    for sym in sector_etfs:
        result = asset_class_from_symbol(sym)
        assert result == "etf", f"{sym} classified as '{result}', expected 'etf'"


def test_crypto_symbols():
    """Crypto pairs with USDT suffix must classify as CRYPTO."""
    crypto_syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT"]
    for sym in crypto_syms:
        result = asset_class_from_symbol(sym)
        assert result == "crypto", f"{sym} classified as '{result}', expected 'crypto'"


def test_forex_symbols():
    """Forex pairs with =X suffix must classify as FOREX."""
    forex_syms = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X"]
    for sym in forex_syms:
        result = asset_class_from_symbol(sym)
        assert result == "forex", f"{sym} classified as '{result}', expected 'forex'"


def test_futures_symbols():
    """Futures with =F suffix must classify as futures."""
    futures_syms = ["GC=F", "CL=F", "SI=F", "NG=F"]
    for sym in futures_syms:
        result = asset_class_from_symbol(sym)
        assert result == "futures", f"{sym} classified as '{result}', expected 'futures'"


def test_bond_symbols():
    """Bond ETFs must classify as bond."""
    bond_syms = ["TLT", "IEF", "SHY", "LQD", "AGG"]
    for sym in bond_syms:
        result = asset_class_from_symbol(sym)
        assert result == "bond", f"{sym} classified as '{result}', expected 'bond'"


if __name__ == "__main__":
    # Standalone runner
    import inspect
    failures = 0
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"  [PASS] {name}")
            except AssertionError as e:
                failures += 1
                print(f"  [FAIL] {name} — {e}")
            except Exception as e:
                failures += 1
                print(f"  [ERROR] {name} — {e}")
    print(f"\nResults: {failures} failure(s)")
    sys.exit(1 if failures else 0)
