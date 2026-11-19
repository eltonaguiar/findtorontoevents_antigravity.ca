"""BASE-USD pairs must classify as crypto, never equity (2026-11-19).

Before this fix, ``normalize_symbol('ADA-USD')`` produced ``ADAUSD``, which matched
no entry in ``_CRYPTO_SUFFIXES`` (bare ``USD`` is a fiat quote, not a stablecoin).
The symbol then fell through to the ``return "equity"`` fallback, so 209 crypto
MeanReversionBB picks were written to at_pick_outcomes as asset_class='equity':
a crypto pair with a fixed +3%/-2% grid was polluting the EQUITY book.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alpha_engine.asset_class import (  # noqa: E402
    asset_class_from_symbol,
    classify_pick_asset_class_upper,
    normalize_asset_class,
)

# Every symbol observed mislabelled in production on 2026-11-19.
OBSERVED_MISLABELLED = [
    "ADA-USD", "AVAX-USD", "BTC-USD", "DOGE-USD", "DOT-USD",
    "ETH-USD", "LINK-USD", "SOL-USD", "XRP-USD",
]


@pytest.mark.parametrize("symbol", OBSERVED_MISLABELLED)
def test_observed_symbols_classify_as_crypto(symbol):
    assert normalize_asset_class({"symbol": symbol}) == "crypto"


@pytest.mark.parametrize("symbol", OBSERVED_MISLABELLED)
def test_symbol_helper_agrees(symbol):
    assert asset_class_from_symbol(symbol) == "crypto"


def test_uppercase_wrapper_returns_crypto():
    assert classify_pick_asset_class_upper({"symbol": "SOL-USD"}) == "CRYPTO"


def test_corrupt_upstream_label_does_not_win():
    """Incident #48 precedent: an explicit pair beats a corrupted label."""
    for label in ("equity", "EQUITY", "bond", "stocks", "forex"):
        assert normalize_asset_class({"symbol": "ADA-USD", "asset_class": label}) == "crypto"
        assert normalize_asset_class({"symbol": "ADA-USD", "category": label}) == "crypto"


def test_fiat_bases_stay_forex():
    assert normalize_asset_class({"symbol": "EUR-USD"}) == "forex"
    assert normalize_asset_class({"symbol": "GBP-USD"}) == "forex"
    assert asset_class_from_symbol("EUR-USD") == "forex"


def test_yahoo_suffixes_still_win():
    assert normalize_asset_class({"symbol": "USDJPY=X"}) == "forex"
    assert normalize_asset_class({"symbol": "NG=F"}) == "futures"


def test_usdt_pairs_unchanged():
    assert normalize_asset_class({"symbol": "BTCUSDT"}) == "crypto"
    assert normalize_asset_class({"symbol": "ADAUSDT"}) == "crypto"


def test_non_crypto_symbols_unaffected():
    assert normalize_asset_class({"symbol": "TLT"}) == "bond"
    assert normalize_asset_class({"symbol": "SPY"}) == "etf"
    assert normalize_asset_class({"symbol": "AAPL"}) == "equity"
    assert normalize_asset_class({"symbol": "TLT", "category": "bond"}) == "bond"


def test_unseparated_pair_is_not_forced_to_crypto():
    """ADAUSD has no separator, so the rule must not claim it — no regression
    on the fallback path that other symbols depend on."""
    assert normalize_asset_class({"symbol": "ADAUSD"}) in ("crypto", "equity")


def test_equity_default_still_applies_to_unknown_tickers():
    assert normalize_asset_class({"symbol": "ZZZZ"}) == "equity"
