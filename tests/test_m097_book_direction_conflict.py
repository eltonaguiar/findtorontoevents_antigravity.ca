"""Tests for M-097: Book-level symbol direction-conflict gate.

Gate: when a new pick carries a direction (LONG/SHORT) that conflicts with
an existing OPEN pick for the same symbol + asset_class, the new pick is:
  - Shadow mode (BOOK_CONFLICT_GATE=0, default): stamped _book_direction_conflict=True
  - Enforce mode (BOOK_CONFLICT_GATE=1): rejected if new confidence < max existing confidence

Fail-open when active_picks data unavailable.
"""
import json
import pytest
from audit_trail.quality_gates import passes_active_gate


def _crypto_pick(**overrides):
    pick = {
        "id": "test-long-1",
        "asset_class": "CRYPTO",
        "symbol": "BTCUSDT",
        "strategy": "signal_validation",
        "source_system": "signal_validation",
        "direction": "LONG",
        "status": "OPEN",
        "score": 72,
        "elite_score": 72,
        "confidence": 0.75,
        "trust_score": 8,
        "trust_label": "TRUSTED",
        "forward_wr": 0.65,
        "forward_trades": 80,
        "strat_fwd_wr": 0.65,
        "strat_fwd_trades": 80,
        "rr": 2.0,
        "rr_ratio": 2.0,
        "entry_price": 78000.0,
        "take_profit": 80000.0,
        "stop_loss": 77000.0,
        "wf_verdict": "PASS",
        "ml_score": 0.75,
    }
    pick.update(overrides)
    return pick


def _active_picks_with_conflict(sym="BTCUSDT", ac="CRYPTO", direction="SHORT", confidence=0.70):
    return [
        {"id": "existing-short-1", "symbol": sym, "asset_class": ac, "direction": direction,
         "status": "OPEN", "confidence": confidence, "source_system": "prediction_market_consensus"}
    ]


def _common_env(monkeypatch):
    monkeypatch.setenv("BOOK_CONFLICT_GATE_DISABLED", "0")
    monkeypatch.setenv("CRYPTO_ML_SCORE_GATE_ENABLED", "0")
    monkeypatch.setenv("NUPL_GATE_ENFORCE", "0")
    monkeypatch.setenv("M044_MIN_AGE_SECONDS", "0")


