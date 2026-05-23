"""Phase A: verify classify_pick_quality_v2 delegates to production gates."""

import os
import unittest
from datetime import datetime, timezone

from audit_trail.quality_gates import (
    classify_pick_quality_v2,
    passes_active_gate,
    passes_smart_gate,
)


def _base_pick(**overrides):
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
        "confidence": 0.75,  # <=0.85: CRYPTO_HIGH_CONF_GUARD blocks >0.85 (added 2026-05-14)
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "SWING",
        "rr_ratio": 2.0,
        # PR #644 (2026-05-03 per-asset quality gate) added an explicit
        # forward_validated=True requirement at the top of passes_smart_gate.
        # Test fixtures must opt in or the smart-gate short-circuits to False.
        "forward_validated": True,
        "forward_trades": 30,
        "forward_wr": 0.65,
        "strat_fwd_trades": 30,
        "strat_fwd_wr": 0.65,
    }
    pick.update(overrides)
    return pick


class ClassifyPickQualityV2Tests(unittest.TestCase):
    def test_rejected_when_no_symbol(self):
        pick = _base_pick(symbol="")
        self.assertFalse(passes_active_gate(dict(pick, status="ACTIVE")))
        self.assertEqual(classify_pick_quality_v2(pick), "REJECTED")

    def test_smart_when_passes_smart_gate(self):
        pick = _base_pick()
        # Sanity: this fixture must actually clear the smart gate.
        self.assertTrue(passes_smart_gate(dict(pick, status="ACTIVE")))
        self.assertEqual(classify_pick_quality_v2(pick), "SMART")

    def test_active_when_crypto_short(self):
        # CRYPTO SHORT is explicitly blocked from SMART (LONG-only rule)
        # but still passes the active gate.
        # 2026-05-13: CRYPTO_SHORT_REGIME_GATE_ENABLED defaults to ON; pin
        # disabled here so this test isolates the LONG-only SMART exclusion
        # from the regime gate.
        os.environ["CRYPTO_SHORT_REGIME_GATE_ENABLED"] = "0"
        try:
            pick = _base_pick(direction="SHORT", entry_price=100.0,
                              take_profit=90.0, stop_loss=105.0)
            p2 = dict(pick, status="ACTIVE")
            self.assertTrue(passes_active_gate(p2))
            self.assertFalse(passes_smart_gate(p2))
            self.assertEqual(classify_pick_quality_v2(pick), "ACTIVE")
        finally:
            os.environ.pop("CRYPTO_SHORT_REGIME_GATE_ENABLED", None)

    def test_evaluates_closed_picks_at_issue(self):
        # Closed pick (LOST) should still be classifiable via v2.
        pick = _base_pick(status="LOST")
        self.assertEqual(classify_pick_quality_v2(pick), "SMART")


if __name__ == "__main__":
    unittest.main()
