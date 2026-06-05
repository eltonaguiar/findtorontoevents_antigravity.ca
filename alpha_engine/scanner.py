#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Live Market Scanner v1.1
========================================
Main entry point. Fetches real market data, runs 100 strategies across
crypto, forex, and equities, ranks signals with ML, manages picks.

v1.1: Added regime-conditional strategy routing (Action 3.1).
      Detects market regime (trending/ranging/transitional) per symbol
      using ADX + volatility, then annotates each signal with regime
      compatibility metadata. Incompatible signals are NOT blocked,
      but flagged with a regime_warning and penalized 10% on ML score.

Usage:
  python scanner.py                   # Full scan, all strategies
  python scanner.py --crypto-only     # Crypto strategies only
  python scanner.py --forex-only      # Forex strategies only
  python scanner.py --dry-run         # Show signals without opening picks
  python scanner.py --train-ml        # Train ML model on historical picks
  python scanner.py --status          # Show current portfolio status

No fake data. No placeholder signals. If no strategy fires, output is empty.
All signals stored in SQLite for forward-looking validation.
"""

from __future__ import annotations

import sys
_orig_print = print
def print(*args, **kwargs):
    """Robust print that survives closed stderr/stdout on Windows."""
    try:
        _orig_print(*args, **kwargs)
    except (ValueError, OSError):
        pass

# Force UTF-8 for subprocess/Windows output stability
if sys.platform == "win32":
    import os
    os.environ.setdefault("PYTHONUTF8", "1")
    # reconfigure() removed -- crashes under subprocess/pipes on Windows.
    # PYTHONUTF8=1 env var (set above) handles UTF-8 for all I/O.

import argparse
import json
import logging
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path

# Import standardized win rate calculation
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root for shared/
from shared import calculate_win_rate

import numpy as np

try:
    from alpha_engine.feed_hygiene import (
        sanitize_active_picks,
        has_deterministic_loss_pattern,
        _DEAD_SYMBOLS,
    )
except ImportError:
    sanitize_active_picks = lambda picks, label="": picks
    has_deterministic_loss_pattern = lambda symbol, prices: False
    _DEAD_SYMBOLS = set()

# Polymarket Volume Spike Filter: invalidate session cache at scan start
# so fresh signals are picked up each scan cycle.
try:
    from alpha_engine.polymarket_volume_filter import invalidate_cache as _pm_invalidate_cache
    _HAS_PM_VOL_FILTER = True
except ImportError:
    _pm_invalidate_cache = None
    _HAS_PM_VOL_FILTER = False

try:
    from alpha_engine.crypto_feature_pipeline import compute_crypto_features as _compute_crypto_features
    _HAS_CRYPTO_FEATURE_PIPELINE = True
except ImportError:
    _compute_crypto_features = None
    _HAS_CRYPTO_FEATURE_PIPELINE = False

# ---------------------------------------------------------------------------
# Signal frequency throttle -- cap signals per strategy per scan cycle
# ---------------------------------------------------------------------------
MAX_SIGNALS_PER_STRATEGY_PER_SCAN = 5

# Last-run data-fetch diagnostics. Populated by main() so the CLI entry point
# can distinguish a real-empty market (exit 0 + ::warning::) from a
# data-provider outage (exit 1 + ::error::). Without this the scanner exited
# GitHub Actions GREEN on a total yfinance failure — "fail-open masking",
# the same gap closed for etf_scanner.py / bond_scanner.py. Resolver-fix Step 2.
# scan_ran stays False for --train-ml / --status invocations so the guard
# does not fire on non-scanning runs.
LAST_RUN_DIAGNOSTICS: dict = {
    "scan_ran": False,
    "symbols_requested": 0,
    "symbols_loaded": 0,
    "raw_signals": 0,
}


def _sanitize_for_json(obj):
    """Recursively replace NaN/Infinity with None so json.dump never emits invalid tokens."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items() if not k.startswith("_raw_")}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if hasattr(obj, "item"):
        v = obj.item()
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
    return obj
import pandas as pd
import yfinance as yf

# Ensure local imports work when running as script
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (
    ALL_SYMBOLS, CRYPTO_SYMBOLS, FOREX_SYMBOLS, EQUITY_SYMBOLS,
    COMMODITY_SYMBOLS, FUTURES_SYMBOLS, ETF_SYMBOLS, BOND_SYMBOLS,
    DATA_DIR, ML_MODEL_PATH, CATEGORY_RISK, TRAILING_STOP, TRAIL_ACTIVATE_PCT,
    MAX_OPEN_PICKS, MAX_PICKS_PER_STRATEGY, MAX_PICKS_PER_SYMBOL,
    MAX_RISK_PER_TRADE, MAX_ALLOCATION_PER_PICK, MAX_TOTAL_EXPOSURE,
    MAX_CORRELATED_EXPOSURE, STARTING_CAPITAL, MAX_SAME_DIRECTION_CRYPTO,
    YF_PERIOD_DAILY, YF_INTERVAL_DAILY,
    FEAR_GREED_URL, COINGECKO_BASE,
    OBI_SHADOW_MODE,
    resolve_yf_symbols,
    MIN_ELITE_SCORE_FOR_PICKS,
    STRATEGY_MIN_CONFIDENCE,
)
from database import SQLiteStore
from elite_scorer import compute_elite_score
from ml_ranker import MLSignalRanker
from position_sizing import get_position_size, get_kelly_fraction
# P3: Regime-aware position sizing (5 rules -- 2026-05-24)
try:
    from alpha_engine.regime_position_sizer import compute_position_size as compute_regime_position_size
    _HAS_REGIME_POSITION_SIZER = True
except ImportError:
    compute_regime_position_size = None
    _HAS_REGIME_POSITION_SIZER = False
try:
    from orderbook_strategies import get_orderbook_scores_batch
except ImportError:
    get_orderbook_scores_batch = None

try:
    from obi_velocity import compute_obi_velocity_batch
except ImportError:
    compute_obi_velocity_batch = None

# Coinalyze derivatives data (OI, funding, long/short ratio) -- free Binance endpoints
try:
    from coinalyze_client import get_derivatives_batch
except ImportError:
    get_derivatives_batch = None

# OHLCV provider failover (Tiingo -> Polygon -> AlphaVantage). yfinance is
# hard-blocked from GitHub Actions runner IPs; this fills daily OHLCV gaps so
# a Yahoo outage degrades gracefully instead of silently emptying the scan.
# No-op (transparent) when no provider key is configured. CLAUDE.md API-Failover-Rule.
try:
    from ohlcv_failover import fetch_ohlcv_failover, failover_available
    _HAS_OHLCV_FAILOVER = True
except ImportError:
    try:
        from alpha_engine.ohlcv_failover import fetch_ohlcv_failover, failover_available
        _HAS_OHLCV_FAILOVER = True
    except ImportError:
        _HAS_OHLCV_FAILOVER = False

# DefiLlama TVL/stablecoin capital flow signals -- free, no auth
try:
    from defillama_signals import get_defi_composite_signal
except ImportError:
    get_defi_composite_signal = None

# Chi-squared validated technical features (7 indicators, 92.4% XGBoost accuracy)
try:
    from technical_features import compute_technical_features as _compute_tech_features
except ImportError:
    _compute_tech_features = None

# Cross-sectional ranking features (Liu et al. 2022 JFE -- ranking > absolute forecasting)
try:
    from cross_sectional import inject_cross_sectional_features
except ImportError:
    inject_cross_sectional_features = None

# Feature populator: compute real OHLCV-derived features at pick creation time
# (Phase 16 -- kills 25 dead features by wiring real data into every pick)
try:
    from feature_populator import populate_batch as populate_features_batch
except ImportError:
    populate_features_batch = None

# VPIN: Volume-Synchronized Probability of Informed Trading (Easley et al. 2012)
try:
    from vpin_signal import get_vpin_scores_batch, VPIN_STRATEGIES
except ImportError:
    get_vpin_scores_batch = None
    VPIN_STRATEGIES = {}

# LunarCrush Galaxy Score: social sentiment for crypto (free/keyed API)
try:
    from lunarcrush_signal import get_lunarcrush_scores_batch, LUNARCRUSH_STRATEGIES
except ImportError:
    get_lunarcrush_scores_batch = None
    LUNARCRUSH_STRATEGIES = {}

# Portfolio Correlation Guard: blocks picks too correlated with existing positions
try:
    from portfolio_correlation_guard import filter_picks_by_correlation as _corr_filter
    _HAS_CORR_GUARD = True
except ImportError:
    _corr_filter = None
    _HAS_CORR_GUARD = False

# Kill Switch: auto-halt signal generation on drawdown/SL spikes/win-rate collapse
try:
    from kill_switch import check_kill_conditions as _check_kill_conditions
    _HAS_KILL_SWITCH = True
except ImportError:
    _check_kill_conditions = None
    _HAS_KILL_SWITCH = False

# FWLS: context-weighted blend of ml_score + confidence
try:
    from fwls_stacker import fwls_blend as _fwls_blend
except ImportError:
    _fwls_blend = None

# Direction Balance Guard: cap LONG/SHORT ratio by Fear & Greed regime
try:
    from direction_balance_guard import enforce_direction_balance as _enforce_direction_balance
    _HAS_DIRECTION_GUARD = True
except ImportError:
    _enforce_direction_balance = None
    _HAS_DIRECTION_GUARD = False

# Regime Sentinel: 4-state on-chain cycle classifier (MVRV + F&G + funding)
try:
    from regime_sentinel import get_regime_sentinel
    _HAS_REGIME_SENTINEL = True
except ImportError:
    get_regime_sentinel = None
    _HAS_REGIME_SENTINEL = False

# Pine Script indicator filters: Squeeze Momentum, EMA Cloud, VWAP-BB Squeeze, Safety Index
try:
    from pine_to_python_indicators import pine_indicator_filter as _pine_indicator_filter
    _HAS_PINE_FILTERS = True
except ImportError:
    _pine_indicator_filter = None
    _HAS_PINE_FILTERS = False

# Conformal Prediction: calibrated uncertainty intervals for position sizing (ICLR 2024)
try:
    from conformal_sizing import ConformalSizer
    _conformal_sizer = ConformalSizer(coverage=0.90)
except ImportError:
    _conformal_sizer = None

# Winner Indicator System: MSI + EQS + RiskFilter (reverse-engineered from closed picks)
try:
    from winner_indicator_system import score_pick as _score_winner_indicators
    _HAS_WINNER_INDICATORS = True
except ImportError:
    _score_winner_indicators = None
    _HAS_WINNER_INDICATORS = False

# Exit reason normalizer (issue #186 -- canonical buckets for downstream consumers)
try:
    from tldr_winner_report import normalize_exit_reason as _normalize_exit_reason
except ImportError:
    _normalize_exit_reason = None

from crypto_strategies import CRYPTO_STRATEGIES
from forex_strategies import FOREX_STRATEGIES
from equity_strategies import EQUITY_STRATEGIES
from commodities_strategies import COMMODITY_STRATEGIES
from futures_strategies import FUTURES_STRATEGIES
from etf_strategies import ETF_STRATEGIES
from bond_strategies import BOND_STRATEGIES
from indicators import rsi as compute_rsi, hma_slope as compute_hma_slope, volume_ratio as compute_volume_ratio
from transaction_costs import (
    COST_MODELS,
    get_round_trip_cost, apply_costs, adjust_tp_for_costs,
    adjusted_win_rate as compute_adjusted_win_rate,
    get_cost_model,
)

from alpha_engine import config as _ae_config  # SSO for FOREX kill-switch
# Non-Crypto Quality Gate: macro filters for equity/forex picks (VIX, SPY SMA200, FX vol regime)
try:
    from non_crypto_quality_gate import (
        equity_macro_gate as _equity_macro_gate,
        forex_macro_gate as _forex_macro_gate,
        vix_confidence_adj as _vix_confidence_adj,
        is_killed as _nc_is_killed,
        forex_conf_cap as _forex_conf_cap,
        equity_conf_cap as _equity_conf_cap,
        bond_macro_gate as _bond_macro_gate,
        vix_bond_confidence_adj as _vix_bond_confidence_adj,
        bond_conf_cap as _bond_conf_cap,
    )
    _HAS_NC_QUALITY_GATE = True
except ImportError:
    _equity_macro_gate = None
    _forex_macro_gate = None
    _vix_confidence_adj = None
    _nc_is_killed = None
    _forex_conf_cap = None
    _equity_conf_cap = None
    _bond_macro_gate = None
    _vix_bond_confidence_adj = None
    _bond_conf_cap = None
    _HAS_NC_QUALITY_GATE = False

# Dynamic Universe: hot symbols from Binance Futures ranked by momentum/volume/volatility
try:
    from dynamic_universe import load_dynamic_symbols, load_dynamic_symbol_meta
    _HAS_DYNAMIC_UNIVERSE = True
except ImportError:
    load_dynamic_symbols = None
    load_dynamic_symbol_meta = None
    _HAS_DYNAMIC_UNIVERSE = False

# Fast variants: relaxed-threshold mutations of proven strategies for higher signal frequency
try:
    from fast_variants import FAST_VARIANT_STRATEGIES
except ImportError:
    FAST_VARIANT_STRATEGIES = {}

# Advanced strategies: dip amplifiers, on-chain, quant overlays
try:
    from advanced_strategies import ADVANCED_STRATEGIES
except ImportError:
    ADVANCED_STRATEGIES = {}

# DNA scalp variants: optimized strategy x symbol combos from backtesting
try:
    from kira_dna_scalp_variants import DNA_SCALP_STRATEGIES
    ADVANCED_STRATEGIES.update(DNA_SCALP_STRATEGIES)
except ImportError:
    pass

# Keltner Evolved: genetically evolved compression-expansion variants (genome evolution)
try:
    from keltner_evolved import KELTNER_EVOLVED_STRATEGIES
except ImportError:
    KELTNER_EVOLVED_STRATEGIES = {}

# Super Strategies: 10 confluence-based strategies combining best proven edges
try:
    from super_strategies import SUPER_STRATEGIES
except ImportError:
    SUPER_STRATEGIES = {}

# Quant Strategies: pairs trading, TSMOM, momentum blends (Gemini research #9)
try:
    from quant_strategies import QUANT_STRATEGIES
except ImportError:
    QUANT_STRATEGIES = {}

# Untapped Strategies: Google Trends contrarian, rare high-WR signals (Gemini research #10)
try:
    from untapped_strategies import UNTAPPED_STRATEGIES
except ImportError:
    UNTAPPED_STRATEGIES = {}

# COT Positioning: CFTC commercial positioning for forex (55-62% WR, free data)
try:
    from cot_positioning import COT_STRATEGIES
except ImportError:
    COT_STRATEGIES = {}

# TVL Momentum: DefiLlama capital flow signals → tradeable picks (free API, no key)
try:
    from tvl_momentum_strategy import TVL_MOMENTUM_STRATEGIES
except ImportError:
    TVL_MOMENTUM_STRATEGIES = {}

# TTM Squeeze: Bollinger inside Keltner breakout detection (60-75% WR)
try:
    from ttm_squeeze import TTM_SQUEEZE_STRATEGIES
except ImportError:
    TTM_SQUEEZE_STRATEGIES = {}

# Binance Futures Sentiment: long/short ratio, taker volume, OI signals (free Binance API)
try:
    from binance_sentiment import SENTIMENT_STRATEGIES
except ImportError:
    SENTIMENT_STRATEGIES = {}

# Survivor Strategies: backtested survivors wired into live scanner
# connors_r3 (71% WR), keltner_mean_reversion (67.3% WR), bollinger_mean_reversion (60.6% WR),
# volatility_scaled (65.8% WR), williams_r_oversold (58.8% WR)
try:
    from survivor_strategies import SURVIVOR_STRATEGIES
except ImportError:
    SURVIVOR_STRATEGIES = {}

# CryptoPanic News Sentiment + Fear & Greed Index (100 req/month, 8h cache)
try:
    from cryptopanic_feargreed import CRYPTOPANIC_STRATEGIES
except ImportError:
    CRYPTOPANIC_STRATEGIES = {}

# Sentiment-Price Divergence: detect sentiment/price trend divergences (reversal signals)
try:
    from sentiment_divergence import DIVERGENCE_STRATEGIES
except ImportError:
    DIVERGENCE_STRATEGIES = {}

# Technical Divergence: RSI/MFI/TSI divergence + market structure + trailing entry (r/algotrading)
try:
    from divergence_strategy import TECHNICAL_DIVERGENCE_STRATEGIES
except ImportError:
    TECHNICAL_DIVERGENCE_STRATEGIES = {}

# GARCH(1,1) Volatility: vol breakout + vol mean-reversion (Engle 1982, Bollerslev 1986)
try:
    from garch_volatility import GARCH_STRATEGIES
except ImportError:
    GARCH_STRATEGIES = {}

# Cointegration Pairs: statistical arbitrage on cointegrated crypto/forex pairs
try:
    from pairs_pick_generator import COINTEGRATION_STRATEGIES
except ImportError:
    try:
        from cointegration_pairs import COINTEGRATION_STRATEGIES
    except ImportError:
        COINTEGRATION_STRATEGIES = {}

# Candlestick Patterns: classic reversal/continuation patterns (hammer, engulfing, doji, etc.)
try:
    from candlestick_patterns import CANDLESTICK_STRATEGIES
except ImportError:
    CANDLESTICK_STRATEGIES = {}

# Hoffman Strategy: Rob Hoffman inventory retracement bar (ICE award-winning, trend following)
try:
    from hoffman_strategy import HOFFMAN_STRATEGIES
except ImportError:
    HOFFMAN_STRATEGIES = {}

# Session Breakout: London/NY/Asian session range breakout (intraday momentum)
try:
    from session_breakout import SESSION_STRATEGIES
except ImportError:
    SESSION_STRATEGIES = {}

# Range Breakout: consolidation range breakout with volume confirmation
try:
    from range_breakout import RANGE_BREAKOUT_STRATEGIES
except ImportError:
    RANGE_BREAKOUT_STRATEGIES = {}

# CNN-Lite Pattern Recognition: lightweight CNN for chart pattern detection (universal)
try:
    from pattern_cnn_lite import CNN_LITE_STRATEGIES
except ImportError:
    CNN_LITE_STRATEGIES = {}

# Cascade Contrarian: OI/MCap + funding rate cascade reversal (Binance futures, 60-68% WR)
try:
    from cascade_contrarian import CASCADE_CONTRARIAN_STRATEGIES
except ImportError:
    CASCADE_CONTRARIAN_STRATEGIES = {}

try:
    from hybrid_strategies import HYBRID_STRATEGIES
except ImportError:
    HYBRID_STRATEGIES = {}

# Google Antigravity (Gemini) baby_strategies wrapped for scanner
try:
    from antigravity_strategies import ANTIGRAVITY_STRATEGIES
except ImportError:

    ANTIGRAVITY_STRATEGIES = {}
try:
    from vt_baby_strategies import VT_BABY_STRATEGIES
except ImportError:
    VT_BABY_STRATEGIES = {}


# Token Unlock Event Short: Keyrock study 16K events, short before cliff unlocks (7-30d)
try:
    from unlock_event_strategy import TOKEN_UNLOCK_EVENT_STRATEGIES
except ImportError:
    TOKEN_UNLOCK_EVENT_STRATEGIES = {}

# Flow & Behavioral: stablecoin flow momentum + disposition effect contrarian
# Wei, Bianchi & Liao (2024 JFE) + Shams (2024 JF)
try:
    from flow_behavioral_strategies import FLOW_BEHAVIORAL_STRATEGIES
except ImportError:
    FLOW_BEHAVIORAL_STRATEGIES = {}

# Fundamental Valuation: BTC power law, NVM Metcalfe, ETH gas reversal
# Santostasi (2024), Ante et al. (2024), Cong, He & Tang (2023 Mgmt Science)
try:
    from fundamental_valuation_strategies import FUNDAMENTAL_VALUATION_STRATEGIES
except ImportError:
    FUNDAMENTAL_VALUATION_STRATEGIES = {}

# Institutional On-Chain: COT positioning proxy, OI breakout, miner capitulation recovery
# Bianchi & Babiak (2024), Aloosh et al. (2024), Nuzzi et al. (2024 CoinMetrics)
try:
    from institutional_onchain_strategies import INSTITUTIONAL_ONCHAIN_STRATEGIES
except ImportError:
    INSTITUTIONAL_ONCHAIN_STRATEGIES = {}

# Sideways Market Strategies: grid range scalper, squeeze range fade, intraday seasonality
# + Heikin Ashi trend filter (confidence adjuster applied post-collection)
try:
    from sideways_market_strategies import SIDEWAYS_MARKET_STRATEGIES, apply_ha_filter
except ImportError:
    SIDEWAYS_MARKET_STRATEGIES = {}
    apply_ha_filter = None

# Microstructure Momentum: VPIN spike continuation + cointegration half-life pairs
try:
    from microstructure_momentum import MICROSTRUCTURE_MOMENTUM_STRATEGIES
except ImportError:
    MICROSTRUCTURE_MOMENTUM_STRATEGIES = {}

# Novel Quick-Win Strategies: VRP signal, stablecoin flow on-chain, correlation breakout
try:
    from novel_strategies import NOVEL_STRATEGIES
except ImportError:
    NOVEL_STRATEGIES = {}

# Supplemental Data: Messari fundamentals, mempool.space BTC, Ethplorer ERC-20 whales
# Liu et al. (2022 JFE), Easley et al. (2019), Makarov & Schoar (2020)
try:
    from supplemental_data_strategies import SUPPLEMENTAL_DATA_STRATEGIES
except ImportError:
    SUPPLEMENTAL_DATA_STRATEGIES = {}

# Wave 4/5/6: Coinlore, Blockchain.info, Solana RPC, Gemini, Bybit, DefiLlama
# Bouri et al. (2021), Cong & He (2019), Makarov & Schoar (2020), Lyons (2023)
try:
    from wave456_strategies import WAVE456_STRATEGIES
except ImportError:
    WAVE456_STRATEGIES = {}

# On-Chain & Macro Tier 1: MVRV Z-Score, SOPR, NVT, SSR, DXY, Yield Curve
# Mahmudov & Puell (2018), Shirakashi (2019), Woo (2017), Estrella & Mishkin (1996)
try:
    from onchain_macro_strategies import generate_macro_picks, ONCHAIN_MACRO_STRATEGIES
except ImportError:
    generate_macro_picks = None
    ONCHAIN_MACRO_STRATEGIES = {}

# Super Alligator: Bill Williams Alligator (SMMA 13/8/5) + VWAP/SMA200 filters
# 4 variants: standard, scalp, swing, daily (Williams 1995)
try:
    from alligator_strategies import generate_alligator_picks, ALLIGATOR_STRATEGIES
except ImportError:
    generate_alligator_picks = None
    ALLIGATOR_STRATEGIES = {}

# Deribit Options-Derived Signals: risk reversal, max pain, put/call ratio
# Bollen & Whaley (2004), Goyal & Saretto (2009), Ederington & Guan (2002)
try:
    from options_signals import generate_options_picks, OPTIONS_STRATEGIES
except ImportError:
    generate_options_picks = None
    OPTIONS_STRATEGIES = {}

# Quant Research: Fisher Transform, Garman-Klass, TTM Squeeze, Hurst, KAMA,
# Vortex, Amihud, Vol Term Structure (8 strategies, stdlib only)
try:
    from quant_research_strategies import generate_quant_picks, QUANT_RESEARCH_STRATEGIES
except ImportError:
    generate_quant_picks = None
    QUANT_RESEARCH_STRATEGIES = {}

# CTA Bridge: 6 academic CTA strategies (TSMOM, Donchian, Golden Cross, FX Multi, Commodity Mom, X-Asset)
try:
    from cta_bridge import CTA_BRIDGE_STRATEGIES
except ImportError:
    CTA_BRIDGE_STRATEGIES = {}

# Quant Algorithms: Kalman, Bayesian, GARCH, Cointegration Pairs, Gaussian Mean-Revert,
# Adaptive Bollinger, Z-Score Momentum, Polynomial Regression Reversal (8 strategies, stdlib only)
try:
    from quant_algorithms import generate_quant_algorithm_picks, QUANT_ALGORITHM_STRATEGIES
except ImportError:
    generate_quant_algorithm_picks = None
    QUANT_ALGORITHM_STRATEGIES = {}

# Volume & Microstructure: OBV Trend, Volume Profile, MFI, Williams %R, Vol-MA Cross, LinReg Channels (6 strategies, stdlib only)
# NOTE: VOLUME_MICRO_STRATEGIES is metadata (dicts), NOT callables.
# Picks are generated via generate_volume_micro_picks() -- do NOT merge into strategies dict.
try:
    from volume_microstructure_strategies import generate_volume_micro_picks, VOLUME_MICRO_STRATEGIES
except ImportError:
    generate_volume_micro_picks = None
    VOLUME_MICRO_STRATEGIES = {}

# Advanced Quant: Beta-Neutral Arbitrage, Volatility Arbitrage, Correlation Breakdown, KDE Bands, Poisson Event (5 strategies)
try:
    from advanced_quant_strategies import ADVANCED_QUANT_STRATEGIES
except ImportError:
    ADVANCED_QUANT_STRATEGIES = {}


# Advanced Statistical: Fractal Dimension, DFA Timer, PCA Factor Rotation (3 strategies)
try:
    from advanced_statistical_strategies import ADVANCED_STATISTICAL_STRATEGIES
except ImportError:
    ADVANCED_STATISTICAL_STRATEGIES = {}

# High-Accuracy Phase 1: KAMA Adaptive, RSI-MACD-Vol Confluence, Kalman Filter Trend (65-72% WR)
try:
    from high_accuracy_strategies import HIGH_ACCURACY_STRATEGIES
except ImportError:
    HIGH_ACCURACY_STRATEGIES = {}

# Wavelet Transform + Cycle Detection: Haar wavelet multi-scale trend, DFT periodogram timing (2 strategies)
try:
    from wavelet_cycle_strategies import WAVELET_CYCLE_STRATEGIES
except ImportError:
    WAVELET_CYCLE_STRATEGIES = {}

# Incubator Strategies: 5 battle-tested Pine Script conversions (Triple Supertrend, ADX Momentum, TTM Squeeze, Dual Thrust ORB, ICT FVG)
try:
    from incubator_strategies import INCUBATOR_STRATEGIES
except ImportError:
    INCUBATOR_STRATEGIES = {}

# Crypto Enhancement Pack: 5 combo strategies (funding+sentiment, whale+regime, options+momentum, MTF confluence, liquidation reversal)
try:
    from crypto_enhancement_pack import generate_enhancement_picks, CRYPTO_ENHANCEMENT_STRATEGIES
except Exception:
    generate_enhancement_picks = None
    CRYPTO_ENHANCEMENT_STRATEGIES = {}

# Gainer Capture: 3 strategies to catch 20-100%+ pumps early
# Early Momentum Rider, Breakout Continuation, Momentum Portfolio
try:
    from gainer_capture_strategy import generate_gainer_picks, GAINER_CAPTURE_STRATEGIES
except ImportError:
    generate_gainer_picks = None
    GAINER_CAPTURE_STRATEGIES = {}

# Sustained Gainer: 5-condition confluence (20d high + volume + MA cross + RSI + MACD)
# Jegadeesh & Titman (1993), trailing stop portfolio, 48h time stop
try:
    from sustained_gainer_algorithm import generate_sustained_gainer_picks, SUSTAINED_GAINER_STRATEGIES
except ImportError:
    generate_sustained_gainer_picks = None
    SUSTAINED_GAINER_STRATEGIES = {}

# Multi-Signal Confluence: 4-layer confirmation (mean reversion + volume + EMA + MACD)
# 3 A/B variants: 3of4, 4of4, weighted (Elder 2002, Kaufman 1998)
try:
    from multi_signal_confluence import CONFLUENCE_STRATEGIES
except ImportError:
    CONFLUENCE_STRATEGIES = {}

# Quant Stack: KAMA + ATR Trailing Stop + Regime Switch (Mercury 2 blueprint)
try:
    from quant_stack_strategy import QUANT_STACK_STRATEGIES
except ImportError:
    QUANT_STACK_STRATEGIES = {}

# Trend Catcher: adaptive SuperTrend pullback, EMA stack, Donchian rider, Keltner squeeze (4H)
# Inspired by r/algotrading open-source trend tools — multi-TF adaptive trend detection
try:
    from trend_catcher import TREND_CATCHER_STRATEGIES
except ImportError:
    TREND_CATCHER_STRATEGIES = {}

# Inverse Edge System: exploit structural losers (WR<40%, PF<0.90, split-half validated)
# by flipping their signals. From r/algotrading: sustained anti-edge = real inverse edge.
try:
    from inverse_edge_system import INVERSE_EDGE_STRATEGIES
except ImportError:
    INVERSE_EDGE_STRATEGIES = {}

# EMA Retracement Mean Reversion: dynamic S/R bounce at EMA(21/50), stack alignment
# r/algotrading concept: calm pullback to EMA = tight SL, favorable R:R (60.3% WR verified)
try:
    from ema_retracement_strategy import EMA_RETRACEMENT_STRATEGIES
except ImportError:
    EMA_RETRACEMENT_STRATEGIES = {}

# World-Class v2.1: Truly Strong suite (DET + Sector Relative + Night Alpha)
try:
    from world_class_strategies_v21 import WORLD_CLASS_V21_STRATEGIES
except ImportError:
    WORLD_CLASS_V21_STRATEGIES = {}

# Proven Edge: night_session_scalper, fear_greed_short_contrarian, high_trust_momentum,
#              vwma_momentum_trend, supertrend_optimized, macd_divergence_scanner
try:
    from proven_edge_strategies import PROVEN_EDGE_STRATEGIES
except ImportError:
    PROVEN_EDGE_STRATEGIES = {}

# Crypto Edge: funding_rate_extreme, oi_price_divergence_v2, liquidation_flush_recovery
try:
    from crypto_edge_strategies import CRYPTO_EDGE_STRATEGIES
except ImportError:
    CRYPTO_EDGE_STRATEGIES = {}

# Confluence Strategies: fear_keltner, rsi_volume_regime, whale_momentum, multi_source, night_fear_short
try:
    from confluence_strategies import CONFLUENCE_STRATEGIES as CONFLUENCE_V2_STRATEGIES
except ImportError:
    CONFLUENCE_V2_STRATEGIES = {}

# Crypto ML Tuner: optimized XGBoost params, cross-asset correlation, retrain triggers
try:
    from crypto_ml_tuner import should_force_retrain as _should_force_retrain
    _HAS_CRYPTO_ML_TUNER = True
except ImportError:
    _should_force_retrain = None
    _HAS_CRYPTO_ML_TUNER = False

# Crypto Risk Gates: funding rate, regime, concentration, staleness, portfolio heat
try:
    from crypto_risk_gates import (
        apply_crypto_gates as _apply_crypto_gates,
        LOW_CONFIDENCE_STRATEGIES as _LOW_CONFIDENCE_STRATEGIES,
        compute_portfolio_heat as _compute_portfolio_heat,
        is_portfolio_overheated as _is_portfolio_overheated,
    )
    _HAS_CRYPTO_RISK_GATES = True
except ImportError:
    _apply_crypto_gates = None
    _LOW_CONFIDENCE_STRATEGIES = {}
    _compute_portfolio_heat = None
    _is_portfolio_overheated = None
    _HAS_CRYPTO_RISK_GATES = False

