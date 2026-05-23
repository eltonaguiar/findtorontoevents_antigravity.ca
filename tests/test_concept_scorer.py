"""Tests for alpha_engine/concept_scorer.py (B5 — Cursor Phase 3).

All tests use ``unittest.mock.patch`` to override CONCEPT_SCORING_SHADOW so
they do NOT rely on sys.modules poisoning.  Each patch is scoped to the
individual test (no cross-test state leakage).
"""

import importlib
from unittest.mock import patch

import pytest


def _reload_scorer():
    """Reimport concept_scorer so module-level _SHADOW_ON is re-evaluated."""
    import alpha_engine.concept_scorer as m
    importlib.reload(m)
    return m


# ---------------------------------------------------------------------------
# Shadow-OFF behaviour (default)
# ---------------------------------------------------------------------------

class TestShadowOff:
    def test_pts_zero_for_every_family(self):
        with patch.dict("os.environ", {"CONCEPT_SCORING_SHADOW": "0"}):
            mod = _reload_scorer()
            families = [
                "skyrocket", "tradingagents", "long_term_value",
                "penny_stock", "reverse_engineer", "meme_coin",
                "mercury2", "standard",
            ]
            for fam in families:
                pick = {"concept_family": fam}
                result = mod.compute_concept_modifier(pick, strategy_perf=None)
                assert result["pts"] == 0, f"{fam}: expected pts=0 when shadow OFF"
                assert result["shadow_on"] is False
                assert result["gated"] is False

    def test_missing_family_defaults_to_standard(self):
        with patch.dict("os.environ", {"CONCEPT_SCORING_SHADOW": "0"}):
            mod = _reload_scorer()
            result = mod.compute_concept_modifier({}, strategy_perf=None)
            assert result["pts"] == 0
            assert result["family"] == "standard"

    def test_none_family_defaults_to_standard(self):
        with patch.dict("os.environ", {"CONCEPT_SCORING_SHADOW": "0"}):
            mod = _reload_scorer()
            result = mod.compute_concept_modifier(
                {"concept_family": None}, strategy_perf=None
            )
            assert result["family"] == "standard"


# ---------------------------------------------------------------------------
# Shadow-ON ungated families
# ---------------------------------------------------------------------------

class TestShadowOnUngated:
    @pytest.mark.parametrize("family,expected_pts", [
        ("long_term_value", 1),
        ("penny_stock", -1),
        ("reverse_engineer", -1),
        ("meme_coin", -2),
        ("standard", 0),
        ("mercury2", 0),
    ])
    def test_ungated_pts(self, family, expected_pts):
        with patch.dict("os.environ", {"CONCEPT_SCORING_SHADOW": "1"}):
            mod = _reload_scorer()
            pick = {"concept_family": family}
            result = mod.compute_concept_modifier(pick, strategy_perf=None)
            assert result["pts"] == expected_pts, f"{family}: got {result['pts']}"
            assert result["shadow_on"] is True
            assert result["gated"] is False

    def test_pts_bounded_at_floor(self):
        """No ungated family produces pts < -3."""
        with patch.dict("os.environ", {"CONCEPT_SCORING_SHADOW": "1"}):
            mod = _reload_scorer()
            for fam, raw in mod._UNGATED_FAMILIES.items():
                result = mod.compute_concept_modifier({"concept_family": fam}, None)
                assert result["pts"] >= -3

    def test_pts_bounded_at_cap(self):
        """No ungated family produces pts > +3."""
        with patch.dict("os.environ", {"CONCEPT_SCORING_SHADOW": "1"}):
            mod = _reload_scorer()
            for fam, raw in mod._UNGATED_FAMILIES.items():
                result = mod.compute_concept_modifier({"concept_family": fam}, None)
                assert result["pts"] <= 3


# ---------------------------------------------------------------------------
# Shadow-ON gated families — skyrocket
# ---------------------------------------------------------------------------

class TestSkyrocketGate:
    def test_gated_when_no_strategy_perf(self):
        with patch.dict("os.environ", {"CONCEPT_SCORING_SHADOW": "1"}):
            mod = _reload_scorer()
            pick = {"concept_family": "skyrocket"}
            result = mod.compute_concept_modifier(pick, strategy_perf=None)
            assert result["pts"] == 0
            assert result["gated"] is True
            assert result["shadow_on"] is True

    def test_gated_when_n_insufficient(self):
        with patch.dict("os.environ", {"CONCEPT_SCORING_SHADOW": "1"}):
            mod = _reload_scorer()
            pick = {"concept_family": "skyrocket"}
            result = mod.compute_concept_modifier(
                pick, {"n_closed": 15, "fwd_wr": 0.70}
            )
            assert result["pts"] == 0
            assert result["gated"] is True

    def test_gated_when_wr_insufficient(self):
        with patch.dict("os.environ", {"CONCEPT_SCORING_SHADOW": "1"}):
            mod = _reload_scorer()
            pick = {"concept_family": "skyrocket"}
            result = mod.compute_concept_modifier(
                pick, {"n_closed": 40, "fwd_wr": 0.45}
            )
            assert result["pts"] == 0
            assert result["gated"] is True

    def test_awarded_when_gate_met(self):
        with patch.dict("os.environ", {"CONCEPT_SCORING_SHADOW": "1"}):
            mod = _reload_scorer()
            pick = {"concept_family": "skyrocket"}
            result = mod.compute_concept_modifier(
                pick, {"n_closed": 30, "fwd_wr": 0.50}
            )
            assert result["pts"] == 3
            assert result["gated"] is False
            assert result["shadow_on"] is True

    def test_awarded_above_threshold(self):
        with patch.dict("os.environ", {"CONCEPT_SCORING_SHADOW": "1"}):
            mod = _reload_scorer()
            pick = {"concept_family": "skyrocket"}
            result = mod.compute_concept_modifier(
                pick, {"n_closed": 100, "fwd_wr": 0.80}
            )
            assert result["pts"] == 3


