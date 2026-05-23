"""Mutation Lab — Strategy evolution pipeline.

SCOUT -> MUTATE+BACKTEST -> PROMOTE pipeline that backtests all DNA
mutations on real Binance 4h klines before they go live.

Stages:
  1. SCOUT:   Query audit DB for top-15 winners & bottom-15 losers
  2. MUTATE:  Generate mutations (A=amplify, B=flip, C=fix) and backtest
              each on BTCUSDT, ETHUSDT, SOLUSDT (750 bars of 4h data)
  3. PROMOTE: Apply quality gates, register winners in strategy_registry.db,
              write final picks to genome/data/mutation_lab_picks.json

Quality gates: WR >= 45%, Sharpe >= 0.5, max_dd < 20%, min_trades >= 5

Super Mutations (v3.0):
  5 blended strategies crossing the ONLY 3 profitable systems:
  - keltner_rsi_confluence_v2  — Keltner squeeze + dual RSI oversold
  - consensus_deep_value_hybrid — Consensus + RSI capitulation + F&G
  - genesis_momentum_blend     — GENESIS scoring + momentum confirmation
  - ml_keltner_adaptive        — ML features + adaptive Keltner channels
  - multi_system_conviction_filter — Meta-strategy: 3+ layers must agree
"""

__version__ = "3.0.0"
