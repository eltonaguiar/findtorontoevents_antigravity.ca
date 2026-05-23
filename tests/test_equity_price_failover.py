"""Tests for `alpha_engine.equity_price_failover`.

Contract verified:
  - Failover walks the chain in tier order.
  - Returning None from one adapter advances to the next.
  - All-sources-failed returns None gracefully.
  - 1-hour disk cache is respected (TTL + invalidation).
  - Public-API shapes match what `value_screener_runner` expects.
  - Network is stubbed throughout — these tests are sandbox-safe.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

import alpha_engine.equity_price_failover as epf


# ---------------------------------------------------------------------------
# Fixtures: redirect cache to tmp + reset module-level chain hooks
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _isolate_module(tmp_path, monkeypatch):
    """Each test gets a clean cache dir + restored chain + scrubbed env."""
    monkeypatch.setattr(epf, "CACHE_DIR", tmp_path / "cache")
    # Default: no API keys present in test sandbox unless explicitly set.
    for var in (
        "FINNHUB_API_KEY", "FINNHUB",
        "TIINGO_API_KEY", "TWELVE_DATA_API_KEY",
        "ALPHA_VANTAGE_API_KEY", "FMP_API_KEY",
        "POLYGON_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)
    yield


# ---------------------------------------------------------------------------
# Chain orchestration
# ---------------------------------------------------------------------------
def test_chain_walks_in_order_first_success_wins(monkeypatch):
    calls: list[str] = []

    def good(t: str):
        calls.append("good")
        return {"price": 100.0, "volume": 10, "asof": "2026-04-28", "source": "good"}

    def never(t: str):
        calls.append("never")
        return {"price": 999.0, "volume": 0, "asof": "x", "source": "never"}

    monkeypatch.setattr(epf, "_QUOTE_CHAIN", [good, never])
    q = epf.fetch_quote("AAPL", use_cache=False)
    assert q is not None
    assert q["source"] == "good"
    assert q["price"] == 100.0
    # Chain must short-circuit on first success
    assert calls == ["good"]


def test_chain_falls_through_when_first_returns_none(monkeypatch):
    calls: list[str] = []

    def fail(t: str):
        calls.append("fail")
        return None

    def good(t: str):
        calls.append("good")
        return {"price": 50.0, "volume": 1, "asof": "2026-04-28", "source": "good"}

    monkeypatch.setattr(epf, "_QUOTE_CHAIN", [fail, good])
    q = epf.fetch_quote("MSFT", use_cache=False)
    assert q["source"] == "good"
    assert calls == ["fail", "good"]


def test_chain_falls_through_when_adapter_raises(monkeypatch):
    calls: list[str] = []

    def crash(t: str):
        calls.append("crash")
        raise RuntimeError("adapter blew up")

    def good(t: str):
        calls.append("good")
        return {"price": 7.0, "volume": 1, "asof": "2026-04-28", "source": "good"}

    monkeypatch.setattr(epf, "_QUOTE_CHAIN", [crash, good])
    q = epf.fetch_quote("GOOG", use_cache=False)
    assert q["source"] == "good"
    assert calls == ["crash", "good"]


def test_all_chain_failures_return_none(monkeypatch):
    monkeypatch.setattr(
        epf, "_QUOTE_CHAIN",
        [lambda t: None, lambda t: None, lambda t: None],
    )
    assert epf.fetch_quote("XXX", use_cache=False) is None


def test_market_cap_chain_walks_in_order(monkeypatch):
    monkeypatch.setattr(
        epf, "_MARKETCAP_CHAIN",
        [lambda t: None, lambda t: 1.5e12, lambda t: 9e12],
    )
    assert epf.fetch_market_cap("AAPL", use_cache=False) == 1.5e12


def test_market_cap_skips_zero_or_negative(monkeypatch):
    monkeypatch.setattr(
        epf, "_MARKETCAP_CHAIN",
        [lambda t: 0.0, lambda t: -50, lambda t: 5e9],
    )
    assert epf.fetch_market_cap("BAC", use_cache=False) == 5e9


def test_market_cap_all_failures_returns_none(monkeypatch):
    monkeypatch.setattr(
        epf, "_MARKETCAP_CHAIN",
        [lambda t: None, lambda t: 0.0],
    )
    assert epf.fetch_market_cap("FAIL", use_cache=False) is None


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------
def test_cache_round_trip_within_ttl(monkeypatch):
    calls = {"n": 0}

    def src(t):
        calls["n"] += 1
        return {"price": 42.0, "volume": 5, "asof": "2026-04-28", "source": "src"}

    monkeypatch.setattr(epf, "_QUOTE_CHAIN", [src])
    q1 = epf.fetch_quote("CCC")
    q2 = epf.fetch_quote("CCC")
    assert q1 == q2
    assert q1["price"] == 42.0
    assert calls["n"] == 1, "cache should suppress a 2nd network call"


def test_cache_invalidates_after_ttl(monkeypatch):
    monkeypatch.setattr(epf, "CACHE_TTL_SEC", 0)  # immediate expiry
    calls = {"n": 0}

    def src(t):
        calls["n"] += 1
        return {"price": 1.0 + calls["n"], "volume": 0, "asof": "x", "source": "src"}

    monkeypatch.setattr(epf, "_QUOTE_CHAIN", [src])
    q1 = epf.fetch_quote("DDD")
    # Sleep a microsecond to make sure mtime advances past the TTL window
    time.sleep(0.01)
    q2 = epf.fetch_quote("DDD")
    assert q1["price"] != q2["price"]
    assert calls["n"] == 2


def test_cache_disabled_via_use_cache_false(monkeypatch):
    calls = {"n": 0}

    def src(t):
        calls["n"] += 1
        return {"price": 11.0, "volume": 0, "asof": "x", "source": "src"}

    monkeypatch.setattr(epf, "_QUOTE_CHAIN", [src])
    epf.fetch_quote("EEE", use_cache=False)
    epf.fetch_quote("EEE", use_cache=False)
    assert calls["n"] == 2


def test_market_cap_cached_separately_from_quote(monkeypatch, tmp_path):
    monkeypatch.setattr(epf, "_MARKETCAP_CHAIN", [lambda t: 7.5e11])
    epf.fetch_market_cap("FFF")
    p = epf._cache_path("FFF", "marketcap")
    assert p.exists()
    payload = json.loads(p.read_text(encoding="utf-8"))
    assert payload["market_cap"] == 7.5e11


def test_quote_cache_strips_private_fields(monkeypatch):
    """Adapters may return _market_cap (FMP piggyback) — must not leak to disk."""

    def fmp_like(t):
        return {"price": 200.0, "volume": 1, "asof": "x",
                "source": "fmp", "_market_cap": 3e12}

    monkeypatch.setattr(epf, "_QUOTE_CHAIN", [fmp_like])
    q = epf.fetch_quote("GGG")
    assert "_market_cap" not in q
    assert q["price"] == 200.0
    cached = json.loads(epf._cache_path("GGG", "quote").read_text(encoding="utf-8"))
    assert "_market_cap" not in cached


# ---------------------------------------------------------------------------
# Adapter behaviour — each is mockable via _HTTP_GET_JSON / _HTTP_GET_TEXT
# ---------------------------------------------------------------------------
def test_stooq_adapter_parses_csv(monkeypatch):
    csv_body = (
        "Symbol,Date,Time,Open,High,Low,Close,Volume\n"
        "AAPL.US,2026-04-28,16:00:00,170.10,172.00,169.50,171.55,52500000\n"
    )
    monkeypatch.setattr(epf, "_HTTP_GET_TEXT", lambda url, **kw: csv_body)
    out = epf._adapter_stooq_quote("AAPL")
    assert out["price"] == 171.55
    assert out["volume"] == 52500000
    assert out["source"] == "stooq"
    assert out["asof"] == "2026-04-28"


def test_stooq_adapter_returns_none_on_nd_response(monkeypatch):
    csv_body = (
        "Symbol,Date,Time,Open,High,Low,Close,Volume\n"
        "ZZZZ.US,N/D,N/D,N/D,N/D,N/D,N/D,N/D\n"
    )
    monkeypatch.setattr(epf, "_HTTP_GET_TEXT", lambda url, **kw: csv_body)
    assert epf._adapter_stooq_quote("ZZZZ") is None


def test_stooq_adapter_returns_none_on_http_failure(monkeypatch):
    monkeypatch.setattr(epf, "_HTTP_GET_TEXT", lambda url, **kw: None)
    assert epf._adapter_stooq_quote("AAPL") is None


def test_finnhub_adapter_requires_key(monkeypatch):
    """No FINNHUB_API_KEY -> returns None without making any HTTP call."""
    seen = {"called": False}

    def trap(*a, **kw):
        seen["called"] = True
        return None

    monkeypatch.setattr(epf, "_HTTP_GET_JSON", trap)
    assert epf._adapter_finnhub_quote("AAPL") is None
    assert seen["called"] is False


def test_finnhub_adapter_parses_quote(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key")
    monkeypatch.setattr(
        epf, "_HTTP_GET_JSON",
        lambda url, **kw: {"c": 175.30, "h": 176, "l": 174, "o": 175,
                            "pc": 174.5, "t": 1745858400},
    )
    out = epf._adapter_finnhub_quote("AAPL")
    assert out["price"] == 175.30
    assert out["source"] == "finnhub"


def test_finnhub_marketcap_converts_millions_to_dollars(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "k")
    monkeypatch.setattr(
        epf, "_HTTP_GET_JSON",
        lambda url, **kw: {"marketCapitalization": 2_750_000.0,
                            "name": "Apple", "ticker": "AAPL"},
    )
    mc = epf._adapter_finnhub_marketcap("AAPL")
    assert mc == 2_750_000.0 * 1_000_000  # $2.75T


def test_fmp_quote_includes_market_cap_piggyback(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "k")
    monkeypatch.setattr(
        epf, "_HTTP_GET_JSON",
        lambda url, **kw: [{"price": 410.55, "volume": 1234567,
                             "marketCap": 3_080_000_000_000.0}],
    )
    out = epf._adapter_fmp_quote("MSFT")
    assert out["price"] == 410.55
    assert out["volume"] == 1234567
    assert out["_market_cap"] == 3_080_000_000_000.0


def test_polygon_marketcap_parses_results_envelope(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "k")
    monkeypatch.setattr(
        epf, "_HTTP_GET_JSON",
        lambda url, **kw: {"results": {"market_cap": 1.5e12, "ticker": "AAPL"}},
    )
    assert epf._adapter_polygon_marketcap("AAPL") == 1.5e12


def test_polygon_marketcap_handles_missing_results(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "k")
    monkeypatch.setattr(epf, "_HTTP_GET_JSON",
                        lambda url, **kw: {"status": "OK"})  # no "results"
    assert epf._adapter_polygon_marketcap("AAPL") is None


def test_yfinance_adapter_returns_none_when_unavailable(monkeypatch):
    """Test the yfinance ImportError branch via direct hook injection."""
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **kw):
        if name == "yfinance":
            raise ImportError("yfinance not installed in this sandbox")
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert epf._adapter_yfinance_quote("AAPL") is None
    assert epf._adapter_yfinance_marketcap("AAPL") is None


# ---------------------------------------------------------------------------
# Public batch / drop-in helpers
# ---------------------------------------------------------------------------
def test_fetch_quotes_batch_returns_dict_keyed_by_ticker(monkeypatch):
    monkeypatch.setattr(
        epf, "_QUOTE_CHAIN",
        [lambda t: {"price": float(len(t)), "volume": 0, "asof": "x", "source": "stub"}],
    )
    out = epf.fetch_quotes_batch(["AAPL", "MSFT", "GOOGL"])
    assert set(out.keys()) == {"AAPL", "MSFT", "GOOGL"}
    assert out["AAPL"]["price"] == 4.0


def test_fetch_prices_default_returns_legacy_shape(monkeypatch):
    """`value_screener_runner` calls this expecting {ticker: price | None}."""
    monkeypatch.setattr(
        epf, "_QUOTE_CHAIN",
        [lambda t: {"price": 99.0, "volume": 0, "asof": "x", "source": "s"}
                    if t == "AAPL" else None],
    )
    out = epf.fetch_prices_default(["AAPL", "ZZZZ"])
    assert out == {"AAPL": 99.0, "ZZZZ": None}


def test_fetch_market_caps_default_returns_legacy_shape(monkeypatch):
    monkeypatch.setattr(
        epf, "_MARKETCAP_CHAIN",
        [lambda t: 1.0e12 if t == "AAPL" else None],
    )
    out = epf.fetch_market_caps_default(["AAPL", "ZZZZ"])
    assert out == {"AAPL": 1.0e12, "ZZZZ": None}


def test_normalize_ticker_lowers_and_strips():
    assert epf._normalize_ticker("  aapl  ") == "AAPL"
    assert epf._normalize_ticker("") == ""
    assert epf._normalize_ticker(None) == ""


# ---------------------------------------------------------------------------
# BLOCKER 1 regression — Stooq non-US handling
# ---------------------------------------------------------------------------
def test_stooq_skips_non_us_amsterdam_listing(monkeypatch):
    """ASML.AS is the Amsterdam listing — Stooq must NOT silently issue
    `asml.as.us` and return wrong-ticker data."""
    fired = {"http": False}

    def trap(url, **kw):
        fired["http"] = True
        return "Symbol,Date,Time,Open,High,Low,Close,Volume\nASML.US,2026-04-28,16:00:00,1,2,1,1.5,100\n"

    monkeypatch.setattr(epf, "_HTTP_GET_TEXT", trap)
    out = epf._adapter_stooq_quote("ASML.AS")
    assert out is None
    assert fired["http"] is False, "Stooq must skip non-US tickers BEFORE making any HTTP call"


def test_stooq_skips_non_us_hk_listing(monkeypatch):
    """9988.HK (Alibaba HK listing) must skip Stooq."""
    monkeypatch.setattr(epf, "_HTTP_GET_TEXT",
                        lambda url, **kw: pytest.fail("HTTP must not be called"))
    assert epf._adapter_stooq_quote("9988.HK") is None


def test_stooq_skips_unknown_exchange_suffix(monkeypatch):
    """An unrecognized suffix is treated as non-US — refuse to guess."""
    monkeypatch.setattr(epf, "_HTTP_GET_TEXT",
                        lambda url, **kw: pytest.fail("HTTP must not be called"))
    assert epf._adapter_stooq_quote("FOO.XYZ") is None


def test_stooq_handles_us_class_share_dot_to_hyphen(monkeypatch):
    """BRK.B is a US class share — Stooq URL must hyphenate to brk-b.us."""
    captured = {"url": None}

    def capture(url, **kw):
        captured["url"] = url
        return ("Symbol,Date,Time,Open,High,Low,Close,Volume\n"
                "BRK-B.US,2026-04-28,16:00:00,400,401,399,400.5,1000\n")

    monkeypatch.setattr(epf, "_HTTP_GET_TEXT", capture)
    out = epf._adapter_stooq_quote("BRK.B")
    assert out is not None
    assert out["price"] == 400.5
    assert "brk-b.us" in captured["url"]


def test_stooq_plain_us_ticker_still_works(monkeypatch):
    """Regression check: plain AAPL must still resolve to aapl.us (untouched behavior)."""
    captured = {"url": None}

    def capture(url, **kw):
        captured["url"] = url
        return ("Symbol,Date,Time,Open,High,Low,Close,Volume\n"
                "AAPL.US,2026-04-28,16:00:00,170,171,169,170.5,1000\n")

    monkeypatch.setattr(epf, "_HTTP_GET_TEXT", capture)
    out = epf._adapter_stooq_quote("AAPL")
    assert out is not None
    assert "aapl.us" in captured["url"]


def test_stooq_symbol_helper_returns_none_for_non_us():
    assert epf._stooq_symbol("ASML.AS") is None
    assert epf._stooq_symbol("9988.HK") is None
    assert epf._stooq_symbol("VOD.L") is None
    assert epf._stooq_symbol("FOO.UNKNOWN") is None


def test_stooq_symbol_helper_returns_us_form():
    assert epf._stooq_symbol("AAPL") == "aapl.us"
    assert epf._stooq_symbol("MSFT") == "msft.us"
    assert epf._stooq_symbol("BRK.B") == "brk-b.us"


# ---------------------------------------------------------------------------
# BLOCKER 2 regression — FMP cache bypass / piggyback marketcap caching
# ---------------------------------------------------------------------------
def test_fmp_marketcap_uses_quote_cache_no_double_http(monkeypatch):
    """fetch_quote(FMP) followed by fetch_market_cap(FMP) must NOT
    issue two HTTP calls — the piggyback marketcap is cached on the
    first call and re-used on the second.
    """
    monkeypatch.setenv("FMP_API_KEY", "k")
    http_calls = {"n": 0}

    def fmp_response(url, **kw):
        http_calls["n"] += 1
        return [{"price": 410.55, "volume": 1234567,
                 "marketCap": 3_080_000_000_000.0}]

    monkeypatch.setattr(epf, "_HTTP_GET_JSON", fmp_response)
    # Force chain to be FMP-only so we don't get piggyback from another adapter
    monkeypatch.setattr(epf, "_QUOTE_CHAIN", [epf._adapter_fmp_quote])
    monkeypatch.setattr(epf, "_MARKETCAP_CHAIN", [epf._adapter_fmp_marketcap])

    q = epf.fetch_quote("MSFT")
    assert q["price"] == 410.55
    # Second call: should reuse the side-channel marketcap cache, no new HTTP
    mc = epf.fetch_market_cap("MSFT")
    assert mc == 3_080_000_000_000.0
    assert http_calls["n"] == 1, (
        f"FMP must be called exactly once across fetch_quote + fetch_market_cap, "
        f"got {http_calls['n']}"
    )


def test_fmp_marketcap_writes_piggyback_cache_with_source_tag(monkeypatch):
    """The side-channel marketcap cache must record source='fmp_piggyback'
    so a future fetch_market_cap call knows it can short-circuit."""
    monkeypatch.setenv("FMP_API_KEY", "k")
    monkeypatch.setattr(
        epf, "_HTTP_GET_JSON",
        lambda url, **kw: [{"price": 100.0, "volume": 1, "marketCap": 5e11}],
    )
    monkeypatch.setattr(epf, "_QUOTE_CHAIN", [epf._adapter_fmp_quote])

    epf.fetch_quote("PIGGYBACK")
    cached = epf._cache_read("PIGGYBACK", "marketcap")
    assert cached is not None
    assert cached["market_cap"] == 5e11
    assert cached["source"] == "fmp_piggyback"


def test_fetch_quote_does_not_persist_market_cap_in_quote_cache(monkeypatch):
    """Quote cache must remain free of `_market_cap` (regression on existing behavior)."""
    monkeypatch.setenv("FMP_API_KEY", "k")
    monkeypatch.setattr(
        epf, "_HTTP_GET_JSON",
        lambda url, **kw: [{"price": 50.0, "volume": 1, "marketCap": 1e11}],
    )
    monkeypatch.setattr(epf, "_QUOTE_CHAIN", [epf._adapter_fmp_quote])
    epf.fetch_quote("HHH")
    quote_cache = epf._cache_read("HHH", "quote")
    assert "_market_cap" not in quote_cache


# ---------------------------------------------------------------------------
# BLOCKER 3 regression — parallel batch fetch + circuit breaker
# ---------------------------------------------------------------------------
def test_fetch_quotes_batch_runs_in_parallel(monkeypatch):
    """Parallel batch must complete faster than sequential by a clear margin."""
    sleep_per_call = 0.05  # 50ms per ticker

    def slow(t):
        time.sleep(sleep_per_call)
        return {"price": 1.0, "volume": 0, "asof": "x", "source": "slow"}

    monkeypatch.setattr(epf, "_QUOTE_CHAIN", [slow])
    tickers = [f"T{i}" for i in range(8)]
    start = time.perf_counter()
    out = epf.fetch_quotes_batch(tickers, use_cache=False, max_workers=8)
    elapsed = time.perf_counter() - start
    assert len(out) == 8
    # Sequential would be ~8 * 50ms = 400ms; with 8 workers, expect <250ms.
    # Allow generous slack for Windows ThreadPoolExecutor warmup.
    sequential_time = sleep_per_call * len(tickers)
    assert elapsed < sequential_time * 0.7, (
        f"parallel fetch took {elapsed:.3f}s; sequential would be {sequential_time:.3f}s — "
        f"expected <70% of sequential"
    )


def test_fetch_quotes_batch_returns_all_tickers(monkeypatch):
    monkeypatch.setattr(
        epf, "_QUOTE_CHAIN",
        [lambda t: {"price": float(len(t)), "volume": 0, "asof": "x", "source": "stub"}],
    )
    out = epf.fetch_quotes_batch(["AAA", "BBBB", "CC"], use_cache=False)
    assert set(out.keys()) == {"AAA", "BBBB", "CC"}
    assert out["BBBB"]["price"] == 4.0


def test_fetch_quotes_batch_circuit_breaker_aborts_on_consecutive_failures(monkeypatch):
    """If N tickers in a row return None, the breaker must stop further fetches."""
    fetch_count = {"n": 0}

    def always_fail(t):
        fetch_count["n"] += 1
        return None

    monkeypatch.setattr(epf, "_QUOTE_CHAIN", [always_fail])
    tickers = [f"T{i}" for i in range(50)]
    out = epf.fetch_quotes_batch(tickers, use_cache=False, max_workers=1,
                                  failure_budget=5)
    assert len(out) == 50
    # All tickers reported as None
    assert all(v is None for v in out.values())
    # Breaker must trip before all 50 are tried — we expect well under 50 calls
    assert fetch_count["n"] <= 12, (
        f"circuit breaker should have aborted after ~5-8 failures, "
        f"saw {fetch_count['n']} calls"
    )


def test_fetch_quotes_batch_circuit_breaker_disabled_when_budget_zero(monkeypatch):
    """failure_budget=0 disables the breaker (used for debug / always-complete runs)."""
    fetch_count = {"n": 0}

    def always_fail(t):
        fetch_count["n"] += 1
        return None

    monkeypatch.setattr(epf, "_QUOTE_CHAIN", [always_fail])
    out = epf.fetch_quotes_batch([f"T{i}" for i in range(20)], use_cache=False,
                                  max_workers=1, failure_budget=0)
    assert fetch_count["n"] == 20
    assert all(v is None for v in out.values())


def test_fetch_quotes_batch_resets_failure_counter_on_success(monkeypatch):
    """A success in the middle resets the consecutive-failure counter.

    With budget=5, 4 fails (T0-T3) then a success at T4 must reset the
    counter; subsequent fails must accumulate again from 0. Without the
    reset, the breaker would trip too early on streaks broken by sporadic
    successes.
    """
    results_map = {f"T{i}": None for i in range(20)}
    results_map["T4"] = {"price": 1.0, "volume": 0, "asof": "x", "source": "ok"}

    monkeypatch.setattr(epf, "_QUOTE_CHAIN", [lambda t: results_map.get(t)])
    out = epf.fetch_quotes_batch(list(results_map.keys()), use_cache=False,
                                  max_workers=1, failure_budget=5)
    # T4 success means counter resets to 0; breaker can't trip until T9
    assert out["T4"] is not None
    # T0-T3 returned None (4 fails, under budget), T4 success, T5-T9 fails (breaker trips at T9)
    # T0-T8 must have been called and returned correct results
    for i in range(9):
        if i == 4:
            assert out[f"T{i}"] is not None, f"T{i} should be the success row"
        else:
            assert out[f"T{i}"] is None, f"T{i} should have been called (and returned None)"


def test_fetch_market_caps_batch_runs_in_parallel(monkeypatch):
    """Parallel marketcap batch must work the same way."""
    monkeypatch.setattr(
        epf, "_MARKETCAP_CHAIN",
        [lambda t: float(len(t)) * 1e9],
    )
    out = epf.fetch_market_caps_batch(["AAA", "BBBB", "CC"], use_cache=False)
    assert out == {"AAA": 3e9, "BBBB": 4e9, "CC": 2e9}


# ---------------------------------------------------------------------------
# BLOCKER 4 regression — EDGAR price decoupling (no recursion into full quote chain)
# ---------------------------------------------------------------------------
def test_edgar_marketcap_does_not_recurse_into_full_quote_chain(monkeypatch):
    """When fetch_market_cap reaches EDGAR, EDGAR must NOT call fetch_quote()
    (which walks all 7 quote sources). The minimal price fetch uses ONLY
    Stooq + Finnhub directly.
    """
    fetch_quote_called = {"n": 0}

    def trap_fetch_quote(*a, **kw):
        fetch_quote_called["n"] += 1
        return None

    monkeypatch.setattr(epf, "fetch_quote", trap_fetch_quote)

    # Stub the FundamentalsFetcher to return shares_outstanding
    class _StubFundamentals:
        def fetch(self, ticker, **kw):
            class _Rec:
                balance_sheet = {"shares_outstanding": 1e9}
            return _Rec()

    import alpha_engine.fundamentals_fetcher as ff
    monkeypatch.setattr(ff, "FundamentalsFetcher", _StubFundamentals)

    # Stub _adapter_stooq_quote to return a price (the minimal chain's first stop)
    monkeypatch.setattr(
        epf, "_adapter_stooq_quote",
        lambda t: {"price": 50.0, "volume": 0, "asof": "x", "source": "stooq"},
    )

    mc = epf._adapter_edgar_marketcap("AAPL")
    assert mc == 5e10  # 1e9 shares * $50
    assert fetch_quote_called["n"] == 0, (
        "EDGAR adapter must not recurse into the full quote chain; "
        "it must use the minimal Stooq+Finnhub price fetch instead"
    )


def test_edgar_marketcap_accepts_explicit_price_kwarg(monkeypatch):
    """When caller passes a known-good price, EDGAR uses it without fetching."""

    class _StubFundamentals:
        def fetch(self, ticker, **kw):
            class _Rec:
                balance_sheet = {"shares_outstanding": 2e9}
            return _Rec()

    import alpha_engine.fundamentals_fetcher as ff
    monkeypatch.setattr(ff, "FundamentalsFetcher", _StubFundamentals)

    # Trap any minimal-price fetch — it must NOT be called
    def fail_minimal(t):
        pytest.fail("minimal-price fetch must not run when explicit price provided")

    monkeypatch.setattr(epf, "_edgar_minimal_price", fail_minimal)
    mc = epf._adapter_edgar_marketcap("AAPL", price=100.0)
    assert mc == 2e11  # 2e9 * $100


def test_edgar_minimal_price_uses_only_stooq_and_finnhub(monkeypatch):
    """The minimal-price chain must be exactly Stooq + Finnhub, in order."""
    calls = []

    def stooq(t):
        calls.append("stooq")
        return None

    def finnhub(t):
        calls.append("finnhub")
        return {"price": 42.0, "volume": 0, "asof": "x", "source": "finnhub"}

    monkeypatch.setattr(epf, "_adapter_stooq_quote", stooq)
    monkeypatch.setattr(epf, "_adapter_finnhub_quote", finnhub)
    p = epf._edgar_minimal_price("AAPL")
    assert p == 42.0
    assert calls == ["stooq", "finnhub"]


def test_fetch_market_cap_passes_price_hint_to_edgar(monkeypatch):
    """fetch_market_cap pre-fetches the EDGAR price hint and passes it
    so EDGAR doesn't recompute it. Verifies the orchestrator side."""
    edgar_received_price = {"value": "not-set"}

    def fake_edgar(ticker, *, price=None):
        edgar_received_price["value"] = price
        if price is None:
            return None
        return float(price) * 1e9

    monkeypatch.setattr(epf, "_adapter_edgar_marketcap", fake_edgar)
    monkeypatch.setattr(epf, "_MARKETCAP_CHAIN", [fake_edgar])
    monkeypatch.setattr(
        epf, "_adapter_stooq_quote",
        lambda t: {"price": 75.0, "volume": 0, "asof": "x", "source": "stooq"},
    )
    mc = epf.fetch_market_cap("AAPL", use_cache=False)
    assert edgar_received_price["value"] == 75.0
    assert mc == 75.0 * 1e9
