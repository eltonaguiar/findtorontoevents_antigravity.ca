"""Regression tests for git-checkout mtime poisoning on price failover caches."""
from __future__ import annotations

import json
import os
import time

import alpha_engine.commodity_price_failover as cpf
import alpha_engine.equity_price_failover as epf
import alpha_engine.forex_price_failover as fpf


def test_commodity_cache_rejects_fresh_mtime_without_cached_at(tmp_path, monkeypatch):
    cache_dir = tmp_path / "commodity_cache"
    cache_dir.mkdir(parents=True)
    monkeypatch.setattr(cpf, "CACHE_DIR", cache_dir)

    stale = cache_dir / "CL_F.json"
    stale.write_text(
        json.dumps({"price": 75.0, "symbol": "CL=F", "currency": "USD",
                    "asof": "2026-06-06", "source": "yahoo_v8"}),
        encoding="utf-8",
    )
    os.utime(stale, None)  # simulate fresh git checkout mtime

    calls = {"n": 0}

    def live_adapter(sym):
        calls["n"] += 1
        return {"price": 68.5, "symbol": "CL=F", "currency": "USD",
                "asof": "2026-11-15", "source": "live_mock"}

    monkeypatch.setattr(cpf, "_ADAPTERS", [live_adapter])
    res = cpf.fetch_commodity_price("CL=F")
    assert res["price"] == 68.5
    assert res["source"] == "live_mock"
    assert calls["n"] == 1
    assert "_cached_at" not in res


def test_commodity_cache_rejects_expired_cached_at_even_with_fresh_mtime(tmp_path, monkeypatch):
    cache_dir = tmp_path / "commodity_cache"
    cache_dir.mkdir(parents=True)
    monkeypatch.setattr(cpf, "CACHE_DIR", cache_dir)

    stale = cache_dir / "ZS_F.json"
    stale.write_text(
        json.dumps({"price": 1180.0, "symbol": "ZS=F", "currency": "USD",
                    "asof": "2026-06-06", "source": "yahoo_v8",
                    "_cached_at": time.time() - cpf.CACHE_TTL_SEC - 60}),
        encoding="utf-8",
    )
    os.utime(stale, None)

    monkeypatch.setattr(
        cpf, "_ADAPTERS",
        [lambda sym: {"price": 1020.0, "symbol": "ZS=F", "currency": "USD",
                      "asof": "2026-11-15", "source": "live_mock"}],
    )
    res = cpf.fetch_commodity_price("ZS=F")
    assert res["price"] == 1020.0


def test_forex_cache_rejects_stale_and_supports_use_cache_false(tmp_path, monkeypatch):
    cache_dir = tmp_path / "forex_cache"
    cache_dir.mkdir(parents=True)
    monkeypatch.setattr(fpf, "CACHE_DIR", cache_dir)

    stale = cache_dir / "EURGBP.json"
    stale.write_text(
        json.dumps({"price": 0.85, "base": "EUR", "quote": "GBP",
                    "asof": "2026-06-06", "source": "yahoo_v8"}),
        encoding="utf-8",
    )
    os.utime(stale, None)

    calls = {"n": 0}

    def live_fx(pair):
        calls["n"] += 1
        return {"price": 0.831 + 0.001 * calls["n"], "base": "EUR", "quote": "GBP",
                "asof": "2026-11-15", "source": "live_fx"}

    monkeypatch.setattr(fpf, "_ADAPTERS", [live_fx])
    r1 = fpf.fetch_forex_rate("EURGBP")
    r2 = fpf.fetch_forex_rate("EURGBP")
    assert r1 == r2
    assert calls["n"] == 1
    assert "_cached_at" not in r1

    r3 = fpf.fetch_forex_rate("EURGBP", use_cache=False)
    assert calls["n"] == 2
    assert r3["price"] != r1["price"]


def test_equity_cache_rejects_expired_cached_at_with_fresh_mtime(tmp_path, monkeypatch):
    cache_dir = tmp_path / "equity_cache"
    cache_dir.mkdir(parents=True)
    monkeypatch.setattr(epf, "CACHE_DIR", cache_dir)

    stale = cache_dir / "TBLU.quote.json"
    stale.write_text(
        json.dumps({"price": 10.0, "volume": 100, "asof": "2026-11-13",
                    "source": "old", "_cached_at": time.time() - epf.CACHE_TTL_SEC - 10}),
        encoding="utf-8",
    )
    os.utime(stale, None)

    monkeypatch.setattr(
        epf, "_QUOTE_CHAIN",
        [lambda t: {"price": 15.5, "volume": 200, "asof": "2026-11-15", "source": "fresh"}],
    )
    res = epf.fetch_quote("TBLU")
    assert res["price"] == 15.5
    assert "_cached_at" not in res