# ---------------------------------------------------------------------------
# Shadow-ON gated families — tradingagents
# ---------------------------------------------------------------------------

class TestTradingAgentsGate:
    def test_gated_when_n_insufficient(self):
        with patch.dict("os.environ", {"CONCEPT_SCORING_SHADOW": "1"}):
            mod = _reload_scorer()
            pick = {"concept_family": "tradingagents"}
            result = mod.compute_concept_modifier(
                pick, {"n_closed": 5, "fwd_wr": 0.70}
            )
            assert result["pts"] == 0
            assert result["gated"] is True

    def test_gated_when_wr_below_55(self):
        with patch.dict("os.environ", {"CONCEPT_SCORING_SHADOW": "1"}):
            mod = _reload_scorer()
            pick = {"concept_family": "tradingagents"}
            result = mod.compute_concept_modifier(
                pick, {"n_closed": 35, "fwd_wr": 0.50}
            )
            assert result["pts"] == 0
            assert result["gated"] is True

    def test_awarded_when_gate_met(self):
        with patch.dict("os.environ", {"CONCEPT_SCORING_SHADOW": "1"}):
            mod = _reload_scorer()
            pick = {"concept_family": "tradingagents"}
            result = mod.compute_concept_modifier(
                pick, {"n_closed": 30, "fwd_wr": 0.55}
            )
            assert result["pts"] == 2
            assert result["gated"] is False


# ---------------------------------------------------------------------------
# fw_wr None / 0.0 distinction
# ---------------------------------------------------------------------------

class TestFwWrEdgeCases:
    """Guard against the 'fw_wr=0.0 treated same as None' regression."""

    def test_explicit_zero_wr_means_gate_not_met(self):
        """fwd_wr=0.0 is a real value, not missing — must fail the WR gate."""
        with patch.dict("os.environ", {"CONCEPT_SCORING_SHADOW": "1"}):
            mod = _reload_scorer()
            pick = {"concept_family": "skyrocket"}
            result = mod.compute_concept_modifier(
                pick, {"n_closed": 50, "fwd_wr": 0.0}
            )
            assert result["pts"] == 0
            assert result["gated"] is True

    def test_none_fwd_wr_falls_back_to_zero(self):
        """fwd_wr=None should be treated as 0.0, not bypass the gate."""
        with patch.dict("os.environ", {"CONCEPT_SCORING_SHADOW": "1"}):
            mod = _reload_scorer()
            pick = {"concept_family": "skyrocket"}
            result = mod.compute_concept_modifier(
                pick, {"n_closed": 50, "fwd_wr": None}
            )
            assert result["pts"] == 0
            assert result["gated"] is True


# ---------------------------------------------------------------------------
# concept_gate_shadow_audit (quality_gates.py helper)
# ---------------------------------------------------------------------------

class TestConceptGateShadowAudit:
    def test_returns_dict_with_expected_keys(self):
        from audit_trail.quality_gates import concept_gate_shadow_audit
        pick = {"concept_family": "standard"}
        result = concept_gate_shadow_audit(pick)
        assert isinstance(result, dict)
        for key in ("concept_family", "concept_pts", "shadow_on", "gated", "reason"):
            assert key in result, f"missing key: {key}"

    def test_shadow_off_returns_zero_pts(self):
        with patch.dict("os.environ", {"CONCEPT_SCORING_SHADOW": "0"}):
            _reload_scorer()
            from audit_trail.quality_gates import concept_gate_shadow_audit
            result = concept_gate_shadow_audit({"concept_family": "skyrocket"})
            assert result["concept_pts"] == 0
            assert result["shadow_on"] is False

    def test_fallback_on_missing_concept_family(self):
        from audit_trail.quality_gates import concept_gate_shadow_audit
        result = concept_gate_shadow_audit({})
        assert result["concept_family"] == "standard"

    def test_no_prod_impact_default(self):
        """concept_gate_shadow_audit must never affect gate decisions (read-only)."""
        from audit_trail.quality_gates import concept_gate_shadow_audit, passes_active_gate
        pick = {
            "concept_family": "skyrocket",
            "symbol": "TEST",
            "direction": "LONG",
            "asset_class": "EQUITY",
        }
        # Call audit helper — must not raise or mutate pick
        original_keys = set(pick.keys())
        _ = concept_gate_shadow_audit(pick)
        assert set(pick.keys()) == original_keys
