"""
ML-Based Execution Optimization System for Cryptocurrency Trading
=================================================================

This module implements a machine learning approach to optimize trade execution
by classifying liquidity conditions in L2 order book data, rather than 
predicting price direction.

Academic Foundation:
- Bertsimas & Lo (1998): "Optimal Control of Execution Costs"
- Almgren & Chriss (2000): "Optimal Execution of Portfolio Transactions"
- Cont et al. (2014): "Price dynamics in a Markovian limit order market"

Author: Quantitative Finance Research Team
"""

import asyncio
import json
import logging
import numpy as np
import pandas as pd
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Callable, Any
import websockets
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler, LabelEncoder
import xgboost as xgb
import joblib
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LiquidityCondition(Enum):
    """Classification of current market liquidity conditions."""
    TIGHT_DEEP = "tight_deep"        # Tight spread, deep book - ideal for market orders
    TIGHT_SHALLOW = "tight_shallow"  # Tight spread, shallow book - use small market orders
    WIDE_DEEP = "wide_deep"          # Wide spread, deep book - use limit orders
    WIDE_SHALLOW = "wide_shallow"    # Wide spread, shallow book - avoid or wait
    IMBALANCED_BUY = "imbalanced_buy"    # Heavy bid pressure - buy urgency
    IMBALANCED_SELL = "imbalanced_sell"  # Heavy ask pressure - sell urgency


class ExecutionRecommendation(Enum):
    """Recommended execution strategy based on liquidity analysis."""
    MARKET_ORDER_NOW = "market_order_now"
    LIMIT_ORDER_PASSIVE = "limit_order_passive"
    LIMIT_ORDER_AGGRESSIVE = "limit_order_aggressive"
    WAIT_IMPROVE = "wait_improve"
    SPLIT_ORDER = "split_order"
    CANCEL_WAIT = "cancel_wait"


@dataclass
class OrderBookLevel:
    """Represents a single level in the order book."""
    price: float
    quantity: float
    order_count: Optional[int] = None

    @property
    def value(self) -> float:
        """Dollar value at this level."""
        return self.price * self.quantity


@dataclass
class OrderBookSnapshot:
    """Complete snapshot of L2 order book at a point in time."""
    symbol: str
    timestamp: datetime
    bids: List[OrderBookLevel] = field(default_factory=list)
    asks: List[OrderBookLevel] = field(default_factory=list)

    @property
    def best_bid(self) -> Optional[float]:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> Optional[float]:
        return self.asks[0].price if self.asks else None

    @property
    def mid_price(self) -> Optional[float]:
        if self.best_bid and self.best_ask:
            return (self.best_bid + self.best_ask) / 2
        return None

    @property
    def spread(self) -> Optional[float]:
        if self.best_bid and self.best_ask:
            return self.best_ask - self.best_bid
        return None

    @property
    def spread_bps(self) -> Optional[float]:
        """Spread in basis points."""
        if self.spread and self.mid_price:
            return (self.spread / self.mid_price) * 10000
        return None


@dataclass
class ExecutionSignal:
    """Output signal from the execution optimizer."""
    symbol: str
    timestamp: datetime
    side: str  # 'buy' or 'sell'
    quantity: float
    liquidity_condition: LiquidityCondition
    recommendation: ExecutionRecommendation
    expected_slippage_bps: float
    confidence: float
    features: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'side': self.side,
            'quantity': self.quantity,
            'liquidity_condition': self.liquidity_condition.value,
            'recommendation': self.recommendation.value,
            'expected_slippage_bps': self.expected_slippage_bps,
            'confidence': self.confidence,
            'features': self.features
        }


