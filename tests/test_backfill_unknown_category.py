"""Unit tests for the ISO currency-pair rule in tools/backfill_unknown_category.py.

2026-11-28: the sync labels `USD-JPY` / `USD-CHF` FOREX at ingest, but the
backfill tool reported them as unclassifiable because
`alpha_engine.config.detect_asset_class` returns 'unknown' for a bare X-Y shape.
The two rules must not drift apart: if the sync accepts a pair the backfill
cannot classify, every run reports the same rows as unrepairable.

No database is touched here.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.backfill_unknown_category import (  # noqa: E402
    _FX_ISO,
    iso_fx_pair,
    resolve,
)

TRADING_PICKS_ALLOWED = {
    "CRYPTO", "EQUITY", "FOREX", "ETF", "BOND", "COMMODITY", "FUTURES",
    "INDEX", "PREDICTION_MARKET", "MEMECOIN", "PENNY_STOCK",
}


@pytest.mark.parametrize("symbol", ["USD-JPY", "USD-CHF", "usd-jpy",
                                    "EUR-USD", "GBP-JPY"])
def test_iso_pairs_are_forex(symbol: str) -> None:
    assert iso_fx_pair(symbol)
    assert resolve({"symbol": symbol}, TRADING_PICKS_ALLOWED) == ("FOREX", "iso_pair")


@pytest.mark.parametrize("symbol", [
    "BTC-USD",      # BTC is not an ISO code — the -USD crypto rule owns it
    "ETH-USD",
    "XAU-USD",
    "AAPL",         # no separator
    "USDJPY",       # no separator (detect_asset_class calls this forex)
    "USD-",         # half missing
    "-JPY",
    "USD-JPY-X",    # two separators
    "",
    "NOTREAL",
])
def test_non_iso_shapes_are_not_iso_pairs(symbol: str) -> None:
    assert not iso_fx_pair(symbol)


def test_iso_pair_never_has_a_12th_label() -> None:
    """An ISO pair resolves to FOREX, never to something outside the enum."""
    target, why = resolve({"symbol": "USD-JPY"}, TRADING_PICKS_ALLOWED)
    assert target in TRADING_PICKS_ALLOWED and target == "FOREX"
    assert why == "iso_pair"


def test_source_rule_outranks_the_symbol() -> None:
    """An unambiguous emitter still wins over the symbol shape."""
    target, why = resolve(
        {"symbol": "USD-JPY", "source_system": "etf_all_strategies"},
        TRADING_PICKS_ALLOWED,
    )
    assert (target, why) == ("ETF", "source:etf_all_strategies")


def test_fx_set_matches_the_sync() -> None:
    """The copy in the tool must equal the sync's set, or the two drift apart."""
    src = (REPO_ROOT / "alpha_engine" / "mysql_trading_sync.py").read_text(
        encoding="utf-8")
    block = re.search(r"_FX_ISO = frozenset\(\{(.*?)\}\)", src, re.S)
    assert block, "_FX_ISO not found in alpha_engine/mysql_trading_sync.py"
    sync_codes = set(re.findall(r'"([A-Z]{2,4})"', block.group(1)))
    assert sync_codes == set(_FX_ISO)
    assert len(_FX_ISO) == 27
