"""
================================================================================
COMPREHENSIVE REGIME DETECTION SYSTEM FOR ALGORITHMIC TRADING
================================================================================

A production-ready regime detection module that acts as HARD TOGGLES (filters)
rather than signal generators. Based on academic research in:
- VIX-based regime classification
- Hidden Markov Models for regime detection
- DXY (dollar strength) as macro filter
- Volatility clustering (GARCH models)
- Regime-switching strategies

Author: Quantitative Finance Research
Version: 1.0.0

ACADEMIC REFERENCES:
-------------------
[1] Dapena, Serur & Siri (2018) - "Measuring and trading volatility on the 
    US stock market: A regime switching approach" - Universidad del CEMA
    
[2] Hamilton (1989) - "A New Approach to the Economic Analysis of Nonstationary
    Time Series and the Business Cycle" - Econometrica
    
[3] Bollerslev (1986) - "Generalized Autoregressive Conditional Heteroskedasticity"
    - Journal of Econometrics
    
[4] Glosten, Jagannathan & Runkle (1993) - "On the Relation between the 
    Expected Value and the Volatility of the Nominal Excess Return on Stocks"
    - Journal of Finance

[5] Kritzman & Li (2010) - "Skulls, Financial Turbulence, and Risk Management"
    - Financial Analysts Journal

================================================================================
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime, timedelta
import warnings
from collections import defaultdict
import json

# Optional imports for advanced features
try:
    from hmmlearn.hmm import GaussianHMM
    HMM_AVAILABLE = True
except ImportError:
    HMM_AVAILABLE = False
    warnings.warn("hmmlearn not installed. HMM features will be disabled.")

try:
    from arch import arch_model
    ARCH_AVAILABLE = True
except ImportError:
    ARCH_AVAILABLE = False
    warnings.warn("arch not installed. GARCH features will be disabled.")

try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.mixture import GaussianMixture
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


# ==============================================================================
# ENUMERATIONS AND DATA CLASSES
# ==============================================================================

class MarketRegime(Enum):
    """
    Market regime classifications based on VIX and macro conditions.
    
    BULL: Low volatility, trending up - favorable for long strategies
    BEAR: High volatility, trending down - risk-off mode
    CHOP: Medium volatility, range-bound - unfavorable for trend strategies
    CRISIS: Extreme volatility - full lockdown mode
    TRANSITION: Regime change in progress - exercise caution
    """
    BULL = auto()
    BEAR = auto()
    CHOP = auto()
    CRISIS = auto()
    TRANSITION = auto()
    UNKNOWN = auto()


class AssetClass(Enum):
    """Asset class categories for regime-specific filtering."""
    EQUITY_INDEX = auto()
    EQUITY_SECTOR = auto()
    COMMODITY = auto()
    CURRENCY = auto()
    BOND = auto()
    VOLATILITY = auto()
    CRYPTO = auto()
    ALTERNATIVE = auto()


class TradeDirection(Enum):
    """Trade direction for filtering decisions."""
    LONG = 1
    SHORT = -1
    NEUTRAL = 0


@dataclass
class RegimeThresholds:
    """
    Configurable thresholds for regime classification.
    
    Default values based on academic research and industry practice:
    - VIX < 15: Extreme calm (BULL)
    - VIX 15-20: Normal calm (BULL)
    - VIX 20-25: Elevated (CHOP)
    - VIX 25-30: High (BEAR)
    - VIX > 30: Extreme (CRISIS)
    """
    # VIX thresholds
    vix_bull_max: float = 20.0
    vix_chop_min: float = 20.0
    vix_chop_max: float = 25.0
    vix_bear_min: float = 25.0
    vix_crisis_min: float = 30.0
    
    # DXY thresholds for currency filtering
    dxy_strong_usd: float = 105.0
    dxy_weak_usd: float = 100.0
    
    # Term structure thresholds (VIX3M/VIX ratio)
    vix_contango_threshold: float = 1.0  # > 1 = contango
    vix_backwardation_threshold: float = 0.95  # < 0.95 = backwardation
    
    # Transition detection
    regime_persistence_days: int = 3  # Days to confirm regime change
    
    def to_dict(self) -> Dict:
        return {
            'vix_bull_max': self.vix_bull_max,
            'vix_chop_min': self.vix_chop_min,
            'vix_chop_max': self.vix_chop_max,
            'vix_bear_min': self.vix_bear_min,
            'vix_crisis_min': self.vix_crisis_min,
            'dxy_strong_usd': self.dxy_strong_usd,
            'dxy_weak_usd': self.dxy_weak_usd,
            'vix_contango_threshold': self.vix_contango_threshold,
            'vix_backwardation_threshold': self.vix_backwardation_threshold,
            'regime_persistence_days': self.regime_persistence_days
        }


@dataclass
class AssetClassConfig:
    """
    Configuration for per-asset-class regime filtering.
    
    This allows different asset classes to have different regime sensitivities.
    """
    asset_class: AssetClass
    
    # Regime exemptions (regimes where this asset class is allowed despite general filter)
    exempt_regimes: List[MarketRegime] = field(default_factory=list)
    
    # Direction-specific exemptions
    long_allowed_regimes: List[MarketRegime] = field(default_factory=list)
    short_allowed_regimes: List[MarketRegime] = field(default_factory=list)
    
    # Custom VIX thresholds for this asset class (optional)
    custom_vix_threshold: Optional[float] = None
    
    # DXY sensitivity
    dxy_sensitive: bool = True
    
    # Volatility scaling factor (higher = more tolerant of volatility)
    volatility_tolerance: float = 1.0
    
    def __post_init__(self):
        # Set defaults based on asset class
        if not self.long_allowed_regimes:
            self.long_allowed_regimes = [MarketRegime.BULL, MarketRegime.CHOP]
        if not self.short_allowed_regimes:
            self.short_allowed_regimes = [MarketRegime.BEAR, MarketRegime.CHOP]


@dataclass
class RegimeState:
    """Current state of the market regime with metadata."""
    regime: MarketRegime
    timestamp: datetime
    vix_level: float
    dxy_level: Optional[float] = None
    vix_term_structure: Optional[float] = None  # VIX3M/VIX ratio
    
    # Regime stability metrics
    regime_days: int = 0  # Days in current regime
    regime_probability: float = 1.0  # Confidence in regime classification
    
    # Additional features
    realized_vol: Optional[float] = None
    implied_vol_premium: Optional[float] = None  # VIX - realized vol
    
    def to_dict(self) -> Dict:
        return {
            'regime': self.regime.name,
            'timestamp': self.timestamp.isoformat(),
            'vix_level': self.vix_level,
            'dxy_level': self.dxy_level,
            'vix_term_structure': self.vix_term_structure,
            'regime_days': self.regime_days,
            'regime_probability': self.regime_probability,
            'realized_vol': self.realized_vol,
            'implied_vol_premium': self.implied_vol_premium
        }


@dataclass
class FilterDecision:
    """Result of a trade filter decision."""
    allow_trade: bool
    reason: str
    regime_state: RegimeState
    asset_class: AssetClass
    direction: TradeDirection
    
    # Additional context
    risk_adjustment: float = 1.0  # Position size multiplier (0-1)
    warning_flags: List[str] = field(default_factory=list)


# ==============================================================================
# MAIN REGIME DETECTOR CLASS
# ==============================================================================

class RegimeDetector:
    """
    Comprehensive regime detection system for algorithmic trading.
    
    This class implements HARD TOGGLES (filters) rather than signal generators.
    It uses multiple macro indicators to classify market regimes and determine
    whether trades should be allowed for specific asset classes.
    
    KEY FEATURES:
    -------------
    1. VIX-based regime classification (BULL/BEAR/CHOP/CRISIS)
    2. DXY (dollar strength) macro filter
    3. VIX term structure analysis (contango/backwardation)
    4. Per-asset-class filtering with exemptions
    5. Hidden Markov Model (optional) for probabilistic regime detection
    6. GARCH volatility forecasting (optional)
    7. Regime persistence tracking to avoid whipsaws
    
    USAGE:
    ------
    >>> detector = RegimeDetector()
    >>> detector.update_market_data(vix=18.5, dxy=103.2)
    >>> decision = detector.allow_trade(
    ...     asset_class=AssetClass.EQUITY_INDEX,
    ...     direction=TradeDirection.LONG,
    ...     symbol="ES"
    ... )
    >>> if decision.allow_trade:
    ...     execute_trade()
    """
    
    def __init__(
        self,
        thresholds: Optional[RegimeThresholds] = None,
        use_hmm: bool = False,
        use_garch: bool = False,
        hmm_lookback: int = 252,
        verbose: bool = False
    ):
        """
        Initialize the RegimeDetector.
        
        Parameters:
        -----------
        thresholds : RegimeThresholds, optional
            Custom thresholds for regime classification
        use_hmm : bool
            Whether to use Hidden Markov Model for regime detection
        use_garch : bool
            Whether to use GARCH for volatility forecasting
        hmm_lookback : int
            Number of days to use for HMM training
        verbose : bool
            Whether to print diagnostic information
        """
        self.thresholds = thresholds or RegimeThresholds()
        self.use_hmm = use_hmm and HMM_AVAILABLE
        self.use_garch = use_garch and ARCH_AVAILABLE
        self.hmm_lookback = hmm_lookback
        self.verbose = verbose
        
        # State tracking
        self.current_state: Optional[RegimeState] = None
        self.regime_history: List[RegimeState] = []
        self.max_history = 1000
        
        # Market data storage
        self.vix_history: pd.Series = pd.Series(dtype=float)
        self.dxy_history: pd.Series = pd.Series(dtype=float)
        self.returns_history: pd.Series = pd.Series(dtype=float)
        
        # Asset class configurations
        self.asset_configs: Dict[AssetClass, AssetClassConfig] = {}
        self._setup_default_asset_configs()
        
        # HMM model storage
        self.hmm_model: Optional[GaussianHMM] = None
        self.hmm_scaler: Optional[StandardScaler] = None
        
        # GARCH model storage
        self.garch_model = None
        self.garch_results = None
        
        # Statistics
        self.filter_stats = {
            'total_checks': 0,
            'trades_allowed': 0,
            'trades_blocked': 0,
            'regime_transitions': 0
        }
        
        if self.verbose:
            print(f"RegimeDetector initialized:")
            print(f"  HMM enabled: {self.use_hmm}")
            print(f"  GARCH enabled: {self.use_garch}")
            print(f"  Thresholds: {self.thresholds.to_dict()}")
    
    def _setup_default_asset_configs(self):
        """Setup default configurations for each asset class."""
        # Equity Index - sensitive to VIX, blocked in high vol
        self.asset_configs[AssetClass.EQUITY_INDEX] = AssetClassConfig(
            asset_class=AssetClass.EQUITY_INDEX,
            long_allowed_regimes=[MarketRegime.BULL, MarketRegime.CHOP],
            short_allowed_regimes=[MarketRegime.BEAR],
            dxy_sensitive=False,
            volatility_tolerance=1.0
        )
        
        # Commodities - often work in CHOP, exempt from some filters
        self.asset_configs[AssetClass.COMMODITY] = AssetClassConfig(
            asset_class=AssetClass.COMMODITY,
            long_allowed_regimes=[MarketRegime.BULL, MarketRegime.CHOP, MarketRegime.BEAR],
            short_allowed_regimes=[MarketRegime.BULL, MarketRegime.CHOP, MarketRegime.BEAR],
            exempt_regimes=[MarketRegime.CHOP],  # Key exemption!
            dxy_sensitive=True,  # Strong USD hurts commodities
            volatility_tolerance=1.2
        )
        
        # Currencies - very DXY sensitive
        self.asset_configs[AssetClass.CURRENCY] = AssetClassConfig(
            asset_class=AssetClass.CURRENCY,
            long_allowed_regimes=[MarketRegime.BULL, MarketRegime.CHOP, MarketRegime.BEAR],
            short_allowed_regimes=[MarketRegime.BULL, MarketRegime.CHOP, MarketRegime.BEAR],
            dxy_sensitive=True,
            volatility_tolerance=1.0
        )
        
        # Bonds - often safe haven
        self.asset_configs[AssetClass.BOND] = AssetClassConfig(
            asset_class=AssetClass.BOND,
            long_allowed_regimes=[MarketRegime.BULL, MarketRegime.CHOP, MarketRegime.BEAR, MarketRegime.CRISIS],
            short_allowed_regimes=[MarketRegime.BULL],
            dxy_sensitive=False,
            volatility_tolerance=1.3
        )
        
        # Volatility products - only in specific regimes
        self.asset_configs[AssetClass.VOLATILITY] = AssetClassConfig(
            asset_class=AssetClass.VOLATILITY,
            long_allowed_regimes=[MarketRegime.BEAR, MarketRegime.CRISIS],
            short_allowed_regimes=[MarketRegime.BULL, MarketRegime.CHOP],
            dxy_sensitive=False,
            volatility_tolerance=1.5
        )
        
        # Crypto - high volatility tolerance
        self.asset_configs[AssetClass.CRYPTO] = AssetClassConfig(
            asset_class=AssetClass.CRYPTO,
            long_allowed_regimes=[MarketRegime.BULL, MarketRegime.CHOP],
            short_allowed_regimes=[MarketRegime.BEAR, MarketRegime.CHOP],
            dxy_sensitive=True,
            volatility_tolerance=1.5
        )
    
    def configure_asset_class(
        self,
        asset_class: AssetClass,
        config: AssetClassConfig
    ):
        """
        Configure regime filtering for a specific asset class.
        
        Parameters:
        -----------
        asset_class : AssetClass
            The asset class to configure
        config : AssetClassConfig
            Configuration for this asset class
        """
        self.asset_configs[asset_class] = config
        if self.verbose:
            print(f"Configured {asset_class.name}: exempt_regimes={config.exempt_regimes}")
    
    def update_market_data(
        self,
        timestamp: Optional[datetime] = None,
        vix: Optional[float] = None,
        dxy: Optional[float] = None,
        vix3m: Optional[float] = None,
        returns: Optional[float] = None,
        realized_vol: Optional[float] = None
    ) -> RegimeState:
        """
        Update market data and detect current regime.
        
        Parameters:
        -----------
        timestamp : datetime, optional
            Timestamp for this data point
        vix : float, optional
            Current VIX level
        dxy : float, optional
            Current DXY (dollar index) level
        vix3m : float, optional
            3-month VIX for term structure
        returns : float, optional
            Market returns for volatility calculation
        realized_vol : float, optional
            Realized volatility (annualized)
        
        Returns:
        --------
        RegimeState
            Current regime state
        """
        timestamp = timestamp or datetime.now()
        
        # Store historical data
        if vix is not None:
            self.vix_history[timestamp] = vix
        if dxy is not None:
            self.dxy_history[timestamp] = dxy
        if returns is not None:
            self.returns_history[timestamp] = returns
        
        # Calculate term structure
        vix_term_structure = None
        if vix3m is not None and vix is not None and vix > 0:
            vix_term_structure = vix3m / vix
        
        # Calculate implied vol premium
        implied_vol_premium = None
        if vix is not None and realized_vol is not None:
            implied_vol_premium = vix - realized_vol
        
        # Detect regime
        regime = self._detect_regime(vix, vix_term_structure)
        
        # Calculate regime persistence
        regime_days = 0
        regime_probability = 1.0
        
        if self.current_state is not None:
            if regime == self.current_state.regime:
                regime_days = self.current_state.regime_days + 1
            else:
                regime_days = 1
                self.filter_stats['regime_transitions'] += 1
        
        # HMM-based probability (if enabled)
        if self.use_hmm and len(self.returns_history) >= self.hmm_lookback:
            regime_probability = self._get_hmm_regime_probability()
        
        # Create state
        new_state = RegimeState(
            regime=regime,
            timestamp=timestamp,
            vix_level=vix if vix is not None else 0,
            dxy_level=dxy,
            vix_term_structure=vix_term_structure,
            regime_days=regime_days,
            regime_probability=regime_probability,
            realized_vol=realized_vol,
            implied_vol_premium=implied_vol_premium
        )
        
        self.current_state = new_state
        self.regime_history.append(new_state)
        
        # Trim history
        if len(self.regime_history) > self.max_history:
            self.regime_history = self.regime_history[-self.max_history:]
        
        # Update GARCH if enabled
        if self.use_garch and len(self.returns_history) >= 100:
            self._update_garch()
        
        if self.verbose:
            print(f"[{timestamp}] Regime: {regime.name}, VIX: {vix:.2f}, DXY: {dxy:.2f}")
        
        return new_state
    
    def _detect_regime(
        self,
        vix: Optional[float],
        vix_term_structure: Optional[float]
    ) -> MarketRegime:
        """
        Detect market regime based on VIX and term structure.
        
        This implements the core regime classification logic.
        """
        if vix is None:
            return MarketRegime.UNKNOWN
        
        t = self.thresholds
        
        # Primary regime classification based on VIX
        if vix >= t.vix_crisis_min:
            regime = MarketRegime.CRISIS
        elif vix >= t.vix_bear_min:
            regime = MarketRegime.BEAR
        elif vix >= t.vix_chop_min:
            regime = MarketRegime.CHOP
        else:
            regime = MarketRegime.BULL
        
        # Term structure adjustment
        if vix_term_structure is not None:
            if vix_term_structure < t.vix_backwardation_threshold:
                # Backwardation indicates stress - elevate regime
                if regime == MarketRegime.BULL:
                    regime = MarketRegime.CHOP
                elif regime == MarketRegime.CHOP:
                    regime = MarketRegime.BEAR
            elif regime == MarketRegime.BEAR and vix_term_structure > t.vix_contango_threshold:
                # Contango in bear market might indicate recovery
                if self.current_state and self.current_state.regime_days > 5:
                    regime = MarketRegime.TRANSITION
        
        return regime
    
    def allow_trade(
        self,
        asset_class: AssetClass,
        direction: TradeDirection,
        symbol: Optional[str] = None,
        override_reason: Optional[str] = None
    ) -> FilterDecision:
        """
        Determine if a trade should be allowed based on current regime.
        
        This is the MAIN FILTER METHOD - acts as a HARD TOGGLE.
        
        Parameters:
        -----------
        asset_class : AssetClass
            The asset class of the trade
        direction : TradeDirection
            Direction of the trade (LONG/SHORT)
        symbol : str, optional
            Specific symbol (for logging/debugging)
        override_reason : str, optional
            Reason for overriding filter (for audit trail)
        
        Returns:
        --------
        FilterDecision
            Decision with allow_trade flag and reasoning
        """
        self.filter_stats['total_checks'] += 1
        
        if self.current_state is None:
            return FilterDecision(
                allow_trade=False,
                reason="No regime data available",
                regime_state=RegimeState(MarketRegime.UNKNOWN, datetime.now(), 0),
                asset_class=asset_class,
                direction=direction,
                risk_adjustment=0
            )
        
        config = self.asset_configs.get(asset_class)
        if config is None:
            config = AssetClassConfig(asset_class=asset_class)
        
        regime = self.current_state.regime
        vix = self.current_state.vix_level
        dxy = self.current_state.dxy_level
        
        warnings = []
        risk_adjustment = 1.0
        
        # Check regime exemptions
        if regime in config.exempt_regimes:
            self.filter_stats['trades_allowed'] += 1
            return FilterDecision(
                allow_trade=True,
                reason=f"Regime {regime.name} exempted for {asset_class.name}",
                regime_state=self.current_state,
                asset_class=asset_class,
                direction=direction,
                risk_adjustment=1.0,
                warning_flags=["REGIME_EXEMPT"]
            )
        
        # Check direction-specific regime permissions
        allowed_regimes = (
            config.long_allowed_regimes if direction == TradeDirection.LONG
            else config.short_allowed_regimes
        )
        
        if regime not in allowed_regimes:
            self.filter_stats['trades_blocked'] += 1
            return FilterDecision(
                allow_trade=False,
                reason=f"Regime {regime.name} not in allowed list for {direction.name} {asset_class.name}",
                regime_state=self.current_state,
                asset_class=asset_class,
                direction=direction,
                risk_adjustment=0
            )
        
        # Check DXY filter for USD-sensitive assets
        if config.dxy_sensitive and dxy is not None:
            if direction == TradeDirection.LONG and dxy > self.thresholds.dxy_strong_usd:
                # Strong USD - be cautious with non-USD longs
                if asset_class in [AssetClass.COMMODITY, AssetClass.CURRENCY]:
                    warnings.append("STRONG_USD")
                    risk_adjustment *= 0.7
            elif direction == TradeDirection.SHORT and dxy < self.thresholds.dxy_weak_usd:
                warnings.append("WEAK_USD")
                risk_adjustment *= 0.7
        
        # Check VIX level against custom threshold
        if config.custom_vix_threshold is not None:
            if vix > config.custom_vix_threshold:
                warnings.append("VIX_ABOVE_CUSTOM")
                risk_adjustment *= 0.5
        
        # Apply volatility tolerance scaling
        if regime == MarketRegime.CHOP:
            risk_adjustment *= config.volatility_tolerance
        elif regime == MarketRegime.BEAR:
            risk_adjustment *= config.volatility_tolerance * 0.7
        elif regime == MarketRegime.CRISIS:
            risk_adjustment *= 0.3
        
        # Ensure minimum risk adjustment
        risk_adjustment = max(0.1, min(1.0, risk_adjustment))
        
        self.filter_stats['trades_allowed'] += 1
        
        return FilterDecision(
            allow_trade=True,
            reason=f"Trade allowed in {regime.name} regime",
            regime_state=self.current_state,
            asset_class=asset_class,
            direction=direction,
            risk_adjustment=risk_adjustment,
            warning_flags=warnings
        )
    
    def batch_filter_signals(
        self,
        signals: List[Dict]
    ) -> List[FilterDecision]:
        """
        Filter multiple trading signals at once.
        
        Parameters:
        -----------
        signals : List[Dict]
            List of signal dictionaries with keys:
            - 'asset_class': AssetClass
            - 'direction': TradeDirection
            - 'symbol': str (optional)
            - 'size': float (optional)
        
        Returns:
        --------
        List[FilterDecision]
            Filter decisions for each signal
        """
        decisions = []
        for signal in signals:
            decision = self.allow_trade(
                asset_class=signal['asset_class'],
                direction=signal['direction'],
                symbol=signal.get('symbol')
            )
            decisions.append(decision)
        return decisions
    
    def get_regime_summary(self, lookback_days: int = 30) -> Dict:
        """
        Get summary statistics of recent regime behavior.
        
        Parameters:
        -----------
        lookback_days : int
            Number of days to include in summary
        
        Returns:
        --------
        Dict
            Summary statistics
        """
        if not self.regime_history:
            return {"error": "No regime history available"}
        
        from datetime import timezone
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        recent = [r for r in self.regime_history if r.timestamp >= cutoff]
        
        if not recent:
            return {"error": f"No data in last {lookback_days} days"}
        
        regime_counts = defaultdict(int)
        for r in recent:
            regime_counts[r.regime.name] += 1
        
        vix_levels = [r.vix_level for r in recent if r.vix_level > 0]
        dxy_levels = [r.dxy_level for r in recent if r.dxy_level is not None]
        
        return {
            'lookback_days': lookback_days,
            'total_observations': len(recent),
            'regime_distribution': dict(regime_counts),
            'current_regime': self.current_state.regime.name if self.current_state else None,
            'vix_statistics': {
                'mean': np.mean(vix_levels) if vix_levels else None,
                'std': np.std(vix_levels) if vix_levels else None,
                'min': np.min(vix_levels) if vix_levels else None,
                'max': np.max(vix_levels) if vix_levels else None
            },
            'dxy_statistics': {
                'mean': np.mean(dxy_levels) if dxy_levels else None,
                'std': np.std(dxy_levels) if dxy_levels else None,
                'min': np.min(dxy_levels) if dxy_levels else None,
                'max': np.max(dxy_levels) if dxy_levels else None
            },
            'filter_statistics': self.filter_stats.copy()
        }
    
    def export_regime_history(self, filepath: str):
        """Export regime history to JSON file."""
        history = [r.to_dict() for r in self.regime_history]
        with open(filepath, 'w') as f:
            json.dump(history, f, indent=2, default=str)
        if self.verbose:
            print(f"Exported {len(history)} regime states to {filepath}")
    
    # ======================================================================
    # ADVANCED FEATURES: HMM AND GARCH
    # ======================================================================
    
    def fit_hmm(self, returns: np.ndarray, n_components: int = 2) -> 'GaussianHMM':
        """
        Fit a Hidden Markov Model to returns data.
        
        Based on academic research showing HMMs effectively identify
        latent market regimes (low vol vs high vol).
        
        Parameters:
        -----------
        returns : np.ndarray
            Array of returns
        n_components : int
            Number of hidden states (typically 2 or 3)
        
        Returns:
        --------
        GaussianHMM
            Fitted HMM model
        """
        if not HMM_AVAILABLE:
            raise ImportError("hmmlearn required for HMM features")
        
        # Prepare features
        features = np.column_stack([
            returns,
            np.abs(returns),
            pd.Series(returns).rolling(5).std().fillna(0).values
        ])
        
        # Scale features
        self.hmm_scaler = StandardScaler()
        features_scaled = self.hmm_scaler.fit_transform(features)
        
        # Fit HMM
        model = GaussianHMM(
            n_components=n_components,
            covariance_type="full",
            n_iter=1000,
            random_state=42
        )
        model.fit(features_scaled)
        
        self.hmm_model = model
        
        if self.verbose:
            print(f"HMM fitted with {n_components} components")
            print(f"Transition matrix:\n{model.transmat_}")
        
        return model
    
    def _get_hmm_regime_probability(self) -> float:
        """Get regime probability from HMM."""
        if self.hmm_model is None or not HMM_AVAILABLE:
            return 1.0
        
        if len(self.returns_history) < 10:
            return 1.0
        
        recent_returns = self.returns_history.tail(20).values
        features = np.column_stack([
            recent_returns,
            np.abs(recent_returns),
            pd.Series(recent_returns).rolling(5).std().fillna(0).values
        ])
        
        features_scaled = self.hmm_scaler.transform(features)
        
        # Predict hidden states
        hidden_states = self.hmm_model.predict(features_scaled)
        
        # Calculate probability of current regime persisting
        current_state = hidden_states[-1]
        transition_probs = self.hmm_model.transmat_[current_state]
        persistence_prob = transition_probs[current_state]
        
        return persistence_prob
    
    def fit_garch(self, returns: pd.Series, p: int = 1, q: int = 1) -> Dict:
        """
        Fit a GARCH model for volatility forecasting.
        
        Based on Bollerslev (1986) GARCH model for volatility clustering.
        
        Parameters:
        -----------
        returns : pd.Series
            Return series
        p : int
            GARCH order (lag variances)
        q : int
            ARCH order (lag squared residuals)
        
        Returns:
        --------
        Dict
            Model results and forecasts
        """
        if not ARCH_AVAILABLE:
            raise ImportError("arch package required for GARCH features")
        
        # Scale returns for numerical stability
        scaled_returns = returns * 100
        
        # Fit GARCH
        model = arch_model(
            scaled_returns,
            vol='GARCH',
            p=p,
            q=q,
            mean='Constant',
            dist='normal'
        )
        
        results = model.fit(disp='off')
        self.garch_results = results
        
        # Forecast next day volatility
        forecast = results.forecast(horizon=1)
        next_vol = np.sqrt(forecast.variance.values[-1, 0]) / 100
        
        if self.verbose:
            print(f"GARCH({p},{q}) fitted")
            print(f"Next-day volatility forecast: {next_vol:.4f}")
        
        return {
            'model': model,
            'results': results,
            'forecast_volatility': next_vol,
            'params': results.params.to_dict(),
            'aic': results.aic,
            'bic': results.bic
        }
    
    def _update_garch(self):
        """Update GARCH model with latest data."""
        if len(self.returns_history) >= 100:
            try:
                self.fit_garch(self.returns_history.tail(252))
            except Exception as e:
                if self.verbose:
                    print(f"GARCH update failed: {e}")
    
    def get_volatility_forecast(self, horizon: int = 5) -> Optional[np.ndarray]:
        """
        Get volatility forecast from GARCH model.
        
        Parameters:
        -----------
        horizon : int
            Forecast horizon in days
        
        Returns:
        --------
        np.ndarray
            Volatility forecasts
        """
        if self.garch_results is None or not ARCH_AVAILABLE:
            return None
        
        forecast = self.garch_results.forecast(horizon=horizon)
        vol_forecast = np.sqrt(forecast.variance.values[-1, :]) / 100
        
        return vol_forecast


# ==============================================================================
# UTILITY FUNCTIONS AND HELPERS
# ==============================================================================

def create_regime_detector_from_data(
    vix_data: pd.Series,
    dxy_data: Optional[pd.Series] = None,
    returns_data: Optional[pd.Series] = None,
    **kwargs
) -> RegimeDetector:
    """
    Create and initialize a RegimeDetector from historical data.
    
    Parameters:
    -----------
    vix_data : pd.Series
        Historical VIX data with datetime index
    dxy_data : pd.Series, optional
        Historical DXY data with datetime index
    returns_data : pd.Series, optional
        Historical returns data with datetime index
    **kwargs
        Additional arguments for RegimeDetector
    
    Returns:
    --------
    RegimeDetector
        Initialized detector with historical context
    """
    detector = RegimeDetector(**kwargs)
    
    # Process data chronologically
    for timestamp in vix_data.index:
        vix = vix_data.loc[timestamp]
        dxy = dxy_data.loc[timestamp] if dxy_data is not None and timestamp in dxy_data.index else None
        ret = returns_data.loc[timestamp] if returns_data is not None and timestamp in returns_data.index else None
        
        detector.update_market_data(
            timestamp=timestamp,
            vix=vix,
            dxy=dxy,
            returns=ret
        )
    
    return detector


def get_default_thresholds_for_risk_profile(risk_profile: str) -> RegimeThresholds:
    """
    Get default thresholds for different risk profiles.
    
    Parameters:
    -----------
    risk_profile : str
        One of 'conservative', 'moderate', 'aggressive'
    
    Returns:
    --------
    RegimeThresholds
        Appropriate thresholds
    """
    if risk_profile == 'conservative':
        return RegimeThresholds(
            vix_bull_max=18.0,
            vix_chop_min=18.0,
            vix_chop_max=22.0,
            vix_bear_min=22.0,
            vix_crisis_min=28.0,
            dxy_strong_usd=103.0,
            regime_persistence_days=5
        )
    elif risk_profile == 'aggressive':
        return RegimeThresholds(
            vix_bull_max=22.0,
            vix_chop_min=22.0,
            vix_chop_max=28.0,
            vix_bear_min=28.0,
            vix_crisis_min=35.0,
            dxy_strong_usd=108.0,
            regime_persistence_days=2
        )
    else:  # moderate
        return RegimeThresholds()


# ==============================================================================
# EXAMPLE USAGE AND DEMONSTRATION
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("REGIME DETECTOR - EXAMPLE USAGE")
    print("=" * 80)
    
    # Create detector with moderate risk profile
    detector = RegimeDetector(
        thresholds=get_default_thresholds_for_risk_profile('moderate'),
        verbose=True
    )
    
    # Simulate market data updates
    test_data = [
        (datetime(2024, 1, 15), 14.5, 102.5),  # Bull market
        (datetime(2024, 1, 16), 15.2, 103.0),
        (datetime(2024, 1, 17), 16.8, 103.5),
        (datetime(2024, 1, 18), 21.5, 104.0),  # Transition to chop
        (datetime(2024, 1, 19), 22.3, 104.5),
        (datetime(2024, 1, 22), 26.5, 105.5),  # Bear market
        (datetime(2024, 1, 23), 28.0, 106.0),
        (datetime(2024, 1, 24), 32.0, 107.0),  # Crisis
    ]
    
    for ts, vix, dxy in test_data:
        detector.update_market_data(timestamp=ts, vix=vix, dxy=dxy)
        
        # Test trade decisions for different asset classes
        for asset_class in [AssetClass.EQUITY_INDEX, AssetClass.COMMODITY]:
            decision = detector.allow_trade(
                asset_class=asset_class,
                direction=TradeDirection.LONG,
                symbol=f"TEST_{asset_class.name}"
            )
            print(f"  {asset_class.name}: {'ALLOW' if decision.allow_trade else 'BLOCK'} - {decision.reason}")
    
    print("\n" + "=" * 80)
    print("REGIME SUMMARY")
    print("=" * 80)
    summary = detector.get_regime_summary(lookback_days=30)
    print(json.dumps(summary, indent=2, default=str))