class OrderBookFeatureEngineer:
    """
    Feature engineering for L2 order book data.
    Extracts meaningful features for liquidity classification.
    """

    def __init__(self, depth_levels: int = 10):
        self.depth_levels = depth_levels
        self.price_history = deque(maxlen=100)
        self.feature_history = deque(maxlen=1000)

    def extract_features(self, snapshot: OrderBookSnapshot) -> Dict[str, float]:
        """
        Extract comprehensive features from order book snapshot.

        Features based on academic research:
        - Depth imbalance (Cont et al., 2014)
        - Bid-ask spread metrics
        - Order flow toxicity (VPIN-like measures)
        - Price impact estimates
        """
        features = {}

        if not snapshot.bids or not snapshot.asks:
            return features

        mid = snapshot.mid_price
        spread = snapshot.spread
        spread_bps = snapshot.spread_bps

        # Basic features
        features['mid_price'] = mid
        features['spread'] = spread
        features['spread_bps'] = spread_bps
        features['best_bid'] = snapshot.best_bid
        features['best_ask'] = snapshot.best_ask

        # Depth features at different levels
        bid_depths = [level.quantity for level in snapshot.bids[:self.depth_levels]]
        ask_depths = [level.quantity for level in snapshot.asks[:self.depth_levels]]
        bid_values = [level.value for level in snapshot.bids[:self.depth_levels]]
        ask_values = [level.value for level in snapshot.asks[:self.depth_levels]]

        # Cumulative depth
        features['bid_depth_l1'] = bid_depths[0] if bid_depths else 0
        features['ask_depth_l1'] = ask_depths[0] if ask_depths else 0
        features['bid_depth_l5'] = sum(bid_depths[:5]) if len(bid_depths) >= 5 else sum(bid_depths)
        features['ask_depth_l5'] = sum(ask_depths[:5]) if len(ask_depths) >= 5 else sum(ask_depths)
        features['bid_depth_l10'] = sum(bid_depths)
        features['ask_depth_l10'] = sum(ask_depths)

        # Value-weighted depth (more important)
        features['bid_value_l5'] = sum(bid_values[:5]) if len(bid_values) >= 5 else sum(bid_values)
        features['ask_value_l5'] = sum(ask_values[:5]) if len(ask_values) >= 5 else sum(ask_values)

        # Depth imbalance (key predictor of short-term price movement)
        total_bid_depth = features['bid_depth_l5']
        total_ask_depth = features['ask_depth_l5']

        if total_bid_depth + total_ask_depth > 0:
            features['depth_imbalance'] = (total_bid_depth - total_ask_depth) / (total_bid_depth + total_ask_depth)
        else:
            features['depth_imbalance'] = 0

        if features['bid_value_l5'] + features['ask_value_l5'] > 0:
            features['value_imbalance'] = (features['bid_value_l5'] - features['ask_value_l5']) / (features['bid_value_l5'] + features['ask_value_l5'])
        else:
            features['value_imbalance'] = 0

        # Level 1 imbalance (most immediate pressure)
        if features['bid_depth_l1'] + features['ask_depth_l1'] > 0:
            features['l1_imbalance'] = (features['bid_depth_l1'] - features['ask_depth_l1']) / (features['bid_depth_l1'] + features['ask_depth_l1'])
        else:
            features['l1_imbalance'] = 0

        # Spread relative to depth (liquidity score)
        avg_depth = (features['bid_depth_l5'] + features['ask_depth_l5']) / 2
        if avg_depth > 0:
            features['liquidity_score'] = 1 / (spread_bps / 100 + 1 / (avg_depth + 1))
        else:
            features['liquidity_score'] = 0

        # Price impact estimates (based on square-root law)
        # Impact ≈ σ * sqrt(Q/ADV) where Q is order size
        for size in [0.1, 0.5, 1.0, 5.0]:  # BTC sizes
            if features['bid_depth_l5'] > 0:
                features[f'buy_impact_{size}btc'] = self._estimate_impact(size, features['bid_depth_l5'], spread_bps)
            if features['ask_depth_l5'] > 0:
                features[f'sell_impact_{size}btc'] = self._estimate_impact(size, features['ask_depth_l5'], spread_bps)

        # Book slope (steepness of order book)
        if len(bid_depths) >= 3:
            bid_prices = [level.price for level in snapshot.bids[:3]]
            bid_sizes = [level.quantity for level in snapshot.bids[:3]]
            price_range = max(bid_prices) - min(bid_prices)
            if price_range > 0:
                features['bid_slope'] = (bid_sizes[0] - bid_sizes[-1]) / price_range
            else:
                features['bid_slope'] = 0

        if len(ask_depths) >= 3:
            ask_prices = [level.price for level in snapshot.asks[:3]]
            ask_sizes = [level.quantity for level in snapshot.asks[:3]]
            price_range = max(ask_prices) - min(ask_prices)
            if price_range > 0:
                features['ask_slope'] = (ask_sizes[-1] - ask_sizes[0]) / price_range
            else:
                features['ask_slope'] = 0

        # Store for time-based features
        self.price_history.append(mid)
        self.feature_history.append(features)

        # Time-based features if we have history
        if len(self.price_history) >= 10:
            prices = list(self.price_history)
            features['price_volatility_10'] = np.std(prices[-10:]) / np.mean(prices[-10:]) * 10000 if np.mean(prices[-10:]) > 0 else 0

        if len(self.feature_history) >= 2:
            prev = self.feature_history[-2]
            features['depth_imbalance_change'] = features['depth_imbalance'] - prev.get('depth_imbalance', 0)
            features['spread_change'] = spread_bps - prev.get('spread_bps', 0)

        return features

    def _estimate_impact(self, order_size: float, depth: float, spread_bps: float) -> float:
        """
        Estimate price impact in bps using square-root law.
        Impact = spread/2 + k * sqrt(order_size / depth)
        """
        if depth <= 0:
            return spread_bps
        k = 5  # Impact coefficient (market-dependent)
        temporary_impact = k * np.sqrt(order_size / depth) * 100  # Convert to bps
        return spread_bps / 2 + temporary_impact


