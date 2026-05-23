"""Centralized configuration for the Coinglass DNA Bundle."""
from pathlib import Path

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = str(DATA_DIR / "coinglass.db")

# Symbols to track (Binance USDT perpetual format) — top 21 by volume/liquidity
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT",
    "XRPUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
    "MATICUSDT", "LTCUSDT",
    # Added 2026-03-18: top-100 coins expansion
    "HYPEUSDT", "TRXUSDT", "XLMUSDT", "TAOUSDT", "KASUSDT",
    "RENDERUSDT", "ONDOUSDT", "ICPUSDT", "ETCUSDT",
]

# Map for CoinGecko price lookups
SYMBOL_TO_COINGECKO = {
    "BTCUSDT": "bitcoin",
    "ETHUSDT": "ethereum",
    "SOLUSDT": "solana",
    "BNBUSDT": "binancecoin",
    "DOGEUSDT": "dogecoin",
    "XRPUSDT": "ripple",
    "ADAUSDT": "cardano",
    "AVAXUSDT": "avalanche-2",
    "LINKUSDT": "chainlink",
    "DOTUSDT": "polkadot",
    "MATICUSDT": "matic-network",
    "LTCUSDT": "litecoin",
    # Added 2026-03-18
    "HYPEUSDT": "hyperliquid",
    "TRXUSDT": "tron",
    "XLMUSDT": "stellar",
    "TAOUSDT": "bittensor",
    "KASUSDT": "kaspa",
    "RENDERUSDT": "render-token",
    "ONDOUSDT": "ondo-finance",
    "ICPUSDT": "internet-computer",
    "ETCUSDT": "ethereum-classic",
}

# Data fetcher
FETCH_TIMEOUT = 10
RETRY_MAX = 3
RETRY_BASE_DELAY = 1.0
MIN_INTERVAL_BETWEEN_CALLS = 1.0  # seconds per source

# Strategy thresholds
EXTREME_REVERSION_Z_THRESHOLD = 2.0
WHALE_DIVERGENCE_MIN_DIFF = 0.15
MOMENTUM_SMA_WINDOW = 3
MOMENTUM_CONSECUTIVE_MIN = 3
CROSS_EXCHANGE_SPREAD_MIN = 0.20
FUNDING_RATIO_THRESHOLD = 1.15
SENTIMENT_LONG_THRESHOLD = 0.70
SENTIMENT_SHORT_THRESHOLD = 0.30
SPIKE_THRESHOLD_PCT = 30.0
MIN_SIGNAL_CONFIDENCE = 0.60  # Minimum confidence to emit a signal

# Paper portfolio
STARTING_CAPITAL = 10_000.0
RISK_PER_TRADE_PCT = 2.0
MAX_CONCURRENT_POSITIONS = 8
TP_ATR_MULT = 2.0
SL_ATR_MULT = 1.0
MAX_HOLD_HOURS = 48

# Discord
DISCORD_WEBHOOK_PAPERTRADE = ""  # Set via env var at runtime

PORTFOLIO_SUMMARY_INTERVAL_HOURS = 2

# Rolling windows (minutes)
ZSCORE_WINDOW_MINUTES = 1440     # 24 hours
MOMENTUM_WINDOW_MINUTES = 60     # 1 hour
SENTIMENT_NORM_WINDOW_DAYS = 30
