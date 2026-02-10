
# COMPREHENSIVE RISK MANAGEMENT FRAMEWORK FOR QUANTITATIVE TRADING
# =================================================================

## TABLE OF CONTENTS
# 1. Position Sizing Framework
# 2. Portfolio-Level Risk Controls
# 3. Regime Detection Methodology
# 4. Dynamic Leverage & Volatility Targeting
# 5. Specific Risk Rules & Thresholds
# 6. Meta-Learner Risk Allocator
# 7. Python Implementation

# =============================================================================
# SECTION 1: POSITION SIZING FRAMEWORK
# =============================================================================

## 1.1 KELLY CRITERION IMPLEMENTATION

"""
The Kelly Criterion determines optimal position size based on edge and odds.

K = (p*b - q) / b

Where:
- K = Kelly fraction (optimal bet size)
- p = probability of win
- q = probability of loss (1-p)
- b = average win / average loss (payoff ratio)
"""

def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """
    Calculate full Kelly fraction.
    
    Args:
        win_rate: Probability of winning (0-1)
        avg_win: Average winning trade return (positive)
        avg_loss: Average losing trade return (positive number)
    
    Returns:
        Kelly fraction (can be negative if no edge)
    """
    if avg_loss == 0:
        return 0
    
    b = avg_win / avg_loss  # Payoff ratio
    q = 1 - win_rate
    
    kelly = (win_rate * b - q) / b
    
    return max(0, kelly)  # No negative bets


### Fractional Kelly (RECOMMENDED FOR LIVE TRADING)
"""
Full Kelly is too aggressive for most traders due to:
- Parameter estimation errors
- Non-stationary markets
- Fat tails in returns

RECOMMENDED FRACTIONS:
- Conservative: 0.10 - 0.15 (10-15% of Kelly)
- Moderate: 0.20 - 0.25 (20-25% of Kelly)
- Aggressive: 0.30 - 0.50 (30-50% of Kelly)
- NEVER use full Kelly in production
"""

def fractional_kelly(win_rate: float, avg_win: float, avg_loss: float, 
                     fraction: float = 0.25) -> float:
    """
    Calculate fractional Kelly position size.
    
    Args:
        win_rate: Probability of winning
        avg_win: Average winning trade return
        avg_loss: Average losing trade return
        fraction: Kelly fraction (default 0.25 = quarter Kelly)
    
    Returns:
        Fractional Kelly position size
    """
    kelly = kelly_criterion(win_rate, avg_win, avg_loss)
    return kelly * fraction


## 1.2 VOLATILITY TARGETING POSITION SIZING

"""
Volatility targeting adjusts position sizes to maintain constant risk exposure.
This is the PREFERRED method for systematic strategies.

Formula:
Position_Size = (Target_Volatility / Realized_Volatility) * Base_Position
"""

def volatility_target_position(
    base_position: float,
    target_volatility: float,  # Annualized target (e.g., 0.15 = 15%)
    realized_volatility: float,  # Annualized realized vol
    max_leverage: float = 2.0,
    min_position: float = 0.0
) -> float:
    """
    Calculate position size based on volatility targeting.
    
    Args:
        base_position: Base position size without vol adjustment
        target_volatility: Target annualized volatility (e.g., 0.15)
        realized_volatility: Current realized volatility (annualized)
        max_leverage: Maximum allowed leverage multiplier
        min_position: Minimum position size (can be 0 for cash)
    
    Returns:
        Volatility-adjusted position size
    """
    if realized_volatility <= 0:
        return base_position
    
    vol_scalar = target_volatility / realized_volatility
    
    # Apply leverage constraints
    vol_scalar = min(vol_scalar, max_leverage)
    vol_scalar = max(vol_scalar, 0)  # No negative scaling
    
    adjusted_position = base_position * vol_scalar
    
    return max(adjusted_position, min_position)


## 1.3 STRATEGY-SPECIFIC POSITION SIZING RULES

"""
FEEDBACK REQUIREMENT IMPLEMENTATION:
- Never risk more than 2% on momentum trades
- Never risk more than 5% on "Safe Bet" Dividend Aristocrats
"""

POSITION_SIZE_LIMITS = {
    'momentum': {
        'max_position_pct': 0.02,  # 2% of portfolio
        'max_kelly_fraction': 0.20,  # 20% Kelly
        'target_volatility': 0.20,  # 20% annualized
        'stop_loss_pct': 0.08,  # 8% stop loss
    },
    'dividend_aristocrat': {
        'max_position_pct': 0.05,  # 5% of portfolio
        'max_kelly_fraction': 0.30,  # 30% Kelly
        'target_volatility': 0.12,  # 12% annualized
        'stop_loss_pct': 0.15,  # 15% stop loss (wider for value)
    },
    'mean_reversion': {
        'max_position_pct': 0.03,  # 3% of portfolio
        'max_kelly_fraction': 0.25,
        'target_volatility': 0.15,
        'stop_loss_pct': 0.05,  # Tight stop for mean reversion
    },
    'trend_following': {
        'max_position_pct': 0.04,  # 4% of portfolio
        'max_kelly_fraction': 0.25,
        'target_volatility': 0.18,
        'stop_loss_pct': 0.10,  # ATR-based trailing stop
    },
    'statistical_arbitrage': {
        'max_position_pct': 0.03,  # 3% of portfolio
        'max_kelly_fraction': 0.20,
        'target_volatility': 0.10,  # Lower vol target
        'stop_loss_pct': 0.06,
    }
}


def get_strategy_position_limits(strategy_type: str) -> dict:
    """
    Get position sizing parameters for a specific strategy type.
    
    Args:
        strategy_type: Type of trading strategy
    
    Returns:
        Dictionary with position sizing parameters
    """
    return POSITION_SIZE_LIMITS.get(strategy_type, POSITION_SIZE_LIMITS['momentum'])


## 1.4 RISK-BASED POSITION SIZING (ATR Method)

"""
Use Average True Range (ATR) to determine position size based on risk per share.

Formula:
Risk per share = Entry Price - Stop Price (based on ATR multiple)
Position Size = (Account Risk $) / (Risk per share)
"""

def atr_based_position_size(
    account_value: float,
    entry_price: float,
    atr_20: float,
    risk_per_trade_pct: float = 0.01,  # 1% of account per trade
    atr_multiple: float = 2.0,  # Stop at 2x ATR
    max_position_pct: float = 0.05  # Max 5% in single position
) -> dict:
    """
    Calculate position size based on ATR risk management.
    
    Args:
        account_value: Total account value
        entry_price: Planned entry price
        atr_20: 20-day Average True Range
        risk_per_trade_pct: Percentage of account to risk per trade
        atr_multiple: ATR multiplier for stop loss
        max_position_pct: Maximum position as % of account
    
    Returns:
        Dictionary with position details
    """
    # Calculate dollar risk amount
    dollar_risk = account_value * risk_per_trade_pct
    
    # Calculate stop loss price
    stop_price = entry_price - (atr_20 * atr_multiple)
    
    # Risk per share
    risk_per_share = entry_price - stop_price
    
    if risk_per_share <= 0:
        return {'shares': 0, 'position_value': 0, 'stop_price': 0}
    
    # Calculate number of shares
    shares = int(dollar_risk / risk_per_share)
    
    # Calculate position value
    position_value = shares * entry_price
    
    # Apply maximum position constraint
    max_position_value = account_value * max_position_pct
    if position_value > max_position_value:
        shares = int(max_position_value / entry_price)
        position_value = shares * entry_price
    
    return {
        'shares': shares,
        'position_value': position_value,
        'position_pct': position_value / account_value,
        'stop_price': stop_price,
        'dollar_risk': shares * risk_per_share,
        'risk_pct': (shares * risk_per_share) / account_value
    }


