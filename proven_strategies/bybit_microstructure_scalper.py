
"""
================================================================================
BYBIT MICROSTRUCTURE SCALPER - COMPLETE BACKTEST IMPLEMENTATION
Target: 91.67% Win Rate Replication
================================================================================

This strategy implements:
- Order Flow Imbalance (OFI) detection
- VWAP mean reversion with regime detection
- Microstructure bid-ask analysis
- Scaled profit-taking with breakeven management
- Position pyramiding

Author: Synthesized from Parallel Investigation Findings
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import warnings
warnings.filterwarnings('ignore')


# =============================================================================
# CONFIGURATION AND PARAMETERS
# =============================================================================

@dataclass
class StrategyConfig:
    """Configuration parameters for the strategy"""
    # Position Sizing
    base_position_size: float = 0.5  # BTC
    max_position_size: float = 0.6   # BTC
    min_position_size: float = 0.1   # BTC (recovery trades)
    pyramid_ratio: float = 0.5       # 50% of base for pyramids
    max_pyramids: int = 2
    leverage: float = 10.0

    # Entry Filters
    vwap_threshold: float = 0.003    # ±0.3% of VWAP
    ofi_threshold: float = 0.6       # |OFI| > 0.6 for entry
    ofi_exit_threshold: float = 0.4  # Exit if OFI reverses > 0.4
    spread_threshold: float = 0.0002 # < 0.02% spread
    volume_threshold: float = 20.0   # > 20 BTC/min
    bid_ask_ratio_long: float = 1.3  # > 1.3 for longs
    bid_ask_ratio_short: float = 0.77 # < 0.77 for shorts

    # Exit Parameters
    stop_loss_pct: float = 0.0012    # 0.12% stop loss
    tp1_pct: float = 0.0015          # 0.15% TP1
    tp2_pct: float = 0.0030          # 0.30% TP2
    tp3_pct: float = 0.0050          # 0.50% TP3
    tp4_pct: float = 0.0080          # 0.80% TP4 (runner)

    tp1_size: float = 0.40           # Close 40% at TP1
    tp2_size: float = 0.30           # Close 30% at TP2
    tp3_size: float = 0.20           # Close 20% at TP3
    tp4_size: float = 0.10           # Close 10% at TP4

    breakeven_trigger: float = 0.0015 # Move to BE at TP1
    breakeven_offset: float = 0.0002  # +0.02% above entry
    trailing_stop_pct: float = 0.0010 # 0.10% trailing after TP2

    # Timing
    funding_times: List[int] = field(default_factory=lambda: [0, 8, 16])
    funding_avoid_minutes: int = 15
    min_trade_spacing_seconds: int = 4  # For pyramids

    # Regime Detection
    adx_threshold: float = 25.0
    adx_period: int = 14
    bb_period: int = 20
    bb_std: float = 2.0

    # Risk Management
    max_daily_trades: int = 6
    max_concurrent_trades: int = 2
    cooldown_after_loss_seconds: int = 60


class TradeDirection(Enum):
    LONG = 1
    SHORT = -1
    FLAT = 0


class Regime(Enum):
    RANGE = "range"
    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    UNKNOWN = "unknown"


@dataclass
class Trade:
    """Represents a single trade"""
    entry_time: pd.Timestamp
    entry_price: float
    direction: TradeDirection
    size: float
    stop_loss: float
    take_profits: Dict[str, float]
    is_pyramid: bool = False
    parent_trade_id: Optional[int] = None

    # Runtime state
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    realized_pnl: float = 0.0
    remaining_size: float = 0.0
    highest_profit_pct: float = 0.0
    tp1_hit: bool = False
    tp2_hit: bool = False
    current_stop: float = 0.0

    def __post_init__(self):
        self.remaining_size = self.size
        self.current_stop = self.stop_loss


# =============================================================================
# TECHNICAL INDICATORS
# =============================================================================

class TechnicalIndicators:
    """Calculate all required technical indicators"""

    @staticmethod
    def vwap(df: pd.DataFrame, period: int = 60) -> pd.Series:
        """
        Calculate Volume Weighted Average Price
        Uses typical price (H+L+C)/3 * Volume
        """
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).rolling(window=period).sum() /                df['volume'].rolling(window=period).sum()
        return vwap

    @staticmethod
    def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average Directional Index"""
        high = df['high']
        low = df['low']
        close = df['close']

        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Directional Movement
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        plus_dm[plus_dm <= minus_dm] = 0
        minus_dm[minus_dm <= plus_dm] = 0

        # Smoothed values
        atr = tr.ewm(alpha=1/period, min_periods=period).mean()
        plus_di = 100 * plus_dm.ewm(alpha=1/period, min_periods=period).mean() / atr
        minus_di = 100 * minus_dm.ewm(alpha=1/period, min_periods=period).mean() / atr

        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.ewm(alpha=1/period, min_periods=period).mean()

        return adx, plus_di, minus_di

    @staticmethod
    def bollinger_bands(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = df['close'].rolling(window=period).mean()
        rolling_std = df['close'].rolling(window=period).std()
        upper = sma + (rolling_std * std)
        lower = sma - (rolling_std * std)
        return upper, sma, lower

    @staticmethod
    def order_flow_imbalance(df: pd.DataFrame, window: int = 60) -> pd.Series:
        """
        Calculate Order Flow Imbalance (OFI)

        OFI = (Aggressive Buy Volume - Aggressive Sell Volume) / Total Volume

        Aggressive Buy: Close near high (buyers lifting offers)
        Aggressive Sell: Close near low (sellers hitting bids)
        """
        # Calculate position within bar (0 = at low, 1 = at high)
        bar_position = (df['close'] - df['low']) / (df['high'] - df['low'])
        bar_position = bar_position.fillna(0.5)

        # Classify as aggressive buy/sell based on close position
        aggressive_buy = df['volume'] * bar_position
        aggressive_sell = df['volume'] * (1 - bar_position)

        # Calculate OFI over window
        ofi = (aggressive_buy.rolling(window=window).sum() - 
               aggressive_sell.rolling(window=window).sum()) /               df['volume'].rolling(window=window).sum()

        return ofi

    @staticmethod
    def bid_ask_ratio(df: pd.DataFrame, window: int = 10) -> pd.Series:
        """
        Estimate bid-ask ratio from price action
        Higher ratio = more buying pressure (more bids)
        """
        # Use close position within bar as proxy
        bar_position = (df['close'] - df['low']) / (df['high'] - df['low'])
        bar_position = bar_position.fillna(0.5)

        # Smooth it
        ratio = bar_position.rolling(window=window).mean() /                 (1 - bar_position.rolling(window=window).mean() + 1e-10)

        return ratio

    @staticmethod
    def spread_pct(df: pd.DataFrame) -> pd.Series:
        """Calculate spread as percentage of price"""
        return (df['high'] - df['low']) / df['close']


# =============================================================================
# MAIN STRATEGY CLASS
# =============================================================================

class BybitMicrostructureScalper:
    """
    Bybit Microstructure Scalper Strategy

    Implements the 91.67% win rate strategy through:
    - Order Flow Imbalance detection
    - VWAP mean reversion
    - Microstructure analysis
    - Scaled profit-taking
    """

    def __init__(self, config: StrategyConfig = None):
        self.config = config or StrategyConfig()
        self.indicators = TechnicalIndicators()

        # State tracking
        self.trades: List[Trade] = []
        self.active_trades: List[Trade] = []
        self.daily_trade_count: int = 0
        self.last_trade_time: Optional[pd.Timestamp] = None
        self.last_loss_time: Optional[pd.Timestamp] = None
        self.current_regime: Regime = Regime.UNKNOWN

        # Performance tracking
        self.equity_curve: List[float] = []
        self.daily_pnls: List[float] = []

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add all required indicators to the dataframe"""
        data = df.copy()

        # VWAP
        data['vwap'] = self.indicators.vwap(data, period=60)

        # ADX for regime detection
        data['adx'], data['plus_di'], data['minus_di'] = self.indicators.adx(data, 
                                                                              period=self.config.adx_period)

        # Bollinger Bands
        data['bb_upper'], data['bb_middle'], data['bb_lower'] = self.indicators.bollinger_bands(
            data, period=self.config.bb_period, std=self.config.bb_std)

        # Order Flow Imbalance
        data['ofi'] = self.indicators.order_flow_imbalance(data, window=60)

        # Bid-ask ratio
        data['bid_ask_ratio'] = self.indicators.bid_ask_ratio(data, window=10)

        # Spread
        data['spread_pct'] = self.indicators.spread_pct(data)

        # Volume (1-minute)
        data['volume_1min'] = data['volume']

        # Distance from VWAP
        data['vwap_distance'] = (data['close'] - data['vwap']) / data['vwap']

        return data

    def detect_regime(self, data: pd.Series) -> Regime:
        """Detect current market regime"""
        adx = data['adx']
        plus_di = data['plus_di']
        minus_di = data['minus_di']
        close = data['close']
        vwap = data['vwap']
        bb_upper = data['bb_upper']
        bb_lower = data['bb_lower']

        if pd.isna(adx):
            return Regime.UNKNOWN

        # Trend detection
        if adx > self.config.adx_threshold:
            if plus_di > minus_di and close > vwap:
                return Regime.TREND_UP
            elif minus_di > plus_di and close < vwap:
                return Regime.TREND_DOWN

        # Range detection - price between bands and ADX low
        if adx < self.config.adx_threshold:
            if bb_lower < close < bb_upper:
                return Regime.RANGE

        return Regime.UNKNOWN

    def is_funding_time(self, timestamp: pd.Timestamp) -> bool:
        """Check if current time is near funding"""
        hour = timestamp.hour
        minute = timestamp.minute

        for funding_hour in self.config.funding_times:
            # Check if within avoidance window
            if hour == funding_hour:
                return minute < self.config.funding_avoid_minutes
            elif hour == (funding_hour - 1) % 24:
                return minute >= (60 - self.config.funding_avoid_minutes)

        return False

    def check_entry_conditions(self, data: pd.Series, direction: TradeDirection) -> Tuple[bool, float]:
        """
        Check if all entry conditions are met
        Returns: (should_enter, position_size)
        """
        # Extract values
        close = data['close']
        vwap = data['vwap']
        ofi = data['ofi']
        bid_ask_ratio = data['bid_ask_ratio']
        spread_pct = data['spread_pct']
        volume = data['volume_1min']
        vwap_distance = data['vwap_distance']

        # Check for NaN values
        if any(pd.isna([close, vwap, ofi, spread_pct, volume])):
            return False, 0.0

        # 1. VWAP Filter: Within ±0.3% of VWAP
        if abs(vwap_distance) > self.config.vwap_threshold:
            return False, 0.0

        # 2. OFI Filter
        if direction == TradeDirection.LONG:
            if ofi < self.config.ofi_threshold:
                return False, 0.0
            if bid_ask_ratio < self.config.bid_ask_ratio_long:
                return False, 0.0
        else:  # SHORT
            if ofi > -self.config.ofi_threshold:
                return False, 0.0
            if bid_ask_ratio > self.config.bid_ask_ratio_short:
                return False, 0.0

        # 3. Spread Filter
        if spread_pct > self.config.spread_threshold:
            return False, 0.0

        # 4. Volume Filter
        if volume < self.config.volume_threshold:
            return False, 0.0

        # 5. Regime Filter
        if self.current_regime == Regime.UNKNOWN:
            return False, 0.0

        # For range mode: fade extremes (price away from VWAP)
        # For trend mode: only enter on pullbacks (price near VWAP)
        if self.current_regime == Regime.RANGE:
            # In range, we want some distance from VWAP to fade
            if abs(vwap_distance) < 0.001:  # Too close to VWAP
                return False, 0.0

        # Determine position size
        ofi_magnitude = abs(ofi)

        if ofi_magnitude > 0.8 and volume > 30:
            position_size = self.config.max_position_size
        elif ofi_magnitude >= 0.6:
            position_size = self.config.base_position_size
        else:
            position_size = self.config.min_position_size

        return True, position_size

    def can_enter_trade(self, timestamp: pd.Timestamp) -> bool:
        """Check if we can enter a new trade"""
        # Check daily limit
        if self.daily_trade_count >= self.config.max_daily_trades:
            return False

        # Check concurrent trades limit
        if len(self.active_trades) >= self.config.max_concurrent_trades:
            return False

        # Check funding time
        if self.is_funding_time(timestamp):
            return False

        # Check cooldown after loss
        if self.last_loss_time is not None:
            seconds_since_loss = (timestamp - self.last_loss_time).total_seconds()
            if seconds_since_loss < self.config.cooldown_after_loss_seconds:
                return False

        return True

    def enter_trade(self, timestamp: pd.Timestamp, price: float, 
                    direction: TradeDirection, size: float, 
                    is_pyramid: bool = False) -> Trade:
        """Create and enter a new trade"""

        # Calculate stop loss
        if direction == TradeDirection.LONG:
            stop_loss = price * (1 - self.config.stop_loss_pct)
        else:
            stop_loss = price * (1 + self.config.stop_loss_pct)

        # Calculate take profits
        if direction == TradeDirection.LONG:
            take_profits = {
                'tp1': price * (1 + self.config.tp1_pct),
                'tp2': price * (1 + self.config.tp2_pct),
                'tp3': price * (1 + self.config.tp3_pct),
                'tp4': price * (1 + self.config.tp4_pct)
            }
        else:
            take_profits = {
                'tp1': price * (1 - self.config.tp1_pct),
                'tp2': price * (1 - self.config.tp2_pct),
                'tp3': price * (1 - self.config.tp3_pct),
                'tp4': price * (1 - self.config.tp4_pct)
            }

        trade = Trade(
            entry_time=timestamp,
            entry_price=price,
            direction=direction,
            size=size,
            stop_loss=stop_loss,
            take_profits=take_profits,
            is_pyramid=is_pyramid
        )

        self.active_trades.append(trade)
        self.trades.append(trade)
        self.last_trade_time = timestamp
        self.daily_trade_count += 1

        return trade

    def check_pyramid_conditions(self, trade: Trade, data: pd.Series, 
                                  timestamp: pd.Timestamp) -> bool:
        """Check if we can add a pyramid position"""
        # Check minimum spacing
        if self.last_trade_time is not None:
            seconds_since_last = (timestamp - self.last_trade_time).total_seconds()
            if seconds_since_last < self.config.min_trade_spacing_seconds:
                return False

        # Check if trade is profitable
        current_price = data['close']
        if trade.direction == TradeDirection.LONG:
            profit_pct = (current_price - trade.entry_price) / trade.entry_price
            ofi = data['ofi']
            # OFI must strengthen (increase for longs)
            if profit_pct > 0 and ofi > self.config.ofi_threshold + 0.1:
                return True
        else:
            profit_pct = (trade.entry_price - current_price) / trade.entry_price
            ofi = data['ofi']
            # OFI must strengthen (decrease for shorts)
            if profit_pct > 0 and ofi < -(self.config.ofi_threshold + 0.1):
                return True

        return False

    def update_trailing_stop(self, trade: Trade, current_price: float):
        """Update trailing stop based on highest profit reached"""
        if trade.direction == TradeDirection.LONG:
            profit_pct = (current_price - trade.entry_price) / trade.entry_price
            if profit_pct > trade.highest_profit_pct:
                trade.highest_profit_pct = profit_pct
                # Update trailing stop
                new_stop = current_price * (1 - self.config.trailing_stop_pct)
                if new_stop > trade.current_stop:
                    trade.current_stop = new_stop
        else:
            profit_pct = (trade.entry_price - current_price) / trade.entry_price
            if profit_pct > trade.highest_profit_pct:
                trade.highest_profit_pct = profit_pct
                # Update trailing stop
                new_stop = current_price * (1 + self.config.trailing_stop_pct)
                if new_stop < trade.current_stop:
                    trade.current_stop = new_stop

    def manage_trade(self, trade: Trade, data: pd.Series, timestamp: pd.Timestamp) -> bool:
        """
        Manage an active trade - check exits
        Returns True if trade is closed
        """
        current_price = data['close']
        ofi = data['ofi']
        spread_pct = data['spread_pct']
        volume = data['volume_1min']

        # Calculate current profit
        if trade.direction == TradeDirection.LONG:
            profit_pct = (current_price - trade.entry_price) / trade.entry_price
        else:
            profit_pct = (trade.entry_price - current_price) / trade.entry_price

        # Check stop loss
        if trade.direction == TradeDirection.LONG:
            if current_price <= trade.current_stop:
                self.close_trade(trade, timestamp, current_price, 'STOP_LOSS')
                return True
        else:
            if current_price >= trade.current_stop:
                self.close_trade(trade, timestamp, current_price, 'STOP_LOSS')
                return True

        # Check OFI reversal exit
        if trade.direction == TradeDirection.LONG:
            if ofi < -self.config.ofi_exit_threshold:
                self.close_trade(trade, timestamp, current_price, 'OFI_REVERSAL')
                return True
        else:
            if ofi > self.config.ofi_exit_threshold:
                self.close_trade(trade, timestamp, current_price, 'OFI_REVERSAL')
                return True

        # Check spread widening
        if spread_pct > 0.0005:  # 0.05%
            self.close_trade(trade, timestamp, current_price, 'SPREAD_WIDEN')
            return True

        # Check take profits
        if not trade.tp1_hit and profit_pct >= self.config.tp1_pct:
            # Close TP1 portion
            close_size = trade.size * self.config.tp1_size
            trade.remaining_size -= close_size
            trade.tp1_hit = True
            # Move to breakeven
            trade.current_stop = trade.entry_price * (1 + self.config.breakeven_offset)                                  if trade.direction == TradeDirection.LONG                                  else trade.entry_price * (1 - self.config.breakeven_offset)

        elif trade.tp1_hit and not trade.tp2_hit and profit_pct >= self.config.tp2_pct:
            # Close TP2 portion
            close_size = trade.size * self.config.tp2_size
            trade.remaining_size -= close_size
            trade.tp2_hit = True
            # Activate trailing stop
            self.update_trailing_stop(trade, current_price)

        elif trade.tp2_hit and profit_pct >= self.config.tp3_pct:
            # Close TP3 portion
            close_size = trade.size * self.config.tp3_size
            trade.remaining_size -= close_size
            # Close remaining at TP3
            self.close_trade(trade, timestamp, current_price, 'TP3')
            return True

        # Update trailing stop if TP2 hit
        if trade.tp2_hit:
            self.update_trailing_stop(trade, current_price)

        return False

    def close_trade(self, trade: Trade, timestamp: pd.Timestamp, 
                    exit_price: float, reason: str):
        """Close a trade and calculate P&L"""
        trade.exit_time = timestamp
        trade.exit_price = exit_price
        trade.exit_reason = reason

        # Calculate P&L
        if trade.direction == TradeDirection.LONG:
            pnl_per_btc = (exit_price - trade.entry_price)
        else:
            pnl_per_btc = (trade.entry_price - exit_price)

        # P&L = Direction × (Exit - Entry) × Quantity × 10 (leverage)
        trade.realized_pnl = trade.direction.value * (exit_price - trade.entry_price) *                              trade.size * self.config.leverage

        # Track loss for cooldown
        if trade.realized_pnl < 0:
            self.last_loss_time = timestamp

        # Remove from active trades
        if trade in self.active_trades:
            self.active_trades.remove(trade)

    def run_backtest(self, df: pd.DataFrame, initial_capital: float = 100000.0) -> Dict:
        """
        Run full backtest on historical data

        Parameters:
        -----------
        df : pd.DataFrame
            Must contain columns: open, high, low, close, volume
            Index should be datetime
        initial_capital : float
            Starting capital in USD

        Returns:
        --------
        Dict containing backtest results
        """
        # Prepare data with indicators
        data = self.prepare_data(df)

        capital = initial_capital
        equity = [capital]

        for i in range(len(data)):
            if i < 60:  # Skip until indicators are valid
                continue

            row = data.iloc[i]
            timestamp = data.index[i]

            # Update regime
            self.current_regime = self.detect_regime(row)

            # Manage existing trades
            trades_to_remove = []
            for trade in self.active_trades:
                if self.manage_trade(trade, row, timestamp):
                    trades_to_remove.append(trade)

            # Check for pyramid opportunities
            for trade in self.active_trades:
                if not trade.is_pyramid and self.check_pyramid_conditions(trade, row, timestamp):
                    if self.can_enter_trade(timestamp):
                        pyramid_size = trade.size * self.config.pyramid_ratio
                        self.enter_trade(timestamp, row['close'], 
                                        trade.direction, pyramid_size, is_pyramid=True)

            # Check for new entries
            if self.can_enter_trade(timestamp):
                # Try LONG
                should_enter_long, size_long = self.check_entry_conditions(row, TradeDirection.LONG)
                if should_enter_long:
                    self.enter_trade(timestamp, row['close'], TradeDirection.LONG, size_long)
                else:
                    # Try SHORT
                    should_enter_short, size_short = self.check_entry_conditions(row, TradeDirection.SHORT)
                    if should_enter_short:
                        self.enter_trade(timestamp, row['close'], TradeDirection.SHORT, size_short)

            # Update equity
            unrealized_pnl = 0
            for trade in self.active_trades:
                if trade.direction == TradeDirection.LONG:
                    unrealized_pnl += (row['close'] - trade.entry_price) * trade.remaining_size * self.config.leverage
                else:
                    unrealized_pnl += (trade.entry_price - row['close']) * trade.remaining_size * self.config.leverage

            realized_pnl = sum(t.realized_pnl for t in self.trades if t.exit_time is not None)
            capital = initial_capital + realized_pnl + unrealized_pnl
            equity.append(capital)

        # Close any remaining trades at last price
        final_price = data['close'].iloc[-1]
        final_time = data.index[-1]
        for trade in self.active_trades:
            self.close_trade(trade, final_time, final_price, 'END_OF_DATA')

        # Calculate metrics
        closed_trades = [t for t in self.trades if t.exit_time is not None]
        winning_trades = [t for t in closed_trades if t.realized_pnl > 0]
        losing_trades = [t for t in closed_trades if t.realized_pnl <= 0]

        total_trades = len(closed_trades)
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0

        avg_win = np.mean([t.realized_pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.realized_pnl for t in losing_trades]) if losing_trades else 0

        total_profit = sum([t.realized_pnl for t in winning_trades])
        total_loss = abs(sum([t.realized_pnl for t in losing_trades]))
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')

        final_capital = initial_capital + sum(t.realized_pnl for t in closed_trades)
        total_return = (final_capital - initial_capital) / initial_capital * 100

        # Calculate max drawdown
        equity_series = pd.Series(equity)
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min() * 100

        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'total_return_pct': total_return,
            'max_drawdown_pct': max_drawdown,
            'final_capital': final_capital,
            'initial_capital': initial_capital,
            'equity_curve': equity,
            'trades': closed_trades,
            'exit_reasons': pd.Series([t.exit_reason for t in closed_trades]).value_counts().to_dict()
        }


# =============================================================================
# USAGE EXAMPLE AND BACKTEST RUNNER
# =============================================================================

def run_example_backtest():
    """Example of how to run the backtest"""

    # Create sample data (replace with real BTC data)
    np.random.seed(42)
    dates = pd.date_range(start='2024-03-24', periods=4320, freq='1min')  # 3 days

    # Generate realistic BTC price action
    returns = np.random.normal(0.00005, 0.001, len(dates))
    price = 65000 * np.exp(np.cumsum(returns))

    # Create OHLCV data
    df = pd.DataFrame({
        'open': price * (1 + np.random.normal(0, 0.0002, len(dates))),
        'high': price * (1 + abs(np.random.normal(0, 0.0005, len(dates)))),
        'low': price * (1 - abs(np.random.normal(0, 0.0005, len(dates)))),
        'close': price,
        'volume': np.random.exponential(25, len(dates))
    }, index=dates)

    # Ensure high >= max(open, close) and low <= min(open, close)
    df['high'] = df[['open', 'close', 'high']].max(axis=1)
    df['low'] = df[['open', 'close', 'low']].min(axis=1)

    # Initialize and run strategy
    config = StrategyConfig()
    strategy = BybitMicrostructureScalper(config)

    print("=" * 80)
    print("BYBIT MICROSTRUCTURE SCALPER - BACKTEST RESULTS")
    print("=" * 80)

    results = strategy.run_backtest(df, initial_capital=100000)

    print(f"\n{'METRIC':<30} {'VALUE':>20}")
    print("-" * 52)
    print(f"{'Total Trades':<30} {results['total_trades']:>20}")
    print(f"{'Winning Trades':<30} {results['winning_trades']:>20}")
    print(f"{'Losing Trades':<30} {results['losing_trades']:>20}")
    print(f"{'Win Rate (%)':<30} {results['win_rate']:>19.2f}%")
    print(f"{'Average Win ($)':<30} {results['avg_win']:>20.2f}")
    print(f"{'Average Loss ($)':<30} {results['avg_loss']:>20.2f}")
    print(f"{'Profit Factor':<30} {results['profit_factor']:>20.2f}")
    print(f"{'Total Return (%)':<30} {results['total_return_pct']:>19.2f}%")
    print(f"{'Max Drawdown (%)':<30} {results['max_drawdown_pct']:>19.2f}%")
    print(f"{'Final Capital ($)':<30} {results['final_capital']:>20.2f}")

    print(f"\n{'EXIT REASON BREAKDOWN:':}")
    for reason, count in results['exit_reasons'].items():
        print(f"  {reason}: {count}")

    return results


if __name__ == "__main__":
    results = run_example_backtest()
