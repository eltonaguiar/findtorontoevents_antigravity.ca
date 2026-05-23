"""
Configuration for the Regime Terminal — market definitions, HMM parameters, strategy rules.
"""

# ─── HMM Parameters ───────────────────────────────────────────────────────────
HMM_N_REGIMES = 7
HMM_COVARIANCE_TYPE = "full"  # Full Gaussian covariance (captures feature correlations)
HMM_N_ITER = 200
HMM_TOL = 0.01
HMM_RANDOM_STATE = 42

# ─── Regime Labels (ordered worst → best by mean return) ──────────────────────
REGIME_LABELS = [
    "Crash",           # Severe drawdown, extreme fear
    "Strong Bear",     # Sustained downtrend, high vol
    "Mild Bear",       # Grinding lower, moderate vol
    "Chop/Neutral",    # Sideways, no clear trend
    "Accumulation",    # Smart money buying, low vol compression
    "Mild Bull",       # Steady uptrend, moderate confidence
    "Strong Bull",     # Full bull run, high momentum
]

# ─── Regime Colors (for dashboard) ───────────────────────────────────────────
REGIME_COLORS = {
    "Crash":         "#dc2626",  # Red
    "Strong Bear":   "#ef4444",  # Light red
    "Mild Bear":     "#f97316",  # Orange
    "Chop/Neutral":  "#6b7280",  # Gray
    "Accumulation":  "#3b82f6",  # Blue
    "Mild Bull":     "#22c55e",  # Green
    "Strong Bull":   "#16a34a",  # Dark green
}

# ─── Leverage Map (regime → position sizing multiplier) ───────────────────────
LEVERAGE_MAP = {
    "Strong Bull":   2.5,   # Aggressive long
    "Mild Bull":     1.5,   # Moderate long
    "Accumulation":  0.75,  # Small long (early)
    "Chop/Neutral":  0.0,   # Cash — sit on hands
    "Mild Bear":    -0.5,   # Small short / hedge
    "Strong Bear":  -1.5,   # Moderate short
    "Crash":        -2.0,   # Aggressive short / full hedge
}

# ─── Signal Hysteresis (minimum bars in regime before acting) ─────────────────
MIN_REGIME_BARS = 3  # Must be in same regime for 3+ periods before trading

# ─── Confirmation Requirements ────────────────────────────────────────────────
# Lowered from 7/8 to 4/8 to generate more signals for forward-test validation.
# At 7/8, the gate was so strict it generated 0 signals — no data to validate.
# 4/8 allows signals through while still requiring majority confirmation.
MIN_CONFIRMATIONS = 4  # Out of 8 technical conditions
CONFIRMATION_INDICATORS = [
    "rsi",           # RSI alignment with regime
    "macd",          # MACD histogram direction
    "ema_cross",     # 9/21 EMA cross
    "volume",        # Above-average volume
    "momentum",      # 5-day momentum direction
    "bb_position",   # Bollinger Band position
    "atr_expansion", # Volatility expansion
    "trend_align",   # 50/200 SMA trend alignment
]

# ─── Cooldown ─────────────────────────────────────────────────────────────────
EXIT_COOLDOWN_BARS = 12  # 12 bars (hours/days) cooldown after exit

# ─── Walk-Forward Backtest Parameters ─────────────────────────────────────────
TRAIN_WINDOW_DAYS = 365     # 1 year training window
TEST_WINDOW_DAYS = 30       # 1 month test window
TRANSACTION_COST_BPS = 10   # 10 bps round-trip (0.10%)
SLIPPAGE_BPS = 5            # 5 bps slippage estimate

# ─── Data Parameters ──────────────────────────────────────────────────────────
LOOKBACK_DAYS = 730         # 2 years of historical data
DATA_INTERVAL = "1d"        # Daily bars (use "1h" for intraday)

# ─── Market Definitions ──────────────────────────────────────────────────────
MARKETS = {
    "crypto": {
        "label": "Crypto (Large Cap)",
        "tickers": [
            "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD",
            "AVAX-USD", "LINK-USD", "DOT-USD", "MATIC-USD", "ATOM-USD",
        ],
    },
    "meme": {
        "label": "Meme Coins",
        "tickers": [
            "DOGE-USD", "SHIB-USD", "PEPE24478-USD", "FLOKI-USD",
            "BONK-USD", "WIF-USD",
        ],
    },
    "forex": {
        "label": "Forex (Major Pairs)",
        "tickers": [
            "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X",
            "USDCAD=X", "NZDUSD=X", "USDCHF=X",
        ],
    },
    "stocks": {
        "label": "Stocks (Large Cap)",
        "tickers": [
            "SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA",
            "AMD", "META", "AMZN", "GOOGL",
        ],
    },
    "penny": {
        "label": "Penny Stocks / Growth",
        "tickers": [
            "SNDL", "SOFI", "PLTR", "NIO", "LCID",
            "RIVN", "OPEN", "DNA", "IONQ", "QUBT",
        ],
    },
}

# Flatten all tickers for convenience
ALL_TICKERS = []
TICKER_CATEGORY = {}
for cat, info in MARKETS.items():
    for t in info["tickers"]:
        ALL_TICKERS.append(t)
        TICKER_CATEGORY[t] = cat
