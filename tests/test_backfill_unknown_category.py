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


def test_peer_label_resolves_a_shape_the_classifier_cannot_read() -> None:
    """JTO-USD2: the stray digit defeats the pair rule, the table knows better."""
    peers = {"JTO-USD2": "CRYPTO"}
    target, why = resolve({"symbol": "JTO-USD2"}, TRADING_PICKS_ALLOWED,
                          peers, set())
    assert (target, why) == ("CRYPTO", "peer_label")


def test_equity_universe_is_only_a_last_resort() -> None:
    """BRK-B has price history in equity_daily_ohlcv; nothing else can read it."""
    target, why = resolve({"symbol": "BRK-B"}, TRADING_PICKS_ALLOWED,
                          {}, {"BRK-B", "AAPL"})
    assert (target, why) == ("EQUITY", "equity_universe")


def test_classifier_outranks_peer_and_universe() -> None:
    """Proof rules never second-guess a symbol the classifier reads cleanly."""
    target, why = resolve({"symbol": "SPY"}, TRADING_PICKS_ALLOWED,
                          {"SPY": "EQUITY"}, {"SPY"})
    assert (target, why) == ("ETF", "detect:etf")


def test_no_evidence_means_no_label() -> None:
    """An unknown symbol with no peers and no price history stays untouched."""
    assert resolve({"symbol": "NOTREAL2"}, TRADING_PICKS_ALLOWED,
                   {}, set()) == (None, "detect:unknown")


def test_alias_rule_repairs_a_lowercase_fork() -> None:
    """A `meme` row is the same class as MEMECOIN, so it resolves by alias."""
    target, why = resolve({"symbol": "PEPE-USD", "reason": "alias",
                           "current_label": "meme"}, TRADING_PICKS_ALLOWED)
    assert (target, why) == ("MEMECOIN", "alias:meme")


def test_alias_map_matches_the_sync() -> None:
    """The sync re-creates these forks each run; both sides must agree.

    origin/main still carries `_CATEGORY_KNOWN_PASSTHROUGH = {"meme", "index",
    "unknown"}`, which is why the repaired row came back at 07:59Z. The branch
    normalizes them instead — this test pins that mapping in both places.
    """
    src = (REPO_ROOT / "alpha_engine" / "mysql_trading_sync.py").read_text(
        encoding="utf-8")
    for key, value in (("meme", "MEMECOIN"), ("index", "INDEX"),
                       ("managed_futures", "FUTURES"),
                       ("prediction_market", "PREDICTION_MARKET")):
        assert f'"{key}": "{value}"' in src, f"sync lost the {key} alias"


def test_upsert_protects_an_existing_category() -> None:
    """The sync must not blank a repaired label when the source sends ''. 65
    rows relabelled at 04:06Z were restored to '' by the 04:59Z sync."""
    src = (REPO_ROOT / "alpha_engine" / "mysql_trading_sync.py").read_text(
        encoding="utf-8")
    assert ("category     = COALESCE(NULLIF(VALUES(category), ''), category)")
    assert "COALESCE(NULLIF(VALUES(category), ''), category)" in src
    assert "category     = VALUES(category)," not in src


def test_fx_set_matches_the_sync() -> None:
    """The copy in the tool must equal the sync's set, or the two drift apart."""
    src = (REPO_ROOT / "alpha_engine" / "mysql_trading_sync.py").read_text(
        encoding="utf-8")
    block = re.search(r"_FX_ISO = frozenset\(\{(.*?)\}\)", src, re.S)
    assert block, "_FX_ISO not found in alpha_engine/mysql_trading_sync.py"
    sync_codes = set(re.findall(r'"([A-Z]{2,4})"', block.group(1)))
    assert sync_codes == set(_FX_ISO)
    assert len(_FX_ISO) == 27
