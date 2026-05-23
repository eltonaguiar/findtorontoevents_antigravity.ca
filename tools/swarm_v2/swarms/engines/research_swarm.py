"""Multi-agent research swarm with epistemic triangulation."""

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
    MemoryEntry,
    MessageType,
    ResearchFinding,
    ResearchResult,
    SwarmMessage,
    SwarmTask,
    TaskStatus,
)
from swarms.core.registry import AgentRegistry
from swarms.core.safety import SafetyEnforcer
from swarms.workers.researcher import ResearcherWorker

logger = logging.getLogger(__name__)

MIN_CONFIDENCE = 0.7


class ResearchSwarmOrchestrator(BaseOrchestrator):
    """Orchestrator for deep research with cross-verification.

    Pipeline:
        1. Decompose topic into sub-questions.
        2. Phase 1 — Fan-out: assign each dimension to a researcher.
        3. Phase 2 — Cross-verify: flag contradictions.
        4. Phase 3 — Synthesize into ResearchResult.
        5. Store findings in memory.
    """

    def __init__(
        self,
        memory: SwarmMemory,
        bus: MessageBus,
        registry: AgentRegistry,
        safety: SafetyEnforcer,
        llm: Optional[LLMClient] = None,
    ) -> None:
        super().__init__(memory, bus, registry, safety)
        self.llm: Optional[LLMClient] = llm

    def get_required_agents(self) -> list[AgentRole]:
        """Return [RESEARCHER x4] (one per sub-question + verifier)."""
        return [
            AgentRole.RESEARCHER,
            AgentRole.RESEARCHER,
            AgentRole.RESEARCHER,
            AgentRole.RESEARCHER,
        ]

    async def execute(self, task: SwarmTask) -> dict[str, Any]:
        """Run the research pipeline."""
        task.status = TaskStatus.IN_PROGRESS
        agent_ids = self.create_agents()

        topic = task.inputs.get("topic", task.description)
        depth = task.inputs.get("depth", 3)

        # Step 1: Decompose
        sub_questions = self._decompose_topic(topic, depth)

        # Step 2: Phase 1 — Fan-out research
        researchers = agent_ids[:depth]
        findings_list = await self._run_research(topic, sub_questions, researchers)

        # Step 3: Phase 2 — Cross-verify
        contradictions = self._cross_verify(findings_list)

        # Step 4: Phase 3 — Synthesize
        result = self._synthesize(topic, findings_list, contradictions, sub_questions)

        # Store in memory
        for finding in result.findings:
            entry = MemoryEntry(
                content=finding.claim,
                metadata={
                    "source": finding.source,
                    "confidence": finding.confidence,
                },
                tags=["research", topic],
                source_swarm="research",
            )
            self.memory.add(entry)

        task.status = TaskStatus.COMPLETED
        output = result.model_dump()
        self.store_result(task, output)
        return output

    def _decompose_topic(self, topic: str, depth: int) -> list[str]:
        """Decompose a research topic into sub-questions."""
        templates = [
            f"What is the history of {topic}?",
            f"What are the current best practices for {topic}?",
            f"What are the main criticisms or limitations of {topic}?",
            f"What recent developments have occurred in {topic}?",
            f"How does {topic} compare to alternatives?",
        ]
        return templates[:depth]

    async def _run_research(
        self, topic: str, sub_questions: list[str], researchers: list[str]
    ) -> list[ResearchFinding]:
        """Fan-out research to :class:`ResearcherWorker` agents.

        Each worker investigates one sub-question via a real LLM when
        :attr:`llm` is wired in, otherwise via the deterministic
        knowledge-base path.
        """
        async def _research(question: str, researcher_id: str) -> ResearchFinding:
            config = AgentConfig(
                role=AgentRole.RESEARCHER,
                model=self.llm.model if self.llm else "template",
                system_prompt=f"You are a {AgentRole.RESEARCHER.value} agent.",
            )
            worker = ResearcherWorker(researcher_id, config, self.bus, llm=self.llm)
            findings = await worker.research(
                topic=topic, dimension=question, depth=3
            )
            if findings:
                return findings[0]
            return ResearchFinding(
                source=f"researcher_{researcher_id}",
                confidence=0.5,
                claim=f"No findings for: {question}",
                evidence=[],
            )

        findings = await asyncio.gather(
            *[_research(q, researchers[i % len(researchers)]) for i, q in enumerate(sub_questions)]
        )
        return list(findings)

    def _cross_verify(
        self, findings: list[ResearchFinding]
    ) -> list[tuple[str, str]]:
        """Detect contradictions between findings."""
        contradictions = []
        for i, f1 in enumerate(findings):
            for f2 in findings[i + 1:]:
                # Simple heuristic: very different confidence = potential contradiction
                if abs(f1.confidence - f2.confidence) > 0.3:
                    contradictions.append((f1.claim, f2.claim))
                    f1.contradictions.append(f2.claim)
                    f2.contradictions.append(f1.claim)
        return contradictions

    def _synthesize(
        self,
        topic: str,
        findings: list[ResearchFinding],
        contradictions: list[tuple[str, str]],
        sub_questions: list[str],
    ) -> ResearchResult:
        """Aggregate findings into a ResearchResult."""
        consensus_claims = [
            f.claim for f in findings
            if f.confidence >= MIN_CONFIDENCE and not f.contradictions
        ]
        disputed_claims = list(set(c[0] for c in contradictions))
        gaps = [q for q in sub_questions if not any(q in f.claim for f in findings)]
        sources = list(set(f.source for f in findings))

        return ResearchResult(
            topic=topic,
            findings=findings,
            consensus_claims=consensus_claims,
            disputed_claims=disputed_claims,
            gaps=gaps,
            sources=sources,
        )
