"""
AUDIT INTEGRATION FOR NEW STRATEGIES
=====================================
Integrates new strategies into ejaguiar1_stocks database and audit dashboard.

Tables affected:
- strategy_registry: Master catalog of all strategies
- at_raw_picks: Live signal tracking
- at_signal_outcomes: Forward test results
- at_strategy_symbol_performance: Per-symbol performance stats

Also updates audit_dashboard/index.html with new strategy tracking.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# STRATEGY DEFINITIONS FOR AUDIT
# =============================================================================

NEW_STRATEGIES = [
    # Prop-Firm Strategies
    {
        'strategy_name': 'KC_SCALP_v1',
        'strategy_type': 'PROP_FIRM',
        'category': 'SCALPING',
        'description': 'Keltner Channel compression breakout scalper',
        'target_win_rate': 0.75,
        'target_profit_factor': 2.0,
        'max_drawdown_target': 0.05,
        'timeframe': '1h',
        'hold_time_hours': 4,
        'position_size': 0.10,
        'risk_reward': 1.5,
        'asset_class': 'CRYPTO',
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT'],
        'entry_logic': 'Keltner band compression + volume expansion',
        'exit_logic': 'ATR-based TP/SL + 4h time stop',
        'status': 'APPROVED_FOR_FORWARD',
        'forward_test_allocation': 0.15
    },
    {
        'strategy_name': 'VWAP_ELITE_v1',
        'strategy_type': 'PROP_FIRM',
        'category': 'MEAN_REVERSION',
        'description': 'VWAP mean reversion with RSI and volatility filters',
        'target_win_rate': 0.70,
        'target_profit_factor': 1.8,
        'max_drawdown_target': 0.06,
        'timeframe': '1h',
        'hold_time_hours': 6,
        'position_size': 0.08,
        'risk_reward': 1.5,
        'asset_class': 'CRYPTO',
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'LINKUSDT', 'AVAXUSDT'],
        'entry_logic': 'Price >2std from VWAP + RSI extreme + vol filter',
        'exit_logic': 'Return to VWAP or 6h time stop',
        'status': 'APPROVED_FOR_FORWARD',
        'forward_test_allocation': 0.12
    },
    {
        'strategy_name': 'MTF_RSI_v1',
        'strategy_type': 'PROP_FIRM',
        'category': 'MOMENTUM',
        'description': 'Multi-timeframe RSI confluence for high-confidence entries',
        'target_win_rate': 0.72,
        'target_profit_factor': 1.9,
        'max_drawdown_target': 0.05,
        'timeframe': '1h',
        'hold_time_hours': 12,
        'position_size': 0.10,
        'risk_reward': 1.67,
        'asset_class': 'CRYPTO',
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT'],
        'entry_logic': 'RSI(1h,4h,1d) all aligned oversold/overbought',
        'exit_logic': 'RSI reversion to 50 or TP/SL',
        'status': 'APPROVED_FOR_FORWARD',
        'forward_test_allocation': 0.13
    },
    # General Trading Strategies
    {
        'strategy_name': 'FLASH_REV_v1',
        'strategy_type': 'GENERAL',
        'category': 'CRISIS_ALPHA',
        'description': 'Flash crash reversal hunter - extreme drop capture',
        'target_win_rate': 0.78,
        'target_profit_factor': 2.5,
        'max_drawdown_target': 0.08,
        'timeframe': '1h',
        'hold_time_hours': 12,
        'position_size': 0.05,
        'risk_reward': 2.0,
        'asset_class': 'CRYPTO',
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT', 'LINKUSDT'],
        'entry_logic': '>5% drop in 4h + RSI <25 + volume spike',
        'exit_logic': 'RSI recovery or 12h time stop',
        'status': 'APPROVED_FOR_FORWARD',
        'forward_test_allocation': 0.08
    },
    {
        'strategy_name': 'FUNDING_PRO_v1',
        'strategy_type': 'GENERAL',
        'category': 'FUNDING_ARB',
        'description': 'Funding rate momentum with RSI confirmation',
        'target_win_rate': 0.70,
        'target_profit_factor': 2.0,
        'max_drawdown_target': 0.06,
        'timeframe': '1h',
        'hold_time_hours': 8,
        'position_size': 0.08,
        'risk_reward': 1.67,
        'asset_class': 'CRYPTO',
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT'],
        'entry_logic': 'Extreme funding rate + RSI confirmation',
        'exit_logic': 'Funding normalization or TP/SL',
        'status': 'APPROVED_FOR_FORWARD',
        'forward_test_allocation': 0.10
    },
    {
        'strategy_name': 'HMA_TREND_v1',
        'strategy_type': 'GENERAL',
        'category': 'TREND_FOLLOWING',
        'description': 'HMA trend following with ADX confirmation',
        'target_win_rate': 0.65,
        'target_profit_factor': 1.8,
        'max_drawdown_target': 0.08,
        'timeframe': '1h',
        'hold_time_hours': 24,
        'position_size': 0.08,
        'risk_reward': 2.0,
        'asset_class': 'CRYPTO',
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'LINKUSDT'],
        'entry_logic': 'HMA slope + ADX>25 + pullback to HMA',
        'exit_logic': 'HMA reversal or trailing stop',
        'status': 'APPROVED_FOR_FORWARD',
        'forward_test_allocation': 0.08
    },
    {
        'strategy_name': 'BB_SQUEEZE_v1',
        'strategy_type': 'GENERAL',
        'category': 'BREAKOUT',
        'description': 'Bollinger Band squeeze breakout with volume',
        'target_win_rate': 0.68,
        'target_profit_factor': 1.8,
        'max_drawdown_target': 0.06,
        'timeframe': '1h',
        'hold_time_hours': 8,
        'position_size': 0.08,
        'risk_reward': 1.67,
        'asset_class': 'CRYPTO',
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT', 'MATICUSDT'],
        'entry_logic': 'BB width compression + breakout + volume',
        'exit_logic': 'Opposite band touch or TP/SL',
        'status': 'APPROVED_FOR_FORWARD',
        'forward_test_allocation': 0.08
    },
    {
        'strategy_name': 'MULTI_FACTOR_v1',
        'strategy_type': 'GENERAL',
        'category': 'ENSEMBLE',
        'description': 'Adaptive multi-factor scoring ensemble',
        'target_win_rate': 0.65,
        'target_profit_factor': 1.7,
        'max_drawdown_target': 0.07,
        'timeframe': '1h',
        'hold_time_hours': 12,
        'position_size': 0.06,
        'risk_reward': 1.67,
        'asset_class': 'CRYPTO',
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT'],
        'entry_logic': 'Composite score >0.6 from trend/momentum/vol/volume',
        'exit_logic': 'Score reversal or 12h time stop',
        'status': 'APPROVED_FOR_FORWARD',
        'forward_test_allocation': 0.06
    },
    {
        'strategy_name': 'keltner_hma_filter_enhanced',
        'strategy_type': 'ALPHA_ENGINE',
        'category': 'BREAKOUT',
        'description': 'Enhanced Keltner squeeze breakout + dynamic HMA slope with validation & volatility adjustment',
        'target_win_rate': 0.70,
        'target_profit_factor': 1.9,
        'max_drawdown_target': 0.05,
        'timeframe': '1h',
        'hold_time_hours': 8,
        'position_size': 0.10,
        'risk_reward': 1.67,
        'asset_class': 'CRYPTO',
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT', 'LINKUSDT'],
        'entry_logic': 'Keltner squeeze + HMA slope alignment (dynamic threshold)',
        'exit_logic': 'Volatility-adjusted ATR TP/SL',
        'status': 'APPROVED_FOR_FORWARD',
        'forward_test_allocation': 0.12
    },
    {
        'strategy_name': 'multi_sigma_volume_enhanced',
        'strategy_type': 'ALPHA_ENGINE',
        'category': 'MEAN_REVERSION',
        'description': 'Multi-sigma reversion + volume expansion with dynamic sigma threshold',
        'target_win_rate': 0.72,
        'target_profit_factor': 2.0,
        'max_drawdown_target': 0.06,
        'timeframe': '1h',
        'hold_time_hours': 6,
        'position_size': 0.09,
        'risk_reward': 1.33,
        'asset_class': 'CRYPTO',
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT'],
        'entry_logic': 'Dynamic sigma extreme + volume expansion',
        'exit_logic': 'ATR-based reversion TP/SL',
        'status': 'APPROVED_FOR_FORWARD',
        'forward_test_allocation': 0.11
    },
    {
        'strategy_name': 'hurst_rsi_extreme_enhanced',
        'strategy_type': 'ALPHA_ENGINE',
        'category': 'MEAN_REVERSION',
        'description': 'Hurst mean-reversion regime + dynamic RSI extremes with validation',
        'target_win_rate': 0.75,
        'target_profit_factor': 2.1,
        'max_drawdown_target': 0.04,
        'timeframe': '1h',
        'hold_time_hours': 12,
        'position_size': 0.11,
        'risk_reward': 2.0,
        'asset_class': 'CRYPTO',
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT'],
        'entry_logic': 'Hurst < dynamic threshold + RSI extreme',
        'exit_logic': 'Mean reversion TP/SL',
        'status': 'APPROVED_FOR_FORWARD',
        'forward_test_allocation': 0.13
    },
    # Baby Strategies - March 2026 Additions
    {
        'strategy_name': 'VWAP_RSI_INSTITUTIONAL',
        'strategy_type': 'BABY_STRATEGY',
        'category': 'MEAN_REVERSION',
        'description': 'VWAP + Triple RSI(14/21/50) institutional confluence mean reversion',
        'target_win_rate': 0.68,
        'target_profit_factor': 1.9,
        'max_drawdown_target': 0.06,
        'timeframe': '1h',
        'hold_time_hours': 6,
        'position_size': 0.08,
        'risk_reward': 1.5,
        'asset_class': 'CRYPTO',
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT'],
        'entry_logic': 'Price near VWAP + RSI(14)<40 + RSI(21)>50 + RSI(50)>55 + volume',
        'exit_logic': 'TP at 2-sigma VWAP band, SL at 1-sigma opposite band',
        'status': 'APPROVED_FOR_FORWARD',
        'forward_test_allocation': 0.10
    },
    {
        'strategy_name': 'LIQUIDATION_CASCADE_CONTRARIAN',
        'strategy_type': 'BABY_STRATEGY',
        'category': 'STRUCTURAL',
        'description': 'Catches wick bounces after liquidation cascades using volume/ATR spike detection',
        'target_win_rate': 0.62,
        'target_profit_factor': 1.8,
        'max_drawdown_target': 0.08,
        'timeframe': '1h',
        'hold_time_hours': 8,
        'position_size': 0.06,
        'risk_reward': 2.0,
        'asset_class': 'CRYPTO',
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'AVAXUSDT', 'DOGEUSDT', 'ADAUSDT'],
        'entry_logic': 'Wick >3x ATR + volume spike >3x + recovery >50% of wick',
        'exit_logic': 'TP at 50% of wick range, SL beyond wick extreme + 0.5 ATR',
        'status': 'APPROVED_FOR_FORWARD',
        'forward_test_allocation': 0.08
    },
    {
        'strategy_name': 'REGIME_SENTINEL_COMPOSITE',
        'strategy_type': 'BABY_STRATEGY',
        'category': 'META_STRATEGY',
        'description': 'Multi-factor regime classifier + extreme fear/greed contrarian signals',
        'target_win_rate': 0.75,
        'target_profit_factor': 2.2,
        'max_drawdown_target': 0.05,
        'timeframe': '1h',
        'hold_time_hours': 24,
        'position_size': 0.10,
        'risk_reward': 2.0,
        'asset_class': 'CRYPTO',
        'symbols': ['BTCUSDT'],  # Regime-based; applies to all crypto
        'entry_logic': 'ACCUMULATION regime + extreme fear (<15) + RSI<30',
        'exit_logic': 'Regime shift to DISTRIBUTION or extreme greed',
        'status': 'APPROVED_FOR_FORWARD',
        'forward_test_allocation': 0.12
    },
    {
        'strategy_name': 'RSI_PAIRS_ARBITRAGE',
        'strategy_type': 'BABY_STRATEGY',
        'category': 'STATISTICAL_ARBITRAGE',
        'description': 'Z-score spread + RSI-timed pairs arbitrage on correlated crypto',
        'target_win_rate': 0.74,
        'target_profit_factor': 2.2,
        'max_drawdown_target': 0.04,
        'timeframe': '1h',
        'hold_time_hours': 48,
        'position_size': 0.08,
        'risk_reward': 1.6,
        'asset_class': 'CRYPTO',
        'symbols': ['BTCUSDT', 'ETHUSDT'],
        'entry_logic': 'Z-score <-2.0 + RSI underperformer <35 (long spread)',
        'exit_logic': 'Z-score reversion to ±0.5 or stop at ±3.5',
        'status': 'APPROVED_FOR_FORWARD',
        'forward_test_allocation': 0.08
    }
]

# =============================================================================
# BABY STRATEGIES IMPORT SUPPORT
# =============================================================================

BABY_STRATEGY_MODULES = [
    ('vwap_rsi_institutional', 'VWAPRSIInstitutionalStrategy'),
    ('liquidation_cascade_contrarian', 'LiquidationCascadeContrarianStrategy'),
    ('regime_sentinel_composite', 'RegimeSentinelCompositeStrategy'),
    ('rsi_pairs_arbitrage', 'RSIPairsArbitrageStrategy'),
]


def import_baby_strategies():
    """
    Dynamically import baby strategies and return class mappings.
    
    Returns:
        Dict mapping strategy_name -> (module, class, NAME constant)
    """
    import importlib
    import sys
    from pathlib import Path
    
    strategies = {}
    baby_strat_path = Path(__file__).parent / 'baby_strategies'
    
    if str(baby_strat_path) not in sys.path:
        sys.path.insert(0, str(baby_strat_path))
    
    for module_name, class_name in BABY_STRATEGY_MODULES:
        try:
            module = importlib.import_module(module_name)
            strategy_class = getattr(module, class_name)
            name_constant = getattr(module, 'NAME', module_name)
            description = getattr(module, 'DESCRIPTION', '')
            symbols = getattr(module, 'SYMBOLS', [])
            
            strategies[name_constant] = {
                'module': module,
                'class': strategy_class,
                'name': name_constant,
                'description': description,
                'symbols': symbols,
            }
            logger.info(f"[LOADED] Baby strategy: {name_constant}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to import {module_name}: {e}")
    
    return strategies


def verify_baby_strategies():
    """
    Verify all baby strategies can be imported and instantiated.
    
    Returns:
        Tuple of (success_count, error_list)
    """
    strategies = import_baby_strategies()
    errors = []
    
    print("\n" + "="*70)
    print("BABY STRATEGIES VERIFICATION")
    print("="*70 + "\n")
    
    for name, info in strategies.items():
        try:
            # Instantiate the strategy
            instance = info['class']()
            
            # Check for required method
            if not hasattr(instance, 'generate_signals'):
                errors.append(f"{name}: Missing generate_signals method")
                print(f"❌ {name}: Missing generate_signals method")
                continue
            
            # Try calling with minimal data
            import pandas as pd
            import numpy as np
            
            test_data = pd.DataFrame({
                'open': np.random.uniform(50000, 51000, 100),
                'high': np.random.uniform(51000, 52000, 100),
                'low': np.random.uniform(49000, 50000, 100),
                'close': np.random.uniform(50000, 51000, 100),
                'volume': np.random.uniform(1000, 5000, 100),
            })
            
            signals = instance.generate_signals(test_data, symbol='BTCUSDT')
            
            print(f"[OK] {name}")
            print(f"   Description: {info['description'][:60]}...")
            print(f"   Symbols: {', '.join(info['symbols'][:3])}{'...' if len(info['symbols']) > 3 else ''}")
            print(f"   Test signals generated: {len(signals)}")
            
        except Exception as e:
            errors.append(f"{name}: {str(e)}")
            print(f"[FAIL] {name}: {e}")
    
    print(f"\n{'='*70}")
    print(f"Results: {len(strategies) - len(errors)}/{len(strategies)} strategies verified")
    print(f"{'='*70}\n")
    
    return len(strategies) - len(errors), errors


# =============================================================================
# SQL GENERATION
# =============================================================================

def generate_strategy_registry_sql() -> str:
    """Generate SQL for strategy_registry table."""
    sql = []
    sql.append("-- Strategy Registry Insert/Update Statements")
    sql.append(f"-- Generated: {datetime.now().isoformat()}")
    sql.append("")
    
    for strat in NEW_STRATEGIES:
        symbols_json = json.dumps(strat['symbols'])
        
        sql.append(f"""
