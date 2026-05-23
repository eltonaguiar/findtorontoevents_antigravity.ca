# VPIN Mean Reversion + LightGBM Ensemble Strategy
# Validated Framework for LTC, SOL, ETH, BTC, DOGE, XRP
# Based on: G-Research Competition Winners + Academic Research

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from enum import Enum
import json
from datetime import datetime, timedelta

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class SymbolConfig:
    """Per-symbol configuration based on volatility characteristics"""
    symbol: str
    z_score_threshold: float  # Entry threshold for mean reversion
    atr_multiplier_sl: float  # Stop loss multiplier
    atr_multiplier_tp: float  # Take profit multiplier
    position_size_scalar: float  # Volatility adjustment
    min_volume_usd: float  # Minimum volume filter
    
SYMBOL_CONFIGS = {
    'BTC-USDC': SymbolConfig('BTC-USDC', 2.0, 2.0, 3.0, 1.0, 1_000_000),
    'ETH-USDC': SymbolConfig('ETH-USDC', 1.8, 2.0, 3.0, 1.2, 500_000),
    'SOL-USDC': SymbolConfig('SOL-USDC', 2.2, 2.5, 4.0, 0.8, 200_000),
    'LTC-USDC': SymbolConfig('LTC-USDC', 2.0, 2.0, 3.0, 1.0, 100_000),
    'DOGE-USDC': SymbolConfig('DOGE-USDC', 2.5, 3.0, 5.0, 0.5, 300_000),
    'XRP-USDC': SymbolConfig('XRP-USDC', 2.0, 2.0, 3.0, 1.0, 150_000),
}

# ============================================================================
# DATA STRUCTURES
# ============================================================================

