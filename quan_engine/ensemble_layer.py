"""
QuanEnsemble - CONSENSUS_75 Voting Layer
==========================================
Aggregates strategy votes and emits a signal only when:
  1. >= 75% of non-ABSTAIN voters agree on direction
  2. Average confidence of agreeing voters >= 0.65

This prevents any single strategy from forcing a trade and ensures
the ensemble only acts on high-conviction consensus.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from quan_engine.config import CONSENSUS_THRESHOLD, MIN_AVG_CONFIDENCE


@dataclass
class Vote:
    """A single strategy's directional opinion."""
    strategy: str
    direction: str        # "BUY", "SELL", or "ABSTAIN"
    confidence: float     # 0.0 - 1.0
    metadata: dict = field(default_factory=dict)


@dataclass
class EnsembleSignal:
    """Emitted when consensus is reached."""
    direction: str
    avg_confidence: float
    consensus_pct: float
    votes: List[Vote]
    strategy_count: int


class QuanEnsemble:
    """CONSENSUS_60 voting engine across a strategy pool.

    Two modes:
      1. CONSENSUS — 60% of active voters agree + avg confidence >= 0.55
         Requires at least 2 active voters.
      2. HIGH_CONVICTION_SOLO — If only 1 strategy fires but with
         confidence >= 0.80, emit a heavily discounted signal.
         Solo signals are rare and penalized to prevent noise.
    """

    MIN_ACTIVE_FOR_CONSENSUS = 2  # Require at least 2 strategies to agree
    SOLO_HIGH_CONVICTION = 0.80    # Solo signals need very high conviction
    SOLO_CONFIDENCE_DISCOUNT = 0.70  # Heavy discount for solo signals

    def __init__(
        self,
        consensus_threshold: float = CONSENSUS_THRESHOLD,
        min_confidence: float = MIN_AVG_CONFIDENCE,
    ):
        self.consensus_threshold = consensus_threshold
        self.min_confidence = min_confidence

    def vote(self, votes: List[Vote]) -> Optional[EnsembleSignal]:
        """Tally votes and return an EnsembleSignal if consensus is met.

        Args:
            votes: List of Vote objects from individual strategies.

        Returns:
            EnsembleSignal if thresholds are met, otherwise None.
        """
        # Filter out abstentions
        active = [v for v in votes if v.direction in ("BUY", "SELL")]
        if not active:
            return None

        buy_votes = [v for v in active if v.direction == "BUY"]
        sell_votes = [v for v in active if v.direction == "SELL"]

        total_active = len(active)

        # Determine majority direction
        if len(buy_votes) >= len(sell_votes):
            majority_votes = buy_votes
            direction = "BUY"
        else:
            majority_votes = sell_votes
            direction = "SELL"

        # --- Mode 1: Full consensus (when we have enough voters for meaningful consensus) ---
        if total_active >= self.MIN_ACTIVE_FOR_CONSENSUS:
            consensus_pct = len(majority_votes) / total_active
            if consensus_pct >= self.consensus_threshold:
                avg_confidence = sum(v.confidence for v in majority_votes) / len(majority_votes)
                if avg_confidence >= self.min_confidence:
                    return EnsembleSignal(
                        direction=direction,
                        avg_confidence=round(avg_confidence, 4),
                        consensus_pct=round(consensus_pct, 4),
                        votes=votes,
                        strategy_count=len(votes),
                    )

        # --- Mode 2: Solo high-conviction signal (fallback for 1 voter or failed consensus) ---
        if total_active >= 1:
            solo = active[0]
            print(f"DEBUG: Solo signal check - confidence {solo.confidence} >= {self.SOLO_HIGH_CONVICTION}?")
            if solo.confidence >= self.SOLO_HIGH_CONVICTION:
                discounted_conf = solo.confidence * self.SOLO_CONFIDENCE_DISCOUNT
                return EnsembleSignal(
                    direction=solo.direction,
                    avg_confidence=round(discounted_conf, 4),
                    consensus_pct=1.0,
                    votes=votes,
                    strategy_count=len(votes),
                )

        return None
