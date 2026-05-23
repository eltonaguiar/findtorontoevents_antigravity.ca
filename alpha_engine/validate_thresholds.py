"""
Score Threshold Validation
==========================
Validates score thresholds and provides safe loading with bounds checking.

Schema matches the output of engine/dynamic_threshold.py (data/score_thresholds.json):
  {
    "generated_at": "...",
    "config": { "half_life_days": ..., "lookback_days": ... },
    "total_closed_picks": N,
    "asset_class_thresholds": {
      "CRYPTO": {
        "threshold": 65,
        "profit_factor": 1.89,
        "win_rate": 52.3,
        "weighted_trades": 312.5,
        "raw_trades": 287,
        "asset_class": "CRYPTO",
        "weighted_win_pnl": ...,
        "weighted_loss_pnl": ...
      },
      "BOND": {
        "threshold": 50,
        "profit_factor": 0.0,
        "win_rate": 0.0,
        "weighted_trades": 0.0,
        "raw_trades": 0,
        "asset_class": "BOND",
        "reason": "insufficient_data"
      }
    }
  }
"""

import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

# Defer pydantic import — not needed for CLI dry-run validation on bare CI runners
try:
    from pydantic import BaseModel, Field
    _HAS_PYDANTIC = True
except ImportError:
    _HAS_PYDANTIC = False

if _HAS_PYDANTIC:
    class AssetClassThreshold(BaseModel):
        """Validated single asset-class threshold entry (pydantic model)."""
        threshold: float = Field(ge=0, le=100,
                                 description="Minimum elite score for this asset class (0-100)")
        profit_factor: float = Field(ge=0,
                                      description="Profit factor used to derive the threshold")
        win_rate: float = Field(ge=0, le=100,
                                 description="Win rate percentage for this asset class")
        weighted_trades: float = Field(ge=0,
                                       description="Time-decay weighted trade count")
        raw_trades: int = Field(ge=0,
                                description="Raw (unweighted) trade count")
        asset_class: str = ""
        reason: Optional[str] = None
        weighted_win_pnl: Optional[float] = None
        weighted_loss_pnl: Optional[float] = None

        class Config:
            schema_extra = {
                "example": {
                    "threshold": 65,
                    "profit_factor": 1.89,
                    "win_rate": 52.3,
                    "weighted_trades": 312.5,
                    "raw_trades": 287,
                    "asset_class": "CRYPTO",
                }
            }
else:
    # Stub for environments without pydantic (e.g. bare CI runners)
    class AssetClassThreshold:  # type: ignore[no-redef]
        """Fallback threshold holder when pydantic is unavailable."""
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
            # Match pydantic defaults for optional fields (tests assert .reason is None, etc.)
            if not hasattr(self, "reason"):
                self.reason = None
            if not hasattr(self, "weighted_win_pnl"):
                self.weighted_win_pnl = None
            if not hasattr(self, "weighted_loss_pnl"):
                self.weighted_loss_pnl = None
            # Basic bounds check even without pydantic
            t = kwargs.get("threshold", 0)
            if not isinstance(t, (int, float)) or t < 0 or t > 100:
                raise ValueError(f"threshold {t} out of bounds - must be 0-100")
            pf = kwargs.get("profit_factor", 0)
            if not isinstance(pf, (int, float)) or pf < 0:
                raise ValueError(f"profit_factor {pf} must be >= 0")
            wr = kwargs.get("win_rate", 0)
            if not isinstance(wr, (int, float)) or wr < 0 or wr > 100:
                raise ValueError(f"win_rate {wr} out of bounds - must be 0-100")


