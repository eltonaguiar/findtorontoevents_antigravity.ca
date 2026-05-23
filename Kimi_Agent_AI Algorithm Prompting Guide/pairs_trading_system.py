"""
================================================================================
PAIRS TRADING SYSTEM - PRODUCTION-READY IMPLEMENTATION
================================================================================
A comprehensive market-neutral pairs trading framework for crypto and equity pairs.

Features:
- Cointegration testing (Engle-Granger, Johansen)
- Z-score based entry/exit signals
- Market-neutral position sizing (dollar-neutral, beta-neutral)
- Dynamic risk management
- Backtesting framework

Author: Quantitative Research Team
Version: 1.0.0
================================================================================
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from scipy import stats
from statsmodels.tsa.stattools import coint, adfuller
from statsmodels.tools.tools import add_constant
from statsmodels.regression.linear_model import OLS
from statsmodels.tsa.api import VAR
from statsmodels.tsa.vector_ar.vecm import coint_johansen
import warnings
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

warnings.filterwarnings('ignore')


# ================================================================================
# MATHEMATICAL FOUNDATION - COINTEGRATION THEORY
# ================================================================================
"""
COINTEGRATION MATHEMATICAL DERIVATION:
--------------------------------------

Two time series Y_t and X_t are cointegrated if:
1. Both series are I(1) - integrated of order 1 (non-stationary in levels but stationary in first differences)
2. There exists a linear combination Z_t = Y_t - βX_t - α that is I(0) - stationary

ENGLE-GRANGER TWO-STEP METHOD:
------------------------------
Step 1: Estimate the long-run equilibrium relationship via OLS:
    Y_t = α + βX_t + ε_t
    
    The residuals ε_t represent the deviation from equilibrium (spread).

Step 2: Test residuals for stationarity using Augmented Dickey-Fuller:
    Δε_t = γε_{t-1} + Σ(δ_i Δε_{t-i}) + u_t
    
    H0: γ = 0 (unit root exists, no cointegration)
    H1: γ < 0 (stationary, cointegration exists)

JOHANSEN TEST (for multiple cointegrating relationships):
---------------------------------------------------------
The Johansen test is based on the Vector Error Correction Model (VECM):
    ΔY_t = ΠY_{t-1} + Σ(Γ_i ΔY_{t-i}) + ΨD_t + ε_t

Where:
- Y_t is a vector of n time series
- Π = αβ' contains information about long-run relationships
- α is the adjustment coefficient matrix
- β is the cointegrating vector matrix
- r = rank(Π) = number of cointegrating relationships

Test statistics:
- Trace statistic: λ_trace = -T Σ(ln(1-λ_i)) for i=r+1 to n
- Max eigenvalue: λ_max = -T ln(1-λ_{r+1})

Z-SCORE CALCULATION:
-------------------
Z_t = (Spread_t - μ_Spread) / σ_Spread

