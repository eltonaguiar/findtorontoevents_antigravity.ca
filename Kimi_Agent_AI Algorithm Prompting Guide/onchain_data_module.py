"""
On-Chain Data Integration Module for Crypto Trading
====================================================
Provides whale tracking, exchange flow analysis, and confidence scoring
as a signal multiplier for existing trading strategies.

Free Tier API Limits:
- Whale Alert: 10 calls/minute
- Dune Analytics: 2500 calls/month
- Glassnode: Limited free tier (rate limited)

Author: Quantitative Finance Research
"""

import requests
import time
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import logging
from functools import wraps
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FlowType(Enum):
    """Classification of fund flows"""
    UNKNOWN = "unknown"
    EXCHANGE_OUTFLOW = "exchange_outflow"  # Bullish signal
    EXCHANGE_INFLOW = "exchange_inflow"    # Bearish signal
    STAKING = "staking"                     # Neutral (filter out)
    OTC = "otc"                            # Neutral (filter out)
    WHALE_WALLET = "whale_wallet"          # Watch for patterns


class ConfidenceLevel(Enum):
    """Confidence levels for signal boosting"""
    VERY_LOW = 0.0
    LOW = 0.25
    NEUTRAL = 0.5
    HIGH = 0.75
    VERY_HIGH = 1.0


@dataclass
class WhaleTransaction:
    """Represents a whale transaction"""
    tx_hash: str
    timestamp: datetime
    from_address: str
    to_address: str
    amount: float
    amount_usd: float
    symbol: str
    blockchain: str
    flow_type: FlowType = FlowType.UNKNOWN
    from_entity: Optional[str] = None
    to_entity: Optional[str] = None
    confidence_score: float = 0.0


@dataclass
class ExchangeFlow:
    """Represents exchange flow data"""
    exchange: str
    timestamp: datetime
    inflow: float
    outflow: float
    netflow: float
    inflow_usd: float
    outflow_usd: float
    netflow_usd: float
    symbol: str


@dataclass
class OnChainSignal:
    """Combined on-chain signal for confidence boosting"""
    symbol: str
    timestamp: datetime
    whale_score: float
    exchange_score: float
    combined_score: float
    supporting_evidence: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class RateLimiter:
    """Thread-safe rate limiter for API calls"""

    def __init__(self, calls_per_minute: int):
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call_time = 0
        self.lock = threading.Lock()

    def wait(self):
        """Wait if necessary to respect rate limit"""
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_call_time
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)
            self.last_call_time = time.time()


class Cache:
    """Simple TTL cache for API responses"""

    def __init__(self, default_ttl_seconds: int = 300):
        self.cache = {}
        self.default_ttl = default_ttl_seconds
        self.lock = threading.Lock()

    def _make_key(self, *args, **kwargs) -> str:
        """Create cache key from arguments"""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, *args, **kwargs) -> Optional[Any]:
        """Get cached value if not expired"""
        key = self._make_key(*args, **kwargs)
        with self.lock:
            if key in self.cache:
                value, expiry = self.cache[key]
                if time.time() < expiry:
                    return value
                else:
                    del self.cache[key]
        return None

    def set(self, value: Any, ttl: Optional[int] = None, *args, **kwargs):
        """Cache value with TTL"""
        key = self._make_key(*args, **kwargs)
        expiry = time.time() + (ttl or self.default_ttl)
        with self.lock:
            self.cache[key] = (value, expiry)

    def clear(self):
        """Clear all cached values"""
        with self.lock:
            self.cache.clear()


