"""
Market OHLCV Data Ingestion
===========================
Fetches OHLCV data from Binance and stores as Parquet.
Supports multiple timeframes and efficient incremental updates.
"""

import pandas as pd
import numpy as np
import requests
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import time
import logging

from alpha_engine.config import (
    BINANCE_BASE, BINANCE_FUTURES_BASE,
    PARQUET_COMPRESSION, TIME_FRAMES
)
from alpha_engine.utils.storage import write_parquet, append_to_parquet

logger = logging.getLogger(__name__)


def fetch_binance_ohlcv(
    symbol: str,
    interval: str,
    start_ts: Optional[int] = None,
    end_ts: Optional[int] = None,
    limit: int = 1000,
    use_futures: bool = False
) -> pd.DataFrame:
    """
    Fetch OHLCV data from Binance API.
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
        interval: Kline interval (e.g., '1m', '5m', '1h', '1d')
        start_ts: Start timestamp in milliseconds
        end_ts: End timestamp in milliseconds
        limit: Number of candles to fetch (max 1000)
        use_futures: Use futures API instead of spot
        
    Returns:
        DataFrame with columns [open, high, low, close, volume, quote_volume]
    """
    base = BINANCE_FUTURES_BASE if use_futures else BINANCE_BASE
    endpoint = "/fapi/v1/klines" if use_futures else "/api/v3/klines"
    
    url = f"{base}{endpoint}"
    params = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": min(limit, 1000)
    }
    
    if start_ts:
        params["startTime"] = int(start_ts)
    if end_ts:
        params["endTime"] = int(end_ts)
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            return pd.DataFrame()
        
        # Binance kline format:
        # [open_time, open, high, low, close, volume, close_time, quote_volume, 
        #  num_trades, taker_buy_base, taker_buy_quote, ignore]
        df = pd.DataFrame(data, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'num_trades',
            'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])
        
        # Convert types
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms', utc=True)
        df['close_time'] = pd.to_datetime(df['close_time'], unit='ms', utc=True)
        
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 
                        'quote_volume', 'taker_buy_base', 'taker_buy_quote']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df['num_trades'] = pd.to_numeric(df['num_trades'], errors='coerce').astype(int)
        
        df.set_index('open_time', inplace=True)
        
        return df[['open', 'high', 'low', 'close', 'volume', 'quote_volume', 
                   'num_trades', 'taker_buy_base', 'taker_buy_quote']]
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {symbol} {interval}: {e}")
        return pd.DataFrame()


def fetch_historical_ohlcv(
    symbol: str,
    interval: str,
    days_back: int = 30,
    use_futures: bool = False
) -> pd.DataFrame:
    """
    Fetch historical OHLCV data for specified lookback period.
    Handles pagination for large requests.
    """
    end_ts = int(datetime.utcnow().timestamp() * 1000)
    start_ts = int((datetime.utcnow() - timedelta(days=days_back)).timestamp() * 1000)
    
    all_data = []
    current_start = start_ts
    
    while current_start < end_ts:
        df = fetch_binance_ohlcv(
            symbol, interval,
            start_ts=current_start,
            end_ts=end_ts,
            limit=1000,
            use_futures=use_futures
        )
        
        if df.empty:
            break
        
        all_data.append(df)
        
        # Update start timestamp for next batch
        last_time = df.index[-1]
        current_start = int(last_time.timestamp() * 1000) + 1
        
        # Rate limit
        time.sleep(0.1)
        
        # Break if we've reached the end
        if len(df) < 1000:
            break
    
    if not all_data:
        return pd.DataFrame()
    
    combined = pd.concat(all_data, axis=0)
    combined = combined[~combined.index.duplicated(keep='first')]
    return combined.sort_index()