# =============================================================================
# SECTION 2: PORTFOLIO-LEVEL RISK CONTROLS
# =============================================================================

## 2.1 MAXIMUM DRAWDOWN CIRCUIT BREAKERS

"""
Drawdown circuit breakers progressively reduce exposure as losses accumulate.
This prevents catastrophic losses during extended drawdowns.
"""

DRAWDOWN_THRESHOLDS = {
    'level_1': {
        'drawdown_pct': 0.05,  # 5% drawdown
        'action': 'warning',
        'exposure_reduction': 0.0,  # No reduction, just alert
        'position_size_factor': 1.0
    },
    'level_2': {
        'drawdown_pct': 0.10,  # 10% drawdown
        'action': 'reduce',
        'exposure_reduction': 0.25,  # Reduce to 75% exposure
        'position_size_factor': 0.75
    },
    'level_3': {
        'drawdown_pct': 0.15,  # 15% drawdown
        'action': 'significant_reduce',
        'exposure_reduction': 0.50,  # Reduce to 50% exposure
        'position_size_factor': 0.50
    },
    'level_4': {
        'drawdown_pct': 0.20,  # 20% drawdown
        'action': 'severe_reduce',
        'exposure_reduction': 0.75,  # Reduce to 25% exposure
        'position_size_factor': 0.25
    },
    'level_5': {
        'drawdown_pct': 0.25,  # 25% drawdown
        'action': 'halt',
        'exposure_reduction': 1.0,  # Go to cash
        'position_size_factor': 0.0
    }
}


def check_drawdown_circuit_breaker(
    current_equity: float,
    peak_equity: float,
    current_exposure: float
) -> dict:
    """
    Check if drawdown circuit breaker should trigger.
    
    Args:
        current_equity: Current portfolio value
        peak_equity: Highest portfolio value achieved
        current_exposure: Current portfolio exposure (0-1)
    
    Returns:
        Dictionary with action and new exposure level
    """
    if peak_equity <= 0:
        return {'triggered': False, 'action': 'none', 'new_exposure': current_exposure}
    
    drawdown = (peak_equity - current_equity) / peak_equity
    
    # Check thresholds in reverse (highest first)
    for level_name, level_config in sorted(
        DRAWDOWN_THRESHOLDS.items(), 
        key=lambda x: x[1]['drawdown_pct'], 
        reverse=True
    ):
        if drawdown >= level_config['drawdown_pct']:
            new_exposure = current_exposure * (1 - level_config['exposure_reduction'])
            return {
                'triggered': True,
                'level': level_name,
                'drawdown_pct': drawdown,
                'action': level_config['action'],
                'new_exposure': new_exposure,
                'position_size_factor': level_config['position_size_factor']
            }
    
    return {
        'triggered': False,
        'action': 'none',
        'drawdown_pct': drawdown,
        'new_exposure': current_exposure,
        'position_size_factor': 1.0
    }


## 2.2 VALUE-AT-RISK (VaR) LIMITS

"""
VaR estimates potential loss at a given confidence level.
Use parametric (variance-covariance), historical, or Monte Carlo methods.
"""

import numpy as np
from scipy import stats

def calculate_var(
    positions: dict,  # {symbol: {'weight': float, 'returns': array}}
    confidence_level: float = 0.95,
    method: str = 'parametric',
    lookback_days: int = 252
) -> dict:
    """
    Calculate portfolio Value-at-Risk.
    
    Args:
        positions: Dictionary of positions with weights and return history
        confidence_level: VaR confidence level (e.g., 0.95 for 95%)
        method: 'parametric', 'historical', or 'monte_carlo'
        lookback_days: Historical lookback period
    
    Returns:
        Dictionary with VaR metrics
    """
    # Extract weights and returns
    symbols = list(positions.keys())
    weights = np.array([positions[s]['weight'] for s in symbols])
    
    # Build returns matrix
    returns_matrix = np.column_stack([
        positions[s]['returns'][-lookback_days:] 
        for s in symbols
    ])
    
    # Portfolio returns
    portfolio_returns = np.dot(returns_matrix, weights)
    
    if method == 'parametric':
        # Variance-covariance method
        mean_return = np.mean(portfolio_returns)
        std_return = np.std(portfolio_returns)
        z_score = stats.norm.ppf(1 - confidence_level)
        var = -(mean_return + z_score * std_return)
        
    elif method == 'historical':
        # Historical simulation
        var = -np.percentile(portfolio_returns, (1 - confidence_level) * 100)
        
    elif method == 'monte_carlo':
        # Monte Carlo simulation
        n_sims = 10000
        mean_return = np.mean(portfolio_returns)
        std_return = np.std(portfolio_returns)
        simulated = np.random.normal(mean_return, std_return, n_sims)
        var = -np.percentile(simulated, (1 - confidence_level) * 100)
    
    # Calculate CVaR (Expected Shortfall)
    cvar = -np.mean(portfolio_returns[portfolio_returns <= -var])
    
    return {
        'var_daily': var,
        'var_annualized': var * np.sqrt(252),
        'cvar_daily': cvar,
        'confidence_level': confidence_level,
        'method': method,
        'portfolio_volatility': np.std(portfolio_returns) * np.sqrt(252)
    }


## 2.3 RISK PARITY ALLOCATION

"""
Risk parity allocates capital such that each asset contributes equally to portfolio risk.
This creates a more balanced risk profile than equal weighting.
"""

def risk_parity_weights(
    cov_matrix: np.ndarray,
    asset_names: list,
    max_iterations: int = 100,
    tolerance: float = 1e-6
) -> dict:
    """
    Calculate risk parity portfolio weights using iterative approach.
    
    Args:
        cov_matrix: Covariance matrix of asset returns
        asset_names: List of asset names
        max_iterations: Maximum iterations for convergence
        tolerance: Convergence tolerance
    
    Returns:
        Dictionary with risk parity weights and risk contributions
    """
    n = len(asset_names)
    
    # Initialize equal weights
    weights = np.ones(n) / n
    
    for _ in range(max_iterations):
        # Calculate portfolio variance
        portfolio_var = np.dot(weights, np.dot(cov_matrix, weights))
        
        # Calculate marginal risk contributions
        marginal_risk = np.dot(cov_matrix, weights)
        
        # Calculate risk contributions
        risk_contrib = weights * marginal_risk / portfolio_var
        
        # Check convergence
        if np.std(risk_contrib) < tolerance:
            break
        
        # Update weights
        weights = weights * marginal_risk / portfolio_var
        weights = weights / np.sum(weights)
    
    return {
        'weights': dict(zip(asset_names, weights)),
        'risk_contributions': dict(zip(asset_names, risk_contrib)),
        'target_risk_contrib': 1.0 / n
    }


## 2.4 PORTFOLIO HEAT METRICS

"""
Portfolio heat measures total risk exposure. Keep heat within manageable bounds.
"""

def calculate_portfolio_heat(
    positions: dict,  # {symbol: {'weight': float, 'beta': float, 'volatility': float}}
    correlation_matrix: np.ndarray = None
) -> dict:
    """
    Calculate portfolio heat metrics.
    
    Args:
        positions: Dictionary of positions with risk attributes
        correlation_matrix: Correlation matrix between positions
    
    Returns:
        Dictionary with heat metrics
    """
    symbols = list(positions.keys())
    n = len(symbols)
    
    weights = np.array([positions[s]['weight'] for s in symbols])
    betas = np.array([positions[s].get('beta', 1.0) for s in symbols])
    vols = np.array([positions[s]['volatility'] for s in symbols])
    
    # Portfolio beta (market exposure)
    portfolio_beta = np.sum(weights * betas)
    
    # Gross exposure
    gross_exposure = np.sum(np.abs(weights))
    
    # Net exposure
    net_exposure = np.sum(weights)
    
    # Portfolio volatility
    if correlation_matrix is not None:
        cov_matrix = np.outer(vols, vols) * correlation_matrix
        portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
    else:
        # Assume uncorrelated for quick estimate
        portfolio_vol = np.sqrt(np.sum((weights * vols) ** 2))
    
    # Concentration metrics
    hhi = np.sum(weights ** 2)  # Herfindahl-Hirschman Index
    effective_n = 1 / hhi if hhi > 0 else 0
    
    return {
        'portfolio_beta': portfolio_beta,
        'gross_exposure': gross_exposure,
        'net_exposure': net_exposure,
        'portfolio_volatility': portfolio_vol,
        'concentration_hhi': hhi,
        'effective_n_positions': effective_n,
        'heat_score': gross_exposure * portfolio_vol  # Combined metric
    }


