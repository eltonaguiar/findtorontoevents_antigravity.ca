"""
DefiLlama Capital Flow Signals
==============================
Uses the free DefiLlama API (no auth required) to generate capital flow
signals for the Alpha Engine ML ranker.

Endpoints used:
  - api.llama.fi/v2/historicalChainTvl/{chain}
  - api.llama.fi/v2/chains
  - stablecoins.llama.fi/stablecoins?includePrices=true
  - stablecoins.llama.fi/stablecoincharts/all?stablecoin=1

Author: Alpha Engine
"""

import time
import logging
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Simple in-memory cache (key -> (timestamp, data))
# ---------------------------------------------------------------------------
_cache: dict = {}
CACHE_TTL_SECONDS = 900  # 15 minutes

REQUEST_TIMEOUT = 10  # seconds


def _get_cached(key: str):
    """Return cached value if still fresh, else None."""
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < CACHE_TTL_SECONDS:
            return data
    return None


def _set_cached(key: str, data):
    _cache[key] = (time.time(), data)


# ---------------------------------------------------------------------------
# Chain name mapping (token symbol -> DefiLlama chain slug)
# ---------------------------------------------------------------------------
CHAIN_MAP = {
    "ETH": "Ethereum",
    "SOL": "Solana",
    "AVAX": "Avalanche",
    "BNB": "BSC",
    "MATIC": "Polygon",
    "ARB": "Arbitrum",
    "OP": "Optimism",
    "FTM": "Fantom",
    "BASE": "Base",
    "NEAR": "Near",
    "SUI": "Sui",
    "APT": "Aptos",
    "ATOM": "Cosmos",
    "DOT": "Polkadot",
    "ADA": "Cardano",
    "TRX": "Tron",
}


def _resolve_chain(chain: str) -> str:
    """Resolve a chain name/symbol to the DefiLlama slug."""
    upper = chain.upper().strip()
    if upper in CHAIN_MAP:
        return CHAIN_MAP[upper]
    # Already a proper slug like "Ethereum" or "ethereum"
    return chain.capitalize() if chain.islower() else chain


# ---------------------------------------------------------------------------
# 1. Chain TVL momentum
# ---------------------------------------------------------------------------
def get_chain_tvl_momentum(chain: str, window: int = 7) -> dict:
    """
    Fetch historical TVL for *chain* and compute rate-of-change over *window* days.

    Returns:
        {
            "chain": str,
            "tvl_current": float,
            "tvl_7d_ago": float,
            "momentum_pct": float,
            "signal": "INFLOW" | "OUTFLOW" | "FLAT"
        }
    """
    slug = _resolve_chain(chain)
    cache_key = f"tvl_momentum:{slug}:{window}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    default = {
        "chain": slug,
        "tvl_current": 0.0,
        "tvl_7d_ago": 0.0,
        "momentum_pct": 0.0,
        "signal": "FLAT",
    }

    try:
        url = f"https://api.llama.fi/v2/historicalChainTvl/{slug}"
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()  # list of {"date": unix, "tvl": float}

        if not data or len(data) < window + 1:
            logger.warning("Not enough TVL history for %s (%d points)", slug, len(data) if data else 0)
            return default

        # Data is sorted oldest-first; take the tail
        tvl_current = float(data[-1]["tvl"])
        tvl_past = float(data[-(window + 1)]["tvl"])

        if tvl_past == 0:
            return default

        momentum_pct = ((tvl_current - tvl_past) / tvl_past) * 100.0

        if momentum_pct > 2.0:
            signal = "INFLOW"
        elif momentum_pct < -2.0:
            signal = "OUTFLOW"
        else:
            signal = "FLAT"

        result = {
            "chain": slug,
            "tvl_current": round(tvl_current, 2),
            "tvl_7d_ago": round(tvl_past, 2),
            "momentum_pct": round(momentum_pct, 4),
            "signal": signal,
        }
        _set_cached(cache_key, result)
        return result

    except Exception as exc:
        logger.error("get_chain_tvl_momentum(%s) failed: %s", slug, exc)
        return default


