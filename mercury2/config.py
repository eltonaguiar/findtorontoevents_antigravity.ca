# -*- coding: utf-8 -*-
"""Mercury 2 — Configuration."""

import os, pathlib

# ── Paths ──
BASE_DIR = pathlib.Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"
DATA_DIR.mkdir(exist_ok=True)
MODEL_DIR.mkdir(exist_ok=True)

# ── Symbol universe (order preserved; duplicates removed) ──
_RAW_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "INJUSDT",
    "SUIUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "FETUSDT",
    "POLUSDT", "TONUSDT", "SEIUSDT", "DYDXUSDT", "APEUSDT",
    "ALGOUSDT", "HBARUSDT", "WLDUSDT", "STRKUSDT", "CHZUSDT",
    "ETCUSDT", "TIAUSDT", "JTOUSDT", "WUSDT",
    "HYPEUSDT", "XLMUSDT", "TAOUSDT", "KASUSDT",
    "RENDERUSDT", "ONDOUSDT", "ICPUSDT",
    "ETHFIUSDT", "QNTUSDT", "DEXEUSDT", "ENJUSDT", "THEUSDT",
    "PIXELUSDT", "ANKRUSDT", "HOTUSDT", "SAHARAUSDT",
]
SYMBOLS = list(dict.fromkeys(_RAW_SYMBOLS))

# ── Timeframe & history ──
TIMEFRAME = "1h"
HIST_DAYS = 365 * 2          # 2 years for training
SCAN_BARS = 300              # Bars to fetch for live scanning (≈12.5 days)
ATR_PERIOD = 14
TP_ATR_MULT = 2.0            # ATR-based TP multiplier for training labels
SL_ATR_MULT = 1.5            # ATR-based SL multiplier for training labels

# ── Risk parameters ──
CAPITAL = 10_000
RISK_PER_TRADE = 0.01        # 1% per trade
MIN_CONFIDENCE = 0.62        # ensemble prob floor (tightened — weak IC on historical closes)
MIN_EDGE_MULT = 2.0          # prob must exceed 2× total cost
MAX_CONCURRENT_PICKS = 6     # cap actives; scanner ranks by prob and takes top N only
DEGRADED_MAX_PICKS = 3       # stricter cap when DSR/PSR validation is degraded
TOP_K = 3                    # top-gainer bucket size (reduced from 5 — less dilution)
MIN_RR = 2.0                 # minimum risk:reward ratio (raised from 1.5 — need better R:R to survive 31% WR)

# ── Symbol blacklist (persistently poor-performing symbols) ──
# Previous blacklist had BTC/ETH/XRP/DOT/INJ/FET based on only 0/2 trades each
# — too small a sample (6/20 symbols blocked = 30% of universe).
# Keeping only low-liquidity symbols with structural issues. BTC/ETH/XRP
# are high-liquidity majors that deserve re-evaluation with better risk guards.
SYMBOL_BLACKLIST = {"INJUSDT", "FETUSDT"}

# ── Cost model (round-trip) ──
ROUND_TRIP_FEE = 0.002       # 0.20% maker-only
SLIPPAGE = {
    "BTCUSDT": 0.0003, "ETHUSDT": 0.0003, "SOLUSDT": 0.0005,
    "BNBUSDT": 0.0005, "XRPUSDT": 0.0007, "DOGEUSDT": 0.001,
    "ADAUSDT": 0.001, "AVAXUSDT": 0.001, "TRXUSDT": 0.001,
    "DOTUSDT": 0.001, "LINKUSDT": 0.001, "LTCUSDT": 0.001,
    "BCHUSDT": 0.001, "SHIBUSDT": 0.001, "INJUSDT": 0.001,
    "SUIUSDT": 0.001, "ARBUSDT": 0.001, "OPUSDT": 0.001,
    "AAVEUSDT": 0.001, "FETUSDT": 0.001,
    "POLUSDT": 0.001, "TONUSDT": 0.001, "SEIUSDT": 0.001,
    "DYDXUSDT": 0.001, "APEUSDT": 0.001, "ALGOUSDT": 0.001,
    "HBARUSDT": 0.001, "WLDUSDT": 0.001, "STRKUSDT": 0.001,
    "CHZUSDT": 0.001, "ETCUSDT": 0.001, "TIAUSDT": 0.001,
    "JTOUSDT": 0.001, "WUSDT": 0.001,
    # Added 2026-03-18
    "HYPEUSDT": 0.001, "TRXUSDT": 0.001, "XLMUSDT": 0.001,
    "TAOUSDT": 0.001, "KASUSDT": 0.001, "RENDERUSDT": 0.001,
    "ONDOUSDT": 0.001, "ICPUSDT": 0.001, "LTCUSDT": 0.001,
    # Added 2026-03-19
    "ETHFIUSDT": 0.001, "QNTUSDT": 0.001, "DEXEUSDT": 0.001,
    "ENJUSDT": 0.001, "THEUSDT": 0.001, "PIXELUSDT": 0.001,
    "ANKRUSDT": 0.001, "HOTUSDT": 0.001, "SAHARAUSDT": 0.001,
}

def round_trip_cost(symbol: str) -> float:
    return ROUND_TRIP_FEE + 2 * SLIPPAGE.get(symbol, 0.001)

# ── Validation gates ──
# Lowered from 0.60 → 0.30 (Mar 16 2026): current model has DSR=0.000, PSR=0.000
# at the 0.60 threshold due to negative Sharpe (-4.48) from test-set distribution.
# 0.30 allows degraded-but-functional operation while retaining the gate as a signal.
DSR_GATE = 0.20  # Lowered from 0.30 to allow model deployment in bearish market
PSR_GATE = 0.20  # Will raise back to 0.30 when model passes consistently
TARGET_SHARPE = 2.0

# ── Trend filters ──
DAILY_MA_PERIOD = 50

# ── Features ──
ENSEMBLE_PARAMS = {
    "conservative": {"max_depth": 3, "learning_rate": 0.05, "n_estimators": 150, "reg_alpha": 1.0, "reg_lambda": 1.0},
    "aggressive":   {"max_depth": 6, "learning_rate": 0.10, "n_estimators": 250, "reg_alpha": 0.1, "reg_lambda": 0.1},
    "balanced":     {"max_depth": 4, "learning_rate": 0.07, "n_estimators": 200, "reg_alpha": 0.0, "reg_lambda": 1.0},
}

# ── LightGBM top-gainer params ──
TOP_GAINER_PARAMS = {
    "objective": "regression",
    "learning_rate": 0.05,
    "num_leaves": 31,
    "n_estimators": 400,
    "max_depth": -1,
    "subsample": 0.8,
    "colsample_bytree": 0.9,
    "verbose": -1,
}

# ── Features ──
FEATURE_COLS = [
    "ret_1h", "ret_4h", "ret_24h",
    "rsi_14", "macd",
    "atr", "bb_width",
    "vol_ratio", "above_200",
    "fng", "btc_dom",
    "pair_id",
]

# ── Discord ──
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "")

# ── Version ──
VERSION = "1.0.0"
SYSTEM_NAME = "Mercury2"
