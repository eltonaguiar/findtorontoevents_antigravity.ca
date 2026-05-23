"""Tests for tools/ai_attribution/capture_production_pick.py."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.ai_attribution.capture_production_pick import (  # noqa: E402
    _confidence_pct, _normalize_direction, to_attribution_record,
)


def test_happy_path():
    p = {
        "id": "P1", "symbol": "AAPL", "strategy": "Classic Momentum",
        "source_system": "smart_picks", "asset_class": "equity",
        "direction": "long", "confidence": 0.72,
        "created_at": "2026-05-16T00:00:00Z", "timeframe": "1d",
    }
    rec = to_attribution_record(p)
    assert rec["pick_id"] == "P1"
    assert rec["asset_class"] == "EQUITY"          # upper-cased
    assert rec["direction"] == "LONG"
    assert rec["consensus_tier"] == "rule_engine"
    assert len(rec["models_consulted"]) == 1
    mc = rec["models_consulted"][0]
    assert mc["underlying_model"] == "rule_engine"
    assert mc["name"] == "smart_picks"
    assert mc["vote"] == "LONG"
    assert mc["confidence_0_100"] == 72
    assert mc["justification_summary"] == "Classic Momentum"


def test_empty_dict_does_not_crash():
    rec = to_attribution_record({})
    assert rec["pick_id"].startswith("ruleadapt-")
    assert rec["asset_class"] == "UNKNOWN"
    assert rec["direction"] == "LONG"
    assert rec["models_consulted"][0]["underlying_model"] == "rule_engine"
    assert rec["models_consulted"][0]["confidence_0_100"] == 0


def test_none_input_does_not_crash():
    rec = to_attribution_record(None)  # type: ignore[arg-type]
    assert rec["pick_id"].startswith("ruleadapt-")


def test_missing_confidence_is_zero():
    rec = to_attribution_record({"id": "X", "symbol": "BTC"})
    assert rec["models_consulted"][0]["confidence_0_100"] == 0


def test_string_confidence_handled():
    assert _confidence_pct("0.5") == 50
    assert _confidence_pct("garbage") == 0
    assert _confidence_pct(None) == 0


def test_confidence_clamped_and_percent_form():
    assert _confidence_pct(1.0) == 100      # fraction 1.0 -> 100%
    assert _confidence_pct(2.0) == 2        # >1.5 treated as already-percent
    assert _confidence_pct(150) == 100      # out-of-range percent clamps
    assert _confidence_pct(-0.3) == 0       # negative clamps to 0
    assert _confidence_pct(85) == 85        # already percent


def test_direction_normalization():
    assert _normalize_direction("buy") == "LONG"
    assert _normalize_direction("SELL") == "SHORT"
    assert _normalize_direction("short") == "SHORT"
    assert _normalize_direction(None) == "LONG"
    assert _normalize_direction("garbage") == "LONG"


def test_pick_id_generated_when_absent():
    r1 = to_attribution_record({"symbol": "A"})
    r2 = to_attribution_record({"symbol": "A"})
    assert r1["pick_id"] != r2["pick_id"]   # unique each call
    assert all(r["pick_id"].startswith("ruleadapt-") for r in (r1, r2))


def test_source_falls_back_to_strategy():
    rec = to_attribution_record({"id": "X", "strategy": "vwap_reclaim"})
    assert rec["models_consulted"][0]["name"] == "vwap_reclaim"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
