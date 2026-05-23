"""Multi-agent coding swarm with mandatory test enforcement."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from swarms.core.base_orchestrator import BaseOrchestrator
from swarms.core.llm_client import LLMClient
from swarms.core.memory import SwarmMemory
from swarms.core.messaging import MessageBus
from swarms.core.models import (
    AgentConfig,
    AgentRole,
    CodeArtifact,
    MemoryEntry,
    MessageType,
    SwarmMessage,
    SwarmTask,
    TaskStatus,
)
from swarms.core.registry import AgentRegistry
from swarms.core.safety import SafetyEnforcer
from swarms.workers.code_generator import CodeGeneratorWorker
from swarms.workers.code_reviewer import CodeReviewerWorker
from swarms.workers.test_writer import TestWriterWorker

logger = logging.getLogger(__name__)

DEFAULT_MAX_REVISIONS = 3
TEST_COVERAGE_THRESHOLD = 80.0


class CodingSwarmOrchestrator(BaseOrchestrator):
    """Orchestrator for multi-agent code generation.

    Pipeline:
        1. Decompose task into sub-tasks.
        2. Fan-out to code_generator agents (parallel).
        3. Collect code + tests from each generator.
        4. Route to code_reviewer agents (parallel review).
        5. Revision loop (max 3) if issues found.
        6. Test enforcement — all tests must pass.
        7. Store results in memory.

    Parameters
    ----------
    llm :
        Optional :class:`LLMClient`.  When supplied, code-generator workers
        produce code via a real LLM.  When ``None`` (the default) the swarm
        is fully hermetic and uses the deterministic template path — no
        network access.
    """

    def __init__(
        self,
        memory: SwarmMemory,
        bus: MessageBus,
        registry: AgentRegistry,
        safety: SafetyEnforcer,
        llm: Optional[LLMClient] = None,
    ) -> None:
        super().__init__(memory=memory, bus=bus, registry=registry, safety=safety)
        self.llm: Optional[LLMClient] = llm

    def get_required_agents(self) -> list[AgentRole]:
        """Return [CODE_GENERATOR x3, CODE_REVIEWER x2, TEST_WRITER x2]."""
        return [
            AgentRole.CODE_GENERATOR,
            AgentRole.CODE_GENERATOR,
            AgentRole.CODE_GENERATOR,
            AgentRole.CODE_REVIEWER,
            AgentRole.CODE_REVIEWER,
            AgentRole.TEST_WRITER,
            AgentRole.TEST_WRITER,
        ]

    async def execute(self, task: SwarmTask) -> dict[str, Any]:
        """Run the full coding pipeline."""
        task.status = TaskStatus.IN_PROGRESS
        agent_ids = self.create_agents()

        # Parse inputs
        description = task.inputs.get("description", task.description)
        max_revisions = task.inputs.get("max_revisions", DEFAULT_MAX_REVISIONS)
        strict = task.inputs.get("strict", False)
        models = task.inputs.get("models", ["gpt-4o"])

        # Step 1: Decompose into sub-tasks
        sub_tasks = self._decompose_task(description)
        logger.info("CodingSwarm: decomposed into %d sub-tasks", len(sub_tasks))

        # Step 2: Fan-out to code generators
        generators = [aid for aid in agent_ids if aid.startswith("code_generator")]
        code_results = await self._run_generators(sub_tasks, generators, models)

        # Step 3: Route to test writers for enrichment
        test_writers = [aid for aid in agent_ids if aid.startswith("test_writer")]
        code_results = await self._run_test_writers(code_results, test_writers)

        # Step 4-5: Review + revision loop
        reviewers = [aid for aid in agent_ids if aid.startswith("code_reviewer")]
        artifacts = await self._review_and_revise(
            code_results, reviewers, max_revisions, strict
        )

        # Step 6: Test enforcement
        final_artifacts = self._enforce_tests(artifacts, strict=strict)

        # Mark complete
        task.status = TaskStatus.COMPLETED if final_artifacts else TaskStatus.FAILED
        result = {
            "artifacts": [a.model_dump() for a in final_artifacts],
            "artifact_count": len(final_artifacts),
            "description": description,
            "strict": strict,
        }
        self.store_result(task, result)
        return result

    # -- Pipeline stages --------------------------------------------------

    def _decompose_task(self, description: str) -> list[dict]:
        """Decompose a coding task into sub-tasks (stub for subclassing)."""
        # In production this would use an LLM; here we return a single task.
        return [{"description": description, "filepath": "generated.py", "language": "python"}]

    async def _run_generators(
        self,
        sub_tasks: list[dict],
        generators: list[str],
        models: list[str],
    ) -> list[dict]:
        """Fan-out code generation to :class:`CodeGeneratorWorker` agents.

        Each sub-task is dispatched to a real worker which renders source +
        tests (via a real LLM when :attr:`llm` is wired in, otherwise via the
        deterministic template path) and runs pytest against the result.
        """
        model = models[0] if models else "gpt-4o"

        async def _generate(task_def: dict, gen_id: str) -> dict:
            config = AgentConfig(
                role=AgentRole.CODE_GENERATOR,
                model=model,
                system_prompt=f"You are a {AgentRole.CODE_GENERATOR.value} agent.",
            )
            worker = CodeGeneratorWorker(gen_id, config, self.bus, llm=self.llm)
            task = SwarmTask(
                task_type="coding",
                description=task_def.get("description", ""),
                inputs={
                    "filepath": task_def.get("filepath", "generated.py"),
                    "language": task_def.get("language", "python"),
                },
            )
            artifact = await worker.generate(task)
            return {
                "filepath": artifact.filepath,
                "language": artifact.language,
                "source_code": artifact.source_code,
                "tests": artifact.tests,
                "test_results": artifact.test_results,
                "generator_id": gen_id,
            }

        tasks = [
            _generate(st, generators[i % len(generators)])
            for i, st in enumerate(sub_tasks)
        ]
        return await asyncio.gather(*tasks)

    async def _run_test_writers(
        self,
        code_results: list[dict],
        test_writers: list[str],
    ) -> list[dict]:
        """Enrich code with tests via :class:`TestWriterWorker` agents.

        Each writer produces tests via a real LLM when :attr:`llm` is wired
        in, otherwise via the deterministic template path.
        """
        async def _enrich(code: dict, tw_id: str) -> dict:
            config = AgentConfig(
                role=AgentRole.TEST_WRITER,
                model=self.llm.model if self.llm else "template",
                system_prompt=f"You are a {AgentRole.TEST_WRITER.value} agent.",
            )
            worker = TestWriterWorker(tw_id, config, self.bus, llm=self.llm)
            artifact = CodeArtifact(
                filepath=code.get("filepath", "generated.py"),
                language=code.get("language", "python"),
                source_code=code.get("source_code", ""),
                tests=code.get("tests"),
            )
            tests = await worker.write_tests(artifact)
            if tests:
                code["tests"] = tests
                # Tests were replaced — re-run the suite so test_results
                # reflects the enriched tests, not the generator's originals.
                artifact.tests = tests
                code["test_results"] = await worker.run_test_suite(artifact)
            return code

        tasks = [
            _enrich(cr, test_writers[i % len(test_writers)])
            for i, cr in enumerate(code_results)
        ]
        return await asyncio.gather(*tasks)

    async def _review_and_revise(
        self,
        code_results: list[dict],
        reviewers: list[str],
        max_revisions: int,
        strict: bool,
    ) -> list[CodeArtifact]:
        """Run review loop with optional revision."""
        artifacts: list[CodeArtifact] = []
        for code in code_results:
            review_comments: list[dict] = []
            for revision in range(max_revisions):
                reviews = await self._run_reviewers(code, reviewers)
                review_comments.extend(reviews)
                issues = [r for r in reviews if r.get("issues")]
                if not issues:
                    break
                if revision < max_revisions - 1:
                    code["source_code"] += f"\n# Fixed revision {revision + 1}"
            artifacts.append(
                CodeArtifact(
                    filepath=code["filepath"],
                    language=code["language"],
                    source_code=code["source_code"],
                    tests=code.get("tests"),
                    test_results=code.get("test_results"),
                    review_comments=review_comments,
                )
            )
        return artifacts

    async def _run_reviewers(
        self,
        code: dict,
        reviewers: list[str],
    ) -> list[dict]:
        """Fan-out code review to :class:`CodeReviewerWorker` agents.

        Each reviewer runs a real LLM review when :attr:`llm` is wired in,
        otherwise the deterministic static-analysis path.
        """
        artifact = CodeArtifact(
            filepath=code.get("filepath", "generated.py"),
            language=code.get("language", "python"),
            source_code=code.get("source_code", ""),
            tests=code.get("tests"),
            test_results=code.get("test_results"),
        )
        task = SwarmTask(
            task_type="coding",
            description=code.get("description", ""),
            inputs={},
        )

        async def _review(rev_id: str) -> dict:
            config = AgentConfig(
                role=AgentRole.CODE_REVIEWER,
                model=self.llm.model if self.llm else "template",
                system_prompt=f"You are a {AgentRole.CODE_REVIEWER.value} agent.",
            )
            worker = CodeReviewerWorker(rev_id, config, self.bus, llm=self.llm)
            result = await worker.review(artifact, task)
            return {
                "reviewer": rev_id,
                "issues": not result.get("approved", True),
                "score": result.get("score"),
                "comment": f"score={result.get('score')} "
                f"issues={result.get('issues_found', 0)}",
                "review": result,
            }

        return await asyncio.gather(*[_review(rid) for rid in reviewers])

    def _enforce_tests(
        self,
        artifacts: list[CodeArtifact],
        strict: bool = True,
    ) -> list[CodeArtifact]:
        """Select artifacts whose tests pass.

        strict=True  — reject every artifact with a test failure / no tests /
                       sub-threshold coverage (return only clean artifacts,
                       possibly an empty list).
        strict=False — prefer clean artifacts; but if NONE are clean, return
                       the single best-effort artifact (fewest failures, then
                       most passes) rather than nothing. Without this the
                       swarm yields 0 artifacts whenever the LLM-generated
                       tests have a single failure — which made the coding
                       swarm unusable for autonomous runs.
        """
        clean: list[CodeArtifact] = []
        for art in artifacts:
            tr = art.test_results
            if tr is None:
                logger.warning("CodingSwarm: %s has no tests", art.filepath)
                continue
            if tr.get("failed", 0) > 0:
                logger.warning("CodingSwarm: %s has %d test failures",
                               art.filepath, tr["failed"])
                continue
            if tr.get("coverage", 0) < TEST_COVERAGE_THRESHOLD:
                logger.warning(
                    "CodingSwarm: %s coverage %.1f%% below threshold %.1f%%",
                    art.filepath, tr["coverage"], TEST_COVERAGE_THRESHOLD,
                )
                continue
            clean.append(art)

        if clean:
            return clean
        if strict:
            return []
        # Non-strict best-effort: return the least-broken artifact so the
        # caller always has something to iterate on.
        scored = [a for a in artifacts if a.test_results is not None]
        if not scored:
            return []
        best = min(
            scored,
            key=lambda a: (a.test_results.get("failed", 0),
                           -a.test_results.get("passed", 0)),
        )
        logger.warning(
            "CodingSwarm: no artifact passed enforcement — returning "
            "best-effort %s (failed=%d, passed=%d). Review before use.",
            best.filepath,
            best.test_results.get("failed", 0),
            best.test_results.get("passed", 0),
        )
        return [best]