# =============================================================================
# SECTION 3: REGIME DETECTION METHODOLOGY
# =============================================================================

## 3.1 REGIME CLASSIFICATION FRAMEWORK

"""
Define market regimes based on multiple factors:
- Volatility regime (high/low)
- Trend regime (bull/bear/sideways)
- Interest rate regime (rising/falling/stable)
- Credit regime (tight/loose)
"""

REGIME_DEFINITIONS = {
    # Volatility Regimes
    'vol_low': {
        'vix_threshold': 20,
        'realized_vol_threshold': 0.15,
        'description': 'Low volatility environment'
    },
    'vol_high': {
        'vix_threshold': 30,
        'realized_vol_threshold': 0.25,
        'description': 'High volatility environment'
    },
    'vol_extreme': {
        'vix_threshold': 40,
        'realized_vol_threshold': 0.35,
        'description': 'Extreme volatility - crisis mode'
    },
    
    # Trend Regimes
    'trend_bull': {
        'sma_50_200_ratio': 1.05,  # 50-day > 200-day by 5%
        'price_sma200': 1.05,  # Price > 200-day SMA by 5%
        'description': 'Bull market'
    },
    'trend_bear': {
        'sma_50_200_ratio': 0.95,
        'price_sma200': 0.95,
        'description': 'Bear market'
    },
    
    # Rate Regimes
    'rates_rising': {
        'yield_change_3m': 0.005,  # 50bp increase
        'yield_trend': 'up',
        'description': 'Rising rate environment'
    },
    'rates_falling': {
        'yield_change_3m': -0.005,
        'yield_trend': 'down',
        'description': 'Falling rate environment'
    }
}


def detect_volatility_regime(
    vix_current: float,
    realized_vol_20d: float,
    historical_vix_percentile: float
) -> str:
    """
    Detect current volatility regime.
    
    Args:
        vix_current: Current VIX level
        realized_vol_20d: 20-day realized volatility (annualized)
        historical_vix_percentile: VIX percentile vs history
    
    Returns:
        Regime classification string
    """
    if vix_current > 40 or historical_vix_percentile > 95:
        return 'extreme'
    elif vix_current > 30 or historical_vix_percentile > 80:
        return 'high'
    elif vix_current > 20 or historical_vix_percentile > 50:
        return 'elevated'
    else:
        return 'low'


def detect_trend_regime(
    price: float,
    sma_50: float,
    sma_200: float,
    price_52w_high: float,
    price_52w_low: float
) -> dict:
    """
    Detect current trend regime.
    
    Args:
        price: Current price
        sma_50: 50-day simple moving average
        sma_200: 200-day simple moving average
        price_52w_high: 52-week high
        price_52w_low: 52-week low
    
    Returns:
        Dictionary with trend regime details
    """
    regime = {}
    
    # Golden cross / Death cross
    if sma_50 > sma_200 * 1.02:
        regime['primary'] = 'bull'
        regime['strength'] = 'strong' if price > sma_50 else 'weak'
    elif sma_50 < sma_200 * 0.98:
        regime['primary'] = 'bear'
        regime['strength'] = 'strong' if price < sma_50 else 'weak'
    else:
        regime['primary'] = 'neutral'
        regime['strength'] = 'sideways'
    
    # Distance from 52-week extremes
    pct_from_high = (price_52w_high - price) / price_52w_high
    pct_from_low = (price - price_52w_low) / price_52w_low
    
    regime['pct_from_52w_high'] = pct_from_high
    regime['pct_from_52w_low'] = pct_from_low
    regime['in_correction'] = pct_from_high > 0.10  # 10% from highs
    regime['in_bear_market'] = pct_from_high > 0.20  # 20% from highs
    
    return regime


def detect_interest_rate_regime(
    current_yield: float,
    yield_3m_ago: float,
    yield_1y_ago: float,
    yield_curve_spread: float  # 10Y - 2Y
) -> dict:
    """
    Detect interest rate regime.
    
    Args:
        current_yield: Current 10-year yield
        yield_3m_ago: Yield 3 months ago
        yield_1y_ago: Yield 1 year ago
        yield_curve_spread: 10Y-2Y spread
    
    Returns:
        Dictionary with rate regime details
    """
    regime = {}
    
    # Trend direction
    change_3m = current_yield - yield_3m_ago
    change_1y = current_yield - yield_1y_ago
    
    if change_3m > 0.005 and change_1y > 0.01:
        regime['direction'] = 'sharply_rising'
    elif change_3m > 0.0025:
        regime['direction'] = 'rising'
    elif change_3m < -0.005 and change_1y < -0.01:
        regime['direction'] = 'sharply_falling'
    elif change_3m < -0.0025:
        regime['direction'] = 'falling'
    else:
        regime['direction'] = 'stable'
    
    # Yield curve regime
    if yield_curve_spread < -0.0050:
        regime['curve'] = 'deeply_inverted'
        regime['recession_warning'] = True
    elif yield_curve_spread < -0.0025:
        regime['curve'] = 'inverted'
        regime['recession_warning'] = True
    elif yield_curve_spread < 0.0025:
        regime['curve'] = 'flat'
        regime['recession_warning'] = False
    else:
        regime['curve'] = 'steep'
        regime['recession_warning'] = False
    
    regime['level'] = 'high' if current_yield > 0.05 else 'low' if current_yield < 0.025 else 'moderate'
    
    return regime


## 3.2 COMPOSITE REGIME DETECTION

def detect_market_regime(
    market_data: dict
) -> dict:
    """
    Detect comprehensive market regime combining all factors.
    
    Args:
        market_data: Dictionary with market indicators
    
    Returns:
        Composite regime classification
    """
    # Detect individual regimes
    vol_regime = detect_volatility_regime(
        market_data.get('vix', 20),
        market_data.get('realized_vol_20d', 0.15),
        market_data.get('vix_percentile', 50)
    )
    
    trend_regime = detect_trend_regime(
        market_data.get('spy_price', 400),
        market_data.get('sma_50', 390),
        market_data.get('sma_200', 380),
        market_data.get('price_52w_high', 450),
        market_data.get('price_52w_low', 350)
    )
    
    rate_regime = detect_interest_rate_regime(
        market_data.get('yield_10y', 0.04),
        market_data.get('yield_10y_3m_ago', 0.038),
        market_data.get('yield_10y_1y_ago', 0.035),
        market_data.get('yield_curve_spread', 0.01)
    )
    
    # Composite regime classification
    composite = {
        'volatility': vol_regime,
        'trend': trend_regime['primary'],
        'rates': rate_regime['direction'],
        'yield_curve': rate_regime['curve'],
        'recession_warning': rate_regime['recession_warning']
    }
    
    # Determine overall regime
    if vol_regime == 'extreme' or trend_regime.get('in_bear_market'):
        composite['overall'] = 'crisis'
        composite['risk_level'] = 5
    elif vol_regime == 'high' or trend_regime['primary'] == 'bear':
        composite['overall'] = 'risk_off'
        composite['risk_level'] = 4
    elif rate_regime['recession_warning']:
        composite['overall'] = 'late_cycle'
        composite['risk_level'] = 3
    elif trend_regime['primary'] == 'bull' and vol_regime == 'low':
        composite['overall'] = 'goldilocks'
        composite['risk_level'] = 1
    else:
        composite['overall'] = 'neutral'
        composite['risk_level'] = 2
    
    return composite


