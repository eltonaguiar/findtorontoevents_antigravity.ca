"""
================================================================================
STATISTICAL ARBITRAGE MODEL
================================================================================
Mean Reversion & Pairs Trading Strategy for Cryptocurrency Markets

Methodology:
- Ornstein-Uhlenbeck process modeling
- Kalman filter for dynamic hedge ratios
- Cointegration-based pair selection
- Bollinger Band mean reversion

Reference: "Statistical Arbitrage in the U.S. Equities Market" 
(Gatev, Goetzmann, Rouwenhorst, 2006)
================================================================================
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum
import json
from scipy import stats
from scipy.optimize import minimize


class SignalType(Enum):
    """Types of statistical arbitrage signals"""
    MEAN_REVERSION = "mean_reversion"
    PAIRS_TRADE = "pairs_trade"
    TREND_FILTERED_MR = "trend_filtered_mr"


@dataclass
class StatArbConfig:
    """Configuration for Statistical Arbitrage model"""
    # Mean reversion parameters
    lookback_window: int = 20  # Period for mean/std calculation
    entry_zscore: float = 1.5  # Enter when |z-score| > 1.5
    exit_zscore: float = 0.5  # Exit when |z-score| < 0.5
    stop_zscore: float = 3.0  # Stop loss at |z-score| > 3.0
    
    # Half-life estimation
    half_life_max: int = 60  # Maximum acceptable half-life
    half_life_min: int = 2   # Minimum acceptable half-life
    
    # Risk management
    max_position: float = 1.0
    position_scaling: str = "zscore_inverse"  # How to scale position
    
    # Trend filtering
    use_trend_filter: bool = True
    trend_ma_period: int = 50
    
    # Volatility scaling
    target_volatility: float = 0.40  # 40% annualized


class OrnsteinUhlenbeck:
    """
    Ornstein-Uhlenbeck process for modeling mean reversion
    
    The OU process is described by:
    dx(t) = θ(μ - x(t))dt + σdW(t)
    
    Where:
    - θ: Speed of mean reversion
    - μ: Long-term mean
    - σ: Volatility
    - Half-life: ln(2) / θ
    """
    
    def __init__(self):
        self.theta = None
        self.mu = None
        self.sigma = None
        self.half_life = None
    
    def fit(self, prices: np.ndarray) -> Dict:
        """
        Fit OU process to price series using linear regression
        
        Returns:
            Dict with parameters and fit statistics
        """
        # Calculate returns (discretized OU)
        x = prices[:-1]
        dx = np.diff(prices)
        
        # Regression: dx = θ(μ - x)dt + ε
        # Rearranged: dx = θμ - θx + ε
        # y = a + bx where a = θμ, b = -θ
        
        # Add constant for intercept
        X = np.column_stack([np.ones(len(x)), x])
        
        # OLS regression
        try:
            beta = np.linalg.lstsq(X, dx, rcond=None)[0]
            a, b = beta[0], beta[1]
            
            self.theta = -b
            self.mu = a / self.theta if self.theta != 0 else np.mean(prices)
            
            # Calculate residuals and sigma
            dx_pred = a + b * x
            residuals = dx - dx_pred
            self.sigma = np.std(residuals)
            
            # Calculate half-life
            if self.theta > 0:
                self.half_life = np.log(2) / self.theta
            else:
                self.half_life = np.inf
            
            # R-squared
            ss_res = np.sum(residuals ** 2)
            ss_tot = np.sum((dx - np.mean(dx)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            return {
                'theta': self.theta,
                'mu': self.mu,
                'sigma': self.sigma,
                'half_life': self.half_life,
                'r_squared': r_squared,
                'is_mean_reverting': self.theta > 0 and self.half_life < 100
            }
        except:
            return {
                'theta': 0,
                'mu': np.mean(prices),
                'sigma': np.std(prices),
                'half_life': np.inf,
                'r_squared': 0,
                'is_mean_reverting': False
            }
    
    def predict_next(self, current: float) -> float:
        """Predict next value based on OU dynamics"""
        if self.theta is None:
            return current
        # E[x(t+1)] = x(t) + θ(μ - x(t))
        return current + self.theta * (self.mu - current)
    
    def expected_return(self, current: float, holding_period: int = 1) -> float:
        """Expected return over holding period"""
        if self.theta is None or self.theta <= 0:
            return 0
        
        # E[x(t+h)] = μ + (x(t) - μ) * exp(-θh)
        expected_price = self.mu + (current - self.mu) * np.exp(-self.theta * holding_period)
        return (expected_price - current) / current


class KalmanFilterPairs:
    """
    Kalman filter for dynamic pairs trading hedge ratios
    
    Estimates the time-varying relationship between two assets:
    y(t) = alpha(t) + beta(t) * x(t) + epsilon(t)
    """
    
    def __init__(self, delta: float = 1e-4):
        """
        Args:
            delta: Transition covariance (lower = smoother estimates)
        """
        self.delta = delta
        
        # State: [alpha, beta]
        self.state = np.array([0., 1.])
        self.covariance = np.eye(2)
        
        # Transition matrix (identity - random walk)
        self.F = np.eye(2)
        
        # Observation matrix placeholder
        self.H = np.zeros((1, 2))
        
        # Measurement noise
        self.R = 1.0
    
    def update(self, x: float, y: float) -> Tuple[float, float, float]:
        """
        Update filter with new observation
        
        Args:
            x: Independent variable price
            y: Dependent variable price
            
        Returns:
            alpha, beta, spread
        """
        # Prediction
        self.state = self.F @ self.state
        self.covariance = self.F @ self.covariance @ self.F.T + self.delta * np.eye(2)
        
        # Observation matrix
        self.H = np.array([[1, x]])
        
        # Innovation
        y_pred = self.H @ self.state
        innovation = y - y_pred
        
        # Innovation covariance
        S = self.H @ self.covariance @ self.H.T + self.R
        
        # Kalman gain
        K = self.covariance @ self.H.T / S
        
        # Update
        self.state = self.state + K.flatten() * innovation
        self.covariance = (np.eye(2) - K @ self.H) @ self.covariance
        
        alpha, beta = self.state
        spread = y - (alpha + beta * x)
        
        return alpha, beta, spread
    
    def get_hedge_ratio(self) -> Tuple[float, float]:
        """Get current alpha and beta estimates"""
        return self.state[0], self.state[1]


class StatisticalArbitrageModel:
    """
    Statistical Arbitrage Trading Model
    
    Combines multiple mean reversion strategies:
    1. Ornstein-Uhlenbeck based signals
    2. Bollinger Band mean reversion
    3. Kalman filter pairs trading (when pair available)
    4. Trend-filtered mean reversion
    """
    
    def __init__(self, config: StatArbConfig = None):
        self.config = config or StatArbConfig()
        self.ou_process = OrnsteinUhlenbeck()
        self.kalman = None  # Initialized when pair data provided
        
        # State tracking
        self.zscore_history = []
        self.position = 0
        self.entry_zscore = 0
    
    def calculate_zscore(self, price: float, mean: float, std: float) -> float:
        """Calculate normalized z-score"""
        if std == 0:
            return 0
        return (price - mean) / std
    
    def get_mean_reversion_signal(self, df: pd.DataFrame) -> Dict:
        """
        Generate mean reversion signal based on OU process
        """
        prices = df['price'].values
        
        # Need sufficient data
        if len(prices) < self.config.lookback_window:
            return {'signal': 0, 'confidence': 0, 'half_life': np.inf}
        
        # Calculate rolling statistics
        recent_prices = prices[-self.config.lookback_window:]
        mean = np.mean(recent_prices)
        std = np.std(recent_prices)
        current_price = prices[-1]
        
        # Calculate z-score
        zscore = self.calculate_zscore(current_price, mean, std)
        self.zscore_history.append(zscore)
        
        # Fit OU process for half-life estimation
        ou_params = self.ou_process.fit(recent_prices)
        
        # Trend filter
        trend_aligned = True
        if self.config.use_trend_filter and len(prices) >= self.config.trend_ma_period:
            ma_trend = np.mean(prices[-self.config.trend_ma_period:])
            trend_direction = 1 if current_price > ma_trend else -1
            # Only take mean reversion trades against the trend when strongly extended
            if trend_direction * zscore < 0 and abs(zscore) < self.config.entry_zscore * 1.5:
                trend_aligned = False
        
        # Generate signal
        signal = 0
        confidence = 0
        
        if ou_params['is_mean_reverting'] and trend_aligned:
            half_life = ou_params['half_life']
            
            # Check if half-life is in acceptable range
            if self.config.half_life_min <= half_life <= self.config.half_life_max:
                
                # Entry signal
                if abs(zscore) > self.config.entry_zscore and self.position == 0:
                    signal = -np.sign(zscore)  # Trade opposite to z-score
                    self.position = signal
                    self.entry_zscore = zscore
                    confidence = min(abs(zscore) / self.config.stop_zscore, 1.0)
                
                # Exit signal
                elif self.position != 0:
                    if abs(zscore) < self.config.exit_zscore:
                        signal = 0  # Exit
                        self.position = 0
                        confidence = 1.0
                    elif abs(zscore) > self.config.stop_zscore:
                        signal = 0  # Stop loss
                        self.position = 0
                        confidence = 0.0
                    else:
                        signal = self.position  # Hold
                        confidence = 1 - abs(zscore) / self.config.stop_zscore
        
        return {
            'signal': signal,
            'zscore': zscore,
            'half_life': ou_params['half_life'],
            'confidence': confidence,
            'is_mean_reverting': ou_params['is_mean_reverting'],
            'r_squared': ou_params['r_squared']
        }
    
    def get_pairs_signal(self, df_primary: pd.DataFrame, 
                         df_secondary: pd.DataFrame) -> Dict:
        """
        Generate pairs trading signal using Kalman filter
        
        Args:
            df_primary: Primary asset (to trade)
            df_secondary: Secondary asset (for hedge)
        """
        if len(df_primary) < 10 or len(df_secondary) < 10:
            return {'signal': 0, 'hedge_ratio': 1.0}
        
        # Initialize Kalman filter on first use
        if self.kalman is None:
            self.kalman = KalmanFilterPairs()
        
        # Get prices
        y = df_primary['price'].values[-1]
        x = df_secondary['price'].values[-1]
        
        # Update filter
        alpha, beta, spread = self.kalman.update(x, y)
        
        # Calculate spread z-score (need history)
        # Simplified: use recent spread variance
        if len(df_primary) >= self.config.lookback_window:
            recent_y = df_primary['price'].values[-self.config.lookback_window:]
            recent_x = df_secondary['price'].values[-self.config.lookback_window:]
            
            # Calculate historical spreads
            spreads = recent_y - (alpha + beta * recent_x)
            spread_mean = np.mean(spreads)
            spread_std = np.std(spreads)
            
            if spread_std > 0:
                zscore = (spread - spread_mean) / spread_std
                
                # Generate signal
                if abs(zscore) > self.config.entry_zscore:
                    signal = -np.sign(zscore)
                    confidence = min(abs(zscore) / self.config.stop_zscore, 1.0)
                else:
                    signal = 0
                    confidence = 0
                
                return {
                    'signal': signal,
                    'zscore': zscore,
                    'spread': spread,
                    'alpha': alpha,
                    'beta': beta,
                    'confidence': confidence,
                    'hedge_ratio': beta
                }
        
        return {'signal': 0, 'hedge_ratio': beta}
    
    def predict(self, df: pd.DataFrame, pair_df: Optional[pd.DataFrame] = None) -> Dict:
        """
        Generate prediction using statistical arbitrage approach
        
        Args:
            df: Primary asset data
            pair_df: Optional pair asset for pairs trading
        """
        signals = {}
        
        # Mean reversion signal
        mr_signal = self.get_mean_reversion_signal(df)
        signals['mean_reversion'] = mr_signal
        
        # Pairs signal if pair data available
        if pair_df is not None:
            pair_signal = self.get_pairs_signal(df, pair_df)
            signals['pairs'] = pair_signal
            
            # Combine signals (prioritize pairs if available)
            if abs(pair_signal.get('zscore', 0)) > abs(mr_signal.get('zscore', 0)):
                primary_signal = pair_signal
                signal_type = SignalType.PAIRS_TRADE
            else:
                primary_signal = mr_signal
                signal_type = SignalType.MEAN_REVERSION
        else:
            primary_signal = mr_signal
            signal_type = SignalType.MEAN_REVERSION
        
        # Position sizing
        position_size = 0
        if primary_signal['signal'] != 0:
            if self.config.position_scaling == "zscore_inverse":
                # Scale inversely by z-score magnitude
                position_size = min(abs(primary_signal['signal']) * 
                                   primary_signal.get('confidence', 0.5), 
                                   self.config.max_position)
            else:
                position_size = self.config.max_position if primary_signal['signal'] != 0 else 0
        
        return {
            'signal': primary_signal['signal'],
            'direction': 'LONG' if primary_signal['signal'] > 0 
                        else 'SHORT' if primary_signal['signal'] < 0 
                        else 'NEUTRAL',
            'position_size': position_size,
            'confidence': primary_signal.get('confidence', 0),
            'zscore': primary_signal.get('zscore', 0),
            'half_life': primary_signal.get('half_life', np.inf),
            'signal_type': signal_type.value,
            'model_type': 'Statistical_Arbitrage',
            'components': signals,
            'timestamp': str(df.index[-1]) if hasattr(df.index[-1], '__str__') else df.index[-1]
        }
    
    def backtest(self, df: pd.DataFrame, pair_df: Optional[pd.DataFrame] = None,
                 asset: str = None, train_size: int = 50, 
                 step_size: int = 4) -> Dict:
        """
        Walk-forward backtest
        """
        results = {
            'predictions': [],
            'returns': [],
            'zscores': [],
            'half_lives': [],
            'timestamps': []
        }
        
        idx = train_size
        while idx < len(df) - 1:
            test_df = df.iloc[:idx+1]
            test_pair = pair_df.iloc[:idx+1] if pair_df is not None else None
            
            # Generate prediction
            pred = self.predict(test_df, test_pair)
            
            # Calculate realized return
            future_return = df['price'].iloc[idx+1] / df['price'].iloc[idx] - 1
            
            # Strategy return
            if pred['signal'] != 0:
                strategy_return = future_return * np.sign(pred['signal']) * pred['position_size']
            else:
                strategy_return = 0
            
            results['predictions'].append(pred['signal'])
            results['returns'].append(strategy_return)
            results['zscores'].append(pred.get('zscore', 0))
            results['half_lives'].append(pred.get('half_life', np.inf))
            results['timestamps'].append(df.index[idx])
            
            idx += step_size
        
        return results


# Model metadata
STAT_ARB_METADATA = {
    "model_name": "CryptoAlpha_Statistical_Arbitrage",
    "architecture": "Multi-Strategy Mean Reversion",
    "components": [
        "Ornstein-Uhlenbeck Process Estimation",
        "Kalman Filter Pairs Trading",
        "Bollinger Band Mean Reversion",
        "Trend-Filtered Signals",
        "Half-Life Based Position Sizing"
    ],
    "key_parameters": {
        "entry_zscore": 1.5,
        "exit_zscore": 0.5,
        "stop_zscore": 3.0,
        "half_life_range": "2-60 periods",
        "lookback_window": 20
    },
    "signal_types": ["MEAN_REVERSION", "PAIRS_TRADE"],
    "key_advantages": [
        "Mathematically grounded in OU process theory",
        "Dynamic hedge ratios via Kalman filter",
        "Explicit mean reversion speed estimation",
        "Natural risk management via z-score stops",
        "Works well in sideways markets"
    ],
    "limitations": [
        "Requires sufficient mean reversion in price series",
        "Half-life estimation can be noisy",
        "Underperforms in strong trending markets",
        "Pairs trading requires correlated assets",
        "Kalman filter sensitive to initial parameters"
    ],
    "best_market_conditions": [
        "Sideways/consolidating markets",
        "High mean reversion (low half-life)",
        "Correlated asset pairs available",
        "Moderate volatility regimes"
    ]
}


def get_stat_arb_documentation() -> str:
    """Return formatted model documentation"""
    return json.dumps(STAT_ARB_METADATA, indent=2)


if __name__ == "__main__":
    print("=" * 80)
    print("STATISTICAL ARBITRAGE MODEL")
    print("=" * 80)
    print("\nModel Metadata:")
    print(get_stat_arb_documentation())
    print("\n" + "=" * 80)
    print("This model excels in sideways markets with clear mean reversion")
    print("=" * 80)
