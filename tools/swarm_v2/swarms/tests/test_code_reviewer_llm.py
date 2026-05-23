"""Tests for the real-LLM wiring in :class:`CodeReviewerWorker`.

All LLM interactions are mocked — these tests never make a network call.
They verify that:

* a wired-in, available LLM drives the review (LLM path),
* ``llm=None`` keeps the deterministic static-analysis path,
* ``complete()`` returning ``None`` falls back to the deterministic path,
* an unparsable LLM response falls back to the deterministic path,
* an LLM that reports ``NONE`` yields an empty comment list.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from swarms.core.messaging import MessageBus
from swarms.core.models import AgentConfig, AgentRole, CodeArtifact, SwarmTask
from swarms.workers.code_reviewer import CodeReviewerWorker


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config() -> AgentConfig:
    """A minimal reviewer agent config."""
    return AgentConfig(role=AgentRole.CODE_REVIEWER, model="mock-model")


@pytest.fixture
def bus() -> MessageBus:
    """A fresh in-memory message bus."""
    return MessageBus()


@pytest.fixture
def artifact() -> CodeArtifact:
    """A simple, well-formed Python artifact to review."""
    return CodeArtifact(
        filepath="sample.py",
        language="python",
        source_code='"""Sample."""\n\n\ndef add(a, b):\n    return a + b\n',
        tests='def test_add():\n    assert add(1, 2) == 3\n',
    )


@pytest.fixture
def task() -> SwarmTask:
    """A minimal coding task."""
    return SwarmTask(
        task_type="coding",
        description="implement an addition helper",
        inputs={"language": "python"},
    )


def _mock_llm(complete_return: object) -> MagicMock:
    """Build a mock :class:`LLMClient` whose ``complete`` returns *complete_return*."""
    llm = MagicMock()
    llm.available = True
    llm.provider_name = "mockprovider"
    llm.model = "mock-model"
    llm.complete.return_value = complete_return
    return llm


# ---------------------------------------------------------------------------
# LLM path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_path_parses_structured_findings(config, bus, artifact, task):
    """A well-formed pipe-delimited response is parsed into comment dicts."""
    response = (
        "critical | eval() detected | remove the eval call\n"
        "warning | function lacks a docstring | add a docstring\n"
        "info | line slightly long | wrap the line\n"
    )
    worker = CodeReviewerWorker("rev-1", config, bus, llm=_mock_llm(response))

    result = await worker.review(artifact, task)

    assert worker.llm.complete.called
    assert result["issues_found"] == 3
    severities = sorted(c["severity"] for c in result["comments"])
    assert severities == ["critical", "info", "warning"]
    first = result["comments"][0]
    assert set(first) == {"line", "severity", "message", "suggestion"}
    assert first["message"] == "eval() detected"
    assert first["suggestion"] == "remove the eval call"


@pytest.mark.asyncio
async def test_llm_path_none_sentinel_yields_no_comments(config, bus, artifact, task):
    """An LLM reporting ``NONE`` produces an empty comment list (clean review)."""
    worker = CodeReviewerWorker("rev-2", config, bus, llm=_mock_llm("NONE"))

    result = await worker.review(artifact, task)

    assert result["issues_found"] == 0
    assert result["comments"] == []
    assert result["score"] == 100.0
    assert result["approved"] is True


@pytest.mark.asyncio
async def test_llm_path_skips_unknown_severity_lines(config, bus, artifact, task):
    """Lines with an invalid severity token are dropped, valid ones kept."""
    response = (
        "blocker | not a real severity | ignored\n"
        "warning | real finding | fix it\n"
    )
    worker = CodeReviewerWorker("rev-3", config, bus, llm=_mock_llm(response))

    result = await worker.review(artifact, task)

    assert result["issues_found"] == 1
    assert result["comments"][0]["severity"] == "warning"


@pytest.mark.asyncio
async def test_llm_path_tolerates_list_markers(config, bus, artifact, task):
    """Leading list markers / numbering on findings are stripped before parsing."""
    response = (
        "1. warning | numbered finding | fix it\n"
        "- info | bulleted finding | tidy up\n"
    )
    worker = CodeReviewerWorker("rev-4", config, bus, llm=_mock_llm(response))

    result = await worker.review(artifact, task)

    assert result["issues_found"] == 2
    messages = {c["message"] for c in result["comments"]}
    assert messages == {"numbered finding", "bulleted finding"}


# ---------------------------------------------------------------------------
# Deterministic / fallback paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deterministic_path_when_llm_is_none(config, bus, artifact, task):
    """With ``llm=None`` the deterministic static-analysis path is used."""
    worker = CodeReviewerWorker("rev-5", config, bus)

    assert worker.llm is None
    result = await worker.review(artifact, task)

    # Deterministic reviewer always returns a structured result.
    assert "score" in result
    assert "comments" in result
    assert isinstance(result["comments"], list)


@pytest.mark.asyncio
async def test_fallback_when_complete_returns_none(config, bus, artifact, task):
    """When ``complete()`` returns ``None`` the deterministic path runs."""
    llm = _mock_llm(None)
    worker = CodeReviewerWorker("rev-6", config, bus, llm=llm)

    result = await worker.review(artifact, task)

    assert llm.complete.called
    # Deterministic review of clean code still produces a valid result.
    assert isinstance(result["comments"], list)
    assert 0.0 <= result["score"] <= 100.0


@pytest.mark.asyncio
async def test_fallback_when_response_unparsable(config, bus, artifact, task):
    """Garbage text with no pipe-delimited findings falls back deterministically."""
    llm = _mock_llm("Sure! Here is my review of your great code. Looks fine.")
    worker = CodeReviewerWorker("rev-7", config, bus, llm=llm)

    result = await worker.review(artifact, task)

    assert llm.complete.called
    assert isinstance(result["comments"], list)
    assert 0.0 <= result["score"] <= 100.0


@pytest.mark.asyncio
async def test_unavailable_llm_uses_deterministic_path(config, bus, artifact, task):
    """An LLM with ``available=False`` is never called; deterministic path runs."""
    llm = MagicMock()
    llm.available = False
    worker = CodeReviewerWorker("rev-8", config, bus, llm=llm)

    result = await worker.review(artifact, task)

    llm.complete.assert_not_called()
    assert isinstance(result["comments"], list)


def test_parse_llm_review_returns_none_on_no_findings(config, bus):
    """`_parse_llm_review` signals fallback (``None``) when nothing is parsable."""
    worker = CodeReviewerWorker("rev-9", config, bus)

    assert worker._parse_llm_review("just prose, no findings here") is None


def test_parse_llm_review_empty_list_on_none_sentinel(config, bus):
    """`_parse_llm_review` returns an empty list for the ``NONE`` sentinel."""
    worker = CodeReviewerWorker("rev-10", config, bus)

    assert worker._parse_llm_review("NONE") == []
