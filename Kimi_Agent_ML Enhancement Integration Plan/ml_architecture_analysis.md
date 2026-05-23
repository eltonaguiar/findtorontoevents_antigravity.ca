
# ML Enhancement Integration Plan - Technical Architecture Analysis
## Crypto Prediction System - Expert Review

---

## 1. CURRENT ARCHITECTURE ANALYSIS

### 1.1 Strengths Identified

| Aspect | Assessment | Rationale |
|--------|------------|-----------|
| **Merge Order** | Strong | Feature contract-first approach prevents downstream breakage |
| **Health Gates** | Good | Progressive tightening allows safe iteration |
| **SL Calibrator** | Mature | Tighten-only mode prevents regression |
| **Feature Flagging** | Prudent | Entry timing behind flag allows staged rollout |
| **KPI Framework** | Comprehensive | 6 dimensions cover feature/model/operational health |

### 1.2 Critical Gaps Identified

| Gap | Risk Level | Impact |
|-----|------------|--------|
| **No schema versioning** | HIGH | Breaking changes will corrupt historical data |
| **No contract validation layer** | HIGH | Invalid features may pass silently |
| **Missing data lineage tracking** | MEDIUM | Cannot trace feature corruption sources |
| **No backfill coordination protocol** | MEDIUM | Race conditions during backfill possible |
| **Undefined API boundaries** | MEDIUM | Component coupling will increase |
| **No feature store abstraction** | MEDIUM | Direct DB coupling reduces flexibility |
| **Missing A/B test framework** | MEDIUM | Cannot isolate improvement attribution |

---

## 2. DETAILED FEATURE CONTRACT SCHEMA

### 2.1 Core Contract Structure: ml_features_at_entry