class LiquidityClassifier:
    """
    Machine Learning classifier for liquidity conditions.
    Uses Random Forest or XGBoost to classify market state.
    """

    def __init__(self, model_type: str = 'xgboost', model_path: Optional[str] = None):
        self.model_type = model_type
        self.model_path = model_path
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.feature_names = []
        self.is_trained = False
        self.num_classes = None

        if model_path:
            self.load_model(model_path)

    def _initialize_model(self, num_classes: int = None):
        """Initialize the ML model."""
        # Always create a fresh model instance to avoid cached state issues
        if self.model_type == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=20,
                min_samples_leaf=10,
                random_state=42,
                n_jobs=-1
            )
        elif self.model_type == 'xgboost':
            import xgboost as xgb_module
            # Force create a completely new classifier
            self.model = xgb_module.XGBClassifier.__new__(xgb_module.XGBClassifier)
            self.model.__init__(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1
            )
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")

    def prepare_features(self, features: Dict[str, float]) -> np.ndarray:
        """Convert feature dictionary to numpy array."""
        if not self.feature_names:
            # Initialize feature names from first sample
            self.feature_names = sorted([k for k in features.keys() if k not in ['mid_price', 'best_bid', 'best_ask']])

        return np.array([features.get(name, 0) for name in self.feature_names]).reshape(1, -1)

    def train(self, X: np.ndarray, y: np.ndarray):
        """Train the liquidity classifier."""
        logger.info(f"Training {self.model_type} model on {len(X)} samples")

        # Encode labels
        y_encoded = self.label_encoder.fit_transform(y)
        num_classes = len(self.label_encoder.classes_)
        logger.info(f"Classes: {self.label_encoder.classes_}")
        
        # Re-initialize model with correct number of classes
        self._initialize_model(num_classes=num_classes)

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Train model
        self.model.fit(X_scaled, y_encoded)
        self.is_trained = True

        # Log feature importance
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            for name, imp in zip(self.feature_names, importances):
                logger.info(f"  {name}: {imp:.4f}")

        logger.info("Training complete")

    def predict(self, features: Dict[str, float]) -> Tuple[LiquidityCondition, float]:
        """
        Predict liquidity condition from features.
        Returns condition and confidence score.
        """
        if not self.is_trained:
            # Fallback to rule-based classification
            return self._rule_based_classify(features)

        X = self.prepare_features(features)
        X_scaled = self.scaler.transform(X)

        # Get prediction and probabilities
        prediction_encoded = self.model.predict(X_scaled)[0]
        probabilities = self.model.predict_proba(X_scaled)[0]
        confidence = max(probabilities)

        # Decode label
        prediction_label = self.label_encoder.inverse_transform([prediction_encoded])[0]
        condition = LiquidityCondition(prediction_label)
        return condition, confidence

    def _rule_based_classify(self, features: Dict[str, float]) -> Tuple[LiquidityCondition, float]:
        """Rule-based classification when model is not trained."""
        spread_bps = features.get('spread_bps', 10)
        depth_imbalance = features.get('depth_imbalance', 0)
        bid_depth = features.get('bid_depth_l5', 0)
        ask_depth = features.get('ask_depth_l5', 0)

        # Define thresholds
        TIGHT_SPREAD = 5  # bps
        DEEP_BOOK = 10    # BTC
        IMBALANCE_THRESHOLD = 0.3

        # Check imbalance first (most important)
        if depth_imbalance > IMBALANCE_THRESHOLD:
            return LiquidityCondition.IMBALANCED_BUY, 0.7
        elif depth_imbalance < -IMBALANCE_THRESHOLD:
            return LiquidityCondition.IMBALANCED_SELL, 0.7

        # Check spread and depth
        is_tight = spread_bps < TIGHT_SPREAD
        is_deep = (bid_depth > DEEP_BOOK) and (ask_depth > DEEP_BOOK)

        if is_tight and is_deep:
            return LiquidityCondition.TIGHT_DEEP, 0.8
        elif is_tight and not is_deep:
            return LiquidityCondition.TIGHT_SHALLOW, 0.7
        elif not is_tight and is_deep:
            return LiquidityCondition.WIDE_DEEP, 0.7
        else:
            return LiquidityCondition.WIDE_SHALLOW, 0.8

    def save_model(self, path: str):
        """Save model to disk."""
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'label_encoder': self.label_encoder,
            'feature_names': self.feature_names,
            'model_type': self.model_type
        }, path)
        logger.info(f"Model saved to {path}")

    def load_model(self, path: str):
        """Load model from disk."""
        data = joblib.load(path)
        self.model = data['model']
        self.scaler = data['scaler']
        self.label_encoder = data['label_encoder']
        self.feature_names = data['feature_names']
        self.model_type = data['model_type']
        self.is_trained = True
        logger.info(f"Model loaded from {path}")


