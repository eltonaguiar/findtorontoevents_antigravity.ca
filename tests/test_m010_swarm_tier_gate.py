"""Tests for M-010: Single-persona swarm tier-gate.

Verifies passes_tier_gate() in tools/swarm/swarm_pick_schema.py.
"""
import os
import sys
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools.swarm.swarm_pick_schema import passes_tier_gate, derive_consensus_tier


def _pick(tier):
    return {"consensus_tier": tier}


def test_unanimous_passes_strong_gate():
    """unanimous tier must pass a 'strong' min_tier gate."""
    assert passes_tier_gate(_pick("unanimous"), min_tier="strong") is True


def test_strong_passes_strong_gate():
    """strong tier must pass a 'strong' min_tier gate."""
    assert passes_tier_gate(_pick("strong"), min_tier="strong") is True


def test_moderate_fails_strong_gate():
    """moderate tier must fail a 'strong' min_tier gate."""
    assert passes_tier_gate(_pick("moderate"), min_tier="strong") is False


def test_single_fails_strong_gate():
    """single-model tier must fail a 'strong' min_tier gate."""
    assert passes_tier_gate(_pick("single"), min_tier="strong") is False


def test_control_fails_moderate_gate():
    """control (no model vote) must fail a 'moderate' min_tier gate."""
    assert passes_tier_gate(_pick("control"), min_tier="moderate") is False


def test_moderate_passes_moderate_gate():
    """moderate tier must pass a 'moderate' min_tier gate."""
    assert passes_tier_gate(_pick("moderate"), min_tier="moderate") is True


def test_kill_switch_always_passes():
    """SWARM_TIER_GATE_ENABLED=0 must always pass regardless of tier."""
    with patch.dict(os.environ, {"SWARM_TIER_GATE_ENABLED": "0"}):
        assert passes_tier_gate(_pick("control"), min_tier="unanimous") is True


def test_unknown_tier_fails():
    """Unknown tier value must fail the gate."""
    assert passes_tier_gate(_pick("UNKNOWN_TIER"), min_tier="moderate") is False


def test_derive_and_gate_integration():
    """derive_consensus_tier() output must work correctly with passes_tier_gate()."""
    tier = derive_consensus_tier(consensus_score=0.90, models_voted=4)
    assert tier == "strong"
    assert passes_tier_gate({"consensus_tier": tier}, min_tier="strong") is True

    tier_low = derive_consensus_tier(consensus_score=0.40, models_voted=1)
    assert tier_low == "single"
    assert passes_tier_gate({"consensus_tier": tier_low}, min_tier="strong") is False