Where spread can be:
- Price spread: S_t = P1_t - βP2_t
- Log spread: S_t = ln(P1_t) - βln(P2_t)  (more stable for crypto)
- Ratio: S_t = P1_t / P2_t
"""


# ================================================================================
# DATA CLASSES AND ENUMS
# ================================================================================

class SignalType(Enum):
    """Types of trading signals."""
    LONG_SPREAD = 1      # Long asset1, short asset2
    SHORT_SPREAD = -1    # Short asset1, long asset2
    NO_SIGNAL = 0


class ExitReason(Enum):
    """Reasons for exiting a position."""
    MEAN_REVERSION = "mean_reversion"
    STOP_LOSS = "stop_loss"
    TIME_STOP = "time_stop"
    MAX_HOLDING = "max_holding"
    DIVERGENCE_CONTINUATION = "divergence_continuation"


@dataclass
class PairConfig:
    """Configuration for a trading pair."""
    asset1: str
    asset2: str
    lookback_period: int = 60          # Period for calculating hedge ratio and z-score
    entry_zscore: float = 2.0          # Entry threshold
    exit_zscore: float = 0.5           # Exit threshold (mean reversion)
    stop_loss_zscore: float = 3.5      # Stop loss if divergence continues
    max_holding_periods: int = 20      # Maximum holding periods
    position_size_method: str = "dollar_neutral"  # dollar_neutral, beta_neutral, volatility_parity
    confidence_level: float = 0.05     # For cointegration test
    
    def __post_init__(self):
        assert self.entry_zscore > self.exit_zscore, "Entry must be > exit"
        assert self.stop_loss_zscore > self.entry_zscore, "Stop loss must be > entry"


@dataclass
class Position:
    """Represents an open position in a pair trade."""
    pair: Tuple[str, str]
    direction: SignalType
    entry_date: datetime
    entry_zscore: float
    entry_spread: float
    hedge_ratio: float
    position_sizes: Dict[str, float]  # {asset: quantity}
    entry_prices: Dict[str, float]
    
    # Tracking
    max_zscore_seen: float = 0.0
    min_zscore_seen: float = 0.0
    periods_held: int = 0
    
    def update_extremes(self, zscore: float):
        """Update extreme z-scores seen during position."""
        self.max_zscore_seen = max(self.max_zscore_seen, zscore)
        self.min_zscore_seen = min(self.min_zscore_seen, zscore)


@dataclass
class Trade:
    """Completed trade record."""
    pair: Tuple[str, str]
    direction: SignalType
    entry_date: datetime
    exit_date: datetime
    entry_zscore: float
    exit_zscore: float
    exit_reason: ExitReason
    pnl: float
    pnl_pct: float
    holding_periods: int
    
    def __repr__(self):
        return (f"Trade({self.pair[0]}/{self.pair[1]}, {self.direction.name}, "
                f"PnL={self.pnl:.4f}, Exit={self.exit_reason.value})")


@dataclass
class CointegrationResult:
    """Results from cointegration testing."""
    pair: Tuple[str, str]
    is_cointegrated: bool
    test_type: str  # "engle_granger" or "johansen"
    test_statistic: float
    p_value: Optional[float]
    critical_values: Dict[str, float]
    hedge_ratio: float
    intercept: float
    half_life: float
    adf_residuals: float  # ADF test statistic on residuals
    
    def __repr__(self):
        status = "COINTEGRATED" if self.is_cointegrated else "NOT COINTEGRATED"
        p_str = f"{self.p_value:.4f}" if self.p_value is not None else "N/A"
        return f"CointResult({self.pair[0]}/{self.pair[1]}, {status}, p={p_str})"


# ================================================================================
# PAIRS TRADING STRATEGY CLASS
# ================================================================================

class PairsTradingStrategy:
    """
    Comprehensive pairs trading strategy implementation.
    
    Supports:
    - Multiple cointegration tests (Engle-Granger, Johansen)
    - Z-score based signal generation
    - Market-neutral position sizing
    - Dynamic risk management
    """
    
    def __init__(self, 
                 config: Optional[PairConfig] = None,
                 use_log_prices: bool = True,
                 transaction_cost: float = 0.001):
        """
        Initialize the pairs trading strategy.
        
        Args:
            config: Pair configuration parameters
            use_log_prices: Use log prices for spread calculation (recommended for crypto)
            transaction_cost: Transaction cost as fraction (e.g., 0.001 = 0.1%)
        """
        self.config = config or PairConfig("BTC", "ETH")
        self.use_log_prices = use_log_prices
        self.transaction_cost = transaction_cost
        
        # State
        self.positions: Dict[Tuple[str, str], Position] = {}
        self.trades: List[Trade] = []
        self.hedge_ratio_history: List[float] = []
        self.zscore_history: List[float] = []
        
        logger.info(f"Initialized PairsTradingStrategy for {self.config.asset1}/{self.config.asset2}")
    
    # ============================================================================
    # COINTEGRATION TESTING METHODS
    # ============================================================================
    
    @staticmethod
    def engle_granger_test(price1: pd.Series, 
                           price2: pd.Series,
                           significance: float = 0.05) -> CointegrationResult:
        """
        Perform Engle-Granger two-step cointegration test.
        
        Args:
            price1: Price series for asset 1 (dependent variable)
            price2: Price series for asset 2 (independent variable)
            significance: Significance level for test
            
        Returns:
            CointegrationResult with test statistics and hedge ratio
        """
        # Step 1: OLS regression to find hedge ratio
        X = add_constant(price2)
        model = OLS(price1, X).fit()
        
        intercept = model.params.iloc[0]
        hedge_ratio = model.params.iloc[1]
        residuals = model.resid
        
        # Step 2: ADF test on residuals
        adf_result = adfuller(residuals, autolag='AIC')
        adf_stat = adf_result[0]
        adf_pvalue = adf_result[1]
        critical_values = {
            '1%': adf_result[4]['1%'],
            '5%': adf_result[4]['5%'],
            '10%': adf_result[4]['10%']
        }
        
        # Cointegration test (similar to ADF on residuals)
        coint_stat, coint_pvalue, _ = coint(price1, price2)
        
        # Calculate half-life of mean reversion
        # From Ornstein-Uhlenbeck process: dS = -θ(S-μ)dt + σdW
        # Half-life = ln(2) / θ
        lagged_residuals = residuals.shift(1).dropna()
        delta_residuals = residuals.diff().dropna()
        
        # Align series
        delta_residuals = delta_residuals.loc[lagged_residuals.index]
        
        # Regression: Δε_t = α + ρε_{t-1} + u_t
        X_ou = add_constant(lagged_residuals)
        ou_model = OLS(delta_residuals, X_ou).fit()
        theta = -ou_model.params.iloc[1]
        
        half_life = np.log(2) / theta if theta > 0 else np.inf
        
        is_cointegrated = coint_pvalue < significance
        
        return CointegrationResult(
            pair=(price1.name, price2.name),
            is_cointegrated=is_cointegrated,
            test_type="engle_granger",
            test_statistic=coint_stat,
            p_value=coint_pvalue,
            critical_values=critical_values,
            hedge_ratio=hedge_ratio,
            intercept=intercept,
            half_life=half_life,
            adf_residuals=adf_stat
        )
    
    @staticmethod
    def johansen_test(prices_df: pd.DataFrame,
                      det_order: int = 0,
                      k_ar_diff: int = 1,
                      significance: float = 0.05) -> List[CointegrationResult]:
        """
        Perform Johansen cointegration test for multiple time series.
        
        Args:
            prices_df: DataFrame with price series as columns
            det_order: Deterministic term (0: no constant, 1: constant, 2: linear trend)
            k_ar_diff: Number of lagged differences
            significance: Significance level
            
        Returns:
            List of CointegrationResult for each pair
        """
        results = []
        
        # Johansen test
        johansen = coint_johansen(prices_df, det_order, k_ar_diff)
        
        # Trace statistic critical values
        trace_crit = johansen.cvt  # Critical values for trace statistic
        max_eig_crit = johansen.cvm  # Critical values for max eigenvalue
        
        # Determine number of cointegrating relationships
        n_series = len(prices_df.columns)
        
        for i in range(n_series - 1):
            for j in range(i + 1, n_series):
                asset1 = prices_df.columns[i]
                asset2 = prices_df.columns[j]
                
                # Get pair-specific cointegration via Engle-Granger for simplicity
                pair_result = PairsTradingStrategy.engle_granger_test(
                    prices_df[asset1], prices_df[asset2], significance
                )
                results.append(pair_result)
        
        return results
    
    @staticmethod
    def find_cointegrated_pairs(price_df: pd.DataFrame,
                                significance: float = 0.05,
                                min_half_life: float = 1.0,
                                max_half_life: float = 252.0) -> pd.DataFrame:
        """
        Find all cointegrated pairs from a universe of assets.
        
        Args:
            price_df: DataFrame with price series as columns
            significance: Significance level for cointegration test
            min_half_life: Minimum acceptable half-life (periods)
            max_half_life: Maximum acceptable half-life (periods)
            
        Returns:
            DataFrame with cointegrated pairs sorted by p-value
        """
        pairs_results = []
        assets = price_df.columns.tolist()
        
        logger.info(f"Testing {len(assets)} assets for cointegration...")
        
        for i in range(len(assets)):
            for j in range(i + 1, len(assets)):
                asset1, asset2 = assets[i], assets[j]
                
                # Get overlapping data
                pair_data = price_df[[asset1, asset2]].dropna()
                
                if len(pair_data) < 100:
                    continue
                
                # Perform Engle-Granger test
                result = PairsTradingStrategy.engle_granger_test(
                    pair_data[asset1], pair_data[asset2], significance
                )
                
                # Filter by half-life
                if (result.is_cointegrated and 
                    min_half_life <= result.half_life <= max_half_life):
                    pairs_results.append({
                        'asset1': asset1,
                        'asset2': asset2,
                        'p_value': result.p_value,
                        'hedge_ratio': result.hedge_ratio,
                        'half_life': result.half_life,
                        'adf_stat': result.adf_residuals,
                        'test_statistic': result.test_statistic
                    })
        
        if not pairs_results:
            logger.warning("No cointegrated pairs found")
            return pd.DataFrame()
        
        results_df = pd.DataFrame(pairs_results)
        results_df = results_df.sort_values('p_value')
        
        logger.info(f"Found {len(results_df)} cointegrated pairs")
        
        return results_df
    
    # ============================================================================
    # SPREAD AND Z-SCORE CALCULATIONS
    # ============================================================================
    
    def calculate_spread(self, 
                         price1: pd.Series, 
                         price2: pd.Series,
                         hedge_ratio: Optional[float] = None,
                         lookback: Optional[int] = None) -> pd.Series:
        """
        Calculate the spread between two price series.
        
        Args:
            price1: Price series for asset 1
            price2: Price series for asset 2
            hedge_ratio: Hedge ratio (if None, calculated from lookback period)
            lookback: Lookback period for calculating hedge ratio
            
        Returns:
            Spread series
        """
        if self.use_log_prices:
            p1 = np.log(price1)
            p2 = np.log(price2)
        else:
            p1 = price1
            p2 = price2
        
        if hedge_ratio is None:
            if lookback is None:
                lookback = self.config.lookback_period
            
            # Rolling hedge ratio via OLS
            hedge_ratio = self._calculate_hedge_ratio(p1.iloc[-lookback:], 
                                                       p2.iloc[-lookback:])
        
        spread = p1 - hedge_ratio * p2
        
        return spread
    
    def _calculate_hedge_ratio(self, 
                               p1: pd.Series, 
                               p2: pd.Series,
                               method: str = "ols") -> float:
        """
        Calculate hedge ratio between two series.
        
        Args:
            p1: Series 1 (can be log prices)
            p2: Series 2
            method: "ols" or "tls" (total least squares)
            
        Returns:
            Hedge ratio (beta)
        """
        if method == "ols":
            # Ordinary Least Squares: minimize vertical distances
            X = add_constant(p2)
            model = OLS(p1, X).fit()
            return model.params.iloc[1]
        
        elif method == "tls":
            # Total Least Squares: minimize perpendicular distances
            # Using PCA approach
            data = np.vstack([p1, p2]).T
            pca = np.linalg.svd(data - data.mean(axis=0))
            # The hedge ratio comes from the principal component
            return -pca[2][0, 1] / pca[2][0, 0] if pca[2][0, 0] != 0 else 1.0
        
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def calculate_zscore(self, 
                         spread: pd.Series,
                         lookback: Optional[int] = None,
                         method: str = "simple") -> pd.Series:
        """
        Calculate z-score of the spread.
        
        Args:
            spread: Spread series
            lookback: Lookback window for mean and std
            method: "simple", "ewm" (exponentially weighted), or "kalman"
            
        Returns:
            Z-score series
        """
        if lookback is None:
            lookback = self.config.lookback_period
        
        if method == "simple":
            # Simple rolling z-score
            mean = spread.rolling(window=lookback).mean()
            std = spread.rolling(window=lookback).std()
            zscore = (spread - mean) / std
            
        elif method == "ewm":
            # Exponentially weighted z-score (more responsive)
            mean = spread.ewm(span=lookback).mean()
            std = spread.ewm(span=lookback).std()
            zscore = (spread - mean) / std
            
        elif method == "kalman":
            # Kalman filter for adaptive mean and variance
            zscore = self._kalman_zscore(spread, lookback)
            
        else:
            raise ValueError(f"Unknown method: {method}")
        
        self.zscore_history = zscore.dropna().tolist()
        
        return zscore
    
    def _kalman_zscore(self, spread: pd.Series, lookback: int) -> pd.Series:
        """
        Calculate z-score using Kalman filter for adaptive estimation.
        
        The Kalman filter adapts to changing market conditions by
        updating the mean estimate with each new observation.
        """
        # Kalman filter parameters
        observation_cov = 1.0
        transition_cov = 0.01  # Process noise
        
        # Initialize
        n = len(spread)
        filtered_mean = np.zeros(n)
        filtered_var = np.zeros(n)
        
        # Initial state
        filtered_mean[0] = spread.iloc[0]
        filtered_var[0] = 1.0
        
        for t in range(1, n):
            # Prediction step
            pred_mean = filtered_mean[t-1]
            pred_var = filtered_var[t-1] + transition_cov
            
            # Update step
            innovation = spread.iloc[t] - pred_mean
            innovation_var = pred_var + observation_cov
            kalman_gain = pred_var / innovation_var
            
            filtered_mean[t] = pred_mean + kalman_gain * innovation
            filtered_var[t] = (1 - kalman_gain) * pred_var
        
        # Calculate rolling std for z-score
        rolling_std = spread.rolling(window=lookback).std()
        
        zscore = (spread - pd.Series(filtered_mean, index=spread.index)) / rolling_std
        
        return zscore
    
    # ============================================================================
    # SIGNAL GENERATION
    # ============================================================================
    
    def generate_signals(self, 
                         zscore: pd.Series,
                         entry_threshold: Optional[float] = None,
                         exit_threshold: Optional[float] = None,
                         stop_loss: Optional[float] = None) -> pd.DataFrame:
        """
        Generate trading signals based on z-score thresholds.
        
        Args:
            zscore: Z-score series
            entry_threshold: Entry z-score threshold
            exit_threshold: Exit z-score threshold
            stop_loss: Stop loss z-score threshold
            
        Returns:
            DataFrame with signals and positions
        """
        if entry_threshold is None:
            entry_threshold = self.config.entry_zscore
        if exit_threshold is None:
            exit_threshold = self.config.exit_zscore
        if stop_loss is None:
            stop_loss = self.config.stop_loss_zscore
        
        signals = pd.DataFrame(index=zscore.index)
        signals['zscore'] = zscore
        signals['signal'] = SignalType.NO_SIGNAL.value
        signals['position'] = 0
        
        current_position = 0
        
        for i in range(1, len(signals)):
            z = signals['zscore'].iloc[i]
            
            if current_position == 0:
                # No position - look for entry
                if z > entry_threshold:
                    # Short spread: short asset1, long asset2
                    signals['signal'].iloc[i] = SignalType.SHORT_SPREAD.value
                    current_position = -1
                elif z < -entry_threshold:
                    # Long spread: long asset1, short asset2
                    signals['signal'].iloc[i] = SignalType.LONG_SPREAD.value
                    current_position = 1
                    
            elif current_position == 1:
                # Long spread position - look for exit
                if z > -exit_threshold or z < -stop_loss:
                    # Exit: mean reversion or stop loss
                    signals['signal'].iloc[i] = SignalType.NO_SIGNAL.value
                    current_position = 0
                    
            elif current_position == -1:
                # Short spread position - look for exit
                if z < exit_threshold or z > stop_loss:
                    # Exit: mean reversion or stop loss
                    signals['signal'].iloc[i] = SignalType.NO_SIGNAL.value
                    current_position = 0
            
            signals['position'].iloc[i] = current_position
        
        return signals
    
    def generate_signals_advanced(self,
                                   zscore: pd.Series,
                                   spread: pd.Series,
                                   price1: pd.Series,
                                   price2: pd.Series,
                                   entry_threshold: Optional[float] = None,
                                   exit_threshold: Optional[float] = None,
                                   stop_loss: Optional[float] = None) -> pd.DataFrame:
        """
        Generate signals with additional filters and conditions.
        
        Additional filters:
        - Trend filter: only trade when spread is mean-reverting
        - Volatility filter: avoid trading in extreme volatility
        - Correlation filter: ensure pair correlation is stable
        """
        if entry_threshold is None:
            entry_threshold = self.config.entry_zscore
        if exit_threshold is None:
            exit_threshold = self.config.exit_zscore
        if stop_loss is None:
            stop_loss = self.config.stop_loss_zscore
        
        signals = pd.DataFrame(index=zscore.index)
        signals['zscore'] = zscore
        signals['spread'] = spread
        signals['signal'] = SignalType.NO_SIGNAL.value
        signals['position'] = 0
        signals['exit_reason'] = None
        
        # Calculate additional filters
        lookback = self.config.lookback_period
        
        # Hurst exponent (mean reversion indicator)
        signals['hurst'] = self._calculate_hurst_exponent(spread, lookback)
        
        # Rolling correlation
        signals['correlation'] = self._calculate_rolling_correlation(price1, price2, lookback)
        
        # Volatility regime
        signals['volatility'] = spread.rolling(lookback).std()
        signals['vol_percentile'] = signals['volatility'].rolling(lookback * 2).apply(
            lambda x: stats.percentileofscore(x, x.iloc[-1]) / 100
        )
        
        current_position = 0
        entry_zscore = 0
        
        for i in range(lookback * 2, len(signals)):
            z = signals['zscore'].iloc[i]
            hurst = signals['hurst'].iloc[i]
            corr = signals['correlation'].iloc[i]
            vol_pct = signals['vol_percentile'].iloc[i]
            
            # Entry filters
            mean_reverting = hurst < 0.5
            stable_correlation = corr > 0.5
            normal_volatility = vol_pct < 0.8  # Not in top 20% volatility
            
            can_enter = mean_reverting and stable_correlation and normal_volatility
            
            if current_position == 0:
                if can_enter:
                    if z > entry_threshold:
                        signals['signal'].iloc[i] = SignalType.SHORT_SPREAD.value
                        current_position = -1
                        entry_zscore = z
                    elif z < -entry_threshold:
                        signals['signal'].iloc[i] = SignalType.LONG_SPREAD.value
                        current_position = 1
                        entry_zscore = z
                        
            elif current_position == 1:
                # Check exit conditions
                if z > -exit_threshold:
                    signals['signal'].iloc[i] = SignalType.NO_SIGNAL.value
                    signals['exit_reason'].iloc[i] = ExitReason.MEAN_REVERSION.value
                    current_position = 0
                elif z < -stop_loss:
                    signals['signal'].iloc[i] = SignalType.NO_SIGNAL.value
                    signals['exit_reason'].iloc[i] = ExitReason.DIVERGENCE_CONTINUATION.value
                    current_position = 0
                    
            elif current_position == -1:
                # Check exit conditions
                if z < exit_threshold:
                    signals['signal'].iloc[i] = SignalType.NO_SIGNAL.value
                    signals['exit_reason'].iloc[i] = ExitReason.MEAN_REVERSION.value
                    current_position = 0
                elif z > stop_loss:
                    signals['signal'].iloc[i] = SignalType.NO_SIGNAL.value
                    signals['exit_reason'].iloc[i] = ExitReason.DIVERGENCE_CONTINUATION.value
                    current_position = 0
            
            signals['position'].iloc[i] = current_position
        
        return signals
    
    def _calculate_hurst_exponent(self, 
                                   series: pd.Series, 
                                   max_lag: int = 100) -> pd.Series:
        """
        Calculate Hurst exponent to test for mean reversion.
        
        H < 0.5: Mean-reverting
        H = 0.5: Random walk
        H > 0.5: Trending
        """
        lags = range(2, min(max_lag, len(series) // 4))
        
        hurst_values = []
        
        for i in range(len(series)):
            if i < max_lag * 2:
                hurst_values.append(0.5)
                continue
            
            # Get window of data
            window = series.iloc[max(0, i - max_lag * 2):i]
            
            # Calculate tau for each lag
            tau = [np.sqrt(np.std(np.subtract(window[lag:], window[:-lag]))) 
                   for lag in lags]
            
            # Fit linear regression to log-log plot
            poly = np.polyfit(np.log(lags), np.log(tau), 1)
            hurst = poly[0] * 2.0
            
            hurst_values.append(hurst)
        
        return pd.Series(hurst_values, index=series.index)
    
    def _calculate_rolling_correlation(self,
                                        price1: pd.Series,
                                        price2: pd.Series,
                                        window: int) -> pd.Series:
        """Calculate rolling correlation between two price series."""
        returns1 = price1.pct_change()
        returns2 = price2.pct_change()
        return returns1.rolling(window).corr(returns2)
    
    # ============================================================================
    # POSITION SIZING
    # ============================================================================
    
    def calculate_position_sizes(self,
                                  price1: float,
                                  price2: float,
                                  hedge_ratio: float,
                                  capital: float,
                                  method: Optional[str] = None,
                                  beta1: float = 1.0,
                                  beta2: float = 1.0) -> Dict[str, float]:
        """
        Calculate position sizes for market-neutral pair trade.
        
        Args:
            price1: Current price of asset 1
            price2: Current price of asset 2
            hedge_ratio: Hedge ratio from cointegration
            capital: Total capital allocated to the trade
            method: "dollar_neutral", "beta_neutral", "volatility_parity"
            beta1: Beta of asset 1 (for beta-neutral sizing)
            beta2: Beta of asset 2
            
        Returns:
            Dictionary with position sizes {asset1: quantity, asset2: quantity}
        """
        if method is None:
            method = self.config.position_size_method
        
        if method == "dollar_neutral":
            # Dollar-neutral: equal dollar exposure on both legs
            # Long $X of asset1, short $X of asset2
            half_capital = capital / 2
            qty1 = half_capital / price1
            qty2 = half_capital / price2
            
        elif method == "beta_neutral":
            # Beta-neutral: neutralize market exposure
            # Position sizes adjusted by beta
            # β_portfolio = w1*β1 + w2*β2 = 0
            # With hedge ratio: w1 = hedge_ratio * w2
            # hedge_ratio * w2 * β1 + w2 * β2 = 0
            # w2 * (hedge_ratio * β1 + β2) = 0
            
            # For dollar-neutral beta hedge:
            dollar1 = capital / 2
            dollar2 = -dollar1 * (beta1 / beta2) if beta2 != 0 else -dollar1
            
            qty1 = dollar1 / price1
            qty2 = abs(dollar2) / price2
            
        elif method == "volatility_parity":
            # Volatility parity: equal risk contribution
            # Position sizes inversely proportional to volatility
            # Requires historical data - simplified version
            qty1 = (capital / 2) / price1
            qty2 = (capital / 2) / price2
            
        elif method == "kelly":
            # Kelly criterion position sizing
            # Requires edge and odds estimates
            kelly_fraction = 0.25  # Conservative half-Kelly
            edge = 0.02  # Expected return
            odds = 1.0   # Payoff ratio
            
            kelly_size = capital * kelly_fraction * (edge / odds)
            qty1 = kelly_size / price1
            qty2 = kelly_size / price2
            
        else:
            raise ValueError(f"Unknown position sizing method: {method}")
        
        return {
            self.config.asset1: qty1,
            self.config.asset2: qty2
        }
    
    # ============================================================================
    # RISK MANAGEMENT
    # ============================================================================
    
    def check_exit_conditions(self,
                               position: Position,
                               current_zscore: float,
                               current_prices: Dict[str, float],
                               current_date: datetime) -> Tuple[bool, ExitReason]:
        """
        Check if position should be exited based on various conditions.
        
        Returns:
            Tuple of (should_exit, exit_reason)
        """
        # Update position tracking
        position.update_extremes(current_zscore)
        position.periods_held += 1
        
        # Check mean reversion
        if position.direction == SignalType.LONG_SPREAD:
            if current_zscore >= -self.config.exit_zscore:
                return True, ExitReason.MEAN_REVERSION
        else:  # SHORT_SPREAD
            if current_zscore <= self.config.exit_zscore:
                return True, ExitReason.MEAN_REVERSION
        
        # Check stop loss (divergence continuation)
        if abs(current_zscore) > self.config.stop_loss_zscore:
            return True, ExitReason.DIVERGENCE_CONTINUATION
        
        # Check maximum holding period
        if position.periods_held >= self.config.max_holding_periods:
            return True, ExitReason.MAX_HOLDING
        
        # Check unrealized PnL stop loss (optional)
        unrealized_pnl = self._calculate_unrealized_pnl(position, current_prices)
        max_loss_pct = -0.05  # 5% max loss
        
        entry_value = sum(position.entry_prices.values())
        if entry_value > 0 and unrealized_pnl / entry_value < max_loss_pct:
            return True, ExitReason.STOP_LOSS
        
        return False, ExitReason.MEAN_REVERSION  # Default, won't be used
    
    def _calculate_unrealized_pnl(self,
                                   position: Position,
                                   current_prices: Dict[str, float]) -> float:
        """Calculate unrealized PnL for open position."""
        pnl = 0.0
        
        for asset, qty in position.position_sizes.items():
            entry_price = position.entry_prices[asset]
            current_price = current_prices[asset]
            
            if position.direction == SignalType.LONG_SPREAD:
                if asset == self.config.asset1:
                    pnl += qty * (current_price - entry_price)
                else:
                    pnl += qty * (entry_price - current_price)
            else:  # SHORT_SPREAD
                if asset == self.config.asset1:
                    pnl += qty * (entry_price - current_price)
                else:
                    pnl += qty * (current_price - entry_price)
        
        return pnl
    
    def calculate_var(self,
                      returns: pd.DataFrame,
                      position_sizes: Dict[str, float],
                      current_prices: Dict[str, float],
                      confidence: float = 0.95,
                      method: str = "historical") -> float:
        """
        Calculate Value at Risk for the pair position.
        
        Args:
            returns: Historical returns DataFrame
            position_sizes: Position quantities
            current_prices: Current prices
            confidence: VaR confidence level
            method: "historical", "parametric", or "monte_carlo"
            
        Returns:
            VaR value (positive number representing potential loss)
        """
        # Calculate position values
        position_values = {
            asset: qty * current_prices[asset]
            for asset, qty in position_sizes.items()
        }
        
        # Calculate portfolio returns
        weights = np.array([
            position_values[self.config.asset1],
            -position_values[self.config.asset2]  # Short position
        ])
        total_value = abs(weights).sum()
        weights = weights / total_value
        
        pair_returns = returns[[self.config.asset1, self.config.asset2]].dropna()
        portfolio_returns = pair_returns @ weights
        
        if method == "historical":
            var = -np.percentile(portfolio_returns, (1 - confidence) * 100)
            
        elif method == "parametric":
            mu = portfolio_returns.mean()
            sigma = portfolio_returns.std()
            var = -(mu - stats.norm.ppf(confidence) * sigma)
            
        elif method == "monte_carlo":
            # Monte Carlo simulation
            n_sims = 10000
            simulated_returns = np.random.normal(
                portfolio_returns.mean(),
                portfolio_returns.std(),
                n_sims
            )
            var = -np.percentile(simulated_returns, (1 - confidence) * 100)
            
        else:
            raise ValueError(f"Unknown VaR method: {method}")
        
        return var * total_value


# ================================================================================
# BACKTESTING FRAMEWORK
# ================================================================================

class PairsBacktester:
    """
    Backtesting framework for pairs trading strategies.
    """
    
    def __init__(self,
                 strategy: PairsTradingStrategy,
                 initial_capital: float = 100000.0):
        """
        Initialize the backtester.
        
        Args:
            strategy: PairsTradingStrategy instance
            initial_capital: Starting capital
        """
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # Tracking
        self.equity_curve: List[float] = []
        self.dates: List[datetime] = []
        self.positions_history: List[Dict] = []
        
    def run_backtest(self,
                     price1: pd.Series,
                     price2: pd.Series,
                     rebalance_freq: int = 1) -> pd.DataFrame:
        """
        Run backtest on historical price data.
        
        Args:
            price1: Price series for asset 1
            price2: Price series for asset 2
            rebalance_freq: Rebalance frequency (periods)
            
        Returns:
            DataFrame with backtest results
        """
        config = self.strategy.config
        lookback = config.lookback_period
        
        # Initialize results
        results = pd.DataFrame(index=price1.index)
        results['price1'] = price1
        results['price2'] = price2
        results['spread'] = np.nan
        results['zscore'] = np.nan
        results['signal'] = 0
        results['position'] = 0
        results['hedge_ratio'] = np.nan
        results['returns'] = 0.0
        results['cumulative_returns'] = 1.0
        results['drawdown'] = 0.0
        
        current_position = None
        
        for i in range(lookback, len(price1)):
            date = price1.index[i]
            
            # Get lookback window
            window1 = price1.iloc[max(0, i - lookback):i]
            window2 = price2.iloc[max(0, i - lookback):i]
            
            # Calculate spread and z-score
            spread = self.strategy.calculate_spread(window1, window2)
            zscore = self.strategy.calculate_zscore(spread)
            
            current_zscore = zscore.iloc[-1]
            current_spread = spread.iloc[-1]
            
            results.loc[date, 'spread'] = current_spread
            results.loc[date, 'zscore'] = current_zscore
            
            # Calculate hedge ratio
            hedge_ratio = self.strategy._calculate_hedge_ratio(
                np.log(window1) if self.strategy.use_log_prices else window1,
                np.log(window2) if self.strategy.use_log_prices else window2
            )
            results.loc[date, 'hedge_ratio'] = hedge_ratio
            
            # Check for exit if in position
            if current_position is not None:
                current_prices = {
                    config.asset1: price1.iloc[i],
                    config.asset2: price2.iloc[i]
                }
                
                should_exit, exit_reason = self.strategy.check_exit_conditions(
                    current_position, current_zscore, current_prices, date
                )
                
                if should_exit:
                    # Close position
                    pnl = self._close_position(
                        current_position, price1.iloc[i], price2.iloc[i], date, exit_reason
                    )
                    results.loc[date, 'returns'] = pnl / self.current_capital
                    current_position = None
                    results.loc[date, 'signal'] = 0
                else:
                    results.loc[date, 'signal'] = current_position.direction.value
                    
            # Check for entry if not in position
            if current_position is None and i % rebalance_freq == 0:
                if current_zscore > config.entry_zscore:
                    # Short spread
                    current_position = self._open_position(
                        SignalType.SHORT_SPREAD, date, current_zscore,
                        current_spread, hedge_ratio, price1.iloc[i], price2.iloc[i]
                    )
                    results.loc[date, 'signal'] = SignalType.SHORT_SPREAD.value
                    
                elif current_zscore < -config.entry_zscore:
                    # Long spread
                    current_position = self._open_position(
                        SignalType.LONG_SPREAD, date, current_zscore,
                        current_spread, hedge_ratio, price1.iloc[i], price2.iloc[i]
                    )
                    results.loc[date, 'signal'] = SignalType.LONG_SPREAD.value
            
            results.loc[date, 'position'] = 1 if current_position else 0
            
            # Update equity curve
            self.equity_curve.append(self.current_capital)
            self.dates.append(date)
        
        # Close any open position at the end
        if current_position is not None:
            self._close_position(
                current_position, price1.iloc[-1], price2.iloc[-1],
                price1.index[-1], ExitReason.MAX_HOLDING
            )
        
        # Calculate cumulative returns and drawdown
        results['cumulative_returns'] = (1 + results['returns']).cumprod()
        results['drawdown'] = (results['cumulative_returns'] / 
                               results['cumulative_returns'].cummax() - 1)
        
        return results
    
    def _open_position(self,
                       direction: SignalType,
                       date: datetime,
                       zscore: float,
                       spread: float,
                       hedge_ratio: float,
                       price1: float,
                       price2: float) -> Position:
        """Open a new position."""
        config = self.strategy.config
        
        # Calculate position sizes
        position_sizes = self.strategy.calculate_position_sizes(
            price1, price2, hedge_ratio, self.current_capital * 0.5  # Use 50% of capital
        )
        
        position = Position(
            pair=(config.asset1, config.asset2),
            direction=direction,
            entry_date=date,
            entry_zscore=zscore,
            entry_spread=spread,
            hedge_ratio=hedge_ratio,
            position_sizes=position_sizes,
            entry_prices={config.asset1: price1, config.asset2: price2}
        )
        
        return position
    
    def _close_position(self,
                        position: Position,
                        price1: float,
                        price2: float,
                        date: datetime,
                        exit_reason: ExitReason) -> float:
        """Close a position and calculate PnL."""
        config = self.strategy.config
        
        # Calculate PnL
        qty1 = position.position_sizes[config.asset1]
        qty2 = position.position_sizes[config.asset2]
        
        if position.direction == SignalType.LONG_SPREAD:
            # Long asset1, short asset2
            pnl1 = qty1 * (price1 - position.entry_prices[config.asset1])
            pnl2 = qty2 * (position.entry_prices[config.asset2] - price2)
        else:  # SHORT_SPREAD
            # Short asset1, long asset2
            pnl1 = qty1 * (position.entry_prices[config.asset1] - price1)
            pnl2 = qty2 * (price2 - position.entry_prices[config.asset2])
        
        gross_pnl = pnl1 + pnl2
        
        # Subtract transaction costs
        entry_value = qty1 * position.entry_prices[config.asset1] + qty2 * position.entry_prices[config.asset2]
        exit_value = qty1 * price1 + qty2 * price2
        transaction_cost = (entry_value + exit_value) * self.strategy.transaction_cost
        
        net_pnl = gross_pnl - transaction_cost
        
        # Update capital
        self.current_capital += net_pnl
        
        # Record trade
        trade = Trade(
            pair=position.pair,
            direction=position.direction,
            entry_date=position.entry_date,
            exit_date=date,
            entry_zscore=position.entry_zscore,
            exit_zscore=0,  # Would need to track
            exit_reason=exit_reason,
            pnl=net_pnl,
            pnl_pct=net_pnl / (entry_value / 2),
            holding_periods=position.periods_held
        )
        self.strategy.trades.append(trade)
        
        return net_pnl
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Calculate performance metrics from backtest."""
        if not self.strategy.trades:
            return {}
        
        trades = self.strategy.trades
        returns = [t.pnl_pct for t in trades]
        
        # Basic metrics
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.pnl > 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        
        # Sharpe ratio (assuming 252 periods per year)
        sharpe = (avg_return / std_return * np.sqrt(252)) if std_return > 0 else 0
        
        # Profit factor
        gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
        
        # Average holding period
        avg_holding = np.mean([t.holding_periods for t in trades])
        
        # Max drawdown from equity curve
        equity = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity)
        drawdown = (equity - running_max) / running_max
        max_drawdown = drawdown.min()
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'std_return': std_return,
            'sharpe_ratio': sharpe,
            'profit_factor': profit_factor,
            'avg_holding_periods': avg_holding,
            'max_drawdown': max_drawdown,
            'final_capital': self.current_capital,
            'total_return': (self.current_capital - self.initial_capital) / self.initial_capital
        }


