"""
Timeframe Utilities
===================
Helpers for resampling and aligning time series data.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from alpha_engine.config import TIME_FRAMES


def resample_ohlcv(
    df: pd.DataFrame,
    target_interval: str,
    price_cols: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Resample OHLCV data to a different timeframe.
    
    Args:
        df: DataFrame with OHLCV data (must have datetime index)
        target_interval: Target interval (e.g., '1h', '4h', '1d')
        price_cols: Column names [open, high, low, close, volume]
        
    Returns:
        Resampled DataFrame
    """
    if price_cols is None:
        price_cols = ['open', 'high', 'low', 'close', 'volume']
    
    o, h, l, c, v = price_cols[:5]
    
    resampled = df.resample(target_interval).agg({
        o: 'first',
        h: 'max',
        l: 'min',
        c: 'last',
        v: 'sum'
    }).dropna()
    
    return resampled


def align_timestamps(
    df_list: List[pd.DataFrame],
    method: str = 'inner'
) -> List[pd.DataFrame]:
    """
    Align multiple DataFrames to common timestamps.
    
    Args:
        df_list: List of DataFrames with datetime indices
        method: 'inner' (intersection) or 'outer' (union)
        
    Returns:
        List of aligned DataFrames
    """
    if not df_list:
        return []
    
    # Find common index
    if method == 'inner':
        common_idx = df_list[0].index
        for df in df_list[1:]:
            common_idx = common_idx.intersection(df.index)
    else:
        common_idx = df_list[0].index
        for df in df_list[1:]:
            common_idx = common_idx.union(df.index)
        common_idx = common_idx.sort_values()
    
    # Reindex all DataFrames
    aligned = [df.reindex(common_idx) for df in df_list]
    return aligned


def get_bar_count(
    lookback: str,
    interval: str
) -> int:
    """
    Calculate number of bars needed for a lookback period.
    
    Args:
        lookback: Lookback period (e.g., '30d', '6h')
        interval: Bar interval (e.g., '1h', '5m')
        
    Returns:
        Number of bars
    """
    # Parse lookback
    lookback_value = int(lookback[:-1])
    lookback_unit = lookback[-1]
    
    # Convert lookback to seconds
    multipliers = {'m': 60, 'h': 3600, 'd': 86400, 'w': 604800}
    lookback_seconds = lookback_value * multipliers.get(lookback_unit, 3600)
    
    # Parse interval
    interval_value = int(interval[:-1])
    interval_unit = interval[-1]
    interval_seconds = interval_value * multipliers.get(interval_unit, 60)
    
    return max(1, lookback_seconds // interval_seconds)


def generate_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate time-based features from datetime index.
    
    Features:
        - hour: Hour of day (0-23)
        - day_of_week: Day of week (0-6)
        - month: Month (1-12)
        - is_weekend: Boolean
        - session: Trading session (asian, london, ny, ny_pm)
    """
    df = df.copy()
    idx = df.index
    
    df['hour'] = idx.hour
    df['day_of_week'] = idx.dayofweek
    df['month'] = idx.month
    df['is_weekend'] = (idx.dayofweek >= 5).astype(int)
    
    # Trading sessions (UTC)
    df['session'] = 'other'
    df.loc[(idx.hour >= 0) & (idx.hour < 7), 'session'] = 'asian'
    df.loc[(idx.hour >= 7) & (idx.hour < 13), 'session'] = 'london'
    df.loc[(idx.hour >= 13) & (idx.hour < 17), 'session'] = 'ny'
    df.loc[(idx.hour >= 17) & (idx.hour < 21), 'session'] = 'ny_pm'
    
    return df
