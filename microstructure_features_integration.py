#!/usr/bin/env python3
"""
MICROSTRUCTURE FEATURES INTEGRATION
Integrates L2 order book and on-chain metrics into ML feature pipeline

Features:
- L2 order book microstructure features
- On-chain sentiment and flow metrics
- Network health indicators
- Whale activity signals
- Real-time feature updates
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import numpy as np
import pandas as pd

# Import our agents
from l2_orderbook_agent import L2OrderBookAgent, L2Config
from onchain_metrics_agent import OnChainMetricsAgent, OnChainConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('microstructure_features.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# MICROSTRUCTURE FEATURES CONFIG
# ============================================================================

@dataclass
class MicrostructureConfig:
    """Configuration for microstructure features"""
    ENABLE_L2_FEATURES: bool = True
    ENABLE_ONCHAIN_FEATURES: bool = True
    ENABLE_REALTIME_UPDATES: bool = True

    # Feature update frequency
    FEATURE_UPDATE_INTERVAL: int = 60  # seconds

    # Feature history length
    MAX_FEATURE_HISTORY: int = 1000

    # Symbols to track
    SYMBOLS: Optional[List[str]] = None

    def __post_init__(self):
        if self.SYMBOLS is None:
            self.SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT']

# ============================================================================
# MICROSTRUCTURE FEATURES COLLECTOR
# ============================================================================

class MicrostructureFeaturesCollector:
    """Collects and integrates microstructure features"""

    def __init__(self, config: MicrostructureConfig):
        self.config = config

        # Initialize agents
        self.l2_agent = None
        self.onchain_agent = None

        if config.ENABLE_L2_FEATURES:
            l2_config = L2Config()
            self.l2_agent = L2OrderBookAgent(l2_config)

        if config.ENABLE_ONCHAIN_FEATURES:
            onchain_config = OnChainConfig()
            self.onchain_agent = OnChainMetricsAgent(onchain_config)

        # Feature storage
        self.feature_history: Dict[str, List[Dict]] = {}
        self.last_update = datetime.now()

    async def start_collection(self):
        """Start collecting microstructure features"""
        logger.info("Starting microstructure features collection")

        # Start individual agents
        tasks = []

        if self.l2_agent:
            tasks.append(asyncio.create_task(self.l2_agent.start_collection()))

        if self.onchain_agent:
            tasks.append(asyncio.create_task(self.onchain_agent.start_collection()))

        # Start feature integration
        if self.config.ENABLE_REALTIME_UPDATES:
            tasks.append(asyncio.create_task(self._update_features_loop()))

        await asyncio.gather(*tasks)

    async def _update_features_loop(self):
        """Continuously update features"""
        while True:
            try:
                await self._update_all_features()
                await asyncio.sleep(self.config.FEATURE_UPDATE_INTERVAL)
            except Exception as e:
                logger.error(f"Error updating features: {e}")
                await asyncio.sleep(10)

    async def _update_all_features(self):
        """Update features for all symbols"""
        for symbol in self.config.SYMBOLS:
            features = await self.get_symbol_features(symbol)
            if features:
                if symbol not in self.feature_history:
                    self.feature_history[symbol] = []

                self.feature_history[symbol].append({
                    'timestamp': datetime.now(),
                    'features': features
                })

                # Keep history limited
                if len(self.feature_history[symbol]) > self.config.MAX_FEATURE_HISTORY:
                    self.feature_history[symbol] = self.feature_history[symbol][-self.config.MAX_FEATURE_HISTORY:]

        self.last_update = datetime.now()
        logger.info(f"Updated microstructure features for {len(self.config.SYMBOLS)} symbols")

    async def get_symbol_features(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get all microstructure features for a symbol"""
        features = {}

        # L2 Order Book Features
        if self.l2_agent:
            l2_features = self.l2_agent.get_latest_features(symbol)
            if l2_features:
                features.update({
                    'l2_bid_ask_spread': l2_features.bid_ask_spread,
                    'l2_relative_spread': l2_features.relative_spread,
                    'l2_order_imbalance': l2_features.order_imbalance,
                    'l2_volume_imbalance': l2_features.volume_imbalance,
                    'l2_bid_depth_5': l2_features.bid_depth_5,
                    'l2_ask_depth_5': l2_features.ask_depth_5,
                    'l2_total_depth_ratio': l2_features.total_depth_ratio,
                    'l2_slope_bid': l2_features.slope_bid,
                    'l2_slope_ask': l2_features.slope_ask,
                    'l2_convexity': l2_features.convexity,
                    'l2_estimated_slippage_1pct': l2_features.estimated_slippage_1pct,
                    'l2_estimated_slippage_5pct': l2_features.estimated_slippage_5pct,
                })

        # On-Chain Features
        if self.onchain_agent:
            # Map symbol to on-chain format
            onchain_symbol = symbol.replace('USDT', '').replace('USD', '')

            # Whale sentiment
            whale_sentiment = self.onchain_agent.get_whale_sentiment(onchain_symbol)
            if whale_sentiment:
                features.update({
                    'onchain_whale_sentiment': whale_sentiment['whale_sentiment'],
                    'onchain_whale_count_24h': whale_sentiment['whale_count'],
                    'onchain_whale_volume_24h': whale_sentiment['total_volume'],
                })

            # Exchange flows
            flow_sentiment = self.onchain_agent.get_flow_sentiment(onchain_symbol)
            if flow_sentiment:
                features.update({
                    'onchain_flow_sentiment': flow_sentiment['flow_sentiment'],
                    'onchain_net_flow_24h': flow_sentiment['net_flow_24h'],
                    'onchain_flow_ratio_24h': flow_sentiment['flow_ratio_24h'],
                })

            # Network health
            network_health = self.onchain_agent.get_network_health_score(onchain_symbol)
            features['onchain_network_health'] = network_health

        return features if features else None

    def get_feature_history(self, symbol: str, hours: int = 24) -> List[Dict]:
        """Get historical features for a symbol"""
        if symbol not in self.feature_history:
            return []

        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            entry for entry in self.feature_history[symbol]
            if entry['timestamp'] > cutoff
        ]

    def get_latest_features_df(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get latest features as DataFrame for ML integration"""
        features = self.get_symbol_features(symbol)
        if not features:
            return None

        # Convert to DataFrame with single row
        df = pd.DataFrame([features])
        df.index = [datetime.now()]

        return df

# ============================================================================
# INTEGRATION WITH PRODUCTION ENGINE
# ============================================================================

class MicrostructureFeaturesIntegration:
    """Integration layer for production ML engine"""

    def __init__(self, config: Optional[MicrostructureConfig] = None):
        self.config = config or MicrostructureConfig()
        self.collector = MicrostructureFeaturesCollector(self.config)
        self._collection_task = None

    async def start(self):
        """Start the microstructure features collection"""
        if not self._collection_task:
            self._collection_task = asyncio.create_task(self.collector.start_collection())
            logger.info("Microstructure features integration started")

    async def stop(self):
        """Stop the collection"""
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
            self._collection_task = None
            logger.info("Microstructure features integration stopped")

    def get_features_for_symbol(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get current microstructure features for ML prediction"""
        try:
            # Create event loop if needed
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                # If loop is running, we need to handle this differently
                # For now, return cached features
                return self._get_cached_features(symbol)
            else:
                # Run in new loop
                return loop.run_until_complete(self.collector.get_symbol_features(symbol))

        except Exception as e:
            logger.error(f"Error getting features for {symbol}: {e}")
            return None

    def _get_cached_features(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get cached features when event loop is running"""
        # This is a simplified version - in production, you'd want proper async handling
        if symbol in self.collector.feature_history and self.collector.feature_history[symbol]:
            latest = self.collector.feature_history[symbol][-1]
            return latest['features']
        return None

    def enrich_ml_features(self, base_features_df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Enrich base ML features with microstructure data"""
        try:
            micro_features = self.get_features_for_symbol(symbol)

            if micro_features:
                # Add microstructure features to the DataFrame
                for feature_name, value in micro_features.items():
                    base_features_df[feature_name] = value

                logger.info(f"Enriched {symbol} features with {len(micro_features)} microstructure features")

            return base_features_df

        except Exception as e:
            logger.error(f"Error enriching features for {symbol}: {e}")
            return base_features_df

# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Global instance for easy access
_microstructure_integration = None

def get_microstructure_integration() -> MicrostructureFeaturesIntegration:
    """Get global microstructure integration instance"""
    global _microstructure_integration
    if _microstructure_integration is None:
        _microstructure_integration = MicrostructureFeaturesIntegration()
    return _microstructure_integration

async def start_microstructure_collection():
    """Start global microstructure collection"""
    integration = get_microstructure_integration()
    await integration.start()

async def stop_microstructure_collection():
    """Stop global microstructure collection"""
    integration = get_microstructure_integration()
    await integration.stop()

# ============================================================================
# STANDALONE TESTING
# ============================================================================

async def test_microstructure_features():
    """Test microstructure features collection"""
    config = MicrostructureConfig()
    collector = MicrostructureFeaturesCollector(config)

    print("Starting microstructure features test...")

    # Start collection in background
    collection_task = asyncio.create_task(collector.start_collection())

    # Wait a bit for data to collect
    await asyncio.sleep(5)

    # Test getting features
    for symbol in config.SYMBOLS[:2]:  # Test first 2 symbols
        features = await collector.get_symbol_features(symbol)
        if features:
            print(f"\n{symbol} microstructure features:")
            for key, value in list(features.items())[:5]:  # Show first 5
                print(f"  {key}: {value:.4f}")
        else:
            print(f"No features available for {symbol}")

    # Stop collection
    collection_task.cancel()
    try:
        await collection_task
    except asyncio.CancelledError:
        pass

    print("Microstructure features test completed")

if __name__ == "__main__":
    asyncio.run(test_microstructure_features())