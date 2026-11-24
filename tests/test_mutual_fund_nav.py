"""Tests for alpha_engine.mutual_fund_nav."""

from datetime import datetime, timedelta, timezone

import pytest

from alpha_engine.mutual_fund_nav import (
    MUTUAL_FUND_SYMBOLS,
    build_nav_record,
    fetch_nav,
    fetch_navs,
    is_mutual_fund,
)

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)


def test_known_funds_classify_and_equities_do_not():
    assert is_mutual_fund("VFIAX") is True
    assert is_mutual_fund(" vfiax ") is True
    assert is_mutual_fund("SPY") is False
    assert is_mutual_fund("AAPL") is False
    assert is_mutual_fund(None) is False


def test_universe_is_no_load_core_funds():
    assert {"VFIAX", "VTSAX", "FXAIX", "SWPPX"} <= MUTUAL_FUND_SYMBOLS
    assert not ({"SPY", "QQQ", "TLT"} & MUTUAL_FUND_SYMBOLS)


def test_build_nav_record_computes_daily_change():
    record = build_nav_record("vfiax", [("2026-11-13", 100.0), ("2026-11-14", 101.0)])
    assert record["symbol"] == "VFIAX"
    assert record["nav"] == pytest.approx(101.0)
    assert record["prev_nav"] == pytest.approx(100.0)
    assert record["change_pct"] == pytest.approx(1.0)
    assert record["nav_date"] == "2026-11-14"


def test_build_nav_record_sorts_and_skips_bad_values():
    record = build_nav_record(
        "SWPPX",
        [("2026-11-14", 50.0), ("2026-11-12", 0.0), ("2026-11-13", 49.0)],
    )
    assert record["nav"] == pytest.approx(50.0)
    assert record["prev_nav"] == pytest.approx(49.0)


def test_empty_history_returns_none():
    assert build_nav_record("VFIAX", []) is None


def test_fetch_nav_uses_cache_within_ttl(tmp_path):
    calls = []

    def provider(symbol, period):
        calls.append(symbol)
        return [("2026-11-13", 10.0), ("2026-11-14", 10.5)]

    cache = tmp_path / "nav.json"
    first = fetch_nav("VFIAX", cache_path=cache, now=NOW, history_provider=provider)
    second = fetch_nav("VFIAX", cache_path=cache, now=NOW, history_provider=provider)
    assert first["nav"] == pytest.approx(10.5)
    assert second["nav"] == pytest.approx(10.5)
    assert calls == ["VFIAX"], "second call should be served from cache"


def test_fetch_nav_refetches_after_ttl(tmp_path):
    calls = []

    def provider(symbol, period):
        calls.append(symbol)
        return [("2026-11-13", 10.0), ("2026-11-14", 10.0 + len(calls))]

    cache = tmp_path / "nav.json"
    fetch_nav("VTSAX", cache_path=cache, now=NOW, history_provider=provider)
    later = NOW + timedelta(hours=13)
    record = fetch_nav("VTSAX", cache_path=cache, now=later, history_provider=provider)
    assert len(calls) == 2
    assert record["nav"] == pytest.approx(12.0)


def test_fetch_nav_fails_open_on_provider_error(tmp_path):
    def boom(symbol, period):
        raise RuntimeError("provider down")

    assert fetch_nav("FXAIX", cache_path=tmp_path / "nav.json", history_provider=boom) is None


def test_fetch_navs_batch(tmp_path):
    def provider(symbol, period):
        return [("2026-11-14", 20.0)]

    out = fetch_navs(
        ["VFIAX", "SWPPX"], cache_path=tmp_path / "nav.json", now=NOW, history_provider=provider
    )
    assert set(out) == {"VFIAX", "SWPPX"}
    assert out["SWPPX"]["nav"] == pytest.approx(20.0)


# ── class registration ─────────────────────────────────────────────────────
def test_registered_in_classifiers():
    from alpha_engine.asset_class import (
        asset_class_from_symbol,
        classify_pick_asset_class_upper,
        normalize_asset_class,
    )
    from alpha_engine.money_ready_verdict import CANONICAL_ASSET_CLASSES, CLASS_WR_FLOORS
    from audit_trail.asset_classification import ASSET_CLASSES, AssetClass, classify_asset
    from audit_trail.quality_gates import ASSET_CLASS_SMART_THRESHOLDS

    assert asset_class_from_symbol("VFIAX") == "mutual_fund"
    assert normalize_asset_class({"symbol": "VFIAX"}) == "mutual_fund"
    assert normalize_asset_class({"symbol": "FXAIX", "category": "mutual_fund"}) == "mutual_fund"
    assert classify_pick_asset_class_upper({"symbol": "SWPPX"}) == "MUTUAL_FUND"
    assert classify_asset("FXAIX") is AssetClass.MUTUAL_FUND
    assert "MUTUAL_FUND" in ASSET_CLASSES
    assert "MUTUAL_FUND" in CANONICAL_ASSET_CLASSES
    assert "MUTUAL_FUND" in CLASS_WR_FLOORS
    assert "MUTUAL_FUND" in ASSET_CLASS_SMART_THRESHOLDS


def test_other_classes_unchanged_by_mf_registration():
    from alpha_engine.asset_class import asset_class_from_symbol

    assert asset_class_from_symbol("SPY") == "etf"
    assert asset_class_from_symbol("TLT") == "bond"
    assert asset_class_from_symbol("AAPL") == "equity"
    assert asset_class_from_symbol("EURUSD=X") == "forex"
    assert asset_class_from_symbol("CL=F") == "futures"


def test_empty_class_reports_unproven_not_pass():
    import audit_trail.dashboard_generator as generator

    smart_by_asset, summary = generator._build_per_asset_quality_summary([], [], "t")
    mf = summary["MUTUAL_FUND"]
    assert mf["activeCount"] == 0
    assert mf["smartCount"] == 0
    assert mf["thresholdPass"] is False
    assert smart_by_asset["MUTUAL_FUND"] == []
    assert [k for k, v in summary.items() if v["activeCount"] == 0 and v["thresholdPass"]] == []
