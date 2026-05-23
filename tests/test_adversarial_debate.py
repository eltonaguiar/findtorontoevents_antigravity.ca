"""Tests for alpha_engine/adversarial_debate.py (sidecar, default-off).

No live LLM calls — all tests inject a stub `http_post` callable that returns
canned OpenAI-compatible responses. Tests verify:
  1. Default-OFF behavior: apply_to_picks is a no-op without the env flag.
  2. Env-var resolver respects standard names + legacy fallbacks.
  3. JSON parser tolerates code fences, prose wrappers, and bad confidence.
  4. score_pick returns a dict even when one provider raises.
  5. apply_to_picks does not propagate exceptions into the host.
"""
from __future__ import annotations

import json
import os

import pytest

from alpha_engine import adversarial_debate as ad


def _make_oai_response(text: str) -> dict:
    return {"choices": [{"message": {"content": text}}]}


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    """Each test starts with relevant env flags cleared."""
    for k in (
        ad.ENV_FLAG,
        "DEEPSEEK_API_KEY", "DEEPSEEK_API",
        "XAI_API_KEY", "X_AI_KEY", "GROK_SUPER", "X_AI_SECONDOP",
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY",
        "CEREBRAS_API_KEY", "CEREBRAS_API",
        "MOONSHOT_API_KEY", "KIMI_API_KEY",
        "OLLAMA_CLOUD_KEY",
        "UEPS_ADVERSARIAL_BULL_PROVIDER",
        "UEPS_ADVERSARIAL_BEAR_PROVIDER",
        "UEPS_ADVERSARIAL_KEEP_MARGIN",
    ):
        monkeypatch.delenv(k, raising=False)
    yield


# ────────────────────────────────────────────────────────────────────────
# Default-OFF safety
# ────────────────────────────────────────────────────────────────────────

def test_apply_is_noop_when_flag_off():
    picks = [{"symbol": "AAPL", "asset_class": "EQUITY"}]

    def stub_post(*_args, **_kwargs):
        raise AssertionError("http_post should NOT be called when flag is off")

    out = ad.apply_to_picks(picks, http_post=stub_post)
    assert out == picks
    assert "adversarial_score" not in picks[0]


def test_is_enabled_recognizes_canonical_truthy(monkeypatch):
    for val, expected in (("1", True), ("0", False), ("true", True),
                          ("YES", True), ("on", True), ("anything-else", False)):
        monkeypatch.setenv(ad.ENV_FLAG, val)
        assert ad.is_enabled() is expected, f"{val!r} -> {expected}"


# ────────────────────────────────────────────────────────────────────────
# Env-var resolver: standard + legacy fallback
# ────────────────────────────────────────────────────────────────────────

def test_resolver_prefers_standard_env(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "standard-key")
    monkeypatch.setenv("DEEPSEEK_API", "legacy-key")
    provider = ad._PROVIDERS["deepseek"]
    assert ad._resolve_api_key(provider) == "standard-key"


def test_resolver_falls_back_to_legacy(monkeypatch):
    monkeypatch.setenv("X_AI_KEY", "legacy-grok-key")
    provider = ad._PROVIDERS["xai"]
    assert ad._resolve_api_key(provider) == "legacy-grok-key"


def test_resolver_returns_none_when_no_key():
    provider = ad._PROVIDERS["openai"]
    assert ad._resolve_api_key(provider) is None


def test_post_chat_raises_when_no_key():
    with pytest.raises(ad.DebateError, match="no API key"):
        ad._post_chat("openai", "sys", "user")


# ────────────────────────────────────────────────────────────────────────
# JSON tolerant parser
# ────────────────────────────────────────────────────────────────────────

def test_parse_clean_json():
    text = '{"thesis": "Strong moat", "confidence": 0.8}'
    thesis, conf = ad._parse_thesis_json(text)
    assert thesis == "Strong moat"
    assert conf == 0.8


def test_parse_json_with_markdown_fence():
    text = "Here you go:\n```json\n{\"thesis\": \"OK\", \"confidence\": 0.5}\n```"
    thesis, conf = ad._parse_thesis_json(text)
    assert thesis == "OK"
    assert conf == 0.5


def test_parse_clamps_confidence_out_of_range():
    text = '{"thesis": "x", "confidence": 1.7}'
    _, conf = ad._parse_thesis_json(text)
    assert conf == 1.0
    text = '{"thesis": "x", "confidence": -0.4}'
    _, conf = ad._parse_thesis_json(text)
    assert conf == 0.0


def test_parse_handles_non_numeric_confidence():
    text = '{"thesis": "x", "confidence": "high"}'
    thesis, conf = ad._parse_thesis_json(text)
    assert thesis == "x"
    assert conf == 0.0


def test_parse_falls_through_on_garbage():
    thesis, conf = ad._parse_thesis_json("totally not json")
    assert thesis == "totally not json"
    assert conf == 0.0


# ────────────────────────────────────────────────────────────────────────
# score_pick: end-to-end with stubbed transport
# ────────────────────────────────────────────────────────────────────────