INSERT INTO strategy_registry (
    strategy_name, strategy_type, category, description,
    target_win_rate, target_profit_factor, max_drawdown_target,
    timeframe, hold_time_hours, position_size, risk_reward,
    asset_class, symbols, entry_logic, exit_logic, status,
    forward_test_allocation, created_at, updated_at
) VALUES (
    '{strat['strategy_name']}',
    '{strat['strategy_type']}',
    '{strat['category']}',
    '{strat['description']}',
    {strat['target_win_rate']},
    {strat['target_profit_factor']},
    {strat['max_drawdown_target']},
    '{strat['timeframe']}',
    {strat['hold_time_hours']},
    {strat['position_size']},
    {strat['risk_reward']},
    '{strat['asset_class']}',
    '{symbols_json}',
    '{strat['entry_logic']}',
    '{strat['exit_logic']}',
    '{strat['status']}',
    {strat['forward_test_allocation']},
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    target_win_rate = {strat['target_win_rate']},
    target_profit_factor = {strat['target_profit_factor']},
    status = '{strat['status']}',
    forward_test_allocation = {strat['forward_test_allocation']},
    updated_at = NOW();
""")
    
    return '\n'.join(sql)


def generate_at_raw_picks_schema_update() -> str:
    """Generate SQL to update at_raw_picks schema for new strategies."""
    return """
-- Update at_raw_picks schema for new strategies
-- Adds columns if they don't exist

ALTER TABLE at_raw_picks 
ADD COLUMN IF NOT EXISTS strategy_category VARCHAR(50) AFTER strategy_name,
ADD COLUMN IF NOT EXISTS risk_reward DECIMAL(5,2) AFTER confidence,
ADD COLUMN IF NOT EXISTS hold_time_hours INT AFTER risk_reward,
ADD COLUMN IF NOT EXISTS pnl_pct_current DECIMAL(8,4) AFTER exit_price,
ADD COLUMN IF NOT EXISTS rsi_1h DECIMAL(5,2) AFTER pnl_pct_current,
ADD COLUMN IF NOT EXISTS hma_slope TINYINT AFTER rsi_1h,
ADD COLUMN IF NOT EXISTS volume_ratio DECIMAL(5,2) AFTER hma_slope;

-- Add index for new strategy lookups
CREATE INDEX IF NOT EXISTS idx_strategy_category ON at_raw_picks(strategy_category);
CREATE INDEX IF NOT EXISTS idx_strategy_status ON at_raw_picks(status, strategy_name);
"""


def generate_at_signal_outcomes_schema() -> str:
    """Generate SQL for at_signal_outcomes tracking."""
    return """
-- Ensure at_signal_outcomes has strategy tracking
ALTER TABLE at_signal_outcomes
ADD COLUMN IF NOT EXISTS strategy_category VARCHAR(50) AFTER strategy_name,
ADD COLUMN IF NOT EXISTS exit_reason VARCHAR(50) AFTER pnl_pct,
ADD COLUMN IF NOT EXISTS max_drawdown_pct DECIMAL(8,4) AFTER exit_reason,
ADD COLUMN IF NOT EXISTS hold_time_hours DECIMAL(8,2) AFTER max_drawdown_pct;

-- Index for performance analysis
CREATE INDEX IF NOT EXISTS idx_outcomes_category ON at_signal_outcomes(strategy_category, exit_time);
"""


def generate_at_strategy_symbol_performance_sql() -> str:
    """Generate SQL for per-strategy per-symbol performance table."""
    return """
-- Create/update strategy_symbol_performance table
CREATE TABLE IF NOT EXISTS at_strategy_symbol_performance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    strategy_name VARCHAR(100) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    total_trades INT DEFAULT 0,
    wins INT DEFAULT 0,
    losses INT DEFAULT 0,
    win_rate DECIMAL(5,4) DEFAULT 0,
    avg_win_pct DECIMAL(10,6) DEFAULT 0,
    avg_loss_pct DECIMAL(10,6) DEFAULT 0,
    profit_factor DECIMAL(8,4) DEFAULT 0,
    total_pnl_pct DECIMAL(10,6) DEFAULT 0,
    max_drawdown_pct DECIMAL(8,4) DEFAULT 0,
    last_trade_time TIMESTAMP NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_strat_sym (strategy_name, symbol),
    INDEX idx_performance (win_rate, total_trades)
) ENGINE=InnoDB;

