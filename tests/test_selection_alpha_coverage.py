"""Selection-alpha publish path and bar-coverage diagnosis (2026-11-19).

Two defects this locks down:
  1. the ledger's whitelist dropped `by_class`, so per-class alpha was computed,
     used by the G8 gate, and never published;
  2. `unmeasured` gave no reason, hiding stale price tables (equity_daily_ohlcv
     ended 2026-06-18 while 486 of 765 equity picks closed after it).
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alpha_engine.audit3_selection_alpha import bar_coverage  # noqa: E402
from alpha_engine.audit3_tribunal import ALPHA_PASSTHROUGH_KEYS  # noqa: E402


def _ms(y, m, d):
    return int(datetime(y, m, d, tzinfo=timezone.utc).timestamp() * 1000)


def test_by_class_is_published():
    assert "by_class" in ALPHA_PASSTHROUGH_KEYS


def test_bar_coverage_is_published():
    assert "bar_coverage" in ALPHA_PASSTHROUGH_KEYS


def test_existing_keys_still_published():
    for key in ("overall", "by_slice", "covered", "n_universe", "missing"):
        assert key in ALPHA_PASSTHROUGH_KEYS


def test_coverage_counts_found_and_missing_symbols():
    bars = {"EQUITY:AAPL": [(_ms(2026, 6, 17), 100.0)], "EQUITY:MSFT": [(_ms(2026, 6, 18), 200.0)]}
    cov = bar_coverage(bars, {"EQUITY": {"AAPL", "MSFT", "ZZZZ"}})
    assert cov["EQUITY"]["symbols_requested"] == 3
    assert cov["EQUITY"]["symbols_found"] == 2
    assert cov["EQUITY"]["missing_symbols"] == ["ZZZZ"]
    assert cov["EQUITY"]["last_bar"] == "2026-06-18"


def test_coverage_reports_no_bars_for_a_class():
    cov = bar_coverage({}, {"COMMODITY": {"GC=F"}})
    assert cov["COMMODITY"]["symbols_found"] == 0
    assert cov["COMMODITY"]["last_bar"] is None


def test_coverage_empty_want():
    assert bar_coverage({}, {}) == {}
    assert bar_coverage({}, None) == {}


def test_coverage_last_bar_is_the_maximum_not_the_last_key():
    bars = {"ETF:SPY": [(_ms(2026, 10, 30), 1.0), (_ms(2026, 3, 2), 2.0)]}
    cov = bar_coverage(bars, {"ETF": {"SPY"}})
    assert cov["ETF"]["last_bar"] == "2026-10-30"


def test_bond_has_a_price_table_mapping():
    """BOND had no TABLE_FOR entry, so its gate could never be measured."""
    from alpha_engine.audit3_selection_alpha import TABLE_FOR, TOLERANCE_MS
    assert TABLE_FOR.get("BOND") == ("etf_daily_ohlcv", "date")
    assert "BOND" in TOLERANCE_MS


def test_every_backfilled_class_has_a_table():
    from alpha_engine.audit3_selection_alpha import TABLE_FOR
    for klass in ("CRYPTO", "EQUITY", "ETF", "FOREX", "COMMODITY", "BOND"):
        assert klass in TABLE_FOR, klass


# --- instrument-level counting (2026-11-19) -------------------------------
# Coverage used to count spelling variants as separate symbols: CRYPTO read
# 36/173 and FOREX 12/44 even though most "missing" entries were variants of
# instruments already priced. These lock the instrument-level ratio.

def test_crypto_spelling_variants_collapse_to_one_instrument():
    bars = {"CRYPTO:BTCUSDT": [(_ms(2026, 11, 19), 60000.0)]}
    cov = bar_coverage(bars, {"CRYPTO": {"BTC-USD", "BTCUSDT", "BTC"}})
    assert cov["CRYPTO"]["symbols_requested"] == 1
    assert cov["CRYPTO"]["symbols_found"] == 1
    assert cov["CRYPTO"]["variants_considered"] == 3
    assert cov["CRYPTO"]["missing_symbols"] == []


def test_missing_instrument_is_reported_once_by_short_name():
    cov = bar_coverage({}, {"CRYPTO": {"ADA-USD", "ADAUSDT", "ADAUSD", "ADA"}})
    assert cov["CRYPTO"]["symbols_requested"] == 1
    assert cov["CRYPTO"]["symbols_found"] == 0
    assert cov["CRYPTO"]["missing_symbols"] == ["ADA"]


def test_forex_vendor_spellings_collapse():
    bars = {"FOREX:AUDJPY": [(_ms(2026, 11, 18), 97.0)]}
    cov = bar_coverage(bars, {"FOREX": {"AUDJPY=X", "AUD/JPY", "AUDJPY"}})
    assert cov["FOREX"]["symbols_requested"] == 1
    assert cov["FOREX"]["symbols_found"] == 1


def test_distinct_instruments_are_still_counted_separately():
    bars = {"EQUITY:AAPL": [(_ms(2026, 11, 19), 1.0)]}
    cov = bar_coverage(bars, {"EQUITY": {"AAPL", "MSFT", "BRK.B", "BRK-B"}})
    assert cov["EQUITY"]["symbols_requested"] == 3   # AAPL, MSFT, BRK.B/BRK-B
    assert cov["EQUITY"]["symbols_found"] == 1
    assert cov["EQUITY"]["missing_symbols"] == ["BRK-B", "MSFT"]


# --- FUTURES is a real payload class, not a synonym for COMMODITY -----------
# futures_tsmom_winner emits on ES=F/NQ=F/GC=F/HG=F with asset_class=FUTURES and
# _class() returns "FUTURES". Without a TABLE_FOR entry those picks were
# unmeasurable by construction — the same defect BOND had.

def test_futures_has_a_price_table_mapping():
    from alpha_engine.audit3_selection_alpha import TABLE_FOR, TOLERANCE_MS
    assert TABLE_FOR.get("FUTURES") == ("futures_daily_ohlcv", "date")
    assert "FUTURES" in TOLERANCE_MS


def test_every_payload_class_is_mappable():
    from alpha_engine.audit3_selection_alpha import TABLE_FOR
    for klass in ("BOND", "COMMODITY", "CRYPTO", "EQUITY", "ETF", "FOREX", "FUTURES"):
        assert klass in TABLE_FOR, klass