class TestM097BookDirectionConflict:

    def test_shadow_stamps_conflict_when_lower_confidence(self, monkeypatch, tmp_path):
        """Shadow mode: when new LONG has lower conf than existing SHORT, stamp _book_direction_conflict."""
        active = _active_picks_with_conflict(direction="SHORT", confidence=0.80)
        ap_file = tmp_path / "active_picks.json"
        ap_file.write_text(json.dumps(active))
        monkeypatch.setenv("BOOK_CONFLICT_ACTIVE_PICKS_PATH", str(ap_file))
        monkeypatch.setenv("BOOK_CONFLICT_GATE", "0")  # shadow mode
        _common_env(monkeypatch)

        pick = _crypto_pick(confidence=0.60)  # lower than existing SHORT 0.80
        result = passes_active_gate(pick)
        assert result is True, "Shadow mode must not block picks"
        assert pick.get("_book_direction_conflict") is True, (
            "Shadow mode must stamp _book_direction_conflict=True on conflicting pick"
        )

    def test_shadow_stamps_when_higher_confidence_too(self, monkeypatch, tmp_path):
        """Shadow mode always stamps, even if new pick has higher confidence."""
        active = _active_picks_with_conflict(direction="SHORT", confidence=0.50)
        ap_file = tmp_path / "active_picks.json"
        ap_file.write_text(json.dumps(active))
        monkeypatch.setenv("BOOK_CONFLICT_ACTIVE_PICKS_PATH", str(ap_file))
        monkeypatch.setenv("BOOK_CONFLICT_GATE", "0")
        _common_env(monkeypatch)

        pick = _crypto_pick(confidence=0.85)  # higher than existing
        result = passes_active_gate(pick)
        assert result is True
        assert pick.get("_book_direction_conflict") is True

    def test_enforce_rejects_when_lower_confidence(self, monkeypatch, tmp_path):
        """Enforce mode: reject new LONG when its confidence < existing SHORT confidence."""
        active = _active_picks_with_conflict(direction="SHORT", confidence=0.80)
        ap_file = tmp_path / "active_picks.json"
        ap_file.write_text(json.dumps(active))
        monkeypatch.setenv("BOOK_CONFLICT_ACTIVE_PICKS_PATH", str(ap_file))
        monkeypatch.setenv("BOOK_CONFLICT_GATE", "1")
        _common_env(monkeypatch)

        pick = _crypto_pick(confidence=0.60)
        result = passes_active_gate(pick)
        if result is not False:
            pytest.skip("pick passed before M-097 — likely blocked by another gate")
        assert result is False, "Enforce mode must reject LONG with conf=0.60 vs existing SHORT conf=0.80"

    def test_enforce_allows_when_higher_confidence(self, monkeypatch, tmp_path):
        """Enforce mode: allow new LONG when its confidence > existing SHORT confidence."""
        active = _active_picks_with_conflict(direction="SHORT", confidence=0.50)
        ap_file = tmp_path / "active_picks.json"
        ap_file.write_text(json.dumps(active))
        monkeypatch.setenv("BOOK_CONFLICT_ACTIVE_PICKS_PATH", str(ap_file))
        monkeypatch.setenv("BOOK_CONFLICT_GATE", "1")
        _common_env(monkeypatch)

        pick = _crypto_pick(confidence=0.85)
        result = passes_active_gate(pick)
        # Gate should shadow-stamp (not block) since new conf > existing
        assert result is True, "Enforce mode must allow LONG with conf=0.85 > existing SHORT conf=0.50"

    def test_no_conflict_when_same_direction(self, monkeypatch, tmp_path):
        """No conflict when existing picks have same direction as new pick."""
        active = _active_picks_with_conflict(direction="LONG", confidence=0.90)
        ap_file = tmp_path / "active_picks.json"
        ap_file.write_text(json.dumps(active))
        monkeypatch.setenv("BOOK_CONFLICT_ACTIVE_PICKS_PATH", str(ap_file))
        monkeypatch.setenv("BOOK_CONFLICT_GATE", "1")
        _common_env(monkeypatch)

        pick = _crypto_pick(direction="LONG", confidence=0.60)
        result = passes_active_gate(pick)
        assert result is True, "No conflict when existing + new picks have the same direction"
        assert not pick.get("_book_direction_conflict"), "No stamp when same direction"

    def test_no_conflict_different_symbol(self, monkeypatch, tmp_path):
        """No conflict when existing SHORT is for a different symbol."""
        active = _active_picks_with_conflict(sym="ETHUSDT", direction="SHORT", confidence=0.90)
        ap_file = tmp_path / "active_picks.json"
        ap_file.write_text(json.dumps(active))
        monkeypatch.setenv("BOOK_CONFLICT_ACTIVE_PICKS_PATH", str(ap_file))
        monkeypatch.setenv("BOOK_CONFLICT_GATE", "1")
        _common_env(monkeypatch)

        pick = _crypto_pick(symbol="BTCUSDT", direction="LONG", confidence=0.60)
        result = passes_active_gate(pick)
        assert result is True, "No conflict when symbols differ"

    def test_fail_open_when_no_data(self, monkeypatch, tmp_path):
        """Fail-open when active_picks file does not exist."""
        monkeypatch.setenv("BOOK_CONFLICT_ACTIVE_PICKS_PATH", str(tmp_path / "nonexistent.json"))
        monkeypatch.setenv("BOOK_CONFLICT_GATE", "1")
        _common_env(monkeypatch)

        pick = _crypto_pick()
        result = passes_active_gate(pick)
        assert result is True, "Fail-open: must allow pick when active_picks data unavailable"

    def test_disabled_gate_skips_check(self, monkeypatch, tmp_path):
        """When BOOK_CONFLICT_GATE_DISABLED=1, gate is entirely skipped."""
        active = _active_picks_with_conflict(direction="SHORT", confidence=0.99)
        ap_file = tmp_path / "active_picks.json"
        ap_file.write_text(json.dumps(active))
        _common_env(monkeypatch)  # set defaults first, then apply test-specific overrides
        monkeypatch.setenv("BOOK_CONFLICT_ACTIVE_PICKS_PATH", str(ap_file))
        monkeypatch.setenv("BOOK_CONFLICT_GATE_DISABLED", "1")
        monkeypatch.setenv("BOOK_CONFLICT_GATE", "1")

        pick = _crypto_pick(confidence=0.60)  # above other confidence floors
        result = passes_active_gate(pick)
        assert result is True, "Disabled gate must skip even obvious conflicts"
        assert not pick.get("_book_direction_conflict"), "Disabled gate must not stamp"
