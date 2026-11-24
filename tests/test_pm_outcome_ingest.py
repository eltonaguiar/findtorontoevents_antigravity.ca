"""Tests for audit_trail.pm_outcome_ingest (offline, injected fetchers)."""

import json
from datetime import datetime, timezone

import pytest

from audit_trail.pm_contract_resolver import load_market_outcomes, resolve_contract_pick
from audit_trail.pm_outcome_ingest import (
    ingest,
    parse_kalshi,
    parse_polymarket,
)

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)


def test_parse_polymarket_reads_settled_price():
    records = parse_polymarket(
        [
            {
                "id": "0xabc",
                "outcomes": '["Yes", "No"]',
                "outcomePrices": '["1", "0"]',
                "endDate": "2026-11-15T00:00:00Z",
            },
            {
                "id": "0xdef",
                "outcomes": '["Yes", "No"]',
                "outcomePrices": '["0", "1"]',
            },
        ]
    )
    assert records[0]["outcome"] == "YES"
    assert records[1]["outcome"] == "NO"
    assert records[0]["source"] == "polymarket"


def test_parse_polymarket_skips_unsettled_market():
    records = parse_polymarket(
        [{"id": "0xopen", "outcomes": '["Yes","No"]', "outcomePrices": '["0.62","0.38"]'}]
    )
    assert records == []


def test_parse_kalshi_uses_result_field():
    records = parse_kalshi(
        [
            {"ticker": "KXBTC-25", "result": "yes", "close_time": "2026-11-01T00:00:00Z"},
            {"ticker": "KXETH-25", "result": "no"},
            {"ticker": "KXOPEN", "result": ""},
        ]
    )
    assert [r["outcome"] for r in records] == ["YES", "NO"]


def test_ingest_merges_existing_and_writes_feed(tmp_path):
    out = tmp_path / "pm_market_outcomes.json"
    out.write_text(
        json.dumps({"markets": [{"market_id": "OLD-1", "outcome": "YES"}]}), encoding="utf-8"
    )
    result = ingest(
        out,
        polymarket_fetcher=lambda: [
            {"market_id": "PM-1", "ticker": "PM-1", "outcome": "NO", "source": "polymarket"}
        ],
        kalshi_fetcher=lambda: [
            {"market_id": "K-1", "ticker": "K-1", "outcome": "YES", "source": "kalshi"}
        ],
    )
    payload = json.loads(out.read_text(encoding="utf-8"))
    ids = {m["market_id"] for m in payload["markets"]}
    assert ids == {"OLD-1", "PM-1", "K-1"}
    assert result["total"] == 3
    assert result["errors"] == []


def test_ingest_fail_open_on_fetcher_error(tmp_path):
    result = ingest(
        tmp_path / "feed.json",
        polymarket_fetcher=lambda: (_ for _ in ()).throw(RuntimeError("429")),
        kalshi_fetcher=lambda: [],
    )
    assert result["total"] == 0
    assert result["errors"] and "429" in result["errors"][0]


def test_local_only_never_calls_fetchers(tmp_path):
    def boom():
        raise AssertionError("network fetch attempted in local-only mode")

    result = ingest(tmp_path / "feed.json", polymarket_fetcher=boom, kalshi_fetcher=boom, local_only=True)
    assert result["fetched"] == 0


def test_end_to_end_ingest_then_resolve(tmp_path):
    out = tmp_path / "pm_market_outcomes.json"
    ingest(
        out,
        polymarket_fetcher=lambda: [
            {
                "market_id": "0xchain",
                "ticker": "0xchain",
                "outcome": "YES",
                "source": "polymarket",
            }
        ],
        kalshi_fetcher=lambda: [],
    )
    markets = load_market_outcomes((str(out),))
    pick = {"market_id": "0xchain", "contract_side": "YES", "entry_price": 0.30}
    settled = resolve_contract_pick(pick, markets, now=NOW)
    assert settled["status"] == "WON"
    assert settled["pnl_pct"] == pytest.approx(233.3333, abs=1e-3)