-- Insert placeholder rows for new strategies
"""


# =============================================================================
# DASHBOARD INTEGRATION
# =============================================================================

def generate_dashboard_config() -> Dict:
    """Generate configuration for audit dashboard."""
    return {
        'new_strategies': NEW_STRATEGIES,
        'strategy_groups': {
            'PROP_FIRM': [s['strategy_name'] for s in NEW_STRATEGIES if s['strategy_type'] == 'PROP_FIRM'],
            'GENERAL': [s['strategy_name'] for s in NEW_STRATEGIES if s['strategy_type'] == 'GENERAL']
        },
        'performance_targets': {
            'PROP_FIRM': {'win_rate': 0.70, 'profit_factor': 1.8},
            'GENERAL': {'win_rate': 0.65, 'profit_factor': 1.6}
        },
        'colors': {
            'KC_SCALP_v1': '#4CAF50',
            'VWAP_ELITE_v1': '#2196F3',
            'MTF_RSI_v1': '#9C27B0',
            'FLASH_REV_v1': '#FF9800',
            'FUNDING_PRO_v1': '#00BCD4',
            'HMA_TREND_v1': '#E91E63',
            'BB_SQUEEZE_v1': '#795548',
            'MULTI_FACTOR_v1': '#607D8B'
        }
    }


def generate_dashboard_js() -> str:
    """Generate JavaScript for dashboard integration."""
    config = generate_dashboard_config()
    
    js = f"""
