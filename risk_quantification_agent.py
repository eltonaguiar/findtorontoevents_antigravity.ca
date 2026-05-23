#!/usr/bin/env python3
"""
Risk Quantification Agent
=========================
Industry-standard portfolio risk management system implementing VaR, stress testing,
portfolio optimization, and dynamic risk controls.

Features:
- Historical VaR/CVaR calculations (252-day rolling window)
- Monte Carlo stress testing for market scenarios
- Modern portfolio theory optimization
- Dynamic risk limits based on volatility
- Risk attribution by asset, strategy, and time horizon
- Real-time risk monitoring and alerts
- Web dashboard for risk visualization
- API endpoints for risk queries

Author: AI Assistant
Date: 2026
"""

import asyncio
import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import statistics
import random
import math

# Required imports
import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize
import requests

# Optional imports with fallbacks
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    class FastAPI:
        def __init__(self, **kwargs): self.routes = []
        def get(self, path): return lambda func: None
        def post(self, path): return lambda func: None
    class HTMLResponse: pass
    def uvicorn_run(app, **kwargs): logger.info("Mock uvicorn - web server not started")

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    class MockPool:
        async def close(self): pass
        async def fetchrow(self, query, *args): return None
        async def fetch(self, query, *args): return []
        async def execute(self, query, *args): pass

try:
    import aioredis
    AIREDIS_AVAILABLE = True
