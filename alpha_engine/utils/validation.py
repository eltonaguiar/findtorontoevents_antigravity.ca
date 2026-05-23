import pandas as pd
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class AlgorithmInputError(Exception):
    pass

def validate_dataframe(df: pd.DataFrame, required_columns: list[str] = ['Open', 'High', 'Low', 'Close', 'Volume']) -> pd.DataFrame:
    """
    Validate input DataFrame for algorithm processing.
    Raises AlgorithmInputError if invalid.
    """
    if df is None or df.empty:
        raise AlgorithmInputError("DataFrame is None or empty")
    
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise AlgorithmInputError(f"Missing required columns: {missing}")
    
    for col in required_columns:
        if df[col].dtype not in ['float64', 'float32', 'int64', 'int32']:
            raise AlgorithmInputError(f"Column {col} must be numeric")
        if df[col].isna().all():
            raise AlgorithmInputError(f"Column {col} is entirely NaN")
    
    if len(df) < 50:
        logger.warning(f"DataFrame has only {len(df)} rows, may be insufficient for indicators")
    
    logger.info(f"Validated DataFrame: {len(df)} rows, {len(df.columns)} columns")
    return df

def load_thresholds(config_path: str = 'config/thresholds.json') -> Dict[str, Any]:
    """
    Load dynamic thresholds from config file.
    """
    try:
        import json
        with open(config_path, 'r') as f:
            thresholds = json.load(f)
        logger.info(f"Loaded thresholds from {config_path}")
        return thresholds
    except FileNotFoundError:
        logger.warning(f"Thresholds config not found at {config_path}, using defaults")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {config_path}: {e}")
        raise AlgorithmInputError(f"Invalid thresholds config: {e}")

def adjust_thresholds(base_threshold: float, volatility: float, config: Dict[str, Any]) -> float:
    """
    Dynamically adjust threshold based on volatility.
    """
    if config.get('global', {}).get('volatility_adjust', False):
        factor = 1 + (volatility - 1.0) * 0.5  # Scale by 50% of vol deviation
        return base_threshold * factor
    return base_threshold