// NEW STRATEGIES DASHBOARD INTEGRATION
// Auto-generated: {datetime.now().isoformat()}

const NEW_STRATEGIES_CONFIG = {json.dumps(config, indent=2)};

// Strategy group colors for charting
const STRATEGY_COLORS = {json.dumps(config['colors'])};

// Performance target thresholds
const PERFORMANCE_TARGETS = {json.dumps(config['performance_targets'])};

// Filter functions for dashboard
function isNewStrategy(strategyName) {{
    return NEW_STRATEGIES_CONFIG.new_strategies.some(s => s.strategy_name === strategyName);
}}

function getStrategyType(strategyName) {{
    const strat = NEW_STRATEGIES_CONFIG.new_strategies.find(s => s.strategy_name === strategyName);
    return strat ? strat.strategy_type : 'UNKNOWN';
}}

function getStrategyTarget(strategyName, metric) {{
    const type = getStrategyType(strategyName);
    return PERFORMANCE_TARGETS[type]?.[metric] || null;
}}

// Health score calculation for new strategies
function calculateStrategyHealth(strategyName, actualWinRate, actualPF) {{
    const targetWR = getStrategyTarget(strategyName, 'win_rate') || 0.65;
    const targetPF = getStrategyTarget(strategyName, 'profit_factor') || 1.6;
    
    const wrScore = Math.min(actualWinRate / targetWR, 1.5);
    const pfScore = actualPF === Infinity ? 1.5 : Math.min(actualPF / targetPF, 1.5);
    
    const healthScore = (wrScore + pfScore) / 2 * 100;
    
    if (healthScore >= 90) return {{ status: 'HEALTHY', badge: '[GREEN]', score: healthScore }};
    if (healthScore >= 70) return {{ status: 'WATCH', badge: '[YELLOW]', score: healthScore }};
    return {{ status: 'DEGRADED', badge: '[RED]', score: healthScore }};
}}