def store_ohlcv_parquet(
    df: pd.DataFrame,
    symbol: str,
    interval: str,
    data_dir: Path = Path("data/ohlcv")
) -> Path:
    """
    Store OHLCV data as Parquet, partitioned by symbol and date.
    
    Directory structure: data/ohlcv/{symbol}/{interval}/{YYYY-MM-DD}.parquet
    """
    symbol_clean = symbol.replace('/', '_').replace('-', '_')
    base_dir = data_dir / symbol_clean / interval
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # Group by date and write separate files
    df['date'] = df.index.date
    
    written_files = []
    for date, group in df.groupby('date'):
        filepath = base_dir / f"{date}.parquet"
        
        # Remove date column before storing
        group_to_store = group.drop(columns=['date'])
        
        # Append or create new file
        append_to_parquet(group_to_store, filepath)
        written_files.append(filepath)
    
    logger.info(f"Stored {len(df)} rows for {symbol} {interval} to {base_dir}")
    return base_dir


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute derived features from OHLCV data.
    
    Features:
        - returns: Log returns
        - volatility: Realized volatility (20-period)
        - atr: Average True Range
        - vwap: Volume Weighted Average Price
        - rsi: Relative Strength Index (14)
        - bb_upper, bb_lower: Bollinger Bands
    """
    df = df.copy()
    
    # Returns
    df['returns'] = np.log(df['close'] / df['close'].shift(1))
    
    # Realized volatility (20-period, annualized)
    df['volatility_20'] = df['returns'].rolling(20).std() * np.sqrt(365 * 24 * 12)  # For 5m bars
    
    # ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift(1))
    low_close = np.abs(df['low'] - df['close'].shift(1))
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr_14'] = tr.rolling(14).mean()
    
    # VWAP (daily reset)
    df['vwap'] = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    # Bollinger Bands
    df['bb_middle'] = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_middle'] + 2 * bb_std
    df['bb_lower'] = df['bb_middle'] - 2 * bb_std
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    
    # Volume features
    df['volume_sma_20'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_sma_20']
    
    return df


class OHLCVIngestor:
    """
    Main class for OHLCV data ingestion and management.
    """
    
    def __init__(self, data_dir: Path = Path("data/ohlcv")):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def update_symbol(
        self,
        symbol: str,
        interval: str,
        lookback_days: int = 7,
        use_futures: bool = False
    ) -> pd.DataFrame:
        """
        Update stored data for a symbol/interval with latest data.
        """
        df = fetch_historical_ohlcv(symbol, interval, lookback_days, use_futures)
        
        if not df.empty:
            store_ohlcv_parquet(df, symbol, interval, self.data_dir)
        
        return df
    
    def load_symbol(
        self,
        symbol: str,
        interval: str,
        lookback_days: int = 30
    ) -> pd.DataFrame:
        """
        Load stored data for a symbol/interval.
        """
        from alpha_engine.utils.storage import read_parquet
        
        symbol_clean = symbol.replace('/', '_').replace('-', '_')
        pattern = f"{self.data_dir}/{symbol_clean}/{interval}/*.parquet"
        
        df = read_parquet(pattern)
        
        if not df.empty and lookback_days:
            cutoff = datetime.utcnow() - timedelta(days=lookback_days)
            df = df[df.index >= cutoff]
        
        return df
    
    def update_all_symbols(
        self,
        symbols: List[str],
        intervals: List[str] = None,
        lookback_days: int = 7
    ) -> Dict[str, pd.DataFrame]:
        """
        Update all symbols for specified intervals.
        """
        if intervals is None:
            intervals = ['5m', '15m', '1h', '4h']
        
        results = {}
        for symbol in symbols:
            for interval in intervals:
                key = f"{symbol}_{interval}"
                try:
                    df = self.update_symbol(symbol, interval, lookback_days)
                    results[key] = df
                    time.sleep(0.2)  # Rate limiting
                except Exception as e:
                    logger.error(f"Failed to update {key}: {e}")
                    results[key] = pd.DataFrame()
        
        return results