class OnChainDataProvider:
    """
    Main class for on-chain data integration.

    Provides whale tracking, exchange flow analysis, and confidence scoring
    to enhance existing trading signals.

    Usage:
        provider = OnChainDataProvider(
            whale_alert_api_key="your_key",
            glassnode_api_key="your_key"
        )

        # Get confidence boost for a long signal
        confidence = provider.calculate_confidence_boost("BTC", "long")
    """

    # Known exchange addresses (subset for filtering)
    KNOWN_EXCHANGES = {
        "binance": ["1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s"],  # Example
        "coinbase": ["3F9CGMu7JSJnMHAzntfkgE8ykhVg6x3Z6Z"],
        "kraken": ["3EeqjXDWxW1xXwHpdj1mEY6J7Y7Y7Y7Y7Y"],
        "bitfinex": ["3D2oetdNuZUqQHPJmcMDDHYoqkyNVsFk9r"],
        "okx": ["3FupZp77ySr7jwoLYEJ9oLqDqDqDqDqDqD"],
    }

    # Known staking addresses
    KNOWN_STAKING = {
        "lido": ["0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"],
        "rocketpool": ["0x1CC9cF5596522c6F997E1122b123B36E3b706791"],
    }

    # Whale threshold in USD
    WHALE_THRESHOLD_USD = 10_000_000  # $10M
    MAJOR_WHALE_THRESHOLD_USD = 50_000_000  # $50M

    def __init__(
        self,
        whale_alert_api_key: Optional[str] = None,
        glassnode_api_key: Optional[str] = None,
        dune_api_key: Optional[str] = None,
        cache_ttl: int = 300,
        whale_alert_rate_limit: int = 10,  # 10 calls/min for free tier
    ):
        """
        Initialize the on-chain data provider.

        Args:
            whale_alert_api_key: API key for Whale Alert
            glassnode_api_key: API key for Glassnode
            dune_api_key: API key for Dune Analytics
            cache_ttl: Cache time-to-live in seconds
            whale_alert_rate_limit: Max calls per minute for Whale Alert
        """
        self.whale_alert_api_key = whale_alert_api_key
        self.glassnode_api_key = glassnode_api_key
        self.dune_api_key = dune_api_key

        # Initialize rate limiters
        self.whale_limiter = RateLimiter(whale_alert_rate_limit)
        self.glassnode_limiter = RateLimiter(30)  # Conservative for free tier

        # Initialize cache
        self.cache = Cache(cache_ttl)

        # API endpoints
        self.whale_alert_base = "https://api.whale-alert.io/v1"
        self.glassnode_base = "https://api.glassnode.com/v1"

        # Track API usage
        self.api_calls = defaultdict(int)
        self.api_calls_reset_time = datetime.now() + timedelta(days=1)

    def _check_api_reset(self):
        """Reset API call counters if day has passed"""
        if datetime.now() >= self.api_calls_reset_time:
            self.api_calls.clear()
            self.api_calls_reset_time = datetime.now() + timedelta(days=1)

    def _make_request(
        self, 
        url: str, 
        params: Optional[Dict] = None, 
        headers: Optional[Dict] = None,
        api_name: str = "unknown"
    ) -> Optional[Dict]:
        """Make HTTP request with error handling"""
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            self.api_calls[api_name] += 1

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                logger.warning(f"Rate limit hit for {api_name}")
                return None
            else:
                logger.warning(f"API error {response.status_code} for {api_name}")
                return None
        except Exception as e:
            logger.error(f"Request failed for {api_name}: {e}")
            return None

    def get_whale_flows(
        self,
        symbol: str,
        min_value_usd: float = 10_000_000,
        hours_back: int = 24,
        blockchain: Optional[str] = None
    ) -> List[WhaleTransaction]:
        """
        Fetch whale transactions from Whale Alert API.

        Args:
            symbol: Crypto symbol (e.g., "BTC", "ETH")
            min_value_usd: Minimum transaction value in USD
            hours_back: How many hours to look back
            blockchain: Specific blockchain (optional)

        Returns:
            List of WhaleTransaction objects
        """
        if not self.whale_alert_api_key:
            logger.warning("Whale Alert API key not provided")
            return []

        # Check cache
        cache_key = ("whale_flows", symbol, min_value_usd, hours_back, blockchain)
        cached = self.cache.get(*cache_key)
        if cached:
            return cached

        # Rate limit
        self.whale_limiter.wait()

        # Calculate timestamp
        start_time = int((datetime.now() - timedelta(hours=hours_back)).timestamp())

        # Build request
        url = f"{self.whale_alert_base}/transactions"
        params = {
            "api_key": self.whale_alert_api_key,
            "min_value": min_value_usd,
            "start": start_time,
            "currency": symbol.lower(),
        }
        if blockchain:
            params["blockchain"] = blockchain

        # Make request
        data = self._make_request(url, params, api_name="whale_alert")

        if not data or "transactions" not in data:
            return []

        # Parse transactions
        transactions = []
        for tx in data.get("transactions", []):
            whale_tx = WhaleTransaction(
                tx_hash=tx.get("hash", ""),
                timestamp=datetime.fromtimestamp(tx.get("timestamp", 0)),
                from_address=tx.get("from", {}).get("address", ""),
                to_address=tx.get("to", {}).get("address", ""),
                amount=tx.get("amount", 0),
                amount_usd=tx.get("amount_usd", 0),
                symbol=tx.get("symbol", symbol).upper(),
                blockchain=tx.get("blockchain", "unknown"),
                from_entity=tx.get("from", {}).get("owner", ""),
                to_entity=tx.get("to", {}).get("owner", ""),
            )

            # Classify flow type
            whale_tx.flow_type = self._classify_flow(whale_tx)

            # Calculate individual confidence
            whale_tx.confidence_score = self._calculate_tx_confidence(whale_tx)

            transactions.append(whale_tx)

        # Cache and return
        self.cache.set(transactions, 60, *cache_key)  # 1 min cache for whale data
        return transactions

    def _classify_flow(self, tx: WhaleTransaction) -> FlowType:
        """
        Classify transaction flow type with false positive filtering.

        Returns:
            FlowType classification
        """
        from_addr = tx.from_address.lower()
        to_addr = tx.to_address.lower()
        from_entity = (tx.from_entity or "").lower()
        to_entity = (tx.to_entity or "").lower()

        # Check for staking (filter out as false positive)
        for staking_name, addresses in self.KNOWN_STAKING.items():
            if any(addr.lower() in [from_addr, to_addr] for addr in addresses):
                return FlowType.STAKING

        # Check for known staking keywords
        staking_keywords = ["stake", "staking", "lido", "rocketpool", "validator"]
        if any(kw in from_entity or kw in to_entity for kw in staking_keywords):
            return FlowType.STAKING

        # Check for OTC (filter out as false positive)
        otc_keywords = ["otc", "over-the-counter", "institutional", "custody"]
        if any(kw in from_entity or kw in to_entity for kw in otc_keywords):
            return FlowType.OTC

        # Check for exchange flows
        is_from_exchange = any(
            ex in from_entity or any(addr.lower() == from_addr for addr in addrs)
            for ex, addrs in self.KNOWN_EXCHANGES.items()
        )
        is_to_exchange = any(
            ex in to_entity or any(addr.lower() == to_addr for addr in addrs)
            for ex, addrs in self.KNOWN_EXCHANGES.items()
        )

        if is_from_exchange and not is_to_exchange:
            return FlowType.EXCHANGE_OUTFLOW  # Bullish
        elif is_to_exchange and not is_from_exchange:
            return FlowType.EXCHANGE_INFLOW   # Bearish

        # Whale wallet to whale wallet
        if tx.amount_usd >= self.WHALE_THRESHOLD_USD:
            return FlowType.WHALE_WALLET

        return FlowType.UNKNOWN

    def _calculate_tx_confidence(self, tx: WhaleTransaction) -> float:
        """
        Calculate confidence score for individual transaction.

        Higher scores for:
        - Larger amounts
        - Confirmed exchange flows
        - Multiple confirmations
        """
        score = 0.0

        # Amount-based scoring
        if tx.amount_usd >= self.MAJOR_WHALE_THRESHOLD_USD:
            score += 0.4
        elif tx.amount_usd >= self.WHALE_THRESHOLD_USD:
            score += 0.25

        # Flow type scoring
        if tx.flow_type == FlowType.EXCHANGE_OUTFLOW:
            score += 0.35  # Strong bullish signal
        elif tx.flow_type == FlowType.EXCHANGE_INFLOW:
            score += 0.35  # Strong bearish signal
        elif tx.flow_type == FlowType.WHALE_WALLET:
            score += 0.15  # Moderate signal

        # Entity verification bonus
        if tx.from_entity or tx.to_entity:
            score += 0.1

        return min(score, 1.0)

    def get_exchange_flows(
        self,
        symbol: str,
        hours_back: int = 24,
        exchange: Optional[str] = None
    ) -> List[ExchangeFlow]:
        """
        Fetch exchange flow data from Glassnode or Dune.

        Note: This is a simplified implementation. In production, you would
        integrate with Glassnode's exchange flow endpoints or Dune queries.

        Args:
            symbol: Crypto symbol
            hours_back: Hours to look back
            exchange: Specific exchange (optional)

        Returns:
            List of ExchangeFlow objects
        """
        # Check cache
        cache_key = ("exchange_flows", symbol, hours_back, exchange)
        cached = self.cache.get(*cache_key)
        if cached:
            return cached

        # Try Glassnode if available
        if self.glassnode_api_key:
            flows = self._get_glassnode_exchange_flows(symbol, hours_back, exchange)
        else:
            # Fallback: estimate from whale data
            flows = self._estimate_exchange_flows_from_whales(symbol, hours_back)

        self.cache.set(flows, 300, *cache_key)  # 5 min cache
        return flows

    def _get_glassnode_exchange_flows(
        self,
        symbol: str,
        hours_back: int,
        exchange: Optional[str] = None
    ) -> List[ExchangeFlow]:
        """Fetch exchange flows from Glassnode API"""
        self.glassnode_limiter.wait()

        # Glassnode endpoint for exchange netflows
        endpoint = f"/metrics/distribution/exchange_netflow"
        url = f"{self.glassnode_base}{endpoint}"

        params = {
            "a": symbol.upper(),
            "api_key": self.glassnode_api_key,
            "i": "1h",  # 1 hour intervals
        }

        data = self._make_request(url, params, api_name="glassnode")

        if not data or not isinstance(data, list):
            return []

        flows = []
        cutoff_time = datetime.now() - timedelta(hours=hours_back)

        for item in data:
            timestamp = datetime.fromtimestamp(item.get("t", 0))
            if timestamp < cutoff_time:
                continue

            netflow = item.get("v", 0)

            # Estimate inflow/outflow from netflow
            # This is simplified - real implementation would fetch both
            estimated_inflow = max(0, -netflow) if netflow < 0 else 0
            estimated_outflow = max(0, netflow) if netflow > 0 else 0

            flow = ExchangeFlow(
                exchange=exchange or "aggregated",
                timestamp=timestamp,
                inflow=estimated_inflow,
                outflow=estimated_outflow,
                netflow=netflow,
                inflow_usd=estimated_inflow,  # Would convert to USD
                outflow_usd=estimated_outflow,
                netflow_usd=netflow,
                symbol=symbol.upper(),
            )
            flows.append(flow)

        return flows

    def _estimate_exchange_flows_from_whales(
        self,
        symbol: str,
        hours_back: int
    ) -> List[ExchangeFlow]:
        """
        Estimate exchange flows from whale transaction data.
        Used as fallback when Glassnode is unavailable.
        """
        whale_txs = self.get_whale_flows(symbol, hours_back=hours_back)

        # Aggregate by hour
        hourly_flows = defaultdict(lambda: {"inflow": 0, "outflow": 0})

        for tx in whale_txs:
            hour_key = tx.timestamp.replace(minute=0, second=0, microsecond=0)

            if tx.flow_type == FlowType.EXCHANGE_INFLOW:
                hourly_flows[hour_key]["inflow"] += tx.amount
            elif tx.flow_type == FlowType.EXCHANGE_OUTFLOW:
                hourly_flows[hour_key]["outflow"] += tx.amount

        # Create ExchangeFlow objects
        flows = []
        for hour, data in sorted(hourly_flows.items()):
            flow = ExchangeFlow(
                exchange="estimated_from_whales",
                timestamp=hour,
                inflow=data["inflow"],
                outflow=data["outflow"],
                netflow=data["outflow"] - data["inflow"],
                inflow_usd=data["inflow"],  # Simplified
                outflow_usd=data["outflow"],
                netflow_usd=data["outflow"] - data["inflow"],
                symbol=symbol.upper(),
            )
            flows.append(flow)

        return flows

    def calculate_confidence_boost(
        self,
        symbol: str,
        signal_direction: str,  # "long" or "short"
        lookback_hours: int = 24,
        base_confidence: float = 0.5
    ) -> OnChainSignal:
        """
        Calculate confidence boost based on on-chain data.

        This is the main method for integrating on-chain data with
        existing trading signals. Returns a confidence score (0-1) that
        can be used to scale position sizes or filter trades.

        Args:
            symbol: Trading pair symbol (e.g., "BTC")
            signal_direction: "long" or "short"
            lookback_hours: How many hours of data to analyze
            base_confidence: Starting confidence level

        Returns:
            OnChainSignal with combined confidence score
        """
        evidence = []
        warnings = []

        # Get whale data
        whale_txs = self.get_whale_flows(symbol, hours_back=lookback_hours)

        # Filter out false positives
        valid_whales = [
            tx for tx in whale_txs 
            if tx.flow_type not in [FlowType.STAKING, FlowType.OTC]
        ]

        # Calculate whale score
        whale_score = self._calculate_whale_score(valid_whales, signal_direction)

        # Get exchange flows
        exchange_flows = self.get_exchange_flows(symbol, hours_back=lookback_hours)

        # Calculate exchange score
        exchange_score = self._calculate_exchange_score(exchange_flows, signal_direction)

        # Combine scores with weights
        # Whale movements: 40%, Exchange flows: 60%
        # Exchange flows are generally more reliable
        combined_score = (whale_score * 0.4) + (exchange_score * 0.6)

        # Build evidence list
        if whale_score > 0.6:
            bullish_whales = sum(1 for tx in valid_whales 
                               if tx.flow_type == FlowType.EXCHANGE_OUTFLOW)
            evidence.append(f"{bullish_whales} major exchange outflows detected")

        if exchange_score > 0.6:
            netflow = sum(f.netflow for f in exchange_flows)
            if signal_direction == "long" and netflow > 0:
                evidence.append(f"Net exchange outflow: {netflow:,.2f} {symbol}")
            elif signal_direction == "short" and netflow < 0:
                evidence.append(f"Net exchange inflow: {abs(netflow):,.2f} {symbol}")

        # Add warnings
        if len(valid_whales) < 3:
            warnings.append("Limited whale activity - low signal strength")

        # Filtered transactions
        filtered = len(whale_txs) - len(valid_whales)
        if filtered > 0:
            evidence.append(f"Filtered {filtered} staking/OTC transactions")

        return OnChainSignal(
            symbol=symbol,
            timestamp=datetime.now(),
            whale_score=whale_score,
            exchange_score=exchange_score,
            combined_score=combined_score,
            supporting_evidence=evidence,
            warnings=warnings
        )

    def _calculate_whale_score(
        self, 
        whale_txs: List[WhaleTransaction], 
        signal_direction: str
    ) -> float:
        """
        Calculate whale-based confidence score.

        Scoring logic:
        - Long signals: Look for exchange outflows (accumulation)
        - Short signals: Look for exchange inflows (distribution)
        """
        if not whale_txs:
            return 0.5  # Neutral if no data

        # Categorize transactions
        outflows = [tx for tx in whale_txs if tx.flow_type == FlowType.EXCHANGE_OUTFLOW]
        inflows = [tx for tx in whale_txs if tx.flow_type == FlowType.EXCHANGE_INFLOW]
        whale_wallet = [tx for tx in whale_txs if tx.flow_type == FlowType.WHALE_WALLET]

        # Calculate weighted volumes
        outflow_volume = sum(tx.amount_usd for tx in outflows)
        inflow_volume = sum(tx.amount_usd for tx in inflows)
        whale_volume = sum(tx.amount_usd for tx in whale_wallet)

        total_volume = outflow_volume + inflow_volume + whale_volume
        if total_volume == 0:
            return 0.5

        # Calculate ratios
        outflow_ratio = outflow_volume / total_volume
        inflow_ratio = inflow_volume / total_volume

        # Score based on signal direction
        if signal_direction == "long":
            # For longs, outflows are bullish
            # Score: 0.5 + (outflow_ratio - inflow_ratio) * 0.5
            score = 0.5 + (outflow_ratio - inflow_ratio) * 0.5

            # Bonus for major whale movements
            major_outflows = sum(1 for tx in outflows 
                               if tx.amount_usd >= self.MAJOR_WHALE_THRESHOLD_USD)
            score += min(major_outflows * 0.05, 0.15)

        else:  # short
            # For shorts, inflows are bearish
            score = 0.5 + (inflow_ratio - outflow_ratio) * 0.5

            # Bonus for major whale movements
            major_inflows = sum(1 for tx in inflows 
                              if tx.amount_usd >= self.MAJOR_WHALE_THRESHOLD_USD)
            score += min(major_inflows * 0.05, 0.15)

        # Clamp to [0, 1]
        return max(0.0, min(1.0, score))

    def _calculate_exchange_score(
        self, 
        flows: List[ExchangeFlow], 
        signal_direction: str
    ) -> float:
        """
        Calculate exchange flow-based confidence score.

        Scoring logic:
        - Net outflow (positive) = accumulation = bullish
        - Net inflow (negative) = distribution = bearish
        """
        if not flows:
            return 0.5  # Neutral if no data

        # Calculate total netflow
        total_netflow = sum(f.netflow for f in flows)
        total_volume = sum(abs(f.inflow) + abs(f.outflow) for f in flows)

        if total_volume == 0:
            return 0.5

        # Netflow ratio (-1 to 1)
        netflow_ratio = total_netflow / total_volume if total_volume > 0 else 0

        # Calculate score based on direction
        if signal_direction == "long":
            # Positive netflow (outflow) supports longs
            score = 0.5 + netflow_ratio * 0.5
        else:
            # Negative netflow (inflow) supports shorts
            score = 0.5 - netflow_ratio * 0.5

        # Add consistency bonus
        consistent_direction = sum(
            1 for f in flows 
            if (signal_direction == "long" and f.netflow > 0) or
               (signal_direction == "short" and f.netflow < 0)
        )
        consistency_ratio = consistent_direction / len(flows) if flows else 0
        score += consistency_ratio * 0.1

        return max(0.0, min(1.0, score))

    def get_api_usage_stats(self) -> Dict:
        """Get current API usage statistics"""
        self._check_api_reset()
        return {
            "calls_today": dict(self.api_calls),
            "reset_time": self.api_calls_reset_time.isoformat(),
            "cache_entries": len(self.cache.cache),
        }