// Export for use in dashboard
if (typeof module !== 'undefined' && module.exports) {{
    module.exports = {{ NEW_STRATEGIES_CONFIG, STRATEGY_COLORS, PERFORMANCE_TARGETS,
                       isNewStrategy, getStrategyType, calculateStrategyHealth }};
}}
"""
    return js


# =============================================================================
# FILE GENERATION
# =============================================================================

def save_all_files():
    """Save all integration files."""
    output_dir = Path('audit_integration')
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # SQL Files
    sql_files = {
        '01_strategy_registry.sql': generate_strategy_registry_sql(),
        '02_raw_picks_schema.sql': generate_at_raw_picks_schema_update(),
        '03_signal_outcomes_schema.sql': generate_at_signal_outcomes_schema(),
        '04_symbol_performance.sql': generate_at_strategy_symbol_performance_sql(),
    }
    
    for filename, content in sql_files.items():
        filepath = output_dir / filename
        with open(filepath, 'w') as f:
            f.write(content)
        logger.info(f"Saved {filepath}")
    
    # Combined SQL
    combined_sql = '\n\n'.join([
        "-- NEW STRATEGY AUDIT INTEGRATION",
        f"-- Generated: {datetime.now().isoformat()}",
        "-- Run these SQL statements in order\n",
        sql_files['01_strategy_registry.sql'],
        "\n--\n-- Schema Updates\n--\n",
        sql_files['02_raw_picks_schema.sql'],
        sql_files['03_signal_outcomes_schema.sql'],
        sql_files['04_symbol_performance.sql']
    ])
    
    combined_path = output_dir / f'ALL_INTEGRATION_SQL_{timestamp}.sql'
    with open(combined_path, 'w') as f:
        f.write(combined_sql)
    logger.info(f"Saved combined SQL: {combined_path}")
    
    # Dashboard JS
    js_content = generate_dashboard_js()
    js_path = output_dir / f'new_strategies_dashboard_{timestamp}.js'
    with open(js_path, 'w') as f:
        f.write(js_content)
    logger.info(f"Saved dashboard JS: {js_path}")
    
    # Strategy config JSON
    config = generate_dashboard_config()
    config_path = output_dir / f'new_strategies_config_{timestamp}.json'
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    logger.info(f"Saved config JSON: {config_path}")
    
    # README
    readme = f"""# New Strategy Audit Integration