# ---------------------------------------------------------------------------
# 2. Stablecoin supply signal
# ---------------------------------------------------------------------------
def get_stablecoin_supply_signal() -> dict:
    """
    Compare current aggregate stablecoin market-cap to 7 days ago.

    Rising supply  = dry powder waiting to deploy = BULLISH
    Falling supply = capital exiting               = BEARISH

    Returns:
        {
            "total_supply": float,
            "supply_change_7d_pct": float,
            "signal": "BULLISH" | "BEARISH" | "NEUTRAL"
        }
    """
    cache_key = "stablecoin_supply_signal"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    default = {
        "total_supply": 0.0,
        "supply_change_7d_pct": 0.0,
        "signal": "NEUTRAL",
    }

    try:
        # --- current aggregate supply from /stablecoins ---
        resp = requests.get(
            "https://stablecoins.llama.fi/stablecoins?includePrices=true",
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        stables = resp.json().get("peggedAssets", [])

        total_now = 0.0
        for coin in stables:
            # Each coin has "chains" list and "chainCirculating" dict
            # Simplest: use the top-level "circulating" -> "peggedUSD"
            circ = coin.get("circulating", {}).get("peggedUSD", 0)
            if circ:
                total_now += float(circ)

        # --- historical USDT supply chart (stablecoin id=1) for 7d comparison ---
        resp2 = requests.get(
            "https://stablecoins.llama.fi/stablecoincharts/all?stablecoin=1",
            timeout=REQUEST_TIMEOUT,
        )
        resp2.raise_for_status()
        chart = resp2.json()  # list of {"date": unix, "totalCirculating": {"peggedUSD": float}, ...}

        if not chart or len(chart) < 8:
            logger.warning("Not enough stablecoin chart history")
            result = {**default, "total_supply": round(total_now, 2)}
            _set_cached(cache_key, result)
            return result

        # Use the full aggregate supply for current, and compute 7d change
        # from the chart (USDT is the largest component and a good proxy)
        usdt_now = float(chart[-1].get("totalCirculating", {}).get("peggedUSD", 0))
        usdt_7d = float(chart[-8].get("totalCirculating", {}).get("peggedUSD", 0))

        if usdt_7d == 0:
            result = {**default, "total_supply": round(total_now, 2)}
            _set_cached(cache_key, result)
            return result

        supply_change_pct = ((usdt_now - usdt_7d) / usdt_7d) * 100.0

        if supply_change_pct > 0.5:
            signal = "BULLISH"
        elif supply_change_pct < -0.5:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"

        result = {
            "total_supply": round(total_now, 2),
            "supply_change_7d_pct": round(supply_change_pct, 4),
            "signal": signal,
        }
        _set_cached(cache_key, result)
        return result

    except Exception as exc:
        logger.error("get_stablecoin_supply_signal() failed: %s", exc)
        return default


# ---------------------------------------------------------------------------
# 3. TVL vs price divergence
# ---------------------------------------------------------------------------
def get_tvl_price_divergence(chain: str, price_change_pct: float) -> dict:
    """
    Compare TVL momentum with price change to detect accumulation/distribution.

    - TVL rising + price falling  -> accumulation -> BULLISH  (score > 0)
    - TVL falling + price rising  -> distribution -> BEARISH  (score < 0)
    - Same direction              -> neutral      (score ~ 0)

    Args:
        chain: chain name or symbol (e.g. "ethereum", "ETH")
        price_change_pct: 7-day price change percentage of the chain's native token

    Returns:
        {
            "chain": str,
            "tvl_change_pct": float,
            "price_change_pct": float,
            "divergence_score": float (-1.0 to 1.0),
            "signal": "BULLISH_DIVERGENCE" | "BEARISH_DIVERGENCE" | "NO_DIVERGENCE"
        }
    """
    slug = _resolve_chain(chain)
    cache_key = f"tvl_price_div:{slug}:{price_change_pct}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    default = {
        "chain": slug,
        "tvl_change_pct": 0.0,
        "price_change_pct": price_change_pct,
        "divergence_score": 0.0,
        "signal": "NO_DIVERGENCE",
    }

    try:
        tvl_data = get_chain_tvl_momentum(chain)
        tvl_change = tvl_data["momentum_pct"]

        # Divergence = TVL direction minus price direction
        # Normalize both to [-1, 1] range using tanh-like clamping
        def _norm(val: float, scale: float = 10.0) -> float:
            """Soft-clamp to [-1, 1]."""
            return max(-1.0, min(1.0, val / scale))

        tvl_norm = _norm(tvl_change)
        price_norm = _norm(price_change_pct)

        # Divergence score: positive when TVL leads price (accumulation)
        # negative when price leads TVL (distribution)
        divergence_score = tvl_norm - price_norm
        divergence_score = max(-1.0, min(1.0, divergence_score))

        if divergence_score > 0.3:
            signal = "BULLISH_DIVERGENCE"
        elif divergence_score < -0.3:
            signal = "BEARISH_DIVERGENCE"
        else:
            signal = "NO_DIVERGENCE"

        result = {
            "chain": slug,
            "tvl_change_pct": round(tvl_change, 4),
            "price_change_pct": round(price_change_pct, 4),
            "divergence_score": round(divergence_score, 4),
            "signal": signal,
        }
        _set_cached(cache_key, result)
        return result

    except Exception as exc:
        logger.error("get_tvl_price_divergence(%s) failed: %s", slug, exc)
        return default