```python
"""
FEATURE CONTRACT SPECIFICATION v1.0
====================================
Defines the canonical schema for ML features at trade entry time.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union
from enum import Enum
import numpy as np
from datetime import datetime


class FeatureType(Enum):
    """Classification of feature semantic types"""
    PRICE = "price"                    # Raw price data
    VOLUME = "volume"                  # Volume metrics
    TIME = "time"                      # Temporal features
    VOLATILITY = "volatility"          # Vol measures
    MOMENTUM = "momentum"              # Momentum indicators
    REGIME = "regime"                  # Market regime indicators
    ORDERBOOK = "orderbook"            # L2/L3 data
    DERIVED = "derived"                # Computed features
    TARGET = "target"                  # Prediction targets


class FeatureCardinality(Enum):
    """Expected value distribution characteristics"""
    CONTINUOUS = "continuous"          # Float range
    DISCRETE = "discrete"              # Integer categories
    BINARY = "binary"                  # 0/1 values
    CONSTANT = "constant"              # Single value (problematic)


@dataclass(frozen=True)
class FeatureSpec:
    """
    Immutable specification for a single feature.

    Attributes:
        name: Canonical feature identifier
        dtype: Expected numpy dtype
        feature_type: Semantic category
        cardinality: Value distribution type
        nullable: Whether null values are permitted
        default_value: Fallback for missing data
        valid_range: Tuple of (min, max) for validation
        description: Human-readable documentation
        dependencies: List of upstream feature names
        compute_version: Version of computation logic
    """
    name: str
    dtype: np.dtype
    feature_type: FeatureType
    cardinality: FeatureCardinality
    nullable: bool = False
    default_value: Optional[Union[float, int]] = None
    valid_range: Optional[tuple] = None
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    compute_version: str = "1.0"

    def validate_value(self, value) -> tuple[bool, str]:
        """Validate a single value against this spec"""
        if value is None or (isinstance(value, float) and np.isnan(value)):
            if not self.nullable:
                return False, f"Feature {self.name}: null value not allowed"
            return True, ""

        if self.valid_range:
            min_val, max_val = self.valid_range
            if value < min_val or value > max_val:
                return False, f"Feature {self.name}: value {value} outside range"

        return True, ""


@dataclass
class FeatureContract:
    """
    Complete contract for the ml_features_at_entry dataset.

    This contract serves as:
    1. Schema definition for data producers
    2. Validation specification for data consumers
    3. Documentation for model training pipelines
    4. Compatibility check for model serving
    """

    contract_version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Core identifier columns (always required)
    identifier_features: List[FeatureSpec] = field(default_factory=lambda: [
        FeatureSpec(
            name="trade_id",
            dtype=np.dtype("int64"),
            feature_type=FeatureType.TIME,
            cardinality=FeatureCardinality.DISCRETE,
            nullable=False,
            description="Unique trade entry identifier"
        ),
        FeatureSpec(
            name="symbol",
            dtype=np.dtype("O"),  # object/string
            feature_type=FeatureType.PRICE,
            cardinality=FeatureCardinality.DISCRETE,
            nullable=False,
            description="Trading pair symbol (e.g., BTC-USD)"
        ),
        FeatureSpec(
            name="entry_timestamp",
            dtype=np.dtype("datetime64[ns]"),
            feature_type=FeatureType.TIME,
            cardinality=FeatureCardinality.CONTINUOUS,
            nullable=False,
            description="UTC timestamp of trade entry"
        ),
    ])

    # Agent 1: Time/Vol/Outcome features (to be added in merge 2)
    temporal_features: List[FeatureSpec] = field(default_factory=lambda: [
        FeatureSpec(
            name="hour_of_day",
            dtype=np.dtype("int8"),
            feature_type=FeatureType.TIME,
            cardinality=FeatureCardinality.DISCRETE,
            nullable=False,
            valid_range=(0, 23),
            description="Hour of day (0-23) for session analysis"
        ),
        FeatureSpec(
            name="day_of_week",
            dtype=np.dtype("int8"),
            feature_type=FeatureType.TIME,
            cardinality=FeatureCardinality.DISCRETE,
            nullable=False,
            valid_range=(0, 6),
            description="Day of week (0=Monday, 6=Sunday)"
        ),
        FeatureSpec(
            name="is_weekend",
            dtype=np.dtype("bool"),
            feature_type=FeatureType.TIME,
            cardinality=FeatureCardinality.BINARY,
            nullable=False,
            description="Whether entry is on weekend"
        ),
        FeatureSpec(
            name="seconds_since_midnight",
            dtype=np.dtype("int32"),
            feature_type=FeatureType.TIME,
            cardinality=FeatureCardinality.CONTINUOUS,
            nullable=False,
            valid_range=(0, 86400),
            description="Seconds since midnight UTC"
        ),
    ])

    volatility_features: List[FeatureSpec] = field(default_factory=lambda: [
        FeatureSpec(
            name="realized_vol_1h",
            dtype=np.dtype("float32"),
            feature_type=FeatureType.VOLATILITY,
            cardinality=FeatureCardinality.CONTINUOUS,
            nullable=False,
            valid_range=(0.0, 10.0),  # 0% to 1000% annualized
            description="1-hour realized volatility (annualized)"
        ),
        FeatureSpec(
            name="realized_vol_24h",
            dtype=np.dtype("float32"),
            feature_type=FeatureType.VOLATILITY,
            cardinality=FeatureCardinality.CONTINUOUS,
            nullable=False,
            valid_range=(0.0, 10.0),
            description="24-hour realized volatility (annualized)"
        ),
        FeatureSpec(
            name="parkinson_vol_1h",
            dtype=np.dtype("float32"),
            feature_type=FeatureType.VOLATILITY,
            cardinality=FeatureCardinality.CONTINUOUS,
            nullable=True,
            valid_range=(0.0, 10.0),
            default_value=0.0,
            description="Parkinson volatility estimator (high-low based)"
        ),
        FeatureSpec(
            name="garman_klass_vol_1h",
            dtype=np.dtype("float32"),
            feature_type=FeatureType.VOLATILITY,
            cardinality=FeatureCardinality.CONTINUOUS,
            nullable=True,
            valid_range=(0.0, 10.0),
            default_value=0.0,
            description="Garman-Klass volatility estimator (OHLC based)"
        ),
    ])

    outcome_features: List[FeatureSpec] = field(default_factory=lambda: [
        FeatureSpec(
            name="target_return_1h",
            dtype=np.dtype("float32"),
            feature_type=FeatureType.TARGET,
            cardinality=FeatureCardinality.CONTINUOUS,
            nullable=True,
            valid_range=(-1.0, 1.0),  # -100% to +100%
            description="Actual 1-hour forward return (training target)"
        ),
        FeatureSpec(
            name="target_return_4h",
            dtype=np.dtype("float32"),
            feature_type=FeatureType.TARGET,
            cardinality=FeatureCardinality.CONTINUOUS,
            nullable=True,
            valid_range=(-1.0, 1.0),
            description="Actual 4-hour forward return (training target)"
        ),
        FeatureSpec(
            name="hit_stop_loss",
            dtype=np.dtype("bool"),
            feature_type=FeatureType.TARGET,
            cardinality=FeatureCardinality.BINARY,
            nullable=True,
            description="Whether trade hit stop loss (for SL calibrator)"
        ),
        FeatureSpec(
            name="max_adverse_excursion",
            dtype=np.dtype("float32"),
            feature_type=FeatureType.TARGET,
            cardinality=FeatureCardinality.CONTINUOUS,
            nullable=True,
            valid_range=(-1.0, 0.0),
            description="Maximum negative P&L during trade"
        ),
    ])

    # Agent 2: SL Calibrator features (already implemented)
    sl_calibrator_features: List[FeatureSpec] = field(default_factory=lambda: [
        FeatureSpec(
            name="sl_group_id",
            dtype=np.dtype("O"),
            feature_type=FeatureType.DERIVED,
            cardinality=FeatureCardinality.DISCRETE,
            nullable=True,
            description="Stop-loss calibration group identifier"
        ),
        FeatureSpec(
            name="sl_calibrated_rate",
            dtype=np.dtype("float32"),
            feature_type=FeatureType.DERIVED,
            cardinality=FeatureCardinality.CONTINUOUS,
            nullable=True,
            valid_range=(0.0, 1.0),
            description="Calibrated stop-loss rate for this group"
        ),
        FeatureSpec(
            name="sl_confidence",
            dtype=np.dtype("float32"),
            feature_type=FeatureType.DERIVED,
            cardinality=FeatureCardinality.CONTINUOUS,
            nullable=True,
            valid_range=(0.0, 1.0),
            description="Confidence in calibration (based on sample size)"
        ),
    ])

    # Agent 5: Entry timing features (behind feature flag)
    entry_timing_features: List[FeatureSpec] = field(default_factory=lambda: [
        FeatureSpec(
            name="entry_timing_score",
            dtype=np.dtype("float32"),
            feature_type=FeatureType.DERIVED,
            cardinality=FeatureCardinality.CONTINUOUS,
            nullable=True,
            valid_range=(0.0, 1.0),
            description="Composite entry timing quality score"
        ),
        FeatureSpec(
            name="spread_at_entry_bps",
            dtype=np.dtype("float32"),
            feature_type=FeatureType.ORDERBOOK,
            cardinality=FeatureCardinality.CONTINUOUS,
            nullable=True,
            valid_range=(0.0, 1000.0),
            description="Bid-ask spread in basis points at entry"
        ),
        FeatureSpec(
            name="orderbook_imbalance",
            dtype=np.dtype("float32"),
            feature_type=FeatureType.ORDERBOOK,
            cardinality=FeatureCardinality.CONTINUOUS,
            nullable=True,
            valid_range=(-1.0, 1.0),
            description="(bid_vol - ask_vol) / (bid_vol + ask_vol)"
        ),
    ])

    def get_all_features(self) -> Dict[str, FeatureSpec]:
        """Return all features as a name -> spec mapping"""
        all_specs = {}
        for category in [
            self.identifier_features,
            self.temporal_features,
            self.volatility_features,
            self.outcome_features,
            self.sl_calibrator_features,
            self.entry_timing_features,
        ]:
            for spec in category:
                all_specs[spec.name] = spec
        return all_specs

    def validate_dataframe(self, df) -> Dict[str, any]:
        """
        Validate a dataframe against this contract.
        Returns validation report with errors and warnings.
        """
        report = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "missing_features": [],
            "extra_features": [],
            "type_mismatches": [],
        }

        expected_features = set(self.get_all_features().keys())
        actual_features = set(df.columns)

        # Check for missing features
        missing = expected_features - actual_features
        if missing:
            report["missing_features"] = list(missing)
            report["errors"].append(f"Missing required features: {missing}")
            report["valid"] = False

        # Check for extra features
        extra = actual_features - expected_features
        if extra:
            report["extra_features"] = list(extra)
            report["warnings"].append(f"Unexpected features present: {extra}")

        # Validate each present feature
        for feat_name in expected_features & actual_features:
            spec = self.get_all_features()[feat_name]

            # Check dtype compatibility
            actual_dtype = df[feat_name].dtype
            if not np.can_cast(actual_dtype, spec.dtype, casting="safe"):
                report["type_mismatches"].append({
                    "feature": feat_name,
                    "expected": str(spec.dtype),
                    "actual": str(actual_dtype)
                })
                report["errors"].append(
                    f"Type mismatch for {feat_name}: expected {spec.dtype}, got {actual_dtype}"
                )
                report["valid"] = False

        return report


# Global contract instance
ML_FEATURES_CONTRACT = FeatureContract()
```


