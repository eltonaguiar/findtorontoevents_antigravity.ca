"""Strategy generators - rules-based, ML, and hybrid strategies."""
from .base import BaseStrategy
from .generator import StrategyGenerator

# NOTE: unique_algorithmic_strategies import removed 2026-06-01 — the file was
# referenced by commit a57d3d18a ("P0 §15 trap fixes") but never committed,
# causing `ModuleNotFoundError: No module named
# 'alpha_engine.strategies.unique_algorithmic_strategies'` on every import.
# Re-add this import once the file lands.
