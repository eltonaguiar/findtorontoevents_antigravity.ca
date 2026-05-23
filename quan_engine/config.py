"""
QuanEngine Configuration
========================
All tunable parameters in one place. No magic numbers in other modules.
"""
import os

# --- Regime Router ---
HURST_WINDOW = 100           # Rolling window for Hurst R/S analysis
HURST_TREND_THRESHOLD = 0.55 # H > this → trending regime
HURST_MR_THRESHOLD = 0.45    # H < this → mean-reverting regime

# --- Ensemble ---
CONSENSUS_THRESHOLD = 0.45   # 45% of pool must agree (was 0.60; lowered for wider coverage)
MIN_AVG_CONFIDENCE = 0.45    # Average confidence floor (was 0.55; lowered to emit more signals)

# --- Mode Dispatcher ---
MODES = {
    "SCALP": {
        "timeframe": "15m",
        "max_hold_bars": 8,       # 2 hours
        "rr_target": 2.0,
        "atr_tp_mult": 1.5,
        "atr_sl_mult": 0.75,
        "trailing_activation": None,  # No trailing for scalp
    },
    "SWING": {
        "timeframe": "1h",
        "max_hold_bars": 48,      # 48 hours
        "rr_target": 2.8,
        "atr_tp_mult": 2.5,
        "atr_sl_mult": 0.9,
        "trailing_activation": 1.5,   # Activate at 1.5× ATR profit
    },
    "POSITION": {
        "timeframe": "4h",
        "max_hold_bars": 180,     # 30 days
        "rr_target": 3.6,
        "atr_tp_mult": 4.0,
        "atr_sl_mult": 1.1,
        "trailing_activation": 2.0,   # Activate at 2× ATR profit
    },
}

# --- Risk Gate ---
KELLY_FRACTION = 0.5         # Half-Kelly
POSITION_CAPS = {
    "SCALP": 0.03,            # 3% max per trade
    "SWING": 0.05,            # 5% max per trade
    "POSITION": 0.08,         # 8% max per trade
}
MAX_CONCURRENT_PER_MODE = 999  # TESTING SPRINT: was 3, uncapped
MAX_CONCURRENT_TOTAL = 999     # TESTING SPRINT: was 6, uncapped
CORRELATION_THRESHOLD = 0.70  # Skip if > 0.7 correlated with existing

# --- Symbols ---
# MATICUSDT removed 2026-04-23: Polygon rebranded to POL in Sep 2024 and the
# MATIC-USD yfinance feed is frozen at a stale pre-migration price (~$0.3794).
# Scanner was emitting ~30 MATICUSDT LONG picks/day at the stale entry_price,
# all resolving TP_HIT because the resolver compared stale entry vs current
# live/POL price. Net effect: 760 bogus 100%-WR rows in universal_resolved_picks.json
# inflating quan_engine aggregate WR to 89.5%. Root cause of the artifact
# logged in memory project_quan_engine_matic_positive_artifact.
# Reference: reports/SYNTHESIS_6_ANALYSES_AUDIT_WHATIF_2026_04_23.md §9.
# Core 20 — scanned every run for active signals (expanded 2026-03-18)
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT",
    "XRPUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT",
    # Added 2026-03-18: top-100 coins expansion
    "HYPEUSDT", "TRXUSDT", "XLMUSDT", "TAOUSDT", "KASUSDT",
    "RENDERUSDT", "ONDOUSDT", "ICPUSDT", "ETCUSDT", "LTCUSDT",
]

# Extended universe — scanned for market overview / next-best-picks
SYMBOLS_EXTENDED = [
    # Top 10 (also in SYMBOLS)
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT",
    "XRPUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT",
    # Large caps
    "LTCUSDT", "LINKUSDT", "UNIUSDT", "AAVEUSDT", "ATOMUSDT",
    "NEARUSDT", "APTUSDT", "SUIUSDT", "TONUSDT", "ICPUSDT",
    # Mid caps / momentum plays
    "ARBUSDT", "OPUSDT", "MKRUSDT", "INJUSDT", "FETUSDT",
    "TIAUSDT", "SEIUSDT", "JUPUSDT", "WIFUSDT", "PEPEUSDT",
    # Established alts
    "FILUSDT", "TRXUSDT", "ETCUSDT", "ALGOUSDT", "XLMUSDT",
    "VETUSDT", "HBARUSDT", "SANDUSDT", "MANAUSDT", "AXSUSDT",
    # DeFi / Layer 2
    "SNXUSDT", "COMPUSDT", "CRVUSDT", "LDOUSDT", "RNDRUSDT",
    # Added 2026-03-18: top-100 coins expansion
    "HYPEUSDT", "TAOUSDT", "KASUSDT", "ONDOUSDT", "RENDERUSDT",
    "LTCUSDT",
]