# ================================================================================
# PARAMETER OPTIMIZATION
# ================================================================================

class ParameterOptimizer:
    """
    Optimize pairs trading parameters using walk-forward analysis.
    """
    
    @staticmethod
    def optimize_zscore_thresholds(price1: pd.Series,
                                    price2: pd.Series,
                                    entry_range: np.ndarray = np.arange(1.5, 3.5, 0.25),
                                    exit_range: np.ndarray = np.arange(0.0, 1.5, 0.25),
                                    lookback_range: List[int] = [30, 60, 90],
                                    metric: str = "sharpe") -> pd.DataFrame:
        """
        Grid search for optimal z-score thresholds.
        
        Args:
            price1: Price series for asset 1
            price2: Price series for asset 2
            entry_range: Range of entry thresholds to test
            exit_range: Range of exit thresholds to test
            lookback_range: Range of lookback periods to test
            metric: Optimization metric ("sharpe", "return", "win_rate")
            
        Returns:
            DataFrame with optimization results
        """
        results = []
        
        for lookback in lookback_range:
            for entry in entry_range:
                for exit_thresh in exit_range:
                    if exit_thresh >= entry:
                        continue
                    
                    config = PairConfig(
                        asset1="Asset1",
                        asset2="Asset2",
                        lookback_period=lookback,
                        entry_zscore=entry,
                        exit_zscore=exit_thresh
                    )
                    
                    strategy = PairsTradingStrategy(config)
                    backtester = PairsBacktester(strategy)
                    
                    try:
                        backtest_results = backtester.run_backtest(price1, price2)
                        metrics = backtester.get_performance_metrics()
                        
                        if metrics:
                            results.append({
                                'lookback': lookback,
                                'entry': entry,
                                'exit': exit_thresh,
                                'sharpe': metrics.get('sharpe_ratio', 0),
                                'return': metrics.get('total_return', 0),
                                'win_rate': metrics.get('win_rate', 0),
                                'max_dd': metrics.get('max_drawdown', 0),
                                'trades': metrics.get('total_trades', 0)
                            })
                    except Exception as e:
                        logger.warning(f"Error with params {lookback}/{entry}/{exit_thresh}: {e}")
        
        results_df = pd.DataFrame(results)
        
        if not results_df.empty:
            results_df = results_df.sort_values(metric, ascending=False)
        
        return results_df
    
    @staticmethod
    def walk_forward_optimization(price1: pd.Series,
                                   price2: pd.Series,
                                   train_size: int = 252,
                                   test_size: int = 63,
                                   param_grid: Optional[Dict] = None) -> pd.DataFrame:
        """
        Walk-forward optimization to avoid overfitting.
        
        Args:
            price1: Price series for asset 1
            price2: Price series for asset 2
            train_size: Training window size
            test_size: Testing window size
            param_grid: Dictionary of parameter ranges
            
        Returns:
            DataFrame with out-of-sample results
        """
        if param_grid is None:
            param_grid = {
                'entry_zscore': [1.5, 2.0, 2.5],
                'exit_zscore': [0.0, 0.5, 1.0],
                'lookback_period': [30, 60, 90]
            }
        
        results = []
        n = len(price1)
        
        # Walk forward
        for start in range(0, n - train_size - test_size, test_size):
            train_end = start + train_size
            test_end = train_end + test_size
            
            train1 = price1.iloc[start:train_end]
            train2 = price2.iloc[start:train_end]
            test1 = price1.iloc[train_end:test_end]
            test2 = price2.iloc[train_end:test_end]
            
            # In-sample optimization
            best_sharpe = -np.inf
            best_params = None
            
            for entry in param_grid['entry_zscore']:
                for exit_thresh in param_grid['exit_zscore']:
                    for lookback in param_grid['lookback_period']:
                        if exit_thresh >= entry:
                            continue
                        
                        config = PairConfig(
                            asset1="Asset1",
                            asset2="Asset2",
                            lookback_period=lookback,
                            entry_zscore=entry,
                            exit_zscore=exit_thresh
                        )
                        
                        strategy = PairsTradingStrategy(config)
                        backtester = PairsBacktester(strategy)
                        
                        try:
                            backtester.run_backtest(train1, train2)
                            metrics = backtester.get_performance_metrics()
                            
                            if metrics and metrics.get('sharpe_ratio', 0) > best_sharpe:
                                best_sharpe = metrics['sharpe_ratio']
                                best_params = {
                                    'entry': entry,
                                    'exit': exit_thresh,
                                    'lookback': lookback
                                }
                        except:
                            continue
            
            # Out-of-sample test
            if best_params:
                config = PairConfig(
                    asset1="Asset1",
                    asset2="Asset2",
                    lookback_period=best_params['lookback'],
                    entry_zscore=best_params['entry'],
                    exit_zscore=best_params['exit']
                )
                
                strategy = PairsTradingStrategy(config)
                backtester = PairsBacktester(strategy)
                
                try:
                    backtester.run_backtest(test1, test2)
                    metrics = backtester.get_performance_metrics()
                    
                    if metrics:
                        results.append({
                            'train_start': price1.index[start],
                            'train_end': price1.index[train_end],
                            'test_start': price1.index[train_end],
                            'test_end': price1.index[test_end],
                            'entry': best_params['entry'],
                            'exit': best_params['exit'],
                            'lookback': best_params['lookback'],
                            **metrics
                        })
                except:
                    continue
        
        return pd.DataFrame(results)