## 3.3 REGIME-BASED ALLOCATION RULES

"""
Define how allocation should shift based on detected regime.
"""

REGIME_ALLOCATION_RULES = {
    'goldilocks': {  # Bull + Low Vol
        'max_equity_exposure': 1.0,
        'max_leverage': 1.5,
        'target_volatility': 0.15,
        'momentum_weight': 0.30,
        'value_weight': 0.25,
        'quality_weight': 0.20,
        'defensive_weight': 0.10,
        'cash_weight': 0.15,
        'hedge_ratio': 0.0
    },
    'neutral': {  # Mixed signals
        'max_equity_exposure': 0.85,
        'max_leverage': 1.2,
        'target_volatility': 0.12,
        'momentum_weight': 0.20,
        'value_weight': 0.25,
        'quality_weight': 0.25,
        'defensive_weight': 0.15,
        'cash_weight': 0.15,
        'hedge_ratio': 0.05
    },
    'late_cycle': {  # Recession warning
        'max_equity_exposure': 0.70,
        'max_leverage': 1.0,
        'target_volatility': 0.10,
        'momentum_weight': 0.10,
        'value_weight': 0.20,
        'quality_weight': 0.30,
        'defensive_weight': 0.25,
        'cash_weight': 0.15,
        'hedge_ratio': 0.10
    },
    'risk_off': {  # Bear or High Vol
        'max_equity_exposure': 0.50,
        'max_leverage': 1.0,
        'target_volatility': 0.08,
        'momentum_weight': 0.05,
        'value_weight': 0.15,
        'quality_weight': 0.25,
        'defensive_weight': 0.30,
        'cash_weight': 0.25,
        'hedge_ratio': 0.20
    },
    'crisis': {  # Extreme conditions
        'max_equity_exposure': 0.25,
        'max_leverage': 1.0,
        'target_volatility': 0.05,
        'momentum_weight': 0.0,
        'value_weight': 0.10,
        'quality_weight': 0.15,
        'defensive_weight': 0.25,
        'cash_weight': 0.50,
        'hedge_ratio': 0.40
    }
}


def get_regime_allocation(regime: str) -> dict:
    """
    Get allocation parameters for a given regime.
    
    Args:
        regime: Regime classification
    
    Returns:
        Dictionary with allocation rules
    """
    return REGIME_ALLOCATION_RULES.get(regime, REGIME_ALLOCATION_RULES['neutral'])


# =============================================================================
# SECTION 4: DYNAMIC LEVERAGE & VOLATILITY TARGETING
# =============================================================================

## 4.1 TARGET VOLATILITY FRAMEWORK

"""
Maintain constant portfolio volatility by adjusting leverage.
This is the cornerstone of modern risk management.
"""

class VolatilityTargeter:
    """
    Dynamic leverage based on realized volatility.
    """
    
    def __init__(
        self,
        target_volatility: float = 0.10,  # 10% annualized target
        max_leverage: float = 2.0,
        min_leverage: float = 0.0,
        vol_lookback: int = 20,
        smoothing_factor: float = 0.1  # EMA smoothing
    ):
        self.target_vol = target_volatility
        self.max_leverage = max_leverage
        self.min_leverage = min_leverage
        self.vol_lookback = vol_lookback
        self.smoothing = smoothing_factor
        self.current_leverage = 1.0
    
    def calculate_leverage(
        self,
        returns: np.ndarray,
        current_regime: str = 'neutral'
    ) -> float:
        """
        Calculate optimal leverage based on realized volatility.
        
        Args:
            returns: Array of historical returns
            current_regime: Current market regime
        
        Returns:
            Optimal leverage multiplier
        """
        # Calculate realized volatility
        if len(returns) < self.vol_lookback:
            return self.current_leverage
        
        realized_vol = np.std(returns[-self.vol_lookback:]) * np.sqrt(252)
        
        if realized_vol <= 0:
            return self.current_leverage
        
        # Target leverage
        target_leverage = self.target_vol / realized_vol
        
        # Apply regime adjustments
        regime_multipliers = {
            'goldilocks': 1.2,
            'neutral': 1.0,
            'late_cycle': 0.8,
            'risk_off': 0.6,
            'crisis': 0.3
        }
        
        regime_mult = regime_multipliers.get(current_regime, 1.0)
        target_leverage *= regime_mult
        
        # Apply constraints
        target_leverage = np.clip(
            target_leverage, 
            self.min_leverage, 
            self.max_leverage
        )
        
        # Smooth the adjustment
        self.current_leverage = (
            self.smoothing * target_leverage + 
            (1 - self.smoothing) * self.current_leverage
        )
        
        return self.current_leverage
    
    def apply_to_positions(
        self,
        base_positions: dict,
        leverage: float
    ) -> dict:
        """
        Apply leverage multiplier to all positions.
        
        Args:
            base_positions: Dictionary of base position weights
            leverage: Leverage multiplier
        
        Returns:
            Leverage-adjusted positions
        """
        return {
            symbol: weight * leverage 
            for symbol, weight in base_positions.items()
        }


## 4.2 LEVERAGE CONSTRAINTS BY REGIME

LEVERAGE_LIMITS = {
    'goldilocks': {
        'max_leverage': 2.0,
        'max_gross_exposure': 2.5,
        'max_single_position': 0.10,
        'margin_requirement': 0.25
    },
    'neutral': {
        'max_leverage': 1.5,
        'max_gross_exposure': 2.0,
        'max_single_position': 0.08,
        'margin_requirement': 0.30
    },
    'late_cycle': {
        'max_leverage': 1.2,
        'max_gross_exposure': 1.5,
        'max_single_position': 0.06,
        'margin_requirement': 0.35
    },
    'risk_off': {
        'max_leverage': 1.0,
        'max_gross_exposure': 1.2,
        'max_single_position': 0.05,
        'margin_requirement': 0.50
    },
    'crisis': {
        'max_leverage': 1.0,
        'max_gross_exposure': 1.0,
        'max_single_position': 0.03,
        'margin_requirement': 1.0  # No margin
    }
}


def check_leverage_constraints(
    positions: dict,
    regime: str,
    account_equity: float
) -> dict:
    """
    Check if positions comply with leverage constraints.
    
    Args:
        positions: Dictionary of positions
        regime: Current market regime
        account_equity: Total account equity
    
    Returns:
        Dictionary with constraint check results
    """
    limits = LEVERAGE_LIMITS.get(regime, LEVERAGE_LIMITS['neutral'])
    
    # Calculate metrics
    gross_exposure = sum(abs(p['weight']) for p in positions.values())
    net_exposure = sum(p['weight'] for p in positions.values())
    max_position = max(abs(p['weight']) for p in positions.values())
    
    leverage = gross_exposure  # Simplified leverage calculation
    
    violations = []
    
    if leverage > limits['max_leverage']:
        violations.append(f"Leverage {leverage:.2f} exceeds max {limits['max_leverage']}")
    
    if gross_exposure > limits['max_gross_exposure']:
        violations.append(f"Gross exposure {gross_exposure:.2f} exceeds max {limits['max_gross_exposure']}")
    
    if max_position > limits['max_single_position']:
        violations.append(f"Max position {max_position:.2%} exceeds limit {limits['max_single_position']:.2%}")
    
    return {
        'compliant': len(violations) == 0,
        'violations': violations,
        'leverage': leverage,
        'gross_exposure': gross_exposure,
        'net_exposure': net_exposure,
        'max_position': max_position,
        'limits': limits
    }


