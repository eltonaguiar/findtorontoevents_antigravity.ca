"""
Tests for tier-gated pick emission in genome.generate_picks

Uses sys.modules mocking to prevent heavy genome imports (pandas etc.)
"""

import sys
import types
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Mock the heavy genome package before importing generate_picks
_genome_mock = MagicMock()
# Provide the names that generate_picks.py imports at module level
_genome_mock.DNAPermutationEngine = MagicMock
_genome_mock.DNABacktester = MagicMock
_genome_mock.StrategyRegistry = MagicMock
_genome_mock.StrategyDNA = MagicMock
_genome_mock.create_strategy_dna = MagicMock()
_genome_mock.CombinationLogic = MagicMock()
_genome_mock.MarketRegime = MagicMock()

sys.modules["genome"] = _genome_mock

# Now load generate_picks without pandas chain
_spec = importlib.util.spec_from_file_location(
    "genome.generate_picks",
    Path(__file__).resolve().parent.parent / "genome" / "generate_picks.py",
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["genome.generate_picks"] = _mod
_spec.loader.exec_module(_mod)

should_emit_pick = _mod.should_emit_pick


# ------------------------------------------------------------------ #
#  should_emit_pick tests
# ------------------------------------------------------------------ #

def test_incubator_not_emitted():
    assert should_emit_pick("INCUBATOR") is False


def test_sandbox_emitted():
    assert should_emit_pick("SANDBOX") is True


def test_fresh_picks_emitted():
    assert should_emit_pick("FRESH_PICKS") is True


def test_dna_master_emitted():
    assert should_emit_pick("DNA_MASTER") is True


def test_unknown_tier_not_emitted():
    assert should_emit_pick(None) is False
