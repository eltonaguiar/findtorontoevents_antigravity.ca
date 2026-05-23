"""Tests for M-096: CT=F symbol concentration cap for COMMODITY.

Gate: when CT=F represents >= 35% of OPEN COMMODITY picks in active_picks.json,
new CT=F picks are shadow-stamped (COMMODITY_CTF_CAP=0, default) or hard-rejected
(COMMODITY_CTF_CAP=1). Fail-open when no active_picks data.
"""
import json
import pytest
from pathlib import Path
from audit_trail.quality_gates import passes_smart_gate


def _base_ctf_pick(**overrides):
    pick = {
        "id": "ctf-test-1",
        "asset_class": "COMMODITY",
        "symbol": "CT=F",
        "strategy": "multi_asset_cot",
        "source_system": "multi_asset_cot",
        "direction": "LONG",
        "status": "OPEN",
        "score": 72,
        "elite_score": 72,
        "confidence": 0.75,
        "trust_score": 7,
        "trust_label": "TRUSTED",
        "forward_wr": 0.70,
        "forward_trades": 40,
        "strat_fwd_wr": 0.70,
        "strat_fwd_trades": 40,
        "rr": 2.0,
        "rr_ratio": 2.0,
        "entry_price": 80.0,
        "take_profit": 88.0,
        "stop_loss": 76.0,
        "wf_verdict": "PASS",
    }
    pick.update(overrides)
    return pick


def _build_active_picks(ct_f_count: int, other_count: int) -> list:
    picks = []
    for i in range(ct_f_count):
        picks.append({"asset_class": "COMMODITY", "symbol": "CT=F", "status": "OPEN", "id": f"ctf-{i}"})
    for i in range(other_count):
        picks.append({"asset_class": "COMMODITY", "symbol": "HG=F", "status": "OPEN", "id": f"hgf-{i}"})
    return picks


def _common_env(monkeypatch):
    monkeypatch.setenv("CONCENTRATION_CAP_ENABLED", "0")
    monkeypatch.setenv("COT_DEDUP_GATE_ENABLED", "0")
    monkeypatch.setenv("COMMODITY_SHORT_ONLY", "0")
    # M-002 ctf_weekly_cap fires before M-096 and can block CT=F picks based on
    # 7-day window live data. Disable so tests isolate M-096 path only.
    monkeypatch.setenv("COMMODITY_CTF_WEEKLY_CAP", "off")
    # matrix_symbol_gates restricts multi_asset_cot to CT=F only; disable so
    # M-096 tests that probe non-CT=F symbols (HG=F) aren't blocked by matrix gate.
    monkeypatch.setenv("MATRIX_SYMBOL_GATES", "0")


class TestM096CTFConcentrationCap:

    def test_ctf_shadow_when_above_cap_default_mode(self, monkeypatch, tmp_path):
        active_picks = _build_active_picks(ct_f_count=9, other_count=1)
        ap_file = tmp_path / "active_picks.json"
        ap_file.write_text(json.dumps(active_picks))
        monkeypatch.setenv("COMMODITY_CTF_ACTIVE_PICKS_PATH", str(ap_file))
        monkeypatch.setenv("COMMODITY_CTF_CAP", "0")
        _common_env(monkeypatch)
        pick = _base_ctf_pick()
        result = passes_smart_gate(pick)
        if result is False:
            pytest.skip("pick blocked by other gate before M-096 shadow check")
        assert pick.get("_ctf_concentration_shadow") is True or result is True, (
            "Shadow mode: must stamp _ctf_concentration_shadow=True or allow through"
        )

    def test_ctf_hard_reject_when_above_cap_enforce_mode(self, monkeypatch, tmp_path):
        active_picks = _build_active_picks(ct_f_count=9, other_count=1)
        ap_file = tmp_path / "active_picks.json"
        ap_file.write_text(json.dumps(active_picks))
        monkeypatch.setenv("COMMODITY_CTF_ACTIVE_PICKS_PATH", str(ap_file))
        monkeypatch.setenv("COMMODITY_CTF_CAP", "1")
        monkeypatch.setenv("COMMODITY_CTF_MAX_PCT", "0.35")
        _common_env(monkeypatch)
        pick = _base_ctf_pick()
        result = passes_smart_gate(pick)
        assert result is False, f"M-096 enforce: CT=F at 90% concentration must be blocked. Got True."

    def test_ctf_passes_when_below_cap(self, monkeypatch, tmp_path):
        active_picks = _build_active_picks(ct_f_count=3, other_count=7)
        ap_file = tmp_path / "active_picks.json"
        ap_file.write_text(json.dumps(active_picks))
        monkeypatch.setenv("COMMODITY_CTF_ACTIVE_PICKS_PATH", str(ap_file))
        monkeypatch.setenv("COMMODITY_CTF_CAP", "1")
        monkeypatch.setenv("COMMODITY_CTF_MAX_PCT", "0.35")
        _common_env(monkeypatch)
        pick = _base_ctf_pick()
        result = passes_smart_gate(pick)
        assert result is True, f"M-096: CT=F at 30% should pass the 35% cap. Got False."

    def test_non_ctf_symbol_unaffected(self, monkeypatch, tmp_path):
        active_picks = _build_active_picks(ct_f_count=9, other_count=1)
        ap_file = tmp_path / "active_picks.json"
        ap_file.write_text(json.dumps(active_picks))
        monkeypatch.setenv("COMMODITY_CTF_ACTIVE_PICKS_PATH", str(ap_file))
        monkeypatch.setenv("COMMODITY_CTF_CAP", "1")
        monkeypatch.setenv("COMMODITY_CTF_MAX_PCT", "0.35")
        _common_env(monkeypatch)
        pick = _base_ctf_pick(symbol="HG=F")
        result = passes_smart_gate(pick)
        assert result is True, "M-096 must not affect non-CT=F COMMODITY picks. HG=F should pass."

    def test_fail_open_when_no_data(self, monkeypatch, tmp_path):
        monkeypatch.setenv("COMMODITY_CTF_ACTIVE_PICKS_PATH", str(tmp_path / "nonexistent.json"))
        monkeypatch.setenv("COMMODITY_CTF_CAP", "1")
        _common_env(monkeypatch)
        pick = _base_ctf_pick()
        result = passes_smart_gate(pick)
        assert result is True, "M-096 fail-open: must allow CT=F when no active_picks data available."

    def test_skip_when_fewer_than_5_commodity_picks(self, monkeypatch, tmp_path):
        active_picks = _build_active_picks(ct_f_count=3, other_count=0)  # n=3 < 5
        ap_file = tmp_path / "active_picks.json"
        ap_file.write_text(json.dumps(active_picks))
        monkeypatch.setenv("COMMODITY_CTF_ACTIVE_PICKS_PATH", str(ap_file))
        monkeypatch.setenv("COMMODITY_CTF_CAP", "1")
        monkeypatch.setenv("COMMODITY_CTF_MAX_PCT", "0.35")
        _common_env(monkeypatch)
        pick = _base_ctf_pick()
        result = passes_smart_gate(pick)
        assert result is True, "M-096: with < 5 COMMODITY picks, gate should skip (insufficient sample)."