# =============================================================================
# SECTION 5: SPECIFIC RISK RULES & THRESHOLDS
# =============================================================================

## 5.1 PER-POSITION RISK LIMITS

POSITION_RISK_LIMITS = {
    # By Strategy Type
    'momentum': {
        'max_position_pct': 0.02,  # 2% max
        'max_risk_pct': 0.005,  # 0.5% risk per trade
        'max_concentration': 0.02,
        'stop_loss_type': 'trailing',
        'profit_target': 0.20,
        'time_stop_days': 30
    },
    'dividend_aristocrat': {
        'max_position_pct': 0.05,  # 5% max
        'max_risk_pct': 0.01,  # 1% risk per trade
        'max_concentration': 0.05,
        'stop_loss_type': 'fixed',
        'profit_target': 0.15,
        'time_stop_days': 90
    },
    'mean_reversion': {
        'max_position_pct': 0.03,
        'max_risk_pct': 0.005,
        'max_concentration': 0.03,
        'stop_loss_type': 'fixed',
        'profit_target': 0.08,
        'time_stop_days': 10
    },
    'trend_following': {
        'max_position_pct': 0.04,
        'max_risk_pct': 0.008,
        'max_concentration': 0.04,
        'stop_loss_type': 'atr_trailing',
        'profit_target': None,  # Let winners run
        'time_stop_days': None
    },
    'statistical_arbitrage': {
        'max_position_pct': 0.03,
        'max_risk_pct': 0.003,
        'max_concentration': 0.03,
        'stop_loss_type': 'fixed',
        'profit_target': 0.05,
        'time_stop_days': 20
    }
}


## 5.2 SECTOR/INDUSTRY CONCENTRATION LIMITS

SECTOR_LIMITS = {
    'technology': {
        'max_pct': 0.25,
        'max_single_stock': 0.05,
        'beta_adjusted_max': 0.30
    },
    'healthcare': {
        'max_pct': 0.20,
        'max_single_stock': 0.05,
        'beta_adjusted_max': 0.25
    },
    'financials': {
        'max_pct': 0.20,
        'max_single_stock': 0.04,
        'beta_adjusted_max': 0.25
    },
    'consumer_discretionary': {
        'max_pct': 0.15,
        'max_single_stock': 0.04,
        'beta_adjusted_max': 0.20
    },
    'industrials': {
        'max_pct': 0.15,
        'max_single_stock': 0.04,
        'beta_adjusted_max': 0.18
    },
    'energy': {
        'max_pct': 0.10,
        'max_single_stock': 0.03,
        'beta_adjusted_max': 0.12
    },
    'utilities': {
        'max_pct': 0.10,
        'max_single_stock': 0.03,
        'beta_adjusted_max': 0.10
    },
    'consumer_staples': {
        'max_pct': 0.10,
        'max_single_stock': 0.03,
        'beta_adjusted_max': 0.10
    },
    'materials': {
        'max_pct': 0.08,
        'max_single_stock': 0.03,
        'beta_adjusted_max': 0.08
    },
    'real_estate': {
        'max_pct': 0.08,
        'max_single_stock': 0.03,
        'beta_adjusted_max': 0.08
    },
    'communication_services': {
        'max_pct': 0.10,
        'max_single_stock': 0.03,
        'beta_adjusted_max': 0.10
    }
}


def check_sector_concentration(
    positions: dict,  # {symbol: {'weight': float, 'sector': str, 'beta': float}}
    sector_limits: dict = None
) -> dict:
    """
    Check sector concentration against limits.
    
    Args:
        positions: Dictionary of positions with sector info
        sector_limits: Sector limit configuration
    
    Returns:
        Dictionary with concentration analysis
    """
    if sector_limits is None:
        sector_limits = SECTOR_LIMITS
    
    # Aggregate by sector
    sector_exposure = {}
    for symbol, pos in positions.items():
        sector = pos.get('sector', 'unknown')
        weight = pos.get('weight', 0)
        beta = pos.get('beta', 1.0)
        
        if sector not in sector_exposure:
            sector_exposure[sector] = {
                'total_weight': 0,
                'beta_adjusted': 0,
                'stocks': []
            }
        
        sector_exposure[sector]['total_weight'] += weight
        sector_exposure[sector]['beta_adjusted'] += weight * beta
        sector_exposure[sector]['stocks'].append({
            'symbol': symbol,
            'weight': weight,
            'beta': beta
        })
    
    # Check limits
    violations = []
    for sector, exposure in sector_exposure.items():
        limits = sector_limits.get(sector, {'max_pct': 0.15, 'max_single_stock': 0.03})
        
        if exposure['total_weight'] > limits['max_pct']:
            violations.append({
                'type': 'sector_limit',
                'sector': sector,
                'current': exposure['total_weight'],
                'limit': limits['max_pct']
            })
        
        # Check single stock limit within sector
        max_stock = max(s['weight'] for s in exposure['stocks'])
        if max_stock > limits['max_single_stock']:
            violations.append({
                'type': 'single_stock',
                'sector': sector,
                'current': max_stock,
                'limit': limits['max_single_stock']
            })
    
    return {
        'sector_exposure': sector_exposure,
        'violations': violations,
        'compliant': len(violations) == 0
    }


## 5.3 CORRELATION-BASED POSITION ADJUSTMENTS

"""
Reduce position sizes when correlations spike (diversification breaks down).
"""

def calculate_portfolio_correlation_stress(
    returns_matrix: np.ndarray,
    lookback: int = 60
) -> dict:
    """
    Calculate correlation stress metrics.
    
    Args:
        returns_matrix: Matrix of asset returns (T x N)
        lookback: Lookback period for correlation calculation
    
    Returns:
        Dictionary with correlation stress metrics
    """
    if len(returns_matrix) < lookback:
        return {'stress_level': 'unknown', 'avg_correlation': 0}
    
    recent_returns = returns_matrix[-lookback:]
    
    # Calculate correlation matrix
    corr_matrix = np.corrcoef(recent_returns.T)
    
    # Average pairwise correlation (excluding diagonal)
    mask = ~np.eye(corr_matrix.shape[0], dtype=bool)
    avg_corr = np.mean(np.abs(corr_matrix[mask]))
    
    # Determine stress level
    if avg_corr > 0.8:
        stress_level = 'extreme'
        position_reduction = 0.50
    elif avg_corr > 0.7:
        stress_level = 'high'
        position_reduction = 0.30
    elif avg_corr > 0.6:
        stress_level = 'elevated'
        position_reduction = 0.15
    else:
        stress_level = 'normal'
        position_reduction = 0.0
    
    return {
        'avg_correlation': avg_corr,
        'stress_level': stress_level,
        'position_reduction': position_reduction,
        'correlation_matrix': corr_matrix
    }


def adjust_positions_for_correlation(
    positions: dict,
    returns_matrix: np.ndarray,
    max_correlation: float = 0.70
) -> dict:
    """
    Adjust position sizes based on correlation stress.
    
    Args:
        positions: Current positions
        returns_matrix: Historical returns
        max_correlation: Maximum acceptable average correlation
    
    Returns:
        Correlation-adjusted positions
    """
    stress = calculate_portfolio_correlation_stress(returns_matrix)
    
    reduction_factor = 1 - stress['position_reduction']
    
    adjusted_positions = {}
    for symbol, pos in positions.items():
        adjusted_positions[symbol] = {
            **pos,
            'original_weight': pos['weight'],
            'weight': pos['weight'] * reduction_factor,
            'correlation_adjustment': reduction_factor
        }
    
    return {
        'positions': adjusted_positions,
        'stress_metrics': stress,
        'total_reduction': 1 - reduction_factor
    }


## 5.4 LIQUIDITY FILTERS

