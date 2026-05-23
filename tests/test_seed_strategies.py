"""
Tests for genome.seed_strategies — 4-Island Seed Strategy Definitions
"""

import sys
import os
import importlib.util
from pathlib import Path

import pytest

# Ensure the genome/logs directory exists (dna_engine sets up a FileHandler)
_genome_dir = Path(__file__).resolve().parent.parent / "genome"
(_genome_dir / "logs").mkdir(parents=True, exist_ok=True)

# Import dna_engine directly to avoid genome.__init__ pulling in pandas/heavy deps
_de_spec = importlib.util.spec_from_file_location(
    "genome.dna_engine",
    _genome_dir / "dna_engine.py",
)
_de_mod = importlib.util.module_from_spec(_de_spec)
sys.modules["genome.dna_engine"] = _de_mod
_de_spec.loader.exec_module(_de_mod)
StrategyDNA = _de_mod.StrategyDNA
create_strategy_dna = _de_mod.create_strategy_dna

# Now import seed_strategies (it imports from genome.dna_engine which we just registered)
_ss_spec = importlib.util.spec_from_file_location(
    "genome.seed_strategies",
    _genome_dir / "seed_strategies.py",
)
_ss_mod = importlib.util.module_from_spec(_ss_spec)
sys.modules["genome.seed_strategies"] = _ss_mod
_ss_spec.loader.exec_module(_ss_mod)

ISLAND_CONFIGS = _ss_mod.ISLAND_CONFIGS
get_island_seeds = _ss_mod.get_island_seeds
get_all_island_seeds = _ss_mod.get_all_island_seeds


# ------------------------------------------------------------------ #
#  Island configuration tests
# ------------------------------------------------------------------ #

def test_four_islands_defined():
    """ISLAND_CONFIGS has exactly 4 keys: bear, bull, range, recent."""
    assert len(ISLAND_CONFIGS) == 4
    assert set(ISLAND_CONFIGS.keys()) == {"bear", "bull", "range", "recent"}


def test_each_island_has_seeds():
    """Every island must have at least 3 seed strategies."""
    for name, config in ISLAND_CONFIGS.items():
        assert len(config["seeds"]) >= 3, f"Island {name} needs >= 3 seeds"


def test_each_island_has_description_and_mutation_bias():
    """Every island config should have description and mutation_bias."""
    for name, config in ISLAND_CONFIGS.items():
        assert "description" in config, f"Island {name} missing description"
        assert "mutation_bias" in config, f"Island {name} missing mutation_bias"


# ------------------------------------------------------------------ #
#  Seed generation tests
# ------------------------------------------------------------------ #

def test_get_island_seeds_returns_strategy_dna():
    """Each seed should be a StrategyDNA with non-empty genes."""
    for island_name in ISLAND_CONFIGS:
        seeds = get_island_seeds(island_name)
        assert len(seeds) >= 3
        for s in seeds:
            assert isinstance(s, StrategyDNA)
            assert s.genes


def test_get_all_island_seeds():
    """get_all_island_seeds returns a dict with all 4 islands."""
    all_seeds = get_all_island_seeds()
    assert set(all_seeds.keys()) == {"bear", "bull", "range", "recent"}
    for island_name, seeds in all_seeds.items():
        assert len(seeds) >= 3


def test_invalid_island_raises():
    """Requesting a non-existent island should raise KeyError."""
    with pytest.raises(KeyError):
        get_island_seeds("nonexistent_island")


# ------------------------------------------------------------------ #
#  Island-specific strategy character tests
# ------------------------------------------------------------------ #

def test_bear_island_has_defensive_seeds():
    """Bear island should contain mean-reversion or oversold entry logic."""
    seeds = get_island_seeds("bear")
    entry_logics = [s.genes.get("entry_logic", "") for s in seeds]
    assert any("mean_reversion" in e or "oversold" in e for e in entry_logics)


def test_bull_island_has_momentum_seeds():
    """Bull island should contain momentum, breakout, or golden_cross entry logic."""
    seeds = get_island_seeds("bull")
    entry_logics = [s.genes.get("entry_logic", "") for s in seeds]
    assert any("momentum" in e or "breakout" in e or "golden_cross" in e for e in entry_logics)


def test_recent_island_has_ensemble_seed():
    """Recent island should contain an HMLF/ensemble strategy."""
    seeds = get_island_seeds("recent")
    names = [s.name for s in seeds]
    assert any("hmlf" in n.lower() or "ensemble" in n.lower() for n in names)


def test_range_island_has_mean_reversion():
    """Range island should focus on mean-reversion strategies."""
    seeds = get_island_seeds("range")
    entry_logics = [s.genes.get("entry_logic", "") for s in seeds]
    assert any("mean_reversion" in e or "oversold" in e for e in entry_logics)


# ------------------------------------------------------------------ #
#  Gene integrity tests
# ------------------------------------------------------------------ #

def test_all_seeds_have_expected_wr():
    """Every seed strategy should carry an expected_wr gene."""
    for island_name in ISLAND_CONFIGS:
        seeds = get_island_seeds(island_name)
        for s in seeds:
            assert "expected_wr" in s.genes, (
                f"Seed {s.name} on island {island_name} missing expected_wr"
            )
            assert 0.0 < s.genes["expected_wr"] < 1.0


def test_all_seeds_have_source():
    """Every seed strategy should carry a source gene for traceability."""
    for island_name in ISLAND_CONFIGS:
        seeds = get_island_seeds(island_name)
        for s in seeds:
            assert "source" in s.genes, (
                f"Seed {s.name} on island {island_name} missing source"
            )


def test_unique_strategy_names_across_islands():
    """No two seeds should share the same name across all islands."""
    all_names = []
    for island_name in ISLAND_CONFIGS:
        seeds = get_island_seeds(island_name)
        all_names.extend(s.name for s in seeds)
    assert len(all_names) == len(set(all_names)), "Duplicate strategy names found"
