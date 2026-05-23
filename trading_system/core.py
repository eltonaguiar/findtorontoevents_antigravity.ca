"""
Live Trading System - Core Implementation
=========================================
This module contains the core implementation classes for the live trading system.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

import aioredis
import asyncpg
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"

class OrderStatus(Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class SignalType(Enum):
    ENTRY_LONG = "ENTRY_LONG"
    ENTRY_SHORT = "ENTRY_SHORT"
    EXIT_LONG = "EXIT_LONG"
    EXIT_SHORT = "EXIT_SHORT"
    HOLD = "HOLD"

class HealthStatus(Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


# ============================================================================
# DATA MODELS
# ============================================================================

class Tick(BaseModel):
    """Market tick data model"""
    symbol: str
    price: Decimal
    size: Decimal
    timestamp: datetime
    exchange: str
    side: Optional[str] = None
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }

class Signal(BaseModel):
    """Trading signal model"""
    signal_id: str = Field(default_factory=lambda: str(uuid4()))
    symbol: str
    signal_type: SignalType
    confidence: float = Field(ge=0.0, le=1.0)
    strategy: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class Order(BaseModel):
    """Order model"""
    order_id: str = Field(default_factory=lambda: str(uuid4()))
    signal_id: Optional[str] = None
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Decimal = Decimal("0")
    avg_fill_price: Optional[Decimal] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }

class Fill(BaseModel):
    """Order fill model"""
    fill_id: str = Field(default_factory=lambda: str(uuid4()))
    order_id: str
    symbol: str
    filled_quantity: Decimal
    filled_price: Decimal
    fee: Decimal
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }

class Position(BaseModel):
    """Position model"""
    symbol: str
    quantity: Decimal
    avg_entry_price: Optional[Decimal] = None
    unrealized_pnl: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# DATA INGESTION LAYER
# ============================================================================

class WebSocketManager:
    """
    Manages WebSocket connections to exchanges with automatic reconnection.
    """
    
    def __init__(self, redis_url: str, reconnect_delay: float = 1.0):
        self.redis_url = redis_url
        self.reconnect_delay = reconnect_delay
        self.connections: Dict[str, Any] = {}
        self.running = False
        self.redis: Optional[aioredis.Redis] = None
        
    async def start(self):
        """Initialize Redis connection"""
        self.redis = await aioredis.from_url(self.redis_url)
        self.running = True
        logger.info("WebSocket manager started")
        
    async def stop(self):
        """Stop all connections"""
        self.running = False
        for conn in self.connections.values():
            await conn.close()
        if self.redis:
            await self.redis.close()
        logger.info("WebSocket manager stopped")
        
    async def subscribe_exchange(self, exchange: str, symbols: List[str]):
        """Subscribe to exchange WebSocket feed"""
        while self.running:
            try:
                await self._connect_and_stream(exchange, symbols)
            except Exception as e:
                logger.error(f"WebSocket error for {exchange}: {e}")
                await asyncio.sleep(self.reconnect_delay)
                
    async def _connect_and_stream(self, exchange: str, symbols: List[str]):
        """Connect to exchange and stream data"""
        # Implementation would connect to actual exchange WebSocket
        # This is a placeholder for the architecture
        logger.info(f"Connecting to {exchange} for symbols: {symbols}")
        
        while self.running:
            # Simulate receiving tick data
            await asyncio.sleep(0.1)
            
    async def publish_tick(self, tick: Tick):
        """Publish tick to Redis Stream"""
        if self.redis:
            stream_key = f"market:ticks:{tick.symbol}"
            await self.redis.xadd(
                stream_key,
                tick.model_dump(),
                maxlen=10000
            )


class MarketDataNormalizer:
    """
    Normalizes market data from different exchanges into standard format.
    """
    
    @staticmethod
    def normalize_tick(exchange: str, raw_data: Dict) -> Tick:
        """Convert exchange-specific format to standard Tick"""
        normalizers = {
            "binance": MarketDataNormalizer._normalize_binance,
            "coinbase": MarketDataNormalizer._normalize_coinbase,
            "kraken": MarketDataNormalizer._normalize_kraken,
        }
        
        normalizer = normalizers.get(exchange)
        if not normalizer:
            raise ValueError(f"Unknown exchange: {exchange}")
            
        return normalizer(raw_data)
    
    @staticmethod
    def _normalize_binance(data: Dict) -> Tick:
        return Tick(
            symbol=data["s"],
            price=Decimal(str(data["p"])),
            size=Decimal(str(data["q"])),
            timestamp=datetime.utcnow(),
            exchange="binance",
            side="buy" if data["m"] else "sell"
        )
    
    @staticmethod
    def _normalize_coinbase(data: Dict) -> Tick:
        return Tick(
            symbol=data["product_id"].replace("-", ""),
            price=Decimal(str(data["price"])),
            size=Decimal(str(data["last_size"])),
            timestamp=datetime.utcnow(),
            exchange="coinbase",
            side=data.get("side")
        )
    
    @staticmethod
    def _normalize_kraken(data: Dict) -> Tick:
        # Kraken-specific normalization
        return Tick(
            symbol=data["pair"],
            price=Decimal(str(data["price"])),
            size=Decimal(str(data["volume"])),
            timestamp=datetime.utcnow(),
            exchange="kraken",
            side=data.get("side")
        )


# ============================================================================
# SIGNAL GENERATION LAYER
# ============================================================================

class IndicatorCalculator:
    """
    Real-time technical indicator calculations using sliding windows.
    """
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.price_windows: Dict[str, List[Decimal]] = {}
        self.volume_windows: Dict[str, List[Decimal]] = {}
        
    def update(self, tick: Tick):
        """Update indicators with new tick"""
        symbol = tick.symbol
        
        if symbol not in self.price_windows:
            self.price_windows[symbol] = []
            self.volume_windows[symbol] = []
            
        self.price_windows[symbol].append(tick.price)
        self.volume_windows[symbol].append(tick.size)
        
        # Maintain window size
        if len(self.price_windows[symbol]) > self.window_size:
            self.price_windows[symbol].pop(0)
            self.volume_windows[symbol].pop(0)
            
    def ema(self, symbol: str, period: int) -> Optional[Decimal]:
        """Calculate Exponential Moving Average"""
        prices = self.price_windows.get(symbol, [])
        if len(prices) < period:
            return None
            
        multiplier = Decimal("2") / Decimal(period + 1)
        ema = sum(prices[-period:]) / period  # SMA as starting point
        
        for price in prices[-period+1:]:
            ema = (price * multiplier) + (ema * (Decimal("1") - multiplier))
            
        return ema
    
    def rsi(self, symbol: str, period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index"""
        prices = self.price_windows.get(symbol, [])
        if len(prices) < period + 1:
            return None
            
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(float(change))
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(abs(float(change)))
                
        if len(gains) < period:
            return None
            
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))