LIQUIDITY_REQUIREMENTS = {
    'minimums': {
        'avg_daily_volume': 500000,  # Shares
        'avg_daily_dollar_volume': 10000000,  # $10M
        'max_bid_ask_spread_pct': 0.005,  # 0.5%
        'min_market_cap_millions': 500  # $500M
    },
    'position_sizing': {
        'max_position_days_volume': 0.10,  # Position <= 10% of daily volume
        'max_impact_bps': 50,  # Max 50 bps market impact
        'max_slippage_pct': 0.001  # Max 0.1% slippage
    }
}


def check_liquidity(
    symbol: str,
    position_size: int,
    liquidity_data: dict
) -> dict:
    """
    Check if position meets liquidity requirements.
    
    Args:
        symbol: Stock symbol
        position_size: Number of shares
        liquidity_data: Dictionary with liquidity metrics
    
    Returns:
        Liquidity check results
    """
    reqs = LIQUIDITY_REQUIREMENTS
    violations = []
    
    # Check minimum volume
    if liquidity_data.get('avg_volume', 0) < reqs['minimums']['avg_daily_volume']:
        violations.append('Insufficient average volume')
    
    # Check dollar volume
    if liquidity_data.get('avg_dollar_volume', 0) < reqs['minimums']['avg_daily_dollar_volume']:
        violations.append('Insufficient dollar volume')
    
    # Check spread
    if liquidity_data.get('spread_pct', 1) > reqs['minimums']['max_bid_ask_spread_pct']:
        violations.append('Spread too wide')
    
    # Check market cap
    if liquidity_data.get('market_cap_millions', 0) < reqs['minimums']['min_market_cap_millions']:
        violations.append('Market cap too small')
    
    # Check position size vs volume
    position_vs_volume = position_size / liquidity_data.get('avg_volume', 1)
    if position_vs_volume > reqs['position_sizing']['max_position_days_volume']:
        violations.append(f'Position {position_vs_volume:.1%} of daily volume exceeds limit')
    
    return {
        'symbol': symbol,
        'liquid': len(violations) == 0,
        'violations': violations,
        'position_vs_volume': position_vs_volume,
        'liquidity_score': calculate_liquidity_score(liquidity_data)
    }


def calculate_liquidity_score(liquidity_data: dict) -> float:
    """
    Calculate composite liquidity score (0-100).
    """
    score = 100
    
    # Volume score
    vol_ratio = liquidity_data.get('avg_volume', 0) / 500000
    score *= min(vol_ratio, 1.0)
    
    # Spread score
    spread = liquidity_data.get('spread_pct', 0.01)
    score *= max(0, 1 - spread * 100)
    
    # Market cap score
    cap_ratio = liquidity_data.get('market_cap_millions', 500) / 500
    score *= min(cap_ratio, 1.0)
    
    return min(score, 100)


## 5.5 TURNOVER CONSTRAINTS

TURNOVER_LIMITS = {
    'per_trade': {
        'max_single_trade_pct': 0.10,  # Max 10% in single trade
        'min_holding_days': 1  # No day trading
    },
    'daily': {
        'max_daily_turnover_pct': 0.20,  # Max 20% daily
        'max_daily_trades': 10
    },
    'monthly': {
        'max_monthly_turnover_pct': 1.0,  # Max 100% monthly
        'max_monthly_trades': 50
    },
    'annual': {
        'max_annual_turnover': 5.0,  # Max 5x annual turnover
        'target_annual_turnover': 2.0  # Target 2x
    }
}


def check_turnover_constraints(
    proposed_trades: list,
    trade_history: list,
    portfolio_value: float
) -> dict:
    """
    Check if proposed trades comply with turnover limits.
    
    Args:
        proposed_trades: List of proposed trades
        trade_history: Historical trades
        portfolio_value: Current portfolio value
    
    Returns:
        Turnover constraint check results
    """
    violations = []
    
    # Calculate proposed daily turnover
    daily_turnover = sum(t['value'] for t in proposed_trades) / portfolio_value
    
    if daily_turnover > TURNOVER_LIMITS['daily']['max_daily_turnover_pct']:
        violations.append(f'Daily turnover {daily_turnover:.1%} exceeds limit')
    
    if len(proposed_trades) > TURNOVER_LIMITS['daily']['max_daily_trades']:
        violations.append(f'Too many daily trades: {len(proposed_trades)}')
    
    # Check single trade size
    for trade in proposed_trades:
        trade_pct = trade['value'] / portfolio_value
        if trade_pct > TURNOVER_LIMITS['per_trade']['max_single_trade_pct']:
            violations.append(f'Trade {trade["symbol"]} size {trade_pct:.1%} exceeds limit')
    
    return {
        'compliant': len(violations) == 0,
        'violations': violations,
        'daily_turnover': daily_turnover,
        'num_trades': len(proposed_trades)
    }


# =============================================================================
# SECTION 6: META-LEARNER RISK ALLOCATOR
# =============================================================================

"""
The Meta-Learner dynamically allocates capital across strategies based on:
- Recent performance (momentum of returns)
- Regime alignment (which strategies work in current regime)
- Risk-adjusted metrics (Sharpe, Sortino, Calmar)
- Correlation structure (avoid correlated strategies during stress)
"""

