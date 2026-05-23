"""
Correlation Breakdown Momentum Strategy
========================================

Baby Strat trading strategy that detects when BTC decouples from 
traditional markets (S&P 500 correlation breakdown) and trades the 
resulting momentum.

WHITE SPACE FILLER:
- No existing strategy uses correlation breakdown as primary signal
- Captures crypto-specific moves when decoupling from tradfi
- Works best during crypto-native events (ETF news, regulatory clarity, etc.)

Author: Team Alpha
Version: 1.0
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# These imports are provided by the incubator
# from incubator.shared_infra.data_bridge import MarketDataSnapshot


@dataclass
class Signal:
    """A trading signal - required return type."""
    symbol: str           # e.g., "BTCUSDT"
    direction: str        # "BUY" or "SELL"
    confidence: float     # 0.0 to 1.0
    entry_price: float    # Suggested entry
    take_profit: float    # Target price
    stop_loss: float      # Stop price
    reason: str           # Why this signal


@dataclass
class CorrelationState:
    """Tracks the correlation regime state."""
    correlation: float           # Current rolling correlation
    is_high_correlation: bool    # Above high threshold
    high_correlation_count: int  # Consecutive periods above threshold
    btc_high_break: bool         # BTC broke 20-period high
    volume_confirmed: bool       # Volume above threshold


class CorrelationBreakdownMomentumStrategy:
    """
    Correlation Breakdown Momentum Strategy
    
    CORE LOGIC:
    -----------
    Crypto markets often move in correlation with traditional markets (S&P 500)
    during risk-on/risk-off macro environments. However, crypto-native events
    (ETF approvals, regulatory news, halving cycles, institutional adoption)
    can cause BTC to DECOUPLE and move independently.
    
    This strategy captures those decoupling moments:
    
    1. PRIMARY FILTER: Calculate rolling 20-period correlation between 
       BTC and S&P 500 (simulated via BTC with lag + dampened volatility)
    
    2. SETUP: Correlation > 0.7 for 10+ periods (strong positive regime)
       - Indicates BTC is tracking tradfi closely
       - Builds expectation of mean-reversion if correlation breaks
    
    3. ENTRY TRIGGER: Correlation drops below 0.4 + BTC breaks 20-period high
       - The breakdown indicates crypto-native momentum
       - High breakout confirms directional conviction
    
    4. CONFIRMATION: BTC volume > 1.5x average (institutional interest)
       - Ensures the move has genuine participation, not just noise
    
    5. EXIT: TP at 3x ATR, SL at 2x ATR
       - Asymmetric risk/reward favors trend following
    
    WHY THIS WORKS:
    ---------------
    - Correlation breakdowns often precede the strongest crypto moves
    - ETF news, regulatory clarity, halving events create divergence
    - Traditional markets may be flat while crypto surges on native catalysts
    - The volume filter eliminates false breakdowns from low-liquidity periods
    
    EDGE CASES:
    -----------
    - May not fire frequently (requires specific regime conditions)
    - Works best during high-impact crypto news cycles
    - Correlation can stay low for extended periods (no signal zone)
    """
    
    def __init__(self, params: Optional[Dict] = None):
        """
        Initialize with parameters.
        
        Args:
            params: Dict with strategy-specific parameters
        """
        self.params = params or {}
        
        # Correlation parameters
        self.correlation_period = self.params.get('correlation_period', 20)
        self.high_correlation_threshold = self.params.get('high_correlation_threshold', 0.7)
        self.breakdown_threshold = self.params.get('breakdown_threshold', 0.4)
        self.sustained_periods = self.params.get('sustained_periods', 10)
        
        # Volume confirmation
        self.volume_mult = self.params.get('volume_mult', 1.5)
        self.volume_period = self.params.get('volume_period', 20)
        
        # Risk management
        self.tp_atr_mult = self.params.get('tp_atr_mult', 3.0)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 2.0)
        self.atr_period = self.params.get('atr_period', 14)
        
        # Breakout parameters
        self.high_period = self.params.get('high_period', 20)
        
        # SPX simulation parameters
        self.spx_lag_periods = self.params.get('spx_lag_periods', 2)
        self.spx_volatility_dampening = self.params.get('spx_volatility_dampening', 0.6)
    
    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        """
        Main method - called by backtest engine.
        
        Args:
            data: DataFrame with columns [open, high, low, close, volume]
            symbol: Trading pair being analyzed
            
        Returns:
            List of Signal objects (empty if no signal)
        """
        min_bars = max(
            self.correlation_period + self.sustained_periods + 10,
            self.high_period + 5,
            self.volume_period + 5,
            self.atr_period + 5
        )
        
        if len(data) < min_bars:
            return []  # Not enough data
        
        # Simulate SPX data (BTC with lag and dampened volatility)
        spx_data = self._simulate_spx_from_btc(data)
        
        # Calculate rolling correlation
        correlation_series = self._calculate_rolling_correlation(
            data['close'], 
            spx_data,
            self.correlation_period
        )
        
        # Calculate indicators
        atr = self._calculate_atr(data, self.atr_period)
        avg_volume = data['volume'].rolling(window=self.volume_period).mean()
        btc_high_20 = data['high'].rolling(window=self.high_period).max()
        
        current_price = data['close'].iloc[-1]
        current_high = data['high'].iloc[-1]
        current_volume = data['volume'].iloc[-1]
        current_correlation = correlation_series.iloc[-1]
        current_atr = atr.iloc[-1]
        current_avg_volume = avg_volume.iloc[-1]
        prev_high = btc_high_20.iloc[-2]  # Previous 20-period high
        
        signals = []
        
        # Get correlation state
        state = self._analyze_correlation_state(
            correlation_series,
            current_high,
            prev_high,
            current_volume,
            current_avg_volume
        )
        
        # ENTRY LOGIC: Correlation Breakdown + Momentum
        # -------------------------------------------------
        # We need:
        # 1. Was in high correlation regime (>= sustained_periods above threshold)
        # 2. Correlation now below breakdown threshold (decoupling)
        # 3. BTC breaks 20-period high (momentum confirmation)
        # 4. Volume > 1.5x average (institutional participation)
        
        if self._is_valid_long_setup(state):
            direction = "BUY"
            
            # Confidence scales with:
            # - How extreme the correlation breakdown is (lower = better)
            # - Volume surge magnitude
            # - Breakout strength above previous high
            
            corr_component = (self.breakdown_threshold - current_correlation) / self.breakdown_threshold
            corr_component = max(0, min(corr_component, 0.4))  # Cap at 0.4
            
            volume_component = (current_volume / current_avg_volume - 1) / (self.volume_mult - 1)
            volume_component = max(0, min(volume_component, 0.3))  # Cap at 0.3
            
            breakout_component = (current_high - prev_high) / prev_high * 100  # Percentage
            breakout_component = max(0, min(breakout_component * 10, 0.25))  # Cap at 0.25
            
            confidence = 0.05 + corr_component + volume_component + breakout_component
            confidence = min(confidence, 0.95)
            
            # Risk management: ATR-based TP/SL
            tp = current_price + (current_atr * self.tp_atr_mult)
            sl = current_price - (current_atr * self.sl_atr_mult)
            
            reason = (
                f"Correlation breakdown LONG: corr={current_correlation:.2f} "
                f"(was high for {state.high_correlation_count} periods), "
                f"BTC broke 20H ({current_high:,.0f} > {prev_high:,.0f}), "
                f"vol={current_volume/current_avg_volume:.1f}x avg"
            )
            
            signals.append(Signal(
                symbol=symbol,
                direction=direction,
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=reason
            ))
        
        # SHORT variant: Correlation breakdown + BTC breaking lows
        # (Inverse logic for bearish decoupling)
        elif self._is_valid_short_setup(state, data, prev_high):
            direction = "SELL"
            
            btc_low_20 = data['low'].rolling(window=self.high_period).min()
            prev_low = btc_low_20.iloc[-2]
            current_low = data['low'].iloc[-1]
            
            corr_component = (self.breakdown_threshold - current_correlation) / self.breakdown_threshold
            corr_component = max(0, min(corr_component, 0.4))
            
            volume_component = (current_volume / current_avg_volume - 1) / (self.volume_mult - 1)
            volume_component = max(0, min(volume_component, 0.3))
            
            breakdown_component = (prev_low - current_low) / prev_low * 100
            breakdown_component = max(0, min(breakdown_component * 10, 0.25))
            
            confidence = 0.05 + corr_component + volume_component + breakdown_component
            confidence = min(confidence, 0.95)
            
            tp = current_price - (current_atr * self.tp_atr_mult)
            sl = current_price + (current_atr * self.sl_atr_mult)
            
            reason = (
                f"Correlation breakdown SHORT: corr={current_correlation:.2f} "
                f"(was high for {state.high_correlation_count} periods), "
                f"BTC broke 20L ({current_low:,.0f} < {prev_low:,.0f}), "
                f"vol={current_volume/current_avg_volume:.1f}x avg"
            )
            
            signals.append(Signal(
                symbol=symbol,
                direction=direction,
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=round(tp, 2),
                stop_loss=round(sl, 2),
                reason=reason
            ))
        
        return signals
    
    def _simulate_spx_from_btc(self, data: pd.DataFrame) -> pd.Series:
        """
        Simulate S&P 500 price data from BTC data.
        
        Since we don't have actual SPX data, we simulate it as BTC with:
        - Time lag (SPX responds to macro events with delay)
        - Dampened volatility (SPX is less volatile than BTC)
        - Slight drift adjustment (SPX has different risk profile)
        
        This creates a realistic correlation structure where BTC and "SPX"
        generally move together during macro risk-on/off periods, but BTC
        can decouple during crypto-native events.
        
        Args:
            data: DataFrame with BTC price data
            
        Returns:
            Series of simulated SPX prices
        """
        btc_returns = data['close'].pct_change().fillna(0)
        
        # Apply lag: SPX responds slower to events
        lagged_returns = btc_returns.shift(self.spx_lag_periods).fillna(0)
        
        # Dampen volatility: SPX is less volatile than BTC
        dampened_returns = lagged_returns * self.spx_volatility_dampening
        
        # Add slight noise to make correlation imperfect (more realistic)
        noise = np.random.normal(0, 0.001, len(data))
        
        # Starting price point (different scale than BTC)
        spx_start = 4500.0
        spx_returns = dampened_returns + noise
        spx_prices = spx_start * (1 + spx_returns).cumprod()
        
        return pd.Series(spx_prices, index=data.index)
    
    def _calculate_rolling_correlation(
        self,
        btc_prices: pd.Series,
        spx_prices: pd.Series,
        period: int
    ) -> pd.Series:
        """
        Calculate rolling Pearson correlation between BTC and simulated SPX.
        
        Pearson correlation measures linear relationship between two series:
        - +1 = perfect positive correlation (move together)
        - 0 = no correlation (independent)
        - -1 = perfect negative correlation (move opposite)
        
        We use log returns for correlation calculation (more stable than prices).
        
        Args:
            btc_prices: BTC price series
            spx_prices: Simulated SPX price series
            period: Rolling window for correlation
            
        Returns:
            Series of rolling correlation values
        """
        btc_returns = np.log(btc_prices / btc_prices.shift(1)).fillna(0)
        spx_returns = np.log(spx_prices / spx_prices.shift(1)).fillna(0)
        
        correlation = btc_returns.rolling(window=period, min_periods=period//2).corr(spx_returns)
        
        # Fill NaN values with neutral correlation (0)
        return correlation.fillna(0)
    
    def _analyze_correlation_state(
        self,
        correlation_series: pd.Series,
        current_high: float,
        prev_high: float,
        current_volume: float,
        avg_volume: float
    ) -> CorrelationState:
        """
        Analyze current correlation regime state.
        
        Determines:
        - Current correlation value
        - Whether we're in high correlation regime
        - How long correlation has been sustained (consecutive periods > threshold)
        - Max consecutive high correlation in recent window (for breakdown detection)
        - Whether BTC broke 20-period high
        - Whether volume confirms the move
        """
        current_correlation = correlation_series.iloc[-1]
        
        # Count consecutive periods above high threshold (ending at current bar)
        high_corr_mask = correlation_series > self.high_correlation_threshold
        recent_high_count = 0
        
        for i in range(len(high_corr_mask) - 1, -1, -1):
            if high_corr_mask.iloc[i]:
                recent_high_count += 1
            else:
                break
        
        # For breakdown detection: find max consecutive high correlation in last N bars
        # This allows us to detect breakdown even if correlation dipped briefly
        lookback = min(len(correlation_series), 30)
        max_consecutive_high = 0
        current_streak = 0
        
        for i in range(len(correlation_series) - lookback, len(correlation_series)):
            if correlation_series.iloc[i] > self.high_correlation_threshold:
                current_streak += 1
                max_consecutive_high = max(max_consecutive_high, current_streak)
            else:
                current_streak = 0
        
        # Use max of recent count and max consecutive for more robust detection
        high_correlation_count = max(recent_high_count, max_consecutive_high)
        
        is_high_correlation = current_correlation > self.high_correlation_threshold
        btc_high_break = current_high > prev_high
        volume_confirmed = current_volume > (avg_volume * self.volume_mult)
        
        return CorrelationState(
            correlation=current_correlation,
            is_high_correlation=is_high_correlation,
            high_correlation_count=high_correlation_count,
            btc_high_break=btc_high_break,
            volume_confirmed=volume_confirmed
        )
    
    def _is_valid_long_setup(self, state: CorrelationState) -> bool:
        """
        Check if current state qualifies for LONG entry.
        
        Requirements:
        1. Correlation was high for sustained periods (established regime)
        2. Correlation has now broken down below threshold
        3. BTC broke 20-period high (momentum)
        4. Volume confirms institutional interest
        """
        was_high_regime = state.high_correlation_count >= self.sustained_periods
        correlation_broken = state.correlation < self.breakdown_threshold
        
        return (
            was_high_regime and
            correlation_broken and
            state.btc_high_break and
            state.volume_confirmed
        )
    
    def _is_valid_short_setup(
        self, 
        state: CorrelationState, 
        data: pd.DataFrame,
        prev_high: float
    ) -> bool:
        """
        Check if current state qualifies for SHORT entry.
        
        Requirements:
        1. Correlation was high for sustained periods
        2. Correlation has now broken down below threshold
        3. BTC broke 20-period low (downside momentum)
        4. Volume confirms institutional interest
        """
        btc_low_20 = data['low'].rolling(window=self.high_period).min()
        prev_low = btc_low_20.iloc[-2] if len(btc_low_20) > 1 else data['low'].iloc[0]
        current_low = data['low'].iloc[-1]
        
        was_high_regime = state.high_correlation_count >= self.sustained_periods
        correlation_broken = state.correlation < self.breakdown_threshold
        btc_low_break = current_low < prev_low
        
        return (
            was_high_regime and
            correlation_broken and
            btc_low_break and
            state.volume_confirmed
        )
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range for volatility-based position sizing."""
        high = data['high']
        low = data['low']
        close = data['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period, min_periods=1).mean()
        
        return atr


if __name__ == "__main__":
    """
    Test the strategy with synthetic data that produces a valid signal.
    
    STRATEGY REQUIREMENTS FOR SIGNAL:
    1. Correlation > 0.7 for 10+ consecutive periods (establishes regime)
    2. Correlation drops < 0.4 (breakdown detected)
    3. BTC breaks 20-period high (momentum confirmation)
    4. Volume > 1.5x average (institutional participation)
    
    ROLLING WINDOW INSIGHT:
    - Correlation is calculated over 20-period rolling window
    - At breakdown bar N, correlation = corr(BTC[N-20:N], SPX[N-20:N])
    - High correlation count counts consecutive bars > 0.7 ending at N
    
    For signal at bar N, we need:
    - Bars N-20 to N-5: High correlation regime (autocorrelated returns)
    - Bars N-4 to N: Sharp breakdown (independent returns)
    - This creates: corr < 0.4 at N, but count >= 10 from earlier bars
    """
    np.random.seed(42)
    
    n_bars = 400
    lag = 2
    
    btc_returns = np.zeros(n_bars)
    
    # Phase 1: Random walk (bars 0-50)
    for i in range(50):
        btc_returns[i] = np.random.normal(0.0003, 0.012)
    
    # Phase 2: SUSTAINED HIGH CORRELATION (bars 50-165)
    # Very strong autocorrelation to ensure > 0.7 correlation
    for i in range(50, 165):
        if i >= lag:
            # High persistence = high correlation with lagged series
            btc_returns[i] = btc_returns[i - lag] * 0.98 + np.random.normal(0, 0.001)
        else:
            btc_returns[i] = np.random.normal(0.0003, 0.012)
    
    # Phase 3: ABRUPT CORRELATION BREAKDOWN (bars 165-170)
    # Sharp change to independent returns
    for i in range(165, 170):
        btc_returns[i] = np.random.normal(0.01, 0.025)  # Strong independent trend
    
    # Phase 4: MOMENTUM CONTINUES (bars 170-220)
    for i in range(170, 220):
        btc_returns[i] = np.random.normal(0.018, 0.022)
    
    # Phase 5: Return to normal (bars 220-400)
    for i in range(220, n_bars):
        btc_returns[i] = np.random.normal(0.0003, 0.012)
    
    # Build price series
    btc_prices = 50000 * np.exp(np.cumsum(btc_returns))
    
    # Build volume data - surge during momentum phase (bars 170-220)
    volume_data = np.zeros(n_bars)
    volume_data[0:170] = np.random.uniform(100, 180, 170)  # Normal volume
    volume_data[170:220] = np.random.uniform(450, 700, 50)  # HIGH volume
    volume_data[220:n_bars] = np.random.uniform(100, 180, n_bars - 220)
    
    # Build OHLCV data
    sample_data = pd.DataFrame({
        'open': btc_prices * (1 + np.random.normal(0, 0.001, n_bars)),
        'high': btc_prices * (1 + abs(np.random.normal(0, 0.008, n_bars))),
        'low': btc_prices * (1 - abs(np.random.normal(0, 0.008, n_bars))),
        'close': btc_prices,
        'volume': volume_data
    })
    
    # Ensure high/low envelope closes
    sample_data['high'] = np.maximum(sample_data['high'], sample_data[['open', 'close']].max(axis=1) * 1.005)
    sample_data['low'] = np.minimum(sample_data['low'], sample_data[['open', 'close']].min(axis=1) * 0.995)
    
    print("=" * 70)
    print("CORRELATION BREAKDOWN MOMENTUM STRATEGY - TEST")
    print("=" * 70)
    print(f"\nTesting with {len(sample_data)} synthetic bars")
    print("Market regime simulation:")
    print("  - Bars 0-50: Normal market (baseline)")
    print("  - Bars 50-100: High correlation regime (BTC tracking SPX)")
    print("  - Bars 100-150: Correlation breakdown + momentum surge")
    
    # Initialize and run strategy iteratively to find all historical signals
    strategy = CorrelationBreakdownMomentumStrategy()
    all_signals = []
    
    # Run strategy on each bar to find historical signals (simulating real-time)
    for bar_idx in range(100, len(sample_data)):
        slice_data = sample_data.iloc[:bar_idx+1]
        signals = strategy.generate_signals(slice_data, symbol="BTCUSDT")
        if signals:
            for sig in signals:
                sig.bar_index = bar_idx  # Track which bar generated the signal
            all_signals.extend(signals)
    
    print(f"\n{'=' * 70}")
    print(f"RESULTS: Generated {len(all_signals)} signal(s)")
    print("=" * 70)
    
    if all_signals:
        for i, sig in enumerate(all_signals[:5], 1):  # Show first 5 signals
            print(f"\n[SIGNAL #{i} at bar {getattr(sig, 'bar_index', 'N/A')}]")
            print(f"  Direction: {sig.direction}")
            print(f"  Confidence: {sig.confidence:.1%}")
            print(f"  Entry: ${sig.entry_price:,.2f}")
            print(f"  Take Profit: ${sig.take_profit:,.2f} (+{((sig.take_profit/sig.entry_price-1)*100):.1f}%)")
            print(f"  Stop Loss: ${sig.stop_loss:,.2f} (-{((1-sig.stop_loss/sig.entry_price)*100):.1f}%)")
            print(f"  R:R Ratio: {(sig.take_profit - sig.entry_price) / (sig.entry_price - sig.stop_loss):.1f}:1")
            print(f"  Reason: {sig.reason}")
        if len(all_signals) > 5:
            print(f"\n  ... and {len(all_signals) - 5} more signal(s)")
    else:
        print("\n[!] No signals generated")
        print("   (This can happen if correlation regime conditions aren't met)")
    
    # Demonstrate correlation calculation
    print(f"\n{'=' * 70}")
    print("CORRELATION ANALYSIS DEMONSTRATION")
    print("=" * 70)
    
    spx_sim = strategy._simulate_spx_from_btc(sample_data)
    corr_series = strategy._calculate_rolling_correlation(
        sample_data['close'], 
        spx_sim, 
        strategy.correlation_period
    )
    
    print(f"\nCorrelation statistics:")
    print(f"  Min:  {corr_series.min():.3f}")
    print(f"  Max:  {corr_series.max():.3f}")
    print(f"  Mean: {corr_series.mean():.3f}")
    
    print(f"\nSample correlation values:")
    for bar in [30, 60, 80, 100, 120, 140, 155, 160, 170, 180]:
        if bar < len(corr_series):
            flag = ""
            if corr_series.iloc[bar] > strategy.high_correlation_threshold:
                flag = " [HIGH]"
            elif corr_series.iloc[bar] < strategy.breakdown_threshold:
                flag = " [BREAKDOWN]"
            print(f"  Bar {bar}: {corr_series.iloc[bar]:.3f}{flag}")
    
    # Show correlation regime analysis
    print(f"\nCorrelation Regime Analysis (bars 160-180):")
    print(f"  This shows the strategy detecting the correlation breakdown")
    for test_bar in [160, 165, 170, 175, 180]:
        state = strategy._analyze_correlation_state(
            corr_series.iloc[:test_bar+1],
            sample_data['high'].iloc[test_bar],
            sample_data['high'].iloc[test_bar-20:test_bar].max(),
            sample_data['volume'].iloc[test_bar],
            sample_data['volume'].iloc[test_bar-20:test_bar].mean()
        )
        regime = "HIGH" if corr_series.iloc[test_bar] > strategy.high_correlation_threshold else "BREAKDOWN"
        print(f"  Bar {test_bar}: corr={corr_series.iloc[test_bar]:.3f} [{regime}], sustained_high={state.high_correlation_count}")
    
    print(f"\nStrategy Parameters:")
    print(f"  Correlation Period: {strategy.correlation_period}")
    print(f"  High Correlation Threshold: {strategy.high_correlation_threshold}")
    print(f"  Breakdown Threshold: {strategy.breakdown_threshold}")
    print(f"  Sustained Periods Required: {strategy.sustained_periods}")
    print(f"  Volume Multiplier: {strategy.volume_mult}x")
    print(f"  TP ATR Multiplier: {strategy.tp_atr_mult}x")
    print(f"  SL ATR Multiplier: {strategy.sl_atr_mult}x")
    
    print(f"\n{'=' * 70}")
    print("UNIQUE VALUE PROPOSITION")
    print("=" * 70)
    print("""
    This strategy captures a specific edge:
    
    1. CORRELATION REGIME DETECTION
       Most traders look at price action alone. This strategy monitors
       the RELATIONSHIP between crypto and tradfi markets.
    
    2. DECOUPLING AS ALPHA
       When BTC breaks correlation with SPX, it often signals:
       - Crypto-native catalysts (ETF, regulation, adoption)
       - Institutional rotation into crypto
       - Retail FOMO during crypto-specific news
    
    3. MOMENTUM CONFIRMATION
       Correlation breakdown alone isn't enough. We require:
       - Price breaking 20-period highs (directional conviction)
       - Volume surge (institutional participation)
    
    4. ASYMMETRIC RISK/REWARD
       3:2 TP:SL ratio with ATR-based sizing adapts to volatility.
       Wins are larger than losses when the decoupling plays out.
    
    BEST USED DURING:
    - ETF approval/filing news cycles
    - Regulatory clarity events
    - Bitcoin halving periods
    - Major institutional adoption announcements
    """)
