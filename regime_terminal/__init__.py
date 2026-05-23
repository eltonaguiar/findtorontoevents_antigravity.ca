"""
Regime Terminal — Hidden Markov Model Market Regime Detection
Inspired by Renaissance Technologies' approach to probabilistic market state classification.

Uses Gaussian HMM to detect 7 hidden market regimes across crypto, forex, stocks,
penny stocks, and meme coins. Trains on price data (not trade outcomes), solving
the chicken-and-egg problem that plagues traditional ML trading systems.
"""

__version__ = "1.0.0"
