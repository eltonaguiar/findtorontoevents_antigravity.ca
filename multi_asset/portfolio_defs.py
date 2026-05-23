#!/usr/bin/env python3
"""
MULTI-ASSET PORTFOLIO DEFINITIONS — Single Source of Truth
============================================================
Institutional-quality strategy definitions across all asset classes.

Sections:
    1. STRATEGY_REGISTRY     — Every strategy with metadata, rules, backtest status
    2. ASSET_CLASS_CONFIGS   — Per-class symbol universes, sector maps, risk params
    3. RISK_PROFILES         — Conservative / Moderate / Aggressive envelopes
    4. FAILOVER_API_PRIORITY — Ordered data-provider failover chain
    5. QA_CHECKS             — Data-quality validation rules
    6. PORTFOLIOS            — 16 production portfolios (legacy compat)
    7. Helper functions
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

# ---------------------------------------------------------------------------
# 1. STRATEGY_REGISTRY — Canonical strategy catalogue
# ---------------------------------------------------------------------------
STRATEGY_REGISTRY: dict[str, dict[str, Any]] = {
    # ------------------------------------------------------------------
    # MEAN REVERSION
    # ------------------------------------------------------------------
    "connors_rsi2": {
        "name": "Connors RSI-2 Mean Reversion",
        "asset_classes": ["stock", "futures", "etf"],
        "expected_wr": 0.757,
        "expected_sharpe": 4.84,
        "data_requirements": ["daily_ohlcv"],
        "entry_rules": (
            "RSI(2) < 5 on daily close while RSI(14) > 50 (uptrend filter). "
            "Connors RSI composite (percentile rank of streak + RSI-2 + ROC rank) "
            "below 10."
        ),
        "exit_rules": (
            "Close above SMA(5) or after max_hold_days. "
            "Hard stop at 1.5x ATR(14) below entry."
        ),
        "position_sizing": "Fixed fractional 2% risk per trade",
        "backtest_status": "proven",
        "hyperopt_optimal_params": {
            "rsi_period": 2,
            "rsi_entry": 5,
            "sma_exit_period": 5,
            "trend_filter_period": 200,
        },
        "references": [
            "Connors & Alvarez, 'Short Term Trading Strategies That Work', 2008",
            "Internal backtest: SPY 2005-2024, p=6e-6",
        ],
    },
    "mean_reversion_bollinger": {
        "name": "Bollinger Band Mean Reversion",
        "asset_classes": ["stock", "futures", "forex", "etf"],
        "expected_wr": 0.62,
        "expected_sharpe": 1.80,
        "data_requirements": ["daily_ohlcv"],
        "entry_rules": (
            "Close below lower Bollinger Band (20,2) AND RSI(14) < 30. "
            "Volume must be > 1.2x 20-day average (capitulation confirm)."
        ),
        "exit_rules": (
            "Close above SMA(20) or touch upper BB. "
            "Time stop at max_hold_days. Hard stop at 2x ATR below entry."
        ),
        "position_sizing": "Fixed fractional 1.5-2% risk per trade",
        "backtest_status": "proven",
        "hyperopt_optimal_params": {
            "bb_period": 20,
            "bb_std": 2.0,
            "rsi_period": 14,
            "rsi_threshold": 30,
        },
        "references": [
            "Bollinger, 'Bollinger on Bollinger Bands', 2001",
        ],
    },

    # ------------------------------------------------------------------
    # TREND FOLLOWING
    # ------------------------------------------------------------------
    "ema_stack_momentum": {
        "name": "EMA Stack Trend Following",
        "asset_classes": ["stock", "futures", "etf"],
        "expected_wr": 0.55,
        "expected_sharpe": 1.60,
        "data_requirements": ["daily_ohlcv"],
        "entry_rules": (
            "EMA(9) > EMA(21) > EMA(50) > EMA(200) for longs (reverse for shorts). "
            "ADX(14) > 25 to confirm trending regime. Volume > 20-day SMA."
        ),
        "exit_rules": (
            "EMA(9) crosses below EMA(21) or ADX drops below 20. "
            "Trailing stop at 2.5x ATR(14)."
        ),
        "position_sizing": "Fixed fractional 2% risk per trade",
        "backtest_status": "proven",
        "hyperopt_optimal_params": {
            "fast_ema": 9,
            "mid_ema": 21,
            "slow_ema": 50,
            "trend_ema": 200,
            "adx_threshold": 25,
        },
        "references": [
            "Covel, 'Trend Following', 5th ed., 2017",
        ],
    },
    "breakout_atr": {
        "name": "ATR Volatility Breakout",
        "asset_classes": ["stock", "penny", "etf"],
        "expected_wr": 0.52,
        "expected_sharpe": 1.45,
        "data_requirements": ["daily_ohlcv"],
        "entry_rules": (
            "20-day high breakout with ATR(14) expansion > 1.5x its 20-day SMA. "
            "Volume must be > 2x 20-day average on breakout bar."
        ),
        "exit_rules": (
            "Trailing stop at 2x ATR(14). Time stop at max_hold_days. "
            "Close below 10-day low for exit."
        ),
        "position_sizing": "Fixed fractional 1.5-2% risk per trade",
        "backtest_status": "proven",
        "hyperopt_optimal_params": {
            "breakout_period": 20,
            "atr_expansion_factor": 1.5,
            "volume_multiplier": 2.0,
            "trailing_atr_mult": 2.0,
        },
        "references": [
            "Keltner channel expansion variant (Chester Keltner, 1960)",
        ],
    },

    # ------------------------------------------------------------------
    # CARRY / YIELD
    # ------------------------------------------------------------------
    "carry_momentum": {
        "name": "FX Carry Trade with Momentum Filter",
        "asset_classes": ["forex"],
        "expected_wr": 0.58,
        "expected_sharpe": 1.30,
        "data_requirements": ["daily_ohlcv", "interest_rates"],
        "entry_rules": (
            "Long high-yield currency vs low-yield when 1M momentum confirms direction. "
            "Interest rate differential > 150 bps. EMA(50) slope positive."
        ),
        "exit_rules": (
            "Momentum reversal (1M return turns negative) or VIX > 30 (risk-off). "
            "Hard stop at 2x ATR(14)."
        ),
        "position_sizing": "Fixed fractional 1% risk (forex leverage adjustment)",
        "backtest_status": "proven",
        "hyperopt_optimal_params": {
            "min_rate_diff_bps": 150,
            "momentum_lookback": 21,
            "risk_off_vix": 30,
        },
        "references": [
            "Lustig, Roussanov & Verdelhan, 'Common Risk Factors in Currency Markets', RFS 2011",
        ],
    },
    "sovereign_yield_spread": {
        "name": "Sovereign Yield Spread Premium",
        "asset_classes": ["forex"],
        "expected_wr": 0.56,
        "expected_sharpe": 1.20,
        "data_requirements": ["daily_ohlcv", "sovereign_yields"],
        "entry_rules": (
            "Model forward premium/discount from real 2Y sovereign yield spreads. "
            "Enter when spread widens beyond 1-sigma from 60-day mean. "
            "Trend filter: price above 50-day SMA."
        ),
        "exit_rules": (
            "Spread mean-reverts to within 0.5-sigma or max_hold_days. "
            "Hard stop at 1.5x ATR(14)."
        ),
        "position_sizing": "Fixed fractional 1.5% risk per trade",
        "backtest_status": "testing",
        "hyperopt_optimal_params": {
            "spread_lookback": 60,
            "entry_sigma": 1.0,
            "exit_sigma": 0.5,
        },
        "references": [
            "Engel, 'Exchange Rates and Interest Parity', Handbook of Intl Econ, 2014",
        ],
    },

    # ------------------------------------------------------------------
    # VOLATILITY / VIX
    # ------------------------------------------------------------------
    "vix_spike_reversal": {
        "name": "VIX Spike Mean Reversion",
        "asset_classes": ["etf", "futures"],
        "expected_wr": 0.65,
        "expected_sharpe": 2.10,
        "data_requirements": ["daily_ohlcv", "vix"],
        "entry_rules": (
            "VIX spikes > 20% in a single day AND then closes below prior day's high "
            "(reversal candle). Rotate from defensive (TLT/GLD) into risk (SPY/QQQ)."
        ),
        "exit_rules": (
            "VIX drops below 20-day SMA or 15 days elapsed. "
            "Hard stop if VIX makes new high above spike level."
        ),
        "position_sizing": "Fixed fractional 2% risk per trade",
        "backtest_status": "proven",
        "hyperopt_optimal_params": {
            "vix_spike_pct": 0.20,
            "hold_days_max": 15,
        },
        "references": [
            "Whaley, 'The Investor Fear Gauge', JFE 2000",
        ],
    },

    # ------------------------------------------------------------------
    # MACRO / REGIME
    # ------------------------------------------------------------------
    "macro_factor_regime": {
        "name": "Macro Regime Switching Allocator",
        "asset_classes": ["etf"],
        "expected_wr": 0.60,
        "expected_sharpe": 1.50,
        "data_requirements": ["daily_ohlcv", "yield_curve", "fed_funds_prob"],
        "entry_rules": (
            "Classify regime from 2Y/10Y spread + Fed funds futures probabilities: "
            "expansion (SPY), contraction (TLT+GLD), stagflation (GLD+BIL), "
            "recovery (SPY+IWM). Rebalance monthly or on regime change."
        ),
        "exit_rules": (
            "Regime change triggers rebalance. Max allocation drift of 5% before "
            "forced rebalance. 45-day max hold per position."
        ),
        "position_sizing": "Equal weight within regime bucket, 2% total risk",
        "backtest_status": "testing",
        "hyperopt_optimal_params": {
            "yield_curve_threshold": 0.0,
            "rebalance_drift_pct": 0.05,
        },
        "references": [
            "Ilmanen, 'Expected Returns', Wiley 2011",
            "Dalio, 'All Weather' framework",
        ],
    },

    # ------------------------------------------------------------------
    # SENTIMENT / COT
    # ------------------------------------------------------------------
    "cot_sentiment_fade": {
        "name": "COT Speculator Fader",
        "asset_classes": ["futures"],
        "expected_wr": 0.58,
        "expected_sharpe": 1.40,
        "data_requirements": ["daily_ohlcv", "cot_report"],
        "entry_rules": (
            "CFTC COT non-commercial net position reaches 90th percentile "
            "(3-year lookback) = fade. Enter on weekly close reversal candle."
        ),
        "exit_rules": (
            "Net positioning returns to 50th percentile or 21 days elapsed. "
            "Hard stop at 2.5x ATR(14)."
        ),
        "position_sizing": "Fixed fractional 1.5% risk per trade",
        "backtest_status": "testing",
        "hyperopt_optimal_params": {
            "percentile_threshold": 90,
            "lookback_years": 3,
            "exit_percentile": 50,
        },
        "references": [
            "CFTC Commitments of Traders, weekly release",
            "De Roon, Nijman & Veld, 'Hedging Pressure Effects in Futures Markets', JF 2000",
        ],
    },

    # ------------------------------------------------------------------
    # FLOW / DARK POOL
    # ------------------------------------------------------------------
    "dark_pool_options_flow": {
        "name": "Dark Pool & Options Flow",
        "asset_classes": ["stock"],
        "expected_wr": 0.60,
        "expected_sharpe": 1.70,
        "data_requirements": ["daily_ohlcv", "options_flow", "dark_pool_prints"],
        "entry_rules": (
            "Unusual options volume > 3x 20-day average on single-leg calls. "
            "Dark pool block print > $1M on bid side. Enter on next open."
        ),
        "exit_rules": (
            "Options expiry - 5 days or target hit at 3.5x ATR. "
            "Hard stop at 1.5x ATR below entry."
        ),
        "position_sizing": "Fixed fractional 2% risk per trade",
        "backtest_status": "testing",
        "hyperopt_optimal_params": {
            "options_volume_mult": 3.0,
            "dark_pool_min_usd": 1_000_000,
        },
        "references": [
            "Hu, 'Dark Pool Trading and Information Acquisition', RFS 2023",
        ],
    },

    # ------------------------------------------------------------------
    # SHORT SQUEEZE
    # ------------------------------------------------------------------
    "short_interest_squeeze": {
        "name": "Short Squeeze Predictor",
        "asset_classes": ["penny", "stock"],
        "expected_wr": 0.48,
        "expected_sharpe": 1.80,
        "data_requirements": ["daily_ohlcv", "short_interest", "borrow_rate"],
        "entry_rules": (
            "Short interest > 20% of float AND days-to-cover > 5 AND "
            "borrow fee > 30% annualized. Enter on volume breakout > 3x average."
        ),
        "exit_rules": (
            "Take profit at 6x ATR or 50% gain. "
            "Hard stop at 2.5x ATR below entry. Time stop at 14 days."
        ),
        "position_sizing": "Fixed fractional 1.5% risk (high vol asset adjustment)",
        "backtest_status": "testing",
        "hyperopt_optimal_params": {
            "si_pct_threshold": 0.20,
            "dtc_threshold": 5,
            "borrow_fee_threshold": 0.30,
            "volume_breakout_mult": 3.0,
        },
        "references": [
            "Engelberg, Reed & Ringgenberg, 'How are Shorts Informed?', JFE 2012",
        ],
    },

    # ------------------------------------------------------------------
    # ON-CHAIN / CRYPTO
    # ------------------------------------------------------------------
    "onchain_whale_tracking": {
        "name": "On-Chain Whale & Macro Composite",
        "asset_classes": ["crypto"],
        "expected_wr": 0.60,
        "expected_sharpe": 1.90,
        "data_requirements": [
            "daily_ohlcv", "exchange_netflow", "stablecoin_supply",
            "miner_revenue", "fear_greed_index",
        ],
        "entry_rules": (
            "Composite score from: MVRV < 1.0 (undervalued), exchange netflow negative "
            "(accumulation), stablecoin supply ratio rising, Fear & Greed < 20. "
            "Require 3 of 4 signals aligned."
        ),
        "exit_rules": (
            "MVRV > 3.5 (overvalued) or Fear & Greed > 80 or 20 days elapsed. "
            "Trailing stop at 2x ATR(14)."
        ),
        "position_sizing": "Fixed fractional 2% risk per trade",
        "backtest_status": "testing",
        "hyperopt_optimal_params": {
            "mvrv_buy": 1.0,
            "mvrv_sell": 3.5,
            "fg_buy": 20,
            "fg_sell": 80,
            "min_signals": 3,
        },
        "references": [
            "Willy Woo, NVT ratio (2017)",
            "Glassnode Academy, MVRV methodology",
            "Internal alpha_engine onchain_strategies.py",
        ],
    },

    # ------------------------------------------------------------------
    # MUTUAL FUND TACTICAL
    # ------------------------------------------------------------------
    "tactical_fund_rotation": {
        "name": "Tactical Mutual Fund Rotation",
        "asset_classes": ["mutual_fund"],
        "expected_wr": 0.58,
        "expected_sharpe": 1.25,
        "data_requirements": ["daily_nav", "fund_flows"],
        "entry_rules": (
            "Rank Vanguard/iShares core funds by 3M momentum + 1M reversal. "
            "Top 3 funds get equal allocation. Rebalance monthly."
        ),
        "exit_rules": (
            "Fund drops from top-3 ranking at next monthly rebalance. "
            "Emergency exit if drawdown exceeds 8% from peak NAV."
        ),
        "position_sizing": "Equal weight across top-3, max 33% per fund",
        "backtest_status": "research",
        "hyperopt_optimal_params": {
            "momentum_lookback": 63,
            "reversal_lookback": 21,
            "top_n": 3,
            "rebalance_freq_days": 21,
        },
        "references": [
            "Jegadeesh & Titman, 'Returns to Buying Winners', JF 1993",
            "Antonacci, 'Dual Momentum Investing', 2014",
        ],
    },
}

# ---------------------------------------------------------------------------
# 2. ASSET_CLASS_CONFIGS — Symbol universes, sector maps, class-level params
# ---------------------------------------------------------------------------
ASSET_CLASS_CONFIGS: dict[str, dict[str, Any]] = {
    # ------------------------------------------------------------------
    # STOCKS — Mega-cap + large-cap universe
    # ------------------------------------------------------------------
    "stock": {
        "description": "US large-cap equities",
        "universe": [
            # Technology
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "CRM", "ORCL",
            # Financials
            "JPM", "V", "MA", "GS", "BAC",
            # Healthcare
            "UNH", "JNJ", "LLY", "PFE",
            # Consumer / Industrial
            "WMT", "COST", "HD", "CAT",
        ],
        "sector_groupings": {
            "technology": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "CRM", "ORCL"],
            "financials": ["JPM", "V", "MA", "GS", "BAC"],
            "healthcare": ["UNH", "JNJ", "LLY", "PFE"],
            "consumer_industrial": ["WMT", "COST", "HD", "CAT"],
        },
        "risk_params": {
            "default_stop_atr_mult": 1.5,
            "max_sector_exposure_pct": 40,
            "min_avg_volume": 1_000_000,
            "min_market_cap_b": 10,
            "max_correlation_within_portfolio": 0.80,
        },
        "trading_hours": "09:30-16:00 ET",
        "data_source": "yfinance",
    },

    # ------------------------------------------------------------------
    # PENNY STOCKS — High-vol sub-$20 names
    # ------------------------------------------------------------------
    "penny": {
        "description": "Sub-$20 high-volatility equities with strict filters",
        "universe": [
            "SOFI", "PLTR", "NIO", "MARA", "RIOT", "IONQ",
            "GME", "AMC", "CVNA", "BBBY", "LCID", "RIVN",
            "PLUG", "FCEL", "DKNG", "SKLZ",
        ],
        "sector_groupings": {
            "fintech": ["SOFI"],
            "ai_data": ["PLTR", "IONQ"],
            "ev_energy": ["NIO", "LCID", "RIVN", "PLUG", "FCEL"],
            "crypto_mining": ["MARA", "RIOT"],
            "meme_retail": ["GME", "AMC", "CVNA", "BBBY"],
            "gaming_entertainment": ["DKNG", "SKLZ"],
        },
        "risk_params": {
            "default_stop_atr_mult": 2.5,
            "max_sector_exposure_pct": 30,
            "min_avg_volume": 5_000_000,
            "max_price": 20.0,
            "min_price": 0.50,
            "max_spread_pct": 1.0,
            "max_correlation_within_portfolio": 0.70,
        },
        "volume_filters": {
            "min_daily_dollar_volume": 10_000_000,
            "breakout_volume_mult": 2.0,
            "reject_if_avg_vol_below": 2_000_000,
        },
        "trading_hours": "09:30-16:00 ET",
        "data_source": "yfinance",
    },

    # ------------------------------------------------------------------
    # ETFs — All 11 SPDR sectors + commodity + bond + international
    # ------------------------------------------------------------------
    "etf": {
        "description": "Sector SPDRs, commodity, bond, and broad market ETFs",
        "universe": [
            # Broad market
            "SPY", "QQQ", "IWM", "DIA",
            # 11 SPDR sector ETFs
            "XLB",   # Materials
            "XLC",   # Communication Services
            "XLE",   # Energy
            "XLF",   # Financials
            "XLI",   # Industrials
            "XLK",   # Technology
            "XLP",   # Consumer Staples
            "XLRE",  # Real Estate
            "XLU",   # Utilities
            "XLV",   # Health Care
            "XLY",   # Consumer Discretionary
            # Commodities
            "GLD",   # Gold
            "SLV",   # Silver
            "USO",   # Oil
            "DBA",   # Agriculture
            # Bonds
            "TLT",   # 20+ Year Treasury
            "IEF",   # 7-10 Year Treasury
            "HYG",   # High Yield Corporate
            "LQD",   # Investment Grade Corporate
            "BIL",   # 1-3 Month T-Bill (cash proxy)
            "TIP",   # TIPS (inflation-protected)
            # International
            "EFA",   # Developed ex-US
            "EEM",   # Emerging Markets
            "FXI",   # China
            # Volatility
            "VIXY",  # VIX Short-Term Futures
            # Dollar
            "UUP",   # US Dollar Bullish
        ],
        "sector_groupings": {
            "broad_market": ["SPY", "QQQ", "IWM", "DIA"],
            "spdr_sectors": [
                "XLB", "XLC", "XLE", "XLF", "XLI", "XLK",
                "XLP", "XLRE", "XLU", "XLV", "XLY",
            ],
            "commodities": ["GLD", "SLV", "USO", "DBA"],
            "fixed_income": ["TLT", "IEF", "HYG", "LQD", "BIL", "TIP"],
            "international": ["EFA", "EEM", "FXI"],
            "alternatives": ["VIXY", "UUP"],
        },
        "risk_params": {
            "default_stop_atr_mult": 2.0,
            "max_sector_exposure_pct": 35,
            "min_avg_volume": 500_000,
            "max_correlation_within_portfolio": 0.85,
        },
        "trading_hours": "09:30-16:00 ET",
        "data_source": "yfinance",
    },

    # ------------------------------------------------------------------
    # FUTURES — Major contracts with margin requirements
    # ------------------------------------------------------------------
    "futures": {
        "description": "CME/CBOT/NYMEX/COMEX futures contracts",
        "universe": [
            "ES=F",   # E-mini S&P 500
            "NQ=F",   # E-mini Nasdaq 100
            "YM=F",   # E-mini Dow
            "RTY=F",  # E-mini Russell 2000
            "CL=F",   # WTI Crude Oil
            "GC=F",   # Gold
            "SI=F",   # Silver
            "ZN=F",   # 10-Year Treasury Note
            "ZB=F",   # 30-Year Treasury Bond
            "ZC=F",   # Corn
            "ZS=F",   # Soybeans
            "ZW=F",   # Wheat
            "NG=F",   # Natural Gas
            "HG=F",   # Copper
        ],
        "contract_specs": {
            "ES=F":  {"exchange": "CME",   "tick_size": 0.25, "point_value": 50,    "margin_initial": 12_650, "margin_maintenance": 11_500},
            "NQ=F":  {"exchange": "CME",   "tick_size": 0.25, "point_value": 20,    "margin_initial": 17_600, "margin_maintenance": 16_000},
            "YM=F":  {"exchange": "CBOT",  "tick_size": 1.0,  "point_value": 5,     "margin_initial": 9_900,  "margin_maintenance": 9_000},
            "RTY=F": {"exchange": "CME",   "tick_size": 0.10, "point_value": 50,    "margin_initial": 6_600,  "margin_maintenance": 6_000},
            "CL=F":  {"exchange": "NYMEX", "tick_size": 0.01, "point_value": 1000,  "margin_initial": 7_260,  "margin_maintenance": 6_600},
            "GC=F":  {"exchange": "COMEX", "tick_size": 0.10, "point_value": 100,   "margin_initial": 10_230, "margin_maintenance": 9_300},
            "SI=F":  {"exchange": "COMEX", "tick_size": 0.005,"point_value": 5000,  "margin_initial": 10_450, "margin_maintenance": 9_500},
            "ZN=F":  {"exchange": "CBOT",  "tick_size": 0.015625, "point_value": 1000, "margin_initial": 2_200, "margin_maintenance": 2_000},
            "ZB=F":  {"exchange": "CBOT",  "tick_size": 0.03125,  "point_value": 1000, "margin_initial": 4_400, "margin_maintenance": 4_000},
            "ZC=F":  {"exchange": "CBOT",  "tick_size": 0.25, "point_value": 50,    "margin_initial": 1_650,  "margin_maintenance": 1_500},
            "ZS=F":  {"exchange": "CBOT",  "tick_size": 0.25, "point_value": 50,    "margin_initial": 2_475,  "margin_maintenance": 2_250},
            "ZW=F":  {"exchange": "CBOT",  "tick_size": 0.25, "point_value": 50,    "margin_initial": 1_925,  "margin_maintenance": 1_750},
            "NG=F":  {"exchange": "NYMEX", "tick_size": 0.001,"point_value": 10000, "margin_initial": 4_400,  "margin_maintenance": 4_000},
            "HG=F":  {"exchange": "COMEX", "tick_size": 0.0005,"point_value": 25000,"margin_initial": 5_500,  "margin_maintenance": 5_000},
        },
        "sector_groupings": {
            "equity_index": ["ES=F", "NQ=F", "YM=F", "RTY=F"],
            "energy": ["CL=F", "NG=F"],
            "metals": ["GC=F", "SI=F", "HG=F"],
            "fixed_income": ["ZN=F", "ZB=F"],
            "agriculture": ["ZC=F", "ZS=F", "ZW=F"],
        },
        "risk_params": {
            "default_stop_atr_mult": 2.0,
            "max_sector_exposure_pct": 40,
            "max_notional_per_contract": 500_000,
            "max_correlation_within_portfolio": 0.75,
        },
        "trading_hours": "18:00-17:00 ET (nearly 23h)",
        "data_source": "yfinance",
    },

    # ------------------------------------------------------------------
    # FOREX — Major + cross pairs with carry data
    # ------------------------------------------------------------------
    "forex": {
        "description": "G10 FX major and cross pairs",
        "universe": [
            "EURUSD=X", "USDJPY=X", "GBPUSD=X", "AUDUSD=X", "NZDUSD=X",
            "USDCAD=X", "USDCHF=X", "EURGBP=X", "EURJPY=X", "GBPJPY=X",
            "AUDJPY=X",
        ],
        "carry_data": {
            # Approximate overnight swap rates (annualized) — updated periodically
            "EURUSD=X": {"long_swap_pct": -2.8, "short_swap_pct": 1.2},
            "USDJPY=X": {"long_swap_pct": 4.5,  "short_swap_pct": -6.0},
            "GBPUSD=X": {"long_swap_pct": -1.5, "short_swap_pct": 0.3},
            "AUDUSD=X": {"long_swap_pct": 1.0,  "short_swap_pct": -2.5},
            "NZDUSD=X": {"long_swap_pct": 1.2,  "short_swap_pct": -2.8},
            "USDCAD=X": {"long_swap_pct": -0.5, "short_swap_pct": -0.8},
            "USDCHF=X": {"long_swap_pct": 3.0,  "short_swap_pct": -4.5},
            "EURGBP=X": {"long_swap_pct": -1.8, "short_swap_pct": 0.5},
            "EURJPY=X": {"long_swap_pct": 3.5,  "short_swap_pct": -5.0},
            "GBPJPY=X": {"long_swap_pct": 5.0,  "short_swap_pct": -7.0},
            "AUDJPY=X": {"long_swap_pct": 4.0,  "short_swap_pct": -6.5},
        },
        "sector_groupings": {
            "dollar_majors": ["EURUSD=X", "USDJPY=X", "GBPUSD=X", "USDCAD=X", "USDCHF=X"],
            "commodity_fx": ["AUDUSD=X", "NZDUSD=X"],
            "crosses": ["EURGBP=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X"],
        },
        "risk_params": {
            "default_stop_atr_mult": 1.5,
            "max_pair_exposure": 2,
            "max_same_base_exposure": 3,
            "default_leverage": 20,
            "max_correlation_within_portfolio": 0.80,
        },
        "pip_values": {
            "EURUSD=X": 0.0001, "USDJPY=X": 0.01, "GBPUSD=X": 0.0001,
            "AUDUSD=X": 0.0001, "NZDUSD=X": 0.0001, "USDCAD=X": 0.0001,
            "USDCHF=X": 0.0001, "EURGBP=X": 0.0001, "EURJPY=X": 0.01,
            "GBPJPY=X": 0.01,   "AUDJPY=X": 0.01,
        },
        "trading_hours": "24h Sun 17:00 - Fri 17:00 ET",
        "data_source": "yfinance",
    },

    # ------------------------------------------------------------------
    # CRYPTO — References alpha_engine configs; minimal duplication
    # ------------------------------------------------------------------
    "crypto": {
        "description": "Cryptocurrency — see alpha_engine/ for full strategy configs",
        "universe": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT"],
        "sector_groupings": {
            "layer1": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT"],
            "defi": [],
            "meme": [],
        },
        "risk_params": {
            "default_stop_atr_mult": 2.0,
            "max_single_asset_pct": 30,
            "max_correlation_within_portfolio": 0.75,
        },
        "symbol_normalization": {
            "BTC-USD": "BTCUSDT",
            "BTCUSD": "BTCUSDT",
            "ETH-USD": "ETHUSDT",
            "ETHUSD": "ETHUSDT",
            "SOL-USD": "SOLUSDT",
            "SOLUSD": "SOLUSDT",
        },
        "trading_hours": "24/7",
        "data_source": "alpha_engine",
        "alpha_engine_ref": "alpha_engine/scanner.py",
    },

    # ------------------------------------------------------------------
    # MUTUAL FUNDS — Core Vanguard / iShares for tactical allocation
    # ------------------------------------------------------------------
    "mutual_fund": {
        "description": "Low-cost index mutual funds for tactical rotation",
        "universe": [
            # Vanguard
            "VFINX",   # 500 Index (Investor)
            "VTSAX",   # Total Stock Market (Admiral)
            "VBTLX",   # Total Bond Market (Admiral)
            "VTIAX",   # Total International Stock (Admiral)
            "VGSLX",   # Real Estate Index (Admiral)
            "VPMAX",   # Primecap (Admiral)
            "VWELX",   # Wellington
            "VGHCX",   # Health Care
            "VITAX",   # Information Technology (Admiral)
            # iShares / Fidelity
            "FXAIX",   # Fidelity 500 Index
            "FBALX",   # Fidelity Balanced
            "FSMEX",   # Fidelity Select Medical
            "FSPTX",   # Fidelity Select Technology
            "FBIOX",   # Fidelity Select Biotech
        ],
        "sector_groupings": {
            "broad_equity": ["VFINX", "VTSAX", "FXAIX"],
            "balanced": ["VWELX", "FBALX"],
            "fixed_income": ["VBTLX"],
            "international": ["VTIAX"],
            "sector_specialty": ["VGHCX", "VITAX", "FSMEX", "FSPTX", "FBIOX"],
            "real_assets": ["VGSLX"],
            "active": ["VPMAX"],
        },
        "risk_params": {
            "default_stop_dd_pct": -8.0,
            "max_single_fund_pct": 33,
            "rebalance_frequency_days": 21,
            "min_holding_period_days": 30,
            "max_correlation_within_portfolio": 0.85,
        },
        "notes": (
            "Mutual funds settle T+1 and can only be traded at NAV close. "
            "No intraday execution. Short selling not permitted."
        ),
        "trading_hours": "NAV calculated at 16:00 ET",
        "data_source": "yfinance",
    },
}

# ---------------------------------------------------------------------------
# 3. RISK_PROFILES — Tiered risk envelopes
# ---------------------------------------------------------------------------
RISK_PROFILES: dict[str, dict[str, Any]] = {
    "conservative": {
        "max_drawdown_pct": -3.0,
        "position_size_pct": 5.0,
        "max_picks": 5,
        "max_portfolio_heat_pct": 15.0,
        "max_correlated_positions": 2,
        "stop_loss_required": True,
        "description": "Capital preservation focus. Suitable for large accounts.",
    },
    "moderate": {
        "max_drawdown_pct": -5.0,
        "position_size_pct": 10.0,
        "max_picks": 10,
        "max_portfolio_heat_pct": 30.0,
        "max_correlated_positions": 4,
        "stop_loss_required": True,
        "description": "Balanced risk/reward. Default for most strategies.",
    },
    "aggressive": {
        "max_drawdown_pct": -8.0,
        "position_size_pct": 15.0,
        "max_picks": 20,
        "max_portfolio_heat_pct": 50.0,
        "max_correlated_positions": 6,
        "stop_loss_required": True,
        "description": "Growth-oriented. Higher drawdown tolerance for higher returns.",
    },
    "speculative": {
        "max_drawdown_pct": -15.0,
        "position_size_pct": 20.0,
        "max_picks": 30,
        "max_portfolio_heat_pct": 75.0,
        "max_correlated_positions": 8,
        "stop_loss_required": False,
        "description": "Penny stocks, crypto moonshots. Only with risk capital.",
    },
}

# ---------------------------------------------------------------------------
# 4. FAILOVER_API_PRIORITY — Ordered data provider chain
# ---------------------------------------------------------------------------
FAILOVER_API_PRIORITY: list[dict[str, Any]] = [
    {
        "provider": "yfinance",
        "tier": "primary",
        "rate_limit": "2000/hour (unofficial)",
        "cost": "free",
        "asset_classes": ["stock", "etf", "futures", "forex", "mutual_fund", "crypto"],
        "notes": "Unofficial Yahoo Finance wrapper. No API key needed.",
    },
    {
        "provider": "alpha_vantage",
        "tier": "secondary",
        "rate_limit": "500/day (free), 75/min (premium)",
        "cost": "free tier available",
        "asset_classes": ["stock", "etf", "forex", "crypto"],
        "env_key": "ALPHA_VANTAGE_API_KEY",
        "notes": "Good forex/crypto coverage. Daily limit can be restrictive.",
    },
    {
        "provider": "polygon",
        "tier": "tertiary",
        "rate_limit": "5/min (free), unlimited (paid)",
        "cost": "paid for real-time",
        "asset_classes": ["stock", "etf", "futures", "forex", "crypto"],
        "env_key": "POLYGON_API_KEY",
        "notes": "Institutional-grade. Best for options flow and tick data.",
    },
    {
        "provider": "twelve_data",
        "tier": "quaternary",
        "rate_limit": "800/day (free), 8/min",
        "cost": "free tier available",
        "asset_classes": ["stock", "etf", "forex", "crypto"],
        "env_key": "TWELVE_DATA_API_KEY",
        "notes": "Good technical indicator endpoint. Decent free tier.",
    },
    {
        "provider": "finnhub",
        "tier": "fifth",
        "rate_limit": "60/min (free)",
        "cost": "free tier available",
        "asset_classes": ["stock", "etf", "forex", "crypto"],
        "env_key": "FINNHUB_API_KEY",
        "notes": "Real-time quotes, earnings, insider transactions.",
    },
]

# ---------------------------------------------------------------------------
# 5. QA_CHECKS — Data quality validation rules
# ---------------------------------------------------------------------------
QA_CHECKS: dict[str, dict[str, Any]] = {
    "stale_data": {
        "description": "Flag data where the latest timestamp is older than threshold",
        "max_staleness": timedelta(hours=24),
        "severity": "warning",
        "action": "log_and_skip",
        "check_fn": "lambda ts, now: (now - ts) > timedelta(hours=24)",
    },
    "stale_data_critical": {
        "description": "Block trading if data is older than 48 hours",
        "max_staleness": timedelta(hours=48),
        "severity": "critical",
        "action": "block_trade",
        "check_fn": "lambda ts, now: (now - ts) > timedelta(hours=48)",
    },
    "zero_negative_price": {
        "description": "Reject OHLCV rows where any price field is zero or negative",
        "severity": "critical",
        "action": "reject_row",
        "fields": ["open", "high", "low", "close"],
        "check_fn": "lambda row: any(row.get(f, 0) <= 0 for f in ['open','high','low','close'])",
    },
    "volume_anomaly": {
        "description": "Flag volume spikes > 10x the 20-day average",
        "multiplier": 10,
        "severity": "warning",
        "action": "log_and_flag",
        "check_fn": "lambda vol, avg_vol: vol > 10 * avg_vol",
    },
    "duplicate_picks_cross_portfolio": {
        "description": "Detect the same symbol held across multiple portfolios simultaneously",
        "severity": "warning",
        "action": "log_and_warn",
        "max_overlap": 2,
        "notes": "Up to 2 portfolios may hold same symbol if strategies differ.",
    },
    "symbol_mismatch": {
        "description": "Normalize symbol variants to canonical form",
        "severity": "info",
        "action": "auto_normalize",
        "normalization_map": {
            # Crypto variants
            "BTC-USD": "BTCUSDT", "BTCUSD": "BTCUSDT",
            "ETH-USD": "ETHUSDT", "ETHUSD": "ETHUSDT",
            "SOL-USD": "SOLUSDT", "SOLUSD": "SOLUSDT",
            "BNB-USD": "BNBUSDT", "BNBUSD": "BNBUSDT",
            "XRP-USD": "XRPUSDT", "XRPUSD": "XRPUSDT",
            "ADA-USD": "ADAUSDT", "ADAUSD": "ADAUSDT",
            # Forex variants
            "EUR/USD": "EURUSD=X", "EURUSD": "EURUSD=X",
            "USD/JPY": "USDJPY=X", "USDJPY": "USDJPY=X",
            "GBP/USD": "GBPUSD=X", "GBPUSD": "GBPUSD=X",
        },
    },
    "correlated_positions_unhedged": {
        "description": "Warn when highly correlated positions lack offsetting hedge",
        "severity": "warning",
        "action": "log_and_warn",
        "correlation_threshold": 0.85,
        "min_positions_to_check": 2,
        "notes": (
            "e.g. long AAPL + long MSFT + long QQQ = triple tech exposure. "
            "Suggest adding TLT or GLD as partial hedge."
        ),
    },
    "hlc_consistency": {
        "description": "Verify high >= open,close and low <= open,close for each bar",
        "severity": "critical",
        "action": "reject_row",
        "check_fn": (
            "lambda row: row['high'] >= max(row['open'], row['close']) "
            "and row['low'] <= min(row['open'], row['close'])"
        ),
    },
    "weekend_data": {
        "description": "Traditional markets should not have weekend bars (crypto exempt)",
        "severity": "warning",
        "action": "reject_row",
        "exempt_classes": ["crypto"],
        "check_fn": "lambda dt, asset_class: dt.weekday() >= 5 and asset_class != 'crypto'",
    },
}

# ---------------------------------------------------------------------------
# 6. PORTFOLIOS — 16 production portfolio definitions (legacy-compatible)
# ---------------------------------------------------------------------------
PORTFOLIOS: dict[str, dict] = {
    # -----------------------------------------------------------------------
    # 1. idx_connors_rsi2 — Connors RSI-2 on Index Futures
    # -----------------------------------------------------------------------
    "idx_connors_rsi2": {
        "name": "Index Futures Connors RSI-2",
        "strategy": "connors_rsi2",
        "asset_class": "futures",
        "symbols": ["ES=F", "NQ=F", "YM=F"],
        "description": "Mean reversion on index futures using proven RSI-2 < 5 entry.",
        "risk_profile": "moderate",
        "risk": {
            "stop_loss_atr_mult": 1.5,
            "take_profit_atr_mult": 3.0,
            "max_hold_days": 10,
            "max_positions": 3,
            "risk_per_trade_pct": 0.02,
        },
    },

    # -----------------------------------------------------------------------
    # 2. idx_mean_revert — Bollinger Mean Reversion on Futures
    # -----------------------------------------------------------------------
    "idx_mean_revert": {
        "name": "Futures Bollinger Mean Reversion",
        "strategy": "mean_reversion_bollinger",
        "asset_class": "futures",
        "symbols": ["ES=F", "NQ=F", "CL=F", "GC=F", "SI=F", "ZN=F"],
        "description": "Buy below lower BB + RSI(14) < 30. Sell above upper BB + RSI(14) > 70.",
        "risk_profile": "moderate",
        "risk": {
            "stop_loss_atr_mult": 2.0,
            "take_profit_atr_mult": 2.5,
            "max_hold_days": 7,
            "max_positions": 4,
            "risk_per_trade_pct": 0.015,
        },
    },

    # -----------------------------------------------------------------------
    # 3. idx_trend_follow — EMA Stack Trend Following on Futures
    # -----------------------------------------------------------------------
    "idx_trend_follow": {
        "name": "Futures EMA Stack Trend",
        "strategy": "ema_stack_momentum",
        "asset_class": "futures",
        "symbols": ["ES=F", "NQ=F", "CL=F", "GC=F"],
        "description": "EMA 9>21>50>200 aligned = long. Reverse for short. Ride the trend.",
        "risk_profile": "moderate",
        "risk": {
            "stop_loss_atr_mult": 2.5,
            "take_profit_atr_mult": 5.0,
            "max_hold_days": 20,
            "max_positions": 3,
            "risk_per_trade_pct": 0.02,
        },
    },

    # -----------------------------------------------------------------------
    # 4. stk_connors_rsi2 — Connors RSI-2 on Blue-Chip Stocks
    # -----------------------------------------------------------------------
    "stk_connors_rsi2": {
        "name": "Blue-Chip Connors RSI-2",
        "strategy": "connors_rsi2",
        "asset_class": "stock",
        "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V"],
        "description": "Proven RSI-2 mean reversion on mega-cap equities. 75%+ WR documented.",
        "risk_profile": "moderate",
        "risk": {
            "stop_loss_atr_mult": 1.5,
            "take_profit_atr_mult": 3.0,
            "max_hold_days": 10,
            "max_positions": 5,
            "risk_per_trade_pct": 0.02,
        },
    },

    # -----------------------------------------------------------------------
    # 5. stk_momentum — Stocks Momentum Breakout
    # -----------------------------------------------------------------------
    "stk_momentum": {
        "name": "Stocks Momentum Breakout",
        "strategy": "breakout_atr",
        "asset_class": "stock",
        "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V"],
        "description": "20-day high breakout with ATR expansion > 1.5x and volume confirmation.",
        "risk_profile": "moderate",
        "risk": {
            "stop_loss_atr_mult": 2.0,
            "take_profit_atr_mult": 4.0,
            "max_hold_days": 15,
            "max_positions": 4,
            "risk_per_trade_pct": 0.02,
        },
    },

    # -----------------------------------------------------------------------
    # 6. fx_mean_revert — Forex Mean Reversion
    # -----------------------------------------------------------------------
    "fx_mean_revert": {
        "name": "Forex Bollinger Mean Reversion",
        "strategy": "mean_reversion_bollinger",
        "asset_class": "forex",
        "symbols": ["EURUSD=X", "USDJPY=X", "GBPUSD=X", "AUDUSD=X", "NZDUSD=X"],
        "description": "Bollinger band mean reversion on major pairs. Tighter TP/SL for forex.",
        "risk_profile": "conservative",
        "risk": {
            "stop_loss_atr_mult": 1.5,
            "take_profit_atr_mult": 2.0,
            "max_hold_days": 14,
            "max_positions": 4,
            "risk_per_trade_pct": 0.01,
        },
    },

    # -----------------------------------------------------------------------
    # 7. fx_carry — Forex Carry Trade
    # -----------------------------------------------------------------------
    "fx_carry": {
        "name": "Forex Carry Trade Momentum",
        "strategy": "carry_momentum",
        "asset_class": "forex",
        "symbols": ["USDJPY=X", "AUDUSD=X", "NZDUSD=X", "GBPUSD=X"],
        "description": "Long high-yield vs low-yield when momentum confirms. JPY pairs primary.",
        "risk_profile": "conservative",
        "risk": {
            "stop_loss_atr_mult": 2.0,
            "take_profit_atr_mult": 3.0,
            "max_hold_days": 30,
            "max_positions": 3,
            "risk_per_trade_pct": 0.01,
        },
    },

    # -----------------------------------------------------------------------
    # 8. etf_sector_rotation — ETF Sector Rotation
    # -----------------------------------------------------------------------
    "etf_sector_rotation": {
        "name": "ETF Sector Rotation",
        "strategy": "ema_stack_momentum",
        "asset_class": "etf",
        "symbols": ["SPY", "QQQ", "XLK", "XLF", "XLE", "GLD", "IWM"],
        "description": "Rotate into strongest sector ETFs based on EMA alignment + relative strength.",
        "risk_profile": "moderate",
        "risk": {
            "stop_loss_atr_mult": 2.0,
            "take_profit_atr_mult": 4.0,
            "max_hold_days": 20,
            "max_positions": 4,
            "risk_per_trade_pct": 0.02,
        },
    },

    # -----------------------------------------------------------------------
    # 9. etf_bond_equity — TLT vs SPY Bond-Equity Rotation
    # -----------------------------------------------------------------------
    "etf_bond_equity": {
        "name": "Bond-Equity Rotation",
        "strategy": "vix_spike_reversal",
        "asset_class": "etf",
        "symbols": ["SPY", "TLT", "QQQ", "GLD"],
        "description": "When VIX spikes >20% and reverses, rotate from bonds to equities.",
        "risk_profile": "moderate",
        "risk": {
            "stop_loss_atr_mult": 2.5,
            "take_profit_atr_mult": 4.0,
            "max_hold_days": 15,
            "max_positions": 2,
            "risk_per_trade_pct": 0.02,
        },
    },

    # -----------------------------------------------------------------------
    # 10. penny_volume_breakout — Penny Stock Volume Breakout
    # -----------------------------------------------------------------------
    "penny_volume_breakout": {
        "name": "Penny Stock Volume Breakout",
        "strategy": "breakout_atr",
        "asset_class": "penny",
        "symbols": ["SOFI", "PLTR", "NIO", "MARA", "RIOT", "IONQ"],
        "description": "20-day high breakout on penny stocks with 2x+ volume surge.",
        "risk_profile": "aggressive",
        "risk": {
            "stop_loss_atr_mult": 2.5,
            "take_profit_atr_mult": 5.0,
            "max_hold_days": 7,
            "max_positions": 3,
            "risk_per_trade_pct": 0.015,
        },
    },

    # -----------------------------------------------------------------------
    # 11. stk_dark_pool_options — Dark Pool & Options Flow
    # -----------------------------------------------------------------------
    "stk_dark_pool_options": {
        "name": "Dark Pool & Options Flow Equities",
        "strategy": "dark_pool_options_flow",
        "asset_class": "stock",
        "symbols": ["AAPL", "NVDA", "TSLA", "AMD", "META", "MSFT", "PLTR"],
        "description": "Tracks unusual options volume and dark pool block prints for institutional support.",
        "risk_profile": "moderate",
        "risk": {
            "stop_loss_atr_mult": 1.5,
            "take_profit_atr_mult": 3.5,
            "max_hold_days": 10,
            "max_positions": 4,
            "risk_per_trade_pct": 0.02,
        },
    },

    # -----------------------------------------------------------------------
    # 12. penny_short_squeeze — Short Squeeze Predictor
    # -----------------------------------------------------------------------
    "penny_short_squeeze": {
        "name": "Short Squeeze Predictor",
        "strategy": "short_interest_squeeze",
        "asset_class": "penny",
        "symbols": ["MARA", "RIOT", "SOFI", "GME", "AMC", "CVNA"],
        "description": "Utilizes short interest ratios, borrow fees, and days-to-cover metrics.",
        "risk_profile": "speculative",
        "risk": {
            "stop_loss_atr_mult": 2.5,
            "take_profit_atr_mult": 6.0,
            "max_hold_days": 14,
            "max_positions": 3,
            "risk_per_trade_pct": 0.015,
        },
    },

    # -----------------------------------------------------------------------
    # 13. etf_macro_regime — Macro Regime Switching
    # -----------------------------------------------------------------------
    "etf_macro_regime": {
        "name": "Macro Regime Switching",
        "strategy": "macro_factor_regime",
        "asset_class": "etf",
        "symbols": ["SPY", "TLT", "GLD", "UUP", "BIL"],
        "description": "Allocates based on yield curve (2y/10y) and fed funds probabilities.",
        "risk_profile": "conservative",
        "risk": {
            "stop_loss_atr_mult": 2.0,
            "take_profit_atr_mult": 4.0,
            "max_hold_days": 45,
            "max_positions": 3,
            "risk_per_trade_pct": 0.02,
        },
    },

    # -----------------------------------------------------------------------
    # 14. idx_cot_fader — COT Speculator Fader
    # -----------------------------------------------------------------------
    "idx_cot_fader": {
        "name": "COT Report Fader",
        "strategy": "cot_sentiment_fade",
        "asset_class": "futures",
        "symbols": ["ES=F", "NQ=F", "CL=F", "GC=F", "ZC=F"],
        "description": "Fades extreme retail/non-commercial positioning from CFTC COT reports.",
        "risk_profile": "moderate",
        "risk": {
            "stop_loss_atr_mult": 2.5,
            "take_profit_atr_mult": 5.0,
            "max_hold_days": 21,
            "max_positions": 3,
            "risk_per_trade_pct": 0.015,
        },
    },

    # -----------------------------------------------------------------------
    # 15. fx_yield_spread — Yield Spread Premium
    # -----------------------------------------------------------------------
    "fx_yield_spread": {
        "name": "Forex Yield Spread Premium",
        "strategy": "sovereign_yield_spread",
        "asset_class": "forex",
        "symbols": ["USDJPY=X", "EURUSD=X", "AUDUSD=X", "GBPUSD=X"],
        "description": "Models forward premium/discount based on real sovereign yield spread differences.",
        "risk_profile": "moderate",
        "risk": {
            "stop_loss_atr_mult": 1.5,
            "take_profit_atr_mult": 3.0,
            "max_hold_days": 30,
            "max_positions": 3,
            "risk_per_trade_pct": 0.015,
        },
    },

    # -----------------------------------------------------------------------
    # 16. crypto_onchain_macro — On-Chain Smart Money
    # -----------------------------------------------------------------------
    "crypto_onchain_macro": {
        "name": "Crypto On-Chain Macro",
        "strategy": "onchain_whale_tracking",
        "asset_class": "crypto",
        "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        "description": "Incorporates stablecoin exchange flows, large holder wallet tracking, and miner capitulation.",
        "risk_profile": "aggressive",
        "risk": {
            "stop_loss_atr_mult": 2.0,
            "take_profit_atr_mult": 5.0,
            "max_hold_days": 20,
            "max_positions": 2,
            "risk_per_trade_pct": 0.02,
        },
    },
}


# ---------------------------------------------------------------------------
# 7. HELPER FUNCTIONS
# ---------------------------------------------------------------------------

def get_portfolio(name: str) -> dict | None:
    """Get portfolio definition by name."""
    return PORTFOLIOS.get(name)


def get_all_symbols() -> list[str]:
    """Get flat list of all unique symbols across all portfolios."""
    syms: set[str] = set()
    for p in PORTFOLIOS.values():
        syms.update(p["symbols"])
    return sorted(syms)


def get_portfolios_for_strategy(strategy: str) -> list[str]:
    """Get portfolio names that use a given strategy."""
    return [name for name, p in PORTFOLIOS.items() if p["strategy"] == strategy]


def get_strategy_meta(strategy: str) -> dict | None:
    """Get full strategy metadata from the registry."""
    return STRATEGY_REGISTRY.get(strategy)


def get_asset_class_config(asset_class: str) -> dict | None:
    """Get configuration for an asset class."""
    return ASSET_CLASS_CONFIGS.get(asset_class)


def get_risk_profile(name: str) -> dict | None:
    """Get a risk profile by name (conservative/moderate/aggressive/speculative)."""
    return RISK_PROFILES.get(name)


def get_universe(asset_class: str) -> list[str]:
    """Get the full symbol universe for an asset class."""
    config = ASSET_CLASS_CONFIGS.get(asset_class)
    return config["universe"] if config else []


def normalize_symbol(raw: str) -> str:
    """Normalize a symbol to its canonical form using all known mappings."""
    # Check crypto normalization first
    crypto_map = ASSET_CLASS_CONFIGS.get("crypto", {}).get("symbol_normalization", {})
    if raw in crypto_map:
        return crypto_map[raw]
    # Check QA symbol mismatch map
    qa_map = QA_CHECKS.get("symbol_mismatch", {}).get("normalization_map", {})
    if raw in qa_map:
        return qa_map[raw]
    return raw


def get_failover_providers(asset_class: str) -> list[str]:
    """Return ordered list of data providers that support the given asset class."""
    return [
        p["provider"]
        for p in FAILOVER_API_PRIORITY
        if asset_class in p["asset_classes"]
    ]


def validate_portfolio_risk(portfolio_name: str) -> list[str]:
    """
    Validate a portfolio's risk parameters against its assigned risk profile.
    Returns list of warnings (empty = all good).
    """
    portfolio = PORTFOLIOS.get(portfolio_name)
    if not portfolio:
        return [f"Portfolio '{portfolio_name}' not found"]

    profile_name = portfolio.get("risk_profile", "moderate")
    profile = RISK_PROFILES.get(profile_name)
    if not profile:
        return [f"Risk profile '{profile_name}' not found"]

    warnings: list[str] = []
    risk = portfolio.get("risk", {})

    if risk.get("max_positions", 0) > profile["max_picks"]:
        warnings.append(
            f"{portfolio_name}: max_positions ({risk['max_positions']}) "
            f"exceeds {profile_name} max_picks ({profile['max_picks']})"
        )

    return warnings


def get_all_qa_checks() -> dict[str, dict]:
    """Return all QA check definitions."""
    return QA_CHECKS.copy()
