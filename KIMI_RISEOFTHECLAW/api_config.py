"""
api_config.py — KIMI Rise of the Claw v11.0
Centralized API key loader — reads from .env file in same directory.

Usage:
    from api_config import COINGECKO_KEY, CURRENCYLAYER_KEY, ...

Keys are loaded from KIMI_RISEOFTHECLAW/.env (never committed to git).
Fallback to environment variables for GitHub Actions / CI.
"""

import os
from pathlib import Path

_ENV_PATH = Path(__file__).parent / ".env"


def _load_env() -> dict:
    """Load .env file key=value pairs."""
    env = {}
    if _ENV_PATH.exists():
        with open(_ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip()
    return env


_ENV = _load_env()


def _get(key: str, default: str = "") -> str:
    """Get key from .env first, then OS environment."""
    return _ENV.get(key) or os.environ.get(key, default)


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------

COINDESK_API_KEY = _get("COINDESK_API_KEY")
"""CoinDesk API key — access to BTC price data, news, and market data."""

COINGECKO_API_KEY = _get("COINGECKO_API_KEY")
"""CoinGecko Pro API key — trending coins, market data, exchange volumes.
Endpoint: https://pro-api.coingecko.com/api/v3/
Use header: x-cg-pro-api-key: {COINGECKO_API_KEY}
"""

CRYPTOQUANT_API_KEY = _get("CRYPTOQUANT_API_KEY")
"""CryptoQuant API key — on-chain exchange flows, miner data, derivatives.
Endpoint: https://api.cryptoquant.com/v1/
Use header: Authorization: Bearer {CRYPTOQUANT_API_KEY}
On-chain signals available: exchange netflow, miner outflow, SOPR, MVRV
"""

CRYPTOSCAN_API_KEY = _get("CRYPTOSCAN_API_KEY")
"""CryptoScan API key — blockchain scanning and token analysis."""

CURRENCYLAYER_API_KEY = _get("CURRENCYLAYER_API_KEY")
"""CurrencyLayer API key — real-time forex rates (168 currencies).
Endpoint: http://apilayer.net/api/live?access_key={CURRENCYLAYER_API_KEY}&currencies=EUR,GBP,AUD...
Free plan: 250 req/month. Used for carry trade rate differentials.
"""

# Telegram (set via env or GitHub Secrets)
TELEGRAM_API_ID = _get("TELEGRAM_API_ID")
TELEGRAM_API_HASH = _get("TELEGRAM_API_HASH")
TELEGRAM_SESSION = _get("TELEGRAM_SESSION")

# Twitter / X API
TWITTER_BEARER_TOKEN = _get("TWITTER_BEARER_TOKEN")


# ---------------------------------------------------------------------------
# CoinGecko Pro helper (replaces free API calls in crypto_acceleration_engine)
# ---------------------------------------------------------------------------

def get_coingecko_headers() -> dict:
    """Return headers for CoinGecko Pro API calls."""
    if COINGECKO_API_KEY:
        return {"x-cg-pro-api-key": COINGECKO_API_KEY}
    return {}


COINGECKO_BASE = (
    "https://pro-api.coingecko.com/api/v3" if COINGECKO_API_KEY
    else "https://api.coingecko.com/api/v3"
)
"""CoinGecko base URL — Pro if key available, else free tier."""


# ---------------------------------------------------------------------------
# CurrencyLayer forex rates helper
# ---------------------------------------------------------------------------

def _fetch_currencylayer(currencies: str) -> dict:
    """Primary source: CurrencyLayer (250 req/month free plan)."""
    if not CURRENCYLAYER_API_KEY:
        return {}
    try:
        import urllib.request
        import json
        url = (f"http://apilayer.net/api/live"
               f"?access_key={CURRENCYLAYER_API_KEY}&currencies={currencies}&format=1")
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read())
        if not data.get("success", True):
            return {}  # Rate-limited or error
        quotes = data.get("quotes", {})
        if quotes:
            return quotes
    except Exception:
        pass
    return {}