---

## 3. API SPECIFICATIONS BETWEEN COMPONENTS

### 3.1 Component Interface Definitions

```python
"""
API SPECIFICATIONS FOR ML PIPELINE COMPONENTS
==============================================
"""

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable, Callable
import pandas as pd
from datetime import datetime
from enum import Enum


# ============================================================================
# 3.1.1 FEATURE STORE INTERFACE
# ============================================================================

@runtime_checkable
class FeatureStore(Protocol):
    """
    Abstract interface for feature storage and retrieval.

    Implementations may use:
    - Feast (feature store)
    - Redis (low-latency serving)
    - PostgreSQL (historical storage)
    - Parquet files (batch processing)
    """

    def get_features_at_time(
        self,
        symbol: str,
        timestamp: datetime,
        feature_names: list[str],
        contract_version: str = "1.0.0"
    ) -> dict:
        """
        Retrieve features for a specific symbol at a specific time.

        Args:
            symbol: Trading pair symbol
            timestamp: UTC timestamp for feature values
            feature_names: List of feature names to retrieve
            contract_version: Schema version to use

        Returns:
            Dictionary of feature_name -> value

        Raises:
            FeatureNotFoundError: If feature not available
            ContractVersionError: If version mismatch
        """
        ...

    def get_features_batch(
        self,
        queries: list[dict],  # [{symbol, timestamp, features}]
        contract_version: str = "1.0.0"
    ) -> pd.DataFrame:
        """
        Batch retrieve features for multiple points.

        Returns DataFrame with columns: [symbol, timestamp] + feature_names
        """
        ...

    def write_features(
        self,
        df: pd.DataFrame,
        contract_version: str = "1.0.0",
        validation_mode: str = "strict"
    ) -> dict:
        """
        Write features to store with contract validation.

        Args:
            df: DataFrame with feature columns
            contract_version: Schema version
            validation_mode: "strict" (fail on error) or "lenient" (log warnings)

        Returns:
            Write report with validation results
        """
        ...


# ============================================================================
# 3.1.2 FEATURE CONTRACT VALIDATOR INTERFACE
# ============================================================================

class ValidationResult(Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class FeatureContractValidator(ABC):
    """
    Validates data against the feature contract.
    Implementations check schema, types, ranges, and nullability.
    """

    @abstractmethod
    def validate(
        self,
        data: pd.DataFrame,
        contract: "FeatureContract"
    ) -> dict:
        """
        Validate data against contract.

        Returns:
            {
                "result": ValidationResult,
                "errors": list[str],
                "warnings": list[str],
                "statistics": dict
            }
        """
        pass

    @abstractmethod
    def check_health_gate(
        self,
        data: pd.DataFrame,
        gate_threshold: float
    ) -> tuple[bool, dict]:
        """
        Check if data passes the health gate threshold.

        Args:
            data: Feature dataframe to check
            gate_threshold: Maximum allowed dead feature percentage

        Returns:
            (passed, report_dict)
        """
        pass


# ============================================================================
# 3.1.3 SL CALIBRATOR INTERFACE
# ============================================================================

class SLCalibrator(ABC):
    """
    Stop-loss calibration service with hierarchical fallback.

    Calibration hierarchy:
    1. Group-specific rate (if 10+ winners in group)
    2. Parent bucket rate (if 10+ winners in parent)
    3. Global default rate
    """

    MIN_SAMPLES_FOR_CALIBRATION = 10

    @abstractmethod
    def calibrate_group(
        self,
        group_id: str,
        trades_df: pd.DataFrame
    ) -> dict:
        """
        Calibrate SL rate for a specific group.

        Args:
            group_id: Identifier for the calibration group
            trades_df: DataFrame with columns [hit_sl, return, ...]

        Returns:
            {
                "calibrated_rate": float,
                "confidence": float,
                "sample_size": int,
                "fallback_level": str  # "group", "parent", "global"
            }
        """
        pass

    @abstractmethod
    def get_sl_rate(
        self,
        group_id: str,
        parent_bucket: str = None
    ) -> dict:
        """
        Get calibrated SL rate with hierarchical fallback.

        Args:
            group_id: Specific group identifier
            parent_bucket: Parent category for fallback

        Returns:
            SL calibration result with fallback metadata
        """
        pass

    @abstractmethod
    def get_coverage_stats(self) -> dict:
        """
        Get calibration coverage statistics.

        Returns:
            {
                "total_groups": int,
                "calibrated_groups": int,
                "coverage_percentage": float,
                "groups_needing_more_data": list[str]
            }
        """
        pass


# ============================================================================
# 3.1.4 ENTRY TIMING SERVICE INTERFACE
# ============================================================================

class EntryTimingService(ABC):
    """
    Entry timing quality assessment service.

    Behind feature flag: "entry_timing_v2_enabled"
    """

    @abstractmethod
    def compute_timing_score(
        self,
        symbol: str,
        entry_timestamp: datetime,
        orderbook_data: dict
    ) -> dict:
        """
        Compute entry timing quality score.

        Args:
            symbol: Trading pair
            entry_timestamp: Entry time
            orderbook_data: L2 orderbook snapshot

        Returns:
            {
                "timing_score": float,  # 0-1, higher is better
                "spread_bps": float,
                "orderbook_imbalance": float,
                "confidence": float
            }
        """
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if entry timing v2 is enabled via feature flag."""
        pass


# ============================================================================
# 3.1.5 MODEL SERVING INTERFACE
# ============================================================================

class ModelServer(ABC):
    """
    Model inference service with contract validation.
    """

    @abstractmethod
    def predict(
        self,
        features: dict,
        model_version: str = "latest"
    ) -> dict:
        """
        Generate prediction from features.

        Args:
            features: Dictionary of feature_name -> value
            model_version: Specific model version or "latest"

        Returns:
            {
                "prediction": float,
                "confidence": float,
                "model_version": str,
                "feature_hash": str,  # For reproducibility
                "latency_ms": float
            }
        """
        pass

    @abstractmethod
    def get_feature_importance(self) -> dict:
        """Get current model feature importance scores."""
        pass

    @abstractmethod
    def health_check(self) -> dict:
        """Check model server health status."""
        pass
```