class Strategy(ABC):
    """Abstract base class for trading strategies"""
    
    @abstractmethod
    async def generate_signal(self, tick: Tick, indicators: IndicatorCalculator) -> Optional[Signal]:
        """Generate trading signal from tick and indicators"""
        pass


class MomentumStrategy(Strategy):
    """
    Simple momentum strategy using EMA crossover.
    """
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.name = "momentum_v2"
        
    async def generate_signal(self, tick: Tick, indicators: IndicatorCalculator) -> Optional[Signal]:
        fast_ema = indicators.ema(tick.symbol, self.fast_period)
        slow_ema = indicators.ema(tick.symbol, self.slow_period)
        
        if fast_ema is None or slow_ema is None:
            return None
            
        if fast_ema > slow_ema * Decimal("1.001"):
            return Signal(
                symbol=tick.symbol,
                signal_type=SignalType.ENTRY_LONG,
                confidence=0.75,
                strategy=self.name,
                metadata={
                    "fast_ema": str(fast_ema),
                    "slow_ema": str(slow_ema)
                }
            )
        elif fast_ema < slow_ema * Decimal("0.999"):
            return Signal(
                symbol=tick.symbol,
                signal_type=SignalType.EXIT_LONG,
                confidence=0.70,
                strategy=self.name,
                metadata={
                    "fast_ema": str(fast_ema),
                    "slow_ema": str(slow_ema)
                }
            )
            
        return None


