#!/usr/bin/env python3
"""
ON-CHAIN METRICS AGENT
Fetches and analyzes blockchain data for crypto trading signals

Features:
- Real-time blockchain metrics
- Whale transaction monitoring
- Network congestion analysis
- Exchange flow analysis
- Mining difficulty and hashrate
- On-chain sentiment indicators
"""

import os
import sys
import json
import time
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import aiohttp
import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('onchain_metrics.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class OnChainConfig:
    """On-chain metrics configuration"""
    GLASSNODE_API_KEY: str = '2TJ9hTzXJQq6H5BkJ8K8XJQq6H5BkJ8K'  # Placeholder
    CRYPTOQUANT_API_KEY: str = 'placeholder_key'
    BLOCKCHAIN_COM_API_KEY: str = ''

    # Assets to track
    SYMBOLS: Optional[List[str]] = None

    # Update frequencies
    METRICS_INTERVAL: int = 300  # 5 minutes
    WHALE_INTERVAL: int = 60     # 1 minute

    # Whale transaction thresholds (in USD)
    WHALE_THRESHOLDS: Optional[Dict[str, float]] = None

    # Metrics to calculate
    ENABLE_WHALE_TRACKING: bool = True
    ENABLE_EXCHANGE_FLOWS: bool = True
    ENABLE_NETWORK_METRICS: bool = True
    ENABLE_MINING_METRICS: bool = True

    def __post_init__(self):
        if self.SYMBOLS is None:
            self.SYMBOLS = ['BTC', 'ETH', 'SOL', 'ADA']

        if self.WHALE_THRESHOLDS is None:
            self.WHALE_THRESHOLDS = {
                'BTC': 1000000,  # $1M
                'ETH': 500000,   # $500K
                'SOL': 100000,   # $100K
                'ADA': 50000     # $50K
            }

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class WhaleTransaction:
    """Large on-chain transaction"""
    symbol: str
    hash: str
    timestamp: datetime
    value_usd: float
    sender: str
    receiver: str
    transaction_type: str  # 'whale_buy', 'whale_sell', 'whale_transfer'

@dataclass
class ExchangeFlows:
    """Exchange inflow/outflow metrics"""
    symbol: str
    timestamp: datetime

    # Inflows (deposits to exchanges)
    exchange_inflow_1h: float
    exchange_inflow_24h: float

    # Outflows (withdrawals from exchanges)
    exchange_outflow_1h: float
    exchange_outflow_24h: float

    # Net flow
    net_flow_1h: float
    net_flow_24h: float

    # Flow ratio (outflow/inflow)
    flow_ratio_1h: float
    flow_ratio_24h: float

@dataclass
class NetworkMetrics:
    """Network health and activity metrics"""
    symbol: str
    timestamp: datetime

    # Transaction metrics
    transaction_count_24h: int
    active_addresses_24h: int
    new_addresses_24h: int

    # Network congestion
    average_gas_price: float
    median_gas_price: float
    gas_used_24h: float

    # Hashrate and difficulty (for PoW chains)
    hashrate: Optional[float]
    difficulty: Optional[float]

    # UTXO metrics (for Bitcoin)
    utxo_count: Optional[int]
    utxo_value_mean: Optional[float]

@dataclass
class MiningMetrics:
    """Mining-related metrics"""
    symbol: str
    timestamp: datetime

    # Mining profitability
    mining_profitability: float
    mining_revenue: float
    mining_cost: float

    # Mining difficulty adjustment
    difficulty_change_pct: float
    next_difficulty_adjustment: datetime

    # Miner activity
    active_miners: Optional[int]
    mining_pool_distribution: Dict[str, float]

# ============================================================================
# GLASSNODE API CLIENT
# ============================================================================

class GlassnodeClient:
    """Client for Glassnode on-chain analytics API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.glassnode.com/v1/metrics"

    async def get_metric(self, asset: str, metric: str, since: Optional[datetime] = None) -> Optional[List[Dict]]:
        """Fetch metric data from Glassnode"""
        try:
            url = f"{self.base_url}/{asset}/{metric}"
            params = {
                'api_key': self.api_key,
                'i': '1h',  # 1 hour intervals
                'c': 'USD'
            }

            if since:
                params['s'] = str(int(since.timestamp()))

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        logger.error(f"Glassnode API error: {response.status} for {asset}/{metric}")
                        return None

        except Exception as e:
            logger.error(f"Error fetching Glassnode data: {e}")
            return None

# ============================================================================
# CRYPTOQUANT API CLIENT
# ============================================================================

class CryptoQuantClient:
    """Client for CryptoQuant exchange flow analytics"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.cryptoquant.com/v1"

    async def get_exchange_flows(self, asset: str, hours: int = 24) -> Optional[Dict]:
        """Get exchange inflow/outflow data"""
        try:
            url = f"{self.base_url}/{asset.lower()}/exchange-flows"
            params = {
                'api_key': self.api_key,
                'window': f'{hours}h'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        logger.error(f"CryptoQuant API error: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Error fetching CryptoQuant data: {e}")
            return None

# ============================================================================
# WHALE TRANSACTION MONITOR
# ============================================================================

class WhaleMonitor:
    """Monitor large on-chain transactions"""

    def __init__(self, config: OnChainConfig):
        self.config = config
        self.whales: Dict[str, List[WhaleTransaction]] = {}

    async def scan_whale_transactions(self, symbol: str) -> List[WhaleTransaction]:
        """Scan for whale transactions on blockchain.

        Returns real whale transactions from blockchain explorer APIs.
        Returns an empty list when no real data is available (never fabricates data).
        """
        try:
            # TODO: Integrate with real blockchain explorer APIs (e.g. Whale Alert,
            # Etherscan, Blockchain.com) to fetch actual large transactions.
            # Until a real data source is connected, return empty list honestly.
            logger.debug(f"No real whale data source configured for {symbol} — returning empty list")
            return []

        except Exception as e:
            logger.error(f"Error scanning whale transactions for {symbol}: {e}")
            return []

# ============================================================================
# EXCHANGE FLOW ANALYZER
# ============================================================================

class ExchangeFlowAnalyzer:
    """Analyze exchange inflows and outflows"""

    def __init__(self, config: OnChainConfig):
        self.config = config
        self.cryptoquant = CryptoQuantClient(config.CRYPTOQUANT_API_KEY)
        self.flows: Dict[str, List[ExchangeFlows]] = {}

    async def get_exchange_flows(self, symbol: str) -> Optional[ExchangeFlows]:
        """Get current exchange flow metrics"""
        try:
            # Try CryptoQuant API first
            data = await self.cryptoquant.get_exchange_flows(symbol, 24)

            if data:
                # Parse CryptoQuant response
                inflow_1h = data.get('inflow_1h', 0)
                inflow_24h = data.get('inflow_24h', 0)
                outflow_1h = data.get('outflow_1h', 0)
                outflow_24h = data.get('outflow_24h', 0)

                net_flow_1h = outflow_1h - inflow_1h
                net_flow_24h = outflow_24h - inflow_24h

                flow_ratio_1h = outflow_1h / inflow_1h if inflow_1h > 0 else float('inf')
                flow_ratio_24h = outflow_24h / inflow_24h if inflow_24h > 0 else float('inf')

                flows = ExchangeFlows(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    exchange_inflow_1h=inflow_1h,
                    exchange_inflow_24h=inflow_24h,
                    exchange_outflow_1h=outflow_1h,
                    exchange_outflow_24h=outflow_24h,
                    net_flow_1h=net_flow_1h,
                    net_flow_24h=net_flow_24h,
                    flow_ratio_1h=flow_ratio_1h,
                    flow_ratio_24h=flow_ratio_24h
                )

                return flows

            else:
                # No data from API — return None instead of fabricating data
                logger.warning(f"CryptoQuant API returned no exchange flow data for {symbol} — returning None")
                return None

        except Exception as e:
            logger.error(f"Error getting exchange flows for {symbol}: {e}")
            return None

# ============================================================================
# NETWORK METRICS ANALYZER
# ============================================================================

class NetworkMetricsAnalyzer:
    """Analyze network health and activity"""

    def __init__(self, config: OnChainConfig):
        self.config = config
        self.glassnode = GlassnodeClient(config.GLASSNODE_API_KEY)
        self.metrics: Dict[str, List[NetworkMetrics]] = {}

    async def get_network_metrics(self, symbol: str) -> Optional[NetworkMetrics]:
        """Get current network metrics"""
        try:
            # Fetch various metrics from Glassnode
            since = datetime.now() - timedelta(hours=24)

            # Transaction metrics
            tx_count_data = await self.glassnode.get_metric(symbol.lower(), 'transactions/count', since)
            active_addr_data = await self.glassnode.get_metric(symbol.lower(), 'addresses/active_count', since)
            new_addr_data = await self.glassnode.get_metric(symbol.lower(), 'addresses/new_non_zero_count', since)

            # Extract latest values
            tx_count_24h = tx_count_data[-1]['v'] if tx_count_data else 0
            active_addresses_24h = active_addr_data[-1]['v'] if active_addr_data else 0
            new_addresses_24h = new_addr_data[-1]['v'] if new_addr_data else 0

            # Gas metrics (for ETH-like chains)
            gas_price_data = await self.glassnode.get_metric(symbol.lower(), 'fees/gas_price_mean', since)
            gas_used_data = await self.glassnode.get_metric(symbol.lower(), 'fees/gas_used', since)

            average_gas_price = gas_price_data[-1]['v'] if gas_price_data else 0
            gas_used_24h = gas_used_data[-1]['v'] if gas_used_data else 0
            median_gas_price = average_gas_price * 0.8  # Approximation

            # Mining metrics (for PoW chains like BTC)
            hashrate = None
            difficulty = None
            if symbol.upper() == 'BTC':
                hashrate_data = await self.glassnode.get_metric('btc', 'mining/hash_rate_mean', since)
                difficulty_data = await self.glassnode.get_metric('btc', 'mining/difficulty_latest', since)

                hashrate = hashrate_data[-1]['v'] if hashrate_data else None
                difficulty = difficulty_data[-1]['v'] if difficulty_data else None

            # UTXO metrics (BTC specific)
            utxo_count = None
            utxo_value_mean = None
            if symbol.upper() == 'BTC':
                utxo_count_data = await self.glassnode.get_metric('btc', 'blockchain/utxo_count', since)
                utxo_value_data = await self.glassnode.get_metric('btc', 'blockchain/utxo_value_mean', since)

                utxo_count = utxo_count_data[-1]['v'] if utxo_count_data else None
                utxo_value_mean = utxo_value_data[-1]['v'] if utxo_value_data else None

            metrics = NetworkMetrics(
                symbol=symbol,
                timestamp=datetime.now(),
                transaction_count_24h=int(tx_count_24h),
                active_addresses_24h=int(active_addresses_24h),
                new_addresses_24h=int(new_addresses_24h),
                average_gas_price=average_gas_price,
                median_gas_price=median_gas_price,
                gas_used_24h=gas_used_24h,
                hashrate=hashrate,
                difficulty=difficulty,
                utxo_count=utxo_count,
                utxo_value_mean=utxo_value_mean
            )

            return metrics

        except Exception as e:
            logger.error(f"Error getting network metrics for {symbol}: {e}")
            return None

# ============================================================================
# ON-CHAIN METRICS AGENT
# ============================================================================

class OnChainMetricsAgent:
    """Main agent for on-chain metrics collection and analysis"""

    def __init__(self, config: OnChainConfig):
        self.config = config
        self.whale_monitor = WhaleMonitor(config)
        self.flow_analyzer = ExchangeFlowAnalyzer(config)
        self.network_analyzer = NetworkMetricsAnalyzer(config)

        # Data storage
        self.whale_transactions: Dict[str, List[WhaleTransaction]] = {}
        self.exchange_flows: Dict[str, List[ExchangeFlows]] = {}
        self.network_metrics: Dict[str, List[NetworkMetrics]] = {}

    async def start_collection(self):
        """Start collecting on-chain metrics"""
        logger.info("Starting on-chain metrics collection")

        # Start different collection tasks
        tasks = []

        if self.config.ENABLE_WHALE_TRACKING:
            tasks.append(asyncio.create_task(self._collect_whale_data()))

        if self.config.ENABLE_EXCHANGE_FLOWS:
            tasks.append(asyncio.create_task(self._collect_flow_data()))

        if self.config.ENABLE_NETWORK_METRICS:
            tasks.append(asyncio.create_task(self._collect_network_data()))

        # Run all tasks
        await asyncio.gather(*tasks)

    async def _collect_whale_data(self):
        """Collect whale transaction data"""
        while True:
            for symbol in self.config.SYMBOLS:
                whales = await self.whale_monitor.scan_whale_transactions(symbol)

                if symbol not in self.whale_transactions:
                    self.whale_transactions[symbol] = []

                self.whale_transactions[symbol].extend(whales)

                # Keep only recent transactions (last 100 per symbol)
                if len(self.whale_transactions[symbol]) > 100:
                    self.whale_transactions[symbol] = self.whale_transactions[symbol][-100:]

            await asyncio.sleep(self.config.WHALE_INTERVAL)

    async def _collect_flow_data(self):
        """Collect exchange flow data"""
        while True:
            for symbol in self.config.SYMBOLS:
                flows = await self.flow_analyzer.get_exchange_flows(symbol)

                if flows:
                    if symbol not in self.exchange_flows:
                        self.exchange_flows[symbol] = []

                    self.exchange_flows[symbol].append(flows)

                    # Keep only recent data (last 100 per symbol)
                    if len(self.exchange_flows[symbol]) > 100:
                        self.exchange_flows[symbol] = self.exchange_flows[symbol][-100:]

                    logger.info(f"Updated flows for {symbol}: net_24h=${flows.net_flow_24h:,.0f}")

            await asyncio.sleep(self.config.METRICS_INTERVAL)

    async def _collect_network_data(self):
        """Collect network metrics data"""
        while True:
            for symbol in self.config.SYMBOLS:
                metrics = await self.network_analyzer.get_network_metrics(symbol)

                if metrics:
                    if symbol not in self.network_metrics:
                        self.network_metrics[symbol] = []

                    self.network_metrics[symbol].append(metrics)

                    # Keep only recent data (last 100 per symbol)
                    if len(self.network_metrics[symbol]) > 100:
                        self.network_metrics[symbol] = self.network_metrics[symbol][-100:]

                    logger.info(f"Updated network metrics for {symbol}: {metrics.transaction_count_24h} txns")

            await asyncio.sleep(self.config.METRICS_INTERVAL)

    def get_whale_sentiment(self, symbol: str, hours: int = 24) -> Dict[str, Any]:
        """Calculate whale activity sentiment"""
        if symbol not in self.whale_transactions:
            return {'whale_sentiment': 0, 'whale_count': 0, 'total_volume': 0}

        cutoff = datetime.now() - timedelta(hours=hours)
        recent_whales = [w for w in self.whale_transactions[symbol] if w.timestamp > cutoff]

        if not recent_whales:
            return {'whale_sentiment': 0, 'whale_count': 0, 'total_volume': 0}

        # Simple sentiment: +1 for buys/transfers, -1 for sells
        sentiment_scores = []
        for whale in recent_whales:
            if whale.transaction_type == 'whale_buy':
                sentiment_scores.append(1)
            elif whale.transaction_type == 'whale_sell':
                sentiment_scores.append(-1)
            else:  # transfer
                sentiment_scores.append(0.5)

        avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0
        total_volume = sum(w.value_usd for w in recent_whales)

        return {
            'whale_sentiment': avg_sentiment,
            'whale_count': len(recent_whales),
            'total_volume': total_volume
        }

    def get_flow_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Calculate exchange flow sentiment"""
        if symbol not in self.exchange_flows or not self.exchange_flows[symbol]:
            return {'flow_sentiment': 0, 'net_flow_24h': 0, 'flow_ratio_24h': 1}

        latest_flow = self.exchange_flows[symbol][-1]

        # Positive sentiment when outflows > inflows (distribution to exchanges)
        flow_sentiment = latest_flow.net_flow_24h / max(abs(latest_flow.exchange_inflow_24h), 1000000)

        return {
            'flow_sentiment': flow_sentiment,
            'net_flow_24h': latest_flow.net_flow_24h,
            'flow_ratio_24h': latest_flow.flow_ratio_24h
        }

    def get_network_health_score(self, symbol: str) -> float:
        """Calculate network health score (0-1)"""
        if symbol not in self.network_metrics or not self.network_metrics[symbol]:
            return 0.5

        latest = self.network_metrics[symbol][-1]

        # Simple health score based on activity
        activity_score = min(latest.transaction_count_24h / 100000, 1.0)  # Normalize
        address_score = min(latest.active_addresses_24h / 50000, 1.0)    # Normalize

        health_score = (activity_score + address_score) / 2
        return health_score

# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    """Main execution function"""
    config = OnChainConfig()
    agent = OnChainMetricsAgent(config)

    # Start data collection
    await agent.start_collection()

if __name__ == "__main__":
    asyncio.run(main())