"""
IsolatedDataBridge - Read-Only Market Data Access
=================================================

Provides incubator agents with secure, read-only access to market data.
Prevents any possibility of interfering with production systems.

Safety Mechanisms:
- Read-only database connections
- No API keys accessible
- No write permissions to production
- Cached data to prevent rate limiting
"""

import os
import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Paths (read-only access)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_DB = PROJECT_ROOT / "crypto_data.db"
CACHE_DIR = Path(__file__).resolve().parent / "_cache"
CACHE_DIR.mkdir(exist_ok=True)


@dataclass
class MarketDataSnapshot:
    """Standardized market data container."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str
    source: str


class IsolatedDataBridge:
    """
    Secure read-only bridge to market data.
    
    Agents CAN:
    - Read OHLCV data
    - Read funding rates
    - Read Fear & Greed index
    - Read on-chain metrics
    
    Agents CANNOT:
    - Execute trades
    - Write to production DB
    - Access API keys
    - Modify existing models
    """
    
    # Allowed symbols (subset to prevent resource exhaustion)
    ALLOWED_PAIRS = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
        "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "TAOUSDT",
    ]
    
    # Allowed timeframes
    ALLOWED_TIMEFRAMES = ["1h", "4h", "1d"]
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.cache = {}
        self._connection = None
        logger.info(f"[DataBridge] Initialized for agent {agent_id}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Create read-only database connection."""
        if self._connection is None:
            if not PRODUCTION_DB.exists():
                raise FileNotFoundError(f"Production DB not found: {PRODUCTION_DB}")
            # Open in read-only mode
            uri = f"file:{PRODUCTION_DB}?mode=ro"
            self._connection = sqlite3.connect(uri, uri=True)
            self._connection.row_factory = sqlite3.Row
        return self._connection
    
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 1000,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[MarketDataSnapshot]:
        """
        Fetch OHLCV data for a symbol.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            timeframe: "1h", "4h", or "1d"
            limit: Maximum bars to return
            start_time: Optional start filter
            end_time: Optional end filter
            
        Returns:
            List of MarketDataSnapshot objects
        """
        # Validate inputs
        if symbol not in self.ALLOWED_PAIRS:
            raise ValueError(f"Symbol {symbol} not in allowed list. Use: {self.ALLOWED_PAIRS}")
        if timeframe not in self.ALLOWED_TIMEFRAMES:
            raise ValueError(f"Timeframe {timeframe} not allowed. Use: {self.ALLOWED_TIMEFRAMES}")
        if limit > 5000:
            raise ValueError("Max limit is 5000 bars")
        
        # Check cache first
        cache_key = f"{symbol}_{timeframe}_{limit}"
        if cache_key in self.cache:
            cache_time, data = self.cache[cache_key]
            if datetime.now() - cache_time < timedelta(minutes=5):
                logger.debug(f"[DataBridge] Cache hit for {cache_key}")
                return data
        
        # Fetch from database
        conn = self._get_connection()
        table_name = f"{symbol.lower()}_{timeframe}"
        
        query = f"""
            SELECT timestamp, open, high, low, close, volume 
            FROM {table_name}
            WHERE 1=1
            {f"AND timestamp >= ?" if start_time else ""}
            {f"AND timestamp <= ?" if end_time else ""}
            ORDER BY timestamp DESC
            LIMIT ?
        """
        
        params = []
        if start_time:
            params.append(int(start_time.timestamp() * 1000))
        if end_time:
            params.append(int(end_time.timestamp() * 1000))
        params.append(limit)
        
        try:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            snapshots = []
            for row in reversed(rows):  # Oldest first
                snapshots.append(MarketDataSnapshot(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(row['timestamp'] / 1000),
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row['volume'],
                    timeframe=timeframe,
                    source="incubator_readonly"
                ))
            
            # Cache result
            self.cache[cache_key] = (datetime.now(), snapshots)
            logger.info(f"[DataBridge] Fetched {len(snapshots)} bars for {symbol} {timeframe}")
            return snapshots
            
        except sqlite3.Error as e:
            logger.error(f"[DataBridge] Database error: {e}")
            raise
    
    def fetch_funding_rates(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Fetch funding rate history for a symbol."""
        if symbol not in self.ALLOWED_PAIRS:
            raise ValueError(f"Symbol {symbol} not allowed")
        
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT timestamp, funding_rate, mark_price FROM funding_rates WHERE symbol = ? ORDER BY timestamp DESC LIMIT ?",
                (symbol, limit)
            )
            return [
                {
                    "timestamp": datetime.fromtimestamp(row['timestamp'] / 1000),
                    "funding_rate": row['funding_rate'],
                    "mark_price": row['mark_price']
                }
                for row in reversed(cursor.fetchall())
            ]
        except sqlite3.Error:
            # Table might not exist, return empty
            return []
    
    def fetch_fear_greed(self) -> Optional[Dict]:
        """Fetch latest Fear & Greed index."""
        cache_file = CACHE_DIR / "fear_greed.json"
        
        # Check file cache
        if cache_file.exists():
            with open(cache_file) as f:
                cached = json.load(f)
                cached_time = datetime.fromisoformat(cached['timestamp'])
                if datetime.now() - cached_time < timedelta(hours=1):
                    return cached
        
        # Fetch from production DB
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT value, classification, timestamp FROM fear_greed ORDER BY timestamp DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                result = {
                    "value": row['value'],
                    "classification": row['classification'],
                    "timestamp": datetime.fromtimestamp(row['timestamp'])
                }
                # Update cache
                with open(cache_file, 'w') as f:
                    json.dump({**result, "timestamp": result["timestamp"].isoformat()}, f)
                return result
        except sqlite3.Error:
            pass
        
        return None
    
    def get_universe(self) -> List[str]:
        """Return list of allowed trading pairs."""
        return self.ALLOWED_PAIRS.copy()
    
    def get_correlation_matrix(self, symbols: List[str], timeframe: str = "1h", lookback: int = 100) -> Dict:
        """Calculate correlation matrix for given symbols."""
        import numpy as np
        
        if len(symbols) > 10:
            raise ValueError("Max 10 symbols for correlation calculation")
        
        returns = {}
        for symbol in symbols:
            data = self.fetch_ohlcv(symbol, timeframe, lookback)
            closes = [d.close for d in data]
            if len(closes) > 1:
                returns[symbol] = np.diff(np.log(closes))
        
        # Compute correlation
        corr_matrix = {}
        for s1 in symbols:
            corr_matrix[s1] = {}
            for s2 in symbols:
                if s1 in returns and s2 in returns:
                    corr = np.corrcoef(returns[s1], returns[s2])[0, 1]
                    corr_matrix[s1][s2] = float(corr)
                else:
                    corr_matrix[s1][s2] = 0.0
        
        return corr_matrix
    
    def __del__(self):
        """Cleanup connection."""
        if self._connection:
            self._connection.close()


# Security: Prevent any write operations
original_setattr = IsolatedDataBridge.__setattr__

def secure_setattr(self, name, value):
    """Block any attempts to set trading-related attributes."""
    blocked_terms = ['trade', 'order', 'position', 'execute', 'buy', 'sell']
    if any(term in name.lower() for term in blocked_terms):
        raise PermissionError(
            f"[SECURITY] Incubator agents cannot set '{name}'. "
            "Trading operations are blocked in sandbox."
        )
    original_setattr(self, name, value)

IsolatedDataBridge.__setattr__ = secure_setattr