class SlippageEstimator:
    """
    Estimates expected slippage for different execution strategies.
    Based on market impact models from Almgren & Chriss (2000).
    """

    def __init__(self):
        # Impact model parameters (can be calibrated from historical data)
        self.eta = 0.1  # Temporary impact coefficient
        self.gamma = 0.01  # Permanent impact coefficient
        self.sigma = 0.02  # Volatility (2% per day)

    def estimate_market_order_slippage(
        self, 
        quantity: float, 
        features: Dict[str, float],
        side: str
    ) -> float:
        """
        Estimate slippage in bps for a market order.

        Uses square-root impact law:
        Slippage = (Spread/2) + η * σ * sqrt(Q/D)

        Where:
        - Q = order quantity
        - D = depth at relevant side
        - σ = volatility
        - η = impact coefficient
        """
        spread_bps = features.get('spread_bps', 10)

        if side == 'buy':
            depth = features.get('bid_depth_l5', 1)
        else:
            depth = features.get('ask_depth_l5', 1)

        # Base slippage is half the spread
        base_slippage = spread_bps / 2

        # Market impact component
        if depth > 0:
            impact = self.eta * self.sigma * np.sqrt(quantity / depth) * 10000
        else:
            impact = spread_bps * 2  # High impact if no depth

        return base_slippage + impact

    def estimate_limit_order_fill_probability(
        self,
        quantity: float,
        limit_price_offset_bps: float,
        features: Dict[str, float],
        side: str,
        max_wait_seconds: int = 300
    ) -> Tuple[float, float]:
        """
        Estimate fill probability and time for a limit order.

        Returns:
            (fill_probability, expected_fill_time_seconds)
        """
        spread_bps = features.get('spread_bps', 10)
        depth_imbalance = features.get('depth_imbalance', 0)

        # Adjust for side
        if side == 'sell':
            depth_imbalance = -depth_imbalance

        # Probability increases with how aggressive the limit is
        # and with favorable depth imbalance
        if side == 'buy':
            # Buy limit below mid
            aggressiveness = 1 - (limit_price_offset_bps / spread_bps) if spread_bps > 0 else 0.5
        else:
            # Sell limit above mid
            aggressiveness = 1 - (limit_price_offset_bps / spread_bps) if spread_bps > 0 else 0.5

        aggressiveness = max(0, min(1, aggressiveness))

        # Base probability from aggressiveness
        base_prob = 0.3 + 0.5 * aggressiveness

        # Adjust for imbalance
        imbalance_adjustment = 0.2 * depth_imbalance

        fill_prob = max(0.1, min(0.95, base_prob + imbalance_adjustment))

        # Expected fill time (inverse relationship with probability)
        expected_time = max_wait_seconds * (1 - fill_prob) / fill_prob

        return fill_prob, expected_time