# Prediction Market Whale Tracker: Polymarket momentum, whale follow, Kalshi intraday,
# smart money divergence, cross-market consensus (6 strategies)
try:
    from prediction_market_whales import generate_prediction_market_picks, PREDICTION_MARKET_WHALE_STRATEGIES
except ImportError:
    generate_prediction_market_picks = None
    PREDICTION_MARKET_WHALE_STRATEGIES = {}

# Volatility Mean Reversion: Cycle 13 breakthrough — enter on vol spike, exit on reversion.
# 30/30 symbols profitable across ALL asset classes (PF 2-5).
try:
    from volatility_mean_reversion import VOL_MR_STRATEGIES
except ImportError:
    try:
        from alpha_engine.volatility_mean_reversion import VOL_MR_STRATEGIES
    except ImportError:
        VOL_MR_STRATEGIES = {}

# Cycle 16 strategies: MACD divergence, momentum breakout, mean reversion ATR, trend ensemble
try:
    from cycle16_strategies import CYCLE16_STRATEGIES
except ImportError:
    try:
        from alpha_engine.cycle16_strategies import CYCLE16_STRATEGIES
    except ImportError:
        CYCLE16_STRATEGIES = {}

# Cycle 17 strategies: stoch_rsi, pivot_reversion, ichimoku, yield_curve_proxy, range_trading
try:
    from cycle17_strategies import CYCLE17_STRATEGIES
except ImportError:
    try:
        from alpha_engine.cycle17_strategies import CYCLE17_STRATEGIES
    except ImportError:
        CYCLE17_STRATEGIES = {}

# ---------------------------------------------------------------------------
# GENERATOR-LEVEL HARD KILL -- strategies that must NEVER generate signals.
# This is the absolute last line of defense. Checked in run_strategies() loop
# AND in post-generation signal filtering. No bypass possible.
# ---------------------------------------------------------------------------
GENERATOR_HARD_KILL: set = {
    "binance_smart_money",      # 45.8% WR, 44% copy volume picking illiquid alts, -0.21% PnL
    "winner_pattern_precursor", # 17.7% WR on 96 trades, -91.9% PnL (added 2026-03-26)
    "quan_engine_scalp",          # 0% WR, -794% total PnL zombie — killed 2026-04-22
}

VERSION = "2.0"
STRATEGY_COUNT = len(CRYPTO_STRATEGIES) + len(FOREX_STRATEGIES) + len(EQUITY_STRATEGIES) + len(FAST_VARIANT_STRATEGIES) + len(ADVANCED_STRATEGIES) + len(KELTNER_EVOLVED_STRATEGIES) + len(SUPER_STRATEGIES) + len(VPIN_STRATEGIES) + len(LUNARCRUSH_STRATEGIES) + len(QUANT_STRATEGIES) + len(UNTAPPED_STRATEGIES) + len(TVL_MOMENTUM_STRATEGIES) + len(TTM_SQUEEZE_STRATEGIES) + len(SENTIMENT_STRATEGIES) + len(SURVIVOR_STRATEGIES) + len(CRYPTOPANIC_STRATEGIES) + len(DIVERGENCE_STRATEGIES) + len(GARCH_STRATEGIES) + len(COINTEGRATION_STRATEGIES) + len(CANDLESTICK_STRATEGIES) + len(HOFFMAN_STRATEGIES) + len(SESSION_STRATEGIES) + len(RANGE_BREAKOUT_STRATEGIES) + len(CNN_LITE_STRATEGIES) + len(CASCADE_CONTRARIAN_STRATEGIES) + len(HYBRID_STRATEGIES) + len(ANTIGRAVITY_STRATEGIES) + len(VT_BABY_STRATEGIES) + len(TOKEN_UNLOCK_EVENT_STRATEGIES) + len(FLOW_BEHAVIORAL_STRATEGIES) + len(FUNDAMENTAL_VALUATION_STRATEGIES) + len(INSTITUTIONAL_ONCHAIN_STRATEGIES) + len(SIDEWAYS_MARKET_STRATEGIES) + len(MICROSTRUCTURE_MOMENTUM_STRATEGIES) + len(NOVEL_STRATEGIES) + len(SUPPLEMENTAL_DATA_STRATEGIES) + len(WAVE456_STRATEGIES) + len(ONCHAIN_MACRO_STRATEGIES) + len(ALLIGATOR_STRATEGIES) + len(OPTIONS_STRATEGIES) + len(QUANT_RESEARCH_STRATEGIES) + len(CTA_BRIDGE_STRATEGIES) + len(QUANT_ALGORITHM_STRATEGIES) + len(HIGH_ACCURACY_STRATEGIES) + len(VOLUME_MICRO_STRATEGIES) + len(ADVANCED_QUANT_STRATEGIES) + len(CRYPTO_ENHANCEMENT_STRATEGIES) + len(GAINER_CAPTURE_STRATEGIES) + len(SUSTAINED_GAINER_STRATEGIES) + len(CONFLUENCE_STRATEGIES) + len(ADVANCED_STATISTICAL_STRATEGIES) + len(INCUBATOR_STRATEGIES) + len(QUANT_STACK_STRATEGIES) + len(EMA_RETRACEMENT_STRATEGIES) + len(PREDICTION_MARKET_WHALE_STRATEGIES) + len(COMMODITY_STRATEGIES) + len(FUTURES_STRATEGIES) + len(ETF_STRATEGIES) + len(BOND_STRATEGIES) + len(VOL_MR_STRATEGIES) + len(CYCLE16_STRATEGIES) + len(CYCLE17_STRATEGIES)


# ---------------------------------------------------------------------------
# Forward-Test Gate -- Action 1.3 Remediation
# Lowered from 30 to 15 for faster initial validation cycle.
# Strategies can become "validated" sooner, accelerating the feedback loop.
# ML training threshold remains at 50 (needs more data for reliable model).
# ---------------------------------------------------------------------------
FORWARD_GATE_MIN_TRADES = 10    # Lowered from 15 -- faster feedback loop
FORWARD_GATE_MIN_WR = 0.50
EARLY_SUPPRESS_TRADES = 4       # If 0% WR after 4 trades, suppress early
EARLY_SUPPRESS_MAX_WR = 0.10    # Below 10% WR with 4+ trades = suppress


def passes_forward_gate(strategy_name: str, strategy_stats: dict,
                        min_trades: int = FORWARD_GATE_MIN_TRADES,
                        min_wr: float = FORWARD_GATE_MIN_WR
                        ) -> tuple[bool, str, int, float]:
    """
    Check if a strategy has enough forward-test data to be published
    as a validated signal. New strategies are NOT blocked -- they
    accumulate data in 'unvalidated' mode.

    Early suppression: strategies with 0-10% WR after 4+ trades are
    immediately suppressed (don't wait for 10 trades to confirm they're bad).

    Returns: (passes, reason, trade_count, win_rate)
    """
    wins = int(strategy_stats.get("wins", strategy_stats.get("won", 0)))
    losses = int(strategy_stats.get("losses", strategy_stats.get("lost", 0)))
    total = int(strategy_stats.get("closed_picks", wins + losses))
    # Use standardized win rate calculation (excludes zero-PnL)
    wr = strategy_stats.get("win_rate", calculate_win_rate(wins, total))

    # Early suppression: 0-10% WR with 4+ trades = proven loser, don't wait
    if total >= EARLY_SUPPRESS_TRADES and wr <= EARLY_SUPPRESS_MAX_WR:
        return (False, f"early_suppress ({wr:.0%} WR on {total} trades)", total, float(wr))

    if total < min_trades:
        return (False, f"insufficient_data ({total}/{min_trades} trades)", total, float(wr))
    if wr < min_wr:
        return (False, f"low_wr ({wr:.1%} < {min_wr:.0%})", total, float(wr))
    return (True, "validated", total, float(wr))


# ---------------------------------------------------------------------------
# Market Regime Detection (Action 3.1)
# ---------------------------------------------------------------------------

def detect_market_regime(df: pd.DataFrame, adx_period: int = 14,
                         adx_trending: float = 25.0,
                         adx_ranging: float = 20.0) -> dict:
    """
    Detect market regime using ADX + volatility.

    Returns dict with:
      - regime: 'trending' | 'ranging' | 'transitional' | 'unknown'
      - adx: current ADX value (float or None)
      - volatility: 20-day rolling std of returns (float or None)
      - plus_di: +DI value
      - minus_di: -DI value
      - trend_direction: 'bullish' | 'bearish' | None (based on +DI vs -DI)

    Reference: Wilder (1978). ADX > 25 = trending, < 20 = ranging.
    """
    if df is None or len(df) < adx_period * 2:
        return {"regime": "unknown", "adx": None, "volatility": None,
                "plus_di": None, "minus_di": None, "trend_direction": None}

    # Resolve column names (handle both 'High' and 'high')
    high = df["High"] if "High" in df.columns else df.get("high")
    low = df["Low"] if "Low" in df.columns else df.get("low")
    close = df["Close"] if "Close" in df.columns else df.get("close")

    if high is None or low is None or close is None:
        return {"regime": "unknown", "adx": None, "volatility": None,
                "plus_di": None, "minus_di": None, "trend_direction": None}

    try:
        # Calculate +DM / -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

        # True Range
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ], axis=1).max(axis=1)
        atr_val = tr.rolling(adx_period).mean()

        # +DI / -DI
        plus_di = 100.0 * (plus_dm.rolling(adx_period).mean() / (atr_val + 1e-10))
        minus_di = 100.0 * (minus_dm.rolling(adx_period).mean() / (atr_val + 1e-10))

        # DX -> ADX
        dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10)
        adx_series = dx.rolling(adx_period).mean()

        current_adx = float(adx_series.iloc[-1]) if not pd.isna(adx_series.iloc[-1]) else None
        current_plus_di = float(plus_di.iloc[-1]) if not pd.isna(plus_di.iloc[-1]) else None
        current_minus_di = float(minus_di.iloc[-1]) if not pd.isna(minus_di.iloc[-1]) else None

        # Volatility: 20-day rolling std of returns
        returns = close.pct_change()
        vol = float(returns.rolling(20).std().iloc[-1]) if len(returns) >= 20 else None
        if vol is not None and pd.isna(vol):
            vol = None

        # Regime classification
        if current_adx is None:
            regime = "unknown"
        elif current_adx >= adx_trending:
            regime = "trending"
        elif current_adx <= adx_ranging:
            regime = "ranging"
        else:
            regime = "transitional"

        # Trend direction from DI
        trend_direction = None
        if current_plus_di is not None and current_minus_di is not None:
            if current_plus_di > current_minus_di:
                trend_direction = "bullish"
            elif current_minus_di > current_plus_di:
                trend_direction = "bearish"

        return {
            "regime": regime,
            "adx": round(current_adx, 2) if current_adx is not None else None,
            "volatility": round(vol, 6) if vol is not None else None,
            "plus_di": round(current_plus_di, 2) if current_plus_di is not None else None,
            "minus_di": round(current_minus_di, 2) if current_minus_di is not None else None,
            "trend_direction": trend_direction,
        }

    except Exception:
        return {"regime": "unknown", "adx": None, "volatility": None,
                "plus_di": None, "minus_di": None, "trend_direction": None}


# ---------------------------------------------------------------------------
# Strategy-Regime Mapping (Action 3.1)
# ---------------------------------------------------------------------------
# Maps each strategy to the regime(s) where it performs best.
# Strategies NOT in this map default to universal (all regimes).
#
# Categories:
#   trending     - Momentum / breakout / trend-following
#   ranging      - Mean-reversion / oscillator-based
#   transitional - Works in regime transitions
#   universal    - Regime-independent (event-driven, on-chain, funding, etc.)
# ---------------------------------------------------------------------------

STRATEGY_REGIME_MAP: dict[str, list[str]] = {
    # =====================================================================
    # CRYPTO STRATEGIES (core 33 + community 6 + spike 6)
    # =====================================================================

    # --- Momentum / Trend-following (best in trending) ---
    "btc_ichimoku_cloud":           ["trending"],
    "crypto_breakout_volume":       ["trending"],
    "altcoin_season_rotation":      ["trending"],
    "break_of_structure":           ["trending"],
    "multi_timeframe_ema_stack":    ["trending"],
    "cross_sectional_momentum":     ["trending"],
    "atr_volatility_breakout":      ["trending"],
    "obv_divergence_breakout":      ["trending"],

    # --- Mean-Reversion (best in ranging) ---
    "btc_200d_sma_bounce":          ["ranging", "transitional"],
    "connors_rsi2_crypto":          ["ranging"],
    "rsi_hidden_divergence":        ["ranging"],
    "stochrsi_oversold_bounce":     ["ranging"],
    "hurst_mean_reversion":         ["ranging"],
    "vwap_sd_mean_reversion":       ["ranging"],
    "rsi_macd_confluence":          ["ranging", "transitional"],
    "volume_climax_reversal":       ["ranging"],
    "cmf_zero_line_cross":          ["ranging", "transitional"],

    # --- DNA Mutations (relaxed variants) ---
    "dna_hurst_relaxed":            ["ranging"],
    "dna_ema_stack_relaxed":        ["trending"],
    "dna_fractal_bounce_relaxed":   ["ranging", "transitional"],

    # --- Volatility / Squeeze (transitional -- await breakout) ---
    "entropy_adaptive_rsi":         ["ranging", "transitional"],

    # --- Event / Sentiment / Universal ---
    "crypto_fear_greed_contrarian":  ["trending", "ranging", "transitional"],
    "funding_rate_extreme":          ["trending", "ranging", "transitional"],
    "wyckoff_accumulation":          ["ranging", "transitional"],
    "smart_money_fvg":               ["trending", "ranging", "transitional"],
    "coingecko_trending_volume":     ["trending", "ranging", "transitional"],
    "ape_wisdom_social_momentum":    ["trending", "ranging", "transitional"],
    "btc_dominance_reversal":        ["trending", "ranging", "transitional"],
    "crypto_weekend_drift":          ["trending", "ranging", "transitional"],
    "mfi_smart_money_detection":     ["trending", "ranging", "transitional"],
    "liquidity_sweep_reversal":      ["ranging", "transitional"],

    # --- Wave 2: Millionaire Trader / Quant / SMC ---
    "swing_failure_pattern":         ["ranging", "transitional"],
    "funding_rate_carry":            ["trending", "ranging", "transitional"],
    "oi_funding_squeeze":            ["transitional"],
    "liquidation_cascade_bottom":    ["trending", "ranging", "transitional"],
    "whale_accumulation_detector":   ["trending", "ranging", "transitional"],
    "cascade_contrarian":            ["trending", "ranging", "transitional"],  # all regimes, strongest in high-vol

    # --- Community strategies ---
    "community_ema_9_21_rsi_crypto":          ["trending"],
    "community_bb_squeeze_breakout_crypto":   ["transitional", "trending"],
    "community_rsi_extreme_reversal_crypto":  ["ranging"],
    "community_vwap_bounce_crypto":           ["ranging"],
    "community_momentum_breakout_volume_crypto": ["trending"],
    "community_ict_fvg_selective":            ["trending", "ranging", "transitional"],

    # --- Spike strategies ---
    "spike_momentum_ignition":  ["trending"],
    "spike_squeeze_breakout":   ["transitional", "trending"],
    "spike_rsi_extreme":        ["ranging"],
    "spike_volume_explosion":   ["trending"],
    "spike_macd_divergence":    ["ranging", "transitional"],
    "spike_zscore_extreme":     ["ranging"],

    # --- Fast Variants (relaxed proven strategies) ---
    "fast_rsi2_relaxed":        ["ranging"],
    "fast_rsi2_extended":       ["ranging"],
    "fast_vix_moderate":        ["trending", "ranging", "transitional"],
    "fast_funding_wide":        ["trending", "ranging", "transitional"],
    "fast_rsi2_aggressive":     ["ranging", "transitional"],
    "fast_triple_confirm":      ["ranging"],
    "fast_rsi2_short":          ["ranging", "transitional"],

    # =====================================================================
    # ON-CHAIN STRATEGIES (10)
    # =====================================================================
    "mvrv_sma_proxy":           ["trending", "ranging", "transitional"],
    "hash_ribbon_buy":          ["trending", "ranging", "transitional"],
    "stablecoin_buying_power":  ["trending", "ranging", "transitional"],
    "nvt_overvaluation":        ["trending", "ranging", "transitional"],
    "fear_greed_extreme_dca":   ["trending", "ranging", "transitional"],
    "sopr_dip_buy_proxy":       ["ranging", "transitional"],
    "onchain_composite_score":  ["trending", "ranging", "transitional"],
    "hayes_liquidity_index":    ["trending", "ranging", "transitional"],
    "pentoshi_htf_structure":   ["trending"],
    "funding_rate_arbitrage":   ["trending", "ranging", "transitional"],
    "cross_exchange_basis_carry": ["trending", "ranging", "transitional"],

    # =====================================================================
    # VPIN + LUNARCRUSH (Phase 4 -- 2026-03-15)
    # =====================================================================
    "vpin_informed_flow":        ["trending", "ranging", "transitional"],
    "galaxy_score_momentum":     ["trending", "ranging", "transitional"],
    "sentiment_price_divergence": ["trending", "ranging", "transitional"],

    # =====================================================================
    # QUANT STRATEGIES (4)
    # =====================================================================
    "tsmom_28d":                ["trending"],
    "cointegrated_pairs":       ["ranging"],
    "momentum_mean_rev_blend":  ["trending", "ranging", "transitional"],
    "oi_price_divergence":      ["transitional"],

    # =====================================================================
    # EVENT-DRIVEN STRATEGIES (8)
    # =====================================================================
    "token_unlock_short":       ["trending", "ranging", "transitional"],
    "token_unlock_event_short": ["trending", "ranging", "transitional"],
    "token_unlock_pressure":    ["trending", "ranging", "transitional"],
    "token_unlock_bounce":      ["ranging", "transitional"],
    "liquidation_cascade_buy":  ["trending", "ranging", "transitional"],
    "exchange_netflow_reversal": ["trending", "ranging", "transitional"],
    "btc_dip_recovery":         ["ranging", "transitional"],
    "narrative_rotation":       ["trending"],
    "new_pair_momentum":        ["trending"],
    "cross_exchange_spread":    ["trending", "ranging", "transitional"],
    "momentum_crash_hedge":     ["trending"],

    # =====================================================================
    # ADVANCED STRATEGIES (8)
    # =====================================================================
    "vol_risk_premium":           ["trending", "ranging", "transitional"],
    "dynamic_momentum_scaling":   ["trending"],
    "goplus_filtered_sniper":     ["trending", "ranging", "transitional"],
    "altcoin_dip_amplifier":      ["ranging", "transitional"],
    "unlock_scoring_enhanced":    ["trending", "ranging", "transitional"],
    "cascade_volume_detector":    ["trending", "ranging", "transitional"],
    "dvol_extreme_buy":           ["ranging", "transitional"],
    "sector_momentum_7d":         ["trending"],

    # =====================================================================
    # FOREX STRATEGIES (12 + 3 community + COT)
    # =====================================================================
    "carry_trade_momentum":          ["trending"],
    "forex_mean_reversion_200d":     ["ranging"],
    "jpy_risk_off":                  ["trending", "ranging", "transitional"],
    "dxy_correlation_regime":        ["trending", "ranging", "transitional"],
    "forex_bollinger_squeeze":       ["transitional", "trending"],
    "session_momentum_continuation": ["trending"],
    "dxy_rsi_mean_reversion":        ["ranging"],
    "sunday_night_gap_trade":        ["ranging", "transitional"],
    "session_volatility_expansion":  ["transitional", "trending"],
    "forex_tsmom_12m":               ["trending"],
    "forex_logistic_direction":      ["trending", "ranging", "transitional"],
    "forex_rsi2_mean_reversion":     ["ranging", "transitional"],
    "cot_positioning":               ["trending", "ranging", "transitional"],
    "community_ema_8_21_scalp_forex":       ["trending"],
    "community_london_breakout_v2_forex":   ["trending"],
    "community_forex_zscore_mean_reversion": ["ranging"],

    # =====================================================================
    # EQUITY STRATEGIES (12 + 2 community)
    # =====================================================================
    "momentum_factor_12m":           ["trending"],
    "penny_volume_breakout":         ["trending"],
    "meme_social_velocity":          ["trending", "ranging", "transitional"],
    "quality_value_composite":       ["trending", "ranging", "transitional"],
    "intermarket_risk_on":           ["trending"],
    "support_resistance_bounce":     ["ranging"],
    "connors_rsi2_scanner":          ["ranging"],
    "triple_rsi_scanner":            ["ranging"],
    "vix_spike_reversal_scanner":    ["trending", "ranging", "transitional"],
    "turn_of_month_scanner":         ["trending", "ranging", "transitional"],
    "earnings_gap_reversal_scanner": ["ranging", "transitional"],
    "gap_reversal_tech_stocks":      ["ranging", "transitional"],
    "community_orb_equity":          ["trending"],
    "community_penny_volume_surge":  ["trending"],

    # =====================================================================
    # MERCURY AI STRATEGIES -- Wave 12 (5)
    # =====================================================================
    "hurst_regime_momentum":    ["trending", "ranging"],  # self-selecting by regime
    "lw_vwap_mean_reversion":   ["ranging", "transitional"],
    "funding_term_structure":   ["trending", "ranging", "transitional"],
    "spot_perp_basis_arb":      ["trending", "ranging", "transitional"],
    "iv_skew_reversion":        ["ranging", "transitional"],

    # =====================================================================
    # NEXTGEN STRATEGIES -- Wave 13 (12)
    # =====================================================================
    "cointegration_pair_trade":      ["ranging"],  # mean-reversion on spread
    "adx_volatility_breakout":       ["trending"],  # ADX-confirmed breakout
    "seasonal_factor_rotation":      ["trending", "ranging", "transitional"],  # calendar effect
    "multi_factor_equity_rotation":  ["trending", "ranging", "transitional"],  # monthly rebalance
    "dead_cat_bounce_momentum":      ["ranging", "transitional"],  # extreme fear reversal
    "market_structure_break":        ["trending"],  # round-number level break
    "volume_acceleration_reversion": ["ranging", "transitional"],  # absorption reversal
    "night_liquidity_drift":         ["trending", "ranging", "transitional"],  # off-peak breakout
    "spread_of_candles_gap":         ["ranging", "transitional"],  # gap fill trade
    "vix_correlation_divergence":    ["ranging", "transitional"],  # VIX fear decoupling
    "profit_taking_reentry":         ["trending"],  # momentum continuation
    "bb_rsi_mean_reversion":         ["ranging"],  # BB touch + RSI extreme
    "pi_cycle_regime_gate":          ["trending", "ranging", "transitional"],  # macro gate
    "puell_multiple_extreme":        ["trending", "ranging", "transitional"],  # macro on-chain

    # =====================================================================
    # SURVIVOR STRATEGIES (3) -- backtested survivors, mean-reversion
    # =====================================================================
    "connors_r3_survivor":                  ["ranging"],  # RSI-2 mean reversion, best in ranging
    "keltner_mean_reversion_survivor":      ["ranging", "transitional"],  # Keltner channel MR
    "bollinger_mean_reversion_survivor":    ["ranging", "transitional"],  # BB lower band MR

    # =====================================================================
    # CRYPTOPANIC + FEAR & GREED (cryptopanic_feargreed.py)
    # =====================================================================
    "cryptopanic_news_sentiment":           ["trending", "ranging", "transitional"],  # contrarian sentiment

    # =====================================================================
    # COINTEGRATION PAIRS (cointegration_pairs.py) -- mean reversion
    # =====================================================================
    # Mean-reversion on spread: works in all regimes (pairs are market-neutral)
    "cointegration_pair_zscore":         ["trending", "ranging", "transitional"],
    "cointegration_half_life_trade":     ["trending", "ranging", "transitional"],

    # =====================================================================
    # CANDLESTICK PATTERNS (candlestick_patterns.py) -- reversal patterns
    # =====================================================================
    "hammer_reversal":                   ["ranging", "transitional"],
    "engulfing_reversal":                ["ranging", "transitional"],
    "doji_reversal":                     ["ranging"],
    "morning_evening_star":              ["ranging", "transitional"],
    "three_white_soldiers_black_crows":  ["trending"],

    # =====================================================================
    # HOFFMAN STRATEGY (hoffman_strategy.py) -- trend following
    # =====================================================================
    "hoffman_inventory_retracement":     ["trending"],
    "hoffman_continuation":              ["trending"],

    # =====================================================================
    # SESSION BREAKOUT (session_breakout.py) -- momentum/breakout
    # =====================================================================
    "london_session_breakout":           ["trending", "transitional"],
    "ny_session_breakout":               ["trending", "transitional"],
    "asian_session_breakout":            ["ranging", "transitional"],

    # =====================================================================
    # RANGE BREAKOUT (range_breakout.py) -- momentum/breakout
    # =====================================================================
    "consolidation_range_breakout":      ["trending", "transitional"],
    "volatility_contraction_breakout":   ["transitional", "trending"],
    "opening_range_breakout":            ["trending"],

    # =====================================================================
    # CNN-LITE PATTERN RECOGNITION (pattern_cnn_lite.py) -- universal
    # =====================================================================
    "cnn_lite_pattern_signal":           ["trending", "ranging", "transitional"],

    # =====================================================================
    # SWEEP BREAKOUT SCALER (sweep_breakout_scaler.py) -- breakout/momentum
    # =====================================================================
    "sweep_breakout_scaler":             ["trending", "transitional"],

    # =====================================================================
    # CROSS-SECTIONAL REVERSAL (reversal_strategies.py) -- mean reversion
    # =====================================================================
    "cross_sectional_reversal":          ["ranging", "mean_reverting"],

    # =====================================================================
    # SYMBOL-SPECIFIC VARIANTS (symbol_specific_variants.py)
    # =====================================================================
    "cross_sectional_reversal_sol":      ["ranging", "mean_reverting"],
    "cross_sectional_reversal_eth":      ["ranging", "mean_reverting"],
    "residual_momentum_midcap":          ["trending", "transitional"],
    "oi_momentum_btc":                   ["trending", "transitional"],
    "oi_momentum_eth":                   ["trending", "transitional"],
    "crowd_contrarian_doge":             ["ranging", "mean_reverting"],
    "crowd_contrarian_xrp":              ["ranging", "mean_reverting"],
    "btc_macro_composite":               ["trending", "ranging", "transitional"],

    # =====================================================================
    # SIDEWAYS MARKET STRATEGIES (3 + HA filter)
    # =====================================================================
    "grid_range_scalper":                ["ranging", "mean_reverting"],
    "squeeze_range_fade":                ["ranging", "mean_reverting"],
    "intraday_seasonality":              ["trending", "ranging", "transitional"],

    # =====================================================================
    # CTA BRIDGE STRATEGIES (6) -- academic CTA replication
    # =====================================================================
    "cta_tsmom_blend":                   ["trending"],
    "cta_donchian_55":                   ["trending"],
    "cta_golden_cross":                  ["trending"],
    "cta_fx_multifactor":                ["trending", "ranging", "transitional"],
    "cta_commodity_momentum":            ["trending"],
    "cta_cross_asset_tsmom":             ["trending", "ranging", "transitional"],

    # =====================================================================
    # HIGH-ACCURACY PHASE 1 (3 strategies, 65-72% WR)
    # =====================================================================
    "kama_volatility_adaptive":          ["trending", "transitional"],
    "rsi_macd_vol_confluence":           ["ranging", "transitional"],
    "kalman_filter_trend":               ["trending"],

    # =====================================================================
    # VOLATILITY MEAN REVERSION (Cycle 13 -- universal, all regimes)
    # =====================================================================
    "volatility_mean_reversion":         ["trending", "ranging", "transitional"],
}

# Default for strategies not explicitly mapped: universal (all regimes)
_UNIVERSAL_REGIMES = ["trending", "ranging", "transitional"]


def get_strategy_allowed_regimes(strategy_name: str) -> list[str]:
    """Return list of regimes where a strategy is expected to perform well."""
    return STRATEGY_REGIME_MAP.get(strategy_name, _UNIVERSAL_REGIMES)


def compute_regime_cache(data: dict[str, pd.DataFrame],
                         context: dict | None = None) -> dict[str, dict]:
    """
    Pre-compute market regime for every symbol with data.
    Returns dict: symbol -> regime_info dict.
    Cached per scan to avoid recomputation.

    If HMM regime data is available in context, overlays HMM fields
    onto the ADX-based regime (hmm_regime, hmm_confidence, hmm_signal).
    """
    regimes = {}
    for symbol, df in data.items():
        regimes[symbol] = detect_market_regime(df)

    # Overlay HMM regime data if available
    hmm_data = (context or {}).get("hmm_regime", {})
    per_symbol_hmm = hmm_data.get("per_symbol", {})
    hmm_count = 0
    for symbol in regimes:
        if symbol in per_symbol_hmm:
            hmm = per_symbol_hmm[symbol]
            regimes[symbol]["hmm_regime"] = hmm.get("regime", "unknown")
            regimes[symbol]["hmm_alpha_regime"] = hmm.get("alpha_regime", "unknown")
            regimes[symbol]["hmm_confidence"] = hmm.get("confidence", 0)
            regimes[symbol]["hmm_signal"] = hmm.get("signal", "FLAT")
            regimes[symbol]["hmm_leverage"] = hmm.get("leverage", 1.0)
            hmm_count += 1
    if hmm_count > 0:
        print(f"  HMM overlay: {hmm_count}/{len(regimes)} symbols enriched")

    return regimes


def annotate_signal_with_regime(signal: dict, regime_cache: dict[str, dict]) -> dict:
    """
    Add regime metadata to a signal dict. Does NOT block signals --
    just adds informational fields for downstream filtering/reporting.

    Added fields:
      - market_regime: full regime dict for the symbol
      - regime_compatible: bool (True if strategy suits current regime)
      - regime_warning: str or None (warning if incompatible)
    """
    symbol = signal.get("symbol", "")
    strategy = signal.get("strategy", "")

    regime_info = regime_cache.get(symbol, {
        "regime": "unknown", "adx": None, "volatility": None,
        "plus_di": None, "minus_di": None, "trend_direction": None,
    })

    signal["market_regime"] = regime_info

    current_regime = regime_info.get("regime", "unknown")
    allowed_regimes = get_strategy_allowed_regimes(strategy)

    # Unknown regime is always considered compatible (no data to judge)
    if current_regime == "unknown":
        signal["regime_compatible"] = True
        signal["regime_warning"] = None
    elif current_regime in allowed_regimes:
        signal["regime_compatible"] = True
        signal["regime_warning"] = None
    else:
        signal["regime_compatible"] = False
        adx_val = regime_info.get("adx")
        adx_str = f", ADX={adx_val}" if adx_val is not None else ""
        signal["regime_warning"] = (
            f"Strategy '{strategy}' not optimal for {current_regime} market"
            f" (best in: {', '.join(allowed_regimes)}{adx_str})"
        )

    return signal


# ---------------------------------------------------------------------------
# Data Fetching (with retries)
# ---------------------------------------------------------------------------