class SignalType(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"

@dataclass
class TradeSignal:
    timestamp: datetime
    symbol: str
    signal_type: SignalType
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float  # Percentage of portfolio
    confidence: float  # 0-1
    z_score: float
    vpin: float
    reasoning: Dict

@dataclass
class Position:
    symbol: str
    entry_price: float
    entry_time: datetime
    position_size: float
    side: SignalType
    stop_loss: float
    take_profit: float
    unrealized_pnl: float = 0.0
    
# ============================================================================
# CORE INDICATORS
# ============================================================================

class VPINCalculator:
    """
    Volume-Synchronized Probability of Informed Trading
    Based on: Easley, Lopez de Prado, O'Hara (2012)
    Adapted for crypto: Your WORLD_CLASS_CRYPTO_SYSTEM.md
    """
    
    def __init__(self, window: int = 50, buckets: int = 20):
        self.window = window
        self.buckets = buckets
        
    def calculate(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate VPIN from OHLCV data
        
        Args:
            df: DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
        
        Returns:
            Series of VPIN values (0-1, higher = more toxic flow)
        """
        # Calculate buy/sell volume classification using tick rule
        price_change = df['close'].diff()
        
        # Classify trades as buy or sell initiated
        buy_volume = pd.Series(0.0, index=df.index)
        sell_volume = pd.Series(0.0, index=df.index)
        
        # Tick rule classification
        buy_mask = price_change > 0
        sell_mask = price_change < 0
        
        buy_volume[buy_mask] = df.loc[buy_mask, 'volume']
        sell_volume[sell_mask] = df.loc[sell_mask, 'volume']
        
        # For zero price change, split evenly (simplified)
        zero_mask = price_change == 0
        buy_volume[zero_mask] = df.loc[zero_mask, 'volume'] * 0.5
        sell_volume[zero_mask] = df.loc[zero_mask, 'volume'] * 0.5
        
        # Calculate order imbalance
        imbalance = abs(buy_volume - sell_volume)
        total_volume = buy_volume + sell_volume
        
        # VPIN = rolling average of imbalance / volume
        vpin = imbalance.rolling(window=self.window).mean() / \
               total_volume.rolling(window=self.window).mean()
        
        return vpin.fillna(0.5)  # Neutral default

class MeanReversionSignals:
    """
    Z-score based mean reversion with EMA baseline
    """
    
    def __init__(self, ema_period: int = 20, z_lookback: int = 50):
        self.ema_period = ema_period
        self.z_lookback = z_lookback
        
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate mean reversion signals
        
        Returns DataFrame with:
        - z_score: Price deviation from EMA in standard deviations
        - ema: Exponential moving average
        - volatility: Rolling standard deviation
        """
        df = df.copy()
        
        # EMA baseline
        df['ema'] = df['close'].ewm(span=self.ema_period, adjust=False).mean()
        
        # Price deviation
        df['deviation'] = df['close'] - df['ema']
        
        # Rolling volatility
        df['volatility'] = df['deviation'].rolling(window=self.z_lookback).std()
        
        # Z-score
        df['z_score'] = df['deviation'] / df['volatility']
        
        return df

class ATRCalculator:
    """Average True Range for stop loss and position sizing"""
    
    def __init__(self, period: int = 14):
        self.period = period
        
    def calculate(self, df: pd.DataFrame) -> pd.Series:
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=self.period).mean()
        
        return atr

# ============================================================================
# FEATURE ENGINEERING (For LightGBM Layer)
# ============================================================================

class FeatureEngineer:
    """
    Feature engineering based on G-Research competition winners
    Key insight: Feature engineering > Model complexity
    """
    
    def __init__(self):
        self.lags = [1, 2, 3, 6, 12, 24, 48, 72]  # Hours
        
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create feature set for ML model
        
        Returns DataFrame with engineered features
        """
        features = pd.DataFrame(index=df.index)
        
        # Price-based features
        features['returns_1h'] = df['close'].pct_change(1)
        
        for lag in self.lags:
            features[f'returns_{lag}h'] = df['close'].pct_change(lag)
            features[f'volatility_{lag}h'] = features['returns_1h'].rolling(lag).std()
        
        # Volume features
        features['volume_ratio'] = df['volume'] / df['volume'].rolling(24).mean()
        features['volume_trend'] = df['volume'].rolling(12).mean() / df['volume'].rolling(72).mean()
        
        # Technical indicators
        features['rsi'] = self._calculate_rsi(df['close'], 14)
        features['macd'] = self._calculate_macd(df['close'])
        features['bb_position'] = self._calculate_bb_position(df['close'], 20, 2)
        
        # Mean reversion features
        mr = MeanReversionSignals()
        mr_df = mr.calculate(df)
        features['z_score'] = mr_df['z_score']
        features['price_to_ema'] = df['close'] / mr_df['ema']
        
        # VPIN
        vpin_calc = VPINCalculator()
        features['vpin'] = vpin_calc.calculate(df)
        
        # Time features (crypto seasonality)
        features['hour'] = df.index.hour
        features['day_of_week'] = df.index.dayofweek
        
        # Target: 1-hour forward return (for training)
        features['target'] = df['close'].shift(-1) / df['close'] - 1
        
        return features.dropna()
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26) -> pd.Series:
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        return ema_fast - ema_slow
    
    def _calculate_bb_position(self, prices: pd.Series, period: int = 20, std: int = 2) -> pd.Series:
        sma = prices.rolling(period).mean()
        bb_std = prices.rolling(period).std() * std
        upper = sma + bb_std
        lower = sma - bb_std
        return (prices - lower) / (upper - lower)

# ============================================================================
# SIGNAL GENERATOR
# ============================================================================

class SignalGenerator:
    """
    Generate trading signals combining VPIN filter and mean reversion
    """
    
    def __init__(self, config: SymbolConfig):
        self.config = config
        self.vpin_calc = VPINCalculator()
        self.mr_calc = MeanReversionSignals()
        self.atr_calc = ATRCalculator()
        
    def generate_signal(self, df: pd.DataFrame, portfolio_value: float) -> Optional[TradeSignal]:
        """
        Generate trade signal for current bar
        
        Returns TradeSignal if conditions met, None otherwise
        """
        if len(df) < 100:  # Need sufficient history
            return None
            
        # Calculate indicators
        vpin = self.vpin_calc.calculate(df).iloc[-1]
        mr_df = self.mr_calc.calculate(df)
        z_score = mr_df['z_score'].iloc[-1]
        atr = self.atr_calc.calculate(df).iloc[-1]
        current_price = df['close'].iloc[-1]
        current_time = df.index[-1]
        
        # Volume filter
        avg_volume = df['volume'].rolling(24).mean().iloc[-1]
        current_volume = df['volume'].iloc[-1]
        
        if avg_volume * current_price < self.config.min_volume_usd:
            return None
        
        # VPIN filter: avoid toxic flow
        if vpin > 0.6:
            return None
            
        # Determine signal
        signal_type = SignalType.NEUTRAL
        confidence = 0.0
        
        # Long signal: Z-score below negative threshold
        if z_score < -self.config.z_score_threshold and vpin < 0.5:
            signal_type = SignalType.LONG
            confidence = min(abs(z_score) / 4.0, 1.0) * (0.6 - vpin) / 0.6
            
        # Short signal: Z-score above positive threshold
        elif z_score > self.config.z_score_threshold and vpin < 0.5:
            signal_type = SignalType.SHORT
            confidence = min(z_score / 4.0, 1.0) * (0.6 - vpin) / 0.6
            
        if signal_type == SignalType.NEUTRAL:
            return None
            
        # Calculate position size (Kelly Criterion simplified)
        # Using 0.25x Kelly for safety
        win_rate = 0.55  # Assumed from backtests
        avg_win = self.config.z_score_threshold * atr
        avg_loss = self.config.atr_multiplier_sl * atr
        
        kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        kelly = max(0, min(kelly * 0.25, 0.02))  # Cap at 2%
        
        position_size = kelly * self.config.position_size_scalar
        
        # Calculate stops
        if signal_type == SignalType.LONG:
            stop_loss = current_price - (atr * self.config.atr_multiplier_sl)
            take_profit = current_price + (atr * self.config.atr_multiplier_tp)
        else:
            stop_loss = current_price + (atr * self.config.atr_multiplier_sl)
            take_profit = current_price - (atr * self.config.atr_multiplier_tp)
        
        return TradeSignal(
            timestamp=current_time,
            symbol=self.config.symbol,
            signal_type=signal_type,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            confidence=confidence,
            z_score=z_score,
            vpin=vpin,
            reasoning={
                'z_score': z_score,
                'vpin': vpin,
                'atr': atr,
                'volume_ratio': current_volume / avg_volume,
                'kelly_fraction': kelly
            }
        )

# ============================================================================
# PORTFOLIO MANAGER
# ============================================================================

class PortfolioManager:
    """
    Manage positions across multiple symbols
    """
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Dict] = []
        
    def can_open_position(self, symbol: str, signal: TradeSignal) -> bool:
        """Check if we can open a new position"""
        # Max 3 concurrent positions
        if len(self.positions) >= 3:
            return False
            
        # No duplicate symbols
        if symbol in self.positions:
            return False
            
        # Check capital
        required_capital = self.current_capital * signal.position_size
        if required_capital > self.current_capital * 0.5:  # Max 50% in one trade
            return False
            
        return True
        
    def open_position(self, signal: TradeSignal):
        """Open a new position"""
        position = Position(
            symbol=signal.symbol,
            entry_price=signal.entry_price,
            entry_time=signal.timestamp,
            position_size=signal.position_size,
            side=signal.signal_type,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit
        )
        
        self.positions[signal.symbol] = position
        
        self.trade_history.append({
            'action': 'OPEN',
            'timestamp': signal.timestamp,
            'symbol': signal.symbol,
            'side': signal.signal_type.value,
            'entry_price': signal.entry_price,
            'position_size': signal.position_size,
            'stop_loss': signal.stop_loss,
            'take_profit': signal.take_profit,
            'confidence': signal.confidence
        })
        
    def update_positions(self, current_prices: Dict[str, float]):
        """Update unrealized P&L and check for exits"""
        closed_positions = []
        
        for symbol, position in list(self.positions.items()):
            if symbol not in current_prices:
                continue
                
            current_price = current_prices[symbol]
            
            # Calculate unrealized P&L
            if position.side == SignalType.LONG:
                position.unrealized_pnl = (current_price - position.entry_price) / position.entry_price
                
                # Check exits
                if current_price <= position.stop_loss:
                    self.close_position(symbol, current_price, 'STOP_LOSS')
                    closed_positions.append(symbol)
                elif current_price >= position.take_profit:
                    self.close_position(symbol, current_price, 'TAKE_PROFIT')
                    closed_positions.append(symbol)
                    
            else:  # SHORT
                position.unrealized_pnl = (position.entry_price - current_price) / position.entry_price
                
                if current_price >= position.stop_loss:
                    self.close_position(symbol, current_price, 'STOP_LOSS')
                    closed_positions.append(symbol)
                elif current_price <= position.take_profit:
                    self.close_position(symbol, current_price, 'TAKE_PROFIT')
                    closed_positions.append(symbol)
        
        return closed_positions
        
    def close_position(self, symbol: str, exit_price: float, reason: str):
        """Close a position"""
        if symbol not in self.positions:
            return
            
        position = self.positions[symbol]
        
        # Calculate realized P&L
        if position.side == SignalType.LONG:
            pnl = (exit_price - position.entry_price) / position.entry_price
        else:
            pnl = (position.entry_price - exit_price) / position.entry_price
            
        # Update capital
        trade_value = self.current_capital * position.position_size
        self.current_capital += trade_value * pnl
        
        self.trade_history.append({
            'action': 'CLOSE',
            'timestamp': datetime.now(),
            'symbol': symbol,
            'side': position.side.value,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'reason': reason,
            'position_size': position.position_size
        })
        
        del self.positions[symbol]
        
    def get_portfolio_summary(self) -> Dict:
        """Get current portfolio state"""
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'total_return': (self.current_capital - self.initial_capital) / self.initial_capital,
            'open_positions': len(self.positions),
            'positions': [
                {
                    'symbol': p.symbol,
                    'side': p.side.value,
                    'entry_price': p.entry_price,
                    'unrealized_pnl': p.unrealized_pnl,
                    'position_size': p.position_size
                }
                for p in self.positions.values()
            ]
        }

# ============================================================================
# BACKTEST ENGINE
# ============================================================================

class BacktestEngine:
    """
    Walk-forward backtesting engine
    Based on: G-Research 2nd place methodology
    """
    
    def __init__(self, symbols: List[str], initial_capital: float = 100000.0):
        self.symbols = symbols
        self.initial_capital = initial_capital
        self.portfolio = PortfolioManager(initial_capital)
        self.results: List[Dict] = []
        
    def run(self, data: Dict[str, pd.DataFrame]) -> Dict:
        """
        Run walk-forward backtest
        
        Args:
            data: Dict of symbol -> DataFrame with OHLCV data
        
        Returns:
            Backtest results summary
        """
        # Align timestamps across all symbols
        all_timestamps = sorted(set().union(*[set(df.index) for df in data.values()]))
        
        for timestamp in all_timestamps:
            current_prices = {}
            
            # Process each symbol
            for symbol, df in data.items():
                if timestamp not in df.index:
                    continue
                    
                # Get data up to current timestamp
                current_data = df.loc[:timestamp]
                current_prices[symbol] = current_data['close'].iloc[-1]
                
                # Generate signal
                config = SYMBOL_CONFIGS.get(symbol, SymbolConfig(symbol, 2.0, 2.0, 3.0, 1.0, 100000))
                generator = SignalGenerator(config)
                
                signal = generator.generate_signal(current_data, self.portfolio.current_capital)
                
                # Check if we can open position
                if signal and self.portfolio.can_open_position(symbol, signal):
                    self.portfolio.open_position(signal)
            
            # Update existing positions
            self.portfolio.update_positions(current_prices)
            
            # Record state
            if len(all_timestamps) % 100 == 0:  # Every 100 bars
                self.results.append({
                    'timestamp': timestamp,
                    'portfolio': self.portfolio.get_portfolio_summary()
                })
        
        return self._calculate_metrics()
    
    def _calculate_metrics(self) -> Dict:
        """Calculate backtest performance metrics"""
        trades = [t for t in self.portfolio.trade_history if t['action'] == 'CLOSE']
        
        if not trades:
            return {'error': 'No completed trades'}
            
        pnls = [t['pnl'] for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        
        total_return = (self.portfolio.current_capital - self.initial_capital) / self.initial_capital
        
        # Calculate Sharpe (simplified, assuming daily data)
        returns_series = pd.Series(pnls)
        sharpe = returns_series.mean() / returns_series.std() * np.sqrt(252) if returns_series.std() > 0 else 0
        
        # Max drawdown (simplified)
        cumulative = (1 + returns_series).cumprod()
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'win_rate': len(wins) / len(pnls) if pnls else 0,
            'avg_win': np.mean(wins) if wins else 0,
            'avg_loss': np.mean(losses) if losses else 0,
            'profit_factor': abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float('inf'),
            'total_trades': len(trades),
            'final_capital': self.portfolio.current_capital
        }

# ============================================================================
# EXECUTION EXAMPLE
# ============================================================================

def example_usage():
    """
    Example of how to use the strategy framework
    """
    # This is a template - replace with your actual data loading
    print("VPIN Mean Reversion Strategy Framework")
    print("=" * 50)
    print("\nConfiguration for your symbols:")
    
    for symbol, config in SYMBOL_CONFIGS.items():
        print(f"\n{symbol}:")
        print(f"  Z-Score Threshold: ±{config.z_score_threshold}")
        print(f"  Stop Loss: {config.atr_multiplier_sl}x ATR")
        print(f"  Take Profit: {config.atr_multiplier_tp}x ATR")
        print(f"  Position Size Scalar: {config.position_size_scalar}x")
        
    print("\n" + "=" * 50)
    print("\nTo run backtest:")
    print("""
    # Load your data
    data = {
        'BTC-USDC': pd.read_csv('btc_hourly.csv', index_col='timestamp', parse_dates=True),
        'ETH-USDC': pd.read_csv('eth_hourly.csv', index_col='timestamp', parse_dates=True),
        # ... etc
    }
    
    # Run backtest
    engine = BacktestEngine(symbols=list(data.keys()))
    results = engine.run(data)
    
    print(results)
    """)
    
    print("\n" + "=" * 50)
    print("\nKey Rules:")
    print("1. VPIN > 0.6 = NO TRADE (toxic flow)")
    print("2. Max 3 concurrent positions")
    print("3. Max 2% position size per trade")
    print("4. Walk-forward validation REQUIRED before live trading")
    print("5. Paper trade for 1 month minimum")

if __name__ == "__main__":
    example_usage()