---

## 4. DATA FLOW ARCHITECTURE

### 4.1 System Data Flow (Text Diagram)

```
DATA INGESTION LAYER
--------------------
Market Data (L1) ----+       
Trade Data (fills) --+---> FEATURE ENGINEERING LAYER
Orderbook (L2/L3) ---+       
On-Chain Data -------+       

                             RAW FEATURE COMPUTATION (Agent 1)
                             - Temporal Features
                             - Volatility Features  
                             - Momentum Features
                             - Price Features
                                      |
                                      v
                             FEATURE CONTRACT VALIDATOR (Agent 4)
                             - Schema validation
                             - Type validation
                             - Range validation
                             - Null validation
                             - Health gate check
                                      |
                                      v
                             FEATURE STORE (Feast/Redis/PostgreSQL)
                             - Online store (Redis): Low-latency serving
                             - Offline store (Parquet/Postgres): Historical
                                      |
                                      v
MODEL SERVING LAYER
-------------------

SL CALIBRATOR SERVICE (Agent 2)
- Group calibration (n >= 10)
- Parent bucket fallback
- Global default fallback
- Tighten-only mode
        |
        v
ENTRY TIMING SERVICE (Agent 5) - FEATURE FLAGGED
- Feature flag: entry_timing_v2_enabled
- Timing score computation
- Orderbook features
        |
        v
MODEL INFERENCE ENGINE
- Input: ml_features_at_entry (validated)
- Output: Prediction + Confidence
- Safety: drift detection, bounds validation
        |
        v
MONITORING & GOVERNANCE LAYER
-----------------------------
- Feature Health Monitor (dead %, constant %, null %)
- KPI Dashboard (6 KPIs)
- Alert Manager (health gate, drift, latency)
```


---

## 5. MISSING TECHNICAL CONSIDERATIONS

### 5.1 Data Versioning Strategy