class MetaLearnerRiskAllocator:
    """
    Dynamic strategy allocation based on performance and regime.
    """
    
    def __init__(
        self,
        strategies: list,
        lookback_window: int = 63,  # 3 months
        performance_weight: float = 0.4,
        regime_weight: float = 0.3,
        risk_weight: float = 0.3,
        min_allocation: float = 0.05,
        max_allocation: float = 0.50,
        rebalance_frequency: str = 'weekly'
    ):
        self.strategies = strategies
        self.lookback = lookback_window
        self.weights = {
            'performance': performance_weight,
            'regime': regime_weight,
            'risk': risk_weight
        }
        self.min_alloc = min_allocation
        self.max_alloc = max_allocation
        self.rebalance_freq = rebalance_frequency
        self.current_allocations = {s: 1.0/len(strategies) for s in strategies}
    
    def calculate_performance_score(
        self,
        strategy_returns: np.ndarray
    ) -> float:
        """
        Calculate performance-based allocation score.
        
        Uses risk-adjusted returns with recency weighting.
        """
        if len(strategy_returns) < 20:
            return 0.5
        
        # Recent performance (last 20 days)
        recent_returns = strategy_returns[-20:]
        recent_sharpe = np.mean(recent_returns) / (np.std(recent_returns) + 1e-8)
        
        # Medium-term performance
        medium_returns = strategy_returns[-self.lookback:]
        medium_sharpe = np.mean(medium_returns) / (np.std(medium_returns) + 1e-8)
        
        # Weight recent more heavily
        score = 0.6 * recent_sharpe + 0.4 * medium_sharpe
        
        # Normalize to 0-1 range
        score = 1 / (1 + np.exp(-score))  # Sigmoid
        
        return score
    
    def calculate_regime_score(
        self,
        strategy_type: str,
        current_regime: str
    ) -> float:
        """
        Calculate regime alignment score.
        
        Based on historical strategy performance in similar regimes.
        """
        # Regime-strategy compatibility matrix
        compatibility = {
            'momentum': {
                'goldilocks': 1.0,
                'neutral': 0.7,
                'late_cycle': 0.4,
                'risk_off': 0.2,
                'crisis': 0.0
            },
            'dividend_aristocrat': {
                'goldilocks': 0.6,
                'neutral': 0.8,
                'late_cycle': 0.9,
                'risk_off': 0.7,
                'crisis': 0.5
            },
            'mean_reversion': {
                'goldilocks': 0.4,
                'neutral': 0.7,
                'late_cycle': 0.6,
                'risk_off': 0.8,
                'crisis': 0.3
            },
            'trend_following': {
                'goldilocks': 0.9,
                'neutral': 0.8,
                'late_cycle': 0.5,
                'risk_off': 0.6,
                'crisis': 0.4
            },
            'statistical_arbitrage': {
                'goldilocks': 0.7,
                'neutral': 0.8,
                'late_cycle': 0.6,
                'risk_off': 0.5,
                'crisis': 0.2
            }
        }
        
        return compatibility.get(strategy_type, {}).get(current_regime, 0.5)
    
    def calculate_risk_score(
        self,
        strategy_returns: np.ndarray,
        max_drawdown: float
    ) -> float:
        """
        Calculate risk-based allocation score.
        
        Higher score for better risk-adjusted metrics.
        """
        if len(strategy_returns) < 20:
            return 0.5
        
        # Sharpe ratio
        sharpe = np.mean(strategy_returns) / (np.std(strategy_returns) + 1e-8)
        
        # Sortino ratio (downside deviation)
        downside_returns = strategy_returns[strategy_returns < 0]
        downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 1e-8
        sortino = np.mean(strategy_returns) / downside_std
        
        # Calmar ratio (return / max drawdown)
        calmar = np.mean(strategy_returns) * 252 / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Combined risk score
        score = (sharpe + sortino + calmar) / 3
        
        # Normalize
        score = 1 / (1 + np.exp(-score))
        
        return score
    
    def calculate_correlation_penalty(
        self,
        strategy_returns: dict
    ) -> dict:
        """
        Calculate correlation-based penalties.
        
        Reduce allocation to highly correlated strategies.
        """
        symbols = list(strategy_returns.keys())
        returns_matrix = np.column_stack([strategy_returns[s] for s in symbols])
        
        # Calculate correlation matrix
        corr_matrix = np.corrcoef(returns_matrix.T)
        
        penalties = {}
        for i, s1 in enumerate(symbols):
            # Average correlation with other strategies
            avg_corr = np.mean([corr_matrix[i][j] for j in range(len(symbols)) if i != j])
            
            # Penalty increases with correlation
            penalty = min(avg_corr * 0.5, 0.3)  # Max 30% penalty
            penalties[s1] = 1 - penalty
        
        return penalties
    
    def allocate(
        self,
        strategy_returns: dict,  # {strategy_name: returns_array}
        current_regime: str,
        strategy_types: dict,  # {strategy_name: type}
        max_drawdowns: dict  # {strategy_name: max_dd}
    ) -> dict:
        """
        Calculate optimal strategy allocations.
        
        Args:
            strategy_returns: Dictionary of strategy return series
            current_regime: Current market regime
            strategy_types: Dictionary mapping strategies to types
            max_drawdowns: Dictionary of strategy max drawdowns
        
        Returns:
            Dictionary with optimal allocations
        """
        scores = {}
        
        for strategy in self.strategies:
            returns = strategy_returns.get(strategy, np.array([]))
            
            # Performance score
            perf_score = self.calculate_performance_score(returns)
            
            # Regime score
            strategy_type = strategy_types.get(strategy, 'momentum')
            regime_score = self.calculate_regime_score(strategy_type, current_regime)
            
            # Risk score
            max_dd = max_drawdowns.get(strategy, -0.10)
            risk_score = self.calculate_risk_score(returns, max_dd)
            
            # Combined score
            combined = (
                self.weights['performance'] * perf_score +
                self.weights['regime'] * regime_score +
                self.weights['risk'] * risk_score
            )
            
            scores[strategy] = combined
        
        # Apply correlation penalties
        penalties = self.calculate_correlation_penalty(strategy_returns)
        for strategy in scores:
            scores[strategy] *= penalties.get(strategy, 1.0)
        
        # Convert scores to allocations
        total_score = sum(scores.values())
        if total_score > 0:
            allocations = {s: scores[s] / total_score for s in self.strategies}
        else:
            allocations = {s: 1.0 / len(self.strategies) for s in self.strategies}
        
        # Apply min/max constraints
        allocations = self._apply_allocation_constraints(allocations)
        
        # Normalize to sum to 1
        total = sum(allocations.values())
        allocations = {s: allocations[s] / total for s in allocations}
        
        self.current_allocations = allocations
        
        return {
            'allocations': allocations,
            'scores': scores,
            'penalties': penalties
        }
    
    def _apply_allocation_constraints(self, allocations: dict) -> dict:
        """Apply min/max allocation constraints."""
        constrained = allocations.copy()
        
        # Apply minimum
        for s in constrained:
            constrained[s] = max(constrained[s], self.min_alloc)
        
        # Apply maximum
        for s in constrained:
            constrained[s] = min(constrained[s], self.max_alloc)
        
        return constrained
    
    def should_reduce_exposure(
        self,
        portfolio_metrics: dict,
        current_regime: str
    ) -> dict:
        """
        Determine if overall exposure should be reduced or shifted to cash.
        
        Args:
            portfolio_metrics: Current portfolio metrics
            current_regime: Current market regime
        
        Returns:
            Dictionary with exposure adjustment recommendation
        """
        # Cash allocation rules by regime
        cash_rules = {
            'goldilocks': 0.10,
            'neutral': 0.15,
            'late_cycle': 0.20,
            'risk_off': 0.30,
            'crisis': 0.50
        }
        
        target_cash = cash_rules.get(current_regime, 0.15)
        
        # Adjust for drawdown
        current_dd = portfolio_metrics.get('current_drawdown', 0)
        if current_dd > 0.10:
            target_cash += 0.10
        if current_dd > 0.15:
            target_cash += 0.15
        
        # Adjust for VaR breach
        var_breach = portfolio_metrics.get('var_breach', False)
        if var_breach:
            target_cash += 0.10
        
        # Cap at 70%
        target_cash = min(target_cash, 0.70)
        
        return {
            'target_cash_allocation': target_cash,
            'target_equity_allocation': 1 - target_cash,
            'reduce_exposure': target_cash > 0.25,
            'reason': f'Regime: {current_regime}, Drawdown: {current_dd:.1%}'
        }


## 6.2 STRATEGY CORRELATION HANDLING DURING STRESS

"""
When correlations spike during stress, traditional diversification fails.
Implement correlation-based hedging and exposure reduction.
"""

def handle_stress_correlations(
    strategy_returns: dict,
    current_allocations: dict,
    stress_threshold: float = 0.75
) -> dict:
    """
    Adjust allocations when strategy correlations spike.
    
    Args:
        strategy_returns: Dictionary of strategy returns
        current_allocations: Current strategy allocations
        stress_threshold: Correlation threshold for stress mode
    
    Returns:
        Adjusted allocations and hedging recommendations
    """
    # Calculate correlation matrix
    symbols = list(strategy_returns.keys())
    returns_matrix = np.column_stack([strategy_returns[s] for s in symbols])
    corr_matrix = np.corrcoef(returns_matrix.T)
    
    # Average correlation
    mask = ~np.eye(corr_matrix.shape[0], dtype=bool)
    avg_corr = np.mean(np.abs(corr_matrix[mask]))
    
    if avg_corr < stress_threshold:
        return {
            'stress_mode': False,
            'allocations': current_allocations,
            'hedge_ratio': 0.0
        }
    
    # Stress mode - reduce correlated strategies
    stress_allocations = current_allocations.copy()
    
    # Find most correlated strategy pairs
    high_corr_pairs = []
    for i in range(len(symbols)):
        for j in range(i+1, len(symbols)):
            if abs(corr_matrix[i][j]) > stress_threshold:
                high_corr_pairs.append((symbols[i], symbols[j], corr_matrix[i][j]))
    
    # Reduce allocation to highly correlated strategies
    for s1, s2, corr in high_corr_pairs:
        # Reduce both strategies
        reduction = (corr - stress_threshold) * 0.5
        stress_allocations[s1] *= (1 - reduction)
        stress_allocations[s2] *= (1 - reduction)
    
    # Normalize
    total = sum(stress_allocations.values())
    stress_allocations = {s: stress_allocations[s] / total for s in stress_allocations}
    
    # Increase hedge ratio
    hedge_ratio = min((avg_corr - stress_threshold) * 2, 0.50)
    
    return {
        'stress_mode': True,
        'avg_correlation': avg_corr,
        'high_correlation_pairs': high_corr_pairs,
        'allocations': stress_allocations,
        'hedge_ratio': hedge_ratio,
        'recommended_hedge': 'SPY_puts' if hedge_ratio > 0.2 else 'VIX_calls'
    }