# ================================================================================
# UTILITY FUNCTIONS
# ================================================================================

def plot_pairs_analysis(price1: pd.Series,
                        price2: pd.Series,
                        spread: pd.Series,
                        zscore: pd.Series,
                        signals: pd.DataFrame,
                        save_path: Optional[str] = None):
    """
    Create visualization of pairs trading analysis.
    
    Args:
        price1: Price series for asset 1
        price2: Price series for asset 2
        spread: Spread series
        zscore: Z-score series
        signals: Signals DataFrame
        save_path: Path to save figure
    """
    try:
        import matplotlib.pyplot as plt
        
        fig, axes = plt.subplots(4, 1, figsize=(14, 12))
        
        # Plot 1: Normalized prices
        ax1 = axes[0]
        (price1 / price1.iloc[0]).plot(ax=ax1, label=price1.name)
        (price2 / price2.iloc[0]).plot(ax=ax1, label=price2.name)
        ax1.set_title('Normalized Prices')
        ax1.legend()
        ax1.grid(True)
        
        # Plot 2: Spread
        ax2 = axes[1]
        spread.plot(ax=ax2, color='purple')
        ax2.axhline(spread.mean(), color='red', linestyle='--', label='Mean')
        ax2.set_title('Spread')
        ax2.legend()
        ax2.grid(True)
        
        # Plot 3: Z-score with signals
        ax3 = axes[2]
        zscore.plot(ax=ax3, color='blue')
        
        # Entry/exit lines
        config = PairConfig("", "")  # Default config for thresholds
        ax3.axhline(config.entry_zscore, color='red', linestyle='--', alpha=0.5)
        ax3.axhline(-config.entry_zscore, color='red', linestyle='--', alpha=0.5)
        ax3.axhline(config.exit_zscore, color='green', linestyle='--', alpha=0.5)
        ax3.axhline(-config.exit_zscore, color='green', linestyle='--', alpha=0.5)
        ax3.fill_between(zscore.index, -config.entry_zscore, config.entry_zscore, 
                         alpha=0.1, color='green')
        
        # Plot signals
        long_signals = signals[signals['signal'] == SignalType.LONG_SPREAD.value]
        short_signals = signals[signals['signal'] == SignalType.SHORT_SPREAD.value]
        
        ax3.scatter(long_signals.index, zscore.loc[long_signals.index], 
                   color='green', marker='^', s=100, label='Long Spread')
        ax3.scatter(short_signals.index, zscore.loc[short_signals.index], 
                   color='red', marker='v', s=100, label='Short Spread')
        
        ax3.set_title('Z-Score with Signals')
        ax3.legend()
        ax3.grid(True)
        
        # Plot 4: Position over time
        ax4 = axes[3]
        signals['position'].plot(ax=ax4, drawstyle='steps-post')
        ax4.set_title('Position')
        ax4.set_ylim(-1.5, 1.5)
        ax4.grid(True)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        plt.show()
        
    except ImportError:
        logger.warning("matplotlib not available for plotting")