# --- Strategy Pools ---
TRENDING_STRATEGIES = [
    "corr_hma_trend",
    "overnight_seasonality_btc",
    "pairs_spread_btceth",
    "liquidity_sweep_reversal",
]

MR_STRATEGIES = [
    "consecutive_down_rsi",
    "rsi2_bb_squeeze",
    "autocorr_reversion",
    "volume_profile_deviation",
]

# Always-on prop firm strategies (fire in ANY market condition)
PROP_STRATEGIES = [
    "rsi_momentum_prop",
    "atr_breakout_prop",
    "ema_momentum_prop",
    "fear_greed_contrarian",
    # Wave 20 proven strategies (backtested 61-85% WR)
    "proven_keltner_squeeze_prop",
    "proven_triple_ema_prop",
    "proven_vwap_mr_prop",
    "proven_stochrsi_prop",
    "proven_propfirm_cons_prop",
    "ema_aggressive_prop",
]

# --- Backtest ---
IS_MONTHS = 18               # In-sample window
OOS_MONTHS = 6               # Out-of-sample window
ROLL_MONTHS = 3              # Roll forward increment
MIN_TRADES_OOS = 100         # Minimum trades per OOS window

# --- Anti-overfit thresholds ---
OOS_SHARPE_RATIO = 0.70      # OOS Sharpe ≥ 70% of IS Sharpe
OOS_WR_TOLERANCE_PP = 10     # OOS WR within 10 percentage points of IS
MIN_PROFIT_FACTOR = 1.5
MAX_CONSECUTIVE_LOSSES = 5
MAX_DRAWDOWN_PCT = 15.0
MAX_SINGLE_TRADE_PNL_PCT = 20.0  # No single trade > 20% of total P&L
MIN_PROFITABLE_WINDOWS = 4   # Must be profitable in ≥ 4 of 6 OOS windows

# --- Data ---
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DATA_DIR, "quan_engine.db")
SIGNALS_PATH = os.path.join(DATA_DIR, "active_signals.json")

# --- API ---
BINANCE_BASE = "https://api.binance.com"
# Fallbacks for geo-restricted environments (GitHub Actions US runners get HTTP 451)
BINANCE_FALLBACK_URLS = [
    "https://data-api.binance.vision",   # Public data API (unrestricted)
    "https://api.binance.us",            # US-legal endpoint
]
FEAR_GREED_URL = "https://api.alternative.me/fng/?limit=1"

# --- Failover System Configuration ---
FAILOVER_CONFIG = {
    # Data source priority (higher = later fallback)
    "data_source_priority": [
        "yfinance",          # Tier 1: Primary (geo-safe)
        "binance",           # Tier 1: Primary exchange
        "coingecko",         # Tier 2: Crypto data API
        "cryptocompare",     # Tier 2: Crypto data API
        "cache",             # Tier 3: Local cache
        "mock",              # Tier 4: Mock data (testing only)
    ],
    
    # Cache settings
    "cache_ttl_minutes": 60,
    "stale_data_ttl_hours": 24,
    "enable_stale_cache_fallback": True,
    "enable_mock_fallback": False,  # NEVER enable in production
    
    # Retry settings
    "max_retries_per_source": 3,
    "retry_base_delay_seconds": 1.0,
    "retry_max_delay_seconds": 10.0,
    "retry_backoff_multiplier": 2.0,
    
    # Rate limits (requests per minute)
    "rate_limits": {
        "coingecko": 10,       # Free tier: 10-30 calls/min
        "cryptocompare": 100,  # Free tier: 100k/month
        "binance": 1200,       # 1200 weight per minute
    },
    
    # Health monitoring
    "health_check_interval_minutes": 5,
    "failure_threshold_for_unhealthy": 3,
    "auto_disable_unhealthy_sources": True,
    
    # Notification failover
    "notification_channels": [
        "discord_webhook",
        "discord_bot",
        "email",
        "slack_webhook",
        "file_fallback",
    ],
    "notification_batch_window_seconds": 5,
    "notification_rate_limit_per_minute": 30,
    "critical_notification_retry": True,
    
    # Circuit breaker settings
    "circuit_breaker_failure_threshold": 5,
    "circuit_breaker_timeout_seconds": 60,
    "circuit_breaker_half_open_max_calls": 3,
}

# CoinGecko symbol mapping (loaded dynamically in failover_system.py)
COINGECKO_API_BASE = "https://api.coingecko.com/api/v3"
CRYPTOCOMPARE_API_BASE = "https://min-api.cryptocompare.com/data"

# --- Backtest cost model ---
ROUND_TRIP_COST_PCT = 0.0015  # 0.15% (taker + maker + slippage)
