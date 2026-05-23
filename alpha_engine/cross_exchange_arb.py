"""
ALPHA_ENGINE -- Cross-Exchange Arbitrage Engine
===============================================
Monitors price differentials and funding-rate spreads across Binance, OKX,
and Kraken to identify arbitrage opportunities.

Opportunity types:
  1. Price Arbitrage  -- Same asset priced differently across exchanges
  2. Funding Rate Arb -- Divergent perpetual funding rates (carry trade)

Data sources (all FREE, no API keys):
  - Binance spot:    /api/v3/ticker/price
  - Binance futures: /fapi/v1/ticker/price, /fapi/v1/premiumIndex
  - OKX spot:        /api/v5/market/ticker
  - OKX funding:     /api/v5/public/funding-rate
  - Kraken spot:     /0/public/Ticker (failover)

Execution cost model accounts for:
  - Maker/taker fees per exchange
  - Estimated withdrawal fees
  - Slippage (order-book depth proxy)

References:
  - Makarov & Schoar (2020), "Trading and Arbitrage in Cryptocurrency Markets"
    -- JFE: 135(2), pp. 293-319; cross-exchange spreads 1-5% during high vol
  - Hautsch et al. (2018), Limit Order Book dynamics across venues
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
    "DOGEUSDT", "XRPUSDT", "AVAXUSDT", "ADAUSDT",
]

# Exchange API base URLs (with fallbacks for geo-blocked CI)
BINANCE_SPOT_BASES = [
    "https://api.binance.com", "https://api1.binance.com",
    "https://data-api.binance.vision", "https://api.binance.us",
]
BINANCE_FUTURES_BASES = [
    "https://fapi.binance.com", "https://fapi1.binance.com",
    "https://fapi2.binance.com",
]
BINANCE_SPOT = BINANCE_SPOT_BASES[0]
BINANCE_FUTURES = BINANCE_FUTURES_BASES[0]
OKX_BASE = "https://www.okx.com"
KRAKEN_BASE = "https://api.kraken.com"

# Symbol mappings per exchange
_OKX_MAP = {
    "BTCUSDT": "BTC-USDT", "ETHUSDT": "ETH-USDT",
    "SOLUSDT": "SOL-USDT", "BNBUSDT": "BNB-USDT",
    "DOGEUSDT": "DOGE-USDT", "XRPUSDT": "XRP-USDT",
    "AVAXUSDT": "AVAX-USDT", "ADAUSDT": "ADA-USDT",
}

_KRAKEN_MAP = {
    "BTCUSDT": "XBTUSDT", "ETHUSDT": "ETHUSDT",
    "SOLUSDT": "SOLUSDT", "DOGEUSDT": "DOGEUSDT",
    "XRPUSDT": "XRPUSDT", "AVAXUSDT": "AVAXUSDT",
    "ADAUSDT": "ADAUSDT",
    # BNB not on Kraken -- will be skipped
}

# Fee schedule (maker/taker mid-point for retail tier)
_FEES = {
    "binance": 0.0010,   # 0.10% spot
    "okx":     0.0010,   # 0.10% spot
    "kraken":  0.0020,   # 0.20% spot (taker)
}

# Estimated withdrawal fees in USDT terms
_WITHDRAWAL_FEES_USDT = {
    "binance": 1.0,
    "okx":     0.5,
    "kraken":  2.5,
}

# Slippage estimate in bps based on typical order-book depth
_SLIPPAGE_BPS = {
    "BTCUSDT": 1.0, "ETHUSDT": 1.5, "SOLUSDT": 3.0, "BNBUSDT": 2.5,
    "DOGEUSDT": 4.0, "XRPUSDT": 2.0, "AVAXUSDT": 4.0, "ADAUSDT": 3.5,
}


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _fetch_json(url: str, timeout: int = 8) -> Optional[dict | list]:
    """Fetch JSON from a URL with timeout and error handling."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine-ArbScanner/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(value: float) -> float:
    """Round to appropriate precision based on magnitude."""
    if value == 0:
        return 0.0
    abs_val = abs(value)
    if abs_val >= 100:
        return round(value, 2)
    elif abs_val >= 1:
        return round(value, 4)
    elif abs_val >= 0.01:
        return round(value, 6)
    else:
        return round(value, 8)


# ---------------------------------------------------------------------------
# Price fetching -- multi-exchange
# ---------------------------------------------------------------------------

def _fetch_binance_spot_price(symbol: str) -> Optional[float]:
    """Fetch spot price from Binance."""
    url = f"{BINANCE_SPOT}/api/v3/ticker/price?symbol={symbol}"
    data = _fetch_json(url)
    if data and "price" in data:
        return float(data["price"])
    return None