```python
"""
DATA VERSIONING SPECIFICATION
==============================
"""

class DataVersionManager:
    """
    Manages schema and data versioning for reproducibility.
    """

    VERSIONING_STRATEGY = {
        # Schema versions follow semver
        # MAJOR: Breaking changes (column removal, type change)
        # MINOR: Additive changes (new columns)
        # PATCH: Bug fixes, documentation

        "1.0.0": {
            "release_date": "2024-01-15",
            "changes": "Initial contract",
            "breaking": False,
            "migration_required": False
        },
        "1.1.0": {
            "release_date": "2024-02-01", 
            "changes": "Added temporal features (Agent 1)",
            "breaking": False,
            "migration_required": False
        },
        "2.0.0": {
            "release_date": "TBD",
            "changes": "Removed deprecated features",
            "breaking": True,
            "migration_required": True,
            "migration_script": "migrate_v1_to_v2.py"
        }
    }

    @staticmethod
    def get_compatible_versions(model_version: str) -> list[str]:
        """
        Return data versions compatible with a model version.

        Model trained on v1.1 data can consume v1.1 or v1.0 data
        (backward compatible within major version).
        """
        ...

    @staticmethod
    def validate_compatibility(
        data_version: str,
        model_version: str
    ) -> bool:
        """Check if data version is compatible with model version."""
        ...
```

### 5.2 Schema Evolution Handling

| Change Type | Handling Strategy | Example |
|-------------|-------------------|---------|
| **Add column** | Safe, backward compatible | Add hour_of_day |
| **Remove column** | Breaking, needs major version | Remove deprecated feature |
| **Type change** | Requires migration | float32 -> float64 |
| **Rename column** | Use alias system | vol_1h -> realized_vol_1h |
| **Change nullability** | Requires backfill | Make nullable -> required |
| **Change valid_range** | Safe if wider, warning if narrower | Expand range for new assets |

### 5.3 Backward Compatibility Requirements

```python
"""
BACKWARD COMPATIBILITY LAYER
=============================
"""

class CompatibilityLayer:
    """
    Handles reading data from older schema versions.
    """

    COLUMN_ALIASES = {
        # Old name -> New name
        "vol_1h": "realized_vol_1h",
        "vol_24h": "realized_vol_24h",
        "sl_rate": "sl_calibrated_rate",
    }

    DEFAULT_VALUES = {
        # For columns added in newer versions, provide defaults for old data
        "hour_of_day": lambda row: row["entry_timestamp"].hour,
        "day_of_week": lambda row: row["entry_timestamp"].dayofweek,
        "is_weekend": lambda row: row["entry_timestamp"].dayofweek >= 5,
    }

    @classmethod
    def upgrade_dataframe(
        cls,
        df: pd.DataFrame,
        from_version: str,
        to_version: str
    ) -> pd.DataFrame:
        """
        Upgrade dataframe from older schema to current.

        Steps:
        1. Rename aliased columns
        2. Add missing columns with defaults
        3. Validate against target contract
        """
        ...
```

### 5.4 Testing Strategy Per Component

```python
"""
TESTING STRATEGY
================
"""

TEST_MATRIX = {
    "FeatureContract": {
        "unit_tests": [
            "test_feature_spec_validation",
            "test_contract_validation_pass",
            "test_contract_validation_fail_missing_column",
            "test_contract_validation_fail_type_mismatch",
            "test_contract_validation_fail_range_violation",
        ],
        "integration_tests": [
            "test_contract_with_real_data_sample",
            "test_contract_version_compatibility",
        ],
        "property_tests": [
            "test_all_features_have_valid_ranges",
            "test_no_duplicate_feature_names",
        ]
    },

    "FeatureStore": {
        "unit_tests": [
            "test_write_and_read_roundtrip",
            "test_batch_retrieval",
            "test_version_isolation",
        ],
        "integration_tests": [
            "test_redis_postgres_consistency",
            "test_failover_behavior",
        ],
        "performance_tests": [
            "test_read_latency_sla",
            "test_write_throughput",
        ]
    },

    "SLCalibrator": {
        "unit_tests": [
            "test_calibration_with_sufficient_samples",
            "test_fallback_to_parent",
            "test_fallback_to_global",
            "test_tighten_only_mode",
        ],
        "integration_tests": [
            "test_end_to_end_calibration_flow",
            "test_coverage_stats_accuracy",
        ],
        "regression_tests": [
            "test_sl_rate_never_increases",
        ]
    },

    "EntryTimingService": {
        "unit_tests": [
            "test_timing_score_computation",
            "test_spread_calculation",
            "test_orderbook_imbalance",
        ],
        "integration_tests": [
            "test_feature_flag_behavior",
            "test_with_live_orderbook",
        ],
        "canary_tests": [
            "test_timing_vs_baseline_improvement",
        ]
    }
}
```

---

## 6. CONCRETE IMPLEMENTATION GUIDANCE

### 6.1 Feature Health Gate Implementation