def _fetch_frankfurter(currencies: str) -> dict:
    """Fallback source: Frankfurter API (free, unlimited, no key needed).
    Converts Frankfurter format {EUR: 0.92, ...} to CurrencyLayer format {USDEUR: 0.92, ...}
    for compatibility with downstream consumers.
    """
    try:
        import urllib.request
        import json
        url = f"https://api.frankfurter.dev/v1/latest?from=USD&to={currencies}"
        req = urllib.request.Request(url, headers={"User-Agent": "KIMI/11.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        rates = data.get("rates", {})
        if rates:
            # Convert to CurrencyLayer format: {USDEUR: 0.92, USDGBP: 0.79, ...}
            return {f"USD{k}": v for k, v in rates.items()}
    except Exception:
        pass
    return {}


def _fetch_yfinance_forex(currencies: str) -> dict:
    """Last-resort fallback: yfinance forex symbols (free, unlimited)."""
    try:
        import yfinance as yf
        currency_list = [c.strip() for c in currencies.split(",")]
        quotes = {}
        for cur in currency_list:
            try:
                ticker = yf.Ticker(f"{cur}=X")
                info = ticker.fast_info
                if hasattr(info, "last_price") and info.last_price:
                    quotes[f"USD{cur}"] = float(info.last_price)
                else:
                    hist = ticker.history(period="1d")
                    if hist is not None and len(hist) > 0:
                        quotes[f"USD{cur}"] = float(hist["Close"].iloc[-1])
            except Exception:
                continue
        return quotes
    except ImportError:
        pass
    return {}


def get_live_forex_rates(currencies: str = "EUR,GBP,AUD,NZD,CAD,CHF,JPY") -> dict:
    """
    Fetch live forex rates with fallback chain:
      1. CurrencyLayer (primary, 250 req/month free plan)
      2. Frankfurter API (free, unlimited, no key needed)
      3. yfinance forex symbols (free, unlimited)
    Returns {USDEUR: 0.92, USDGBP: 0.79, ...}
    """
    # Try CurrencyLayer first
    rates = _fetch_currencylayer(currencies)
    if rates:
        return rates

    # Fallback to Frankfurter API (free, unlimited)
    rates = _fetch_frankfurter(currencies)
    if rates:
        return rates

    # Last resort: yfinance
    rates = _fetch_yfinance_forex(currencies)
    if rates:
        return rates

    return {}


# ---------------------------------------------------------------------------
# CryptoQuant on-chain signals (exchange netflow)
# ---------------------------------------------------------------------------

def get_exchange_netflow(symbol: str = "btc", window: str = "day") -> dict:
    """
    CryptoQuant exchange netflow: negative = outflow (bullish), positive = inflow (bearish).
    symbol: 'btc', 'eth'
    Returns {value, unit, block_date}
    """
    if not CRYPTOQUANT_API_KEY:
        return {}
    try:
        import urllib.request
        import json
        url = f"https://api.cryptoquant.com/v1/{symbol}/exchange-flows/netflow?window={window}&limit=1"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {CRYPTOQUANT_API_KEY}",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        results = data.get("result", {}).get("data", [])
        if results:
            return results[-1]
    except Exception:
        pass
    return {}


if __name__ == "__main__":
    print("=== API Config Status ===")
    print(f"CoinDesk:       {'OK' if COINDESK_API_KEY else 'MISSING'}")
    print(f"CoinGecko Pro:  {'OK' if COINGECKO_API_KEY else 'MISSING (using free tier)'}")
    print(f"CryptoQuant:    {'OK' if CRYPTOQUANT_API_KEY else 'MISSING'}")
    print(f"CryptoScan:     {'OK' if CRYPTOSCAN_API_KEY else 'MISSING'}")
    print(f"CurrencyLayer:  {'OK' if CURRENCYLAYER_API_KEY else 'MISSING'}")
    print(f"Telegram:       {'OK' if TELEGRAM_API_ID else 'MISSING'}")
    print(f"Twitter/X:      {'OK' if TWITTER_BEARER_TOKEN else 'MISSING'}")
    print(f"\nCoinGecko base: {COINGECKO_BASE}")
    if CURRENCYLAYER_API_KEY:
        print("\nTesting CurrencyLayer...")
        rates = get_live_forex_rates("EUR,GBP,AUD")
        print(f"  Rates: {rates}")
    if CRYPTOQUANT_API_KEY:
        print("\nTesting CryptoQuant BTC netflow...")
        flow = get_exchange_netflow("btc")
        print(f"  BTC netflow: {flow}")