# ---------------------------------------------------------------------------
# 4. Composite DeFi signal
# ---------------------------------------------------------------------------
def get_defi_composite_signal() -> dict:
    """
    Combine TVL momentum (Ethereum), stablecoin supply, and TVL-price divergence
    into a single composite score for the ML ranker.

    Returns:
        {
            "composite_score": float (-1.0 to 1.0),
            "components": {
                "eth_tvl_momentum": dict,
                "stablecoin_supply": dict,
                "eth_tvl_price_div": dict,
            },
            "signal": "STRONG_BULLISH" | "BULLISH" | "NEUTRAL" | "BEARISH" | "STRONG_BEARISH"
        }
    """
    cache_key = "defi_composite"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    default = {
        "composite_score": 0.0,
        "components": {},
        "signal": "NEUTRAL",
    }

    try:
        # Component 1: Ethereum TVL momentum (largest DeFi chain)
        eth_tvl = get_chain_tvl_momentum("ethereum")

        # Component 2: Stablecoin supply
        stable = get_stablecoin_supply_signal()

        # Component 3: ETH TVL vs price divergence
        # We use ETH TVL change as a rough proxy; caller can supply real price
        # For composite, assume price_change ≈ 0 (we only have TVL data here)
        eth_div = get_tvl_price_divergence("ethereum", price_change_pct=0.0)

        # --- Score computation ---
        # TVL momentum component: map signal to score
        tvl_score_map = {"INFLOW": 1.0, "OUTFLOW": -1.0, "FLAT": 0.0}
        tvl_score = tvl_score_map.get(eth_tvl["signal"], 0.0)

        # Stablecoin component
        stable_score_map = {"BULLISH": 1.0, "BEARISH": -1.0, "NEUTRAL": 0.0}
        stable_score = stable_score_map.get(stable["signal"], 0.0)

        # Divergence component (already -1 to 1)
        div_score = eth_div["divergence_score"]

        # Weighted average: TVL 40%, Stablecoin 35%, Divergence 25%
        composite = (tvl_score * 0.40) + (stable_score * 0.35) + (div_score * 0.25)
        composite = max(-1.0, min(1.0, round(composite, 4)))

        if composite > 0.5:
            signal = "STRONG_BULLISH"
        elif composite > 0.15:
            signal = "BULLISH"
        elif composite < -0.5:
            signal = "STRONG_BEARISH"
        elif composite < -0.15:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"

        result = {
            "composite_score": composite,
            "components": {
                "eth_tvl_momentum": eth_tvl,
                "stablecoin_supply": stable,
                "eth_tvl_price_div": eth_div,
            },
            "signal": signal,
        }
        _set_cached(cache_key, result)
        return result

    except Exception as exc:
        logger.error("get_defi_composite_signal() failed: %s", exc)
        return default


# ---------------------------------------------------------------------------
# Demo / CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    print("=" * 60)
    print("DefiLlama Capital Flow Signals -- Demo")
    print("=" * 60)

    print("\n--- 1. Ethereum TVL Momentum (7d) ---")
    eth = get_chain_tvl_momentum("ethereum")
    print(json.dumps(eth, indent=2))

    print("\n--- 2. Solana TVL Momentum (7d) ---")
    sol = get_chain_tvl_momentum("SOL")
    print(json.dumps(sol, indent=2))

    print("\n--- 3. Stablecoin Supply Signal ---")
    sc = get_stablecoin_supply_signal()
    print(json.dumps(sc, indent=2))

    print("\n--- 4. ETH TVL vs Price Divergence (price -5%) ---")
    div = get_tvl_price_divergence("ethereum", price_change_pct=-5.0)
    print(json.dumps(div, indent=2))

    print("\n--- 5. Composite DeFi Signal ---")
    comp = get_defi_composite_signal()
    print(json.dumps(comp, indent=2))

    print("\n" + "=" * 60)
    print(f"Composite score: {comp['composite_score']} -> {comp['signal']}")
    print("=" * 60)
