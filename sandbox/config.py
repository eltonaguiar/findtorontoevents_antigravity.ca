"""Configuration for the Opposite Day sandbox."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # repo root
SANDBOX_DIR = Path(__file__).resolve().parent
DB_PATH = SANDBOX_DIR / "data" / "opposite_day.db"

# Engine source files (relative to ROOT)
ENGINE_SOURCES = {
    "predictions": ROOT / "predictions" / "data" / "active_predictions.json",
    "kimi": ROOT / "KIMI_RISEOFTHECLAW" / "data" / "live_signals_now.json",
    "alpha": ROOT / "alpha_engine" / "data" / "active_picks.json",
    "signal_engine": ROOT / "crypto_signal_engine" / "data" / "active_picks.json",
    "cross_aggregator": ROOT / "cross_aggregation" / "data" / "super_signals.json",
}

# Timeline checkpoints in seconds
CHECKPOINTS = {"1h": 3600, "4h": 14400, "12h": 43200, "24h": 86400}

# Pick expiration
EXPIRATION_SECONDS = 86400  # 24 hours

# Default TP/SL for engines that don't provide them (percentage from entry)
DEFAULT_TP_PCT = 5.0
DEFAULT_SL_PCT = 3.0

# Excluded symbols
EXCLUDED_SYMBOLS = {"SUIUSDT"}

# Discord
WEBHOOK_ENV_VAR = "DISCORD_PAPER_TRADE_WEBHOOK"
EMBED_CHAR_LIMIT = 6000
MAX_PICKS_PER_EMBED = 8  # truncate after this many
DISCORD_RATE_LIMIT_RETRY = 3
DISCORD_RETRY_DELAY = 2  # seconds

# Price fetch
# Binance spot price — with fallbacks for geo-restricted CI
import os as _os
if _os.environ.get("GITHUB_ACTIONS"):
    BINANCE_TICKER_URL = "https://data-api.binance.vision/api/v3/ticker/price"
else:
    BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/price"
BINANCE_TICKER_FALLBACK_URLS = [
    "https://api1.binance.com/api/v3/ticker/price",
    "https://api2.binance.com/api/v3/ticker/price",
    "https://data-api.binance.vision/api/v3/ticker/price",
    "https://api.binance.us/api/v3/ticker/price",
]
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