```python
"""
FEATURE HEALTH GATE IMPLEMENTATION
===================================
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Callable
from datetime import datetime, timedelta


@dataclass
class HealthGateConfig:
    """Configuration for progressive health gate tightening."""

    # Initial threshold (most permissive)
    initial_dead_feature_threshold: float = 0.50  # 50%

    # After 3 stable retrains
    stage2_dead_feature_threshold: float = 0.35  # 35%
    stage2_required_stable_retrains: int = 3

    # After backfill + stable coverage
    stage3_dead_feature_threshold: float = 0.20  # 20%
    stage3_required_coverage: float = 0.95  # 95% of symbols

    # Final target
    final_dead_feature_threshold: float = 0.10  # 10% (10/39 features)

    # Stability criteria
    stable_retrain_window_days: int = 30
    max_dead_features_allowed: int = 10


class FeatureHealthGate:
    """
    Implements the progressive health gate for feature quality.

    The gate tightens over time as the system stabilizes:
    1. Start: 50% dead features allowed (development phase)
    2. After 3 stable retrains: 35% allowed
    3. After backfill + 95% coverage: 20% allowed
    4. Final: 10% allowed (10/39 features)
    """

    def __init__(self, config: HealthGateConfig = None):
        self.config = config or HealthGateConfig()
        self.retrain_history: list[dict] = []
        self.current_stage: int = 1

    def compute_feature_health(
        self,
        df: pd.DataFrame,
        contract: "FeatureContract"
    ) -> dict:
        """
        Compute comprehensive feature health metrics.

        Returns:
            {
                "dead_features": list[str],      # Features with zero variance
                "dead_percentage": float,         # % of features dead
                "constant_features": list[str],   # Features with single value
                "constant_percentage": float,     # % of features constant
                "null_percentages": dict,         # Per-feature null %
                "high_null_features": list[str],  # Features with >5% nulls
                "overall_health_score": float,    # 0-1 composite score
            }
        """
        expected_features = list(contract.get_all_features().keys())

        # Filter to only expected features
        df_expected = df[expected_features]

        results = {
            "dead_features": [],
            "dead_percentage": 0.0,
            "constant_features": [],
            "constant_percentage": 0.0,
            "null_percentages": {},
            "high_null_features": [],
            "overall_health_score": 0.0,
        }

        # Identify dead features (zero variance)
        for col in df_expected.columns:
            if df_expected[col].dtype in ["float32", "float64", "int32", "int64"]:
                if df_expected[col].nunique() <= 1:
                    results["dead_features"].append(col)

        results["dead_percentage"] = len(results["dead_features"]) / len(expected_features)

        # Identify constant features (single unique value)
        for col in df_expected.columns:
            if df_expected[col].nunique() == 1:
                results["constant_features"].append(col)

        results["constant_percentage"] = len(results["constant_features"]) / len(expected_features)

        # Compute null percentages
        for col in df_expected.columns:
            null_pct = df_expected[col].isnull().mean()
            results["null_percentages"][col] = null_pct
            if null_pct > 0.05:  # 5% threshold
                results["high_null_features"].append(col)

        # Compute overall health score
        # Weight: dead (50%), constant (30%), nulls (20%)
        dead_score = 1 - results["dead_percentage"]
        constant_score = 1 - results["constant_percentage"]
        null_score = 1 - len(results["high_null_features"]) / len(expected_features)

        results["overall_health_score"] = (
            0.5 * dead_score +
            0.3 * constant_score +
            0.2 * null_score
        )

        return results

    def check_gate(
        self,
        df: pd.DataFrame,
        contract: "FeatureContract",
        retrain_count: int = 0,
        coverage_percentage: float = 0.0
    ) -> tuple[bool, dict]:
        """
        Check if data passes the current health gate.

        Args:
            df: Feature dataframe to check
            contract: Feature contract specification
            retrain_count: Number of consecutive stable retrains
            coverage_percentage: Current data coverage %

        Returns:
            (passed, detailed_report)
        """
        health = self.compute_feature_health(df, contract)

        # Determine current threshold based on stage
        if retrain_count >= self.config.stage2_required_stable_retrains:
            if coverage_percentage >= self.config.stage3_required_coverage:
                current_threshold = self.config.stage3_dead_feature_threshold
                stage = 3
            else:
                current_threshold = self.config.stage2_dead_feature_threshold
                stage = 2
        else:
            current_threshold = self.config.initial_dead_feature_threshold
            stage = 1

        # Check if we pass
        passed = health["dead_percentage"] <= current_threshold

        report = {
            "passed": passed,
            "stage": stage,
            "threshold": current_threshold,
            "actual_dead_percentage": health["dead_percentage"],
            "dead_features": health["dead_features"],
            "health_metrics": health,
            "recommendations": []
        }

        # Generate recommendations
        if health["dead_features"]:
            report["recommendations"].append(
                f"Remove or fix dead features: {health['dead_features']}"
            )
        if health["constant_features"]:
            report["recommendations"].append(
                f"Investigate constant features: {health['constant_features']}"
            )
        if health["high_null_features"]:
            report["recommendations"].append(
                f"Address high null features: {health['high_null_features']}"
            )

        return passed, report

    def record_retrain(self, health_report: dict, success: bool):
        """Record a retrain event for stage progression tracking."""
        self.retrain_history.append({
            "timestamp": datetime.utcnow(),
            "health_report": health_report,
            "success": success
        })


# Usage example
health_gate = FeatureHealthGate()

# During pipeline execution
passed, report = health_gate.check_gate(
    df=training_data,
    contract=ML_FEATURES_CONTRACT,
    retrain_count=3,  # We have had 3 stable retrains
    coverage_percentage=0.96  # 96% coverage achieved
)

if not passed:
    print(f"Health gate FAILED at stage {report['stage']}")
    print(f"Threshold: {report['threshold']:.1%}, Actual: {report['actual_dead_percentage']:.1%}")
    for rec in report['recommendations']:
        print(f"  - {rec}")
    raise HealthGateViolation("Feature health check failed")
```


