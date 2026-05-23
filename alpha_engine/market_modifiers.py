"""
Market Modifiers -- Confidence adjustments based on macro signals
================================================================
QW1: BTC Dominance trend -> boost/reduce alt confidence
QW2: Treasury Holdings -> boost BTC/ETH confidence
QW3: Circulating Supply Change -> boost deflationary coins
"""

import requests
import json
import os
from datetime import datetime, timezone

_CACHE = {}
_CACHE_TTL = 3600  # 1 hour


def _cached_get(url, key, ttl=3600):
    """Simple in-memory cache for API calls."""
    now = datetime.now(timezone.utc).timestamp()
    if key in _CACHE and now - _CACHE[key]["ts"] < ttl:
        return _CACHE[key]["data"]
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        _CACHE[key] = {"data": data, "ts": now}
        return data
    except Exception as e:
        print(f"  [market_modifiers] {key} fetch failed: {e}")
        return _CACHE.get(key, {}).get("data")


def btc_dominance_modifier(symbol: str) -> float:
    """
    Returns a confidence multiplier based on BTC dominance trend.
    - BTC.D falling -> alt season -> boost alts (1.05-1.15)
    - BTC.D rising -> BTC season -> reduce alts (0.85-0.95), boost BTC (1.05)
    - BTC.D stable -> no change (1.0)

    Uses CoinGecko /api/v3/global (free, no key).
    """
    data = _cached_get("https://api.coingecko.com/api/v3/global", "cg_global")
    if not data:
        return 1.0

    try:
        btc_d = data["data"]["market_cap_percentage"]["btc"]
        # Store for trend detection
        history_file = os.path.join(os.path.dirname(__file__), "data", "btc_dominance_history.json")
        history = []
        if os.path.exists(history_file):
            try:
                with open(history_file, "r") as f:
                    history = json.load(f)
            except Exception:
                history = []

        # Append current reading
        history.append({"ts": datetime.now(timezone.utc).isoformat(), "btc_d": btc_d})
        # Keep last 336 readings (14 days at hourly)
        history = history[-336:]

        try:
            with open(history_file, "w") as f:
                json.dump(history, f)
        except Exception:
            pass

        # Need at least 24 readings (1 day) for trend
        if len(history) < 24:
            return 1.0

        # 7-day SMA vs current
        recent_7d = [h["btc_d"] for h in history[-168:]] if len(history) >= 168 else [h["btc_d"] for h in history]
        sma_7d = sum(recent_7d) / len(recent_7d)

        # Trend: negative = BTC.D falling (alt season), positive = BTC.D rising
        trend = (btc_d - sma_7d) / max(sma_7d, 1)  # Normalized change

        is_btc = symbol.upper().startswith("BTC")

        if trend < -0.02:  # BTC.D falling >2% from SMA -> strong alt season
            return 1.0 if is_btc else 1.12
        elif trend < -0.005:  # Mild alt season
            return 1.0 if is_btc else 1.05
        elif trend > 0.02:  # BTC.D rising >2% -> BTC season
            return 1.08 if is_btc else 0.88
        elif trend > 0.005:  # Mild BTC season
            return 1.03 if is_btc else 0.95
        else:
            return 1.0  # Neutral
    except Exception as e:
        print(f"  [btc_d_modifier] error: {e}")
        return 1.0


def treasury_confidence_boost(symbol: str) -> float:
    """
    Returns confidence boost for coins held in corporate treasuries.
    BTC/ETH only (CoinGecko free API).
    Returns 0.0 to 0.10 boost.
    """
    sym = symbol.upper().replace("-USD", "").replace("USDT", "")

    if sym == "BTC":
        coin_id = "bitcoin"
    elif sym == "ETH":
        coin_id = "ethereum"
    else:
        return 0.0  # Only BTC/ETH have treasury data

    data = _cached_get(
        f"https://api.coingecko.com/api/v3/companies/public_treasury/{coin_id}",
        f"treasury_{coin_id}",
        ttl=86400  # Cache 24h -- treasury data doesn't change often
    )
    if not data:
        return 0.0

    try:
        total_holdings = data.get("total_holdings", 0)

        # Simple heuristic: if major institutions hold significant amounts, boost confidence
        # MicroStrategy alone holds ~200K+ BTC
        if coin_id == "bitcoin" and total_holdings > 200000:
            return 0.08
        elif coin_id == "bitcoin" and total_holdings > 100000:
            return 0.05
        elif coin_id == "ethereum" and total_holdings > 500000:
            return 0.06
        elif coin_id == "ethereum" and total_holdings > 200000:
            return 0.04

        return 0.02  # Some institutional presence
    except Exception as e:
        print(f"  [treasury_boost] error: {e}")
        return 0.0


