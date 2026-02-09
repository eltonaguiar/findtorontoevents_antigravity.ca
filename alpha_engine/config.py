"""
Alpha Engine Configuration
Central configuration for all modules. Override via environment variables or config.yaml.
"""
import os
from pathlib import Path
from datetime import datetime

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
CACHE_DIR = BASE_DIR / "cache"
DATA_DIR = BASE_DIR / "data_cache"

for d in [OUTPUT_DIR, CACHE_DIR, DATA_DIR]:
    d.mkdir(exist_ok=True)

# ─── Universe ─────────────────────────────────────────────────────────────────
# Default universe: S&P 500 constituents (top liquid names)
DEFAULT_UNIVERSE = [
    # Mega-cap tech
    "AAPL", "MSFT", "GOOG", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "ORCL",
    # Financials
    "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "BLK", "SCHW", "AXP",
    # Healthcare
    "UNH", "JNJ", "LLY", "PFE", "ABT", "TMO", "MRK", "ABBV", "DHR", "BMY",
    # Consumer
    "WMT", "PG", "KO", "PEP", "COST", "MCD", "NKE", "SBUX", "TGT", "HD",
    # Industrials
    "CAT", "HON", "UPS", "GE", "RTX", "DE", "LMT", "BA", "MMM", "UNP",
    # Energy
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HAL",
    # Tech / Semis
    "AMD", "INTC", "QCOM", "TXN", "MU", "AMAT", "LRCX", "KLAC", "ADI", "MRVL",
    # Communication
    "DIS", "NFLX", "CMCSA", "T", "VZ", "TMUS", "CHTR", "EA", "TTWO", "WBD",
    # REITs / Utilities
    "AMT", "PLD", "CCI", "EQIX", "SPG", "NEE", "DUK", "SO", "D", "AEP",
    # Other quality
    "BRK-B", "LIN", "SHW", "ECL", "ITW", "EMR", "APD", "FIS", "FISV", "ADP",
]

# Sector ETFs for regime/rotation analysis
SECTOR_ETFS = {
    "Technology": "XLK",
    "Financials": "XLF",
    "Healthcare": "XLV",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Industrials": "XLI",
    "Energy": "XLE",
    "Materials": "XLB",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Communication Services": "XLC",
}

# Benchmarks
BENCHMARKS = ["SPY", "QQQ", "IWM", "DIA", "VTI"]

# Macro tickers
MACRO_TICKERS = {
    "VIX": "^VIX",
    "TNX": "^TNX",       # 10Y Treasury Yield
    "TYX": "^TYX",       # 30Y Treasury Yield
    "IRX": "^IRX",       # 13-Week T-Bill
    "DXY": "DX-Y.NYB",   # US Dollar Index
    "GOLD": "GC=F",      # Gold Futures
    "OIL": "CL=F",       # Crude Oil Futures
    "SPY": "SPY",
}

# ─── Date Ranges ──────────────────────────────────────────────────────────────
BACKTEST_START = "2015-01-01"
BACKTEST_END = datetime.now().strftime("%Y-%m-%d")
TRAIN_WINDOW_YEARS = 3
TEST_WINDOW_MONTHS = 6

# ─── Transaction Costs ───────────────────────────────────────────────────────
COMMISSION_PER_SHARE = 0.005       # $0.005/share (IB-like)
MIN_COMMISSION = 1.00              # $1.00 minimum
SLIPPAGE_BPS = 10                  # 10 basis points (0.10%)
BORROW_COST_ANNUAL_BPS = 50       # 50 bps/year for shorts
TAX_RATE_SHORT_TERM = 0.37        # Short-term cap gains
TAX_RATE_LONG_TERM = 0.20         # Long-term cap gains

# ─── Questrade Canada Costs ──────────────────────────────────────────────────
QUESTRADE_FOREX_FEE = 0.0175      # 1.75% for USD trades
QUESTRADE_ECN_FEE = 0.0035        # $0.0035/share
QUESTRADE_SEC_FEE = 0.0000278     # SEC fee rate

