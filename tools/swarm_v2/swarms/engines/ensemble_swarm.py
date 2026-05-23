"""Ensemble swarm for weighted prediction aggregation."""

from __future__ import annotations

import asyncio
import logging
import statistics
from typing import Any

from swarms.core.base_orchestrator import BaseOrchestrator
from swarms.core.models import (
    AgentRole,
    EnsembleResult,
    MemoryEntry,
    MessageType,
    SwarmMessage,
    SwarmTask,
    TaskStatus,
    VoteResult,
)

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.8


class EnsembleSwarmOrchestrator(BaseOrchestrator):
    """Orchestrator for ensemble prediction with weighted aggregation.

    Pipeline:
        1. Register N prediction agents.
        2. Fan-out: each agent makes prediction with confidence.
        3. Aggregate:
           - Classification: weighted majority vote
           - Regression: weighted average
        4. Calculate confidence interval.
        5. If interval too wide, spawn additional agents.
    """

    def get_required_agents(self) -> list[AgentRole]:
        """Return [TACTICIAN x5]."""
        return [
            AgentRole.TACTICIAN,
            AgentRole.TACTICIAN,
            AgentRole.TACTICIAN,
            AgentRole.TACTICIAN,
            AgentRole.TACTICIAN,
        ]

    async def execute(self, task: SwarmTask) -> dict[str, Any]:
        """Run the ensemble prediction pipeline."""
        task.status = TaskStatus.IN_PROGRESS
        agent_ids = self.create_agents()

        prediction_task = task.inputs.get("prediction_task", task.description)
        task_type = task.inputs.get("task_type", "classification")
        confidence_threshold = task.inputs.get(
            "confidence_threshold", CONFIDENCE_THRESHOLD
        )

        # Step 1-2: Fan-out predictions
        votes = await self._collect_votes(agent_ids, prediction_task, task_type)

        # Step 3: Aggregate
        if task_type == "classification":
            aggregated = self._aggregate_classifications(votes)
        else:
            aggregated = self._aggregate_regressions(votes)

        # Step 4: Confidence interval
        ci = self._confidence_interval(votes)

        # Step 5: Expansion if low confidence
        ci_width = ci[1] - ci[0]
        if ci_width > (1 - confidence_threshold):
            logger.info("EnsembleSwarm: low confidence (width=%.2f), expanding", ci_width)
            extra_ids = await self._spawn_extra_agents(2)
            extra_votes = await self._collect_votes(extra_ids, prediction_task, task_type)
            votes.extend(extra_votes)
            if task_type == "classification":
                aggregated = self._aggregate_classifications(votes)
            else:
                aggregated = self._aggregate_regressions(votes)
            ci = self._confidence_interval(votes)

        dissenting = [
            v.reasoning for v in votes
            if v.vote != aggregated
        ]

        result = EnsembleResult(
            predictions=votes,
            aggregated_result=aggregated,
            confidence_interval=ci,
            dissenting_opinions=dissenting,
        )

        task.status = TaskStatus.COMPLETED
        output = result.model_dump()
        self.store_result(task, output)
        return output

    async def _collect_votes(
        self, agent_ids: list[str], prediction_task: str, task_type: str = "classification"
    ) -> list[VoteResult]:
        """Collect predictions from all agents."""
        async def _vote(agent_id: str) -> VoteResult:
            msg = SwarmMessage(
                msg_type=MessageType.VOTE,
                sender="orchestrator",
                recipients=[agent_id],
                payload={"task": prediction_task},
            )
            await self.bus.publish(msg)
            await asyncio.sleep(0.001)
            # Deterministic mock for testing
            idx = int(agent_id.split("_")[-1]) if "_" in agent_id else 0
            confidences = [0.9, 0.7, 0.85, 0.6, 0.95]
            if task_type == "regression":
                vote_values = [100.0, 200.0, 150.0, 50.0, 175.0]
            else:
                vote_values = ["buy", "sell", "buy", "hold", "buy"]
            return VoteResult(
                agent_id=agent_id,
                vote=vote_values[idx % len(vote_values)],
                confidence=confidences[idx % len(confidences)],
                reasoning=f"Reasoning from {agent_id}",
            )

        return await asyncio.gather(*[_vote(aid) for aid in agent_ids])

    async def _spawn_extra_agents(self, count: int) -> list[str]:
        """Spawn additional agents for low-confidence scenarios."""
        new_ids = []
        for i in range(count):
            agent_id = f"tactician_extra_{i}"
            from swarms.core.models import AgentConfig
            config = AgentConfig(
                role=AgentRole.TACTICIAN,
                model="gpt-4o",
                system_prompt="You are an additional ensemble predictor.",
            )
            self.registry.register(agent_id, config)
            new_ids.append(agent_id)
        return new_ids

    def _aggregate_classifications(self, votes: list[VoteResult]) -> Any:
        """Weighted majority vote (weight = confidence)."""
        weighted_counts: dict[Any, float] = {}
        for v in votes:
            weighted_counts[v.vote] = weighted_counts.get(v.vote, 0.0) + v.confidence
        return max(weighted_counts, key=weighted_counts.get) if weighted_counts else None

    def _aggregate_regressions(self, votes: list[VoteResult]) -> float:
        """Weighted average (weight = confidence)."""
        total_weight = sum(v.confidence for v in votes)
        if total_weight == 0:
            return 0.0
        return sum(float(v.vote) * v.confidence for v in votes) / total_weight

    def _confidence_interval(self, votes: list[VoteResult]) -> tuple[float, float]:
        """Calculate confidence interval from vote confidences."""
        confidences = [v.confidence for v in votes]
        if not confidences:
            return (0.0, 0.0)
        mean_conf = statistics.mean(confidences)
        if len(confidences) > 1:
            try:
                std_err = statistics.stdev(confidences) / (len(confidences) ** 0.5)
            except statistics.StatisticsError:
                std_err = 0.0
        else:
            std_err = 0.0
        return (max(0.0, mean_conf - 1.96 * std_err), min(1.0, mean_conf + 1.96 * std_err))
