"""
Tests for ISSUE 3 — delisted-symbol filter for equity scanner watchlists.

Verifies STOCKS/scanners/delisted_symbols.filter_delisted removes known
delisted/renamed tickers (NKLA, SQ, SURF, FFIE, ...) that break yfinance
batch downloads.
"""

import sys
from pathlib import Path

SCANNERS = Path(__file__).resolve().parent.parent / "STOCKS" / "scanners"
if str(SCANNERS) not in sys.path:
    sys.path.insert(0, str(SCANNERS))

from delisted_symbols import filter_delisted, is_delisted, DELISTED_SYMBOLS


def test_named_delisted_tickers_flagged():
    for sym in ("NKLA", "SQ", "SURF", "FFIE"):
        assert is_delisted(sym), f"{sym} should be flagged delisted"
        assert sym in DELISTED_SYMBOLS


def test_case_insensitive():
    assert is_delisted("nkla")
    assert is_delisted("  Surf ")


def test_live_tickers_not_flagged():
    for sym in ("AAPL", "MSFT", "NVDA", "SPY", "GME", "AMC"):
        assert not is_delisted(sym), f"{sym} is live, must not be filtered"


def test_filter_removes_delisted_preserves_order():
    seed = ["AAPL", "NKLA", "MSFT", "SQ", "GME", "FFIE", "SURF"]
    out = filter_delisted(seed)
    assert out == ["AAPL", "MSFT", "GME"]


def test_filter_empty_and_noop():
    assert filter_delisted([]) == []
    assert filter_delisted(["AAPL", "MSFT"]) == ["AAPL", "MSFT"]


if __name__ == "__main__":
    test_named_delisted_tickers_flagged()
    test_case_insensitive()
    test_live_tickers_not_flagged()
    test_filter_removes_delisted_preserves_order()
    test_filter_empty_and_noop()
    print("OK — all delisted-symbol tests passed")