# ============================================================================
# INTEGRATION EXAMPLE
# ============================================================================

class SignalEnhancer:
    """
    Example integration class showing how to use OnChainDataProvider
    to enhance existing trading signals.
    """

    def __init__(self, onchain_provider: OnChainDataProvider):
        self.provider = onchain_provider

        # Confidence thresholds for position sizing
        self.thresholds = {
            "minimum": 0.4,    # Don't trade below this
            "small": 0.5,      # 50% position size
            "medium": 0.65,    # 75% position size
            "full": 0.8,       # 100% position size
            "boost": 0.9,      # 125% position size (overweight)
        }

    def enhance_signal(
        self,
        symbol: str,
        base_signal: str,  # "buy" or "sell"
        base_confidence: float,
        strategy_wr: float = 0.624  # Your current win rate
    ) -> Dict:
        """
        Enhance existing signal with on-chain confidence boost.

        Returns enhanced signal with position size recommendation.
        """
        direction = "long" if base_signal == "buy" else "short"

        # Get on-chain confidence
        onchain = self.provider.calculate_confidence_boost(
            symbol=symbol,
            signal_direction=direction,
            base_confidence=base_confidence
        )

        # Calculate combined confidence
        # Weight: 70% technical, 30% on-chain
        combined_confidence = (base_confidence * 0.7) + (onchain.combined_score * 0.3)

        # Determine position size
        position_size = self._calculate_position_size(combined_confidence)

        # Calculate expected value
        expected_value = self._calculate_expected_value(
            combined_confidence, strategy_wr
        )

        return {
            "symbol": symbol,
            "base_signal": base_signal,
            "base_confidence": base_confidence,
            "onchain_confidence": onchain.combined_score,
            "combined_confidence": combined_confidence,
            "position_size_pct": position_size,
            "expected_value": expected_value,
            "whale_score": onchain.whale_score,
            "exchange_score": onchain.exchange_score,
            "evidence": onchain.supporting_evidence,
            "warnings": onchain.warnings,
            "execute": combined_confidence >= self.thresholds["minimum"],
        }

    def _calculate_position_size(self, confidence: float) -> float:
        """Calculate position size based on confidence"""
        if confidence < self.thresholds["minimum"]:
            return 0.0
        elif confidence < self.thresholds["small"]:
            return 0.5
        elif confidence < self.thresholds["medium"]:
            return 0.75
        elif confidence < self.thresholds["full"]:
            return 1.0
        else:
            return 1.25

    def _calculate_expected_value(
        self, 
        confidence: float, 
        win_rate: float,
        avg_win: float = 2.0,  # R multiples
        avg_loss: float = 1.0
    ) -> float:
        """Calculate expected value of trade"""
        # Adjust win rate by confidence
        adjusted_wr = win_rate * confidence

        # EV = (Win% * Avg Win) - (Loss% * Avg Loss)
        ev = (adjusted_wr * avg_win) - ((1 - adjusted_wr) * avg_loss)
        return ev


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