Generated: {datetime.now().isoformat()}

## Files

### SQL Files (run in order)
1. `01_strategy_registry.sql` - Register new strategies in master catalog
2. `02_raw_picks_schema.sql` - Update at_raw_picks table schema
3. `03_signal_outcomes_schema.sql` - Update at_signal_outcomes schema
4. `04_symbol_performance.sql` - Create per-symbol performance tracking
5. `ALL_INTEGRATION_SQL_{{timestamp}}.sql` - All statements combined

### Dashboard Files
- `new_strategies_dashboard_{{timestamp}}.js` - Dashboard JavaScript integration
- `new_strategies_config_{{timestamp}}.json` - Strategy configuration

## New Strategies Added

| Strategy | Type | Target WR | Allocation |
|----------|------|-----------|------------|
"""
    for s in NEW_STRATEGIES:
        readme += f"| {s['strategy_name']} | {s['strategy_type']} | {s['target_win_rate']:.0%} | {s['forward_test_allocation']:.0%} |\n"
    
    readme += f"""
## Integration Steps

1. Run SQL files in order against ejaguiar1_stocks database
2. Copy dashboard JS to audit_dashboard/scripts/
3. Include JS in audit_dashboard/index.html
4. Deploy updated dashboard
5. Start forward testing for approved strategies

