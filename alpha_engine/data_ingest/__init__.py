"""
Data Ingestion Module
=====================
Handles fetching and storing market data from various sources.
All data stored as Parquet for efficient retrieval.
"""

from .market_ohlcv import fetch_binance_ohlcv, store_ohlcv_parquet
from .orderbook_depth import OrderbookCollector, compute_imbalance
from .macro_factors import MacroFactorCollector

__all__ = [
    "fetch_binance_ohlcv",
    "store_ohlcv_parquet", 
    "OrderbookCollector",
    "compute_imbalance",
    "MacroFactorCollector",
]
