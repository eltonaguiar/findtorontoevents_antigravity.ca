"""
ALPHA_ENGINE — Incubator Pipeline
==================================
Discovers high-probability trading strategies via systematic parameter
permutation, vectorized backtesting, and multi-objective ranking.

Workflow:
  1. seed_extractor   → top strategies from audit DB + live stats
  2. parameter_space  → tunable param definitions per strategy family
  3. permutation_engine → Latin Hypercube / Sobol sampling
  4. fast_backtester   → vectorized BTC-USD & ETH-USD backtests
  5. ranker            → composite score ranking
  6. incubator_db      → persist candidates with status=INCUBATOR
  7. run_incubator     → orchestrator CLI

Usage:
  python -m alpha_engine.incubator.run_incubator          # full pipeline
  python -m alpha_engine.incubator.run_incubator --seeds   # show seeds only
  python -m alpha_engine.incubator.run_incubator --rank    # rank existing results
"""
