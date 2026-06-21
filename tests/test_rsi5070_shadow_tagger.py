"""Unit tests for the rsi5070 shadow tagger (forward-measurement carve-out for the
designated honest lead crypto_rsi5070_us). Canonical predicate: CRYPTO ∧ LONG/BUY ∧
50<=RSI(14,1h)<=70 ∧ US session (13.5<=UTC hour<21). Env-gated, DEFAULT OFF."""
import os
import pytest
from audit_trail.quality_gates import _rsi5070_shadow_match, tag_rsi5070_shadow


# --- pure predicate -----------------------------------------------------------
def test_match_canonical():
    assert _rsi5070_shadow_match("CRYPTO", "LONG", 60.0, 15.0) is True
    assert _rsi5070_shadow_match("CRYPTO", "BUY", 50.0, 13.5) is True   # band + session edges
    assert _rsi5070_shadow_match("CRYPTO", "LONG", 70.0, 20.99) is True


def test_reject_non_crypto():
    assert _rsi5070_shadow_match("EQUITY", "LONG", 60.0, 15.0) is False


def test_reject_short():
    assert _rsi5070_shadow_match("CRYPTO", "SHORT", 60.0, 15.0) is False


def test_reject_rsi_out_of_band():
    assert _rsi5070_shadow_match("CRYPTO", "LONG", 49.9, 15.0) is False
    assert _rsi5070_shadow_match("CRYPTO", "LONG", 70.1, 15.0) is False


def test_reject_non_us_session():
    assert _rsi5070_shadow_match("CRYPTO", "LONG", 60.0, 13.49) is False  # EU
    assert _rsi5070_shadow_match("CRYPTO", "LONG", 60.0, 21.0) is False   # ASIA edge
    assert _rsi5070_shadow_match("CRYPTO", "LONG", 60.0, 3.0) is False    # ASIA


def test_predicate_never_raises_on_bad_input():
    assert _rsi5070_shadow_match("CRYPTO", "LONG", None, 15.0) is False
    assert _rsi5070_shadow_match(None, None, "x", "y") is False


# --- env gating (default OFF) -------------------------------------------------
def test_tagger_noop_when_disabled(monkeypatch):
    monkeypatch.delenv("CRYPTO_RSI5070_SHADOW_ENABLE", raising=False)
    pick = {"asset_class": "CRYPTO", "direction": "LONG", "rsi": 60.0}
    out = tag_rsi5070_shadow(pick)
    assert "forward_test_only" not in out and "_monitor_tag" not in out


def test_tagger_tags_when_enabled_and_matching(monkeypatch):
    monkeypatch.setenv("CRYPTO_RSI5070_SHADOW_ENABLE", "1")
    # force a US-session hour deterministically
    import audit_trail.quality_gates as qg
    monkeypatch.setattr(qg, "_rsi5070_shadow_match", lambda *a, **k: True)
    pick = {"asset_class": "CRYPTO", "direction": "LONG", "rsi": 60.0}
    out = tag_rsi5070_shadow(pick)
    assert out["forward_test_only"] is True
    assert out["_monitor_mode"] is True
    assert out["_monitor_tag"] == "RSI5070_SHADOW"
    assert out["_sizing_override"] == "zero"


def test_tagger_noop_when_enabled_but_not_matching(monkeypatch):
    monkeypatch.setenv("CRYPTO_RSI5070_SHADOW_ENABLE", "1")
    import audit_trail.quality_gates as qg
    monkeypatch.setattr(qg, "_rsi5070_shadow_match", lambda *a, **k: False)
    pick = {"asset_class": "EQUITY", "direction": "LONG", "rsi": 60.0}
    out = tag_rsi5070_shadow(pick)
    assert "forward_test_only" not in out