except ImportError:
    AIREDIS_AVAILABLE = False
    class MockRedis:
        async def from_url(self, url): return self
        async def close(self): pass
        async def publish(self, channel, message): pass
        async def set(self, key, value): pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('risk_quantification.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION & DATA MODELS
# ============================================================================

class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class StressScenario(Enum):
    MARKET_CRASH = "MARKET_CRASH"
    VOLATILITY_SPIKE = "VOLATILITY_SPIKE"
    LIQUIDITY_CRISIS = "LIQUIDITY_CRISIS"
    SECTOR_CRASH = "SECTOR_CRASH"
    GEOPOLITICAL = "GEOPOLITICAL"

@dataclass
class RiskConfig:
    """Risk management configuration"""
    # VaR settings
    var_confidence_level: float = 0.95
    var_horizon_days: int = 1
    var_window_days: int = 252

    # Portfolio limits
    max_portfolio_var: float = 0.05  # 5% max VaR
    max_single_position_var: float = 0.02  # 2% max position VaR
    max_correlation_threshold: float = 0.8

    # Risk monitoring
    risk_update_interval_seconds: float = 60.0
    alert_cooldown_minutes: int = 10

    # Optimization settings
    target_return: float = 0.15  # 15% annual target
    risk_free_rate: float = 0.03  # 3% risk-free rate

    # Stress testing
    monte_carlo_simulations: int = 10000
    stress_test_scenarios: List[StressScenario] = field(default_factory=lambda: [
        StressScenario.MARKET_CRASH,
        StressScenario.VOLATILITY_SPIKE,
        StressScenario.LIQUIDITY_CRISIS
    ])

@dataclass
class PortfolioPosition:
    """Portfolio position with risk metrics"""
    symbol: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    weight: float
    var_contribution: float = 0.0
    cvar_contribution: float = 0.0
    beta: float = 1.0
    volatility: float = 0.0

@dataclass
class Portfolio:
    """Portfolio with risk metrics"""
    positions: Dict[str, PortfolioPosition]
    total_value: float
    cash: float
    total_var: float
    total_cvar: float
    sharpe_ratio: float
    diversification_ratio: float
    last_updated: datetime = field(default_factory=datetime.utcnow)

@dataclass
class VaRResult:
    """Value at Risk calculation result"""
    symbol: str
    var_95: float
    cvar_95: float
    confidence_level: float
    horizon_days: int
    calculation_method: str
    window_days: int
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class StressTestResult:
    """Stress test scenario result"""
    scenario: StressScenario
    portfolio_loss: float
    loss_percentage: float
    worst_asset: str
    worst_loss: float
    probability: float
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class RiskAttribution:
    """Risk attribution breakdown"""
    total_variance: float
    asset_contributions: Dict[str, float]
    strategy_contributions: Dict[str, float]
    time_horizon_contributions: Dict[str, float]
    unexplained_variance: float
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class RiskAlert:
    """Risk management alert"""
    alert_id: str
    alert_type: str
    severity: RiskLevel
    message: str
    value: float
    threshold: float
    symbol: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False

# ============================================================================
# RISK QUANTIFICATION AGENT
# ============================================================================

class RiskQuantificationAgent:
    """
    Comprehensive risk quantification agent implementing industry-standard
    portfolio risk management with VaR, stress testing, and optimization.
    """

    def __init__(self, redis_url: str, db_url: str, config: RiskConfig = None):
        self.redis_url = redis_url
        self.db_url = db_url
        self.config = config or RiskConfig()

        # Core components
        self.redis: Optional[Any] = None
        self.db: Optional[Any] = None

        # State
        self.portfolio = Portfolio(
            positions={},
            total_value=0.0,
            cash=100000.0,  # Default starting cash
            total_var=0.0,
            total_cvar=0.0,
            sharpe_ratio=0.0,
            diversification_ratio=0.0
        )

        self.historical_data: Dict[str, pd.DataFrame] = {}
        self.var_results: Dict[str, VaRResult] = {}
        self.stress_results: List[StressTestResult] = []
        self.risk_attribution = RiskAttribution(
            total_variance=0.0,
            asset_contributions={},
            strategy_contributions={},
            time_horizon_contributions={},
            unexplained_variance=0.0
        )
        self.active_alerts: Dict[str, RiskAlert] = {}

        # Monitoring tasks
        self.risk_monitoring_task: Optional[asyncio.Task] = None
        self.dashboard_task: Optional[asyncio.Task] = None

        # Web components
        self.app: Optional[Any] = None
        self.server_task: Optional[asyncio.Task] = None

        logger.info("Risk Quantification Agent initialized")

    async def initialize(self):
        """Initialize connections and start monitoring"""
        try:
            # Initialize Redis
            if AIREDIS_AVAILABLE:
                self.redis = await aioredis.from_url(self.redis_url)
                logger.info("Redis connection established")
            else:
                self.redis = MockRedis()
                logger.warning("Redis not available, using mock")

            # Initialize database
            if ASYNCPG_AVAILABLE:
                self.db = await asyncpg.create_pool(self.db_url)
                await self._create_tables()
                logger.info("Database connection established")
            else:
                self.db = MockPool()
                logger.warning("Database not available, using mock")

            # Load historical data
            await self._load_historical_data()

            # Start monitoring
            self.risk_monitoring_task = asyncio.create_task(self._risk_monitoring_loop())
            self.dashboard_task = asyncio.create_task(self._dashboard_update_loop())

            # Start web server
            if FASTAPI_AVAILABLE:
                self.app = self._create_web_app()
                self.server_task = asyncio.create_task(self._start_web_server())

            logger.info("Risk Quantification Agent started successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Risk Agent: {e}")
            raise

    async def _create_tables(self):
        """Create database tables for risk data"""
        if not ASYNCPG_AVAILABLE:
            return

        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS risk_var_results (
                symbol TEXT PRIMARY KEY,
                var_95 REAL,
                cvar_95 REAL,
                confidence_level REAL,
                horizon_days INTEGER,
                calculation_method TEXT,
                window_days INTEGER,
                timestamp TIMESTAMP
            )
        """)

        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS risk_stress_results (
                scenario TEXT,
                portfolio_loss REAL,
                loss_percentage REAL,
                worst_asset TEXT,
                worst_loss REAL,
                probability REAL,
                timestamp TIMESTAMP
            )
        """)

        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS risk_alerts (
                alert_id TEXT PRIMARY KEY,
                alert_type TEXT,
                severity TEXT,
                message TEXT,
                value REAL,
                threshold REAL,
                symbol TEXT,
                timestamp TIMESTAMP,
                acknowledged BOOLEAN
            )
        """)

    async def _load_historical_data(self):
        """Load historical price data for risk calculations"""
        symbols = ['BTC', 'ETH', 'SOL', 'ADA', 'DOT']  # Default symbols

        for symbol in symbols:
            try:
                # Load from database or API
                data = await self._fetch_historical_prices(symbol, days=730)  # 2+ years
                if data:
                    self.historical_data[symbol] = pd.DataFrame(data)
                    self.historical_data[symbol]['date'] = pd.to_datetime(self.historical_data[symbol]['date'])
                    self.historical_data[symbol] = self.historical_data[symbol].set_index('date').sort_index()
                    logger.info(f"Loaded {len(self.historical_data[symbol])} days of data for {symbol}")
            except Exception as e:
                logger.error(f"Failed to load historical data for {symbol}: {e}")

    async def _fetch_historical_prices(self, symbol: str, days: int) -> List[Dict]:
        """Fetch historical price data"""
        # This would integrate with data_validator_agent or external APIs
        # For now, return mock data
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        data = []
        current_date = start_date
        price = 50000.0 if symbol == 'BTC' else 3000.0  # Mock starting prices

        while current_date <= end_date:
            # Generate realistic price movements
            daily_return = np.random.normal(0.001, 0.03)  # Mean 0.1%, vol 3%
            price *= (1 + daily_return)

            data.append({
                'date': current_date,
                'price': price,
                'volume': price * np.random.uniform(1000, 10000)
            })

            current_date += timedelta(days=1)

        return data

    # ============================================================================
    # VaR/CVaR CALCULATIONS
    # ============================================================================

    def calculate_historical_var(self, symbol: str, confidence_level: float = 0.95,
                               horizon_days: int = 1, window_days: int = 252) -> VaRResult:
        """
        Calculate historical Value at Risk using rolling window
        """
        if symbol not in self.historical_data:
            raise ValueError(f"No historical data for {symbol}")

        df = self.historical_data[symbol]

        # Calculate daily returns
        df = df.copy()
        df['returns'] = df['price'].pct_change()

        # Use rolling window of recent data
        recent_data = df.tail(window_days)
        returns = recent_data['returns'].dropna()

        if len(returns) < 30:
            raise ValueError(f"Insufficient data for {symbol}: {len(returns)} days")

        # Calculate VaR (loss at confidence level)
        var_percentile = (1 - confidence_level) * 100
        var_95 = np.percentile(returns, var_percentile)

        # Calculate CVaR (Expected Shortfall)
        tail_losses = returns[returns <= var_95]
        cvar_95 = tail_losses.mean() if len(tail_losses) > 0 else var_95

        # Scale for horizon (assuming independence)
        if horizon_days > 1:
            var_95 = var_95 * np.sqrt(horizon_days)
            cvar_95 = cvar_95 * np.sqrt(horizon_days)

        result = VaRResult(
            symbol=symbol,
            var_95=abs(var_95),  # Convert to positive loss
            cvar_95=abs(cvar_95),
            confidence_level=confidence_level,
            horizon_days=horizon_days,
            calculation_method="historical",
            window_days=window_days
        )

        self.var_results[symbol] = result
        return result

    def calculate_portfolio_var(self) -> Tuple[float, float]:
        """
        Calculate portfolio VaR using variance-covariance method
        """
        if not self.portfolio.positions:
            return 0.0, 0.0

        # Get position weights and volatilities
        weights = []
        volatilities = []
        symbols = []

        for symbol, position in self.portfolio.positions.items():
            if symbol in self.var_results:
                weights.append(position.weight)
                volatilities.append(self.var_results[symbol].var_95)
                symbols.append(symbol)

        if not weights:
            return 0.0, 0.0

        weights = np.array(weights)
        volatilities = np.array(volatilities)

        # Calculate correlation matrix
        returns_data = []
        for symbol in symbols:
            if symbol in self.historical_data:
                returns = self.historical_data[symbol]['price'].pct_change().dropna().tail(252)
                returns_data.append(returns)

        if len(returns_data) < 2:
            # Simple sum if no correlation data
            portfolio_var = np.sum(weights * volatilities)
            portfolio_cvar = portfolio_var * 1.2  # Approximation
        else:
            # Calculate covariance matrix
            returns_df = pd.concat(returns_data, axis=1, keys=symbols)
            cov_matrix = returns_df.cov()

            # Portfolio variance
            portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
            portfolio_var = np.sqrt(portfolio_variance)

            # CVaR approximation
            portfolio_cvar = portfolio_var * 1.2

        self.portfolio.total_var = portfolio_var
        self.portfolio.total_cvar = portfolio_cvar

        return portfolio_var, portfolio_cvar

    # ============================================================================
    # STRESS TESTING
    # ============================================================================

    def run_stress_test(self, scenario: StressScenario) -> StressTestResult:
        """
        Run Monte Carlo stress test for given scenario
        """
        if not self.portfolio.positions:
            return StressTestResult(
                scenario=scenario,
                portfolio_loss=0.0,
                loss_percentage=0.0,
                worst_asset="",
                worst_loss=0.0,
                probability=0.0
            )

        # Define scenario parameters
        scenario_params = self._get_scenario_parameters(scenario)

        losses = []
        worst_assets = []
        worst_losses = []

        # Run Monte Carlo simulations
        for _ in range(self.config.monte_carlo_simulations):
            portfolio_loss = 0.0
            max_loss = 0.0
            worst_sym = ""

            for symbol, position in self.portfolio.positions.items():
                # Generate stressed return
                base_vol = self.var_results.get(symbol, VaRResult(symbol, 0.05, 0.07, 0.95, 1, "historical", 252)).var_95
                stressed_return = self._generate_stressed_return(symbol, scenario_params, base_vol)

                position_loss = position.market_value * stressed_return
                portfolio_loss += position_loss

                if abs(position_loss) > abs(max_loss):
                    max_loss = position_loss
                    worst_sym = symbol

            losses.append(portfolio_loss)
            worst_assets.append(worst_sym)
            worst_losses.append(max_loss)

        # Calculate statistics
        losses_array = np.array(losses)
        mean_loss = np.mean(losses_array)
        loss_percentile = np.percentile(losses_array, 5)  # 95% confidence worst case

        # Find most common worst asset
        from collections import Counter
        worst_asset = Counter(worst_assets).most_common(1)[0][0]
        worst_loss = np.mean([loss for loss, asset in zip(worst_losses, worst_assets) if asset == worst_asset])

        result = StressTestResult(
            scenario=scenario,
            portfolio_loss=abs(loss_percentile),
            loss_percentage=abs(loss_percentile) / self.portfolio.total_value,
            worst_asset=worst_asset,
            worst_loss=abs(worst_loss),
            probability=0.05  # 5th percentile
        )

        self.stress_results.append(result)
        return result

    def _get_scenario_parameters(self, scenario: StressScenario) -> Dict[str, float]:
        """Get stress test parameters for scenario"""
        params = {
            StressScenario.MARKET_CRASH: {
                'market_drop': 0.20,  # 20% market drop
                'volatility_multiplier': 2.0,
                'correlation_increase': 0.3
            },
            StressScenario.VOLATILITY_SPIKE: {
                'market_drop': 0.05,
                'volatility_multiplier': 3.0,
                'correlation_increase': 0.1
            },
            StressScenario.LIQUIDITY_CRISIS: {
                'market_drop': 0.15,
                'volatility_multiplier': 2.5,
                'correlation_increase': 0.4
            },
            StressScenario.SECTOR_CRASH: {
                'market_drop': 0.10,
                'volatility_multiplier': 1.8,
                'correlation_increase': 0.2
            },
            StressScenario.GEOPOLITICAL: {
                'market_drop': 0.12,
                'volatility_multiplier': 2.2,
                'correlation_increase': 0.25
            }
        }
        return params.get(scenario, params[StressScenario.MARKET_CRASH])

    def _generate_stressed_return(self, symbol: str, params: Dict, base_vol: float) -> float:
        """Generate stressed return for Monte Carlo simulation"""
        # Base return from historical distribution
        if symbol in self.historical_data:
            returns = self.historical_data[symbol]['price'].pct_change().dropna()
            base_return = np.random.choice(returns)
        else:
            base_return = np.random.normal(0, base_vol)

        # Apply stress
        stressed_vol = base_vol * params['volatility_multiplier']
        stress_impact = np.random.normal(-params['market_drop'], stressed_vol)

        return base_return + stress_impact

    # ============================================================================
    # PORTFOLIO OPTIMIZATION
    # ============================================================================

    def optimize_portfolio(self, target_return: Optional[float] = None) -> Dict[str, float]:
        """
        Optimize portfolio using Modern Portfolio Theory
        Returns optimal weights for minimum variance at target return
        """
        if not self.historical_data:
            return {}

        symbols = list(self.historical_data.keys())
        if len(symbols) < 2:
            return {symbols[0]: 1.0} if symbols else {}

        # Calculate expected returns and covariance
        returns_data = []
        for symbol in symbols:
            ret = self.historical_data[symbol]['price'].pct_change().dropna()
            returns_data.append(ret)

        returns_df = pd.concat(returns_data, axis=1, keys=symbols)
        expected_returns = returns_df.mean() * 252  # Annualize
        cov_matrix = returns_df.cov() * 252  # Annualize

        # Optimization target
        target = target_return or self.config.target_return

        def portfolio_volatility(weights):
            return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

        def portfolio_return(weights):
            return np.sum(expected_returns * weights)

        def objective(weights):
            return portfolio_volatility(weights)

        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},  # Weights sum to 1
            {'type': 'eq', 'fun': lambda w: portfolio_return(w) - target}  # Target return
        ]

        bounds = [(0, 1) for _ in symbols]  # No short selling
        initial_weights = np.array([1/len(symbols)] * len(symbols))

        try:
            result = minimize(objective, initial_weights,
                            method='SLSQP', bounds=bounds, constraints=constraints)

            if result.success:
                optimal_weights = dict(zip(symbols, result.x))
                logger.info(f"Portfolio optimized with target return {target:.2%}")
                return optimal_weights
            else:
                logger.warning("Portfolio optimization failed")
                return {}
        except Exception as e:
            logger.error(f"Optimization error: {e}")
            return {}

    # ============================================================================
    # RISK ATTRIBUTION
    # ============================================================================

    def calculate_risk_attribution(self) -> RiskAttribution:
        """
        Calculate risk attribution by asset, strategy, and time horizon
        """
        if not self.portfolio.positions:
            return self.risk_attribution

        # Calculate total portfolio variance
        total_variance = self.portfolio.total_var ** 2

        # Asset contribution (marginal contribution to risk)
        asset_contributions = {}
        for symbol, position in self.portfolio.positions.items():
            if symbol in self.var_results:
                # Simplified: weight * individual variance
                individual_var = self.var_results[symbol].var_95
                contribution = position.weight ** 2 * individual_var ** 2
                asset_contributions[symbol] = contribution / total_variance

        # Strategy contributions (placeholder - would need strategy classification)
        strategy_contributions = {
            'momentum': 0.4,
            'mean_reversion': 0.3,
            'trend_following': 0.3
        }

        # Time horizon contributions
        time_horizon_contributions = {
            'short_term': 0.6,  # Intraday
            'medium_term': 0.3,  # Days
            'long_term': 0.1    # Weeks
        }

        # Unexplained variance
        explained = sum(asset_contributions.values())
        unexplained = max(0, 1 - explained)

        self.risk_attribution = RiskAttribution(
            total_variance=total_variance,
            asset_contributions=asset_contributions,
            strategy_contributions=strategy_contributions,
            time_horizon_contributions=time_horizon_contributions,
            unexplained_variance=unexplained
        )

        return self.risk_attribution

    # ============================================================================
    # DYNAMIC RISK LIMITS
    # ============================================================================

    def calculate_dynamic_limits(self) -> Dict[str, float]:
        """
        Calculate dynamic risk limits based on current market conditions
        """
        # Base limits from config
        limits = {
            'max_portfolio_var': self.config.max_portfolio_var,
            'max_single_position_var': self.config.max_single_position_var,
            'max_correlation_threshold': self.config.max_correlation_threshold
        }

        # Adjust based on volatility
        current_volatility = self._calculate_market_volatility()
        vol_multiplier = min(1.0, 0.5 / current_volatility)  # Reduce limits in high vol

        limits['max_portfolio_var'] *= vol_multiplier
        limits['max_single_position_var'] *= vol_multiplier

        # Adjust based on portfolio risk
        if self.portfolio.total_var > limits['max_portfolio_var']:
            limits['max_portfolio_var'] = self.portfolio.total_var * 0.9  # Allow some buffer

        return limits

    def _calculate_market_volatility(self) -> float:
        """Calculate current market volatility"""
        if not self.historical_data:
            return 0.03  # Default 3%

        volatilities = []
        for symbol, df in self.historical_data.items():
            if len(df) > 30:
                returns = df['price'].pct_change().dropna().tail(30)
                vol = returns.std() * np.sqrt(252)  # Annualized
                volatilities.append(vol)

        return np.mean(volatilities) if volatilities else 0.03

    # ============================================================================
    # MONITORING & ALERTS
    # ============================================================================

    async def _risk_monitoring_loop(self):
        """Continuous risk monitoring"""
        while True:
            try:
                await self._update_risk_metrics()
                await self._check_risk_limits()
                await asyncio.sleep(self.config.risk_update_interval_seconds)
            except Exception as e:
                logger.error(f"Risk monitoring error: {e}")
                await asyncio.sleep(60)

    async def _update_risk_metrics(self):
        """Update all risk metrics"""
        # Calculate VaR for all positions
        for symbol in self.portfolio.positions.keys():
            try:
                var_result = self.calculate_historical_var(symbol)
                # Store in database
                if ASYNCPG_AVAILABLE and self.db:
                    await self.db.execute("""
                        INSERT INTO risk_var_results
                        (symbol, var_95, cvar_95, confidence_level, horizon_days, calculation_method, window_days, timestamp)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        ON CONFLICT (symbol) DO UPDATE SET
                        var_95 = EXCLUDED.var_95,
                        cvar_95 = EXCLUDED.cvar_95,
                        timestamp = EXCLUDED.timestamp
                    """, symbol, var_result.var_95, var_result.cvar_95,
                        var_result.confidence_level, var_result.horizon_days,
                        var_result.calculation_method, var_result.window_days,
                        var_result.timestamp)
            except Exception as e:
                logger.error(f"Failed to calculate VaR for {symbol}: {e}")

        # Calculate portfolio risk
        self.calculate_portfolio_var()

        # Update risk attribution
        self.calculate_risk_attribution()

        # Run stress tests periodically
        if len(self.stress_results) == 0 or \
           (datetime.utcnow() - self.stress_results[-1].timestamp).total_seconds() > 3600:
            for scenario in self.config.stress_test_scenarios:
                try:
                    result = self.run_stress_test(scenario)
                    if ASYNCPG_AVAILABLE and self.db:
                        await self.db.execute("""
                            INSERT INTO risk_stress_results
                            (scenario, portfolio_loss, loss_percentage, worst_asset, worst_loss, probability, timestamp)
                            VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """, result.scenario.value, result.portfolio_loss, result.loss_percentage,
                            result.worst_asset, result.worst_loss, result.probability, result.timestamp)
                except Exception as e:
                    logger.error(f"Stress test failed for {scenario.value}: {e}")

    async def _check_risk_limits(self):
        """Check risk limits and generate alerts"""
        limits = self.calculate_dynamic_limits()

        # Portfolio VaR limit
        if self.portfolio.total_var > limits['max_portfolio_var']:
            await self._generate_alert(
                "PORTFOLIO_VAR_EXCEEDED",
                RiskLevel.HIGH,
                f"Portfolio VaR {self.portfolio.total_var:.2%} exceeds limit {limits['max_portfolio_var']:.2%}",
                self.portfolio.total_var,
                limits['max_portfolio_var']
            )

        # Individual position limits
        for symbol, position in self.portfolio.positions.items():
            if position.var_contribution > limits['max_single_position_var']:
                await self._generate_alert(
                    "POSITION_VAR_EXCEEDED",
                    RiskLevel.MEDIUM,
                    f"{symbol} position VaR {position.var_contribution:.2%} exceeds limit {limits['max_single_position_var']:.2%}",
                    position.var_contribution,
                    limits['max_single_position_var'],
                    symbol
                )

    async def _generate_alert(self, alert_type: str, severity: RiskLevel, message: str,
                            value: float, threshold: float, symbol: Optional[str] = None):
        """Generate risk alert"""
        alert_id = f"{alert_type}_{symbol or 'PORTFOLIO'}_{int(time.time())}"

        # Check cooldown
        if alert_id in self.active_alerts:
            last_alert = self.active_alerts[alert_id]
            if (datetime.utcnow() - last_alert.timestamp).total_seconds() < self.config.alert_cooldown_minutes * 60:
                return

        alert = RiskAlert(
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            value=value,
            threshold=threshold,
            symbol=symbol
        )

        self.active_alerts[alert_id] = alert

        # Store in database
        if ASYNCPG_AVAILABLE and self.db:
            await self.db.execute("""
                INSERT INTO risk_alerts
                (alert_id, alert_type, severity, message, value, threshold, symbol, timestamp, acknowledged)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, alert.alert_id, alert.alert_type, alert.severity.value, alert.message,
                alert.value, alert.threshold, alert.symbol, alert.timestamp, alert.acknowledged)

        logger.warning(f"Risk Alert: {message}")

        # Publish to Redis
        if AIREDIS_AVAILABLE and self.redis:
            await self.redis.publish("risk_alerts", json.dumps({
                "alert_id": alert.alert_id,
                "type": alert.alert_type,
                "severity": alert.severity.value,
                "message": alert.message,
                "symbol": alert.symbol,
                "timestamp": alert.timestamp.isoformat()
            }))

    # ============================================================================
    # WEB DASHBOARD & API
    # ============================================================================

    def _create_web_app(self) -> FastAPI:
        """Create FastAPI web application"""
        app = FastAPI(title="Risk Quantification Dashboard", version="1.0.0")

        @app.get("/", response_class=HTMLResponse)
        async def dashboard():
            """Main risk dashboard"""
            return self._generate_dashboard_html()

        @app.get("/api/risk/portfolio")
        async def get_portfolio_risk():
            """Get current portfolio risk metrics"""
            return {
                "total_var": self.portfolio.total_var,
                "total_cvar": self.portfolio.total_cvar,
                "sharpe_ratio": self.portfolio.sharpe_ratio,
                "diversification_ratio": self.portfolio.diversification_ratio,
                "positions": [
                    {
                        "symbol": pos.symbol,
                        "weight": pos.weight,
                        "var_contribution": pos.var_contribution,
                        "cvar_contribution": pos.cvar_contribution
                    }
                    for pos in self.portfolio.positions.values()
                ]
            }

        @app.get("/api/risk/var/{symbol}")
        async def get_var(symbol: str):
            """Get VaR for specific symbol"""
            if symbol not in self.var_results:
                raise HTTPException(status_code=404, detail=f"VaR not calculated for {symbol}")
            return self.var_results[symbol].__dict__

        @app.get("/api/risk/stress")
        async def get_stress_results():
            """Get stress test results"""
            return [result.__dict__ for result in self.stress_results[-10:]]  # Last 10

        @app.get("/api/risk/attribution")
        async def get_risk_attribution():
            """Get risk attribution breakdown"""
            return self.risk_attribution.__dict__

        @app.get("/api/risk/limits")
        async def get_risk_limits():
            """Get current dynamic risk limits"""
            return self.calculate_dynamic_limits()

        @app.get("/api/risk/alerts")
        async def get_active_alerts():
            """Get active risk alerts"""
            return [alert.__dict__ for alert in self.active_alerts.values()]

        @app.post("/api/portfolio/update")
        async def update_portfolio(positions: Dict[str, Dict[str, float]]):
            """Update portfolio positions"""
            try:
                self.portfolio.positions.clear()
                total_value = 0.0

                for symbol, pos_data in positions.items():
                    position = PortfolioPosition(
                        symbol=symbol,
                        quantity=pos_data.get('quantity', 0.0),
                        avg_cost=pos_data.get('avg_cost', 0.0),
                        current_price=pos_data.get('current_price', 0.0),
                        market_value=pos_data.get('market_value', 0.0),
                        unrealized_pnl=pos_data.get('unrealized_pnl', 0.0),
                        weight=pos_data.get('weight', 0.0)
                    )
                    self.portfolio.positions[symbol] = position
                    total_value += position.market_value

                self.portfolio.total_value = total_value
                self.portfolio.last_updated = datetime.utcnow()

                # Recalculate risk metrics
                await self._update_risk_metrics()

                return {"status": "success", "message": "Portfolio updated"}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        return app

    def _generate_dashboard_html(self) -> str:
        """Generate HTML dashboard"""
        positions_html = ''.join('<tr><td>{}</td><td>{:.2%}</td><td>{:.2%}</td><td>{:.2%}</td></tr>'.format(
            pos.symbol, pos.weight, pos.var_contribution, pos.cvar_contribution
        ) for pos in self.portfolio.positions.values())

        critical_alerts_html = ''.join('<div class="alert"><strong>{}</strong>: {}</div>'.format(
            alert.alert_type, alert.message
        ) for alert in self.active_alerts.values() if alert.severity == RiskLevel.CRITICAL)

        high_alerts_html = ''.join('<div class="warning"><strong>{}</strong>: {}</div>'.format(
            alert.alert_type, alert.message
        ) for alert in self.active_alerts.values() if alert.severity == RiskLevel.HIGH)

        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Risk Quantification Dashboard</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .metric {{ background: #f0f0f0; padding: 10px; margin: 10px; border-radius: 5px; }}
                .alert {{ background: #ffcccc; border: 1px solid #ff0000; padding: 10px; margin: 10px; }}
                .warning {{ background: #ffffcc; border: 1px solid #ffaa00; padding: 10px; margin: 10px; }}
            </style>
        </head>
        <body>
            <h1>Risk Quantification Dashboard</h1>
            <p>Last updated: {}</p>

            <h2>Portfolio Risk Metrics</h2>
            <div class="metric">
                <strong>Total VaR (95%):</strong> {:.2%}<br>
                <strong>Total CVaR (95%):</strong> {:.2%}<br>
                <strong>Sharpe Ratio:</strong> {:.2f}<br>
                <strong>Diversification Ratio:</strong> {:.2f}
            </div>

            <h2>Position Risk</h2>
            <table border="1" style="width: 100%;">
                <tr><th>Symbol</th><th>Weight</th><th>VaR Contribution</th><th>CVaR Contribution</th></tr>
                {}
            </table>

            <h2>Active Alerts</h2>
            {}
            {}
        </body>
        </html>
        """.format(
            datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            self.portfolio.total_var,
            self.portfolio.total_cvar,
            self.portfolio.sharpe_ratio,
            self.portfolio.diversification_ratio,
            positions_html,
            critical_alerts_html,
            high_alerts_html
        )
        return html

    async def _dashboard_update_loop(self):
        """Update dashboard data periodically"""
        while True:
            try:
                # Update dashboard data in Redis for real-time updates
                if AIREDIS_AVAILABLE and self.redis:
                    dashboard_data = {
                        "portfolio_var": self.portfolio.total_var,
                        "portfolio_cvar": self.portfolio.total_cvar,
                        "alerts": len(self.active_alerts),
                        "positions": len(self.portfolio.positions),
                        "last_update": datetime.utcnow().isoformat()
                    }
                    await self.redis.set("risk_dashboard", json.dumps(dashboard_data))

                await asyncio.sleep(30)  # Update every 30 seconds
            except Exception as e:
                logger.error(f"Dashboard update error: {e}")
                await asyncio.sleep(60)

    async def _start_web_server(self):
        """Start the web server"""
        if FASTAPI_AVAILABLE and self.app:
            config = uvicorn.Config(self.app, host="0.0.0.0", port=8001)
            server = uvicorn.Server(config)
            await server.serve()

    async def shutdown(self):
        """Shutdown the agent"""
        logger.info("Shutting down Risk Quantification Agent")

        # Cancel tasks
        if self.risk_monitoring_task:
            self.risk_monitoring_task.cancel()
        if self.dashboard_task:
            self.dashboard_task.cancel()
        if self.server_task:
            self.server_task.cancel()

        # Close connections
        if AIREDIS_AVAILABLE and self.redis:
            await self.redis.close()
        if ASYNCPG_AVAILABLE and self.db:
            await self.db.close()

# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    """Main execution function"""
    # Configuration
    redis_url = "redis://localhost:6379"
    db_url = "postgresql://user:password@localhost:5432/risk_db"

    # Initialize agent
    agent = RiskQuantificationAgent(redis_url, db_url)

    try:
        await agent.initialize()

        # Example portfolio update
        sample_portfolio = {
            "BTC": {
                "quantity": 0.5,
                "avg_cost": 45000.0,
                "current_price": 50000.0,
                "market_value": 25000.0,
                "unrealized_pnl": 2500.0,
                "weight": 0.25
            },
            "ETH": {
                "quantity": 10.0,
                "avg_cost": 2500.0,
                "current_price": 3000.0,
                "market_value": 30000.0,
                "unrealized_pnl": 5000.0,
                "weight": 0.30
            },
            "SOL": {
                "quantity": 100.0,
                "avg_cost": 100.0,
                "current_price": 120.0,
                "market_value": 12000.0,
                "unrealized_pnl": 2000.0,
                "weight": 0.12
            }
        }

        # Update portfolio via API simulation
        await agent._create_web_app().routes[-1].endpoint(sample_portfolio)  # Update portfolio

        # Run some calculations
        print("Running risk calculations...")

        # Calculate VaR for positions
        for symbol in sample_portfolio.keys():
            try:
                var_result = agent.calculate_historical_var(symbol)
                print(f"{symbol} VaR (95%): {var_result.var_95:.2%}")
            except Exception as e:
                print(f"Failed to calculate VaR for {symbol}: {e}")

        # Calculate portfolio risk
        port_var, port_cvar = agent.calculate_portfolio_var()
        print(f"Portfolio VaR: {port_var:.2%}, CVaR: {port_cvar:.2%}")

        # Run stress test
        stress_result = agent.run_stress_test(StressScenario.MARKET_CRASH)
        print(f"Market Crash Stress Test - Loss: {stress_result.portfolio_loss:.2f} ({stress_result.loss_percentage:.2%})")

        # Optimize portfolio
        optimal_weights = agent.optimize_portfolio()
        print(f"Optimal Portfolio Weights: {optimal_weights}")

        # Risk attribution
        attribution = agent.calculate_risk_attribution()
        print(f"Risk Attribution - Explained: {(1-attribution.unexplained_variance):.1%}")

        print("Risk Quantification Agent demo completed successfully!")

        # Keep running for monitoring
        print("Demo completed successfully! Agent is running...")
        await asyncio.sleep(5)  # Just run for 5 seconds for demo
        print("Exiting demo...")

    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await agent.shutdown()

if __name__ == "__main__":
    asyncio.run(main())