class ExecutionOptimizer:
    """
    Main execution optimization engine.
    Combines liquidity classification with slippage estimation
    to provide execution recommendations.
    """

    def __init__(
        self, 
        classifier: Optional[LiquidityClassifier] = None,
        slippage_estimator: Optional[SlippageEstimator] = None,
        risk_aversion: float = 0.5  # 0 = aggressive, 1 = conservative
    ):
        self.classifier = classifier or LiquidityClassifier()
        self.slippage_estimator = slippage_estimator or SlippageEstimator()
        self.risk_aversion = risk_aversion
        self.execution_history = deque(maxlen=1000)

    def get_execution_recommendation(
        self,
        symbol: str,
        side: str,
        quantity: float,
        features: Dict[str, float],
        urgency: str = 'normal'  # 'low', 'normal', 'high'
    ) -> ExecutionSignal:
        """
        Get execution recommendation for an order.

        This is the main entry point for the execution optimizer.
        """
        timestamp = datetime.now()

        # Classify liquidity condition
        liquidity_condition, confidence = self.classifier.predict(features)

        # Estimate slippage for market order
        market_slippage = self.slippage_estimator.estimate_market_order_slippage(
            quantity, features, side
        )

        # Determine recommendation based on condition and urgency
        recommendation = self._determine_strategy(
            liquidity_condition,
            market_slippage,
            features,
            side,
            quantity,
            urgency
        )

        signal = ExecutionSignal(
            symbol=symbol,
            timestamp=timestamp,
            side=side,
            quantity=quantity,
            liquidity_condition=liquidity_condition,
            recommendation=recommendation,
            expected_slippage_bps=market_slippage,
            confidence=confidence,
            features=features
        )

        self.execution_history.append(signal)
        return signal

    def _determine_strategy(
        self,
        condition: LiquidityCondition,
        market_slippage: float,
        features: Dict[str, float],
        side: str,
        quantity: float,
        urgency: str
    ) -> ExecutionRecommendation:
        """Determine optimal execution strategy."""

        # Urgency overrides
        if urgency == 'high':
            return ExecutionRecommendation.MARKET_ORDER_NOW

        if urgency == 'low':
            # Patient execution - always use limit orders
            if condition in [LiquidityCondition.IMBALANCED_BUY, LiquidityCondition.IMBALANCED_SELL]:
                return ExecutionRecommendation.LIMIT_ORDER_PASSIVE
            return ExecutionRecommendation.WAIT_IMPROVE

        # Normal urgency - use condition-based logic
        if condition == LiquidityCondition.TIGHT_DEEP:
            # Excellent conditions for market order
            if market_slippage < 5:  # Less than 5 bps
                return ExecutionRecommendation.MARKET_ORDER_NOW
            else:
                return ExecutionRecommendation.LIMIT_ORDER_AGGRESSIVE

        elif condition == LiquidityCondition.TIGHT_SHALLOW:
            # Good spread but shallow book
            if quantity < features.get('bid_depth_l1' if side == 'buy' else 'ask_depth_l1', 0):
                return ExecutionRecommendation.MARKET_ORDER_NOW
            else:
                return ExecutionRecommendation.SPLIT_ORDER

        elif condition == LiquidityCondition.WIDE_DEEP:
            # Wide spread but deep book - use limit order
            return ExecutionRecommendation.LIMIT_ORDER_AGGRESSIVE

        elif condition == LiquidityCondition.WIDE_SHALLOW:
            # Worst conditions - wait or cancel
            return ExecutionRecommendation.CANCEL_WAIT

        elif condition == LiquidityCondition.IMBALANCED_BUY:
            if side == 'buy':
                # Buying into buy pressure - urgency
                return ExecutionRecommendation.MARKET_ORDER_NOW
            else:
                # Selling into buy pressure - can be patient
                return ExecutionRecommendation.LIMIT_ORDER_PASSIVE

        elif condition == LiquidityCondition.IMBALANCED_SELL:
            if side == 'sell':
                # Selling into sell pressure - urgency
                return ExecutionRecommendation.MARKET_ORDER_NOW
            else:
                # Buying into sell pressure - can be patient
                return ExecutionRecommendation.LIMIT_ORDER_PASSIVE

        return ExecutionRecommendation.LIMIT_ORDER_AGGRESSIVE

    def get_optimal_order_size(
        self,
        total_quantity: float,
        features: Dict[str, float],
        max_slippage_bps: float = 10
    ) -> List[float]:
        """
        Split large orders into optimal sizes based on book depth.
        Implements basic order slicing from Bertsimas & Lo (1998).
        """
        bid_depth = features.get('bid_depth_l5', 1)
        ask_depth = features.get('ask_depth_l5', 1)

        # Conservative slice size - 20% of L5 depth
        max_slice = min(bid_depth, ask_depth) * 0.2

        slices = []
        remaining = total_quantity

        while remaining > 0:
            slice_size = min(remaining, max_slice)
            slices.append(slice_size)
            remaining -= slice_size

        return slices


