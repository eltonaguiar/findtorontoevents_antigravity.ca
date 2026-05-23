"""
Transaction Cost Model Module
=============================
Comprehensive cost modeling for multi-asset trading systems.

Features:
- Asset-class specific commission models
- Volume and volatility-based slippage estimation
- Market impact modeling (Almgren-Chriss)
- Round-trip cost calculations
- Post-commission PnL tracking

Author: Quantitative Finance Research
Version: 1.0.0
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, List, Tuple, Union
from enum import Enum, auto
from abc import ABC, abstractmethod
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AssetClass(Enum):
    """Asset class enumeration for cost modeling."""
    STOCK = auto()
    ETF = auto()
    FUTURES = auto()
    CRYPTO = auto()
    FOREX = auto()
    OPTION = auto()


class OrderType(Enum):
    """Order type for cost calculations."""
    MARKET = auto()
    LIMIT = auto()
    STOP = auto()
    STOP_LIMIT = auto()


@dataclass
class TradeDetails:
    """Container for trade details required for cost calculation."""
    symbol: str
    asset_class: AssetClass
    quantity: float
    price: float
    order_type: OrderType = OrderType.MARKET
    
    # Optional fields for advanced slippage calculation
    volume_24h: Optional[float] = None  # 24h volume for liquidity estimation
    volatility: Optional[float] = None  # Annualized volatility (decimal)
    bid_ask_spread: Optional[float] = None  # Current bid-ask spread
    market_cap: Optional[float] = None  # Market cap for impact estimation
    
    @property
    def notional_value(self) -> float:
        """Calculate notional value of the trade."""
        return abs(self.quantity * self.price)
    
    @property
    def is_buy(self) -> bool:
        """True if this is a buy order."""
        return self.quantity > 0


@dataclass
class CostBreakdown:
    """Detailed breakdown of transaction costs."""
    commission: float
    slippage: float
    market_impact: float
    fees: float  # Exchange/regulatory fees
    total_cost: float
    
    # Per-unit costs for analysis
    commission_per_share: float = 0.0
    slippage_bps: float = 0.0
    total_cost_bps: float = 0.0
    
    def __post_init__(self):
        """Calculate derived metrics."""
        self.total_cost = self.commission + self.slippage + self.market_impact + self.fees


@dataclass
class PositionPnL:
    """Position-level PnL with cost tracking."""
    symbol: str
    quantity: float
    entry_price: float
    exit_price: Optional[float] = None
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    
    # Cost tracking
    entry_cost: CostBreakdown = field(default_factory=lambda: CostBreakdown(0, 0, 0, 0, 0))
    exit_cost: Optional[CostBreakdown] = None
    
    @property
    def gross_pnl(self) -> float:
        """Gross PnL before costs."""
        if self.exit_price is None:
            return 0.0
        return self.quantity * (self.exit_price - self.entry_price)
    
    @property
    def total_costs(self) -> float:
        """Total transaction costs."""
        total = self.entry_cost.total_cost
        if self.exit_cost:
            total += self.exit_cost.total_cost
        return total
    
    @property
    def net_pnl(self) -> float:
        """Net PnL after all costs."""
        return self.gross_pnl - self.total_costs
    
    @property
    def cost_drag_pct(self) -> float:
        """Cost drag as percentage of gross PnL."""
        if self.gross_pnl == 0:
            return 0.0
        return (self.total_costs / abs(self.gross_pnl)) * 100 if self.gross_pnl != 0 else 0.0


# =============================================================================
# COMMISSION MODELS
# =============================================================================

class CommissionModel(ABC):
    """Abstract base class for commission models."""
    
    @abstractmethod
    def calculate(self, trade: TradeDetails) -> float:
        """Calculate commission for a trade."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get human-readable description of the commission structure."""
        pass


@dataclass
class TieredCommissionModel(CommissionModel):
    """
    Tiered commission model with percentage + per-share/component fees.
    
    Common for: Stocks, ETFs
    """
    percentage_rate: float = 0.0  # Percentage of notional (e.g., 0.001 = 0.1%)
    per_share_rate: float = 0.0   # Per share/unit (e.g., 0.01 = $0.01/share)
    min_commission: float = 0.0   # Minimum commission per trade
    max_commission: Optional[float] = None  # Maximum commission cap
    
    def calculate(self, trade: TradeDetails) -> float:
        """Calculate tiered commission."""
        notional = trade.notional_value
        shares = abs(trade.quantity)
        
        # Calculate both components
        pct_fee = notional * self.percentage_rate
        share_fee = shares * self.per_share_rate
        
        # Take maximum of the two (common broker structure)
        commission = max(pct_fee, share_fee)
        
        # Apply minimum
        commission = max(commission, self.min_commission)
        
        # Apply maximum cap if set
        if self.max_commission is not None:
            commission = min(commission, self.max_commission)
        
        return commission
    
    def get_description(self) -> str:
        return (f"Tiered: max({self.percentage_rate*100:.3f}%, ${self.per_share_rate:.3f}/share) "
                f"[min: ${self.min_commission:.2f}" + 
                (f", max: ${self.max_commission:.2f}]" if self.max_commission else "]"))


@dataclass
class FlatCommissionModel(CommissionModel):
    """
    Flat fee per trade or per contract.
    
    Common for: Options, some crypto exchanges
    """
    flat_fee: float  # Flat fee per trade
    per_contract_rate: float = 0.0  # Additional per-contract fee
    
    def calculate(self, trade: TradeDetails) -> float:
        """Calculate flat commission."""
        contracts = abs(trade.quantity)
        return self.flat_fee + (contracts * self.per_contract_rate)
    
    def get_description(self) -> str:
        if self.per_contract_rate > 0:
            return f"Flat: ${self.flat_fee:.2f} + ${self.per_contract_rate:.3f}/contract"
        return f"Flat: ${self.flat_fee:.2f} per trade"