class SignalGenerator:
    """
    Orchestrates signal generation from multiple strategies.
    """
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
        self.indicators = IndicatorCalculator()
        self.strategies: List[Strategy] = []
        self.running = False
        
    async def start(self):
        """Initialize signal generator"""
        self.redis = await aioredis.from_url(self.redis_url)
        self.running = True
        logger.info("Signal generator started")
        
    async def stop(self):
        """Stop signal generator"""
        self.running = False
        if self.redis:
            await self.redis.close()
        logger.info("Signal generator stopped")
        
    def add_strategy(self, strategy: Strategy):
        """Add a trading strategy"""
        self.strategies.append(strategy)
        
    async def process_tick(self, tick: Tick):
        """Process tick and generate signals"""
        # Update indicators
        self.indicators.update(tick)
        
        # Generate signals from all strategies
        for strategy in self.strategies:
            signal = await strategy.generate_signal(tick, self.indicators)
            if signal:
                await self._publish_signal(signal)
                
    async def _publish_signal(self, signal: Signal):
        """Publish signal to Redis Stream"""
        if self.redis:
            await self.redis.xadd(
                "signals:generated",
                signal.model_dump(),
                maxlen=10000
            )
            logger.info(f"Signal generated: {signal.signal_type.value} for {signal.symbol}")


# ============================================================================
# RISK MANAGEMENT LAYER
# ============================================================================

@dataclass
class RiskLimits:
    """Risk limit configuration"""
    max_position_value: Decimal = Decimal("1000000")
    max_position_pct: Decimal = Decimal("0.10")
    max_daily_loss: Decimal = Decimal("50000")
    max_order_size: Decimal = Decimal("100")
    max_slippage_bps: int = 50
    portfolio_drawdown_pct: float = 5.0


class RiskManager:
    """
    Pre-trade risk management with position limits and circuit breakers.
    """
    
    def __init__(self, redis_url: str, db_url: str, limits: RiskLimits):
        self.redis_url = redis_url
        self.db_url = db_url
        self.limits = limits
        self.redis: Optional[aioredis.Redis] = None
        self.db: Optional[asyncpg.Pool] = None
        self.circuit_breaker_active = False
        self.daily_pnl: Decimal = Decimal("0")
        
    async def start(self):
        """Initialize risk manager"""
        self.redis = await aioredis.from_url(self.redis_url)
        self.db = await asyncpg.create_pool(self.db_url)
        logger.info("Risk manager started")
        
    async def stop(self):
        """Stop risk manager"""
        if self.redis:
            await self.redis.close()
        if self.db:
            await self.db.close()
        logger.info("Risk manager stopped")
        
    async def validate_order(self, order: Order, current_price: Decimal) -> tuple[bool, Optional[str]]:
        """
        Validate order against risk limits.
        Returns (is_valid, rejection_reason)
        """
        # Check circuit breaker
        if self.circuit_breaker_active:
            return False, "Circuit breaker active"
            
        # Check order size
        if order.quantity > self.limits.max_order_size:
            return False, f"Order size {order.quantity} exceeds limit {self.limits.max_order_size}"
            
        # Check price sanity (away from market)
        if order.order_type == OrderType.LIMIT and order.price:
            slippage = abs(order.price - current_price) / current_price * 10000
            if slippage > self.limits.max_slippage_bps:
                return False, f"Price {slippage} bps away from market"
                
        # Check position limits
        position = await self._get_position(order.symbol)
        new_quantity = position.quantity + (order.quantity if order.side == OrderSide.BUY else -order.quantity)
        position_value = abs(new_quantity) * current_price
        
        if position_value > self.limits.max_position_value:
            return False, f"Position value {position_value} exceeds limit"
            
        # Check daily loss limit
        if self.daily_pnl < -self.limits.max_daily_loss:
            await self._activate_circuit_breaker("Daily loss limit reached")
            return False, "Daily loss limit reached"
            
        return True, None
        
    async def _get_position(self, symbol: str) -> Position:
        """Get current position for symbol"""
        if not self.db:
            return Position(symbol=symbol, quantity=Decimal("0"))
            
        row = await self.db.fetchrow(
            "SELECT * FROM positions WHERE symbol = $1",
            symbol
        )
        
        if row:
            return Position(
                symbol=row["symbol"],
                quantity=row["quantity"],
                avg_entry_price=row["avg_entry_price"],
                unrealized_pnl=row["unrealized_pnl"],
                realized_pnl=row["realized_pnl"],
                last_updated=row["last_updated"]
            )
        return Position(symbol=symbol, quantity=Decimal("0"))
        
    async def _activate_circuit_breaker(self, reason: str):
        """Activate circuit breaker"""
        self.circuit_breaker_active = True
        logger.critical(f"CIRCUIT BREAKER ACTIVATED: {reason}")
        
        # Publish alert
        if self.redis:
            await self.redis.publish(
                "alerts:critical",
                json.dumps({
                    "type": "CIRCUIT_BREAKER",
                    "reason": reason,
                    "timestamp": datetime.utcnow().isoformat()
                })
            )
            
    async def update_daily_pnl(self, pnl: Decimal):
        """Update daily P&L"""
        self.daily_pnl += pnl
        
        # Check drawdown
        if self.daily_pnl < -self.limits.max_daily_loss:
            await self._activate_circuit_breaker("Daily loss limit reached")