## Database Connection

```python
import mysql.connector

conn = mysql.connector.connect(
    host='mysql.50webs.com',
    user='ejaguiar1_stocks',
    password='your_password',
    database='ejaguiar1_stocks'
)
```
"""
    
    readme_path = output_dir / 'README.md'
    with open(readme_path, 'w') as f:
        f.write(readme)
    logger.info(f"Saved README: {readme_path}")
    
    return output_dir


# =============================================================================
# MAIN
# =============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Audit Integration for New Strategies")
    parser.add_argument("--verify-baby", action="store_true", help="Verify baby strategies can be imported")
    parser.add_argument("--generate-only", action="store_true", help="Only generate integration files")
    args = parser.parse_args()
    
    if args.verify_baby:
        success_count, errors = verify_baby_strategies()
        if errors:
            print(f"\n❌ Errors found:")
            for error in errors:
                print(f"   - {error}")
        return success_count
    
    logger.info("=" * 80)
    logger.info("AUDIT INTEGRATION - NEW STRATEGIES")
    logger.info("=" * 80)
    
    output_dir = save_all_files()
    
    # Count by type
    prop_firm = sum(1 for s in NEW_STRATEGIES if s['strategy_type'] == 'PROP_FIRM')
    general = sum(1 for s in NEW_STRATEGIES if s['strategy_type'] == 'GENERAL')
    alpha_engine = sum(1 for s in NEW_STRATEGIES if s['strategy_type'] == 'ALPHA_ENGINE')
    baby_strat = sum(1 for s in NEW_STRATEGIES if s['strategy_type'] == 'BABY_STRATEGY')
    
    logger.info("=" * 80)
    logger.info(f"Integration files saved to: {output_dir}")
    logger.info(f"Total strategies: {len(NEW_STRATEGIES)}")
    logger.info(f"  - Prop-Firm: {prop_firm}")
    logger.info(f"  - General: {general}")
    logger.info(f"  - Alpha Engine: {alpha_engine}")
    logger.info(f"  - Baby Strategies: {baby_strat}")
    logger.info("=" * 80)
    
    print(f"\n[OK] Integration files generated in: {output_dir}")
    print(f"\nStrategy Summary:")
    print(f"  - Prop-Firm: {prop_firm}")
    print(f"  - General: {general}")
    print(f"  - Alpha Engine: {alpha_engine}")
    print(f"  - Baby Strategies: {baby_strat}")
    print(f"\nNext steps:")
    print(f"  1. Review SQL files in {output_dir}")
    print(f"  2. Run: python audit_integration_new_strategies.py --verify-baby")
    print(f"  3. Run against ejaguiar1_stocks database")
    print(f"  4. Update audit_dashboard/index.html with new JS")
    print(f"  5. Start forward testing approved strategies")
    
    # Optionally verify baby strategies
    if not args.generate_only:
        print(f"\n[OPTIONAL] Verify baby strategies:")
        print(f"  python audit_integration_new_strategies.py --verify-baby")


if __name__ == "__main__":
    main()