@dataclass
class CryptoCommissionModel(CommissionModel):
    """
    Crypto-specific commission model with maker/taker fees.
    
    Common for: Cryptocurrency exchanges
    """
    maker_rate: float = 0.0  # Maker fee (limit orders that add liquidity)
    taker_rate: float = 0.0  # Taker fee (market orders that remove liquidity)
    
    def calculate(self, trade: TradeDetails, is_maker: bool = False) -> float:
        """Calculate crypto commission."""
        notional = trade.notional_value
        rate = self.maker_rate if is_maker else self.taker_rate
        return notional * rate
    
    def get_description(self) -> str:
        return f"Crypto: Maker {self.maker_rate*100:.3f}%, Taker {self.taker_rate*100:.3f}%"


@dataclass
class FuturesCommissionModel(CommissionModel):
    """
    Futures-specific commission model.
    
    Common for: Futures contracts
    """
    per_contract_fee: float  # Fee per contract
    exchange_fee: float = 0.0  # Exchange fee per contract
    clearing_fee: float = 0.0  # Clearing fee per contract
    
    def calculate(self, trade: TradeDetails) -> float:
        """Calculate futures commission."""
        contracts = abs(trade.quantity)
        total_per_contract = self.per_contract_fee + self.exchange_fee + self.clearing_fee
        return contracts * total_per_contract
    
    def get_description(self) -> str:
        total = self.per_contract_fee + self.exchange_fee + self.clearing_fee
        return (f"Futures: ${total:.3f}/contract "
                f"(broker: ${self.per_contract_fee:.3f}, "
                f"exch: ${self.exchange_fee:.3f}, "
                f"clear: ${self.clearing_fee:.3f})")


@dataclass
class ForexCommissionModel(CommissionModel):
    """
    Forex commission model (spread-based or commission-based).
    
    Common for: Currency trading
    """
    spread_pips: float = 1.0  # Typical spread in pips
    commission_per_lot: float = 0.0  # Commission per standard lot (100k units)
    
    def calculate(self, trade: TradeDetails) -> float:
        """Calculate forex commission (spread cost)."""
        # Spread cost is embedded in execution price
        # Commission is additional if charged
        lots = abs(trade.quantity) / 100000
        return lots * self.commission_per_lot
    
    def get_description(self) -> str:
        return f"Forex: {self.spread_pips:.1f} pips spread + ${self.commission_per_lot:.2f}/lot"


# =============================================================================
# SLIPPAGE MODELS
# =============================================================================

class SlippageModel(ABC):
    """Abstract base class for slippage models."""
    
    @abstractmethod
    def estimate(self, trade: TradeDetails) -> float:
        """Estimate slippage in currency terms."""
        pass


@dataclass
class VolumeBasedSlippageModel(SlippageModel):
    """
    Slippage model based on trade size relative to volume.
    
    Formula: slippage = base_slippage * (trade_size / volume)^exponent
    """
    base_slippage_bps: float = 5.0  # Base slippage in basis points
    volume_exponent: float = 0.5    # Square root model typically
    min_slippage_bps: float = 1.0   # Minimum slippage floor
    max_slippage_bps: float = 100.0  # Maximum slippage cap
    
    def estimate(self, trade: TradeDetails) -> float:
        """Estimate slippage based on volume participation."""
        if trade.volume_24h is None or trade.volume_24h <= 0:
            # Default to base slippage if no volume data
            slippage_bps = self.base_slippage_bps
        else:
            # Calculate participation rate
            participation = trade.notional_value / trade.volume_24h
            
            # Apply square root model
            slippage_bps = self.base_slippage_bps * (participation ** self.volume_exponent)
        
        # Apply floor and cap
        slippage_bps = max(slippage_bps, self.min_slippage_bps)
        slippage_bps = min(slippage_bps, self.max_slippage_bps)
        
        # Convert to currency
        slippage = trade.notional_value * (slippage_bps / 10000)
        
        return slippage


@dataclass
class VolatilityBasedSlippageModel(SlippageModel):
    """
    Slippage model incorporating volatility.
    
    Higher volatility = higher slippage
    """
    base_slippage_bps: float = 5.0
    volatility_multiplier: float = 10.0  # Scale factor for volatility impact
    reference_volatility: float = 0.20   # 20% annual vol as baseline
    
    def estimate(self, trade: TradeDetails) -> float:
        """Estimate slippage incorporating volatility."""
        slippage_bps = self.base_slippage_bps
        
        if trade.volatility is not None and trade.volatility > 0:
            # Adjust slippage based on relative volatility
            vol_ratio = trade.volatility / self.reference_volatility
            slippage_bps *= (1 + self.volatility_multiplier * (vol_ratio - 1))
        
        # Convert to currency
        slippage = trade.notional_value * (slippage_bps / 10000)
        
        return max(slippage, 0)


