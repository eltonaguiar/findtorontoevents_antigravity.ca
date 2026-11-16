"""Tests for alpha_engine.drawdown_circuit_breaker stale-state handling.

Regression: a stale (>2h) ACTIVE/CRITICAL breaker state must never be treated
as CLEAR. It must be recomputed from the live portfolio, and if recomputation
fails the check must fail safe (return True), not silently allow new entries.
"""
import json
from datetime import datetime, timedelta, timezone

import pytest

from alpha_engine import drawdown_circuit_breaker as dcb


def _write_state(tmp_path, level, age_hours):
    ts = (datetime.now(timezone.utc) - timedelta(hours=age_hours)).isoformat()
    state = {"level": level, "timestamp": ts}
    path = tmp_path / "drawdown_circuit_breaker.json"
    path.write_text(json.dumps(state), encoding="utf-8")
    return path


def test_missing_state_is_clear(tmp_path, monkeypatch):
    monkeypatch.setattr(dcb, "STATE_FILE", tmp_path / "nope.json")
    assert dcb.is_drawdown_breaker_active() is False


def test_fresh_active_state_blocks(tmp_path, monkeypatch):
    monkeypatch.setattr(dcb, "STATE_FILE", _write_state(tmp_path, "CIRCUIT_BREAKER_ACTIVE", 0.5))
    assert dcb.is_drawdown_breaker_active() is True


def test_stale_active_state_recomputes(tmp_path, monkeypatch):
    monkeypatch.setattr(dcb, "STATE_FILE", _write_state(tmp_path, "CIRCUIT_BREAKER_CRITICAL", 5))
    monkeypatch.setattr(dcb, "check_drawdown_breaker", lambda *a, **k: {"level": "CLEAR"})
    assert dcb.is_drawdown_breaker_active() is False


def test_stale_active_state_recompute_still_active(tmp_path, monkeypatch):
    monkeypatch.setattr(dcb, "STATE_FILE", _write_state(tmp_path, "CIRCUIT_BREAKER_ACTIVE", 5))
    monkeypatch.setattr(
        dcb, "check_drawdown_breaker", lambda *a, **k: {"level": "CIRCUIT_BREAKER_CRITICAL"}
    )
    assert dcb.is_drawdown_breaker_active() is True


def test_stale_active_state_recompute_failure_fails_safe(tmp_path, monkeypatch):
    monkeypatch.setattr(dcb, "STATE_FILE", _write_state(tmp_path, "CIRCUIT_BREAKER_ACTIVE", 5))

    def _boom(*a, **k):
        raise RuntimeError("portfolio unavailable")

    monkeypatch.setattr(dcb, "check_drawdown_breaker", _boom)
    assert dcb.is_drawdown_breaker_active() is True