def _fetch_okx_spot_price(symbol: str) -> Optional[float]:
    """Fetch spot price from OKX."""
    okx_sym = _OKX_MAP.get(symbol)
    if not okx_sym:
        return None
    url = f"{OKX_BASE}/api/v5/market/ticker?instId={okx_sym}"
    data = _fetch_json(url)
    if data and "data" in data and len(data["data"]) > 0:
        return float(data["data"][0].get("last", 0)) or None
    return None


def _fetch_kraken_spot_price(symbol: str) -> Optional[float]:
    """Fetch spot price from Kraken (failover exchange)."""
    kraken_sym = _KRAKEN_MAP.get(symbol)
    if not kraken_sym:
        return None
    url = f"{KRAKEN_BASE}/0/public/Ticker?pair={kraken_sym}"
    data = _fetch_json(url)
    if data and "result" in data and data.get("error", []) == []:
        # Kraken returns nested dict with pair name as key
        for pair_key, pair_data in data["result"].items():
            # 'c' = last trade [price, volume]
            if "c" in pair_data and len(pair_data["c"]) > 0:
                return float(pair_data["c"][0])
    return None


def fetch_prices_multi_exchange(symbol: str) -> dict[str, float]:
    """
    Fetch current prices from Binance, OKX, and Kraken for a given symbol.

    Parameters
    ----------
    symbol : str
        Trading pair in Binance format, e.g. "BTCUSDT".

    Returns
    -------
    dict[str, float]
        Mapping of {exchange_name: price} for all exchanges that returned data.
    """
    prices: dict[str, float] = {}

    binance_price = _fetch_binance_spot_price(symbol)
    if binance_price:
        prices["binance"] = binance_price

    okx_price = _fetch_okx_spot_price(symbol)
    if okx_price:
        prices["okx"] = okx_price

    kraken_price = _fetch_kraken_spot_price(symbol)
    if kraken_price:
        prices["kraken"] = kraken_price

    return prices


# ---------------------------------------------------------------------------
# Funding rate fetching -- multi-exchange
# ---------------------------------------------------------------------------

def _fetch_binance_funding_rate(symbol: str) -> Optional[float]:
    """Fetch current funding rate from Binance Futures."""
    url = f"{BINANCE_FUTURES}/fapi/v1/premiumIndex?symbol={symbol}"
    data = _fetch_json(url)
    if data and "lastFundingRate" in data:
        return float(data["lastFundingRate"])
    return None


def _fetch_okx_funding_rate(symbol: str) -> Optional[float]:
    """Fetch current funding rate from OKX."""
    okx_sym = _OKX_MAP.get(symbol)
    if not okx_sym:
        return None
    # OKX swap instrument ID format: BTC-USDT-SWAP
    swap_id = okx_sym + "-SWAP"
    url = f"{OKX_BASE}/api/v5/public/funding-rate?instId={swap_id}"
    data = _fetch_json(url)
    if data and "data" in data and len(data["data"]) > 0:
        rate_str = data["data"][0].get("fundingRate", "")
        if rate_str:
            return float(rate_str)
    return None


def fetch_funding_rates_multi(symbol: str) -> dict[str, float]:
    """
    Fetch perpetual funding rates from Binance Futures and OKX.

    Parameters
    ----------
    symbol : str
        Trading pair in Binance format, e.g. "BTCUSDT".

    Returns
    -------
    dict[str, float]
        Mapping of {exchange_name: funding_rate}.
    """
    rates: dict[str, float] = {}

    binance_rate = _fetch_binance_funding_rate(symbol)
    if binance_rate is not None:
        rates["binance"] = binance_rate

    okx_rate = _fetch_okx_funding_rate(symbol)
    if okx_rate is not None:
        rates["okx"] = okx_rate

    return rates


# ---------------------------------------------------------------------------
# Execution cost estimation
# ---------------------------------------------------------------------------

def estimate_execution_cost(symbol: str, exchanges: tuple[str, str]) -> float:
    """
    Estimate round-trip execution cost in basis points (bps) for an arbitrage
    trade between two exchanges.

    Includes:
      - Trading fees on both sides (buy + sell)
      - Withdrawal fee (to move asset from buy to sell exchange)
      - Estimated slippage on both sides

    Parameters
    ----------
    symbol : str
        Trading pair, e.g. "BTCUSDT".
    exchanges : tuple[str, str]
        (buy_exchange, sell_exchange) names.

    Returns
    -------
    float
        Estimated round-trip cost in basis points.
    """
    buy_ex, sell_ex = exchanges

    # Trading fees (both sides) in bps
    buy_fee_bps = _FEES.get(buy_ex, 0.0015) * 10_000
    sell_fee_bps = _FEES.get(sell_ex, 0.0015) * 10_000

    # Slippage (both sides) in bps
    slippage = _SLIPPAGE_BPS.get(symbol, 3.0) * 2  # both legs

    # Withdrawal fee as bps (estimated against a mid-range trade size of $5000)
    withdrawal_usdt = _WITHDRAWAL_FEES_USDT.get(buy_ex, 2.0)
    withdrawal_bps = (withdrawal_usdt / 5000) * 10_000

    total_bps = buy_fee_bps + sell_fee_bps + slippage + withdrawal_bps
    return round(total_bps, 2)


