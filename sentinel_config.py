"""
Sentinel Fund Configuration - Hedge Fund-Style Risk Management Parameters
Based on Mercury AI feedback and institutional best practices
"""

from dataclasses import dataclass
from typing import Dict, List

@dataclass
class RiskParameters:
    """Risk budgeting parameters"""
    CORE_BOOK_WEIGHT: float = 0.80           # 80% of capital to core
    INCUBATOR_WEIGHT: float = 0.20           # 20% to incubator
    
    MAX_POSITION_SIZE_CORE: float = 0.02     # 2% per core position
    MAX_POSITION_SIZE_INCUBATOR: float = 0.005  # 0.5% per incubator position
    
    PORTFOLIO_MAX_DD_PERCENT: float = 0.10   # 10% hard stop
    COMPONENT_MAX_DD_PERCENT: float = 0.05   # 5% per component stop
    
    KELLY_FRACTION: float = 0.25             # Quarter Kelly for safety

@dataclass
class SignalGates:
    """Signal filtering gates"""
    MIN_RR_DEFAULT: float = 1.5              # Minimum risk/reward
    MIN_RR_MERCURY: float = 1.4              # Mercury can use slightly lower
    
    CONSENSUS_MIN_SYSTEMS: int = 2           # At least 2 systems must agree
    FRESHNESS_MAX_MINUTES: int = 15          # Signal must be < 15 min old
    
    # Direction filtering for Alpha Engine
    ALPHA_SHORT_ONLY: bool = True            # Block Alpha long signals
    ALPHA_MIN_LONG_WR: float = 0.30          # Minimum long win rate to allow

@dataclass
class PerformanceThresholds:
    """Performance gates for core book inclusion"""
    MIN_EXPECTANCY_PERCENT: float = 0.0      # Must be profitable
    MIN_WIN_RATE: float = 0.30               # Minimum 30% win rate
    MIN_TRADES_FOR_INCLUSION: int = 10       # Need sample size
    
    # Demotion thresholds
    DEMOTE_EXPECTANCY_THRESHOLD: float = 0.0  # Demote if expectancy < 0
    DEMOTE_WR_THRESHOLD: float = 0.30         # Demote if WR < 30%
    DEMOTE_DD_THRESHOLD: float = 0.05         # Demote if DD > 5%

@dataclass
class RegimeDetection:
    """Market regime parameters"""
    HURST_TRENDING_THRESHOLD: float = 0.6     # Hurst > 0.6 = trending
    HURST_MEAN_REVERT_THRESHOLD: float = 0.4  # Hurst < 0.4 = mean-reverting
    
    VOLATILITY_LOOKBACK: int = 24             # Hours for vol calculation
    HIGH_VOL_PERCENTILE: float = 0.80         # Top 20% = high vol
    LOW_VOL_PERCENTILE: float = 0.20          # Bottom 20% = low vol

# Strategy classifications
CORE_STRATEGIES: List[str] = [
    "funding_carry",
    "funding_carry_elite",
    "autocorrelation_exploiter",
    "hurst_regime_adaptive",
    "volume_profile_value_area",
    "adaptive_vr_confluence",
    "multi_sigma_reversal",
    "baby_battleground",
    "claws_of_doom",
]

KILL_LIST_STRATEGIES: List[str] = [
    "smart_money_fvg",
    "m2_liquidity_lag",
    "ema_crossover", 
    "bollinger_squeeze",
]

# Strategy family classifications
MEAN_REVERSION_STRATEGIES: List[str] = [
    "autocorrelation_exploiter",
    "multi_sigma_reversal",
    "volume_profile_value_area",
]

TREND_FOLLOWING_STRATEGIES: List[str] = [
    "hurst_regime_adaptive",
    "adaptive_vr_confluence",
]

FUNDING_ARB_STRATEGIES: List[str] = [
    "funding_carry",
    "funding_carry_elite",
]

# Initialize config instances
RISK = RiskParameters()
GATES = SignalGates()
PERFORMANCE = PerformanceThresholds()
REGIME = RegimeDetection()

# File paths
CORE_WHITELIST_PATH = "core_whitelist.json"
KILL_LIST_PATH = "kill_list.json"
PERFORMANCE_TRACKER_PATH = "sentinel_performance_tracker.json"
EQUITY_CURVES_PATH = "sentinel_equity_curves.json"
DASHBOARD_OUTPUT_PATH = "sentinel_pm_dashboard.json"

# Time constants
REFRESH_INTERVAL_SECONDS: int = 60         # How often to refresh
WEEKLY_REPORT_DAY: int = 0                  # Monday (0=Monday, 6=Sunday)
