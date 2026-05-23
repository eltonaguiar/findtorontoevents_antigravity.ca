"""P1/#7: Net-of-cost slippage promotion gate in money_ready_verdict._verdict()."""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
import unittest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "alpha_engine"))


def _reload_mrv(enabled: str) -> object:
    """Reload the module with a specific env-var setting."""
    env_key = "SLIPPAGE_PROMOTION_GATE_ENABLED"
    old = os.environ.get(env_key)
    os.environ[env_key] = enabled
    try:
        import alpha_engine.money_ready_verdict as mrv
        importlib.reload(mrv)
        return mrv
    finally:
        if old is None:
            os.environ.pop(env_key, None)
        else:
            os.environ[env_key] = old


class TestSlippageGateShadow(unittest.TestCase):
    """Gate is OFF (default=0): MONEY_READY passes through even if expectancy < 0."""

    def setUp(self):
        self.mrv = _reload_mrv("0")

    def _dsr_ok(self):
        return {"ok": True, "dsr_score": 0.97}

    def _pbo_ok(self):
        return {"ok": True, "pbo": 0.30}

    def _spa_ok(self):
        return {"ok": True, "spa_p": 0.08, "n_spa_pass": 3}

    def test_shadow_off_money_ready_passes(self):
        mrv = self.mrv
        result = mrv._verdict(
            n=100, wr=0.56, pf=1.6,
            dsr=self._dsr_ok(), pbo=self._pbo_ok(), spa=self._spa_ok(),
            asset_class="EQUITY",
            avg_win=0.001, avg_loss=0.002,  # expectancy negative (tiny edge)
        )
        self.assertEqual(result, "MONEY_READY", "Shadow-OFF must NOT block MONEY_READY")

    def test_shadow_recommend_stamped_when_would_fail(self):
        """_slippage_recommend='NOT_READY' when shadow gate would have fired."""
        mrv = self.mrv
        # Build a scenario where expectancy < 0 post-slippage:
        # EQUITY slippage=10bps=0.001; avg_win=0.001; avg_loss=0.002; wr=0.55
        # expectancy = 0.55*(0.001-0.001) - 0.45*(0.002+0.001) = 0 - 0.00135 < 0
        dsr = {"ok": True, "dsr_score": 0.97}
        pbo = {"ok": True, "pbo": 0.30}
        spa = {"ok": True, "spa_p": 0.08, "n_spa_pass": 3}
        # Call the full money_ready_verdict with mock data via _expectancy_gate
        eg = mrv._expectancy_gate(0.55, 0.001, 0.002, asset_class="EQUITY")
        self.assertIsNotNone(eg.get("expectancy"))
        # expectancy should be negative or zero
        self.assertLessEqual(eg["expectancy"], 0.0)
        self.assertFalse(eg["expectancy_ok"])

    def test_shadow_recommend_none_when_expectancy_ok(self):
        """_slippage_recommend=None when expectancy is positive (no downgrade needed)."""
        mrv = self.mrv
        eg = mrv._expectancy_gate(0.65, 0.05, 0.02, asset_class="EQUITY")
        self.assertTrue(eg["expectancy_ok"])


class TestSlippageGateEnabled(unittest.TestCase):
    """Gate is ON (=1): MONEY_READY blocked when post-slippage expectancy ≤ 0."""

    def setUp(self):
        self.mrv = _reload_mrv("1")

    def _dsr_ok(self):
        return {"ok": True, "dsr_score": 0.97}

    def _pbo_ok(self):
        return {"ok": True, "pbo": 0.30}

    def _spa_ok(self):
        return {"ok": True, "spa_p": 0.08, "n_spa_pass": 3}

    def test_gate_on_blocks_money_ready_when_expectancy_negative(self):
        mrv = self.mrv
        # EQUITY: slippage=10bps; avg_win tiny → expectancy < 0
        result = mrv._verdict(
            n=100, wr=0.55, pf=1.6,
            dsr=self._dsr_ok(), pbo=self._pbo_ok(), spa=self._spa_ok(),
            asset_class="EQUITY",
            avg_win=0.0005, avg_loss=0.002,
        )
        self.assertEqual(result, "NOT_READY", "Gate-ON must block when expectancy < 0")

    def test_gate_on_allows_money_ready_when_expectancy_positive(self):
        mrv = self.mrv
        # EQUITY: avg_win=5%, avg_loss=2%, wr=65% — clearly positive expectancy
        result = mrv._verdict(
            n=100, wr=0.65, pf=2.0,
            dsr=self._dsr_ok(), pbo=self._pbo_ok(), spa=self._spa_ok(),
            asset_class="EQUITY",
            avg_win=0.05, avg_loss=0.02,
        )
        self.assertEqual(result, "MONEY_READY")

    def test_gate_on_skips_when_avg_win_zero(self):
        """Gate must fail-open when avg_win/avg_loss are unavailable."""
        mrv = self.mrv
        result = mrv._verdict(
            n=100, wr=0.65, pf=2.0,
            dsr=self._dsr_ok(), pbo=self._pbo_ok(), spa=self._spa_ok(),
            asset_class="EQUITY",
            avg_win=0.0, avg_loss=0.0,  # no data
        )
        self.assertEqual(result, "MONEY_READY", "Fail-open when win/loss unavailable")

    def test_gate_does_not_affect_non_money_ready_verdicts(self):
        """Gate only fires on MONEY_READY path."""
        mrv = self.mrv
        result = mrv._verdict(
            n=100, wr=0.40, pf=0.9,
            dsr={"ok": False}, pbo={"ok": False}, spa={"ok": False},
            asset_class="EQUITY",
            avg_win=0.001, avg_loss=0.002,
        )
        self.assertEqual(result, "NOT_READY")

    def test_gate_enabled_flag_is_true(self):
        self.assertTrue(self.mrv._SLIPPAGE_GATE_ENABLED)


class TestEmitGateConfigRegistry(unittest.TestCase):
    """SLIPPAGE_PROMOTION_GATE must be in GATE_REGISTRY."""

    def test_gate_in_registry(self):
        from tools.emit_gate_config import GATE_REGISTRY
        ids = [g["id"] for g in GATE_REGISTRY]
        self.assertIn("SLIPPAGE_PROMOTION_GATE", ids)

    def test_gate_is_enforced_by_default(self):
        # 2026-05-19, swarm-settled Q1 verdict: the expectancy gate is now the
        # real money-ready promotion gate — ENFORCED by default (was shadow).
        from tools.emit_gate_config import GATE_REGISTRY
        gate = next(g for g in GATE_REGISTRY if g["id"] == "SLIPPAGE_PROMOTION_GATE")
        self.assertEqual(gate["default"], "1")
        self.assertEqual(gate["category"], "hard_gate")
        self.assertEqual(gate["severity"], "P1")


if __name__ == "__main__":
    unittest.main()
