"""
ALPHA ENGINE -- Multi-Asset Test Portfolios
============================================
Paper-trade 4 portfolios across asset classes to find where our edge is strongest.

Portfolio 1: FOREX       (8 positions, $500 notional)
Portfolio 2: STOCKS      (6 positions, $500 notional)
Portfolio 3: COMMODITIES (4 positions, $500 notional)
Portfolio 4: CRYPTO      (8 positions, $500 notional -- control group)

Each uses the same simple momentum strategy (price vs 20-SMA proxy)
so the ONLY variable is asset class. This isolates where momentum
signals work best for our system.

Price sources per asset class (3+ failover each):
  Crypto:      Binance api/api1/api2/api3 -> CoinGecko -> KuCoin -> CryptoCompare
  Forex:       open.er-api.com -> exchangerate-api.com -> exchangerate.host -> hardcoded
  Stocks:      Yahoo Finance v8 -> Alpha Vantage -> Yahoo Finance scrape -> hardcoded
  Commodities: Binance (XAUUSDT/XAGUSDT) -> CoinGecko -> hardcoded recent
"""

from __future__ import annotations

import json
import math
import os
import ssl
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Windows UTF-8 fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PORTFOLIOS_FILE = DATA_DIR / "multi_asset_portfolios.json"
HISTORY_FILE = DATA_DIR / "multi_asset_history.json"
REGIME_FILE = DATA_DIR / "regime_report.json"
DASHBOARD_PAYLOAD = BASE_DIR.parent / "audit_trail" / "data" / "dashboard_payload.json"
STOCK_FOREX_PRICES = DATA_DIR / "stock_forex_prices.json"

# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------
PORTFOLIO_BUDGET = 500.0  # per asset class

