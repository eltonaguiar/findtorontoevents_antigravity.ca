"""
Order Book Depth Data Ingestion
===============================
Collects order book snapshots from Binance and computes imbalance metrics.
Optimized for high-frequency mean-reversion strategies.
"""

import pandas as pd
import numpy as np
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import time
import logging
from collections import deque
import threading

from alpha_engine.config import BINANCE_BASE, BINANCE_FUTURES_BASE, PARQUET_COMPRESSION
from alpha_engine.utils.storage import append_to_parquet

logger = logging.getLogger(__name__)


def fetch_orderbook(
    symbol: str,
    limit: int = 10,
    use_futures: bool = False
) -> Optional[Dict]:
    """
    Fetch order book snapshot from Binance.
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
        limit: Depth limit (5, 10, 20, 50, 100, 500, 1000)
        use_futures: Use futures API
        
    Returns:
        Dict with 'bids', 'asks', 'lastUpdateId'
    """
    base = BINANCE_FUTURES_BASE if use_futures else BINANCE_BASE
    endpoint = "/fapi/v1/depth" if use_futures else "/api/v3/depth"
    
    url = f"{base}{endpoint}"
    params = {
        "symbol": symbol.upper(),
        "limit": limit
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching orderbook for {symbol}: {e}")
        return None


def compute_imbalance(
    orderbook: Dict,
    levels: int = 5
) -> Dict[str, float]:
    """
    Compute order book imbalance metrics.
    
    Args:
        orderbook: Orderbook dict with 'bids' and 'asks'
        levels: Number of levels to consider (top N)
        
    Returns:
        Dict with imbalance metrics
    """
    bids = orderbook.get('bids', [])
    asks = orderbook.get('asks', [])
    
    if not bids or not asks:
        return {}
    
    # Take top N levels
    bids = bids[:levels]
    asks = asks[:levels]
    
    # Convert to float
    bid_prices = np.array([float(b[0]) for b in bids])
    bid_vols = np.array([float(b[1]) for b in bids])
    ask_prices = np.array([float(a[0]) for a in asks])
    ask_vols = np.array([float(a[1]) for a in asks])
    
    # Volume imbalance
    total_bid_vol = bid_vols.sum()
    total_ask_vol = ask_vols.sum()
    
    # Standard imbalance metric: (bid_vol - ask_vol) / (bid_vol + ask_vol)
    # Range: -1 (all asks) to +1 (all bids)
    volume_imbalance = (total_bid_vol - total_ask_vol) / (total_bid_vol + total_ask_vol + 1e-10)
    
    # Weighted by price (closer to mid = more important)
    mid_price = (bid_prices[0] + ask_prices[0]) / 2
    
    bid_weights = 1 / (1 + np.abs(bid_prices - mid_price) / mid_price)
    ask_weights = 1 / (1 + np.abs(ask_prices - mid_price) / mid_price)
    
    weighted_bid_vol = (bid_vols * bid_weights).sum()
    weighted_ask_vol = (ask_vols * ask_weights).sum()
    weighted_imbalance = (weighted_bid_vol - weighted_ask_vol) / (weighted_bid_vol + weighted_ask_vol + 1e-10)
    
    # Spread metrics
    spread = ask_prices[0] - bid_prices[0]
    spread_pct = spread / mid_price
    
    # Depth metrics
    bid_depth = (bid_vols * bid_prices).sum()  # Value in quote currency
    ask_depth = (ask_vols * ask_prices).sum()
    
    # Cumulative depth at different levels
    bid_cumulative = np.cumsum(bid_vols)
    ask_cumulative = np.cumsum(ask_vols)
    
    return {
        'mid_price': mid_price,
        'spread': spread,
        'spread_pct': spread_pct,
        'volume_imbalance': volume_imbalance,
        'weighted_imbalance': weighted_imbalance,
        'bid_vol_total': total_bid_vol,
        'ask_vol_total': total_ask_vol,
        'bid_depth': bid_depth,
        'ask_depth': ask_depth,
        'depth_ratio': bid_depth / (ask_depth + 1e-10),
        # Price levels
        'best_bid': bid_prices[0],
        'best_ask': ask_prices[0],
        'bid_pressure_l2': bid_cumulative[min(1, len(bid_cumulative)-1)],
        'bid_pressure_l5': bid_cumulative[-1],
        'ask_pressure_l2': ask_cumulative[min(1, len(ask_cumulative)-1)],
        'ask_pressure_l5': ask_cumulative[-1],
    }


def compute_micro_price(
    orderbook: Dict,
    levels: int = 5
) -> float:
    """
    Compute micro-price (volume-weighted mid).
    More accurate fair value estimate than simple mid-price.
    """
    imb = compute_imbalance(orderbook, levels)
    if not imb:
        return 0.0
    
    # Micro-price adjustment based on imbalance
    mid = imb['mid_price']
    imbalance = imb['volume_imbalance']
    spread = imb['spread']
    
    # Adjust mid towards the side with more volume
    adjustment = imbalance * spread * 0.5
    return mid + adjustment


class OrderbookCollector:
    """
    High-frequency orderbook collector with batching and disk flushing.
    """
    
    def __init__(
        self,
        symbol: str,
        snapshot_interval: float = 1.0,  # seconds
        flush_interval: int = 60,  # flush to disk every N snapshots
        data_dir: Path = Path("data/orderbook"),
        use_futures: bool = False
    ):
        self.symbol = symbol
        self.snapshot_interval = snapshot_interval
        self.flush_interval = flush_interval
        self.data_dir = data_dir
        self.use_futures = use_futures
        
        self.buffer: List[Dict] = []
        self.snapshot_count = 0
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        
        # Ensure output directory exists
        self.output_dir = data_dir / symbol.replace('/', '_')
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def collect_snapshot(self) -> Optional[Dict]:
        """Collect a single snapshot with computed metrics."""
        ob = fetch_orderbook(self.symbol, limit=10, use_futures=self.use_futures)
        
        if ob is None:
            return None
        
        metrics = compute_imbalance(ob, levels=5)
        if not metrics:
            return None
        
        snapshot = {
            'timestamp': datetime.utcnow(),
            'symbol': self.symbol,
            'lastUpdateId': ob.get('lastUpdateId'),
            **metrics
        }
        
        return snapshot
    
    def flush_buffer(self):
        """Write buffered snapshots to Parquet."""
        if not self.buffer:
            return
        
        df = pd.DataFrame(self.buffer)
        df.set_index('timestamp', inplace=True)
        
        # Group by date for partitioning
        date_str = datetime.utcnow().strftime('%Y-%m-%d')
        filepath = self.output_dir / f"{date_str}.parquet"
        
        try:
            append_to_parquet(df, filepath)
            logger.debug(f"Flushed {len(self.buffer)} snapshots to {filepath}")
        except Exception as e:
            logger.error(f"Failed to flush buffer: {e}")
        
        self.buffer = []
    
    def _collection_loop(self):
        """Main collection loop (runs in separate thread)."""
        while not self._stop_event.is_set():
            try:
                snapshot = self.collect_snapshot()
                
                if snapshot:
                    self.buffer.append(snapshot)
                    self.snapshot_count += 1
                    
                    # Flush if buffer is full
                    if len(self.buffer) >= self.flush_interval:
                        self.flush_buffer()
                
                # Sleep until next snapshot
                time.sleep(self.snapshot_interval)
                
            except Exception as e:
                logger.error(f"Error in collection loop: {e}")
                time.sleep(self.snapshot_interval)
        
        # Final flush on stop
        self.flush_buffer()
    
    def start(self):
        """Start the collector in a background thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Collector already running")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._collection_loop, daemon=True)
        self._thread.start()
        logger.info(f"Started orderbook collector for {self.symbol}")
    
    def stop(self):
        """Stop the collector and flush remaining data."""
        self._stop_event.set()
        
        if self._thread:
            self._thread.join(timeout=10)
        
        self.flush_buffer()
        logger.info(f"Stopped orderbook collector for {self.symbol}. Total snapshots: {self.snapshot_count}")
    
    def get_recent_snapshots(self, lookback_seconds: int = 300) -> pd.DataFrame:
        """
        Get recent snapshots from memory buffer and disk.
        """
        cutoff = datetime.utcnow() - timedelta(seconds=lookback_seconds)
        
        # Get from buffer
        buffer_df = pd.DataFrame(self.buffer)
        if not buffer_df.empty:
            buffer_df.set_index('timestamp', inplace=True)
            buffer_df = buffer_df[buffer_df.index >= cutoff]
        
        # Get from disk (today's file)
        date_str = datetime.utcnow().strftime('%Y-%m-%d')
        filepath = self.output_dir / f"{date_str}.parquet"
        
        if filepath.exists():
            disk_df = pd.read_parquet(filepath)
            disk_df = disk_df[disk_df.index >= cutoff]
            
            if not buffer_df.empty:
                return pd.concat([disk_df, buffer_df]).sort_index()
            return disk_df
        
        return buffer_df


def collect_orderbook_batch(
    symbols: List[str],
    duration_seconds: int = 60,
    snapshot_interval: float = 1.0,
    use_futures: bool = False
) -> Dict[str, pd.DataFrame]:
    """
    Collect orderbook snapshots for multiple symbols over a duration.
    Synchronous batch collection (for backfilling/testing).
    """
    results = {sym: [] for sym in symbols}
    start_time = time.time()
    
    logger.info(f"Collecting orderbook data for {len(symbols)} symbols over {duration_seconds}s")
    
    while time.time() - start_time < duration_seconds:
        for symbol in symbols:
            try:
                snapshot = OrderbookCollector(symbol, use_futures=use_futures).collect_snapshot()
                if snapshot:
                    results[symbol].append(snapshot)
            except Exception as e:
                logger.error(f"Error collecting {symbol}: {e}")
        
        time.sleep(snapshot_interval)
    
    # Convert to DataFrames
    return {sym: pd.DataFrame(data).set_index('timestamp') if data else pd.DataFrame() 
            for sym, data in results.items()}