def supply_change_boost(symbol: str) -> float:
    """
    Returns confidence boost for coins with decreasing circulating supply.
    Uses CoinGecko /coins/{id} for supply data.
    Returns 0.0 to 0.15 boost.
    """
    # Map symbol to CoinGecko ID
    sym = symbol.upper().replace("-USD", "").replace("USDT", "")
    SYMBOL_TO_CG = {
        "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "XRP": "ripple",
        "BNB": "binancecoin", "ADA": "cardano", "DOGE": "dogecoin", "DOT": "polkadot",
        "AVAX": "avalanche-2", "LINK": "chainlink", "NEAR": "near", "UNI": "uniswap",
        "AAVE": "aave", "ARB": "arbitrum", "INJ": "injective-protocol", "ATOM": "cosmos",
        "FET": "fetch-ai", "HYPE": "hyperliquid", "TRX": "tron", "SUI": "sui",
        "MATIC": "matic-network", "ONDO": "ondo-finance", "RENDER": "render-token",
    }

    cg_id = SYMBOL_TO_CG.get(sym)
    if not cg_id:
        return 0.0

    data = _cached_get(
        f"https://api.coingecko.com/api/v3/coins/{cg_id}?localization=false&tickers=false&community_data=false&developer_data=false",
        f"supply_{cg_id}",
        ttl=3600
    )
    if not data:
        return 0.0

    try:
        market = data.get("market_data", {})
        circulating = market.get("circulating_supply") or 0
        max_supply = market.get("max_supply") or market.get("total_supply") or 0

        if not circulating or not max_supply:
            return 0.0

        supply_ratio = circulating / max_supply

        # Track supply changes over time
        history_file = os.path.join(os.path.dirname(__file__), "data", "supply_history.json")
        history = {}
        if os.path.exists(history_file):
            try:
                with open(history_file, "r") as f:
                    history = json.load(f)
            except Exception:
                history = {}

        prior = history.get(cg_id, {}).get("circulating", circulating)
        delta_pct = (prior - circulating) / max(prior, 1) * 100  # Positive = supply decreased

        # Update history
        history[cg_id] = {
            "circulating": circulating,
            "max_supply": max_supply,
            "ratio": round(supply_ratio, 4),
            "ts": datetime.now(timezone.utc).isoformat()
        }
        try:
            with open(history_file, "w") as f:
                json.dump(history, f, indent=2)
        except Exception:
            pass

        # Boost if supply is decreasing (burns/locks)
        if delta_pct > 5.0:  # >5% decrease -- major burn/lock event
            return 0.15
        elif delta_pct > 1.0:  # >1% decrease -- significant
            return 0.10
        elif delta_pct > 0.1:  # Minor decrease
            return 0.05
        elif supply_ratio < 0.5:  # Less than 50% of max supply in circulation
            return 0.03  # Mild boost for scarcity

        return 0.0
    except Exception as e:
        print(f"  [supply_change] error: {e}")
        return 0.0


def apply_all_modifiers(pick: dict) -> dict:
    """
    Apply all market modifiers to a pick's confidence score.
    Call this in the scanner after generating signals.
    """
    symbol = pick.get("symbol", "")
    original_conf = pick.get("confidence", 0.5)

    # QW1: BTC dominance modifier (multiplicative)
    btc_d_mod = btc_dominance_modifier(symbol)

    # QW2: Treasury boost (additive)
    treasury_boost = treasury_confidence_boost(symbol)

    # QW3: Supply change boost (additive)
    supply_boost = supply_change_boost(symbol)

    # Apply
    new_conf = original_conf * btc_d_mod + treasury_boost + supply_boost
    new_conf = round(min(0.95, max(0.05, new_conf)), 2)

    # Track what changed
    if new_conf != original_conf:
        mods = []
        if btc_d_mod != 1.0:
            mods.append(f"BTC.D\u00d7{btc_d_mod:.2f}")
        if treasury_boost > 0:
            mods.append(f"Treasury+{treasury_boost:.2f}")
        if supply_boost > 0:
            mods.append(f"Supply+{supply_boost:.2f}")
        pick["_market_mods"] = ", ".join(mods)

    pick["confidence"] = new_conf
    return pick
