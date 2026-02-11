"""
World-Class Intelligence — Configuration
"""
import os

# API endpoint for storing intelligence data
API_BASE = "https://findtorontoevents.ca/live-monitor/api"
INTEL_API = f"{API_BASE}/world_class_intelligence.php"
ADMIN_KEY = "livetrader2026"

# Custom headers to bypass ModSecurity WAF (blocks python-requests User-Agent)
API_HEADERS = {"User-Agent": "WorldClassIntelligence/1.0"}

# FRED API (free key — get from https://fred.stlouisfed.org/docs/api/api_key.html)
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")

# Asset class benchmarks
BENCHMARKS = {
    "CRYPTO": "BTC-USD",
    "STOCK": "SPY",
    "FOREX": "EURUSD=X"
}

# Crypto symbols (matching live-monitor)
CRYPTO_SYMBOLS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    "ADA-USD", "DOT-USD", "LINK-USD", "AVAX-USD", "DOGE-USD"
]

# Stock symbols
STOCK_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META",
    "JPM", "WMT", "XOM", "NFLX", "JNJ", "BAC"
]

# Forex symbols (Yahoo format)
FOREX_SYMBOLS = [
    "EURUSD=X", "GBPUSD=X", "JPY=X", "CADUSD=X",
    "AUDUSD=X", "NZDUSD=X"
]

# Momentum algos (disable when Hurst < 0.45)
MOMENTUM_ALGOS = [
    "Momentum Burst", "Breakout 24h", "Volatility Breakout",
    "Trend Sniper", "Volume Spike", "VAM",
    "ADX Trend Strength", "Alpha Predator"
]

# Mean-reversion algos (disable when Hurst > 0.55)
MEAN_REVERSION_ALGOS = [
    "RSI Reversal", "DCA Dip", "Dip Recovery",
    "Mean Reversion Sniper"
]

# All algorithm names
ALL_ALGOS = [
    "Momentum Burst", "RSI Reversal", "Breakout 24h", "DCA Dip",
    "Bollinger Squeeze", "MACD Crossover", "Consensus",
    "Volatility Breakout", "Trend Sniper", "Dip Recovery",
    "Volume Spike", "VAM", "Mean Reversion Sniper",
    "ADX Trend Strength", "StochRSI Crossover", "Awesome Oscillator",
    "RSI(2) Scalp", "Ichimoku Cloud", "Alpha Predator",
    "Insider Cluster Buy", "13F New Position",
    "Sentiment Divergence", "Contrarian Fear/Greed"
]
