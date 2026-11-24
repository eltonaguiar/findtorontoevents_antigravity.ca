"""Tests for prediction_market_agents.polymarket_momentum_agent + shared
alpha_engine.polymarket_signals fetch/parse path.

Root-cause regression (2026-11-16): Gamma's `order=volume` silently sorts the
*string* `volume` field lexicographically, so the top-N market window was an
arbitrary slice and scan_momentum() emitted 0 rows with no error ("silent
empty"). These tests pin the fix with fixtures of the expected upstream
payloads (Gamma `/markets` rows and CLOB `/prices-history` rows, shapes
captured live 2026-11-16):

  - fetch_crypto_markets() must request the numeric sort key `order=volumeNum`
  - scan_momentum() must emit rows when upstream momentum data exists
  - an empty result must NEVER be silent: payload carries status+notice/error
    and a ::warning:: / ::error:: stderr annotation is emitted
  - a genuine p=0.0 history point must not be coerced to the current price
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpha_engine import polymarket_signals
from prediction_market_agents import polymarket_momentum_agent

BASE_TS = 1_800_000_000  # fixed synthetic epoch for history fixtures

GAMMA_MARKET_FIXTURE_UPDOWN = {
    "id": "900001",
    "question": "Bitcoin Up or Down - November 16, 2:00PM-2:30PM ET",
    "slug": "bitcoin-up-or-down-nov-16-2pm",
    "active": True,
    "closed": False,
    "endDate": "2027-01-01T00:00:00Z",
    "outcomes": '["Up", "Down"]',
    "outcomePrices": '["0.62", "0.38"]',
    "volume": "48231.55",
    "volumeNum": 48231.55,
    "volume24hr": 48231.55,
    "liquidityNum": 12345.6,
    "clobTokenIds": '["1111111111", "1111111112"]',
}

GAMMA_MARKET_FIXTURE_PRICE_ABOVE = {
    "id": "900002",
    "question": "Will Ethereum reach $3,000 by December 31?",
    "slug": "will-ethereum-reach-3000",
    "active": True,
    "closed": False,
    "endDate": "2027-01-01T00:00:00Z",
    "outcomes": '["Yes", "No"]',
    "outcomePrices": '["0.75", "0.25"]',
    "volume": "25000.0",
    "volumeNum": 25000.0,
    "volume24hr": 8000.0,
    "liquidityNum": 9000.0,
    "clobTokenIds": '["2222222221", "2222222222"]',
}

# CLOB /prices-history shape: {"history": [{"t": epoch_seconds, "p": price}]}
CLOB_HISTORY_FIXTURE_BTC = {
    "history": [
        {"t": BASE_TS - 8 * 3600, "p": 0.35},
        {"t": BASE_TS - 4 * 3600, "p": 0.40},
        {"t": BASE_TS, "p": 0.55},
    ]
}

CLOB_HISTORY_FIXTURE_ETH = {
    "history": [
        {"t": BASE_TS - 2 * 3600, "p": 0.60},
        {"t": BASE_TS, "p": 0.75},
    ]
}

CLOB_HISTORY_FIXTURE_FLAT = {
    "history": [
        {"t": BASE_TS - 8 * 3600, "p": 0.50},
        {"t": BASE_TS, "p": 0.50},
    ]
}


class _FakeUpstream:
    """Route-based stand-in for polymarket_signals._fetch_json."""

    def __init__(self, markets, histories, raise_error=False):
        self.markets = markets
        self.histories = histories
        self.raise_error = raise_error
        self.market_params = []

    def __call__(self, url, params=None):
        if self.raise_error:
            raise RuntimeError("simulated transport explosion")
        if "/markets" in url:
            self.market_params.append(dict(params or {}))
            return list(self.markets)
        if "/prices-history" in url:
            token = (params or {}).get("market", "")
            return self.histories.get(token, {"history": []})
        return None


@pytest.fixture
def fake_env(monkeypatch, tmp_path):
    """Wire fixtures in and stop OUTPUT_FILE / price snapshots touching reality."""
    monkeypatch.setattr(
        polymarket_momentum_agent, "OUTPUT_FILE", tmp_path / "momentum_signals.json"
    )
    monkeypatch.setattr(
        polymarket_momentum_agent,
        "_snapshot_trade_levels",
        lambda symbol, direction: (50000.0, 51250.0, 49250.0),
    )
    return monkeypatch


def _install(monkeypatch, fake):
    polymarket_signals._FETCH_ERRORS.clear()
    monkeypatch.setattr(polymarket_signals, "_fetch_json", fake)


def test_fetch_crypto_markets_uses_numeric_sort_key(fake_env):
    fake = _FakeUpstream([GAMMA_MARKET_FIXTURE_UPDOWN], {})
    _install(fake_env, fake)

    markets = polymarket_signals.fetch_crypto_markets(limit=100)

    assert fake.market_params, "Gamma /markets endpoint was never called"
    for params in fake.market_params:
        assert params.get("order") == "volumeNum", (
            "Gamma `order=volume` sorts the string field lexicographically; "
            "the numeric sort key `volumeNum` must be used"
        )
    assert [m["symbol"] for m in markets] == ["BTCUSDT"]


def test_scan_momentum_emits_rows_when_data_exists(fake_env):
    fake = _FakeUpstream(
        [GAMMA_MARKET_FIXTURE_UPDOWN, GAMMA_MARKET_FIXTURE_PRICE_ABOVE],
        {
            "1111111111": CLOB_HISTORY_FIXTURE_BTC,
            "2222222221": CLOB_HISTORY_FIXTURE_ETH,
        },
    )
    _install(fake_env, fake)

    result = polymarket_momentum_agent.scan_momentum()

    assert result["status"] == "ok"
    assert result["error"] is None
    assert result["momentum_signals"] == 2
    by_symbol = {s["symbol"]: s for s in result["signals"]}
    assert by_symbol["BTCUSDT"]["direction"] == "LONG"
    assert by_symbol["BTCUSDT"]["strategy"] == "pm_momentum_detector"
    assert by_symbol["BTCUSDT"]["source_system"] == "polymarket_momentum"
    assert by_symbol["ETHUSDT"]["direction"] == "LONG"
    assert by_symbol["ETHUSDT"]["signal_type"] == "BUY"
    assert by_symbol["BTCUSDT"]["momentum_data"]["delta_4h"] == pytest.approx(0.15)
    saved = json.loads(polymarket_momentum_agent.OUTPUT_FILE.read_text())
    assert saved["momentum_signals"] == 2


def test_scan_momentum_empty_is_never_silent(fake_env, capsys):
    fake = _FakeUpstream(
        [GAMMA_MARKET_FIXTURE_UPDOWN], {"1111111111": CLOB_HISTORY_FIXTURE_FLAT}
    )
    _install(fake_env, fake)

    result = polymarket_momentum_agent.scan_momentum()

    assert result["momentum_signals"] == 0
    assert result["signals"] == []
    assert result["status"] == "empty"
    assert result["notice"], "empty emission must carry a notice"
    assert result["error"] is None
    err = capsys.readouterr().err
    assert "::warning::" in err


def test_scan_momentum_fetch_failure_is_loud(fake_env, capsys):
    fake = _FakeUpstream([], {}, raise_error=True)
    _install(fake_env, fake)

    result = polymarket_momentum_agent.scan_momentum()

    assert result["status"] == "error"
    assert result["error"]
    assert result["notice"]
    err = capsys.readouterr().err
    assert "::error::" in err


def test_swallowed_fetch_error_surfaces_as_error_not_empty(fake_env, capsys):
    fake = _FakeUpstream([], {})

    def failing_fetch(url, params=None):
        polymarket_signals._FETCH_ERRORS.append(f"HTTP 500 fetching {url}: boom")
        return None

    polymarket_signals._FETCH_ERRORS.clear()
    fake_env.setattr(polymarket_signals, "_fetch_json", failing_fetch)

    result = polymarket_momentum_agent.scan_momentum()

    assert result["status"] == "error"
    assert "HTTP 500" in (result["error"] or "")
    assert "::error::" in capsys.readouterr().err


def test_calculate_clob_momentum_zero_prob_not_coerced():
    history = {
        "history": [
            {"t": BASE_TS, "p": 0.0},
            {"t": BASE_TS + 24 * 3600, "p": 0.9},
        ]
    }["history"]
    mom = polymarket_signals.calculate_clob_momentum(history)
    assert mom is not None
    # A genuine p=0.0 point four-plus hours back must be used as-is; coercing
    # falsy 0.0 to "current" would zero the momentum and hide the move.
    assert mom["momentum_4h"] == pytest.approx(0.9)
    assert mom["momentum_signal"] == "BULLISH"
