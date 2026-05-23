"""
Enhanced ML Config — 50 Crypto Pairs × 5 Timeframes × 4 Model Variants
========================================================================
Expanded pair bucket from 14 → 30 covering majors, alts, DeFi, meme, AI/data.
"""

from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "results"
AB_TEST_DIR = BASE_DIR / "ab_tests"

for d in [DATA_DIR, MODELS_DIR, RESULTS_DIR, AB_TEST_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── 50 Target Crypto Pairs ──────────────────────────────────────────────────
# Full target universe for v4 testing (user-specified 50 symbols)
CRYPTO_PAIRS = [
    # === Tier 1: Majors (6) — tightest spreads, deepest books ===
    "BTCUSDT",    # Bitcoin
    "ETHUSDT",    # Ethereum
    "BNBUSDT",    # BNB
    "SOLUSDT",    # Solana
    "XRPUSDT",    # XRP
    "TRXUSDT",    # Tron
    # === Tier 2: Large-Cap Alts (10) ===
    # Rotated Feb 26 2026: DOT/LTC/BCH → TAO/NEAR/RENDER (AI narrative momentum)
    "ADAUSDT",    # Cardano
    "AVAXUSDT",   # Avalanche
    "TAOUSDT",    # Bittensor (AI)
    "LINKUSDT",   # Chainlink
    "NEARUSDT",   # NEAR Protocol (AI)
    "RENDERUSDT", # Render (AI/GPU)
    "ETCUSDT",    # Ethereum Classic
    "DOGEUSDT",   # Dogecoin
    "SHIBUSDT",   # Shiba Inu
    "HBARUSDT",   # Hedera
    # === Tier 3: Alt L1/L2 (12) ===
    "SUIUSDT",    # Sui
    "INJUSDT",    # Injective
    "ARBUSDT",    # Arbitrum
    "OPUSDT",     # Optimism
    "SEIUSDT",    # Sei
    "TIAUSDT",    # Celestia
    "APTUSDT",    # Aptos
    "ATOMUSDT",   # Cosmos
    "FILUSDT",    # Filecoin
    "NEARUSDT",   # NEAR Protocol
    "ALGOUSDT",   # Algorand
    "TONUSDT",    # Toncoin (OKX primary, Binance may differ)
    # === Tier 4: DeFi & AI (7) ===
    "AAVEUSDT",   # Aave
    "DYDXUSDT",   # dYdX
    "FETUSDT",    # Fetch.ai
    "WLDUSDT",    # Worldcoin
    "STRKUSDT",   # Starknet
    "JTOUSDT",    # Jito
    "WUSDT",      # Wormhole
    # === Tier 5: Small-Cap / Volatile (6) ===
    "APEUSDT",    # ApeCoin
    "CHZUSDT",    # Chiliz
    "ZKUSDT",     # ZKsync
    "ZROUSDT",    # LayerZero
    "POLUSDT",    # Polygon (was MATIC)
    # === Tier 6: New Additions (9) — Mar 19 2026 ===
    "ETHFIUSDT",  # Ether.fi
    "QNTUSDT",    # Quant
    "DEXEUSDT",   # DeXe
    "ENJUSDT",    # Enjin
    "THEUSDT",    # Thena
    "PIXELUSDT",  # Pixels
    "ANKRUSDT",   # Ankr
    "HOTUSDT",    # Holo
    "SAHARAUSDT", # Sahara AI
]

# Pairs from other exchanges (not on Binance or limited)
# MEXC:RIVERUSDT, OKX:GLMUSDT, HTX:ULTIMAUSDT, OKX:ZBCNUSDT, BYBIT:VVVUSDT
# These require separate exchange API integration
OTHER_EXCHANGE_PAIRS = {
    "RIVERUSDT": "mexc",
    "GLMUSDT": "okx",
    "ULTIMAUSDT": "htx",
    "ZBCNUSDT": "okx",
    "VVVUSDT": "bybit",
}

# ─── Timeframes ───────────────────────────────────────────────────────────────
# 10 tradeable timeframes covering scalp → position
# Sub-minute (1s-30s) requires exchange co-location and is not ML-feasible here
# DATA LIMITS TRIPLED for world-class model quality
TIMEFRAMES = {
    "1m":  {"interval": "1m",  "limit": 4500,  "seq_len": 30,   "horizon": 3,   "style": "scalp"},
    "3m":  {"interval": "3m",  "limit": 4500,  "seq_len": 36,   "horizon": 4,   "style": "scalp"},
    "5m":  {"interval": "5m",  "limit": 6000,  "seq_len": 48,   "horizon": 6,   "style": "scalp"},
    "15m": {"interval": "15m", "limit": 6000,  "seq_len": 48,   "horizon": 8,   "style": "scalp"},
    "30m": {"interval": "30m", "limit": 6000,  "seq_len": 48,   "horizon": 8,   "style": "scalp"},
    "1h":  {"interval": "1h",  "limit": 15000, "seq_len": 60,   "horizon": 12,  "style": "intraday"},
    "4h":  {"interval": "4h",  "limit": 9000,  "seq_len": 60,   "horizon": 12,  "style": "swing"},
    "1d":  {"interval": "1d",  "limit": 2000,  "seq_len": 60,   "horizon": 5,   "style": "position"},
    "1w":  {"interval": "1w",  "limit": 500,   "seq_len": 30,   "horizon": 3,   "style": "position"},
    "1M":  {"interval": "1M",  "limit": 120,   "seq_len": 12,   "horizon": 2,   "style": "position"},
}

# ─── Model Variants (A/B/C/D Testing) ────────────────────────────────────────
MODEL_VARIANTS = {
    "A_xgboost": {
        "type": "xgboost",
        "description": "XGBoost gradient boosting — v1.5 reduced complexity",
        "params": {
            "n_estimators": 300,
            "max_depth": 4,
            "learning_rate": 0.02,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.5,
            "reg_lambda": 2.0,
            "gamma": 0.1,
            "min_child_weight": 10,
            "scale_pos_weight": 5.0,
            "early_stopping_rounds": 50,
        },
    },
    "B_lightgbm": {
        "type": "lightgbm",
        "description": "LightGBM — v1.5 reduced complexity",
        "params": {
            "n_estimators": 300,
            "max_depth": 5,
            "learning_rate": 0.02,
            "num_leaves": 31,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.5,
            "reg_lambda": 2.0,
            "min_child_samples": 20,
            "is_unbalance": True,
            "early_stopping_rounds": 50,
        },
    },
    "C_random_forest": {
        "type": "random_forest",
        "description": "Random Forest — v1.5 reduced complexity",
        "params": {
            "n_estimators": 300,
            "max_depth": 8,
            "min_samples_split": 80,
            "min_samples_leaf": 30,
            "max_features": "sqrt",
            "class_weight": "balanced_subsample",
            "bootstrap": True,
        },
    },
    "D_ensemble_stack": {
        "type": "stacking",
        "description": "Stacking meta-learner — combines A+B+C with logistic regression",
        "base_models": ["A_xgboost", "B_lightgbm", "C_random_forest"],
        "meta_params": {
            "C": 1.0,
            "class_weight": "balanced",
            "max_iter": 1000,
        },
    },
}

# ─── Feature Engineering Config ───────────────────────────────────────────────
FEATURE_GROUPS = {
    "momentum": [
        "rsi_14", "rsi_7", "rsi_slope_5", "rsi_slope_10",
        "macd_hist", "macd_signal_cross", "macd_divergence",
        "roc_5", "roc_10", "roc_20",
        "williams_r_14", "cci_20",
        "stoch_k", "stoch_d", "stoch_cross",
    ],
    "volume": [
        "vol_ratio_20", "vol_ratio_5", "vol_spike_3x",
        "obv_slope", "obv_divergence",
        "vwap_distance", "volume_ma_ratio",
        "relative_volume_1h", "cumulative_delta_proxy",
    ],
    "volatility": [
        "atr_14", "atr_ratio", "atr_percentile_60",
        "bb_width", "bb_percentb", "bb_squeeze",
        "keltner_squeeze", "realized_vol_20",
        "high_low_range_pct", "close_to_high_pct",
    ],
    "trend": [
        "ema_5_20_cross", "ema_20_50_cross", "ema_50_200_cross",
        "price_vs_ema20", "price_vs_ema50", "price_vs_ema200",
        "adx_14", "di_plus", "di_minus",
        "aroon_up", "aroon_down",
        "supertrend_signal",
    ],
    "price_structure": [
        "higher_highs_3", "lower_lows_3",
        "inside_bar", "outside_bar",
        "doji_pattern", "engulfing_pattern",
        "consolidation_range_20", "price_compression",
        "distance_from_52w_high", "distance_from_52w_low",
    ],
    "market_context": [
        "btc_correlation_20", "btc_return_1h", "btc_return_24h",
        "fear_greed_index", "funding_rate",
        "hour_sin", "hour_cos",  # Time encoding
        "day_sin", "day_cos",
    ],
}

# V3 additional feature groups (25+ new features)
V3_FEATURE_GROUPS = {
    "order_flow": [
        "buy_pressure", "sell_pressure", "pressure_imbalance",
        "whale_buy_signal", "whale_sell_signal", "cvd_acceleration",
    ],
    "advanced_volatility": [
        "parkinson_vol_20", "garman_klass_vol_20", "vol_regime_ratio",
        "vol_of_vol", "vol_zscore",
    ],
    "multi_timeframe": [
        "htf_trend_slope", "htf_ema_alignment", "rsi_consistency",
        "rsi_cross_tf_divergence", "momentum_consistency", "htf_range_position",
    ],
    "macro_context": [
        "gold_correlation_20", "gold_return_24h", "gold_momentum_diff",
        "dxy_correlation_20", "dxy_return_24h",
        "btc_beta_20", "relative_strength_btc",
    ],
}

# Total features per observation
TOTAL_FEATURES = sum(len(v) for v in FEATURE_GROUPS.values())
V3_TOTAL_FEATURES = TOTAL_FEATURES + sum(len(v) for v in V3_FEATURE_GROUPS.values())

# ─── Regime Detection ─────────────────────────────────────────────────────────
REGIME_CONFIG = {
    "n_regimes": 4,
    "labels": ["bull_low_vol", "bull_high_vol", "bear_low_vol", "bear_high_vol"],
    "features": ["return_20d", "volatility_20d", "rsi_14", "adx_14"],
    "retrain_every_days": 30,
}

# ─── TP/SL Config (ATR-based, per style) ──────────────────────────────────────
# v1.3 LESSONS FROM FORWARD PICKS (Feb 22 — 34 picks, 23.5% WR):
#   - Scalp 15m: 31.8% WR with 3.0/1.5 — SELL signals won 6/7, BUY lost
#     → Tighten TP to 2.5x (more achievable), widen SL to 2.0x (fewer noise exits)
#   - Intraday 1h: 8.3% WR — catastrophic. 1.5x SL still too tight.
#     → Widen SL to 2.5x ATR, keep TP at 3.5x (2.5x SL catches normal pullbacks)
#   - ZROUSDT lost -6.73% vs 2.16% SL — price gapped through hourly check
#     → MIN_SL_DISTANCE_PCT raised to 0.8% in tracker
#   - Key insight: R:R matters less than WR. A 50% WR with 1.5:1 R:R = profitable.
TPSL_CONFIG = {
    "scalp":    {"tp_atr_mult": 2.5, "sl_atr_mult": 2.0, "max_hold_bars": 24},   # v1.3: TP 3.0→2.5, SL 1.5→2.0
    "intraday": {"tp_atr_mult": 3.5, "sl_atr_mult": 2.5, "max_hold_bars": 24},   # v1.3: SL 1.5→2.5, TP 3.0→3.5
    "swing":    {"tp_atr_mult": 4.5, "sl_atr_mult": 2.5, "max_hold_bars": 20},   # v1.3: SL 2.0→2.5, TP 4.0→4.5
    "position": {"tp_atr_mult": 5.0, "sl_atr_mult": 3.0, "max_hold_bars": 10},   # v1.3: SL 2.5→3.0
}

# ─── Live Picks Confidence Thresholds ─────────────────────────────────────────
# v1.3 LESSON: 31/34 picks had prob < 0.60 — all coin flips that lost
# Only 3 picks with prob ≥ 0.60, and even BNB 0.8463 still lost (overfit model)
# New strategy: fewer, higher-quality picks only
MIN_CONFIDENCE = 0.65   # v1.3: raised 0.55→0.65 (matches tracker gate)
HIGH_CONFIDENCE = 0.75  # v1.3: raised 0.65→0.75
MEDIUM_CONFIDENCE = 0.65  # v1.3: raised 0.55→0.65

# ─── A/B Test Evaluation Metrics ──────────────────────────────────────────────
EVALUATION_METRICS = [
    "accuracy",
    "precision",
    "recall",
    "f1_score",
    "roc_auc",
    "sharpe_ratio",
    "profit_factor",
    "max_drawdown",
    "win_rate",
    "expectancy",
]

# Minimum samples to declare a winner in A/B test
AB_TEST_MIN_SAMPLES = 100
AB_TEST_CONFIDENCE = 0.95

# V3 model-specific config
V3_CONFIG = {
    "smote_target_ratio": 0.0,       # SMOTE disabled (v1.5) — synthetic data degrades time series
    "use_smote": False,              # v1.5: explicitly disabled
    "adaptive_target_min": 0.15,     # Min positive rate for adaptive thresholds
    "adaptive_target_max": 0.30,     # Max positive rate for adaptive thresholds
    "purge_gap": 20,                 # Bars gap between train/test in purged CV
    "cv_folds": 5,                   # Number of walk-forward CV folds (v1.5: 4->5)
    "bootstrap_samples": 1000,       # Bootstrap iterations for significance tests
}

# ─── Binance API Config ──────────────────────────────────────────────────────
BINANCE_SPOT_BASE = "https://api.binance.com"
BINANCE_FUTURES_BASE = "https://fapi.binance.com"
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
FEAR_GREED_URL = "https://api.alternative.me/fng/"

# ─── V4 Config: World-Class Overhaul ────────────────────────────────────────
V4_CONFIG = {
    # Walk-forward validation
    "n_splits": 5,
    "purge_gap": 20,
    "embargo_pct": 0.01,
    "min_train_bars": 500,
    "min_test_bars": 100,
    # Binance costs
    "maker_fee": 0.001,
    "taker_fee": 0.001,
    # Position sizing (fractional Kelly)
    "kelly_fraction": 0.25,
    "max_position_pct": 0.10,
    "max_concurrent": 999,  # TESTING SPRINT: was 3, uncapped
    # Validation gates (ALL must pass for tradeable model)
    # Sharpe 0.80 for individual strategy (portfolio Sharpe will be higher via diversification)
    # WR is adaptive in prove_edge.py based on actual R:R ratio
    "min_sharpe": 0.80,
    "min_win_rate": 0.45,  # overridden by adaptive gate in prove_edge
    "min_profit_factor": 1.2,
    "max_drawdown": 0.25,
    "min_dsr_prob": 0.95,
    "max_mc_pvalue": 0.05,
    "min_folds": 3,
    "max_sharpe_cv": 1.0,
    # Monte Carlo
    "n_permutations": 1000,
    # Focus pairs (prove edge here before expanding)
    "priority_pairs": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"],
    "priority_timeframes": ["1h", "4h"],
    # Annualization factors (bars per year)
    "bars_per_year": {
        "1m": 525600, "3m": 175200, "5m": 105120,
        "15m": 35040, "30m": 17520, "45m": 11680,
        "1h": 8760, "4h": 2190, "1d": 365,
        "2d": 182, "1w": 52, "1M": 12,
    },
}

# Per-pair slippage (accounts for liquidity differences)
SLIPPAGE_MAP = {
    # Tier 1 Majors: tight spreads, deep books
    "BTCUSDT": 0.0005, "ETHUSDT": 0.0005, "BNBUSDT": 0.0005,
    "SOLUSDT": 0.0007, "XRPUSDT": 0.0007, "TRXUSDT": 0.0008,
    # Tier 2 Large-cap alts
    "ADAUSDT": 0.0008, "AVAXUSDT": 0.0008, "TAOUSDT": 0.001,
    "LINKUSDT": 0.0008, "NEARUSDT": 0.001, "RENDERUSDT": 0.001,
    "ETCUSDT": 0.0008, "DOGEUSDT": 0.001, "SHIBUSDT": 0.0015,
    "HBARUSDT": 0.001,
    # Tier 3 Alt L1/L2
    "SUIUSDT": 0.001, "INJUSDT": 0.001, "ARBUSDT": 0.001,
    "OPUSDT": 0.001, "SEIUSDT": 0.0012, "TIAUSDT": 0.0012,
    "APTUSDT": 0.001, "ATOMUSDT": 0.001, "FILUSDT": 0.001,
    "NEARUSDT": 0.001, "ALGOUSDT": 0.001, "TONUSDT": 0.001,
    # Tier 4 DeFi & AI
    "AAVEUSDT": 0.0012, "DYDXUSDT": 0.0012, "FETUSDT": 0.001,
    "WLDUSDT": 0.0012, "STRKUSDT": 0.0015, "JTOUSDT": 0.0015,
    "WUSDT": 0.0015,
    # Tier 5 Small-cap / Volatile
    "APEUSDT": 0.0012, "CHZUSDT": 0.001, "ZKUSDT": 0.0015,
    "ZROUSDT": 0.0015, "POLUSDT": 0.001,
    # Tier 6 New Additions (Mar 19 2026)
    "ETHFIUSDT": 0.0012, "QNTUSDT": 0.001, "DEXEUSDT": 0.0015,
    "ENJUSDT": 0.001, "THEUSDT": 0.0015, "PIXELUSDT": 0.0015,
    "ANKRUSDT": 0.001, "HOTUSDT": 0.0012, "SAHARAUSDT": 0.0015,
    # Legacy (still in some models)
    "MKRUSDT": 0.0015, "UNIUSDT": 0.001, "JUPUSDT": 0.0012,
    "RAYUSDT": 0.0015, "PEPEUSDT": 0.002, "RENDERUSDT": 0.001,
    "WIFUSDT": 0.002,
}

def get_slippage(pair: str) -> float:
    """Get slippage for a pair, default 0.001 if unknown."""
    return SLIPPAGE_MAP.get(pair, 0.001)


# ---------------------------------------------------------------------------
# Auto-Improvement Configuration
# ---------------------------------------------------------------------------
AUTO_IMPROVE_CONFIG = {
    "min_closed_picks_to_evaluate": 10,
    "retrain_trigger_wr_threshold": 0.45,
    "retrain_trigger_pf_threshold": 1.0,
    "scheduled_retrain_cron": "0 2 * * *",
    "conditional_retrain_enabled": False,  # Not yet implemented
}