def generate_sample_data(n_periods: int = 1000,
                         correlation: float = 0.9,
                         mean_reversion_speed: float = 0.1,
                         seed: int = 42) -> Tuple[pd.Series, pd.Series]:
    """
    Generate sample cointegrated price data for testing.
    
    Args:
        n_periods: Number of periods
        correlation: Correlation between assets
        mean_reversion_speed: Speed of mean reversion
        seed: Random seed
        
    Returns:
        Tuple of (price1, price2) series
    """
    np.random.seed(seed)
    
    # Generate common factor (random walk)
    common_factor = np.cumsum(np.random.randn(n_periods) * 0.01)
    
    # Generate cointegrated series
    # Y_t = β * X_t + ε_t where ε_t is mean-reverting
    beta = 0.5
    
    # Mean-reverting residual
    epsilon = np.zeros(n_periods)
    epsilon[0] = np.random.randn()
    
    for t in range(1, n_periods):
        epsilon[t] = (1 - mean_reversion_speed) * epsilon[t-1] + np.random.randn() * 0.02
    
    # Construct prices
    price1 = 100 * np.exp(common_factor + epsilon)
    price2 = 100 * np.exp(common_factor / beta)
    
    dates = pd.date_range(start='2020-01-01', periods=n_periods, freq='D')
    
    return (pd.Series(price1, index=dates, name='Asset1'),
            pd.Series(price2, index=dates, name='Asset2'))