@dataclass
class CombinedSlippageModel(SlippageModel):
    """
    Combined slippage model using volume, volatility, and spread.
    """
    volume_weight: float = 0.4
    volatility_weight: float = 0.4
    spread_weight: float = 0.2
    
    volume_model: VolumeBasedSlippageModel = field(
        default_factory=lambda: VolumeBasedSlippageModel())
    volatility_model: VolatilityBasedSlippageModel = field(
        default_factory=lambda: VolatilityBasedSlippageModel())
    
    def estimate(self, trade: TradeDetails) -> float:
        """Estimate slippage using combined factors."""
        # Volume-based component
        volume_slippage = self.volume_model.estimate(trade)
        
        # Volatility-based component
        vol_slippage = self.volatility_model.estimate(trade)
        
        # Spread-based component
        spread_slippage = 0.0
        if trade.bid_ask_spread is not None:
            # Assume execution at mid + half spread
            spread_slippage = trade.notional_value * (trade.bid_ask_spread / 2)
        
        # Weighted combination
        total_slippage = (
            self.volume_weight * volume_slippage +
            self.volatility_weight * vol_slippage +
            self.spread_weight * spread_slippage
        )
        
        return total_slippage


# =============================================================================
# MARKET IMPACT MODELS (Advanced)
# =============================================================================

class MarketImpactModel(ABC):
    """Abstract base class for market impact models."""
    
    @abstractmethod
    def calculate(self, trade: TradeDetails) -> float:
        """Calculate market impact cost."""
        pass


@dataclass
class AlmgrenChrissModel(MarketImpactModel):
    """
    Almgren-Chriss market impact model.
    
    Temporary impact: h * sigma * (X/V)^gamma
    Permanent impact: g * sigma * (X/V)^delta
    
    Where:
    - sigma: daily volatility
    - X: trade size
    - V: average daily volume
    - h, g: impact coefficients
    - gamma, delta: exponents (typically 0.5-0.6)
    """
    temporary_impact_coef: float = 0.5  # h
    permanent_impact_coef: float = 0.2  # g
    temp_exponent: float = 0.6          # gamma
    perm_exponent: float = 0.6          # delta
    
    def calculate(self, trade: TradeDetails) -> float:
        """Calculate Almgren-Chriss market impact."""
        if trade.volume_24h is None or trade.volatility is None:
            return 0.0
        
        X = trade.notional_value
        V = trade.volume_24h
        sigma = trade.volatility / np.sqrt(252)  # Convert annual to daily
        
        if V <= 0 or sigma <= 0:
            return 0.0
        
        # Participation rate
        participation = X / V
        
        # Temporary impact (execution cost)
        temp_impact = (self.temporary_impact_coef * sigma * 
                      (participation ** self.temp_exponent))
        
        # Permanent impact (price movement)
        perm_impact = (self.permanent_impact_coef * sigma * 
                      (participation ** self.perm_exponent))
        
        # Total impact in currency terms
        total_impact = (temp_impact + perm_impact) * trade.notional_value
        
        return total_impact


@dataclass
class SquareRootImpactModel(MarketImpactModel):
    """
    Square root market impact model (simpler alternative).
    
    Impact = eta * sigma * sqrt(X/V)
    """
    impact_coef: float = 1.0  # eta
    
    def calculate(self, trade: TradeDetails) -> float:
        """Calculate square root market impact."""
        if trade.volume_24h is None or trade.volatility is None:
            return 0.0
        
        X = trade.notional_value
        V = trade.volume_24h
        sigma = trade.volatility / np.sqrt(252)  # Daily volatility
        
        if V <= 0 or sigma <= 0:
            return 0.0
        
        impact = self.impact_coef * sigma * np.sqrt(X / V)
        return impact * trade.notional_value


# =============================================================================
# MAIN COST MODEL CLASS
# =============================================================================

@dataclass
class AssetCostConfig:
    """Configuration for a specific asset's cost structure."""
    asset_class: AssetClass
    commission_model: CommissionModel
    slippage_model: SlippageModel
    market_impact_model: Optional[MarketImpactModel] = None
    exchange_fees: float = 0.0  # Additional exchange fees
    regulatory_fees: float = 0.0  # SEC, FINRA fees, etc.


