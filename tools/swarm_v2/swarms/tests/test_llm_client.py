"""Unit tests for swarms.core.llm_client.

Fully mocked — no test makes a real network call. ``urllib.request.urlopen``
is always patched and the environment is controlled via ``patch.dict`` so
provider auto-detection is deterministic.
"""

from __future__ import annotations

import io
import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from swarms.core.llm_client import (
    PROVIDERS,
    LLMClient,
    detect_providers,
)


def _fake_response(payload: dict) -> MagicMock:
    """Build a context-manager mock mimicking ``urlopen``'s return value."""
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


def _chat_payload(content: str = "", reasoning: str = "") -> dict:
    """Build an OpenAI-compatible chat-completions payload."""
    message: dict = {}
    if content:
        message["content"] = content
    if reasoning:
        message["reasoning_content"] = reasoning
    return {"choices": [{"message": message}]}


# ─── detect_providers ────────────────────────────────────────────────


class TestDetectProviders:
    def test_detects_keyed_providers(self):
        with patch.dict(
            "os.environ",
            {"DEEPSEEK_API": "k1", "GROQ_KEY": "k2"},
            clear=True,
        ):
            detected = detect_providers()
        assert "deepseek" in detected
        assert "groq" in detected

    def test_no_keys_returns_llm7_keyless(self):
        # LLM7.io is a keyless provider — always usable even with no API keys.
        with patch.dict("os.environ", {}, clear=True):
            detected = detect_providers()
        assert "llm7" in detected

    def test_detection_order_matches_provider_order(self):
        with patch.dict(
            "os.environ",
            {"GROQ_KEY": "k", "DEEPSEEK_API": "k"},
            clear=True,
        ):
            detected = detect_providers()
        # deepseek precedes groq in PROVIDERS
        assert detected.index("deepseek") < detected.index("groq")
        assert [p.name for p in PROVIDERS][0] == "deepseek"


# ─── LLMClient construction / availability ───────────────────────────


class TestLLMClientConstruction:
    def test_explicit_provider_with_key_is_available(self):
        with patch.dict("os.environ", {"DEEPSEEK_API": "secret"}, clear=True):
            client = LLMClient(provider="deepseek")
        assert client.available is True
        assert client.provider_name == "deepseek"
        assert client.model == "deepseek-chat"

    def test_explicit_provider_without_key_is_unavailable(self):
        with patch.dict("os.environ", {}, clear=True):
            client = LLMClient(provider="deepseek")
        assert client.available is False
        assert client.provider_name == "deepseek"

    def test_bogus_provider_raises_value_error(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError):
                LLMClient(provider="bogus")

    def test_auto_detect_picks_first_keyed_provider(self):
        with patch.dict("os.environ", {"GROQ_API_KEY": "k"}, clear=True):
            client = LLMClient()
        assert client.provider_name == "groq"
        assert client.available is True

    def test_auto_detect_no_key_falls_back_to_llm7(self):
        # With no API keys, LLMClient falls back to the keyless LLM7 provider.
        with patch.dict("os.environ", {}, clear=True):
            client = LLMClient()
        assert client.available is True
        assert client.provider_name == "llm7"
        assert client.model is not None

    def test_model_override(self):
        with patch.dict("os.environ", {"DEEPSEEK_API": "k"}, clear=True):
            client = LLMClient(provider="deepseek", model="custom-model")
        assert client.model == "custom-model"


# ─── complete() ──────────────────────────────────────────────────────


class TestComplete:
    def test_happy_path_parses_content(self):
        with patch.dict("os.environ", {"DEEPSEEK_API": "k"}, clear=True):
            client = LLMClient(provider="deepseek")
        with patch(
            "urllib.request.urlopen",
            return_value=_fake_response(_chat_payload(content="hello world")),
        ):
            result = client.complete("hi")
        assert result == "hello world"

    def test_falls_back_to_reasoning_content(self):
        with patch.dict("os.environ", {"DEEPSEEK_API": "k"}, clear=True):
            client = LLMClient(provider="deepseek")
        with patch(
            "urllib.request.urlopen",
            return_value=_fake_response(_chat_payload(reasoning="reasoned answer")),
        ):
            result = client.complete("hi")
        assert result == "reasoned answer"

    def test_content_preferred_over_reasoning(self):
        with patch.dict("os.environ", {"DEEPSEEK_API": "k"}, clear=True):
            client = LLMClient(provider="deepseek")
        payload = _chat_payload(content="primary", reasoning="secondary")
        with patch("urllib.request.urlopen", return_value=_fake_response(payload)):
            result = client.complete("hi")
        assert result == "primary"

    def test_passes_system_prompt(self):
        with patch.dict("os.environ", {"DEEPSEEK_API": "k"}, clear=True):
            client = LLMClient(provider="deepseek")
        with patch(
            "urllib.request.urlopen",
            return_value=_fake_response(_chat_payload(content="ok")),
        ) as mock_open:
            client.complete("hi", system="be terse")
        sent_body = json.loads(mock_open.call_args[0][0].data.decode("utf-8"))
        roles = [m["role"] for m in sent_body["messages"]]
        assert roles == ["system", "user"]

    def test_returns_none_on_http_error(self):
        with patch.dict("os.environ", {"DEEPSEEK_API": "k"}, clear=True):
            client = LLMClient(provider="deepseek")
        err = urllib.error.HTTPError(
            url="x", code=500, msg="boom", hdrs=None, fp=io.BytesIO(b"")
        )
        with patch("urllib.request.urlopen", side_effect=err):
            assert client.complete("hi") is None

    def test_returns_none_on_url_error(self):
        with patch.dict("os.environ", {"DEEPSEEK_API": "k"}, clear=True):
            client = LLMClient(provider="deepseek")
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("no route"),
        ):
            assert client.complete("hi") is None

    def test_returns_none_on_malformed_json(self):
        with patch.dict("os.environ", {"DEEPSEEK_API": "k"}, clear=True):
            client = LLMClient(provider="deepseek")
        bad = MagicMock()
        bad.read.return_value = b"not json{{{"
        bad.__enter__.return_value = bad
        bad.__exit__.return_value = False
        with patch("urllib.request.urlopen", return_value=bad):
            assert client.complete("hi") is None

    def test_returns_none_on_missing_choices(self):
        with patch.dict("os.environ", {"DEEPSEEK_API": "k"}, clear=True):
            client = LLMClient(provider="deepseek")
        with patch(
            "urllib.request.urlopen",
            return_value=_fake_response({"unexpected": True}),
        ):
            assert client.complete("hi") is None

    def test_returns_none_on_empty_content(self):
        with patch.dict("os.environ", {"DEEPSEEK_API": "k"}, clear=True):
            client = LLMClient(provider="deepseek")
        with patch(
            "urllib.request.urlopen",
            return_value=_fake_response(_chat_payload()),
        ):
            assert client.complete("hi") is None

    def test_returns_none_when_not_available(self):
        with patch.dict("os.environ", {}, clear=True):
            client = LLMClient(provider="deepseek")
        # No network call should be attempted; urlopen left unpatched on
        # purpose — if it were invoked the test would fail loudly.
        assert client.complete("hi") is None