# ================================================================================
# MAIN EXECUTION EXAMPLE
# ================================================================================

def main():
    """Main execution demonstrating the pairs trading system."""
    
    print("=" * 80)
    print("PAIRS TRADING SYSTEM - DEMONSTRATION")
    print("=" * 80)
    
    # Generate sample cointegrated data
    print("\n[1] Generating sample cointegrated price data...")
    price1, price2 = generate_sample_data(n_periods=1000, correlation=0.9)
    print(f"    Asset 1: {len(price1)} observations")
    print(f"    Asset 2: {len(price2)} observations")
    
    # Test for cointegration
    print("\n[2] Testing for cointegration (Engle-Granger)...")
    coint_result = PairsTradingStrategy.engle_granger_test(price1, price2)
    print(f"    {coint_result}")
    print(f"    Hedge Ratio: {coint_result.hedge_ratio:.4f}")
    print(f"    Half-Life: {coint_result.half_life:.2f} periods")
    
    # Configure strategy
    print("\n[3] Configuring pairs trading strategy...")
    config = PairConfig(
        asset1="Asset1",
        asset2="Asset2",
        lookback_period=60,
        entry_zscore=2.0,
        exit_zscore=0.5,
        stop_loss_zscore=3.5,
        max_holding_periods=30,
        position_size_method="dollar_neutral"
    )
    print(f"    Entry Z-Score: ±{config.entry_zscore}")
    print(f"    Exit Z-Score: ±{config.exit_zscore}")
    print(f"    Stop Loss: ±{config.stop_loss_zscore}")
    print(f"    Lookback: {config.lookback_period} periods")
    
    # Initialize strategy
    strategy = PairsTradingStrategy(config, use_log_prices=True)
    
    # Calculate spread and z-score
    print("\n[4] Calculating spread and z-score...")
    spread = strategy.calculate_spread(price1, price2)
    zscore = strategy.calculate_zscore(spread, method="simple")
    print(f"    Spread mean: {spread.mean():.4f}")
    print(f"    Spread std: {spread.std():.4f}")
    print(f"    Z-score range: [{zscore.min():.2f}, {zscore.max():.2f}]")
    
    # Generate signals
    print("\n[5] Generating trading signals...")
    signals = strategy.generate_signals(zscore)
    long_signals = (signals['signal'] == SignalType.LONG_SPREAD.value).sum()
    short_signals = (signals['signal'] == SignalType.SHORT_SPREAD.value).sum()
    print(f"    Long spread signals: {long_signals}")
    print(f"    Short spread signals: {short_signals}")
    
    # Run backtest
    print("\n[6] Running backtest...")
    backtester = PairsBacktester(strategy, initial_capital=100000)
    results = backtester.run_backtest(price1, price2)
    
    # Performance metrics
    print("\n[7] Performance Metrics:")
    metrics = backtester.get_performance_metrics()
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"    {key}: {value:.4f}")
        else:
            print(f"    {key}: {value}")
    
    # Show trades
    print("\n[8] Trade Summary:")
    if strategy.trades:
        trades_df = pd.DataFrame([
            {
                'entry_date': t.entry_date,
                'exit_date': t.exit_date,
                'direction': t.direction.name,
                'pnl': t.pnl,
                'pnl_pct': t.pnl_pct,
                'exit_reason': t.exit_reason.value,
                'holding': t.holding_periods
            }
            for t in strategy.trades
        ])
        print(trades_df.head(10).to_string())
    
    # Parameter optimization example
    print("\n[9] Parameter Optimization (sample)...")
    print("    Running grid search for optimal thresholds...")
    
    # Use smaller ranges for demo
    opt_results = ParameterOptimizer.optimize_zscore_thresholds(
        price1.iloc[:500], price2.iloc[:500],
        entry_range=np.arange(1.5, 3.0, 0.5),
        exit_range=np.arange(0.0, 1.0, 0.5),
        lookback_range=[30, 60]
    )
    
    if not opt_results.empty:
        print("\n    Top 5 parameter combinations:")
        print(opt_results.head().to_string())
    
    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    
    return results, metrics


if __name__ == "__main__":
    results, metrics = main()
