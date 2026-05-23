"""All constants for the Crypto Signal Engine."""
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = DATA_DIR / "models"
DOCS_DIR = BASE_DIR / "docs"

# Assets — day-trade (core 3, most liquid)
DAYTRADE_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

# Assets — top-gainer prediction (all Binance-listed)
# Rotated Feb 26 2026: LTC/BCH/DOT → NEAR/RENDER/TAO (AI narrative momentum)
TOP_GAINER_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "TAOUSDT",
    "LINKUSDT", "RENDERUSDT", "NEARUSDT", "SHIBUSDT", "INJUSDT",
    "SUIUSDT", "ARBUSDT", "OPUSDT", "SEIUSDT", "DYDXUSDT",
    "APEUSDT", "ALGOUSDT", "HBARUSDT", "WLDUSDT", "STRKUSDT",
    "ZROUSDT", "ZKUSDT", "AAVEUSDT", "CHZUSDT", "ETCUSDT",
    "WUSDT", "JTOUSDT", "FETUSDT", "TIAUSDT",
    # Added 2026-03-18: top-100 coins expansion
    "HYPEUSDT", "XLMUSDT", "KASUSDT", "ONDOUSDT", "ICPUSDT", "LTCUSDT",
]

# Timeframe
TIMEFRAME = "1h"
HIST_BARS = 2000  # ~83 days of 1h candles

# Model
ATR_PERIOD = 14
LABEL_HORIZON = 4  # predict 4 bars (4h) ahead

# TP/SL multipliers (ATR-based)
TP_ATR_MULT = 4.0   # TP = 4x ATR (wider target, higher reward)
SL_ATR_MULT = 1.5   # SL = 1.5x ATR (tighter stop, less risk per trade)
# Risk:Reward = 1:2.67 → only need ~28% win rate to break even

# Validation gates
DSR_GATE = 0.75
PSR_GATE = 0.75
TARGET_SR = 2.0

# Risk engine
MIN_CONF = 0.45          # minimum for any signal (lowered from 0.60 — was rejecting all signals)
MIN_CONF_PREMIUM = 0.60  # premium / Discord quality (lowered from 0.75)
MIN_EDGE_MULT = 2.0      # expected edge must exceed 2x total cost
MIN_VOL_RATIO = 1.2      # volume must be 1.2x 24h average (avoid dead markets)
CAPITAL = 10_000
RISK_PER_TRADE = 0.01    # 1% equity per trade

# Costs (round-trip)
ROUND_TRIP_FEE = 0.002   # 0.20% maker fee
SLIPPAGE_MAP = {
    "BTCUSDT": 0.0003, "ETHUSDT": 0.0003, "BNBUSDT": 0.0005,
    "SOLUSDT": 0.0005, "XRPUSDT": 0.0007,
}
DEFAULT_SLIPPAGE = 0.001

# XGBoost hyperparameters — three model variants
# All use early_stopping_rounds=20 to prevent overfitting
XGB_CONFIGS = {
    "conservative": {
        "max_depth": 3, "learning_rate": 0.03, "n_estimators": 300,
        "reg_alpha": 2.0, "reg_lambda": 2.0,
        "subsample": 0.7, "colsample_bytree": 0.7,
        "min_child_weight": 5,
    },
    "aggressive": {
        "max_depth": 4, "learning_rate": 0.05, "n_estimators": 300,
        "reg_alpha": 1.0, "reg_lambda": 1.0,
        "subsample": 0.8, "colsample_bytree": 0.8,
        "min_child_weight": 3,
    },
    "balanced": {
        "max_depth": 3, "learning_rate": 0.04, "n_estimators": 300,
        "reg_alpha": 1.5, "reg_lambda": 1.5,
        "subsample": 0.75, "colsample_bytree": 0.75,
        "min_child_weight": 4,
    },
}
EARLY_STOPPING_ROUNDS = 20

# LightGBM top-gainer regressor hyperparameters
LGB_CONFIG = {
    "objective": "regression",
    "learning_rate": 0.05,
    "num_leaves": 31,
    "n_estimators": 400,
    "subsample": 0.8,
    "colsample_bytree": 0.9,
}

# Feature list (15 core features — all vary per bar, no scalar broadcasts).
# Verified 2026-04-17 against the deployed lgb_top_gainer.txt model: model
# has all 15 + pair_id (16 total) matching this list. Plan 4's retrain
# DID produce the correct 16-feature model — the earlier 13:33Z run failure
# was a transient (likely stale-cache or non-Plan-4 commit deployment), NOT
# a schema mismatch.
FEATURES = [
    "ret_1h", "ret_4h", "ret_24h",
    "rsi_14", "macd", "atr", "bb_width",
    "vol_ratio", "above_200",
    "rsi_slope", "close_ema9", "atr_ratio",
    "candle_body", "high_low_pos", "ret_vol_corr",
]

TOP_GAINER_FEATURES = FEATURES + ["pair_id"]

# Strategy descriptions (human-readable explanations for each pick)
STRATEGY_DESCRIPTIONS = {
    "LONG": (
        "Bullish signal: XGBoost ensemble (3 models: conservative, aggressive, balanced) "
        "predicts upward price movement in next 4 hours. Entry confirmed by: "
        "1) model agreement (2/3 majority), 2) trend guard (above 200 SMA or F&G < 20), "
        "3) volume filter (above average activity). "
        f"TP = entry + {TP_ATR_MULT}x ATR. SL = entry - {SL_ATR_MULT}x ATR. "
        f"Risk:Reward = 1:{TP_ATR_MULT/SL_ATR_MULT:.1f}. "
        "Position sized at 1% equity risk."
    ),
    "SHORT": (
        "Bearish signal: RSI > 70 (overbought) AND price below 200 SMA — "
        "classic bearish divergence. XGBoost ensemble confirms downward probability. "
        f"TP = entry - {TP_ATR_MULT}x ATR. SL = entry + {SL_ATR_MULT}x ATR. "
        f"Risk:Reward = 1:{TP_ATR_MULT/SL_ATR_MULT:.1f}. "
        "Position sized at 1% equity risk."
    ),
}

# Guard descriptions (explain each filter)
GUARD_DESCRIPTIONS = {
    "confidence": "Model confidence must be >= {threshold}% (ensemble average of 3 XGBoost model probabilities)",
    "cost_edge": "Predicted probability must exceed 2x total trading cost (fee + slippage) to ensure positive expected value",
    "trend": "Price must be above 200-period SMA (bullish trend) OR Fear & Greed Index < 20 (extreme fear = contrarian buy)",
    "funding": "Funding rate z-score must be within +/- 2 standard deviations (avoids extreme leverage conditions)",
    "atr_edge": "Take-profit distance (3x ATR) must exceed 2x total cost (ensures reward covers expenses)",
}