def test_score_pick_keeps_when_bull_dominates(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")
    monkeypatch.setenv("XAI_API_KEY", "k")

    def stub(url, headers, body):
        b = json.loads(body)
        sys_msg = b["messages"][0]["content"]
        if "BULL case" in sys_msg:
            return _make_oai_response('{"thesis":"Catalyst-driven", "confidence":0.85}')
        if "BEAR case" in sys_msg:
            return _make_oai_response('{"thesis":"Some risk", "confidence":0.40}')
        raise AssertionError(f"unexpected sys: {sys_msg!r}")

    out = ad.score_pick({"symbol": "MSFT"}, http_post=stub)
    assert out["bull_confidence"] == 0.85
    assert out["bear_confidence"] == 0.40
    assert out["adversarial_score"] == pytest.approx(0.45, abs=1e-9)
    assert out["adversarial_keep"] is True


def test_score_pick_drops_when_bear_dominates(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")
    monkeypatch.setenv("XAI_API_KEY", "k")

    def stub(url, headers, body):
        sys_msg = json.loads(body)["messages"][0]["content"]
        if "BULL case" in sys_msg:
            return _make_oai_response('{"thesis":"x","confidence":0.30}')
        return _make_oai_response('{"thesis":"y","confidence":0.80}')

    out = ad.score_pick({"symbol": "AMD"}, http_post=stub)
    assert out["adversarial_score"] == pytest.approx(-0.5, abs=1e-9)
    assert out["adversarial_keep"] is False


def test_score_pick_drops_at_keep_margin_boundary(monkeypatch):
    """Margin exactly equal to KEEP_MARGIN is a KEEP (>=); just under it is a drop."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")
    monkeypatch.setenv("XAI_API_KEY", "k")

    def stub_at_margin(url, headers, body):
        sys_msg = json.loads(body)["messages"][0]["content"]
        if "BULL case" in sys_msg:
            return _make_oai_response('{"thesis":"x","confidence":0.65}')
        return _make_oai_response('{"thesis":"y","confidence":0.50}')  # margin = 0.15

    out = ad.score_pick({"symbol": "X"}, http_post=stub_at_margin)
    assert out["adversarial_keep"] is True

    def stub_below_margin(url, headers, body):
        sys_msg = json.loads(body)["messages"][0]["content"]
        if "BULL case" in sys_msg:
            return _make_oai_response('{"thesis":"x","confidence":0.64}')
        return _make_oai_response('{"thesis":"y","confidence":0.50}')  # margin = 0.14

    out = ad.score_pick({"symbol": "Y"}, http_post=stub_below_margin)
    assert out["adversarial_keep"] is False


def test_score_pick_records_error_when_one_side_fails(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")
    # No XAI key => bear side raises DebateError

    def stub(url, headers, body):
        return _make_oai_response('{"thesis":"x","confidence":0.7}')

    out = ad.score_pick({"symbol": "Z"}, http_post=stub)
    assert out["bull_confidence"] == 0.7
    assert out["bear_confidence"] == 0.0
    assert "_error_bear" in out
    assert "no API key" in out["_error_bear"]
    # bear=0 means margin = 0.7 — passes default keep_margin
    assert out["adversarial_keep"] is False  # bear didn't actually answer (>=0 check)


def test_apply_to_picks_swallows_unexpected_exception(monkeypatch):
    """Sidecar must never break the host pipeline."""
    monkeypatch.setenv(ad.ENV_FLAG, "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")
    monkeypatch.setenv("XAI_API_KEY", "k")

    def boom(*_a, **_kw):
        raise RuntimeError("transport melted")

    picks = [{"symbol": "AAPL"}, {"symbol": "MSFT"}]
    out = ad.apply_to_picks(picks, http_post=boom)
    assert len(out) == 2
    # Picks remain in the list (sidecar did not crash); fields not set because
    # score_pick's inner try/except logged and returned a default block.
    assert out is picks  # mutation in place


def test_apply_to_picks_stamps_fields_when_enabled(monkeypatch):
    monkeypatch.setenv(ad.ENV_FLAG, "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")
    monkeypatch.setenv("XAI_API_KEY", "k")

    def stub(url, headers, body):
        sys_msg = json.loads(body)["messages"][0]["content"]
        if "BULL case" in sys_msg:
            return _make_oai_response('{"thesis":"bull","confidence":0.7}')
        return _make_oai_response('{"thesis":"bear","confidence":0.4}')

    picks = [{"symbol": "AAPL", "asset_class": "EQUITY"}]
    ad.apply_to_picks(picks, http_post=stub)
    p = picks[0]
    assert p["bull_thesis"] == "bull"
    assert p["bear_thesis"] == "bear"
    assert p["adversarial_score"] == pytest.approx(0.3, abs=1e-9)
    assert p["adversarial_keep"] is True


# ────────────────────────────────────────────────────────────────────────
# Provider request shape
# ────────────────────────────────────────────────────────────────────────

def test_post_chat_uses_standard_oai_shape(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "the-key")
    captured = {}

    def stub(url, headers, body):
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = json.loads(body)
        return _make_oai_response('{"thesis":"x","confidence":0.5}')

    ad._post_chat("deepseek", "sys", "user", http_post=stub)
    assert captured["url"].endswith("/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer the-key"
    assert captured["headers"]["Content-Type"] == "application/json"
    assert captured["body"]["model"] == ad._PROVIDERS["deepseek"].default_model
    assert len(captured["body"]["messages"]) == 2
    assert captured["body"]["messages"][0]["role"] == "system"
    assert captured["body"]["messages"][1]["role"] == "user"
    assert "max_tokens" in captured["body"]


def test_post_chat_unknown_provider_raises():
    with pytest.raises(ad.DebateError, match="unknown provider"):
        ad._post_chat("not-a-provider", "x", "y")
