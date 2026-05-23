"""Unit tests for alpha_engine.trust_audit_export — entry-time trust audit snapshots."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure repo root on sys.path so imports work
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from alpha_engine.trust_audit_export import (
    EXPORT_DIR,
    _build_audit_entry,
    _get_system_config_snapshot,
    export_trust_audit,
    reset_session_cache,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_session_cache():
    """Reset the in-memory dedup cache before every test."""
    reset_session_cache()
    yield
    reset_session_cache()


@pytest.fixture
def tmp_export_dir(tmp_path):
    """Redirect EXPORT_DIR to a temp dir for isolated tests."""
    original = EXPORT_DIR
    import alpha_engine.trust_audit_export as mod
    mod.EXPORT_DIR = tmp_path / "trust_audit_exports"
    yield mod.EXPORT_DIR
    mod.EXPORT_DIR = original


def _make_pick(
    pick_id: str = "BTCUSDT_LONG_1713620000",
    symbol: str = "BTCUSDT",
    strategy: str = "funding_rate_carry",
    direction: str = "LONG",
    trust_score: int = 8,
    trust_label: str = "EXCELLENT",
    strat_fwd_wr: float = 62.5,
    strat_fwd_trades: int = 14,
    regime: str = "BULL",
    entry_price: float = 64500.0,
    tp: float = 68000.0,
    sl: float = 63000.0,
    timestamp: str = "2026-04-20T14:28:00Z",
    asset_class: str = "CRYPTO",
) -> dict:
    """Build a minimal enriched pick dict for testing."""
    return {
        "id": pick_id,
        "symbol": symbol,
        "strategy": strategy,
        "direction": direction,
        "trust_score": trust_score,
        "trust_label": trust_label,
        "trust_breakdown": {
            "freshness": 2,
            "track_record": 3,
            "edge": 2,
            "regime_alignment": 1,
            "rr_quality": 0,
        },
        "strat_fwd_wr": strat_fwd_wr,
        "strat_fwd_trades": strat_fwd_trades,
        "regime_at_entry": regime,
        "entry_price": entry_price,
        "take_profit": tp,
        "stop_loss": sl,
        "timestamp": timestamp,
        "asset_class": asset_class,
    }


# ---------------------------------------------------------------------------
# Tests: _build_audit_entry
# ---------------------------------------------------------------------------

class TestBuildAuditEntry:
    def test_builds_entry_from_enriched_pick(self):
        pick = _make_pick()
        config = {"SMART_PICKS_CRYPTO_LONG_ONLY": False}
        ts = "2026-04-20T14:30:00+00:00"
        entry = _build_audit_entry(pick, config, ts)
        assert entry is not None
        assert entry["pick_id"] == "BTCUSDT_LONG_1713620000"
        assert entry["symbol"] == "BTCUSDT"
        assert entry["trust_score"] == 8
        assert entry["trust_label"] == "EXCELLENT"
        assert entry["raw_inputs"]["strat_fwd_wr"] == 62.5
        assert entry["raw_inputs"]["regime"] == "BULL"
        assert entry["config_snapshot"] == config

    def test_returns_none_for_unenriched_pick(self):
        pick = {"id": "TEST_1", "symbol": "ETHUSDT", "strategy": "test"}
        entry = _build_audit_entry(pick, {}, "2026-04-20T14:30:00+00:00")
        assert entry is None

    def test_returns_none_for_pick_without_id(self):
        pick = _make_pick()
        del pick["id"]
        entry = _build_audit_entry(pick, {}, "2026-04-20T14:30:00+00:00")
        assert entry is None

    def test_raw_inputs_captures_all_sources(self):
        pick = _make_pick()
        # Also set alternate field names
        pick["forward_wr"] = 55.0
        pick["forward_trades"] = 10
        pick["htf_bias"] = "BEAR"
        entry = _build_audit_entry(pick, {}, "2026-04-20T14:30:00+00:00")
        # strat_fwd_wr takes priority over forward_wr
        assert entry["raw_inputs"]["strat_fwd_wr"] == 62.5
        assert entry["raw_inputs"]["strat_fwd_trades"] == 14
        # regime_at_entry takes priority over htf_bias
        assert entry["raw_inputs"]["regime"] == "BULL"

    def test_raw_inputs_fallback_to_alternate_fields(self):
        pick = _make_pick()
        del pick["strat_fwd_wr"]
        del pick["regime_at_entry"]
        pick["forward_wr"] = 55.0
        pick["htf_bias"] = "BEAR"
        entry = _build_audit_entry(pick, {}, "2026-04-20T14:30:00+00:00")
        assert entry["raw_inputs"]["strat_fwd_wr"] == 55.0
        assert entry["raw_inputs"]["regime"] == "BEAR"

    def test_raw_inputs_from_extra_dict(self):
        pick = _make_pick()
        del pick["regime_at_entry"]
        pick["extra"] = {"fast_regime": "NEUTRAL"}
        entry = _build_audit_entry(pick, {}, "2026-04-20T14:30:00+00:00")
        assert entry["raw_inputs"]["regime"] == "NEUTRAL"

    def test_raw_inputs_from_extra_json_string(self):
        """extra field may be a JSON string, not a dict."""
        pick = _make_pick()
        del pick["regime_at_entry"]
        pick["extra"] = '{"fast_regime": "CAPITULATION"}'
        entry = _build_audit_entry(pick, {}, "2026-04-20T14:30:00+00:00")
        assert entry["raw_inputs"]["regime"] == "CAPITULATION"

    def test_direction_not_in_raw_inputs(self):
        """direction is at top level, not duplicated in raw_inputs."""
        pick = _make_pick()
        entry = _build_audit_entry(pick, {}, "2026-04-20T14:30:00+00:00")
        assert "direction" not in entry["raw_inputs"]
        assert entry["direction"] == "LONG"

    def test_trust_breakdown_captured(self):
        pick = _make_pick()
        entry = _build_audit_entry(pick, {}, "2026-04-20T14:30:00+00:00")
        assert entry["trust_breakdown"]["freshness"] == 2
        assert entry["trust_breakdown"]["track_record"] == 3
        assert entry["trust_breakdown"]["edge"] == 2
        assert entry["trust_breakdown"]["regime_alignment"] == 1
        assert entry["trust_breakdown"]["rr_quality"] == 0


# ---------------------------------------------------------------------------
# Tests: _get_system_config_snapshot
# ---------------------------------------------------------------------------

class TestSystemConfigSnapshot:
    def test_returns_dict_with_expected_keys(self):
        snap = _get_system_config_snapshot()
        assert "SMART_PICKS_CRYPTO_LONG_ONLY" in snap
        assert "TIER_MULTIPLIERS" in snap
        assert "ASSET_CLASS_TRUST_THRESHOLDS" in snap

    def test_snapshot_values_are_capturable(self):
        """Config may or may not be importable (depends on environment),
        but the function should not raise."""
        snap = _get_system_config_snapshot()
        # If importable, values should be set; otherwise None/{}
        assert isinstance(snap, dict)


# ---------------------------------------------------------------------------
# Tests: export_trust_audit
# ---------------------------------------------------------------------------

class TestExportTrustAudit:
    def test_exports_enriched_picks(self, tmp_export_dir):
        picks = [_make_pick(pick_id=f"TEST_{i}") for i in range(3)]
        count = export_trust_audit(picks, config_snapshot={"test": True})
        assert count == 3

        # Verify JSONL file was created
        files = list(tmp_export_dir.glob("trust_audit_*.jsonl"))
        assert len(files) == 1

        # Parse and verify contents
        lines = files[0].read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3
        for line in lines:
            entry = json.loads(line)
            assert entry["config_snapshot"] == {"test": True}
            assert "trust_score" in entry
            assert "raw_inputs" in entry

    def test_skips_unenriched_picks(self, tmp_export_dir):
        picks = [
            _make_pick(pick_id="ENRICHED_1"),
            {"id": "RAW_1", "symbol": "ETHUSDT"},  # no trust_score
        ]
        count = export_trust_audit(picks)
        assert count == 1

    def test_skips_picks_without_id(self, tmp_export_dir):
        picks = [_make_pick(pick_id=""), {"trust_score": 5}]  # no id
        count = export_trust_audit(picks)
        assert count == 0

    def test_dedup_within_session(self, tmp_export_dir):
        picks = [_make_pick(pick_id="DEDUP_1")]
        count1 = export_trust_audit(picks)
        assert count1 == 1
        # Second export of same picks should skip (already in session cache)
        count2 = export_trust_audit(picks)
        assert count2 == 0

    def test_dedup_resets_after_reset_session_cache(self, tmp_export_dir):
        picks = [_make_pick(pick_id="DEDUP_RESET_1")]
        assert export_trust_audit(picks) == 1
        reset_session_cache()
        # After reset, the pick is exportable again (but JSONL will have 2 lines)
        assert export_trust_audit(picks) == 1

    def test_empty_picks_list(self, tmp_export_dir):
        count = export_trust_audit([])
        assert count == 0

    def test_mixed_enriched_and_raw(self, tmp_export_dir):
        picks = [
            _make_pick(pick_id="MIX_1", trust_score=7),
            {"id": "MIX_RAW", "symbol": "SOLUSDT"},
            _make_pick(pick_id="MIX_2", trust_score=5),
        ]
        count = export_trust_audit(picks)
        assert count == 2

    def test_config_snapshot_auto_detected(self, tmp_export_dir):
        picks = [_make_pick(pick_id="CONFIG_AUTO_1")]
        # Pass no config_snapshot — should auto-detect
        count = export_trust_audit(picks, config_snapshot=None)
        assert count == 1

        # Verify the entry has config_snapshot with expected keys
        files = list(tmp_export_dir.glob("trust_audit_*.jsonl"))
        entry = json.loads(files[0].read_text(encoding="utf-8").strip())
        assert "SMART_PICKS_CRYPTO_LONG_ONLY" in entry["config_snapshot"]

    def test_export_timestamp_is_iso_format(self, tmp_export_dir):
        picks = [_make_pick(pick_id="TS_1")]
        export_trust_audit(picks)

        files = list(tmp_export_dir.glob("trust_audit_*.jsonl"))
        entry = json.loads(files[0].read_text(encoding="utf-8").strip())
        # Should be parseable as ISO datetime
        dt = datetime.fromisoformat(entry["export_timestamp"])
        assert dt.tzinfo is not None  # has timezone info

    def test_jsonl_file_naming_convention(self, tmp_export_dir):
        picks = [_make_pick(pick_id="NAME_1")]
        export_trust_audit(picks)

        files = list(tmp_export_dir.glob("trust_audit_*.jsonl"))
        assert len(files) == 1
        # Filename should be trust_audit_YYYY_MM_DD.jsonl
        name = files[0].name
        assert name.startswith("trust_audit_")
        assert name.endswith(".jsonl")
        # Date portion should be parseable
        date_part = name.replace("trust_audit_", "").replace(".jsonl", "")
        datetime.strptime(date_part, "%Y_%m_%d")


# ---------------------------------------------------------------------------
# Tests: Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_pick_with_pick_id_field(self, tmp_export_dir):
        """Some picks use 'pick_id' instead of 'id'."""
        pick = _make_pick()
        del pick["id"]
        pick["pick_id"] = "ALT_ID_1"
        entry = _build_audit_entry(pick, {}, "2026-04-20T14:30:00+00:00")
        assert entry is not None
        assert entry["pick_id"] == "ALT_ID_1"

    def test_pick_with_nan_values(self, tmp_export_dir):
        """NaN values should be handled by json.dumps default=str."""
        import math
        pick = _make_pick(pick_id="NAN_1")
        pick["strat_fwd_wr"] = float("nan")
        count = export_trust_audit([pick])
        assert count == 1  # should not crash

    def test_multiple_picks_same_id_only_exported_once(self, tmp_export_dir):
        """Duplicate pick_id in same list should only export once."""
        picks = [_make_pick(pick_id="DUP_SAME_1"), _make_pick(pick_id="DUP_SAME_1")]
        count = export_trust_audit(picks)
        assert count == 1

    def test_large_batch_export(self, tmp_export_dir):
        """Test exporting many picks at once."""
        picks = [_make_pick(pick_id=f"BATCH_{i}") for i in range(100)]
        count = export_trust_audit(picks)
        assert count == 100

        files = list(tmp_export_dir.glob("trust_audit_*.jsonl"))
        lines = files[0].read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 100
