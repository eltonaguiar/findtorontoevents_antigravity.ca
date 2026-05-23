"""Tests for the LLM wiring of :class:`ResearcherWorker`.

All tests are hermetic — the :class:`LLMClient` is always a :class:`MagicMock`,
so no real network call is ever made.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from swarms.core.models import AgentConfig, AgentRole, ResearchFinding
from swarms.workers.researcher import ResearcherWorker, _extract_json


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config() -> AgentConfig:
    """A baseline agent config (mid-tier model → quality multiplier 1.0)."""
    return AgentConfig(role=AgentRole.RESEARCHER, model="gpt-4o")


@pytest.fixture
def bus() -> MagicMock:
    """A mock message bus with an async ``broadcast``."""
    b = MagicMock()
    b.broadcast = AsyncMock()
    return b


def _canned_findings_json(n: int = 2) -> str:
    """Return a JSON-array LLM response with *n* well-formed findings."""
    findings = [
        {
            "source": f"LLM source #{i + 1}",
            "confidence": 0.8,
            "claim": f"LLM claim #{i + 1} about the topic",
            "evidence": [f"evidence A{i}", f"evidence B{i}"],
        }
        for i in range(n)
    ]
    return "```json\n" + json.dumps(findings) + "\n```"


def _mock_llm(complete_return) -> MagicMock:
    """Build a mock LLMClient with ``.available=True``."""
    llm = MagicMock()
    llm.available = True
    llm.provider_name = "mock-provider"
    llm.model = "mock-model"
    llm.complete = MagicMock(return_value=complete_return)
    return llm


# ---------------------------------------------------------------------------
# _extract_json helper
# ---------------------------------------------------------------------------


class TestExtractJson:
    def test_extracts_fenced_json_array(self):
        text = "```json\n[{\"a\": 1}]\n```"
        assert _extract_json(text) == [{"a": 1}]

    def test_extracts_bare_json_object(self):
        assert _extract_json('prefix {"k": "v"} suffix') == {"k": "v"}

    def test_returns_none_on_garbage(self):
        assert _extract_json("not json at all") is None

    def test_returns_none_on_empty(self):
        assert _extract_json("") is None

    def test_extracts_json_after_prose_preamble(self):
        # Swarm Q4 live validation (2026-05-17): prose before the fence must not
        # prevent JSON extraction. Real engine responses often prepend explanatory
        # text before the code block.
        text = (
            "Here is my analysis of the findings:\n\n"
            "The strategy shows a clear edge in the COMMODITY space.\n\n"
            "```json\n"
            '[{"system": "cot_positioning", "verdict": "MONEY_READY"}]\n'
            "```"
        )
        result = _extract_json(text)
        assert result == [{"system": "cot_positioning", "verdict": "MONEY_READY"}]

    def test_extracts_nested_json_object_after_preamble(self):
        text = (
            "Based on my review:\n\n"
            "```json\n"
            '{"verdict": "DONE", "summary": "all gates pass"}\n'
            "```"
        )
        result = _extract_json(text)
        assert result == {"verdict": "DONE", "summary": "all gates pass"}

    def test_fenced_block_wins_over_bare_object_in_preamble(self):
        # When there's a bare {..} in prose AND a fenced block, prefer the fence.
        text = 'This is bad json {garbage} below is the real payload\n```json\n{"ok": true}\n```'
        result = _extract_json(text)
        assert result == {"ok": True}


# ---------------------------------------------------------------------------
# LLM path
# ---------------------------------------------------------------------------


class TestLLMPath:
    @pytest.mark.asyncio
    async def test_llm_path_parses_findings(self, config, bus):
        """A valid LLM response is parsed into ResearchFinding objects."""
        llm = _mock_llm(_canned_findings_json(2))
        worker = ResearcherWorker("r1", config, bus, llm=llm)

        findings = await worker.research("quantum computing", "performance", depth=2)

        assert len(findings) == 2
        assert all(isinstance(f, ResearchFinding) for f in findings)
        assert findings[0].claim == "LLM claim #1 about the topic"
        assert llm.complete.called

    @pytest.mark.asyncio
    async def test_llm_path_broadcasts(self, config, bus):
        """The LLM path still broadcasts findings on the bus."""
        llm = _mock_llm(_canned_findings_json(1))
        worker = ResearcherWorker("r1", config, bus, llm=llm)

        await worker.research("topic", "dimension", depth=1)

        bus.broadcast.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_llm_confidence_clamped(self, config, bus):
        """Out-of-range confidence values are clamped into [0, 1]."""
        bad = json.dumps(
            [{"source": "s", "confidence": 5.0, "claim": "c", "evidence": []}]
        )
        llm = _mock_llm(bad)
        worker = ResearcherWorker("r1", config, bus, llm=llm)

        findings = await worker.research("t", "d", depth=1)

        assert len(findings) == 1
        assert 0.0 <= findings[0].confidence <= 1.0


# ---------------------------------------------------------------------------
# Deterministic / fallback paths
# ---------------------------------------------------------------------------


class TestDeterministicPath:
    @pytest.mark.asyncio
    async def test_none_llm_uses_deterministic(self, config, bus):
        """``llm=None`` → deterministic knowledge-base path."""
        worker = ResearcherWorker("r1", config, bus, llm=None)

        findings = await worker.research("python", "performance", depth=2)

        assert len(findings) >= 1
        assert all(isinstance(f, ResearchFinding) for f in findings)

    @pytest.mark.asyncio
    async def test_default_llm_is_none(self, config, bus):
        """The ``llm`` parameter defaults to ``None``."""
        worker = ResearcherWorker("r1", config, bus)
        assert worker.llm is None

    @pytest.mark.asyncio
    async def test_complete_returns_none_falls_back(self, config, bus):
        """``complete()`` returning ``None`` → deterministic fallback."""
        llm = _mock_llm(None)
        worker = ResearcherWorker("r1", config, bus, llm=llm)

        findings = await worker.research("python", "security", depth=2)

        assert len(findings) >= 1
        # Deterministic KB claim, not an LLM claim.
        assert any("Pickle" in f.claim for f in findings)

    @pytest.mark.asyncio
    async def test_unparsable_response_falls_back(self, config, bus):
        """A non-JSON LLM response → deterministic fallback."""
        llm = _mock_llm("I cannot help with that.")
        worker = ResearcherWorker("r1", config, bus, llm=llm)

        findings = await worker.research("python", "performance", depth=2)

        assert len(findings) >= 1
        assert any("GIL" in f.claim for f in findings)

    @pytest.mark.asyncio
    async def test_unavailable_llm_falls_back(self, config, bus):
        """An LLM with ``.available=False`` is never called."""
        llm = _mock_llm(_canned_findings_json(1))
        llm.available = False
        worker = ResearcherWorker("r1", config, bus, llm=llm)

        findings = await worker.research("python", "performance", depth=1)

        assert len(findings) >= 1
        llm.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_json_array_falls_back(self, config, bus):
        """An LLM response with no usable findings → deterministic fallback."""
        llm = _mock_llm("```json\n[]\n```")
        worker = ResearcherWorker("r1", config, bus, llm=llm)

        findings = await worker.research("python", "performance", depth=2)

        assert len(findings) >= 1
        assert any("GIL" in f.claim for f in findings)
