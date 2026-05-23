"""Deep research worker agent.

Conducts structured research on a topic dimension, producing findings with
confidence scores.  Supports cross-verification of findings against other
researchers for epistemic triangulation.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from swarms.core.models import (
    AgentConfig,
    AgentRole,
    MessageType,
    ResearchFinding,
    SwarmMessage,
)
from swarms.core.messaging import MessageBus
from swarms.core.llm_client import LLMClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Deterministic research knowledge base (simulated)
# ---------------------------------------------------------------------------

# Pre-seeded knowledge fragments keyed by (topic_keyword, dimension_keyword)
_KNOWLEDGE_BASE: dict[tuple[str, str], list[dict]] = {
    # Topic: "python"
    ("python", "performance"): [
        {
            "claim": "Python's GIL limits true parallelism for CPU-bound workloads",
            "evidence": [
                "CPython's GIL ensures only one thread executes Python bytecode at a time",
                "Multiprocessing module works around GIL by using separate processes",
                "PyPy and Jython offer alternative GIL implementations",
            ],
            "confidence": 0.95,
            "source": "Python Documentation + Academic Literature",
        },
        {
            "claim": "asyncio provides single-threaded concurrency for I/O-bound applications",
            "evidence": [
                "async/await syntax introduced in Python 3.5",
                "Event loop manages multiple I/O operations without threading overhead",
                "Benchmarks show asyncio outperforming threading for high-concurrency I/O",
            ],
            "confidence": 0.92,
            "source": "Python asyncio docs + performance benchmarks",
        },
    ],
    ("python", "security"): [
        {
            "claim": "Pickle deserialization is unsafe for untrusted data",
            "evidence": [
                "pickle.loads() can execute arbitrary code during unpickling",
                "CVE-2019-11340 and similar vulnerabilities documented",
                "Official docs recommend using json for untrusted sources",
            ],
            "confidence": 0.98,
            "source": "Python Security Documentation",
        },
    ],
    # Topic: "machine learning"
    ("machine learning", "performance"): [
        {
            "claim": "GPU acceleration provides 10-100x speedup for deep learning training",
            "evidence": [
                "CUDA cores enable massive parallel matrix operations",
                "TensorFlow and PyTorch show order-of-magnitude improvements with GPU",
                "TPUs provide additional 2-3x over GPUs for specific workloads",
            ],
            "confidence": 0.93,
            "source": "MLSys Conference Papers + Vendor Benchmarks",
        },
    ],
    ("machine learning", "security"): [
        {
            "claim": "Model inversion attacks can reconstruct training data from model outputs",
            "evidence": [
                "Fredrikson et al. (2015) demonstrated model inversion on facial recognition",
                "Membership inference attacks are practical against overfitted models",
                "Differential privacy is a mitigating technique",
            ],
            "confidence": 0.88,
            "source": "ACM CCS Papers + NIST AI Risk Framework",
        },
    ],
    # Topic: "distributed systems"
    ("distributed systems", "consistency"): [
        {
            "claim": "CAP theorem states distributed systems can guarantee at most two of consistency, availability, and partition tolerance",
            "evidence": [
                "Formal proof by Gilbert and Lynch (2002)",
                "In practice, partition tolerance is not optional — leaving CP or AP choices",
                "Real-world systems like Dynamo (AP) and Spanner (CP) demonstrate the tradeoff",
            ],
            "confidence": 0.96,
            "source": "Brewer (2000) + Gilbert & Lynch (2002)",
        },
    ],
    ("distributed systems", "performance"): [
        {
            "claim": "Eventual consistency models can achieve higher throughput than strong consistency",
            "evidence": [
                "Amazon Dynamo paper reports 99.9th percentile latency under 300ms",
                "Strong consensus protocols (Paxos/Raft) add 1-2 RTT overhead",
                "Read repair and hinted handoff manage convergence latency",
            ],
            "confidence": 0.90,
            "source": "Dynamo Paper (SOSP 2007) + Raft Paper",
        },
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_JSON_FENCE_RE = re.compile(
    r"```[ \t]*(?:json)?[ \t]*\r?\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)


def _extract_json(text: str) -> Optional[Any]:
    """Extract the first JSON value from an LLM response.

    Handles responses that wrap JSON in a markdown ```` ```json ```` fence as
    well as bare JSON. Returns the decoded object, or ``None`` when no valid
    JSON could be found.

    Parameters
    ----------
    text :
        Raw LLM response text.

    Returns
    -------
    Any or None
        The decoded JSON value, or ``None`` on parse failure.
    """
    if not text:
        return None

    candidates: list[str] = []
    fenced = _JSON_FENCE_RE.findall(text)
    candidates.extend(block.strip() for block in fenced)

    # Fall back to the widest [...] / {...} span in the raw text.
    for open_ch, close_ch in (("[", "]"), ("{", "}")):
        start = text.find(open_ch)
        end = text.rfind(close_ch)
        if start != -1 and end > start:
            candidates.append(text[start : end + 1])

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
    return None


# ---------------------------------------------------------------------------
# ResearcherWorker
# ---------------------------------------------------------------------------


class ResearcherWorker:
    """Conducts deep research on a topic dimension.

    Capabilities
    ------------
    * Search and synthesize information.
    * Evaluate source credibility.
    * Cross-reference findings.
    * Generate structured research findings with confidence scores.

    Parameters
    ----------
    agent_id :
        Unique identifier for this worker instance.
    config :
        Agent configuration (role, model, temperature, …).
    bus :
        Shared :class:`MessageBus` for inter-agent communication.
    llm :
        Optional :class:`LLMClient`.  When supplied *and* available the worker
        researches via a real LLM; otherwise it falls back to the
        deterministic knowledge-base path.  ``None`` (the default) keeps the
        worker fully hermetic — no network access.
    """

    def __init__(
        self,
        agent_id: str,
        config: AgentConfig,
        bus: MessageBus,
        llm: Optional[LLMClient] = None,
    ) -> None:
        self.agent_id: str = agent_id
        self.config: AgentConfig = config
        self.bus: MessageBus = bus
        self.llm: Optional[LLMClient] = llm

    # -- public API ------------------------------------------------------------

    async def research(
        self,
        topic: str,
        dimension: str,
        depth: int = 3,
    ) -> list[ResearchFinding]:
        """Research a specific *dimension* of a *topic*.

        In production this would call search APIs, read papers, and crawl
documentation.  In this simulation it queries a deterministic knowledge
base and generates placeholder findings when no seeded data exists.

        Parameters
        ----------
        topic :
            The high-level research topic (e.g. ``"python"``,
            ``"machine learning"``).
        dimension :
            The sub-dimension to investigate (e.g. ``"performance"``,
            ``"security"``).
        depth :
            Research depth — controls how many findings to attempt to
            retrieve (1-5).  Default is 3.

        Returns
        -------
        list[ResearchFinding]
            Structured findings, each with a confidence score in [0, 1].
        """
        logger.info(
            "ResearcherWorker[%s]: researching topic='%s' dimension='%s' depth=%d",
            self.agent_id,
            topic,
            dimension,
            depth,
        )

        # Prefer a real LLM when one is wired in and available; on any
        # failure (no LLM, unavailable, network error, unparsable response)
        # fall through to the deterministic knowledge-base path below.
        if self.llm is not None and self.llm.available:
            llm_findings = self._llm_research(topic, dimension, depth)
            if llm_findings is not None:
                logger.info(
                    "ResearcherWorker[%s]: LLM path (provider=%s) — %d findings",
                    self.agent_id,
                    self.llm.provider_name,
                    len(llm_findings),
                )
                findings = self._apply_model_quality(llm_findings)
                await self.bus.broadcast(
                    payload={
                        "agent_id": self.agent_id,
                        "topic": topic,
                        "dimension": dimension,
                        "findings": [f.model_dump() for f in findings],
                        "depth": depth,
                    },
                    sender=self.agent_id,
                    msg_type=MessageType.RESEARCH_FINDING,
                )
                return findings

        logger.info(
            "ResearcherWorker[%s]: deterministic knowledge-base path",
            self.agent_id,
        )

        findings: list[ResearchFinding] = []
        topic_lower = topic.lower()
        dim_lower = dimension.lower()

        # 1. Query seeded knowledge base
        for (kb_topic, kb_dim), entries in _KNOWLEDGE_BASE.items():
            if kb_topic in topic_lower or topic_lower in kb_topic:
                if kb_dim in dim_lower or dim_lower in kb_dim:
                    for entry in entries[:depth]:
                        finding = ResearchFinding(
                            source=entry["source"],
                            confidence=entry["confidence"],
                            claim=entry["claim"],
                            evidence=list(entry["evidence"]),
                        )
                        findings.append(finding)

        # 2. If no seeded matches, generate simulated findings
        if not findings:
            logger.debug(
                "ResearcherWorker[%s]: no seeded data — generating simulated findings",
                self.agent_id,
            )
            for i in range(depth):
                confidence = self._derive_confidence(topic, dimension, i)
                finding = ResearchFinding(
                    source=f"Simulated source #{i + 1} for '{topic}/{dimension}'",
                    confidence=round(confidence, 2),
                    claim=(
                        f"Simulated claim #{i + 1} about {topic} in the "
                        f"context of {dimension} — depth level {i + 1}"
                    ),
                    evidence=[
                        f"Evidence point A for claim #{i + 1}",
                        f"Evidence point B for claim #{i + 1}",
                    ],
                )
                findings.append(finding)

        # 3. Apply model-quality modifier
        findings = self._apply_model_quality(findings)

        logger.info(
            "ResearcherWorker[%s]: produced %d findings for '%s/%s'",
            self.agent_id,
            len(findings),
            topic,
            dimension,
        )

        # Broadcast findings
        await self.bus.broadcast(
            payload={
                "agent_id": self.agent_id,
                "topic": topic,
                "dimension": dimension,
                "findings": [f.model_dump() for f in findings],
                "depth": depth,
            },
            sender=self.agent_id,
            msg_type=MessageType.RESEARCH_FINDING,
        )

        return findings

    async def cross_verify(
        self,
        my_findings: list[ResearchFinding],
        other_findings: list[ResearchFinding],
    ) -> list[dict]:
        """Cross-verify *my_findings* against *other_findings*.

        Flags contradictions and produces resolution notes for each
        disagreement.

        Parameters
        ----------
        my_findings :
            Findings produced by this researcher.
        other_findings :
            Findings produced by another researcher for comparison.

        Returns
        -------
        list[dict]
            Each dict has keys:

            * ``my_claim`` (*str*)
            * ``other_claim`` (*str*)
            * ``contradiction_type`` (*str*) — ``direct`` | ``partial`` | ``omission``
            * ``severity`` (*str*) — ``high`` | ``medium`` | ``low``
            * ``resolution_notes`` (*str*)
        """
        logger.info(
            "ResearcherWorker[%s]: cross-verifying %d findings against %d peer findings",
            self.agent_id,
            len(my_findings),
            len(other_findings),
        )

        contradictions: list[dict] = []

        # Build lookup by claim keyword overlap
        my_claims = {f.claim: f for f in my_findings}
        other_claims = {f.claim: f for f in other_findings}

        # Check for contradictions: overlapping topic but divergent confidence
        for my_claim_text, my_finding in my_claims.items():
            matched = False
            for other_claim_text, other_finding in other_claims.items():
                if self._claims_overlap(my_claim_text, other_claim_text):
                    matched = True
                    confidence_diff = abs(my_finding.confidence - other_finding.confidence)

                    if confidence_diff > 0.3:
                        contradictions.append(
                            {
                                "my_claim": my_claim_text,
                                "other_claim": other_claim_text,
                                "contradiction_type": "partial",
                                "severity": "high" if confidence_diff > 0.5 else "medium",
                                "resolution_notes": (
                                    f"Confidence divergence: {my_finding.confidence:.2f} vs "
                                    f"{other_finding.confidence:.2f}. "
                                    "Recommend additional primary-source verification."
                                ),
                            }
                        )
                    # Check for mutually exclusive evidence
                    my_evidence = set(my_finding.evidence)
                    other_evidence = set(other_finding.evidence)
                    if my_evidence and other_evidence and not my_evidence & other_evidence:
                        contradictions.append(
                            {
                                "my_claim": my_claim_text,
                                "other_claim": other_claim_text,
                                "contradiction_type": "partial",
                                "severity": "medium",
                                "resolution_notes": (
                                    "Disjoint evidence sets — findings may be addressing "
                                    "different aspects of the same question."
                                ),
                            }
                        )

            if not matched:
                # This claim has no peer support — flag as omission in other findings
                contradictions.append(
                    {
                        "my_claim": my_claim_text,
                        "other_claim": "(no matching claim)",
                        "contradiction_type": "omission",
                        "severity": "low",
                        "resolution_notes": (
                            "This claim was not found in peer findings — "
                            "may represent unique insight or oversight by peer."
                        ),
                    }
                )

        # Check for claims in other_findings not present in my_findings
        for other_claim_text, other_finding in other_claims.items():
            matched = any(
                self._claims_overlap(other_claim_text, my_text)
                for my_text in my_claims
            )
            if not matched:
                contradictions.append(
                    {
                        "my_claim": "(no matching claim)",
                        "other_claim": other_claim_text,
                        "contradiction_type": "omission",
                        "severity": "low",
                        "resolution_notes": (
                            "Peer found a claim not present in local findings — "
                            "consider expanding research scope."
                        ),
                    }
                )

        logger.info(
            "ResearcherWorker[%s]: cross-verification found %d contradiction(s)",
            self.agent_id,
            len(contradictions),
        )

        return contradictions

    async def handle_message(self, message: SwarmMessage) -> Optional[SwarmMessage]:
        """Process incoming messages relevant to research.

        Supported message types:

        * ``TASK_ASSIGNMENT`` with research instructions — triggers :meth:`research`.

        Parameters
        ----------
        message :
            The incoming swarm message.

        Returns
        -------
        SwarmMessage or None
            A response message containing research findings.
        """
        if message.msg_type == MessageType.TASK_ASSIGNMENT:
            task_data = message.payload.get("task", {})
            inputs = task_data.get("inputs", {})
            topic = inputs.get("topic", "")
            dimension = inputs.get("dimension", "general")
            depth = inputs.get("depth", 3)

            if topic:
                findings = await self.research(topic, dimension, depth=depth)
                return SwarmMessage(
                    msg_type=MessageType.RESEARCH_FINDING,
                    sender=self.agent_id,
                    recipients=[message.sender],
                    payload={
                        "agent_id": self.agent_id,
                        "topic": topic,
                        "dimension": dimension,
                        "findings": [f.model_dump() for f in findings],
                    },
                )

        # Cross-verification request
        if message.msg_type == MessageType.RESEARCH_FINDING:
            payload = message.payload
            if "peer_findings" in payload and "my_findings" in payload:
                my_findings = [
                    ResearchFinding(**f) for f in payload["my_findings"]
                ]
                peer_findings = [
                    ResearchFinding(**f) for f in payload["peer_findings"]
                ]
                contradictions = await self.cross_verify(my_findings, peer_findings)
                return SwarmMessage(
                    msg_type=MessageType.CONSENSUS,
                    sender=self.agent_id,
                    recipients=[message.sender],
                    payload={
                        "agent_id": self.agent_id,
                        "contradictions": contradictions,
                    },
                )

        return None

    # -- internal helpers ------------------------------------------------------

    def _llm_research(
        self,
        topic: str,
        dimension: str,
        depth: int,
    ) -> Optional[list[ResearchFinding]]:
        """Research *topic*/*dimension* via the wired-in :class:`LLMClient`.

        Parameters
        ----------
        topic :
            The high-level research topic.
        dimension :
            The sub-dimension to investigate.
        depth :
            Number of findings to request.

        Returns
        -------
        list[ResearchFinding] or None
            Parsed findings on success; ``None`` when the completion failed
            or produced no parsable findings (caller then uses the
            deterministic knowledge-base path).
        """
        system = (
            "You are a rigorous research analyst. Output ONLY valid JSON — no "
            "prose outside the JSON. Every claim must be backed by concrete "
            "evidence points and an honest confidence score in [0, 1]."
        )
        prompt = (
            f"Research the '{dimension}' dimension of the topic '{topic}'.\n\n"
            f"Return EXACTLY a JSON array of {depth} finding objects and "
            "nothing else. Each object must have these keys:\n"
            '  "source"     : string — origin of the claim,\n'
            '  "confidence" : number in [0, 1],\n'
            '  "claim"      : string — the factual assertion,\n'
            '  "evidence"   : array of strings — supporting data points.\n'
        )
        text = self.llm.complete(prompt, system=system)
        if text is None:
            return None

        parsed = _extract_json(text)
        if not isinstance(parsed, list):
            return None

        findings: list[ResearchFinding] = []
        for entry in parsed:
            if not isinstance(entry, dict):
                continue
            try:
                confidence = float(entry.get("confidence", 0.0))
            except (TypeError, ValueError):
                continue
            confidence = round(min(1.0, max(0.0, confidence)), 2)
            claim = entry.get("claim")
            source = entry.get("source")
            if not isinstance(claim, str) or not claim.strip():
                continue
            if not isinstance(source, str) or not source.strip():
                source = f"LLM research: {topic}/{dimension}"
            raw_evidence = entry.get("evidence", [])
            evidence = [
                str(e) for e in raw_evidence if isinstance(e, (str, int, float))
            ] if isinstance(raw_evidence, list) else []
            findings.append(
                ResearchFinding(
                    source=source,
                    confidence=confidence,
                    claim=claim,
                    evidence=evidence,
                )
            )

        if not findings:
            return None
        return findings

    def _derive_confidence(self, topic: str, dimension: str, index: int) -> float:
        """Generate a deterministic confidence score for a simulated finding.

        The score is based on a hash of the inputs so the same query always
        produces the same confidence, with slight variation by *index*.
        """
        # Deterministic pseudo-random from string hash
        combined = f"{topic}:{dimension}:{index}:{self.agent_id}"
        hash_val = hash(combined) % 1000
        base = 0.5 + (hash_val / 1000.0) * 0.4  # range 0.5 - 0.9
        return round(min(0.99, max(0.1, base)), 2)

    def _apply_model_quality(
        self, findings: list[ResearchFinding]
    ) -> list[ResearchFinding]:
        """Adjust confidence scores based on the configured model quality.

        Higher-quality models (e.g. ``"gpt-4o"``) retain higher confidence;
        lower-quality models have their confidence dampened.
        """
        model = self.config.model.lower()

        # Quality tiers
        if any(m in model for m in ("gpt-4", "claude-3-opus", "claude-sonnet")):
            multiplier = 1.0
        elif any(m in model for m in ("gpt-3.5", "claude-3-haiku", "claude-instant")):
            multiplier = 0.9
        else:
            multiplier = 0.85

        adjusted: list[ResearchFinding] = []
        for f in findings:
            new_confidence = min(1.0, f.confidence * multiplier)
            adjusted.append(
                ResearchFinding(
                    source=f.source,
                    confidence=round(new_confidence, 2),
                    claim=f.claim,
                    evidence=list(f.evidence),
                    contradictions=list(f.contradictions),
                )
            )
        return adjusted

    def _claims_overlap(self, claim1: str, claim2: str) -> bool:
        """Check whether two claims address the same subject.

        Uses simple keyword overlap as a heuristic.
        """
        words1 = set(re.findall(r"\b\w+\b", claim1.lower()))
        words2 = set(re.findall(r"\b\w+\b", claim2.lower()))
        # Filter out stop words
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "can", "need", "dare", "ought", "used", "to", "of", "in",
            "for", "on", "with", "at", "by", "from", "as", "into",
            "through", "during", "before", "after", "above", "below",
            "between", "out", "off", "over", "under", "again", "further",
            "then", "once", "and", "but", "if", "or", "because", "until",
            "while", "although", "though", "since", "unless", "than",
            "this", "that", "these", "those", "i", "me", "my", "we",
            "our", "you", "your", "he", "him", "his", "she", "her",
            "it", "its", "they", "them", "their", "what", "which", "who",
            "when", "where", "why", "how", "all", "each", "both", "few",
            "more", "most", "other", "some", "such", "no", "nor", "not",
            "only", "own", "same", "so", "than", "too", "very", "just",
            "about", "also", "any", "up", "down", "here", "there",
        }
        content1 = words1 - stop_words
        content2 = words2 - stop_words
        if not content1 or not content2:
            return False
        overlap = content1 & content2
        total = content1 | content2
        return len(overlap) / len(total) > 0.3 if total else False