class TransactionCostModel:
    """
    Main transaction cost model for multi-asset trading systems.
    
    Features:
    - Asset-class specific commission structures
    - Configurable slippage models
    - Optional market impact modeling
    - Round-trip cost calculation
    - Post-commission PnL tracking
    """
    
    # Default configurations for each asset class
    DEFAULT_CONFIGS: Dict[AssetClass, AssetCostConfig] = {
        AssetClass.STOCK: AssetCostConfig(
            asset_class=AssetClass.STOCK,
            commission_model=TieredCommissionModel(
                percentage_rate=0.0,  # Many brokers offer zero-commission
                per_share_rate=0.005,  # $0.005 per share
                min_commission=1.0,
                max_commission=None
            ),
            slippage_model=CombinedSlippageModel(),
            market_impact_model=None,
            exchange_fees=0.0,
            regulatory_fees=0.0000229  # SEC fee ~$22.90 per $1M
        ),
        
        AssetClass.ETF: AssetCostConfig(
            asset_class=AssetClass.ETF,
            commission_model=TieredCommissionModel(
                percentage_rate=0.0,
                per_share_rate=0.005,
                min_commission=1.0,
                max_commission=None
            ),
            slippage_model=CombinedSlippageModel(),
            market_impact_model=None,
            exchange_fees=0.0,
            regulatory_fees=0.0000229
        ),
        
        AssetClass.FUTURES: AssetCostConfig(
            asset_class=AssetClass.FUTURES,
            commission_model=FuturesCommissionModel(
                per_contract_fee=0.50,  # Broker commission
                exchange_fee=0.85,       # Exchange fee
                clearing_fee=0.05        # Clearing fee
            ),
            slippage_model=VolumeBasedSlippageModel(
                base_slippage_bps=2.0,  # Futures typically tighter
                min_slippage_bps=0.5
            ),
            market_impact_model=None,
            exchange_fees=0.0,
            regulatory_fees=0.02  # NFA fee per contract
        ),
        
        AssetClass.CRYPTO: AssetCostConfig(
            asset_class=AssetClass.CRYPTO,
            commission_model=CryptoCommissionModel(
                maker_rate=0.0008,  # 0.08% maker
                taker_rate=0.0012   # 0.12% taker
            ),
            slippage_model=CombinedSlippageModel(
                volume_weight=0.5,
                volatility_weight=0.5,
                spread_weight=0.0
            ),
            market_impact_model=SquareRootImpactModel(impact_coef=0.8),
            exchange_fees=0.0,
            regulatory_fees=0.0
        ),
        
        AssetClass.FOREX: AssetCostConfig(
            asset_class=AssetClass.FOREX,
            commission_model=ForexCommissionModel(
                spread_pips=1.0,
                commission_per_lot=0.0
            ),
            slippage_model=VolumeBasedSlippageModel(
                base_slippage_bps=1.0
            ),
            market_impact_model=None,
            exchange_fees=0.0,
            regulatory_fees=0.0
        ),
        
        AssetClass.OPTION: AssetCostConfig(
            asset_class=AssetClass.OPTION,
            commission_model=FlatCommissionModel(
                flat_fee=0.50,  # Base per contract
                per_contract_rate=0.50
            ),
            slippage_model=VolumeBasedSlippageModel(
                base_slippage_bps=10.0,  # Options wider spreads
                min_slippage_bps=5.0
            ),
            market_impact_model=None,
            exchange_fees=0.0,
            regulatory_fees=0.000029  # Options regulatory fee
        )
    }
    
    def __init__(self, configs: Optional[Dict[AssetClass, AssetCostConfig]] = None):
        """
        Initialize the cost model.
        
        Args:
            configs: Optional custom configurations per asset class.
                     If None, uses default configurations.
        """
        self.configs = configs or self.DEFAULT_CONFIGS.copy()
        self._trade_history: List[Tuple[TradeDetails, CostBreakdown]] = []
        
        logger.info("TransactionCostModel initialized")
    
    def set_config(self, asset_class: AssetClass, config: AssetCostConfig) -> None:
        """Set custom configuration for an asset class."""
        self.configs[asset_class] = config
        logger.info(f"Updated config for {asset_class.name}")
    
    def get_config(self, asset_class: AssetClass) -> AssetCostConfig:
        """Get configuration for an asset class."""
        if asset_class not in self.configs:
            raise ValueError(f"No configuration found for {asset_class}")
        return self.configs[asset_class]
    
    def calculate_commission(self, trade: TradeDetails, is_maker: bool = False) -> float:
        """
        Calculate commission for a trade.
        
        Args:
            trade: Trade details
            is_maker: For crypto - True if maker order
        
        Returns:
            Commission amount in currency
        """
        config = self.get_config(trade.asset_class)
        commission_model = config.commission_model
        
        # Handle crypto maker/taker
        if isinstance(commission_model, CryptoCommissionModel):
            commission = commission_model.calculate(trade, is_maker)
        else:
            commission = commission_model.calculate(trade)
        
        # Add regulatory fees
        if config.regulatory_fees > 0:
            regulatory = trade.notional_value * config.regulatory_fees
            commission += regulatory
        
        return commission
    
    def estimate_slippage(self, trade: TradeDetails) -> float:
        """
        Estimate slippage for a trade.
        
        Args:
            trade: Trade details with optional volume/volatility data
        
        Returns:
            Estimated slippage in currency
        """
        config = self.get_config(trade.asset_class)
        return config.slippage_model.estimate(trade)
    
    def calculate_market_impact(self, trade: TradeDetails) -> float:
        """
        Calculate market impact for a trade (if model configured).
        
        Args:
            trade: Trade details
        
        Returns:
            Market impact cost in currency
        """
        config = self.get_config(trade.asset_class)
        
        if config.market_impact_model is None:
            return 0.0
        
        return config.market_impact_model.calculate(trade)
    
    def calculate_round_trip_cost(
        self,
        symbol: str,
        asset_class: AssetClass,
        quantity: float,
        entry_price: float,
        exit_price: float,
        entry_volume_24h: Optional[float] = None,
        exit_volume_24h: Optional[float] = None,
        volatility: Optional[float] = None,
        is_maker_entry: bool = False,
        is_maker_exit: bool = False
    ) -> Dict[str, float]:
        """
        Calculate complete round-trip transaction costs.
        
        Args:
            symbol: Trading symbol
            asset_class: Asset class
            quantity: Position size (positive for long)
            entry_price: Entry execution price
            exit_price: Exit execution price
            entry_volume_24h: 24h volume at entry
            exit_volume_24h: 24h volume at exit
            volatility: Annualized volatility
            is_maker_entry: True if entry was maker order (crypto)
            is_maker_exit: True if exit was maker order (crypto)
        
        Returns:
            Dictionary with detailed cost breakdown
        """
        # Entry trade
        entry_trade = TradeDetails(
            symbol=symbol,
            asset_class=asset_class,
            quantity=quantity,
            price=entry_price,
            volume_24h=entry_volume_24h,
            volatility=volatility
        )
        
        # Exit trade (negative quantity for closing)
        exit_trade = TradeDetails(
            symbol=symbol,
            asset_class=asset_class,
            quantity=-quantity,
            price=exit_price,
            volume_24h=exit_volume_24h,
            volatility=volatility
        )
        
        # Calculate entry costs
        entry_commission = self.calculate_commission(entry_trade, is_maker_entry)
        entry_slippage = self.estimate_slippage(entry_trade)
        entry_impact = self.calculate_market_impact(entry_trade)
        
        # Calculate exit costs
        exit_commission = self.calculate_commission(exit_trade, is_maker_exit)
        exit_slippage = self.estimate_slippage(exit_trade)
        exit_impact = self.calculate_market_impact(exit_trade)
        
        # Get exchange fees
        config = self.get_config(asset_class)
        entry_exchange = entry_trade.notional_value * config.exchange_fees
        exit_exchange = exit_trade.notional_value * config.exchange_fees
        
        # Summarize
        total_commission = entry_commission + exit_commission
        total_slippage = entry_slippage + exit_slippage
        total_impact = entry_impact + exit_impact
        total_fees = entry_exchange + exit_exchange
        total_cost = total_commission + total_slippage + total_impact + total_fees
        
        # Notional values
        entry_notional = entry_trade.notional_value
        exit_notional = exit_trade.notional_value
        total_notional = entry_notional + exit_notional
        
        return {
            'entry_commission': entry_commission,
            'exit_commission': exit_commission,
            'total_commission': total_commission,
            'entry_slippage': entry_slippage,
            'exit_slippage': exit_slippage,
            'total_slippage': total_slippage,
            'entry_market_impact': entry_impact,
            'exit_market_impact': exit_impact,
            'total_market_impact': total_impact,
            'entry_exchange_fees': entry_exchange,
            'exit_exchange_fees': exit_exchange,
            'total_exchange_fees': total_fees,
            'total_cost': total_cost,
            'entry_notional': entry_notional,
            'exit_notional': exit_notional,
            'total_notional': total_notional,
            'cost_as_pct_of_notional': (total_cost / total_notional * 100) if total_notional > 0 else 0,
            'cost_in_bps': (total_cost / total_notional * 10000) if total_notional > 0 else 0
        }
    
    def calculate_post_commission_pnl(
        self,
        symbol: str,
        asset_class: AssetClass,
        quantity: float,
        entry_price: float,
        exit_price: float,
        entry_volume_24h: Optional[float] = None,
        exit_volume_24h: Optional[float] = None,
        volatility: Optional[float] = None,
        entry_time: Optional[datetime] = None,
        exit_time: Optional[datetime] = None
    ) -> PositionPnL:
        """
        Calculate post-commission PnL for a complete trade.
        
        Args:
            symbol: Trading symbol
            asset_class: Asset class
            quantity: Position size
            entry_price: Entry price
            exit_price: Exit price
            entry_volume_24h: Volume at entry
            exit_volume_24h: Volume at exit
            volatility: Annualized volatility
            entry_time: Entry timestamp
            exit_time: Exit timestamp
        
        Returns:
            PositionPnL object with full cost breakdown
        """
        # Calculate round-trip costs
        costs = self.calculate_round_trip_cost(
            symbol=symbol,
            asset_class=asset_class,
            quantity=quantity,
            entry_price=entry_price,
            exit_price=exit_price,
            entry_volume_24h=entry_volume_24h,
            exit_volume_24h=exit_volume_24h,
            volatility=volatility
        )
        
        # Create entry cost breakdown
        entry_cost = CostBreakdown(
            commission=costs['entry_commission'],
            slippage=costs['entry_slippage'],
            market_impact=costs['entry_market_impact'],
            fees=costs['entry_exchange_fees'],
            total_cost=costs['entry_commission'] + costs['entry_slippage'] + 
                       costs['entry_market_impact'] + costs['entry_exchange_fees']
        )
        
        # Create exit cost breakdown
        exit_cost = CostBreakdown(
            commission=costs['exit_commission'],
            slippage=costs['exit_slippage'],
            market_impact=costs['exit_market_impact'],
            fees=costs['exit_exchange_fees'],
            total_cost=costs['exit_commission'] + costs['exit_slippage'] + 
                       costs['exit_market_impact'] + costs['exit_exchange_fees']
        )
        
        # Create position PnL
        position_pnl = PositionPnL(
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            exit_price=exit_price,
            entry_time=entry_time,
            exit_time=exit_time,
            entry_cost=entry_cost,
            exit_cost=exit_cost
        )
        
        return position_pnl
    
    def estimate_breakeven_move(
        self,
        symbol: str,
        asset_class: AssetClass,
        quantity: float,
        price: float,
        volume_24h: Optional[float] = None,
        volatility: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Estimate the price move required to break even after costs.
        
        Args:
            symbol: Trading symbol
            asset_class: Asset class
            quantity: Position size
            price: Current price
            volume_24h: 24h volume
            volatility: Annualized volatility
        
        Returns:
            Dictionary with breakeven analysis
        """
        # Create dummy trade for cost estimation
        trade = TradeDetails(
            symbol=symbol,
            asset_class=asset_class,
            quantity=quantity,
            price=price,
            volume_24h=volume_24h,
            volatility=volatility
        )
        
        # Estimate one-way costs
        commission = self.calculate_commission(trade)
        slippage = self.estimate_slippage(trade)
        impact = self.calculate_market_impact(trade)
        
        one_way_cost = commission + slippage + impact
        round_trip_cost = one_way_cost * 2  # Entry + exit
        
        notional = trade.notional_value
        
        # Breakeven price move
        if quantity != 0:
            breakeven_move = round_trip_cost / abs(quantity)
            breakeven_pct = (breakeven_move / price) * 100
        else:
            breakeven_move = 0
            breakeven_pct = 0
        
        return {
            'one_way_cost': one_way_cost,
            'round_trip_cost': round_trip_cost,
            'breakeven_price_move': breakeven_move,
            'breakeven_pct': breakeven_pct,
            'commission': commission,
            'slippage': slippage,
            'market_impact': impact,
            'notional_value': notional
        }
    
    def get_cost_summary(self) -> pd.DataFrame:
        """
        Get summary of cost configurations for all asset classes.
        
        Returns:
            DataFrame with cost configuration summary
        """
        data = []
        for asset_class, config in self.configs.items():
            data.append({
                'Asset Class': asset_class.name,
                'Commission Model': config.commission_model.get_description(),
                'Exchange Fees': f"{config.exchange_fees*100:.4f}%" if config.exchange_fees > 0 else "$0",
                'Regulatory Fees': f"{config.regulatory_fees*100:.4f}%" if config.regulatory_fees > 0 else "$0",
                'Market Impact': 'Enabled' if config.market_impact_model else 'Disabled'
            })
        
        return pd.DataFrame(data)


# =============================================================================
# PRESET CONFIGURATIONS FOR RETAIL TRADERS
# =============================================================================

def create_retail_stock_config(
    broker: str = 'interactive_brokers'
) -> AssetCostConfig:
    """
    Create retail stock trading configuration.
    
    Brokers:
    - 'zero_commission': Robinhood, Webull style (0%)
    - 'interactive_brokers': IBKR Pro tiered
    - 'traditional': E*Trade, Schwab, etc.
    """
    if broker == 'zero_commission':
        commission = TieredCommissionModel(
            percentage_rate=0.0,
            per_share_rate=0.0,
            min_commission=0.0
        )
    elif broker == 'interactive_brokers':
        commission = TieredCommissionModel(
            percentage_rate=0.0035,  # 0.35% max
            per_share_rate=0.0035,   # $0.0035 per share
            min_commission=0.35,
            max_commission=0.01      # 1% cap
        )
    else:  # traditional
        commission = TieredCommissionModel(
            percentage_rate=0.0,
            per_share_rate=0.01,  # $0.01 per share
            min_commission=4.95,
            max_commission=None
        )
    
    return AssetCostConfig(
        asset_class=AssetClass.STOCK,
        commission_model=commission,
        slippage_model=CombinedSlippageModel(),
        regulatory_fees=0.0000229
    )


def create_retail_crypto_config(
    exchange: str = 'coinbase_pro'
) -> AssetCostConfig:
    """
    Create retail crypto trading configuration.
    
    Exchanges:
    - 'coinbase_pro': Coinbase Pro/Advanced
    - 'binance_us': Binance.US
    - 'kraken': Kraken
    """
    if exchange == 'coinbase_pro':
        commission = CryptoCommissionModel(
            maker_rate=0.0060,  # 0.60%
            taker_rate=0.0080   # 0.80%
        )
    elif exchange == 'binance_us':
        commission = CryptoCommissionModel(
            maker_rate=0.0010,  # 0.10%
            taker_rate=0.0010   # 0.10%
        )
    else:  # kraken
        commission = CryptoCommissionModel(
            maker_rate=0.0016,  # 0.16%
            taker_rate=0.0026   # 0.26%
        )
    
    return AssetCostConfig(
        asset_class=AssetClass.CRYPTO,
        commission_model=commission,
        slippage_model=CombinedSlippageModel(
            volume_weight=0.5,
            volatility_weight=0.5
        ),
        market_impact_model=SquareRootImpactModel(impact_coef=0.8)
    )


def create_retail_futures_config(
    broker: str = 'ninjatrader'
) -> AssetCostConfig:
    """
    Create retail futures trading configuration.
    
    Brokers:
    - 'ninjatrader': NinjaTrader
    - 'tradovate': Tradovate
    - 'interactive_brokers': IBKR
    """
    if broker == 'ninjatrader':
        commission = FuturesCommissionModel(
            per_contract_fee=0.09,
            exchange_fee=0.85,
            clearing_fee=0.05
        )
    elif broker == 'tradovate':
        commission = FuturesCommissionModel(
            per_contract_fee=0.29,
            exchange_fee=0.85,
            clearing_fee=0.05
        )
    else:  # interactive_brokers
        commission = FuturesCommissionModel(
            per_contract_fee=0.85,
            exchange_fee=0.85,
            clearing_fee=0.05
        )
    
    return AssetCostConfig(
        asset_class=AssetClass.FUTURES,
        commission_model=commission,
        slippage_model=VolumeBasedSlippageModel(
            base_slippage_bps=2.0,
            min_slippage_bps=0.5
        ),
        regulatory_fees=0.02  # NFA fee
    )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_cost_model_from_current(
    current_percentage: float = 0.001,
    current_per_share: float = 0.01,
    current_slippage: float = 0.0005
) -> TransactionCostModel:
    """
    Create a cost model based on current system parameters.
    
    This helps migrate from the existing 0.1% + $0.01/share + 0.05% slippage model
    to the new comprehensive model.
    
    Args:
        current_percentage: Current percentage fee (0.001 = 0.1%)
        current_per_share: Current per-share fee
        current_slippage: Current slippage estimate (0.0005 = 0.05%)
    
    Returns:
        TransactionCostModel configured to match current system
    """
    configs = {}
    
    # Stocks and ETFs use the current model
    for asset_class in [AssetClass.STOCK, AssetClass.ETF]:
        configs[asset_class] = AssetCostConfig(
            asset_class=asset_class,
            commission_model=TieredCommissionModel(
                percentage_rate=current_percentage,
                per_share_rate=current_per_share,
                min_commission=1.0
            ),
            slippage_model=VolumeBasedSlippageModel(
                base_slippage_bps=current_slippage * 10000
            )
        )
    
    # Futures - use default
    configs[AssetClass.FUTURES] = TransactionCostModel.DEFAULT_CONFIGS[AssetClass.FUTURES]
    
    # Crypto - use default
    configs[AssetClass.CRYPTO] = TransactionCostModel.DEFAULT_CONFIGS[AssetClass.CRYPTO]
    
    return TransactionCostModel(configs)


# =============================================================================
# EXAMPLE USAGE AND DEMONSTRATION
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("TRANSACTION COST MODEL - DEMONSTRATION")
    print("=" * 70)
    
    # Initialize the cost model
    cost_model = TransactionCostModel()
    
    # Display default configurations
    print("\n📊 DEFAULT COST CONFIGURATIONS:")
    print(cost_model.get_cost_summary().to_string(index=False))
    
    # Example 1: Stock Trade (JPM)
    print("\n" + "=" * 70)
    print("EXAMPLE 1: STOCK TRADE - JPM")
    print("=" * 70)
    
    jpm_entry = TradeDetails(
        symbol="JPM",
        asset_class=AssetClass.STOCK,
        quantity=100,
        price=175.50,
        volume_24h=15_000_000,  # $15M daily volume
        volatility=0.25  # 25% annual vol
    )
    
    jpm_commission = cost_model.calculate_commission(jpm_entry)
    jpm_slippage = cost_model.estimate_slippage(jpm_entry)
    
    print(f"Trade: Buy 100 shares JPM @ $175.50")
    print(f"Notional Value: ${jpm_entry.notional_value:,.2f}")
    print(f"Commission: ${jpm_commission:.2f}")
    print(f"Estimated Slippage: ${jpm_slippage:.2f}")
    print(f"One-way Cost: ${jpm_commission + jpm_slippage:.2f}")
    
    # Round-trip cost
    jpm_rt = cost_model.calculate_round_trip_cost(
        symbol="JPM",
        asset_class=AssetClass.STOCK,
        quantity=100,
        entry_price=175.50,
        exit_price=180.00,
        entry_volume_24h=15_000_000,
        exit_volume_24h=15_000_000,
        volatility=0.25
    )
    
    print(f"\nRound-trip Analysis (Entry $175.50, Exit $180.00):")
    print(f"  Gross PnL: ${100 * (180.00 - 175.50):,.2f}")
    print(f"  Total Commission: ${jpm_rt['total_commission']:.2f}")
    print(f"  Total Slippage: ${jpm_rt['total_slippage']:.2f}")
    print(f"  Total Cost: ${jpm_rt['total_cost']:.2f}")
    print(f"  Cost as % of Notional: {jpm_rt['cost_as_pct_of_notional']:.3f}%")
    
    # Post-commission PnL
    jpm_pnl = cost_model.calculate_post_commission_pnl(
        symbol="JPM",
        asset_class=AssetClass.STOCK,
        quantity=100,
        entry_price=175.50,
        exit_price=180.00,
        entry_volume_24h=15_000_000,
        exit_volume_24h=15_000_000,
        volatility=0.25
    )
    
    print(f"\nPost-Commission PnL:")
    print(f"  Gross PnL: ${jpm_pnl.gross_pnl:,.2f}")
    print(f"  Total Costs: ${jpm_pnl.total_costs:.2f}")
    print(f"  Net PnL: ${jpm_pnl.net_pnl:,.2f}")
    print(f"  Cost Drag: {jpm_pnl.cost_drag_pct:.1f}%")
    
    # Example 2: Crypto Trade (BTC)
    print("\n" + "=" * 70)
    print("EXAMPLE 2: CRYPTO TRADE - BTC")
    print("=" * 70)
    
    btc_entry = TradeDetails(
        symbol="BTC-USD",
        asset_class=AssetClass.CRYPTO,
        quantity=0.5,
        price=67_500.00,
        volume_24h=35_000_000_000,  # $35B daily volume
        volatility=0.65  # 65% annual vol
    )
    
    btc_commission = cost_model.calculate_commission(btc_entry, is_maker=False)
    btc_slippage = cost_model.estimate_slippage(btc_entry)
    btc_impact = cost_model.calculate_market_impact(btc_entry)
    
    print(f"Trade: Buy 0.5 BTC @ $67,500")
    print(f"Notional Value: ${btc_entry.notional_value:,.2f}")
    print(f"Commission (Taker): ${btc_commission:.2f}")
    print(f"Estimated Slippage: ${btc_slippage:.2f}")
    print(f"Market Impact: ${btc_impact:.2f}")
    print(f"One-way Cost: ${btc_commission + btc_slippage + btc_impact:.2f}")
    
    # Round-trip
    btc_rt = cost_model.calculate_round_trip_cost(
        symbol="BTC-USD",
        asset_class=AssetClass.CRYPTO,
        quantity=0.5,
        entry_price=67_500.00,
        exit_price=70_000.00,
        entry_volume_24h=35_000_000_000,
        exit_volume_24h=35_000_000_000,
        volatility=0.65
    )
    
    print(f"\nRound-trip Analysis (Entry $67,500, Exit $70,000):")
    print(f"  Gross PnL: ${0.5 * (70000 - 67500):,.2f}")
    print(f"  Total Commission: ${btc_rt['total_commission']:.2f}")
    print(f"  Total Slippage: ${btc_rt['total_slippage']:.2f}")
    print(f"  Total Market Impact: ${btc_rt['total_market_impact']:.2f}")
    print(f"  Total Cost: ${btc_rt['total_cost']:.2f}")
    print(f"  Cost as % of Notional: {btc_rt['cost_as_pct_of_notional']:.3f}%")
    
    # Example 3: Futures Trade (CL=F - Crude Oil)
    print("\n" + "=" * 70)
    print("EXAMPLE 3: FUTURES TRADE - CL=F (Crude Oil)")
    print("=" * 70)
    
    cl_entry = TradeDetails(
        symbol="CL=F",
        asset_class=AssetClass.FUTURES,
        quantity=2,  # 2 contracts
        price=78.50,
        volume_24h=500_000_000,  # ~$500M notional
        volatility=0.35
    )
    
    cl_commission = cost_model.calculate_commission(cl_entry)
    cl_slippage = cost_model.estimate_slippage(cl_entry)
    
    print(f"Trade: Buy 2 CL contracts @ $78.50")
    print(f"Notional Value: ${cl_entry.notional_value:,.2f}")
    print(f"Commission: ${cl_commission:.2f}")
    print(f"Estimated Slippage: ${cl_slippage:.2f}")
    print(f"One-way Cost: ${cl_commission + cl_slippage:.2f}")
    
    # Round-trip
    cl_rt = cost_model.calculate_round_trip_cost(
        symbol="CL=F",
        asset_class=AssetClass.FUTURES,
        quantity=2,
        entry_price=78.50,
        exit_price=80.00,
        entry_volume_24h=500_000_000,
        exit_volume_24h=500_000_000,
        volatility=0.35
    )
    
    print(f"\nRound-trip Analysis (Entry $78.50, Exit $80.00):")
    print(f"  Gross PnL: ${2 * 1000 * (80.00 - 78.50):,.2f} (2 contracts x 1000 barrels)")
    print(f"  Total Commission: ${cl_rt['total_commission']:.2f}")
    print(f"  Total Slippage: ${cl_rt['total_slippage']:.2f}")
    print(f"  Total Cost: ${cl_rt['total_cost']:.2f}")
    print(f"  Cost as % of Notional: {cl_rt['cost_as_pct_of_notional']:.3f}%")
    
    # Example 4: ETF Trade (SPY)
    print("\n" + "=" * 70)
    print("EXAMPLE 4: ETF TRADE - SPY")
    print("=" * 70)
    
    spy_entry = TradeDetails(
        symbol="SPY",
        asset_class=AssetClass.ETF,
        quantity=50,
        price=595.00,
        volume_24h=25_000_000_000,  # Very liquid
        volatility=0.16
    )
    
    spy_commission = cost_model.calculate_commission(spy_entry)
    spy_slippage = cost_model.estimate_slippage(spy_entry)
    
    print(f"Trade: Buy 50 SPY shares @ $595.00")
    print(f"Notional Value: ${spy_entry.notional_value:,.2f}")
    print(f"Commission: ${spy_commission:.2f}")
    print(f"Estimated Slippage: ${spy_slippage:.2f}")
    print(f"One-way Cost: ${spy_commission + spy_slippage:.2f}")
    
    # Breakeven analysis
    spy_be = cost_model.estimate_breakeven_move(
        symbol="SPY",
        asset_class=AssetClass.ETF,
        quantity=50,
        price=595.00,
        volume_24h=25_000_000_000,
        volatility=0.16
    )
    
    print(f"\nBreakeven Analysis:")
    print(f"  Round-trip Cost: ${spy_be['round_trip_cost']:.2f}")
    print(f"  Required Price Move: ${spy_be['breakeven_price_move']:.2f}")
    print(f"  Required Move %: {spy_be['breakeven_pct']:.3f}%")
    
    # Summary comparison
    print("\n" + "=" * 70)
    print("COST COMPARISON SUMMARY")
    print("=" * 70)
    
    summary_data = [
        {
            'Asset': 'JPM (Stock)',
            'Notional': f"${jpm_entry.notional_value:,.0f}",
            'Commission': f"${jpm_rt['total_commission']:.2f}",
            'Slippage': f"${jpm_rt['total_slippage']:.2f}",
            'Total Cost': f"${jpm_rt['total_cost']:.2f}",
            'Cost %': f"{jpm_rt['cost_as_pct_of_notional']:.3f}%"
        },
        {
            'Asset': 'BTC (Crypto)',
            'Notional': f"${btc_entry.notional_value:,.0f}",
            'Commission': f"${btc_rt['total_commission']:.2f}",
            'Slippage': f"${btc_rt['total_slippage']:.2f}",
            'Total Cost': f"${btc_rt['total_cost']:.2f}",
            'Cost %': f"{btc_rt['cost_as_pct_of_notional']:.3f}%"
        },
        {
            'Asset': 'CL=F (Futures)',
            'Notional': f"${cl_entry.notional_value:,.0f}",
            'Commission': f"${cl_rt['total_commission']:.2f}",
            'Slippage': f"${cl_rt['total_slippage']:.2f}",
            'Total Cost': f"${cl_rt['total_cost']:.2f}",
            'Cost %': f"{cl_rt['cost_as_pct_of_notional']:.3f}%"
        },
        {
            'Asset': 'SPY (ETF)',
            'Notional': f"${spy_entry.notional_value:,.0f}",
            'Commission': f"${spy_be['round_trip_cost']/2:.2f}",
            'Slippage': f"${spy_slippage:.2f}",
            'Total Cost': f"${spy_be['round_trip_cost']:.2f}",
            'Cost %': f"{spy_be['round_trip_cost']/spy_entry.notional_value*100:.3f}%"
        }
    ]
    
    summary_df = pd.DataFrame(summary_data)
    print(summary_df.to_string(index=False))
    
    print("\n" + "=" * 70)
    print("✅ DEMONSTRATION COMPLETE")
    print("=" * 70)