### 6.2 Component Communication Specification

```python
"""
COMPONENT COMMUNICATION PATTERNS
=================================
"""

from typing import TypedDict
import json


# ============================================================================
# Message Types for Inter-Component Communication
# ============================================================================

class FeatureUpdateEvent(TypedDict):
    """Event published when features are updated."""
    event_type: str  # "feature_update"
    symbol: str
    timestamp: str  # ISO format
    contract_version: str
    feature_names: list[str]
    validation_result: str  # "pass", "warn", "fail"


class HealthGateEvent(TypedDict):
    """Event published when health gate status changes."""
    event_type: str  # "health_gate_check"
    stage: int
    passed: bool
    threshold: float
    actual_dead_percentage: float
    timestamp: str


class SLCalibrationEvent(TypedDict):
    """Event published when SL calibration is updated."""
    event_type: str  # "sl_calibration"
    group_id: str
    old_rate: float
    new_rate: float
    sample_size: int
    fallback_level: str
    timestamp: str


class ModelPredictionEvent(TypedDict):
    """Event published for each model prediction."""
    event_type: str  # "model_prediction"
    trade_id: int
    symbol: str
    prediction: float
    confidence: float
    model_version: str
    feature_hash: str
    latency_ms: float
    timestamp: str


# ============================================================================
# Message Bus Interface
# ============================================================================

class MessageBus:
    """
    Async message bus for component communication.

    Implementations: Redis Pub/Sub, Kafka, RabbitMQ, or in-memory for testing.
    """

    TOPICS = {
        "features": "ml.features",
        "health": "ml.health",
        "calibration": "ml.calibration", 
        "predictions": "ml.predictions",
        "alerts": "ml.alerts"
    }

    def publish(self, topic: str, message: dict):
        """Publish a message to a topic."""
        ...

    def subscribe(self, topic: str, handler: Callable):
        """Subscribe to a topic with a handler function."""
        ...


# ============================================================================
# Synchronous API Client
# ============================================================================

class MLSystemClient:
    """
    Synchronous client for inter-service communication.

    Used for request-response patterns where async is not appropriate.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url

    def get_features(
        self,
        symbol: str,
        timestamp: datetime,
        contract_version: str = "1.0.0"
    ) -> dict:
        """Synchronous feature retrieval."""
        ...

    def validate_features(self, features: dict) -> dict:
        """Synchronous feature validation."""
        ...

    def get_sl_rate(self, group_id: str) -> dict:
        """Synchronous SL rate retrieval."""
        ...

    def predict(self, features: dict) -> dict:
        """Synchronous prediction."""
        ...
```

### 6.3 Merge Stage Technical Specifications

```python
"""
MERGE STAGE SPECIFICATIONS
===========================
"""

MERGE_STAGES = {
    "stage_1": {
        "name": "Feature Contract (Agent 4)",
        "order": 1,
        "description": "Establish ml_features_at_entry contract + health gate",

        "deliverables": [
            "FeatureContract dataclass with all feature specs",
            "Feature validation layer",
            "Health gate implementation (50% threshold)",
            "Contract versioning system",
        ],

        "api_changes": [
            "NEW: POST /v1/features/validate",
            "NEW: GET /v1/contract/schema",
            "NEW: GET /v1/health/gate-status",
        ],

        "database_changes": [
            "ADD: contract_version column to features table",
            "ADD: validation_metadata JSON column",
        ],

        "testing_requirements": [
            "Unit tests for all FeatureSpec validation",
            "Integration tests for contract validation",
            "Load tests for validation performance",
        ],

        "rollback_plan": [
            "Contract is additive only - no rollback needed",
            "Validation can be disabled via config",
        ],

        "success_criteria": [
            "All existing features pass contract validation",
            "Health gate reports < 50% dead features",
            "Validation latency < 10ms per row",
        ]
    },

    "stage_2": {
        "name": "Fix Dead Features (Agent 1)",
        "order": 2,
        "description": "Add time/vol/outcome features to the contract",

        "deliverables": [
            "Temporal feature computation (hour_of_day, day_of_week, etc.)",
            "Volatility feature computation (realized_vol, parkinson_vol, etc.)",
            "Outcome feature computation (target_return, hit_stop_loss, etc.)",
            "Feature computation pipeline",
        ],

        "api_changes": [
            "UPDATE: FeatureContract with new feature specs",
            "NEW: POST /v1/features/compute-temporal",
            "NEW: POST /v1/features/compute-volatility",
            "NEW: POST /v1/features/compute-outcomes",
        ],

        "database_changes": [
            "ADD: temporal_features table",
            "ADD: volatility_features table", 
            "ADD: outcome_features table",
        ],

        "testing_requirements": [
            "Unit tests for each feature computation",
            "Integration tests for feature pipeline",
            "Backfill validation tests",
        ],

        "rollback_plan": [
            "Disable new feature computation",
            "Revert to previous contract version",
        ],

        "success_criteria": [
            "Dead feature count reduced by > 50%",
            "New features pass contract validation",
            "Backfill completes for 90 days of history",
        ]
    },

    "stage_3": {
        "name": "SL Calibrator (Agent 2)",
        "order": 3,
        "description": "Keep in 'tighten-only' mode (already implemented)",

        "deliverables": [
            "SL calibration service (COMPLETE)",
            "Hierarchical fallback (COMPLETE)",
            "Coverage tracking (COMPLETE)",
        ],

        "api_changes": [
            "EXISTING: GET /v1/sl/calibrate",
            "EXISTING: GET /v1/sl/rate/{group_id}",
            "EXISTING: GET /v1/sl/coverage-stats",
        ],

        "database_changes": [
            "EXISTING: sl_calibration table",
        ],

        "testing_requirements": [
            "Verify tighten-only mode is enforced",
            "Test fallback hierarchy",
        ],

        "rollback_plan": [
            "SL rates are tighten-only - no rollback needed",
            "Can disable calibration and use defaults",
        ],

        "success_criteria": [
            "No SL rate increases observed",
            "Coverage expands to 10+ groups",
            "Fallback hierarchy works correctly",
        ]
    },

    "stage_4": {
        "name": "Entry Timing (Agent 5)",
        "order": 4,
        "description": "Merge LAST, behind feature flag initially",

        "deliverables": [
            "Entry timing score computation",
            "Orderbook-based features (spread, imbalance)",
            "Feature flag integration",
            "A/B testing framework",
        ],

        "api_changes": [
            "NEW: POST /v1/entry/timing-score",
            "NEW: GET /v1/flags/entry-timing-v2",
            "NEW: POST /v1/experiments/create",
        ],

        "database_changes": [
            "ADD: entry_timing_features table",
            "ADD: feature_flags table",
            "ADD: experiments table",
        ],

        "testing_requirements": [
            "Unit tests for timing score computation",
            "Integration tests with orderbook data",
            "Feature flag behavior tests",
            "A/B test statistical validation",
        ],

        "rollback_plan": [
            "Disable feature flag: entry_timing_v2_enabled = false",
            "Revert to baseline entry logic",
        ],

        "success_criteria": [
            "Adverse entry bps reduced vs baseline",
            "No increase in max intraday drawdown",
            "Statistically significant improvement (p < 0.05)",
        ]
    }
}
```

