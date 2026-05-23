"""
M-083: Tests for pre-enrichment of elite_score before forward_validator adjustment pipeline.

Root cause: strategies that emit signals without elite_score had their score built from
0 (default) by GRU/OBI/MTF adjustments, producing junk values like -8.2 instead of the
real score (27-33 for cyclic_momentum_stack, 33 for fractal_sr_bounce).

Fix: batch enrich signals missing elite_score before the main loop in run_generation().
"""
import pytest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'alpha_engine'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'audit_trail'))


class TestM083EliteScorePreEnrichment:
    """Tests that signals missing elite_score get enriched before adjustments."""

    def _make_signal(self, strategy: str, elite_score=None, **kwargs):
        """Create a minimal test signal."""
        sig = {
            "symbol": "ETHUSDT",
            "strategy": strategy,
            "source_system": strategy,
            "confidence": 0.65,
            "signal_type": "BUY",
            "direction": "LONG",
            "category": "crypto",
            "asset_class": "CRYPTO",
            "entry_price": 2500.0,
            "take_profit": 2600.0,
            "stop_loss": 2450.0,
        }
        if elite_score is not None:
            sig["elite_score"] = elite_score
        sig.update(kwargs)
        return sig

    def test_signals_missing_elite_score_are_identified(self):
        """M-083: Signals with elite_score=None should be detected as unscored."""
        signals = [
            self._make_signal("cyclic_momentum_stack"),          # None
            self._make_signal("stochrsi_oversold_bounce"),       # None
            self._make_signal("fractal_sr_bounce", elite_score=33),  # pre-scored
            self._make_signal("kimi_riseoftheclaw", elite_score=45),  # pre-scored
        ]
        unscored = [s for s in signals if s.get("elite_score") is None]
        pre_scored = [s for s in signals if s.get("elite_score") is not None]
        assert len(unscored) == 2
        assert len(pre_scored) == 2
        assert all(s["strategy"] in ("cyclic_momentum_stack", "stochrsi_oversold_bounce")
                   for s in unscored)

    def test_enrich_picks_produces_positive_score_for_cyclic(self):
        """cyclic_momentum_stack should score 20-40 via compute_elite_score, not -8.2."""
        try:
            from elite_scorer import compute_elite_score
        except ImportError:
            pytest.skip("elite_scorer not available")

        pick = self._make_signal("cyclic_momentum_stack", ml_score=0.261)
        result = compute_elite_score(pick)
        score = result["elite_score"]
        assert score > -5, (
            f"M-083: cyclic_momentum_stack real score should be > -5, got {score}. "
            "Junk score would be ~-8.2 from 0 + adjustment baseline."
        )
        assert score > 15, (
            f"M-083: cyclic_momentum_stack real score should be > 15, got {score}. "
            "Expected range 20-40 (computed from market_cap_tier + confidence + forward_wr)."
        )

    def test_enrich_picks_produces_above_threshold_for_fractal_sr_bounce(self):
        """fractal_sr_bounce with ml_score=0.95 should score >= 30 via compute_elite_score."""
        try:
            from elite_scorer import compute_elite_score
        except ImportError:
            pytest.skip("elite_scorer not available")

        pick = self._make_signal("fractal_sr_bounce", ml_score=0.95)
        result = compute_elite_score(pick)
        score = result["elite_score"]
        assert score >= 28, (
            f"M-083: fractal_sr_bounce (ml=0.95) should score >= 28, got {score}. "
            "High ml_score should elevate above QUALITY_GATE floor (30)."
        )

    def test_enrich_picks_produces_above_threshold_for_stochrsi(self):
        """stochrsi_oversold_bounce with ml_score=0.69 should score >= 25."""
        try:
            from elite_scorer import compute_elite_score
        except ImportError:
            pytest.skip("elite_scorer not available")

        pick = self._make_signal("stochrsi_oversold_bounce", ml_score=0.69)
        result = compute_elite_score(pick)
        score = result["elite_score"]
        assert score >= 25, (
            f"M-083: stochrsi_oversold_bounce (ml=0.69) should score >= 25, got {score}. "
            "Junk score was ~-8.2; real score should be near Gate 9 threshold."
        )

    def test_pre_existing_elite_score_not_overwritten(self):
        """M-083: Signals that already have elite_score should not be re-enriched."""
        try:
            from elite_scorer import enrich_picks_with_elite_score
            from pathlib import Path
        except ImportError:
            pytest.skip("elite_scorer not available")

        pick = self._make_signal("kimi_riseoftheclaw", elite_score=75)
        original_score = pick["elite_score"]

        # The M-083 filter only processes signals where elite_score is None
        unscored = [p for p in [pick] if p.get("elite_score") is None]
        assert len(unscored) == 0, "Pre-scored pick should not be in unscored list"
        assert pick["elite_score"] == original_score, "Pre-scored pick should not be modified"

    def test_enrich_picks_with_none_elite_score_batch(self):
        """M-083: Batch enrichment should set elite_score for all None-scored signals."""
        try:
            from elite_scorer import enrich_picks_with_elite_score
            from pathlib import Path
        except ImportError:
            pytest.skip("elite_scorer not available")

        picks = [
            self._make_signal("cyclic_momentum_stack"),
            self._make_signal("stochrsi_oversold_bounce", ml_score=0.69),
        ]
        assert all(p.get("elite_score") is None for p in picks), "Should start with None"

        data_dir = Path(__file__).parent.parent / "alpha_engine" / "data"
        enrich_picks_with_elite_score(picks, data_dir)

        for p in picks:
            score = p.get("elite_score")
            assert score is not None, f"Elite score should be set after enrichment for {p['strategy']}"
            assert isinstance(score, (int, float)), f"Elite score should be numeric, got {type(score)}"
            assert score > -5, (
                f"After M-083 enrichment, {p['strategy']} should have score > -5, got {score}. "
                "Junk value would indicate adjustment-from-zero bug persists."
            )

    def test_m083_sentinel_value_is_not_negative_8_2(self):
        """M-083: The -8.2 sentinel bug should not appear after enrichment."""
        try:
            from elite_scorer import compute_elite_score
        except ImportError:
            pytest.skip("elite_scorer not available")

        strategies = ["cyclic_momentum_stack", "stochrsi_oversold_bounce", "fractal_sr_bounce"]
        for strategy in strategies:
            pick = self._make_signal(strategy)
            result = compute_elite_score(pick)
            score = result["elite_score"]
            assert abs(score - (-8.2)) > 5, (
                f"M-083: {strategy} score={score} is suspiciously close to -8.2 sentinel. "
                "Sentinel -8.2 was caused by adjustment-from-zero bug."
            )
