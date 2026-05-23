"""
QuanEngine — High-Performance Crypto Prediction Engine
======================================================
Regime-aware ensemble system targeting prop-firm grade success rates.

Architecture:
  Market Data → RegimeRouter → Strategy Pools → QuanEnsemble
  → ModeDispatcher → RiskGate → ForwardTracker → Output

Targets: 65-75% WR, Sharpe > 2.0, Max DD < 15%
"""
__version__ = "1.0.0"
