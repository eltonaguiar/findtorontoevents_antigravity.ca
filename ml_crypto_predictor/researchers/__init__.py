"""
Multi-Researcher Framework — Academic Deep Learning Approaches
==============================================================

A collaborative multi-agent system where each researcher specializes in a
different academic deep learning methodology for crypto prediction.

Architecture:
  - Base Researcher class with standardized interface
  - Specialized researchers for different approaches:
    * SequenceModelResearcher (LSTM/GRU/CNN temporal models)
    * TransformerResearcher (attention-based architectures)
    * GraphNeuralResearcher (GNN for correlation networks)
    * ContrastiveResearcher (self-supervised representation learning)
    * MetaLearningResearcher (rapid adaptation to new pairs)
    * EnsembleResearcher (sophisticated stacking/blending)
    * RegimeResearcher (market regime detection & adaptation)
    * FeatureResearcher (automated feature engineering)
  - ResearchCoordinator orchestrates collaboration
  - Shared knowledge base and results registry

All researchers follow the academic methodology:
  1. Literature review & hypothesis formulation
  2. Data preparation & experimental design
  3. Model implementation with proper validation
  4. Statistical significance testing
  5. Reproducible reporting

Inspired by: Antigravity AI's institutional-grade research standards.
"""

# Core imports (always available)
from .base import Researcher, ResearchQuestion
from .coordinator import ResearchCoordinator

# Specialized researchers — lazy imports since these may not be implemented yet.
# Without try/except guards, importing ml_crypto_predictor would crash with
# ModuleNotFoundError and break the enhanced_models pipeline in GitHub Actions.
_optional_researchers = {}

def _try_import(name, module_path):
    """Safely import an optional researcher module.

    Catches ImportError/ModuleNotFoundError for missing optional deps,
    and NameError for modules that use type annotations referring to
    optional packages without ``from __future__ import annotations``
    (e.g. ``-> nn.Module`` when torch is missing). Without the NameError
    branch, a single torch-less environment kills the whole package
    import, hiding all working personas.
    """
    try:
        import importlib
        mod = importlib.import_module(module_path, package=__name__)
        cls = getattr(mod, name, None)
        if cls:
            _optional_researchers[name] = cls
            globals()[name] = cls
    except (ImportError, ModuleNotFoundError, NameError):
        pass

_try_import("SequenceModelResearcher", ".sequence_researcher")
_try_import("TransformerResearcher", ".transformer_researcher")
_try_import("GraphNeuralResearcher", ".graph_neural_researcher")
_try_import("ContrastiveResearcher", ".contrastive_researcher")
_try_import("MetaLearningResearcher", ".meta_learning_researcher")
_try_import("EnsembleResearcher", ".ensemble_researcher")
_try_import("RegimeResearcher", ".regime_researcher")
_try_import("FeatureResearcher", ".feature_researcher")
_try_import("MeanReversionResearcher", ".mean_reversion_researcher")
_try_import("MomentumResearcher", ".momentum_researcher")
_try_import("DataQualityResearcher", ".data_quality_researcher")
_try_import("ExecutionResearcher", ".execution_researcher")
_try_import("RiskResearcher", ".risk_researcher")
_try_import("ValidationResearcher", ".validation_researcher")
_try_import("AlternativeDataResearcher", ".alternative_data_researcher")
_try_import("RobustnessResearcher", ".robustness_researcher")
_try_import("GovernanceResearcher", ".governance_researcher")

# Hedge-fund-grade uplift personas (added 2026-05-02, plan Themes A/B/C/D/E/F).
# See updates/2026-05-02-hedge-fund-grade-uplift-foundation.md for the full
# wiring plan and ml_crypto_predictor/researchers/meta_orchestrator_researcher.py
# HANDOFF_MAP for the dynamic-spawn → fixed-persona contract.
_try_import("VolTargetingResearcher", ".vol_targeting_researcher")
_try_import("ReconciliationResearcher", ".reconciliation_researcher")
_try_import("HMMRegimeResearcher", ".hmm_regime_researcher")
_try_import("RiskParityResearcher", ".risk_parity_researcher")
_try_import("FactorOverlayResearcher", ".factor_overlay_researcher")
_try_import("MultipleTestingResearcher", ".multiple_testing_researcher")
_try_import("MetaOrchestratorResearcher", ".meta_orchestrator_researcher")
_try_import("TransactionCostResearcher", ".transaction_cost_researcher")

__all__ = [
    "Researcher",
    "ResearchQuestion",
    "ResearchCoordinator",
] + list(_optional_researchers.keys())