def download_with_retries(tickers: str, period: str, interval: str,
                          is_batch: bool = True) -> pd.DataFrame | None:
    """Download data from yfinance with retries and exponential backoff."""
    MAX_RETRIES = 3
    BACKOFF = [5, 15, 45]

    for attempt in range(MAX_RETRIES):
        try:
            if is_batch:
                data = yf.download(
                    tickers,
                    period=period,
                    interval=interval,
                    group_by="ticker" if len(tickers.split()) > 1 else None,
                    auto_adjust=True,
                    threads=True,
                    progress=False,
                )
            else:
                data = yf.download(
                    tickers,
                    period=period,
                    interval=interval,
                    auto_adjust=True,
                    progress=False,
                )
            if data is not None and not data.empty:
                return data
            print(f"  [WARN] yfinance attempt {attempt+1}/{MAX_RETRIES} returned empty for {tickers}")
        except Exception as e:
            print(f"  [WARN] yfinance attempt {attempt+1}/{MAX_RETRIES} failed for {tickers}: {e}")
        if attempt < MAX_RETRIES - 1:
            time.sleep(BACKOFF[attempt])

    # Provider failover: yfinance exhausted all retries (Yahoo outage / CI IP
    # block). Tiingo -> Polygon -> AlphaVantage serve daily OHLCV from normal
    # cloud-reachable APIs. Failover is per-symbol + daily-only, so it only
    # applies to single-symbol daily calls; batch/intraday keep yfinance-only
    # behavior. Fail-open: any error here falls through to the original
    # `return None`. (CLAUDE.md API-Failover-Rule)
    _is_single = is_batch is False or len(tickers.split()) == 1
    if (_HAS_OHLCV_FAILOVER and _is_single
            and interval in ("1d", "1day", "1D", "d")):
        symbol = tickers.split()[0]
        try:
            if failover_available():
                df, provider = fetch_ohlcv_failover(symbol)
                if df is not None and not df.empty:
                    print(f"  [INFO] yfinance failed for {symbol} — "
                          f"recovered {len(df)} bars via {provider}")
                    return df
        except Exception as e:  # noqa: BLE001
            print(f"  [WARN] OHLCV failover error for {symbol}: {e}")

    return None


def fetch_market_data(symbols: list[str], period: str = YF_PERIOD_DAILY,
                      interval: str = YF_INTERVAL_DAILY) -> dict[str, pd.DataFrame]:
    """
    Fetch OHLCV data from yfinance for all symbols.
    Returns dict: symbol -> DataFrame with columns [Open, High, Low, Close, Volume].
    """
    data = {}
    all_tickers = " ".join(symbols)
    print(f"  Fetching {len(symbols)} symbols from yfinance ({period}/{interval})...")

    raw = download_with_retries(all_tickers, period, interval, is_batch=True)

    if raw is None or raw.empty:
        print("  [WARN] Batch download failed, trying individual symbols...")
        for symbol in symbols:
            df = download_with_retries(symbol, period, interval, is_batch=False)
            if df is not None and not df.empty:
                df = df.dropna(subset=["Close"])
                if len(df) >= 10:
                    data[symbol] = df
        print(f"  Got data for {len(data)}/{len(symbols)} symbols (individual fallback)")
        # Binance klines fallback for crypto symbols still missing
        _missing_crypto = [s for s in symbols if s not in data and ('USD' in s or 'USDT' in s)]
        if _missing_crypto:
            print(f"  Trying Binance klines for {len(_missing_crypto)} missing crypto symbols...")
            for _sym in _missing_crypto:
                try:
                    _bsym = _sym.upper().replace('-USD', 'USDT').replace('-', '')
                    if not _bsym.endswith('USDT') and 'USD' in _bsym:
                        _bsym = _bsym.replace('USD', 'USDT')
                    import urllib.request as _ur
                    _kdata = None
                    # Binance mirrors + CoinGecko/KuCoin/CryptoCompare failover (API rule)
                    for _kbase in [
                        "https://api.binance.com",
                        "https://api1.binance.com",
                        "https://api2.binance.com",
                        "https://api3.binance.com",
                        "https://data-api.binance.vision",
                    ]:
                        try:
                            _kurl = f"{_kbase}/api/v3/klines?symbol={_bsym}&interval=1d&limit=200"
                            _kreq = _ur.Request(_kurl, headers={"User-Agent": "Mozilla/5.0"})
                            _kdata = json.loads(_ur.urlopen(_kreq, timeout=10).read())
                            if _kdata:
                                break
                        except Exception:
                            continue
                    # CoinGecko fallback
                    if not _kdata:
                        try:
                            _cg_id = _bsym.replace("USDT", "").lower()
                            _cg_url = f"https://api.coingecko.com/api/v3/coins/{_cg_id}/ohlc?vs_currency=usd&days=200"
                            _cg_req = _ur.Request(_cg_url, headers={"User-Agent": "Mozilla/5.0"})
                            _cg_raw = json.loads(_ur.urlopen(_cg_req, timeout=10).read())
                            if _cg_raw and len(_cg_raw) >= 10:
                                _kdata = [[r[0], r[1], r[2], r[3], r[4], 0, 0, 0, 0, 0, 0, 0] for r in _cg_raw]
                        except Exception:
                            pass
                    # KuCoin fallback
                    if not _kdata:
                        try:
                            _kc_sym = _bsym.replace("USDT", "-USDT")
                            _kc_url = f"https://api.kucoin.com/api/v1/market/candles?type=1day&symbol={_kc_sym}"
                            _kc_req = _ur.Request(_kc_url, headers={"User-Agent": "Mozilla/5.0"})
                            _kc_raw = json.loads(_ur.urlopen(_kc_req, timeout=10).read())
                            _kc_candles = _kc_raw.get("data", []) if isinstance(_kc_raw, dict) else []
                            if _kc_candles and len(_kc_candles) >= 10:
                                _kdata = [[int(c[0])*1000, c[1], c[3], c[4], c[2], c[5], 0, 0, 0, 0, 0, 0] for c in _kc_candles]
                                _kdata.reverse()
                        except Exception:
                            pass
                    # CryptoCompare fallback
                    if not _kdata:
                        try:
                            _cc_fsym = _bsym.replace("USDT", "")
                            _cc_url = f"https://min-api.cryptocompare.com/data/v2/histoday?fsym={_cc_fsym}&tsym=USDT&limit=200"
                            _cc_req = _ur.Request(_cc_url, headers={"User-Agent": "Mozilla/5.0"})
                            _cc_raw = json.loads(_ur.urlopen(_cc_req, timeout=10).read())
                            _cc_data = _cc_raw.get("Data", {}).get("Data", []) if isinstance(_cc_raw, dict) else []
                            if _cc_data and len(_cc_data) >= 10:
                                _kdata = [[d["time"]*1000, d["open"], d["high"], d["low"], d["close"], d.get("volumeto", 0), 0, 0, 0, 0, 0, 0] for d in _cc_data]
                        except Exception:
                            pass
                    if _kdata and len(_kdata) >= 10:
                        import pandas as _pd
                        _kdf = _pd.DataFrame(_kdata, columns=['ts','Open','High','Low','Close','Volume','ct','qv','tr','tbv','tbq','ig'])
                        for _c in ['Open','High','Low','Close','Volume']:
                            _kdf[_c] = _kdf[_c].astype(float)
                        _kdf.index = _pd.to_datetime(_kdf['ts'], unit='ms')
                        data[_sym] = _kdf[['Open','High','Low','Close','Volume']]
                except Exception:
                    pass
            print(f"  After Binance fallback: {len(data)}/{len(symbols)} symbols")
        return data

    for symbol in symbols:
        try:
            if len(symbols) == 1:
                df = raw
            else:
                df = raw[symbol] if symbol in raw.columns.get_level_values(0) else None

            if df is None or df.empty:
                continue

            # Drop rows where Close is NaN
            df = df.dropna(subset=["Close"])
            if len(df) < 10:
                continue

            data[symbol] = df
        except Exception:
            continue

    print(f"  Got data for {len(data)}/{len(symbols)} symbols")
    return data