class OrderBookAnalyzer:
    """
    Main class for analyzing Binance L2 order book data via WebSocket.
    Provides real-time liquidity analysis and execution recommendations.
    """

    BINANCE_WS_URL = "wss://stream.binance.com:9443/ws"

    def __init__(
        self,
        symbol: str = "btcusdt",
        depth_levels: int = 10,
        model_path: Optional[str] = None,
        callback: Optional[Callable[[ExecutionSignal], None]] = None
    ):
        self.symbol = symbol.lower()
        self.depth_levels = depth_levels
        self.callback = callback

        # Components
        self.feature_engineer = OrderBookFeatureEngineer(depth_levels)
        self.classifier = LiquidityClassifier(model_path=model_path)
        self.optimizer = ExecutionOptimizer(self.classifier)

        # State
        self.current_snapshot: Optional[OrderBookSnapshot] = None
        self.websocket = None
        self.is_running = False
        self.message_count = 0
        self.last_update_id = 0

        # Statistics
        self.stats = {
            'messages_received': 0,
            'snapshots_processed': 0,
            'signals_generated': 0,
            'start_time': None
        }

    async def connect_websocket(self):
        """
        Connect to Binance WebSocket for L2 order book data.
        Uses the depth stream which provides order book updates.
        """
        stream_name = f"{self.symbol}@depth{self.depth_levels}@100ms"
        ws_url = f"{self.BINANCE_WS_URL}/{stream_name}"

        logger.info(f"Connecting to Binance WebSocket: {ws_url}")

        try:
            async with websockets.connect(ws_url) as websocket:
                self.websocket = websocket
                self.is_running = True
                self.stats['start_time'] = datetime.now()

                logger.info(f"Connected to {self.symbol} depth stream")

                async for message in websocket:
                    if not self.is_running:
                        break

                    await self._process_message(message)

        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            self.is_running = False

    async def _process_message(self, message: str):
        """Process incoming WebSocket message."""
        try:
            data = json.loads(message)
            self.stats['messages_received'] += 1

            # Parse order book update
            snapshot = self._parse_depth_update(data)
            self.current_snapshot = snapshot

            # Extract features
            features = self.feature_engineer.extract_features(snapshot)

            # Store for analysis
            self.stats['snapshots_processed'] += 1

            # Log periodically
            if self.stats['snapshots_processed'] % 100 == 0:
                self._log_status(features)

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _parse_depth_update(self, data: Dict) -> OrderBookSnapshot:
        """Parse Binance depth update into OrderBookSnapshot."""
        timestamp = datetime.fromtimestamp(data.get('E', datetime.now().timestamp()) / 1000)

        # Parse bids and asks
        bids = []
        asks = []

        for price, qty in data.get('b', []):
            bids.append(OrderBookLevel(
                price=float(price),
                quantity=float(qty)
            ))

        for price, qty in data.get('a', []):
            asks.append(OrderBookLevel(
                price=float(price),
                quantity=float(qty)
            ))

        # Sort bids descending, asks ascending
        bids.sort(key=lambda x: x.price, reverse=True)
        asks.sort(key=lambda x: x.price)

        return OrderBookSnapshot(
            symbol=self.symbol.upper(),
            timestamp=timestamp,
            bids=bids,
            asks=asks
        )

    def calculate_depth_imbalance(self, levels: int = 5) -> Optional[float]:
        """
        Calculate depth imbalance at specified levels.
        Returns value between -1 (all ask) and +1 (all bid).
        """
        if not self.current_snapshot:
            return None

        features = self.feature_engineer.extract_features(self.current_snapshot)
        return features.get('depth_imbalance', 0)

    def classify_liquidity(self) -> Optional[Tuple[LiquidityCondition, float]]:
        """Classify current liquidity condition."""
        if not self.current_snapshot:
            return None

        features = self.feature_engineer.extract_features(self.current_snapshot)
        return self.classifier.predict(features)

    def get_execution_signal(
        self,
        side: str,
        quantity: float,
        urgency: str = 'normal'
    ) -> Optional[ExecutionSignal]:
        """Get execution recommendation for an order."""
        if not self.current_snapshot:
            logger.warning("No order book data available")
            return None

        features = self.feature_engineer.extract_features(self.current_snapshot)

        signal = self.optimizer.get_execution_recommendation(
            symbol=self.symbol.upper(),
            side=side,
            quantity=quantity,
            features=features,
            urgency=urgency
        )

        self.stats['signals_generated'] += 1

        if self.callback:
            self.callback(signal)

        return signal

    def _log_status(self, features: Dict[str, float]):
        """Log current market status."""
        spread_bps = features.get('spread_bps', 0)
        imbalance = features.get('depth_imbalance', 0)
        mid = features.get('mid_price', 0)

        logger.info(
            f"[{self.symbol.upper()}] Mid: ${mid:,.2f} | "
            f"Spread: {spread_bps:.2f} bps | "
            f"Imbalance: {imbalance:+.3f} | "
            f"Msgs: {self.stats['messages_received']}"
        )

    def get_current_features(self) -> Optional[Dict[str, float]]:
        """Get current order book features."""
        if not self.current_snapshot:
            return None
        return self.feature_engineer.extract_features(self.current_snapshot)

    def stop(self):
        """Stop the WebSocket connection."""
        self.is_running = False
        logger.info("OrderBookAnalyzer stopped")

    def get_stats(self) -> Dict:
        """Get runtime statistics."""
        stats = self.stats.copy()
        if stats['start_time']:
            stats['runtime_seconds'] = (datetime.now() - stats['start_time']).total_seconds()
        return stats


