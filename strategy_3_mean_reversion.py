"""
STRATEGY 3: MEAN REVERSION - VOLUMETRIC LIQUIDITY (u/DevFuturesTrader)
Based on: ES/NQ futures mean reversion using anchored VWAP and CVD divergence

Key Principles:
- Trade volumetric liquidity zones (not S/R lines)
- Price outside 2SD of anchored VWAP = outlier territory
- CVD divergence indicates passive absorption
- Entry on 5-min candle close back inside zone
- Target session VWAP first, then opposing 1st std band
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
from enum import Enum


class TradeDirection(Enum):
    LONG = "long"
    SHORT = "short"


@dataclass
class MeanReversionTrade:
    entry_time: pd.Timestamp
    direction: TradeDirection
    entry_price: float
    stop_loss: float
    target_1: float  # Session VWAP
    target_2: float  # Opposing 1st std band
    vwap_2sd: float  # Entry reference
    cvd_divergence: bool
    volume_profile_zone: str  # LVN or HVN
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    pnl_ticks: Optional[float] = None
    exit_reason: Optional[str] = None  # 'target1', 'target2', 'stop', 'manual'


class VolumetricMeanReversion:
    """
    Mean Reversion Strategy using Volumetric Analysis
    
    Parameters:
    -----------
    vwap_std_threshold : float
        Standard deviation threshold for outlier detection (default 2.0)
    session_start : str
        Time when new session starts (default '09:30' for US equities)
    timeframe : str
        Trading timeframe (default '5min')
    tick_size : float
        Minimum tick size for the instrument
    point_value : float
        Dollar value per point
    """
    
    def __init__(
        self,
        vwap_std_threshold: float = 2.0,
        session_start: str = '09:30',
        timeframe: str = '5min',
        tick_size: float = 0.25,  # ES tick size
        point_value: float = 50.0,  # ES point value
        max_hold_bars: int = 20
    ):
        self.vwap_std_threshold = vwap_std_threshold
        self.session_start = session_start
        self.timeframe = timeframe
        self.tick_size = tick_size
        self.point_value = point_value
        self.max_hold_bars = max_hold_bars
        self.trades: List[MeanReversionTrade] = []
        
    def calculate_vwap(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Volume-Weighted Average Price (VWAP)
        Resets at session start
        """
        df = df.copy()
        
        # Identify new sessions
        df['Time'] = df.index.time
        session_start_time = pd.to_datetime(self.session_start).time()
        
        # Create session groups
        df['New_Session'] = df['Time'] == session_start_time
        df['Session_ID'] = df['New_Session'].cumsum()
        
        # Calculate VWAP for each session
        df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['TP_Volume'] = df['Typical_Price'] * df['Volume']
        
        # Group by session and calculate cumulative values
        vwap_values = []
        std_values = []
        
        for session_id, group in df.groupby('Session_ID'):
            cum_tp_vol = group['TP_Volume'].cumsum()
            cum_vol = group['Volume'].cumsum()
            vwap = cum_tp_vol / cum_vol
            
            # Calculate standard deviation bands
            # Simplified: using rolling std of typical price
            std = group['Typical_Price'].expanding().std()
            
            vwap_values.extend(vwap.values)
            std_values.extend(std.values)
        
        df['VWAP'] = vwap_values
        df['VWAP_STD'] = std_values
        df['VWAP_1st_Std_Up'] = df['VWAP'] + df['VWAP_STD']
        df['VWAP_1st_Std_Down'] = df['VWAP'] - df['VWAP_STD']
        df['VWAP_2nd_Std_Up'] = df['VWAP'] + (2 * df['VWAP_STD'])
        df['VWAP_2nd_Std_Down'] = df['VWAP'] - (2 * df['VWAP_STD'])
        
        return df
    
    def calculate_cvd(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Cumulative Volume Delta (CVD)
        Estimates buying vs selling pressure
        """
        df = df.copy()
        
        # Estimate volume delta using close position in range
        # Close near high = more buying, close near low = more selling
        range_size = df['High'] - df['Low']
        close_position = (df['Close'] - df['Low']) / range_size
        
        # Volume delta estimate
        df['Volume_Delta'] = (2 * close_position - 1) * df['Volume']
        df['CVD'] = df['Volume_Delta'].cumsum()
        
        return df
    
    def identify_volume_profile_zones(
        self, 
        df: pd.DataFrame, 
        lookback: int = 20
    ) -> pd.DataFrame:
        """
        Identify Low Volume Nodes (LVN) and High Volume Nodes (HVN)
        Simplified implementation using price levels
        """
        df = df.copy()
        
        # Create price bins
        df['Price_Bin'] = pd.cut(df['Close'], bins=lookback)
        
        # Calculate volume at each price level (simplified)
        # In practice, this requires tick data or volume profile analysis
        df['Volume_Profile_Zone'] = 'normal'
        
        # Mark potential LVN areas (low volume after consolidation)
        df['Volume_MA'] = df['Volume'].rolling(lookback).mean()
        df['Is_LVN'] = df['Volume'] < df['Volume_MA'] * 0.5
        
        return df
    
    def detect_cvd_divergence(
        self, 
        df: pd.DataFrame, 
        lookback: int = 3
    ) -> pd.DataFrame:
        """
        Detect CVD divergence
        Bullish: Price makes new low, CVD makes higher low (absorption)
        Bearish: Price makes new high, CVD makes lower high (distribution)
        """
        df = df.copy()
        
        # Price direction
        df['Price_Low_Change'] = df['Low'].diff(lookback)
        df['Price_High_Change'] = df['High'].diff(lookback)
        
        # CVD direction
        df['CVD_Change'] = df['CVD'].diff(lookback)
        
        # Bullish divergence: Lower price low, higher CVD low
        df['Bullish_Divergence'] = (
            (df['Price_Low_Change'] < 0) &  # Price made lower low
            (df['CVD_Change'] > 0)  # CVD made higher low
        )
        
        # Bearish divergence: Higher price high, lower CVD high
        df['Bearish_Divergence'] = (
            (df['Price_High_Change'] > 0) &  # Price made higher high
            (df['CVD_Change'] < 0)  # CVD made lower high
        )
        
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate mean reversion signals
        """
        # Calculate all indicators
        df = self.calculate_vwap(df)
        df = self.calculate_cvd(df)
        df = self.identify_volume_profile_zones(df)
        df = self.detect_cvd_divergence(df)
        
        # LONG Signal conditions:
        # 1. Price below 2nd std down (outlier)
        # 2. Bullish CVD divergence (absorption)
        # 3. Close back inside the 2nd std band
        df['Long_Setup'] = (
            (df['Low'] < df['VWAP_2nd_Std_Down']) &  # Hit outlier territory
            (df['Bullish_Divergence'])  # CVD divergence
        )
        
        df['Long_Signal'] = (
            df['Long_Setup'].shift(1) &  # Setup on previous bar
            (df['Close'] > df['VWAP_2nd_Std_Down'])  # Close back inside
        )
        
        # SHORT Signal conditions:
        # 1. Price above 2nd std up (outlier)
        # 2. Bearish CVD divergence (distribution)
        # 3. Close back inside the 2nd std band
        df['Short_Setup'] = (
            (df['High'] > df['VWAP_2nd_Std_Up']) &  # Hit outlier territory
            (df['Bearish_Divergence'])  # CVD divergence
        )
        
        df['Short_Signal'] = (
            df['Short_Setup'].shift(1) &  # Setup on previous bar
            (df['Close'] < df['VWAP_2nd_Std_Up'])  # Close back inside
        )
        
        return df
    
    def calculate_targets(
        self, 
        row: pd.Series, 
        direction: TradeDirection
    ) -> Tuple[float, float, float]:
        """
        Calculate stop loss and targets
        
        Returns:
        --------
        (stop_loss, target_1, target_2)
        """
        if direction == TradeDirection.LONG:
            # Stop below the absorption wick (2nd std down)
            stop_loss = row['VWAP_2nd_Std_Down'] - self.tick_size
            # Target 1: Session VWAP (the mean)
            target_1 = row['VWAP']
            # Target 2: Opposing 1st std band
            target_2 = row['VWAP_1st_Std_Up']
        else:
            # Stop above the absorption wick (2nd std up)
            stop_loss = row['VWAP_2nd_Std_Up'] + self.tick_size
            # Target 1: Session VWAP (the mean)
            target_1 = row['VWAP']
            # Target 2: Opposing 1st std band
            target_2 = row['VWAP_1st_Std_Down']
        
        return stop_loss, target_1, target_2
    
    def backtest(
        self, 
        df: pd.DataFrame, 
        initial_balance: float = 50000,
        contracts_per_trade: int = 1
    ) -> pd.DataFrame:
        """
        Backtest the mean reversion strategy
        """
        df = self.generate_signals(df)
        
        balance = initial_balance
        equity_curve = []
        open_trade: Optional[MeanReversionTrade] = None
        bars_in_trade = 0
        
        for i, (time, row) in enumerate(df.iterrows()):
            # Manage open trade
            if open_trade:
                bars_in_trade += 1
                exit_triggered = False
                exit_price = None
                exit_reason = None
                
                if open_trade.direction == TradeDirection.LONG:
                    # Check stop loss
                    if row['Low'] <= open_trade.stop_loss:
                        exit_price = open_trade.stop_loss
                        exit_reason = 'stop'
                        exit_triggered = True
                    # Check target 1 (VWAP)
                    elif row['High'] >= open_trade.target_1 and bars_in_trade > 1:
                        exit_price = open_trade.target_1
                        exit_reason = 'target1'
                        exit_triggered = True
                    # Check target 2 (1st std)
                    elif row['High'] >= open_trade.target_2:
                        exit_price = open_trade.target_2
                        exit_reason = 'target2'
                        exit_triggered = True
                    # Max hold time
                    elif bars_in_trade >= self.max_hold_bars:
                        exit_price = row['Close']
                        exit_reason = 'time'
                        exit_triggered = True
                
                else:  # SHORT
                    # Check stop loss
                    if row['High'] >= open_trade.stop_loss:
                        exit_price = open_trade.stop_loss
                        exit_reason = 'stop'
                        exit_triggered = True
                    # Check target 1 (VWAP)
                    elif row['Low'] <= open_trade.target_1 and bars_in_trade > 1:
                        exit_price = open_trade.target_1
                        exit_reason = 'target1'
                        exit_triggered = True
                    # Check target 2 (1st std)
                    elif row['Low'] <= open_trade.target_2:
                        exit_price = open_trade.target_2
                        exit_reason = 'target2'
                        exit_triggered = True
                    # Max hold time
                    elif bars_in_trade >= self.max_hold_bars:
                        exit_price = row['Close']
                        exit_reason = 'time'
                        exit_triggered = True
                
                if exit_triggered:
                    # Calculate P&L
                    if open_trade.direction == TradeDirection.LONG:
                        pnl_ticks = (exit_price - open_trade.entry_price) / self.tick_size
                    else:
                        pnl_ticks = (open_trade.entry_price - exit_price) / self.tick_size
                    
                    pnl_dollars = pnl_ticks * self.tick_size * self.point_value * contracts_per_trade
                    
                    open_trade.exit_time = time
                    open_trade.exit_price = exit_price
                    open_trade.pnl_ticks = pnl_ticks
                    open_trade.exit_reason = exit_reason
                    
                    balance += pnl_dollars
                    self.trades.append(open_trade)
                    open_trade = None
                    bars_in_trade = 0
            
            # Check for new entry
            if open_trade is None:
                if row['Long_Signal']:
                    stop, t1, t2 = self.calculate_targets(row, TradeDirection.LONG)
                    
                    open_trade = MeanReversionTrade(
                        entry_time=time,
                        direction=TradeDirection.LONG,
                        entry_price=row['Close'],
                        stop_loss=stop,
                        target_1=t1,
                        target_2=t2,
                        vwap_2sd=row['VWAP_2nd_Std_Down'],
                        cvd_divergence=row['Bullish_Divergence'],
                        volume_profile_zone='LVN' if row['Is_LVN'] else 'normal'
                    )
                    bars_in_trade = 0
                    
                elif row['Short_Signal']:
                    stop, t1, t2 = self.calculate_targets(row, TradeDirection.SHORT)
                    
                    open_trade = MeanReversionTrade(
                        entry_time=time,
                        direction=TradeDirection.SHORT,
                        entry_price=row['Close'],
                        stop_loss=stop,
                        target_1=t1,
                        target_2=t2,
                        vwap_2sd=row['VWAP_2nd_Std_Up'],
                        cvd_divergence=row['Bearish_Divergence'],
                        volume_profile_zone='LVN' if row['Is_LVN'] else 'normal'
                    )
                    bars_in_trade = 0
            
            equity_curve.append({
                'Time': time,
                'Balance': balance,
                'VWAP': row['VWAP'],
                'Close': row['Close'],
                'In_Trade': open_trade is not None
            })
        
        return pd.DataFrame(equity_curve).set_index('Time')
    
    def get_performance_metrics(self) -> Dict:
        """Calculate performance metrics"""
        if not self.trades:
            return {}
        
        closed_trades = [t for t in self.trades if t.exit_reason]
        if not closed_trades:
            return {}
        
        pnls = [t.pnl_ticks for t in closed_trades if t.pnl_ticks is not None]
        winning_trades = [p for p in pnls if p > 0]
        losing_trades = [p for p in pnls if p < 0]
        
        # Calculate R-multiples (profit relative to risk)
        # Assuming ~8 tick risk for ES
        risk_ticks = 8
        r_multiples = [p / risk_ticks for p in pnls]
        
        return {
            'Total_Trades': len(closed_trades),
            'Winning_Trades': len(winning_trades),
            'Losing_Trades': len(losing_trades),
            'Win_Rate': len(winning_trades) / len(closed_trades) if closed_trades else 0,
            'Total_Ticks': sum(pnls),
            'Avg_Win_Ticks': np.mean(winning_trades) if winning_trades else 0,
            'Avg_Loss_Ticks': np.mean(losing_trades) if losing_trades else 0,
            'Profit_Factor': abs(sum(winning_trades) / sum(losing_trades)) if losing_trades and sum(losing_trades) != 0 else float('inf'),
            'Avg_R_Multiple': np.mean(r_multiples) if r_multiples else 0,
            'Target1_Exits': len([t for t in closed_trades if t.exit_reason == 'target1']),
            'Target2_Exits': len([t for t in closed_trades if t.exit_reason == 'target2']),
            'Stop_Exits': len([t for t in closed_trades if t.exit_reason == 'stop']),
        }


def create_sample_futures_data(
    periods: int = 1000,
    freq: str = '5min'
) -> pd.DataFrame:
    """
    Create sample futures data for testing
    """
    np.random.seed(42)
    
    # Generate timestamps
    index = pd.date_range(
        start='2024-01-01 09:30', 
        periods=periods, 
        freq=freq
    )
    
    # Generate price with trend and mean reversion
    returns = np.random.normal(0.0001, 0.001, periods)
    
    # Add some mean reversion behavior
    for i in range(10, periods):
        if i % 50 < 10:  # Every ~50 bars, create a mean reversion opportunity
            returns[i] = -returns[i-5:i].sum() * 0.3  # Partial reversion
    
    close = 4500 * np.exp(np.cumsum(returns))
    
    # Generate OHLC
    high = close * (1 + np.abs(np.random.normal(0, 0.001, periods)))
    low = close * (1 - np.abs(np.random.normal(0, 0.001, periods)))
    open_price = close * (1 + np.random.normal(0, 0.0005, periods))
    
    # Volume
    volume = np.random.randint(1000, 10000, periods)
    
    df = pd.DataFrame({
        'Open': open_price,
        'High': high,
        'Low': low,
        'Close': close,
        'Volume': volume
    }, index=index)
    
    return df


if __name__ == "__main__":
    print("=" * 70)
    print("VOLUMETRIC MEAN REVERSION STRATEGY - ES/NQ Futures")
    print("=" * 70)
    
    strategy = VolumetricMeanReversion(
        vwap_std_threshold=2.0,
        tick_size=0.25,
        point_value=50.0,
        max_hold_bars=20
    )
    
    print("\nStrategy Parameters:")
    print(f"  VWAP Std Threshold: {strategy.vwap_std_threshold} SD")
    print(f"  Session Start: {strategy.session_start}")
    print(f"  Tick Size: ${strategy.tick_size}")
    print(f"  Point Value: ${strategy.point_value}")
    print(f"  Max Hold Bars: {strategy.max_hold_bars}")
    
    print("\nGenerating sample futures data...")
    data = create_sample_futures_data(periods=2000)
    print(f"Data shape: {data.shape}")
    print(f"Price range: ${data['Close'].min():.2f} - ${data['Close'].max():.2f}")
    
    print("\nRunning backtest...")
    equity = strategy.backtest(data, initial_balance=50000, contracts_per_trade=1)
    
    metrics = strategy.get_performance_metrics()
    
    print("\n" + "=" * 70)
    print("BACKTEST RESULTS")
    print("=" * 70)
    
    if metrics:
        for key, value in metrics.items():
            if isinstance(value, float):
                if 'Rate' in key:
                    print(f"  {key}: {value:.2%}")
                elif 'Ticks' in key:
                    print(f"  {key}: {value:.1f} ticks")
                else:
                    print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
        
        # Calculate dollar P&L
        total_ticks = metrics.get('Total_Ticks', 0)
        dollar_pnl = total_ticks * strategy.tick_size * strategy.point_value
        print(f"\n  Total P&L: ${dollar_pnl:,.2f}")
        print(f"  Final Balance: ${equity['Balance'].iloc[-1]:,.2f}")
        
        # Per trade stats
        if metrics['Total_Trades'] > 0:
            pnl_per_trade = dollar_pnl / metrics['Total_Trades']
            print(f"  Avg P&L per Trade: ${pnl_per_trade:.2f}")
    else:
        print("  No trades generated in backtest period")
    
    print("\n" + "=" * 70)
    print("NOTE: This is a simplified implementation.")
    print("Real implementation requires:")
    print("  - Tick-level data for accurate volume profile")
    print("  - Real-time CVD calculation from order flow")
    print("  - Multi-timeframe LVN/HVN analysis")
    print("  - Custom OB calculations with volumetric data")
    print("=" * 70)
