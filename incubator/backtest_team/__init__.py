"""
Baby Strat Backtest Team
========================

A modular backtesting system for validating Baby Strat strategies.

Components:
- controller.py: Orchestrates backtest runs
- runner.py: Executes individual backtests
- validator.py: Validates strategy quality and uniqueness

Usage:
    from backtest_team.controller import BacktestController
    controller = BacktestController(days=90)
    report = controller.run()
"""

__version__ = "1.0.0"
__all__ = ['controller', 'runner', 'validator']
