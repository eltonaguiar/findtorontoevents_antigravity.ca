"""Phase 1 feed-membership stamping tests.

Covers:
  * is_smart_pick_per_pick — None when strategy missing; True on canonical
    PROVEN LONG crypto; False on crypto SHORT (LONG-only rule)
  * is_verified_alpha_per_pick — True/False by allow-list membership
  * evaluate_hc_tier — grade-* when criteria met, None otherwise
  * at_issue_* idempotency — twin fields frozen after first ACTIVE->CLOSED
    snapshot and do not drift when stamp_picks is called again.
"""

import unittest
from datetime import datetime, timezone

from audit_trail.feed_membership import (
    VERIFIED_ALPHA_SOURCES,
    evaluate_hc_tier,
    is_smart_pick_per_pick,
    is_verified_alpha_per_pick,
)
from audit_trail.stamp_pick_quality import stamp_picks


def _base_pick(**overrides):
    # Mirrors tests/test_classify_pick_quality_v2.py::_base_pick so the
    # Smart-gate fixture is known to clear the gate.
    pick = {
        "id": "pick-1",
        "symbol": "BTCUSDT",
        "asset_class": "CRYPTO",
        "source_system": "pm_whale_signals",
        "strategy": "pm_whale_0xeee92f",
        "status": "OPEN",
        "direction": "LONG",
        "entry_price": 100.0,
        "take_profit": 110.0,
        "stop_loss": 95.0,
        "score": 65,
        "trust_score": 6,
        "trust_label": "MODERATE",
        "trust_tier": "PROVEN",
        "source_tier": "PROVEN",
        "confidence": 0.80,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "SWING",
        "rr_ratio": 2.0,
        # PR #644 (per-asset-class smart-gate) added a forward_validated=True
        # requirement at the top of passes_smart_gate; fixtures must opt in
        # or the smart-gate short-circuits to False. forward_wr/trades meet
        # the per-class CRYPTO floor (min_fwr=0.62, min_trades=10) in
        # ASSET_CLASS_SMART_THRESHOLDS. Mirrors the fixture sweep in
        # tests/test_classify_pick_quality_v2.py post-#660/#644.
        "forward_validated": True,
        "forward_trades": 30,
        "forward_wr": 0.65,
        "strat_fwd_trades": 30,
        "strat_fwd_wr": 0.65,
    }
    pick.update(overrides)
    return pick


class IsSmartPickPerPickTests(unittest.TestCase):
    def test_none_when_strategy_missing(self):
        p = _base_pick(strategy="")
        self.assertIsNone(is_smart_pick_per_pick(p))

    def test_true_on_proven_long_crypto_swing(self):
        p = _base_pick()  # LONG, SWING, score 65, PROVEN, conf 0.88, RR 2.0
        self.assertTrue(is_smart_pick_per_pick(p))

    def test_false_on_crypto_short(self):
        # SMART_PICKS_CRYPTO_LONG_ONLY blocks SHORT crypto from Smart Picks.
        p = _base_pick(
            direction="SHORT",
            entry_price=100.0,
            take_profit=90.0,
            stop_loss=105.0,
        )
        self.assertFalse(is_smart_pick_per_pick(p))


class IsVerifiedAlphaPerPickTests(unittest.TestCase):
    def test_true_when_proven_and_in_allowlist(self):
        # Pick any source currently in VERIFIED_ALPHA_SOURCES
        allowed = next(iter(VERIFIED_ALPHA_SOURCES))
        p = _base_pick(trust_tier="PROVEN", source_system=allowed)
        self.assertTrue(is_verified_alpha_per_pick(p))

    def test_false_when_proven_but_not_in_allowlist(self):
        p = _base_pick(trust_tier="PROVEN", source_system="not_in_allowlist_xyz")
        self.assertFalse(is_verified_alpha_per_pick(p))

    def test_false_when_source_allowed_but_not_proven(self):
        allowed = next(iter(VERIFIED_ALPHA_SOURCES))
        p = _base_pick(trust_tier="WATCH", source_system=allowed)
        self.assertFalse(is_verified_alpha_per_pick(p))


class EvaluateHcTierTests(unittest.TestCase):
    def test_non_none_when_criteria_met(self):
        p = _base_pick(score=75, trust_tier="PROVEN", confidence=0.85)
        tier = evaluate_hc_tier(p)
        self.assertIn(tier, {"grade-a", "grade-b"})

    def test_none_when_score_too_low(self):
        p = _base_pick(score=30, trust_tier="PROVEN", confidence=0.85)
        self.assertIsNone(evaluate_hc_tier(p))

    def test_none_when_trust_not_reliable_or_proven(self):
        p = _base_pick(score=80, trust_tier="WATCH", confidence=0.90)
        self.assertIsNone(evaluate_hc_tier(p))

    def test_none_when_confidence_too_low(self):
        p = _base_pick(score=80, trust_tier="PROVEN", confidence=0.50)
        self.assertIsNone(evaluate_hc_tier(p))


class AtIssueIdempotencyTests(unittest.TestCase):
    def test_at_issue_twins_frozen_across_repeated_stamps(self):
        # CLOSED/WON pick — first stamp should snapshot at_issue_* twins.
        p = _base_pick(status="WON")
        picks = [p]
        stamp_picks(picks, strategy_stats={}, dry_run=True)

        self.assertIn("at_issue_is_smart_pick", p)
        self.assertIn("at_issue_is_verified_alpha", p)
        self.assertIn("at_issue_hc_tier", p)

        frozen_smart = p["at_issue_is_smart_pick"]
        frozen_va = p["at_issue_is_verified_alpha"]
        frozen_hc = p["at_issue_hc_tier"]

        # Mutate the "live" inputs that feed the evaluators — the at_issue_*
        # twins must NOT move.
        p["trust_tier"] = "AVOID"
        p["score"] = 5
        p["confidence"] = 0.05
        p["source_system"] = "some_other_source"

        stamp_picks(picks, strategy_stats={}, dry_run=True)

        self.assertEqual(p["at_issue_is_smart_pick"], frozen_smart)
        self.assertEqual(p["at_issue_is_verified_alpha"], frozen_va)
        self.assertEqual(p["at_issue_hc_tier"], frozen_hc)


if __name__ == "__main__":
    unittest.main()
