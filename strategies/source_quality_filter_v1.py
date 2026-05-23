"""
Source Quality Filter v1
Strategy ID: source_quality_filter_v1
Purpose: Eliminate toxic sources and amplify top performing sources

Evidence: 5.96% performance spread between best and worst sources
Blocked Sources:
- volume_spike_breakout: 9.4% WR, -2.03% avg PnL
- stochrsi_macd_combo: 0.0% WR, -2.00% avg PnL
- ml_enhanced_TRXUSDT: 0.0% WR, -0.79% avg PnL

Amplified Sources (+50% allocation):
- breakout_b_ml: 87.5% WR, +3.93% avg PnL
- kimi_signal_tracking: 61.5% WR, +3.66% avg PnL
- ml_crypto_pred: 89.3% WR, +2.58% avg PnL
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Set
from dataclasses import dataclass


@dataclass
class FilterResult:
    passed: bool
    adjusted_score: float
    reason: str


class SourceQualityFilter:
    def __init__(self):
        # Hard blocked sources (toxic - zero redeeming value)
        self.blocked_sources: Set[str] = {
            "volume_spike_breakout",
            "stochrsi_macd_combo",
            "ml_enhanced_TRXUSDT_1d_B_lightgbm",
        }

        # Top sources to amplify (+50% score bonus)
        self.amplified_sources: Dict[str, float] = {
            "breakout_b_ml": 1.5,
            "kimi_signal_tracking": 1.5,
            "ml_crypto_pred": 1.5,
            "revival_all": 1.4,
            "chatgpt_combined": 1.4,
            "luxalgo_filters": 1.4,
            "rl_agent": 1.4,
        }

        # Underperforming sources (-20% score penalty)
        self.penalized_sources: Dict[str, float] = {
            "quan_engine": 0.8,
            "alpha_engine_fast": 0.8,
        }

        self.min_acceptable_score = 40  # Hard floor per TESTING_PROTOCOL.MD

    def filter_signal(self, signal: Dict) -> FilterResult:
        """Apply source quality filtering to a single signal"""
        source = signal.get("source", "").lower()

        # Hard block toxic sources
        if source in self.blocked_sources:
            return FilterResult(
                passed=False,
                adjusted_score=0.0,
                reason=f"Source {source} is blocked (toxic performance)",
            )

        # Check score floor
        base_score = signal.get("score", 0)
        if base_score < self.min_acceptable_score:
            return FilterResult(
                passed=False,
                adjusted_score=base_score,
                reason=f"Score {base_score} below minimum threshold {self.min_acceptable_score}",
            )

        # Apply amplification/penalty weights
        adjusted_score = base_score
        reason = "Passed base quality check"

        if source in self.amplified_sources:
            multiplier = self.amplified_sources[source]
            adjusted_score = base_score * multiplier
            reason = f"Amplified top source {source} (multiplier {multiplier})"
        elif source in self.penalized_sources:
            multiplier = self.penalized_sources[source]
            adjusted_score = base_score * multiplier
            reason = (
                f"Penalized underperforming source {source} (multiplier {multiplier})"
            )

        # Cap adjusted score at 99
        adjusted_score = min(adjusted_score, 99.0)

        return FilterResult(passed=True, adjusted_score=adjusted_score, reason=reason)

    def filter_batch(self, signals: List[Dict]) -> List[Dict]:
        """Filter a batch of signals and adjust scores"""
        filtered = []

        for sig in signals:
            result = self.filter_signal(sig)
            if result.passed:
                sig_copy = sig.copy()
                sig_copy["original_score"] = sig.get("score", 0)
                sig_copy["score"] = result.adjusted_score
                sig_copy["quality_filter_reason"] = result.reason
                filtered.append(sig_copy)

        # Sort by adjusted score descending
        filtered.sort(key=lambda x: x["score"], reverse=True)

        return filtered

    def get_stats(self) -> Dict:
        return {
            "blocked_sources_count": len(self.blocked_sources),
            "amplified_sources_count": len(self.amplified_sources),
            "penalized_sources_count": len(self.penalized_sources),
            "min_acceptable_score": self.min_acceptable_score,
        }


if __name__ == "__main__":
    filter = SourceQualityFilter()
    stats = filter.get_stats()
    print(f"Source Quality Filter v1 initialized")
    print(f"Blocked sources: {stats['blocked_sources_count']}")
    print(f"Amplified sources: {stats['amplified_sources_count']}")
    print(f"Penalized sources: {stats['penalized_sources_count']}")
    print(f"Score floor: {stats['min_acceptable_score']}")
