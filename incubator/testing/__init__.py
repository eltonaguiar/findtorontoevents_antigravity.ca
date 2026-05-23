"""
Baby Strat Testing Utilities
============================

STANDARD TESTING FRAMEWORK - Use these functions, don't create your own!

This module provides standardized testing functions for all Baby Strategies.
AI agents should import and use these functions rather than creating custom testing code.

Usage:
    from incubator.testing import run_tier1_backtest, run_tier2_backtest, check_pass_criteria
    
    # Test your strategy
    result = run_tier1_backtest(MyStrategy, 'BTC/USDT', '1h')
    passed, reasons = check_pass_criteria(result)
    
Forward Testing:
    from incubator.testing import ForwardTestTracker, register_strategy_for_forward_test
    
    # Register strategy for forward testing
    register_strategy_for_forward_test('my_strategy', 'web_ai', backtest_metrics)
    
    # Update forward performance
    update_forward_performance('my_strategy', forward_metrics, trades)
    
    # Check if ready for graduation
    result = check_graduation_readiness('my_strategy')
"""

from .backtest_utils import (
    run_tier1_backtest,
    run_tier2_backtest, 
    run_full_backtest,
    check_pass_criteria,
    load_data,
    get_all_pairs,
    get_tier1_pairs,
    get_timeframes,
    PASS_CRITERIA
)

from .parallel_utils import (
    claim_strategy,
    release_claim,
    get_worker_id,
    is_strategy_claimed
)

from .forward_test_tracker import (
    ForwardTestTracker,
    StrategyGraduationCriteria,
    ForwardTestRecord,
    get_tracker,
    register_strategy_for_forward_test,
    update_forward_performance,
    check_graduation_readiness
)

from .forward_dashboard import (
    ForwardTestDashboard,
    generate_forward_report,
    get_graduation_candidates
)

from .forward_test_coordinator import (
    ForwardTestCoordinator
)

__all__ = [
    # Backtest utilities
    'run_tier1_backtest',
    'run_tier2_backtest',
    'run_full_backtest',
    'check_pass_criteria',
    'load_data',
    'get_all_pairs',
    'get_tier1_pairs',
    'get_timeframes',
    'PASS_CRITERIA',
    # Parallel coordination
    'claim_strategy',
    'release_claim',
    'get_worker_id',
    'is_strategy_claimed',
    # Forward testing
    'ForwardTestTracker',
    'StrategyGraduationCriteria',
    'ForwardTestRecord',
    'get_tracker',
    'register_strategy_for_forward_test',
    'update_forward_performance',
    'check_graduation_readiness',
    # Dashboard
    'ForwardTestDashboard',
    'generate_forward_report',
    'get_graduation_candidates',
    # Coordinator
    'ForwardTestCoordinator'
]
