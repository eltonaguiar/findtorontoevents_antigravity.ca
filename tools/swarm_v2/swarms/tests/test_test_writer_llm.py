"""Tests for the real-LLM wiring in :class:`TestWriterWorker`.

All LLM interactions are mocked — these tests never make a network call.
They verify that:

* a wired-in, available LLM drives test generation (LLM path),
* ``llm=None`` keeps the deterministic template path,
* ``complete()`` returning ``None`` falls back to the template path,
* a response with no fenced code block falls back to the template path,
* the first fenced block is extracted when the model emits prose + code.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from swarms.core.messaging import MessageBus
from swarms.core.models import AgentConfig, AgentRole, CodeArtifact
# Imported under a non-``Test``-prefixed alias so pytest does not attempt to
# collect the worker class (whose name starts with ``Test``) as a test case.
from swarms.workers.test_writer import TestWriterWorker as WriterWorker


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config() -> AgentConfig:
    """A minimal test-writer agent config."""
    return AgentConfig(role=AgentRole.TEST_WRITER, model="mock-model")


@pytest.fixture
def bus() -> MessageBus:
    """A fresh in-memory message bus."""
    return MessageBus()


@pytest.fixture
def artifact() -> CodeArtifact:
    """A simple Python artifact to write tests for."""
    return CodeArtifact(
        filepath="calc.py",
        language="python",
        source_code='"""Calc."""\n\n\ndef add(a, b):\n    return a + b\n',
    )


@pytest.fixture
def js_artifact() -> CodeArtifact:
    """A non-Python artifact (should never reach the LLM path)."""
    return CodeArtifact(
        filepath="calc.js",
        language="javascript",
        source_code="function add(a, b) { return a + b; }",
    )


def _mock_llm(complete_return: object) -> MagicMock:
    """Build a mock :class:`LLMClient` whose ``complete`` returns *complete_return*."""
    llm = MagicMock()
    llm.available = True
    llm.provider_name = "mockprovider"
    llm.model = "mock-model"
    llm.complete.return_value = complete_return
    return llm


_LLM_TEST_FILE = (
    "import pytest\n"
    "from calc import add\n\n\n"
    "def test_add():\n"
    "    assert add(1, 2) == 3\n"
)


# ---------------------------------------------------------------------------
# LLM path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_path_extracts_fenced_block(config, bus, artifact):
    """A fenced code block in the LLM response becomes the returned test file."""
    response = f"Here are the tests:\n\n```python\n{_LLM_TEST_FILE}```\n"
    worker = WriterWorker("tw-1", config, bus, llm=_mock_llm(response))

    tests = await worker.write_tests(artifact)

    assert worker.llm.complete.called
    assert tests == _LLM_TEST_FILE.strip()
    assert "def test_add()" in tests


@pytest.mark.asyncio
async def test_llm_path_takes_first_block_when_multiple(config, bus, artifact):
    """When the model emits multiple blocks, the first one is returned."""
    response = (
        f"```python\n{_LLM_TEST_FILE}```\n\n"
        "And an alternative:\n\n```python\nassert True\n```\n"
    )
    worker = WriterWorker("tw-2", config, bus, llm=_mock_llm(response))

    tests = await worker.write_tests(artifact)

    assert tests == _LLM_TEST_FILE.strip()


@pytest.mark.asyncio
async def test_llm_path_handles_untagged_fence(config, bus, artifact):
    """A fenced block with no language tag is still extracted."""
    response = f"```\n{_LLM_TEST_FILE}```"
    worker = WriterWorker("tw-3", config, bus, llm=_mock_llm(response))

    tests = await worker.write_tests(artifact)

    assert tests == _LLM_TEST_FILE.strip()


# ---------------------------------------------------------------------------
# Deterministic / fallback paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deterministic_path_when_llm_is_none(config, bus, artifact):
    """With ``llm=None`` the deterministic template path is used."""
    worker = WriterWorker("tw-4", config, bus)

    assert worker.llm is None
    tests = await worker.write_tests(artifact)

    # Deterministic template path always emits its scaffolding markers.
    assert "auto-generated edge-case tests" in tests
    assert "TestEdgeCases" in tests


@pytest.mark.asyncio
async def test_fallback_when_complete_returns_none(config, bus, artifact):
    """When ``complete()`` returns ``None`` the template path runs."""
    llm = _mock_llm(None)
    worker = WriterWorker("tw-5", config, bus, llm=llm)

    tests = await worker.write_tests(artifact)

    assert llm.complete.called
    assert "auto-generated edge-case tests" in tests


@pytest.mark.asyncio
async def test_fallback_when_no_code_block(config, bus, artifact):
    """A response with no fenced block falls back to the template path."""
    llm = _mock_llm("I cannot write tests for this, sorry — no code fences here.")
    worker = WriterWorker("tw-6", config, bus, llm=llm)

    tests = await worker.write_tests(artifact)

    assert llm.complete.called
    assert "auto-generated edge-case tests" in tests


@pytest.mark.asyncio
async def test_unavailable_llm_uses_template_path(config, bus, artifact):
    """An LLM with ``available=False`` is never called; template path runs."""
    llm = MagicMock()
    llm.available = False
    worker = WriterWorker("tw-7", config, bus, llm=llm)

    tests = await worker.write_tests(artifact)

    llm.complete.assert_not_called()
    assert "auto-generated edge-case tests" in tests


@pytest.mark.asyncio
async def test_non_python_never_calls_llm(config, bus, js_artifact):
    """Non-Python artifacts short-circuit before the LLM path."""
    llm = _mock_llm(f"```python\n{_LLM_TEST_FILE}```")
    worker = WriterWorker("tw-8", config, bus, llm=llm)

    tests = await worker.write_tests(js_artifact)

    llm.complete.assert_not_called()
    assert "javascript" in tests
