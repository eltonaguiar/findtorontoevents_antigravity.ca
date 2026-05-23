"""
Tests for evolve_strategies.py v2 -- island model + onchain gene wiring.
"""

import sys
import importlib.util
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Import modules via importlib to avoid genome.__init__ pulling pandas
# ---------------------------------------------------------------------------
_genome_dir = Path(__file__).resolve().parent.parent / "genome"


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _genome_dir / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_dna_mod = _load_module("genome.dna_engine", "dna_engine.py")
_reg_mod = _load_module("genome.strategy_registry", "strategy_registry.py")
_seed_mod = _load_module("genome.seed_strategies", "seed_strategies.py")
_oc_mod = _load_module("genome.onchain_data", "onchain_data.py")
_ev_mod = _load_module("genome.evolve_strategies", "evolve_strategies.py")

evolve = _ev_mod.evolve

# Aliases
StrategyDNA = _dna_mod.StrategyDNA
FitnessScore = _dna_mod.FitnessScore
IslandModel = _dna_mod.IslandModel
create_strategy_dna = _dna_mod.create_strategy_dna


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _make_pop(n=6):
    """Build a small population of (StrategyDNA, FitnessScore) tuples."""
    pop = []
    for i in range(n):
        dna = create_strategy_dna(f"test_strat_{i}", timeframe="1h")
        fitness = FitnessScore(overall_fitness=0.5 + 0.01 * i)
        pop.append((dna, fitness))
    return pop


# ---------------------------------------------------------------------------
#  Tests -- Legacy mode
# ---------------------------------------------------------------------------

class TestEvolveLegacyMode:
    """evolve() with use_islands=False should use old path (no IslandModel)."""

    def test_legacy_returns_population_and_history(self):
        pop = _make_pop(6)
        result_pop, result_hist = evolve(
            initial_population=pop,
            generations=1,
            population_size=6,
            mutation_rate=0.1,
            elite_ratio=0.2,
            use_islands=False,
        )
        assert isinstance(result_pop, list)
        assert isinstance(result_hist, list)
        assert len(result_pop) > 0

    def test_legacy_does_not_create_island_model(self):
        pop = _make_pop(6)
        with patch.object(_ev_mod, "IslandModel") as mock_island_cls:
            evolve(
                initial_population=pop,
                generations=1,
                population_size=6,
                use_islands=False,
            )
            mock_island_cls.assert_not_called()


# ---------------------------------------------------------------------------
#  Tests -- Island mode
# ---------------------------------------------------------------------------

class TestEvolveIslandMode:
    """evolve() with use_islands=True should create IslandModel."""

    @patch.object(_ev_mod, "OnchainDataFetcher")
    @patch.object(_ev_mod, "get_all_island_seeds")
    def test_island_mode_creates_island_model(self, mock_seeds, mock_fetcher_cls):
        # Provide minimal seeds so IslandModel can init
        mock_seeds.return_value = {
            "bear": [create_strategy_dna("bear_s", timeframe="1h")],
            "bull": [create_strategy_dna("bull_s", timeframe="1h")],
            "range": [create_strategy_dna("range_s", timeframe="1h")],
            "recent": [create_strategy_dna("recent_s", timeframe="1h")],
        }
        # Mock onchain fetcher
        mock_fetcher_instance = MagicMock()
        mock_fetcher_instance.get_all_genes.return_value = {
            "fear_greed": 50, "funding_rate": 0.0, "ssr": 10.0,
        }
        mock_fetcher_cls.return_value = mock_fetcher_instance

        result_pop, result_hist = evolve(
            generations=2,
            population_size=12,
            use_islands=True,
            use_onchain=True,
        )

        assert isinstance(result_pop, list)
        assert len(result_pop) > 0
        assert isinstance(result_hist, list)
        assert len(result_hist) == 2
        # Seeds were requested
        mock_seeds.assert_called_once()
        # Onchain fetcher was used
        mock_fetcher_cls.assert_called_once()

    @patch.object(_ev_mod, "get_all_island_seeds")
    def test_island_mode_without_onchain(self, mock_seeds):
        mock_seeds.return_value = {
            "bear": [create_strategy_dna("b", timeframe="1h")],
            "bull": [create_strategy_dna("bu", timeframe="1h")],
            "range": [create_strategy_dna("r", timeframe="1h")],
            "recent": [create_strategy_dna("re", timeframe="1h")],
        }
        result_pop, result_hist = evolve(
            generations=1,
            population_size=12,
            use_islands=True,
            use_onchain=False,
        )
        assert isinstance(result_pop, list)
        assert len(result_pop) > 0

    @patch.object(_ev_mod, "get_all_island_seeds")
    def test_island_history_records_per_island_stats(self, mock_seeds):
        mock_seeds.return_value = {
            "bear": [create_strategy_dna("b", timeframe="1h")],
            "bull": [create_strategy_dna("bu", timeframe="1h")],
            "range": [create_strategy_dna("r", timeframe="1h")],
            "recent": [create_strategy_dna("re", timeframe="1h")],
        }
        _, history = evolve(
            generations=3,
            population_size=16,
            use_islands=True,
            use_onchain=False,
        )
        assert len(history) == 3
        for record in history:
            assert "islands" in record
            for name in ("bear", "bull", "range", "recent"):
                assert name in record["islands"]
                assert "mutation_rate" in record["islands"][name]
                assert "stagnation" in record["islands"][name]