# ---------------------------------------------------------------------------
# Price arbitrage detection
# ---------------------------------------------------------------------------

def detect_price_arb(symbol: str, min_spread_bps: float = 10) -> Optional[dict]:
    """
    Compare spot prices across exchanges and detect profitable arbitrage
    opportunities where the spread exceeds a minimum threshold.

    Parameters
    ----------
    symbol : str
        Trading pair, e.g. "BTCUSDT".
    min_spread_bps : float
        Minimum spread in basis points to qualify as an opportunity.

    Returns
    -------
    Optional[dict]
        Arbitrage opportunity details, or None if no opportunity found.
    """
    prices = fetch_prices_multi_exchange(symbol)

    if len(prices) < 2:
        return None

    # Find min and max priced exchanges
    exchanges = list(prices.keys())
    min_ex = min(exchanges, key=lambda x: prices[x])
    max_ex = max(exchanges, key=lambda x: prices[x])

    buy_price = prices[min_ex]
    sell_price = prices[max_ex]

    if buy_price <= 0:
        return None

    spread_bps = ((sell_price - buy_price) / buy_price) * 10_000

    if spread_bps < min_spread_bps:
        return None

    # Check if spread exceeds execution costs
    exec_cost_bps = estimate_execution_cost(symbol, (min_ex, max_ex))
    net_profit_bps = spread_bps - exec_cost_bps

    if net_profit_bps <= 0:
        return None

    # Confidence: higher spread relative to cost = higher confidence
    confidence = min(0.95, 0.50 + (net_profit_bps / 100) * 0.3)
    confidence = round(confidence, 2)

    return {
        "symbol": symbol,
        "type": "price_arb",
        "buy_exchange": min_ex,
        "sell_exchange": max_ex,
        "buy_price": _smart_round(buy_price),
        "sell_price": _smart_round(sell_price),
        "spread_bps": round(spread_bps, 2),
        "execution_cost_bps": exec_cost_bps,
        "net_profit_bps": round(net_profit_bps, 2),
        "estimated_profit_pct": round(net_profit_bps / 100, 4),
        "confidence": confidence,
        "all_prices": {ex: _smart_round(p) for ex, p in prices.items()},
        "detected_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# Funding rate arbitrage detection
# ---------------------------------------------------------------------------

def detect_funding_arb(symbol: str, min_rate_diff: float = 0.0005) -> Optional[dict]:
    """
    Compare perpetual funding rates across exchanges and detect carry
    opportunities where rate divergence is exploitable.

    Strategy: Go long perps on the exchange with lower funding (you GET paid)
    and short perps on the exchange with higher funding (the premium you pay
    is smaller than what you earn on the other side).

    Parameters
    ----------
    symbol : str
        Trading pair, e.g. "BTCUSDT".
    min_rate_diff : float
        Minimum absolute funding rate difference to qualify.

    Returns
    -------
    Optional[dict]
        Funding arb opportunity details, or None.
    """
    rates = fetch_funding_rates_multi(symbol)

    if len(rates) < 2:
        return None

    exchanges = list(rates.keys())
    min_rate_ex = min(exchanges, key=lambda x: rates[x])
    max_rate_ex = max(exchanges, key=lambda x: rates[x])

    rate_diff = abs(rates[max_rate_ex] - rates[min_rate_ex])

    if rate_diff < min_rate_diff:
        return None

    # Funding is charged 3x/day (every 8h) -- annualize
    # Annual yield = rate_diff * 3 * 365
    annualized_yield = rate_diff * 3 * 365

    # Determine direction: long where funding is lower (you receive),
    # short where funding is higher (crowded longs pay you)
    if rates[max_rate_ex] > 0:
        direction = "LONG"  # long on low-funding exchange
        long_exchange = min_rate_ex
        short_exchange = max_rate_ex
    else:
        direction = "SHORT"  # both negative = short on less-negative side
        long_exchange = min_rate_ex
        short_exchange = max_rate_ex

    confidence = min(0.90, 0.55 + rate_diff * 200)
    confidence = round(confidence, 2)

    return {
        "symbol": symbol,
        "type": "funding_arb",
        "long_exchange": long_exchange,
        "short_exchange": short_exchange,
        "long_rate": round(rates[long_exchange], 6),
        "short_rate": round(rates[short_exchange], 6),
        "rate_diff": round(rate_diff, 6),
        "annualized_yield": round(annualized_yield, 4),
        "direction": direction,
        "confidence": confidence,
        "all_rates": {ex: round(r, 6) for ex, r in rates.items()},
        "detected_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# Convert arb opportunities to pick format
# ---------------------------------------------------------------------------

def _arb_to_pick(arb: dict) -> dict:
    """Convert a raw arb opportunity dict into a standard pick format."""

    if arb["type"] == "price_arb":
        entry = arb["buy_price"]
        tp = arb["sell_price"]
        sl = _smart_round(entry * (1 - arb["spread_bps"] / 10_000))
        return {
            "symbol": arb["symbol"],
            "direction": "LONG",
            "strategy": "cross_exchange_price_arb",
            "source": "cross_exchange_arb",
            "confidence": arb["confidence"],
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "details": {
                "buy_exchange": arb["buy_exchange"],
                "sell_exchange": arb["sell_exchange"],
                "spread_bps": arb["spread_bps"],
                "net_profit_bps": arb["net_profit_bps"],
                "execution_cost_bps": arb["execution_cost_bps"],
            },
            "generated_at": arb["detected_at"],
        }

    elif arb["type"] == "funding_arb":
        # Funding arb is market-neutral; entry/tp/sl are notional
        # Use current price as entry, yield as TP proxy
        prices = fetch_prices_multi_exchange(arb["symbol"])
        entry = prices.get("binance") or prices.get("okx") or 0
        if entry == 0:
            entry = 1.0  # fallback
        daily_yield = arb["rate_diff"] * 3
        tp = _smart_round(entry * (1 + daily_yield * 7))   # 7-day target
        sl = _smart_round(entry * (1 - daily_yield * 3))   # 3-day adverse
        return {
            "symbol": arb["symbol"],
            "direction": arb["direction"],
            "strategy": "cross_exchange_funding_arb",
            "source": "cross_exchange_arb",
            "confidence": arb["confidence"],
            "entry_price": _smart_round(entry),
            "take_profit": tp,
            "stop_loss": sl,
            "details": {
                "long_exchange": arb["long_exchange"],
                "short_exchange": arb["short_exchange"],
                "rate_diff": arb["rate_diff"],
                "annualized_yield": arb["annualized_yield"],
            },
            "generated_at": arb["detected_at"],
        }

    return {}


# ---------------------------------------------------------------------------
# Main scanner
# ---------------------------------------------------------------------------

def scan_all_arb(symbols: list[str] | None = None) -> list[dict]:
    """
    Scan all symbols for cross-exchange arbitrage opportunities.

    Runs both price and funding rate arb detection on every symbol,
    returning results sorted by estimated profit (best first).

    Parameters
    ----------
    symbols : list[str] or None
        Symbols to scan. Defaults to DEFAULT_SYMBOLS.

    Returns
    -------
    list[dict]
        List of pick-formatted opportunities sorted by confidence.
    """
    if symbols is None:
        symbols = DEFAULT_SYMBOLS

    opportunities: list[dict] = []

    for symbol in symbols:
        # Price arb
        price_arb = detect_price_arb(symbol)
        if price_arb:
            pick = _arb_to_pick(price_arb)
            if pick:
                opportunities.append(pick)

        # Funding arb
        funding_arb = detect_funding_arb(symbol)
        if funding_arb:
            pick = _arb_to_pick(funding_arb)
            if pick:
                opportunities.append(pick)

    # Sort by confidence descending
    opportunities.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    return opportunities


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    syms = sys.argv[1:] if len(sys.argv) > 1 else None
    print(f"Cross-Exchange Arbitrage Scanner -- {_now_iso()}")
    print(f"Scanning: {syms or DEFAULT_SYMBOLS}")
    print("-" * 60)

    results = scan_all_arb(syms)

    if not results:
        print("No arbitrage opportunities found (spreads below thresholds).")
    else:
        for i, pick in enumerate(results, 1):
            print(f"\n[{i}] {pick['symbol']} -- {pick['strategy']}")
            print(f"    Direction:  {pick['direction']}")
            print(f"    Confidence: {pick['confidence']}")
            print(f"    Entry:      {pick['entry_price']}")
            print(f"    TP:         {pick['take_profit']}")
            print(f"    SL:         {pick['stop_loss']}")
            for k, v in pick["details"].items():
                print(f"    {k}: {v}")

    print(f"\nTotal opportunities: {len(results)}")