# =============================================================================
# SECTION 7: PYTHON IMPLEMENTATION - COMPLETE RISK MANAGER CLASS
# =============================================================================

class ComprehensiveRiskManager:
    """
    Complete risk management system integrating all components.
    """
    
    def __init__(
        self,
        account_value: float,
        target_volatility: float = 0.12,
        max_drawdown_limit: float = 0.20
    ):
        self.account_value = account_value
        self.target_vol = target_volatility
        self.max_dd_limit = max_drawdown_limit
        
        # Initialize sub-components
        self.vol_targeter = VolatilityTargeter(target_volatility=target_volatility)
        self.meta_allocator = MetaLearnerRiskAllocator(
            strategies=['momentum', 'dividend', 'mean_reversion', 'trend', 'stat_arb']
        )
        
        # State tracking
        self.peak_equity = account_value
        self.current_drawdown = 0
        self.current_regime = 'neutral'
        self.circuit_breaker_active = False
        
    def pre_trade_risk_check(
        self,
        symbol: str,
        strategy_type: str,
        entry_price: float,
        stop_price: float,
        position_data: dict
    ) -> dict:
        """
        Comprehensive pre-trade risk check.
        """
        results = {
            'approved': True,
            'symbol': symbol,
            'violations': [],
            'warnings': [],
            'adjusted_size': None
        }
        
        # 1. Check position limits by strategy
        limits = get_strategy_position_limits(strategy_type)
        max_position_value = self.account_value * limits['max_position_pct']
        
        # 2. Calculate risk per trade
        risk_per_share = entry_price - stop_price
        if risk_per_share <= 0:
            results['approved'] = False
            results['violations'].append('Invalid stop loss')
            return results
        
        # 3. Calculate position size
        dollar_risk = self.account_value * limits['max_risk_pct']
        shares = int(dollar_risk / risk_per_share)
        position_value = shares * entry_price
        
        # 4. Check against max position
        if position_value > max_position_value:
            shares = int(max_position_value / entry_price)
            position_value = shares * entry_price
            results['warnings'].append('Position size reduced to max limit')
        
        # 5. Check liquidity
        liquidity_check = check_liquidity(symbol, shares, position_data.get('liquidity', {}))
        if not liquidity_check['liquid']:
            results['approved'] = False
            results['violations'].extend(liquidity_check['violations'])
        
        # 6. Check sector concentration
        sector_check = check_sector_concentration(
            position_data.get('current_positions', {})
        )
        if not sector_check['compliant']:
            results['warnings'].append('Sector concentration warning')
        
        # 7. Check drawdown circuit breaker
        if self.circuit_breaker_active:
            results['approved'] = False
            results['violations'].append('Circuit breaker active - no new trades')
        
        results['adjusted_size'] = {
            'shares': shares,
            'position_value': position_value,
            'position_pct': position_value / self.account_value,
            'dollar_risk': shares * risk_per_share,
            'risk_pct': (shares * risk_per_share) / self.account_value
        }
        
        return results
    
    def update_portfolio_state(
        self,
        current_equity: float,
        market_data: dict,
        strategy_returns: dict
    ) -> dict:
        """
        Update portfolio state and check all risk controls.
        """
        self.account_value = current_equity
        
        # Update peak equity and drawdown
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        
        self.current_drawdown = (self.peak_equity - current_equity) / self.peak_equity
        
        # Detect regime
        self.current_regime = detect_market_regime(market_data)['overall']
        
        # Check circuit breaker
        cb_result = check_drawdown_circuit_breaker(
            current_equity, self.peak_equity, 1.0
        )
        self.circuit_breaker_active = cb_result['triggered']
        
        # Calculate portfolio heat
        portfolio_heat = calculate_portfolio_heat(
            market_data.get('positions', {}),
            market_data.get('correlation_matrix')
        )
        
        # Calculate VaR
        var_result = calculate_var(
            market_data.get('positions', {}),
            confidence_level=0.95
        )
        
        # Check correlation stress
        if 'returns_matrix' in market_data:
            stress = calculate_portfolio_correlation_stress(market_data['returns_matrix'])
        else:
            stress = {'stress_level': 'unknown'}
        
        # Calculate optimal leverage
        if 'portfolio_returns' in market_data:
            optimal_leverage = self.vol_targeter.calculate_leverage(
                market_data['portfolio_returns'],
                self.current_regime
            )
        else:
            optimal_leverage = 1.0
        
        # Meta-learner allocation
        allocation = self.meta_allocator.allocate(
            strategy_returns,
            self.current_regime,
            market_data.get('strategy_types', {}),
            market_data.get('max_drawdowns', {})
        )
        
        # Cash allocation recommendation
        cash_rec = self.meta_allocator.should_reduce_exposure(
            {
                'current_drawdown': self.current_drawdown,
                'var_breach': var_result['var_daily'] > 0.02
            },
            self.current_regime
        )
        
        return {
            'current_equity': current_equity,
            'peak_equity': self.peak_equity,
            'current_drawdown': self.current_drawdown,
            'current_regime': self.current_regime,
            'circuit_breaker': cb_result,
            'portfolio_heat': portfolio_heat,
            'var': var_result,
            'correlation_stress': stress,
            'optimal_leverage': optimal_leverage,
            'strategy_allocations': allocation,
            'cash_recommendation': cash_rec
        }


# =============================================================================
# SECTION 8: QUICK REFERENCE - KEY FORMULAS
# =============================================================================

"""
## Position Sizing Formulas

### Kelly Criterion
K = (p*b - q) / b
Where: p = win rate, q = 1-p, b = avg win / avg loss

### Fractional Kelly (Recommended)
Position = K * f
Where: f = fraction (0.15-0.30 recommended)

### Volatility Targeting
Leverage = Target_Vol / Realized_Vol
Position_Size = Base_Position * Leverage

### ATR-Based Sizing
Shares = (Account * Risk%) / (ATR * ATR_Multiple)

## Risk Metrics

### Value at Risk (Parametric)
VaR = -(u + z*o)
Where: u = mean return, o = std dev, z = confidence z-score

### Expected Shortfall (CVaR)
CVaR = E[X | X <= -VaR]

### Portfolio Volatility
op = sqrt(w'Zw)
Where: w = weight vector, Z = covariance matrix

### Maximum Drawdown
MDD = max((Peak - Trough) / Peak)

## Regime Detection

### Volatility Regime
if VIX > 40: extreme
elif VIX > 30: high
elif VIX > 20: elevated
else: low

### Trend Regime
if SMA50 > SMA200 * 1.02: bull
elif SMA50 < SMA200 * 0.98: bear
else: neutral

## Risk Limits Summary

| Metric | Conservative | Moderate | Aggressive |
|--------|-------------|----------|------------|
| Max Position | 2% | 3% | 5% |
| Max Sector | 15% | 20% | 25% |
| Max Drawdown | 15% | 20% | 25% |
| Daily VaR | 1% | 2% | 3% |
| Max Leverage | 1.2x | 1.5x | 2.0x |
| Kelly Fraction | 15% | 25% | 40% |

"""

# =============================================================================
# END OF RISK MANAGEMENT FRAMEWORK
# =============================================================================
