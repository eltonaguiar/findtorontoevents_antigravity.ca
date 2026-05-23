"""
Research Configuration — Settings for the Multi-Researcher Framework
====================================================================

Centralized configuration for the academic deep learning research program.
Controls which researchers are active, resource allocation, and experiment settings.
"""

from pathlib import Path
from typing import Dict, List, Any

# ─── Base Directory ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
RESEARCH_DIR = BASE_DIR / "results" / "research"
COORDINATOR_DIR = RESEARCH_DIR / "coordinator"

# ─── Active Researchers ───────────────────────────────────────────────────────
# Enable/disable specific researchers based on available resources and priorities
ACTIVE_RESEARCHERS = {
    # Deep Learning Architecture Researchers
    "sequence_models": True,      # LSTM/GRU/CNN - high priority
    "transformers": True,         # Attention models - high priority
    "graph_neural": False,       # GNN - requires torch_geometric
    "contrastive": False,        # Self-supervised - experimental
    "meta_learning": False,      # Few-shot - complex, low priority
    "ensemble": True,            # Stacking/boosting - high priority
    
    # Strategy & Signal Researchers
    "momentum": True,            # Trend-following - high priority
    "mean_reversion": True,      # Statistical arbitrage - high priority
    "regime_detection": True,    # Market regimes - high priority
    "feature_engineering": True, # Feature discovery - high priority
    "alternative_data": True,    # Sentiment/on-chain - medium priority
    
    # Risk & Validation Researchers
    "execution": True,           # Market microstructure - high priority
    "risk_management": True,     # Portfolio construction - high priority
    "validation": True,          # Overfitting detection - high priority
    "robustness": True,          # Stress testing - high priority
    "data_quality": True,        # Data integrity - high priority
    "governance": True,          # Compliance & audit - high priority
}

# ─── Resource Allocation ───────────────────────────────────────────────────────
# Control computational resources per researcher
RESOURCE_LIMITS = {
    "max_concurrent_experiments": 2,  # How many researchers can run simultaneously
    "max_training_time_hours": 2.0,  # Per experiment
    "max_memory_gb": 8.0,            # Per experiment
    "gpu_required": False,           # Set True to require GPU for deep learning
    "allow_parallel": False,         # Not yet implemented
}

# ─── Experiment Settings ───────────────────────────────────────────────────────
DEFAULT_EXPERIMENT_CONFIG = {
    "train_test_split": 0.7,         # Chronological split
    "validation_split": 0.15,        # From training data
    "cross_validation_folds": 5,
    "random_seed": 42,
    "early_stopping_patience": 20,
    "max_epochs": 100,
    "batch_size": 64,
    "learning_rate": 0.001,
}

# ─── Data Configuration ───────────────────────────────────────────────────────
DATA_CONFIG = {
    "pairs": None,  # None = use all from config.py, or list like ["BTCUSDT", "ETHUSDT"]
    "timeframe": "1h",
    "min_data_points": 500,
    "cache_data": True,
    "fetch_missing": True,
}

# ─── Model Storage ─────────────────────────────────────────────────────────────
MODEL_STORAGE = {
    "save_interval": 10,  # Save checkpoint every N epochs
    "keep_best_only": True,  # Only keep best model (by validation score)
    "max_checkpoints": 3,  # Maximum checkpoints per experiment
    "compress_models": True,  # Use joblib compression
}

# ─── Logging and Monitoring ─────────────────────────────────────────────────────
LOGGING_CONFIG = {
    "level": "INFO",  # DEBUG, INFO, WARNING, ERROR
    "log_to_file": True,
    "log_to_console": True,
    "log_dir": str(RESEARCH_DIR / "logs"),
    "tensorboard": False,  # Not yet implemented
    "wandb": False,  # Weights & Biases integration (not yet implemented)
}

# ─── Validation and Testing ─────────────────────────────────────────────────────
VALIDATION_CONFIG = {
    "walk_forward_windows": 3,  # Number of walk-forward validation splits
    "min_confidence_threshold": 0.6,  # Minimum confidence to accept result
    "statistical_significance_alpha": 0.05,  # For hypothesis testing
    "require_reproducibility": True,  # Must be able to reproduce results
    "max_overfit_threshold": 0.05,  # Max allowed train-test AUC gap
}

