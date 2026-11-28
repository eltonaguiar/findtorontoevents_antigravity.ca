"""Regression: category inference for NULL/empty rows in mysql_trading_sync.

# 2026-06-11 INCIDENT_OVERALL#88: category canonical form is now UPPERCASE at the
# ingest chokepoint (consumer-derived; see mysql_trading_sync._CATEGORY_CANONICAL_MAP).
# Expectations updated lowercase->UPPERCASE; 'meme' stays passthrough (env-mapped downstream).

Reference: swarm_runs/next_steps_perf_2026-05-09/ (4/4 engine consensus).
Q11/Q2/Q4 from PR #862 also flagged that 7 of top 10 30d winners (BTCUSDT,
JUPUSDT, ENAUSDT, RENDERUSDT, ADAUSDT, NEARUSDT, STXUSDT) are tagged
NULL/empty category, making them invisible to category-based router and
audit-page filters even though they're plainly crypto.

Inference rules (writer-side, only when pick.get('category') is empty):
  *USDT / *USDC / *BUSD / *DAI / *PERP  → crypto
  *-USD                                  → crypto
  *=F                                    → futures
  *=X                                    → forex
  USD-JPY                                → forex (both halves real ISO codes)
  else: detect_asset_class(symbol), accepted only when it returns one of the
        11 canonical members (crypto/equity/etf/forex/bond/commodity/futures/
        index/prediction_market/memecoin/penny_stock). 'mutual_fund' and
        'unknown' are refused → category stays empty (unclassifiable), so no
        12th label is ever invented at ingest.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alpha_engine.mysql_trading_sync import pick_to_row


def _base(symbol, **kw):
    p = {
        "id": "test_" + symbol.replace(":", "_"),
        "symbol": symbol,
        "direction": "LONG",
        "status": "ACTIVE",
    }
    p.update(kw)
    return p


def test_btcusdt_empty_category_becomes_crypto():
    r = pick_to_row(_base("BTCUSDT"))
    assert r["category"] == "CRYPTO"


def test_jupusdt_empty_category_becomes_crypto():
    r = pick_to_row(_base("JUPUSDT"))
    assert r["category"] == "CRYPTO"


def test_dash_usd_format_becomes_crypto():
    """ADA-USD / SOL-USD / NEAR-USD yahoo-style still crypto."""
    for sym in ("ADA-USD", "SOL-USD", "NEAR-USD", "BTC-USD"):
        r = pick_to_row(_base(sym))
        assert r["category"] == "CRYPTO", f"{sym} got {r['category']}"


def test_futures_equals_F_becomes_futures():
    for sym in ("CL=F", "SI=F", "ZC=F", "ZS=F", "HG=F"):
        r = pick_to_row(_base(sym))
        assert r["category"] == "FUTURES", f"{sym} got {r['category']}"


def test_forex_equals_X_becomes_forex():
    for sym in ("EURUSD=X", "GBPUSD=X", "USDJPY=X", "CADJPY=X"):
        r = pick_to_row(_base(sym))
        assert r["category"] == "FOREX", f"{sym} got {r['category']}"


def test_explicit_category_NEVER_overridden():
    """If pick has explicit category, inference must NOT touch it.

    2026-11-28: the expected value is now the canonical form 'MEMECOIN' —
    the explicit label is still not overridden by inference (it is not
    'CRYPTO'), it is only case/synonym normalized to the one canonical enum.
    """
    r = pick_to_row(_base("BTCUSDT", category="meme"))
    assert r["category"] == "MEMECOIN"  # not "crypto"
    r2 = pick_to_row(_base("CL=F", category="commodity"))
    assert r2["category"] == "COMMODITY"  # not "futures"


def test_equity_tickers_get_EQUITY_never_crypto_or_futures():
    """Plain equity tickers used to reach the table with an EMPTY label.

    2026-11-28: the classifier fallback now labels them EQUITY (593 such picks
    per sync, e.g. iso_regime_terminal SPY/AMD/GOOGL). The original intent of
    this test still holds — they must never be inferred as crypto or futures.
    """
    for sym in ("AAPL", "NVDA", "TSLA", "JNJ"):
        r = pick_to_row(_base(sym))
        assert r["category"] == "EQUITY", f"{sym} got {r['category']}"


def test_unclassifiable_stays_empty():
    """A symbol the classifier cannot place keeps an empty category.

    detect_asset_class('NOTREAL') is 'unknown', which is not a canonical member,
    so nothing is invented. Rows like this are left for
    tools/backfill_unknown_category.py rather than getting a 12th label.
    """
    r = pick_to_row(_base("NOTREAL"))
    assert r["category"] == "", f"NOTREAL should be empty, got {r['category']}"


def test_lowercase_input_normalized():
    """Inference is case-insensitive on the lookup."""
    r = pick_to_row(_base("btcusdt"))
    assert r["category"] == "CRYPTO"


def test_perp_suffix_treated_as_crypto():
    """BINANCE:BTCUSDT.P style (perpetuals)."""
    r = pick_to_row(_base("BTCUSDPERP"))
    assert r["category"] == "CRYPTO"


def test_explicit_empty_string_treated_as_null():
    """category='' should still trigger inference (not pass through empty)."""
    r = pick_to_row(_base("BTCUSDT", category=""))
    assert r["category"] == "CRYPTO"


def test_explicit_whitespace_treated_as_null():
    """category='   ' (whitespace) should still trigger inference."""
    r = pick_to_row(_base("BTCUSDT", category="   "))
    assert r["category"] == "CRYPTO"