---

## 7. SUMMARY OF RECOMMENDATIONS

### 7.1 Critical Actions (Do First)

1. **Implement Feature Contract Validation Layer**
   - Create FeatureContract dataclass with all feature specs
   - Add validation methods for schema, types, ranges
   - Deploy health gate with 50% initial threshold

2. **Add Data Versioning**
   - Implement DataVersionManager for schema versioning
   - Store contract_version with all feature data
   - Create migration scripts for future schema changes

3. **Define API Boundaries**
   - Implement FeatureStore protocol
   - Create SLCalibrator abstract interface
   - Add EntryTimingService with feature flag support

### 7.2 Important Actions (Do Soon)

4. **Add Data Lineage Tracking**
   - Track feature computation dependencies
   - Store provenance metadata with each feature
   - Enable debugging of feature corruption

5. **Implement A/B Testing Framework**
   - Create experiment assignment logic
   - Track metrics per variant
   - Statistical significance testing

6. **Add Comprehensive Monitoring**
   - Feature drift detection
   - Prediction distribution tracking
   - Latency and error rate alerts

### 7.3 Nice-to-Have (Do Later)

7. **Feature Store Abstraction**
   - Migrate to Feast or similar feature store
   - Separate online/offline storage
   - Point-in-time correctness

8. **Automated Retraining Pipeline**
   - Trigger retrain on drift detection
   - Automated model promotion
   - Shadow deployment for validation

---

## 8. RISK MITIGATION MATRIX

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Schema breaking change | Medium | High | Versioning + migration scripts |
| Feature corruption | Medium | High | Validation layer + lineage tracking |
| SL rate regression | Low | Critical | Tighten-only mode enforcement |
| Entry timing degradation | Medium | High | Feature flag + A/B testing |
| Performance degradation | Low | Medium | Load testing + latency monitoring |
| Data inconsistency | Medium | High | Contract validation + health gates |

---

## 9. KEY TECHNICAL SPECIFICATIONS SUMMARY

### Feature Contract Schema
- **39 total features** across 6 categories
- **3 identifier features** (trade_id, symbol, entry_timestamp)
- **4 temporal features** (hour_of_day, day_of_week, is_weekend, seconds_since_midnight)
- **4 volatility features** (realized_vol_1h/24h, parkinson_vol_1h, garman_klass_vol_1h)
- **4 outcome features** (target_return_1h/4h, hit_stop_loss, max_adverse_excursion)
- **3 SL calibrator features** (sl_group_id, sl_calibrated_rate, sl_confidence)
- **3 entry timing features** (entry_timing_score, spread_at_entry_bps, orderbook_imbalance)

### Health Gate Thresholds
- **Stage 1**: 50% dead features allowed (initial)
- **Stage 2**: 35% dead features allowed (after 3 stable retrains)
- **Stage 3**: 20% dead features allowed (after backfill + 95% coverage)
- **Final**: 10% dead features allowed (10/39 features)

### API Endpoints Required
- `POST /v1/features/validate` - Validate features against contract
- `GET /v1/contract/schema` - Get current contract schema
- `GET /v1/health/gate-status` - Check health gate status
- `GET /v1/sl/rate/{group_id}` - Get calibrated SL rate
- `GET /v1/sl/coverage-stats` - Get calibration coverage
- `GET /v1/flags/entry-timing-v2` - Check feature flag status

### Database Schema Additions
- `contract_version` column to features table
- `validation_metadata` JSON column
- `feature_flags` table for feature toggles
- `experiments` table for A/B testing
