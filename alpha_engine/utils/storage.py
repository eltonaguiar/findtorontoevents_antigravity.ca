"""
Storage Utilities
=================
Helpers for Parquet read/write operations with proper partitioning.
"""

import pandas as pd
from pathlib import Path
from typing import List, Optional, Union
import pyarrow as pa
import pyarrow.parquet as pq
from alpha_engine.config import PARQUET_COMPRESSION


def read_parquet(
    path_pattern: Union[str, Path],
    columns: Optional[List[str]] = None,
    filters: Optional[List[tuple]] = None
) -> pd.DataFrame:
    """
    Read Parquet file(s) matching path pattern.
    
    Args:
        path_pattern: Glob pattern or specific file path
        columns: Optional list of columns to read
        filters: Optional PyArrow filters for row filtering
        
    Returns:
        DataFrame with data
    """
    path = Path(path_pattern)
    
    # Handle glob patterns
    if '*' in str(path_pattern):
        files = list(path.parent.glob(path.name))
        if not files:
            return pd.DataFrame()
        
        dfs = []
        for f in sorted(files):
            try:
                df = pd.read_parquet(f, columns=columns, filters=filters)
                dfs.append(df)
            except Exception:
                continue
        
        if not dfs:
            return pd.DataFrame()
        return pd.concat(dfs, axis=0).sort_index()
    
    # Single file
    if not path.exists():
        return pd.DataFrame()
    
    return pd.read_parquet(path, columns=columns, filters=filters)


def write_parquet(
    df: pd.DataFrame,
    base_path: Union[str, Path],
    partition_cols: Optional[List[str]] = None,
    filename: Optional[str] = None
) -> Path:
    """
    Write DataFrame to Parquet with optional partitioning.
    
    Args:
        df: DataFrame to write
        base_path: Base directory for storage
        partition_cols: Columns to partition by (e.g., ['symbol', 'date'])
        filename: Specific filename (default: timestamp.parquet)
        
    Returns:
        Path to written file
    """
    base = Path(base_path)
    base.mkdir(parents=True, exist_ok=True)
    
    if filename is None:
        from datetime import datetime
        filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.parquet"
    
    if partition_cols:
        # Write partitioned dataset
        import pyarrow.dataset as ds
        
        table = pa.Table.from_pandas(df)
        ds.write_dataset(
            table,
            base_path=base,
            partitioning=partition_cols,
            format="parquet",
            compression=PARQUET_COMPRESSION,
            existing_data_behavior="overwrite_or_ignore"
        )
        return base
    else:
        # Single file
        out_path = base / filename
        df.to_parquet(out_path, compression=PARQUET_COMPRESSION, index=True)
        return out_path


def list_parquet_files(
    base_path: Union[str, Path],
    pattern: str = "**/*.parquet"
) -> List[Path]:
    """List all parquet files matching pattern."""
    base = Path(base_path)
    if not base.exists():
        return []
    return sorted(base.glob(pattern))


def append_to_parquet(
    df: pd.DataFrame,
    filepath: Union[str, Path]
) -> Path:
    """
    Append DataFrame to existing Parquet file.
    Creates new file if doesn't exist.
    """
    filepath = Path(filepath)
    
    if filepath.exists():
        existing = pd.read_parquet(filepath)
        combined = pd.concat([existing, df], axis=0)
        # Remove duplicates based on index
        combined = combined[~combined.index.duplicated(keep='last')]
        combined.to_parquet(filepath, compression=PARQUET_COMPRESSION, index=True)
    else:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(filepath, compression=PARQUET_COMPRESSION, index=True)
    
    return filepath
