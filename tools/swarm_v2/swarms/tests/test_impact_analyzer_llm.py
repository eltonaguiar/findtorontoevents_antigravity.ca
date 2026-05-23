"""Tests for the LLM wiring of :class:`ImpactAnalyzerWorker`.

All tests are hermetic — the :class:`LLMClient` is always a :class:`MagicMock`,
so no real network call is ever made.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from swarms.core.models import AgentConfig, AgentRole
from swarms.workers.impact_analyzer import (
    ImpactAnalyzerWorker,
    _extract_json_object,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config() -> AgentConfig:
    """A baseline agent config."""
    return AgentConfig(role=AgentRole.IMPACT_ANALYZER, model="gpt-4o")


@pytest.fixture
def bus() -> MagicMock:
    """A mock message bus with an async ``broadcast``."""
    b = MagicMock()
    b.broadcast = AsyncMock()
    return b


@pytest.fixture
def pr_data() -> dict:
    """A representative PR payload."""
    return {
        "pr_number": 42,
        "title": "Refactor auth module",
        "files_changed": [
            {
                "filename": "auth/login.py",
                "status": "modified",
                "patch": "def login(user):",
                "additions": 10,
                "deletions": 3,
            }
        ],
    }


def _canned_impact_json() -> str:
    """Return a well-formed JSON-object LLM impact response."""
    impact = {
        "affected_files": ["auth/login.py"],
        "affected_modules": ["auth"],
        "breaking_changes": ["login() signature changed"],
        "risk_score": 65.0,
        "risk_level": "high",
        "dependencies_affected": ["session_store"],
    }
    return "```json\n" + json.dumps(impact) + "\n```"


def _mock_llm(complete_return) -> MagicMock:
    """Build a mock LLMClient with ``.available=True``."""
    llm = MagicMock()
    llm.available = True
    llm.provider_name = "mock-provider"
    llm.model = "mock-model"
    llm.complete = MagicMock(return_value=complete_return)
    return llm


# ---------------------------------------------------------------------------
# _extract_json_object helper
# ---------------------------------------------------------------------------


class TestExtractJsonObject:
    def test_extracts_fenced_object(self):
        assert _extract_json_object('```json\n{"a": 1}\n```') == {"a": 1}

    def test_extracts_bare_object(self):
        assert _extract_json_object('noise {"k": "v"} tail') == {"k": "v"}

    def test_returns_none_on_garbage(self):
        assert _extract_json_object("no json here") is None

    def test_returns_none_on_array(self):
        """A top-level array is not a valid impact object."""
        assert _extract_json_object("[1, 2, 3]") is None


# ---------------------------------------------------------------------------
# LLM path
# ---------------------------------------------------------------------------


class TestLLMPath:
    @pytest.mark.asyncio
    async def test_llm_path_parses_impact(self, config, bus, pr_data):
        """A valid LLM response is parsed into the impact result shape."""
        llm = _mock_llm(_canned_impact_json())
        worker = ImpactAnalyzerWorker("ia1", config, bus, llm=llm)

        result = await worker.analyze_pr_impact(pr_data)

        assert result["risk_score"] == 65.0
        assert result["risk_level"] == "high"
        assert result["affected_modules"] == ["auth"]
        assert result["breaking_changes"] == ["login() signature changed"]
        assert llm.complete.called

    @pytest.mark.asyncio
    async def test_llm_path_result_keys(self, config, bus, pr_data):
        """The LLM result has the same keys as the deterministic result."""
        llm = _mock_llm(_canned_impact_json())
        worker = ImpactAnalyzerWorker("ia1", config, bus, llm=llm)

        result = await worker.analyze_pr_impact(pr_data)

        for key in (
            "affected_files",
            "affected_modules",
            "breaking_changes",
            "risk_score",
            "risk_level",
            "dependencies_affected",
        ):
            assert key in result

    @pytest.mark.asyncio
    async def test_llm_path_broadcasts(self, config, bus, pr_data):
        """The LLM path still broadcasts the impact on the bus."""
        llm = _mock_llm(_canned_impact_json())
        worker = ImpactAnalyzerWorker("ia1", config, bus, llm=llm)

        await worker.analyze_pr_impact(pr_data)

        bus.broadcast.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_llm_risk_score_clamped(self, config, bus, pr_data):
        """Out-of-range risk scores are clamped into [0, 100]."""
        bad = json.dumps(
            {
                "affected_files": [],
                "affected_modules": [],
                "breaking_changes": [],
                "risk_score": 9999.0,
                "risk_level": "critical",
                "dependencies_affected": [],
            }
        )
        llm = _mock_llm(bad)
        worker = ImpactAnalyzerWorker("ia1", config, bus, llm=llm)

        result = await worker.analyze_pr_impact(pr_data)

        assert 0.0 <= result["risk_score"] <= 100.0

    @pytest.mark.asyncio
    async def test_llm_invalid_risk_level_derived(self, config, bus, pr_data):
        """An invalid risk_level is re-derived from the numeric score."""
        bad = json.dumps(
            {
                "affected_files": [],
                "affected_modules": [],
                "breaking_changes": [],
                "risk_score": 10.0,
                "risk_level": "bogus-level",
                "dependencies_affected": [],
            }
        )
        llm = _mock_llm(bad)
        worker = ImpactAnalyzerWorker("ia1", config, bus, llm=llm)

        result = await worker.analyze_pr_impact(pr_data)

        assert result["risk_level"] in ("low", "medium", "high", "critical")
        assert result["risk_level"] == "low"


# ---------------------------------------------------------------------------
# Deterministic / fallback paths
# ---------------------------------------------------------------------------


class TestDeterministicPath:
    @pytest.mark.asyncio
    async def test_none_llm_uses_deterministic(self, config, bus, pr_data):
        """``llm=None`` → deterministic heuristic path."""
        worker = ImpactAnalyzerWorker("ia1", config, bus, llm=None)

        result = await worker.analyze_pr_impact(pr_data)

        assert "auth/login.py" in result["affected_files"]
        assert isinstance(result["risk_score"], float)

    @pytest.mark.asyncio
    async def test_default_llm_is_none(self, config, bus):
        """The ``llm`` parameter defaults to ``None``."""
        worker = ImpactAnalyzerWorker("ia1", config, bus)
        assert worker.llm is None

    @pytest.mark.asyncio
    async def test_complete_returns_none_falls_back(self, config, bus, pr_data):
        """``complete()`` returning ``None`` → deterministic fallback."""
        llm = _mock_llm(None)
        worker = ImpactAnalyzerWorker("ia1", config, bus, llm=llm)

        result = await worker.analyze_pr_impact(pr_data)

        assert "auth/login.py" in result["affected_files"]
        assert llm.complete.called

    @pytest.mark.asyncio
    async def test_unparsable_response_falls_back(self, config, bus, pr_data):
        """A non-JSON LLM response → deterministic fallback."""
        llm = _mock_llm("Sorry, I cannot analyze this.")
        worker = ImpactAnalyzerWorker("ia1", config, bus, llm=llm)

        result = await worker.analyze_pr_impact(pr_data)

        assert "auth/login.py" in result["affected_files"]

    @pytest.mark.asyncio
    async def test_unavailable_llm_falls_back(self, config, bus, pr_data):
        """An LLM with ``.available=False`` is never called."""
        llm = _mock_llm(_canned_impact_json())
        llm.available = False
        worker = ImpactAnalyzerWorker("ia1", config, bus, llm=llm)

        result = await worker.analyze_pr_impact(pr_data)

        assert "auth/login.py" in result["affected_files"]
        llm.complete.assert_not_called()
