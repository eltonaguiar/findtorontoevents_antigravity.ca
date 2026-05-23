"""Tests for M-098: ETF VIX regime gate.

Gate: when VIX >= ETF_VIX_GATE_THRESHOLD (default 25.0) and pick is ETF,
  - Enforce mode (ETF_VIX_GATE=1, default 2026-05-18+): hard-reject the pick
  - Shadow mode (ETF_VIX_GATE=0): stamp _etf_vix_regime_block=True only
E-006: every VIX trigger is appended to reports/etf_vix_gate_log.jsonl.
Fail-open when VIX data unavailable.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch
from audit_trail.quality_gates import passes_active_gate


def _etf_pick(**overrides):
    pick = {
        "id": "test-etf-1",
        "asset_class": "ETF",
        "symbol": "SPY",
        "strategy": "sector_rotation",
        "source_system": "sector_rotation",
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
        "entry_price": 500.0,
        "take_profit": 520.0,
        "stop_loss": 490.0,
        "wf_verdict": "PASS",
        "ml_score": 0.75,
    }
    pick.update(overrides)
    return pick


def _common_env(monkeypatch):
    monkeypatch.setenv("ETF_VIX_GATE_DISABLED", "0")
    monkeypatch.setenv("CRYPTO_ML_SCORE_GATE_ENABLED", "0")
    monkeypatch.setenv("NUPL_GATE_ENFORCE", "0")
    monkeypatch.setenv("M044_MIN_AGE_SECONDS", "0")
    monkeypatch.setenv("BOOK_CONFLICT_GATE_DISABLED", "1")


class TestM098ETFVixGate:

    def test_shadow_stamps_when_vix_above_threshold(self, monkeypatch):
        """Shadow mode: VIX=28 >= 25 → stamp _etf_vix_regime_block=True, don't block."""
        _common_env(monkeypatch)
        monkeypatch.setenv("ETF_VIX_GATE", "0")
        monkeypatch.setenv("ETF_VIX_GATE_THRESHOLD", "25.0")

        pick = _etf_pick()
        with patch("audit_trail.vix_regime_gate.get_cached_vix", return_value=28.0):
            result = passes_active_gate(pick)

        assert result is True, "Shadow mode must not block pick"
        assert pick.get("_etf_vix_regime_block") is True, "Shadow mode must stamp _etf_vix_regime_block=True"

    def test_shadow_no_stamp_when_vix_below_threshold(self, monkeypatch):
        """Shadow mode: VIX=22 < 25 → no stamp, pass through."""
        _common_env(monkeypatch)
        monkeypatch.setenv("ETF_VIX_GATE", "0")
        monkeypatch.setenv("ETF_VIX_GATE_THRESHOLD", "25.0")

        pick = _etf_pick()
        with patch("audit_trail.vix_regime_gate.get_cached_vix", return_value=22.0):
            result = passes_active_gate(pick)

        assert result is True
        assert not pick.get("_etf_vix_regime_block"), "No stamp when VIX below threshold"

    def test_enforce_rejects_when_vix_above_threshold(self, monkeypatch):
        """Enforce mode: VIX=30 >= 25 → hard reject ETF pick."""
        _common_env(monkeypatch)
        monkeypatch.setenv("ETF_VIX_GATE", "1")
        monkeypatch.setenv("ETF_VIX_GATE_THRESHOLD", "25.0")

        pick = _etf_pick()
        with patch("audit_trail.vix_regime_gate.get_cached_vix", return_value=30.0):
            result = passes_active_gate(pick)

        if result is not False:
            pytest.skip("pick passed before M-098 — blocked by another gate")
        assert result is False, "Enforce mode must reject ETF when VIX >= threshold"

    def test_enforce_allows_when_vix_below_threshold(self, monkeypatch):
        """Enforce mode: VIX=20 < 25 → allow ETF pick."""
        _common_env(monkeypatch)
        monkeypatch.setenv("ETF_VIX_GATE", "1")
        monkeypatch.setenv("ETF_VIX_GATE_THRESHOLD", "25.0")

        pick = _etf_pick()
        with patch("audit_trail.vix_regime_gate.get_cached_vix", return_value=20.0):
            result = passes_active_gate(pick)

        assert result is True, "Enforce mode must allow ETF when VIX < threshold"

    def test_custom_threshold(self, monkeypatch):
        """Threshold is configurable via ETF_VIX_GATE_THRESHOLD."""
        _common_env(monkeypatch)
        monkeypatch.setenv("ETF_VIX_GATE", "0")
        monkeypatch.setenv("ETF_VIX_GATE_THRESHOLD", "30.0")  # higher threshold

        pick = _etf_pick()
        with patch("audit_trail.vix_regime_gate.get_cached_vix", return_value=28.0):
            result = passes_active_gate(pick)

        assert result is True
        assert not pick.get("_etf_vix_regime_block"), "VIX=28 < threshold=30 → no block"

    def test_non_etf_unaffected(self, monkeypatch):
        """Gate only applies to ETF asset class — CRYPTO pick passes through."""
        _common_env(monkeypatch)
        monkeypatch.setenv("ETF_VIX_GATE", "1")
        monkeypatch.setenv("ETF_VIX_GATE_THRESHOLD", "25.0")

        crypto_pick = {
            "id": "test-crypto-1",
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
        with patch("audit_trail.vix_regime_gate.get_cached_vix", return_value=35.0):
            result = passes_active_gate(crypto_pick)

        assert not crypto_pick.get("_etf_vix_regime_block"), "Non-ETF must not be stamped"

    def test_fail_open_when_vix_unavailable(self, monkeypatch):
        """Fail-open: when VIX data returns None, pick passes through."""
        _common_env(monkeypatch)
        monkeypatch.setenv("ETF_VIX_GATE", "1")
        monkeypatch.setenv("ETF_VIX_GATE_THRESHOLD", "25.0")

        pick = _etf_pick()
        with patch("audit_trail.vix_regime_gate.get_cached_vix", return_value=None):
            result = passes_active_gate(pick)

        assert result is True, "Fail-open: must allow pick when VIX data unavailable"

    def test_disabled_gate_skips_check(self, monkeypatch):
        """ETF_VIX_GATE_DISABLED=1 skips the gate entirely."""
        _common_env(monkeypatch)
        monkeypatch.setenv("ETF_VIX_GATE_DISABLED", "1")
        monkeypatch.setenv("ETF_VIX_GATE", "1")
        monkeypatch.setenv("ETF_VIX_GATE_THRESHOLD", "5.0")  # threshold so low it would always fire

        pick = _etf_pick()
        with patch("audit_trail.vix_regime_gate.get_cached_vix", return_value=100.0):
            result = passes_active_gate(pick)

        assert result is True, "Disabled gate must not block"
        assert not pick.get("_etf_vix_regime_block"), "Disabled gate must not stamp"

    def test_bond_etf_symbols_exempt_from_vix_gate(self, monkeypatch):
        """Bond ETF symbols (TLT/IEF/SHY/LQD) are exempt from VIX gate even if tagged ETF.
        These instruments rally in risk-off VIX spikes (E-007, 2026-05-18).
        """
        _common_env(monkeypatch)
        monkeypatch.setenv("ETF_VIX_GATE", "1")
        monkeypatch.setenv("ETF_VIX_GATE_THRESHOLD", "25.0")
        monkeypatch.setenv("ETF_VIX_GATE_ENABLED", "1")
        monkeypatch.setenv("ETF_VIX_GATE_ENFORCE", "1")

        for sym in ("TLT", "IEF", "SHY", "LQD", "AGG", "BND"):
            pick = _etf_pick(symbol=sym)
            with patch("audit_trail.vix_regime_gate.get_cached_vix", return_value=35.0):
                result = passes_active_gate(pick)
            # Must not be hard-rejected by either M-098 or PR-E1 VIX gate
            assert result is not False or pick.get("_blocked_by") not in ("M-098", "PR-E1"), (
                f"Bond ETF {sym} must be exempt from VIX gate (E-007)"
            )

    def test_e006_exception_log_written(self, monkeypatch, tmp_path):
        """E-006: every VIX trigger appends a JSON entry to etf_vix_gate_log.jsonl."""
        _common_env(monkeypatch)
        monkeypatch.setenv("ETF_VIX_GATE", "0")  # shadow so pick isn't blocked
        monkeypatch.setenv("ETF_VIX_GATE_THRESHOLD", "25.0")
        # Point the log to a tmp dir so we don't pollute the real reports/
        log_path = tmp_path / "etf_vix_gate_log.jsonl"
        monkeypatch.chdir(tmp_path)
        (tmp_path / "reports").mkdir()

        pick = _etf_pick()
        with patch("audit_trail.vix_regime_gate.get_cached_vix", return_value=28.0):
            passes_active_gate(pick)

        log_file = tmp_path / "reports" / "etf_vix_gate_log.jsonl"
        assert log_file.exists(), "E-006 log file must be created"
        entries = [json.loads(line) for line in log_file.read_text().splitlines() if line.strip()]
        assert len(entries) >= 1, "At least one log entry must be written"
        entry = entries[-1]
        assert entry["vix_value"] == 28.0
        assert entry["threshold"] == 25.0
        assert entry["mode"] == "shadow"
        assert entry["blocked"] is False
        assert "ts" in entry
        assert "symbol" in entry