class ThresholdValidator:
    """Validates and loads score thresholds safely."""

    def __init__(self, thresholds_path: Path):
        self.thresholds_path = thresholds_path
        self.validated_config: Dict[str, Any] = {}
        self.validation_errors: list = []

    def validate_file(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate thresholds file structure and bounds.
        Returns (is_valid, report_dict)
        """
        report: Dict[str, Any] = {
            "timestamp": None,
            "valid": False,
            "errors": [],
            "warnings": [],
            "thresholds": {}
        }

        # Check file exists
        if not self.thresholds_path.exists():
            report["errors"].append(f"Thresholds file not found: {self.thresholds_path}")
            return False, report

        # Load JSON
        try:
            with open(self.thresholds_path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            report["errors"].append(f"Invalid JSON: {e}")
            return False, report
        except OSError as e:
            report["errors"].append(f"File read error: {e}")
            return False, report

        # Validate root structure
        if not isinstance(data, dict):
            report["errors"].append("Root must be a dictionary")
            return False, report

        report["timestamp"] = data.get("generated_at")

        # Locate the thresholds dict - supports both old and new schema
        asset_thresholds = data.get("asset_class_thresholds", data)

        if not isinstance(asset_thresholds, dict):
            report["errors"].append("asset_class_thresholds must be a dictionary")
            return False, report

        # Validate each threshold entry
        for asset_class, config in asset_thresholds.items():
            # Skip metadata keys that aren't asset-class entries
            if asset_class in ("generated_at", "config", "total_closed_picks"):
                continue
            if not isinstance(config, dict):
                report["errors"].append(
                    f"{asset_class}: entry must be a dict, got {type(config).__name__}"
                )
                continue

            try:
                validated = AssetClassThreshold(**config)
                self.validated_config[asset_class] = validated
                report["thresholds"][asset_class] = {
                    "threshold": getattr(validated, "threshold", None),
                    "profit_factor": getattr(validated, "profit_factor", None),
                    "win_rate": getattr(validated, "win_rate", None),
                    "raw_trades": getattr(validated, "raw_trades", None),
                    "status": "valid"
                }
            except ValueError as e:
                report["errors"].append(f"{asset_class}: {str(e)}")
                report["thresholds"][asset_class] = {
                    "status": "invalid", "error": str(e)
                }

        # Warnings for suspicious but not invalid values
        for asset_class, config in self.validated_config.items():
            threshold = getattr(config, "threshold", 0)
            raw_trades = getattr(config, "raw_trades", 0)
            pf = getattr(config, "profit_factor", 0)
            reason = getattr(config, "reason", None)

            # Warn if threshold is very high (too restrictive)
            if threshold > 80:
                report["warnings"].append(
                    f"{asset_class}: threshold very high ({threshold}) - "
                    f"may filter out almost all picks"
                )
            # Warn if threshold is 0 (no filtering at all)
            if threshold == 0 and raw_trades > 0:
                report["warnings"].append(
                    f"{asset_class}: threshold is 0 with {raw_trades} trades - "
                    f"no quality gate applied"
                )
            # Warn if profit_factor is 0 but trades exist
            if pf == 0 and raw_trades > 10:
                report["warnings"].append(
                    f"{asset_class}: PF=0 with {raw_trades} trades - "
                    f"possible data issue"
                )
            # Warn on insufficient data entries
            if reason == "insufficient_data":
                report["warnings"].append(
                    f"{asset_class}: insufficient data - using fallback threshold"
                )

        report["valid"] = len(report["errors"]) == 0
        return report["valid"], report

    def load_validated(self) -> Dict[str, Any]:
        """Load and return validated thresholds, or raise on error."""
        is_valid, report = self.validate_file()

        if not is_valid:
            error_msg = "Score threshold validation FAILED:\n"
            for error in report["errors"]:
                error_msg += f"  - {error}\n"
            raise ValueError(error_msg)

        return self.validated_config

    def get_threshold(self, asset_class: str, direction: str = "min") -> float:
        """
        Safely get a threshold value with fallback defaults.
        direction: 'min' or 'max' (both return the same threshold in current schema)
        """
        if asset_class not in self.validated_config:
            print(f"Warning: No threshold for {asset_class}, using safe default (threshold=50)")
            return 50.0

        config = self.validated_config[asset_class]
        return float(getattr(config, "threshold", 50.0))


def validate_and_apply_thresholds(thresholds_path: Path) -> Tuple[bool, str]:
    """
    Full validation pipeline for score thresholds.
    Suitable for GitHub Actions pre-commit checks.
    Returns (success, message)
    """
    validator = ThresholdValidator(thresholds_path)
    is_valid, report = validator.validate_file()

    message = "Score Threshold Validation Report\n"
    message += "=" * 50 + "\n"
    if report["timestamp"]:
        message += f"Generated: {report['timestamp']}\n"

    if report["errors"]:
        message += f"\nERRORS ({len(report['errors'])}):\n"
        for error in report["errors"]:
            message += f"  - {error}\n"

    if report["warnings"]:
        message += f"\nWARNINGS ({len(report['warnings'])}):\n"
        for warning in report["warnings"]:
            message += f"  - {warning}\n"

    if is_valid:
        message += f"\nValid thresholds: {len(report['thresholds'])} asset classes\n"
    else:
        message += "\nValidation FAILED\n"

    return is_valid, message


# ---------------------------------------------------------------------------
# CLI entry point - useful for GitHub Actions dry-run validation step.
# Uses plain JSON validation (no pydantic) so it works on bare CI runners.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/score_thresholds.json")

    if not path.exists():
        print(f"ERROR: File not found: {path}")
        sys.exit(1)

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"ERROR: Cannot read file: {e}")
        sys.exit(1)

    # Plain-JSON bounds validation (no pydantic dependency needed on CI)
    errors = []
    warnings = []
    asset_thresholds = data.get("asset_class_thresholds", data)

    if not isinstance(asset_thresholds, dict):
        print("ERROR: asset_class_thresholds must be a dictionary")
        sys.exit(1)

    for ac, cfg in asset_thresholds.items():
        if ac in ("generated_at", "config", "total_closed_picks"):
            continue
        if not isinstance(cfg, dict):
            errors.append(f"{ac}: entry must be a dict")
            continue
        t = cfg.get("threshold")
        if t is None:
            errors.append(f"{ac}: missing 'threshold' key")
        elif not isinstance(t, (int, float)) or t < 0 or t > 100:
            errors.append(f"{ac}: threshold {t} out of bounds (must be 0-100)")
        if isinstance(t, (int, float)) and t > 80:
            warnings.append(f"{ac}: threshold very high ({t}) - may filter almost all picks")

    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  - {w}")

    print(f"OK: {len(asset_thresholds)} asset classes validated")
    sys.exit(0)