# =============================================================================
# SYNCHRONOUS WRAPPER FOR EASIER USE
# =============================================================================

class ExecutionOptimizerSync:
    """
    Synchronous wrapper for the execution optimizer.
    Useful for integration with existing trading systems.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.classifier = LiquidityClassifier(model_path=model_path)
        self.optimizer = ExecutionOptimizer(self.classifier)
        self.feature_engineer = OrderBookFeatureEngineer()

    def analyze_order_book(
        self,
        bids: List[Tuple[float, float]],
        asks: List[Tuple[float, float]],
        symbol: str = "BTCUSDT"
    ) -> Dict[str, Any]:
        """
        Analyze order book data and return liquidity assessment.

        Args:
            bids: List of (price, quantity) tuples
            asks: List of (price, quantity) tuples
            symbol: Trading pair symbol

        Returns:
            Dictionary with liquidity analysis
        """
        # Create snapshot
        bid_levels = [OrderBookLevel(price=p, quantity=q) for p, q in bids]
        ask_levels = [OrderBookLevel(price=p, quantity=q) for p, q in asks]

        snapshot = OrderBookSnapshot(
            symbol=symbol,
            timestamp=datetime.now(),
            bids=bid_levels,
            asks=ask_levels
        )

        # Extract features
        features = self.feature_engineer.extract_features(snapshot)

        # Classify liquidity
        condition, confidence = self.classifier.predict(features)

        return {
            'liquidity_condition': condition.value,
            'confidence': confidence,
            'features': features,
            'mid_price': snapshot.mid_price,
            'spread_bps': snapshot.spread_bps
        }

    def recommend_execution(
        self,
        bids: List[Tuple[float, float]],
        asks: List[Tuple[float, float]],
        side: str,
        quantity: float,
        symbol: str = "BTCUSDT",
        urgency: str = 'normal'
    ) -> ExecutionSignal:
        """
        Get execution recommendation for an order.

        Args:
            bids: List of (price, quantity) tuples
            asks: List of (price, quantity) tuples
            side: 'buy' or 'sell'
            quantity: Order size in base currency
            symbol: Trading pair symbol
            urgency: 'low', 'normal', or 'high'

        Returns:
            ExecutionSignal with recommendation
        """
        # Create snapshot
        bid_levels = [OrderBookLevel(price=p, quantity=q) for p, q in bids]
        ask_levels = [OrderBookLevel(price=p, quantity=q) for p, q in asks]

        snapshot = OrderBookSnapshot(
            symbol=symbol,
            timestamp=datetime.now(),
            bids=bid_levels,
            asks=ask_levels
        )

        # Extract features and get recommendation
        features = self.feature_engineer.extract_features(snapshot)

        signal = self.optimizer.get_execution_recommendation(
            symbol=symbol,
            side=side,
            quantity=quantity,
            features=features,
            urgency=urgency
        )

        return signal


# =============================================================================
# TRAINING MODULE
# =============================================================================

def generate_synthetic_training_data(
    n_samples: int = 10000,
    random_state: int = 42
) -> Tuple[pd.DataFrame, np.ndarray]:
    """
    Generate synthetic training data for liquidity classifier.
    In production, use historical order book data with labeled outcomes.
    """
    np.random.seed(random_state)

    data = []
    labels = []

    for _ in range(n_samples):
        # Generate realistic order book features
        spread_bps = np.random.exponential(5) + 1
        bid_depth_l1 = np.random.lognormal(0, 1)
        ask_depth_l1 = np.random.lognormal(0, 1)
        bid_depth_l5 = bid_depth_l1 * np.random.uniform(2, 5)
        ask_depth_l5 = ask_depth_l1 * np.random.uniform(2, 5)

        # Depth imbalance
        depth_imbalance = np.random.normal(0, 0.3)
        depth_imbalance = np.clip(depth_imbalance, -1, 1)

        # Value imbalance
        value_imbalance = np.random.normal(0, 0.2)
        value_imbalance = np.clip(value_imbalance, -1, 1)

        # Volatility
        volatility = np.random.exponential(10)

        sample = {
            'spread_bps': spread_bps,
            'bid_depth_l1': bid_depth_l1,
            'ask_depth_l1': ask_depth_l1,
            'bid_depth_l5': bid_depth_l5,
            'ask_depth_l5': ask_depth_l5,
            'depth_imbalance': depth_imbalance,
            'value_imbalance': value_imbalance,
            'l1_imbalance': depth_imbalance * np.random.uniform(0.8, 1.2),
            'bid_value_l5': bid_depth_l5 * 30000,
            'ask_value_l5': ask_depth_l5 * 30000,
            'price_volatility_10': volatility,
            'liquidity_score': 1 / (spread_bps / 100 + 1 / (bid_depth_l5 + 1))
        }

        # Determine label based on features
        if abs(depth_imbalance) > 0.4:
            if depth_imbalance > 0:
                label = LiquidityCondition.IMBALANCED_BUY.value
            else:
                label = LiquidityCondition.IMBALANCED_SELL.value
        elif spread_bps < 5 and bid_depth_l5 > 10 and ask_depth_l5 > 10:
            label = LiquidityCondition.TIGHT_DEEP.value
        elif spread_bps < 5:
            label = LiquidityCondition.TIGHT_SHALLOW.value
        elif bid_depth_l5 > 10 and ask_depth_l5 > 10:
            label = LiquidityCondition.WIDE_DEEP.value
        else:
            label = LiquidityCondition.WIDE_SHALLOW.value

        data.append(sample)
        labels.append(label)

    return pd.DataFrame(data), np.array(labels)


def train_liquidity_classifier(
    model_type: str = 'xgboost',
    output_path: str = 'liquidity_classifier.pkl',
    n_samples: int = 10000
):
    """Train and save a liquidity classifier model."""
    logger.info(f"Generating {n_samples} synthetic training samples...")
    df, labels = generate_synthetic_training_data(n_samples)

    # Prepare features
    feature_cols = [c for c in df.columns if c not in ['mid_price', 'best_bid', 'best_ask']]
    X = df[feature_cols].values

    # Train model
    classifier = LiquidityClassifier(model_type=model_type)
    classifier.feature_names = feature_cols
    classifier.train(X, labels)

    # Save model
    classifier.save_model(output_path)

    logger.info(f"Model saved to {output_path}")
    return classifier


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

async def example_realtime_analysis():
    """Example of real-time order book analysis."""

    # Create analyzer
    analyzer = OrderBookAnalyzer(symbol="btcusdt", depth_levels=10)

    # Define callback for signals
    def on_signal(signal: ExecutionSignal):
        print(f"\n[EXECUTION SIGNAL]")
        print(f"  Condition: {signal.liquidity_condition.value}")
        print(f"  Recommendation: {signal.recommendation.value}")
        print(f"  Expected Slippage: {signal.expected_slippage_bps:.2f} bps")
        print(f"  Confidence: {signal.confidence:.2%}")

    analyzer.callback = on_signal

    # Run for 30 seconds
    try:
        await asyncio.wait_for(
            analyzer.connect_websocket(),
            timeout=30
        )
    except asyncio.TimeoutError:
        print("\nAnalysis complete")
        print(f"Stats: {analyzer.get_stats()}")


def example_sync_usage():
    """Example of synchronous usage with existing data."""

    # Sample order book data
    bids = [
        (30000.0, 2.5),   # price, quantity
        (29999.5, 3.0),
        (29999.0, 5.0),
        (29998.5, 8.0),
        (29998.0, 12.0),
    ]

    asks = [
        (30000.5, 2.0),
        (30001.0, 4.0),
        (30001.5, 6.0),
        (30002.0, 10.0),
        (30002.5, 15.0),
    ]

    # Create optimizer
    optimizer = ExecutionOptimizerSync()

    # Analyze order book
    analysis = optimizer.analyze_order_book(bids, asks, "BTCUSDT")
    print("Liquidity Analysis:")
    print(f"  Condition: {analysis['liquidity_condition']}")
    print(f"  Spread: {analysis['spread_bps']:.2f} bps")
    print(f"  Mid Price: ${analysis['mid_price']:,.2f}")

    # Get execution recommendation
    signal = optimizer.recommend_execution(
        bids=bids,
        asks=asks,
        side='buy',
        quantity=1.0,  # 1 BTC
        urgency='normal'
    )

    print(f"\nExecution Recommendation:")
    print(f"  Action: {signal.recommendation.value}")
    print(f"  Expected Slippage: {signal.expected_slippage_bps:.2f} bps")
    print(f"  Confidence: {signal.confidence:.2%}")


if __name__ == "__main__":
    # Train a model first
    print("Training liquidity classifier...")
    train_liquidity_classifier(output_path="/mnt/okcomputer/output/liquidity_classifier.pkl")

    # Run synchronous example
    print("\n" + "="*60)
    print("SYNCHRONOUS EXAMPLE")
    print("="*60)
    example_sync_usage()
