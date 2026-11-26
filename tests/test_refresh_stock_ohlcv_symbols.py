"""Symbol-universe hygiene for tools/refresh_stock_ohlcv.py.

Regression context: picks-now-refresh run 45746318864 concluded SUCCESS with 1,427
ERROR lines. 840 of them were yfinance's own "No data found, symbol may be
delisted" — one per dead ticker — and the universe still carried `$ADA`, `$SQ`
and other dollar-prefixed or delisted symbols. These tests pin the sanitising.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.refresh_stock_ohlcv import KNOWN_DELISTED, normalize_yf_symbol


def test_strips_dollar_prefix():
    # a live ticker keeps its cleaned form
    assert normalize_yf_symbol("$AAPL") == "AAPL"
    assert normalize_yf_symbol("$SPY") == "SPY"
    # a dead ticker is stripped AND then dropped, so `$SQ` never reaches Yahoo
    assert normalize_yf_symbol("$SQ") is None


def test_strips_whitespace_and_uppercases():
    assert normalize_yf_symbol("  spy  ") == "SPY"
    assert normalize_yf_symbol("btc-usd") == "BTC-USD"


def test_preserves_yfinance_suffixes():
    for sym in ("EURUSD=X", "GC=F", "BTC-USD", "BRK-B"):
        assert normalize_yf_symbol(sym) == sym


def test_known_delisted_are_dropped():
    for sym in KNOWN_DELISTED:
        assert normalize_yf_symbol(sym) is None
        assert normalize_yf_symbol(f"${sym}") is None


def test_empty_and_blank_return_none():
    for bad in ("", "   ", None, "$"):
        assert normalize_yf_symbol(bad) is None


def test_live_tickers_survive():
    for sym in ("AAPL", "SPY", "QQQ", "XYZ"):
        assert normalize_yf_symbol(sym) == sym


def test_delisted_mapping_is_documented():
    # every entry explains itself, so the next person can audit the list
    for sym, why in KNOWN_DELISTED.items():
        assert why and len(why) > 3, f"{sym} has no rationale"