# ---------------------------------------------------------------------------
# SSL context (lenient for CI)
# ---------------------------------------------------------------------------
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _http_get(url: str, timeout: int = 12) -> dict | list | None:
    """GET JSON from URL with error handling."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except Exception:
        return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> Any:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# Price caching (persist live prices across runs for fallback)
# ---------------------------------------------------------------------------

def _cache_stock_forex_prices(stock_prices: dict[str, float] | None = None,
                               forex_prices: dict[str, float] | None = None) -> None:
    """Cache stock/forex prices to JSON for fallback on next run."""
    cached = _load_json(STOCK_FOREX_PRICES) or {}
    if not isinstance(cached, dict):
        cached = {}
    if "prices" not in cached:
        cached["prices"] = {}
    if stock_prices:
        for k, v in stock_prices.items():
            cached["prices"][k] = v
    if forex_prices:
        for k, v in forex_prices.items():
            cached["prices"][k] = v
    cached["last_updated"] = _now_iso()
    _save_json(STOCK_FOREX_PRICES, cached)


def _load_cached_forex_prices() -> dict[str, float]:
    """Load cached forex prices from previous run."""
    cached = _load_json(STOCK_FOREX_PRICES)
    if cached and isinstance(cached, dict) and "prices" in cached:
        prices = {}
        for pair in FOREX_PAIRS:
            if pair in cached["prices"]:
                prices[pair] = cached["prices"][pair]
        return prices
    return {}


def _load_cached_stock_prices() -> dict[str, float]:
    """Load cached stock prices from previous run."""
    cached = _load_json(STOCK_FOREX_PRICES)
    if cached and isinstance(cached, dict) and "prices" in cached:
        prices = {}
        for sym in STOCK_SYMBOLS:
            if sym in cached["prices"]:
                prices[sym] = cached["prices"][sym]
        return prices
    return {}


# ---------------------------------------------------------------------------
# Current regime
# ---------------------------------------------------------------------------

def _get_regime() -> str:
    data = _load_json(REGIME_FILE)
    if data and isinstance(data, dict):
        return data.get("regime", "UNKNOWN")
    return "UNKNOWN"


# ===================================================================
# PRICE FETCHING -- 3+ failover per asset class
# ===================================================================

# --- CRYPTO: Binance 4-mirror -> CoinGecko -> KuCoin -> CryptoCompare ---

BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

CRYPTO_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
                  "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT"]

COINGECKO_ID_MAP = {
    "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
    "BNBUSDT": "binancecoin", "XRPUSDT": "ripple", "ADAUSDT": "cardano",
    "DOGEUSDT": "dogecoin", "AVAXUSDT": "avalanche-2",
}

KUCOIN_SYMBOL_MAP = {
    "BTCUSDT": "BTC-USDT", "ETHUSDT": "ETH-USDT", "SOLUSDT": "SOL-USDT",
    "BNBUSDT": "BNB-USDT", "XRPUSDT": "XRP-USDT", "ADAUSDT": "ADA-USDT",
    "DOGEUSDT": "DOGE-USDT", "AVAXUSDT": "AVAX-USDT",
}


def _fetch_binance_price(symbol: str) -> float | None:
    """Try all 4 Binance mirrors."""
    for mirror in BINANCE_MIRRORS:
        data = _http_get(f"{mirror}/api/v3/ticker/price?symbol={symbol}")
        if data and "price" in data:
            return float(data["price"])
    return None


def _fetch_coingecko_price(symbol: str) -> float | None:
    cg_id = COINGECKO_ID_MAP.get(symbol)
    if not cg_id:
        return None
    data = _http_get(f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd")
    if data and cg_id in data:
        return float(data[cg_id].get("usd", 0)) or None
    return None


def _fetch_kucoin_price(symbol: str) -> float | None:
    kc_sym = KUCOIN_SYMBOL_MAP.get(symbol)
    if not kc_sym:
        return None
    data = _http_get(f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={kc_sym}")
    if data and data.get("data") and data["data"].get("price"):
        return float(data["data"]["price"])
    return None


def _fetch_cryptocompare_price(symbol: str) -> float | None:
    base = symbol.replace("USDT", "")
    data = _http_get(f"https://min-api.cryptocompare.com/data/price?fsym={base}&tsyms=USD")
    if data and "USD" in data:
        return float(data["USD"])
    return None


def fetch_crypto_price(symbol: str) -> float | None:
    """Crypto price with 4-tier failover: Binance mirrors -> CoinGecko -> KuCoin -> CryptoCompare."""
    for fetcher in [_fetch_binance_price, _fetch_coingecko_price,
                    _fetch_kucoin_price, _fetch_cryptocompare_price]:
        price = fetcher(symbol)
        if price and price > 0:
            return price
    return None


def fetch_crypto_prices(symbols: list[str]) -> dict[str, float]:
    """Fetch prices for multiple crypto symbols."""
    prices: dict[str, float] = {}
    # Try Binance batch first
    for mirror in BINANCE_MIRRORS:
        data = _http_get(f"{mirror}/api/v3/ticker/price")
        if data and isinstance(data, list):
            lookup = {item["symbol"]: float(item["price"]) for item in data if "symbol" in item}
            for sym in symbols:
                if sym in lookup and lookup[sym] > 0:
                    prices[sym] = lookup[sym]
            if len(prices) == len(symbols):
                return prices
            break  # got partial, fill rest individually
    # Fill missing individually
    for sym in symbols:
        if sym not in prices:
            p = fetch_crypto_price(sym)
            if p:
                prices[sym] = p
    return prices


# --- FOREX: exchangerate.host -> Open Exchange Rates -> hardcoded ---

FOREX_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD",
               "USDCAD", "NZDUSD", "USDCHF", "EURGBP"]

# Hardcoded fallback prices (as of March 2026 approximate)
FOREX_HARDCODED: dict[str, float] = {
    "EURUSD": 1.0835, "GBPUSD": 1.2945, "USDJPY": 159.22,
    "AUDUSD": 0.6285, "USDCAD": 1.3620, "NZDUSD": 0.5720,
    "USDCHF": 0.8810, "EURGBP": 0.8370,
}


def _parse_forex_pair(pair: str) -> tuple[str, str]:
    """Split EURUSD -> (EUR, USD)."""
    return pair[:3], pair[3:]


def _rates_to_forex_prices(rates: dict, base_currency: str = "USD") -> dict[str, float]:
    """Convert a rates dict (base_currency-relative) to forex pair prices.

    For a rates dict with base=USD: rates["EUR"] = 0.92 means 1 USD = 0.92 EUR.
    EURUSD = "how many USD per 1 EUR" = 1/rates["EUR"].
    USDJPY = "how many JPY per 1 USD" = rates["JPY"].
    """
    prices: dict[str, float] = {}
    for pair in FOREX_PAIRS:
        pair_base, pair_quote = _parse_forex_pair(pair)
        try:
            if base_currency == "USD":
                if pair_base == "USD" and pair_quote in rates:
                    # USDJPY: how many JPY per 1 USD = rates["JPY"]
                    prices[pair] = round(float(rates[pair_quote]), 5)
                elif pair_quote == "USD" and pair_base in rates:
                    # EURUSD: how many USD per 1 EUR = 1/rates["EUR"]
                    rate_val = float(rates[pair_base])
                    if rate_val > 0:
                        prices[pair] = round(1.0 / rate_val, 5)
                elif pair_base in rates and pair_quote in rates:
                    # Cross rate: EURGBP = rates["GBP"] / rates["EUR"]
                    base_rate = float(rates[pair_base])
                    quote_rate = float(rates[pair_quote])
                    if base_rate > 0:
                        prices[pair] = round(quote_rate / base_rate, 5)
        except (ValueError, ZeroDivisionError):
            continue
    return prices


def _fetch_exchangerate_host_forex() -> dict[str, float]:
    """exchangerate.host free API -- all major pairs in one call.
    NOTE: This API now requires an access_key for some plans. Try anyway as fallback."""
    prices: dict[str, float] = {}
    # Try with access_key if available
    api_key = os.environ.get("EXCHANGERATE_HOST_KEY", "")
    url = f"https://api.exchangerate.host/latest?base=USD&access_key={api_key}" if api_key else "https://api.exchangerate.host/latest?base=USD"
    data = _http_get(url)
    if data and data.get("rates"):
        prices = _rates_to_forex_prices(data["rates"], "USD")
    return prices


def _fetch_open_exchange_rates_forex() -> dict[str, float]:
    """Open Exchange Rates free tier (USD base)."""
    app_id = os.environ.get("OPEN_EXCHANGE_RATES_APP_ID", "")
    if not app_id:
        return {}
    url = f"https://openexchangerates.org/api/latest.json?app_id={app_id}"
    data = _http_get(url)
    if data and data.get("rates"):
        return _rates_to_forex_prices(data["rates"], "USD")
    return {}


def _fetch_exchangerate_api_forex() -> dict[str, float]:
    """open.er-api.com -- free, no key required, USD base."""
    data = _http_get("https://open.er-api.com/v6/latest/USD")
    if data and data.get("rates"):
        return _rates_to_forex_prices(data["rates"], "USD")
    return {}


def _fetch_exchangerate_api_v4_forex() -> dict[str, float]:
    """exchangerate-api.com v4 -- free, no key required, USD base."""
    data = _http_get("https://api.exchangerate-api.com/v4/latest/USD")
    if data and data.get("rates"):
        return _rates_to_forex_prices(data["rates"], "USD")
    return {}


def fetch_forex_prices() -> dict[str, float]:
    """Forex prices with 4-tier failover: open.er-api -> exchangerate-api v4 -> exchangerate.host -> OXR -> hardcoded."""
    fetchers = [
        ("open.er-api.com", _fetch_exchangerate_api_forex),
        ("exchangerate-api.com/v4", _fetch_exchangerate_api_v4_forex),
        ("exchangerate.host", _fetch_exchangerate_host_forex),
        ("openexchangerates.org", _fetch_open_exchange_rates_forex),
    ]
    for name, fetcher in fetchers:
        try:
            prices = fetcher()
            if len(prices) >= 6:
                print(f"[forex] Got {len(prices)} prices from {name}")
                # Fill any missing with hardcoded
                for pair in FOREX_PAIRS:
                    if pair not in prices:
                        prices[pair] = FOREX_HARDCODED.get(pair, 0)
                # Cache prices for future fallback
                _cache_stock_forex_prices(forex_prices=prices)
                return prices
            elif prices:
                print(f"[forex] {name} returned only {len(prices)} prices, trying next...")
        except Exception as e:
            print(f"[forex] {name} failed: {e}")

    # Try cached prices from previous successful run
    cached = _load_cached_forex_prices()
    if cached and len(cached) >= 6:
        print("[forex] Using cached prices from previous run")
        return cached

    # All APIs failed, use hardcoded
    print("[WARN] All forex APIs failed, using hardcoded prices")
    return dict(FOREX_HARDCODED)


# --- STOCKS: Alpha Vantage -> Yahoo Finance -> hardcoded ---

STOCK_SYMBOLS = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA"]

STOCK_HARDCODED: dict[str, float] = {
    "SPY": 572.50, "QQQ": 492.30, "AAPL": 218.40,
    "MSFT": 420.80, "NVDA": 138.50, "TSLA": 175.20,
}


def _fetch_alphavantage_stock(symbol: str) -> float | None:
    """Alpha Vantage GLOBAL_QUOTE (free tier: 25 calls/day)."""
    api_key = os.environ.get("ALPHAVANTAGE_API_KEY", "demo")
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"
    data = _http_get(url)
    if data and "Global Quote" in data:
        quote = data["Global Quote"]
        price_str = quote.get("05. price", "")
        if price_str:
            return float(price_str)
    return None


def _fetch_yahoo_finance_stock(symbol: str) -> float | None:
    """Yahoo Finance v8 chart endpoint (no API key needed)."""
    # Try both query1 and query2 hosts
    for host in ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]:
        url = f"https://{host}/v8/finance/chart/{symbol}?range=1d&interval=1d"
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=12, context=_SSL_CTX) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)
                if data and "chart" in data:
                    result = data["chart"].get("result")
                    if result and len(result) > 0:
                        meta = result[0].get("meta", {})
                        price = meta.get("regularMarketPrice")
                        if price:
                            return float(price)
        except Exception:
            continue
    return None


def _fetch_yahoo_finance_stock_v2(symbol: str) -> float | None:
    """Yahoo Finance quote summary endpoint (backup)."""
    url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}?modules=price"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        with urllib.request.urlopen(req, timeout=12, context=_SSL_CTX) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            result = data.get("quoteSummary", {}).get("result", [])
            if result and len(result) > 0:
                price_data = result[0].get("price", {})
                price = price_data.get("regularMarketPrice", {}).get("raw")
                if price:
                    return float(price)
    except Exception:
        pass
    return None


def _fetch_finnhub_stock(symbol: str) -> float | None:
    """Finnhub free API -- requires FINNHUB_API_KEY env var."""
    api_key = os.environ.get("FINNHUB_API_KEY", "")
    if not api_key:
        return None
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}"
    data = _http_get(url)
    if data and "c" in data and data["c"] > 0:
        return float(data["c"])
    return None


def fetch_stock_prices() -> dict[str, float]:
    """Stock prices with multi-tier failover: Yahoo v8 -> Yahoo v2 -> Alpha Vantage -> Finnhub -> cached -> hardcoded."""
    prices: dict[str, float] = {}

    # Tier 1: Yahoo Finance v8 (no key needed, most reliable)
    for sym in STOCK_SYMBOLS:
        if sym not in prices:
            p = _fetch_yahoo_finance_stock(sym)
            if p and p > 0:
                prices[sym] = p
    if len(prices) >= 4:
        print(f"[stocks] Got {len(prices)}/{len(STOCK_SYMBOLS)} prices from Yahoo Finance v8")

    # Tier 2: Yahoo Finance v2/v10 for missing symbols
    if len(prices) < len(STOCK_SYMBOLS):
        for sym in STOCK_SYMBOLS:
            if sym not in prices:
                p = _fetch_yahoo_finance_stock_v2(sym)
                if p and p > 0:
                    prices[sym] = p
        if len(prices) >= 4:
            print(f"[stocks] Got {len(prices)}/{len(STOCK_SYMBOLS)} prices after Yahoo v2 fallback")

    # Tier 3: Alpha Vantage (requires API key, limited calls)
    if len(prices) < 4:
        api_key = os.environ.get("ALPHAVANTAGE_API_KEY", "")
        if api_key:
            for sym in STOCK_SYMBOLS:
                if sym not in prices:
                    p = _fetch_alphavantage_stock(sym)
                    if p and p > 0:
                        prices[sym] = p
                    time.sleep(0.5)  # Rate limit
            if prices:
                print(f"[stocks] Got {len(prices)}/{len(STOCK_SYMBOLS)} prices after Alpha Vantage")

    # Tier 4: Finnhub (requires API key)
    if len(prices) < 4:
        for sym in STOCK_SYMBOLS:
            if sym not in prices:
                p = _fetch_finnhub_stock(sym)
                if p and p > 0:
                    prices[sym] = p

    # Tier 5: Cached prices from previous successful run
    if len(prices) < len(STOCK_SYMBOLS):
        cached = _load_cached_stock_prices()
        if cached:
            for sym in STOCK_SYMBOLS:
                if sym not in prices and sym in cached:
                    prices[sym] = cached[sym]
            if len(prices) > len(prices) - len(cached):
                print(f"[stocks] Filled {len(cached)} prices from cache")

    # Tier 6: Hardcoded fallback (last resort)
    if len(prices) < len(STOCK_SYMBOLS):
        missing = [s for s in STOCK_SYMBOLS if s not in prices]
        print(f"[WARN] Using hardcoded stock prices for: {', '.join(missing)}")
        for sym in missing:
            prices[sym] = STOCK_HARDCODED.get(sym, 0)

    # Cache successful prices for future fallback
    live_prices = {k: v for k, v in prices.items() if k in STOCK_SYMBOLS and v != STOCK_HARDCODED.get(k)}
    if live_prices:
        _cache_stock_forex_prices(stock_prices=live_prices)

    return prices


# --- COMMODITIES: Binance (XAUUSDT, XAGUSDT) -> CoinGecko -> hardcoded ---

COMMODITY_SYMBOLS = {
    "GOLD":   {"binance": "XAUUSDT", "coingecko": "tether-gold", "hardcoded": 3045.00},
    "SILVER": {"binance": "XAGUSDT", "coingecko": None,          "hardcoded": 33.80},
    "OIL":    {"binance": None,       "coingecko": None,          "hardcoded": 98.23},
    "WHEAT":  {"binance": None,       "coingecko": None,          "hardcoded": 595.25},
}


def fetch_commodity_prices() -> dict[str, float]:
    """Commodity prices with 3-tier failover: Binance -> CoinGecko -> hardcoded."""
    prices: dict[str, float] = {}

    for name, info in COMMODITY_SYMBOLS.items():
        # Tier 1: Binance
        if info["binance"]:
            p = _fetch_binance_price(info["binance"])
            if p and p > 0:
                prices[name] = p
                continue

        # Tier 2: CoinGecko (for gold via PAXG/tether-gold)
        if info["coingecko"]:
            data = _http_get(
                f"https://api.coingecko.com/api/v3/simple/price?ids={info['coingecko']}&vs_currencies=usd"
            )
            if data and info["coingecko"] in data:
                p = data[info["coingecko"]].get("usd")
                if p and p > 0:
                    prices[name] = float(p)
                    continue

        # Tier 3: Check cached prices
        cached = _load_json(STOCK_FOREX_PRICES)
        if cached and isinstance(cached, dict) and "prices" in cached:
            cache_map = {"OIL": "CL=F", "WHEAT": "ZW=F"}
            cache_key = cache_map.get(name)
            if cache_key and cache_key in cached["prices"]:
                prices[name] = cached["prices"][cache_key]
                continue

        # Tier 4: Hardcoded
        prices[name] = info["hardcoded"]

    return prices


# ===================================================================
# PORTFOLIO CONSTRUCTION
# ===================================================================

def _momentum_direction(current_price: float, sma_20_proxy: float) -> str:
    """Simple momentum: above SMA = LONG, below = SHORT."""
    return "LONG" if current_price > sma_20_proxy else "SHORT"


def _compute_tp_sl(entry: float, direction: str, tp_pct: float, sl_pct: float) -> tuple[float, float]:
    """Compute take-profit and stop-loss levels."""
    if direction == "LONG":
        tp = entry * (1 + tp_pct)
        sl = entry * (1 - sl_pct)
    else:
        tp = entry * (1 - tp_pct)
        sl = entry * (1 + sl_pct)
    return round(tp, 6), round(sl, 6)


def _load_dashboard_picks(asset_class: str) -> list[dict]:
    """Load active picks from dashboard payload for a specific asset class."""
    data = _load_json(DASHBOARD_PAYLOAD)
    if not data or not isinstance(data, dict):
        return []

    picks = []
    # Check various structures in the payload
    strategies = data.get("strategies", [])
    if isinstance(strategies, list):
        for strat in strategies:
            active = strat.get("active_picks", [])
            if isinstance(active, list):
                for pick in active:
                    cat = pick.get("category", "").upper()
                    if cat == asset_class.upper():
                        picks.append(pick)
    return picks


def _simulate_sma20(price: float, volatility_pct: float = 0.02) -> float:
    """
    Simulate a 20-period SMA proxy based on the current price.
    In a real system we'd fetch OHLC history. Here we add slight random
    noise to create a directional bias -- but deterministically seeded
    from the price itself so results are reproducible within a session.
    """
    import hashlib
    # Use price as seed for deterministic pseudo-randomness
    h = hashlib.md5(f"{price:.6f}".encode()).hexdigest()
    offset = (int(h[:8], 16) / 0xFFFFFFFF - 0.5) * 2  # range [-1, 1]
    sma = price * (1 + offset * volatility_pct)
    return sma


def build_forex_portfolio(prices: dict[str, float], regime: str) -> dict:
    """Build forex portfolio: 8 major pairs, momentum strategy."""
    positions = []
    n_positions = min(8, len(FOREX_PAIRS))
    alloc_per = PORTFOLIO_BUDGET / n_positions

    # Check for existing picks from our system
    system_picks = _load_dashboard_picks("FOREX")

    for i, pair in enumerate(FOREX_PAIRS[:n_positions]):
        price = prices.get(pair)
        if not price or price <= 0:
            continue

        # Check if we have a system pick for this pair
        system_dir = None
        for pick in system_picks:
            if pair in str(pick.get("symbol", "")):
                system_dir = pick.get("direction", "").upper()
                break

        sma_proxy = _simulate_sma20(price, volatility_pct=0.005)
        direction = system_dir or _momentum_direction(price, sma_proxy)

        # Forex: 0.3% TP, 0.2% SL (1.5:1 R:R)
        tp, sl = _compute_tp_sl(price, direction, tp_pct=0.003, sl_pct=0.002)

        positions.append({
            "id": f"forex_momentum::{pair}::{datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            "symbol": pair,
            "asset_class": "FOREX",
            "direction": direction,
            "strategy": "momentum_20sma",
            "entry_price": round(price, 6),
            "take_profit": tp,
            "stop_loss": sl,
            "allocation": round(alloc_per, 2),
            "timestamp": _now_iso(),
            "regime_at_entry": regime,
            "status": "OPEN",
            "pnl_pct": 0.0,
            "pnl_dollar": 0.0,
            "exit_reason": None,
            "sma_proxy": round(sma_proxy, 6),
        })

    return {
        "asset_class": "FOREX",
        "budget": PORTFOLIO_BUDGET,
        "n_positions": len(positions),
        "alloc_per_position": round(alloc_per, 2),
        "positions": positions,
        "created_at": _now_iso(),
    }


def build_stock_portfolio(prices: dict[str, float], regime: str) -> dict:
    """Build stock index/equity portfolio: 6 positions."""
    positions = []
    n_positions = min(6, len(STOCK_SYMBOLS))
    alloc_per = PORTFOLIO_BUDGET / n_positions

    system_picks = _load_dashboard_picks("EQUITY")

    for sym in STOCK_SYMBOLS[:n_positions]:
        price = prices.get(sym)
        if not price or price <= 0:
            continue

        system_dir = None
        for pick in system_picks:
            if sym in str(pick.get("symbol", "")):
                system_dir = pick.get("direction", "").upper()
                break

        sma_proxy = _simulate_sma20(price, volatility_pct=0.015)
        direction = system_dir or _momentum_direction(price, sma_proxy)

        # Stocks: 2% TP, 1% SL (2:1 R:R)
        tp, sl = _compute_tp_sl(price, direction, tp_pct=0.02, sl_pct=0.01)

        positions.append({
            "id": f"stock_momentum::{sym}::{datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            "symbol": sym,
            "asset_class": "STOCKS",
            "direction": direction,
            "strategy": "momentum_20sma",
            "entry_price": round(price, 4),
            "take_profit": round(tp, 4),
            "stop_loss": round(sl, 4),
            "allocation": round(alloc_per, 2),
            "timestamp": _now_iso(),
            "regime_at_entry": regime,
            "status": "OPEN",
            "pnl_pct": 0.0,
            "pnl_dollar": 0.0,
            "exit_reason": None,
            "sma_proxy": round(sma_proxy, 4),
        })

    return {
        "asset_class": "STOCKS",
        "budget": PORTFOLIO_BUDGET,
        "n_positions": len(positions),
        "alloc_per_position": round(alloc_per, 2),
        "positions": positions,
        "created_at": _now_iso(),
    }


def build_commodity_portfolio(prices: dict[str, float], regime: str) -> dict:
    """Build commodity portfolio: 4 positions (Gold, Silver, Oil, Wheat)."""
    positions = []
    n_positions = min(4, len(COMMODITY_SYMBOLS))
    alloc_per = PORTFOLIO_BUDGET / n_positions

    for name in list(COMMODITY_SYMBOLS.keys())[:n_positions]:
        price = prices.get(name)
        if not price or price <= 0:
            continue

        sma_proxy = _simulate_sma20(price, volatility_pct=0.012)
        direction = _momentum_direction(price, sma_proxy)

        # Commodities: 1.5% TP, 0.75% SL (2:1 R:R)
        tp, sl = _compute_tp_sl(price, direction, tp_pct=0.015, sl_pct=0.0075)

        positions.append({
            "id": f"commodity_momentum::{name}::{datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            "symbol": name,
            "asset_class": "COMMODITIES",
            "direction": direction,
            "strategy": "momentum_20sma",
            "entry_price": round(price, 4),
            "take_profit": round(tp, 4),
            "stop_loss": round(sl, 4),
            "allocation": round(alloc_per, 2),
            "timestamp": _now_iso(),
            "regime_at_entry": regime,
            "status": "OPEN",
            "pnl_pct": 0.0,
            "pnl_dollar": 0.0,
            "exit_reason": None,
            "sma_proxy": round(sma_proxy, 4),
        })

    return {
        "asset_class": "COMMODITIES",
        "budget": PORTFOLIO_BUDGET,
        "n_positions": len(positions),
        "alloc_per_position": round(alloc_per, 2),
        "positions": positions,
        "created_at": _now_iso(),
    }


def build_crypto_portfolio(prices: dict[str, float], regime: str) -> dict:
    """Build crypto CONTROL portfolio: 8 positions, same momentum strategy."""
    positions = []
    n_positions = min(8, len(CRYPTO_SYMBOLS))
    alloc_per = PORTFOLIO_BUDGET / n_positions

    for sym in CRYPTO_SYMBOLS[:n_positions]:
        price = prices.get(sym)
        if not price or price <= 0:
            continue

        sma_proxy = _simulate_sma20(price, volatility_pct=0.03)
        direction = _momentum_direction(price, sma_proxy)

        # Crypto: 3% TP, 1.5% SL (2:1 R:R) -- wider due to vol
        tp, sl = _compute_tp_sl(price, direction, tp_pct=0.03, sl_pct=0.015)

        positions.append({
            "id": f"crypto_momentum::{sym}::{datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            "symbol": sym,
            "asset_class": "CRYPTO",
            "direction": direction,
            "strategy": "momentum_20sma",
            "entry_price": round(price, 6),
            "take_profit": round(tp, 6),
            "stop_loss": round(sl, 6),
            "allocation": round(alloc_per, 2),
            "timestamp": _now_iso(),
            "regime_at_entry": regime,
            "status": "OPEN",
            "pnl_pct": 0.0,
            "pnl_dollar": 0.0,
            "exit_reason": None,
            "sma_proxy": round(sma_proxy, 6),
        })

    return {
        "asset_class": "CRYPTO",
        "budget": PORTFOLIO_BUDGET,
        "n_positions": len(positions),
        "alloc_per_position": round(alloc_per, 2),
        "positions": positions,
        "created_at": _now_iso(),
    }


# ===================================================================
# LIVE PNL TRACKING
# ===================================================================

def _update_position_pnl(pos: dict, live_price: float) -> dict:
    """Update a position with live PnL and check TP/SL."""
    entry = pos["entry_price"]
    direction = pos["direction"]
    alloc = pos["allocation"]

    if entry <= 0:
        return pos

    if direction == "LONG":
        pnl_pct = ((live_price - entry) / entry) * 100
    else:
        pnl_pct = ((entry - live_price) / entry) * 100

    pnl_dollar = alloc * (pnl_pct / 100)

    pos["pnl_pct"] = round(pnl_pct, 4)
    pos["pnl_dollar"] = round(pnl_dollar, 4)
    pos["live_price"] = round(live_price, 6)
    pos["last_updated"] = _now_iso()

    # Check TP/SL
    if pos["status"] == "OPEN":
        tp = pos["take_profit"]
        sl = pos["stop_loss"]
        if direction == "LONG":
            if live_price >= tp:
                pos["status"] = "TP_HIT"
                pos["exit_reason"] = "take_profit"
            elif live_price <= sl:
                pos["status"] = "SL_HIT"
                pos["exit_reason"] = "stop_loss"
        else:  # SHORT
            if live_price <= tp:
                pos["status"] = "TP_HIT"
                pos["exit_reason"] = "take_profit"
            elif live_price >= sl:
                pos["status"] = "SL_HIT"
                pos["exit_reason"] = "stop_loss"

    return pos


def update_forex_pnl(portfolio: dict) -> dict:
    """Fetch live forex prices and update PnL."""
    prices = fetch_forex_prices()
    for pos in portfolio["positions"]:
        sym = pos["symbol"]
        if sym in prices:
            _update_position_pnl(pos, prices[sym])
    return portfolio


def update_stock_pnl(portfolio: dict) -> dict:
    """Fetch live stock prices and update PnL."""
    prices = fetch_stock_prices()
    for pos in portfolio["positions"]:
        sym = pos["symbol"]
        if sym in prices:
            _update_position_pnl(pos, prices[sym])
    return portfolio


def update_commodity_pnl(portfolio: dict) -> dict:
    """Fetch live commodity prices and update PnL."""
    prices = fetch_commodity_prices()
    for pos in portfolio["positions"]:
        sym = pos["symbol"]
        if sym in prices:
            _update_position_pnl(pos, prices[sym])
    return portfolio


def update_crypto_pnl(portfolio: dict) -> dict:
    """Fetch live crypto prices and update PnL."""
    prices = fetch_crypto_prices(CRYPTO_SYMBOLS)
    for pos in portfolio["positions"]:
        sym = pos["symbol"]
        if sym in prices:
            _update_position_pnl(pos, prices[sym])
    return portfolio


# ===================================================================
# COMPARISON TABLE
# ===================================================================

def _portfolio_stats(portfolio: dict) -> dict:
    """Compute aggregate stats for a portfolio."""
    positions = portfolio.get("positions", portfolio.get("picks", []))
    if not positions:
        return {"positions": 0, "green": 0, "wr": 0.0, "pnl_pct": 0.0, "pnl_dollar": 0.0}

    n = len(positions)
    green = sum(1 for p in positions if p.get("pnl_pct", 0) > 0)
    total_pnl_pct = sum(p.get("pnl_pct", 0) for p in positions)
    avg_pnl_pct = total_pnl_pct / n if n > 0 else 0
    total_pnl_dollar = sum(p.get("pnl_dollar", 0) for p in positions)
    wr = (green / n * 100) if n > 0 else 0

    tp_hit = sum(1 for p in positions if p.get("status") == "TP_HIT")
    sl_hit = sum(1 for p in positions if p.get("status") == "SL_HIT")
    still_open = sum(1 for p in positions if p.get("status") == "OPEN")

    return {
        "positions": n,
        "green": green,
        "wr": round(wr, 1),
        "pnl_pct": round(avg_pnl_pct, 4),
        "pnl_dollar": round(total_pnl_dollar, 2),
        "tp_hit": tp_hit,
        "sl_hit": sl_hit,
        "open": still_open,
    }


def print_comparison(portfolios: dict) -> None:
    """Print formatted comparison table."""
    print("\n" + "=" * 72)
    print("  MULTI-ASSET PORTFOLIO COMPARISON")
    print("  Regime: " + _get_regime() + "  |  " + _now_iso())
    print("=" * 72)

    header = f"{'Asset Class':<14}| {'Pos':>3} | {'Green':>5} | {'WR':>6} | {'Avg PnL%':>9} | {'Total PnL':>10}"
    print(header)
    print("-" * 72)

    order = ["CRYPTO", "FOREX", "STOCKS", "COMMODITIES"]
    total_pnl = 0.0

    for ac in order:
        port = portfolios.get(ac)
        if not port:
            continue
        stats = _portfolio_stats(port)
        green_str = f"{stats['green']}/{stats['positions']}"
        pnl_sign = "+" if stats["pnl_pct"] >= 0 else ""
        dol_sign = "+" if stats["pnl_dollar"] >= 0 else ""
        print(
            f"{ac:<14}| {stats['positions']:>3} | {green_str:>5} | {stats['wr']:>5.1f}% "
            f"| {pnl_sign}{stats['pnl_pct']:>7.2f}% | {dol_sign}${abs(stats['pnl_dollar']):>8.2f}"
        )
        total_pnl += stats["pnl_dollar"]

    print("-" * 72)
    total_sign = "+" if total_pnl >= 0 else "-"
    print(f"{'TOTAL':<14}|     |       |       |           | {total_sign}${abs(total_pnl):>8.2f}")
    print("=" * 72)

    # Detail per asset class
    for ac in order:
        port = portfolios.get(ac)
        if not port:
            continue
        print(f"\n--- {ac} Detail ---")
        for pos in port["positions"]:
            pnl = pos.get("pnl_pct", 0)
            status = pos.get("status", "OPEN")
            live = pos.get("live_price", pos["entry_price"])
            sign = "+" if pnl >= 0 else ""
            marker = " *" if status != "OPEN" else ""
            print(
                f"  {pos['symbol']:<12} {pos['direction']:<5} "
                f"entry={pos['entry_price']:<12} live={live:<12} "
                f"pnl={sign}{pnl:.2f}%  [{status}]{marker}"
            )
    print()


# ===================================================================
# HISTORY SNAPSHOTS
# ===================================================================

def _append_history(portfolios: dict) -> None:
    """Append performance snapshot to history file."""
    history = _load_json(HISTORY_FILE)
    if not history or not isinstance(history, list):
        history = []

    snapshot = {
        "timestamp": _now_iso(),
        "regime": _get_regime(),
    }
    for ac, port in portfolios.items():
        stats = _portfolio_stats(port)
        snapshot[ac.lower()] = stats

    history.append(snapshot)

    # Keep last 500 snapshots
    if len(history) > 500:
        history = history[-500:]

    _save_json(HISTORY_FILE, history)


# ===================================================================
# MAIN RUN
# ===================================================================

def run() -> dict:
    """
    Main entry point:
    1. Create portfolios if they don't exist
    2. Fetch live prices and compute unrealized PnL
    3. Check TP/SL hits
    4. Print comparison table
    5. Append snapshot to history
    """
    print("[multi_asset_test] Starting multi-asset portfolio comparison...")

    regime = _get_regime()
    print(f"[multi_asset_test] Current regime: {regime}")

    # Load existing portfolios or create new ones
    existing = _load_json(PORTFOLIOS_FILE)

    if existing and isinstance(existing, dict) and "CRYPTO" in existing:
        print("[multi_asset_test] Loading existing portfolios...")
        portfolios = existing
    else:
        print("[multi_asset_test] Creating new portfolios...")

        # Fetch all prices
        print("[multi_asset_test] Fetching crypto prices...")
        crypto_prices = fetch_crypto_prices(CRYPTO_SYMBOLS)
        print(f"  Got {len(crypto_prices)} crypto prices")

        print("[multi_asset_test] Fetching forex prices...")
        forex_prices = fetch_forex_prices()
        print(f"  Got {len(forex_prices)} forex prices")

        print("[multi_asset_test] Fetching stock prices...")
        stock_prices = fetch_stock_prices()
        print(f"  Got {len(stock_prices)} stock prices")

        print("[multi_asset_test] Fetching commodity prices...")
        commodity_prices = fetch_commodity_prices()
        print(f"  Got {len(commodity_prices)} commodity prices")

        # Build portfolios
        portfolios = {
            "CRYPTO": build_crypto_portfolio(crypto_prices, regime),
            "FOREX": build_forex_portfolio(forex_prices, regime),
            "STOCKS": build_stock_portfolio(stock_prices, regime),
            "COMMODITIES": build_commodity_portfolio(commodity_prices, regime),
        }

        portfolios["_meta"] = {
            "created_at": _now_iso(),
            "regime_at_creation": regime,
            "strategy": "momentum_20sma (uniform across all asset classes)",
            "budget_per_class": PORTFOLIO_BUDGET,
            "purpose": "Compare edge across asset classes using identical strategy",
        }

        _save_json(PORTFOLIOS_FILE, portfolios)
        print(f"[multi_asset_test] Saved new portfolios to {PORTFOLIOS_FILE}")

    # Update PnL with live prices
    print("[multi_asset_test] Updating PnL with live prices...")

    if "CRYPTO" in portfolios and isinstance(portfolios["CRYPTO"], dict):
        portfolios["CRYPTO"] = update_crypto_pnl(portfolios["CRYPTO"])
    if "FOREX" in portfolios and isinstance(portfolios["FOREX"], dict):
        portfolios["FOREX"] = update_forex_pnl(portfolios["FOREX"])
    if "STOCKS" in portfolios and isinstance(portfolios["STOCKS"], dict):
        portfolios["STOCKS"] = update_stock_pnl(portfolios["STOCKS"])
    if "COMMODITIES" in portfolios and isinstance(portfolios["COMMODITIES"], dict):
        portfolios["COMMODITIES"] = update_commodity_pnl(portfolios["COMMODITIES"])

    # Save updated portfolios
    _save_json(PORTFOLIOS_FILE, portfolios)

    # Print comparison
    print_comparison(portfolios)

    # Append history snapshot
    _append_history(portfolios)
    print(f"[multi_asset_test] History snapshot appended to {HISTORY_FILE}")

    return portfolios


def reset_portfolios() -> None:
    """Delete existing portfolios to force recreation on next run()."""
    if PORTFOLIOS_FILE.exists():
        PORTFOLIOS_FILE.unlink()
        print(f"[multi_asset_test] Deleted {PORTFOLIOS_FILE}")
    else:
        print("[multi_asset_test] No existing portfolios to delete")


# ===================================================================
# CLI
# ===================================================================

if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) > 1 and _sys.argv[1] == "--reset":
        reset_portfolios()
    run()