# ============================================================================
# ORDER EXECUTION LAYER
# ============================================================================

class OrderExecutor:
    """
    Order execution engine with smart routing and fill handling.
    """
    
    def __init__(self, redis_url: str, db_url: str):
        self.redis_url = redis_url
        self.db_url = db_url
        self.redis: Optional[aioredis.Redis] = None
        self.db: Optional[asyncpg.Pool] = None
        self.pending_orders: Dict[str, Order] = {}
        self.running = False
        
    async def start(self):
        """Initialize order executor"""
        self.redis = await aioredis.from_url(self.redis_url)
        self.db = await asyncpg.create_pool(self.db_url)
        self.running = True
        
        # Start fill listener
        asyncio.create_task(self._listen_for_fills())
        logger.info("Order executor started")
        
    async def stop(self):
        """Stop order executor"""
        self.running = False
        if self.redis:
            await self.redis.close()
        if self.db:
            await self.db.close()
        logger.info("Order executor stopped")
        
    async def submit_order(self, order: Order) -> bool:
        """Submit order to exchange"""
        try:
            # Update order status
            order.status = OrderStatus.SUBMITTED
            self.pending_orders[order.order_id] = order
            
            # Persist to database
            await self._persist_order(order)
            
            # Publish to execution stream
            if self.redis:
                await self.redis.xadd(
                    "orders:submitted",
                    order.model_dump(),
                    maxlen=10000
                )
                
            logger.info(f"Order submitted: {order.order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit order: {e}")
            order.status = OrderStatus.REJECTED
            return False
            
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel pending order"""
        if order_id not in self.pending_orders:
            return False
            
        order = self.pending_orders[order_id]
        order.status = OrderStatus.CANCELLED
        
        await self._update_order_status(order_id, OrderStatus.CANCELLED)
        del self.pending_orders[order_id]
        
        logger.info(f"Order cancelled: {order_id}")
        return True
        
    async def _listen_for_fills(self):
        """Listen for fill updates from exchange"""
        while self.running:
            try:
                # In production, this would listen to exchange WebSocket
                # Simulating fill processing
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Fill listener error: {e}")
                await asyncio.sleep(5)
                
    async def process_fill(self, fill: Fill):
        """Process order fill"""
        order_id = fill.order_id
        
        if order_id not in self.pending_orders:
            logger.warning(f"Fill received for unknown order: {order_id}")
            return
            
        order = self.pending_orders[order_id]
        order.filled_quantity += fill.filled_quantity
        
        # Update average fill price
        if order.avg_fill_price is None:
            order.avg_fill_price = fill.filled_price
        else:
            total_value = (order.filled_quantity - fill.filled_quantity) * order.avg_fill_price
            total_value += fill.filled_quantity * fill.filled_price
            order.avg_fill_price = total_value / order.filled_quantity
            
        # Check if fully filled
        if order.filled_quantity >= order.quantity:
            order.status = OrderStatus.FILLED
            del self.pending_orders[order_id]
        else:
            order.status = OrderStatus.PARTIAL
            
        # Persist fill
        await self._persist_fill(fill)
        await self._update_order_status(order_id, order.status)
        
        # Publish fill event
        if self.redis:
            await self.redis.xadd(
                "orders:fills",
                fill.model_dump(),
                maxlen=10000
            )
            
        logger.info(f"Fill processed: {fill.fill_id} for order {order_id}")
        
    async def _persist_order(self, order: Order):
        """Persist order to database"""
        if not self.db:
            return
            
        await self.db.execute(
            """
            INSERT INTO orders (order_id, signal_id, symbol, side, order_type, 
                              quantity, price, status, timestamp)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            order.order_id, order.signal_id, order.symbol, order.side.value,
            order.order_type.value, order.quantity, order.price,
            order.status.value, order.timestamp
        )
        
    async def _persist_fill(self, fill: Fill):
        """Persist fill to database"""
        if not self.db:
            return
            
        await self.db.execute(
            """
            INSERT INTO fills (fill_id, order_id, symbol, filled_quantity, 
                             filled_price, fee, timestamp)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            fill.fill_id, fill.order_id, fill.symbol, fill.filled_quantity,
            fill.filled_price, fill.fee, fill.timestamp
        )
        
    async def _update_order_status(self, order_id: str, status: OrderStatus):
        """Update order status in database"""
        if not self.db:
            return
            
        await self.db.execute(
            "UPDATE orders SET status = $1 WHERE order_id = $2",
            status.value, order_id
        )


# ============================================================================
# POSITION TRACKING LAYER
# ============================================================================

class PositionTracker:
    """
    Real-time position and P&L tracking.
    """
    
    def __init__(self, redis_url: str, db_url: str):
        self.redis_url = redis_url
        self.db_url = db_url
        self.redis: Optional[aioredis.Redis] = None
        self.db: Optional[asyncpg.Pool] = None
        self.positions: Dict[str, Position] = {}
        self.price_cache: Dict[str, Decimal] = {}
        
    async def start(self):
        """Initialize position tracker"""
        self.redis = await aioredis.from_url(self.redis_url)
        self.db = await asyncpg.create_pool(self.db_url)
        
        # Load existing positions
        await self._load_positions()
        logger.info("Position tracker started")
        
    async def stop(self):
        """Stop position tracker"""
        if self.redis:
            await self.redis.close()
        if self.db:
            await self.db.close()
        logger.info("Position tracker stopped")
        
    async def _load_positions(self):
        """Load positions from database"""
        if not self.db:
            return
            
        rows = await self.db.fetch("SELECT * FROM positions")
        for row in rows:
            position = Position(
                symbol=row["symbol"],
                quantity=row["quantity"],
                avg_entry_price=row["avg_entry_price"],
                unrealized_pnl=row["unrealized_pnl"],
                realized_pnl=row["realized_pnl"],
                last_updated=row["last_updated"]
            )
            self.positions[position.symbol] = position
            
    async def update_price(self, symbol: str, price: Decimal):
        """Update market price and recalculate unrealized P&L"""
        self.price_cache[symbol] = price
        
        if symbol in self.positions:
            position = self.positions[symbol]
            if position.avg_entry_price and position.quantity != 0:
                price_diff = price - position.avg_entry_price
                position.unrealized_pnl = price_diff * position.quantity
                position.last_updated = datetime.utcnow()
                
                await self._persist_position(position)
                
    async def process_fill(self, fill: Fill, order_side: OrderSide):
        """Update position based on fill"""
        symbol = fill.symbol
        
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol, quantity=Decimal("0"))
            
        position = self.positions[symbol]
        
        # Calculate realized P&L for closing trades
        realized_pnl = Decimal("0")
        if position.quantity != 0:
            if (position.quantity > 0 and order_side == OrderSide.SELL) or \
               (position.quantity < 0 and order_side == OrderSide.BUY):
                # Closing position
                close_qty = min(abs(position.quantity), fill.filled_quantity)
                realized_pnl = (fill.filled_price - position.avg_entry_price) * close_qty
                if position.quantity < 0:
                    realized_pnl = -realized_pnl
                    
        # Update position quantity
        if order_side == OrderSide.BUY:
            position.quantity += fill.filled_quantity
        else:
            position.quantity -= fill.filled_quantity
            
        # Update average entry price
        if position.quantity > 0 and order_side == OrderSide.BUY:
            if position.avg_entry_price is None:
                position.avg_entry_price = fill.filled_price
            else:
                total_value = (position.quantity - fill.filled_quantity) * position.avg_entry_price
                total_value += fill.filled_quantity * fill.filled_price
                position.avg_entry_price = total_value / position.quantity
        elif position.quantity < 0 and order_side == OrderSide.SELL:
            if position.avg_entry_price is None:
                position.avg_entry_price = fill.filled_price
            else:
                total_value = abs(position.quantity - fill.filled_quantity) * position.avg_entry_price
                total_value += fill.filled_quantity * fill.filled_price
                position.avg_entry_price = total_value / abs(position.quantity)
        elif position.quantity == 0:
            position.avg_entry_price = None
            
        position.realized_pnl += realized_pnl
        position.last_updated = datetime.utcnow()
        
        await self._persist_position(position)
        
        # Publish position update
        if self.redis:
            await self.redis.publish(
                f"positions:updates:{symbol}",
                position.model_dump_json()
            )
            
    async def _persist_position(self, position: Position):
        """Persist position to database"""
        if not self.db:
            return
            
        await self.db.execute(
            """
            INSERT INTO positions (symbol, quantity, avg_entry_price, 
                                 unrealized_pnl, realized_pnl, last_updated)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (symbol) DO UPDATE SET
                quantity = EXCLUDED.quantity,
                avg_entry_price = EXCLUDED.avg_entry_price,
                unrealized_pnl = EXCLUDED.unrealized_pnl,
                realized_pnl = EXCLUDED.realized_pnl,
                last_updated = EXCLUDED.last_updated
            """,
            position.symbol, position.quantity, position.avg_entry_price,
            position.unrealized_pnl, position.realized_pnl, position.last_updated
        )
        
    def get_position(self, symbol: str) -> Position:
        """Get current position for symbol"""
        return self.positions.get(symbol, Position(symbol=symbol, quantity=Decimal("0")))
        
    def get_total_pnl(self) -> tuple[Decimal, Decimal]:
        """Get total realized and unrealized P&L"""
        realized = sum(p.realized_pnl for p in self.positions.values())
        unrealized = sum(p.unrealized_pnl for p in self.positions.values())
        return realized, unrealized


# ============================================================================
# ORCHESTRATION
# ============================================================================

class TradingSystem:
    """
    Main trading system orchestrator.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.running = False
        
        # Initialize components
        self.ws_manager = WebSocketManager(config["redis_url"])
        self.signal_generator = SignalGenerator(config["redis_url"])
        self.risk_manager = RiskManager(
            config["redis_url"],
            config["db_url"],
            RiskLimits(**config.get("risk_limits", {}))
        )
        self.order_executor = OrderExecutor(config["redis_url"], config["db_url"])
        self.position_tracker = PositionTracker(config["redis_url"], config["db_url"])
        
    async def start(self):
        """Start the trading system"""
        logger.info("Starting trading system...")
        
        # Start all components
        await self.ws_manager.start()
        await self.signal_generator.start()
        await self.risk_manager.start()
        await self.order_executor.start()
        await self.position_tracker.start()
        
        # Add default strategy
        self.signal_generator.add_strategy(MomentumStrategy())
        
        self.running = True
        
        # Start main processing loops
        asyncio.create_task(self._process_signals())
        asyncio.create_task(self._process_fills())
        
        logger.info("Trading system started successfully")
        
    async def stop(self):
        """Stop the trading system"""
        logger.info("Stopping trading system...")
        self.running = False
        
        await self.ws_manager.stop()
        await self.signal_generator.stop()
        await self.risk_manager.stop()
        await self.order_executor.stop()
        await self.position_tracker.stop()
        
        logger.info("Trading system stopped")
        
    async def _process_signals(self):
        """Process signals from Redis Stream"""
        while self.running:
            try:
                if self.signal_generator.redis:
                    messages = await self.signal_generator.redis.xread(
                        {"signals:generated": "$"},
                        count=10,
                        block=1000
                    )
                    
                    for stream, msgs in messages:
                        for msg_id, data in msgs:
                            signal = Signal(**data)
                            await self._handle_signal(signal)
                            
            except Exception as e:
                logger.error(f"Signal processing error: {e}")
                await asyncio.sleep(1)
                
    async def _handle_signal(self, signal: Signal):
        """Handle trading signal"""
        # Get current price
        current_price = self.position_tracker.price_cache.get(signal.symbol)
        if not current_price:
            logger.warning(f"No price available for {signal.symbol}")
            return
            
        # Build order from signal
        order = Order(
            signal_id=signal.signal_id,
            symbol=signal.symbol,
            side=OrderSide.BUY if signal.signal_type == SignalType.ENTRY_LONG else OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0")  # Would be calculated based on position sizing
        )
        
        # Risk check
        is_valid, reason = await self.risk_manager.validate_order(order, current_price)
        if not is_valid:
            logger.warning(f"Order rejected by risk manager: {reason}")
            return
            
        # Submit order
        success = await self.order_executor.submit_order(order)
        if success:
            logger.info(f"Order submitted for signal {signal.signal_id}")
            
    async def _process_fills(self):
        """Process fills from Redis Stream"""
        while self.running:
            try:
                if self.order_executor.redis:
                    messages = await self.order_executor.redis.xread(
                        {"orders:fills": "$"},
                        count=10,
                        block=1000
                    )
                    
                    for stream, msgs in messages:
                        for msg_id, data in msgs:
                            fill = Fill(**data)
                            # Get order side from pending orders
                            order = self.order_executor.pending_orders.get(fill.order_id)
                            if order:
                                await self.position_tracker.process_fill(fill, order.side)
                                
            except Exception as e:
                logger.error(f"Fill processing error: {e}")
                await asyncio.sleep(1)


# ============================================================================
# HEALTH CHECK
# ============================================================================

class HealthChecker:
    """
    System health monitoring.
    """
    
    def __init__(self, trading_system: TradingSystem):
        self.system = trading_system
        self.checks: List[Callable[[], HealthStatus]] = []
        
    def register_check(self, check: Callable[[], HealthStatus]):
        """Register a health check"""
        self.checks.append(check)
        
    async def run_checks(self) -> Dict[str, HealthStatus]:
        """Run all health checks"""
        results = {}
        for check in self.checks:
            try:
                status = await check()
                results[check.__name__] = status
            except Exception as e:
                results[check.__name__] = HealthStatus.UNHEALTHY
                logger.error(f"Health check failed: {e}")
        return results


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    """Main entry point"""
    config = {
        "redis_url": "redis://localhost:6379",
        "db_url": "postgresql://user:pass@localhost/trading",
        "risk_limits": {
            "max_position_value": 1000000,
            "max_position_pct": 0.10,
            "max_daily_loss": 50000,
            "max_order_size": 100,
            "max_slippage_bps": 50
        }
    }
    
    system = TradingSystem(config)
    
    try:
        await system.start()
        
        # Run indefinitely
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        await system.stop()


if __name__ == "__main__":
    asyncio.run(main())