# ─── Risk Management ─────────────────────────────────────────────────────────
MAX_POSITION_PCT = 0.05            # 5% max single position
MIN_POSITION_PCT = 0.005           # 0.5% min position
MAX_SECTOR_PCT = 0.25              # 25% max sector exposure
MAX_DRAWDOWN_HALT = 0.15           # Halt trading at 15% drawdown
KELLY_FRACTION = 0.25              # Quarter-Kelly for safety
MOMENTUM_MAX_RISK = 0.02           # 2% max risk per momentum trade
SAFE_BET_MAX_RISK = 0.05           # 5% max for dividend aristocrats

# ─── Feature Configuration ────────────────────────────────────────────────────
FEATURE_FAMILIES = {
    "momentum": True,
    "cross_sectional": True,
    "volatility": True,
    "volume": True,
    "mean_reversion": True,
    "regime": True,
    "fundamental": True,
    "growth": True,
    "valuation": True,
    "earnings": True,
    "seasonality": True,
    "options": True,
    "sentiment": True,
    "flow": True,
}

# Momentum lookback periods
MOMENTUM_WINDOWS = [5, 10, 21, 63, 126, 252]  # 1w, 2w, 1m, 3m, 6m, 1y
MOVING_AVG_WINDOWS = [10, 20, 50, 100, 200]

# ─── Strategy Params ──────────────────────────────────────────────────────────
HOLDING_PERIODS = [1, 3, 5, 21, 63, 126]  # days
TOP_K_PICKS = [5, 10, 20, 30, 50]
REBALANCE_FREQUENCIES = ["daily", "weekly", "monthly"]

# ─── Validation ───────────────────────────────────────────────────────────────
WALK_FORWARD_TRAIN_DAYS = 756      # ~3 years
WALK_FORWARD_TEST_DAYS = 126       # ~6 months
PURGED_CV_FOLDS = 5
EMBARGO_DAYS = 5
MONTE_CARLO_SIMULATIONS = 1000
MIN_SHARPE_THRESHOLD = 0.5
MIN_TRADES_FOR_SIGNIFICANCE = 30

# ─── Regime Thresholds ────────────────────────────────────────────────────────
VIX_LOW = 16
VIX_MODERATE = 20
VIX_HIGH = 25
VIX_EXTREME = 35
DXY_TREND_WINDOW = 50              # 50-day SMA for DXY
DXY_STRONG_THRESHOLD = 0.02        # 2% above 50d SMA = strong dollar

# ─── Earnings ─────────────────────────────────────────────────────────────────
EARNINGS_BEAT_THRESHOLD = 0.05     # 5% EPS beat = significant
CONSECUTIVE_BEATS_REQUIRED = 3     # 3 quarters of beats
PEAD_DRIFT_WINDOW = 42             # 6 weeks post-earnings

# ─── Insider Activity ─────────────────────────────────────────────────────────
INSIDER_CLUSTER_THRESHOLD = 3      # 3+ insiders buying
INSIDER_LOOKBACK_DAYS = 14         # within 14 days
INSIDER_SCORE_MULTIPLIER = 1.5     # 1.5x score boost

# ─── Dividend Aristocrats ─────────────────────────────────────────────────────
MIN_DIVIDEND_INCREASE_YEARS = 25
DIVIDEND_ARISTOCRATS = [
    "JNJ", "PG", "KO", "PEP", "MMM", "ABT", "ABBV", "MCD", "WMT", "CL",
    "EMR", "GPC", "SHW", "SWK", "ADP", "ITW", "BDX", "DOV", "PPG", "AFL",
    "ECL", "ED", "GD", "TGT", "WBA", "LOW", "ATO", "CINF", "CVX", "XOM",
    "FRT", "HRL", "NDSN", "NUE", "PNR", "ROP", "SPGI", "SYY", "TROW",
    "CB", "CHD", "APD", "BEN", "CAH", "CTAS", "GWW", "KMB", "LEG", "LIN",
]

# ─── Logging ──────────────────────────────────────────────────────────────────
LOG_LEVEL = os.environ.get("ALPHA_LOG_LEVEL", "INFO")
VERBOSE = os.environ.get("ALPHA_VERBOSE", "0") == "1"
