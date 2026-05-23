"""
Exit Management System for Multi-Asset Algorithmic Trading
==========================================================
Production-ready module with ATR-based exits, partial profit-taking,
time-based exits, and volatility regime adjustments.

Author: Quantitative Finance Research
Version: 1.0.0

Features:
- ATR-based initial SL (1x ATR) and TP (1.5x ATR)
- Half-ATR trailing stop with ratchet mechanism
- Partial profit-taking at configurable levels
- Time-based exits (max hold period)
- Volatility regime adjustment (wider stops in high VIX)
- Asset-class specific handling
- Breakeven stop activation
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple, Callable
from enum import Enum
from datetime import datetime, timedelta
import warnings

# ============================================================================
# ENUMS AND DATA CLASSES
# ============================================================================

class ExitType(Enum):
    """Types of exit signals"""
    INITIAL_STOP = "initial_stop"
    TAKE_PROFIT = "take_profit"
    TRAILING_STOP = "trailing_stop"
    TIME_EXIT = "time_exit"
    PARTIAL_PROFIT = "partial_profit"
    BREAKEVEN = "breakeven"


class VolatilityRegime(Enum):
    """Market volatility regimes"""
    COMPRESSION = "compression"      # ATR < 70% of baseline
    NORMAL = "normal"                # ATR 70-115% of baseline
    EXPANSION = "expansion"          # ATR 115-140% of baseline
    HIGH_VOLATILITY = "high_vol"     # ATR > 140% of baseline
    EXHAUSTION = "exhaustion"        # Declining ATR after high vol


class AssetClass(Enum):
    """Asset class categories for specialized handling"""
    EQUITY_ETF = "equity_etf"
    STOCK = "stock"
    COMMODITY_FUTURES = "commodity_futures"
    CRYPTO = "crypto"


@dataclass
class ExitSignal:
    """Represents an exit signal with all relevant information"""
    exit_type: ExitType
    timestamp: datetime
    price: float
    quantity: float  # Quantity to exit (can be partial)
    reason: str
    pnl: Optional[float] = None
    exit_percentage: float = 100.0  # Percentage of position to exit

    def __repr__(self):
        return (f"ExitSignal({self.exit_type.value}, price={self.price:.4f}, "
                f"qty={self.quantity:.4f}, pct={self.exit_percentage:.1f}%)")


@dataclass
class Position:
    """Represents a trading position"""
    symbol: str
    asset_class: AssetClass
    entry_price: float
    entry_time: datetime
    quantity: float
    direction: int  # 1 for long, -1 for short

    # Exit configuration
    initial_stop_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    trailing_stop_price: Optional[float] = None

    # Position state
    remaining_quantity: float = field(default=0.0)
    highest_price: Optional[float] = None  # For trailing stop (long)
    lowest_price: Optional[float] = None   # For trailing stop (short)
    partial_exits: List[ExitSignal] = field(default_factory=list)
    is_closed: bool = False

    def __post_init__(self):
        if self.remaining_quantity == 0.0:
            self.remaining_quantity = self.quantity
        if self.direction == 1 and self.highest_price is None:
            self.highest_price = self.entry_price
        if self.direction == -1 and self.lowest_price is None:
            self.lowest_price = self.entry_price

    @property
    def unrealized_pnl(self, current_price: float = None) -> float:
        """Calculate unrealized P&L"""
        if current_price is None:
            return 0.0
        return self.direction * (current_price - self.entry_price) * self.remaining_quantity

    @property
    def current_exposure(self) -> float:
        """Current position exposure"""
        return self.remaining_quantity * self.entry_price


# ============================================================================
# VOLATILITY REGIME DETECTOR
# ============================================================================

class VolatilityRegimeDetector:
    """
    Detects market volatility regimes based on ATR analysis.

    Regime Classification:
    - COMPRESSION: ATR < 0.70 * baseline (consolidation, energy building)
    - NORMAL: 0.70 <= ATR/baseline <= 1.15 (normal market conditions)
    - EXPANSION: 1.15 < ATR/baseline <= 1.40 (volatility breaking out)
    - HIGH_VOLATILITY: ATR/baseline > 1.40 (strong sustained trend)
    - EXHAUSTION: Declining ATR after high volatility period
    """

    def __init__(
        self,
        atr_period: int = 14,
        baseline_period: int = 50,
        compression_threshold: float = 0.70,
        expansion_threshold: float = 1.15,
        high_vol_threshold: float = 1.40,
        exhaustion_lookback: int = 5
    ):
        self.atr_period = atr_period
        self.baseline_period = baseline_period
        self.compression_threshold = compression_threshold
        self.expansion_threshold = expansion_threshold
        self.high_vol_threshold = high_vol_threshold
        self.exhaustion_lookback = exhaustion_lookback

        self.atr_history: List[float] = []
        self.regime_history: List[Tuple[datetime, VolatilityRegime]] = []

    def calculate_true_range(self, high: float, low: float, close_prev: float) -> float:
        """Calculate True Range for a single bar"""
        tr1 = high - low
        tr2 = abs(high - close_prev)
        tr3 = abs(low - close_prev)
        return max(tr1, tr2, tr3)

    def calculate_atr(self, prices_df: pd.DataFrame) -> float:
        """Calculate ATR from OHLC DataFrame"""
        if len(prices_df) < self.atr_period:
            return prices_df["high"].iloc[-1] - prices_df["low"].iloc[-1]

        df = prices_df.copy()
        df["tr1"] = df["high"] - df["low"]
        df["tr2"] = abs(df["high"] - df["close"].shift(1))
        df["tr3"] = abs(df["low"] - df["close"].shift(1))
        df["true_range"] = df[["tr1", "tr2", "tr3"]].max(axis=1)
        df["atr"] = df["true_range"].rolling(window=self.atr_period).mean()

        return df["atr"].iloc[-1]

    def detect_regime(
        self,
        current_atr: float,
        timestamp: datetime,
        vix_value: Optional[float] = None
    ) -> VolatilityRegime:
        """
        Detect current volatility regime.

        Args:
            current_atr: Current ATR value
            timestamp: Current timestamp
            vix_value: Optional VIX value for equity markets

        Returns:
            VolatilityRegime enum value
        """
        self.atr_history.append(current_atr)

        # Keep only necessary history
        max_history = max(self.baseline_period + self.exhaustion_lookback, 100)
        if len(self.atr_history) > max_history:
            self.atr_history = self.atr_history[-max_history:]

        if len(self.atr_history) < self.baseline_period:
            return VolatilityRegime.NORMAL

        # Calculate baseline ATR
        baseline_atr = np.mean(self.atr_history[-self.baseline_period:])

        if baseline_atr == 0:
            return VolatilityRegime.NORMAL

        atr_ratio = current_atr / baseline_atr

        # Check for exhaustion (declining ATR after high vol)
        if len(self.atr_history) >= self.exhaustion_lookback + 1:
            recent_atrs = self.atr_history[-self.exhaustion_lookback:]
            previous_atrs = self.atr_history[-(self.exhaustion_lookback+1):-1]

            if (np.mean(recent_atrs) < np.mean(previous_atrs) and 
                len(self.regime_history) > 0 and
                self.regime_history[-1][1] in [VolatilityRegime.HIGH_VOLATILITY, VolatilityRegime.EXPANSION]):
                regime = VolatilityRegime.EXHAUSTION
                self.regime_history.append((timestamp, regime))
                return regime

        # Classify regime based on ATR ratio
        if atr_ratio < self.compression_threshold:
            regime = VolatilityRegime.COMPRESSION
        elif atr_ratio <= self.expansion_threshold:
            regime = VolatilityRegime.NORMAL
        elif atr_ratio <= self.high_vol_threshold:
            regime = VolatilityRegime.EXPANSION
        else:
            regime = VolatilityRegime.HIGH_VOLATILITY

        # Override with VIX if provided (for equity markets)
        if vix_value is not None:
            regime = self._adjust_for_vix(regime, vix_value)

        self.regime_history.append((timestamp, regime))
        return regime

    def _adjust_for_vix(
        self,
        base_regime: VolatilityRegime,
        vix_value: float
    ) -> VolatilityRegime:
        """Adjust regime classification based on VIX level"""
        if vix_value > 30:
            return VolatilityRegime.HIGH_VOLATILITY
        elif vix_value > 20 and base_regime != VolatilityRegime.HIGH_VOLATILITY:
            return VolatilityRegime.EXPANSION
        return base_regime

    def get_regime_multiplier(self, regime: VolatilityRegime) -> float:
        """Get ATR multiplier adjustment for regime"""
        multipliers = {
            VolatilityRegime.COMPRESSION: 0.85,    # Tighter stops
            VolatilityRegime.NORMAL: 1.0,           # Standard stops
            VolatilityRegime.EXPANSION: 1.15,       # Wider stops
            VolatilityRegime.HIGH_VOLATILITY: 1.3,  # Much wider stops
            VolatilityRegime.EXHAUSTION: 1.0        # Back to normal
        }
        return multipliers.get(regime, 1.0)


# ============================================================================
# EXIT MANAGER - MAIN CLASS
# ============================================================================

class ExitManager:
    """
    Comprehensive Exit Management System for Multi-Asset Trading

    Features:
    - ATR-based initial stop loss and take profit
    - Half-ATR trailing stop with ratchet mechanism
    - Partial profit-taking at multiple levels
    - Time-based exits (max hold period)
    - Volatility regime adjustment
    - Asset-class specific handling
    - Breakeven stop activation
    """

    # Default parameters by asset class
    DEFAULT_PARAMS = {
        AssetClass.EQUITY_ETF: {
            "sl_atr_mult": 1.0,
            "tp_atr_mult": 1.5,
            "trail_atr_mult": 0.5,
            "partial_tp_levels": [(1.0, 0.5)],  # (atr_mult, exit_pct)
            "breakeven_atr_mult": 0.8,
            "max_hold_days": 20,
            "ratchet_lock_pct": 0.50
        },
        AssetClass.STOCK: {
            "sl_atr_mult": 1.0,
            "tp_atr_mult": 1.5,
            "trail_atr_mult": 0.5,
            "partial_tp_levels": [(1.0, 0.5)],
            "breakeven_atr_mult": 0.8,
            "max_hold_days": 15,
            "ratchet_lock_pct": 0.50
        },
        AssetClass.COMMODITY_FUTURES: {
            "sl_atr_mult": 1.0,
            "tp_atr_mult": 2.0,
            "trail_atr_mult": 0.5,
            "partial_tp_levels": [(1.0, 0.5), (2.0, 0.25)],
            "breakeven_atr_mult": 0.8,
            "max_hold_days": 10,
            "ratchet_lock_pct": 0.50
        },
        AssetClass.CRYPTO: {
            "sl_atr_mult": 1.5,
            "tp_atr_mult": 2.5,
            "trail_atr_mult": 0.75,
            "partial_tp_levels": [(1.0, 0.3), (2.0, 0.3)],
            "breakeven_atr_mult": 1.0,
            "max_hold_days": 7,
            "ratchet_lock_pct": 0.50
        }
    }

    def __init__(
        self,
        atr_period: int = 14,
        use_volatility_regime: bool = True,
        custom_params: Optional[Dict] = None
    ):
        """
        Initialize Exit Manager

        Args:
            atr_period: Period for ATR calculation
            use_volatility_regime: Whether to adjust for volatility regimes
            custom_params: Override default parameters per asset class
        """
        self.atr_period = atr_period
        self.use_volatility_regime = use_volatility_regime
        self.regime_detector = VolatilityRegimeDetector(atr_period=atr_period)

        # Apply custom parameters if provided
        self.params = self.DEFAULT_PARAMS.copy()
        if custom_params:
            for asset_class, params in custom_params.items():
                if asset_class in self.params:
                    self.params[asset_class].update(params)

        # Track active positions
        self.positions: Dict[str, Position] = {}

        # Track partial profit levels hit
        self.partial_levels_hit: Dict[str, List[float]] = {}

    def calculate_atr(self, prices_df: pd.DataFrame, period: Optional[int] = None) -> float:
        """Calculate ATR from OHLC DataFrame"""
        if period is None:
            period = self.atr_period

        if len(prices_df) < period:
            # Fallback: use simple range
            return (prices_df["high"].iloc[-period:] - prices_df["low"].iloc[-period:]).mean()

        df = prices_df.copy()
        df["tr1"] = df["high"] - df["low"]
        df["tr2"] = abs(df["high"] - df["close"].shift(1))
        df["tr3"] = abs(df["low"] - df["close"].shift(1))
        df["true_range"] = df[["tr1", "tr2", "tr3"]].max(axis=1)
        df["atr"] = df["true_range"].rolling(window=period).mean()

        return df["atr"].iloc[-1]

    def initialize_position(
        self,
        symbol: str,
        asset_class: AssetClass,
        entry_price: float,
        entry_time: datetime,
        quantity: float,
        direction: int,  # 1 for long, -1 for short
        prices_df: pd.DataFrame,
        vix_value: Optional[float] = None,
        custom_params: Optional[Dict] = None
    ) -> Position:
        """
        Initialize a new position with calculated exit levels

        Args:
            symbol: Trading symbol
            asset_class: Asset class category
            entry_price: Entry price
            entry_time: Entry timestamp
            quantity: Position quantity
            direction: 1 for long, -1 for short
            prices_df: OHLC DataFrame for ATR calculation
            vix_value: Optional VIX value for regime detection
            custom_params: Override default parameters for this position

        Returns:
            Position object with initialized exit levels
        """
        # Get parameters for asset class
        params = self.params[asset_class].copy()
        if custom_params:
            params.update(custom_params)

        # Calculate ATR
        current_atr = self.calculate_atr(prices_df)

        # Detect volatility regime and adjust multipliers
        regime = VolatilityRegime.NORMAL
        regime_mult = 1.0
        if self.use_volatility_regime:
            regime = self.regime_detector.detect_regime(current_atr, entry_time, vix_value)
            regime_mult = self.regime_detector.get_regime_multiplier(regime)

        # Adjust multipliers based on regime
        sl_mult = params["sl_atr_mult"] * regime_mult
        tp_mult = params["tp_atr_mult"] * regime_mult
        trail_mult = params["trail_atr_mult"] * regime_mult

        # Calculate exit levels
        if direction == 1:  # Long
            initial_stop = entry_price - (current_atr * sl_mult)
            take_profit = entry_price + (current_atr * tp_mult)
            trailing_stop = entry_price - (current_atr * trail_mult)
        else:  # Short
            initial_stop = entry_price + (current_atr * sl_mult)
            take_profit = entry_price - (current_atr * tp_mult)
            trailing_stop = entry_price + (current_atr * trail_mult)

        # Create position
        position = Position(
            symbol=symbol,
            asset_class=asset_class,
            entry_price=entry_price,
            entry_time=entry_time,
            quantity=quantity,
            direction=direction,
            initial_stop_price=initial_stop,
            take_profit_price=take_profit,
            trailing_stop_price=trailing_stop,
            highest_price=entry_price if direction == 1 else None,
            lowest_price=entry_price if direction == -1 else None
        )

        # Store position
        self.positions[symbol] = position
        self.partial_levels_hit[symbol] = []

        return position

    def check_initial_stop(self, symbol: str, current_price: float, timestamp: datetime) -> Optional[ExitSignal]:
        """Check if initial stop loss has been hit"""
        if symbol not in self.positions:
            return None

        position = self.positions[symbol]

        if position.is_closed or position.remaining_quantity <= 0:
            return None

        if position.initial_stop_price is None:
            return None

        stop_hit = False
        if position.direction == 1:  # Long
            stop_hit = current_price <= position.initial_stop_price
        else:  # Short
            stop_hit = current_price >= position.initial_stop_price

        if stop_hit:
            pnl = position.direction * (current_price - position.entry_price) * position.remaining_quantity
            return ExitSignal(
                exit_type=ExitType.INITIAL_STOP,
                timestamp=timestamp,
                price=current_price,
                quantity=position.remaining_quantity,
                reason=f"Initial stop loss hit at {position.initial_stop_price:.4f}",
                pnl=pnl,
                exit_percentage=100.0
            )

        return None

    def check_take_profit(self, symbol: str, current_price: float, timestamp: datetime) -> Optional[ExitSignal]:
        """Check if take profit level has been hit"""
        if symbol not in self.positions:
            return None

        position = self.positions[symbol]

        if position.is_closed or position.remaining_quantity <= 0:
            return None

        if position.take_profit_price is None:
            return None

        tp_hit = False
        if position.direction == 1:  # Long
            tp_hit = current_price >= position.take_profit_price
        else:  # Short
            tp_hit = current_price <= position.take_profit_price

        if tp_hit:
            pnl = position.direction * (current_price - position.entry_price) * position.remaining_quantity
            return ExitSignal(
                exit_type=ExitType.TAKE_PROFIT,
                timestamp=timestamp,
                price=current_price,
                quantity=position.remaining_quantity,
                reason=f"Take profit hit at {position.take_profit_price:.4f}",
                pnl=pnl,
                exit_percentage=100.0
            )

        return None

    def update_trailing_stop(
        self,
        symbol: str,
        current_price: float,
        current_atr: float,
        timestamp: datetime
    ) -> Optional[ExitSignal]:
        """
        Update trailing stop and check if hit.

        Implements half-ATR trailing stop that ratchets on new highs/lows
        with gain-locking mechanism.

        Args:
            symbol: Position symbol
            current_price: Current market price
            current_atr: Current ATR value
            timestamp: Current timestamp

        Returns:
            ExitSignal if trailing stop hit, None otherwise
        """
        if symbol not in self.positions:
            return None

        position = self.positions[symbol]

        if position.is_closed or position.remaining_quantity <= 0:
            return None

        params = self.params[position.asset_class]
        trail_mult = params["trail_atr_mult"]
        lock_pct = params["ratchet_lock_pct"]

        # Update highest/lowest price
        if position.direction == 1:  # Long
            if position.highest_price is None or current_price > position.highest_price:
                position.highest_price = current_price

                # Calculate new trailing stop (ratchet mechanism)
                new_trail = current_price - (current_atr * trail_mult)

                # Only move stop up (ratchet - never move down)
                if new_trail > position.trailing_stop_price:
                    position.trailing_stop_price = new_trail

        else:  # Short
            if position.lowest_price is None or current_price < position.lowest_price:
                position.lowest_price = current_price

                # Calculate new trailing stop
                new_trail = current_price + (current_atr * trail_mult)

                # Only move stop down
                if new_trail < position.trailing_stop_price:
                    position.trailing_stop_price = new_trail

        # Check gain-locking: lock >50% gains
        if position.direction == 1 and position.highest_price:
            gain_pct = (position.highest_price - position.entry_price) / position.entry_price
            if gain_pct > 0:
                min_stop = position.entry_price + (position.entry_price * gain_pct * lock_pct)
                if position.trailing_stop_price < min_stop:
                    position.trailing_stop_price = min_stop

        elif position.direction == -1 and position.lowest_price:
            gain_pct = (position.entry_price - position.lowest_price) / position.entry_price
            if gain_pct > 0:
                max_stop = position.entry_price - (position.entry_price * gain_pct * lock_pct)
                if position.trailing_stop_price > max_stop:
                    position.trailing_stop_price = max_stop

        # Check if trailing stop hit
        trail_hit = False
        if position.direction == 1:
            trail_hit = current_price <= position.trailing_stop_price
        else:
            trail_hit = current_price >= position.trailing_stop_price

        if trail_hit:
            pnl = position.direction * (current_price - position.entry_price) * position.remaining_quantity
            return ExitSignal(
                exit_type=ExitType.TRAILING_STOP,
                timestamp=timestamp,
                price=current_price,
                quantity=position.remaining_quantity,
                reason=f"Trailing stop hit at {position.trailing_stop_price:.4f}",
                pnl=pnl,
                exit_percentage=100.0
            )

        return None

    def check_partial_profit(
        self,
        symbol: str,
        current_price: float,
        current_atr: float,
        timestamp: datetime
    ) -> Optional[ExitSignal]:
        """
        Check if partial profit level should be taken

        Args:
            symbol: Position symbol
            current_price: Current market price
            current_atr: Current ATR value for calculating profit levels
            timestamp: Current timestamp

        Returns:
            ExitSignal for partial exit if level hit, None otherwise
        """
        if symbol not in self.positions:
            return None

        position = self.positions[symbol]

        if position.is_closed or position.remaining_quantity <= 0:
            return None

        params = self.params[position.asset_class]
        partial_levels = params["partial_tp_levels"]

        for atr_mult, exit_pct in partial_levels:
            # Skip if this level already hit
            if atr_mult in self.partial_levels_hit.get(symbol, []):
                continue

            # Calculate profit target for this level
            if position.direction == 1:  # Long
                target_price = position.entry_price + (current_atr * atr_mult)
                level_hit = current_price >= target_price
            else:  # Short
                target_price = position.entry_price - (current_atr * atr_mult)
                level_hit = current_price <= target_price

            if level_hit:
                # Mark level as hit
                if symbol not in self.partial_levels_hit:
                    self.partial_levels_hit[symbol] = []
                self.partial_levels_hit[symbol].append(atr_mult)

                # Calculate quantity to exit
                exit_quantity = position.remaining_quantity * exit_pct

                # Update remaining quantity
                position.remaining_quantity -= exit_quantity

                # Calculate P&L for this partial exit
                pnl = position.direction * (current_price - position.entry_price) * exit_quantity

                return ExitSignal(
                    exit_type=ExitType.PARTIAL_PROFIT,
                    timestamp=timestamp,
                    price=current_price,
                    quantity=exit_quantity,
                    reason=f"Partial profit at {atr_mult}x ATR ({exit_pct*100:.0f}% of position)",
                    pnl=pnl,
                    exit_percentage=exit_pct * 100
                )

        return None

    def check_time_exit(self, symbol: str, current_time: datetime) -> Optional[ExitSignal]:
        """
        Check if position should be exited due to time limit

        Args:
            symbol: Position symbol
            current_time: Current timestamp

        Returns:
            ExitSignal if time limit exceeded, None otherwise
        """
        if symbol not in self.positions:
            return None

        position = self.positions[symbol]

        if position.is_closed or position.remaining_quantity <= 0:
            return None

        params = self.params[position.asset_class]
        max_hold_days = params["max_hold_days"]

        hold_duration = current_time - position.entry_time

        if hold_duration.days >= max_hold_days:
            current_price = position.entry_price
            pnl = 0
            return ExitSignal(
                exit_type=ExitType.TIME_EXIT,
                timestamp=current_time,
                price=current_price,
                quantity=position.remaining_quantity,
                reason=f"Time exit: held for {hold_duration.days} days (max: {max_hold_days})",
                pnl=pnl,
                exit_percentage=100.0
            )

        return None

    def check_breakeven(
        self,
        symbol: str,
        current_price: float,
        current_atr: float
    ) -> bool:
        """
        Check if position should be moved to breakeven

        Returns True if stop was moved to breakeven
        """
        if symbol not in self.positions:
            return False

        position = self.positions[symbol]

        if position.is_closed:
            return False

        params = self.params[position.asset_class]
        be_mult = params["breakeven_atr_mult"]

        # Calculate breakeven trigger level
        if position.direction == 1:  # Long
            be_trigger = position.entry_price + (current_atr * be_mult)
            if current_price >= be_trigger:
                # Move stop to breakeven (entry price + small buffer)
                new_stop = position.entry_price * 1.001  # Small profit buffer
                if position.initial_stop_price < new_stop:
                    position.initial_stop_price = new_stop
                    return True
        else:  # Short
            be_trigger = position.entry_price - (current_atr * be_mult)
            if current_price <= be_trigger:
                new_stop = position.entry_price * 0.999
                if position.initial_stop_price > new_stop:
                    position.initial_stop_price = new_stop
                    return True

        return False

    def process_bar(
        self,
        symbol: str,
        bar: Dict,
        prices_df: pd.DataFrame,
        vix_value: Optional[float] = None
    ) -> List[ExitSignal]:
        """
        Process a new price bar and check all exit conditions

        Args:
            symbol: Position symbol
            bar: Current OHLCV bar {"open", "high", "low", "close", "volume", "timestamp"}
            prices_df: DataFrame with recent price history for ATR calculation
            vix_value: Optional VIX value

        Returns:
            List of ExitSignals (can be multiple for partial exits)
        """
        if symbol not in self.positions:
            return []

        position = self.positions[symbol]

        if position.is_closed:
            return []

        signals = []

        # Update volatility regime
        current_atr = self.calculate_atr(prices_df)
        if self.use_volatility_regime:
            self.regime_detector.detect_regime(current_atr, bar["timestamp"], vix_value)

        # Check breakeven first
        self.check_breakeven(symbol, bar["close"], current_atr)

        # Check partial profits (before full exits)
        partial_signal = self.check_partial_profit(symbol, bar["close"], current_atr, bar["timestamp"])
        if partial_signal:
            signals.append(partial_signal)
            position.partial_exits.append(partial_signal)

        # Check initial stop
        stop_signal = self.check_initial_stop(symbol, bar["low"] if position.direction == 1 else bar["high"], bar["timestamp"])
        if stop_signal:
            signals.append(stop_signal)
            position.is_closed = True
            return signals

        # Check take profit
        tp_signal = self.check_take_profit(symbol, bar["high"] if position.direction == 1 else bar["low"], bar["timestamp"])
        if tp_signal:
            signals.append(tp_signal)
            position.is_closed = True
            return signals

        # Update and check trailing stop
        trail_signal = self.update_trailing_stop(symbol, bar["close"], current_atr, bar["timestamp"])
        if trail_signal:
            signals.append(trail_signal)
            position.is_closed = True
            return signals

        # Check time exit
        time_signal = self.check_time_exit(symbol, bar["timestamp"])
        if time_signal:
            time_signal.price = bar["close"]  # Update with actual price
            time_signal.pnl = position.direction * (bar["close"] - position.entry_price) * position.remaining_quantity
            signals.append(time_signal)
            position.is_closed = True
            return signals

        return signals

    def get_position_status(self, symbol: str, current_price: float) -> Dict:
        """Get current position status and exit levels"""
        if symbol not in self.positions:
            return {}

        position = self.positions[symbol]

        unrealized_pnl = position.direction * (current_price - position.entry_price) * position.remaining_quantity
        pnl_pct = (current_price - position.entry_price) / position.entry_price * 100 * position.direction

        return {
            "symbol": symbol,
            "entry_price": position.entry_price,
            "current_price": current_price,
            "remaining_quantity": position.remaining_quantity,
            "unrealized_pnl": unrealized_pnl,
            "pnl_pct": pnl_pct,
            "initial_stop": position.initial_stop_price,
            "take_profit": position.take_profit_price,
            "trailing_stop": position.trailing_stop_price,
            "highest_price": position.highest_price,
            "lowest_price": position.lowest_price,
            "partial_exits": len(position.partial_exits),
            "is_closed": position.is_closed
        }

    def close_position(self, symbol: str, current_price: float, timestamp: datetime, reason: str = "manual") -> Optional[ExitSignal]:
        """Manually close a position"""
        if symbol not in self.positions:
            return None

        position = self.positions[symbol]

        if position.is_closed:
            return None

        pnl = position.direction * (current_price - position.entry_price) * position.remaining_quantity

        signal = ExitSignal(
            exit_type=ExitType.TAKE_PROFIT,  # Generic exit type
            timestamp=timestamp,
            price=current_price,
            quantity=position.remaining_quantity,
            reason=f"Manual close: {reason}",
            pnl=pnl,
            exit_percentage=100.0
        )

        position.is_closed = True
        position.remaining_quantity = 0

        return signal


# ============================================================================
# BACKTESTER CLASS
# ============================================================================

class ExitBacktester:
    """
    Backtesting framework for exit strategy optimization
    """

    def __init__(self, exit_manager: ExitManager):
        self.exit_manager = exit_manager
        self.results = []

    def run_backtest(
        self,
        trades: List[Dict],
        price_data: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Run backtest on historical trades

        Args:
            trades: List of trade dicts with "symbol", "entry_time", "entry_price", etc.
            price_data: Dict mapping symbols to OHLCV DataFrames

        Returns:
            DataFrame with backtest results
        """
        results = []

        for trade in trades:
            symbol = trade["symbol"]
            asset_class = trade["asset_class"]

            if symbol not in price_data:
                continue

            df = price_data[symbol]
            entry_time = trade["entry_time"]

            # Find entry index
            entry_idx = df[df["timestamp"] >= entry_time].index[0]

            # Get ATR window before entry
            atr_start = max(0, entry_idx - 28)
            atr_window = df.iloc[atr_start:entry_idx]

            # Initialize position
            position = self.exit_manager.initialize_position(
                symbol=symbol,
                asset_class=asset_class,
                entry_price=trade["entry_price"],
                entry_time=entry_time,
                quantity=trade["quantity"],
                direction=trade["direction"],
                prices_df=atr_window,
                vix_value=trade.get("vix_value")
            )

            # Simulate trade
            trade_result = self._simulate_trade(position, df, entry_idx)
            results.append(trade_result)

        return pd.DataFrame(results)

    def _simulate_trade(
        self,
        position: Position,
        df: pd.DataFrame,
        entry_idx: int
    ) -> Dict:
        """Simulate a single trade through completion"""
        symbol = position.symbol

        exit_signals = []

        for i in range(entry_idx, len(df)):
            bar = df.iloc[i]

            # Get price history for ATR
            history_start = max(0, i - 27)
            prices_df = df.iloc[history_start:i+1]

            bar_dict = {
                "timestamp": bar["timestamp"],
                "open": bar["open"],
                "high": bar["high"],
                "low": bar["low"],
                "close": bar["close"],
                "volume": bar["volume"]
            }

            signals = self.exit_manager.process_bar(symbol, bar_dict, prices_df)

            if signals:
                exit_signals.extend(signals)

                # Check if position closed
                if any(s.exit_type in [ExitType.INITIAL_STOP, ExitType.TAKE_PROFIT,
                                       ExitType.TRAILING_STOP, ExitType.TIME_EXIT] 
                       for s in signals):
                    break

        # Calculate trade metrics
        total_pnl = sum(s.pnl for s in exit_signals if s.pnl is not None)

        # Determine exit type
        final_exit = None
        for s in reversed(exit_signals):
            if s.exit_type in [ExitType.INITIAL_STOP, ExitType.TAKE_PROFIT,
                              ExitType.TRAILING_STOP, ExitType.TIME_EXIT]:
                final_exit = s.exit_type
                break

        hold_bars = i - entry_idx + 1

        return {
            "symbol": symbol,
            "entry_price": position.entry_price,
            "exit_price": exit_signals[-1].price if exit_signals else df.iloc[i]["close"],
            "total_pnl": total_pnl,
            "exit_type": final_exit.value if final_exit else "open",
            "hold_bars": hold_bars,
            "num_partial_exits": len([s for s in exit_signals if s.exit_type == ExitType.PARTIAL_PROFIT]),
            "max_unrealized_pnl": 0,
        }

    def optimize_parameters(
        self,
        trades: List[Dict],
        price_data: Dict[str, pd.DataFrame],
        param_grid: Dict
    ) -> pd.DataFrame:
        """
        Grid search parameter optimization

        Args:
            trades: List of historical trades
            price_data: Dict of price DataFrames
            param_grid: Dict of parameter ranges to test
                e.g., {"sl_atr_mult": [0.5, 1.0, 1.5], "tp_atr_mult": [1.5, 2.0, 2.5]}

        Returns:
            DataFrame with optimization results
        """
        from itertools import product

        results = []

        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())

        for combo in product(*param_values):
            params = dict(zip(param_names, combo))

            # Create exit manager with these parameters
            custom_params = {AssetClass.COMMODITY_FUTURES: params}
            em = ExitManager(atr_period=14, custom_params=custom_params)

            backtester = ExitBacktester(em)
            result_df = backtester.run_backtest(trades, price_data)

            # Calculate metrics
            total_pnl = result_df["total_pnl"].sum()
            win_rate = (result_df["total_pnl"] > 0).mean()
            avg_pnl = result_df["total_pnl"].mean()

            result = {
                **params,
                "total_pnl": total_pnl,
                "win_rate": win_rate,
                "avg_pnl": avg_pnl,
                "num_trades": len(result_df)
            }
            results.append(result)

        return pd.DataFrame(results).sort_values("total_pnl", ascending=False)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "ExitManager",
    "ExitBacktester", 
    "VolatilityRegimeDetector",
    "ExitType",
    "VolatilityRegime",
    "AssetClass",
    "ExitSignal",
    "Position"
]