def fetch_context_data() -> dict:
    """Fetch supplementary data: Fear & Greed, CoinGecko trending, etc."""
    import urllib.request
    import urllib.error

    context = {}

    # Fear & Greed Index
    try:
        req = urllib.request.Request(FEAR_GREED_URL,
                                    headers={"User-Agent": "ALPHA_ENGINE/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            context["fear_greed"] = json.loads(resp.read())
    except Exception:
        pass

    # CoinGecko trending
    try:
        url = f"{COINGECKO_BASE}/search/trending"
        req = urllib.request.Request(url, headers={"User-Agent": "ALPHA_ENGINE/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            context["coingecko_trending"] = json.loads(resp.read())
    except Exception:
        pass

    # Binance funding rates (for top crypto) -- with endpoint failover
    try:
        from config import BINANCE_FUTURES_BASE
        try:
            from config import BINANCE_FUTURES_FALLBACK_URLS
        except ImportError:
            BINANCE_FUTURES_FALLBACK_URLS = []
        _fapi_bases = [BINANCE_FUTURES_BASE] + BINANCE_FUTURES_FALLBACK_URLS
        funding = {}
        for symbol, info in list(CRYPTO_SYMBOLS.items())[:10]:
            binance_sym = info.get("binance")
            if not binance_sym:
                continue
            for _fbase in _fapi_bases:
                try:
                    url = f"{_fbase}/fapi/v1/fundingRate?symbol={binance_sym}&limit=1"
                    req = urllib.request.Request(url, headers={"User-Agent": "ALPHA_ENGINE/1.0"})
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        resp_data = json.loads(resp.read())
                        if resp_data:
                            funding[symbol] = float(resp_data[0]["fundingRate"])
                    break  # success, stop trying endpoints
                except urllib.error.HTTPError as e:
                    if e.code in (451, 403):
                        continue  # geo-blocked, try next
                    break
                except Exception:
                    continue
        context["funding_rates"] = funding
    except Exception:
        pass

    # Regime Sentinel: 4-state on-chain cycle classifier (MVRV + F&G + funding)
    if _HAS_REGIME_SENTINEL:
        try:
            sentinel = get_regime_sentinel()
            context["regime_sentinel"] = sentinel
            print(f"  Regime Sentinel: {sentinel['regime']} "
                  f"(conf={sentinel['confidence']:.0%}, "
                  f"risk_mult={sentinel['risk_multiplier']}x, "
                  f"bias={sentinel['action_bias']})")
        except Exception as e:
            print(f"  Warning: Regime Sentinel failed: {e}")

    # HMM Regime data (from Regime Terminal bridge)
    hmm_regime_path = Path(__file__).parent / "data" / "hmm_regime.json"
    if hmm_regime_path.exists():
        try:
            with open(hmm_regime_path) as f:
                hmm_data = json.load(f)
            context["hmm_regime"] = hmm_data
            agg = hmm_data.get("aggregate", {})
            n_symbols = len(hmm_data.get("per_symbol", {}))
            print(f"  HMM regime: {agg.get('market_regime', '?')} | "
                  f"crypto: {agg.get('crypto_regime', '?')} | "
                  f"conf: {agg.get('hmm_confidence', 0):.0%} | "
                  f"{n_symbols} symbols")
        except Exception:
            pass

    return context


# ---------------------------------------------------------------------------
# Pick Management
# ---------------------------------------------------------------------------

def check_open_picks(db: SQLiteStore, data: dict[str, pd.DataFrame]) -> list[dict]:
    """
    Check all open picks against current prices.
    Close picks that hit TP, SL, trailing stop, or max hold time.
    Returns list of closed pick summaries.
    """
    closed = []
    open_picks = db.get_open_picks()

    for pick in open_picks:
        symbol = pick["symbol"]
        df = data.get(symbol)
        if df is None:
            continue

        current_price = float(df["Close"].iloc[-1])
        entry_price = pick["entry_price"]
        tp = pick["take_profit"]
        sl = pick["stop_loss"]
        category = pick.get("category", "stock")
        signal_type = pick.get("signal_type", "BUY")

        # Track high water mark
        high_price = float(df["High"].iloc[-1])
        hwm = pick.get("high_water_mark") or entry_price
        hwm = max(hwm, high_price)

        # Hold duration
        try:
            entry_dt = datetime.strptime(pick["entry_date"], "%Y-%m-%d")
            now_dt = datetime.now(timezone.utc).replace(tzinfo=None)
            hold_days = (now_dt - entry_dt).days
        except (ValueError, TypeError):
            hold_days = 0

        exit_reason = None
        exit_price = current_price

        if signal_type == "BUY":
            # Take profit hit
            if tp and current_price >= tp:
                exit_reason = "TP_HIT"
                exit_price = tp
            # Stop loss hit
            elif sl and current_price <= sl:
                exit_reason = "SL_HIT"
                exit_price = sl
            # Trailing stop
            elif TRAILING_STOP.get(category):
                profit_pct = (hwm - entry_price) / entry_price
                if profit_pct > TRAIL_ACTIVATE_PCT:
                    trail_pct = TRAILING_STOP[category]
                    trail_level = hwm * (1 - trail_pct)
                    if current_price <= trail_level:
                        exit_reason = "TRAILING"
                        exit_price = current_price
        elif signal_type == "SELL":
            if tp and current_price <= tp:
                exit_reason = "TP_HIT"
                exit_price = tp
            elif sl and current_price >= sl:
                exit_reason = "SL_HIT"
                exit_price = sl

        # Max hold time
        _, _, max_hold = CATEGORY_RISK.get(category, (-0.08, 0.15, 10))
        if hold_days >= max_hold and exit_reason is None:
            exit_reason = "TIME_EXIT"

        if exit_reason:
            # Normalize exit_reason to canonical bucket (issue #186)
            if _normalize_exit_reason is not None:
                exit_reason = _normalize_exit_reason(exit_reason)
            # Apply transaction costs to closed pick
            category = pick.get("category", "stock")
            cost_data = apply_costs(entry_price, exit_price, symbol, category, signal_type)
            result = db.close_pick(
                pick["id"], exit_price, exit_reason, hwm,
                transaction_cost_pct=cost_data["transaction_cost_pct"],
                cost_model=cost_data["cost_model"],
            )
            closed.append(result)

            # Update conformal prediction calibration with closed trade outcome
            if _conformal_sizer is not None:
                _ml_at_entry = pick.get("ml_score") or 0.5
                _extra = json.loads(pick["extra_json"]) if pick.get("extra_json") else {}
                if _extra.get("ml_score"):
                    _ml_at_entry = float(_extra["ml_score"])
                _win = 1.0 if exit_reason == "TP_HIT" else 0.0
                _conformal_sizer.update(_ml_at_entry, _win)

            # Record trade outcome in tournament engine (feature-flagged)
            try:
                use_tournament = os.environ.get("ALPHA_TOURNAMENT", "0") == "1"
                if use_tournament:
                    from tournament_engine import TournamentEngine
                    from config import DATA_DIR as _DATA_DIR
                    _db_path = str(_DATA_DIR / "alpha.db")
                    status = result.get("status", "")
                    pnl_pct = result.get("pnl_pct", 0) or 0
                    won = (status == "WON")
                    regime = pick.get("regime", "all") or "all"

                    for portfolio_name in ["conservative", "moderate", "aggressive"]:
                        te = TournamentEngine(_db_path, portfolio=portfolio_name)
                        te.record_trade(pick["strategy"], won=won,
                                       pnl_pct=pnl_pct, regime=regime)
                        # Record combo if confluence data exists
                        extra = json.loads(pick["extra_json"]) if pick.get("extra_json") else {}
                        combo_strats = extra.get("confluence_strategies")
                        if combo_strats and len(combo_strats) > 1:
                            combo_id = te.get_combo_id(combo_strats)
                            te.record_trade(combo_id, won=won,
                                          pnl_pct=pnl_pct, entity_type="combo", regime=regime)
                        te.evaluate(pick["strategy"], regime=regime)
            except Exception as e:
                print(f"  Warning: Tournament recording failed for {pick.get('strategy', '?')}: {e}")

    return closed


# ---------------------------------------------------------------------------
# ML Feature Contract -- compute features at signal time (OHLCV is fresh)
# ---------------------------------------------------------------------------

def _compute_rsi_raw(close: pd.Series, period: int = 14) -> float:
    """Compute RSI from a close price series. Returns last RSI value."""
    if len(close) < period + 1:
        return 50.0
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window=period, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period, min_periods=period).mean()
    rs = gain / loss.replace(0, 1e-10)
    rsi_val = 100 - (100 / (1 + rs))
    last = rsi_val.iloc[-1]
    return float(last) if pd.notna(last) else 50.0


def _compute_macd_signal_raw(close: pd.Series) -> float:
    """Compute MACD histogram (MACD line - signal line), normalized."""
    if len(close) < 35:
        return 0.0
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    last_hist = histogram.iloc[-1]
    if pd.isna(last_hist):
        return 0.0
    mean_price = close.iloc[-1]
    if mean_price > 0:
        return float(last_hist / mean_price)  # normalize by price
    return 0.0


def _compute_bb_position_raw(close: pd.Series) -> float:
    """Compute Bollinger Band position: (close - SMA20) / (2 * std20). Range ~[-1, 1]."""
    if len(close) < 20:
        return 0.0
    sma20 = close.rolling(20).mean().iloc[-1]
    std20 = close.rolling(20).std().iloc[-1]
    if pd.isna(sma20) or pd.isna(std20) or std20 == 0:
        return 0.0
    return float(max(-2.0, min(2.0, (close.iloc[-1] - sma20) / (2.0 * std20))))


def _compute_atr_pct_raw(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
    """Compute ATR as percentage of close price."""
    if len(close) < period + 1:
        return 0.0
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr_val = tr.rolling(period).mean().iloc[-1]
    if pd.isna(atr_val) or close.iloc[-1] == 0:
        return 0.0
    return float(atr_val / close.iloc[-1])


def compute_ml_features_at_entry(symbol: str, data: dict, signal: dict) -> dict:
    """Compute full ML feature vector at entry time while OHLCV data is available.

    These features are stored with the signal/pick and used by ml_ranker.py
    for both training and scoring, solving the stale-data problem where
    features were extracted later from missing/default data.
    """
    features = {}
    try:
        df = data.get(symbol)
        if df is None:
            # Try first available key as fallback
            keys = list(data.keys())
            df = data[keys[0]] if keys else None
        if df is None or df.empty:
            return features

        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume'] if 'Volume' in df.columns else pd.Series(dtype=float)

        # --- Price / momentum features ---
        features['rsi_14'] = _compute_rsi_raw(close, 14)
        features['rsi_7'] = _compute_rsi_raw(close, 7)
        features['macd_signal'] = _compute_macd_signal_raw(close)
        features['bb_position'] = _compute_bb_position_raw(close)
        features['atr_pct'] = _compute_atr_pct_raw(high, low, close)

        # Volume ratio: current bar vs 20-bar average
        if len(volume) > 20:
            vol_mean = volume.rolling(20).mean().iloc[-1]
            features['volume_ratio'] = float(volume.iloc[-1] / vol_mean) if vol_mean > 0 else 1.0
        else:
            features['volume_ratio'] = 1.0

        # Price vs SMAs
        if len(close) > 20:
            sma20 = close.rolling(20).mean().iloc[-1]
            features['price_vs_sma20'] = float(close.iloc[-1] / sma20 - 1) if sma20 > 0 else 0.0
        else:
            features['price_vs_sma20'] = 0.0

        if len(close) > 50:
            sma50 = close.rolling(50).mean().iloc[-1]
            features['price_vs_sma50'] = float(close.iloc[-1] / sma50 - 1) if sma50 > 0 else 0.0
        else:
            features['price_vs_sma50'] = 0.0

        if len(close) > 200:
            sma200 = close.rolling(200).mean().iloc[-1]
            features['price_vs_sma200'] = float(close.iloc[-1] / sma200 - 1) if sma200 > 0 else 0.0
        else:
            features['price_vs_sma200'] = 0.0

        # --- Time features ---
        import datetime as _dt
        now = _dt.datetime.utcnow()
        hour = now.hour
        features['hour_sin'] = math.sin(2 * math.pi * hour / 24)
        features['hour_cos'] = math.cos(2 * math.pi * hour / 24)
        features['day_of_week'] = now.weekday()
        features['is_weekend'] = 1.0 if now.weekday() >= 5 else 0.0

        # --- Volatility regime ---
        if len(close) >= 30:
            recent_vol = float(close.pct_change().tail(5).std())
            hist_vol = float(close.pct_change().tail(30).std())
            features['vol_ratio'] = recent_vol / max(hist_vol, 1e-8)
            if recent_vol < hist_vol * 0.5:
                features['vol_regime'] = 0  # low
            elif recent_vol > hist_vol * 1.5:
                features['vol_regime'] = 2  # high
            else:
                features['vol_regime'] = 1  # medium

        # --- Momentum features ---
        if len(close) >= 7:
            features['momentum_7d'] = float(close.iloc[-1] / close.iloc[-7] - 1)
        if len(close) >= 14:
            features['momentum_14d'] = float(close.iloc[-1] / close.iloc[-14] - 1)

        # --- Candle features ---
        if 'Open' in df.columns:
            body = abs(float(close.iloc[-1] - df['Open'].iloc[-1]))
            wick = float(high.iloc[-1] - low.iloc[-1])
            features['body_ratio'] = body / max(wick, 1e-8)

        # --- Funding rate features (Phase 6 -- strongest 4h-1d predictors) ---
        # Fetch live funding rate from Binance Futures API for crypto symbols
        try:
            import urllib.request
            import urllib.error
            # Normalize symbol for Binance futures (e.g., BTC -> BTCUSDT)
            _sym_upper = symbol.upper().replace("-", "").replace("/", "")
            if not _sym_upper.endswith("USDT"):
                _sym_upper = _sym_upper.replace("USD", "") + "USDT"
            # Binance Futures mirrors failover (API rule)
            _fresp = None
            for _fbase in [
                "https://fapi.binance.com",
                "https://fapi1.binance.com",
                "https://fapi2.binance.com",
            ]:
                try:
                    funding_url = f'{_fbase}/fapi/v1/fundingRate?symbol={_sym_upper}&limit=30'
                    _freq = urllib.request.Request(funding_url)
                    _freq.add_header('User-Agent', 'Mozilla/5.0')
                    _fresp = json.loads(urllib.request.urlopen(_freq, timeout=5).read())
                    if _fresp:
                        break
                except Exception:
                    continue
            # CoinGecko funding rate fallback (not directly available, skip gracefully)
            # KuCoin funding rate fallback
            if not _fresp:
                try:
                    _kc_fsym = _sym_upper.replace("USDT", "-USDT")
                    _kc_furl = f"https://api-futures.kucoin.com/api/v1/funding-rate/{_kc_fsym}/current"
                    _kc_freq = urllib.request.Request(_kc_furl)
                    _kc_freq.add_header('User-Agent', 'Mozilla/5.0')
                    _kc_fraw = json.loads(urllib.request.urlopen(_kc_freq, timeout=5).read())
                    _kc_fdata = _kc_fraw.get("data", {}) if isinstance(_kc_fraw, dict) else {}
                    if _kc_fdata and "value" in _kc_fdata:
                        _fresp = [{"fundingRate": str(_kc_fdata["value"])}]
                except Exception:
                    pass
            if _fresp and isinstance(_fresp, list):
                features['funding_rate_raw'] = float(_fresp[-1].get('fundingRate', 0))

                # Z-score vs 30-period rolling mean/std
                _rates = [float(r.get('fundingRate', 0)) for r in _fresp]
                if len(_rates) >= 5:
                    _mean = sum(_rates) / len(_rates)
                    _std = (sum((r - _mean) ** 2 for r in _rates) / len(_rates)) ** 0.5
                    features['funding_z_30d'] = (_rates[-1] - _mean) / max(_std, 1e-8)
                else:
                    features['funding_z_30d'] = 0.0

                # Persistence: count consecutive same-sign funding periods
                _persist = 0
                if len(_rates) >= 2:
                    _last_sign = 1 if _rates[-1] >= 0 else -1
                    for _r in reversed(_rates[:-1]):
                        _r_sign = 1 if _r >= 0 else -1
                        if _r_sign == _last_sign:
                            _persist += 1
                        else:
                            break
                    _persist = _persist * _last_sign  # positive = consecutive positive funding
                features['funding_persistence'] = float(_persist)
        except Exception:
            features.setdefault('funding_rate_raw', 0.0)
            features.setdefault('funding_z_30d', 0.0)
            features.setdefault('funding_persistence', 0.0)

        # --- Open interest 24h change (Binance fapi via coinalyze_client) ---
        # Persisted into ml_features_at_entry so oi_change_24h accumulates a
        # history on every crypto pick. NOT yet a model feature: once ~30-60d
        # of data exists it can be added to ml_ranker FEATURE_LIST (full
        # retrain) or used as an OI-extreme regime gate. Adding an unused key
        # to the feature dict is harmless -- the vectorizer only reads keys in
        # FEATURE_LIST. See reports/oi_ml_ranker_plan_2026-05-17.md.
        try:
            from coinalyze_client import get_open_interest as _get_oi
            _oi = _get_oi(symbol)
            features['oi_change_24h'] = float(_oi.get('oi_change_24h', 0.0) or 0.0)
        except Exception:
            features.setdefault('oi_change_24h', 0.0)

        # --- Chi-squared validated technical features (7 indicators) ---
        # Pure-Python computation from OHLCV arrays; injected onto signal dict
        # for ML ranker consumption (mom30, rsi30, macd_hist_norm, stoch_k30,
        # stoch_d30, cci20_norm, williams_r).
        if _compute_tech_features is not None:
            try:
                _closes_list = [float(c) for c in close.tolist()]
                _highs_list = [float(h) for h in high.tolist()]
                _lows_list = [float(l) for l in low.tolist()]
                _vols_list = [float(v) for v in volume.tolist()] if len(volume) > 0 else []
                _tech = _compute_tech_features(_closes_list, _highs_list, _lows_list, _vols_list)
                features.update(_tech)
            except Exception:
                pass

        # Sanitize: replace NaN/inf with None
        for k, v in list(features.items()):
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                features[k] = None

    except Exception:
        pass
    return features


# ---------------------------------------------------------------------------
# Signal Processing
# ---------------------------------------------------------------------------

def _update_scan_timing(total_ms: float) -> dict:
    """Update rolling-window scan timing stats and persist to data/scan_timing.json.

    Maintains the last 100 scan durations to compute avg, P50, P99 percentiles.
    Returns the timing report dict.
    """
    timing_path = DATA_DIR / "scan_timing.json"
    history: list[float] = []

    # Load existing history
    if timing_path.exists():
        try:
            with open(timing_path, "r") as f:
                existing = json.load(f)
            history = existing.get("history_ms", [])
        except (json.JSONDecodeError, IOError):
            pass

    # Append current and cap at 100
    history.append(round(total_ms, 1))
    if len(history) > 100:
        history = history[-100:]

    arr = sorted(history)
    n = len(arr)
    avg_ms = sum(arr) / n if n else 0
    p50_ms = arr[n // 2] if n else 0
    p99_idx = min(n - 1, int(n * 0.99))
    p99_ms = arr[p99_idx] if n else 0

    report = {
        "last_scan_ms": round(total_ms, 1),
        "avg_scan_ms": round(avg_ms, 1),
        "p50_scan_ms": round(p50_ms, 1),
        "p99_scan_ms": round(p99_ms, 1),
        "scans_recorded": n,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "history_ms": history,
    }

    try:
        timing_path.parent.mkdir(parents=True, exist_ok=True)
        with open(timing_path, "w") as f:
            json.dump(report, f, indent=2)
    except IOError as e:
        logging.warning("Failed to write scan_timing.json: %s", e)

    return report


def run_strategies(data: dict[str, pd.DataFrame], context: dict,
                   strategy_filter: str = "all") -> list[dict]:
    """Run all strategies and collect signals. Skips disabled strategies."""
    all_signals = []
    _signal_counts: dict[str, int] = {}  # Per-strategy signal throttle
    _strategy_timings: dict[str, float] = {}  # Per-strategy timing (ms)
    strategies = {}

    def _normalize_signal_type(signal: dict) -> str:
        raw = str(signal.get("signal_type", signal.get("direction", ""))).upper()
        if raw in ("BUY", "LONG"):
            return "BUY"
        if raw in ("SELL", "SHORT"):
            return "SELL"
        return ""

    if strategy_filter in ("all", "crypto"):
        strategies.update(CRYPTO_STRATEGIES)
    if strategy_filter in ("all", "forex"):
        strategies.update(FOREX_STRATEGIES)
    if strategy_filter in ("all", "equity"):
        strategies.update(EQUITY_STRATEGIES)
    # Fast variants: always loaded (they span crypto + equity + commodities)
    if strategy_filter == "all" and FAST_VARIANT_STRATEGIES:
        strategies.update(FAST_VARIANT_STRATEGIES)
    # Advanced strategies (dip amplifiers, quant overlays)
    if strategy_filter in ("all", "crypto") and ADVANCED_STRATEGIES:
        strategies.update(ADVANCED_STRATEGIES)
    # Keltner Evolved: genetically evolved variants (sandbox)
    if strategy_filter in ("all", "crypto") and KELTNER_EVOLVED_STRATEGIES:
        strategies.update(KELTNER_EVOLVED_STRATEGIES)
    # Super Strategies: 10 confluence-based strategies (sandbox)
    if strategy_filter in ("all", "crypto") and SUPER_STRATEGIES:
        strategies.update(SUPER_STRATEGIES)
    # VPIN: informed flow detection from Binance aggTrades (Easley et al. 2012)
    if strategy_filter in ("all", "crypto") and VPIN_STRATEGIES:
        strategies.update(VPIN_STRATEGIES)
    # LunarCrush: social sentiment momentum from Galaxy Score API
    if strategy_filter in ("all", "crypto") and LUNARCRUSH_STRATEGIES:
        strategies.update(LUNARCRUSH_STRATEGIES)
    # Quant: pairs trading, TSMOM, cointegration (market-neutral)
    if strategy_filter in ("all", "crypto") and QUANT_STRATEGIES:
        strategies.update(QUANT_STRATEGIES)
    # Untapped: Google Trends contrarian, rare high-WR signals
    if strategy_filter in ("all", "crypto") and UNTAPPED_STRATEGIES:
        strategies.update(UNTAPPED_STRATEGIES)
    # COT: CFTC positioning for forex (weekly, extreme = signal)
    if strategy_filter in ("all", "forex") and COT_STRATEGIES:
        strategies.update(COT_STRATEGIES)
    # Commodities: seasonal, metals MR, energy breakout, DXY inverse
    if strategy_filter in ("all", "commodity") and COMMODITY_STRATEGIES:
        strategies.update(COMMODITY_STRATEGIES)
    # Futures: TSMOM, ConnorsRSI2, cross-asset momentum, vol-regime breakout
    if strategy_filter in ("all", "futures") and FUTURES_STRATEGIES:
        strategies.update(FUTURES_STRATEGIES)
    # ETF: dual momentum, sector rotation, risk parity, trend following
    if strategy_filter in ("all", "etf") and ETF_STRATEGIES:
        strategies.update(ETF_STRATEGIES)
    # Bond: yield momentum, duration rotation, BB mean reversion
    if strategy_filter in ("all", "bond") and BOND_STRATEGIES:
        strategies.update(BOND_STRATEGIES)
    # TVL Momentum: DefiLlama capital flow → tradeable crypto picks
    if strategy_filter in ("all", "crypto") and TVL_MOMENTUM_STRATEGIES:
        strategies.update(TVL_MOMENTUM_STRATEGIES)
    # TTM Squeeze: BB inside Keltner compression breakout
    if strategy_filter in ("all", "crypto") and TTM_SQUEEZE_STRATEGIES:
        strategies.update(TTM_SQUEEZE_STRATEGIES)
    # Binance Sentiment: L/S ratio, taker volume, OI divergence
    if strategy_filter in ("all", "crypto") and SENTIMENT_STRATEGIES:
        strategies.update(SENTIMENT_STRATEGIES)
    # Survivor Strategies: backtested survivors (connors_r3, keltner, bollinger, vol_scaled, williams_r)
    if strategy_filter in ("all", "crypto") and SURVIVOR_STRATEGIES:
        strategies.update(SURVIVOR_STRATEGIES)
    # CryptoPanic News Sentiment + Fear & Greed DCA (contrarian on sentiment extremes)
    if strategy_filter in ("all", "crypto") and CRYPTOPANIC_STRATEGIES:
        strategies.update(CRYPTOPANIC_STRATEGIES)
    # Sentiment-Price Divergence: F&G/Galaxy vs price trend divergence (reversal)
    if strategy_filter in ("all", "crypto") and DIVERGENCE_STRATEGIES:
        strategies.update(DIVERGENCE_STRATEGIES)
    # Technical Divergence: RSI/MFI/TSI divergence + market structure + trailing entry
    if strategy_filter in ("all", "crypto") and TECHNICAL_DIVERGENCE_STRATEGIES:
        strategies.update(TECHNICAL_DIVERGENCE_STRATEGIES)
    # GARCH(1,1) Volatility: vol breakout + vol mean-reversion
    if strategy_filter in ("all", "crypto") and GARCH_STRATEGIES:
        strategies.update(GARCH_STRATEGIES)
    # Cointegration Pairs: statistical arbitrage on cointegrated pairs (mean reversion)
    if strategy_filter in ("all", "crypto") and COINTEGRATION_STRATEGIES:
        strategies.update(COINTEGRATION_STRATEGIES)
    # Candlestick Patterns: classic reversal/continuation patterns
    if strategy_filter in ("all", "crypto") and CANDLESTICK_STRATEGIES:
        strategies.update(CANDLESTICK_STRATEGIES)
    # Hoffman Strategy: inventory retracement bar (trend following)
    if strategy_filter in ("all", "crypto") and HOFFMAN_STRATEGIES:
        strategies.update(HOFFMAN_STRATEGIES)
    # Session Breakout: London/NY/Asian session range breakout (momentum)
    if strategy_filter in ("all", "crypto", "forex") and SESSION_STRATEGIES:
        strategies.update(SESSION_STRATEGIES)
    # Range Breakout: consolidation range breakout with volume confirmation
    if strategy_filter in ("all", "crypto") and RANGE_BREAKOUT_STRATEGIES:
        strategies.update(RANGE_BREAKOUT_STRATEGIES)
    # CNN-Lite Pattern Recognition: universal chart pattern detection
    if strategy_filter in ("all", "crypto", "forex", "equity") and CNN_LITE_STRATEGIES:
        strategies.update(CNN_LITE_STRATEGIES)
    # Cascade Contrarian: OI/MCap + funding rate cascade reversal
    if strategy_filter in ("all", "crypto") and CASCADE_CONTRARIAN_STRATEGIES:
        strategies.update(CASCADE_CONTRARIAN_STRATEGIES)
    # Hybrid Confluence: VWAP+RSI, Hoffman+Keltner, AI EMA pullback (crypto + forex)
    if strategy_filter in ("all", "crypto", "forex") and HYBRID_STRATEGIES:
        strategies.update(HYBRID_STRATEGIES)
    # Antigravity (Google Gemini): VWAP-RSI institutional, liquidation cascade, regime sentinel, RSI pairs
    if strategy_filter in ("all", "crypto") and ANTIGRAVITY_STRATEGIES:
        strategies.update(ANTIGRAVITY_STRATEGIES)
    # Vibe-trading vt_* babies: LuxAlgo alts, Myfxbook sentiment, restatement short, GDX/SLV stat-arb,
    # bond_yield_curve_momentum (BOND), copper_platinum_cot_momentum (COMMODITY)
    if strategy_filter in ("all", "crypto", "equity", "forex", "bond", "commodity") and VT_BABY_STRATEGIES:
        strategies.update(VT_BABY_STRATEGIES)
    # Flow & Behavioral: stablecoin flow momentum + disposition effect contrarian
    if strategy_filter in ("all", "crypto") and FLOW_BEHAVIORAL_STRATEGIES:
        strategies.update(FLOW_BEHAVIORAL_STRATEGIES)
    # Fundamental Valuation: BTC power law, NVM Metcalfe, ETH gas reversal
    if strategy_filter in ("all", "crypto") and FUNDAMENTAL_VALUATION_STRATEGIES:
        strategies.update(FUNDAMENTAL_VALUATION_STRATEGIES)
    # Institutional On-Chain: COT positioning, OI breakout, miner capitulation
    if strategy_filter in ("all", "crypto") and INSTITUTIONAL_ONCHAIN_STRATEGIES:
        strategies.update(INSTITUTIONAL_ONCHAIN_STRATEGIES)
    # Sideways Market: grid range scalper, squeeze range fade, intraday seasonality
    if strategy_filter in ("all", "crypto") and SIDEWAYS_MARKET_STRATEGIES:
        strategies.update(SIDEWAYS_MARKET_STRATEGIES)
    # Microstructure Momentum: VPIN spike continuation + cointegration half-life pairs
    if strategy_filter in ("all", "crypto") and MICROSTRUCTURE_MOMENTUM_STRATEGIES:
        strategies.update(MICROSTRUCTURE_MOMENTUM_STRATEGIES)
    # Novel Quick-Win: VRP signal, stablecoin flow on-chain, correlation breakout
    if strategy_filter in ("all", "crypto") and NOVEL_STRATEGIES:
        strategies.update(NOVEL_STRATEGIES)
    # Supplemental Data: Messari fundamentals, mempool.space BTC, Ethplorer ERC-20 whales
    if strategy_filter in ("all", "crypto") and SUPPLEMENTAL_DATA_STRATEGIES:
        strategies.update(SUPPLEMENTAL_DATA_STRATEGIES)
    # Wave 4/5/6: Coinlore, Blockchain.info, Solana, Gemini, DefiLlama
    if strategy_filter in ("all", "crypto") and WAVE456_STRATEGIES:
        strategies.update(WAVE456_STRATEGIES)
    # CTA Bridge: academic CTA strategies across forex, equity, commodity
    if strategy_filter in ("all", "forex", "equity") and CTA_BRIDGE_STRATEGIES:
        strategies.update(CTA_BRIDGE_STRATEGIES)
    # High-Accuracy Phase 1: KAMA Adaptive, RSI-MACD-Vol Confluence, Kalman Filter (65-72% WR)
    if strategy_filter in ("all", "crypto") and HIGH_ACCURACY_STRATEGIES:
        strategies.update(HIGH_ACCURACY_STRATEGIES)
    # Volume & Microstructure: OBV, Volume Profile, MFI, Williams %R, Vol-MA Cross, LinReg
    # NOTE: These use metadata dicts, not callables. Picks come from generate_volume_micro_picks()
    # called separately below. Do NOT merge VOLUME_MICRO_STRATEGIES into strategies dict.
    # Advanced Quant: Beta-Neutral Arb, Vol Arb, Corr Breakdown, KDE Bands, Poisson Events
    if strategy_filter in ("all", "crypto") and ADVANCED_QUANT_STRATEGIES:
        strategies.update(ADVANCED_QUANT_STRATEGIES)
    # Advanced Statistical: Fractal Dimension, DFA Timer, PCA Factor Rotation
    if strategy_filter in ("all", "crypto") and ADVANCED_STATISTICAL_STRATEGIES:
        strategies.update(ADVANCED_STATISTICAL_STRATEGIES)
    # Gainer Capture: early momentum, breakout continuation, momentum portfolio
    if strategy_filter in ("all", "crypto") and GAINER_CAPTURE_STRATEGIES:
        strategies.update(GAINER_CAPTURE_STRATEGIES)
    # Multi-Signal Confluence: 4-layer confirmation (3of4, 4of4, weighted variants)
    if strategy_filter in ("all", "crypto") and CONFLUENCE_STRATEGIES:
        strategies.update(CONFLUENCE_STRATEGIES)
    # Wavelet Transform + Cycle Detection: Haar multi-scale trend, DFT periodogram timing
    if strategy_filter in ("all", "crypto") and WAVELET_CYCLE_STRATEGIES:
        strategies.update(WAVELET_CYCLE_STRATEGIES)
    # Quant Stack: KAMA + ATR Trailing Stop + Regime Switch (Mercury 2 blueprint)
    if strategy_filter in ("all", "crypto") and QUANT_STACK_STRATEGIES:
        strategies.update(QUANT_STACK_STRATEGIES)
    # Trend Catcher: adaptive SuperTrend pullback, EMA stack, Donchian rider, Keltner squeeze (4H)
    if strategy_filter in ("all", "crypto") and TREND_CATCHER_STRATEGIES:
        strategies.update(TREND_CATCHER_STRATEGIES)
    # EMA Retracement Mean Reversion: dynamic S/R bounce (21/50/stack) with regime filter
    if strategy_filter in ("all", "crypto") and EMA_RETRACEMENT_STRATEGIES:
        strategies.update(EMA_RETRACEMENT_STRATEGIES)
    # Inverse Edge: flip signals from structural losers (WR<40%, split-half validated)
    if strategy_filter in ("all", "crypto") and INVERSE_EDGE_STRATEGIES:
        strategies.update(INVERSE_EDGE_STRATEGIES)
    
    # World-Class v2.1 "Truly Strong" Suite: Night Alpha, Regime Momentum, Sector Relative
    if strategy_filter == "all" and WORLD_CLASS_V21_STRATEGIES:
        strategies.update(WORLD_CLASS_V21_STRATEGIES)
    # Proven Edge: night session scalper, fear/greed short contrarian, high trust momentum
    if strategy_filter in ("all", "crypto") and PROVEN_EDGE_STRATEGIES:
        strategies.update(PROVEN_EDGE_STRATEGIES)
    # Crypto Edge: funding rate extreme, OI-price divergence v2, liquidation flush recovery
    if strategy_filter in ("all", "crypto") and CRYPTO_EDGE_STRATEGIES:
        strategies.update(CRYPTO_EDGE_STRATEGIES)
    # Confluence V2: fear+keltner, RSI+volume+regime, whale+momentum+trust, multi-source, night+fear+short
    if strategy_filter in ("all", "crypto") and CONFLUENCE_V2_STRATEGIES:
        strategies.update(CONFLUENCE_V2_STRATEGIES)
    # Volatility Mean Reversion: universal strategy — Cycle 13 breakthrough (30/30 profitable)
    if strategy_filter == "all" and VOL_MR_STRATEGIES:
        strategies.update(VOL_MR_STRATEGIES)
    # Cycle 16 strategies: MACD divergence, momentum breakout, mean reversion ATR, trend ensemble
    if strategy_filter == "all" and CYCLE16_STRATEGIES:
        strategies.update(CYCLE16_STRATEGIES)
    # Cycle 17 strategies: stoch_rsi, pivot_reversion, ichimoku, yield_curve_proxy, range_trading
    if strategy_filter == "all" and CYCLE17_STRATEGIES:
        strategies.update(CYCLE17_STRATEGIES)

    # Load disabled strategies and direction restrictions from auto-tuner
    disabled = set()
    direction_restrictions = {}
    boost_factors = {}
    _is_strategy_disabled = None
    try:
        from auto_tuner import (get_disabled_strategies, get_direction_restrictions,
                                get_boost_factors, is_strategy_disabled as _isd)
        disabled = get_disabled_strategies()
        _is_strategy_disabled = _isd
        direction_restrictions = get_direction_restrictions()
        boost_factors = get_boost_factors()
        if disabled:
            print(f"  Auto-tuner: {len(disabled)} strategies disabled")
        if direction_restrictions:
            print(f"  Auto-tuner: {len(direction_restrictions)} strategies direction-restricted")
        if boost_factors:
            boosted = {k: v for k, v in boost_factors.items() if v > 1.0}
            if boosted:
                print(f"  Auto-tuner: {len(boosted)} strategies boosted")
    except Exception:
        pass

    # Pre-compute regime cache for all symbols (Action 3.1 + HMM overlay)
    regime_cache = compute_regime_cache(data, context)
    regime_counts = {"trending": 0, "ranging": 0, "transitional": 0, "unknown": 0}
    for sym, rinfo in regime_cache.items():
        r = rinfo.get("regime", "unknown")
        regime_counts[r] = regime_counts.get(r, 0) + 1
    print(f"  Regime detection: {regime_counts}")

    _strategies_t0 = time.perf_counter()
    _n_symbols = len(data)

    for name, func in strategies.items():
        if name in GENERATOR_HARD_KILL:
            continue  # HARD KILL at generator level -- no signals allowed
        if name in disabled:
            continue  # Skip disabled strategy (exact name match)
        # Pattern + category check (e.g. *_15m_D_ensemble_stack, forex)
        if _is_strategy_disabled is not None and _is_strategy_disabled(name):
            continue

        _strat_t0 = time.perf_counter()
        try:
            # Some strategies accept context (fear_greed, funding rates, etc.)
            import inspect
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())

            # Pattern 1: func(data, symbol) -- per-symbol strategies (keltner_evolved, ttm_squeeze, etc.)
            if params == ["data", "symbol"]:
                signals = []
                for sym, df in data.items():
                    try:
                        sigs = func(data, sym)
                        if sigs:
                            signals.extend(sigs)
                    except Exception:
                        pass
            # Pattern 2: func(symbol, df, market_data=...) -- per-symbol with DataFrame (hoffman, session, range, cnn)
            elif len(params) >= 2 and params[0] == "symbol" and params[1] == "df":
                signals = []
                for sym, df in data.items():
                    try:
                        sigs = func(sym, df, market_data=data)
                        if sigs:
                            signals.extend(sigs)
                    except Exception:
                        pass
            # Pattern 3: func(data, context=...) -- standard multi-symbol strategies
            elif "context" in sig.parameters:
                signals = func(data, context=context)
            else:
                signals = func(data)

            if signals:
                # Apply direction restrictions (Feb 26 2026)
                allowed_dir = direction_restrictions.get(name)
                if allowed_dir:
                    before = len(signals)
                    normalized = []
                    for s in signals:
                        s_type = _normalize_signal_type(s)
                        if s_type:
                            s["signal_type"] = s_type
                            normalized.append(s)
                    signals = [s for s in normalized if s.get("signal_type") == allowed_dir]
                    if before != len(signals):
                        print(f"  [{name}] direction filter: {before} -> {len(signals)} ({allowed_dir} only)")

                # Apply boost factors to ML score / confidence
                boost = boost_factors.get(name, 1.0)
                if boost > 1.0:
                    for s in signals:
                        s["boost_factor"] = boost
                        # Boost confidence by sqrt(factor) to avoid overriding caps
                        old_conf = s.get("confidence", 0.5)
                        s["confidence"] = round(min(0.95, old_conf * (boost ** 0.5)), 3)

                # Annotate each signal with regime info (Action 3.1)
                for i, s in enumerate(signals):
                    signals[i] = annotate_signal_with_regime(s, regime_cache)

                # Signal frequency throttle -- cap per strategy per scan
                remaining = MAX_SIGNALS_PER_STRATEGY_PER_SCAN - _signal_counts.get(name, 0)
                if remaining <= 0:
                    logging.info(f"Signal throttle: {name} hit {MAX_SIGNALS_PER_STRATEGY_PER_SCAN} limit")
                    continue
                if len(signals) > remaining:
                    logging.info(f"Signal throttle: {name} hit {MAX_SIGNALS_PER_STRATEGY_PER_SCAN} limit")
                    signals = signals[:remaining]
                _signal_counts[name] = _signal_counts.get(name, 0) + len(signals)

                # ML Feature Contract: compute features at signal time while OHLCV is fresh
                for s in signals:
                    sym = s.get("symbol", "")
                    s["ml_features_at_entry"] = compute_ml_features_at_entry(sym, data, s)
                    # Promote chi-squared technical features to top-level for ML ranker
                    _mf = s.get("ml_features_at_entry", {})
                    for _tk in ("mom30", "rsi30", "macd_hist_norm", "stoch_k30",
                                "stoch_d30", "cci20_norm", "williams_r"):
                        if _tk in _mf and _mf[_tk] is not None:
                            s[_tk] = _mf[_tk]

                all_signals.extend(signals)
                print(f"  [{name}] -> {len(signals)} signal(s)")
        except Exception as e:
            print(f"  [{name}] ERROR: {e}")
        finally:
            _strategy_timings[name] = (time.perf_counter() - _strat_t0) * 1000

    # -- Scan timing instrumentation -------------------------------------
    _strategies_elapsed_ms = (time.perf_counter() - _strategies_t0) * 1000
    _n_strategies_run = len(_strategy_timings)
    _per_strategy_avg_ms = (_strategies_elapsed_ms / _n_strategies_run) if _n_strategies_run else 0
    _per_symbol_avg_ms = (_strategies_elapsed_ms / _n_symbols) if _n_symbols else 0
    _timing_report = _update_scan_timing(_strategies_elapsed_ms)
    print(f"  Scan timing: {_strategies_elapsed_ms:.0f}ms "
          f"(avg={_timing_report['avg_scan_ms']:.0f}ms, "
          f"P99={_timing_report['p99_scan_ms']:.0f}ms) "
          f"| per_strategy={_per_strategy_avg_ms:.0f}ms, "
          f"per_symbol={_per_symbol_avg_ms:.0f}ms")

    # DNA Mutation 3: Anti-Consensus Contrarian -- fades extreme signal agreement
    try:
        from dna_mutations import anti_consensus_contrarian
        contrarian_signals = anti_consensus_contrarian(data, all_signals=all_signals)
        if contrarian_signals:
            all_signals.extend(contrarian_signals)
            print(f"  [anti_consensus_contrarian] -> {len(contrarian_signals)} contrarian signal(s)")
    except Exception as e:
        print(f"  [anti_consensus_contrarian] skipped: {e}")

    # DNA Mutations 6-8: Relaxed variants of high-WR strategies
    try:
        from dna_mutations import dna_hurst_relaxed, dna_ema_stack_relaxed, dna_fractal_bounce_relaxed
        for mut_fn in [dna_hurst_relaxed, dna_ema_stack_relaxed, dna_fractal_bounce_relaxed]:
            mut_signals = mut_fn(data)
            if mut_signals:
                all_signals.extend(mut_signals)
                print(f"  [{mut_fn.__name__}] -> {len(mut_signals)} signal(s)")
    except Exception as e:
        print(f"  [dna_mutations_6_8] skipped: {e}")

    # Incubator Strategies: 5 battle-tested Pine Script conversions
    # Triple Supertrend, ADX Momentum, TTM Squeeze, Dual Thrust ORB, ICT FVG
    try:
        from incubator_strategies import generate_incubator_picks
        incubator_picks = generate_incubator_picks()
        if incubator_picks:
            all_signals.extend(incubator_picks)
            print(f"  [incubator_strategies] -> {len(incubator_picks)} pick(s)")
    except Exception as e:
        print(f"  [incubator_strategies] skipped: {e}")

    # Beta-Adjusted Residual Momentum (Liu & Tsyvinski, RFS)
    try:
        from residual_momentum import beta_adjusted_residual_momentum
        resid_signals = beta_adjusted_residual_momentum(data)
        if resid_signals:
            all_signals.extend(resid_signals)
            print(f"  [beta_adjusted_residual_momentum] -> {len(resid_signals)} signal(s)")
    except Exception as e:
        print(f"  [beta_adjusted_residual_momentum] skipped: {e}")

    # Sweep Breakout Scaler -- reverse-engineered from top Binance copy trader
    try:
        from sweep_breakout_scaler import sweep_breakout_scan
        sweep_signals = sweep_breakout_scan(data)
        if sweep_signals:
            all_signals.extend(sweep_signals)
            print(f"  [sweep_breakout_scaler] -> {len(sweep_signals)} signal(s)")
    except Exception as e:
        print(f"  [sweep_breakout_scaler] skipped: {e}")

    # Cross-Sectional Reversal: LONG losers / SHORT winners (-0.6 corr with momentum)
    try:
        from reversal_strategies import scan_cross_sectional_reversal
        # Collect symbols where momentum strategies fired (avoid contradictions)
        _momentum_strat_names = {"cross_sectional_momentum", "momentum_catcher", "wavetrend_oscillator", "true_strength_index"}
        _momentum_syms = {s.get("symbol") for s in all_signals if s.get("strategy") in _momentum_strat_names}
        # Detect regime from existing signal annotations
        _reversal_regime = None
        for s in all_signals:
            _rr = s.get("extra", {}).get("regime") or s.get("regime_at_entry")
            if _rr:
                _reversal_regime = _rr
                break
        reversal_picks = scan_cross_sectional_reversal(
            existing_momentum_symbols=_momentum_syms,
            market_regime=_reversal_regime,
        )
        if reversal_picks:
            all_signals.extend(reversal_picks)
            print(f"  [cross_sectional_reversal] -> {len(reversal_picks)} reversal signal(s)")
    except Exception as e:
        print(f"  [cross_sectional_reversal] skipped: {e}")

    # Gap #1: Gainer-to-Pick auto-promotion
    try:
        from gainer_promoter import promote_top_gainers
        promoted = promote_top_gainers(data, existing_symbols={s.get("symbol") for s in all_signals})
        if promoted:
            all_signals.extend(promoted)
            print(f"  [gainer_promoter] -> {len(promoted)} auto-promoted gainer(s)")
    except Exception as e:
        print(f"  [gainer_promoter] skipped: {e}")

    # OKX Top-Trader Consensus + Binance Crowd Contrarian
    try:
        from okx_consensus_signal import okx_top_trader_consensus, binance_crowd_contrarian
        okx_picks = okx_top_trader_consensus(data=data)
        if okx_picks:
            all_signals.extend(okx_picks)
            print(f"  [okx_top_trader_consensus] -> {len(okx_picks)} consensus pick(s)")
        contrarian_picks = binance_crowd_contrarian(data=data)
        if contrarian_picks:
            all_signals.extend(contrarian_picks)
            print(f"  [binance_crowd_contrarian] -> {len(contrarian_picks)} contrarian pick(s)")
    except Exception as e:
        print(f"  [okx_binance_signals] skipped: {e}")

    # Token Unlock Event Short: Keyrock study, short before cliff unlocks
    try:
        from unlock_event_strategy import token_unlock_event_short
        unlock_signals = token_unlock_event_short(data)
        if unlock_signals:
            all_signals.extend(unlock_signals)
            print(f"  [token_unlock_event_short] -> {len(unlock_signals)} unlock short signal(s)")
    except Exception as e:
        print(f"  [token_unlock_event_short] skipped: {e}")

    # Token Unlock Supply Shock: pressure SHORT + contrarian bounce LONG
    try:
        from token_unlock_signals import token_unlock_pressure, token_unlock_bounce
        pressure_sigs = token_unlock_pressure(data)
        if pressure_sigs:
            all_signals.extend(pressure_sigs)
            print(f"  [token_unlock_pressure] -> {len(pressure_sigs)} pressure short signal(s)")
        bounce_sigs = token_unlock_bounce(data)
        if bounce_sigs:
            all_signals.extend(bounce_sigs)
            print(f"  [token_unlock_bounce] -> {len(bounce_sigs)} bounce long signal(s)")
    except Exception as e:
        print(f"  [token_unlock_signals] skipped: {e}")

    # NOTE: stablecoin_flow_momentum, disposition_effect_contrarian,
    # btc_power_law_deviation, nvm_metcalfe_valuation, eth_gas_fee_reversal,
    # cme_cot_positioning, weekly_oi_change_momentum, miner_capitulation_recovery
    # are registered via strategies.update() and run in the strategy loop above.
    # Direct calls removed to prevent duplicate signal generation.

    # Annotate each signal with its indicator family (for confluence engine)
    try:
        from config import STRATEGY_FAMILIES
        for sig in all_signals:
            sig["family"] = STRATEGY_FAMILIES.get(sig.get("strategy", ""), "unknown")
    except Exception as e:
        print(f"  Warning: Could not annotate signal families: {e}")

    # Heikin Ashi trend filter: adjust confidence based on HA candle direction
    # BUY + bearish HA -> -0.08 conf, BUY + bullish HA -> +0.05 conf (and inverse for SELL)
    if apply_ha_filter is not None:
        try:
            ha_adjusted = 0
            for sig in all_signals:
                old_conf = sig.get("confidence", 0.5)
                apply_ha_filter(sig, data)
                if sig.get("confidence", old_conf) != old_conf:
                    ha_adjusted += 1
            if ha_adjusted:
                print(f"  [heikin_ashi_filter] Adjusted confidence on {ha_adjusted}/{len(all_signals)} signals")
        except Exception as e:
            print(f"  [heikin_ashi_filter] skipped: {e}")

    # HTF (Higher Timeframe) confirmation filter: daily EMA/RSI/BB/MACD/Williams %R
    # Penalizes picks against daily trend (-0.10 conf), boosts aligned picks (+0.05)
    try:
        from htf_confirmation import apply_htf_filter as _apply_htf
        all_signals = _apply_htf(all_signals)
    except Exception as e:
        print(f"  [htf_confirmation] skipped: {e}")

    # ── Non-Crypto Quality Gate: filter equity/forex signals through macro gates ──
    # Previously these gates existed but were never called from scanner.py,
    # meaning 78+ non-crypto picks fired with zero macro filtering.
    if _HAS_NC_QUALITY_GATE and all_signals:
        try:
            from indicators import sma as _sma_fn
        except ImportError:
            _sma_fn = None

        nc_blocked = 0
        nc_adjusted = 0
        nc_killed = 0
        cleaned_signals = []

        for sig in all_signals:
            sym = sig.get("symbol", "")
            strat = sig.get("strategy", "")
            cat = sig.get("category", sig.get("asset_class", "")).upper()

            # Skip crypto signals — they have their own gates
            if cat in ("CRYPTO", "MEME", "") or sym.endswith("USDT") or sym.endswith("-USDT"):
                cleaned_signals.append(sig)
                continue

            # Kill check: halve confidence for killed strategies
            if _nc_is_killed and _nc_is_killed(strat):
                old_conf = sig.get("confidence", 0.5)
                sig["confidence"] = round(old_conf * 0.5, 4)
                sig["_nc_gate"] = "killed_halved"
                nc_killed += 1

            # Equity macro gate (SPY SMA200, crash, trend break)
            if cat in ("EQUITY", "STOCK", "ETF") and _equity_macro_gate:
                gate_ok, gate_reason = _equity_macro_gate(data)
                if not gate_ok:
                    sig["_nc_gate"] = gate_reason
                    sig["confidence"] = round(sig.get("confidence", 0.5) * 0.3, 4)
                    nc_blocked += 1

            # FOREX_HIGH_CONVICTION carve-out (2026-05-24): cta_replicator (n=97, PF 2.38,
            # WR 64.9%) isolated from main FOREX basket. Reclassify to FOREX_HIGH_CONVICTION
            # so it bypasses the zero-allocation kill-switch below.
            if cat == "FOREX" and sig.get("source_system", "").strip().lower() == "cta_replicator":
                sig["asset_class"] = "FOREX_HIGH_CONVICTION"
                sig["category"] = "FOREX_HIGH_CONVICTION"
                cat = "FOREX_HIGH_CONVICTION"
                # Fall through -- normal processing, NOT killed

            # FOREX zero-allocation (2026-05-24): kill-switch per EDGE_CRITERIA_ACTION_PLAN.
            # Both swarm engines agree: FOREX signal is bad, not mis-scaled. Zero-allocate.
            # Verification: SELECT COUNT(*) WHERE asset_class='FOREX' → 0.
            # LIFTED 2026-06-05: forex_carry_g10 backtest meets unlock (PF=1.59, WR=60.4%, n=197)
            if cat == "FOREX" and _ae_config.FOREX_HARD_DISABLE:
                sig["confidence"] = 0.0
                sig["forex_killed"] = True
                nc_blocked += 1  # count in summary log
                continue  # skip — do not append to cleaned_signals

            # Forex macro gate (vol regime)
            if cat == "FOREX" and _forex_macro_gate:
                gate_ok, gate_reason = _forex_macro_gate(data, sym)
                if not gate_ok:
                    sig["_nc_gate"] = gate_reason
                    sig["confidence"] = round(sig.get("confidence", 0.5) * 0.3, 4)
                    nc_blocked += 1

            # VIX confidence adjustment
            if _vix_confidence_adj and cat in ("EQUITY", "STOCK", "ETF", "FUTURES", "COMMODITY"):
                vix_mult = _vix_confidence_adj(data, strat)
                if vix_mult < 1.0:
                    old_conf = sig.get("confidence", 0.5)
                    sig["confidence"] = round(old_conf * vix_mult, 4)
                    sig["_vix_adj"] = vix_mult
                    nc_adjusted += 1

            # Confidence caps per asset class
            if cat == "FOREX" and _forex_conf_cap:
                sig["confidence"] = _forex_conf_cap(sig.get("confidence", 0.5), strat)
            elif cat in ("EQUITY", "STOCK", "ETF") and _equity_conf_cap:
                sig["confidence"] = _equity_conf_cap(sig.get("confidence", 0.5), strat)

            cleaned_signals.append(sig)

        all_signals = cleaned_signals
        if nc_blocked or nc_adjusted or nc_killed:
            print(f"  [nc_quality_gate] blocked={nc_blocked}, vix_adj={nc_adjusted}, killed={nc_killed}")


    # On-chain metrics from CoinMetrics + Mempool
    try:
        from coinmetrics_signal import get_onchain_features
        from mempool_signal import get_mempool_features
        _mempool = get_mempool_features()
        for sig in all_signals:
            sym = sig.get("symbol", "")
            onchain = get_onchain_features(sym)
            sig.setdefault("extra", {}).update(onchain)
            sig.setdefault("extra", {}).update(_mempool)
        print(f"  [onchain+mempool] Enriched {len(all_signals)} signals")
    except Exception as e:
        print(f"  [onchain+mempool] skipped: {e}")

    # Symbol-Specific Strategy Variants: tuned reversal/momentum/contrarian per symbol
    try:
        from symbol_specific_variants import scan_all_symbol_variants
        variant_picks = scan_all_symbol_variants(data)
        if variant_picks:
            all_signals.extend(variant_picks)
            print(f"  [symbol_variants] -> {len(variant_picks)} total signal(s)")
    except Exception as e:
        print(f"  [symbol_variants] skipped: {e}")

    # Contrarian Consensus Flip: quality-weighted cross-system contrarian meta-strategy
    # Reads all_signals + alpha_engine picks + copy_trader_intel picks
    # Fires when 3+ strategies agree AND consensus is low-quality or regime is ranging
    try:
        from contrarian_consensus import generate_contrarian_consensus_picks
        cc_picks = generate_contrarian_consensus_picks(data=data, all_signals=all_signals)
        if cc_picks:
            all_signals.extend(cc_picks)
            try:
                print(f"  [contrarian_consensus_flip] -> {len(cc_picks)} contrarian pick(s)")
            except ValueError:
                pass
    except Exception as e:
        try:
            print(f"  [contrarian_consensus_flip] skipped: {e}")
        except ValueError:
            pass

    # Inverse Strategies: mutation-validated direction flips (winner_pattern_precursor_inverse, etc.)
    # Reads active_picks.json, flips direction of strategies whose inverse was PASS in mutation_backtest
    try:
        from inverse_strategies import run as run_inverse_strategies
        inverse_picks = run_inverse_strategies()
        if inverse_picks:
            all_signals.extend(inverse_picks)
            try:
                print(f"  [inverse_strategies] -> {len(inverse_picks)} mutation-validated inverse pick(s)")
            except ValueError:
                pass
    except Exception as e:
        try:
            print(f"  [inverse_strategies] skipped: {e}")
        except ValueError:
            pass

    # Quan Engine Scalp Hybrid Inverse (SANDBOX, 0.25x sizing) -- per-symbol
    # direction matrix: KEEP_LONG TRX/TAO, INVERT 9 chronic-loss symbols, BLOCK MATIC.
    # See updates/2026-04-17-quan-engine-scalp-mutation-investigation.md (M_HYBRID).
    # Backtest: WR 71.26%, PF 2.890 on 414 trades. Sandbox: 50-trade live probation.
    try:
        from quan_engine_scalp_hybrid_inverse import run as run_quan_hybrid_inverse
        hybrid_picks = run_quan_hybrid_inverse()
        if hybrid_picks:
            all_signals.extend(hybrid_picks)
            try:
                print(f"  [quan_engine_scalp_hybrid_inverse] -> {len(hybrid_picks)} sandbox pick(s)")
            except ValueError:
                pass
    except Exception as e:
        try:
            print(f"  [quan_engine_scalp_hybrid_inverse] skipped: {e}")
        except ValueError:
            pass

    # Final GENERATOR_HARD_KILL sweep -- catch any signals that leaked through
    # DNA mutations, contrarian, inverse, or other secondary generators.
    _pre_kill = len(all_signals)
    all_signals = [s for s in all_signals if s.get("strategy", "") not in GENERATOR_HARD_KILL]
    _killed = _pre_kill - len(all_signals)
    if _killed:
        print(f"  [GENERATOR_HARD_KILL] Removed {_killed} signal(s) from killed strategies")

    # Elite score gate (2026-04-22 edge analysis) — per-asset-class after
    # CRYPTO-calibrated global floor of 70 was found to hard-kill 100% of
    # EQUITY picks (see config.MIN_ELITE_SCORE_BY_CLASS).
    try:
        from alpha_engine.config import min_elite_score_for as _min_elite_for
    except Exception:
        _min_elite_for = lambda _ac: MIN_ELITE_SCORE_FOR_PICKS
    _pre_elite = len(all_signals)
    _kill_counts: dict[str, int] = {}
    _kept = []
    for s in all_signals:
        es = s.get("elite_score")
        if es is None:
            _kept.append(s); continue
        try:
            es_val = float(es)
        except (TypeError, ValueError):
            _kept.append(s); continue
        floor = _min_elite_for(s.get("asset_class") or s.get("category"))
        if 0 < es_val < floor:
            _ac = (s.get("asset_class") or s.get("category") or "UNKNOWN").upper()
            _kill_counts[_ac] = _kill_counts.get(_ac, 0) + 1
            continue
        _kept.append(s)
    all_signals = _kept
    _elite_killed = _pre_elite - len(all_signals)
    if _elite_killed:
        _breakdown = ", ".join(f"{k}={v}" for k, v in sorted(_kill_counts.items()))
        print(f"  [ELITE_SCORE_GATE] Removed {_elite_killed} signal(s) below per-class floor ({_breakdown})")

    # Per-strategy confidence gate (2026-04-22 edge analysis)
    # e.g. ml_crypto_predictor: confidence=0.50 -> worst performer; require >=0.70
    if STRATEGY_MIN_CONFIDENCE:
        _pre_conf = len(all_signals)
        _conf_filtered = []
        for s in all_signals:
            _strat = str(s.get("strategy", "")).strip()
            _min_conf = STRATEGY_MIN_CONFIDENCE.get(_strat)
            if _min_conf is not None:
                _conf = float(s.get("confidence", 0) or 0)
                if _conf < _min_conf:
                    continue  # skip
            _conf_filtered.append(s)
        all_signals = _conf_filtered
        _conf_killed = _pre_conf - len(all_signals)
        if _conf_killed:
            print(f"  [STRATEGY_CONF_GATE] Removed {_conf_killed} signal(s) below per-strategy confidence threshold")

    return all_signals


def enrich_signals_with_ml_features(
    signals: list[dict],
    data: dict[str, pd.DataFrame],
) -> list[dict]:
    """Add hma_slope, volume_ratio, rsi_1h, rsi_4h to each signal dict.

    These fields are consumed by forward_testing/signal_quality_ml.py at
    inference time.  Failures are silently caught so the pipeline is never
    broken by this enrichment step.
    """
    # Cache per-symbol so we don't recompute for every signal on the same symbol
    _cache: dict[str, dict] = {}

    def _compute_features(symbol: str) -> dict:
        if symbol in _cache:
            return _cache[symbol]

        features: dict = {
            "hma_slope": None,
            "volume_ratio": None,
            "rsi_1h": None,
            "rsi_4h": None,
        }

        df = data.get(symbol)
        if df is None or len(df) < 30:
            _cache[symbol] = features
            return features

        close = df["Close"]
        volume = df["Volume"] if "Volume" in df.columns else None

        # --- hma_slope: +1 / -1 / 0 ---
        try:
            slope_series = compute_hma_slope(close, period=21)
            last_slope = slope_series.iloc[-1]
            features["hma_slope"] = int(last_slope) if pd.notna(last_slope) else 0
        except Exception:
            pass

        # --- volume_ratio: current bar vol / 20-bar avg ---
        try:
            if volume is not None and len(volume) >= 20:
                vr_series = compute_volume_ratio(volume, period=20)
                last_vr = vr_series.iloc[-1]
                features["volume_ratio"] = round(float(last_vr), 4) if pd.notna(last_vr) else None
        except Exception:
            pass

        # --- rsi_1h: RSI(14) on the base (1h) timeframe ---
        try:
            rsi_series = compute_rsi(close, period=14)
            last_rsi = rsi_series.iloc[-1]
            features["rsi_1h"] = round(float(last_rsi), 2) if pd.notna(last_rsi) else None
        except Exception:
            pass

        # --- rsi_4h: RSI(14) on 4h resampled data ---
        try:
            if len(df) >= 56:  # need at least 14 * 4 = 56 bars of 1h data
                df_4h = df.resample("4h").agg({
                    "Open": "first",
                    "High": "max",
                    "Low": "min",
                    "Close": "last",
                    "Volume": "sum",
                }).dropna(subset=["Close"])
                if len(df_4h) >= 14:
                    rsi_4h_series = compute_rsi(df_4h["Close"], period=14)
                    last_rsi_4h = rsi_4h_series.iloc[-1]
                    features["rsi_4h"] = round(float(last_rsi_4h), 2) if pd.notna(last_rsi_4h) else None
        except Exception:
            pass

        _cache[symbol] = features
        return features

    enriched_count = 0
    for signal in signals:
        try:
            symbol = signal.get("symbol", "")
            feats = _compute_features(symbol)
            signal["hma_slope"] = feats["hma_slope"]
            signal["volume_ratio"] = feats["volume_ratio"]
            signal["rsi_1h"] = feats["rsi_1h"]
            signal["rsi_4h"] = feats["rsi_4h"]
            enriched_count += 1
        except Exception:
            # Ensure keys exist even on failure
            signal.setdefault("hma_slope", None)
            signal.setdefault("volume_ratio", None)
            signal.setdefault("rsi_1h", None)
            signal.setdefault("rsi_4h", None)

    print(f"  ML feature enrichment: {enriched_count}/{len(signals)} signals enriched "
          f"(hma_slope, volume_ratio, rsi_1h, rsi_4h)")
    return signals


def rank_and_filter_signals(signals: list[dict], ranker: MLSignalRanker,
                            db: SQLiteStore,
                            market_data: dict[str, pd.DataFrame] | None = None,
                            ) -> list[dict]:
    """Rank signals with ML and apply filters.

    Includes falling-knife protection: blocks crypto/meme LONG signals when
    price is >25% below the 200-day SMA (structural bear market, not a dip).
    """
    if not signals:
        return []

    # -- Falling knife filter (universal) ---------------------------------
    # Prevents opening longs in structural bear markets.
    # Evidence: BTC/ETH/SOL longs went 1W/14L during F&G=8, BTC -34% from 200 SMA.
    FALLING_KNIFE_THRESHOLD = 0.25  # 25% below 200-day SMA
    FALLING_KNIFE_CATEGORIES = {"crypto", "meme"}
    _sma_cache: dict[str, float | None] = {}

    def _get_200d_sma(symbol: str) -> float | None:
        """Get 200-day SMA from market_data if available."""
        if symbol in _sma_cache:
            return _sma_cache[symbol]
        sma = None
        if market_data and symbol in market_data:
            df = market_data[symbol]
            if len(df) >= 200:
                sma = float(df["Close"].iloc[-200:].mean())
        _sma_cache[symbol] = sma
        return sma

    pre_knife = len(signals)
    kept = []
    for s in signals:
        cat = s.get("category", "stock")
        sig_type = s.get("signal_type", "BUY")
        if cat in FALLING_KNIFE_CATEGORIES and sig_type == "BUY":
            sma = _get_200d_sma(s["symbol"])
            if sma and sma > 0:
                price = s.get("entry_price", 0)
                pct_below = (sma - price) / sma
                if pct_below > FALLING_KNIFE_THRESHOLD:
                    s["_rejected"] = True
                    s["_reject_reason"] = (
                        f"Falling knife: {s['symbol']} {pct_below:.0%} below "
                        f"200-day SMA (${sma:,.0f}). Structural bear, not a dip."
                    )
                    print(f"  [FALLING KNIFE] {s['_reject_reason']}")
                    continue
        kept.append(s)
    signals = kept
    if pre_knife > len(signals):
        print(f"  Falling knife filter removed {pre_knife - len(signals)} signal(s)")

    # -- Forex conflict resolution -----------------------------------------
    # Prevents same forex pair from having both BUY and SELL in the same batch.
    # Root cause: 5 SELL + 1 BUY on AUDJPY was promoted simultaneously.
    # Fix: if >70% of signals agree on direction → keep majority; else skip pair.
    from collections import defaultdict as _dd
    _forex_by_sym = _dd(lambda: {"BUY": [], "SELL": []})
    _non_forex = []
    for s in signals:
        if s.get("category") == "forex":
            sig_type = s.get("signal_type", "BUY")
            _forex_by_sym[s["symbol"]][sig_type].append(s)
        else:
            _non_forex.append(s)

    _forex_kept = []
    for sym, dirs in _forex_by_sym.items():
        buys = dirs["BUY"]
        sells = dirs["SELL"]
        total = len(buys) + len(sells)
        if total == 0:
            continue
        if buys and sells:
            # Conflicting signals -- apply 70% majority rule
            buy_pct = len(buys) / total
            if buy_pct > 0.70:
                _forex_kept.extend(buys)
                print(f"  [FX CONFLICT] {sym}: {len(buys)} BUY vs {len(sells)} SELL → keeping BUY ({buy_pct:.0%})")
            elif buy_pct < 0.30:
                _forex_kept.extend(sells)
                print(f"  [FX CONFLICT] {sym}: {len(buys)} BUY vs {len(sells)} SELL → keeping SELL ({1-buy_pct:.0%})")
            else:
                print(f"  [FX CONFLICT] {sym}: {len(buys)} BUY vs {len(sells)} SELL → SKIPPING (no clear majority)")
        else:
            _forex_kept.extend(buys + sells)

    pre_conflict = len(signals)
    signals = _non_forex + _forex_kept
    if pre_conflict > len(signals):
        print(f"  Forex conflict resolution removed {pre_conflict - len(signals)} signal(s)")

    # -- Risk:Reward gate -------------------------------------------------
    # Reject signals with RR < 1.0 (risk exceeds reward -- negative expectancy).
    # Boost confidence +10% for signals with RR >= 2.0 (strong reward profile).
    # Category-aware R:R thresholds: forex has tighter ranges than crypto
    MIN_RR_BY_CATEGORY = {
        "crypto": 1.0,     # Crypto: block only negative expectancy
        "forex": 0.8,      # Forex: tighter R:R is normal (1.0-1.5 typical)
        "equity": 1.0,
        "commodity": 1.0,
        "default": 1.0,
    }
    HIGH_RR_BOOST_THRESHOLD = 2.0
    HIGH_RR_BOOST_PCT = 0.10  # 10% confidence boost
    pre_rr = len(signals)
    rr_kept = []
    for s in signals:
        rr = s.get("risk_reward", 0)
        # Compute RR if not already set
        if rr == 0 and s.get("entry_price") and s.get("take_profit") and s.get("stop_loss"):
            ep = s["entry_price"]
            tp = s["take_profit"]
            sl = s["stop_loss"]
            tp_dist = abs(tp - ep)
            sl_dist = abs(sl - ep)
            if sl_dist > 0:
                rr = round(tp_dist / sl_dist, 2)
                s["risk_reward"] = rr
        _cat = (s.get("category") or "crypto").lower()
        _min_rr = MIN_RR_BY_CATEGORY.get(_cat, MIN_RR_BY_CATEGORY["default"])
        if rr < _min_rr:
            print(f"  [RR GATE] REJECTED {s.get('symbol', '?')} {s.get('strategy', '?')}: "
                  f"R:R={rr:.2f} < {_min_rr} ({_cat}, risk exceeds reward)")
            continue
        if rr >= HIGH_RR_BOOST_THRESHOLD:
            old_conf = s.get("confidence", 0.5)
            new_conf = round(min(0.95, old_conf * (1 + HIGH_RR_BOOST_PCT)), 3)
            s["confidence"] = new_conf
            s["rr_boosted"] = True
        rr_kept.append(s)
    signals = rr_kept
    rr_removed = pre_rr - len(signals)
    if rr_removed > 0:
        print(f"  RR gate removed {rr_removed} signal(s) (category-aware thresholds)")
    rr_boosted_count = sum(1 for s in signals if s.get("rr_boosted"))
    if rr_boosted_count > 0:
        print(f"  RR gate boosted {rr_boosted_count} signal(s) with R:R >= {HIGH_RR_BOOST_THRESHOLD} (+{HIGH_RR_BOOST_PCT*100:.0f}% confidence)")

    # Count convergence: how many strategies fired on the same symbol
    symbol_counts: dict[str, int] = {}
    # Also track symbol+direction for confluence detection
    symbol_dir_strategies: dict[str, list[str]] = {}
    for s in signals:
        sym = s["symbol"]
        symbol_counts[sym] = symbol_counts.get(sym, 0) + 1
        direction = s.get("direction", s.get("signal_type", "BUY")).upper()
        if direction in ("BUY", "LONG"):
            direction = "LONG"
        elif direction in ("SELL", "SHORT"):
            direction = "SHORT"
        key = f"{sym}::{direction}"
        symbol_dir_strategies.setdefault(key, []).append(s.get("strategy", ""))

    # Populate confluence_strategies for ALL signals (not behind feature flag)
    for s in signals:
        sym = s["symbol"]
        direction = s.get("direction", s.get("signal_type", "BUY")).upper()
        if direction in ("BUY", "LONG"):
            direction = "LONG"
        elif direction in ("SELL", "SHORT"):
            direction = "SHORT"
        key = f"{sym}::{direction}"
        co_strategies = [st for st in symbol_dir_strategies.get(key, []) if st != s.get("strategy", "")]
        if co_strategies:
            s["confluence_strategies"] = co_strategies
            s["confluence_score"] = 1.0 + len(co_strategies) * 0.15  # boost per co-strategy
            s["confluence_reason"] = f"{len(co_strategies)} other strategies agree: {', '.join(co_strategies[:5])}"

    # -- OBI injection: populate orderbook_imbalance before ML scoring -----
    # Fetches live Binance L2 depth for all unique symbols in one batch call.
    # In shadow mode (OBI_SHADOW_MODE=True), scores are logged but NOT injected
    # into signals -- the ML ranker sees default 0 until shadow validation passes.
    if get_orderbook_scores_batch is not None:
        try:
            unique_symbols = list(symbol_counts.keys())
            obi_scores = get_orderbook_scores_batch(unique_symbols, dry_run=OBI_SHADOW_MODE)
            obi_count = len(obi_scores)
            if obi_count > 0:
                print(f"  OBI fetched for {obi_count}/{len(unique_symbols)} symbols"
                      f" (shadow={OBI_SHADOW_MODE})")
                if not OBI_SHADOW_MODE:
                    # Live mode: inject OBI into each signal for ML scoring
                    for s in signals:
                        sym = s["symbol"]
                        if sym in obi_scores:
                            s["orderbook_imbalance"] = obi_scores[sym]
                else:
                    # Shadow mode: log OBI values but don't inject (ML sees default 0)
                    for s in signals:
                        sym = s["symbol"]
                        if sym in obi_scores:
                            s["_obi_shadow"] = obi_scores[sym]
            else:
                print("  OBI: no scores returned (API may be unavailable)")
        except Exception as e:
            print(f"  OBI injection failed (non-fatal): {e}")

    # -- OBI velocity injection: delta-5, delta-15, acceleration ----------
    # Computes rate-of-change of OBI from historical snapshots (obi_history.json).
    # EFMA 2025: OBI velocity is a stronger leading indicator than absolute OBI.
    # obi_scores may not be defined if get_orderbook_scores_batch is None or failed
    _obi_scores_for_vel = locals().get("obi_scores") or {}
    if compute_obi_velocity_batch is not None and _obi_scores_for_vel:
        try:
            if len(_obi_scores_for_vel) > 0:
                obi_vel = compute_obi_velocity_batch(_obi_scores_for_vel)
                vel_count = len(obi_vel)
                if vel_count > 0:
                    print(f"  OBI velocity computed for {vel_count} symbols")
                    if not OBI_SHADOW_MODE:
                        for s in signals:
                            sym = s["symbol"]
                            if sym in obi_vel:
                                s["obi_delta_5"] = obi_vel[sym]["obi_delta_5"]
                                s["obi_delta_15"] = obi_vel[sym]["obi_delta_15"]
                                s["obi_acceleration"] = obi_vel[sym]["obi_acceleration"]
                    else:
                        for s in signals:
                            sym = s["symbol"]
                            if sym in obi_vel:
                                s["_obi_vel_shadow"] = obi_vel[sym]
        except Exception as e:
            print(f"  OBI velocity injection failed (non-fatal): {e}")

    # -- Derivatives injection: OI change, funding rate, long/short ratio ----
    if get_derivatives_batch is not None:
        try:
            unique_symbols = list(symbol_counts.keys())
            crypto_syms = [s for s in unique_symbols if s.endswith("USDT")]
            if crypto_syms:
                deriv_data = get_derivatives_batch(crypto_syms)
                deriv_count = len(deriv_data)
                if deriv_count > 0:
                    print(f"  Derivatives data for {deriv_count}/{len(crypto_syms)} symbols")
                    for s in signals:
                        sym = s["symbol"]
                        if sym in deriv_data:
                            d = deriv_data[sym]
                            s["oi_change_24h"] = d.get("oi_change_24h", 0)
                            s["funding_rate"] = d.get("funding_rate", 0)
                            s["long_short_ratio"] = d.get("long_short_ratio", 1.0)
        except Exception as e:
            print(f"  Derivatives injection failed (non-fatal): {e}")

    # -- DefiLlama TVL composite signal (macro capital flow) ----
    if get_defi_composite_signal is not None:
        try:
            defi_signal = get_defi_composite_signal()
            defi_score = defi_signal.get("composite_score", 0)
            if abs(defi_score) > 0.01:
                print(f"  DefiLlama composite: {defi_score:+.3f} ({defi_signal.get('signal', 'N/A')})")
                for s in signals:
                    s["defi_tvl_score"] = defi_score
        except Exception as e:
            print(f"  DefiLlama injection failed (non-fatal): {e}")

    # -- Finnhub economic event risk (pre-FOMC/CPI positioning) ----
    try:
        from finnhub_events import get_event_signal
        event_sig = get_event_signal()
        event_risk = event_sig.get("event_risk", "LOW")
        if event_risk != "LOW":
            print(f"  Finnhub events: {event_risk} -- {event_sig.get('next_event', '?')} "
                  f"in {event_sig.get('hours_until', '?')}h")
            for s in signals:
                s["event_risk"] = event_risk
                s["next_event"] = event_sig.get("next_event", "")
                s["event_hours"] = event_sig.get("hours_until", 999)
    except Exception as e:
        print(f"  Finnhub events skipped (non-fatal): {e}")

    # -- Google Trends retail sentiment (free, no API key) ----
    try:
        from google_trends_signal import get_crypto_sentiment
        gt_sig = get_crypto_sentiment()
        gt_signal = gt_sig.get("signal", "NEUTRAL")
        if gt_signal not in ("NEUTRAL", "UNAVAILABLE"):
            print(f"  Google Trends: {gt_signal} -- FOMO ratio {gt_sig.get('fomo_ratio', 0)}")
            for s in signals:
                s["retail_sentiment"] = gt_signal
                s["fomo_ratio"] = gt_sig.get("fomo_ratio", 1.0)
    except Exception as e:
        print(f"  Google Trends skipped (non-fatal): {e}")

    # -- FRED macro liquidity (Hayes net liquidity index) ----
    try:
        from fred_liquidity import get_macro_signal
        macro = get_macro_signal()
        macro_sig = macro.get("macro_signal", "NEUTRAL")
        if macro_sig != "NEUTRAL":
            factors = ", ".join(macro.get("factors", []))
            print(f"  FRED macro: {macro_sig} -- {factors}")
            for s in signals:
                s["macro_signal"] = macro_sig
                s["macro_score"] = macro.get("macro_score", 0)
    except Exception as e:
        print(f"  FRED macro skipped (non-fatal): {e}")

    # -- VPIN injection: informed trading probability before ML scoring ----
    if get_vpin_scores_batch is not None:
        try:
            crypto_syms = [s for s in symbol_counts.keys() if s.endswith("-USD")]
            if crypto_syms:
                vpin_scores = get_vpin_scores_batch(crypto_syms[:10])  # Top 10 to limit API calls
                vpin_count = len(vpin_scores)
                if vpin_count > 0:
                    print(f"  VPIN fetched for {vpin_count}/{len(crypto_syms)} symbols")
                    for s in signals:
                        sym = s["symbol"]
                        if sym in vpin_scores:
                            vd = vpin_scores[sym]
                            s["vpin"] = vd["vpin"]
                            s["ofi"] = vd.get("ofi", 0)
                            s["ofi_abs"] = vd.get("ofi_abs", 0)
                            s["vpin_signal"] = vd["signal"]
                            s["vpin_buy_pct"] = vd["buy_pct"]
                else:
                    print("  VPIN: no scores returned (API may be unavailable)")
        except Exception as e:
            print(f"  VPIN injection failed (non-fatal): {e}")

    # -- LunarCrush Galaxy Score injection: social sentiment before ML scoring ----
    if get_lunarcrush_scores_batch is not None:
        try:
            crypto_syms = [s for s in symbol_counts.keys() if s.endswith("-USD")]
            if crypto_syms:
                lc_scores = get_lunarcrush_scores_batch(crypto_syms[:10])  # Top 10, rate-limited
                lc_count = len(lc_scores)
                if lc_count > 0:
                    print(f"  LunarCrush fetched for {lc_count}/{len(crypto_syms)} symbols")
                    for s in signals:
                        sym = s["symbol"]
                        if sym in lc_scores:
                            lcd = lc_scores[sym]
                            s["galaxy_score"] = lcd["galaxy_score"]
                            s["alt_rank"] = lcd["alt_rank"]
                            s["social_volume"] = lcd["social_volume"]
                            s["social_sentiment"] = lcd["sentiment"]
                else:
                    print("  LunarCrush: no scores returned (API may be unavailable)")
        except Exception as e:
            print(f"  LunarCrush injection failed (non-fatal): {e}")

    # Score each signal
    for signal in signals:
        strategy_stats = db.compute_strategy_stats(signal.get("strategy", "unknown"))
        convergence = symbol_counts.get(signal["symbol"], 1) - 1
        ml_score = ranker.score_signal(signal, strategy_stats, convergence)
        signal["ml_score"] = round(ml_score, 3)
        signal["convergence"] = convergence

        # FWLS: context-weighted blend of ml_score + confidence (optional boost)
        if _fwls_blend is not None:
            _conf_raw = float(signal.get("confidence", 0.5) or 0.5)
            _fwls_out = _fwls_blend(signal, ml_score, _conf_raw)
            if abs(_fwls_out - ml_score) > 0.001:
                signal["ml_score_pre_fwls"] = signal["ml_score"]
                signal["ml_score"] = round(_fwls_out, 3)

        # Conformal prediction: attach interval width as confidence metric
        if _conformal_sizer is not None:
            _cp_diag = _conformal_sizer.get_diagnostics(ml_score)
            signal["conformal_width"] = _cp_diag["conformal_width"]
            signal["conformal_multiplier"] = _cp_diag["conformal_multiplier"]
            signal["conformal_calibrated"] = _cp_diag["conformal_calibrated"]

        # Forward-test gate annotation -- mark signal before filtering
        gate_pass, gate_reason, tc, wr = passes_forward_gate(
            signal.get("strategy", ""), strategy_stats)
        signal["forward_validated"] = gate_pass
        signal["forward_status"] = gate_reason
        signal["forward_trades"] = tc
        signal["forward_wr"] = round(wr, 4)

        # Regime gate: upgraded from 10% penalty to tiered enforcement
        # - Incompatible regime: 30% penalty (was 10%) -- still allows exceptional signals
        # - Unknown regime: no penalty (insufficient data to judge)
        # Based on: Kimi/Grok feedback -- regime mismatch is the #1 cause of false signals
        if not signal.get("regime_compatible", True):
            signal["ml_score_pre_regime"] = signal["ml_score"]
            signal["ml_score"] = round(signal["ml_score"] * 0.70, 3)
            signal["regime_penalty"] = 0.30

        # Volume confirmation filter: require above-average volume for breakout signals
        # Mean reversion strategies exempt (they work on low-volume exhaustion)
        _BREAKOUT_KEYWORDS = {"breakout", "squeeze", "momentum", "trend", "ema_stack"}
        strategy_name = signal.get("strategy", "")
        is_breakout_type = any(kw in strategy_name for kw in _BREAKOUT_KEYWORDS)
        if is_breakout_type:
            vol_ratio = signal.get("volume_ratio") or signal.get("extra", {}).get("volume_ratio")
            if vol_ratio is not None and vol_ratio < 1.0:
                signal["ml_score_pre_volume"] = signal["ml_score"]
                signal["ml_score"] = round(signal["ml_score"] * 0.80, 3)
                signal["volume_warning"] = f"Low volume ({vol_ratio:.1f}x avg) for breakout strategy"

    # LOW_CONFIDENCE_STRATEGIES penalty: known 0% WR strategies get 0.4x ml_score
    if _HAS_CRYPTO_RISK_GATES and _LOW_CONFIDENCE_STRATEGIES:
        _lc_penalized = 0
        for s in signals:
            if s.get("strategy", "") in _LOW_CONFIDENCE_STRATEGIES:
                s["ml_score_pre_lowconf"] = s.get("ml_score", 0)
                s["ml_score"] = round(s.get("ml_score", 0) * 0.40, 3)
                s["low_confidence_strategy"] = True
                s["low_confidence_reason"] = _LOW_CONFIDENCE_STRATEGIES[s["strategy"]]
                _lc_penalized += 1
        if _lc_penalized:
            print(f"  [FILTER] Low-confidence strategy penalty: {_lc_penalized} signals penalized (0.4x)")

    # Repeat-loser cooldown: penalize symbols with 2+ recent SL hits across ALL strategies
    try:
        from datetime import datetime, timezone, timedelta
        cooldown_hours = 72
        closed_path = os.path.join(os.path.dirname(__file__), "data", "closed_picks.json")
        if os.path.exists(closed_path):
            import json as _json
            with open(closed_path) as _f:
                _closed = _json.load(_f)
            cutoff = datetime.now(timezone.utc) - timedelta(hours=cooldown_hours)
            recent_sl: dict[str, int] = {}
            for cp in _closed:
                if cp.get("status") in ("SL_HIT", "LOST"):
                    ts = cp.get("timestamp") or cp.get("created_at") or ""
                    try:
                        if ts and datetime.fromisoformat(ts.replace("Z", "+00:00")) > cutoff:
                            sym = cp.get("symbol", "")
                            recent_sl[sym] = recent_sl.get(sym, 0) + 1
                    except (ValueError, TypeError):
                        pass
            repeat_losers = {sym for sym, count in recent_sl.items() if count >= 2}
            if repeat_losers:
                penalized = 0
                for s in signals:
                    if s.get("symbol", "") in repeat_losers:
                        s["ml_score"] = round(s.get("ml_score", 0) * 0.50, 3)
                        s["repeat_loser_penalty"] = True
                        penalized += 1
                if penalized:
                    print(f"  [FILTER] Repeat-loser cooldown: {penalized} signals penalized "
                          f"({len(repeat_losers)} symbols with 2+ SL in {cooldown_hours}h)")
    except Exception as e:
        print(f"  [WARN] Repeat-loser check failed (non-fatal): {e}")

    # -- Data-driven filters (calibrated from 273-trade PnL audit 2026-03-16) --

    # -- Confidence floor gate (Mar 17 2026 root cause fix) --------------
    # Low-confidence signals waste capital slots. Tiered by category/direction:
    #   crypto BUY:  >= 0.60 (slightly permissive -- most volume)
    #   crypto SELL: >= 0.80 (strict -- SHORT WR is 20%)
    #   meme:        >= 0.80 BUY only (no meme shorts at all)
    #   forex:       blocked entirely (handled by auto_tuner HARD_DISABLED)
    #   default:     >= 0.65
    _CONF_FLOOR = {
        "crypto_BUY": 0.60,
        "crypto_SELL": 0.80,
        "meme_BUY": 0.80,
        "meme_SELL": 999.0,   # Block all meme shorts
        "forex_BUY": 0.50,    # Forex strategies naturally produce 0.55-0.60 conf
        "forex_SELL": 0.50,   # Lower floor — forex is less volatile, needs room
        "equity_BUY": 0.50,
        "equity_SELL": 0.50,
        "commodity_BUY": 0.55,
        "commodity_SELL": 0.55,
        "futures_BUY": 0.55,
        "futures_SELL": 0.55,
        "bond_BUY": 0.50,
        "bond_SELL": 0.50,
        "default": 0.65,
    }
    conf_filtered = []
    conf_blocked = 0
    for s in signals:
        _cat = str(s.get("category", "crypto")).lower()
        _dir = s.get("direction", s.get("signal_type", "BUY")).upper()
        if _dir in ("SHORT", "SELL"):
            _dir = "SELL"
        else:
            _dir = "BUY"
        _conf_key = f"{_cat}_{_dir}"
        _min_conf = _CONF_FLOOR.get(_conf_key, _CONF_FLOOR["default"])
        _sig_conf = s.get("confidence", 0) or 0
        if isinstance(_sig_conf, str):
            try:
                _sig_conf = float(_sig_conf)
            except (ValueError, TypeError):
                _sig_conf = 0
        if _sig_conf >= _min_conf:
            conf_filtered.append(s)
        else:
            conf_blocked += 1
            print(f"  [CONF FLOOR] BLOCK {s.get('symbol', '?')} {s.get('strategy', '?')}: "
                  f"confidence={_sig_conf:.2f} < {_min_conf:.2f} "
                  f"(floor for {_cat}/{_dir})")
    if conf_blocked:
        print(f"  [CONF FLOOR] Blocked {conf_blocked} signals below confidence floor")
    signals = conf_filtered

    # SHORT direction gate: SHORT trades have 20.6% WR vs 69.4% LONG.
    # Require ml_score >= 0.90 for shorts (vs 0.65 for longs).
    SHORT_ML_THRESHOLD = 0.90
    short_blocked = 0
    for s in signals:
        direction = s.get("direction", s.get("signal_type", "")).upper()
        if direction in ("SHORT", "SELL") and s.get("ml_score", 0) < SHORT_ML_THRESHOLD:
            s["ml_score_pre_short_gate"] = s.get("ml_score", 0)
            s["ml_score"] = 0.0  # will be filtered by MIN_ML_SCORE below
            s["short_gate_blocked"] = True
            short_blocked += 1
    if short_blocked:
        print(f"  [FILTER] SHORT gate: blocked {short_blocked} shorts with ml_score < {SHORT_ML_THRESHOLD}")

    # Optional bucket calibration (isotonic export → data/scanner_calibration_config.json)
    try:
        from scanner_score_calibration import apply_optional_scanner_calibration

        _cal_n = apply_optional_scanner_calibration(signals)
        if _cal_n:
            print(
                f"  [SCANNER_CAL] Adjusted ml_score on {_cal_n} signals "
                f"(scanner_calibration_config.json)"
            )
    except Exception:
        pass

    # NOTE: Overconfidence penalty REMOVED (2026-03-18).
    # Gate cost analysis showed conf > 0.85 picks actually WIN in closed picks data.
    # The 38.9% WR stat was from a small, biased sample. Shadow-tracking instead.
    overconf_count = sum(1 for s in signals if float(s.get("confidence", 0) or 0) > 0.85)
    if overconf_count:
        print(f"  [INFO] High-confidence signals: {overconf_count} picks with conf > 0.85 (no penalty applied)")

    # Sort by ML score (highest first)
    signals.sort(key=lambda x: x.get("ml_score", 0), reverse=True)

    # -- Regime-conditional ML thresholds ----------------------------------
    # Flat 0.65 gate was letting low-quality signals through in high-vol markets
    # where SL hit rate is highest.  Now we require higher confidence when
    # volatility is elevated (20-day rolling std of returns).
    #
    # Thresholds calibrated from 352-trade audit:
    #   high-vol  (vol > 0.04 or regime=trending+bearish): 0.78  -- only cream-of-crop
    #   medium    (0.02 < vol <= 0.04 or regime=transitional): 0.65  -- status quo
    #   low-vol   (vol <= 0.02 or regime=ranging):            0.58  -- more permissive
    #   unknown   (no regime data):                           0.65  -- safe default
    #
    # Impact: reduces SL hit rate in dangerous markets while opening more
    # opportunities in calm, range-bound conditions.

    # Thresholds FURTHER lowered (2026-03-18) -- gate cost analysis showed
    # ML precision@20 = 0.40 (worse than random). Filtering on a broken model
    # costs alpha. Lowered to 0.30-0.40 until precision > 0.50.
    _REGIME_ML_THRESHOLDS = {
        "high_vol": 0.20,   # Lowered from 0.40 -- ML model overfitting (AUC 0.99), let signals through
        "medium":   0.15,   # Lowered from 0.35
        "low_vol":  0.10,   # Lowered from 0.30
        "unknown":  0.15,   # Lowered from 0.35
    }

    def _get_regime_ml_threshold(signal: dict) -> tuple[float, str]:
        """Return (threshold, regime_label) for a signal based on its market regime."""
        ri = signal.get("market_regime") or {}
        vol = ri.get("volatility")
        regime = ri.get("regime", "unknown")
        trend_dir = ri.get("trend_direction")

        # If volatility data is available, use it as primary classifier
        if vol is not None:
            if vol > 0.04:
                return _REGIME_ML_THRESHOLDS["high_vol"], "high_vol"
            elif vol <= 0.02:
                return _REGIME_ML_THRESHOLDS["low_vol"], "low_vol"
            else:
                return _REGIME_ML_THRESHOLDS["medium"], "medium"

        # Fallback to regime string when volatility is missing
        if regime == "trending" and trend_dir == "bearish":
            return _REGIME_ML_THRESHOLDS["high_vol"], "high_vol"
        elif regime == "ranging":
            return _REGIME_ML_THRESHOLDS["low_vol"], "low_vol"
        elif regime == "transitional":
            return _REGIME_ML_THRESHOLDS["medium"], "medium"

        return _REGIME_ML_THRESHOLDS["unknown"], "unknown"

    filtered = []
    regime_filter_counts: dict[str, int] = {"passed": 0, "blocked": 0}
    regime_threshold_used: dict[str, int] = {}
    for s in signals:
        threshold, regime_label = _get_regime_ml_threshold(s)
        s["ml_regime_threshold"] = threshold
        s["ml_regime_label"] = regime_label
        regime_threshold_used[regime_label] = regime_threshold_used.get(regime_label, 0) + 1
        if s.get("ml_score", 0) >= threshold:
            filtered.append(s)
            regime_filter_counts["passed"] += 1
        else:
            regime_filter_counts["blocked"] += 1

    if regime_filter_counts["blocked"] > 0:
        breakdown = ", ".join(f"{k}={v}" for k, v in sorted(regime_threshold_used.items()))
        print(f"  [REGIME ML GATE] Passed {regime_filter_counts['passed']}, "
              f"blocked {regime_filter_counts['blocked']} "
              f"(thresholds: high_vol={_REGIME_ML_THRESHOLDS['high_vol']}, "
              f"medium={_REGIME_ML_THRESHOLDS['medium']}, "
              f"low_vol={_REGIME_ML_THRESHOLDS['low_vol']}) "
              f"[{breakdown}]")

    # Correlation filter: prevent >3 picks on same symbol (diversification)
    # Skip if open positions overlap too heavily on one asset
    symbol_pick_count: dict[str, int] = {}
    diversified = []
    MAX_SAME_SYMBOL = 3
    for s in filtered:
        sym = s.get("symbol", "")
        count = symbol_pick_count.get(sym, 0)
        if count >= MAX_SAME_SYMBOL:
            s["skipped_reason"] = f"Correlation cap: already {count} picks on {sym}"
            continue
        symbol_pick_count[sym] = count + 1
        diversified.append(s)

    skipped_corr = len(filtered) - len(diversified)
    if skipped_corr > 0:
        print(f"  [FILTER] Skipped {skipped_corr} signals (correlation/diversification cap)")

    # -- Execution cost gate: block signals where friction eats the edge ----
    try:
        from execution_cost import compute_net_edge
        cost_passed = []
        cost_blocked = 0
        for s in diversified:
            result = compute_net_edge(s)
            net_edge = result.get("net_edge_bps", 0)
            profitable = result.get("is_profitable", True)
            s["net_edge_bps"] = net_edge
            sym = s.get("symbol", "?")
            strat = s.get("strategy", "?")
            if not profitable:
                cost_blocked += 1
                print(f"  [COST GATE] {sym} {strat} net_edge={net_edge:.0f}bps -- BLOCK")
                continue
            print(f"  [COST GATE] {sym} {strat} net_edge={net_edge:.0f}bps -- PASS")
            cost_passed.append(s)
        if cost_blocked > 0:
            print(f"  Execution cost gate blocked {cost_blocked} signal(s)")
        diversified = cost_passed
    except ImportError:
        print("  [WARN] execution_cost module not available -- cost gate skipped")
    except Exception as e:
        print(f"  [WARN] Execution cost gate failed (non-fatal): {e}")

    # -----------------------------------------------------------------------
    # EMERGENCY REGIME GATE: Suppress low-score crypto LONGs in bearish regime
    # Dashboard showed "68% of LONGs are losing" but scanner kept generating them.
    # This gate reads hmm_regime.json + feargreed_cache.json DIRECTLY (context
    # is not passed to rank_and_filter_signals) and suppresses crypto/meme LONGs
    # with elite_score < 70 when regime is bearish or F&G < 25 (Extreme Fear).
    # -----------------------------------------------------------------------
    try:
        _hmm_path = DATA_DIR / "hmm_regime.json"
        _fg_path = DATA_DIR / "feargreed_cache.json"

        _hmm_data = {}
        _fg_value = 50
        if _hmm_path.exists():
            with open(_hmm_path) as _f:
                _hmm_data = json.load(_f)
            print(f"  [REGIME GATE] hmm_regime.json loaded: aggregate={_hmm_data.get('aggregate', {})}")
        else:
            print("  [REGIME GATE] hmm_regime.json NOT FOUND -- skipping regime gate")

        if _fg_path.exists():
            with open(_fg_path) as _f:
                _fg_data_raw = json.load(_f)
            _fg_value = float(_fg_data_raw.get("current", 50))
            print(f"  [REGIME GATE] feargreed_cache.json loaded: F&G={_fg_value} ({_fg_data_raw.get('classification', '?')})")
        else:
            print("  [REGIME GATE] feargreed_cache.json NOT FOUND -- using default F&G=50")

        _agg_regime = str(_hmm_data.get("aggregate", {}).get("market_regime", "")).lower()
        _crypto_regime = str(_hmm_data.get("aggregate", {}).get("crypto_regime", "")).lower()
        _overview = _hmm_data.get("market_overview", {})
        _bear_count = _overview.get("bear_count", 0)
        _bull_count = _overview.get("bull_count", 0)
        _total = _overview.get("total_scanned", 1)

        _is_bearish = (
            _agg_regime in ("bear", "bearish", "crash", "crisis")
            or _crypto_regime in ("bear", "bearish", "crash", "crisis")
            or _fg_value < 25
            or (_bear_count > 0 and _bear_count / max(_total, 1) > 0.50)
        )

        if _is_bearish:
            _before_regime = len(diversified)
            _regime_kept = []
            for _s in diversified:
                _dir = str(_s.get("direction", _s.get("signal_type", ""))).upper()
                _cat = str(_s.get("category", "")).lower()
                _score = float(_s.get("elite_score", _s.get("ml_score", _s.get("score", 0))) or 0)
                if (_dir in ("LONG", "BUY")
                        and _cat in ("crypto", "meme")
                        and _score < 70):
                    print(f"  [REGIME GATE] SUPPRESSED {_s.get('symbol','?')} {_s.get('strategy','?')} "
                          f"dir={_dir} score={_score:.1f} (bearish regime, F&G={_fg_value}, "
                          f"agg_regime={_agg_regime})")
                    continue
                _regime_kept.append(_s)
            _suppressed = _before_regime - len(_regime_kept)
            if _suppressed > 0:
                print(f"  [REGIME GATE] BEARISH regime detected (regime={_agg_regime}, "
                      f"F&G={_fg_value}, bears={_bear_count}/{_total}): "
                      f"suppressed {_suppressed} low-score crypto/meme LONGs (kept score>=70 only)")
            else:
                print(f"  [REGIME GATE] BEARISH regime but no low-score crypto LONGs to suppress")
            diversified = _regime_kept
        else:
            print(f"  [REGIME GATE] Regime not bearish (regime={_agg_regime}, F&G={_fg_value}) -- no suppression")
    except Exception as _e:
        print(f"  [REGIME GATE] Failed (non-fatal, no picks suppressed): {_e}")

    return diversified


def compute_position_size(
    entry_price: float,
    stop_loss: float,
    category: str,
    capital: float = STARTING_CAPITAL,
    current_exposure: float = 0.0,
) -> float:
    """
    Risk-based position sizing: risk MAX_RISK_PER_TRADE per trade.

    Position size = risk_amount / distance_to_stop
    Capped at MAX_ALLOCATION_PER_PICK and respects MAX_TOTAL_EXPOSURE.

    Returns dollar allocation for this pick.
    """
    if entry_price <= 0 or stop_loss <= 0:
        return min(capital * MAX_ALLOCATION_PER_PICK, capital * (MAX_TOTAL_EXPOSURE - current_exposure / capital))

    risk_amount = capital * MAX_RISK_PER_TRADE  # e.g. 2% of $10K = $200

    # Distance to stop as fraction of entry
    stop_distance = abs(entry_price - stop_loss) / entry_price
    if stop_distance <= 0:
        stop_distance = 0.05  # fallback 5%

    # Position size = risk / stop_distance
    position = risk_amount / stop_distance

    # Cap at MAX_ALLOCATION_PER_PICK (e.g. 15% of capital)
    max_alloc = capital * MAX_ALLOCATION_PER_PICK
    position = min(position, max_alloc)

    # Respect MAX_TOTAL_EXPOSURE
    remaining_exposure = max(capital * MAX_TOTAL_EXPOSURE - current_exposure, 0)
    position = min(position, remaining_exposure)

    return round(position, 2)


def open_new_picks(signals: list[dict], db: SQLiteStore,
                   market_data: dict[str, pd.DataFrame] | None = None,
                   context: dict | None = None) -> list[str]:
    """Open new picks from top-ranked signals, respecting limits and risk sizing."""
    opened = []
    total_open = db.count_open_picks()

    # Track current exposure for position sizing
    open_picks_all = db.get_open_picks()
    current_exposure = sum(
        float(p.get("extra_json") and json.loads(p["extra_json"]).get("allocation", 0) or 0)
        for p in open_picks_all
    )

    # Track sector exposure for correlated exposure limit
    sector_exposure: dict[str, float] = {}
    for p in open_picks_all:
        cat = p.get("category", "stock")
        extra = json.loads(p["extra_json"]) if p.get("extra_json") else {}
        alloc = float(extra.get("allocation", 0))
        sector_exposure[cat] = sector_exposure.get(cat, 0) + alloc

    for signal in signals:
        if total_open >= MAX_OPEN_PICKS:
            break

        strategy = signal.get("strategy", "")
        strategy_open = db.count_open_picks(strategy)
        if strategy_open >= MAX_PICKS_PER_STRATEGY:
            continue

        # Check if we already have this symbol open from this strategy
        existing = db.get_open_picks(strategy)
        existing_symbols = {p["symbol"] for p in existing}
        if signal.get("symbol") in existing_symbols:
            continue

        # Per-symbol limit: max N concurrent positions on same symbol (any strategy)
        symbol_open = sum(1 for p in open_picks_all if p["symbol"] == signal["symbol"])
        if symbol_open >= MAX_PICKS_PER_SYMBOL:
            continue

        # Direction-diversity gate: prevent too many same-direction crypto positions
        category = signal.get("category", "stock")
        signal_type = signal.get("signal_type", "BUY")
        if category == "crypto":
            same_dir_crypto = sum(
                1 for p in open_picks_all
                if p.get("category", "stock") == "crypto"
                and (p.get("signal_type") or "BUY").upper() == signal_type.upper()
            )
            if same_dir_crypto >= MAX_SAME_DIRECTION_CRYPTO:
                continue

        # Check correlated exposure limit
        cat_exposure = sector_exposure.get(category, 0)
        if cat_exposure >= STARTING_CAPITAL * MAX_CORRELATED_EXPOSURE:
            continue

        # Emission gates (cooldown + daily cap) — Fix B/C extended to crypto.
        # Prevents per-symbol re-entry churn and >MAX_TRADES_PER_DAY bursts.
        try:
            from alpha_engine.non_crypto_policy import check_emission_gates as _ceg
            _gate = _ceg(str(signal.get("symbol") or ""))
            if _gate.get("blocked"):
                logger.debug(
                    "emission_gate_blocked %s %s: %s",
                    signal.get("strategy", "?"), signal.get("symbol", "?"),
                    _gate.get("reason"),
                )
                continue
        except Exception:
            pass

        # Tournament tier gate: Challenger strategies are paper-only (feature-flagged)
        try:
            use_tournament = os.environ.get("ALPHA_TOURNAMENT", "0") == "1"
            if use_tournament:
                from tournament_engine import TournamentEngine
                from config import DATA_DIR as _DATA_DIR
                _db_path = str(_DATA_DIR / "alpha.db")
                te = TournamentEngine(_db_path, portfolio="moderate")
                tier = te.get_tier(strategy)
                tier_risk = te.get_risk_pct(tier)
                if tier_risk == 0.0:  # challenger = paper only
                    print(f"  {strategy} is Challenger (paper-only), skipping live pick")
                    db.record_signal(signal)  # still record for tracking
                    continue
        except Exception as e:
            print(f"  Warning: Tournament tier check failed for {strategy}: {e}")

        # Record signal
        db.record_signal(signal)

        # Compute risk-based position size (legacy)
        entry_price = signal["entry_price"]
        stop_loss = signal.get("stop_loss", 0)
        allocation = compute_position_size(
            entry_price, stop_loss, category,
            STARTING_CAPITAL, current_exposure,
        )

        # Kelly Criterion position sizing (Gemini consensus)
        _strategy_stats = db.compute_strategy_stats(strategy) if hasattr(db, 'compute_strategy_stats') else {}
        _crypto_alloc = sum(
            v for cat, v in sector_exposure.items()
            if cat in ("crypto", "meme")
        )
        kelly_sizing = get_position_size(
            signal=signal,
            account_equity=STARTING_CAPITAL,
            strategy_stats=_strategy_stats,
            kelly_tier="quarter",
            open_positions=open_picks_all,
            current_crypto_allocation=_crypto_alloc,
        )

        # P3: Regime-aware position sizing (5 rules -- 2026-05-24)
        if _HAS_REGIME_POSITION_SIZER and compute_regime_position_size is not None:
            try:
                _asset_class = signal.get("category", signal.get("asset_class", "crypto")).upper()
                _direction = signal.get("signal_type", signal.get("direction", "BUY"))
                _atr_val = float(kelly_sizing.get("atr_adjustment", 0) or 0)
                _price = float(signal.get("entry_price", 0))
                _base_risk = float(kelly_sizing.get("kelly_fraction", 0.02))
                _regime = (context or {}).get("regime_sentinel", {}).get("regime",
                           (context or {}).get("hmm_regime", {}).get("aggregate", {}).get("market_regime"))
                _active = open_picks_all or []
                _p3_sizing = compute_regime_position_size(
                    symbol=symbol,
                    direction=_direction,
                    asset_class=_asset_class,
                    entry_price=_price,
                    atr=_atr_val,
                    portfolio_value=STARTING_CAPITAL,
                    base_risk_pct=_base_risk * 100,
                    active_positions=_active,
                    current_total_exposure_pct=current_exposure,
                    regime=_regime,
                )
                # Merge P3 results into kelly_sizing for downstream consumption
                kelly_sizing["p3_position_size_pct"] = _p3_sizing.get("position_size_pct", 0)
                kelly_sizing["p3_position_size_usd"] = _p3_sizing.get("position_size_usd", 0)
                kelly_sizing["p3_regime_multiplier"] = _p3_sizing.get("regime_multiplier", 1.0)
                kelly_sizing["p3_correlation_penalty"] = _p3_sizing.get("correlation_penalty", 1.0)
                kelly_sizing["p3_portfolio_heat_scale"] = _p3_sizing.get("portfolio_heat_scale", 1.0)
                kelly_sizing["p3_stop_distance_pct"] = _p3_sizing.get("stop_distance_pct", 0.0)
                kelly_sizing["p3_rules_applied"] = _p3_sizing.get("rules_applied", [])
                kelly_sizing["p3_regime"] = _p3_sizing.get("regime", "unknown")
                # Apply P3 sizing to allocation if available
                _p3_pct = _p3_sizing.get("position_size_pct", 0)
                if _p3_pct > 0:
                    _old_alloc = allocation
                    allocation = round(STARTING_CAPITAL * _p3_pct / 100, 2)
                    _delta_pct = abs(allocation - _old_alloc) / max(_old_alloc, 1) * 100
                    if _delta_pct > 20:
                        logger.info(
                            "[P3_sizing] %s allocation %s → %s (Δ%.0f%%, rules=%s)",
                            symbol, round(_old_alloc, 2), round(allocation, 2),
                            _delta_pct, _p3_sizing.get("rules_applied", [])
                        )
            except Exception:
                pass  # fail-open: P3 sizing is additive, not blocking

        # Apply Regime Sentinel risk multiplier to position sizing
        sentinel_data = (context or {}).get("regime_sentinel", {})
        sentinel_risk_mult = sentinel_data.get("risk_multiplier", 1.0)
        allocation = round(allocation * sentinel_risk_mult, 2)

        # Apply conformal prediction sizing multiplier
        _cp_mult = signal.get("conformal_multiplier", 1.0) or 1.0
        allocation = round(allocation * _cp_mult, 2)

        # Adjust TP for transaction costs (widen target)
        raw_tp = signal.get("take_profit")
        signal_type = signal.get("signal_type", "BUY")
        cost_model = get_cost_model(signal["symbol"], category)
        round_trip_cost = cost_model["total_per_trade"]

        if raw_tp and entry_price > 0:
            adjusted_tp = adjust_tp_for_costs(
                entry_price, raw_tp, signal["symbol"], category, signal_type
            )
        else:
            adjusted_tp = raw_tp

        # Build regime string for storage (Action 3.1)
        regime_info = signal.get("market_regime", {})
        regime_str = regime_info.get("regime", "unknown") if regime_info else "unknown"

        # Slippage/execution gap tracking: capture live market price at pick creation
        market_price_at_signal = None
        slippage_pct = None
        if market_data and signal["symbol"] in market_data:
            _mdf = market_data[signal["symbol"]]
            if _mdf is not None and not _mdf.empty and "Close" in _mdf.columns:
                market_price_at_signal = float(_mdf["Close"].iloc[-1])
                if market_price_at_signal > 0 and entry_price > 0:
                    slippage_pct = round(
                        abs(entry_price - market_price_at_signal) / market_price_at_signal * 100, 4
                    )

        # PR-V (xiao mi mimo Fix #3) — stale-price / dead-symbol gate.
        # Prevents next-MATIC-style ghost trading on flat OHLCV streams.
        # Memory ref: project_confidence_rho_matic_artifact (660 MATIC 0%-WR rows).
        # Default-ON; set ALPHA_FEED_HYGIENE_DISABLED=1 to bypass.
        if os.environ.get("ALPHA_FEED_HYGIENE_DISABLED", "0") != "1":
            _sym = (signal.get("symbol") or "").upper()
            if _sym in _DEAD_SYMBOLS:
                log.info("[feed-hygiene] skip %s — dead symbol", _sym)
                continue
            if market_data and signal["symbol"] in market_data:
                _mdf2 = market_data[signal["symbol"]]
                if _mdf2 is not None and not _mdf2.empty and "Close" in _mdf2.columns:
                    try:
                        _recent = _mdf2["Close"].iloc[-10:].tolist()
                        if has_deterministic_loss_pattern(_sym, _recent):
                            log.info("[feed-hygiene] skip %s — stale/deterministic price pattern", _sym)
                            continue
                    except Exception:
                        pass

        # Open pick with cost-adjusted TP and risk-based allocation
        pick_id = db.open_pick({
            "strategy": signal.get("strategy", ""),
            "symbol": signal.get("symbol", ""),
            "category": category,
            "signal_type": signal_type,
            "entry_price": entry_price,
            "entry_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "take_profit": adjusted_tp,
            "stop_loss": stop_loss,
            "confidence": signal.get("confidence"),
            "ml_score": signal.get("ml_score"),
            "regime": regime_str,
            "regime_at_entry": ((context or {}).get("hmm_regime", {}).get("aggregate", {}).get("market_regime") or regime_str or "UNKNOWN").upper(),
            "regime_timestamp": (context or {}).get("hmm_regime", {}).get("generated_at", ""),
            "atr_at_entry": signal.get("atr_at_entry"),
            "rsi_at_entry": signal.get("rsi_at_entry"),
            "volume_ratio": signal.get("volume_ratio"),
            "extra": {
                **signal.get("extra", {}),
                "allocation": allocation,
                "gross_tp": raw_tp,
                "net_tp": adjusted_tp,
                "transaction_cost_pct": round_trip_cost,
                "cost_model": cost_model.get("total_per_trade", 0),
                "position_sizing": "kelly_criterion",
                "risk_per_trade_pct": MAX_RISK_PER_TRADE,
                "kelly_fraction": kelly_sizing["kelly_fraction"],
                "kelly_tier_fraction": kelly_sizing["kelly_tier_fraction"],
                "kelly_tier": kelly_sizing["kelly_tier"],
                "kelly_position_size_usd": kelly_sizing["position_size_usd"],
                "atr_adjustment": kelly_sizing["atr_adjustment"],
                "correlation_group": kelly_sizing["correlation_group"],
                "trailing_stop_atr": kelly_sizing["trailing_stop_atr"],
                "sizing_capped_by": kelly_sizing["capped_by"],
                "regime_compatible": signal.get("regime_compatible", True),
                "regime_adx": regime_info.get("adx"),
                "regime_volatility": regime_info.get("volatility"),
                "regime_trend_direction": regime_info.get("trend_direction"),
                "regime_warning": signal.get("regime_warning"),
                "hmm_regime": regime_info.get("hmm_regime"),
                "hmm_confidence": regime_info.get("hmm_confidence"),
                "hmm_signal": regime_info.get("hmm_signal"),
                "hmm_leverage": regime_info.get("hmm_leverage"),
                # --- Regime Sentinel (4-state on-chain cycle) ---
                "sentinel_regime": sentinel_data.get("regime"),
                "sentinel_confidence": sentinel_data.get("confidence"),
                "sentinel_risk_multiplier": sentinel_risk_mult,
                "sentinel_action_bias": sentinel_data.get("action_bias"),
                "sentinel_mvrv": (sentinel_data.get("inputs") or {}).get("mvrv"),
                "sentinel_fng": (sentinel_data.get("inputs") or {}).get("fng"),
                "sentinel_funding": (sentinel_data.get("inputs") or {}).get("funding_rate"),
                # --- ML training features (persisted for retraining) ---
                # All enriched features must be stored here so ML training
                # via _build_features() sees real values (not always-zero).
                "funding_rate": signal.get("funding_rate"),
                "orderbook_imbalance": signal.get("orderbook_imbalance"),
                "obi_delta_5": signal.get("obi_delta_5"),
                "obi_delta_15": signal.get("obi_delta_15"),
                "obi_acceleration": signal.get("obi_acceleration"),
                "market_fear_greed": signal.get("market_fear_greed"),
                "ema_position": signal.get("ema_position"),
                "spread_pct": signal.get("spread_pct"),
                "wick_ratio": signal.get("wick_ratio"),
                "entry_distance_vwap": signal.get("entry_distance_vwap"),
                "bb_pct_b": signal.get("bb_pct_b"),
                "vpin": signal.get("vpin"),
                "galaxy_score": signal.get("galaxy_score"),
                "risk_reward": signal.get("risk_reward"),
                # Forward-test gate + technical features (were missing, always-zero in ML)
                "forward_wr": signal.get("forward_wr"),
                "forward_trades": signal.get("forward_trades"),
                "forward_validated": signal.get("forward_validated"),
                "hma_slope": signal.get("hma_slope"),
                "rsi_1h": signal.get("rsi_1h"),
                "rsi_4h": signal.get("rsi_4h"),
                "convergence": signal.get("convergence", 0),
                "regime_encoded": signal.get("regime_encoded", 0),
                "confluence_score": signal.get("confluence_score"),
                "generated_at": signal.get("generated_at") or signal.get("timestamp"),
                # Slippage/execution gap tracking
                "market_price_at_signal": market_price_at_signal,
                "slippage_pct": slippage_pct,
                # ML Feature Contract: pre-computed features at entry time
                "ml_features_at_entry": signal.get("ml_features_at_entry", {}),
                # Conformal prediction uncertainty interval
                "conformal_width": signal.get("conformal_width"),
                "conformal_multiplier": signal.get("conformal_multiplier"),
                "conformal_calibrated": signal.get("conformal_calibrated"),
            },
        })
        opened.append(pick_id)
        total_open += 1
        current_exposure += allocation
        sector_exposure[category] = sector_exposure.get(category, 0) + allocation

    return opened


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_report(signals: list[dict], closed: list[dict],
                 opened: list[str], db: SQLiteStore, elapsed: float):
    """Print formatted scan report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    summary = db.get_summary()

    print()
    print("=" * 70)
    print(f"  ALPHA ENGINE v{VERSION} -- Scan Results")
    print(f"  {now} | {STRATEGY_COUNT} strategies | Scan took {elapsed:.1f}s")
    print("=" * 70)

    # Closed picks
    if closed:
        print(f"\n  CLOSED PICKS ({len(closed)}):")
        for c in closed:
            pnl = c.get("pnl_pct", 0) or 0
            emoji = "W" if c.get("status") == "WON" or (c.get("status") != "LOST" and pnl > 0) else "L"
            gross_pnl = c.get("gross_pnl_pct", c["pnl_pct"])
            net_pnl = c.get("net_pnl_pct", c["pnl_pct"])
            cost_pct = c.get("transaction_cost_pct", 0)
            print(f"    [{emoji}] {c['symbol']:12s} {c['strategy']:30s} "
                  f"Gross={gross_pnl:+.2f}%  Net={net_pnl:+.2f}%  "
                  f"(${c['pnl_dollar']:+.2f})  Cost={cost_pct:.2f}%  "
                  f"Exit: {c['exit_reason']}")

    # New signals
    if signals:
        # Forward gate summary
        validated = [s for s in signals if s.get("forward_validated")]
        unvalidated = [s for s in signals if not s.get("forward_validated")]
        if unvalidated:
            print(f"\n  [FORWARD GATE] {len(validated)}/{len(signals)} signals "
                  f"from validated strategies ({len(unvalidated)} unvalidated)")

        # Regime compatibility summary (Action 3.1)
        compatible_count = sum(1 for s in signals if s.get("regime_compatible", True))
        incompatible_count = len(signals) - compatible_count
        if incompatible_count > 0:
            print(f"  [REGIME FILTER] {compatible_count} compatible, "
                  f"{incompatible_count} mismatched (penalized -10% ML score)")

        high_conf = [s for s in signals if s.get("ml_score", 0) >= 0.60]
        med_conf = [s for s in signals if 0.40 <= s.get("ml_score", 0) < 0.60]

        if high_conf:
            print(f"\n  HIGH CONFIDENCE SIGNALS (ML >= 0.60): {len(high_conf)}")
            for s in high_conf[:10]:
                ep = s["entry_price"] or 1
                tp_pct = (s["take_profit"] / ep - 1) * 100 if s.get("take_profit") else 0
                sl_pct = (s["stop_loss"] / ep - 1) * 100 if s.get("stop_loss") else 0
                conv_tag = f" [+{s['convergence']} converge]" if s.get("convergence", 0) > 0 else ""
                gate_tag = "" if s.get("forward_validated") else " [UNVALIDATED]"
                # Regime tag (Action 3.1)
                regime_tag = ""
                ri = s.get("market_regime", {})
                if ri and ri.get("regime") != "unknown":
                    regime_tag = f" [{ri['regime'].upper()}"
                    if ri.get("adx") is not None:
                        regime_tag += f" ADX={ri['adx']}"
                    regime_tag += "]"
                    if not s.get("regime_compatible", True):
                        regime_tag += " [!MISMATCH]"
                _st = s.get('signal_type', s.get('direction', '?'))
                print(f"    {_st:4s}  {s.get('symbol','?'):16s} @ {s.get('entry_price','?'):<12}{gate_tag}")
                print(f"          Strategy: {s.get('strategy','?')} (ML={s.get('ml_score',0):.2f}){conv_tag}{regime_tag}")
                print(f"          TP: {s['take_profit']} ({tp_pct:+.1f}%)  "
                      f"SL: {s['stop_loss']} ({sl_pct:+.1f}%)  "
                      f"R:R={s.get('risk_reward', 0):.1f}")
                print(f"          {s.get('reason', '')}")
                print()

        if med_conf:
            print(f"  MEDIUM CONFIDENCE SIGNALS (ML 0.40-0.60): {len(med_conf)}")
            for s in med_conf[:5]:
                gate_tag = "" if s.get("forward_validated") else " [UNVALIDATED]"
                regime_warn = ""
                if not s.get("regime_compatible", True):
                    regime_warn = " [!REGIME]"
                sig_type = s.get('signal_type', s.get('direction', '?'))
                print(f"    {sig_type:4s} {s['symbol']:16s} @ {s.get('entry_price','?'):<12} "
                      f"ML={s.get('ml_score',0):.2f}  {s.get('strategy','?')}{gate_tag}{regime_warn}")
    else:
        print("\n  No signals generated this scan.")

    # Opened picks
    if opened:
        print(f"\n  NEW PICKS OPENED: {len(opened)}")
        for pid in opened:
            print(f"    -> {pid}")

    # Portfolio summary
    print(f"\n  PORTFOLIO: {summary['open_picks']} open | "
          f"{summary['closed_picks']} closed | "
          f"W/L: {summary['won']}/{summary['lost']} | "
          f"Win rate: {summary['win_rate']*100:.1f}%")
    print("=" * 70)


def print_status(db: SQLiteStore):
    """Print current portfolio status."""
    summary = db.get_summary()
    open_picks = db.get_open_picks()

    print("=" * 70)
    print(f"  ALPHA ENGINE v{VERSION} -- Portfolio Status")
    print("=" * 70)
    print(f"  Total signals generated: {summary['total_signals']}")
    print(f"  Open picks: {summary['open_picks']}")
    print(f"  Closed picks: {summary['closed_picks']}")
    print(f"  Won: {summary['won']} | Lost: {summary['lost']}")
    print(f"  Win rate: {summary['win_rate']*100:.1f}%")

    if open_picks:
        print(f"\n  OPEN POSITIONS:")
        for p in open_picks:
            print(f"    {p['signal_type']:4s} {p['symbol']:16s} "
                  f"entry={p['entry_price']}  "
                  f"TP={p.get('take_profit', '?')}  "
                  f"SL={p.get('stop_loss', '?')}  "
                  f"ML={p.get('ml_score', '?')}  "
                  f"[{p['strategy']}]")

    # Strategy leaderboard
    all_stats = db.get_all_strategy_stats()
    if all_stats:
        print(f"\n  STRATEGY LEADERBOARD:")
        print(f"  {'Strategy':35s} {'WR':>6s} {'Sharpe':>7s} {'PF':>6s} "
              f"{'Picks':>6s} {'Gate':>10s}")
        print(f"  {'-'*35} {'-'*6} {'-'*7} {'-'*6} {'-'*6} {'-'*10}")
        for s in all_stats[:15]:
            gate_pass, _, tc, wr = passes_forward_gate(s["strategy"], s)
            gate_label = "VALIDATED" if gate_pass else f"{tc}/{FORWARD_GATE_MIN_TRADES}"
            print(f"  {s['strategy']:35s} "
                  f"{s.get('win_rate', 0)*100:5.1f}% "
                  f"{s.get('sharpe', 0):6.2f} "
                  f"{s.get('profit_factor', 0):5.2f} "
                  f"{s.get('closed_picks', 0):5d} "
                  f"{gate_label:>10s}")

    print("=" * 70)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="ALPHA_ENGINE Live Scanner")
    parser.add_argument("--crypto-only", action="store_true", help="Run crypto strategies only")
    parser.add_argument("--forex-only", action="store_true", help="Run forex strategies only")
    parser.add_argument("--equity-only", action="store_true", help="Run equity strategies only")
    parser.add_argument("--commodity-only", action="store_true", help="Run commodity strategies only")
    parser.add_argument("--futures-only", action="store_true", help="Run futures strategies only")
    parser.add_argument("--etf-only", action="store_true", help="Run ETF strategies only")
    parser.add_argument("--bond-only", action="store_true", help="Run bond strategies only")
    parser.add_argument("--dry-run", action="store_true", help="Show signals without opening picks")
    parser.add_argument("--train-ml", action="store_true", help="Train ML model")
    parser.add_argument("--status", action="store_true", help="Show portfolio status")
    args = parser.parse_args()

    # Initialize
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = SQLiteStore()
    ranker = MLSignalRanker()

    if args.status:
        print_status(db)
        db.close()
        return

    if args.train_ml:
        print("Training ML model...")
        metrics = ranker.train(db)
        print(json.dumps(metrics, indent=2))
        db.close()
        return

    # Determine which symbols to fetch
    strategy_filter = "all"
    symbols = list(ALL_SYMBOLS.keys())
    if args.crypto_only:
        strategy_filter = "crypto"
        symbols = list(CRYPTO_SYMBOLS.keys())
    elif args.forex_only:
        strategy_filter = "forex"
        symbols = list(FOREX_SYMBOLS.keys())
    elif args.equity_only:
        strategy_filter = "equity"
        symbols = list(EQUITY_SYMBOLS.keys())
    elif args.commodity_only:
        strategy_filter = "commodity"
        symbols = list(COMMODITY_SYMBOLS.keys())
    elif args.futures_only:
        strategy_filter = "futures"
        symbols = list(FUTURES_SYMBOLS.keys())
    elif args.etf_only:
        strategy_filter = "etf"
        symbols = list(ETF_SYMBOLS.keys())
    elif args.bond_only:
        strategy_filter = "bond"
        symbols = list(BOND_SYMBOLS.keys())

    # Merge dynamic universe symbols (hot coins from Binance Futures)
    _dynamic_count = 0
    if _HAS_DYNAMIC_UNIVERSE and strategy_filter in ("all", "crypto"):
        try:
            _dyn_symbols = load_dynamic_symbols()
            if _dyn_symbols:
                _existing = set(symbols)
                _new_dynamic = [s for s in _dyn_symbols if s not in _existing]
                symbols.extend(_new_dynamic)
                _dynamic_count = len(_new_dynamic)
                if _dynamic_count > 0:
                    print(f"  [DYNAMIC] Added {_dynamic_count} hot symbols from dynamic universe")
        except Exception as _dyn_err:
            print(f"  [DYNAMIC] Skipped: {_dyn_err}")

    # Merge missed-opportunity recommendations (symbols we keep missing)
    _missed_opp_count = 0
    if strategy_filter in ("all", "crypto"):
        try:
            from missed_opportunity_analyzer import get_universe_additions
            _missed_adds = get_universe_additions()
            if _missed_adds:
                _existing_mo = set(symbols)
                for _msym in _missed_adds:
                    if _msym not in _existing_mo:
                        symbols.append(_msym)
                        _missed_opp_count += 1
                if _missed_opp_count > 0:
                    print(f"  [MISSED-OPP] Added {_missed_opp_count} symbols from missed opportunity analyzer")
        except Exception as _mo_err:
            print(f"  [MISSED-OPP] Skipped: {_mo_err}")

    # Merge hindsight winner patterns (symbols that pump frequently)
    _hindsight_count = 0
    if strategy_filter in ("all", "crypto"):
        try:
            _winner_patterns_path = DATA_DIR / "winner_patterns.json"
            if _winner_patterns_path.exists():
                with open(_winner_patterns_path, encoding="utf-8") as _wpf:
                    _wp_data = json.load(_wpf)
                if _wp_data.get("status") == "active":
                    _freq_winners = _wp_data.get("most_frequent_winners", {})
                    # Top 10 most-frequently-winning symbols
                    _top_winners = sorted(_freq_winners.items(), key=lambda x: x[1], reverse=True)[:10]
                    _existing_set = set(symbols)
                    for _wsym, _wcount in _top_winners:
                        if _wsym not in _existing_set:
                            # Map Binance symbol (e.g. BTCUSDT) to yfinance format (BTC-USD)
                            _base = _wsym.replace("USDT", "")
                            _yf_key = f"{_base}-USD"
                            if _yf_key not in _existing_set:
                                symbols.append(_yf_key)
                                _hindsight_count += 1
                    if _hindsight_count > 0:
                        print(f"  [HINDSIGHT] Boosted {_hindsight_count} symbols from winner patterns")
        except Exception as _hs_err:
            print(f"  [HINDSIGHT] Skipped: {_hs_err}")

    start_time = time.time()
    print(f"\nALPHA ENGINE v{VERSION} -- Starting scan ({strategy_filter})")
    print(f"  {STRATEGY_COUNT} strategies | {len(symbols)} symbols"
          f"{f' ({_dynamic_count} dynamic)' if _dynamic_count else ''}"
          f"{f' ({_hindsight_count} hindsight)' if _hindsight_count else ''}")
    print(f"  ML model trained: {ranker.is_trained}")
    print(f"  Regime detection: ENABLED (ADX-based, Action 3.1)")
    print()

    # -- Kill Switch: check portfolio health before generating new picks ----
    _kill_switch_status = {
        "is_killed": False, "kill_reason": None, "severity": "ok",
        "recommended_action": "none", "conditions": [], "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    if _HAS_KILL_SWITCH:
        try:
            _kill_switch_status = _check_kill_conditions()
            _ks_sev = _kill_switch_status.get("severity", "ok")
            _ks_action = _kill_switch_status.get("recommended_action", "none")
            if _kill_switch_status.get("is_killed"):
                print(f"  [KILL SWITCH] TRIGGERED: severity={_ks_sev}, action={_ks_action}")
                print(f"  [KILL SWITCH] Reason: {_kill_switch_status.get('kill_reason', 'unknown')}")
                if _ks_action in ("close_all", "pause_new_entries"):
                    print(f"  [KILL SWITCH] Skipping new pick generation (action={_ks_action})")
            elif _ks_sev == "warning":
                print(f"  [KILL SWITCH] WARNING: {_kill_switch_status.get('kill_reason', 'see conditions')}")
            else:
                print(f"  [KILL SWITCH] OK: no conditions triggered")
        except Exception as _ks_err:
            print(f"  [KILL SWITCH] Check failed (non-fatal): {_ks_err}")
    else:
        print("  [KILL SWITCH] Module not available (skipped)")

    # If kill switch says close_all or pause_new_entries, skip the entire scan
    _kill_switch_halt = (
        _kill_switch_status.get("is_killed", False)
        and _kill_switch_status.get("recommended_action") in ("close_all", "pause_new_entries")
    )

    # Step 0: Auto-train ML model if stale (>24h) or missing
    # Uses smart_train() which does incremental training by default
    # and falls back to full retrain on drift or >100 new picks.
    try:
        _model_stale = True
        if ML_MODEL_PATH.exists():
            _model_age_h = (datetime.now(timezone.utc).timestamp()
                            - ML_MODEL_PATH.stat().st_mtime) / 3600
            _model_stale = _model_age_h > 24
            if _model_stale:
                print(f"  [ML] Model is {_model_age_h:.1f}h old (>24h) -- retraining")
        else:
            print("  [ML] No saved model found -- checking if training data available")

        if _model_stale:
            _closed_count = db.get_summary().get("closed_picks", 0)
            if _closed_count >= ranker.MIN_SAMPLES_TO_TRAIN:
                print(f"  [ML] Training on {_closed_count} closed picks...")
            else:
                print(f"  [ML] DB has {_closed_count} picks, attempting JSON import + training...")

            # Back-fill prediction outcomes before training (for drift detection)
            try:
                _closed_path = DATA_DIR / "closed_picks.json"
                if _closed_path.exists():
                    with open(_closed_path, encoding="utf-8") as _cpf:
                        _closed_for_drift = json.load(_cpf)
                    _filled = ranker.update_prediction_outcomes(_closed_for_drift)
                    if _filled > 0:
                        print(f"  [ML] Back-filled {_filled} prediction outcomes for drift detection")
            except Exception as _drift_fill_err:
                print(f"  [ML] Outcome back-fill failed (non-fatal): {_drift_fill_err}")

            # smart_train: incremental by default, full on drift or >100 new picks
            _ml_metrics = ranker.smart_train(db)
            _ml_status = _ml_metrics.get("status", "unknown")
            if _ml_status == "trained":
                print(f"  [ML] Result: full retrain"
                      f" | model={_ml_metrics.get('model_type', '?')}"
                      f" | ROC-AUC={_ml_metrics.get('cv_roc_auc', '?')}"
                      f" | samples={_ml_metrics.get('samples', '?')}")
            elif _ml_status == "incremental_trained":
                print(f"  [ML] Result: incremental"
                      f" | trees_added={_ml_metrics.get('trees_added', '?')}"
                      f" | new_picks={_ml_metrics.get('new_picks', '?')}"
                      f" | total_trees=~{_ml_metrics.get('total_trees', '?')}")
            elif _ml_status == "insufficient_data":
                print(f"  [ML] Only {_ml_metrics.get('samples', 0)} closed picks"
                      f" (need {ranker.MIN_SAMPLES_TO_TRAIN}) -- using heuristic")
            elif _ml_status.startswith("skipped"):
                print(f"  [ML] Training skipped: {_ml_status}")
            else:
                print(f"  [ML] Training result: {_ml_status}")
    except Exception as _ml_err:
        print(f"  [ML] Training failed (non-fatal): {_ml_err}")

    # Polymarket volume spike filter: invalidate cache at scan start
    if _HAS_PM_VOL_FILTER and _pm_invalidate_cache is not None:
        _pm_invalidate_cache()

    # Step 1: Fetch market data (with yfinance ticker resolution)
    print("[1/5] Fetching market data...")
    yf_tickers, yf_to_key, binance_only = resolve_yf_symbols(symbols)
    _remapped = [t for t in yf_tickers if yf_to_key.get(t) != t]
    if _remapped:
        print(f"  [YF-REMAP] {len(_remapped)} tickers remapped: "
              + ", ".join(f"{yf_to_key[t]}->{t}" for t in _remapped[:8]))
    if binance_only:
        print(f"  [YF-SKIP] {len(binance_only)} symbols use Binance-only: "
              + ", ".join(binance_only[:8])
              + ("..." if len(binance_only) > 8 else ""))
    # Fetch yfinance data using corrected tickers, then remap keys back
    _fetch_requested = len(yf_tickers) + len(binance_only)
    raw_data = fetch_market_data(yf_tickers + binance_only)
    data = {}
    for yf_t, df in raw_data.items():
        canonical = yf_to_key.get(yf_t, yf_t)  # map back to dict key
        data[canonical] = df
    # Record fetch diagnostics so the __main__ fail-open guard can tell a
    # data-provider outage apart from a genuinely empty market.
    LAST_RUN_DIAGNOSTICS["scan_ran"] = True
    LAST_RUN_DIAGNOSTICS["symbols_requested"] = _fetch_requested
    LAST_RUN_DIAGNOSTICS["symbols_loaded"] = len(data)
    if not data:
        print("  FATAL: No market data received. Aborting.")
        db.close()
        sys.exit(1)

    # Step 2: Fetch context (Fear & Greed, funding rates, etc.)
    print("[2/5] Fetching context data (sentiment, funding rates)...")
    context = fetch_context_data()
    fg = context.get("fear_greed", {}).get("data", [{}])
    fg_val = fg[0].get("value", "?") if fg else "?"
    print(f"  Fear & Greed: {fg_val}")
    if "funding_rates" in context:
        print(f"  Funding rates: {len(context['funding_rates'])} symbols")

    # Step 3: Check existing open picks (TP/SL/trailing)
    print("[3/5] Checking open picks...")
    closed = check_open_picks(db, data)
    if closed:
        print(f"  Closed {len(closed)} pick(s)")

    # Step 4: Run strategies (with regime annotation - Action 3.1)
    # If kill switch halted, skip new signal generation entirely
    if _kill_switch_halt:
        print(f"[4/5] SKIPPED -- kill switch active (action={_kill_switch_status.get('recommended_action')})")
        signals = []
    else:
        print(f"[4/5] Running {strategy_filter} strategies (regime-aware)...")
        signals = run_strategies(data, context, strategy_filter)
        print(f"  Total raw signals: {len(signals)}")

    # -- Dynamic Gainer Momentum: inject picks from top gainers tracker ---
    try:
        from gainer_tracker import run_gainer_tracker
        gainer_picks = run_gainer_tracker()
        if gainer_picks:
            for gp in gainer_picks:
                gp.setdefault("strategy", "dynamic_gainer_momentum")
                gp.setdefault("signal_type", "BUY")
                gp.setdefault("confidence", gp.get("score", 0.6))
                # Compute ML features so gainers go through same scoring path
                sym = gp.get("symbol", "")
                if sym and sym in data:
                    gp["ml_features_at_entry"] = compute_ml_features_at_entry(sym, data, gp)
            signals.extend(gainer_picks)
            print(f"  [dynamic_gainer_momentum] -> {len(gainer_picks)} gainer signal(s)")
    except ImportError:
        pass  # gainer_tracker module not available yet
    except Exception as e:
        print(f"  [dynamic_gainer_momentum] skipped: {e}")

    # -- Copy Trader Consensus: inject picks from top copy trader analyzer --
    try:
        try:
            from alpha_engine.copy_trader_analyzer import analyze_top_traders
        except ImportError:
            from copy_trader_analyzer import analyze_top_traders
        ct_picks = analyze_top_traders()
        if ct_picks:
            signals.extend(ct_picks)
            print(f"  [COPY TRADER] {len(ct_picks)} consensus picks from top traders")
    except ImportError:
        pass  # copy_trader_analyzer module not available yet
    except Exception as e:
        print(f"  [COPY TRADER] skipped: {e}")

    # -- Copy Trader Bridge: inject filtered picks from copy_trader_intel pipeline --
    try:
        try:
            from alpha_engine.copy_trader_bridge import get_copy_trader_picks
        except ImportError:
            from copy_trader_bridge import get_copy_trader_picks
        bridge_picks = get_copy_trader_picks()
        if bridge_picks:
            signals.extend(bridge_picks)
            print(f"  [COPY TRADER BRIDGE] {len(bridge_picks)} filtered picks from copy_trader_intel")
    except ImportError:
        pass  # copy_trader_bridge module not available yet
    except Exception as e:
        print(f"  [COPY TRADER BRIDGE] skipped: {e}")

    # -- On-Chain & Macro Confluence: inject macro regime picks (6 indicators) --
    if generate_macro_picks is not None:
        try:
            macro_picks = generate_macro_picks()
            if macro_picks:
                signals.extend(macro_picks)
                print(f"  [MACRO ONCHAIN] {len(macro_picks)} macro confluence pick(s)")
        except ImportError:
            pass
        except Exception as e:
            print(f"  [MACRO ONCHAIN] skipped: {e}")

    # -- Super Alligator: Bill Williams Alligator + VWAP/SMA200 (4 variants) --
    if generate_alligator_picks is not None:
        try:
            alligator_picks = generate_alligator_picks()
            if alligator_picks:
                signals.extend(alligator_picks)
                print(f"  [ALLIGATOR] {len(alligator_picks)} alligator pick(s)")
        except ImportError:
            pass
        except Exception as e:
            print(f"  [ALLIGATOR] skipped: {e}")

    # -- Deribit Options Signals: risk reversal, max pain, put/call ratio --
    if generate_options_picks is not None:
        try:
            options_picks = generate_options_picks()
            if options_picks:
                signals.extend(options_picks)
                print(f"  [OPTIONS] {len(options_picks)} deribit options pick(s)")
        except ImportError:
            pass
        except Exception as e:
            print(f"  [OPTIONS] skipped: {e}")

    # -- Quant Research: Fisher, Garman-Klass, TTM Squeeze, Hurst, KAMA, Vortex, Amihud, Vol Term --
    if generate_quant_picks is not None:
        try:
            qr_picks = generate_quant_picks()
            if qr_picks:
                signals.extend(qr_picks)
                print(f"  [QUANT RESEARCH] {len(qr_picks)} quant research pick(s)")
        except ImportError:
            pass
        except Exception as e:
            print(f"  [QUANT RESEARCH] skipped: {e}")

    # -- Quant Algorithms: Kalman, Bayesian, GARCH, Cointegration, Gaussian, Adaptive BB, Z-Score, Poly Reg --
    if generate_quant_algorithm_picks is not None:
        try:
            qa_picks = generate_quant_algorithm_picks()
            if qa_picks:
                signals.extend(qa_picks)
                print(f"  [QUANT ALGORITHMS] {len(qa_picks)} quant algorithm pick(s)")
        except ImportError:
            pass
        except Exception as e:
            print(f"  [QUANT ALGORITHMS] skipped: {e}")

    # -- Volume & Microstructure: OBV, Volume Profile, MFI, Williams %R, Vol-MA Cross, LinReg Channels --
    if generate_volume_micro_picks is not None:
        try:
            vm_picks = generate_volume_micro_picks()
            if vm_picks:
                signals.extend(vm_picks)
                print(f"  [VOLUME MICRO] {len(vm_picks)} volume/microstructure pick(s)")
        except ImportError:
            pass
        except Exception as e:
            print(f"  [VOLUME MICRO] skipped: {e}")

    # -- Crypto Enhancement Pack: 5 high-WR combo strategies (Funding+Sentiment, Whale+Regime, Options+Momentum, MTF, Liquidation) --
    if generate_enhancement_picks is not None:
        try:
            ce_picks = generate_enhancement_picks()
            if ce_picks:
                # Enrich each pick with crypto ML features from the feature pipeline
                if _HAS_CRYPTO_FEATURE_PIPELINE and _compute_crypto_features is not None:
                    for p in ce_picks:
                        try:
                            sym = p.get("symbol", "")
                            # Fetch minimal OHLCV for feature computation
                            _ce_klines = None
                            # Binance mirrors + CoinGecko/KuCoin/CryptoCompare failover (API rule)
                            for _ce_base in [
                                "https://api.binance.com",
                                "https://api1.binance.com",
                                "https://api2.binance.com",
                                "https://api3.binance.com",
                                "https://data-api.binance.vision",
                            ]:
                                try:
                                    _ce_url = f"{_ce_base}/api/v3/klines?symbol={sym}&interval=4h&limit=70"
                                    _ce_req = urllib.request.Request(_ce_url, headers={"User-Agent": "AlphaEngine/2.0"})
                                    with urllib.request.urlopen(_ce_req, timeout=8) as _ce_resp:
                                        _ce_klines = json.loads(_ce_resp.read())
                                    break
                                except Exception:
                                    continue
                            # CoinGecko fallback
                            if not _ce_klines:
                                try:
                                    _ce_cg_id = sym.replace("USDT", "").lower()
                                    _ce_cg_url = f"https://api.coingecko.com/api/v3/coins/{_ce_cg_id}/ohlc?vs_currency=usd&days=12"
                                    _ce_cg_req = urllib.request.Request(_ce_cg_url, headers={"User-Agent": "AlphaEngine/2.0"})
                                    with urllib.request.urlopen(_ce_cg_req, timeout=8) as _ce_cg_resp:
                                        _ce_cg_raw = json.loads(_ce_cg_resp.read())
                                    if _ce_cg_raw and len(_ce_cg_raw) >= 10:
                                        _ce_klines = [[r[0], r[1], r[2], r[3], r[4], 0, 0, 0, 0, 0, 0, 0] for r in _ce_cg_raw]
                                except Exception:
                                    pass
                            # KuCoin fallback
                            if not _ce_klines:
                                try:
                                    _ce_kc_sym = sym.replace("USDT", "-USDT")
                                    _ce_kc_url = f"https://api.kucoin.com/api/v1/market/candles?type=4hour&symbol={_ce_kc_sym}"
                                    _ce_kc_req = urllib.request.Request(_ce_kc_url, headers={"User-Agent": "AlphaEngine/2.0"})
                                    with urllib.request.urlopen(_ce_kc_req, timeout=8) as _ce_kc_resp:
                                        _ce_kc_raw = json.loads(_ce_kc_resp.read())
                                    _ce_kc_candles = _ce_kc_raw.get("data", []) if isinstance(_ce_kc_raw, dict) else []
                                    if _ce_kc_candles and len(_ce_kc_candles) >= 10:
                                        _ce_klines = [[int(c[0])*1000, c[1], c[3], c[4], c[2], c[5], 0, 0, 0, 0, 0, 0] for c in _ce_kc_candles]
                                        _ce_klines.reverse()
                                except Exception:
                                    pass
                            # CryptoCompare fallback
                            if not _ce_klines:
                                try:
                                    _ce_cc_fsym = sym.replace("USDT", "")
                                    _ce_cc_url = f"https://min-api.cryptocompare.com/data/v2/histohour?fsym={_ce_cc_fsym}&tsym=USDT&limit=70&aggregate=4"
                                    _ce_cc_req = urllib.request.Request(_ce_cc_url, headers={"User-Agent": "AlphaEngine/2.0"})
                                    with urllib.request.urlopen(_ce_cc_req, timeout=8) as _ce_cc_resp:
                                        _ce_cc_raw = json.loads(_ce_cc_resp.read())
                                    _ce_cc_data = _ce_cc_raw.get("Data", {}).get("Data", []) if isinstance(_ce_cc_raw, dict) else []
                                    if _ce_cc_data and len(_ce_cc_data) >= 10:
                                        _ce_klines = [[d["time"]*1000, d["open"], d["high"], d["low"], d["close"], d.get("volumeto", 0), 0, 0, 0, 0, 0, 0] for d in _ce_cc_data]
                                except Exception:
                                    pass
                            if _ce_klines:
                                _ce_ohlcv = {
                                    "open": [float(k[1]) for k in _ce_klines],
                                    "high": [float(k[2]) for k in _ce_klines],
                                    "low": [float(k[3]) for k in _ce_klines],
                                    "close": [float(k[4]) for k in _ce_klines],
                                    "volume": [float(k[5]) for k in _ce_klines],
                                }
                                p["ml_features"] = _compute_crypto_features(sym, _ce_ohlcv)
                        except Exception:
                            pass  # Feature enrichment is best-effort
                signals.extend(ce_picks)
                print(f"  [CRYPTO ENHANCEMENT] {len(ce_picks)} combo pick(s)")
        except ImportError:
            pass
        except Exception as e:
            print(f"  [CRYPTO ENHANCEMENT] skipped: {e}")

    # -- Sustained Gainer Confluence: 5-condition momentum breakout with trailing stop portfolio --
    if generate_sustained_gainer_picks is not None:
        try:
            sg_picks = generate_sustained_gainer_picks()
            if sg_picks:
                signals.extend(sg_picks)
                print(f"  [SUSTAINED GAINER] {len(sg_picks)} confluence pick(s)")
        except ImportError:
            pass
        except Exception as e:
            print(f"  [SUSTAINED GAINER] skipped: {e}")

    # -- Gainer Capture: 3 strategies scanning ALL Binance for big movers --
    if generate_gainer_picks is not None:
        try:
            existing_syms = {s.get("symbol", "") for s in signals}
            gc_picks = generate_gainer_picks(data=data, existing_symbols=existing_syms)
            if gc_picks:
                signals.extend(gc_picks)
                print(f"  [GAINER CAPTURE] {len(gc_picks)} gainer pick(s)")
        except ImportError:
            pass
        except Exception as e:
            print(f"  [GAINER CAPTURE] skipped: {e}")

    # -- Prediction Market Whales: Polymarket momentum, whale follow, Kalshi intraday, divergence, consensus --
    if generate_prediction_market_picks is not None:
        try:
            pmw_picks = generate_prediction_market_picks()
            if pmw_picks:
                signals.extend(pmw_picks)
                print(f"  [PREDICTION MARKET WHALES] {len(pmw_picks)} prediction market pick(s)")
        except ImportError:
            pass
        except Exception as e:
            print(f"  [PREDICTION MARKET WHALES] skipped: {e}")

    # -- Global TP/SL sanity check: enforce maximum percentages per asset class --
    # Prevents unrealistic targets (e.g. 30-172% TP on equities from analyst targets,
    # commodity-scale ATR multipliers on ETFs, etc.)
    _TP_SL_MAX = {
        # category -> (max_tp_pct, max_sl_pct)
        "crypto": (15.0, 8.0),
        "meme": (15.0, 8.0),
        "forex": (1.5, 1.0),
        "equity": (8.0, 5.0),
        "stocks": (5.0, 3.0),
        "stock": (5.0, 3.0),
        "penny": (8.0, 5.0),
        "commodity": (5.0, 3.0),
        "futures": (5.0, 3.0),
        "index": (3.0, 2.0),
        "etf": (4.0, 2.5),
        "bond": (6.0, 4.0),  # matches bond_strategies.py hard caps
    }
    _DEFAULT_TP_SL_MAX = (5.0, 3.0)

    # ETF symbols that should use tighter caps even if categorised as "equity"
    _ETF_SYMBOLS = {"SPY", "QQQ", "IWM", "EFA", "EEM", "DIA",
                     "XLF", "XLE", "XLK", "XLV", "XLI", "GLD", "SLV", "USO",
                     "VTI", "VOO", "ARKK", "ARKG", "SOXL", "TQQQ"}
    # Bond ETF symbols — force category to "bond" for tighter TP/SL caps (3%/2%)
    _BOND_SYMBOLS = {"TLT", "IEF", "SHY", "LQD", "HYG", "AGG", "BND", "EMB"}

    _tp_sl_clamped = 0
    if signals:
        for sig in signals:
            entry = sig.get("entry_price", 0)
            tp = sig.get("take_profit", 0)
            sl = sig.get("stop_loss", 0)
            if not entry or entry <= 0:
                continue

            cat = str(sig.get("category", "")).lower()
            sym = sig.get("symbol", "")

            # Override category for known ETFs
            if sym in _ETF_SYMBOLS:
                cat = "etf"
            elif sym in _BOND_SYMBOLS:
                cat = "bond"

            max_tp_pct, max_sl_pct = _TP_SL_MAX.get(cat, _DEFAULT_TP_SL_MAX)

            # Calculate current TP/SL percentages
            tp_pct = abs(tp - entry) / entry * 100
            sl_pct = abs(sl - entry) / entry * 100

            clamped = False
            if tp_pct > max_tp_pct:
                # Clamp TP to max percentage
                if tp > entry:
                    sig["take_profit"] = round(entry * (1 + max_tp_pct / 100), 6)
                else:
                    sig["take_profit"] = round(entry * (1 - max_tp_pct / 100), 6)
                clamped = True

            if sl_pct > max_sl_pct:
                # Clamp SL to max percentage
                if sl < entry:
                    sig["stop_loss"] = round(entry * (1 - max_sl_pct / 100), 6)
                else:
                    sig["stop_loss"] = round(entry * (1 + max_sl_pct / 100), 6)
                clamped = True

            if clamped:
                _tp_sl_clamped += 1
                # Recalculate risk/reward after clamping
                new_tp = sig["take_profit"]
                new_sl = sig["stop_loss"]
                direction = sig.get("direction", sig.get("signal_type", "LONG")).upper()
                if direction in ("LONG", "BUY"):
                    rr = (new_tp - entry) / (entry - new_sl) if entry > new_sl else 0
                else:
                    rr = (entry - new_tp) / (new_sl - entry) if new_sl > entry else 0
                sig["risk_reward"] = round(rr, 2)

        if _tp_sl_clamped > 0:
            print(f"  [TP/SL SANITY] Clamped {_tp_sl_clamped} signals with out-of-range targets")

    # Record raw signal count for the __main__ fail-open guard (before any
    # ML ranking / gate filtering trims the list).
    LAST_RUN_DIAGNOSTICS["raw_signals"] = len(signals)

    # Enrich signals with ML features for forward_testing/signal_quality_ml.py
    if signals:
        signals = enrich_signals_with_ml_features(signals, data)

    # Cross-sectional ranking: rank each symbol vs universe (Liu et al. 2022 JFE)
    if signals and inject_cross_sectional_features is not None:
        try:
            signals = inject_cross_sectional_features(signals, data)
        except Exception as _cs_err:
            print(f"  [CROSS-SECTIONAL] Failed (non-fatal): {_cs_err}")

    # Phase 16: Populate real OHLCV-derived features on every signal BEFORE ML scoring.
    # This kills 25 dead features by fetching Binance klines and computing RSI, ATR,
    # MACD, Stochastic, CCI, Williams %R, VWAP deviation, Garman-Klass vol, etc.
    if signals and populate_features_batch is not None:
        try:
            signals = populate_features_batch(signals)
        except Exception as _fp_err:
            print(f"  [FEATURE POPULATOR] Failed (non-fatal): {_fp_err}")

    # Pine Script indicator filters: enrich signals with squeeze/EMA/VWAP/safety scores
    # Winning indicators from backtest: VWAP-BB Squeeze (66.7% WR), Momentum Safety (50.5%),
    # Squeeze Momentum (48.5%), EMA Cloud (44.9%). Composite score penalizes low-quality entries.
    if _HAS_PINE_FILTERS and signals:
        try:
            from api_failover import fetch_klines as _pine_fetch_klines
            _pine_ohlcv_cache: dict = {}
            _pine_enriched = 0
            _pine_penalized = 0
            for _sig in signals:
                _sym = _sig.get("symbol", "")
                if _sym not in _pine_ohlcv_cache:
                    _kl = _pine_fetch_klines(_sym, "4h", 100)
                    if _kl:
                        _pine_ohlcv_cache[_sym] = {
                            "close": np.array([float(k[4]) for k in _kl]),
                            "high": np.array([float(k[2]) for k in _kl]),
                            "low": np.array([float(k[3]) for k in _kl]),
                            "volume": np.array([float(k[5]) for k in _kl]),
                        }
                    else:
                        _pine_ohlcv_cache[_sym] = None
                _ohlcv = _pine_ohlcv_cache.get(_sym)
                if _ohlcv is not None:
                    _sig = _pine_indicator_filter(_sig, _ohlcv)
                    _pine_enriched += 1
                    if not _sig.get("pine_filter_pass", True):
                        _pine_penalized += 1
                        # Penalize ML score by 15% for low pine composite
                        if "ml_score" in _sig:
                            _sig["ml_score"] = _sig["ml_score"] * 0.85
                        _sig["pine_penalty_applied"] = True
            print(f"  [PINE FILTERS] Enriched {_pine_enriched} signals, "
                  f"penalized {_pine_penalized} (low pine composite score)")
        except Exception as _pine_err:
            print(f"  [PINE FILTERS] Failed (non-fatal): {_pine_err}")

    # Confluence filtering: require 2+ indicator families to agree (feature-flagged)
    use_confluence = os.environ.get("ALPHA_CONFLUENCE", "0") == "1"
    if use_confluence and signals:
        try:
            from confluence_engine import ConfluenceEngine
            min_fam = int(os.environ.get("ALPHA_MIN_FAMILIES", "2"))
            ce = ConfluenceEngine(min_families=min_fam, time_window_hours=4.0)
            confluence_results = ce.process_signals(signals)
            print(f"  Confluence: {len(signals)} raw -> {len(confluence_results)} groups "
                  f"after {min_fam}+ family filter")
            # Mark approved signals with confluence metadata
            approved = set()
            for cs in confluence_results:
                for s in cs["contributing_signals"]:
                    s["confluence_score"] = cs["confluence_score"]
                    s["confluence_families"] = cs["family_count"]
                    s["confluence_strategies"] = cs["contributing_strategies"]
                    approved.add((s["strategy"], s["symbol"], s["signal_type"]))
            before_count = len(signals)
            signals = [s for s in signals
                       if (s["strategy"], s["symbol"], s["signal_type"]) in approved]
            print(f"  Confluence filter: {before_count} -> {len(signals)} signals passed")
        except Exception as e:
            print(f"  Warning: Confluence filtering failed, using all signals: {e}")

    # Log regime compatibility stats (Action 3.1)
    if signals:
        compat = sum(1 for s in signals if s.get("regime_compatible", True))
        incompat = len(signals) - compat
        print(f"  Regime-compatible: {compat} | Regime-mismatched: {incompat}")

    # Inject Fear & Greed index into each signal for ML feature extraction
    try:
        _fg_data = context.get("fear_greed", {}).get("data", [{}])
        _fg_index = int(_fg_data[0].get("value", 50)) if _fg_data else 50
    except (ValueError, TypeError, IndexError):
        _fg_index = 50
    for _sig in (signals or []):
        _sig["fear_greed_index"] = _fg_index

    # Step 5: Rank with ML, apply forward gate + regime penalty, and open picks
    print("[5/5] Ranking signals with ML (regime-penalized)...")
    ranked = rank_and_filter_signals(signals, ranker, db, market_data=data)
    print(f"  Signals after ML filter: {len(ranked)}")

    # Forward gate summary
    n_validated = sum(1 for s in ranked if s.get("forward_validated"))
    n_unvalidated = len(ranked) - n_validated
    if ranked:
        print(f"  [FORWARD GATE] {n_validated}/{len(ranked)} from validated strategies "
              f"({n_unvalidated} unvalidated -- still tracked, not blocked)")

    # -- Crypto Risk Gates: funding rate, regime, concentration, LOW_CONFIDENCE --
    if _HAS_CRYPTO_RISK_GATES and ranked:
        _pre_gate = len(ranked)
        _regime_info = context.get("regime", {}) if context else {}
        _open_picks_for_heat = db.get_open_picks() if db else []
        # Check portfolio heat before opening new picks
        if _is_portfolio_overheated and _is_portfolio_overheated(_open_picks_for_heat):
            print(f"  [CRYPTO GATE] Portfolio overheated ({_compute_portfolio_heat(_open_picks_for_heat):.1f}%) -- blocking new crypto picks")
            ranked = [s for s in ranked if s.get("category", "stock") not in ("crypto", "meme")]
        else:
            # Build strategy stats for gate decisions
            _strat_stats_for_gate = {}
            try:
                _all_closed_for_gate = db.get_closed_picks(limit=5000) if db else []
                from collections import defaultdict as _ddfg
                _ss_fg = _ddfg(lambda: {"won": 0, "total": 0})
                for _cp_fg in _all_closed_for_gate:
                    _sn = _cp_fg.get("strategy", "")
                    _ss_fg[_sn]["total"] += 1
                    if _cp_fg.get("status") == "WON":
                        _ss_fg[_sn]["won"] += 1
                for _sn, _sv in _ss_fg.items():
                    _strat_stats_for_gate[_sn] = {
                        "closed_count": _sv["total"],
                        "win_rate": _sv["won"] / max(_sv["total"], 1),
                    }
            except Exception as _e_fg:
                print(f"  [CRYPTO GATE] Warning: could not build strategy stats: {_e_fg}")

            _gated = []
            _blocked = 0
            for _sig in ranked:
                result = _apply_crypto_gates(
                    _sig,
                    regime_data=_regime_info,
                    funding_data=None,  # auto-fetch from Binance
                    active_picks=_open_picks_for_heat,
                    strategy_stats=_strat_stats_for_gate,
                )
                if result is not None:
                    _gated.append(result)
                else:
                    _blocked += 1
            ranked = _gated
        _post_gate = len(ranked)
        if _pre_gate > _post_gate:
            print(f"  [CRYPTO GATE] {_pre_gate - _post_gate} picks blocked/filtered ({_post_gate} remaining)")

    # -- Crypto ML Tuner: check if retrain is needed --
    if _HAS_CRYPTO_ML_TUNER and _should_force_retrain:
        try:
            _ml_meta_path = DATA_DIR / "meta_learner_model.json"
            _ml_meta = {}
            if _ml_meta_path.exists():
                with open(_ml_meta_path) as _f:
                    _ml_meta = json.load(_f)
            _closed_for_retrain = db.get_closed_picks(limit=5000) if db else []
            if _should_force_retrain(_ml_meta, _closed_for_retrain):
                print("  [ML TUNER] Force retrain recommended: model may be stale or underperforming")
        except Exception as _e_rt:
            print(f"  [ML TUNER] Warning: retrain check failed: {_e_rt}")

    # -- Strategy Leaderboard: rank strategies, apply confidence modifiers --
    _leaderboard_data = {}
    if _HAS_STRATEGY_LEADERBOARD and _update_leaderboard:
        try:
            _lb_regime = None
            if context and context.get("regime"):
                _lb_regime = str(context["regime"].get("regime", "")).upper() or None
            _leaderboard_data = _update_leaderboard(regime=_lb_regime) or {}
            if _leaderboard_data:
                _lb_top = len(_leaderboard_data.get("top_tier", []))
                _lb_proven = len(_leaderboard_data.get("proven", []))
                _lb_under = len(_leaderboard_data.get("underperforming", []))
                _lb_toxic = len(_leaderboard_data.get("toxic", []))
                print(f"  [LEADERBOARD] {_leaderboard_data.get('total_strategies', 0)} strategies ranked "
                      f"({_lb_top} top-tier, {_lb_proven} proven, {_lb_under} underperforming, {_lb_toxic} toxic)")
                if ranked and _apply_leaderboard:
                    ranked = _apply_leaderboard(ranked, _leaderboard_data)
        except Exception as _lb_err:
            print(f"  [LEADERBOARD] Warning: {_lb_err}")

    # -- Hard WR Gate: block strategies with <25% WR on 10+ closed trades --
    # This is a last-resort gate that catches any toxic strategy not already
    # in LOW_CONFIDENCE_STRATEGIES or HARD_KILL_STRATEGIES.
    if ranked and db:
        try:
            _wr_gate_closed = db.get_closed_picks(limit=5000)
            from collections import defaultdict as _dd_wrg
            _wr_gate_stats: dict[str, dict[str, int]] = _dd_wrg(lambda: {"won": 0, "total": 0})
            for _cp_wrg in _wr_gate_closed:
                _sn_wrg = _cp_wrg.get("strategy", "")
                if _sn_wrg:
                    _wr_gate_stats[_sn_wrg]["total"] += 1
                    if _cp_wrg.get("status") == "WON":
                        _wr_gate_stats[_sn_wrg]["won"] += 1
            _pre_wr_gate = len(ranked)
            _wr_blocked = []
            _wr_passed = []
            for _sig_wrg in ranked:
                _strat_wrg = _sig_wrg.get("strategy", "")
                _st_wrg = _wr_gate_stats.get(_strat_wrg, {})
                _total_wrg = _st_wrg.get("total", 0)
                if _total_wrg >= 10:
                    _wr_wrg = _st_wrg.get("won", 0) / _total_wrg
                    if _wr_wrg < 0.25:
                        _wr_blocked.append((_strat_wrg, _wr_wrg, _total_wrg))
                        continue
                _wr_passed.append(_sig_wrg)
            ranked = _wr_passed
            for _bname, _bwr, _btotal in _wr_blocked:
                print(f"  [HARD KILL] Blocked {_bname} -- {_bwr:.0%} WR on {_btotal} trades")
                logger.info("[HARD KILL] Blocked %s -- %.0f%% WR on %d trades", _bname, _bwr * 100, _btotal)
            if _pre_wr_gate > len(ranked):
                print(f"  [HARD WR GATE] {_pre_wr_gate - len(ranked)} picks blocked ({len(ranked)} remaining)")
        except Exception as _e_wrg:
            print(f"  [HARD WR GATE] Warning: could not apply WR gate: {_e_wrg}")

    # -- Direction Balance Guard: cap LONG/SHORT ratio by Fear & Greed regime --
    if _HAS_DIRECTION_GUARD and ranked:
        try:
            _open_picks_for_dir = db.get_open_picks() if db else []
            _fg_for_dir = {}
            # Reuse FGI from context if available
            try:
                _fg_ctx = context.get("fear_greed", {}).get("data", [{}])
                _fg_val = int(_fg_ctx[0].get("value", 50)) if _fg_ctx else 50
                _fg_for_dir = {"fgi": _fg_val}
            except (ValueError, TypeError, IndexError, AttributeError):
                pass  # enforce_direction_balance will fetch its own
            _pre_dir = len(ranked)
            ranked = _enforce_direction_balance(
                ranked,
                active_picks=_open_picks_for_dir,
                regime_data=_fg_for_dir,
            )
            _dir_capped = _pre_dir - len(ranked)
            if _dir_capped > 0:
                print(f"  [DIRECTION] {_dir_capped} picks capped by direction balance guard ({len(ranked)} remaining)")
        except Exception as _e_dir:
            print(f"  [DIRECTION] Warning: direction balance guard failed (non-fatal): {_e_dir}")

    opened = []
    if not args.dry_run and ranked:
        opened = open_new_picks(ranked, db, market_data=data, context=context)

    # Report
    elapsed = time.time() - start_time
    print_report(ranked, closed, opened, db, elapsed)

    # -- Export closed picks and strategy performance to JSON --------------
    # Ensures forward_trades / forward_wr are always up-to-date in JSON
    # and closed_picks.json is available for external consumers.
    try:
        all_closed = db.get_closed_picks(limit=5000)

        # Deduplicate by (strategy, symbol, entry_price, close_time[:16])
        _seen_keys: set[tuple] = set()
        deduped_closed: list[dict] = []
        _dupes_removed = 0
        for _cp in all_closed:
            _dedup_key = (
                _cp.get("strategy", ""),
                _cp.get("symbol", ""),
                str(_cp.get("entry_price", "")),
                (_cp.get("exit_date") or _cp.get("close_time") or "")[:16],
            )
            if _dedup_key in _seen_keys:
                _dupes_removed += 1
                continue
            _seen_keys.add(_dedup_key)
            deduped_closed.append(_cp)
        if _dupes_removed > 0:
            print(f"  [DEDUP] Removed {_dupes_removed} duplicate closed picks before writing JSON")

        closed_picks_path = DATA_DIR / "closed_picks.json"
        with open(closed_picks_path, "w", encoding="utf-8") as f:
            json.dump(_sanitize_for_json(deduped_closed), f, indent=2, default=str)
        print(f"  Saved {len(deduped_closed)} closed picks to {closed_picks_path}")

        # Update strategy_performance.json with forward_trades, forward_wr, and net_wr
        all_strategies = set(CRYPTO_STRATEGIES.keys()) | set(FOREX_STRATEGIES.keys()) | set(EQUITY_STRATEGIES.keys()) | set(ADVANCED_STRATEGIES.keys()) | set(KELTNER_EVOLVED_STRATEGIES.keys()) | set(SUPER_STRATEGIES.keys()) | set(SURVIVOR_STRATEGIES.keys()) | set(FUNDAMENTAL_VALUATION_STRATEGIES.keys()) | set(ADVANCED_QUANT_STRATEGIES.keys()) | set(ADVANCED_STATISTICAL_STRATEGIES.keys()) | set(PROVEN_EDGE_STRATEGIES.keys()) | set(CRYPTO_EDGE_STRATEGIES.keys()) | set(CONFLUENCE_V2_STRATEGIES.keys()) | set(COMMODITY_STRATEGIES.keys()) | set(FUTURES_STRATEGIES.keys()) | set(ETF_STRATEGIES.keys()) | set(BOND_STRATEGIES.keys())
        strat_perf = {}
        for strat_name in all_strategies:
            stats = db.compute_strategy_stats(strat_name)
            gross_wr = stats.get("win_rate", 0)
            # Compute net win rate after transaction costs
            avg_cost = 0.007  # 0.7% round-trip (crypto altcoin conservative default)
            avg_win_est = 0.05
            avg_loss_est = 0.03
            if stats.get("wins", 0) > 0 and stats.get("losses", 0) > 0:
                closed_strat = db.get_closed_picks(strat_name, limit=500)
                pnls = [p["pnl_pct"] for p in closed_strat if p.get("pnl_pct") is not None]
                wins_pnl = [p for p in pnls if p > 0]
                losses_pnl = [abs(p) for p in pnls if p <= 0]
                if wins_pnl and losses_pnl:
                    avg_win_est = sum(wins_pnl) / len(wins_pnl)
                    avg_loss_est = sum(losses_pnl) / len(losses_pnl)
            net_wr = compute_adjusted_win_rate(gross_wr, avg_win_est, avg_loss_est, avg_cost)
            strat_perf[strat_name] = {
                "closed_picks": stats.get("closed_picks", 0),
                "wins": stats.get("wins", 0),
                "losses": stats.get("losses", 0),
                "gross_win_rate": gross_wr,
                "net_win_rate": net_wr,
                "win_rate": gross_wr,  # backward compat
                "sharpe": stats.get("sharpe", 0),
                "profit_factor": stats.get("profit_factor", 0),
                "forward_trades": stats.get("closed_picks", 0),
                "forward_wr": gross_wr,
                "transaction_cost_est": avg_cost,
            }
        strat_perf_path = DATA_DIR / "strategy_performance.json"
        with open(strat_perf_path, "w") as f:
            json.dump(_sanitize_for_json(strat_perf), f, indent=2)
        print(f"  Updated strategy performance for {len(strat_perf)} strategies")
    except Exception as e:
        print(f"  Warning: Could not export closed picks / strategy performance: {e}")

    # Export tournament state (feature-flagged)
    try:
        use_tournament = os.environ.get("ALPHA_TOURNAMENT", "0") == "1"
        if use_tournament:
            from tournament_engine import TournamentEngine
            tournament_data = {}
            _db_path = str(DATA_DIR / "alpha.db")
            for pname in ["conservative", "moderate", "aggressive"]:
                te = TournamentEngine(_db_path, portfolio=pname)
                tournament_data[pname] = te.get_all_states()
            tournament_path = DATA_DIR / "tournament_state.json"
            with open(tournament_path, "w") as f:
                json.dump(_sanitize_for_json(tournament_data), f, indent=2, default=str)
            print(f"  Exported tournament state to {tournament_path}")
    except Exception as e:
        print(f"  Warning: Could not export tournament state: {e}")

    # Compute regime summary for snapshot (Action 3.1)
    regime_summary = {"trending": 0, "ranging": 0, "transitional": 0, "unknown": 0}
    regime_cache = compute_regime_cache(data, context)
    for sym, rinfo in regime_cache.items():
        r = rinfo.get("regime", "unknown")
        regime_summary[r] = regime_summary.get(r, 0) + 1

    # Save scan snapshot (includes forward gate + regime summary + transaction costs)
    scan_snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": VERSION,
        "strategy_count": STRATEGY_COUNT,
        "symbols_fetched": len(data),
        "raw_signals": len(signals),
        "filtered_signals": len(ranked),
        "picks_opened": len(opened),
        "picks_closed": len(closed),
        "ml_trained": ranker.is_trained,
        "elapsed_seconds": round(elapsed, 1),
        "forward_gate": {
            "validated_signals": n_validated,
            "unvalidated_signals": n_unvalidated,
            "min_trades": FORWARD_GATE_MIN_TRADES,
            "min_wr": FORWARD_GATE_MIN_WR,
        },
        "regime_detection": {
            "enabled": True,
            "method": "ADX_14 + volatility + Regime Sentinel",
            "thresholds": {"trending": ">= 25", "ranging": "<= 20"},
            "symbol_regimes": regime_summary,
            "signals_regime_compatible": sum(
                1 for s in ranked if s.get("regime_compatible", True)
            ),
            "signals_regime_mismatched": sum(
                1 for s in ranked if not s.get("regime_compatible", True)
            ),
            "regime_sentinel": context.get("regime_sentinel", {}),
        },
        "kill_switch_status": {
            "is_killed": _kill_switch_status.get("is_killed", False),
            "severity": _kill_switch_status.get("severity", "ok"),
            "recommended_action": _kill_switch_status.get("recommended_action", "none"),
            "kill_reason": _kill_switch_status.get("kill_reason"),
            "conditions_count": len(_kill_switch_status.get("conditions", [])),
            "checked_at": _kill_switch_status.get("checked_at", ""),
        },
        "transaction_costs": {
            "enabled": True,
            "position_sizing": "risk_based",
            "max_risk_per_trade": MAX_RISK_PER_TRADE,
            "max_allocation_per_pick": MAX_ALLOCATION_PER_PICK,
            "max_total_exposure": MAX_TOTAL_EXPOSURE,
            "max_correlated_exposure": MAX_CORRELATED_EXPOSURE,
            "cost_models": {
                name: f"{model['total_per_trade']*100:.2f}%"
                for name, model in COST_MODELS.items()
            },
        },
    }
    scan_path = DATA_DIR / "last_scan.json"
    with open(scan_path, "w") as f:
        json.dump(_sanitize_for_json(scan_snapshot), f, indent=2)

    # -- Hindsight Learner: run hourly check (non-blocking) -------------
    try:
        try:
            from alpha_engine.hindsight_learner import run_hourly_check
        except ImportError:
            from hindsight_learner import run_hourly_check
        run_hourly_check()
        print("  [hindsight_learner] hourly check completed")
    except ImportError:
        pass  # hindsight_learner module not available yet
    except Exception as e:
        print(f"  [hindsight_learner] skipped: {e}")

    # Export ALL open DB picks to active_picks.json (so portfolio trackers can read them)
    try:
        all_open = db.get_open_picks()
        active_export = []
        for p in all_open:
            pd = dict(p)
            # Merge extra_json fields into top-level
            ej = {}
            if pd.get("extra_json"):
                try:
                    ej = json.loads(pd["extra_json"])
                except Exception:
                    pass
            pd.update(ej)
            pd.pop("extra_json", None)
            # Skip picks with obviously broken entry prices
            _ep = float(pd.get("entry_price", 0) or 0)
            if _ep <= 0 or (_ep < 0.001 and pd.get("category") == "crypto"):
                continue
            # Inject strategy stats from closed_picks (strategy_performance.json gets overwritten by scanner)
            try:
                if not hasattr(open_new_picks, "_strat_stats"):
                    _cp_path = DATA_DIR / "closed_picks.json"
                    with open(_cp_path, encoding="utf-8") as _cpf:
                        _closed = json.load(_cpf)
                    from collections import defaultdict
                    _ss = defaultdict(lambda: {"w": 0, "l": 0, "t": 0})
                    for _cp in _closed:
                        if not isinstance(_cp, dict): continue
                        _sn = _cp.get("strategy", "")
                        if not _sn: continue
                        _ss[_sn]["t"] += 1
                        if str(_cp.get("status","")).upper() == "WON" or float(_cp.get("pnl_pct",0) or 0) > 0:
                            _ss[_sn]["w"] += 1
                        else:
                            _ss[_sn]["l"] += 1
                    open_new_picks._strat_stats = dict(_ss)
                _st = open_new_picks._strat_stats.get(pd.get("strategy", ""), {})
                if _st.get("t", 0) > 0:
                    pd["forward_trades"] = _st["t"]
                    pd["forward_wr"] = round(_st["w"] / _st["t"], 4)
                    pd["forward_validated"] = _st["t"] >= 4
            except Exception:
                pass
            # Always re-score with latest elite_scorer (DB stores stale/zero scores)
            try:
                result = compute_elite_score(pd)
                pd["elite_score"] = result["elite_score"]
                pd["elite_grade"] = result["elite_grade"]
                pd["elite_breakdown"] = result["elite_breakdown"]
            except Exception:
                pass
            # Stamp regime_at_entry from HMM regime data if missing
            if not pd.get("regime_at_entry"):
                try:
                    _hmm_path = DATA_DIR / "hmm_regime.json"
                    if _hmm_path.exists():
                        with open(_hmm_path, encoding="utf-8") as _hf:
                            _hmm = json.load(_hf)
                        pd["regime_at_entry"] = (_hmm.get("aggregate", {}).get("market_regime") or "UNKNOWN").upper()
                        pd["regime_timestamp"] = _hmm.get("generated_at", "")
                except Exception:
                    pd["regime_at_entry"] = "UNKNOWN"
            # --- WINNER INDICATOR SCORING (v1.1 -- reverse-engineered from 368 picks) ---
            # Adds msi, eqs, combined_score, risk_flags, portfolio assignment.
            # MSI Q4=74.4% WR, EQS Q4=78.9% WR, GAMMA portfolio=68.3% WR.
            if _HAS_WINNER_INDICATORS:
                try:
                    _wi = _score_winner_indicators(pd)
                    pd["msi"] = _wi["msi"]
                    pd["eqs"] = _wi["eqs"]
                    pd["combined_score"] = _wi["combined_score"]
                    pd["winner_portfolio"] = _wi["portfolio"]
                    pd["risk_blocked"] = _wi["blocked"]
                    pd["risk_flags"] = [f"{sev}: {msg}" for sev, msg in _wi.get("risk_flags", [])]
                except Exception:
                    pass

            # --- MINIMUM SCORE GATE (v2024.03.24) ---
            # Prevent unscored/low-quality picks from reaching paper trading.
            # Score tier analysis shows: 0-24 = 11% WR, 25-49 = 14% WR.
            # Only picks with elite_score >= 25 should be tracked.
            _pick_score = float(pd.get("elite_score", pd.get("score", 0)) or 0)
            if _pick_score < 25:
                logger.info(
                    "BLOCKED %s %s from active export: score %.0f < 25 minimum",
                    pd.get("strategy", "?"), pd.get("symbol", "?"), _pick_score,
                )
                continue
            active_export.append(pd)
        # Stamp kill switch status onto each active pick for downstream consumers
        _ks_active = _kill_switch_status.get("is_killed", False)
        _ks_severity = _kill_switch_status.get("severity", "ok")
        for _ap in active_export:
            _ap["kill_switch_active"] = _ks_active
            _ap["kill_switch_severity"] = _ks_severity
        active_export = sanitize_active_picks(active_export, "alpha_engine_scanner")
        # --- BOOK-LEVEL DIRECTION-CONFLICT RECONCILER (env-gated, shadow-first) ---
        # Removes delta-cancelling opposing-direction pick pairs (same symbol
        # carrying both LONG and SHORT). Hygiene fix per
        # reports/opposing_legs_finding_2026-05-18.md — NOT an edge claim.
        # DIRECTION_CONFLICT_RECONCILER unset/"0" (default) = SHADOW: log the
        # would-be drops, leave the book unchanged. "1"/"true"/"yes"/"on" =
        # ENFORCE: remove the dropped picks. Fail-open: any error -> book
        # unchanged.
        try:
            from alpha_engine.conflict_reconciler import (
                reconcile_direction_conflicts as _reconcile_conflicts,
                summarize as _summarize_conflicts,
            )
            _recon_kept, _recon_dropped = _reconcile_conflicts(active_export)
            if _recon_dropped:
                _recon_flag = str(
                    os.environ.get("DIRECTION_CONFLICT_RECONCILER", "0") or "0"
                ).strip().lower()
                _recon_on = _recon_flag in ("1", "true", "yes", "on")
                _recon_msg = _summarize_conflicts(_recon_dropped)
                if _recon_on:
                    active_export = _recon_kept
                    print(f"  [conflict_reconciler] ENFORCE: {_recon_msg}")
                else:
                    print(f"  [conflict_reconciler] SHADOW (no change): would drop {_recon_msg}")
        except Exception as _recon_err:
            # Fail-open: reconciler must never block the active-book export.
            print(f"  [conflict_reconciler] skipped (fail-open): {_recon_err}")
        active_path = DATA_DIR / "active_picks.json"
        with open(active_path, "w", encoding="utf-8") as f:
            json.dump(active_export, f, indent=2, ensure_ascii=False, default=str)
        print(f"  Exported {len(active_export)} open picks to active_picks.json"
              f"{' [KILL SWITCH ACTIVE]' if _ks_active else ''}")
    except Exception as _exp_err:
        print(f"  [WARN] active_picks export failed: {_exp_err}")

    # -- Recommended Portfolio: generate balanced portfolio from active picks --
    try:
        try:
            from alpha_engine.generate_recommended_portfolio import generate_recommended_portfolio
        except ImportError:
            from generate_recommended_portfolio import generate_recommended_portfolio
        generate_recommended_portfolio()
        print("  [recommended_portfolio] generation completed")
    except ImportError:
        pass  # generate_recommended_portfolio module not available yet
    except Exception as e:
        print(f"  [recommended_portfolio] skipped: {e}")

    # -- Equity Tracker: record portfolio snapshot for equity curve --
    try:
        try:
            from alpha_engine.equity_tracker import record_snapshot as _eq_snapshot
        except ImportError:
            from equity_tracker import record_snapshot as _eq_snapshot
        _eq_result = _eq_snapshot()
        if _eq_result:
            print(f"  [equity_tracker] snapshot recorded: ${_eq_result['equity']:,.2f} (dd: {_eq_result['drawdown_pct']:+.2f}%)")
        else:
            print("  [equity_tracker] skipped: no portfolio files found")
    except Exception as _eq_err:
        print(f"  [equity_tracker] skipped: {_eq_err}")

    db.close()
    print(f"\nDone. Scan saved to {scan_path}")


if __name__ == "__main__":
    main()

    # ── fail-open guard ────────────────────────────────────────────────────
    # Stop the scanner from exiting GitHub Actions GREEN on a data-provider
    # outage. main() already sys.exit(1)s on a total fetch failure (empty
    # data dict); this catches the partial-outage case (e.g. yfinance returns
    # <50% of requested symbols) which otherwise passes silently and corrupts
    # the audit ledger with phantom-healthy status. Mirrors the ratio logic
    # in etf_scanner.py / bond_scanner.py. Resolver-fix Step 2.
    # Skipped for --train-ml / --status runs (scan_ran stays False).
    if LAST_RUN_DIAGNOSTICS.get("scan_ran"):
        _requested = max(1, LAST_RUN_DIAGNOSTICS["symbols_requested"])
        _loaded = LAST_RUN_DIAGNOSTICS["symbols_loaded"]
        _ratio = _loaded / _requested
        if _ratio < 0.5:
            print(f"::error::DATA FETCH FAILURE — only {_loaded}/{_requested} "
                  f"symbols loaded (yfinance/failover degraded); refusing to "
                  f"exit green on missing data")
            sys.exit(1)
        if LAST_RUN_DIAGNOSTICS["raw_signals"] == 0:
            print(f"::warning::Scanner produced 0 raw signals on healthy data "
                  f"({_loaded}/{_requested} symbols loaded) — real-empty "
                  f"market, not a data failure")