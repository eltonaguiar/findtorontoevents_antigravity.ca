#!/usr/bin/env python3
"""
L2 ORDER BOOK DATA FETCHER
Fetches Level 2 order book data for microstructure analysis

Features:
- Real-time L2 order book snapshots
- Bid/ask spread analysis
- Order book imbalance calculations
- Market depth metrics
- Slippage estimation
- High-frequency microstructure features
"""

import os
import sys
import json
import time
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field
try:
    import websockets  # type: ignore[import-unresolved]
except ImportError:
    websockets = None  # type: ignore[assignment]
try:
    import aiohttp  # type: ignore[import-unresolved]
except ImportError:
    aiohttp = None  # type: ignore[assignment]
import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('l2_orderbook.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class L2Config:
    """L2 order book configuration"""
    BINANCE_API_KEY: str = ''
    BINANCE_SECRET: str = ''
    KRAKEN_API_KEY: str = ''
    KRAKEN_SECRET: str = ''

    # Symbols to track
    SYMBOLS: List[str] = field(default_factory=lambda: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT'])

    # Order book depth
    MAX_DEPTH: int = 50  # Levels to fetch

    # Update frequency
    SNAPSHOT_INTERVAL: int = 60  # Seconds between snapshots
    REALTIME_UPDATE_MS: int = 100  # WebSocket update frequency

    # Microstructure features
    CALCULATE_IMBALANCE: bool = True
    CALCULATE_SPREAD: bool = True
    CALCULATE_DEPTH: bool = True
    CALCULATE_SLIPPAGE: bool = True

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class OrderBookLevel:
    """Single order book level"""
    price: float
    quantity: float
    timestamp: datetime

@dataclass
class OrderBookSnapshot:
    """Complete order book snapshot"""
    symbol: str
    timestamp: datetime
    bids: List[OrderBookLevel]  # Best bids first (highest price)
    asks: List[OrderBookLevel]  # Best asks first (lowest price)
    exchange: str

@dataclass
class MicrostructureFeatures:
    """Calculated microstructure features"""
    symbol: str
    timestamp: datetime

    # Spread metrics
    bid_ask_spread: float
    relative_spread: float

    # Imbalance metrics
    order_imbalance: float
    volume_imbalance: float

    # Depth metrics
    bid_depth_5: float  # Total volume in top 5 bids
    ask_depth_5: float  # Total volume in top 5 asks
    total_depth_ratio: float

    # Slippage estimation
    estimated_slippage_1pct: float  # Slippage for 1% of order book
    estimated_slippage_5pct: float  # Slippage for 5% of order book

    # Advanced metrics
    slope_bid: float  # Price sensitivity of bid side
    slope_ask: float  # Price sensitivity of ask side
    convexity: float  # Order book convexity

# ============================================================================
# BINANCE L2 FETCHER
# ============================================================================

class BinanceL2Fetcher:
    """Fetch L2 order book from Binance"""

    def __init__(self, config: L2Config):
        self.config = config
        self.base_url = "https://api.binance.com"
        self.ws_url = "wss://stream.binance.com:9443/ws"

    async def get_snapshot(self, symbol: str) -> Optional[OrderBookSnapshot]:
        """Get order book snapshot via REST API"""
        try:
            url = f"{self.base_url}/api/v3/depth"
            params = {
                'symbol': symbol.upper(),
                'limit': self.config.MAX_DEPTH
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()

                        bids = [
                            OrderBookLevel(float(price), float(qty), datetime.now())
                            for price, qty in data['bids']
                        ]
                        asks = [
                            OrderBookLevel(float(price), float(qty), datetime.now())
                            for price, qty in data['asks']
                        ]

                        return OrderBookSnapshot(
                            symbol=symbol,
                            timestamp=datetime.now(),
                            bids=bids,
                            asks=asks,
                            exchange='binance'
                        )
                    else:
                        logger.error(f"Binance API error: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Error fetching Binance snapshot for {symbol}: {e}")
            return None

    async def subscribe_realtime(self, symbol: str, callback):
        """Subscribe to real-time order book updates"""
        stream_name = f"{symbol.lower()}@depth{self.config.MAX_DEPTH}@100ms"

        try:
            async with websockets.connect(f"{self.ws_url}/{stream_name}") as websocket:
                logger.info(f"Connected to Binance WebSocket for {symbol}")

                while True:
                    message = await websocket.recv()
                    data = json.loads(message)

                    if 'bids' in data and 'asks' in data:
                        bids = [
                            OrderBookLevel(float(price), float(qty), datetime.now())
                            for price, qty in data['bids']
                        ]
                        asks = [
                            OrderBookLevel(float(price), float(qty), datetime.now())
                            for price, qty in data['asks']
                        ]

                        snapshot = OrderBookSnapshot(
                            symbol=symbol,
                            timestamp=datetime.now(),
                            bids=bids,
                            asks=asks,
                            exchange='binance'
                        )

                        await callback(snapshot)

        except Exception as e:
            logger.error(f"WebSocket error for {symbol}: {e}")

# ============================================================================
# MICROSTRUCTURE ANALYZER
# ============================================================================

class MicrostructureAnalyzer:
    """Calculate microstructure features from order book"""

    def __init__(self, config: L2Config):
        self.config = config

    def calculate_features(self, snapshot: OrderBookSnapshot) -> MicrostructureFeatures:
        """Calculate all microstructure features"""

        # Basic spread metrics
        best_bid = snapshot.bids[0].price if snapshot.bids else 0
        best_ask = snapshot.asks[0].price if snapshot.asks else float('inf')

        bid_ask_spread = best_ask - best_bid
        mid_price = (best_bid + best_ask) / 2
        relative_spread = bid_ask_spread / mid_price if mid_price > 0 else 0

        # Imbalance metrics
        bid_volume = sum(level.quantity for level in snapshot.bids[:10])  # Top 10 levels
        ask_volume = sum(level.quantity for level in snapshot.asks[:10])

        total_volume = bid_volume + ask_volume
        order_imbalance = (bid_volume - ask_volume) / total_volume if total_volume > 0 else 0

        # Volume-weighted imbalance
        bid_weighted = sum(level.price * level.quantity for level in snapshot.bids[:10])
        ask_weighted = sum(level.price * level.quantity for level in snapshot.asks[:10])

        volume_imbalance = (bid_weighted - ask_weighted) / (bid_weighted + ask_weighted) if (bid_weighted + ask_weighted) > 0 else 0

        # Depth metrics
        bid_depth_5 = sum(level.quantity for level in snapshot.bids[:5])
        ask_depth_5 = sum(level.quantity for level in snapshot.asks[:5])
        total_depth_ratio = bid_depth_5 / ask_depth_5 if ask_depth_5 > 0 else float('inf')

        # Slippage estimation (simplified)
        slippage_1pct = self._estimate_slippage(snapshot, 0.01)
        slippage_5pct = self._estimate_slippage(snapshot, 0.05)

        # Advanced metrics
        slope_bid = self._calculate_slope(snapshot.bids[:10])
        slope_ask = self._calculate_slope(snapshot.asks[:10])
        convexity = self._calculate_convexity(snapshot)

        return MicrostructureFeatures(
            symbol=snapshot.symbol,
            timestamp=snapshot.timestamp,
            bid_ask_spread=bid_ask_spread,
            relative_spread=relative_spread,
            order_imbalance=order_imbalance,
            volume_imbalance=volume_imbalance,
            bid_depth_5=bid_depth_5,
            ask_depth_5=ask_depth_5,
            total_depth_ratio=total_depth_ratio,
            estimated_slippage_1pct=slippage_1pct,
            estimated_slippage_5pct=slippage_5pct,
            slope_bid=slope_bid,
            slope_ask=slope_ask,
            convexity=convexity
        )

    def _estimate_slippage(self, snapshot: OrderBookSnapshot, order_size_pct: float) -> float:
        """Estimate slippage for a given order size percentage"""
        try:
            # Simplified slippage calculation
            # In reality, would need actual order size and more sophisticated modeling
            mid_price = (snapshot.bids[0].price + snapshot.asks[0].price) / 2

            # Assume order size as percentage of total depth
            total_bid_depth = sum(level.quantity * level.price for level in snapshot.bids)
            total_ask_depth = sum(level.quantity * level.price for level in snapshot.asks)

            # For buy order, slippage through ask side
            ask_cumulative = 0
            slippage_price = 0

            for level in snapshot.asks:
                level_value = level.quantity * level.price
                if ask_cumulative + level_value >= order_size_pct * total_ask_depth:
                    # Partial fill
                    remaining = order_size_pct * total_ask_depth - ask_cumulative
                    slippage_price += (remaining / level.quantity) * level.price
                    break
                else:
                    ask_cumulative += level_value
                    slippage_price += level_value

            slippage = (slippage_price / (order_size_pct * total_ask_depth) - mid_price) / mid_price
            return slippage

        except Exception as e:
            logger.error(f"Error estimating slippage: {e}")
            return 0.0

    def _calculate_slope(self, levels: List[OrderBookLevel]) -> float:
        """Calculate price sensitivity (slope) of order book side"""
        if len(levels) < 2:
            return 0.0

        try:
            # Simple linear regression on cumulative volume vs price
            prices = [level.price for level in levels]
            volumes = [level.quantity for level in levels]

            # Cumulative volume
            cum_volume = np.cumsum(volumes)

            # Linear regression
            slope, _ = np.polyfit(cum_volume, prices, 1)
            return slope

        except Exception as e:
            logger.error(f"Error calculating slope: {e}")
            return 0.0

    def _calculate_convexity(self, snapshot: OrderBookSnapshot) -> float:
        """Calculate order book convexity"""
        try:
            # Simplified convexity measure
            # Difference between actual mid and volume-weighted mid
            bid_prices = [level.price for level in snapshot.bids[:10]]
            bid_volumes = [level.quantity for level in snapshot.bids[:10]]
            ask_prices = [level.price for level in snapshot.asks[:10]]
            ask_volumes = [level.quantity for level in snapshot.asks[:10]]

            bid_vwap = np.average(bid_prices, weights=bid_volumes)
            ask_vwap = np.average(ask_prices, weights=ask_volumes)

            actual_mid = (snapshot.bids[0].price + snapshot.asks[0].price) / 2
            vwap_mid = (bid_vwap + ask_vwap) / 2

            convexity = (vwap_mid - actual_mid) / actual_mid
            return convexity

        except Exception as e:
            logger.error(f"Error calculating convexity: {e}")
            return 0.0

# ============================================================================
# L2 ORDER BOOK AGENT
# ============================================================================

class L2OrderBookAgent:
    """Main agent for L2 order book data collection and analysis"""

    def __init__(self, config: L2Config):
        self.config = config
        self.fetcher = BinanceL2Fetcher(config)
        self.analyzer = MicrostructureAnalyzer(config)
        self.snapshots: Dict[str, List[OrderBookSnapshot]] = {}
        self.features: Dict[str, List[MicrostructureFeatures]] = {}

    async def start_collection(self):
        """Start collecting order book data"""
        logger.info("Starting L2 order book data collection")

        # Start snapshot collection
        asyncio.create_task(self._collect_snapshots())

        # Start real-time updates for major symbols
        for symbol in self.config.SYMBOLS[:2]:  # Limit to 2 for demo
            asyncio.create_task(self._subscribe_realtime(symbol))

    async def _collect_snapshots(self):
        """Collect periodic snapshots"""
        while True:
            for symbol in self.config.SYMBOLS:
                snapshot = await self.fetcher.get_snapshot(symbol)
                if snapshot:
                    if symbol not in self.snapshots:
                        self.snapshots[symbol] = []
                    self.snapshots[symbol].append(snapshot)

                    # Keep only recent snapshots (last 100)
                    if len(self.snapshots[symbol]) > 100:
                        self.snapshots[symbol] = self.snapshots[symbol][-100:]

                    # Calculate features
                    features = self.analyzer.calculate_features(snapshot)
                    if symbol not in self.features:
                        self.features[symbol] = []
                    self.features[symbol].append(features)

                    # Keep only recent features
                    if len(self.features[symbol]) > 100:
                        self.features[symbol] = self.features[symbol][-100:]

                    logger.info(f"Collected snapshot for {symbol}: spread={features.bid_ask_spread:.4f}")

            await asyncio.sleep(self.config.SNAPSHOT_INTERVAL)

    async def _subscribe_realtime(self, symbol: str):
        """Subscribe to real-time updates"""
        async def callback(snapshot: OrderBookSnapshot):
            features = self.analyzer.calculate_features(snapshot)
            logger.info(f"Real-time update for {symbol}: imbalance={features.order_imbalance:.3f}")

        await self.fetcher.subscribe_realtime(symbol, callback)

    def get_latest_features(self, symbol: str) -> Optional[MicrostructureFeatures]:
        """Get latest microstructure features for symbol"""
        if symbol in self.features and self.features[symbol]:
            return self.features[symbol][-1]
        return None

    def get_features_history(self, symbol: str, hours: int = 24) -> List[MicrostructureFeatures]:
        """Get historical microstructure features"""
        if symbol not in self.features:
            return []

        cutoff = datetime.now() - timedelta(hours=hours)
        return [f for f in self.features[symbol] if f.timestamp > cutoff]

# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    """Main execution function"""
    config = L2Config()
    agent = L2OrderBookAgent(config)

    # Start data collection
    await agent.start_collection()

    # Keep running
    while True:
        await asyncio.sleep(60)
        # Could add periodic analysis here

if __name__ == "__main__":
    asyncio.run(main())