def example_usage():
    """Example of how to use the on-chain data module"""

    # Initialize provider (with your API keys)
    provider = OnChainDataProvider(
        whale_alert_api_key="your_whale_alert_key",
        glassnode_api_key="your_glassnode_key",
    )

    # Initialize signal enhancer
    enhancer = SignalEnhancer(provider)

    # Example: Your existing Keltner/RSI signal
    your_signal = {
        "symbol": "BTC",
        "signal": "buy",
        "confidence": 0.65,  # Your technical confidence
    }

    # Enhance with on-chain data
    enhanced = enhancer.enhance_signal(
        symbol=your_signal["symbol"],
        base_signal=your_signal["signal"],
        base_confidence=your_signal["confidence"],
    )

    print("=" * 60)
    print("SIGNAL ENHANCEMENT RESULT")
    print("=" * 60)
    print(f"Symbol: {enhanced['symbol']}")
    print(f"Base Confidence: {enhanced['base_confidence']:.2%}")
    print(f"On-Chain Confidence: {enhanced['onchain_confidence']:.2%}")
    print(f"Combined Confidence: {enhanced['combined_confidence']:.2%}")
    print(f"Position Size: {enhanced['position_size_pct']:.0%}")
    print(f"Expected Value: {enhanced['expected_value']:.3f}R")
    print(f"Execute: {enhanced['execute']}")
    print("\nEvidence:")
    for e in enhanced['evidence']:
        print(f"  + {e}")
    print("\nWarnings:")
    for w in enhanced['warnings']:
        print(f"  ! {w}")

    return enhanced


if __name__ == "__main__":
    example_usage()