# ─── Knowledge Base ────────────────────────────────────────────────────────────
KNOWLEDGE_BASE_CONFIG = {
    "auto_share": True,  # Automatically share results after validation
    "retention_days": 90,  # Keep raw results for N days
    "compress_old": True,  # Compress results older than 30 days
    "export_formats": ["json", "csv"],  # Export formats for results
}

# ─── Notification and Alerts ────────────────────────────────────────────────────
NOTIFICATIONS = {
    "enabled": False,
    "on_completion": False,  # Notify when experiment completes
    "on_failure": True,  # Notify on experiment failure
    "email": None,  # Email address for notifications
    "discord_webhook": None,  # Discord webhook URL
}

# ─── Advanced Settings ─────────────────────────────────────────────────────────
ADVANCED = {
    "experiment_timeout_seconds": 7200,  # 2 hours
    "auto_retry_failed": 1,  # Retry failed experiments once
    "dependency_check": True,  # Verify dependencies before starting
    "cleanup_temp": True,  # Clean up temporary files after completion
    "profile_memory": False,  # Memory profiling (debug)
    "profile_time": False,  # Timing profiling (debug)
}

# ─── Helper Functions ──────────────────────────────────────────────────────────

def get_active_researchers() -> List[str]:
    """Return list of researcher IDs that are enabled."""
    return [rid for rid, active in ACTIVE_RESEARCHERS.items() if active]

def get_researcher_config(researcher_id: str) -> Dict[str, Any]:
    """Get configuration specific to a researcher."""
    base_config = DEFAULT_EXPERIMENT_CONFIG.copy()
    
    # Researcher-specific overrides
    overrides = {
        # Deep Learning
        "sequence_models": {
            "max_epochs": 50,
            "batch_size": 64,
            "early_stopping_patience": 15,
        },
        "transformers": {
            "max_epochs": 30,
            "batch_size": 32,
            "learning_rate": 0.0005,
        },
        "graph_neural": {
            "max_epochs": 100,
            "batch_size": 32,
        },
        "contrastive": {
            "max_epochs": 200,
            "batch_size": 128,
            "learning_rate": 0.01,
        },
        "meta_learning": {
            "max_epochs": 50,
            "batch_size": 32,
            "learning_rate": 0.001,
        },
        "ensemble": {
            "max_epochs": 100,
        },
        
        # Strategy & Signal
        "momentum": {
            "max_epochs": 50,
            "batch_size": 64,
        },
        "mean_reversion": {
            "max_epochs": 50,
            "batch_size": 64,
        },
        "regime_detection": {
            "max_epochs": 100,
        },
        "feature_engineering": {
            "max_epochs": 50,
        },
        "alternative_data": {
            "max_epochs": 30,
            "batch_size": 32,
        },
        
        # Risk & Validation
        "execution": {
            "max_epochs": 30,
            "batch_size": 64,
        },
        "risk_management": {
            "max_epochs": 50,
            "batch_size": 64,
        },
        "validation": {
            "max_epochs": 30,
            "batch_size": 64,
        },
        "robustness": {
            "max_epochs": 30,
            "batch_size": 64,
        },
        "data_quality": {
            "max_epochs": 30,
            "batch_size": 64,
        },
        "governance": {
            "max_epochs": 30,
            "batch_size": 64,
        },
    }
    
    if researcher_id in overrides:
        base_config.update(overrides[researcher_id])
    
    return base_config

def validate_config() -> List[str]:
    """Validate configuration and return any warnings/errors."""
    warnings = []
    
    if not any(ACTIVE_RESEARCHERS.values()):
        warnings.append("No researchers are active!")
    
    if RESOURCE_LIMITS["max_concurrent_experiments"] > len(get_active_researchers()):
        warnings.append("More concurrent slots than active researchers")
    
    if DATA_CONFIG["min_data_points"] < 300:
        warnings.append("min_data_points may be too low for deep learning")
    
    return warnings

# Run validation on import
_config_warnings = validate_config()
if _config_warnings:
    print("[Research Config] Warnings:")
    for w in _config_warnings:
        print(f"  - {w}")
